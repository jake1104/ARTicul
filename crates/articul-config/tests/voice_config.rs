use std::path::PathBuf;

fn config_path(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../config")
        .join(name)
}

#[test]
fn default_voice_loads_and_validates() {
    let cfg = articul_config::VoiceConfig::load(&config_path("default-voice.toml"))
        .expect("default voice must load");
    assert_eq!(cfg.sample_rate.hz, 22050);
    assert!(cfg.source.f0_hz > 0.0);
    assert!(!cfg.cascade().is_empty());
}

#[test]
fn klatt_voice_loads_and_validates() {
    let cfg = articul_config::VoiceConfig::load(&config_path("klatt-voice.toml"))
        .expect("klatt voice must load");
    assert_eq!(cfg.sample_rate.hz, 22050);
    assert!(!cfg.parallel().is_empty());
}

#[test]
fn rejects_out_of_range_sample_rate() {
    let bad = "[sample_rate]\nhz = 100\n[source]\nf0_hz = 120.0\nopen_quotient = 0.6\nasymmetry = 0.7\naspiration_noise = 0.05\n[cascade_formants]\n[[cascade_formants.formant]]\nindex = 1\nfreq_hz = 500.0\nbw_hz = 60.0\n[parallel_formants]\n[prosody]\nrate = 1.0\npitch_scale = 1.0\n";
    let err = articul_config::VoiceConfig::parse_str(bad).unwrap_err();
    assert!(!err.is_empty());
}
