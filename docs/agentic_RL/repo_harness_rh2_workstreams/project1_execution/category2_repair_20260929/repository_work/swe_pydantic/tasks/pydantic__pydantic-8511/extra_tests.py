


def test_inherited_required_field_without_local_annotations():
    @pydantic.dataclasses.dataclass
    class Parent:
        x: int = Field()

    @pydantic.dataclasses.dataclass
    class Child(Parent):
        pass

    assert Child(x='3').x == 3


def test_inherited_hidden_field_without_local_annotations():
    @pydantic.dataclasses.dataclass
    class Parent:
        x: int = Field(repr=False)

    @pydantic.dataclasses.dataclass
    class Child(Parent):
        pass

    assert Child(x='3').x == 3


def test_inherited_factory_field_without_local_annotations():
    @pydantic.dataclasses.dataclass
    class Parent:
        x: int = Field(default_factory=lambda: 3)

    @pydantic.dataclasses.dataclass
    class Child(Parent):
        pass

    assert Child().x == 3


def test_field_default_repr_stays_visible():
    @pydantic.dataclasses.dataclass
    class Visible:
        x: int = Field(default=3)

    assert 'x=3' in repr(Visible())
