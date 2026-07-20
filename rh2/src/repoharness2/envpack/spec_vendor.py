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
