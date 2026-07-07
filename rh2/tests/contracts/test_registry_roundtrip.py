"""registry 级系统性测试：每个顶层契约对象——合法样例通过、未知字段拒收、JSON 往返。

这三条是 S1-1 验收的底线（fail-closed 单测的"每个对象至少一个合法样例 +
未知字段拒收"部分）；各模块更细的非法组合测试见同目录其他文件。
"""

import pytest
from contract_samples import VALID_SAMPLE_FACTORIES
from pydantic import ValidationError

from repoharness2.contracts import SCHEMA_REGISTRY

ALL_SCHEMA_IDS = sorted(SCHEMA_REGISTRY)


def test_registry_and_sample_factories_cover_same_schemas():
    assert set(VALID_SAMPLE_FACTORIES) == set(SCHEMA_REGISTRY)


@pytest.mark.parametrize("schema_id", ALL_SCHEMA_IDS)
def test_valid_sample_passes(schema_id):
    model_cls = SCHEMA_REGISTRY[schema_id]
    instance = model_cls.model_validate(VALID_SAMPLE_FACTORIES[schema_id]())
    assert instance.schema_id == schema_id


@pytest.mark.parametrize("schema_id", ALL_SCHEMA_IDS)
def test_unknown_top_level_field_rejected(schema_id):
    payload = VALID_SAMPLE_FACTORIES[schema_id]()
    payload["unexpected_extra_field"] = "smuggled"
    with pytest.raises(ValidationError, match="unexpected_extra_field"):
        SCHEMA_REGISTRY[schema_id].model_validate(payload)


@pytest.mark.parametrize("schema_id", ALL_SCHEMA_IDS)
def test_json_roundtrip_is_stable(schema_id):
    model_cls = SCHEMA_REGISTRY[schema_id]
    first = model_cls.model_validate(VALID_SAMPLE_FACTORIES[schema_id]())
    second = model_cls.model_validate_json(first.model_dump_json())
    assert first == second


@pytest.mark.parametrize("schema_id", ALL_SCHEMA_IDS)
def test_wrong_schema_id_rejected(schema_id):
    payload = VALID_SAMPLE_FACTORIES[schema_id]()
    payload["schema_id"] = "rh2.not_a_real_schema.v1"
    with pytest.raises(ValidationError):
        SCHEMA_REGISTRY[schema_id].model_validate(payload)


@pytest.mark.parametrize("schema_id", ALL_SCHEMA_IDS)
def test_frozen_models_reject_mutation(schema_id):
    """契约对象是 evidence：构造后禁止原地改字段（frozen=True）。"""

    model_cls = SCHEMA_REGISTRY[schema_id]
    instance = model_cls.model_validate(VALID_SAMPLE_FACTORIES[schema_id]())
    with pytest.raises(ValidationError):
        instance.schema_id = "tampered"  # type: ignore[misc]
