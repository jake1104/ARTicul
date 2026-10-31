use pyo3::prelude::*;
use pyo3::types::PyDict;

#[pyfunction]
fn lookup_features<'py>(py: Python<'py>, symbol: &str) -> Option<Bound<'py, PyDict>> {
    let p = articul_phon::lookup(symbol)?;
    let d = PyDict::new_bound(py);
    d.set_item("symbol", p.base_symbol.clone()).ok()?;
    d.set_item(
        "kind",
        match p.kind {
            articul_phon::SegmentKind::Consonant { .. } => "consonant",
            articul_phon::SegmentKind::Vowel { .. } => "vowel",
        },
    )
    .ok()?;
    d.set_item("place", p.place().map(|v| format!("{v:?}")))
        .ok()?;
    d.set_item("manner", p.manner().map(|v| format!("{v:?}")))
        .ok()?;
    d.set_item("voiced", p.is_voiced()).ok()?;
    d.set_item("nasal", p.is_nasal()).ok()?;
    Some(d)
}

#[pyfunction]
fn synthesize(text: &str, sample_rate: u32, f0: f32) -> Vec<f32> {
    articul_cli::render_sentence(text, sample_rate, f0)
}

#[pymodule]
fn _articul(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(lookup_features, m)?)?;
    m.add_function(wrap_pyfunction!(synthesize, m)?)?;
    Ok(())
}
