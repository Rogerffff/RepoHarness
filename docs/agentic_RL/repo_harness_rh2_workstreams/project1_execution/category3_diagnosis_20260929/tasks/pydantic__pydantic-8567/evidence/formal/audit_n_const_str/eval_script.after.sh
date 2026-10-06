#!/bin/bash
set -xo pipefail
source /opt/miniconda3/bin/activate
conda activate testbed
cd /testbed
git config --global --add safe.directory /testbed
git status
git show
git -c core.fileMode=false diff 8060fa1cff965850e5e08a67ca73d5272dcdcf9f
git checkout 8060fa1cff965850e5e08a67ca73d5272dcdcf9f tests/test_validators.py
git apply -v - <<'EOF_RH2_V2_TEST_PATCH'
diff --git a/tests/test_validators.py b/tests/test_validators.py
--- a/tests/test_validators.py
+++ b/tests/test_validators.py
@@ -20,6 +20,7 @@
     ConfigDict,
     Field,
     GetCoreSchemaHandler,
+    PlainSerializer,
     PydanticDeprecatedSince20,
     PydanticUserError,
     TypeAdapter,
@@ -2810,3 +2811,19 @@ def value_b_validator(cls, value):
             'ctx': {'error': IsInstance(AssertionError)},
         },
     ]
+
+
+def test_plain_validator_plain_serializer() -> None:
+    """https://github.com/pydantic/pydantic/issues/8512"""
+    ser_type = str
+    serializer = PlainSerializer(lambda x: ser_type(int(x)), return_type=ser_type)
+    validator = PlainValidator(lambda x: bool(int(x)))
+
+    class Blah(BaseModel):
+        foo: Annotated[bool, validator, serializer]
+        bar: Annotated[bool, serializer, validator]
+
+    blah = Blah(foo='0', bar='1')
+    data = blah.model_dump()
+    assert isinstance(data['foo'], ser_type)
+    assert isinstance(data['bar'], ser_type)

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
pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_validators.py
RH2_TEST_RC=$?
: '>>>>> End Test Output'
echo "RH2_TEST_RC=$RH2_TEST_RC"
echo "RH2_TS_TEST_END=$(date +%s.%N)"
git checkout 8060fa1cff965850e5e08a67ca73d5272dcdcf9f tests/test_validators.py
