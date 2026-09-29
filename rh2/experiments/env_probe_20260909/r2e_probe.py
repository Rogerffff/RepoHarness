#!/usr/bin/env python3
"""R2E-Gym 环境探针 runner（B 线，2026-09-09）。

对 R2E-Gym-Subset 候选任务（冻结 revision e8b9fcb…）在 fresh 容器里执行：
  facts   镜像身份 / HEAD / 修复提交是否在 git 历史中可达 / venv / 测试目录
  noop    无修改：恢复 /r2e_tests → /testbed/r2e_tests，运行 run_tests.sh，
          与 expected_output_json 按“预期状态映射精确匹配”判 reward，预期 0
  gold    由 parsed_commit_content 重建非测试 .py 文件的 unified diff（与 Prime 固定实现同规则），
          git apply 后同样评分，预期 1；同时记录与容器内 `git diff HEAD <fix_commit>` 的一致性
  probe_unrelated  无关文件补丁，预期 0

reward 语义复刻 R2E 原始 runtime `_calculate_reward_r2e`：解析 pytest `short test summary info`
段的 PASSED/FAILED/ERROR，测试名 = nodeid 去掉文件路径后以 `.` 连接；
reward=1 当且仅当解析映射与预期映射键数相同且每个非空键状态相同。
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import difflib
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

RUNNER_VERSION = "r2e_probe/0.3"  # 0.2：parser 对齐 Prime；0.3：两侧对称去完整 ANSI（pillow expected 键含 ESC 序列）
_print_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def sh(cmd, timeout=None, input_bytes=None):
    return subprocess.run(cmd, capture_output=True, timeout=timeout, input=input_bytes)


def sha256_text(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


UNRELATED_PATCH = """diff --git a/RH2_PROBE_UNRELATED.md b/RH2_PROBE_UNRELATED.md
new file mode 100644
--- /dev/null
+++ b/RH2_PROBE_UNRELATED.md
@@ -0,0 +1,2 @@
+rh2 env probe: unrelated file added at repo root
+this change must not make the failing tests pass
"""


# ----------------------------------------------------------------------------
# gold 重建（与 Prime r2e_gym taskset.extract_gold_patch 同规则：非测试 .py 文件）
# ----------------------------------------------------------------------------


def is_test_path(p: str) -> bool:
    parts = p.split("/")
    base = parts[-1]
    if base.startswith("test_") or base.endswith("_test.py") or base == "conftest.py":
        return True
    return any(seg in ("test", "tests", "testing") for seg in parts[:-1])


def build_gold_patch(parsed_commit_content: str) -> tuple[str, dict]:
    pc = json.loads(parsed_commit_content)
    pieces, included, excluded = [], [], []
    for fd in pc["file_diffs"]:
        path = (fd.get("header") or {}).get("file", {}).get("path") or (fd.get("plus_file") or {}).get("path", "")
        path = path[2:] if path.startswith("b/") else path
        if fd.get("is_binary_file"):
            excluded.append((path, "binary"))
            continue
        if not path.endswith(".py"):
            excluded.append((path, "non_py"))
            continue
        if is_test_path(path):
            excluded.append((path, "test"))
            continue
        old = fd.get("old_file_content") or ""
        new = fd.get("new_file_content") or ""
        if old == new:
            excluded.append((path, "no_change"))
            continue
        old_l = old.splitlines(keepends=True)
        new_l = new.splitlines(keepends=True)
        if old_l and not old_l[-1].endswith("\n"):
            old_l[-1] += "\n"
        if new_l and not new_l[-1].endswith("\n"):
            new_l[-1] += "\n"
        diff = difflib.unified_diff(old_l, new_l, fromfile=f"a/{path}", tofile=f"b/{path}", n=3)
        body = "".join(diff)
        pieces.append(f"diff --git a/{path} b/{path}\n" + body)
        included.append(path)
    return "".join(pieces), {"included": included, "excluded": excluded, "old_commit": pc.get("old_commit_hash"), "new_commit": pc.get("new_commit_hash")}


# ----------------------------------------------------------------------------
# R2E 日志解析与 reward
# ----------------------------------------------------------------------------


def parse_pytest_summary(output: str) -> dict:
    """逐字复刻 Prime r2e_gym taskset.parse_log_pytest（与 R2E 原始 runtime 同规则）：
    取 short test summary info 之后的行；PASSED 键 = "::" 之后的全部（含空格）；FAILED/ERROR 再截 " - "。"""
    output = re.sub(r"\x1b\[[0-9;]*m|\r", "", output or "")
    if "short test summary info" not in output:
        return {}
    out = {}
    for line in output.split("short test summary info")[1].strip().split("\n"):
        if "PASSED" in line:
            out[".".join(line.split("::")[1:])] = "PASSED"
        elif "FAILED" in line:
            out[".".join(line.split("::")[1:]).split(" - ")[0]] = "FAILED"
        elif "ERROR" in line:
            parts = line.split("::")
            name = ".".join(parts[1:]) if len(parts) > 1 else line
            out[name.split(" - ")[0]] = "ERROR"
    return out


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _decolor(d: dict) -> dict:
    """Prime `_decolor` 只删 `[数字m`，会把 `\\x1b[1mtest\\x1b[0m` 变成 `\\x1btest\\x1b`（残留 ESC）。
    我们对两侧都先删完整 ANSI 序列，再套 Prime 规则，保证对称；pillow 的 expected 键自带 ANSI，是数据侧事实。"""
    out = {}
    for k, v in d.items():
        k2 = ANSI_RE.sub("", k)
        k2 = re.sub(r"\[\d+m", "", k2)
        out[k2] = v
    return out


def normalize_map(d: dict) -> dict:
    """键归一化（两侧相同）：去 ANSI，再 split(" - ")[0]。"""
    d = _decolor(d)
    return {k.split(" - ")[0]: d[k] for k in sorted(d)}


def has_ansi(d: dict) -> bool:
    return any("\x1b" in k for k in d)


def r2e_reward(parsed_raw: dict, expected_raw: dict) -> tuple[int, dict]:
    parsed = normalize_map(parsed_raw)
    expected = normalize_map(expected_raw)
    details = {
        "expected_keys_have_ansi": has_ansi(expected_raw),
        "parsed_keys_have_ansi": has_ansi(parsed_raw),
        "expected_n": len(expected),
        "parsed_n": len(parsed),
        "missing": [k for k in expected if k not in parsed][:8],
        "extra": [k for k in parsed if k not in expected][:8],
        "mismatch": [(k, expected[k], parsed[k]) for k in expected if k in parsed and parsed[k] != expected[k]][:8],
        "n_missing": sum(1 for k in expected if k not in parsed),
        "n_extra": sum(1 for k in parsed if k not in expected),
        "n_mismatch": sum(1 for k in expected if k in parsed and parsed[k] != expected[k]),
        "expected_statuses": {s: list(expected.values()).count(s) for s in set(expected.values())},
    }
    # 以下与 Prime calculate_reward 逐字同义：长度不等 → 0；parse 的每个非空键必须在 expected 且状态相同
    if len(parsed) != len(expected):
        return 0, details
    for k in parsed:
        if k and (k not in expected or parsed[k] != expected[k]):
            return 0, details
    return 1, details


# ----------------------------------------------------------------------------
# docker
# ----------------------------------------------------------------------------


class Container:
    def __init__(self, name, image, network_none, memory, cpus):
        self.name, self.image, self.network_none, self.memory, self.cpus = name, image, network_none, memory, cpus

    def start(self):
        cmd = ["docker", "run", "-d", "--name", self.name, "--memory", self.memory, "--memory-swap", self.memory, "--cpus", self.cpus, "--label", "rh2probe=1"]
        if self.network_none:
            cmd += ["--network", "none"]
        cmd += [self.image, "sleep", "infinity"]
        r = sh(cmd, timeout=120)
        if r.returncode != 0:
            raise RuntimeError(f"docker run failed: {r.stderr.decode()[-400:]}")

    def exec(self, script, timeout=600, user=None):
        cmd = ["docker", "exec"] + (["-u", user] if user else []) + [self.name, "bash", "-c", script]
        return sh(cmd, timeout=timeout)

    def cp_in(self, text, dest, mode="0644"):
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write(text)
            tmp = f.name
        try:
            r = sh(["docker", "cp", tmp, f"{self.name}:{dest}"], timeout=120)
            if r.returncode != 0:
                raise RuntimeError(f"docker cp failed: {r.stderr.decode()[-300:]}")
            self.exec(f"chmod {mode} {shlex.quote(dest)}", timeout=30)
        finally:
            os.unlink(tmp)

    def cp_out(self, src):
        with tempfile.TemporaryDirectory() as td:
            r = sh(["docker", "cp", f"{self.name}:{src}", td + "/f"], timeout=300)
            return Path(td + "/f").read_text(errors="replace") if r.returncode == 0 else None

    def rm(self):
        sh(["docker", "rm", "-f", self.name], timeout=120)


def image_repo_digest(image):
    r = sh(["docker", "image", "inspect", "--format", "{{json .RepoDigests}}", image], timeout=60)
    if r.returncode != 0:
        return None
    for d in json.loads(r.stdout.decode()):
        if "@" in d:
            return d.split("@", 1)[1]
    return None


# ----------------------------------------------------------------------------


def run_job(rows, cands, commit, gate, attempt, args):
    t0 = time.time()
    row = rows[commit]
    cand = cands.get(commit, {})
    image = row["docker_image"]
    expected = json.loads(row["expected_output_json"]) if row.get("expected_output_json") else {}
    network_none = gate != "facts"
    rec = {
        "schema": "rh2.env_probe.r2e.v1",
        "runner_version": RUNNER_VERSION,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "source": "R2E-Gym/R2E-Gym-Subset",
        "source_revision": open(Path(args.data) / "r2e_subset.revision").read().strip(),
        "commit_hash": commit,
        "repo": row["repo_name"],
        "image_ref": image,
        "image_digest_actual": image_repo_digest(image),
        "gate": gate,
        "attempt": attempt,
        "network": "none" if network_none else "default",
        "expected_n": len(expected),
        "result": None,
        "reward": None,
        "notes": [],
    }
    out_dir = Path(args.out) / "logs_r2e" / row["repo_name"] / commit[:12] / gate / f"a{attempt}"
    out_dir.mkdir(parents=True, exist_ok=True)
    patch, gold_meta = None, {}
    if gate == "gold":
        patch, gold_meta = build_gold_patch(row["parsed_commit_content"])
        rec["gold_meta"] = gold_meta
        if not patch.strip():
            rec["result"] = "fixture_invalid:empty_gold"
            rec["elapsed_s"] = round(time.time() - t0, 1)
            return rec
        (out_dir / "gold.diff").write_text(patch)
    elif gate == "probe_unrelated":
        patch = UNRELATED_PATCH
    rec["fixture_digest"] = sha256_text(patch or "")
    key = hashlib.sha256(f"{commit}|{gate}|{attempt}|{rec['fixture_digest']}|{rec['image_digest_actual']}".encode()).hexdigest()[:16]
    rec["key"] = key
    c = Container(f"rh2r2e_{key}", image, network_none, args.memory, args.cpus)
    try:
        c.start()
        facts_script = r"""
cd /testbed 2>/dev/null || { echo RH2_FACT no_testbed; exit 0; }
echo RH2_FACT uname=$(uname -m)
echo RH2_FACT head=$(git rev-parse HEAD 2>/dev/null)
echo RH2_FACT fix_reachable=$(git cat-file -t FIXCOMMIT 2>/dev/null || echo no)
echo RH2_FACT head_is_parent_of_fix=$( [ "$(git rev-parse FIXCOMMIT^ 2>/dev/null)" = "$(git rev-parse HEAD)" ] && echo yes || echo no )
echo RH2_FACT remotes=$(git remote 2>/dev/null | wc -l) refs=$(git for-each-ref 2>/dev/null | wc -l) tags=$(git tag | wc -l)
echo RH2_FACT commits_after_head=$(git rev-list --all --count --not HEAD 2>/dev/null)
echo RH2_FACT status_lines=$(git status --porcelain 2>/dev/null | wc -l)
echo RH2_FACT venv_python=$(.venv/bin/python -V 2>&1 | tr ' ' '_')
echo RH2_FACT r2e_tests_root=$(ls /r2e_tests 2>/dev/null | wc -l) r2e_tests_in_testbed=$(ls /testbed/r2e_tests 2>/dev/null | wc -l)
echo RH2_FACT run_tests_sh=$(test -f /testbed/run_tests.sh && echo yes || echo no)
echo RH2_FACT expected_file=$(ls /testbed/expected_test_output.json /expected_test_output.json 2>/dev/null | wc -l)
if command -v curl >/dev/null 2>&1; then curl -sI --max-time 6 https://pypi.org/simple/ -o /dev/null -w 'RH2_FACT egress_pypi=%{http_code}\n' || echo RH2_FACT egress_pypi=fail; else echo RH2_FACT egress_pypi=no_curl; fi
""".replace("FIXCOMMIT", commit)
        r = c.exec(facts_script, timeout=180)
        facts = {}
        for ln in r.stdout.decode(errors="replace").splitlines():
            if ln.startswith("RH2_FACT "):
                for kv in ln[9:].split():
                    if "=" in kv:
                        k2, v2 = kv.split("=", 1)
                        facts[k2] = v2
        rec["facts"] = facts
        rec["run_tests_sh"] = (c.cp_out("/testbed/run_tests.sh") or "")[:400]
        if gate == "facts":
            rec["result"] = "recorded"
            rec["elapsed_s"] = round(time.time() - t0, 1)
            return rec

        if patch is not None:
            c.cp_in(patch, "/tmp/patch.diff")
            ap = c.exec("cd /testbed && git apply --whitespace=fix -v /tmp/patch.diff && echo RH2_APPLY=ok", timeout=120)
            rec["patch_apply"] = "git_apply" if ap.returncode == 0 else "failed"
            if ap.returncode != 0:
                rec["patch_apply_err"] = ap.stderr.decode(errors="replace")[-600:]
                rec["result"] = "patch_apply_failed"
                rec["elapsed_s"] = round(time.time() - t0, 1)
                return rec
            if gate == "gold":
                # 与容器内 git diff HEAD..fix_commit（同一文件集合）的一致性
                files = " ".join(shlex.quote(p) for p in gold_meta["included"])
                gd = c.exec(f"cd /testbed && git stash -q && git diff HEAD {commit} -- {files} > /tmp/git_gold.diff; git stash pop -q; wc -l < /tmp/git_gold.diff", timeout=120)
                git_gold = c.cp_out("/tmp/git_gold.diff") or ""
                (out_dir / "git_gold.diff").write_text(git_gold)
                rec["gold_git_diff_lines"] = len(git_gold.splitlines())
                def norm(d):
                    return [ln for ln in d.splitlines() if ln.startswith(("+", "-")) and not ln.startswith(("+++", "---"))]
                rec["gold_matches_git_diff_changed_lines"] = norm(git_gold) == norm(patch)
        # 评分 setup（复刻 Prime/R2E：恢复隐藏测试目录，清 pycache）
        setup = "cd /testbed && rm -rf /testbed/r2e_tests && cp -r /r2e_tests /testbed/r2e_tests && find /testbed -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null; echo RH2_SETUP_OK"
        s = c.exec(setup, timeout=300)
        rec["setup_ok"] = "RH2_SETUP_OK" in s.stdout.decode(errors="replace")
        t_test = time.time()
        r = c.exec(f"cd /testbed && timeout -k 30 {args.timeout} bash run_tests.sh > /tmp/test_output.txt 2>&1; echo $? > /tmp/rc", timeout=args.timeout + 120)
        rec["t_test"] = round(time.time() - t_test, 2)
        rc = (c.cp_out("/tmp/rc") or "").strip()
        rec["test_rc"] = int(rc) if rc.isdigit() else rc[:20]
        rec["timed_out"] = rec["test_rc"] == 124
        content = c.cp_out("/tmp/test_output.txt") or ""
        (out_dir / "test_output.txt").write_text(content)
        rec["log_sha256"] = sha256_text(content)
        rec["log_bytes"] = len(content)
        rec["log_path"] = str(out_dir / "test_output.txt")
        parsed = parse_pytest_summary(content)
        (out_dir / "status_map.json").write_text(json.dumps(parsed, indent=0))
        reward, det = r2e_reward(parsed, expected)
        rec["reward"] = reward
        rec["reward_details"] = det
        rec["tests_collected"] = "collected" in content
        if rec["timed_out"]:
            rec["result"] = "timeout"
        elif not parsed and not rec["tests_collected"]:
            rec["result"] = "infra_failed:no_tests_ran"
        elif gate == "noop":
            rec["result"] = "passed" if reward == 0 and det["n_mismatch"] + det["n_missing"] >= 1 else ("suspicious" if reward == 1 else "failed")
        elif gate == "gold":
            rec["result"] = "passed" if reward == 1 else "failed"
        elif gate == "probe_unrelated":
            rec["result"] = "passed" if reward == 0 else "suspicious_pass"
    except subprocess.TimeoutExpired as e:
        rec["result"] = "infra_failed:docker_timeout"
        rec["notes"].append(str(e)[:300])
    except Exception as e:  # noqa: BLE001
        rec["result"] = f"infra_failed:{type(e).__name__}"
        rec["notes"].append(str(e)[:500])
    finally:
        c.rm()
    rec["elapsed_s"] = round(time.time() - t0, 1)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="/work/data")
    ap.add_argument("--out", default="/work/ledger")
    ap.add_argument("--ledger", default="r2e_ledger.jsonl")
    ap.add_argument("--commits", required=True, help="逗号分隔 commit_hash / repo 名 / all / core24")
    ap.add_argument("--gates", default="facts,noop,gold")
    ap.add_argument("--attempts", type=int, default=1)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--memory", default="8g")
    ap.add_argument("--cpus", default="3")
    ap.add_argument("--rerun", action="store_true")
    args = ap.parse_args()
    rows = {}
    for line in open(Path(args.data) / "r2e_candidates_full.jsonl"):
        r = json.loads(line)
        rows[r["commit_hash"]] = r
    cands = {}
    for line in open(Path(args.data) / "candidate_manifest.jsonl"):
        c = json.loads(line)
        if "R2E" in c["source"]:
            cands[c["candidate_key"].split("::")[1]] = c
    sel = args.commits
    if sel == "all":
        commits = list(rows)
    elif sel == "core24":
        commits = [k for k, c in cands.items() if c["group"] == "core24" and k in rows]
    else:
        commits = []
        for x in sel.split(","):
            x = x.strip()
            if x in rows:
                commits.append(x)
            else:
                commits += [k for k, r in rows.items() if r["repo_name"] == x]
    ledger = Path(args.out) / args.ledger
    ledger.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if ledger.exists() and not args.rerun:
        for line in open(ledger):
            try:
                r = json.loads(line)
                if r.get("result") and not str(r["result"]).startswith("infra_failed"):
                    done.add(r["key_plan"])
            except Exception:
                pass
    jobs = []
    for cm in commits:
        for gate in args.gates.split(","):
            for a in range(1, (1 if gate == "facts" else args.attempts) + 1):
                pk = f"{cm}|{gate}|{a}"
                if pk not in done:
                    jobs.append((cm, gate, a, pk))
    log(f"{len(jobs)} jobs, {args.workers} workers, ledger={ledger}")
    lock = threading.Lock()

    def work(j):
        cm, gate, a, pk = j
        log(f"START {rows[cm]['repo_name']} {cm[:12]} {gate} a{a}")
        rec = run_job(rows, cands, cm, gate, a, args)
        rec["key_plan"] = pk
        with lock:
            with open(ledger, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        d = rec.get("reward_details") or {}
        log(f"DONE  {rows[cm]['repo_name']} {cm[:12]} {gate} a{a} -> {rec.get('result')} reward={rec.get('reward')} parsed={d.get('parsed_n')}/{d.get('expected_n')} mism={d.get('n_mismatch')} miss={d.get('n_missing')} t={rec.get('elapsed_s')}s")
        return rec

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(work, jobs))


if __name__ == "__main__":
    sys.exit(main())
