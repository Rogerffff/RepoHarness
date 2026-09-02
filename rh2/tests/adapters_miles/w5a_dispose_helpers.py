"""W5a 关停链 miles 侧测试的可 import 替身（miles `load_function` 需要模块路径）。"""

from __future__ import annotations


class FakeGroupAdmissionFatal(RuntimeError):
    """形状 = adapters/miles/group_admission.GroupAdmissionFatal（带 reason_code）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


def raising_admission_filter(args, samples, **kwargs):
    """dynamic filter 替身：在 miles `DefaultDataBuffer.put()` 内抛 fatal（复合 filter 的失败形状）。"""

    raise FakeGroupAdmissionFatal("identity_missing", "交付样本缺六字段身份（测试替身）")
