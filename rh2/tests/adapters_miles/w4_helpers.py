"""W4 测试的可 import 替身与共享构造器（miles `load_function` 需要模块路径）。"""

from __future__ import annotations

from typing import Any


def reject_all_filter(args, samples, **kwargs):
    """dynamic filter 替身：一律 keep=False（drop 事件的 dynamic_filter 分支）。"""

    from miles.rollout.filter_hub.base_types import DynamicFilterOutput

    return DynamicFilterOutput(keep=False, reason="test_reject_all")


def formal_group(
    world,
    *,
    versions_per_member: list[list[str]],
    group_index: int = 0,
    task_id: str = "task-A",
    prompt_group: list[Any] | None = None,
    reward_values: list[float] | None = None,
    claim_formal: bool = True,
    attempt_seq: int = 1,
) -> tuple[list[Any], list[list[Any]]]:
    """构造一个（声称）formal 的完成组：每个成员一叶（miles Sample），metadata 带 rh2 formal 链的
    键（admission 载荷占位 + 六字段身份的三个键 + 分派 task_id）。只测 buffer 的 consume-time
    判定与事件字段，所以 admission 载荷内容是占位（这些测试都不挂真实复合 filter）。

    返回 (prompt_group, group)；group 形状 = list[list[Sample]]（miles GenerateFnOutput.samples 形态）。
    """

    n = len(versions_per_member)
    if prompt_group is None:
        prompt_group = []
        for slot in range(n):
            p = world.MS(index=group_index * n + slot, group_index=group_index, prompt=f"prompt-{task_id}")
            p.metadata = {"task_id": task_id, "instance_id": f"inst-{task_id}", "prompt_id": f"p-{task_id}"}
            prompt_group.append(p)
    group: list[list[Any]] = []
    for slot, (p, versions) in enumerate(zip(prompt_group, versions_per_member)):
        s = world.MS(index=p.index, group_index=p.group_index, prompt=p.prompt)
        s.status = world.MS.Status.COMPLETED
        s.reward = float(reward_values[slot]) if reward_values is not None else float(slot % 2)
        s.tokens = [1, 2, 3]
        s.response_length = 2
        s.loss_mask = [1, 1]
        s.weight_versions = [str(v) for v in versions]
        s.metadata = dict(p.metadata or {})
        gid = f"miles_g{group_index}"
        s.metadata.update(
            {
                "rh2_prompt_group_id": gid,
                "rh2_member_slot": slot,
                "rh2_rollout_execution_id": f"{gid}_m{slot}",
                "rh2_physical_attempt_id": f"{gid}_m{slot}#p{attempt_seq}-{task_id}",
                "rh2_physical_attempt_seq": attempt_seq,
            }
        )
        if claim_formal:
            s.metadata["rh2_admission"] = {"schema_id": "synthetic-placeholder"}
        group.append([s])
    return prompt_group, group


def read_events(events_dir, kinds: tuple[str, ...] | None = None) -> list[dict]:
    """读取 MILES_RH2_EVENT_DIR 下的全部事件行（按文件名、行序）。"""

    import json
    from pathlib import Path

    rows: list[dict] = []
    for path in sorted(Path(events_dir).glob("rh2_events_*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    if kinds is not None:
        rows = [r for r in rows if r.get("event") in kinds]
    return rows
