#!/usr/bin/env python3
"""R2E 修订草案的试跑（2026-09-29，单题闭环试行）。**不是正式评分**，只给修订定稿前的快速对照。

在本机派生镜像的一次性容器里（不联网）按正式 grader 的顺序做：
  应用候选补丁（root，排除 r2e_tests/）→ 删 /testbed/r2e_tests，从镜像私有位置 /rh2_private/r2e_tests 复制隐藏测试
  → 在复制件上应用修订草案 → 工作区属主给评分用户 → 以 uid 54322 在 Start / End 标记之间跑来源入口 `bash run_tests.sh`
  → 用正式解析器（r2e_parsers.parse_log_pytest + normalize_status_map）解析标记之间的段，与期望逐键比。
与正式评分的差别：不做基线重建比对；不核隐藏测试树与入口摘要（草案改了测试，摘要必然不同）；权限布置简化为
整个 /testbed 给评分用户。所以试跑结果只作修订方向的依据，定稿后必须走正式材料（修订单、派生镜像材料步骤）与正式评分。

用法（远端，从 rh2/）：
  .venv/bin/python experiments/r2e_lifecycle_20260929/trial_grade.py --task <instance_id> --patch <文件|none>
      [--edits <draft.json>] [--expected <expected.json>|current] --out <结果.json> [--timeout 1800]
draft.json：{"revisions": [{"kind": "hidden_test_text_replace", "target": "<相对 r2e_tests/ 的路径>",
                             "edits": [{"old": "...", "new": "..."}]},
                            {"kind": "hidden_test_file_add", "target": "...", "content": "..."}]}
  每条 edit 的 old 在当前文本里必须恰好出现一次（与正式修订单同一纪律）。
--expected：修订后的完整期望映射 {键: 状态} 的文件；`current` = 当前正式材料里的期望映射；不给则只输出观测映射。
派生镜像取 /work/r2e/derived/*/<instance_id>/facts.json 里 ok 的那次构建。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

RH2 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RH2 / "src"))

from repoharness2.envpack import scoring  # noqa: E402
from repoharness2.envpack.r2e_parsers import normalize_status_map, parse_log_pytest  # noqa: E402

DERIVED_ROOT = Path("/work/r2e/derived")
START, END = scoring.R2E_EVAL_START_MARKER, scoring.R2E_EVAL_END_MARKER

APPLY_EDITS_PY = r'''
import json, sys
from pathlib import Path
d = json.loads(Path(sys.argv[1]).read_text())
root = Path("/testbed/r2e_tests")
for rev in d.get("revisions", []):
    rel = Path(rev["target"])
    if rel.is_absolute() or ".." in rel.parts:
        raise SystemExit("unsafe_target:" + rev["target"])
    tgt = root / rel
    if rev["kind"] == "hidden_test_text_replace":
        s = tgt.read_text()
        for e in rev["edits"]:
            n = s.count(e["old"])
            if n != 1:
                raise SystemExit("edit_not_unique:%s:%d:%r" % (rev["target"], n, e["old"][:80]))
            s = s.replace(e["old"], e["new"])
        tgt.write_text(s)
    elif rev["kind"] == "hidden_test_file_add":
        if tgt.exists():
            raise SystemExit("add_target_exists:" + rev["target"])
        tgt.parent.mkdir(parents=True, exist_ok=True)
        tgt.write_text(rev["content"])
    else:
        raise SystemExit("unknown_kind:" + rev["kind"])
print("RH2_TRIAL_EDITS_APPLIED=%d" % len(d.get("revisions", [])))
'''


def derived_image(iid: str) -> tuple[str, str | None]:
    for facts in sorted(DERIVED_ROOT.glob(f"*/{iid}/facts.json")):
        d = json.loads(facts.read_text())
        if d.get("ok"):
            return d["derived_image_id"], d.get("recipe_id")
    raise SystemExit(f"{iid}: /work/r2e/derived 下没有 ok 的派生镜像")


def current_expected(iid: str) -> dict[str, str]:
    from repoharness2.envpack.ingest_r2e_subset import load_trusted_r2e_ingest_outputs

    trusted = load_trusted_r2e_ingest_outputs(RH2.parent)
    for g in trusted.result.grading_bundles:
        if g.instance_id == iid:
            return g.expected_map()
    raise SystemExit(f"{iid}: 正式材料里没有这道题")


def dk(*args: str, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, errors="replace", **kw)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--task", required=True)
    ap.add_argument("--patch", required=True, help="候选补丁文件；none = 不改代码（noop）")
    ap.add_argument("--edits", default=None, help="修订草案 draft.json")
    ap.add_argument("--expected", default=None, help="期望映射文件，或 current")
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=int, default=1800)
    ns = ap.parse_args()

    img, recipe = derived_image(ns.task)
    name = f"r2e-trial-{uuid.uuid4().hex[:10]}"
    res: dict = {"task": ns.task, "image": img, "recipe_id": recipe, "patch": ns.patch, "edits": ns.edits,
                 "expected": ns.expected, "kind": "trial_not_formal_grading"}
    started = time.time()
    try:
        r = dk("run", "-d", "--name", name, "--network", "none", "--label", "rh2.r2e_lifecycle=trial",
               "--entrypoint", "sleep", img, "infinity")
        if r.returncode != 0:
            res["verdict"] = f"container_failed:{r.stderr[-300:]}"
            return 1
        dk("exec", name, "git", "config", "--global", "--add", "safe.directory", "/testbed")
        if ns.patch != "none":
            dk("cp", ns.patch, f"{name}:/tmp/cand.patch")
            a = dk("exec", "-w", "/testbed", name, "bash", "-c",
                   "git apply --exclude='r2e_tests/*' -v /tmp/cand.patch 2>&1 | tail -20; echo RH2_APPLY_RC=${PIPESTATUS[0]}")
            res["apply"] = a.stdout[-4000:]
            if "RH2_APPLY_RC=0" not in a.stdout:
                res["verdict"] = "patch_apply_failed"
                return 1
        rs = dk("exec", name, "bash", "-c",
                "rm -rf /testbed/r2e_tests && cp -r /rh2_private/r2e_tests /testbed/r2e_tests"
                " && find /testbed/r2e_tests -type d -name __pycache__ -prune -exec rm -rf {} +")
        if rs.returncode != 0:
            res["verdict"] = f"restore_failed:{rs.stderr[-300:]}"
            return 1
        if ns.edits:
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
                fh.write(APPLY_EDITS_PY)
            dk("cp", fh.name, f"{name}:/tmp/apply_edits.py")
            dk("cp", ns.edits, f"{name}:/tmp/draft.json")
            e = dk("exec", name, "/testbed/.venv/bin/python", "/tmp/apply_edits.py", "/tmp/draft.json")
            res["edits_apply"] = (e.stdout + e.stderr)[-2000:]
            if e.returncode != 0:
                res["verdict"] = "edits_failed"
                return 1
        dk("exec", name, "chown", "-R", "54322:54322", "/testbed")
        script = (f"cd /testbed; echo RH2_INSTALL_SKIPPED=1; echo '{START}'; bash run_tests.sh; RC=$?; "
                  f"echo '{END}'; echo RH2_TEST_RC=$RC")
        t0 = time.time()
        r = dk("exec", "-u", "54322:54322", "-w", "/testbed", "-e", "HOME=/tmp", name,
               "timeout", str(ns.timeout), "bash", "-c", script)
        res["test_seconds"] = round(time.time() - t0, 1)
        log = r.stdout
        seg = log.split(START, 1)[1].split(END, 1)[0] if (START in log and END in log) else ""
        obs = normalize_status_map(parse_log_pytest(seg))
        res.update(markers=bool(seg), observed=obs, n_observed=len(obs), log_tail=log[-8000:], stderr_tail=r.stderr[-2000:])
        if ns.expected:
            raw = current_expected(ns.task) if ns.expected == "current" else json.loads(Path(ns.expected).read_text())
            exp = normalize_status_map(raw)
            missing = sorted(set(exp) - set(obs))
            extra = sorted(set(obs) - set(exp))
            diff = [[k, exp[k], obs[k]] for k in sorted(exp) if k in obs and exp[k] != obs[k]]
            res.update(expected_n=len(exp), missing=missing, extra=extra, status_diff=diff,
                       match=not (missing or extra or diff))
            res["verdict"] = "match" if res["match"] else "mismatch"
        else:
            res["verdict"] = "observed_only"
        return 0
    finally:
        dk("rm", "-f", name)
        res["seconds"] = round(time.time() - started, 1)
        out = Path(ns.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        summary = {k: res.get(k) for k in ("task", "verdict", "n_observed", "expected_n", "missing", "extra", "status_diff", "seconds")}
        print(json.dumps(summary, ensure_ascii=False)[:4000])


if __name__ == "__main__":
    sys.exit(main())
