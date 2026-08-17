"""B2（F2-2b 重构切片）：FrozenPatchArtifactV1——评分消费的不可变文件 delta。

A-prime T0 第 4/5 条：结构化、排序、可重算 digest 的文件 delta；v1 支持
regular/symlink × add/modify/delete 与 mode {100644,100755,120000}，其他
对象 fail-closed；身份绑定 task/bundle/runtime image/baseline/logical
execution/physical attempt（不同 attempt 禁止覆盖——持久层强制，契约
携带身份）；artifact 自身 digest 由 `compute_frozen_patch_digest()` 外部
重算，不进字段（防自引用）。

内容承载（v1 实现口径）：delta 是模型改动集（远小于全树），content 以
inline base64 + digest 双载（读取方必须重算 digest 比对）；blob 拆分
按引用存储随 B5 持久化再做，不提前建 CAS。

排除区口径（A-prime 第 6 条）：排除 namespace 不进 entries；exporter
另行出具排除区 census 变化事实（excluded_census_changed），tamper 判定
（需权限/命令/ownership 证据）归 B3 hygiene，不在本契约预决。
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from ._base import GitSha, NonEmptyStr, Sha256Digest, StrictModel

__all__ = [
    "FrozenPatchArtifactV1",
    "PatchEntry",
    "compute_frozen_patch_digest",
]


def _check_canonical_path(path: str) -> None:
    if path.startswith("/"):
        raise ValueError(f"路径必须相对：{path!r}")
    if "\x00" in path:
        raise ValueError("路径含 NUL。")
    if any(p in ("", ".", "..") for p in path.split("/")):
        raise ValueError(f"路径必须 canonical：{path!r}")


class PatchEntry(StrictModel):
    """一条文件 delta（lstat/no-follow 语义，与 baseline entry 同构）。"""

    path: NonEmptyStr = Field(description="canonical POSIX 相对路径。")
    operation: Literal["add", "modify", "delete"] = Field(description="操作。")
    object_type: Literal["regular", "symlink"] = Field(
        description="对象类型（delete 时 = 基线中被删对象的类型）。"
    )
    mode: Literal["100644", "100755", "120000"] | None = Field(
        default=None, description="add/modify 必填；delete 必空。"
    )
    content_b64: str | None = Field(
        default=None,
        description="add/modify regular：文件内容 base64；symlink：target 字节 base64。",
    )
    content_digest: Sha256Digest | None = Field(
        default=None, description="content_b64 解码字节的 sha256（读取方必须重算）。"
    )

    @model_validator(mode="after")
    def _check(self) -> "PatchEntry":
        _check_canonical_path(self.path)
        if self.operation == "delete":
            if self.mode is not None or self.content_b64 is not None or self.content_digest is not None:
                raise ValueError("delete 不得携带 mode/content。")
            return self
        # add / modify
        if self.mode is None or self.content_b64 is None or self.content_digest is None:
            raise ValueError(f"{self.operation} 必须携带 mode + content_b64 + content_digest。")
        if self.object_type == "symlink" and self.mode != "120000":
            raise ValueError("symlink 的 mode 必须 120000。")
        if self.object_type == "regular" and self.mode == "120000":
            raise ValueError("regular 不得用 symlink mode。")
        try:
            raw = base64.b64decode(self.content_b64, validate=True)
        except Exception as exc:
            raise ValueError(f"content_b64 非法：{exc}") from exc
        digest = "sha256:" + hashlib.sha256(raw).hexdigest()
        if digest != self.content_digest:
            raise ValueError("content_digest 与 content_b64 重算不符。")
        return self


class FrozenPatchArtifactV1(StrictModel):
    """评分消费的唯一冻结输入（raw；hygiene/projection 见 B3）。"""

    schema_id: Literal["rh2.fa.frozen_patch_artifact.v1"] = Field(
        default="rh2.fa.frozen_patch_artifact.v1", description="schema 判别字段。"
    )
    task_id: NonEmptyStr = Field(description="任务 id。")
    rollout_execution_id: NonEmptyStr = Field(description="逻辑执行 id（replay 稳定）。")
    physical_attempt_id: NonEmptyStr = Field(
        description="物理 attempt id——artifact 按 attempt 唯一，禁止覆盖。"
    )
    baseline_manifest_digest: Sha256Digest = Field(
        description="B1 基线 manifest digest（delta 的锚；grader 应用前须重建验证）。"
    )
    public_bundle_digest: Sha256Digest = Field(description="公开 bundle lineage。")
    runtime_image_digest: Sha256Digest = Field(description="运行镜像不可变 digest。")
    materialized_head: GitSha = Field(description="基线 HEAD lineage（自 B1 透传）。")
    entries: tuple[PatchEntry, ...] = Field(
        description="文件 delta（按 path 排序且唯一；空 = 模型零改动）。"
    )
    excluded_census_changed: bool = Field(
        description="排除区（.harness/ 等）census 相对基线是否变化——事实记录，"
        "tamper 判定归 B3（需权限/命令证据，不得仅凭变化推断）。"
    )

    @model_validator(mode="after")
    def _check(self) -> "FrozenPatchArtifactV1":
        paths = [e.path for e in self.entries]
        if paths != sorted(paths):
            raise ValueError("entries 必须按 path 排序。")
        if len(paths) != len(set(paths)):
            raise ValueError("entries path 必须唯一。")
        path_set = set(paths)
        for p in paths:
            segs = p.split("/")
            for i in range(1, len(segs)):
                if "/".join(segs[:i]) in path_set:
                    raise ValueError(f"父子前缀冲突：{'/'.join(segs[:i])!r} 与 {p!r}。")
        return self


def compute_frozen_patch_digest(artifact: FrozenPatchArtifactV1) -> str:
    """artifact digest（读写双方各自重算；不进自身字段）。"""

    canonical = json.dumps(
        artifact.model_dump(mode="json"), sort_keys=True, ensure_ascii=False,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
