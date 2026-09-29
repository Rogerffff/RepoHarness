"""复用真实 vendored builder，区别模型输出量与训练 response 区域长度。"""

import json
import sys
from pathlib import Path

root = next(p for p in Path(__file__).resolve().parents if (p / 'rh2/pyproject.toml').is_file())
sys.path.insert(0, str(root / 'rh2/src'))

from slime.agent.trajectory import _SampleBuilder, TurnRecord
from slime.utils.types import Sample

builder = _SampleBuilder(fork_threshold=0)
turns = [
    TurnRecord(prompt_ids=[1, 2], output_ids=[3, 4], finish_reason='stop'),
    TurnRecord(prompt_ids=[1, 2, 3, 4] + list(range(100, 200)), output_ids=[5, 6], finish_reason='stop'),
]
for turn in turns:
    builder.append_turn(turn, builder.classify_token_drift(turn))
row = builder.to_sample(Sample(index=0, group_index=0, prompt=''), {})
result = {
    'response_length': row.response_length,
    'generated_output_tokens': sum(len(t.output_ids) for t in turns),
    'loss_mask_sum': sum(row.loss_mask),
    'input_tokens': len(row.tokens),
}
assert result == {'response_length': 104, 'generated_output_tokens': 4, 'loss_mask_sum': 4, 'input_tokens': 106}
print(json.dumps(result))
