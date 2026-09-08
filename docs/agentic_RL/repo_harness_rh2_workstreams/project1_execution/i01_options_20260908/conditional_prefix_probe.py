"""I01 窄探针：保留输出 token 与保留真实条件前缀是两件事。

只执行固定版本 Polar 的原始类定义，使用已经解析好的合成 Trace；
不模拟 HTTP、tokenizer 或生产发生率，也不修改外部源码。
"""

import ast
from collections import defaultdict
from copy import deepcopy
import json
import logging
from pathlib import Path
from types import SimpleNamespace


source_path = Path(__file__).parent / "sources/polar_prefix_merging.py"
module = ast.parse(source_path.read_text())
builder_class = next(
    item for item in module.body
    if isinstance(item, ast.ClassDef) and item.name == "PrefixMergingBuilder"
)
isolated_module = ast.Module(
    body=[
        ast.ImportFrom(
            module="__future__",
            names=[ast.alias(name="annotations")],
            level=0,
        ),
        builder_class,
    ],
    type_ignores=[],
)
ast.fix_missing_locations(isolated_module)
namespace = {
    "BaseTrajectoryBuilder": object,
    "Trace": SimpleNamespace,
    "build_trace_from_completion": lambda completion: completion,
    "logger": logging.getLogger("i01_prefix_probe"),
    "deepcopy": deepcopy,
    "_NATURAL_STOP_REASONS": frozenset({"stop", "tool_calls", "stop_sequence"}),
}
exec(compile(isolated_module, str(source_path), "exec"), namespace)
builder = namespace["PrefixMergingBuilder"](end_of_turn_token_id=99)


def trace(prompt, response):
    return SimpleNamespace(
        prompt_ids=prompt,
        response_ids=response,
        loss_mask=[1] * len(response),
        response_logprobs=[-0.5] * len(response),
        prompt_messages=[],
        response_messages=[],
        tools=[],
        finish_reason="stop",
        metadata={},
    )


first = trace([10], [20, 99])
second = trace([10, 21, 99, 30], [40, 99])
assert builder._find_extendable_chain(second.prompt_ids, [first.prompt_ids]) == 0
stats = defaultdict(int)
merged = builder._finalize_chain([first, second], stats)
merged_ids = merged.prompt_ids + merged.response_ids
second_start = len(merged_ids) - len(second.response_ids)
training_prefix = merged_ids[:second_start]
assert merged_ids == [10, 20, 99, 30, 40, 99]
assert merged.loss_mask == [1, 1, 0, 1, 1]
assert training_prefix != second.prompt_ids
assert stats["chains_reconstructed_full"] == 1

print(json.dumps({
    "scope": "固定版本原类的合成 Trace 输入；未运行生产请求",
    "first_prompt": first.prompt_ids,
    "first_response": first.response_ids,
    "second_actual_prompt": second.prompt_ids,
    "second_response": second.response_ids,
    "merged_ids": merged_ids,
    "merged_loss_mask": merged.loss_mask,
    "second_training_prefix": training_prefix,
    "all_sampled_output_ids_retained": True,
    "second_conditioning_prefix_matches": training_prefix == second.prompt_ids,
    "stats": dict(stats),
}, ensure_ascii=False, indent=2))
