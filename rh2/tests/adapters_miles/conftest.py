"""adapters_miles 测试的公共环境装配（miles 迁移 C0）。

三条硬约束，决定了本 conftest 的形状：

1. **vendor 优先**：本目录测试必须用 rh2/src/slime（vendor）而不是
   reference/slime。为了不污染同一 pytest 会话里的其他测试（tests/adapters
   与 tests/contract_slime_async 自己把 reference/slime 插进 sys.path，
   且 contract 侧要 import vendor 有意不含的 slime.rollout.*/dp_schedule），
   slime 的 path/module 装配全部放在**module 级 autouse fixture 的
   setup/teardown**里做，测试模块自身**不得在模块级 import
   slime/miles/repoharness2.adapters.miles**（一律经 `world` fixture 或
   测试函数内 import）。teardown 会把 vendor slime 与
   repoharness2.adapters.miles 从 sys.modules 摘除并还原 sys.path，
   后续目录（contract_slime_async）重新 import 时拿回 reference/slime。

2. **ray stub**：miles.utils.misc 模块级 `import ray`，rh2 venv 无 ray。
   这里装一个只覆盖"import 成立"所需符号的最小 stub（真实训练环境有真
   ray；本 stub 与 spike P0-1 对 sglang 的 stub 同一性质——环境噪音，
   不复刻任何行为）。

3. **sglang stub**：miles.rollout.base_types 经 data_source ->
   chat_template_utils 模块级拉 sglang 两个符号（protocol.Tool、
   encoding_dsv4，spike 已核）。只有用到 base_types/load_generate_function
   的测试需要，按需调 `install_sglang_stub()`。
"""

from __future__ import annotations

import sys
import types
from argparse import Namespace
from pathlib import Path

import pytest

RH2_SRC = Path(__file__).resolve().parents[2] / "src"
REPO_ROOT = Path(__file__).resolve().parents[3]
MILES_ROOT = REPO_ROOT / "reference" / "miles"

collect_ignore: list[str] = []


# ---------------------------------------------------------------------------
# stub 安装（幂等）
# ---------------------------------------------------------------------------


def _install_ray_stub() -> None:
    try:
        import ray  # noqa: F401

        return  # 环境里有真 ray（或已装过 stub）
    except ModuleNotFoundError:
        pass

    ray = types.ModuleType("ray")
    ray.__path__ = []  # 伪装成包，允许 "ray.util" 子模块挂载
    ray.__rh2_test_stub__ = True
    ray_util = types.ModuleType("ray.util")
    ray_util.__path__ = []
    sched = types.ModuleType("ray.util.scheduling_strategies")

    class NodeAffinitySchedulingStrategy:  # 只为 miles.utils.ray_utils import 成立
        def __init__(self, *a, **k):
            pass

    sched.NodeAffinitySchedulingStrategy = NodeAffinitySchedulingStrategy
    state_mod = types.ModuleType("ray.util.state")
    state_mod.list_nodes = lambda *a, **k: []
    ray.util = ray_util
    ray_util.scheduling_strategies = sched
    ray_util.state = state_mod
    sys.modules.update(
        {
            "ray": ray,
            "ray.util": ray_util,
            "ray.util.scheduling_strategies": sched,
            "ray.util.state": state_mod,
        }
    )


def install_sglang_stub() -> None:
    """miles 加载链的 sglang 最小 stub（符号清单与 spike P0-1 步骤 5 相同）。"""

    if "sglang" in sys.modules:
        return
    import pydantic

    class _StubTool(pydantic.BaseModel):
        """sglang Tool 占位：仅让 import 成立，不复刻 schema。"""

        model_config = pydantic.ConfigDict(extra="allow")

    def _mk(name: str) -> types.ModuleType:
        m = types.ModuleType(name)
        m.__rh2_test_stub__ = True
        sys.modules[name] = m
        return m

    _sglang = _mk("sglang")
    _srt = _mk("sglang.srt")
    _ep = _mk("sglang.srt.entrypoints")
    _oa = _mk("sglang.srt.entrypoints.openai")
    _proto = _mk("sglang.srt.entrypoints.openai.protocol")
    _enc = _mk("sglang.srt.entrypoints.openai.encoding_dsv4")
    _sglang.srt = _srt
    _srt.entrypoints = _ep
    _ep.openai = _oa
    _oa.protocol = _proto
    _oa.encoding_dsv4 = _enc
    _proto.Tool = _StubTool


def _evict_module_prefix(prefix: str) -> None:
    for name in [n for n in sys.modules if n == prefix or n.startswith(prefix + ".")]:
        del sys.modules[name]


# ---------------------------------------------------------------------------
# vendor slime 世界（module 级 autouse）
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True, scope="module")
def _vendor_slime_world():
    saved_path = list(sys.path)

    # 同会话早前目录（tests/adapters）可能已加载 reference/slime——全部摘除，
    # 让本目录 import 重新解析到 vendor。
    _evict_module_prefix("slime")
    _evict_module_prefix("repoharness2.adapters.miles")  # 其内绑定 SlimeSample 类对象

    if str(RH2_SRC) in sys.path:
        sys.path.remove(str(RH2_SRC))
    sys.path.insert(0, str(RH2_SRC))
    if str(MILES_ROOT) not in sys.path:
        sys.path.insert(1, str(MILES_ROOT))

    _install_ray_stub()

    import slime

    assert Path(slime.__file__).resolve().is_relative_to(RH2_SRC), (
        f"slime 未解析到 vendor：{slime.__file__}"
    )

    yield

    # 摘除 vendor 世界并还原 path：后续目录（contract_slime_async 等）
    # 重新 import slime 时按它们自己的 path 插入拿 reference/slime。
    _evict_module_prefix("slime")
    _evict_module_prefix("repoharness2.adapters.miles")
    sys.path[:] = saved_path


# ---------------------------------------------------------------------------
# world fixture：集中提供两侧 Sample 类与被测函数（测试函数内取用）
# ---------------------------------------------------------------------------


class _World:
    """惰性 import 汇集点：测试模块不得模块级 import 这些名字。"""

    def __init__(self) -> None:
        from miles.utils.types import Sample as MilesSample
        from slime.utils.types import Sample as SlimeSample

        from repoharness2.adapters.miles import (
            CanonicalizationError,
            Rh2MilesGenerateFn,
            canonicalize_group,
            canonicalize_sample,
        )

        self.MS = MilesSample
        self.SS = SlimeSample
        self.CanonicalizationError = CanonicalizationError
        self.Rh2MilesGenerateFn = Rh2MilesGenerateFn
        self.canonicalize_group = canonicalize_group
        self.canonicalize_sample = canonicalize_sample
        # 工具转发：测试模块不 `import conftest`（tests/ 下多目录同名
        # conftest.py，按 sys.path 裸 import 会撞名），统一走 world。
        self.install_sglang_stub = install_sglang_stub
        self.rh2_src = RH2_SRC

    # -- 样本工厂（形状对齐 vendor to_sample / rh2 收口路径的真实输出）------

    def mk_miles_input(self, index=0, group_index=0, rollout_id=None, **over):
        s = self.MS(
            index=index,
            group_index=group_index,
            rollout_id=rollout_id,
            prompt="prompt",
            routing_key=f"rk-{group_index}-{index}",
        )
        for k, v in over.items():
            setattr(s, k, v)
        return s

    def mk_vendor_sample(
        self,
        index=0,
        group_index=0,
        rollout_id=None,
        status=None,
        truncated=False,
        reward=1.0,
        versions=("7",),
        **over,
    ):
        """vendor `_SampleBuilder.to_sample()` + backfill 后的典型叶链形状。"""

        s = self.SS(
            index=index,
            group_index=group_index,
            rollout_id=rollout_id,
            prompt="prompt",
            label=None,
            tokens=[10, 11, 12, 13, 14],
            response="resp",
            response_length=3,
            loss_mask=[1, 0, 1],
            rollout_log_probs=[-0.1, 0.0, -0.25],
            reward=reward,
            weight_versions=[str(v) for v in versions],
            status=status if status is not None else self.SS.Status.COMPLETED,
            metadata={"truncated": truncated, "use_tool": False, "ill_formed": False},
        )
        for k, v in over.items():
            setattr(s, k, v)
        return s

    def mk_miles_args(self, **over):
        """miles buffer/postprocess/train conversion 消费的最小 args 面。"""

        base = dict(
            async_data_buffer_capacity_factor=2.0,
            rollout_batch_size=2,
            dynamic_sampling_filter_path=None,
            max_weight_staleness=None,
            reward_key=None,
            disable_rollout_trim_samples=False,
            use_dynamic_global_batch_size=False,
            global_batch_size=4,
            advantage_estimator="grpo",
            rewards_normalization=True,
            grpo_std_normalization=True,
            multi_lora=None,
            n_samples_per_prompt=4,
        )
        base.update(over)
        return Namespace(**base)


@pytest.fixture
def world(_vendor_slime_world) -> _World:
    return _World()
