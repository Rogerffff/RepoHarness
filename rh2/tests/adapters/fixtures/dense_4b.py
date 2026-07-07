"""fixture (b)：Qwen3-4B dense 风格产物——无 routing（显式 not_applicable）。

对应 S1-7a 的 debug training transport step 形态（A2）：dense 只是没有 routing
tape，top_p=0.95 时 top-p tape 照样必须在场并被投影消费。单叶链、两轮生成夹
一段工具输出：prompt 12 + 生成 10 + 工具 5 + 生成 8 → tokens 35、response 23、
top-p offsets 长 24（工具段 5 个零宽 pad）。tape 载荷用 list[int]（slime 解码后
形态），与 fixture (a) 的 base64 形态互补覆盖唯一解码点。
"""

from __future__ import annotations

from repoharness2.adapters.slime import SlimeBranchAnnotation, SlimeRewardInput

from fixtures.common import (
    FixtureSlimeSample,
    ProjectionInputs,
    capture_record_dict,
    topp_offsets,
)

TRAJECTORY_ID = "traj_dense_0001"
TASK_ID = "psf__requests-2931"
MODEL = "Qwen/Qwen3-4B"

PROMPT, GEN_1, TOOL, GEN_2 = 12, 10, 5, 8
RESP = GEN_1 + TOOL + GEN_2  # 23
KEPT_PER_TOKEN = [3] * GEN_1 + [0] * TOOL + [3] * GEN_2  # 30 + 0 + 24 = 54


def build() -> ProjectionInputs:
    offsets = topp_offsets(KEPT_PER_TOKEN)
    sample = FixtureSlimeSample(
        tokens=(
            [1500 + i for i in range(PROMPT)]
            + [2500 + i for i in range(GEN_1)]
            + [3500 + i for i in range(TOOL)]
            + [4500 + i for i in range(GEN_2)]
        ),
        response_length=RESP,
        loss_mask=[1] * GEN_1 + [0] * TOOL + [1] * GEN_2,
        rollout_log_probs=(
            [-(i + 1) * 0.05 for i in range(GEN_1)]
            + [0.0] * TOOL
            + [-(i + 1) * 0.075 for i in range(GEN_2)]
        ),
        rollout_top_p_token_ids=list(range(120000, 120000 + offsets[-1])),
        rollout_top_p_token_offsets=list(offsets),
        rollout_routed_experts=None,  # dense：没有 routing tape
        rollout_id=3,
        index=0,
    )

    capture_dicts = [
        capture_record_dict(
            record_id="cap_d1",
            turn_id="turn_0",
            trajectory_id=TRAJECTORY_ID,
            model_name=MODEL,
            prompt_token_count=PROMPT,
            response_token_count=GEN_1,
            return_routed_experts=False,  # dense 请求方就不该开 routing
            tokenizer_name=MODEL,
        ),
        capture_record_dict(
            record_id="cap_d2",
            turn_id="turn_1",
            trajectory_id=TRAJECTORY_ID,
            model_name=MODEL,
            prompt_token_count=PROMPT + GEN_1 + TOOL,  # 27
            response_token_count=GEN_2,
            return_routed_experts=False,
            tokenizer_name=MODEL,
        ),
    ]

    annotations = [
        # 不给 context_runs：工具段 [22, 27) 走默认映射
        # （mask=0 -> tool_result / tool_or_env_context），正好验证 H4 默认路径。
        SlimeBranchAnnotation(branch_id="b0", capture_record_ids=["cap_d1", "cap_d2"]),
    ]

    reward = SlimeRewardInput(
        reward_scope="trace_level",
        raw_reward=0.0,
        reward_event_refs=["rpt_grading_0002"],
        credit_assignment_strategy="direct_trace_reward",
    )

    return ProjectionInputs(
        samples=[sample],
        capture_dicts=capture_dicts,
        annotations=annotations,
        reward=reward,
        kwargs={
            "task_id": TASK_ID,
            "serving_precision": "bfloat16",
            "serving_sampling_backend": "pytorch",
        },
    )
