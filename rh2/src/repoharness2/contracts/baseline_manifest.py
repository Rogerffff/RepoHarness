"""B1（F2-2b 重构切片）：BaselineWorkspaceManifestV1——评分基线唯一权威。

A-prime T0 第 2 条：trusted materialization 完成后、harness 获得写权限前
生成；覆盖 **scoreable tree 内全部受支持路径**（不由实现者裁量"与评分
无关"）；排除 namespace 显式、版本化并进入 manifest policy digest；
lstat/no-follow 语义记录 path/type/mode/content 或 symlink digest；绑定
image、environment、materialized head 与 base_commit lineage。
fresh grader 应用 projection 前必须重建并验证同一 manifest digest。

digest 口径（A-prime 第 5 条防自引用）：manifest 自身 digest 不作为
字段存在，由 `compute_baseline_manifest_digest()` 对 canonical JSON
重算，读写双方各自计算比对（外层 ArtifactRef/audit 承载值）。

路径碰撞口径（codex 三轮修正）：只拒绝目标评分文件系统无法无损表达的
碰撞——Linux case-sensitive grader 下 Foo.py 与 foo.py 合法共存；
父子前缀冲突（同一 path 既是文件又是他人目录前缀）仍拒绝。
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from ._base import GitSha, NonEmptyStr, Sha256Digest, StrictModel

__all__ = [
    "BASELINE_MANIFEST_POLICY_V1",
    "BaselineEntry",
    "BaselineManifestPolicy",
    "BaselineWorkspaceManifestV1",
    "compute_baseline_manifest_digest",
    "compute_policy_digest",
]


def _check_canonical_path(path: str) -> None:
    if path.startswith("/"):
        raise ValueError(f"路径必须相对：{path!r}")
    # 控制字符（含 TAB/LF/NUL/DEL）一律拒绝：census 线协议 `\t` 分隔 `\n`
    # 分行，带这些字节会破坏解析并让 digest 可碰撞（Falsifier F5，与
    # frozen_patch._check_canonical_path 同一收口）。空格保留。
    for ch in path:
        if ch < "\x20" or ch == "\x7f":
            raise ValueError(f"路径含控制字符（0x{ord(ch):02x}）：{path!r}")
    parts = path.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise ValueError(f"路径必须 canonical（无空段/./..）：{path!r}")


class BaselineManifestPolicy(StrictModel):
    """排除 namespace 政策（显式、版本化；digest 进 manifest 身份）。"""

    policy_version: NonEmptyStr = Field(description="政策版本号（改动即换版本）。")
    excluded_namespaces: tuple[NonEmptyStr, ...] = Field(
        description="被排除的目录前缀（以 / 结尾；如 .git/、.harness/）。"
    )

    @model_validator(mode="after")
    def _check(self) -> "BaselineManifestPolicy":
        for ns in self.excluded_namespaces:
            if not ns.endswith("/"):
                raise ValueError(f"排除 namespace 必须以 / 结尾：{ns!r}")
            _check_canonical_path(ns.rstrip("/"))
        if list(self.excluded_namespaces) != sorted(set(self.excluded_namespaces)):
            raise ValueError("excluded_namespaces 必须排序且唯一。")
        return self


# v1 生效政策：.git/（repo 元数据非 scoreable 内容）与 .harness/
# （runtime 私有——A-prime 第 6 条：记录并排除，不静默消失：生成器对
# 排除区产出独立 census 供审计）
BASELINE_MANIFEST_POLICY_V1 = BaselineManifestPolicy(
    policy_version="baseline_policy_v1",
    excluded_namespaces=(".git/", ".harness/"),
)


def compute_policy_digest(policy: BaselineManifestPolicy) -> str:
    canonical = json.dumps(
        policy.model_dump(mode="json"), sort_keys=True, ensure_ascii=False,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class BaselineEntry(StrictModel):
    """一条基线路径事实（lstat/no-follow 语义）。"""

    path: NonEmptyStr = Field(description="canonical POSIX 相对路径。")
    object_type: Literal["regular", "symlink"] = Field(description="对象类型。")
    mode: Literal["100644", "100755", "120000"] = Field(description="git 语义 mode。")
    content_digest: Sha256Digest | None = Field(
        default=None, description="regular：内容 sha256。"
    )
    symlink_target_digest: Sha256Digest | None = Field(
        default=None, description="symlink：target 字节 sha256（不跟随读取目标）。"
    )

    @model_validator(mode="after")
    def _check(self) -> "BaselineEntry":
        _check_canonical_path(self.path)
        if self.object_type == "regular":
            if self.mode == "120000":
                raise ValueError("regular 不得用 symlink mode。")
            if not self.content_digest or self.symlink_target_digest is not None:
                raise ValueError("regular 必须带 content_digest 且不得带 symlink 字段。")
        else:
            if self.mode != "120000":
                raise ValueError("symlink 的 mode 必须 120000。")
            if not self.symlink_target_digest or self.content_digest is not None:
                raise ValueError("symlink 必须带 symlink_target_digest 且不得带 content。")
        return self


class BaselineWorkspaceManifestV1(StrictModel):
    """评分基线唯一权威（A-prime 第 2 条）。"""

    schema_id: Literal["rh2.fa.baseline_workspace_manifest.v1"] = Field(
        default="rh2.fa.baseline_workspace_manifest.v1", description="schema 判别字段。"
    )
    task_id: NonEmptyStr = Field(description="任务 id。")
    workdir: NonEmptyStr = Field(description="容器内 scoreable tree 根（如 /testbed）。")
    # B1 closure（codex P1-1）：lineage 按**真实事实名**记录，不互相冒充。
    # public_bundle_digest = FA task 现有事实；environment_package_digest =
    # EnvironmentPackageV1.digest()，正式链接通前保持 None（不许用 bundle
    # digest 填空——"环境包 lineage 未接通"是 formal gate blocker）。
    public_bundle_digest: Sha256Digest = Field(description="公开 bundle digest。")
    environment_package_digest: Sha256Digest | None = Field(
        default=None, description="环境包 digest（正式链接通前 None，不伪造）。"
    )
    runtime_image_digest: Sha256Digest = Field(
        description="实际运行镜像的不可变 digest（sandbox lease 实测；tag 不得伪装）。"
    )
    materialized_head: GitSha = Field(
        description="materialize 完成时刻的 HEAD commit（真实 delta 基准锚）。"
    )
    task_base_commit: GitSha = Field(
        description="任务 base commit——**仅 lineage**，不是评分基线。"
    )
    policy: BaselineManifestPolicy = Field(description="排除 namespace 政策。")
    policy_digest: Sha256Digest = Field(description="政策 digest（须与重算一致）。")
    entries: tuple[BaselineEntry, ...] = Field(
        description="scoreable tree 全部受支持路径（按 path 排序且唯一）。"
    )
    excluded_census_digest: Sha256Digest | None = Field(
        default=None,
        description="排除区（.harness/ 等）独立 census 的 digest——审计回链，"
        "排除不等于消失（A-prime 第 6 条）。",
    )

    @model_validator(mode="after")
    def _check(self) -> "BaselineWorkspaceManifestV1":
        if self.policy_digest != compute_policy_digest(self.policy):
            raise ValueError("policy_digest 与政策重算不符。")
        paths = [e.path for e in self.entries]
        if paths != sorted(paths):
            raise ValueError("entries 必须按 path 排序。")
        if len(paths) != len(set(paths)):
            raise ValueError("entries path 必须唯一。")
        path_set = set(paths)
        for p in paths:
            # 父子前缀冲突：同一名字既是文件又是他人目录前缀 → 无法表达
            segs = p.split("/")
            for i in range(1, len(segs)):
                if "/".join(segs[:i]) in path_set:
                    raise ValueError(f"父子前缀冲突：{'/'.join(segs[:i])!r} 与 {p!r}。")
            for ns in self.policy.excluded_namespaces:
                if p == ns.rstrip("/") or p.startswith(ns):
                    raise ValueError(f"entry {p!r} 落在排除 namespace {ns!r} 内。")
        return self


def compute_baseline_manifest_digest(manifest: BaselineWorkspaceManifestV1) -> str:
    """manifest digest（读写双方各自重算；不进 manifest 自身字段）。"""

    canonical = json.dumps(
        manifest.model_dump(mode="json"), sort_keys=True, ensure_ascii=False,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
