#!/usr/bin/env bash
# L3 反例 · python__mypy-11352：构造最小 mypy 输入，比较 base / gold / candidate 的输出。
#
# 要回答的问题：候选与 gold 的差别（reveal_type 里多显示一个未使用的 SendType `S`）
# 到底只是**展示**不同，还是会改变 mypy 接受/拒绝的程序集合。
#
# 做法：把每个最小程序写成独立文件，用 `mypy --config-file=` 跑，
# 记录 **退出码** 与 **每行诊断**，分成两层比较：
#   L1 语义层：每个 case 是否报错（rc）、报错在第几行、错误码是什么
#   L2 展示层：`Revealed type is "..."` 的具体字符串
# 只有 L1 出现差异，才能说"接受/拒绝的程序集合变了"；只有 L2 有差异，就是展示差异。
#
# 用法（在任务镜像容器内，由 run_matrix.sh 调用；也可单独跑）：
#   OUT_JSON=/l3/out/x.json CASES_DIR=/tmp/l3cases bash diagnostic_test.sh
set -u

: "${WORKDIR:=/testbed}"
: "${CASES_DIR:=/tmp/l3_mypy_11352_cases}"
: "${OUT_JSON:=/tmp/l3_mypy_11352_cases.json}"
: "${PY:=}"
: "${MYPY_FLAGS:=--config-file= --no-incremental --no-error-summary --hide-error-context}"

if [ -z "$PY" ]; then
  for c in /opt/miniconda3/envs/testbed/bin/python /usr/local/bin/python python3 python; do
    if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
  done
fi

mkdir -p "$CASES_DIR"
rm -f "$CASES_DIR"/*.py "$CASES_DIR"/*.out 2>/dev/null

# ---------------------------------------------------------------- 前置检查
# 镜像里的 mypy 若是 mypyc 编译过的扩展（.so），改 .py 不会生效，整组结果无意义。
PLUGIN_FILE="$("$PY" -c 'import mypy.plugins.default as m; print(m.__file__)' 2>&1)"
echo "[preflight] mypy.plugins.default -> $PLUGIN_FILE"
case "$PLUGIN_FILE" in
  *.py) ;;
  *) echo "[preflight][WARN] 不是 .py（可能是 mypyc 编译产物），补丁可能不生效——结果记 unknown" ;;
esac

# ---------------------------------------------------------------- 用例
# A 组：题面原例（async）。语义判据：有没有 "Incompatible types in assignment"。
cat > "$CASES_DIR/a1_async_identity_problem_statement.py" <<'EOF'
import contextlib, typing

_T = typing.TypeVar('_T')


@contextlib.asynccontextmanager
async def identity(element: _T) -> typing.AsyncIterator[_T]:
    yield element


async def main() -> None:
    async with identity(1) as number:
        reveal_type(number)
        number = 2
EOF

# A2：同一场景的负例。把 int 换成 str 赋值，**必须**报错；
# 若 candidate/gold 任一不报错，说明类型被推成了 Any，是真实语义缺陷。
cat > "$CASES_DIR/a2_async_identity_negative.py" <<'EOF'
import contextlib, typing

_T = typing.TypeVar('_T')


@contextlib.asynccontextmanager
async def identity(element: _T) -> typing.AsyncIterator[_T]:
    yield element


async def main() -> None:
    async with identity(1) as number:
        number = 'not an int'
EOF

# A3：同步对照（base 就应该是对的）。
cat > "$CASES_DIR/a3_sync_identity_baseline.py" <<'EOF'
import contextlib, typing

_T = typing.TypeVar('_T')


@contextlib.contextmanager
def identity(element: _T) -> typing.Iterator[_T]:
    yield element


def main() -> None:
    with identity(1) as number:
        reveal_type(number)
        number = 2
EOF

# B 组：带 SendType 的 Generator/AsyncGenerator —— 展示层差异的来源。
cat > "$CASES_DIR/b1_sync_sendtype_reveal.py" <<'EOF'
from contextlib import contextmanager
from typing import TypeVar, Generator

T = TypeVar('T')
S = TypeVar('S')


@contextmanager
def yield_id(item: T) -> Generator[T, S, None]:
    yield item


reveal_type(yield_id)

with yield_id(1) as x:
    reveal_type(x)
    x = 2
EOF

cat > "$CASES_DIR/b2_async_sendtype_reveal.py" <<'EOF'
from contextlib import asynccontextmanager
from typing import TypeVar, AsyncGenerator

T = TypeVar('T')
S = TypeVar('S')


@asynccontextmanager
async def yield_id(item: T) -> AsyncGenerator[T, S]:
    yield item


reveal_type(yield_id)


async def main() -> None:
    async with yield_id(1) as x:
        reveal_type(x)
        x = 2
EOF

# C 组：**语义层**候选项 —— 显式类型应用。
# 若未使用的 S 仍被量化，`yield_id[int]` 的类型参数个数就从 1 变成 2，
# 这是"接受/拒绝的程序集合"层面的差异，不是展示差异。
cat > "$CASES_DIR/c1_type_application_one_arg.py" <<'EOF'
from contextlib import contextmanager
from typing import TypeVar, Generator

T = TypeVar('T')
S = TypeVar('S')


@contextmanager
def yield_id(item: T) -> Generator[T, S, None]:
    yield item


f = yield_id[int]
reveal_type(f)
EOF

cat > "$CASES_DIR/c2_type_application_two_args.py" <<'EOF'
from contextlib import contextmanager
from typing import TypeVar, Generator

T = TypeVar('T')
S = TypeVar('S')


@contextmanager
def yield_id(item: T) -> Generator[T, S, None]:
    yield item


f = yield_id[int, str]
reveal_type(f)
EOF

# C3：赋值到精确的 Callable 注解（官方 SendType 用例里那条 `f = g` 的正向版本）。
cat > "$CASES_DIR/c3_assign_to_exact_callable.py" <<'EOF'
from contextlib import contextmanager
from typing import TypeVar, Generator, Callable, ContextManager

T = TypeVar('T')
S = TypeVar('S')


@contextmanager
def yield_id(item: T) -> Generator[T, S, None]:
    yield item


f: Callable[[int], ContextManager[int]] = yield_id
reveal_type(f)
EOF

# C4：官方用例里的负例（把两参数函数赋给它），比较错误消息里是否多出 S。
cat > "$CASES_DIR/c4_incompatible_assignment_message.py" <<'EOF'
from contextlib import contextmanager
from typing import TypeVar, Generator, Any

T = TypeVar('T')
S = TypeVar('S')


@contextmanager
def yield_id(item: T) -> Generator[T, S, None]:
    yield item


f = yield_id


def g(x: Any, y: Any) -> Any:
    pass


f = g
EOF

# C5：把装饰后的函数传给高阶函数（更贴近真实用法）。
cat > "$CASES_DIR/c5_pass_to_higher_order.py" <<'EOF'
from contextlib import contextmanager
from typing import TypeVar, Generator, Callable, ContextManager

T = TypeVar('T')
S = TypeVar('S')


@contextmanager
def yield_id(item: T) -> Generator[T, S, None]:
    yield item


def use(cm_factory: Callable[[int], ContextManager[int]]) -> int:
    with cm_factory(1) as v:
        return v


reveal_type(use(yield_id))
EOF

# C6：通过变量间接调用（检查 S 是否在调用点留下未解的类型变量）。
cat > "$CASES_DIR/c6_indirect_call.py" <<'EOF'
from contextlib import contextmanager
from typing import TypeVar, Generator

T = TypeVar('T')
S = TypeVar('S')


@contextmanager
def yield_id(item: T) -> Generator[T, S, None]:
    yield item


h = yield_id
reveal_type(h(1))
with h(1) as y:
    reveal_type(y)
    y = 2
EOF

# ---------------------------------------------------------------- 逐个跑
for f in "$CASES_DIR"/*.py; do
  n="$(basename "$f" .py)"
  flags="$MYPY_FLAGS"
  case "$n" in
    a1_*|a2_*|b2_*) flags="$flags --python-version 3.7" ;;   # asynccontextmanager 需要 3.7+
  esac
  ( cd "$WORKDIR" && "$PY" -m mypy $flags "$f" ) > "$CASES_DIR/$n.out" 2>&1
  echo "rc=$? $n" >> "$CASES_DIR/$n.out"
done

# ---------------------------------------------------------------- 汇总 JSON
"$PY" - "$CASES_DIR" "$OUT_JSON" <<'PYEOF'
import json, os, re, sys
cases_dir, out_json = sys.argv[1], sys.argv[2]
RE_LINE = re.compile(r"^(?P<file>[^:]+):(?P<line>\d+):\s*(?P<sev>error|note|warning):\s*(?P<msg>.*)$")
RE_REVEAL = re.compile(r'Revealed type is "(.*)"')
res = {}
for fn in sorted(os.listdir(cases_dir)):
    if not fn.endswith(".out"):
        continue
    name = fn[:-4]
    text = open(os.path.join(cases_dir, fn), errors="replace").read()
    rc = None
    m = re.search(r"^rc=(\d+) ", text, re.M)
    if m:
        rc = int(m.group(1))
    semantic, display = [], []
    for line in text.splitlines():
        mm = RE_LINE.match(line.strip())
        if not mm:
            continue
        msg = mm.group("msg")
        rv = RE_REVEAL.search(msg)
        if rv:
            display.append({"line": int(mm.group("line")), "revealed": rv.group(1)})
        else:
            # 语义层：只留严重级别 + 行号 + 消息头（去掉具体类型名里的可变部分留给人读）
            semantic.append({
                "line": int(mm.group("line")),
                "severity": mm.group("sev"),
                "message": msg,
            })
    res[name] = {
        "rc": rc,
        "semantic_diagnostics": semantic,
        "semantic_signature": [(d["line"], d["severity"], d["message"].split(" (")[0][:60]) for d in semantic],
        "revealed_types": display,
        "raw_chars": len(text),
    }
with open(out_json, "w") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
print("[ok] wrote", out_json)
PYEOF
