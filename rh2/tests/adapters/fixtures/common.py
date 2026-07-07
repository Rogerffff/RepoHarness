"""fixture 公共件：slime Sample 的 duck 型替身、tape 载荷生成器、capture 记录工厂。

FixtureSlimeSample 的字段名与 reference/slime/slime/utils/types.py 的 Sample
逐一对应（tokens/response_length/loss_mask/rollout_log_probs/
rollout_top_p_token_ids/rollout_top_p_token_offsets/rollout_routed_experts/
weight_versions/rollout_id/index/status/remove_sample/metadata），
project_from_slime 只按属性名 duck 型读取，不 import slime。
"""

from __future__ import annotations

import base64
import dataclasses
import struct
from typing import Any

from repoharness2.adapters.slime import (
    SlimeBranchAnnotation,
    SlimeRewardInput,
    project_from_slime,
)
from repoharness2.contracts import GenerationCaptureRecord

SHA_TEMPLATE = "sha256:" + "a" * 64
SHA_PROMPT = "sha256:" + "b" * 64
SHA_META = "sha256:" + "c" * 64
TS = "2026-07-07T09:30:25Z"


@dataclasses.dataclass
class FixtureSlimeSample:
    """slime.utils.types.Sample 的字段名快照（只含投影用到的子集）。"""

    tokens: list[int] = dataclasses.field(default_factory=list)
    response_length: int = 0
    loss_mask: list[int] | None = None
    rollout_log_probs: list[float] | None = None
    # tape 载荷保持 wire 弹性：list[int] / base64 str / None（与 slime 字段同名）
    rollout_top_p_token_ids: Any = None
    rollout_top_p_token_offsets: Any = None
    rollout_routed_experts: Any = None
    weight_versions: list[str] = dataclasses.field(default_factory=lambda: ["default"])
    rollout_id: int | None = None
    index: int | None = None
    status: str = "completed"
    remove_sample: bool = False
    metadata: dict = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class ProjectionInputs:
    """一组可直接喂给 project_from_slime 的输入（测试在副本上做局部破坏）。"""

    samples: list[FixtureSlimeSample]
    capture_dicts: list[dict]
    annotations: list[SlimeBranchAnnotation]
    reward: SlimeRewardInput
    kwargs: dict

    def capture_records(self) -> list[GenerationCaptureRecord]:
        return [GenerationCaptureRecord.model_validate(d) for d in self.capture_dicts]

    def project(self, **overrides):
        samples = overrides.pop("samples", self.samples)
        capture_records = overrides.pop("capture_records", None)
        if capture_records is None:
            capture_records = self.capture_records()
        annotations = overrides.pop("annotations", self.annotations)
        reward = overrides.pop("reward", self.reward)
        kwargs = {**self.kwargs, **overrides}
        return project_from_slime(
            samples, capture_records, annotations=annotations, reward=reward, **kwargs
        )


def b64_int32(values: list[int]) -> str:
    """把 int 列表编码成 SGLang meta_info 同款 base64 int32 小端字节串。"""

    return base64.b64encode(struct.pack(f"<{len(values)}i", *values)).decode("ascii")


def routing_flat(rows: int, layers: int, topk: int) -> list[int]:
    """确定性生成 [rows, layers, topk] 的扁平 routing tape（专家 id 0..127）。"""

    return [(i * 13 + 7) % 128 for i in range(rows * layers * topk)]


def topp_offsets(per_token_kept: list[int]) -> list[int]:
    """按每个 response token 的核集合大小生成 ragged offsets（长度 = token 数 + 1）。

    例：16 个 token、核集合大小 9x4 + 7x3 → offsets 长 17、末位 57
    （对齐 uh_probe_result.json：top_p_token_offsets_len=17）。
    """

    offsets = [0]
    for kept in per_token_kept:
        offsets.append(offsets[-1] + kept)
    return offsets


def capture_record_dict(
    *,
    record_id: str,
    turn_id: str,
    trajectory_id: str,
    model_name: str,
    prompt_token_count: int,
    response_token_count: int,
    top_p: float = 0.95,
    return_top_p_token_ids: bool = True,
    return_routed_experts: bool = True,
    renderer_cls_name: str = "Qwen3Renderer",
    tokenizer_name: str = "Qwen/Qwen3-30B-A3B",
) -> dict:
    """complete/aligned 的 GenerationCaptureRecord JSON 形态（测试可局部改坏）。"""

    has_top_p_tape = return_top_p_token_ids and top_p < 1.0
    return {
        "schema_id": "rh2.generation_capture_record.v1",
        "record_id": record_id,
        "request_id": f"req_{record_id}",
        "turn_id": turn_id,
        "trajectory_id": trajectory_id,
        "model_name": model_name,
        "backend_name": "sglang",
        "backend_version": "0.5.9",
        "sampling_params": {
            "temperature": 1.0,
            "top_p": top_p,
            "max_new_tokens": max(response_token_count, 1),
            "return_top_p_token_ids": return_top_p_token_ids,
            "return_routed_experts": return_routed_experts,
        },
        "renderer_cls_name": renderer_cls_name,
        "tokenizer_name": tokenizer_name,
        "template_hash": SHA_TEMPLATE,
        "prompt_token_count": prompt_token_count,
        "response_token_count": response_token_count,
        "prompt_token_ids_ref": {"ref_id": f"{record_id}_prompt_ids"},
        "prompt_token_ids_sha256": SHA_PROMPT,
        "response_token_ids_ref": {"ref_id": f"{record_id}_output_ids"},
        "raw_meta_info_digest": SHA_META,
        "logprobs_ref": {"ref_id": f"{record_id}_logprobs"},
        "top_p_token_ids_ref": {"ref_id": f"{record_id}_topp_ids"} if has_top_p_tape else None,
        "top_p_token_offsets_ref": (
            {"ref_id": f"{record_id}_topp_offsets"} if has_top_p_tape else None
        ),
        "routed_experts_ref": (
            {"ref_id": f"{record_id}_routing"} if return_routed_experts else None
        ),
        "capture_status": "complete",
        "alignment_status": "aligned",
        "captured_at_utc": TS,
    }


def degrade_capture_to_partial(capture: dict, *, drop_top_p_tape: bool = True) -> dict:
    """把 complete 记录改成"请求了 tape 但没捕到"的 partial 形态（U-H 回归形态）。

    对齐 capture 层禁令：此时 capture_status 不允许 complete，alignment 不允许
    aligned——这是 stock SGLang 静默忽略 custom_params 时捕获层的如实记法。
    """

    degraded = dict(capture)
    if drop_top_p_tape:
        degraded["top_p_token_ids_ref"] = None
        degraded["top_p_token_offsets_ref"] = None
    degraded["capture_status"] = "partial"
    degraded["alignment_status"] = "not_checked"
    return degraded
