"""第六组 2A 渲染（network_supply_brief_20260924 §4.2 / §4.5 NS1）：安装段与测试段拆成两次 exec。

真实 bundle（getmoto__moto-6913）经当前 renderer 渲染两段脚本，本机 Bash 执行；只把环境相关的行换成本机等价物
（conda 激活 → `:`、`cd /testbed` → 临时目录），安装命令换成带 export / 函数 / cd 的确定性配方，测试命令换成确定性
PASSED 文本。对照三种形态（NS1）：
- 原单 shell（`render_v2_candidate_test_script`）；
- 只携带状态、没有来源前导（反证：官方 Start/End 冒号标记只有 xtrace 才进日志 → 标记全缺、解析 0 项）；
- 前导 + 携带（本实现）：Start/End 齐全，真实 parser 解析项数与单 shell 相同，导出变量 / 函数 / cwd 带到测试段。
另覆盖三种安装结束形态（提前退出 / 状态写入失败 / 安装命令非零但 shell 继续）的阶段行，以及没有安装段的题返回 None。
"""

from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path

import pytest

from repoharness2.adapters.slime.prepared_task_face import (
    SUPPLY_CARRY_RESTORE_LINES,
    V2_EVAL_END_MARKER,
    V2_EVAL_START_MARKER,
    _v2_candidate_test_lines,
    build_grading_spec_from_host_view,
    render_v2_candidate_install_script,
    render_v2_candidate_test_after_install_script,
    render_v2_candidate_test_script,
)
from repoharness2.envpack.bundles_v2 import PrivateGradingBundleV2
from repoharness2.envpack.spec_vendor import derive_install_cmd, derive_test_command_for_bundle
from repoharness2.envpack.training_view import HostGradingView

REPO_ROOT = Path(__file__).resolve().parents[3]
GRADING_BUNDLES_V2 = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/grading_bundles_v2_v0.jsonl"
INSTANCE = "getmoto__moto-6913"
RECIPE = ('export OMP_NUM_THREADS=1; export PATH="/opt/probe/bin:$PATH"; carry_func() { echo "func-$OMP_NUM_THREADS"; }; '
          'NOT_EXPORTED=hidden; mkdir -p "$RH2_WORK/sub" && cd "$RH2_WORK/sub"')


def _bundle(instance_id: str) -> PrivateGradingBundleV2:
    for line in GRADING_BUNDLES_V2.read_text().splitlines():
        if f'"{instance_id}"' in line:
            row = json.loads(line)
            return PrivateGradingBundleV2(**{k: v for k, v in row.items() if k != "schema_id"})
    raise AssertionError(instance_id)


@pytest.fixture(scope="module")
def moto():
    grading = _bundle(INSTANCE)
    view = HostGradingView(
        task_id=f"swe_gym_lite::{grading.instance_id}", source="swe_gym_lite", instance_id=grading.instance_id,
        environment_package_digest="sha256:" + "0" * 64, grading_bundle_digest=grading.digest(), grading=grading,
    )
    spec = build_grading_spec_from_host_view(view, image="unused:probe", image_manifest_digest="sha256:" + "1" * 64)
    return grading, spec


def _localize(script: str, grading: PrivateGradingBundleV2, *, install: str = RECIPE) -> str:
    """只换环境相关的行（本机没有 /opt/miniconda3 与 /testbed）；其余逐字是 renderer 的输出。"""

    official_install = derive_install_cmd(grading.spec_vendor_id, grading.repo_key_lower, grading.version)
    official_test = derive_test_command_for_bundle(grading)
    payload = "\n".join(f"PASSED {name}" for name in [*grading.fail_to_pass, *grading.pass_to_pass]) + "\n"
    probe_test = ('echo "RH2_PROBE_CARRIED=${OMP_NUM_THREADS:-absent}:$(carry_func 2>/dev/null || echo nofunc):'
                  '${PWD##*/}:${NOT_EXPORTED:-absent}"; printf %s ' + shlex.quote(payload))
    out = []
    for line in script.splitlines():
        if line in ("source /opt/miniconda3/bin/activate", "conda activate testbed") or line.startswith("git config --global"):
            out.append(":")
        elif line == "cd /testbed":
            out.append('cd "$RH2_WORK"')
        elif line == official_install:
            out.append(install)
        elif line == official_test:
            out.append(probe_test)
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def _bash(script: str, work: Path, home: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["/bin/bash", "-c", script], env={"PATH": "/usr/bin:/bin", "HOME": str(home), "RH2_WORK": str(work)},
                          cwd=work, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)


def _markers(log: str) -> tuple[bool, bool]:
    return (f"+ : '{V2_EVAL_START_MARKER}'" in log, f"+ : '{V2_EVAL_END_MARKER}'" in log)


def test_two_exec_form_with_preamble_parses_like_the_single_shell_and_carries_state(moto, tmp_path):
    grading, spec = moto
    install = render_v2_candidate_install_script(grading)
    test = render_v2_candidate_test_after_install_script(grading)
    assert install is not None and test is not None
    assert install.splitlines()[:2] == ["#!/bin/bash", "set -xo pipefail"] and test.splitlines()[:2] == ["#!/bin/bash", "set -xo pipefail"]

    single = _bash(_localize(render_v2_candidate_test_script(grading, spec.hygiene.test_files), grading), tmp_path, tmp_path)
    single_verdict = spec.parse_log(single.stdout)
    assert _markers(single.stdout) == (True, True) and single_verdict.num_parsed_tests > 0

    home = tmp_path / "home"
    home.mkdir()
    first = _bash(_localize(install, grading), tmp_path, home)
    assert "\nRH2_PHASE_CARRY=start\n" in first.stdout and "\nRH2_PHASE_HANDOFF=1\n" in first.stdout
    second = _bash(_localize(test, grading), tmp_path, home)
    log = first.stdout + second.stdout
    assert _markers(log) == (True, True)
    verdict = spec.parse_log(log)
    assert verdict.num_parsed_tests == single_verdict.num_parsed_tests and verdict.resolution == single_verdict.resolution
    # 导出变量、函数、cwd 带到测试段；未导出变量不带
    assert "\nRH2_PROBE_CARRIED=1:func-1:sub:absent\n" in log
    # 恢复过程不进 xtrace（导出表不刷进日志）
    assert "+ . " not in second.stdout and "declare -x" not in second.stdout


def test_falsifier_carry_without_the_source_preamble_loses_the_markers(moto, tmp_path):
    grading, spec = moto
    home = tmp_path / "home"
    home.mkdir()
    _bash(_localize(render_v2_candidate_install_script(grading), grading), tmp_path, home)
    bare = "\n".join([*SUPPLY_CARRY_RESTORE_LINES[1:-1], *_v2_candidate_test_lines(grading)]) + "\n"
    second = _bash(_localize(bare, grading), tmp_path, home)
    assert _markers(second.stdout) == (False, False) and spec.parse_log(second.stdout).num_parsed_tests == 0


@pytest.mark.parametrize(("install", "carry_start", "handoff", "install_rc"), [
    ("exit 3", False, False, None),  # 安装段 shell 提前退出：没走到携带尾部
    ("false", True, True, "1"),  # 安装命令非零但 shell 继续：照常交接
])
def test_install_end_shapes_are_visible_in_the_phase_lines(moto, tmp_path, install, carry_start, handoff, install_rc):
    grading, _spec = moto
    home = tmp_path / "home"
    home.mkdir()
    out = _bash(_localize(render_v2_candidate_install_script(grading), grading, install=install), tmp_path, home).stdout
    assert ("\nRH2_PHASE_CARRY=start\n" in out) is carry_start and ("\nRH2_PHASE_HANDOFF=1\n" in out) is handoff
    if install_rc is not None:
        assert f"\nRH2_INSTALL_RC={install_rc}\n" in out


def test_carry_write_failure_is_distinguishable(moto, tmp_path):
    grading, _spec = moto
    blocked = tmp_path / "blocked"
    blocked.write_text("not a directory")  # HOME 指向文件：mkdir -p "$HOME/.rh2" 失败
    out = _bash(_localize(render_v2_candidate_install_script(grading), grading), tmp_path, blocked).stdout
    assert "\nRH2_PHASE_CARRY=start\n" in out and "\nRH2_PHASE_CARRY_FAILED=1\n" in out
    assert "\nRH2_PHASE_HANDOFF=1\n" not in out


def test_missing_carry_files_stop_the_test_exec_before_the_markers(moto, tmp_path):
    grading, spec = moto
    empty_home = tmp_path / "empty"
    empty_home.mkdir()
    out = _bash(_localize(render_v2_candidate_test_after_install_script(grading), grading), tmp_path, empty_home)
    assert "\nRH2_CARRY_MISSING=1\n" in out.stdout and _markers(out.stdout) == (False, False)
    assert spec.parse_log(out.stdout).num_parsed_tests == 0


def test_a_task_without_an_install_segment_renders_no_two_exec_scripts(moto, monkeypatch):
    """216 题目前都有安装段；没有安装段的来源（R2E 另走自己的 renderer）在受控供应下不需要网络，两段脚本为 None。"""
    from repoharness2.adapters.slime import prepared_task_face as face

    grading, _spec = moto
    monkeypatch.setattr(face, "derive_install_cmd", lambda *_a: None)
    assert face.render_v2_candidate_install_script(grading) is None
    assert face.render_v2_candidate_test_after_install_script(grading) is None
