"""R2E-Gym-Subset 判定规则的可执行移植（R2E 接线 R-a/R-b，2026-09-20；用户决定 DR1=A、DR2 撤回）。

来源：`environments/swe/r2e_gym/r2e_gym/taskset.py` @ PrimeIntellect-ai/prime-envs
c4d04dfe212c153a587ea4ce072ae6753e74d6e9（Apache-2.0）。原文件逐字节副本、LICENSE 与 provenance 见
`docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/vendor/`（sha256 见 `R2E_RULE_SOURCE_SHA256`）。
**数据集 revision（e8b9fcbc…）不能替代代码版本**，所以规则源码单独固定；来源只有这一种去色行为，
本模块不维护第二套实现。

移植范围 = 四处纯函数逻辑，行为等价由 `tests/envpack/test_r2e_parsers.py` 钉住：测试按 AST 从 vendored
原文件取出同名函数，与本模块在固定样本和既有真实日志语料上对拍。

1. `parse_log_pytest`：逐字移植。只读**第一处** `short test summary info` 之后、下一处之前的文本；
   PASSED 行的键 = `::` 之后各段用 `.` 连接（文件路径被丢掉）；FAILED / ERROR 行再截 `" - "`；
   ERROR 行没有 `::`（收集错误只给文件名）时整行作键；SKIPPED / XFAIL 行不产出键。
2. `decolor_keys`（上游 `_decolor`）：正则是 `\\x1b\\[\\d+m`。上游源文件把 ESC 写成一个**不可见的原始字节**，
   用不显示控制字符的工具读那一行会误读成 `\\[\\d+m`（"只删 `[数字m`、留下 ESC"——09-09 与 09-20 两次误读
   均已撤回）。本移植改用显式转义 `\\x1b` 书写同一模式，这是唯一的书写差异。只删单参数序列
   （`\\x1b[1m`、`\\x1b[0m`）；期望侧与观测侧用同一函数，所以对称。
3. `normalize_status_map`：上游 `calculate_reward` 里对两侧各做一次的 `{k.split(" - ")[0]: d[k] for k in sorted(d)}`
   （去色之后）。两个键归一化后相同时，排序靠后的覆盖靠前的——与上游同。
4. `extract_gold_patch`：逐字移植（由 `parsed_commit_content` 的 hunk 重建 unified diff；只含非测试 `.py`）。

与上游 `calculate_reward` 的**一处有意差别**不在本模块：RH2 的判定用 `scoring.expected_map_matches`
（期望键 ∪ 观测键 的并集口径），上游在键数相等时会跳过空的观测键（例：观测 `{"": PASSED, a: PASSED}`、
期望 `{a: PASSED, b: PASSED}` → 上游给 1，RH2 给 0）。`prime_calculate_reward` 在这里保留上游原样行为，
只用于对拍与对账，不作生产判定。

不做的事：不先剥日志侧 ANSI / CR（上游不剥；评分日志来自无 TTY 的 exec，来源期望键也没有 CR）；
不重写入口命令；不为 unittest 形态的入口另立规则（pillow `3ac9396e` 的自定义 runner 自己打印同形摘要段）。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

R2E_RULE_SOURCE_ID = "prime_envs_c4d04dfe"
R2E_RULE_SOURCE_REPO = "PrimeIntellect-ai/prime-envs"
R2E_RULE_SOURCE_COMMIT = "c4d04dfe212c153a587ea4ce072ae6753e74d6e9"
R2E_RULE_SOURCE_PATH = "environments/swe/r2e_gym/r2e_gym/taskset.py"
R2E_RULE_SOURCE_SHA256 = "b928139eb0e9b4da9ca5d0ad927e17cf32727a6d18bc444ed57d63ca1a273bed"
R2E_RULE_SOURCE_VENDOR_RELPATH = (
    "docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/vendor/prime_envs_r2e_gym_taskset_c4d04dfe.py"
)

R2E_DATASET = "R2E-Gym/R2E-Gym-Subset"
R2E_DATASET_REVISION = "e8b9fcbce43eaca0dc2c0d4798ee6f3e965f590a"

# GradingReport.grader_version 用：数据 revision 与规则代码版本都写明（不再扩报告契约）。
R2E_GRADER_VERSION_TAG = f"r2e-gym-subset@{R2E_DATASET_REVISION[:8]}+parser:prime-envs@{R2E_RULE_SOURCE_COMMIT[:8]}"
R2E_PARSER_VERSION_TAG = f"r2e_parsers@prime-envs:{R2E_RULE_SOURCE_COMMIT[:8]}"

SHORT_SUMMARY_MARKER = "short test summary info"


@dataclass(frozen=True)
class R2ERuleSourcePin:
    """固定版本的上游规则源文件身份（包记录的 `spec_vendor_json_sha256` 由它派生）。"""

    rule_source_id: str
    repo: str
    commit: str
    path: str
    sha256: str  # 裸 hex
    vendor_relpath: str


_RULE_SOURCE_PINS: dict[str, R2ERuleSourcePin] = {
    R2E_RULE_SOURCE_ID: R2ERuleSourcePin(
        rule_source_id=R2E_RULE_SOURCE_ID,
        repo=R2E_RULE_SOURCE_REPO,
        commit=R2E_RULE_SOURCE_COMMIT,
        path=R2E_RULE_SOURCE_PATH,
        sha256=R2E_RULE_SOURCE_SHA256,
        vendor_relpath=R2E_RULE_SOURCE_VENDOR_RELPATH,
    )
}


def r2e_rule_source_pin(rule_source_id: str) -> R2ERuleSourcePin:
    """按封闭 id 取规则源 pin；未知 id 直接拒（不接受调用方自带的路径或摘要）。"""

    try:
        return _RULE_SOURCE_PINS[rule_source_id]
    except KeyError as exc:
        raise ValueError(f"未知 R2E rule_source_id: {rule_source_id!r}") from exc


def parse_log_pytest(log: str | None) -> dict[str, str]:
    """上游 `parse_log_pytest` 逐字移植：pytest `short test summary info` 段 → {测试名: 状态}。

    例：`PASSED r2e_tests/test_1.py::TestA::test_x` → `{"TestA.test_x": "PASSED"}`；
    `FAILED r2e_tests/test_1.py::test_y - AssertionError: …` → `{"test_y": "FAILED"}`；
    没有该段 → `{}`（零解析，由 manager 的 P-A 三路判定接手，本函数不抛异常）。
    """

    if log is None or SHORT_SUMMARY_MARKER not in log:
        return {}
    out: dict[str, str] = {}
    for line in log.split(SHORT_SUMMARY_MARKER)[1].strip().split("\n"):
        if "PASSED" in line:
            out[".".join(line.split("::")[1:])] = "PASSED"
        elif "FAILED" in line:
            out[".".join(line.split("::")[1:]).split(" - ")[0]] = "FAILED"
        elif "ERROR" in line:
            parts = line.split("::")
            # 收集错误的 ERROR 行可能没有 "::"（只给文件名）——整行作键，不产出空键
            name = ".".join(parts[1:]) if len(parts) > 1 else line
            out[name.split(" - ")[0]] = "ERROR"
    return out


_DECOLOR_RE = re.compile(r"\x1b\[\d+m")


def decolor_keys(d: dict[str, str]) -> dict[str, str]:
    """上游 `_decolor`：删键里的单参数 ANSI 序列（`\\x1b[1m` 这类）。见模块头第 2 条。"""

    return {_DECOLOR_RE.sub("", k): v for k, v in d.items()}


def normalize_status_map(d: dict[str, str]) -> dict[str, str]:
    """期望侧与观测侧共用的键归一化：去色 → 按键排序 → 截 `" - "`。见模块头第 3 条。"""

    decolored = decolor_keys(d)
    return {k.split(" - ")[0]: decolored[k] for k in sorted(decolored)}


def prime_calculate_reward(test_output: str | None, expected_output_json: str) -> float:
    """上游 `calculate_reward` 的原样行为（**只用于对拍 / 对账**，生产判定见 `scoring.parse_eval_log_r2e`）。"""

    parse = normalize_status_map(parse_log_pytest(test_output))
    expected = normalize_status_map(json.loads(expected_output_json))
    if len(parse) != len(expected):
        return 0.0
    for k in parse:
        if k and (k not in expected or parse[k] != expected[k]):
            return 0.0
    return 1.0


def is_gold_excluded_test_path(path: str) -> bool:
    """上游 `extract_gold_patch` 的测试文件判据（gold 只含 agent 该改的源码，测试来自镜像）。"""

    parts = path.split("/")
    return (
        path.endswith("_test.py")
        or parts[-1].startswith("test_")
        or any(p in ("tests", "Tests", "test", "Test") for p in parts)
    )


def extract_gold_patch(parsed_commit_content: str | dict, only_python: bool = True) -> str:
    """上游 `extract_gold_patch` 逐字移植：由 `parsed_commit_content` 的 hunk 重建 unified diff。

    只含非测试 `.py` 文件。重建出的补丁与"按 old/new 文件内容重新 diff"的补丁**字节不同**（头部与 hunk 分块
    不同），但在来源旧文件上应用后的内容相同（B 线 B2：48/48）——对账比较纳入文件集合与应用结果，不比字节。
    """

    if not parsed_commit_content:  # 没有 commit JSON 的行：没有 gold 可建
        return ""
    data = json.loads(parsed_commit_content) if isinstance(parsed_commit_content, str) else parsed_commit_content
    patch = ""
    for fd in data.get("file_diffs", []):
        path = fd.get("header", {}).get("file", {}).get("path", "")
        if not path or (only_python and not path.endswith(".py")):
            continue
        if is_gold_excluded_test_path(path):
            continue
        patch += f"diff --git a/{path} b/{path}\n"
        if fd.get("header", {}).get("misc_line"):
            patch += fd["header"]["misc_line"] + "\n"
        index_line = fd.get("index_line")
        if index_line:
            mode = index_line.get("mode", "")
            patch += (
                f"index {index_line.get('old_commit_hash', '')}..{index_line.get('new_commit_hash', '')}"
                f"{' ' if mode else ''}{mode}\n"
            )
        minus, plus = fd.get("minus_file"), fd.get("plus_file")
        if minus and plus:
            patch += f"--- {minus['path']}\n+++ {plus['path']}\n"
        for hunk in fd.get("hunks", []):
            desc = hunk.get("descriptor", {})
            old, new = desc.get("old_range", {}), desc.get("new_range", {})
            old_str = str(old.get("start", 0)) + (f",{old['length']}" if old.get("length") is not None else "")
            new_str = str(new.get("start", 0)) + (f",{new['length']}" if new.get("length") is not None else "")
            patch += f"@@ -{old_str} +{new_str} @@" + (f" {desc['section']}" if desc.get("section") else "") + "\n"
            for line in hunk.get("line_group", {}).get("all_lines", []):
                c, t = line.get("content", ""), line.get("type", "")
                patch += {
                    "context": f" {c}\n",
                    "added": f"+{c}\n",
                    "deleted": f"-{c}\n",
                    "note": f"\\ {c}\n",
                }.get(t, "")
    return patch


def gold_patch_included_paths(parsed_commit_content: str | dict, only_python: bool = True) -> list[str]:
    """`extract_gold_patch` 纳入的文件路径（与上面同判据；对账"纳入文件集合"用）。"""

    if not parsed_commit_content:
        return []
    data = json.loads(parsed_commit_content) if isinstance(parsed_commit_content, str) else parsed_commit_content
    out: list[str] = []
    for fd in data.get("file_diffs", []):
        path = fd.get("header", {}).get("file", {}).get("path", "")
        if not path or (only_python and not path.endswith(".py")):
            continue
        if is_gold_excluded_test_path(path):
            continue
        out.append(path)
    return out
