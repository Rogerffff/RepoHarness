"""SWE-Gym fork 日志 parser 的可执行移植（S1-b，评分接线 2026-09-15，用户决定 D1=A）。

来源：`swebench/harness/log_parsers.py` @ SWE-Gym/SWE-Bench-Fork 242429c188fcfd06aad13fce9a54d450470bf0ac，
原文件逐字节副本与 provenance 见 `docs/agentic_RL/repo_harness_rh2_workstreams/s2/vendor/`
（sha256 见 `SWEGYM_PARSERS_SOURCE_SHA256`）。

为什么需要：安装的 swebench 4.1.0 在 spec 注册表（`MAP_REPO_VERSION_TO_SPECS`）就不覆盖 SWE-Gym 的
9 个仓库，`scoring.parse_official_eval` 走不到 parser；fork 在基础映射之外新增了 13 个仓库的映射，
全部是 pytest `-rA` 摘要行解析（pydantic 用带 ANSI/控制字符清洗的变体）。

移植差异（行为等价由 `tests/envpack/test_swegym_parsers.py` 的回归语料钉住）：

1. `TestStatus` 枚举值本地定义（与 swebench 4.1.0 相同的五个字符串，测试与安装库逐字对拍），
   模块 import 不依赖 swebench（envpack 纪律：swebench 只在解析时惰性 import）。
2. `parse_log_pytest_pydantic` 去掉上游一行针对特定测试名的调试 `print`（不影响返回值）。
3. `parse_log_pytest_pydantic` 上游对只含状态词的行（如单独一行 `PASSED`）会 `IndexError`；
   本移植与 `parse_log_pytest` 一样跳过这类行——候选可控的 stdout 不能让 parser 抛异常把评分
   洗成 infra。上游在该行上没有任何返回值可言，跳过是唯一保守选择。
4. 只移植 fork **新增**的仓库映射；基础映射（django/sympy/requests/astropy 等）仍走安装的
   swebench 4.1.0（v1 路径 `scoring.parse_official_eval`）。
5. 标记切段、坏码检查与 report 计算不在本模块：v2 入口 `scoring.parse_eval_log_v2` 只以
   `>>>>> Start/End Test Output` 之间的段作为状态来源（不做 4.1.0 的整份日志回退）。
"""

from __future__ import annotations

import re
from collections.abc import Callable

SWEGYM_PARSERS_SOURCE_COMMIT = "242429c188fcfd06aad13fce9a54d450470bf0ac"
SWEGYM_PARSERS_SOURCE_SHA256 = "44ce810ca5bc14fb07f5f765cf6955ad9fac9218f1e1f7112914edbd52fc825f"
SWEGYM_PARSERS_VERSION_TAG = f"swegym_parsers@{SWEGYM_PARSERS_SOURCE_COMMIT[:8]}"

# swebench.harness.constants.TestStatus 的五个值（顺序与上游枚举一致；测试与安装库对拍）。
TEST_STATUS_VALUES: tuple[str, ...] = ("FAILED", "PASSED", "SKIPPED", "ERROR", "XFAIL")

LogParser = Callable[[str], dict[str, str]]


class SwegymParserError(KeyError):
    """仓库不在 fork 新增映射内（消费方应回退到 v1 官方路径或拒绝）。"""


def parse_log_pytest(log: str) -> dict[str, str]:
    """fork `parse_log_pytest` 逐字移植：`PASSED path::case` / `FAILED path::case - msg` 摘要行。"""
    test_status_map: dict[str, str] = {}
    for line in log.split("\n"):
        if any([line.startswith(x) for x in TEST_STATUS_VALUES]):
            # Additional parsing for FAILED status
            if line.startswith("FAILED"):
                line = line.replace(" - ", " ")
            test_case = line.split()
            if len(test_case) <= 1:
                continue
            test_status_map[test_case[1]] = test_case[0]
    return test_status_map


def parse_log_pytest_pydantic(log: str) -> dict[str, str]:
    """fork `parse_log_pytest_pydantic` 移植：先去 `[NNm` 色码与 0x01–0x1f 控制字符，再去
    `FAILED [..]` 的方括号注记；兼容旧版 pytest 把状态词放行尾的形态。差异见模块头 2、3。"""
    test_status_map: dict[str, str] = {}
    escapes = "".join([chr(char) for char in range(1, 32)])
    translator = str.maketrans("", "", escapes)
    for line in log.split("\n"):
        line = re.sub(r"\[(\d+)m", "", line)
        line = line.translate(translator)
        # additionally to pytest v2 we remove the [...] from FAILED
        line = re.sub(r"FAILED\s*\[.*?\]", "FAILED", line)
        if any([line.startswith(x) for x in TEST_STATUS_VALUES]):
            if line.startswith("FAILED"):
                line = line.replace(" - ", " ")
            test_case = line.split()
            if len(test_case) <= 1:
                continue
            test_status_map[test_case[1]] = test_case[0]
        # Support older pytest versions by checking if the line ends with the test status
        elif any([line.endswith(x) for x in TEST_STATUS_VALUES]):
            test_case = line.split()
            if len(test_case) <= 1:
                continue
            test_status_map[test_case[0]] = test_case[1]
    return test_status_map


# fork 在基础映射之外新增的仓库（键为小写投影，与 fork 末行 LOWER_MAP_REPO_TO_PARSER 语义一致）。
MAP_REPO_TO_PARSER_SWEGYM: dict[str, LogParser] = {
    "python/mypy": parse_log_pytest,
    "getmoto/moto": parse_log_pytest,
    "conan-io/conan": parse_log_pytest,
    "modin-project/modin": parse_log_pytest,
    "project-monai/monai": parse_log_pytest,
    "iterative/dvc": parse_log_pytest,
    "dask/dask": parse_log_pytest,
    "bokeh/bokeh": parse_log_pytest,
    "mne-tools/mne-python": parse_log_pytest,
    "hypothesisworks/hypothesis": parse_log_pytest,
    "pydantic/pydantic": parse_log_pytest_pydantic,
    "pandas-dev/pandas": parse_log_pytest,
    "facebookresearch/hydra": parse_log_pytest,
}


def lookup_parser(repo_key_lower: str) -> LogParser:
    """按 repo 小写键取 parser；不在映射内即拒（不静默回退到别的 parser）。"""
    if repo_key_lower != repo_key_lower.lower():
        raise SwegymParserError(f"repo_key_lower 未小写化: {repo_key_lower!r}")
    try:
        return MAP_REPO_TO_PARSER_SWEGYM[repo_key_lower]
    except KeyError as exc:
        raise SwegymParserError(f"fork 新增映射不含仓库 {repo_key_lower!r}") from exc
