"""窄探针：精确 token 前缀不能阻止原始消息树的 assistant rewrite。

从仓库根目录运行：
PYTHONDONTWRITEBYTECODE=1 rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/i01_options_20260908/tito_clean_rewrite_probe.py

只调用真实 Anthropic 翻译器和 vendored manager；不实现方案 C，不调用模型。
token 和 logprob 为合成输入，精确前缀只代表假定 TITO 成功后的 manager 输入。
"""

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "rh2/src"))

from slime.agent.adapters.anthropic import _translate_messages
from slime.agent.trajectory import DriftKind, TrajectoryManager, TurnRecord, _SampleBuilder
from slime.utils.types import Sample


def run_case(threshold: int) -> dict:
    wire_user = {"role": "user", "content": "task"}
    wire_assistant = {
        "role": "assistant",
        "content": [
            {"type": "thinking", "thinking": "stored reasoning"},
            {"type": "text", "text": "first action"},
        ],
    }
    wire_echo = {
        "role": "assistant",
        "content": [{"type": "text", "text": "first action"}],
    }
    wire_observation = {"role": "user", "content": "observation"}
    first_messages = _translate_messages([wire_user], None)
    stored_assistant = _translate_messages([wire_assistant], None)[0]
    second_messages = _translate_messages([wire_user, wire_echo, wire_observation], None)
    p1 = [100, 101]
    a1 = [201, 202, 203, 204]
    p2 = p1 + a1 + [300]
    a2 = list(range(5000, 5020))
    t1 = TurnRecord(p1, a1, "stop", [-0.2] * len(a1))
    t2 = TurnRecord(p2, a2, "stop", [-0.3] * len(a2))

    builder = _SampleBuilder(threshold)
    builder.append_turn(t1, DriftKind.CLEAN)
    token_relation = builder.classify_token_drift(t2)
    assert token_relation is DriftKind.CLEAN
    assert p2[: len(p1 + a1)] == p1 + a1
    assert stored_assistant != second_messages[1]

    manager = TrajectoryManager(fork_threshold_tokens=threshold)
    manager.record_turn("s", turn=t1, prompt_messages=first_messages, response_message=stored_assistant)
    manager.record_turn(
        "s", turn=t2, prompt_messages=second_messages,
        response_message={"role": "assistant", "content": "done"},
    )
    root = manager._trees["s"]
    leaves = list(root.leaves())
    nodes = {id(node): node for leaf in leaves for node in leaf.path_from_root()}
    retained_turns = sorted(node.turn_index for node in nodes.values() if node.turn is not None)
    rewrites = [node.metadata["merged_rewrite"] for node in nodes.values() if "merged_rewrite" in node.metadata]
    samples = manager.get_trajectory("s", base_sample=Sample(index=0, group_index=0, prompt="task"), reward=1)
    # Sample 的 loss_mask 只覆盖 response 区，tokens 仍包含首轮 prompt。
    trained_ids = [
        token for sample in samples
        for token, mask in zip(sample.tokens[-sample.response_length :], sample.loss_mask, strict=True)
        if mask
    ]
    assert retained_turns == ([2] if threshold == 1024 else [1, 2])
    assert trained_ids == (a2 if threshold == 1024 else a1 + a2)
    assert len(samples) == (1 if threshold == 1024 else 2)
    return {
        "threshold": threshold,
        "token_relation_before_message_tree": token_relation.name,
        "exact_prefix": p2[: len(p1 + a1)] == p1 + a1,
        "stored_assistant": stored_assistant,
        "replayed_assistant": second_messages[1],
        "new_output_tokens": len(a2),
        "tree_leaves": len(leaves),
        "retained_turn_indices": retained_turns,
        "merged_rewrites": rewrites,
        "samples": len(samples),
        "trained_tokens": len(trained_ids),
        "first_action_trained_tokens": sum(token in a1 for token in trained_ids),
        "rewards": [sample.reward for sample in samples],
    }


result = {
    "scope": "合成精确 token 前缀；真实消息翻译与 manager；未实现或验证 TITO adapter",
    "trajectory_sha256": hashlib.sha256((ROOT / "rh2/src/slime/agent/trajectory.py").read_bytes()).hexdigest(),
    "cases": [run_case(1024), run_case(0)],
    "assertions": "PASS",
}
print(json.dumps(result, ensure_ascii=False, indent=2))
