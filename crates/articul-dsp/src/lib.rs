pub mod cascade;
pub mod cpp_bridge;
pub mod parallel;
pub mod radiation;
pub mod source;
pub mod spectrum;
pub mod vowels;

pub use cascade::CascadeFilter;
pub use cascade::NotchFilter;
pub use cascade::Resonator;
pub use cpp_bridge::cpp_available;
#[cfg(feature = "cpp")]
pub use cpp_bridge::cpp_process_single;
pub use parallel::frication_level_for;
pub use parallel::frication_noise;
pub use parallel::fricative_shaping;
pub use parallel::lateral_notch;
pub use parallel::nasal_branch_needed;
pub use parallel::nasal_notch;
pub use parallel::nasalize_bandwidths;
pub use parallel::ParallelFilter;
pub use radiation::apply_radiation;

pub use source::cf0_boost_factor;
pub use source::effective_aspiration;
pub use source::GlottalSource;
pub use spectrum::spectral_slope_db_per_oct;
pub use vowels::korean_locus_pull;
pub use vowels::korean_vowel_formants;
pub use vowels::locus_adjusted_formants;
pub use vowels::locus_pull_toward;
pub use vowels::reduced_vowel_targets;
pub use vowels::vowel_formants;

pub fn version() -> &'static str {
    "0.0.1"
}
