# CR1/CR2 独立有界复核（2026-09-19）

**CR1 在本轮真实日志范围内闭合；CR2 的原 Python 子进程反例闭合，仍有一项自然嵌套 pytest 的同边界余项。** 没有新增反作弊、环境资格或资源规则；没有修改生产源码、维护测试、共享文档、历史探针或历史证据。

本机 Python 3.12.13 / pytest 9.1.1，使用默认 `-rA`、`--tb=short`、`--tb=long`、`--tb=native` 和 `-rA -q` 五种形态。45 次真实 pytest 子进程产生新日志，30 次实际 `SWEGradingManager.grade` 读取这些日志；需要时执行生产 compile renderer 生成的真实 Python 编译脚本。容器、资源观察与资格使用既有维护替身，**没有执行 Docker、SSH、API 或真实训练**，因此不把 CPU 资格注入称为真实题目资格。探针开头/结尾源码摘要一致，见 [完整输入输出](probe_pytest_shapes.json) 和 [摘要](summary.json)。

| 验证 | 当前 manager 实际结果 |
| --- | --- |
| collection / conftest 导入候选坏语法，各五种日志 | 10/10 为 `candidate_execution_failed / 0`；位置均为 `src/thing.py:1`，真实复证同行命中。collection parser 的一条文件级 ERROR 仍正确触发，未被“非零解析”错误放行。 |
| 普通参数 `load_metadata("src/unused.py")`，实际缺外部依赖 | 五种日志各配坏/好 unused 源码，10/10 均为 `test_log_parse_failed / None`，语法位置为空、没有发起 compile。 |
| 固定父测试、只改候选 label；捕获 Python 缺模块异常，父 1 failed + 1 passed | 5/5 为 `source_rule → tests_failed / 0`；测试源码前后 SHA-256 一致。 |
| 同样固定父测试，子进程换成真实 pytest collection 缺模块 | 5/5 仍错误地为 `unattributed → test_log_parse_failed / None`；详见下文。 |
| 维护测试 `-k 'test_pa_cr1 or test_pa_cr2'` | **4 passed、51 deselected**，见 [维护测试输出](maintenance_pytest.log)。 |

**唯一余项：CR2 / P1，Captured 中内层 pytest 的自然标题使剥离提前结束。** 默认日志 [captured_pytest_default_rA.log](logs/captured_pytest_default_rA.log) 第 96 行是父 `Captured stdout call`；第 97 行是子 pytest 自己输出的 `=== test session starts ===`。`rh2/src/repoharness2/grading/manager.py:1117,1130–1133` 把这个内层标题当成父级分节边界，后续子 `ERROR collecting` 被保留。随后 `classify_execution_failure_shape:1147–1151` 返回 `pytest_error_collecting`，`_decide_execution_failure:3106–3115` 未进入来源分支，`grade:1832–1836` 转成 None。

父 pytest 实际末尾是两条 `[after]` 测试状态和 **1 failed + 1 passed**（默认日志第 119–122 行），rc=1。参考 ID 保持 `[before]`，所以真实 parser 得到 `reference_all_missing`；其 `num_parsed_tests=3` 含子进程的一条文件级 ERROR，不能把这个数字称为三个父测试。生产来源评分在同一输入上已是 `tests_failed / 0`，本轮分流却将其覆盖为 None。违反的是原 CR2 已定“正常完成测试中的捕获输出不能单独证明全局启动/collection 失败”，不是新反作弊要求。

此路径在当前 replay/formal 使用的 manager 分流中**生产可达**：仅需已有测试自然启动子 pytest、候选改变参数 ID 使参考全缺席；不依赖资格供给或未实施能力。具体 SWE 题库发生率未知，本子审未证明已选任务已出现该组合，也未执行训练。影响是把正常失败负样本变成不可评分，并按既有准入语义可能连带丢组；组运输由主审验证。

建议将这一个余项与 CR2 一并窄修后核销；不暂停环境/数据工作，也不扩成任意嵌套日志解析器。优先把**末尾外层短摘要中的逐测试状态、正常完成汇总及没有 collection 中断**作为正向来源规则证据，保留真正 collection/conftest 分流；不能单凭 `num_parsed_tests > 0` 放行，也不继续增加任意分节标题正则来猜嵌套层级。这样只触及当前 manager owner，不需新状态、公共契约或服务；是否能泛化到更多运行器仍未知，未识别格式继续既有未知去向。

[局部设计对照](completion_evidence.json) 将这个方向以本进程函数替换验证于相同日志和真实 manager：5 个内层 pytest 例恢复 0；其余 20 个案例结果不变，包括全部 10 个真语法失败正例。脚本 [probe_completion_evidence.py](probe_completion_evidence.py) 在退出前恢复函数，生产文件 SHA-256 未变。**这是修法方向的实证，不是已实施修复，也不是完整新 parser 的验收。** 相比删除已批 P-A、整体 fail-stop 或直接递延已知同边界误分流，局部修正的影响面和验证成本较小。

复现命令：从仓库根，以 `PYTHONDONTWRITEBYTECODE=1 rh2/.venv/bin/python <新证据目录>/probe_pytest_shapes.py` 执行；设计对照随后运行 `probe_completion_evidence.py`。已有证据保持只读，复跑时把两个脚本和 `old_probe_copy.py` 复制到新的输出目录；脚本从自身路径向上找到仓库，输出随新目录落盘。维护测试从 `rh2/` 运行 `.venv/bin/python -m pytest -p no:cacheprovider -q tests/grading/test_w3b_grader_profile_unit.py -k 'test_pa_cr1 or test_pa_cr2' --basetemp=<新的输出目录>/maintenance_tmp`。

**停止条件：** 只要求该自然内层 pytest 例在 manager 中回到来源 0，且本次 collection/conftest 正控、普通路径反例和普通 Python 子进程反例保持通过。满足后停止这轮 CR1/CR2 扩审。CR1 的六行窗口、其它未覆盖 pytest 版本或日志格式只记录为首片格式覆盖范围，不另设新门；不重开资源、反作弊或资格全链路审计。
