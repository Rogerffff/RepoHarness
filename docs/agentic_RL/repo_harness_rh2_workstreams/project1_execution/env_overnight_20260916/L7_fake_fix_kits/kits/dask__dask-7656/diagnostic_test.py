"""L7 判别用例 · dask__dask-7656

gold 在 `dask/delayed.py` 里改了**两处**同形状的代码：`unpack_collections`（:109）
与 `to_task_dask`（:191）。唯一的 F2P 只经过前者，48 条 P2P 也不碰后者，
所以"只改一处"的部分修复在判分面上与 gold 无法区分。

三态预期：base 失败、gold 通过、fake 失败（to_task_dask 仍然 AttributeError）。
"""
import dataclasses
import warnings

import dask


def test_l7_to_task_dask_also_handles_init_false_fields():
    from dask.delayed import to_task_dask

    ADataClass = dataclasses.make_dataclass(
        "ADataClass", [("a", int), ("b", int, dataclasses.field(init=False))]
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # to_task_dask 自带 DeprecationWarning
        task, dsk = to_task_dask(ADataClass(a=dask.delayed(3)))
    assert task is not None
