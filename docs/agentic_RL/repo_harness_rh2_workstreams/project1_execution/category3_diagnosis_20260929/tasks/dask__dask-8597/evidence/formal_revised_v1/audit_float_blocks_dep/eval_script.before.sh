#!/bin/bash
set -xo pipefail
source /opt/miniconda3/bin/activate
conda activate testbed
cd /testbed
git config --global --add safe.directory /testbed
git status
git show
git -c core.fileMode=false diff c1c88f066672c0b216fc24862a2b36a0a9fb4e22
git checkout c1c88f066672c0b216fc24862a2b36a0a9fb4e22 dask/array/tests/test_slicing.py
git apply -v - <<'EOF_RH2_V2_TEST_PATCH'
diff --git a/dask/array/tests/test_slicing.py b/dask/array/tests/test_slicing.py
--- a/dask/array/tests/test_slicing.py
+++ b/dask/array/tests/test_slicing.py
@@ -1065,3 +1065,35 @@
     actual = array[mask].compute()
     expected = np.arange(13, 24)
     assert_eq(actual, expected)
+
+
+def test_slice_array_null_dimension():
+    array = da.from_array(np.zeros((3, 0)))
+    expected = np.zeros((3, 0))[[0]]
+    assert_eq(array[[0]], expected)
+
+    # The same holds beyond the example: a list index along any axis of an
+    # array whose other axes include one of length zero (any position, dtype
+    # and chunking; several, repeated, unsorted or negative indices) gives
+    # NumPy's result as a dask array, whatever the documented setting of
+    # ``array.slicing.split-large-chunks``.  Empty chunks are never large, so
+    # no warning either (warnings from dask modules fail this test suite).
+    cases = [
+        (np.zeros((3, 0)), "auto", ([0],)),
+        (np.zeros((0, 3)), "auto", (slice(None), [2, 0, 2])),
+        (np.zeros((6, 0, 4), dtype="i4"), (2, -1, 2), ([5, 0, 5, -1, 3],)),
+        (np.zeros((3, 0)), "auto", ([0, 1, 2] * 40,)),
+    ]
+    for split in [None, False, True]:
+        with dask.config.set({"array.slicing.split-large-chunks": split}):
+            for x, chunks, index in cases:
+                result = da.from_array(x, chunks=chunks)[index]
+                assert isinstance(result, da.Array)
+                assert_eq(result, x[index])
+
+    # The documented default warning for really large chunks still works.
+    with dask.config.set({"array.chunk-size": "0.1Mb"}):
+        a = np.arange(2 * 128 * 128, dtype="int64").reshape(2, 128, 128)
+        arr = da.from_array(a, chunks=(1, 128, 128))
+        with pytest.warns(da.PerformanceWarning):
+            arr[[0] + [1] * 11]

EOF_RH2_V2_TEST_PATCH
echo RH2_PHASE_START=install
echo "RH2_TS_INSTALL_START=$(date +%s.%N)"
set -E; trap 'echo "RH2_INSTALL_CMD_FAILED=$? ${BASH_COMMAND}"' ERR
python -m pip install --no-deps -e .
RH2_INSTALL_RC=$?
trap - ERR; set +E
echo "RH2_INSTALL_RC=$RH2_INSTALL_RC"
echo "RH2_TS_INSTALL_END=$(date +%s.%N)"
echo RH2_PHASE_END=install
echo "RH2_TS_TEST_START=$(date +%s.%N)"
: '>>>>> Start Test Output'
pytest -n0 -rA  --color=no dask/array/tests/test_slicing.py
RH2_TEST_RC=$?
: '>>>>> End Test Output'
echo "RH2_TEST_RC=$RH2_TEST_RC"
echo "RH2_TS_TEST_END=$(date +%s.%N)"
git checkout c1c88f066672c0b216fc24862a2b36a0a9fb4e22 dask/array/tests/test_slicing.py
