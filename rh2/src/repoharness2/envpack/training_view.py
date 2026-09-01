"""W2a training-only typed view：trusted controller + 两侧剥离视图（Wave1）。

背景（06 计划 §3 W2a 行，两条代码事实实现批已逐行复核）：

1. 完整 loader `load_trusted_ingest_outputs`（ingest_swegym_lite.py）**无条件**
   反序列化全部四面——`load_ingest_outputs` 里 `IngestResult(...)` 一次性构造
   packages / public / grading / **validation（含 golden_patch）** 四个列表。
   所以 rollout actor 不得直调它：谁调它，谁的进程里就有金标解。
2. `EnvironmentPackageV1` 只有身份 + digest 字段（无 prompt/test_patch/
   eval_cmd）——它可以随便携带，但单靠它评不了分；完整 v2 评分链归 T2-d/W3a。

本模块的所有权架构（D0-3 已拍板边界）：

```text
load_trusted_ingest_outputs（host 侧 trusted 入口，四面全量）
        │
        ▼
TrustedTaskController（本模块；host 进程内，不是新服务）
  ├─ 构建时重跑 package↔public↔grading↔validation 四面关系检查
  │  （运行输入一致性检查，不是授权门）
  ├─ RolloutTaskView   → 发往 rollout actor/sandbox/模型侧的唯一形态：
  │                      public task + 身份 + environment_package_digest
  ├─ HostGradingView   → 仅 host 侧 grading 控制面：内嵌密封
  │                      PrivateGradingBundleV2 + 同一 digest 锚
  └─ ValidationOnlyBundle / golden_patch：构建后**直接丢弃，不存任何属性**
     ——验证门（T2-d/W3a）是另一个 host 侧消费方，自己调 trusted 入口
```

可见性纪律（与 bundles.py 三道防线同源，正反测试见 tests/test_w2a_*.py）：

- `RolloutTaskView` 字段名与 `PRIVATE_ONLY_FIELD_NAMES ∪ GOLDEN_FIELD_NAMES`
  交集为空（模块导入即断言）；整树 model_dump 过 forbidden marker 扫描
  （validator 内建，脏视图构造即炸，不存在"构造完再扫"的窗口）。
- `HostGradingView` 不含任何 golden 字段（导入断言 + extra="forbid"）。
- `environment_package_digest = EnvironmentPackageV1.digest()` 在两侧视图
  都携带，且 `grading_view()` 要求调用方**交回**该 digest 才放行——身份锚
  不许只在入口核一次后丢失（后续 baseline/grading/eligibility join 复用）。

T1 决策（对 RolloutTaskSpec 的携带形态）：rollout 侧**只携带 opaque digest
锚，不内嵌密封 grading bundle**。理由：RolloutTaskView 会被序列化进 actor
进程/日志/prompt 组装路径，内嵌密封对象离"一次 model_dump 泄漏"只差一个
bug；digest 锚保留 join 一致性而零内容。密封内嵌只发生在 HostGradingView
——它从不跨进程发往 rollout 方向。
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from repoharness2.contracts import scan_for_forbidden_markers
from repoharness2.contracts._base import (
    NonEmptyStr,
    SafeIdentifier,
    Sha256Digest,
    StrictModel,
)
from repoharness2.envpack.bundles import PRIVATE_ONLY_FIELD_NAMES, PublicTaskBundle
from repoharness2.envpack.bundles_v2 import (
    GOLDEN_FIELD_NAMES,
    EnvironmentPackageV1,
    PrivateGradingBundleV2,
    ValidationOnlyBundle,
    task_id_for,
)
from repoharness2.envpack.ingest_swegym_lite import (
    IngestResult,
    load_trusted_ingest_outputs,
    verify_bundle_relations_non_authoritative,
    verify_package_relations,
)


class TrustedViewError(ValueError):
    """typed view 消费链 fail-closed 异常（unknown task / 漏包 / digest 不符 /
    关系检查失败）。"""


class RolloutTaskView(StrictModel):
    """发往 rollout actor / sandbox / 模型侧的**唯一**任务形态。

    内容 = public task bundle + 身份 + environment_package_digest。刻意不含：
    grading bundle（含 opaque 内嵌都不许）、validation bundle、任何私有字段名。
    digest 锚随视图走，rollout 结果回到 host 侧做 grading/baseline/eligibility
    join 时交回同一 digest（见 `TrustedTaskController.grading_view`）。
    """

    schema_id: Literal["rh2.rollout_task_view.v1"] = Field(
        default="rh2.rollout_task_view.v1", description="schema 判别字段。"
    )
    task_id: NonEmptyStr = Field(description='source-qualified 任务主键（"<source>::<instance_id>"）。')
    source: Literal["swe_gym_lite"] = Field(description="数据源（与 EnvironmentPackageV1 同枚举）。")
    instance_id: SafeIdentifier = Field(description="源内任务 id。")
    environment_package_digest: Sha256Digest = Field(
        description="EnvironmentPackageV1.digest()——贯穿 rollout→grading→"
        "baseline/eligibility join 的一致性锚，不只在入口核一次。"
    )
    public_bundle_digest: Sha256Digest = Field(
        description="PublicTaskBundle.digest()——来源是 EnvironmentPackageV1 记录的"
        "绑定值；validator 重算比对。二轮复核补：只靠泄漏 marker 扫描发现不了"
        "合法内容漂移（如追加一个普通工具），内容摘要才能钉住模型可见面。"
    )
    public: PublicTaskBundle = Field(description="模型可见面全量（题面/镜像/工具/公开提示）。")

    @model_validator(mode="after")
    def _check_identity_and_leaks(self) -> "RolloutTaskView":
        if self.task_id != task_id_for(self.source, self.instance_id):
            raise ValueError(f"task_id={self.task_id!r} 与 source::instance_id 不一致")
        if self.instance_id != self.public.instance_id:
            raise ValueError(
                f"视图 instance_id={self.instance_id} 与 public bundle "
                f"{self.public.instance_id} 不一致"
            )
        if self.public_bundle_digest != self.public.digest():
            raise ValueError(
                f"{self.instance_id}: public_bundle_digest 与 public bundle 重算 "
                "digest 不符——模型可见面内容漂移（构造后被改/与包记录不一致）"
            )
        # 视图级泄漏扫描（validator 内建）：即使 public bundle 单独扫过，
        # 视图整树再扫一次——防止将来加字段时绕开 bundle 级防线。
        hits = scan_for_forbidden_markers(self.model_dump(mode="json"))
        if hits:
            detail = "; ".join(f"{h.path} 命中 {h.marker}（{h.kind}）" for h in hits)
            raise ValueError(f"{self.instance_id}: rollout 视图泄漏扫描命中 {len(hits)} 处：{detail}")
        return self

    def revalidated(self) -> "RolloutTaskView":
        """消费时刻重验（Wave1 复核 F3）：`frozen=True` 只挡字段重赋值，
        嵌套 list（如 `public.allowed_tools`）构造后仍可变——validator 只在
        构造时跑一次，"通过泄漏扫描"因此不是终身属性。**真正序列化进
        prompt/actor payload 或进入评分 join 之前必须调用本方法**：round-trip
        重跑全部 validator（身份一致性 + 泄漏扫描 + public 内容 digest 重算），
        构造后被污染的副本——无论是塞 marker 还是合法内容漂移——在此被拒。"""

        return type(self).model_validate(self.model_dump(mode="python"))


class HostGradingView(StrictModel):
    """仅 host 侧 grading 控制面消费的评分视图（**永不**发往 rollout actor/
    sandbox/模型/SFT/export）。

    T1 决策落点：`PrivateGradingBundleV2` 在这里**内嵌密封**（host 进程内对象，
    不跨进程序列化）；rollout 方向只存在 opaque digest 锚。仍不含 golden——
    ValidationOnlyBundle 连本视图都进不来（正式 grader 也不许见金标解）。
    """

    schema_id: Literal["rh2.host_grading_view.v1"] = Field(
        default="rh2.host_grading_view.v1", description="schema 判别字段。"
    )
    task_id: NonEmptyStr = Field(description="source-qualified 任务主键（与 rollout 视图同锚）。")
    source: Literal["swe_gym_lite"] = Field(description="数据源。")
    instance_id: SafeIdentifier = Field(description="源内任务 id。")
    environment_package_digest: Sha256Digest = Field(
        description="与 RolloutTaskView 同一 digest 锚（join 一致性）。"
    )
    grading_bundle_digest: Sha256Digest = Field(
        description="PrivateGradingBundleV2.digest()（validator 重算比对，自证字段）。"
    )
    grading: PrivateGradingBundleV2 = Field(
        description="密封评分面（test_patch/F2P/P2P/eval_cmd；不含 golden）。"
    )

    @model_validator(mode="after")
    def _check_identity_and_digest(self) -> "HostGradingView":
        if self.task_id != task_id_for(self.source, self.instance_id):
            raise ValueError(f"task_id={self.task_id!r} 与 source::instance_id 不一致")
        if self.instance_id != self.grading.instance_id:
            raise ValueError(
                f"视图 instance_id={self.instance_id} 与 grading bundle "
                f"{self.grading.instance_id} 不一致"
            )
        if self.grading_bundle_digest != self.grading.digest():
            raise ValueError("grading_bundle_digest 与内嵌 grading bundle 重算 digest 不符")
        return self

    def revalidated(self) -> "HostGradingView":
        """消费时刻重验（Wave1 复核 F3，与 RolloutTaskView.revalidated 同义务）：
        评分材料在真正进入 grader/构造 grading spec 之前必须过这里——嵌套
        list（如 fail_to_pass）被构造后篡改时，digest 重算比对在此拒绝。"""

        return type(self).model_validate(self.model_dump(mode="python"))


# ---------------------------------------------------------------------------
# 导入期静态断言（第二道防线；单测再钉一次）
# ---------------------------------------------------------------------------

_MODEL_SIDE_FORBIDDEN_FIELD_NAMES = PRIVATE_ONLY_FIELD_NAMES | GOLDEN_FIELD_NAMES
assert not set(RolloutTaskView.model_fields) & _MODEL_SIDE_FORBIDDEN_FIELD_NAMES, (
    "RolloutTaskView 字段名撞上私有/golden 名单——W2a 剥离被破坏"
)
assert "grading" not in RolloutTaskView.model_fields and "validation" not in RolloutTaskView.model_fields, (
    "RolloutTaskView 不许携带 grading/validation 字段（连 opaque 内嵌都不许）"
)
assert not set(HostGradingView.model_fields) & GOLDEN_FIELD_NAMES, (
    "HostGradingView 字段名撞上 golden 名单——正式评分面不许见金标解"
)
assert not set(PrivateGradingBundleV2.model_fields) & GOLDEN_FIELD_NAMES, (
    "PrivateGradingBundleV2 出现 golden 字段——v2 三分体系被破坏"
)


# 构造令牌：只有本模块的 `_build` 能拿到；raw-map 直接构造被拒（二轮复核 F4）。
_CONSTRUCTION_TOKEN = object()


class TrustedTaskController:
    """host 侧 trusted controller：调完整 loader → 四面关系检查 → 剥离视图。

    不是新服务、不是权限平台——就是 host 进程内的一层构造 + 查表，把
    "谁能拿到什么"从约定变成类型形状：

    - rollout 侧只经 `rollout_view()` 取 `RolloutTaskView`；
    - host grader 只经 `grading_view()` 取 `HostGradingView`，且必须交回
      rollout 视图携带的 `environment_package_digest`（digest 贯穿的强制点）；
    - `ValidationOnlyBundle` 构建后即丢弃，controller 上**不存在**任何持有
      golden 内容的属性（tests/test_w2a_trusted_views.py 做对象图可达性测试）。

    正式入口 = `from_repo_root`（走 `load_trusted_ingest_outputs` 全链验证 +
    controller 内逐包 strict 重验）。合成夹具单测用显式命名的
    `build_for_tests_from_ingest_result`（非权威关系检查，产物不进正式链，
    与 `write_ingest_outputs_for_tests` 同一命名纪律）。**raw-map 直接构造
    没有入口**（构造令牌），入库对象经 `revalidated()` 重验并与调用方引用
    隔离；取数口返回深拷贝副本，消费方在真正序列化/评分前再 `revalidated()`。
    """

    def __init__(self, *, rollout_views: dict[str, RolloutTaskView],
                 grading_views: dict[str, HostGradingView],
                 _token: object = None) -> None:
        # Wave1 二轮复核 F4：raw-map 构造改为内部入口——只有 `_build`
        # 持有 `_CONSTRUCTION_TOKEN`。正式代码只许 `from_repo_root`，测试只
        # 许 `build_for_tests_from_ingest_result`；两条路径都经过四面关系
        # 检查（package 记录把内容 digest 绑到身份上），"外层身份 A、内部
        # 评分材料 B"的重新封装对象没有入口。
        if _token is not _CONSTRUCTION_TOKEN:
            raise TrustedViewError(
                "TrustedTaskController 不接受直接构造——正式代码用 from_repo_root，"
                "测试用 build_for_tests_from_ingest_result（四面关系检查是入口的一部分）"
            )
        # 第二道防线（F4 一轮修复保留）：两侧配对校验——key 集合一致、
        # map key == view.task_id、两侧身份与 environment digest 逐任务一致。
        # 这只挡结构性错配；把 reward 绑定到 host 原始分派的 attempt
        # （authoritative join）归 W1b 第一集成切片。
        if set(rollout_views) != set(grading_views):
            only_r = sorted(set(rollout_views) - set(grading_views))[:3]
            only_g = sorted(set(grading_views) - set(rollout_views))[:3]
            raise TrustedViewError(
                f"controller 两侧 task 集合不一致（rollout 独有 {only_r}，"
                f"grading 独有 {only_g}）——拒绝构造"
            )
        for key, rv in rollout_views.items():
            gv = grading_views[key]
            if rv.task_id != key or gv.task_id != key:
                raise TrustedViewError(
                    f"map key {key!r} 与视图 task_id（rollout={rv.task_id!r} / "
                    f"grading={gv.task_id!r}）不一致——拒绝构造"
                )
            if (rv.source, rv.instance_id) != (gv.source, gv.instance_id):
                raise TrustedViewError(
                    f"{key}: 两侧身份不一致（rollout={rv.source}::{rv.instance_id} / "
                    f"grading={gv.source}::{gv.instance_id}）——拒绝构造"
                )
            if rv.environment_package_digest != gv.environment_package_digest:
                raise TrustedViewError(
                    f"{key}: 两侧 environment_package_digest 不一致——拒绝构造"
                )
        # 入库前重验 + 隔离（二轮复核 F4）：`revalidated()` 走 model_validate
        # 产出全新对象树——调用方保留的任何嵌套引用都不再指向库内对象，
        # 且入库对象在此刻通过了全部 validator。
        self._rollout_views = {k: v.revalidated() for k, v in rollout_views.items()}
        self._grading_views = {k: v.revalidated() for k, v in grading_views.items()}

    # ------------------------------------------------------------------ 构建

    @classmethod
    def from_repo_root(cls, repo_root: Path) -> "TrustedTaskController":
        """正式入口：完整 trusted loader（四面全量+全链验证）→ 剥离视图。

        loader 内部已逐包跑过 `verify_package_relations`；controller 不依赖
        这一实现细节，用 loader 返回的可信 pins/image_store 再逐包重验一次
        （消费期重验义务，与 ingest 模块"轮次 12"纪律一致）。
        """
        trusted = load_trusted_ingest_outputs(repo_root)

        def _strict_verify(pkg, public, grading, validation) -> None:
            verify_package_relations(pkg, public, grading, validation,
                                     pins=trusted.pins, image_store=trusted.image_store)

        return cls._build(trusted.result, _strict_verify)

    @classmethod
    def build_for_tests_from_ingest_result(cls, result: IngestResult) -> "TrustedTaskController":
        """**test-only**：合成 IngestResult → controller（非权威关系检查：
        不核 T1 pins、不核镜像清单）。正式消费链一律走 `from_repo_root`。"""
        return cls._build(result, verify_bundle_relations_non_authoritative)

    @classmethod
    def _build(cls, result: IngestResult, verify) -> "TrustedTaskController":
        def _index(models, face: str) -> dict[str, object]:
            out: dict[str, object] = {}
            for m in models:
                if m.instance_id in out:
                    raise TrustedViewError(f"{face} 面重复 instance_id: {m.instance_id}")
                out[m.instance_id] = m
            return out

        publics = _index(result.public_bundles, "public")
        gradings = _index(result.grading_bundles, "grading")
        validations = _index(result.validation_bundles, "validation")
        pkg_ids = {p.instance_id for p in result.packages}
        if len(pkg_ids) != len(result.packages):
            raise TrustedViewError("package 面重复 instance_id")
        for face, idx in (("public", publics), ("grading", gradings), ("validation", validations)):
            if set(idx) != pkg_ids:
                missing = sorted(pkg_ids - set(idx))[:3]
                extra = sorted(set(idx) - pkg_ids)[:3]
                raise TrustedViewError(
                    f"{face} 面与 package 面 id 集合不一致（漏包 fail-closed）："
                    f"缺 {missing}，多 {extra}"
                )

        rollout_views: dict[str, RolloutTaskView] = {}
        grading_views: dict[str, HostGradingView] = {}
        for pkg in result.packages:
            public = publics[pkg.instance_id]
            grading = gradings[pkg.instance_id]
            validation = validations[pkg.instance_id]
            try:
                # 四面关系检查：运行输入一致性检查（不是授权门）。任何
                # digest/身份错位在这里 fail-closed，坏包不产出任何视图。
                verify(pkg, public, grading, validation)
            except (TrustedViewError, ValueError) as exc:
                raise TrustedViewError(
                    f"{pkg.instance_id}: 四面关系检查失败，拒绝构造视图：{exc}"
                ) from exc
            epd = pkg.digest()
            rollout_views[pkg.task_id] = RolloutTaskView(
                task_id=pkg.task_id,
                source=pkg.source,
                instance_id=pkg.instance_id,
                environment_package_digest=epd,
                public_bundle_digest=pkg.public_bundle_digest,  # 包记录的绑定值，validator 重算比对
                public=public,
            )
            grading_views[pkg.task_id] = HostGradingView(
                task_id=pkg.task_id,
                source=pkg.source,
                instance_id=pkg.instance_id,
                environment_package_digest=epd,
                grading_bundle_digest=pkg.grading_bundle_digest,
                grading=grading,
            )
            # ValidationOnlyBundle 到此为止：参与了关系检查，然后被丢弃。
            del validation
        return cls(rollout_views=rollout_views, grading_views=grading_views,
                   _token=_CONSTRUCTION_TOKEN)

    # ------------------------------------------------------------------ 消费

    def task_ids(self) -> tuple[str, ...]:
        """全部 source-qualified task_id（确定性排序）。"""
        return tuple(sorted(self._rollout_views))

    def rollout_view(self, task_id: str) -> RolloutTaskView:
        """rollout 侧唯一取数口。unknown task → fail-closed。

        返回**深拷贝隔离副本**（Wave1 复核 F3）：一个消费者对副本嵌套
        容器的修改不会污染 controller 权威份或其它消费者；副本自身的
        篡改由消费时刻的 `revalidated()` 拒绝。"""
        view = self._rollout_views.get(task_id)
        if view is None:
            raise TrustedViewError(f"unknown task_id（rollout 视图不存在）: {task_id!r}")
        return view.model_copy(deep=True)

    def grading_view(self, task_id: str, *,
                     environment_package_digest: str) -> HostGradingView:
        """host grader 唯一取数口。

        调用方必须交回 rollout 链路携带的 `environment_package_digest`——
        digest 在入口核过之后不许丢失，回到评分面时再核一次（mismatch =
        评错环境的前兆，fail-closed）。
        """
        view = self._grading_views.get(task_id)
        if view is None:
            raise TrustedViewError(f"unknown task_id（grading 视图不存在）: {task_id!r}")
        if environment_package_digest != view.environment_package_digest:
            raise TrustedViewError(
                f"{task_id}: environment_package_digest 不符（交回 "
                f"{environment_package_digest[:23]}…，期望 "
                f"{view.environment_package_digest[:23]}…）——拒绝评分 join"
            )
        # 深拷贝隔离（F3）：评分消费方拿副本，进入 grader 前过 revalidated()。
        return view.model_copy(deep=True)

    def verify_environment_package_digest(self, task_id: str, digest: str) -> None:
        """给 baseline/eligibility 等 join 消费方的锚核对口（不返回内容）。"""
        view = self._rollout_views.get(task_id)
        if view is None:
            raise TrustedViewError(f"unknown task_id（无法核对 digest）: {task_id!r}")
        if digest != view.environment_package_digest:
            raise TrustedViewError(
                f"{task_id}: environment_package_digest 不符——join 拒绝"
            )


# 显式导出面：ValidationOnlyBundle 只为关系检查 import，不在导出面。
__all__ = [
    "HostGradingView",
    "RolloutTaskView",
    "TrustedTaskController",
    "TrustedViewError",
]

# 防御性收尾：本模块任何公开对象都不该把 ValidationOnlyBundle 再导出去。
assert ValidationOnlyBundle.__name__ not in __all__
assert EnvironmentPackageV1.__name__ not in __all__  # 包记录经 digest 锚消费，不经本模块转手
