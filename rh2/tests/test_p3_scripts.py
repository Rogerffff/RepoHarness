"""pytest 收集入口：P3 预实验脚本包静态验证。

实体在 tests/check_p3_scripts.py（任务书指定文件名，不匹配 pytest 默认
`test_*.py` 收集模式）；本文件 re-export 使 `uv run pytest tests/ -q`
全套自动收集。单独跑也可以：`uv run pytest tests/check_p3_scripts.py -q`。
"""

from check_p3_scripts import *  # noqa: F401,F403
