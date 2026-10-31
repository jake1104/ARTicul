use articul_front::plan;
use articul_front::Stress;
use articul_front::Xsampa;

fn stress_of(word: &str) -> (Vec<articul_phon::Phoneme>, Vec<Stress>) {
    Xsampa::new().transcribe(word)
}

#[test]
fn primary_stress_attaches_to_following_vowel() {
    let (seq, marks) = stress_of("\"h@lu");
    assert_eq!(seq.len(), 4);
    assert_eq!(seq[0].base_symbol, "h");
    assert_eq!(seq[1].base_symbol, "ə");
    assert_eq!(
        marks,
        vec![
            Stress::Unstressed,
            Stress::Primary,
            Stress::Unstressed,
            Stress::Unstressed,
        ]
    );
}

#[test]
fn each_marker_attaches_to_its_own_vowel() {
    let (seq, marks) = stress_of("\"h@\"loU");
    assert_eq!(seq.len(), 5);
    assert_eq!(
        marks,
        vec![
            Stress::Unstressed,
            Stress::Primary,
            Stress::Unstressed,
            Stress::Primary,
            Stress::Unstressed,
        ]
    );
}

#[test]
fn consonants_before_vowel_get_no_stress() {
    let (seq, marks) = stress_of("\"stra");
    assert_eq!(seq.len(), 4);
    assert_eq!(
        marks,
        vec![
            Stress::Unstressed,
            Stress::Unstressed,
            Stress::Unstressed,
            Stress::Primary,
        ]
    );
}

#[test]
fn secondary_stress_marks_following_vowel() {
    let (seq, marks) = stress_of("%lo");
    assert_eq!(seq.len(), 2);
    assert_eq!(marks, vec![Stress::Unstressed, Stress::Secondary]);
}

#[test]
fn trailing_marker_without_vowel_is_dropped() {
    let (seq, marks) = stress_of("\"p");
    assert_eq!(seq.len(), 1);
    assert_eq!(marks, vec![Stress::Unstressed]);
    let (seq2, marks2) = stress_of("\"%");
    assert!(seq2.is_empty());
    assert!(marks2.is_empty());
}

#[test]
fn last_marker_wins() {
    let (seq, marks) = stress_of("\"%a");
    assert_eq!(seq.len(), 1);
    assert_eq!(marks, vec![Stress::Secondary]);
}

#[test]
fn marker_after_base_attaches_to_later_vowel() {
    let (seq, marks) = stress_of("a\"bi");
    assert_eq!(seq.len(), 3);
    assert_eq!(
        marks,
        vec![Stress::Unstressed, Stress::Unstressed, Stress::Primary]
    );
}

#[test]
fn plan_carries_stress_through() {
    let (seq, _) = stress_of("\"h@\"loU");
    let marks = vec![
        Stress::Unstressed,
        Stress::Primary,
        Stress::Unstressed,
        Stress::Unstressed,
        Stress::Unstressed,
    ];
    let out = plan(&seq, &marks, 1.0, 1.0, 120.0);
    assert_eq!(out.len(), 5);
    for (u, m) in out.iter().zip(marks.iter()) {
        assert_eq!(u.stress, *m);
    }
}

#[test]
fn plan_defaults_missing_stress_to_unstressed() {
    let (seq, _) = stress_of("pin");
    let out = plan(&seq, &[], 1.0, 1.0, 120.0);
    assert_eq!(out.len(), 3);
    assert!(out.iter().all(|u| u.stress == Stress::Unstressed));
    assert!(out.iter().all(|u| u.duration_ms >= 10));
    assert!(out.iter().all(|u| u.f0_hz > 0.0));
}
