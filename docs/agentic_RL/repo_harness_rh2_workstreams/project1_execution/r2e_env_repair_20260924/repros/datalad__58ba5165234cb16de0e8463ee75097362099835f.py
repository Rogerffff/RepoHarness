"""公开复现：datalad 58ba5165 —— [PY: ... PY] / [CMD: ... CMD] 文档标记内含方括号时命令行文档处理出错。
依据：公开题面示例（demo_doc 原样）。题面的 alter_interface_docs_for_cmdline 在该提交位于 datalad/cli/interface.py。
判据（题面"期望行为"的最小解释）：命令行文档应去掉 PY 段、保留 CMD 段内容（含内部方括号），不留标记残片，
保留 "End of demo."。空白归一后比较。只观测，不写 /testbed。导入：先普通导入并记录，失败再把 cwd 加进 sys.path。"""
import os
import sys

sys.dont_write_bytecode = True
try:
    import datalad
    print("IMPORT_PLAIN=ok %s" % datalad.__file__)
except ImportError as exc:
    print("IMPORT_PLAIN=fail (%s: %s); retry with cwd %s on sys.path" % (type(exc).__name__, exc, os.getcwd()))
    sys.path.insert(0, os.getcwd())
from datalad.cli.interface import alter_interface_docs_for_cmdline

demo_doc = """\
And an example for in-line markup: [PY: just for Python PY] and
the other one [CMD: just for the command line CMD]. [PY: multiline
python-only with [ brackets [] ] PY][CMD: multiline cli-only with [ brackets
[] ] CMD]. End of demo.
"""
out = alter_interface_docs_for_cmdline(demo_doc)
print("OUTPUT=%r" % out)
flat = " ".join(out.split())
problems = []
if "python-only" in flat or "just for Python" in flat:
    problems.append("python-only text kept")
if "PY]" in flat or "[PY:" in flat or "CMD]" in flat or "[CMD:" in flat:
    problems.append("markup left over")
if "multiline cli-only with [ brackets [] ]" not in flat:
    problems.append("cli-only text with brackets missing")
if "End of demo." not in flat:
    problems.append("trailing text missing")
print("PROBLEMS=%s" % (problems or "none"))
print("REPRO_OBSERVED=%d" % (1 if problems else 0))
