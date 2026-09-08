# R5c GLM-5.3 官方文章：预读与原文获取记录

**状态：未完成官方博客精读，不能计入已读完成数。** 2026-09-08 尝试读取《GLM-5.3: Frontier Coding with Emergent Cyber Capabilities》的原站、官方开发文档及模型卡，没有取得发布博客全文。当前实际可完整核读的是固定提交的官方 GitHub README 相关段落，另取得少量官方模型卡的搜索索引片段。这些载体可以确认部分发布主张，但不能恢复博客的训练方法、图表、脚注和完整实验条件。本稿保存已核事实与明确续读位置，不用旧调查或媒体转述填成新的精读成果。

导航：[来源及覆盖](#sources) · [已核官方说明](#verified) · [尚待原文检验的问题](#pending) · [续读与交付状态](#status)

<a id="sources"></a>
## 1. 来源、版本与实际覆盖

阅读日期：**2026-09-08**。项目读取基线为 `Rogerffff/RepoHarness@miles-migration@17d9899c6d4b61938f74bd9121da8dee9b621a8d`。本次只负责 R5c，不重写 R5b、R14、R15，也不将 GLM-5.3-Flash 合并进本任务。

| 标识 | 来源 | 本轮真实取得情况 | 允许支撑的内容 |
| --- | --- | --- | --- |
| B | [Z.AI GLM-5.3 官方博客][B] | 多次访问均未返回正文；主要为 Cache miss | 确认入口由官方 README 链接；不能确认文章的完整结构、图数或脚注 |
| D1/D2 | [英文开发文档][D1]、[中文开发文档][D2] | 未取得正文；Markdown 入口也未成功 | 仅保留入口，不从旧笔记恢复其当前内容 |
| C | [zai-org/GLM-5 README][C]，commit `008de4dbcc220032eb9b80a9a9802afad46a4053`（2026-09-01） | 读取 Introduction、Download Model、Serve、Note 和 Fine-tuning；GLM-5.3、5.2、Flash 的内容分别辨认 | 下文 §2 的官方声明及当前说明；不充当 8 月训练使用的代码版本 |
| M | [zai-org/GLM-5.3 模型卡][M] | 搜索索引返回部分引言、数表和使用说明；页面、Raw/Blame 等入口未取得完整正文 | 只能作片段级佐证；不称模型卡全文已读或评测脚注已覆盖 |
| U | [RepoHarness 原资料索引 R5c][U] | 读取固定项目提交中的登记行 | 仅作为待核线索；登记的 2026-08-14 不能冒称本轮从博客页头核得 |
| Q | [Codex 对 O01 的质量反馈][Q]与[阅读模板][T] | 已读相关范围 | 约束来源覆盖、曲线记录、独立审查身份和并行写入，不作为 GLM 训练证据 |

原站直连下载及容器 requests 也未成功，容器报域名解析失败。本轮未取得任何 R5c 原始 PDF、HTML 快照或图片；没有调用 OCR，也没有宣称看过不可访问的图。

U 登记的是“URL，未制作本地 PDF”。这只是该登记时的资产状态，不证明作者没有 PDF，也不证明用户其他工作区没有保存原文。当前没有足够依据制作原文章节覆盖表；下表是**任务范围的实际完成状态**，不是臆造的原文目录。

| 所需阅读范围 | 状态 |
| --- | --- |
| 博客标题、日期、导语的原页核对 | 未取得原页；标题和日期仍依登记 |
| 训练阶段、coding 数据与环境生产 | 未回原文核验 |
| SAO、compaction、OPD 和 slime 的最终采用方式 | 未回原文核验 |
| 数值一致性、调度与性能实验 | 未回原文核验 |
| 网络安全结果、风险、缓解措施和发布边界 | 只有 C 的概括，未覆盖博客完整范围 |
| 完整数表、曲线、图注和评测脚注 | 未完成；不以搜索片段或新闻表格替代 |
| 当前官方 README 的模型关系和使用说明 | 已核 C 中相关段落 |
| 作者自查 / 独立审查 / 实验复现 | 来源预读自查完成 / 未进行 / 未进行 |

<a id="verified"></a>
## 2. 已能从固定官方 README 确认什么

### 2.1 同一 base 的发布声明，不等于完整 checkpoint lineage

C 的 GLM-5.3 引言明确把它描述为沿用 GLM-5.2 的 base，增益来自 post-training。它还宣称内部 Z.ai Code Bench 改善约 50%，并强调 coding、长程任务与网络安全能力。[C，Introduction → GLM-5.3 & GLM-5.3-Flash][C]

**证据层级：这是作者发布主张，不是本轮独立实验结论。** 已读段落没有恢复完整训练阶段、初始化 checkpoint、各阶段耗时或训练数据变化。因此不能据此写成“从公开 GLM-5.2 最终权重直接续训一个月”，也不能把所有差值归给单独的 SAO、compaction 或某个数据机制。

“改善约 50%”的分母和具体比较协议须回完整博客与原图核对；不是增加 50 个百分点。C 没有在该段给出足够的原始数值，本稿不借第三方转述补算。

### 2.2 GLM-5.3 与 GLM-5.3-Flash 必须分开

C 对普通 GLM-5.3 使用上述同 base 声明；对 Flash 则描述新 base、稀疏与线性注意力的混合架构、mHC 及多模态预训练。Download Model 表将普通 5.3 标为 **744B-A40B**，Flash 标为 **320B-A18B**。[C，Introduction、Download Model][C]

这是本轮可以直接排除的一种归因错误：不能拿 Flash 的架构和预训练变化，解释普通 5.3 的后训练收益。反过来，也不能把普通 5.3 的“同 base”声明用于 Flash。模型权重文件的逐参数计数不在本轮核查范围内。

### 2.3 当前推理接口说明不等于训练超参数

C 的 Note 指明 5.3 支持 `reasoning_effort=low/high/max`，默认或其他值回落为 `max`；复现榜单建议保持 `max`。`clear_thinking` 未传时默认 `false`，聊天使用建议显式设为 `true`。[C，Serve → Note][C]

这些是固定 README 的使用说明，不是本轮已经检查过 tokenizer/chat-template 源码或在线 API 的行为。它们说明评测至少需要记录 effort 与历史 thinking 的保留方式，却不能补出训练 token budget、PPO 参数或博客各 benchmark 的专属协议。

### 2.4 能力主张与公开资产分别记录

C 宣称 CyberGym 漏洞发现表现领先，以及利用类 benchmark 相对 5.2 超过两倍；但该 README 概括没有给训练任务、攻击链结构、完整评测资源和安全干预对照。本轮只记录这种声明存在，不据此断言“没有任何安全训练就涌现全部能力”，也不转换成可操作的漏洞利用指导。[C，Introduction][C]

C 提供普通 GLM-5.3 的 FP8 与 BF16 官方权重入口，并列出 SGLang、vLLM、Transformers 等部署文档，以及 slime/ms-swift 微调入口。[C，Download Model、Serve、Fine-tuning][C] 入口存在不等于旗舰历史训练配方开放，也不证明所有框架支持项都用于该模型。本轮未下载权重、核验模型 LICENSE 全文或运行 serving；不把代码仓库许可、5.2 许可或 Flash 许可套到普通 5.3。

<a id="pending"></a>
## 3. 原索引中的重点：保留为待核问题，不升级为训练事实

以下左列仅转述 U 的登记主题。**尤其是 `1e-7` 与 `>2.3×`，本轮没有从博客原文核得，不应引用本稿将其包装成新的一手确认。**

| U 登记的主题 | 取得全文后必须核对的内容 |
| --- | --- |
| 真实工作模式 → 长程可执行环境；judge 检查可解性 | 原料、生成/求解/审核角色、人工参与、数量漏斗、耗时与失败类型；有没有与普通扩容的对照 |
| verifier 不看 reference；oracle / no-op / unsolved-state 检查；solver 轨迹审计 | “不看 reference”约束的是哪个生成阶段；运行时资产隔离是否另有规定；合法替代解、误杀和随机性怎样检查 |
| SAO + compaction | 是命名采用声明还是给出完整组合目标；是否披露 critic、DIS、跨段 GAE、summary mask 和全局分母；不能由 R14/R15 自动补入 |
| Megatron / SGLang / data-buffer；top-p mask 与 top-k/full-vocabulary OPD | 框架新增支持与最终模型实际采用分别是什么；采样支持集、teacher/student 概率及训练消费怎样对齐 |
| R3-style / full numerical alignment；logprob 差 `1e-7` 量级 | 差值是 signed/absolute、平均/最大、逐 token/逐序列；模型、dtype、batch、cache、routing、稀疏索引及比较基线是什么 |
| router/slime 联合调度；长程 coding RL 吞吐 `>2.3×` | 分母是请求、token、有效 rollout 还是更新；硬件和工作负载是否匹配；是否包含教师、评分、失败和额外存储成本 |
| 网络安全能力与开放策略 | 训练能力范围、评测条件、发现与利用的指标分别是什么；历史发布计划与后来可下载状态是否混用 |

来源：[U 的 R5c 登记行][U]。这些问题不预设原文缺少相应信息；在正文没有取得时，正确状态是**未核验**，不是**未披露**。

## 4. 与本线程已有三篇的关系：目前不作采用结论

[SAO](R15_single_rollout_asynchronous_optimization.md)、[CompactionRL](R14_compaction_rl.md)和[GLM-5.2 官方文章](R5b_glm5_2_blog.md)各有独立来源与阅读边界。它们只能提供比较坐标，不能承担 GLM-5.3 缺失正文的事实证明。

后续比较优先回答三个问题：5.3 对 5.2 新增了什么明确披露；新增机制是否有独立消融；哪些只是当前框架支持或作者的整体采用主张。只有取得对应原文以后，才讨论项目一的候选增量。本轮不批准新数据管线、loss、教师调度或训练资源配置。

<a id="status"></a>
## 5. 续读入口与交付状态

本稿沿用预定 R5c 正文路径，方便取得原文后就地继续，但**不是可计入完成数的正式精读成品**。补读需要官方博客可读全文，或保持来源和日期的 PDF/HTML 快照；只提供新闻摘要或另一模型的综述不能补齐关键缺口。

取得原文后，先按真实文章结构覆盖所有正文、图表、脚注及相关安全内容，再逐项核对 §3；不要仅搜索已有关键词而遗漏新增章节。若来源版本不同，保留各自结果与条件，不自行调和。固定 README 相关段落已核，不必重新整库审计。

作者自查见 [R5c 来源检查记录](reviews/R5c_self_check_20260908.md)。本轮没有独立 reviewer，没有复现实验，也没有宣称原图已看。共享 README/catalog/批次状态、历史笔记及训练代码均不修改。

## 来源链接

[B]: https://z.ai/blog/glm-5.3
[D1]: https://docs.z.ai/guides/llm/glm-5.3
[D2]: https://docs.bigmodel.cn/cn/guide/models/text/glm-5.3
[M]: https://huggingface.co/zai-org/GLM-5.3/blob/main/README.md
[C]: https://github.com/zai-org/GLM-5/blob/008de4dbcc220032eb9b80a9a9802afad46a4053/README.md
[U]: https://github.com/Rogerffff/RepoHarness/blob/17d9899c6d4b61938f74bd9121da8dee9b621a8d/docs/harness_improve/external_paper_references/README.md
[Q]: https://github.com/Rogerffff/RepoHarness/blob/17d9899c6d4b61938f74bd9121da8dee9b621a8d/docs/harness_improve/external_paper_references/reading_notes/reviews/15_O01_codex_quality_review_20260907.md
[T]: https://github.com/Rogerffff/RepoHarness/blob/17d9899c6d4b61938f74bd9121da8dee9b621a8d/docs/harness_improve/external_paper_references/reading_notes/NOTE_TEMPLATE.md
