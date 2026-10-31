fn rms(x: &[f32]) -> f32 {
    (x.iter().map(|v| v * v).sum::<f32>() / x.len().max(1) as f32).sqrt()
}

fn peak(x: &[f32]) -> f32 {
    x.iter().map(|v| v.abs()).fold(0.0, f32::max)
}

fn render(text: &str) -> Vec<f32> {
    articul_cli::render_sentence(text, 22050, 120.0)
}

fn trough_max_db(x: &[f32], sr: u32) -> f32 {
    let w = (sr / 100) as usize;
    let mut nrms = Vec::new();
    let mut i = 0usize;
    while i < x.len() {
        let e = (i + w).min(x.len());
        nrms.push(rms(&x[i..e]));
        i = e;
    }
    let prev = 10usize;
    let end = nrms.len().saturating_sub(15);
    let mut worst = 0.0f32;
    for k in prev..end {
        let ctx: f32 = nrms[k - prev..k].iter().sum::<f32>() / prev as f32;
        if ctx <= 1e-9 || nrms[k] <= 1e-9 {
            continue;
        }
        let d = 20.0 * (nrms[k] / ctx).log10();
        if d < worst {
            worst = d;
        }
    }
    worst
}

const INPUTS: [&str; 3] = ["hE \"loU", "%an njVN \"hasejo", "%jV\"bo%se%jo"];

#[test]
fn demo_rms_audible() {
    for text in INPUTS {
        let out = render(text);
        assert!(!out.is_empty());
        let g = rms(&out);
        let p = peak(&out);
        assert!(g >= 0.10, "rms {g:.4} < 0.10 for {text}");
        assert!(p <= 0.99, "peak {p:.4} > 0.99 for {text}");
    }
}

#[test]
fn intra_word_troughs_bounded() {
    for text in &INPUTS[1..] {
        let out = render(text);
        let worst = trough_max_db(&out, 22050);
        assert!(
            worst >= -14.0,
            "trough {worst:.1}dB deeper than -14dB for {text}"
        );
    }
}

#[test]
fn tail_not_buried() {
    let out = render("%jV\"bo%se%jo");
    let n3 = out.len() / 3;
    let t = rms(&out[2 * n3..]);
    assert!(t >= 0.03, "yeobo tail rms {t:.4} < 0.03");
}
