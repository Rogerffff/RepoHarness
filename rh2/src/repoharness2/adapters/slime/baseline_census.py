"""B1：baseline 生成器——materialize 尾部对容器树做一次可信 census。

信任前提：本函数在 harness 获得写权限**之前**运行（materialize 段），
树内容完全由 materializer 决定，模型尚未介入——因此允许在容器内用
find/stat/sha256sum 枚举（这不是 exporter 的信任边界问题；exporter
（B2）面对的是模型写过的树，那里才禁止容器内 Git/脚本信任）。

枚举语义 = lstat/no-follow：symlink 记 target 字节 digest 不跟随；
FIFO/socket/device 直接使枚举失败（fail-closed，不静默跳过）；排除
namespace 单独 census（排除 ≠ 消失，digest 进 manifest 审计回链）。

性能：真实 SWE 镜像数万文件的全量 census 成本在 FA-5 实测校准（已
登记递延）；本机测试用小树。
"""

from __future__ import annotations

import hashlib
from typing import Any

from repoharness2.contracts.baseline_manifest import (
    BASELINE_MANIFEST_POLICY_V1,
    BaselineEntry,
    BaselineManifestPolicy,
    BaselineWorkspaceManifestV1,
    compute_policy_digest,
)

__all__ = ["BaselineCensusError", "build_census_script", "generate_baseline_manifest", "parse_census_output"]


class BaselineCensusError(RuntimeError):
    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


def build_census_script(workdir: str, policy: BaselineManifestPolicy) -> str:
    """枚举脚本：每行 `<kind>\\t<perm>\\t<sha256>\\t<path>`；排除区行首用
    EXCL 标记（独立 census）。遇到不支持对象类型输出 UNSUPPORTED 行。"""

    prunes = " ".join(
        f"-path './{ns.rstrip('/')}' -prune -o" for ns in policy.excluded_namespaces
    )
    excl_finds = " ; ".join(
        f"find './{ns.rstrip('/')}' -type f -print 2>/dev/null | LC_ALL=C sort | "
        f"while IFS= read -r p; do printf 'EXCL\\t%s\\n' \"${{p#./}}\"; done"
        for ns in policy.excluded_namespaces
    )
    return f"""set -e
cd {workdir}
find . {prunes} \\( -type f -o -type l -o \\( ! -type d ! -type f ! -type l \\) \\) -print | LC_ALL=C sort | while IFS= read -r p; do
  rel="${{p#./}}"
  if [ -L "$p" ]; then
    tgt=$(readlink "$p" | tr -d '\\n' | sha256sum | cut -d' ' -f1)
    printf 'symlink\\t120000\\t%s\\t%s\\n' "$tgt" "$rel"
  elif [ -f "$p" ]; then
    if [ -x "$p" ]; then perm=100755; else perm=100644; fi
    sha=$(sha256sum "$p" | cut -d' ' -f1)
    printf 'regular\\t%s\\t%s\\t%s\\n' "$perm" "$sha" "$rel"
  else
    printf 'UNSUPPORTED\\t%s\\n' "$rel"
  fi
done
{excl_finds}
"""


def parse_census_output(
    text: str,
    *,
    task_id: str,
    workdir: str,
    environment_package_digest: str,
    image_manifest_digest: str,
    materialized_head: str,
    task_base_commit: str,
    policy: BaselineManifestPolicy,
) -> BaselineWorkspaceManifestV1:
    """确定性解析（纯函数，独立可测）。UNSUPPORTED 行 → fail-closed。"""

    entries: list[BaselineEntry] = []
    excluded_paths: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if parts[0] == "UNSUPPORTED":
            raise BaselineCensusError(
                "unsupported_object_in_baseline",
                f"scoreable tree 含不支持对象：{parts[1] if len(parts) > 1 else '?'}",
            )
        if parts[0] == "EXCL":
            excluded_paths.append(parts[1])
            continue
        if len(parts) != 4:
            raise BaselineCensusError("census_parse_error", f"畸形行：{line!r}")
        kind, perm, sha, path = parts
        if kind == "regular":
            entries.append(BaselineEntry(
                path=path, object_type="regular", mode=perm,  # type: ignore[arg-type]
                content_digest=f"sha256:{sha}",
            ))
        elif kind == "symlink":
            entries.append(BaselineEntry(
                path=path, object_type="symlink", mode="120000",
                symlink_target_digest=f"sha256:{sha}",
            ))
        else:
            raise BaselineCensusError("census_parse_error", f"未知类型：{kind!r}")
    entries.sort(key=lambda e: e.path)
    excluded_census_digest = (
        "sha256:" + hashlib.sha256(
            "\n".join(sorted(excluded_paths)).encode("utf-8")
        ).hexdigest()
        if excluded_paths else None
    )
    return BaselineWorkspaceManifestV1(
        task_id=task_id,
        workdir=workdir,
        environment_package_digest=environment_package_digest,
        image_manifest_digest=image_manifest_digest,
        materialized_head=materialized_head,
        task_base_commit=task_base_commit,
        policy=policy,
        policy_digest=compute_policy_digest(policy),
        entries=tuple(entries),
        excluded_census_digest=excluded_census_digest,
    )


async def generate_baseline_manifest(
    workspace: Any,
    *,
    task_id: str,
    workdir: str,
    environment_package_digest: str,
    image_manifest_digest: str,
    materialized_head: str,
    task_base_commit: str,
    policy: BaselineManifestPolicy = BASELINE_MANIFEST_POLICY_V1,
) -> BaselineWorkspaceManifestV1:
    result = await workspace.run_bash(build_census_script(workdir, policy))
    if getattr(result, "exit_code", 1) != 0:
        raise BaselineCensusError(
            "baseline_census_failed",
            f"census 脚本失败（exit={result.exit_code}）：{result.stderr.strip()[-300:]}",
        )
    return parse_census_output(
        result.stdout,
        task_id=task_id,
        workdir=workdir,
        environment_package_digest=environment_package_digest,
        image_manifest_digest=image_manifest_digest,
        materialized_head=materialized_head,
        task_base_commit=task_base_commit,
        policy=policy,
    )
