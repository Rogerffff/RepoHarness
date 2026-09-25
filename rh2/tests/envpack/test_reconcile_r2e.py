"""R-f 对账脚本的一致性口径（Codex closeout F1 的两个最小反例）。

`agree` 不能只看 reward 与差异键集合：期望 PASSED、RH2 得 FAILED、参考得 ERROR 时两侧 reward 都 0、
`mismatched` 都是同一个键，但执行行为不同，必须判不一致。参考账本自报值与其日志重算矛盾时要单列，不能沉默。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "reconcile_r2e.py"


@pytest.fixture(scope="module")
def reconcile():
    """脚本在导入时把 rh2/src 插到 sys.path 首位；用完恢复，免得后续测试（例 reference/slime 的差分测试）
    误取 vendored slime（Codex 09-24 复核 F2）。"""
    saved = list(sys.path)
    spec = importlib.util.spec_from_file_location("reconcile_r2e_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.path[:] = saved


def _comparison(reconcile, expected, rh2_obs, ref_obs, *, ref_reward: float, source: str = "m3") -> dict:
    return {"source": source, "reference_log": f"{source}.txt", "reference_prime_reward": ref_reward,
            "comparison": reconcile.compare(expected, rh2_obs, ref_obs)}


def test_same_reward_and_same_mismatched_key_but_different_status_is_not_agreement(reconcile):
    expected = {"T.a": "PASSED", "T.b": "PASSED"}
    comp = _comparison(reconcile, expected, {"T.a": "FAILED", "T.b": "PASSED"}, {"T.a": "ERROR", "T.b": "PASSED"}, ref_reward=0.0)
    inner = comp["comparison"]
    assert inner["sets_equal"] is True  # 两侧相对期望的差异键集合相同（都只有 T.a）
    assert inner["rh2"]["mismatched"] == ["T.a"] and inner["reference"]["mismatched"] == ["T.a"]
    assert inner["observed_maps_equal"] is False and inner["observed_diff"] == {"T.a": ("FAILED", "ERROR")}
    facts = reconcile.decide_agreement(0.0, [comp], ledger_rewards=[])
    assert (facts["reward_equal"], facts["diff_sets_equal"], facts["observed_maps_equal"]) == (True, True, False)
    assert facts["agree"] is False and facts["reference_ledger_consistent"] is None


def test_reference_ledger_contradicting_its_own_log_is_flagged_not_silently_agreed(reconcile):
    expected = {"T.a": "PASSED"}
    comp = _comparison(reconcile, expected, {"T.a": "FAILED"}, {"T.a": "FAILED"}, ref_reward=0.0)
    facts = reconcile.decide_agreement(0.0, [comp], ledger_rewards=[1])  # 账本自报 1，日志重算 0
    assert facts["agree"] is True  # 两侧日志逐键相同：日志层面的一致成立
    assert facts["reference_ledger_consistent"] is False  # 但账本矛盾必须单列，不被总体一致淹没
    ok = reconcile.decide_agreement(0.0, [comp], ledger_rewards=[0, 0])
    assert ok["reference_ledger_consistent"] is True and ok["agree"] is True
    assert reconcile.decide_agreement(None, [comp], ledger_rewards=[])["agree"] is False  # RH2 无 reward（infra）不算一致


def test_m3_ledger_is_cross_checked_only_against_m3_logs_and_unknown_without_valid_rewards(reconcile):
    """Codex 09-24 P2：混入 `--old-root` 的不同参考结果时，不能把"来源之间有分歧"报成"M3 账本与自己的日志矛盾"。"""
    expected = {"T.a": "PASSED"}
    m3 = _comparison(reconcile, expected, {"T.a": "FAILED"}, {"T.a": "FAILED"}, ref_reward=0.0, source="m3")
    old = _comparison(reconcile, expected, {"T.a": "FAILED"}, {"T.a": "PASSED"}, ref_reward=1.0, source="old")
    facts = reconcile.decide_agreement(0.0, [m3, old], ledger_rewards=[0])
    assert facts["agree"] is False  # 与旧来源的日志确实不同：总体不一致
    assert facts["reference_ledger_consistent"] is True  # 但 M3 账本与 M3 自己的日志是自洽的
    assert reconcile.decide_agreement(0.0, [m3, old], ledger_rewards=[1])["reference_ledger_consistent"] is False
    assert reconcile.decide_agreement(0.0, [m3, old], ledger_rewards=[None])["reference_ledger_consistent"] is None
    assert reconcile.decide_agreement(0.0, [old], ledger_rewards=[0])["reference_ledger_consistent"] is None  # 没有 M3 日志可互核


def _expected_revision(before: str, after: str, old: str, new: str):
    import hashlib

    from repoharness2.envpack.ingest_r2e_subset import REVISION_KIND_EXPECTED, R2EExpectedChange, R2EMaterialRevision

    def sha(t: str) -> str:
        return "sha256:" + hashlib.sha256(t.encode("utf-8")).hexdigest()

    import json
    change = R2EExpectedChange.diff(json.loads(before), json.loads(after))
    return R2EMaterialRevision(revision_id="r2e-mr-900", instance_id="x__y", kind=REVISION_KIND_EXPECTED,
                               target="expected_output_json", edits=((old, new),), sha256_before=sha(before),
                               sha256_after=sha(after), revised_file=None, expected_change=change, decision_ref="test")


def test_expected_revised_row_cross_checks_the_m3_ledger_against_the_source_expected(reconcile):
    """期望修订后（例：r2e-mr-001 把一个状态从 FAILED 改为 PASSED），M3 账本仍是按来源期望算的 0；
    互核必须用来源期望（取自原始行）重算的 reward，不能把"修订前后期望不同"报成"M3 账本与自己的日志矛盾"。"""
    source = '{"T.a": "PASSED", "T.b": "FAILED"}'
    revised = '{"T.a": "PASSED", "T.b": "PASSED"}'
    rev = _expected_revision(source, revised, '"T.b": "FAILED"', '"T.b": "PASSED"')
    assert reconcile.source_expected_json("x__y", source, (rev,)) == source
    assert reconcile.source_expected_json("x__y", source, ()) == source  # 无期望修订：原样返回
    expected = {"T.a": "PASSED", "T.b": "PASSED"}
    comp = _comparison(reconcile, expected, {"T.a": "PASSED", "T.b": "PASSED"}, {"T.a": "PASSED", "T.b": "PASSED"}, ref_reward=1.0)
    comp["reference_prime_reward_source_expected"] = 0.0  # 同一份参考日志按来源期望算：T.b 不符 → 0
    facts = reconcile.decide_agreement(1.0, [comp], ledger_rewards=[0, 0])
    assert facts["agree"] is True and facts["reward_equal"] is True  # RH2 按修订后期望评分，与修订后重算一致
    assert facts["reference_ledger_consistent"] is True  # M3 账本 0 与来源期望重算 0 自洽
    assert reconcile.decide_agreement(1.0, [comp], ledger_rewards=[1])["reference_ledger_consistent"] is False


def test_source_expected_refuses_a_row_that_does_not_match_the_revision(reconcile):
    source = '{"T.a": "FAILED"}'
    revised = '{"T.a": "PASSED"}'
    rev = _expected_revision(source, revised, '"FAILED"', '"PASSED"')
    with pytest.raises(ValueError, match="sha256_before"):
        reconcile.source_expected_json("x__y", '{"T.a": "ERROR"}', (rev,))  # 原始行不是修订单记录的那份来源期望


def _mv(reconcile, **kw):
    base = {"recorded": None, "observed": None, "source_expected": {}, "current_expected": {}, "has_expected_rev": False,
            "has_hidden_rev": False, "recipe_id": "r2e_derive_v1", "forced": None}
    base.update(kw)
    return reconcile.decide_material_version(**base)


def test_material_version_is_read_from_the_ledger_evidence_not_from_the_current_pool(reconcile):
    """Codex 09-24 F1：历史账本（来源版评分）不能被贴上当前修订。期望修订看哪一版能重现账本判定，
    隐藏测试修订看评分所用镜像的配方身份；判不出、混版或与显式指定不符都标 unmatched。"""
    src = {"T.a": "PASSED", "T.b": "FAILED"}
    cur = {"T.a": "PASSED", "T.b": "PASSED"}
    obs = {"T.a": "PASSED", "T.b": "PASSED"}   # 发布镜像里两键都 PASSED
    as_source = reconcile.verdict_tuple(src, obs)  # 来源版评分时 grader 记下的判定：T.b 不符
    as_current = reconcile.verdict_tuple(cur, obs)
    assert _mv(reconcile, recorded=as_source, observed=obs, source_expected=src, current_expected=cur,
               has_expected_rev=True)["version"] == "source"
    assert _mv(reconcile, recorded=as_current, observed=obs, source_expected=src, current_expected=cur,
               has_expected_rev=True)["version"] == "current"
    # 隐藏测试修订：来源版镜像 → source；带材料步骤的镜像 → current
    assert _mv(reconcile, has_hidden_rev=True, recipe_id="r2e_derive_v1")["version"] == "source"
    assert _mv(reconcile, has_hidden_rev=True, recipe_id="r2e_derive_v1+material_v2")["version"] == "current"
    assert _mv(reconcile, has_hidden_rev=True, recipe_id=None)["version"] == "unmatched"
    # 两类证据矛盾（期望是修订版、镜像是来源版）→ 混版
    mixed = _mv(reconcile, recorded=as_current, observed=obs, source_expected=src, current_expected=cur,
                has_expected_rev=True, has_hidden_rev=True, recipe_id="r2e_derive_v1")
    assert mixed["version"] == "unmatched" and "混版" in mixed["why"]
    # 两版都重现不了（或缺明细）→ unmatched，不猜
    assert _mv(reconcile, recorded=(9, 9, [], [], []), observed=obs, source_expected=src, current_expected=cur,
               has_expected_rev=True)["version"] == "unmatched"
    assert _mv(reconcile, recorded=None, observed=obs, source_expected=src, current_expected=cur,
               has_expected_rev=True)["version"] == "unmatched"
    # 显式指定与证据不符 → unmatched；没有修订的题两版相同
    assert _mv(reconcile, recorded=as_source, observed=obs, source_expected=src, current_expected=cur,
               has_expected_rev=True, forced="current")["version"] == "unmatched"
    assert _mv(reconcile)["version"] == "current"


def test_rows_graded_with_revised_hidden_tests_or_an_env_recipe_are_listed_apart(reconcile):
    """参考 runner 跑的是来源材料与来源环境：隐藏测试修订、环境配方（改了依赖版本，例 orange3 固定 SciPy 1.5.4）
    的行都单列，不计入"与来源一致"的总数；版本未匹配的行不参与。"""
    assert reconcile.row_class(version="current", hidden_tests_revised=False, recipe_id="r2e_derive_v1") == "counted"
    assert reconcile.row_class(version="source", hidden_tests_revised=False, recipe_id="r2e_derive_v1") == "counted"
    assert reconcile.row_class(version="current", hidden_tests_revised=True, recipe_id="r2e_derive_v1+material_v2") == "hidden_revised"
    assert reconcile.row_class(version="current", hidden_tests_revised=False, recipe_id="r2e_derive_v1+env_v1") == "env_recipe"
    assert reconcile.row_class(version="unmatched", hidden_tests_revised=False, recipe_id="r2e_derive_v1") == "unmatched"
