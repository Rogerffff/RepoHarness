"""W5a：launch trap 入口（run-label 兜底清理 + 无残留检查）。

用桩 docker（sh 脚本，状态文件记录"仍存在的容器"）真实执行清理与检查；
"伪容器句柄" = 状态文件里的名字；临时目录 = tmp_path 下真实目录。三条纪律各有
反例：查询失败 ≠ 零残留；只动本 run label 的容器；先记后删。
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

from repoharness2.shutdown import run_residue

RUN_ID = "20260902T000000Z-p1-r7"
SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "rh2_run_trap_cleanup.sh"
RESIDUE_PY = Path(run_residue.__file__)


def _stub_docker(bins: Path, state: Path, *, fail_ps: bool = False, fail_rm_for: str = "") -> Path:
    bins.mkdir(parents=True, exist_ok=True)
    script = f"""#!/bin/sh
STATE="{state}"
LOG="{state}.log"
echo "$@" >> "$LOG"
if [ "$1" = "ps" ]; then
  if [ "{int(fail_ps)}" = "1" ]; then echo "Cannot connect to the Docker daemon" >&2; exit 1; fi
  case "$*" in *"label=rh2.run_id={RUN_ID} "*) cat "$STATE" ;; esac
  exit 0
fi
if [ "$1" = "rm" ]; then
  name="$3"
  if [ "$name" = "{fail_rm_for}" ]; then echo "cannot remove $name: device busy" >&2; exit 1; fi
  grep -v "^$name$" "$STATE" > "$STATE.new" || true
  mv "$STATE.new" "$STATE"
  echo "$name"
  exit 0
fi
exit 2
"""
    docker = bins / "docker"
    docker.write_text(script, encoding="utf-8")
    docker.chmod(docker.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return docker


def _setup(tmp_path: Path, names: list[str], **kw) -> tuple[Path, Path, list[str]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    state = tmp_path / "containers.txt"
    state.write_text("".join(f"{n}\n" for n in names), encoding="utf-8")
    docker = _stub_docker(tmp_path / "bin", state, **kw)
    scratch = tmp_path / "scratch"
    ws = scratch / f"rh2-{RUN_ID}-ws1"
    ws.mkdir(parents=True)
    (ws / "junk.txt").write_text("x", encoding="utf-8")
    other = scratch / "rh2-otherrun-ws9"
    other.mkdir()
    return docker, state, [str(scratch / f"rh2-{RUN_ID}-*")]


def test_cleanup_removes_labeled_containers_and_tmp_then_check_is_clean(tmp_path):
    docker, state, globs = _setup(tmp_path, ["rh2-rollout-a-1", "rh2-grading-b-2"])
    report = run_residue.cleanup_residue(run_id=RUN_ID, docker_bin=str(docker), tmp_globs=globs)
    assert report["ok"] is True and report["docker_query_ok"] is True
    assert report["containers_found"] == ["rh2-grading-b-2", "rh2-rollout-a-1"]  # 先记
    assert report["containers_removed"] == ["rh2-grading-b-2", "rh2-rollout-a-1"]  # 后删
    assert report["containers_failed"] == {}
    assert state.read_text(encoding="utf-8") == ""  # 伪容器句柄全部消失
    assert [Path(p).name for p in report["tmp_removed"]] == [f"rh2-{RUN_ID}-ws1"]
    assert not (tmp_path / "scratch" / f"rh2-{RUN_ID}-ws1").exists()
    assert (tmp_path / "scratch" / "rh2-otherrun-ws9").is_dir()  # 别的 run 的目录不碰
    log = (str(state) + ".log")
    assert "rm -f rh2-rollout-a-1" in Path(log).read_text(encoding="utf-8")
    check = run_residue.check_residue(run_id=RUN_ID, docker_bin=str(docker), tmp_globs=globs)
    assert check["ok"] is True and check["residue_count"] == 0 and check["containers"] == []


def test_check_lists_residue_and_fails(tmp_path):
    docker, _state, globs = _setup(tmp_path, ["rh2-rollout-left"])
    out = tmp_path / "out" / "check.json"
    rc = run_residue.main(
        ["check", "--run-id", RUN_ID, "--docker-bin", str(docker), "--tmp-glob", globs[0], "--out", str(out)]
    )
    assert rc == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["ok"] is False and report["residue_count"] == 2
    assert report["containers"] == ["rh2-rollout-left"]
    assert [Path(p).name for p in report["tmp"]] == [f"rh2-{RUN_ID}-ws1"]


def test_docker_query_failure_is_not_zero_residue(tmp_path):
    docker, _state, globs = _setup(tmp_path, [], fail_ps=True)
    cleanup = run_residue.cleanup_residue(run_id=RUN_ID, docker_bin=str(docker), tmp_globs=[])
    assert cleanup["ok"] is False and cleanup["docker_query_ok"] is False and cleanup["containers_found"] is None
    assert "rc=1" in cleanup["detail"]["docker_error"]
    check = run_residue.check_residue(run_id=RUN_ID, docker_bin=str(docker), tmp_globs=[])
    assert check["ok"] is False and check["residue_count"] is None
    missing = run_residue.check_residue(run_id=RUN_ID, docker_bin=str(tmp_path / "no-such-docker"), tmp_globs=[])
    assert missing["ok"] is False and "docker ps failed" in missing["detail"]["docker_error"]


def test_cleanup_rm_failure_is_reported_and_check_still_sees_it(tmp_path):
    docker, state, _globs = _setup(tmp_path, ["rh2-rollout-busy", "rh2-grading-ok"], fail_rm_for="rh2-rollout-busy")
    report = run_residue.cleanup_residue(run_id=RUN_ID, docker_bin=str(docker), tmp_globs=[])
    assert report["ok"] is False
    assert report["containers_removed"] == ["rh2-grading-ok"]
    assert list(report["containers_failed"]) == ["rh2-rollout-busy"]
    assert "device busy" in report["containers_failed"]["rh2-rollout-busy"]
    check = run_residue.check_residue(run_id=RUN_ID, docker_bin=str(docker), tmp_globs=[])
    assert check["ok"] is False and check["containers"] == ["rh2-rollout-busy"]


def test_only_own_run_label_is_touched_and_empty_run_id_rejected(tmp_path):
    docker, state, _globs = _setup(tmp_path, ["rh2-rollout-mine"])
    foreign = run_residue.cleanup_residue(run_id="some-other-run", docker_bin=str(docker), tmp_globs=[])
    assert foreign["ok"] is True and foreign["containers_found"] == [] and foreign["containers_removed"] == []
    assert state.read_text(encoding="utf-8") == "rh2-rollout-mine\n"  # 本 run 的容器没被别的 run id 删掉
    names, error = run_residue.list_run_containers(str(docker), "")
    assert names is None and "run_id 为空" in error
    empty = run_residue.cleanup_residue(run_id="", docker_bin=str(docker), tmp_globs=[])
    assert empty["ok"] is False and empty["containers_found"] is None


def test_trap_script_end_to_end_clean_and_residue(tmp_path):
    env = {**os.environ, "RH2_PYTHON": sys.executable}
    docker, state, globs = _setup(tmp_path, ["rh2-rollout-x", "rh2-grading-y"])
    out_dir = tmp_path / "ev"
    proc = subprocess.run(
        ["bash", str(SCRIPT), RUN_ID, str(docker), str(out_dir), globs[0]],
        capture_output=True, text=True, env=env, timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    cleanup = json.loads((out_dir / "run_residue_cleanup.json").read_text(encoding="utf-8"))
    check = json.loads((out_dir / "run_residue_check.json").read_text(encoding="utf-8"))
    assert cleanup["containers_removed"] == ["rh2-grading-y", "rh2-rollout-x"] and check["residue_count"] == 0
    assert "无残留" in proc.stdout

    # 残留分支：一个容器删不掉 → 脚本非零，两份报告都在
    docker2, _state2, _ = _setup(tmp_path / "second", ["rh2-rollout-stuck"], fail_rm_for="rh2-rollout-stuck")
    out2 = tmp_path / "ev2"
    proc2 = subprocess.run(
        ["bash", str(SCRIPT), RUN_ID, str(docker2), str(out2)],
        capture_output=True, text=True, env=env, timeout=60,
    )
    assert proc2.returncode == 1
    check2 = json.loads((out2 / "run_residue_check.json").read_text(encoding="utf-8"))
    assert check2["containers"] == ["rh2-rollout-stuck"] and check2["ok"] is False
    assert "cleanup_rc=1 check_rc=1" in proc2.stderr

    # 用法错误
    assert subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True, env=env).returncode == 2


def test_run_residue_module_runs_standalone_by_file_path(tmp_path):
    """launch trap 里 PYTHONPATH 未必就位：模块必须能按文件路径独立运行（纯 stdlib）。"""

    docker, _state, _ = _setup(tmp_path, [])
    proc = subprocess.run(
        [sys.executable, str(RESIDUE_PY), "check", "--run-id", RUN_ID, "--docker-bin", str(docker)],
        capture_output=True, text=True, env={"PATH": os.environ["PATH"]}, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["residue_count"] == 0
