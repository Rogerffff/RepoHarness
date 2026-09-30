# 复核者行为探针（私有对照）：在容器内以 /testbed 的 coverage 运行。
# 输出各场景的 totals 与逐文件 summary，供按公开需求判断对错（不以 gold 为答案）。
import json, os, subprocess, sys, tempfile, textwrap, importlib
sys.path.insert(0, "/testbed")
import coverage

A = """\
a = {'b': 1}
if a.get('a'):
    b = 1
"""
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
NOBR = """\
x = 1
y = 2
"""

def pick(rep):
    t = rep["totals"]
    files = {k: v["summary"] for k, v in rep["files"].items()}
    return {"meta_branch": rep["meta"]["branch_coverage"], "totals": t, "files": files}

def api_report(mods, branch=True, reload_from_saved=False, order=None):
    d = tempfile.mkdtemp()
    os.chdir(d)
    sys.path.insert(0, d)
    srcs = {"a": A, "branchy": BRANCHY, "nobr": NOBR}
    for m in mods:
        open(m + ".py", "w").write(srcs[m])
    df = os.path.join(d, ".coverage")
    cov = coverage.Coverage(branch=branch, data_file=df)
    cov.start()
    ms = [importlib.import_module(m) for m in mods]
    cov.stop()
    if reload_from_saved:
        cov.save()
        cov = coverage.Coverage(data_file=df)
        cov.load()
    morfs = ms if order is None else [ms[i] for i in order]
    out = os.path.join(d, "out.json")
    cov.json_report(morfs, outfile=out)
    for m in mods:
        sys.modules.pop(m, None)
    sys.path.remove(d)
    return pick(json.load(open(out)))

def cli_report(mods, branch_flag=True, rc_branch=False, json_args=()):
    d = tempfile.mkdtemp()
    srcs = {"a": A, "branchy": BRANCHY, "nobr": NOBR}
    for m in mods:
        open(os.path.join(d, m + ".py"), "w").write(srcs[m])
    open(os.path.join(d, "main.py"), "w").write("".join("import %s\n" % m for m in mods))
    if rc_branch:
        open(os.path.join(d, ".coveragerc"), "w").write("[run]\nbranch = True\n")
    py = "/testbed/.venv/bin/python"
    env = dict(os.environ, PYTHONPATH="/testbed")
    run = [py, "-m", "coverage", "run", "--source=."] + (["--branch"] if branch_flag else []) + ["main.py"]
    r1 = subprocess.run(run, cwd=d, env=env, capture_output=True, text=True)
    r2 = subprocess.run([py, "-m", "coverage", "json", "-o", "cli.json"] + list(json_args), cwd=d, env=env, capture_output=True, text=True)
    res = {"run_rc": r1.returncode, "json_rc": r2.returncode, "json_err": r2.stderr[-300:]}
    try:
        rep = pick(json.load(open(os.path.join(d, "cli.json"))))
        # 只留被测模块，main.py 也会出现
        res.update(rep)
    except Exception as e:
        res["load_err"] = repr(e)
    return res

scen = {}
def run(name, fn, *a, **k):
    try:
        scen[name] = fn(*a, **k)
    except Exception as e:
        scen[name] = {"error": repr(e)[:300]}


def issue_example():
    d = tempfile.mkdtemp(); os.chdir(d); sys.path.insert(0, d)
    open("a_ex.py", "w").write(A)
    cov = coverage.Coverage(branch=True)
    cov.start()
    import a_ex
    cov.stop()
    cov.json_report(outfile='coverage.json')
    sys.path.remove(d); sys.modules.pop("a_ex", None)
    return pick(json.load(open(os.path.join(d, "coverage.json"))))

run("E0_issue_example", issue_example)

run("S1_api_a_branch", api_report, ["a"])
run("S2_api_branchy", api_report, ["branchy"])
run("S3_api_two_files", api_report, ["a", "branchy"])
run("S4_api_two_files_rev", api_report, ["a", "branchy"], order=[1, 0])
run("S5_api_two_saved", api_report, ["a", "branchy"], reload_from_saved=True)
run("S6_api_line_mode", api_report, ["a", "branchy"], branch=False)
run("S7_api_three_with_nobranch", api_report, ["a", "branchy", "nobr"])

def zero_branch_report(reload_from_saved=False):
    # 分支模式、报告的文件合计零个分支去向
    return api_report(["nobr"], reload_from_saved=reload_from_saved)

run("Z1_api_zero_branches", zero_branch_report)
run("Z2_api_zero_branches_saved", zero_branch_report, True)

run("C1_cli_branch_flag", cli_report, ["a", "branchy"], branch_flag=True)
run("C2_cli_rc_branch", cli_report, ["a", "branchy"], branch_flag=False, rc_branch=True)
run("C3_cli_line", cli_report, ["a", "branchy"], branch_flag=False)
run("C4_cli_include_one_file", cli_report, ["a", "branchy"], json_args=("--include=branchy.py",))
run("C5_cli_omit_main", cli_report, ["a", "branchy"], json_args=("--omit=main.py",))
print("PROBE_JSON " + json.dumps(scen, sort_keys=True))
