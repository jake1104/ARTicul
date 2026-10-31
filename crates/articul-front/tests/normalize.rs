use articul_front::normalize;

#[test]
fn splits_on_whitespace() {
    assert_eq!(normalize("hi DEn"), vec!["hi", "DEn"]);
}

#[test]
fn preserves_case() {
    assert_eq!(normalize("S N T s n t"), vec!["S", "N", "T", "s", "n", "t"]);
}

#[test]
fn drops_empty_input() {
    assert!(normalize("   ").is_empty());
}

#[test]
fn keeps_punctuation_for_transcriber() {
    assert_eq!(normalize("hi, DEn."), vec!["hi,", "DEn."]);
}
