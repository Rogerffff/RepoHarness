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
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Literal, Protocol

from repoharness2.contracts import (
    ArtifactRef,
    CleanupPolicy,
    GradingReport,
    GradingTimingRecord,
    PatchHygieneResult,
    SandboxLease,
)
from repoharness2.envpack import bundles, materialize, scoring

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
    stdout, stderr = await proc.communicate(input=input_bytes)
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
EXPORT_PATCH_SCRIPT = (
    "git add -N . 1>&2 && git -c core.fileMode=false diff --binary HEAD"
)


async def export_cleaned_patch(workspace: WorkspaceRunner, rules: HygieneRules) -> CleanedPatch:
    """A7 条 1：从 agent workspace 导出 final patch 并按规则清洗。"""

    result = await workspace.run_bash(EXPORT_PATCH_SCRIPT)
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


class GradingInfraError(RuntimeError):
    """评分链路自身故障（infra 族）。category 决定 GradingReport 的归因取值。"""

    def __init__(
        self,
        detail: str,
        *,
        category: Literal["infra_failure", "test_log_parse_failed"] = "infra_failure",
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.category = category


@dataclass
class _ContainerRecord:
    """per-容器记账条目（P1：TTL GC 与孤儿判定的数据底座）。"""

    name: str
    trajectory_id: str
    created_epoch: float
    created_monotonic: float
    removed: bool = False


def _sanitize_for_name(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "-", text).strip("-.")
    return (cleaned or "traj")[:24]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


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
        self.leases: list[SandboxLease] = []  # 评分容器租约 evidence（P9 deny_all 由 schema 锁死）

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
        workspace: WorkspaceRunner,
        spec: GradingEnvSpec,
        queue_wait_seconds: float = 0.0,
        queue_depth_at_enqueue: int | None = None,
        backpressure_triggered: bool = False,
    ) -> GradingReport:
        """评分一条轨迹：导出→清洗→fresh 容器 clean checkout→重放→测试→官方解析→报告。

        queue_* 参数由 GradingQueue 注入（F5 排队等待计时与反压事实）；
        直接调用（不经队列）时保持默认值即可。
        """

        total_start = time.monotonic()
        nonce = uuid.uuid4().hex[:8]
        timing_parts = {"image_pull": 0.0, "env_reset": 0.0, "prep": 0.0, "test": 0.0}
        record: _ContainerRecord | None = None
        cleaned: CleanedPatch | None = None
        replay_started = False
        eval_log_text: str | None = None
        peak_memory_mb = 0.0

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

        def _hygiene() -> PatchHygieneResult | None:
            # 没走到重放阶段的 infra 报告不附 hygiene（附了反而暗示做过 clean 重放）。
            if cleaned is None or not replay_started:
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
            # 阶段 1+2（prep 前半）：导出 + hygiene 清洗（A7 条 1/3/4）
            prep_start = time.monotonic()
            try:
                cleaned = await export_cleaned_patch(workspace, spec.hygiene)
            except WorkspaceExportError as exc:
                raise GradingInfraError(f"workspace_patch_export_failed: {exc}") from exc
            timing_parts["prep"] += time.monotonic() - prep_start

            # 阶段 3 前置：镜像就绪（P10 第一档，预拉取命中记 0.0）
            timing_parts["image_pull"] = await self._ensure_image(spec.image)

            # 阶段 3：fresh 容器 + 镜像 digest 比对 + clean checkout + 血缘核验（A7 条 2）
            reset_start = time.monotonic()
            record = await self._start_container(trajectory_id, spec, nonce)
            await self._verify_image_digest(record, spec)
            await self._clean_checkout(record, spec)
            timing_parts["env_reset"] = time.monotonic() - reset_start

            # 阶段 4（prep 后半）：写入并重放 cleaned patch
            prep_start = time.monotonic()
            replay_started = True
            apply_ok = await self._replay_patch(record, spec, cleaned)
            timing_parts["prep"] += time.monotonic() - prep_start
            if not apply_ok:
                # A7 条 6 三分之一：cleaned patch 在 clean checkout 上 apply 失败 = 模型负样本
                peak_memory_mb = await self._read_peak_memory_mb(record)
                return GradingReport(
                    **common,
                    outcome="unresolved",
                    failure_category="patch_apply_failed",
                    reward=0.0,
                    patch_hygiene=_hygiene(),
                    timings=_timings(),
                    graded_at_utc=_now_utc(),
                )

            # 阶段 5：跑官方 eval（合并单流 2>&1，S1-2 提醒的日志形态）
            test_start = time.monotonic()
            eval_log_text = await self._run_eval(record, spec)
            timing_parts["test"] = time.monotonic() - test_start
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
                fields = {
                    **fields,
                    "outcome": "unresolved",
                    "failure_category": "tests_failed",
                    "reward": 0.0,
                }
            return GradingReport(
                **common,
                **fields,
                patch_hygiene=hygiene,
                eval_log_ref=self._persist_eval_log(nonce, trajectory_id, eval_log_text),
                timings=_timings(),
                graded_at_utc=_now_utc(),
            )
        except GradingInfraError as exc:
            # infra 族收口（P4）：本分支不存在 reward 取值——想给 infra 报告塞
            # reward 连参数都没有，schema 校验器是第二道锁。
            if record is not None:
                peak_memory_mb = await self._read_peak_memory_mb(record)
            return GradingReport(
                **common,
                outcome="failed_to_grade",
                failure_category=exc.category,
                reward=None,
                infra_failure_detail=exc.detail,
                patch_hygiene=_hygiene(),
                eval_log_ref=(
                    self._persist_eval_log(nonce, trajectory_id, eval_log_text)
                    if eval_log_text is not None
                    else None
                ),
                timings=_timings(),
                graded_at_utc=_now_utc(),
            )
        finally:
            if record is not None:
                await self._remove_container(record)

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
        async with lock:
            if image in self._images_ready:
                return 0.0
            inspect = await self._docker("image", "inspect", image)
            if inspect.exit_code == 0:
                self._images_ready.add(image)
                return 0.0
            pull_start = time.monotonic()
            pull = await self._docker("pull", image)
            if pull.exit_code != 0:
                raise GradingInfraError(
                    f"grading_image_pull_failed:{image}:{pull.stderr.strip()[-300:]}"
                )
            self._images_ready.add(image)
            return time.monotonic() - pull_start

    # ------------------------------------------------------------------ 内部：容器生命周期
    async def _start_container(
        self, trajectory_id: str, spec: GradingEnvSpec, nonce: str
    ) -> _ContainerRecord:
        prefix = self.config.label_prefix
        name = f"{self.config.name_prefix}-{_sanitize_for_name(trajectory_id)}-{nonce}"
        created_epoch = time.time()

        # 租约先行：网络策略唯一来源是 SandboxLease（purpose=grading 在 schema 层
        # 锁死 deny_all，P9），docker 参数由租约推导——想开网先得改契约。
        image_id = await self._docker("image", "inspect", "-f", "{{.Id}}", spec.image)
        lease = SandboxLease(
            lease_id=f"lease_{name}",
            container_id=name,
            image_digest=image_id.stdout.strip(),
            purpose="grading",
            created_by="grading_manager",
            network_policy_owner="grading_manager",
            network_policy="deny_all",
            permission_policy_owner="grading_manager",
            run_as_user="root",
            cleanup=CleanupPolicy(
                owner="grading_manager",
                steps=["remove_container", "release_lease"],
                on_cleanup_failure="record_runtime_finding_and_infra_failure",
                timeout_seconds=self.config.cleanup_timeout_seconds,
            ),
            created_at_utc=_now_utc(),
        )
        network_args = {"deny_all": ("--network", "none")}[lease.network_policy]

        args: list[str] = [
            "run",
            "--detach",
            *network_args,
            "--label",
            f"{prefix}.owner={self.run_id}",
            "--label",
            f"{prefix}.trajectory={trajectory_id}",
            "--label",
            f"{prefix}.created_at_epoch={int(created_epoch)}",
        ]
        if spec.checkout_mode == "clone_from_readonly_snapshot":
            # P6：共享快照永远只读挂载，评分只在容器私有的 /testbed 副本上进行。
            args += ["--volume", f"{spec.snapshot_host_path}:{spec.snapshot_mount_path}:ro"]
        args += ["--name", name, spec.image, "sleep", "infinity"]

        run = await self._docker(*args)
        if run.exit_code != 0:
            raise GradingInfraError(
                f"grading_container_start_failed:{run.stderr.strip()[-300:]}"
            )
        self.leases.append(lease)
        record = _ContainerRecord(
            name=name,
            trajectory_id=trajectory_id,
            created_epoch=created_epoch,
            created_monotonic=time.monotonic(),
        )
        self._records.append(record)
        return record

    async def _remove_container(self, record: _ContainerRecord) -> None:
        if record.removed:
            return
        rm = await self._docker("rm", "-f", record.name)
        if rm.exit_code == 0:
            record.removed = True
        else:
            # Q8：清理失败不许静默——留痕供 S1-6 收口为 runtime finding。
            self.cleanup_failures.append(
                f"container_rm_failed:{record.name}:{rm.stderr.strip()[-200:]}"
            )

    async def _container_running(self, record: _ContainerRecord) -> bool:
        inspect = await self._docker("inspect", "-f", "{{.State.Running}}", record.name)
        return inspect.exit_code == 0 and inspect.stdout.strip() == "true"

    async def _exec_bash(
        self, record: _ContainerRecord, script: str, *, input_bytes: bytes | None = None
    ) -> ExecResult:
        if input_bytes is not None:
            return await self._docker(
                "exec", "-i", record.name, "bash", "-c", script, input_bytes=input_bytes
            )
        return await self._docker("exec", record.name, "bash", "-c", script)

    async def _exec_bash_checked(
        self,
        record: _ContainerRecord,
        script: str,
        *,
        phase: str,
        timeout: float,
        input_bytes: bytes | None = None,
    ) -> ExecResult:
        """带分段超时（P3）与容器死亡检测（P4）的 exec：
        超时 -> infra；命令失败且容器已死 -> infra（killed）；其余交调用方定夺。"""

        try:
            result = await asyncio.wait_for(
                self._exec_bash(record, script, input_bytes=input_bytes), timeout=timeout
            )
        except (TimeoutError, asyncio.TimeoutError):
            raise GradingInfraError(
                f"grading_{phase}_timeout_after_{int(timeout)}s"
            ) from None
        if result.exit_code != 0 and not await self._container_running(record):
            raise GradingInfraError(f"grading_container_killed_during_{phase}")
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
    async def _clean_checkout(self, record: _ContainerRecord, spec: GradingEnvSpec) -> None:
        """A7 条 2：准备 clean checkout 并用 S1-2 血缘判据核验。"""

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

    async def _run_eval(self, record: _ContainerRecord, spec: GradingEnvSpec) -> str:
        """写入官方 eval 脚本并以合并单流（2>&1）执行，返回原始日志文本。"""

        script_path = spec.eval_script_path
        write = await self._exec_bash_checked(
            record,
            f"mkdir -p $(dirname {script_path}) && cat > {script_path}",
            phase="eval_write",
            timeout=spec.apply_timeout_seconds,
            input_bytes=spec.eval_script.encode(),
        )
        if write.exit_code != 0:
            raise GradingInfraError(
                f"grading_eval_script_write_failed:{write.stderr.strip()[-300:]}"
            )
        # 官方脚本自身 exit code 不作判据（测试失败常导致非零退出），
        # 死亡检测由 _exec_bash_checked 完成，结论一律交官方 parser。
        result = await self._exec_bash_checked(
            record,
            f"bash {script_path} 2>&1",
            phase="test",
            timeout=spec.test_timeout_seconds,
        )
        return result.stdout if result.stdout else result.stderr

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
