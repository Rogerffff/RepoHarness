#!/usr/bin/env python3
"""R-f 工具窄复核：真实对账 CLI + 无 Docker 的锁互斥/异常探针。

仅在本文件所在目录新增证据。构建路径只替换 Docker 相关叶节点，
保留真实 main/_main_locked/write_overlays 与 results.json 读写。
"""
from __future__ import annotations

import contextlib
import errno
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/scripts/reconcile_r2e.py").is_file())
SCRIPTS = ROOT / "rh2/scripts"
WORK = HERE / ("probe_output_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
WORK.mkdir()
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")


def module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


reconcile = module("reconcile_r2e")
build = module("build_r2e_derived")
trusted = reconcile.load_trusted_r2e_ingest_outputs(ROOT)
g = next(g for g in trusted.result.grading_bundles if g.repo_key_lower == "coveragepy")
expected = reconcile.normalize_status_map(g.expected_map())
key = next(k for k, v in expected.items() if v == "PASSED")


def logtext(obs):
    text = "================ short test summary info ================\n"
    text += "\n".join(f"{v} r2e_tests/test_probe.py::{k.replace('.', '::')}" for k, v in obs.items()) + "\n"
    assert reconcile.normalize_status_map(reconcile.parse_log_pytest(text)) == obs
    return text


def reconcile_case(name, rh2_status, ref_status, ledger_rewards, *, old_expected=False):
    d = WORK / name
    ref_dir = d / "m3/gold_ledger/logs_r2e" / g.repo / g.source_commit_hash[:12] / "gold/a1"
    ref_dir.mkdir(parents=True)
    obs_a, obs_b = dict(expected), dict(expected)
    obs_a[key], obs_b[key] = rh2_status, ref_status
    log = d / "rh2.log"
    log.write_text(reconcile.scoring.R2E_EVAL_START_MARKER + "\n" + logtext(obs_a) + reconcile.scoring.R2E_EVAL_END_MARKER + "\n")
    (ref_dir / "test_output.txt").write_text(logtext(obs_b))
    m3 = [{"commit_hash": g.source_commit_hash, "gate": "gold", "attempt": i + 1, "reward": rw} for i, rw in enumerate(ledger_rewards)]
    (d / "m3/gold_ledger/r2e_gold_m3.jsonl").write_text("".join(json.dumps(r) + "\n" for r in m3))
    row = {"instance_id": g.instance_id, "candidate": {"kind": "gold"}, "report": {"reward": 0.0}, "log": {"path": str(log)}}
    ledger = d / "rh2.jsonl"
    ledger.write_text(json.dumps(row) + "\n")
    args = [sys.executable, "-B", str(SCRIPTS / "reconcile_r2e.py"), "--repo-root", str(ROOT), "--ledger", str(ledger), "--m3-root", str(d / "m3"), "--out", str(d / "out")]
    if old_expected:
        old_log = d / "old/logs_r2e" / g.repo / g.source_commit_hash[:12] / "gold/a1/test_output.txt"
        old_log.parent.mkdir(parents=True)
        old_log.write_text(logtext(expected))
        args += ["--old-root", str(d / "old")]
    proc = subprocess.run(args, capture_output=True, text=True, env=ENV, timeout=20)
    (d / "cli_stdout.txt").write_text(proc.stdout)
    (d / "cli_stderr.txt").write_text(proc.stderr)
    assert proc.returncode == 0, proc.stderr
    rec = json.loads((d / "out/reconcile.json").read_text())[0]
    return {k: rec[k] for k in ("agree", "reward_equal", "diff_sets_equal", "observed_maps_equal", "reference_ledger_consistent", "m3_ledger_rewards")} | {"exit_code": proc.returncode}


results = {"source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (SCRIPTS / "reconcile_r2e.py", SCRIPTS / "build_r2e_derived.py")}, "work": str(WORK.relative_to(ROOT))}
results["F1_status_mismatch"] = reconcile_case("status_mismatch", "FAILED", "ERROR", [])
assert results["F1_status_mismatch"]["diff_sets_equal"] is True
assert results["F1_status_mismatch"]["agree"] is False
results["F1_ledger_contradiction"] = reconcile_case("ledger_contradiction", "FAILED", "FAILED", [1])
assert results["F1_ledger_contradiction"]["agree"] is True
assert results["F1_ledger_contradiction"]["reference_ledger_consistent"] is False
results["null_reward_observation"] = reconcile_case("null_reward", "FAILED", "FAILED", [None])
results["mixed_reference_sources_observation"] = reconcile_case("mixed_reference_sources", "FAILED", "FAILED", [0], old_expected=True)


def argv(out, *extra):
    return ["--repo-root", str(ROOT), "--out-dir", str(out), *extra]


def quiet_main(args):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return build.main(args)


concurrent = WORK / "concurrent"
concurrent.mkdir()
(concurrent / "overlays.jsonl").write_text("sentinel\n")
(concurrent / "results.json").write_text('{"sentinel": true}\n')
worker_code = """
import importlib.util,sys
from pathlib import Path
s=importlib.util.spec_from_file_location('worker_build',sys.argv[1]); b=importlib.util.module_from_spec(s); s.loader.exec_module(b)
original=b._main_locked
def paused(ns,ap,out):
    print('READY',flush=True)
    assert sys.stdin.readline().strip()=='RELEASE'
    return original(ns,ap,out)
b._main_locked=paused
sys.exit(b.main(sys.argv[2:]))
"""
owner = subprocess.Popen([sys.executable, "-B", "-c", worker_code, str(SCRIPTS / "build_r2e_derived.py"), *argv(concurrent, "--regenerate-overlays")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=ENV)
try:
    assert owner.stdout.readline().strip() == "READY"
    refused = []
    for flags in (("--all",), ("--regenerate-overlays",)):
        p = subprocess.run([sys.executable, "-B", str(SCRIPTS / "build_r2e_derived.py"), *argv(concurrent, *flags)], capture_output=True, text=True, env=ENV, timeout=20)
        refused.append({"flags": list(flags), "exit_code": p.returncode, "error": json.loads(p.stderr)["error"]})
        assert p.returncode == 2 and (concurrent / ".build.lock").is_file()
        assert (concurrent / "overlays.jsonl").read_text() == "sentinel\n"
        assert json.loads((concurrent / "results.json").read_text()) == {"sentinel": True}
    stdout, stderr = owner.communicate("RELEASE\n", timeout=20)
    assert owner.returncode == 0, stderr
    assert not (concurrent / ".build.lock").exists()
    results["F2_two_process_exclusion"] = {"contenders": refused, "owner_exit_code": owner.returncode, "lock_released": True, "regenerated": (concurrent / "overlays.jsonl").read_text() == ""}
finally:
    if owner.poll() is None:
        owner.kill()
        owner.communicate()


events = []
out = WORK / "read_write_coverage"
out.mkdir()
(out / "results.json").write_text(json.dumps({"tasks": {"older_task": {"ok": True}}}))
real_read, real_write = Path.read_text, Path.write_text


def checked_read(path, *a, **kw):
    if path.is_relative_to(out):
        assert (out / ".build.lock").exists(), path
        events.append({"operation": "read", "path": str(path.relative_to(out))})
    return real_read(path, *a, **kw)


def checked_write(path, *a, **kw):
    if path.is_relative_to(out):
        assert (out / ".build.lock").exists(), path
        events.append({"operation": "write", "path": str(path.relative_to(out))})
    return real_write(path, *a, **kw)


def fake_build(_docker, *, out, grading, **kw):
    assert (out / ".build.lock").exists()
    result = {"ok": True, "failures": [], "overlay": {"task_id": "r2e_gym_subset::" + grading.instance_id}}
    d = out / grading.instance_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "facts.json").write_text(json.dumps(result))
    return result


with patch.object(build, "build_one", fake_build), patch.object(build, "host_facts", lambda _: {"probe": "no_docker"}), patch.object(Path, "read_text", checked_read), patch.object(Path, "write_text", checked_write):
    assert quiet_main(argv(out, "--task-ids", g.instance_id)) == 0
assert not (out / ".build.lock").exists()
assert "older_task" in json.loads((out / "results.json").read_text())["tasks"]
assert {e["path"] for e in events if e["operation"] == "read"} >= {"results.json", g.instance_id + "/facts.json"}
assert {e["path"] for e in events if e["operation"] == "write"} >= {"results.json", "overlays.jsonl", g.instance_id + "/facts.json"}
results["F2_read_write_coverage"] = {"events": events, "all_inside_lock": True, "previous_results_preserved": True}


releases = []
for name, exc in (("runtime_error", RuntimeError("injected")), ("keyboard_interrupt", KeyboardInterrupt()), ("system_exit", SystemExit(2))):
    out_exc = WORK / name
    with patch.object(build, "_main_locked", side_effect=exc):
        try:
            quiet_main(argv(out_exc, "--regenerate-overlays"))
        except BaseException as caught:
            assert type(caught) is type(exc)
        else:
            raise AssertionError(name)
    assert not (out_exc / ".build.lock").exists()
    releases.append({"case": name, "lock_released": True})
for name, payload in (("malformed_facts", "{"),):
    out_exc = WORK / name
    (out_exc / "one").mkdir(parents=True)
    (out_exc / "one/facts.json").write_text(payload)
    try:
        quiet_main(argv(out_exc, "--regenerate-overlays"))
    except json.JSONDecodeError:
        pass
    else:
        raise AssertionError(name)
    assert not (out_exc / ".build.lock").exists()
    releases.append({"case": name, "lock_released": True})
results["F2_exception_release"] = releases

for sink in ("overlays.jsonl", "results.json"):
    out_sink = WORK / ("sink_failure_" + sink.replace(".", "_"))

    def fail_write(path, *a, **kw):
        if path == out_sink / sink:
            assert (out_sink / ".build.lock").exists()
            raise OSError(errno.ENOSPC, "injected artifact sink failure")
        return real_write(path, *a, **kw)

    with patch.object(build, "build_one", fake_build), patch.object(build, "host_facts", lambda _: {"probe": "no_docker"}), patch.object(Path, "write_text", fail_write):
        try:
            quiet_main(argv(out_sink, "--task-ids", g.instance_id))
        except OSError as exc:
            assert exc.errno == errno.ENOSPC
        else:
            raise AssertionError(sink)
    assert not (out_sink / ".build.lock").exists()
    releases.append({"case": "artifact_write_error:" + sink, "lock_released": True})


out_header = WORK / "lock_header_write_error"
real_fdopen = os.fdopen


class FailingLockWriter:
    def __init__(self, fd, *a, **kw):
        self.real = real_fdopen(fd, *a, **kw)

    def __enter__(self):
        return self

    def write(self, text):
        raise OSError(errno.ENOSPC, "injected lock metadata write failure")

    def __exit__(self, *_):
        self.real.close()


with patch.object(build.os, "fdopen", FailingLockWriter):
    try:
        quiet_main(argv(out_header, "--regenerate-overlays"))
    except OSError as exc:
        assert exc.errno == errno.ENOSPC
    else:
        raise AssertionError("expected lock metadata write failure")
assert (out_header / ".build.lock").exists()
retry = quiet_main(argv(out_header, "--regenerate-overlays"))
assert retry == 2
results["F2_lock_header_write_error_observation"] = {"lock_left_behind": True, "lock_bytes": (out_header / ".build.lock").stat().st_size, "retry_exit_code": retry, "overlays_written": (out_header / "overlays.jsonl").exists()}

(WORK / "summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(results, ensure_ascii=False, indent=2))
