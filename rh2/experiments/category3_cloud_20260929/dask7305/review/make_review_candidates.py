"""dask__dask-7305 独立复核者自造的候选补丁（私有对照用，不交给求解者）。

用法：python make_review_candidates.py <base 目录> <输出目录>
base 目录放镜像 c3keep/dask7305:src 中 /testbed 的两个原件（可用
`docker run --rm --network none c3keep/dask7305:src cat /testbed/dask/dataframe/<文件>` 取出）：
  partitionquantiles.py  sha256 248afefc0a63a31b8ae1b2d9b89d24fecb587bb6cfbaca037885936df226f26b
  shuffle.py             sha256 84bb142cbf0166c35f7325f4ff7ca146a719974814ab04a6af1870f56806b84d
每个候选都是对 base 源码的文本替换；替换前断言原文恰好出现一次。

候选按公开要求（大整数下 partition_quantiles 的最小值、最大值精确，结果有序、dtype 保持；
set_index 不丢行、每行落在自己的 divisions 区间）预先定性，不以 gold 为答案：
  错误：rv_pin_noclip、rv_interp_pin_noclip、rv_swallow_int64、rv_maxonly_threshold、
        rv_si_override、rv_sorted_assume、rv_len2
  合理：rv_lower_full、rv_exact_linear、rv_minmax_graph、rv_dup_branch
"""
import difflib
import hashlib
import sys
from pathlib import Path

PQ = "dask/dataframe/partitionquantiles.py"
SH = "dask/dataframe/shuffle.py"

# ---------------- base 原文片段 ----------------
SUMMARY_BASE = '''    interpolation = "linear"
    if is_categorical_dtype(data):
        data = data.codes
        interpolation = "nearest"
    vals, n = _percentile(data, qs, interpolation=interpolation)
    if interpolation == "linear" and np.issubdtype(data.dtype, np.integer):
        vals = np.round(vals).astype(data.dtype)
    vals_and_weights = percentiles_to_weights(qs, vals, length)
'''

PVW_ARRAY_BASE = '''    vals, weights = vals_and_weights
    vals = np.array(vals)
    weights = np.array(weights)
'''

PVW_INTERP_BASE = '''            q_weights = np.cumsum(weights)
            q_target = np.linspace(q_weights[0], q_weights[-1], npartitions + 1)
            rv = np.interp(q_target, q_weights, vals)
'''

PVW_UNDERSAMPLED_COND_BASE = '''        if np.issubdtype(vals.dtype, np.number) and not is_categorical_dtype(dtype):
            # Interpolate extra divisions
'''

PQ_LAST_BASE = '''    name3 = "re-quantiles-3-" + token
    last_dsk = {
        (name3, 0): (
            pd.Series,  # TODO: Use `type(df._meta)` when cudf adds `tolist()`
            (process_val_weights, merged_key, npartitions, (name0, 0)),
            qs,
            None,
            df.name,
        )
    }

    dsk = merge(df.dask, dtype_dsk, val_dsk, merge_dsk, last_dsk)
'''

SH_SET_INDEX_BASE = '''        mins = methods.tolist(mins)
        maxes = methods.tolist(maxes)

        empty_dataframe_detected = pd.isnull(divisions).all()
'''

# ---------------- 可复用的替换片段 ----------------
SUMMARY_GOLD = '''    interpolation = "linear"
    if is_categorical_dtype(data):
        data = data.codes
        interpolation = "nearest"
    elif np.issubdtype(data.dtype, np.integer):
        interpolation = "nearest"
    vals, n = _percentile(data, qs, interpolation=interpolation)
    vals_and_weights = percentiles_to_weights(qs, vals, length)
'''

# 与作者 gold_full 的 process_val_weights 两处修补相同（带 dtype 建数组；唯一值不足分支钉住两端并夹住中间值）
PVW_ARRAY_TYPED = '''    vals, weights = vals_and_weights
    if isinstance(dtype, np.dtype) and np.issubdtype(dtype, np.integer):
        vals = np.array(vals, dtype=dtype)
    else:
        vals = np.array(vals)
    weights = np.array(weights)
'''

PVW_INTERP_PIN_CLIP = '''            q_weights = np.cumsum(weights)
            q_target = np.linspace(q_weights[0], q_weights[-1], npartitions + 1)
            rv = np.interp(q_target, q_weights, vals)
            if np.issubdtype(vals.dtype, np.integer):
                lo, hi = int(vals[0]), int(vals[-1])
                inner = [min(max(int(x), lo), hi) for x in rv[1:-1]]
                rv = np.array([lo] + inner + [hi], dtype=vals.dtype)
'''


def summary_with(extra_cond_block):
    return SUMMARY_BASE.replace(
        '''        interpolation = "nearest"
    vals, n = _percentile''',
        '''        interpolation = "nearest"
''' + extra_cond_block + '''    vals, n = _percentile''',
    )


# ---------------- 错误候选 ----------------

# 只把摘要两端改成精确值（#6864 / 上游 CuPy 分支的写法），内部线性值经 float64 舍入后不夹住。
# 值很密（相邻差小于 float64 的间距）时，内部值会越过真实最大值，结果无序或端点错。
SUMMARY_PIN_NOCLIP = '''    interpolation = "linear"
    if is_categorical_dtype(data):
        data = data.codes
        interpolation = "nearest"
    vals, n = _percentile(data, qs, interpolation=interpolation)
    if interpolation == "linear" and np.issubdtype(data.dtype, np.integer):
        vals = np.round(vals).astype(data.dtype)
        # float64 cannot hold every large integer: keep the exact extremes
        if qs[0] == 0:
            vals[0] = data.min()
        if qs[-1] == 100:
            vals[-1] = data.max()
    vals_and_weights = percentiles_to_weights(qs, vals, length)
'''

# 唯一值不足分支：先转回整数 dtype，再只钉住两端；中间值不夹住。
PVW_INTERP_PIN_NOCLIP = '''            q_weights = np.cumsum(weights)
            q_target = np.linspace(q_weights[0], q_weights[-1], npartitions + 1)
            rv = np.interp(q_target, q_weights, vals)
            if np.issubdtype(vals.dtype, np.integer):
                # np.interp works in float64: restore the exact endpoints
                rv = rv.astype(vals.dtype)
                rv[0], rv[-1] = vals[0], vals[-1]
'''

# 吞掉错误：按 int64 建数组，≥ 2**63 时 OverflowError 被吞掉并静默退回 float64。
PVW_ARRAY_SWALLOW = '''    vals, weights = vals_and_weights
    if isinstance(dtype, np.dtype) and np.issubdtype(dtype, np.integer):
        try:
            vals = np.array(vals, dtype=np.int64)
        except OverflowError:
            vals = np.array(vals)
    else:
        vals = np.array(vals)
    weights = np.array(weights)
'''

# 值域阈值：只看最大值是否超过 2**53；全为大负数的分区仍走 float64 线性插值。
SUMMARY_MAXONLY = summary_with('''    elif np.issubdtype(data.dtype, np.integer) and data.max() > 2 ** 53:
        # float64 is exact below 2**53; above that pick existing values
        interpolation = "nearest"
''')

# 依赖顺序：按位置直接取分区里的第 k 个元素，默认分区已排序。
SUMMARY_SORTED_ASSUME = '''    interpolation = "linear"
    if is_categorical_dtype(data):
        data = data.codes
        interpolation = "nearest"
    elif np.issubdtype(data.dtype, np.integer):
        # take existing values instead of interpolating through float64
        idx = np.round(np.asarray(qs) / 100.0 * (len(data) - 1)).astype(int)
        vals = np.asarray(data)[idx]
        return percentiles_to_weights(qs, vals, length)
    vals, n = _percentile(data, qs, interpolation=interpolation)
    if interpolation == "linear" and np.issubdtype(data.dtype, np.integer):
        vals = np.round(vals).astype(data.dtype)
    vals_and_weights = percentiles_to_weights(qs, vals, length)
'''

# 示例拟合：只有分区不超过 2 行（题面原例的形态）时才改用 nearest。
SUMMARY_LEN2 = summary_with('''    elif np.issubdtype(data.dtype, np.integer) and len(data) <= 2:
        interpolation = "nearest"
''')

# 抑制症状：partition_quantiles 不动，只在 set_index 里用精确的逐分区 min/max 改写 divisions 两端。
SH_SET_INDEX_OVERRIDE = '''        mins = methods.tolist(mins)
        maxes = methods.tolist(maxes)

        if (
            pd.api.types.is_integer_dtype(index2.dtype)
            and len(divisions)
            and not pd.isnull(divisions).any()
        ):
            # use the exact minimum and maximum for the outer divisions
            known_mins = [m for m in mins if not pd.isnull(m)]
            known_maxes = [m for m in maxes if not pd.isnull(m)]
            if known_mins and known_maxes:
                divisions[0] = min(known_mins)
                divisions[-1] = max(known_maxes)

        empty_dataframe_detected = pd.isnull(divisions).all()
'''

# ---------------- 合理但与 gold、三份正对照都不同的实现 ----------------

SUMMARY_LOWER = summary_with('''    elif np.issubdtype(data.dtype, np.integer):
        interpolation = "lower"
''')

# 保留线性插值，但用 Python 整数精确计算（2**32 定点权重），结果必在相邻两个样本值之间。
SUMMARY_EXACT_LINEAR = '''    interpolation = "linear"
    if is_categorical_dtype(data):
        data = data.codes
        interpolation = "nearest"
    elif np.issubdtype(data.dtype, np.integer):
        # Linear interpolation computed with Python integers: float64 cannot
        # hold every large integer.
        s = np.sort(np.asarray(data))
        pos = np.asarray(qs, dtype=float) / 100.0 * (len(s) - 1)
        lo_i = np.floor(pos).astype(np.intp)
        hi_i = np.minimum(lo_i + 1, len(s) - 1)
        out = []
        for i, j, f in zip(lo_i.tolist(), hi_i.tolist(), (pos - lo_i).tolist()):
            a, b = int(s[i]), int(s[j])
            w = int(round(min(max(f, 0.0), 1.0) * (1 << 32)))
            out.append(a + ((b - a) * w + (1 << 31)) // (1 << 32))
        vals = np.array(out, dtype=s.dtype)
        return percentiles_to_weights(qs, vals, length)
    vals, n = _percentile(data, qs, interpolation=interpolation)
    if interpolation == "linear" and np.issubdtype(data.dtype, np.integer):
        vals = np.round(vals).astype(data.dtype)
    vals_and_weights = percentiles_to_weights(qs, vals, length)
'''

PVW_INTERP_EXACT = '''            q_weights = np.cumsum(weights)
            q_target = np.linspace(q_weights[0], q_weights[-1], npartitions + 1)
            if np.issubdtype(vals.dtype, np.integer):
                # exact integer interpolation between neighbouring summary values
                idx = np.searchsorted(q_weights, q_target, side="right") - 1
                idx = np.clip(idx, 0, len(vals) - 1)
                out = []
                for t, i in zip(q_target.tolist(), idx.tolist()):
                    if i >= len(vals) - 1:
                        out.append(int(vals[-1]))
                        continue
                    a, b = int(vals[i]), int(vals[i + 1])
                    wa, wb = float(q_weights[i]), float(q_weights[i + 1])
                    f = 0.0 if wb == wa else (t - wa) / (wb - wa)
                    w = int(round(min(max(f, 0.0), 1.0) * (1 << 32)))
                    out.append(a + ((b - a) * w + (1 << 31)) // (1 << 32))
                rv = np.array(out, dtype=vals.dtype)
            else:
                rv = np.interp(q_target, q_weights, vals)
'''

# 摘要与合并都不动（base 的线性近似），在图里另算每个分区的精确 min/max，最后钉住两端、夹住并排序。
PQ_LAST_MINMAX = '''    name3 = "re-quantiles-3-" + token
    name_mm = "re-quantiles-minmax-" + token
    mm_dsk = {(name_mm, i): (_exact_min_max, key) for i, key in enumerate(df_keys)}
    last_dsk = {
        (name3, 0): (
            pd.Series,  # TODO: Use `type(df._meta)` when cudf adds `tolist()`
            (
                _pin_min_max,
                (process_val_weights, merged_key, npartitions, (name0, 0)),
                sorted(mm_dsk),
            ),
            qs,
            None,
            df.name,
        )
    }

    dsk = merge(df.dask, dtype_dsk, val_dsk, merge_dsk, mm_dsk, last_dsk)
'''

MINMAX_HELPERS_ANCHOR = '''def dtype_info(df):
'''
MINMAX_HELPERS = '''def _exact_min_max(s):
    """Exact (min, max) of an integer partition as Python ints, else None"""
    dtype = getattr(s, "dtype", None)
    if len(s) and isinstance(dtype, np.dtype) and np.issubdtype(dtype, np.integer):
        return int(s.min()), int(s.max())
    return None


def _pin_min_max(rv, min_maxes):
    """Replace approximate ends by the exact global minimum and maximum"""
    min_maxes = [x for x in min_maxes if x is not None]
    if (
        not min_maxes
        or not isinstance(rv, np.ndarray)
        or not np.issubdtype(rv.dtype, np.integer)
    ):
        return rv
    lo = min(x[0] for x in min_maxes)
    hi = max(x[1] for x in min_maxes)
    out = sorted(min(max(int(v), lo), hi) for v in rv.tolist())
    out[0], out[-1] = lo, hi
    return np.array(out, dtype=rv.dtype)


def dtype_info(df):
'''

# 唯一值不足时整数不再插值，改走“重复已有值”的分支（与非数值类型相同）。
PVW_UNDERSAMPLED_COND_DUP = '''        if (
            np.issubdtype(vals.dtype, np.number)
            and not np.issubdtype(vals.dtype, np.integer)
            and not is_categorical_dtype(dtype)
        ):
            # Interpolate extra divisions
'''


def rep(text, old, new):
    assert text.count(old) == 1, (old[:80], text.count(old))
    return text.replace(old, new)


def build(base_pq, base_sh):
    c = {}
    pvw_full = lambda t: rep(rep(t, PVW_ARRAY_BASE, PVW_ARRAY_TYPED), PVW_INTERP_BASE, PVW_INTERP_PIN_CLIP)  # noqa: E731

    c["rv_pin_noclip"] = {PQ: pvw_full(rep(base_pq, SUMMARY_BASE, SUMMARY_PIN_NOCLIP))}
    c["rv_interp_pin_noclip"] = {PQ: rep(rep(rep(base_pq, SUMMARY_BASE, SUMMARY_GOLD), PVW_ARRAY_BASE, PVW_ARRAY_TYPED), PVW_INTERP_BASE, PVW_INTERP_PIN_NOCLIP)}
    c["rv_swallow_int64"] = {PQ: rep(rep(rep(base_pq, SUMMARY_BASE, SUMMARY_GOLD), PVW_ARRAY_BASE, PVW_ARRAY_SWALLOW), PVW_INTERP_BASE, PVW_INTERP_PIN_CLIP)}
    c["rv_maxonly_threshold"] = {PQ: pvw_full(rep(base_pq, SUMMARY_BASE, SUMMARY_MAXONLY))}
    c["rv_si_override"] = {SH: rep(base_sh, SH_SET_INDEX_BASE, SH_SET_INDEX_OVERRIDE)}
    c["rv_sorted_assume"] = {PQ: pvw_full(rep(base_pq, SUMMARY_BASE, SUMMARY_SORTED_ASSUME))}
    c["rv_len2"] = {PQ: pvw_full(rep(base_pq, SUMMARY_BASE, SUMMARY_LEN2))}

    c["rv_lower_full"] = {PQ: pvw_full(rep(base_pq, SUMMARY_BASE, SUMMARY_LOWER))}
    c["rv_exact_linear"] = {PQ: rep(rep(rep(base_pq, SUMMARY_BASE, SUMMARY_EXACT_LINEAR), PVW_ARRAY_BASE, PVW_ARRAY_TYPED), PVW_INTERP_BASE, PVW_INTERP_EXACT)}
    c["rv_minmax_graph"] = {PQ: rep(rep(base_pq, PQ_LAST_BASE, PQ_LAST_MINMAX), MINMAX_HELPERS_ANCHOR, MINMAX_HELPERS)}
    c["rv_dup_branch"] = {PQ: rep(rep(rep(base_pq, SUMMARY_BASE, SUMMARY_GOLD), PVW_ARRAY_BASE, PVW_ARRAY_TYPED), PVW_UNDERSAMPLED_COND_BASE, PVW_UNDERSAMPLED_COND_DUP)}
    return c


def main():
    base_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    base_pq = (base_dir / "partitionquantiles.py").read_text()
    base_sh = (base_dir / "shuffle.py").read_text()
    assert hashlib.sha256(base_pq.encode()).hexdigest().startswith("248afefc0a63"), "unexpected base partitionquantiles.py"
    assert hashlib.sha256(base_sh.encode()).hexdigest().startswith("84bb142cbf01"), "unexpected base shuffle.py"
    out_dir.mkdir(parents=True, exist_ok=True)
    base = {PQ: base_pq, SH: base_sh}
    for name, files in build(base_pq, base_sh).items():
        chunks = []
        for path, new in files.items():
            old = base[path]
            diff = difflib.unified_diff(old.splitlines(True), new.splitlines(True), f"a/{path}", f"b/{path}")
            chunks.append(f"diff --git a/{path} b/{path}\n" + "".join(diff))
        data = "".join(chunks)
        (out_dir / f"{name}.patch").write_text(data)
        print(name, hashlib.sha256(data.encode()).hexdigest())


if __name__ == "__main__":
    main()
