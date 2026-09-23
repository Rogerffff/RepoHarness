#!/usr/bin/env python3
"""Claude Code + 外部 API 模型（DeepSeek Anthropic 兼容端点）的可解性参考探针。

**这不是 rh2 编排链**：rh2 的 Anthropic adapter 直发 SGLang，沙箱隔离网络不可达公网。
本探针在同一任务镜像里独立运行 Claude Code 2.1.205（rh2 pin），尽量复用 rh2 条件：
  - 提示词 = rh2 `bundles.render_user_prompt(public)` 的原文格式（无额外 hint）
  - 启动参数 = rh2 ClaudeCodeHarness.launch_flags + launch.sh 默认 `--disallowedTools Task WebFetch WebSearch`
  - 运行用户 agent/54321，工作目录 /testbed；先执行 rh2 的 git-sanitize.sh 清理未来 git 对象
  - 结束后导出 patch（含新增文件），交给 swegym_probe.py 的 candidate 门在 fresh 容器用官方脚本评分
结果字段名 api_reference_run；只回答“该题在此 harness 下能否被一个强模型解出”，不进任何成功率统计。
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

RUNNER_VERSION = "cc_probe/0.1"
CC_VERSION = "2.1.205"
AGENT_UID = 54321
_lock = threading.Lock()


def log(msg):
    with _lock:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def sh(cmd, timeout=None):
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def dexec(name, script, user=None, timeout=600):
    cmd = ["docker", "exec"] + (["-u", user] if user else []) + [name, "bash", "-c", script]
    return sh(cmd, timeout=timeout)


def dcp_in(name, text, dest, mode="0644", owner=None):
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write(text)
        tmp = f.name
    try:
        r = sh(["docker", "cp", tmp, f"{name}:{dest}"], timeout=120)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.decode()[-300:])
        own = f" && chown {owner} {shlex.quote(dest)}" if owner else ""
        dexec(name, f"chmod {mode} {shlex.quote(dest)}{own}", timeout=30)
    finally:
        os.unlink(tmp)


def dcp_out(name, src):
    with tempfile.TemporaryDirectory() as td:
        r = sh(["docker", "cp", f"{name}:{src}", td + "/f"], timeout=600)
        return Path(td + "/f").read_text(errors="replace") if r.returncode == 0 else None


def deepseek_balance(key):
    try:
        req = urllib.request.Request("https://api.deepseek.com/user/balance", headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            d = json.load(resp)
        for b in d.get("balance_infos", []):
            if b.get("currency") == "CNY":
                return float(b.get("total_balance"))
    except Exception as e:  # noqa: BLE001
        log(f"balance query failed: {e}")
    return None


def render_user_prompt(public):
    return (
        f"Fix the following issue from the `{public['repo']}` repository "
        f"(checked out at {public['workdir']}, commit {public['base_commit'][:12]}):\n\n"
        f"{public['problem_statement']}"
    )


def summarize_stream(stream_text):
    turns = 0
    tools = Counter()
    result = {}
    init = {}
    n_lines = 0
    for ln in stream_text.splitlines():
        ln = ln.strip()
        if not ln.startswith("{"):
            continue
        try:
            ev = json.loads(ln)
        except Exception:
            continue
        n_lines += 1
        t = ev.get("type")
        if t == "system" and ev.get("subtype") == "init":
            init = {k: ev.get(k) for k in ("model", "permissionMode", "claude_code_version", "tools") if k in ev}
        elif t == "assistant":
            turns += 1
            msg = ev.get("message") or {}
            for blk in msg.get("content") or []:
                if isinstance(blk, dict) and blk.get("type") == "tool_use":
                    tools[blk.get("name", "?")] += 1
        elif t == "result":
            result = {k: ev.get(k) for k in ("subtype", "is_error", "num_turns", "duration_ms", "duration_api_ms", "total_cost_usd", "stop_reason", "terminal_reason") if k in ev}
            usage = ev.get("usage") or {}
            result["usage"] = {k: usage.get(k) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens") if k in usage}
            mu = ev.get("modelUsage") or {}
            result["models"] = list(mu.keys())
    return {"assistant_events": turns, "num_turns": result.get("num_turns"), "tool_calls": dict(tools), "tool_calls_total": sum(tools.values()), "cc_result": result, "init": init, "events": n_lines}


def run_task(iid, public, image, args, key):
    t0 = time.time()
    name = f"rh2cc_{iid.lower().replace('__', '_s_')[:40]}"
    out_dir = Path(args.out) / "logs_cc" / iid
    out_dir.mkdir(parents=True, exist_ok=True)
    rec = {
        "schema": "rh2.env_probe.cc_reference.v1",
        "runner_version": RUNNER_VERSION,
        "kind": "api_reference_run",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "instance_id": iid,
        "repo": public["repo"],
        "image_ref": image,
        "harness": f"claude-code {CC_VERSION}",
        "model": args.model,
        "endpoint": "https://api.deepseek.com/anthropic",
        "max_turns": args.max_turns,
        "wall_clock_s": args.wall,
        "disallowed_tools": "Task WebFetch WebSearch",
        "prompt_format": "rh2.bundles.render_user_prompt",
        "result": None,
        "notes": [],
    }
    bal0 = deepseek_balance(key)
    rec["balance_cny_before"] = bal0
    sh(["docker", "rm", "-f", name], timeout=60)
    try:
        r = sh(["docker", "run", "-d", "--name", name, "--memory", args.memory, "--memory-swap", args.memory, "--cpus", args.cpus, "--label", "rh2probe=1", image, "sleep", "infinity"], timeout=180)
        if r.returncode != 0:
            raise RuntimeError("docker run: " + r.stderr.decode()[-300:])
        r = sh(["docker", "cp", args.ccbundle, f"{name}:/opt/ccbundle"], timeout=600)
        if r.returncode != 0:
            raise RuntimeError("cp ccbundle: " + r.stderr.decode()[-300:])
        settings = json.dumps({"hasCompletedOnboarding": True, "bypassPermissionsModeAccepted": True})
        setup = f"""
set -e
useradd -u {AGENT_UID} -m -s /bin/bash agent 2>/dev/null || true
ln -sf /opt/ccbundle/node/bin/node /usr/local/bin/node
ln -sf /opt/ccbundle/cc/bin/claude /usr/local/bin/claude
mkdir -p /home/agent/.claude
echo {shlex.quote(settings)} | tee /home/agent/.claude.json /home/agent/.claude/settings.json > /dev/null
chown -R agent:agent /home/agent
cd /testbed && echo RH2_FACT before_future=$(git rev-list --all --count --not HEAD 2>/dev/null) before_remotes=$(git remote | wc -l)
"""
        s = dexec(name, setup, timeout=300)
        if s.returncode != 0:
            raise RuntimeError("setup: " + s.stderr.decode()[-400:])
        facts = {}
        for ln in s.stdout.decode(errors="replace").splitlines():
            if ln.startswith("RH2_FACT "):
                for kv in ln[9:].split():
                    if "=" in kv:
                        k2, v2 = kv.split("=", 1)
                        facts[k2] = v2
        # git-sanitize（rh2 脚本，root）
        san = Path(args.sanitize_script).read_text()
        dcp_in(name, san, "/tmp/git-sanitize.sh", "0755")
        g = dexec(name, "bash /tmp/git-sanitize.sh 2>&1 | tail -5; cd /testbed && echo RH2_FACT after_future=$(git rev-list --all --count --not HEAD 2>/dev/null) after_remotes=$(git remote | wc -l) after_refs=$(git for-each-ref | wc -l)", timeout=900)
        for ln in g.stdout.decode(errors="replace").splitlines():
            if ln.startswith("RH2_FACT "):
                for kv in ln[9:].split():
                    if "=" in kv:
                        k2, v2 = kv.split("=", 1)
                        facts[k2] = v2
            elif ln.startswith("RH2_GIT_SANITIZE"):
                facts["sanitize_line"] = ln[:120]
        rec["facts"] = facts
        dexec(name, "chown -R agent:agent /testbed", timeout=600)
        prompt = render_user_prompt(public)
        dcp_in(name, prompt, "/home/agent/prompt.txt", "0644", "agent:agent")
        (out_dir / "prompt.txt").write_text(prompt)
        run_script = f"""#!/bin/bash
export HOME=/home/agent
export PATH=/opt/ccbundle/node/bin:/usr/local/bin:$PATH
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_AUTH_TOKEN={shlex.quote(key)}
export ANTHROPIC_MODEL={shlex.quote(args.model)}
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1
export CLAUDE_CODE_ATTRIBUTION_HEADER=0
export DISABLE_TELEMETRY=1
export DISABLE_AUTOUPDATER=1
cd /testbed
echo "RH2_CC_START $(date +%s.%N)"
timeout -k 30 {args.wall} claude -p "$(cat /home/agent/prompt.txt)" --permission-mode bypassPermissions --output-format stream-json --include-hook-events --verbose --disallowedTools Task WebFetch WebSearch --max-turns {args.max_turns} > /home/agent/stream.jsonl 2> /home/agent/stderr.txt
echo "RH2_CC_END $(date +%s.%N) rc=$?"
"""
        dcp_in(name, run_script, "/home/agent/run_cc.sh", "0700", "agent:agent")
        t_cc = time.time()
        r = dexec(name, "bash /home/agent/run_cc.sh", user=f"{AGENT_UID}:{AGENT_UID}", timeout=args.wall + 180)
        rec["t_cc_s"] = round(time.time() - t_cc, 1)
        tail = r.stdout.decode(errors="replace").strip().splitlines()
        rec["cc_rc"] = next((ln.split("rc=")[-1] for ln in tail if ln.startswith("RH2_CC_END")), None)
        stream = dcp_out(name, "/home/agent/stream.jsonl") or ""
        stderr = dcp_out(name, "/home/agent/stderr.txt") or ""
        (out_dir / "stream.jsonl").write_text(stream)
        (out_dir / "stderr.txt").write_text(stderr)
        rec["stream_bytes"] = len(stream)
        rec["stderr_tail"] = stderr[-500:]
        rec.update(summarize_stream(stream))
        # 导出 patch（root；含新增文件；排除探针自身文件）
        exp = dexec(name, "cd /testbed && git add -A -- . && git diff --cached --binary HEAD > /tmp/candidate.diff; git reset -q; wc -c < /tmp/candidate.diff; git status --porcelain | wc -l", timeout=300)
        patch = dcp_out(name, "/tmp/candidate.diff") or ""
        pdir = Path(args.candidate_dir)
        pdir.mkdir(parents=True, exist_ok=True)
        (pdir / f"{iid}.diff").write_text(patch)
        (out_dir / "candidate.diff").write_text(patch)
        rec["patch_bytes"] = len(patch)
        rec["patch_files"] = sorted({ln.split(" b/", 1)[1] for ln in patch.splitlines() if ln.startswith("diff --git ")})
        rec["patch_touches_tests"] = [p for p in rec["patch_files"] if "/test" in p or p.startswith("test")]
        rec["result"] = "ran" if patch.strip() else "ran_empty_patch"
    except subprocess.TimeoutExpired as e:
        rec["result"] = "infra_failed:docker_timeout"
        rec["notes"].append(str(e)[:300])
    except Exception as e:  # noqa: BLE001
        rec["result"] = f"infra_failed:{type(e).__name__}"
        rec["notes"].append(str(e)[:500])
    finally:
        sh(["docker", "rm", "-f", name], timeout=120)
    bal1 = deepseek_balance(key)
    rec["balance_cny_after"] = bal1
    rec["cost_cny"] = round(bal0 - bal1, 3) if (bal0 is not None and bal1 is not None) else None
    rec["elapsed_s"] = round(time.time() - t0, 1)
    return rec


def grade_candidate(iid, args):
    """调用 swegym_probe.py 的 candidate 门（官方脚本，fresh 容器，默认网络）。"""
    cmd = [sys.executable, str(Path(__file__).parent / "swegym_probe.py"), "--data", args.data, "--out", args.out, "--ledger", "cc_candidate_grading.jsonl", "--instances", iid, "--gates", "candidate", "--variants", "default", "--workers", "1", "--candidate-dir", args.candidate_dir, "--rerun"]
    r = sh(cmd, timeout=3600)
    ledger = Path(args.out) / "cc_candidate_grading.jsonl"
    last = None
    if ledger.exists():
        for ln in open(ledger):
            try:
                rr = json.loads(ln)
            except Exception:
                continue
            if rr.get("instance_id") == iid and rr.get("gate") == "candidate":
                last = rr
    if last is None:
        return {"grade_result": "grading_failed", "grade_stderr": r.stderr.decode(errors="replace")[-300:]}
    return {"grade_result": last.get("result"), "official_verdict": last.get("official_verdict"), "strict_full": (last.get("strict") or {}).get("strict_full"), "f2p_status": (last.get("strict") or {}).get("f2p_status"), "p2p_not_ok": (last.get("strict") or {}).get("p2p_not_ok"), "patch_apply": last.get("patch_apply")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="/work/data")
    ap.add_argument("--out", default="/work/ledger")
    ap.add_argument("--ledger", default="cc_reference_ledger.jsonl")
    ap.add_argument("--instances", required=True)
    ap.add_argument("--model", default="deepseek-v4-pro")
    ap.add_argument("--max-turns", type=int, default=60)
    ap.add_argument("--wall", type=int, default=1800)
    ap.add_argument("--memory", default="8g")
    ap.add_argument("--cpus", default="3")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--ccbundle", default="/work/ccbundle")
    ap.add_argument("--sanitize-script", default="/work/data/sandbox_probes/git-sanitize.sh")
    ap.add_argument("--candidate-dir", default="/work/ledger/cc_patches")
    ap.add_argument("--key-file", default="/work/secrets/deepseek.key")
    ap.add_argument("--reserve-cny", type=float, default=10.0)
    ap.add_argument("--no-grade", action="store_true")
    args = ap.parse_args()
    key = Path(args.key_file).read_text().strip()
    public = {}
    for line in open(Path(args.data) / "public_bundles_v0.jsonl"):
        p = json.loads(line)
        public[p["instance_id"]] = p
    cands = {}
    for line in open(Path(args.data) / "candidate_manifest.jsonl"):
        c = json.loads(line)
        if "SWE-Gym" in c["source"]:
            cands[c["instance_id"]] = c
    if args.instances.startswith("@"):
        instances = [l.strip() for l in open(args.instances[1:]) if l.strip() and not l.startswith("#")]
    else:
        instances = [x.strip() for x in args.instances.split(",") if x.strip()]
    ledger = Path(args.out) / args.ledger
    ledger.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if ledger.exists():
        for ln in open(ledger):
            try:
                rr = json.loads(ln)
                if rr.get("result") and not str(rr["result"]).startswith("infra_failed"):
                    done.add(rr["instance_id"])
            except Exception:
                pass
    todo = [i for i in instances if i not in done]
    log(f"{len(todo)} tasks todo (skipping {len(done)} done), workers={args.workers}")
    stop = threading.Event()

    def work(iid):
        if stop.is_set():
            return
        bal = deepseek_balance(key)
        if bal is not None and bal < args.reserve_cny:
            log(f"balance {bal} CNY below reserve {args.reserve_cny}; stopping")
            stop.set()
            return
        image = cands[iid]["image_ref"] if iid in cands else public[iid]["image"]
        log(f"START {iid} balance={bal}")
        rec = run_task(iid, public[iid], image, args, key)
        if not args.no_grade and rec.get("result", "").startswith("ran") and rec.get("patch_bytes", 0) > 0:
            rec.update(grade_candidate(iid, args))
        elif rec.get("result") == "ran_empty_patch":
            rec["grade_result"] = "unresolved_empty_patch"
        with _lock:
            with open(ledger, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        cr = rec.get("cc_result") or {}
        log(f"DONE  {iid} -> {rec.get('result')} grade={rec.get('grade_result')} official={rec.get('official_verdict')} turns={rec.get('num_turns')} tools={rec.get('tool_calls_total')} cost_cny={rec.get('cost_cny')} t_cc={rec.get('t_cc_s')}s subtype={cr.get('subtype')} patch_files={len(rec.get('patch_files') or [])}")

    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(work, todo))


if __name__ == "__main__":
    sys.exit(main())
