from __future__ import annotations

from repo_harness.tools.symbol_index import filter_symbols, index_python_symbols


def test_index_python_symbols_records_classes_functions_and_methods():
    symbols, error = index_python_symbols(
        path="pkg/demo.py",
        source=(
            "class Demo:\n"
            "    async def load(self, item):\n"
            "        return item\n\n"
            "def helper(value):\n"
            "    return value\n"
        ),
    )

    qualified_names = {symbol["qualified_name"]: symbol for symbol in symbols}

    assert error is None
    assert qualified_names["Demo"]["symbol_kind"] == "class"
    assert qualified_names["Demo.load"]["symbol_kind"] == "method"
    assert qualified_names["Demo.load"]["signature"] == "async def load(self, item)"
    assert qualified_names["helper"]["symbol_kind"] == "function"


def test_filter_symbols_normalizes_case_and_underscore_boundaries():
    symbols, _ = index_python_symbols(
        path="pkg/demo.py",
        source="class MultiValue:\n    pass\n\ndef parse_value():\n    return None\n",
    )

    matches = filter_symbols(symbols, query="multi_value", symbol_kind="any")

    assert [match["qualified_name"] for match in matches] == ["MultiValue"]
    assert "name" in matches[0]["matched_fields"]
