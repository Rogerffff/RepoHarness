"""GradingReport：评分结论 + 失败归因三分 + 最小 patch hygiene 结果（S1-4 / A7）。

失败归因三分（FailureCategory，02 文档 §4 契约映射表）：

  infra_failure       评分基础设施故障（容器被杀、镜像拉不下来、超时…）。
                      **绝不允许落成 reward=0**——那会把基建噪声当成负样本教给模型。
  patch_apply_failed  cleaned patch 在 clean checkout 上 apply 失败（模型产出问题）。
  tests_failed        patch 应用成功但官方测试未全过（正常负样本）。

最小 patch hygiene（A7，S1 不推迟）：从 agent workspace 导出 cleaned final patch，
在 fresh grading sandbox / clean checkout 上重放，先做测试篡改与私有文件污染检查，
再跑官方 parser。hygiene 拒绝的 patch 不允许出现"resolved"结论。

本报告是 runtime-private 审计资产：它天然要描述 test_patch/F2P 等私有事实，
因此在 inspect-rh2-artifact 的 marker 扫描中属于豁免名单（见 cli.py），
但它永远不得进入 public projection / 模型可见上下文 / 训练导出。
"""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from repoharness2.contracts._base import (
    ArtifactRef,
    NonEmptyStr,
    Sha256Digest,
    StrictModel,
)
from repoharness2.contracts.timing import GradingTimingRecord

GradingFailureCategory = Literal["infra_failure", "patch_apply_failed", "tests_failed"]

GradingOutcome = Literal[
    "resolved",  # 官方 parser 判 RESOLVED_FULL（全部 F2P 过且 P2P 无一失败）
    "unresolved",  # 评了分但未解决（patch_apply_failed 或 tests_failed）
    "failed_to_grade",  # 评分动作本身失败（唯一合法归因是 infra_failure）
]

PatchHygieneVerdict = Literal[
    "clean",  # 未发现篡改与污染，可以进入官方评分
    "rejected_test_tampering",  # patch 触碰了测试文件（评分前会被 reset，但企图必须记录并拒绝）
    "rejected_forbidden_contamination",  # patch 触碰了题面/运行时私有/grader-only 文件
]


class PatchHygieneResult(StrictModel):
    """cleaned final patch 的卫生检查结论（A7 最小集）。

    fail-closed 行为：verdict 与两个布尔事实必须互洽——
    verdict=clean 时两个布尔必须都是 False；test_files_modified=True 时
    verdict 必须是 rejected_test_tampering；forbidden_path_touched=True 时
    verdict 不得为 clean。矛盾组合一律拒收。
    """

    cleaned_patch_digest: Sha256Digest = Field(
        description="从 agent workspace 导出并清洗后的 final patch 内容 digest（重放与审计锚点）。"
    )
    replayed_on_clean_checkout: bool = Field(
        description="是否在 fresh grading sandbox / clean checkout 上重放（A7 要求 True；False 表示同容器评分的旧形态，gate 会降级）。"
    )
    test_files_modified: bool = Field(
        description="patch 是否修改了官方测试文件（篡改企图，verdict 必须随之为 rejected_test_tampering）。"
    )
    forbidden_path_touched: bool = Field(
        description="patch 是否触碰题面文件 / 运行时私有文件 / grader-only 文件。"
    )
    forbidden_paths: list[NonEmptyStr] = Field(
        default_factory=list,
        description="被触碰的禁区路径列表（相对路径）。当且仅当 forbidden_path_touched=True 时非空。",
    )
    verdict: PatchHygieneVerdict = Field(description="hygiene 结论三分。")

    @model_validator(mode="after")
    def _check_verdict_consistency(self) -> "PatchHygieneResult":
        if self.verdict == "clean" and (self.test_files_modified or self.forbidden_path_touched):
            raise ValueError(
                "verdict=clean 与篡改/污染事实矛盾："
                f"test_files_modified={self.test_files_modified}, "
                f"forbidden_path_touched={self.forbidden_path_touched}。"
            )
        if self.test_files_modified and self.verdict != "rejected_test_tampering":
            raise ValueError(
                "test_files_modified=True 时 verdict 必须是 rejected_test_tampering（测试篡改优先级最高）。"
            )
        if (
            not self.test_files_modified
            and self.forbidden_path_touched
            and self.verdict != "rejected_forbidden_contamination"
        ):
            raise ValueError(
                "forbidden_path_touched=True（且无测试篡改）时 verdict 必须是 rejected_forbidden_contamination。"
            )
        if self.forbidden_path_touched != bool(self.forbidden_paths):
            raise ValueError(
                "forbidden_paths 非空 当且仅当 forbidden_path_touched=True"
                f"（得到 touched={self.forbidden_path_touched}, paths={self.forbidden_paths}）。"
            )
        return self


class GradingReport(StrictModel):
    """一次评分动作的完整结论（SWEGradingManager 的输出契约）。

    创建者：SWEGradingManager（S1-4，生命周期第 6 步，在 custom_generate 编排内）。
    消费者：RewardFacts（reward 出处）、EligibilityGate 的 clean_grading 维度、
    故障注入测试（杀容器 -> infra_failure）、F5 吞吐画像。

    fail-closed 校验清单：
    1. outcome=failed_to_grade <=> failure_category=infra_failure，且 reward 必须为 None
       （关键非法样例：infra_failure + reward=0.0 直接拒收）；
    2. outcome=unresolved 必须归因 patch_apply_failed 或 tests_failed，且 reward 必填；
    3. outcome=resolved 不得携带 failure_category，reward 必填且 > 0；
    4. hygiene verdict 非 clean 时 outcome 不得为 resolved（被拒 patch 不许拿满分）；
    5. F2P/P2P 计数只在测试真正跑过时在场（failed_to_grade / patch_apply_failed 时必须为 None）。
    """

    schema_id: Literal["rh2.grading_report.v1"] = Field(
        default="rh2.grading_report.v1", description="schema 判别字段。"
    )
    report_id: NonEmptyStr = Field(description="评分报告 id（RewardFacts.reward_event_refs 指向它）。")
    trajectory_id: NonEmptyStr = Field(description="被评分轨迹 id。")
    task_id: NonEmptyStr = Field(description="任务 id。")
    grader_name: NonEmptyStr = Field(
        description="评分器名称（S1：swebench_official_parser——官方 make_test_spec + get_eval_report 链路）。"
    )
    grader_version: NonEmptyStr = Field(description="评分器/解析库版本（如 swebench==4.1.0）。")
    outcome: GradingOutcome = Field(description="评分结论三态。")
    failure_category: GradingFailureCategory | None = Field(
        default=None,
        description="失败归因三分。resolved 时必须为 None；unresolved/failed_to_grade 时必填且互斥约束见校验器。",
    )
    reward: float | None = Field(
        default=None,
        description=(
            "标量 reward（S1 语义：resolved=1.0，unresolved=0.0）。"
            "infra_failure 时必须为 None——评不了分就没有 reward，绝不用 0.0 顶替。"
        ),
    )
    f2p_pass_count: int | None = Field(
        default=None, ge=0, description="FAIL_TO_PASS 通过数（仅测试真正运行后在场）。"
    )
    f2p_total_count: int | None = Field(
        default=None, ge=0, description="FAIL_TO_PASS 总数。"
    )
    p2p_fail_count: int | None = Field(
        default=None, ge=0, description="PASS_TO_PASS 失败数（回归计数，resolved 要求为 0）。"
    )
    p2p_total_count: int | None = Field(
        default=None, ge=0, description="PASS_TO_PASS 总数。"
    )
    patch_hygiene: PatchHygieneResult | None = Field(
        default=None,
        description="patch 卫生检查结果。除 failed_to_grade（hygiene 可能根本没跑到）外必填。",
    )
    infra_failure_detail: NonEmptyStr | None = Field(
        default=None,
        description="infra_failure 的具体故障描述（如 grading_container_killed）。failed_to_grade 时必填。",
    )
    eval_log_ref: ArtifactRef | None = Field(
        default=None, description="官方测试完整输出日志的 opaque 引用（runtime-private）。"
    )
    timings: GradingTimingRecord | None = Field(
        default=None, description="本次评分的五类计时与资源画像（F5；内嵌形态）。"
    )
    graded_at_utc: AwareDatetime = Field(description="评分完成时间（必须带时区）。")

    @model_validator(mode="after")
    def _check_grading_contract(self) -> "GradingReport":
        if self.outcome == "failed_to_grade":
            # 1. infra 三联：归因、无 reward、有故障描述
            if self.failure_category != "infra_failure":
                raise ValueError(
                    f"outcome=failed_to_grade 的唯一合法归因是 infra_failure，得到 {self.failure_category}。"
                )
            if self.reward is not None:
                raise ValueError(
                    f"infra_failure 时 reward 必须为 None，得到 {self.reward}"
                    "（fail-closed：基建故障绝不允许伪装成 reward=0 的负样本）。"
                )
            if self.infra_failure_detail is None:
                raise ValueError("failed_to_grade 时 infra_failure_detail 必填（故障要可归因、可复盘）。")
            if any(
                value is not None
                for value in (self.f2p_pass_count, self.f2p_total_count, self.p2p_fail_count, self.p2p_total_count)
            ):
                raise ValueError("failed_to_grade 时不得携带 F2P/P2P 计数（测试根本没有可信运行）。")
        elif self.outcome == "unresolved":
            # 2. 未解决必须归因，且 reward 在场
            if self.failure_category not in ("patch_apply_failed", "tests_failed"):
                raise ValueError(
                    "outcome=unresolved 必须归因为 patch_apply_failed 或 tests_failed，"
                    f"得到 {self.failure_category}。"
                )
            if self.reward is None:
                raise ValueError("outcome=unresolved 时 reward 必填（正常负样本，S1 语义为 0.0）。")
            if self.failure_category == "patch_apply_failed" and any(
                value is not None
                for value in (self.f2p_pass_count, self.f2p_total_count, self.p2p_fail_count, self.p2p_total_count)
            ):
                raise ValueError("patch_apply_failed 时不得携带 F2P/P2P 计数（测试未运行）。")
        else:  # resolved
            # 3. resolved 三联：无归因、reward>0、测试计数在场
            if self.failure_category is not None:
                raise ValueError(f"outcome=resolved 不得携带 failure_category（得到 {self.failure_category}）。")
            if self.reward is None or self.reward <= 0.0:
                raise ValueError(
                    f"outcome=resolved 要求 reward 为正数（S1 语义 1.0），得到 {self.reward}。"
                )
            counts = (self.f2p_pass_count, self.f2p_total_count, self.p2p_fail_count, self.p2p_total_count)
            if any(value is None for value in counts):
                raise ValueError("outcome=resolved 时 F2P/P2P 四个计数必须齐全（RESOLVED_FULL 的判据输入）。")
            assert self.p2p_fail_count is not None
            if self.p2p_fail_count != 0:
                raise ValueError(
                    f"outcome=resolved 要求 p2p_fail_count=0（P2P 无一失败），得到 {self.p2p_fail_count}。"
                )
            if self.f2p_pass_count != self.f2p_total_count:
                raise ValueError(
                    f"outcome=resolved 要求全部 F2P 通过：pass={self.f2p_pass_count}, total={self.f2p_total_count}。"
                )

        # 计数自洽
        if (
            self.f2p_pass_count is not None
            and self.f2p_total_count is not None
            and self.f2p_pass_count > self.f2p_total_count
        ):
            raise ValueError(
                f"f2p_pass_count({self.f2p_pass_count}) 不得大于 f2p_total_count({self.f2p_total_count})。"
            )
        if (
            self.p2p_fail_count is not None
            and self.p2p_total_count is not None
            and self.p2p_fail_count > self.p2p_total_count
        ):
            raise ValueError(
                f"p2p_fail_count({self.p2p_fail_count}) 不得大于 p2p_total_count({self.p2p_total_count})。"
            )

        # 4. hygiene 与结论互检
        if self.outcome != "failed_to_grade" and self.patch_hygiene is None:
            raise ValueError(
                f"outcome={self.outcome} 时 patch_hygiene 必填（A7：评了分就必须有卫生检查结论）。"
            )
        if self.patch_hygiene is not None and self.patch_hygiene.verdict != "clean" and self.outcome == "resolved":
            raise ValueError(
                f"patch hygiene verdict={self.patch_hygiene.verdict} 的 patch 不得给出 resolved 结论"
                "（被拒 patch 不许拿满分）。"
            )
        if self.outcome != "failed_to_grade" and self.infra_failure_detail is not None:
            raise ValueError("非 failed_to_grade 结论不得携带 infra_failure_detail。")
        return self
