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
"""

from __future__ import annotations

import hashlib
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
    source: Literal["swe_gym_lite"] = Field(description="数据源（首版封闭枚举；扩源升版本）。")
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
    grading_bundle_digest: Sha256Digest = Field(description="PrivateGradingBundleV2.digest()。")
    validation_bundle_digest: Sha256Digest = Field(description="ValidationOnlyBundle.digest()。")
    raw_archive_sha256: Sha256Digest = Field(description="来源 raw archive（T1a）的文件 digest。")
    image_manifest_keyed_sha256: Sha256Digest = Field(description="键控镜像清单（T1b）的文件 digest。")
    spec_vendor_json_sha256: Sha256Digest = Field(
        description="vendor 规范化 JSON 的 digest（由 spec_vendor_id 经固定注册表派生，"
        "builder 现算填入，不接受调用方自由值）。"
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


def build_environment_package(
    *,
    public,  # PublicTaskBundle（v1 类型，不在此文件 import 以免循环；duck-typed digest()）
    grading: PrivateGradingBundleV2,
    validation: ValidationOnlyBundle,
    source: str = TASK_SOURCE_SWE_GYM_LITE,
    raw_archive_sha256: str,
    image_manifest_keyed_sha256: str,
) -> EnvironmentPackageV1:
    """从三个已构造 bundle 组装包记录：digest 由本函数现算（防手填漂移），
    三方 instance_id / 镜像身份一致性在此断言。"""
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
    from repoharness2.envpack.spec_vendor import (  # 延迟 import 防环
        vendor_pin,
        verify_grading_eval_cmd,
    )
    # eval_cmd 强制互检（codex 轮次 13 严重 1：互检函数不进 canonical builder
    # 就只是注释——恶意 eval_cmd 曾能组出正式包）。构造期第一道防线；
    # T2-c resolved-package validator 与 T2-d 消费前互检是第二、三道。
    verify_grading_eval_cmd(grading)
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
        spec_vendor_json_sha256="sha256:" + vendor_pin(grading.spec_vendor_id).json_sha256,
    )
