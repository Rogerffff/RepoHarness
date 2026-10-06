"""L7 判别用例 · Project-MONAI__MONAI-3403

F2P 只查"两次调用的返回元素类型一致"。gold 真正改的两件事没有任何断言：
(a) 不再就地改写传入的 centers；(b) 返回 int。

三态预期：base 两条都失败、gold 两条都通过、fake 两条都失败
（fake 保留就地改写、并且返回 torch.Tensor）。
"""
from monai.transforms.utils import correct_crop_centers


def test_l7_input_centers_are_not_mutated():
    centers = [1, 1, 1]
    snapshot = list(centers)
    correct_crop_centers(centers, [4, 4, 4], [10, 10, 10])
    assert centers == snapshot


def test_l7_result_elements_are_python_ints():
    result = correct_crop_centers([1, 1, 1], [4, 4, 4], [10, 10, 10])
    assert all(isinstance(c, int) for c in result), [type(c) for c in result]
