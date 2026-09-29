# 本轮验证记录

日期：2026-09-16。全部本机 CPU；没有 Docker、SSH、GPU、API。生产源码与维护测试只读。

## 维护测试

工作目录 `rh2/`：

```text
.venv/bin/python -m pytest -q tests/contracts/test_grading.py tests/grading/test_w3b_grader_profile_unit.py tests/adapters/test_batch4_pa_transport.py
........................................................................ [ 85%]
............                                                             [100%]
84 passed in 4.00s
exit_code=0

.venv/bin/python -m pytest -q tests/adapters/test_replay_grade.py::test_pa_qualification_ledger_round_trip tests/adapters/test_w1b_prepared_task_face_v2.py -k pa
............                                                             [100%]
12 passed in 3.11s
exit_code=0
```

共 96 passed、0 skipped。`-k pa` 同时匹配第二个文件的节点路径，因此该文件的 11 项都运行；不是只运行一个命名含 pa 的函数。

## 独立反例

仓库根目录：

```text
rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch4_scoring_20260910/implementation_review_20260916/training/probe_training_semantics.py
{
  "unrelated_bad_unused": "candidate_execution_failed",
  "unrelated_clean_control": "test_log_parse_failed",
  "normal_tests_all_reference_missing": "test_log_parse_failed",
  "compile_probe_shadow_rc": 1,
  "r2e_impossible_counts": [7, 0],
  "all_termination_unknown": "candidate_execution_failed"
}
exit_code=0
```

探针使用真实本机 Python 3.12.13、pytest 9.1.1 生成日志，真实执行生产 `render_compile_probe_script`；随后调用真实 `SWEGradingManager.grade`，Docker 操作使用现有维护测试的 `ProfileGraderFakeDocker` 替身。它证明上述评分逻辑和实际日志形状，不等价于真实容器或模型运行。完整结果见 [probe_training_semantics.json](probe_training_semantics.json)；本机用户目录和临时目录替换为占位符，源码 SHA-256 保留。
