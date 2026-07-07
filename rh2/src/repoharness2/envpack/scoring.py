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

  - silent success：不在日志出现的 F2P/P2P 按通过计（官方 check_pass_and_fail 行为）。
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
    f2p_success: list[str] = Field(description="F2P 清单内判通过的测试（含 silent success）。")
    f2p_failure: list[str] = Field(description="F2P 清单内判失败的测试。")
    p2p_success: list[str] = Field(description="P2P 清单内判通过的测试（含 silent success）。")
    p2p_failure: list[str] = Field(description="P2P 清单内判失败的测试（回归项）。")
    num_parsed_tests: int = Field(ge=0, description="日志里实际解析出的测试条数（0 = 可疑，供上层加严）。")

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
