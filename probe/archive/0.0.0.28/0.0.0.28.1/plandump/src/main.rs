// Plan + gain-arm dump for task 0.0.0.28.1 (read-only probe, no engine change).
// Prints per-segment: engine segment_gain_db value plus probe-side arm
// decomposition (base arm, declination, final, floor) with an equality check.

use articul_front::{plan_utterance, Stress};
use articul_phon::{Manner, Place, SegmentKind};

const SR: u32 = 22050;

fn is_vowel(p: &articul_phon::Phoneme) -> bool {
    matches!(p.kind, SegmentKind::Vowel { .. })
}

fn arm_of(
    u: &articul_front::prosody::ProsodicPhoneme,
    index: usize,
    total: usize,
) -> (String, f32, f32, f32, bool) {
    let mut base: f32;
    let arm: String;
    match &u.phoneme.kind {
        SegmentKind::Vowel { .. } => match u.stress {
            Stress::Unstressed => {
                base = -3.5;
                arm = "unstressed-vowel".to_string();
            }
            Stress::Secondary | Stress::Primary => {
                base = 0.0;
                arm = "stressed-vowel".to_string();
            }
        },
        SegmentKind::Consonant { place, manner } => match manner {
            Manner::Nasal => {
                base = -8.0;
                arm = "nasal".to_string();
            }
            Manner::Approximant
            | Manner::LateralApproximant
            | Manner::Trill
            | Manner::TapFlap => {
                base = -7.0;
                arm = "approximant".to_string();
            }
            Manner::Fricative => {
                let b = if matches!(u.phoneme.place(), Some(Place::Glottal))
                    && !u.phoneme.is_voiced()
                {
                    -10.0
                } else {
                    match place {
                        Place::Alveolar | Place::Postalveolar | Place::Retroflex => -5.0,
                        _ => -18.0,
                    }
                };
                let tag = if matches!(u.phoneme.place(), Some(Place::Glottal))
                    && !u.phoneme.is_voiced()
                {
                    "h-fric"
                } else {
                    match place {
                        Place::Alveolar | Place::Postalveolar | Place::Retroflex => "sibilant",
                        _ => "weak-fric",
                    }
                };
                base = b;
                arm = if u.phoneme.is_voiced() {
                    base -= 10.0;
                    format!("voiced-{}+voff", tag)
                } else {
                    tag.to_string()
                };
            }
            Manner::LateralFricative => {
                if u.phoneme.is_voiced() {
                    base = -28.0;
                    arm = "latfric-voiced".to_string();
                } else {
                    base = -18.0;
                    arm = "latfric-unvoiced".to_string();
                }
            }
            _ => {
                base = 0.0;
                arm = "other-stop".to_string();
            }
        },
    }
    if u.phoneme.secondary.aspirated {
        base = base.max(-3.0);
    }
    let decl = -((index.min(12)) as f32);
    let mut fin = 0.0f32;
    if total > 0 && index + 1 == total && !is_vowel(&u.phoneme) {
        fin = -4.0;
    }
    let raw = base + decl + fin;
    let floored = raw.max(-12.0);
    (arm, base, decl, fin, (floored - raw).abs() > 1e-6)
}

fn dump(text: &str, label: &str) {
    let words = articul_front::normalize(text);
    let parsed = articul_front::parse_utterance(&words);
    let units = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    let total = units.len();
    println!("== {} :: {}", label, text);
    println!("units={}", total);
    for (i, u) in units.iter().enumerate() {
        let seg_len = ((u.duration_ms as f32 / 1000.0) * SR as f32)
            .round()
            .max(1.0) as usize;
        let g = articul_cli::segment_gain_db(u, i, total);
        let (arm, base, decl, fin, floored) = arm_of(u, i, total);
        let expect = (base + decl + fin).max(-12.0);
        let ok = (g - expect).abs() < 1e-4;
        println!(
            "u{} sym={} dur={}ms stress={:?} word_final={} pause={} seglen={} arm={} base={:.1} decl={:.1} fin={:.1} floor={} engine={:.3}dB match={}",
            i,
            u.phoneme.base_symbol,
            u.duration_ms,
            u.stress,
            u.word_final,
            u.is_pause,
            seg_len,
            arm,
            base,
            decl,
            fin,
            if floored { 1 } else { 0 },
            g,
            if ok { "OK" } else { "MISMATCH" }
        );
        assert!(ok, "arm decomposition diverged from engine");
    }
}

fn main() {
    dump("TIs TIN", "fixed_sentence");
    dump("hE \"loU", "demo_hello");
    dump("\"ma", "creak_probe");
    dump("apa", "gain_probe");
    dump("\"sprit", "cluster_probe");
    dump("a, pa", "pause_probe");
    dump("%an njVN \"hasejo", "annyeong");
    dump("%jV\"bo%se%jo", "yeobo");
    dump("\"hE l@U", "old_input");
}
