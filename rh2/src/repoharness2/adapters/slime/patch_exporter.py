"""B2：trusted exporter——静止确认后从模型写过的树导出 FrozenPatchArtifact。

信任边界（A-prime T0 第 3 条的实现选型）：**全程不调用 git**。post-run
census 复用 B1 的 find/sha256sum/readlink 枚举（纯字节事实），delta 由
host 侧对 baseline manifest 做结构化比较——repo 内的 config/hooks/
attributes/filters/external diff/textconv/index 根本没有被执行或读取的
机会（不变量由"不存在 git 进程"满足，而非命令行参数关闭）。

流程：post census（含排除区独立 census）→ host 侧 diff（纯函数）→
变更集内容抓取（base64，仅 add/modify 的文件；delete 无内容）→
FrozenPatchArtifactV1。post 树出现不支持对象（FIFO 等）= census
UNSUPPORTED 行 → typed 失败（unsafe 分类细化归 B3，本层 fail-closed）。
"""

from __future__ import annotations

import base64
import hashlib
from typing import Any

from repoharness2.adapters.slime.baseline_census import (
    BaselineCensusError,
    build_census_script,
    parse_census_output,
)
from repoharness2.contracts.baseline_manifest import (
    BaselineWorkspaceManifestV1,
    compute_baseline_manifest_digest,
)
from repoharness2.contracts.frozen_patch import FrozenPatchArtifactV1, PatchEntry

__all__ = ["PatchExportError", "diff_census_against_baseline", "export_frozen_patch"]


class PatchExportError(RuntimeError):
    def __init__(
        self,
        reason_code: str,
        message: str,
        *,
        object_path: str | None = None,
        object_type: str | None = None,
    ) -> None:
        self.reason_code = reason_code
        # B5 复核三轮 P1-1：unsupported 对象的路径/类型结构化透传
        self.object_path = object_path
        self.object_type = object_type
        super().__init__(f"{reason_code}: {message}")


def diff_census_against_baseline(
    baseline: BaselineWorkspaceManifestV1,
    post_entries: dict[str, Any],
) -> list[dict[str, Any]]:
    """结构化比较（纯函数）：返回 [{path, operation, object_type, mode,
    digest}]，digest 为 post 侧对象 digest（delete 无）。

    检出面：内容变化（含 untracked——census 对全部受支持路径哈希内容，
    没有 git 的 staged/unstracked 概念差）、mode-only 变化、类型变化
    （regular⟷symlink = modify）、新增、删除。
    """

    base_by_path = {e.path: e for e in baseline.entries}
    changes: list[dict[str, Any]] = []
    for path, post in sorted(post_entries.items()):
        base = base_by_path.get(path)
        post_digest = (
            post.content_digest if post.object_type == "regular"
            else post.symlink_target_digest
        )
        if base is None:
            changes.append(dict(path=path, operation="add",
                                object_type=post.object_type, mode=post.mode,
                                digest=post_digest))
            continue
        base_digest = (
            base.content_digest if base.object_type == "regular"
            else base.symlink_target_digest
        )
        if (base.object_type, base.mode, base_digest) != (
            post.object_type, post.mode, post_digest
        ):
            changes.append(dict(path=path, operation="modify",
                                object_type=post.object_type, mode=post.mode,
                                digest=post_digest))
    for path, base in base_by_path.items():
        if path not in post_entries:
            changes.append(dict(path=path, operation="delete",
                                object_type=base.object_type, mode=None,
                                digest=None))
    changes.sort(key=lambda c: c["path"])
    return changes


def _shell_quote(path: str) -> str:
    return "'" + path.replace("'", "'\\''") + "'"


def build_content_fetch_script(workdir: str, paths_regular: list[str],
                               paths_symlink: list[str]) -> str:
    """变更集内容抓取（无 git）：regular 输出文件 base64，symlink 输出
    target 字节 base64；每行 `<path>\\t<b64>`（b64 无换行）。"""

    lines = ["set -e", f"cd {workdir}"]
    for p in paths_regular:
        q = _shell_quote(p)
        lines.append(
            f"printf '%s\\t' {q}; base64 < {q} | tr -d '\\n'; printf '\\n'"
        )
    for p in paths_symlink:
        q = _shell_quote(p)
        lines.append(
            f"printf '%s\\t' {q}; readlink {q} | tr -d '\\n' | base64 | tr -d '\\n'; printf '\\n'"
        )
    return "\n".join(lines) + "\n"


async def export_frozen_patch(
    workspace: Any,
    baseline: BaselineWorkspaceManifestV1,
    *,
    rollout_execution_id: str,
    physical_attempt_id: str,
) -> FrozenPatchArtifactV1:
    # B2 closure P1-1：baseline digest 单一事实源——由 exporter 对实际
    # 消费的 baseline 对象内部重算，不接受调用方另填（B3 以此为身份锚）
    baseline_manifest_digest = compute_baseline_manifest_digest(baseline)
    # 1) post-run census（同 B1 脚本；无 git；UNSUPPORTED fail-closed）
    result = await workspace.run_bash(
        build_census_script(baseline.workdir, baseline.policy)
    )
    if getattr(result, "exit_code", 1) != 0:
        raise PatchExportError(
            "post_census_failed",
            f"post census 失败（exit={result.exit_code}）：{result.stderr.strip()[-300:]}",
        )
    try:
        post = parse_census_output(
            result.stdout,
            task_id=baseline.task_id,
            workdir=baseline.workdir,
            public_bundle_digest=baseline.public_bundle_digest,
            runtime_image_digest=baseline.runtime_image_digest,
            materialized_head=baseline.materialized_head,
            task_base_commit=baseline.task_base_commit,
            policy=baseline.policy,
        )
    except BaselineCensusError as exc:
        # 不支持对象（模型产出 FIFO 等）单列（B3 按 unsafe artifact 分类）
        if exc.reason_code == "unsupported_object_in_baseline":
            raise PatchExportError(
                "unsupported_object_in_patch",
                str(exc),
                object_path=exc.object_path,
                object_type=exc.object_type,
            ) from exc
        raise PatchExportError("post_census_parse_failed", str(exc)) from exc

    post_by_path = {e.path: e for e in post.entries}
    changes = diff_census_against_baseline(baseline, post_by_path)

    # 2) 内容抓取（仅 add/modify）
    need_regular = [c["path"] for c in changes
                    if c["operation"] != "delete" and c["object_type"] == "regular"]
    need_symlink = [c["path"] for c in changes
                    if c["operation"] != "delete" and c["object_type"] == "symlink"]
    contents: dict[str, str] = {}
    if need_regular or need_symlink:
        fetch = await workspace.run_bash(
            build_content_fetch_script(baseline.workdir, need_regular, need_symlink)
        )
        if getattr(fetch, "exit_code", 1) != 0:
            raise PatchExportError(
                "content_fetch_failed",
                f"内容抓取失败（exit={fetch.exit_code}）：{fetch.stderr.strip()[-300:]}",
            )
        for line in fetch.stdout.splitlines():
            if not line:
                continue
            path, _, b64 = line.partition("\t")
            contents[path] = b64

    # 3) 组装 + **变更内容一致性检查**（closure 更名：只覆盖已识别
    # add/modify entry 的抓取内容 vs census digest，不是全树 writer-zero
    # 证明——writer-zero 的 owner 是 quiescence barrier）
    entries: list[PatchEntry] = []
    for c in changes:
        if c["operation"] == "delete":
            entries.append(PatchEntry(path=c["path"], operation="delete",
                                      object_type=c["object_type"]))
            continue
        b64 = contents.get(c["path"])
        if b64 is None:
            raise PatchExportError(
                "content_fetch_incomplete", f"变更文件未取到内容：{c['path']!r}"
            )
        raw = base64.b64decode(b64, validate=True)
        digest = "sha256:" + hashlib.sha256(raw).hexdigest()
        if digest != c["digest"]:
            raise PatchExportError(
                "content_digest_race",
                f"{c['path']!r} 抓取内容与 census digest 不符——静止期间存在写者。",
            )
        entries.append(PatchEntry(
            path=c["path"], operation=c["operation"], object_type=c["object_type"],
            mode=c["mode"], content_b64=b64, content_digest=digest,
        ))

    return FrozenPatchArtifactV1(
        task_id=baseline.task_id,
        rollout_execution_id=rollout_execution_id,
        physical_attempt_id=physical_attempt_id,
        baseline_manifest_digest=baseline_manifest_digest,
        public_bundle_digest=baseline.public_bundle_digest,
        runtime_image_digest=baseline.runtime_image_digest,
        materialized_head=baseline.materialized_head,
        entries=tuple(entries),
        excluded_pathset_changed=(
            post.excluded_census_digest != baseline.excluded_census_digest
        ),
    )
