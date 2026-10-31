use articul_cli::cf0_mode;
use articul_cli::Cf0Mode;

#[test]
fn cf0_threshold_selects_flat_or_decay() {
    assert_eq!(cf0_mode(true, true, 49), Cf0Mode::Flat);
    assert_eq!(cf0_mode(true, true, 50), Cf0Mode::Decay);
    assert_eq!(cf0_mode(true, true, 200), Cf0Mode::Decay);
    assert_eq!(cf0_mode(true, false, 200), Cf0Mode::None);
    assert_eq!(cf0_mode(false, true, 200), Cf0Mode::None);
}

#[test]
fn final_voiced_segment_runs_irregular() {
    let out = articul_cli::render_sentence("\"ma", 22050, 120.0);
    assert!(out.len() > 4000);
    let n = out.len();
    let tail = &out[n - 1500..];
    let early = &out[1200..2700];
    let tail_lags = [0, 500, 1000]
        .iter()
        .map(|o| autocorr_lag(&tail[*o..*o + 500], 80, 320))
        .collect::<Vec<_>>();
    let early_lags = [0, 500, 1000]
        .iter()
        .map(|o| autocorr_lag(&early[*o..*o + 500], 80, 320))
        .collect::<Vec<_>>();
    let tail_spread = tail_lags.iter().max().unwrap() - tail_lags.iter().min().unwrap();
    let early_spread = early_lags.iter().max().unwrap() - early_lags.iter().min().unwrap();
    assert!(tail_spread > 40, "tail lags={tail_lags:?}");
    assert!(early_spread < 15, "early lags={early_lags:?}");
}

fn autocorr_lag(x: &[f32], min_lag: usize, max_lag: usize) -> usize {
    let mut best_lag = min_lag;
    let mut best = f32::MIN;
    for lag in min_lag..max_lag.min(x.len()) {
        let mut s = 0.0f32;
        for i in 0..x.len() - lag {
            s += x[i] * x[i + lag];
        }
        if s > best {
            best = s;
            best_lag = lag;
        }
    }
    best_lag
}

#[test]
fn vowel_onset_after_voiceless_obstruent_runs_faster() {
    let out = articul_cli::render_sentence("pa:t", 22050, 120.0);
    assert!(out.len() > 3000);
    let vstart = 926usize;
    let onset = &out[vstart + 200..vstart + 1000];
    let late = &out[vstart + 1150..vstart + 1800];
    let onset_lag = autocorr_lag(onset, 100, 260);
    let late_lag = autocorr_lag(late, 100, 260);
    assert!(
        onset_lag < late_lag,
        "onset lag {onset_lag} must be shorter than late lag {late_lag}"
    );
    let ratio = late_lag as f32 / onset_lag as f32;
    assert!(ratio > 1.03 && ratio < 1.25, "f0 lift ratio={ratio}");
}
