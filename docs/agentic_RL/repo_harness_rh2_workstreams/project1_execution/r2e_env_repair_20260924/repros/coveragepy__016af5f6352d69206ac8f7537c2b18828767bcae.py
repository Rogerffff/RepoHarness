"""公开复现（E06，只据公开题面）：coveragepy 016af5f6 —— 被测代码文件名无法按 UTF-8 编码（'\\udcff.py'）时 save() 崩溃。

(A) 照题面示例原样：exec(compile("pass", "\\udcff.py", "exec")) 在 cov.start() 之前，coverage 下只 exec("pass")。
(B) 最小等价调用：把 exec(compile("pass", "\\udcff.py", "exec")) 放到 start()/stop() 之间（题面说的是"trace files ... with a
    non-UTF8 encodable filename"）。数据文件与 cwd 都在 /tmp 临时目录，不写 /testbed。
判定：A 或 B 的 save() 抛 UnicodeEncodeError → REPRO_OBSERVED=1（并注明是哪一种）。
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
os.chdir(tempfile.mkdtemp())


def run(label, before, under):
    if before:
        exec(compile("pass", "\udcff.py", "exec"))
    cov = coverage.Coverage(data_file=os.path.abspath(".coverage_" + label))
    cov.start()
    if under:
        exec(compile("pass", "\udcff.py", "exec"))
    else:
        exec("pass")
    cov.stop()
    try:
        cov.save()
        return "saved"
    except UnicodeEncodeError as exc:
        return f"UnicodeEncodeError: {exc}"


a = run("A", True, False)
b = run("B", False, True)
print("A (literal example):", a)
print("B (exec under coverage):", b)
hits = [n for n, r in (("A", a), ("B", b)) if r.startswith("UnicodeEncodeError")]
if hits:
    print("REPRO_OBSERVED=1 (UnicodeEncodeError on save in variant(s) %s)" % hits)
else:
    print("REPRO_OBSERVED=0 reason=save() succeeded in both variants")
