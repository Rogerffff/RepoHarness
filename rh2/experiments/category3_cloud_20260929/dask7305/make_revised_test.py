"""生成 dask__dask-7305 修订版测试补丁草案（R-b＋R-c），并写出 --materials JSON。

用法：python make_revised_test.py <base test_shuffle.py> <原 test_patch 文件> <输出目录>
测试 ID 与 F2P／P2P 分组不变：只改 F2P test_set_index_interpolate 的函数体，新增一个模块级 helper；
P2P test_set_index_interpolate_large_uint 与原补丁逐字相同。
"""
import difflib
import hashlib
import json
import sys
from pathlib import Path

REL = "dask/dataframe/tests/test_shuffle.py"

OLD_F2P = '''def test_set_index_interpolate():
    df = pd.DataFrame({"x": [4, 1, 1, 3, 3], "y": [1.0, 1, 1, 1, 2]})
    d = dd.from_pandas(df, 2)

    d1 = d.set_index("x", npartitions=3)
    assert d1.npartitions == 3
    assert set(d1.divisions) == set([1, 2, 3, 4])

    d2 = d.set_index("y", npartitions=3)
    assert d2.divisions[0] == 1.0
    assert 1.0 < d2.divisions[1] < d2.divisions[2] < 2.0
    assert d2.divisions[3] == 2.0
'''

NEW_F2P = '''def _assert_exact_int_divisions(values, dtype, npartitions_in, npartitions_out):
    # #7304: partition_quantiles and set_index keep the exact minimum and
    # maximum of large integers.  Compare as Python ints: numpy compares uint64
    # with int through float64, which hides off-by-one errors.
    from dask.dataframe.partitionquantiles import partition_quantiles

    df = pd.DataFrame({"x": np.array(values, dtype=dtype)})
    ddf = dd.from_pandas(df, npartitions=npartitions_in, sort=False)
    lo, hi = min(values), max(values)

    qs = partition_quantiles(ddf.x, npartitions=npartitions_out).compute()
    assert qs.dtype == np.dtype(dtype)
    got = [int(v) for v in qs]
    assert got[0] == lo
    assert got[-1] == hi
    assert got == sorted(got)

    d1 = ddf.set_index("x", npartitions=npartitions_out)
    divisions = [int(v) for v in d1.divisions]
    assert divisions[0] == lo
    assert divisions[-1] == hi
    parts = [d1.get_partition(i).compute() for i in range(d1.npartitions)]
    for i, part in enumerate(parts):
        if len(part):
            assert divisions[i] <= int(part.index.min())
            if i < len(parts) - 1:
                assert int(part.index.max()) < divisions[i + 1]
            else:
                assert int(part.index.max()) <= divisions[i + 1]
    assert sorted(int(v) for part in parts for v in part.index) == sorted(values)


def test_set_index_interpolate():
    df = pd.DataFrame({"x": [4, 1, 1, 3, 3], "y": [1.0, 1, 1, 1, 2]})
    d = dd.from_pandas(df, 2)

    d1 = d.set_index("x", npartitions=3)
    assert d1.npartitions == 3
    # Inner divisions are approximate and may differ between implementations;
    # the ends are the exact minimum and maximum, the divisions are sorted
    # integers and every row lands in its own division range.
    assert d1.divisions[0] == 1
    assert d1.divisions[-1] == 4
    assert list(d1.divisions) == sorted(d1.divisions)
    assert all(np.issubdtype(type(x), np.integer) for x in d1.divisions)
    assert_eq(d1, df.set_index("x"))

    d2 = d.set_index("y", npartitions=3)
    assert d2.divisions[0] == 1.0
    assert 1.0 < d2.divisions[1] < d2.divisions[2] < 2.0
    assert d2.divisions[3] == 2.0

    # Large integers (#7304), for several numbers of output partitions and with
    # unsorted input whose minimum sits in the last partition.
    big = 612509347682975743
    issue = [big, 616762138058293247]
    order = [(i * 7919) % 200 for i in range(200)][::-1]
    _assert_exact_int_divisions(issue, "uint64", 1, 1)
    _assert_exact_int_divisions(issue, "uint64", 1, 3)
    _assert_exact_int_divisions([big + 997 * k for k in order], "uint64", 4, 4)
    _assert_exact_int_divisions([-big + 6125093476829757 * k for k in order], "int64", 4, 4)
    _assert_exact_int_divisions([big + 89000000000000001 * k for k in order], "uint64", 4, 4)
'''

OLD_AFTER_INT = '''    assert all(np.issubdtype(type(x), np.integer) for x in d1.divisions)


def test_set_index_timezone():
'''

# 与原 test_patch 新增的 P2P 函数逐字相同
NEW_AFTER_INT = '''    assert all(np.issubdtype(type(x), np.integer) for x in d1.divisions)


def test_set_index_interpolate_large_uint():
    """This test is for #7304"""
    df = pd.DataFrame(
        {"x": np.array([612509347682975743, 616762138058293247], dtype=np.uint64)}
    )
    d = dd.from_pandas(df, 1)

    d1 = d.set_index("x", npartitions=1)
    assert d1.npartitions == 1
    assert set(d1.divisions) == set([612509347682975743, 616762138058293247])


def test_set_index_timezone():
'''


def main():
    base_path, orig_patch_path, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    old = base_path.read_text()
    new = old
    for a, b in ((OLD_F2P, NEW_F2P), (OLD_AFTER_INT, NEW_AFTER_INT)):
        assert new.count(a) == 1, a[:60]
        new = new.replace(a, b)
    # P2P 函数必须与原补丁新增的函数逐字一致
    orig_patch = orig_patch_path.read_text()
    p2p_added = "".join(line[1:] + "\n" for line in orig_patch.splitlines()
                        if line.startswith("+") and not line.startswith("+++"))
    assert "def test_set_index_interpolate_large_uint():" in p2p_added
    large_uint_body = p2p_added[p2p_added.index("def test_set_index_interpolate_large_uint"):]
    assert large_uint_body.strip() in new
    diff = difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                fromfile=f"a/{REL}", tofile=f"b/{REL}", n=3)
    patch = f"diff --git a/{REL} b/{REL}\n" + "".join(diff)
    out.mkdir(parents=True, exist_ok=True)
    (out / "revised_test_v1.patch").write_text(patch)
    materials = {
        "version": "c3-dask7305-exact-ends-v1",
        "tasks": {"dask__dask-7305": {
            "original_patch_sha256": hashlib.sha256(orig_patch.encode()).hexdigest(),
            "test_patch": patch,
            "revised_patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
            "reason": ("T2a/T2b: no reference assertion checks the partition_quantiles endpoints "
                       "(large_uint P2P goes through the single-partition min/max shortcut and passes on base); "
                       "T1: F2P pins the approximate inner divisions {1,2,4}, contradicting the visible old test "
                       "{1,2,3,4} and rejecting exact-endpoint fixes; G1: gold still loses the endpoints when "
                       "partition_quantiles is under-sampled (np.interp) and for uint64 spanning 2**63 "
                       "(untyped np.array), and set_index then drops rows. R-b relaxes the inner divisions to "
                       "behaviour; R-c adds exact-endpoint and row-placement checks for the issue data at 1 and 3 "
                       "output partitions, 200 unsorted large uint64, large int64 and uint64 spanning 2**63."),
            "positive_control": "gold_full (gold + typed process_val_weights + exact endpoints in the "
                                "under-sampled branch); second: exact_full. Both pending independent verification.",
        }},
    }
    (out / "materials_revised_v1.json").write_text(json.dumps(materials, ensure_ascii=False, indent=1) + "\n")
    print(materials["tasks"]["dask__dask-7305"]["revised_patch_sha256"])


if __name__ == "__main__":
    main()
