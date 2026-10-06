

def test_repr_false_field_preserves_default_factory():
    @pydantic.dataclasses.dataclass
    class HiddenFactory:
        x: List[int] = Field(default_factory=list, repr=False)

    first, second = HiddenFactory(), HiddenFactory()
    assert first.x == [] and second.x == []
    assert first.x is not second.x


def test_inherited_repr_false_field_preserves_default_factory():
    @pydantic.dataclasses.dataclass
    class Parent:
        x: List[int] = Field(default_factory=list, repr=False)

    @pydantic.dataclasses.dataclass
    class Child(Parent):
        pass

    first, second = Child(), Child()
    assert first.x == [] and second.x == []
    assert first.x is not second.x


def test_repr_false_field_preserves_gt_constraint():
    @pydantic.dataclasses.dataclass
    class Positive:
        x: int = Field(default=1, gt=0, repr=False)

    assert Positive(x='2').x == 2
    with pytest.raises(ValidationError) as exc_info:
        Positive(x=0)
    assert any(error['type'] == 'greater_than' and error['loc'] == ('x',) for error in exc_info.value.errors())


def test_repr_false_field_preserves_alias():
    @pydantic.dataclasses.dataclass
    class Aliased:
        x: int = Field(default=1, alias='y', repr=False)

    assert Aliased(y='2').x == 2
