# 独立证据核验（2026-09-24）

本分工的结论：**真实评分证据账目成立，没有发现新的漏题、错绑身份、日志哈希不符或逐键对账异常。**这支持保留 R-f 与本轮中央复跑结果；它不单独证明“完整开发环境已修好”，也不取代主审对环境资格范围、开发探针有效性和材料提案的判断。

核验只读原始材料与证据，新增产物仅在本目录；未修改生产代码、作者记录或原始日志，未用远端、未起容器。按根 AGENTS 与 review-standards 的独立上下文要求执行。用固定 SHA 的 vendor 源码 AST 提取四个函数，独立重建 expected/observed 映射与并集判分；未导入或运行被审 `collate_facts.py` / `reconcile_r2e.py` / 开发探针解析器作 oracle。

复现（仓库根）：

```bash
python3 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_review_20260924/evidence_agent/audit_evidence.py
```

输出 [summary.json](summary.json) 的 `issues=[]`；其 `observations` 保留下面的条件差异与文档更正，**不表示作者全部总结无误**。

| 核验对象 | 独立结果 |
| --- | --- |
| 输入 / 摄入 | 四项输入 pin 与四份 ingest 文件 SHA/count 正确；48 个唯一任务，raw expected 与 grading expected 相同 |
| 真评分账本 | 本轮 98 条（中央 96 + numpy 配方 2）与 R-f 对应 98 条，合计 196 条；无漏题、额外题、重复 report ID、日志引用或 run/task/attempt |
| 日志、sidecar、身份 | 196 条日志 SHA 正确；sidecar 与账本一致；test segment 完整、无 stage_error、清理成功；overlay/image ID、base manifest、隐藏测试树、入口脚本、来源 gold patch 均正确绑定 |
| 默认 profile 结果 | 两轮均 noop 48 个 0、gold 45 个 1 / 3 个 0；中央与 R-f **96/96 完整状态映射相同**，不只是 reward 或差异集合相同 |
| 独立参考 | 336 份参考日志直接解析；M3 gold / 09-09 v3 账本 240 行哈希与 reward 重核通过；两轮均 **94/96 行 = 47/48 题**逐键一致 |
| 唯一参考差异 | numpy `2f4a9650` 默认 profile 的 `TestSavezLoad.test_big_arrays`，noop/gold 都是 RH2 FAILED、参考 PASSED；无新差异 |
| numpy 资源配方 | 09-23 / 09-24 共四行在 6 GiB `/tmp` + 12 GiB memory 下与参考逐键一致；noop 141/142、gold 142/142，镜像与脚本相同。最小配置仍未测试 |
| 回传 / 引用 | 中央 204 份文件与 `remote_envrepair_final/_rerun2` 字节相同；local 账本仅改两个路径字段；两路 driver 均 48 行、exit 0、无残留句柄或 cleanup failures。3406 条记录引用可解析，含两条通用引用人工消歧 |
| 48 题探针 | 原始 KEY/value 与当前主包 JSON 完全相符；48/48 十项最小条件成立，uid=54321、HEAD / image ID 与材料一致；公开复现标记 46/48、无 pip 27/48。这里核的是证据一致性，不扩张十条件的证明范围 |
| 8 题抽验 | 原始关键字段、git status、十项最小条件 8/8 一致；执行容器和开始时间与主包不同。保存的 `derived` 仅 3/8 完全相同，另外 5 份仅旧 `pip_ok` 不同；独立按原始 pip 输出纠正后 8/8 完全相同 |
| 资格统计 | 48 份记录重算确为 **42 environment_qualified + 1 qualified_with_recipe + 2 held_material + 3 needs_decision**；43 份 qualified 记录满足作者列明的 R01/R02/R08/R13/R15 与最小条件。此计数不能自行解决主审发现的资格定义问题 |

R01、R02、R13、R15 的语义边界：

- **R01**：48 题真实证据的镜像、基线 HEAD、树摘要和评分入口均一致。未发现身份串题。
- **R02**：48 题确有非空 mismatch、无 missing、非零解析；每题 noop→gold 都至少有一键恢复。coveragepy `016af5f6`、datalad `58ba5165`、numpy `2f4a9650` 的 noop 还同时含材料/资源差异，不能把“所有 mismatch 都来自题面目标”当自动结果。目标与题面的对应仍靠 R16 人工判断。
- **R13**：原始完整映射的 96/96 重复由本次独立核验补强。两轮 timeout budgets 并不相同：candidate/grading 为 R-f `1800/1800` 秒、中央 `900/3600` 秒；资源 policy、镜像、candidate 和 scripts digest 相同。所有执行完整，最大 phases 总和分别约 195/243 秒，因此不推翻本轮同资源 profile 的重复结论；也不证明时序行为永远确定。
- **R15**：94/96 的含义是 47 题 noop/gold 各自与全部对应参考映射相同；numpy 一题默认资源例外，配方四行补齐。没有用相同 reward 替代逐键对账。

本轮文档收口建议（均为 P2 证据表述更正，离线即可，不需新增真机 gate）：

| 当前行为 / 证据位置 | 影响与验收条件 |
| --- | --- |
| `r2e_env_repair_20260924/README.md:23,38,127`、`known_issues.json:158` 写非 PASSED 为 16 题；原始 expected 与当前 facts 都是 **20 题、34 FAILED + 59 ERROR = 93 键** | 是汇总错误，未发现摄入变化。20/20 R06 均有原因说明和证据引用，没有额外四题漏审；收口把总数改正，保持逐题列表不变 |
| `README.md:38` 写“对账 46 题 agree”，与同页 94/96 不符 | 改为 47 题；numpy 是唯一不一致题。可用本目录 `rows.json` 逐题重算 |
| `acceptance_20260924.md:10,28,42` 仍称 `derived` 全同；五份 `_accept` 是 v2，主包是 v3 | v2 把 `No module named pip` 判为 true。numpy 示例：`_accept/p2/dev_probe/numpy__d89…/dev_probe.json:114` 为 true、主包 `p2/dev_probe/numpy__d89…/dev_probe.json:113` 为 false。保留原始日志，用新版本另存重解析结果或在验收说明中明确这一个字段；不要改写历史原始证据。修正后需 8/8 derived 相同 |
| 总结称“全部归因”；orange3 `9b5494e2/screening_record.json:64` 明写两个 scorer 失败的依赖原因属推断、未单独验证 | 汇总应保留这一不确定性，不改成已实验证实。其余原因有逐题记录；不因这两个推断追加本轮真机阻塞 |

分期与停止条件：中央复跑、资源复验和参考逐键对账已足够收口，**本分工没有新 P0/P1，也没有需要租机或保留机器才能回答的问题**。更正上述摘要、保留 budget 差异及原始日志即可停止证据补跑；正式开发条件/资格是否收口、材料是否修订由主审结合其它分工裁定。本分工不重开历史 R-f 阴影，也不把参考一致性当训练准入。

产物：[rows.json](rows.json) 为 196 条独立映射与参考差异，[repeats.json](repeats.json) 为两轮 98 对比较，[record_checks.json](record_checks.json) 保留 20 题 R06 原文，[probe_checks.json](probe_checks.json) 与 [acceptance_checks.json](acceptance_checks.json) 为探针对照，[file_hashes.json](file_hashes.json) 固定本次读取文件。
