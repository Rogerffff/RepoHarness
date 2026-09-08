# B：Claude 首轮建议的判断与外部 Pro 补读任务

日期：2026-09-08。性质：阅读与方案建议，不批准实现、租机、题单或训练语义。依据 [Claude 建议全文](B_materials_20260908/00_B_reading_synthesis_and_first_round_plan.md)、[Claude 资产盘点](B_materials_20260908/repo_asset_inventory.md)及 [Codex 阅读整合](b_reading_20260908/00_reading_synthesis.md)。本轮读完前两份 Claude 文档；没有重新执行其 loader/parser 探针或审完整评分链。

## 1. Claude 当前主张及我的判断

Claude 主张从阅读转入小批真实验证：补 SWE-Gym 任务的评分适配，在 x86 Linux 验约 20 题，检查 empty/gold、重复运行、题意与测试、少量合法替代解，再通过只推理不起 learner 的真实 Claude Code 入口诊断目标基座。他提出 ≤40 题 dev 与 Verified 100–200 题最终坐标，也建议暂不新增其他题源 ingestion 或 terminal 训练。具体题量、划分和载体仍是讨论稿。

其新增价值是资产盘点：他报告 216 题 bundle/pins 可读取、实际覆盖 9 个仓库，但未找到这批题的真实容器评分产物；离线 parser 探针失败，现有正式数据划分和目标 30B 基座画像也缺失。这些比“环境数据已经准备好了”的说法具体。未找到历史产物应保留检索范围，不能据此证明任何未记录的远端运行从未发生。

**我同意小批验证与基座诊断的方向，但不把 216 题、Verified 子集或 20 题规模提前作为正式方案。** 已有投入可用作启动材料，不是来源优于其他资产的证据；外部补读可与后续本地准备并行。

以下几项应在实施讨论前收紧：

- **评分适配不能按“约 30 行”验收。** 需要真实测试日志、测试 ID 与 F2P/P2P 对应、收集错误/超时/空结果，以及 mypy/conan 等实际命令边界。vendored constants 没有 parser 映射，不等于完整上游 SWE-Gym fork 没有 parser；先找原作者评分路径。小批数据有助于区分失败原因，但不能批准“所有超时或零解析一律 reward 0”。
- **基座通过率 <20%、0/8 组过半只是待测猜想。** Verified/OpenHands 上的分数不能跨数据、harness、模型变体和预算外推到 SWE-Gym Lite。即使简化为每题单次成功率均为 20%、八次条件独立，全失败概率也是 `0.8^8≈16.8%`；全失败超过一半对应单次概率低于约 8.3%。真实任务难度和尝试相关性各异，需要任务级采样。
- **“Pro 约 30% 坏题”和“少于 60 题只能看十几个点”过于简化。** N13b 是筛选后审计及不同审查分支，不能当随机抽样全库坏题率；小样本能辨别多大变化还依赖基础成功率、配对差异与相关性，不能仅由题数下绝对结论。见 [N13b 精读](../../../harness_improve/external_paper_references/reading_notes/N13b_coding_eval_signal_noise.md)及 [评测整合](b_reading_20260908/02_evaluation_and_harness.md)。
- **费用与部署组件仍需具体核价和试跑。** $10/一天、镜像体积和 216 全量工期是估算；是否需要 registry、机器磁盘/网络和基座精度，应按实际用法选择。量化模型可用于某些接口诊断，但不能直接替代计划训练精度下的基座分数。gold/no-op 的环境检查本身不要求先付费调用强模型。

以上是对建议中证据与推论的检查，没有新增运行时 bug 定案，也未改 Claude 原稿。

## 2. 这些是不是明确需要外部精读的材料

**是明确有价值的补读主题，但不是同等紧急，也不是全部读完才能继续 B 线。** 上轮列的是“当前库缺少完整独立成稿”，不是“原始作者没有披露”，也不是把每篇都升级为实施前置条件。

建议现在并行安排前四个主题；若外部 Pro 容量充足，后两个可同批，无需等现有 216 题失败后才读。下表版本身份已于本轮回官方入口核对；这项核对不是全文精读。Pro 开工时再记录实际读取版本。

| 顺序 | 主题与主来源 | 为什么补；不应预设什么 |
| --- | --- | --- |
| 1 | **SWE-Gym**：[Training Software Engineering Agents and Verifiers with SWE-Gym，2412.21139v2](https://arxiv.org/abs/2412.21139v2)，[官方仓库](https://github.com/SWE-Gym/SWE-Gym) | 本项目候选来源本身；恢复 Full/Lite 的关系、构建和原始验证、agent/verifier 训练及推理扩展。不能用上游总述替代本项目评分适配验证。 |
| 2 | **Agentica DeepSWE 训练配方**：[Together 官方技术文](https://www.together.ai/blog/deepswe)，[官方模型卡](https://huggingface.co/agentica-org/DeepSWE-Preview)及其链接的 rLLM/R2E-Gym 训练与评测资产 | 直接 RL 的正例与选数据的负例都直接相关。官方文 §6 报告 SWE-Gym/SWE-smith 的 RL 改善有限、solve-none 较高；应恢复条件，不能外推它们普遍不能训。不是 Datacurve 同名 benchmark。 |
| 3 | **Agentic Reinforcement Learning for Real-World Code Repair**：[2510.22075v1](https://arxiv.org/abs/2510.22075v1) | 原文明确报告匹配环境下提升、跨环境泛化失败；需弄清“环境变化”究竟改了什么，帮助我们设计训练/诊断/最终测评的关系。不能把它等同所有跨仓库或跨 harness 都失败。 |
| 4 | **SWE-rebench 实际运维经验**：[Nebius 官方基建文章](https://nebius.com/blog/posts/infrastructure-behind-swe-rebench)，[AI Engineer 原演讲与转录入口](https://ai.engineer/talks/wcUJWP6WpGM-swe-rebench-lessons-from-evaluating-coding-agents) | 关注评分稳定性、修题、人时、缓存/重试和可靠性指标。两项来源各自成文，与已经读完的 O11 V2 论文互相链接；无需重做 O11。 |
| 5 | **ScaleSWE**：[Immersion in the GitHub Universe: Scaling Coding Agents to Mastery，2602.09892v4](https://arxiv.org/abs/2602.09892v4) | 真实 PR、构建/测试/题面合成、监督轨迹与约 30B-A3B 初始化路线的备选。摘要已明确是轨迹蒸馏与 fine-tuning 证据，不自动算 RL 实证；库中旧版本引用需对账。 |
| 6 | **SWE-Dev**：[Building Software Engineering Agents with Training and Inference Scaling，2506.07636v2](https://arxiv.org/abs/2506.07636v2)，[ACL 正式版](https://aclanthology.org/2025.findings-acl.193/)，[官方仓库](https://github.com/THUDM/SWE-Dev) | 补测试合成、轨迹训练、单次执行预算扩展；也是 CompactionRL 转引的题源。读完上游仍不能恢复 CompactionRL 没披露的具体子集。 |

DeepSWE 值得升到本批前列：它包含对现有候选数据的直接 RL 尝试，也包含从教师轨迹 SFT 后继续 RL 改善有限的尝试。它提供与成功配方相反的证据，值得查完整条件，不应只记最高分。[官方技术文 §6](https://www.together.ai/blog/deepswe)

O28 需修正来源层级：原目录的 Sean Weldon 页面是他对演讲的整理，并非 Ibragim/Nebius 原始技术报告。此次已定位主办方原演讲入口；优先读原始转录/幻灯片/视频，二手页面只用来找待核说法。尤其“每题一人日”“时间切分是唯一办法”等不能不查原话、对象和条件就写成我方要求。

另有两项是**补完旧稿**：E3 Envs-FORGE 应恢复完整原文并更新已有稿；GLM-5.3 保留预读状态，若只服务当前 B 任务，其优先级低于上述直接 SWE 来源。两者都不另起重复编号。

## 3. 可转发给 Pro 的共同任务说明

下面说明与上表中某一主题一起发送。重点是先完整读，再用项目问题查漏；不把问题清单变成阅读范围限制。

> 请完整精读分配的主来源，包括所有后训练阶段、实验分支、图表、附录、负结果与局限。博客检查尾部案例、补充材料和所链接的训练配方；演讲按完整转录阅读，并核影响结论的幻灯片/时间戳。现有项目问题只用于读完后查漏，不能省略其他后训练内容。
>
> 项目一是 miles + SGLang + 真实 coding harness + rh2 的 SWE 后训练闭环；B 线负责环境、数据、评测与基座诊断。当前任务集和最终评测尚未确定，八卡约 30B-A3B 是资源背景。你的任务是沉淀可追溯证据与条件化启示，不批准项目范围、算法、筛选阈值或预算。
>
> 在完整阅读后，特别核对：任务从哪里来、镜像/测试如何产生和验证、Full/Lite/Subset/公开发布量与实际训练消费量的差异；训练模型与教师、SFT/RL/蒸馏和推理扩展的分别贡献；reward、失败、超时、组统计与 mask；划分/泄漏、真实 harness 和预算；全部成本的分母、反例与公开资产复用边界。
>
> 若某项原文没有披露，明确标注；分清未披露、未取得、未检查。不要用现代代码补历史实验。实现附查只追会影响结论的实际入口与字段消费，固定 commit，避免整库审计。测试 ID、parser、测试选择与 reward 边界对数据源论文尤其有用，但不要因此省略它的其他实验。
>
> 成文保持中文，保留原文章节覆盖表、关键数字的页码/图表/时间戳、作者解释与读者推论的区分。每个独立主来源维护自己的 Markdown；同一发布的官方博客、模型卡、关联代码可作为一个带来源分层的配方专题。最后写作者自查，真实说明独立 reviewer 是否存在。没有独立工具时不用虚构审查，也不把 self-check 文件名写成已独立通过。
>
> 输出到 `docs/harness_improve/external_paper_references/reading_notes/`，自查到其 `reviews/`。开工先检查远端是否已有同来源新稿，复用已有入口。只提交自己负责的正文和自查；共享 README/catalog 交汇总会话维护，避免并行覆盖。使用最新分支构造仅含本任务文件的普通提交，遇到前移重新基于最新版本处理，不 force push。不得修改训练代码或项目定案。

建议文件名（开工先查重）：

| 主题 | 正文 | 自查 |
| --- | --- | --- |
| SWE-Gym | `O04_swe_gym.md` | `O04_self_check_YYYYMMDD.md` |
| DeepSWE 模型配方 | `O02_deepswe_training_recipe.md` | `O02_self_check_YYYYMMDD.md` |
| Real-World Code Repair | `agentic_rl_real_world_code_repair_2510.22075.md` | `real_world_code_repair_self_check_YYYYMMDD.md` |
| SWE-rebench 官方基建 | `O28a_swe_rebench_infrastructure.md` | `O28a_self_check_YYYYMMDD.md` |
| SWE-rebench 原演讲 | `O28b_swe_rebench_evaluation_lessons.md` | `O28b_self_check_YYYYMMDD.md` |
| ScaleSWE | `O05_scale_swe.md` | `O05_self_check_YYYYMMDD.md` |
| SWE-Dev | `swe_dev_2506.07636.md` | `swe_dev_self_check_YYYYMMDD.md` |

SWE-Dev 和 Real-World Code Repair 暂用名称+arXiv ID，未擅自占用新的共享来源编号。日期填写实际成文日期。前四个主题对应五份主来源文档，第四个主题可以由一个 Pro 会话依次完成两份；一次安排全部六个主题则预计七份主来源文档。

## 4. 与 B 工作的关系

本文件只准备了可下发任务，没有替用户启动外部会话、租机或修改评分实现。外部阅读回答方法和来源的已知证据；实际环境是否可运行、parser 是否正确、目标基座能否学与真实成本仍要本地/远端小批实验。补读与后续准备可以并行，不新增“全部论文读完”闸门。
