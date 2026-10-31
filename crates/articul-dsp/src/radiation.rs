pub fn apply_radiation(input: &[f32]) -> Vec<f32> {
    let mut out = Vec::with_capacity(input.len());
    let mut prev = 0.0;
    for &x in input {
        out.push(x - 0.97 * prev);
        prev = x;
    }
    out
}
