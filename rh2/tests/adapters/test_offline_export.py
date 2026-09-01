"""离线导出器（S1-8）单测：资格门拒收、token 重建校验、digest 清单、幂等。

FinalizedRollout 来源 = experiments/s1_parity.py 的 S1-6 mock 链（importlib 按
路径加载；真实代码路径——capture 钩子/回填/投影/finalize_rollout——全部走生产
模块，与 tests/adapters/test_slime_generate.py 同一 mock 纪律）。
"""

import asyncio
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path

import pytest

from repoharness2.adapters.offline_export import (
    OfflineExportError,
    OfflineExportInput,
    export_rollouts,
)
from repoharness2.contracts import SCHEMA_REGISTRY, ArtifactRef

_SCRIPT = Path(__file__).resolve().parents[2] / "experiments" / "s1_parity.py"
_spec = importlib.util.spec_from_file_location("rh2_s1_parity_for_export_tests", _SCRIPT)
parity = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = parity  # dataclass 解析字符串注解需要模块已注册
_spec.loader.exec_module(parity)


def run_chain(*, moe: bool = False, infra_grading: bool = False):
    """跑一条 mock 链，返回 (delivered_samples, audit, hook)。"""

    chain = parity.build_chain(moe=moe, infra_grading=infra_grading)
    delivered = asyncio.run(parity._run_chain(chain))
    audit = chain.orchestrator.audits[-1]
    hook = chain.adapter_ref["adapter"].hook
    return delivered, audit, hook


def export_input(audit, hook, **overrides) -> OfflineExportInput:
    kwargs = {
        "finalized": audit.finalized,
        "capture_records": list(hook.records),
        "artifact_store": dict(hook.artifact_store),
    }
    kwargs.update(overrides)
    return OfflineExportInput(**kwargs)


# ---------------------------------------------------------------------------
# 正常路径：落盘产物 + digest 清单 + schema 校验
# ---------------------------------------------------------------------------


def test_export_writes_records_artifacts_and_manifest(tmp_path):
    delivered, audit, hook = run_chain()
    manifest = export_rollouts(
        [export_input(audit, hook)], out_dir=tmp_path, exported_at_utc=parity.EXPORT_STAMP
    )
    assert manifest.record_count == 1

    # records.jsonl 的行必须能按 SCHEMA_REGISTRY 走通严格校验（inspector 同路径）
    line = (tmp_path / "records.jsonl").read_text().splitlines()[0]
    payload = json.loads(line)
    record = SCHEMA_REGISTRY[payload["schema_id"]].model_validate(payload)
    assert record.training_eligibility_class == "online_policy_loss_eligible"  # A3：无封顶（T1 oracle 改动）
    assert record.exporter_version == "rh2.offline_export.s1.v1"
    assert record.offline_filter_report_ref is None  # §2：导出时挂点为空

    # 三类 payload 落盘且 digest 与 manifest / 记录内引用逐一命中
    (branch,) = record.branches
    for ref in (branch.token_ids_ref, branch.loss_mask_ref, branch.rollout_logprobs_ref):
        path = tmp_path / "artifacts" / f"{ref.ref_id}.bin"
        payload_bytes = path.read_bytes()
        assert len(payload_bytes) == ref.byte_size
        assert "sha256:" + hashlib.sha256(payload_bytes).hexdigest() == ref.sha256
        assert manifest.artifacts[ref.ref_id] == ref.sha256

    # 在线交付面与导出面的派生视图键一致（parity-core 的最小面）
    (leaf,) = delivered
    assert leaf.metadata["eligibility_report_ref"] == record.eligibility_report_ref
    exported_tokens = list(
        struct.unpack(
            f"<{branch.token_ids_ref.byte_size // 4}i",
            (tmp_path / "artifacts" / f"{branch.token_ids_ref.ref_id}.bin").read_bytes(),
        )
    )
    assert exported_tokens == list(leaf.tokens)


def test_export_is_idempotent_byte_for_byte(tmp_path):
    _, audit, hook = run_chain()
    first = export_rollouts(
        [export_input(audit, hook)], out_dir=tmp_path / "a", exported_at_utc=parity.EXPORT_STAMP
    )
    second = export_rollouts(
        [export_input(audit, hook)], out_dir=tmp_path / "b", exported_at_utc=parity.EXPORT_STAMP
    )
    assert first.to_json_dict() == second.to_json_dict()
    assert (tmp_path / "a" / "records.jsonl").read_bytes() == (tmp_path / "b" / "records.jsonl").read_bytes()
    assert (tmp_path / "a" / "manifest.json").read_bytes() == (tmp_path / "b" / "manifest.json").read_bytes()
    # 同目录重导出 = 覆盖写，不追加
    again = export_rollouts(
        [export_input(audit, hook)], out_dir=tmp_path / "a", exported_at_utc=parity.EXPORT_STAMP
    )
    assert again.records_jsonl_sha256 == first.records_jsonl_sha256
    assert len((tmp_path / "a" / "records.jsonl").read_text().splitlines()) == 1


# ---------------------------------------------------------------------------
# 资格门：audit 档直接拒（第一道防线；第二道是 schema 不可表示，见 test_export.py）
# ---------------------------------------------------------------------------


def test_audit_tier_refused_directly(tmp_path):
    """infra 评分 -> gate 双维失败 -> audit 档 -> 导出器 fail-closed。"""

    _, audit, hook = run_chain(infra_grading=True)
    assert audit.finalized.eligibility_report.eligibility_class == "audit_only_or_rejected"
    with pytest.raises(OfflineExportError, match=r"^\[audit_tier_not_exportable\]"):
        export_rollouts(
            [export_input(audit, hook)], out_dir=tmp_path, exported_at_utc=parity.EXPORT_STAMP
        )


# ---------------------------------------------------------------------------
# token 事实链 fail-closed：payload 缺失 / digest 不符 / 重建不一致 / 记录不全
# ---------------------------------------------------------------------------


def test_missing_payload_refused(tmp_path):
    _, audit, hook = run_chain()
    store = dict(hook.artifact_store)
    victim = next(ref_id for ref_id in store if ref_id.endswith("_output_ids"))
    del store[victim]
    with pytest.raises(OfflineExportError, match=r"^\[artifact_payload_missing\]"):
        export_rollouts(
            [export_input(audit, hook, artifact_store=store)],
            out_dir=tmp_path,
            exported_at_utc=parity.EXPORT_STAMP,
        )


def test_tampered_payload_digest_mismatch_refused(tmp_path):
    """payload 被改动但引用 digest 未变：重算比对当场拒收。"""

    _, audit, hook = run_chain()
    store = dict(hook.artifact_store)
    victim = next(ref_id for ref_id in store if ref_id.endswith("_output_ids"))
    store[victim] = store[victim][:-4] + struct.pack("<i", 999999)
    with pytest.raises(OfflineExportError, match=r"^\[artifact_digest_mismatch\]"):
        export_rollouts(
            [export_input(audit, hook, artifact_store=store)],
            out_dir=tmp_path,
            exported_at_utc=parity.EXPORT_STAMP,
        )


def test_token_reconstruction_mismatch_refused(tmp_path):
    """digest 自洽但内容与轮次链矛盾的 payload：前缀校验拒收。

    构造方式：把第 0 轮 prompt payload 换成另一串 int32 并同步换引用 digest
    （模拟"存储层张冠李戴但对象自洽"的形态）——重建序列的前缀校验必须抓住它。
    """

    _, audit, hook = run_chain()
    store = dict(hook.artifact_store)
    record0 = hook.records[0]
    tampered = struct.pack(f"<{record0.prompt_token_count}i", *range(9000, 9000 + record0.prompt_token_count))
    ref_id = record0.prompt_token_ids_ref.ref_id
    store[ref_id] = tampered
    fixed_record = record0.model_copy(
        update={
            "prompt_token_ids_ref": ArtifactRef(
                ref_id=ref_id,
                sha256="sha256:" + hashlib.sha256(tampered).hexdigest(),
                byte_size=len(tampered),
            )
        }
    )
    records = [fixed_record] + list(hook.records[1:])
    with pytest.raises(OfflineExportError, match=r"^\[token_reconstruction_mismatch\]"):
        export_rollouts(
            [export_input(audit, hook, capture_records=records, artifact_store=store)],
            out_dir=tmp_path,
            exported_at_utc=parity.EXPORT_STAMP,
        )


def test_missing_capture_record_refused(tmp_path):
    _, audit, hook = run_chain()
    with pytest.raises(OfflineExportError, match=r"^\[capture_record_missing_for_export\]"):
        export_rollouts(
            [export_input(audit, hook, capture_records=list(hook.records[:1]))],
            out_dir=tmp_path,
            exported_at_utc=parity.EXPORT_STAMP,
        )


def test_partial_capture_record_refused(tmp_path):
    """回链记录非 complete：token_faithful 导出的凭据不成立。"""

    _, audit, hook = run_chain()
    degraded = hook.records[0].model_copy(
        update={"capture_status": "partial", "alignment_status": "not_checked"}
    )
    records = [degraded] + list(hook.records[1:])
    with pytest.raises(OfflineExportError, match=r"^\[capture_record_not_complete_for_export\]"):
        export_rollouts(
            [export_input(audit, hook, capture_records=records)],
            out_dir=tmp_path,
            exported_at_utc=parity.EXPORT_STAMP,
        )


def test_duplicate_trajectory_in_batch_refused(tmp_path):
    _, audit, hook = run_chain()
    with pytest.raises(OfflineExportError, match=r"^\[duplicate_trajectory_in_batch\]"):
        export_rollouts(
            [export_input(audit, hook), export_input(audit, hook)],
            out_dir=tmp_path,
            exported_at_utc=parity.EXPORT_STAMP,
        )


def test_empty_batch_refused(tmp_path):
    with pytest.raises(OfflineExportError, match=r"^\[no_rollouts_to_export\]"):
        export_rollouts([], out_dir=tmp_path)
