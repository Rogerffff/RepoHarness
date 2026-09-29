"""L7 判别用例 · Project-MONAI__MONAI-3715

判分面只有 mode='eval'（F2P）和默认 mode（P2P），所以"无条件 self.mode = eval_mode"满分，
而这恰好把题面真正要修的东西（mode='train' 应当用 train_mode）毁掉。

三态预期：base 失败（"train" != ForwardMode.TRAIN，掉进 else 抛 ValueError）、
gold 通过、fake 失败（train 被静默降级成 eval；非法 mode 也不再抛）。
"""
import pytest
import torch

from monai.engines import PrepareBatchDefault, SupervisedEvaluator
from monai.engines.evaluator import eval_mode, train_mode
from monai.utils.enums import ForwardMode


class _Net(torch.nn.Module):
    def forward(self, x):
        return x


def _make(mode):
    return SupervisedEvaluator(
        device=torch.device("cpu"),
        val_data_loader=[],
        epoch_length=0,
        network=_Net(),
        non_blocking=False,
        prepare_batch=PrepareBatchDefault(),
        decollate=False,
        mode=mode,
    )


@pytest.mark.parametrize("mode", ["train", ForwardMode.TRAIN])
def test_l7_train_mode_is_honored(mode):
    assert _make(mode).mode is train_mode


@pytest.mark.parametrize("mode", ["eval", ForwardMode.EVAL])
def test_l7_eval_mode_is_honored(mode):
    assert _make(mode).mode is eval_mode


def test_l7_invalid_mode_still_raises():
    with pytest.raises(ValueError):
        _make("definitely-not-a-mode")
