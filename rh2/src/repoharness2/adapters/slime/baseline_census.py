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

from re import escape as re_escape
from shlex import quote as shlex_quote

from repoharness2.contracts.baseline_manifest import (
    BASELINE_MANIFEST_POLICY_V1,
    BaselineEntry,
    BaselineManifestPolicy,
    BaselineWorkspaceManifestV1,
    compute_policy_digest,
)

__all__ = ["BaselineCensusError", "build_census_script", "generate_baseline_manifest", "parse_census_output"]


class BaselineCensusError(RuntimeError):
    def __init__(
        self,
        reason_code: str,
        message: str,
        *,
        object_path: str | None = None,
        object_type: str | None = None,
    ) -> None:
        self.reason_code = reason_code
        # B5 复核三轮 P1-1：不支持对象的路径/类型作为结构化事实随异常
        # 携带（workspace 清理后 receipt 仍能给出可解引用的拒绝证据）。
        self.object_path = object_path
        self.object_type = object_type
        super().__init__(f"{reason_code}: {message}")


# 第六组 E2a：普通文件的摘要位先用这个占位（64 个 0），批量哈希后按位置替换。计划行只在脚本内部的临时文件里，不会输出。
_CENSUS_DIGEST_PLACEHOLDER = "0" * 64


def build_census_script(workdir: str, policy: BaselineManifestPolicy) -> str:
    """枚举脚本：每行 `<kind>\\t<perm>\\t<sha256>\\t<path>`；排除区行首用
    EXCL 标记（独立 census）。遇到不支持对象类型输出 UNSUPPORTED 行。

    第六组 E2a（E2/E4 Brief §1.5）：枚举、排序、逐行内建分类、软链处理照旧；普通文件的摘要不再逐个 `$(sha256sum | cut)`
    起进程，而是把路径 NUL 分隔收集起来一次 `xargs -0 -r sha256sum`，按位置合并回计划行。整批结果先写进私有临时目录并
    验证（xargs 成功、摘要行数 = 普通文件数、每个摘要是 64 位十六进制），成功才输出；任何一步不符（单个文件读不了、
    临时目录建不了、工具报错）就整批丢弃、改走原来的逐文件路径，不会先输出半批再追加。两条路径在所有输入上逐字节同输出
    （真实 Linux 差分：`tests/adapters/test_e2a_batched_census.py`）。`RH2_CENSUS_FORCE_FALLBACK` 非空时直接走逐文件路径
    （只供差分测试；root 可信通道 `env -i` 清空环境，候选设置不了）。

    同批修复（差分发现）：文件名含反斜线或回车时，GNU sha256sum 在输出行首加一个转义反斜线，旧脚本 `cut -d' ' -f1`
    把它当成摘要的一部分（`\\<hash>`），契约的摘要格式拒绝它——候选建一个 `a\\b.py` 就会让解析抛字段级
    ValidationError、升级为 run-fatal。两条路径都去掉这一个转义前缀：反斜线文件名照常作为普通文件；含回车的文件名交给
    路径规则，走既有的不支持路径名处置。没有任何已落盘的基线清单含这类条目（旧脚本在生成时就会失败），既有摘要不变。"""

    prunes = " ".join(
        f"-path './{ns.rstrip('/')}' -prune -o" for ns in policy.excluded_namespaces
    )
    # 第四组 P-C（R4）：只剪**目录**（-type d），同名普通文件/软链照常列出；被剪目录下的文件只计数，不进 digest。
    cache_dirs = tuple(policy.regenerable_cache_dirs)
    if cache_dirs:
        names = " -o ".join(f"-name {shlex_quote(d)}" for d in cache_dirs)
        ns_prunes = prunes
        prunes = prunes + f" \\( -type d \\( {names} \\) -prune \\) -o"
        alt = "|".join(re_escape(d) for d in cache_dirs)
        cache_count = (
            f"echo \"CACHE_OMITTED_DIRS\t$(find . {ns_prunes} -type d \\( {names} \\) -prune -print | wc -l | tr -d ' ')\"\n"
            f"echo \"CACHE_OMITTED_FILES\t$(find . {ns_prunes} -type f -print | grep -c -E '/({alt})/' || true)\"\n"
        )
    else:
        cache_count = ""
    excl_finds = " ; ".join(
        f"find './{ns.rstrip('/')}' -type f -print 2>/dev/null | LC_ALL=C sort | "
        f"while IFS= read -r p; do printf 'EXCL\\t%s\\n' \"${{p#./}}\"; done"
        for ns in policy.excluded_namespaces
    )
    find_cmd = f"find . {prunes} \\( -type f -o -type l -o \\( ! -type d ! -type f ! -type l \\) \\) -print | LC_ALL=C sort"
    ph = _CENSUS_DIGEST_PLACEHOLDER
    return f"""set -e
cd {workdir}
rh2_census_per_file() {{
{find_cmd} | while IFS= read -r p; do
  rel="${{p#./}}"
  if [ -L "$p" ]; then
    tgt=$(readlink "$p" | tr -d '\\n' | sha256sum | cut -d' ' -f1)
    printf 'symlink\\t120000\\t%s\\t%s\\n' "$tgt" "$rel"
  elif [ -f "$p" ]; then
    if [ -x "$p" ]; then perm=100755; else perm=100644; fi
    sha=$(sha256sum "$p" | cut -d' ' -f1)
    sha="${{sha#\\\\}}"
    printf 'regular\\t%s\\t%s\\t%s\\n' "$perm" "$sha" "$rel"
  else
    if [ -p "$p" ]; then t=fifo; elif [ -S "$p" ]; then t=socket; elif [ -b "$p" ]; then t=block_device; elif [ -c "$p" ]; then t=char_device; else t=unknown; fi
    printf 'UNSUPPORTED\\t%s\\t%s\\n' "$t" "$rel"
  fi
done
}}
rh2_census_batched() {{
  local d="$1" n_reg=0 n_sum=0 line h
  {find_cmd} > "$d/list" || return 1
  exec 4> "$d/reg" || return 1
  while IFS= read -r p; do
    rel="${{p#./}}"
    if [ -L "$p" ]; then
      tgt=$(readlink "$p" | tr -d '\\n' | sha256sum | cut -d' ' -f1)
      printf 'symlink\\t120000\\t%s\\t%s\\n' "$tgt" "$rel"
    elif [ -f "$p" ]; then
      if [ -x "$p" ]; then perm=100755; else perm=100644; fi
      printf 'regular\\t%s\\t{ph}\\t%s\\n' "$perm" "$rel"
      printf '%s\\0' "$p" >&4
      n_reg=$((n_reg + 1))
    else
      if [ -p "$p" ]; then t=fifo; elif [ -S "$p" ]; then t=socket; elif [ -b "$p" ]; then t=block_device; elif [ -c "$p" ]; then t=char_device; else t=unknown; fi
      printf 'UNSUPPORTED\\t%s\\t%s\\n' "$t" "$rel"
    fi
  done < "$d/list" > "$d/plan" || {{ exec 4>&-; return 1; }}
  exec 4>&-
  xargs -0 -r sha256sum < "$d/reg" > "$d/sums" 2>/dev/null || return 1
  while IFS= read -r line; do
    h="${{line%% *}}"
    h="${{h#\\\\}}"
    case "$h" in *[!0-9a-f]*) return 1 ;; esac
    [ "${{#h}}" -eq 64 ] || return 1
    printf '%s\\n' "$h"
    n_sum=$((n_sum + 1))
  done < "$d/sums" > "$d/hashes" || return 1
  [ "$n_sum" -eq "$n_reg" ] || return 1
  exec 3< "$d/hashes" || return 1
  while IFS= read -r line; do
    case "$line" in
      regular$'\\t'100755$'\\t'{ph}$'\\t'*|regular$'\\t'100644$'\\t'{ph}$'\\t'*)
        IFS= read -r h <&3 || {{ exec 3<&-; return 1; }}
        printf '%s%s%s\\n' "${{line:0:15}}" "$h" "${{line:79}}" ;;
      *) printf '%s\\n' "$line" ;;
    esac
  done < "$d/plan" > "$d/out" || {{ exec 3<&-; return 1; }}
  exec 3<&-
}}
rh2_census_tmp=$(mktemp -d 2>/dev/null || true)
if [ -n "$rh2_census_tmp" ] && [ -d "$rh2_census_tmp" ] && [ -z "${{RH2_CENSUS_FORCE_FALLBACK:-}}" ] && rh2_census_batched "$rh2_census_tmp"; then
  cat "$rh2_census_tmp/out"
else
  rh2_census_per_file
fi
if [ -n "$rh2_census_tmp" ]; then rm -rf "$rh2_census_tmp"; fi
{excl_finds}
{cache_count}"""


def parse_census_omitted_counts(text: str) -> dict[str, int]:
    """第四组 P-C：census 输出里的可再生缓存省略计数（只进 sidecar/账本，不进 manifest 身份）。"""
    counts: dict[str, int] = {}
    for line in text.splitlines():
        parts = line.split("\t")
        if parts and parts[0].startswith("CACHE_OMITTED") and len(parts) >= 2 and parts[1].strip().isdigit():
            counts["dirs" if parts[0].endswith("DIRS") else "files"] = int(parts[1].strip())
    return counts


def baseline_policy_for_task_id(task_id: str) -> BaselineManifestPolicy:
    """第四组 P-C：所选 Python SWE 来源（swe_gym_lite）用政策 v2（省略可再生缓存目录）；R2E 接线 R-c：
    r2e_gym_subset 用 r2e_v1（v2 + 排除 `.venv/`——环境本体在工作目录里）；其它来源沿用 v1。"""
    from repoharness2.contracts.baseline_manifest import (
        BASELINE_MANIFEST_POLICY_R2E_V1,
        BASELINE_MANIFEST_POLICY_V2,
    )

    source = task_id.split("::", 1)[0] if "::" in task_id else ""
    if source == "swe_gym_lite":
        return BASELINE_MANIFEST_POLICY_V2
    if source == "r2e_gym_subset":
        return BASELINE_MANIFEST_POLICY_R2E_V1
    return BASELINE_MANIFEST_POLICY_V1


def parse_census_output(
    text: str,
    *,
    task_id: str,
    workdir: str,
    public_bundle_digest: str,
    runtime_image_digest: str,
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
            # 新格式 3 字段 UNSUPPORTED\t<type>\t<path>；兼容旧 2 字段
            # （type 未知）。路径/类型进结构化异常字段（B5 复核三轮 P1-1：
            # receipt 拒绝证据）。
            if len(parts) >= 3:
                obj_type, obj_path = parts[1], parts[2]
            else:
                obj_type, obj_path = None, (parts[1] if len(parts) > 1 else "?")
            raise BaselineCensusError(
                "unsupported_object_in_baseline",
                f"scoreable tree 含不支持对象：{obj_path}"
                f"（type={obj_type or 'unknown'}）",
                object_path=obj_path,
                object_type=obj_type,
            )
        if parts[0] == "EXCL":
            excluded_paths.append(parts[1])
            continue
        if parts[0].startswith("CACHE_OMITTED"):
            continue  # 第四组 P-C：计数行不进 manifest（用 parse_census_omitted_counts 读）
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
        public_bundle_digest=public_bundle_digest,
        runtime_image_digest=runtime_image_digest,
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
    public_bundle_digest: str,
    runtime_image_digest: str,
    materialized_head: str,
    task_base_commit: str,
    policy: BaselineManifestPolicy = BASELINE_MANIFEST_POLICY_V1,
    omitted_sink: dict[str, int] | None = None,
) -> BaselineWorkspaceManifestV1:
    result = await workspace.run_bash(build_census_script(workdir, policy))
    if getattr(result, "exit_code", 1) != 0:
        raise BaselineCensusError(
            "baseline_census_failed",
            f"census 脚本失败（exit={result.exit_code}）：{result.stderr.strip()[-300:]}",
        )
    if omitted_sink is not None:
        omitted_sink.update(parse_census_omitted_counts(result.stdout))
    return parse_census_output(
        result.stdout,
        task_id=task_id,
        workdir=workdir,
        public_bundle_digest=public_bundle_digest,
        runtime_image_digest=runtime_image_digest,
        materialized_head=materialized_head,
        task_base_commit=task_base_commit,
        policy=policy,
    )
