"""Reference-based evaluation harness (report-only, never gates the build).

Corpus items are rendered with the release CLI, then compared with MCD
(DTW over MFCC c1..c12), F0 RMSE over DTW-aligned voiced frames (pyin),
and total-duration Pearson correlation.

Reference pack convention (human recordings, not stored in this repo):
a directory with one wav per corpus item, basename matching the item id
plus ".wav" (e.g. "demo_hello.wav"), same sample rate as the synth
output. Pass it with --reference-dir to get synth-vs-human columns.
Without it the script reports self-consistency (run A vs run B, which
must be exact) and the cross-utterance MCD matrix (discriminability).

Usage:
    python eval_reference.py --articul <bin> --voice <toml> --out <dir> [--reference-dir <dir>]
    python eval_reference.py --self-test
"""

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile

import librosa
import numpy as np

ITEMS = {
    "fixed_sentence": "TIs TIN",
    "demo_hello": "hE \"loU",
    "creak_probe": "\"ma",
    "gain_probe": "apa",
    "cluster_probe": "\"sprit",
    "pause_probe": "a, pa",
}

SAMPLE_RATE = 22050


def render(articul, voice, out_dir, tag):
    paths = {}
    for item_id, text in ITEMS.items():
        path = os.path.join(out_dir, "%s_%s.wav" % (item_id, tag))
        subprocess.run(
            [articul, "synthesize", "--text", text, "--voice", voice, "--out", path],
            check=True,
            capture_output=True,
        )
        paths[item_id] = path
    return paths


def load_mono(path):
    y, sr = librosa.load(path, sr=SAMPLE_RATE, mono=True)
    return y.astype(np.float64)


def mfcc_no_c0(y):
    m = librosa.feature.mfcc(y=y, sr=SAMPLE_RATE, n_mfcc=13)
    return m[1:, :]


def dtw_path(a, b):
    _, path = librosa.sequence.dtw(a, b, metric="euclidean")
    return [(int(i), int(j)) for (i, j) in path.tolist()]


def mcd(a_feats, b_feats):
    path = dtw_path(a_feats, b_feats)
    total = 0.0
    for i, j in path:
        diff = a_feats[:, i] - b_feats[:, j]
        total += float(np.dot(diff, diff))
    mean_sq = total / max(1, len(path))
    return (10.0 / math.log(10.0)) * math.sqrt(2.0 * mean_sq)


def f0_track(y):
    f0, voiced, _ = librosa.pyin(
        y, fmin=50.0, fmax=500.0, sr=SAMPLE_RATE, frame_length=1024, hop_length=256
    )
    return np.asarray(f0, dtype=float), np.asarray(voiced, dtype=bool)


def f0_rmse(a_feats, a_f0, a_v, b_feats, b_f0, b_v):
    path = dtw_path(a_feats, b_feats)
    errs = []
    agree = 0
    for i, j in path:
        if i < len(a_v) and j < len(b_v):
            if bool(a_v[i]) == bool(b_v[j]):
                agree += 1
            if bool(a_v[i]) and bool(b_v[j]):
                fa = float(a_f0[i])
                fb = float(b_f0[j])
                if math.isfinite(fa) and math.isfinite(fb) and fa > 0 and fb > 0:
                    errs.append((math.log(fa) - math.log(fb)) ** 2)
    rmse_st = math.sqrt(sum(errs) / max(1, len(errs))) * 12.0 / math.log(2.0)
    return rmse_st, agree / max(1, len(path))


def duration_corr(a_lens, b_lens):
    a = np.asarray(a_lens, dtype=float)
    b = np.asarray(b_lens, dtype=float)
    if np.std(a) < 1e-9 or np.std(b) < 1e-9:
        return 1.0 if np.allclose(a, b) else 0.0
    return float(np.corrcoef(a, b)[0, 1])


def evaluate_pair(a_paths, b_paths):
    per_item = {}
    a_lens = []
    b_lens = []
    for item_id in ITEMS:
        ya = load_mono(a_paths[item_id])
        yb = load_mono(b_paths[item_id])
        a_lens.append(len(ya))
        b_lens.append(len(yb))
        fa = mfcc_no_c0(ya)
        fb = mfcc_no_c0(yb)
        a_f0, a_v = f0_track(ya)
        b_f0, b_v = f0_track(yb)
        rmse, agree = f0_rmse(fa, a_f0, a_v, fb, b_f0, b_v)
        per_item[item_id] = {
            "mcd_db": mcd(fa, fb),
            "f0_rmse_st": rmse,
            "voiced_agreement": agree,
            "len_a": len(ya),
            "len_b": len(yb),
        }
    return {
        "per_item": per_item,
        "duration_corr": duration_corr(a_lens, b_lens),
    }


def cross_matrix(paths):
    feats = {k: mfcc_no_c0(load_mono(p)) for k, p in paths.items()}
    ids = sorted(feats)
    return {
        a: {b: mcd(feats[a], feats[b]) for b in ids} for a in ids
    }


def self_test():
    import shutil

    tmp = tempfile.mkdtemp(prefix="eval_selftest_")
    articul = os.path.join(os.getcwd(), "target", "release", "articul")
    if os.name == "nt":
        articul += ".exe"
    voice = os.path.join(os.getcwd(), "config", "default-voice.toml")
    try:
        a = render(articul, voice, tmp, "a")
        b = render(articul, voice, tmp, "b")
        rep = evaluate_pair(a, b)
        for item_id, m in rep["per_item"].items():
            assert m["mcd_db"] < 1e-6, (item_id, m)
            assert m["f0_rmse_st"] < 1e-6, (item_id, m)
            assert m["voiced_agreement"] == 1.0, (item_id, m)
        assert rep["duration_corr"] == 1.0, rep
        mx = cross_matrix(a)
        ids = sorted(mx)
        for x in ids:
            for y in ids:
                if x == y:
                    assert mx[x][y] < 1e-6, (x, y, mx[x][y])
                else:
                    assert mx[x][y] > 1.0, (x, y, mx[x][y])
        print("SELF-TEST PASS: deterministic renders identical, distinct items separated")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--articul", default=os.path.join("target", "release", "articul"))
    ap.add_argument("--voice", default=os.path.join("config", "default-voice.toml"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--reference-dir", default=None)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if not args.out:
        print("need --out <dir> (or use --self-test)", file=sys.stderr)
        return 2
    os.makedirs(args.out, exist_ok=True)
    run_a = render(args.articul, args.voice, args.out, "runA")
    rep = {"self_consistency": evaluate_pair(run_a, render(args.articul, args.voice, args.out, "runB"))}
    rep["cross_mcd"] = cross_matrix(run_a)
    if args.reference_dir:
        ref = {}
        for item_id in ITEMS:
            cand = os.path.join(args.reference_dir, item_id + ".wav")
            if os.path.exists(cand):
                ref[item_id] = cand
        if ref:
            rep["vs_reference"] = evaluate_pair(run_a, ref)
        else:
            rep["vs_reference"] = "no matching reference wavs found"
    else:
        rep["vs_reference"] = "no reference pack supplied"
    with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=2)
    print("mean self MCD: %.4f dB" % np.mean([m["mcd_db"] for m in rep["self_consistency"]["per_item"].values()]))
    print("duration corr: %.4f" % rep["self_consistency"]["duration_corr"])
    print("report: %s" % os.path.join(args.out, "report.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
