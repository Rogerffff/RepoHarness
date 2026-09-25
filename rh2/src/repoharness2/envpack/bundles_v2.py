"""bundle v2 三分体系：grading 面与 golden 面分离（S2-1 T2-b）。

为什么有 v2（codex 轮次 4 阻塞 3，执行计划 §3.0）：v1 的
`PrivateGradingBundle` 强制内嵌 `golden_patch`，而 data_freeze 的
`strip_spec.yaml` 把 `patch` 归为 **validation_only**（金标解只许环境验证门
可见，模型补丁的评分路径不许见）。v1 已被 frozen_v1 冻结不能改，故新增
三分体系，v1 原样保留供 8 题基线：

```text
PublicTaskBundle（复用 v1，本文件不重定义）   模型可见面
PrivateGradingBundleV2（本文件）              评分面：test_patch / F2P / P2P /
                                              eval_cmd（vendor spec）——不含 golden
ValidationOnlyBundle（本文件）                验证门面：golden_patch（仅环境
                                              验证门沙箱可见）
EnvironmentPackageV1（本文件）                包记录：三 bundle 只以 digest 关联
                                              + 镜像身份 + 数据 provenance
```

身份与大小写定案（T1/T2-a 两次实测同一坑：docker 仓库名与 SWE-Gym spec 表
最终键都是小写）：**内部权威 repo 身份 = 数据集原始大小写 `owner/name`**；
`repo_key_lower` 是显式存储的小写投影（validator 钉死 == repo.lower()），
registry 拉取与 vendor spec 查表一律用投影，禁止隐式 .lower() 散落各处。

eval 形态（T2-a 推论）：xingyaoww 镜像预构建（依赖已装好），评分 =
容器内 `eval_cmd + 测试选择器` + 官方 parser——v2 不携带官方 eval_script
全文，只携带 vendor spec 的 `eval_cmd` 与 spec 来源 digest（可回溯到
`s2/vendor/swegym_constants_242429c1.py`）。

可见性纪律（与 v1 三道防线同源）：ValidationOnlyBundle 与
PrivateGradingBundleV2 都是 runtime-private；**golden 相关字段名与 v2
grading 字段集的交集必须为空**（单测钉死——防止将来有人把 golden 塞回
评分面）。EnvironmentPackageV1 只有 digest/身份，不含任何内容字段。

第二个来源（R2E 接线 2026-09-20，用户决定 DR1=A）：`r2e_gym_subset` 的评分面是
`PrivateGradingBundleR2E`——R2E 没有 test_patch 与 F2P/P2P 清单，判定原料是
"期望状态映射 + 固定入口 `run_tests.sh` + 镜像内隐藏测试"。它与 v2 并列、不改 v2；
public / validation / 包记录三个模型两个来源共用（包记录只把 `source` 枚举放宽）。
SWE 侧既有产物的序列化字节与摘要不因此变化（`tests/envpack/test_ingest_r2e_subset.py` 钉住）。
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from typing import Literal

from pydantic import Field, model_validator

from repoharness2.contracts._base import (
    GitSha,
    NonEmptyStr,
    SafeIdentifier,
    Sha256Digest,
    StrictModel,
    canonical_json_digest,
)

# golden 面字段名黑名单：v2 grading 面字段集与它的交集必须为空（单测钉死）。
GOLDEN_FIELD_NAMES: frozenset[str] = frozenset(
    {"patch", "golden_patch", "parsed_commit_content", "gold_patch"}
)

TASK_SOURCE_SWE_GYM_LITE = "swe_gym_lite"
TASK_SOURCE_R2E_GYM_SUBSET = "r2e_gym_subset"

# 来源枚举（封闭）：两侧视图、prepared 产物与包记录共用这一处定义。再加来源 = 改这里 +
# 给出对应的评分面模型与 ingest 入口，不存在"只放宽枚举"的半接入。
TaskSource = Literal["swe_gym_lite", "r2e_gym_subset"]


def task_id_for(source: str, instance_id: str) -> str:
    """source-qualified task_id（去重语义定案：任务身份 ≠ 环境身份，跨源
    duplicate cluster 以它为主键之一，见执行计划 T2 与 T1 报告）。"""
    return f"{source}::{instance_id}"


class PrivateGradingBundleV2(StrictModel):
    """评分面（v2）：**不含 golden**——金标解在 ValidationOnlyBundle。

    runtime-private：可进评分沙箱与审计存储，永不进 rollout 容器、public
    projection、模型上下文、SFT/export。
    """

    schema_id: Literal["rh2.private_grading_bundle.v2"] = Field(
        default="rh2.private_grading_bundle.v2", description="schema 判别字段。"
    )
    instance_id: SafeIdentifier = Field(description="任务 id（与 public/validation 配对键）。")
    repo: NonEmptyStr = Field(description='仓库身份权威（数据集原始大小写 "owner/name"）。')
    repo_key_lower: NonEmptyStr = Field(
        description="repo 的小写投影（registry / vendor spec 查表键；validator 钉死派生关系）。"
    )
    version: NonEmptyStr = Field(description="仓库版本号（vendor spec 与官方 parser 的配置键）。")
    base_commit: GitSha = Field(description="题目基线提交（血缘校验锚点）。")
    test_patch: NonEmptyStr = Field(description="官方 golden test patch（评分期 apply 引入判定测试）。")
    fail_to_pass: list[NonEmptyStr] = Field(
        min_length=1, description="FAIL_TO_PASS 清单（修复必须让这些测试由败转胜）。"
    )
    pass_to_pass: list[NonEmptyStr] = Field(
        default_factory=list, description="PASS_TO_PASS 清单（修复不得让这些测试回归）。"
    )
    eval_cmd: NonEmptyStr = Field(
        description="容器内测试命令（vendor spec 的 test_cmd 的**信息性副本**；"
        "预构建镜像内直接执行，不走官方 checkout/install eval_script。"
        "权威 = spec_vendor.derive_eval_cmd 派生值，消费方必须互检——"
        "本字段不是可独立信任的自由字符串）。"
    )
    python_version: NonEmptyStr | None = Field(
        default=None, description="vendor spec 声明的 python 版本（证据用；镜像内已就位）。"
    )
    spec_vendor_id: Literal["swegym_constants_242429c1"] = Field(
        description="eval_cmd 的来源 vendor 身份（封闭枚举，codex 轮次 12：artifact "
        "不携带可执行文件路径——路径与 digest 由 envpack.spec_vendor 固定注册表映射；"
        "eval_cmd 权威 = derive_eval_cmd(vendor_id, repo_key_lower, version)，"
        "本字段值消费时必须互检）。"
    )

    @model_validator(mode="after")
    def _check_case_projection(self) -> "PrivateGradingBundleV2":
        if self.repo_key_lower != self.repo.lower():
            raise ValueError(
                f"repo_key_lower={self.repo_key_lower!r} 不是 repo={self.repo!r} 的小写投影"
            )
        return self

    @model_validator(mode="after")
    def _check_test_set_invariants(self) -> "PrivateGradingBundleV2":
        """F2P/P2P 集合不变量进 schema（codex 轮次 15 一般 3）：矛盾评分事实
        （同测试既 F2P 又 P2P、或列表内重复）在模型层不可表示——不再依赖
        ingestion 构造时检查（那只是第一道防线，绕过构造器直接造 bundle
        也必须被拒）。"""
        if len(set(self.fail_to_pass)) != len(self.fail_to_pass):
            raise ValueError("fail_to_pass 含重复测试项")
        if len(set(self.pass_to_pass)) != len(self.pass_to_pass):
            raise ValueError("pass_to_pass 含重复测试项")
        overlap = set(self.fail_to_pass) & set(self.pass_to_pass)
        if overlap:
            raise ValueError(f"fail_to_pass 与 pass_to_pass 交集非空: {sorted(overlap)[:3]}")
        return self

    def digest(self) -> str:
        return canonical_json_digest(self.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# R2E-Gym-Subset 评分面（R2E 接线 R-a）
# ---------------------------------------------------------------------------

R2E_EXPECTED_STATUSES: frozenset[str] = frozenset({"PASSED", "FAILED", "ERROR"})
"""来源 parser 只产出这三种状态（SKIPPED / XFAIL 行被来源规则丢弃），期望映射里出现别的值即数据面变动。"""

# 隐藏测试相对路径：只许安全字符的相对路径——树摘要要在 Python 与容器内 `sha256sum` 两侧算出同值，
# 文件名含空格 / 反斜杠 / 换行时 `sha256sum` 会转义输出，两侧口径就不再相同。
_R2E_HIDDEN_PATH_RE = re.compile(r"^[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*$")


def r2e_hidden_tests_tree_digest(files: Iterable[tuple[str, str]]) -> str:
    """隐藏测试树摘要。`files` = (相对 `r2e_tests/` 的路径, 文件内容 sha256（`sha256:` 前缀）)。

    定义：每个文件一行 `"<64 位 hex>  ./<相对路径>\\n"`，按 `./<相对路径>` 的字节序排序后整体取 sha256。
    这正是容器内下面这条命令的输出，可信 setup 用它在 grader 里复算比对（R-c）：

        cd /testbed/r2e_tests && find . -type f -not -path '*/__pycache__/*' -print0 \\
            | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum

    例：两个文件 `__init__.py`（空文件）与 `test_1.py` → 两行，`./__init__.py` 在前（`_` 的字节值小于小写字母）。
    """

    lines = []
    for rel, digest in sorted(files, key=lambda item: ("./" + item[0]).encode("utf-8")):
        lines.append(f"{digest.removeprefix('sha256:')}  ./{rel}\n")
    return "sha256:" + hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def _r2e_parse_expected_output_json(text: str) -> dict[str, str]:
    """把来源的 `expected_output_json` 原文解析成期望映射；重复键 / 非对象 / 空 / 未知状态一律拒绝。"""

    def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
        keys = [k for k, _ in pairs]
        if len(set(keys)) != len(keys):
            raise ValueError("expected_output_json 含重复键（json.loads 会静默只留最后一个）")
        return dict(pairs)

    parsed = json.loads(text, object_pairs_hook=_no_duplicate_keys)
    if not isinstance(parsed, dict) or not parsed:
        raise ValueError("expected_output_json 不是非空 JSON 对象")
    for key, status in parsed.items():
        if not key:
            raise ValueError("expected_output_json 含空键")
        if status not in R2E_EXPECTED_STATUSES:
            raise ValueError(f"expected_output_json 键 {key!r} 的状态 {status!r} 不在 {sorted(R2E_EXPECTED_STATUSES)}")
    return dict(parsed)


class R2EHiddenTestFile(StrictModel):
    """镜像内 `/r2e_tests` 下的一个隐藏测试文件（路径相对 `r2e_tests/`）。"""

    path: NonEmptyStr = Field(description="相对 r2e_tests/ 的路径（只许安全字符，见 `_R2E_HIDDEN_PATH_RE`）。")
    sha256: Sha256Digest = Field(description="文件内容 sha256。")

    @model_validator(mode="after")
    def _check_path(self) -> "R2EHiddenTestFile":
        if not _R2E_HIDDEN_PATH_RE.match(self.path) or ".." in self.path.split("/"):
            raise ValueError(f"隐藏测试路径不安全: {self.path!r}")
        if "__pycache__" in self.path.split("/"):
            raise ValueError(f"隐藏测试清单不收字节码缓存: {self.path!r}")
        return self


class PrivateGradingBundleR2E(StrictModel):
    """评分面（R2E-Gym-Subset）：期望状态映射 + 固定入口原文 + 隐藏测试清单。**不含 gold**。

    runtime-private（与 v2 同纪律）：可进评分沙箱与审计存储，永不进 rollout 容器、public
    projection、模型上下文、SFT/export。判定语义是"观测状态映射 == 期望状态映射"——期望值可以是
    FAILED / ERROR（例：pandas `19c5eea5` 的期望里本来就有 ERROR 键），不能套 SWE 的"失败即不过"。
    """

    schema_id: Literal["rh2.private_grading_bundle.r2e.v1"] = Field(
        default="rh2.private_grading_bundle.r2e.v1", description="schema 判别字段（评分视图按它分派来源）。"
    )
    instance_id: SafeIdentifier = Field(description='任务 id = "<repo>__<source_commit_hash>"（validator 钉死）。')
    repo: NonEmptyStr = Field(description='来源 `repo_name` 原文（R2E 只给仓库短名，如 "coveragepy"，不补 owner）。')
    repo_key_lower: NonEmptyStr = Field(description="repo 的小写投影（与 v2 同形，validator 钉死）。")
    base_commit: GitSha = Field(
        description="镜像内 /testbed 的 HEAD（修复提交的父提交）。来源行只给符号形式 `<commit>^`，"
        "40 位值取自镜像实测事实表。"
    )
    source_commit_hash: GitSha = Field(description="来源行 `commit_hash`（修复提交；镜像 tag 与 instance_id 的组成部分）。")
    expected_output_json: NonEmptyStr = Field(
        description="来源 `expected_output_json` **原文**（键不预归一化、不重排；pillow 六题的键自带 ANSI 序列）。"
        "消费方用 `expected_map()` 取映射，归一化在判定时两侧对称地做。"
    )
    expected_output_json_sha256: Sha256Digest = Field(description="上述原文的 sha256（validator 重算比对）。")
    run_tests_sh: NonEmptyStr = Field(
        description="镜像内 `/testbed/run_tests.sh` 的逐字原文——评分前由可信 setup 按它重写入口，"
        "agent 对该文件的改动在此被覆盖；不改写成我们自己的 pytest 命令。"
    )
    run_tests_sh_sha256: Sha256Digest = Field(description="run_tests_sh 原文的 sha256（validator 重算比对）。")
    hidden_test_files: list[R2EHiddenTestFile] = Field(
        min_length=1, description="镜像内 `/r2e_tests` 的文件清单（评分前恢复到 /testbed/r2e_tests）。"
    )
    hidden_tests_tree_sha256: Sha256Digest = Field(
        description="`r2e_hidden_tests_tree_digest(hidden_test_files)`（validator 重算；grader 内用同一定义复算）。"
    )
    parser_id: Literal["r2e_prime_pytest_v1"] = Field(
        default="r2e_prime_pytest_v1", description="日志 parser 身份（`envpack.r2e_parsers`）。"
    )
    normalization_version: Literal["prime_decolor_v1"] = Field(
        default="prime_decolor_v1", description="键归一化口径：固定上游实现（两侧同规则去色、截 ' - '），只有这一种。"
    )
    rule_source_id: Literal["prime_envs_c4d04dfe"] = Field(
        default="prime_envs_c4d04dfe",
        description="parser / 归一化 / gold 重建规则的**代码**来源身份（prime-envs@c4d04dfe…）。"
        "数据 revision 不能替代代码版本，所以与 spec_vendor_id 分开记。",
    )
    source_revision: GitSha = Field(description="数据集 revision（HF `R2E-Gym/R2E-Gym-Subset` 的 40 位提交号）。")
    spec_vendor_id: Literal["r2e_gym_subset_e8b9fcbc"] = Field(
        default="r2e_gym_subset_e8b9fcbc", description="**数据**来源身份（数据集 + revision 前缀，封闭枚举）。"
    )
    material_revisions: list[SafeIdentifier] = Field(
        default_factory=list,
        description="已应用的材料修订编号（`s2_r2e/revisions/material_revisions_v1.json`，每条都经用户批准）。"
        "空 = 来源原件；非空时 `expected_output_json` 或 `hidden_test_files` 是修订后的内容，"
        "来源原件的摘要记在修订文件里（例：`r2e-mr-001` 把 coveragepy `016af5f6` 的一个期望键改为 PASSED）。",
    )

    @model_validator(mode="after")
    def _check_identity(self) -> "PrivateGradingBundleR2E":
        if self.repo_key_lower != self.repo.lower():
            raise ValueError(f"repo_key_lower={self.repo_key_lower!r} 不是 repo={self.repo!r} 的小写投影")
        if self.instance_id != r2e_instance_id_for(self.repo, self.source_commit_hash):
            raise ValueError(
                f"instance_id={self.instance_id!r} 与 repo/source_commit_hash 不一致"
                f"（期望 {r2e_instance_id_for(self.repo, self.source_commit_hash)!r}）"
            )
        if not self.source_revision.startswith(self.spec_vendor_id.rsplit("_", 1)[-1]):
            raise ValueError(
                f"source_revision={self.source_revision[:12]}… 与 spec_vendor_id={self.spec_vendor_id!r} 的 revision 前缀不符"
            )
        return self

    @model_validator(mode="after")
    def _check_self_attesting_digests(self) -> "PrivateGradingBundleR2E":
        def _sha(text: str) -> str:
            return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

        if _sha(self.expected_output_json) != self.expected_output_json_sha256:
            raise ValueError("expected_output_json_sha256 与原文不符")
        _r2e_parse_expected_output_json(self.expected_output_json)  # 结构与状态值合法性
        if _sha(self.run_tests_sh) != self.run_tests_sh_sha256:
            raise ValueError("run_tests_sh_sha256 与原文不符")
        paths = [f.path for f in self.hidden_test_files]
        if len(set(paths)) != len(paths):
            raise ValueError("hidden_test_files 含重复路径")
        recomputed = r2e_hidden_tests_tree_digest((f.path, f.sha256) for f in self.hidden_test_files)
        if recomputed != self.hidden_tests_tree_sha256:
            raise ValueError("hidden_tests_tree_sha256 与按文件清单重算的树摘要不符")
        if self.material_revisions != sorted(set(self.material_revisions)):
            raise ValueError("material_revisions 必须去重且按编号排序（同一份修订集合只有一种写法）")
        return self

    def expected_map(self) -> dict[str, str]:
        """期望状态映射（来源原文解析；键未归一化）。"""

        return _r2e_parse_expected_output_json(self.expected_output_json)

    def digest(self) -> str:
        return canonical_json_digest(self.model_dump(mode="json"))


def r2e_instance_id_for(repo: str, source_commit_hash: str) -> str:
    """R2E 的源内任务 id：`<repo>__<commit_hash 40 位>`（例 `aiohttp__1c1c0ea3…`，满足 SafeIdentifier）。"""

    return f"{repo}__{source_commit_hash}"


# 评分面联合：评分视图与包记录的构造入口按 `schema_id` 分派，不做鸭子类型猜测。
PrivateGradingBundleAny = PrivateGradingBundleV2 | PrivateGradingBundleR2E


class ValidationOnlyBundle(StrictModel):
    """验证门面：金标解。**只有环境验证门沙箱可见**（strip_spec validation_only
    归属的契约化）——rollout 与模型补丁的评分路径都不许见。"""

    schema_id: Literal["rh2.validation_only_bundle.v1"] = Field(
        default="rh2.validation_only_bundle.v1", description="schema 判别字段。"
    )
    instance_id: SafeIdentifier = Field(description="任务 id（与 public/grading 配对键）。")
    golden_patch: NonEmptyStr = Field(description="官方正解 patch（golden 门 / mutation probe 的原料）。")
    golden_patch_sha256: Sha256Digest = Field(
        description="golden_patch 文本的 sha256 自证字段（validator 重算比对）。"
    )

    @model_validator(mode="after")
    def _check_patch_digest(self) -> "ValidationOnlyBundle":
        actual = "sha256:" + hashlib.sha256(self.golden_patch.encode("utf-8")).hexdigest()
        if actual != self.golden_patch_sha256:
            raise ValueError("golden_patch_sha256 与 golden_patch 内容不符")
        return self

    def digest(self) -> str:
        return canonical_json_digest(self.model_dump(mode="json"))


class EnvironmentPackageV1(StrictModel):
    """环境包记录：三 bundle 以 digest 关联 + 镜像稳定身份 + 数据 provenance。

    只有 digest 与身份字段、零内容字段——它可以进任何账本与报告而不构成
    泄漏面；按 digest 取回具体 bundle 时再受各自可见性纪律约束。
    """

    schema_id: Literal["rh2.environment_package.v1"] = Field(
        default="rh2.environment_package.v1", description="schema 判别字段。"
    )
    task_id: NonEmptyStr = Field(description='source-qualified 任务主键（"<source>::<instance_id>"）。')
    source: TaskSource = Field(
        description="数据源（封闭枚举）。2026-09-20 用户决定 DR1=A 增 r2e_gym_subset；枚举放宽不改变"
        "已有 swe_gym_lite 包记录的序列化字节与摘要。"
    )
    instance_id: SafeIdentifier = Field(description="源内任务 id。")
    repo: NonEmptyStr = Field(description="仓库身份权威（原始大小写）。")
    repo_key_lower: NonEmptyStr = Field(description="小写投影（validator 钉死）。")
    base_commit: GitSha = Field(
        description="环境身份的一半（repo+base_commit = 环境身份；同环境不同任务合法共存，"
        "见 T1 报告 moto/mypy 两对实测）。"
    )
    image: NonEmptyStr = Field(description="镜像引用（含 tag；身份以 digest 为准）。")
    image_manifest_digest: Sha256Digest = Field(description="镜像 manifest digest（运行期按此拉取比对）。")
    public_bundle_digest: Sha256Digest = Field(description="PublicTaskBundle.digest()。")
    grading_bundle_digest: Sha256Digest = Field(
        description="评分面 bundle 的 digest()（swe_gym_lite = PrivateGradingBundleV2；r2e_gym_subset = PrivateGradingBundleR2E）。"
    )
    validation_bundle_digest: Sha256Digest = Field(description="ValidationOnlyBundle.digest()。")
    raw_archive_sha256: Sha256Digest = Field(
        description="来源 raw archive 的文件 digest（swe：T1a 全量行；r2e：48 行来源原始行文件）。"
    )
    image_manifest_keyed_sha256: Sha256Digest = Field(
        description="镜像身份表的文件 digest（swe：T1b 键控镜像清单；r2e：镜像实测事实表）。"
    )
    spec_vendor_json_sha256: Sha256Digest = Field(
        description="来源规则文件的 digest，builder 经固定注册表现算填入，不接受调用方自由值"
        "（swe：vendor 规范化 JSON；r2e：固定版本的上游规则源文件，见 envpack.r2e_parsers）。"
    )

    @model_validator(mode="after")
    def _check_identity(self) -> "EnvironmentPackageV1":
        if self.task_id != task_id_for(self.source, self.instance_id):
            raise ValueError(f"task_id={self.task_id!r} 与 source::instance_id 不一致")
        if self.repo_key_lower != self.repo.lower():
            raise ValueError("repo_key_lower 不是 repo 的小写投影")
        return self

    def digest(self) -> str:
        return canonical_json_digest(self.model_dump(mode="json"))


def build_private_grading_bundle(
    *,
    instance_id: str,
    repo: str,
    version: str,
    base_commit: str,
    test_patch: str,
    fail_to_pass: list[str],
    pass_to_pass: list[str],
    spec_vendor_id: str = "swegym_constants_242429c1",
) -> PrivateGradingBundleV2:
    """grading bundle 的 canonical 构造器：`eval_cmd`/`python_version` 由
    vendor 注册表**派生**（codex 轮次 13：ingestion 不自己填 eval_cmd，
    自由字符串没有进入路径）。"""
    from repoharness2.envpack.spec_vendor import derive_eval_cmd, lookup_spec

    repo_key_lower = repo.lower()
    spec = lookup_spec(spec_vendor_id, repo_key_lower, version)
    return PrivateGradingBundleV2(
        instance_id=instance_id,
        repo=repo,
        repo_key_lower=repo_key_lower,
        version=version,
        base_commit=base_commit,
        test_patch=test_patch,
        fail_to_pass=fail_to_pass,
        pass_to_pass=pass_to_pass,
        eval_cmd=derive_eval_cmd(spec_vendor_id, repo_key_lower, version),
        python_version=(str(spec["python"]) if spec.get("python") is not None else None),
        spec_vendor_id=spec_vendor_id,  # type: ignore[arg-type]
    )


def expected_source_for_grading(grading: PrivateGradingBundleAny) -> str:
    """评分面模型 → 它唯一合法的来源。包记录、视图与 ingest 都用这一处映射互检：
    "来源写 swe、评分面却是 R2E 形状"的错配对象没有构造路径。"""

    if isinstance(grading, PrivateGradingBundleR2E):
        return TASK_SOURCE_R2E_GYM_SUBSET
    if isinstance(grading, PrivateGradingBundleV2):
        return TASK_SOURCE_SWE_GYM_LITE
    raise TypeError(f"未知评分面类型: {type(grading).__name__}")


def build_environment_package(
    *,
    public,  # PublicTaskBundle（v1 类型，不在此文件 import 以免循环；duck-typed digest()）
    grading: PrivateGradingBundleAny,
    validation: ValidationOnlyBundle,
    source: str = TASK_SOURCE_SWE_GYM_LITE,
    raw_archive_sha256: str,
    image_manifest_keyed_sha256: str,
) -> EnvironmentPackageV1:
    """从三个已构造 bundle 组装包记录：digest 由本函数现算（防手填漂移），
    三方 instance_id / 镜像身份一致性在此断言。"""
    if source != expected_source_for_grading(grading):
        raise ValueError(
            f"source={source!r} 与评分面 {type(grading).__name__} 不匹配"
            f"（该评分面只属于 {expected_source_for_grading(grading)!r}）"
        )
    if not (public.instance_id == grading.instance_id == validation.instance_id):
        raise ValueError(
            f"三 bundle instance_id 不一致: {public.instance_id} / "
            f"{grading.instance_id} / {validation.instance_id}"
        )
    # 任务身份交叉核对（codex 轮次 12 严重 1：不核对则可组出"模型解 A 仓、
    # 评分器评 B 仓"的包——public 与 grading 的 repo/base_commit 必须逐字相等）。
    if public.repo != grading.repo:
        raise ValueError(f"public.repo={public.repo!r} 与 grading.repo={grading.repo!r} 不一致")
    if public.base_commit != grading.base_commit:
        raise ValueError(
            f"public.base_commit={public.base_commit} 与 grading.base_commit={grading.base_commit} 不一致"
        )
    if isinstance(grading, PrivateGradingBundleR2E):
        # R2E 没有 eval_cmd（入口是 bundle 内逐字携带的 run_tests.sh，摘要自证）；
        # 规则文件 digest 取固定版本的上游规则源（parser / 归一化 / gold 重建同出一处）。
        from repoharness2.envpack.r2e_parsers import r2e_rule_source_pin  # 延迟 import 防环

        rule_source_sha256 = r2e_rule_source_pin(grading.rule_source_id).sha256
    else:
        from repoharness2.envpack.spec_vendor import (  # 延迟 import 防环
            vendor_pin,
            verify_grading_eval_cmd,
        )
        # eval_cmd 强制互检（codex 轮次 13 严重 1：互检函数不进 canonical builder
        # 就只是注释——恶意 eval_cmd 曾能组出正式包）。构造期第一道防线；
        # T2-c resolved-package validator 与 T2-d 消费前互检是第二、三道。
        verify_grading_eval_cmd(grading)
        rule_source_sha256 = vendor_pin(grading.spec_vendor_id).json_sha256
    return EnvironmentPackageV1(
        task_id=task_id_for(source, grading.instance_id),
        source=source,  # type: ignore[arg-type] —— Literal 校验由模型执行
        instance_id=grading.instance_id,
        repo=grading.repo,
        repo_key_lower=grading.repo_key_lower,
        base_commit=grading.base_commit,
        image=public.image,
        image_manifest_digest=public.image_manifest_digest,
        public_bundle_digest=public.digest(),
        grading_bundle_digest=grading.digest(),
        validation_bundle_digest=validation.digest(),
        raw_archive_sha256=raw_archive_sha256,
        image_manifest_keyed_sha256=image_manifest_keyed_sha256,
        spec_vendor_json_sha256="sha256:" + rule_source_sha256,
    )
