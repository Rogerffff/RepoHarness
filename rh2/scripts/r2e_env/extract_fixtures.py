#!/usr/bin/env python3
"""从 base 提交的 conftest 链里**原样**摘出隐藏测试缺的 fixture（只读；2026-09-24 夜，T0-6 第二步用）。

R2E 把隐藏测试从仓库原目录搬进 `r2e_tests/` 后，原目录上各层 `conftest.py` 不再生效，用到的 fixture 找不到，用例恒 ERROR。
修法（用户批准的 T0-6 方案 B）是在私有 `r2e_tests/conftest.py` 里补回这些 fixture。本工具保证"补回"是原文：

- 输入：原测试文件所在目录向上的 conftest 链（外层在前、内层在后，都取自镜像里 base 提交、与 git 索引一致的原文）与缺的 fixture 名；
- 同名 fixture 按 pytest 的查找规则取**最内层**；fixture 的参数里若还有 fixture（`request` 等内置除外），同样按链查找并一并摘出；
- 每个摘出的定义所引用的模块级名字（常量、辅助函数、导入）在**它自己所在的 conftest** 里解析并一并带上（与 Python 作用域一致）；
- 输出的每段都是源文件的原始行（装饰器 + 函数体，或整条语句），按来源文件分节并注明出处与 git blob；不改写任何一行；
- 不带 autouse fixture、hook（`pytest_*`）或与缺失名字无关的定义；解析不到的名字或同名冲突直接报错，不猜。
- 缺哪些 fixture 可以直接给（`--need`），也可以给隐藏测试原文（`--tests`）由 `requested_fixtures` 静态算出：pytest 对每个
  用例只报第一个找不到的 fixture，按报错补会漏（T0-6 第二步 pandas `32dd55cb`、`7dd34ea7` 第一版草稿即如此）。
  算出的名字里 conftest 链解析不到的（插件 fixture 等）与需要人工核对的写法会打印出来，不静默丢弃。

用法（从 rh2/）：
  .venv/bin/python scripts/r2e_env/extract_fixtures.py --chain <外层 conftest> [--chain <内层 conftest> …] \\
      --blob <路径>=<git blob> … [--need float_frame …] [--tests <隐藏测试文件>] --header "<说明行>" --out <文件>
"""

from __future__ import annotations

import argparse
import ast
import builtins
import sys
from dataclasses import dataclass, field
from pathlib import Path

PYTEST_BUILTIN_FIXTURES = frozenset({
    "request", "tmp_path", "tmpdir", "tmp_path_factory", "tmpdir_factory", "monkeypatch", "capsys", "capsysbinary",
    "capfd", "capfdbinary", "caplog", "recwarn", "pytestconfig", "cache", "record_property", "record_xml_attribute",
    "record_testsuite_property", "doctest_namespace",
})
_BUILTINS = frozenset(dir(builtins))


class ExtractError(ValueError):
    pass


@dataclass
class Module:
    rel: str
    text: str
    tree: ast.Module
    lines: list[str] = field(default_factory=list)
    fixtures: dict[str, ast.FunctionDef] = field(default_factory=dict)
    defs: dict[str, ast.stmt] = field(default_factory=dict)   # 模块级名字 → 定义它的语句（函数 / 类 / 赋值 / 导入）

    @classmethod
    def parse(cls, rel: str, text: str) -> "Module":
        tree = ast.parse(text)
        m = cls(rel=rel, text=text, tree=tree, lines=text.splitlines(keepends=True))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if is_fixture(node):
                    m.fixtures[fixture_name(node)] = node
                m.defs.setdefault(node.name, node)
            elif isinstance(node, ast.ClassDef):
                m.defs.setdefault(node.name, node)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in targets:
                    for n in ast.walk(t):
                        if isinstance(n, ast.Name):
                            m.defs.setdefault(n.id, node)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    bound = alias.asname or alias.name.split(".")[0]
                    m.defs.setdefault(bound, node)
        return m

    def source_of(self, node: ast.stmt) -> str:
        start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
        return "".join(self.lines[start - 1:node.end_lineno])


def is_fixture(node: ast.FunctionDef) -> bool:
    for dec in node.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if ast.unparse(target).split(".")[-1] == "fixture":
            return True
    return False


def fixture_name(node: ast.FunctionDef) -> str:
    for dec in node.decorator_list:
        if isinstance(dec, ast.Call) and ast.unparse(dec.func).split(".")[-1] == "fixture":
            for kw in dec.keywords:
                if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                    return kw.value.value
    return node.name


def is_autouse(node: ast.FunctionDef) -> bool:
    for dec in node.decorator_list:
        if isinstance(dec, ast.Call):
            for kw in dec.keywords:
                if kw.arg == "autouse" and isinstance(kw.value, ast.Constant) and kw.value.value:
                    return True
    return False


def free_names(node: ast.stmt) -> set[str]:
    """语句里以读方式出现、需要到模块顶层解析的名字（含装饰器、默认值、函数体）；去掉内置名。
    函数（含嵌套函数、lambda、推导式）里的参数与赋过值的名字算局部，不去模块顶层找——否则函数体里的同名局部变量
    （例：pandas `idx` fixture 里的局部 `index_names`）会把同名的模块级定义错带进来。"""

    names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    local: set[str] = set()
    for fn in ast.walk(node):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            a = fn.args
            local |= {x.arg for x in a.posonlyargs + a.args + a.kwonlyargs}
            local |= {x.arg for x in (a.vararg, a.kwarg) if x is not None}
            body = fn.body if isinstance(fn.body, list) else [fn.body]
            for stmt in body:
                local |= {n.id for n in ast.walk(stmt) if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del))}
        elif isinstance(fn, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for gen in fn.generators:
                local |= {n.id for n in ast.walk(gen.target) if isinstance(n, ast.Name)}
    # 装饰器与默认值在函数外求值，其中的名字仍需到模块顶层找
    outer: set[str] = set()
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for expr in node.decorator_list + node.args.defaults + [d for d in node.args.kw_defaults if d is not None]:
            outer |= {n.id for n in ast.walk(expr) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return ((names - local) | outer) - _BUILTINS


@dataclass
class Requested:
    names: set[str]            # 用例请求、本模块没定义、也不是 pytest 内置的 fixture 名（要到 conftest 链里找）
    review: list[str]          # 静态分析看不全、需要人工核对的地方（动态取 fixture、间接参数化、继承来的用例等）


def _param_names(decorators: list[ast.expr]) -> tuple[set[str], list[str]]:
    names, notes = set(), []
    for dec in decorators:
        if isinstance(dec, ast.Call) and ast.unparse(dec.func).split(".")[-1] == "parametrize" and dec.args:
            first = dec.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                names |= {s.strip() for s in first.value.split(",") if s.strip()}
            elif isinstance(first, (ast.List, ast.Tuple)):
                names |= {e.value for e in first.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)}
            else:
                notes.append(f"parametrize 参数名不是字面量: {ast.unparse(first)}")
            if any(kw.arg == "indirect" for kw in dec.keywords):
                notes.append(f"间接参数化（indirect）: {ast.unparse(first)}")
    return names, notes


def _usefixtures(decorators: list[ast.expr]) -> set[str]:
    out = set()
    for dec in decorators:
        if isinstance(dec, ast.Call) and ast.unparse(dec.func).split(".")[-1] == "usefixtures":
            out |= {a.value for a in dec.args if isinstance(a, ast.Constant) and isinstance(a.value, str)}
    return out


def requested_fixtures(test_text: str) -> Requested:
    """隐藏测试模块里各用例（模块级 `test*` 函数与 `Test*` 类里的 `test*` 方法）请求的 fixture：参数名与 usefixtures，
    减去 parametrize 直接给值的参数名、本模块（含类内）定义的 fixture 与 pytest 内置 fixture；请求到的本模块 fixture
    的参数递归计入。pytest 对每个用例只报第一个找不到的 fixture，按报错补会漏；这里一次算全，再由试跑确认。"""

    tree = ast.parse(test_text)
    local = {fixture_name(n): n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and is_fixture(n)}
    review: list[str] = []
    wanted: set[str] = set()

    def visit(fn: ast.FunctionDef, given: set[str], uses: set[str]) -> None:
        params, notes = _param_names(fn.decorator_list)
        review.extend(f"{fn.name}: {x}" for x in notes)
        args = [a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs if a.arg not in ("self", "cls")]
        wanted.update(a for a in args if a not in params | given)
        wanted.update(_usefixtures(fn.decorator_list) | uses)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            visit(node, set(), set())
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            given, notes = _param_names(node.decorator_list)
            review.extend(f"{node.name}: {x}" for x in notes)
            bases = [ast.unparse(b) for b in node.bases if ast.unparse(b) != "object"]
            if bases:
                review.append(f"{node.name} 继承 {bases}：基类里的用例与 fixture 不在本文件，需另核")
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith("test"):
                    visit(item, given, _usefixtures(node.decorator_list))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and "pytestmark" in ast.unparse(node).split("=")[0]:
            wanted.update(_usefixtures([e for e in ast.walk(node) if isinstance(e, ast.Call)]))
        elif isinstance(node, ast.FunctionDef) and node.name.startswith("pytest_"):
            review.append(f"模块里有 hook {node.name}")
    if "getfixturevalue" in test_text:
        review.append("用到 request.getfixturevalue（动态取 fixture，名字需人工核对）")
    out: set[str] = set()
    seen: set[str] = set()
    todo = sorted(wanted)
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        if name in local:
            fx = local[name]
            todo.extend(a.arg for a in fx.args.posonlyargs + fx.args.args + fx.args.kwonlyargs if a.arg not in ("self", "cls"))
        elif name not in PYTEST_BUILTIN_FIXTURES:
            out.add(name)
    return Requested(names=out, review=review)


def extract(chain: list[Module], needed: list[str]) -> list[tuple[Module, ast.stmt]]:
    """返回按（来源模块在链中的顺序, 源码行号）排好的 (模块, 语句) 列表。"""

    selected: dict[tuple[int, int], tuple[Module, ast.stmt]] = {}
    fixture_owner: dict[str, int] = {}

    def resolve_fixture(name: str) -> tuple[int, Module, ast.FunctionDef] | None:
        for idx in range(len(chain) - 1, -1, -1):   # 最内层优先（pytest 规则）
            if name in chain[idx].fixtures:
                return idx, chain[idx], chain[idx].fixtures[name]
        return None

    def add_stmt(idx: int, mod: Module, node: ast.stmt) -> None:
        key = (idx, node.lineno)
        if key in selected:
            return
        selected[key] = (mod, node)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return
        for name in sorted(free_names(node)):
            if name in mod.defs:
                add_stmt(idx, mod, mod.defs[name])
            elif name not in {"pytest"}:
                # 不在本模块顶层：可能是函数局部名、推导式变量或参数；参数若是 fixture 在下面单独处理
                pass

    todo = list(needed)
    while todo:
        name = todo.pop(0)
        if name in fixture_owner or name in PYTEST_BUILTIN_FIXTURES:
            continue
        found = resolve_fixture(name)
        if found is None:
            raise ExtractError(f"fixture {name!r} 在 conftest 链里找不到")
        idx, mod, node = found
        if is_autouse(node):
            raise ExtractError(f"fixture {name!r} 是 autouse，不应作为缺失 fixture 补回")
        fixture_owner[name] = idx
        add_stmt(idx, mod, node)
        for arg in [a.arg for a in node.args.args + node.args.kwonlyargs]:
            if arg not in PYTEST_BUILTIN_FIXTURES and resolve_fixture(arg) is not None:
                todo.append(arg)
    # 同一个模块级名字不能来自两个不同来源：导入比较绑定目标（从哪个模块取哪个名字），其它定义比较原文
    seen: dict[str, tuple[str, object]] = {}
    for (idx, _), (mod, node) in selected.items():
        for name, stmt in mod.defs.items():
            if stmt is node:
                ident = binding_identity(node, name) if isinstance(node, (ast.Import, ast.ImportFrom)) else mod.source_of(node)
                if name in seen and seen[name][1] != ident:
                    raise ExtractError(f"名字 {name!r} 在 {seen[name][0]} 与 {mod.rel} 里定义不同，合并会冲突")
                seen[name] = (mod.rel, ident)
    return [selected[k] for k in sorted(selected)]


def binding_identity(node: ast.stmt, bound: str) -> tuple:
    """导入语句给名字 `bound` 绑定的目标：两条写法不同、但绑定同一对象的导入不算冲突。"""

    for alias in node.names:
        name = alias.asname or (alias.name if isinstance(node, ast.ImportFrom) else alias.name.split(".")[0])
        if name == bound:
            if isinstance(node, ast.ImportFrom):
                return ("from", node.level, node.module, alias.name)
            return ("import", alias.name if alias.asname else alias.name.split(".")[0])
    return ("?", bound)


def render(chain: list[Module], picked: list[tuple[Module, ast.stmt]], *, header: list[str], blobs: dict[str, str]) -> str:
    out = [f"# {h}\n" for h in header]
    imports, bodies = [], []
    import_seen: set[str] = set()
    for mod, node in picked:
        src = mod.source_of(node)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if src not in import_seen:
                import_seen.add(src)
                imports.append(src)
        else:
            bodies.append((mod, src))
    out.append("\n")
    out.extend(imports)
    current = None
    for mod, src in bodies:
        if mod is not current:
            blob = blobs.get(mod.rel, "?")
            out.append(f"\n\n# ---- 摘自 base 提交的 {mod.rel}（git blob {blob}）原文 ----\n")
            current = mod
        out.append("\n\n" + src)
    text = "".join(out).rstrip("\n") + "\n"
    ast.parse(text)  # 输出必须是合法 Python
    return text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chain", action="append", required=True, help="conftest 链，外层在前；形如 <仓库内相对路径>=<本地文件>")
    ap.add_argument("--blob", action="append", default=[], help="<仓库内相对路径>=<git blob>，写进出处注释")
    ap.add_argument("--need", action="append", default=[])
    ap.add_argument("--tests", action="append", default=[], help="隐藏测试原文；静态算出它请求的 fixture 并入 --need")
    ap.add_argument("--header", action="append", default=[])
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    chain = []
    for item in args.chain:
        rel, _, path = item.partition("=")
        chain.append(Module.parse(rel, Path(path).read_text(encoding="utf-8")))
    blobs = dict(b.split("=", 1) for b in args.blob)
    need = list(args.need)
    for path in args.tests:
        req = requested_fixtures(Path(path).read_text(encoding="utf-8"))
        in_chain = sorted(n for n in req.names if any(n in m.fixtures for m in chain))
        print(f"{path}: 请求 {sorted(req.names)}；链里有 {in_chain}；链里没有 {sorted(req.names - set(in_chain))}")
        for note in req.review:
            print(f"  需人工核对: {note}")
        need += [n for n in in_chain if n not in need]
    if not need:
        ap.error("没有要补的 fixture（--need 与 --tests 都没给出名字）")
    picked = extract(chain, need)
    Path(args.out).write_text(render(chain, picked, header=args.header, blobs=blobs), encoding="utf-8")
    names = sorted({fixture_name(n) for _, n in picked if isinstance(n, ast.FunctionDef) and is_fixture(n)})
    print(f"fixtures: {names}; statements: {len(picked)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
