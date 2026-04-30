from app import greeting


def test_greeting_normalizes_name():
    assert greeting("  repo harness  ") == "Hello, Repo Harness!"
