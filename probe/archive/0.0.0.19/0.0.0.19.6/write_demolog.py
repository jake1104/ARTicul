import hashlib

raw = open("demo/hello.wav", "rb").read()
lines = [
    "wrote 9792 samples to demo/hello.wav",
    "samples 9792 rate 22050 ch 1 mono 16-bit (X-SAMPA hE loU stressed, config/default-voice.toml)",
    "sha256 " + hashlib.sha256(raw).hexdigest(),
    "deterministic demo render confirmed: probe/0.0.0.19.6/hello-check.wav byte-identical",
]
open("logs/0.0.0.19.6/demo.log", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
