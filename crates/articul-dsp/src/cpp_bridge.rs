#[cfg(feature = "cpp")]
unsafe extern "C" {
    fn resonator_process(input: *const f32, output: *mut f32, len: u64, a: f32, b: f32, c: f32);
}

pub fn cpp_available() -> bool {
    cfg!(feature = "cpp")
}

#[cfg(feature = "cpp")]
pub fn cpp_process_single(freq_hz: f32, bw_hz: f32, sample_rate: u32, input: &[f32]) -> Vec<f32> {
    let t = 1.0 / sample_rate as f32;
    let c0 = (-2.0 * std::f32::consts::PI * bw_hz * t).exp();
    let c = -c0;
    let b = 2.0
        * (-std::f32::consts::PI * bw_hz * t).exp()
        * (2.0 * std::f32::consts::PI * freq_hz * t).cos();
    let a = 1.0 - b - c;
    let mut out = vec![0.0; input.len()];
    unsafe {
        resonator_process(
            input.as_ptr(),
            out.as_mut_ptr(),
            input.len() as u64,
            a,
            b,
            c,
        );
    }
    out
}
