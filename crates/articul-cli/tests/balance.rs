use articul_front::parse_utterance;
use articul_front::plan_utterance;

fn word_bounds(words: &[String], sample_rate: u32) -> Vec<(usize, usize)> {
    let parsed = parse_utterance(words);
    let planned = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    let mut lens: Vec<usize> = Vec::with_capacity(planned.len());
    for u in &planned {
        lens.push(
            ((u.duration_ms as f32 / 1000.0) * sample_rate as f32)
                .round()
                .max(1.0) as usize,
        );
    }
    let mut bounds = Vec::new();
    let mut pos = 0usize;
    let mut wstart = 0usize;
    let mut idx = 0usize;
    for (wi, w) in parsed.iter().enumerate() {
        for (k, _) in w.phonemes.iter().enumerate() {
            if k > 0 {
                let prev_vowel = matches!(
                    w.phonemes[k - 1].kind,
                    articul_phon::SegmentKind::Vowel { .. }
                );
                let cur_vowel =
                    matches!(w.phonemes[k].kind, articul_phon::SegmentKind::Vowel { .. });
                let fade = if prev_vowel && cur_vowel { 1102 } else { 176 };
                pos -= fade.min(pos);
            } else if wi > 0 {
                let prev_last = &parsed[wi - 1].phonemes;
                let prev_vowel = prev_last
                    .last()
                    .map(|p| matches!(p.kind, articul_phon::SegmentKind::Vowel { .. }))
                    .unwrap_or(false);
                let cur_vowel =
                    matches!(w.phonemes[k].kind, articul_phon::SegmentKind::Vowel { .. });
                let fade = if prev_vowel && cur_vowel { 1102 } else { 176 };
                pos -= fade.min(pos);
            }
            pos += lens[idx];
            idx += 1;
        }
        bounds.push((wstart, pos));
        wstart = pos;
    }
    bounds
}

fn rms_db(x: &[f32]) -> f32 {
    let r = (x.iter().map(|v| v * v).sum::<f32>() / x.len().max(1) as f32).sqrt();
    20.0 * r.max(1e-9).log10()
}

fn word_db(out: &[f32], start: usize, end: usize) -> f32 {
    let s = (start + 300).min(out.len());
    let e = end.saturating_sub(300).max(s + 1).min(out.len());
    rms_db(&out[s..e])
}

#[test]
fn demo_meets_word_balance() {
    let words = vec!["hE".to_string(), "\"loU".to_string()];
    let out = articul_cli::render_sentence("hE \"loU", 22050, 120.0);
    let bounds = word_bounds(&words, 22050);
    assert_eq!(bounds.len(), 2);
    let db0 = word_db(&out, bounds[0].0, bounds[0].1);
    let db1 = word_db(&out, bounds[1].0, bounds[1].1);
    assert!(db1 - db0 >= -6.0, "word balance {db1:.1}dB vs {db0:.1}dB");
}

#[test]
fn stressed_nucleus_holds_at_least_100ms() {
    let words = vec!["hE".to_string(), "\"loU".to_string()];
    let parsed = parse_utterance(&words);
    let planned = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    let mut flat_idx = 0usize;
    let mut nucleus_ms = 0u32;
    for w in &parsed {
        for (k, p) in w.phonemes.iter().enumerate() {
            let is_vowel = matches!(p.kind, articul_phon::SegmentKind::Vowel { .. });
            let stressed = w
                .stress
                .get(k)
                .copied()
                .unwrap_or(articul_front::Stress::Unstressed)
                != articul_front::Stress::Unstressed;
            if is_vowel && stressed {
                nucleus_ms = nucleus_ms.max(planned[flat_idx].duration_ms);
            }
            flat_idx += 1;
        }
    }
    assert!(nucleus_ms >= 100, "nucleus {nucleus_ms}ms");
}

#[test]
fn old_input_violates_word_balance() {
    let words = vec!["\"hE".to_string(), "l@U".to_string()];
    let out = articul_cli::render_sentence("\"hE l@U", 22050, 120.0);
    let bounds = word_bounds(&words, 22050);
    assert_eq!(bounds.len(), 2);
    let db0 = word_db(&out, bounds[0].0, bounds[0].1);
    let db1 = word_db(&out, bounds[1].0, bounds[1].1);
    assert!(
        db1 - db0 < -6.0,
        "old input must violate the gate, got {db1:.1}dB vs {db0:.1}dB"
    );
}
