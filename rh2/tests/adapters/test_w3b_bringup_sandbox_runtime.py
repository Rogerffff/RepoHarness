"""W3b：bringup 接线（替身 docker，不需要 daemon）。

- 非 s1 模式：`BringupService` 解析两个 profile（非法 env 在任何资源型副作用前就拒）、harness 侧代理地址
  改为 relay 别名、grader profile 注入 GradingManagerConfig；
- `_start_sandbox_runtime`：起 relay → 同一 verify 入口 → run 级记录写 ARTIFACT_DIR/runtime_profile.json
  （digest 与 startup evidence / orchestrator 一致）；验证不过 → StartupCheckError 且启动回滚停掉 relay；
- 关停链 `egress_runtime` 步：删残留 attempt 网络 + relay；
- s1_compat：profile 不接（冻结回退面零改变）。

任务面用冻结 v1 八题（legacy bring-up 路径：prepared 链要 import miles，那是 tests/adapters_miles lane 的事）。
tokenizer 缓存缺失即 skip（与 tests/adapters_miles 的 bringup 测试同口径）。
"""

from __future__ import annotations

import asyncio
import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tests/
from sandbox_test_support import ProfileFakeState, make_grader_profile, make_rollout_profile  # noqa: E402

from repoharness2.adapters.slime import sandbox_profile as sp  # noqa: E402
from repoharness2.grading.manager import ExecResult  # noqa: E402

BASE = "a" * 40


class _SandboxRuntimeFakeDocker:
    """relay 启动/就绪、verify 全流程、关停清理所需的最小 docker 面（其余交给 ProfileFakeState）。"""

    def __init__(self, *, probe_overrides: dict[str, str] | None = None) -> None:
        self.state = ProfileFakeState(
            head=BASE, rollout_profile=make_rollout_profile(), grader_profile=make_grader_profile(),
            probe_overrides=probe_overrides or {},
        )
        self.calls: list[tuple[str, ...]] = []
        self.removed: list[str] = []

    def bind_profiles(self, rollout, grader) -> None:
        self.state.rollout_profile = rollout
        self.state.grader_profile = grader

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        self.calls.append(args)
        handled = self.state.dispatch(args, input_bytes)
        if handled is not None:
            return handled
        cmd = args[0]
        if cmd == "run":
            return ExecResult(0, "deadbeef\n", "")
        if cmd == "rm":
            self.removed.append(args[-1])
            return ExecResult(0, "", "")
        if cmd == "exec":
            script = args[-1]
            if "RH2_RELAY_LISTENING" in script:
                return ExecResult(0, "RH2_RELAY_LISTENING\n", "")
            if "test -d" in script and "/.git" in script:
                return ExecResult(0, "", "")  # 探针镜像无 /testbed → sanitize 如实 skipped
            return ExecResult(0, "", "")
        raise AssertionError(f"_SandboxRuntimeFakeDocker 不认识的命令: {args}")


def _service(monkeypatch, tmp_path, *, mode: str, docker: _SandboxRuntimeFakeDocker | None):
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


async def test_audit_only_bringup_starts_relay_verifies_and_writes_run_record(monkeypatch, tmp_path):
    docker = _SandboxRuntimeFakeDocker()
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
        record = json.loads((tmp_path / "artifacts" / "runtime_profile.json").read_text())
        assert record["ok"] and record["runtime_profile_digest"] == service.runtime_profile_digest
        assert record["probe_image"] in {spec.image for spec in service.task_specs.values()}
        assert record["harness_adapter_url"] == service.harness_adapter_url and record["execution_mode"] == "fa_audit_only"
        assert record["rollout"]["checks"]["prelaunch"]["ok"] and record["grader"]["checks"]["prelaunch"]["ok"]
        relay_run = next(c for c in docker.calls if c[0] == "run" and service.egress_relay.container_name in c)
        assert "--read-only" in relay_run and "65534:65534" in relay_run and "rh2.run_id=" in " ".join(relay_run)
        # 关停链：egress_runtime 步删 relay（fake 记 rm）
        report = await service.close(reason="w3b_test")
        assert report.ok, report.to_dict()
        step = next(s for s in report.steps if s.name == "egress_runtime")
        assert step.status == "ok" and service.egress_relay is None
        assert any(c[0] == "rm" and c[-1].startswith("rh2-egress-relay-") for c in docker.calls)
        closed = True
    finally:
        if not closed:
            service.app_handle.stop()


async def test_verification_failure_blocks_startup_and_rollback_stops_relay(monkeypatch, tmp_path):
    docker = _SandboxRuntimeFakeDocker(probe_overrides={"NET_forbidden_0": "CONNECTED"})
    bringup, service = _service(monkeypatch, tmp_path, mode="fa_audit_only", docker=docker)
    rolled_back = False
    try:
        docker.bind_profiles(service.rollout_profile, service.grader_profile)

        async def no_engine_probe():
            return None

        monkeypatch.setattr(service, "_run_startup_checks", no_engine_probe)
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
    docker = _SandboxRuntimeFakeDocker()
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
