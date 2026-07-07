"""GenerationCaptureRecord：SGLang 客户端响应层的原始生成事实 sidecar（补充条款 A4）。

为什么需要它：slime `Sample` 是训练容器，不是完整审计事实源——它在
TrajectoryManager 归并、loss mask 计算之后才成形，top-p tape / routing tape /
sampling 参数 / 后端版本这些事实必须在更早的位置（协议 adapter 拿到 SGLang
`/generate` 响应的那一刻）捕获。TrajectoryProjection 通过
`BranchProjection.capture_record_refs` 引用本记录，而不是从训练后的 Sample 反推。

一条真实形状的记录（S1-0 探针，Qwen/Qwen3-30B-A3B on slime patch 镜像）：
prompt 15 token、生成 16 token、top_p=0.95、logprobs 16 条、
top_p_token_offsets 长 17、routed_experts 形状 [30, 48, 8]、
meta_info.id = "68ecd97a303343fdb0d984cd8e86e011"（即 request_id）。
"""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from repoharness2.contracts._base import (
    ArtifactRef,
    NonEmptyStr,
    Sha256Digest,
    StrictModel,
)

CaptureStatus = Literal[
    "complete",  # 本轮全部期望事实（ids/logprobs/按需 tape）都已捕获且对齐
    "partial",  # 捕获到部分事实（例如 tape 缺失、abort 截断）——gate 会挡在 online 档外
    "failed",  # 本轮捕获失败（请求失败 / 解析失败）
]

AlignmentStatus = Literal[
    "aligned",  # output ids / logprobs / tape 长度关系全部核对通过
    "mismatch",  # 有事实在场但对不上（长度/offsets 关系断裂）
    "not_checked",  # 尚未核对（只允许与 partial/failed 搭配）
]


class CaptureSamplingParams(StrictModel):
    """本轮 /generate 请求实际使用的采样参数（引用自请求体，不是训练配置的转述）。"""

    temperature: float = Field(ge=0.0, description="采样温度（E2 配方 1.0）。")
    top_p: float = Field(gt=0.0, le=1.0, description="top-p 截断（E2 定案 0.95）。")
    max_new_tokens: int = Field(ge=1, description="本轮最大生成 token 数。")
    return_top_p_token_ids: bool = Field(
        description=(
            "是否请求 top-p tape（slime patch 的 custom_params）。S0-6 实测该 flag 是"
            "字段在场与否的开关（control case：不带 flag 时字段缺席），必须原样记录。"
        )
    )
    return_routed_experts: bool = Field(
        description="是否请求 MoE routing tape（dense 模型请求方应传 False）。"
    )


class GenerationCaptureRecord(StrictModel):
    """一次 /generate 调用的原始事实 sidecar（A4 字段清单的逐项落点）。

    创建者：slime Anthropic adapter 侧的捕获钩子（S1-6 编排注入），
    在响应成功 flush 后立即写出。消费者：project_from_slime（回链）、
    inspect-rh2-artifact（审计）、parity 校验（S1-8）。

    fail-closed 行为（模型校验器逐条执行）：
    1. capture_status=complete 时，logprobs_ref 必填且 alignment_status 必须是 aligned；
    2. 请求了 top-p tape（top_p<1.0 且 return_top_p_token_ids=True）而 tape 引用缺失时，
       capture_status 不允许是 complete——这正是"镜像静默降级"的探测点（U-H 回归）；
    3. 请求了 routing tape 而 routed_experts_ref 缺失时，同样禁止 complete；
    4. top-p 的 ids/offsets 引用必须成对出现（slime 同款约束）；
    5. prompt 侧必须至少给 hash 或 ref 之一；raw meta_info 必须至少给 digest 或 ref 之一
       ——meta_info 一条在 capture_status=failed 时豁免（请求失败可能根本没有 meta_info）；
    6. response_token_count > 0 时 response_token_ids_ref 必填（对 partial/failed 同样生效：
       声称生成了 token 就必须能指出 ids 在哪，否则计数无凭据）；
    7. capture_status=failed 时 capture_failure_reason 必填（失败不可无因）；
       非 failed 状态不得携带该字段。
    """

    schema_id: Literal["rh2.generation_capture_record.v1"] = Field(
        default="rh2.generation_capture_record.v1",
        description="schema 判别字段。",
    )
    record_id: NonEmptyStr = Field(description="本捕获记录的唯一 id（BranchProjection 回链用）。")
    request_id: NonEmptyStr = Field(
        description="推理服务端分配的请求 id（SGLang meta_info.id，例如 68ecd97a…）。"
    )
    turn_id: NonEmptyStr = Field(description="轨迹内的轮次 id（同一轨迹多轮生成按此排序）。")
    trajectory_id: NonEmptyStr = Field(description="所属轨迹 id。")
    model_name: NonEmptyStr = Field(description="模型名（如 Qwen/Qwen3-30B-A3B）。")
    backend_name: Literal["sglang", "vllm"] = Field(
        description="推理后端。取值封闭：新后端必须先扩契约（fail-closed）。"
    )
    backend_version: NonEmptyStr = Field(description="推理后端版本（如 0.5.9）。")
    sampling_params: CaptureSamplingParams = Field(description="本轮实际采样参数。")
    renderer_cls_name: NonEmptyStr = Field(
        description="渲染 prompt 所用 renderer 类名（U-G 断言的事实来源）。"
    )
    tokenizer_name: NonEmptyStr = Field(description="tokenizer 名称。")
    template_hash: Sha256Digest = Field(
        description="chat template 内容 digest（渲染一致性 / parity 比对的锚点）。"
    )
    prompt_token_count: int = Field(ge=1, description="prompt token 数（例：15）。")
    response_token_count: int = Field(
        ge=0, description="实际生成 token 数（例：16；abort 时可为 0）。"
    )
    prompt_token_ids_ref: ArtifactRef | None = Field(
        default=None, description="prompt token ids 的引用（与 hash 至少给一个）。"
    )
    prompt_token_ids_sha256: Sha256Digest | None = Field(
        default=None, description="prompt token ids 的 digest（与 ref 至少给一个）。"
    )
    response_token_ids_ref: ArtifactRef | None = Field(
        default=None,
        description="采样 output ids 的引用（response_token_count>0 时必填，任何 capture_status 下都不豁免）。",
    )
    raw_meta_info_ref: ArtifactRef | None = Field(
        default=None,
        description="原始 meta_info 全文引用（与 digest 至少给一个；capture_status=failed 时可都缺）。",
    )
    raw_meta_info_digest: Sha256Digest | None = Field(
        default=None,
        description="原始 meta_info 规范化 digest（与 ref 至少给一个；capture_status=failed 时可都缺）。",
    )
    logprobs_ref: ArtifactRef | None = Field(
        default=None, description="逐 token logprob（meta_info.output_token_logprobs）的引用。"
    )
    top_p_token_ids_ref: ArtifactRef | None = Field(
        default=None, description="top-p 保留核集合 ids 的引用（与 offsets 成对）。"
    )
    top_p_token_offsets_ref: ArtifactRef | None = Field(
        default=None, description="top-p ragged offsets 的引用（与 ids 成对）。"
    )
    routed_experts_ref: ArtifactRef | None = Field(
        default=None, description="MoE routing tape 的引用（dense 模型为 None）。"
    )
    capture_status: CaptureStatus = Field(description="本轮捕获完成度结论。")
    capture_failure_reason: NonEmptyStr | None = Field(
        default=None,
        description=(
            "捕获失败原因（如 request_timeout、response_parse_error）。"
            "capture_status=failed 时必填；complete/partial 时必须为 None。"
        ),
    )
    alignment_status: AlignmentStatus = Field(description="本轮对齐核对结论。")
    captured_at_utc: AwareDatetime = Field(description="捕获时间（必须带时区）。")

    @model_validator(mode="after")
    def _check_capture_contract(self) -> "GenerationCaptureRecord":
        # 5. prompt 与 meta_info 的"至少一个"规则（meta_info 在 failed 时豁免：
        #    请求失败可能根本没拿到 meta_info，强求会逼生产者伪造 digest）
        if self.prompt_token_ids_ref is None and self.prompt_token_ids_sha256 is None:
            raise ValueError(
                "prompt_token_ids_ref 与 prompt_token_ids_sha256 至少提供一个（A4）。"
            )
        if (
            self.capture_status != "failed"
            and self.raw_meta_info_ref is None
            and self.raw_meta_info_digest is None
        ):
            raise ValueError(
                "raw_meta_info_ref 与 raw_meta_info_digest 至少提供一个"
                "（A4；仅 capture_status=failed 允许都缺）。"
            )

        # 6. 计数与 ids 引用互检：声称生成了 token 就必须能指出 ids 在哪
        if self.response_token_count > 0 and self.response_token_ids_ref is None:
            raise ValueError(
                f"response_token_count={self.response_token_count} > 0 时 response_token_ids_ref 必填"
                "（fail-closed：无 ids 引用的计数声明无凭据，partial/failed 也不豁免）。"
            )

        # 7. failed 必须有失败原因；非 failed 不得携带
        if self.capture_status == "failed" and self.capture_failure_reason is None:
            raise ValueError("capture_status=failed 时 capture_failure_reason 必填（失败不可无因）。")
        if self.capture_status != "failed" and self.capture_failure_reason is not None:
            raise ValueError(
                f"capture_status={self.capture_status} 不得携带 capture_failure_reason"
                "（失败原因只属于 failed 状态）。"
            )

        # 4. top-p ids/offsets 成对
        if (self.top_p_token_ids_ref is None) != (self.top_p_token_offsets_ref is None):
            raise ValueError(
                "top_p_token_ids_ref 与 top_p_token_offsets_ref 必须成对出现"
                "（slime 同款约束：只有一半的 tape 不可重放）。"
            )

        expects_top_p_tape = (
            self.sampling_params.return_top_p_token_ids and self.sampling_params.top_p < 1.0
        )
        expects_routing_tape = self.sampling_params.return_routed_experts

        if self.capture_status == "complete":
            # 1. complete 的基线要求
            if self.response_token_count < 1:
                raise ValueError("capture_status=complete 要求 response_token_count >= 1。")
            if self.response_token_ids_ref is None:
                raise ValueError("capture_status=complete 时 response_token_ids_ref 必填。")
            if self.logprobs_ref is None:
                raise ValueError(
                    "capture_status=complete 时 logprobs_ref 必填"
                    "（缺逐 token logprob 的轮次最多算 partial）。"
                )
            if self.alignment_status != "aligned":
                raise ValueError(
                    f"capture_status=complete 要求 alignment_status=aligned，"
                    f"得到 {self.alignment_status}（未核对/对不上的捕获不许自称完整）。"
                )
            # 2/3. 请求了 tape 就必须真的捕到（防镜像静默降级，U-H 回归点）
            if expects_top_p_tape and self.top_p_token_ids_ref is None:
                raise ValueError(
                    "请求了 top-p tape（top_p<1.0 且 return_top_p_token_ids=True）但引用缺失："
                    "这是 stock SGLang 静默忽略的典型形态，capture_status 不允许为 complete。"
                )
            if expects_routing_tape and self.routed_experts_ref is None:
                raise ValueError(
                    "请求了 routing tape（return_routed_experts=True）但 routed_experts_ref 缺失，"
                    "capture_status 不允许为 complete。"
                )
        else:
            # partial / failed 不允许伪装成已对齐
            if self.alignment_status == "aligned":
                raise ValueError(
                    f"capture_status={self.capture_status} 与 alignment_status=aligned 矛盾："
                    "未完整捕获的轮次不可能通过全量对齐核对。"
                )
        return self
