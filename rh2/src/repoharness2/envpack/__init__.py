"""repoharness2.envpack：SWE 环境包库（框架无关层，S1-2）。

这是 S0-7 SweSmokeTaskset 拆两层后的**库层**：物化血缘校验（materialize）、
官方 parser 评分（scoring）、public/private bundle 拆分与冻结账本
（bundles / freeze）。它服务多个绑定面——verifiers 薄壳
（taskset/swebench_smoke.py）、S1-4 SWEGradingManager、S1-6 slime custom_generate。

**硬约束（单测钉死）**：本包及其所有子模块 import 时不得引入 verifiers，
也不得引入 swebench（swebench 只在真正解析日志时惰性 import）。
允许依赖 repoharness2.contracts（纯 pydantic 契约层）。
"""

from repoharness2.envpack.bundles import (
    DEFAULT_ALLOWED_TOOLS,
    FROZEN_V1_FILE,
    PRIVATE_ONLY_FIELD_NAMES,
    PUBLIC_SYSTEM_HINTS,
    TASKS_FILE,
    BundleLeakError,
    BundlePair,
    PrivateGradingBundle,
    PublicTaskBundle,
    load_bundle_pairs,
    load_task_entries,
    render_user_prompt,
    scan_public_bundle,
    sha256_of_text,
    split_frozen_entry,
)
from repoharness2.envpack.freeze import (
    FROZEN_SCHEMA_ID,
    FrozenRecordMismatch,
    build_freeze_record,
    build_frozen_v1,
    load_frozen_v1,
    verify_pairs_against_frozen,
    write_frozen_v1,
)
from repoharness2.envpack.materialize import (
    BASH_ENV_CONTENT,
    BASH_ENV_PATH,
    MaterializeCheck,
    MaterializeError,
    build_probe_script,
    evaluate_probe,
)
from repoharness2.envpack.scoring import (
    EVAL_SCRIPT_PATH,
    GRADER_NAME,
    EvalVerdict,
    grading_outcome_fields,
    parse_eval_log,
    parse_official_eval,
    swebench_version,
)

__all__ = [
    "BASH_ENV_CONTENT",
    "BASH_ENV_PATH",
    "DEFAULT_ALLOWED_TOOLS",
    "EVAL_SCRIPT_PATH",
    "FROZEN_SCHEMA_ID",
    "FROZEN_V1_FILE",
    "GRADER_NAME",
    "PRIVATE_ONLY_FIELD_NAMES",
    "PUBLIC_SYSTEM_HINTS",
    "TASKS_FILE",
    "BundleLeakError",
    "BundlePair",
    "EvalVerdict",
    "FrozenRecordMismatch",
    "MaterializeCheck",
    "MaterializeError",
    "PrivateGradingBundle",
    "PublicTaskBundle",
    "build_freeze_record",
    "build_frozen_v1",
    "build_probe_script",
    "evaluate_probe",
    "grading_outcome_fields",
    "load_bundle_pairs",
    "load_frozen_v1",
    "load_task_entries",
    "parse_eval_log",
    "parse_official_eval",
    "render_user_prompt",
    "scan_public_bundle",
    "sha256_of_text",
    "split_frozen_entry",
    "swebench_version",
    "verify_pairs_against_frozen",
    "write_frozen_v1",
]
