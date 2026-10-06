"""公开复现：datalad 16c1ffc3 —— 自定义 result_filter 收不到 API 调用的 kwargs（如 dataset）。
依据：公开题面示例。题面用的 Test_Utils 定义在公开测试模块 datalad/interface/tests/test_utils.py；为不依赖测试
模块，这里按其公开定义写一个等价的最小命令类（Interface + datasetmethod + eval_results，产出 status=ok 的结果）。
只观测，不写 /testbed。导入：先普通导入并记录，失败再把 cwd 加进 sys.path。"""
import os
import sys

sys.dont_write_bytecode = True
try:
    import datalad
    print("IMPORT_PLAIN=ok %s" % datalad.__file__)
except ImportError as exc:
    print("IMPORT_PLAIN=fail (%s: %s); retry with cwd %s on sys.path" % (type(exc).__name__, exc, os.getcwd()))
    sys.path.insert(0, os.getcwd())
from datalad.distribution.dataset import datasetmethod
from datalad.interface.base import Interface
from datalad.interface.utils import eval_results


class Repro_Cmd(Interface):
    @staticmethod
    @datasetmethod(name="repro_cmd_16c1")
    @eval_results
    def __call__(number, dataset=None):
        for i in range(number):
            yield {"path": "some", "status": "ok", "somekey": i}


def custom_filter(res, **kwargs):
    assert "dataset" in kwargs, "'dataset' not found in %r" % (kwargs,)
    return True


try:
    out = Repro_Cmd().__call__(4, dataset="awesome", result_filter=custom_filter)
    print("RESULT_LEN=%d" % len(out))
    print("REPRO_OBSERVED=0 (filter received dataset kwarg)")
except AssertionError as exc:
    print("EXC=AssertionError: %s" % exc)
    print("REPRO_OBSERVED=1")
