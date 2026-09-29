"""dask__dask-8801 私有行为矩阵（不交给求解者）。在候选已套用的 /testbed 中运行，输出一行 JSON。

覆盖：
- 单文件目录下各种内容：正常映射、映射内含字符串/列表/null、空文件、全注释、显式 null、四种假值非映射、
  两种语法错误、顶层 list / str / 缺冒号的 str / int；
  每项记录 collect_yaml 的结果或异常类型、消息里是否含路径（原样 / repr）、原测试的三个英文词组、
  解析器原因是否出现在渲染后的 traceback 中、警告；再记录 collect(paths, env={}) 的结果（原缺陷在 merge 处）；
- 两文件目录（坏文件 a.yaml 排在正常文件 b.yaml 之前）：报错指向哪个文件；
- 直接给文件路径而不是目录；
- 新进程 import dask：隔离 HOME 与 DASK_ROOT_CONFIG，DASK_CONFIG 指向坏文件目录、ensure_file(comment=True) 产物目录、
  正常映射目录。
权限分支需要非 root，另由 pytest 以 nobody 身份运行公开测试覆盖。
"""

import json
import os
import subprocess
import sys
import tempfile
import traceback
import warnings

import yaml

from dask.config import collect, collect_yaml, ensure_file, merge

PHRASES = ["is malformed", "original error message", "must have a dict"]
CASES = {
    "mapping": b"x: 1\ny:\n  a: 2\n",
    "mapping_nested_values": b"x: some string\ny: [1, 2]\nz: null\n",
    "empty": b"",
    "comment_only": b"# x: 1\n#   y: 2\n",
    "explicit_null": b"null\n",
    "falsy_zero": b"0\n",
    "falsy_false": b"false\n",
    "falsy_empty_list": b"[]\n",
    "falsy_empty_str": b"''\n",
    "syntax_brace": b"{",
    "syntax_tab": b"a: 1\n\tb: 2\n",
    "list": b"[1234]",
    "str": b"a plain string\n",
    "str_missing_colon": b"distributed.worker.memory.target 0.6\n",
    "int": b"1234\n",
}


def parser_problem(content: bytes):
    try:
        yaml.safe_load(content.decode())
    except yaml.YAMLError as exc:
        return getattr(exc, "problem", None) or str(exc)
    return None


def describe(exc: BaseException, path: str, problem):
    msg = str(exc)
    rendered = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    rest = msg.replace(path, "").lower()
    return {
        "exc": type(exc).__name__,
        "msg": msg[:300],
        "path_in_msg": path in msg,
        "repr_path_in_msg": repr(path) in msg,
        "phrases": {p: (p in msg) for p in PHRASES},
        "problem_in_msg": (problem in msg) if problem else None,
        "problem_in_rendered_tb": (problem in rendered) if problem else None,
        "mentions_dict_or_mapping": ("dict" in rest or "mapping" in rest),
    }


def run_case(content: bytes, extra_after: bool = False, direct_file: bool = False):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "a.yaml")
        with open(p, "wb") as f:
            f.write(content)
        if extra_after:
            with open(os.path.join(d, "b.yaml"), "wb") as f:
                f.write(b"b_key: 1\n")
        target = p if direct_file else d
        problem = parser_problem(content)
        out = {}
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                res = collect_yaml(paths=[target])
                out["collect_yaml"] = {"exc": None, "result": repr(res)[:200], "merged": repr(merge(*res))[:200]}
            except Exception as exc:
                out["collect_yaml"] = describe(exc, p, problem)
                if extra_after:
                    out["collect_yaml"]["names_b_instead"] = os.path.join(d, "b.yaml") in str(exc)
            out["warnings"] = [
                {"cat": x.category.__name__, "path_in_msg": p in str(x.message), "msg": str(x.message)[:200]} for x in w
            ]
        try:
            res = collect(paths=[target], env={})
            out["collect"] = {"exc": None, "result": repr(res)[:200]}
        except Exception as exc:
            out["collect"] = {"exc": type(exc).__name__, "msg": str(exc)[:200], "path_in_msg": p in str(exc)}
        return out


def fresh_import(dask_config_dir: str, probe: str = "import dask"):
    with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as root_cfg:
        env = dict(os.environ, HOME=home, DASK_ROOT_CONFIG=root_cfg, DASK_CONFIG=dask_config_dir)
        env.pop("PYTHONWARNINGS", None)
        r = subprocess.run([sys.executable, "-W", "always", "-c", probe], env=env, capture_output=True, text=True, cwd="/")
        err = [ln for ln in r.stderr.strip().splitlines() if ln.strip()]
        return {"rc": r.returncode, "stdout": r.stdout.strip()[-200:], "stderr_tail": err[-2:] if err else []}


result = {"cases": {}, "order": {}, "direct_file": {}, "fresh_import": {}}
for name, content in CASES.items():
    result["cases"][name] = run_case(content)
for name in ["list", "str", "int"]:
    result["order"][name] = run_case(CASES[name], extra_after=True)
for name in ["str", "syntax_brace"]:
    result["direct_file"][name] = run_case(CASES[name], direct_file=True)

with tempfile.TemporaryDirectory() as d:
    with open(os.path.join(d, "a.yaml"), "wb") as f:
        f.write(CASES["str_missing_colon"])
    result["fresh_import"]["bad_str_dir"] = fresh_import(d)
with tempfile.TemporaryDirectory() as d:
    with open(os.path.join(d, "a.yaml"), "wb") as f:
        f.write(CASES["syntax_brace"])
    result["fresh_import"]["bad_syntax_dir"] = fresh_import(d)
with tempfile.TemporaryDirectory() as d:
    # 与文档 configuration.rst 所述下游做法相同：把默认配置以全注释形式复制到用户配置目录
    ensure_file(source="/testbed/dask/dask.yaml", destination=d, comment=True)
    result["fresh_import"]["commented_default_dir"] = fresh_import(
        d, "import dask; print(dask.config.get('temporary-directory', 'MISSING'))"
    )
    result["fresh_import"]["commented_default_dir"]["files"] = sorted(os.listdir(d))
with tempfile.TemporaryDirectory() as d:
    with open(os.path.join(d, "a.yaml"), "wb") as f:
        f.write(b"my-probe-key: 42\n")
    result["fresh_import"]["valid_dir"] = fresh_import(d, "import dask; print(dask.config.get('my-probe-key'))")

print(json.dumps(result, ensure_ascii=False))
