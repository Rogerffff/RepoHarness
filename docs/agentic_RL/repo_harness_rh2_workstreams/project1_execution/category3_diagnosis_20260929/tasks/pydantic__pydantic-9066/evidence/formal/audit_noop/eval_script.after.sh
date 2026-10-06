#!/bin/bash
set -xo pipefail
source /opt/miniconda3/bin/activate
conda activate testbed
cd /testbed
git config --global --add safe.directory /testbed
git status
git show
git -c core.fileMode=false diff a3b7214a1d6ac8e32c29e9d4436ea6a9e253ead7
git checkout a3b7214a1d6ac8e32c29e9d4436ea6a9e253ead7 tests/test_json_schema.py
git apply -v - <<'EOF_RH2_V2_TEST_PATCH'
diff --git a/tests/test_json_schema.py b/tests/test_json_schema.py
--- a/tests/test_json_schema.py
+++ b/tests/test_json_schema.py
@@ -5995,3 +5995,38 @@ class Model(BaseModel):
     assert Model.model_fields['a'].is_required()
     assert Model.model_fields['b'].is_required()
     assert Model.model_fields['c'].is_required()
+
+
+@pytest.mark.parametrize(
+    'field_type,default_value,expected_schema',
+    [
+        (
+            IPvAnyAddress,
+            IPv4Address('127.0.0.1'),
+            {
+                'properties': {
+                    'field': {'default': '127.0.0.1', 'format': 'ipvanyaddress', 'title': 'Field', 'type': 'string'}
+                },
+                'title': 'Model',
+                'type': 'object',
+            },
+        ),
+        (
+            IPvAnyAddress,
+            IPv6Address('::1'),
+            {
+                'properties': {
+                    'field': {'default': '::1', 'format': 'ipvanyaddress', 'title': 'Field', 'type': 'string'}
+                },
+                'title': 'Model',
+                'type': 'object',
+            },
+        ),
+    ],
+)
+def test_default_value_encoding(field_type, default_value, expected_schema):
+    class Model(BaseModel):
+        field: field_type = default_value
+
+    schema = Model.model_json_schema()
+    assert schema == expected_schema

EOF_RH2_V2_TEST_PATCH
echo RH2_PHASE_START=install
echo "RH2_TS_INSTALL_START=$(date +%s.%N)"
set -E; trap 'echo "RH2_INSTALL_CMD_FAILED=$? ${BASH_COMMAND}"' ERR
rh2_recipe_install() {
  python -m pip install -e . || return $?
  python -I - <<'RH2_TEST_REQUIREMENTS'
import pathlib, tomli
p = tomli.loads(pathlib.Path('/testbed/pyproject.toml').read_text())
groups = p.get('tool', {}).get('pdm', {}).get('dev-dependencies', {})
requirements = [x for name in ('testing', 'testing-extra') for x in groups.get(name, [])]
pathlib.Path('/tmp/rh2-envrepair-testing-reqs.txt').write_text('\n'.join(requirements) + '\n')
RH2_TEST_REQUIREMENTS
  [ "$?" = 0 ] || return 1
  python -m pip install -r /tmp/rh2-envrepair-testing-reqs.txt
}
rh2_recipe_install
RH2_INSTALL_RC=$?
trap - ERR; set +E
echo "RH2_INSTALL_RC=$RH2_INSTALL_RC"
echo "RH2_TS_INSTALL_END=$(date +%s.%N)"
echo RH2_PHASE_END=install
echo "RH2_TS_TEST_START=$(date +%s.%N)"
: '>>>>> Start Test Output'
pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_json_schema.py
RH2_TEST_RC=$?
: '>>>>> End Test Output'
echo "RH2_TEST_RC=$RH2_TEST_RC"
echo "RH2_TS_TEST_END=$(date +%s.%N)"
git checkout a3b7214a1d6ac8e32c29e9d4436ea6a9e253ead7 tests/test_json_schema.py
