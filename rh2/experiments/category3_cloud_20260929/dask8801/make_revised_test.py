"""生成 dask__dask-8801 修订版测试草案（v1–v3）（私有诊断材料，不交给求解者）。

用法：python make_revised_test.py <base test_config.py> <原 test.patch> <输出目录> <v1|v2|v3>
输出：revised_test_<v>.patch（相对 base 的完整 test_patch，测试编号不变）、test_config_revised_<v>.py、
materials_revised_<v>.json（replay_with_install_recipe.py --materials 的输入）。

v2 相对 v1 只多一处：检查“加载失败”时用 warnings.catch_warnings() 忽略警告。原因是 setup.cfg 的
filterwarnings = error:::dask[.*] 会把 dask 发出的警告升级为异常，v1 的 pytest.raises(Exception) 因此把
“警告并跳过”（warn_skip）当成了报错（私有对照 semantic_v2 中 warn_skip 在 v1 下得 1）。
v3 相对 v2 再多一处：在 test_collect_yaml_no_top_level_dict 末尾用新进程执行题面场景 import dask（DASK_CONFIG 指向
含顶层 str 的目录，隔离 HOME 与 DASK_ROOT_CONFIG），要求导入失败且报错点名该文件；拦下“collect_yaml 抛错、
模块导入时捕获并警告”的 import_swallow。

改动（每条对应一个有公开依据的窄问题）：
- R-b：去掉三个英文词组、repr 引号与 ValueError 类型的约束，改为行为断言——报错点名出问题的文件
  （原样路径即可），并说明原因：语法错误时解析器给出的原因在消息或显示的异常链中可见；顶层类型错误时
  消息（去掉路径后）提到 dict / mapping 或实际得到的类型；
- R-c：顶层非映射补题面原例的 str 与一个数字标量（原测试只有 list）；语法错误补一个 ScannerError 实例（原测试只有
  ParserError）；坏文件后面放一个正常文件，报错必须指向坏文件；空文件与全注释文件照常视为空配置。
"""

import hashlib
import json
import sys
from pathlib import Path

base_path, orig_patch_path, out_dir = map(Path, sys.argv[1:4])
VERSION = sys.argv[4]
assert VERSION in ("v1", "v2", "v3")
BASE = base_path.read_text()
ORIG_PATCH = orig_patch_path.read_text()

ANCHOR = """        config = merge(*collect_yaml(paths=[dir_path]))
        assert config == expected


def test_env():
"""
NEW_TESTS = '''        config = merge(*collect_yaml(paths=[dir_path]))
        assert config == expected


def _displayed_error(exc):
    """The text Python shows for ``exc``, including any displayed exception chain."""
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def test_collect_yaml_malformed_file(tmpdir):
    dir_path = str(tmpdir)
    fil_path = os.path.join(dir_path, "a.yaml")

    for content in [b"{", b"a: 1\\n\\tb: 2\\n"]:
        with open(fil_path, mode="wb") as f:
            f.write(content)
        with pytest.raises(yaml.YAMLError) as parse_error:
            yaml.safe_load(content.decode())

        # Loading fails with an error that names the offending file, and the
        # parser's reason stays visible (in the message or the shown chain)
        with pytest.raises(Exception) as rec:
            @@LOAD@@
        assert fil_path in str(rec.value)
        assert parse_error.value.problem in _displayed_error(rec.value)


def test_collect_yaml_no_top_level_dict(tmpdir):
    dir_path = str(tmpdir)
    fil_path = os.path.join(dir_path, "a.yaml")

    # Files that load as nothing (empty, or fully commented out as written by
    # ``ensure_file(..., comment=True)``) are still valid and contribute nothing
    for content in [b"", b"# x: 1\\n"]:
        with open(fil_path, mode="wb") as f:
            f.write(content)
        assert merge(*collect_yaml(paths=[dir_path])) == {}

    # A valid config file that is read after the malformed one
    with open(os.path.join(dir_path, "b.yaml"), mode="wb") as f:
        f.write(b"x: 1\\n")

    for content, type_name in [(b"[1234]", "list"), (b"hello", "str"), (b"1234", "int")]:
        with open(fil_path, mode="wb") as f:
            f.write(content)

        # Loading fails with an error that names the offending file and says
        # that a mapping was expected (or what was found instead)
        with pytest.raises(Exception) as rec:
            @@LOAD@@
        msg = str(rec.value)
        assert fil_path in msg
        rest = msg.replace(fil_path, "").lower()
        assert "dict" in rest or "mapping" in rest or type_name in rest
@@IMPORT_CHECK@@

def test_env():
'''
IMPORT_CHECK = '''
    # The reported scenario: a fresh ``import dask`` that reads such a file
    # fails with this error rather than an unrelated one
    with open(fil_path, mode="wb") as f:
        f.write(b"hello")
    env = dict(
        os.environ,
        DASK_CONFIG=dir_path,
        DASK_ROOT_CONFIG=os.path.join(dir_path, "no-such-dir"),
        HOME=os.path.join(dir_path, "no-such-home"),
    )
    proc = subprocess.run(
        [sys.executable, "-c", "import dask"],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode != 0
    assert fil_path in proc.stderr
'''
NEW_TESTS = NEW_TESTS.replace("@@IMPORT_CHECK@@\n", (IMPORT_CHECK if VERSION == "v3" else "") + "\n")

if VERSION == "v1":
    NEW_TESTS = NEW_TESTS.replace("@@LOAD@@", "collect_yaml(paths=[dir_path])")
    IMPORTS = "import sys\nimport traceback\n"
else:
    # 警告不算加载失败：setup.cfg 会把 dask 的警告升级为异常，这里显式忽略
    NEW_TESTS = NEW_TESTS.replace(
        "@@LOAD@@",
        "with warnings.catch_warnings():\n"
        "                warnings.simplefilter(\"ignore\")\n"
        "                collect_yaml(paths=[dir_path])",
    )
    IMPORTS = "import sys\nimport traceback\nimport warnings\n"
    if VERSION == "v3":
        IMPORTS = "import subprocess\n" + IMPORTS
assert BASE.count(ANCHOR) == 1
REVISED = BASE.replace(ANCHOR, NEW_TESTS)
assert REVISED.count("import sys\n") == 1
REVISED = REVISED.replace("import sys\n", IMPORTS, 1)

out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / f"test_config_revised_{VERSION}.py").write_text(REVISED)

import difflib  # noqa: E402

patch = "diff --git a/dask/tests/test_config.py b/dask/tests/test_config.py\n" + "".join(
    difflib.unified_diff(
        BASE.splitlines(keepends=True),
        REVISED.splitlines(keepends=True),
        "a/dask/tests/test_config.py",
        "b/dask/tests/test_config.py",
    )
)
(out_dir / f"revised_test_{VERSION}.patch").write_text(patch)
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()  # noqa: E731
materials = {
    "version": f"c3-dask8801-diagnosis-semantics-{VERSION}",
    "tasks": {
        "dask__dask-8801": {
            "original_patch_sha256": sha(ORIG_PATCH),
            "test_patch": patch,
            "revised_patch_sha256": sha(patch),
            "reason": (
                "T1: exact phrases, repr() quoting and ValueError class have no public basis (R-b: keep file named + "
                "reason shown). S1: issue's own str top level, ScannerError, error naming a later file, and "
                "empty/commented-out files were not asserted (R-c)."
                + (" v2: warnings are ignored while checking that loading fails (setup.cfg escalates dask warnings)."
                   if VERSION in ("v2", "v3") else "")
                + (" v3: a fresh `import dask` reading such a file must fail and name it (the reported scenario)."
                   if VERSION == "v3" else "")
            ),
            "positive_control": "gold",
        }
    },
}
(out_dir / f"materials_revised_{VERSION}.json").write_text(json.dumps(materials, ensure_ascii=False, indent=1) + "\n")
print(json.dumps({"revised_patch_sha256": sha(patch), "original_patch_sha256": sha(ORIG_PATCH)}, indent=1))
