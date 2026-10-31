use articul_front::normalize;
use articul_front::plan;
use articul_front::Xsampa;

fn pipeline(text: &str) -> Vec<articul_front::prosody::ProsodicPhoneme> {
    let g = Xsampa::new();
    let mut seq = Vec::new();
    let mut marks = Vec::new();
    for w in normalize(text) {
        let (mut ph, mut st) = g.transcribe(&w);
        seq.append(&mut ph);
        marks.append(&mut st);
    }
    plan(&seq, &marks, 1.0, 1.0, 120.0)
}

#[test]
fn sentence_produces_phonemes_with_prosody() {
    let out = pipeline("hi DEn");
    assert_eq!(out.len(), 5);
    assert!(out.iter().all(|u| u.duration_ms >= 10));
    assert!(out.iter().all(|u| u.f0_hz > 0.0));
}

#[test]
fn digits_do_not_break_pipeline() {
    let out = pipeline("a1 DEn");
    assert!(!out.is_empty());
}
