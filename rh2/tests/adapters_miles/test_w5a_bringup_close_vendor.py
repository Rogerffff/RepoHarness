"""W5a：真实 BringupService（vendor slime：真 tokenizer/renderer/AnthropicAdapter 线程/
capture wire/评分队列）的关停链——线程真停、端口真关、单例入口 sticky CLOSED。

CPU 边界与 test_bringup_vendor_only 同口径：只走 __init__（async_start 的启动探针需要
真实 SGLang），tokenizer 用本机 HF 缓存的 Qwen/Qwen3-8B（缺失即 skip）。
"""

from __future__ import annotations

import asyncio
import json
import socket
import sys
from argparse import Namespace

import pytest


def _strip_reference_slime_paths():
    removed = [p for p in sys.path if "reference/slime" in p]
    for p in removed:
        sys.path.remove(p)
    return removed


async def test_w5a_real_bringup_service_close_stops_thread_and_rejects_get(world, monkeypatch, tmp_path):
    removed = _strip_reference_slime_paths()
    service = None
    try:
        import repoharness2.adapters.slime.bringup as bringup
        from repoharness2.shutdown import ServiceClosedError

        monkeypatch.setattr(bringup, "ARTIFACT_DIR", tmp_path / "artifacts")
        monkeypatch.setattr(bringup, "ADAPTER_BIND_HOST", "127.0.0.1")
        monkeypatch.setattr(bringup, "ADAPTER_PUBLIC_HOST", "127.0.0.1")
        monkeypatch.setattr(bringup, "ADAPTER_PORT", 0)
        monkeypatch.setattr(bringup.BringupService, "_instance", None)
        monkeypatch.setattr(bringup.BringupService, "_startup_state", "NEW")
        monkeypatch.setattr(bringup.BringupService, "_startup_error", None)
        monkeypatch.setattr(bringup, "_SERVICE_LOCK", asyncio.Lock())
        monkeypatch.setenv("HF_HUB_OFFLINE", "1")
        monkeypatch.setenv("RH2_SHUTDOWN_INFLIGHT_GRACE_SEC", "0.1")

        args = Namespace(
            hf_checkpoint="Qwen/Qwen3-8B",
            sglang_router_ip="127.0.0.1",
            sglang_router_port=59999,  # __init__ 只拼 URL，不发请求
            rollout_max_context_len=0,
            sglang_tool_call_parser=None,
            sglang_reasoning_parser=None,
            # 资源闭包上界估算读的 miles 参数
            rollout_batch_size=2,
            n_samples_per_prompt=2,
            num_rollout=2,
            rollout_max_response_len=512,
        )
        try:
            service = bringup.BringupService(args)
        except OSError as exc:
            pytest.skip(f"本机无 Qwen3-8B tokenizer 缓存且离线，跳过：{exc}")
        assert service.shutdown_timeouts.inflight_grace == 0.1  # env 旋钮真进配置
        # 模拟 get() 已把它登记成单例（不跑 async_start）
        bringup.BringupService._instance = service
        bringup.BringupService._startup_state = "RUNNING"
        port = service.app_handle.port
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            pass  # adapter 线程在跑，端口可连

        report = await service.close(reason="vendor_close_test")
        assert report.ok, report.to_dict()
        assert not service.app_handle.thread.is_alive()
        with pytest.raises(OSError):
            socket.create_connection(("127.0.0.1", port), timeout=1)  # 端口真关
        assert service.registry.closed and service.grading_manager.closed
        assert report.step("grading_queue").status == "skipped"  # 从未 start：如实 skipped
        assert report.step("adapter_http").status == "ok"
        assert bringup.BringupService._startup_state == "CLOSED"
        with pytest.raises(ServiceClosedError) as ei:
            await bringup.BringupService.get(args)
        assert ei.value.face == "bringup_get"
        assert (await bringup.close_bringup_service()) is report  # 幂等入口
        artifacts = tmp_path / "artifacts"
        written = json.loads((artifacts / "shutdown_report.json").read_text(encoding="utf-8"))
        assert written["ok"] is True and written["trigger"] == "owner_close"
        closure = json.loads((artifacts / "resource_closure.json").read_text(encoding="utf-8"))
        assert closure["memory_upper_bound"]["inputs"]["max_attempts_retained"] == 2 * 2 * 2 * 2
        assert closure["memory_upper_bound"]["inputs"]["max_concurrent_executions"] == 4
        assert closure["fsync_latency"]["samples"] == 16
        assert closure["growth_collections"]["registry_hooks"]["length"] == 0
        events = [json.loads(line) for line in (artifacts / "bringup_events.jsonl").read_text(encoding="utf-8").splitlines()]
        assert [e["event"] for e in events] == ["shutdown_started", "shutdown_completed"]
    finally:
        if service is not None and service.app_handle.thread.is_alive():
            service.app_handle.stop()
        for p in removed:
            sys.path.append(p)
