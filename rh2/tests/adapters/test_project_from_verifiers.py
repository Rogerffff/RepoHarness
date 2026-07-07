"""project_from_verifiers（S1-8）单测：6 份真实 toy dump 全量投影 + fail-closed 矩阵。

真实数据面：docs/agentic_RL/repo_harness_rh2_workstreams/s0/toy_trace_dump/ 的
S0-3 dump——6 份可投影（EvalClient 文本中继，12 条 Trace）+ 1 份 error dump
（default_subprocess_deepseek_attempt.json，nodes=0 的缺 key 轨迹，天然的
拒收路径样本）。合成 fail-closed 用例基于最小 trace dict 逐项破坏。
"""

import json
from pathlib import Path

import pytest

from repoharness2.adapters.verifiers_projection import (
    EVAL_RELAY_RENDERER_CLS_NAME,
    VerifiersProjectionError,
    VerifiersRewardInput,
    project_from_verifiers,
    reward_input_from_trace,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DUMP_DIR = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s0/toy_trace_dump"

PROJECTABLE_DUMPS = [
    "default_docker.json",
    "default_subprocess.json",
    "default_subprocess_deepseek.json",
    "default_subprocess_maxturns1.json",
    "null_docker.json",
    "null_subprocess.json",
]


def load_dump(name: str) -> dict:
    return json.loads((DUMP_DIR / name).read_text())


# ---------------------------------------------------------------------------
# 真实 dump：全部可投影且降级标注逐项正确
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dump_name", PROJECTABLE_DUMPS)
def test_all_projectable_dumps_project_with_explicit_degradation(dump_name):
    dump = load_dump(dump_name)
    assert dump["traces"], f"{dump_name} 里没有 trace"
    for trace in dump["traces"]:
        projection = project_from_verifiers(trace, model_name=dump["meta"]["model"])
        assert projection.source_framework == "verifiers"
        assert projection.trajectory_id == trace["id"]
        assert projection.source_object_ref == f"verifiers_trace_{trace['id']}"
        # 哨兵值：不伪装真实 renderer/tokenizer（U-G 断言遇到它必然拦下）
        assert projection.renderer_cls_name == EVAL_RELAY_RENDERER_CLS_NAME
        assert projection.tokenizer_name == f"eval_relay_untokenized:{dump['meta']['model']}"

        (branch,) = projection.branches
        # 四联降级标注：logprob missing / top-p 未捕获 / routing 未捕获 / mask 全 0
        assert branch.logprob_alignment_status == "missing"
        assert branch.logprob_provenance is None
        assert branch.sampling_mask.mask_kind == "not_captured_text_relay"
        assert branch.sampling_mask.top_p is None
        assert branch.routing.alignment == "not_captured_text_relay"
        assert all(span.mask == 0 for span in branch.loss_mask_spans)
        assert not branch.capture_record_refs  # 无捕获 -> schema 链保证 mask=1 不可表示
        # 采样段理由必须是文本中继降级码（不许伪装成普通上下文）
        sampled_starts = {
            span.start for span in branch.token_spans if span.source_type == "sampled_assistant"
        }
        assert sampled_starts, "至少一段采样文本"
        for span in branch.loss_mask_spans:
            if span.start in sampled_starts:
                assert span.reason == "token_capture_unavailable_downgraded"
        # reward 事实直读 Trace.rewards
        assert projection.reward_facts.reward_scope == "trace_level"
        assert projection.reward_facts.raw_reward == sum(trace["rewards"].values())


def test_deepseek_trace_layout_matches_real_usage_accounting():
    """真实 provider（deepseek-chat）3 轮轨迹的逐段布局（含 cache 计入的 input_tokens）。

    d703bc8d 的 usage：i=[484, 170+384, 102+512]=[484,554,614]、c=[60,44,20]，
    差分出工具段 10 与 16 -> 布局 [0,484) prompt | [484,544) 采样 | [544,554) 工具 |
    [554,598) 采样 | [598,614) 工具 | [614,634) 采样，response=150。
    """

    dump = load_dump("default_subprocess_deepseek.json")
    trace = dump["traces"][0]
    assert trace["id"].startswith("d703bc8d")
    projection = project_from_verifiers(trace, model_name=dump["meta"]["model"])
    (branch,) = projection.branches
    assert branch.prompt_token_count == 484
    assert branch.response_token_count == 150
    spans = [(s.start, s.end, s.source_type) for s in branch.token_spans]
    assert spans == [
        (0, 484, "prompt_context"),
        (484, 544, "sampled_assistant"),
        (544, 554, "tool_result"),
        (554, 598, "sampled_assistant"),
        (598, 614, "tool_result"),
        (614, 634, "sampled_assistant"),
    ]
    assert projection.reward_facts.raw_reward == 1.0


def test_error_attempt_dump_fails_closed():
    """缺 key 的 error 轨迹（nodes=0，首轮模型调用即失败）：拒收而非空投影。"""

    dump = load_dump("default_subprocess_deepseek_attempt.json")
    assert len(dump["traces"]) == 2
    for trace in dump["traces"]:
        with pytest.raises(VerifiersProjectionError, match=r"^\[trace_has_no_branches\]"):
            project_from_verifiers(trace, model_name=dump["meta"]["model"])


# ---------------------------------------------------------------------------
# 合成 fail-closed 矩阵（最小 trace dict 上逐项破坏）
# ---------------------------------------------------------------------------


def usage(prompt: int, completion: int, cached: int | None = None) -> dict:
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "cached_input_tokens": cached,
        "reasoning_tokens": None,
        "cost": None,
    }


def node(role: str, parent: int | None, *, sampled: bool = False, u: dict | None = None, **extra) -> dict:
    base = {
        "parent": parent,
        "message": {"role": role, "content": "x"},
        "sampled": sampled,
        "token_ids": [],
        "mask": [],
        "is_content": [],
        "logprobs": [],
        "finish_reason": "stop" if sampled else None,
        "usage": u,
    }
    base.update(extra)
    return base


def minimal_trace(**overrides) -> dict:
    trace = {
        "id": "trace_synth_0001",
        "task": {"name": "synthetic-task", "idx": 0},
        "nodes": [
            node("user", None),
            node("assistant", 0, sampled=True, u=usage(53, 24)),
        ],
        "rewards": {"task_completed": 1.0},
        "stop_condition": "agent_completed",
        "errors": [],
    }
    trace.update(overrides)
    return trace


def test_minimal_synthetic_trace_projects():
    projection = project_from_verifiers(minimal_trace(), model_name="deepseek-chat")
    (branch,) = projection.branches
    assert (branch.prompt_token_count, branch.response_token_count) == (53, 24)


def test_token_faithful_trace_rejected_not_silently_degraded():
    """节点带 token ids = TrainClient 轨迹：必须拒绝，绝不静默降成文本级。"""

    trace = minimal_trace()
    trace["nodes"][1]["token_ids"] = [1, 2, 3]
    trace["nodes"][1]["mask"] = [True, True, True]
    with pytest.raises(VerifiersProjectionError, match=r"^\[token_faithful_trace_not_supported\]"):
        project_from_verifiers(trace, model_name="deepseek-chat")


def test_missing_usage_rejected():
    trace = minimal_trace()
    trace["nodes"][1]["usage"] = None
    with pytest.raises(VerifiersProjectionError, match=r"^\[usage_facts_missing\]"):
        project_from_verifiers(trace, model_name="deepseek-chat")


def test_inconsistent_usage_accounting_rejected():
    """第 2 轮 input(60) < 第 1 轮 input+completion(77)：计数座标系不成立。"""

    trace = minimal_trace(
        nodes=[
            node("user", None),
            node("assistant", 0, sampled=True, u=usage(53, 24)),
            node("tool", 1),
            node("assistant", 2, sampled=True, u=usage(60, 10)),
        ]
    )
    with pytest.raises(VerifiersProjectionError, match=r"^\[usage_accounting_inconsistent\]"):
        project_from_verifiers(trace, model_name="deepseek-chat")


def test_zero_completion_turn_rejected():
    trace = minimal_trace()
    trace["nodes"][1]["usage"] = usage(53, 0)
    with pytest.raises(VerifiersProjectionError, match=r"^\[sampled_turn_zero_completion\]"):
        project_from_verifiers(trace, model_name="deepseek-chat")


def test_branch_without_sampled_response_rejected():
    trace = minimal_trace(nodes=[node("user", None), node("tool", 0)])
    with pytest.raises(VerifiersProjectionError, match=r"^\[branch_without_sampled_response\]"):
        project_from_verifiers(trace, model_name="deepseek-chat")


def test_multi_branch_eval_trace_rejected():
    """两个叶子（compaction 形态）：文本中继无 token 级血缘，显式拒绝。"""

    trace = minimal_trace(
        nodes=[
            node("user", None),
            node("assistant", 0, sampled=True, u=usage(53, 24)),
            node("assistant", 0, sampled=True, u=usage(53, 30)),
        ]
    )
    with pytest.raises(VerifiersProjectionError, match=r"^\[eval_relay_multi_branch_not_supported\]"):
        project_from_verifiers(trace, model_name="deepseek-chat")


def test_default_reward_requires_trace_rewards():
    trace = minimal_trace(rewards={})
    with pytest.raises(VerifiersProjectionError, match=r"^\[trace_rewards_missing\]"):
        project_from_verifiers(trace, model_name="deepseek-chat")


def test_explicit_reward_input_overrides_trace_rewards():
    """走 finalize_rollout 的形态：reward_event_refs 指向本次评分报告。"""

    projection = project_from_verifiers(
        minimal_trace(),
        model_name="deepseek-chat",
        reward=VerifiersRewardInput(
            reward_scope="trace_level",
            raw_reward=1.0,
            reward_event_refs=["rpt_trace_synth_0001"],
            credit_assignment_strategy="direct_trace_reward",
        ),
    )
    assert projection.reward_facts.reward_event_refs == ["rpt_trace_synth_0001"]


def test_reward_input_from_trace_components():
    reward = reward_input_from_trace(minimal_trace())
    assert reward.components == {"task_completed": 1.0}
    assert reward.reward_event_refs == ["verifiers_trace_rewards:trace_synth_0001"]
