# 退化（§4 第 3 步，只改 mask）：da.ma.ones_like / zeros_like 的值、dtype、MaskedArray 类型与 gold 相同，
# 但 mask 错误（MODE=none：全不屏蔽；MODE=invert：取反）。empty_like 与 gold 相同。
import os
from pathlib import Path
mode = os.environ["MODE"]
p = Path("dask/array/ma.py")
s = p.read_text()
mask_expr = {"none": "False", "invert": "~np.ma.getmaskarray(x)"}[mode]
s += f'''

def _wrong_mask(func):
    def inner(x, **kwargs):
        r = func(x, **kwargs)
        return np.ma.masked_array(np.ma.getdata(r), mask={mask_expr})

    return inner


@derived_from(np.ma.core)
def ones_like(a, **kwargs):
    a = asanyarray(a)
    return a.map_blocks(_wrong_mask(np.ma.core.ones_like), **kwargs)


@derived_from(np.ma.core)
def zeros_like(a, **kwargs):
    a = asanyarray(a)
    return a.map_blocks(_wrong_mask(np.ma.core.zeros_like), **kwargs)


@derived_from(np.ma.core)
def empty_like(a, **kwargs):
    a = asanyarray(a)
    return a.map_blocks(np.ma.core.empty_like, **kwargs)
'''
p.write_text(s)
