import subprocess, os
ROOT = r"E:\01_coding\ARTicul"
BIN = os.path.join(ROOT, "target", "release", "articul.exe")
VOICE = os.path.join(ROOT, "config", "default-voice.toml")
OUT = os.path.join(ROOT, "probe", "0.0.0.28.1")
ITEMS = {
    "fixed_sentence": "TIs TIN",
    "demo_hello": "hE \"loU",
    "creak_probe": "\"ma",
    "gain_probe": "apa",
    "cluster_probe": "\"sprit",
    "pause_probe": "a, pa",
    "annyeong": "%an njVN \"hasejo",
    "yeobo": "%jV\"bo%se%jo",
}
for name, text in ITEMS.items():
    p = os.path.join(OUT, name + ".wav")
    r = subprocess.run([BIN, "synthesize", "--text", text, "--voice", VOICE, "--out", p],
                       capture_output=True, text=True)
    print(name, "rc=", r.returncode, "stderr=", r.stderr.strip()[:200])
print("done")
