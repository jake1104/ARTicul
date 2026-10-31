pub mod normalize;
pub mod prosody;
pub mod xsampa;

pub use normalize::normalize;
pub use prosody::parse_utterance;
pub use prosody::plan;
pub use prosody::plan_utterance;
pub use prosody::plan_utterance_korean;
pub use prosody::BoundaryTone;
pub use prosody::WordProsody;
pub use xsampa::Xsampa;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Stress {
    Unstressed,
    Secondary,
    Primary,
}

pub fn version() -> &'static str {
    "0.0.1"
}
