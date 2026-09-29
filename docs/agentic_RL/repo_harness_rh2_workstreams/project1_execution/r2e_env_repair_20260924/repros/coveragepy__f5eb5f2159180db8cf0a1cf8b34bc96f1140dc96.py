"""公开复现（E06，只据公开题面）：coveragepy f5eb5f21 —— branch=True 时 JSON 报告 totals 缺 covered_branches / missing_branches。

题面示例的 "execute some code" 用最小等价：/tmp 临时目录里写一个有分支的小模块，Coverage(branch=True) 下 import，
json_report(outfile=<tmp>/coverage.json)。不写 /testbed。判定：totals 缺这两个键 → REPRO_OBSERVED=1。
"""
import json
import os
import sys
import tempfile

try:
    import coverage
    IMPORT = "direct"
except ImportError as exc:
    sys.path.insert(0, os.getcwd())
    IMPORT = f"cwd_fallback({type(exc).__name__})"
    import coverage

print("REPRO_IMPORT=" + IMPORT, coverage.__file__, coverage.__version__)
tmp = tempfile.mkdtemp()
os.chdir(tmp)
sys.path.insert(0, tmp)
with open("mod_branch.py", "w") as f:
    f.write("def f(x):\n    if x:\n        return 1\n    return 2\n\n\nf(1)\n")
cov = coverage.Coverage(branch=True, data_file=os.path.join(tmp, ".coverage"))
cov.start()
import mod_branch  # noqa: E402,F401
cov.stop()
outfile = os.path.join(tmp, "coverage.json")
cov.json_report(outfile=outfile)
with open(outfile) as f:
    totals = json.load(f)["totals"]
print("totals:", json.dumps(totals, sort_keys=True))
missing = [k for k in ("covered_branches", "missing_branches") if k not in totals]
if missing:
    print("REPRO_OBSERVED=1 (totals missing %s)" % missing)
else:
    print("REPRO_OBSERVED=0 reason=totals has both branch keys")
