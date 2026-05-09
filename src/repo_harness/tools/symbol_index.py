"""Lightweight Python AST symbol indexing for model-visible source files."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any


SYMBOL_INDEX_POLICY_VERSION = "repo_harness_python_ast_symbol_index_v0"
SUPPORTED_SYMBOL_KINDS = {"any", "class", "function", "method"}


@dataclass
class SymbolRecord:
    name: str
    qualified_name: str
    symbol_kind: str
    path: str
    line: int
    end_line: int | None = None
    parent: str | None = None
    signature: str | None = None
    matched_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "qualified_name": self.qualified_name,
            "symbol_kind": self.symbol_kind,
            "path": self.path,
            "line": self.line,
            "end_line": self.end_line,
            "parent": self.parent,
            "signature": self.signature,
            "matched_fields": list(self.matched_fields),
        }


class _SymbolVisitor(ast.NodeVisitor):
    def __init__(self, *, path: str) -> None:
        self.path = path
        self.class_stack: list[str] = []
        self.function_stack: list[str] = []
        self.symbols: list[SymbolRecord] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        parent = ".".join([*self.class_stack, *self.function_stack]) or None
        qualified_name = ".".join([*self.class_stack, *self.function_stack, node.name])
        self.symbols.append(
            SymbolRecord(
                name=node.name,
                qualified_name=qualified_name,
                symbol_kind="class",
                path=self.path,
                line=int(getattr(node, "lineno", 0) or 0),
                end_line=getattr(node, "end_lineno", None),
                parent=parent,
                signature=f"class {node.name}",
            )
        )
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record_function(node, async_prefix=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record_function(node, async_prefix=True)

    def _record_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, *, async_prefix: bool) -> None:
        parent = ".".join([*self.class_stack, *self.function_stack]) or None
        qualified_name = ".".join([*self.class_stack, *self.function_stack, node.name])
        symbol_kind = "method" if self.class_stack else "function"
        prefix = "async def" if async_prefix else "def"
        self.symbols.append(
            SymbolRecord(
                name=node.name,
                qualified_name=qualified_name,
                symbol_kind=symbol_kind,
                path=self.path,
                line=int(getattr(node, "lineno", 0) or 0),
                end_line=getattr(node, "end_lineno", None),
                parent=parent,
                signature=f"{prefix} {node.name}{_signature_from_args(node.args)}",
            )
        )
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()


def index_python_symbols(*, path: str, source: str) -> tuple[list[dict[str, Any]], str | None]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [], f"{exc.__class__.__name__}: {exc.msg} at line {exc.lineno}"
    visitor = _SymbolVisitor(path=path)
    visitor.visit(tree)
    return [symbol.to_dict() for symbol in visitor.symbols], None


def filter_symbols(
    symbols: list[dict[str, Any]],
    *,
    query: str,
    symbol_kind: str,
) -> list[dict[str, Any]]:
    query_norm = _normalize_symbol_text(query)
    matches: list[dict[str, Any]] = []
    for symbol in symbols:
        if symbol_kind != "any" and symbol.get("symbol_kind") != symbol_kind:
            continue
        fields = {
            "name": str(symbol.get("name") or ""),
            "qualified_name": str(symbol.get("qualified_name") or ""),
            "path": str(symbol.get("path") or ""),
            "signature": str(symbol.get("signature") or ""),
        }
        matched_fields = [
            field_name
            for field_name, value in fields.items()
            if query_norm in _normalize_symbol_text(value)
        ]
        if not matched_fields:
            continue
        matches.append({**symbol, "matched_fields": matched_fields})
    return sorted(matches, key=_symbol_rank_key)


def _symbol_rank_key(symbol: dict[str, Any]) -> tuple[int, str, int, str]:
    fields = symbol.get("matched_fields") or []
    if "name" in fields:
        rank = 0
    elif "qualified_name" in fields:
        rank = 1
    elif "signature" in fields:
        rank = 2
    else:
        rank = 3
    return (
        rank,
        str(symbol.get("path") or ""),
        int(symbol.get("line") or 0),
        str(symbol.get("qualified_name") or ""),
    )


def _normalize_symbol_text(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _signature_from_args(args: ast.arguments) -> str:
    names = [arg.arg for arg in [*args.posonlyargs, *args.args]]
    if args.vararg is not None:
        names.append(f"*{args.vararg.arg}")
    names.extend(arg.arg for arg in args.kwonlyargs)
    if args.kwarg is not None:
        names.append(f"**{args.kwarg.arg}")
    return f"({', '.join(names)})"
