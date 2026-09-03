"""离线导出器（S1-8）：FinalizedRollout -> TrainingExportRecord + jsonl + digest 清单。

输入纪律（治理层唯一关口的下游）：本模块**只吃 gate 之后的 FinalizedRollout**
（`governance.wrapper.finalize_rollout` 的返回值）——它内含 EligibilityReport /
GradingReport / TrajectoryProjection / GroupRepairSignal 四件套且 trajectory_id
已互检。任何绕过 finalize_rollout 的裸投影都没有资格结论，本模块拒绝提供
"补一份资格"的旁路。

历史第二道门槛"`scan_result.clean` 否则 `projection_scan_not_clean`"已按决策包 D2-4
（2026-09-04 owner 已批）删除：TrajectoryProjection 不是模型可见面，其 marker 扫描既不是
资格语义也不该在导出侧重复把关（`FinalizedRollout` 已无 `scan_result`）。

资格门（双道防线）：

1. 导出器显式拒绝：`eligibility_class == "audit_only_or_rejected"` 直接抛
   OfflineExportError(reason_code="audit_tier_not_exportable")；
2. schema 层不可表示：TrainingExportRecord.training_eligibility_class 的
   Literal 里根本没有 audit 值（contracts/export.py）。

token 逐位保真（parity-core 的证据基础）：导出器不信任任何中间转述，token
payload 从 GenerationCaptureRecord 的原始捕获 artifact **重建并逐位校验**：

    1. 每个被回链 capture 记录必须在场且 capture_status="complete"；
    2. payload 按 ArtifactRef.ref_id 从 artifact_store 取字节流，重算 sha256
       与引用 digest 比对（差一位即拒）；
    3. 分支 token 序列 = 最后一轮 prompt_ids + 最后一轮 output_ids（线性
       追加式多轮的不变量：末轮 prompt 是全序列前缀）；随后逐轮验证
       (a) 每轮 prompt_ids 恰为重建序列的前缀（长度=该轮 prompt_token_count），
       (b) 每个 mask=1 连续段的 token 恰等于对应轮次的 output_ids。
       具体数值例（S1-6 dense mock 链）：prompt 12 + 生成 10 + 工具 5 + 生成 8，
       末轮 prompt 27 token + 末轮输出 8 token 重建出 35 token 全序列；
       mask=1 段 [12,22) 必须逐位等于第 0 轮 output_ids、[27,35) 等于第 1 轮。
    4. compaction/分叉分支（lineage 非 None）当前显式拒绝——重放前缀的重建
       需要树侧血缘信息，S1-8 不实现，绝不静默给出可能错位的 token。

幂等与 digest 清单：同一批输入（含显式 exported_at_utc）重复导出，records.jsonl
与 manifest.json 逐字节相同；manifest 记录每条 record 的规范化 digest、每个
payload artifact 的 sha256 与 records.jsonl 全文 digest，inspector/离线消费方
可全量重算比对。
"""

from __future__ import annotations

import hashlib
import json
import struct
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repoharness2.contracts import (
    ArtifactRef,
    GenerationCaptureRecord,
    TrainingExportRecord,
    canonical_json_digest,
)
from repoharness2.contracts.export import ExportBranchTokens
from repoharness2.contracts.trajectory import BranchProjection
from repoharness2.governance import FinalizedRollout

__all__ = [
    "EXPORTER_VERSION",
    "ExportManifest",
    "OfflineExportError",
    "OfflineExportInput",
    "build_training_export_record",
    "export_rollouts",
]

# 导出器版本（warm-start 文档 §4 的 analyzer version 纪律：改导出语义必须升版本，
# 让两个版本产出的 records.jsonl 永远可区分）。
EXPORTER_VERSION = "rh2.offline_export.s1.v1"

MANIFEST_FILENAME = "manifest.json"
RECORDS_FILENAME = "records.jsonl"
ARTIFACTS_DIRNAME = "artifacts"


class OfflineExportError(RuntimeError):
    """导出层 fail-closed 拒绝（reason_code 机器可读，单测与上游按它分支）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


@dataclass(frozen=True)
class OfflineExportInput:
    """一条 rollout 的导出输入三件套。

    - finalized：治理关口产物（资格结论 + 投影 + 评分 + 扫描）；
    - capture_records：本轨迹全部 GenerationCaptureRecord（FinalizedRollout
      刻意不内嵌它们——A4 sidecar 独立存放，导出时显式传入）；
    - artifact_store：ref_id -> 原始字节流（S1-6 的 GenerationCaptureHook.
      artifact_store 就是这个形态；离线场景可用读目录的 Mapping 适配）。
    """

    finalized: FinalizedRollout
    capture_records: Sequence[GenerationCaptureRecord]
    artifact_store: Mapping[str, bytes]


@dataclass(frozen=True)
class ExportManifest:
    """一次批量导出的 digest 清单（manifest.json 的内存形态）。"""

    exporter_version: str
    record_count: int
    records: list[dict[str, str]]  # [{record_id, trajectory_id, task_id, sha256}]
    artifacts: dict[str, str]  # ref_id -> sha256:<hex>
    records_jsonl_sha256: str

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "manifest_schema": "rh2.offline_export_manifest.v1",
            "exporter_version": self.exporter_version,
            "record_count": self.record_count,
            "records": self.records,
            "artifacts": dict(sorted(self.artifacts.items())),
            "records_jsonl_sha256": self.records_jsonl_sha256,
        }


def _sha256(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _resolve_payload(
    ref: ArtifactRef | None, *, field_name: str, store: Mapping[str, bytes]
) -> bytes:
    """按引用取原始字节流并重算 digest 比对（防转述、防篡改）。"""

    if ref is None:
        raise OfflineExportError(
            "capture_artifact_ref_missing", f"{field_name} 引用缺失，token 事实链断裂。"
        )
    payload = store.get(ref.ref_id)
    if payload is None:
        raise OfflineExportError(
            "artifact_payload_missing",
            f"{field_name} 的 payload（ref_id={ref.ref_id!r}）不在 artifact_store 里。",
        )
    if ref.sha256 is not None and _sha256(payload) != ref.sha256:
        raise OfflineExportError(
            "artifact_digest_mismatch",
            f"{field_name}（ref_id={ref.ref_id!r}）字节流 digest 与引用申明不符"
            "（payload 被改动或存储层取错对象）。",
        )
    return payload


def _decode_int32(payload: bytes, *, field_name: str) -> list[int]:
    if len(payload) % 4 != 0:
        raise OfflineExportError(
            "artifact_payload_not_int32", f"{field_name} 字节数 {len(payload)} 不是 4 的倍数。"
        )
    return list(struct.unpack(f"<{len(payload) // 4}i", payload))


def _decode_f64(payload: bytes, *, field_name: str) -> list[float]:
    if len(payload) % 8 != 0:
        raise OfflineExportError(
            "artifact_payload_not_f64", f"{field_name} 字节数 {len(payload)} 不是 8 的倍数。"
        )
    return list(struct.unpack(f"<{len(payload) // 8}d", payload))


def _dense_loss_mask(branch: BranchProjection) -> list[int]:
    """LossMaskSpan（response 段平铺，全序列座标）展开成逐 token 0/1 向量。"""

    mask = [0] * branch.response_token_count
    for span in branch.loss_mask_spans:
        for pos in range(span.start, span.end):
            mask[pos - branch.prompt_token_count] = span.mask
    return mask


def _mask1_runs(mask: Sequence[int]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    for idx, value in enumerate(mask):
        if value == 1:
            if runs and runs[-1][1] == idx:
                runs[-1] = (runs[-1][0], idx + 1)
            else:
                runs.append((idx, idx + 1))
    return runs


def _reconstruct_branch_tokens(
    branch: BranchProjection,
    records: Sequence[GenerationCaptureRecord],
    store: Mapping[str, bytes],
) -> tuple[list[int], list[int], list[float] | None]:
    """从原始捕获 artifact 重建并逐位校验分支 (tokens, loss_mask, logprobs)。

    模块 docstring 第 3 条的实现。任何一步对不上都拒绝导出——宁可少导一条，
    不导一条 token 可能错位的记录。
    """

    branch_name = f"branch {branch.branch_id}"
    turns: list[dict[str, Any]] = []
    for record in records:
        prompt_ids = _decode_int32(
            _resolve_payload(
                record.prompt_token_ids_ref,
                field_name=f"{record.record_id}.prompt_token_ids_ref",
                store=store,
            ),
            field_name=f"{record.record_id}.prompt_token_ids",
        )
        output_ids = _decode_int32(
            _resolve_payload(
                record.response_token_ids_ref,
                field_name=f"{record.record_id}.response_token_ids_ref",
                store=store,
            ),
            field_name=f"{record.record_id}.response_token_ids",
        )
        if len(prompt_ids) != record.prompt_token_count or len(output_ids) != record.response_token_count:
            raise OfflineExportError(
                "capture_payload_count_mismatch",
                f"{record.record_id} 的 payload 长度与记录计数不符：prompt "
                f"{len(prompt_ids)}/{record.prompt_token_count}，response "
                f"{len(output_ids)}/{record.response_token_count}。",
            )
        logprobs: list[float] | None = None
        if record.logprobs_ref is not None:
            logprobs = _decode_f64(
                _resolve_payload(
                    record.logprobs_ref,
                    field_name=f"{record.record_id}.logprobs_ref",
                    store=store,
                ),
                field_name=f"{record.record_id}.logprobs",
            )
            if len(logprobs) != record.response_token_count:
                raise OfflineExportError(
                    "capture_payload_count_mismatch",
                    f"{record.record_id} 的 logprobs 长度 {len(logprobs)} != "
                    f"response_token_count {record.response_token_count}。",
                )
        turns.append({"record": record, "prompt": prompt_ids, "output": output_ids, "logprobs": logprobs})

    # 线性追加式多轮的不变量：末轮 prompt 是全序列前缀，全序列 = 末轮 prompt + 末轮输出。
    last = turns[-1]
    tokens: list[int] = list(last["prompt"]) + list(last["output"])
    total = branch.prompt_token_count + branch.response_token_count
    if len(tokens) != total:
        raise OfflineExportError(
            "token_reconstruction_mismatch",
            f"{branch_name}：末轮 prompt({len(last['prompt'])}) + 末轮输出({len(last['output'])}) "
            f"= {len(tokens)} token，与分支申报 prompt+response = {total} 不符"
            "（非线性追加形态——compaction/REALIGN 的重建需要树侧血缘，S1-8 拒绝）。",
        )
    if len(turns[0]["prompt"]) != branch.prompt_token_count:
        raise OfflineExportError(
            "token_reconstruction_mismatch",
            f"{branch_name}：首轮 prompt {len(turns[0]['prompt'])} token 与分支 "
            f"prompt_token_count {branch.prompt_token_count} 不符。",
        )
    for turn in turns:
        prompt_ids = turn["prompt"]
        if tokens[: len(prompt_ids)] != prompt_ids:
            raise OfflineExportError(
                "token_reconstruction_mismatch",
                f"{branch_name}：轮 {turn['record'].record_id} 的 prompt_ids 不是重建序列的前缀"
                "（多轮上下文被改写过，线性重建不成立）。",
            )

    loss_mask = _dense_loss_mask(branch)
    runs = _mask1_runs(loss_mask)
    if len(runs) != len(turns):
        raise OfflineExportError(
            "trainable_runs_vs_turns_mismatch",
            f"{branch_name}：mask=1 连续段 {len(runs)} 个与回链轮次 {len(turns)} 个不等"
            "（轮次归属无法一一对应，token 身份校验不可能完成）。",
        )
    logprobs_dense: list[float] | None = [0.0] * branch.response_token_count
    for (start, end), turn in zip(runs, turns):
        output_ids = turn["output"]
        if end - start != len(output_ids):
            raise OfflineExportError(
                "trainable_runs_vs_turns_mismatch",
                f"{branch_name}：mask=1 段 [{start},{end}) 长 {end - start} 与轮 "
                f"{turn['record'].record_id} 的输出 {len(output_ids)} token 不等。",
            )
        segment = tokens[branch.prompt_token_count + start : branch.prompt_token_count + end]
        if segment != output_ids:
            raise OfflineExportError(
                "token_reconstruction_mismatch",
                f"{branch_name}：mask=1 段 [{start},{end}) 的重建 token 与轮 "
                f"{turn['record'].record_id} 的原始 output_ids 逐位不符。",
            )
        if logprobs_dense is not None and turn["logprobs"] is not None:
            logprobs_dense[start:end] = turn["logprobs"]
        else:
            logprobs_dense = None  # 任一轮缺 logprob 就整支显式缺失，不许补零伪装
    return tokens, loss_mask, logprobs_dense


def build_training_export_record(
    item: OfflineExportInput,
    *,
    payload_sink: dict[str, bytes],
    exported_at_utc: datetime | None = None,
) -> TrainingExportRecord:
    """把一条 gate 之后的 rollout 构造成导出记录，token payload 写入 payload_sink。

    fail-closed 拒绝清单（reason_code）：
    - audit_tier_not_exportable：资格档为 audit_only_or_rejected（第一道防线；
      第二道在 schema——TrainingExportRecord 根本表示不了 audit 值）；
    - lineage_reconstruction_not_supported：compaction/分叉分支；
    - capture_record_missing_for_export / capture_record_not_complete_for_export；
    - artifact_payload_missing / artifact_digest_mismatch / token_reconstruction_mismatch
      / trainable_runs_vs_turns_mismatch（见 _reconstruct_branch_tokens）。
    """

    finalized = item.finalized
    report = finalized.eligibility_report
    projection = finalized.projection

    if report.eligibility_class == "audit_only_or_rejected":
        raise OfflineExportError(
            "audit_tier_not_exportable",
            f"轨迹 {report.trajectory_id} 的资格档是 audit_only_or_rejected"
            f"（reason_codes={report.reason_codes}）——离线导出只接受 "
            "offline_or_sft_candidate 及以上（warm-start 文档 §2 的入口条件）。",
        )
    records_by_id = {record.record_id: record for record in item.capture_records}
    branches: list[ExportBranchTokens] = []
    for branch in projection.branches:
        if branch.lineage is not None:
            raise OfflineExportError(
                "lineage_reconstruction_not_supported",
                f"分支 {branch.branch_id} 带 compaction/分叉血缘：重放前缀的 token 重建"
                "需要树侧信息，S1-8 显式拒绝（绝不静默导出可能错位的 token）。",
            )
        linked: list[GenerationCaptureRecord] = []
        for ref in branch.capture_record_refs:
            record = records_by_id.get(ref)
            if record is None:
                raise OfflineExportError(
                    "capture_record_missing_for_export",
                    f"分支 {branch.branch_id} 回链的 capture 记录 {ref!r} 未随导出输入提供。",
                )
            if record.capture_status != "complete":
                raise OfflineExportError(
                    "capture_record_not_complete_for_export",
                    f"分支 {branch.branch_id} 回链的 capture 记录 {ref!r} 是 "
                    f"{record.capture_status}——非 complete 捕获支撑不了 token_faithful 导出。",
                )
            linked.append(record)

        tokens, loss_mask, logprobs = _reconstruct_branch_tokens(
            branch, linked, item.artifact_store
        )

        prefix = f"texp_{projection.trajectory_id}_{branch.branch_id}"
        token_payload = struct.pack(f"<{len(tokens)}i", *tokens)
        mask_payload = struct.pack(f"<{len(loss_mask)}i", *loss_mask)
        payload_sink[f"{prefix}_tokens"] = token_payload
        payload_sink[f"{prefix}_loss_mask"] = mask_payload
        logprobs_ref = None
        if logprobs is not None:
            lp_payload = struct.pack(f"<{len(logprobs)}d", *logprobs)
            payload_sink[f"{prefix}_logprobs"] = lp_payload
            logprobs_ref = ArtifactRef(
                ref_id=f"{prefix}_logprobs", sha256=_sha256(lp_payload), byte_size=len(lp_payload)
            )
        branches.append(
            ExportBranchTokens(
                branch_id=branch.branch_id,
                prompt_token_count=branch.prompt_token_count,
                response_token_count=branch.response_token_count,
                trainable_token_count=sum(loss_mask),
                token_ids_ref=ArtifactRef(
                    ref_id=f"{prefix}_tokens", sha256=_sha256(token_payload), byte_size=len(token_payload)
                ),
                loss_mask_ref=ArtifactRef(
                    ref_id=f"{prefix}_loss_mask", sha256=_sha256(mask_payload), byte_size=len(mask_payload)
                ),
                rollout_logprobs_ref=logprobs_ref,
                capture_record_refs=list(branch.capture_record_refs),
            )
        )

    return TrainingExportRecord(
        record_id=f"texp_{projection.trajectory_id}",
        trajectory_id=projection.trajectory_id,
        task_id=projection.task_id,
        source_framework=projection.source_framework,
        source_object_ref=projection.source_object_ref,
        exporter_version=EXPORTER_VERSION,
        projection_digest=canonical_json_digest(projection.model_dump(mode="json")),
        eligibility_report_ref=report.report_id,
        training_eligibility_class=report.eligibility_class,  # audit 在上面已拒，schema 再锁一遍
        eligibility_facts_digest=report.facts_digest,
        gate_version=report.gate_version,
        grading_report_ref=finalized.grading_report.report_id,
        reward_facts=projection.reward_facts,
        renderer_cls_name=projection.renderer_cls_name,
        tokenizer_name=projection.tokenizer_name,
        chat_template_hash=projection.chat_template_hash,
        branches=branches,
        offline_filter_report_ref=None,  # §2：导出时为空，离线过滤作业之后才回填
        exported_at_utc=exported_at_utc or datetime.now(timezone.utc),
    )


def _canonical_record_line(record: TrainingExportRecord) -> str:
    """记录的规范化 JSON 行（与 canonical_json_digest 同一序列化规则，digest 可直接重算）。"""

    return json.dumps(
        record.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )


def export_rollouts(
    items: Sequence[OfflineExportInput],
    *,
    out_dir: Path | str,
    exported_at_utc: datetime | None = None,
) -> ExportManifest:
    """批量导出：records.jsonl + artifacts/<ref_id>.bin + manifest.json。

    幂等语义：同一批输入 + 同一显式 exported_at_utc，重复调用产出逐字节相同的
    三类文件（覆盖写，不追加）；默认 exported_at_utc=None 时取当前 UTC 一次、
    整批共用（需要可复现导出的调用方——如 parity 脚本——显式传固定时间戳）。
    """

    if not items:
        raise OfflineExportError("no_rollouts_to_export", "导出输入为空。")
    stamp = exported_at_utc or datetime.now(timezone.utc)
    root = Path(out_dir)
    artifacts_dir = root / ARTIFACTS_DIRNAME
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    payloads: dict[str, bytes] = {}
    records: list[TrainingExportRecord] = []
    seen_trajectories: set[str] = set()
    for item in items:
        record = build_training_export_record(
            item, payload_sink=payloads, exported_at_utc=stamp
        )
        if record.trajectory_id in seen_trajectories:
            raise OfflineExportError(
                "duplicate_trajectory_in_batch",
                f"轨迹 {record.trajectory_id} 在同一批导出中出现两次（记录会互相覆盖）。",
            )
        seen_trajectories.add(record.trajectory_id)
        records.append(record)

    lines = [_canonical_record_line(record) for record in records]
    jsonl_text = "".join(line + "\n" for line in lines)
    (root / RECORDS_FILENAME).write_text(jsonl_text, encoding="utf-8")
    for ref_id, payload in sorted(payloads.items()):
        (artifacts_dir / f"{ref_id}.bin").write_bytes(payload)

    manifest = ExportManifest(
        exporter_version=EXPORTER_VERSION,
        record_count=len(records),
        records=[
            {
                "record_id": record.record_id,
                "trajectory_id": record.trajectory_id,
                "task_id": record.task_id,
                "sha256": canonical_json_digest(record.model_dump(mode="json")),
            }
            for record in records
        ],
        artifacts={ref_id: _sha256(payload) for ref_id, payload in payloads.items()},
        records_jsonl_sha256=_sha256(jsonl_text.encode("utf-8")),
    )
    (root / MANIFEST_FILENAME).write_text(
        json.dumps(manifest.to_json_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
