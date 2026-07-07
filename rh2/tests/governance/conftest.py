"""tests/governance 的 pytest 桥接：复用 tests/contracts 的合法样例工厂。

S1-1 的 `tests/contracts/contract_samples.py` 是全仓契约样例的单一事实源
（数值取自真实探针：prompt 15 / 生成 16 / offsets 17）。governance 测试在
它之上组装 gate 输入，因此把 tests/contracts 加进 sys.path——不复制一份
样例文件，避免两份样例漂移。
"""

from __future__ import annotations

import sys
from pathlib import Path

_CONTRACTS_TESTS_DIR = Path(__file__).resolve().parent.parent / "contracts"
if str(_CONTRACTS_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_CONTRACTS_TESTS_DIR))
