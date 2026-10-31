// f32 dump for task 0.0.0.28.1 (read-only probe, no engine change).
// Renders via articul_cli::render_sentence (f32, no i16 quantization) and
// mirrors the junction_nospark_red2.rs window logic exactly.

use articul_front::parse_utterance;
use articul_front::plan_utterance;
use articul_front::prosody::ProsodicPhoneme;

const SR: u32 = 22050;
const WIN_MS: f32 = 10.0;
const PEAK_BOUND: f32 = 0.9;
const CLAMP_CUTOFF: f32 = 0.985;

fn is_vowel_unit(u: &ProsodicPhoneme) -> bool {
    matches!(u.phoneme.kind, articul_phon::SegmentKind::Vowel { .. })
}

fn is_goat_onset(u: &ProsodicPhoneme) -> bool {
    !u.is_pause
        && u.stress != articul_front::Stress::Unstressed
        && u.phoneme.base_symbol == "o"
        && matches!(
            u.phoneme.kind,
            articul_phon::SegmentKind::Vowel { rounded: true, .. }
        )
}

fn is_goat_offglide(u: &ProsodicPhoneme) -> bool {
    !u.is_pause
        && u.stress == articul_front::Stress::Unstressed
        && u.phoneme.base_symbol == "\u{28a}"
        && matches!(
            u.phoneme.kind,
            articul_phon::SegmentKind::Vowel { .. }
        )
}

fn work_groups(planned: &[ProsodicPhoneme]) -> Vec<Vec<usize>> {
    let mut groups: Vec<Vec<usize>> = Vec::new();
    let mut i = 0usize;
    while i < planned.len() {
        if i + 1 < planned.len() && is_goat_onset(&planned[i]) && is_goat_offglide(&planned[i + 1])
        {
            groups.push(vec![i, i + 1]);
            i += 2;
        } else {
            groups.push(vec![i]);
            i += 1;
        }
    }
    groups
}

fn group_len_ms(planned: &[ProsodicPhoneme], group: &[usize]) -> u32 {
    group.iter().map(|oi| planned[*oi].duration_ms).sum()
}

fn samples(ms: u32) -> usize {
    ((ms as f32 / 1000.0) * SR as f32).round().max(1.0) as usize
}

fn dump(text: &str, label: &str, outdir: &str) {
    let words: Vec<String> = articul_front::normalize(text);
    let parsed = parse_utterance(&words);
    let planned = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    let out = articul_cli::render_sentence(text, SR, 120.0);
    let path = format!("{}/{}.f32", outdir, label);
    let bytes: Vec<u8> = out.iter().flat_map(|v| v.to_le_bytes()).collect();
    std::fs::write(&path, &bytes).unwrap();
    let win = ((WIN_MS / 1000.0) * SR as f32).round() as usize;
    let groups = work_groups(&planned);
    let lens: Vec<usize> = groups
        .iter()
        .map(|g| samples(group_len_ms(&planned, g)))
        .collect();
    println!("== {} n={} groups={}", label, out.len(), groups.len());
    let mut pos = 0usize;
    for (gi, group) in groups.iter().enumerate() {
        let fade = if gi == 0 {
            0usize
        } else {
            let left_v = is_vowel_unit(&planned[groups[gi - 1][0]]);
            let right_v = is_vowel_unit(&planned[group[0]]);
            if left_v && right_v { 1102usize } else { 176usize }
        };
        if gi > 0 {
            pos -= fade.min(pos);
            let end = (pos + win).min(out.len());
            let mut peak = 0.0f32;
            let mut clamped = 0usize;
            for v in &out[pos..end] {
                let a = v.abs();
                if a < CLAMP_CUTOFF {
                    if a > peak {
                        peak = a;
                    }
                } else {
                    clamped += 1;
                }
            }
            println!(
                "start{} pos={} unclamped={:.6} clamped={} {}",
                gi,
                pos,
                peak,
                clamped,
                if peak >= PEAK_BOUND { "SPARK" } else { "ok" }
            );
        }
        pos += lens[gi];
    }
}

fn main() {
    let outdir = std::env::args().nth(1).expect("outdir arg");
    dump("TIs TIN", "fixed_sentence", &outdir);
    dump("hE \"loU", "demo_hello", &outdir);
    dump("\"ma", "creak_probe", &outdir);
    dump("apa", "gain_probe", &outdir);
    dump("\"sprit", "cluster_probe", &outdir);
    dump("a, pa", "pause_probe", &outdir);
    dump("%an njVN \"hasejo", "annyeong", &outdir);
    dump("%jV\"bo%se%jo", "yeobo", &outdir);
    dump("\"hE l@U", "old_input", &outdir);
}
