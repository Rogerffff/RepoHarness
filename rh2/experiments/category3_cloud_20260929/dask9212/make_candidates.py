"""生成 dask__dask-9212 的候选补丁（私有对照与正式评分用，不交给求解者）。

用法：python make_candidates.py <base 源码目录> <输出目录>
base 目录里需要镜像内 base 提交的 dask/base.py 原件（git show HEAD:dask/base.py）。
每个候选都是对 base 源码的文本替换；替换前断言原文恰好出现一次。

候选按公开要求分三组（判断见 result.md）：
- 合理实现（与 gold 不同）：alt_modqual、alt_hookfirst、alt_up2024、alt_pickle、alt_docs；
- 错误实现：w_value、w_noval、w_hash、w_name；§4 第 3 步退化探测 w_const（固定 token）；
- 边界实现：w_str（只与字符串 "Color.RED" 这类字面值相撞，与 gold 的同名碰撞同属边缘输入）。
"""
import difflib
import sys
from pathlib import Path

REL = "dask/base.py"

IMPORT_BASE = "from contextlib import contextmanager\nfrom functools import partial\n"
IMPORT_ENUM = "from contextlib import contextmanager\nfrom enum import Enum\nfrom functools import partial\n"

ANCHOR = "@normalize_token.register(object)\ndef normalize_object(o):\n"

OBJECT_BASE = '''@normalize_token.register(object)
def normalize_object(o):
    method = getattr(o, "__dask_tokenize__", None)
    if method is not None:
        return method()

    if callable(o):
'''


def registered(body):
    """在 normalize_object 之前插入一个 Enum 注册函数（与 gold 同一位置）。"""
    return f"@normalize_token.register(Enum)\ndef normalize_enum(e):\n{body}\n\n\n" + ANCHOR


CANDIDATES = {
    # 合理替代 1：类用模块名与限定名标识，同短名的不同类不再相撞；值与 gold 一样不再递归规范化
    "alt_modqual": [
        (IMPORT_BASE, IMPORT_ENUM),
        (ANCHOR, registered(
            "    # Identify the class by module and qualified name, so members of\n"
            "    # different Enum classes that share a short name do not collide.\n"
            "    cls = type(e)\n"
            "    return \"enum\", cls.__module__, cls.__qualname__, e.name, e.value")),
    ],
    # 合理替代 2：不注册，在 normalize_object 的 __dask_tokenize__ 检查之后处理 Enum（保留钩子优先）
    "alt_hookfirst": [
        (IMPORT_BASE, IMPORT_ENUM),
        (OBJECT_BASE, '''@normalize_token.register(object)
def normalize_object(o):
    method = getattr(o, "__dask_tokenize__", None)
    if method is not None:
        return method()

    if isinstance(o, Enum):
        cls = type(o)
        return "enum", cls.__module__, cls.__qualname__, o.name, o.value

    if callable(o):
'''),
    ],
    # 合理替代 3（上游式）：仿 dask 2024.2.0，类型取 (短名, 模块)，值递归规范化
    "alt_up2024": [
        (IMPORT_BASE, IMPORT_ENUM),
        (ANCHOR, registered(
            "    cls = type(e)\n"
            "    return \"enum\", (cls.__name__, cls.__module__), e.name, normalize_token(e.value)")),
    ],
    # 合理替代 5（上游 2025 式）：不看短名，pickle 按引用（模块＋限定名＋值）；局部类改用 cloudpickle
    "alt_pickle": [
        (IMPORT_BASE, IMPORT_ENUM),
        (ANCHOR, registered(
            "    # Pickle by reference (module, qualified name and value), as later dask\n"
            "    # releases do; classes that cannot be pickled by reference (e.g. local\n"
            "    # classes) go through cloudpickle, like normalize_function.\n"
            "    try:\n"
            "        return pickle.dumps(e, protocol=4)\n"
            "    except Exception:\n"
            "        import cloudpickle\n"
            "\n"
            "        return cloudpickle.dumps(e, protocol=4)")),
    ],
    # 合理替代 4（文档式）：照 custom-collections.rst 示例 `(Foo, self.a, self.b)`，元组里放类对象本身
    "alt_docs": [
        (IMPORT_BASE, IMPORT_ENUM),
        (ANCHOR, registered("    return type(e), e.name, e.value")),
    ],
    # 错误：只用值。不同类的同值成员、成员与原始值 1 都相撞
    "w_value": [
        (IMPORT_BASE, IMPORT_ENUM),
        (ANCHOR, registered("    return e.value")),
    ],
    # 错误：类短名＋成员名，丢掉值。Python 3.10 下 Flag 组合值的 name 都是 None，全部相撞
    "w_noval": [
        (IMPORT_BASE, IMPORT_ENUM),
        (ANCHOR, registered("    return type(e).__name__, e.name")),
    ],
    # 错误：Enum.__hash__ 即 hash(name)，跨类同名成员相撞，Flag 组合值相撞，跨进程不稳定
    "w_hash": [
        (IMPORT_BASE, IMPORT_ENUM),
        (ANCHOR, registered("    return hash(e)")),
    ],
    # 错误：只用成员名
    "w_name": [
        (IMPORT_BASE, IMPORT_ENUM),
        (ANCHOR, registered("    return e.name")),
    ],
    # §4 第 3 步退化探测：与输入无关的固定结果
    "w_const": [
        (IMPORT_BASE, IMPORT_ENUM),
        (ANCHOR, registered("    return \"enum\"")),
    ],
    # 边界：str(e) 形如 "Color.RED"，与同内容的字符串参数相撞
    "w_str": [
        (IMPORT_BASE, IMPORT_ENUM),
        (ANCHOR, registered("    return str(e)")),
    ],
}


def main():
    base_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    original = (base_dir / REL).read_text()
    for name, edits in CANDIDATES.items():
        text = original
        for old, new in edits:
            assert text.count(old) == 1, (name, old[:60], text.count(old))
            text = text.replace(old, new)
        diff = difflib.unified_diff(original.splitlines(keepends=True), text.splitlines(keepends=True),
                                    fromfile=f"a/{REL}", tofile=f"b/{REL}")
        (out_dir / f"{name}.patch").write_text(f"diff --git a/{REL} b/{REL}\n" + "".join(diff))
        print(out_dir / f"{name}.patch")


if __name__ == "__main__":
    main()
