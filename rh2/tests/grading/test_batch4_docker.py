"""第四组 P-D / P-C 的真实容器往返（fixture 镜像，@pytest.mark.docker）。

流程与 driver 相同：候选容器（fixture 镜像 + 只读快照）clone → B1 census → 改动 → B2 导出 → 分类 → 投影 →
FrozenDeltaSource → 正式 grader profile 的 fresh grader（clone 模式）评分。
- P-D：基线普通文件 `config` 变成目录 `config/default.json`，重放成功、评分正常；
- P-C：政策 v2 下 `__pycache__/`、`.pytest_cache/` 目录被整体省略且计数，同名普通文件与软链仍导出。
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import pytest
from conftest import requires_docker
from grading_fixtures import (
    FIXTURE_INSTANCE_ID,
    SRC_FIXED,
    FixtureRepo,
    build_fixture_repo,
    git_in,
    make_candidate_test_script,
    make_fixture_spec,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sandbox_test_support import make_grader_profile  # noqa: E402

from repoharness2.adapters.slime.baseline_census import generate_baseline_manifest  # noqa: E402
from repoharness2.adapters.slime.patch_exporter import export_frozen_patch  # noqa: E402
from repoharness2.adapters.slime.replay_grade import DockerExecWorkspace  # noqa: E402
from repoharness2.contracts.baseline_manifest import BASELINE_MANIFEST_POLICY_V1, BASELINE_MANIFEST_POLICY_V2  # noqa: E402
from repoharness2.contracts.frozen_patch import compute_frozen_patch_digest  # noqa: E402
from repoharness2.contracts.scoring_projection import classify_frozen_patch  # noqa: E402
from repoharness2.grading.manager import (  # noqa: E402
    FrozenDeltaSource,
    GradingManagerConfig,
    SWEGradingManager,
    run_docker,
)
from repoharness2.grading.trusted_projection import build_trusted_scoring_projection  # noqa: E402

pytestmark = [pytest.mark.docker, requires_docker]


async def _candidate_flow(image: str, repo: FixtureRepo, mutate_script: str, policy):
    name = f"rh2-b4-cand-{uuid.uuid4().hex[:8]}"
    run = await run_docker("run", "--detach", "--network", "none", "-v", f"{repo.path}:/rh2/snapshot:ro", "--name", name, image, "sleep", "infinity")
    assert run.exit_code == 0, run.stderr
    ws = DockerExecWorkspace(run_docker, name)
    sink_b: dict[str, int] = {}
    sink_p: dict[str, int] = {}
    try:
        r = await ws.run_bash("git clone -q /rh2/snapshot /testbed && git -C /testbed rev-parse HEAD")
        assert r.exit_code == 0, r.stderr
        head = r.stdout.strip()
        baseline = await generate_baseline_manifest(
            ws, task_id=FIXTURE_INSTANCE_ID, workdir="/testbed", public_bundle_digest="sha256:" + "e" * 64,
            runtime_image_digest="sha256:" + "1" * 64, materialized_head=head, task_base_commit=repo.base_commit,
            policy=policy, omitted_sink=sink_b,
        )
        m = await ws.run_bash(mutate_script)
        assert m.exit_code == 0, m.stderr
        artifact = await export_frozen_patch(ws, baseline, rollout_execution_id="b4", physical_attempt_id="b4#p1-aaaa", omitted_sink=sink_p)
    finally:
        await run_docker("rm", "-f", name)
    return baseline, artifact, sink_b, sink_p


def _grade_manager(tmp_path: Path) -> SWEGradingManager:
    return SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs", sandbox_profile=make_grader_profile()))


def _eval_log(manager, report) -> str:
    return (Path(manager.config.eval_log_dir) / f"{report.eval_log_ref.ref_id}.eval.log").read_text()


async def test_pd_file_to_dir_round_trip_grades_normally(fixture_image, tmp_path):
    repo0 = build_fixture_repo(tmp_path / "repo")
    (repo0.path / "config").write_text("a=1\n")
    git_in(repo0.path, "add", "config")
    git_in(repo0.path, "commit", "-qm", "add config")
    repo = FixtureRepo(path=repo0.path, base_commit=git_in(repo0.path, "rev-parse", "HEAD").strip())
    mutate = (
        "cd /testbed && rm config && mkdir config && printf '{}\\n' > config/default.json && "
        f"cat > src/thing.py <<'EOF'\n{SRC_FIXED}EOF\n"
    )
    baseline, artifact, _, _ = await _candidate_flow(fixture_image, repo, mutate, BASELINE_MANIFEST_POLICY_V1)
    assert [(e.path, e.operation) for e in artifact.entries] == [("config", "delete"), ("config/default.json", "add"), ("src/thing.py", "modify")]
    report, _ = classify_frozen_patch(artifact, baseline)
    assert report.verdict == "projectable"
    prelude = "test -d /testbed/config && test -f /testbed/config/default.json && echo RH2_CONFIG_DIR_OK || echo RH2_CONFIG_DIR_MISSING\n"
    spec = make_fixture_spec(repo.base_commit, fixture_image, snapshot_host_path=str(repo.path), candidate_test_script=make_candidate_test_script(extra_prelude=prelude))
    projection, split = build_trusted_scoring_projection(artifact, spec.hygiene)
    assert split.unsupported_shape_reasons == () and projection.included_entry_paths == ("config", "config/default.json", "src/thing.py")
    source = FrozenDeltaSource(frozen_patch=artifact, baseline_manifest=baseline, projection=projection, frozen_patch_digest=compute_frozen_patch_digest(artifact))
    manager = _grade_manager(tmp_path)
    graded = await manager.grade(trajectory_id="b4-pd", workspace=None, spec=spec, frozen_delta=source)
    assert graded.outcome == "resolved" and graded.reward == 1.0, graded.infra_failure_detail
    log = _eval_log(manager, graded)
    assert "RH2_CONFIG_DIR_OK" in log  # fresh grader 里：普通文件 config 已删、目录 config/default.json 已建


async def test_pc_cache_dirs_omitted_by_type_and_counted(fixture_repo, fixture_image, tmp_path):
    mutate = (
        "cd /testbed && mkdir -p src/__pycache__ && echo x > src/__pycache__/thing.cpython-312.pyc && "
        "mkdir -p .pytest_cache/v && echo y > .pytest_cache/v/x && echo z > tests/__pycache__ && ln -s thing.py src/.pytest_cache"
    )
    baseline, artifact, sink_b, sink_p = await _candidate_flow(fixture_image, fixture_repo, mutate, BASELINE_MANIFEST_POLICY_V2)
    assert baseline.policy.policy_version == "baseline_policy_v2" and sink_b == {"dirs": 0, "files": 0}
    assert sink_p == {"dirs": 2, "files": 2}
    assert [(e.path, e.operation, e.object_type) for e in artifact.entries] == [("src/.pytest_cache", "add", "symlink"), ("tests/__pycache__", "add", "regular")]
    assert artifact.excluded_pathset_changed is False
    report, _ = classify_frozen_patch(artifact, baseline)
    assert report.verdict == "projectable"
    spec = make_fixture_spec(fixture_repo.base_commit, fixture_image, snapshot_host_path=str(fixture_repo.path), candidate_test_script=make_candidate_test_script())
    projection, split = build_trusted_scoring_projection(artifact, spec.hygiene)
    assert projection.included_entry_paths == ("src/.pytest_cache",) and split.ignored_paths == ("tests/__pycache__",)
    source = FrozenDeltaSource(frozen_patch=artifact, baseline_manifest=baseline, projection=projection, frozen_patch_digest=compute_frozen_patch_digest(artifact))
    manager = _grade_manager(tmp_path)
    graded = await manager.grade(trajectory_id="b4-pc", workspace=None, spec=spec, frozen_delta=source)
    assert graded.outcome == "unresolved" and graded.failure_category == "tests_failed", graded.infra_failure_detail
    assert manager.container_records[-1].omitted_cache == {"dirs": 0, "files": 0}
    side = json.loads((Path(manager.config.eval_log_dir) / f"{graded.eval_log_ref.ref_id}.diagnostics.json").read_text())
    assert side["grader_baseline_omitted_cache_count"] == {"dirs": 0, "files": 0}  # 只反映 grader 重建 baseline 的省略计数


SRC_SYNTAX_ERROR = 'def feature(:\n    return "fixed"\n'


async def test_pa_candidate_syntax_error_is_candidate_execution_failed_only_with_qualification(fixture_repo, fixture_image, tmp_path):
    """第四组 P-A 真容器往返：候选把 src/thing.py 改成语法错误 → 官方测试脚本在 import 阶段崩溃（零解析）。
    - 带有效资格记录：编译复证（候选身份、同一解释器）报 SyntaxError → candidate_execution_failed、reward 0、阶段 test_startup；
    - 同一日志、资格缺席：failed_to_grade / test_log_parse_failed / reward None，detail 记 qualification:absent。"""
    import dataclasses

    from repoharness2.grading.manager import EnvQualification, grading_image_identity, grading_scripts_digest, render_compile_probe_script

    mutate = f"cd /testbed && cat > src/thing.py <<'EOF'\n{SRC_SYNTAX_ERROR}EOF\n"
    baseline, artifact, _, _ = await _candidate_flow(fixture_image, fixture_repo, mutate, BASELINE_MANIFEST_POLICY_V2)
    assert [(e.path, e.operation) for e in artifact.entries] == [("src/thing.py", "modify")]
    report, _ = classify_frozen_patch(artifact, baseline)
    assert report.verdict == "projectable"
    spec = make_fixture_spec(
        fixture_repo.base_commit, fixture_image, snapshot_host_path=str(fixture_repo.path),
        candidate_test_script=make_candidate_test_script(), render_compile_probe=render_compile_probe_script,
    )
    q = EnvQualification(
        image_identity=grading_image_identity(spec), scripts_digest=grading_scripts_digest(spec), reference_missing_count=0,
        source="fixture_gold:rpt_1", qualified_at_utc="2026-09-16T00:00:00Z",
    )
    projection, split = build_trusted_scoring_projection(artifact, spec.hygiene)
    source = FrozenDeltaSource(frozen_patch=artifact, baseline_manifest=baseline, projection=projection, frozen_patch_digest=compute_frozen_patch_digest(artifact))

    manager = _grade_manager(tmp_path)
    graded = await manager.grade(trajectory_id="b4-pa-q", workspace=None, spec=dataclasses.replace(spec, env_qualification=q), frozen_delta=source)
    assert graded.outcome == "unresolved" and graded.failure_category == "candidate_execution_failed" and graded.reward == 0.0, graded.infra_failure_detail
    assert graded.execution_failure_stage == "test_startup" and graded.f2p_total_count is None
    ev = graded.execution_failure_evidence
    assert any(line.startswith("SyntaxError:") for line in ev), ev
    assert any(line.startswith("compile_probe:src/thing.py:SyntaxError:line=1:") for line in ev), ev
    side = json.loads((Path(manager.config.eval_log_dir) / f"{graded.eval_log_ref.ref_id}.diagnostics.json").read_text())
    dec = side["execution_failure_decision"]
    assert dec["kind"] == "candidate" and dec["trigger"] == "zero_parsed" and dec["compile_probe"]["error_paths"] == [f"src/thing.py:SyntaxError:line=1:{dec['compile_probe']['error_paths'][0].split(':', 3)[3]}"]
    assert dec["compile_probe"]["interpreter"] and side["resource_facts"]["oom_kill_events"] == 0
    assert "SyntaxError" in _eval_log(manager, graded)

    manager2 = _grade_manager(tmp_path / "second")
    graded2 = await manager2.grade(trajectory_id="b4-pa-noq", workspace=None, spec=spec, frozen_delta=source)
    assert graded2.outcome == "failed_to_grade" and graded2.failure_category == "test_log_parse_failed" and graded2.reward is None
    assert graded2.infra_failure_detail.startswith("eval_log_zero_parsed_tests:unattributed:") and "qualification:absent" in graded2.infra_failure_detail


async def test_pc_r6_omitted_cache_dir_replaced_by_regular_file_is_graded_not_infra(fixture_image, tmp_path):
    """A 线复核 R6：基线里有 `.pytest_cache/old`（政策 v2 整体省略），候选把目录换成同名普通文件 → 导出只见 `add`；
    grader 应用前按 manifest 政策删掉可再生缓存目录（一致规范化），应用成功、评分正常，不再落 `add_target_exists` infra。"""
    repo0 = build_fixture_repo(tmp_path / "repo")
    (repo0.path / ".pytest_cache").mkdir()
    (repo0.path / ".pytest_cache" / "old").write_text("stale\n")
    git_in(repo0.path, "add", "-f", ".pytest_cache/old")
    git_in(repo0.path, "commit", "-qm", "add cache dir")
    repo = FixtureRepo(path=repo0.path, base_commit=git_in(repo0.path, "rev-parse", "HEAD").strip())
    mutate = (
        "cd /testbed && rm -rf .pytest_cache && printf 'not a dir\\n' > .pytest_cache && "
        f"cat > src/thing.py <<'EOF'\n{SRC_FIXED}EOF\n"
    )
    baseline, artifact, sink_b, _ = await _candidate_flow(fixture_image, repo, mutate, BASELINE_MANIFEST_POLICY_V2)
    assert sink_b == {"dirs": 1, "files": 1}
    assert [(e.path, e.operation, e.object_type) for e in artifact.entries] == [(".pytest_cache", "add", "regular"), ("src/thing.py", "modify", "regular")]
    report, _ = classify_frozen_patch(artifact, baseline)
    assert report.verdict == "projectable"
    prelude = "test -f /testbed/.pytest_cache && ! test -d /testbed/.pytest_cache && echo RH2_CACHE_FILE_OK || echo RH2_CACHE_FILE_MISSING\n"
    spec = make_fixture_spec(repo.base_commit, fixture_image, snapshot_host_path=str(repo.path), candidate_test_script=make_candidate_test_script(extra_prelude=prelude))
    projection, split = build_trusted_scoring_projection(artifact, spec.hygiene)
    assert split.unsupported_shape_reasons == () and projection.included_entry_paths == (".pytest_cache", "src/thing.py")
    source = FrozenDeltaSource(frozen_patch=artifact, baseline_manifest=baseline, projection=projection, frozen_patch_digest=compute_frozen_patch_digest(artifact))
    manager = _grade_manager(tmp_path)
    graded = await manager.grade(trajectory_id="b4-r6", workspace=None, spec=spec, frozen_delta=source)
    assert graded.outcome == "resolved" and graded.reward == 1.0, graded.infra_failure_detail
    assert "RH2_CACHE_FILE_OK" in _eval_log(manager, graded)

