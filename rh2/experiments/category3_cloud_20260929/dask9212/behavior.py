"""dask__dask-9212 私有行为矩阵（容器内 Python 3.10 运行，不交给求解者）。

按公开要求判对错，不以 gold 为答案：
- R1 确定性：同一 Enum 成员多次 tokenize 得到同一 token（严格模式 tokenize.ensure-deterministic=True 下也不报错）；
- R2 区分性：不同成员得到不同 token。文档（custom-collections.rst）写明 token“基于参数值生成 key”、
  `__dask_tokenize__` 应返回“fully representative of the object”的值，示例断言“tokens for different
  objects aren't equal”。token 相撞时，按 token 命名的任务（pure delayed、Delayed 运算符、map_blocks）
  会在同一张图里合并，返回错误结果。
每个用例单独 try/except，一个候选崩溃不影响其它用例。输出一行一个 JSON：
  {"case", "group", "ok": true/false/null（null 表示只记录事实）, 其余为观测值}
"""
import json
import os
import subprocess
import sys
import traceback

MODDIR = "/tmp/c3mods"
os.makedirs(MODDIR, exist_ok=True)

MOD_AB = '''
from enum import Enum, IntEnum, Flag


class Color(Enum):
    RED = 1
    BLUE = 2

    def describe(self):
        return "{mod}"


class IColor(IntEnum):
    RED = 1
    BLUE = 2


class Perm(Flag):
    R = 1
    W = 2
    X = 4


class Hook(Enum):
    """用户按文档推荐的 __dask_tokenize__ 自己保证区分（base 上 Enum 没有注册时的做法）。"""
    A = 1
    B = 2

    def __dask_tokenize__(self):
        return ("hook", type(self).__module__, type(self).__qualname__, self.name)


class Plain:
    pass
'''

FILES = {
    "audit_a.py": MOD_AB.replace("{mod}", "audit_a"),
    "audit_b.py": MOD_AB.replace("{mod}", "audit_b"),
    "audit_funcs.py": '''
def which(e):
    return type(e).__module__


def describe(e):
    return e.describe()


def pick(e):
    return e


def as_dict(a, b):
    return {a: "from " + type(a).__module__, b: "from " + type(b).__module__}


def tag_blocks(x, color):
    return x + (100 if type(color).__module__ == "audit_a" else 200)


def type_name(e):
    return type(e).__name__


def value_of(e):
    return e.value
''',
    "audit_nested.py": '''
from enum import Enum


class Reader:
    class Mode(Enum):
        FAST = 1


class Writer:
    class Mode(Enum):
        FAST = 1


def make_local(kind):
    class Color(kind):
        RED = 1
        BLUE = 2
    return Color
''',
    "audit_core.py": '''
from enum import Enum, IntEnum, Flag, IntFlag


class Color(Enum):
    RED = 1
    BLUE = 2
    CRIMSON = 1  # alias of RED


class Light(Enum):
    RED = 1
    BLUE = 2


class Shape(Enum):
    CIRCLE = 1
    SQUARE = 2


class IColor(IntEnum):
    RED = 1
    BLUE = 2


class Perm(Flag):
    R = 1
    W = 2
    X = 4


class IPerm(IntFlag):
    R = 1
    W = 2
    X = 4


class SColor(str, Enum):
    RED = "red"
    BLUE = "blue"


class Planet(Enum):
    EARTH = (5.976e24, 6.37814e6)
    MARS = (6.421e23, 3.3972e6)


class Conf(Enum):
    A = {"k": [1, 2]}
    B = {"k": [1, 3]}


class Tags(Enum):
    A = frozenset({"alpha", "beta", "gamma", "delta", "epsilon"})
    B = frozenset({"x", "y"})


class Obj:
    pass


class Sentinel(Enum):
    MISSING = Obj()
    DEFAULT = Obj()


class Hooked(Enum):
    A = 1
    B = 2

    def __dask_tokenize__(self):
        return ("hooked", self.name)


class Registered(Enum):
    A = 1
    B = 2
''',
}
for fn, text in FILES.items():
    with open(os.path.join(MODDIR, fn), "w") as f:
        f.write(text)
sys.path.insert(0, MODDIR)

import dask  # noqa: E402
import dask.array as da  # noqa: E402
import numpy as np  # noqa: E402
from dask.base import normalize_token, tokenize  # noqa: E402

import audit_a as A  # noqa: E402
import audit_b as B  # noqa: E402
import audit_core as C  # noqa: E402
import audit_funcs as F  # noqa: E402
import audit_nested as N  # noqa: E402


def emit(rec):
    print(json.dumps(rec, sort_keys=True, default=repr), flush=True)


def run(case, group, fn):
    try:
        rec = fn()
    except Exception as e:  # noqa: BLE001
        rec = {"ok": False, "error": f"{type(e).__name__}: {e}"[:300], "tb": traceback.format_exc()[-500:]}
    rec["case"], rec["group"] = case, group
    emit(rec)


def norm(x):
    try:
        return repr(normalize_token(x))[:160]
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {e}"[:160]


# ---------- R1／R2 核心：各类 Enum 与值形态 ----------
KINDS = {
    "Enum_int": (C.Color.RED, C.Color.BLUE),
    "Flag_single": (C.Perm.R, C.Perm.W),
    "IntEnum": (C.IColor.RED, C.IColor.BLUE),
    "IntFlag_single": (C.IPerm.R, C.IPerm.W),
    "str_mixin": (C.SColor.RED, C.SColor.BLUE),
    "tuple_value": (C.Planet.EARTH, C.Planet.MARS),
    "dict_value": (C.Conf.A, C.Conf.B),
    "frozenset_value": (C.Tags.A, C.Tags.B),
    "object_value": (C.Sentinel.MISSING, C.Sentinel.DEFAULT),
}
for kind, (m1, m2) in KINDS.items():
    run(f"stable:{kind}", "R1", lambda m1=m1: {"ok": tokenize(m1) == tokenize(m1), "norm": norm(m1)})
    run(f"distinct:{kind}", "R2", lambda m1=m1, m2=m2: {"ok": tokenize(m1) != tokenize(m2)})

    def strict(m1=m1, m2=m2):
        with dask.config.set({"tokenize.ensure-deterministic": True}):
            a, b, c = tokenize(m1), tokenize(m1), tokenize(m2)
        return {"ok": a == b and a != c}
    run(f"strict:{kind}", "R1", strict)

run("stable:container", "R1", lambda: {
    "ok": tokenize([C.Color.RED, C.Perm.R], x={"k": C.Color.BLUE}) == tokenize([C.Color.RED, C.Perm.R], x={"k": C.Color.BLUE})
    and tokenize(x=C.Color.RED) != tokenize(x=C.Color.BLUE)})
run("alias:same_member", "R1", lambda: {"ok": tokenize(C.Color.CRIMSON) == tokenize(C.Color.RED)})

# ---------- R2 的非示例实例：不同类、原始值、Flag 组合值 ----------
run("xclass:same_name_value(Color.RED~Light.RED)", "R2", lambda: {
    "ok": tokenize(C.Color.RED) != tokenize(C.Light.RED), "norm": [norm(C.Color.RED), norm(C.Light.RED)]})
run("xclass:same_value(Color.RED~Shape.CIRCLE)", "R2", lambda: {
    "ok": tokenize(C.Color.RED) != tokenize(C.Shape.CIRCLE)})
run("xclass:IntEnum(IColor.RED~Color.RED)", "R2", lambda: {"ok": tokenize(C.IColor.RED) != tokenize(C.Color.RED)})
run("raw:Color.RED~1", "R2", lambda: {"ok": tokenize(C.Color.RED) != tokenize(1)})
run("raw:Color.RED~'RED'", "R2", lambda: {"ok": tokenize(C.Color.RED) != tokenize("RED")})
run("raw:Color.RED~'Color.RED'", "R2-edge", lambda: {"ok": tokenize(C.Color.RED) != tokenize("Color.RED")})
run("flag:combo~combo(R|W~R|X)", "R2", lambda: {
    "ok": tokenize(C.Perm.R | C.Perm.W) != tokenize(C.Perm.R | C.Perm.X),
    "norm": [norm(C.Perm.R | C.Perm.W), norm(C.Perm.R | C.Perm.X)]})
run("flag:combo~empty(R|W~Perm(0))", "R2", lambda: {"ok": tokenize(C.Perm.R | C.Perm.W) != tokenize(C.Perm(0)),
                                                     "norm": norm(C.Perm(0))})
run("flag:combo_stable", "R1", lambda: {"ok": tokenize(C.Perm.R | C.Perm.W) == tokenize(C.Perm.W | C.Perm.R)})
run("intflag:combo~combo", "R2", lambda: {"ok": tokenize(C.IPerm.R | C.IPerm.W) != tokenize(C.IPerm.R | C.IPerm.X)})


# 上面这些 token 相撞时的用户可见后果：同一个 pure delayed 函数、两个参数一起 compute
def consequence(label, fn, x, y, expect):
    def f():
        dx, dy = dask.delayed(fn, pure=True)(x), dask.delayed(fn, pure=True)(y)
        got = dask.compute(dx, dy, scheduler="sync")
        return {"ok": tuple(got) == expect, "keys_equal": dx.key == dy.key, "got": list(got)}
    run(f"consequence:{label}", "R2", f)


consequence("xclass type_name(Color.RED, Light.RED)", F.type_name, C.Color.RED, C.Light.RED, ("Color", "Light"))
consequence("xclass type_name(Color.RED, Shape.CIRCLE)", F.type_name, C.Color.RED, C.Shape.CIRCLE, ("Color", "Shape"))
consequence("raw type_name(Color.RED, 1)", F.type_name, C.Color.RED, 1, ("Color", "int"))
consequence("flag value_of(R|W, R|X)", F.value_of, C.Perm.R | C.Perm.W, C.Perm.R | C.Perm.X, (3, 5))
consequence("flag value_of(R|W, Perm(0))", F.value_of, C.Perm.R | C.Perm.W, C.Perm(0), (3, 0))


# ---------- 跨进程稳定（不同 PYTHONHASHSEED 的两个新进程） ----------
CROSS = ["Color.RED", "Perm.R | Perm.W", "IColor.RED", "SColor.RED", "Planet.EARTH", "Conf.A",
         "Tags.A", "Sentinel.MISSING", "Hooked.A"]
code = ("import sys, json; sys.path.insert(0, %r)\n"
        "from audit_core import *\nfrom dask.base import tokenize\n"
        "print(json.dumps({e: tokenize(eval(e)) for e in %r}))") % (MODDIR, CROSS)
outs = []
for seed in ("1", "2"):
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       env={**os.environ, "PYTHONHASHSEED": seed})
    outs.append(json.loads(r.stdout) if r.returncode == 0 else {"error": r.stderr[-300:]})
for e in CROSS:
    run(f"crossproc:{e}", "R1-crossproc", lambda e=e: {
        "ok": all(e in o for o in outs) and outs[0][e] == outs[1][e]})

# ---------- 与已有注册、钩子的交互 ----------
run("hook:__dask_tokenize__ honored", "hook", lambda: {
    "ok": None, "honored": normalize_token(C.Hooked.A) == ("hooked", "A"), "norm": norm(C.Hooked.A)})


def user_register():
    normalize_token.register(C.Registered)(lambda e: ("registered", e.name))
    return {"ok": normalize_token(C.Registered.A) == ("registered", "A"), "norm": norm(C.Registered.A)}
run("register:user normalize_token.register(MyEnum) wins", "hook", user_register)
run("mixin:IntEnum/IntFlag/str normalized text", "info", lambda: {
    "ok": None, "IColor.RED": norm(C.IColor.RED), "IPerm.R|W": norm(C.IPerm.R | C.IPerm.W),
    "SColor.RED": norm(C.SColor.RED), "tok_IColor.RED": tokenize(C.IColor.RED)})
run("class:Enum class objects A.Color~B.Color (pre-existing)", "info", lambda: {
    "ok": None, "equal": tokenize(A.Color) == tokenize(B.Color), "norm": norm(A.Color)})
run("class:plain class objects A.Plain~B.Plain", "info", lambda: {
    "ok": None, "equal": tokenize(A.Plain) == tokenize(B.Plain), "norm": norm(A.Plain)})
run("norm:gold-like representation of A.Color.RED", "info", lambda: {
    "ok": None, "A": norm(A.Color.RED), "B": norm(B.Color.RED)})

# ---------- 决定性对照：不同模块、同名同值的 Color.RED ----------
EXPECT = ("audit_a", "audit_b")


def pair_delayed(fn, x, y, **kw):
    dx, dy = dask.delayed(fn, **kw)(x), dask.delayed(fn, **kw)(y)
    return dx, dy


def samename_token():
    return {"ok": None, "tokens_equal": tokenize(A.Color.RED) == tokenize(B.Color.RED),
            "stable_a": tokenize(A.Color.RED) == tokenize(A.Color.RED)}
run("samename:token A.Color.RED~B.Color.RED", "samename", samename_token)


def samename_pure(sched):
    def f():
        dx, dy = pair_delayed(F.which, A.Color.RED, B.Color.RED, pure=True)
        got = dask.compute(dx, dy, scheduler=sched)
        return {"ok": tuple(got) == EXPECT, "keys_equal": dx.key == dy.key, "got": list(got),
                "key": dx.key}
    return f
run("samename:pure delayed which() compute together sync", "samename", samename_pure("sync"))
run("samename:pure delayed which() compute together threads", "samename", samename_pure("threads"))


def samename_single():
    dx, dy = pair_delayed(F.which, A.Color.RED, B.Color.RED, pure=True)
    got = (dx.compute(scheduler="sync"), dy.compute(scheduler="sync"))
    return {"ok": got == EXPECT, "got": list(got)}
run("samename:pure delayed computed separately", "samename", samename_single)


def samename_method():
    dx, dy = pair_delayed(F.describe, A.Color.RED, B.Color.RED, pure=True)
    got = dask.compute(dx, dy, scheduler="sync")
    return {"ok": tuple(got) == EXPECT, "keys_equal": dx.key == dy.key, "got": list(got)}
run("samename:pure delayed e.describe() compute together", "samename", samename_method)


def samename_impure():
    dx, dy = pair_delayed(F.which, A.Color.RED, B.Color.RED)  # pure 默认 False
    got = dask.compute(dx, dy, scheduler="sync")
    return {"ok": tuple(got) == EXPECT, "keys_equal": dx.key == dy.key, "got": list(got)}
run("samename:default (impure) delayed", "samename", samename_impure)


def samename_eq():
    v = dask.delayed(F.pick)(A.Color.RED)  # 值本身不 pure；== 运算符在 Delayed 上固定按 pure 建 key
    ea, eb = (v == A.Color.RED), (v == B.Color.RED)
    got = dask.compute(ea, eb, scheduler="sync")
    return {"ok": tuple(got) == (True, False), "keys_equal": ea.key == eb.key, "got": list(got)}
run("samename:Delayed == operator (always pure)", "samename", samename_eq)


def samename_getitem():
    d = dask.delayed(F.as_dict)(A.Color.RED, B.Color.RED)
    ga, gb = d[A.Color.RED], d[B.Color.RED]
    got = dask.compute(ga, gb, scheduler="sync")
    return {"ok": tuple(got) == ("from audit_a", "from audit_b"), "keys_equal": ga.key == gb.key,
            "got": list(got)}
run("samename:Delayed [] getitem (always pure)", "samename", samename_getitem)


def samename_map_blocks():
    x = da.arange(4, chunks=2)
    x1 = x.map_blocks(F.tag_blocks, color=A.Color.RED, dtype=x.dtype)
    x2 = x.map_blocks(F.tag_blocks, color=B.Color.RED, dtype=x.dtype)
    r1, r2 = dask.compute(x1, x2, scheduler="sync")
    diff = (x1 - x2).compute(scheduler="sync")
    ok = r1.tolist() == [100, 101, 102, 103] and r2.tolist() == [200, 201, 202, 203] and diff.tolist() == [-100] * 4
    return {"ok": ok, "names_equal": x1.name == x2.name, "r1": r1.tolist(), "r2": r2.tolist(),
            "x1_minus_x2": diff.tolist()}
run("samename:map_blocks(color=...) names and results", "samename", samename_map_blocks)


def samename_kind(get, label, fn=F.which, expect=EXPECT):
    def f():
        xa, xb = get(A), get(B)
        dx, dy = pair_delayed(fn, xa, xb, pure=True)
        got = dask.compute(dx, dy, scheduler="sync")
        return {"ok": tuple(got) == expect, "tokens_equal": tokenize(xa) == tokenize(xb),
                "keys_equal": dx.key == dy.key, "got": list(got), "norm": norm(xa)}
    run(f"samename:{label}", "samename", f)


samename_kind(lambda m: m.IColor.RED, "IntEnum IColor.RED (base path unchanged)")
samename_kind(lambda m: m.Perm.R, "Flag Perm.R")
samename_kind(lambda m: m.Hook.A, "user __dask_tokenize__ hook Hook.A")


def nested():
    ta, tb = tokenize(N.Reader.Mode.FAST), tokenize(N.Writer.Mode.FAST)
    return {"ok": None, "tokens_equal": ta == tb, "norm": [norm(N.Reader.Mode.FAST), norm(N.Writer.Mode.FAST)]}
run("samename:nested Reader.Mode.FAST~Writer.Mode.FAST (same module)", "samename-info", nested)


def local_classes():
    from enum import Enum, Flag
    c1, c2, f1 = N.make_local(Enum), N.make_local(Enum), N.make_local(Flag)
    return {"ok": None, "enum_enum_equal": tokenize(c1.RED) == tokenize(c2.RED),
            "enum_flag_equal": tokenize(c1.RED) == tokenize(f1.RED), "norm": norm(c1.RED)}
run("samename:local classes from the same function (like the test)", "samename-info", local_classes)

emit({"case": "_env", "group": "info", "ok": None, "python": sys.version.split()[0], "numpy": np.__version__,
      "dask": dask.__version__, "dask_file": dask.__file__})
