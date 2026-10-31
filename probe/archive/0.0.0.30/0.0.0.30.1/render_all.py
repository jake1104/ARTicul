import subprocess, os, hashlib
ROOT = r"E:\01_coding\ARTicul"
BIN = os.path.join(ROOT, "target", "release", "articul.exe")
VOICE = os.path.join(ROOT, "config", "default-voice.toml")
OUT = os.path.join(ROOT, "probe", "0.0.0.30.1")
ITEMS = {
    "fixed_sentence": "TIs TIN",
    "demo_hello": "hE \"loU",
    "creak_probe": "\"ma",
    "gain_probe": "apa",
    "cluster_probe": "\"sprit",
    "pause_probe": "a, pa",
    "annyeong": "%an njVN \"hasejo",
    "yeobo": "%jV\"bo%se%jo",
    "old_input": "\"hE l@U",
}
EXPECTED_FIXED_SHA = "cfba9ef28a1a17eee0ba2626b64bb3877f66a51c93fcbdb9ecea3bf99b5b455a"
for name, text in ITEMS.items():
    p = os.path.join(OUT, name + ".wav")
    r = subprocess.run([BIN, "synthesize", "--text", text, "--voice", VOICE, "--out", p],
                       capture_output=True, text=True)
    raw = open(p, "rb").read()
    n = (len(raw) - 44) // 2
    print("%s rc=%d samples=%d sha=%.16s" % (name, r.returncode, n, hashlib.sha256(raw).hexdigest()))
    if r.returncode != 0:
        print("STDERR: " + r.stderr.strip()[:500])
print("fixed_sentence full-sha match CFBA: %s" % (
    hashlib.sha256(open(os.path.join(OUT, "fixed_sentence.wav"), "rb").read()).hexdigest()
    == EXPECTED_FIXED_SHA))
for a, b in [("demo_hello", "demo/hello.wav"), ("annyeong", "demo/annyeonghaseyo.wav"),
             ("yeobo", "demo/yeoboseyo.wav")]:
    ra = open(os.path.join(OUT, a + ".wav"), "rb").read()
    rb = open(os.path.join(ROOT, b), "rb").read()
    print("identity %s vs %s: %s (sizes %d/%d)" % (a, b, ra == rb, len(ra), len(rb)))
print("done")
