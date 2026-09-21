"""L7 判别用例 · Project-MONAI__MONAI-6975

gold 改的是 `apply_transform` 的 `lazy` 默认值（False -> None）；
只改 `Dataset._transform` 一个调用点也能过全部 4 条 F2P，
但另外 11 个调用点（CacheDataset / IterableDataset / GridPatchDataset / engines 等）仍然坏着。

三态预期：base 失败、gold 通过、fake 失败。
"""
import inspect

from monai.transforms.transform import apply_transform


def test_l7_apply_transform_lazy_default_is_none():
    param = inspect.signature(apply_transform).parameters["lazy"]
    assert param.default is None, param.default
