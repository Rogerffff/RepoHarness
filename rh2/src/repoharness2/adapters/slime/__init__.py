"""slime 绑定：训练主线的投影 adapter（S1-3）与编排胶水（S1-6，未来）。"""

from repoharness2.adapters.slime.projection import (
    ResponseContextRun,
    SlimeBranchAnnotation,
    SlimeProjectionError,
    SlimeRewardInput,
    assert_renderer_class,
    decode_int32_tape,
    project_from_slime,
)

__all__ = [
    "ResponseContextRun",
    "SlimeBranchAnnotation",
    "SlimeProjectionError",
    "SlimeRewardInput",
    "assert_renderer_class",
    "decode_int32_tape",
    "project_from_slime",
]
