"""I21（第五组）：真实 `BringupService` 启动纵切——评测题包的加载、按平面核对 / 解析、启动期预检、独立评测作业。

与 `test_w3b_formal_entry_vertical.py` 同一套替身（fake 引擎 + FakeDocker；本机无 tokenizer 缓存即 skip）。
评测题包与训练题包是同一种 trusted-prep 产物；这里特意让两个题包**有交集**（TID2），验证代码不设互斥。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))
from sandbox_test_support import SandboxRuntimeFakeDocker  # noqa: E402
from test_w3b_formal_entry_vertical import _args, _prepare, _with_engine  # noqa: E402
from w1b_synthetic_tasks import IIDS, TID1, TID2, prepare_synthetic  # noqa: E402

HOOK = "repoharness2.adapters.miles.eval_report.log_eval_rollout_data"
POINT = "0123abcd4567"


def _eval_env(bringup, monkeypatch, eval_fx, *, eval_only: bool = False):
    monkeypatch.setattr(bringup, "EVAL_PREPARED_TASKS_DIR", str(eval_fx.prepared_dir))
    monkeypatch.setattr(bringup, "EVAL_PREPARED_TASKS_MANIFEST_SHA256", eval_fx.manifest_sha256)
    monkeypatch.setattr(bringup, "EVAL_HOST_GRADING_ARTIFACT_PATH", str(eval_fx.host_path))
    monkeypatch.setattr(bringup, "EVAL_HOST_GRADING_ARTIFACT_SHA256", eval_fx.manifest.host_grading_artifact_sha256)
    monkeypatch.setattr(bringup, "EVAL_ONLY", eval_only)


def _eval_args(args, eval_fx, **over):
    vars(args).update(
        eval_interval=1, eval_uses_snapshots=False, custom_eval_rollout_log_function_path=HOOK, reward_key=None,
        eval_reward_key=None, ci_metric_checker_key=None,
        eval_datasets=[SimpleNamespace(name="swe_dev", path=str(eval_fx.prompts_path), custom_generate_function_path=None)],
    )
    vars(args).update(over)
    return args


def _assignment(idm, assignment_from_dispatch, record, *, evaluation: bool):
    if evaluation:
        gid = f"eval-{POINT}-d0-p0"
    else:
        gid = "miles_g0"
    identity = {idm.GROUP_ID_KEY: gid, idm.GROUP_INDEX_KEY: 0, idm.EXECUTION_ID_KEY: f"{gid}_m0", idm.MEMBER_SLOT_KEY: 0,
                idm.ATTEMPT_ID_KEY: f"{gid}_m0#p1-01234567", idm.ATTEMPT_SEQ_KEY: 1}
    return assignment_from_dispatch(record, identity, evaluation=evaluation), identity


async def test_formal_startup_loads_the_eval_package_and_resolves_each_plane_from_its_own(world, monkeypatch, tmp_path):
    async def body(port, _requests):
        import repoharness2.adapters.slime.bringup as bringup
        import repoharness2.adapters.slime.generate as generate_mod
        from repoharness2.adapters.miles import identity as idm
        from repoharness2.adapters.miles.attempt_assignment import AttemptAssignmentError, assignment_from_dispatch

        train_fx = _prepare(bringup, monkeypatch, tmp_path)                      # 训练题包：TID1 + TID2
        eval_fx = prepare_synthetic(tmp_path / "evalpkg", iids=(IIDS[1],))       # 评测题包：TID2（与训练有交集）
        _eval_env(bringup, monkeypatch, eval_fx)
        monkeypatch.setattr(generate_mod, "run_docker", SandboxRuntimeFakeDocker())
        args = _eval_args(_args(port, train_fx), eval_fx)
        try:
            await bringup.ensure_fa_started(args)
        except OSError as exc:
            pytest.skip(f"本机无 Qwen3-8B tokenizer 缓存且离线，跳过：{exc}")
        service = bringup.BringupService._instance
        try:
            assert service.eval_wiring.enabled and not service.eval_wiring.eval_only
            assert service.prepared_face is not None and service.eval_prepared_face is not None
            assert set(service.eval_prepared_face.task_ids()) == {TID2} and set(service.task_specs) == {TID1, TID2}
            assert getattr(args, "rh2_eval_only", False) is False
            evidence = json.loads((tmp_path / "artifacts" / "startup_evidence.json").read_text())
            assert evidence["eval_wiring"] == {"enabled": True, "eval_only": False, "dataset_name": "swe_dev", "eval_task_count": 1,
                                               "train_task_count": 2, "train_eval_task_overlap_count": 1,  # 交集只记数，不拒绝
                                               "eval_max_prompt_len": None}

            # 评测 attempt 只能绑定评测题包里的题；训练 attempt 照旧走训练题包
            eval_tid1, _ = _assignment(idm, assignment_from_dispatch, train_fx.manifest.record(TID1).model_dump(mode="json"), evaluation=True)
            with pytest.raises(AttemptAssignmentError, match="dispatch_not_authoritative"):
                service.attempt_assignments.bind(eval_tid1)  # TID1 不在评测题包里
            record = eval_fx.manifest.record(TID2).model_dump(mode="json")
            eval_tid2, identity = _assignment(idm, assignment_from_dispatch, record, evaluation=True)
            service.attempt_assignments.bind(eval_tid2)
            sample = SimpleNamespace(metadata={**record, **identity}, label=TID2)
            try:
                assert service._resolve_task(sample).task_id == TID2
                assert service._resolve_grading_spec(sample).task_id == TID2
            finally:
                service.lifecycle.exit_execution()
            assert service._face_for(eval_tid2) is service.eval_prepared_face
            train_tid2, _ = _assignment(idm, assignment_from_dispatch, train_fx.manifest.record(TID2).model_dump(mode="json"), evaluation=False)
            assert service._face_for(train_tid2) is service.prepared_face  # 同一道 TID2，训练平面走训练题包
            report = await service.close(reason="i21_eval_vertical")
            assert report.ok, report.to_dict()
        finally:
            if bringup.BringupService._startup_state != "CLOSED":
                await service.grading_queue.close(drain=False)
                service.app_handle.stop()

    await _with_engine(world, body)


async def test_eval_enabled_without_an_eval_package_is_rejected_at_startup_not_at_step_k(world, monkeypatch, tmp_path):
    async def body(port, _requests):
        import repoharness2.adapters.slime.bringup as bringup
        from repoharness2.adapters.slime.generate import StartupCheckError

        train_fx = _prepare(bringup, monkeypatch, tmp_path)
        for name in ("EVAL_PREPARED_TASKS_DIR", "EVAL_HOST_GRADING_ARTIFACT_PATH", "EVAL_HOST_GRADING_ARTIFACT_SHA256"):
            monkeypatch.setattr(bringup, name, None)
        monkeypatch.setattr(bringup, "EVAL_ONLY", False)
        args = _eval_args(_args(port, train_fx), train_fx)
        try:
            with pytest.raises(StartupCheckError, match="eval_prepared_tasks_missing"):
                await bringup.ensure_fa_started(args)
        except OSError as exc:
            pytest.skip(f"本机无 Qwen3-8B tokenizer 缓存且离线，跳过：{exc}")
        assert bringup.BringupService._startup_state == "FAILED" and bringup.BringupService._instance is None
        # 钩子没接线同样在启动期拒绝（否则评不了分的样本会让 miles 默认聚合对 None 求和而崩）
        eval_fx = prepare_synthetic(tmp_path / "evalpkg", iids=(IIDS[1],))
        _prepare(bringup, monkeypatch, tmp_path / "second")
        _eval_env(bringup, monkeypatch, eval_fx)
        with pytest.raises(StartupCheckError, match="eval_report_hook_not_wired"):
            await bringup.ensure_fa_started(_eval_args(_args(port, train_fx), eval_fx, custom_eval_rollout_log_function_path=None))

    await _with_engine(world, body)


async def test_eval_only_job_starts_without_a_training_package_and_refuses_training_dispatch(world, monkeypatch, tmp_path):
    async def body(port, _requests):
        import repoharness2.adapters.slime.bringup as bringup
        import repoharness2.adapters.slime.generate as generate_mod
        from repoharness2.adapters.miles import identity as idm
        from repoharness2.adapters.miles.attempt_assignment import AttemptAssignmentError, assignment_from_dispatch

        unused_fx = _prepare(bringup, monkeypatch, tmp_path, with_prepared=False)  # 不配置训练题包
        eval_fx = prepare_synthetic(tmp_path / "evalpkg")
        _eval_env(bringup, monkeypatch, eval_fx, eval_only=True)
        monkeypatch.setattr(generate_mod, "run_docker", SandboxRuntimeFakeDocker())
        args = _eval_args(_args(port, unused_fx), eval_fx, num_rollout=0, debug_rollout_only=True, fully_async=True,
                          rollout_global_dataset=False, prompt_data=None, skip_eval_before_train=False)  # 独立评测作业的启动形态
        try:
            await bringup.ensure_fa_started(args)
        except OSError as exc:
            pytest.skip(f"本机无 Qwen3-8B tokenizer 缓存且离线，跳过：{exc}")
        service = bringup.BringupService._instance
        try:
            assert service.prepared_face is None and service.eval_prepared_face is not None and service.task_specs == {}
            assert args.rh2_eval_only is True  # Rh2MilesGenerateFn 据此拒绝训练派发
            assert service.orchestrator._grading_spec_resolver is not None
            record = eval_fx.manifest.record(TID1).model_dump(mode="json")
            train_assignment, _ = _assignment(idm, assignment_from_dispatch, record, evaluation=False)
            with pytest.raises(AttemptAssignmentError, match="dispatch_not_authoritative"):
                service.attempt_assignments.bind(train_assignment)  # 训练平面没有题包
            eval_assignment, _ = _assignment(idm, assignment_from_dispatch, record, evaluation=True)
            service.attempt_assignments.bind(eval_assignment)
            report = await service.close(reason="i21_eval_only_vertical")
            assert report.ok, report.to_dict()
        finally:
            if bringup.BringupService._startup_state != "CLOSED":
                await service.grading_queue.close(drain=False)
                service.app_handle.stop()

    await _with_engine(world, body)
