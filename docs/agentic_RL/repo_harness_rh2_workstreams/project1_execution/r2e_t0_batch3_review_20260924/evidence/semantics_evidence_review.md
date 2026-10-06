# 批次三独立语义与证据复核

复核时间：2026-09-25（本地日期）。职责：Falsifier / Training Semantics 子审查；只读生产代码、材料和原始证据。未运行 Docker、远端命令或 pytest；只在本目录新增复核脚本与结果。

结论：在本批**指定的材料 v3 / pins v4、derived7 与 replay_b5**范围，未发现阻塞静态审查的语义或证据问题。环境资格不等于正式入池；orange3 两个 scorer 键继续交评分质量筛查。

## 直接证据与复核方法

- [semantics_evidence_probe.py](semantics_evidence_probe.py)：独立读取 JSON、pytest 摘要和 Git blob，未调用实现方的 `analyze_b3.py`、`extract_fixtures.py` 或生产 parser。
- [semantics_evidence_result.json](semantics_evidence_result.json)：611 项断言式核对全部通过；含逐 fixture 的原路径、最近 conftest 层级、base blob、原行号、复制行号与 decorator，以及 28 行正式日志与镜像定位。
- 重复执行：在仓库根运行 `PYTHONDONTWRITEBYTECODE=1 python3 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_t0_batch3_review_20260924/evidence/semantics_evidence_probe.py`。仅覆盖本目录的复核结果 JSON。

## Fixture 与 expected 语义

隐藏测试从原数据行取原文，先与修复提交中的原文件逐字匹配，取得真实原路径；再从本地缓存 `runs/r2e_static_prep_20260924/git/pandas.git` 读取每题评分面 `base_commit` 的完整祖先 conftest 链，按最近层级解析 fixture。6 份新增 conftest 中共 20 个 fixture 的函数、decorator、参数、默认 scope 与原文一致；依赖闭合、导入来自同一 base 链，没有多提或漏提 fixture，没有新增 autouse/hook。特别核实 7dd3 的 `sort` 取 indexes 层的 `[None, False]`，而非 pandas 根的同名其它定义；8778 的 `idx` 仅由原 multi-index 测试请求并取 multi 层。

七题已有隐藏测试文件与来源原文摘要一致，没有删除或改写测试断言。6 道 pandas 的 56 个旧 ERROR 键只发生批准的支撑恢复：28 个原键改成 PASSED、28 个未展开键替换成 101 个参数键，共 129 个恢复后的回归键，在 noop 中也全部 PASSED。原有 11 个目标 F2P 键（noop FAILED、gold PASSED）及其状态完整保留。

| 题 | 原键数 → 当前键数 | 删 / 增 / 改状态 | 原目标 F2P 数 | 正式 noop / gold（各两次） |
| --- | --- | --- | --- | --- |
| pandas 19c5 | 155 → 162 | 6 / 13 / 11 | 1 | 161/162；162/162 |
| pandas 294c | 21 → 21 | 0 / 0 / 1 | 1 | 20/21；21/21 |
| pandas 32dd | 92 → 92 | 0 / 0 / 13 | 2 | 90/92；92/92 |
| pandas 7dd3 | 34 → 46 | 4 / 16 / 0 | 2 | 44/46；46/46 |
| pandas 8778 | 34 → 58 | 8 / 32 / 1 | 2 | 56/58；58/58 |
| pandas f656 | 323 → 353 | 10 / 40 / 2 | 3 | 350/353；353/353 |
| orange3 9b5494e2 | 13 → 13 | 0 / 0 / 2 | 2 | 11/13；13/13 |

表中分子为匹配 expected 的键数。orange3 gold 仍是 **11 PASSED + 2 FAILED**，因当前 expected 正确保留两个 scorer FAILED，匹配数为 13/13；不能把它表述为 13 个测试全 PASSED。orange3 本批只改 `test_LogisticRegression`、`test_coefficients` 两键 FAILED→PASSED，目标 `test_auto_solver`、`test_probability` 不变。两个 scorer 失败的具体原因未在本轮解决。

所有未改变状态的 expected 行及其相对顺序逐字不变。七题修复前后 skip/xfail 摘要相同，正式日志也与最终 dryrun 一致：19c5 有 9 skipped（缺 SciPy）+ 1 xfailed，294c 有 1 skipped，32dd 有 1 skipped（缺 SciPy），orange3 有 1 skipped，其余三题为零；没有用增加 skip/xfail 换取通过。

## 最终日志、材料及镜像绑定

- 32dd/7dd3 使用 `dryrun_b3r2`；其余 pandas 使用 `dryrun_b3`；orange3 使用 `dryrun_b3o`。未把 `drafts_first_try` 或第一轮残留 ERROR 结果作为最终证据。
- 每题修复后 noop、gold 各两次逐键及顺序一致；orange3 在已换 SciPy 的镜像上，原样私有材料的第三次也一致。每份最终 dryrun setup 文件摘要与当前评分面匹配。
- `replay_b5/ledger_b5_{noop,gold}.jsonl` 共 28 行：7 题各 noop 两次、gold 两次。每行日志 SHA256 可重建；从日志重算的键图、匹配数、总数与 reward 全部吻合；没有缺键、多键或未结束片段；cleanup 均完成。
- 正式日志的 `RH2_SETUP_HIDDEN_TESTS_TREE`、`RH2_SETUP_ENTRY_SHA256` 绑定当前评分面；账本实际 image ID、overlay image ID/ref、recipe ID/SHA256 绑定 `derived7/overlays.jsonl` 与逐题 facts；facts 的 hidden tree、HEAD 绑定当前评分面的 tree/base。候选均没有触碰测试支撑路径。
- 修订单 v3 保留 v2 七条的原 JSON 片段，新增 13 条仅涉及本批七题。pins v4 五个输入文件摘要全部匹配磁盘；公开面与验证面和 v2 归档逐字节相同；评分面、环境包恰好只改变这七题。

这证明**此次保存下来的运行确实使用配套材料和镜像**；不证明未来任意 overlay 都会被消费入口正确拒绝。主审单独核对的 orange3 旧镜像与新 expected 混配问题，应区分为运行时接线问题：纯静态审查可启动，但该题下一次候选 replay / actor 使用前应绑定 mr-020 与批准的环境配方并拒绝旧 overlay。无需为此重跑本次 28 行或在本子任务泛化环境契约。

## 全池计数

独立遍历 48 份 `screening_record.json`：`environment_qualified` 32、`qualified_with_recipe` 2、`qualified_with_revision` 10、`grading_ok_open_items` 4，没有 `needs_decision`。

独立解析当前 48 个 expected：11 题共 29 个非 PASSED 键；逐题完整键图在结果 JSON 的 `nonpassed_current_expected`。题数/键数为 aiohttp 240da100 2、4075c653 3；datalad 16c1ffc3 5、6b6fa389 1、9ba5de09 5；orange3 9b5494e2 2、f237f968 3；pillow 2b061b68 2、2d01f7d0 2；scrapy 9a15fcf8 2、a95a338e 2。

## 边界

本轮是保存证据的只读重建，未独立重跑真实环境；复跑次数只能支撑有限次确定性观察。未尝试判断任意正确替代解是否被隐藏测试接受，未把已登记的语义/评分质量问题升级成环境侧已解决。env_v2 的实现、运行入口对环境配方的约束，以及静态包导出的完整性分别由其它审查分工处理。
