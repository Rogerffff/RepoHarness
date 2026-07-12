"""T1 封板输入 pins：ingestion 可信输入链的根（codex 轮次 14 严重 1）。

问题：T2-c 运行器曾"读当前文件现算 SHA 当 provenance"——raw archive 或
键控清单被一致性修改时，运行器会给改后的数据算出新 SHA 并当作合法来源，
而不是报告"T1 输入漂移"。

方案：`t1_input_pins_v1.json` 是**独立、封板、不可追加**的记录（区别于仍在
追加 T2 产物的 s2_1 总 manifest），固定 T1 关闭时刻七项输入资产的 digest；
该记录自身的 sha256 钉死在本模块常量（本文件被 S1 账本 rglob 追踪，形成
"代码 → pins 记录 → 输入文件"的防篡改链）。任何消费方（ingestion 运行器 /
strict validator / T2-d/e loader）必须先过 `load_and_verify_t1_pins`。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from importlib.resources import files as _pkg_files
from pathlib import Path

# t1_input_pins_v1.json 的仓库相对路径与内容 digest（封板后不许变；变更 =
# 重大事件，须走显式新版本 + 评审，不是改常量）。
T1_PINS_RELPATH = "docs/agentic_RL/repo_harness_rh2_workstreams/s2/t1_input_pins_v1.json"
T1_PINS_SHA256 = "687756035178512974b06986c6a3064b25369104580e5db5c5d4c460d9b053d5"

PINS_SCHEMA_ID = "rh2.s2_1.t1_input_pins.v1"

# 七项封板输入的键（记录内必须恰好这些键，多/少都拒）
EXPECTED_PIN_KEYS = frozenset({
    "raw_archive",            # s2/raw/swe_gym_lite_full_f70b1a29.jsonl
    "image_manifest_keyed",   # s2/image_manifest_keyed.json（T1 关闭态 v4）
    "image_registry_evidence",  # s2/raw/image_registry_evidence.jsonl
    "survivors",              # data_freeze/labels/static_gate_survivors.txt
    "image_refs",             # data_freeze/meta/image_refs_swegym.txt
    "strip_spec",             # data_freeze/strip_spec.yaml
    "vendor_specs_json",      # 包内 envpack/data/swegym_specs_242429c1.json
})


class T1PinsError(ValueError):
    """pins 记录缺失/被改/输入漂移（一律 fail-closed）。"""


@dataclass(frozen=True)
class T1InputPins:
    """已验证的 pins 视图：字段值即七项资产的 sha256（裸 hex）。"""

    raw_archive: str
    image_manifest_keyed: str
    image_registry_evidence: str
    survivors: str
    image_refs: str
    strip_spec: str
    vendor_specs_json: str


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_and_verify_t1_pins(repo_root: Path) -> T1InputPins:
    """三级验证：pins 文件自身 digest → 记录结构 → 七项输入文件逐一比对。"""
    pins_path = repo_root / T1_PINS_RELPATH
    if not pins_path.exists():
        raise T1PinsError(f"T1 pins 记录缺失: {T1_PINS_RELPATH}")
    data = pins_path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != T1_PINS_SHA256:
        raise T1PinsError(
            f"T1 pins 记录 digest 不符（actual {actual[:16]}… != pin {T1_PINS_SHA256[:16]}…）"
            "——封板记录被修改，拒绝一切 ingestion 消费")
    doc = json.loads(data)
    if doc.get("schema_id") != PINS_SCHEMA_ID:
        raise T1PinsError(f"pins schema_id 非法: {doc.get('schema_id')!r}")
    entries = doc.get("pins", {})
    if set(entries) != EXPECTED_PIN_KEYS:
        raise T1PinsError(
            f"pins 键集合不符：多={sorted(set(entries) - EXPECTED_PIN_KEYS)} "
            f"少={sorted(EXPECTED_PIN_KEYS - set(entries))}")

    resolved: dict[str, str] = {}
    for key, ent in entries.items():
        want = ent["sha256"]
        if ent["kind"] == "repo_file":
            p = repo_root / ent["path"]
            if not p.exists():
                raise T1PinsError(f"{key}: 输入文件缺失 {ent['path']}")
            got = _sha256_file(p)
        elif ent["kind"] == "package_data":
            res = _pkg_files("repoharness2.envpack") / "data" / ent["path"]
            if not res.is_file():
                raise T1PinsError(f"{key}: 包内数据缺失 {ent['path']}")
            got = hashlib.sha256(res.read_bytes()).hexdigest()
        else:
            raise T1PinsError(f"{key}: 未知 kind {ent['kind']!r}")
        if got != want:
            raise T1PinsError(
                f"{key}: T1 输入漂移！文件 {got[:16]}… != 封板 pin {want[:16]}…"
                "——不是重算新 provenance 的时机，先人工裁决漂移原因")
        resolved[key] = want
    return T1InputPins(**resolved)
