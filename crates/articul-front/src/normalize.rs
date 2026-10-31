pub fn normalize(text: &str) -> Vec<String> {
    text.split_whitespace()
        .filter(|w| !w.is_empty())
        .map(str::to_string)
        .collect()
}
