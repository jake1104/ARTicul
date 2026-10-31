fn main() {
    if std::env::var("CARGO_FEATURE_CPP").is_ok() {
        cc::Build::new()
            .cpp(true)
            .opt_level(2)
            .file("../../cpp/resonator/resonator.cpp")
            .compile("resonator");
    }
}
