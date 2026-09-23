"""09-19 有界 CPU Production Tracer：不启动 Docker、网络、模型或训练。

调用生产 prepared/driver/queue/manager。actor 只抽取并执行原文件中的
task-face load / resolver / grading-submit AST，避免启动模型 HTTP 服务；
它证明这一接缝的运输，不冒充完整 BringupService 启动。
"""
from __future__ import annotations

import ast
import asyncio
import hashlib
import inspect
import json
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/pyproject.toml").exists())
for path in (ROOT / "reference/miles-rh2-integration", ROOT / "rh2/src", ROOT / "rh2/tests", ROOT / "rh2/tests/grading", ROOT / "rh2/tests/adapters"):
    sys.path.insert(0, str(path))

from test_replay_grade import DriverProfileFakeDocker  # noqa: E402
from test_w3b_grader_profile_unit import GOOD_SETUP_ATTEST  # noqa: E402
from sandbox_test_support import make_grader_profile, make_rollout_profile  # noqa: E402
from repoharness2.adapters.miles import identity as idm  # noqa: E402
from repoharness2.adapters.miles.attempt_assignment import AttemptAssignmentRegistry, assignment_from_dispatch  # noqa: E402
from repoharness2.adapters.slime.prepared_task_face import PreparedTaskFace  # noqa: E402
from repoharness2.adapters.slime.replay_grade import (  # noqa: E402
    CandidateInput, DerivedImage, ReplayGrader, load_context, load_env_qualifications, prepare_for_replay,
)
from repoharness2.contracts.baseline_manifest import BaselineWorkspaceManifestV1  # noqa: E402
from repoharness2.contracts.frozen_patch import FrozenPatchArtifactV1, compute_frozen_patch_digest  # noqa: E402
from repoharness2.contracts.scoring_projection import ScoringProjectionArtifactV1  # noqa: E402
from repoharness2.envpack.prepared_tasks import HOST_GRADING_FILE  # noqa: E402
from repoharness2.grading.manager import (  # noqa: E402
    ExecResult, FrozenDeltaSource, GradingManagerConfig, SWEGradingManager, env_qualification_status, patch_touched_paths,
)
from repoharness2.grading.queue import GradingQueue, GradingQueueConfig  # noqa: E402
from repoharness2.shutdown.chain import LifecycleState  # noqa: E402

TASK = "swe_gym_lite::getmoto__moto-6913"
ID_A = "sha256:" + "ab" * 32
ID_B = "sha256:" + "cd" * 32
TAG = "local/derived:review"


def snapshot():
    paths = [
        "rh2/src/repoharness2/adapters/slime/bringup.py",
        "rh2/src/repoharness2/adapters/slime/prepared_task_face.py",
        "rh2/src/repoharness2/adapters/slime/replay_grade.py",
        "rh2/src/repoharness2/adapters/slime/sandbox_profile.py",
        "rh2/src/repoharness2/grading/manager.py",
        "rh2/src/repoharness2/grading/queue.py",
    ]
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}


class ImageDocker(DriverProfileFakeDocker):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tag_id = ID_A
        self.swap_after_inspect = False
        self.run_images = []

    async def __call__(self, *args, input_bytes=None):
        if args[:4] == ("image", "inspect", "-f", "{{.Id}}"):
            self.calls.append(args)
            observed = self.tag_id
            if self.swap_after_inspect:
                self.tag_id = ID_B
                self.swap_after_inspect = False
            return ExecResult(0, observed + "\n", "")
        if args[0] == "run":
            self.run_images.append({"ref": args[-3], "actual_id": self.tag_id, "init": "--init" in args})
        return await super().__call__(*args, input_bytes=input_bytes)


def ctx_for(summary, docker, name, *, derived=False, qualifications=None):
    return load_context(
        prepared_dir=summary["prepared_dir"], private_dir=summary["private_dir"],
        manifest_sha256=summary["prepared_manifest_sha256"],
        rollout_profile=make_rollout_profile(), grader_profile=make_grader_profile(),
        artifacts_dir=HERE / "runtime" / name / "artifacts", run_id=name,
        docker=docker, qualifications=qualifications,
        derived_image=DerivedImage(ref=TAG, recipe="CPU identity probe") if derived else None,
    )


def configure(docker, ctx):
    public = ctx.rollout_views[TASK].public
    grading = ctx.grading_views[TASK].grading
    docker.base_commit = public.base_commit
    docker.repo_digests = (f"{public.image.split(':')[0]}@{public.image_manifest_digest}",)
    n = len(set(patch_touched_paths(grading.test_patch)))
    docker.setup_attest = {**GOOD_SETUP_ATTEST, "RH2_SETUP_EXPECTED_TEST_FILES": str(n), "RH2_SETUP_TEST_FILES": str(n)}
    docker.eval_log = (
        "RH2_INSTALL_RC=0\n+ : '>>>>> Start Test Output'\n"
        + "".join(f"PASSED {t}\n" for t in [*grading.fail_to_pass, *grading.pass_to_pass])
        + "+ : '>>>>> End Test Output'\nRH2_TEST_RC=0\n"
    )
    docker.observation_stdout = "RH2_OBS_RUNNER_DIGEST=same\n"


async def replay(summary, name, *, derived=False, qualifications=None, tag_id=ID_A, swap=False):
    docker = ImageDocker(base_commit="0" * 40, image_present=True)
    docker.tag_id = tag_id
    docker.swap_after_inspect = swap
    ctx = ctx_for(summary, docker, name, derived=derived, qualifications=qualifications)
    configure(docker, ctx)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=HERE / "runtime" / name / "logs", sandbox_profile=make_grader_profile()), docker=docker)
    ledger = HERE / "runtime" / name / "ledger.jsonl"
    row = await ReplayGrader(ctx, manager, ledger_path=ledger).replay_one(TASK, CandidateInput(kind="noop", origin="noop"))
    assert row["stage_error"] is None and row["report"]["reward"] == 1.0, row
    assert all(r.removed and r.eval_log_partial is None for r in manager.container_records)
    assert all(x["init"] for x in docker.run_images)
    await manager.close()
    return row, ctx, docker, ledger


def actor_slice(summary):
    path = ROOT / "rh2/src/repoharness2/adapters/slime/bringup.py"
    tree = ast.parse(path.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "BringupService")
    ctor = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    load = next(n for n in ast.walk(ctor) if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
                and isinstance(n.value.func, ast.Attribute) and isinstance(n.value.func.value, ast.Name)
                and n.value.func.value.id == "PreparedTaskFace" and n.value.func.attr == "load")
    methods = [next(n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
               for name in ("_resolve_grading_spec", "_grading_submit")]
    service = SimpleNamespace(lifecycle=LifecycleState())
    env = {
        "PreparedTaskFace": PreparedTaskFace, "self": service,
        "PREPARED_TASKS_DIR": summary["prepared_dir"],
        "PREPARED_TASKS_MANIFEST_SHA256": summary["prepared_manifest_sha256"],
        "HOST_GRADING_ARTIFACT_PATH": str(Path(summary["private_dir"]) / HOST_GRADING_FILE),
        "HOST_GRADING_ARTIFACT_SHA256": summary["host_grading_artifact_sha256"],
        "AGENT_TIME_BUDGET_SEC": 600,
        "args": SimpleNamespace(prompt_data=str(Path(summary["prepared_dir"]) / "prompts.jsonl")),
        "INJECT_INFRA_INSTANCE": None, "Any": object,
    }
    exec(compile(ast.Module(body=[load, *methods], type_ignores=[]), str(path), "exec"), env)
    face = service.prepared_face
    service.attempt_assignments = AttemptAssignmentRegistry(verify_dispatch=face.verify_dispatch)
    record = face.manifest.record(TASK).model_dump(mode="json")
    minted = {
        idm.GROUP_ID_KEY: "review_g0", idm.GROUP_INDEX_KEY: 0, idm.EXECUTION_ID_KEY: "review_g0_m0",
        idm.MEMBER_SLOT_KEY: 0, idm.ATTEMPT_ID_KEY: "review_g0_m0#p1-01234567", idm.ATTEMPT_SEQ_KEY: 1,
    }
    service.attempt_assignments.bind(assignment_from_dispatch(record, minted))
    sample = SimpleNamespace(metadata={**record, **minted}, label=TASK)
    return service, sample, env, [k.arg for k in load.value.keywords]


async def formal_transport(summary, ctx, qualification, name, inject_constructor):
    service, sample, env, load_keywords = actor_slice(summary)
    if inject_constructor:
        service.prepared_face = PreparedTaskFace(
            manifest=ctx.manifest, rollout_views=ctx.rollout_views, host_grading_views=ctx.grading_views,
            time_budget_seconds=600, qualifications=qualification,
        )
    spec = env["_resolve_grading_spec"](service, sample)
    docker = ImageDocker(base_commit="0" * 40, image_present=True)
    configure(docker, ctx)
    # 完整日志长文本应写盘，评分结束后不能留在 _records。
    docker.eval_log += "MEMORY_SENTINEL=" + "z" * (1024 * 1024) + "\n"
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=HERE / "runtime" / name / "logs", sandbox_profile=make_grader_profile()), docker=docker)
    service.grading_queue = GradingQueue(manager, GradingQueueConfig(concurrency=1, queue_size=2))
    artifact_path = next(ctx.artifacts_dir.rglob("frozen_patch.json"))
    artifact = FrozenPatchArtifactV1.model_validate_json(artifact_path.read_text())
    baseline = BaselineWorkspaceManifestV1.model_validate_json((artifact_path.parent / "baseline_manifest.json").read_text())
    projection = ScoringProjectionArtifactV1.model_validate_json((artifact_path.parent / "projection.json").read_text())
    source = FrozenDeltaSource(frozen_patch=artifact, baseline_manifest=baseline, projection=projection, frozen_patch_digest=compute_frozen_patch_digest(artifact))
    await service.grading_queue.start()
    try:
        report = await env["_grading_submit"](service, trajectory_id=name, workspace=None, spec=spec, frozen_delta=source)
    finally:
        await service.grading_queue.close()
    record = manager.container_records[-1]
    log_path = manager.config.eval_log_dir / f"{report.eval_log_ref.ref_id}.eval.log"
    assert report.reward == 1.0 and report.outcome == "resolved"
    assert record.eval_log_partial is None and record.removed
    assert "MEMORY_SENTINEL=" in log_path.read_text()
    assert "MEMORY_SENTINEL=" not in repr(vars(record))
    await manager.close()
    return {
        "scope": "原 actor 三处 AST + prepared/attempt registry/queue/frozen manager；未启动完整 actor",
        "constructor_injection": inject_constructor, "actor_load_keywords": load_keywords,
        "load_signature_has_qualifications": "qualifications" in inspect.signature(PreparedTaskFace.load).parameters,
        "spec_qualification": env_qualification_status(spec)[1], "sidecar_qualification": record.diagnostics["env_qualification"],
        "report": report.model_dump(mode="json"), "log_bytes": log_path.stat().st_size,
        "record_retains_full_log": False, "all_container_runs_have_init": all(x["init"] for x in docker.run_images),
    }


async def cancellation(summary, name, where):
    entered = asyncio.Event()

    class CancelDocker(ImageDocker):
        async def __call__(self, *args, input_bytes=None):
            is_inspect = args[:4] == ("image", "inspect", "-f", "{{.Id}}")
            is_post = args[0] == "exec" and "RH2_OBS_IMPORT_PATH" in args[-1]
            if (where == "derived_inspect" and is_inspect) or (where == "post_observation" and is_post):
                entered.set()
                await asyncio.Event().wait()
            return await super().__call__(*args, input_bytes=input_bytes)

    docker = CancelDocker(base_commit="0" * 40, image_present=True)
    ctx = ctx_for(summary, docker, name, derived=True)
    configure(docker, ctx)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=HERE / "runtime" / name / "logs", sandbox_profile=make_grader_profile()), docker=docker)
    ledger = HERE / "runtime" / name / "ledger.jsonl"
    task = asyncio.create_task(ReplayGrader(ctx, manager, ledger_path=ledger).replay_one(TASK, CandidateInput(kind="noop", origin="noop")))
    await asyncio.wait_for(entered.wait(), timeout=10)
    task.cancel()
    try:
        await task
        raise AssertionError("取消未传播")
    except asyncio.CancelledError:
        pass
    rows = [json.loads(l) for l in ledger.read_text().splitlines()]
    assert len(rows) == 1
    row = rows[0]
    if where == "derived_inspect":
        assert row["stage_error"] == "cancelled:derived_image_inspect" and not docker.run_images
    else:
        assert row["stage_error"] == "cancelled:grading" and row["log"]["partial"] is False
        data = Path(row["log"]["path"]).read_bytes()
        assert row["log"]["sha256"] == "sha256:" + hashlib.sha256(data).hexdigest()
        assert all(r.removed and r.eval_log_partial is None for r in manager.container_records)
    await manager.close()
    return {"stage_error": row["stage_error"], "ledger_rows": len(rows), "log": row["log"], "cancel_propagated": True,
            "all_manager_records_freed": all(r.eval_log_partial is None for r in manager.container_records),
            "container_runs": docker.run_images}


async def main():
    summary = prepare_for_replay(repo_root=ROOT, out_dir=HERE / "runtime/prepared", private_dir=HERE / "runtime/private", task_ids=[TASK])
    result = {"source_sha256": snapshot()}
    base, ctx, _, ledger = await replay(summary, "base_gold")
    qualification = load_env_qualifications([ledger])
    assert list(qualification) == [TASK]
    result["formal_default"] = await formal_transport(summary, ctx, qualification, "formal_default", False)
    result["constructor_transport_positive"] = await formal_transport(summary, ctx, qualification, "formal_injected", True)
    assert result["formal_default"]["spec_qualification"] == "absent"
    assert result["constructor_transport_positive"]["spec_qualification"].startswith("ok:")
    _, _, _, dledger = await replay(summary, "derived_gold", derived=True)
    derived_qualification = load_env_qualifications([dledger])
    for name, image_id, swap in (("stable", ID_A, False), ("rebuilt_before_inspect", ID_B, False), ("retag_after_inspect", ID_A, True)):
        row, _, docker, _ = await replay(summary, name, derived=True, qualifications=derived_qualification, tag_id=image_id, swap=swap)
        result[name] = {"qualification": row["env_qualification"], "identity_recorded": row["image_identity"],
                        "image_id_actual_recorded": row["image_id_actual"], "run_images": docker.run_images,
                        "reward": row["report"]["reward"]}
    assert result["stable"]["qualification"].startswith("ok:")
    assert result["rebuilt_before_inspect"]["qualification"] == "image_identity_mismatch"
    assert result["retag_after_inspect"]["qualification"].startswith("ok:")
    assert all(x["actual_id"] == ID_B for x in result["retag_after_inspect"]["run_images"])
    result["cancel_derived_inspect"] = await cancellation(summary, "cancel_inspect", "derived_inspect")
    result["cancel_post_observation"] = await cancellation(summary, "cancel_post", "post_observation")
    assert result["source_sha256"] == snapshot(), "复核过程中被审源码变化"
    text = json.dumps(result, ensure_ascii=False, indent=2).replace(str(ROOT), "<repo>")
    (HERE / "production_probe_result.json").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    asyncio.run(main())
