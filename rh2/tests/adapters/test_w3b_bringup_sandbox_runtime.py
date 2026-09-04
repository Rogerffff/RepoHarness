"""W3b：bringup 接线（替身 docker，不需要 daemon）+ codex Wave3 复核 F4（egress 清理失败不得假绿）。

- 非 s1 模式：`BringupService` 解析两个 profile（非法 env 在任何资源型副作用前就拒）、harness 侧代理地址
  改为 relay 别名、grader profile 注入 GradingManagerConfig；
- `_start_sandbox_runtime`：起 relay → 同一 verify 入口 → run 级记录写 ARTIFACT_DIR/runtime_profile.json
  （digest 与 startup evidence / orchestrator 一致）；验证不过 → StartupCheckError 且启动回滚停掉 relay；
- 关停链 `egress_runtime` 步：删残留 attempt 网络 + relay；
- F4 反例：network ls 失败 / network rm 失败 / 正常关停 relay rm 失败 / relay ready-timeout 后 rm 失败 /
  启动回滚 relay rm 失败——每条都不得给出 ok=true 或丢掉 handle/证据，且 label 残留查询看得见残留；
- s1_compat：profile 不接（冻结回退面零改变）。

任务面用冻结 v1 八题（legacy bring-up 路径：prepared 链要 import miles，那是 tests/adapters_miles lane 的事）。
tokenizer 缓存缺失即 skip（与 tests/adapters_miles 的 bringup 测试同口径）。
"""

from __future__ import annotations

import asyncio
import functools
import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tests/
from sandbox_test_support import SandboxRuntimeFakeDocker  # noqa: E402

from repoharness2.adapters.slime import sandbox_profile as sp  # noqa: E402


def _service(monkeypatch, tmp_path, *, mode: str, docker: SandboxRuntimeFakeDocker | None):
    import repoharness2.adapters.slime.bringup as bringup
    import repoharness2.adapters.slime.generate as generate_mod
    from slime.agent.adapters import common as slime_common

    # capture wire 进程级单代：同进程第二个 BringupService 会被所有权检查拒绝（勘误 4）。
    # 本文件每个测试各起一个 service，测前把 wire 归属记录清掉（与 wire 语义无关的接线测试）。
    monkeypatch.setattr(slime_common, "_rh2_capture_wire_installed", False, raising=False)
    monkeypatch.setattr(slime_common, "_rh2_capture_wire_registry", None, raising=False)
    monkeypatch.setattr(bringup, "ARTIFACT_DIR", tmp_path / "artifacts")
    monkeypatch.setattr(bringup, "ADAPTER_BIND_HOST", "127.0.0.1")
    monkeypatch.setattr(bringup, "ADAPTER_PUBLIC_HOST", "127.0.0.1")
    monkeypatch.setattr(bringup, "ADAPTER_PORT", 0)
    monkeypatch.setattr(bringup, "EXECUTION_MODE", mode)
    monkeypatch.setattr(bringup, "PREPARED_TASKS_DIR", None)  # legacy v1 八题任务面
    monkeypatch.setattr(bringup.BringupService, "_instance", None)
    monkeypatch.setattr(bringup.BringupService, "_startup_state", "NEW")
    monkeypatch.setattr(bringup.BringupService, "_startup_error", None)
    monkeypatch.setattr(bringup, "_SERVICE_LOCK", asyncio.Lock())
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.delenv("MILES_RH2_RUN_ID", raising=False)
    if docker is not None:
        monkeypatch.setattr(generate_mod, "run_docker", docker)
    args = Namespace(
        hf_checkpoint="Qwen/Qwen3-8B", sglang_router_ip="127.0.0.1", sglang_router_port=59999,
        rollout_max_context_len=0, sglang_tool_call_parser=None, sglang_reasoning_parser=None,
        rollout_batch_size=2, n_samples_per_prompt=2, num_rollout=2, rollout_max_response_len=512,
    )
    try:
        service = bringup.BringupService(args)
    except OSError as exc:
        pytest.skip(f"本机无 Qwen3-8B tokenizer 缓存且离线，跳过：{exc}")
    return bringup, service


async def _no_engine_probe():
    return None


async def test_audit_only_bringup_starts_relay_verifies_and_writes_run_record(monkeypatch, tmp_path):
    docker = SandboxRuntimeFakeDocker()
    bringup, service = _service(monkeypatch, tmp_path, mode="fa_audit_only", docker=docker)
    closed = False
    try:
        assert service.rollout_profile is not None and service.grader_profile is not None
        docker.bind_profiles(service.rollout_profile, service.grader_profile)
        # harness 侧代理地址 = relay 别名；上游 = 宿主 adapter 实际端口
        assert service.harness_adapter_url == "http://rh2-egress-relay:18001"
        assert service.rollout_profile.model_proxy_upstream_port == service.app_handle.port
        assert service.grading_manager.config.sandbox_profile is service.grader_profile
        assert service.runtime_profile_digest == sp.runtime_profile_digest(service.rollout_profile, service.grader_profile)
        assert service.task_specs  # 冻结 v1 八题任务面

        await service._start_sandbox_runtime()
        assert service.egress_relay is not None and service.egress_relay.alias == "rh2-egress-relay"
        assert service.egress_relay.repo_digests == (sp.RELAY_IMAGE_DEFAULT,)  # R2：实际镜像 digest 已核对
        record = json.loads((tmp_path / "artifacts" / "runtime_profile.json").read_text())
        assert record["ok"] and record["runtime_profile_digest"] == service.runtime_profile_digest
        assert record["probe_image"] in {spec.image for spec in service.task_specs.values()}
        assert record["harness_adapter_url"] == service.harness_adapter_url and record["execution_mode"] == "fa_audit_only"
        assert record["rollout"]["checks"]["prelaunch"]["ok"] and record["grader"]["checks"]["prelaunch"]["ok"]
        assert record["relay"]["repo_digests"] == [sp.RELAY_IMAGE_DEFAULT]
        relay_run = next(c for c in docker.calls if c[0] == "run" and service.egress_relay.container_name in c)
        assert "--read-only" in relay_run and "65534:65534" in relay_run and "rh2.run_id=" in " ".join(relay_run)
        assert sp.RELAY_IMAGE_DEFAULT in relay_run  # digest-pinned 引用直接下发 docker run
        # 关停链：egress_runtime 步删 relay（fake 记 rm），报告 ok
        report = await service.close(reason="w3b_test")
        assert report.ok, report.to_dict()
        step = next(s for s in report.steps if s.name == "egress_runtime")
        assert step.status == "ok" and service.egress_relay is None
        assert report.residue["egress_cleanup_failures"] == [] and report.residue["egress_relay_left"] is None
        assert any(c[0] == "rm" and c[-1].startswith("rh2-egress-relay-") for c in docker.calls)
        closed = True
    finally:
        if not closed:
            service.app_handle.stop()


async def test_verification_failure_blocks_startup_and_rollback_stops_relay(monkeypatch, tmp_path):
    docker = SandboxRuntimeFakeDocker(probe_overrides={"NET_forbidden_0": "CONNECTED"})
    bringup, service = _service(monkeypatch, tmp_path, mode="fa_audit_only", docker=docker)
    rolled_back = False
    try:
        docker.bind_profiles(service.rollout_profile, service.grader_profile)
        monkeypatch.setattr(service, "_run_startup_checks", _no_engine_probe)
        with pytest.raises(bringup.StartupCheckError, match="sandbox_profile_verification_failed"):
            await service.async_start(service._profile_args)
        record = json.loads((tmp_path / "artifacts" / "runtime_profile.json").read_text())
        assert record["ok"] is False and any("egress 未阻断" in f for f in record["failures"])
        assert service.egress_relay is None  # 启动回滚停掉了 relay
        assert any(c[0] == "rm" and c[-1].startswith("rh2-egress-relay-") for c in docker.calls)
        rolled_back = True
    finally:
        if not rolled_back:  # async_start 的统一回滚已停 adapter 线程；只在未走到回滚时兜底
            service.app_handle.stop()


def test_invalid_profile_env_is_rejected_before_any_resource(monkeypatch, tmp_path):
    monkeypatch.setenv("RH2_SANDBOX_PIDS_LIMIT", "lots")
    with pytest.raises(sp.SandboxProfileError, match="sandbox_env_not_int"):
        _service(monkeypatch, tmp_path, mode="fa_audit_only", docker=None)


async def test_s1_compat_keeps_legacy_path_without_profile(monkeypatch, tmp_path):
    docker = SandboxRuntimeFakeDocker()
    bringup, service = _service(monkeypatch, tmp_path, mode="s1_compat", docker=docker)
    try:
        assert service.rollout_profile is None and service.grader_profile is None
        assert service.harness_adapter_url == service.adapter_url
        assert service.grading_manager.config.sandbox_profile is None
        await service._start_sandbox_runtime()
        assert service.egress_relay is None and not docker.calls
        assert not (tmp_path / "artifacts" / "runtime_profile.json").exists()
    finally:
        service.app_handle.stop()


# ---------------------------------------------------------------------------
# F4（codex Wave3 复核）：egress 清理失败不得报成正常关停；启动回滚不得忘记 handle
# ---------------------------------------------------------------------------


async def _started_service(monkeypatch, tmp_path, docker):
    bringup, service = _service(monkeypatch, tmp_path, mode="fa_audit_only", docker=docker)
    docker.bind_profiles(service.rollout_profile, service.grader_profile)
    await service._start_sandbox_runtime()
    assert service.egress_relay is not None
    return bringup, service


async def test_f4_attempt_network_remove_failure_marks_shutdown_not_ok_and_lists_failure(monkeypatch, tmp_path):
    docker = SandboxRuntimeFakeDocker()
    bringup, service = await _started_service(monkeypatch, tmp_path, docker)
    # 关停时本 run 还残留一张 attempt 网络，且守护进程拒绝删它（active endpoints）
    docker.state.networks["rh2-egress-leftover"] = "10.212.0.8/29"
    docker.state.network_rm_fail_for = ("rh2-egress-leftover",)
    report = await service.close(reason="f4_network_rm")
    assert report.ok is False and report.residue_free is False
    assert any("rh2-egress-leftover" in f for f in report.residue["egress_cleanup_failures"])
    step = next(s for s in report.steps if s.name == "egress_runtime")
    assert step.facts["failures"]  # 事实仍在 step facts 里（证据），同时进 residue（判据）
    assert report.residue["egress_relay_left"] is None  # relay 本身删掉了


async def test_f4_network_list_failure_is_residue_not_zero(monkeypatch, tmp_path):
    docker = SandboxRuntimeFakeDocker()
    bringup, service = await _started_service(monkeypatch, tmp_path, docker)
    docker.state.network_ls_fail = True
    report = await service.close(reason="f4_network_ls")
    assert report.ok is False
    assert "network_ls_failed" in report.residue["egress_cleanup_failures"]  # 查询失败 ≠ 零残留


async def test_f4_relay_remove_failure_on_normal_shutdown_marks_not_ok_keeps_handle_and_is_label_visible(monkeypatch, tmp_path):
    docker = SandboxRuntimeFakeDocker()
    bringup, service = await _started_service(monkeypatch, tmp_path, docker)
    relay_name = service.egress_relay.container_name
    run_id = service.egress_relay.run_id
    docker.relay_rm_fail = True
    report = await service.close(reason="f4_relay_rm")
    assert report.ok is False and report.residue["egress_relay_left"] == relay_name
    assert any(relay_name in f for f in report.residue["egress_cleanup_failures"])
    assert service.egress_relay is not None  # handle 不丢
    assert docker.containers_with_label(f"rh2.run_id={run_id}") == [relay_name]  # launch trap 的 label 残留查询看得见


async def test_f4_relay_ready_timeout_remove_failure_at_startup_keeps_evidence_and_first_cause(monkeypatch, tmp_path):
    docker = SandboxRuntimeFakeDocker(relay_never_ready=True, relay_rm_fail=True)
    bringup, service = _service(monkeypatch, tmp_path, mode="fa_audit_only", docker=docker)
    docker.bind_profiles(service.rollout_profile, service.grader_profile)
    monkeypatch.setattr(service, "_run_startup_checks", _no_engine_probe)
    monkeypatch.setattr(bringup, "start_egress_relay", functools.partial(sp.start_egress_relay, ready_timeout=0.3))
    rolled_back = False
    try:
        with pytest.raises(bringup.StartupCheckError, match="egress_relay_start_failed") as ei:
            await service.async_start(service._profile_args)
        assert "残留容器" in str(ei.value) and "egress_relay_not_ready" in str(ei.value)  # 首因 + 残留证据同在
        assert service.sandbox_startup_leftovers == (f"rh2-egress-relay-local-{__import__('os').getpid()}",)
        assert any(e.startswith("relay_leftover_containers") for e in service._startup_rollback_errors)
        assert docker.containers_with_label(f"rh2.run_id=local-{__import__('os').getpid()}") == list(service.sandbox_startup_leftovers)
        rolled_back = True
    finally:
        if not rolled_back:
            service.app_handle.stop()


async def test_f4_startup_rollback_relay_remove_failure_keeps_handle_and_does_not_mask_first_cause(monkeypatch, tmp_path):
    docker = SandboxRuntimeFakeDocker(probe_overrides={"NET_forbidden_0": "CONNECTED"}, relay_rm_fail=True)
    bringup, service = _service(monkeypatch, tmp_path, mode="fa_audit_only", docker=docker)
    docker.bind_profiles(service.rollout_profile, service.grader_profile)
    monkeypatch.setattr(service, "_run_startup_checks", _no_engine_probe)
    rolled_back = False
    try:
        with pytest.raises(bringup.StartupCheckError, match="sandbox_profile_verification_failed"):  # 首因不被回滚错误覆盖
            await service.async_start(service._profile_args)
        assert service.egress_relay is not None  # 删除失败 → handle 保留
        assert any(e.startswith("relay_stop:") for e in service._startup_rollback_errors)
        assert docker.containers_with_label(f"rh2.run_id={service.egress_relay.run_id}") == [service.egress_relay.container_name]
        rolled_back = True
    finally:
        if not rolled_back:
            service.app_handle.stop()
