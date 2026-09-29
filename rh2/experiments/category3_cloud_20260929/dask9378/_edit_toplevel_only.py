# 另一种设计：不新增 da.ma 入口，而是让顶层 da.ones_like / zeros_like / empty_like 对 masked 输入保留 mask
# （题面 “Currently” 示例用的正是顶层函数）。指定 shape/chunks 时沿用原路径。
from pathlib import Path
p = Path("dask/array/creation.py")
s = p.read_text()
for fn in ("empty", "ones", "zeros"):
    old = f'''    a = asarray(a, name=False)
    shape, chunks = _get_like_function_shapes_chunks(a, chunks, shape)
    return {fn}(
'''
    assert s.count(old) == 1, fn
    new = f'''    a = asarray(a, name=False)
    if shape is None and chunks is None and isinstance(a._meta, np.ma.MaskedArray):
        return a.map_blocks(
            partial(np.ma.core.{fn}_like, dtype=dtype, order=order), dtype=(dtype or a.dtype)
        )
    shape, chunks = _get_like_function_shapes_chunks(a, chunks, shape)
    return {fn}(
'''
    s = s.replace(old, new)
p.write_text(s)
