#!/usr/bin/env python3
"""SWE-Gym 环境探针 runner（B 线，2026-09-09）。

用途：对 216 题 SWE-Gym Lite 存活集中的任务，在 fresh 容器里执行官方 fork
（SWE-Gym/SWE-Bench-Fork@242429c1）生成的 eval 脚本，分别检查：
  facts            镜像身份 / HEAD / 解释器 / git 历史与网络可见性
  empty            无修改基线：官方脚本真跑，F2P 应失败
  gold             参考修复：官方 RESOLVED_FULL 且严格判定通过
  probe_unrelated  无关文件补丁：应不通过
  probe_mutation   gold 删末 hunk：四态记录，不判题
变体（variant）：
  default            官方脚本原样、默认网络、root
  offline            官方脚本原样、--network none、root
  offline_noinstall  删除 install 行、--network none、root
  grader_user        root 做 setup/install，测试命令以 uid 54322 执行

每次运行写一行 ledger jsonl，并保留 eval.sh / patch.diff / test_output.txt / status_map.json。
它是官方 oracle（参考路径），不是 rh2 grader；rh2 集成对账另做。
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from swebench.harness.constants import (
    APPLY_PATCH_FAIL,
    APPLY_PATCH_PASS,
    FAIL_TO_PASS,
    MAP_REPO_VERSION_TO_SPECS,
    PASS_TO_PASS,
    RESET_FAILED,
    TESTS_ERROR,
    TESTS_TIMEOUT,
)
from swebench.harness.grading import get_eval_tests_report, get_resolution_status
from swebench.harness.log_parsers import MAP_REPO_TO_PARSER
from swebench.harness.test_spec import make_test_spec

FORK_COMMIT = "242429c188fcfd06aad13fce9a54d450470bf0ac"
RUNNER_VERSION = "swegym_probe/0.1"
GRADER_UID = 54322
GRADER_USER = "rh2grader"
OK_STATUS = {"PASSED", "XFAIL"}

_print_lock = threading.Lock()
_run_control = None


class ProbeStopped(RuntimeError):
    """实验整批截止或收到停止信号；不改变官方评分判定。"""


class RunControl:
    def __init__(self, wall_seconds: float):
        self.started = time.monotonic()
        self.deadline = self.started + wall_seconds
        # 总预算包含观测与回收；短替身探针也保留相同的收口比例。
        self.cleanup_reserve = min(60.0, wall_seconds * 0.2)
        self.work_deadline = self.deadline - self.cleanup_reserve
        self.stopped = threading.Event()
        self.reason = None

    def stop(self, reason: str) -> None:
        if not self.stopped.is_set():
            self.reason = reason
            self.stopped.set()

    def remaining(self, cleanup: bool = False) -> float:
        if not cleanup and time.monotonic() >= self.work_deadline:
            self.stop("wall_deadline")
        if not cleanup and self.stopped.is_set():
            raise ProbeStopped(self.reason)
        left = (self.deadline if cleanup else self.work_deadline) - time.monotonic()
        if left <= 0:
            raise ProbeStopped("wall_deadline")
        return left


def log(msg: str) -> None:
    with _print_lock:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def sh(cmd: list[str], timeout: float | None = None, input_bytes: bytes | None = None, *, cleanup: bool = False) -> subprocess.CompletedProcess:
    if _run_control is None:
        return subprocess.run(cmd, capture_output=True, timeout=timeout, input=input_bytes)
    allowed = min(timeout or float("inf"), _run_control.remaining(cleanup))
    command_deadline = time.monotonic() + allowed
    # 只管理当前 Docker CLI 子进程；容器内进程由 finally 的 docker rm -f 回收。
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE if input_bytes is not None else None) as proc:
        first = True
        try:
            while True:
                left = min(command_deadline - time.monotonic(), _run_control.remaining(cleanup))
                if left <= 0:
                    raise subprocess.TimeoutExpired(cmd, allowed)
                try:
                    stdout, stderr = proc.communicate(input=input_bytes if first else None, timeout=min(0.5, left))
                    return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
                except subprocess.TimeoutExpired:
                    first = False
        except BaseException:
            proc.kill()
            proc.communicate()
            raise


def sha256_text(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


# ----------------------------------------------------------------------------
# 数据
# ----------------------------------------------------------------------------


class Data:
    def __init__(self, data_dir: Path):
        self.raw = {}
        for line in open(data_dir / "swe_gym_lite_full_f70b1a29.jsonl"):
            r = json.loads(line)
            self.raw[r["instance_id"]] = r
        self.grading = {}
        for line in open(data_dir / "grading_bundles_v2_v0.jsonl"):
            b = json.loads(line)
            self.grading[b["instance_id"]] = b
        self.validation = {}
        for line in open(data_dir / "validation_bundles_v0.jsonl"):
            v = json.loads(line)
            self.validation[v["instance_id"]] = v
        self.public = {}
        for line in open(data_dir / "public_bundles_v0.jsonl"):
            p = json.loads(line)
            self.public[p["instance_id"]] = p
        self.candidates = {}
        for line in open(data_dir / "candidate_manifest.jsonl"):
            c = json.loads(line)
            if "SWE-Gym" in c["source"]:
                self.candidates[c["instance_id"]] = c

    def image_ref(self, iid: str) -> str:
        if iid in self.candidates:
            return self.candidates[iid]["image_ref"]
        return self.public[iid]["image"]

    def image_digest(self, iid: str) -> str | None:
        if iid in self.candidates:
            return self.candidates[iid].get("image_digest_from_existing_inventory")
        return self.public[iid].get("image_manifest_digest")


def as_list(v):
    if isinstance(v, str):
        return json.loads(v)
    return list(v)


# ----------------------------------------------------------------------------
# 官方 eval 脚本 + 阶段标记
# ----------------------------------------------------------------------------


def build_scripts(raw_row: dict, variant: str) -> dict:
    """返回 {root_script, test_script(None 除 grader_user), meta}。

    default/offline：单一脚本 = 官方 eval 脚本原样，仅插入 RH2_PHASE 回显行。
    offline_noinstall：删除 install 元素。
    grader_user：root 脚本 = 官方脚本去掉测试命令与其后的 reset；测试脚本 = 激活 + 测试命令；
                 reset 由 root 脚本之后再执行（tail_script）。
    """
    spec = make_test_spec(dict(raw_row))
    repo_l = raw_row["repo"].lower()
    specs = MAP_REPO_VERSION_TO_SPECS[repo_l][raw_row["version"]]
    elems = list(spec.eval_script_list)
    install = specs.get("install")
    test_cmd_prefix = specs["test_cmd"]
    install_idx = [i for i, e in enumerate(elems) if install is not None and e == install]
    test_idx = [i for i, e in enumerate(elems) if e.startswith(test_cmd_prefix)]
    if len(test_idx) != 1:
        raise RuntimeError(f"test line not uniquely found: {test_idx}")
    ti = test_idx[0]
    # 官方脚本原文（用于核对我们的重建没有改语义）
    official_text = spec.eval_script
    rebuilt = "#!/bin/bash\nset -xo pipefail\n" + "\n".join(elems) + "\n"
    official_matches = rebuilt == official_text

    def mark(name: str, start: bool) -> str:
        if start:
            return f'echo "RH2_PHASE_START {name} $(date +%s.%N)"'
        return f'RH2_RC=$?; echo "RH2_PHASE_END {name} $(date +%s.%N) rc=$RH2_RC"'

    out = []
    setup_started = False
    for i, e in enumerate(elems):
        if install_idx and i == install_idx[0]:
            if variant == "offline_noinstall":
                out.append('echo "RH2_PHASE_SKIP install"')
                continue
            out.append(mark("install", True))
            out.append(e)
            out.append(mark("install", False))
            continue
        if e.startswith("git checkout ") and i < ti and not setup_started:
            setup_started = True
            out.append(mark("setup", True))
            out.append(e)
            continue
        if e.startswith("git apply -v -") and i < ti:
            out.append(e)
            out.append(mark("setup", False))
            continue
        if i == ti:
            out.append(mark("test", True))
            out.append(e)
            out.append(mark("test", False))
            continue
        out.append(e)
    header = "#!/bin/bash\nset -xo pipefail\n"
    meta = {
        "official_script_sha256": sha256_text(official_text),
        "rebuild_matches_official": official_matches,
        "install_line_present": bool(install_idx),
        "install_line": install if install_idx else None,
        "test_line": elems[ti],
        "test_cmd_prefix": test_cmd_prefix,
        "fork_arch": spec.arch,
    }
    if variant != "grader_user":
        return {"root_script": header + "\n".join(out) + "\n", "test_script": None, "tail_script": None, "meta": meta}
    # grader_user：拆分
    # 找到 out 中测试命令位置（mark test start 之前）
    t_start = out.index(mark("test", True))
    t_end = out.index(mark("test", False))
    root_part = out[:t_start]
    test_part = out[t_start : t_end + 1]
    tail_part = out[t_end + 1 :]
    activate = [e for e in elems[:ti] if e.startswith("source ") or e.startswith("conda activate") or e.startswith("cd /testbed")]
    # 去重保持顺序
    seen = set()
    act = []
    for a in activate:
        if a not in seen:
            act.append(a)
            seen.add(a)
    test_script = header + "export HOME=/tmp/rh2grader_home\nmkdir -p $HOME\nid -un > $HOME/whoami\n" + "\n".join(act + test_part) + "\n"
    tail_script = header + "\n".join(act + tail_part) + "\n"
    return {"root_script": header + "\n".join(root_part) + "\n", "test_script": test_script, "tail_script": tail_script, "meta": meta}


# ----------------------------------------------------------------------------
# fixture 补丁
# ----------------------------------------------------------------------------

UNRELATED_PATCH = """diff --git a/RH2_PROBE_UNRELATED.md b/RH2_PROBE_UNRELATED.md
new file mode 100644
--- /dev/null
+++ b/RH2_PROBE_UNRELATED.md
@@ -0,0 +1,2 @@
+rh2 env probe: unrelated file added at repo root
+this change must not make the failing tests pass
"""


def split_files(patch: str) -> list[list[str]]:
    lines = patch.splitlines(keepends=True)
    files, cur = [], []
    for ln in lines:
        if ln.startswith("diff --git ") and cur:
            files.append(cur)
            cur = []
        cur.append(ln)
    if cur:
        files.append(cur)
    return files


def split_hunks(file_lines: list[str]) -> tuple[list[str], list[list[str]]]:
    header, hunks, cur = [], [], None
    for ln in file_lines:
        if ln.startswith("@@"):
            if cur is not None:
                hunks.append(cur)
            cur = [ln]
        elif cur is None:
            header.append(ln)
        else:
            cur.append(ln)
    if cur is not None:
        hunks.append(cur)
    return header, hunks


def mutate_gold(gold: str) -> tuple[str | None, str]:
    """删除最后一个 hunk；若全补丁只有一个 hunk，则删该 hunk 最后一条 '+' 行并修正计数。"""
    files = split_files(gold)
    parsed = [split_hunks(f) for f in files]
    total_hunks = sum(len(h) for _, h in parsed)
    if total_hunks == 0:
        return None, "fixture_invalid:no_hunks"
    if total_hunks >= 2:
        # 删最后一个文件的最后一个 hunk；若该文件只剩 0 个 hunk 则整段删除
        for fi in range(len(parsed) - 1, -1, -1):
            header, hunks = parsed[fi]
            if hunks:
                hunks = hunks[:-1]
                parsed[fi] = (header, hunks)
                break
        out = []
        for header, hunks in parsed:
            if not hunks:
                continue
            out.extend(header)
            for h in hunks:
                out.extend(h)
        return "".join(out), "drop_last_hunk"
    # 单 hunk：删最后一条 '+' 行
    header, hunks = parsed[0]
    h = hunks[0]
    plus_idx = [i for i, ln in enumerate(h) if ln.startswith("+") and not ln.startswith("+++")]
    if not plus_idx:
        return None, "fixture_invalid:single_hunk_no_added_line"
    del h[plus_idx[-1]]
    m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)", h[0])
    if not m:
        return None, "fixture_invalid:bad_hunk_header"
    old_s, old_c, new_s, new_c, rest = m.groups()
    new_c = int(new_c or 1) - 1
    h[0] = f"@@ -{old_s},{old_c or 1} +{new_s},{new_c} @@{rest}\n"
    return "".join(header) + "".join(h), "drop_last_added_line"


# ----------------------------------------------------------------------------
# 判定
# ----------------------------------------------------------------------------


def parse_official(content: str, repo_lower: str) -> tuple[dict, bool, str]:
    """复刻 fork grading.get_logs_eval 的判断，但不依赖日志路径命名。"""
    markers = [APPLY_PATCH_FAIL, RESET_FAILED, TESTS_ERROR, TESTS_TIMEOUT, "Failed to reset task environment"]
    hit = [m for m in markers if m in content]
    if hit or "applied patch" not in content.lower():
        return {}, False, ("marker:" + "|".join(hit)) if hit else "no_applied_patch_marker"
    content2 = content.split(f"{APPLY_PATCH_PASS} (pred)")[-1]
    parser = MAP_REPO_TO_PARSER[repo_lower]
    return parser(content2), True, "ok"


def strict_verdict(sm: dict, f2p: list[str], p2p: list[str]) -> dict:
    f2p_missing = [c for c in f2p if c not in sm]
    p2p_missing = [c for c in p2p if c not in sm]
    f2p_bad = [c for c in f2p if c in sm and sm[c] not in OK_STATUS]
    p2p_bad = [c for c in p2p if c in sm and sm[c] not in OK_STATUS]
    ref = f2p + p2p
    skipped = [c for c in ref if sm.get(c) == "SKIPPED"]
    xfail = [c for c in ref if sm.get(c) == "XFAIL"]
    full = bool(f2p) and not f2p_missing and not f2p_bad and not p2p_missing and not p2p_bad
    return {
        "strict_full": full,
        "f2p_total": len(f2p),
        "p2p_total": len(p2p),
        "p2p_empty": len(p2p) == 0,
        "f2p_missing": len(f2p_missing),
        "p2p_missing": len(p2p_missing),
        "f2p_not_ok": len(f2p_bad),
        "p2p_not_ok": len(p2p_bad),
        "ref_skipped": len(skipped),
        "ref_xfail": len(xfail),
        "f2p_status": {c: sm.get(c, "MISSING") for c in f2p},
        "p2p_not_ok_examples": (p2p_bad + p2p_missing)[:5],
    }


def parse_phases(content: str) -> dict:
    out = {}
    starts, ends, rcs = {}, {}, {}
    for ln in content.splitlines():
        if ln.startswith("RH2_PHASE_START "):
            _, name, ts = ln.split()[:3]
            starts[name] = float(ts)
        elif ln.startswith("RH2_PHASE_END "):
            parts = ln.split()
            name, ts = parts[1], float(parts[2])
            ends[name] = ts
            for p in parts[3:]:
                if p.startswith("rc="):
                    rcs[name] = int(p[3:])
        elif ln.startswith("RH2_PHASE_SKIP "):
            out[f"t_{ln.split()[1]}"] = None
            out[f"rc_{ln.split()[1]}"] = "skipped"
    for name in ("setup", "install", "test"):
        if name in starts and name in ends:
            out[f"t_{name}"] = round(ends[name] - starts[name], 2)
        elif name in starts:
            out[f"t_{name}"] = "unfinished"
        if name in rcs:
            out[f"rc_{name}"] = rcs[name]
    return out


# ----------------------------------------------------------------------------
# docker
# ----------------------------------------------------------------------------


_pull_locks: dict[str, threading.Lock] = {}
_pull_locks_guard = threading.Lock()


def ensure_image(image: str, timeout: float = 3600) -> dict:
    """镜像不在本地则显式 docker pull（同一镜像的并发 job 串行等待），避免 docker run 按需拉取超时。"""
    with _pull_locks_guard:
        lock = _pull_locks.setdefault(image, threading.Lock())
    with lock:
        r = sh(["docker", "image", "inspect", "--format", "{{.Id}}", image], timeout=60)
        if r.returncode == 0:
            return {"pulled": False, "t_pull": 0.0}
        t0 = time.time()
        p = sh(["docker", "pull", image], timeout=timeout)
        if p.returncode != 0:
            raise RuntimeError(f"docker pull failed: {p.stderr.decode()[-300:]}")
        return {"pulled": True, "t_pull": round(time.time() - t0, 1)}


class Container:
    def __init__(self, name: str, image: str, network_none: bool, memory: str, cpus: str, shm_size: str | None = None):
        self.name = name
        self.image = image
        self.network_none = network_none
        self.memory = memory
        self.cpus = cpus
        self.shm_size = shm_size
        self.container_id: str | None = None

    def start(self) -> None:
        cmd = ["docker", "run", "-d", "--name", self.name, "--memory", self.memory, "--memory-swap", self.memory, "--cpus", self.cpus, "--label", "rh2probe=1"]
        if self.shm_size:
            cmd += ["--shm-size", self.shm_size]
        if self.network_none:
            cmd += ["--network", "none"]
        cmd += [self.image, "sleep", "infinity"]
        r = sh(cmd, timeout=600)
        if r.returncode != 0:
            raise RuntimeError(f"docker run failed: {r.stderr.decode()[-400:]}")
        self.container_id = r.stdout.decode().strip()[:64] or None

    def resource_facts(self) -> dict:
        """容器删除前读取 cgroup v2 memory.peak / memory.events（宿主侧），并记 OOMKilled 与实际 shm 大小。
        口径：peak 覆盖容器整个生命周期（含 install 与测试）；不可读时标 missing，不填零。"""
        out = {"mem_peak_bytes": None, "mem_peak_source": "missing", "oom_kill_events": None, "oom_killed_flag": None, "shm_size_bytes": None}
        if not self.container_id:
            return out
        cid = self.container_id
        r = sh(["docker", "inspect", "--format", "{{.State.OOMKilled}} {{.HostConfig.ShmSize}} {{.HostConfig.Memory}}", cid], timeout=10, cleanup=True)
        if r.returncode == 0:
            parts = r.stdout.decode().split()
            if len(parts) >= 3:
                out["oom_killed_flag"] = parts[0] == "true"
                out["shm_size_bytes"] = int(parts[1]) if parts[1].isdigit() else None
                out["memory_limit_bytes"] = int(parts[2]) if parts[2].isdigit() else None
        for base in (f"/sys/fs/cgroup/system.slice/docker-{cid}.scope", f"/sys/fs/cgroup/docker/{cid}"):
            try:
                peak = Path(base, "memory.peak").read_text().strip()
                out["mem_peak_bytes"] = int(peak)
                out["mem_peak_source"] = "cgroup_v2_memory.peak"
                try:
                    ev = Path(base, "memory.events").read_text()
                    for ln in ev.splitlines():
                        if ln.startswith("oom_kill "):
                            out["oom_kill_events"] = int(ln.split()[1])
                except Exception:
                    pass
                break
            except Exception:
                continue
        return out

    def exec(self, script: str, user: str | None = None, timeout: float = 600, workdir: str | None = None) -> subprocess.CompletedProcess:
        cmd = ["docker", "exec"]
        if user:
            cmd += ["-u", user]
        if workdir:
            cmd += ["-w", workdir]
        cmd += [self.name, "bash", "-c", script]
        return sh(cmd, timeout=timeout)

    def cp_in(self, text: str, dest: str, mode: str = "0644") -> None:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".tmp") as f:
            f.write(text)
            tmp = f.name
        try:
            r = sh(["docker", "cp", tmp, f"{self.name}:{dest}"], timeout=120)
            if r.returncode != 0:
                raise RuntimeError(f"docker cp failed: {r.stderr.decode()[-300:]}")
            self.exec(f"chmod {mode} {shlex.quote(dest)}", timeout=30)
        finally:
            os.unlink(tmp)

    def cp_out(self, src: str, *, cleanup: bool = False) -> str | None:
        with tempfile.TemporaryDirectory() as td:
            r = sh(["docker", "cp", f"{self.name}:{src}", td + "/f"], timeout=5 if cleanup else 300, cleanup=cleanup)
            if r.returncode != 0:
                return None
            return Path(td + "/f").read_text(errors="replace")

    def rm(self) -> None:
        r = sh(["docker", "rm", "-f", self.name], timeout=30 if _run_control else 120, cleanup=True)
        if r.returncode != 0 and b"No such container" not in r.stderr:
            raise RuntimeError(f"docker rm failed: {r.stderr.decode(errors='replace')[-300:]}")


def image_repo_digest(image: str) -> str | None:
    r = sh(["docker", "image", "inspect", "--format", "{{json .RepoDigests}}", image], timeout=60)
    if r.returncode != 0:
        return None
    try:
        ds = json.loads(r.stdout.decode())
        for d in ds:
            if "@" in d:
                return d.split("@", 1)[1]
    except Exception:
        return None
    return None


def image_arch(image: str) -> str | None:
    r = sh(["docker", "image", "inspect", "--format", "{{.Architecture}}/{{.Os}}", image], timeout=60)
    return r.stdout.decode().strip() if r.returncode == 0 else None


# ----------------------------------------------------------------------------
# 一次运行
# ----------------------------------------------------------------------------


def job_key(iid: str, gate: str, variant: str, attempt: int, fixture_digest: str, image_digest: str | None) -> str:
    s = f"{iid}|{gate}|{variant}|{attempt}|{fixture_digest}|{image_digest}"
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def run_job(data: Data, iid: str, gate: str, variant: str, attempt: int, args) -> dict:
    t0 = time.time()
    raw = data.raw[iid]
    g = data.grading[iid]
    repo_lower = g["repo_key_lower"]
    f2p = as_list(g["fail_to_pass"])
    p2p = as_list(g["pass_to_pass"])
    image = data.image_ref(iid)
    expected_digest = data.image_digest(iid)
    actual_digest = image_repo_digest(image)
    network_none = variant in ("offline", "offline_noinstall")
    exec_user = GRADER_USER if variant == "grader_user" else "root"

    # fixture
    fixture_note = ""
    if gate in ("facts", "empty"):
        patch = None
    elif gate == "gold":
        patch = data.validation[iid]["golden_patch"]
    elif gate == "probe_unrelated":
        patch = UNRELATED_PATCH
    elif gate == "probe_mutation":
        patch, fixture_note = mutate_gold(data.validation[iid]["golden_patch"])
    elif gate in ("candidate", "candidate_projected"):
        # 外部候选补丁（例如 Claude Code + API 模型的求解产物），路径 <candidate_dir>/<iid>.diff
        # candidate_projected：去掉候选中触及官方 test_patch 路径的文件段（模拟 rh2 可信投影：官方测试路径的候选改动不参与评分）
        cpath = Path(args.candidate_dir) / f"{iid}.diff"
        if not cpath.exists():
            patch, fixture_note = None, f"fixture_invalid:missing {cpath}"
        else:
            patch = cpath.read_text()
            fixture_note = f"candidate_from:{cpath}"
            if not patch.strip():
                patch, fixture_note = None, "fixture_invalid:empty_candidate"
            elif gate == "candidate_projected":
                official_paths = set()
                for ln in g["test_patch"].splitlines():
                    if ln.startswith("diff --git "):
                        official_paths.add(ln.split(" b/", 1)[1])
                kept, dropped = [], []
                for sec in split_files(patch):
                    head = sec[0] if sec else ""
                    p = head.split(" b/", 1)[1].strip() if " b/" in head else ""
                    (dropped if p in official_paths else kept).append(p if p in official_paths else sec)
                patch = "".join("".join(s) for s in kept)
                fixture_note += f";projected_dropped={dropped}"
                if not patch.strip():
                    patch, fixture_note = None, "fixture_invalid:empty_after_projection"
    else:
        raise ValueError(gate)
    fixture_digest = sha256_text(patch or "")
    key = job_key(iid, gate, variant, attempt, fixture_digest, actual_digest)
    rec = {
        "schema": "rh2.env_probe.swegym.v1",
        "runner_version": RUNNER_VERSION,
        "fork_commit": FORK_COMMIT,
        "key": key,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "source": "SWE-Gym/SWE-Gym-Lite",
        "source_revision": "f70b1a29ab120eb0a0ee7a1deb029825e735b2b0",
        "instance_id": iid,
        "repo": g["repo"],
        "version": g["version"],
        "base_commit": g["base_commit"],
        "image_ref": image,
        "image_digest_expected": expected_digest,
        "image_digest_actual": actual_digest,
        "image_digest_match": (expected_digest == actual_digest) if (expected_digest and actual_digest) else None,
        "image_arch": image_arch(image),
        "gate": gate,
        "variant": variant,
        "attempt": attempt,
        "network": "none" if network_none else "default",
        "exec_user_test": exec_user,
        "fixture_digest": fixture_digest,
        "fixture_note": fixture_note,
        "f2p_total": len(f2p),
        "p2p_total": len(p2p),
        "result": None,
        "official_verdict": None,
        "strict": None,
        "notes": [],
    }
    if gate in ("probe_mutation", "candidate", "candidate_projected") and patch is None:
        rec["result"] = "fixture_invalid"
        rec["notes"].append(fixture_note)
        rec["elapsed_s"] = round(time.time() - t0, 1)
        return rec

    # 输出按 run_tag 隔离：不同条件（网络 / shm / 内存）不复用昨夜的 a<attempt> 目录与容器名
    logs_root = Path(args.out) / "logs" if args.run_tag == "default" else Path(args.out) / "logs" / args.run_tag
    out_dir = logs_root / iid / gate / variant / f"a{attempt}"
    out_dir.mkdir(parents=True, exist_ok=True)
    rec["run_tag"] = args.run_tag
    rec["conditions"] = {"memory": args.memory, "cpus": args.cpus, "shm_size": args.shm_size, "network": rec["network"], "exec_user_test": exec_user, "timeout_s": args.timeout}
    scripts = build_scripts(raw, variant)
    rec.update({k: v for k, v in scripts["meta"].items()})
    (out_dir / "eval.sh").write_text(scripts["root_script"])
    if scripts["test_script"]:
        (out_dir / "eval_test.sh").write_text(scripts["test_script"])
        (out_dir / "eval_tail.sh").write_text(scripts["tail_script"])
    if patch is not None:
        (out_dir / "patch.diff").write_text(patch)

    cname = f"rh2probe_{key}" if args.run_tag == "default" else f"rh2probe_{re.sub(r'[^A-Za-z0-9_.-]', '_', args.run_tag)[:24]}_{key}"
    c = Container(cname, image, network_none, args.memory, args.cpus, shm_size=args.shm_size)
    rec["container_name"] = cname
    content = ""
    try:
        pull = ensure_image(image)
        rec["image_pulled_now"] = pull["pulled"]
        rec["t_pull"] = pull["t_pull"]
        # 同题并发 job 可能由另一个 worker 拉好镜像；锁释放后两边都重读身份。
        actual_digest = image_repo_digest(image)
        rec["image_digest_actual"] = actual_digest
        rec["image_digest_match"] = (expected_digest == actual_digest) if (expected_digest and actual_digest) else None
        rec["image_arch"] = image_arch(image)
        t_start = time.time()
        c.start()
        rec["t_container_start"] = round(time.time() - t_start, 2)
        # facts（每个 job 都记，便于对账；facts gate 只做这一步）
        facts_script = r"""
cd /testbed 2>/dev/null || { echo RH2_FACT no_testbed; exit 0; }
echo RH2_FACT head=$(git rev-parse HEAD 2>/dev/null)
echo RH2_FACT status_lines=$(git status --porcelain 2>/dev/null | wc -l)
echo RH2_FACT refs=$(git for-each-ref 2>/dev/null | wc -l)
echo RH2_FACT tags=$(git tag 2>/dev/null | wc -l)
echo RH2_FACT remotes=$(git remote 2>/dev/null | wc -l)
echo RH2_FACT reflog_lines=$(git reflog 2>/dev/null | wc -l)
echo RH2_FACT all_commits=$(git rev-list --all --count 2>/dev/null)
echo RH2_FACT head_commits=$(git rev-list HEAD --count 2>/dev/null)
echo RH2_FACT unreachable=$(git fsck --unreachable --no-reflogs --connectivity-only 2>/dev/null | grep -c '^unreachable ')
echo RH2_FACT python=$(/opt/miniconda3/envs/testbed/bin/python -V 2>&1 | tr ' ' '_')
echo RH2_FACT uname=$(uname -m)
echo RH2_FACT conftest_root=$(ls conftest.py 2>/dev/null | wc -l) pytest_ini=$(ls pytest.ini 2>/dev/null | wc -l) setup_cfg=$(ls setup.cfg 2>/dev/null | wc -l) pyproject=$(ls pyproject.toml 2>/dev/null | wc -l) tox_ini=$(ls tox.ini 2>/dev/null | wc -l)
echo RH2_FACT users=$(getent passwd | wc -l) agent_user=$(id -u agent 2>/dev/null || echo none)
echo RH2_FACT git_version=$(git --version | tr ' ' '_')
MOD=$(python3 - <<'PYMOD'
import json
m={"python/mypy":"mypy","pandas-dev/pandas":"pandas","dask/dask":"dask","getmoto/moto":"moto","iterative/dvc":"dvc","project-monai/monai":"monai","modin-project/modin":"modin","pydantic/pydantic":"pydantic","conan-io/conan":"conans"}
print(m.get("REPO_LOWER",""))
PYMOD
)
if [ -n "$MOD" ]; then
  LOC=$(cd /tmp && /opt/miniconda3/envs/testbed/bin/python -c "import $MOD,os; print(os.path.realpath($MOD.__file__))" 2>/dev/null || echo import_failed)
  echo RH2_FACT import_module=$MOD import_file=$LOC import_from_testbed=$( case "$LOC" in /testbed/*) echo yes;; *) echo no;; esac )
fi
if command -v curl >/dev/null 2>&1; then curl -sI --max-time 6 https://pypi.org/simple/ -o /dev/null -w 'RH2_FACT egress_pypi=%{http_code}\n' || echo RH2_FACT egress_pypi=fail; else echo RH2_FACT egress_pypi=no_curl; fi
"""
        r = c.exec(facts_script.replace("REPO_LOWER", repo_lower), timeout=180)
        facts = {}
        for ln in r.stdout.decode(errors="replace").splitlines():
            if ln.startswith("RH2_FACT "):
                for kv in ln[9:].split():
                    if "=" in kv:
                        k2, v2 = kv.split("=", 1)
                        facts[k2] = v2
        rec["facts"] = facts
        rec["head_equals_base"] = (facts.get("head") == g["base_commit"]) if facts.get("head") else None
        if gate == "facts":
            # 检查 base_commit 之后是否还有可达的未来提交（含 gold 修复）
            fut = c.exec(f"cd /testbed && git rev-list --all --count --not {g['base_commit']} 2>/dev/null || echo err", timeout=60)
            rec["facts"]["commits_not_ancestor_of_base"] = fut.stdout.decode().strip()[:40]
            rec["result"] = "recorded"
            rec["elapsed_s"] = round(time.time() - t0, 1)
            return rec

        # 候选补丁（官方 run_instance 的应用方式：git apply --allow-empty，失败退 patch --fuzz=5）
        if patch is not None:
            c.cp_in(patch, "/tmp/patch.diff")
            chk = c.exec("cd /testbed && git --version && git apply --check -v /tmp/patch.diff && echo RH2_CHECK=ok", timeout=120)
            rec["git_version"] = (chk.stdout.decode(errors="replace").splitlines() or [""])[0][:40]
            rec["git_apply_check_ok"] = "RH2_CHECK=ok" in chk.stdout.decode(errors="replace")
            if not rec["git_apply_check_ok"]:
                rec["git_apply_check_err"] = chk.stderr.decode(errors="replace")[-400:]
            ap = c.exec("cd /testbed && git apply --allow-empty -v /tmp/patch.diff && echo RH2_APPLY=git_apply", timeout=120)
            if ap.returncode != 0:
                rec["git_apply_allow_empty_err"] = ap.stderr.decode(errors="replace")[-300:]
                ap2 = c.exec("cd /testbed && patch --batch --fuzz=5 -p1 -i /tmp/patch.diff && echo RH2_APPLY=patch_fuzz5", timeout=120)
                if ap2.returncode != 0:
                    rec["patch_apply"] = "failed"
                    rec["patch_apply_err"] = (ap.stderr.decode(errors="replace") + ap2.stdout.decode(errors="replace"))[-600:]
                    rec["result"] = "fixture_invalid" if gate == "probe_mutation" else "patch_apply_failed"
                    rec["elapsed_s"] = round(time.time() - t0, 1)
                    return rec
                rec["patch_apply"] = "patch_fuzz5"
            else:
                rec["patch_apply"] = "git_apply"
        else:
            rec["patch_apply"] = "none"

        # 评分脚本
        c.cp_in(scripts["root_script"], "/eval.sh", "0755")
        if variant == "grader_user":
            c.exec(f"useradd -u {GRADER_UID} -M -s /bin/bash {GRADER_USER} 2>/dev/null; chown -R {GRADER_UID}:{GRADER_UID} /testbed; mkdir -p /tmp/rh2grader_home; chown {GRADER_UID}:{GRADER_UID} /tmp/rh2grader_home", timeout=600)
            c.cp_in(scripts["test_script"], "/eval_test.sh", "0755")
            c.cp_in(scripts["tail_script"], "/eval_tail.sh", "0755")
        t_eval = time.time()
        r = c.exec(f"timeout -k 30 {args.timeout} /bin/bash /eval.sh > /tmp/test_output.txt 2>&1; echo $? > /tmp/eval_rc", timeout=args.timeout + 120)
        if variant == "grader_user":
            # root 写的日志文件对 54322 不可写：先放开权限，测试阶段的 rc 写到 grader 自己的 home
            c.exec("chmod 666 /tmp/test_output.txt", timeout=30)
            c.exec(f"timeout -k 30 {args.timeout} /bin/bash /eval_test.sh >> /tmp/test_output.txt 2>&1; echo $? > /tmp/rh2grader_home/eval_test_rc", user=f"{GRADER_UID}:{GRADER_UID}", timeout=args.timeout + 120)
            c.exec("/bin/bash /eval_tail.sh >> /tmp/test_output.txt 2>&1", timeout=600)
        rec["t_eval_total"] = round(time.time() - t_eval, 2)
        rc_txt = c.cp_out("/tmp/eval_rc") or ""
        rec["eval_rc"] = int(rc_txt.strip()) if rc_txt.strip().isdigit() else rc_txt.strip()[:20]
        if variant == "grader_user":
            rc2 = c.cp_out("/tmp/rh2grader_home/eval_test_rc") or ""
            rec["eval_test_rc"] = int(rc2.strip()) if rc2.strip().isdigit() else rc2.strip()[:20]
            who = c.exec("cat /tmp/rh2grader_home/whoami 2>/dev/null", timeout=30)
            rec["test_phase_user"] = who.stdout.decode(errors="replace").strip()[:40]
        content = c.cp_out("/tmp/test_output.txt") or ""
        (out_dir / "test_output.txt").write_text(content)
        rec["log_sha256"] = sha256_text(content)
        rec["log_bytes"] = len(content)
        rec["log_path"] = str(out_dir / "test_output.txt")
        rec["timed_out"] = rec["eval_rc"] == 124
        rec.update(parse_phases(content))
        rec["test_patch_applied"] = "applied patch" in content.lower()
        # 共享内存 / 资源类故障签名（只计数，不判定）
        rec["log_signatures"] = {
            "bus_error": content.count("Bus error") + content.count("SIGBUS"),
            "no_space_left": content.count("No space left on device"),
            "memory_error": content.count("MemoryError") + content.count("Cannot allocate memory"),
            "killed": content.count("Killed"),
        }
        sm, found, why = parse_official(content, repo_lower)
        rec["official_parse"] = why
        rec["parsed_cases"] = len(sm)
        (out_dir / "status_map.json").write_text(json.dumps(sm, indent=0))
        if found:
            report = get_eval_tests_report(sm, {FAIL_TO_PASS: f2p, PASS_TO_PASS: p2p})
            rec["official_verdict"] = get_resolution_status(report)
            rec["official_f2p_success"] = len(report[FAIL_TO_PASS]["success"])
            rec["official_f2p_failure"] = len(report[FAIL_TO_PASS]["failure"])
            rec["official_p2p_success"] = len(report[PASS_TO_PASS]["success"])
            rec["official_p2p_failure"] = len(report[PASS_TO_PASS]["failure"])
        else:
            rec["official_verdict"] = "UNPARSED"
        rec["strict"] = strict_verdict(sm, f2p, p2p)
        counts = {}
        for v in sm.values():
            counts[v] = counts.get(v, 0) + 1
        rec["status_counts"] = counts

        # 门的结论
        tests_ran = rec.get("rc_test") is not None and rec.get("rc_test") != "skipped"
        if rec["timed_out"]:
            rec["result"] = "timeout"
        elif not rec["test_patch_applied"]:
            rec["result"] = "infra_failed:test_patch_not_applied"
        elif not tests_ran:
            rec["result"] = "infra_failed:test_phase_missing"
        elif gate == "empty":
            f2p_failing = sum(1 for cse in f2p if sm.get(cse) not in OK_STATUS)
            rec["empty_f2p_failing_or_missing"] = f2p_failing
            rec["result"] = "passed" if (rec["parsed_cases"] > 0 and f2p_failing >= 1 and rec["official_verdict"] != "RESOLVED_FULL") else ("suspicious" if rec["parsed_cases"] == 0 else "failed")
        elif gate == "gold":
            rec["result"] = "passed" if (rec["official_verdict"] == "RESOLVED_FULL" and rec["strict"]["strict_full"]) else ("lenient_only" if rec["official_verdict"] == "RESOLVED_FULL" else "failed")
        elif gate == "probe_unrelated":
            rec["result"] = "passed" if rec["official_verdict"] != "RESOLVED_FULL" else "suspicious_pass"
        elif gate == "probe_mutation":
            rec["result"] = "rejected" if rec["official_verdict"] != "RESOLVED_FULL" else "suspicious_pass"
        elif gate in ("candidate", "candidate_projected"):
            rec["result"] = "resolved" if (rec["official_verdict"] == "RESOLVED_FULL" and rec["strict"]["strict_full"]) else ("resolved_lenient_only" if rec["official_verdict"] == "RESOLVED_FULL" else "unresolved")
    except ProbeStopped as e:
        rec["result"] = "infra_failed:run_stopped"
        rec["stop_reason"] = str(e)
        rec["notes"].append(str(e))
    except subprocess.TimeoutExpired as e:
        rec["result"] = "infra_failed:docker_timeout"
        rec["notes"].append(str(e)[:300])
    except Exception as e:  # noqa: BLE001
        rec["result"] = f"infra_failed:{type(e).__name__}"
        rec["notes"].append(str(e)[:500])
    finally:
        # Docker exec 超时或被整批截止打断时，先抢救已有日志，再读资源，最后回收。
        if c.container_id and not rec.get("log_path"):
            try:
                partial = c.cp_out("/tmp/test_output.txt", cleanup=True)
                if partial is not None:
                    (out_dir / "test_output.txt").write_text(partial)
                    rec.update(log_path=str(out_dir / "test_output.txt"), log_sha256=sha256_text(partial), log_bytes=len(partial), log_partial=True)
            except Exception as e:  # noqa: BLE001
                rec["notes"].append(f"partial_log_unavailable:{type(e).__name__}:{str(e)[:200]}")
        rec.update(mem_peak_bytes=None, mem_peak_source="missing", oom_kill_events=None, oom_killed_flag=None, shm_size_bytes=None)
        try:
            rec.update(c.resource_facts())
        except Exception as e:  # noqa: BLE001
            rec["notes"].append(f"resource_facts_unavailable:{type(e).__name__}:{str(e)[:200]}")
        try:
            c.rm()
            rec["cleanup_ok"] = True
        except Exception as e:  # noqa: BLE001
            rec["cleanup_ok"] = False
            rec["cleanup_error"] = f"{type(e).__name__}:{str(e)[:300]}"
            if _run_control:
                _run_control.stop("cleanup_failed")
    rec["elapsed_s"] = round(time.time() - t0, 1)
    return rec


# ----------------------------------------------------------------------------
# 调度
# ----------------------------------------------------------------------------


def load_done(ledger: Path) -> set[str]:
    done = set()
    if ledger.exists():
        for line in open(ledger):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("result") and not str(r["result"]).startswith("infra_failed") and r.get("cleanup_ok") is not False:
                done.add(r["key_plan"])
    return done


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="/work/data")
    ap.add_argument("--out", default="/work/ledger")
    ap.add_argument("--ledger", default="swegym_ledger.jsonl")
    ap.add_argument("--instances", required=True, help="逗号分隔 instance_id，或 @文件（每行一个）")
    ap.add_argument("--gates", default="facts,empty,gold")
    ap.add_argument("--variants", default="default")
    ap.add_argument("--attempts", type=int, default=1)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=2400)
    ap.add_argument("--memory", default="8g")
    ap.add_argument("--cpus", default="3")
    ap.add_argument("--rerun", action="store_true", help="忽略已有结果重跑")
    ap.add_argument("--candidate-dir", default="/work/ledger/cc_patches", help="gate=candidate 时读取 <dir>/<instance_id>.diff")
    ap.add_argument("--rmi-after", action="store_true", help="同一 instance 全部 job 完成后 docker rmi 其镜像（keep 列表除外）")
    ap.add_argument("--keep-images", default=None, help="不删除的 instance_id 列表文件")
    ap.add_argument("--run-tag", default="default", help="实验条件标记：隔离日志目录、容器名与恢复键（例如 stage1_offline、shm1g）")
    ap.add_argument("--shm-size", default=None, help="docker --shm-size（例如 1g）；默认不设 = Docker 默认 64 MiB")
    ap.add_argument("--wall-seconds", type=float, default=None, help="整批墙钟预算（含最后最多 60 秒观测/回收）；不设置则沿用无整批截止的行为")
    args = ap.parse_args()
    if args.wall_seconds is not None and args.wall_seconds <= 0:
        ap.error("--wall-seconds 必须大于零")
    if args.workers < 1 or args.attempts < 1 or args.timeout < 1:
        ap.error("--workers、--attempts 和 --timeout 必须为正整数")

    global _run_control
    _run_control = RunControl(args.wall_seconds) if args.wall_seconds is not None else None
    control = _run_control
    started = time.monotonic()
    old_handlers = {}
    if control:
        for sig in (signal.SIGINT, signal.SIGTERM):
            old_handlers[sig] = signal.signal(sig, lambda number, frame: control.stop(f"signal:{number}"))
    try:
        summary = run_batch(args)
    except Exception as e:  # noqa: BLE001
        summary = {"status": "fatal", "errors": [f"{type(e).__name__}:{str(e)[:500]}"]}
    finally:
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)
        _run_control = None
    summary.update(run_tag=args.run_tag, wall_seconds=args.wall_seconds, elapsed_s=round(time.monotonic() - started, 2), stop_reason=control.reason if control else None, cleanup_reserve_s=control.cleanup_reserve if control else 0)
    summary_path = Path(args.out) / f"{Path(args.ledger).stem}_summary.json"
    try:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    except Exception as e:  # noqa: BLE001
        summary["status"] = "fatal"
        summary.setdefault("errors", []).append(f"summary_write_failed:{type(e).__name__}:{str(e)[:300]}")
    log("RUN_SUMMARY " + json.dumps(summary, ensure_ascii=False))
    return {"completed": 0, "partial": 2, "fatal": 1}[summary["status"]]


def run_batch(args) -> dict:

    data = Data(Path(args.data))
    if args.instances.startswith("@"):
        instances = [l.strip() for l in open(args.instances[1:]) if l.strip() and not l.startswith("#")]
    else:
        instances = [x.strip() for x in args.instances.split(",") if x.strip()]
    if not instances or len(set(instances)) != len(instances):
        raise ValueError("题单不能为空或包含重复 instance_id")
    gates = args.gates.split(",")
    variants = args.variants.split(",")
    ledger = Path(args.out) / args.ledger
    ledger.parent.mkdir(parents=True, exist_ok=True)
    done = set() if args.rerun else load_done(ledger)

    jobs = []
    for iid in instances:
        if iid not in data.raw or iid not in data.grading:
            raise ValueError(f"unknown instance {iid}")
        for gate in gates:
            for variant in variants:
                n = 1 if gate in ("facts",) else args.attempts
                for attempt in range(1, n + 1):
                    plan_key = f"{iid}|{gate}|{variant}|{attempt}" if args.run_tag == "default" else f"{args.run_tag}|{iid}|{gate}|{variant}|{attempt}"
                    if plan_key in done:
                        continue
                    jobs.append((iid, gate, variant, attempt, plan_key))
    log(f"{len(jobs)} jobs, {args.workers} workers, ledger={ledger}")
    write_lock = threading.Lock()
    # --rmi-after：同一 instance 的全部 job 完成后删除其镜像（keep 列表除外），用于 216 全量的 pull-run-rmi
    keep = set()
    if args.keep_images:
        keep = {l.strip() for l in open(args.keep_images) if l.strip()}
    remaining = {}
    for j in jobs:
        remaining[j[0]] = remaining.get(j[0], 0) + 1
    rm_lock = threading.Lock()
    stop = _run_control.stopped if _run_control else threading.Event()

    def work(j):
        iid, gate, variant, attempt, plan_key = j
        log(f"START {plan_key}")
        try:
            rec = run_job(data, iid, gate, variant, attempt, args)
        except Exception as e:  # noqa: BLE001
            rec = {"schema": "rh2.env_probe.swegym.v1", "runner_version": RUNNER_VERSION, "started_at": datetime.now(timezone.utc).isoformat(), "instance_id": iid, "gate": gate, "variant": variant, "attempt": attempt, "run_tag": args.run_tag, "conditions": {"memory": args.memory, "cpus": args.cpus, "shm_size": args.shm_size, "timeout_s": args.timeout}, "result": "infra_failed:worker_exception", "notes": [f"{type(e).__name__}:{str(e)[:500]}"], "worker_error": True}
            if isinstance(e, ProbeStopped):
                rec.update(result="infra_failed:run_stopped", stop_reason=str(e), worker_error=False)
        rec["key_plan"] = plan_key
        if rec.get("worker_error") or rec.get("cleanup_ok") is False:
            if _run_control:
                _run_control.stop("worker_or_cleanup_failed")
            stop.set()
        if args.rmi_after:
            with rm_lock:
                remaining[iid] -= 1
                last = remaining[iid] == 0
            if last and iid not in keep and not stop.is_set():
                try:
                    r = sh(["docker", "rmi", data.image_ref(iid)], timeout=300)
                    rec["image_cleanup_ok"] = r.returncode == 0
                    if r.returncode != 0:
                        raise RuntimeError(r.stderr.decode(errors="replace")[-300:])
                except ProbeStopped as e:
                    rec["image_cleanup_deferred"] = str(e)
                except Exception as e:  # noqa: BLE001
                    rec["image_cleanup_ok"] = False
                    rec.setdefault("notes", []).append(f"image_cleanup_failed:{type(e).__name__}:{str(e)[:300]}")
                    if _run_control:
                        _run_control.stop("image_cleanup_failed")
                    stop.set()
        with write_lock:
            with open(ledger, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        log(f"DONE  {plan_key} -> {rec.get('result')} official={rec.get('official_verdict')} strict={(rec.get('strict') or {}).get('strict_full')} t={rec.get('elapsed_s')}s install_rc={rec.get('rc_install')} t_install={rec.get('t_install')} t_test={rec.get('t_test')}")
        return rec

    records, errors, submitted = [], [], 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        pending = {}
        while pending or (submitted < len(jobs) and not stop.is_set()):
            if _run_control:
                try:
                    _run_control.remaining()
                except ProbeStopped:
                    stop.set()
            while len(pending) < args.workers and submitted < len(jobs) and not stop.is_set():
                job = jobs[submitted]
                pending[ex.submit(work, job)] = job[-1]
                submitted += 1
            if not pending:
                break
            finished, _ = cf.wait(pending, timeout=0.2, return_when=cf.FIRST_COMPLETED)
            for future in finished:
                plan_key = pending.pop(future)
                try:
                    records.append(future.result())
                except Exception as e:  # noqa: BLE001
                    errors.append(f"{plan_key}:{type(e).__name__}:{str(e)[:300]}")
                    if _run_control:
                        _run_control.stop("ledger_or_worker_failed")
                    stop.set()
    fatal = bool(errors) or any(r.get("worker_error") or r.get("cleanup_ok") is False or r.get("image_cleanup_ok") is False for r in records)
    incomplete = submitted < len(jobs) or any(str(r.get("result", "")).startswith("infra_failed") for r in records)
    return {"status": "fatal" if fatal else "partial" if incomplete or stop.is_set() else "completed", "planned_jobs": len(jobs), "submitted_jobs": submitted, "recorded_jobs": len(records), "not_started_jobs": len(jobs) - submitted, "not_recorded_keys": [e.split(":", 1)[0] for e in errors], "infra_failed_jobs": sum(str(r.get("result", "")).startswith("infra_failed") for r in records), "cleanup_failed_containers": [r.get("container_name") for r in records if r.get("cleanup_ok") is False], "errors": errors}


if __name__ == "__main__":
    sys.exit(main())
