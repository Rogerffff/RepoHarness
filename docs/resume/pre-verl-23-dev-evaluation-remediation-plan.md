# Pre-verl 二十三题开发测评问题修复实施计划

更新时间：2026-05-09  
状态：待实施的 Harness hardening 计划  
依据问题日志：`docs/resume/pre-verl-23-dev-evaluation-issue-log.md`  
依据开发测评目录：`runs/pre-verl-agentloop-23-dev-deepseek-pro-development-20260508T185350Z`

## 1. 结论

本计划用于修复 `deepseek-v4-pro` 二十三题开发测评暴露出的 Harness 侧问题。当前开发测评可以证明基础链路已经能完成正式 run、生成 final verifier boundary、执行上下文可见性审计，并产出 accepted 样本；但它还不能直接作为最终简历展示用正式基线，因为 verifier parser、verifier 输出审计、环境材料化和工具性能仍存在会污染评测归因的问题。

本计划本轮处理 4 组修复：

1. 修复 pytest selector 归因和 error 计数一致性，对应 `DEV23-P2-001` 和 `DEV23-P2-004`。
2. 修复 final verifier 非零退出时的 stdout / stderr 审计、pytest exit reason 和不可解析输出标记，对应 `DEV23-P2-003`。
3. 修复 PyVista final verifier 环境缺少 `libGL.so.1` 以及环境错误被错误归因为模型错误的问题，对应 `DEV23-P2-006`。
4. 修复 `symbol_search(root=".")` 在较大仓库中过慢的问题，对应 `DEV23-P2-005`。

`DEV23-P2-002` 暂不在本轮处理。长期只读探索和空补丁超时可能与上下文膨胀、旧工具结果污染和缺少分层压缩有关。当前正在开发完整的 `auto compact`、`tool compact` 和多层上下文压缩机制，因此本项先保留为观察项。等上下文压缩机制完成并通过 smoke / 二十三题复测后，再判断是否需要更强的 convergence nudge 或 experimental hard gate。

`DEV23-RUN-001` 是错误模型试跑记录项，不需要代码修复。本轮只在验证阶段继续保留模型配置核对，确保废弃的 `deepseek-v4-flash` run 不进入 `deepseek-v4-pro` 分母。

## 2. 范围和非目标

范围内：

- pytest 输出解析、selector 归因、参数化测试归因、error / failed 计数一致性。
- final verifier 命令输出 artifact、stdout / stderr 绑定、pytest exit code 结构化解释。
- final verifier 环境缺失依赖时的 failure owner、failure category、reward invalid reason 和 run metadata 归因。
- PyVista / VTK 依赖 `libGL.so.1` 的 Docker 环境材料化和 live preflight。
- `symbol_search` 的宽 root 保护、Python AST 解析缓存、慢扫描诊断和恢复调用。
- 回归测试、局部 replay / rerun、targeted smoke 和审计扫描。

范围外：

- 本轮不增强 `convergence nudge` 的第三阶段强收敛策略。
- 本轮不改变 hidden tests、gold patch、hidden selector 或 evaluator-only material 的可见性边界。
- 本轮不修改 Claude Code 参考项目，只借鉴设计思路。
- 本轮不把 Docker execution mode 描述为生产级安全沙箱。
- 本轮不重跑完整二十三题正式基线，除非前置 targeted 验证全部通过后另行安排。

## 3. 推荐实施顺序

| 顺序 | 修复项 | 对应问题 | 为什么排在这里 |
|---:|---|---|---|
| 0 | 冻结复现证据和增加扫描脚本 | 全部问题 | 先把当前问题变成可重复扫描的事实，避免修复后只能凭人工印象判断。 |
| 1 | 修复 pytest parser 和 selector attribution | `DEV23-P2-001`、`DEV23-P2-004` | 直接影响 fail-to-pass、pass-to-pass、reward 分数和训练样本质量，应最先修。 |
| 2 | 修复 final verifier 输出审计和 exit reason | `DEV23-P2-003` | parser 修好后，需要让所有非零退出都有可审计原始输出和结构化解释。 |
| 3 | 修复 PyVista 环境材料化和环境错误归因 | `DEV23-P2-006` | 第 18 题当前不是可靠模型错误，需要先恢复可执行环境，再修正归因口径。 |
| 4 | 修复 `symbol_search` 宽 root 性能保护 | `DEV23-P2-005` | 不影响当前 accepted 判定，但会消耗任务 wall-clock 预算，修完能减少后续评测干扰。 |
| 5 | 汇总验证和 targeted smoke | 全部已修问题 | 用局部复现任务和干净 targeted smoke 证明修复没有引入新的 P1 / P2。 |

## 4. 阶段 0：冻结复现证据和增加扫描脚本

### 4.1 目标

先把本轮二十三题中已经暴露的问题转换成自动化扫描项。修复前扫描应能稳定命中当前问题；修复后扫描应不再命中，或者命中项被明确归因为环境 / 模型 / 已知延期项。

### 4.2 建议修改位置

- 可新增脚本：`scripts/pre_verl/inspect_23_dev_issue_patterns.py`
- 或复用现有 inspect CLI：`src/repo_harness/cli/` 下增加子命令。
- 单元测试建议放在：`tests/unit/test_pre_verl_issue_scanners.py`

如果本轮只想控制改动范围，可以先做成 `scripts/pre_verl/` 下的开发复盘脚本，不立刻纳入正式 CLI。

### 4.3 扫描项

扫描项至少包括：

1. `exit_code != 0` 且 `summary_counts.failed > 0`，但 `failed_count=0`。
2. `exit_code != 0` 且 `failed_nodeids` 非空，但 `failed_count=0`。
3. `summary_counts.errors > 0`，但 `error_count=0`。
4. `error_nodeids` 非空，但 `error_count=0`。
5. `error_nodeids` 或 `failed_nodeids` 中含有错误前缀，例如 `FAILED `、`ERROR `。
6. pytest `exit_code=4` 且缺少 stdout / stderr 引用或缺少 `pytest_exit_reason`。
7. pytest `exit_code=4` 且 stderr / command output 中包含 `ImportError`、`ModuleNotFoundError`、`cannot open shared object file`、`No module named`。
8. `tool_completed` 中 `effective_tool_name="symbol_search"` 且 `duration_ms > 5000`。
9. `symbol_search` typed result 中 `root="."`、`candidate_file_count` 超过阈值但没有 `slow_scan`、`recovery_call` 或 `recommended_narrow_roots`。

### 4.4 验证方式

修复前执行：

```bash
PATH=.venv/bin:$PATH python scripts/pre_verl/inspect_23_dev_issue_patterns.py \
  runs/pre-verl-agentloop-23-dev-deepseek-pro-development-20260508T185350Z
```

预期应命中：

- 第 4 题和第 16 题的参数化 selector 归因问题。
- 第 21 题的 error 计数不一致问题。
- 第 18 题的 pytest `exit_code=4` 和 PyVista `libGL.so.1` 环境问题。
- 第 18 题和第 22 题的慢 `symbol_search`。

修复后执行同一命令，预期：

- parser 一致性问题不再出现。
- 第 18 题如仍因环境失败，应被归为环境 / verifier 输入问题，而不是模型错误。
- `symbol_search` 慢扫描应要么消失，要么带有 `slow_scan=true`、`semantic_complete=false` 和恢复调用。

## 5. 阶段 1：修复 pytest parser 和 selector attribution

### 5.1 对应问题

- `DEV23-P2-001`：pytest 参数化用例没有归回未参数化 selector。
- `DEV23-P2-004`：pytest `error_count` 和 `error_nodeids` 解析不一致。

### 5.2 当前风险

当前 `src/repo_harness/verifier/pytest_parser.py` 能解析 summary 和部分 node id，但 selector 归因仍不完整。典型错误是：

```text
selector: path/to/test_file.py::test_func
actual failed nodeid: path/to/test_file.py::test_func[param_value]
```

这类参数化失败应该归回原始 selector，但当前 `_selector_matches_any()` 只处理 exact match 和 `selector::child`，没有处理 `selector[...]`。

第 21 题还暴露了另一类问题：`summary_counts.errors > 0`，`error_nodeids` 非空，但 `error_count=0`。这说明 parser 能看到 error 事实，但 selector result 聚合没有把它们同步成一致的计数和状态。

### 5.3 目标行为

修复后必须满足：

- 未参数化 selector 能匹配参数化 pytest node id。
- class / method selector 能匹配其下的参数化 method node id。
- `FAILED path::node` 和 `ERROR path::node` 这类 summary 行要规范化成纯 node id，不能把 `FAILED ` 或 `ERROR ` 前缀保留下来。
- `summary_counts.failed`、`summary_counts.errors`、`failed_nodeids`、`error_nodeids`、`failed_count`、`error_count` 不能互相矛盾。
- 不能只用整条 pytest 命令的非零 exit code 把所有 selector 都标为失败。
- 当 pytest 输出不足以判断某个 selector 状态时，应标为 `unknown`，并写入 parse warning，而不是静默算作 passed 或 failed。

### 5.4 建议修改位置

- `src/repo_harness/verifier/pytest_parser.py`
  - 修改 `_selector_matches_any()`。
  - 增加 `_selector_matches_nodeid()`，集中处理 exact、parameterized、descendant、descendant parameterized。
  - 增加 node id prefix 规范化函数，去掉 `FAILED `、`ERROR `、`PASSED ` 等前缀。
  - 增加 parser warnings，例如 `parameterized_selector_match_used`、`summary_error_count_without_error_nodeids`、`nodeid_status_prefix_normalized`、`selector_status_inferred_from_summary`。
- `src/repo_harness/pre_verl_agentloop.py`
  - 修改 `_selector_result_payload()`，在 `test_cases` 里保留 `match_strategy`、`matched_nodeid`、`status_source`。
  - 如果 schema 暂不想扩展 `test_cases`，至少在 selector result 顶层加入 `selector_match_summary`、`unmatched_failed_nodeids`、`unmatched_error_nodeids`。
- `src/repo_harness/reward/calculator.py`
  - 确认 reward 使用修复后的 selector result，并在 selector result inconsistent 时不要给满分。
- `src/repo_harness/evaluation/metrics.py`
  - 如果 metrics 统计 failed / error count，需要同步使用新字段。

### 5.5 实施步骤

1. 为 `_normalize_nodeid()` 增加状态前缀清理：
   - 输入 `FAILED pydicom/tests/test_config.py::TestDebug::test_debug_off_handler_stream` 应输出 `pydicom/tests/test_config.py::TestDebug::test_debug_off_handler_stream`。
   - 输入 `ERROR tests/test_x.py::test_y` 应输出 `tests/test_x.py::test_y`。
2. 修改 `_selector_matches_any()`：
   - `nodeid == selector`：`exact`。
   - `nodeid.startswith(selector + "[")`：`parameterized_prefix`。
   - `nodeid.startswith(selector + "::")`：`descendant_prefix`。
   - 对 class selector，`path::Class` 应匹配 `path::Class::test_method[...]`。
3. 在 `selector_statuses()` 中返回每个 selector 的匹配策略：
   - `test_id`
   - `status`
   - `match_strategy`
   - `matched_nodeid`
   - `status_source`
4. 调整 unknown / passed 推断规则：
   - 只有当 `suite_completed=true` 且 parsed failure / error facts 与 summary 能对齐时，才允许从“未出现在失败集合”推断为 passed。
   - 如果 summary 显示失败数量大于已解析 node id 数量，则不能把未匹配 selector 全部推断为 passed，应保持 unknown，并写入 warning。
5. 增加一致性检查：
   - 如果 `summary_counts.failed > 0` 但 `failed_count=0` 且 `failed_nodeids` 非空，写入 `verifier_result_inconsistent`。
   - 如果 `summary_counts.errors > 0` 但 `error_count=0` 且 `error_nodeids` 非空，写入 `verifier_result_inconsistent`。
   - 该字段应进入 selector result、final verifier result、reward diagnostics 或 run metadata diagnostics。
6. 修复 reward：
   - 对 `exit_code != 0` 且 selector result inconsistent 的 suite，不允许 `fail_to_pass_score=1.0` 或 `pass_to_pass_score=1.0`。
   - 如果 result invalid，应保留原始 diagnostic score，但 `final_reward` 仍按 invalid 样本策略处理。

### 5.6 单元测试

更新或新增 `tests/unit/test_pytest_parser.py`：

- 未参数化 selector 匹配参数化失败：

```text
selector = "test/dialects/ansi_test.py::test__dialect__ansi_multiple_semicolons"
failed nodeid = "test/dialects/ansi_test.py::test__dialect__ansi_multiple_semicolons[select 1;]"
expected status = failed
expected match_strategy = parameterized_prefix
```

- class / method 参数化匹配：

```text
selector = "tests/unittest_brain_builtin.py::TestStringNodes::test_string_format_uninferable"
failed nodeid = "tests/unittest_brain_builtin.py::TestStringNodes::test_string_format_uninferable[case0]"
expected status = failed
```

- error summary 一致性：

```text
summary_counts = {"errors": 5, "failed": 5}
error_nodeids 非空
expected error_count > 0
```

- 前缀清理：

```text
raw = "FAILED pydicom/tests/test_config.py::TestDebug::test_debug_off_handler_stream"
expected normalized = "pydicom/tests/test_config.py::TestDebug::test_debug_off_handler_stream"
```

更新 `tests/unit/test_pre_verl_agentloop.py`：

- 构造 selector result payload，断言 `failed_count`、`error_count`、`unknown_count` 和 `parse_warnings` 与 parser 输出一致。

更新 `tests/unit/test_reward.py`：

- 构造 `exit_code=1`、summary 有 failure、selector result inconsistent 的情况，断言 reward 不会给满分。

### 5.7 局部验证

修复后建议先跑：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_pytest_parser.py \
  tests/unit/test_pre_verl_agentloop.py \
  tests/unit/test_reward.py
```

然后对第 4 题、第 16 题、第 21 题做局部 replay 或定向 rerun：

- `pre_verl_dev_004_sqlfluff__sqlfluff_1517`
- `pre_verl_dev_016_pylint_dev__astroid_1866`
- `pre_verl_dev_021_pydicom__pydicom_901`

验收标准：

- 第 4 题和第 16 题不再出现 `summary_counts.failed > 0` 但 `failed_count=0`。
- 第 21 题不再出现 `summary_counts.errors > 0` 或 `error_nodeids` 非空但 `error_count=0`。
- 相关 reward 不再把失败 suite 计为满分。

## 6. 阶段 2：修复 final verifier 输出审计和 pytest exit reason

### 6.1 对应问题

- `DEV23-P2-003`：final verifier pytest `exit_code=4` 缺少 stdout / stderr 审计材料。

### 6.2 当前风险

第 18 题里 selector result 有 `output_artifact_ref`，但对应 container execution facts 中 `stdout_ref=null` 且 `stderr_ref=null`。这会导致审计时需要人工跳到 command output artifact 中查找真实错误，而不是在 final verifier result、container facts 和 run metadata 中直接看到 stdout / stderr 引用和 exit reason。

### 6.3 目标行为

修复后必须满足：

- final verifier 的每一次 fail-to-pass 和 pass-to-pass 命令，无论 exit code 取值如何，都保存可追踪输出。这里包括 pytest exit code `5` / no tests collected，也包括 timeout。
- selector result 至少包含：
  - `output_artifact_ref`
  - `stdout_preview`
  - `stderr_preview`
  - `container_execution_facts_ref`
  - `pytest_exit_reason`
  - `verifier_output_unparsed`
- container execution facts 应能绑定 stdout / stderr，或者明确绑定 combined command output artifact。
- pytest `exit_code=4` 必须被结构化标注为 `pytest_usage_or_collection_error`、`pytest_config_or_import_error` 或更具体的 reason。
- 如果 `exit_code != 0` 且 `summary_counts={}`，不能让结果看起来像“没有失败用例”，应设置 `verifier_output_unparsed=true` 或 `pytest_output_parse_warnings`。

### 6.4 建议修改位置

- `src/repo_harness/workspace/docker_adapter.py`
  - 在 `_execute_in_container()` 或 `run_command()` 附近补充 stdout / stderr artifact 绑定。
  - 如果暂时不拆分 stdout / stderr 文件，也要在 container facts 中写入 combined `output_artifact_ref`。
- `src/repo_harness/workspace/adapter.py`
  - 本地 workspace adapter 也应保持同样字段，避免 Docker / local 行为不一致。
- `src/repo_harness/workspace/schemas.py`
  - 如当前 `ExecutionResult` 缺少 stdout / stderr artifact refs，需要扩展 schema。
- `src/repo_harness/pre_verl_agentloop.py`
  - `_selector_result_payload()` 中加入 output refs、preview、exit reason、unparsed 标记。
  - `_append_boundary_step_event()` 中加入 output artifact refs 和 exit reason。
- `src/repo_harness/verifier/pytest_parser.py`
  - 增加 `pytest_exit_reason()` 或在 parse result 中增加 exit reason 字段。

### 6.5 实施步骤

1. 扩展执行结果 schema：
   - 如果现有 `ExecutionResult` 已经支持 `stdout_ref` / `stderr_ref`，则补齐 Docker adapter 写入逻辑。
   - 如果不支持，新增字段并保持向后兼容。
2. Docker command 执行后保存三类输出引用：
   - combined command output artifact，保留当前格式。
   - stdout artifact。
   - stderr artifact。
3. container facts 中写入：
   - `stdout_ref`
   - `stderr_ref`
   - `output_artifact_ref`
   - `stdout_preview`
   - `stderr_preview`
   - `captured_output_empty`
4. selector result 中写入同样的输出引用或引用摘要。
5. 增加 pytest exit reason 分类：
   - exit code `0`：`pytest_passed`
   - exit code `1` 且有 failed / errors：`pytest_test_failures`
   - exit code `2`：`pytest_interrupted`
   - exit code `3`：`pytest_internal_error`
   - exit code `4`：`pytest_usage_or_collection_error`
   - exit code `5` 或包含 no tests：`pytest_no_tests_collected`
   - timeout：`pytest_timeout`
6. 对 `exit_code=4` 增加 stderr 关键词 refinement：
   - `ImportError`、`ModuleNotFoundError`、`cannot open shared object file`：`pytest_config_or_import_error`
   - pytest 参数错误或 selector invalid：`pytest_usage_error`
   - collection 阶段错误：`pytest_collection_error`
7. 当 `exit_code != 0` 且 parser 没有 summary / node ids：
   - `verifier_output_unparsed=true`
   - `parse_warnings` 增加 `nonzero_exit_without_parsed_test_facts`
   - reward 和 run metadata 可以读取该字段作为 invalid 或 environment diagnostic。

### 6.6 单元测试和集成测试

新增或更新：

- `tests/unit/test_pre_verl_agentloop.py`
- `tests/unit/test_pytest_parser.py`
- `tests/integration/test_workspace_lifecycle.py`
- 如已有 Docker adapter 专项测试，可以增加 `tests/unit/test_docker_adapter_image_platform.py` 或新增 `tests/unit/test_docker_adapter_output_artifacts.py`

重点测试：

- 模拟 `exit_code=4` 且 stderr 非空，断言 selector result 包含 stderr preview 和 output refs。
- 模拟 `exit_code=4` 且 stdout / stderr 都为空，断言 `captured_output_empty=true`，而不是缺字段。
- 模拟 Docker command 输出，断言 container facts 里有 stdout / stderr 或 combined output artifact 引用。
- 断言 `pytest_exit_reason` 出现在 final verifier result 和 boundary step event 中。

### 6.7 验收标准

对第 18 题局部 rerun 或 replay 后：

- `pre_verl_fail_to_pass_result.json` 和 `pre_verl_pass_to_pass_result.json` 中有 `pytest_exit_reason`。
- selector result 层有 `stdout_preview`、`stderr_preview` 或明确的 output refs。
- container execution facts 不再只有 `exit_code=4` 和空输出引用。
- 如果仍然是 environment import error，必须进入阶段 3 的环境归因路径。

## 7. 阶段 3：修复 PyVista 环境材料化和环境错误归因

### 7.1 对应问题

- `DEV23-P2-006`：PyVista final verifier 环境缺少 `libGL.so.1`，导致第 18 题不可可靠归因为模型错误。

### 7.2 当前风险

第 18 题 pytest 在配置解析阶段导入 `pyvista`，随后导入 VTK 相关模块，最终因为缺少系统库 `libGL.so.1` 退出。此时测试并没有真正进入任务断言阶段，不能可靠记为 `model_wrong_fix`。

### 7.3 目标行为

修复后必须满足：

- PyVista 任务的 Docker 环境能成功导入 `pyvista`。
- 缺少系统依赖时，run 在 setup / preflight 或 final verifier 阶段被归为 environment / verifier input 问题，而不是模型错误。
- `final_verifier_boundary.json`、`run_metadata.json`、`reward.json` 的 failure owner 和 invalid reason 口径一致。
- 训练导出不把这类环境失败样本当作模型错误样本。

### 7.4 建议修改位置

- `src/repo_harness/workspace/docker_adapter.py`
  - 如默认 Dockerfile 需要增加系统库，可以在 image template 或 task-specific materialization 层实现。
- `src/repo_harness/workspace/materialization.py`
  - 如果已有任务级环境材料化入口，可在这里加入 task-specific system package 处理。
- `src/repo_harness/pre_verl_agentloop.py`
  - final verifier 对 pytest import / environment error 做归因转换。
- `src/repo_harness/run_metadata/writer.py`
  - 将 environment failure 写入 failure diagnostics。
- `src/repo_harness/reward/calculator.py`
  - environment failure 的 `invalid_reason` 应与 boundary 一致。
- `scripts/pre_verl/run_agentloop_evaluation.py`
  - 如 run config / freeze manifest 需要记录环境 preflight policy，在这里冻结。

### 7.5 实施步骤

1. 确认第 18 题真实任务环境：
   - 当前 task definition 显示 `environment.execution_image="python:3.9"`。
   - 不要只在裸 `python:3.9` 容器中打印 Python 版本，因为这不能验证 PyVista / VTK 的系统库依赖。
   - 应在第 18 题材料化后的真实任务环境中执行 live preflight，修复前应能复现 `libGL.so.1` 缺失，修复后应退出码为 0。

```bash
python -c "import pyvista; print(pyvista.PyVistaDeprecationWarning)"
```

2. 在 PyVista 任务环境中安装系统依赖：
   - Debian / Ubuntu 系镜像通常需要 `libgl1`。
   - 如果 VTK / Qt / Matplotlib 继续暴露缺失库，再按 preflight 输出补充最小依赖，例如 `libglib2.0-0`、`libxrender1`、`libxext6`、`libsm6`。不要一次加入过宽的桌面环境依赖。
3. 增加 live preflight：
   - setup 后执行 `python -c "import pyvista"`。
   - 如果 task 的 pytest 配置会导入特定 warning class，也可以执行 `python -c "import pyvista; print(pyvista.PyVistaDeprecationWarning)"`。
4. 将 preflight 结果写入 artifact：
   - `environment_preflight_status`
   - `environment_preflight_command`
   - `environment_preflight_exit_code`
   - `environment_preflight_output_ref`
5. 增加 environment error 分类函数：
   - 输入 pytest stdout / stderr / command output。
   - 只有满足下面任一条件时，才输出 `final_verifier_environment_error`：
     - clean preflight 在模型补丁应用前已经失败。
     - stderr 明确命中外部系统共享库缺失，例如 `cannot open shared object file`、`libGL.so.1`。
     - stderr 明确命中解释器环境中的第三方依赖缺失，并且该依赖不是模型补丁新增的仓库内 import。
     - 同一错误可以在没有模型补丁的 clean verification workspace 中复现。
   - 不要把所有 `ImportError`、`ModuleNotFoundError` 或 `No module named` 都直接归为环境问题。模型删除仓库内模块、改错 import 路径、引入不存在的仓库内模块时，也会出现这些错误，这类情况应保留为 `model_wrong_fix` 或 `ambiguous_verifier_failure`。
6. 修改 final verifier boundary 归因：
   - `failure_owner="harness_or_environment"` 或现有 schema 中等价 owner。
   - `failure_category="final_verifier_environment_error"` 或现有 schema 中最接近的 environment failure category。
   - 保留 `pytest_exit_reason` 和 stderr artifact 引用。
7. 修改 reward：
   - `invalid_for_training=true`
   - `final_reward=0.0`
   - `invalid_reason="final_verifier_environment_error"` 或更具体的 `pytest_command_error_environment_dependency_missing`
8. 修改 run metadata：
   - `failure_category=environment_failure`
   - `failure_type=environment_setup_failed`、`final_verifier_environment_error` 或新增枚举。
   - details 中绑定 output refs 和命中的 stderr pattern。
9. 更新 run matrix / summary：
   - 将 environment / verifier failure 从 `model_wrong_fix` 分母中剥离。
   - 汇总中单独统计 `environment_or_verifier_failure_count`。

### 7.6 单元测试和局部验证

新增或更新：

- `tests/unit/test_pre_verl_agentloop.py`
- `tests/unit/test_run_metadata.py`
- `tests/unit/test_reward.py`
- `tests/unit/test_pre_verl_agentloop_scheduler.py`

重点测试：

- 模拟 pytest `exit_code=4` 且 stderr 包含 `ImportError: libGL.so.1`，断言：
  - boundary 不是 `model_wrong_fix`。
  - run metadata 是 environment failure。
  - reward invalid reason 是 environment failure。
- 模拟模型补丁删除仓库内模块、修改仓库内 import path 或引入不存在的仓库内模块，断言不能被归为 environment failure，应保留为 `model_wrong_fix` 或 `ambiguous_verifier_failure`。
- 模拟 stderr 包含普通 assertion failure，断言不会误归因为 environment。
- run config / freeze manifest 中记录 environment preflight policy。

局部验证：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_pre_verl_agentloop.py \
  tests/unit/test_run_metadata.py \
  tests/unit/test_reward.py
```

然后局部 rerun：

- `pre_verl_dev_018_pyvista__pyvista_4315`

验收标准：

- PyVista final verifier 不再因为 `libGL.so.1` 缺失退出。
- 如果仍然有其他系统依赖缺失，必须被归为 environment failure，并留下 stderr artifact。
- 第 18 题不再被错误统计为可靠的 `model_wrong_fix`。

## 8. 阶段 4：修复 `symbol_search` 宽 root 性能保护

### 8.1 对应问题

- `DEV23-P2-005`：`symbol_search` 在宽 root 下仍可能消耗过多 wall-clock 时间。

### 8.2 当前风险

当前 `symbol_search` 在 [minimal.py](../../src/repo_harness/tools/minimal.py) 中会先 `list_files(root, "*.py")`，然后逐个读取 Python 文件并执行 AST 解析。第 18 题 `root="."` 扫描 347 个 Python 文件耗时约 115 秒，第 22 题扫描 124 个 Python 文件耗时约 35 秒。

这不是 parser 正确性问题，而是工具性能和预算保护问题。模型有时会在首轮直接选择 `symbol_search(root=".")`，即使首轮上下文已经提供了更窄的 repository action index 候选目录。

### 8.3 目标行为

修复后必须满足：

- `symbol_search` 对同一 workspace 的同一 Python 文件不重复解析。
- 宽 root 搜索在候选文件数超过阈值时，不直接执行昂贵全仓扫描。
- 工具能返回可恢复结果，告诉模型收窄 root，而不是把慢扫描结果伪装成普通成功。
- 慢扫描必须可观测：typed result 和 event 中能看到 candidate file count、scanned file count、duration、slow scan 标记和恢复调用。
- 达到软超时或扫描上限时，不能返回可信 no-match，应返回 `semantic_complete=false` 和 `result_kind="partial_symbol_scan"` 或 `scan_requires_narrow_root`。

### 8.4 建议修改位置

- `src/repo_harness/tools/symbol_index.py`
  - 增加缓存对象或可复用 index builder。
  - 缓存 key 至少包含 path 和 source hash。
- `src/repo_harness/tools/minimal.py`
  - 修改 `_symbol_search()`。
  - 增加宽 root 阈值、扫描上限、慢扫描 typed 字段和 recovery call。
- `src/repo_harness/context/builder.py`
  - 更新 `tool_use_guidance`，明确 action index 有候选目录时不要优先 `symbol_search(root=".")`。
- `tests/unit/test_symbol_index.py`
- `tests/unit/test_tools.py`
- `tests/unit/test_context_builder.py`

### 8.5 实施步骤

1. 增加 symbol index cache：
   - cache scope 建议为 per-run 或 per-tool-executor。
   - cache entry 至少包含 `path`、`source_hash`、`symbols`、`parse_error`。
   - 文件被模型编辑后，source hash 改变，应重新解析该文件。
2. 增加宽 root 阈值：
   - 建议初始阈值：`candidate_file_count > 120` 且 `root in {".", ""}` 时触发保护。
   - 阈值应写入工具 typed result，例如 `wide_root_candidate_file_threshold=120`。
3. 宽 root 保护触发时优先返回 recoverable result：
   - `result_kind="scan_requires_narrow_root"`。
   - `scan_complete=false`。
   - `semantic_complete=false`。
   - `recovery_call` 建议使用更窄 root。
   - `recommended_narrow_roots` 可以来自候选文件的顶层 package 统计，例如 `pyvista/core`、`pydicom`、`src/sqlfluff`。
4. 如果决定仍允许部分扫描：
   - 设置 `symbol_search_soft_file_limit`，例如 120 个 Python 文件。
   - 扫描达到上限后返回 `result_kind="partial_symbol_scan"`。
   - 如果没有匹配，也只能说“已扫描子集无匹配”，不能说“全仓无匹配”。
5. 增加慢扫描字段：
   - `slow_scan`
   - `slow_scan_threshold_ms`
   - `duration_ms` 或 `execution_duration_ms`
   - `candidate_file_count`
   - `scanned_file_count`
   - `cache_hit_file_count`
   - `cache_miss_file_count`
   - `recommended_narrow_roots`
6. 更新 `tool_use_guidance`：
   - 如果首轮 action index 已给出候选源码目录，应优先用候选目录作为 `symbol_search.root`。
   - 只有没有任何候选目录，或者前几次窄搜索失败时，才考虑 `root="."`。
7. 保持搜索事实可信协议：
   - parse error、visibility error、read error 仍然导致 partial 结果。
   - 宽 root 中止不能被记为 `complete_no_symbol_match`。
   - result envelope 必须携带恢复调用。

### 8.6 单元测试和局部验证

新增或更新：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_symbol_index.py \
  tests/unit/test_tools.py \
  tests/unit/test_context_builder.py
```

重点测试：

- 同一文件第二次 symbol search 命中 cache。
- 文件内容变化后 cache 失效并重新解析。
- `root="."` 且候选 Python 文件数超过阈值时，不执行完整扫描，而是返回 `scan_requires_narrow_root`。
- partial scan 返回 `semantic_complete=false`，不能返回 `complete_no_symbol_match`。
- `recommended_narrow_roots` 至少包含一个来自候选路径统计的可执行 root。
- 首轮 `tool_use_guidance` 提示模型优先使用 action index 候选目录。

局部验证：

- 对第 18 题和第 22 题做 replay / rerun。
- 扫描所有 `symbol_search.duration_ms > 5000` 的调用。

验收标准：

- 第 18 题不再出现 115 秒级 `symbol_search(root=".")`。
- 第 22 题不再出现 35 秒级 `symbol_search(root=".")`。
- 如果模型仍调用宽 root，工具应返回恢复提示，而不是长时间阻塞。

## 9. 延期项：`DEV23-P2-002` 暂不处理

### 9.1 暂停原因

`DEV23-P2-002` 暴露的是 convergence nudge 未能阻止长期只读探索和空补丁超时。当前已经确认 Harness 会注入模型可见 nudge，且提示内容包含停止大范围探索、选择最小补丁、缺少 `edit_file.old_text` 时读取最小范围、无法完成时 final answer 等内容。

但是，当前正在开发完整的上下文压缩机制，包括 `auto compact`、`tool compact` 和多层次 compact。长期只读探索可能是上下文膨胀、旧工具结果污染、重复搜索结果残留、关键恢复调用被淹没等因素共同导致的。此时直接加更强第三阶段提示，可能会掩盖真正的上下文问题。

### 9.2 本轮只保留的轻量事项

本轮不新增 `near_budget_finalize_patch` 的空补丁第三阶段，也不引入 hard gate。

可以保留以下审计观察，但不作为本计划主修复项：

- 继续记录 `convergence_nudge_injected`。
- 继续记录 `nudge_ignored_empty_patch`。
- 后续如果修改相关代码，可顺手补充 `task_timeout_remaining_sec_at_latest_nudge` 等 wall-clock 字段，但不把它作为本轮阻塞项。

### 9.3 重新评估条件

等上下文压缩机制完成后，执行：

1. 5 题 targeted smoke。
2. 覆盖第 3 题和第 14 题的局部 rerun。
3. 必要时执行新的二十三题开发测评。

如果在 compact 完成后，第 3 题、第 14 题仍然出现：

- 多次模型可见 nudge 后仍无编辑。
- `post_latest_nudge_action="no_observed_action_after_nudge"`。
- 空补丁进入 `task_timeout`。

再考虑新增 experimental convergence policy。该策略应先作为实验配置冻结，不应直接进入最终正式基线。

## 10. 总体验证方案

### 10.1 静态和单元测试

每个阶段完成后至少运行：

```bash
PATH=.venv/bin:$PATH python -m compileall src scripts/pre_verl
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_pytest_parser.py \
  tests/unit/test_pre_verl_agentloop.py \
  tests/unit/test_reward.py \
  tests/unit/test_run_metadata.py \
  tests/unit/test_tools.py \
  tests/unit/test_symbol_index.py \
  tests/unit/test_context_builder.py
```

如果修改 Docker adapter 或 workspace 输出 artifact，再运行：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/integration/test_workspace_lifecycle.py \
  tests/unit/test_docker_adapter_image_platform.py
```

### 10.2 修复前后扫描

修复前和修复后都运行阶段 0 的扫描脚本：

```bash
PATH=.venv/bin:$PATH python scripts/pre_verl/inspect_23_dev_issue_patterns.py \
  runs/pre-verl-agentloop-23-dev-deepseek-pro-development-20260508T185350Z
```

修复后的预期：

- 第 4 题、第 16 题、第 21 题的 parser inconsistency 不再出现。
- 第 18 题的 `exit_code=4` 有完整 output refs 和 exit reason。
- 第 18 题如是环境错误，不再归因为 `model_wrong_fix`。
- 第 18 题、第 22 题不再出现无保护的慢 `symbol_search(root=".")`。

### 10.3 局部 rerun / replay

建议局部验证任务：

| 任务 | 验证目标 |
|---|---|
| `pre_verl_dev_004_sqlfluff__sqlfluff_1517` | 参数化 failed selector 归因。 |
| `pre_verl_dev_016_pylint_dev__astroid_1866` | 参数化 failed selector 归因和 reward 分数。 |
| `pre_verl_dev_018_pyvista__pyvista_4315` | pytest exit code 4 输出审计、PyVista 环境、environment failure 归因、慢 symbol search。 |
| `pre_verl_dev_021_pydicom__pydicom_901` | error_count 和 error_nodeids 一致性。 |
| `pre_verl_dev_022_pydicom__pydicom_1139` | `symbol_search` 宽 root 性能保护。 |

如果有 replay 机制，优先 replay verifier / parser / tool result，不必立即重复完整模型调用。涉及环境修复和 `symbol_search` 性能时，需要至少做局部 Docker rerun。

如果需要直接执行局部 Docker rerun，可以使用下面的命令模板。`--task-id` 可以重复传入；`RUN_DIR` 是 `--output-dir` 指定的目录，具体 `RUN_TASK_DIR` 从 `RUN_DIR/run_task_runs/` 下按任务名查找。

```bash
PATH=.venv/bin:$PATH python scripts/pre_verl/run_agentloop_evaluation.py \
  --pre-verl-task-set-manifest runs/pre-verl-eval-stage1-materialized-task-set-20260507T040000Z/pre_verl_task_set_manifest.json \
  --output-dir runs/pre-verl-agentloop-dev23-remediation-local-rerun-YYYYMMDDTHHMMSSZ \
  --mode smoke \
  --task-id pre_verl_dev_004_sqlfluff__sqlfluff_1517 \
  --task-id pre_verl_dev_016_pylint_dev__astroid_1866 \
  --task-id pre_verl_dev_018_pyvista__pyvista_4315 \
  --task-id pre_verl_dev_021_pydicom__pydicom_901 \
  --task-id pre_verl_dev_022_pydicom__pydicom_1139 \
  --provider deepseek \
  --model-id deepseek-v4-pro \
  --execution-mode docker \
  --permission-mode auto \
  --deepseek-thinking disabled \
  --run-id-prefix pre_verl_agentloop \
  --execute
```

### 10.4 Targeted smoke

局部验证通过后，执行一个干净的 5 题 Docker targeted smoke，建议覆盖：

- `004 sqlfluff`
- `016 astroid`
- `018 pyvista`
- `021 pydicom`
- `022 pydicom`

如果考虑和历史 smoke 对齐，也可以保留一两个已 accepted 的 sanity task，但本轮目标是验证 hardening，不是最大化 accepted 率。

可执行命令模板：

```bash
PATH=.venv/bin:$PATH python scripts/pre_verl/run_agentloop_evaluation.py \
  --pre-verl-task-set-manifest runs/pre-verl-eval-stage1-materialized-task-set-20260507T040000Z/pre_verl_task_set_manifest.json \
  --output-dir runs/pre-verl-agentloop-targeted-smoke-dev23-remediation-YYYYMMDDTHHMMSSZ \
  --mode smoke \
  --task-id pre_verl_dev_004_sqlfluff__sqlfluff_1517 \
  --task-id pre_verl_dev_016_pylint_dev__astroid_1866 \
  --task-id pre_verl_dev_018_pyvista__pyvista_4315 \
  --task-id pre_verl_dev_021_pydicom__pydicom_901 \
  --task-id pre_verl_dev_022_pydicom__pydicom_1139 \
  --provider deepseek \
  --model-id deepseek-v4-pro \
  --execution-mode docker \
  --permission-mode auto \
  --deepseek-thinking disabled \
  --run-id-prefix pre_verl_agentloop \
  --execute
```

targeted smoke 必查：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-pre-verl-agentloop-boundary-index \
  RUN_DIR/pre_verl_agentloop_final_verifier_boundary_index.json \
  --assert-all-formal-runs-bound \
  --assert-command-order \
  --assert-clean-source-origin \
  --assert-run-task-lineage \
  --assert-no-legacy-adapter
```

并对每个 run 执行：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-model-visible-context RUN_TASK_DIR \
  --assert-no-hidden-test-material \
  --assert-prepared-messages-bound \
  --assert-provider-body-equivalent \
  --assert-tool-results-recoverable \
  --assert-no-over-redaction
```

### 10.5 进入下一轮二十三题的门槛

只有满足下面条件，才建议进入下一轮二十三题开发测评或正式基线：

- parser inconsistency 扫描为 0。
- `exit_code=4` 都有 output refs、preview 和 exit reason。
- PyVista 环境 preflight 通过，或者环境失败能被正确剥离为 environment / verifier failure。
- `symbol_search(root=".")` 不再出现 30 秒以上无保护扫描。
- `inspect-pre-verl-agentloop-boundary-index` 通过。
- `inspect-model-visible-context` 全部通过。
- `final_verifier_boundary.json`、`run_metadata.json`、`reward.json` 三者的 failure owner、failure category、failure type 和 invalid reason 口径一致。
- environment / verifier failure 不进入 trainable export，不进入 `model_wrong_fix` 分母。
- run matrix 或汇总报告中有 `environment_or_verifier_failure_count` 或等价字段；如果当前没有现成字段，阶段 0 扫描脚本必须输出等价统计。
- 新 smoke 没有新的 P1 / P2。

如已有 export 或 reward inspect 命令可复用，应增加对应断言；如果没有现成命令，本计划要求阶段 0 扫描脚本覆盖这些检查，并在 smoke 结束后输出机器可读 JSON。

## 11. 风险和回滚策略

### 11.1 parser 修复风险

风险：参数化 selector 匹配过宽，可能把不属于 selector 的 node id 归进去。

控制方式：

- 匹配必须基于完整 node id 边界，只允许 `selector`、`selector[...]`、`selector::child`。
- 不能使用普通字符串包含匹配。
- 对所有 match strategy 写入审计字段。

### 11.2 环境错误归因风险

风险：模型补丁导致 import error，却被错误归为环境失败。

控制方式：

- 只有在 clean environment preflight 已失败、final verifier stderr 明确命中外部系统共享库缺失，或者同一第三方依赖缺失能在没有模型补丁的 clean verification workspace 中复现时，才归为 environment failure。
- 如果模型补丁修改了 import 路径或删除包内模块，应保留为 `model_wrong_fix` 或 `ambiguous_verifier_failure`，并把 evidence 写入 diagnostics。

### 11.3 `symbol_search` 宽 root 保护风险

风险：过早要求收窄 root，导致模型拿不到全局符号信息。

控制方式：

- 返回 `recommended_narrow_roots` 和可执行 recovery call。
- 对候选文件数低于阈值的仓库仍允许完整扫描。
- 提供显式配置或调试参数允许宽扫描，但正式评测默认保护开启。

### 11.4 与上下文压缩机制的交互风险

风险：本轮修复增加的字段或 artifact 被后续 tool compact 错误压掉。

控制方式：

- 所有新增关键诊断字段都进入 artifact-backed result envelope。
- tool compact 必须保留 tool call / tool result 配对，以及 `result_envelope.recovery_call`、`pytest_exit_reason`、`output_artifact_ref`、`semantic_complete` 等关键字段。

## 12. 完成定义

本计划完成时，需要产出以下证据：

1. 代码修改完成，并有清晰的 diff 范围。
2. 单元测试和必要集成测试通过。
3. 阶段 0 扫描脚本能证明旧问题不再复现，或被正确重分类。
4. 第 4、16、18、21、22 题完成局部 replay / rerun。
5. 干净 5 题 Docker targeted smoke 通过基础审计。
6. `docs/resume/pre-verl-23-dev-evaluation-issue-log.md` 更新每个问题状态：已修复、已验证、延期或仍需处理。
7. 如果要进入下一轮二十三题，必须明确本轮 smoke 没有新增 P1 / P2。
