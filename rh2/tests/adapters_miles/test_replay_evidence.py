"""租前完整审查 PR-P0-5 修复验收：R3 trainer 侧 replay 消费证据的计算核。

judge 消费的 replay_fill/replay_consume/replay_exhausted 事件由两个可本地测试
的生产函数支撑：

- ``BaseReplayManager.consumption_snapshot``：逐 stream 的 forward/backward pop
  计数与队列长度快照（per-step delta 与耗尽判定的原始事实）。
- ``replay_sample_digests``：converted tape 的逐样本 sha256——必须与 rollout 侧
  ``rollout_manager._emit_rollout_evidence`` 对 numpy tape 的 digest 字节兼容，
  否则 source→consume 联结（routing_replay_source_linkage）永远对不上。
"""

from __future__ import annotations

import hashlib

import pytest

pytestmark = pytest.mark.integration_base


def test_consumption_snapshot_tracks_record_and_pop_counters(world):
    """record 进队、pop 计数、clear_all_forward 重置——快照逐 stream 如实反映。"""
    import torch

    from miles.utils.replay_base import BaseReplayManager

    m = BaseReplayManager()
    m.enabled = True
    r0, r1 = m.create_replay(), m.create_replay()
    for r in (r0, r1):
        # 直接进队（record 的 pin_memory / pop 的 cuda 搬运是 GPU 路径；这里
        # 验证的是计数快照契约本身）
        r.top_indices_list.extend(torch.zeros(4, 8, dtype=torch.int32) for _ in range(3))
    snap = m.consumption_snapshot()
    assert snap == {
        "num_streams": 2,
        "forward_indices": [0, 0],
        "backward_indices": [0, 0],
        "queue_lens": [3, 3],
    }
    r0.forward_index = 3
    r1.forward_index = 3
    r0.backward_index = 2
    snap = m.consumption_snapshot()
    assert snap["forward_indices"] == [3, 3]
    assert snap["backward_indices"] == [2, 0]
    m.clear_all_forward()
    assert m.consumption_snapshot()["forward_indices"] == [0, 0]
    m.clear_all()
    assert m.consumption_snapshot() == {
        "num_streams": 2,
        "forward_indices": [0, 0],
        "backward_indices": [0, 0],
        "queue_lens": [0, 0],
    }


def test_replay_digest_byte_compatible_with_rollout_side(world):
    """trainer 侧 torch int32 tape 的 digest == rollout 侧 numpy tape 的 digest
    （rollout_manager 用 sha256(arr.tobytes())）——同数据必须同哈希，值变必须
    变哈希，否则联结检查要么永远红、要么什么都联不住。"""
    import numpy as np
    import torch

    from miles.utils.replay_base import replay_sample_digests

    rng = np.random.default_rng(7)
    src = rng.integers(0, 128, size=(5, 48, 8), dtype=np.int32)
    rollout_side = hashlib.sha256(src.tobytes()).hexdigest()

    converted = torch.from_numpy(src.copy())
    [trainer_side] = replay_sample_digests([converted])
    assert trainer_side == rollout_side

    tampered = src.copy()
    tampered[0, 0, 0] += 1
    [other] = replay_sample_digests([torch.from_numpy(tampered)])
    assert other != rollout_side

    # 非 contiguous 张量也必须按行主序字节哈希（helper 内部 contiguous 化）
    transposed = torch.from_numpy(src.copy()).permute(1, 0, 2).permute(1, 0, 2)
    [same] = replay_sample_digests([transposed])
    assert same == rollout_side

    assert replay_sample_digests(None) is None
