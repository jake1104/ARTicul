use articul_front::parse_utterance;
use articul_front::plan_utterance;

const SR: u32 = 22050;

#[test]
fn tmp_peak_probe() {
    for text in ["hE \"loU", "%an njVN \"hasejo", "%jV\"bo%se%jo"] {
        let words: Vec<String> = articul_front::normalize(text);
        let parsed = parse_utterance(&words);
        let planned = plan_utterance(&parsed, 1.0, 1.0, 120.0);
        let out = articul_cli::render_sentence(text, SR, 120.0);
        let mut pos = 0usize;
        let mut cum_ms = 0u32;
        let mut report = String::new();
        for (gi, u) in planned.iter().enumerate() {
            if gi > 0 {
                let fade = 176usize;
                pos -= fade.min(pos);
                let win = 221usize;
                let end = (pos + win).min(out.len());
                let mut peak = 0.0f32;
                let mut at = pos;
                for (k, v) in out[pos..end].iter().enumerate() {
                    if v.abs() > peak {
                        peak = v.abs();
                        at = pos + k;
                    }
                }
                let gpeak = out.iter().map(|v| v.abs()).fold(0.0, f32::max);
                report.push_str(&format!(
                    "{text} b{gi} t={cum_ms}ms pos={pos} argmax={at} d={} peak={peak:.6} gpeak={gpeak:.6}\n",
                    (at as i64 - pos as i64) as f32 / SR as f32 * 1000.0,
                ));
            }
            let n = ((u.duration_ms as f32 / 1000.0) * SR as f32).round().max(1.0) as usize;
            pos += n;
            cum_ms += u.duration_ms;
        }
        print!("{report}");
    }
}
