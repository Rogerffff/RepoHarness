# R2E T0-1 / T0-2 与 numpy 环境修复：聚焦复核

2026-09-24，Codex A 主审；独立消费链复核与独立证据复核各一份。范围：Claude 本轮摄入修订、派生配方、三题真实评分、资格口径更正及新增工具行为。此前 [R2E 环境轮审查](../r2e_env_review_20260924/README.md) 的历史结论保留，本页记录本轮核销。

**结论：三题修复和资格范围更正通过本轮限定验收，没有发现新的评分主链 P0/P1。留下两个不要求重跑机器的工具 P2：历史账本被套用当前材料版本；对账测试污染后续测试的导入路径。** 后者已用修订前归档代码证明存在，不是 T0-1/2 判分修订造成的回归。另有少量旧说明未同步。

本轮仅写审查工件与当前状态指针；未改生产、测试、材料、原始证据，未提交。远端只读核验，没有新建容器、改 A 线文件或清理机器。T0-1/2 的已有批准不重新请示；T0-3…7 继续未定。

## 1. 修复结果与核销

| 对象 | 独立核验 | 裁定 |
| --- | --- | --- |
| coveragepy `016af5f6` | expected 仅一键 FAILED→PASSED，15 键不增删；真实 noop 两次均 0、14/15，gold 两次均 1、15/15；完整观测映射与 M3 相同 | T0-1 A 实施通过；参考账本自身仍须按来源版 expected 解释 |
| datalad `58ba5165` | 私有 `test_1.py` 仅改一行导入，expected 不变；两次 noop 均 0、2/4，两次 gold 均 1、4/4；修订全文、树摘要、派生镜像与 grader 使用的材料匹配 | T0-2 B1 实施通过。修订版没有同版本独立 runner；现有真实 grader 与早前 B1 dry-run 的一致性不能称为这一独立参考已补齐 |
| numpy `43e333e2` | 镜像 hypothesis=6.24.1，pytest 保留8.3.4；agent 身份相关模块可收集，TestAverage 6 passed；两次 noop 均 0、87/88，两次 gold 均 1、88/88，与配方前及独立参考映射相同 | 本题相关开发阻断已修。其余 TestCov/TestCorrcoef 的10个失败仍存在，已查为旧 setup 兼容问题；本轮不要求为此更换 grader 的 pytest 大版本 |
| 上轮 R1 资格问题 | 48份处置重计为 **33合格＋2带配方＋2带材料修订＋8有未完成项＋3待决定**；`apply_r13` 三案确认无目标不提升、有 open_items 不提升、明确目标且无 open_items 才改变状态 | 自动兜底提升已删除，资格范围更正接受。37题的分层环境结论仍不等于37道正式训练题 |
| 上轮 R2/R3 主要事实 | 最新决定表已区分 orange3 的已证异常和推断、scrapy 的不同失败位置、pandas 的静态可达路径与实测；来源20题93个非PASSED键，coverage修订后为19题92键 | 主要更正完成；§4列残余旧说明，不再阻塞这三道修复 |

12行日志、sidecar、候选gold、镜像ID、隐藏树、入口摘要全部互核。每题相同候选的两次结果完整映射相同，不只最终reward相同。独立证据审直接使用固定vendor规则重建映射，没有以作者的 `reconcile_r2e.py` 作唯一oracle。

## 2. 新修订契约与实际消费

实现选择合理：修订在摄入时落实，通过既有 prepared 私有面传到 grader；没有新增运行时忽略键、候选覆盖策略或审批平台。`material_revisions` 表达已批准材料的来历，不改变逐键相等评分规则，无需把这个字段再拆成一次重复 T0。

```text
代码 pins v2 → 五项受信输入 → 原文重放修订 → grading bundle / package digest
  → TrustedTaskController → prepare_tasks / 私有 host_grading_views
  → PreparedTaskFace / build_r2e_grading_spec → parser 闭包 → report

同一受信修订单 → 派生构建 material_v1 → 私有测试树
  → overlay → ReplayGrader → manager root setup 校验 → candidate uid 测试
```

全部48题经真实 prepare/load/分派入口回放；本批归档 prepared 与当前受信输入新生成的私有文件逐字节相同。两项材料修订之外，**46题评分内容不变**；numpy 另有镜像配方改变，扣除它就是用户所述的其余45题。48题公开面与gold文件逐字节不变，修订编号、期望映射未进入solver payload。SWE216题四面及manifest重序列化字节不变，缺省来源仍只有SWE。

需保留一个迁移口径：新增 `material_revisions: []` 参与规范序列化，所以 **48个R2E评分摘要、继而48个package摘要都改变了**。这是元数据改变，不是46题内容被修改；旧prepared不能当作新版本直接混用。本轮已存来源产物及运行输入，历史版本的解释应保留对应快照。

真实消费拒绝探针确认：缺修订单、旧package摘要、旧datalad隐藏树会被识别；旧树覆盖表在driver阶段即停止且没有Docker调用。另四例以真实ReplayGrader和manager、Docker替身注入真实日志，证明新bundle确实传到真实parser；这些CPU探针不冒充新的真容器执行。

详见 [消费链与不变量矩阵](transport_agent/README.md)、[独立证据复核](evidence_agent/README.md)。本轮未新增线程、队列或恢复owner，不重审既有关停链；crash/cancel/timeout等既有边界不因材料版本变化重复注入。正式actor后续接入按A线最新记录推进，本次不是其总验收。

## 3. 两个工具收尾项

### F1 / P2：历史账本的材料版本取错，误报旧结果或改变统计分母

**位置：** `rh2/scripts/reconcile_r2e.py:159–173` 从当前trusted池取bundle与revisions，再直接给每条输入账本填 `material_revisions` / `hidden_tests_revised`，没有选择或核对该批实际材料版本。

**真实反例：** 将R-f原始三题noop/gold六行交给当前CLI，日志均在场且无改动：

- 旧coverage gold本来按来源expected得0、与来源runner一致；工具给它贴 `r2e-mr-001`，按新expected把参考重算为1，得到 `agree=false`。
- 旧datalad两行从未用过修订测试；工具仍贴 `r2e-mr-002`、`hidden_tests_revised=true`，将其排除在一致总数之外。
- 源账本的SHA、报告和日志没有错，是解释版本错了。M3账本倒放回来源expected的本轮修法本身正确，但只处理了参考一侧。

**影响和分期：** `production_observed` 指离线对账CLI实测，**不指训练评分错误**。本批新12行已由归档prepared绑定独立验证，结论不受影响。之后重算旧批或合并新旧批之前修；无需重跑评分。

**最小建议：** 使用与输入批次对应的材料快照，或要求用户显式选择来源版/修订版并检查一致性。无法确定时标明“版本未匹配”，不要自动赋当前修订、写分歧或改变分母。无需自动多版本数据库，也无需把全部私有材料复制进每一条训练样本。

**验收：** 来源版六行恢复原有一致性且datalad不被错误排除；本批新12行仍为8条可对账一致＋4条隐藏测试修订单列；混版不能无提示套用一种版本。探针及逐行输出：[probe_tool_boundaries.py](probe_tool_boundaries.py)、[tool_boundaries.json](tool_boundaries.json)；完整CLI工件在 `runs/r2e_t0_review_20260924/current_tool_old_ledger/`。

### F2 / P2：顺序失败有确定根因，测试fixture未恢复脚本导入副作用

**位置：** `rh2/tests/envpack/test_reconcile_r2e.py:17–22` 的module fixture动态加载CLI；`rh2/scripts/reconcile_r2e.py:27` 将 `rh2/src` 插到 `sys.path` 首位。fixture没有恢复路径，后续需要 `reference/slime` 的六个差分测试误取vendored slime，于是缺 `slime.utils.dp_schedule` / `slime.rollout`。

**本机反例和修法验证：**

| 运行 | 结果 |
| --- | --- |
| 差分文件单独 | 6 passed |
| 对账文件后接差分文件 | 5 passed / 6 failed |
| 排除本轮两个修订用例再连跑 | 3 passed / 6 failed |
| 用R-f归档中的原脚本与原测试连跑 | 2 passed / 6 failed；证明问题早于本轮材料修订 |
| 只用临时pytest插件在fixture结束恢复原sys.path | **11 passed**；未修改生产或维护测试 |

**裁定：** Claude“不是本轮材料修订引入”的判断成立，但仅凭单独通过不足以证明。本次已补原因与历史对照。这是 `test_only` 的工具卫生问题，不是训练接线P1，也不应通过skip/改oracle消除。

**最小建议：** 对账测试fixture保存并恢复自己触发的导入路径副作用；本探针证明这一窄修足够。验收即上述两个真实文件连跑11过。旧基线已坏可作为非阻塞维护项，但现在修复成本很小，适合一起收尾。复现：从 `rh2/` 跑 `.venv/bin/pytest -q tests/envpack/test_reconcile_r2e.py tests/contract_slime_async/test_dp_schedule_differential.py`。

## 4. 文案与证据剩余边界

- `dispositions.json` 的旧scope仍有“未修改摄入面”，scrapy `cfed9b66` 的旧reason仍写三个“死键”；`known_issues.json:159` 总族摘要仍留16题等旧说法，应跟最新决定表一致。pandas `4ec87eb9` 的旧 `state_if_r13_passes` 可以清理，但目前 `open_items` 会阻止误提升，**不是新运行时回归**。
- numpy 的完整开发探针有镜像ID/uid记录；TestAverage额外摘要只保存版本与结果，身份来自同时保存的执行脚本，不具有grader账本那样完整的独立身份字段。相关测试恢复可运行的判断有证据，但不把六个base用例通过当作业务bug已修复。
- datalad缺少修订版独立runner已经明确披露，本轮真实grader与材料内容核对足以接受窄修，不为补这个标签再要求复制一轮评分实现。后续有同版本独立对照再补。
- 旧 `facts.json` 保持来源版、本次修订证据写进record的安排可接受；不能把两种材料混作R13重复。工具再生成/聚合时应保留这一版本边界，F1是其中已经实测有问题的一处。
- 旧R-f结论继续适用于来源版。本轮不把已批准的expected修订反写进旧成绩，不把37道环境候选等同正式训练准入，不替用户决定T0-3…7。

## 5. 验证范围、远端与停止条件

主审本机：摄入、parser、R2E语义、渲染、对账相关维护测试 **85 passed**；消费链子审另跑8项定向测试（与85项部分重叠，不相加）。主审有三案资格工具探针、历史六行CLI、上述顺序反例及窄修验证；相关代码/脚本ruff通过。未声称独立重跑作者1536项全套或39项Docker测试。

新机器只读核验：B线408项快照摘要全符，无运行中容器；抽查8个关键文件，7个与当前本机相同，仅对账脚本是本地最后一次修正之前的版本。它不参与已完成的grader判分；该差别不推翻12行真实评分。本轮未新运行grader、未改/停止实例、未删镜像或B工作目录。摘要见 [remote_snapshot.json](remote_snapshot.json)，不在提交文档记录机器地址/密钥。

**停止条件：** 三题修复和本轮资格更正可以收口，继续其余环境/材料工作；没有需要继续占机才能回答的本轮疑点。F1在下一次历史重算前修，F2可一并本机收尾，只需针对性复核，无需再安排48题真机或全套RL测试。后续新实验只针对实际选定的T0材料修订。

本轮维度：A/D/E/F/G/H/N覆盖受信输入、混版拒绝、真实消费与归档绑定；B仅批准两题奖励材料变化；C/I不增审批与正式训练闸门；J/K检查修订是否扩为运行时平台；L新增成本在离线摄入/镜像构建，无每token热路径；M由F1与文案版本边界处理。发现均落在现有维度，不需新增审查机制。
