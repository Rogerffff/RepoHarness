"""SWEGradingManager 最小版（S1-4）：clean-checkout 重放评分 + A7 最小 patch hygiene。

一次 grade() 的完整流程（对照 A7 七条最小要求）：

    1. 从 agent workspace 导出 final patch（`git add -N . && git diff HEAD --binary`，
       连未跟踪新文件一起导出）                                    —— A7 条 1
    2. hygiene 检查：按 diff 段切分，剔除测试文件篡改段（A7 条 3）与
       题面/运行时私有/grader-only 文件污染段（A7 条 4），得 cleaned patch；
       检出即写 PatchHygieneResult（verdict 非 clean）并在结论上封顶
       （hygiene 被拒的 patch 永远拿不到 resolved，contracts 校验器双保险）
    3. fresh grading 容器（--network none，P9）上做 clean checkout，
       用 envpack.materialize 的血缘判据核验 /testbed              —— A7 条 2
    4. 在 clean checkout 上重放 cleaned patch（git apply）
    5. 跑官方 eval 脚本（stdout+stderr 合并单流，S1-2 提醒的日志形态）
    6. envpack.scoring 官方 parser 解析                            —— A7 条 5
    7. 三分归因（A7 条 6）+ infra 族强制 reward=None（A7 条 7）
       组装 GradingReport（五类计时 + 队列/容器资源画像，F5）

失败归因决策树（S1-4 定案，依据 = manager 自己掌握的证据层级）：

    workspace 导不出 patch / 容器起不来 / checkout 血缘失败 / 容器被杀 /
    分段超时（P3）
        -> infra_failure（reward=None）
    我们的 git apply 在 clean checkout 上失败（容器活着）
        -> patch_apply_failed（模型负样本，reward=0.0，无测试计数）
    eval 跑了但：官方 parser 抛异常 / 日志带官方坏码（我们的 apply 已成功，
    坏码只能来自 eval 段自身）/ 标记齐全但解析出 0 条测试
    （空 status_map + 官方 silent-success 语义会静默给出可信度为零的结论）
        -> test_log_parse_failed（infra 族，reward=None）
    正常解析
        -> envpack.scoring.grading_outcome_fields 的三态
           （resolved=1.0 / tests_failed=0.0 / patch_apply_failed=0.0），
           hygiene 非 clean 时 resolved 降为 unresolved+tests_failed（封顶）

容器通道定案（S1-4 决策，理由记录 implementation-notes）：**直接 docker CLI**
（asyncio subprocess），不经 verifiers DockerRuntime。因为：
(a) verifiers DockerRuntime 硬编码 `--network host` 且不支持 label——评分容器
    需要 `--network none`（P9）+ label 记账（P1 孤儿清扫），子类化后 start()
    几乎整段重写，没有复用价值；
(b) grading 与 envpack 同属框架无关库层：S1-6 slime 绑定同样要用本 manager，
    保持零 verifiers import（tests/grading 有子进程探针钉死）；
(c) P1 清扫、P4 杀容器注入本来就要直接操作 docker CLI。
docker 调用函数是构造参数（P7 backend-neutral）：单测注入 FakeDocker，
未来换独立评分池/serverless 后端只需替换这一个可调用对象。
"""

from __future__ import annotations

import asyncio
import math
from contextvars import ContextVar
import base64
import hashlib
import os
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol

from repoharness2.contracts import (
    ArtifactRef,
    CleanupPolicy,
    GradingReport,
    GradingTimingRecord,
    PatchHygieneResult,
    SandboxLease,
)
from repoharness2.envpack import bundles, materialize, scoring

if TYPE_CHECKING:  # W3b：profile 模块按需 import（模块级会经 adapters.slime 包 __init__ 绕回本模块，循环）
    from repoharness2.adapters.slime.sandbox_profile import GraderSandboxProfile
from repoharness2.grading.trusted_projection import expected_candidate_paths

# ---------------------------------------------------------------------------
# docker CLI 薄层（可注入，P7）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecResult:
    """一次子进程/容器命令的结果（与 verifiers ProgramResult 同形态，但零依赖）。"""

    exit_code: int
    stdout: str
    stderr: str


# docker 调用签名：await docker("run", "-d", ...)，可选 stdin 字节流。
DockerRunner = Callable[..., Awaitable[ExecResult]]


async def run_docker(*args: str, input_bytes: bytes | None = None) -> ExecResult:
    """默认 docker CLI 通道：`docker <args>`，stdout/stderr 全量捕获。"""

    proc = await asyncio.create_subprocess_exec(
        "docker",
        *args,
        stdin=asyncio.subprocess.PIPE if input_bytes is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await proc.communicate(input=input_bytes)
    except asyncio.CancelledError:
        # 批 B（I03；Codex 批 B 审查 R2a）：本函数是物化（inspect / 建网 / docker run / exec）与
        # 评分的默认 Docker 通道——episode 期限或关停取消到达时先回收宿主 CLI 子进程再传播；
        # 容器内进程不因此停止，由所有者按名字回收（rm -f）。此前只等 communicate，取消即孤儿。
        try:
            proc.kill()
        except ProcessLookupError:  # 已退出
            pass
        await proc.wait()
        raise
    return ExecResult(
        exit_code=proc.returncode or 0,
        stdout=stdout.decode(errors="replace"),
        stderr=stderr.decode(errors="replace"),
    )


# ---------------------------------------------------------------------------
# agent workspace 抽象（patch 导出的执行通道）
# ---------------------------------------------------------------------------


class WorkspaceRunner(Protocol):
    """能在 agent workspace 的仓库根目录跑一段 bash 的最小协议。

    S1-4 自带 HostWorkspace（本机目录形态，fixture/单测用）；
    真实 rollout 容器形态（docker exec 进 rollout 容器的 /testbed）由
    S1-6 slime 绑定按同签名提供——manager 不关心 workspace 在哪里，
    只要求"能跑 git 并拿到输出"。
    """

    async def run_bash(self, script: str) -> ExecResult: ...


@dataclass(frozen=True)
class HostWorkspace:
    """本机目录形态的 agent workspace（cwd = 仓库根）。"""

    root: Path

    async def run_bash(self, script: str) -> ExecResult:
        proc = await asyncio.create_subprocess_exec(
            "bash",
            "-c",
            script,
            cwd=self.root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return ExecResult(
            exit_code=proc.returncode or 0,
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
        )


class WorkspaceExportError(RuntimeError):
    """agent workspace 导不出 patch（workspace 死亡/不是 git 仓库…）→ infra_failure。"""


# ---------------------------------------------------------------------------
# patch 段切分与 hygiene 分类（A7 条 3/4）
# ---------------------------------------------------------------------------

# `git diff` 每个文件段的头行。带引号形态（路径含特殊字符时 git 会加引号）也接住。
_DIFF_HEADER_RE = re.compile(r'^diff --git "?a/(?P<a>[^"\t\n]+)"? "?b/(?P<b>[^"\t\n]+)"?$')

# 头行解析失败的段在 forbidden_paths 里的占位标签（fail-closed：看不懂的段一律当污染剔除）。
UNPARSEABLE_SEGMENT_LABEL = "<unparseable_diff_segment>"


@dataclass(frozen=True)
class PatchSegment:
    """一个文件级 diff 段（从 `diff --git` 头行到下一个头行之前）。"""

    paths: tuple[str, ...]  # 头行里的 a/ b/ 两侧路径（去重；解析失败为空）
    text: str  # 段原文（含头行）
    header_parsed: bool


def split_patch_segments(patch_text: str) -> list[PatchSegment]:
    """把整份 patch 按 `diff --git` 头行切成文件段。

    头行之前若存在非空前导内容（正常 `git diff` 输出不该有），作为一个
    header_parsed=False 的段返回——hygiene 分类会把它当污染剔除（fail-closed）。
    """

    if not patch_text.strip():
        return []
    segments: list[PatchSegment] = []
    preamble: list[str] = []
    current: list[str] | None = None

    def _flush(lines: list[str], *, is_preamble: bool) -> None:
        text = "".join(lines)
        if is_preamble:
            if text.strip():
                segments.append(PatchSegment(paths=(), text=text, header_parsed=False))
            return
        match = _DIFF_HEADER_RE.match(lines[0].rstrip("\n"))
        if match is None:
            segments.append(PatchSegment(paths=(), text=text, header_parsed=False))
            return
        paths = tuple(dict.fromkeys((match.group("a"), match.group("b"))))
        segments.append(PatchSegment(paths=paths, text=text, header_parsed=True))

    for line in patch_text.splitlines(keepends=True):
        if line.startswith("diff --git "):
            if current is not None:
                _flush(current, is_preamble=False)
            elif preamble:
                _flush(preamble, is_preamble=True)
            current = [line]
        elif current is None:
            preamble.append(line)
        else:
            current.append(line)
    if current is not None:
        _flush(current, is_preamble=False)
    elif preamble:
        _flush(preamble, is_preamble=True)
    return segments


def patch_touched_paths(patch_text: str) -> set[str]:
    """patch 触碰的全部路径（供 build_swe_grading_spec 从 test_patch 提取官方测试文件）。"""

    paths: set[str] = set()
    for seg in split_patch_segments(patch_text):
        paths.update(seg.paths)
    return paths


@dataclass(frozen=True)
class HygieneRules:
    """hygiene 判定规则（按任务/数据集配置；匹配语义 = fnmatch，`*` 会跨越 `/`）。

    - test_files：官方测试文件的**精确**相对路径（SWE 任务从 private.test_patch 提取）。
    - test_globs：测试文件通配（宁误报不漏报——命中即当篡改，误报由人工豁免）。
    - forbidden_globs：题面/运行时私有/grader-only 文件通配（A7 条 4）。
    """

    test_files: tuple[str, ...] = ()
    test_globs: tuple[str, ...] = ()
    forbidden_globs: tuple[str, ...] = ()

    def is_test_path(self, path: str) -> bool:
        return path in self.test_files or any(fnmatch(path, g) for g in self.test_globs)

    def is_forbidden_path(self, path: str) -> bool:
        return any(fnmatch(path, g) for g in self.forbidden_globs)


@dataclass(frozen=True)
class CleanedPatch:
    """导出 + 清洗后的 final patch（A7 条 1/3/4 的产物）。"""

    raw_patch: str  # workspace 原始 diff（审计留存；不用于评分）
    cleaned_patch: str  # 剔除篡改/污染段后的重放载荷
    cleaned_patch_digest: str  # sha256:<hex>，重放与审计锚点
    test_files_modified: bool
    stripped_test_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]

    @property
    def verdict(self) -> str:
        """三分结论（优先级与 contracts.PatchHygieneResult 校验器一致：篡改 > 污染）。"""

        if self.test_files_modified:
            return "rejected_test_tampering"
        if self.forbidden_paths:
            return "rejected_forbidden_contamination"
        return "clean"

    def hygiene_result(self, *, replayed_on_clean_checkout: bool) -> PatchHygieneResult:
        """构造契约对象。replayed 标志如实反映是否真的走到了 clean checkout 重放。"""

        return PatchHygieneResult(
            cleaned_patch_digest=self.cleaned_patch_digest,
            replayed_on_clean_checkout=replayed_on_clean_checkout,
            test_files_modified=self.test_files_modified,
            forbidden_path_touched=bool(self.forbidden_paths),
            forbidden_paths=list(self.forbidden_paths),
            verdict=self.verdict,
        )


def clean_patch(raw_patch: str, rules: HygieneRules) -> CleanedPatch:
    """按 hygiene 规则清洗 patch：逐段分类，命中即整段剔除并记录事实。"""

    kept: list[str] = []
    stripped_test: list[str] = []
    forbidden: list[str] = []
    for seg in split_patch_segments(raw_patch):
        if not seg.header_parsed:
            # fail-closed：解析不了头行的段当作污染剔除，绝不盲目重放。
            forbidden.append(UNPARSEABLE_SEGMENT_LABEL)
            continue
        test_hit = any(rules.is_test_path(p) for p in seg.paths)
        forbidden_hit = any(rules.is_forbidden_path(p) for p in seg.paths)
        if test_hit:
            stripped_test.extend(p for p in seg.paths if rules.is_test_path(p))
        if forbidden_hit:
            forbidden.extend(p for p in seg.paths if rules.is_forbidden_path(p))
        if test_hit or forbidden_hit:
            continue
        kept.append(seg.text)
    cleaned = "".join(kept)
    return CleanedPatch(
        raw_patch=raw_patch,
        cleaned_patch=cleaned,
        cleaned_patch_digest=bundles.sha256_of_text(cleaned),
        test_files_modified=bool(stripped_test),
        stripped_test_paths=tuple(dict.fromkeys(stripped_test)),
        forbidden_paths=tuple(sorted(dict.fromkeys(forbidden))),
    )


# 导出脚本：`git add -N .` 把未跟踪新文件登记为 intent-to-add，让它们出现在
# `git diff HEAD` 里（agent 新建的源文件/污染文件都不能漏）；`--binary` 保证
# 二进制改动可重放；`core.fileMode=false` 与 S0-7 finalize 存证口径一致。
#
# fail-closed（S1-7a 前置修复，codex#3）：add -N 失败必须让整段导出失败——
# 旧写法 `|| true` 会吞错，此时 `git diff HEAD` 照样成功但**静默漏掉全部
# 未跟踪新文件**（典型注入：.git/index.lock 残留时 add -N 拿不到索引锁），
# 评分就会在"少了新文件的半份 patch"上得出假阴性结论。`1>&2` 把 add 的
# stdout 并进 stderr，保证 stdout 仍是纯净的 diff 载荷。
#
# 基线未跟踪文件排除（S1-7a 远程回归实测发现）：部分官方镜像的 /testbed 在
# **base 状态就自带未跟踪文件**（实测 psf__requests-1142 自带 872KB 的
# `build/lib/**` 构建残留），`git add -N .` 会把这些非 agent 产物也卷进
# patch，重放到 clean checkout 时因"already exists in working directory"
# 整体 apply 失败（S0-7 直评 resolved 的题被误判 patch_apply_failed）。
# 所以 workspace 所有者在物化完成时把基线未跟踪清单写到
# BASE_UNTRACKED_MANIFEST（`git ls-files --others --exclude-standard`，
# 与 add -N 的取数集合一致）；导出时对清单里的路径逐条
# `:(exclude,literal)`。清单不存在时行为与旧版完全一致（fixture/host
# workspace 兼容）。已知边界：agent 若**修改**了基线未跟踪文件，该改动会被
# 排除出 patch——这些文件本就不属于被评分的源码树（clean checkout 上它们
# 保持镜像原样），官方 eval 不消费。
BASE_UNTRACKED_MANIFEST = "/rh2/base_untracked.txt"

# 物化侧生成基线清单的脚本（workspace 所有者在 /testbed 就位后执行一次）。
BASE_UNTRACKED_SNAPSHOT_SCRIPT = (
    "mkdir -p $(dirname {manifest}) && "
    "git ls-files --others --exclude-standard > {manifest}"
)


def build_export_patch_script(manifest_path: str = BASE_UNTRACKED_MANIFEST) -> str:
    """构造 patch 导出脚本（manifest_path 可参数化，单测用临时路径注入）。"""

    return (
        "git add -N . 1>&2 && excl=() && "
        f'if [ -f {manifest_path} ]; then '
        "while IFS= read -r p; do "
        '[ -n "$p" ] && excl+=(":(exclude,literal)$p"); '
        f"done < {manifest_path}; fi && "
        'git -c core.fileMode=false diff --binary HEAD -- . "${excl[@]}"'
    )


EXPORT_PATCH_SCRIPT = build_export_patch_script()


@dataclass(frozen=True)
class FrozenDeltaSource:
    """B4（A-prime 第 1/2/5 条）：FA formal 评分的唯一输入源——冻结 delta
    经 hygiene 后的 projection + raw artifact + baseline。
    设置本源时 grade() **不读取 rollout workspace**（workspace 参数可为
    None）；应用前必须（T0 拍板文本第 2 条）在 fresh checkout 上**重建
    完整 BaselineWorkspaceManifestV1 并比对 digest**，并核验
    source/spec/容器三方的 task/workdir/base/head 绑定；应用 = 直接文件
    写入（无 git、无 diff 文本）。失败语义：baseline/绑定矛盾 →
    BaselineIntegrityError（run-halt，不是成员损耗）；应用动作失败 →
    GradingInfraError（reward=None，不得记模型 reward 0——直接写入不存在
    "冲突"，S1 的 patch_apply_failed 不适用，模型坏 patch 只能在测试阶段
    表现为 unresolved）。

    W3a（D2-1/D2-3）：`projection.included_entry_paths` = 可信评分投影的
    candidate_solution 路径集（控制面路径已拆出、不重放）；三个对象都来自
    持久化产物或可由持久化产物重建——rollout 容器在本源组装前已被释放，
    grader 除本源外没有任何输入。"""

    frozen_patch: "object"  # FrozenPatchArtifactV1（避免 contracts 循环 import 用鸭子）
    baseline_manifest: "object"  # BaselineWorkspaceManifestV1
    projection: "object"  # ScoringProjectionArtifactV1
    frozen_patch_digest: str


def _shq(text: str) -> str:
    """POSIX 单引号安全包裹。"""

    return "'" + text.replace("'", "'\\''") + "'"


def _shq_rel(path: str) -> str:
    """相对路径操作数：`./` 前缀 + 单引号。`./` 让 `-` 开头的路径不会被
    rm/chmod/ln/mkdir 当成选项——比 `--` 更可移植（BSD chmod 不接受
    mode 之后的 `--`，真实文件系统测试在 macOS 上抓到过）。仅用于路径
    操作数；symlink target 必须逐字保留（改写会改变链内容），走 `ln -s --`。"""

    return _shq("./" + path)


@dataclass
class FrozenApplyPlan:
    """B4 P1：task-aware hygiene 筛查 + 应用计划（对 S1 clean_patch 的镜像）。

    W3a（D2-3）起在 FA frozen-delta 路径的角色：输入已经是可信评分投影的 candidate
    子集（控制面路径在 producer 侧拆出、grader 侧独立重算核对），因此 verdict 恒为
    clean、`applied_paths` == 投影路径集、`applied_entry_set_digest` = 实际重放子集
    digest（PatchHygieneResult.digest_kind=applied_entry_set）。stripped/forbidden 非空只
    可能来自程序错误（grade() 升 BaselineIntegrityError）。S1 diff 文本路径不经本类。"""

    applied_paths: tuple[str, ...]
    stripped_test_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]
    applied_entry_set_digest: str
    apply_completed: bool = False

    @property
    def verdict(self) -> str:
        # 优先级与 CleanedPatch.verdict / contracts 校验器一致：篡改 > 污染
        if self.stripped_test_paths:
            return "rejected_test_tampering"
        if self.forbidden_paths:
            return "rejected_forbidden_contamination"
        return "clean"


def compute_applied_entry_set_digest(entries: "list[object]") -> str:
    """实际应用的 entry 子集的 canonical digest（PatchHygieneResult
    digest_kind=applied_entry_set 的取值；hygiene 剔除后 ≠ 完整 artifact
    digest，两种 digest 语义用 digest_kind 显式区分，不得混装）。"""

    lines = sorted(
        f"{e.operation}\t{e.object_type}\t{e.mode or ''}\t{e.content_digest or ''}\t{e.path}"
        for e in entries
    )
    return "sha256:" + hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def screen_frozen_entries(
    entries: "list[object]", rules: HygieneRules
) -> FrozenApplyPlan:
    """对冻结 entries 做 task-aware hygiene 筛查（S1 clean_patch 的 FA 镜像；
    匹配器复用同一个 HygieneRules，规则语义零分叉）。纯函数，独立可测。"""

    applied: list[object] = []
    stripped_test: list[str] = []
    forbidden: list[str] = []
    for e in entries:
        test_hit = rules.is_test_path(e.path)
        forbidden_hit = rules.is_forbidden_path(e.path)
        if test_hit:
            stripped_test.append(e.path)
        if forbidden_hit:
            forbidden.append(e.path)
        if test_hit or forbidden_hit:
            continue
        applied.append(e)
    return FrozenApplyPlan(
        applied_paths=tuple(e.path for e in applied),
        stripped_test_paths=tuple(dict.fromkeys(stripped_test)),
        forbidden_paths=tuple(sorted(dict.fromkeys(forbidden))),
        applied_entry_set_digest=compute_applied_entry_set_digest(applied),
    )


def build_delta_delete_command(testbed_path: str, path: str) -> str:
    """delete：`rm -f` 对 symlink 是 no-follow（删链本体不碰 target）。"""

    return f"cd {_shq(testbed_path)} && rm -f {_shq_rel(path)}"


def build_delta_write_command(
    testbed_path: str, path: str, *, mode: str, operation: str
) -> str:
    """regular add/modify（内容经 stdin 送入，二进制安全）。

    P0-2 修复核心：**写入前必须先 unlink 旧对象**——`cat > path` 的 shell
    重定向会跟随既有 symlink，把模型内容写进 target（合法的
    symlink→regular 类型变化就会写穿评分树外的文件）。`rm -f` 先删掉
    旧对象（regular 或 symlink 本体，绝不跟随），再创建全新 regular 文件。
    add 额外断言目标原本不存在（census 重建比对已证树==baseline，此处是
    防御性双保险，命中即应用失败走 infra）。"""

    q = _shq_rel(path)
    parent = "/".join(path.split("/")[:-1])
    mk = f"mkdir -p {_shq_rel(parent)} && " if parent else ""
    perm = "755" if mode == "100755" else "644"
    guard = (
        f"if [ -e {q} ] || [ -L {q} ]; then echo add_target_exists:{q} >&2; exit 3; fi; "
        if operation == "add"
        else f"rm -f {q} && "
    )
    return (
        f"cd {_shq(testbed_path)} && {mk}{guard}cat > {q} && chmod {perm} {q}"
    )


def build_delta_symlink_command(testbed_path: str, path: str, target: str) -> str:
    """symlink add/modify：先 unlink 旧对象再 `ln -s --`（同 P0-2 纪律）。
    target 逐字保留（`--` 终止选项解析，覆盖 `-` 开头 target；路径操作数
    用 `./` 前缀）。"""

    parent = "/".join(path.split("/")[:-1])
    mk = f"mkdir -p {_shq_rel(parent)} && " if parent else ""
    return (
        f"cd {_shq(testbed_path)} && {mk}"
        f"rm -f {_shq_rel(path)} && ln -s -- {_shq(target)} {_shq_rel(path)}"
    )


async def export_cleaned_patch(
    workspace: WorkspaceRunner,
    rules: HygieneRules,
    *,
    export_script: str = EXPORT_PATCH_SCRIPT,
) -> CleanedPatch:
    """A7 条 1：从 agent workspace 导出 final patch 并按规则清洗。

    export_script 默认生产脚本；单测经 build_export_patch_script(临时 manifest)
    注入宿主可写路径（生产 manifest 固定在容器内 BASE_UNTRACKED_MANIFEST）。
    """

    result = await workspace.run_bash(export_script)
    if result.exit_code != 0:
        raise WorkspaceExportError(
            f"workspace patch 导出失败（exit={result.exit_code}）: {result.stderr.strip()[-500:]}"
        )
    return clean_patch(result.stdout, rules)


# ---------------------------------------------------------------------------
# 评分环境 spec
# ---------------------------------------------------------------------------

# SWE 任务默认测试通配（fnmatch，`*` 跨 `/`）：django tests/、sympy */tests/、
# requests 根目录 test_*.py、astropy 深层 tests/ 都被覆盖。宁误报不漏报。
DEFAULT_SWE_TEST_GLOBS: tuple[str, ...] = (
    "*tests/*",
    "*testing/*",
    "test_*.py",
    "*/test_*.py",
    "*_test.py",
    "*/*_test.py",
)

# SWE 任务默认禁区通配：rh2 运行时私有落点（cleaned patch、eval 脚本等都写在
# 容器 /rh2/ 下、仓库外，正常 diff 不会出现；出现同名仓库内路径即视为污染企图）。
DEFAULT_SWE_FORBIDDEN_GLOBS: tuple[str, ...] = (".rh2*", "rh2/*")


@dataclass(frozen=True)
class GradingEnvSpec:
    """一次评分动作的环境说明书（框架无关；SWE 任务用 build_swe_grading_spec 生成）。"""

    task_id: str
    image: str  # 评分容器镜像（SWE=官方任务镜像；本机测试=轻量 fixture 镜像）
    base_commit: str  # 40 位 git sha（血缘判据锚点）
    eval_script: str  # 官方 eval 脚本全文（SWE 来自 private bundle）
    parse_log: Callable[[str], scoring.EvalVerdict]  # 官方 parser 入口（绑定私有材料）
    grader_version: str
    hygiene: HygieneRules
    # F2（codex Wave3 复核）：grader profile 路径下 eval 拆两步——
    #   trusted_setup_script：root 执行（恢复 official test files、应用 official test_patch、git status/show/diff）；
    #   candidate_test_script：候选执行用户执行（只跑测试命令，带官方 Start/End 标记）。
    # 两者都在场才允许在 profile 下评分（缺失 = SandboxProfileViolation run-halt）；legacy（无 profile）路径仍只用 eval_script。
    trusted_setup_script: str | None = None
    candidate_test_script: str | None = None
    # 运行期镜像 digest 比对（S1-7a 前置修复，codex#1）：二选一、必选其一——
    # 要么给出 envpack 冻结的 manifest digest（评分容器启动后与实际镜像的
    # RepoDigests 比对，不符即 infra_failure），要么显式声明 image_local_build
    # 豁免（本地构建 fixture 镜像没有 RepoDigests）。两者都缺 = 构造即拒。
    image_manifest_digest: str | None = None
    image_local_build: bool = False
    checkout_mode: Literal["image_embedded", "clone_from_readonly_snapshot"] = "image_embedded"
    # clone 模式（本机 fixture）：宿主侧只读快照目录，以 :ro 挂进容器后 clone 出 /testbed（P6）。
    snapshot_host_path: str | None = None
    snapshot_mount_path: str = "/rh2/snapshot"
    testbed_path: str = "/testbed"  # materialize 探针脚本固定探 /testbed，暂不做成活动参数
    eval_script_path: str = scoring.EVAL_SCRIPT_PATH
    grader_name: str = scoring.GRADER_NAME
    env_reset_timeout_seconds: float = 300.0
    apply_timeout_seconds: float = 120.0
    test_timeout_seconds: float = 1800.0  # P3：manager 内部分段 timeout，比外层 scoring_timeout 更严

    def __post_init__(self) -> None:
        if (self.image_manifest_digest is None) == (not self.image_local_build):
            raise ValueError(
                "镜像 digest 校验必须显式二选一：要么提供 image_manifest_digest"
                "（冻结记录，运行期 RepoDigests 比对），要么声明 image_local_build=True"
                "（本地构建镜像豁免）；两者都缺或同时给出都拒绝——豁免不允许静默发生。"
            )
        if self.checkout_mode == "clone_from_readonly_snapshot" and not self.snapshot_host_path:
            raise ValueError("clone_from_readonly_snapshot 模式必须提供 snapshot_host_path")
        if self.testbed_path != "/testbed":
            raise ValueError(
                "S1-4 血缘探针（envpack.materialize.build_probe_script）固定探 /testbed，"
                f"暂不支持 testbed_path={self.testbed_path!r}"
            )


def build_swe_grading_spec(pair: bundles.BundlePair) -> GradingEnvSpec:
    """从 S1-2 的 BundlePair 构造真实 SWE 任务的评分 spec。

    - 镜像/base_commit 来自 public 半区（公开事实）；
    - eval 脚本、官方 parser 配置、测试文件清单来自 private 半区（评分私有），
      只进评分容器，永不进 rollout 容器（A6）；
    - 官方测试文件 = private.test_patch 触碰的路径（精确名单）+ 默认通配。
    """

    private = pair.private
    test_files = tuple(sorted(patch_touched_paths(private.test_patch)))

    def _parse(log_text: str) -> scoring.EvalVerdict:
        return scoring.parse_eval_log(private, log_text)

    return GradingEnvSpec(
        task_id=pair.instance_id,
        image=pair.public.image,
        base_commit=pair.public.base_commit,
        # 冻结 digest 进 spec：评分容器启动后与实际镜像 RepoDigests 比对（codex#1）。
        image_manifest_digest=pair.public.image_manifest_digest,
        eval_script=private.eval_script,
        parse_log=_parse,
        grader_version=f"swebench-{scoring.swebench_version()}",
        hygiene=HygieneRules(
            test_files=test_files,
            test_globs=DEFAULT_SWE_TEST_GLOBS,
            forbidden_globs=DEFAULT_SWE_FORBIDDEN_GLOBS,
        ),
        checkout_mode="image_embedded",  # 官方镜像自带 /testbed@base（血缘判据核验）
    )


# ---------------------------------------------------------------------------
# manager 本体
# ---------------------------------------------------------------------------


@dataclass
class GradingManagerConfig:
    """manager 级配置（评分并发不在这里——那是 queue.py 的职责）。"""

    label_prefix: str = "rh2.grading"  # 容器 label 键前缀（P1 记账与清扫的锚点）
    name_prefix: str = "rh2-grading"  # 容器名前缀
    prepare_concurrency: int = 2  # P2：prepare 预热的有界信号量
    orphan_min_age_seconds: float = 3600.0  # P1：startup 清扫只动超过此年龄的外来容器
    eval_log_dir: Path | None = None  # 非空时把 eval 原始日志落盘并出 ArtifactRef
    cleanup_timeout_seconds: int = 120
    # W3b（D2-2）：独立 grader Docker profile。None = 旧参数（--network none、root、无限额）——
    # 只给 s1_compat 冻结路径与既有单测；bringup 对非 s1 模式一律注入。
    sandbox_profile: "GraderSandboxProfile | None" = None


class GradingInfraError(RuntimeError):
    """评分链路自身故障（infra 族）。category 决定 GradingReport 的归因取值。"""

    def __init__(
        self,
        detail: str,
        *,
        category: Literal["infra_failure", "test_log_parse_failed"] = "infra_failure",
        op: str | None = None,
        exit_code: int | None = None,
        stderr: str | None = None,
        container_name: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.category = category
        # N2b：产生故障的操作阶段与原始 CLI 返回（重试判定只看这些，不解析 detail 文案）；
        # container_name = docker run 失败时本次已生成的名字（创建回包丢失 → 先按名收口）
        self.op = op
        self.exit_code = exit_code
        self.stderr = stderr
        self.container_name = container_name


# N2a（第 2 组剩余实施 Brief §3.2；Codex 计划审查 R1）：一条评分任务的**工作期限**——由编排在提交时建立，
# 随 queue item 传到 worker，再由 grade() 设进本 task 的 contextvar；准备 / 等待 / 重试共用它。
# 每个阻塞的 Docker 操作与分段 timeout 都取 min(既有 timeout, 剩余)，剩余 ≤ 0 → GradingInfraError
# ("grading_deadline_exhausted:<phase>") → 既有 failed_to_grade / infra 族归类（不决定第四组 reward 规则）。
# 清理 / 收口（_close_container_scope）沿自己的 cleanup_timeout_seconds，不受它约束。
_GRADING_DEADLINE: ContextVar[float | None] = ContextVar("rh2_grading_deadline_monotonic", default=None)
GRADING_DEADLINE_EXHAUSTED = "grading_deadline_exhausted"


def grading_deadline_left() -> float | None:
    """当前评分任务的剩余秒数；没有期限 = None。"""

    deadline = _GRADING_DEADLINE.get()
    if deadline is None:
        return None
    return deadline - time.monotonic()


def require_grading_time(phase: str) -> float | None:
    """剩余 ≤ 0 即抛 GradingInfraError（期限耗尽，phase 说明在哪个环节）；返回剩余秒数（无期限 = None）。"""

    left = grading_deadline_left()
    if left is not None and left <= 0:
        raise GradingInfraError(f"{GRADING_DEADLINE_EXHAUSTED}:{phase}")
    return left


def bounded_by_grading_deadline(timeout: float, phase: str) -> float:
    """分段 timeout 与评分期限取小（先核期限未耗尽）。"""

    left = require_grading_time(phase)
    return timeout if left is None else min(timeout, left)


# N2b（I16，第 2 组 §5 / 补充说明 §8；Codex 计划审查 §6）：只对**已核对的 Docker CLI 错误形态**判"可重试的
# 传输 / 服务故障"。按操作阶段 + 原始 CLI 返回判定；不按单独的 `EOF` / `timeout` 子串兜底；确定的配置 /
# 认证 / 引用错误先排除，不被通用传输字样覆盖；没有可靠来源的形态不开放（返回 None = 不重试）。
# 形态来源：moby client / CLI 的连接错误文案（"Cannot connect to the Docker daemon"、"error during connect"）、
# Go net 层错误（"connection reset by peer" / "connection refused" / "broken pipe" / "i/o timeout" /
# "TLS handshake timeout" / "net/http: request canceled"）、distribution/registry 暂态状态
# （"received unexpected HTTP status: 5xx"、"503 Service Unavailable"、"toomanyrequests"）。
_NON_RETRYABLE_SHAPES: tuple[str, ...] = (
    "not found", "manifest unknown", "pull access denied", "unauthorized", "denied: requested access",
    "invalid reference format", "no such image", "repository does not exist", "name unknown",
)
_DAEMON_CONNECT_SHAPES: tuple[str, ...] = (
    "cannot connect to the docker daemon", "error during connect", "connection reset by peer",
    "connection refused", "broken pipe",
)
_REGISTRY_TRANSPORT_SHAPES: tuple[str, ...] = (
    "tls handshake timeout", "i/o timeout", "net/http: request canceled", "received unexpected http status: 5",
    "503 service unavailable", "toomanyrequests",
)
REGRADE_ALLOWED_OPS: tuple[str, ...] = ("image_pull", "container_start")
MAX_GRADING_ATTEMPTS = 2  # 补充说明 §8：整次评分任务总共最多两次尝试（不是 pull、start 各加一次）
GRADING_REGRADE_EVENT = "grading_regrade"


def classify_docker_transport_error(op: str, exit_code: int, stderr: str | None) -> str | None:
    """返回可重试类别（"daemon_connect" / "registry_transport"）或 None（不重试：未知 / 确定性错误 / 阶段不允许）。"""

    if op not in REGRADE_ALLOWED_OPS or exit_code == 0:
        return None
    text = (stderr or "").lower()
    if not text or any(shape in text for shape in _NON_RETRYABLE_SHAPES):
        return None
    if any(shape in text for shape in _DAEMON_CONNECT_SHAPES):
        return "daemon_connect"
    if op == "image_pull" and any(shape in text for shape in _REGISTRY_TRANSPORT_SHAPES):
        return "registry_transport"
    return None


def _emit_grading_event(kind: str, **fields: Any) -> None:
    """可选观测：经 miles 集成分支的事件日志发一条；miles 不在路径 / 未启用 → 不发。不影响评分结果。"""

    try:
        from miles.utils import rh2_event_log
    except Exception:  # noqa: BLE001
        return
    try:
        if rh2_event_log.enabled():
            rh2_event_log.emit(kind, **fields)
    except Exception:  # noqa: BLE001
        return



class BaselineIntegrityError(RuntimeError):
    """B4 P0-1：exact-baseline 重建/绑定校验失败 = **系统性契约错误**。

    与 GradingInfraError 的分界（A-prime 失败表）：infra = 该次评分动作
    自身的故障（容器/网络/超时），可以按成员损耗记 failed_to_grade；而
    baseline/lineage 矛盾意味着"grader 看到的树 ≠ 模型看到的树"或
    "同进程两份事实分家"——继续训练会系统性污染样本。因此本异常**故意
    不被 grade() 捕获**，穿队列上抛，由 generate 转
    FatalExecutionInfrastructureError（run-halt），与 B3
    ProjectionContractError 同通道。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


class GradingScopeTerminationError(BaselineIntegrityError):
    """批 D-2（I14 grading 侧；06 A4"execution scope 无法终止 = run-fatal，仍继续清理"）：评分容器在
    有界收口（rm -f → kill → rm -f）之后**仍在运行或状态无法确认**。

    与普通 failed_to_grade 的分界：评分动作失败可按成员损耗继续；但一个仍在跑测试 / 状态未知的容器
    会继续占用资源、且后续评分容器会与它并存，继续接新任务只会累积。复用 BaselineIntegrityError 的
    传播通道（故意不被 grade() 捕获，穿队列上抛，由 generate 转 FatalExecutionInfrastructureError）。
    第一次 rm 失败但随后确认已停止 / 已删除 → 只留 cleanup_failures 诊断，不 fatal。"""


class SandboxProfileViolation(BaselineIntegrityError):
    """W3b：grader 容器创建后核对发现 profile 未生效（或 root 可信初始化失败）。

    这是**系统性配置错误**而不是单次评分动作的故障：同 profile 的下一次评分同样不合格，
    记 failed_to_grade 只会把"配置不合"洗成成员损耗并继续训练。因此与 BaselineIntegrityError
    同通道——grade() 不捕获、穿队列上抛，generate.py 转 FatalExecutionInfrastructureError
    （run-halt，cleanup 仍执行）。容器在抛出前已移除。"""


@dataclass
class _ContainerRecord:
    """per-容器记账条目（P1：TTL GC 与孤儿判定的数据底座）。"""

    name: str
    trajectory_id: str
    created_epoch: float
    created_monotonic: float
    removed: bool = False
    # W3b：本容器的启动前核对摘要（profile 在场时必有；None = legacy 参数）
    prelaunch: dict[str, Any] | None = None
    # F2：候选测试前的控制面权限布置自证（PROTECTED_FILES/DIRS、MISSING_FILES、TESTBED_STAT）
    control_surface: dict[str, str] | None = None
    # F2 + codex Wave3 §9.2：root 可信 setup 的自证（apply 返回码、official test 文件在位数等）；
    # 判定失败时也先记账再抛，审计里看得到"卡在哪一条判据"。
    trusted_setup: dict[str, str] | None = None
    # 可信 setup / 权限布置阶段的原始输出：候选测试从未启动时 grade() 拿不到 eval 日志，
    # 用它给 infra 报告留 eval_log_ref（否则真实故障现场丢失）。
    eval_log_partial: str | None = None


# W3a 生命周期计时：grader 内部六段（与 adapters/slime/attempt_timing.LIFECYCLE_SEGMENTS 同名）。
GRADER_PHASE_SEGMENTS: tuple[str, ...] = (
    "grader_start_and_verify",
    "grader_baseline_rebuild",
    "delta_apply",
    "grader_trusted_setup",  # F2/P2-4：root 可信 setup（恢复 official tests + 应用 test_patch + 权限布置），与 test 分开
    "test",
    "parser_and_report",
    "grader_cleanup",
)

# manager 内暂存的分段记录上限：orchestrator 经 take_grader_phase_timing() 取走即删除；
# 没有消费者（例如 bringup 尚未接线）时按 FIFO 淘汰最旧记录，防止长 run 无界增长。
_GRADER_PHASE_TIMING_RETENTION = 1024


@dataclass
class GraderPhaseTiming:
    """一次 grade() 的内部分段计时（进程内值对象，不是 contracts 记录——GradingTimingRecord 的
    五类计时是冻结契约，本对象补齐 W3a 要求的更细分段；两者由 record_id 关联）。"""

    record_id: str
    trajectory_id: str
    task_id: str
    segments: dict[str, float | None] = field(
        default_factory=lambda: {name: None for name in GRADER_PHASE_SEGMENTS}
    )
    frozen_delta_path: bool = False  # True = FA frozen-delta 路径；False = S1 diff 文本路径

    def add(self, segment: str, seconds: float) -> None:
        if segment not in self.segments:
            raise KeyError(f"未知 grader 分段：{segment!r}")
        self.segments[segment] = round((self.segments[segment] or 0.0) + max(seconds, 0.0), 6)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "trajectory_id": self.trajectory_id,
            "task_id": self.task_id,
            "frozen_delta_path": self.frozen_delta_path,
            "segments_seconds": dict(self.segments),
        }


def _sanitize_for_name(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "-", text).strip("-.")
    return (cleaned or "traj")[:24]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _count_field(facts: dict[str, str], key: str) -> int | None:
    """自证里的计数字段 → 非负整数；缺失/非十进制整数一律 None（判据按"取不到 = 不达标"处理）。"""

    raw = facts.get(key, "")
    return int(raw) if raw.isdigit() else None


def _check_trusted_setup_attest(
    exit_code: int, facts: dict[str, str], expected_total: int
) -> str | None:
    """root 可信 setup 的成功判据。返回 None = 通过；返回字符串 = 不通过的原因码。

    判据（全部必须成立，任一不成立就不许启动候选测试）：

    1. setup 脚本本身退出码为 0；
    2. 自证文件里有 `RH2_SETUP_OK=1`——脚本只有在"official test_patch 的 `git apply` 成功
       + 没有任何 official test 路径是 symlink/目录 + 至少一个 official test 文件在位"时才写这一行；
    3. `RH2_SETUP_APPLY_RC=0`（manager 侧独立复核 apply 结果，不只信 OK 行）；
    4. `RH2_SETUP_EXPECTED_TEST_FILES` 与 manager 按 `spec.hygiene.test_files` 去重后算出的数量相等
       ——脚本里内嵌的 official test 清单必须就是本次评分 spec 的那一份，两侧分家即拒；
    5. **缺失数为 0**，且在位普通文件数恰好等于期望总数（脚本的分类循环覆盖了整份清单，一个不缺）。

    为什么"不存在"也算失败（codex Wave3 §10.2 对上一轮判据的纠正）：`hygiene.test_files` 取自
    `patch_touched_paths(test_patch)`，也就是 `diff --git a/X b/Y` 两侧路径，因此被 official test_patch
    **删除**或**改名**掉的测试文件也在清单里，apply 之后确实可能有路径不在位。上一轮曾按"setup 与
    权限布置数出的缺失数相等就放行"，但那保不住不变量的另一半——**"official patch 规定为不存在的
    路径必须保持不存在"**：权限布置把祖先目录设成 root:root 1777，sticky 位只阻止候选删除/改名
    别人已存在的条目，不阻止它在缺失的名字上**新建**文件；候选测试命令又把含旧路径的整份清单传给
    runner。codex 在真实 SWE 镜像里实测候选 uid 能重建缺失路径，并让 vendor pytest 真的收集执行它。
    因此本 profile 直接要求缺失数为 0：official patch **新增**测试文件不受影响（apply 成功后已在位），
    只是暂不支持"最终结果仍缺路径"的删除/改名形状（冻结的 216 题实测删除 0、改名 0，无可评分性损失）。"""

    if exit_code != 0:
        return "setup_exit_code"
    if facts.get("RH2_SETUP_OK") != "1":
        return "setup_not_attested"
    if facts.get("RH2_SETUP_APPLY_RC") != "0":
        return "official_test_patch_apply_failed"
    if facts.get("RH2_SETUP_EXPECTED_TEST_FILES") != str(expected_total):
        return "official_test_file_list_mismatch"
    present = _count_field(facts, "RH2_SETUP_TEST_FILES")
    absent = _count_field(facts, "RH2_SETUP_ABSENT_TEST_FILES")
    if present is None or absent is None or present + absent != expected_total:
        return "official_test_files_not_accounted"
    if facts.get("RH2_SETUP_IRREGULAR_TEST_FILES", "?") != "":
        return "official_test_file_not_regular"
    if absent != 0 or present != expected_total:
        # 缺失即拒（§10.2）：sticky 目录挡不住候选在"应当不存在"的 official 路径上新建文件。
        return "official_test_file_missing_after_setup"
    return None


def _check_control_surface_attest(
    exit_code: int, facts: dict[str, str], setup_facts: dict[str, str], expected_total: int
) -> str | None:
    """候选测试前控制面权限布置的成功判据。返回 None = 通过；否则是不通过的原因码。

    判据：

    1. 权限脚本退出码为 0 且写出 `RH2_PROTECT_OK=1`（脚本自身已复核每个受保护文件 `0 644`、
       每级祖先目录 `0 1777`）；
    2. `EXPECTED_FILES` 等于 manager 按 spec 算出的去重后 official test 文件数（脚本清单 = spec 清单）；
    3. `IRREGULAR_FILES` 为空——official test 路径上出现 symlink/目录一律拒（symlink 目标可被改写，
       "保护住了 symlink 本身"不等于保护住被执行的测试）；
    4. `MISSING_FILES_COUNT` 为 0（§10.2：缺失即拒），且 `PROTECTED_FILES` 精确等于去重后的
       official test 文件数，同时与可信 setup 在 official patch 成功应用之后数出的在位普通文件数一致。
       也就是说：清单里的每一个 official test 文件都已经是 root 属主只读普通文件，一个都不能少、
       也不能多出来源不明的一个。"""

    if exit_code != 0:
        return "protect_exit_code"
    if facts.get("RH2_PROTECT_OK") != "1":
        return "protect_not_attested"
    if facts.get("EXPECTED_FILES") != str(expected_total):
        return "official_test_file_list_mismatch"
    if facts.get("IRREGULAR_FILES", "?") != "":
        return "official_test_file_not_regular"
    protected = _count_field(facts, "PROTECTED_FILES")
    missing = _count_field(facts, "MISSING_FILES_COUNT")
    present_after_setup = _count_field(setup_facts, "RH2_SETUP_TEST_FILES")
    absent_after_setup = _count_field(setup_facts, "RH2_SETUP_ABSENT_TEST_FILES")
    if protected is None or missing is None or present_after_setup is None or absent_after_setup is None:
        return "protect_counts_unreadable"
    if missing != 0 or absent_after_setup != 0:
        return "official_test_file_missing"
    if protected != present_after_setup or protected != expected_total:
        return "protected_count_mismatch"
    return None


class SWEGradingManager:
    """进程级评分管理器：prepare（可选预热）/ grade（评分本体）/ gc（记账回收）。

    P7 形态：每 worker 进程一个实例（接口 backend-neutral——docker 调用可注入，
    跨进程统一池化/独立评分服务留 S5）。
    """

    def __init__(
        self,
        config: GradingManagerConfig | None = None,
        docker: DockerRunner | None = None,
    ) -> None:
        self.config = config or GradingManagerConfig()
        self._docker = docker or run_docker
        self.run_id = uuid.uuid4().hex[:12]  # 本实例的 owner 标识（label + 孤儿判定）
        self._records: list[_ContainerRecord] = []
        self._images_ready: set[str] = set()
        self._image_locks: dict[str, asyncio.Lock] = {}
        self._prepare_sem = asyncio.Semaphore(self.config.prepare_concurrency)
        self._prepare_tasks: set[asyncio.Task] = set()
        self.prepare_failures: list[str] = []  # prepare 失败只记录不外抛（P5：grade 不受连累）
        self.cleanup_failures: list[str] = []  # Q8：清理失败必须留痕（S1-6 收口为 finding）
        self.regrade_events: list[dict[str, Any]] = []  # N2b：追加评分事实（上限 256 条；消费者 = close() 报告 + 事件日志）
        self.leases: list[SandboxLease] = []  # 评分容器租约 evidence（P9 deny_all 由 schema 锁死）
        self._closed = False  # W5a：close() 后 grade 走 typed 拒绝
        # W3a：grade() 内部分段计时暂存（record_id → GraderPhaseTiming），orchestrator 经
        # take_grader_phase_timing() 取走合并进 attempt 生命周期记录。
        self._phase_timings: dict[str, GraderPhaseTiming] = {}
        # W3b：grader 容器启动前核对摘要（有界；run 记录/关停报告取数）
        self.prelaunch_checks: list[dict[str, Any]] = []

    # ------------------------------------------------------------------ W3a 分段计时
    def take_grader_phase_timing(self, record_id: str) -> GraderPhaseTiming | None:
        """取走（并删除）某次评分的内部分段计时；record_id = GradingReport.timings.record_id。
        不存在（未评分 / 已取走 / 超出保留上限被淘汰）返回 None。"""

        return self._phase_timings.pop(record_id, None)

    def _retain_phase_timing(self, timing: GraderPhaseTiming) -> None:
        self._phase_timings[timing.record_id] = timing
        while len(self._phase_timings) > _GRADER_PHASE_TIMING_RETENTION:
            oldest = next(iter(self._phase_timings))
            del self._phase_timings[oldest]

    # ------------------------------------------------------------------ W5a 关停
    async def close(self) -> dict[str, Any]:
        """关停（幂等）：取消预热任务 → 回收全部记账容器（gc 全量）→ 置 closed。

        只处理**本实例记过账**的容器（`_records`）；不按 label 扫别人的容器
        （那是 launch trap 的 run-label 兜底，见 shutdown/run_residue.py）。清理
        失败照旧进 `cleanup_failures`（Q8 留痕），本方法不抛——关停链按返回的
        `containers_open` 判残留。
        """

        pending = [t for t in self._prepare_tasks if not t.done()]
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        removed = await self.gc()
        self._closed = True
        return {
            "prepare_cancelled": len(pending),
            "containers_removed": removed,
            "containers_open": [r.name for r in self._records if not r.removed],
            "cleanup_failures": list(self.cleanup_failures),
            "regrade_events": len(self.regrade_events),  # N2b：本 run 追加评分次数
        }

    @property
    def closed(self) -> bool:
        return self._closed

    # ------------------------------------------------------------------ P1
    async def startup(self) -> list[str]:
        """进程启动清扫：按 label 前缀找出**不属于本实例**且超龄的评分容器并移除。

        年龄门槛（orphan_min_age_seconds）防止误杀同宿主上其他活跃 worker 的
        容器——正常评分容器寿命只有几分钟，超过一小时仍在的 label 容器就是
        上一次进程崩溃留下的孤儿。
        """

        prefix = self.config.label_prefix
        fmt = f'{{{{.ID}}}}\t{{{{.Label "{prefix}.owner"}}}}\t{{{{.Label "{prefix}.created_at_epoch"}}}}'
        listing = await self._docker(
            "ps", "-a", "--filter", f"label={prefix}.owner", "--format", fmt
        )
        removed: list[str] = []
        if listing.exit_code != 0:
            return removed
        now = time.time()
        for line in listing.stdout.splitlines():
            parts = (line.split("\t") + ["", ""])[:3]
            container_id, owner, created_raw = parts[0].strip(), parts[1].strip(), parts[2].strip()
            if not container_id or owner == self.run_id:
                continue
            try:
                age = now - float(created_raw)
            except ValueError:
                age = float("inf")  # 没有合法时间戳的 label 容器直接视为孤儿
            if age < self.config.orphan_min_age_seconds:
                continue
            rm = await self._docker("rm", "-f", container_id)
            if rm.exit_code == 0:
                removed.append(container_id)
            else:
                self.cleanup_failures.append(
                    f"orphan_sweep_rm_failed:{container_id}:{rm.stderr.strip()[-200:]}"
                )
        return removed

    # ------------------------------------------------------------------ P2
    def prepare(self, spec: GradingEnvSpec) -> asyncio.Task:
        """可选预热（S1 仅做镜像预拉取，P10 第一档）。fire-and-forget + 有界信号量（P2）。

        失败只记 prepare_failures，不外抛也不污染缓存——grade() 走自己的
        _ensure_image 冷启动路径（P5），与 prepare 的存亡完全解耦。
        """

        async def _job() -> None:
            async with self._prepare_sem:
                try:
                    await self._ensure_image(spec.image)
                except Exception as exc:  # noqa: BLE001 预热失败绝不能伤及主链路
                    self.prepare_failures.append(f"{spec.image}:{exc}")

        task = asyncio.create_task(_job())
        self._prepare_tasks.add(task)
        task.add_done_callback(self._prepare_tasks.discard)
        return task

    # ------------------------------------------------------------------ 评分本体
    async def grade(
        self,
        *,
        trajectory_id: str,
        workspace: WorkspaceRunner | None,
        spec: GradingEnvSpec,
        frozen_delta: "FrozenDeltaSource | None" = None,
        queue_wait_seconds: float = 0.0,
        queue_depth_at_enqueue: int | None = None,
        backpressure_triggered: bool = False,
        deadline_monotonic: float | None = None,
    ) -> GradingReport:
        """评分一条轨迹：导出→清洗→fresh 容器 clean checkout→重放→测试→官方解析→报告。

        queue_* 参数由 GradingQueue 注入（F5 排队等待计时与反压事实）；
        直接调用（不经队列）时保持默认值即可。`deadline_monotonic`（N2a）= 本次评分工作的期限
        （编排提交时建立，含排队）；None = 不设期限（旧调用面）。
        """

        if self._closed:
            # W5a：关停后不再起任何评分容器。typed 拒绝（不是 failed_to_grade 报告：
            # 那会被当成一次真实的评分基建失败计数）。
            from repoharness2.shutdown.chain import ServiceClosedError

            raise ServiceClosedError("grading_manager_grade", f"评分管理器已关停，拒绝 {trajectory_id}")
        token = _GRADING_DEADLINE.set(deadline_monotonic)
        try:
            return await self._grade_within_deadline(
                trajectory_id=trajectory_id, workspace=workspace, spec=spec, frozen_delta=frozen_delta,
                queue_wait_seconds=queue_wait_seconds, queue_depth_at_enqueue=queue_depth_at_enqueue,
                backpressure_triggered=backpressure_triggered,
            )
        finally:
            _GRADING_DEADLINE.reset(token)

    async def _grade_within_deadline(
        self,
        *,
        trajectory_id: str,
        workspace: WorkspaceRunner | None,
        spec: GradingEnvSpec,
        frozen_delta: "FrozenDeltaSource | None",
        queue_wait_seconds: float,
        queue_depth_at_enqueue: int | None,
        backpressure_triggered: bool,
    ) -> GradingReport:
        total_start = time.monotonic()
        nonce = uuid.uuid4().hex[:8]
        timing_parts = {"image_pull": 0.0, "env_reset": 0.0, "prep": 0.0, "test": 0.0}
        record: _ContainerRecord | None = None
        cleaned: CleanedPatch | None = None
        fa_plan: FrozenApplyPlan | None = None
        replay_started = False
        eval_log_text: str | None = None
        peak_memory_mb = 0.0
        # W3a：grader 内部分段（与 timing_parts 并行记录；timing_parts 是冻结契约的五类口径）。
        phase = GraderPhaseTiming(
            record_id=f"timing_{nonce}", trajectory_id=trajectory_id, task_id=spec.task_id,
            frozen_delta_path=frozen_delta is not None,
        )
        self._retain_phase_timing(phase)
        phase_started = time.monotonic()  # grader_start_and_verify 从 grade() 入口起算

        def _timings() -> GradingTimingRecord:
            return GradingTimingRecord(
                record_id=f"timing_{nonce}",
                trajectory_id=trajectory_id,
                task_id=spec.task_id,
                image_pull_seconds=round(timing_parts["image_pull"], 3),
                env_reset_seconds=round(timing_parts["env_reset"], 3),
                prep_seconds=round(timing_parts["prep"], 3),
                test_seconds=round(timing_parts["test"], 3),
                total_grading_seconds=round(
                    max(time.monotonic() - total_start, timing_parts["test"]), 3
                ),
                queue_wait_seconds=round(queue_wait_seconds, 3),
                container_peak_memory_mb=peak_memory_mb,
                queue_depth_at_enqueue=queue_depth_at_enqueue,
                backpressure_triggered=backpressure_triggered,
            )

        def _infra_log_text() -> str | None:
            """infra 报告要落盘的日志文本：完整 eval 日志优先；候选测试没跑成时退到
            可信 setup / 权限布置阶段的原始输出（F2 判据的证据面）。"""

            if eval_log_text is not None:
                return eval_log_text
            return record.eval_log_partial if record is not None else None

        def _hygiene() -> PatchHygieneResult | None:
            # 没走到重放阶段的 infra 报告不附 hygiene（附了反而暗示做过 clean 重放）。
            if not replay_started:
                return None
            if frozen_delta is not None:
                # B4 P1：task-aware 筛查事实如实上报（generic projectable
                # ≠ task 级 clean）；digest = 实际应用子集的 canonical
                # digest（digest_kind 显式区分，不冒充 cleaned diff）；
                # replayed 只有应用**完成**才是 True——中途 infra 失败的
                # 报告不得声称已重放。
                if fa_plan is None:
                    return None
                return PatchHygieneResult(
                    verdict=fa_plan.verdict,
                    cleaned_patch_digest=fa_plan.applied_entry_set_digest,
                    digest_kind="applied_entry_set",
                    test_files_modified=bool(fa_plan.stripped_test_paths),
                    forbidden_path_touched=bool(fa_plan.forbidden_paths),
                    forbidden_paths=list(fa_plan.forbidden_paths),
                    replayed_on_clean_checkout=fa_plan.apply_completed,
                )
            if cleaned is None:
                return None
            return cleaned.hygiene_result(replayed_on_clean_checkout=True)

        common = dict(
            report_id=f"rpt_grading_{nonce}",
            trajectory_id=trajectory_id,
            task_id=spec.task_id,
            grader_name=spec.grader_name,
            grader_version=spec.grader_version,
        )

        try:
            # 阶段 1+2（prep 前半）：B4 起两源互斥——frozen_delta（FA
            # formal，**不读 workspace**）或 S1 导出。FA 路径先做纯绑定
            # 检查（source 内部一致 + source⟷spec + **可信评分投影路径集
            # 独立重算相等**，起容器前 fail-fast，矛盾 = BaselineIntegrityError
            # run-halt）。
            require_grading_time("queue")  # N2a：排队已耗尽期限 → 不起容器，直接 failed_to_grade
            prep_start = time.monotonic()
            if frozen_delta is not None:
                cleaned = None  # FA 路径无 diff 文本
                self._verify_frozen_delta_binding(spec, frozen_delta)
                included = set(frozen_delta.projection.included_entry_paths)
                fa_plan = screen_frozen_entries(
                    [e for e in frozen_delta.frozen_patch.entries if e.path in included],
                    spec.hygiene,
                )
                if fa_plan.verdict != "clean":
                    # W3a（D2-3）：绑定检查已证明 included == 按同一规则重算的
                    # candidate_solution 路径集，其中不可能再有控制面路径；到达
                    # 这里 = 同一进程内两次纯函数计算结果分家（程序错误），与
                    # 其它绑定矛盾同通道 run-halt——不再是"漏筛 → infra 成员
                    # 损耗"（旧 unscreened_hygiene_hit 保险杠随 D2-3 删除：控制面
                    # 路径既不是 unsafe 也不该到 grader，判定权威在投影拆分）。
                    raise BaselineIntegrityError(
                        "scoring_projection_split_inconsistent",
                        "candidate 子集经 hygiene 复筛仍命中控制面路径："
                        + ",".join((*fa_plan.stripped_test_paths, *fa_plan.forbidden_paths))[:200],
                    )
            else:
                if workspace is None:
                    raise GradingInfraError(
                        "workspace_missing_without_frozen_delta"
                    )
                try:
                    cleaned = await export_cleaned_patch(workspace, spec.hygiene)
                except WorkspaceExportError as exc:
                    raise GradingInfraError(
                        f"workspace_patch_export_failed: {exc}"
                    ) from exc
            timing_parts["prep"] += time.monotonic() - prep_start

            # 阶段 3 前置 + 阶段 3 起点：镜像就绪（P10 第一档，预拉取命中记 0.0）+ fresh 容器。
            # N2b（I16）：这两个环节的**已识别**传输 / 服务故障最多追加一次（同工件、同配置、同队列槽位、不重置期限）
            reset_start = time.monotonic()
            timing_parts["image_pull"], record = await self._ready_image_and_start_container(
                trajectory_id, spec, nonce
            )
            # 阶段 3 其余：镜像 digest 比对 + clean checkout + 血缘核验（A7 条 2）——不在重试范围
            await self._verify_image_digest(record, spec)
            checkout_head = await self._clean_checkout(record, spec)
            timing_parts["env_reset"] = time.monotonic() - reset_start
            phase.add("grader_start_and_verify", time.monotonic() - phase_started)

            # 阶段 4（prep 后半）：frozen delta 路径 = 先 exact-baseline
            # 重建比对（T0 第 2 条；mismatch → BaselineIntegrityError
            # run-halt），再直接应用 candidate_solution 子集；S1 路径 = 重放 cleaned patch
            prep_start = time.monotonic()
            replay_started = True
            if frozen_delta is not None:
                rebuild_started = time.monotonic()
                await self._verify_baseline_rebuild(
                    record, spec, frozen_delta, checkout_head
                )
                phase.add("grader_baseline_rebuild", time.monotonic() - rebuild_started)
                assert fa_plan is not None  # 阶段 1 已构造
                apply_started = time.monotonic()
                await self._apply_frozen_delta(record, spec, frozen_delta, fa_plan)
                phase.add("delta_apply", time.monotonic() - apply_started)
                apply_ok = True  # 应用失败已作 infra 抛出（A-prime：非模型负样本）
            else:
                apply_started = time.monotonic()
                apply_ok = await self._replay_patch(record, spec, cleaned)
                phase.add("delta_apply", time.monotonic() - apply_started)
            timing_parts["prep"] += time.monotonic() - prep_start
            if not apply_ok:
                # A7 条 6 三分之一：cleaned patch 在 clean checkout 上 apply 失败 = 模型负样本
                report_started = time.monotonic()
                peak_memory_mb = await self._read_peak_memory_mb(record)
                report = GradingReport(
                    **common,
                    outcome="unresolved",
                    failure_category="patch_apply_failed",
                    reward=0.0,
                    patch_hygiene=_hygiene(),
                    timings=_timings(),
                    graded_at_utc=_now_utc(),
                )
                phase.add("parser_and_report", time.monotonic() - report_started)
                return report

            # 阶段 5：跑官方 eval（合并单流 2>&1，S1-2 提醒的日志形态）
            test_start = time.monotonic()
            eval_log_text, trusted_setup_seconds = await self._run_eval(record, spec, phase)
            # F2/P2-4：`test` 只计候选测试本身；root 可信 setup（恢复 official tests / 应用 test_patch /
            # 权限布置）单独记 grader_trusted_setup（由 _run_eval 记账——判据挡下、候选测试没跑成的那次
            # 也要在计时里看得见；legacy 路径恒 0）。
            timing_parts["test"] = max(time.monotonic() - test_start - trusted_setup_seconds, 0.0)
            phase.add("test", timing_parts["test"])
            report_started = time.monotonic()
            peak_memory_mb = await self._read_peak_memory_mb(record)

            # 阶段 6：官方 parser 解析（A7 条 5）
            verdict = self._parse_eval_log(spec, eval_log_text)

            # 阶段 7：结论组装（A7 条 6/7 + hygiene 封顶）
            fields = scoring.grading_outcome_fields(verdict)
            hygiene = _hygiene()
            assert hygiene is not None  # replay_started=True 后恒成立
            if hygiene.verdict != "clean" and fields["outcome"] == "resolved":
                # A7 条 3/4 的"降级"落点：被拒 patch 即使测试全过也不得 resolved
                # （contracts 校验器同样会拒绝 resolved+非 clean，这里是第一道闸）。
                # W3a 注：FA frozen-delta 路径的 hygiene 描述的是**已重放的 candidate 子集**，
                # 按可信评分投影构造恒为 clean；本分支只对 S1 diff 文本路径（冻结回退面）有效。
                fields = {
                    **fields,
                    "outcome": "unresolved",
                    "failure_category": "tests_failed",
                    "reward": 0.0,
                }
            report = GradingReport(
                **common,
                **fields,
                patch_hygiene=hygiene,
                eval_log_ref=self._persist_eval_log(nonce, trajectory_id, eval_log_text),
                timings=_timings(),
                graded_at_utc=_now_utc(),
            )
            phase.add("parser_and_report", time.monotonic() - report_started)
            return report
        except GradingInfraError as exc:
            # infra 族收口（P4）：本分支不存在 reward 取值——想给 infra 报告塞
            # reward 连参数都没有，schema 校验器是第二道锁。
            report_started = time.monotonic()
            if record is not None:
                peak_memory_mb = await self._read_peak_memory_mb(record)
            report = GradingReport(
                **common,
                outcome="failed_to_grade",
                failure_category=exc.category,
                reward=None,
                infra_failure_detail=exc.detail,
                patch_hygiene=_hygiene(),
                # 候选测试从未启动时没有 eval 日志，但可信 setup / 权限布置的原始输出必须留下来
                # （F2 判据挡下的那次，故障现场就在这段里）。
                eval_log_ref=(
                    self._persist_eval_log(nonce, trajectory_id, _infra_log_text())
                    if _infra_log_text() is not None
                    else None
                ),
                timings=_timings(),
                graded_at_utc=_now_utc(),
            )
            phase.add("parser_and_report", time.monotonic() - report_started)
            return report
        finally:
            if record is not None:
                cleanup_started = time.monotonic()
                try:
                    # 批 D-2：有界收口——仍运行 / 无法确认 → GradingScopeTerminationError 穿队列上抛
                    # （替换在途的 failed_to_grade 结果：scope 未终止比单次评分结果更重要）
                    await self._close_container_scope(record)
                finally:
                    phase.add("grader_cleanup", time.monotonic() - cleanup_started)

    # ------------------------------------------------------------------ gc
    async def gc(
        self, trajectory_id: str | None = None, ttl_seconds: float | None = None
    ) -> list[str]:
        """记账回收（P1/P8）：按 trace 精确回收，或按 TTL 扫过期；都不传 = 全量回收。"""

        now = time.monotonic()
        removed: list[str] = []
        for record in self._records:
            if record.removed:
                continue
            if trajectory_id is not None and record.trajectory_id != trajectory_id:
                continue
            if ttl_seconds is not None and (now - record.created_monotonic) < ttl_seconds:
                continue
            await self._remove_container(record)
            if record.removed:
                removed.append(record.name)
        return removed

    # ------------------------------------------------------------------ 内部：镜像
    async def _ensure_image(self, image: str) -> float:
        """镜像就绪并返回拉取耗时（本地命中/已就绪 = 0.0，F5 口径）。

        per-image 锁让并发的 prepare 与 grade 只拉一次（P5 竞态的另一半：
        谁先到谁拉，后到者等锁再查缓存）。
        """

        if image in self._images_ready:
            return 0.0
        lock = self._image_locks.setdefault(image, asyncio.Lock())
        # N2a：等锁、inspect、pull 都消费同一评分期限（wait_for 取消 → 默认 runner 杀宿主 CLI）
        try:
            await asyncio.wait_for(lock.acquire(), timeout=bounded_by_grading_deadline(math.inf, "image_lock"))
        except (TimeoutError, asyncio.TimeoutError):
            raise GradingInfraError(f"{GRADING_DEADLINE_EXHAUSTED}:image_lock") from None
        try:
            if image in self._images_ready:
                return 0.0
            inspect = await self._await_within_grading_deadline(
                self._docker("image", "inspect", image), phase="image_inspect"
            )
            if inspect.exit_code == 0:
                self._images_ready.add(image)
                return 0.0
            pull_start = time.monotonic()
            pull = await self._await_within_grading_deadline(self._docker("pull", image), phase="image_pull")
            if pull.exit_code != 0:
                raise GradingInfraError(
                    f"grading_image_pull_failed:{image}:{pull.stderr.strip()[-300:]}",
                    op="image_pull", exit_code=pull.exit_code, stderr=pull.stderr,
                )
            self._images_ready.add(image)
            return time.monotonic() - pull_start
        finally:
            lock.release()

    async def _await_within_grading_deadline(self, aw, *, phase: str):
        """N2a：一个 Docker 操作受评分期限约束；到点取消它（默认 runner 在取消路径 kill+wait 宿主 CLI）。"""

        left = require_grading_time(phase)
        if left is None:
            return await aw
        try:
            return await asyncio.wait_for(aw, timeout=left)
        except (TimeoutError, asyncio.TimeoutError):
            raise GradingInfraError(f"{GRADING_DEADLINE_EXHAUSTED}:{phase}") from None

    # ------------------------------------------------------------------ 内部：容器生命周期
    async def _ready_image_and_start_container(
        self, trajectory_id: str, spec: GradingEnvSpec, nonce: str
    ) -> tuple[float, _ContainerRecord]:
        """N2b（I16，补充说明 §8 已批范围）：镜像就绪 + 新 grader 容器启动，整次评分任务最多 MAX_GRADING_ATTEMPTS 次。

        只有 `classify_docker_transport_error` 认出的传输 / 服务故障才追加一次；prelaunch / profile 违规、
        准备阶段、候选测试一律不在这里（它们不经本函数的 except）。追加前：期限未耗尽（不重置）、manager 未
        关停；`docker run` 失败时容器可能已按本次名字创建——先把该名字登记进 `_records` 并走
        `_close_container_scope`（absent / stopped → 可继续；running / unknown → GradingScopeTerminationError，
        run-fatal，不重试）。第二次用新 nonce / 新名字；两次都失败 → 一条 GradingInfraError 带两次原始错误。
        """

        first_failure: GradingInfraError | None = None
        attempt_nonce = nonce
        for attempt in range(1, MAX_GRADING_ATTEMPTS + 1):
            try:
                pull_seconds = await self._ensure_image(spec.image)
                record = await self._start_container(trajectory_id, spec, attempt_nonce)
                return pull_seconds, record
            except GradingInfraError as exc:
                category = classify_docker_transport_error(exc.op or "", exc.exit_code or 0, exc.stderr)
                if first_failure is not None:
                    raise GradingInfraError(
                        f"{exc.detail}; first_attempt: {first_failure.detail}",
                        op=exc.op, exit_code=exc.exit_code, stderr=exc.stderr,
                    ) from exc
                if category is None or attempt >= MAX_GRADING_ATTEMPTS or self._closed:
                    raise
                require_grading_time("regrade")  # 共用同一评分期限：耗尽即不再追加
                if exc.op == "container_start" and exc.container_name:
                    # 创建回包丢失不证明容器不存在：按本次名字登记并收口（对象进现有清理记录，close/gc 可见）
                    temp = _ContainerRecord(
                        name=exc.container_name, trajectory_id=trajectory_id,
                        created_epoch=time.time(), created_monotonic=time.monotonic(),
                    )
                    self._records.append(temp)
                    await self._close_container_scope(temp)
                first_failure = exc
                event = {
                    "trajectory_id": trajectory_id, "op": exc.op, "category": category, "attempt": attempt,
                    "detail": exc.detail[:300],
                }
                self.regrade_events.append(event)
                del self.regrade_events[:-256]
                _emit_grading_event(GRADING_REGRADE_EVENT, **event)
                attempt_nonce = uuid.uuid4().hex[:8]
        raise AssertionError("unreachable: regrade loop must return or raise")

    async def _start_container(
        self, trajectory_id: str, spec: GradingEnvSpec, nonce: str
    ) -> _ContainerRecord:
        prefix = self.config.label_prefix
        name = f"{self.config.name_prefix}-{_sanitize_for_name(trajectory_id)}-{nonce}"
        created_epoch = time.time()

        # 租约先行：网络策略唯一来源是 SandboxLease（purpose=grading 在 schema 层
        # 锁死 deny_all，P9），docker 参数由租约推导——想开网先得改契约。
        profile = self.config.sandbox_profile
        image_id = await self._await_within_grading_deadline(
            self._docker("image", "inspect", "-f", "{{.Id}}", spec.image), phase="image_id_inspect"
        )
        lease = SandboxLease(
            lease_id=f"lease_{name}",
            container_id=name,
            image_digest=image_id.stdout.strip(),
            purpose="grading",
            created_by="grading_manager",
            network_policy_owner="grading_manager",
            network_policy="deny_all",
            permission_policy_owner="grading_manager",
            # W3b：profile 在场时候选代码（官方 eval 脚本）以非 root 候选执行用户运行；可信步骤仍 root。
            run_as_user="root" if profile is None else profile.candidate_exec_user,
            cleanup=CleanupPolicy(
                owner="grading_manager",
                steps=["remove_container", "release_lease"],
                on_cleanup_failure="record_runtime_finding_and_infra_failure",
                timeout_seconds=self.config.cleanup_timeout_seconds,
            ),
            created_at_utc=_now_utc(),
        )
        network_args = {"deny_all": ("--network", "none")}[lease.network_policy]

        labels: list[str] = [
            "--label",
            f"{prefix}.owner={self.run_id}",
            "--label",
            f"{prefix}.trajectory={trajectory_id}",
            "--label",
            f"{prefix}.created_at_epoch={int(created_epoch)}",
        ]
        # 本 run owner label（miles GPU spike shutdown 探针锚点，与 rollout
        # 容器同款）：MILES_RH2_RUN_ID 在环境中时给评分容器盖同一 run 印章，
        # postrun_probes.py shutdown 探针按 label=rh2.run_id=<run_id> 精确归属；
        # 未设（单测/非 spike 链）时 docker 参数保持原样。
        if run_id := os.environ.get("MILES_RH2_RUN_ID"):
            labels += ["--label", f"rh2.run_id={run_id}"]
        declared_binds: list[tuple[str, str]] = []
        if spec.checkout_mode == "clone_from_readonly_snapshot":
            # P6：共享快照永远只读挂载，评分只在容器私有的 /testbed 副本上进行。
            declared_binds.append((spec.snapshot_host_path, spec.snapshot_mount_path))
        if profile is None:
            args: list[str] = ["run", "--detach", *network_args, *labels]
            for src, dst in declared_binds:
                args += ["--volume", f"{src}:{dst}:ro"]
            args += ["--name", name, spec.image, "sleep", "infinity"]
        else:
            # W3b：grader 容器参数只由独立 grader profile 组装（deny_all、cap-drop ALL + 可信初始化
            # 能力、no-new-privileges、PID/CPU/memory+swap/tmpfs 限额、只读声明挂载）。
            args = profile.docker_run_args(
                name=name, image=spec.image, labels=labels, declared_readonly_binds=declared_binds
            )

        run = await self._await_within_grading_deadline(self._docker(*args), phase="container_start")
        if run.exit_code != 0:
            raise GradingInfraError(
                f"grading_container_start_failed:{run.stderr.strip()[-300:]}",
                op="container_start", exit_code=run.exit_code, stderr=run.stderr, container_name=name,
            )
        self.leases.append(lease)
        record = _ContainerRecord(
            name=name,
            trajectory_id=trajectory_id,
            created_epoch=created_epoch,
            created_monotonic=time.monotonic(),
        )
        self._records.append(record)
        if profile is not None:
            await self._grader_prelaunch(record, profile, declared_binds)
        return record

    async def _grader_prelaunch(
        self, record: _ContainerRecord, profile: "GraderSandboxProfile", declared_binds: list[tuple[str, str]]
    ) -> None:
        """W3b：grader 容器创建后、任何评分步骤之前——root 可信初始化（建候选执行用户、safe.directory）
        + 一次 inspect + 一次候选用户身份探针（断网只剩 loopback、非 root、CapEff=0、限额）。
        不合格 → 先移除容器再抛 SandboxProfileViolation（run-halt 通道）。"""

        from repoharness2.adapters.slime.sandbox_profile import (
            grader_trusted_init_script,
            run_grader_prelaunch_check,
            run_trusted_init,
        )

        try:
            init = await run_trusted_init(
                self._docker, name=record.name, script=grader_trusted_init_script(profile),
                timeout=profile.init_timeout_seconds,
            )
        except RuntimeError as exc:
            await self._remove_container(record)
            raise SandboxProfileViolation(
                "grader_trusted_init_failed", f"{record.name}: {str(exc)[:400]}"
            ) from exc
        report = await run_grader_prelaunch_check(
            self._docker, name=record.name, profile=profile, declared_readonly_binds=declared_binds
        )
        summary = report.to_dict()
        summary["trusted_init"] = init
        record.prelaunch = summary
        self.prelaunch_checks.append(summary)
        del self.prelaunch_checks[:-256]
        if not report.ok:
            await self._remove_container(record)
            raise SandboxProfileViolation(
                "grader_sandbox_profile_violation",
                f"{record.name}: " + "; ".join(report.violations)[:600],
            )

    async def _remove_container(self, record: _ContainerRecord, *, timeout: float | None = None) -> None:
        if record.removed:
            return
        try:
            if timeout is None:
                rm = await self._docker("rm", "-f", record.name)
            else:
                # 批 D-2（Codex 联合审查 R2）：收口路径的 rm 受剩余清理预算约束（wait_for 取消 → 默认
                # runner kill+wait 宿主 CLI）；超时 = 未删除，留痕后由状态判定继续
                rm = await asyncio.wait_for(self._docker("rm", "-f", record.name), timeout=max(0.0, timeout))
        except (TimeoutError, asyncio.TimeoutError):
            self.cleanup_failures.append(f"container_rm_timeout:{record.name}:{timeout}s")
            return
        if rm.exit_code == 0:
            record.removed = True
        else:
            # Q8：清理失败不许静默——留痕供 S1-6 收口为 runtime finding。
            self.cleanup_failures.append(
                f"container_rm_failed:{record.name}:{rm.stderr.strip()[-200:]}"
            )

    async def _container_state(self, record: _ContainerRecord, *, timeout: float | None = None) -> str:
        """批 D-2：容器状态三分——"running" / "stopped"（存在但已退出）/ "absent"（已删除）/
        "unknown"（inspect 失败：daemon 不可达等）。此前 `_container_running` 把 inspect 失败也压成
        False（"已死"），Codex 批 B/计划审查 R4：无法确认 ≠ 已停止。"""

        try:
            if timeout is None:
                inspect = await self._docker("inspect", "-f", "{{.State.Running}}", record.name)
            else:
                inspect = await asyncio.wait_for(
                    self._docker("inspect", "-f", "{{.State.Running}}", record.name), timeout=max(0.0, timeout)
                )
        except (TimeoutError, asyncio.TimeoutError):
            return "unknown"  # inspect 未在预算内返回 = 无法确认
        if inspect.exit_code == 0:
            out = inspect.stdout.strip().lower()
            if out == "true":
                return "running"
            if out == "false":
                return "stopped"
            return "unknown"  # 成功退出也只认明确的 true / false
        err = (inspect.stderr or inspect.stdout).strip().lower()
        # Codex 联合审查 R4：只认**明确指向本容器**的"不存在"（docker 的形态："Error: No such object: <name>" /
        # "No such container: <name>"）。连接 / 传输诊断（如 "dial unix /var/run/docker.sock: connect: no such
        # file or directory"）里的 "no such" 指的是 socket，不是容器——容器可能仍在另一端运行，只能是 unknown。
        if ("no such object" in err or "no such container" in err) and record.name.lower() in err:
            return "absent"
        return "unknown"

    async def _container_running(self, record: _ContainerRecord) -> bool:
        return (await self._container_state(record)) == "running"

    async def _close_container_scope(self, record: _ContainerRecord) -> None:
        """批 D-2：grade() 收尾的**有界**收口（总截止点 = config.cleanup_timeout_seconds，Codex 联合审查
        R2：每个 rm / inspect / kill 都拿剩余预算做 wait_for；预算耗尽 = 状态无法确认）。rm -f 成功 →
        已删除；失败 → 看状态：已停止 / 已删除 → 只留诊断（cleanup_failures 已由 _remove_container 记）；
        仍运行 → docker kill 再 rm -f 一次；最终仍运行或无法确认 → GradingScopeTerminationError（run-fatal，
        穿队列上抛）。停止与删除分开表述。"""

        budget = float(self.config.cleanup_timeout_seconds)
        started = time.monotonic()

        def left() -> float:
            return max(0.0, budget - (time.monotonic() - started))

        await self._remove_container(record, timeout=left())
        if record.removed:
            return
        state = await self._container_state(record, timeout=left()) if left() > 0 else "unknown"
        if state in ("stopped", "absent"):
            self.cleanup_failures.append(f"container_scope_stopped_but_not_removed:{record.name}:{state}")
            return
        if state == "running" and left() > 0:
            try:
                await asyncio.wait_for(self._docker("kill", record.name), timeout=left())
            except (TimeoutError, asyncio.TimeoutError):
                self.cleanup_failures.append(f"container_kill_timeout:{record.name}")
            await self._remove_container(record, timeout=left())
            if record.removed:
                return
            state = await self._container_state(record, timeout=left()) if left() > 0 else "unknown"
            if state in ("stopped", "absent"):
                self.cleanup_failures.append(f"container_scope_killed_but_not_removed:{record.name}:{state}")
                return
        exhausted = left() <= 0
        self.cleanup_failures.append(
            f"container_scope_termination_failed:{record.name}:{state}"
            + (f":cleanup_budget_exhausted_{budget}s" if exhausted else "")
        )
        raise GradingScopeTerminationError(
            "grading_scope_termination_failed",
            f"评分容器 {record.name} 在有界收口（rm -f → kill → rm -f，预算 {budget}s"
            f"{'，已耗尽' if exhausted else ''}）后状态仍为 {state}"
            "——scope 无法确认终止，按 06 A4 run-halt（继续接新任务只会累积残留）。",
        )

    async def _exec_bash(
        self,
        record: _ContainerRecord,
        script: str,
        *,
        input_bytes: bytes | None = None,
        user: str | None = None,
        home: str | None = None,
    ) -> ExecResult:
        # W3b：user/home 只在"执行候选代码"（官方 eval 脚本）时给出——以候选执行用户身份运行；
        # 未给出时参数形状与 W3b 之前逐字相同（可信步骤仍 root）。
        args: list[str] = ["exec"]
        if input_bytes is not None:
            args.append("-i")
        if user is not None:
            args += ["-u", user]
        if home is not None:
            args += ["-e", f"HOME={home}"]
        args += [record.name, "bash", "-c", script]
        if input_bytes is not None:
            return await self._docker(*args, input_bytes=input_bytes)
        return await self._docker(*args)

    async def _exec_bash_checked(
        self,
        record: _ContainerRecord,
        script: str,
        *,
        phase: str,
        timeout: float,
        input_bytes: bytes | None = None,
        user: str | None = None,
        home: str | None = None,
    ) -> ExecResult:
        """带分段超时（P3）与容器死亡检测（P4）的 exec：
        超时 -> infra；命令失败且容器已死 -> infra（killed）；其余交调用方定夺。"""

        base_timeout = timeout
        timeout = bounded_by_grading_deadline(timeout, phase)  # N2a：分段 timeout 与评分期限取小
        try:
            result = await asyncio.wait_for(
                self._exec_bash(record, script, input_bytes=input_bytes, user=user, home=home), timeout=timeout
            )
        except (TimeoutError, asyncio.TimeoutError):
            if timeout < base_timeout:
                # 是评分期限而不是分段 timeout 先到：归因写清楚（同为 infra 族 failed_to_grade）
                raise GradingInfraError(f"{GRADING_DEADLINE_EXHAUSTED}:{phase}") from None
            raise GradingInfraError(
                f"grading_{phase}_timeout_after_{int(timeout)}s"
            ) from None
        if result.exit_code != 0:
            state = await self._container_state(
                record, timeout=min(30.0, float(self.config.cleanup_timeout_seconds))
            )
            if state in ("stopped", "absent"):
                raise GradingInfraError(f"grading_container_killed_during_{phase}")
            if state == "unknown":
                # 批 D-2：inspect 失败（daemon 不可达等）≠ 容器已死——单独归因，不冒充 killed
                raise GradingInfraError(f"grading_container_state_unknown_during_{phase}")
        return result

    async def _verify_image_digest(self, record: _ContainerRecord, spec: GradingEnvSpec) -> None:
        """启动后镜像 digest 比对（codex#1 fail-closed）：容器实际运行的镜像
        必须命中 envpack 冻结的 image_manifest_digest（查 RepoDigests，不是 image ID）。

        比对对象是 `docker inspect -f {{.Image}}` 给出的**容器实际镜像**而非
        spec.image 标签——标签在 inspect 与 run 之间可能被重指（:latest 漂移），
        以运行中容器为准才封得住这个窗口。本地构建 fixture 镜像（无 RepoDigests）
        走 spec.image_local_build 显式豁免；豁免缺席时空 RepoDigests 一律拒绝。
        """

        if spec.image_local_build:
            return  # 显式豁免：本地构建镜像没有 RepoDigests，schema 层已强制声明
        expected = spec.image_manifest_digest
        assert expected is not None  # GradingEnvSpec.__post_init__ 的二选一保证
        ref = await self._docker("inspect", "-f", "{{.Image}}", record.name)
        if ref.exit_code != 0:
            raise GradingInfraError(
                f"grading_image_ref_inspect_failed:{ref.stderr.strip()[-300:]}"
            )
        digests = await self._docker(
            "image", "inspect", "-f", materialize.IMAGE_REPO_DIGESTS_FORMAT, ref.stdout.strip()
        )
        check = materialize.evaluate_image_digest(
            expected, digests.exit_code, digests.stdout, digests.stderr
        )
        if not check.ok:
            raise GradingInfraError(
                f"grading_image_digest_mismatch:{check.failure_message()[:400]}"
            )

    # ------------------------------------------------------------------ 内部：评分各阶段
    async def _clean_checkout(self, record: _ContainerRecord, spec: GradingEnvSpec) -> str:
        """A7 条 2：准备 clean checkout 并用 S1-2 血缘判据核验。

        返回容器内 /testbed 的实际 HEAD sha（探针实测值）。血缘判据接受
        HEAD==base 或 HEAD^==base（官方镜像 overlay commit 形态，
        materialize.py S0-7）；B4 用返回值与 baseline.materialized_head
        对账——评分树必须与模型开工的树是**同一个 commit**。"""

        if spec.checkout_mode == "clone_from_readonly_snapshot":
            clone = await self._exec_bash_checked(
                record,
                f"git clone --no-hardlinks {spec.snapshot_mount_path} {spec.testbed_path} "
                f"&& git -C {spec.testbed_path} checkout --detach {spec.base_commit}",
                phase="env_reset",
                timeout=spec.env_reset_timeout_seconds,
            )
            if clone.exit_code != 0:
                raise GradingInfraError(
                    f"grading_clean_checkout_failed:{clone.stderr.strip()[-300:]}"
                )
        probe = await self._exec_bash_checked(
            record,
            materialize.build_probe_script(spec.base_commit),
            phase="env_reset",
            timeout=spec.env_reset_timeout_seconds,
        )
        check = materialize.evaluate_probe(
            spec.base_commit, probe.exit_code, probe.stdout, probe.stderr
        )
        if not check.ok:
            raise GradingInfraError(
                f"grading_checkout_lineage_failed:{check.failure_message()[:300]}"
            )
        return check.head

    def _verify_frozen_delta_binding(
        self, spec: GradingEnvSpec, source: "FrozenDeltaSource"
    ) -> None:
        """B4 P0-1 + P1-2 纯检查半区：source 三对象完整对账 + source⟷spec 绑定。

        不需要容器，放在评分早段（起容器之前）fail-fast。任何不一致 =
        BaselineIntegrityError（run-halt 通道）。B5 起这些对象会被持久化
        再装配，本函数是装配后的信任边界（不管 source 来自内存还是磁盘）。

        materialized_head 故意**不**与 spec.base_commit 绑定：官方 SWE
        镜像的 /testbed HEAD 是构建时叠加的 overlay commit（且内容不保证
        为空——materialize.py S0-7 实证），合法形态是 HEAD^==base_commit。
        它与 grader 实际 checkout HEAD 的对账在 _verify_baseline_rebuild
        （容器半区）完成。"""

        from repoharness2.contracts.baseline_manifest import (
            compute_baseline_manifest_digest,
        )
        from repoharness2.contracts.frozen_patch import compute_frozen_patch_digest

        art = source.frozen_patch
        baseline = source.baseline_manifest
        proj = source.projection
        art_digest = compute_frozen_patch_digest(art)
        if art_digest != source.frozen_patch_digest:
            raise BaselineIntegrityError(
                "frozen_delta_binding_mismatch",
                f"artifact 重算 digest {art_digest} != source 声明 {source.frozen_patch_digest}",
            )
        if art_digest != proj.frozen_patch_digest:
            raise BaselineIntegrityError(
                "frozen_delta_binding_mismatch",
                f"projection 锚 {proj.frozen_patch_digest} != artifact {art_digest}",
            )
        base_digest = compute_baseline_manifest_digest(baseline)
        if art.baseline_manifest_digest != base_digest:
            raise BaselineIntegrityError(
                "frozen_delta_binding_mismatch",
                f"artifact.baseline_manifest_digest {art.baseline_manifest_digest} "
                f"!= baseline 重算 {base_digest}",
            )
        # artifact ⟷ baseline 血缘四元组（classify 已互检过；grader 独立
        # 复核——B5 装配后 classify 的结论不随对象同行）
        for field_name in ("task_id", "public_bundle_digest",
                           "runtime_image_digest", "materialized_head"):
            if getattr(art, field_name) != getattr(baseline, field_name):
                raise BaselineIntegrityError(
                    "frozen_delta_binding_mismatch",
                    f"lineage {field_name}: artifact={getattr(art, field_name)!r} "
                    f"!= baseline={getattr(baseline, field_name)!r}",
                )
        # projection ⟷ artifact 身份绑定
        for field_name in ("rollout_execution_id", "physical_attempt_id"):
            if getattr(proj, field_name) != getattr(art, field_name):
                raise BaselineIntegrityError(
                    "frozen_delta_binding_mismatch",
                    f"identity {field_name}: projection={getattr(proj, field_name)!r} "
                    f"!= artifact={getattr(art, field_name)!r}",
                )
        # W3a（D2-3 可信评分投影）：projection 路径集必须**等于**按同一控制面规则
        # （spec.hygiene）对 artifact 独立重算的 candidate_solution 路径集——既不能
        # "隐去"solution 路径（少了 = 拿不完整改动评分），也不能"夹带"控制面路径
        # （多了 = 控制面改动会影响 reward）。B4 v1 的"等于 artifact 全路径集"是本
        # 检查在"控制面为空"时的特例。对称差即契约矛盾（run-halt）。
        entry_paths = {e.path for e in art.entries}
        expected = expected_candidate_paths(list(art.entries), spec.hygiene)
        included = set(proj.included_entry_paths)
        if not included <= entry_paths:
            diff = sorted(included - entry_paths)[:5]
            raise BaselineIntegrityError(
                "frozen_delta_binding_mismatch",
                f"projection 路径集含 artifact 不存在的路径（示例：{diff}）",
            )
        if included != expected:
            diff = sorted(included.symmetric_difference(expected))[:5]
            raise BaselineIntegrityError(
                "frozen_delta_binding_mismatch",
                "projection 路径集 != 可信评分投影重算的 candidate_solution 路径集"
                f"（对称差示例：{diff}；artifact 路径数 {len(entry_paths)}，"
                f"控制面路径数 {len(entry_paths) - len(expected)}）",
            )
        # 逐 entry 前置状态 vs baseline：add 必须原先不存在；modify/delete
        # 必须存在；delete 的对象类型必须与 baseline 一致（modify 允许类型
        # 变化——symlink→regular 是合法 delta）。防"删除 baseline 不存在的
        # 路径"这类语义矛盾 delta 静默成功（rm -f 幂等吞掉）。
        base_by_path = {e.path: e for e in baseline.entries}
        for e in art.entries:
            if e.operation == "add" and e.path in base_by_path:
                raise BaselineIntegrityError(
                    "frozen_delta_prestate_mismatch",
                    f"add 路径在 baseline 已存在：{e.path!r}",
                )
            if e.operation in ("modify", "delete") and e.path not in base_by_path:
                raise BaselineIntegrityError(
                    "frozen_delta_prestate_mismatch",
                    f"{e.operation} 路径在 baseline 不存在：{e.path!r}",
                )
            if (
                e.operation == "delete"
                and base_by_path[e.path].object_type != e.object_type
            ):
                raise BaselineIntegrityError(
                    "frozen_delta_prestate_mismatch",
                    f"delete 对象类型不符：entry={e.object_type} "
                    f"baseline={base_by_path[e.path].object_type}（{e.path!r}）",
                )
        # source ⟷ spec 绑定。镜像不做相等断言：rollout 镜像 = 官方任务
        # 镜像 + harness 层，与评分镜像合法不同（评分镜像自身由
        # _verify_image_digest 对 RepoDigests fail-closed）；树内容等价性
        # 由 census 重建比对直接证明。
        for label, got, expect in (
            ("task_id", baseline.task_id, spec.task_id),
            ("workdir", baseline.workdir, spec.testbed_path),
            ("task_base_commit", baseline.task_base_commit, spec.base_commit),
        ):
            if got != expect:
                raise BaselineIntegrityError(
                    "grading_spec_binding_mismatch",
                    f"{label}: baseline={got!r} != spec={expect!r}",
                )

    async def _verify_baseline_rebuild(
        self,
        record: "_ContainerRecord",
        spec: GradingEnvSpec,
        source: "FrozenDeltaSource",
        checkout_head: str,
    ) -> None:
        """B4 P0-1 容器半区（T0 拍板文本第 2 条逐字）：apply 前在 fresh
        checkout 上用 B1 的同一 census 脚本/解析器**重建完整
        BaselineWorkspaceManifestV1**，digest 不等 = grader 看到的树 ≠
        模型开工时的树 → run-halt。lineage 字段从 source.baseline 复制
        （容器内无法重推导；它们的真伪由绑定检查与 digest 自包含性负责），
        因此本比对的有效信号 = 全部 entries（path/type/mode/content 或
        symlink digest，lstat/no-follow）+ 排除区路径集 + policy。

        入口先做 HEAD 对账：grader 实际 checkout HEAD（探针实测）必须
        等于 baseline.materialized_head——官方镜像 HEAD 是 overlay commit
        （≠ base_commit 且内容可非空），两侧同镜像 → 同 overlay HEAD；
        不等说明评分树与模型开工树不是同一个 commit。"""

        if checkout_head != source.baseline_manifest.materialized_head:
            raise BaselineIntegrityError(
                "grading_head_mismatch",
                f"grader checkout HEAD {checkout_head!r} != "
                f"baseline.materialized_head "
                f"{source.baseline_manifest.materialized_head!r}"
                "（评分树与模型开工树不是同一 commit）",
            )

        # 局部 import：baseline_census 属 adapters.slime 包，包 __init__ 会
        # 拉起 generate → generate 反向 import 本模块，模块级互相引用成环；
        # 延迟到调用时（彼时两模块都已初始化完毕）是最小解。census 算法
        # 本体仍是 B1 单一权威，这里零复制。
        from repoharness2.adapters.slime.baseline_census import (
            BaselineCensusError,
            build_census_script,
            parse_census_output,
        )
        from repoharness2.contracts.baseline_manifest import (
            compute_baseline_manifest_digest,
        )

        baseline = source.baseline_manifest
        res = await self._exec_bash_checked(
            record,
            build_census_script(spec.testbed_path, baseline.policy),
            phase="baseline_rebuild",
            timeout=spec.env_reset_timeout_seconds,
        )
        if res.exit_code != 0:
            raise BaselineIntegrityError(
                "baseline_rebuild_census_failed",
                f"census 脚本失败（exit={res.exit_code}）：{res.stderr.strip()[-300:]}",
            )
        try:
            rebuilt = parse_census_output(
                res.stdout,
                task_id=baseline.task_id,
                workdir=baseline.workdir,
                public_bundle_digest=baseline.public_bundle_digest,
                runtime_image_digest=baseline.runtime_image_digest,
                materialized_head=baseline.materialized_head,
                task_base_commit=baseline.task_base_commit,
                policy=baseline.policy,
            )
        except BaselineCensusError as exc:
            raise BaselineIntegrityError(
                "baseline_rebuild_parse_failed", str(exc)
            ) from exc
        expect = compute_baseline_manifest_digest(baseline)
        got = compute_baseline_manifest_digest(rebuilt)
        if got != expect:
            raise BaselineIntegrityError(
                "baseline_digest_mismatch",
                f"fresh checkout 重建 manifest digest {got} != baseline {expect}"
                f"（rebuilt_entries={len(rebuilt.entries)}, "
                f"baseline_entries={len(baseline.entries)}）",
            )

    async def _apply_frozen_delta(
        self,
        record: "_ContainerRecord",
        spec: GradingEnvSpec,
        source: "FrozenDeltaSource",
        plan: FrozenApplyPlan,
    ) -> None:
        """B4：在已通过 baseline 重建校验的 checkout 上直接应用冻结 delta
        （无 git、无 diff 文本）。只应用 plan.applied_paths（task-aware
        hygiene 剔除后的子集）。全部命令带 `--` 且写入前先 unlink 旧对象
        （P0-2：`cat >` 会跟随旧 symlink 写穿 target）。任何失败 =
        GradingInfraError（评分动作故障，reward=None，不得记模型 reward 0）。"""

        entries = {e.path: e for e in source.frozen_patch.entries}
        included = [p for p in plan.applied_paths if p in entries]

        # 防御纵深（Falsifier F6，非模型可控但无上游拦截）：若 baseline 树
        # 里某个祖先目录本身是 symlink（如官方镜像在 base_commit 就带
        # `d -> /outside` 的目录软链），则 `mkdir -p ./d && cat > ./d/x`
        # 会**跟随该软链写到 testbed 之外**。模型无法注入这种祖先（模型的
        # 任何 symlink 都是独立 entry，被 frozen_patch 父子前缀校验挡掉，
        # 且 census 等价证明树==baseline），所以这里只可能由 baseline 自身
        # 的软链形状触发。拒绝应用（apply 安全性拒绝 = GradingInfraError
        # 成员损耗、reward=None，非模型负样本；不升 run-halt——树本身与
        # baseline 一致，是环境形状问题不是事实分家。是否因"官方镜像系统性
        # 带逃逸软链"升级为 run-halt，留 B6 真实镜像证据裁定）。
        baseline_symlink_paths = {
            e.path for e in source.baseline_manifest.entries
            if e.object_type == "symlink"
        }
        if baseline_symlink_paths:
            for path in included:
                segs = path.split("/")
                for i in range(1, len(segs)):
                    ancestor = "/".join(segs[:i])
                    if ancestor in baseline_symlink_paths:
                        raise GradingInfraError(
                            f"apply_path_ancestor_is_symlink:{path}:祖先 "
                            f"{ancestor!r} 在 baseline 中是软链，拒绝跟随写出"
                        )

        async def _run(script: str, phase: str, input_bytes: bytes | None = None) -> None:
            res = await self._exec_bash_checked(
                record,
                script,
                phase=phase,
                timeout=spec.apply_timeout_seconds,
                input_bytes=input_bytes,
            )
            if res.exit_code != 0:
                raise GradingInfraError(
                    f"{phase}_failed:{res.stderr.strip()[-200:]}"
                )

        # 两遍应用：先全部 delete，再写入/建链——dir↔file 互换类 delta 里
        # 旧对象必须先消失（同名前缀路径的写入才不会撞上残留）。
        for path in sorted(included):
            if entries[path].operation == "delete":
                await _run(
                    build_delta_delete_command(spec.testbed_path, path),
                    "delta_delete",
                )
        for path in sorted(included):
            e = entries[path]
            if e.operation == "delete":
                continue
            raw = base64.b64decode(e.content_b64, validate=True)
            digest = "sha256:" + hashlib.sha256(raw).hexdigest()
            if digest != e.content_digest:
                raise GradingInfraError(f"delta_content_digest_mismatch:{path}")
            if e.object_type == "symlink":
                try:
                    target = raw.decode("utf-8", errors="strict")
                except UnicodeDecodeError as exc:
                    # B3 已 fail-closed 拒收非 UTF-8 target（unsafe），此处
                    # 是防裸异常逃逸的兜底：typed infra，不许穿透评分链。
                    raise GradingInfraError(
                        f"delta_symlink_target_undecodable:{path}"
                    ) from exc
                await _run(
                    build_delta_symlink_command(spec.testbed_path, path, target),
                    "delta_symlink",
                )
            else:
                await _run(
                    build_delta_write_command(
                        spec.testbed_path, path, mode=e.mode, operation=e.operation
                    ),
                    "delta_write",
                    input_bytes=raw,
                )
        plan.apply_completed = True

    async def _replay_patch(
        self, record: _ContainerRecord, spec: GradingEnvSpec, cleaned: CleanedPatch
    ) -> bool:
        """在 clean checkout 上重放 cleaned patch。返回 apply 是否成功。"""

        if not cleaned.cleaned_patch.strip():
            return True  # 清洗后为空（或 agent 零改动）：no-op 重放，直接跑基线测试
        write = await self._exec_bash_checked(
            record,
            "mkdir -p /rh2 && cat > /rh2/cleaned.patch",
            phase="patch_write",
            timeout=spec.apply_timeout_seconds,
            input_bytes=cleaned.cleaned_patch.encode(),
        )
        if write.exit_code != 0:
            raise GradingInfraError(
                f"grading_patch_write_failed:{write.stderr.strip()[-300:]}"
            )
        apply = await self._exec_bash_checked(
            record,
            f"cd {spec.testbed_path} && git apply --whitespace=nowarn /rh2/cleaned.patch",
            phase="patch_apply",
            timeout=spec.apply_timeout_seconds,
        )
        return apply.exit_code == 0

    async def _write_root_script(self, record: _ContainerRecord, path: str, text: str, *, timeout: float) -> None:
        """root 写脚本（属主 root、umask 022 → 0644：候选用户可读不可改）。"""

        write = await self._exec_bash_checked(
            record,
            f"mkdir -p $(dirname {path}) && cat > {path}",
            phase="eval_write",
            timeout=timeout,
            input_bytes=text.encode(),
        )
        if write.exit_code != 0:
            raise GradingInfraError(
                f"grading_eval_script_write_failed:{write.stderr.strip()[-300:]}"
            )

    async def _run_eval(
        self, record: _ContainerRecord, spec: GradingEnvSpec, phase: GraderPhaseTiming
    ) -> tuple[str, float]:
        """跑官方 eval，返回 (合并日志文本, root 可信 setup 秒数)。

        legacy（无 grader profile，S1 冻结路径）：写入完整 eval_script 并以 root 执行，setup 秒数恒 0。

        grader profile（F2，D2-3 不变量的运行期半边）三步：
          1. root：`trusted_setup_script`（恢复 official test files、应用 official test_patch、git status/show/diff）
             ——候选代码此时尚未运行；
          2. root：`grader_protect_control_surface_script`——/testbed 交给候选用户，但 official test files
             root:root 0644、其全部祖先目录（含 /testbed）root:root 1777（sticky）：候选进程不能改写/删除/重命名/同路径重建它们；
          3. 候选执行用户：`candidate_test_script`（只跑测试命令，带官方 Start/End 标记）；脚本本身由 root 写在
             root 属主目录/sticky /tmp 里，候选进程无法在执行中改写。
        日志 = setup 输出 + 候选测试输出（形态与官方单脚本一致，parser 不变）。

        codex Wave3 §9.2 收口：第 1、2 步各有明确成功判据，任一不达标立即走 typed grading-infra
        （`GradingInfraError` → outcome=failed_to_grade、reward=None），**候选测试根本不启动**——
        既不会产出 reward=0 也不会产出 reward=1。判据见 `_check_trusted_setup_attest` 与
        `_check_control_surface_attest` 的注释。"""

        script_path = spec.eval_script_path
        profile = self.config.sandbox_profile
        if profile is None:
            await self._write_root_script(record, script_path, spec.eval_script, timeout=spec.apply_timeout_seconds)
            # 官方脚本自身 exit code 不作判据（测试失败常导致非零退出），
            # 死亡检测由 _exec_bash_checked 完成，结论一律交官方 parser。
            result = await self._exec_bash_checked(
                record,
                f"bash {script_path} 2>&1",
                phase="test",
                timeout=spec.test_timeout_seconds,
            )
            phase.add("grader_trusted_setup", 0.0)
            return (result.stdout if result.stdout else result.stderr), 0.0

        if spec.trusted_setup_script is None or spec.candidate_test_script is None:
            # 评分材料没有按 F2 拆分 = environment adapter 侧的系统性缺陷：同 profile 的每次评分都会撞上，
            # 记 failed_to_grade 只会把它洗成成员损耗——run-halt。
            raise SandboxProfileViolation(
                "grader_eval_split_required",
                f"{spec.task_id}: grader profile 要求 trusted_setup_script + candidate_test_script（拆分的 eval），"
                "评分材料只有单一 eval_script。",
            )
        from repoharness2.adapters.slime.sandbox_profile import (
            GRADER_TRUSTED_SETUP_ATTEST_PATH,
            grader_protect_control_surface_script,
            normalize_official_test_files,
            parse_key_value_output,
        )

        official_files = normalize_official_test_files(spec.hygiene.test_files)
        if not official_files:
            # 一个 official test 文件都没有：控制面无从保护，"本次要执行的 official test 全部是 root 只读
            # 普通文件"这条不变量退化成空真。与 grader_eval_split_required 同类——environment adapter 侧的
            # 系统性缺陷，不洗成成员损耗。
            raise SandboxProfileViolation(
                "grader_official_test_files_required",
                f"{spec.task_id}: grader profile 要求 hygiene.test_files 给出 official test 文件精确清单，当前为空。",
            )

        setup_started = time.monotonic()
        try:
            setup_path = f"{script_path}.trusted_setup"
            await self._write_root_script(
                record, setup_path, spec.trusted_setup_script, timeout=spec.apply_timeout_seconds
            )
            setup = await self._exec_bash_checked(
                record,
                f"bash {setup_path} 2>&1",
                phase="trusted_setup",
                timeout=spec.env_reset_timeout_seconds,
            )
            setup_log = setup.stdout if setup.stdout else setup.stderr
            record.eval_log_partial = setup_log
            # 自证不从 setup 的标准输出里认：那份输出含 `git diff <base>`，也就是候选自己写的代码，
            # 候选只要在源码里放一行 `RH2_SETUP_OK=1` 就能伪造。改读 root 写的自证文件——
            # 候选代码在这一步之前从未运行，没有任何写入口。
            attest = await self._exec_bash_checked(
                record,
                f"cat {GRADER_TRUSTED_SETUP_ATTEST_PATH} 2>/dev/null",
                phase="trusted_setup_attest",
                timeout=spec.apply_timeout_seconds,
            )
            setup_facts = parse_key_value_output(attest.stdout)
            record.trusted_setup = setup_facts
            reason = _check_trusted_setup_attest(setup.exit_code, setup_facts, len(official_files))
            if reason is not None:
                raise GradingInfraError(
                    f"grading_trusted_setup_failed:{reason}:rc={setup.exit_code}:"
                    f"{setup_facts.get('RH2_SETUP_ERROR', '')}"
                )

            protect = await self._exec_bash_checked(
                record,
                grader_protect_control_surface_script(profile, official_files),
                phase="control_surface_protect",
                timeout=spec.env_reset_timeout_seconds,
            )
            protect_facts = parse_key_value_output(protect.stdout)
            record.control_surface = protect_facts
            record.eval_log_partial = setup_log + protect.stdout
            reason = _check_control_surface_attest(
                protect.exit_code, protect_facts, setup_facts, len(official_files)
            )
            if reason is not None:
                raise GradingInfraError(
                    f"grading_control_surface_protect_failed:{reason}:rc={protect.exit_code}:"
                    f"{protect_facts.get('RH2_PROTECT_ERROR', '')}:{protect.stderr.strip()[-200:]}"
                )
            await self._write_root_script(
                record, script_path, spec.candidate_test_script, timeout=spec.apply_timeout_seconds
            )
        finally:
            # 成功与失败都记 grader_trusted_setup 段：被判据挡下的那次也要在计时/审计里看得见。
            trusted_setup_seconds = time.monotonic() - setup_started
            phase.add("grader_trusted_setup", trusted_setup_seconds)

        result = await self._exec_bash_checked(
            record,
            f"bash {script_path} 2>&1",
            phase="test",
            timeout=spec.test_timeout_seconds,
            user=str(profile.candidate_exec_uid),
            home=f"/home/{profile.candidate_exec_user}",
        )
        test_log = result.stdout if result.stdout else result.stderr
        return setup_log + test_log, trusted_setup_seconds

    def _parse_eval_log(self, spec: GradingEnvSpec, log_text: str) -> scoring.EvalVerdict:
        """官方 parser 解析 + manager 级加严（test_log_parse_failed 的两个判据）。"""

        try:
            verdict = spec.parse_log(log_text)
        except Exception as exc:  # noqa: BLE001 parser 崩溃是评分链路问题，不是模型负样本
            raise GradingInfraError(
                f"official_parser_exception:{type(exc).__name__}:{exc}",
                category="test_log_parse_failed",
            ) from exc
        if not verdict.apply_ok:
            # 我们的 git apply 已经成功，日志坏码（缺标记/RESET_FAILED/TESTS_ERROR/
            # TESTS_TIMEOUT）只能来自 eval 段自身 -> 评分链路问题（infra 族）。
            raise GradingInfraError(
                "official_bad_codes_after_successful_replay",
                category="test_log_parse_failed",
            )
        if verdict.num_parsed_tests == 0:
            # 标记齐全但一条测试都解析不出：官方 silent-success 语义此时会产出
            # "全部按通过计"的假结论（S1-4 实测确认），必须拦下判 infra 族。
            raise GradingInfraError(
                "eval_log_zero_parsed_tests",
                category="test_log_parse_failed",
            )
        return verdict

    async def _read_peak_memory_mb(self, record: _ContainerRecord) -> float:
        """读容器内存峰值（cgroup v2 memory.peak，回退 v1）。读不到记 0.0（不阻塞评分）。"""

        result = await self._exec_bash(
            record,
            "cat /sys/fs/cgroup/memory.peak 2>/dev/null"
            " || cat /sys/fs/cgroup/memory/memory.max_usage_in_bytes 2>/dev/null",
        )
        try:
            return round(int(result.stdout.strip()) / (1024 * 1024), 3)
        except (ValueError, TypeError):
            return 0.0

    def _persist_eval_log(
        self, nonce: str, trajectory_id: str, log_text: str
    ) -> ArtifactRef | None:
        """eval 原始日志落盘（runtime-private 证据），返回 opaque 引用。"""

        if self.config.eval_log_dir is None:
            return None
        log_dir = Path(self.config.eval_log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        ref_id = f"evallog_{_sanitize_for_name(trajectory_id)}_{nonce}"
        payload = log_text.encode()
        (log_dir / f"{ref_id}.eval.log").write_bytes(payload)
        import hashlib

        return ArtifactRef(
            ref_id=ref_id,
            sha256="sha256:" + hashlib.sha256(payload).hexdigest(),
            byte_size=len(payload),
        )

    # ------------------------------------------------------------------ 观测
    @property
    def container_records(self) -> tuple[_ContainerRecord, ...]:
        """容器记账快照（测试/审计用；返回副本防外部改账）。"""

        return tuple(self._records)
