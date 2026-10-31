use articul_front::parse_utterance;
use articul_front::plan;
use articul_front::plan_utterance;
use articul_front::Stress;
use articul_front::WordProsody;

fn phonemes_of(word: &str) -> (Vec<articul_phon::Phoneme>, Vec<Stress>) {
    articul_front::Xsampa::new().transcribe(word)
}

fn primary(n: usize) -> Vec<Stress> {
    vec![Stress::Primary; n]
}

fn single_word(word: &str, marks: Vec<Stress>, boundary: f32) -> WordProsody {
    let (seqv, _) = phonemes_of(word);
    WordProsody {
        phonemes: seqv,
        stress: marks,
        boundary_after: boundary,
        function_word: false,
        emphasized: false,
    }
}

#[test]
fn final_rhyme_uses_strong_tier() {
    let w = single_word("pan", primary(3), 1.0);
    let out = plan_utterance(std::slice::from_ref(&w), 1.0, 1.0, 120.0);
    assert_eq!(out.len(), 3);
    assert_eq!(out[1].duration_ms, 246);
    assert_eq!(out[2].duration_ms, 120);
}

#[test]
fn comma_rhyme_uses_weak_tier() {
    let w = single_word("pan", primary(3), 0.4);
    let out = plan_utterance(std::slice::from_ref(&w), 1.0, 1.0, 120.0);
    assert_eq!(out[1].duration_ms, 217);
    assert_eq!(out[2].duration_ms, 107);
}

#[test]
fn word_initial_consonant_lengthened() {
    let words = vec!["pa".to_string()];
    let parsed = parse_utterance(&words);
    let out = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    assert!(out[0].duration_ms >= 52 && out[0].duration_ms <= 58);
}

#[test]
fn slow_rate_compresses_sublinearly() {
    let a = articul_phon::lookup("a").expect("a");
    let seqv = vec![a];
    let marks = vec![Stress::Unstressed];
    let out = plan(&seqv, &marks, 0.5, 1.0, 120.0);
    assert!(out[0].duration_ms > 170 && out[0].duration_ms < 185);
}

#[test]
fn no_lengthening_without_boundary() {
    let w = single_word("a", primary(1), 0.0);
    let out = plan_utterance(std::slice::from_ref(&w), 1.0, 1.0, 120.0);
    let flat = plan(&w.phonemes, &w.stress, 1.0, 1.0, 120.0);
    assert_eq!(out.len(), flat.len());
    for (a, b) in out.iter().zip(flat.iter()) {
        assert_eq!(a.duration_ms, b.duration_ms);
    }
}

#[test]
fn cluster_shortens_non_initial_consonants() {
    let w = single_word("split", primary(5), 0.0);
    let out = plan_utterance(std::slice::from_ref(&w), 1.0, 1.0, 120.0);
    assert_eq!(out[0].duration_ms, 142);
    assert_eq!(out[1].duration_ms, 76);
    assert_eq!(out[2].duration_ms, 74);
}

#[test]
fn single_onset_keeps_full_duration() {
    let w = single_word("pan", primary(3), 0.0);
    let out = plan_utterance(std::slice::from_ref(&w), 1.0, 1.0, 120.0);
    assert_eq!(out[0].duration_ms, 98);
}

#[test]
fn disyllabic_word_gets_0_9() {
    let w = single_word("pana", primary(4), 0.0);
    let out = plan_utterance(std::slice::from_ref(&w), 1.0, 1.0, 120.0);
    assert_eq!(out[1].duration_ms, 170);
    assert_eq!(out[3].duration_ms, 167);
}

#[test]
fn trisyllabic_word_gets_0_8() {
    let w = single_word("panana", primary(6), 0.0);
    let out = plan_utterance(std::slice::from_ref(&w), 1.0, 1.0, 120.0);
    assert_eq!(out[1].duration_ms, 151);
    assert_eq!(out[3].duration_ms, 148);
    assert_eq!(out[5].duration_ms, 145);
}

#[test]
fn function_word_shortens_unless_emphasized() {
    let words = vec!["D@".to_string(), "k{t".to_string()];
    let parsed = parse_utterance(&words);
    assert_eq!(parsed.len(), 2);
    assert!(parsed[0].function_word);
    assert!(!parsed[0].emphasized);
    assert!(!parsed[1].function_word);
    let out = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    assert_eq!(out[0].duration_ms, 53);
    assert_eq!(out[1].duration_ms, 46);
    let loud = vec!["\"D@".to_string()];
    let parsed_loud = parse_utterance(&loud);
    assert!(parsed_loud[0].function_word);
    assert!(parsed_loud[0].emphasized);
    let (tseq, _) = phonemes_of("tu");
    let plain = WordProsody {
        phonemes: tseq.clone(),
        stress: vec![Stress::Unstressed, Stress::Unstressed],
        boundary_after: 0.0,
        function_word: true,
        emphasized: false,
    };
    let loud_word = WordProsody {
        phonemes: tseq,
        stress: vec![Stress::Unstressed, Stress::Primary],
        boundary_after: 0.0,
        function_word: true,
        emphasized: true,
    };
    let out_plain = plan_utterance(std::slice::from_ref(&plain), 1.0, 1.0, 120.0);
    let out_loud = plan_utterance(std::slice::from_ref(&loud_word), 1.0, 1.0, 120.0);
    assert_eq!(out_plain[0].duration_ms, 43);
    assert_eq!(out_plain[1].duration_ms, 72);
    assert_eq!(out_loud[0].duration_ms, 54);
    assert_eq!(out_loud[1].duration_ms, 163);
}

#[test]
fn comma_inserts_160ms_pause() {
    let words = vec!["a,".to_string(), "pa".to_string()];
    let parsed = parse_utterance(&words);
    let out = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    assert_eq!(out.len(), 4);
    assert!(out[1].is_pause);
    assert_eq!(out[1].duration_ms, 160);
    assert!(!out[0].is_pause && !out[2].is_pause && !out[3].is_pause);
}

#[test]
fn durations_are_deterministic() {
    let words = vec!["hE".to_string(), "\"loU".to_string()];
    let parsed = parse_utterance(&words);
    let a = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    let b = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    assert_eq!(
        a.iter().map(|u| u.duration_ms).collect::<Vec<_>>(),
        b.iter().map(|u| u.duration_ms).collect::<Vec<_>>()
    );
}

#[test]
fn variance_stays_within_six_percent() {
    let a = articul_phon::lookup("a").expect("a");
    let seqv = vec![a.clone(), a.clone(), a.clone(), a.clone(), a.clone(), a];
    let marks = vec![Stress::Unstressed; 6];
    let out = plan(&seqv, &marks, 1.0, 1.0, 120.0);
    for u in &out {
        let base = 180.0 * 0.55;
        assert!(
            (u.duration_ms as f32 - base).abs() <= 0.07 * base + 1.0,
            "duration {} out of variance bound",
            u.duration_ms
        );
    }
}

#[test]
fn rate_compresses_sublinearly() {
    let a = articul_phon::lookup("a").expect("a");
    let seqv = vec![a];
    let marks = vec![Stress::Unstressed];
    let slow = plan(&seqv, &marks, 1.0, 1.0, 120.0);
    let fast = plan(&seqv, &marks, 2.0, 1.0, 120.0);
    assert!(fast[0].duration_ms < slow[0].duration_ms);
    assert!(
        fast[0].duration_ms > 50,
        "must compress less than linear halving, got {}",
        fast[0].duration_ms
    );
    assert!(fast[0].duration_ms <= 60);
}

#[test]
fn utterance_f0_matches_flat_plan() {
    let words = vec!["\"papa".to_string(), "papan".to_string()];
    let parsed = parse_utterance(&words);
    let out = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    let mut flat_seq = Vec::new();
    let mut flat_marks = Vec::new();
    for w in &parsed {
        flat_seq.extend(w.phonemes.iter().cloned());
        flat_marks.extend(w.stress.iter().copied());
    }
    let flat = plan(&flat_seq, &flat_marks, 1.0, 1.0, 120.0);
    assert_eq!(out.len(), flat.len());
    for (a, b) in out.iter().zip(flat.iter()) {
        assert!((a.f0_hz - b.f0_hz).abs() < 1e-4);
    }
}
