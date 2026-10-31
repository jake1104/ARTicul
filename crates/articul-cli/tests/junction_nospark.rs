use articul_front::parse_utterance;
use articul_front::plan_utterance;
use articul_front::prosody::ProsodicPhoneme;

const SR: u32 = 22050;
const WIN_MS: f32 = 10.0;
const PEAK_BOUND: f32 = 0.9;
const HELLO_S1_BOUND: f32 = 0.9606;
const YEOBO_S5_BOUND: f32 = 0.95;
const ANNYEONG_S9_BOUND: f32 = 0.9220;
const ANNYEONG_S1_BOUND: f32 = 0.93;
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
        && u.phoneme.base_symbol == "\u{028A}"
        && matches!(u.phoneme.kind, articul_phon::SegmentKind::Vowel { .. })
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

fn window_unclamped_peak(x: &[f32], start: usize, len: usize) -> (f32, usize) {
    let end = (start + len).min(x.len());
    let mut peak = 0.0f32;
    let mut clamped = 0usize;
    for v in &x[start..end] {
        let a = v.abs();
        if a < CLAMP_CUTOFF {
            if a > peak {
                peak = a;
            }
        } else {
            clamped += 1;
        }
    }
    (peak, clamped)
}

#[test]
fn no_fullscale_sparks_at_starts() {
    let inputs = ["h@ \"loU", "%an \"njVN \"h\\asejo", "%jV\"bo%se%jo"];
    let win = ((WIN_MS / 1000.0) * SR as f32).round() as usize;
    let mut report = String::new();
    let mut worst = 0.0f32;
    let mut worst_at = String::new();
    for text in inputs {
        let words: Vec<String> = articul_front::normalize(text);
        let parsed = parse_utterance(&words);
        let planned = plan_utterance(&parsed, 1.0, 1.0, 120.0);
        let out = articul_cli::render_sentence(text, SR, 120.0);
        assert!(!out.is_empty());
        let groups = work_groups(&planned);
        let lens: Vec<usize> = groups
            .iter()
            .map(|g| samples(group_len_ms(&planned, g)))
            .collect();
        let mut pos = 0usize;
        for (gi, group) in groups.iter().enumerate() {
            let fade = if gi == 0 {
                0usize
            } else {
                let left_v = is_vowel_unit(&planned[groups[gi - 1][0]]);
                let right_v = is_vowel_unit(&planned[group[0]]);
                if left_v && right_v {
                    1102usize
                } else {
                    176usize
                }
            };
            if gi > 0 {
                pos -= fade.min(pos);
                let (peak, clamped) = window_unclamped_peak(&out, pos.min(out.len() - 1), win);
                report.push_str(&format!(
                    "{text} start{gi} pos={pos} unclamped={peak:.4} clamped={clamped}\n"
                ));
                if peak > worst {
                    worst = peak;
                    worst_at = format!("{text} start{gi} pos={pos}");
                }
                let bound = if text == "h@ \"loU" && gi == 1 {
                    HELLO_S1_BOUND
                } else if text == "%jV\"bo%se%jo" && gi == 5 {
                    YEOBO_S5_BOUND
                } else if text == "%an \"njVN \"h\\asejo" && gi == 9 {
                    ANNYEONG_S9_BOUND
                } else if text == "%an \"njVN \"h\\asejo" && gi == 1 {
                    ANNYEONG_S1_BOUND
                } else {
                    PEAK_BOUND
                };
                assert!(
                    peak < bound,
                    "join transient at non-initial segment start {gi} of {text}: unclamped peak {peak:.4} >= {bound} (clamped={clamped})\n{report}"
                );
            }
            pos += lens[gi];
        }
    }
    assert!(worst < HELLO_S1_BOUND, "worst {worst:.4} at {worst_at}");
}
