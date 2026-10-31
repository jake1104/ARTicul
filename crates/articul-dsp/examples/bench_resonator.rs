use std::time::Instant;

fn workload() -> Vec<f32> {
    let mut rng = 0x12345678u32;
    let mut v = Vec::with_capacity(22050);
    for _ in 0..22050 {
        rng = rng.wrapping_mul(1664525).wrapping_add(1013904223);
        v.push(((rng >> 8) as f32) / 16777216.0 * 2.0 - 1.0);
    }
    v
}

fn main() {
    let input = workload();
    let filter = articul_dsp::CascadeFilter::single(500.0, 60.0, 22050);
    let iters = 50;
    let start = Instant::now();
    let mut sink = 0.0;
    for _ in 0..iters {
        let out = filter.process(&input);
        sink += out[1000];
    }
    let rust_ms = start.elapsed().as_secs_f64() * 1000.0;
    println!("rust_ms={rust_ms:.1} iters={iters} sink={sink:.6}");
    println!("cpp_available={}", articul_dsp::cpp_available());
    #[cfg(feature = "cpp")]
    {
        let start = Instant::now();
        let mut sink = 0.0;
        for _ in 0..iters {
            let out = articul_dsp::cpp_process_single(500.0, 60.0, 22050, &input);
            sink += out[1000];
        }
        let cpp_ms = start.elapsed().as_secs_f64() * 1000.0;
        println!("cpp_ms={cpp_ms:.1} iters={iters} sink={sink:.6}");
        println!("speedup={:.2}", rust_ms / cpp_ms);
    }
}
