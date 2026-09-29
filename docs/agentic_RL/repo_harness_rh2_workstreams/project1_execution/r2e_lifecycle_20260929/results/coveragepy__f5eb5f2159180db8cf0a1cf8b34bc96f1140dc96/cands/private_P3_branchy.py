# P-3（主审 §7）：gold 下用 API 测 BRANCHY，同时出 XML，并按"先 run --branch、另起报告对象"再出一次 JSON。
import importlib, json, os, re, sys, tempfile, textwrap
import coverage
d = tempfile.mkdtemp()
os.chdir(d)
sys.path.insert(0, d)
src = textwrap.dedent("""\
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
    """)
open("branchy.py", "w").write(src)
data = os.path.join(d, ".coverage")
cov = coverage.Coverage(branch=True, data_file=data)
cov.start()
mod = importlib.import_module("branchy")
cov.stop()
cov.json_report([mod], outfile="r.json")
t = json.load(open("r.json"))["totals"]
print("P3 JSON totals", json.dumps({k: v for k, v in t.items() if "branch" in k}, sort_keys=True))
cov.xml_report([mod], outfile="r.xml")
print("P3 XML", re.search(r"<coverage [^>]*>", open("r.xml").read()).group(0))
cov.save()
cov2 = coverage.Coverage(data_file=data)
cov2.load()
cov2.json_report([mod], outfile="r2.json")
t2 = json.load(open("r2.json"))
print("P3 SAVED meta.branch_coverage", t2["meta"].get("branch_coverage"),
      json.dumps({k: v for k, v in t2["totals"].items() if "branch" in k}, sort_keys=True))
