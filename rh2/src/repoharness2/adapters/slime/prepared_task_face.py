"""W1b 第一集成切片（F6）：RolloutManager actor 内的 prepared 任务面。

职责（与 bringup 的 v1 `load_bundle_pairs()` 八题任务面并列，二选一）：

1. 只读 trusted-prep 的两份产物（`envpack.prepared_tasks` 三个读取口，全部复核
   identity/digest/权限），**不调用完整 loader**；
2. 公开面 → `RolloutTaskSpec`（`grading_spec=None`：rollout 侧只携带 digest 锚，
   评分材料不再内嵌在模型侧可见路径的对象上——W2a T1）；
3. 私有面 → 同一 actor 进程持有的 `HostGradingView` 表；评分 spec/parser **在
   本进程内从 v2 safe view 构造**（`build_grading_spec_from_host_view`），闭包捕获的是
   `PrivateGradingBundleV2`（无 golden 字段），取代 v1 `build_swe_grading_spec` 捕获
   含 golden_patch 的 `PrivateGradingBundle` 的构造方式；
4. 评分材料查找只经 F4 的 `AttemptAssignment`（attempt → host 原始分派），并在
   消费时刻 `revalidated()`。

v2 eval 脚本形态说明：`PrivateGradingBundleV2` 不携带官方 eval_script 全文，只有
vendor spec 派生的 `eval_cmd`。这里按 swebench `make_eval_script_list_py` 的尾段
形态渲染（reset 测试文件 → heredoc apply test_patch → 标记 → eval_cmd + 测试文件
→ 标记 → reset），测试文件 = test_patch 触碰路径。**该脚本在真实镜像上的正确性
（含 SWE-Gym 各仓库的测试选择器与 parser 覆盖）归 T2-d/W3a 验证**；本切片只保证
对象图/所有权属性与构造接缝。
"""

from __future__ import annotations

import shlex
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from repoharness2.adapters.slime.generate import RolloutTaskSpec
from repoharness2.envpack import scoring
from repoharness2.envpack.bundles import render_user_prompt
from repoharness2.envpack.bundles_v2 import PrivateGradingBundleV2
from repoharness2.envpack.prepared_tasks import (
    PreparedTasksError,
    PreparedTasksManifest,
    load_host_grading_views,
    load_prepared_manifest,
    load_prepared_rollout_views,
    verify_prompt_data_binding,
)
from repoharness2.envpack.spec_vendor import verify_grading_eval_cmd
from repoharness2.envpack.training_view import HostGradingView, RolloutTaskView
from repoharness2.grading.manager import (
    DEFAULT_SWE_FORBIDDEN_GLOBS,
    DEFAULT_SWE_TEST_GLOBS,
    GradingEnvSpec,
    HygieneRules,
    patch_touched_paths,
)

# swebench.harness.constants 的两个日志标记（官方 parser 按它们切出测试输出段）。
# 不在模块级 import swebench（envpack 纪律：swebench 只在解析日志时惰性 import）；
# 单测与 swebench 常量逐字对拍。
V2_EVAL_START_MARKER = ">>>>> Start Test Output"
V2_EVAL_END_MARKER = ">>>>> End Test Output"
V2_EVAL_HEREDOC_DELIMITER = "EOF_RH2_V2_TEST_PATCH"
V2_EVAL_CONDA_ENV = "testbed"
V2_EVAL_TESTBED = "/testbed"


class GradingMaterialsError(RuntimeError):
    """actor 内评分材料查找/构造 fail-closed 错误（reason_code 机器可读）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


def render_v2_eval_script(grading: PrivateGradingBundleV2, test_files: Sequence[str]) -> str:
    """从 v2 评分面渲染 eval 脚本（形态对齐 swebench make_eval_script_list_py 尾段）。"""

    verify_grading_eval_cmd(grading)  # eval_cmd 消费前互检（bundles_v2 第三道防线）
    if not test_files:
        raise GradingMaterialsError(
            "v2_test_files_empty", f"{grading.instance_id}: test_patch 未触碰任何路径——无法确定测试文件，拒绝构造 eval 脚本。"
        )
    if V2_EVAL_HEREDOC_DELIMITER in grading.test_patch:
        raise GradingMaterialsError(
            "v2_heredoc_delimiter_collision", f"{grading.instance_id}: test_patch 含 heredoc 定界符，拒绝构造 eval 脚本。"
        )
    files = " ".join(shlex.quote(p) for p in test_files)
    reset = f"git checkout {grading.base_commit} {files}"
    lines = [
        "#!/bin/bash",
        "set -uxo pipefail",
        "source /opt/miniconda3/bin/activate",
        f"conda activate {V2_EVAL_CONDA_ENV}",
        f"cd {V2_EVAL_TESTBED}",
        f"git config --global --add safe.directory {V2_EVAL_TESTBED}",
        "git status",
        "git show",
        f"git -c core.fileMode=false diff {grading.base_commit}",
        reset,
        f"git apply -v - <<'{V2_EVAL_HEREDOC_DELIMITER}'",
        grading.test_patch,
        V2_EVAL_HEREDOC_DELIMITER,
        f": '{V2_EVAL_START_MARKER}'",
        f"{grading.eval_cmd} {files}",
        f": '{V2_EVAL_END_MARKER}'",
        reset,
    ]
    return "\n".join(lines) + "\n"


def build_grading_spec_from_host_view(
    view: HostGradingView, *, image: str, image_manifest_digest: str
) -> GradingEnvSpec:
    """actor 内从 v2 safe view 构造评分 spec：parser 闭包只捕获 PrivateGradingBundleV2（无 golden）。"""

    grading = view.grading
    test_files = tuple(sorted(patch_touched_paths(grading.test_patch)))

    def _parse(log_text: str) -> scoring.EvalVerdict:
        return scoring.parse_eval_log(grading, log_text)

    return GradingEnvSpec(
        task_id=view.task_id,
        image=image,
        base_commit=grading.base_commit,
        image_manifest_digest=image_manifest_digest,
        eval_script=render_v2_eval_script(grading, test_files),
        parse_log=_parse,
        grader_version=f"swebench-{scoring.swebench_version()}",
        hygiene=HygieneRules(
            test_files=test_files,
            test_globs=DEFAULT_SWE_TEST_GLOBS,
            forbidden_globs=DEFAULT_SWE_FORBIDDEN_GLOBS,
        ),
        checkout_mode="image_embedded",
    )


def rollout_spec_from_view(view: RolloutTaskView, *, time_budget_seconds: int) -> RolloutTaskSpec:
    """RolloutTaskView → 模型侧任务面（grading_spec=None：只带 digest 锚）。"""

    public = view.public
    return RolloutTaskSpec(
        task_id=view.task_id,
        image=public.image,
        base_commit=public.base_commit,
        image_manifest_digest=public.image_manifest_digest,
        prompt=render_user_prompt(public),
        public_bundle_payload=public.model_dump_json(indent=2).encode("utf-8"),
        public_bundle_digest=view.public_bundle_digest,
        grading_spec=None,
        workdir=public.workdir,
        time_budget_seconds=time_budget_seconds,
    )


class PreparedTaskFace:
    """actor 内任务面：公开 RolloutTaskSpec 表 + host 侧 HostGradingView 表 + manifest 记录。"""

    def __init__(
        self,
        *,
        manifest: PreparedTasksManifest,
        rollout_views: dict[str, RolloutTaskView],
        host_grading_views: dict[str, HostGradingView],
        time_budget_seconds: int,
    ) -> None:
        if set(rollout_views) != set(manifest.task_ids()) or set(host_grading_views) != set(manifest.task_ids()):
            raise PreparedTasksError("任务面两侧视图集合与 manifest 不一致，拒绝构造")
        self._manifest = manifest
        self._rollout_views = rollout_views
        self._host_grading_views = host_grading_views
        self._specs = {
            tid: rollout_spec_from_view(view, time_budget_seconds=time_budget_seconds)
            for tid, view in rollout_views.items()
        }

    @classmethod
    def load(
        cls,
        *,
        prepared_dir: Path | str,
        host_grading_path: Path | str | None,
        host_grading_sha256: str | None,
        time_budget_seconds: int,
        prompt_data_path: Any = None,
    ) -> "PreparedTaskFace":
        """从两份产物加载（全部复核）；``prompt_data_path`` 非 None 时把 miles 数据源读的
        文件与 prep 的 prompts.jsonl 按内容 digest 绑定。"""

        if not host_grading_path or not host_grading_sha256:
            raise PreparedTasksError(
                "prepared 链要求同时给出 runtime-private 产物的 opaque 路径与期望 sha256"
                "（RH2_HOST_GRADING_ARTIFACT_PATH / RH2_HOST_GRADING_ARTIFACT_SHA256）"
            )
        manifest = load_prepared_manifest(prepared_dir)
        rollout_views = load_prepared_rollout_views(prepared_dir, manifest)
        host_views = load_host_grading_views(host_grading_path, expected_sha256=host_grading_sha256, manifest=manifest)
        if prompt_data_path is not None:
            verify_prompt_data_binding(prompt_data_path, manifest)
        return cls(
            manifest=manifest,
            rollout_views=rollout_views,
            host_grading_views=host_views,
            time_budget_seconds=time_budget_seconds,
        )

    @property
    def manifest(self) -> PreparedTasksManifest:
        return self._manifest

    def task_ids(self) -> tuple[str, ...]:
        return self._manifest.task_ids()

    def verify_dispatch(self, assignment: Any) -> None:
        """F4 绑定时的 manifest 核对：分派三元组必须是 manifest 同一行记录的值。"""

        rec = self._manifest.record(assignment.task_id)
        if (
            rec.environment_package_digest != assignment.environment_package_digest
            or rec.public_bundle_digest != assignment.public_bundle_digest
        ):
            raise PreparedTasksError(
                f"{assignment.task_id}: 分派 digest 与 prepared manifest 记录不符——不是 host 原始分派的三元组"
            )

    def rollout_spec(self, task_id: str) -> RolloutTaskSpec:
        spec = self._specs.get(task_id)
        if spec is None:
            raise PreparedTasksError(f"unknown task_id（prepared 任务面不存在）: {task_id!r}")
        return spec

    def grading_spec(self, assignment: Any) -> GradingEnvSpec:
        """按 attempt 绑定的分派取评分材料：manifest 核对 → digest 贯穿核对 → revalidated() → 构造 spec。"""

        try:
            self.verify_dispatch(assignment)
        except PreparedTasksError as exc:
            raise GradingMaterialsError("grading_dispatch_not_authoritative", str(exc)) from exc
        view = self._host_grading_views.get(assignment.task_id)
        if view is None:
            raise GradingMaterialsError(
                "grading_view_missing", f"{assignment.task_id}: actor 内没有对应的 host grading 视图。"
            )
        if view.environment_package_digest != assignment.environment_package_digest:
            raise GradingMaterialsError(
                "grading_environment_digest_mismatch",
                f"{assignment.task_id}: attempt 绑定的 environment_package_digest 与 host grading 视图不符——拒绝评分 join。",
            )
        try:
            view = view.revalidated()
        except Exception as exc:  # noqa: BLE001 - 消费时刻重验失败即拒绝
            raise GradingMaterialsError(
                "grading_view_revalidation_failed", f"{assignment.task_id}: host grading 视图消费时刻重验失败：{exc}"
            ) from exc
        rollout_view = self._rollout_views[assignment.task_id]
        return build_grading_spec_from_host_view(
            view,
            image=rollout_view.public.image,
            image_manifest_digest=rollout_view.public.image_manifest_digest,
        )


__all__ = [
    "V2_EVAL_END_MARKER",
    "V2_EVAL_START_MARKER",
    "GradingMaterialsError",
    "PreparedTaskFace",
    "build_grading_spec_from_host_view",
    "render_v2_eval_script",
    "rollout_spec_from_view",
]
