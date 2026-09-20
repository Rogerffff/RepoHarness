"""vendor spec 资产的机器复算测试（codex 轮次 12 一般 4）。

把 T2-a 报告里的数字变成可重算断言：冻结 raw archive、216 survivor、
vendor JSON 任一变化都会在此直接红灯，而不是只留报告文字。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repoharness2.envpack.spec_vendor import (
    SPEC_VENDOR_ID_SWEGYM_242429C1,
    VendorSpecError,
    derive_eval_cmd,
    load_vendor_specs,
    lookup_spec,
    vendor_pin,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams"
RAW = DOCS / "s2/raw/swe_gym_lite_full_f70b1a29.jsonl"
SURVIVORS_FILE = DOCS / "data_freeze/labels/static_gate_survivors.txt"


@pytest.fixture(scope="module")
def specs():
    return load_vendor_specs(SPEC_VENDOR_ID_SWEGYM_242429C1)


@pytest.fixture(scope="module")
def survivor_rows():
    survivors = {
        s.strip() for s in SURVIVORS_FILE.read_text().splitlines() if s.strip()
    }
    rows = [json.loads(l) for l in RAW.read_text().splitlines() if l.strip()]
    picked = [r for r in rows if r["instance_id"] in survivors]
    assert len(picked) == 216
    return picked


def test_vendor_json_digest_matches_pin(specs):
    # load_vendor_specs 内部已核对 digest；本测试确保加载路径真的走到（非空）
    assert specs, "vendor specs 不应为空"
    pin = vendor_pin(SPEC_VENDOR_ID_SWEGYM_242429C1)
    assert pin.source_commit == "242429c188fcfd06aad13fce9a54d450470bf0ac"


def test_vendor_totals_recomputed(specs):
    assert len(specs) == 33, "仓库数应为 33（T2-a 实测）"
    assert sum(len(v) for v in specs.values()) == 808, "spec 对总数应为 808"


def test_all_vendor_repo_keys_lowercase(specs):
    assert all(k == k.lower() for k in specs), "最终表必须全小写键（fork 末行重绑定语义）"


def test_216_survivors_fully_covered(specs, survivor_rows):
    missing = [
        (r["instance_id"], r["repo"], r["version"])
        for r in survivor_rows
        if r["version"] not in specs.get(r["repo"].lower(), {})
    ]
    assert missing == [], f"survivor spec 缺失: {missing[:5]}"


def test_derive_eval_cmd_for_every_survivor(specs, survivor_rows):
    for r in survivor_rows:
        cmd = derive_eval_cmd(
            SPEC_VENDOR_ID_SWEGYM_242429C1, r["repo"].lower(), r["version"]
        )
        assert cmd.strip(), f"{r['instance_id']}: 空 test_cmd"


def test_lookup_rejects_uppercase_key():
    with pytest.raises(VendorSpecError, match="未小写化"):
        lookup_spec(SPEC_VENDOR_ID_SWEGYM_242429C1, "Project-MONAI/MONAI", "1.0")


def test_official_swebench_covers_zero_of_216(survivor_rows):
    swebench_constants = pytest.importorskip(
        "swebench.harness.constants",
        reason="official swebench 未安装（swe 依赖组），跳过官方零覆盖复算",
    )
    official = swebench_constants.MAP_REPO_VERSION_TO_SPECS
    covered = [
        r["instance_id"]
        for r in survivor_rows
        if r["version"] in official.get(r["repo"], {})
        or r["version"] in official.get(r["repo"].lower(), {})
    ]
    assert covered == [], f"官方表意外覆盖: {covered[:5]}（风险 F 前提变化，需复核）"


# ---- 轮次 13：包内数据 + 重提取逐字节等价 --------------------------------------

def test_vendor_json_is_package_data():
    """运行期 JSON 必须是包内资源（wheel 安装态可用），不靠仓库根推算。"""
    from importlib.resources import files
    pin = vendor_pin(SPEC_VENDOR_ID_SWEGYM_242429C1)
    res = files("repoharness2.envpack") / "data" / pin.json_package_name
    assert res.is_file(), "vendor JSON 不在包内 data/——wheel 安装后 load_vendor_specs 必坏"


def test_reextraction_byte_identical_to_package_json():
    """vendored Python（digest 锁定）重新提取后必须逐字节等于包内 JSON——
    防两个 pin 分别更新造成语义脱节（codex 轮次 13 一般 3）。
    exec 只发生在测试/构建期，运行期仍只读 JSON。"""
    import hashlib as _h
    import importlib.util
    import json as _json
    import warnings
    from importlib.resources import files

    pin = vendor_pin(SPEC_VENDOR_ID_SWEGYM_242429C1)
    py = REPO_ROOT / pin.source_py_relpath
    assert _h.sha256(py.read_bytes()).hexdigest() == pin.source_py_sha256
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        spec = importlib.util.spec_from_file_location("swegym_constants_reextract", py)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    payload = (_json.dumps(mod.MAP_REPO_VERSION_TO_SPECS, ensure_ascii=False,
                           sort_keys=True, separators=(",", ":")) + "\n").encode()
    packaged = (files("repoharness2.envpack") / "data" / pin.json_package_name).read_bytes()
    assert payload == packaged, "重提取结果与包内 JSON 不一致（两个 pin 语义脱节）"
    assert _h.sha256(packaged).hexdigest() == pin.json_sha256


# ---- S1-a（评分接线 2026-09-15）：安装/eval_commands/测试选择器派生与 216 行官方契约 ----

from repoharness2.envpack.spec_vendor import (  # noqa: E402
    NON_TEST_EXTS,
    derive_eval_commands,
    derive_install_cmd,
    derive_test_command,
    derive_test_directives,
)

# A1：oracle 随 rh2 测试树走（docs 下的 B_materials 原件是证据副本，存在时必须逐字节相同）
CONTRACT_216 = Path(__file__).resolve().parent / "data" / "official_cmd_contract_216.json"
CONTRACT_216_DOCS_COPY = DOCS / "project1_execution/B_materials_20260908/official_cmd_contract_216.json"
GRADING_BUNDLES_V2 = DOCS / "s2/ingest/grading_bundles_v2_v0.jsonl"
RESOURCE_FILE_CASES = {
    # 来源 get_test_directives 会剔除资源文件；这三题此前被 rh2 当测试文件传给 pytest（B 线复核 B1）
    "getmoto__moto-4847": "pytest -n0 -rA tests/test_acm/test_acm.py",
    "getmoto__moto-7607": (
        "pytest -n0 -rA tests/test_stepfunctions/parser/__init__.py "
        "tests/test_stepfunctions/parser/test_stepfunctions_dynamodb_integration.py"
    ),
    "iterative__dvc-5336": "pytest -rA tests/unit/remote/test_local.py",
}


@pytest.fixture(scope="module")
def contract_rows():
    rows = json.loads(CONTRACT_216.read_text())
    assert len(rows) == 216
    if CONTRACT_216_DOCS_COPY.exists():
        assert CONTRACT_216_DOCS_COPY.read_bytes() == CONTRACT_216.read_bytes(), "docs 证据副本与测试 oracle 分家"
    return {r["instance_id"]: r for r in rows}


@pytest.fixture(scope="module")
def grading_bundles_v2():
    rows = [json.loads(l) for l in GRADING_BUNDLES_V2.read_text().splitlines() if l.strip()]
    assert len(rows) == 216
    return {r["instance_id"]: r for r in rows}


def test_official_test_line_contract_216(contract_rows, grading_bundles_v2):
    """216/216 派生测试命令必须与官方 fork 生成的 eval 脚本测试行逐字相等（含 mypy `-k` 与资源文件剔除）。"""
    mismatches = []
    for iid, row in grading_bundles_v2.items():
        derived = derive_test_command(row["spec_vendor_id"], row["repo_key_lower"], row["version"], row["test_patch"])
        official = contract_rows[iid]["official_test_line"]
        if derived != official:
            mismatches.append((iid, derived, official))
    assert mismatches == [], f"{len(mismatches)} 条与官方行不一致，例如 {mismatches[:3]}"


def test_resource_file_cases_are_dropped_from_selector_but_kept_in_restore_list(grading_bundles_v2):
    from repoharness2.grading.manager import patch_touched_paths

    for iid, expected in RESOURCE_FILE_CASES.items():
        row = grading_bundles_v2[iid]
        cmd = derive_test_command(row["spec_vendor_id"], row["repo_key_lower"], row["version"], row["test_patch"])
        assert cmd == expected
        touched = patch_touched_paths(row["test_patch"])
        directives = set(derive_test_directives(row["repo_key_lower"], row["test_patch"]))
        dropped = {p for p in touched if any(p.endswith(e) for e in NON_TEST_EXTS)}
        assert dropped, f"{iid}: 应含至少一个资源文件"
        assert directives.isdisjoint(dropped)
        # 恢复/保护清单（test_patch 触碰的全部路径）不因选择器缩减
        assert dropped <= touched and directives <= touched


def test_install_and_eval_commands_presence(contract_rows, grading_bundles_v2):
    """官方 fork `make_eval_script_list` 的规则：spec 有 `install` 就逐字加入 eval 脚本、有 `eval_commands`
    就在激活环境后逐条执行。216 题的 9 个仓库全部带 `install`；只有 conan 12 题带 `eval_commands`。
    注意：contract JSON 里的 `install_step_in_eval` 是 2026-09-09 的 `pip install` 子串启发式（pydantic 20 题的
    安装串是 `pdm add …; make install`，被记成 False），不作 oracle；`eval_commands` 标志仍可对照。"""
    for iid, row in grading_bundles_v2.items():
        c = contract_rows[iid]
        install = derive_install_cmd(row["spec_vendor_id"], row["repo_key_lower"], row["version"])
        assert install is not None and install.strip(), iid
        evc = derive_eval_commands(row["spec_vendor_id"], row["repo_key_lower"], row["version"])
        assert bool(evc) == bool(c["eval_commands"]), iid
        if row["repo_key_lower"] == "conan-io/conan":
            assert evc == ("export PYTHONPATH=${PYTHONPATH:-}:$(pwd)",)
        else:
            assert evc == ()
    pydantic_install = derive_install_cmd(SPEC_VENDOR_ID_SWEGYM_242429C1, "pydantic/pydantic", "2.04")
    assert pydantic_install.startswith('export PATH="$HOME/.local/bin:$PATH"; pdm add pre-commit')


def test_mypy_selector_uses_case_names_not_files():
    patch = (
        "diff --git a/test-data/unit/check-x.test b/test-data/unit/check-x.test\n"
        "--- a/test-data/unit/check-x.test\n+++ b/test-data/unit/check-x.test\n"
        "+[case testAlpha]\n+[case testBeta]\n"
    )
    cmd = derive_test_command(SPEC_VENDOR_ID_SWEGYM_242429C1, "python/mypy", "0.820", patch)
    assert cmd == 'pytest -n0 -rA -k "testAlpha or testBeta"'
    assert "check-x.test" not in cmd


def test_directive_filter_and_django_transform():
    patch = (
        "diff --git a/tests/a/test_a.py b/tests/a/test_a.py\n"
        "diff --git a/tests/a/data.json b/tests/a/data.json\n"
        "diff --git a/tests/a/fixture.csv b/tests/a/fixture.csv\n"
    )
    assert derive_test_directives("getmoto/moto", patch) == ["tests/a/test_a.py"]
    assert derive_test_directives("django/django", patch) == ["a.test_a"]
    assert derive_test_directives("swe-bench/humaneval", patch) == ["test.py"]
