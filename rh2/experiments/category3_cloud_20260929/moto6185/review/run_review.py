"""复核者私有对照与私有模拟评分（moto-6185）。不是正式评分。

每个变体：一次性容器（原镜像 c3keep/moto6185:src、--network none、root）→ git apply 候选 →
  1) probe_review.py 行为探针；
  2) 依次套用各测试版本（原材料、v2、v2s、复核者 v3 草案），运行评分包的测试命令
     `pytest -n0 -rA` 跑 tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py，
     按 SWE 解析规则（状态词 + 节点名取到第一个空白为止，两个带空格的 `[set …]` 节点因此合并为一个键）
     逐项核对参考名单：F2P 1 项、P2P 34 项，全部 PASSED 记 1；
  3) 可选：tests/test_dynamodb 全套。
启动每个容器前等待，直到全机运行中的容器少于 3 个；同一时间最多 --workers 个本脚本的容器。

用法：python run_review.py --out <目录> [--workers 2] [--suite 变体,...] 变体名...
变体名：base、gold、作者候选（../<名>.patch）、复核者候选（candidates/<名>.patch）。
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
REPO = HERE.parents[3]
INGEST = REPO / "docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest"
IID = "getmoto__moto-6185"
IMAGE = "c3keep/moto6185:src"
TEST_FILE = "tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py"
PATH = "/opt/miniconda3/envs/testbed/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


def bundle(name):
    for line in open(INGEST / name):
        d = json.loads(line)
        if d.get("instance_id") == IID:
            return d
    raise KeyError(name)


GRADING = bundle("grading_bundles_v2_v0.jsonl")
GOLD = bundle("validation_bundles_v0.jsonl")["golden_patch"]
F2P, P2P = GRADING["fail_to_pass"], GRADING["pass_to_pass"]
EVAL_CMD = GRADING["eval_cmd"]  # pytest -n0 -rA
TESTS = {
    "orig": GRADING["test_patch"],
    "v2": (EXP / "revised_test_v2.patch").read_text(),
    "v2s": (EXP / "revised_test_v2s.patch").read_text(),
    "v3d": (HERE / "revised_test_v3_draft.patch").read_text(),
}


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def candidate_patch(name):
    if name == "base":
        return None
    if name == "gold":
        return GOLD
    for p in (HERE / "candidates" / f"{name}.patch", EXP / f"{name}.patch"):
        if p.exists():
            return p.read_text()
    raise FileNotFoundError(name)


def parse_swe(log):
    """SWE-bench/SWE-Gym 的 pytest 解析：以状态词开头的行，取第二个空白分隔字段为键。"""
    status = {}
    for line in log.splitlines():
        if any(line.startswith(s) for s in ("PASSED", "FAILED", "SKIPPED", "ERROR", "XFAIL")):
            if line.startswith("FAILED"):
                line = line.replace(" - ", " ")
            parts = line.split()
            if len(parts) > 1:
                status[parts[1]] = parts[0]
    return status


def grade(log):
    st = parse_swe(log)
    ok = lambda k: st.get(k) in ("PASSED", "XFAIL")  # noqa: E731
    f2p = sum(ok(k) for k in F2P)
    p2p = sum(ok(k) for k in P2P)
    missing = [k for k in F2P + P2P if k not in st]
    return {"reward": int(f2p == len(F2P) and p2p == len(P2P)), "f2p": f"{f2p}/{len(F2P)}",
            "p2p": f"{p2p}/{len(P2P)}", "missing": missing, "parsed": len(st)}


def failure_excerpt(log):
    """F2P 失败时，摘出测试文件中的失败行号与异常行（供结论页引用）。"""
    lines = log.splitlines()
    out = []
    for i, line in enumerate(lines):
        if line.startswith(f"{TEST_FILE}:") and ":" in line[len(TEST_FILE) + 1:]:
            out.append(line.strip())
        elif line.startswith("E ") and len(out) < 12:
            out.append(line.strip()[:160])
    return out[:12]


def dk(*a, **k):
    return subprocess.run(["docker", *a], capture_output=True, text=True, **k)


def wait_slot():
    while int(len(dk("ps", "-q").stdout.split())) >= 3:
        time.sleep(20)


def run_variant(name, out, suite):
    vd = out / name
    vd.mkdir(parents=True, exist_ok=True)
    patch = candidate_patch(name)
    cname = f"rv6185-{name[:18]}-{uuid.uuid4().hex[:6]}"
    rec = {"variant": name, "candidate_sha256": sha(patch) if patch else None}
    wait_slot()
    try:
        r = dk("run", "-d", "--rm", "--network", "none", "--name", cname, "--entrypoint", "sleep", IMAGE, "3600")
        assert r.returncode == 0, r.stderr
        dk("exec", cname, "mkdir", "-p", "/in")
        tmp = vd / "_in"
        tmp.mkdir(exist_ok=True)
        if patch:
            (tmp / "candidate.patch").write_text(patch)
        for ver, text in TESTS.items():
            (tmp / f"test_{ver}.patch").write_text(text)
        (tmp / "probe_review.py").write_text((HERE / "probe_review.py").read_text())
        for f in tmp.iterdir():
            dk("cp", str(f), f"{cname}:/in/{f.name}")
        ex = lambda cmd, t=900: dk("exec", "-e", f"PATH={PATH}", "-w", "/testbed", cname,  # noqa: E731
                                   "timeout", str(t), "bash", "-c", cmd)
        if patch:
            a = ex("git apply /in/candidate.patch")
            rec["apply_rc"] = a.returncode
            assert a.returncode == 0, a.stderr
        rec["worktree_diff_sha256"] = sha(ex("git diff -- moto").stdout)
        p = ex("python /in/probe_review.py", 600)
        (vd / "probe.jsonl").write_text(p.stdout)
        if p.returncode != 0:
            (vd / "probe.stderr").write_text(p.stderr[-4000:])
        rec["probe"] = {json.loads(l)["row"]: json.loads(l) for l in p.stdout.splitlines() if l.startswith("{")}
        rec["tests"] = {}
        for ver in TESTS:
            cmd = (f"git apply /in/test_{ver}.patch && TEST_SERVER_MODE=false {EVAL_CMD} -p no:cacheprovider "
                   f"--tb=short {TEST_FILE}; rc=$?; git checkout -q -- {TEST_FILE}; exit $rc")
            t = ex(cmd)
            log = t.stdout + t.stderr
            g = grade(log)
            g["pytest_rc"] = t.returncode
            g["tail"] = [l for l in log.splitlines() if l.startswith("=")][-1:]
            if g["reward"] == 0:
                g["excerpt"] = failure_excerpt(log)
            rec["tests"][ver] = g
            summary = "\n".join(l for l in log.splitlines()
                                if l.startswith(("PASSED", "FAILED", "ERROR", "SKIPPED", "=", "E ", TEST_FILE)))
            (vd / f"test_{ver}.txt").write_text(summary)
        if name in suite:
            s = ex("TEST_SERVER_MODE=false python -m pytest -p no:cacheprovider -n0 -q -rf tests/test_dynamodb", 1800)
            lines = (s.stdout + s.stderr).splitlines()
            rec["suite"] = {"rc": s.returncode, "tail": lines[-1:] if lines else [],
                            "failed": [l for l in lines if l.startswith("FAILED")][:20]}
    except Exception as e:  # noqa: BLE001
        rec["error"] = repr(e)[:500]
    finally:
        dk("rm", "-f", cname)
        for f in (vd / "_in").glob("*"):
            f.unlink()
        (vd / "_in").rmdir()
    (vd / "record.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1, default=str))
    print(name, {v: rec.get("tests", {}).get(v, {}).get("reward") for v in TESTS}, rec.get("error", ""), flush=True)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--suite", default="")
    ap.add_argument("variants", nargs="+")
    ns = ap.parse_args()
    out = Path(ns.out)
    out.mkdir(parents=True, exist_ok=True)
    suite = set(filter(None, ns.suite.split(",")))
    with ThreadPoolExecutor(max_workers=min(ns.workers, 2)) as pool:
        recs = list(pool.map(lambda v: run_variant(v, out, suite), ns.variants))
    meta = {"image": IMAGE, "eval_cmd": EVAL_CMD, "test_file": TEST_FILE,
            "tests_sha256": {k: sha(v) for k, v in TESTS.items()}, "gold_sha256": sha(GOLD),
            "f2p": F2P, "p2p_count": len(P2P)}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(json.dumps({r["variant"]: {v: r.get("tests", {}).get(v, {}).get("reward") for v in TESTS} for r in recs}))


if __name__ == "__main__":
    sys.exit(main())
