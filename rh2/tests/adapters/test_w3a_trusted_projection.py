"""W3a（决策包 D2-3，owner 2026-09-04 已批）：可信评分投影 —— 控制面改动不重放、不 DROP、不 unsafe。

被测事实：
- 纯函数 `split_trusted_scoring_projection` / `build_trusted_scoring_projection`（排除法、分类优先级、
  路径集不交且并集完整、evidence/审计记录形态、evidence 截断）；
- 正式链 e2e（真实 SWEGradingManager + 评分侧 FakeDocker）：
    只改测试没修代码 → grader 自然 0（tests_failed）且正常进组（EligibilityReport 在场，KEEP_FULL）；
    写测试且真修好 → 1（resolved）；
    控制面路径清单/计数进审计（audit.trusted_projection）+ Outcome evidence_refs + sidecar；
    `.rh2*` / `rh2/*` 命中 = 命名空间冲突：不进投影、不 unsafe、不 fatal、照常评分；
    结构不安全 artifact（symlink 逃逸）仍是 unsafe 永久拒绝、不评分；
- grader 侧独立重算与投影不一致 = run-halt（见 tests/grading/test_b4_frozen_delta.py）。
"""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "grading"))
from grading_fixtures import FAILING_FAKE_LOG, GOOD_FAKE_LOG, FakeDocker, make_fixture_spec  # noqa: E402
from test_f2_2_capability import _stamp_fa_identity  # noqa: E402
from test_slime_generate import (  # noqa: E402
    BASE_COMMIT,
    SAMPLING_PARAMS,
    TASK_ID_DENSE,
    FakeFinalizationStore,
    FakeRolloutDocker,
    _Args,
    _formal_config,
    build_dense_chain,
    dense_turns,
    make_task,
)
from test_w3a_formal_grading_freeze import make_barrier  # noqa: E402

from repoharness2.contracts.frozen_patch import FrozenPatchArtifactV1, PatchEntry, compute_frozen_patch_digest  # noqa: E402
from repoharness2.governance.admission import (  # noqa: E402
    DispositionPolicy,
    decide_member_disposition,
    resolve_admission_payload,
)
from repoharness2.grading.manager import (  # noqa: E402
    DEFAULT_SWE_FORBIDDEN_GLOBS,
    DEFAULT_SWE_TEST_GLOBS,
    GradingManagerConfig,
    HygieneRules,
    SWEGradingManager,
)
from repoharness2.grading.trusted_projection import (  # noqa: E402
    EVIDENCE_IGNORED_PATH_LIMIT,
    TRUSTED_PROJECTION_RULE_VERSION,
    build_trusted_scoring_projection,
    classify_control_plane_path,
    expected_candidate_paths,
    split_trusted_scoring_projection,
)

SWE_RULES = HygieneRules(
    test_files=("tests/test_official.py",),
    test_globs=DEFAULT_SWE_TEST_GLOBS,
    forbidden_globs=DEFAULT_SWE_FORBIDDEN_GLOBS,
)


def _entry(path: str, content: bytes = b"x", *, operation: str = "add") -> PatchEntry:
    if operation == "delete":
        return PatchEntry(path=path, operation="delete", object_type="regular")
    return PatchEntry(
        path=path, operation=operation, object_type="regular", mode="100644",
        content_b64=base64.b64encode(content).decode(),
        content_digest="sha256:" + hashlib.sha256(content).hexdigest(),
    )


# ---------------------------------------------------------------------------
# 纯函数
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path, expected", [
    ("tests/test_official.py", "official_test_file"),  # 精确文件优先于 glob
    ("tests/test_new.py", "test_glob"),
    ("pkg/tests/helpers.py", "test_glob"),
    ("test_root.py", "test_glob"),
    ("pkg/mod_test.py", "test_glob"),
    (".rh2_marker", "reserved_namespace"),
    ("rh2/eval.sh", "reserved_namespace"),
    ("src/fix.py", None),
    ("conftest.py", None),  # 已知不足：conftest/pytest.ini 等不在首训控制面（登记不修）
    ("setup.cfg", None),
])
def test_classify_control_plane_path_priority(path, expected):
    assert classify_control_plane_path(SWE_RULES, path) == expected


def test_split_is_exclusion_based_and_partitions_paths():
    entries = [
        _entry("src/fix.py"), _entry("tests/test_new.py"), _entry("tests/test_official.py", operation="delete"),
        _entry("rh2/eval.sh"), _entry("docs/x.md"), _entry(".rh2_marker"),
    ]
    split = split_trusted_scoring_projection(entries, SWE_RULES)
    assert split.candidate_paths == ("docs/x.md", "src/fix.py")
    assert split.ignored_paths == (".rh2_marker", "rh2/eval.sh", "tests/test_new.py", "tests/test_official.py")
    assert set(split.candidate_paths) | set(split.ignored_paths) == {e.path for e in entries}
    assert set(split.candidate_paths) & set(split.ignored_paths) == set()
    assert split.ignored_counts_by_class() == {"official_test_file": 1, "test_glob": 1, "reserved_namespace": 2}
    by_path = {e.path: e for e in split.ignored_entries}
    assert by_path["tests/test_official.py"].operation == "delete"
    assert by_path["tests/test_official.py"].control_plane_class == "official_test_file"
    rec = split.to_record()
    assert rec["rule_version"] == TRUSTED_PROJECTION_RULE_VERSION
    assert rec["candidate_solution_count"] == 2 and rec["ignored_validation_count"] == 4
    assert rec["ignored_validation_entries"][0] == {
        "path": ".rh2_marker", "operation": "add", "object_type": "regular", "control_plane_class": "reserved_namespace",
    }
    refs = split.evidence_refs()
    assert refs[0] == f"trusted_projection:{TRUSTED_PROJECTION_RULE_VERSION}"
    assert refs[1] == "trusted_projection:candidate=2:ignored=4"
    assert "ignored_validation_delta:official_test_file:delete:tests/test_official.py" in refs
    assert expected_candidate_paths(entries, SWE_RULES) == {"docs/x.md", "src/fix.py"}


def test_split_with_empty_control_plane_rules_keeps_everything():
    entries = [_entry("tests/test_new.py"), _entry("src/fix.py")]
    split = split_trusted_scoring_projection(entries, HygieneRules())
    assert split.candidate_paths == ("src/fix.py", "tests/test_new.py") and split.ignored_entries == ()
    assert split.evidence_refs()[1] == "trusted_projection:candidate=2:ignored=0"


def test_evidence_refs_truncate_long_ignored_lists():
    entries = [_entry(f"tests/test_{i:03d}.py") for i in range(EVIDENCE_IGNORED_PATH_LIMIT + 7)]
    split = split_trusted_scoring_projection(entries, SWE_RULES)
    refs = split.evidence_refs()
    assert sum(r.startswith("ignored_validation_delta:test_glob:") for r in refs) == EVIDENCE_IGNORED_PATH_LIMIT
    assert refs[-1] == "ignored_validation_delta_truncated:7"
    assert len(split.to_record()["ignored_validation_entries"]) == EVIDENCE_IGNORED_PATH_LIMIT + 7  # 审计全量


def test_build_projection_references_candidate_paths_only_and_binds_digest():
    art = FrozenPatchArtifactV1(
        task_id="t", rollout_execution_id="exec_1", physical_attempt_id="exec_1#p1-aaaa",
        baseline_manifest_digest="sha256:" + "b" * 64, public_bundle_digest="sha256:" + "e" * 64,
        runtime_image_digest="sha256:" + "1" * 64, materialized_head="a" * 40,
        entries=(_entry("src/fix.py"), _entry("tests/test_new.py")), excluded_pathset_changed=False,
    )
    projection, split = build_trusted_scoring_projection(art, SWE_RULES)
    assert projection.included_entry_paths == ("src/fix.py",)
    assert projection.frozen_patch_digest == compute_frozen_patch_digest(art)
    assert projection.rollout_execution_id == "exec_1" and projection.physical_attempt_id == "exec_1#p1-aaaa"
    assert split.ignored_paths == ("tests/test_new.py",)


# ---------------------------------------------------------------------------
# 正式链 e2e（真实 grader）
# ---------------------------------------------------------------------------


def _task_with_rules(rules: HygieneRules):
    task = make_task(TASK_ID_DENSE)
    spec = make_fixture_spec(
        BASE_COMMIT, "fake-image:v1", checkout_mode="image_embedded", task_id=TASK_ID_DENSE, hygiene=rules,
    )
    return dataclasses.replace(task, grading_spec=spec)


def _chain(tree: dict[str, bytes], *, eval_log: str, rules: HygieneRules = SWE_RULES, artifact_dir=None):
    grading_docker = FakeDocker(base_commit=BASE_COMMIT, eval_log=eval_log)
    manager = SWEGradingManager(GradingManagerConfig(), docker=grading_docker)
    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=make_barrier(tree), turns=turns,
        finalization_store=FakeFinalizationStore(), docker=FakeRolloutDocker(exec_after_rm_raises=True),
        task=_task_with_rules(rules), artifact_dir=artifact_dir,
    )
    _stamp_fa_identity(chain.base_sample)
    submitted: list[dict] = []

    async def submit(*, trajectory_id, workspace, spec, frozen_delta=None):
        submitted.append({"workspace": workspace, "frozen_delta": frozen_delta})
        return await manager.grade(trajectory_id=trajectory_id, workspace=workspace, spec=spec, frozen_delta=frozen_delta)

    chain.orchestrator._grading_submit = submit
    chain.orchestrator._grader_phase_timing_source = manager.take_grader_phase_timing
    return chain, submitted, grading_docker


_IDENTITY = {"rh2_physical_attempt_id": "exec_F22#p1-cafe1234", "rh2_rollout_execution_id": "exec_F22"}


def _decide(leaf):
    """consumer 侧 join（同 test_w1b_delivery_face._resolve：叶身份键由 miles 交付面盖上，此处补齐）。"""

    payload = resolve_admission_payload({**leaf.metadata, **_IDENTITY})
    return payload, decide_member_disposition(payload, policy=DispositionPolicy())


async def test_test_only_change_scores_zero_and_enters_group_normally():
    """只改测试没修代码：投影 candidate 为空 → grader 在干净 baseline 上后写 official test_patch、跑
    eval → 自然 0（tests_failed）；EligibilityReport 七维全过、KEEP_FULL；控制面路径进审计与 evidence。"""

    chain, submitted, grading_docker = _chain(
        {"tests/test_official.py": b"def test_official():\n    assert False\n",
         "tests/test_new.py": b"def test_new():\n    assert True\n"},
        eval_log=FAILING_FAKE_LOG,
    )
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    (call,) = submitted
    assert call["workspace"] is None and call["frozen_delta"].projection.included_entry_paths == ()
    report = audit.finalized.grading_report
    assert report.outcome == "unresolved" and report.failure_category == "tests_failed" and report.reward == 0.0
    assert report.patch_hygiene.verdict == "clean" and report.patch_hygiene.test_files_modified is False
    assert audit.unsafe_artifact_reasons == [] and audit.ignored_validation_entry_count == 2
    assert audit.trusted_projection["ignored_validation_counts_by_class"] == {
        "official_test_file": 1, "test_glob": 1, "reserved_namespace": 0,
    }
    assert audit.trusted_projection["candidate_solution_paths"] == []
    # 控制面文件一个字节都没写进 grader 容器
    joined = "\n".join(c[-1] for c in grading_docker.calls if c[0] == "exec" and isinstance(c[-1], str))
    assert "test_official.py" not in joined and "test_new.py" not in joined
    (leaf,) = delivered
    assert leaf.remove_sample is False and leaf.reward == 0.0
    payload, d = _decide(leaf)
    assert (d.verdict, d.reason_code) == ("KEEP_FULL", "all_dimensions_ok")
    assert payload.eligibility_report.facts.security_and_leakage.ok is True
    assert payload.eligibility_report.facts.clean_grading.ok is True
    evidence = payload.outcome.evidence_refs
    assert "ignored_validation_delta:official_test_file:add:tests/test_official.py" in evidence
    assert "ignored_validation_delta:test_glob:add:tests/test_new.py" in evidence
    assert "trusted_projection:candidate=0:ignored=2" in evidence


async def test_test_plus_real_fix_scores_one(tmp_path):
    """同时写测试且真修好：candidate = src/fix.py 重放，eval 全过 → 1（resolved）；sidecar 落盘
    trusted_scoring_projection.json。"""

    chain, submitted, grading_docker = _chain(
        {"src/fix.py": b"print('fixed')\n", "tests/test_new.py": b"def test_new():\n    assert True\n"},
        eval_log=GOOD_FAKE_LOG, artifact_dir=tmp_path,
    )
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    (call,) = submitted
    assert call["frozen_delta"].projection.included_entry_paths == ("src/fix.py",)
    report = audit.finalized.grading_report
    assert report.outcome == "resolved" and report.reward == 1.0
    joined = "\n".join(c[-1] for c in grading_docker.calls if c[0] == "exec" and isinstance(c[-1], str))
    assert "'./src/fix.py'" in joined and "test_new.py" not in joined
    (leaf,) = delivered
    assert leaf.reward == 1.0
    _payload, d = _decide(leaf)
    assert d.verdict == "KEEP_FULL"
    sidecar = json.loads((tmp_path / audit.trajectory_id / "trusted_scoring_projection.json").read_text())
    assert sidecar["candidate_solution_paths"] == ["src/fix.py"]
    assert sidecar["ignored_validation_entries"] == [
        {"path": "tests/test_new.py", "operation": "add", "object_type": "regular", "control_plane_class": "test_glob"},
    ]


async def test_reserved_namespace_hit_is_ignored_not_unsafe_not_fatal():
    """`.rh2*` / `rh2/*` = 命名空间冲突：不进投影、不宣称边界突破（不 unsafe、不 fatal），照常评分。"""

    chain, submitted, grading_docker = _chain(
        {"src/fix.py": b"print('fixed')\n", "rh2/inject.sh": b"echo pwned\n", ".rh2_note": b"x\n"},
        eval_log=GOOD_FAKE_LOG,
    )
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.unsafe_artifact_reasons == [] and audit.finalized is not None
    assert audit.finalized.grading_report.outcome == "resolved"
    assert submitted[0]["frozen_delta"].projection.included_entry_paths == ("src/fix.py",)
    assert audit.trusted_projection["ignored_validation_counts_by_class"]["reserved_namespace"] == 2
    # delta 写入命令用 `./<path>` 形态；grader 自己的 /rh2/eval.sh 脚本路径与之无关
    joined = "\n".join(c[-1] for c in grading_docker.calls if c[0] == "exec" and isinstance(c[-1], str))
    assert "'./src/fix.py'" in joined
    assert "'./rh2/inject.sh'" not in joined and "'./.rh2_note'" not in joined
    (leaf,) = delivered
    _payload, d = _decide(leaf)
    assert d.verdict == "KEEP_FULL"
    assert "ignored_validation_delta:reserved_namespace:add:rh2/inject.sh" in _payload.outcome.evidence_refs


async def test_structurally_unsafe_artifact_is_still_permanent_rejection():
    """结构不安全（symlink 逃逸）仍走 unsafe_artifact_permanent_rejection：不投影、不评分、DROP。"""

    target = b"../../../etc/shadow"
    tb64 = base64.b64encode(target).decode()
    tsha = hashlib.sha256(target).hexdigest()
    from types import SimpleNamespace

    from repoharness2.adapters.slime.generate import QuiescenceConfirmed

    class _Ws:
        snapshot_ref = "sha256:abc"

        def __init__(self, underlying):
            self._u = underlying

        async def run_bash(self, script):
            if "find ." in script:
                return SimpleNamespace(exit_code=0, stdout=f"symlink\t120000\t{tsha}\tsrc/link\n", stderr="")
            if "readlink" in script:
                return SimpleNamespace(exit_code=0, stdout=f"src/link\t{tb64}\n", stderr="")
            return await self._u.run_bash(script)

    class _Barrier:
        async def establish(self, *, workspace, audit):
            return QuiescenceConfirmed(frozen_grading_workspace=_Ws(workspace), snapshot_ref="sha256:abc", evidence_refs=("s",))

    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=_Barrier(), turns=turns, finalization_store=FakeFinalizationStore(),
        task=_task_with_rules(SWE_RULES),
    )
    _stamp_fa_identity(chain.base_sample)
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert chain.grading.calls == [] and audit.trusted_projection is None
    assert audit.unsafe_artifact_reasons == ["unsafe_symlink_escape:src/link"]
    (leaf,) = delivered
    payload, d = _decide(leaf)
    assert payload.outcome.reason_code == "unsafe_artifact_permanent_rejection"
    assert (d.verdict, d.reason_code) == ("DROP_GROUP", "unsafe_artifact_permanent_rejection")


async def test_grader_recomputes_split_from_spec_and_rejects_tampered_projection():
    """信任边界：producer 投影被篡改成夹带控制面路径（模拟持久化/装配层错误）→ grader 侧按
    spec.hygiene 独立重算不等 → BaselineIntegrityError run-halt（经 generate 升 Fatal），不起评分容器。"""

    from repoharness2.adapters.slime.async_worker import FatalExecutionInfrastructureError
    from repoharness2.grading.manager import FrozenDeltaSource

    chain, submitted, grading_docker = _chain(
        {"src/fix.py": b"x\n", "tests/test_new.py": b"y\n"}, eval_log=GOOD_FAKE_LOG,
    )
    manager_grade = chain.orchestrator._grading_submit

    async def tampered_submit(*, trajectory_id, workspace, spec, frozen_delta=None):
        tampered = FrozenDeltaSource(
            frozen_patch=frozen_delta.frozen_patch, baseline_manifest=frozen_delta.baseline_manifest,
            projection=frozen_delta.projection.model_copy(
                update={"included_entry_paths": ("src/fix.py", "tests/test_new.py")}
            ),
            frozen_patch_digest=frozen_delta.frozen_patch_digest,
        )
        return await manager_grade(trajectory_id=trajectory_id, workspace=workspace, spec=spec, frozen_delta=tampered)

    chain.orchestrator._grading_submit = tampered_submit
    with pytest.raises(FatalExecutionInfrastructureError, match="frozen_delta_binding_mismatch"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert not any(c[0] == "run" for c in grading_docker.calls)
    audit = chain.orchestrator.audits[0]
    assert any(f.error_type == "frozen_delta_binding_mismatch" for f in audit.failure_records)
