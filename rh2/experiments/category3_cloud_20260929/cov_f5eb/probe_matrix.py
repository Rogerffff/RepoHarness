"""私有行为矩阵（不交给求解者）：在评分镜像里对一个候选跑 7 种情形，打印 JSON 报告的 totals 与每文件 summary。

覆盖面（作者须知 §2 第 4 步）：
- 规模：单文件 / 两文件（totals 是否按文件累加）；
- 数据状态：进程内数据 / 保存后由不设 branch 的新对象读回 / CLI 两进程 / 行模式数据 / 分支模式但零分支；
- 相邻属性：每文件 summary 与 totals、num_branches、num_partial_branches、meta.branch_coverage；
- 独立口径：同一数据的 XML 报告 branches-valid / branches-covered（不经过 jsonreport.py）。
期望值不取自 gold：BRANCHY 为 6/0/4/2（修订计划 §2.2 的推导，XML 独立核对），题面示例文件为 2/1/1/1。
用法：/testbed/.venv/bin/python probe_matrix.py <空的工作目录>
"""
import importlib
import json
import os
import subprocess
import sys
import textwrap
import xml.dom.minidom

import coverage

work = sys.argv[1]
os.makedirs(work, exist_ok=True)
os.chdir(work)
sys.path.insert(0, work)
PY = sys.executable

BRANCHY = """\
def f(x):
    if x:
        return 1
    return 2

def g(x):
    if x:
        return 1
    return 2

def h(x):
    if x:
        return 1
    return 2

f(0)
f(1)
g(0)
g(1)
"""
EXAMPLE_AFTER_IMPORT = """\
import {other}
a = {{'b': 1}}
if a.get('a'):
    b = 1
"""
NO_BRANCH = "x = 1\ny = 2\n"


def write(name, text):
    with open(name + ".py", "w") as f:
        f.write(textwrap.dedent(text))


def load(path):
    with open(path) as f:
        return json.load(f)


def brief(report):
    keys = ("num_branches", "num_partial_branches", "covered_branches", "missing_branches")
    tot = report["totals"]
    return {
        "branch_coverage": report["meta"]["branch_coverage"],
        "totals_branch": {k: tot.get(k, "<absent>") for k in keys},
        "totals_extra_keys": sorted(set(tot) - {"covered_lines", "num_statements", "percent_covered",
                                               "missing_lines", "excluded_lines"} - set(keys)),
        "files": {name: {k: v["summary"].get(k, "<absent>") for k in keys}
                  for name, v in sorted(report["files"].items())},
        "files_extra_keys": {name: sorted(set(v["summary"]) - {"covered_lines", "num_statements", "percent_covered",
                                                              "missing_lines", "excluded_lines"} - set(keys))
                             for name, v in sorted(report["files"].items())},
    }


def xml_totals(cov, morfs, out):
    cov.xml_report(morfs, outfile=out)
    root = xml.dom.minidom.parse(out).documentElement
    return {a: root.getAttribute(a) for a in ("branches-valid", "branches-covered", "lines-valid", "lines-covered")}


def run(name, fn):
    try:
        res = fn()
    except Exception as exc:  # 候选可能在某些情形下抛异常：记录下来，不中断其它情形
        res = {"error": "%s: %s" % (type(exc).__name__, exc)}
    print("PROBE " + json.dumps({"scenario": name, "result": res}, sort_keys=True))


def s1_single():
    write("p1_branchy", BRANCHY)
    cov = coverage.Coverage(branch=True, data_file="p1.coverage")
    cov.start()
    mod = importlib.import_module("p1_branchy")
    cov.stop()
    cov.json_report([mod], outfile="p1.json")
    return dict(brief(load("p1.json")), xml=xml_totals(cov, [mod], "p1.xml"))


def s2_two_files():
    write("p2_branchy", BRANCHY)
    write("p2_main", EXAMPLE_AFTER_IMPORT.format(other="p2_branchy"))
    cov = coverage.Coverage(branch=True, data_file="p2.coverage")
    cov.start()
    main = importlib.import_module("p2_main")
    cov.stop()
    cov.json_report([main, main.p2_branchy], outfile="p2.json")
    cov.save()
    return dict(brief(load("p2.json")), xml=xml_totals(cov, [main, main.p2_branchy], "p2.xml"))


def s3_saved_two_files():
    # 依赖 s2 保存的数据：新对象不设 branch，读回后出报告
    cov = coverage.Coverage(data_file="p2.coverage")
    cov.load()
    cov.json_report(["p2_main.py", "p2_branchy.py"], outfile="p3.json")
    return brief(load("p3.json"))


def s4_cli_two_files():
    write("p4_branchy", BRANCHY)
    write("p4_main", EXAMPLE_AFTER_IMPORT.format(other="p4_branchy"))
    env = dict(os.environ, COVERAGE_FILE=os.path.join(work, "p4.coverage"), PYTHONPATH=work)
    r1 = subprocess.run([PY, "-m", "coverage", "run", "--branch", "p4_main.py"], env=env,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    r2 = subprocess.run([PY, "-m", "coverage", "json", "-o", "p4.json", "--include=" + work + "/*"], env=env,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    if r2.returncode != 0 or not os.path.exists("p4.json"):
        return {"run_rc": r1.returncode, "json_rc": r2.returncode, "out": (r1.stdout + r2.stdout)[-800:]}
    return dict(brief(load("p4.json")), run_rc=r1.returncode, json_rc=r2.returncode)


def s5_zero_branches():
    write("p5_flat", NO_BRANCH)
    cov = coverage.Coverage(branch=True, data_file="p5.coverage")
    cov.start()
    mod = importlib.import_module("p5_flat")
    cov.stop()
    cov.json_report([mod], outfile="p5.json")
    return brief(load("p5.json"))


def s6_line_mode_two_files():
    write("p6_branchy", BRANCHY)
    write("p6_main", EXAMPLE_AFTER_IMPORT.format(other="p6_branchy"))
    cov = coverage.Coverage(data_file="p6.coverage")
    cov.start()
    main = importlib.import_module("p6_main")
    cov.stop()
    cov.json_report([main, main.p6_branchy], outfile="p6.json")
    return brief(load("p6.json"))


def s7_report_return_value():
    # report() 的返回值（--fail-under 用）：两文件分支模式
    write("p7_branchy", BRANCHY)
    write("p7_main", EXAMPLE_AFTER_IMPORT.format(other="p7_branchy"))
    cov = coverage.Coverage(branch=True, data_file="p7.coverage")
    cov.start()
    main = importlib.import_module("p7_main")
    cov.stop()
    return {"json_report_return": cov.json_report([main, main.p7_branchy], outfile="p7.json"),
            "report_return": cov.report([main, main.p7_branchy], file=open(os.devnull, "w"))}


print("PROBE_COVERAGE " + json.dumps({"version": coverage.__version__, "file": coverage.__file__}))
for name, fn in [("S1_single_branchy", s1_single), ("S2_two_files", s2_two_files),
                 ("S3_saved_reload_no_branch_cfg", s3_saved_two_files), ("S4_cli_run_branch_then_json", s4_cli_two_files),
                 ("S5_branch_mode_zero_branches", s5_zero_branches), ("S6_line_mode_two_files", s6_line_mode_two_files),
                 ("S7_report_return", s7_report_return_value)]:
    run(name, fn)
