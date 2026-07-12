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
import re
import secrets
import struct
import time
import uuid
from collections.abc import Awaitable, Callable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Protocol

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
    GradingFailureCategory,
    GradingReport,
    HarnessLaunchSpec,
    ModelProxyEndpoint,
    SandboxLease,
    WorkspaceHandle,
    canonical_json_digest,
)
from repoharness2.envpack import bundles, materialize
from repoharness2.governance import FinalizedRollout, GroupRepairSignal, finalize_rollout
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
) -> list[TurnTape]:
    """把 capture 钩子攒下的按轮 tape 回填到一条叶链 Sample 上（原地写字段）。

    背景（S1-3 slime 源码核对）：TrajectoryManager 叶链产物 `_SampleBuilder.
    to_sample()` 只填 tokens/response_length/loss_mask/rollout_log_probs/
    reward/status/metadata；rollout_top_p_token_ids/offsets、rollout_routed_experts、
    weight_versions 的合并逻辑在 `Sample.append_response_tokens/_apply_meta_info`
    （非 TrajectoryManager 路径）。这些字段在 slime Sample dataclass 上都存在、
    可写，本函数按 slime 自己的合并语义回填：

    - run<->turn 归属：token 同一性锚定（见 `_match_turns_to_runs`——S1-7a 用
      真实 TrajectoryManager 证伪了 mock 的"段数=轮数且等长"假设 3）；
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
    per_turn_versions: list[str] = []
    versions_complete = True
    for tape in used:
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


class SessionAdapter(Protocol):
    """slime BaseAdapter 的会话生命周期面（open/finish/drop，字段名逐一对应）。

    真实实现 = slime `AnthropicAdapter`（含内部 TrajectoryManager）；
    finish_session 返回叶链 Sample 列表（TrajectoryManager.get_trajectory 语义）。
    """

    def open_session(
        self, sid: str, *, sampling_defaults: dict | None = None, max_context_tokens: int = 0
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
    """一次 rollout 的任务面（public 半区事实 + 评分 spec 引用）。

    评分私有材料**不在本对象上**：grading_spec 内嵌的 eval 脚本/parser 闭包
    只进评分容器（S1-4 通道），永不写入 rollout 容器（A6/Q6）。
    """

    task_id: str
    image: str
    base_commit: str
    prompt: str
    public_bundle_payload: bytes  # 写入 rollout 容器的 public bundle JSON 字节流
    public_bundle_digest: str  # sha256:<hex>（BundleMount 记账）
    grading_spec: GradingEnvSpec
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
    staleness_threshold: int = 4
    # FA-0（05 计划 D-FA-1/FA-0.3）：正式链开关。True 时：
    #   1. 构造 orchestrator 即断言 policy_version 不是静态哨兵值（step_0/None）
    #      且可解析为十进制整数（引擎 update_weights 计数器语义）；
    #   2. 装配期要求每个入训轮的 tape 都带真实 weight_version（缺失 fail-closed）；
    #   3. 握手的 staleness_steps 按真实版本差计算，不再恒 0。
    # False = S1 兼容/测试路径（默认），行为逐字不变。
    require_real_weight_versions: bool = False
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

    def step(self, name: str) -> None:
        self.steps.append(name)
        self.mark(name)

    def mark(self, name: str) -> None:
        """记录不改变 S1 生命周期步骤语义的旁路时间线事件。"""

        self.timeline.append(
            RolloutTimelineEntry(
                step=name,
                seconds_since_start=round(time.monotonic() - self.started_monotonic, 3),
                epoch_seconds=round(time.time(), 3),
            )
        )

    def timeline_dicts(self) -> list[dict[str, float | str]]:
        return [
            {
                "step": entry.step,
                "seconds_since_start": entry.seconds_since_start,
                "epoch_seconds": entry.epoch_seconds,
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
    ) -> None:
        if config.require_real_weight_versions:
            # FA-0 正式链启动断言：静态哨兵版本禁止进入正式链（05 计划 FA-0.3 验收项）。
            version = config.policy_version
            if version is None or version == "step_0":
                raise StartupCheckError(
                    "static_policy_version_forbidden_in_formal_chain",
                    f"require_real_weight_versions=True 但 policy_version={version!r}——"
                    "正式链必须用引擎探针实测的 weight_version（glue 假设 4 管道），"
                    "静态哨兵值只允许测试路径。",
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
                    "正式链（require_real_weight_versions=True）必须同时开启 "
                    "reject_context_shrink——D-FA-6 的收缩兜底是硬要求，"
                    "不能只凭 DISABLE_COMPACT 环境变量宣布 compaction 已关闭。",
                )
            if not config.reject_on_nonzero_harness_exit:
                raise StartupCheckError(
                    "nonzero_exit_rejection_disabled_in_formal_chain",
                    "正式链必须同时开启 reject_on_nonzero_harness_exit——"
                    "任务失败的负样本是 CC exit 0 + grader reward=0；CC 非零"
                    "退出只可能是 harness/API/进程执行失败，无已验证的非零"
                    "业务退出码前一律拒绝（codex 轮次 9 P0-3）。",
                )
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
        self.audits: list[RolloutAudit] = []

    # ------------------------------------------------------------------ 入口
    async def generate(
        self, args: Any, sample: Any, sampling_params: dict[str, Any], evaluation: bool = False
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
        sid = self._session_id(sample, task)
        sample.session_id = sid
        trajectory_id = sid

        audit = RolloutAudit(trajectory_id=trajectory_id, task_id=task.task_id)
        self.audits.append(audit)
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
        session_defaults = {
            **sampling_params,
            # E2 硬依赖：top_p<1.0 必须请求 top-p tape；MoE 必须请求 routing tape。
            "return_top_p_token_ids": top_p < 1.0,
            "return_routed_experts": self.config.expect_moe_routing,
        }
        adapter = self._adapter_factory(hook, session_defaults)

        stage = "materialize"
        sandbox: _MaterializedSandbox | None = None
        session_open = False
        try:
            sandbox = await self._materialize_rollout_sandbox(task, trajectory_id, audit)
            audit.step("step2_workspace_materialized")

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
                sampling_defaults=session_defaults,
                max_context_tokens=self.config.max_context_len,
            )
            session_open = True
            audit.mark("harness_started")
            harness_task = asyncio.ensure_future(
                self._harness_driver.run(
                    sandbox.workspace,
                    workdir=launch.workdir,
                    session_id=launch.model_proxy.session_id,
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
            audit.step("step3_harness_completed")

            stage = "assemble"
            # P0-2：harness 返回后复检 session poison（权威信号）——不可归因
            # 故障期间捕获的任何轮都不可训，整 execution 缺员。
            if self._session_poison_check is not None and self._session_poison_check(sid):
                raise SlimeBindingError(
                    "session_poisoned_during_execution",
                    f"session {sid} 在 harness 执行期间中毒（proxy 判不可归因故障）"
                    "——已捕获的 partial trace 全部作废，execution 缺员。",
                )
            if self.config.reject_on_nonzero_harness_exit and exit_code != 0:
                raise SlimeBindingError(
                    "nonzero_harness_exit_in_formal_chain",
                    f"harness 非零退出 {exit_code}（正式链拒绝）——训练守卫下 CC "
                    "不该因 infra 失败退出，可疑到拒绝该 execution。",
                )
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
            samples = await adapter.finish_session(
                sid,
                base_sample=sample,
                reward=0.0,  # 真实 reward 出自步骤 6 评分，之后再回写（见差异假设清单）
                extra_metadata={"instance_id": task.task_id},
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
                used = backfill_leaf_sample(
                    leaf,
                    turns,
                    moe_num_layers=self.config.moe_num_layers,
                    moe_router_topk=self.config.moe_router_topk,
                    policy_version=self.config.policy_version,
                    require_real_weight_versions=self.config.require_real_weight_versions,
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
                )
                for facts, used_ids in zip(leaf_facts, used_record_ids)
            ]
            audit.step("step5_leaf_samples_assembled_and_backfilled")

            stage = "finalize"
            handshake = self._build_handshake(trajectory_id, samples)
            audit.handshake = handshake
            finalized = await self._finalize(
                task=task,
                trajectory_id=trajectory_id,
                base_sample=sample,
                samples=samples,
                leaf_facts=leaf_facts,
                hook=hook,
                workspace=sandbox.workspace,
                handshake=handshake,
                audit=audit,
            )
            audit.finalized = finalized
            audit.step("step8_gate_finalized")

            stage = "deliver"
            return self._deliver(
                task=task,
                base_sample=sample,
                samples=samples,
                finalized=finalized,
                hook=hook,
                audit=audit,
                evaluation=evaluation,
                top_p=top_p,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - 收口为 abort，归因进 audit
            audit.failure_records.append(
                RolloutFailureRecord(
                    stage=stage,
                    error_type=type(exc).__name__,
                    detail=str(exc)[:500],
                )
            )
            return self._abort_result(
                sample, reason=f"rh2_{stage}_failed:{type(exc).__name__}", task=task, top_p=top_p
            )
        finally:
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
                await self._cleanup_container(sandbox.lease, sandbox.container_name, audit)
            audit.mark("cleanup_completed")
            if self._session_poison_release is not None:
                # 真正的 execution 清理 ACK：harness 终止 + 会话撤销 + 容器
                # 清理都已完成，active poison 此刻才允许归档（轮次 11）
                self._session_poison_release(sid)

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
        run = await self._docker(
            "run",
            "--detach",
            *network_args,
            "--label",
            f"{prefix}.trajectory={trajectory_id}",
            "--label",
            f"{prefix}.created_at_epoch={int(_now_utc().timestamp())}",
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
        return BackendHandshake(
            handshake_id=f"hs_{trajectory_id}",
            trajectory_id=trajectory_id,
            backend_name="slime",
            policy_version=current_version,
            weight_versions_seen=seen or [current_version],
            staleness_steps=staleness_steps,
            staleness_threshold=self.config.staleness_threshold,
            staleness_within_threshold=staleness_steps <= self.config.staleness_threshold,
            group_signal=None,
            accepted=True,
            handshaked_at_utc=_now_utc(),
        )

    async def _finalize(
        self,
        *,
        task: RolloutTaskSpec,
        trajectory_id: str,
        base_sample: Any,
        samples: Sequence[Any],
        leaf_facts: Sequence[LeafFacts],
        hook: GenerationCaptureHook,
        workspace: RolloutContainerWorkspace,
        handshake: BackendHandshake | None,
        audit: RolloutAudit,
    ) -> FinalizedRollout:
        """步骤 6~8：只准调 finalize_rollout（治理层唯一关口，顺序已被 wrapper 固化）。"""

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
            audit.mark("grading_started")
            report = await self._grading_submit(
                trajectory_id=trajectory_id, workspace=workspace, spec=task.grading_spec
            )
            audit.step("step6_grading_completed")
            return report

        def _project(report: GradingReport):
            audit.mark("projection_started")
            projection = project_from_slime(
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
            audit.step("step7_projection_completed")
            return projection

        return await finalize_rollout(
            grade=_grade,
            project=_project,
            capture_records=hook.records,
            handshake=handshake,
            findings=(),
            backpressure_events=list(self._backpressure_events_source()),
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
        if self._repair_signal_sink is not None:
            self._repair_signal_sink(signal)
        audit.repair_signal_forwarded = True
        self._write_artifacts(audit, hook, finalized)

        report = finalized.eligibility_report
        if signal.degraded:
            # 降级判据 = 七维事实（S1 封顶不算降级，S1-5 定案），样本以 slime
            # abort 形状剔除；完整判定依据在 sidecar（artifact 旁路已落盘）。
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
    ) -> list[Any]:
        """slime 例程 _abort_result 的同形收口：标记剔除并保持 fan-out 列表形状。

        top-p 补充（S1-7a 源码核对推翻差异假设 7 的"逐字段照抄即可"）：
        `rollout_top_p != 1.0` 时 slime `_convert_samples_to_train_data` 对
        **每条**样本（含 remove_sample 剔除样本）断言 top-p 双字段在场且
        `len(offsets) == response_length + 1`——例程 abort 形状缺这两个字段，
        在 top-p 训练配置下整个 batch 转换会当场 assert 崩。剔除样本没有任何
        可训练 token，如实回填零宽 tape：ids=[]、offsets=[0,0]（response_length
        =1 的占位 token 核集合为空）。top_p 为 None 或 1.0 时保持例程原形状
        （此时 slime 反过来要求字段**不在场**，混填会让 batch 收集分叉）。
        """

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
