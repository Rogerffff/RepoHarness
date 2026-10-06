#!/bin/bash
# 主审 §8 第 3 条原样：脚本必须从 .py 文件运行（inspect.getsource 读不到标准输入里定义的函数）
cat > /tmp/r2e_priv_a95a.py <<'PYEOF'
import sys, warnings
sys.path.insert(0, "/testbed")
from functools import partial
from scrapy.utils.misc import is_generator_with_return_value, warn_on_generator_with_return_value

def g_ret(a, b):
    yield {}
    return 1

def g_none(a, b):
    yield {}

print(is_generator_with_return_value(partial(g_ret, 1)), is_generator_with_return_value(partial(g_none, 1)), is_generator_with_return_value(g_ret))
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    warn_on_generator_with_return_value(None, g_ret)
print(len(w))
PYEOF
cd /testbed && python /tmp/r2e_priv_a95a.py
echo RH2_CMD_RC=$?
