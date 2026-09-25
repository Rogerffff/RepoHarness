"""R2E 评分脚本的真实容器往返（R2E 接线 R-c；fixture 镜像，@pytest.mark.docker）。

夹具镜像按 R2E 派生镜像的形状搭：`/testbed` 内嵌在镜像里（不是 clone）、初态不是干净树（已跟踪文件带未提交改动、
`.venv` 与 `run_tests.sh` 未跟踪）、环境本体 `.venv` 在工作目录里、隐藏测试只在 root 私有目录
`/rh2_private/r2e_tests`、入口是自定义 runner（形态同 pillow `3ac9396e`：自己打印 pytest 形状的摘要段——
夹具镜像里没有 pytest，也不为测试联网装）。期望映射里带一个 FAILED 键，所以 gold 的入口退出码是 1。

流程与 driver 相同：候选容器 → B1 census（政策 r2e_v1）→ census 之后的解释器预检 → 改动 → B2 导出 → 投影 →
FrozenDeltaSource → 正式 grader profile 的 fresh grader 评分。
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import pytest
from conftest import requires_docker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sandbox_test_support import make_grader_profile  # noqa: E402

from repoharness2.adapters.slime.baseline_census import generate_baseline_manifest  # noqa: E402
from repoharness2.adapters.slime.patch_exporter import export_frozen_patch  # noqa: E402
from repoharness2.adapters.slime.r2e_grading_scripts import build_r2e_grading_spec  # noqa: E402
from repoharness2.adapters.slime.replay_grade import DockerExecWorkspace  # noqa: E402
from repoharness2.contracts.baseline_manifest import BASELINE_MANIFEST_POLICY_R2E_V1  # noqa: E402
from repoharness2.contracts.frozen_patch import compute_frozen_patch_digest  # noqa: E402
from repoharness2.contracts.scoring_projection import classify_frozen_patch  # noqa: E402
from repoharness2.envpack.bundles_v2 import (  # noqa: E402
    PrivateGradingBundleR2E,
    R2EHiddenTestFile,
    r2e_hidden_tests_tree_digest,
)
from repoharness2.envpack.r2e_parsers import R2E_DATASET_REVISION  # noqa: E402
from repoharness2.grading.manager import (  # noqa: E402
    BaselineIntegrityError,
    FrozenDeltaSource,
    GradingManagerConfig,
    SWEGradingManager,
    run_docker,
)
from repoharness2.grading.trusted_projection import build_trusted_scoring_projection  # noqa: E402

pytestmark = [pytest.mark.docker, requires_docker]

R2E_FIXTURE_IMAGE = "rh2-r2e-grading-fixture:v1"
ENTRY = ".venv/bin/python -W ignore r2e_tests/runner.py"
EXPECTED = {"TestCore.test_feature_fixed": "PASSED", "TestCore.test_legacy_known_failure": "FAILED"}

RUNNER = '''"""fixture 隐藏测试：自定义 runner，自己打印 pytest 形状的摘要段。"""
import sys

sys.path.insert(0, "/testbed")
import pkg.core as core  # 候选把它改成语法错误 → 这里直接 traceback（零解析）

results = []


def case(name, fn):
    try:
        fn()
        results.append(("PASSED", name, ""))
    except Exception as exc:  # noqa: BLE001
        results.append(("FAILED", name, f" - {type(exc).__name__}: {exc}"))


def _fixed():
    assert core.feature() == "fixed", core.feature()


def _legacy():
    raise AssertionError("known failure in this environment")


case("TestCore::test_feature_fixed", _fixed)
case("TestCore::test_legacy_known_failure", _legacy)
print("=========================== short test summary info ============================")
for status, name, msg in results:
    print(f"{status} r2e_tests/test_1.py::{name}{msg}")
failed = sum(1 for status, _, _ in results if status != "PASSED")
print(f"=================== {failed} failed, {len(results) - failed} passed in 0.01s ===================")
sys.exit(1 if failed else 0)
'''
HIDDEN_FILES = {"__init__.py": "", "runner.py": RUNNER}

_DOCKERFILE = f"""\
FROM {{base}}
COPY r2e_tests /rh2_private/r2e_tests
RUN set -e; mkdir -p /testbed/pkg && cd /testbed && git init -q \\
 && printf 'def feature():\\n    return "broken"\\n' > pkg/core.py && : > pkg/__init__.py \\
 && git add -A && git commit -qm base \\
 && mkdir -p .venv/bin .venv/lib/fixturelib && ln -s "$(command -v python3)" .venv/bin/python \\
 && printf 'VALUE = 1\\n' > .venv/lib/fixturelib/__init__.py \\
 && printf '%s' '{ENTRY}' > run_tests.sh \\
 && printf 'COMPAT = 1\\n' >> pkg/__init__.py \\
 && chmod 700 /rh2_private
"""

SRC_FIXED = 'def feature():\n    return "fixed"\n'


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def r2e_image(fixture_image: str) -> tuple[str, str]:
    """(镜像名, 镜像内 /testbed 的 HEAD)。每个测试模块重建一次（内容由本文件决定，缓存层使重建很快）。"""

    with tempfile.TemporaryDirectory() as ctx:
        tests = Path(ctx) / "r2e_tests"
        tests.mkdir()
        for name, text in HIDDEN_FILES.items():
            (tests / name).write_text(text)
        (Path(ctx) / "Dockerfile").write_text(_DOCKERFILE.format(base=fixture_image))
        build = subprocess.run(["docker", "build", "-t", R2E_FIXTURE_IMAGE, ctx], capture_output=True, text=True, timeout=900)
    assert build.returncode == 0, build.stderr[-3000:]
    head = subprocess.run(
        ["docker", "run", "--rm", R2E_FIXTURE_IMAGE, "git", "-C", "/testbed", "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=120,
    )
    assert head.returncode == 0, head.stderr
    return R2E_FIXTURE_IMAGE, head.stdout.strip()


def _bundle(head: str, *, hidden: dict[str, str] | None = None) -> PrivateGradingBundleR2E:
    files = [R2EHiddenTestFile(path=n, sha256=_sha(t)) for n, t in sorted((hidden or HIDDEN_FILES).items())]
    expected = json.dumps(EXPECTED)
    return PrivateGradingBundleR2E(
        instance_id="fixture__" + "f" * 40, repo="fixture", repo_key_lower="fixture", base_commit=head,
        source_commit_hash="f" * 40, expected_output_json=expected, expected_output_json_sha256=_sha(expected),
        run_tests_sh=ENTRY, run_tests_sh_sha256=_sha(ENTRY), hidden_test_files=files,
        hidden_tests_tree_sha256=r2e_hidden_tests_tree_digest((f.path, f.sha256) for f in files),
        source_revision=R2E_DATASET_REVISION,
    )


def _spec(image: str, head: str, bundle: PrivateGradingBundleR2E):
    spec = build_r2e_grading_spec(
        task_id="r2e_gym_subset::" + bundle.instance_id, grading=bundle, image=image,
        image_manifest_digest="sha256:" + "0" * 64,
    )
    return dataclasses.replace(spec, image_manifest_digest=None, image_local_build=True)  # 本地构建的夹具镜像


async def _candidate_flow(image: str, head: str, task_id: str, mutate: str, *, before_census: str = ""):
    name = f"rh2-r2e-cand-{uuid.uuid4().hex[:8]}"
    run = await run_docker("run", "--detach", "--network", "none", "--name", name, image, "sleep", "infinity")
    assert run.exit_code == 0, run.stderr
    ws = DockerExecWorkspace(run_docker, name)
    try:
        if before_census:
            pre = await ws.run_bash(before_census)
            assert pre.exit_code == 0, pre.stderr
        baseline = await generate_baseline_manifest(
            ws, task_id=task_id, workdir="/testbed", public_bundle_digest="sha256:" + "e" * 64,
            runtime_image_digest="sha256:" + "1" * 64, materialized_head=head, task_base_commit=head,
            policy=BASELINE_MANIFEST_POLICY_R2E_V1,
        )
        # R2E 的解释器预检放在首次 census **之后**，且不写字节码（B 线 B1）
        preflight = await ws.run_bash("cd /testbed && .venv/bin/python -B -I -S -c pass && echo RH2_PREFLIGHT_OK")
        assert "RH2_PREFLIGHT_OK" in preflight.stdout, preflight.stderr
        changed = await ws.run_bash(mutate)
        assert changed.exit_code == 0, changed.stderr
        artifact = await export_frozen_patch(ws, baseline, rollout_execution_id="r2e", physical_attempt_id="r2e#p1-aaaa")
    finally:
        await run_docker("rm", "-f", name)
    return baseline, artifact


def _source(artifact, baseline, spec) -> FrozenDeltaSource:
    report, _ = classify_frozen_patch(artifact, baseline)
    assert report.verdict == "projectable", report
    projection, split = build_trusted_scoring_projection(artifact, spec.hygiene)
    assert split.unsupported_shape_reasons == ()
    return FrozenDeltaSource(
        frozen_patch=artifact, baseline_manifest=baseline, projection=projection,
        frozen_patch_digest=compute_frozen_patch_digest(artifact),
    )


def _manager(tmp_path: Path) -> SWEGradingManager:
    return SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs", sandbox_profile=make_grader_profile()))


def _eval_log(manager: SWEGradingManager, report) -> str:
    return (Path(manager.config.eval_log_dir) / f"{report.eval_log_ref.ref_id}.eval.log").read_text()


async def test_fix_resolves_even_though_the_entry_exits_nonzero_for_an_expected_failed_key(r2e_image, tmp_path):
    image, head = r2e_image
    bundle = _bundle(head)
    spec = _spec(image, head, bundle)
    baseline, artifact = await _candidate_flow(
        image, head, spec.task_id, f"cd /testbed && cat > pkg/core.py <<'EOF'\n{SRC_FIXED}EOF\n")
    assert baseline.policy.policy_version == "baseline_policy_r2e_v1"
    # 初态不是干净树：未提交的兼容补丁与未跟踪的入口都在基线里；.venv 整个在排除区
    paths = {e.path for e in baseline.entries}
    assert {"pkg/__init__.py", "pkg/core.py", "run_tests.sh"} <= paths and not any(p.startswith(".venv/") for p in paths)
    assert [(e.path, e.operation) for e in artifact.entries] == [("pkg/core.py", "modify")]

    manager = _manager(tmp_path)
    report = await manager.grade(trajectory_id="r2e-fix", workspace=None, spec=spec, frozen_delta=_source(artifact, baseline, spec))
    assert (report.outcome, report.reward, report.grading_semantics) == ("resolved", 1.0, "r2e_expected_map"), report.infra_failure_detail
    assert (report.expected_match_count, report.expected_total_count, report.f2p_total_count) == (2, 2, None)
    log = _eval_log(manager, report)
    assert "RH2_SETUP_OK=1" in log and "RH2_INSTALL_SKIPPED=1" in log and "RH2_TEST_RC=1" in log
    assert f"RH2_SETUP_HIDDEN_TESTS_TREE={bundle.hidden_tests_tree_sha256.removeprefix('sha256:')}" in log
    # 隐藏测试的私有位置对沙箱身份不可读
    peek = subprocess.run(
        ["docker", "run", "--rm", "--user", "54322:54322", image, "sh", "-c", "ls /rh2_private/r2e_tests"],
        capture_output=True, text=True, timeout=120,
    )
    assert peek.returncode != 0 and "runner.py" not in peek.stdout


async def test_tampered_entry_and_planted_tests_are_overwritten_so_noop_stays_a_source_rule_zero(r2e_image, tmp_path):
    image, head = r2e_image
    spec = _spec(image, head, _bundle(head))
    forged = "print('short test summary info'); print('PASSED r2e_tests/test_1.py::TestCore::test_feature_fixed'); print('FAILED r2e_tests/test_1.py::TestCore::test_legacy_known_failure - x')"
    mutate = (
        "cd /testbed && printf '%s' 'echo forged-entry' > run_tests.sh && mkdir -p r2e_tests"
        f" && cat > r2e_tests/runner.py <<'EOF'\n{forged}\nEOF\n"
        "printf 'raise SystemExit(0)\\n' > r2e_tests/conftest.py\n"
    )
    baseline, artifact = await _candidate_flow(image, head, spec.task_id, mutate)
    assert [(e.path, e.operation) for e in artifact.entries] == [
        ("r2e_tests/conftest.py", "add"), ("r2e_tests/runner.py", "add"), ("run_tests.sh", "modify")]
    source = _source(artifact, baseline, spec)
    # official 清单内的路径（入口、隐藏测试同名文件）不重放；清单外的 r2e_tests/conftest.py 会被重放，随后被可信 setup 清掉
    assert source.projection.included_entry_paths == ("r2e_tests/conftest.py",)

    manager = _manager(tmp_path)
    report = await manager.grade(trajectory_id="r2e-tamper", workspace=None, spec=spec, frozen_delta=source)
    assert (report.outcome, report.failure_category, report.reward) == ("unresolved", "tests_failed", 0.0), report.infra_failure_detail
    assert (report.expected_match_count, report.expected_total_count) == (1, 2)
    log = _eval_log(manager, report)
    assert "forged-entry" not in log and "RH2_SETUP_OK=1" in log
    assert "FAILED r2e_tests/test_1.py::TestCore::test_feature_fixed - AssertionError: broken" in log  # 真 runner 跑的


async def test_hidden_tests_drift_is_infra_and_the_candidate_segment_never_starts(r2e_image, tmp_path):
    image, head = r2e_image
    drifted = _bundle(head, hidden={**HIDDEN_FILES, "runner.py": RUNNER + "# bundle 记录的内容与镜像里的不同\n"})
    spec = _spec(image, head, drifted)
    baseline, artifact = await _candidate_flow(
        image, head, spec.task_id, f"cd /testbed && cat > pkg/core.py <<'EOF'\n{SRC_FIXED}EOF\n")
    manager = _manager(tmp_path)
    report = await manager.grade(trajectory_id="r2e-drift", workspace=None, spec=spec, frozen_delta=_source(artifact, baseline, spec))
    assert (report.outcome, report.reward, report.grading_semantics) == ("failed_to_grade", None, "r2e_expected_map")
    log = _eval_log(manager, report)
    assert "RH2_SETUP_ERROR=hidden_tests_tree_mismatch:" in log
    assert "RH2_SETUP_OK=1" not in log and ">>>>> Start Test Output" not in log


async def test_python_prewarm_before_the_first_census_breaks_the_baseline_rebuild(r2e_image, tmp_path):
    """B 线 B1 的边界：`.venv/` 在排除区，但排除区的**路径清单**仍进基线身份。首次 census 之前用解释器 import 过
    `.venv` 里的包 → `.venv/**/__pycache__/*.pyc` 进了候选侧基线 → fresh grader 重建的基线没有这些路径 → 停批。
    （census 之后、带 `-B` 的预检不受影响——前三个用例的流程里都有它。）"""

    image, head = r2e_image
    spec = _spec(image, head, _bundle(head))
    prewarm = "cd /testbed && PYTHONPATH=/testbed/.venv/lib .venv/bin/python -c 'import fixturelib' && ls .venv/lib/fixturelib/__pycache__"
    baseline, artifact = await _candidate_flow(
        image, head, spec.task_id, f"cd /testbed && cat > pkg/core.py <<'EOF'\n{SRC_FIXED}EOF\n", before_census=prewarm)
    manager = _manager(tmp_path)
    with pytest.raises(BaselineIntegrityError) as halted:
        await manager.grade(trajectory_id="r2e-prewarm", workspace=None, spec=spec, frozen_delta=_source(artifact, baseline, spec))
    # 普通条目数相同（3 == 3），摘要却不同：差别只在排除区的路径清单摘要
    assert "baseline_digest_mismatch" in str(halted.value)
    assert "rebuilt_entries=3, baseline_entries=3" in str(halted.value)
    await manager.close()
