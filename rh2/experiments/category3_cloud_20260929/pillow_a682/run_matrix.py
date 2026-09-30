"""私有模拟评分驱动（pillow__a682ceaf）：每个候选一个全新、断网、root 的一次性容器（semantic_control.py），
依次跑选定版本的隐藏测试、公开测试 Tests/test_file_gif.py 与 Tests/test_image_convert.py、行为矩阵 probe_matrix.py，
再用 grade_r2e.py（RH2 移植的上游 parse_log_pytest + prime_calculate_reward）逐键对照期望映射。

用法：python run_matrix.py <输出目录> <候选,...> <隐藏测试版本 id,...>
每起一个容器前先等到机器上运行的容器少于 3 个（共用机器的约定）；同一时间只起 1 个本题容器。
这是私有模拟，不是 R2E 正式评分链。
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RH2 = HERE.parents[2]
SEMCTL = RH2 / "experiments/task2_swegym_dev_20260925/semantic_control.py"
GRADE = RH2 / "experiments/category3_cloud_20260929/pillow3a61/grade_r2e.py"
IMAGE = "c3keep/pillow_a682:src"  # = namanjain12/pillow_final@sha256:c9ee334c…5733（摘要已核）

# 命令 id → (替换进 r2e_tests/test_1.py 的文件，None 表示镜像原件；期望映射；运行身份)
MATERIALS = {
    "h0_orig": (None, "expected_output_orig.json", "root"),
    "h1_rev1": ("hidden_test_1_revised_v1.py", "expected_output_orig.json", "root"),
    "h1u_rev1": ("hidden_test_1_revised_v1.py", "expected_output_orig.json", "uid54322"),
    "h2_rev1_nowarn": ("hidden_test_1_revised_v1_nowarn.py", "expected_output_orig.json", "root"),
    "h3_rev2": ("hidden_test_1_revised_v2.py", "expected_output_orig.json", "root"),
    "h3u_rev2": ("hidden_test_1_revised_v2.py", "expected_output_orig.json", "uid54322"),
}

out = Path(sys.argv[1]).resolve()
cands = sys.argv[2].split(",")
mats = sys.argv[3].split(",")
out.mkdir(parents=True, exist_ok=True)


def hidden_cmd(test_file, who):
    cp = "rm -rf /testbed/r2e_tests && cp -r /r2e_tests /testbed/r2e_tests"
    if test_file:
        cp += f" && cp /in/{test_file} /testbed/r2e_tests/test_1.py"
    if who == "root":
        run = "bash /in/run_tests.sh 2>&1"
    else:  # 与正式评分同类的非 root 身份（私有近似：只换 uid，不套正式 profile）
        # 来源镜像的解释器在 0700 的 /root 下（派生镜像会搬迁），这里在一次性容器里放开 /root 的遍历权限代替
        run = ("chmod 755 /root && chown -R 54322:54322 /testbed && rm -rf /tmp/u54322 && mkdir -p /tmp/u54322 "
               "&& chown 54322:54322 /tmp/u54322 && HOME=/tmp/u54322 TMPDIR=/tmp/u54322 "
               "setpriv --reuid=54322 --regid=54322 --clear-groups bash /in/run_tests.sh 2>&1")
    return f"{cp} && sha256sum /testbed/r2e_tests/test_1.py && {run}; rm -rf /testbed/r2e_tests"


PROBE = os.environ.get("C3_PROBE", "probe_matrix.py")  # v2 起用 probe_matrix_v2.py
files = {"run_tests.sh": str(HERE / "run_tests.sh"), PROBE: str(HERE / PROBE)}
for m in mats:
    if MATERIALS[m][0]:
        files[MATERIALS[m][0]] = str(HERE / MATERIALS[m][0])
commands = [{"id": m, "cmd": hidden_cmd(MATERIALS[m][0], MATERIALS[m][2]), "timeout_s": 900}
            for m in mats if MATERIALS[m][2] == "root"]
commands += [
    {"id": "pub_tests", "timeout_s": 900,
     "cmd": "PYTHONDONTWRITEBYTECODE=1 python -m pytest Tests/test_file_gif.py Tests/test_image_convert.py "
            "-p no:cacheprovider -q --color=no 2>&1 | tail -n 15; echo \"pytest_rc=${PIPESTATUS[0]}\""},
    {"id": "probe", "timeout_s": 600, "cmd": f"rm -rf /tmp/probe && python /in/{PROBE} /tmp/probe 2>&1"},
]
# 非 root 身份放最后：它会 chown /testbed 并放开 /root
commands += [{"id": m, "cmd": hidden_cmd(MATERIALS[m][0], MATERIALS[m][2]), "timeout_s": 900}
             for m in mats if MATERIALS[m][2] != "root"]

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

# 逐键评分（上游口径 prime_calculate_reward；RH2 生产用并集口径，本题键集下两者一致性另行抽查）
grades = out / "grades.jsonl"
with grades.open("a") as g:
    for cand in cands:
        row = {"variant": cand}
        for m in mats:
            log = out / cand / f"{m}.out"
            if not log.exists():
                row[m] = "missing"
                continue
            res = subprocess.run([sys.executable, str(GRADE), str(log), str(HERE / MATERIALS[m][1])],
                                 capture_output=True, text=True)
            row[m] = json.loads(res.stdout) if res.returncode == 0 else {"grade_error": res.stderr[-300:]}
        g.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps({"variant": cand, **{m: (row[m]["reward"] if isinstance(row[m], dict) and "reward" in row[m]
                                                   else row[m]) for m in mats}}), flush=True)
