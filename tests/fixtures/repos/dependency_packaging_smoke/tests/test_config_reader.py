from app import dependency_names


def test_dependency_names_returns_full_list():
    payload = """
[project]
name = "demo"
dependencies = [
  "tomli==2.0.1",
  "pytest>=8,<9",
]
"""

    assert dependency_names(payload) == ["tomli==2.0.1", "pytest>=8,<9"]

