"""生成 dask__dask-7305 的候选补丁（私有对照与正式评分用，不交给求解者）。

用法：python make_candidates.py <base 文件目录> <输出目录>
base 目录里需要镜像内的 dask/dataframe/partitionquantiles.py 与 shuffle.py 原件。
每个候选都是对 base 源码的文本替换；替换前断言原文恰好出现一次。
"""
import difflib
import sys
from pathlib import Path

PQ = "dask/dataframe/partitionquantiles.py"
SH = "dask/dataframe/shuffle.py"

# ---- base 原文片段 ----
SUMMARY_BASE = '''    interpolation = "linear"
    if is_categorical_dtype(data):
        data = data.codes
        interpolation = "nearest"
    vals, n = _percentile(data, qs, interpolation=interpolation)
    if interpolation == "linear" and np.issubdtype(data.dtype, np.integer):
        vals = np.round(vals).astype(data.dtype)
    vals_and_weights = percentiles_to_weights(qs, vals, length)
'''

# gold 的 percentiles_summary（与 gold.patch 逐字一致）
SUMMARY_GOLD = '''    interpolation = "linear"
    if is_categorical_dtype(data):
        data = data.codes
        interpolation = "nearest"
    elif np.issubdtype(data.dtype, np.integer):
        interpolation = "nearest"
    vals, n = _percentile(data, qs, interpolation=interpolation)
    vals_and_weights = percentiles_to_weights(qs, vals, length)
'''

# 合理替代 A：保留线性插值的内部分界，只把两端恢复为精确的最小值与最大值
# （与 _percentile 对 datetime 的 #6864 处理、上游 CuPy 分支同一思路，这里两端都做）
SUMMARY_EXACT_ENDS = '''    interpolation = "linear"
    if is_categorical_dtype(data):
        data = data.codes
        interpolation = "nearest"
    vals, n = _percentile(data, qs, interpolation=interpolation)
    if interpolation == "linear" and np.issubdtype(data.dtype, np.integer):
        vals = np.round(vals).astype(data.dtype)
        # Linear interpolation goes through float64, which cannot represent
        # every large integer exactly (e.g. uint64 above 2**53), so the
        # interpolated extremes may drift.  Keep the exact minimum and maximum
        # of the data (compare dask/dask#6864 for datetimes).
        lo, hi = data.min(), data.max()
        np.clip(vals, lo, hi, out=vals)
        if qs[0] == 0:
            vals[0] = lo
        if qs[-1] == 100:
            vals[-1] = hi
    vals_and_weights = percentiles_to_weights(qs, vals, length)
'''

# 合理替代 B：同样取已有样本值（离散选择），但平局取 higher
SUMMARY_HIGHER = '''    interpolation = "linear"
    if is_categorical_dtype(data):
        data = data.codes
        interpolation = "nearest"
    elif np.issubdtype(data.dtype, np.integer):
        # Pick existing values: linear interpolation goes through float64,
        # which cannot represent large integers exactly.
        interpolation = "higher"
    vals, n = _percentile(data, qs, interpolation=interpolation)
    if interpolation == "linear" and np.issubdtype(data.dtype, np.integer):
        vals = np.round(vals).astype(data.dtype)
    vals_and_weights = percentiles_to_weights(qs, vals, length)
'''

# 退化 N1（只对部分规模有效）：改成 nearest，但在 float64 上取值，2**53 以上仍会漂移
SUMMARY_NEAREST_VIA_FLOAT = '''    interpolation = "linear"
    if is_categorical_dtype(data):
        data = data.codes
        interpolation = "nearest"
    elif np.issubdtype(data.dtype, np.integer):
        # Pick existing values instead of interpolating between them
        interpolation = "nearest"
        vals, n = _percentile(data.astype(np.float64), qs, interpolation=interpolation)
        vals = vals.astype(data.dtype)
        return percentiles_to_weights(qs, vals, length)
    vals, n = _percentile(data, qs, interpolation=interpolation)
    if interpolation == "linear" and np.issubdtype(data.dtype, np.integer):
        vals = np.round(vals).astype(data.dtype)
    vals_and_weights = percentiles_to_weights(qs, vals, length)
'''

# 退化 N2（只覆盖类型子集）：只对 uint64 改用 nearest
SUMMARY_UINT_ONLY = '''    interpolation = "linear"
    if is_categorical_dtype(data):
        data = data.codes
        interpolation = "nearest"
    elif data.dtype == np.uint64:
        interpolation = "nearest"
    vals, n = _percentile(data, qs, interpolation=interpolation)
    if interpolation == "linear" and np.issubdtype(data.dtype, np.integer):
        vals = np.round(vals).astype(data.dtype)
    vals_and_weights = percentiles_to_weights(qs, vals, length)
'''

# 退化 N4（依赖顺序）：用每个分区的首尾元素当端点，默认数据已排序
SUMMARY_FIRST_LAST = '''    interpolation = "linear"
    if is_categorical_dtype(data):
        data = data.codes
        interpolation = "nearest"
    vals, n = _percentile(data, qs, interpolation=interpolation)
    if interpolation == "linear" and np.issubdtype(data.dtype, np.integer):
        vals = np.round(vals).astype(data.dtype)
        # keep the exact first and last values of the (sorted) partition
        vals[0], vals[-1] = data[0], data[-1]
    vals_and_weights = percentiles_to_weights(qs, vals, length)
'''

# 退化 N5（只处理题面示例字面值）：只在 npartitions=1（题面的调用）时改用 nearest
SUMMARY_K1_ONLY = '''    interpolation = "linear"
    if is_categorical_dtype(data):
        data = data.codes
        interpolation = "nearest"
    elif np.issubdtype(data.dtype, np.integer) and num_new == 1:
        interpolation = "nearest"
    vals, n = _percentile(data, qs, interpolation=interpolation)
    if interpolation == "linear" and np.issubdtype(data.dtype, np.integer):
        vals = np.round(vals).astype(data.dtype)
    vals_and_weights = percentiles_to_weights(qs, vals, length)
'''

# ---- process_val_weights：两处剩余精度损失 ----
PVW_ARRAY_BASE = '''    vals, weights = vals_and_weights
    vals = np.array(vals)
    weights = np.array(weights)
'''
PVW_ARRAY_TYPED = '''    vals, weights = vals_and_weights
    if isinstance(dtype, np.dtype) and np.issubdtype(dtype, np.integer):
        # Keep integer summaries in their own dtype: e.g. a mix of uint64
        # values below and above 2**63 would otherwise become float64.
        vals = np.array(vals, dtype=dtype)
    else:
        vals = np.array(vals)
    weights = np.array(weights)
'''
PVW_INTERP_BASE = '''            rv = np.interp(q_target, q_weights, vals)
        else:
'''
PVW_INTERP_PINNED = '''            rv = np.interp(q_target, q_weights, vals)
            if np.issubdtype(vals.dtype, np.integer):
                # np.interp works in float64, which cannot hold every large
                # integer: keep the exact endpoints and stay within them.
                lo, hi = int(vals[0]), int(vals[-1])
                inner = [min(max(int(x), lo), hi) for x in rv[1:-1]]
                rv = np.array([lo] + inner + [hi], dtype=vals.dtype)
        else:
'''

# ---- shuffle：症状抑制 ----
SETPART_BASE = '''    partitions = divisions.searchsorted(s, side="right") - 1
    partitions[(s >= divisions.iloc[-1]).values] = len(divisions) - 2
    return partitions
'''
SETPART_CLIP = '''    partitions = divisions.searchsorted(s, side="right") - 1
    partitions[(s >= divisions.iloc[-1]).values] = len(divisions) - 2
    # values below the first division belong to the first partition
    partitions[(s < divisions.iloc[0]).values] = 0
    return partitions
'''

CANDIDATES = {
    "gold_recon": {PQ: [(SUMMARY_BASE, SUMMARY_GOLD)]},  # 用于核对与 gold.patch 等价，不参评
    "exact_ends": {PQ: [(SUMMARY_BASE, SUMMARY_EXACT_ENDS)]},
    "higher_int": {PQ: [(SUMMARY_BASE, SUMMARY_HIGHER)]},
    "nearest_via_float": {PQ: [(SUMMARY_BASE, SUMMARY_NEAREST_VIA_FLOAT)]},
    "uint_only": {PQ: [(SUMMARY_BASE, SUMMARY_UINT_ONLY)]},
    "first_last": {PQ: [(SUMMARY_BASE, SUMMARY_FIRST_LAST)]},
    "k1_only": {PQ: [(SUMMARY_BASE, SUMMARY_K1_ONLY)]},
    "clip_partition": {SH: [(SETPART_BASE, SETPART_CLIP)]},
    "gold_full": {PQ: [(SUMMARY_BASE, SUMMARY_GOLD), (PVW_ARRAY_BASE, PVW_ARRAY_TYPED),
                       (PVW_INTERP_BASE, PVW_INTERP_PINNED)]},
    "exact_full": {PQ: [(SUMMARY_BASE, SUMMARY_EXACT_ENDS), (PVW_ARRAY_BASE, PVW_ARRAY_TYPED),
                        (PVW_INTERP_BASE, PVW_INTERP_PINNED)]},
    # 只修 process_val_weights、不改摘要阶段：用来区分两处缺陷各自的作用
    "pvw_only": {PQ: [(PVW_ARRAY_BASE, PVW_ARRAY_TYPED), (PVW_INTERP_BASE, PVW_INTERP_PINNED)]},
    # 第二批（09-29 同日追加）：完整的 higher 版本；gold 只补其中一处剩余缺陷
    "higher_full": {PQ: [(SUMMARY_BASE, SUMMARY_HIGHER), (PVW_ARRAY_BASE, PVW_ARRAY_TYPED),
                         (PVW_INTERP_BASE, PVW_INTERP_PINNED)]},
    "gold_pin_only": {PQ: [(SUMMARY_BASE, SUMMARY_GOLD), (PVW_INTERP_BASE, PVW_INTERP_PINNED)]},
    "gold_typed_only": {PQ: [(SUMMARY_BASE, SUMMARY_GOLD), (PVW_ARRAY_BASE, PVW_ARRAY_TYPED)]},
}


def main():
    base_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, edits in CANDIDATES.items():
        chunks = []
        for rel, reps in edits.items():
            old = (base_dir / Path(rel).name).read_text()
            new = old
            for a, b in reps:
                assert new.count(a) == 1, (name, rel, a[:60])
                new = new.replace(a, b)
            diff = difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                        fromfile=f"a/{rel}", tofile=f"b/{rel}", n=3)
            chunks.append(f"diff --git a/{rel} b/{rel}\n" + "".join(diff))
        (out_dir / f"{name}.patch").write_text("".join(chunks))
        print(name)


if __name__ == "__main__":
    main()
