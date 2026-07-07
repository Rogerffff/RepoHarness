"""从 bring-up sidecar 重建 FinalizedRollout 并跑 S1-8 离线导出（导出记录样本）。

任务清单要求的"导出记录样本"产物：对一条**已交付**（offline_or_sft_candidate）
rollout 的治理 sidecar（eligibility/projection/grading/signal + tape 字节流）
重建 FinalizedRollout，经 `adapters/offline_export/export_rollouts` 走真实导出
链路（token 从 capture 原始 artifact 重建 + 逐轮前缀校验 + digest 重算），
产出 records.jsonl + artifacts/ + manifest.json。

sidecar 没有 scan_result（编排旁路只落四类 + capture），扫描是投影的确定性
纯函数，这里按 wrapper 同一实现重算（私有 import，实验脚本范围内可接受）。

用法（容器内）::

    python export_sample.py --rollout-dir /root/bringup/artifacts/rollouts/<id> \
        --out-dir /root/bringup/artifacts/export_sample
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from repoharness2.adapters.offline_export.exporter import OfflineExportInput, export_rollouts
from repoharness2.contracts import GenerationCaptureRecord, GradingReport, TrajectoryProjection
from repoharness2.contracts.eligibility import EligibilityReport
from repoharness2.governance import FinalizedRollout, GroupRepairSignal
from repoharness2.governance.projection_scan import _scan_public_projection


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rollout-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    root = Path(args.rollout_dir)

    projection = TrajectoryProjection.model_validate_json(
        (root / "trajectory_projection.json").read_text()
    )
    finalized = FinalizedRollout(
        grading_report=GradingReport.model_validate_json(
            (root / "grading_report.json").read_text()
        ),
        projection=projection,
        scan_result=_scan_public_projection(projection),  # 确定性重算（见 docstring）
        eligibility_report=EligibilityReport.model_validate_json(
            (root / "eligibility_report.json").read_text()
        ),
        group_repair_signal=GroupRepairSignal.model_validate_json(
            (root / "group_repair_signal.json").read_text()
        ),
    )
    captures = [
        GenerationCaptureRecord.model_validate(item)
        for item in json.loads((root / "capture_records.json").read_text())
    ]
    store = {
        path.stem: path.read_bytes() for path in (root / "tapes").glob("*.bin")
    }
    manifest = export_rollouts(
        [OfflineExportInput(finalized=finalized, capture_records=captures, artifact_store=store)],
        out_dir=args.out_dir,
    )
    print(
        json.dumps(
            {
                "record_count": manifest.record_count,
                "records": manifest.records,
                "records_jsonl_sha256": manifest.records_jsonl_sha256,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
