"""S1-2 拆分方向的钉死测试：envpack 库层 import 时不得引入 verifiers / swebench。

验收条款原文（03-s1-execution-plan.md S1-2）："库层单测不 import verifiers"。
本测试比"测试文件自己不写 import verifiers"更强：在**干净子进程**里 import
envpack 的每个模块，然后检查 sys.modules——只要任何 envpack 模块（或它拉进来的
依赖链）偷偷 import 了 verifiers，这里就会当场失败。swebench 同理（评分依赖
必须保持惰性：EnvConfig 校验 / bundle 加载都不应该要求运行机装 swebench）。

用子进程而不是当前进程的原因：pytest 进程里 tests/contract_verifiers 早就
import 过 verifiers，sys.modules 已被污染，在当前进程里断言毫无意义。
"""

import json
import subprocess
import sys

ENVPACK_MODULES = [
    "repoharness2.envpack",
    "repoharness2.envpack.materialize",
    "repoharness2.envpack.scoring",
    "repoharness2.envpack.bundles",
    "repoharness2.envpack.freeze",
]

_PROBE_TEMPLATE = """
import importlib, json, sys
for name in {modules!r}:
    importlib.import_module(name)
leaked = sorted(
    m for m in sys.modules
    if m == "verifiers" or m.startswith("verifiers.")
    or m == "swebench" or m.startswith("swebench.")
)
print(json.dumps(leaked))
"""


def test_envpack_import_pulls_no_verifiers_or_swebench():
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE_TEMPLATE.format(modules=ENVPACK_MODULES)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"envpack 模块子进程 import 失败:\n{proc.stderr}"
    leaked = json.loads(proc.stdout.strip().splitlines()[-1])
    assert leaked == [], f"envpack import 链泄漏了框架依赖: {leaked}"


def test_envpack_data_loading_needs_no_verifiers_or_swebench():
    """数据面同样框架无关：加载 8 题 + frozen_v1 校验 + digest 重算全程零 verifiers/swebench。"""

    script = """
import json, sys
from repoharness2.envpack import load_bundle_pairs
pairs = load_bundle_pairs()  # 默认对照 frozen_v1，本身就是一次全量防漂移校验
assert len(pairs) == 8, f"冻结题单应为 8 题，得到 {len(pairs)}"
leaked = sorted(
    m for m in sys.modules
    if m.split(".")[0] in ("verifiers", "swebench")
)
print(json.dumps(leaked))
"""
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert proc.returncode == 0, f"envpack 数据加载子进程失败:\n{proc.stderr}"
    leaked = json.loads(proc.stdout.strip().splitlines()[-1])
    assert leaked == [], f"envpack 数据加载泄漏了框架依赖: {leaked}"
