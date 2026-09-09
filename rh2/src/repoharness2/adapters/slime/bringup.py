"""F2-0 迁移：本模块为 `experiments/s1_7a_bringup/glue.py` 的正式位置
（src 唯一权威；experiments 侧为薄兼容壳）。

S1-7a 训练主链路胶水：slime custom_generate -> rh2 编排本体（真实接线）。

slime 启动参数指向本模块：

    --custom-generate-function-path s1_7a_bringup.glue.generate

进程内单例 `BringupService` 在**第一条 rollout 到来时**完成一次性启动
（与 slime 例程 `_AdapterService` 同层级；差别是本服务随后把编排本体挂到
`args.rh2_orchestrator`，rh2_custom_generate 只认这个显式挂点）：

1. tokenizer + renderer（renderers 库 `Qwen3RendererConfig` 显式配置，
   规避 U-G 本地路径静默回落 DefaultRenderer）；
2. **startup_checks 真实执行（A2/U-G/U-H）**：对真实 SGLang router 发一次
   带 tape flag 的 /generate 探针，renderer 断言 + top-p tape 断言全过才放行，
   evidence 落 startup_evidence.json；任一失败直接抛异常，训练循环起不来；
3. 起共享 AnthropicAdapter（aiohttp 线程），安装 capture wire（替换
   call_sglang_generate + 包装 record_turn，见 capture_wire.py）；
4. 冻结 8 题 -> RolloutTaskSpec 表（防漂移校验开启）；
5. GradingManager + GradingQueue（F5 默认并发 4 / 队列 8）；
6. RolloutOrchestrator（config.policy_version = 探针实测引擎 weight_version，
   假设 4 的真实事实源）。

评测模式：本 bring-up 不跑 eval（E10 主评测面语义已在库层与 mock 全绿，
7a 只验训练传输链）。

infra 注入（验收项"gate 拒绝路径真实触发一次"）：环境变量
`RH2_INJECT_INFRA_INSTANCE=<instance_id>` 时，该题的**第一条** rollout 的
评分 spec 被替换成产不出合法官方日志的 eval 脚本 -> 官方 parser 解析失败
-> GradingReport(failed_to_grade/test_log_parse_failed, reward=None) ->
gate clean_grading/reward_scope 维失败 -> GroupRepairSignal.degraded ->
样本以 abort 形状剔除。注入靠 artifact 目录下的 marker 文件保证恰好一次。

W10（决策包 D2+B v2 B-5b，多 engine 最小正确性）：本模块把 rid 级 abort 接到
`MilesRouterWorkerClient.broadcast_abort`（router `/list_workers` 全部 worker 广播同一
rid，绕过 MilesRouter 的逐请求最小负载选路），并**删除**了经 router 随机查一台 engine 的
"权威版本探测"（旧 `_latest_engine_version`：GET `/model_info`）——finalize/proxy 所用的
current 版本改为 `_observed_current_version`（引擎一手回包的最大观测，无记录回退启动探针
值）。consume-time 阈值 `--max-weight-staleness` 以记录镜像形式填入
`SlimeBindingConfig.staleness_threshold`（W4 接缝，B-1）。
"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
from collections.abc import Callable
from datetime import datetime, timezone
import json
import os
import re
import time
from pathlib import Path
from typing import Any


from repoharness2.contracts.fa_runtime import outcome_dict_is_unsafe_rejection
from repoharness2.contracts.finalization import FinalizationStoreConflict
from repoharness2.adapters.slime.generate import (
    PROCESS_CLOCK_DOMAIN,
    LeafFacts,
    StartupCheckError,
    RolloutOrchestrator,
    SlimeBindingConfig,
    parse_bool_env_flag,
    rh2_custom_generate,
    rollout_task_from_bundle_pair,
    startup_checks,
)
from repoharness2.envpack import bundles
from repoharness2.grading.manager import (
    GradingManagerConfig,
    SWEGradingManager,
)
from repoharness2.grading.queue import GradingQueue, GradingQueueConfig

from repoharness2.adapters.slime.capture_wire import (
    CaptureRegistry,
    install_capture_wire,
    make_threadsafe_session_drain_owner,
)
from repoharness2.adapters.slime.engine_router_client import MilesRouterWorkerClient, worker_base_urls
from repoharness2.adapters.slime.docker_sandbox import DockerSandbox
from repoharness2.adapters.slime.sandbox_profile import (
    EgressRelayHandle,
    GraderSandboxProfile,
    RolloutSandboxProfile,
    SandboxNetworkError,
    grader_profile_from_env,
    list_labeled_networks,
    rollout_profile_from_env,
    runtime_profile_digest,
    start_egress_relay,
    stop_egress_relay,
    teardown_attempt_network,
    verify_sandbox_profiles,
    write_runtime_profile_record,
)
from repoharness2.shutdown import (
    LifecycleState,
    MemoryEstimateInputs,
    ServiceClosedError,
    ShutdownReport,
    ShutdownStep,
    ShutdownTimeouts,
    Skipped,
    close_inflight_executions,
    collect_growth_facts,
    describe_exception,
    install_signal_shutdown,
    resource_closure_facts,
    run_shutdown_chain,
    write_resource_closure_facts,
)

# ---------------------------------------------------------------------------
# 环境旋钮（全部有默认值；训练脚本统一显式设置）
# ---------------------------------------------------------------------------

MODEL_ID = os.environ.get("RH2_MODEL_ID", "Qwen/Qwen3-4B")
EXPECTED_RENDERER = os.environ.get("RH2_EXPECTED_RENDERER", "Qwen3Renderer")
ADAPTER_BIND_HOST = os.environ.get("ADAPTER_BIND_HOST", "0.0.0.0")
ADAPTER_PORT = int(os.environ.get("ADAPTER_PORT", "18001"))
# rollout 容器（bridge 网络）反连宿主侧 adapter 的地址：默认 docker0 网关
ADAPTER_PUBLIC_HOST = os.environ.get("ADAPTER_PUBLIC_HOST", "172.17.0.1")
ARTIFACT_DIR = Path(os.environ.get("RH2_BRINGUP_ARTIFACT_DIR", "/root/bringup/artifacts"))
# W3b（D2-2）：唯一正式 rollout profile + 独立 grader profile 在 s1_compat 之外的模式**一律启用**，
# 没有关闭它的 env 开关（s1_compat 是冻结回退面，改它的容器参数触 T0，所以不接）。
# 启动前验证用的探针镜像缺省 = 任务面第一个任务的镜像（真实镜像最诚实）；可用 env 指定。
SANDBOX_VERIFY_IMAGE = os.environ.get("RH2_SANDBOX_VERIFY_IMAGE") or None


def sandbox_profile_enabled() -> bool:
    """W3b profile 是否接入（按当前 EXECUTION_MODE 动态判断，测试可 monkeypatch 模式）。"""

    return EXECUTION_MODE != "s1_compat"


def _sandbox_docker():
    """W3b sandbox 运行时（relay / verify / 残留网络）用的 docker 通道 = generate.run_docker
    （测试替换 generate.run_docker 即同时替换这里）。"""

    from repoharness2.adapters.slime import generate as _generate

    return _generate.run_docker


class FileFinalizationStore:
    """B5 durable handoff 的文件实现（generate.FinalizationStore 协议）。

    T0 第 9 条逐字（B5 复核 P1-3 纠正首版共享 CAS 偏离）：
    **per-execution immutable 目录、不建全局 CAS**。布局（root =
    ARTIFACT_DIR/finalization）：

        attempts/<attempt_key>/frozen_patch.json
        attempts/<attempt_key>/baseline_manifest.json
        attempts/<attempt_key>/receipt.json
        attempts/<attempt_key>/cleanup.json     （独立追加，非 receipt 改写）

    全部文件 **write-once**：同内容重复写幂等成功；同路径不同内容 =
    FinalizationStoreConflict（typed，绝不覆盖）。baseline manifest 因此
    每 attempt 一份（不去重）——存储成本随 attempt 数线性，真实尺寸在
    B6/FA-5 实测；若需共享 CAS 必须按 T0 重新提案，不得 T1 偷渡。
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    @staticmethod
    def _safe(name: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]", "_", name)

    def _attempt_dir(self, attempt_key: str) -> Path:
        return self.root / "attempts" / self._safe(attempt_key)

    @staticmethod
    def _write_once(path: Path, payload: dict[str, Any]) -> None:
        canonical = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, default=str
        )
        if path.exists():
            if path.read_text(encoding="utf-8") == canonical:
                return  # 同内容重写：幂等
            raise FinalizationStoreConflict(
                f"immutable 违约：{path} 已存在且内容不同（拒绝覆盖）"
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(canonical)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)

    def put_artifact_bodies(self, *, frozen_patch: Any, baseline_manifest: Any) -> None:
        adir = self._attempt_dir(frozen_patch.physical_attempt_id)
        self._write_once(adir / "frozen_patch.json", frozen_patch.model_dump(mode="json"))
        self._write_once(
            adir / "baseline_manifest.json", baseline_manifest.model_dump(mode="json")
        )

    def persist_receipt(self, receipt: Any) -> None:
        attempt_key = receipt.physical_attempt_id or receipt.trajectory_id
        self._write_once(
            self._attempt_dir(attempt_key) / "receipt.json",
            receipt.model_dump(mode="json"),
        )

    def append_cleanup_result(self, result: Any) -> None:
        # receipt_id = "rcpt_" + 已消毒 attempt key（generate 构造保证）
        attempt_key = result.receipt_id.removeprefix("rcpt_")
        self._write_once(
            self._attempt_dir(attempt_key) / "cleanup.json",
            result.model_dump(mode="json"),
        )
HARNESS_KIND = os.environ.get("RH2_BRINGUP_HARNESS", "claude_code")  # claude_code | simple
# F2-2 复核四轮：显式运行模式（s1_compat | fa_audit_only | fa_formal；
# fa_formal 还需注入 RuntimeQuiescenceBarrier——F2-2b 提供）
EXECUTION_MODE = os.environ.get("RH2_EXECUTION_MODE", "s1_compat")
AGENT_TIME_BUDGET_SEC = int(os.environ.get("SWE_AGENT_TIME_BUDGET_SEC", "600"))
MAX_TURNS_PER_SID = int(os.environ.get("RH2_MAX_TURNS_PER_SID", "25"))
# I01（2026-09-08 定案：B 路线）：vendor TrajectoryManager 的 fork 阈值。0 = 只有精确 token 前缀
# 才合并，任何重渲染漂移都 FORK 新开训练行；REALIGN 覆盖与消息 rewrite-merge 两个销毁点同时关闭，
# 每个真实生成轮在该 execution 的训练行并集中恰有一次 loss_mask=1 归属。这是决定值，不设 env 旋钮
# （默认值不应成为隐藏路径）；值随 runtime_profile.json 与 execution audit 的 turn_coverage 落盘。
FORK_THRESHOLD_TOKENS = 0

# 批 D（I04；第一组已批 A5-a ① / A5-b (2)）：present_truncated 的处置注入值。写成常量而不是 env
# 旋钮（默认值不应成为隐藏路径，与 I01 同纪律）；owner_cancelled / agent_violation 未定，保持 None
# （遇到仍 fail-fast，如实记录）；policy_horizon 共用槽位本轮只服务已批的 turn producer
# （max_turns_exhausted），不从它推导未来 token / context producer。值随 runtime_profile.json 落盘。
DISPOSITION_POLICY_VALUES: dict[str, str | None] = {
    "policy_horizon_truncation": "KEEP_FULL",
    "hard_wall_truncation": "DROP_GROUP",
    "owner_cancelled_truncation": None,
    "agent_violation": None,
}


def make_disposition_policy():
    """已批处置的 DispositionPolicy 实例（库层保持中立：值只在这里给）。"""

    from repoharness2.governance.admission import DispositionPolicy

    return DispositionPolicy(**DISPOSITION_POLICY_VALUES)


def inject_disposition_policy(args: Any):
    """批 D：把已批处置注入 `args.rh2_disposition_policy`（group_admission 的读取键）。

    未设 → 注入；已设且与常量逐槽一致 → 保持；已设但不一致或类型不对 → `StartupCheckError`
    （处置不是可覆盖的旋钮，不许隐藏覆盖）。返回生效的 policy。必须先于首个 present_truncated
    成员到达 buffer（否则 group filter 抛 DispositionNotInjectedError 并停机）。
    """

    from repoharness2.adapters.miles.group_admission import DISPOSITION_POLICY_ARGS_KEY
    from repoharness2.governance.admission import DispositionPolicy

    expected = make_disposition_policy()
    existing = getattr(args, DISPOSITION_POLICY_ARGS_KEY, None)
    if existing is None:
        setattr(args, DISPOSITION_POLICY_ARGS_KEY, expected)
        return expected
    if not isinstance(existing, DispositionPolicy):
        raise StartupCheckError(
            "disposition_policy_conflict",
            f"args.{DISPOSITION_POLICY_ARGS_KEY} 必须是 DispositionPolicy，得到 {type(existing).__name__}。",
        )
    mismatch = {
        name: (getattr(existing, name), value)
        for name, value in DISPOSITION_POLICY_VALUES.items()
        if getattr(existing, name) != value
    }
    if mismatch:
        raise StartupCheckError(
            "disposition_policy_conflict",
            f"args.{DISPOSITION_POLICY_ARGS_KEY} 与已批处置不一致（槽位: 现值 / 已批）：{mismatch}"
            "——处置不是可覆盖的旋钮，改常量并登记。",
        )
    return existing
INJECT_INFRA_INSTANCE = os.environ.get("RH2_INJECT_INFRA_INSTANCE", "")
# MoE routing tape 期望（P3 预实验 J4 增补，见 preflight/8gpu_preflight_protocol.md
# J4 判据 2/3）：Qwen3-30B-A3B 等 MoE 模型置 "1"——启动探针与生产会话都请求
# return_routed_experts，startup_checks 按 MoE 口径断言 routing tape 在场。
# 默认 "0"，7a 的 Qwen3-4B dense 行为逐字不变（A2：dense 只是没有 routing）。
EXPECT_MOE_ROUTING = os.environ.get("RH2_EXPECT_MOE_ROUTING", "0") == "1"
MOE_NUM_LAYERS = int(os.environ["RH2_MOE_NUM_LAYERS"]) if os.environ.get("RH2_MOE_NUM_LAYERS") else None
MOE_ROUTER_TOPK = int(os.environ["RH2_MOE_ROUTER_TOPK"]) if os.environ.get("RH2_MOE_ROUTER_TOPK") else None
# W1b 第一集成切片（F6）：prepared artifact 链的四个启动旋钮（目录/manifest 外部 SHA/private artifact 路径/期望 digest）——只携带 opaque 路径与
# 期望 digest（私有内容不进 env/args）。RH2_PREPARED_TASKS_DIR 未设 = legacy v1 八题
# 任务面（s1_compat/fa_audit_only 的 bring-up 路径）；fa_formal 缺它 = 拒绝，不回退。
PREPARED_TASKS_DIR = os.environ.get("RH2_PREPARED_TASKS_DIR") or None
# 公开 manifest 的外部输入身份（trusted-prep stdout 的 prepared_manifest_sha256）：目录内
# 三件套协调篡改在 actor 启动时 fail-closed。被动 digest（06 §6），不是授权闸门。
PREPARED_TASKS_MANIFEST_SHA256 = os.environ.get("RH2_PREPARED_TASKS_MANIFEST_SHA256") or None
HOST_GRADING_ARTIFACT_PATH = os.environ.get("RH2_HOST_GRADING_ARTIFACT_PATH") or None
HOST_GRADING_ARTIFACT_SHA256 = os.environ.get("RH2_HOST_GRADING_ARTIFACT_SHA256") or None
# W5a 关停：SIGTERM 是否接到关停链上。默认 "0"（opt-in）——Ray worker 进程自带
# SIGTERM 处置，无条件覆盖等于改变运行边界；launch/集成者显式置 "1" 才安装
# （install 只在有运行中 loop 的主线程可行，见 shutdown.chain.install_signal_shutdown）。
SHUTDOWN_ON_SIGTERM = os.environ.get("RH2_SHUTDOWN_ON_SIGTERM", "0") == "1"


def select_task_face_mode(execution_mode: str, prepared_dir: str | None) -> str:
    """任务面选择（纯函数，单测钉死；W1b 第一集成切片 F6）。

    - prepared 目录在场：只在 fa_audit_only/fa_formal 允许（F4 attempt 绑定依赖六字段
      身份，s1_compat 不铸造）→ ``"prepared"``；
    - prepared 目录缺席：fa_formal 直接拒绝——**formal 入口不得静默回退 v1 BundlePair**
      （v1 私有面内嵌 golden_patch）；s1_compat/fa_audit_only → ``"legacy_v1"``。
    """

    if prepared_dir:
        if execution_mode == "s1_compat":
            raise RuntimeError(
                "RH2_PREPARED_TASKS_DIR 已设但 RH2_EXECUTION_MODE=s1_compat：prepared 链依赖六字段"
                "身份（attempt 绑定），s1_compat 不铸造——拒绝启动（改 fa_audit_only/fa_formal，"
                "或去掉 prepared 目录走 v1 八题 bring-up）。"
            )
        return "prepared"
    if execution_mode == "fa_formal":
        raise RuntimeError(
            "fa_formal 缺 RH2_PREPARED_TASKS_DIR：formal 入口不得静默回退 v1 BundlePair 八题"
            "（v1 私有面含 golden_patch）——先在 host 侧运行一次性 trusted-prep"
            "（python -m repoharness2.envpack.trusted_prep）。"
        )
    return "legacy_v1"


_INJECTED_EVAL_SCRIPT = (
    "#!/bin/bash\n"
    "echo 'RH2_BRINGUP_INJECTED_INFRA_NOISE: this log has no official markers'\n"
)


# ---------------------------------------------------------------------------
# harness 驱动（真实 = slime ClaudeCodeHarness；降级 = 容器内最小 Anthropic 循环）
# ---------------------------------------------------------------------------


class ClaudeCodeDriver:
    """HarnessDriver 形状 -> slime ClaudeCodeHarness。

    安装偏离（记录进 bring-up 报告）：slime 例程的 install_cli 走
    Node22 + `npm install -g <主包 tgz>`，但 Claude Code 2.x 的 npm 主包是
    bootstrap（postinstall 再去 registry 拉平台二进制，沙箱内引入一次
    在线依赖）。这里改为直接上载 `@anthropic-ai/claude-code-linux-x64`
    平台包并解出**自包含原生二进制**（免 Node/npm、离线可装），随后
    write_config/launch_and_wait 原样走 slime ClaudeCodeHarness.run。
    """

    name = "claude_code"
    platform_tarball_env = "SLIME_AGENT_CC_PLATFORM_TARBALL"

    async def _install_native_cli(self, sb: DockerSandbox, *, timeout: float = 180) -> None:
        tarball = os.environ[self.platform_tarball_env]
        await sb.write_file("/tmp/cc-platform.tgz", Path(tarball))
        _code, _out, _err = await sb.exec(
            "set -e && mkdir -p /tmp/cc-extract && "
            "tar -xzf /tmp/cc-platform.tgz -C /tmp/cc-extract && "
            "install -m 0755 /tmp/cc-extract/package/claude /usr/local/bin/claude && "
            "/usr/local/bin/claude --version",
            user="root",
            timeout=timeout,
            check=True,
        )
        # codex 轮次 10 一般 2：不只运行，还要**比较**——版本漂移 fail-fast
        # （CC 行为画像绑定固定版本，见 fa/claude_code_retry_timeout_source_
        # guided_validation.md §4）。结果进 startup evidence。
        expected = os.environ.get("RH2_CLAUDE_CODE_VERSION", "2.1.205")
        observed = _out.strip().splitlines()[-1] if _out.strip() else ""
        # 轮次 11 一般 1：token 精确比较——子串判断会放过 "12.1.205-x"
        tokens = re.split(r"[^0-9A-Za-z.\-]+", observed)
        if expected not in tokens:
            from repoharness2.adapters.slime.generate import SlimeBindingError

            # 批 A（I05）：typed 且**不在** FAILURE_CODE_TERMINATION_MAP 内 → 编排层 run-halt。
            # 版本画像失效是 run 级配置错误（每个 attempt 都会失败），不能当单次引导故障补采。
            raise SlimeBindingError(
                "cc_version_mismatch",
                f"容器内 claude --version 不符：观测 {observed!r} 的 token 集不含"
                f"期望 {expected!r}——CC 版本画像失效，fail-fast（升级须先重跑探针套件）。",
            )
        self.cc_version_observed = observed
        # 轮次 11 一般 2 / 轮次 12 一般 2：进程内**只写一次** + 临时文件原子
        # replace（多 rollout 并发不再竞写同一文件）；失败不静默（计数 + 打印，
        # 版本校验本身已通过，evidence 缺失只降级审计面不阻断）
        if not getattr(self, "_cc_version_evidence_written", False):
            try:
                target = ARTIFACT_DIR / "cc_version_observed.json"
                tmp = ARTIFACT_DIR / ".cc_version_observed.tmp"
                tmp.write_text(
                    json.dumps({"observed": observed, "expected": expected}, ensure_ascii=False)
                )
                os.replace(tmp, target)
                self._cc_version_evidence_written = True
            except Exception as exc:  # noqa: BLE001
                self.cc_version_evidence_error = f"{type(exc).__name__}: {exc}"
                print(f"[rh2-bringup] cc_version evidence 落盘失败：{exc}")

    async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
        from slime.agent.harness import ClaudeCodeHarness
        from slime.agent.sandbox import EXIT_TIME_BUDGET_EXCEEDED

        from repoharness2.adapters.slime.docker_sandbox import SandboxExecError
        from repoharness2.adapters.slime.generate import (
            HARNESS_LAUNCH_FACTS,
            SlimeBindingError,
            ensure_claude_code_training_guards,
        )

        # 批 B（I03）：time_budget_sec = 编排此刻的剩余 episode 预算（vendored 兼容的相对整数秒）。
        # 引导步骤（装 CLI / useradd+chown / 写配置）各自的超时上限与剩余预算取 min（浮点，不取整）；
        # 引导吃光预算或引导途中被期限取消 → 不启动 CC，launch facts 写 launch_attempted=False
        # （编排据此归 hard_wall、hit_by=bootstrap，不走 drain / 装配）。启动事实三态（Codex 批 B
        # 审查 R3）：launch_attempted=False（已知未尝试）/ True（已进入上游 run，**不等于** CC 已启动）；
        # launched 只有 False / None（未确认）——不复制上游启动流程去精确定位 spawn。真正的强制保护
        # 在编排层（绝对期限 + 取消）；这里是让引导步骤合作地在期限内结束、并回填事实。
        started = time.monotonic()
        deadline = started + float(time_budget_sec)
        facts = HARNESS_LAUNCH_FACTS.get()
        if facts is None:
            facts = {}  # 非编排调用（直接跑驱动的单测）
        facts["launch_attempted"] = False
        facts["launched"] = None
        step_bound_by_deadline = False  # 当前引导步骤的 timeout 是否由 episode 期限（而非步骤上限）决定

        def remaining() -> float:
            return deadline - time.monotonic()

        def bounded(cap: float) -> float:
            nonlocal step_bound_by_deadline
            left = remaining()
            step_bound_by_deadline = left < cap
            return max(0.05, min(float(cap), left))

        def budget_exhausted(reason: str) -> int:
            facts["bootstrap_seconds"] = round(time.monotonic() - started, 3)
            facts["remaining_at_launch"] = round(remaining(), 3)
            facts["launch_attempted"] = False
            facts["launched"] = False
            facts["bootstrap_deadline_reason"] = reason
            return EXIT_TIME_BUDGET_EXCEEDED

        sb = DockerSandbox(sandbox.container_name)
        try:
            if remaining() <= 0:
                return budget_exhausted("before_install")
            await self._install_native_cli(sb, timeout=bounded(180))
            if remaining() <= 0:
                return budget_exhausted("after_install")
            # 预建 agent 用户（与 slime ensure_agent_user 同一命令、宽超时）：
            # slime 侧写死 timeout=60s，django 官方镜像 /testbed 数万文件的
            # chown -R 在 overlay2 copy-up 下超时（run6 实测 8/8 django rollout
            # exit=124 全灭）。本命令幂等（id agent 短路），预跑成功后 slime
            # 内部那次变成 no-op。上限 900s 与剩余预算取 min（批 B）。
            await sb.exec(
                f"id agent >/dev/null 2>&1 || useradd -m -s /bin/bash agent && "
                f"chown -R agent:agent /home/agent {workdir} && "
                f"git config --system --add safe.directory '*' && id agent",
                user="root",
                check=True,
                timeout=bounded(900),
            )
            # D-FA-6 接线（FA-1，FA-0 递延项）：DISABLE_COMPACT=1 合并进
            # SLIME_AGENT_CC_EXTRA_ENVS——slime ClaudeCodeHarness 会把该 JSON 并入
            # CC 子进程环境。merged 存 self 供 evidence 采集；真实子进程验真挂
            # FA-5 短租（本机无法冒烟真实 CC）。警示：env 只关 auto/manual compact，
            # Microcompact/Context Collapse 由装配期收缩检测兜底（generate.py）。
            self.compaction_guard_envs = ensure_claude_code_training_guards(os.environ)
            left = remaining()
            if left <= 0:
                return budget_exhausted("after_bootstrap")
            facts["bootstrap_seconds"] = round(time.monotonic() - started, 3)
            facts["remaining_at_launch"] = round(left, 3)
            facts["launch_attempted"] = True  # 进入上游 run：ensure user / write config / spawn 仍在其中
            return await ClaudeCodeHarness().run(
                sb,
                workdir=workdir,
                session_id=session_id,
                adapter_url=adapter_url,
                time_budget_sec=max(1, int(left)),
                prompt=prompt,
            )
        except asyncio.CancelledError:
            # 编排的绝对期限 / 关停在引导途中取消——尚未尝试启动就如实回填（编排据此跳过 drain / 装配）；
            # 已进入上游 run 的取消保持 launch_attempted=True、launched=None（未确认）。
            if not facts.get("launch_attempted"):
                facts["bootstrap_seconds"] = round(time.monotonic() - started, 3)
                facts["remaining_at_launch"] = round(remaining(), 3)
                facts["launched"] = False
                facts["bootstrap_deadline_reason"] = "cancelled_during_bootstrap"
            raise
        except SandboxExecError as exc:
            if exc.exit_code == 124 and step_bound_by_deadline and not facts.get("launch_attempted"):
                # 该步骤的 timeout 由 episode 期限决定（min(上限, 剩余) 取到了剩余）——超时 = 墙钟到点，
                # 不是引导故障；按构造判定，不看异常发生时"是否刚好过墙"（Codex 批 B 审查 R3）。
                facts["bootstrap_exec_error"] = str(exc)[:300]
                return budget_exhausted("bootstrap_step_timed_out_at_deadline")
            # 批 A（I05；Codex 批 A 审查 R1 修正）：只有 DockerSandbox 自己抛的操作失败
            # （exec check=True 非零 / 超时 124、write_file 非零——覆盖装 CLI、useradd/chown、
            # slime 的 ensure_agent_user / write_config / spawn）才是可证明来源的单次容器层面
            # 引导故障（task-local，ABORTED 补采）。其它 RuntimeError（我方或 vendored 代码
            # 不变量）与 typed 码（cc_version_mismatch / cc_training_guard_conflict…）原样
            # 上抛，由编排层按 FAILURE_CODE_TERMINATION_MAP 分流（不在表内 = run-halt）。
            # detail 保留原始 exec 输出供诊断。
            raise SlimeBindingError(
                "harness_bootstrap_failed", f"{type(exc).__name__}: {exc}"[:400]
            ) from exc


_SIMPLE_AGENT_PY = r'''
import json, os, subprocess, sys, urllib.request

ADAPTER = os.environ["RH2_ADAPTER_URL"]
SID = os.environ["RH2_SESSION_ID"]
WORKDIR = os.environ.get("RH2_WORKDIR", "/testbed")
MAX_TURNS = int(os.environ.get("RH2_SIMPLE_MAX_TURNS", "12"))
PROMPT_PATH = os.environ["RH2_PROMPT_PATH"]

TOOLS = [{
    "name": "bash",
    "description": "Run a bash command in the repository checkout and return stdout+stderr.",
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    },
}]

def post(messages):
    body = {
        "model": "slime-actor",
        "max_tokens": 1024,
        "messages": messages,
        "tools": TOOLS,
        "system": "You are a software engineer fixing a bug in the repo at " + WORKDIR + ".",
    }
    req = urllib.request.Request(
        ADAPTER + "/v1/messages",
        data=json.dumps(body).encode(),
        headers={
            "content-type": "application/json",
            "authorization": "Bearer " + SID,
            "x-api-key": SID,
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read().decode())

prompt = open(PROMPT_PATH).read()
messages = [{"role": "user", "content": prompt}]
for turn in range(MAX_TURNS):
    reply = post(messages)
    content = reply.get("content") or []
    messages.append({"role": "assistant", "content": content})
    tool_uses = [b for b in content if b.get("type") == "tool_use"]
    if reply.get("stop_reason") != "tool_use" or not tool_uses:
        break
    results = []
    for block in tool_uses:
        cmd = (block.get("input") or {}).get("command") or "true"
        proc = subprocess.run(
            ["bash", "-c", cmd], cwd=WORKDIR, capture_output=True, text=True, timeout=180
        )
        out = (proc.stdout + proc.stderr)[-4000:]
        results.append({
            "type": "tool_result",
            "tool_use_id": block["id"],
            "content": out or "(no output)",
        })
    messages.append({"role": "user", "content": results})
print("SIMPLE_AGENT_DONE turns=", turn + 1)
'''


class SimpleLoopDriver:
    """降级预案（风险预案条款）：容器内最小 Anthropic Messages 循环 + bash 工具。

    诚实标注：SlimeBindingConfig.harness_name 必须配 "mock_harness"——这不是
    Claude Code，transport 链路等价但 harness 行为面不同（deviation 上报）。
    """

    name = "mock_harness"

    async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
        sb = DockerSandbox(sandbox.container_name)
        await sb.write_file("/rh2/simple_agent.py", _SIMPLE_AGENT_PY)
        await sb.write_file("/rh2/prompt.txt", prompt)
        code, out, err = await sb.exec(
            "python3 /rh2/simple_agent.py || python /rh2/simple_agent.py",
            env={
                "RH2_ADAPTER_URL": adapter_url,
                "RH2_SESSION_ID": session_id,
                "RH2_WORKDIR": workdir,
                "RH2_PROMPT_PATH": "/rh2/prompt.txt",
            },
            timeout=time_budget_sec,
        )
        if code != 0:
            # 与 CC 语义一致：非零退出码原样上抛给编排层记录（不是异常）
            print(f"[rh2-simple-agent] exit={code} tail={err[-300:] or out[-300:]}")
        return code


# ---------------------------------------------------------------------------
# 服务单例
# ---------------------------------------------------------------------------


# 单例锁必须在 import 期创建（import 单线程）：懒创建有并发窗口——32 条
# rollout 同时首调 get() 时会各自 new Lock -> 多个 BringupService 实例 ->
# 多个 adapter 线程抢同一端口（run4 实测 "Exception in thread
# rh2-anthropic-adapter" 即此形态）。
_SERVICE_LOCK = asyncio.Lock()


def _termination_block(audit: Any) -> dict[str, Any] | None:
    """批 C：audit.termination + 最终 termination_kind（outcome 优先，其次 hint）。"""

    block = getattr(audit, "termination", None)
    if block is None:
        return None
    block = dict(block)
    outcome = getattr(audit, "outcome_v2", None) or {}
    block["kind"] = outcome.get("termination_kind") or getattr(audit, "termination_kind_hint", None)
    return block


def _episode_deadline_block(audit: Any, proxy: Any) -> dict[str, Any] | None:
    """批 B：audit.episode_deadline + proxy 侧按 paid 累计的 model_call 排队秒数。"""

    block = getattr(audit, "episode_deadline", None)
    if block is None:
        return None
    block = dict(block)
    scope = audit.physical_attempt_id or audit.session_id
    if proxy is not None and scope and hasattr(proxy, "queue_wait_seconds_total"):
        block["model_call_queue_wait_seconds_total"] = proxy.queue_wait_seconds_total(scope)
    else:
        block["model_call_queue_wait_seconds_total"] = None
    return block


def write_execution_audit_record(proxy, audit, path) -> None:
    """execution 终态审计（轮次 13 P0-5 + 轮次 14 事务化）：

    事务顺序 = **snapshot → 持久写成功 → ack 移除**——写失败时 attempt 仍在
    热内存（下次审计/停机报告仍可导出），不会"既拒绝 rollout 又丢审计依据"。
    记录含完整时间线与分段耗时（timeline_dicts/timing_summary——轮次 14 仍需
    修正 4：此前只写 steps，丢掉了专门建设的阶段耗时证据）、最终 disposition
    与 Eligibility 引用。"""

    attempts_snapshot = []
    if proxy is not None and audit.session_id:
        # P0-2：attempt 账目按 paid 命名空间；paid 缺失（S1 兼容）回退
        # audit.session_id（F2-2 复核后 = 非秘密 internal sid，与 wire
        # 账目键一致——token 只做认证，不再是任何键）
        _attempt_scope = audit.physical_attempt_id or audit.session_id
        attempts_snapshot = proxy.snapshot_attempts(_attempt_scope)
    finalized = audit.finalized
    eligibility_ref = None
    disposition = "aborted"
    if finalized is not None:
        disposition = "finalized"
        report = getattr(finalized, "eligibility_report", None)
        eligibility_ref = getattr(report, "report_id", None)
    elif audit.outcome_v2 is not None and outcome_dict_is_unsafe_rejection(
        audit.outcome_v2
    ):
        # B3 终核：disposition 与 schema/producer 共用唯一谓词（七字段
        # 全量），reason 字符串或部分字段不足以派生 permanent_rejected
        # 阻塞 4：unsafe 永久拒绝从既有 outcome 事实派生 disposition
        # （不建第二份可独立修改的准入账），不再落 unknown_terminal
        disposition = "permanent_rejected"
    elif getattr(audit, "audit_only", False):
        # F2-2 复核三轮 P1-2：屏障前 audit-only 收口显式记名——不是
        # unknown_terminal（那是"无失败记录且未 finalize"的兜底），
        # fault-domain 统计（FA-2B）按本值排除，不污染 capture 故障率
        disposition = "audit_only_rejected"
    elif not audit.failure_records:
        disposition = "unknown_terminal"
    # F2-0b 复核 P1-B：写 record 时只读一次 monotonic/epoch，monotonic 与
    # epoch 两套起止一起落盘——timeline 首/末事件不等于构造/持久化时刻，
    # 且 proxy 区间要能校验落在 execution wall 内
    wall_end_monotonic = time.monotonic()
    wall_end_epoch = time.time()
    record = {
        "schema_id": "rh2.fa.execution_audit.v1",
        "trajectory_id": audit.trajectory_id,
        "session_id": audit.session_id,
        "physical_attempt_id": audit.physical_attempt_id,
        "task_id": audit.task_id,
        "disposition": disposition,
        "eligibility_report_ref": eligibility_ref,
        "delivered_sample_count": audit.delivered_sample_count,
        "lease_released": audit.lease_released,
        "repair_signal_forwarded": audit.repair_signal_forwarded,
        "steps": list(audit.steps),
        "timeline": audit.timeline_dicts(),
        "timing_summary": audit.timing_summary(),
        # F2-0b Observability V0：双时钟**原始事实**（wall + 候选区间）——
        # D1b 前不派生 chargeable_execution_seconds（五审 2.1/2.2）
        "wall_start_epoch": audit.started_epoch_seconds,
        "wall_start_monotonic": audit.started_monotonic,
        "wall_end_epoch": wall_end_epoch,
        "wall_end_monotonic": wall_end_monotonic,
        "wall_clock_domain_id": PROCESS_CLOCK_DOMAIN,
        "non_chargeable_intervals": list(audit.non_chargeable_intervals),
        # 批 B（I03）：统一 episode 期限的观测块（可选键；B 线定预算数值的实测来源）
        "episode_deadline": _episode_deadline_block(audit, proxy),
        # 批 C（I02/I14）：终止事实观测块（B 的接口：kind ∈ completed / max_turns_exhausted /
        # hard_wall_timeout / 基础设施族；turn_budget / harness_exit_code / stop）
        "termination": _termination_block(audit),
        # F2-2：quiescence 事实 + Outcome v2（producer 产物随审计持久化；
        # assembler 消费归 F2-5）。session_id 自 F2-2 复核起 = 非秘密
        # internal sid（s- 前缀）；capability token 只认证不落任何持久面
        # B2 closure P1-2：B1/B2 摘要入持久审计（完整 artifact 归 B5）
        "baseline_manifest_digest": audit.baseline_manifest_digest,
        "baseline_entry_count": audit.baseline_entry_count,
        "frozen_patch_digest": audit.frozen_patch_digest,
        "patch_entry_count": audit.patch_entry_count,
        "excluded_pathset_changed": audit.excluded_pathset_changed,
        "runtime_private_pathset_changed": audit.runtime_private_pathset_changed,
        "unsafe_artifact_reasons": list(audit.unsafe_artifact_reasons),
        "scoring_projection_entry_count": audit.scoring_projection_entry_count,
        # W3b：run 级 profile 摘要（join 键）+ 本 attempt 的 sandbox 创建期/启动前核对事实
        # （不是每轨迹能力事实，不进 eligibility）
        "runtime_profile_digest": getattr(audit, "runtime_profile_digest", None),
        "egress_network": getattr(audit, "egress_network", None),
        "sandbox_setup": getattr(audit, "sandbox_setup", None),
        "prelaunch_check": getattr(audit, "prelaunch_check", None),
        "session_plane_drained": audit.session_plane_drained,
        "runtime_quiescence_confirmed": audit.runtime_quiescence_confirmed,
        "capture_closed": audit.capture_closed,
        "outcome_v2": audit.outcome_v2,
        "harness_exit_code": audit.harness_exit_code,
        "failure_records": [
            {"stage": f.stage, "error_type": f.error_type, "detail": f.detail}
            for f in audit.failure_records
        ],
        "cleanup_failures": [
            {"step": c.step, "detail": c.detail} for c in audit.cleanup_failures
        ],
        "context_shrink_reasons": list(audit.context_shrink_reasons),
        # I01：动作覆盖与训练行成本（可选键；schema_id 不变，消费者忽略未知键）
        "turn_coverage": getattr(audit, "turn_coverage", None),
        "model_call_attempts": [a.model_dump(mode="json") for a in attempts_snapshot],
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    # 持久化成功才移除热内存（ack）
    if proxy is not None and audit.session_id:
        proxy.ack_attempts(_attempt_scope)


def build_production_model_call_proxy(
    registry, version_provider, *, require_real: bool, artifact_sink
):
    """生产 proxy 装配（轮次 14 仍需修正 5：装配面必须可本地回归——测试
    断言 limiter 真的传进 proxy，而不是散在 async_start 里没法测）。"""

    from repoharness2.adapters.slime.async_worker import (
        ModelCallProxy,
        ResourceLimits,
        StaticActiveCoordinator,
    )

    limits = ResourceLimits(
        {"model_call": int(os.environ.get("RH2_FA_LIMIT_MODEL_CALL", "32"))}
    )
    proxy = ModelCallProxy(
        StaticActiveCoordinator(version_provider),
        attempt_timeout_seconds=900.0,  # 与 wire sock_read 同级
        artifact_sink=artifact_sink,
        sink_required=require_real,
        limits=limits,
    )
    registry.model_call_proxy = proxy
    return proxy


def bringup_leaf_facts(sid, samples, hook):
    """bring-up 的树侧事实提取（F1 身份制版；模块级以便本地回归）。

    多叶链（FORK/compaction）也放行——库层 default_leaf_facts 的单叶限制
    保持不变，这里是 bring-up 面对真实 CC FORK（run6 实测 4/32）的显式
    选择。旧做法（附"全部 session capture id"、归属交 `_match_turns_to_runs`
    按 token 内容反推）已被 F1 身份制取代：PerRolloutAdapter.finish_session
    在树走查后把身份 span 附在每条叶链 Sample 上（`RH2_TURN_IDENTITY_
    SPANS_ATTR`），这里读出装进 LeafFacts——capture_record_ids 与
    turn_spans 逐条对位，orchestrator 的 backfill/装配据此直取归属，token
    相等只作校验断言。span 缺失 = finish 包装没走到（接线破损），
    fail-closed。
    """

    from repoharness2.adapters.slime.generate import (
        RH2_TURN_IDENTITY_SPANS_ATTR,
        SlimeBindingError,
    )

    facts = []
    for i, sample in enumerate(samples):
        spans = getattr(sample, RH2_TURN_IDENTITY_SPANS_ATTR, None)
        if spans is None:
            raise SlimeBindingError(
                "turn_identity_spans_missing_on_leaf",
                f"叶链 b{i}（sid={sid}）没有身份 span 附加属性——"
                "PerRolloutAdapter.finish_session 的身份导出没有生效，"
                "拒绝退回按内容反推归属（F1 修复语义）。",
            )
        facts.append(
            LeafFacts(
                branch_id=f"b{i}",
                capture_record_ids=tuple(s.capture_record_id for s in spans),
                turn_spans=tuple(spans),
            )
        )
    return facts


def make_per_rollout_adapter(registry, shared_adapter, hook):
    """SessionAdapter 形状（轮次 14：从闭包提取为模块级，open rollback 等
    语义可本地回归）。"""

    class PerRolloutAdapter:
        def open_session(
            self, sid, *, sampling_defaults=None, max_context_tokens=0,
            physical_attempt_id=None, capability_token=None, deadline_monotonic=None,
        ):
            # 轮次 13 P1-6：open 事务化——底层 open 失败必须回滚 registry
            # 注册。F2-1a 熔断后收敛：paid 与 hook 同一原子注册、同一
            # rollback（不存在预登记残留面）。F2-2 复核 P0-3：capability
            # token（认证映射）同事务绑定/回滚。
            registry.register(
                sid, hook,
                physical_attempt_id=physical_attempt_id,
                capability_token=capability_token,
                deadline_monotonic=deadline_monotonic,  # 批 B：episode 期限显式下传 proxy
            )
            try:
                shared_adapter.open_session(
                    sid,
                    sampling_defaults=sampling_defaults,
                    max_context_tokens=max_context_tokens,
                )
            except BaseException:
                registry.unregister(sid)
                raise

        async def finish_session(
            self, sid, *, base_sample, reward=0.0, extra_metadata=None, wait_timeout=5.0
        ):
            # F1 身份制（叶侧）：先幂等 drain 掉在飞轮（underlying finish 内
            # 会再 shutdown 一次，无副作用差异），再拿住树根引用——
            # get_trajectory 随后弹树，但树对象仍被本引用持有，供只读树
            # 走查导出身份 span。max_sample_tokens 必须在 finish 弹 store
            # 之前读到（vendor finish_session 用同一值截断样本）。
            manager = getattr(shared_adapter, "manager", None)
            root = None
            fork_threshold = 0
            max_sample_tokens = 0
            if manager is not None:
                await shared_adapter.shutdown_session(sid, wait_timeout=wait_timeout)
                root = manager._trees.get(sid)
                fork_threshold = manager._fork_threshold
                session = shared_adapter.store.get(sid)
                max_sample_tokens = (
                    int(getattr(session, "max_context_tokens", 0) or 0)
                    if session is not None
                    else 0
                )
            samples = await shared_adapter.finish_session(
                sid,
                base_sample=base_sample,
                reward=reward,
                extra_metadata=extra_metadata,
                wait_timeout=wait_timeout,
            )
            if samples:
                from repoharness2.adapters.slime.generate import (
                    RH2_TURN_COVERAGE_ATTR,
                    SlimeBindingError,
                )
                from repoharness2.adapters.slime.turn_identity import (
                    attach_turn_identity_spans,
                )

                if root is None:
                    raise SlimeBindingError(
                        "turn_identity_tree_unavailable",
                        f"session {sid} 产出了叶链样本但树根不可得（shared "
                        "adapter 无 TrajectoryManager 树）——身份 span 无从"
                        "导出，fail-closed。",
                    )
                coverage = attach_turn_identity_spans(
                    samples,
                    root,
                    fork_threshold=fork_threshold,
                    max_sample_tokens=max_sample_tokens,
                    resolve_capture_id=(
                        lambda turn_index: registry.turn_capture_binding(
                            sid, turn_index
                        )
                    ),
                )
                # I01：覆盖统计随叶链运到编排层（generate.take_turn_coverage 取走后
                # 进 RolloutAudit.turn_coverage 并剥除）；同一 dict 挂到每条叶链上。
                coverage_dict = coverage.to_dict()
                for leaf in samples:
                    setattr(leaf, RH2_TURN_COVERAGE_ATTR, coverage_dict)
            return samples

        def revoke_session(self, sid):
            # F2-2 quiescence 第一步：HTTP 层拒新请求（guard 按 revoked 集合
            # 403）。同步方法——撤销只改 registry 状态，不做 IO；drain 仍由
            # 随后的 finish/drop（slime shutdown_session 语义）完成。
            registry.revoke(sid)

        async def drop_session(self, sid, *, wait_timeout=5.0):
            try:
                await shared_adapter.drop_session(sid, wait_timeout=wait_timeout)
            finally:
                registry.unregister(sid)

    return PerRolloutAdapter()


def staleness_threshold_mirror_from_args(args: Any) -> int | None:
    """W4 接缝（B-1）：`SlimeBindingConfig.staleness_threshold` 记录镜像的唯一来源 = miles
    `--max-weight-staleness N`（`args.max_weight_staleness`）。

    - 未配置（属性缺失或 None）→ None：generate.py 按前置清理批的哨兵行为处理（非 s1 写
      `STALENESS_THRESHOLD_MIRROR_UNBOUNDED` 并在 audit 时间线记
      `staleness_threshold_mirror_unconfigured`；s1_compat 写冻结历史值）；
    - 非负 int → 原值（bool 不算 int）；
    - 其它（负数 / 非整数）→ RuntimeError：启动配置错误，在任何资源型副作用之前炸。

    这是**记录镜像**，不是资格门：gate / admission / 复合 group filter 都不消费它（B-1，
    consume-time 唯一权威 = miles `DefaultDataBuffer.get()` 的同一参数）。
    """

    value = getattr(args, "max_weight_staleness", None)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(
            f"--max-weight-staleness={value!r} 不是非负整数——consume-time 阈值镜像无法记录，拒绝启动。"
        )
    return value


def expected_engine_count(args: Any) -> int | None:
    """固定 topology 下预期的 SGLang engine 数（abort 广播核对集合完整性的唯一预期值来源）。

    miles 代码事实：`miles/ray/rollout/rollout_server.py` 建 engine 的式子是
    ``num_engines = group_cfg.num_gpus // min(num_gpus_per_engine, args.num_gpus_per_node)``；
    首训由 `experiments/miles_gpu_spike/launch.sh` 钉死为**单节点、单 model group、无 PD**
    （拒 `--sglang-config` / `--prefill-num-servers`），所以那条式子退化成

        engine 数 = rollout_num_gpus // rollout_num_gpus_per_engine

    两个参数都来自 BringupService 已持有的 miles args（`self._profile_args`，即 `get()` 传进来
    的那份），不另外读环境变量、不猜默认值。

    返回 ``None`` = **算不出来**，也就是"不能声称核对过"：
    - 任一参数缺席 / 不是整数 / ≤ 0；
    - 不整除（miles 的整数除法会静默丢余数卡，此时真实 engine 数与本式不一定一致）；
    - 给了 `num_gpus_per_node` 且 per-engine 卡数超过它（engine 会按每节点卡数切，本式不成立）。
    调用方（`_verify_router_worker_set`）在 fa_formal 下把 ``None`` 当作核对失败处理。
    """

    def _positive_int(name: str) -> int | None:
        value = getattr(args, name, None)
        if value is None or isinstance(value, bool):
            return None
        try:
            value = int(value)
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None

    gpus = _positive_int("rollout_num_gpus")
    per_engine = _positive_int("rollout_num_gpus_per_engine")
    if gpus is None or per_engine is None or gpus % per_engine != 0:
        return None
    per_node = _positive_int("num_gpus_per_node")
    if per_node is not None and per_engine > per_node:
        return None  # 多节点切法：miles 会按 min(per_engine, per_node) 建更多 engine，本式不成立
    return gpus // per_engine


class BringupService:
    _instance: "BringupService | None" = None

    def __init__(self, args: Any) -> None:
        from slime.agent.adapters import AnthropicAdapter
        from slime.agent.aiohttp_threaded import FilteredAccessLogger, run_app_in_thread
        from slime.utils.processing_utils import load_tokenizer

        # codex Wave3 §9.4：owner loop = **构造本服务的那个 event loop**。生产拓扑里
        # `BringupService.get()` 由 miles 共享后台 AsyncLoopThread 上的 rollout fn await
        # （`miles/ray/rollout/rollout_manager.py` 把 rollout fn / worker / buffer / bringup
        # 都放在同一个后台 loop），所以这里取到的就是 owner loop。关停链、grading queue、
        # 在飞执行表全部属于它；adapter 的 aiohttp 线程（`run_app_in_thread`，vendored）另有
        # 自己的 loop，从那边来的 run-fatal 必须 `call_soon_threadsafe` 派回来，
        # 不能就地 `create_task`（否则关停链跑在 adapter loop 上，await owner loop 的 Future 会
        # 报 "attached to a different loop"）。绑定放在最前面：任何后续副作用出错都能正确关停。
        self._owner_loop: asyncio.AbstractEventLoop | None = None
        self._bind_owner_loop()
        # W5a 关停面（纯配置，先于任何资源型副作用）：超时上界从环境读（非法值
        # 在起线程之前就炸）；LifecycleState 是"关闭后禁 submit/resolve"与在飞
        # 执行登记的唯一状态位；run-fatal 通道接到 _on_run_fatal。
        self.shutdown_timeouts = ShutdownTimeouts.from_env(os.environ)
        self.lifecycle = LifecycleState()
        self.lifecycle.on_fatal = self._on_run_fatal
        self._close_task: asyncio.Task[ShutdownReport] | None = None
        self.shutdown_report: ShutdownReport | None = None
        # W5a 复核 #3b：关停进行中到达的 run-fatal 先排队，落盘前全部吸收进报告
        self._fatals_during_close: list[BaseException] = []
        self._closing_report: ShutdownReport | None = None
        # patch 0013：close 进行中后到的原因/残留（pending，落盘前吸收）；residue 只能在链后并入
        self._pending_late_facts: list[dict[str, Any]] = []
        self._deferred_residues: list[dict[str, Any]] = []
        self._uninstall_signal_shutdown: Any = None
        self._profile_args = args  # 资源闭包上界估算读 miles/slime 的并发与长度参数
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        self.registry = CaptureRegistry()
        # W4 接缝（B-1）：consume-time 阈值 `--max-weight-staleness N` 的记录用镜像——纯配置，
        # 非法值在 tokenizer/线程等任何副作用之前就炸。
        self.staleness_threshold_mirror = staleness_threshold_mirror_from_args(args)
        self.tokenizer = load_tokenizer(args.hf_checkpoint, trust_remote_code=True)
        self.sglang_url = f"http://{args.sglang_router_ip}:{args.sglang_router_port}"
        # W10（B-5b）：rid 级 abort 广播客户端——问 router `/list_workers` 取全部 worker，
        # 绕过 router 逐 worker 直发同一 rid（持有者终止、其余忽略）。接到 capture registry 的
        # engine_abort 挂点后，wire 的 cancel/超时 abort 不再经 MilesRouter 最小负载错发。
        # 实时列表失败时的回退目标集合由 `_verify_router_worker_set()` 在启动核对通过后下发
        # （核对不过就不下发，也不进入 RUNNING）；client 内已无"经 router 单发"的回退路径。
        self.router_workers = MilesRouterWorkerClient(self.sglang_url)
        self.registry.engine_abort = self.router_workers.broadcast_abort
        self.max_context_len = int(getattr(args, "rollout_max_context_len", 0) or 0)
        # B2（R6-ext）请求侧引擎选择（与 generate.py session_defaults 同一
        # args 显式开关，不猜引擎）：True = sglang-miles 构建（原生
        # sampling-mask primitive），启动探针改请求新顶层约定
        # return_sampling_mask（旧 custom_params 约定对该引擎无效，沿用会在
        # U-H 探针假阳性 fail）。probe 的 top_k 上界取 args.rollout_top_k
        # ——mask 请求要求有限 top_k（T0-A），缺失时探针在 wire 前置校验
        # fail-closed（sampling_mask_param_missing），启动即暴露配置缺口。
        self.engine_sampling_mask = bool(getattr(args, "rh2_engine_sampling_mask", False))
        self._probe_top_k = getattr(args, "rollout_top_k", None)

        # -- U-G：renderer 显式配置 + 类名断言（v2_renderer_report §4 的规避写法）
        from renderers import Qwen3RendererConfig, create_renderer

        self.renderer = create_renderer(self.tokenizer, config=Qwen3RendererConfig())

        # -- capture wire **先于** 共享 adapter 构造（Codex 修后复核 R1）：vendored `BaseAdapter.__init__`
        #    在构造时就把当时的 `self._run_turn` 绑定成 POST /v1/messages 的 handler（aiohttp 路由保存的是
        #    bound method 对象），之后再替换类属性不会更新已登记的路由——turn 预算的"先等已接纳在飞轮交付
        #    再拒绝"包装（`install_turn_budget_wire` 包装 `_run_turn`）在"先构造、后安装"的顺序下根本不在
        #    生产路由上。先安装再构造，路由登记直接绑到包装；下面再用启动核对兜底。
        install_capture_wire(self.registry)
        self.adapter = AnthropicAdapter(
            tokenizer=self.tokenizer,
            sglang_url=self.sglang_url,
            tool_parser=getattr(args, "sglang_tool_call_parser", None) or None,
            reasoning_parser=getattr(args, "sglang_reasoning_parser", None) or None,
            max_turns_per_sid=MAX_TURNS_PER_SID,
            fork_threshold_tokens=FORK_THRESHOLD_TOKENS,
        )
        # codex 轮次 10 P0-2 的 404 守卫：构造器 patch 现在已对生产 adapter 生效（先安装后构造），
        # 这里的显式补装是幂等兜底，并在起线程前断言在场
        from repoharness2.adapters.slime.capture_wire import (
            assert_no_404_guard_installed,
            assert_turn_pipeline_bound_to_routes,
            ensure_no_404_middleware,
        )

        ensure_no_404_middleware(self.adapter.app)
        assert_no_404_guard_installed(self.adapter.app)
        # Codex 修后复核 R1 的启动核对：已登记的 POST 路由必须就是当前（已包装的）`_run_turn`；
        # 顺序再被改回去时这里 typed 停止，而不是带着失效的在飞交付保护进入 RUNNING
        try:
            assert_turn_pipeline_bound_to_routes(self.adapter)
        except RuntimeError as exc:
            raise StartupCheckError("turn_budget_wire_not_bound_to_route", str(exc)) from exc
        # 轮次 13 P0-1：bearer 能力预检——未知/已关/中毒会话 HTTP 层拒绝，
        # 不产生 SGLang 请求（wire 内 UnknownSessionError 是第二道）
        from repoharness2.adapters.slime.capture_wire import build_session_guard_middleware

        self.adapter.app.middlewares.append(build_session_guard_middleware(self.registry))
        # 复核六轮 P0-2：纯配置校验在**任何资源启动之前**（线程未起）
        if EXECUTION_MODE not in ("s1_compat", "fa_audit_only", "fa_formal"):
            raise RuntimeError(f"RH2_EXECUTION_MODE={EXECUTION_MODE!r} 不在三值枚举内。")
        # F1（codex Wave3 复核，2026-09-04）：此处曾有无条件 `raise RuntimeError("fa_formal 暂禁…")` 临时挡板
        # （2026-08-19 设，移除条件 = W1b + W3a + W3b + W4 完成，已满足；D0-4 不建代码级 owner 闸门）。
        # 现已删除。fa_formal 真正的必需核对全部保留且各自 typed 停止：prepared 任务面
        # （select_task_face_mode：缺 RH2_PREPARED_TASKS_DIR 即拒，不回退 v1）、身份/版本契约
        # （validate_execution_config：require_real_weight_versions + 数值 policy_version + 屏障）、
        # sandbox profile（RolloutOrchestrator：缺 profile/relay/digest 即拒）、finalization store、
        # 启动前验证（_start_sandbox_runtime：不过即 StartupCheckError）。
        # -- W3b：两个 profile 的参数在任何资源型副作用之前解析（非法即拒）。rollout profile 的
        #    模型代理上游端口要等 adapter 线程起来才知道，这里先用占位端口验证其余参数。
        self.grader_profile: GraderSandboxProfile | None = None
        self.rollout_profile: RolloutSandboxProfile | None = None
        self.egress_relay: EgressRelayHandle | None = None
        self.runtime_profile_digest: str | None = None
        self.runtime_profile_record: dict[str, Any] | None = None
        # F4：relay 启动失败且自行清理也失败时残留的容器名（带 rh2.run_id label；启动回滚把它并入
        # rollback errors，launch trap 的 label 残留检查可见）。
        self.sandbox_startup_leftovers: tuple[str, ...] = ()
        # F3 接缝：启动探针阶段**数量核对通过**的 router worker URL 集合（`_verify_router_worker_set` 填；
        # 核对不通过时保持空元组，fa_formal 下同时抛 StartupCheckError）。
        self.verified_router_workers: tuple[str, ...] = ()
        if sandbox_profile_enabled():
            self.grader_profile = grader_profile_from_env(os.environ)
            rollout_profile_from_env(
                os.environ, model_proxy_upstream_host=ADAPTER_PUBLIC_HOST, model_proxy_upstream_port=1
            )
        # -- 任务面（W1b 第一集成切片 F6；纯配置/文件校验，仍在资源型副作用之前）：
        #    prepared 链 = 只读 trusted-prep 产物并复核（本 actor 进程不调完整 loader，
        #    对象图里没有 golden/validation 面），或 legacy v1 八题 bring-up；
        #    fa_formal 缺 prepared 产物 = 拒绝，不回退（select_task_face_mode）。
        self.prepared_face = None
        self.attempt_assignments = None
        self.pairs = None
        if select_task_face_mode(EXECUTION_MODE, PREPARED_TASKS_DIR) == "prepared":
            from repoharness2.adapters.miles.attempt_assignment import AttemptAssignmentRegistry
            from repoharness2.adapters.slime.prepared_task_face import PreparedTaskFace

            self.prepared_face = PreparedTaskFace.load(
                prepared_dir=PREPARED_TASKS_DIR,
                manifest_sha256=PREPARED_TASKS_MANIFEST_SHA256,
                host_grading_path=HOST_GRADING_ARTIFACT_PATH,
                host_grading_sha256=HOST_GRADING_ARTIFACT_SHA256,
                time_budget_seconds=AGENT_TIME_BUDGET_SEC,
                # miles RolloutDataSource 读的必须就是 prep 的 prompts.jsonl（按内容 digest 绑定）
                prompt_data_path=getattr(args, "prompt_data", None),
            )
            self.attempt_assignments = AttemptAssignmentRegistry(
                verify_dispatch=self.prepared_face.verify_dispatch
            )
            self.task_specs = {
                tid: self.prepared_face.rollout_spec(tid) for tid in self.prepared_face.task_ids()
            }
        else:
            # 冻结 8 题（防漂移校验开启）。v1 私有面内嵌 golden_patch——只许 bring-up。
            self.pairs = {pair.instance_id: pair for pair in bundles.load_bundle_pairs()}
            self.task_specs = {
                iid: rollout_task_from_bundle_pair(pair, time_budget_seconds=AGENT_TIME_BUDGET_SEC)
                for iid, pair in self.pairs.items()
            }
        self.app_handle = run_app_in_thread(
            self.adapter.app,
            host=ADAPTER_BIND_HOST,
            port=ADAPTER_PORT,
            thread_name="rh2-anthropic-adapter",
            runner_kwargs={
                "handler_cancellation": True,
                "access_log_class": FilteredAccessLogger,
            },
        )
        self.adapter_url = f"http://{ADAPTER_PUBLIC_HOST}:{self.app_handle.port}"
        # W3b：harness 看到的代理地址 = 本 run egress relay 的别名（每个 attempt 网络同名接入）；
        # relay 的上游 = 宿主侧 adapter（ADAPTER_PUBLIC_HOST 现在的含义 = relay 视角的宿主地址）。
        self.harness_adapter_url = self.adapter_url
        if sandbox_profile_enabled():
            self.rollout_profile = rollout_profile_from_env(
                os.environ, model_proxy_upstream_host=ADAPTER_PUBLIC_HOST,
                model_proxy_upstream_port=self.app_handle.port,
            )
            self.runtime_profile_digest = runtime_profile_digest(self.rollout_profile, self.grader_profile)
            self.harness_adapter_url = self.rollout_profile.harness_adapter_url()

        # -- 评分面：manager + F5 队列（并发 4 / 队列 8 默认）
        eval_log_dir = ARTIFACT_DIR / "eval_logs"
        eval_log_dir.mkdir(parents=True, exist_ok=True)
        self.grading_manager = SWEGradingManager(
            # W3b：非 s1 模式注入独立 grader profile（deny_all + 非 root 候选执行 + 限额）
            GradingManagerConfig(eval_log_dir=eval_log_dir, sandbox_profile=self.grader_profile)
        )
        # 轮次 13 P0-4：评分并发旋钮真实接线（此前 rh2_fa_limit_grading 是
        # 无消费者的假配置——评分并发一直由 GradingQueueConfig 独立管理）
        grading_concurrency = int(os.environ.get("RH2_FA_LIMIT_GRADING", "4"))
        self.grading_queue = GradingQueue(
            self.grading_manager,
            GradingQueueConfig(
                concurrency=grading_concurrency, queue_size=grading_concurrency * 2
            ),
            # 批 D-2（Codex 联合审查 R5）：提交者已取消时 grader 的 scope 终止失败仍经进程级入口停 run
            fatal_sink=notify_run_fatal,
        )
        self._queue_started = False

        # -- 事件流（假设核对 + 计时证据的落盘面）
        self.events_path = ARTIFACT_DIR / "bringup_events.jsonl"
        self.signals_path = ARTIFACT_DIR / "group_repair_signals.jsonl"
        self.inject_marker = ARTIFACT_DIR / "infra_injection_fired.marker"

        self.probe_evidence: dict[str, Any] | None = None
        self.policy_version: str = "step_0"
        self.orchestrator: RolloutOrchestrator | None = None
        self.started_monotonic = time.monotonic()

    # -- 一次性异步启动（探针必须在事件循环里发）---------------------------------

    async def async_start(self, args: Any) -> None:
        # codex Wave3 §9.4：owner loop 兜底绑定（__init__ 在同一个 loop 上跑，正常情况下这里是
        # no-op；只有"构造时无 running loop"的装配方式才在这里补上）。首次绑定生效，不改绑。
        self._bind_owner_loop()
        # D-FA-6 接线（FA-1）：启动即把 DISABLE_COMPACT=1 合并进
        # SLIME_AGENT_CC_EXTRA_ENVS（幂等；driver.run 内再合并一次是 no-op），
        # merged dict 进 startup evidence 供 inspector 比对。
        # F2-2 复核四轮 P1-4：模式/组合校验前移到**任何副作用之前**
        # （adapter 线程在 __init__ 已起，属既有结构——其生命周期回滚
        # 登记 FA-5；本函数内的副作用从这里开始全部受校验保护）
        try:
            await self._async_start_body(args)
        except BaseException:
            # 复核五轮 P1-3：统一回滚——queue 与 adapter 线程（app_handle）
            # 都不得遗留（配置错误后重启不能撞线程/端口）
            self._startup_rollback_errors: list[str] = []
            if getattr(self, "_queue_started", False):
                try:
                    await self.grading_queue.close(drain=False)  # 真实 API（八轮：stop 不存在）
                except BaseException as _rb_exc:  # noqa: BLE001 - 记录不覆盖首因
                    self._startup_rollback_errors.append(f"queue_close: {_rb_exc}")
                self._queue_started = False
            handle = getattr(self, "app_handle", None)
            if handle is not None:
                try:
                    handle.stop()
                except BaseException as _rb_exc:  # noqa: BLE001
                    self._startup_rollback_errors.append(f"app_stop: {_rb_exc}")
            relay = getattr(self, "egress_relay", None)
            if relay is not None:  # W3b：启动失败时 relay 容器不得遗留
                try:
                    relay_failures = await stop_egress_relay(_sandbox_docker(), relay)
                except BaseException as _rb_exc:  # noqa: BLE001
                    relay_failures = [f"relay_stop_exception: {_rb_exc}"]
                if relay_failures:
                    # F4：删除失败不得忘记 handle（容器仍带本 run label，launch trap 残留检查可见）；
                    # 错误并入 rollback errors，不覆盖启动首因。
                    self._startup_rollback_errors.append(
                        f"relay_stop: {relay.container_name}: " + "; ".join(relay_failures)
                    )
                else:
                    self.egress_relay = None
            leftovers = getattr(self, "sandbox_startup_leftovers", ())
            if leftovers:
                self._startup_rollback_errors.append(f"relay_leftover_containers: {list(leftovers)}")
            if self._startup_rollback_errors:
                print(f"[rh2-bringup] 启动回滚清理告警（首因照抛）：{self._startup_rollback_errors}")
            raise

    async def _async_start_body(self, args: Any) -> None:
        """启动事务主体（复核六轮 P0-2：探针/queue/config/orchestrator 全部
        在同一事务内，任一步失败由 async_start 的统一回滚清理 queue+app）。"""

        # 八轮：纯配置/CC guard 在资源型副作用（probe/queue）之前
        self.cc_compaction_guard_envs = None
        if HARNESS_KIND == "claude_code":
            from repoharness2.adapters.slime.generate import (
                ensure_claude_code_training_guards,
            )

            self.cc_compaction_guard_envs = ensure_claude_code_training_guards(os.environ)
        await self._run_startup_checks()
        # W3b：起本 run 的 egress relay + 在真实容器上验证两个 profile（一次），记录写 run evidence；
        # 任一必需项不符 → StartupCheckError，训练不启动（同 profile 补采不会修好它）。
        await self._start_sandbox_runtime()
        await self.grading_queue.start()
        self._queue_started = True


        template_hash = "sha256:" + hashlib.sha256(
            (self.tokenizer.chat_template or "").encode()
        ).hexdigest()

        moe_num_layers = MOE_NUM_LAYERS
        if moe_num_layers is None and EXPECT_MOE_ROUTING:
            moe_num_layers = getattr(args, "num_layers", None)
        moe_router_topk = MOE_ROUTER_TOPK
        if moe_router_topk is None and EXPECT_MOE_ROUTING:
            moe_router_topk = getattr(args, "moe_router_topk", None)

        config = SlimeBindingConfig(
            execution_mode=EXECUTION_MODE,
            model_name=MODEL_ID,
            backend_name="sglang",
            backend_version=f"sglang-{_sglang_version()}",
            renderer_cls_name=type(self.renderer).__name__,
            expected_renderer_cls_name=EXPECTED_RENDERER,
            tokenizer_name=MODEL_ID,
            template_hash=template_hash,
            adapter_url=self.harness_adapter_url,  # W3b：经 relay 别名（profile 关闭时 = 宿主地址）
            serving_precision="bfloat16",
            harness_name="claude_code" if HARNESS_KIND == "claude_code" else "mock_harness",
            expect_moe_routing=EXPECT_MOE_ROUTING,  # dense 默认 False；30B MoE 由 RH2_EXPECT_MOE_ROUTING=1 打开
            moe_num_layers=moe_num_layers,
            moe_router_topk=moe_router_topk,
            policy_version=self.policy_version,
            max_context_len=self.max_context_len,
            # W4 接缝（B-1）：consume-time 阈值的记录镜像（None = 未配置 → generate.py 哨兵行为）
            staleness_threshold=self.staleness_threshold_mirror,
            # FA-1 接线：正式链两旋钮（默认 0 = bring-up/S1 行为逐字不变；
            # FA-5 正式冒烟置 1——require 打开时启动断言会强制 reject 同开）。
            # 严格解析：只认 "0"/"1"，拼写错误直接炸（防静默关闭正式防线）
            require_real_weight_versions=parse_bool_env_flag(
                "RH2_REQUIRE_REAL_WEIGHT_VERSIONS",
                os.environ.get("RH2_REQUIRE_REAL_WEIGHT_VERSIONS"),
            ),
            reject_context_shrink=parse_bool_env_flag(
                "RH2_REJECT_CONTEXT_SHRINK", os.environ.get("RH2_REJECT_CONTEXT_SHRINK")
            ),
            # codex 轮次 9 P0-3：正式链默认联动拒绝非零 harness exit（启动
            # 断言强制耦合；env 只允许在非正式链下显式关）
            reject_on_nonzero_harness_exit=parse_bool_env_flag(
                "RH2_REJECT_NONZERO_HARNESS_EXIT",
                os.environ.get("RH2_REJECT_NONZERO_HARNESS_EXIT"),
                default=parse_bool_env_flag(
                    "RH2_REQUIRE_REAL_WEIGHT_VERSIONS",
                    os.environ.get("RH2_REQUIRE_REAL_WEIGHT_VERSIONS"),
                ),
            ),
        )
        driver = ClaudeCodeDriver() if HARNESS_KIND == "claude_code" else SimpleLoopDriver()

        def repair_signal_sink(signal) -> None:
            with self.signals_path.open("a", encoding="utf-8") as fh:
                fh.write(signal.model_dump_json() + "\n")

        self._require_real_weight_versions = config.require_real_weight_versions
        # FA-1 follow-up（codex 轮次 7 P0-4）：proxy 接入真实模型调用链。
        # 真协调器（trainer 侧）FA-4 接线；缺席期 StaticActiveCoordinator =
        # 任何中断不可归因 → poison + 缺员（保守正确）。episode 预算传播：
        # 会话首个模型调用起表（余量偏差 ≈ harness 启动秒级，记 notes）。

        # 轮次 10 一般 1：持久 artifact sink——audit tombstone 有上限会丢
        # 最旧 digest，evidence_refs 不得指向已删除对象；sink 落盘后引用是
        # 外部持久路径，不受内存淘汰影响。正式链强制配置（下方断言）。
        audit_dir = ARTIFACT_DIR / "model_call_audit"
        audit_dir.mkdir(parents=True, exist_ok=True)

        def audit_artifact_sink(attempt_id: str, payload) -> str:
            """持久 evidence sink（codex 轮次 11 P0-2 加固）：
            - 文件名 = sha256(attempt_id)（清洗/截断不再可能碰撞）；
            - 临时文件 + fsync + os.replace 原子落盘（半写文件不可见）；
            - 内容含完整 payload 的 sha256 digest（repr 截断只是预览）；
            - 返回 **相对 opaque 引用**（不泄漏本机绝对路径）。"""

            import hashlib

            from repoharness2.adapters.slime.async_worker import canonical_artifact_bytes

            name = hashlib.sha256(attempt_id.encode()).hexdigest()
            # 轮次 12 一般 3：与内存 record 同一 canonical 字节口径；契约 =
            # **digest-only evidence**（刻意不存完整私有 payload——最小化
            # 原则与密钥纪律一致；preview 有界）
            payload_bytes = canonical_artifact_bytes(payload)
            digest = hashlib.sha256(payload_bytes).hexdigest()
            record = {
                "attempt_id": attempt_id,
                "payload_sha256": digest,
                "payload_preview": payload_bytes[:4096].decode(errors="replace"),
            }
            path = audit_dir / f"{name}.json"
            if path.exists():
                existing = json.loads(path.read_text(encoding="utf-8"))
                if existing.get("payload_sha256") == digest:
                    return f"artifact:model_call_audit/{name}.json"  # 幂等重写
                raise RuntimeError(
                    f"artifact 身份碰撞：{attempt_id} 已存在且 digest 不同——"
                    "attempt 身份必须全局唯一（FA-2 唯一身份验收项）。"
                )
            tmp = audit_dir / f".{name}.tmp"
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(record, fh, ensure_ascii=False)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
            return f"artifact:model_call_audit/{name}.json"

        # 启动 write/read/delete 探针（轮次 11：磁盘满/权限错在训练前暴露）
        probe_ref = audit_artifact_sink("rh2_sink_startup_probe", {"probe": True})
        probe_path = audit_dir / probe_ref.removeprefix("artifact:model_call_audit/")
        if not probe_path.is_file() or "payload_sha256" not in json.loads(
            probe_path.read_text(encoding="utf-8")
        ):
            raise RuntimeError("artifact sink 启动探针失败：写入不可读回。")
        probe_path.unlink()

        # 轮次 13 P0-4 / 轮次 14：生产 proxy 走模块级工厂（可本地回归的
        # 装配面）。所有权：model_call 类信号量只在 adapter 线程 loop 内
        # await；worker 的 sandbox 类由 FA 入口另建——不跨 loop 共享。
        proxy = build_production_model_call_proxy(
            self.registry,
            self._observed_current_version,
            require_real=config.require_real_weight_versions,
            artifact_sink=audit_artifact_sink,
        )
        self.model_call_limits = proxy._limits
        if config.require_real_weight_versions and (
            self.registry.model_call_proxy._artifact_sink is None
        ):  # pragma: no cover - 上两行恒配置；防未来编辑退化
            raise RuntimeError("正式链必须配置持久 artifact_sink（evidence_refs 不可悬空）。")
        # 批 B（I03）：不再设 default_session_budget_seconds（首次模型调用懒起表）——正式链的
        # proxy deadline 由编排在资源占用时刻算好、经 open_session(deadline_monotonic=…) 显式
        # 下传，只有一个起点。

        runtime_barrier = None
        if EXECUTION_MODE == "fa_formal":
            from repoharness2.adapters.slime.quiescence_barrier import (
                DockerQuiescenceBarrier,
            )

            runtime_barrier = DockerQuiescenceBarrier()
        self.orchestrator = RolloutOrchestrator(
            runtime_quiescence_barrier=runtime_barrier,
            config=config,
            task_resolver=self._resolve_task,
            # W1b 第一集成切片（F4/F6）：prepared 链的评分材料按 attempt 绑定在本
            # actor 内查找/构造；legacy 链为 None（任务面内嵌 v1 spec）。
            grading_spec_resolver=(
                self._resolve_grading_spec if self.prepared_face is not None else None
            ),
            adapter_factory=self._adapter_factory,
            harness_driver=driver,
            grading_submit=self._grading_submit,
            leaf_facts_fn=bringup_leaf_facts,
            repair_signal_sink=repair_signal_sink,
            backpressure_events_source=lambda: list(self.grading_queue.events),
            artifact_dir=ARTIFACT_DIR / "rollouts",
            # finalize 时刻的 current version 提供者（W10 起只用引擎一手回包的最大观测，
            # 无记录回退启动探针值；不再经 router 随机探测一台 engine——见方法 docstring）。
            current_policy_version_provider=self._observed_current_version,
            # W3a 接缝：grader 六段分段计时来源（manager 暂存,orchestrator 取走合并进 attempt 生命周期记录）
            grader_phase_timing_source=self.grading_manager.take_grader_phase_timing,
            # W3b（D2-2）：唯一正式 rollout profile + 本 run egress relay + run 级 digest（fa_formal 必需；
            # fa_audit_only 也接同一 profile，让 GPU 探针在开闸前就验证真实边界）。
            sandbox_profile=self.rollout_profile,
            egress_relay=self.egress_relay,
            runtime_profile_digest=self.runtime_profile_digest,
            # P0-2（codex 轮次 8）：harness 返回后复检 session poison
            session_poison_check=self.registry.poison.is_poisoned,
            # P0-4（codex 轮次 9）：poison 即主动取消 harness task
            session_poison_subscribe=self.registry.poison.subscribe,
            session_poison_unsubscribe=self.registry.poison.unsubscribe,
            # 轮次 11：清理完成后才归档 poison（真 ACK；unregister 不再释放）
            session_poison_release=self.registry.poison.release,
            # 批 B（I03）：poison 原因读取——episode_deadline_exhausted 归 hard_wall 而非 api_failure
            session_poison_reason=self.registry.poison.reason,
            # 批 C（I02）：turn 预算事实（capture wire 包装 vendored _check_turn_cap 写入 registry）
            turn_budget_subscribe=self.registry.subscribe_turn_budget,
            turn_budget_unsubscribe=self.registry.unsubscribe_turn_budget,
            turn_budget_snapshot=self.registry.turn_budget_snapshot,
            # 轮次 12 P0 层 1：评分前交付账边界断言
            capture_boundary_check=self.registry.assert_session_clean,
            # 轮次 13 P0-5：execution 终态审计落盘（FA 路径不走 record_event）
            audit_sink=self._write_execution_audit,
            # B5：receipt + artifact body durable handoff（cleanup 前置
            # 条件）。s1_compat 不注入——与"无 store 的 S1 回归"口径一致
            # （B5 复核非阻塞项）；receipt 语义从 fa_audit_only 起生效。
            finalization_store=(
                FileFinalizationStore(ARTIFACT_DIR / "finalization")
                if EXECUTION_MODE != "s1_compat"
                else None
            ),
            # F2-3 批 2a：adapter event-loop 单 owner drain（app 线程已在
            # 上方启动，loop 句柄可用）
            session_drain_owner=make_threadsafe_session_drain_owner(
                self.registry, self.app_handle.loop
            ),
        )

    async def _start_sandbox_runtime(self) -> None:
        """W3b：起本 run 的 egress relay，并用同一 verify 入口（W7 远端调用的也是它）在真实容器上核对
        两个 profile。记录（digest + 参数 + 探针实际值）写 ARTIFACT_DIR/runtime_profile.json **一次**。"""

        if not sandbox_profile_enabled():
            return
        assert self.rollout_profile is not None
        docker = _sandbox_docker()
        run_id = os.environ.get("MILES_RH2_RUN_ID") or f"local-{os.getpid()}"
        labels = ("--label", f"rh2.run_id={run_id}")
        try:
            self.egress_relay = await start_egress_relay(docker, self.rollout_profile, run_id=run_id, labels=labels)
        except SandboxNetworkError as exc:
            # F4：relay 起了但未就绪/镜像 digest 不符且自行 rm 失败 → 容器残留，记进 service 证据
            # （启动回滚并入 rollback errors；label 残留检查也能看到它）。
            self.sandbox_startup_leftovers = tuple(exc.leftover_containers)
            detail = str(exc)
            if exc.leftover_containers:
                detail += f"；残留容器：{list(exc.leftover_containers)}"
            raise StartupCheckError("egress_relay_start_failed", detail) from exc
        image = SANDBOX_VERIFY_IMAGE or next(iter(self.task_specs.values())).image
        record = await verify_sandbox_profiles(
            docker, rollout=self.rollout_profile, grader=self.grader_profile, image=image, run_id=run_id,
            relay=self.egress_relay, labels=labels, expect_upstream_http=True,
        )
        record["adapter_url_host_side"] = self.adapter_url
        record["harness_adapter_url"] = self.harness_adapter_url
        record["execution_mode"] = EXECUTION_MODE
        record["fork_threshold_tokens"] = FORK_THRESHOLD_TOKENS  # I01：B 路线接线值（供事件 join）
        # 批 B（I03）：episode 预算（资源占用起表，含准备 / 引导 / 排队；数值 = SWE_AGENT_TIME_BUDGET_SEC）
        record["episode_budget_seconds"] = AGENT_TIME_BUDGET_SEC
        record["disposition_policy"] = dict(DISPOSITION_POLICY_VALUES)  # 批 D（I04）：已批处置
        record["turn_budget_requests"] = MAX_TURNS_PER_SID  # 批 C（I02）：每 sid 接纳的模型请求数上限
        self.runtime_profile_record = record
        write_runtime_profile_record(ARTIFACT_DIR / "runtime_profile.json", record)
        if not record["ok"]:
            raise StartupCheckError(
                "sandbox_profile_verification_failed",
                "W3b 启动前验证未通过（不启动训练）：" + "; ".join(record["failures"])[:800],
            )

    def _observed_current_version(self) -> str:
        """finalize 握手 / proxy 窗口所用的 current version（W10 起**只用引擎一手回包**）。

        = capture wire 逐轮记录的 `meta_info.weight_version`（含 spans 内全部版本）里的数值
        最大值（锁内快照后遍历）；尚无记录时回退启动探针实测值 `self.policy_version`。

        删除了什么：此前这里经 router 发 GET `/model_info`（fallback `/get_weight_version`）
        问"权威版本"，再用 registry 最大观测做交叉检查（观测 > 权威即 RuntimeError）。多 engine
        下 MilesRouter 把该 GET 随机落到任意一台 engine：更新窗口内探到未更新 engine、而 capture
        已从已更新 engine 观测到新版本时，交叉检查把瞬态偏斜判成"版本管道错乱"**假红崩溃**
        （router_targeting_audit.md §4）。B-1 改判后 finalize-time staleness 不再是任何资格门
        （consume-time `--max-weight-staleness` 是唯一权威，current published 版本由 miles
        buffer 持有），该探测已无资格用途，随 W10 删除（决策包 B-5b）。

        本值的口径 = "截至目前引擎向本进程报告过的最新版本"这一**观测上界**：
        - 一定 ≥ 本轨迹任何 turn 的 behavior 版本（同一 registry），所以 `_build_handshake` 的
          "seen 比 current 新"矛盾检查不会因取数方式假红；
        - 可能滞后于 trainer 刚发布、尚未服务过本进程任何请求的版本——只让 finalize-time lag
          的**观测值**偏小，不影响任何准入判定（lag 只记观测）。
        publish 后的版本收敛事实由 miles 侧经 engine actor 逐台核对（integration tree
        `RolloutManager.set_weight_version`，patch 0015），不经 router。
        """

        latest: int | None = None
        for versions in self.registry.snapshot_weight_versions().values():
            for version in versions:
                try:
                    value = int(str(version), 10)
                except ValueError:
                    continue
                latest = value if latest is None or value > latest else latest
        if latest is not None:
            return str(latest)
        return self.policy_version

    async def _run_startup_checks(self) -> None:
        """U-G renderer 断言 + U-H tape 探针。

        探针**走生产同一条 wire 路径**（capture_wire 替换后的
        call_sglang_generate + 真实 AnthropicAdapter 的 url/参数面），而不是
        手搓 HTTP 体——首日实测手搓探针被 router/引擎以 400 拒（体形状与
        生产路径分叉），改走同路径后探针失败即生产失败，证据同源。
        原始响应经 capture registry 的暂存槽取出（探针轮不 record_turn，
        不会污染任何轨迹）。
        """

        import types

        from slime.agent.adapters import common as slime_common
        from repoharness2.adapters.slime.generate import GenerationCaptureHook

        probe_messages = [{"role": "user", "content": "ping"}]
        # return_dict=False 必须显式：新版 transformers 该函数默认返回
        # BatchEncoding（dict），直接当 input_ids 用会把键名字符串发给引擎
        # （router 报 "did not match any variant of untagged enum InputIds"，
        # run5 实测）。
        ids = self.tokenizer.apply_chat_template(
            probe_messages, tokenize=True, add_generation_prompt=True, return_dict=False
        )
        if isinstance(ids, dict):  # 兼容仍返回 dict 的版本
            ids = ids["input_ids"]
        probe_sid = "rh2-startup-probe"
        probe_hook = GenerationCaptureHook(
            trajectory_id=probe_sid,
            model_name=MODEL_ID,
            backend_name="sglang",
            backend_version=f"sglang-{_sglang_version()}",
            renderer_cls_name=type(self.renderer).__name__,
            tokenizer_name=MODEL_ID,
            template_hash="sha256:" + "0" * 64,
        )
        self.registry.register(probe_sid, probe_hook)
        try:
            # B2（R6-ext）：探针按引擎二选一请求 tape——两约定互斥（与
            # generate.py 会话默认键同一开关来源 rh2_engine_sampling_mask）。
            if self.engine_sampling_mask:
                probe_defaults: dict[str, Any] = {
                    "temperature": 1.0,
                    "top_p": 0.95,
                    # 有限支持集硬上界（T0-A）；None 会被 wire 前置校验拒绝
                    "top_k": self._probe_top_k,
                    "max_new_tokens": 16,
                    "return_sampling_mask": True,
                    "return_routed_experts": EXPECT_MOE_ROUTING,
                }
            else:
                probe_defaults = {
                    "temperature": 1.0,
                    "top_p": 0.95,
                    "max_new_tokens": 16,
                    "return_top_p_token_ids": True,
                    "return_routed_experts": EXPECT_MOE_ROUTING,
                }
            session = types.SimpleNamespace(
                sampling_defaults=probe_defaults,
                max_context_tokens=0,
            )
            await slime_common.call_sglang_generate(
                list(ids), session, {}, adapter=self.adapter, session_id=probe_sid
            )
            # codex 轮次 11 P0-1：pending 是 list[PendingTurn]——经形状权威
            # helper 取恰好一条（旧代码按单对象取会 AttributeError 崩启动）
            turn = self.registry.single_pending_turn(probe_sid)
            data = turn.raw_response
            probe_params = turn.capture_params
        finally:
            self.registry.unregister(probe_sid)

        evidence = startup_checks(
            renderer=self.renderer,
            expected_renderer_cls_name=EXPECTED_RENDERER,
            probe_sampling_params=probe_params,  # 生产路径生效值（含两个 tape flag）
            probe_response=data,
            prompt_token_count=len(ids),
            expect_routing_tape=EXPECT_MOE_ROUTING,  # dense 默认不请求；MoE（J4）按口径断言
            moe_num_layers=MOE_NUM_LAYERS,
            moe_router_topk=MOE_ROUTER_TOPK,
        )
        meta = data.get("meta_info") or {}
        if meta.get("weight_version") is not None:
            self.policy_version = str(meta["weight_version"])  # 假设 4：引擎实测事实源
        evidence["engine_weight_version"] = meta.get("weight_version")
        evidence["sglang_url"] = self.sglang_url
        # W10 / codex Wave3 §9.3：router worker 池事实 + **精确数量核对**（见 _verify_router_worker_set）。
        # 这份集合不只是证据：实时 `/list_workers` 失败时它就是 abort 广播的唯一目标集合，
        # 集合不完整 = 只向部分 engine 投递却报 delivered，真正持有 rid 的 engine 继续占槽。
        # 因此 fa_formal 下核对不过就不能进入 RUNNING（错误在本方法末尾、证据落盘之后抛出）。
        worker_check_error = await self._verify_router_worker_set(evidence)
        evidence["adapter_url"] = self.adapter_url
        evidence["harness_kind"] = HARNESS_KIND
        # W3b：run 级 profile 摘要（完整记录在 runtime_profile.json）与 harness 侧代理地址
        evidence["runtime_profile_digest"] = self.runtime_profile_digest
        evidence["harness_adapter_url"] = self.harness_adapter_url
        # D-FA-6 探针证据：合并进 CC 子进程环境的 extra-envs（async_start 急切
        # 合并；inspector 比对 DISABLE_COMPACT=1 在场，FA-5 短租对真实子进程验真）
        evidence["cc_compaction_guard_envs"] = getattr(
            self, "cc_compaction_guard_envs", None
        )
        self.probe_evidence = evidence
        (ARTIFACT_DIR / "startup_evidence.json").write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False)
        )
        # 证据先落盘再拒绝启动：诊断需要 startup_evidence.json 里的 router_workers 段
        # （expected_count / count / urls / verified）。fa_formal 之外只记录不阻断。
        if worker_check_error is not None and EXECUTION_MODE == "fa_formal":
            raise StartupCheckError("router_workers_unverified", worker_check_error)

    async def _verify_router_worker_set(self, evidence: dict[str, Any]) -> str | None:
        """核对 router 注册的 worker 集合是否 == 固定 topology 的全部 engine（codex Wave3 §9.3）。

        为什么必须核对：abort 广播在实时 `/list_workers` 失败时会退回这份"启动核对集合"，
        并且**只要集合里每个 URL 都返回 2xx 就报 delivered**。启动那一刻若只有 engine A 注册、
        engine B 稍后才注册并持有 rid，未核对的集合就会让一次实际只到 A 的 abort 被记成"已证明到达"，
        B 上的请求继续占 SGLang 生成槽位。

        核对规则（首版不引入健康检查平台，也不做弹性 engine 管理）：

        1. 预期数 = `expected_engine_count(self._profile_args)`（miles 固定 topology 的算式）；
        2. 实际集合 = `/list_workers` 返回值经 `worker_base_urls()` **规范化 + 去重**（去 `@rank`
           后缀与尾斜杠，与 miles `router_worker_base_urls` 同款）后的数量；
        3. **精确相等**才算核对通过——多一个（陌生 worker，可能是别的 run 或 PD/多模型组）
           与少一个（engine 未注册完）同样拒绝；
        4. 预期数算不出来（args 缺参/不整除，见 helper）也算核对失败：不能声称核对过。

        返回 ``None`` = 核对通过（此时、且仅此时把集合交给 router client 作 abort 回退集合）；
        返回字符串 = 失败原因（调用方在 fa_formal 下据此抛 `StartupCheckError`；其余模式只记录）。
        无论成败都把事实写进 ``evidence["router_workers"]``。
        """

        expected = expected_engine_count(self._profile_args)
        try:
            worker_urls = await self.router_workers.list_workers()
        except Exception as exc:  # noqa: BLE001 —— 查询失败 ≠ 空集合：不能据此声称核对过
            evidence["router_workers"] = {
                "error": f"{type(exc).__name__}: {exc}"[:300],
                "expected_count": expected,
                "verified": False,
            }
            reason = (
                f"router `/list_workers` 查询失败，无法核对 engine 集合完整性："
                f"expected_count={expected} error={type(exc).__name__}: {exc}"
            )[:400]
            print(f"[rh2-bringup] {reason}")
            return reason

        normalized = tuple(worker_base_urls(worker_urls))  # 规范化 + 去重后才计数
        evidence["router_workers"] = {
            "urls": list(normalized),
            "count": len(normalized),
            "raw_count": len(worker_urls),
            "expected_count": expected,
            "verified": False,
        }
        if expected is None:
            reason = (
                "预期 engine 数算不出来（miles args 缺 rollout_num_gpus / "
                "rollout_num_gpus_per_engine，或两者不整除 / per-engine 超过单节点卡数）："
                f"router 实际登记 {len(normalized)} 个 worker，但没有可比对的预期值。"
            )
        elif len(normalized) != expected:
            reason = (
                f"router worker 数量与固定 topology 不符：预期 {expected} 个 engine"
                f"（rollout_num_gpus // rollout_num_gpus_per_engine），实际登记 {len(normalized)} 个："
                f"{list(normalized)}"
            )[:400]
        else:
            # 只有精确相等才把集合标成 verified 并交给 router client——不完整集合绝不下发。
            evidence["router_workers"]["verified"] = True
            self.verified_router_workers = normalized
            self.router_workers.set_verified_workers(normalized)
            return None
        print(f"[rh2-bringup] router worker 集合未通过核对：{reason}")
        return reason

    # -- 编排可注入件 ----------------------------------------------------------

    def _resolve_task(self, sample: Any):
        metadata = getattr(sample, "metadata", None) or {}
        # W5a：任务面的第一件事——关停后 typed 拒绝（ServiceClosedError，不是 abort
        # 形状），未关停则把当前执行 task 登记进在飞表并挂 run-fatal 通知器。
        # 这里是 orchestrator 9 步生命周期的 step1 之前（generate.py 先解析任务再建
        # audit），所以被拒的执行不会留下任何 audit/receipt——只在关停报告里计数。
        self.lifecycle.enter_execution(metadata)
        if self.prepared_face is not None:
            # prepared 链（F4）：只按样本自带的 attempt 绑定解析——样本回显的
            # task_id/digest 只用来与 host 原始分派逐字比对，不一致即拒绝。
            assignment = self.attempt_assignments.resolve_for_sample(metadata)
            return self.prepared_face.rollout_spec(assignment.task_id)
        iid = metadata.get("instance_id") or getattr(sample, "label", None)
        if iid not in self.task_specs:
            raise ValueError(f"样本没有可识别的 instance_id（metadata/label 均未命中）: {iid!r}")
        return self.task_specs[iid]

    def _resolve_grading_spec(self, sample: Any):
        """prepared 链评分材料取数口（orchestrator 的 grading_spec_resolver）：
        attempt 绑定 → host grading 视图（消费时刻 revalidated）→ 本进程内构造 spec。"""

        metadata = getattr(sample, "metadata", None) or {}
        assignment = self.attempt_assignments.resolve_for_sample(metadata)
        return self.prepared_face.grading_spec(assignment)

    def _write_execution_audit(self, audit) -> None:
        try:
            write_execution_audit_record(
                self.registry.model_call_proxy, audit, ARTIFACT_DIR / "fa_execution_audit.jsonl"
            )
        finally:
            # W5a：audit sink 在 generate.py 的 finally 里（receipt→cleanup 之后）被调，
            # 是每次执行的最后一个 bringup 注入点——在此注销在飞登记。
            self.lifecycle.exit_execution()

    def _adapter_factory(self, hook, session_defaults):
        return make_per_rollout_adapter(self.registry, self.adapter, hook)

    async def _grading_submit(self, *, trajectory_id, workspace, spec, frozen_delta=None):
        # W5a：评分面在关停链的 grading_queue 步之后关闭（比停收新执行晚——在飞
        # 执行在宽限期内仍要把评分提交完）；关闭后 typed 拒绝。
        self.lifecycle.require_grading_open("grading_submit")
        # frozen_delta 透传（B4 tracer 发现的潜伏缺口）：bringup 今日硬拒
        # fa_formal（唯一会组装 frozen_delta 的模式），但签名若不同步，
        # fa_formal 解禁时 _grade 传 kwarg 会 TypeError 塌成 per-member
        # abort，B4 绑定/重建检查一次都不执行——先把管道铺平。
        if INJECT_INFRA_INSTANCE and spec.task_id == INJECT_INFRA_INSTANCE:
            fired = False
            try:  # marker 文件 O_EXCL 原子创建 = 恰好注入一次
                fd = os.open(self.inject_marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w") as fh:
                    fh.write(trajectory_id + "\n")
                fired = True
            except FileExistsError:
                fired = False
            if fired:
                spec = dataclasses.replace(spec, eval_script=_INJECTED_EVAL_SCRIPT)
        return await self.grading_queue.submit(
            trajectory_id=trajectory_id, workspace=workspace, spec=spec,
            frozen_delta=frozen_delta,
        )

    # -- 事件记录 --------------------------------------------------------------

    def record_event(self, *, args: Any, sample: Any, result: list, wall_seconds: float) -> None:
        sid = getattr(sample, "session_id", None)
        audit = None
        if self.orchestrator is not None:
            for candidate in reversed(self.orchestrator.audits):
                if candidate.trajectory_id == sid:
                    audit = candidate
                    break
        finalized = audit.finalized if audit else None
        grading = finalized.grading_report if finalized else None
        event = {
            "ts": time.time(),
            "session_id": sid,
            "index": getattr(sample, "index", None),
            "group_index": getattr(sample, "group_index", None),  # 假设 10 实测核对
            "instance_id": (getattr(sample, "metadata", None) or {}).get("instance_id"),
            "wall_seconds": round(wall_seconds, 2),
            "returned_samples": len(result),
            "statuses": [str(getattr(s, "status", None)) for s in result],
            "remove_sample": [bool(getattr(s, "remove_sample", False)) for s in result],
            "abort_reason": [
                (getattr(s, "metadata", None) or {}).get("abort_reason") for s in result
            ],
            "response_lengths": [getattr(s, "response_length", None) for s in result],
            "loss_mask_ones": [
                sum(getattr(s, "loss_mask", None) or []) for s in result
            ],
            "truncated_meta": [
                (getattr(s, "metadata", None) or {}).get("truncated") for s in result
            ],  # 假设 6
            "weight_versions_engine": self.registry.weight_versions.get(sid, []),  # 假设 4
            "weight_versions_sample": [
                list(getattr(s, "weight_versions", None) or []) for s in result
            ],
            "rewards": [getattr(s, "reward", None) for s in result],
            "top_p_offsets_len": [
                len(getattr(s, "rollout_top_p_token_offsets", None) or []) for s in result
            ],
            "capture_stats": dict(self.registry.stats),
            "audit_steps": list(audit.steps) if audit else None,
            "audit_timeline": audit.timeline_dicts() if audit else None,
            "rollout_timings": audit.timing_summary() if audit else None,
            "harness_exit_code": audit.harness_exit_code if audit else None,
            "failure_records": (
                [
                    {"stage": f.stage, "error_type": f.error_type, "detail": f.detail[:200]}
                    for f in audit.failure_records
                ]
                if audit
                else None
            ),
            "cleanup_failures": (
                [f"{c.step}:{c.detail[:120]}" for c in audit.cleanup_failures] if audit else None
            ),
            "grading": (
                {
                    "outcome": grading.outcome,
                    "failure_category": grading.failure_category,
                    "reward": grading.reward,
                    "timings": json.loads(grading.timings.model_dump_json())
                    if grading.timings
                    else None,
                }
                if grading
                else None
            ),
            "eligibility_class": (
                finalized.eligibility_report.eligibility_class if finalized else None
            ),
            "degraded": (
                finalized.group_repair_signal.degraded if finalized else None
            ),
        }
        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

    # -- W5a 关停链 -------------------------------------------------------------
    #
    # 顺序（就绪稿 §2.6 的 rh2 侧；miles producer/RolloutManager.dispose 是只读代码，
    # 由集成者在 dispose 里调 close_bringup_service() 一行接上）：
    #   intake_stop → evidence_begin → inflight_executions（先等后取消再等）
    #   → grading_queue（有界 drain，超时改 cancel）→ grading_manager（gc 全部记账容器）
    #   → capture_sessions（残留 session 撤销/drop/注销）→ capture_registry_close（registry 关闭）
    #   → adapter_http（aiohttp 线程停）→ container_residue（只记事实）
    #   → resource_closure（一次性取数）→ [链外] shutdown_report.json + 完成事件
    # 每步有界超时；首因（触发异常或第一个失败步）保留，其后失败记次生；普通
    # evidence 写失败不阻止任何 cleanup 步；close() 幂等（同一 task/同一报告）。

    def _append_event(self, event: dict[str, Any]) -> None:
        """往 bringup_events.jsonl 追加一行（与 record_event 同文件、同格式）。失败抛。"""

        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": time.time(), **event}, ensure_ascii=False, default=str) + "\n")

    def _memory_estimate_inputs(self) -> tuple[MemoryEstimateInputs | None, list[str]]:
        """从 miles/slime args + bringup 旋钮装配内存估计输入；缺项如实返回（不猜）。

        口径（codex W5a 复核 #7）：这是**估计**不是上界——`planned_attempts` 是计划量
        （steps × batch × n），不是 attempt cap（dynamic filter 持续拒绝时补采无上限）；
        buffer 容量按 miles `async_data_buffer_capacity_factor × batch` 计入。
        """

        args = self._profile_args
        missing: list[str] = []

        def need(name: str) -> Any:
            value = getattr(args, name, None)
            if value is None:
                missing.append(name)
            return value

        batch = need("rollout_batch_size")
        n_per_prompt = need("n_samples_per_prompt")
        steps = need("num_rollout")
        max_new = need("rollout_max_response_len")
        top_k: Any = 1
        if self.engine_sampling_mask:
            top_k = getattr(args, "rollout_top_k", None)
            if not isinstance(top_k, int) or top_k < 1:
                missing.append("rollout_top_k")
        if missing:
            return None, missing
        concurrent = getattr(args, "async_max_concurrent_samples", None) or int(batch) * int(n_per_prompt)
        capacity_factor = getattr(args, "async_data_buffer_capacity_factor", None)
        buffer_groups = int(float(capacity_factor) * int(batch)) if capacity_factor else 0  # 0 = 未知
        return (
            MemoryEstimateInputs(
                max_concurrent_executions=int(concurrent),
                grading_concurrency=int(self.grading_queue.config.concurrency),
                model_call_limit=int(os.environ.get("RH2_FA_LIMIT_MODEL_CALL", "32")),
                max_turns_per_execution=int(MAX_TURNS_PER_SID),
                max_new_tokens_per_turn=int(max_new),
                max_context_tokens=int(self.max_context_len or 0),
                top_k_support=int(top_k),
                planned_attempts=int(steps) * int(batch) * int(n_per_prompt),  # 计划量，非上限
                buffer_capacity_groups=buffer_groups,
                samples_per_group=int(n_per_prompt),
            ),
            [],
        )

    def _build_shutdown_steps(self) -> list[ShutdownStep]:
        t = self.shutdown_timeouts

        async def intake_stop() -> dict[str, Any]:
            self.lifecycle.stop_intake()
            return {"inflight_at_stop": self.lifecycle.inflight_count}

        async def evidence_begin() -> dict[str, Any]:
            self._append_event({"event": "shutdown_started", "inflight": self.lifecycle.inflight_count})
            return {"events_path": str(self.events_path)}

        async def inflight_executions() -> dict[str, Any]:
            return await close_inflight_executions(
                self.lifecycle,
                grace_seconds=t.inflight_grace,
                cancel_wait_seconds=t.inflight_cancel_wait,
            )

        async def grading_queue() -> Any:
            self.lifecycle.close_grading()
            if not getattr(self, "_queue_started", False):
                return Skipped("grading queue never started")
            drained = True
            try:
                await asyncio.wait_for(self.grading_queue.close(drain=True), timeout=t.grading_drain)
            except (TimeoutError, asyncio.TimeoutError):
                drained = False
                await self.grading_queue.close(drain=False)  # 超时：撤 worker（worker 的 finally 会删自己的容器）
            self._queue_started = False
            return {"drained_within_timeout": drained, "backpressure_events": len(self.grading_queue.events)}

        async def grading_manager() -> dict[str, Any]:
            return await self.grading_manager.close()

        async def capture_sessions() -> dict[str, Any]:
            with self.registry._lock:
                sids = list(self.registry.hooks)
            dropped: list[str] = []
            failed: dict[str, str] = {}
            for sid in sids:
                self.registry.revoke(sid)  # HTTP 层先拒新请求
                try:
                    await asyncio.wait_for(self.adapter.drop_session(sid, wait_timeout=5.0), timeout=10.0)
                    dropped.append(sid)
                except Exception as exc:  # noqa: BLE001 —— 单个 session 失败不阻断其余
                    failed[sid] = f"{type(exc).__name__}: {exc}"[:200]
                finally:
                    self.registry.unregister(sid)
            return {"sessions_dropped": dropped, "sessions_drop_failed": failed}

        async def capture_registry_close() -> dict[str, Any]:
            # 独立小步（同步、瞬时）：即使上一步 drop 超时被取消，registry 也必须关——
            # 关闭后 HTTP guard 对一切请求 403、register 拒绝，是"关闭后禁 submit"的 HTTP 面。
            hooks_left = self.registry.close()
            return {"hooks_left_after_close": hooks_left}

        async def adapter_http() -> Any:
            handle = getattr(self, "app_handle", None)
            if handle is None:
                return Skipped("adapter app never started")
            if not handle.thread.is_alive():
                return Skipped("adapter thread already stopped")
            await asyncio.to_thread(handle.stop)  # AppHandle.stop 是阻塞调用（runner.cleanup + join）
            return {"thread_alive_after_stop": handle.thread.is_alive()}

        async def container_residue() -> dict[str, Any]:
            orchestrator = self.orchestrator
            return {
                "quarantined_containers": list(orchestrator.cleanup_quarantine) if orchestrator is not None else [],
                "grading_containers_open": [r.name for r in self.grading_manager.container_records if not r.removed],
                "grading_cleanup_failures": list(self.grading_manager.cleanup_failures),
            }

        async def egress_runtime() -> dict[str, Any]:
            """W3b：删本 run 残留的 attempt 私有网络（先断开 relay），再删 relay 容器。
            profile 未启用时如实 skipped。"""

            relay = getattr(self, "egress_relay", None)  # 部分构造的 service（测试）也能走关停链
            if relay is None and not sandbox_profile_enabled():
                return {"skipped": "sandbox profile 未启用（s1_compat）"}
            docker = _sandbox_docker()
            run_id = relay.run_id if relay is not None else (
                os.environ.get("MILES_RH2_RUN_ID") or f"local-{os.getpid()}"
            )
            facts: dict[str, Any] = {
                "relay": relay.container_name if relay is not None else None,
                "relay_removed": False,
                "networks_removed": [],
                "failures": [],
            }
            nets = await list_labeled_networks(docker, label=f"rh2.run_id={run_id}")
            if nets is None:
                facts["failures"].append("network_ls_failed")
            else:
                for net in nets:
                    fails = await teardown_attempt_network(docker, network_name=net, relay=relay)
                    if fails:
                        facts["failures"] += [f"{net}:{f}" for f in fails]
                    else:
                        facts["networks_removed"].append(net)
            if relay is not None:
                fails = await stop_egress_relay(docker, relay)
                facts["failures"] += fails
                facts["relay_removed"] = not fails
                if not fails:
                    self.egress_relay = None
            return facts

        async def resource_closure() -> dict[str, Any]:
            inputs, missing = self._memory_estimate_inputs()
            growth = collect_growth_facts(
                orchestrator=self.orchestrator,
                grading_manager=self.grading_manager,
                grading_queue=self.grading_queue,
                registry=self.registry,
            )
            facts = await asyncio.to_thread(
                resource_closure_facts,
                phase="shutdown",
                memory_inputs=inputs,
                fsync_dir=ARTIFACT_DIR,
                growth=growth,
            )
            if missing:
                facts["memory_estimate"]["missing_inputs"] = missing
            path = write_resource_closure_facts(ARTIFACT_DIR / "resource_closure.json", facts)
            return {
                "path": str(path),
                "memory_estimate_status": facts["memory_estimate"].get("status"),
                "memory_estimate_bytes": facts["memory_estimate"].get("estimate_bytes"),
                "fsync_p95_ms": facts["fsync_latency"].get("p95_ms"),
                "missing_inputs": missing,
            }

        return [
            ShutdownStep("intake_stop", intake_stop, 1.0, kind="control"),
            ShutdownStep("evidence_begin", evidence_begin, t.evidence, kind="evidence"),
            ShutdownStep(
                "inflight_executions", inflight_executions, t.inflight_grace + t.inflight_cancel_wait + 5.0
            ),
            ShutdownStep("grading_queue", grading_queue, t.grading_drain + 15.0),
            ShutdownStep("grading_manager", grading_manager, t.grading_manager),
            ShutdownStep("capture_sessions", capture_sessions, t.capture_sessions),
            ShutdownStep("capture_registry_close", capture_registry_close, 1.0, kind="control"),
            ShutdownStep("adapter_http", adapter_http, t.adapter_http),
            ShutdownStep("container_residue", container_residue, t.container_residue),
            # W3b：容器面清完之后删 attempt 网络与 relay（网络必须没有端点才能删）
            ShutdownStep("egress_runtime", egress_runtime, t.container_residue),
            ShutdownStep("resource_closure", resource_closure, t.resource_closure, kind="evidence"),
        ]

    def _absorb_fatals_during_close(self, report: ShutdownReport) -> int:
        """把关停进行中到达的 run-fatal 全部记进报告（首因为空则设为首因，否则次生）。"""

        absorbed = 0
        while self._fatals_during_close:
            exc = self._fatals_during_close.pop(0)
            report.note_failure("run_fatal_during_shutdown", describe_exception(exc))
            absorbed += 1
        return absorbed

    async def _run_close(
        self,
        reason: str,
        trigger: str,
        first_cause: BaseException | str | None,
        secondary_causes: tuple[str, ...] = (),
        external_residue: dict[str, Any] | None = None,
    ) -> ShutdownReport:
        report = ShutdownReport(reason=reason, trigger=trigger)
        self._closing_report = report
        # 首次调用带的事实与后到事实走同一合并口（patch 0013）：首因/次生立即并入，残留
        # 推迟到链后（此时 report.residue 还没装配）
        self._merge_late_facts(
            report,
            first_cause=first_cause,
            trigger=trigger,
            secondary_causes=secondary_causes,
            external_residue=external_residue,
            phase="initial",
        )
        self._absorb_fatals_during_close(report)
        self._absorb_pending_late_facts(report)
        report = await run_shutdown_chain(
            self._build_shutdown_steps(), reason=reason, trigger=trigger, first_cause=None, report=report
        )
        self._absorb_fatals_during_close(report)
        self._absorb_pending_late_facts(report)
        # 残留汇总（H9 判据的输入：任一非空 = 残留）
        def facts_of(name: str) -> dict[str, Any]:
            step = report.step(name)
            return dict(step.facts) if step is not None and step.facts else {}

        inflight = facts_of("inflight_executions")
        sessions = facts_of("capture_sessions")
        registry_close = facts_of("capture_registry_close")
        containers = facts_of("container_residue")
        http = facts_of("adapter_http")
        egress = facts_of("egress_runtime")
        report.residue = {
            "unfinished_executions": inflight.get("unfinished_after_cancel_wait", []),
            "quarantined_containers": containers.get("quarantined_containers", []),
            "grading_containers_open": containers.get("grading_containers_open", []),
            "sessions_drop_failed": sessions.get("sessions_drop_failed", {}),
            "hooks_left_after_close": registry_close.get("hooks_left_after_close", 0),
            "adapter_thread_alive": bool(http.get("thread_alive_after_stop", False)),
            # F4（codex Wave3 复核）：egress relay / attempt 网络删除失败 = 残留（不是"步骤 ok 但 facts 里有失败"）
            # → residue_free=False → ok=False。network ls 失败同样进这里（查询失败 ≠ 零残留）。
            "egress_cleanup_failures": list(egress.get("failures", []) or []),
            "egress_relay_left": (
                egress.get("relay") if egress.get("relay") and not egress.get("relay_removed") else None
            ),
        }
        # patch 0012/0013：miles rollout fn 关停到期放弃的 worker/组（具体组标识 + 原因）并入
        # 残留——任一非空即 residue_free=False → ok=False，不再假绿。链前到达的残留在此并入。
        while self._deferred_residues:
            self._merge_residue(report, self._deferred_residues.pop(0))
        report.rejected_after_close = dict(self.lifecycle.rejected_after_close)
        self.lifecycle.mark_closed()
        if type(self)._instance is self:
            type(self)._startup_state = "CLOSED"
        if self._uninstall_signal_shutdown is not None:
            try:
                self._uninstall_signal_shutdown()  # 关停完成后第二个 SIGTERM 按默认处置（真退出）
            finally:
                self._uninstall_signal_shutdown = None
        # 链外 evidence flush（codex W5a 复核 #3a：磁盘报告必须**最后**生成，此前的一切失败——
        # 含完成事件写失败、关停期间到达的 fatal——都要反映在落盘的那一份里）：
        #   1. 追加 shutdown_completed 事件（失败 → evidence 失败进报告）；
        #   2. 再次吸收关停期间到达的 fatal；
        #   3. 最后原子写 shutdown_report.json（自身写失败只能留在内存报告与 stdout）。
        try:
            self._append_event(
                {"event": "shutdown_completed", "ok": report.ok, "first_cause": report.first_cause,
                 "residue": report.residue}
            )
        except Exception as exc:  # noqa: BLE001
            report.note_evidence_failure("evidence:shutdown_completed_event", f"{type(exc).__name__}: {exc}"[:300])
        self._absorb_fatals_during_close(report)
        self._absorb_pending_late_facts(report)
        self.shutdown_report = report
        self._closing_report = None  # 此后到达的 fatal 只进 lifecycle.fatal_seen；后到的 close() 事实走合并重写
        try:
            self._write_report_to_disk(report)
        except Exception as exc:  # noqa: BLE001
            report.note_evidence_failure("evidence:shutdown_report", f"{type(exc).__name__}: {exc}"[:300])
        print(f"[rh2-bringup] shutdown {'ok' if report.ok else 'NOT ok'}: trigger={trigger} reason={reason} "
              f"first_cause={report.first_cause!r} residue={report.residue}")
        return report

    async def close(
        self,
        *,
        reason: str = "owner_close",
        trigger: str = "owner_close",
        first_cause: BaseException | str | None = None,
        secondary_causes: tuple[str, ...] | list[str] = (),
        external_residue: dict[str, Any] | None = None,
    ) -> ShutdownReport:
        """显式关停（幂等：cleanup 只执行一次）。首次调用创建关停 task；后续调用（含并发）等待
        同一 task 并拿到**同一个**报告对象。后到的事实（patch 0013，生产顺序 = filter fatal 提前
        触发 close → driver finally → dispose/aclose 才发现 driver/worker 双因与未完成组）**不丢**：
        - close 进行中：进 pending，落盘前吸收（原首因保留，后到首因按规则记 late_primary 次生）；
        - close 已完成：并入同一 ShutdownReport 并**原子重写**同一路径的磁盘报告，ok/residue_free 随之重算。
        调用方被取消不会取消关停链（shield）。永不抛异常——通常在 finally 里调。"""

        late = {
            "trigger": trigger,
            "first_cause": first_cause,
            "secondary_causes": tuple(secondary_causes),
            "external_residue": external_residue,
        }
        if self._close_task is None:
            self._close_task = asyncio.get_running_loop().create_task(
                self._run_close(reason, trigger, first_cause, tuple(secondary_causes), external_residue),
                name="rh2-bringup-shutdown",
            )
        elif first_cause is not None or secondary_causes or external_residue:
            if self.shutdown_report is None:
                self._pending_late_facts.append(late)  # 进行中：落盘前吸收
            else:
                self._amend_completed_report(**late)  # 已完成：合并 + 原子重写
        return await asyncio.shield(self._close_task)

    # -- patch 0013：后到事实的合并（唯一所有者 = 本 report） --------------------------

    def _merge_late_facts(
        self,
        report: ShutdownReport,
        *,
        first_cause: BaseException | str | None,
        trigger: str,
        secondary_causes: tuple[str, ...],
        external_residue: dict[str, Any] | None,
        phase: str,
    ) -> None:
        """优先级规则：报告已有首因则保留，后到首因记 `late_primary(<trigger>)` 次生；次生只做
        **完全相同文本**去重（与既有首因或既有次生逐字相同才跳过——不猜同源，宁可重复）；
        残留在 report.residue 装配之后并入，否则先推迟。每次并入记 late_merges 一条。"""

        if isinstance(first_cause, BaseException):
            desc: str | None = describe_exception(first_cause)
        else:
            desc = str(first_cause)[:400] if first_cause else None
        added_secondary = 0
        if desc:
            if report.first_cause is None:
                report.note_failure("trigger", desc)
            elif desc != report.first_cause:
                line = f"late_primary({trigger}): {desc}"
                if line not in report.secondary_failures:  # 逐字重复的后到首因不叠加
                    report.secondary_failures.append(line)
                    added_secondary += 1
        for cause in secondary_causes:
            text = str(cause)[:400]
            core = text.split(": ", 1)[1] if text.startswith("worker_fatal: ") else text
            line = f"secondary: {text}"
            # 规范化后**完整条目相等**才算重复（codex 复核 P1：子串判断会让已记
            # "optimizer timeout" 时后到的独立 "timeout" 被静默吞掉）。
            if core == report.first_cause or line in report.secondary_failures or f"secondary: {core}" in report.secondary_failures:
                continue
            report.secondary_failures.append(line)
            added_secondary += 1
        rows = 0
        if external_residue:
            if report.residue:
                rows = self._merge_residue(report, external_residue)
            else:
                self._deferred_residues.append(external_residue)
                rows = len(external_residue.get("unfinished_executions", []))
        if desc or secondary_causes or external_residue:
            report.late_merges.append(
                {
                    "phase": phase,
                    "trigger": trigger,
                    "first_cause": desc,
                    "secondary_added": added_secondary,
                    "residue_rows": rows,
                    "at_utc": datetime.now(timezone.utc).isoformat(),
                }
            )

    @staticmethod
    def _merge_residue(report: ShutdownReport, external_residue: dict[str, Any]) -> int:
        existing = list(report.residue.get("unfinished_executions", []))
        added = 0
        for row in external_residue.get("unfinished_executions", []):
            if row not in existing:
                existing.append(row)
                added += 1
        report.residue["unfinished_executions"] = existing
        failure = external_residue.get("rollout_fn_shutdown_failure")
        if failure is not None:
            report.residue["rollout_fn_shutdown_failure"] = failure
        elif "rollout_fn_shutdown_failure" not in report.residue:
            report.residue["rollout_fn_shutdown_failure"] = None
        return added

    def _absorb_pending_late_facts(self, report: ShutdownReport) -> int:
        absorbed = 0
        while self._pending_late_facts:
            late = self._pending_late_facts.pop(0)
            self._merge_late_facts(report, phase="during_close", **late)
            absorbed += 1
        return absorbed

    def _amend_completed_report(
        self,
        *,
        trigger: str,
        first_cause: BaseException | str | None,
        secondary_causes: tuple[str, ...],
        external_residue: dict[str, Any] | None,
    ) -> None:
        report = self.shutdown_report
        assert report is not None
        self._merge_late_facts(
            report,
            first_cause=first_cause,
            trigger=trigger,
            secondary_causes=secondary_causes,
            external_residue=external_residue,
            phase="after_close",
        )
        try:
            self._write_report_to_disk(report)  # 同一路径原子重写：ok/residue_free 随之重算
        except Exception as exc:  # noqa: BLE001
            report.note_evidence_failure("evidence:shutdown_report_rewrite", f"{type(exc).__name__}: {exc}"[:300])
        print(f"[rh2-bringup] shutdown report amended after close: ok={report.ok} first_cause={report.first_cause!r} "
              f"secondary={report.secondary_failures} residue={report.residue}")

    @staticmethod
    def _write_report_to_disk(report: ShutdownReport) -> Path:
        report_path = ARTIFACT_DIR / "shutdown_report.json"
        tmp = report_path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(report.to_dict(), fh, ensure_ascii=False, indent=1, default=str)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, report_path)
        return report_path

    # -- codex Wave3 §9.4：owner loop 归属与 run-fatal 派发 ---------------------------

    def _bind_owner_loop(self) -> asyncio.AbstractEventLoop | None:
        """记住唯一 owner loop。**首次绑定生效**，之后重复调用不改绑（服务一生只属于一个 loop）。

        构造与 `async_start` 都跑在 owner loop 上，所以直接取当前 running loop 即可。
        没有 running loop（同步装配的测试面）则留 None，语义退回"就地执行"。
        """

        if getattr(self, "_owner_loop", None) is not None:
            return self._owner_loop
        try:
            self._owner_loop = asyncio.get_running_loop()
        except RuntimeError:
            self._owner_loop = None
        return self._owner_loop

    def _on_owner_loop(self) -> bool:
        """当前调用是否已经在 owner loop 上（同 loop 内可直接执行，不必绕 call_soon_threadsafe）。"""

        loop = getattr(self, "_owner_loop", None)
        if loop is None:
            return False
        try:
            return asyncio.get_running_loop() is loop
        except RuntimeError:  # 当前线程没有运行中的 loop（纯同步线程）
            return False

    def _post_to_owner_loop(self, fn: Callable[..., Any], *args: Any) -> bool:
        """把一个同步回调排到 owner loop 上执行（线程安全）。

        返回 False = **没送到**（owner loop 未绑定 / 已关闭 / 没在跑 / 已停止接受回调）。调用方据此
        如实上报"未通知"，绝不能把投递失败当成通知成功。

        为什么连 `is_running()` 都要看：`call_soon_threadsafe` 只在 loop **已关闭**时抛
        `RuntimeError`；对一个 `stop()` 过但还没 `close()` 的 loop 它会成功入队，而那个回调永远不会跑。
        owner loop 在生产里是 `run_forever()` 直到关停，`is_running()` 为 False 只出现在
        "还没起来"或"已经停了"两种状态——两种都不能声称通知成功。
        """

        loop = getattr(self, "_owner_loop", None)
        if loop is None or loop.is_closed() or not loop.is_running():
            return False
        try:
            loop.call_soon_threadsafe(fn, *args)
        except RuntimeError:
            # is_closed()/is_running() 与 call_soon_threadsafe 之间 loop 被关掉
            return False
        return True

    def dispatch_run_fatal(self, exc: BaseException) -> bool:
        """run-fatal 的**唯一**投递口：把记账与关停调度整体放到 owner loop 上执行。

        为什么必须派回（codex Wave3 §9.4 的真实调用链）：capture wire 的 abort 升级发生在
        adapter 的 aiohttp 线程（`run_app_in_thread` 建的独立 loop）里，若就地
        `create_task(self._run_close(...))`，关停链会被建在 adapter loop 上——它随后要等
        grading queue、owner loop 上的在飞执行 task，会直接撞 "Future attached to a different loop"，
        而 abort 却已被记成 `notified=true`。

        - 已经在 owner loop 上（在飞执行内的 fatal、owner 自己的调用）→ 就地同步执行，语义不变；
        - 外来线程 / 外来 loop → `owner_loop.call_soon_threadsafe(...)` 整体派回；
        - owner loop 未绑定（只可能是没走 `get()` 的装配）→ 就地执行（无别的 loop 可言）；
        - **派回失败（loop 已关闭/已停）→ 返回 False**，调用侧记 `abort_unproven_unnotified`。
        """

        if self._on_owner_loop() or getattr(self, "_owner_loop", None) is None:
            self._record_run_fatal(exc)
            return True
        return self._post_to_owner_loop(self._record_run_fatal, exc)

    def _record_run_fatal(self, exc: BaseException) -> None:
        """owner loop 上的 run-fatal 执行体：`fatal_seen` 记账 + 关停状态检查 + 关停链调度。"""

        self.lifecycle.fatal_seen.append(exc)
        self._on_run_fatal(exc)

    def _on_run_fatal(self, exc: BaseException) -> None:
        """run-fatal 通道（generate.py `_notify_fatal_halt` 经 task-local 通知器同步调）：
        首次 fatal 即调度关停链（首因 = 该 fatal）。在飞的 fatal 执行自己会先把 receipt
        持久化再清理（B5），关停链的 inflight 步只是等它跑完。

        codex Wave3 §9.4：本函数体**必须跑在 owner loop 上**——关停状态检查（`_close_task` /
        `_closing_report`）与 `_close_task` 创建是同一份状态的读改写，且创建出来的 task 必须属于
        owner loop。外来线程/外来 loop 直接调进来时先派回 owner loop 再执行。
        """

        if getattr(self, "_owner_loop", None) is not None and not self._on_owner_loop():
            # 兜底守卫（正常路径由 dispatch_run_fatal 派回；这里挡住直接调进来的外来线程）。
            if not self._post_to_owner_loop(self._on_run_fatal, exc):
                print(f"[rh2-bringup] run-fatal 无法派回 owner loop（已关闭/未运行），未调度关停链：{exc!r}")
            return
        if self._close_task is not None:
            # codex W5a 复核 #3b：关停进行中的 fatal 不能丢——排队，落盘前吸收进报告
            # （首因为空则成为首因，否则记次生；ok 必为 False）。报告已定稿则只留 fatal_seen。
            if self._closing_report is not None:
                self._fatals_during_close.append(exc)
            return
        loop = getattr(self, "_owner_loop", None)
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return
        code = getattr(exc, "reason_code", None) or type(exc).__name__
        self._close_task = loop.create_task(
            self._run_close(f"run_fatal:{code}", "run_fatal", exc), name="rh2-bringup-shutdown"
        )

    def install_sigterm_shutdown(self) -> None:
        """把 SIGTERM 接到关停链（幂等；需在主线程、有运行中 loop）。opt-in，见 SHUTDOWN_ON_SIGTERM。"""

        if self._uninstall_signal_shutdown is not None:
            return

        async def _on_signal(name: str) -> ShutdownReport:
            return await self.close(reason=f"signal:{name}", trigger="signal")

        try:
            self._uninstall_signal_shutdown = install_signal_shutdown(asyncio.get_running_loop(), _on_signal)
        except (ValueError, RuntimeError, NotImplementedError) as exc:
            # miles 生产拓扑：bringup 在共享后台 AsyncLoopThread（非主线程）上启动，
            # loop.add_signal_handler 在此不可用——如实记录、不让 opt-in 旋钮炸掉 rollout。
            self.signal_shutdown_install_error = f"{type(exc).__name__}: {exc}"
            print(f"[rh2-bringup] SIGTERM 关停未安装（非主线程 loop）：{self.signal_shutdown_install_error}")

    # -- 单例接口 --------------------------------------------------------------

    _startup_state: str = "NEW"  # NEW -> STARTING -> RUNNING | FAILED（sticky）| CLOSED（sticky，W5a）
    _startup_error: BaseException | None = None

    @classmethod
    async def get(cls, args: Any) -> "BringupService":
        async with _SERVICE_LOCK:
            if cls._startup_state == "CLOSED":
                # W5a：关停后 sticky——同进程不再有第二代服务，也不再接任何 rollout
                raise ServiceClosedError(
                    "bringup_get", "BringupService 已关停（同进程单代语义，不重建第二代）"
                )
            if cls._startup_state == "FAILED":
                # 勘误 4：FAILED sticky——同进程绝不创建第二代（首因重抛）
                raise cls._startup_error  # type: ignore[misc]
            if cls._instance is None:
                cls._startup_state = "STARTING"
                try:
                    service = BringupService(args)
                    await service.async_start(args)
                except asyncio.CancelledError:
                    # 终核条件项 2：启动被取消——当前调用原样传播取消，
                    # 但后续调用拿到 typed fatal（不残留 STARTING、不建二代）
                    cls._startup_state = "FAILED"
                    cls._startup_error = StartupCheckError(
                        "bringup_startup_cancelled",
                        "BringupService 启动被取消——单代语义下同进程不再重试。",
                    )
                    raise
                except Exception as exc:
                    # 只 latch Exception；KeyboardInterrupt 等原样传播不 latch
                    cls._startup_state = "FAILED"
                    cls._startup_error = exc
                    raise
                cls._instance = service
                cls._startup_state = "RUNNING"
            return cls._instance


def _sglang_version() -> str:
    try:
        import sglang

        return str(sglang.__version__)
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# slime custom_generate 入口
# ---------------------------------------------------------------------------


def build_fa_sampling_params(args: Any) -> dict[str, Any]:
    """FA rollout 入口的采样配方（codex 轮次 7 P0-2：仓库里此前没有任何
    代码写 rh2_sampling_params）。

    custom_generate 路径的采样参数由 slime 训练循环逐调用传入；FA
    rollout-fn 路径 slime 不传参——从 args 按 slime 自身的字段名构造，
    **缺字段 fail-closed**（采样配方决定 top-p tape 语义，不许猜默认值）。
    """

    required = {
        "rollout_temperature": "temperature",
        "rollout_top_p": "top_p",
        "rollout_max_response_len": "max_new_tokens",
    }
    params: dict[str, Any] = {}
    missing: list[str] = []
    for attr, key in required.items():
        value = getattr(args, attr, None)
        if value is None:
            missing.append(attr)
        else:
            params[key] = value
    if missing:
        raise RuntimeError(
            f"build_fa_sampling_params: args 缺采样字段 {missing}——"
            "FA 入口不猜测采样配方（top-p tape 语义依赖显式值）。"
        )
    params["temperature"] = float(params["temperature"])
    params["top_p"] = float(params["top_p"])
    params["max_new_tokens"] = int(params["max_new_tokens"])
    return params


async def close_bringup_service(
    *,
    reason: str = "external_close",
    trigger: str = "owner_close",
    first_cause: BaseException | str | None = None,
    secondary_causes: tuple[str, ...] | list[str] = (),
    external_residue: dict[str, Any] | None = None,
) -> ShutdownReport | None:
    """W5a 关停入口（进程级）：关掉本进程的 BringupService 单例；从未启动则返回 None。

    生产接线（miles integration 分支 `RolloutManager.dispose()`，W5a 复核 #1）：
    `await rollout_fn.aclose()`（停新提交→取消 worker/active group→唤醒 buffer waiter）
    之后调本函数，并把 aclose 报告里的 `worker_exception`（例如在 buffer.put() 内抛出的
    GroupAdmissionFatal）作为 `first_cause` 传入——它就成为关停报告的首因（trigger 记
    `run_fatal`）。不需要 service 对象、不需要 args。幂等（重复调用拿同一份报告）。
    """

    service = BringupService._instance
    if service is None:
        return None
    if first_cause is not None and trigger == "owner_close":
        trigger = "run_fatal"
    return await service.close(
        reason=reason,
        trigger=trigger,
        first_cause=first_cause,
        secondary_causes=secondary_causes,
        external_residue=external_residue,
    )


def notify_run_fatal(exc: BaseException) -> bool:
    """进程级 run-fatal 通知入口（W5a 复核 #3：不经过 generate.py `_notify_fatal_halt` 的
    fatal 也要触发同一条关停链）。

    两类典型调用者，都不在 owner loop 的执行 context 里：

    - 复合 group filter（`adapters/miles/group_admission.py`，在 miles `DefaultDataBuffer.put()`
      内运行，与执行 task 不在同一 context，contextvar 通知器够不到）：
      `except GroupAdmissionFatal as exc: notify_run_fatal(exc); raise`；
    - capture wire 的 abort 升级（`capture_wire.escalate_abort_unproven`），它跑在 adapter 的
      aiohttp 线程 / 独立 loop 上（`run_app_in_thread`）。

    语义与执行内 fatal 一致：未在关停 → 调度关停链（首因 = exc）；关停进行中 → 吸收进报告；
    已定稿 → 只留 fatal_seen。**记账与调度整体在 owner loop 上完成**（codex Wave3 §9.4，
    见 `BringupService.dispatch_run_fatal`）。

    返回 False = **没通知到**：本进程没有 BringupService，或 owner loop 已关闭/不再接受回调。
    调用方不得据此声称"已通知"（capture_wire 会记 `abort_unproven_unnotified`）。
    """

    service = BringupService._instance
    if service is None:
        return False
    return service.dispatch_run_fatal(exc)


async def ensure_fa_started(args: Any) -> None:
    """FA rollout 入口的启动引导（codex 轮次 7 P0-2）。

    与 custom_generate 首调用共用同一 BringupService 单例：挂
    `args.rh2_orchestrator` 与 `args.rh2_sampling_params`。幂等。
    """

    service = await BringupService.get(args)
    if SHUTDOWN_ON_SIGTERM:
        service.install_sigterm_shutdown()  # 幂等；RH2_SHUTDOWN_ON_SIGTERM=1 才装
    if getattr(args, "rh2_orchestrator", None) is None:
        args.rh2_orchestrator = service.orchestrator
    if getattr(args, "rh2_sampling_params", None) is None:
        args.rh2_sampling_params = build_fa_sampling_params(args)
    # 批 D（I04）：已批处置在启动时注入（turn 截断 KEEP_FULL / hard wall DROP_GROUP），
    # 冲突覆盖 → StartupCheckError。必须先于批 C 的 cap 启用。
    inject_disposition_policy(args)
    # W1b 第一集成切片（F4）：prepared 链把有界 attempt 绑定表挂到 args，
    # Rh2MilesGenerateFn 在铸造身份后 bind、结束后 release。legacy 链为 None。
    if getattr(args, "rh2_attempt_assignments", None) is None and service.attempt_assignments is not None:
        args.rh2_attempt_assignments = service.attempt_assignments


async def generate(args: Any, sample: Any, sampling_params: dict, evaluation: bool = False):
    service = await BringupService.get(args)
    if getattr(args, "rh2_orchestrator", None) is None:
        args.rh2_orchestrator = service.orchestrator
    started = time.monotonic()
    result = await rh2_custom_generate(args, sample, dict(sampling_params), evaluation=evaluation)
    try:
        service.record_event(
            args=args, sample=sample, result=result, wall_seconds=time.monotonic() - started
        )
    except Exception as exc:  # noqa: BLE001 - 证据记录不许伤主链路
        print(f"[rh2-bringup] record_event failed: {type(exc).__name__}: {exc}")
    return result
