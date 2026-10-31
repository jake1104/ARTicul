import subprocess
import sys

EXE = "target/release/articul.exe"

JOBS = [
    (['h@ "loU', "config/default-voice.toml", "probe/0.0.0.35.1/fresh_hello.wav"], "hello"),
    (["%an njVN h\\asejo", "config/korean-voice.toml", "probe/0.0.0.35.1/fresh_annyeong.wav"], "annyeong"),
    (["%jVbosejo", "config/korean-voice.toml", "probe/0.0.0.35.1/fresh_yeobo.wav"], "yeobo"),
    (['"a:', "config/default-voice.toml", "probe/0.0.0.35.1/solo_a_stressed.wav"], "stressed-a"),
]

for (text, voice, out), label in JOBS:
    p = subprocess.run([EXE, "synthesize", "--text", text, "--voice", voice, "--out", out],
                       capture_output=True, text=True)
    print("== %s: rc=%d stdout=%r stderr=%r" % (label, p.returncode, p.stdout.strip(), p.stderr.strip()))
    if p.returncode != 0:
        sys.exit(1)
print("ALL RENDERS OK")
