


def test_plain_validator_serializer_unsupported_type_both_orders():
    class Unsupported:
        pass

    serializer = PlainSerializer(lambda value: 'custom!', return_type=str)
    validator = PlainValidator(lambda value: Unsupported())

    class Before(BaseModel):
        value: Annotated[Unsupported, serializer, validator]

    class After(BaseModel):
        value: Annotated[Unsupported, validator, serializer]

    for model in (Before(value=1), After(value=1)):
        assert isinstance(model.value, Unsupported)
        assert model.model_dump() == {'value': 'custom!'}
        assert model.model_dump_json() == '{"value":"custom!"}'


def test_plain_validator_unresolved_inner_forward_reference():
    class Model(BaseModel):
        value: Annotated['NotDefinedAnywhere8567', PlainValidator(lambda value: value)]

    assert Model(value=5).value == 5


def test_plain_validator_typing_typeddict_inner_schema_not_required():
    from typing import TypedDict

    class Inner(TypedDict):
        a: int

    class Model(BaseModel):
        value: Annotated[Inner, PlainValidator(lambda value: value)]

    assert Model(value={'a': 1}).value == {'a': 1}
