use articul_front::parse_utterance;
use articul_front::plan_utterance;

const SR: u32 = 22050;

fn band_energy(x: &[f32], lo_hz: f32, hi_hz: f32) -> f64 {
    let n = x.len();
    let mut e = 0.0f64;
    for k in 1..=n / 2 {
        let f = k as f64 * SR as f64 / n as f64;
        if f < lo_hz as f64 || f >= hi_hz as f64 {
            continue;
        }
        let mut re = 0.0f64;
        let mut im = 0.0f64;
        for (i, v) in x.iter().enumerate() {
            let a = 2.0 * std::f64::consts::PI * k as f64 * i as f64 / n as f64;
            re += *v as f64 * a.cos();
            im -= *v as f64 * a.sin();
        }
        e += re * re + im * im;
    }
    2.0 * e / n as f64
}

#[test]
fn scratch_flood_check() {
    let text = "hE \"loU";
    let words: Vec<String> = articul_front::normalize(text);
    let parsed = parse_utterance(&words);
    let planned = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    let out = articul_cli::render_sentence(text, SR, 120.0);
    let n = out.len();
    let bed_level = 10.0f32.powf(-50.0 / 20.0);
    let bed_k = (-2.0 * std::f32::consts::PI * 6000.0 / SR as f32).exp();
    let mut bed_state: u64 = 0x9E3779B97F4A7C15;
    let mut bed_lp = 0.0f32;
    let mut bed = vec![0.0f32; n];
    for v in bed.iter_mut() {
        bed_state ^= bed_state << 13;
        bed_state ^= bed_state >> 7;
        bed_state ^= bed_state << 17;
        let w = ((bed_state >> 32) as f32 / u32::MAX as f32) * 2.0 - 1.0;
        bed_lp += (1.0 - bed_k) * (w - bed_lp);
        *v = bed_lp;
    }
    let bed_rms = (bed.iter().map(|v| v * v).sum::<f32>() / n as f32).sqrt();
    let bed_g = bed_level / bed_rms;
    let g3_start = 4698usize;
    let cut = g3_start + 3263;
    for (tag, a, b) in [("o", g3_start + 220, cut - 176), ("U", cut + 220, n - 220)] {
        let seg = &out[a..b];
        let rms: f32 = (seg.iter().map(|v| v * v).sum::<f32>() / seg.len() as f32).sqrt();
        let e_tot: f64 = seg.iter().map(|v| (*v as f64) * (*v as f64)).sum();
        let e_hf = band_energy(seg, 4000.0, 11025.0);
        let bedseg: Vec<f32> = bed[a..b].iter().map(|v| v * bed_g).collect();
        let be_tot: f64 = bedseg.iter().map(|v| (*v as f64) * (*v as f64)).sum();
        let be_hf = band_energy(&bedseg, 4000.0, 11025.0);
        let de_hf = e_hf - be_hf;
        let de_tot = e_tot - be_tot;
        eprintln!("{tag}: rms={rms:.5} hf_meas={:.5} no_bed_hf={:.5} bed_hf_frac_in_seg={:.5} seglen={}",
            e_hf / e_tot.max(1e-18), de_hf / de_tot.max(1e-18), be_hf / e_tot.max(1e-18), b - a);
    }
    let _ = planned;
}
