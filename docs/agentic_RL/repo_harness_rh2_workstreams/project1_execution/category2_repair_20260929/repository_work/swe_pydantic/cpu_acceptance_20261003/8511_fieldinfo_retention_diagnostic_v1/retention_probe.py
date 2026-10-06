"""8511 既有字段信息保留诊断；仅在固定题级容器内执行。"""
import importlib.metadata
import json
import os
import sys
from typing import List

import pydantic
from pydantic import Field, ValidationError
from pydantic.dataclasses import dataclass


def factory():
    @dataclass
    class HiddenFactory:
        x: List[int] = Field(default_factory=list, repr=False)
    a, b = HiddenFactory(), HiddenFactory()
    assert a.x == [] and b.x == [] and a.x is not b.x
    return {'value': a.x, 'independent_factory_values': True}


def inherited_factory():
    @dataclass
    class Parent:
        x: List[int] = Field(default_factory=list, repr=False)
    @dataclass
    class Child(Parent):
        pass
    a, b = Child(), Child()
    assert a.x == [] and b.x == [] and a.x is not b.x
    return {'value': a.x, 'independent_factory_values': True}


def constraint():
    @dataclass
    class Positive:
        x: int = Field(default=1, gt=0, repr=False)
    assert Positive(x='2').x == 2
    try:
        Positive(x=0)
    except ValidationError as exc:
        errors = exc.errors()
        assert any(e['type'] == 'greater_than' and e['loc'] == ('x',) for e in errors), errors
        return {'valid_input': 2, 'invalid_input_rejected': errors}
    raise AssertionError('Field(gt=0, repr=False) must reject explicit x=0')


def alias():
    @dataclass
    class Aliased:
        x: int = Field(default=1, alias='y', repr=False)
    obj = Aliased(y='2')
    assert obj.x == 2, obj.x
    return {'x': obj.x}


facts = {'schema': 'pydantic8511.fieldinfo_retention_diagnostic.v1', 'uid': os.getuid(),
         'python': sys.version, 'pydantic': pydantic.__version__,
         'pydantic_path': pydantic.__file__, 'core': importlib.metadata.version('pydantic-core'),
         'cases': {}}
for name, fn in [('hidden_factory', factory), ('inherited_hidden_factory', inherited_factory),
                 ('hidden_gt_constraint', constraint), ('hidden_alias', alias)]:
    try:
        facts['cases'][name] = {'passed': True, 'observation': fn()}
    except Exception as exc:
        facts['cases'][name] = {'passed': False, 'exception_type': type(exc).__name__, 'message': str(exc)}
facts['all_passed'] = all(c['passed'] for c in facts['cases'].values())
print(json.dumps(facts, ensure_ascii=False, default=str))
sys.exit(0 if facts['all_passed'] else 1)
