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
index 013566ae2..40fca4283 100644
--- a/tests/test_validators.py
+++ b/tests/test_validators.py
@@ -20,12 +20,15 @@ from pydantic import (
     ConfigDict,
     Field,
     GetCoreSchemaHandler,
+    PlainSerializer,
     PydanticDeprecatedSince20,
     PydanticUserError,
+    StrictBool,
     TypeAdapter,
     ValidationError,
     ValidationInfo,
     ValidatorFunctionWrapHandler,
+    WithJsonSchema,
     errors,
     field_validator,
     model_validator,
@@ -2806,3 +2809,82 @@ def test_validate_default_raises_for_dataclasses() -> None:
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
+
+    # Whatever its position, the serializer is used, in python and in JSON mode; validation is unchanged.
+    assert blah.foo is False
+    assert blah.bar is True
+    assert data == {'foo': '0', 'bar': '1'}
+    assert blah.model_dump_json() == '{"foo":"0","bar":"1"}'
+
+    # The annotated type also works outside a model field, e.g. for the items of a list.
+    ta = TypeAdapter(List[Annotated[bool, serializer, validator]])
+    assert ta.validate_python(['0', '1']) == [False, True]
+    assert ta.dump_json([False, True]) == b'["0","1"]'
+
+    # Same with another type and serializer (`when_used='json'`), a validator taking `info`,
+    # and a JSON schema given for the plain validator.
+    class Other(BaseModel):
+        x: Annotated[
+            int,
+            PlainSerializer(lambda x: f'{x:,}', return_type=str, when_used='json'),
+            PlainValidator(lambda v, info: int(v)),
+            WithJsonSchema({'type': 'integer'}, mode='validation'),
+        ]
+
+    other = Other(x='1234')
+    assert other.x == 1234
+    assert other.model_dump() == {'x': 1234}
+    assert other.model_dump_json() == '{"x":"1,234"}'
+
+    # A plain validator replaces the inner validation logic, so it keeps working for a type
+    # pydantic cannot generate a schema for.
+    class Unsupported:
+        pass
+
+    class WithUnsupported(BaseModel):
+        u: Annotated[Unsupported, PlainValidator(lambda v: Unsupported())]
+
+    m = WithUnsupported(u='abc')
+    assert isinstance(m.u, Unsupported)
+    assert isinstance(m.model_dump()['u'], Unsupported)
+
+    # Metadata placed before the plain validator is still replaced by it (documented ordering of validators):
+    # neither the inner constraint (`StrictBool`) nor an inner validator applies, while the serializer is still used.
+    class Replaced(BaseModel):
+        z: Annotated[StrictBool, AfterValidator(lambda v: 1 / 0), serializer, validator]
+
+    replaced = Replaced(z='1')
+    assert replaced.z is True
+    assert replaced.model_dump() == {'z': '1'}
+
+    # The serializer is also used when other metadata sits between it and the plain validator.
+    class Between(BaseModel):
+        w: Annotated[
+            int, PlainSerializer(lambda v: v * 10), AfterValidator(lambda v: 1 / 0), PlainValidator(lambda v: int(v))
+        ]
+
+    between = Between(w='7')
+    assert between.w == 7
+    assert between.model_dump() == {'w': 70}
+
+    # With serializers on both sides of the plain validator, the outer one is used, as without the plain validator.
+    class Both(BaseModel):
+        b: Annotated[bool, PlainSerializer(lambda v: 'inner'), validator, PlainSerializer(lambda v: 'outer')]
+
+    assert Both(b='1').model_dump() == {'b': 'outer'}

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
