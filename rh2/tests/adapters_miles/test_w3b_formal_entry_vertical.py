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


def _args(port: int, fx, *, rollout_num_gpus: int = 2, rollout_num_gpus_per_engine: int = 2) -> Namespace:
    """miles args 的最小面。

    `rollout_num_gpus` / `rollout_num_gpus_per_engine` 是 abort 核对集合的**预期 engine 数**来源
    （codex Wave3 §9.3：engine 数 = 前者 // 后者）；默认 2 // 2 = 1 个 engine，与 `_with_engine`
    默认只登记一个 worker（fake server 自己）一致。多 engine 反例按需覆盖这两个值。"""

    return Namespace(
        hf_checkpoint="Qwen/Qwen3-8B", sglang_router_ip="127.0.0.1", sglang_router_port=port,
        rollout_max_context_len=0, sglang_tool_call_parser=None, sglang_reasoning_parser=None,
        rollout_temperature=1.0, rollout_top_p=0.95, rollout_max_response_len=64,
        rh2_engine_sampling_mask=True, rollout_top_k=20, prompt_data=str(fx.prompts_path),
        rollout_batch_size=2, n_samples_per_prompt=2, num_rollout=2,
        rollout_num_gpus=rollout_num_gpus, rollout_num_gpus_per_engine=rollout_num_gpus_per_engine,
    )


async def _with_engine(world, fn, *, serve_worker_list: bool = True, extra_workers: tuple[str, ...] = ()):
    """起 fake 引擎（同时扮演 router）并把 `(port, engine_requests)` 交给 ``fn``。

    - ``serve_worker_list=True``：挂 `GET /list_workers`，默认只登记 fake server 自己（1 个 worker），
      `extra_workers` 可追加"另外注册的 engine"地址（多 engine 拓扑反例用）；
    - ``serve_worker_list=False``：不挂该路由 → 查询 404 → 启动核对拿不到集合（查询失败反例）。
    """

    from aiohttp.test_utils import TestServer

    removed = _strip_reference_slime_paths()
    try:
        world.install_sglang_stub()
        engine_requests: list[dict] = []
        worker_urls: list[str] | None = [] if serve_worker_list else None
        server = TestServer(_make_fake_engine_app(engine_requests, worker_urls=worker_urls))
        await server.start_server()
        if worker_urls is not None:  # server 起来才知道端口：自己 + 追加的 engine
            worker_urls[:] = [f"http://127.0.0.1:{server.port}", *extra_workers]
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
            # F3 接缝（codex Wave3 §9.3）：核对集合必须与固定 topology 的 engine 数**精确相等**，
            # 且已下发给 router client 作 abort 回退集合（下面 §7 组是专门的完整性反例）。
            assert service.verified_router_workers == (f"http://127.0.0.1:{args.sglang_router_port}",)
            assert service.router_workers.verified_workers == service.verified_router_workers
            assert evidence["router_workers"] == {
                "urls": list(service.verified_router_workers), "count": 1, "raw_count": 1,
                "expected_count": 1, "verified": True,
            }
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


# ---------------------------------------------------------------------------
# codex Wave3 §9.3：abort 核对集合的完整性必须在**生产接缝**（真实 ensure_fa_started）上证明
#
# 为什么这些反例不能用 MilesRouterWorkerClient 的单元测试代替：client 只负责"对给定集合广播"，
# 集合是否等于全部 engine 由 bringup 启动核对决定。集合不完整时 client 照样会对每个 URL 拿到
# 2xx 并报 delivered——真正持有 rid 的那台 engine 却从没收到 abort，请求继续占 SGLang 槽位。
# ---------------------------------------------------------------------------


def _startup_evidence(tmp_path) -> dict:
    return json.loads((tmp_path / "artifacts" / "startup_evidence.json").read_text())


@pytest.mark.parametrize(
    ("shape", "gpus", "per_engine", "extra_workers", "expected", "actual"),
    [
        # 预期 2 个 engine（4 卡 // 每 engine 2 卡），router 只登记 1 个：启动那刻另一台还没注册，
        # 此后它注册并可能持有 rid——把这份集合当完整集合会误报 delivered。
        ("too_few", 4, 2, (), 2, 1),
        # 反方向同样拒绝：预期 1 个，router 却登记 2 个（陌生 worker，可能属于别的 run 或别的模型组）。
        ("too_many", 2, 2, ("http://127.0.0.1:59999",), 1, 2),
    ],
    ids=["too_few", "too_many"],
)
async def test_fa_formal_startup_rejects_router_worker_count_mismatch(
    world, monkeypatch, tmp_path, shape, gpus, per_engine, extra_workers, expected, actual
):
    """反例：worker 数量与固定 topology 不符（多或少）→ typed StartupCheckError，**不进入 RUNNING**，
    且证据里那份集合必须是 `verified: false`（绝不当作 abort 回退集合下发）。"""

    async def body(port, _requests):
        import repoharness2.adapters.slime.bringup as bringup
        import repoharness2.adapters.slime.generate as generate_mod

        fx = _prepare(bringup, monkeypatch, tmp_path)
        monkeypatch.setattr(generate_mod, "run_docker", SandboxRuntimeFakeDocker())
        args = _args(port, fx, rollout_num_gpus=gpus, rollout_num_gpus_per_engine=per_engine)
        try:
            with pytest.raises(bringup.StartupCheckError, match="router_workers_unverified") as ei:
                await bringup.ensure_fa_started(args)
        except OSError as exc:
            pytest.skip(f"本机无 Qwen3-8B tokenizer 缓存且离线，跳过：{exc}")
        assert f"预期 {expected} 个 engine" in str(ei.value) and f"实际登记 {actual} 个" in str(ei.value)
        assert bringup.BringupService._startup_state == "FAILED"  # 不进入 RUNNING
        assert bringup.BringupService._instance is None
        row = _startup_evidence(tmp_path)["router_workers"]
        assert row["verified"] is False and row["count"] == actual and row["expected_count"] == expected

    await _with_engine(world, body, extra_workers=extra_workers)


async def test_fa_formal_startup_rejects_unavailable_router_worker_list(world, monkeypatch, tmp_path):
    """反例：router 不回 worker 列表（`/list_workers` 与 `/workers` 都 404）→ 查询失败 ≠ 空集合，
    不能声称核对过 → typed StartupCheckError，不进入 RUNNING。

    这正是 §9.3 那条可达时序的入口：此前这里只把异常写进 evidence 就放行，abort 时实时列表再失败
    就会退回一份**从未核对过**（甚至为空）的集合。"""

    async def body(port, _requests):
        import repoharness2.adapters.slime.bringup as bringup
        import repoharness2.adapters.slime.generate as generate_mod

        fx = _prepare(bringup, monkeypatch, tmp_path)
        monkeypatch.setattr(generate_mod, "run_docker", SandboxRuntimeFakeDocker())
        try:
            with pytest.raises(bringup.StartupCheckError, match="router_workers_unverified") as ei:
                await bringup.ensure_fa_started(_args(port, fx))
        except OSError as exc:
            pytest.skip(f"本机无 Qwen3-8B tokenizer 缓存且离线，跳过：{exc}")
        assert "查询失败" in str(ei.value)
        assert bringup.BringupService._startup_state == "FAILED"
        assert bringup.BringupService._instance is None
        row = _startup_evidence(tmp_path)["router_workers"]
        assert row["verified"] is False and "404" in row["error"] and "urls" not in row

    await _with_engine(world, body, serve_worker_list=False)


async def test_fa_formal_startup_accepts_complete_two_engine_worker_set(world, monkeypatch, tmp_path):
    """正例：预期 2 个 engine、router 也登记 2 个 → 进入 RUNNING，**且只有此时**才把这份集合
    下发给 router client 作 abort 回退目标（`registry.engine_abort` 就是该 client 的广播函数）。

    单 engine（预期 1、返回 1）的正常路径由本文件第一个纵切用例覆盖。"""

    other = "http://127.0.0.1:59999"  # 第二台 engine 的登记地址（数量核对只看集合，不在启动时逐台探活）

    async def body(port, _requests):
        import repoharness2.adapters.slime.bringup as bringup
        import repoharness2.adapters.slime.generate as generate_mod

        fx = _prepare(bringup, monkeypatch, tmp_path)
        monkeypatch.setattr(generate_mod, "run_docker", SandboxRuntimeFakeDocker())
        args = _args(port, fx, rollout_num_gpus=4, rollout_num_gpus_per_engine=2)  # 预期 2 个 engine
        try:
            await bringup.ensure_fa_started(args)
        except OSError as exc:
            pytest.skip(f"本机无 Qwen3-8B tokenizer 缓存且离线，跳过：{exc}")
        service = bringup.BringupService._instance
        assert service is not None and bringup.BringupService._startup_state == "RUNNING"
        try:
            both = (f"http://127.0.0.1:{port}", other)
            assert service.verified_router_workers == both
            assert service.router_workers.verified_workers == both
            assert service.registry.engine_abort.__self__ is service.router_workers
            row = _startup_evidence(tmp_path)["router_workers"]
            assert row == {"urls": list(both), "count": 2, "raw_count": 2, "expected_count": 2, "verified": True}
        finally:
            if bringup.BringupService._startup_state != "CLOSED":
                await service.close(reason="w3b_worker_set_vertical")

    await _with_engine(world, body, extra_workers=(other,))
