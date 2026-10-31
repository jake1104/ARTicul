use articul_cli::render_with_voice;
use clap::Parser;
use clap::Subcommand;
use std::path::PathBuf;

#[derive(Parser)]
#[command(
    name = "articul",
    version = "0.0.1",
    about = "Rule-based articulatory speech synthesizer"
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Synthesize {
        #[arg(long)]
        text: String,
        #[arg(long)]
        voice: PathBuf,
        #[arg(long)]
        out: PathBuf,
        #[arg(long, default_value_t = 120.0)]
        f0: f32,
    },
    Play {
        #[arg(long)]
        text: String,
        #[arg(long)]
        voice: PathBuf,
        #[arg(long, default_value_t = 120.0)]
        f0: f32,
    },
}

fn write_wav(path: &PathBuf, samples: &[f32], sample_rate: u32) -> Result<(), String> {
    let spec = hound::WavSpec {
        channels: 1,
        sample_rate,
        bits_per_sample: 16,
        sample_format: hound::SampleFormat::Int,
    };
    let mut writer = hound::WavWriter::create(path, spec).map_err(|e| e.to_string())?;
    for s in samples {
        let v = (s.clamp(-1.0, 1.0) * 32767.0).round() as i16;
        writer.write_sample(v).map_err(|e| e.to_string())?;
    }
    writer.finalize().map_err(|e| e.to_string())?;
    Ok(())
}

fn main() {
    let cli = Cli::parse();
    match cli.command {
        Commands::Synthesize {
            text,
            voice,
            out,
            f0,
        } => {
            let cfg = articul_config::VoiceConfig::load(&voice).unwrap_or_else(|e| {
                eprintln!("failed to load voice: {e}");
                std::process::exit(2);
            });
            let samples = render_with_voice(&text, &cfg, f0);
            if let Err(e) = write_wav(&out, &samples, cfg.sample_rate.hz) {
                eprintln!("failed to write wav: {e}");
                std::process::exit(2);
            }
            println!("wrote {} samples to {}", samples.len(), out.display());
        }
        Commands::Play { text, voice, f0 } => {
            let cfg = articul_config::VoiceConfig::load(&voice).unwrap_or_else(|e| {
                eprintln!("failed to load voice: {e}");
                std::process::exit(2);
            });
            let samples = render_with_voice(&text, &cfg, f0);
            if let Err(e) = play_samples(&samples, cfg.sample_rate.hz) {
                eprintln!("playback failed: {e}");
                std::process::exit(2);
            }
            println!("played {} samples", samples.len());
        }
    }
}

fn play_samples(samples: &[f32], sample_rate: u32) -> Result<(), String> {
    use cpal::traits::DeviceTrait;
    use cpal::traits::HostTrait;
    use cpal::traits::StreamTrait;
    let host = cpal::default_host();
    let device = host
        .default_output_device()
        .ok_or_else(|| "no output device".to_string())?;
    let config = device.default_output_config().map_err(|e| e.to_string())?;
    let stream_config: cpal::StreamConfig = config.into();
    let data = std::sync::Arc::new(samples.to_vec());
    let pos = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
    let pos_cb = pos.clone();
    let data_cb = data.clone();
    let stream = device
        .build_output_stream(
            &stream_config,
            move |output: &mut [f32], _| {
                let start = pos_cb.load(std::sync::atomic::Ordering::SeqCst);
                for (i, slot) in output.iter_mut().enumerate() {
                    let idx = start + i;
                    *slot = if idx < data_cb.len() {
                        data_cb[idx]
                    } else {
                        0.0
                    };
                }
                pos_cb.fetch_add(output.len(), std::sync::atomic::Ordering::SeqCst);
            },
            |e| {
                eprintln!("stream error: {e}");
            },
            None,
        )
        .map_err(|e| e.to_string())?;
    stream.play().map_err(|e| e.to_string())?;
    let secs = samples.len() as f32 / sample_rate as f32 + 0.2;
    std::thread::sleep(std::time::Duration::from_secs_f32(secs.max(0.5)));
    Ok(())
}
