"""私有模拟评分驱动：每个候选一个全新、断网、root 的一次性容器（semantic_control.py），
依次跑 5 版隐藏测试（原版、现行 R-c、历史窄 R-b、R-c v2、R-b v2）、公开 tests/test_json.py 与行为矩阵，
再用 grade_r2e.py（RH2 移植的上游 parse_log_pytest + prime_calculate_reward）逐键对照期望映射。

用法：python run_matrix.py <输出目录> <候选,...>
每起一个容器前先等到机器上运行的容器少于 3 个（共用机器的约定）；同一时间只起 1 个本题容器。
这是私有模拟，不是 R2E 正式评分链。
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RH2 = HERE.parents[2]
SEMCTL = RH2 / "experiments/task2_swegym_dev_20260925/semantic_control.py"
IMAGE = "c3keep/coveragepy_f5eb:src"  # = namanjain12/coveragepy_final@sha256:fb0335af…（摘要已核）

out = Path(sys.argv[1]).resolve()
cands = sys.argv[2].split(",")
out.mkdir(parents=True, exist_ok=True)

MATERIALS = {  # 命令 id → (隐藏测试文件, 期望映射, 以哪个身份跑)
    "h0_orig": (None, "expected_output_orig.json", "root"),
    "h1_v8rc": ("hidden_test_1_v8_rc.py", "expected_output_v8_rc.json", "root"),
    "h2_histrb": ("hidden_test_1_hist_rb.py", "expected_output_v8_rc.json", "root"),
    "h3_rc2": ("hidden_test_1_rc2.py", "expected_output_rc2.json", "root"),
    "h4_rb2": ("hidden_test_1_rb2.py", "expected_output_rc2.json", "root"),
    "h3u_rc2": ("hidden_test_1_rc2.py", "expected_output_rc2.json", "uid54322"),
    "h4u_rb2": ("hidden_test_1_rb2.py", "expected_output_rc2.json", "uid54322"),
}


def hidden_cmd(test_file, who):
    cp = "rm -rf /testbed/r2e_tests && cp -r /r2e_tests /testbed/r2e_tests"
    if test_file:
        cp += f" && cp /in/{test_file} /testbed/r2e_tests/test_1.py"
    if who == "root":
        run = "bash /in/run_tests.sh 2>&1"
    else:  # 与正式评分同类的非 root 身份（私有近似：只换 uid，不套正式 profile）
        # 来源镜像的解释器在 0700 的 /root 下；正式派生镜像会搬迁解释器，这里在一次性容器里放开 /root 的遍历权限代替
        # 前面 root 跑过的测试在 /tmp/coverage_test 留下 root 的目录，换一个该身份自己的 TMPDIR
        run = ("chmod 755 /root && chown -R 54322:54322 /testbed && rm -rf /tmp/u54322 && mkdir -p /tmp/u54322 "
               "&& chown 54322:54322 /tmp/u54322 && HOME=/tmp/u54322 TMPDIR=/tmp/u54322 "
               "setpriv --reuid=54322 --regid=54322 --clear-groups bash /in/run_tests.sh 2>&1")
    return f"{cp} && sha256sum /testbed/r2e_tests/test_1.py && {run}; rm -rf /testbed/r2e_tests"


files = {n: str(HERE / n) for n in ["run_tests.sh", "probe_matrix.py", "hidden_test_1_v8_rc.py",
                                     "hidden_test_1_hist_rb.py", "hidden_test_1_rc2.py", "hidden_test_1_rb2.py"]}
commands = [{"id": k, "cmd": hidden_cmd(v[0], v[2]), "timeout_s": 900} for k, v in MATERIALS.items() if v[2] == "root"]
commands += [
    {"id": "pub_test_json", "timeout_s": 900,
     "cmd": "PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/test_json.py -rA -o cache_dir=/tmp/rh2_pytest_cache 2>&1"},
    {"id": "probe", "timeout_s": 600, "cmd": "rm -rf /tmp/probe && python /in/probe_matrix.py /tmp/probe 2>&1"},
]
commands += [{"id": k, "cmd": hidden_cmd(v[0], v[2]), "timeout_s": 900} for k, v in MATERIALS.items() if v[2] != "root"]

for cand in cands:
    while int(subprocess.run("docker ps -q | wc -l", shell=True, capture_output=True, text=True).stdout.strip()) >= 3:
        time.sleep(20)
    prep = [] if cand == "base" else [f"git apply /in/{cand}.patch"]
    spec_files = dict(files)
    if cand != "base":
        spec_files[f"{cand}.patch"] = str(HERE / f"{cand}.patch")
    spec = {"image": IMAGE, "python_prefix": "/testbed/.venv", "variants": {cand: prep},
            "files": spec_files, "commands": commands}
    spec_path = out / f"spec_{cand}.json"
    spec_path.write_text(json.dumps(spec, indent=1))
    t0 = time.time()
    r = subprocess.run([sys.executable, str(SEMCTL), str(spec_path), "--out", str(out)], capture_output=True, text=True)
    (out / "summary.json").replace(out / f"summary_{cand}.json")
    print(json.dumps({"cand": cand, "wall_s": round(time.time() - t0, 1), "rc": r.returncode,
                      "stderr_tail": r.stderr[-300:]}), flush=True)

# 逐键评分
grades = out / "grades.jsonl"
with grades.open("a") as g:
    for cand in cands:
        for mid, (_, exp, _) in MATERIALS.items():
            log = out / cand / f"{mid}.out"
            if not log.exists():
                continue
            r = subprocess.run([str(RH2 / ".venv/bin/python"), str(HERE / "grade_r2e.py"), str(log), str(HERE / exp)],
                               capture_output=True, text=True)
            res = json.loads(r.stdout)
            g.write(json.dumps({"cand": cand, "material": mid, **res}, ensure_ascii=False) + "\n")
            print(cand, mid, res["reward"], sorted(res["mismatch"]), res["unexpected"], flush=True)
