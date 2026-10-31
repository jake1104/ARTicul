use serde::Deserialize;
use std::path::Path;

#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct SampleRate {
    pub hz: u32,
}

#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct Source {
    pub f0_hz: f32,
    pub open_quotient: f32,
    pub asymmetry: f32,
    pub aspiration_noise: f32,
}

#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct Formant {
    pub index: u8,
    pub freq_hz: f32,
    pub bw_hz: f32,
}

#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct CascadeFormants {
    #[serde(default)]
    pub formant: Vec<Formant>,
}

#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct ParallelFormant {
    pub index: u8,
    pub freq_hz: f32,
    pub bw_hz: f32,
    pub amplitude: f32,
}

#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct ParallelFormants {
    #[serde(default)]
    pub formant: Vec<ParallelFormant>,
}

#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct Prosody {
    pub rate: f32,
    pub pitch_scale: f32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Deserialize)]
pub enum KoreanBoundary {
    #[serde(rename = "H")]
    #[default]
    High,
    #[serde(rename = "L")]
    Low,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
pub struct KoreanVoice {
    #[serde(default)]
    pub enabled: bool,
    #[serde(default)]
    pub final_boundary: KoreanBoundary,
}

impl Default for KoreanVoice {
    fn default() -> Self {
        Self {
            enabled: false,
            final_boundary: KoreanBoundary::High,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct VoiceConfig {
    pub sample_rate: SampleRate,
    pub source: Source,
    pub cascade_formants: CascadeFormants,
    pub parallel_formants: ParallelFormants,
    pub prosody: Prosody,
    #[serde(default)]
    pub korean: KoreanVoice,
}

impl VoiceConfig {
    pub fn parse_str(text: &str) -> Result<Self, String> {
        let cfg: Self = toml::from_str(text).map_err(|e| e.to_string())?;
        cfg.validate()?;
        Ok(cfg)
    }

    pub fn load(path: &Path) -> Result<Self, String> {
        let text = std::fs::read_to_string(path).map_err(|e| e.to_string())?;
        Self::parse_str(&text)
    }

    fn validate(&self) -> Result<(), String> {
        if !(8000..=96000).contains(&self.sample_rate.hz) {
            return Err("sample_rate.hz out of range".to_string());
        }
        if !(20.0..=1000.0).contains(&self.source.f0_hz) {
            return Err("source.f0_hz out of range".to_string());
        }
        if !(0.05..=0.99).contains(&self.source.open_quotient) {
            return Err("source.open_quotient out of range".to_string());
        }
        if !(0.05..=0.99).contains(&self.source.asymmetry) {
            return Err("source.asymmetry out of range".to_string());
        }
        if !(0.0..=1.0).contains(&self.source.aspiration_noise) {
            return Err("source.aspiration_noise out of range".to_string());
        }
        if self.cascade_formants.formant.is_empty() {
            return Err("cascade_formants.formant empty".to_string());
        }
        for f in &self.cascade_formants.formant {
            if !(50.0..=10000.0).contains(&f.freq_hz) {
                return Err("cascade freq_hz out of range".to_string());
            }
            if !(10.0..=2000.0).contains(&f.bw_hz) {
                return Err("cascade bw_hz out of range".to_string());
            }
        }
        for f in &self.parallel_formants.formant {
            if !(50.0..=10000.0).contains(&f.freq_hz) {
                return Err("parallel freq_hz out of range".to_string());
            }
            if !(10.0..=2000.0).contains(&f.bw_hz) {
                return Err("parallel bw_hz out of range".to_string());
            }
            if !(0.0..=2.0).contains(&f.amplitude) {
                return Err("parallel amplitude out of range".to_string());
            }
        }
        if !(0.25..=4.0).contains(&self.prosody.rate) {
            return Err("prosody.rate out of range".to_string());
        }
        if !(0.25..=4.0).contains(&self.prosody.pitch_scale) {
            return Err("prosody.pitch_scale out of range".to_string());
        }
        Ok(())
    }

    pub fn cascade(&self) -> &[Formant] {
        &self.cascade_formants.formant
    }

    pub fn parallel(&self) -> &[ParallelFormant] {
        &self.parallel_formants.formant
    }
}

pub fn version() -> &'static str {
    "0.0.1"
}
