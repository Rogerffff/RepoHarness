"""公开复现：datalad 9ba5de09 —— 用 eval_results 装饰的 __call__ 返回 FunctionWrapper 而不是结果列表。
依据：公开题面示例（FakeCommand 原样；FakeCommand().__call__(2) 期望 [0, 1]）。只观测，不写 /testbed。
导入：先普通导入并记录，失败再把 cwd 加进 sys.path。"""
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


class FakeCommand(Interface):

    @staticmethod
    @datasetmethod(name='fake_command')
    @eval_results
    def __call__(number, dataset=None):
        for i in range(number):
            yield i


result = FakeCommand().__call__(2)
print("RESULT_TYPE=%s" % type(result).__name__)
ok = isinstance(result, list) and result == [0, 1]
print("RESULT=%r" % (result if ok else "<%s>" % type(result).__name__,))
print("REPRO_OBSERVED=%d" % (0 if ok else 1))
