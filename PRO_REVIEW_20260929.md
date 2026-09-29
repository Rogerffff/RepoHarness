# 外部 Pro 阅读入口（2026-09-29）

这是 `codex/pro-review-20260929` 分支上的**阅读快照**：以本地已提交版本 `a31cdcd0adb0fab3e681201edfb928653fdf5b3c` 为基础，补入截至整理时的未提交文档、实验脚本和代码。未提交实现按原样保存，不代表已经通过集成验收；计划、实施与验证状态以各题记录为准。本次发布没有运行模型、容器或全量回归。

## 建议阅读顺序

1. [项目当前入口](docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/README.md)：A/B 两线职责和当前工作。
2. [环境流水线总入口](docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/environment_pipeline.md)：环境、静态审查、开发验证和模型探针的工作索引。
3. [120题现状](docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task120_status_20260929/README.md)：72道 SWE-Gym 与48道 R2E 的分类依据。历史分类与当前建议应分开阅读。
4. [第2类41题修复](docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/README.md)、[执行计划](docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/batch_plan.md)：当前材料、已完成步骤和剩余工作。
5. [SWE正式修订入口决策](docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/d6/decision_request.md)：首片范围与成本；最新授权和实施状态见同目录的执行记录，不能用较早的请求页代替当前决定。
6. [统一处理标准](docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md)与[外部资料精读入口](docs/harness_improve/external_paper_references/reading_notes/README.md)。

## 页面与证据

- [统一汇报 HTML](runs/task2_swegym_dev_20260925/screening_standard_v1.html)
- [旧任务二汇报 HTML](runs/task2_swegym_dev_20260925/task2_report.html)
- [SWE40题状态 HTML](runs/swegym40_status_20260929/report.html)

HTML 可下载后本地打开；GitHub 文件页主要展示源码。页面和历史文档中的本机绝对路径不是远程网站地址，仓库前缀后的路径可在本分支查找。部分链接指向未发布的完整运行日志，不能把链接存在当成远端原件已经齐备。

公开仓库内没有上传凭据、本机配置、嵌套参考仓库、新增大型原始数据、下载的论文/源码缓存和完整 `runs/`。保留研究笔记和来源链接；额外纳入三份汇报页及第2类首批紧凑材料。Orange公开读者包保留清单与题面，没有重复上传整个任务源码快照。现有提交中已经跟踪的材料保持原样。

[发布清单](docs/pro_review_20260929/publication_manifest.json)逐项记录本次纳入文件的SHA256、排除范围及机械检查结果。对这份阅读快照的审查结论应带版本；请勿把未提交代码或历史实验结果直接视为当前运行配置。
