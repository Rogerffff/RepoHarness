"""官方 SWE-bench 评分日志解析（框架无关层，S1-2 从 S0-7 SweSmokeTaskset 抽出）。

解析链路（与官方 harness 同形态，S0-7 已对 8 题实测）：

    eval 脚本 stdout+stderr 合并单流日志（调用方负责 `2>&1` 合并——官方脚本
    set -x 的标记走 stderr、测试输出因 repo 而异，不合并就切不出测试段）
      -> swebench.harness.grading.get_logs_eval
         （MAP_REPO_TO_PARSER 按 repo 选 parser，切 '>>>>> Start/End Test Output'
          标记之间的段；同时检查 patch apply 失败等坏码）
      -> get_eval_tests_report 对照 F2P/P2P 清单（清单制记账，不是全日志记账）
      -> get_resolution_status（RESOLVED_FULL / RESOLVED_PARTIAL / RESOLVED_NO）

三类官方 parser 已实测覆盖（s0/swe_smoke_report.md §5）：

  1. django：unittest verbose 行 `test_validate (auth_tests.test_validators.XxxTest) ... ok`
  2. sympy：`bin/test` 行 `test_vector_simplify ok  [OK]`
  3. requests/astropy：`pytest -rA` 摘要行 `PASSED/FAILED/ERROR test_requests.py::...`
     （astropy 输出带 `\\x1b[32m` 等 ANSI 颜色码，官方 parser 自行处理，
      本层不需要也不应该先剥色——回归测试用真实带色日志钉住这一点）

官方语义的两个"如实沿用"（不加严，加严是 S1-4/S2 的活）：

  - 状态口径（2026-09-15 按 swebench 4.1.0 与 SWE-Gym fork 的 grading.py 实测改正；旧注释"缺席按通过计"是错的）：参考 ID **缺席计失败**（`test_failed` = 不在状态映射或 FAILED/ERROR）；
    PASSED/XFAIL 计成功；SKIPPED 不进成功/失败任何一桶——清单全部 SKIPPED 时 report 可得 FULL。
  - apply_ok=False 的坏码集合是并集（APPLY_PATCH_FAIL / RESET_FAILED / TESTS_ERROR /
    TESTS_TIMEOUT / 缺 Start/End 标记），官方不区分成因。本层把它映射为
    patch_apply_failed；若上层（S1-4 manager）掌握容器级证据（如评分容器被杀），
    应改判 infra_failure——那是 manager 的职责，不在 parser 层。

对 swebench 包的依赖是**惰性**的：模块 import 不需要 swebench，只有真正解析时才
import（运行机 venv 需要 swebench==4.1.0，与冻结数据的生成版本一致）。

S1-4 消费接口（A7 预留）：`parse_eval_log(private_bundle, log_text)` 得 EvalVerdict，
`grading_outcome_fields(verdict)` 把 verdict 翻成 contracts.GradingReport 的
outcome/failure_category/reward/计数字段（构造 GradingReport 所需的其余字段——
report_id/trajectory_id/patch_hygiene/timings——由 manager 补齐）。
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from repoharness2.contracts._base import NonEmptyStr, StrictModel
from repoharness2.envpack.bundles import PrivateGradingBundle

# 评分脚本在容器内的落点（绑定层写入 + 执行都用绝对路径，避开 workdir 依赖）。
EVAL_SCRIPT_PATH = "/tmp/rh2_swe_eval.sh"

# GradingReport.grader_name 的固定值（S1-4 直接引用，见 contracts/grading.py docstring）。
GRADER_NAME = "swebench_official_parser"

ResolutionStatus = Literal["RESOLVED_FULL", "RESOLVED_PARTIAL", "RESOLVED_NO"]


class EvalVerdict(StrictModel):
    """一次官方评分解析的完整结论（清单制：所有列表都是 F2P/P2P 清单内测试）。"""

    instance_id: NonEmptyStr = Field(description="被评分的 instance id。")
    apply_ok: bool = Field(
        description="日志无坏码且测试段标记齐全（False = patch/测试基建层面失败，测试结果不可信）。"
    )
    resolution: ResolutionStatus = Field(description="官方三态判定。")
    resolved: bool = Field(description="是否 RESOLVED_FULL（唯一得分态，校验器与 resolution 互检）。")
    f2p_rate: float = Field(ge=0.0, le=1.0, description="FAIL_TO_PASS 通过率（官方 compute_fail_to_pass）。")
    p2p_rate: float = Field(ge=0.0, le=1.0, description="PASS_TO_PASS 通过率（官方 compute_pass_to_pass）。")
    f2p_success: list[str] = Field(description="F2P 清单内判通过的测试（PASSED/XFAIL）。")
    f2p_failure: list[str] = Field(description="F2P 清单内判失败的测试。")
    p2p_success: list[str] = Field(description="P2P 清单内判通过的测试（PASSED/XFAIL）。")
    p2p_failure: list[str] = Field(description="P2P 清单内判失败的测试（回归项）。")
    num_parsed_tests: int = Field(ge=0, description="日志里实际解析出的测试条数（0 = 可疑，供上层加严）。")
    # S1-b（2026-09-15）诊断字段：只有 v2 入口填写；v1 路径保持默认，不影响既有消费者。
    num_parsed_outside_segment: int = Field(
        default=0, ge=0, description="Start/End 标记段之外能被 parser 认出的测试行数（诊断：段外输出不作状态来源）。"
    )
    reference_missing: list[str] = Field(
        default_factory=list, description="参考清单（F2P+P2P）里状态映射缺席的测试（官方口径计失败）。"
    )
    reference_skipped: list[str] = Field(
        default_factory=list, description="参考清单里状态为 SKIPPED 的测试（官方口径不进任何桶）。"
    )
    parser_source: str = Field(
        default="swebench_installed", description="状态映射来自哪个 parser 实现（v1 = 安装的 swebench；v2 = swegym_parsers@<commit>）。"
    )

    @model_validator(mode="after")
    def _check_resolved_consistency(self) -> "EvalVerdict":
        if self.resolved != (self.resolution == "RESOLVED_FULL"):
            raise ValueError(
                f"resolved={self.resolved} 与 resolution={self.resolution} 矛盾"
                "（resolved 当且仅当 RESOLVED_FULL）。"
            )
        if not self.apply_ok and self.resolved:
            raise ValueError("apply_ok=False 时不可能 resolved（测试结果不可信）。")
        return self

    @property
    def reward(self) -> float:
        """S1 reward 判据：1.0 当且仅当 RESOLVED_FULL，其余 0.0。"""

        return 1.0 if self.resolved else 0.0


def swebench_version() -> str:
    """运行机上 swebench 解析库的版本（GradingReport.grader_version 用）。"""

    from importlib.metadata import version

    return version("swebench")


def parse_official_eval(instance: Mapping, log_text: str) -> EvalVerdict:
    """用 swebench 官方 grading 函数解析一份合并流 eval 日志。

    instance 至少要含 make_test_spec 需要的键：instance_id / repo / version /
    base_commit / test_patch / FAIL_TO_PASS / PASS_TO_PASS（后两者官方形态是
    JSON 字符串，list 形态官方同样接受）。S0-7 的同名函数返回 dict，
    本版收紧为 EvalVerdict 严格模型，字段语义不变。
    """

    import tempfile

    from swebench.harness.constants import FAIL_TO_PASS, PASS_TO_PASS, ResolvedStatus
    from swebench.harness.grading import (
        compute_fail_to_pass,
        compute_pass_to_pass,
        get_eval_tests_report,
        get_logs_eval,
        get_resolution_status,
    )
    from swebench.harness.test_spec.test_spec import make_test_spec

    spec = make_test_spec(dict(instance), namespace="swebench", arch="x86_64")
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
        f.write(log_text)
        log_path = f.name
    try:
        status_map, apply_ok = get_logs_eval(spec, log_path)
    finally:
        Path(log_path).unlink(missing_ok=True)

    def _as_list(value) -> list[str]:
        return json.loads(value) if isinstance(value, str) else list(value)

    gold = {
        FAIL_TO_PASS: _as_list(instance["FAIL_TO_PASS"]),
        PASS_TO_PASS: _as_list(instance["PASS_TO_PASS"]),
    }
    report = get_eval_tests_report(status_map, gold)
    resolution = get_resolution_status(report)
    return EvalVerdict(
        instance_id=str(instance["instance_id"]),
        apply_ok=apply_ok,
        resolution=resolution,
        resolved=resolution == ResolvedStatus.FULL.value,
        f2p_rate=compute_fail_to_pass(report),
        p2p_rate=compute_pass_to_pass(report),
        f2p_success=report[FAIL_TO_PASS]["success"],
        f2p_failure=report[FAIL_TO_PASS]["failure"],
        p2p_success=report[PASS_TO_PASS]["success"],
        p2p_failure=report[PASS_TO_PASS]["failure"],
        num_parsed_tests=len(status_map),
    )


def parse_eval_log(private: PrivateGradingBundle, log_text: str) -> EvalVerdict:
    """bundle 形态入口：从 PrivateGradingBundle 重建官方 instance 最小键集后解析。

    这是 S1-4 GradingManager 与 verifiers 薄壳共用的评分入口——评分需要的
    全部私有材料都来自 private bundle，公有侧数据完全不参与。
    """

    instance = {
        "instance_id": private.instance_id,
        "repo": private.repo,
        "version": private.version,
        "base_commit": private.base_commit,
        "test_patch": private.test_patch,
        "FAIL_TO_PASS": list(private.fail_to_pass),
        "PASS_TO_PASS": list(private.pass_to_pass),
    }
    return parse_official_eval(instance, log_text)


def parse_eval_log_v2(grading, log_text: str) -> EvalVerdict:
    """v2 评分面入口（S1-b，评分接线 2026-09-15）：按 `spec_vendor_id` 分派 vendored parser。

    与 v1 `parse_official_eval` 的差别：

    1. 不构造 swebench `TestSpec`（4.1.0 的 spec 注册表不含 SWE-Gym 仓库，`make_test_spec` 会 KeyError）；
       parser 来自 `envpack.swegym_parsers`（fork 242429c1 的移植，按 `grading.repo_key_lower` 查表）。
    2. **只以 `>>>>> Start Test Output` 与 `>>>>> End Test Output` 之间的段作为状态来源**。4.1.0 的
       `get_logs_eval` 在段内解析为空时会回退解析整份日志（B 线复核 B2 的合成反例：段内只有收集失败文字、
       段外两行 PASSED → FULL）；这里不回退，段外能认出的行数只记进 `num_parsed_outside_segment`。
    3. 坏码集合（APPLY_PATCH_FAIL / RESET_FAILED / TESTS_ERROR / TESTS_TIMEOUT）与缺标记 → `apply_ok=False`，
       与 4.1.0 相同；report / resolution 复用 4.1.0 的 `get_eval_tests_report` / `get_resolution_status`
       （与 fork 同语义：缺席计失败、PASSED/XFAIL 计成功、SKIPPED 不进桶）。
    4. 额外填 `reference_missing` / `reference_skipped` / `parser_source` 诊断字段（不改 reward 口径）。

    `grading` 是 `PrivateGradingBundleV2`（鸭子：需要 spec_vendor_id / repo_key_lower / instance_id /
    fail_to_pass / pass_to_pass）。非 SWE-Gym vendor 直接拒绝——不静默回退到 v1。
    """

    from swebench.harness.constants import (
        APPLY_PATCH_FAIL,
        END_TEST_OUTPUT,
        FAIL_TO_PASS,
        PASS_TO_PASS,
        RESET_FAILED,
        START_TEST_OUTPUT,
        TESTS_ERROR,
        TESTS_TIMEOUT,
        ResolvedStatus,
    )
    from swebench.harness.grading import (
        compute_fail_to_pass,
        compute_pass_to_pass,
        get_eval_tests_report,
        get_resolution_status,
    )

    from repoharness2.envpack.spec_vendor import SPEC_VENDOR_ID_SWEGYM_242429C1
    from repoharness2.envpack.swegym_parsers import SWEGYM_PARSERS_VERSION_TAG, lookup_parser

    if grading.spec_vendor_id != SPEC_VENDOR_ID_SWEGYM_242429C1:
        raise ValueError(f"{grading.instance_id}: parse_eval_log_v2 只服务 {SPEC_VENDOR_ID_SWEGYM_242429C1!r}，得到 {grading.spec_vendor_id!r}")
    parser = lookup_parser(grading.repo_key_lower)

    bad_codes = [c for c in (APPLY_PATCH_FAIL, RESET_FAILED, TESTS_ERROR, TESTS_TIMEOUT) if c in log_text]
    has_markers = START_TEST_OUTPUT in log_text and END_TEST_OUTPUT in log_text
    if bad_codes or not has_markers:
        status_map: dict[str, str] = {}
        outside_map: dict[str, str] = {}
        apply_ok = False
    else:
        head, rest = log_text.split(START_TEST_OUTPUT, 1)
        if END_TEST_OUTPUT in rest:
            segment, tail = rest.split(END_TEST_OUTPUT, 1)
        else:
            # End 标记只出现在 Start 之前：段不成立，按缺标记处理（与 4.1.0 的 split 会得到空段一致地不计分）
            segment, tail = "", rest
        status_map = parser(segment)
        outside_map = parser(head + tail)
        apply_ok = True

    f2p = list(grading.fail_to_pass)
    p2p = list(grading.pass_to_pass)
    report = get_eval_tests_report(status_map, {FAIL_TO_PASS: f2p, PASS_TO_PASS: p2p})
    resolution = get_resolution_status(report)
    reference = f2p + p2p
    return EvalVerdict(
        instance_id=str(grading.instance_id),
        apply_ok=apply_ok,
        resolution=resolution,
        resolved=resolution == ResolvedStatus.FULL.value,
        f2p_rate=compute_fail_to_pass(report),
        p2p_rate=compute_pass_to_pass(report),
        f2p_success=report[FAIL_TO_PASS]["success"],
        f2p_failure=report[FAIL_TO_PASS]["failure"],
        p2p_success=report[PASS_TO_PASS]["success"],
        p2p_failure=report[PASS_TO_PASS]["failure"],
        num_parsed_tests=len(status_map),
        num_parsed_outside_segment=len(outside_map),
        reference_missing=[c for c in reference if c not in status_map],
        reference_skipped=[c for c in reference if status_map.get(c) == "SKIPPED"],
        parser_source=SWEGYM_PARSERS_VERSION_TAG,
    )


def grading_outcome_fields(verdict: EvalVerdict) -> dict:
    """把 EvalVerdict 翻成 contracts.GradingReport 的结论字段组（A7 接口）。

    返回键：outcome / failure_category / reward / f2p_pass_count / f2p_total_count /
    p2p_fail_count / p2p_total_count，取值组合保证能通过 GradingReport 的
    fail-closed 校验器：

      - apply_ok=False  -> unresolved + patch_apply_failed + reward=0.0，四计数 None
                           （官方语义：坏码即测试结果不可信，计数无意义）；
      - resolved        -> resolved + 无归因 + reward=1.0 + 四计数齐全；
      - 其余            -> unresolved + tests_failed + reward=0.0 + 四计数齐全。

    计数口径 = 官方 report 的 success/failure 桶（清单内测试的划分；skipped 等
    异态不入桶，与官方 resolution 判定保持同一口径）。**infra_failure 永远不由
    本函数产出**——parser 只看得见日志，容器级故障归 S1-4 manager 判。
    """

    if not verdict.apply_ok:
        return {
            "outcome": "unresolved",
            "failure_category": "patch_apply_failed",
            "reward": 0.0,
            "f2p_pass_count": None,
            "f2p_total_count": None,
            "p2p_fail_count": None,
            "p2p_total_count": None,
        }
    counts = {
        "f2p_pass_count": len(verdict.f2p_success),
        "f2p_total_count": len(verdict.f2p_success) + len(verdict.f2p_failure),
        "p2p_fail_count": len(verdict.p2p_failure),
        "p2p_total_count": len(verdict.p2p_success) + len(verdict.p2p_failure),
    }
    if verdict.resolved:
        return {"outcome": "resolved", "failure_category": None, "reward": 1.0, **counts}
    return {"outcome": "unresolved", "failure_category": "tests_failed", "reward": 0.0, **counts}


# ---------------------------------------------------------------------------
# R2E 方案 A（用户 2026-09-15 选定"最小接入"）：expected 状态映射的精确匹配
# ---------------------------------------------------------------------------


class ExpectedMapMatch(StrictModel):
    """R2E 的判定原料：期望映射（测试 id → 状态）与观测映射逐键比对。

    口径：`total_count` = 期望键 ∪ 观测键 的大小；`match_count` = 并集里"两边都在场且状态相等"的键数。
    多出或缺少任何一个键都让 match < total——resolved 当且仅当 keys_equal 且 match == total > 0。"""

    match_count: int = Field(ge=0)
    total_count: int = Field(ge=0)
    keys_equal: bool
    mismatched: list[str] = Field(default_factory=list, description="状态不等的键（两边都在场）。")
    missing: list[str] = Field(default_factory=list, description="期望里有、观测里没有的键。")
    unexpected: list[str] = Field(default_factory=list, description="观测里有、期望里没有的键。")

    @property
    def resolved(self) -> bool:
        return self.keys_equal and self.total_count > 0 and self.match_count == self.total_count


def expected_map_matches(expected: Mapping[str, str], observed: Mapping[str, str]) -> ExpectedMapMatch:
    """逐键精确匹配（R2E-Gym 的 resolved 口径：观测状态映射与期望映射相等）。"""

    exp_keys, obs_keys = set(expected), set(observed)
    union = sorted(exp_keys | obs_keys)
    mismatched = sorted(k for k in exp_keys & obs_keys if expected[k] != observed[k])
    missing = sorted(exp_keys - obs_keys)
    unexpected = sorted(obs_keys - exp_keys)
    match = sum(1 for k in union if k in exp_keys and k in obs_keys and expected[k] == observed[k])
    return ExpectedMapMatch(
        match_count=match, total_count=len(union), keys_equal=exp_keys == obs_keys,
        mismatched=mismatched, missing=missing, unexpected=unexpected,
    )


def grading_outcome_fields_r2e(match: ExpectedMapMatch) -> dict:
    """把 ExpectedMapMatch 翻成 GradingReport 的结论字段组（grading_semantics="r2e_expected_map"）。

    - resolved（键集相等且全部相等）→ resolved / reward 1.0 / expected 计数齐全；
    - 其余 → unresolved + tests_failed / reward 0.0 / expected 计数齐全（match < total 由口径保证）。
    四个 F2P/P2P 计数恒为 None（契约横切约束）。infra 族仍只由 manager 产出。"""

    counts = {
        "grading_semantics": "r2e_expected_map",
        "expected_match_count": match.match_count,
        "expected_total_count": match.total_count,
        "f2p_pass_count": None, "f2p_total_count": None, "p2p_fail_count": None, "p2p_total_count": None,
    }
    if match.resolved:
        return {"outcome": "resolved", "failure_category": None, "reward": 1.0, **counts}
    return {"outcome": "unresolved", "failure_category": "tests_failed", "reward": 0.0, **counts}
