# DataLad088：Qwen3.6 首臂独立关键原件核查

整理日期：2026-10-03。题目为 `r2e_gym_subset::datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb`，作业为 `gpu1003-datalad088-qwen36-a1`。

**结论：本臂诊断回执与决定性评分证据通过独立核查，候选 raw 0 可信。** 完整评分日志有 15 PASSED、2 FAILED、1 XFAIL；17 个 expected key 中匹配 16 个，唯一不匹配为 `test_url_samples`。固定 `~` 兼容失败符合 expected，另一失败是候选引入的真实解析回归。本次未发现新的题级材料阻断；这不是候选通过，也不是完整训练／留出准入。原请求的 claimed／Coder 臂仍未执行。

审查者不是本修订或模型作业的作者，但已接触私有材料，不是 fresh 公开盲读。本次只读本臂关键原件，没有 SSH、运行模型、重评或修改评分材料。执行者已有的全链运输／80 原件审查可复用；本报告独立核的是原 FP、原 diff、实际基线两份决定性源码、隐藏材料与 runner 身份、完整 eval log、真实首请求、实际终点及清理，不声称再次遍历所有归档成员或独立证明 GPU 内存中的权重身份。完整七维轨迹／效率分析由题主负责。

原件入口为 `runs/ordinary_gpu_probe_20261002/remote/queue_v15/results/gpu1003-datalad088-qwen36-a1/`。执行者报告见 `runs/ordinary_gpu_probe_20261002/reviews/q15_datalad088_qwen36_a1_execution_semantic_review_v1.md` 及同名 JSON；独立读回与脚本见 `runs/category2_repair_20260929/r2e_datalad_088_independent_review/gpu_qwen36_review/{key_original_readback.json,key_original_audit.py}`。

## 决定性候选回归

原 `candidate/*.diff` 在 `URL._set_from_str()` 增加 `elif fields['path'] and ':' in fields['path']:`，将所有仍无 scheme／hostname、但 path 含冒号的输入改判为 `ssh:implicit`。冻结内容中保留了这四行新增代码；原始基线没有此分支。它修好了本题公开例 `weired_url:/`，但条件过宽。

实际 hidden `test_url_samples` 先通过题面例与前面的 SSH 字段检查，随后在保留用例 `example.com/path/sp1\:fname` 失败。这里的冒号已转义，输入应保持本地 `file:implicit` 路径；新分支仍将它判成 SSH。源码 `_split_colon()` 用 `(?<!\\):` 只拆未转义冒号，因此此输入未拆成 host/path，hostname 仍空。`URL._set_from_str()` 最后重建字符串时进入 `__str_ssh__()`，在 `assert(url.startswith('ssh:implicit://'))` 失败。原日志的实例 repr、调用栈、输入和断言与这条源码路径一致；不是材料错误、投影丢失或基础设施 raw 0。

这个转义冒号用例是原材料／065 已有的保留项，**不是 088 新增的两项断言之一**。本轮唯一新的失败 key 是 `test_url_samples`，但触发它的具体 case 是旧有保留项。088 的两项增量身份与静态／CPU结论沿用 [既有独立核查](../followup_k7_k8/independent_review_20261003.md)，旧报告未回写。

| 依据或用例 | 本臂实际结果 | 可得结论 |
| --- | --- | --- |
| `test_url_samples` 中转义冒号本地路径 | 实际执行并在字符串重建失败 | 候选造成回归，足以支持 raw 0 |
| 088 query 增量，`test_parse_url_opts` | 整个函数 PASSED；新增断言位于直接执行路径 | 此增量实际通过 |
| 同函数中较后的无转义 slash 前缀 round trip | 此前已有失败，未执行到 | 不能声称动态通过或失败 |
| 088 `/some/dir:x` 绝对路径增量 | 此前已有失败，未执行到 | 本臂没有其动态结果；代码条件静态上仍过宽 |
| `test_get_local_file_url_linux` | `file:///a~ != file:///a%7E`，FAILED | 与 expected 的 FAILED 一致，非新增回归 |
| nose yield `test_get_url_straight_filename` | XFAIL | 不在 17 个 expected key 中 |

## 冻结内容、公开测试与正式评分

独立重算 FrozenPatch canonical digest 为 `sha256:b9845649d2eedd3efd7127b5b4fc4f7912d3efd781fa6004363eeb230e32bc21`，baseline canonical digest 为 `sha256:ee60bf13a0d71b4360c7c566c2f27121013a72f00f2bbd4eadfe4e8d03c81d4a`，与原 FP、projection、status、result 一致。baseline 246 项，本次直接从实际 `baseline.tar` 读取的 `datalad/support/network.py` 与 `datalad/tests/test_network.py` 均匹配 manifest 摘要和已核原公开输入。原 diff 的两份 hunk 从这些实际旧字节逐字重建 FP 两份新字节；FP 条目各自的 payload SHA 也匹配。实际 runtime image 为 `sha256:c5d390400a668256e8946daeefe9758a9064f64d518418727cdb013a907ec346`，head 为 `2753d4722fbf88015c59135f246b2cac82389612`，与该臂 baseline／attempt 绑定。

公开 `datalad/tests/test_network.py` 的修改只是取消题面例注释及调整相邻说明。它在原 diff、原 FP 与 `grading/projection.json` 的 `included_entry_paths` 中都保留，未当作评分前可删除的公开测试。`patch_hygiene.test_files_modified=false` 是现行 official 控制文件口径，**不能解释为 actor 没修改公开测试**。实际可信 setup 恢复的三项是 `r2e_tests` 中的 `__init__.py`、`conftest.py`、`test_1.py`，另重写 `run_tests.sh`；冻结 `r2e_grading_scripts.py` 与 host grading 原件支持此边界。入口实际运行 `pytest -rA r2e_tests`，不评分公开测试。

GPU prepared 的 `r2e-mr-088`、hidden test SHA `7649b82f…`、expected SHA `15da45ba…`、runner SHA `8285765f…` 与本题已验版本一致。实际 eval log 自证 hidden tree `2a62382c…` 和 runner 摘要，setup 成功、四项 official 文件齐全，Start／End 成对、pytest 到 100%、test RC 1。独立从完整 log 解析出 17 个不重复 expected key，与 expected 集合完全一致；仅 `test_url_samples` 不匹配，故二值 raw 0。原 report／status／result 同值，`infra_failure_detail`、`execution_failure_stage` 均空。原 log 为 8572 字节，SHA `sha256:ac30ca1e07b0763d7167fa4eb01026d176cdb1f4ccac72a8e9896b744dd6d911`。

## 首请求、终点和用途边界

直接核原 `services_v13/qwen36/gateway/<job>/requests.jsonl` 的第一个 HTTP 请求：模型路由为 `Qwen3.6-35B-A3B`，真实 `max_tokens=65536`；user 第二块逐字等于原题面加批准公开 brief，第一块只是 currentDate system reminder。原题面 SHA `a0f4c92e…`、brief SHA `68688ecf…`、实际交付 SHA `2ba74c21…` 与 `attempt.public_delivery` 一致，也与两份原 prompt 文件一致。本报告没有把 Claude Code 元数据的 `maxOutputTokens=32000` 当成 HTTP 请求参数。

18 个原 HTTP response 均 status 200、无 stream error；最后一份 SSE 有 `stop_reason=end_turn` 与 `message_stop`。完整 trajectory 289 记录，末条原 result 为 success、`is_error=false`、`terminal_reason=completed`，harness RC 0、日志完整，没有预算截断证据。模型最后文字“All tests pass”不能作为测试事实：本臂正式日志已经证明候选失败。网关原 session_close 显示 revoked／drained、active=0；solver 停止观察 residual=0、删除 RC 0、无剩余标记资源；grader 原 manager_close 为 created／removed 1／1、open／supply／cleanup_failures 为空、regrade 0。评分与正常结束、清理可同时成立。

**用途仍限 `versioned_baseline_diagnostic_only`，`training_or_holdout=false`。** GPU baseline 的 `environment_package_digest` 仍为 `null`，冻结 contract 明确称环境血缘未接通为 formal gate blocker；prepared host grading 另有新环境包 `677b5a1a…`，不能把它冒充 baseline 内已绑定。真实路由与作业原件支持 Qwen3.6 首臂诊断身份，执行者既有权重身份证明边界保留。本臂没有新增材料阻断，但现有 formal gate 未闭合，claimed／Coder 未执行，也没有验证同仓另外四题。不得把此结论扩展为完整请求结束、候选修复完成或训练资格。
