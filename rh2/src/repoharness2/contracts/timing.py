"""GradingTimingRecord：评分链路五类计时 + 容器峰值/队列等待（F5 用户收紧版）。

F5 定案原文的落点："evidence 记录容器峰值、队列等待、评分耗时与
prep/test/env_reset/image_pull 分段耗时"。即五类计时 =

  1. image_pull_seconds   评分镜像拉取（预拉取命中时可为 0.0）
  2. env_reset_seconds    评分沙箱环境重置 / fresh checkout 准备
  3. prep_seconds         patch 导出、hygiene 检查、test reset 等评分前置
  4. test_seconds         官方测试命令实际运行时长
  5. total_grading_seconds 评分请求端到端总时长（从出队到产出 GradingReport）

外加两个资源事实：queue_wait_seconds（有界评分队列 P11 的排队时长）与
container_peak_memory_mb（评分容器内存峰值）。这些数字直接支撑 F5 的
"实测稳定后再把并发 4 升 8"决策，因此全部必填——不许"忘了测"。
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from repoharness2.contracts._base import NonEmptyStr, StrictModel


class GradingTimingRecord(StrictModel):
    """一次评分动作的计时与资源画像（可独立存证，也可内嵌进 GradingReport）。

    fail-closed 行为：所有时长非负；total_grading_seconds 必须 >= test_seconds
    （测试运行包含在评分总时长内，总时长小于分段是明显的记录错误）。
    """

    schema_id: Literal["rh2.grading_timing_record.v1"] = Field(
        default="rh2.grading_timing_record.v1", description="schema 判别字段。"
    )
    record_id: NonEmptyStr = Field(description="计时记录 id。")
    trajectory_id: NonEmptyStr = Field(description="被评分轨迹 id。")
    task_id: NonEmptyStr = Field(description="任务 id（如 django__django-11099）。")
    image_pull_seconds: float = Field(
        ge=0.0, description="计时 1/5：评分镜像拉取时长（预拉取命中记 0.0，P10 第一档）。"
    )
    env_reset_seconds: float = Field(
        ge=0.0, description="计时 2/5：评分沙箱环境重置 / clean checkout 准备时长。"
    )
    prep_seconds: float = Field(
        ge=0.0, description="计时 3/5：patch 导出 + hygiene 检查 + test reset 等前置时长。"
    )
    test_seconds: float = Field(ge=0.0, description="计时 4/5：官方测试命令运行时长。")
    total_grading_seconds: float = Field(
        ge=0.0, description="计时 5/5：评分端到端总时长（出队到 GradingReport 产出）。"
    )
    queue_wait_seconds: float = Field(
        ge=0.0, description="评分请求在有界队列中的等待时长（P11 反压观测点）。"
    )
    container_peak_memory_mb: float = Field(
        ge=0.0, description="评分容器内存峰值（MB），F5 并发升档决策的输入。"
    )
    queue_depth_at_enqueue: int | None = Field(
        default=None, ge=0, description="入队瞬间的队列深度（可选；首版队列上限 8）。"
    )
    backpressure_triggered: bool = Field(
        default=False,
        description="本次评分是否触发过反压（队列打满）。为 True 时事件还应写入 EligibilityReport。",
    )

    @model_validator(mode="after")
    def _check_totals(self) -> "GradingTimingRecord":
        if self.total_grading_seconds < self.test_seconds:
            raise ValueError(
                f"total_grading_seconds({self.total_grading_seconds}) 不得小于 "
                f"test_seconds({self.test_seconds})：测试运行包含在评分总时长之内。"
            )
        return self
