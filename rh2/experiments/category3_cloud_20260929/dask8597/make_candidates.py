"""生成 dask__dask-8597 的候选补丁（私有对照与正式评分用，不交给求解者）。

用法：python make_candidates.py <base 文件目录> <输出目录>
base 目录里需要镜像内 /testbed 的 dask/array/slicing.py 与 dask/array/core.py 原件
（例如 `docker create c3keep/dask8597:src` 后 `docker cp`）。
每个候选都是对 base 源码的文本替换；替换前断言原文恰好出现一次。按公开要求判对错，不以 gold 为答案。
"""
import difflib
import sys
from pathlib import Path

SL = "dask/array/slicing.py"
CORE = "dask/array/core.py"

# ---- base 原文片段（take 里的块大小阈值） ----
BASE = '''    if math.isnan(other_numel):
        warnsize = maxsize = math.inf
    else:
        maxsize = math.ceil(nbytes / (other_numel * itemsize))
        warnsize = maxsize * 5
'''

# gold 的写法（与 gold.patch 逐字一致，用来核对替换位置）
GOLD = '''    if math.isnan(other_numel) or other_numel == 0:
        warnsize = maxsize = math.inf
    else:
        maxsize = math.ceil(nbytes / (other_numel * itemsize))
        warnsize = maxsize * 5
'''

# ---------------- 合理实现（查误拒 T1） ----------------

# 常见的“防除零”写法：零长度轴时按每行至少 1 个元素估算。阈值变为有限大（默认配置下 1600 万行拆块、
# 8000 万行告警），只有极端规模才与 gold 不同。
CLAMP1 = '''    if math.isnan(other_numel):
        warnsize = maxsize = math.inf
    else:
        # Rows may hold no elements when another dimension has length zero;
        # count at least one element per row so the estimate stays finite.
        maxsize = math.ceil(nbytes / (max(other_numel, 1) * itemsize))
        warnsize = maxsize * 5
'''

# 先设无限，只有每行元素数已知且为正时才算阈值（09-21 复核提出的非 gold 路线）。nan > 0 为 False。
LAZY = '''    # Without a known, positive number of elements per row there is no
    # meaningful per-chunk size limit (unknown chunks, or an empty axis).
    warnsize = maxsize = math.inf
    if other_numel > 0:
        maxsize = math.ceil(nbytes / (other_numel * itemsize))
        warnsize = maxsize * 5
'''

# 捕获溢出、同时关掉 numpy 的除零警告：语义与 gold 相同，结构是 try/except。
ERRSTATE = '''    if math.isnan(other_numel):
        warnsize = maxsize = math.inf
    else:
        with np.errstate(divide="ignore"):
            rows = nbytes / (other_numel * itemsize)
        try:
            maxsize = math.ceil(rows)
        except OverflowError:
            # zero-sized rows: any number of them fits into one chunk
            maxsize = math.inf
        warnsize = maxsize * 5
'''

# ---------------- 错误候选（查漏判） ----------------

# 09-21 主审与复核登记的“仅 split=True 时算阈值”（逐字按复核给出的条件）：
# 默认原例跳过除法而恢复；默认配置的大块警告整体消失；split=True 下零长度轴仍除零。
SPLIT_ONLY = '''    if math.isnan(other_numel) or config.get("array.slicing.split-large-chunks", None) is not True:
        warnsize = maxsize = math.inf
    else:
        maxsize = math.ceil(nbytes / (other_numel * itemsize))
        warnsize = maxsize * 5
'''

# 同上，再加零长度判断：三种配置下零长度轴都对，只丢默认大块警告（用来检验修订是否保护该文档行为）。
SPLIT_ONLY_ZERO = '''    if (
        math.isnan(other_numel)
        or other_numel == 0
        or config.get("array.slicing.split-large-chunks", None) is not True
    ):
        warnsize = maxsize = math.inf
    else:
        maxsize = math.ceil(nbytes / (other_numel * itemsize))
        warnsize = maxsize * 5
'''

# 示例形态子集：只看最后一个轴是否为空（题面原例的零长度轴在最后）。
LAST_AXIS = '''    if math.isnan(other_numel) or sum(chunks[-1]) == 0:
        warnsize = maxsize = math.inf
    else:
        maxsize = math.ceil(nbytes / (other_numel * itemsize))
        warnsize = maxsize * 5
'''

# 示例形态子集：只处理沿第 0 轴索引（题面原例的索引轴）。
AXIS0 = '''    if math.isnan(other_numel) or (axis == 0 and other_numel == 0):
        warnsize = maxsize = math.inf
    else:
        maxsize = math.ceil(nbytes / (other_numel * itemsize))
        warnsize = maxsize * 5
'''

# 吞掉题面报告的异常，但不避开除法：结果对，numpy 仍发 RuntimeWarning（除零）。
SWALLOW_WARN = '''    if math.isnan(other_numel):
        warnsize = maxsize = math.inf
    else:
        try:
            maxsize = math.ceil(nbytes / (other_numel * itemsize))
        except OverflowError:
            maxsize = math.inf
        warnsize = maxsize * 5
'''

# 吞掉错误并“报告成功”：溢出时原样返回输入（不做索引）。关掉除零警告，失败只来自结果本身。
SWALLOW_SELF = '''    if math.isnan(other_numel):
        warnsize = maxsize = math.inf
    else:
        try:
            with np.errstate(divide="ignore"):
                maxsize = math.ceil(nbytes / (other_numel * itemsize))
        except OverflowError:
            # empty rows: nothing to take, keep the input blocks as they are
            dsk = {
                (outname,) + k: (inname,) + k
                for k in product(*[range(len(c)) for c in chunks])
            }
            return tuple(chunks), dsk
        warnsize = maxsize * 5
'''

# 阈值写成 0：默认配置对空块也发“large chunk”警告；split=True 时 ceil(len / 0) 除零。
WARN_ZERO = '''    if math.isnan(other_numel):
        warnsize = maxsize = math.inf
    else:
        maxsize = math.ceil(nbytes / (other_numel * itemsize)) if other_numel else 0
        warnsize = maxsize * 5
'''

# 只对小规模有效：零长度轴时每块 1 行。默认配置下索引超过 5 个就误发警告，split=True 下逐行拆块。
CAP_ONE = '''    if math.isnan(other_numel):
        warnsize = maxsize = math.inf
    else:
        maxsize = math.ceil(nbytes / (other_numel * itemsize)) if other_numel else 1
        warnsize = maxsize * 5
'''

# ---- 在 take 里提前返回的两种写法（插在 other_numel 计算之后） ----
ANCHOR = '''    other_numel = np.prod([sum(x) for x in other_chunks])
'''

# 提前返回、忽略分块计划：所有行都从第一个块取。只在被索引轴只有一个块、其余轴也只有一个块时对。
SINGLE_BLOCK = ANCHOR + '''
    if other_numel == 0:
        # Every row is empty, so there is nothing worth splitting or
        # rearranging: take all requested rows from the first block.
        chunks2 = list(chunks)
        chunks2[axis] = (len(index),)
        slc = tuple(index if i == axis else colon for i in range(len(chunks)))
        zeros = (0,) * len(chunks)
        return tuple(chunks2), {(outname,) + zeros: (getitem, (inname,) + zeros, slc)}
'''

# 提前返回、直接造空块：不读输入，块由 np.zeros 生成，dtype 恒为 float64（只覆盖题面原例的 dtype）。
FLOAT_BLOCKS = ANCHOR + '''
    if other_numel == 0:
        # Every row is empty: build the (empty) output blocks directly
        # instead of reading them from the input.
        chunks2 = list(chunks)
        chunks2[axis] = tuple(len(index_list) for _, index_list in plan)
        dsk = {}
        for idx in product(*[range(len(c)) for c in chunks2]):
            shape = tuple(c[i] for c, i in zip(chunks2, idx))
            dsk[(outname,) + idx] = (np.zeros, shape)
        return tuple(chunks2), dsk
'''

# 同上，但每个任务仍引用对应的输入块（图依赖一致，能通过 HighLevelGraph.validate），块本身用
# np.zeros(shape) 生成，dtype 恒为 float64：只覆盖题面原例的 dtype（float_blocks 已被原测试的图校验拒绝）。
FLOAT_BLOCKS_DEP = ANCHOR + '''
    if other_numel == 0:
        # Every row is empty: create the empty output blocks directly from
        # their shapes instead of indexing into the input blocks.
        def empty_rows(block, shape):
            return np.zeros(shape)

        chunks2 = list(chunks)
        chunks2[axis] = tuple(len(index_list) for _, index_list in plan)
        dsk = {}
        for idx in product(*[range(len(c)) for c in chunks2]):
            src = list(idx)
            src[axis] = plan[idx[axis]][0]
            shape = tuple(c[i] for c, i in zip(chunks2, idx))
            dsk[(outname,) + idx] = (empty_rows, (inname,) + tuple(src), shape)
        return tuple(chunks2), dsk
'''

# ---- Array.__getitem__ 层的两种写法（插在 normalize_index 之后） ----
GI_ANCHOR = '''        index2 = normalize_index(index, self.shape)
        dependencies = {self.name}
'''

# 数据形态子集（返回类型）：没有元素的数组直接用 NumPy 算，返回 numpy.ndarray 而不是 dask Array。
RETURN_NUMPY = '''        index2 = normalize_index(index, self.shape)
        # An array without elements has nothing to compute lazily: index an
        # empty NumPy array of the same shape to get NumPy's result directly.
        if 0 in self.shape and not any(isinstance(i, Array) for i in index2):
            return np.empty(self.shape, dtype=self.dtype)[index2]
        dependencies = {self.name}
'''

# 合理但与 gold 位置不同：没有元素的数组用 NumPy 在空替身上求结果形状，再包成 dask Array。
# 结果仍是 dask Array、dtype 与 NumPy 一致；代价是结果图不再引用输入（空数组没有数据），
# 非 NumPy 后端（cupy 等）的 meta 类型会变成 NumPy（登记为边缘差异）。
EAGER_EMPTY = '''        index2 = normalize_index(index, self.shape)
        # An array without elements holds no data: compute NumPy's result on an
        # empty stand-in of the same shape and wrap it as a dask array.
        if 0 in self.shape and not any(isinstance(i, Array) for i in index2):
            return from_array(np.empty(self.shape, dtype=self.dtype)[index2])
        dependencies = {self.name}
'''

CANDIDATES = {
    "gold_regen": {SL: [(BASE, GOLD)]},
    "clamp1": {SL: [(BASE, CLAMP1)]},
    "lazy_threshold": {SL: [(BASE, LAZY)]},
    "errstate_catch": {SL: [(BASE, ERRSTATE)]},
    "eager_empty": {CORE: [(GI_ANCHOR, EAGER_EMPTY)]},
    "split_only": {SL: [(BASE, SPLIT_ONLY)]},
    "split_only_zero": {SL: [(BASE, SPLIT_ONLY_ZERO)]},
    "last_axis_only": {SL: [(BASE, LAST_AXIS)]},
    "axis0_only": {SL: [(BASE, AXIS0)]},
    "swallow_warn": {SL: [(BASE, SWALLOW_WARN)]},
    "swallow_self": {SL: [(BASE, SWALLOW_SELF)]},
    "warn_zero": {SL: [(BASE, WARN_ZERO)]},
    "cap_one": {SL: [(BASE, CAP_ONE)]},
    "single_block": {SL: [(ANCHOR, SINGLE_BLOCK)]},
    "float_blocks": {SL: [(ANCHOR, FLOAT_BLOCKS)]},
    "float_blocks_dep": {SL: [(ANCHOR, FLOAT_BLOCKS_DEP)]},
    "return_numpy": {CORE: [(GI_ANCHOR, RETURN_NUMPY)]},
}


def make_patch(base_dir: Path, edits: dict) -> str:
    out = []
    for rel, repl in edits.items():
        old = (base_dir / rel).read_text()
        new = old
        for before, after in repl:
            assert new.count(before) == 1, (rel, before[:60])
            new = new.replace(before, after, 1)
        diff = difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True), f"a/{rel}", f"b/{rel}"
        )
        out.append(f"diff --git a/{rel} b/{rel}\n" + "".join(diff))
    return "".join(out)


def main():
    base_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, edits in CANDIDATES.items():
        (out_dir / f"{name}.patch").write_text(make_patch(base_dir, edits))
        print(name)


if __name__ == "__main__":
    main()
