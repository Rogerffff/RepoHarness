#!/bin/bash
set -xo pipefail
source /opt/miniconda3/bin/activate
conda activate testbed
cd /testbed
git config --global --add safe.directory /testbed
git status
git show
git -c core.fileMode=false diff aa801de0f42716d977051f9abb9da2c9399da05c
git checkout aa801de0f42716d977051f9abb9da2c9399da05c dask/tests/test_base.py
git apply -v - <<'EOF_RH2_V2_TEST_PATCH'
diff --git a/dask/tests/test_base.py b/dask/tests/test_base.py
--- a/dask/tests/test_base.py
+++ b/dask/tests/test_base.py
@@ -7,6 +7,7 @@
 import time
 from collections import OrderedDict
 from concurrent.futures import Executor
+from enum import Enum, Flag, IntEnum, IntFlag
 from operator import add, mul
 from typing import Union
 
@@ -425,6 +426,16 @@ def test_tokenize_ordered_dict():
     assert tokenize(a) != tokenize(c)
 
 
+@pytest.mark.parametrize("enum_type", [Enum, IntEnum, IntFlag, Flag])
+def test_tokenize_enum(enum_type):
+    class Color(enum_type):
+        RED = 1
+        BLUE = 2
+
+    assert tokenize(Color.RED) == tokenize(Color.RED)
+    assert tokenize(Color.RED) != tokenize(Color.BLUE)
+
+
 ADataClass = dataclasses.make_dataclass("ADataClass", [("a", int)])
 BDataClass = dataclasses.make_dataclass("BDataClass", [("a", Union[int, float])])  # type: ignore
 

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
pytest -n0 -rA  --color=no dask/tests/test_base.py
RH2_TEST_RC=$?
: '>>>>> End Test Output'
echo "RH2_TEST_RC=$RH2_TEST_RC"
echo "RH2_TS_TEST_END=$(date +%s.%N)"
git checkout aa801de0f42716d977051f9abb9da2c9399da05c dask/tests/test_base.py
