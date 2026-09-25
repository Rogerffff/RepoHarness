"""环境覆盖表：逐题派生镜像的引用方式（R2E 接线 R-d，2026-09-20；用户决定 DR3=A）。

为什么需要：R2E-Gym 的来源镜像在沙箱身份下跑不动（解释器在 0700 的 `/root` 下，48/48）、修复提交是 HEAD 的直接
子提交（答案可达）、隐藏测试 `/r2e_tests` 默认可读。环境侧为每题构建一张**派生镜像**（搬迁解释器、清理 git
历史、隐藏测试搬到 root 私有目录），用这张表告诉评分链"这道题实际用哪张镜像"。

边界：

- 环境包（`EnvironmentPackageV1`）记录的仍是**来源镜像**的引用与 manifest digest；覆盖表不改它，只在其上叠加。
  派生镜像没有 registry manifest digest，身份是本机 image ID——不能把来源镜像的 digest 当成派生镜像的身份。
- 表的数据由环境侧产出；本模块只定义形状与加载校验。消费方（replay driver）负责：核对
  `base_image_*` 与环境包一致、本机 `inspect` 到的 ID 与表内一致，任何不符 = 该题不评分。
- ~~正式 actor 的 rollout 租约目前只认"registry 镜像 + manifest digest"，让它使用覆盖表属于 D4=B，不在本片。~~
  2026-09-25（E09 + D4=B）：正式 actor 的任务面（`adapters/slime/prepared_task_face.py`）也按覆盖表用派生镜像，
  两侧容器按 image ID 启动；R2E 题缺覆盖条目即拒。覆盖表经 `RH2_IMAGE_OVERLAYS_PATH` / `RH2_IMAGE_OVERLAYS_SHA256` 给出。
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from repoharness2.contracts._base import NonEmptyStr, Sha256Digest, StrictModel

ENVIRONMENT_OVERLAY_SCHEMA_ID = "rh2.environment_overlay.v1"

ImageId = Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]


@dataclass(frozen=True)
class RevisionEnvRequirement:
    """只在特定环境下成立的材料修订所需的环境。

    `recipe_component` 是 `recipe_id` 里必须出现的环境步骤片段；它只说明用了哪个安装步骤，不代表装了什么依赖。
    真正的约束是 `approved_recipe_sha256`：批准并用真实 grader 复验过的配方内容身份（`scripts/build_r2e_derived.py`
    的 `composite_recipe_digest`，覆盖 recipe 脚本、环境步骤脚本与逐个 wheel 的 sha256）。依赖内容、wheel 或脚本
    任一变化都会得到新摘要，必须重新复验后再登记（Codex 09-25 复核 R1）。"""

    recipe_component: str
    approved_recipe_sha256: frozenset[str]
    approved_pins: tuple[str, ...]


# 只在特定环境下成立的材料修订（Codex 批次三复核 F1 与 09-25 复核 R1）。例：r2e-mr-020 把 orange3 9b5494e2 的两个
# LogisticRegression 期望键改为 PASSED，只在 SciPy 1.5.4 的环境里成立；旧的 `r2e_derive_v1` 镜像（SciPy 1.7.3）上
# gold 是 11/13、reward 0。登记的摘要是 env_pins_v2 里 orange3 条目（scipy==1.5.4，env_v2.sh）按当前脚本算出的配方
# 身份，与批次三正式运行所用派生镜像（derived7）记录的 recipe_sha256 相同。构建、回放、正式 actor 任务面都按这张表
# 拒绝环境不配套的组合；新增这类修订、或改动配方脚本与依赖时，同时更新这里。
REVISION_ENV_REQUIREMENTS: dict[str, RevisionEnvRequirement] = {
    "r2e-mr-020": RevisionEnvRequirement(
        recipe_component="+env_v2",
        approved_recipe_sha256=frozenset({"sha256:5122771965c2cb69f748b63f874b514b99b33e731a40d8e568a1af05de9e6fbc"}),
        approved_pins=("scipy==1.5.4",),
    ),
}


def required_env_recipe_components(material_revisions: Iterable[str]) -> dict[str, RevisionEnvRequirement]:
    """本题已应用的修订里，要求评分镜像带特定环境的：{修订编号: 要求}。"""

    return {rid: REVISION_ENV_REQUIREMENTS[rid] for rid in material_revisions if rid in REVISION_ENV_REQUIREMENTS}


def env_requirement_mismatch(recipe_id: str, material_revisions: Iterable[str], *, recipe_sha256: str | None) -> str | None:
    """配方是否满足本题修订所需的环境；不满足返回原因文本，满足返回 None。

    先看步骤片段（`env_recipe_required:<修订>:<片段>`），再看配方内容身份是否在批准集合里
    （`env_recipe_not_approved:<修订>`）：只有步骤名对、装的依赖不对的配方同样拒绝。"""

    for rid, req in sorted(required_env_recipe_components(material_revisions).items()):
        if req.recipe_component not in recipe_id:
            return f"env_recipe_required:{rid}:{req.recipe_component}:recipe={recipe_id}"
        if recipe_sha256 not in req.approved_recipe_sha256:
            return f"env_recipe_not_approved:{rid}:recipe_sha256={recipe_sha256}:approved_pins={','.join(req.approved_pins)}"
    return None


class EnvironmentOverlayError(ValueError):
    """覆盖表缺失 / 结构非法 / 重复任务（fail-closed）。"""


class EnvironmentOverlayFacts(StrictModel):
    """派生镜像配方对这张镜像做了什么（环境侧自报；关键项由消费方在容器里复核）。"""

    interpreter_relocated: bool = Field(description="解释器已搬到沙箱身份可执行的位置（如 /opt/py），`.venv/bin/python` 指向它。")
    testbed_owner: NonEmptyStr = Field(description="构建后 /testbed 的属主（如 \"root\"；运行期两侧仍各自改属主）。")
    git_scrubbed: bool = Field(description="已删 ref/tag/remote、过期 reflog 并 gc——修复提交在仓库里不可达。")
    hidden_tests_location: NonEmptyStr = Field(description="隐藏测试的 root 私有位置（绝对路径）。")
    hidden_tests_tree_sha256: Sha256Digest = Field(
        description="该位置的树摘要（定义同 envpack.bundles_v2.r2e_hidden_tests_tree_digest）；消费方与评分面比对。"
    )


class EnvironmentOverlayV1(StrictModel):
    """一道题的环境覆盖条目。"""

    schema_id: Literal["rh2.environment_overlay.v1"] = Field(default=ENVIRONMENT_OVERLAY_SCHEMA_ID)
    task_id: NonEmptyStr = Field(description='source-qualified 任务主键（"<source>::<instance_id>"）。')
    base_image_ref: NonEmptyStr = Field(description="来源镜像引用（必须等于环境包的 image）。")
    base_image_manifest_digest: Sha256Digest = Field(description="来源镜像 manifest digest（必须等于环境包的记录）。")
    derived_image_ref: NonEmptyStr = Field(description="派生镜像的本机 tag（可重指，身份以 derived_image_id 为准）。")
    derived_image_id: ImageId = Field(description="派生镜像的 image ID（`docker image inspect -f {{.Id}}`）。")
    recipe_id: NonEmptyStr = Field(description="配方身份（名称 + 版本）。")
    recipe_sha256: Sha256Digest = Field(description="配方文件内容摘要。")
    built_at_utc: datetime = Field(description="构建时间。")
    facts: EnvironmentOverlayFacts


def parse_environment_overlays(text: str, *, name: str = "overlays.jsonl") -> dict[str, EnvironmentOverlayV1]:
    """JSONL 文本（一题一行）→ {task_id: overlay}。空行跳过；重复 task_id、坏行一律拒。

    调用方已核过文件摘要时，应解析同一份已校验的字节，不再按路径重读（Codex 09-25 复核 O1）。"""

    out: dict[str, EnvironmentOverlayV1] = {}
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            overlay = EnvironmentOverlayV1.model_validate(json.loads(line))
        except ValueError as exc:
            raise EnvironmentOverlayError(f"{name}:{lineno}: 覆盖条目非法: {exc}") from exc
        if overlay.task_id in out:
            raise EnvironmentOverlayError(f"{name}:{lineno}: 重复 task_id {overlay.task_id}")
        out[overlay.task_id] = overlay
    return out


def load_environment_overlays(path: Path | str) -> dict[str, EnvironmentOverlayV1]:
    """按路径读 JSONL 覆盖表；不做摘要核对（需要核对时用调用方读出的字节调 `parse_environment_overlays`）。"""

    p = Path(path)
    if not p.is_file():
        raise EnvironmentOverlayError(f"环境覆盖表不存在: {p}")
    return parse_environment_overlays(p.read_text(encoding="utf-8"), name=p.name)
