


def test_default_encoding_preserves_stdlib_dataclass_instance():
    import dataclasses

    @dataclasses.dataclass
    class Point:
        x: int

    class Model(BaseModel):
        point: Point = Point(1)

    assert Model.model_json_schema()['properties']['point']['default'] == {'x': 1}
