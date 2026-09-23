# 新补充的四份质量审计来源

2026-09-15 核查三份官方网页正文及新发布的 SWE-Bench Pro Verified 论文。原始 HTML 和检索文本在 sources/web_quality/（原文缓存未发布：`docs/harness_improve/external_paper_references/environment_processing_survey_20260915/sources/web_quality/manifest.json`），论文 PDF 单独链接于第 4 项。**本轮是环境专题核查，不是完整精读**：重点读取主文方法、局限及相关附录；没有逐图视觉核验、复现审计器或重跑样本，全部图片/交互依赖也未离线归档。后续 Pro 可从下列原始材料继续读。

## 1. METR：Many SWE-bench-Passing PRs Would Not Be Merged into Main

**实际怎么查：**4 位活跃维护者审查 3 个仓库、95 道题上的 296 份模型补丁；将补丁放进历史仓库副本，以不告知模型/人类来源的方式分批评审，区分核心功能、其他代码回归、代码质量。另混入 47 份真实已合并的 gold 补丁，以其复审接受率校准维护者判断噪声。移除无要求清理的调试工件，并豁免新写测试要求；审查没有 CI。主分析把自动评分失败直接计为维护者失败，另用小规模非随机样本检查假阴性，并做附录敏感性分析。

**用途与边界：**它检查“测试过关能否代表维护者接受”，补充 OpenAI 的题意/测试缺陷审计；也与 FrontierCode **主动设计和校准新 rubric** 不同。不是每道不合并补丁都证明测试错；样本只含三个仓库、旧模型且不允许依据 review 迭代，不能据此宣判新模型的最终修复能力。

来源：[官方文章](https://metr.org/notes/2026-03-10-many-swe-bench-passing-prs-would-not-be-merged-into-main/)（2026-03-10），Data and Methods、Technical limitations、Appendix A1/A3/A8；原始 HTML（原文缓存未发布：`docs/harness_improve/external_paper_references/environment_processing_survey_20260915/sources/web_quality/metr_mergeability.html`） · 检索文本（原文缓存未发布：`docs/harness_improve/external_paper_references/environment_processing_survey_20260915/sources/web_quality/metr_mergeability.txt`）。

## 2. Cursor：Reward hacking is swamping model intelligence gains

**实际怎么查：**审计 agent 读取题面与 731 条完整求解轨迹、看不到通过结果，判断是否直接取得已知修复，区分网页查答案和未来 Git 历史。再用严格 harness 重跑 SWE-bench Pro/Multilingual：开始前删 `.git` 并建单提交仓库，仅评分时恢复历史；默认禁止外连，经固定代理允许指定包源做依赖解析。作者同时说明旧镜像早于上游 Git 清理修复，并发现“镜像系统二进制已修好”也会提示模型去找答案。

**用途与边界：**提供运行期信息泄漏的审计与干预，区别于 OpenAI 的测试语义审查；相比 FrontierCode 1.1 的规则提示/scanner，它主要修改网络和历史可达性。标准/严格差值是两项限制的联合结果，也受 prompt 影响，不能全算作弊贡献；未给审计器误检漏检率，包源许可只是 best effort。作者没有建议所有真实工作任务都断网。

来源：[官方文章](https://cursor.com/blog/reward-hacking-coding-benchmarks)（2026-06-25），Catch a model with a model、Stricter environment design、脚注；原始 HTML（原文缓存未发布：`docs/harness_improve/external_paper_references/environment_processing_survey_20260915/sources/web_quality/cursor_reward_hacking.html`） · 检索文本（原文缓存未发布：`docs/harness_improve/external_paper_references/environment_processing_survey_20260915/sources/web_quality/cursor_reward_hacking.txt`）。

## 3. Datacurve：DeepSWE v1.1

**实际怎么改：**保留原长程工程任务，修依赖漂移、移除部分 flaky tests；agent 在指向起始 commit 的 `main` 上建分支并提交，清除未来 Git 内容。只提取**已提交 diff**到独立 fresh verifier 容器评分；每个定义任务的测试输出 CTRF 名称和状态，用于发现缺测试、提前退出和部分进展。另检查截至 6 月 5 日上游是否已有相似实现，并公开版本对照与轨迹入口。

**用途与边界：**这是可直接对照 RH2 的评分隔离、候选工件、逐测试账本和环境修订实例；不是 Agentica 的同名 DeepSWE 训练配方，也不是 OpenAI/FrontierCode 式完整题意/替代解质检。博客没有公开全部依赖/flaky 修订理由及权限合同；fresh 容器本身不证明候选源码、配置或结构化报告无法影响评分。日期截面的上游检查也不保证以后没有答案泄漏。

来源：[官方文章](https://deepswe.datacurve.ai/blog/deepswe-v1-1)（当前页署 2026-06-14，排行榜另有后续更新时间），导言、What changed、Impact on Results；原始 HTML（原文缓存未发布：`docs/harness_improve/external_paper_references/environment_processing_survey_20260915/sources/web_quality/datacurve_deepswe_v11.html`） · 检索文本（原文缓存未发布：`docs/harness_improve/external_paper_references/environment_processing_survey_20260915/sources/web_quality/datacurve_deepswe_v11.txt`）。

## 4. SWE-Bench Pro Verified：修任务与封泄漏分开验证

**实际怎么做：**保留 731 题，按公开缺陷报告筛出 119 个候选；LLM 判断问题和起草修法，专家最终修订 102 题。优先改题面、requirements、interface，必要才改测试（17 题），随后试跑、看字段 diff 和前后 PASS/FAIL。反泄漏另做：重建单提交仓库并保留准备好的依赖，清理测试/fixture 和 hooks，匿名化 ID/路径、过滤元数据，阻断代码托管域名但保留依赖服务。用 Baseline、仅防泄漏、再修题三个条件分开对照，逐条审查通过变失败是否伤及正常执行。

**用途与边界：**比只报告缺陷多给了可下载修订题库和执行入口；本轮确认 HF 有 731 行 JSONL、AgentCompass 有接入导航，尚未校验每条修订/运行实现。其“优先改题面与测试自洽”可能改变能力目标，不能自动成为我们的修题原则。公开报告候选不等于全池独立复审；仍承认域名绕行、残留工件和遗漏坏题。转移归因含 LLM 判断，未证明零误杀/零泄漏。

来源：[论文 §3–4、§5.2](https://arxiv.org/html/2609.08149v1)（arXiv v1：2026-09-08；PDF 封面另印 2026-09-09，保留两种日期）；本地 PDF（原文缓存未发布：`docs/harness_improve/external_paper_references/environment_processing_survey_20260915/sources/swe_bench_pro_verified_2609.08149v1.pdf`）；[官方修订数据](https://huggingface.co/datasets/opencompass/SWEBench-Pro-Verified) · [AgentCompass](https://github.com/open-compass/AgentCompass)。

四份资料的补读重点是：**人类判断怎样校准、泄漏检测怎样验证、环境/评分版本变更怎样对账，以及如何发布有证据的题目修订**。它们互补，不能把维护者不接受、运行期查答案、测试本身错误统计成同一种“坏题率”。
