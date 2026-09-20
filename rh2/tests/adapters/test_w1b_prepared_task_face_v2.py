"""S1-c（评分接线 2026-09-15）：v2 评分脚本渲染——阶段顺序、命令、标记与退出码事实（不做整段文本快照）。

对照物：216 题的官方测试行契约（B_materials/official_cmd_contract_216.json）与 vendor JSON 的 install/eval_commands。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repoharness2.adapters.slime.prepared_task_face import (
    V2_EVAL_END_MARKER,
    V2_EVAL_START_MARKER,
    render_v2_candidate_test_script,
    render_v2_eval_script,
    render_v2_trusted_setup_script,
)
from repoharness2.envpack.bundles_v2 import PrivateGradingBundleV2
from repoharness2.envpack.spec_vendor import (
    SPEC_VENDOR_ID_SWEGYM_242429C1,
    derive_eval_cmd,
    derive_install_cmd,
    derive_test_command,
)
from repoharness2.grading.manager import patch_touched_paths

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams"
CONTRACT_216 = REPO_ROOT / "rh2/tests/envpack/data/official_cmd_contract_216.json"
GRADING_BUNDLES_V2 = DOCS / "s2/ingest/grading_bundles_v2_v0.jsonl"


def _bundle(row: dict) -> PrivateGradingBundleV2:
    return PrivateGradingBundleV2(**{k: v for k, v in row.items() if k != "schema_id"})


@pytest.fixture(scope="module")
def bundles() -> dict[str, PrivateGradingBundleV2]:
    rows = [json.loads(l) for l in GRADING_BUNDLES_V2.read_text().splitlines() if l.strip()]
    return {r["instance_id"]: _bundle(r) for r in rows}


@pytest.fixture(scope="module")
def contract() -> dict[str, dict]:
    return {r["instance_id"]: r for r in json.loads(CONTRACT_216.read_text())}


def _lines(script: str) -> list[str]:
    return script.splitlines()


def _index(lines: list[str], needle: str) -> int:
    hits = [i for i, l in enumerate(lines) if l == needle]
    assert len(hits) == 1, f"{needle!r} 应恰好出现一次，实际 {len(hits)}"
    return hits[0]


@pytest.mark.parametrize("iid", ["getmoto__moto-4847", "conan-io__conan-13326", "python__mypy-12741", "pandas-dev__pandas-48106", "pydantic__pydantic-8500"])
def test_candidate_script_phase_order_and_commands(bundles, contract, iid):
    g = bundles[iid]
    test_files = tuple(sorted(patch_touched_paths(g.test_patch)))
    lines = _lines(render_v2_candidate_test_script(g, test_files))
    install = derive_install_cmd(g.spec_vendor_id, g.repo_key_lower, g.version)
    assert install is not None
    i_env = _index(lines, "cd /testbed")
    i_ps = _index(lines, "echo RH2_PHASE_START=install")
    i_install = _index(lines, install)
    i_rc = _index(lines, "RH2_INSTALL_RC=$?")
    i_rc_echo = _index(lines, 'echo "RH2_INSTALL_RC=$RH2_INSTALL_RC"')
    i_pe = _index(lines, "echo RH2_PHASE_END=install")
    i_start = _index(lines, f": '{V2_EVAL_START_MARKER}'")
    i_cmd = _index(lines, contract[iid]["official_test_line"])
    i_end = _index(lines, f": '{V2_EVAL_END_MARKER}'")
    i_trc = _index(lines, "RH2_TEST_RC=$?")
    i_trc_echo = _index(lines, 'echo "RH2_TEST_RC=$RH2_TEST_RC"')
    assert i_env < i_ps < i_install < i_rc < i_rc_echo < i_pe < i_start < i_cmd < i_trc < i_end < i_trc_echo
    # 候选段不做任何恢复/注入（那是 root 可信 setup 的事），也没有 reset
    assert not any(l.startswith("git checkout") or l.startswith("git apply") for l in lines)
    # 测试命令只在标记之间出现一次，且是官方行（含 mypy `-k`、资源文件剔除）
    assert lines[i_start + 1] == contract[iid]["official_test_line"]
    if g.repo_key_lower == "conan-io/conan":
        i_evc = _index(lines, "export PYTHONPATH=${PYTHONPATH:-}:$(pwd)")
        assert i_env < i_evc < i_ps


def test_trusted_setup_keeps_full_restore_list_and_vendor_env(bundles):
    g = bundles["getmoto__moto-4847"]  # test_patch 含 .txt 资源文件：选择器剔除，恢复/保护清单保留
    test_files = tuple(sorted(patch_touched_paths(g.test_patch)))
    assert any(f.endswith(".txt") for f in test_files)
    setup = render_v2_trusted_setup_script(g, test_files)
    for f in test_files:
        assert f in setup
    assert "RH2_PHASE_START=install" not in setup and V2_EVAL_START_MARKER not in setup
    conan = bundles["conan-io__conan-13326"]
    conan_files = tuple(sorted(patch_touched_paths(conan.test_patch)))
    assert "export PYTHONPATH=${PYTHONPATH:-}:$(pwd)" in render_v2_trusted_setup_script(conan, conan_files)


def test_legacy_full_script_is_same_line_group(bundles):
    g = bundles["python__mypy-12741"]
    test_files = tuple(sorted(patch_touched_paths(g.test_patch)))
    full = _lines(render_v2_eval_script(g, test_files))
    cand = _lines(render_v2_candidate_test_script(g, test_files))
    # 候选段的每一行（去掉共享的环境前导）都在完整脚本里，顺序一致
    env_prefix = 6
    tail = cand[env_prefix:]
    pos = [full.index(l) for l in tail]
    assert pos == sorted(pos)
    assert full[-1].startswith("git checkout ")  # 官方收尾 reset


def test_all_216_candidate_scripts_carry_official_test_line_and_install(bundles, contract):
    bad = []
    for iid, g in bundles.items():
        files = tuple(sorted(patch_touched_paths(g.test_patch)))
        lines = _lines(render_v2_candidate_test_script(g, files))
        official = contract[iid]["official_test_line"]
        install = derive_install_cmd(g.spec_vendor_id, g.repo_key_lower, g.version)
        if lines.count(official) != 1 or lines.count(install) != 1:
            bad.append(iid)
        assert derive_test_command(g.spec_vendor_id, g.repo_key_lower, g.version, g.test_patch) == official
        assert derive_eval_cmd(g.spec_vendor_id, g.repo_key_lower, g.version) == g.eval_cmd
    assert bad == []


def test_spec_from_host_view_binds_v2_parser_and_versions(bundles):
    from repoharness2.adapters.slime.prepared_task_face import build_grading_spec_from_host_view
    from repoharness2.envpack.swegym_parsers import SWEGYM_PARSERS_VERSION_TAG
    from repoharness2.envpack.training_view import HostGradingView

    g = bundles["getmoto__moto-6913"]
    view = HostGradingView(
        task_id=f"swe_gym_lite::{g.instance_id}", source="swe_gym_lite", instance_id=g.instance_id,
        environment_package_digest="sha256:" + "0" * 64, grading_bundle_digest=g.digest(), grading=g,
    )
    spec = build_grading_spec_from_host_view(view, image="img:tag", image_manifest_digest="sha256:" + "1" * 64)
    assert spec.grader_version.endswith("+" + SWEGYM_PARSERS_VERSION_TAG)
    log = f"x\n+ : '{V2_EVAL_START_MARKER}'\n" + "".join(f"PASSED {t}\n" for t in [*g.fail_to_pass, *g.pass_to_pass]) + f"+ : '{V2_EVAL_END_MARKER}'\n"
    verdict = spec.parse_log(log)
    assert verdict.resolved and verdict.parser_source == SWEGYM_PARSERS_VERSION_TAG
    assert "RH2_PHASE_START=install" in spec.candidate_test_script and V2_EVAL_START_MARKER in spec.candidate_test_script
    assert SPEC_VENDOR_ID_SWEGYM_242429C1 == g.spec_vendor_id


# ---- 第四组 P-B（2026-09-16）：SWE spec 构造入口不再注入测试名通配；观测另行记录 ----

def test_pb_swe_spec_entries_have_no_test_globs(bundles):
    from repoharness2.adapters.slime.prepared_task_face import build_grading_spec_from_host_view
    from repoharness2.envpack.training_view import HostGradingView
    from repoharness2.grading.manager import observe_candidate_paths
    from repoharness2.grading.trusted_projection import classify_control_plane_path

    g = bundles["pandas-dev__pandas-48106"]
    view = HostGradingView(
        task_id=f"swe_gym_lite::{g.instance_id}", source="swe_gym_lite", instance_id=g.instance_id,
        environment_package_digest="sha256:" + "0" * 64, grading_bundle_digest=g.digest(), grading=g,
    )
    spec = build_grading_spec_from_host_view(view, image="img:tag", image_manifest_digest="sha256:" + "1" * 64)
    assert spec.hygiene.test_globs == ()
    rules = spec.hygiene
    assert classify_control_plane_path(rules, "pandas/_testing/_io.py") is None  # 合法源码：重放
    assert classify_control_plane_path(rules, "pandas/tests/series/indexing/test_setitem.py") is None  # 候选写的测试：重放（观测）
    assert classify_control_plane_path(rules, "pandas/tests/indexing/test_loc.py") == "official_test_file"  # official 精确文件仍是控制面
    assert classify_control_plane_path(rules, ".rh2_marker") == "reserved_namespace"
    obs = observe_candidate_paths(["pandas/_testing/_io.py", "pandas/tests/conftest.py", "src/x.py", "pyproject.toml"])
    assert obs == {
        "candidate_test_like_paths": ["pandas/_testing/_io.py", "pandas/tests/conftest.py"],
        "candidate_touched_conftest_or_fixture": ["pandas/tests/conftest.py", "pyproject.toml"],
    }


# ---- 第四组 P-A（2026-09-16）：v2 spec 带编译复证渲染器与资格记录 ----


def test_pa_v2_spec_carries_compile_probe_renderer_and_qualification(bundles):
    import dataclasses

    from repoharness2.adapters.slime.prepared_task_face import build_grading_spec_from_host_view, render_v2_compile_probe_script
    from repoharness2.envpack.training_view import HostGradingView
    from repoharness2.grading.manager import EnvQualification, env_qualification_status, grading_image_identity, grading_scripts_digest

    g = bundles["getmoto__moto-6913"]
    view = HostGradingView(
        task_id=f"swe_gym_lite::{g.instance_id}", source="swe_gym_lite", instance_id=g.instance_id,
        environment_package_digest="sha256:" + "0" * 64, grading_bundle_digest=g.digest(), grading=g,
    )
    spec = build_grading_spec_from_host_view(view, image="img:tag", image_manifest_digest="sha256:" + "1" * 64)
    assert spec.env_qualification is None and env_qualification_status(spec) == (False, "absent")
    script = spec.render_compile_probe(["moto/core/models.py", "README.md"])
    assert script == render_v2_compile_probe_script(["moto/core/models.py", "README.md"])
    assert "conda activate testbed" in script and "RH2_COMPILE_EOF" in script
    assert "moto/core/models.py" in script and "README.md" not in script  # 非 .py 不进脚本
    q = EnvQualification(image_identity=grading_image_identity(spec), scripts_digest=grading_scripts_digest(spec),
                         reference_missing_count=0, source="ledger:rpt", qualified_at_utc="2026-09-16T00:00:00Z")
    spec_q = build_grading_spec_from_host_view(view, image="img:tag", image_manifest_digest="sha256:" + "1" * 64, env_qualification=q)
    assert env_qualification_status(spec_q) == (True, "ok:ledger:rpt")
    # 派生镜像（image_local_build）改变镜像身份 → 原镜像的资格不再有效
    derived = dataclasses.replace(spec_q, image="local/derived:x", image_manifest_digest=None, image_local_build=True)
    assert env_qualification_status(derived) == (False, "image_identity_mismatch")
    assert grading_image_identity(derived) == "local_build:local/derived:x"


def test_install_segment_err_trap_records_failed_commands_and_keeps_last_rc(bundles, tmp_path):
    """2026-09-19（B 线 216 题诊断 / F4）：安装段每条失败命令打 `RH2_INSTALL_CMD_FAILED=<rc> <cmd>`，段末 `RH2_INSTALL_RC`
    仍是最后一条命令的退出码（bash 在 ERR trap 后恢复 $?）。真实 bash 对照 + 渲染器断言。"""
    import subprocess

    from repoharness2.adapters.slime.prepared_task_face import _v2_install_lines
    from repoharness2.grading.manager import candidate_facts_from_log

    g = bundles["getmoto__moto-6913"]
    lines = _v2_install_lines(g)
    assert lines[2].startswith("set -E; trap ") and "RH2_INSTALL_CMD_FAILED=$? ${BASH_COMMAND}" in lines[2]
    assert lines[3] == "make init" and lines[4] == "RH2_INSTALL_RC=$?" and lines[5] == "trap - ERR; set +E"
    # 同一组行、把安装串换成"两条失败 + 一条成功"的对照，真 bash 执行
    fake = [ln if ln != "make init" else "false; ls /nonexistent-rh2 2>/dev/null; (exit 4); (exit 9) && true; echo tail_ok" for ln in lines]
    out = subprocess.run(["bash", "-c", "set -xo pipefail\n" + "\n".join(fake)], capture_output=True, text=True, timeout=60)
    facts = candidate_facts_from_log(out.stdout)
    assert facts["install_rc_last_command"] == 0  # 最后一条 echo 成功
    assert [f["rc"] for f in facts["install_failed_commands"]] == [1, 1, 4]  # `(exit 9) && true`：&& 列表非末项失败不触发 ERR（bash 规则）
    assert facts["install_failed_commands"][0]["cmd"] == "false" and facts["install_failed_commands"][2]["cmd"].startswith("( exit 4 )")
    assert "RH2_INSTALL_CMD_FAILED" not in "".join(ln for ln in out.stdout.splitlines()[-3:])  # 段后 trap 已清

