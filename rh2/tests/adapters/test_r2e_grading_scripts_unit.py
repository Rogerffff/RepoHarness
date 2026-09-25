"""R2E 评分脚本渲染与 spec 分派（R2E 接线 R-c；无 docker）。真实容器里的行为见 tests/grading/test_r2e_docker.py。"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest

from repoharness2.adapters.slime import r2e_grading_scripts as r2e_scripts
from repoharness2.adapters.slime.baseline_census import baseline_policy_for_task_id, build_census_script
from repoharness2.adapters.slime.prepared_task_face import (
    GradingMaterialsError,
    build_grading_spec_from_host_view,
)
from repoharness2.contracts.baseline_manifest import (
    BASELINE_MANIFEST_POLICY_R2E_V1,
    BASELINE_MANIFEST_POLICY_V1,
    BASELINE_MANIFEST_POLICY_V2,
    compute_policy_digest,
)
from repoharness2.envpack.bundles_v2 import (
    PrivateGradingBundleR2E,
    R2EHiddenTestFile,
    r2e_hidden_tests_tree_digest,
)
from repoharness2.envpack.r2e_parsers import R2E_DATASET_REVISION, R2E_GRADER_VERSION_TAG
from repoharness2.envpack.training_view import TrustedTaskController
from repoharness2.grading.manager import grading_scripts_digest, render_compile_probe_script

REPO_ROOT = Path(__file__).resolve().parents[3]
ENTRY = "PYTHONWARNINGS='ignore::UserWarning' .venv/bin/python -W ignore -m pytest -rA r2e_tests"


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _bundle(repo: str = "pillow") -> PrivateGradingBundleR2E:
    expected = json.dumps({"T.a": "PASSED"})
    files = [R2EHiddenTestFile(path="test_1.py", sha256=_sha("t")), R2EHiddenTestFile(path="conftest.py", sha256=_sha("c"))]
    return PrivateGradingBundleR2E(
        instance_id=f"{repo}__" + "a" * 40, repo=repo, repo_key_lower=repo, base_commit="b" * 40,
        source_commit_hash="a" * 40, expected_output_json=expected, expected_output_json_sha256=_sha(expected),
        run_tests_sh=ENTRY, run_tests_sh_sha256=_sha(ENTRY), hidden_test_files=files,
        hidden_tests_tree_sha256=r2e_hidden_tests_tree_digest((f.path, f.sha256) for f in files),
        source_revision=R2E_DATASET_REVISION,
    )


def test_trusted_setup_sets_the_success_state_only_after_every_check():
    g = _bundle()
    lines = r2e_scripts.render_r2e_trusted_setup_script(g).splitlines()

    def _at(needle: str) -> int:
        hits = [i for i, ln in enumerate(lines) if needle in ln]
        assert hits, needle
        return hits[0]

    order = [
        _at("rm -rf /testbed/r2e_tests"),
        _at("cp -r /rh2_private/r2e_tests /testbed/r2e_tests"),
        _at("base64 -d > /testbed/run_tests.sh"),
        _at("hidden_tests_tree_mismatch"),
        _at("run_tests_sh_mismatch"),
        _at("RH2_APPLY_RC=0"),
        _at("RH2_ATTEST="),
        _at("RH2_SETUP_OK=1"),
    ]
    assert order == sorted(order)  # B 线 B3：复制、重写、摘要核验全过之后才置成功状态，再进自证尾段
    assert lines.count("RH2_APPLY_RC=0") == 1
    assert g.hidden_tests_tree_sha256.removeprefix("sha256:") in "\n".join(lines)
    # 入口按 bundle 逐字节重写（原文没有行尾换行，heredoc 会多出一个）
    b64 = [ln for ln in lines if "base64 -d" in ln][0].split("'%s' ")[1].split(" |")[0]
    assert base64.b64decode(b64).decode("utf-8") == ENTRY
    # 不做任何会破坏 R2E 初态（未提交的兼容补丁、未跟踪的 .venv / run_tests.sh）的 git 操作
    assert not any(tok in ln for ln in lines for tok in ("git reset", "git checkout", "git clean", "git stash"))


def test_candidate_segment_has_no_install_and_runs_the_source_entry_verbatim():
    script = r2e_scripts.render_r2e_candidate_test_script(_bundle())
    lines = script.splitlines()
    assert "echo RH2_INSTALL_SKIPPED=1" in lines and "RH2_PHASE_START=install" not in script
    start, run, rc, end = (lines.index(x) for x in (
        "echo '>>>>> Start Test Output'", "bash run_tests.sh", "RH2_TEST_RC=$?", "echo '>>>>> End Test Output'"))
    assert start < run < rc < end < lines.index('echo "RH2_TEST_RC=$RH2_TEST_RC"')
    assert "pytest" not in script and "-q" not in script  # 入口命令不内嵌、不改写


def test_official_files_are_the_hidden_tests_plus_the_entry_and_feed_hygiene():
    g = _bundle()
    assert r2e_scripts.r2e_official_files(g) == ("r2e_tests/conftest.py", "r2e_tests/test_1.py", "run_tests.sh")
    spec = r2e_scripts.build_r2e_grading_spec(
        task_id="r2e_gym_subset::" + g.instance_id, grading=g, image="img", image_manifest_digest="sha256:" + "1" * 64)
    assert spec.hygiene.test_files == r2e_scripts.r2e_official_files(g) and spec.hygiene.test_globs == ()
    assert (spec.grading_semantics, spec.grader_version, spec.checkout_mode) == (
        "r2e_expected_map", R2E_GRADER_VERSION_TAG, "image_embedded")
    verdict = spec.parse_log(">>>>> Start Test Output\nshort test summary info\nPASSED r2e_tests/t.py::T::a\n>>>>> End Test Output\n")
    assert verdict.resolved and verdict.grading_semantics == "r2e_expected_map"
    # 资格键用的脚本摘要随入口 / 隐藏测试变化（同镜像、不同材料不得沿用旧资格）
    other = _bundle().model_copy(update={"run_tests_sh": "x", "run_tests_sh_sha256": _sha("x")})
    other_spec = r2e_scripts.build_r2e_grading_spec(
        task_id=spec.task_id, grading=other, image="img", image_manifest_digest="sha256:" + "1" * 64)
    assert grading_scripts_digest(spec) != grading_scripts_digest(other_spec)


def test_observation_and_compile_probe_name_the_venv_interpreter():
    g = _bundle()
    pre = r2e_scripts.render_r2e_pre_candidate_observation_script(g)
    post = r2e_scripts.render_r2e_post_candidate_observation_script(g)
    assert "/testbed/.venv/bin/python -B - <<'RH2_OBS_EOF'" in pre and "RH2_OBS_RUNNER_DIGEST" in pre
    assert "import PIL, sys" in post and "/testbed/.venv/bin/python -B -c" in post
    assert "conda" not in pre + post
    probe = r2e_scripts.render_r2e_compile_probe_script(["PIL/Image.py", "README.md"])
    assert "/testbed/.venv/bin/python -I -S - <<'RH2_COMPILE_EOF'" in probe and "paths = ['PIL/Image.py']" in probe
    # SWE 的缺省渲染逐字节不变（环境资格记录的脚本摘要依赖它）
    assert "\npython -I -S - <<'RH2_COMPILE_EOF'\n" in render_compile_probe_script(["a.py"])


def test_import_probe_modules_match_the_real_image_facts():
    facts = json.loads((REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/raw/r2e_image_facts_m3_48.json").read_text())
    for task in facts["tasks"]:
        module = r2e_scripts._R2E_IMPORT_PROBE_MODULES[task["repo"]]
        assert task["venv"]["pkg_file"].startswith(f"/testbed/{module}/") or f"/{module}/" in task["venv"]["pkg_file"], task["repo"]


def test_r2e_baseline_policy_is_a_new_version_and_excludes_the_venv():
    assert baseline_policy_for_task_id("r2e_gym_subset::x") is BASELINE_MANIFEST_POLICY_R2E_V1
    assert baseline_policy_for_task_id("swe_gym_lite::x") is BASELINE_MANIFEST_POLICY_V2
    assert baseline_policy_for_task_id("other::x") is BASELINE_MANIFEST_POLICY_V1
    assert BASELINE_MANIFEST_POLICY_R2E_V1.excluded_namespaces == (".git/", ".harness/", ".venv/")
    # 旧政策的摘要不变（既有 manifest / 证据不受影响）。两个值由 cee933b4（本片改动之前）的代码算出。
    assert compute_policy_digest(BASELINE_MANIFEST_POLICY_V1) == "sha256:a3584df757b3e79b3a3074324e2395f283d7a78334b6932d5e986497771fccb8"
    assert compute_policy_digest(BASELINE_MANIFEST_POLICY_V2) == "sha256:77527b33576220ebe06770f4372eeb400fa5b07d0e1f0aa65804373c37866c27"
    digests = {compute_policy_digest(p) for p in (
        BASELINE_MANIFEST_POLICY_V1, BASELINE_MANIFEST_POLICY_V2, BASELINE_MANIFEST_POLICY_R2E_V1)}
    assert len(digests) == 3
    script = build_census_script("/testbed", BASELINE_MANIFEST_POLICY_R2E_V1)
    assert "-path './.venv' -prune" in script
    assert "find './.venv' -type f -print" in script  # B 线 B1：排除区的路径清单仍进 manifest 身份


def test_real_view_dispatches_to_the_r2e_builder_and_unknown_bundle_types_are_rejected():
    controller = TrustedTaskController.from_repo_root(REPO_ROOT, sources=("r2e_gym_subset",))
    tid = next(t for t in controller.task_ids() if "orange3__" in t)
    rv = controller.rollout_view(tid)
    gv = controller.grading_view(tid, environment_package_digest=rv.environment_package_digest)
    spec = build_grading_spec_from_host_view(
        gv, image=rv.public.image, image_manifest_digest=rv.public.image_manifest_digest)
    assert spec.grading_semantics == "r2e_expected_map" and spec.task_id == tid
    entry_b64 = base64.b64encode(gv.grading.run_tests_sh.encode()).decode()
    assert "xvfb-run" in gv.grading.run_tests_sh and entry_b64 in spec.trusted_setup_script

    class _Alien:
        task_id = "x::y"
        grading = object()

    with pytest.raises(GradingMaterialsError, match="grading_bundle_type_unknown"):
        build_grading_spec_from_host_view(_Alien(), image="i", image_manifest_digest="sha256:" + "0" * 64)
