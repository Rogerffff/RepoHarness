# 数据集文档精简与归档方案

整理：2026-10-04。目的：让后续agent从一个当前入口找到本题状态，而不是重读全部历史。**已建立264题入口；物理搬迁仅列候选，本轮未执行。** 此方案不涉及删除实验原件、代码、环境材料或停止其他活跃工作。

## 默认保留什么

| 阅读层 | 保留文件 | 用法 |
| --- | --- | --- |
| 当前入口 | [README.md](README.md) | 默认首先读；只说明264题范围、现状、限制和下一步。 |
| 逐题状态 | [tasks.json](tasks.json) | 只提取负责题目的行；这是带日期的汇总，原负责人仍维护源账。 |
| 人的查询页 | [index.html](index.html) | 与同一份数据生成，支持搜索和分组；不是另一套人工维护状态。 |
| 规则 | [筛查规则v1](../task_screening_standard_v1_20260925.md)、[开发验收协议](../actor_development_validation.md) | 执行相应动作时读对应章节；不先通读草案和所有审查史。 |
| 当前协作与材料 | 52题源总账、更新工具说明、协调规则、发布／部署回执与有效材料索引 | 执行需要时按题读；这些仍有运行用途，原位保留。 |
| 结果原件 | 轨迹、FrozenPatch、评分日志、题主分析、独立复核、材料清单和SHA索引 | 从题目行跳转；不作为所有agent的开工必读包。 |

本次导航调整：项目执行README指向264题入口；`environment_pipeline.md`明确为处理史；分类二README区分264总览与52产物；旧普通探针README明确旧17及历史范围。旧正文和证据链接原样保留。

## 哪些退出默认阅读

扫描范围内2197份Markdown/HTML中，1394份历史证据页＋17份旧包装页，共**1411份**可转为按需查证。包括环境早期批次、静态筛查、独立审查、旧分类和模型分析的日期化记录。退出默认阅读不表示无效或可删除；其中部分是当前任务行仍会引用的证据。

建议保留原目录结构，不把整个 `category2_repair_20260929` 或 `env_recipe_repair_20260919` 直接搬入history：目录内混有当前材料、公开输入、配方、冻结请求和原件。这些不是普通管理文档。

## 17份物理搬迁候选

以下均为**待检查候选**，未发现结构化SHA绑定不等于已证明可安全搬走。完整入链、原SHA和旧→新映射见[机器清单](../../../../../runs/dataset_docs_consolidation_20261004/document_audit/physical_archive_candidates.json)。候选目标统一为 `project1_execution/history/dataset_processing_20261004/<原相对路径>`；不压平目录。

| 原位置，相对project1_execution | 原用途 |
| --- | --- |
| `category2_repair_20260929/batch_plan.md` | 旧批次计划 |
| `category2_repair_20260929/cloud_intake_20261002.md` | 云端交接说明 |
| `category2_repair_20260929/coordination_resume_20261003.md` | 恢复通知 |
| `category2_repair_20260929/publication_pause_checkpoint_20261003.md` | 暂停检查点 |
| `category2_repair_20260929/resume_20260930.md` | 旧恢复安排 |
| `env_probe_20260909/cpu_followup_plan_20260909.md` | 早期CPU计划 |
| `env_probe_20260909/cpu_followup_stages_20260910.md` | 阶段安排 |
| `env_probe_20260909/cpu_followup_stages_review_20260910.md` | 阶段安排复核 |
| `env_probe_20260909/environment_pipeline_redesign_20260911.md` | 旧流程设计 |
| `environment_batch_20260925.md` | 旧批次说明 |
| `environment_batch_20260925_claude_review.md` | 旧批次说明复核 |
| `ordinary_probe_20260929/readiness_review.md` | 旧探针就绪检查 |
| `ordinary_probe_20260929/resume_20260930.md` | 旧探针恢复安排 |
| `swegym40_status_20260929/README.md` | 40题阶段入口 |
| `task120_status_20260929/classification_change_v2.md` | 120题旧分类变更 |
| `task120_status_20260929/fork_handoff.md` | 旧分流交接 |
| `task_lifecycle_workflow_claude_review_20260929.md` | 旧流程方案复核 |

实际搬迁时应先核完入链、出链、动态脚本路径、行号引用及冻结清单；保留原字节与SHA，修好阅读链接和旧路径导航后再验收。不能为了让归档目录整齐而回写历史清单中的path/hash；若存在此类约束，直接原位保留。

## 哪些不能按旧文档处理

- **471份检测到哈希或脚本引用的文档**：458份有结构化SHA引用、19份有脚本引用，二者去重471。这里只识别引用，不能据此声称每份历史SHA都重新验过。
- **配方与执行材料**：例如 `B_materials_20260908/official_cmd_contract_216.json`、环境修复配方、R2E环境pins、public/private材料、binding、request、receipt及冻结输入。
- **仍需独立核或含未决判断的逐题记录**：历史存在不等于工作完成。Dask8597/9212、旧探针语义问题等按任务行接续。
- **已排除的包装页**：`task120_status_20260929/README.md`被生成脚本引用；v0筛查草案及其复核有原样／行号追溯要求，先原位保留，不作为17候选的一部分。
- **当前其他工作**：A线实现与审查、`grading_performance_next_20261004`及相关性能证据、外部数据调查、精读资料、训练协议、安全／公共契约均不在本次搬迁范围。

## 后续维护方式

阶段原始证据可以继续留下，但不要每个线程再创建一份面向所有人的“当前进展总览”。题主更新原有源账和本题记录；汇总者核增量后刷新这里的逐题快照与同源HTML。发生结论变化时保留旧结果和版本关系，不把旧失败静默改为成功。

扫描范围与限制见[审计报告](../../../../../runs/dataset_docs_consolidation_20261004/document_audit/report.md)、[逐文件清单](../../../../../runs/dataset_docs_consolidation_20261004/document_audit/documents.json)及[导航方案原件](../../../../../runs/dataset_docs_consolidation_20261004/document_audit/navigation_archive_plan.json)。未发现引用不是“可删”的证明；聊天、动态生成路径和此次未扫描的外部入口仍可能引用它们。
