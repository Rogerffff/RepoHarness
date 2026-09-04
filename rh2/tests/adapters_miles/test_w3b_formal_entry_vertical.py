"""F1（codex Wave3 复核）：`fa_formal` 真实顶层入口纵切——旧的无条件 `raise RuntimeError("fa_formal 暂禁…")`
挡板已删除（移除条件 W1b + W3a + W3b + W4 已满足；D0-4 不建代码级 owner 闸门），本文件证明：

1. 真实 `ensure_fa_started(args)`（miles 生产入口的启动引导）在 `RH2_EXECUTION_MODE=fa_formal` 下走通
   prepared task face（attempt 绑定解析）+ grading manager（grader profile）+ egress relay + verify +
   RolloutOrchestrator（fa_formal、sandbox profile、finalization store、屏障）组装，并把 orchestrator /
   sampling params / attempt registry 挂到 args；不经 fa_audit_only 绕过；
2. 每个真实必需配置缺失仍 typed 停止：缺 prepared 产物（select_task_face_mode）、版本契约关闭
   （validate_execution_config）、启动前验证不过（_start_sandbox_runtime）——都不新建 approval manifest。

链路与 test_b1_real_bootstrap 同：真 tokenizer/renderer/adapter 线程/capture wire/启动探针打真 HTTP 到 fake 引擎；
docker 面用 SandboxRuntimeFakeDocker（relay/verify/attempt 网络替身）。tokenizer 缓存缺失即 skip。
"""

from __future__ import annotations

import asyncio
import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))
from sandbox_test_support import SandboxRuntimeFakeDocker  # noqa: E402
from test_b1_real_bootstrap import _make_fake_engine_app, _strip_reference_slime_paths  # noqa: E402
from w1b_synthetic_tasks import TID1, TID2, prepare_synthetic  # noqa: E402


def _prepare(bringup, monkeypatch, tmp_path, *, with_prepared: bool = True, real_versions: str = "1"):
    from slime.agent.adapters import common as slime_common

    fx = prepare_synthetic(tmp_path)
    monkeypatch.setattr(slime_common, "_rh2_capture_wire_installed", False, raising=False)
    monkeypatch.setattr(slime_common, "_rh2_capture_wire_registry", None, raising=False)
    monkeypatch.setattr(bringup, "ARTIFACT_DIR", tmp_path / "artifacts")
    monkeypatch.setattr(bringup, "ADAPTER_BIND_HOST", "127.0.0.1")
    monkeypatch.setattr(bringup, "ADAPTER_PUBLIC_HOST", "127.0.0.1")
    monkeypatch.setattr(bringup, "ADAPTER_PORT", 0)
    monkeypatch.setattr(bringup, "HARNESS_KIND", "simple")  # CPU：无 CC 二进制
    monkeypatch.setattr(bringup, "EXECUTION_MODE", "fa_formal")
    if with_prepared:
        monkeypatch.setattr(bringup, "PREPARED_TASKS_DIR", str(fx.prepared_dir))
        monkeypatch.setattr(bringup, "PREPARED_TASKS_MANIFEST_SHA256", fx.manifest_sha256)
        monkeypatch.setattr(bringup, "HOST_GRADING_ARTIFACT_PATH", str(fx.host_path))
        monkeypatch.setattr(bringup, "HOST_GRADING_ARTIFACT_SHA256", fx.manifest.host_grading_artifact_sha256)
    else:
        monkeypatch.setattr(bringup, "PREPARED_TASKS_DIR", None)
    monkeypatch.setattr(bringup.BringupService, "_instance", None)
    monkeypatch.setattr(bringup.BringupService, "_startup_state", "NEW")
    monkeypatch.setattr(bringup.BringupService, "_startup_error", None)
    monkeypatch.setattr(bringup, "_SERVICE_LOCK", asyncio.Lock())
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("RH2_REQUIRE_REAL_WEIGHT_VERSIONS", real_versions)
    monkeypatch.setenv("RH2_REJECT_CONTEXT_SHRINK", "1")
    monkeypatch.setenv("RH2_REJECT_NONZERO_HARNESS_EXIT", "1")
    monkeypatch.delenv("MILES_RH2_RUN_ID", raising=False)
    return fx


def _args(port: int, fx) -> Namespace:
    return Namespace(
        hf_checkpoint="Qwen/Qwen3-8B", sglang_router_ip="127.0.0.1", sglang_router_port=port,
        rollout_max_context_len=0, sglang_tool_call_parser=None, sglang_reasoning_parser=None,
        rollout_temperature=1.0, rollout_top_p=0.95, rollout_max_response_len=64,
        rh2_engine_sampling_mask=True, rollout_top_k=20, prompt_data=str(fx.prompts_path),
        rollout_batch_size=2, n_samples_per_prompt=2, num_rollout=2,
    )


async def _with_engine(world, fn):
    from aiohttp.test_utils import TestServer

    removed = _strip_reference_slime_paths()
    try:
        world.install_sglang_stub()
        engine_requests: list[dict] = []
        server = TestServer(_make_fake_engine_app(engine_requests))
        await server.start_server()
        try:
            return await fn(server.port, engine_requests)
        finally:
            await server.close()
    finally:
        for p in removed:
            sys.path.append(p)


async def test_fa_formal_entry_assembles_prepared_face_grader_profile_relay_and_orchestrator(world, monkeypatch, tmp_path):
    async def body(port, engine_requests):
        import repoharness2.adapters.slime.bringup as bringup
        import repoharness2.adapters.slime.generate as generate_mod
        from repoharness2.adapters.miles import identity as idm
        from repoharness2.adapters.miles.attempt_assignment import assignment_from_dispatch
        from repoharness2.adapters.slime.generate import RolloutOrchestrator

        fx = _prepare(bringup, monkeypatch, tmp_path)
        docker = SandboxRuntimeFakeDocker()
        monkeypatch.setattr(generate_mod, "run_docker", docker)
        args = _args(port, fx)
        try:
            await bringup.ensure_fa_started(args)  # miles 生产入口的启动引导（Rh2MilesGenerateFn 首调用即此）
        except OSError as exc:
            pytest.skip(f"本机无 Qwen3-8B tokenizer 缓存且离线，跳过：{exc}")
        service = bringup.BringupService._instance
        assert service is not None and bringup.BringupService._startup_state == "RUNNING"
        try:
            # ① 任务面 = prepared 链（attempt 绑定解析），不是 v1 八题
            assert service.prepared_face is not None and service.pairs is None
            assert set(service.task_specs) == {TID1, TID2}
            assert args.rh2_attempt_assignments is service.attempt_assignments
            # ② orchestrator = fa_formal 正式链，带唯一正式 rollout profile / relay / run 级 digest / 屏障 / store
            orch = service.orchestrator
            assert isinstance(orch, RolloutOrchestrator) and args.rh2_orchestrator is orch
            assert orch._mode == "fa_formal" and orch.config.require_real_weight_versions is True
            assert orch._sandbox_profile is service.rollout_profile and orch._egress_relay is service.egress_relay
            assert orch._runtime_profile_digest == service.runtime_profile_digest
            assert orch._runtime_barrier is not None and orch._finalization_store is not None
            assert orch._grading_spec_resolver is not None  # prepared 链的评分材料按 attempt 绑定解析
            # ③ 版本契约来自引擎实测（fake 引擎 weight_version=7），不是静态哨兵
            assert service.policy_version == "7" and orch.config.policy_version == "7"
            assert engine_requests and engine_requests[0].get("return_sampling_mask") is True
            # ④ grader profile 注入评分面；relay 起了、verify 记录写盘一次、样本盖章键 = run 级 digest
            assert service.grading_manager.config.sandbox_profile is service.grader_profile
            assert service.egress_relay is not None and service.harness_adapter_url == "http://rh2-egress-relay:18001"
            record = json.loads((tmp_path / "artifacts" / "runtime_profile.json").read_text())
            assert record["ok"] and record["execution_mode"] == "fa_formal"
            assert record["runtime_profile_digest"] == service.runtime_profile_digest
            evidence = json.loads((tmp_path / "artifacts" / "startup_evidence.json").read_text())
            assert evidence["runtime_profile_digest"] == service.runtime_profile_digest
            assert isinstance(service.verified_router_workers, tuple)  # F3 接缝：启动核对过的 worker 集合
            # ⑤ 真实 resolver 只认 attempt 绑定（prepared 链纪律仍在）
            rec = fx.manifest.record(TID1).model_dump(mode="json")
            identity = {
                idm.GROUP_ID_KEY: "miles_g0", idm.GROUP_INDEX_KEY: 0, idm.EXECUTION_ID_KEY: "miles_g0_m0",
                idm.MEMBER_SLOT_KEY: 0, idm.ATTEMPT_ID_KEY: "miles_g0_m0#p1-01234567", idm.ATTEMPT_SEQ_KEY: 1,
            }
            service.attempt_assignments.bind(assignment_from_dispatch(rec, identity))
            from types import SimpleNamespace

            sample = SimpleNamespace(metadata={**rec, **identity}, label=TID1)
            try:
                assert service._resolve_task(sample).task_id == TID1  # 登记在飞执行（W5a），下面显式注销
                gs = service._resolve_grading_spec(sample)
            finally:
                service.lifecycle.exit_execution()  # 与 _write_execution_audit 的 finally 同一注销点
            assert gs.trusted_setup_script and gs.candidate_test_script  # F2：prepared 链评分材料已拆分
            # ⑥ 正常关停：relay 删掉、无残留
            report = await service.close(reason="w3b_formal_vertical")
            assert report.ok, report.to_dict()
            assert service.egress_relay is None
        finally:
            if bringup.BringupService._startup_state != "CLOSED":
                await service.grading_queue.close(drain=False)
                service.app_handle.stop()

    await _with_engine(world, body)


async def test_fa_formal_entry_rejects_missing_prepared_artifacts_typed(world, monkeypatch, tmp_path):
    async def body(port, _requests):
        import repoharness2.adapters.slime.bringup as bringup

        fx = _prepare(bringup, monkeypatch, tmp_path, with_prepared=False)
        with pytest.raises(RuntimeError, match="fa_formal 缺 RH2_PREPARED_TASKS_DIR") as ei:
            await bringup.ensure_fa_started(_args(port, fx))
        assert "OSError" not in repr(ei.value)
        assert bringup.BringupService._startup_state == "FAILED" and bringup.BringupService._instance is None

    await _with_engine(world, body)


async def test_fa_formal_entry_rejects_version_contract_off_and_rolls_back_relay(world, monkeypatch, tmp_path):
    async def body(port, _requests):
        import repoharness2.adapters.slime.bringup as bringup
        import repoharness2.adapters.slime.generate as generate_mod

        fx = _prepare(bringup, monkeypatch, tmp_path, real_versions="0")
        docker = SandboxRuntimeFakeDocker()
        monkeypatch.setattr(generate_mod, "run_docker", docker)
        try:
            with pytest.raises(bringup.StartupCheckError, match="fa_formal_requires_real_weight_versions"):
                await bringup.ensure_fa_started(_args(port, fx))
        except OSError as exc:
            pytest.skip(f"本机无 Qwen3-8B tokenizer 缓存且离线，跳过：{exc}")
        assert bringup.BringupService._startup_state == "FAILED"
        # 启动事务回滚：relay 已起又被停掉，label 残留查询为空
        assert any(c[0] == "rm" and c[-1].startswith("rh2-egress-relay-") for c in docker.calls)
        assert not any(name for name, c in docker.containers.items() if not c["removed"])

    await _with_engine(world, body)


async def test_fa_formal_entry_rejects_sandbox_verification_failure(world, monkeypatch, tmp_path):
    async def body(port, _requests):
        import repoharness2.adapters.slime.bringup as bringup
        import repoharness2.adapters.slime.generate as generate_mod

        fx = _prepare(bringup, monkeypatch, tmp_path)
        docker = SandboxRuntimeFakeDocker(probe_overrides={"HIDDEN_0": "READABLE:/root"})
        monkeypatch.setattr(generate_mod, "run_docker", docker)
        try:
            with pytest.raises(bringup.StartupCheckError, match="sandbox_profile_verification_failed"):
                await bringup.ensure_fa_started(_args(port, fx))
        except OSError as exc:
            pytest.skip(f"本机无 Qwen3-8B tokenizer 缓存且离线，跳过：{exc}")
        record = json.loads((tmp_path / "artifacts" / "runtime_profile.json").read_text())
        assert record["ok"] is False and any("隐藏路径" in f for f in record["failures"])
        assert bringup.BringupService._startup_state == "FAILED"

    await _with_engine(world, body)
