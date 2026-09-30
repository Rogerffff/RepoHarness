"""生成 dask__dask-8597 修订版测试补丁草案（R-c），并写出 --materials JSON。

用法：python make_revised_test.py <base test_slicing.py> <原 test_patch 文件> <输出目录>
测试 ID 与 F2P／P2P 分组不变：只改 F2P test_slice_array_null_dimension 的函数体（原来的 3 行原样保留在最前面）。
"""
import difflib
import hashlib
import json
import sys
from pathlib import Path

REL = "dask/array/tests/test_slicing.py"
IID = "dask__dask-8597"
VERSION = "c3-dask8597-rc-v1"

ORIG_F2P = '''

def test_slice_array_null_dimension():
    array = da.from_array(np.zeros((3, 0)))
    expected = np.zeros((3, 0))[[0]]
    assert_eq(array[[0]], expected)
'''

NEW_F2P = '''

def test_slice_array_null_dimension():
    array = da.from_array(np.zeros((3, 0)))
    expected = np.zeros((3, 0))[[0]]
    assert_eq(array[[0]], expected)

    # The same holds beyond the example: a list index along any axis of an
    # array whose other axes include one of length zero (any position, dtype
    # and chunking; several, repeated, unsorted or negative indices) gives
    # NumPy's result as a dask array, whatever the documented setting of
    # ``array.slicing.split-large-chunks``.  Empty chunks are never large, so
    # no warning either (warnings from dask modules fail this test suite).
    cases = [
        (np.zeros((3, 0)), "auto", ([0],)),
        (np.zeros((0, 3)), "auto", (slice(None), [2, 0, 2])),
        (np.zeros((6, 0, 4), dtype="i4"), (2, -1, 2), ([5, 0, 5, -1, 3],)),
        (np.zeros((3, 0)), "auto", ([0, 1, 2] * 40,)),
    ]
    for split in [None, False, True]:
        with dask.config.set({"array.slicing.split-large-chunks": split}):
            for x, chunks, index in cases:
                result = da.from_array(x, chunks=chunks)[index]
                assert isinstance(result, da.Array)
                assert_eq(result, x[index])

    # The documented default warning for really large chunks still works.
    with dask.config.set({"array.chunk-size": "0.1Mb"}):
        a = np.arange(2 * 128 * 128, dtype="int64").reshape(2, 128, 128)
        arr = da.from_array(a, chunks=(1, 128, 128))
        with pytest.warns(da.PerformanceWarning):
            arr[[0] + [1] * 11]
'''

REASON = (
    "T2c (v1 section 4 step 2, strict D1): the only F2P uses the issue example literally "
    "(np.zeros((3, 0)), index [0], axis 0, default config) and no P2P indexes an array whose other axes "
    "include a zero-length one. Step 3/4: split_only (threshold computed only when split-large-chunks is "
    "True; still divides by zero under True and drops the documented default large-chunk warning), "
    "last_axis_only, axis0_only, single_block, float_blocks, return_numpy and cap_one all score 1 on the "
    "original materials. R-c: same F2P id; original 3 lines kept; adds four non-example instances "
    "(zero axis first/middle/last, index along axis 0 or 1, int32, multi-chunk, repeated/unsorted/negative, "
    "120-row index) under split-large-chunks None/False/True with an explicit dask-Array type check, and "
    "keeps the documented default PerformanceWarning for a really large chunk (docs/source/array-slicing.rst, "
    "dask.yaml 'Warns by default', public test_getitem_avoids_large_chunks which is not in P2P)."
)


def main():
    base_path, orig_patch_path, out_dir = map(Path, sys.argv[1:4])
    out_dir.mkdir(parents=True, exist_ok=True)
    base = base_path.read_text()
    assert base.endswith("    assert_eq(actual, expected)\n")
    orig_patch = orig_patch_path.read_text()
    # 原补丁只在文件末尾追加 F2P；逐字核对，保证修订版与原版只差在函数体
    orig_new = base + ORIG_F2P
    new = base + NEW_F2P
    for line in ORIG_F2P.splitlines():
        if line:
            assert ("+" + line) in orig_patch.splitlines(), line
    diff = difflib.unified_diff(base.splitlines(keepends=True), new.splitlines(keepends=True), f"a/{REL}", f"b/{REL}", n=3)
    patch = f"diff --git a/{REL} b/{REL}\n" + "".join(diff)
    (out_dir / "revised_test_v1.patch").write_text(patch)
    (out_dir / "revised_test_v1.py.tail").write_text(NEW_F2P)
    rev_sha = hashlib.sha256(patch.encode()).hexdigest()
    materials = {
        "version": VERSION,
        "tasks": {IID: {
            "original_patch_sha256": hashlib.sha256(orig_patch.encode()).hexdigest(),
            "test_patch": patch,
            "revised_patch_sha256": rev_sha,
            "reason": REASON,
            "positive_control": "gold (unchanged upstream fix); reasonable non-gold controls clamp1, lazy_threshold, "
                                "errstate_catch, eager_empty (author-written, to be verified by others)",
        }},
    }
    (out_dir / "materials_revised_v1.json").write_text(json.dumps(materials, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"revised_patch_sha256": rev_sha, "orig_new_equals_patch_tail": orig_new.endswith(ORIG_F2P)}))


if __name__ == "__main__":
    main()
