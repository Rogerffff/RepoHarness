# P-A Training Semantics 窄复核（2026-09-19）

结论：**R2、R3 的原问题在本轮范围内闭合；R1、R4 的原具体反例已修，但各留一个同边界余项。** 两项余项都已用真实 pytest 输出进入生产 manager 复现，并验证其实际改变 reward 与组准入。没有新增反作弊平台、资格决策、资源门或训练规则。

只读生产源码与维护测试；新证据全部在本目录。无 SSH、Docker、GPU 或 API。容器 I/O 使用现有 `ProfileGraderFakeDocker`，pytest 与生产 `python -I -S` 内存编译脚本真实执行；资格为 CPU fixture 注入，不等于已取得真实题目资格。真实镜像与资格入口的复核由主审/另一子审负责。

## 原 R1–R4 的闭合状态

| 原项 | 本次正反例 | 结论 |
| --- | --- | --- |
| R1 无关坏语法 | 原例未提及 `src/unused.py` → None，未运行 compile；真实 collection / conftest 导入 `src/thing.py` 坏语法 → 0 | 原具体反例通过；“任意路径提及”尚不能证明因果，见 T1 |
| R2 复证导入仓库模块 | 根 `json.py` / `py_compile.py` / `sitecustomize.py` / `usercustomize.py` 都含导入副作用；目标坏语法正确报 ERROR，合法文件与这些同名模块正确报 OK，副作用不执行；`src/__pycache__` 为普通文件仍可编译 | 本轮闭合；不外推为安装可改解释器的 D3 风险已解决 |
| R3 必要事实全未知仍给 0 | 同一真实 collection SyntaxError：事实已知 → 0；全部事实与 test rc 未知 → None 且具名列缺失；单独缺 rc → None；OOM 正事件 → None | 原缺失事实问题闭合；pids 取舍见下文 |
| R4 正常完成但参考全缺席 | 原例真实 1 failed + 1 passed、rc=1 → `tests_failed / 0`，资源事实未知也不读取；但固定测试内部子进程 traceback 会再次改为 None | 原具体反例通过；完成/全局失败界限仍有 T2 |

完整输入、输出和源码 SHA-256 见 [probe_chainfix_training.json](probe_chainfix_training.json)。维护测试为 **26 passed、26 deselected**，见 [maintenance_pytest.txt](maintenance_pytest.txt)。旧探针先复制为 [old_probe_copy.py](old_probe_copy.py)、[old_group_probe_copy.py](old_group_probe_copy.py)，副本与原文件逐字节一致，历史证据未改。

## T1 / P1：回溯中的普通参数路径仍被当成异常位置

**事实。** 测试 collection 执行 `VALUE = load_metadata("src/unused.py")`，回溯把该调用参数显示出来；`load_metadata` 在导入外部依赖时发生 `ModuleNotFoundError`，完全没有读取、导入或编译 `src/unused.py`。此前同一测试在依赖可用时 2 passed。候选 unused 文件坏语法时，manager 报 `candidate_execution_failed / 0`；同一失败日志，仅将 unused 文件换成合法源码，就变成 `test_log_parse_failed / None`。

**根因。** `manager.py:1125–1139` 的 `referenced_candidate_paths` 对整个测试段做单词边界匹配；`manager.py:3082–3104` 随后把任意匹配路径的 SyntaxError 与通用 collection 形状拼接。路径只出现在源代码参数行，不是实际 SyntaxError 的文件位置；真实终止异常仍是缺依赖。给路径增加左右边界修了子串误认，尚未满足旧 R1 的正向异常关联要求。

**运输与可达性。** [group_transport_result.json](group_transport_result.json) 的 `r1_bad` 经过 prepared registry → 真实 orchestrator → manager → miles `DefaultDataBuffer` → 训练转换，产生 `raw_reward=[1.0,0.0]`，两个成员 loss mask 均非零；`r1_clean_same_log` 整组未进 buffer。当前 replay 的 `--qualification-ledger` → `ReplayGradeDriver.replay_one`（`replay_grade.py:434–438,584`）可给同一 manager 注入资格，属 `production_reachable`；formal 负样本分支取决于流水线向已接的资格入口供给记录，不能据 CPU 注入宣称现时真实训练已污染。

**最小修法与取舍。** 建议 `accepted`，作为旧 R1 未闭合部分在 producer 验收前修：仅将真实异常块中明确的语法异常位置与候选路径/复证结果关联；普通参数、源码引用、日志文本提及不充当该位置。定位不足仍沿原 None 分支。保留已有 startup/collection 真语法失败两个正控，避免退回“所有 collection 都给 0”或“完全删除负样本 producer”。不新增 owner、状态机、重试或服务；正常已有测试结果不变。运行时调用方式常见，但该组合频率未知；代价是格式尚未覆盖的真实语法错误暂留未知，胜于错误负反馈进入训练。

## T2 / P1：测试内部 traceback 仍被当成全局启动失败

**更强的固定测试证据。** [supplemental_r4_fixed_tests.json](supplemental_r4_fixed_tests.json) 中测试源码前后 SHA-256 一致，只改候选 `label="before"` 为 `"after"`。测试参数 ID 来自 label；`before` 时两个测试通过，`after` 时 feature 测试调用一个缺模块的 Python 子进程，stable 测试仍通过。pytest 正常完成 **1 failed + 1 passed，rc=1**。子进程真实 stderr 被 pytest 放在 `Captured stderr call` 中，含 `ModuleNotFoundError:`；没有全局 startup/collection 失败。两条参考 ID 都仍是 `[before]`，故来源规则按缺席给 0。

manager 却匹配 `python_traceback_startup_error`，最终 `test_log_parse_failed / None`。该例无资格也复现，不依赖依赖在资格后消失、测试文件修改或伪造 stdout。

**根因与运输。** `manager.py:1081–1083,1107–1121` 在完整测试段中搜索通用 Python 异常行，没有区分 pytest 捕获的单测试子进程输出与顶层运行器异常；`manager.py:3033–3038` 只在完全没有形状匹配时保留来源规则。主探针还验证：相同局部 traceback 日志只要一个参考 ID 在场，就按来源给 0；全部缺席则变 None。组运输 `r4_simple` 为 `[1,0]` 并进入 buffer，`r4_nested` 整组丢弃，两组都未注入资格。

**可达性。** `production_reachable`，replay 和正式 actor 均可到达：解析出全部非参考测试状态 → `execution_failure_trigger=reference_all_missing` → shape 匹配 → `_decide_execution_failure` → `GradingInfraError`。无新增功能或资格前提；异常被 manager 转为 infra 报告，准入按现有规则整组丢弃。这里不是声称真实题库已观察到该组损失；实测层是 CPU 真实日志和生产运输代码。

**最小修法与取舍。** 建议 `accepted`，作为旧 R4 范围修正继续补齐：有可信逐测试结果并明确正常完成时，测试内部捕获的 Python traceback 不能单独证明全局 startup failure；这类日志保留来源规则。不要直接用 `num_parsed_tests>0` 代替判断，文件级 collection ERROR 也会计入该数。可在现有形状分类中排除 pytest captured 块的通用 traceback，结合完成/逐测试状态判定；真实 conftest 启动和 collection 中断仍走原三路。无需新增状态、重试、平台或 fail-stop。候选导致的普通失败与 ID 变化应继续留下 0 分；当前误判会丢掉同组正常成员。频率未知，局部修正优于删除已批能力或暂停整次运行。

## R3 / pids 的范围说明，不列新 finding

`pids.events max` 是本轮新增的配额触发计数，不能仅据计数文字声称“当前测试被强制终止”。本次同一真实 SyntaxError 日志、rc=2、OOM=0，只把替身读数 `max=0` 改成 `max=1`，结果从 0 变 None；这证明当前在资源干扰可能存在时保守拒绝归因的规则生效。**没有真实 cgroup 历史证明该事件与本次失败无关，因此不据此报告新的归因缺陷或阻塞项。** 文档宜保留“配额命中/存在资源干扰”与“已证进程终止”的区别。

有可信实际结果的分流也已对照：原 R4 普通完成日志即使资源全未知，仍 `source_rule / 0` 且不读资源；同一含子进程 traceback 的日志，只要一条参考结果在场，即使替身 `pids max=1`，也不触发 P-A、仍按来源给 0。资源不确定性目前不是所有正常评分的全局门；`memory.peak` 不是必要事实。

## 复跑与停止条件

从仓库根运行主探针、组运输和固定测试补充探针（均设置 `PYTHONDONTWRITEBYTECODE=1`）：

```text
rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch4_scoring_20260910/chainfix_review_20260919/training/probe_chainfix_training.py
rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch4_scoring_20260910/chainfix_review_20260919/training/group_transport_probe.py
rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch4_scoring_20260910/chainfix_review_20260919/training/supplemental_r4_fixed_tests.py
```

维护测试从 `rh2/` 运行：`.venv/bin/python -m pytest -p no:cacheprovider -q tests/grading/test_w3b_grader_profile_unit.py -k 'test_pa_' tests/adapters/test_batch4_pa_transport.py`。本次将 `--basetemp` 指向本目录的 `pytest_tmp`，未写仓库测试目录。

三个独立探针退出 0，组运输断言通过。主探针记录的四份生产/维护测试源码摘要在收口时仍一致。这里只要求 T1 的真实异常位置关联、T2 的正常完成边界及现有正控复验；R2/R3 不继续扩审，反作弊、资格记录生产和 F4 构建切片沿现有安排，不新增前置条件。
