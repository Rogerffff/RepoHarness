# CR1–CR3 窄修复核 / Codex（2026-09-19）

**结论：CR1、CR3、formal 缓存计数持久化通过；CR2 原反例通过，但还有一个同边界余项，暂不能整体验收。** 只保留下述一项 P1，不重开已通过项、反作弊、资格政策或资源默认值。无新增 T0。

基线：`bac7659e` 加本次未提交实现。78 个涉及文件与作者真机树一致，收尾源码摘要未变，见 [source_snapshot.json](source_snapshot.json)。本轮没有修改生产源码、维护测试、配置或提交；历史证据保持只读。

## 1. 唯一余项：CR2 / P1，捕获的子 pytest 标题被当成父层边界

**真实例子。** 两个固定父测试的参数 ID 来自候选源码中的 `label`。`before` 时两项通过；候选仅将 label 改为 `after`，其中一个测试启动子 pytest，子 pytest 因缺模块发生 collection error，另一个父测试通过。测试文件前后摘要完全一致。父 pytest 正常结束，退出码 1、结果 **1 failed + 1 passed**；原参考 ID 都是 `[before]`，当前来源评分函数给 tests_failed / 0。

父测试捕获的真实子进程输出是：

```text
----------------------------- Captured stdout call -----------------------------
============================= test session starts ==============================
...
==================================== ERRORS ====================================
_ ERROR collecting child/test_child.py _
...
```

**根因与源码。** `rh2/src/repoharness2/grading/manager.py:1117,1130–1133` 将任何 `=== … ===` / `___ … ___` 当作 Captured 结束。子 pytest 的 `test session starts` 标题因此立刻结束剥离，随后内层 `ERROR collecting` 被 `classify_execution_failure_shape`（1147–1151）当成外层全局故障。`_decide_execution_failure` 未走 source_rule，最后覆盖成 `test_log_parse_failed / None`。

这违反的仍是 CR2 已定边界：单测试捕获内容不能单独证明整个测试过程启动/收集失败。没有构造伪造评分行或修改测试，不是新增反作弊要求。

**证据与训练影响。**

- 独立检查在默认 `-rA`、`--tb=short/long/native`、`-rA -q` 五种真实日志中均复现，见 [独立报告](independent/README.md)、[输入输出矩阵](independent/probe_pytest_shapes.json)。
- 主审重新构造固定父测试并执行真实 pytest，复核来源 0 → 实际 None，见 [可运行探针](probe_nested_pytest.py)、[本机结果](root_nested/result.json)。
- 在已有 dvc-5822 镜像中另用临时目录执行相同控制：**Python 3.9.19 / pytest 6.2.3**，before 退出 0，after 退出 1、父测试正常完成。真实镜像日志输入当前 manager 后仍 0 → None。见 [真实镜像输出](remote_nested_pytest.json)、[manager 复核](remote_log_grade/result.json)。此控制使用无网络、只读根、候选 uid，不运行 SWE 题目或改镜像。
- 主审将这份 pytest 6.2.3 日志接入真实 RH2→miles 组运输：两个成员结果为 `[1, None]`，整组未进入 buffer。见 [nested_group_result.json](nested_group_result.json)。模型/容器运输使用维护替身；没有运行 GPU 更新或声称真实训练已污染。

**可达性与频率。** 当前 replay/formal manager 均可达，无环境资格前提；需要测试自然调用子 pytest，且参考 ID 全缺席。该组合在已选题库中的发生率未知，不以构造例声称普遍损耗。普通 Python 子进程的上一轮反例已经通过，本项是 Captured 作用域处理尚未完整。

**建议修法与代价。** 建议 `accepted`，在核销 CR2 前完成。让**可确认的外层正常完成事实**成为来源评分的正向依据，例如末尾外层短摘要中的逐测试状态、正常完成汇总以及没有 collection 中断；全局故障也应归属于外层。不要仅靠 `num_parsed_tests > 0`，本例 parser 的计数还包含子进程文件级 ERROR；也不必继续添加标题正则来猜任意嵌套层级。

这一方向已作进程内设计对照：同一批日志的 5 个嵌套例恢复 0，其余 20 个案例结果不变，包括 10 个真实候选语法失败正例。见 [设计对照](independent/completion_evidence.json)。它未修改生产文件，不等于已实施或完全审过的修复；作者仍需按现有运行器范围实现并保留无法确认时的原处置。成本限于现有 classifier/manager 接缝，不新增服务、公共契约、拒绝规则或人工审批。

**停止条件。** 本自然嵌套例在 manager 中恢复来源 0、组运输恢复可消费的 `[1,0]`，且本轮 collection/conftest 真语法失败、普通参数路径反例、普通 Python 子进程反例不回归，即可关闭 CR2。无需再审任意嵌套运行器、伪造日志或全题库。

## 2. 已核销项目

| 项 | 本次证据与裁定 |
| --- | --- |
| CR1 参数中的普通路径提及 | **通过。** 原坏/好 unused 对照均 None、不发起 compile；五种 traceback 形态共 10 个真实 collection/conftest 正例仍为 candidate_execution_failed / 0。行号错位回归通过。六行窗口属于已测格式覆盖，不另扩为新闸门。 |
| CR2 原普通 Python 子进程反例 | **原例通过。** 固定测试的 1 fail + 1 pass 保留来源 0；实际组运输恢复 `[1,0]`。仅保留 §1 子 pytest 分节头余项。 |
| CR3 排除命名空间 | **通过。** 真实 Git `__pycache__/probe` 分支仍可解析，`.harness` 文件与排除区/整份 manifest 摘要不变；scoreable 缓存正常删除，同名普通文件/软链保持，原目录→普通文件/软链重放正常。 |
| formal 缓存计数 | **通过。** baseline 2 目录/3 文件、post 4 目录/5 文件的运输 fixture，经真实编排与 `write_execution_audit_record` fsync 后重读，值完整保存；不是只检查内存对象。 |
| 状态文案 | 已将 pids 记为资源干扰证据；R7 完整信息在 audit；R5 构造器运输与正式加载来源已区分。构建归因 F4、资格供给等既有后续工作并未因此核销。 |

主审旧例重放见 [old_case_summary.json](old_case_summary.json)、[组运输](replay/group_transport_result.json)、[缓存与持久 audit](cache_audit/probe_results.json)。副本仅调整已修期望与新输出目录，不改历史探针；所有真实执行输出重新生成。

## 3. 验证范围

| 验证 | 结果 |
| --- | --- |
| 本机 contracts/adapters/governance/grading/envpack 非 Docker 套件 | **1407 passed、1 skipped、48 deselected**；skip 为未配置可选本机全量 parser corpus，入库 corpus 已执行。ruff 通过。 |
| 本机实际 batch4 Docker 往返 | **4 passed**，使用已有 fixture 镜像。没有将作者全部 34 项 Docker 声称为主审本轮重跑。 |
| 独立真实日志矩阵 | 45 次 pytest 子进程、30 次实际 manager 调用，25 个案例（参数路径每例含坏/好两个对照）；仅容器/资源为维护替身。维护 CR1/CR2 用例另有 4 passed。 |
| 新真机两行 | dvc-5822 新规则记录 `syntax_error_locations={'dvc/repo/__init__.py':[145]}`、编译复证同行，moto-6913 仍 tests_failed。两份日志摘要/sidecar 对上，旧代码产生的两行 `*_stale` 明确不计入。见 [账本核对](new_ledger_audit.json)。 |
| 远端动作 | 读取作者代码摘要；一个隔离临时容器核对真实 pytest 6.2.3，已回收，无本次容器残留。没有操作 B 的代码树、容器、镜像标签或内核参数。 |

完整结果见 [verification.json](verification.json)。本轮不重跑已通过的 Python 隔离复证版本矩阵、其它清理/取消切片或 SWE 题库。所有需写 prepared 产物的复跑使用新目录，旧工件保持只读。

下一轮只需 Claude 收齐 §1 的外层完成判据及上述正反控，CR1/CR3/计数不重新开放。B 环境工作与新 A 的后续决策继续推进；本报告没有新增用户待拍板项。
