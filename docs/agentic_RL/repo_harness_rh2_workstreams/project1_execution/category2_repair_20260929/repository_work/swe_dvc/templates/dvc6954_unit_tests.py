

def test_parse_negative_float_and_containers():
    text = "rate = -0.25\nvalues = [-2, -0.75]\nconfig = {'shift': -3.5}\n"
    assert parse_py(text, "params.py") == {
        "rate": -0.25,
        "values": [-2, -0.75],
        "config": {"shift": -3.5},
    }
