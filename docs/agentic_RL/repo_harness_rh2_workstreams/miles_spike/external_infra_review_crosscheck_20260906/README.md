# 交叉复核的证据材料

对应 [2026-09-06 交叉复核报告](../external_infra_review_crosscheck_20260906.md)。只用于复现观察，不进入标准测试集或训练资格机制，未改生产代码。全部在仓库 `rh2/` 目录运行。

```bash
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/external_infra_review_crosscheck_20260906/realign_probe.py
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/external_infra_review_crosscheck_20260906/runtime_probe.py
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/external_infra_review_crosscheck_20260906/singleton_signal_probe.py
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/external_infra_review_crosscheck_20260906/grading_classification_probe.py
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/external_infra_review_crosscheck_20260906/extra_actor_zero_probe.py
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/external_infra_review_crosscheck_20260906/run8_raw_probe.py
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/external_infra_review_crosscheck_20260906/run8_decode.py
```

- `realign_probe.py` 使用已缓存 Qwen3-30B-A3B tokenizer revision `ad44e777bcd18fa416d9da3bd8f70d33ebb85d39`，`local_files_only=True`，不下载、不调模型。真实消息翻译/模板/manager，合成消息。`trained_turn_indices` 是内部从 1 开始的 turn 标识；结果里的 t0/t1 是报告中的两轮记号。
- `runtime_probe.py` 使用真实 proxy、adapter cap、aclose、buffer/RH2 关闭链，以及已有依赖导入桩。仅用 shell 函数替身观察权限脚本的控制流，不执行真实 chown/Docker。时间缩到毫秒用于证明边界，不能当默认配置性能测量。日志中的超时 ERROR 是刻意反例。
- `singleton_signal_probe.py` 使用前轮证据目录的 `probe_bootstrap.py` 与真实 CPU loss；证明 accepted 不等于非零 logits 梯度。
- `grading_classification_probe.py` 使用已安装 swebench 4.1.0 真 parser 与 RH2 分类器，合成日志/TimeoutError。证明空解析有归因歧义，不证明真实任务失败频率。
- `extra_actor_zero_probe.py` 使用真实 CPU advantage/custom loss，及 AST 提取的生产 `train_actor` 配合引擎/模型替身。证明 flag 控制流与限定配方的数值关系，不证明真实 GPU forward/replay；另有非零梯度样本验证开关前后数值一致；简化模型的梯度抵消是数学反例，不是30B模型事故。
- `run8_raw_probe.py` 仅读取已归档 token 二进制，核对其 capture SHA256 和前缀；本地只有一个完整 projection，不声称重新核过全部60条。

- `run8_decode.py` 用当前缓存 30B tokenizer 辅助解码历史 4B token 的响应尾部；不把 tokenizer 相同当作已证事实，原始前缀比对由上一脚本完成。

截断接口相关回归命令：

```bash
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" uv run pytest tests/governance/test_w1b_admission_disposition.py tests/adapters_miles/test_w1b_group_admission.py::test_truncated_member_fail_fast_without_injection_and_neutral_with -q
```

本轮结果 45 passed，0 skipped，0 xfailed，2.03 秒。探针的已保存输出以同目录 result 文件为准；成功退出表示复现了当前行为，不表示实现已修复。前轮 801 项回归没有在本轮重跑，也不与45项相加作新覆盖数。
