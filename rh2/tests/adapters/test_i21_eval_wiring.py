"""I21（第五组）：评测接线预检（纯函数）与任务面选择。

共享引擎形态下 miles 直接 await eval，评测里的接线错误会停掉训练驱动——配置层能发现的必须在启动时拒绝。
用户 2026-09-19 决定：评测题包独立配置，但代码里**不**设 train/eval 题目互斥。
"""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest

from repoharness2.adapters.slime.eval_wiring import EVAL_REPORT_HOOK_PATH, EvalWiringError, validate_eval_wiring


def _args(**over):
    base = dict(
        eval_interval=5, eval_uses_snapshots=False, eval_datasets=[NS(name="swe_dev", path="/data/eval/prompts.jsonl", custom_generate_function_path=None)],
        custom_eval_rollout_log_function_path=EVAL_REPORT_HOOK_PATH, reward_key=None, eval_reward_key=None, ci_metric_checker_key=None,
    )
    base.update(over)
    return NS(**base)


# 独立评测作业的启动形态（与 tests/adapters_miles/test_i21_eval_only_driver.py 的 EVAL_ONLY_SHAPE 同一组条件）
EVAL_ONLY = dict(num_rollout=0, debug_rollout_only=True, fully_async=True, rollout_global_dataset=False, prompt_data=None,
                 skip_eval_before_train=False, start_rollout_id=None, sglang_load_format="auto")


def _validate(args, **over):
    kw = dict(execution_mode="fa_formal", eval_only=False, eval_prepared_dir="/prep/eval",
              eval_host_grading_path="/private/eval/host.json", eval_host_grading_sha256="sha256:" + "a" * 64)
    kw.update(over)
    return validate_eval_wiring(args, **kw)


def test_enabled_wiring_returns_the_single_dataset():
    wiring = _validate(_args())
    assert wiring.enabled and not wiring.eval_only
    assert (wiring.dataset_name, wiring.dataset_path) == ("swe_dev", "/data/eval/prompts.jsonl")
    only = _validate(_args(**EVAL_ONLY), eval_only=True, environ={})  # 独立评测作业的完整启动形态
    assert only.enabled and only.eval_only


def test_disabled_when_eval_is_not_requested_or_in_the_frozen_s1_path():
    assert _validate(_args(eval_interval=None)).enabled is False  # 没开 eval：评测题包配了也不加载
    assert _validate(_args(), execution_mode="s1_compat", eval_prepared_dir=None).enabled is False  # 冻结路径不经本批接线
    assert _validate(_args(eval_interval=None), eval_prepared_dir=None, eval_host_grading_path=None, eval_host_grading_sha256=None).enabled is False


@pytest.mark.parametrize(
    ("args_over", "kw_over", "code"),
    [
        ({}, {"eval_prepared_dir": None}, "eval_prepared_tasks_missing"),
        ({}, {"eval_host_grading_sha256": None}, "eval_prepared_tasks_missing"),
        ({"eval_uses_snapshots": True}, {}, "eval_snapshot_mode_unsupported"),
        ({"eval_datasets": []}, {}, "eval_dataset_count_unsupported"),
        ({"eval_datasets": [NS(name="a", path="/a", custom_generate_function_path=None), NS(name="b", path="/b", custom_generate_function_path=None)]}, {}, "eval_dataset_count_unsupported"),
        ({"eval_datasets": [NS(name="a", path="", custom_generate_function_path=None)]}, {}, "eval_dataset_path_missing"),
        ({"eval_datasets": [NS(name="a", path="/a", custom_generate_function_path="other.fn")]}, {}, "eval_dataset_generate_fn_override"),
        ({"custom_eval_rollout_log_function_path": None}, {}, "eval_report_hook_not_wired"),
        ({"eval_reward_key": "score"}, {}, "eval_reward_key_unsupported"),
        ({"reward_key": "score"}, {}, "eval_reward_key_unsupported"),
        ({"ci_metric_checker_key": "eval/swe"}, {}, "eval_metric_checker_unsupported"),
        ({"eval_interval": None}, {"eval_only": True}, "eval_only_without_eval_interval"),
        ({**EVAL_ONLY, "num_rollout": 2}, {"eval_only": True}, "eval_only_requires_zero_training_iterations"),
        ({**EVAL_ONLY, "debug_rollout_only": False}, {"eval_only": True}, "eval_only_requires_rollout_only_driver"),
        ({**EVAL_ONLY, "start_rollout_id": 4}, {"eval_only": True}, "eval_only_requires_fresh_start"),
        ({**EVAL_ONLY, "fully_async": False}, {"eval_only": True}, "eval_only_requires_fully_async_driver"),
        ({**EVAL_ONLY, "skip_eval_before_train": True}, {"eval_only": True}, "eval_only_initial_eval_skipped"),
        ({**EVAL_ONLY, "rollout_global_dataset": True}, {"eval_only": True}, "eval_only_global_dataset_without_prompt_data"),
        ({**EVAL_ONLY, "sglang_load_format": "dummy"}, {"eval_only": True}, "eval_only_dummy_weight_load"),
        ({**EVAL_ONLY}, {"eval_only": True, "environ": {"MILES_SGLANG_DUMMY_LOAD": "1"}}, "eval_only_dummy_weight_load"),
        ({}, {"execution_mode": "s1_compat"}, "eval_requires_identity_mode"),
        ({"eval_interval": None}, {"execution_mode": "s1_compat", "eval_only": True, "eval_prepared_dir": None}, "eval_requires_identity_mode"),
    ],
)
def test_crash_prone_or_unsupported_configurations_are_rejected_at_startup(args_over, kw_over, code):
    with pytest.raises(EvalWiringError) as err:
        _validate(_args(**args_over), **kw_over)
    assert err.value.reason_code == code


def test_task_face_mode_allows_missing_train_package_only_for_eval_only_jobs():
    from repoharness2.adapters.slime.bringup import select_task_face_mode

    assert select_task_face_mode("fa_formal", "/prep/train") == "prepared"
    assert select_task_face_mode("fa_formal", None, eval_only=True, eval_prepared_dir="/prep/eval") == "prepared"
    with pytest.raises(RuntimeError, match="fa_formal 缺 RH2_PREPARED_TASKS_DIR"):
        select_task_face_mode("fa_formal", None)  # 旧规则不变：formal 不回退 v1
    with pytest.raises(RuntimeError, match="fa_formal 缺 RH2_PREPARED_TASKS_DIR"):
        select_task_face_mode("fa_formal", None, eval_only=False, eval_prepared_dir="/prep/eval")  # 训练作业不能只有评测题包
    with pytest.raises(RuntimeError, match="fa_formal 缺 RH2_PREPARED_TASKS_DIR"):
        select_task_face_mode("fa_formal", None, eval_only=True, eval_prepared_dir=None)
    assert select_task_face_mode("s1_compat", None) == "legacy_v1"
    assert select_task_face_mode("fa_audit_only", None) == "legacy_v1"
    with pytest.raises(RuntimeError, match="评测 attempt 按"):
        # fa_audit_only 的 legacy v1 八题任务面没有 attempt 绑定表——配了评测题包却落到这里是配置矛盾
        select_task_face_mode("fa_audit_only", None, eval_only=False, eval_prepared_dir="/prep/eval")


def test_eval_only_checks_do_not_apply_to_training_jobs_and_a_training_file_keeps_the_global_dataset_usable():
    # 训练中评测不受独立评测形态的约束（dummy 加载的引擎会被 bootstrap 发布覆盖；非 fully-async 是训练自己的选择）
    assert _validate(_args(fully_async=False, sglang_load_format="dummy"), environ={"MILES_SGLANG_DUMMY_LOAD": "1"}).enabled
    # 独立评测作业若确实给了训练文件，默认全局数据源可以构造（只是用不上），不拒绝
    ok = _validate(_args(**{**EVAL_ONLY, "rollout_global_dataset": True, "prompt_data": "/data/train/prompts.jsonl"}), eval_only=True, environ={})
    assert ok.eval_only
