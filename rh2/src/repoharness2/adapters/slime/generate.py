"""S1-6 slime 绑定编排胶水：形态 B 训练主链路的 custom_generate 实现。

本模块把 02 文档 §8 的 9 步生命周期编排成一次 `rh2_custom_generate` 调用
（签名对齐 slime 的 custom_generate 约定：`await fn(args, sample, sampling_params,
evaluation=...)`，返回 `list[Sample]`，见 reference/slime/slime/rollout/
sglang_rollout.py 的 load_function 分派与 examples/coding_agent_rl/generate.py）：

    步骤 1  slime 触发 custom_generate                    -> rh2_custom_generate
    步骤 2  [RepoHarness 库] 环境包物化：起 rollout 沙箱，
            envpack.materialize 血缘判据校验 /testbed      -> _materialize_rollout_sandbox
    步骤 3  [slime 现成组件] Claude Code harness 在沙箱内跑 -> HarnessDriver.run（接口
            形状 = slime BaseHarness.run 的关键字签名）
    步骤 4  [slime 现成组件] Anthropic adapter -> SGLang /generate；
            **capture 钩子按轮**从原始响应构造
            GenerationCaptureRecord（A4 sidecar）           -> GenerationCaptureHook
    步骤 5  [slime 现成组件] TrajectoryManager 产叶链 Sample -> SessionAdapter.finish_session
            （S1-3 关键发现：叶链 Sample 不带 tape/weight_versions，
            本模块用钩子攒下的按轮 tape **回填**后才可投影）  -> backfill_leaf_sample
    步骤 6  [RepoHarness 库] GradingManager fresh 评分       \
    步骤 7  [RepoHarness]    project_from_slime 投影          > finalize_rollout
    步骤 8  [RepoHarness]    EligibilityGate 三档资格         /（治理层唯一关口，S1-5；
            顺序 grade -> project -> scan -> gate 已被 wrapper 固化，本模块只准调它）
    步骤 9  合格 -> Sample 返回 slime 训练 batch；降级 -> GroupRepairSignal 在组装配前
            透传训练后端（P4）+ artifact 旁路落盘，样本以 slime abort 形状剔除

A5 sandbox 所有权握手八问的落位（验收级，逐项 schema 实例）：

    Q1 谁建容器            -> SandboxLease.created_by = "slime_adapter"
       （envpack 库层刻意不接触容器 API——materialize.py 只出探针脚本与判据；
       slime 参考实现里也是 custom_generate 层起沙箱，harness 从不建容器）
    Q2 谁物化 /testbed      -> WorkspaceHandle.materialized_by = "repoharness_envpack"
       （血缘判据、探针脚本、BASH_ENV 注入内容全部来自 envpack；编排只是执行通道）
    Q3 harness workdir 如何传入 -> HarnessLaunchSpec.workdir（=public bundle 的
       workdir，SWE 任务 /testbed），经 HarnessDriver.run(workdir=...) 关键字传给
       harness（slime BaseHarness.run 同名参数）
    Q4 模型代理地址如何注入  -> ModelProxyEndpoint(base_url, wire_protocol=
       "anthropic_messages", session_id, inject_env_var="ANTHROPIC_BASE_URL")；
       slime ClaudeCodeHarness.launch_and_wait 实际注入 ANTHROPIC_BASE_URL=
       adapter_url、ANTHROPIC_AUTH_TOKEN=session_id，schema 校验协议与变量名配对
    Q5 网络/权限策略归属     -> SandboxLease.network_policy_owner /
       permission_policy_owner = "slime_adapter"；rollout 容器 network_policy=
       "allowlist"（容器内 harness 必须反连宿主侧模型代理端点，deny_all 会断链），
       justification 必填并如实记录 S1 未做包级过滤（S2 安全 Runtime 收紧）
    Q6 两类 bundle 如何挂载  -> WorkspaceHandle.mounted_bundles 只含
       public_task_bundle（内容写入容器 /rh2/public_task_bundle.json）；
       private_grading_bundle 永不进 rollout 容器——schema 校验器直接拒绝，
       评分私有材料只经 GradingEnvSpec 注入评分容器（S1-4 通道）
    Q7 失败后谁负责清理      -> CleanupPolicy.owner = "slime_adapter"，
       steps=[remove_container, release_lease]；编排在 finally 里无条件执行
       （harness 崩溃、gate 拒绝、投影报错都不豁免）
    Q8 清理失败如何记录      -> CleanupPolicy.on_cleanup_failure =
       "record_runtime_finding_and_infra_failure"；实际失败落
       CleanupFailureRecord(failure_category="infra_failure") 进 audit
       （schema 上"清理失败但不留痕"不可表示）

mock 纪律（S1-6 本机验收；真实 GPU 验收 S1-7a）：可注入件的接口形状全部
对照 slime 源码字段名——HarnessDriver = BaseHarness.run 关键字签名；
SessionAdapter = BaseAdapter 的 open_session/finish_session/drop_session；
SGLang 响应 = {"meta_info": {"id", "finish_reason": {"type"},
"output_token_logprobs": [[logprob, token_id, ...], ...], "top_p_token_ids",
"top_p_token_offsets", "routed_experts"}}（后三者 base64 int32 小端，
与 slime `decode_int32_meta_array` / S1-0 探针 wire 形态一致）。
与 slime 真实接口的差异假设清单见 s1/implementation-notes.md（S1-7a 逐条核对）。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import re
import secrets
import struct
import sys
import time
import uuid

from pydantic import ValidationError
from collections.abc import Awaitable, Callable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Protocol

from repoharness2.adapters.slime.async_worker import FatalExecutionInfrastructureError
from repoharness2.adapters.slime.outcome_producer import (
    FAILURE_CODE_TERMINATION_MAP,
    STAGE_FALLBACK_TERMINATION_MAP,
    build_outcome_v2,
)
from repoharness2.adapters.slime.session_capability import mint_session_capability
from repoharness2.contracts.trajectory import derive_weight_version_max_lag
from repoharness2.adapters.slime.projection import (
    ResponseContextRun,
    SlimeBranchAnnotation,
    SlimeRewardInput,
    assert_renderer_class,
    decode_int32_tape,
    project_from_slime,
)
from repoharness2.contracts import (
    ArtifactRef,
    BackendHandshake,
    BundleMount,
    CaptureSamplingParams,
    CleanupPolicy,
    CompactedSubTraceLineage,
    GenerationCaptureRecord,
    ServerTiming,
    GradingFailureCategory,
    GradingReport,
    HarnessLaunchSpec,
    ModelProxyEndpoint,
    SandboxLease,
    WorkspaceHandle,
    canonical_json_digest,
)
from repoharness2.contracts.fa_runtime import RolloutAttemptOutcomeV2
from repoharness2.contracts.finalization import (
    CleanupFailureFact,
    CleanupResultAppendV1,
    FinalizationReceiptV1,
    FinalizationStoreConflict,
    RejectedObjectEvidenceV1,
    SessionDrainReceiptV1,
)
from repoharness2.envpack import bundles, materialize
from repoharness2.envpack.termination_facts import (
    TerminationFactsError,
    stamp_termination_facts,
    termination_facts_payload,
)
from repoharness2.governance import (
    FinalizedRollout,
    GateInputError,
    GroupRepairSignal,
    SandboxCapabilityFacts,
    finalize_rollout,
)
from repoharness2.governance.admission import (
    AdmissionError,
    derive_admission_payload,
    stamp_admission_payload,
)
from repoharness2.grading.manager import (
    BASE_UNTRACKED_MANIFEST,
    BASE_UNTRACKED_SNAPSHOT_SCRIPT,
    DockerRunner,
    ExecResult,
    GradingEnvSpec,
    build_swe_grading_spec,
    run_docker,
)
from repoharness2.grading.queue import BackpressureEvent

__all__ = [
    "LIFECYCLE_STEPS",
    "CleanupFailureRecord",
    "GenerationCaptureHook",
    "HarnessDriver",
    "LeafFacts",
    "RolloutTimelineEntry",
    "RolloutAudit",
    "RolloutFailureRecord",
    "RolloutOrchestrator",
    "RolloutTaskSpec",
    "SessionAdapter",
    "SlimeBindingConfig",
    "SlimeBindingError",
    "StartupCheckError",
    "TurnIdentitySpan",
    "TurnTape",
    "backfill_leaf_sample",
    "assert_adapter_status_not_404",
    "detect_context_shrink",
    "ensure_claude_code_compaction_disabled",
    "ensure_claude_code_training_guards",
    "parse_bool_env_flag",
    "rh2_custom_generate",
    "rollout_task_from_bundle_pair",
    "startup_checks",
]

# 与 slime slime/utils/types.py 的 meta_info 双键完全一致（wire 兼容两个拼法）。
_TOP_P_IDS_META_KEYS = ("top_p_token_ids", "top_p_kept_token_ids")
_TOP_P_OFFSETS_META_KEYS = ("top_p_token_offsets", "top_p_kept_token_offsets")
_ROUTED_EXPERTS_META_KEY = "routed_experts"

# public bundle 在 rollout 容器内的落点（Q6：以内容写入实现"挂载"，BundleMount 记录事实）。
PUBLIC_BUNDLE_CONTAINER_PATH = "/rh2/public_task_bundle.json"

# 9 步生命周期的 audit 步名（测试按此断言顺序；step9 二选一）。
LIFECYCLE_STEPS = (
    "step1_custom_generate_invoked",
    "step2_workspace_materialized",
    "step3_harness_completed",
    "step4_capture_records_ready",
    "step5_leaf_samples_assembled_and_backfilled",
    "step6_grading_completed",
    "step7_projection_completed",
    "step8_gate_finalized",
    "step9_samples_delivered",  # 或 step9_degraded_signal_forwarded
)


class FinalizationStore(Protocol):
    """B5 durable handoff 通道（A-prime 第 7 条）。三个方法三个时刻：

    - put_artifact_bodies：FrozenDeltaSource 组装后立刻（content-addressed，
      幂等；失败 = T0 失败表第 1 行"无法建立可信 artifact"→ missing 收口）；
    - persist_receipt：finally 段 cleanup **之前**（原子；失败 = 第 2 行
      "durable handoff 失败"→ run halt 并保留 workspace/容器）;
    - append_cleanup_result：cleanup 之后（独立追加，永不改写 receipt；
      失败只落账不再抛——追加失败不许反过来掩盖首因）。"""

    def put_artifact_bodies(self, *, frozen_patch: Any, baseline_manifest: Any) -> None: ...

    def persist_receipt(self, receipt: FinalizationReceiptV1) -> None: ...

    def append_cleanup_result(self, result: CleanupResultAppendV1) -> None: ...


def build_finalization_receipt(
    audit: "RolloutAudit",
    *,
    in_flight_exception: BaseException | None,
    artifact_bodies_persisted: bool,
) -> FinalizationReceiptV1:
    """从 audit 事实构造 receipt（纯函数，独立可测）。

    disposition 推导：致命异常在途 → fatal_run_halt；取消在途 → cancelled；
    step9 已标记 → **delivery_prepared**（样本备好交回 slime——不是
    trainer handoff，见 contracts/finalization docstring；B5 复核 P0）；
    其余 = aborted。abort_reason 只是摘要（outcome_v2 才是权威归因）。
    outcome_v2 typed 嵌入会复跑 Outcome v2 全量不变量——构造失败由调用方
    并入 receipt 持久化失败通道（durable handoff 失败），不静默。"""

    from repoharness2.contracts.fa_runtime import RolloutAttemptOutcomeV2

    if isinstance(in_flight_exception, FatalExecutionInfrastructureError):
        disposition = "fatal_run_halt"
    elif isinstance(in_flight_exception, asyncio.CancelledError):
        disposition = "cancelled"
    elif (
        "step9_samples_delivered" in audit.steps
        or "step9_degraded_signal_forwarded" in audit.steps
    ):
        disposition = "delivery_prepared"
    else:
        disposition = "aborted"
    # B5 复核三轮 P1-2：统一终局归因——fatal/cancelled 的 receipt 同样
    # 要有可恢复的 reason（F2-4 只读 receipt 就能裁定，无需翻 audit）。
    terminal_reason_code: str | None = None
    if disposition == "fatal_run_halt":
        terminal_reason_code = (
            getattr(in_flight_exception, "reason_code", None)
            or type(in_flight_exception).__name__
        )
    elif disposition == "cancelled":
        terminal_reason_code = "cancelled"
    elif disposition == "aborted":
        if audit.outcome_v2 is not None:
            terminal_reason_code = audit.outcome_v2.get("reason_code")
        elif audit.failure_records:
            terminal_reason_code = audit.failure_records[-1].error_type
    attempt_key = audit.physical_attempt_id or audit.trajectory_id
    return FinalizationReceiptV1(
        receipt_id=f"rcpt_{re.sub(r'[^A-Za-z0-9._-]', '_', attempt_key)}",
        task_id=audit.task_id,
        trajectory_id=audit.trajectory_id,
        session_id=audit.session_id,
        physical_attempt_id=audit.physical_attempt_id,
        attempt_disposition=disposition,
        terminal_reason_code=terminal_reason_code,
        rejection_evidence=audit.rejection_evidence,
        outcome_v2=(
            RolloutAttemptOutcomeV2.model_validate(audit.outcome_v2)
            if audit.outcome_v2 is not None
            else None
        ),
        frozen_patch_digest=audit.frozen_patch_digest,
        baseline_manifest_digest=audit.baseline_manifest_digest,
        artifact_bodies_persisted=artifact_bodies_persisted,
        grading_report_id=(
            audit.finalized.grading_report.report_id if audit.finalized else None
        ),
        grading_outcome=(
            audit.finalized.grading_report.outcome if audit.finalized else None
        ),
        eligibility_report_id=(
            audit.finalized.eligibility_report.report_id if audit.finalized else None
        ),
        delivered_sample_count=audit.delivered_sample_count,
        runtime_quiescence_confirmed=audit.runtime_quiescence_confirmed,
        drain_receipt_ref=(
            audit.session_drain_receipt.receipt_id
            if audit.session_drain_receipt is not None
            else None
        ),
        drain_receipt=audit.session_drain_receipt,
        started_epoch_seconds=audit.started_epoch_seconds,
        finalized_at_utc=_now_utc(),
    )


class SlimeBindingError(RuntimeError):
    """编排层 fail-closed 错误（reason_code 机器可读，audit 记录后转 slime abort 形状）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


class StartupCheckError(SlimeBindingError):
    """启动期守门失败（U-G renderer / U-H tape 探针）：必须 fail，禁止静默降级。"""


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _meta_get_first(meta: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in meta:
            return meta[key]
    return None


# ---------------------------------------------------------------------------
# 启动期守门：U-G renderer 断言 + U-H tape 探针断言（S1-7a 复用同一函数）
# ---------------------------------------------------------------------------


def startup_checks(
    *,
    renderer: object,
    expected_renderer_cls_name: str,
    probe_sampling_params: Mapping[str, Any],
    probe_response: Mapping[str, Any],
    prompt_token_count: int,
    expect_routing_tape: bool,
    moe_num_layers: int | None = None,
    moe_router_topk: int | None = None,
) -> dict[str, Any]:
    """启动期两道守门，全部通过才返回 evidence dict，任一失败即抛异常。

    - U-G：renderer 类名精确断言（防本地路径加载 tokenizer 静默回落
      DefaultRenderer，s0/v2_renderer_report.md §4），复用 S1-3 的
      `assert_renderer_class`，失败抛 SlimeProjectionError(renderer_class_mismatch)。
    - U-H：tape 探针断言——对一次**请求了 tape** 的 /generate 探针响应逐项核对
      "请求了就必须在响应里"（S0-6 分水岭：stock SGLang 会静默忽略
      custom_params，字段直接缺席）。缺失即抛 StartupCheckError，不打日志了事。

    参数 `probe_response` 是原始 SGLang 响应 JSON（含 meta_info），
    `probe_sampling_params` 是探针请求实际使用的采样参数（含两个 tape flag）。
    具体数值例（uh_probe_result.json）：prompt 15、生成 16、top_p=0.95 时
    offsets 长 17、routed_experts numel = 30*48*8（30 = 15-1+16）。
    """

    renderer_name = assert_renderer_class(renderer, expected_renderer_cls_name)

    meta = probe_response.get("meta_info")
    if not isinstance(meta, Mapping):
        raise StartupCheckError("probe_meta_info_missing", "探针响应没有 meta_info，无法核对 tape。")

    pairs = meta.get("output_token_logprobs") or []
    if not pairs:
        raise StartupCheckError(
            "probe_logprobs_missing",
            "探针响应 meta_info.output_token_logprobs 为空——return_logprob 未生效，"
            "逐 token logprob 是训练硬依赖。",
        )
    generated = len(pairs)
    logprobs = [float(item[0]) for item in pairs]
    if not all(math.isfinite(value) for value in logprobs):
        raise StartupCheckError("probe_logprobs_not_finite", "探针 logprob 含非有限值。")

    evidence: dict[str, Any] = {
        "renderer_cls_name": renderer_name,
        "prompt_token_count": prompt_token_count,
        "generated_token_count": generated,
        "logprobs_entries": generated,
    }

    top_p = float(probe_sampling_params["top_p"])
    want_top_p_tape = bool(probe_sampling_params.get("return_top_p_token_ids")) and top_p < 1.0
    if want_top_p_tape:
        ids_raw = _meta_get_first(meta, _TOP_P_IDS_META_KEYS)
        offsets_raw = _meta_get_first(meta, _TOP_P_OFFSETS_META_KEYS)
        if ids_raw is None or offsets_raw is None:
            raise StartupCheckError(
                "top_p_tape_missing_in_probe",
                "请求了 top-p tape（return_top_p_token_ids=True 且 top_p="
                f"{top_p} < 1.0）但探针响应缺 top_p_token_ids/offsets——这是"
                " stock SGLang（非 slime patch 镜像）静默忽略 custom_params 的典型"
                "形态，必须在启动期 fail（U-H），不得进入训练循环。",
            )
        ids = decode_int32_tape(ids_raw, field_name="probe.top_p_token_ids")
        offsets = decode_int32_tape(offsets_raw, field_name="probe.top_p_token_offsets")
        if len(offsets) != generated + 1:
            raise StartupCheckError(
                "top_p_offsets_len_mismatch",
                f"探针 top-p offsets 长度 {len(offsets)} != 生成 token 数 + 1 = {generated + 1}。",
            )
        if offsets[0] != 0 or offsets[-1] != len(ids):
            raise StartupCheckError(
                "top_p_offsets_inconsistent",
                f"探针 top-p offsets 首尾不合法：offsets[0]={offsets[0]}（应为 0），"
                f"offsets[-1]={offsets[-1]}（应为 ids 总数 {len(ids)}）。",
            )
        evidence["top_p_token_offsets_len"] = len(offsets)
        evidence["top_p_kept_token_count"] = len(ids)

    # B2（R6-ext）：sampling-mask 探针断言（sglang-miles 引擎路径）。请求了
    # return_sampling_mask 的探针必须收到 output_token_sampling_mask/
    # _logprobs——stock/slime-patch 引擎会静默缺席，与 U-H top-p 探针同一
    # "请求了就必须在响应里"的启动期守门。解析/校验复用装配层同一实现
    # （lazy import：旧链不加载 adapters.miles）。
    if bool(probe_sampling_params.get("return_sampling_mask")):
        from repoharness2.adapters.miles.sampling_mask_assembly import (
            SamplingMaskAssemblyError,
            parse_turn_sampling_support,
        )

        probe_output_ids = [item[1] for item in pairs]
        try:
            probe_support, _probe_support_logprobs = parse_turn_sampling_support(
                probe_output_ids, meta
            )
        except SamplingMaskAssemblyError as exc:
            raise StartupCheckError(
                "sampling_mask_missing_in_probe",
                "请求了 return_sampling_mask 但探针响应不含合法 sampling-support "
                f"tape（{exc.reason_code}）——目标引擎不是带原生 sampling-mask "
                "primitive 的 sglang-miles 构建，或配置错配。必须在启动期 fail"
                "（U-H 同款），不得进入训练循环。",
            ) from exc
        evidence["sampling_mask_supports"] = len(probe_support.supports)
        evidence["sampling_mask_top_k"] = probe_sampling_params.get("top_k")

    routing_raw = meta.get(_ROUTED_EXPERTS_META_KEY)
    if expect_routing_tape:
        if not probe_sampling_params.get("return_routed_experts"):
            raise StartupCheckError(
                "routing_probe_not_requested",
                "expect_routing_tape=True（MoE 模型）但探针请求没开 return_routed_experts，"
                "该探针无法证明 routing tape 能力。",
            )
        if routing_raw is None:
            raise StartupCheckError(
                "routing_tape_missing_in_probe",
                "请求了 routing tape（return_routed_experts=True）但探针响应缺 "
                "routed_experts——镜像静默降级形态（U-H），启动期必须 fail。",
            )
        flat = decode_int32_tape(routing_raw, field_name="probe.routed_experts")
        expected_rows = prompt_token_count - 1 + generated  # SGLang 对齐律（S1-0 实测）
        evidence["routing_rows_expected"] = expected_rows
        if moe_num_layers is not None and moe_router_topk is not None:
            expected_numel = expected_rows * moe_num_layers * moe_router_topk
            if len(flat) != expected_numel:
                raise StartupCheckError(
                    "routing_numel_mismatch",
                    f"探针 routing 元素数 {len(flat)} != 期望 {expected_numel}"
                    f"（rows={expected_rows} x layers={moe_num_layers} x topk={moe_router_topk}）。",
                )
            evidence["routed_experts_shape"] = [expected_rows, moe_num_layers, moe_router_topk]
        elif expected_rows > 0 and len(flat) % expected_rows != 0:
            raise StartupCheckError(
                "routing_numel_mismatch",
                f"探针 routing 元素数 {len(flat)} 不能被期望行数 {expected_rows} 整除。",
            )
    elif routing_raw is not None:
        raise StartupCheckError(
            "unexpected_routing_tape_in_probe",
            "expect_routing_tape=False（dense 声明）但探针响应带了 routed_experts——"
            "模型/配置错配，禁止静默取舍（U-J：renderer/模型必须按模型分别配置）。",
        )

    return evidence


# ---------------------------------------------------------------------------
# 步骤 4：capture 钩子（SGLang 客户端响应层，按轮构造 A4 sidecar + 攒回填 tape）
# ---------------------------------------------------------------------------


def hook_turn_weight_versions(hook: "GenerationCaptureHook") -> list[str] | None:
    """从 capture 钩子取逐轮版本序列（Outcome 记账用，FA-0 第 2 条）。

    V2：spans 轮按区间序展开全部版本（一轮可贡献多个）——否则
    `intra_execution_version_span`（max-min 派生互检）会与 Sample 侧同款
    低报 turn 内跨更新。非 spans 轮取单数（failed 轮两者皆 None，自然
    跳过——与旧 `[r.weight_version for r in hook.records if r.weight_version]`
    的过滤语义逐轮等价，因为 record 与 tape 的 weight_version 同源同值）。
    空序列返回 None（无版本事实，Outcome 校验器按 completion class 处置）。
    """

    versions: list[str] = []
    for tape in hook.tapes:
        if tape.weight_version_spans:
            versions.extend(span.version for span in tape.weight_version_spans)
        elif tape.weight_version:
            versions.append(tape.weight_version)
    return versions or None


@dataclass(frozen=True)
class WeightVersionSpan:
    """一个 per-token 权重版本区间（sglang weight_versions.py wire 形态）。

    wire 事实源 = sglang-miles 4e230c3d 的 `python/sglang/srt/utils/
    weight_versions.py::add_weight_versions_to_meta_info`：
    `meta_info["weight_versions"] = [{"version": str, "start": int,
    "end": int}, ...]`——半开区间 [start, end) 按生成 token 位置计数，
    version 是引擎权重版本字符串（miles 场景为十进制计数器）。
    """

    version: str
    start: int
    end: int


# capture 逐轮版本 provenance 取值（TurnTape.weight_version_provenance）：
# - engine_spans：引擎报了 meta_info.weight_versions（一手 per-token 证据）；
# - single_version_only：引擎只报单数 meta_info.weight_version（旧引擎回退，
#   turn 内跨权重更新时单数只等于最后区间版本——低报 staleness 的形态，
#   消费方必须知道这份记账没有 turn 内多版本分辨力）。
WEIGHT_VERSION_PROVENANCE_SPANS = "engine_spans"
WEIGHT_VERSION_PROVENANCE_SINGLE = "single_version_only"


def parse_weight_version_spans(
    meta: Mapping[str, Any], *, generated: int
) -> tuple[WeightVersionSpan, ...] | None:
    """从 /generate 响应 meta_info 解析 per-token 权重版本区间（fail-closed）。

    返回值：
    - `None`：meta_info **没有 `weight_versions` 键**——旧引擎/未启用版本跟踪，
      调用方回退单数 `weight_version` 并记 provenance=single_version_only。
      注意"键缺失"与"键在场值为 null"是两回事（vendor refresh 复核 P2 #1）：
      pinned writer 只会**不写键**或**写非空 list**，`weight_versions: null`
      不是旧引擎形态而是账目损坏，走 fail-closed（下方不变式 0）；
    - 非空 tuple：解析并校验通过的区间序列。

    引擎**报了就必须合法**（vendor refresh V2 拍板）：任何违反下列合同不变式
    的形态都抛 `SlimeBindingError`（不猜测、不修正、不静默回退单数——坏 spans
    回退单数会把"账目损坏"洗成"旧引擎"）。不变式逐条对照 sglang 单测
    `test/registered/unit/utils/test_weight_versions.py::
    test_spans_satisfy_the_contract_for_random_event_sequences` 与
    `add_weight_versions_to_meta_info` 实现（同 commit 4e230c3d）：

    0. 键在场则值不得为 `null`（None）；
    1. 非空 list，每项含 version/start/end；version 为非空**字符串**（writer
       写入前显式 str 化，wire 上不存在数值版本——int/float 一律拒绝，不做
       宽容转换；宽容会把"上游换了 writer/序列化被改"洗成正常），start/end
       为非负 int（bool 拒绝）；
    2. spans[0].start == 0；相邻区间 prev.end == cur.start（连续无缝隙无重叠）；
    3. 相邻区间版本不同（引擎侧同版本必合并，重复出现 = 上游合同破坏）；
    4. `generated == 0` 时恰好一个空区间 {v, 0, 0}；`generated > 0` 时每个
       区间 start < end 且最后区间 end == generated（覆盖全部生成 token）；
    5. 单数 `weight_version` 必须在场且 == spans[-1].version（sglang 在同一
       函数里一起写两个键，单数 = finalize 时刻值——FA-0 收窄语义的 wire 面）。
    """

    if "weight_versions" not in meta:
        return None
    raw = meta["weight_versions"]

    def _bad(reason: str, detail: str) -> SlimeBindingError:
        return SlimeBindingError(
            f"weight_version_spans_{reason}",
            f"meta_info.weight_versions 非法（{detail}）——引擎报了 spans 就必须"
            "满足 sglang weight_versions.py 合同，fail-closed 拒绝本轮。",
        )

    if raw is None:
        raise _bad(
            "null",
            "键在场但值为 null——writer 只会不写键或写非空 list，"
            "null 不是'旧引擎缺键'，不得回退单数",
        )
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise _bad("not_a_list", f"类型 {type(raw).__name__} 不是 list")
    if not raw:
        raise _bad("empty", "空 list（sglang 合同保证至少一个区间）")

    spans: list[WeightVersionSpan] = []
    for i, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise _bad("item_not_mapping", f"第 {i} 项类型 {type(item).__name__}")
        missing_keys = {"version", "start", "end"} - set(item)
        if missing_keys:
            raise _bad("item_missing_keys", f"第 {i} 项缺键 {sorted(missing_keys)}")
        version = item["version"]
        if not isinstance(version, str):
            raise _bad(
                "version_not_string",
                f"第 {i} 项 version={version!r}（类型 {type(version).__name__}；"
                "writer 合同 version 恒为字符串，数值不做宽容转换）",
            )
        if not version:
            raise _bad("version_empty", f"第 {i} 项 version 为空字符串")
        bounds: list[int] = []
        for key in ("start", "end"):
            value = item[key]
            if not isinstance(value, int) or isinstance(value, bool):
                raise _bad("bound_not_int", f"第 {i} 项 {key}={value!r}")
            if value < 0:
                raise _bad("bound_negative", f"第 {i} 项 {key}={value}")
            bounds.append(value)
        spans.append(WeightVersionSpan(version=version, start=bounds[0], end=bounds[1]))

    if spans[0].start != 0:
        raise _bad("first_start_nonzero", f"首区间 start={spans[0].start} != 0")
    for prev, cur in zip(spans, spans[1:]):
        if cur.start != prev.end:
            kind = "gap" if cur.start > prev.end else "overlap"
            raise _bad(
                kind,
                f"相邻区间 [{prev.start},{prev.end}) 与 [{cur.start},{cur.end}) "
                f"{'有缝隙' if kind == 'gap' else '重叠'}",
            )
        if cur.version == prev.version:
            raise _bad(
                "adjacent_same_version",
                f"相邻区间版本相同 {cur.version!r}（引擎侧必合并）",
            )
    if generated == 0:
        if len(spans) != 1 or spans[0].end != 0:
            raise _bad(
                "zero_output_shape",
                f"零输出轮应恰好一个空区间，got {[(s.version, s.start, s.end) for s in spans]}",
            )
    else:
        for span in spans:
            if span.start >= span.end:
                raise _bad(
                    "empty_span",
                    f"区间 [{span.start},{span.end}) 非零输出轮不得为空/倒置",
                )
        if spans[-1].end != generated:
            raise _bad(
                "end_mismatch",
                f"末区间 end={spans[-1].end} != 生成 token 数 {generated}（越界/欠覆盖）",
            )
    single_raw = meta.get("weight_version")
    if single_raw is None:
        raise _bad(
            "single_version_missing",
            "weight_versions 在场但单数 weight_version 缺失（sglang 同函数一起写两键）",
        )
    if str(single_raw) != spans[-1].version:
        raise _bad(
            "single_version_mismatch",
            f"单数 weight_version={single_raw!r} != 末区间版本 {spans[-1].version!r}"
            "（单数 = finalize 时刻值的合同被破坏）",
        )
    return tuple(spans)


@dataclass(frozen=True)
class TurnTape:
    """一轮 /generate 的解码后事实（capture 记录的回填伴生物，不进契约）。"""

    record_id: str
    turn_index: int
    prompt_token_count: int
    response_token_count: int
    output_ids: tuple[int, ...]
    output_log_probs: tuple[float, ...]
    top_p_token_ids: tuple[int, ...] | None
    top_p_token_offsets: tuple[int, ...] | None
    routed_experts_flat: tuple[int, ...] | None
    # FA-0：本轮引擎真实 weight_version（meta_info.weight_version 原文透传；
    # 权重更新可发生在轮与轮之间，逐轮记录是 faithful DIS 的前置事实）。
    weight_version: str | None = None
    # B2（R6-ext，miles sampling-support 链）：本轮每个生成 token 的引擎支持
    # 集（return_sampling_mask 会话才非 None；旧 top-p 链恒 None）。commit
    # 后由叶链装配层（sampling_mask_assembly.assemble_leaf_sampling_mask）
    # 消费——TurnTape 不进契约，支持集只在进程内走到装配。注意本 tape 的
    # output_log_probs 仍是全词表诊断列（mask 会话的 support-normalized 列
    # 走 TurnRecord -> Sample.rollout_log_probs，capture_wire 已切换）。
    sampling_supports: tuple[tuple[int, ...], ...] | None = None
    # V2（vendor refresh 第二批）：本轮 per-token 权重版本区间（引擎
    # meta_info.weight_versions，parse_weight_version_spans 校验后透传）。
    # None = 引擎未报（旧引擎，provenance=single_version_only）；非 None 时
    # 必然非空且 spans[-1].version == weight_version（parse 已校验）。backfill
    # 把区间的**全部**版本并入 Sample.weight_versions（修 adv_miles 反例：
    # 单数记账把 v10+v11 turn 记成全 v11，DefaultDataBuffer 的 oldest
    # staleness 低报，可能放过期样本入训）。
    weight_version_spans: tuple[WeightVersionSpan, ...] | None = None

    @property
    def weight_version_provenance(self) -> str:
        """本轮版本记账 provenance（engine_spans / single_version_only）。"""

        return (
            WEIGHT_VERSION_PROVENANCE_SPANS
            if self.weight_version_spans is not None
            else WEIGHT_VERSION_PROVENANCE_SINGLE
        )


class GenerationCaptureHook:
    """按轮捕获 SGLang /generate 原始响应 -> GenerationCaptureRecord（A4）。

    真实接线位置（S1-7a）：替换/包装 slime `slime.agent.adapters.common.
    call_sglang_generate`（该函数刻意做成模块级可 monkeypatch），在响应
    成功 flush 后调用本钩子。S1-6 mock 里由 SessionAdapter 替身在每轮调用。

    fail-closed 记账（与 capture schema 的 complete 禁令首尾相接）：
    - 请求了 tape 而响应缺失 -> capture_status="partial"、alignment="not_checked"
      （U-H 静默降级形态的如实记法；投影层随后拒收，样本进不了训练）；
    - tape 在场但对不上（offsets 长度/首尾断裂）-> "partial" + "mismatch"；
    - meta_info 整个缺失 -> "failed" + capture_failure_reason。
    钩子只记录事实、绝不修正数据。
    """

    def __init__(
        self,
        *,
        trajectory_id: str,
        model_name: str,
        backend_name: Literal["sglang", "vllm"],
        backend_version: str,
        renderer_cls_name: str,
        tokenizer_name: str,
        template_hash: str,
        artifact_store: MutableMapping[str, bytes] | None = None,
    ) -> None:
        self.trajectory_id = trajectory_id
        self.model_name = model_name
        self.backend_name = backend_name
        self.backend_version = backend_version
        self.renderer_cls_name = renderer_cls_name
        self.tokenizer_name = tokenizer_name
        self.template_hash = template_hash
        self.artifact_store: MutableMapping[str, bytes] = (
            artifact_store if artifact_store is not None else {}
        )
        self.records: list[GenerationCaptureRecord] = []
        self.tapes: list[TurnTape] = []

    # -- artifact 存储小件 --------------------------------------------------

    def _store(self, ref_id: str, payload: bytes) -> ArtifactRef:
        digest = "sha256:" + hashlib.sha256(payload).hexdigest()
        self.artifact_store[ref_id] = payload
        return ArtifactRef(ref_id=ref_id, sha256=digest, byte_size=len(payload))

    def _store_int32(self, ref_id: str, values: Sequence[int]) -> ArtifactRef:
        return self._store(ref_id, struct.pack(f"<{len(values)}i", *values))

    def _store_f64(self, ref_id: str, values: Sequence[float]) -> ArtifactRef:
        return self._store(ref_id, struct.pack(f"<{len(values)}d", *values))

    # -- 主入口 ---------------------------------------------------------------

    def on_generate_response(
        self,
        *,
        prompt_token_ids: Sequence[int],
        sampling_params: Mapping[str, Any],
        response: Mapping[str, Any],
        turn_support: Any | None = None,  # B2：wire 已解析的 miles TurnSupport
        # V2：wire 已解析校验的 per-token 权重版本区间（capture_wire 在 stage
        # 前解析，commit 时仅在场才传——与 turn_support 同一双路径模式；直调
        # 路径（探针/测试替身）不传，本方法自行用同一 parse 函数从响应重建）。
        weight_version_spans: tuple[WeightVersionSpan, ...] | None = None,
    ) -> GenerationCaptureRecord:
        """处理一轮 /generate 响应。响应字段名与 SGLang wire 形态逐一对应。"""

        turn_index = len(self.records)
        record_id = f"cap_{self.trajectory_id}_t{turn_index}"
        prompt_ids = [int(t) for t in prompt_token_ids]
        if not prompt_ids:
            raise SlimeBindingError("empty_prompt_ids", f"第 {turn_index} 轮 prompt_token_ids 为空。")

        params = CaptureSamplingParams(
            temperature=float(sampling_params["temperature"]),
            top_p=float(sampling_params["top_p"]),
            max_new_tokens=int(sampling_params["max_new_tokens"]),
            return_top_p_token_ids=bool(sampling_params["return_top_p_token_ids"]),
            return_routed_experts=bool(sampling_params["return_routed_experts"]),
        )
        prompt_ref = self._store_int32(f"{record_id}_prompt_ids", prompt_ids)

        meta = response.get("meta_info")
        if not isinstance(meta, Mapping) or not meta.get("id"):
            record = GenerationCaptureRecord(
                record_id=record_id,
                request_id=f"missing_rid_t{turn_index}",
                turn_id=f"turn_{turn_index}",
                trajectory_id=self.trajectory_id,
                model_name=self.model_name,
                backend_name=self.backend_name,
                backend_version=self.backend_version,
                sampling_params=params,
                renderer_cls_name=self.renderer_cls_name,
                tokenizer_name=self.tokenizer_name,
                template_hash=self.template_hash,
                prompt_token_count=len(prompt_ids),
                response_token_count=0,
                prompt_token_ids_ref=prompt_ref,
                capture_status="failed",
                capture_failure_reason="response_meta_info_missing",
                alignment_status="not_checked",
                captured_at_utc=_now_utc(),
            )
            self.records.append(record)
            return record

        # FA-0：逐轮真实引擎版本（slime _apply_meta_info 同源字段；缺失记 None，
        # 是否容忍缺失由正式链 require_real_weight_versions 断言决定，这里只记录事实）。
        raw_weight_version = meta.get("weight_version")
        turn_weight_version = str(raw_weight_version) if raw_weight_version is not None else None

        # 与 slime call_sglang_generate 完全一致的取数方式：
        #   output_ids = [x[1] for x in meta["output_token_logprobs"]]
        #   output_log_probs = [float(x[0]) for x in ...]
        pairs = meta.get("output_token_logprobs") or []
        output_ids = [int(item[1]) for item in pairs]
        output_log_probs = [float(item[0]) for item in pairs]
        generated = len(output_ids)

        mismatches: list[str] = []
        missing: list[str] = []

        want_top_p_tape = params.return_top_p_token_ids and params.top_p < 1.0
        top_p_ids: list[int] | None = None
        top_p_offsets: list[int] | None = None
        ids_raw = _meta_get_first(meta, _TOP_P_IDS_META_KEYS)
        offsets_raw = _meta_get_first(meta, _TOP_P_OFFSETS_META_KEYS)
        if (ids_raw is None) != (offsets_raw is None):
            mismatches.append("top_p_pair_incomplete")
        elif ids_raw is not None:
            top_p_ids = decode_int32_tape(ids_raw, field_name=f"{record_id}.top_p_token_ids")
            top_p_offsets = decode_int32_tape(
                offsets_raw, field_name=f"{record_id}.top_p_token_offsets"
            )
            if (
                len(top_p_offsets) != generated + 1
                or (top_p_offsets and top_p_offsets[0] != 0)
                or (top_p_offsets and top_p_offsets[-1] != len(top_p_ids))
            ):
                mismatches.append("top_p_offsets_inconsistent")
        elif want_top_p_tape:
            missing.append("top_p_tape")  # U-H 静默降级形态：请求了但响应没带

        routing_flat: list[int] | None = None
        routing_raw = meta.get(_ROUTED_EXPERTS_META_KEY)
        if routing_raw is not None:
            routing_flat = decode_int32_tape(routing_raw, field_name=f"{record_id}.routed_experts")
        elif params.return_routed_experts:
            missing.append("routing_tape")

        # B2（R6-ext）：sampling-support tape（miles sglang-miles 引擎会话）。
        # 会话默认键 return_sampling_mask 随 capture_params 到达（capture
        # schema 冻结，flag 不进 CaptureSamplingParams——tape 只落 TurnTape，
        # raw meta_info digest 已覆盖原始事实）。wire 路径在 stage 前解析过
        # 一次并经 PendingTurn.turn_support 传入；直调路径（探针/测试替身）
        # 用**同一个** parse_turn_sampling_support 从响应重建，不存在第二套
        # 解析实现。缺失/对不上按既有 tape 记账口径落 missing/mismatch
        # （partial 记录随后被装配层与投影层双重拒绝，不静默降级）。
        want_sampling_mask = bool(sampling_params.get("return_sampling_mask", False))
        sampling_supports: tuple[tuple[int, ...], ...] | None = None
        if want_sampling_mask:
            parsed_support = turn_support
            if parsed_support is None:
                # lazy import：不带 miles 环境的既有 321 测试面不因本文件被
                # 迫加载 adapters.miles 包（与 capture_wire 同一口径）。
                from repoharness2.adapters.miles.sampling_mask_assembly import (
                    SamplingMaskAssemblyError,
                    parse_turn_sampling_support,
                )

                try:
                    parsed_support, _support_logprobs = parse_turn_sampling_support(
                        output_ids, meta
                    )
                except SamplingMaskAssemblyError as exc:
                    parsed_support = None
                    if exc.reason_code == "sampling_mask_missing_in_response":
                        missing.append("sampling_mask_tape")
                    else:
                        mismatches.append(f"sampling_mask:{exc.reason_code}")
            if parsed_support is not None:
                sampling_supports = tuple(
                    tuple(int(t) for t in support) for support in parsed_support.supports
                )

        # V2：per-token 权重版本区间。wire 路径已在 stage 前解析校验（非法
        # 直接抛、poison+abandon，本方法收到的必是合法产物）；直调路径
        # （探针/测试替身）用**同一个** parse_weight_version_spans 从响应
        # 重建。直调解析失败按既有 tape 记账口径落 mismatch——partial 记录
        # 随后被装配层与投影层拒绝，hook 本身只记录事实不抛错（与
        # sampling mask 的双路径分工一致）。引擎未报（返回 None）= 旧引擎
        # 回退单数，provenance 由 TurnTape.weight_version_provenance 显式
        # 标 single_version_only。
        turn_weight_version_spans = weight_version_spans
        if turn_weight_version_spans is None:
            try:
                turn_weight_version_spans = parse_weight_version_spans(
                    meta, generated=generated
                )
            except SlimeBindingError as exc:
                turn_weight_version_spans = None
                mismatches.append(exc.reason_code)

        if generated < 1:
            missing.append("output_tokens")

        complete = not missing and not mismatches
        record = GenerationCaptureRecord(
            record_id=record_id,
            request_id=str(meta["id"]),
            turn_id=f"turn_{turn_index}",
            trajectory_id=self.trajectory_id,
            model_name=self.model_name,
            backend_name=self.backend_name,
            backend_version=self.backend_version,
            sampling_params=params,
            renderer_cls_name=self.renderer_cls_name,
            tokenizer_name=self.tokenizer_name,
            template_hash=self.template_hash,
            prompt_token_count=len(prompt_ids),
            response_token_count=generated,
            prompt_token_ids_ref=prompt_ref,
            response_token_ids_ref=(
                self._store_int32(f"{record_id}_output_ids", output_ids) if generated else None
            ),
            raw_meta_info_digest=canonical_json_digest(dict(meta)),
            server_timing=_extract_server_timing(meta),
            logprobs_ref=(
                self._store_f64(f"{record_id}_logprobs", output_log_probs) if generated else None
            ),
            top_p_token_ids_ref=(
                self._store_int32(f"{record_id}_topp_ids", top_p_ids)
                if top_p_ids is not None
                else None
            ),
            top_p_token_offsets_ref=(
                self._store_int32(f"{record_id}_topp_offsets", top_p_offsets)
                if top_p_offsets is not None
                else None
            ),
            routed_experts_ref=(
                self._store_int32(f"{record_id}_routing", routing_flat)
                if routing_flat is not None
                else None
            ),
            weight_version=turn_weight_version,
            capture_status="complete" if complete else "partial",
            alignment_status=(
                "aligned" if complete else ("mismatch" if mismatches else "not_checked")
            ),
            captured_at_utc=_now_utc(),
        )
        self.records.append(record)
        self.tapes.append(
            TurnTape(
                record_id=record_id,
                turn_index=turn_index,
                prompt_token_count=len(prompt_ids),
                response_token_count=generated,
                output_ids=tuple(output_ids),
                output_log_probs=tuple(output_log_probs),
                top_p_token_ids=tuple(top_p_ids) if top_p_ids is not None else None,
                top_p_token_offsets=tuple(top_p_offsets) if top_p_offsets is not None else None,
                routed_experts_flat=tuple(routing_flat) if routing_flat is not None else None,
                weight_version=turn_weight_version,
                sampling_supports=sampling_supports,
                weight_version_spans=turn_weight_version_spans,
            )
        )
        return record

    @property
    def tape_by_record_id(self) -> dict[str, TurnTape]:
        return {tape.record_id: tape for tape in self.tapes}


# ---------------------------------------------------------------------------
# D-FA-6：compaction 关闭硬事实（环境注入 + 装配期上下文收缩兜底）
# ---------------------------------------------------------------------------

_CC_EXTRA_ENVS_KEY = "SLIME_AGENT_CC_EXTRA_ENVS"


def parse_bool_env_flag(name: str, raw: str | None, *, default: bool = False) -> bool:
    """正式防线开关的严格解析：只认 "0"/"1"（codex FA-1 审查——"true"/拼写
    错误静默变 False 会无声关闭正式防线，必须拒绝未知值）。"""

    if raw is None or raw == "":
        return default
    if raw == "1":
        return True
    if raw == "0":
        return False
    raise SlimeBindingError(
        "invalid_bool_env_flag",
        f"{name}={raw!r} 不是合法布尔开关——只接受 '0'/'1'（严格解析，"
        "防止拼写错误静默关闭正式防线）。",
    )


# CC 训练守卫环境（codex 轮次 8 源码引导验证：CC 2.1.205 源码 + 黑盒实测）。
# 值语义（`fa/claude_code_retry_timeout_source_guided_validation.md`）：
# - DISABLE_COMPACT=1：关 auto/manual compaction（D-FA-6）；
# - CLAUDE_CODE_MAX_RETRIES=0：CC 自带重试改用 withRetry.ts，默认最多 11 次
#   请求，置 0 使 500/429/断连都只发 1 次——proxy 成为唯一重试 owner；
# - CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK=1：关流式中断后的非流式重发；
# - CLAUDE_CODE_UNATTENDED_RETRY=0：关无人值守持久重试（2.1.205 external
#   build 里该字符串被 tree-shake，设 0 无害、语义留档）。
# 已知例外（实测，不是这几个变量能关的）：流式创建阶段的 **404** 会绕过
# fallback 开关再发一次非流式请求（claude.ts:2607 分支不检查禁用变量）——
# 因此 adapter **任何错误路径都不得返回 404**（见 assert_adapter_status_not_404）。
CLAUDE_CODE_TRAINING_GUARD_ENVS: dict[str, str] = {
    "DISABLE_COMPACT": "1",
    "CLAUDE_CODE_MAX_RETRIES": "0",
    "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK": "1",
    "CLAUDE_CODE_UNATTENDED_RETRY": "0",
}


def ensure_claude_code_training_guards(env: MutableMapping[str, str]) -> dict[str, str]:
    """把 CC 训练守卫环境合并进 SLIME_AGENT_CC_EXTRA_ENVS（原地写 env）。

    slime `agent/harness/claude_code.py` 会把该变量的 JSON 合并进 Claude Code
    子进程环境；返回合并后的 extra-envs dict 作为 audit 证据。冲突检测：
    已有值与守卫值不符即 fail-closed（用户不得覆盖正式防线）。

    警示（CC 压缩文档 + 源码验证）：DISABLE_COMPACT 只覆盖 auto/manual
    compact；Microcompact / Context Collapse 是独立压缩层——**装配期上下文
    收缩检测（reject_context_shrink）是硬兜底**。MAX_RETRIES=0 等只减负 CC
    自身重试，**session poison + execution 主动终止**仍是不可归因故障的主
    防线（404 例外证明环境变量不是完整闭环）。
    """

    merged: dict[str, str] = {}
    raw = env.get(_CC_EXTRA_ENVS_KEY)
    if raw:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise SlimeBindingError(
                "cc_extra_envs_not_object",
                f"{_CC_EXTRA_ENVS_KEY} 已存在但不是 JSON object：{raw!r}。",
            )
        merged.update({str(k): str(v) for k, v in parsed.items()})
    for key, value in CLAUDE_CODE_TRAINING_GUARD_ENVS.items():
        existing = merged.get(key)
        if existing is not None and existing != value:
            raise SlimeBindingError(
                "cc_training_guard_conflict",
                f"{key}={existing!r} 与训练守卫要求值 {value!r} 冲突——正式防线"
                "不得被用户覆盖（fail-closed）。",
            )
        merged[key] = value
    env[_CC_EXTRA_ENVS_KEY] = json.dumps(merged, ensure_ascii=False, sort_keys=True)
    return merged


# 向后兼容别名（旧调用点 = 只关 compaction 的语义子集，现指向全守卫）。
ensure_claude_code_compaction_disabled = ensure_claude_code_training_guards


def assert_adapter_status_not_404(status: int) -> int:
    """adapter 错误路径守卫（codex 轮次 8：CC 2.1.205 对流式创建阶段 404 会
    绕过 fallback 开关再发一次非流式请求）——任何我方 adapter 状态码用本
    函数过一遍，404 直接 fail-closed，改用非 404 + `x-should-retry:false`
    或（主路径）poison + 终止 execution。"""

    if status == 404:
        raise SlimeBindingError(
            "adapter_must_not_return_404",
            "adapter 错误路径返回了 404——CC 2.1.205 会据此绕过 nonstreaming "
            "fallback 开关再发一次请求；改用非 404 状态并 poison session。",
        )
    return status


def detect_context_shrink(
    turns: Sequence[TurnTape], *, shrink_ratio: float = 0.6
) -> list[str]:
    """检测一条轮序列中"无法解释的上下文收缩"（D-FA-6 兜底信号）。

    正常多轮会话的 prompt 单调增长（历史累积）；thinking 剥离/REALIGN 只会
    小幅缩短，compaction / Microcompact / Context Collapse 则把历史替换成
    摘要——prompt 大幅坍缩。判据：某轮 prompt_token_count <
    shrink_ratio ×（此前最大 prompt_token_count）。ratio 预注册 0.6
    （05 计划 D-FA-6；黄线，FA-5 冒烟后校准），返回逐条理由串（空 = 未检出）。

    **作用域警示（codex FA-0 审查严重 2）**：Claude Code 的子 agent 与主
    agent 共享同一 session id（harness 用 ANTHROPIC_AUTH_TOKEN=session_id，
    adapter 以该 token 归组）——**session 级全量 tapes 上跑本检测会把
    "长上下文主 agent 之后启动短上下文子 agent"误判为收缩**。因此：
    session 级结果只作 audit 信号；硬拒绝只允许在**叶链自己的入链轮序列**
    （lineage 内）上执行——编排层照此接线，调用方不得反着用。
    """

    if not (0.0 < shrink_ratio < 1.0) or not math.isfinite(shrink_ratio):
        raise SlimeBindingError(
            "context_shrink_ratio_invalid",
            f"shrink_ratio={shrink_ratio!r} 必须在 (0, 1) 开区间内："
            "0 等于关闭检测，>=1 会把正常等长 prompt 误报为收缩。",
        )
    reasons: list[str] = []
    max_prompt = 0
    for tape in sorted(turns, key=lambda t: t.turn_index):
        if max_prompt and tape.prompt_token_count < shrink_ratio * max_prompt:
            reasons.append(
                f"turn {tape.turn_index}: prompt {tape.prompt_token_count} < "
                f"{shrink_ratio} x max_seen {max_prompt}"
            )
        max_prompt = max(max_prompt, tape.prompt_token_count)
    return reasons


# ---------------------------------------------------------------------------
# 步骤 4/5 衔接：按轮 tape 回填叶链 Sample（S1-3 关键发现的落点）
# ---------------------------------------------------------------------------


def _mask1_runs(loss_mask: Sequence[int]) -> list[tuple[int, int]]:
    """loss_mask 里 mask=1 的连续段（response 座标，半开区间）。"""

    runs: list[tuple[int, int]] = []
    for idx, value in enumerate(loss_mask):
        if value == 1:
            if runs and runs[-1][1] == idx:
                runs[-1] = (runs[-1][0], idx + 1)
            else:
                runs.append((idx, idx + 1))
    return runs


def _match_turns_to_runs(
    response_tokens: Sequence[int],
    runs: Sequence[tuple[int, int]],
    turns: Sequence[TurnTape],
) -> tuple[list[list[TurnTape]], list[TurnTape]]:
    """token 同一性锚定的 run<->turn 匹配（S1-7a 实机形态的回填核心）。

    S1-6 的 mock 假设"mask=1 连续段与轮次一一对应且等长"在真实 TrajectoryManager
    上被证伪（S1-7a run6 实测两种形态）：

    1. **整轮掉落**：REALIGN 把最近一轮响应整段降为上下文（mask=0）或树侧未
       保留该轮 -> mask 段数 = 轮数 - 1（django-16139 实测 3 段 vs 4 轮）；
    2. **同段多轮**：相邻两轮之间没有工具/模板 token 时两轮响应连成一个
       mask=1 段（平铺 tiling）。

    因此改为按 token 逐位锚定：每个 mask=1 段必须被**按提交顺序连续**的若干轮
    output_ids **逐位精确**平铺覆盖；对不上该段起点的轮视为"掉落轮"跳过
    （其 token 仍可能以 mask=0 上下文形式留在序列里，tape 不参与合并）。
    任何段无法被剩余轮精确平铺 -> 当场炸（fail-closed 不放宽：现在是逐位
    token 等值检查，比旧的"数段数"更严）。

    返回 (per_run_turns, used_turns)。
    """

    per_run: list[list[TurnTape]] = []
    turn_idx = 0
    for start, end in runs:
        segment: list[TurnTape] = []
        position = start
        while position < end:
            matched = None
            probe = turn_idx
            while probe < len(turns):
                tape = turns[probe]
                width = tape.response_token_count
                if (
                    width > 0
                    and position + width <= end
                    and tuple(response_tokens[position : position + width]) == tape.output_ids
                ):
                    matched = probe
                    break
                probe += 1
            if matched is None:
                raise SlimeBindingError(
                    "capture_turns_vs_mask_runs_mismatch",
                    f"mask=1 段 [{start},{end}) 自 {position} 起无法被剩余捕获轮逐位平铺"
                    f"（已用 {turn_idx}/{len(turns)} 轮）——存在没有捕获凭据的可训练 token"
                    "或轮次被树侧改写成本函数不认识的形态。",
                )
            segment.append(turns[matched])
            position += turns[matched].response_token_count
            turn_idx = matched + 1
        per_run.append(segment)
    used = [tape for segment in per_run for tape in segment]
    return per_run, used


# ---------------------------------------------------------------------------
# F1 身份制（GPU 前收口，finding §3）：run<->turn 归属不再按内容反推
# ---------------------------------------------------------------------------

# 身份 span 挂在 vendor slime Sample 上的附加属性名（与 sampling-mask 的
# ATTACHED_MASK_ATTR 同一携带机制）：bringup 的 finish_session 包装在树侧
# 导出后写入，bringup_leaf_facts 读出装进 LeafFacts.turn_spans。
RH2_TURN_IDENTITY_SPANS_ATTR = "rh2_turn_identity_spans"


@dataclass(frozen=True)
class TurnIdentitySpan:
    """一条叶链 response 里一个 trained 轮的身份 span（F1 身份制修复）。

    座标系与 ``Sample.loss_mask`` 相同（response 区，首轮 prompt 已剥除）：
    ``start`` 是该轮响应在 response 里的起点，``length`` 是实际进入样本的
    token 数，``capture_record_id`` 是 commit 时刻绑定的 capture 身份
    （CaptureRegistry.bind_turn_identity 的账，树是唯一事实源）。
    """

    start: int
    length: int
    capture_record_id: str


def _runs_from_identity_spans(
    response_tokens: Sequence[int],
    runs: Sequence[tuple[int, int]],
    turns: Sequence[Any],
    spans: Sequence[TurnIdentitySpan],
) -> tuple[list[list[Any]], list[Any]]:
    """身份制的 run<->turn 装配（F1 修复；返回形状与 `_match_turns_to_runs` 相同）。

    与旧 matcher 的本质区别：归属由树侧身份 span **直接给出**（调用方保证
    ``turns[i]`` 与 ``spans[i]`` 是同一轮——bringup 按 span 的
    capture_record_id 顺序取 tape），token 逐位相等从"匹配依据"降级为
    **校验断言**：任何不一致 = 树与 capture 漂移，fail-closed 当场炸。
    身份制下不存在多候选；旧链（无身份信息）继续走 `_match_turns_to_runs`
    原逻辑，行为不动。

    校验项（全部 fail-closed）：
    - spans 与 turns 一一对应；turns 元素带 record_id 属性时（TurnTape）
      复核与 span.capture_record_id 对齐（TurnSupport 无该属性则跳过）；
    - span 宽度必须等于捕获轮的 response_token_count（截断切进轮内 =
      可训练 token 失去完整捕获凭据，与旧 matcher 同样拒绝）；
    - span 覆盖区的 response token 与捕获轮 output_ids 逐位相等；
    - spans 恰好平铺全部 mask=1 段（不多不少：有 span 落在 mask=0 区、
      或 mask=1 段有位置无 span 覆盖，都是树/capture 漂移）。
    """

    if len(turns) != len(spans):
        raise SlimeBindingError(
            "identity_spans_turns_mismatch",
            f"身份 span {len(spans)} 条与捕获轮 {len(turns)} 条不一致——"
            "调用方必须按 span 顺序逐一供轮。",
        )
    prev_end = 0
    for span in spans:
        if span.length <= 0 or span.start < prev_end:
            raise SlimeBindingError(
                "identity_spans_not_ordered",
                f"身份 span ({span.start},+{span.length}) 非正宽或与前一 span 重叠/乱序"
                "——树侧导出损坏。",
            )
        prev_end = span.start + span.length
    for span, tape in zip(spans, turns):
        tape_record_id = getattr(tape, "record_id", None)
        if tape_record_id is not None and tape_record_id != span.capture_record_id:
            raise SlimeBindingError(
                "identity_span_record_misaligned",
                f"身份 span 指认 {span.capture_record_id!r} 但对位捕获轮是 "
                f"{tape_record_id!r}——调用方供轮顺序与 span 不对齐。",
            )
        width = tape.response_token_count
        if span.length != width:
            raise SlimeBindingError(
                "identity_span_width_mismatch",
                f"身份 span ({span.start},+{span.length}) 与捕获轮 "
                f"{span.capture_record_id} 宽度 {width} 不等——截断切进轮内或"
                "树侧身份错位（可训练 token 必须有完整捕获凭据）。",
            )
        actual = tuple(response_tokens[span.start : span.start + span.length])
        if actual != tuple(tape.output_ids):
            raise SlimeBindingError(
                "identity_span_token_drift",
                f"身份 span ({span.start},+{span.length}) 的 response token 与捕获轮 "
                f"{span.capture_record_id} 的 output_ids 逐位不等——树与 capture "
                "漂移（身份制下这不该发生，fail-closed）。",
            )
    per_run: list[list[Any]] = []
    span_idx = 0
    for start, end in runs:
        segment: list[Any] = []
        position = start
        while position < end:
            if span_idx >= len(spans) or spans[span_idx].start != position:
                raise SlimeBindingError(
                    "identity_spans_do_not_tile_runs",
                    f"mask=1 段 [{start},{end}) 自 {position} 起没有身份 span 覆盖"
                    "——存在没有身份凭据的可训练 token。",
                )
            segment.append(turns[span_idx])
            position += spans[span_idx].length
            span_idx += 1
        if position != end:
            raise SlimeBindingError(
                "identity_span_crosses_run_boundary",
                f"身份 span 越过 mask=1 段边界 [{start},{end})（到 {position}）"
                "——trained span 不可能覆盖 mask=0 位置，树/mask 漂移。",
            )
        per_run.append(segment)
    if span_idx != len(spans):
        raise SlimeBindingError(
            "identity_spans_outside_runs",
            f"{len(spans) - span_idx} 条身份 span 不落在任何 mask=1 段内"
            "——trained 轮的 token 在样本里不是可训练位，树/mask 漂移。",
        )
    used = [tape for segment in per_run for tape in segment]
    return per_run, used


def _shape_routing_experts(flat: Sequence[int], *, rows: int, layers: int, topk: int) -> Any:
    """返回 slime 原生的 [rows, layers, topk] routing replay 形状。"""

    try:
        import torch

        return torch.tensor(list(flat), dtype=torch.int32).reshape(rows, layers, topk)
    except Exception:  # noqa: BLE001 - 单测或轻量环境没有 torch 时保留等价嵌套形状
        shaped: list[list[list[int]]] = []
        per_token = layers * topk
        for row in range(rows):
            row_values = list(flat[row * per_token : (row + 1) * per_token])
            shaped.append([row_values[layer * topk : (layer + 1) * topk] for layer in range(layers)])
        return shaped


def backfill_leaf_sample(
    sample: Any,
    turns: Sequence[TurnTape],
    *,
    moe_num_layers: int | None = None,
    moe_router_topk: int | None = None,
    policy_version: str | None = None,
    require_real_weight_versions: bool = False,
    identity_spans: Sequence[TurnIdentitySpan] | None = None,
) -> list[TurnTape]:
    """把 capture 钩子攒下的按轮 tape 回填到一条叶链 Sample 上（原地写字段）。

    背景（S1-3 slime 源码核对）：TrajectoryManager 叶链产物 `_SampleBuilder.
    to_sample()` 只填 tokens/response_length/loss_mask/rollout_log_probs/
    reward/status/metadata；rollout_top_p_token_ids/offsets、rollout_routed_experts、
    weight_versions 的合并逻辑在 `Sample.append_response_tokens/_apply_meta_info`
    （非 TrajectoryManager 路径）。这些字段在 slime Sample dataclass 上都存在、
    可写，本函数按 slime 自己的合并语义回填：

    - run<->turn 归属分两档（F1 身份制修复）：``identity_spans`` 非 None =
      身份路径，归属由树侧身份 span 直取、token 相等降级为校验断言
      （`_runs_from_identity_spans`，漂移 fail-closed）；None = 旧链，
      token 同一性锚定（见 `_match_turns_to_runs`——S1-7a 用真实
      TrajectoryManager 证伪了 mock 的"段数=轮数且等长"假设 3；内容反推
      非单射的已知缺陷 = F1，身份路径修复，旧行为保留不动）；
    - top-p：按轮拼接（`_merge_rollout_top_p_token_data` 语义），mask=0 的
      工具/上下文 token（含掉落轮残留的上下文 token）写零宽 span
      （`_pad_rollout_top_p_offsets` 语义）；
    - routing：取最后一轮的全量 tape。理想情况下行数 = len(tokens) - 1；
      实机上黑盒 harness 可能让 capture prompt 比最终叶链 prompt 多出一段
      前缀上下文（例如 thinking/终端片段被叶链剥离），此时只允许裁掉前缀
      多余行并保留末尾行；少行或不能按 [layers, topk] 整除仍 fail-closed；
    - weight_versions：每个**入训轮**记一次 policy_version（真实值来源 =
      引擎 meta_info.weight_version，S1-7a 已核实）。

    返回实际入训（匹配上 mask=1 段）的轮列表，调用方用它构造分支注释的
    capture 回链（掉落轮不回链——它们不支撑任何可训练 token）。
    """

    loss_mask = list(sample.loss_mask or [])
    runs = _mask1_runs(loss_mask)
    tokens = list(sample.tokens or [])
    response_len = len(loss_mask)
    response_tokens = tokens[-response_len:] if response_len else []
    if identity_spans is not None:
        per_run, used = _runs_from_identity_spans(
            response_tokens, runs, turns, identity_spans
        )
    else:
        per_run, used = _match_turns_to_runs(response_tokens, runs, turns)

    with_top_p = [tape for tape in used if tape.top_p_token_ids is not None]
    if with_top_p:
        if len(with_top_p) != len(used):
            raise SlimeBindingError(
                "top_p_tape_partial_across_turns",
                "部分入训轮有 top-p tape、部分没有——同一采样配方下不可能，事实不一致。",
            )
        merged_ids: list[int] = []
        merged_offsets: list[int] = [0]
        run_segments = {start: segment for (start, _end), segment in zip(runs, per_run)}
        position = 0
        while position < len(loss_mask):
            segment = run_segments.get(position)
            if segment is None:
                merged_offsets.append(merged_offsets[-1])  # 零宽 pad（slime pad 语义）
                position += 1
                continue
            for tape in segment:
                base = merged_offsets[-1]
                offsets = tape.top_p_token_offsets or ()
                merged_ids.extend(tape.top_p_token_ids or ())
                merged_offsets.extend(base + off for off in offsets[1:])
                position += tape.response_token_count
        sample.rollout_top_p_token_ids = merged_ids
        sample.rollout_top_p_token_offsets = merged_offsets

    with_routing = [tape for tape in turns if tape.routed_experts_flat is not None]
    if with_routing:
        last = turns[-1]
        if last.routed_experts_flat is None:
            raise SlimeBindingError(
                "routing_tape_missing_on_last_turn",
                "整段替换语义下最后一轮必须携带全量 routing tape，但它缺失。",
            )
        flat = list(last.routed_experts_flat)
        rows = len(sample.tokens) - 1  # slime _apply_meta_info: expected_rows = len(tokens)-1
        if moe_num_layers is not None and moe_router_topk is not None:
            per_row = moe_num_layers * moe_router_topk
            expected = rows * per_row
            if len(flat) < expected or len(flat) % per_row != 0:
                raise SlimeBindingError(
                    "routing_rows_mismatch_backfill",
                    f"最后一轮 routing 元素数 {len(flat)} != len(tokens)-1 行的期望 {expected}"
                    f"（rows={rows} x layers={moe_num_layers} x topk={moe_router_topk}）。",
                )
            if len(flat) > expected:
                actual_rows = len(flat) // per_row
                extra_rows = actual_rows - rows
                flat = flat[extra_rows * per_row :]
                metadata = dict(getattr(sample, "metadata", None) or {})
                metadata.update(
                    {
                        "rh2_routing_backfill_trimmed_prefix_rows": extra_rows,
                        "rh2_routing_backfill_actual_rows": actual_rows,
                        "rh2_routing_backfill_expected_rows": rows,
                    }
                )
                sample.metadata = metadata
        elif rows > 0 and len(flat) % rows != 0:
            raise SlimeBindingError(
                "routing_rows_mismatch_backfill",
                f"最后一轮 routing 元素数 {len(flat)} 不能按 len(tokens)-1={rows} 行整除。",
            )
        if moe_num_layers is not None and moe_router_topk is not None:
            sample.rollout_routed_experts = _shape_routing_experts(
                flat,
                rows=rows,
                layers=moe_num_layers,
                topk=moe_router_topk,
            )
        else:
            sample.rollout_routed_experts = flat

    # FA-0 真实版本管道：逐入训轮取 tape 上的真实 weight_version，缺失才回退
    # policy_version。口径分两档（精确表述，codex FA-0 审查一般项）：
    # - 正式链（require_real_weight_versions=True）：任何入训轮缺真实值直接
    #   fail-closed（上方断言），序列 100% 真实，禁止任何回退混入；
    # - 非正式路径（bring-up/S1 兼容）：允许逐轮回退 policy_version 形成
    #   真实+回退的混合序列（回退值本身是显式配置事实，不是猜测）；
    # - 两档共同底线：某轮既无真实值又无回退值时**整个字段不写**
    #   （无事实——gate 的 policy_staleness 维会 fail-closed 降级）。
    # V2（per-token spans）：轮 tape 带 weight_version_spans 时，把区间的
    # **全部**版本依序并入（一轮可贡献多个版本）——这是 adv_miles 反例的
    # 直接修复：v10 生成 300 token → 更新 v11 → 续生成 200 token 的轮，
    # 旧口径只记 ["11"]，miles `Sample.oldest_weight_version`（min）随之
    # 高估为 11、DefaultDataBuffer 的 staleness=current-oldest 低报 1 个
    # 版本，可能把本应被 max_weight_staleness 拒绝的组放进训练。spans
    # 口径记 ["10","11"]，oldest/min 语义自动恢复正确。spans[-1].version
    # == tape.weight_version（parse 已校验），序列尾部仍是 finalize 时刻值。
    per_turn_versions: list[str] = []
    versions_complete = True
    for tape in used:
        if tape.weight_version_spans:
            per_turn_versions.extend(span.version for span in tape.weight_version_spans)
            continue
        if require_real_weight_versions and tape.weight_version is None:
            raise SlimeBindingError(
                "turn_weight_version_missing_in_formal_chain",
                f"入训轮 {tape.record_id} 的响应没有 meta_info.weight_version——"
                "正式链禁止用配置值冒充逐轮版本事实（faithful DIS 的 provenance 前置）。",
            )
        version = tape.weight_version if tape.weight_version is not None else policy_version
        if version is None:
            versions_complete = False
            break
        per_turn_versions.append(version)
    if versions_complete and (per_turn_versions or policy_version is not None):
        sample.weight_versions = per_turn_versions or [policy_version]

    # V2：结构化 spans 走既有附加属性机制到 canonicalize（与 rh2_sampling_mask
    # 同款：装配产物类型 + setattr + canonicalize 扩允许集消费转 miles 侧落点，
    # fail-closed）。只在本叶链**存在 spans 事实**时装配（纯单数回退链不挂，
    # 保持旧链路零改变；混合链逐轮 provenance 显式）。lazy import：
    # repoharness2.adapters.miles 包 __init__ 依赖 miles checkout，无 spans
    # 的既有 321 测试面不得因本函数被迫加载。
    if versions_complete and any(tape.weight_version_spans for tape in used):
        from repoharness2.adapters.miles.weight_version_facts import (
            LeafWeightVersionFacts,
            TurnWeightVersionFact,
            attach_leaf_weight_version_facts,
        )

        turn_facts = []
        for tape in used:
            spans = tape.weight_version_spans
            turn_facts.append(
                TurnWeightVersionFact(
                    capture_record_id=tape.record_id,
                    provenance=tape.weight_version_provenance,
                    spans=(
                        tuple((s.version, s.start, s.end) for s in spans)
                        if spans is not None
                        else None
                    ),
                    single_version=(
                        tape.weight_version
                        if tape.weight_version is not None
                        else policy_version
                    ),
                )
            )
        attach_leaf_weight_version_facts(
            sample,
            LeafWeightVersionFacts(
                turns=tuple(turn_facts),
                flat_versions=tuple(per_turn_versions),
            ),
        )
    return used


# ---------------------------------------------------------------------------
# 可注入接口（形状对照 slime 源码；mock 与真实实现共用同一形状）
# ---------------------------------------------------------------------------


class HarnessDriver(Protocol):
    """slime BaseHarness.run 的关键字签名（reference/slime/slime/agent/harness/common.py）。

    真实实现（S1-7a）= 直接调 slime `ClaudeCodeHarness().run(...)`；
    S1-6 mock 打同一形状（参数名一个不许改）。
    """

    name: str

    async def run(
        self,
        sandbox: Any,
        *,
        workdir: str,
        session_id: str,
        adapter_url: str,
        time_budget_sec: int,
        prompt: str,
    ) -> int: ...


@dataclass(frozen=True)
class QuiescenceConfirmed:
    """屏障确认（复核六轮：封闭联合类型之一）。冻结副本 + snapshot
    lineage + 持久证据全部必填——评分链只消费本对象的冻结输入。"""

    frozen_grading_workspace: Any  # 运行时鸭子校验 = WorkspaceRunner（run_bash）
    snapshot_ref: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not callable(getattr(self.frozen_grading_workspace, "run_bash", None)):
            raise ValueError(
                "QuiescenceConfirmed.frozen_grading_workspace 必须是可评分的 "
                "WorkspaceRunner（实现 run_bash）——裸 object 不构成冻结副本。"
            )
        if not self.snapshot_ref:
            raise ValueError("QuiescenceConfirmed 必须携带 snapshot_ref（lineage）。")
        if not self.evidence_refs:
            raise ValueError("QuiescenceConfirmed 必须携带至少一条 evidence_refs。")


@dataclass(frozen=True)
class QuiescenceRejected:
    """屏障拒绝（封闭联合类型之二）：五码之一 + 证据。"""

    reason_code: str
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        from repoharness2.contracts.fa_runtime import RUNTIME_QUIESCENCE_REASON_CODES

        if not self.evidence_refs:
            raise ValueError("QuiescenceRejected 必须携带至少一条 evidence_refs（可审计拒绝）。")
        if self.reason_code not in RUNTIME_QUIESCENCE_REASON_CODES:
            raise ValueError(f"reason_code 必须是勘误 3 五码之一（得到 {self.reason_code!r}）。")


QuiescenceOutcome = QuiescenceConfirmed | QuiescenceRejected  # 真 union 别名


class RuntimeQuiescenceBarrier(Protocol):
    """注入式屏障能力（复核四轮 P0-3）：布尔常量只能声明"作者认为可用"，
    注入对象的存在性本身就是生产接线的证明。fa_formal 构造时必须非空，
    执行时必须调用并取得带证据的结果。F2-2b 提供真实实现（scope 终止/
    写入归零确认/snapshot 冻结/只评冻结副本）。"""

    async def establish(
        self, *, workspace: Any, audit: "RolloutAudit"
    ) -> "QuiescenceConfirmed | QuiescenceRejected": ...


def validate_execution_config(
    config: "SlimeBindingConfig",
    runtime_quiescence_barrier: "RuntimeQuiescenceBarrier | None" = None,
) -> None:
    """启动配置集中校验（复核四轮 P1-4：bringup 在任何副作用前先调本函数；
    orchestrator 构造时再调一次防绕过）。守卫矩阵：

        模式合法性        execution_mode ∈ 三值
        fa_formal 组合    require_real_weight_versions 必须 True + 屏障必须注入
        版本契约（正交）   require_real_weight_versions=True ⇒ 数值版本 +
                          context_shrink 拒绝开启——**与屏障可用性无关**
                          （复核四轮 P0-1：曾被错误缩进进屏障分支）
    """

    mode = config.execution_mode
    if mode not in ("s1_compat", "fa_audit_only", "fa_formal"):
        raise StartupCheckError(
            "unknown_execution_mode", f"execution_mode={mode!r} 不在三值枚举内。"
        )
    if mode == "fa_formal":
        if not config.require_real_weight_versions:
            raise StartupCheckError(
                "fa_formal_requires_real_weight_versions",
                "fa_formal 必须同时开启 require_real_weight_versions（版本契约）。",
            )
        if runtime_quiescence_barrier is None:
            raise StartupCheckError(
                "runtime_barrier_capability_missing",
                "fa_formal 必须注入 RuntimeQuiescenceBarrier（F2-2b 提供实现）"
                "——屏障缺位时正式模式禁止启动；探针用 execution_mode="
                "fa_audit_only（audit-only，产物不可训）。",
            )
        threshold = config.staleness_threshold
        if (
            threshold is None
            or isinstance(threshold, bool)
            or not isinstance(threshold, int)
            or threshold < 0
        ):
            raise StartupCheckError(
                "staleness_threshold_required_in_formal_chain",
                f"fa_formal 要求显式 staleness_threshold（非负 int），得到 {threshold!r}——"
                "D1-4：finalize-time 阈值只定参数化接口、禁止继承隐式默认；数值归决策包 B。",
            )
    if config.require_real_weight_versions:
        version = config.policy_version
        if version is None or version == "step_0":
            raise StartupCheckError(
                "static_policy_version_forbidden_in_formal_chain",
                f"require_real_weight_versions=True 但 policy_version={version!r}——"
                "必须用引擎探针实测的 weight_version，静态哨兵值只允许测试路径。",
            )
        try:
            int(version, 10)
        except ValueError:
            raise StartupCheckError(
                "policy_version_not_numeric_in_formal_chain",
                f"policy_version={version!r} 不是十进制整数——引擎 update_weights "
                "计数器语义要求数值版本，staleness 派生依赖它。",
            ) from None
        if not config.reject_context_shrink:
            raise StartupCheckError(
                "context_shrink_rejection_disabled_in_formal_chain",
                "require_real_weight_versions=True 必须同时开启 "
                "reject_context_shrink——D-FA-6 的收缩兜底是硬要求。",
            )


class SessionAdapter(Protocol):
    """slime BaseAdapter 的会话生命周期面（open/finish/drop，字段名逐一对应）。

    真实实现 = `PerRolloutAdapter`（bringup.py）包装共享 slime
    `AnthropicAdapter`——wrapper 负责把 `physical_attempt_id` 与 hook 一并
    原子注册进 CaptureRegistry（F2-1a 所有权收敛），并把 open/注册纳入
    同一回滚路径；底层 TrajectoryManager 仍来自 AnthropicAdapter。
    finish_session 返回叶链 Sample 列表（TrajectoryManager.get_trajectory 语义）。
    """

    def open_session(
        self,
        sid: str,
        *,
        sampling_defaults: dict | None = None,
        max_context_tokens: int = 0,
        physical_attempt_id: str | None = None,  # F2-1a：经 open 事务原子绑定
        capability_token: str | None = None,  # F2-2：认证映射同事务绑定
    ) -> None: ...

    async def finish_session(
        self,
        sid: str,
        *,
        base_sample: Any,
        reward: float = 0.0,
        extra_metadata: dict | None = None,
        wait_timeout: float = 5.0,
    ) -> list[Any]: ...

    async def drop_session(self, sid: str, *, wait_timeout: float = 5.0) -> None: ...

    def revoke_session(self, sid: str) -> None:
        """F2-2 quiescence 第一步：HTTP 层拒新请求（registry revoked 集合）。

        同步方法（只改状态不做 IO）。编排经 getattr 调用——S1 兼容 mock
        可不实现（无撤销事件），正式 FA 链 PerRolloutAdapter 必须实现。"""
        ...


# 编排按 rollout 构造 hook 后，由工厂产出与之接线的 adapter（真实工厂 = 构造
# AnthropicAdapter 并把 call_sglang_generate 包上捕获钩子；mock 工厂 = 测试替身）。
AdapterFactory = Callable[["GenerationCaptureHook", dict[str, Any]], SessionAdapter]

# 评分提交通道：与 GradingQueue.submit / SWEGradingManager.grade 同关键字形状。
GradingSubmit = Callable[..., Awaitable[GradingReport]]


@dataclass(frozen=True)
class LeafFacts:
    """一条叶链的树侧事实（分支注释的原料，与 finish_session 返回的样本一一对应）。

    真实来源（S1-7a 待实现）：TrajectoryManager 的消息树——重放段 =
    `response_trained` 复用节点、REALIGN 段 = `_align_to_prompt` 覆盖区、
    rewrite 吸收 = `merged_rewrite` metadata（S1-3 已定位）。真实
    TrajectoryManager **没有现成 API** 暴露这些事实（get_trajectory 消费树后
    即丢弃），mock 链由测试提供，真实链需要 hook 树侧快照——差异假设清单第一条。
    """

    branch_id: str
    capture_record_ids: tuple[str, ...]
    context_runs: tuple[ResponseContextRun, ...] = ()
    lineage: CompactedSubTraceLineage | None = None
    # F1 身份制：非 None = 该叶链的 trained 轮身份 span（与 capture_record_ids
    # 逐条对位；bringup 树走查导出）。backfill/装配走身份路径，token 相等
    # 降级为校验断言；None = 旧链按内容锚定（`_match_turns_to_runs`）不动。
    turn_spans: tuple[TurnIdentitySpan, ...] | None = None


LeafFactsFn = Callable[[str, Sequence[Any], "GenerationCaptureHook"], Sequence[LeafFacts]]


def default_leaf_facts(
    sid: str, samples: Sequence[Any], hook: "GenerationCaptureHook"
) -> Sequence[LeafFacts]:
    """默认树侧事实推导：单叶链 = 全部轮次按序回链；多叶链必须显式注入提取器。"""

    if len(samples) != 1:
        raise SlimeBindingError(
            "leaf_facts_extractor_required",
            f"finish_session 产出 {len(samples)} 条叶链（compaction/fan-out 分段），"
            "默认推导只覆盖单叶链——多叶链的轮次归属只有树侧知道，必须注入 leaf_facts_fn。",
        )
    return [
        LeafFacts(
            branch_id="b0",
            capture_record_ids=tuple(record.record_id for record in hook.records),
        )
    ]


# ---------------------------------------------------------------------------
# 任务面与绑定配置
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RolloutTaskSpec:
    """一次 rollout 的任务面（public 半区事实 + 可选的 v1 评分 spec 引用）。

    评分私有材料**不在本对象上**：grading_spec 内嵌的 eval 脚本/parser 闭包
    只进评分容器（S1-4 通道），永不写入 rollout 容器（A6/Q6）。

    W1b 第一集成切片（W2a T1 落地）：prepared 链的任务面 ``grading_spec=None``
    ——rollout 侧只携带 public 面与 digest 锚，评分材料由同一 actor 内的 host
    侧按 attempt 绑定查找（`RolloutOrchestrator(grading_spec_resolver=...)`）。
    内嵌形态只保留给 v1 八题 bring-up 路径（`rollout_task_from_bundle_pair`）
    与既有测试夹具。
    """

    task_id: str
    image: str
    base_commit: str
    prompt: str
    public_bundle_payload: bytes  # 写入 rollout 容器的 public bundle JSON 字节流
    public_bundle_digest: str  # sha256:<hex>（BundleMount 记账）
    grading_spec: GradingEnvSpec | None = None
    workdir: str = "/testbed"
    time_budget_seconds: int = 1800
    # 运行期镜像 digest 比对（S1-7a 前置修复，codex#1，与 GradingEnvSpec 同纪律）：
    # 要么给冻结 manifest digest（rollout 容器启动后与 RepoDigests 比对），
    # 要么显式 image_local_build 豁免；两者都缺 = 构造即拒（豁免不许静默）。
    image_manifest_digest: str | None = None
    image_local_build: bool = False

    def __post_init__(self) -> None:
        if (self.image_manifest_digest is None) == (not self.image_local_build):
            raise ValueError(
                "镜像 digest 校验必须显式二选一：要么提供 image_manifest_digest"
                "（冻结记录，运行期 RepoDigests 比对），要么声明 image_local_build=True"
                "（本地构建镜像豁免）；两者都缺或同时给出都拒绝。"
            )


def rollout_task_from_bundle_pair(
    pair: bundles.BundlePair, *, time_budget_seconds: int = 1800
) -> RolloutTaskSpec:
    """从 S1-2 冻结 BundlePair 构造任务面（真实主链路的取数通道）。"""

    public = pair.public
    return RolloutTaskSpec(
        task_id=pair.instance_id,
        image=public.image,
        base_commit=public.base_commit,
        # 冻结 digest 进任务面：rollout 容器启动后与实际镜像 RepoDigests 比对（codex#1）。
        image_manifest_digest=public.image_manifest_digest,
        prompt=bundles.render_user_prompt(public),
        public_bundle_payload=public.model_dump_json(indent=2).encode("utf-8"),
        public_bundle_digest=public.digest(),
        grading_spec=build_swe_grading_spec(pair),
        workdir=public.workdir,
        time_budget_seconds=time_budget_seconds,
    )


TaskResolver = Callable[[Any], RolloutTaskSpec]


# s1_compat 冻结路径的 staleness 阈值（S1 时代的历史值，**只**在 execution_mode=s1_compat
# 且 config.staleness_threshold=None 时使用）。W1b 第二段（D1-4）起 formal 路径禁止继承任何
# 隐式默认：fa_formal 构造 orchestrator 即要求显式 staleness_threshold（数值归决策包 B），
# 非 s1 模式在握手构造时刻缺阈值 = run-fatal。本常量不是"默认值"，是被冻结的 S1 事实。
S1_COMPAT_LEGACY_STALENESS_THRESHOLD = 4

# W1b 第二段复核修复 #2：在这些阶段由**我方事实**构造 RH2 契约对象时抛出的 pydantic
# ValidationError = 我方接线/事实矛盾（不是任务数据问题）→ typed run-fatal；finalize 之前
# （materialize/harness_run/assemble）的 ValidationError 仍按 stage fallback 归 missing/ABORTED。
_STRUCTURAL_CONTRACT_STAGES: frozenset[str] = frozenset({"finalize", "deliver"})


@dataclass(frozen=True)
class SlimeBindingConfig:
    """绑定级 serving/治理事实（capture 记录、投影、握手的参数来源）。"""

    model_name: str
    backend_version: str
    renderer_cls_name: str  # capture 记录的事实值（来自真实 renderer）
    expected_renderer_cls_name: str  # U-G 期望值（startup + 投影双处断言）
    tokenizer_name: str
    template_hash: str  # sha256:<hex>（chat template 内容 digest）
    adapter_url: str  # 模型代理端点（slime 形态：Anthropic adapter 的 HTTP 地址）
    serving_precision: Literal["float32", "bfloat16", "float16", "float64"] = "bfloat16"
    serving_sampling_backend: str | None = "pytorch"
    backend_name: Literal["sglang", "vllm"] = "sglang"
    harness_name: Literal["claude_code", "codex", "mock_harness"] = "claude_code"
    expect_moe_routing: bool = False  # dense 模型必须 False（A2：dense 只是没有 routing）
    moe_num_layers: int | None = None
    moe_router_topk: int | None = None
    policy_version: str | None = "step_0"  # None = 无 staleness 事实（gate 将 fail-closed 降级）
    # finalize-time staleness 阈值（D1-4 参数化接口）：**无隐式默认**。fa_formal 必须显式给出
    # （validate_execution_config 启动即拒）；非 s1 模式握手构造时刻为 None = run-fatal；
    # s1_compat 为 None 时回退 S1_COMPAT_LEGACY_STALENESS_THRESHOLD（冻结路径零改变）。
    # 数值由决策包 B 确认；复合 group filter 消费时与本字段逐值比对（同一权威配置）。
    staleness_threshold: int | None = None
    # FA-0（05 计划 D-FA-1/FA-0.3）：正式链开关。True 时：
    #   1. 构造 orchestrator 即断言 policy_version 不是静态哨兵值（step_0/None）
    #      且可解析为十进制整数（引擎 update_weights 计数器语义）；
    #   2. 装配期要求每个入训轮的 tape 都带真实 weight_version（缺失 fail-closed）；
    #   3. 握手的 staleness_steps 按真实版本差计算，不再恒 0。
    # False = S1 兼容/测试路径（默认），行为逐字不变。
    # 注（F2-2 复核四轮回归定位）：本旗标是**正交的版本契约**（真实
    # weight_version 强制），模式职责移交 execution_mode。
    require_real_weight_versions: bool = False
    # F2-2 复核四轮：显式运行模式（见 ExecutionModeLiteral 注释）。
    execution_mode: str = "s1_compat"
    # D-FA-6 兜底：装配期检测到"无法解释的上下文收缩"（compaction/Microcompact/
    # Context Collapse 的机械信号）时整条轨迹 fail-closed 退出（收口为 abort 形状，
    # remove_sample=True）。默认 False 保 S1 行为不变；正式 GRPO 基线必须 True。
    reject_context_shrink: bool = False
    context_shrink_ratio: float = 0.6  # 预注册黄线（05 计划 D-FA-6），FA-5 校准
    # P0-2/轮次 9 P0-3（codex）：正式链下 harness 非零退出即拒绝该 execution。
    # 语义澄清（轮次 9 纠正轮次 8 的错误理由）：任务失败负样本 = CC **exit 0**
    # + grader reward=0；CC 非零退出只可能是 harness/API/进程执行失败——
    # 没有已验证的非零业务退出码，formal baseline 全拒。默认 False 仅为
    # S1 测试路径兼容；正式链启动断言强制其为 True（见 __init__）。
    reject_on_nonzero_harness_exit: bool = False
    max_context_len: int = 0
    name_prefix: str = "rh2-rollout"
    label_prefix: str = "rh2.rollout"
    cleanup_timeout_seconds: int = 120
    network_allowlist_justification: str = (
        "rollout 容器内的 Claude Code harness 必须反连宿主侧模型代理端点"
        "（ANTHROPIC_BASE_URL）；S1 仅记录白名单意图，包级过滤归 S2 安全 Runtime。"
    )


# ---------------------------------------------------------------------------
# audit 记录（评分 manager 的 leases/cleanup_failures 同款风格，进程内 evidence）
# ---------------------------------------------------------------------------


@dataclass
class CleanupFailureRecord:
    """Q8：一次清理失败的留痕（policy=record_runtime_finding_and_infra_failure 的落点）。"""

    lease_id: str
    step: str  # 失败的清理步骤（remove_container / release_lease / drop_session）
    detail: str
    failure_category: GradingFailureCategory = "infra_failure"


@dataclass
class RolloutFailureRecord:
    """一次 rollout 级故障（编排把异常收口成 abort 前的归因记录）。"""

    stage: str  # materialize / harness_run / assemble / finalize / deliver
    error_type: str
    detail: str
    failure_category: GradingFailureCategory = "infra_failure"


# F2-0b Observability V0：SGLang meta_info 服务端计时白名单——源码 pin
# `reference/slime/slime/utils/trace_utils.py:SGLANG_TRACE_META_KEYS`
# （slime 本地不可 import，硬编码 + pin；升级 slime 时 fully_async 表面
# 契约测试守 HEAD，白名单漂移人工核对）。只取数值型计时，不含内容。
_SGLANG_SERVER_TIMING_KEYS = (
    "prompt_tokens", "completion_tokens", "cached_tokens",
    "queue_time", "e2e_latency", "decode_throughput",
)


# F2-0b：进程级 monotonic 时钟实例标识——同进程所有线程读同一单调钟，
# 属同一 clock domain，timestamp 可互减（跨进程才不可比）。用 pid 标识。
# F2-2 复核四轮（root-closure）：运行模式 = 唯一显式拓扑信号。
# s1_compat = S1 链（评分交付照旧，无 FA 门控，不产 Outcome）；
# fa_audit_only = FA 探针（身份强制 + 不评分不交付 + audit-only Outcome）；
# fa_formal = 正式链（身份强制 + 注入式 Runtime 屏障必备，屏障确认后
# 才评分交付）。require_real_weight_versions 回归**正交的版本契约**，
# 不再承担模式职责；paid 在场与否不参与任何模式推断。
ExecutionModeLiteral = Literal["s1_compat", "fa_audit_only", "fa_formal"]

PROCESS_CLOCK_DOMAIN = f"proc-{os.getpid()}"
# 注（F2-0b 复核，训前处理项）：proc-pid 不是严格进程 incarnation——fork
# 继承同值、pid 可复用；F2-3/F2-4 前改为含 incarnation 且 fork 后刷新的 ID。
_PROCESS_CLOCK_DOMAIN = PROCESS_CLOCK_DOMAIN


def _extract_server_timing(meta: Mapping[str, Any]) -> "ServerTiming | None":
    """从 meta_info 摘白名单计时键（数值型才收）→ 严格模型 ServerTiming；
    全缺或全部非法返回 None。负值/非有限由 ServerTiming validator 兜底
    （引擎异常值不进遥测——宁缺毋污染）。"""

    out: dict[str, float] = {}
    for key in _SGLANG_SERVER_TIMING_KEYS:
        val = meta.get(key)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            out[key] = val
    if not out:
        return None
    try:
        return ServerTiming(**out)
    except ValidationError:
        # 引擎返回负值/非有限等非法计时——不阻断 capture，只丢该遥测
        # （只捕 ValidationError，程序错误照常暴露；非法遥测计数留 F2-3）
        return None


@dataclass
class RolloutTimelineEntry:
    """一次 rollout 内部的时间线事件。

    `audit.steps` 继续只保存 S1 验收过的生命周期步骤名；本结构作为旁路
    evidence 给 P3/P4 定位长尾瓶颈，避免为了定位一个 Python 转换错误重跑
    完整黑盒 rollout。
    """

    step: str
    seconds_since_start: float
    epoch_seconds: float
    monotonic_ts: float  # F2-0b：原始 monotonic 时间戳（不舍入；相减用它）
    # clock_domain_id = **进程级时钟实例**（同进程各线程共享 monotonic，
    # 属同一 domain，可互减——codex F2-0b P1-2 纠正：不按线程拆 domain）；
    # owner_role 才区分记录者线程角色（orchestrator/adapter/grading）。
    clock_domain_id: str = _PROCESS_CLOCK_DOMAIN
    owner_role: str | None = None
    physical_attempt_id: str | None = None  # 本次物理重放身份（可关联全链）


@dataclass
class RolloutAudit:
    """一次 custom_generate 的完整编排 evidence（tests 与 S1-9 inspector 的对账面）。"""

    trajectory_id: str
    task_id: str
    started_monotonic: float = field(default_factory=time.monotonic)
    started_epoch_seconds: float = field(default_factory=time.time)
    steps: list[str] = field(default_factory=list)
    timeline: list[RolloutTimelineEntry] = field(default_factory=list)
    lease: SandboxLease | None = None
    workspace_handle: WorkspaceHandle | None = None
    launch_spec: HarnessLaunchSpec | None = None
    handshake: BackendHandshake | None = None
    finalized: FinalizedRollout | None = None
    harness_exit_code: int | None = None
    delivered_sample_count: int = 0
    repair_signal_forwarded: bool = False
    lease_released: bool = False
    cleanup_failures: list[CleanupFailureRecord] = field(default_factory=list)
    failure_records: list[RolloutFailureRecord] = field(default_factory=list)
    artifact_paths: list[Path] = field(default_factory=list)
    # D-FA-6：上下文收缩检测结果（空 = 未检出；非空 + reject 关闭 = 只记录）
    context_shrink_reasons: list[str] = field(default_factory=list)
    # 轮次 13 P0-5：audit sink 按 sid drain attempt ledger 的键
    session_id: str | None = None
    # F2-1a：本次物理重放身份（worker dispatch 铸造，经 member metadata
    # 传入；S1 兼容路径可为 None）
    physical_attempt_id: str | None = None
    # F2-0b Observability V0：候选 non-chargeable 区间（权重更新暂停/系统
    # 反压等待，proxy 侧填；V0 只**记录原始区间**，D1b 前不派生
    # chargeable_execution_seconds）。每项 {start, end, reason, source}。
    non_chargeable_intervals: list[dict[str, Any]] = field(default_factory=list)
    # F2-2 quiescence 事实（复核 P0-1 拆分）：session_plane_drained 只
    # 覆盖会话面（撤销 + drain + poison 清白 + 交付账边界干净）；
    # runtime_quiescence_confirmed 是 D1a 完整屏障（含 sandbox execution
    # scope 终止、后台进程/文件写入归零确认、不可变 snapshot 冻结、只对
    # 冻结副本评分）——**完整屏障未落地前恒 False**，completion 推导只信
    # 它，正式链在此之前不产 present_*（missing + 显式 reason_code）。
    session_plane_drained: bool = False
    runtime_quiescence_confirmed: bool = False
    capture_closed: bool = False
    # F2-2 复核 P1-4：终止 trigger 提示（slime exit=-1 = 时间预算耗尽 →
    # hard_wall_timeout；不再误归 harness_crash/completed）
    termination_kind_hint: str | None = None
    # B1：评分基线 digest（manifest 本体不进 audit——数万 entries；
    # 内存 + B5 receipt 持久化）
    baseline_manifest_digest: str | None = None
    baseline_entry_count: int = 0
    # B2：冻结 patch artifact 摘要（本体 execution-local，B5 持久化）
    frozen_patch_digest: str | None = None
    patch_entry_count: int = 0
    excluded_pathset_changed: bool = False
    # B3：hygiene/projection 摘要（AdmissionReport 本体归 FA-2/F2-5）
    runtime_private_pathset_changed: bool = False
    unsafe_artifact_reasons: list[str] = field(default_factory=list)
    scoring_projection_entry_count: int = 0
    # F2-2 复核三轮 P1-2：audit-only 收口标记（屏障前正式探针/带身份
    # bring-up）——bringup 落盘 disposition=audit_only_rejected，
    # fault-domain 统计（FA-2B）按此排除，不污染 capture 故障率
    audit_only: bool = False
    # F2-2 producer：本次 execution 的 Outcome v2（dict 形式随 audit 落盘；
    # S1 兼容路径（无四层身份）为 None）
    outcome_v2: dict[str, Any] | None = None
    # B5 复核三轮 P1-1：artifact 建立前永久拒绝的对象证据（receipt 内嵌）
    rejection_evidence: Any | None = None
    # F2-3 批 1：typed session-plane drain receipt（session_plane_drained
    # bool 的升级形态；finalization receipt 内嵌 durable）
    session_drain_receipt: Any | None = None
    # W1b 第一集成切片（F5）：receipt 持久化后派生的中立 termination 事实载荷
    # （TerminationFactsPayloadV1；generate() 返回前盖到交付面 metadata）。
    # 无 outcome_v2 的 attempt（s1 兼容/身份不全）为 None。
    termination_facts_payload: Any | None = None

    def step(self, name: str) -> None:
        self.steps.append(name)
        self.mark(name)

    def mark(
        self,
        name: str,
        *,
        owner_role: str | None = None,
        clock_domain_id: str = _PROCESS_CLOCK_DOMAIN,
    ) -> None:
        """记录旁路时间线事件（F2-0b）：保存**原始 monotonic 时间戳**，
        clock_domain_id 默认本进程实例（同进程各线程可互减），owner_role
        区分记录者线程角色。缺结束事件天然表示 crash。"""

        now_mono = time.monotonic()
        self.timeline.append(
            RolloutTimelineEntry(
                step=name,
                seconds_since_start=round(now_mono - self.started_monotonic, 3),
                epoch_seconds=round(time.time(), 3),
                monotonic_ts=now_mono,
                clock_domain_id=clock_domain_id,
                owner_role=owner_role,
                physical_attempt_id=self.physical_attempt_id,
            )
        )

    def timeline_dicts(self) -> list[dict[str, float | str]]:
        return [
            {
                "step": entry.step,
                "seconds_since_start": entry.seconds_since_start,
                "epoch_seconds": entry.epoch_seconds,
                "monotonic_ts": entry.monotonic_ts,
                "clock_domain_id": entry.clock_domain_id,
                "owner_role": entry.owner_role,
                "physical_attempt_id": entry.physical_attempt_id,
            }
            for entry in self.timeline
        ]

    def timing_summary(self) -> dict[str, float | None]:
        last_by_step = {entry.step: entry.seconds_since_start for entry in self.timeline}

        def delta(start: str, end: str) -> float | None:
            if start not in last_by_step or end not in last_by_step:
                return None
            return round(last_by_step[end] - last_by_step[start], 3)

        deliver_step = (
            "step9_samples_delivered"
            if "step9_samples_delivered" in last_by_step
            else "step9_degraded_signal_forwarded"
            if "step9_degraded_signal_forwarded" in last_by_step
            else None
        )
        last = self.timeline[-1].seconds_since_start if self.timeline else None
        return {
            "materialize_seconds": delta(
                "step1_custom_generate_invoked", "step2_workspace_materialized"
            ),
            "harness_run_seconds": delta("harness_started", "step3_harness_completed")
            or delta("step2_workspace_materialized", "step3_harness_completed"),
            "capture_finish_backfill_seconds": delta(
                "step3_harness_completed", "step5_leaf_samples_assembled_and_backfilled"
            ),
            "grading_seconds": delta("grading_started", "step6_grading_completed")
            or delta("step5_leaf_samples_assembled_and_backfilled", "step6_grading_completed"),
            "projection_seconds": delta("projection_started", "step7_projection_completed")
            or delta("step6_grading_completed", "step7_projection_completed"),
            "eligibility_gate_seconds": delta(
                "step7_projection_completed", "step8_gate_finalized"
            ),
            "delivery_seconds": delta("step8_gate_finalized", deliver_step)
            if deliver_step is not None
            else None,
            "cleanup_seconds": delta("cleanup_started", "cleanup_completed"),
            "total_audit_seconds": last,
        }


@dataclass(frozen=True)
class _MaterializedSandbox:
    """步骤 2 的产物：容器名 + 契约实例 + 评分可复用的 workspace 执行通道。"""

    container_name: str
    lease: SandboxLease
    handle: WorkspaceHandle
    workspace: "RolloutContainerWorkspace"


@dataclass(frozen=True)
class RolloutContainerWorkspace:
    """rollout 容器形态的 WorkspaceRunner（S1-4 manager 期望的同签名执行通道）。

    与 grading.manager.HostWorkspace 对应：`docker exec <容器> bash -c "cd /testbed && ..."`，
    评分的 patch 导出（EXPORT_PATCH_SCRIPT）直接复用本通道。
    """

    docker: DockerRunner
    container_name: str
    testbed_path: str = "/testbed"

    async def run_bash(self, script: str) -> ExecResult:
        return await self.docker(
            "exec", self.container_name, "bash", "-c", f"cd {self.testbed_path} && {script}"
        )


def _sanitize_for_name(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "-", text).strip("-.")
    return (cleaned or "traj")[:24]


def _set_status(sample: Any, status_name: str) -> None:
    """duck 型写 Sample.status：真实 slime Sample 用嵌套枚举 Sample.Status，
    mock 样本回落成小写字符串（projection 的 _normalized_status 两种都认）。"""

    status_enum = getattr(type(sample), "Status", None)
    if status_enum is not None:
        sample.status = getattr(status_enum, status_name.upper())
    else:
        sample.status = status_name.lower()


# ---------------------------------------------------------------------------
# 编排本体
# ---------------------------------------------------------------------------


class RolloutOrchestrator:
    """S1-6 编排本体：9 步生命周期 + A5 握手契约实例 + fail-closed 收口。

    可注入件（mock 与真实实现同形状）：

    - ``task_resolver``：slime 数据行 -> RolloutTaskSpec（真实 = instance_id 查
      冻结 BundlePair 后 `rollout_task_from_bundle_pair`；测试 = 固定 spec）。
    - ``adapter_factory(hook, session_defaults)``：产出 SessionAdapter。真实 =
      构造 slime AnthropicAdapter 并把 `call_sglang_generate` 包上捕获钩子。
    - ``harness_driver``：BaseHarness.run 形状。真实 = ClaudeCodeHarness()。
    - ``grading_submit``：GradingQueue.submit / SWEGradingManager.grade 形状。
    - ``docker``：docker CLI 通道（S1-4 同款 DockerRunner，FakeDocker 可注入）。
    - ``leaf_facts_fn``：树侧事实提取（默认只支持单叶链）。
    - ``handshake_builder``：staleness 事实来源；缺省按 config.policy_version
      构造零 staleness 握手，policy_version=None 时显式传 None 给 gate
      （该维 fail-closed 降级，S1-5 语义）。
    - ``repair_signal_sink``：组修复信号转发通道（P4：组装配前必须可见）。
    - ``backpressure_events_source``：评分队列反压事件流（GradingQueue.events）。
    """

    def __init__(
        self,
        *,
        config: SlimeBindingConfig,
        task_resolver: TaskResolver | RolloutTaskSpec,
        adapter_factory: AdapterFactory,
        harness_driver: HarnessDriver,
        grading_submit: GradingSubmit,
        docker: DockerRunner | None = None,
        leaf_facts_fn: LeafFactsFn = default_leaf_facts,
        handshake_builder: Callable[[str, Sequence[Any]], BackendHandshake | None] | None = None,
        repair_signal_sink: Callable[[GroupRepairSignal], None] | None = None,
        backpressure_events_source: Callable[[], Sequence[BackpressureEvent]] | None = None,
        mount_planner: Callable[[RolloutTaskSpec], list[BundleMount]] | None = None,
        artifact_dir: Path | str | None = None,
        current_policy_version_provider: Callable[[], str] | None = None,
        session_poison_check: Callable[[str], bool] | None = None,
        session_poison_subscribe: Callable[[str, Callable[[str, str], None]], None] | None = None,
        session_poison_unsubscribe: Callable[[str], None] | None = None,
        session_poison_release: Callable[[str], None] | None = None,
        capture_boundary_check: Callable[[str], None] | None = None,
        audit_sink: Callable[[Any], None] | None = None,
        runtime_quiescence_barrier: "RuntimeQuiescenceBarrier | None" = None,
        finalization_store: "FinalizationStore | None" = None,
        session_drain_owner: Callable[[str], Awaitable[Any]] | None = None,
        grading_spec_resolver: Callable[[Any], GradingEnvSpec] | None = None,
        sandbox_capability_facts_provider: Callable[["RolloutAudit"], SandboxCapabilityFacts | None] | None = None,
    ) -> None:
        # W1b 第二段（A3 / W3b 接缝）：sandbox 正向能力事实的取数口。W3b 落地后由 bringup
        # 注入（sandbox 创建后核实并记录，按 audit/lease 取回）；None = 无事实 → security 维
        # `sandbox_capability_facts_missing`，formal 样本自然非 online（预期时序防护）。
        # s1_compat 不消费本口（该路径显式声明不要求能力事实）。
        self._sandbox_capability_facts_provider = sandbox_capability_facts_provider
        # W1b 第一集成切片（F4/F6）：评分材料取数口。非 None = prepared 链
        # （bringup 注入：样本 → attempt 绑定 → host grading 视图 → actor 内构造
        # spec），此时任务面对象不内嵌评分材料；None = legacy v1 八题链/测试
        # 夹具，用 task.grading_spec。见 `_grading_spec_for`。
        self._grading_spec_resolver = grading_spec_resolver
        # F2-2 复核四轮：集中校验（模式合法性/fa_formal 组合/正交版本契约
        # ——bringup 在副作用前已先调过一次，此处防绕过）
        validate_execution_config(config, runtime_quiescence_barrier)
        # B5：fa_formal 必须带 finalization store——冻结 artifact 的 durable
        # handoff（本体 + receipt）是 A-prime 第 7 条 cleanup 顺序的前提，
        # 缺失时正式链的评分产物会随容器清理蒸发（audit 只有 digest 摘要）。
        if config.execution_mode == "fa_formal" and finalization_store is None:
            raise SlimeBindingError(
                "finalization_store_required",
                "fa_formal 需要 finalization_store（receipt + artifact body "
                "durable handoff）；s1_compat/fa_audit_only 可缺省。",
            )
        self._finalization_store = finalization_store
        # F2-3 批 2a：adapter event-loop 单 owner drain（bringup 接
        # make_threadsafe_session_drain_owner(registry, app_handle.loop)）
        self._session_drain_owner = session_drain_owner
        self._mode: str = config.execution_mode
        self._runtime_barrier = runtime_quiescence_barrier
            # 轮次 14（推翻轮次 9 的硬耦合断言）：非零 exit 拒绝与真实权重
            # 版本不是同一个安全事实——slime episode 时间预算耗尽返回
            # EXIT_TIME_BUDGET_EXCEEDED=-1（sandbox.py:60），是主路径的正常
            # 终止形态；"全部非零一律拒绝"会确定性剔除长任务（长度偏置）。
            # 旋钮保留、glue 默认仍随正式链联动（行为暂不变），但不再启动
            # 断言强制；结构化终止枚举（completed/episode_time_limit/...）
            # 是 FA-2A 前置定义项，落地后按类别决定拒绝/截断评分。
        self.config = config
        self._task_resolver = task_resolver
        self._adapter_factory = adapter_factory
        self._harness_driver = harness_driver
        self._grading_submit = grading_submit
        self._docker = docker or run_docker
        self._leaf_facts_fn = leaf_facts_fn
        self._handshake_builder = handshake_builder
        self._repair_signal_sink = repair_signal_sink
        self._backpressure_events_source = backpressure_events_source or (lambda: ())
        self._mount_planner = mount_planner or self._default_mount_planner
        self.artifact_dir = Path(artifact_dir) if artifact_dir is not None else None
        # FA-0 follow-up（codex 严重 1）：finalize 时刻的 current version 取数点。
        # 真实实现 = glue 注入 engine.get_weight_version 包装（FA-1 接线）；
        # 缺省回退 config.policy_version（rollout 启动时探针值）——在 provider
        # 接入前，握手的 staleness 只是"相对启动版本"的口径，不得称为实时
        # staleness；事实矛盾（seen 比 current 新）无论哪种口径都 fail-closed。
        self._current_policy_version_provider = current_policy_version_provider
        # P0-2（codex 轮次 8）：session poison 复检——harness 返回后，若该
        # session 在执行期间中毒（proxy 判不可归因故障），已捕获的 partial
        # trace 绝不能进评分/训练。glue 注入 registry.poison.is_poisoned。
        self._session_poison_check = session_poison_check
        # 轮次 9 P0-4：poison -> **主动终止**。订阅回调在 harness 运行期挂上，
        # proxy 判不可归因即取消 harness task（不等 CC 自退——404 fallback
        # 已证明客户端自退不可靠）；sandbox 清理走既有 finally 链。
        self._session_poison_subscribe = session_poison_subscribe
        self._session_poison_unsubscribe = session_poison_unsubscribe
        # 轮次 11 身份 4：release = execution 清理 ACK——在 finally 的 sandbox
        # 清理完成后调用（adapter drop_session 只是会话关闭，不算 ACK）
        self._session_poison_release = session_poison_release
        # 轮次 12 P0 层 1：评分/Gate 前的交付账边界断言（glue 注入
        # registry.assert_session_clean——pending/unfinalized draft 在场即
        # poison + 缺员）
        self._capture_boundary_check = capture_boundary_check
        # 轮次 13 P0-5：execution 终态审计落盘（FA 路径绕过 record_event，
        # audit/attempt/清理事实此前只在无界内存）。每个 execution 结束时
        # 调用一次；正式链落盘失败 fail-closed（glue 侧实现语义）。
        self._audit_sink = audit_sink
        self.audits: list[RolloutAudit] = []
        self.outcomes: list[Any] = []  # F2-2：正式链产出的 Outcome v2 序列
        # B1 closure（codex P1-2）：baseline 是 execution-local 变量（generate()
        # 作用域），B2 exporter 以显式参数消费——不建服务级字典/缓存/TTL
        self.cleanup_quarantine: list[str] = []

    # ------------------------------------------------------------------ 入口
    async def generate(
        self, args: Any, sample: Any, sampling_params: dict[str, Any], evaluation: bool = False
    ) -> list[Any]:
        """custom_generate 入口：一次 physical attempt 的执行 + 交付面盖章。

        W1b 第一集成切片（F5）：`_generate_attempt` 的 finally 段在 finalization
        receipt 持久化之后派生 termination 事实载荷（挂 audit）；交付面（成功叶
        链或 abort 形状）在返回给调用方之前统一盖章——载荷以 physical_attempt_id
        为键进入 Sample.metadata（键 `rh2_termination_facts`），供第二段复合
        filter 消费。Fatal/取消原样传播（无交付面可盖）。
        """

        audit_slot: list[RolloutAudit] = []
        delivered = await self._generate_attempt(
            args, sample, sampling_params, evaluation, audit_slot=audit_slot
        )
        if audit_slot and audit_slot[0].termination_facts_payload is not None:
            try:
                stamp_termination_facts(delivered, audit_slot[0].termination_facts_payload)
            except TerminationFactsError as exc:
                # 交付叶与本次 receipt 的 attempt/execution 对不上 = 账实矛盾
                # （与 B4 baseline 矛盾同通道 run-halt），不许带着错事实交付。
                fatal = FatalExecutionInfrastructureError(
                    "termination_facts_stamp_conflict",
                    f"交付面盖章失败：{exc}",
                )
                # W1b 第二段（codex 硬要求）：本 fatal 发生在 receipt/audit 已落盘之后，磁盘
                # 证据（receipt=delivery_prepared、首条审计记录）仍显示成功——经**现有**审计
                # 通道追加一条 attempt-bound 的 fatal 事实（append-only 第二条记录），不建
                # 恢复平台；追加失败只记 secondary fact，不掩盖首因。
                self._append_post_receipt_fatal_fact(audit_slot[0], fatal, stage="deliver")
                self._notify_fatal_halt(fatal)
                raise fatal from exc
        return delivered

    def _append_post_receipt_fatal_fact(
        self, audit: "RolloutAudit", fatal: FatalExecutionInfrastructureError, *, stage: str
    ) -> None:
        """receipt/首条审计已 durable 之后才发生的 fatal：把事实追加进同一 audit 并再走一次
        audit sink（bringup 的 jsonl 是 append-only，第二条记录携带 physical_attempt_id +
        failure_records，磁盘上"成功"与"其后 fatal"两条事实并存、按 attempt 可关联）。"""

        audit.failure_records.append(
            RolloutFailureRecord(
                stage=stage,
                error_type=fatal.reason_code,
                detail=str(fatal)[:500],
            )
        )
        audit.mark(fatal.reason_code)
        if self._audit_sink is None:
            return
        try:
            self._audit_sink(audit)
        except Exception as exc:  # noqa: BLE001 - 追加失败不掩盖首因 fatal
            audit.failure_records.append(
                RolloutFailureRecord(
                    stage=stage,
                    error_type="post_receipt_fatal_audit_append_failed",
                    detail=f"{type(exc).__name__}: {exc}"[:500],
                )
            )

    def _grading_spec_for(self, task: RolloutTaskSpec, sample: Any) -> GradingEnvSpec:
        """评分材料取数口（W1b 第一集成切片）。

        prepared 链：`grading_spec_resolver`（bringup 注入 = 样本 attempt 绑定 →
        host grading 视图 → actor 内构造 spec）——任务面对象上不内嵌评分材料。
        legacy v1 链（八题 bring-up）/测试夹具：`task.grading_spec`。两者都没有 =
        配置矛盾；resolver 失败 = 本 actor 自己的绑定表与正在处理的样本对不上
        ——与 B4 BaselineIntegrityError 同通道 run-halt，不许伪装成
        failed_to_grade 当成员损耗继续。
        """

        if self._grading_spec_resolver is not None:
            try:
                return self._grading_spec_resolver(sample)
            except FatalExecutionInfrastructureError:
                raise
            except Exception as exc:  # noqa: BLE001 - 绑定/材料查找失败一律 run-halt
                raise FatalExecutionInfrastructureError(
                    "grading_materials_join_failed",
                    f"评分材料按 attempt 绑定查找失败：{type(exc).__name__}: {exc}"
                    "——按 A-prime 失败表 run-halt，不得作为成员损耗继续。",
                ) from exc
        if task.grading_spec is not None:
            return task.grading_spec
        raise FatalExecutionInfrastructureError(
            "grading_spec_unavailable",
            f"task {task.task_id} 既无内嵌 grading_spec 也未注入 grading_spec_resolver"
            "——评分材料来源缺失，配置矛盾。",
        )

    async def _generate_attempt(
        self,
        args: Any,
        sample: Any,
        sampling_params: dict[str, Any],
        evaluation: bool = False,
        *,
        audit_slot: list["RolloutAudit"],
    ) -> list[Any]:
        """custom_generate 本体。任何异常都收口为 slime abort 形状 + 清理执行。"""

        # 注意：evaluation=True 是 S1 既有正式面（E10 定案：训练与评测同链路，
        # eval 占位形状返回）——**本方法不拒绝 eval**。05 计划场景 21 的
        # "eval 进入 FA 路径 fail-fast" 落在 FA 生产薄壳
        # （experiments/fa_bringup/rollout_entry.py）：持续 worker 拓扑下
        # eval 必须走标准路径，与 stock fully_async 的 raise 同位。
        task = (
            self._task_resolver
            if isinstance(self._task_resolver, RolloutTaskSpec)
            else self._task_resolver(sample)
        )
        # F2-2（复核 P0-3 重构）：三层分离——公开稳定身份（trajectory_id，
        # 跨 replay 不变）/ 非秘密会话身份（internal sid = s-{paid}，每
        # physical attempt 唯一：slime closed/turn-count/日志/routing key/
        # 异常消息全用它）/ 秘密凭证（capability token，只出现在 CC 环境
        # 与 Authorization 头，guard 认证后即重写为 internal sid，不进入
        # 任何下游或持久面）。
        raw_meta = getattr(sample, "metadata", None)
        meta = raw_meta if isinstance(raw_meta, Mapping) else {}
        physical_attempt_id = (
            str(meta["rh2_physical_attempt_id"])
            if meta.get("rh2_physical_attempt_id") else None
        )
        # F2-2 复核三轮 P0-2：FA 路径的稳定轨迹身份**直接取不可变的
        # rh2_rollout_execution_id**——sample.session_id 会被本方法改写成
        # 当前 attempt 的 internal sid，replay 时经 _session_id 的
        # existing 分支回流会把上次会话身份污染成本次轨迹身份。
        # S1 兼容路径（无 FA metadata）保持旧派生。
        if meta.get("rh2_rollout_execution_id"):
            trajectory_id = str(meta["rh2_rollout_execution_id"])
        else:
            trajectory_id = self._session_id(sample, task)
        capability = mint_session_capability(physical_attempt_id)
        sid = (
            f"s-{physical_attempt_id}"
            if physical_attempt_id is not None
            else f"s-{trajectory_id}"  # S1 兼容：无 replay，稳定即可
        )
        sample.session_id = sid  # 非秘密，随样本持久无碍
        audit = RolloutAudit(
            trajectory_id=trajectory_id,
            task_id=task.task_id,
            session_id=sid,  # internal sid 非秘密，直接落盘
            physical_attempt_id=physical_attempt_id,
        )
        self.audits.append(audit)
        audit_slot.append(audit)
        audit.step("step1_custom_generate_invoked")

        hook = GenerationCaptureHook(
            trajectory_id=trajectory_id,
            model_name=self.config.model_name,
            backend_name=self.config.backend_name,
            backend_version=self.config.backend_version,
            renderer_cls_name=self.config.renderer_cls_name,
            tokenizer_name=self.config.tokenizer_name,
            template_hash=self.config.template_hash,
        )
        top_p = float(sampling_params.get("top_p", 1.0))
        # B2（R6-ext）请求侧二选一：采样支持集的 wire 约定按**args 显式配置**
        # 选择，不猜引擎型号——`args.rh2_engine_sampling_mask=True`（miles 训练
        # 脚本/测试显式设置）= 目标引擎是带原生 sampling-mask primitive 的
        # sglang-miles 构建，top_p<1.0 时开新顶层约定 `return_sampling_mask`；
        # 缺省/False = 旧 slime patch 引擎回退面，保持旧 custom_params 约定
        # `return_top_p_token_ids`，行为与 C1′-b 之前逐字不变。两约定互斥
        # （同开会在装配层与旧投影分支间造两套账，capture_wire 只按会话默认
        # 键各自翻译）。
        use_mask_wire = bool(getattr(args, "rh2_engine_sampling_mask", False))
        session_defaults = {
            **sampling_params,
            # E2 硬依赖：top_p<1.0 必须请求 top-p tape；MoE 必须请求 routing tape。
            "return_top_p_token_ids": top_p < 1.0 and not use_mask_wire,
            "return_routed_experts": self.config.expect_moe_routing,
        }
        if use_mask_wire:
            session_defaults["return_sampling_mask"] = top_p < 1.0
        # mask 链路的占位/剔除样本不写旧 slime 零宽 top-p tape 字段：miles
        # Sample 没有 rollout_top_p_token_ids/offsets（canonicalize 会按未知
        # 属性拒绝），且 miles 训练转换也不消费该字段——传 None 让
        # _abort_result/_deliver 的 eval 占位保持 miles 可回收形状。旧链
        # tape_top_p == top_p，行为不变。
        tape_top_p = None if use_mask_wire else top_p
        # mask 链路投影需要的支持集硬上界（T0-A）：直接取本次 generate 的
        # 采样配方 top_k（与 capture_wire 前置校验的会话上界同源；缺失/非法
        # 值由投影装配层 fail-closed，不在此提前猜测）。旧链恒 None。
        mask_top_k = (
            sampling_params.get("top_k") if use_mask_wire and top_p < 1.0 else None
        )
        adapter = self._adapter_factory(hook, session_defaults)

        # W1b 第一集成切片：评分材料按 attempt 惰性取一次（hygiene 判定与评分
        # 提交共用同一份），取数失败按 `_grading_spec_for` 的 run-halt 语义传播。
        grading_spec_cell: list[GradingEnvSpec] = []

        def grading_spec_for_attempt() -> GradingEnvSpec:
            if not grading_spec_cell:
                grading_spec_cell.append(self._grading_spec_for(task, sample))
            return grading_spec_cell[0]

        stage = "identity"
        sandbox: _MaterializedSandbox | None = None
        session_open = False
        try:
            # F2-2 复核三轮 P0-1：正式模式（显式旗标，不用 paid 推断）在
            # materialize 前强制完整四层身份——身份注入故障 fail-closed
            # （结构化 abort + audit 落盘），不得静默回落 S1 形状（那会
            # 绕过 audit-only 防线去评分/交付）。
            if self._mode != "s1_compat" and (
                physical_attempt_id is None
                or meta.get("rh2_physical_attempt_seq") is None
                or not meta.get("rh2_rollout_execution_id")
                or not meta.get("rh2_prompt_group_id")
                or meta.get("rh2_group_index") is None
                or meta.get("rh2_member_slot") is None
            ):
                raise SlimeBindingError(
                    "fa_identity_incomplete_in_formal_mode",
                    f"FA 模式 member metadata 四层身份不全（trajectory={trajectory_id}）"
                    "——entry 契约破损，fail-closed（不评分不交付）。",
                )
            stage = "materialize"
            sandbox = await self._materialize_rollout_sandbox(task, trajectory_id, audit)
            audit.step("step2_workspace_materialized")
            # B1（A-prime 第 2 条）：harness 获写权前生成评分基线唯一权威。
            # 仅 FA 模式（s1_compat 零改动）；失败走既有异常收口（missing）。
            if self._mode != "s1_compat":
                from repoharness2.adapters.slime.baseline_census import (
                    generate_baseline_manifest,
                )
                from repoharness2.contracts.baseline_manifest import (
                    compute_baseline_manifest_digest,
                )

                head = await sandbox.workspace.run_bash(
                    f"git -C {task.workdir} rev-parse HEAD"
                )
                if head.exit_code != 0:
                    raise SlimeBindingError(
                        "baseline_head_unreadable",
                        f"materialized HEAD 读取失败：{head.stderr.strip()[-200:]}",
                    )
                baseline_manifest = await generate_baseline_manifest(
                    sandbox.workspace,
                    task_id=task.task_id,
                    workdir=task.workdir,
                    public_bundle_digest=task.public_bundle_digest,
                    # 实际运行镜像的不可变 digest（lease 实测）——tag 不得
                    # 伪装；环境包 lineage 未接通 = formal gate blocker，
                    # 不用 bundle digest 填空（codex B1 P1-1）
                    runtime_image_digest=sandbox.lease.image_digest,
                    materialized_head=head.stdout.strip(),
                    task_base_commit=task.base_commit,
                )
                audit.baseline_manifest_digest = compute_baseline_manifest_digest(
                    baseline_manifest
                )
                audit.baseline_entry_count = len(baseline_manifest.entries)
                audit.mark("baseline_manifest_generated")

            stage = "harness_run"
            launch = HarnessLaunchSpec(
                harness_name=self.config.harness_name,
                workspace_id=sandbox.handle.workspace_id,
                workdir=task.workdir,  # Q3
                model_proxy=ModelProxyEndpoint(  # Q4
                    base_url=self.config.adapter_url,
                    wire_protocol="anthropic_messages",
                    session_id=sid,
                    inject_env_var="ANTHROPIC_BASE_URL",
                ),
                env_injections={"BASH_ENV": materialize.BASH_ENV_PATH},
                time_budget_seconds=task.time_budget_seconds,
            )
            audit.launch_spec = launch
            adapter.open_session(
                sid,
                physical_attempt_id=physical_attempt_id,
                sampling_defaults=session_defaults,
                max_context_tokens=self.config.max_context_len,
                capability_token=capability.token,  # F2-2：认证映射同事务绑定
            )
            session_open = True
            audit.mark("harness_started")
            harness_task = asyncio.ensure_future(
                self._harness_driver.run(
                    sandbox.workspace,
                    workdir=launch.workdir,
                    # F2-2：CC 侧拿**秘密 token**做 auth（guard 认证后重写为
                    # internal sid），launch_spec/audit 里的 session_id 是
                    # 非秘密 internal sid
                    session_id=capability.token,
                    adapter_url=launch.model_proxy.base_url,
                    time_budget_sec=launch.time_budget_seconds,
                    prompt=task.prompt,
                )
            )
            if self._session_poison_subscribe is not None:
                # P0-4/轮次 10 P0-1：poison 即取消 harness。生产拓扑是双线程
                # （Ray actor loop 持 harness_task；poison 从 aiohttp adapter
                # 线程发出）——Task.cancel() 不是跨线程安全 API，必须经
                # owner loop 的 call_soon_threadsafe 投递。
                owner_loop = asyncio.get_running_loop()

                def _cancel_from_any_thread(_sid: str, _reason: str) -> None:
                    owner_loop.call_soon_threadsafe(harness_task.cancel)

                self._session_poison_subscribe(sid, _cancel_from_any_thread)
            try:
                exit_code = await harness_task
            except asyncio.CancelledError:
                if self._session_poison_check is not None and self._session_poison_check(sid):
                    # poison 触发的取消：收口为缺员（不是外层关停）
                    raise SlimeBindingError(
                        "session_poisoned_during_execution",
                        f"session {sid} 中毒且 harness 已被主动终止——"
                        "partial trace 作废，execution 缺员。",
                    ) from None
                raise  # 外层取消（关停/超时）原样传播
            finally:
                if self._session_poison_unsubscribe is not None:
                    self._session_poison_unsubscribe(sid)
            audit.harness_exit_code = exit_code
            if exit_code == -1:
                # F2-2 复核 P1-4：slime EXIT_TIME_BUDGET_EXCEEDED=-1 = 时间
                # 预算耗尽——按 D1a 记 hard_wall_timeout（仅 termination
                # trigger），completion 由完整性事实推导；不走 nonzero 拒绝
                # （那会误归 harness_crash），也不伪装 completed。处置留 D1b。
                audit.termination_kind_hint = "hard_wall_timeout"
                audit.mark("hard_wall_timeout_observed")
            audit.step("step3_harness_completed")

            stage = "assemble"
            # F2-2 quiescence 第一步：撤销 capability（HTTP 层拒新请求）。
            # 顺序 = revoke（拒新）→ finish/drain（清旧）→ poison/边界断言
            # （对账）——撤销必须先于 drain，否则 drain 期间仍可能开新轮。
            drain_result = None
            if self._mode != "s1_compat":
                # F2-3 批 2a 复核 P1（顺序根修）：**单 owner drain 必须先于
                # 轨迹冻结**——先在 adapter loop 上证明"不再有 turn 写入"
                # （revoke + inflight 归零 + typed clean 结果），才允许
                # finish_session 弹出轨迹树。旧顺序（先冻结后 drain）下，
                # 已过 guard 未进 slime inflight 的请求可在冻结后 record_
                # turn，owner 事后仍报 clean——冻结先于最后一次写。跨线程
                # 的提前 adapter.revoke_session 不再是正式链线性化点
                # （owner 内的 registry.revoke 在 adapter loop 上原子生效）。
                drain_result = await self._drain_session_plane_owned(
                    sid, physical_attempt_id
                )
                audit.mark("session_revoked")
            else:
                revoke = getattr(adapter, "revoke_session", None)
                if revoke is not None:  # S1 兼容路径：尽力拒新，无 owner 语义
                    revoke(sid)
                    audit.mark("session_revoked")
            # 轮次 13 P0-2：**drain 屏障先行**——正式链上方 owner 已证
            # inflight 归零；finish_session 此刻冻结/弹出轨迹树是安全的。
            # 之后 poison/边界断言读到的是完整快照。顺序：drain ->
            # freeze -> poison -> 非零 exit -> 边界断言 -> 冻结 records 快照。
            samples = await adapter.finish_session(
                sid,
                base_sample=sample,
                reward=0.0,  # 真实 reward 出自步骤 6 评分，之后再回写
                extra_metadata={"instance_id": task.task_id},
            )
            if self._session_poison_check is not None and self._session_poison_check(sid):
                raise SlimeBindingError(
                    "session_poisoned_during_execution",
                    f"session {sid} 在 harness 执行期间中毒（proxy 判不可归因故障）"
                    "——已捕获的 partial trace 全部作废，execution 缺员。",
                )
            if (
                self.config.reject_on_nonzero_harness_exit
                and exit_code != 0
                and exit_code != -1  # hard wall 不是 crash（P1-4），继续按事实收口
            ):
                raise SlimeBindingError(
                    "nonzero_harness_exit_in_formal_chain",
                    f"harness 非零退出 {exit_code}（正式链拒绝）——训练守卫下 CC "
                    "不该因 infra 失败退出，可疑到拒绝该 execution。",
                )
            if self._capture_boundary_check is not None:
                try:
                    self._capture_boundary_check(sid)
                except Exception as exc:
                    raise SlimeBindingError(
                        "capture_boundary_unclean",
                        f"评分前交付账边界断言失败（drain 之后）：{exc}",
                    ) from exc
            # F2-2（复核 P0-1）+ 批 2a 复核 P1：只宣告**会话面**排空，且
            # 只在 typed clean 结果（正式链）+ 边界断言全部通过之后置位
            # ——dirty owner 已在 finish_session 之前 abort，绝不出现
            # "drained=True 与 unclean 归因并存"的审计矛盾。完整 runtime
            # quiescence 由屏障另行确认。
            audit.session_plane_drained = True
            audit.mark("session_plane_drained")
            if self._mode != "s1_compat":
                assert drain_result is not None  # 正式链在冻结前已过 owner
                assert physical_attempt_id is not None  # fa 模式恒有（owner 相等已证）
                audit.session_drain_receipt = SessionDrainReceiptV1(
                    receipt_id=(
                        "drain_"
                        + re.sub(r"[^A-Za-z0-9._-]", "_", physical_attempt_id)
                    ),
                    session_id=sid,
                    physical_attempt_id=physical_attempt_id,
                    trajectory_id=trajectory_id,
                    task_id=task.task_id,
                    revoke_enforced=drain_result.revoke_enforced,
                    late_requests_rejected_after_revoke=(
                        drain_result.late_requests_rejected_after_revoke
                    ),
                    pending_turns_after_drain=drain_result.pending_turns,
                    unfinalized_drafts_after_drain=drain_result.unfinalized_drafts,
                    poison_clean=drain_result.poison_clean,
                    capture_record_count=len(hook.records),
                    turn_seq_high_water=drain_result.turn_seq_high_water,
                    weight_versions_seen=list(drain_result.weight_versions_seen),
                    drained_at_utc=_now_utc(),
                )
                audit.mark("session_drain_receipt_issued")
            if not hook.records:
                raise SlimeBindingError(
                    "no_capture_records",
                    "harness 运行结束但 capture 钩子一轮都没记到——模型代理没被调用"
                    "或钩子没接上（A4：无捕获事实的轨迹不可训练）。",
                )
            audit.step("step4_capture_records_ready")
            # D-FA-6 兜底（session 级）：只作 audit 信号，不硬拒绝——CC 子 agent
            # 与主 agent 共享 session id，session 级比较会误杀合法的短上下文
            # 子 agent（codex FA-0 审查严重 2）。硬拒绝在叶链级执行（见下方
            # 装配循环，lineage 内比较）。
            session_shrink = detect_context_shrink(
                hook.tapes, shrink_ratio=self.config.context_shrink_ratio
            )
            if session_shrink:
                audit.context_shrink_reasons.extend(
                    f"session: {reason}" for reason in session_shrink
                )
            if not samples:
                raise SlimeBindingError(
                    "adapter_session_empty", "finish_session 没有产出任何叶链 Sample。"
                )
            leaf_facts = list(self._leaf_facts_fn(sid, samples, hook))
            if len(leaf_facts) != len(samples):
                raise SlimeBindingError(
                    "leaf_facts_length_mismatch",
                    f"树侧事实 {len(leaf_facts)} 条与叶链 Sample {len(samples)} 条不一致。",
                )
            tape_index = hook.tape_by_record_id
            used_record_ids: list[tuple[str, ...]] = []
            for leaf, facts in zip(samples, leaf_facts):
                turns = []
                for record_id in facts.capture_record_ids:
                    tape = tape_index.get(record_id)
                    if tape is None:
                        raise SlimeBindingError(
                            "capture_record_unknown_in_backfill",
                            f"叶链 {facts.branch_id} 回链 {record_id!r} 不在捕获轮次里。",
                        )
                    turns.append(tape)
                # D-FA-6 硬拒绝（叶链级）：只在该叶链自己的入链轮序列上检测
                # ——lineage 内的 prompt 坍缩没有"子 agent 独立会话"这种合法
                # 解释，检出即整条轨迹 fail-closed 退出基线。
                branch_shrink = detect_context_shrink(
                    turns, shrink_ratio=self.config.context_shrink_ratio
                )
                if branch_shrink:
                    audit.context_shrink_reasons.extend(
                        f"branch {facts.branch_id}: {reason}" for reason in branch_shrink
                    )
                    if self.config.reject_context_shrink:
                        raise SlimeBindingError(
                            "context_shrink_detected",
                            f"叶链 {facts.branch_id} 检测到无法解释的上下文收缩"
                            "（compaction 嫌疑），轨迹退出基线：" + "; ".join(branch_shrink),
                        )
                # F1 身份制：树侧身份 span 在场（bringup 链）即走身份路径
                # ——归属直取、token 相等只作校验断言；span 缺席（mock/
                # default_leaf_facts 旧链）走原 token 锚定逻辑，行为不动。
                used = backfill_leaf_sample(
                    leaf,
                    turns,
                    moe_num_layers=self.config.moe_num_layers,
                    moe_router_topk=self.config.moe_router_topk,
                    policy_version=self.config.policy_version,
                    require_real_weight_versions=self.config.require_real_weight_versions,
                    identity_spans=facts.turn_spans,
                )
                # B2（R6-ext）叶链装配：mask 链路（本次会话请求了
                # return_sampling_mask）把逐轮引擎支持集装配成整条叶链的
                # CSR mask 并挂到 Sample（rh2_sampling_mask 附加属性，
                # canonicalize 的 slime 分支消费转 miles 一等字段）。装配用
                # 与 top-p tape 回填**同一份** run<->turn 锚定实现
                # （_mask1_runs/_match_turns_to_runs，掉落轮自动跳过），
                # 观察/工具位（mask=0）补单例支持集。任一回链轮缺支持集
                # tape = capture 面破损，fail-closed（收口为本 execution
                # 的 abort，不静默交付无 mask 样本）。
                if session_defaults.get("return_sampling_mask"):
                    from repoharness2.adapters.miles.sampling_mask_assembly import (
                        TurnSupport,
                        assemble_leaf_sampling_mask,
                        attach_assembled_mask,
                    )

                    turn_supports = []
                    for tape in turns:
                        if tape.sampling_supports is None:
                            raise SlimeBindingError(
                                "sampling_mask_tape_missing_in_assembly",
                                f"叶链 {facts.branch_id} 回链轮 {tape.record_id} 无"
                                " sampling-support tape——mask 会话每一轮都必须捕到"
                                "支持集（partial 捕获不许进装配）。",
                            )
                        turn_supports.append(
                            TurnSupport(
                                output_ids=tape.output_ids,
                                supports=tape.sampling_supports,
                            )
                        )
                    leaf_loss_mask = list(leaf.loss_mask or [])
                    leaf_tokens = list(leaf.tokens or [])
                    leaf_response_tokens = (
                        leaf_tokens[-len(leaf_loss_mask):] if leaf_loss_mask else []
                    )
                    attach_assembled_mask(
                        leaf,
                        assemble_leaf_sampling_mask(
                            leaf_response_tokens,
                            leaf_loss_mask,
                            turn_supports,
                            identity_spans=facts.turn_spans,
                        ),
                    )
                # 分支注释只回链**入训轮**（掉落轮不支撑任何 mask=1 token；
                # S1-7a token 锚定匹配的产物），空则回退 facts 原单
                # （全 mask=0 的叶链在 gate 层按 no_trainable_tokens 收口）。
                used_record_ids.append(
                    tuple(tape.record_id for tape in used)
                    or tuple(facts.capture_record_ids)
                )
            leaf_facts = [
                LeafFacts(
                    branch_id=facts.branch_id,
                    capture_record_ids=used_ids,
                    context_runs=facts.context_runs,
                    lineage=facts.lineage,
                    turn_spans=facts.turn_spans,
                )
                for facts, used_ids in zip(leaf_facts, used_record_ids)
            ]
            # F1 身份制：span 附加属性只是 finish_session -> leaf_facts 的
            # 运输载体，事实已进 LeafFacts.turn_spans——装配完成即从样本上
            # 剥除，不让内部属性越过 canonicalize 的未知属性 fail-closed
            # 边界（身份 span 不是训练面事实，miles Sample 没有对应位置）。
            for leaf in samples:
                leaf.__dict__.pop(RH2_TURN_IDENTITY_SPANS_ATTR, None)
            audit.capture_closed = True  # F2-2：记录在场且回链装配完成
            audit.step("step5_leaf_samples_assembled_and_backfilled")

            # F2-2 复核二轮 P0-1/P0-2：完整 Runtime 静止屏障（F2-2b）落地
            # 前，正式 FA 路径（有 physical attempt 身份）**不评分、不交付**
            # ——评分会读仍可能被 setsid 后台进程写入的活动 workspace（违反
            # 已批准的"只评冻结副本"），交付会把 missing 成员送进 collector
            # （_member_ok 只看 remove_sample）。收口 = audit-only Outcome
            # （missing + runtime_barrier_unavailable）+ abort 形状（
            # remove_sample=True → collector 显式拒绝）。S1 兼容路径（无
            # paid）不受影响。屏障落地后本挡板整块删除。
            if self._mode == "fa_audit_only":
                audit.audit_only = True
                self._produce_outcome_v2(
                    audit=audit,
                    raw_meta=raw_meta,
                    termination_kind="completed",  # producer 内 hard-wall hint 优先
                    failure_category=None,
                    reason_code="runtime_barrier_unavailable",
                    failed_component=None,
                    task_resolved=None,
                    turn_weight_versions=None,
                    current_version_at_finalize=None,
                    eligibility_report_id=None,
                )
                audit.mark("formal_chain_audit_only_pre_barrier")
                return self._abort_result(
                    sample, reason="rh2_runtime_barrier_unavailable", task=task, top_p=tape_top_p,
                    audit=audit,
                )
            grading_workspace = sandbox.workspace  # s1_compat 既有语义
            barrier_evidence: list[str] = []
            frozen_delta = None  # B4：仅 fa_formal 屏障确认后组装
            if self._mode == "fa_formal":
                # 复核四轮 P0-3：注入式屏障必须真实执行并出具带证据结果；
                # 确认失败 → runtime_quiescence_failure（勘误 3 五码）+
                # abort，绝不评分交付
                try:
                    result = await self._runtime_barrier.establish(
                        workspace=sandbox.workspace, audit=audit
                    )
                except Exception as exc:
                    # P1-4：未知 barrier 异常按已批 D4 表走 run_halt（基建
                    # 级致命，worker 停机），禁止软降级成 capture 故障。
                    # 七轮 P1-1：先写结构化故障（finally 的 audit sink 会
                    # 持久化归因），再走独立致命通道
                    audit.failure_records.append(
                        RolloutFailureRecord(
                            stage="runtime_barrier",
                            error_type="runtime_barrier_exception",
                            detail=f"{type(exc).__name__}: {exc}"[:500],
                        )
                    )
                    audit.mark("runtime_barrier_exception")
                    raise FatalExecutionInfrastructureError(
                        "runtime_barrier_exception",
                        f"Runtime 屏障执行异常：{type(exc).__name__}: {exc}——"
                        "未知屏障故障按 D4 run_halt，不得归因 capture。",
                    ) from exc
                if isinstance(result, QuiescenceConfirmed):
                    audit.runtime_quiescence_confirmed = True
                    audit.mark("runtime_quiescence_confirmed")
                    grading_workspace = result.frozen_grading_workspace
                    barrier_evidence = [f"snapshot:{result.snapshot_ref}", *result.evidence_refs]
                    if audit.session_drain_receipt is not None:
                        # F2-3 批 1：drain receipt 进屏障证据链（Outcome
                        # evidence_refs 可回链到 typed 会话面排空事实）
                        barrier_evidence.append(
                            f"drain_receipt:{audit.session_drain_receipt.receipt_id}"
                        )
                    audit.mark("frozen_snapshot_adopted")
                    # B2：静止确认后导出 FrozenPatchArtifact（无 git 枚举，
                    # host 侧对 B1 baseline 结构化比较）。artifact 为
                    # execution-local，B3 hygiene 显式消费；audit 只落
                    # digest/计数。失败 → typed SlimeBindingError（missing
                    # 收口；unsupported 对象单列码供 B3 分类）。
                    from repoharness2.adapters.slime.patch_exporter import (
                        PatchExportError,
                        export_frozen_patch,
                    )
                    from repoharness2.contracts.frozen_patch import (
                        compute_frozen_patch_digest,
                    )

                    try:
                        # B2 closure P1-4：exporter 消费屏障产出的冻结
                        # workspace（不绕回 live sandbox.workspace——当前
                        # 包装同底层，物理快照落地后语义即分叉）
                        frozen_patch = await export_frozen_patch(
                            grading_workspace,
                            baseline_manifest,
                            rollout_execution_id=(
                                str(meta.get("rh2_rollout_execution_id"))
                                if meta.get("rh2_rollout_execution_id")
                                else trajectory_id
                            ),
                            physical_attempt_id=physical_attempt_id,
                        )
                    except PatchExportError as exc:
                        if exc.reason_code == "unsupported_object_in_patch":
                            # B3 兑现 B2 登记：模型产出不支持对象 = unsafe
                            # artifact（present + 永久拒绝，不评分）。
                            # B5 复核三轮 P1-1：此分支在 artifact 建立之前
                            # 返回——对象路径/类型作为 typed 证据挂 audit，
                            # 由 receipt 内嵌 durable（workspace 清理后
                            # 拒绝证据不消失）。
                            audit.rejection_evidence = RejectedObjectEvidenceV1(
                                reason_code=exc.reason_code,
                                object_path=exc.object_path,
                                object_type=exc.object_type,
                            )
                            audit.unsafe_artifact_reasons = [
                                f"{exc.reason_code}:{exc.object_path or '?'}"
                                f":{exc.object_type or 'unknown'}"
                            ]
                            audit.mark("unsafe_artifact_rejected")
                            self._produce_outcome_v2(
                                audit=audit,
                                raw_meta=raw_meta,
                                termination_kind="completed",
                                failure_category=None,
                                reason_code="unsafe_artifact_permanent_rejection",
                                failed_component="patch_hygiene",
                                task_resolved=None,
                                turn_weight_versions=hook_turn_weight_versions(hook),
                                current_version_at_finalize=(
                                    self._current_policy_version_provider()
                                    if self._current_policy_version_provider is not None
                                    else self.config.policy_version
                                ),
                                eligibility_report_id=None,
                                extra_evidence=[
                                    *barrier_evidence,
                                    exc.reason_code,
                                    f"object:{exc.object_path or '?'}"
                                    f":{exc.object_type or 'unknown'}",
                                ],
                            )
                            # W1b 第二段（三终态 ③ / 附录 A 契约豁免集）：unsafe 是
                            # present_complete + 永久拒绝——不再压成 ABORTED（ABORTED 只
                            # 给 completion=missing），而是真实交付 + admission 载荷（无
                            # EligibilityReport），由复合 filter 整组 DROP。
                            return self._deliver_present_member(
                                task=task, raw_meta=raw_meta, samples=samples,
                                finalized=None, audit=audit,
                            )
                        raise SlimeBindingError(exc.reason_code, str(exc)) from exc
                    audit.frozen_patch_digest = compute_frozen_patch_digest(frozen_patch)
                    audit.patch_entry_count = len(frozen_patch.entries)
                    audit.excluded_pathset_changed = frozen_patch.excluded_pathset_changed
                    audit.mark("frozen_patch_exported")
                    # B5 复核 P1-2（T0 第 9 条 retention）：artifact 建立
                    # 后**立刻**持久化本体——先于任何 hygiene 分支返回。
                    # unsafe 只影响评分与准入，不销毁审计证据（否则 unsafe
                    # 拒绝的 delta 随容器清理蒸发，digest 引用悬空）。
                    # 失败 = T0 失败表第 1 行"无法建立可信 artifact
                    # （持久化失败）"→ missing 收口。
                    try:
                        assert self._finalization_store is not None  # fa_formal ctor 已强制
                        self._finalization_store.put_artifact_bodies(
                            frozen_patch=frozen_patch,
                            baseline_manifest=baseline_manifest,
                        )
                    except FinalizationStoreConflict as exc:
                        # B5 复核三轮 P1-3：同一 physical attempt 出现不同
                        # artifact = 身份复用/持久化事实矛盾——系统性错误，
                        # 不是该成员的样本损耗。绝不包装成 SlimeBindingError
                        # 缺员继续训练（那会把事实冲突伪装成 remove_sample）。
                        raise FatalExecutionInfrastructureError(
                            "finalization_store_conflict",
                            f"artifact immutable 违约：{exc}——身份/事实矛盾，"
                            "run-halt，不重试不补采。",
                        ) from exc
                    except Exception as exc:
                        raise SlimeBindingError(
                            "frozen_artifact_persist_failed",
                            f"artifact 本体持久化失败：{type(exc).__name__}: {exc}",
                        ) from exc
                    audit.mark("artifact_bodies_persisted")
                    # B3：hygiene 分类必须先于 grader（A-prime 第 5/7 条）。
                    # unsafe → present + 永久拒绝：不运行 grader、reward
                    # 不可得、abort 形状（训练面剔除）；准入 verdict 记
                    # audit（AdmissionReport 本体归 FA-2/F2-5）。
                    from repoharness2.contracts.scoring_projection import (
                        classify_frozen_patch,
                    )

                    from repoharness2.contracts.scoring_projection import (
                        ProjectionContractError,
                    )

                    try:
                        hygiene, projection = classify_frozen_patch(
                            frozen_patch, baseline_manifest
                        )
                    except ProjectionContractError as exc:
                        # B3 复核 P1-1：baseline/lineage 互检失败是**系统性
                        # 契约错误**（同进程内两份事实分家），不是该成员的
                        # 样本损耗——走 fatal/run-halt（worker 停机），不许
                        # 伪装成 capture_incomplete 缺员继续训练。
                        audit.failure_records.append(
                            RolloutFailureRecord(
                                stage="scoring_projection",
                                error_type=exc.reason_code,
                                detail=str(exc)[:500],
                            )
                        )
                        audit.mark("projection_contract_mismatch")
                        raise FatalExecutionInfrastructureError(
                            exc.reason_code,
                            f"projection 契约互检失败：{exc}——按 A-prime 失败表"
                            "run-halt，不得作为缺员继续。",
                        ) from exc
                    audit.runtime_private_pathset_changed = (
                        hygiene.runtime_private_pathset_changed
                    )
                    unsafe_reasons: list[str] = []
                    if hygiene.verdict == "unsafe_artifact":
                        unsafe_reasons = list(hygiene.reason_codes)
                    else:
                        # B4 P1-1（T0 失败表 unsafe 行逐字：不运行 grader、
                        # reward=None）：task 级 hygiene（测试文件/禁区
                        # 路径，规则与 grader 同一 HygieneRules 权威）在
                        # grader 之前判定，命中即 unsafe 永久拒绝。不做
                        # "剥掉违规 entry 评剩余 patch"——gate 对篡改事实
                        # 反正拒训（gate.py executed 级），评了只会污染
                        # reward/task_outcome/审计并白跑一次 grader。
                        from repoharness2.grading.manager import (
                            screen_frozen_entries,
                        )

                        plan = screen_frozen_entries(
                            list(frozen_patch.entries), grading_spec_for_attempt().hygiene
                        )
                        if plan.verdict != "clean":
                            unsafe_reasons = [
                                *(f"test_file_modified:{p}"
                                  for p in plan.stripped_test_paths),
                                *(f"forbidden_path_touched:{p}"
                                  for p in plan.forbidden_paths),
                            ]
                    if unsafe_reasons:
                        audit.unsafe_artifact_reasons = unsafe_reasons
                        audit.mark("unsafe_artifact_rejected")
                        self._produce_outcome_v2(
                            audit=audit,
                            raw_meta=raw_meta,
                            termination_kind="completed",
                            failure_category=None,
                            reason_code="unsafe_artifact_permanent_rejection",
                            failed_component="patch_hygiene",
                            task_resolved=None,  # 不评分 → reward 不可得
                            # present 事实的版本链取 capture 真值（A-prime
                            # unsafe 行 = present + 永久拒绝）
                            turn_weight_versions=hook_turn_weight_versions(hook),
                            current_version_at_finalize=(
                                self._current_policy_version_provider()
                                if self._current_policy_version_provider is not None
                                else self.config.policy_version
                            ),
                            eligibility_report_id=None,
                            extra_evidence=[
                                *barrier_evidence,
                                f"frozen_patch:{audit.frozen_patch_digest}",
                                *unsafe_reasons,
                            ],
                        )
                        # W1b 第二段（三终态 ③）：同上——present + 永久拒绝走真实交付
                        # + 载荷（无报告），filter 按契约封闭豁免集 DROP_GROUP。
                        return self._deliver_present_member(
                            task=task, raw_meta=raw_meta, samples=samples,
                            finalized=None, audit=audit,
                        )
                    audit.scoring_projection_entry_count = len(
                        projection.included_entry_paths
                    )
                    audit.mark("scoring_projection_built")
                    # B4：组装 grader 消费源（不读 workspace 的评分路径）
                    from repoharness2.grading.manager import FrozenDeltaSource

                    frozen_delta = FrozenDeltaSource(
                        frozen_patch=frozen_patch,
                        baseline_manifest=baseline_manifest,
                        projection=projection,
                        frozen_patch_digest=audit.frozen_patch_digest,
                    )
                elif isinstance(result, QuiescenceRejected):
                    self._produce_outcome_v2(
                        audit=audit,
                        raw_meta=raw_meta,
                        termination_kind="completed",
                        failure_category="runtime_quiescence_failure",
                        reason_code=result.reason_code,
                        failed_component="runtime_barrier",
                        extra_evidence=list(result.evidence_refs),
                        task_resolved=None,
                        turn_weight_versions=None,
                        current_version_at_finalize=None,
                        eligibility_report_id=None,
                    )
                    audit.mark("runtime_quiescence_failed")
                    return self._abort_result(
                        sample, reason="rh2_runtime_quiescence_failed",
                        task=task, top_p=tape_top_p, audit=audit,
                    )
                else:
                    audit.failure_records.append(
                        RolloutFailureRecord(
                            stage="runtime_barrier",
                            error_type="runtime_barrier_invalid_result",
                            detail=f"type={type(result).__name__}",
                        )
                    )
                    audit.mark("runtime_barrier_invalid_result")
                    raise FatalExecutionInfrastructureError(
                        "runtime_barrier_invalid_result",
                        f"屏障返回未知类型 {type(result).__name__}——封闭联合类型外的"
                        "结果按 D4 未知故障 run_halt。",
                    )

            stage = "finalize"
            handshake = self._build_handshake(trajectory_id, samples)
            audit.handshake = handshake
            finalized = await self._finalize(
                frozen_delta=frozen_delta,
                task=task,
                trajectory_id=trajectory_id,
                base_sample=sample,
                samples=samples,
                leaf_facts=leaf_facts,
                hook=hook,
                workspace=grading_workspace,  # 复核五轮 P0-1：正式链 = 冻结副本
                handshake=handshake,
                audit=audit,
                sampler_support_top_k=mask_top_k,  # B2：mask 链投影替换开关
                grading_spec=grading_spec_for_attempt(),
            )
            audit.finalized = finalized
            audit.step("step8_gate_finalized")

            # F2-2b ③：评分后复核冻结完整性——指纹漂移 = 评分读到过
            # 非冻结状态，评分结果作废，execution 按 missing 收口
            if self._mode == "fa_formal" and hasattr(
                grading_workspace, "verify_integrity"
            ):
                try:
                    snapshot_intact = await grading_workspace.verify_integrity()
                except Exception as exc:  # noqa: BLE001 - 复核通道自身故障 ≠ 完整性不匹配
                    # W1b 切片一复核（必修 1）分流：完整性复核**没有完成**（docker
                    # 通道 OSError 等）既不是"复核证伪"也不是 task-local 缺员——
                    # 评分产物已成、静止事实未被证伪也未被证实，是未知基建故障，
                    # 走 run-fatal 独立通道（与 P0-1 一致），不得洗成 missing/
                    # ABORTED 让 miles 当普通缺员丢弃后补采。
                    audit.failure_records.append(
                        RolloutFailureRecord(
                            stage="finalize",
                            error_type="integrity_recheck_failed",
                            detail=f"{type(exc).__name__}: {exc}"[:500],
                        )
                    )
                    audit.mark("integrity_recheck_failed")
                    raise FatalExecutionInfrastructureError(
                        "integrity_recheck_failed",
                        f"评分后冻结完整性复核无法完成：{type(exc).__name__}: {exc}"
                        "——既非证伪也非证实，按未知基建故障 run-halt。",
                    ) from exc
                if not snapshot_intact:
                    # 复核证伪静止事实（明确的完整性不匹配）：先撤销，completion
                    # 由事实推导 missing；评分产物一并作废（P1-1：missing 不得与
                    # disposition=finalized 并存——finalized 引用先清）。证据引用
                    # 先于 audit 改写取得：取值失败时 finalized 仍在场，通用
                    # except 会按 post-finalize 未分类故障升 fatal，而不是在
                    # "已清引用"的状态下被当成普通缺员。
                    snapshot_evidence = [f"snapshot:{grading_workspace.snapshot_ref}"]
                    audit.runtime_quiescence_confirmed = False
                    audit.finalized = None
                    self._produce_outcome_v2(
                        audit=audit,
                        raw_meta=raw_meta,
                        termination_kind="completed",
                        failure_category="runtime_quiescence_failure",
                        reason_code="snapshot_integrity_mismatch",
                        failed_component="runtime_barrier",
                        task_resolved=None,
                        turn_weight_versions=None,
                        current_version_at_finalize=None,
                        eligibility_report_id=None,
                        extra_evidence=snapshot_evidence,
                    )
                    audit.mark("snapshot_integrity_mismatch")
                    return self._abort_result(
                        sample, reason="rh2_snapshot_integrity_mismatch",
                        task=task, top_p=tape_top_p, audit=audit,
                    )

            # F2-2 producer（成功收口）：termination=completed；评分三态
            # 映射——resolved/unresolved 照实，failed_to_grade = 勘误 2 通道
            # （reward 不可得，completion 不倒写）。凭证 scrub：交付样本的
            # session_id 回写稳定键（capability 秘密不出执行期）。
            grading_outcome = finalized.grading_report.outcome
            if self._mode != "s1_compat":
                self._produce_outcome_v2(
                    audit=audit,
                    raw_meta=raw_meta,
                    termination_kind="completed",
                    failure_category=(
                        "grading_infra_failure" if grading_outcome == "failed_to_grade" else None
                    ),
                    reason_code=None,
                    failed_component=(
                        "grading_container" if grading_outcome == "failed_to_grade" else None
                    ),
                    task_resolved=(
                        None if grading_outcome == "failed_to_grade"
                        else grading_outcome == "resolved"
                    ),
                    turn_weight_versions=list(handshake.weight_versions_seen),
                    current_version_at_finalize=handshake.policy_version,
                    eligibility_report_id=finalized.eligibility_report.report_id,
                    extra_evidence=barrier_evidence,
                )
            stage = "deliver"
            return self._deliver(
                task=task,
                base_sample=sample,
                samples=samples,
                finalized=finalized,
                hook=hook,
                audit=audit,
                evaluation=evaluation,
                top_p=tape_top_p,
            )
        except asyncio.CancelledError:
            raise
        except FatalExecutionInfrastructureError as exc:
            # 复核六轮 P0-1（ownership 收敛项 1）：基建级致命错误走独立
            # 传播通道——绝不进 rollout 软失败收口。联合终核 P1-1：finally
            # 的异步 cleanup（drop_session/容器清理）会推迟异常到达
            # worker——在此**同步**经 task-local notifier 先置 halt，
            # cleanup 窗口内好组即被 collect_batch 拒绝交付。
            self._notify_fatal_halt(exc)
            raise
        # ---- W1b 第二段复核修复 #2：**结构契约类异常**显式提升为 run-fatal（白名单，
        # 不靠 isinstance 猜）。这些异常表示我方接线/事实矛盾，不是任务数据问题——
        # 经 stage fallback 洗成 missing/ABORTED 会被 miles 补采掩盖。
        except GateInputError as exc:
            # gate.py 明确定义：喂给 gate 的对象接错了线（别的轨迹/别的 lease 的事实）。
            raise self._structural_contract_fatal(
                audit, exc, stage=stage, reason_code="gate_wiring_error"
            ) from exc
        except AdmissionError as exc:
            # 交付面 admission 载荷派生/盖章矛盾（_deliver_present_member 内已各自包装，
            # 此处是防漏网的显式通道）。
            raise self._structural_contract_fatal(
                audit, exc, stage=stage, reason_code="admission_contract_error"
            ) from exc
        except ValidationError as exc:
            # finalize/gate/交付面内由**我方自己的事实**构造 RH2 契约对象失败 = 接线矛盾；
            # finalize 之前（materialize/harness_run/assemble）的 ValidationError 仍按
            # stage fallback 归 missing/ABORTED（不扩大 fatal 面）。
            if stage in _STRUCTURAL_CONTRACT_STAGES:
                raise self._structural_contract_fatal(
                    audit, exc, stage=stage, reason_code="rh2_contract_validation_failed"
                ) from exc
            return self._abort_after_task_local_exception(
                exc, stage=stage, audit=audit, raw_meta=raw_meta, sample=sample, task=task,
                tape_top_p=tape_top_p,
            )
        except Exception as exc:  # noqa: BLE001 - 收口为 abort，归因进 audit
            return self._abort_after_task_local_exception(
                exc, stage=stage, audit=audit, raw_meta=raw_meta, sample=sample, task=task,
                tape_top_p=tape_top_p,
            )
        finally:
            # ---- B5（A-prime 第 7 条）：cleanup 只许发生在 finalization
            # receipt 原子持久化**之后**。receipt 持久化失败 = T0 失败表
            # 第 2 行"durable handoff 失败"→ 保留 workspace/容器（不清理、
            # poison 不释放、容器进隔离队列）+ run halt（正常退出路径抛
            # Fatal；异常在途时只落账不掩盖首因异常）。s1/audit-only 未注入
            # store 时跳过 receipt（行为与 B5 前逐字一致）。
            in_flight = sys.exc_info()[1]
            await self._run_finally_section(
                audit=audit, sandbox=sandbox, sid=sid, adapter=adapter, session_open=session_open,
                in_flight=in_flight,
            )

    def _structural_contract_fatal(
        self, audit: "RolloutAudit", exc: BaseException, *, stage: str, reason_code: str
    ) -> FatalExecutionInfrastructureError:
        """结构契约类异常 → typed run-fatal（在 except 子句内：先记 failure_record、再同步
        通知 halt，返回 fatal 由调用方 raise）。不产 Outcome、不返回 ABORTED。"""

        audit.failure_records.append(
            RolloutFailureRecord(
                stage=stage,
                error_type=type(exc).__name__,
                detail=str(exc)[:500],
            )
        )
        audit.mark(reason_code)
        fatal = FatalExecutionInfrastructureError(
            reason_code,
            f"结构契约异常（stage={stage}，{type(exc).__name__}: {str(exc)[:200]}）——"
            "我方接线/事实矛盾不得洗成 ABORTED 让补采掩盖，run-halt。",
        )
        self._notify_fatal_halt(fatal)
        return fatal

    def _abort_after_task_local_exception(
        self,
        exc: BaseException,
        *,
        stage: str,
        audit: "RolloutAudit",
        raw_meta: Any,
        sample: Any,
        task: RolloutTaskSpec,
        tape_top_p: float | None,
    ) -> list[Any]:
        """通用异常收口（task-local 故障 → missing Outcome + abort 形状）；post-finalize
        未分类异常仍升 fatal（切片一复核 必修 1）。"""

        if True:  # 保持原缩进层级不变，便于与历史 diff 对照
            audit.failure_records.append(
                RolloutFailureRecord(
                    stage=stage,
                    error_type=type(exc).__name__,
                    detail=str(exc)[:500],
                )
            )
            # F2-2 producer（异常收口）：错误码映射表优先，未知码按失败
            # 阶段保守兜底（宁归 missing 不猜 present）；completion 仍由
            # audit 上的 quiescence/capture 事实推导，映射只供 termination
            # 与归因。
            code = getattr(exc, "reason_code", None)
            mapped = FAILURE_CODE_TERMINATION_MAP.get(code) if code else None
            if mapped is None:
                mapped = STAGE_FALLBACK_TERMINATION_MAP.get(
                    stage, ("harness_crash", "harness_crash")
                )
            term_kind, fail_cat = mapped
            if audit.finalized is not None:
                # W1b 切片一复核（必修 1）：成功 finalization（step8）之后的失败域
                # 已各自 typed 分流——verify_integrity 通道异常 / Outcome producer
                # 异常 / 核心 admission sidecar 写失败 → run-fatal；可选 telemetry
                # 写失败 → 记录后照常交付。还能走到通用 except 的 post-finalize
                # 异常 = 未分类故障，是不该到达的状态：升 fatal，**不**撤销
                # finalized、不产 missing Outcome、不返回 ABORTED（那会让 miles
                # 当普通缺员丢弃并补采，掩盖 Outcome schema/producer bug、docker
                # 完整性检查异常、核心 sidecar 磁盘失败这类系统性故障）。
                audit.mark("post_finalize_failure_unclassified")
                fatal = FatalExecutionInfrastructureError(
                    "post_finalize_failure_unclassified",
                    f"step8 之后出现未分类异常（stage={stage}，{type(exc).__name__}: "
                    f"{str(exc)[:200]}）——post-finalize 失败域不许洗成 ABORTED，run-halt。",
                )
                self._notify_fatal_halt(fatal)  # 已在 except 子句内，外层 Fatal 分支不再分派
                raise fatal from exc
            if self._mode != "s1_compat":
                try:
                    self._produce_outcome_v2(
                        audit=audit,
                        raw_meta=raw_meta,
                        termination_kind=term_kind,
                        failure_category=fail_cat,
                        reason_code=code or "unmapped_failure_code",
                        failed_component=stage,
                        task_resolved=None,
                        turn_weight_versions=None,
                        current_version_at_finalize=None,
                        eligibility_report_id=None,
                    )
                except FatalExecutionInfrastructureError as fatal:
                    # producer 异常已在守卫入口升 fatal；这里在 except 子句内，
                    # 外层 Fatal 分支不会再次分派——手动通知 halt 后传播。
                    self._notify_fatal_halt(fatal)
                    raise
            try:
                return self._abort_result(
                    sample, reason=f"rh2_{stage}_failed:{type(exc).__name__}", task=task, top_p=tape_top_p,
                    audit=audit,
                )
            except FatalExecutionInfrastructureError as fatal:
                # present 成员被压成 abort 形状 = 交付面接线矛盾（在 except 子句内，手动通知 halt）
                self._notify_fatal_halt(fatal)
                raise

    async def _run_finally_section(
        self,
        *,
        audit: "RolloutAudit",
        sandbox: Any,
        sid: str,
        adapter: Any,
        session_open: bool,
        in_flight: BaseException | None,
    ) -> None:
        """`_generate_attempt` 的 finally 段本体（B5 receipt → F5 事实派生 → cleanup → 追加记录
        → audit sink → 尾部 run-halt 判定）。逐字搬自原 finally 段，只为让 except 链可以拆成显式
        分支而不复制这 200 行；语义零改变。"""

        receipt: FinalizationReceiptV1 | None = None
        receipt_persist_failed = False
        if self._finalization_store is not None:
            try:
                # B5 复核 P1-5：构造也在失败通道内——typed outcome_v2
                # 嵌入会复跑全量不变量，构造失败同样是 durable handoff
                # 失败，不许从 finally 裸逃（掩盖首因）。
                receipt = build_finalization_receipt(
                    audit,
                    in_flight_exception=in_flight,
                    artifact_bodies_persisted=(
                        "artifact_bodies_persisted" in audit.steps
                        or any(
                            e.step == "artifact_bodies_persisted"
                            for e in audit.timeline
                        )
                    ),
                )
                self._finalization_store.persist_receipt(receipt)
                audit.mark("finalization_receipt_persisted")
            except Exception as exc:  # noqa: BLE001 —— 分路处置，绝不静默
                receipt_persist_failed = True
                audit.failure_records.append(
                    RolloutFailureRecord(
                        stage="finalization_receipt",
                        error_type="finalization_receipt_write_failed",
                        detail=f"{type(exc).__name__}: {exc}"[:500],
                    )
                )
                audit.cleanup_failures.append(
                    CleanupFailureRecord(
                        lease_id=(
                            sandbox.lease.lease_id if sandbox else f"lease_{sid}"
                        ),
                        step="finalization_receipt_write_failed",
                        detail=f"{type(exc).__name__}: {exc}"[:300],
                    )
                )
                if sandbox is not None:
                    self.cleanup_quarantine.append(sandbox.container_name)
                audit.mark("finalization_receipt_write_failed")
        # W1b 第一集成切片（F5 producer）：receipt 持久化成功后立刻派生
        # termination 事实载荷（只读派生，fail-closed）。只对形成了 Outcome
        # v2 的 attempt 派生——没有 Outcome 的 attempt（s1 兼容/身份不全的
        # 结构化拒绝）没有 termination 权威，如实记跳过，不伪造事实。派生
        # 失败 = receipt 与 outcome 账实矛盾：异常在途时只记 secondary
        # fact，否则在 finally 末尾 run-halt（与 receipt 写失败同纪律）。
        termination_facts_failed = False
        if receipt is not None and not receipt_persist_failed:
            if audit.outcome_v2 is None:
                audit.mark("termination_facts_skipped_no_outcome")
            else:
                try:
                    audit.termination_facts_payload = termination_facts_payload(receipt)
                    audit.mark("termination_facts_derived")
                except TerminationFactsError as exc:
                    termination_facts_failed = True
                    audit.failure_records.append(
                        RolloutFailureRecord(
                            stage="finalization_receipt",
                            error_type="termination_facts_underivable",
                            detail=f"{type(exc).__name__}: {exc}"[:500],
                        )
                    )
                    audit.mark("termination_facts_underivable")
        cleanup_exception = False
        cleanup_skipped = receipt_persist_failed and self._mode != "s1_compat"
        if cleanup_skipped:
            # 保留现场：session 不 drop、容器不清、poison 不释放
            # （s1_compat 容忍档与 audit sink 同口径：落账后照常清理）。
            # B5 复核 P1-4：跳过就如实标注跳过——不写
            # cleanup_started/cleanup_completed 假事件。
            audit.mark("cleanup_skipped_receipt_failure")
        else:
            audit.mark("cleanup_started")
            if session_open:
                try:
                    await adapter.drop_session(sid, wait_timeout=5.0)
                except Exception as exc:  # noqa: BLE001 - 清理失败必须留痕（Q8）
                    audit.cleanup_failures.append(
                        CleanupFailureRecord(
                            lease_id=sandbox.lease.lease_id if sandbox else f"lease_{sid}",
                            step="drop_session",
                            detail=str(exc)[:300],
                        )
                    )
            if sandbox is not None:
                try:
                    await self._cleanup_container(sandbox.lease, sandbox.container_name, audit)
                except Exception as exc:  # noqa: BLE001 - 轮次 12 一般 1：不许无账
                    # docker socket OSError 等意外异常：结构化落账 + 隔离队列，
                    # 不让清理异常覆盖 rollout 结果
                    cleanup_exception = True
                    audit.cleanup_failures.append(
                        CleanupFailureRecord(
                            lease_id=sandbox.lease.lease_id,
                            step="container_cleanup_exception",
                            detail=f"{type(exc).__name__}: {exc}"[:300],
                        )
                    )
                    self.cleanup_quarantine.append(sandbox.container_name)
        if not cleanup_skipped:
            audit.mark("cleanup_completed")
        poison_released = False
        if (
            receipt_persist_failed
            or cleanup_exception
            or (audit.cleanup_failures and not audit.lease_released)
        ):
            # 清理未确认成功：poison **不释放**（active 保持拒绝力），
            # 容器进隔离队列等重试/人工——release 只在清理确认后发生
            pass
        elif self._session_poison_release is not None:
            # 真正的 execution 清理 ACK：harness 终止 + 会话撤销 + 容器
            # 清理都已完成，active poison 此刻才允许归档（轮次 11）
            self._session_poison_release(sid)
            poison_released = True
        if (
            self._finalization_store is not None
            and receipt is not None
            and not receipt_persist_failed
        ):
            # B5：cleanup 结果**追加**（独立记录，永不改写 receipt——
            # "cleanup failure 附加不覆盖首因"）。receipt 没落盘就没有
            # 追加对象（悬空 cleanup 记录禁止）。追加自身失败只落账。
            try:
                self._finalization_store.append_cleanup_result(
                    CleanupResultAppendV1(
                        receipt_id=receipt.receipt_id,
                        cleanup_failures=[
                            CleanupFailureFact(
                                lease_id=f.lease_id, step=f.step, detail=f.detail
                            )
                            for f in audit.cleanup_failures
                        ],
                        quarantined_container=(
                            sandbox.container_name
                            if sandbox is not None
                            and sandbox.container_name in self.cleanup_quarantine
                            else None
                        ),
                        lease_released=audit.lease_released,
                        poison_released=poison_released,
                        completed_at_utc=_now_utc(),
                    )
                )
            except Exception as exc:  # noqa: BLE001 —— 追加失败不掩盖首因
                audit.cleanup_failures.append(
                    CleanupFailureRecord(
                        lease_id=(
                            sandbox.lease.lease_id if sandbox else f"lease_{sid}"
                        ),
                        step="cleanup_result_append_failed",
                        detail=f"{type(exc).__name__}: {exc}"[:300],
                    )
                )
        if self._audit_sink is not None:
            try:
                self._audit_sink(audit)
            except Exception as exc:  # noqa: BLE001 —— 分链路处置
                if (
                    receipt_persist_failed and self._mode != "s1_compat"
                ) or in_flight is not None:
                    # B5 复核 P1-4 + 三轮 P1-2：**首因优先**——receipt
                    # 失败在前、或任何 Fatal/取消在途时，sink 失败只记
                    # secondary fact；从 finally 抛新异常会**替换**在途
                    # 异常，把 barrier fatal 等首因顶掉成
                    # execution_audit_write_failed。
                    audit.failure_records.append(
                        RolloutFailureRecord(
                            stage="finalization_receipt",
                            error_type="audit_sink_failed_secondary",
                            detail=f"{type(exc).__name__}: {exc}"[:500],
                        )
                    )
                elif self._mode != "s1_compat" or self.config.require_real_weight_versions:
                    # 轮次 14 仍需修正 3：裸 raise 会被 worker 当普通成员
                    # 失败（failure_sink 成功就继续 top-up）——包装成基建
                    # 级致命错误，worker 据此停机（真 run-halt）
                    raise FatalExecutionInfrastructureError(
                        "execution_audit_write_failed",
                        f"审计存储不可用：{type(exc).__name__}: {exc}——"
                        "继续 top-up 只会积累无审计依据的 rollout。",
                    ) from exc
                else:
                    print(f"[rh2] audit sink 落盘失败（bring-up 容忍）：{exc}")
        if receipt_persist_failed and self._mode != "s1_compat" and in_flight is None:
            # B5（T0 失败表第 2 行）：durable handoff 失败 → run halt
            # （worker 停机）。现场已保留（上方跳过 cleanup + 隔离队列）。
            # 异常在途时不抛——不许掩盖首因，Fatal/取消按原样传播，
            # receipt 缺失由 F2-4 恢复端按"未终局"fail-closed 处理。
            raise FatalExecutionInfrastructureError(
                "finalization_receipt_write_failed",
                "finalization receipt 持久化失败——workspace 已保留、"
                "容器入隔离队列；继续 top-up 会产生无终局记录的 attempt。",
            )
        if termination_facts_failed and in_flight is None:
            # F5：receipt 已 durable，但其 outcome/引用账实矛盾到无法派生
            # 事实——继续 top-up 会积累无法 join 的 attempt。首因优先：
            # 异常在途时上方只记 secondary fact，不在此覆盖。
            raise FatalExecutionInfrastructureError(
                "termination_facts_underivable",
                "finalization receipt 与 outcome 的引用账实矛盾，termination 事实"
                "无法派生——receipt 已持久化，run-halt 待人工核对。",
            )

    # ------------------------------------------------------------------ 步骤 2
    def _default_mount_planner(self, task: RolloutTaskSpec) -> list[BundleMount]:
        """Q6 默认挂载计划：rollout 容器只挂 public bundle。"""

        return [
            BundleMount(
                bundle_kind="public_task_bundle",
                bundle_digest=task.public_bundle_digest,
                mount_path=PUBLIC_BUNDLE_CONTAINER_PATH,
            )
        ]

    async def _materialize_rollout_sandbox(
        self, task: RolloutTaskSpec, trajectory_id: str, audit: RolloutAudit
    ) -> _MaterializedSandbox:
        """步骤 2：起 rollout 容器（租约先行）+ envpack 血缘校验 + bundle 写入。"""

        nonce = uuid.uuid4().hex[:8]
        name = f"{self.config.name_prefix}-{_sanitize_for_name(trajectory_id)}-{nonce}"

        image_id = await self._docker("image", "inspect", "-f", "{{.Id}}", task.image)
        if image_id.exit_code != 0:
            raise SlimeBindingError(
                "rollout_image_inspect_failed",
                f"rollout 镜像 {task.image} 不可用：{image_id.stderr.strip()[-300:]}",
            )

        # 租约先行（与 S1-4 评分容器同纪律）：docker 参数从租约推导，A5 Q1/Q5/Q7/Q8。
        lease = SandboxLease(
            lease_id=f"lease_{name}",
            container_id=name,
            image_digest=image_id.stdout.strip(),
            purpose="rollout",
            created_by="slime_adapter",  # Q1
            network_policy_owner="slime_adapter",  # Q5a
            network_policy="allowlist",  # rollout 必须能反连模型代理端点
            network_allowlist_justification=self.config.network_allowlist_justification,
            permission_policy_owner="slime_adapter",  # Q5b
            run_as_user="root",  # S0 现状；harness 进程内降权归 slime ensure_agent_user
            cleanup=CleanupPolicy(  # Q7/Q8
                owner="slime_adapter",
                steps=["remove_container", "release_lease"],
                on_cleanup_failure="record_runtime_finding_and_infra_failure",
                timeout_seconds=self.config.cleanup_timeout_seconds,
            ),
            created_at_utc=_now_utc(),
        )
        audit.lease = lease
        network_args = {"deny_all": ("--network", "none"), "allowlist": ("--network", "bridge")}[
            lease.network_policy
        ]
        prefix = self.config.label_prefix
        # 本 run owner label（miles GPU spike shutdown 探针的精确归属锚点）：
        # launch.sh 经 Ray runtime env 下发 MILES_RH2_RUN_ID，探针用
        # `--filter label=rh2.run_id=<run_id>` 找本 run 遗留容器；env 未设
        # （单测/非 spike 链）时不加 label，docker 参数保持原样。
        run_id_labels: tuple[str, ...] = ()
        if run_id := os.environ.get("MILES_RH2_RUN_ID"):
            run_id_labels = ("--label", f"rh2.run_id={run_id}")
        run = await self._docker(
            "run",
            "--detach",
            *network_args,
            "--label",
            f"{prefix}.trajectory={trajectory_id}",
            "--label",
            f"{prefix}.created_at_epoch={int(_now_utc().timestamp())}",
            *run_id_labels,
            "--name",
            name,
            task.image,
            "sleep",
            "infinity",
        )
        if run.exit_code != 0:
            raise SlimeBindingError(
                "rollout_container_start_failed",
                f"rollout 容器启动失败：{run.stderr.strip()[-300:]}",
            )

        try:
            # 启动后镜像 digest 比对（codex#1 fail-closed）：先于任何写入/探针，
            # 漂移镜像上的 rollout 一步都不该跑。失败走本 try 的清理路径
            # （容器已起必须清，Q7），异常在 generate() 收口为 infra_failure。
            await self._verify_rollout_image_digest(task, name)

            # Q2：/testbed 物化校验——脚本与判据全部来自 envpack（库层所有权），
            # 编排只是执行通道（materialize.py 模块 docstring 的分工原文）。
            probe = await self._docker(
                "exec", name, "bash", "-c", materialize.build_probe_script(task.base_commit)
            )
            check = materialize.evaluate_probe(
                task.base_commit, probe.exit_code, probe.stdout, probe.stderr
            )
            if not check.ok:
                raise SlimeBindingError(
                    "rollout_testbed_lineage_failed", check.failure_message()[:500]
                )

            # 基线未跟踪清单（S1-7a 远程回归发现）：部分官方镜像 /testbed 自带
            # 未跟踪构建残留（实测 psf__requests-1142 的 build/lib/**），必须在
            # harness 动工前存证，评分导出（EXPORT_PATCH_SCRIPT）按清单排除，
            # 否则 patch 掺入非 agent 产物且重放必失败（already exists）。
            snapshot = await self._docker(
                "exec",
                name,
                "bash",
                "-c",
                f"cd {task.workdir} && "
                + BASE_UNTRACKED_SNAPSHOT_SCRIPT.format(manifest=BASE_UNTRACKED_MANIFEST),
            )
            if snapshot.exit_code != 0:
                raise SlimeBindingError(
                    "rollout_base_untracked_snapshot_failed",
                    f"基线未跟踪清单生成失败：{snapshot.stderr.strip()[-300:]}",
                )

            for path, payload, what in (
                (PUBLIC_BUNDLE_CONTAINER_PATH, task.public_bundle_payload, "public bundle"),
                (materialize.BASH_ENV_PATH, materialize.BASH_ENV_CONTENT.encode(), "bash env"),
            ):
                write = await self._docker(
                    "exec",
                    "-i",
                    name,
                    "bash",
                    "-c",
                    f"mkdir -p $(dirname {path}) && cat > {path}",
                    input_bytes=payload,
                )
                if write.exit_code != 0:
                    raise SlimeBindingError(
                        "rollout_workspace_write_failed",
                        f"{what} 写入失败：{write.stderr.strip()[-300:]}",
                    )

            handle = WorkspaceHandle(  # Q2/Q6（private 挂载在此被 schema 拒绝）
                workspace_id=f"ws_{name}",
                lease_id=lease.lease_id,
                role="rollout_workspace",
                testbed_path=task.workdir,
                materialized_by="repoharness_envpack",
                base_commit=task.base_commit,
                head_commit=check.head,
                lineage_check=(
                    "head_equals_base"
                    if check.head == task.base_commit
                    else "head_parent_equals_base"
                ),
                mounted_bundles=self._mount_planner(task),
                materialized_at_utc=_now_utc(),
            )
        except Exception:
            # 物化中途失败：容器已存在，立即按 Q7 清理（外层 finally 不再重复——
            # sandbox 尚未返回给调用方，这里是唯一知道容器名的位置）。
            await self._cleanup_container(lease, name, audit)
            raise
        audit.workspace_handle = handle
        workspace = RolloutContainerWorkspace(
            docker=self._docker, container_name=name, testbed_path=task.workdir
        )
        return _MaterializedSandbox(
            container_name=name, lease=lease, handle=handle, workspace=workspace
        )

    async def _verify_rollout_image_digest(self, task: RolloutTaskSpec, name: str) -> None:
        """启动后镜像 digest 比对（codex#1，与评分容器同判据）：容器实际运行的
        镜像（`docker inspect -f {{.Image}}`，非 spec 标签——封住 :latest 在
        inspect 与 run 之间被重指的窗口）的 RepoDigests 必须命中 envpack 冻结的
        image_manifest_digest。本地构建镜像走 task.image_local_build 显式豁免；
        无豁免且 RepoDigests 为空一律拒绝（evaluate_image_digest 的 fail-closed）。
        """

        if task.image_local_build:
            return  # 显式豁免（RolloutTaskSpec.__post_init__ 强制二选一声明）
        expected = task.image_manifest_digest
        assert expected is not None  # __post_init__ 的二选一保证
        ref = await self._docker("inspect", "-f", "{{.Image}}", name)
        if ref.exit_code != 0:
            raise SlimeBindingError(
                "rollout_image_ref_inspect_failed",
                f"容器实际镜像查询失败：{ref.stderr.strip()[-300:]}",
            )
        digests = await self._docker(
            "image", "inspect", "-f", materialize.IMAGE_REPO_DIGESTS_FORMAT, ref.stdout.strip()
        )
        check = materialize.evaluate_image_digest(
            expected, digests.exit_code, digests.stdout, digests.stderr
        )
        if not check.ok:
            raise SlimeBindingError(
                "rollout_image_digest_mismatch", check.failure_message()[:500]
            )

    # ------------------------------------------------------------------ 步骤 6~8
    def _reward_input(
        self, report: GradingReport, base_sample: Any, task: RolloutTaskSpec
    ) -> SlimeRewardInput:
        """GradingReport -> RewardFacts 原料（gate 将逐值对账，禁止转述）。"""

        group_index = getattr(base_sample, "group_index", None)
        group_id = (
            f"group_{task.task_id}_g{group_index}" if group_index is not None else None
        )
        parent_rollout_id = (
            f"rollout_{task.task_id}_g{group_index}" if group_index is not None else None
        )
        if report.reward is None:  # infra 族：reward 事实必须如实为 none/None（P4 红线）
            return SlimeRewardInput(
                reward_scope="none",
                raw_reward=None,
                reward_event_refs=[report.report_id],
                credit_assignment_strategy="direct_trace_reward",
                group_id=group_id,
                parent_rollout_id=parent_rollout_id,
            )
        return SlimeRewardInput(
            reward_scope="group_level" if group_id is not None else "trace_level",
            raw_reward=report.reward,
            reward_event_refs=[report.report_id],
            credit_assignment_strategy=(
                "backend_group_normalized" if group_id is not None else "direct_trace_reward"
            ),
            group_id=group_id,
            parent_rollout_id=parent_rollout_id,
        )

    def _build_handshake(
        self, trajectory_id: str, samples: Sequence[Any]
    ) -> BackendHandshake | None:
        if self._handshake_builder is not None:
            return self._handshake_builder(trajectory_id, samples)
        if self.config.policy_version is None:
            return None  # 显式无事实：gate 的 policy_staleness 维将 fail-closed 降级
        seen: list[str] = []
        for leaf in samples:
            for version in getattr(leaf, "weight_versions", None) or []:
                if version not in seen:
                    seen.append(version)
        # FA-0：正式链的 staleness 按版本差计算——current（finalize 时刻，
        # provider 实测值优先，缺省回退 config.policy_version）减去 seen 中
        # 最旧版本。事实矛盾（任何 seen 版本比 current 新）fail-closed，
        # 绝不 clamp 成 0 伪装健康（codex FA-0 审查严重 1 的反例）。
        # S1 兼容路径（flag=False）保持恒 0 语义逐字不变。
        current_version = (
            self._current_policy_version_provider()
            if self._current_policy_version_provider is not None
            else self.config.policy_version
        )
        staleness_steps = 0
        if self.config.require_real_weight_versions:
            try:
                current = int(current_version, 10)
                seen_numeric = [int(v, 10) for v in seen] or [current]
            except (TypeError, ValueError):
                raise SlimeBindingError(
                    "weight_versions_not_numeric_in_formal_chain",
                    f"正式链要求数值版本：current={current_version!r}, "
                    f"seen={seen!r}——staleness 无法派生，fail-closed。",
                ) from None
            if max(seen_numeric) > current:
                raise SlimeBindingError(
                    "weight_version_ahead_of_current",
                    f"事实矛盾：seen 含比 current({current}) 更新的版本 "
                    f"{max(seen_numeric)}——current 版本事实过期或版本管道错乱，"
                    "fail-closed（不得 clamp 成 staleness=0 伪装健康）。",
                )
            staleness_steps = current - min(seen_numeric)
        # D1-4：finalize-time 阈值只定参数化接口——非 s1 模式必须显式配置（fa_formal 已在
        # 启动校验拒绝缺失；此处是握手构造时刻的第二道 fail-fast），s1_compat 冻结路径
        # 回退 S1 历史值。禁止在此处发明任何"默认 4"。
        threshold = self.config.staleness_threshold
        if threshold is None:
            if self._mode != "s1_compat":
                raise FatalExecutionInfrastructureError(
                    "staleness_threshold_unconfigured",
                    f"execution_mode={self._mode} 的握手构造缺显式 staleness_threshold——"
                    "finalize-time staleness 判定无阈值可依，run-halt（数值归决策包 B）。",
                )
            threshold = S1_COMPAT_LEGACY_STALENESS_THRESHOLD
        return BackendHandshake(
            handshake_id=f"hs_{trajectory_id}",
            trajectory_id=trajectory_id,
            backend_name="slime",
            policy_version=current_version,
            weight_versions_seen=seen or [current_version],
            staleness_steps=staleness_steps,
            staleness_threshold=threshold,
            staleness_within_threshold=staleness_steps <= threshold,
            group_signal=None,
            accepted=True,
            handshaked_at_utc=_now_utc(),
        )

    async def _drain_session_plane_owned(
        self, sid: str, physical_attempt_id: str | None
    ):
        """F2-3 批 2a：单 owner drain 的消费半区（codex 批 2 首验收分层）。

        契约违约族（owner 缺注入/抛异常/返回非 typed/paid 矛盾）=
        FatalExecutionInfrastructureError → WorkerHalted——内部事实源损坏
        绝不降级成缺员伪装 batch_starved；类型正确但事实不干净 =
        session_plane_drain_unclean（成员级收口，不冒充干净）。返回已验证
        的 clean SessionPlaneDrainResult。"""

        from repoharness2.adapters.slime.capture_wire import SessionPlaneDrainResult

        if self._session_drain_owner is None:
            raise FatalExecutionInfrastructureError(
                "session_drain_owner_missing",
                "正式链未注入 session_drain_owner——drain 所有权缺席"
                "是部署级契约损坏，run-halt。",
            )
        try:
            drain_result = await self._session_drain_owner(sid)
        except Exception as exc:
            raise FatalExecutionInfrastructureError(
                "session_drain_owner_failed",
                f"drain owner 异常：{type(exc).__name__}: {exc}",
            ) from exc
        if not isinstance(drain_result, SessionPlaneDrainResult):
            raise FatalExecutionInfrastructureError(
                "session_drain_owner_contract_violation",
                f"drain owner 返回 {type(drain_result).__name__}，"
                "非 SessionPlaneDrainResult。",
            )
        if drain_result.physical_attempt_id != physical_attempt_id:
            raise FatalExecutionInfrastructureError(
                "session_drain_attempt_mismatch",
                f"drain owner 身份 {drain_result.physical_attempt_id!r} "
                f"!= audit 身份 {physical_attempt_id!r}——两份事实分家。",
            )
        if not (
            drain_result.revoke_enforced
            and drain_result.inflight_zero_confirmed
            and drain_result.pending_turns == 0
            and drain_result.unfinalized_drafts == 0
            and drain_result.poison_clean
        ):
            raise SlimeBindingError(
                "session_plane_drain_unclean",
                "drain 未达干净态："
                f"revoke={drain_result.revoke_enforced} "
                f"inflight_zero={drain_result.inflight_zero_confirmed} "
                f"pending={drain_result.pending_turns} "
                f"drafts={drain_result.unfinalized_drafts} "
                f"poison_clean={drain_result.poison_clean}",
            )
        return drain_result

    async def _finalize(
        self,
        *,
        frozen_delta=None,
        task: RolloutTaskSpec,
        trajectory_id: str,
        base_sample: Any,
        samples: Sequence[Any],
        leaf_facts: Sequence[LeafFacts],
        hook: GenerationCaptureHook,
        workspace: RolloutContainerWorkspace,
        handshake: BackendHandshake | None,
        audit: RolloutAudit,
        sampler_support_top_k: Any | None = None,
        grading_spec: GradingEnvSpec,
    ) -> FinalizedRollout:
        """步骤 6~8：只准调 finalize_rollout（治理层唯一关口，顺序已被 wrapper 固化）。

        ``grading_spec``（W1b 第一集成切片）：本次 attempt 的评分材料，由调用方经
        `_grading_spec_for` 取得（prepared 链 = attempt 绑定查找；legacy = 任务面内嵌）。

        ``sampler_support_top_k``（B2，R6-ext）：非 None = 本次 generate 走
        miles sampling-mask 链路（generate() 按 args.rh2_engine_sampling_mask
        且 top_p<1.0 传入采样配方 top_k），投影产出经
        project_group_with_sampler_support 替换成 sampler_support_token_ids
        事实；None = 旧 top-p tape 投影分支逐字不变。
        """

        annotations = [
            SlimeBranchAnnotation(
                branch_id=facts.branch_id,
                capture_record_ids=list(facts.capture_record_ids),
                lineage=facts.lineage,
                context_runs=list(facts.context_runs),
            )
            for facts in leaf_facts
        ]

        async def _grade() -> GradingReport:
            from repoharness2.grading.manager import BaselineIntegrityError

            audit.mark("grading_started")
            try:
                report = await self._grading_submit(
                    trajectory_id=trajectory_id,
                    # B4：frozen_delta 在场时 grader 不读 workspace（传 None，
                    # 契约级保证"不回读 rollout workspace"）
                    workspace=None if frozen_delta is not None else workspace,
                    spec=grading_spec,
                    **({"frozen_delta": frozen_delta} if frozen_delta is not None else {}),
                )
            except BaselineIntegrityError as exc:
                # B4 P0-1：exact-baseline 重建/绑定矛盾 = grader 看到的树
                # ≠ 模型开工时的树（或同进程事实分家）——系统性契约错误，
                # 与 B3 ProjectionContractError 同通道 run-halt，不许转
                # failed_to_grade 当成员损耗继续训练。
                audit.failure_records.append(
                    RolloutFailureRecord(
                        stage="grading_baseline_verify",
                        error_type=exc.reason_code,
                        detail=str(exc)[:500],
                    )
                )
                audit.mark("grading_baseline_integrity_mismatch")
                raise FatalExecutionInfrastructureError(
                    exc.reason_code,
                    f"exact-baseline 校验失败：{exc}——按 A-prime 失败表 "
                    "run-halt，不得作为成员损耗继续。",
                ) from exc
            audit.step("step6_grading_completed")
            return report

        def _project(report: GradingReport):
            audit.mark("projection_started")

            def _run_projection():
                return project_from_slime(
                    list(samples),
                    hook.records,
                    task_id=task.task_id,
                    annotations=annotations,
                    reward=self._reward_input(report, base_sample, task),
                    serving_precision=self.config.serving_precision,
                    serving_sampling_backend=self.config.serving_sampling_backend,
                    expected_renderer_cls_name=self.config.expected_renderer_cls_name,  # U-G
                    declared_segment_count=len(annotations),
                    moe_num_layers=self.config.moe_num_layers,
                    moe_router_topk=self.config.moe_router_topk,
                    artifact_store=hook.artifact_store,
                )

            if sampler_support_top_k is not None:
                # B2（R6-ext）：mask 链路的投影接线放 miles 侧（projection.py
                # 是冻结面）——helper 复用冻结面的结构校验后，把分支级
                # SamplingMaskRef/LogprobProvenance 替换成
                # sampler_support_token_ids + behavior_support_normalized
                # 事实（T0-B），再整树重校验。lazy import 同 capture_wire
                # 口径（无 miles 环境的旧测试面不加载 adapters.miles）。
                from repoharness2.adapters.miles.projection_ext import (
                    project_group_with_sampler_support,
                )

                projection = project_group_with_sampler_support(
                    _run_projection,
                    list(samples),
                    top_k=sampler_support_top_k,
                    store=hook.artifact_store,
                )
            else:
                projection = _run_projection()
            audit.step("step7_projection_completed")
            return projection

        # A3（W1b 第二段）：security 维要求正向 sandbox 能力事实。非 s1 模式一律要求
        # （provider 缺席/返回 None → `sandbox_capability_facts_missing` → 非 online，
        # W3b 落地前的预期形态）；s1_compat 冻结路径显式声明不要求（evidence 记 not_required）。
        capability_facts: SandboxCapabilityFacts | None = None
        if self._mode != "s1_compat" and self._sandbox_capability_facts_provider is not None:
            capability_facts = self._sandbox_capability_facts_provider(audit)
        # 复核修复 #5：显式传入本次 attempt 实际使用的 SandboxLease.lease_id（materialize 时挂在
        # audit.lease 上的那份租约，不猜）——gate 要求能力事实的 lease_id 逐字相等，旧容器的
        # 能力事实不能认证同一 trajectory 的新容器。
        return await finalize_rollout(
            grade=_grade,
            project=_project,
            capture_records=hook.records,
            handshake=handshake,
            findings=(),
            backpressure_events=list(self._backpressure_events_source()),
            sandbox_capability_facts=capability_facts,
            sandbox_capability_facts_required=self._mode != "s1_compat",
            sandbox_lease_id=audit.lease.lease_id if audit.lease is not None else None,
        )

    # ------------------------------------------------------------------ 步骤 9
    def _deliver(
        self,
        *,
        task: RolloutTaskSpec,
        base_sample: Any,
        samples: Sequence[Any],
        finalized: FinalizedRollout,
        hook: GenerationCaptureHook,
        audit: RolloutAudit,
        evaluation: bool,
        top_p: float | None = None,
    ) -> list[Any]:
        """步骤 9：先透传组修复信号（P4：组装配前可见），再决定交付或剔除。"""

        signal = finalized.group_repair_signal
        forwarded = True
        if self._repair_signal_sink is not None:
            try:
                self._repair_signal_sink(signal)
            except Exception as exc:  # noqa: BLE001 - 可选 telemetry：记录后继续
                # W1b 切片一复核（必修 1）分流：组修复信号的转发通道在 miles 路径
                # 没有生产消费者（组准入由第二段 filter 按交付面 typed 载荷判定；
                # FA-2 assembler 按 06 §2 不做），属可选 telemetry——写失败只记
                # failure_record，样本处置不变（不得把样本改写成 ABORTED）。
                forwarded = False
                audit.failure_records.append(
                    RolloutFailureRecord(
                        stage="deliver",
                        error_type="repair_signal_sink_failed",
                        detail=f"{type(exc).__name__}: {exc}"[:500],
                    )
                )
                audit.mark("repair_signal_sink_failed")
        audit.repair_signal_forwarded = forwarded
        try:
            self._write_artifacts(audit, hook, finalized)
        except Exception as exc:  # noqa: BLE001 - 核心 admission 记录写失败 = run-fatal
            # A4 run-fatal 面：eligibility/grading report、projection、capture 记录
            # 与 tape 是核心 admission record 及其引用——持久化失败时样本不交付
            # + run-halt（finally 的 cleanup 仍照常执行），不得当成员损耗继续。
            audit.failure_records.append(
                RolloutFailureRecord(
                    stage="deliver",
                    error_type="admission_artifact_write_failed",
                    detail=f"{type(exc).__name__}: {exc}"[:500],
                )
            )
            audit.mark("admission_artifact_write_failed")
            raise FatalExecutionInfrastructureError(
                "admission_artifact_write_failed",
                f"核心 admission sidecar 写失败：{type(exc).__name__}: {exc}——样本不交付，run-halt。",
            ) from exc

        report = finalized.eligibility_report
        if signal.degraded and self._mode == "s1_compat":
            # s1_compat 冻结路径（slime FA 回退面 / miles GPU spike bring-up，无组级准入
            # 消费者）：降级样本仍以 slime abort 形状剔除，行为逐字不变。
            audit.step("step9_degraded_signal_forwarded")
            return self._abort_result(
                base_sample, reason="rh2_gate_degraded", task=task, report=report, top_p=top_p
            )

        grading_reward = finalized.grading_report.reward
        if evaluation:
            # 评测模式（E10 主评测面 = 训练同链路 eval 模式）：slime eval 只消费
            # reward，样本按 slime 例程的 eval 占位形状返回（remove_sample=True）。
            base_sample.tokens = [0, 0]
            base_sample.response = ""
            base_sample.response_length = 1
            base_sample.loss_mask = [0]
            base_sample.rollout_log_probs = [0.0]
            if top_p is not None and top_p < 1.0:
                # 与 _abort_result 同理：top-p 训练配置下占位样本也必须带零宽 tape。
                base_sample.rollout_top_p_token_ids = []
                base_sample.rollout_top_p_token_offsets = [0, 0]
            base_sample.reward = float(grading_reward or 0.0)
            base_sample.remove_sample = True
            _set_status(base_sample, "completed")
            base_sample.metadata = {
                **(getattr(base_sample, "metadata", None) or {}),
                "instance_id": task.task_id,
                "eligibility_report_ref": report.derived_view_report_ref,
                "training_eligibility_class": report.derived_view_class,
            }
            audit.delivered_sample_count = 1
            audit.step("step9_samples_delivered")
            return [base_sample]

        if self._mode != "s1_compat":
            # W1b 第二段（三终态 ③，D1 已批）：完整 finalize 的成员——七维全过或任一维
            # 不合格——**一律真实交付**（token/mask/logprob/provenance 真实，remove_sample=False）
            # 并携带 typed admission 载荷；准入由 miles 复合 group filter 按 A2 全员合取
            # 整组裁决（不合格 → keep=False 固定丢弃）。degraded 不再压成 abort 形状：
            # 那会让 filter 永远看不到这些组，把 failed_to_grade 等 present 事实改写成 ABORTED。
            raw_meta = getattr(base_sample, "metadata", None)
            return self._deliver_present_member(
                task=task, raw_meta=raw_meta, samples=samples, finalized=finalized, audit=audit
            )

        for leaf in samples:
            leaf.reward = grading_reward
            # 宿主 metadata 只写两个白名单派生视图键（S1-5 派生视图定案），
            # 值逐字取 report.derived_view_*，治理事实不经其他 key 走私。
            leaf.metadata = {
                **(getattr(leaf, "metadata", None) or {}),
                "eligibility_report_ref": report.derived_view_report_ref,
                "training_eligibility_class": report.derived_view_class,
            }
        audit.delivered_sample_count = len(samples)
        audit.step("step9_samples_delivered")
        return list(samples)

    def _deliver_present_member(
        self,
        *,
        task: RolloutTaskSpec,
        raw_meta: Any,
        samples: Sequence[Any],
        finalized: FinalizedRollout | None,
        audit: RolloutAudit,
    ) -> list[Any]:
        """三终态 ③ 的交付面（非 s1 模式）：present_* 成员真实交付 + typed admission 载荷。

        适用两类成员：
        - 完整 finalize（`finalized` 在场）：合格与不合格都走这里——载荷内嵌 EligibilityReport
          与 Outcome v2，filter 按七维 reason_code 裁决；
        - 契约封闭豁免集（`finalized=None`：unsafe artifact 永久拒绝——present_complete、
          reward 不可得、无 EligibilityReport）：载荷只内嵌 Outcome v2，filter 按豁免集 DROP。

        reward 不可得（failed_to_grade / unsafe）时 miles Sample.reward 用 **NaN** 占位：
        - 不用 None——miles `generate_and_rm` 会对 reward=None 的样本调 rm hub，而 rh2 链
          没有配置 rm_type/custom_rm_path，会在 `async_rm` 里 AttributeError 炸掉整组任务；
        - 不用 0.0——P4 红线：infra/未评分绝不伪装成 reward=0 的负样本；
        - NaN 若因接线错误绕过 filter 进入训练，会在 advantage 计算里 loud-fail 而不是静默污染。
        typed 载荷里 `outcome.reward_unavailable=True` 是权威事实，filter 会核对二者一致。
        """

        meta = raw_meta if isinstance(raw_meta, Mapping) else {}
        if audit.outcome_v2 is None:
            raise FatalExecutionInfrastructureError(
                "admission_payload_without_outcome",
                f"attempt {audit.physical_attempt_id or audit.trajectory_id} 走到交付面却没有 Outcome v2"
                "——非 s1 模式的 present 成员必带执行结果权威，run-halt。",
            )
        report = finalized.eligibility_report if finalized is not None else None
        grading_report = finalized.grading_report if finalized is not None else None
        try:
            outcome = RolloutAttemptOutcomeV2.model_validate(audit.outcome_v2)
            payload = derive_admission_payload(
                outcome=outcome,
                eligibility_report=report,
                grading_report=grading_report,
                handshake=audit.handshake,
                task_id=task.task_id,
                public_bundle_digest=task.public_bundle_digest,
                environment_package_digest=(
                    str(meta["environment_package_digest"])
                    if meta.get("environment_package_digest")
                    else None
                ),
            )
        except (AdmissionError, ValidationError) as exc:
            # 载荷派生失败 = 交付面各权威对象互相矛盾（账实矛盾），run-halt，不许伪装成缺员。
            audit.failure_records.append(
                RolloutFailureRecord(
                    stage="deliver",
                    error_type="admission_payload_build_failed",
                    detail=f"{type(exc).__name__}: {exc}"[:500],
                )
            )
            audit.mark("admission_payload_build_failed")
            raise FatalExecutionInfrastructureError(
                "admission_payload_build_failed",
                f"admission 载荷派生失败：{type(exc).__name__}: {exc}——交付面账实矛盾，run-halt。",
            ) from exc
        grading_reward = grading_report.reward if grading_report is not None else None
        delivered_reward = float("nan") if grading_reward is None else float(grading_reward)
        for leaf in samples:
            leaf.reward = delivered_reward
            leaf.remove_sample = False
            leaf_meta = dict(getattr(leaf, "metadata", None) or {})
            if report is not None:
                # 宿主 metadata 的两个白名单派生视图键（S1-5 载体定案），值逐字取 report。
                leaf_meta["eligibility_report_ref"] = report.derived_view_report_ref
                leaf_meta["training_eligibility_class"] = report.derived_view_class
            leaf.metadata = leaf_meta
        try:
            stamp_admission_payload(list(samples), payload)
        except AdmissionError as exc:
            audit.failure_records.append(
                RolloutFailureRecord(
                    stage="deliver",
                    error_type="admission_payload_stamp_conflict",
                    detail=str(exc)[:500],
                )
            )
            audit.mark("admission_payload_stamp_conflict")
            raise FatalExecutionInfrastructureError(
                "admission_payload_stamp_conflict",
                f"admission 载荷盖章冲突：{exc}——交付叶身份与本次 attempt 不符，run-halt。",
            ) from exc
        if report is None:
            audit.mark("present_member_delivered_without_report")
        elif not finalized.eligibility_report.facts.all_ok():
            audit.mark("degraded_member_delivered_for_group_admission")
        audit.delivered_sample_count = len(samples)
        audit.step("step9_samples_delivered")
        return list(samples)

    def _write_artifacts(
        self, audit: RolloutAudit, hook: GenerationCaptureHook, finalized: FinalizedRollout
    ) -> None:
        """artifact 旁路：sidecar 与 tape 落盘（audit/parity/离线导出的取证面）。"""

        if self.artifact_dir is None:
            return
        root = self.artifact_dir / _sanitize_for_name(audit.trajectory_id)
        root.mkdir(parents=True, exist_ok=True)
        sidecars = {
            "eligibility_report.json": finalized.eligibility_report,
            "trajectory_projection.json": finalized.projection,
            "grading_report.json": finalized.grading_report,
            "group_repair_signal.json": finalized.group_repair_signal,
        }
        for filename, model in sidecars.items():
            path = root / filename
            path.write_text(model.model_dump_json(indent=2), encoding="utf-8")
            audit.artifact_paths.append(path)
        captures_path = root / "capture_records.json"
        captures_path.write_text(
            json.dumps(
                [json.loads(record.model_dump_json()) for record in hook.records],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        audit.artifact_paths.append(captures_path)
        tape_dir = root / "tapes"
        tape_dir.mkdir(exist_ok=True)
        for ref_id, payload in hook.artifact_store.items():
            tape_path = tape_dir / f"{ref_id}.bin"
            tape_path.write_bytes(payload)
            audit.artifact_paths.append(tape_path)

    # ------------------------------------------------------------------ 清理与收口
    async def _cleanup_container(
        self, lease: SandboxLease, name: str, audit: RolloutAudit
    ) -> None:
        """Q7：无条件清理；Q8：失败落 CleanupFailureRecord（infra_failure）。幂等。"""

        if audit.lease_released:
            return
        try:
            rm = await asyncio.wait_for(
                self._docker("rm", "-f", name), timeout=lease.cleanup.timeout_seconds
            )
        except (TimeoutError, asyncio.TimeoutError):
            audit.cleanup_failures.append(
                CleanupFailureRecord(
                    lease_id=lease.lease_id,
                    step="remove_container",
                    detail=f"docker rm 超时（>{lease.cleanup.timeout_seconds}s）",
                )
            )
            return
        if rm.exit_code != 0:
            audit.cleanup_failures.append(
                CleanupFailureRecord(
                    lease_id=lease.lease_id,
                    step="remove_container",
                    detail=rm.stderr.strip()[-300:],
                )
            )
            return
        audit.lease_released = True  # release_lease 步骤 = 记账翻转

    @staticmethod
    def _notify_fatal_halt(exc: FatalExecutionInfrastructureError) -> None:
        """联合终核 P1-1 的同步 halt 通知：finally 的异步 cleanup 会推迟 Fatal 到达
        worker，先经 task-local notifier 置 halt（无 notifier 时是 no-op）。"""

        from repoharness2.adapters.slime.async_worker import fatal_halt_notifier

        notifier = fatal_halt_notifier.get()
        if notifier is not None:
            notifier(exc)

    def _produce_outcome_v2(self, *, audit: "RolloutAudit", **facts: Any) -> None:
        """Outcome v2 producer 的守卫入口（W1b 切片一复核 必修 1）。

        - **只允许调用一次**：每个 physical attempt 只有一条终态 Outcome。此前是
          compare-and-set 静默返回，会把"deliver 失败后通用 except 再次产出"这类
          流程掩盖成普通 ABORTED；现在二次调用本身即 run-fatal（程序错误可见）。
        - **构造失败 = run-fatal**：validator 拒绝/契约矛盾是 producer 或事实层的
          bug，不是单个成员损耗——不许从 except 子句裸逃成 ValidationError，也不许
          洗成 ABORTED。
        """

        if audit.outcome_v2 is not None:
            audit.mark("outcome_producer_called_twice")
            raise FatalExecutionInfrastructureError(
                "outcome_producer_called_twice",
                f"attempt {audit.physical_attempt_id or audit.trajectory_id} 的 Outcome v2 "
                "已产出，producer 被二次调用——终态只允许一条，run-halt。",
            )
        try:
            self._produce_outcome_v2_unguarded(audit=audit, **facts)
        except FatalExecutionInfrastructureError:
            raise
        except Exception as exc:  # noqa: BLE001 - producer/契约异常一律 run-fatal
            audit.failure_records.append(
                RolloutFailureRecord(
                    stage="outcome_producer",
                    error_type=type(exc).__name__,
                    detail=str(exc)[:500],
                )
            )
            audit.mark("outcome_producer_failed")
            raise FatalExecutionInfrastructureError(
                "outcome_producer_failed",
                f"Outcome v2 构造失败：{type(exc).__name__}: {exc}——事实层/契约矛盾，run-halt。",
            ) from exc

    def _produce_outcome_v2_unguarded(
        self,
        *,
        audit: "RolloutAudit",
        raw_meta: Any,
        termination_kind: str,
        failure_category: str | None,
        reason_code: str | None,
        failed_component: str | None,
        task_resolved: bool | None,
        turn_weight_versions: list[str] | None,
        current_version_at_finalize: str | None,
        eligibility_report_id: str | None,
        extra_evidence: list[str] | None = None,
    ) -> None:
        """F2-2 producer 收口：由事实构造 Outcome v2 并挂 audit（随 sink 落盘）。

        S1 兼容路径（metadata 无四层身份）产不出 v2——build 返回 None，
        audit.outcome_v2 保持 None（正式 FA 链 entry 必stamp 身份）。
        构造失败 = 事实矛盾（validator 拒绝），fail-loud 不吞。
        """

        # P0-2 终态唯一性由守卫入口 `_produce_outcome_v2` 强制（二次调用 = fatal，
        # 不再静默 compare-and-set）。
        meta = raw_meta if isinstance(raw_meta, Mapping) else {}
        seq_raw = meta.get("rh2_physical_attempt_seq")
        slot_raw = meta.get("rh2_member_slot")
        gidx_raw = meta.get("rh2_group_index")
        # P1-5：正式 FA 路径（有 paid）要求完整身份字段，不静默补值——
        # 任一缺失 = entry 契约破损，宁不产 v2（audit note）也不伪造
        if audit.physical_attempt_id is not None and (
            seq_raw is None
            or slot_raw is None
            or gidx_raw is None
            or not meta.get("rh2_prompt_group_id")
            or not meta.get("rh2_rollout_execution_id")
        ):
            audit.mark("outcome_v2_skipped_identity_incomplete")
            return
        versions = list(turn_weight_versions or [])
        span = derive_weight_version_max_lag(versions) if versions else None
        # termination：P1-4 的 hard wall 观测优先于调用方给的 kind（真实
        # trigger 事实 > 收口路径推断；异常路径映射到 infra 族时保留映射）
        if audit.termination_kind_hint is not None and termination_kind == "completed":
            termination_kind = audit.termination_kind_hint
        outcome = build_outcome_v2(
            outcome_id=f"ov2_{audit.physical_attempt_id or audit.trajectory_id}",
            prompt_group_id=(
                str(meta["rh2_prompt_group_id"]) if meta.get("rh2_prompt_group_id") else None
            ),
            group_index=int(gidx_raw) if gidx_raw is not None else 0,
            rollout_execution_id=(
                str(meta["rh2_rollout_execution_id"])
                if meta.get("rh2_rollout_execution_id")
                else audit.trajectory_id
            ),
            physical_attempt_id=audit.physical_attempt_id,
            physical_attempt_seq=int(seq_raw) if seq_raw is not None else None,
            member_slot=int(slot_raw) if slot_raw is not None else None,
            termination_kind=termination_kind,  # type: ignore[arg-type]
            quiescence_confirmed=audit.runtime_quiescence_confirmed,
            capture_closed=audit.capture_closed,
            failure_category=failure_category,  # type: ignore[arg-type]
            reason_code=reason_code,
            failed_component=failed_component,
            task_resolved=task_resolved,
            turn_weight_versions=versions,
            intra_execution_version_span=span,
            current_version_at_finalize=current_version_at_finalize,
            eligibility_report_id=eligibility_report_id,
            evidence_refs=[f"audit:{audit.trajectory_id}", *(extra_evidence or [])],
        )
        if outcome is not None:
            audit.outcome_v2 = outcome.model_dump(mode="json")
            self.outcomes.append(outcome)

    def _session_id(self, sample: Any, task: RolloutTaskSpec) -> str:
        """会话 id（兼作 auth token 与路由键）：形状对齐 slime 例程 _session_id。"""

        existing = getattr(sample, "session_id", None)
        if existing:
            return str(existing)
        index = getattr(sample, "index", None)
        group_index = getattr(sample, "group_index", None)
        if index is not None and group_index is not None:
            return f"rh2-{task.task_id}-{index}-{group_index}"
        return f"rh2-{task.task_id}-{secrets.token_hex(8)}"

    def _abort_result(
        self,
        sample: Any,
        *,
        reason: str,
        task: RolloutTaskSpec,
        report: Any | None = None,
        top_p: float | None = None,
        audit: "RolloutAudit | None" = None,
    ) -> list[Any]:
        """slime 例程 _abort_result 的同形收口：标记剔除并保持 fan-out 列表形状。

        W1b 第二段（三终态 ②）：非 s1 模式下 abort 形状（ABORTED，交 miles unused handler）
        **只**允许给 completion_class=missing 的 attempt（未形成 present 对象的已归因 task-local
        故障）或尚无 Outcome 的结构化拒绝（身份不全）；已产出 present_* Outcome 的成员被压成
        abort 形状 = 交付面接线矛盾（"事实说评分完整但样本是 abort 形状"），run-halt。

        top-p 补充（S1-7a 源码核对推翻差异假设 7 的"逐字段照抄即可"）：
        `rollout_top_p != 1.0` 时 slime `_convert_samples_to_train_data` 对
        **每条**样本（含 remove_sample 剔除样本）断言 top-p 双字段在场且
        `len(offsets) == response_length + 1`——例程 abort 形状缺这两个字段，
        在 top-p 训练配置下整个 batch 转换会当场 assert 崩。剔除样本没有任何
        可训练 token，如实回填零宽 tape：ids=[]、offsets=[0,0]（response_length
        =1 的占位 token 核集合为空）。top_p 为 None 或 1.0 时保持例程原形状
        （此时 slime 反过来要求字段**不在场**，混填会让 batch 收集分叉）。
        """

        if (
            audit is not None
            and self._mode != "s1_compat"
            and audit.outcome_v2 is not None
            and audit.outcome_v2.get("completion_class") != "missing"
        ):
            audit.mark("abort_shape_for_present_outcome")
            raise FatalExecutionInfrastructureError(
                "abort_shape_for_present_outcome",
                f"attempt {audit.physical_attempt_id or audit.trajectory_id} 的 Outcome 是 "
                f"{audit.outcome_v2.get('completion_class')}，却要以 abort 形状（{reason}）交付——"
                "ABORTED 只给 completion=missing，present 成员必须真实交付由组级 filter 裁决。",
            )
        sample.tokens = [0, 0]
        sample.response = ""
        sample.response_length = 1
        sample.loss_mask = [0]
        sample.rollout_log_probs = [0.0]
        if top_p is not None and top_p < 1.0:
            sample.rollout_top_p_token_ids = []
            sample.rollout_top_p_token_offsets = [0, 0]
        sample.reward = 0.0
        sample.remove_sample = True
        _set_status(sample, "aborted")
        metadata = {
            **(getattr(sample, "metadata", None) or {}),
            "abort_reason": reason,
            "instance_id": task.task_id,
        }
        if report is not None:
            # 派生视图白名单键：降级样本同样只暴露 report 引用与三档结论，
            # 具体维度/理由码只在 sidecar（EligibilityReport）里。
            metadata["eligibility_report_ref"] = report.derived_view_report_ref
            metadata["training_eligibility_class"] = report.derived_view_class
        sample.metadata = metadata
        return [sample]


# ---------------------------------------------------------------------------
# slime custom_generate 入口（签名对齐 sglang_rollout 的分派约定）
# ---------------------------------------------------------------------------


async def rh2_custom_generate(
    args: Any, sample: Any, sampling_params: dict[str, Any], evaluation: bool = False
) -> list[Any]:
    """slime `--custom-generate-function-path` 指向的入口。

    slime 侧调用形状（reference/slime/slime/rollout/sglang_rollout.py）::

        sample = await custom_generate_func(args, sample, sampling_params, evaluation=evaluation)

    编排本体（RolloutOrchestrator）经 ``args.rh2_orchestrator`` 传入——slime 的
    args 是一个可自由挂属性的 Namespace，训练脚本在启动期构造 orchestrator 并
    挂上去（与 slime 例程用模块级 `_AdapterService(args)` 单例同一层级的选择，
    差别是显式传递、无隐藏全局，mock 单测可逐 rollout 换配置）。
    """

    orchestrator = getattr(args, "rh2_orchestrator", None)
    if orchestrator is None:
        raise SlimeBindingError(
            "orchestrator_not_configured",
            "args.rh2_orchestrator 缺失：训练脚本必须在启动期构造 RolloutOrchestrator "
            "并挂到 slime args 上（startup_checks 通过之后）。",
        )
    return await orchestrator.generate(args, sample, sampling_params, evaluation=evaluation)
