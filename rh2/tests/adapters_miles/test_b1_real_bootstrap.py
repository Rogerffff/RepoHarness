"""B1（R6-ext）验收：miles 生产入口的真实 bootstrap——不手工塞 fake orchestrator。

链路（与验收标准逐字对应）::

    miles load_generate_function("...Rh2MilesGenerateFn")
    -> GenerateFnInput(args 无 rh2_orchestrator)
    -> Rh2MilesGenerateFn.__call__ 惰性 ensure_fa_started(args)
    -> 真实 BringupService（真 tokenizer/renderer/AnthropicAdapter 线程/
       capture wire/启动探针打真 HTTP 到 fake 引擎）构造真实 RolloutOrchestrator
    -> 首个调用进入 rh2 generate（editor 步进到 materialize 阶段）

    fake HTTP 引擎 = 本测试起的真 aiohttp 服务器，按 sglang-miles wire 形态
    应答 /generate（含 output_token_sampling_mask/_logprobs——
    args.rh2_engine_sampling_mask=True 时启动探针必须请求并收到新约定 tape）。

CPU 边界（与 test_bringup_vendor_only 同口径）：tokenizer 用本机 HF 缓存的
Qwen/Qwen3-8B（缺失即 skip）；docker 通道注入即抛的替身（CPU 无容器面，
materialize 失败按既有 fail-closed 收口为 abort 形状返回 miles Sample——
"进入 rh2 generate" 的验收点是 orchestrator 真实注入 + 9 步生命周期启动，
不是完成整条 rollout；完整 mask 纵链归 test_b2_mask_chain.py）。

单例隔离：BringupService 是进程级单代单例，monkeypatch 类状态 + 模块级
启动锁，测试结束还原并停 adapter 线程/评分队列，不泄漏到其他 bringup 测试。
"""

from __future__ import annotations

import asyncio
import sys
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest


def _strip_reference_slime_paths():
    removed = [p for p in sys.path if "reference/slime" in p]
    for p in removed:
        sys.path.remove(p)
    return removed


def _make_fake_engine_app(requests_log: list):
    """sglang-miles /generate 的最小 fake（真 aiohttp server，wire 形态应答）。"""

    from aiohttp import web

    async def generate(request: "web.Request"):
        payload = await request.json()
        requests_log.append(payload)
        # 固定两 token 应答；仅当请求带新顶层旗标才回 sampling-support tape
        # （忠实模拟 sglang-miles：旗标缺席则字段缺席）。
        meta = {
            "id": "rid-fake-probe",
            "weight_version": "7",
            "finish_reason": {"type": "stop"},
            "output_token_logprobs": [[-0.5, 11], [-0.25, 12]],
        }
        if payload.get("return_sampling_mask"):
            meta["output_token_sampling_mask"] = [[11, 5], [12, 9]]
            meta["output_token_sampling_logprobs"] = [-0.05, -0.01]
        return web.json_response({"text": "ok", "meta_info": meta})

    app = web.Application()
    app.router.add_post("/generate", generate)
    return app


async def test_b1_lazy_bootstrap_reaches_rh2_generate(world, monkeypatch, tmp_path):
    from aiohttp.test_utils import TestServer

    removed = _strip_reference_slime_paths()
    try:
        world.install_sglang_stub()
        import repoharness2.adapters.slime.bringup as bringup
        import repoharness2.adapters.slime.generate as generate_mod
        from miles.rollout.base_types import GenerateFnInput, GenerateFnOutput
        from miles.rollout.inference_rollout.compatibility import load_generate_function

        # -- fake 引擎（真 HTTP）先起，端口进 args --------------------------
        engine_requests: list[dict] = []
        server = TestServer(_make_fake_engine_app(engine_requests))
        await server.start_server()

        # -- bringup 环境收口（同 test_bringup_vendor_only）+ 单例隔离 ------
        monkeypatch.setattr(bringup, "ARTIFACT_DIR", tmp_path / "artifacts")
        monkeypatch.setattr(bringup, "ADAPTER_BIND_HOST", "127.0.0.1")
        monkeypatch.setattr(bringup, "ADAPTER_PUBLIC_HOST", "127.0.0.1")
        monkeypatch.setattr(bringup, "ADAPTER_PORT", 0)
        monkeypatch.setattr(bringup, "HARNESS_KIND", "simple")  # CPU：无 CC 二进制
        monkeypatch.setattr(bringup.BringupService, "_instance", None)
        monkeypatch.setattr(bringup.BringupService, "_startup_state", "NEW")
        monkeypatch.setattr(bringup.BringupService, "_startup_error", None)
        monkeypatch.setattr(bringup, "_SERVICE_LOCK", asyncio.Lock())
        monkeypatch.setenv("HF_HUB_OFFLINE", "1")

        # docker 通道替身：CPU 无容器面，materialize 必须确定性快速失败
        # （而不是真去拉 SWE 镜像）；abort 收口正是被验收的 fail-closed 路径。
        async def _no_docker(*args, input_bytes=None):
            raise FileNotFoundError("docker disabled in CPU bootstrap test")

        monkeypatch.setattr(generate_mod, "run_docker", _no_docker)

        # -- miles 侧入口：loader -> GenerateFnInput（args 无 rh2_orchestrator）
        fn = load_generate_function(
            "repoharness2.adapters.miles.generate_fn.Rh2MilesGenerateFn"
        )
        assert isinstance(fn, world.Rh2MilesGenerateFn)

        args = Namespace(
            hf_checkpoint="Qwen/Qwen3-8B",
            sglang_router_ip="127.0.0.1",
            sglang_router_port=server.port,
            rollout_max_context_len=0,
            sglang_tool_call_parser=None,
            sglang_reasoning_parser=None,
            # ensure_fa_started 的 FA 采样配方面（build_fa_sampling_params）
            rollout_temperature=1.0,
            rollout_top_p=0.95,
            rollout_max_response_len=64,
            # B2 请求侧二选一：目标引擎 = sglang-miles（新顶层约定）
            rh2_engine_sampling_mask=True,
            rollout_top_k=20,
        )

        service = None
        try:
            # 任务面 = bringup 冻结 8 题（真实 task_resolver 按 instance_id 查）
            frozen_iids = sorted(
                pair.instance_id for pair in bringup.bundles.load_bundle_pairs()
            )
            sample = world.mk_miles_input(index=0, group_index=0)
            sample.metadata["instance_id"] = frozen_iids[0]
            gi = GenerateFnInput(
                state=SimpleNamespace(args=args),
                sample=sample,
                sampling_params={
                    "temperature": 1.0,
                    "top_p": 0.95,
                    "top_k": 20,
                    "max_new_tokens": 64,
                },
                evaluation=False,
            )
            try:
                out = await fn(gi)
            except OSError as exc:  # tokenizer 缓存缺失且离线——环境问题
                pytest.skip(f"本机无 Qwen3-8B tokenizer 缓存且离线，跳过：{exc}")
            service = bringup.BringupService._instance

            # ① bootstrap 真实发生：orchestrator 由 bringup 构造并注入 args
            assert service is not None and service.orchestrator is not None
            assert args.rh2_orchestrator is service.orchestrator
            assert type(args.rh2_orchestrator).__name__ == "RolloutOrchestrator"
            assert args.rh2_sampling_params == {
                "temperature": 1.0, "top_p": 0.95, "max_new_tokens": 64,
            }

            # ② 启动探针走了新 sampling-mask 约定（请求侧二选一，真 HTTP 证据）
            assert engine_requests, "启动探针没有打到 fake 引擎"
            probe_payload = engine_requests[0]
            assert probe_payload.get("return_sampling_mask") is True
            assert "return_top_p_token_ids" not in (
                probe_payload["sampling_params"].get("custom_params") or {}
            )
            assert probe_payload["sampling_params"]["top_k"] == 20
            assert service.probe_evidence["sampling_mask_supports"] == 2
            assert service.probe_evidence["sampling_mask_top_k"] == 20
            assert service.policy_version == "7"  # 引擎实测 weight_version

            # ③ 首个真实调用进入 rh2 generate：9 步生命周期已启动，CPU 无
            # docker 面按既有 fail-closed 收口为 abort 形状（不是
            # orchestrator_not_configured）
            assert isinstance(out, GenerateFnOutput)
            (aborted,) = out.samples
            assert isinstance(aborted, world.MS)
            assert aborted.status is world.MS.Status.ABORTED
            reason = (aborted.metadata or {})["abort_reason"]
            assert reason.startswith("rh2_materialize_failed"), reason
            assert "orchestrator_not_configured" not in reason
            audit = service.orchestrator.audits[0]
            assert "step1_custom_generate_invoked" in audit.steps
            # mask 链的 abort 占位不携带旧 slime 零宽 top-p tape 字段
            # （miles Sample 没有这两个字段，携带会被 canonicalize 拒绝）
            assert "rollout_top_p_token_ids" not in aborted.__dict__

            # ④ 幂等：第二次调用复用同一 orchestrator（无二代 bringup）
            sample2 = world.mk_miles_input(index=1, group_index=0)
            sample2.metadata["instance_id"] = frozen_iids[0]
            gi2 = GenerateFnInput(
                state=SimpleNamespace(args=args),
                sample=sample2,
                sampling_params=dict(gi.sampling_params),
                evaluation=False,
            )
            out2 = await fn(gi2)
            assert args.rh2_orchestrator is service.orchestrator
            assert isinstance(out2, GenerateFnOutput)
        finally:
            if service is not None:
                await service.grading_queue.close(drain=False)
                service.app_handle.stop()
            await server.close()
    finally:
        for p in removed:
            sys.path.append(p)


def test_b1_bootstrap_is_wired_from_generate_fn_source(world):
    """防回归哨兵：generate_fn 的 bootstrap 必须复用既有 ensure_fa_started
    （不新建抽象）。源码文本断言（与 spike 的源码事实断言测试同风格）。"""

    src = (
        Path(world.rh2_src) / "repoharness2" / "adapters" / "miles" / "generate_fn.py"
    ).read_text(encoding="utf-8")
    assert "ensure_fa_started" in src
    assert "BringupService(" not in src  # 只走单例入口，不自建第二代构造路径
