"""miles 派发路径的 fa_formal 六字段身份铸造（W1a，计划 06 §3 / D0-2）。

背景（已核实的正确性缺口）：vendored 生产链 `repoharness2/adapters/slime/
generate.py:2366-2378` 在非 s1_compat 模式强制要求样本 metadata 预先带全
六字段身份::

    rh2_prompt_group_id        组身份（prompt group 级）
    rh2_group_index            miles 组序号（int）
    rh2_rollout_execution_id   member 的逻辑执行身份（跨 retry 稳定）
    rh2_member_slot            member 在组内的槽位（int，0..n-1）
    rh2_physical_attempt_id    本次物理执行身份（每次派发全新）
    rh2_physical_attempt_seq   同一逻辑执行内的物理尝试序号（1 起递增）

旧链的铸造分两级：fa_bringup `FaRolloutService._task_source`（组/成员级，
`fa_g{seq}` / `{gid}_m{slot}`）+ `ContinuousExecutionWorker`（dispatch 时刻
铸 `{exec}#p{seq}-{uuid8}`）。miles 派发路径（Rh2MilesGenerateFn）此前全仓
零铸造点——本模块补上它，铸造语义对照旧链逐条对齐。

铸造边界 = `Rh2MilesGenerateFn.__call__`（miles 每次对一个 member 调一次
generate，即一次物理 attempt 的派发时刻）。miles 侧没有 rh2 拥有的组级
submit 钩子（`fully_async_rollout._submit_one_group` 是 miles 只读代码），
因此组身份不靠跨成员协调，而是从样本自带的组事实**确定性推导**——同组
成员各自推导得到相同组身份，等价于一次组级铸造：

- 组事实来源（reference/miles `rollout/data_source.py` 已核实）：
  `sample.group_index` 是组级单调计数器（同组 n 个成员共享），
  `sample.index` 是全局样本计数器（组内连续），两者同步递增并被
  checkpoint state_dict 同存同取，因此 `index == group_index * n + slot`
  （n = args.n_samples_per_prompt）在 stock 数据源上恒成立；
- 推导规则：`rh2_prompt_group_id = "miles_g{group_index}"`，
  `slot = index - group_index * n`，越界（不在 0..n-1）即 fail-closed
  拒绝——自定义数据源若打破该算术，这里当场炸而不是静默产出错组身份；
- retry 语义（`Sample.reset_for_retry()` 已核实保留 identity 字段与
  metadata，并把 status 置为 ABORTED；fresh 样本 status=PENDING）：group/
  member 四字段跨 retry 不变；physical attempt 两字段每次派发**必换新**——
  seq 从 metadata 里上一次的值 +1（metadata 随 retry 保留，正是天然的
  per-member 计数载体），attempt id 带 uuid 后缀保证跨进程也不撞。
  **fresh（PENDING）样本不得携带任何保留身份键**（输入 JSON 伪造历史在此
  fail-closed）；只有 ABORTED 回收样本才允许在完整、形制正确的旧身份上
  续铸。session capability 由 generate.py 按 attempt id 每次
  重新铸造（128-bit 随机），attempt 换新即 capability 不复用；
- fan-out 语义：一次 generate 的多个输出叶只是**同一 member 同一
  attempt** 的分支——六字段整组相同地盖到每片叶上；叶上若已带不同值
  （伪造独立 attempt / 冒充新 member）fail-closed 拒绝。

本模块只做中立身份事实（D0-2）：不夹带任何 admission/loss/timeout/
staleness 决定；eligibility 消费归 W1b。零 miles/slime import（鸭子类型：
只要求样本有 group_index/index/metadata/status 四个属性），CPU 任意环境可导。
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

# 六字段键名（与 generate.py:2366-2378 的强校验逐字一致，勿改）。
GROUP_ID_KEY = "rh2_prompt_group_id"
GROUP_INDEX_KEY = "rh2_group_index"
EXECUTION_ID_KEY = "rh2_rollout_execution_id"
MEMBER_SLOT_KEY = "rh2_member_slot"
ATTEMPT_ID_KEY = "rh2_physical_attempt_id"
ATTEMPT_SEQ_KEY = "rh2_physical_attempt_seq"

IDENTITY_KEYS = (
    GROUP_ID_KEY,
    GROUP_INDEX_KEY,
    EXECUTION_ID_KEY,
    MEMBER_SLOT_KEY,
    ATTEMPT_ID_KEY,
    ATTEMPT_SEQ_KEY,
)

# 跨 retry 必须稳定的四个字段（组级 + member 级）；attempt 两字段每次派发换新。
_STABLE_KEYS = (GROUP_ID_KEY, GROUP_INDEX_KEY, EXECUTION_ID_KEY, MEMBER_SLOT_KEY)


class MilesIdentityError(RuntimeError):
    """身份铸造边界 fail-closed 错误（reason_code 机器可读）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


def _require_index_fact(value: Any, *, name: str) -> int:
    # bool 是 int 子类，True/False 混进来说明字段被污染——显式拒绝。
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MilesIdentityError(
            "identity_facts_missing",
            f"样本身份事实 {name}={value!r} 不是非负 int——miles data_source "
            "对训练样本必然赋值（data_source.py 组装配循环），缺失/异型说明"
            "样本没走正常派发链，fail-closed 拒绝铸造。",
        )
    return value


def _dispatch_status(sample: Any) -> str:
    """读样本派发状态并归一成小写字符串（鸭子类型：miles `Sample.Status`
    枚举取 `.value`；裸字符串直接用）。缺失即视为非法派发形态。"""

    raw = getattr(sample, "status", None)
    value = getattr(raw, "value", raw)
    if not isinstance(value, str) or not value:
        raise MilesIdentityError(
            "identity_facts_missing",
            f"样本没有可读的派发状态（status={raw!r}）——不是 miles 派发链的"
            "样本形态，fail-closed 拒绝铸造。",
        )
    return value.lower()


def mint_attempt_identity(sample: Any, *, n_samples_per_prompt: Any) -> dict[str, Any]:
    """在派发时刻为一个 member 铸造/续铸六字段身份，写进 sample.metadata。

    返回本次铸造结果（六键 dict），供输出侧盖章（`stamp_identity_on_outputs`）
    与测试断言使用。语义（模块 docstring 的对照表）：

    - 组/成员四字段从样本组事实确定性推导，跨 retry 稳定；metadata 已带
      **不同值**（跨组错配/冒充他人成员）即 fail-closed，不静默覆写；
    - attempt 两字段每次调用换新：seq = 上次 seq + 1（首个 attempt = 1），
      attempt id = ``{execution_id}#p{seq}-{uuid8}``（与旧
      ContinuousExecutionWorker 的 dispatch 铸造同一形制）。
    """

    meta = getattr(sample, "metadata", None)
    if not isinstance(meta, dict):
        # 对照 fa_bringup P1-4：metadata 不可写则身份无处安放，结构化失败。
        raise MilesIdentityError(
            "member_metadata_not_writable",
            f"member 的 metadata 不是 dict（得到 {type(meta).__name__}）——"
            "六字段身份无法注入，fail-closed。",
        )

    group_index = _require_index_fact(getattr(sample, "group_index", None), name="group_index")
    index = _require_index_fact(getattr(sample, "index", None), name="index")
    if (
        isinstance(n_samples_per_prompt, bool)
        or not isinstance(n_samples_per_prompt, int)
        or n_samples_per_prompt < 1
    ):
        raise MilesIdentityError(
            "group_size_config_missing",
            f"n_samples_per_prompt={n_samples_per_prompt!r} 不是 >=1 的 int——"
            "member slot 推导需要组大小（miles args.n_samples_per_prompt），"
            "缺失/非法即拒绝铸造（不猜组形状）。",
        )

    slot = index - group_index * n_samples_per_prompt
    if not (0 <= slot < n_samples_per_prompt):
        raise MilesIdentityError(
            "member_slot_underivable",
            f"index={index} / group_index={group_index} / "
            f"n_samples_per_prompt={n_samples_per_prompt} 推导出组内槽位 "
            f"{slot}，不在 [0, {n_samples_per_prompt}) 内——样本不满足 stock "
            "data_source 的 `index == group_index*n + slot` 算术（自定义数据源"
            "或身份污染），fail-closed 拒绝而不是产出错误组身份。",
        )

    prompt_group_id = f"miles_g{group_index}"
    derived_stable: dict[str, Any] = {
        GROUP_ID_KEY: prompt_group_id,
        GROUP_INDEX_KEY: group_index,
        EXECUTION_ID_KEY: f"{prompt_group_id}_m{slot}",
        MEMBER_SLOT_KEY: slot,
    }
    # 稳定字段已在场且值不同 = 跨组错配/冒充（metadata 从别的样本串过来，
    # 或组事实被中途改写）。不走"系统字段覆写旧值"的旧链先例：旧链的组身份
    # 出自进程内计数器（跨 batch 必然不同，覆写是常态）；这里的推导是样本
    # 自身事实的纯函数，跨 retry 恒等——出现差异只可能是结构性污染。
    for key, derived in derived_stable.items():
        if key in meta and meta[key] != derived:
            raise MilesIdentityError(
                "identity_conflict",
                f"metadata[{key!r}]={meta[key]!r} 与由样本组事实推导的 "
                f"{derived!r} 不一致——跨组错配/身份复用形态，fail-closed"
                "（该字段跨 retry 恒定，差异即结构性污染）。",
            )

    # 六个 rh2 身份键是 system-reserved（Wave1 复核 F1，二轮复核闭合）：
    # miles 数据集会把输入 JSON 的 metadata 原样放进 Sample（data.py 直传 +
    # data_source deepcopy），所以"metadata 里已有 attempt 历史"不能直接当真。
    # 判定用 miles 自己的可信派发状态（types.py 已核实：fresh 样本
    # `status=PENDING` 默认值；`reset_for_retry()` 把 status 置为 ABORTED 且
    # 保留 metadata）：
    # - PENDING（fresh 派发）：**任一**保留键在场 = 输入污染 → 结构性
    #   fail-closed（哪怕六键齐全且与推导自洽——fresh 输入没有资格携带
    #   历史）；seq 从 1 起铸；
    # - ABORTED（unused handler retry 回收）：六键必须齐全且通过历史真实性
    #   校验才允许续铸；
    # - 其它状态：不是本铸造边界认识的派发形态 → 拒绝（自定义数据源要接
    #   入必须显式对齐这两种状态，不猜）。
    # 不得实现成 sample drop——静默丢弃会掩盖数据污染。
    status = _dispatch_status(sample)
    present_keys = [k for k in IDENTITY_KEYS if k in meta]
    if status == "pending":
        if present_keys:
            raise MilesIdentityError(
                "reserved_identity_keys_polluted",
                f"fresh 派发（status=PENDING）的样本 metadata 带 rh2 保留身份键 "
                f"{present_keys}——输入数据不得携带系统身份历史（含完整自洽的"
                "六键伪造），fail-closed。",
            )
        seq = 1
    elif status == "aborted":
        if len(present_keys) != len(IDENTITY_KEYS):
            raise MilesIdentityError(
                "reserved_identity_keys_polluted",
                f"retry 回收（status=ABORTED）的样本 metadata 保留键不齐全 "
                f"{present_keys}——真实 retry 历史必须六键齐全（reset_for_retry "
                "保留 metadata），残缺即污染/损坏，fail-closed。",
            )
        # 续铸路径的历史真实性校验：稳定四键与推导一致（上面已查）；
        # attempt 两键必须像"本 execution 上一次真实铸造"——旧 id 是
        # 非空字符串、前缀 = 本 execution、#pN 与旧 seq 一致、uuid 后缀
        # 形制完整。伪造外部历史（foreign execution / 编造 seq）在此拒绝。
        prev_seq = meta[ATTEMPT_SEQ_KEY]
        if isinstance(prev_seq, bool) or not isinstance(prev_seq, int) or prev_seq < 1:
            raise MilesIdentityError(
                "attempt_history_corrupt",
                f"metadata[{ATTEMPT_SEQ_KEY!r}]={prev_seq!r} 不是 >=1 的 int——"
                "无法在其上单调续铸，fail-closed。",
            )
        prev_attempt_id = meta[ATTEMPT_ID_KEY]
        expected_prefix = f"{derived_stable[EXECUTION_ID_KEY]}#p{prev_seq}-"
        if (
            not isinstance(prev_attempt_id, str)
            or not prev_attempt_id.startswith(expected_prefix)
            or len(prev_attempt_id) != len(expected_prefix) + 8
            or any(c not in "0123456789abcdef" for c in prev_attempt_id[len(expected_prefix):])
        ):
            raise MilesIdentityError(
                "attempt_history_forged",
                f"metadata[{ATTEMPT_ID_KEY!r}]={prev_attempt_id!r} 不符合本 "
                f"execution 的铸造形制 {expected_prefix!r}+uuid8——外部输入"
                "伪造/篡改 attempt 历史（foreign execution、#pN 与 seq 不符、"
                "空/异型 id 均在此拒绝），fail-closed。",
            )
        seq = prev_seq + 1
    else:
        raise MilesIdentityError(
            "dispatch_status_unexpected",
            f"样本派发状态 {status!r} 不是 pending（fresh）/aborted（retry 回收）"
            "——铸造边界只认识 miles 这两种派发形态，其它状态不猜身份历史，"
            "fail-closed。",
        )

    minted = dict(derived_stable)
    minted[ATTEMPT_SEQ_KEY] = seq
    # uuid 后缀：进程重启丢失 seq 连续性时（metadata 也丢的冷路径）attempt id
    # 仍不可能撞车；同形制 = async_worker.py dispatch 铸造。
    minted[ATTEMPT_ID_KEY] = f"{minted[EXECUTION_ID_KEY]}#p{seq}-{uuid.uuid4().hex[:8]}"

    meta.update(minted)
    return minted


def stamp_identity_on_outputs(output: Any, identity: Mapping[str, Any]) -> None:
    """把本次 attempt 的六字段身份盖到 canonicalize 后的全部输出叶上。

    round-trip 无损的落点：vendor 叶链的 metadata 由 `to_sample` 从
    extra_metadata 重建（不继承输入样本 metadata），六字段不会自动传播到
    输出——由本函数在 canonicalize 之后统一回写。规则：

    - 输出形状 = miles Sample 或任意嵌套 list（canonicalize_group 的输出
      面），逐叶处理、形状不改；
    - fan-out 的所有叶盖**同一份**身份（同 member 同 attempt 的分支）；
    - 叶上已带六字段之一且值不同 = 伪造独立 physical attempt / 冒充新
      member / 串进别的 execution 的输出——fail-closed 拒绝整次交付。

    身份来源只有铸造结果（`mint_attempt_identity` 返回值）；token 内容与
    index 匹配不再承担任何身份推断，只保留 canonicalize 既有的一致性校验
    （D0-2：token 匹配降级为校验断言）。
    """

    missing = [k for k in IDENTITY_KEYS if k not in identity]
    if missing:
        raise MilesIdentityError(
            "identity_stamp_incomplete",
            f"盖章身份缺字段 {missing}——必须使用 mint_attempt_identity 的"
            "完整铸造结果。",
        )
    if isinstance(output, list):
        for item in output:
            stamp_identity_on_outputs(item, identity)
        return
    meta = getattr(output, "metadata", None)
    if not isinstance(meta, dict):
        raise MilesIdentityError(
            "member_metadata_not_writable",
            f"输出叶的 metadata 不是 dict（得到 {type(meta).__name__}）——"
            "身份无法回写，fail-closed。",
        )
    for key in IDENTITY_KEYS:
        if key in meta and meta[key] != identity[key]:
            raise MilesIdentityError(
                "output_identity_forgery",
                f"输出叶 metadata[{key!r}]={meta[key]!r} 与本次 attempt 铸造的 "
                f"{identity[key]!r} 不一致——fan-out 叶不得伪造独立 physical "
                "attempt/新 member，fail-closed 拒绝交付。",
            )
    for key in IDENTITY_KEYS:
        meta[key] = identity[key]
