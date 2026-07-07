"""S1-8 两类 parity 的 pytest 入口：复跑 experiments/s1_parity.py 的全部断言。

脚本本体（importlib 按路径加载）内部全程用硬 assert——任何一处 token 逐位
不一致 / 治理事实错位 / 降级标注缺失都会在脚本层直接炸，本文件只负责把
三个入口纳入测试套件并钉住关键结论字段。判据全文见脚本 docstring 与
s1/parity_report.md。
"""

import importlib.util
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "experiments" / "s1_parity.py"
_spec = importlib.util.spec_from_file_location("rh2_s1_parity", _SCRIPT)
parity = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = parity  # dataclass 解析字符串注解需要模块已注册
_spec.loader.exec_module(parity)


def test_parity_core_token_bitwise_and_audit_gate(tmp_path):
    """parity-core：dense 两轮 + MoE 探针形状，token/loss mask/logprob/reward 逐位。"""

    result = parity.run_parity_core(work_dir=tmp_path)
    assert result["parity_core_pass"] is True
    assert result["audit_tier_refused"] is True
    labels = {chain["label"] for chain in result["chains"]}
    assert labels == {"dense_2turn", "moe_probe_15_16"}
    for chain in result["chains"]:
        assert chain["token_bitwise_equal"] is True
        assert chain["loss_mask_bitwise_equal"] is True
        assert chain["logprobs_bitwise_equal"] is True
        assert chain["reward_facts_bitwise_equal"] is True
        assert chain["idempotent_reexport"] is True
        assert chain["eligibility_class"] == "offline_or_sft_candidate"  # S1 封顶
    by_label = {chain["label"]: chain for chain in result["chains"]}
    assert by_label["dense_2turn"]["token_count"] == 35  # 12+10+5+8
    assert by_label["dense_2turn"]["trainable_token_count"] == 18  # 10+8
    assert by_label["moe_probe_15_16"]["token_count"] == 31  # 15+16


def test_parity_cross_governance_facts():
    """parity-cross：真实 deepseek 轨迹 vs slime mock 链，治理事实级一致性。"""

    result = parity.run_parity_cross()
    assert result["parity_cross_pass"] is True
    assert result["shared_dims_agree"] == ["reward_scope", "security_and_leakage", "clean_grading"]
    assert result["expected_divergence"] == {
        "logprob_alignment": ["logprob_missing"],
        "loss_mask_integrity": ["no_trainable_tokens"],
        "policy_staleness": ["staleness_facts_missing"],
    }
    assert result["slime_class"] == "offline_or_sft_candidate"
    assert result["verifiers_class"] == "audit_only_or_rejected"
    assert result["verifiers_export_refused"] is True


def test_all_six_real_dumps_project_and_error_dump_rejected():
    """6 份 S0-3 真实 dump（12 条 Trace）全部可投影、降级标注正确；error dump 拒收。"""

    result = parity.run_toy_dump_projection()
    assert result["toy_dump_projection_pass"] is True
    assert result["projectable_dumps"] == 6
    assert result["projected_traces"] == 12
    assert result["reject_dump"]["reason_codes"] == ["trace_has_no_branches"] * 2
