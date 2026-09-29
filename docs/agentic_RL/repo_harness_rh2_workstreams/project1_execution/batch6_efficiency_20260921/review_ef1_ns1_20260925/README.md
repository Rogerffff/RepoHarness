# EF1 实现与 NS1 设计修订复核

2026-09-25，Codex。对象：`b50bdad126bb16bd18b05191e65830b120568a0d`；复核期间 HEAD 未变。仅检查上一轮 EF1 / NS1 及改动直接影响的评分聚合，不重开 #5、E1、E4、I18 或网络政策。

**结论：EF1 accepted / fixed；NS1 accepted / fixed in design。两项均可收口，没有新增阻塞项或 T0。E5 本轮无 GPU 部分可进入下一切片；网络可按已批 1A+2A 继续实现，实际联网运行仍待实现验收与作业配置。** 下文三项收敛内容登记到阶段 backlog，不要求先完成才能推进网络或 E2/E4。

## 1. EF1：真实入口到审计到报告通过

源码链已核对：`Rh2MilesGenerateFn.__call__` → `rh2_custom_generate` → `RolloutOrchestrator` 收口 → bringup 注入的 `_write_execution_audit` → `write_execution_audit_record` → `load_run_inputs` → `build_run_report`。旧 `record_event` 不再是评分摘要的必要路径。新块从已有 `finalized.grading_report` 派生，没有新状态 owner、后台任务、重试或训练拒绝。

[主审探针](probe_audit_grading.py)走真实 miles 类入口、prepared 题包读取 / 身份绑定、fa_formal 编排、finalize、审计 writer 和报告。复用既有测试夹具，替身限于模型 / capture 输入、Docker / harness、屏障 / drain、评分结果和 finalization store；eval 宿主能力探测用测试替身，不重验 fork 的派发盖章。五次执行都经正常审计出口，未手工给报告填评分块。

| 场景 | 本轮结果 |
| --- | --- |
| 训练 resolved | reward=1，计有效评分一次 |
| 训练 unresolved / tests_failed | reward=0，计可信零分一次 |
| 训练 failed_to_grade / infra_failure | reward=None，归 reward_unknown，不进入有效评分 |
| 训练 materialize 失败 | 无 grading 块，报告覆盖量 3/4 并给 partial reason |
| eval resolved | 带独立 evaluation 块，不进入训练评分统计 |
| 同一逻辑成员的不同 physical attempt | 分别计数，不因 trajectory_id 相同而误折叠 |
| 同一 physical attempt 的重复审计行 | 评分数和耗时不重复，duplicate 计数增加 |
| 只有 shutdown 生命周期行 | 有效评分、评分总体、评分分段耗时均为未知 |
| audit 与旧 bringup 评分同时存在 | audit 优先，不叠加；纯旧记录的回退仍可读 |

[结果 JSON](probe_audit_grading.json)：`all_required_checks_pass=true`。训练有效评分 total=2（成功 1 + 可信零分 1）；3 个训练评分块的测试时长各为输入的 4 秒，聚合 count=3、sum=12，eval 和重复行均不混入。分母为人工构造的一小时、卡数为配置夹具 8：用于验证算术，不是 GPU 吞吐实测。

作者新增维护测试使用 s1_compat 的 dense 编排夹具；它能证明 writer 运输，但本轮额外走 fa_formal 与真实 miles 包装，补足入口证据。旧“audit 本身没有评分”的测试 oracle 翻转有生产代码依据，不是修改预期掩盖失败。

## 2. NS1：设计已经补齐，不把设计通过当作联网验收

[网络 Brief §4.2 / §4.5](../network_supply_brief_20260924.md)已明确：测试 exec 恢复来源 renderer 的前导，包含 `set -xo pipefail`，随后按候选 UID 恢复 exported 变量 / 函数、用 `cd` 恢复 cwd；状态目录先建。保留原始标记依赖 xtrace 的事实，不加入曾使 pandas 激活失败的 `set -u`。

“安装命令非零但 shell 继续 / shell 提前退出 / 状态写入失败”已分开记录，沿用 P-A；携带状态不充当可信完成证明。撤网确认仍由宿主完成，失败 / 取消 / 期限到点不得启动测试 exec。共享预算与候选 UID 边界没有被改写。

三形态 renderer / parser 对照和 R2E 无安装段正控已进入实现验收清单；旧 root 放行文件、单 shell 交接实现描述已替换。§1 描述当前单 shell 现状、历史复核段引用旧反例，属于背景，不要求把历史事实删掉。E2 的过时“等 T0”开工条件亦已删除。

本轮不重复运行未改动的 Bash 反例，不宣称已跑 R2E 分段或 Docker 撤网新实现。沿前轮证据和本轮修订，NS1 的设计停止条件已满足。**无需重新请求实现授权。**

## 3. 非阻塞收敛项

### OBS-1 / P2：旧交付统计仍把生命周期行当交付

位置：[run_report.py](../../../../../../rh2/src/repoharness2/adapters/miles/run_report.py) 508–542。`by_session` 仍把没有 session_id 的 shutdown 行归到 `None`，再参与 `delivery_records`、`delivered_without_grading_record` 与 eligibility 分布。主审在真实审计输出旁加入两条 shutdown 行，得到 `delivery_records=1`、`delivered_without_grading_record=1`、`eligibility_classes={"None":1}`；评分总数仍正确为 2。证据在 JSON 的 `with_lifecycle_delivery_fields`。

可达性：`production_reachable`，正式 miles 路径写 audit，收尾写 shutdown，但不写旧交付事件。影响是这几个旧交付字段仍不可信，**不是 EF1 的评分速率再次变零**；根因在本批前已存在。

处置：A 线观测收敛 backlog；使用这些交付 / eligibility 字段解释损耗前修。只把真实交付形态纳入旧集合，无交付观测则标未知；不要为此把旧包装硬接回 miles 或增建一套 logger。验收：只有生命周期行时交付字段未知，真实旧交付正控不变，评分数不受影响。按审查标准 §10.5 的停止条件，不阻塞本片或网络实施。

### COMPAT-1 / P3：同一 run 混入新旧审计行时覆盖量会少算旧行

位置：同文件 975–998。存在新 writer 行后，覆盖量只从带 `grading` 键的行计算。人为组合一条新成功记录和另一 attempt 的旧无键记录，显示 1/1，而非“观测 1、旧记录未知 1”；见 JSON 的 `mixed_writer_fixture_only`。

可达性：`conditional_future`，要求同一 run 的输入混入不同 writer 版本；没有当前运行实测。全新 writer 行（包括 `grading=None`）、纯旧记录、不同 run 的拆分不受此例影响。A 线在需要支持这种历史合并时处理：覆盖分母从全部相关 attempt 算，评分来源仍优先 audit；或明确给混版本输入 partial，避免逐字段复杂回填。现在登记，不新增运行闸门，也不改写历史证据。

### 纯清理

`run_report.py` 模块头与 `CALIBER_NOTES` 仍写“audit 不含评分 / 无 bringup 无法知道评分”，应随下次编辑同步；这段旧文字现在也会出现在报告中。`_classify_gradings`（1045 起）已无调用，可删，避免与新的 `_classify_records` 重复维护。无需为这些文案 / 死函数追加新测试平台。

## 4. 验证与停止条件

维护测试在 `rh2/`、集成 fork 环境运行：

```sh
RH2_MILES_PATH=../reference/miles-rh2-integration .venv/bin/pytest -q \
  tests/adapters_miles/test_e5_run_report.py \
  tests/adapters_miles/test_run_report.py \
  tests/adapters_miles/test_i21_eval_run_report.py \
  tests/adapters_miles/test_run_report_real_emitters.py
```

**33 passed**。上面的正式入口运输探针另行通过；相关改动与探针的 ruff E9/F、提交 diff whitespace 检查通过。未重跑全库、双 lane 总数、G1 / CPU 算术探针（本轮没有改对应实现）、Docker、远端或 GPU。

A / D / E / F / G / H / M / N 的证据见各节；B/C：仅观测摘要与离线聚合、NS1 仅设计文档，本轮未改变 reward / mask / 准入或 P12。J/K 的死代码与兼容简化见 §3。L：复用现有同步 audit writer，只多序列化评分摘要；排序 / 去重在离线报告，无新增热路径等待或长期状态；未测吞吐。I：EF1 / NS1 收口，OBS-1 / COMPAT-1 明确分期。本轮是同步摘要与纯聚合的修复复核，未引入新的高风险所有权边界，不重新启动双 subagent 或整链审计。

无新 T0 或临时挡板。E5 本轮无 GPU 内容收口，真实效能与路由仍留 F1–F8 / I18；网络可按 Brief 实施，E2/E4 按共享文件交接推进。只新增审查工件并追加相关状态指针，未改生产 / 测试 oracle / B 在制品，未提交、push、登录机器、发消息或启用网络。
