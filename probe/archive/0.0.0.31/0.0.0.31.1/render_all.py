import subprocess, os, hashlib
ROOT = r"E:\01_coding\ARTicul"
BIN = os.path.join(ROOT, "target", "release", "articul.exe")
VOICE = os.path.join(ROOT, "config", "default-voice.toml")
OUT = os.path.join(ROOT, "probe", "0.0.0.31.1")
ITEMS = {
    "hello": "hE \"loU",
    "annyeong": "%an njVN \"hasejo",
    "yeobo": "%jV\"bo%se%jo",
}
DEMOS = {
    "hello": "demo/hello.wav",
    "annyeong": "demo/annyeonghaseyo.wav",
    "yeobo": "demo/yeoboseyo.wav",
}
for name, text in ITEMS.items():
    p = os.path.join(OUT, name + ".wav")
    r = subprocess.run([BIN, "synthesize", "--text", text, "--voice", VOICE, "--out", p],
                       capture_output=True, text=True)
    raw = open(p, "rb").read()
    n = (len(raw) - 44) // 2
    print("%s rc=%d samples=%d sha=%.16s" % (name, r.returncode, n, hashlib.sha256(raw).hexdigest()))
    if r.returncode != 0:
        print("STDERR: " + r.stderr.strip()[:500])
for name, demo in DEMOS.items():
    ra = open(os.path.join(OUT, name + ".wav"), "rb").read()
    rb = open(os.path.join(ROOT, demo), "rb").read()
    n = (len(ra) - 44) // 2
    print("identity %s vs %s: %s samples=%d" % (name + ".wav", demo, ra == rb, n))
print("done")
