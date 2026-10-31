import io

for f in [
    "crates/articul-cli/tests/tmp_hfprobe.rs",
    "crates/articul-cli/tests/junction_nospark.rs",
]:
    s = io.open(f, encoding="utf-8").read()
    bad = '"\x8a"'
    good = '"\\u{028A}"'
    n = s.count(bad)
    assert n == 1, (f, n)
    io.open(f, "w", encoding="utf-8", newline="").write(s.replace(bad, good))
    print(f + " patched")
