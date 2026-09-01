"""W1b 第一集成切片（F4）：physical attempt → host 原始分派的 authoritative join。

问题（Wave1 复核 F4）：评分侧若接受调用方回显的 (task_id, environment_package_digest)
二元组，两个合法 package A/B 成对替换、旧 retry attempt、并发同题错接都能拼出一个
"自洽"的 join——digest 贯穿只核对了内容一致，没有核对**这是不是 host 给这次 attempt
分派的任务**。

修复：在 `Rh2MilesGenerateFn` 铸造六字段身份之后、进入 rh2 生产链之前，把
``physical_attempt_id → AttemptAssignment``（host 原始分派：来自 prepared prompt
metadata 的三个分派键 + 铸造出的组/成员/attempt 身份）绑进**有界进程内映射**
（`AttemptAssignmentRegistry`）；绑定时用 prep manifest 核对分派三元组（不是回显值
自洽就算）。此后 task 解析与评分材料查找**只以 attempt id 为键**，样本 metadata 上
携带的任何身份/分派键都只用来与绑定逐字比对——不一致即拒绝（调用方回显别的二元组
无效）。attempt 结束即 release，旧 retry attempt 的 id 随之失效；容量上限触顶即拒
（泄漏可见，不静默增长）。不建 durable ledger、不扫盘。

本模块零 miles/slime import（纯 Python），CPU 任意环境可导。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from repoharness2.adapters.miles.identity import (
    ATTEMPT_ID_KEY,
    ATTEMPT_SEQ_KEY,
    EXECUTION_ID_KEY,
    GROUP_ID_KEY,
    GROUP_INDEX_KEY,
    IDENTITY_KEYS,
    MEMBER_SLOT_KEY,
)
from repoharness2.envpack.prepared_tasks import DISPATCH_METADATA_KEYS

DEFAULT_REGISTRY_CAPACITY = 4096


class AttemptAssignmentError(RuntimeError):
    """join 边界 fail-closed 错误（reason_code 机器可读）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


@dataclass(frozen=True)
class AttemptAssignment:
    """一次 physical attempt 的 typed 分派载荷：铸造身份 + host 原始分派三元组。"""

    physical_attempt_id: str
    physical_attempt_seq: int
    rollout_execution_id: str
    prompt_group_id: str
    group_index: int
    member_slot: int
    task_id: str
    environment_package_digest: str
    public_bundle_digest: str

    def dispatch_triple(self) -> dict[str, str]:
        return {
            "task_id": self.task_id,
            "environment_package_digest": self.environment_package_digest,
            "public_bundle_digest": self.public_bundle_digest,
        }

    def identity_view(self) -> dict[str, Any]:
        return {
            GROUP_ID_KEY: self.prompt_group_id,
            GROUP_INDEX_KEY: self.group_index,
            EXECUTION_ID_KEY: self.rollout_execution_id,
            MEMBER_SLOT_KEY: self.member_slot,
            ATTEMPT_ID_KEY: self.physical_attempt_id,
            ATTEMPT_SEQ_KEY: self.physical_attempt_seq,
        }


def assignment_from_dispatch(sample_metadata: Any, minted_identity: Mapping[str, Any]) -> AttemptAssignment:
    """从派发时刻的样本 metadata（prepared prompt 的分派三元组）+ 本次铸造身份组装载荷。"""

    if not isinstance(sample_metadata, Mapping):
        raise AttemptAssignmentError(
            "dispatch_metadata_missing", f"样本 metadata 不是 Mapping（{type(sample_metadata).__name__}）——无分派事实可绑定。"
        )
    missing = [k for k in DISPATCH_METADATA_KEYS if not isinstance(sample_metadata.get(k), str) or not sample_metadata.get(k)]
    if missing:
        raise AttemptAssignmentError(
            "dispatch_metadata_missing",
            f"样本 metadata 缺 prepared 分派键 {missing}——不是 trusted-prep 产物派发出的样本，fail-closed。",
        )
    absent = [k for k in IDENTITY_KEYS if k not in minted_identity]
    if absent:
        raise AttemptAssignmentError(
            "identity_incomplete", f"铸造身份缺字段 {absent}——必须使用 mint_attempt_identity 的完整结果。"
        )
    return AttemptAssignment(
        physical_attempt_id=str(minted_identity[ATTEMPT_ID_KEY]),
        physical_attempt_seq=int(minted_identity[ATTEMPT_SEQ_KEY]),
        rollout_execution_id=str(minted_identity[EXECUTION_ID_KEY]),
        prompt_group_id=str(minted_identity[GROUP_ID_KEY]),
        group_index=int(minted_identity[GROUP_INDEX_KEY]),
        member_slot=int(minted_identity[MEMBER_SLOT_KEY]),
        task_id=str(sample_metadata["task_id"]),
        environment_package_digest=str(sample_metadata["environment_package_digest"]),
        public_bundle_digest=str(sample_metadata["public_bundle_digest"]),
    )


class AttemptAssignmentRegistry:
    """有界进程内映射：physical_attempt_id → AttemptAssignment（attempt 存活期内有效）。

    **生命周期 = 一次 GenerateFn 调用**：`Rh2MilesGenerateFn` 在铸造身份之后 bind、在返回
    之前（finally）release。`resolve_for_sample` 因此**只在在飞期间可用**——生产调用者是
    bringup 的 `_resolve_task` / `_resolve_grading_spec`（编排层在 GenerateFn 调用栈内）。
    GenerateFn 返回后绑定已消失，buffer/filter 阶段（第二段）**不能**用本表对账；那一层
    以 miles `DataBufferInput` 的原始 `prompt_group` 与生成结果 `group` 对账（交付样本上
    已盖分派三元组 + 六字段身份 + termination 事实）。不延长本表生命周期（W1b 切片一复核 顺手修 3）。

    ``verify_dispatch`` 由 prepared task face 提供：用 prep manifest 核对分派三元组
    （task_id ↔ 两个 digest 必须是 manifest 记录的同一行），失败抛任意异常即拒绝绑定。
    """

    def __init__(self, *, verify_dispatch: Callable[[AttemptAssignment], None], capacity: int = DEFAULT_REGISTRY_CAPACITY) -> None:
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
            raise ValueError(f"capacity 必须是 >=1 的 int，得到 {capacity!r}")
        self._verify_dispatch = verify_dispatch
        self._capacity = capacity
        self._active: dict[str, AttemptAssignment] = {}

    def bind(self, assignment: AttemptAssignment) -> None:
        try:
            self._verify_dispatch(assignment)
        except Exception as exc:  # noqa: BLE001 - 任何核对失败都是拒绝绑定
            raise AttemptAssignmentError(
                "dispatch_not_authoritative",
                f"attempt {assignment.physical_attempt_id}: 分派三元组未通过 prep manifest 核对（{type(exc).__name__}: {exc}）"
                "——合法 package 成对替换/伪造分派在此拒绝。",
            ) from exc
        aid = assignment.physical_attempt_id
        if aid in self._active:
            raise AttemptAssignmentError(
                "attempt_already_bound", f"attempt {aid} 已有绑定——同一 physical attempt 不得二次派发。"
            )
        if len(self._active) >= self._capacity:
            raise AttemptAssignmentError(
                "registry_capacity_exceeded",
                f"在飞 attempt 绑定数已达上限 {self._capacity}——release 缺失或并发失控，拒绝新绑定（不静默增长）。",
            )
        self._active[aid] = assignment

    def lookup(self, physical_attempt_id: Any) -> AttemptAssignment:
        if not isinstance(physical_attempt_id, str) or not physical_attempt_id:
            raise AttemptAssignmentError("attempt_id_missing", "样本没有 rh2_physical_attempt_id——无法按 attempt 查找分派。")
        assignment = self._active.get(physical_attempt_id)
        if assignment is None:
            raise AttemptAssignmentError(
                "attempt_not_bound",
                f"attempt {physical_attempt_id} 没有在飞绑定——旧 retry attempt / 未经铸造派发的样本，拒绝。",
            )
        return assignment

    def resolve_for_sample(self, sample_metadata: Any) -> AttemptAssignment:
        """按样本自带的 attempt id 取绑定，再把样本回显的身份/分派键与绑定逐字比对。

        仅在飞（GenerateFn 返回前）可用：release 之后同一 attempt id 一律 `attempt_not_bound`。
        """

        if not isinstance(sample_metadata, Mapping):
            raise AttemptAssignmentError("attempt_id_missing", "样本 metadata 不是 Mapping——无法按 attempt 查找分派。")
        assignment = self.lookup(sample_metadata.get(ATTEMPT_ID_KEY))
        expected: dict[str, Any] = {**assignment.identity_view(), **assignment.dispatch_triple()}
        for key, value in expected.items():
            if sample_metadata.get(key) != value:
                raise AttemptAssignmentError(
                    "assignment_echo_mismatch",
                    f"attempt {assignment.physical_attempt_id}: 样本回显 {key}={sample_metadata.get(key)!r} 与 host 分派 "
                    f"{value!r} 不一致——并发同题错接/回显别的 (task_id, digest) 二元组，拒绝。",
                )
        return assignment

    def release(self, physical_attempt_id: str) -> bool:
        return self._active.pop(physical_attempt_id, None) is not None

    def active_attempt_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._active))

    def __len__(self) -> int:
        return len(self._active)


def stamp_assignment_on_outputs(output: Any, assignment: AttemptAssignment) -> None:
    """把本次 attempt 的分派三元组盖到输出叶（vendor 叶链 metadata 由 to_sample 重建，
    分派键不会自动传播）；叶上已带不同值 = 串进别的分派，fail-closed。"""

    if isinstance(output, list):
        for item in output:
            stamp_assignment_on_outputs(item, assignment)
        return
    meta = getattr(output, "metadata", None)
    if not isinstance(meta, dict):
        raise AttemptAssignmentError(
            "member_metadata_not_writable", f"输出叶的 metadata 不是 dict（得到 {type(meta).__name__}）——分派键无法回写。"
        )
    triple = assignment.dispatch_triple()
    for key, value in triple.items():
        if key in meta and meta[key] != value:
            raise AttemptAssignmentError(
                "output_dispatch_forgery",
                f"输出叶 metadata[{key!r}]={meta[key]!r} 与本次 attempt 分派 {value!r} 不一致——拒绝交付。",
            )
    meta.update(triple)


__all__ = [
    "DEFAULT_REGISTRY_CAPACITY",
    "AttemptAssignment",
    "AttemptAssignmentError",
    "AttemptAssignmentRegistry",
    "assignment_from_dispatch",
    "stamp_assignment_on_outputs",
]
