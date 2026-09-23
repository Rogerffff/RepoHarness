# CR2 收尾判据修复复核（2026-09-19）

**本轮通过，CR2 可以核销。** 上轮约定的三个失败边界、既有正控，以及本轮增加的 pytest-pretty / 外层 rc=0 对照全部符合预期。没有新增阻塞项或 T0；结束这一边界的扩审。

## 1. 验证结果

| 对照 | 当前生产结果 |
| --- | --- |
| quiet 父正常结束、子 pytest collection 失败 | `tests_failed / 0 / source_rule`；实际组 `[1,0]` 可消费 |
| quiet 父确实 collection 中断、子 pytest 成功 | 无资格时保持 None；实际组 `[1,None]` 不可消费 |
| 普通父 conftest 启动失败、只有子 pytest 成功摘要 | 无资格时保持 None，不发起 compile；实际组不消费 |
| 上例外层退出码未知 | 不借子摘要证明外层完成；保持 None |
| 原真机 Python 3.9.19 / pytest 6.2.3 嵌套日志 | 仍为来源 0；实际组可消费 |
| 外层 rc=0，测试有意调用失败子 pytest 并处理其结果；默认、quiet、pretty 三种输出 | 最后外层摘要 `2 passed` 被识别。参考 ID 随候选变化导致全部缺席时，按来源规则给 0；不是因为外层测试全过就给 1 |
| pretty 外层 `1 failed, 1 passed`、rc=1 | 正常完成，来源 0 |
| pretty collection 中断、rc=2 | 不算正常完成，保持 None |
| pretty `--continue-on-collection-errors`，`2 passed, 1 error`、rc=1 | error 计数否定正常完成，保持 None；实际组不消费 |

共 **41 个 manager 评分对照、6 个实际组运输对照，预期全部匹配**。其中既有 10 个真实语法 collection/conftest 正例仍为 `candidate_execution_failed / 0`，16 个未归因对照保持 None，15 个正常执行/参考缺席对照保持来源 0。CR1、CR3 等此前核销状态不变。

[完整结果](replay_result.json) / [复核脚本](replay_current.py) / [运行输出](replay_run.txt)。组运输使用真实 orchestrator、miles buffer 和训练数据转换；模型、容器操作及资源读取使用维护替身，不能称为 GPU 或真实模型训练复现。

## 2. pytest-pretty 不是只对手写格式做匹配

新增隔离运行环境为 **pytest 8.3.5 + pytest-pretty 1.2.0**，未更改项目依赖或锁文件。实际插件根据 pytest 的统计项输出缩进计数，已运行 passed、failed、collection error，以及 passed+error 同时出现的情况。

- pretty 对照使用当前 pydantic 配方的 `--tb=short -vv -o console_output_style=classic --no-header` 输出选项，随后通过项目已有的 **pydantic parser** 进入 manager。源文件变化与固定测试分开，未伪造 pytest 状态行。
- [真实日志](pydantic_runtime/pretty_actual_logs.json)、[生成脚本](generate_pydantic_logs.py)、[插件版本与源码摘要](pretty_runtime.json)、[检查过的插件源码](pytest_pretty_1_2_0_source.py)。这是固定版本的兼容性证据，不宣称覆盖所有 pytest/插件版本，也未确认它恰好等于原镜像插件版本。
- 作者“只有 passed 样本”的表述可以收回：既有 `evallog_replay-e2A-20260915-pyda_626f777f.eval.log` 已有 `Results (0.85s):` 后的 `1 failed / 44 passed`。本轮另补了真实 error 运行，消除了只靠推断 error 文法的缺口。

## 3. 退出事实与现有运行范围

`prepared_task_face._v2_candidate_test_lines` 在派生测试命令之后立即执行 `RH2_TEST_RC=$?`，再输出 End 标记和退出事实；manager 从独立的事实行读取退出码。核对 [216 条固定命令快照](command_contract_scope.json)，全是单条 pytest 调用，无 shell 复合操作符、无显式 quiet。故本次使用命令的 0/1 退出事实与最后摘要共同判定正常完成，在当前范围有生产接线依据。

**两点非阻塞的口径澄清，登记后不再为此增加代码修复轮次：**

1. 未识别摘要或退出事实不支持正常完成时，代码只是**不走正常完成短路，退回既有失败形状及三路判定**。它不保证一律 None：`reference_all_missing` 且没有全局失败形状时，既有 `source_rule` 分支仍可给 0。§10.6 的“其它未识别格式走未确定”应按这个实际控制流理解，不能当成额外拒绝规则。
2. 复合命令在本片**未覆盖**，实现没有一个专门识别复合命令并强制返回 None 的闸门。后续若引入复合命令，应随配方接线确认退出事实对应哪个运行器；当前不需为尚未采用的命令添加通用 shell 分析器。`classify_execution_failure_shape` 的“test_rc 只作为证据”旧 docstring 也可随下次文档清理改成“参与正常完成判定，不单凭退出码归因候选”。

以上不改变来源评分、binary_v1、候选归因、完整组规则或用户已经决定的流水线分期。

## 4. 本轮主审证据与停止条件

| 检查 | 结果与边界 |
| --- | --- |
| 相关维护测试：`uv run pytest tests/grading/test_w3b_grader_profile_unit.py tests/adapters/test_batch4_pa_transport.py -q -rs` | **63 passed**；[输出](pytest_targeted.txt) |
| ruff：本次 manager 与对应维护测试两个文件 | 通过；[输出](ruff.txt) |
| 原始日志/manager 对照 | 41 案通过，含原 pytest 9.1.1 / 6.2.3 日志重放和新 pytest 8.3.5 / pretty 真实运行 |
| 实际组运输 | 6 案通过；3 个可消费 `[1,0]`，3 个拒绝 `[1,None]` |
| 59 条真机日志离线复核 | hash 全匹配；28 tests_failed + 24 resolved 判正常完成，另外 7 条不判正常完成；本次短路未改变形状结论。[证据](saved_corpus_result.json) |
| 远端一致性 | 7 个评分核心/运输/测试文件 SHA-256 与作者独立树一致；[快照](source_snapshot.json)。仅只读核对，没有新跑远端评分 |

其他 A 任务并行修改 `generate.py` / `bringup.py`；本轮裁决限定在评分切片。审查期间 `bringup.py` 继续变化，已记入[结束快照](review_end_source_check.json)，不以此声称整个共享工作树已完成集成审查。被审 manager、对应测试及评分依赖未变化。

作者的全量 1413 非 Docker / 34 Docker 数字未在本轮重复运行，不转述为主审独立验证。本轮未改生产代码、维护测试、配置、历史 evidence 或提交，只补本审查目录及 A 线/原计划登记。既定停止条件已满足，CR2 核销；后续有新版本、新配方或真实失败证据时再按实际影响复查。
