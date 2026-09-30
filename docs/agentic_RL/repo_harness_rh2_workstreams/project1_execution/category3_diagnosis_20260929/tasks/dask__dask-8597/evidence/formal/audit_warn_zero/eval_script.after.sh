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
@@ -1065,3 +1065,9 @@ def test_slice_array_3d_with_bool_numpy_array():
     actual = array[mask].compute()
     expected = np.arange(13, 24)
     assert_eq(actual, expected)
+
+
+def test_slice_array_null_dimension():
+    array = da.from_array(np.zeros((3, 0)))
+    expected = np.zeros((3, 0))[[0]]
+    assert_eq(array[[0]], expected)

EOF_RH2_V2_TEST_PATCH
echo RH2_PHASE_START=install
echo "RH2_TS_INSTALL_START=$(date +%s.%N)"
set -E; trap 'echo "RH2_INSTALL_CMD_FAILED=$? ${BASH_COMMAND}"' ERR
rh2_compat_install() {
 python -m pip install --no-index --find-links=/opt/rh2/compat-wheels --no-deps pytest==7.4.4 || return $?
 python -I -c 'import importlib.metadata as m,json; print("RH2_COMPAT_VERSIONS="+json.dumps({x:m.version(x) for x in ['"'"'pytest'"'"']}))'
 python -m pip install --no-deps -e .
 local original_rc=$?
 python -I -c 'import importlib.metadata as m,json; print("RH2_COMPAT_VERSIONS="+json.dumps({x:m.version(x) for x in ['"'"'pytest'"'"']}))'
 return "$original_rc"
}
rh2_compat_install
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
