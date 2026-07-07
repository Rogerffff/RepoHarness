"""forbidden marker 名单与泄漏扫描工具（继承旧 L4/L5 语义 + S1 补充条款 A6 名单）。

这份名单回答一个问题：**哪些词出现在 public / 模型可见 / 训练可见的视图里，
就意味着评分私有信息可能泄漏了**。它继承两处旧资产的语义：

- 旧 `src/repo_harness/rl/visibility.py` 的 `FORBIDDEN_FIELD_MARKERS`
  （L4 出站扫描：EVALUATOR_ONLY_DENYLIST + batch 私有 key + 别名）；
- 旧 `evaluation/episode_projection.py` 的 `_scan_public_projection_for_leaks`（L5）。

并叠加 S1 补充条款 A6 的 SWE 数据泄漏字段名单：
golden_patch / test_patch / FAIL_TO_PASS / PASS_TO_PASS / hidden_verifier / grader_only。

匹配语义（沿用旧实现，刻意偏保守 / fail-closed）：

1. 归一化：小写 + 非字母数字折叠为下划线。"FAIL_TO_PASS"、"fail-to-pass"、
   "Fail To Pass" 都归一化为 "fail_to_pass"。
2. 子串命中：归一化后的 marker 是被检文本归一化结果的子串即命中，
   例如 key "swe_test_patch_path" 命中 "test_patch"。
3. 紧凑命中：再把下划线去掉做一次子串匹配，用于抓 camelCase
   （"TestPatch" -> "testpatch" 命中）。代价是可能误报
   （例如 "latest_patches" 紧凑后含 "testpatch"）——按 fail-closed 原则接受误报，
   误报由人工豁免，漏报直接污染训练数据。
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from typing import Any, NamedTuple

# ---------------------------------------------------------------------------
# marker 名单
# ---------------------------------------------------------------------------

# A6 名单：SWE 任务数据里天然存在、只许评分器看的字段名。
_A6_SWE_PRIVATE_MARKERS: tuple[str, ...] = (
    "golden_patch",
    "test_patch",
    "fail_to_pass",
    "pass_to_pass",
    "hidden_verifier",
    "grader_only",
)

# 旧 L4 EVALUATOR_ONLY_DENYLIST（visibility.py），去掉与 A6 重复的项。
_LEGACY_EVALUATOR_ONLY_MARKERS: tuple[str, ...] = (
    "gold_patch",
    "accepted_label",
    "complete_reward_metadata",
    "provider_secret",
    "evaluator_only_logs",
    "absolute_run_directory",
    "final_verifier_artifact",
    "reward_metadata_artifact",
    "hidden_test_selector",
    "hidden_test_patch",
    "hidden_test",
)

# 旧 L4 batch 私有 key + 别名（FORBIDDEN_BATCH_EXTRA_FIELD_KEYS / ALIASES）。
_LEGACY_BATCH_PRIVATE_MARKERS: tuple[str, ...] = (
    "audit_ref",
    "run_dir",
    "run_directory",
    "reward_metadata_path",
    "final_verifier_path",
    "gold_patch_path",
)

FORBIDDEN_PUBLIC_MARKERS: frozenset[str] = frozenset(
    _A6_SWE_PRIVATE_MARKERS + _LEGACY_EVALUATOR_ONLY_MARKERS + _LEGACY_BATCH_PRIVATE_MARKERS
)
"""禁止出现在 public projection / 模型可见视图 / 训练导出里的 marker 全集。"""


# ---------------------------------------------------------------------------
# 归一化与匹配
# ---------------------------------------------------------------------------

_NORMALIZE_PATTERN = re.compile(r"[^a-z0-9]+")


def normalize_marker_text(value: str) -> str:
    """把任意文本归一化为小写下划线形态（匹配的公共前置步骤）。

    例："FAIL_TO_PASS" -> "fail_to_pass"；"golden-Patch " -> "golden_patch"。
    """

    return _NORMALIZE_PATTERN.sub("_", value.lower()).strip("_")


def find_forbidden_marker(value: str) -> str | None:
    """在单个字符串里查找 forbidden marker，命中返回 marker 原文，否则 None。

    同时做归一化子串匹配与紧凑（去下划线）子串匹配，语义见模块 docstring。
    按字典序遍历名单：一段文本命中多个 marker 时（如 "hidden_test_patch" 同时含
    hidden_test / test_patch），返回值跨进程确定，evidence 可复现比对。
    """

    normalized = normalize_marker_text(value)
    compact = normalized.replace("_", "")
    for marker in sorted(FORBIDDEN_PUBLIC_MARKERS):
        normalized_marker = normalize_marker_text(marker)
        if normalized_marker and normalized_marker in normalized:
            return marker
        compact_marker = normalized_marker.replace("_", "")
        if compact_marker and compact_marker in compact:
            return marker
    return None


class MarkerHit(NamedTuple):
    """一次 marker 命中：出现位置（JSON path）、命中的 marker、命中在 key 还是 value。"""

    path: str
    marker: str
    kind: str  # "key" | "value"


def iter_forbidden_marker_hits(value: Any, path: str = "$") -> Iterator[MarkerHit]:
    """递归遍历 JSON 树（dict key、str value、list 元素），产出所有 marker 命中。

    - dict：先查 key 本身，再递归 value；
    - list：逐元素递归；
    - str：整串做 marker 匹配；
    - 其余标量（int/float/bool/None）不检查。
    """

    if isinstance(value, Mapping):
        for key, item in value.items():
            key_str = str(key)
            key_path = f"{path}.{key_str}"
            marker = find_forbidden_marker(key_str)
            if marker is not None:
                yield MarkerHit(path=key_path, marker=marker, kind="key")
            yield from iter_forbidden_marker_hits(item, key_path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from iter_forbidden_marker_hits(item, f"{path}[{index}]")
    elif isinstance(value, str):
        marker = find_forbidden_marker(value)
        if marker is not None:
            yield MarkerHit(path=path, marker=marker, kind="value")


def scan_for_forbidden_markers(value: Any) -> list[MarkerHit]:
    """扫描整棵 JSON 树，返回全部 marker 命中（空列表 = 干净）。

    这是 `inspect-rh2-artifact` 四步范式里的"marker 扫描"一步，也是
    S1-2 public task bundle 泄漏扫描、S1-5 投影扫描的共用底层。
    """

    return list(iter_forbidden_marker_hits(value))
