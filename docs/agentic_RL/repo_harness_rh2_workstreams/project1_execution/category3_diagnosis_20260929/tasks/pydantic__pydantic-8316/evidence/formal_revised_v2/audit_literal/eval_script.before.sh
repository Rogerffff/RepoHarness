#!/bin/bash
set -xo pipefail
source /opt/miniconda3/bin/activate
conda activate testbed
cd /testbed
git config --global --add safe.directory /testbed
git status
git show
git -c core.fileMode=false diff 20c0c6d9219e29a95f5e1cadeb05ec39d8c15c24
git checkout 20c0c6d9219e29a95f5e1cadeb05ec39d8c15c24 tests/test_utils.py
git apply -v - <<'EOF_RH2_V2_TEST_PATCH'
diff --git a/tests/test_utils.py b/tests/test_utils.py
--- a/tests/test_utils.py
+++ b/tests/test_utils.py
@@ -529,6 +529,7 @@
         ('Camel2Snake', 'camel_2_snake'),
         ('_CamelToSnake', '_camel_to_snake'),
         ('CamelToSnake_', 'camel_to_snake_'),
+        ('CAMELToSnake', 'camel_to_snake'),
         ('__CamelToSnake__', '__camel_to_snake__'),
         ('Camel2', 'camel_2'),
         ('Camel2_', 'camel_2_'),
@@ -540,6 +541,17 @@
 )
 def test_camel2snake(value: str, result: str) -> None:
     assert to_snake(value) == result
+    if value == 'CAMELToSnake':
+        # an acronym followed by a capitalized word is split wherever it appears, not only at the start
+        assert to_snake('HTTPResponse') == 'http_response'
+        assert to_snake('getHTTPResponseCode') == 'get_http_response_code'
+        assert to_snake('userIDToken') == 'user_id_token'
+        assert to_snake('XMLToJSONConverter') == 'xml_to_json_converter'
+        # ... also next to underscores and digits, which are handled as for the other inputs
+        assert to_snake('__HTTPResponse__') == '__http_response__'
+        assert to_snake('base64URLEncode') == 'base_64_url_encode'
+        # a trailing acronym stays one word
+        assert to_snake('parseURL') == 'parse_url'
 
 
 @pytest.mark.parametrize(

EOF_RH2_V2_TEST_PATCH
echo RH2_PHASE_START=install
echo "RH2_TS_INSTALL_START=$(date +%s.%N)"
set -E; trap 'echo "RH2_INSTALL_CMD_FAILED=$? ${BASH_COMMAND}"' ERR
export PATH="$HOME/.local/bin:$PATH"; pdm add pre-commit; make install;
RH2_INSTALL_RC=$?
trap - ERR; set +E
echo "RH2_INSTALL_RC=$RH2_INSTALL_RC"
echo "RH2_TS_INSTALL_END=$(date +%s.%N)"
echo RH2_PHASE_END=install
echo "RH2_TS_TEST_START=$(date +%s.%N)"
: '>>>>> Start Test Output'
pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_utils.py
RH2_TEST_RC=$?
: '>>>>> End Test Output'
echo "RH2_TEST_RC=$RH2_TEST_RC"
echo "RH2_TS_TEST_END=$(date +%s.%N)"
git checkout 20c0c6d9219e29a95f5e1cadeb05ec39d8c15c24 tests/test_utils.py
