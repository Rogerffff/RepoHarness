# SWE-Bench Pro Verified：获取边界与作者自查记录

日期：2026-09-23。正文：[官方接入核查与全文续读底稿](../swe_bench_pro_verified_2609.08149.md)。

**交付级别：部分完成。论文正文、附录和图表未读，不计入全文精读完成数；官方配套资料与固定源码已读。未进行独立审查或实验复现。** 本记录是作者自查，不伪造子线程、模型 effort、独立 reviewer 或测试执行。

## 1. 项目与文档范围

- 项目基线：`codex/project-status-20260923@0554dafd633cd982288bd60a54f75da65e5c54d4`。
- 本次独立分支：`pro/swe-bench-pro-verified-reading-20260923`，基于上述固定提交。
- 授权：用户要求第一项 SWE-Bench Pro Verified 精读与文档写入；没有修改题目、测试、模型、reward、网络设置或训练代码的授权。
- 阅读规范：已读仓库 `AGENTS.md`、`reading_notes/NOTE_TEMPLATE.md` 与 9 月 23 日同步入口。
- 未改变阅读库总数或“完成”状态；未改共享 README、来源目录、其他线程文件与 MiMo 分支。

## 2. 已取得与未取得的材料

| 材料 | 本次情况 |
| --- | --- |
| arXiv `2609.08149` 索引 | 搜索返回标题、作者、日期与摘要；不是 PDF 正文 |
| arXiv abs/HTML/PDF，含 v1 与无版本入口 | 网页工具返回 cache miss／不可访问；备用 export、ar5iv 等亦未取得 |
| 本机原文 | runtime 无已挂载原件；容器直接联网因 DNS 失败，没有下载到 PDF |
| 远程项目缓存 | `07_source_intake_and_reading_queue.md` 明确写“原文缓存未发布”，登记 37 页 v1 PDF；不能伪造 sandbox 原件链接 |
| HF 全卡、API、文件入口 | 本轮未取得完整 JSONL 与 immutable revision；README 修改讨论片段不代替全卡与数据 |
| 官方研究说明／运行指南 | 通过 GitHub 成功完整读取；运行指南的参数表、全部 Tabs 与结果字段已读 |
| AgentCompass 主实现／网络／Docker recipe | 固定 `5a71ecbbe3799b7b2dc07a28e831fd062f5925d5`；主文件长输出分段补到 EOF，另两文件全文读取 |
| 原始 Pro scripts、Docker 镜像、候选补丁 | 未下载／未执行；没有逐题修订 diff 验证 |

已经在会话中请用户补传 `swe_bench_pro_verified_2609.08149v1.pdf`。不将文件获取失败写成“作者未披露”。没有可用 PDF 对象，因此没有截图或 OCR；不填造图表覆盖表。后续需从原文目录建立覆盖，而不是从本稿反向推测论文结构。

## 3. 本次自查的关键内容

**来源身份。** 不与 SWE-bench Verified、原始 SWE-bench Pro 或 AgentCompass `2607.13705` 报告混为同一来源。当前 AgentCompass 代码与论文实验 revision 分开。

**任务分类。** 731、102 及 22/75/3/2 仅标作当前官方指南报告值；没有宣称重数数据或审计全池。尤其不把 overly narrow tests 自动翻译成一种已确认的低覆盖／误拒类别。

**实验结果。** 没有从二手报道重建模型分数表，没有将文档的默认参数写成论文实验预算，没有填写论文未核实的重复次数、通过变化归因或 zero false positive 结论。

**源码语义。** 分开控制侧 TaskSpec/ground_truth 与模型输入；分开声明的 network policy 与 provider 实际执行；分开 fresh workspace 与候选内容对评分的影响；分开 parser 完成、resolved、进程 returncode 和外层错误状态。

**版本绑定。** 数据默认 `main`、原始脚本默认 `main`、镜像按 tag 且存在本地缓存。只得出“框架 pin 不独自保证资产冻结”，没有声称已观察到实际漂移。

**修订测试落地。** 在已读路径中未见通用追加 `test_patch` 的步骤，但可能由镜像／base commit／scripts 承担；没有下结论说修订未生效或发现上游 bug。

**条件性边界。** entryscript 无显式 `set -e`、空必需集合的集合逻辑、重复 test name 合并，均明确标为静态性质／待验证条件；没有宣称公开题库已经触发。

**旧稿复用。** 环境专题中 119 候选、17 题测试修改、优先改题面及三条件实验等信息只作为续读线索；未包装成本轮重新核实的原文事实。

## 4. 实际检查与未执行项

本地仅对文档进行检查：引用定义和导航锚点、代码围栏／数学分隔符、UTF-8 替换字符、行尾空格，以及 22+75+3+2 和 102/731 的算术。没有对上游 Python 执行单元测试、模拟环境或真实容器，没有声称发现可复现漏洞。

远程文档保存后应回读并核对 blob SHA；本记录不在保存前预填最终 commit。即使远程写入成功，任务状态仍是“待原文的部分交付”，不会自动变成精读完成。

## 5. 下一次只需补这些关键证据

1. PDF/HTML/TeX：版本、目录、全部正文与附录、实验表图及原文局限。
2. 原版与修订数据：固定 revision，按实例比较题面、requirements、interface、测试与评分集合；需要至少一个真实测试修订案例。
3. 对应执行材料：image digest、base commit、脚本版本、被执行测试与修订字段的关系。
4. 论文实验：完整条件、样本分母、重复与归因方法；区分 raw score 与 reviewer 解释。
5. 独立审查：在论文正文补齐后另行安排真实 reviewer；本轮作者检查不替代。

拿到原件后续写原正文，不重做本轮已经完成的官方代码导读，也不复制一篇新的同名摘要。
