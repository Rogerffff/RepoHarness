"""dask__dask-7305 复核者的私有对照与私有模拟评分驱动（一次性、断网、root 容器；不是正式评分）。

用法：
  python run_private.py matrix <输出目录> <候选...>
  python run_private.py grade  <输出目录> <测试补丁名,...> <候选...>

候选名：base | gold | 作者候选（../candidates/<名>.patch）| 复核者候选（candidates/<名>.patch）。
测试补丁名：orig（ingest 原 test_patch）| v1（../revised_test_v1.patch）| 本目录下的 <名>.patch。
grade 模式对每个测试补丁：复位 → 应用候选 → 应用测试补丁 → 按评分包命令
`pytest -n0 -rA --color=no dask/dataframe/tests/test_shuffle.py` 运行，保存完整输出，
再按 grading bundle 的 F2P／P2P 参考名单逐项判分（全部 PASSED 为 1）。
运行中的容器 >= 3 时等待（共用机器规则）。
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUTHOR = HERE.parent
ROOT = HERE.parents[4]
INGEST = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest"
IMAGE = "c3keep/dask7305:src"
IID = "dask__dask-7305"
PY = "/opt/miniconda3/envs/testbed/bin"
TEST_CMD = "pytest -n0 -rA --color=no dask/dataframe/tests/test_shuffle.py"


def bundle(fn):
    for line in open(INGEST / fn):
        d = json.loads(line)
        if d.get("instance_id") == IID:
            return d
    raise KeyError(fn)


def wait_free():
    while int(subprocess.run("docker ps -q | wc -l", shell=True, capture_output=True, text=True).stdout.strip() or 0) >= 3:
        time.sleep(10)


def cand_patch(name):
    if name == "base":
        return None
    if name == "gold":
        p = HERE / "work" / "gold.patch"
        p.parent.mkdir(exist_ok=True)
        p.write_text(bundle("validation_bundles_v0.jsonl")["golden_patch"])
        return p
    for d in (HERE / "candidates", AUTHOR / "candidates"):
        if (d / f"{name}.patch").exists():
            return d / f"{name}.patch"
    raise FileNotFoundError(name)


def test_patch(name):
    if name == "orig":
        p = HERE / "work" / "orig_test.patch"
        p.parent.mkdir(exist_ok=True)
        p.write_text(bundle("grading_bundles_v2_v0.jsonl")["test_patch"])
        return p
    if name == "v1":
        return AUTHOR / "revised_test_v1.patch"
    return HERE / f"{name}.patch"


def docker_run(mounts, script, timeout=1800):
    wait_free()
    args = ["docker", "run", "--rm", "--network", "none", "-e", f"PATH={PY}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "-w", "/testbed"]
    for src, dst in mounts:
        args += ["-v", f"{src}:{dst}:ro"]
    args += [IMAGE, "bash", "-c", script]
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout + r.stderr


def judge(output):
    g = bundle("grading_bundles_v2_v0.jsonl")
    status = {}
    for line in output.splitlines():
        m = re.match(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) (\S+)", line)
        if m:
            status.setdefault(m.group(2), m.group(1))
    f2p = {t: status.get(t, "MISSING") for t in g["fail_to_pass"]}
    p2p_bad = {t: status.get(t, "MISSING") for t in g["pass_to_pass"] if status.get(t) != "PASSED"}
    reward = int(all(v == "PASSED" for v in f2p.values()) and not p2p_bad)
    return {"reward": reward, "f2p": f2p, "p2p_bad": p2p_bad, "p2p_total": len(g["pass_to_pass"])}


def main():
    mode, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    if mode == "matrix":
        cands = sys.argv[3:]
        for c in cands:
            cp = cand_patch(c)
            apply = f"git apply /in/cand.patch && " if cp else ""
            mounts = [(HERE / "matrix.py", "/in/matrix.py")] + ([(cp, "/in/cand.patch")] if cp else [])
            rc, log = docker_run(mounts, f"set -e; {apply} python /in/matrix.py")
            (out / f"{c}.jsonl").write_text(log)
            print(c, "rc", rc, time.strftime("%H:%M:%S"), flush=True)
    elif mode == "grade":
        tests = sys.argv[3].split(",")
        cands = sys.argv[4:]
        for c in cands:
            cp = cand_patch(c)
            for t in tests:
                tp = test_patch(t)
                apply = "git apply /in/cand.patch && " if cp else ""
                mounts = [(tp, "/in/test.patch")] + ([(cp, "/in/cand.patch")] if cp else [])
                cmd = TEST_CMD
                uid = os.environ.get("RUN_UID")
                if uid:  # 以非 root 身份运行测试（补丁仍由 root 应用），用于核对评分身份的影响
                    cmd = f"setpriv --reuid={uid} --regid={uid} --clear-groups env HOME=/tmp {TEST_CMD}"
                script = f"set -o pipefail; git status --short; {apply} git apply /in/test.patch && echo APPLIED_OK && {cmd}"
                t0 = time.time()
                rc, log = docker_run(mounts, script)
                tag = f"__uid{os.environ['RUN_UID']}" if os.environ.get("RUN_UID") else ""
                n = 0
                while (out / f"{c}__{t}{tag}{'' if n == 0 else f'__r{n}'}.log").exists():
                    n += 1
                (out / f"{c}__{t}{tag}{'' if n == 0 else f'__r{n}'}.log").write_text(log)
                res = judge(log) if "APPLIED_OK" in log else {"reward": None, "apply_failed": True}
                res.update({"candidate": c, "test": t, "rc": rc, "seconds": round(time.time() - t0, 1), "uid": os.environ.get("RUN_UID", "0")})
                with open(out / "results.jsonl", "a") as f:
                    f.write(json.dumps(res, sort_keys=True) + "\n")
                print(c, t, "reward", res["reward"], "rc", rc, res["seconds"], "s", time.strftime("%H:%M:%S"), flush=True)


if __name__ == "__main__":
    main()
