import sys

sys.path.insert(0, "probe/0.0.0.34.2")
src = open("probe/0.0.0.34.2/measure_korean.py").read()
src = src.split("for label, path, text")[0]
exec(src)
for label in ["annyeong", "yeobo"]:
    print(label, plan_durations(label))
print("engine annyeong: [179,94,82,74,160,91,80,118,105,121,74,211]")
print("engine yeobo: [79,130,74,103,108,129,74,215]")
