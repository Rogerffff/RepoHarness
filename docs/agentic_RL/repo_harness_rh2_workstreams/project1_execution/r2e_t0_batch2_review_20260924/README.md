# R2E 第二批材料修订与环境诊断复核（2026-09-24）

**结论：T0-5、T0-6 代表题及其 v2 材料运输通过本次限定验收，未发现新的评分主链 P0/P1。** 两题真实评分记录成立，期望修改没有放宽测试断言，另 46 题评分材料不变。还有两处 P2 收尾：两个 CLI 测试仍污染导入路径；静态筛查的源码导出建议须补上镜像内的初始源码改动。它们不要求重跑本批真机评分，也不阻止继续修另外六道 pandas。

审查对象为 HEAD `145cb5fd` 上的未提交工作树，关键输入指纹见 [reviewed_inputs.json](main/reviewed_inputs.json)。主审加两个独立上下文复核；主审独立复跑摄入/运输探针、对账 CLI 与失败最小组合，未修改实现、维护测试、材料或原始 evidence，未访问远端、启动容器、提交或处理机器。

## 1. 两题修复实际恢复了什么

| 对象 | 独立核对 | 裁定 |
| --- | --- | --- |
| pandas `4ec87eb9` | 私有 conftest 的两个 fixture 与 base 原文一致；原隐藏测试断言不变。期望恰好删 2 个未展开的 ERROR 键、增 13 个参数化键，其余键不变。正式 noop 两次均 233/237、gold 两次均 237/237，日志摘要、逐键结果和试跑相符 | 通过。原材料已有全 NA 列的两条 F2P；这次补充恢复了题面 `[2.5, pd.NA]` 的部分 NA 场景，两条 Float 扩展 dtype 用例从 noop FAILED 变 gold PASSED。不能把 13 个展开键都叫新增 F2P；其中整数 fixture 的用例输入没有 NA，是回归检查 |
| scrapy `cfed9b66` | `test.egg` 与捕获的 base 文件相同；两处替换只把旧 `tests.test_middleware` 自引用转到真正执行的 `r2e_tests.test_2`。期望只改 3 个状态，无增删键。正式 noop 两次均 7/9、gold 两次均 9/9；egg-only/path-only 对照解释了各自影响 | 通过。修复后 `test_instances_from_settings` 在 noop 失败、gold 通过，与原有 `test_load_object` 共同区分题面的两部分行为 |
| v2 修订单 → 构建 → grader | 从原始 48 行重摄入与现产物逐字节相同；对上一版归档，只有这两题 grading/package 行变化，public/gold 全 48 题不变。两题修订单、材料树、配方、镜像、prepared 评分面、脚本和 8 条 grader 记录绑定一致；新增文件进入既有可信恢复与保护清单 | 通过。未声明的 expected 新键即使重算 SHA 仍被拒；新增隐藏文件指向已有文件也被拒。没有新增运行时 owner 或队列 |

依据为 [运输审查](transport/README.md)、[语义及原始证据审查](evidence/reward_evidence_review.md)。本次重新解析的是已回传的真实运行记录，**没有新运行这些容器**。两题修改过隐藏测试，仍缺相同修订版本的独立 runner；现有证据是原断言/支撑来源核验、一次性容器对照与真实 RH2 重复评分，不冒称独立来源复现。

orange3 的 7 份诊断日志支持有限结论：SciPy 1.4.1 和 1.5.4 都恢复 `test_LogisticRegression`、`test_coefficients`；两个 scorer 键仍失败。原版及修后 noop/gold 的其余差异吻合，没有把未知的两个 scorer 一并判为已修复。

48 份记录重新计数与结果表一致：**32 环境侧通过、2 带配方、4 带材料修订、10 可判分但有未完成项**。这不等于正式入池或静态质量合格。

## 2. 仍需收尾的两项

### F1 / P2：另外两个 CLI 测试仍未恢复 `sys.path`

- **可达性：`test_only`。** `tests/adapters/test_replay_grade.py:565–567` 与 `tests/adapters/test_r2e_replay_overlay.py:229–231` 在测试函数中执行 `scripts/replay_grade.py`。该脚本第 28 行把 `rh2/src` 放到路径最前，两个测试结束都没有还原。
- **违反的不变量：** 一个测试对导入环境的改变不能决定另一个目录测的是 reference slime 还是 vendor slime。miles fixture 正确清理模块后，后续差分测试按被污染的路径选到 vendor；vendor 有意没有 `dp_schedule`、`slime.rollout`，因而出现六个 `ModuleNotFoundError`。
- **实际复现：** 按作者三目录命令得到 **6 failed / 1208 passed / 343 skipped / 22 deselected**。每个 CLI 用例单独接一个 miles 用例、再接六个差分测试，均为 **6 failed / 2 passed**。不需要两个大目录才能触发。
- **归属与影响：** 上轮两个 envpack fixture 的修复正确，14 项组合已通过；新定位的漏点属于已有 R0/R2E 接线测试，不能把剩余失败全部归给其他线。本项不说明真实 grader 有错，但不能据此声称组合测试已全绿。
- **最小修法：** 对这两处动态导入保存/恢复路径，可沿用已修的 fixture 方式。无需改生产脚本的 CLI 启动规则、放宽差分测试、删测试或改 marker。
- **验收与分期：** B 线测试收尾，本机即可。主审只在探针中恢复两个 CLI 用例的路径，原测试主体不动，得到 **9 passed**；将同等隔离写回维护测试，再复跑下面组合。日志在 `runs/r2e_t0_batch2_review_20260924/{minimal_r0,minimal_cr1,minimal_restore_paths,combined_tests}.txt`，路径变化见 [记录](main/test_paths_restored.json)。

```sh
# 从 rh2/：最小复现；修后应全部通过
.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/adapters/test_replay_grade.py::test_r0_cli_converts_grader_scope_termination_into_a_halt_exit_code \
  tests/adapters/test_r2e_replay_overlay.py::test_cr1_cli_summary_records_the_abort_and_still_reports_cleanup \
  tests/adapters_miles/test_f1_turn_identity.py::test_export_spans_clean_two_turns_with_tool_gap \
  tests/contract_slime_async/test_dp_schedule_differential.py
```

临时验证脚本为 [probe_test_paths.py](main/probe_test_paths.py)，传 `--restore-paths` 后接上述 pytest 参数即可。它只是证明修复范围，不是已改好维护测试。

### F2 / P2：按 base 提交导出的源码不能仅靠 HEAD 与抽查认定等于镜像

- **可达性：`conditional_future`，静态筛查材料打包时。** [准备页 §5](../r2e_env_repair_20260924/static_screening_prep.md)第 61、65 行把公开包定义为精确 base 全部跟踪文件，却建议克隆 base 后按 HEAD 和已拉镜像抽查。这两种核对粒度不一致。
- **既有反例：** M3 事实表已记录 **12/48 初始脏树**，aiohttp 5 题、pandas 7 题。pandas `4ec87eb9` 的镜像删除了 `pyproject.toml`，并改动 `pandas/__init__.py`、`pandas/_version.py`、`setup.cfg`、`versioneer.py`；这些改动没有改变 HEAD。单纯 checkout 会把它们全部还原。见 [12 题事实摘要](main/dirty_base_facts.json)。
- **影响：** 审查者看到的安装、导入和构建条件与 solver 真实看到的不一致，可能误判环境问题或提出无法在原环境使用的建议。这是下一步计划缺口，不影响本批已运行的评分。
- **最小修法与分期：** 克隆 8 个仓库仍可作为节省下载的底稿，但对已知脏树必须叠加镜像初态的修改/删除，再核相应文件；没有可还原的完整差异时只补取这些镜像中的必要文件。无需因本项默认重拉 48 张镜像，也不要求新建版本管理平台。
- **验收：** 静态筛查负责人在发公开包前明确“上游提交树”和“实际解题工作树”的区别，pandas 示例中的删除与四个修改应被保留；仅核 HEAD 不能作为通过证据。历史 findings、gold 与隐藏测试继续只给私有审查者。

## 3. 上轮问题与本轮验证范围

| 检查 | 本轮结果 |
| --- | --- |
| 旧 F1：最新材料套到旧账本 | **关闭本轮既有反例。** 真 CLI 重跑历史 6 行为 6/6；datalad 旧行不再错误单列。新旧 32 行中 20/20 一致，12 行为隐藏测试修订而单列，版本未匹配 0、M3 自相矛盾 0。见 [探针](main/probe_reconcile.py)、[结果](main/reconcile_summary.json) |
| 旧 F2：对账/构建 fixture 导入污染 | 两个被点名 fixture 的组合 **14 passed**。同类漏点 F1 尚待修复，不把局部通过当全目录通过 |
| 两类新材料机制 | 独立子审 **13 个定向维护测试通过**；主审复跑运输探针，48 题字节比较、8 行证据绑定和两类失败注入通过 |
| 语义证据 | 8 正式行、16 次两题 dryrun、7 次 orange3 诊断及 48 状态记录离线核对；没有重跑远端或 Docker |
| 作者声称的全量与 Docker 数字 | 1558/2、Docker 39、lane A 463/343 属作者验证，本轮不重复这些全量作业；本轮自行跑的组合结果在上表及 F1 明列 |

生产调用与所有权详见运输子审：封板输入 → 受信摄入 → 派生镜像 root 私有树 → overlay → prepared 评分面 → 每次独立 grader 的可信恢复/权限布置 → uid 54322 测试 → 来源 parser/评分报告。没有改变训练 loss、group membership 或异步生命周期；现有正式 actor 和真实 CC 行为不属于本轮验收。

A/D/F/G/H/N 核对了来源、身份、私有材料和真实消费者；B 核对了奖励变化只限已批两题、没有删断言；E 发现 F1 并用真实维护测试隔离；C/I 无新增挡板、重复全池或新授权要求；J/K 新增两种材料修订复用现有入口，未见本批需进一步抽象的具体问题；L 本批离线材料处理无新队列/并发状态，性能未重测；M 对账版本未知与隐藏测试修订均单列。crash/cancel/timeout/retry/restart/日志落盘/queue full 的运行期行为本批未改，沿用既有接线审查，不为本轮材料重造故障演示。

## 4. 后续建议与停止条件

1. **建议允许继续其余六道 pandas 的 fixture 修复。** 本题已经证明“恢复原支撑、保留原断言”可行；逐题从对应 base 提取实际依赖的最小 fixture，解释展开键变化，再只复验受影响题。不能仅把新 gold 输出整份接受为正确期望，也不要求每个恢复键都必须是 F2P；P2P 回归检查同样有价值。
2. **orange3 可以批准已经定位的两键局部修复，两个 scorer 保持未完成项。** SciPy 1.5.4 是已测试的候选配方；正式镜像及新期望尚未实施/验收。也可先随质量筛查一起处理，此项不阻止别题推进。两种选择都不能写“本题全部环境问题已解决”。
3. **收窄一处证据措辞即可。** acceptance 第 129 行、decisions E17 和 orange3 提案里的“换版 gold 未收敛，说明来源环境每次必经错误分支”，应改成“本批有限次 gold 警告复跑出现未收敛，两个恢复键的兼容修复得到验证”。这既不证明所有正确候选都必经，也不解释另两个 scorer；不为这句话另加重复实验。
4. **静态筛查可并行准备。** 先补 F2 的源码口径，复用现有环境事实和公开/私有分离流程；环境侧的 32/2/4/10 状态不直接转成训练题单。

本批无需再跑这两题或重做 48 题。F1 修维护测试、F2 修下一步打包说明即可收尾；未来若产生新的材料、环境或判断分歧，再对相应题定点验证。机器保留、终止及共享机器清理由用户或已有授权执行者处理，本轮没有操作。
