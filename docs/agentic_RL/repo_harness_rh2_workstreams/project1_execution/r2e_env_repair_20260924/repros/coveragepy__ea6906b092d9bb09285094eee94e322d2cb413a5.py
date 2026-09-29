"""公开复现（E06，只据公开题面）：coveragepy ea6906b0 —— HTML 报告输出目录里没有 .gitignore。

题面只给 html_report(directory='htmlcov') 与目录清单；最小等价调用：/tmp 临时目录里写一个小模块 main_file.py，
Coverage 下 import 它，再 html_report(directory=<tmp>/htmlcov)。不写 /testbed。
判定：输出目录生成了但没有 .gitignore → REPRO_OBSERVED=1。
"""
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
with open("main_file.py", "w") as f:
    f.write("def f(x):\n    return x + 1\n\n\nf(1)\n")
cov = coverage.Coverage(data_file=os.path.join(tmp, ".coverage"))
cov.start()
import main_file  # noqa: E402,F401
cov.stop()
out = os.path.join(tmp, "htmlcov")
pct = cov.html_report(directory=out)
listing = sorted(os.listdir(out))
print("html_report ->", pct, "files:", listing)
if ".gitignore" in listing:
    with open(os.path.join(out, ".gitignore")) as f:
        print(".gitignore content:", repr(f.read()[:80]))
    print("REPRO_OBSERVED=0 reason=.gitignore present")
else:
    print("REPRO_OBSERVED=1 (no .gitignore in the HTML output directory)")
