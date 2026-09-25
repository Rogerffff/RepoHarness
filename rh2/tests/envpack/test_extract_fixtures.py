"""`scripts/r2e_env/extract_fixtures.py`：从 conftest 链原样摘出缺失 fixture（T0-6 私有 conftest 的来源工具）。"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "r2e_env" / "extract_fixtures.py"

OUTER = '''import numpy as np
import pytest

from pandas import DataFrame

N = 3


def _make():
    return DataFrame(np.arange(N))


@pytest.fixture
def base_frame():
    return _make()


@pytest.fixture(params=[1, 2])
def frame(request, base_frame):
    return base_frame * request.param


@pytest.fixture(autouse=True)
def configure():
    pass
'''
INNER = '''import pytest


@pytest.fixture
def frame(base_frame):
    """内层覆盖外层。"""
    return base_frame + 1
'''


@pytest.fixture(scope="module")
def ex():
    saved = list(sys.path)
    spec = importlib.util.spec_from_file_location("extract_fixtures_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module   # dataclass 解析注解要能在 sys.modules 里找到本模块
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)
        sys.path[:] = saved


def test_innermost_definition_wins_and_dependencies_come_along_verbatim(ex):
    chain = [ex.Module.parse("pkg/conftest.py", OUTER), ex.Module.parse("pkg/tests/conftest.py", INNER)]
    picked = ex.extract(chain, ["frame"])
    text = ex.render(chain, picked, header=["测试"], blobs={"pkg/conftest.py": "abc"})
    ast.parse(text)
    assert "return base_frame + 1" in text and "base_frame * request.param" not in text   # 取内层 frame
    assert "def base_frame():" in text and "def _make():" in text and "N = 3" in text      # 传递依赖都带上
    assert "import numpy as np" in text and "from pandas import DataFrame" in text          # 只带用到的导入
    assert "def configure" not in text                                                       # autouse 不带
    for line in ("def _make():\n    return DataFrame(np.arange(N))\n",):
        assert line in text                                                                  # 原文逐行不改


def test_missing_or_autouse_fixture_is_refused(ex):
    chain = [ex.Module.parse("pkg/conftest.py", OUTER)]
    with pytest.raises(ex.ExtractError, match="找不到"):
        ex.extract(chain, ["no_such_fixture"])
    with pytest.raises(ex.ExtractError, match="autouse"):
        ex.extract(chain, ["configure"])


def test_local_variable_with_a_fixture_name_does_not_drag_that_fixture_in(ex):
    """pandas `idx` fixture 的函数体里有局部变量 `index_names`，同名的模块级 fixture 不应被带进来。"""
    src = (
        "import pytest\n\n\n"
        "@pytest.fixture\ndef idx():\n    index_names = ['a', 'b']\n    return index_names\n\n\n"
        "@pytest.fixture\ndef index_names():\n    return ['a', 'b']\n"
    )
    chain = [ex.Module.parse("pkg/conftest.py", src)]
    text = ex.render(chain, ex.extract(chain, ["idx"]), header=[], blobs={})
    assert "def idx():" in text and "def index_names():" not in text


HIDDEN_TESTS = '''import pytest

from pandas.tests.indexing.common import Base


@pytest.fixture
def local_frame(frame, tmp_path):
    return frame


@pytest.fixture
def unused_local(never_requested):
    return never_requested


@pytest.mark.parametrize("how", ["inner", "outer"])
def test_merge(how, join_type, local_frame):
    pass


@pytest.mark.usefixtures("configure_bits")
class TestThing:
    @pytest.mark.parametrize("names, sort", [(1, 2)])
    def test_a(self, names, sort, names_fixture):
        pass

    def helper(self, not_a_fixture):
        pass


class TestInherited(Base):
    def test_b(self, request):
        request.getfixturevalue("dynamic")
'''


def test_requested_fixtures_collects_every_fixture_a_test_asks_for_at_once(ex):
    """pytest 每个用例只报第一个缺的 fixture（T0-6 第二步 32dd55cb / 7dd34ea7 第一版草稿因此漏补）；静态分析一次算全。"""
    req = ex.requested_fixtures(HIDDEN_TESTS)
    # 参数化给值的名字、本模块 fixture、内置 fixture 不算；本模块 fixture 的依赖（frame）算；没被请求的本模块 fixture 的依赖不算
    assert req.names == {"join_type", "frame", "configure_bits", "names_fixture"}
    assert any("TestInherited" in note and "Base" in note for note in req.review)
    assert any("getfixturevalue" in note for note in req.review)
