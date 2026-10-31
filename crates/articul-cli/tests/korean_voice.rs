use std::path::PathBuf;

const SR: u32 = 22050;
const BASE_F0: f32 = 120.0;

fn workspace_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
}

fn default_cfg() -> articul_config::VoiceConfig {
    articul_config::VoiceConfig::load(&workspace_root().join("config").join("default-voice.toml"))
        .expect("default voice must load")
}

fn korean_cfg() -> articul_config::VoiceConfig {
    articul_config::VoiceConfig::load(&workspace_root().join("config").join("korean-voice.toml"))
        .expect("korean voice must load")
}

fn render_default(text: &str) -> Vec<f32> {
    articul_cli::render_with_voice(text, &default_cfg(), BASE_F0)
}

fn render_korean(text: &str) -> Vec<f32> {
    articul_cli::render_with_voice(text, &korean_cfg(), BASE_F0)
}

fn plan_korean(
    text: &str,
    boundary: articul_front::prosody::BoundaryTone,
) -> Vec<articul_front::prosody::ProsodicPhoneme> {
    let words: Vec<String> = text.split_whitespace().map(str::to_string).collect();
    let parsed = articul_front::parse_utterance(&words);
    articul_front::prosody::plan_utterance_korean(&parsed, 1.0, 1.0, BASE_F0, boundary)
}

fn is_vowel_unit(u: &articul_front::prosody::ProsodicPhoneme) -> bool {
    matches!(u.phoneme.kind, articul_phon::SegmentKind::Vowel { .. })
}

fn unit_boundaries(planned: &[articul_front::prosody::ProsodicPhoneme]) -> Vec<usize> {
    let short = ((0.008 * SR as f32) as usize).max(1);
    let glide = ((0.050 * SR as f32) as usize).max(1);
    let mut bounds = Vec::with_capacity(planned.len() + 1);
    let mut start = 0usize;
    bounds.push(0);
    for (i, u) in planned.iter().enumerate() {
        let len = ((u.duration_ms as f32 / 1000.0) * SR as f32)
            .round()
            .max(1.0) as usize;
        if i > 0 {
            let prev_vowel = is_vowel_unit(&planned[i - 1]);
            let fade = if prev_vowel && is_vowel_unit(u) {
                glide
            } else {
                short
            };
            start = start.saturating_sub(fade.min(start));
        }
        start += len;
        bounds.push(start);
    }
    bounds
}

fn avg_power_fft(seg: &[f32], n_fft: usize) -> Vec<f32> {
    use rustfft::num_complex::Complex;
    use rustfft::FftPlanner;
    let n = seg.len().next_power_of_two().max(64).min(n_fft);
    let mut buf: Vec<Complex<f32>> = Vec::with_capacity(n);
    let m = seg.len().max(2) as f32;
    for (i, s) in seg.iter().enumerate() {
        let w = 0.5 - 0.5 * (std::f32::consts::PI * 2.0 * i as f32 / m).cos();
        buf.push(Complex::new(s * w, 0.0));
    }
    buf.resize(n, Complex::new(0.0, 0.0));
    FftPlanner::new().plan_fft_forward(n).process(&mut buf);
    (0..n / 2).map(|k| buf[k].norm_sqr() / n as f32).collect()
}

fn smooth_spectrum(power: &[f32], width: usize) -> Vec<f32> {
    let half = power.len();
    let mut out = vec![0.0f32; half];
    for (k, slot) in out.iter_mut().enumerate() {
        let a = k.saturating_sub(width);
        let b = (k + width + 1).min(half);
        *slot = power[a..b].iter().sum::<f32>() / (b - a) as f32;
    }
    out
}

fn peak_in_band(power: &[f32], lo_hz: f32, hi_hz: f32) -> Option<f32> {
    let n2 = power.len() * 2;
    let to_bin = |f: f32| (f / SR as f32 * n2 as f32).round() as usize;
    let lo = to_bin(lo_hz).max(3);
    let hi = to_bin(hi_hz).min(power.len().saturating_sub(3));
    if lo >= hi {
        return None;
    }
    let ref_lo = to_bin(300.0).max(1);
    let ref_hi = to_bin(3000.0).min(power.len());
    let mut ref_sorted = power[ref_lo..ref_hi].to_vec();
    ref_sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let median = ref_sorted[ref_sorted.len() / 2].max(1e-12);
    let mut best: Option<(f32, usize)> = None;
    for k in (lo + 2)..(hi.saturating_sub(1)) {
        if power[k] > power[k - 1]
            && power[k] > power[k - 2]
            && power[k] >= power[k + 1]
            && power[k] >= power[k + 2]
            && power[k] > 2.0 * median
            && best.is_none_or(|(p, _)| power[k] > p)
        {
            best = Some((power[k], k));
        }
    }
    best.map(|(_, k)| k as f32 * SR as f32 / n2 as f32)
}

fn vowel_mid_window(
    out: &[f32],
    planned: &[articul_front::prosody::ProsodicPhoneme],
    vowel_idx: usize,
) -> Vec<f32> {
    let bounds = unit_boundaries(planned);
    let mut seen = 0usize;
    for (i, u) in planned.iter().enumerate() {
        if is_vowel_unit(u) {
            if seen == vowel_idx {
                let len = (bounds[i + 1] - bounds[i]).min(out.len().saturating_sub(bounds[i]));
                let start = bounds[i] + len / 4;
                let take = len / 2;
                return out[start..start + take].to_vec();
            }
            seen += 1;
        }
    }
    panic!("vowel {vowel_idx} not found");
}

fn formant_peaks(
    out: &[f32],
    planned: &[articul_front::prosody::ProsodicPhoneme],
    vowel_idx: usize,
) -> Vec<f32> {
    let seg = vowel_mid_window(out, planned, vowel_idx);
    smooth_spectrum(&avg_power_fft(&seg, 8192), 12)
}

fn autocorr_f0(seg: &[f32]) -> Option<f32> {
    let mean = seg.iter().sum::<f32>() / seg.len().max(1) as f32;
    let x: Vec<f32> = seg.iter().map(|v| v - mean).collect();
    let e0: f32 = x.iter().map(|v| v * v).sum();
    if e0 <= 1e-12 {
        return None;
    }
    let lo = (SR as f32 / 250.0).round() as usize;
    let hi = (SR as f32 / 70.0).round() as usize;
    let mut best_lag = 0usize;
    let mut best_val = f32::NEG_INFINITY;
    for lag in lo..=hi.min(x.len().saturating_sub(1)) {
        let mut acc = 0.0f32;
        for i in 0..x.len() - lag {
            acc += x[i] * x[i + lag];
        }
        let v = acc / e0;
        if v > best_val {
            best_val = v;
            best_lag = lag;
        }
    }
    if best_lag == 0 {
        return None;
    }
    Some(SR as f32 / best_lag as f32)
}

fn vowel_center_f0(
    out: &[f32],
    planned: &[articul_front::prosody::ProsodicPhoneme],
    vowel_idx: usize,
) -> f32 {
    let bounds = unit_boundaries(planned);
    let mut seen = 0usize;
    for (i, u) in planned.iter().enumerate() {
        if is_vowel_unit(u) {
            if seen == vowel_idx {
                let center = (bounds[i] + bounds[i + 1]) / 2;
                let half = (0.015 * SR as f32) as usize;
                let a = center.saturating_sub(half);
                let b = (center + half).min(out.len());
                return autocorr_f0(&out[a..b]).expect("voiced center must yield f0");
            }
            seen += 1;
        }
    }
    panic!("vowel {vowel_idx} not found");
}

fn to_st(f: f32) -> f32 {
    12.0 * (f / BASE_F0).log2()
}

fn sha256_hex(data: &[u8]) -> String {
    const K: [u32; 64] = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4,
        0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe,
        0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
        0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
        0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
        0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
        0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116,
        0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
        0xc67178f2,
    ];
    let mut h: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab,
        0x5be0cd19,
    ];
    let mut msg = data.to_vec();
    let bit_len = (data.len() as u64).wrapping_mul(8);
    msg.push(0x80);
    while msg.len() % 64 != 56 {
        msg.push(0);
    }
    msg.extend_from_slice(&bit_len.to_be_bytes());
    for block in msg.chunks_exact(64) {
        let mut w = [0u32; 64];
        for i in 0..16 {
            w[i] = u32::from_be_bytes([
                block[4 * i],
                block[4 * i + 1],
                block[4 * i + 2],
                block[4 * i + 3],
            ]);
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
        }
        let (mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut hh) =
            (h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7]);
        for i in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let t1 = hh
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(K[i])
                .wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let t2 = s0.wrapping_add(maj);
            hh = g;
            g = f;
            f = e;
            e = d.wrapping_add(t1);
            d = c;
            c = b;
            b = a;
            a = t1.wrapping_add(t2);
        }
        h[0] = h[0].wrapping_add(a);
        h[1] = h[1].wrapping_add(b);
        h[2] = h[2].wrapping_add(c);
        h[3] = h[3].wrapping_add(d);
        h[4] = h[4].wrapping_add(e);
        h[5] = h[5].wrapping_add(f);
        h[6] = h[6].wrapping_add(g);
        h[7] = h[7].wrapping_add(hh);
    }
    let mut s = String::with_capacity(64);
    for v in h {
        s.push_str(&format!("{v:08x}"));
    }
    s
}

fn wav_bytes(samples: &[f32], sample_rate: u32) -> Vec<u8> {
    let mut cursor = std::io::Cursor::new(Vec::new());
    {
        let spec = hound::WavSpec {
            channels: 1,
            sample_rate,
            bits_per_sample: 16,
            sample_format: hound::SampleFormat::Int,
        };
        let mut writer = hound::WavWriter::new(&mut cursor, spec).expect("wav writer");
        for v in samples {
            writer
                .write_sample((v.clamp(-1.0, 1.0) * 32767.0).round() as i16)
                .expect("wav sample");
        }
        writer.finalize().expect("wav finalize");
    }
    cursor.into_inner()
}

#[test]
fn sha256_self_check() {
    assert_eq!(
        sha256_hex(b"abc"),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    );
}

#[test]
fn korean_o_f2_neutral() {
    let out = render_korean("%ho");
    let planned = plan_korean("%ho", articul_front::prosody::BoundaryTone::High);
    let power = formant_peaks(&out, &planned, 0);
    let f2 = peak_in_band(&power, 703.0, 777.0);
    assert!(
        f2.is_some(),
        "korean o must show F2 peak in 703-777Hz, got {f2:?}"
    );
}

#[test]
fn korean_a_f1f2_neutral() {
    let out = render_korean("%ha");
    let planned = plan_korean("%ha", articul_front::prosody::BoundaryTone::High);
    let power = formant_peaks(&out, &planned, 0);
    let f1 = peak_in_band(&power, 656.0, 725.0);
    let f2 = peak_in_band(&power, 1072.0, 1258.0);
    assert!(
        f1.is_some(),
        "korean a must show F1 peak in 656-725Hz, got {f1:?}"
    );
    assert!(
        f2.is_some(),
        "korean a must show F2 peak in 1072-1258Hz, got {f2:?}"
    );
}

#[test]
fn korean_e_f2_neutral() {
    let out = render_korean("%he");
    let planned = plan_korean("%he", articul_front::prosody::BoundaryTone::High);
    let power = formant_peaks(&out, &planned, 0);
    let f2 = peak_in_band(&power, 1823.0, 2015.0);
    assert!(
        f2.is_some(),
        "korean e must show F2 peak in 1823-2015Hz, got {f2:?}"
    );
}

fn check_flat_f0(text: &str) {
    let out = render_korean(text);
    let planned = plan_korean(text, articul_front::prosody::BoundaryTone::High);
    let nvowels = planned.iter().filter(|u| is_vowel_unit(u)).count();
    assert!(nvowels >= 2);
    let mut centers = Vec::with_capacity(nvowels);
    for i in 0..nvowels {
        centers.push(to_st(vowel_center_f0(&out, &planned, i)));
    }
    let (last, rest) = centers.split_last().unwrap();
    let lo = rest.iter().fold(f32::INFINITY, |a, b| a.min(*b));
    let hi = rest.iter().fold(f32::NEG_INFINITY, |a, b| a.max(*b));
    assert!(
        hi - lo <= 3.5,
        "non-final vowel-center excursion {lo:.2}..{hi:.2}st must stay within 3.5st"
    );
    for v in rest {
        assert!(
            *v <= 2.5,
            "no non-final vowel-center peak above +2.5st, got {v:.2}"
        );
    }
    assert!(
        (*last - 3.0).abs() <= 0.5,
        "final H% target +3.0+-0.5st, got {last:.2}"
    );
}

#[test]
fn korean_flat_f0_no_nucleus_annyeong() {
    check_flat_f0("%an njVN h\\asejo");
}

#[test]
fn korean_flat_f0_no_nucleus_yeobo() {
    check_flat_f0("jVbosejo");
}

#[test]
fn tis_tin_unchanged_default_voice() {
    let out = render_default("TIs TIN");
    assert_eq!(out.len(), 8822);
    let hash = sha256_hex(&wav_bytes(&out, SR));
    assert_eq!(
        hash,
        "9385ab30c7a9c46f0de2ba533e40b2a94bd9d163732f438bb47c5825dfac41d4"
    );
}

#[test]
fn hello_unchanged_default_voice() {
    let out = render_default("h@ \"loU");
    assert_eq!(out.len(), 9219);
    let reader = hound::WavReader::open(workspace_root().join("demo").join("hello.wav"))
        .expect("demo hello must open");
    assert_eq!(reader.spec().sample_rate, SR);
    let expected: Vec<i16> = reader
        .into_samples::<i16>()
        .map(|s| s.expect("sample"))
        .collect();
    assert_eq!(expected.len(), 9219);
    let rendered: Vec<i16> = out
        .iter()
        .map(|v| (v.clamp(-1.0, 1.0) * 32767.0).round() as i16)
        .collect();
    assert_eq!(rendered, expected);
}
