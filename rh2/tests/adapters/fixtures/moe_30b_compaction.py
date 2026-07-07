"""fixture (a)：Qwen3-30B-A3B 风格 MoE 产物——一 session 两叶链（compaction 分叉）。

形状语义严格参照 s1/uh_probe_result.json：

- 分支 b0（分叉前的原始叶链，恰为 S1-0 探针形状）：prompt 15 token、生成 16
  token、top-p offsets 长 17（末位 57）、routing tape [30, 48, 8]（30 = 15-1+16）。
- 分支 b1（compaction 续写叶链，多轮）：压缩后 prompt 22 token（父前缀重放在
  prompt 段），response 27 = 生成 12 + 工具 6 + 生成 9；top-p offsets 长 28
  （工具段是 6 个零宽 pad，slime `_pad_rollout_top_p_offsets` 语义）；
  routing tape [48, 48, 8]（48 = 22-1+27 = len(tokens)-1，多轮行数守恒）。

capture 记录三条：cap_t1 支撑 b0；cap_t2（prompt 22/生成 12）、cap_t3
（prompt 40/生成 9）支撑 b1。tape 载荷刻意混用 wire 形态：b0 的 ids 是 base64、
offsets 是 list；b1 全 base64——两条路径都要过唯一解码点。
"""

from __future__ import annotations

from repoharness2.adapters.slime import SlimeBranchAnnotation, SlimeRewardInput
from repoharness2.contracts import CompactedSubTraceLineage

from fixtures.common import (
    FixtureSlimeSample,
    ProjectionInputs,
    b64_int32,
    capture_record_dict,
    routing_flat,
    topp_offsets,
)

TRAJECTORY_ID = "traj_moe_0001"
TASK_ID = "django__django-11099"
MODEL = "Qwen/Qwen3-30B-A3B"
NUM_LAYERS, ROUTER_TOPK = 48, 8

# 分支 b0：uh_probe_result.json 原形状
PROMPT_A, RESP_A = 15, 16
KEPT_PER_TOKEN_A = [4] * 9 + [3] * 7  # 合计 57
ROWS_A = PROMPT_A - 1 + RESP_A  # 30

# 分支 b1：compaction 续写，多轮（生成 12 + 工具 6 + 生成 9）
PROMPT_B, GEN_B1, TOOL_B, GEN_B2 = 22, 12, 6, 9
RESP_B = GEN_B1 + TOOL_B + GEN_B2  # 27
KEPT_PER_TOKEN_B = [4] * 5 + [3] * 7 + [0] * TOOL_B + [4] * 3 + [3] * 6  # 41 + 0 + 30 = 71
ROWS_B = PROMPT_B - 1 + RESP_B  # 48


def build() -> ProjectionInputs:
    offsets_a = topp_offsets(KEPT_PER_TOKEN_A)
    offsets_b = topp_offsets(KEPT_PER_TOKEN_B)

    sample_a = FixtureSlimeSample(
        tokens=[1000 + i for i in range(PROMPT_A)] + [2000 + i for i in range(RESP_A)],
        response_length=RESP_A,
        loss_mask=[1] * RESP_A,
        rollout_log_probs=[-(i + 1) * 0.03125 for i in range(RESP_A)],
        rollout_top_p_token_ids=b64_int32(list(range(100000, 100000 + offsets_a[-1]))),
        rollout_top_p_token_offsets=list(offsets_a),
        rollout_routed_experts=b64_int32(routing_flat(ROWS_A, NUM_LAYERS, ROUTER_TOPK)),
        rollout_id=7,
        index=0,
    )
    sample_b = FixtureSlimeSample(
        tokens=(
            [3000 + i for i in range(PROMPT_B)]
            + [4000 + i for i in range(GEN_B1)]
            + [5000 + i for i in range(TOOL_B)]
            + [6000 + i for i in range(GEN_B2)]
        ),
        response_length=RESP_B,
        loss_mask=[1] * GEN_B1 + [0] * TOOL_B + [1] * GEN_B2,
        rollout_log_probs=(
            [-(i + 1) * 0.0625 for i in range(GEN_B1)]
            + [0.0] * TOOL_B
            + [-(i + 1) * 0.125 for i in range(GEN_B2)]
        ),
        rollout_top_p_token_ids=b64_int32(list(range(110000, 110000 + offsets_b[-1]))),
        rollout_top_p_token_offsets=b64_int32(offsets_b),
        rollout_routed_experts=b64_int32(routing_flat(ROWS_B, NUM_LAYERS, ROUTER_TOPK)),
        rollout_id=7,
        index=1,
    )

    capture_dicts = [
        capture_record_dict(
            record_id="cap_t1",
            turn_id="turn_0",
            trajectory_id=TRAJECTORY_ID,
            model_name=MODEL,
            prompt_token_count=PROMPT_A,
            response_token_count=RESP_A,
        ),
        capture_record_dict(
            record_id="cap_t2",
            turn_id="turn_1",
            trajectory_id=TRAJECTORY_ID,
            model_name=MODEL,
            prompt_token_count=PROMPT_B,
            response_token_count=GEN_B1,
        ),
        capture_record_dict(
            record_id="cap_t3",
            turn_id="turn_2",
            trajectory_id=TRAJECTORY_ID,
            model_name=MODEL,
            prompt_token_count=PROMPT_B + GEN_B1 + TOOL_B,  # 40
            response_token_count=GEN_B2,
        ),
    ]

    annotations = [
        SlimeBranchAnnotation(branch_id="b0", capture_record_ids=["cap_t1"]),
        SlimeBranchAnnotation(
            branch_id="b1",
            capture_record_ids=["cap_t2", "cap_t3"],
            lineage=CompactedSubTraceLineage(
                parent_trajectory_id=TRAJECTORY_ID,
                parent_branch_id="b0",
                compaction_event_id="compact_evt_0001",
                fork_point_token_index=5,
                compaction_kind="context_compaction",
                replay_prefix_loss_masked=True,
            ),
            # 工具段 [34, 40)：全序列座标 = prompt 22 + 生成 12 起、宽 6。
            context_runs=[
                {"start": PROMPT_B + GEN_B1, "end": PROMPT_B + GEN_B1 + TOOL_B, "kind": "tool_result"}
            ],
        ),
    ]

    reward = SlimeRewardInput(
        reward_scope="group_level",
        raw_reward=1.0,
        reward_event_refs=["rpt_grading_0001"],
        credit_assignment_strategy="backend_group_normalized",
        group_id="group_django__django-11099",
        parent_rollout_id="rollout_7",
    )

    return ProjectionInputs(
        samples=[sample_a, sample_b],
        capture_dicts=capture_dicts,
        annotations=annotations,
        reward=reward,
        kwargs={
            "task_id": TASK_ID,
            "serving_precision": "bfloat16",
            "serving_sampling_backend": "pytorch",
            "moe_num_layers": NUM_LAYERS,
            "moe_router_topk": ROUTER_TOPK,
        },
    )
