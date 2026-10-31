use articul_dsp::GlottalSource;

#[test]
fn glottal_spectrum_falls_about_12db_per_oct() {
    let src = GlottalSource {
        f0_hz: 100.0,
        open_quotient: 0.6,
        asymmetry: 0.7,
        aspiration_noise: 0.0,
    };
    let out = src.generate(0.5, 22050);
    let slope = articul_dsp::spectral_slope_db_per_oct(&out, 22050);
    assert!(
        (-20.0..=-4.0).contains(&slope),
        "slope={slope} expected near -12 dB/oct"
    );
}
