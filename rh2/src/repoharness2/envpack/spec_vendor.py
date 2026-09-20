"""vendor spec 的固定注册表与只读加载（S2-1 T2，codex 轮次 12 问题 2）。

安全模型：artifact（bundle）里**不携带可执行文件路径**——`spec_vendor_id`
是封闭枚举，本注册表把它映射到**固定的仓库相对路径 + pinned sha256**；
运行期只读取构建期提取的规范化 JSON（`extract_vendor_specs.py` 一次性产出），
**永不 exec vendored Python**。`eval_cmd` 的权威 = 本注册表按
`(vendor_id, repo_key_lower, version)` 派生；bundle 内的 `eval_cmd` 字段只是
信息性副本，消费方必须用 `derive_eval_cmd` 重新派生并互检（不一致即拒）。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from importlib.resources import files as _pkg_files

SPEC_VENDOR_ID_SWEGYM_242429C1 = "swegym_constants_242429c1"


@dataclass(frozen=True)
class VendorPin:
    """一个 vendor 资产的固定身份（路径与 digest 都不接受外部输入）。

    运行期 JSON 是**包内数据**（envpack/data/，随 wheel 发布，
    importlib.resources 读取——codex 轮次 13：推算仓库根在安装态必坏）；
    原始 vendored Python / provenance / LICENSE 是 docs 下的审计资产。
    """

    json_package_name: str     # 规范化 JSON 的包内文件名（envpack/data/ 下）
    json_sha256: str
    source_py_relpath: str     # 原始 vendored Python（仓库审计资产，非运行期依赖）
    source_py_sha256: str
    source_commit: str


VENDOR_REGISTRY: dict[str, VendorPin] = {
    SPEC_VENDOR_ID_SWEGYM_242429C1: VendorPin(
        json_package_name="swegym_specs_242429c1.json",
        json_sha256="0da8f9caeec18e3b41386fb66e677807335c0fe12c41d811dd9fb65f9bfcc925",
        source_py_relpath=(
            "docs/agentic_RL/repo_harness_rh2_workstreams/s2/vendor/"
            "swegym_constants_242429c1.py"
        ),
        source_py_sha256="5bd655172c9a9dfcb494d9c52bcbcc0d79a59cd20c39b8bbdc41ab8b0a9baf14",
        source_commit="242429c188fcfd06aad13fce9a54d450470bf0ac",
    ),
}


class VendorSpecError(ValueError):
    """vendor 资产缺失 / digest 不符 / (repo, version) 无 spec。"""


def vendor_pin(vendor_id: str) -> VendorPin:
    if vendor_id not in VENDOR_REGISTRY:
        raise VendorSpecError(f"未知 spec_vendor_id: {vendor_id!r}（封闭注册表，不接受外部路径）")
    return VENDOR_REGISTRY[vendor_id]


def load_vendor_specs(vendor_id: str) -> dict[str, dict[str, dict]]:
    """读包内 pinned JSON（sha256 必须命中注册表）→ {repo_key_lower: {version: spec}}。"""
    pin = vendor_pin(vendor_id)
    resource = _pkg_files("repoharness2.envpack") / "data" / pin.json_package_name
    if not resource.is_file():
        raise VendorSpecError(f"vendor JSON 包内缺失: envpack/data/{pin.json_package_name}")
    data = resource.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != pin.json_sha256:
        raise VendorSpecError(
            f"vendor JSON digest 不符（actual {actual[:16]}… != pin {pin.json_sha256[:16]}…）"
        )
    return json.loads(data)


def lookup_spec(vendor_id: str, repo_key_lower: str, version: str) -> dict:
    """按 (vendor_id, repo_key_lower, version) 取 spec；键必须已是小写投影。"""
    if repo_key_lower != repo_key_lower.lower():
        raise VendorSpecError(f"repo_key_lower 未小写化: {repo_key_lower!r}")
    specs = load_vendor_specs(vendor_id)
    repo_specs = specs.get(repo_key_lower)
    if repo_specs is None:
        raise VendorSpecError(f"vendor 无该仓库: {repo_key_lower!r}")
    spec = repo_specs.get(version)
    if spec is None:
        raise VendorSpecError(f"vendor 无 ({repo_key_lower!r}, {version!r}) 的 spec")
    return spec


def derive_eval_cmd(vendor_id: str, repo_key_lower: str, version: str) -> str:
    """eval_cmd 的唯一权威派生。消费方拿 bundle 时必须重派生并与其字段互检。"""
    spec = lookup_spec(vendor_id, repo_key_lower, version)
    cmd = spec.get("test_cmd")
    if not cmd or not isinstance(cmd, str):
        raise VendorSpecError(f"({repo_key_lower!r}, {version!r}) 的 spec 缺 test_cmd")
    return cmd


def verify_grading_eval_cmd(bundle) -> None:
    """互检入口：bundle 的 eval_cmd 与 python_version 都必须等于注册表派生值
    （轮次 13 定 eval_cmd；轮次 15 一般 3 补 python_version——凡声称来自
    vendor 的字段消费时一律重派生互检，不一致即拒）。"""
    derived = derive_eval_cmd(bundle.spec_vendor_id, bundle.repo_key_lower, bundle.version)
    if bundle.eval_cmd != derived:
        raise VendorSpecError(
            f"{bundle.instance_id}: eval_cmd 与注册表派生值不符"
            f"（bundle {bundle.eval_cmd!r} != derived {derived!r}）——自由字符串不作权威"
        )
    spec = lookup_spec(bundle.spec_vendor_id, bundle.repo_key_lower, bundle.version)
    derived_py = str(spec["python"]) if spec.get("python") is not None else None
    if bundle.python_version != derived_py:
        raise VendorSpecError(
            f"{bundle.instance_id}: python_version 与注册表派生值不符"
            f"（bundle {bundle.python_version!r} != derived {derived_py!r}）"
        )


# ---------------------------------------------------------------------------
# S1-a（评分接线 2026-09-15）：来源配方的其余派生——安装命令、eval_commands、测试选择器。
# 全部从同一份 pinned JSON 读取（注册表不变）；测试选择规则逐字对齐 fork 242429c1 的
# `test_spec.make_test_command` 与 `utils.get_test_directives`：
#   - python/mypy：用 test_patch 里 `[case X]` 的名字拼 `-k "A or B"`，**不带测试文件**；
#   - 其余仓库：`test_cmd + 按 NON_TEST_EXTS 剔除资源文件后的 test_patch 触碰路径`。
# 216 题的官方行契约见 docs/.../B_materials_20260908/official_cmd_contract_216.json（测试逐字比对）。
# 注意：测试选择器剔除资源文件，**不改变**可信 setup 要恢复/保护的 official 测试文件清单
# （那仍是 test_patch 触碰的全部路径——资源文件是官方测试的 fixture）。
# ---------------------------------------------------------------------------

# fork constants.NON_TEST_EXTS（242429c1）逐字；"csv" 无点号是上游原样（endswith 语义下等价于 *.csv 与 *csv）。
NON_TEST_EXTS: tuple[str, ...] = (
    ".json", ".png", "csv", ".txt", ".md", ".jpg", ".jpeg", ".pkl", ".yml", ".yaml", ".toml",
)

# fork utils.get_test_directives 的文件识别正则（逐字）。
_DIFF_DIRECTIVE_PATTERN = r"diff --git a/.* b/(.*)"
# fork test_spec.make_test_command 的 mypy case 名正则（逐字）。
_MYPY_CASE_PATTERN = r"\[case ([^\]]+)\]"


def derive_install_cmd(vendor_id: str, repo_key_lower: str, version: str) -> str | None:
    """来源 spec 的 `install` 字符串（官方 eval 脚本里逐字执行的那一行；缺失 = None，
    官方脚本此时不含安装步骤）。多命令用 `;` 串联，段末退出码只代表最后一个命令。"""
    spec = lookup_spec(vendor_id, repo_key_lower, version)
    cmd = spec.get("install")
    if cmd is None:
        return None
    if not isinstance(cmd, str) or not cmd.strip():
        raise VendorSpecError(f"({repo_key_lower!r}, {version!r}) 的 install 不是非空字符串")
    return cmd


def derive_eval_commands(vendor_id: str, repo_key_lower: str, version: str) -> tuple[str, ...]:
    """来源 spec 的 `eval_commands`（官方脚本在激活环境后、任何 git 操作前逐条执行；
    例：conan 的 `export PYTHONPATH=${PYTHONPATH:-}:$(pwd)`）。缺失 = 空元组。"""
    spec = lookup_spec(vendor_id, repo_key_lower, version)
    cmds = spec.get("eval_commands")
    if cmds is None:
        return ()
    if not isinstance(cmds, list) or not all(isinstance(c, str) and c.strip() for c in cmds):
        raise VendorSpecError(f"({repo_key_lower!r}, {version!r}) 的 eval_commands 不是非空字符串列表")
    return tuple(cmds)


def derive_test_directives(repo_key_lower: str, test_patch: str) -> list[str]:
    """fork utils.get_test_directives 的逐字实现（按 repo 小写键判断特例）。"""
    import re

    if repo_key_lower == "swe-bench/humaneval":
        return ["test.py"]
    directives = re.findall(_DIFF_DIRECTIVE_PATTERN, test_patch)
    directives = [d for d in directives if not any(d.endswith(ext) for ext in NON_TEST_EXTS)]
    if repo_key_lower == "django/django":
        transformed = []
        for d in directives:
            d = d[: -len(".py")] if d.endswith(".py") else d
            d = d[len("tests/"):] if d.startswith("tests/") else d
            d = d.replace("/", ".")
            transformed.append(d)
        directives = transformed
    return directives


def derive_test_command(vendor_id: str, repo_key_lower: str, version: str, test_patch: str) -> str:
    """官方 eval 脚本里的测试命令行（fork test_spec.make_test_command 逐字语义）。"""
    import re

    test_cmd = derive_eval_cmd(vendor_id, repo_key_lower, version)
    if repo_key_lower == "python/mypy":
        keys = re.findall(_MYPY_CASE_PATTERN, test_patch)
        return test_cmd + " " + f'"{" or ".join(keys)}"'
    return " ".join([test_cmd, *derive_test_directives(repo_key_lower, test_patch)])


def derive_test_command_for_bundle(bundle) -> str:
    """bundle 形态入口：先互检 eval_cmd/python_version（既有防线），再派生测试命令。"""
    verify_grading_eval_cmd(bundle)
    return derive_test_command(bundle.spec_vendor_id, bundle.repo_key_lower, bundle.version, bundle.test_patch)


# S1-m（评分接线 2026-09-15）：候选段之后 root 观测"安装是否作用于候选"用的导入探针模块名（只进诊断，不改判定）。
IMPORT_PROBE_MODULES: dict[str, str] = {
    "python/mypy": "mypy",
    "getmoto/moto": "moto",
    "conan-io/conan": "conans",
    "modin-project/modin": "modin",
    "project-monai/monai": "monai",
    "iterative/dvc": "dvc",
    "dask/dask": "dask",
    "pydantic/pydantic": "pydantic",
    "pandas-dev/pandas": "pandas",
}


def derive_import_probe_module(repo_key_lower: str) -> str | None:
    """仓库 → 顶层导入名（缺席 = 不做导入探针）。"""
    return IMPORT_PROBE_MODULES.get(repo_key_lower)
