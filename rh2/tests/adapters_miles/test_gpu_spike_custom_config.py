"""B2 生产绑定验收（GPU 前最小收口）：GPU spike custom config 经 miles 解析后
`args.rh2_engine_sampling_mask` 必须为 bool True。

被测事实链::

    rh2/experiments/miles_gpu_spike/custom_config.yaml
    --（--custom-config-path 注入）--> miles_validate_args 的 custom_config 块
    （arguments.py: yaml.safe_load(resolve_file_arg(path)) 后逐 key setattr）
    --> args.rh2_engine_sampling_mask is True
    --> capture wire 走新 return_sampling_mask 约定（test_b2_mask_chain 覆盖）

miles 没有独立的 custom-config 加载函数——解析逻辑内联在
`miles_validate_args` 里（integration base arguments.py:3513 附近；pin base
同块在 :3485 附近）。整函数带几百条与本测试无关的参数断言,CPU 下不可
直调,因此本测试：

1. 用 **miles 真实 `resolve_file_arg`** + 同一 `yaml.safe_load`/`setattr`
   语义加载真实 artifact 文件,断言旗标为 bool True（不是字符串 "true"）;
2. **源码锚定**：静态断言 miles arguments.py 里内联块的两行关键表达式仍
   存在——miles 若重构掉该机制,本测试当场红,防"测的是复刻品、生产走的
   是别条路"的静默漂移。

不标 integration_base：custom_config_path 块与 resolve_file_arg 在 pin 与
integration 两个 base 上同源存在,双 lane 都真实执行。
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "experiments" / "miles_gpu_spike" / "custom_config.yaml"
)


def _load_via_miles_semantics(path: Path) -> Namespace:
    """复刻 miles_validate_args custom_config 块的三行语义（同一函数、同一库）。"""
    import yaml
    from miles.utils.file_arg_utils import resolve_file_arg

    args = Namespace(custom_config_path=str(path))
    data = yaml.safe_load(resolve_file_arg(args.custom_config_path)) or {}
    for k, v in data.items():
        setattr(args, k, v)
    return args


def test_custom_config_sets_engine_sampling_mask_true(world):
    args = _load_via_miles_semantics(CONFIG_PATH)
    # bool True 而非字符串："true"/"1" 之类在 generate.py 的 if 判断下也为真,
    # 但会污染 capture_params 记录与后续相等断言——锁死为 YAML bool。
    assert args.rh2_engine_sampling_mask is True


def test_custom_config_sets_zero_signal_bindings(world):
    """F2 配套两 key 的类型与数值（消费者见 yaml 注释）：熔断阈值必须是
    正 int（miles _bump_zero_signal_fuse 与 0 比较、与计数比较）;MoE aux
    coeff 必须是 float 0.0（model_provider 非 None 即覆写,0 关闭 aux 目标,
    保证 total-gradient 零判定 ⇔ policy signal 零）。"""
    args = _load_via_miles_semantics(CONFIG_PATH)
    assert args.max_consecutive_zero_signal_steps == 8
    assert isinstance(args.max_consecutive_zero_signal_steps, int)
    assert args.moe_aux_loss_coeff == 0.0
    assert isinstance(args.moe_aux_loss_coeff, float)


def test_custom_config_carries_exactly_the_reviewed_keys(world):
    """零扩张纪律：artifact 只承载已评审的 key 集,整 dict 断言（多出的 key =
    绕开评审的后门注入面;增删必须同步改这里,构成可审计变更）。
    2026-08-27 F2 扩张：+max_consecutive_zero_signal_steps（零信号连续跳过
    熔断阈值）,+moe_aux_loss_coeff=0.0（训练目标单一化,零信号判定前提）。"""
    import yaml
    from miles.utils.file_arg_utils import resolve_file_arg

    data = yaml.safe_load(resolve_file_arg(str(CONFIG_PATH)))
    assert data == {
        "rh2_engine_sampling_mask": True,
        "max_consecutive_zero_signal_steps": 8,
        "moe_aux_loss_coeff": 0.0,
    }


def test_miles_inline_loader_source_anchor(world):
    """源码锚定：miles_validate_args 的 custom_config 内联块未被重构掉。

    锚定的是**生产解析机制本身**（resolve_file_arg + yaml.safe_load + 逐 key
    setattr）;任一表达式消失说明 --custom-config-path 语义变了,上面两个
    测试的"复刻语义"就不再代表生产行为——必须当场红,重对齐。
    """
    source = (world.miles_root / "miles" / "utils" / "arguments.py").read_text()
    assert "yaml.safe_load(resolve_file_arg(args.custom_config_path))" in source
    assert "setattr(args, k, v)" in source
