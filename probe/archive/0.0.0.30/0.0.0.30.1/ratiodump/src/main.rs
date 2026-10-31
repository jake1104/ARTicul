// Probe: apa rendered ratio under the TEST's bespoke marks
// (Primary, Unstressed, Unstressed), mirroring gain.rs exactly.
use articul_front::{plan, Stress};
use articul_front::Xsampa;

fn rms(x: &[f32]) -> f32 {
    (x.iter().map(|v| v * v).sum::<f32>() / x.len().max(1) as f32).sqrt()
}

fn main() {
    let word = "apa";
    let marks = vec![Stress::Primary, Stress::Unstressed, Stress::Unstressed];
    let (seq, _) = Xsampa::new().transcribe(word);
    assert_eq!(seq.len(), marks.len());
    let planned = plan(&seq, &marks, 1.0, 1.0, 120.0);
    for (i, u) in planned.iter().enumerate() {
        println!(
            "u{} gain={:.4}dB dur={}ms stress={:?}",
            i,
            articul_cli::segment_gain_db(u, i, planned.len()),
            u.duration_ms,
            u.stress
        );
    }
    let out = articul_cli::render_planned(&planned, 22050);
    let mut starts = Vec::with_capacity(planned.len() + 1);
    let mut pos = 0usize;
    for (idx, u) in planned.iter().enumerate() {
        if idx > 0 {
            let f = 176usize;
            pos -= f.min(pos);
        }
        starts.push(pos);
        pos += ((u.duration_ms as f32 / 1000.0) * 22050.0).round() as usize;
    }
    let w0 = &out[starts[0] + 500..starts[0] + 1500];
    let w2 = &out[starts[2] + 300..starts[2] + 1300];
    let ratio = rms(w0) / rms(w2).max(1e-9);
    println!("samples={} ratio={:.4} {}", out.len(), ratio, if ratio > 1.8 { "PASS" } else { "FAIL" });
    let bytes: Vec<u8> = out.iter().flat_map(|v| v.to_le_bytes()).collect();
    std::fs::write("probe/0.0.0.30.1/apa_testplan.f32", &bytes).unwrap();
}
