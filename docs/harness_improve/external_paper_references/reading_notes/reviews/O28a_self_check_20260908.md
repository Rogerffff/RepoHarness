# O28a 作者自查：SWE-rebench 官方运维文章

日期：2026-09-08。正文：[O28a_swe_rebench_infrastructure.md](../O28a_swe_rebench_infrastructure.md)。

**状态：正文精读及作者自查完成；没有独立 reviewer，也没有复现运行。** 本线程没有创建独立审查 agent 的工具；不虚构线程 ID、模型 effort 或“独立通过”。

## 1. 来源与覆盖

主来源是 2025-11-07 Nebius 的 *Behind SWE-rebench: Infrastructure to collect massive datasets of SWE tasks and evaluate agents at scale*。已读网页全部技术正文、伪代码、数据与性能段、贡献者和引用；末尾商业推广仅作范围检查。不延伸为五篇参考文献的全文精读。

逐小节覆盖记录在正文 §1.1。正文没有编号技术图表；顶部装饰图访问失败，未以此补造图片结论。没有 PDF 或 TeX 附件；此来源是网页，不能用论文“附录缺失”描述它。

配套实现固定到 `SWE-rebench/SWE-bench-fork@e4907b7a90eafaa1f0a6428fd04fe31cdd8b4284`。完整读取两个 README 和 `run_evaluation_tracto.py`；`run_evaluation.py` 检查约 L200 至末尾。未全文审计原 `run_instance`、reporting、镜像导入脚本或 Kubernetes 内部 runner。

项目读取基线：`d2df06d49e42b93436d10d1b7a12d4e1f0ae3be5`，`miles-migration`。按 B 任务说明，本文与同批 O28b 独立成文，不改共享索引。

## 2. 本轮重点核对及处理

| 项目 | 本次处理 |
| --- | --- |
| 运行、评分与训练 | 把三者分开；没有替文章补充未披露的 RL 优化器 |
| 数字单位 | 原始数据、候选、合格任务、轨迹、Pods 和评分次数分列 |
| 成本外推 | 历史局部评分耗时不转成端到端预算；派生比例只说明漏斗 |
| 源码身份 | 2026 年代码不代表 2025 年实验 revision |
| 文档命令 | 对照 README 缺失参数与实际 argparse／分支，记为固定版本文档问题 |
| 恢复状态 | 追踪上层 report 检查与后端目录检查；只声明条件性静态风险 |
| 空补丁 | 记录普通入口的执行前过滤，不把它当成已经做过 no-op 验证 |
| 异常与隔离 | 不把 errored=False、map 完成、rootless 或 fresh container 任一项当完整正确性保证 |

来源事实集中简记；后续方法与 B 实验建议明确为读者分析。没有上传原文全文、第三方代码或截图副本。没有对外创建 issue/PR。

## 3. 本地检查与未完成事项

本地检查包括 Markdown 引用定义、内部锚点、两篇互链和自查链接；检查无替换字符／冲突标记；独立复算 `21/153`。这些不是容器、评分或模型实验。实际执行结果记录在本地 `checks.json`，不作为新研究数据上传。

仍未完成：完整 scorer 对拍、失败目录的真实重跑、平台 scheduler retry 语义、全流程费用、任务资产许可链及独立审查。代码建议保持待验证，不因文档完稿就视为 bug 已在线复现。

## 4. 提交范围

本篇、本自查、O28b 正文及 O28b 自查，共四份专属文档。提交时读取最新分支，只普通 fast-forward；不覆盖其他线程文件、不 force push、不修改训练配置或方案批准状态。提交成功与远程回读以交付消息及真实 Git 历史为准，不在成功前预填 commit。
