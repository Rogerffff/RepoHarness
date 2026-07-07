"""public task bundle / private grading bundle 拆分（A6，验收级）。

SWE 任务数据天然混着两类信息：

- **模型可以看的**：题面（problem_statement）、repo/base_commit、镜像与 digest、
  允许工具、公开环境提示。这些进 `PublicTaskBundle`，是 rollout 容器、public
  projection、SFT/export 唯一允许携带的任务数据。
- **只有评分器可以看的**：golden patch、golden test_patch、FAIL_TO_PASS/PASS_TO_PASS
  清单、官方 parser 配置（repo+version 选 parser）、官方 eval 脚本。这些进
  `PrivateGradingBundle`，**永不进 rollout 容器、public projection、SFT/export**
  （挂载纪律由 S1-6 sandbox 握手契约的 WorkspaceHandle 执行）。

三道防线（fail-closed，缺一不可）：

1. **schema 白名单**：两个 bundle 都是 `extra="forbid"` 严格模型——想往 public
   bundle 塞 `test_patch` 字段，构造时就 ValidationError，根本走不到扫描。
2. **字段名静态互斥**：`PublicTaskBundle` 的字段名集合与私有字段名单
   （含 contracts 的 forbidden marker）交集必须为空，单测钉死。
3. **内容泄漏扫描**：`split_frozen_entry` 构造完 public bundle 后，整棵
   model_dump 树过 `contracts.scan_for_forbidden_markers`（key + value 都查，
   紧凑匹配语义见 contracts/constants.py），命中即抛 `BundleLeakError`。
   实测冻结 8 题的题面 + 公开提示 0 误报（见 s1/envpack_freeze_v1.md）。

digest 约定：`bundle.digest()` = 对 `model_dump(mode="json")` 的规范化 JSON
（key 排序 + 紧凑分隔符）做 sha256，带 `sha256:` 前缀——与 contracts 的
`canonical_json_digest` 同一实现，inspector 可独立重算。两个 bundle 各自出
digest，一起写进 `data/frozen_v1.json`（见 freeze.py）。
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from repoharness2.contracts import scan_for_forbidden_markers
from repoharness2.contracts._base import (
    GitSha,
    NonEmptyStr,
    SafeIdentifier,
    Sha256Digest,
    StrictModel,
    canonical_json_digest,
)

# ---------------------------------------------------------------------------
# 冻结数据文件（题目数据随库走，S1-2 起由 envpack 而非 taskset 拥有）
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent / "data"
TASKS_FILE = DATA_DIR / "swe_smoke_tasks.json"
"""S0-7 冻结的完整题目数据（含私有评分材料，runtime-private，不随任何导出走）。"""
FROZEN_V1_FILE = DATA_DIR / "frozen_v1.json"
"""8 题冻结记录（frozen_v1：instance_id + 镜像 digest + 题面 sha256 + 两 bundle digest）。"""

# 模型可见的解题指引（公开提示，进 public bundle；文本与 S0-7 SYSTEM_PROMPT 逐字一致，
# 保证薄壳改造后 8 题回归的模型输入不变）。
PUBLIC_SYSTEM_HINTS = (
    "You are a software engineer fixing a real GitHub issue in the repository "
    "checked out at /testbed (your bash tool already runs there).\n"
    "- The project's Python environment is a pre-activated conda env named "
    "`testbed`: `python`, `pip` and the repo's test tools already point at it.\n"
    "- Explore the code, find the root cause, and edit NON-TEST source files to fix "
    "the issue.\n"
    "- Do NOT modify test files: grading resets the test files to their original "
    "state before running the official test suite, so test edits never count.\n"
    "- You may run tests to verify your fix, but keep runs narrow (a single test "
    "file or module) to save time.\n"
    "- When you are confident the fix is complete, reply with a short summary and "
    "stop calling tools."
)

# 冻结 8 题的允许工具面（default harness 的 bash+edit）。
DEFAULT_ALLOWED_TOOLS: tuple[str, ...] = ("bash", "edit")


class BundleLeakError(ValueError):
    """public bundle 泄漏扫描命中（marker 出现在 key 或 value 里），拒绝出厂。"""


class PublicTaskBundle(StrictModel):
    """模型可见的任务面（A6 名单：题面/repo/base_commit/镜像 digest/允许工具/公开提示）。

    刻意**不**包含的字段（都在 PrivateGradingBundle）：golden patch、test_patch、
    F2P/P2P 清单、eval 脚本、官方测试命令、version（version 是
    MAP_REPO_TO_PARSER/MAP_REPO_VERSION_TO_SPECS 的 parser 配置键，按 fail-closed
    原则归评分侧；模型解题不需要它）。
    """

    schema_id: Literal["rh2.public_task_bundle.v1"] = Field(
        default="rh2.public_task_bundle.v1", description="schema 判别字段。"
    )
    instance_id: SafeIdentifier = Field(description="SWE-bench instance id（任务主键）。")
    repo: NonEmptyStr = Field(description='GitHub 仓库名（如 "django/django"，出现在题面定位头里）。')
    base_commit: GitSha = Field(description="题目基线提交（/testbed 血缘校验的锚点，模型可见）。")
    image: NonEmptyStr = Field(description="官方预构建镜像引用（rollout 容器用它启动）。")
    image_manifest_digest: Sha256Digest = Field(
        description="镜像 manifest digest（题单冻结时逐题核对 Docker Hub 记下，运行期比对防漂移）。"
    )
    workdir: NonEmptyStr = Field(
        default="/testbed", description="agent 工作目录（公开环境事实）。"
    )
    allowed_tools: list[SafeIdentifier] = Field(
        default_factory=lambda: list(DEFAULT_ALLOWED_TOOLS),
        min_length=1,
        description="允许的工具面（冻结 8 题 = default harness 的 bash+edit）。",
    )
    problem_statement: NonEmptyStr = Field(description="题面原文（模型可见的唯一任务描述）。")
    problem_statement_sha256: Sha256Digest = Field(
        description="题面原文的 sha256（自证字段，校验器重算比对；frozen_v1 记录同一值）。"
    )
    public_hints: NonEmptyStr = Field(
        default=PUBLIC_SYSTEM_HINTS,
        description="公开解题指引（system prompt 正文，逐字冻结）。",
    )

    @model_validator(mode="after")
    def _check_statement_digest(self) -> "PublicTaskBundle":
        recomputed = sha256_of_text(self.problem_statement)
        if recomputed != self.problem_statement_sha256:
            raise ValueError(
                "problem_statement_sha256 自证失败："
                f"声明 {self.problem_statement_sha256}，重算 {recomputed}。"
            )
        return self

    def digest(self) -> str:
        """public bundle 的规范化内容 digest（frozen_v1 记录项之一）。"""

        return canonical_json_digest(self.model_dump(mode="json"))


class PrivateGradingBundle(StrictModel):
    """评分器专用的私有面（test_patch/F2P/P2P/官方 parser 配置/golden 相关）。

    本对象是 runtime-private 资产：它可以进评分沙箱与审计存储，
    但**永不**进 rollout 容器、public projection、模型上下文、SFT/export。
    """

    schema_id: Literal["rh2.private_grading_bundle.v1"] = Field(
        default="rh2.private_grading_bundle.v1", description="schema 判别字段。"
    )
    instance_id: SafeIdentifier = Field(description="SWE-bench instance id（与 public 侧配对键）。")
    repo: NonEmptyStr = Field(description="仓库名（官方 MAP_REPO_TO_PARSER 的 parser 选择键之一）。")
    version: NonEmptyStr = Field(
        description="仓库版本号（官方 MAP_REPO_VERSION_TO_SPECS 的 parser/test_cmd 配置键）。"
    )
    base_commit: GitSha = Field(description="题目基线提交（eval 脚本 checkout 测试文件的基线）。")
    golden_patch: NonEmptyStr = Field(
        description="官方正解 patch（golden 相关信息；评分本身不用它，但它属于私有面，绝不许外泄）。"
    )
    test_patch: NonEmptyStr = Field(description="官方 golden test patch（eval 脚本 apply 它引入判定测试）。")
    fail_to_pass: list[NonEmptyStr] = Field(
        min_length=1, description="FAIL_TO_PASS 清单（修复必须让这些测试由败转胜）。"
    )
    pass_to_pass: list[NonEmptyStr] = Field(
        default_factory=list, description="PASS_TO_PASS 清单（修复不得让这些测试回归）。"
    )
    eval_script: NonEmptyStr = Field(
        description="官方 make_test_spec 生成的 eval 脚本全文（S0-7 冻结，评分动作直接执行它）。"
    )
    test_cmd: NonEmptyStr = Field(description="官方测试命令（证据/复核用，eval_script 内已含）。")
    environment_setup_commit: GitSha | None = Field(
        default=None, description="官方环境构建提交（数据集原始字段，存证用）。"
    )

    def digest(self) -> str:
        """private bundle 的规范化内容 digest（frozen_v1 记录项之一）。"""

        return canonical_json_digest(self.model_dump(mode="json"))


# public 字段名与私有面字段名的静态互斥表（第二道防线；单测与本断言双保险）。
PRIVATE_ONLY_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "golden_patch",
        "test_patch",
        "fail_to_pass",
        "pass_to_pass",
        "eval_script",
        "test_cmd",
        "version",
        "environment_setup_commit",
    }
)
assert not (
    set(PublicTaskBundle.model_fields) & PRIVATE_ONLY_FIELD_NAMES
), "PublicTaskBundle 字段名撞上私有面名单——A6 拆分被破坏"


class BundlePair(StrictModel):
    """同一题的 public/private 两半（构造时校验配对键一致）。"""

    public: PublicTaskBundle
    private: PrivateGradingBundle

    @model_validator(mode="after")
    def _check_pairing(self) -> "BundlePair":
        if self.public.instance_id != self.private.instance_id:
            raise ValueError(
                "bundle 配对键不一致："
                f"public={self.public.instance_id}, private={self.private.instance_id}。"
            )
        if self.public.base_commit != self.private.base_commit:
            raise ValueError(
                f"{self.public.instance_id}: public/private 的 base_commit 不一致。"
            )
        return self

    @property
    def instance_id(self) -> str:
        return self.public.instance_id


def sha256_of_text(text: str) -> str:
    """题面等纯文本的 sha256（utf-8 字节流，带 sha256: 前缀）。"""

    import hashlib

    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def scan_public_bundle(public: PublicTaskBundle) -> None:
    """第三道防线：public bundle 整树过 forbidden marker 扫描，命中即拒绝。"""

    hits = scan_for_forbidden_markers(public.model_dump(mode="json"))
    if hits:
        detail = "; ".join(f"{hit.path} 命中 {hit.marker}（{hit.kind}）" for hit in hits)
        raise BundleLeakError(
            f"{public.instance_id}: public task bundle 泄漏扫描命中 {len(hits)} 处：{detail}"
        )


def split_frozen_entry(entry: Mapping) -> BundlePair:
    """把一条冻结题目数据（swe_smoke_tasks.json 的 tasks[i]）拆成 public/private 两半。

    public 侧构造完成后立刻过泄漏扫描（scan_public_bundle），命中即抛
    BundleLeakError——脏 bundle 不允许离开本函数。
    """

    inst = entry["instance"]
    problem_statement = inst["problem_statement"]
    public = PublicTaskBundle(
        instance_id=inst["instance_id"],
        repo=inst["repo"],
        base_commit=inst["base_commit"],
        image=entry["image"],
        image_manifest_digest=entry["image_manifest_digest"],
        problem_statement=problem_statement,
        problem_statement_sha256=sha256_of_text(problem_statement),
    )
    scan_public_bundle(public)
    private = PrivateGradingBundle(
        instance_id=inst["instance_id"],
        repo=inst["repo"],
        version=inst["version"],
        base_commit=inst["base_commit"],
        golden_patch=inst["patch"],
        test_patch=inst["test_patch"],
        fail_to_pass=list(entry["fail_to_pass"]),
        pass_to_pass=list(entry["pass_to_pass"]),
        eval_script=entry["eval_script"],
        test_cmd=entry["test_cmd"],
        environment_setup_commit=inst.get("environment_setup_commit") or None,
    )
    return BundlePair(public=public, private=private)


def render_user_prompt(public: PublicTaskBundle) -> str:
    """从 public bundle 渲染用户 prompt（文本形态与 S0-7 逐字一致，回归锚点）。"""

    return (
        f"Fix the following issue from the `{public.repo}` repository "
        f"(checked out at {public.workdir}, commit {public.base_commit[:12]}):\n\n"
        f"{public.problem_statement}"
    )


# ---------------------------------------------------------------------------
# 冻结数据加载（库层数据入口；verifiers 绑定与 S1-4/S1-6 都从这里取数）
# ---------------------------------------------------------------------------


def load_task_entries(tasks_file: Path | str = TASKS_FILE) -> dict[str, Mapping]:
    """读取冻结题目数据，返回 instance_id -> 冻结条目（保持文件内 idx 顺序）。"""

    payload = json.loads(Path(tasks_file).read_text())
    entries = {t["instance"]["instance_id"]: t for t in payload["tasks"]}
    if len(entries) != len(payload["tasks"]):
        raise ValueError(f"{tasks_file}: 存在重复 instance_id，冻结数据不可信")
    return entries


def load_bundle_pairs(
    tasks_file: Path | str = TASKS_FILE,
    subset: list[str] | None = None,
    frozen_file: Path | str | None = FROZEN_V1_FILE,
) -> list[BundlePair]:
    """加载并拆分冻结题单，默认对照 frozen_v1 记录做防漂移校验。

    - subset：只取这些 instance_id（顺序按 subset 给定）；未知 id 直接报错。
    - frozen_file：非 None 时逐题重算 digest 与 frozen_v1 记录比对
      （题面 sha256 / 镜像 digest / 两 bundle digest 任一不符即抛错，fail-closed）。
      传 None 显式跳过（仅供 freeze.py 自举生成记录时使用）。
    """

    entries = load_task_entries(tasks_file)
    wanted = subset or list(entries)
    unknown = [iid for iid in wanted if iid not in entries]
    if unknown:
        raise ValueError(f"subset 中的 instance 不在冻结题单里: {unknown}")
    pairs = [split_frozen_entry(entries[iid]) for iid in wanted]
    if frozen_file is not None:
        # 惰性 import 避免模块级循环（freeze.py 也 import 本模块）。
        from repoharness2.envpack.freeze import verify_pairs_against_frozen

        verify_pairs_against_frozen(pairs, frozen_file)
    return pairs
