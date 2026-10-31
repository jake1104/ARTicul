pub mod synth;

pub use synth::cf0_mode;
pub use synth::render_gain_track;
pub use synth::render_planned;
pub use synth::render_sentence;
pub use synth::render_with_voice;
pub use synth::segment_gain_db;
pub use synth::Cf0Mode;

pub fn version() -> &'static str {
    "0.0.1"
}
