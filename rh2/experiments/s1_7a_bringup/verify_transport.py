"""A2 全链证据：训练侧 rollout dump（--save-debug-rollout-data 的 .pt）与
治理侧 sidecar（TrajectoryProjection + capture tape 字节流）逐位核对。

核对四件事（每条交付样本）：

1. **loss mask 逐位**：训练 dump 的 loss_masks[i] == 投影 branch 的
   loss_mask_per_token（sampled ∧ role 语义，H4）；
2. **rollout logprob 逐位**：dump 的 rollout_log_probs[i] == capture tape
   （`cap_*_logprobs` 的 float64 小端字节流按 mask=1 段展开回填后的序列）；
3. **top-p tape 逐位（A2 消费面）**：dump 的 rollout_top_p_token_ids/offsets
   == 投影 SamplingMaskRef 指向的 artifact 字节流（int32 小端解码）；
4. **token 逐位**：dump tokens 的 response 段 mask=1 位置 == capture 的
   output_ids 按轮拼接。

用法（容器内，训练 step 完成后）::

    python verify_transport.py \
        --dump /root/bringup/rollout_dumps/rollout_0.pt \
        --artifacts /root/bringup/artifacts/rollouts \
        --out /root/bringup/artifacts/transport_verify.json
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

import torch


def index_sidecars(artifacts_root: Path) -> dict[str, dict]:
    """eligibility report_id -> sidecar 组（交付样本 metadata.eligibility_report_ref
    是与训练 dump 的唯一稳定连接键：TrajectoryManager 叶链 Sample 不带
    session_id，run6 实测 dump 里为 None）。"""

    by_report: dict[str, dict] = {}
    for candidate in sorted(artifacts_root.iterdir()):
        proj = candidate / "trajectory_projection.json"
        rep = candidate / "eligibility_report.json"
        if not (proj.exists() and rep.exists()):
            continue
        report = json.loads(rep.read_text())
        by_report[report["report_id"]] = {
            "dir": candidate,
            "projection": json.loads(proj.read_text()),
            "captures": json.loads((candidate / "capture_records.json").read_text()),
        }
    return by_report


def read_i32(path: Path) -> list[int]:
    payload = path.read_bytes()
    return list(struct.unpack(f"<{len(payload) // 4}i", payload))


def read_f64(path: Path) -> list[float]:
    payload = path.read_bytes()
    return list(struct.unpack(f"<{len(payload) // 8}d", payload))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dump", required=True)
    parser.add_argument("--artifacts", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    dump = torch.load(args.dump, map_location="cpu", weights_only=False)
    samples = dump["samples"] if isinstance(dump, dict) and "samples" in dump else dump
    by_report = index_sidecars(Path(args.artifacts))

    report: dict = {"dump": args.dump, "checked": [], "skipped": [], "all_ok": True}
    for entry in samples:
        # slime save_debug_rollout_data 存的是 Sample.to_dict() 列表或 Sample 对象
        get = entry.get if isinstance(entry, dict) else lambda k, d=None: getattr(entry, k, d)
        metadata = get("metadata") or {}
        sid = metadata.get("eligibility_report_ref")  # 交付样本的稳定连接键
        loss_mask = list(get("loss_mask") or [])
        if not sid or not any(loss_mask):
            report["skipped"].append(
                {
                    "index": get("index"),
                    "abort_reason": metadata.get("abort_reason"),
                    "reason": "removed_or_empty_mask" if not any(loss_mask) else "no_report_ref",
                }
            )
            continue
        side = by_report.get(sid)
        if side is None:
            report["checked"].append({"report_ref": sid, "ok": False, "why": "sidecar_missing"})
            report["all_ok"] = False
            continue

        tokens = list(get("tokens") or [])
        response_length = int(get("response_length") or 0)
        rollout_log_probs = [float(x) for x in (get("rollout_log_probs") or [])]
        top_p_ids = list(get("rollout_top_p_token_ids") or [])
        top_p_offsets = list(get("rollout_top_p_token_offsets") or [])

        # 多叶链（fan-out）：同一 trajectory 的多条 dump 样本共享 report_ref，
        # 且两条叶链的 loss mask 形状可能完全相同（run7 实测 idx=31 有两条
        # [1]*2048）——mask 相等只用来筛候选，最终用 token 同一性选中分支，
        # 已匹配的分支从候选池摘除（一对一消费）。
        side.setdefault("consumed_branches", set())
        response = tokens[-response_length:]
        mask_positions = [i for i, m in enumerate(loss_mask) if m == 1]
        tape_dir = side["dir"] / "tapes"
        captures_by_id = {record["record_id"]: record for record in side["captures"]}

        def branch_tapes(branch):
            cap_ids, cap_lps = [], []
            for record_id in branch["capture_record_refs"]:  # 分支入训轮（按序）
                record = captures_by_id[record_id]
                ids_ref = record.get("response_token_ids_ref")
                lp_ref = record.get("logprobs_ref")
                if ids_ref:
                    cap_ids.append(read_i32(tape_dir / f"{ids_ref['ref_id']}.bin"))
                if lp_ref:
                    cap_lps.append(read_f64(tape_dir / f"{lp_ref['ref_id']}.bin"))
            return (
                [t for turn in cap_ids for t in turn],
                [p for turn in cap_lps for p in turn],
            )

        proj_branch = None
        flat_cap_lps: list[float] = []
        mask_ok = token_ok = False
        for branch in side["projection"]["branches"]:
            if branch["branch_id"] in side["consumed_branches"]:
                continue
            prompt_len = branch["prompt_token_count"]
            candidate_mask = [0] * branch["response_token_count"]
            for span in branch["loss_mask_spans"]:
                # 契约座标系：span 平铺 [prompt, prompt+response)，换回 response 座标
                for i in range(span["start"] - prompt_len, span["end"] - prompt_len):
                    candidate_mask[i] = span["mask"]
            if candidate_mask != loss_mask:
                continue
            ids, lps = branch_tapes(branch)
            if [response[i] for i in mask_positions] == ids:
                proj_branch = branch
                flat_cap_lps = lps  # ids 已在上行比对消费（ruff F841）
                mask_ok = token_ok = True
                side["consumed_branches"].add(branch["branch_id"])
                break
        if proj_branch is None:
            report["checked"].append(
                {"report_ref": sid, "ok": False, "why": "no_branch_matches_dump_mask_and_tokens"}
            )
            report["all_ok"] = False
            continue

        # rollout_log_probs 与 loss_mask 同座标（response 全长），mask=1 位取值比对
        logprob_ok = (
            len(rollout_log_probs) == response_length
            and [rollout_log_probs[i] for i in mask_positions] == flat_cap_lps
        )

        # top-p tape：投影 sampling mask artifact 与训练 dump 双向逐位
        sm = proj_branch.get("sampling_mask") or {}
        ids_ref = sm.get("token_ids_ref") or {}
        off_ref = sm.get("offsets_ref") or {}
        top_p_ok = None
        if ids_ref and off_ref:
            proj_ids = read_i32(tape_dir / f"{ids_ref['ref_id']}.bin")
            proj_offsets = read_i32(tape_dir / f"{off_ref['ref_id']}.bin")
            top_p_ok = (
                proj_ids == [int(x) for x in top_p_ids]
                and proj_offsets == [int(x) for x in top_p_offsets]
                and len(top_p_offsets) == response_length + 1
            )
        routing = proj_branch.get("routing") or {}
        entry_report = {
            "report_ref": sid,
            "branch_id": proj_branch["branch_id"],
            "dump_index": get("index"),
            "response_length": response_length,
            "mask_ones": len(mask_positions),
            "capture_turns": len(proj_branch["capture_record_refs"]),
            "token_bitwise_ok": token_ok,
            "logprob_bitwise_ok": logprob_ok,
            "projection_mask_bitwise_ok": mask_ok,
            "top_p_tape_bitwise_ok": top_p_ok,
            "routing_alignment": routing.get("alignment"),
            "ok": bool(token_ok and logprob_ok and mask_ok and (top_p_ok is not False)),
        }
        report["checked"].append(entry_report)
        report["all_ok"] = report["all_ok"] and entry_report["ok"]

    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(
        f"checked={len(report['checked'])} skipped={len(report['skipped'])} all_ok={report['all_ok']}"
    )
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
