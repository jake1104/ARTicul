use articul_front::parse_utterance;
use articul_front::plan;
use articul_front::plan_utterance;
use articul_front::Stress;

fn seq(word: &str) -> (Vec<articul_phon::Phoneme>, Vec<Stress>) {
    articul_front::Xsampa::new().transcribe(word)
}

#[test]
fn plan_length_matches_input() {
    let s = seq("pin");
    let out = plan(&s.0, &s.1, 1.0, 1.0, 120.0);
    assert_eq!(out.len(), 3);
}

#[test]
fn long_vowel_gets_more_time() {
    let short = articul_phon::lookup("a").expect("a must resolve");
    let mut long = short.clone();
    long.duration.phonemic_length = articul_phon::LengthMark::Long;
    let a = plan(
        std::slice::from_ref(&short),
        &[Stress::Unstressed],
        1.0,
        1.0,
        120.0,
    );
    let b = plan(
        std::slice::from_ref(&long),
        &[Stress::Unstressed],
        1.0,
        1.0,
        120.0,
    );
    assert!(b[0].duration_ms > a[0].duration_ms);
}

#[test]
fn f0_declines_across_utterance() {
    let s = seq("pinpin");
    let out = plan(&s.0, &s.1, 1.0, 1.0, 120.0);
    assert!(out.first().expect("nonempty").f0_hz > out.last().expect("nonempty").f0_hz);
}

#[test]
fn faster_rate_shortens_durations() {
    let s = seq("pin");
    let slow = plan(&s.0, &s.1, 1.0, 1.0, 120.0);
    let fast = plan(&s.0, &s.1, 2.0, 1.0, 120.0);
    for (a, b) in slow.iter().zip(fast.iter()) {
        assert!(b.duration_ms < a.duration_ms);
    }
}

fn unstressed(n: usize) -> Vec<Stress> {
    vec![Stress::Unstressed; n]
}

#[test]
fn intrinsic_fricatives_longer_than_stops() {
    let s = articul_phon::lookup("s").expect("s must resolve");
    let t = articul_phon::lookup("t").expect("t must resolve");
    let ds = plan(std::slice::from_ref(&s), &unstressed(1), 1.0, 1.0, 120.0);
    let dt = plan(std::slice::from_ref(&t), &unstressed(1), 1.0, 1.0, 120.0);
    assert_eq!(ds[0].duration_ms, 71);
    assert_eq!(dt[0].duration_ms, 49);
    assert!(ds[0].duration_ms > dt[0].duration_ms);
    let z = articul_phon::lookup("z").expect("z must resolve");
    let d = articul_phon::lookup("d").expect("d must resolve");
    let dz = plan(std::slice::from_ref(&z), &unstressed(1), 1.0, 1.0, 120.0);
    let dd = plan(std::slice::from_ref(&d), &unstressed(1), 1.0, 1.0, 120.0);
    assert!(dz[0].duration_ms > dd[0].duration_ms);
}

#[test]
fn unstressed_segments_shorten() {
    let a = articul_phon::lookup("a").expect("a must resolve");
    let less = plan(std::slice::from_ref(&a), &unstressed(1), 1.0, 1.0, 120.0);
    let more = plan(
        std::slice::from_ref(&a),
        &[Stress::Primary],
        1.0,
        1.0,
        120.0,
    );
    assert_eq!(less[0].duration_ms, 98);
    assert_eq!(more[0].duration_ms, 179);
    let t = articul_phon::lookup("t").expect("t must resolve");
    let soft = plan(std::slice::from_ref(&t), &unstressed(1), 1.0, 1.0, 120.0);
    let loud = plan(
        std::slice::from_ref(&t),
        &[Stress::Primary],
        1.0,
        1.0,
        120.0,
    );
    assert!(soft[0].duration_ms < loud[0].duration_ms);
}

#[test]
fn pre_voiceless_obstruent_shortens_sonorant() {
    let a = articul_phon::lookup("a").expect("a must resolve");
    let t = articul_phon::lookup("t").expect("t must resolve");
    let d = articul_phon::lookup("d").expect("d must resolve");
    let before_voiceless = plan(&[a.clone(), t], &unstressed(2), 1.0, 1.0, 120.0);
    let before_voiced = plan(&[a, d], &unstressed(2), 1.0, 1.0, 120.0);
    assert_eq!(before_voiceless[0].duration_ms, 89);
    assert_eq!(before_voiced[0].duration_ms, 98);
    assert!(before_voiceless[0].duration_ms < before_voiced[0].duration_ms);
    let m = articul_phon::lookup("m").expect("m must resolve");
    let n = articul_phon::lookup("n").expect("n must resolve");
    let t2 = articul_phon::lookup("t").expect("t must resolve");
    let nasal_voiceless = plan(&[m.clone(), t2], &unstressed(2), 1.0, 1.0, 120.0);
    let nasal_voiced = plan(&[m, n], &unstressed(2), 1.0, 1.0, 120.0);
    assert!(nasal_voiceless[0].duration_ms < nasal_voiced[0].duration_ms);
}

#[test]
fn sublinear_cap_limits_combined_shortening() {
    let e = articul_phon::lookup("e").expect("e must resolve");
    let k = articul_phon::lookup("k").expect("k must resolve");
    let out = plan(&[e, k], &unstressed(2), 1.0, 1.0, 120.0);
    assert_eq!(out[0].duration_ms, 79);
}

#[test]
fn mindur_floor_holds() {
    let tap = articul_phon::lookup("ɾ").expect("tap must resolve");
    let out = plan(std::slice::from_ref(&tap), &unstressed(1), 1.0, 1.0, 120.0);
    assert_eq!(out[0].duration_ms, 30);
}

fn is_vowel(p: &articul_phon::Phoneme) -> bool {
    matches!(p.kind, articul_phon::SegmentKind::Vowel { .. })
}

#[test]
fn baseline_initial_holds_plus_2st() {
    let s = seq("pinpin");
    let out = plan(&s.0, &s.1, 1.0, 1.0, 120.0);
    let expected = 120.0 * 2f32.powf(2.0 / 12.0);
    assert!(
        (out[0].f0_hz - expected).abs() < 2.0,
        "first f0={} want ~{expected}",
        out[0].f0_hz
    );
    let lifted = 120.0 * 2f32.powf(1.43 / 12.0);
    assert!(
        (out[3].f0_hz - lifted).abs() < 3.0,
        "pre-nuclear f0={} want ~{lifted}",
        out[3].f0_hz
    );
}

#[test]
fn nuclear_accent_adds_5st_on_last_primary_vowel() {
    let p = articul_phon::lookup("p").expect("p");
    let a = articul_phon::lookup("a").expect("a");
    let seqv = vec![p.clone(), a.clone(), p.clone(), a.clone()];
    let marks = vec![
        Stress::Unstressed,
        Stress::Unstressed,
        Stress::Unstressed,
        Stress::Primary,
    ];
    let out = plan(&seqv, &marks, 1.0, 1.0, 120.0);
    let baseline_end = 120.0 * 2f32.powf(-1.0 / 12.0);
    let expected = baseline_end * 2f32.powf(5.0 / 12.0);
    assert!(
        (out[3].f0_hz - expected).abs() < 3.0,
        "nucleus f0={} want ~{expected}",
        out[3].f0_hz
    );
}

#[test]
fn post_nuclear_falls_to_minus_7st() {
    let p = articul_phon::lookup("p").expect("p");
    let a = articul_phon::lookup("a").expect("a");
    let n = articul_phon::lookup("n").expect("n");
    let seqv = vec![p.clone(), a.clone(), p.clone(), a.clone(), n.clone()];
    let marks = vec![
        Stress::Unstressed,
        Stress::Unstressed,
        Stress::Unstressed,
        Stress::Primary,
        Stress::Unstressed,
    ];
    let out = plan(&seqv, &marks, 1.0, 1.0, 120.0);
    let expected_final = 120.0 * 2f32.powf(-7.0 / 12.0);
    assert!(
        (out[4].f0_hz - expected_final).abs() < 3.0,
        "final f0={} want ~{expected_final}",
        out[4].f0_hz
    );
    assert!(
        out[3].f0_hz - out[4].f0_hz > 30.0,
        "nucleus {} must exceed post-nuclear {} by >30Hz",
        out[3].f0_hz,
        out[4].f0_hz
    );
}

#[test]
fn bare_input_defaults_nucleus_to_last_vowel() {
    let s = seq("papan");
    assert!(s.0.iter().filter(|p| is_vowel(p)).count() >= 2);
    let out = plan(&s.0, &s.1, 1.0, 1.0, 120.0);
    let mut last_vowel = 0usize;
    for (i, p) in s.0.iter().enumerate() {
        if is_vowel(p) {
            last_vowel = i;
        }
    }
    let peak = out
        .iter()
        .enumerate()
        .max_by(|a, b| a.1.f0_hz.partial_cmp(&b.1.f0_hz).unwrap())
        .map(|(i, _)| i)
        .unwrap();
    assert_eq!(
        peak, last_vowel,
        "peak must sit on last vowel for bare input"
    );
    assert!(
        out.first().unwrap().f0_hz > out.last().unwrap().f0_hz,
        "utterance must still decline overall"
    );
}

fn vowel_seq(n_pairs: usize) -> (Vec<articul_phon::Phoneme>, Vec<usize>) {
    let p = articul_phon::lookup("p").expect("p");
    let a = articul_phon::lookup("a").expect("a");
    let mut seqv = Vec::with_capacity(n_pairs * 2);
    let mut vowels = Vec::new();
    for _ in 0..n_pairs {
        seqv.push(p.clone());
        vowels.push(seqv.len());
        seqv.push(a.clone());
    }
    (seqv, vowels)
}

#[test]
fn prenuclear_primary_adds_3st() {
    let (seqv, vowels) = vowel_seq(3);
    let mut marks = vec![Stress::Unstressed; seqv.len()];
    marks[vowels[0]] = Stress::Primary;
    marks[vowels[2]] = Stress::Primary;
    let out = plan(&seqv, &marks, 1.0, 1.0, 120.0);
    let expected = 120.0 * 2f32.powf(5.0 / 12.0);
    assert!(
        (out[vowels[0]].f0_hz - expected).abs() < 4.0,
        "first accent f0={} want ~{expected}",
        out[vowels[0]].f0_hz
    );
}

#[test]
fn downstep_lowers_each_following_accent_by_1_5st() {
    let (seqv, vowels) = vowel_seq(3);
    let mut marks = vec![Stress::Unstressed; seqv.len()];
    marks[vowels[0]] = Stress::Primary;
    marks[vowels[1]] = Stress::Primary;
    marks[vowels[2]] = Stress::Primary;
    let out = plan(&seqv, &marks, 1.0, 1.0, 120.0);
    let ratio = out[vowels[0]].f0_hz / out[vowels[1]].f0_hz;
    let expected = 2f32.powf(2.75 / 12.0);
    assert!(
        (ratio - expected).abs() < 0.03,
        "downstep ratio={ratio} want ~{expected}"
    );
    assert!(
        out[vowels[0]].f0_hz > out[vowels[1]].f0_hz,
        "accents must step down"
    );
}

#[test]
fn secondary_accent_adds_1_5st() {
    let (seqv, vowels) = vowel_seq(3);
    let mut marks = vec![Stress::Unstressed; seqv.len()];
    marks[vowels[0]] = Stress::Secondary;
    marks[vowels[2]] = Stress::Primary;
    let out = plan(&seqv, &marks, 1.0, 1.0, 120.0);
    let expected = 120.0 * 2f32.powf(3.5 / 12.0);
    assert!(
        (out[vowels[0]].f0_hz - expected).abs() < 4.0,
        "secondary f0={} want ~{expected}",
        out[vowels[0]].f0_hz
    );
}

#[test]
fn phrase_reset_at_pipe_boundary() {
    let words = vec!["papapapa|".to_string(), "papapap".to_string()];
    let parsed = parse_utterance(&words);
    let out = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    assert_eq!(out.len(), 16);
    assert!(out[8].is_pause);
    assert!(
        out[10].f0_hz > out[7].f0_hz,
        "reset must lift word2 onset above word1 close: {} vs {}",
        out[9].f0_hz,
        out[7].f0_hz
    );
    assert!(
        out.first().unwrap().f0_hz > out.last().unwrap().f0_hz,
        "utterance must still decline overall"
    );
}

#[test]
fn space_keeps_single_phrase() {
    let words = vec!["papapapa".to_string(), "papapapa".to_string()];
    let parsed = parse_utterance(&words);
    let out = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    assert!(
        out[9].f0_hz < out[7].f0_hz,
        "no break at space: {} vs {}",
        out[9].f0_hz,
        out[7].f0_hz
    );
}

#[test]
fn accent_tail_decays_after_nucleus() {
    let a = articul_phon::lookup("a").expect("a");
    let p = articul_phon::lookup("p").expect("p");
    let n = articul_phon::lookup("n").expect("n");
    let seqv = vec![a.clone(), p, a, n];
    let marks = vec![
        Stress::Primary,
        Stress::Unstressed,
        Stress::Unstressed,
        Stress::Unstressed,
    ];
    let out = plan(&seqv, &marks, 1.0, 1.0, 120.0);
    let expected = 120.0 * 2f32.powf(11.0 / 12.0 / 12.0);
    assert!(
        (out[2].f0_hz - expected).abs() < 4.0,
        "tail f0={} want ~{expected}",
        out[2].f0_hz
    );
    assert!(
        out[2].f0_hz > out[3].f0_hz,
        "tail must sit above final fall"
    );
}

#[test]
fn phrase_decay_is_convex_not_linear() {
    let s = seq("ptptpt");
    let out = plan(&s.0, &s.1, 1.0, 1.0, 120.0);
    assert_eq!(out.len(), 6);
    let expected = 120.0 * 2f32.powf(-0.628 / 12.0);
    assert!(
        (out[4].f0_hz - expected).abs() < 2.0,
        "mid-phrase f0={} want ~{expected}",
        out[4].f0_hz
    );
}

#[test]
fn accent_attack_starts_before_the_vowel() {
    let a = articul_phon::lookup("a").expect("a");
    let seqv = vec![a.clone(), a];
    let marks = vec![Stress::Unstressed, Stress::Primary];
    let out = plan(&seqv, &marks, 1.0, 1.0, 120.0);
    let expected = 120.0 * 2f32.powf(3.5 / 12.0);
    assert!(
        (out[0].f0_hz - expected).abs() < 3.0,
        "anticipation f0={} want ~{expected}",
        out[0].f0_hz
    );
}

#[test]
fn f0_end_matches_next_start() {
    let s = seq("papan");
    let out = plan(&s.0, &s.1, 1.0, 1.0, 120.0);
    for i in 0..out.len() - 1 {
        assert!(
            (out[i].f0_end_hz - out[i + 1].f0_hz).abs() < 1e-4,
            "end {i} must meet start of next"
        );
    }
    let last = out.last().unwrap();
    assert!(
        (last.f0_end_hz - last.f0_hz).abs() < 1e-4,
        "final segment must end flat"
    );
}
