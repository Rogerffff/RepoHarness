# SWE-1.5：把模型、harness、环境与部署速度作为联合系统

SWE-1.5 的核心不是一个新算法名称，而是在真实 Cascade harness 中后训练开放基座，同时迭代工具、提示词、高保真环境和产品部署。作者用经典测试、代码质量rubric和浏览器agent验收组合评分，并以人工reward hardening修补漏洞。SWE-Bench Pro图示得分40.08%，同模型换SWE-agent/Claude Code后分别34.47%/29.00%；作者自己强调这不代表Cascade普遍优于其他harness。950 tok/s和draft模型来自Cerebras部署优化，不是已经测得RL rollout吞吐。本文保存三个原图和训练／环境披露的边界，不用1.6/1.7或SWE-grep的方法细节补足作者没有给出的配方。

导航：[来源](#scope) · [联合开发](#system) · [环境](#environment) · [评测与速度](#results) · [演进与项目](#project)

<a id="scope"></a>
## 1. 来源、版本与覆盖

Cognition，*Introducing SWE-1.5: Our Fast Agent Model*，[官方网页][WEB]，**2025-10-29**。署名 Jacob Teo、Nikhil Jha、Connor Fogarty、Gary Chang、Theodor Marcu、Edison Zhang、Albert Tam、Sean Sullivan、Swyx、Silas Alberti。

用户提供的 `02_SWE17_16_15.zip` 是主资料，正文采集时间 **2026-09-11T09:43:13.419Z**；本轮阅读 **2026-09-14**。同时取得网页正文核对标题和日期，快照图像与原始PNG用于图表阅读。固定项目基线 `miles-migration@2484c93cad304588b41abeb38b6b6b976dfbda0d`。资料包是来源而非前人精读结论。

| 原文部分 | 已读内容 | 本稿位置 |
| --- | --- | --- |
| 发布导言、Motivation | 模型规模范围、部署速度和联合系统动机 | §2、§5 |
| The Agent-Model Interface | Cascade训练、dogfooding、工具/prompt改动、Falcon Alpha、跨harness图 | §2、§4 |
| RL Coding Environments | 分布、soft factors、人工任务、三种grader、reward hardening | §3 |
| Training & Infrastructure | 开放基座选择、GB200、policy-gradient变体、VM | §2、§5 |
| Public Evals | Pro图与速度图、使用场景和个案 | §4–5 |
| Optimizing for Speed、What's Next | draft、请求优先级、工具开销、产品声明 | §5 |

[视觉索引][VIS]共3页，分别对应原始image-01/02/03，全部目视读取；不是作者发表的论文页。正文没有数学公式或独立附录。网页底部相关文章和导航不算正文；没有为引用的SWE-grep、blockdiff、Junior-Dev Benchmark等填入“全文精读完成”。

<a id="system"></a>
## 2. 联合开发流程与真实模型关系

原文明示模型是数千亿参数量级的frontier-size模型，选取某个强开放基座后，在Cascade及真实任务环境上做端到端RL。**基座名称、确切总/激活参数和checkpoint没有公开**。1.6后来称两者使用同一pre-trained model；这不构成1.5基座的精确身份，也不证明1.6直接续接1.5权重。[导言、Training & Infrastructure][TEXT]

开发循环为：训练模型 → 内部真实使用 → 发现工具、prompt和体验问题 → 修改harness／工具 → 在更新后的条件重新训练。多个beta以 **Falcon Alpha** 名称向用户部署并观察指标。它是产品反馈驱动的模型—系统迭代，不是论文中已经完整定义的数据自动课程，也不是每轮只改一个变量的受控消融。

算法仅称用于长多轮稳定性的 **unbiased policy gradient 的变体**，并指向SWE-grep文章。这里没有完整reward/advantage公式、importance ratio、clip、group样本数、mask、loss分母、学习率或更新调度。不能因此标成标准GRPO/RLOO，不能将引用文的所有细节默认继承，更没有新增SFT或多教师OPD的披露。

作者将harness、推理服务和用户体验纳入agent能力定义，工具改进也会改善Windsurf内其他模型。读者应区分权重收益和所有模型可共享的工具改进，不能把联合系统的全部增益归给RL。

<a id="environment"></a>
## 3. 训练环境：三类评分与人工hardening

### 3.1 数据生产的已知与未知

作者批评常见SWE训练任务repo/类型窄，以及只用单元测试reward会遗漏代码质量、过度try-catch等soft factors。应把它理解为其经验和产品目标，不是“所有单测reward必然产生低质量代码”的因果证明。[RL Coding Environments][TEXT]

为覆盖Devin/Windsurf实际任务及语言分布，团队**人工制作任务**，与资深工程师、开源维护者和工程领导共同设计高保真环境；自建评测借鉴Devin与Junior-Dev Benchmark经验。本文没有仓库数、任务数、镜像数、轨迹数、筛选漏斗、模型成功率或人工成本。所谓训练规模相对小，是作者对该环境路线阶段的描述，不能与“数千GB200训练”拼成一个小预算项目。

### 3.2 三类grader不能简化为“unit test + LLM分数”

| 原文机制 | 主要对象 | 尚未披露 |
| --- | --- | --- |
| Classical tests | 单元／集成测试，验证可执行正确性 | 选择、隔离、F2P/P2P、日志解析和flakiness合同 |
| Rubrics | 代码质量和求解方式 | rubric维度、权重、判定者/模型、一致性及误杀 |
| Agentic grading | browser-use agent端到端测试产品特性 | 浏览器环境、控制模型、工具/时间预算、失败恢复 |

多个机制可以在同一环境组合，原文没有给合成reward公式、优先级或blocker逻辑。不能由三类机制存在就假设它们独立可靠，或直接把后来FrontierCode的规则作为本次配置。

### 3.3 Reward hardening

人工专家主动尝试绕过grader，多轮修补后发现经典测试遗漏，并报告假阳性显著减少；没有量化前后分母、独立攻击者、合法替代解保持率或完整判定程序。原文也说需要进一步研究。[同节][TEXT]

这里的hardening对象是环境与grader，不是已经训练了一个攻击模型。对B线而言，有价值的是把评分作为可被检验的程序；它不替代gold/no-op/alternate solution检查，也不能由“发现更多攻击”直接推断模型真实能力提高。

数据的使用许可、时间切分、去重与污染审计、训练时公开/隐藏测试、候选patch投影、异常重试和终止奖励，本篇未说明。尤其不能从1.6后来的repo不重叠声明倒填1.5的全部数据审计。

<a id="results"></a>
## 4. 公开评测：三张图完整值与比较范围

### 4.1 图1：能力与解码速度并列

图标题SWE-Bench Pro，副标题 **731 tasks across 41 repos**。以下为图示值，不表示本轮重跑或当前榜单。

| 模型 | Score (%) | 图内速度 (tok/s) |
| --- | ---: | ---: |
| Sonnet 4.5 | 43.60 | 69 |
| SWE-1.5 | 40.08 | 950 |
| Haiku 4.5 | 39.45 | 142 |
| GPT-5 (High) | 36.30 | 43 |
| Kimi K2 | 27.67 | 62 |
| SWE-1 | 16.55 | 39 |

来源：`original_assets/image-01.png`。表中SWE-1.5低于Sonnet4.5，而略高于Haiku4.5。没有各模型统一运行配置、重复数、置信区间、最终任务清单和速度测量方法，因此near-SOTA/near-frontier是带时间和系统背景的发布解释，不是统计证明的最高能力。

正文“6×比Haiku、13×比Sonnet更快”是近似部署叙事；按图内数字直接相除分别约6.69和13.77，保留原措辞与显示精度，不以算术比值补出严格基准。图3把相同score与tok/s放到散点平面，**不是新的训练对照或完整任务耗时实验**。

### 4.2 图2：同模型换harness

| harness | SWE-1.5 Score (%) |
| --- | ---: |
| Cascade | 40.08 |
| SWE-agent | 34.47 |
| Claude Code | 29.00 |

来源：`original_assets/image-02.png`。Cascade分别高5.61和11.08个百分点。作者主动强调：这不反映harness本身的普遍优劣；在其他harness上调优的模型也可能相反。分数下降的重要因素之一是工具调用失败增加。[The Agent-Model Interface][TEXT]

这个结果支持训练／部署接口一致性很重要，但不能证明“多harness混训有增益”，也不能在未排除工具协议失配的情况下，把低分全部解释为权重能力迁移失败。缺少重新训练、等预算提示词／adapter修复以及各模型×harness完整矩阵。

### 4.3 个案与测量层级

作者列出代码库探索、端到端全栈应用、配置编辑等使用场景，一位工程师报告Kubernetes manifest编辑从约20秒到不足5秒。这是个案体验，不是公开benchmark全任务wall-clock平均值。内部工程师改用该模型作为daily driver，也不是带随机化控制的偏好研究。

<a id="speed"></a>
## 5. 训练基础设施与部署推理：相邻但不同的两条路径

**训练侧**：数千GB200 NVL72；早期硬件从六月进入团队时firmware不成熟，需要health check、fault-tolerant training和rack-scale NVLink。作者认为可能是首批在新硬件训练并生产发布的模型之一，本文不独立验证“首个”排名。[Training & Infrastructure][TEXT]

**环境侧**：otterlink hypervisor支撑Devin数万并发机器的能力，代码执行和浏览器环境可用于rollout。**数万并发是平台能力，不是已报告本次训练稳定运行了相同数量的有效rollout。** 未给实际利用率、CPU/内存、镜像复用、重试和sandbox启动数据。

**部署侧**：与Cerebras协作，训练优化后的draft以投机解码，增加请求优先级机制来改善完整agent session。此段位于Optimizing for Speed，不能改写为“训练期在线draft已经提高RL吞吐”，也没有披露draft结构、接受率、更新频率、训练成本或目标分布保证。

当模型以up to950 tok/s解码，lint检查和命令执行等原先小开销变成瓶颈，重写这些组件使**每步开销最多减少2秒**。它是上界/特定场景，不是每步固定节省2秒，更不是每个训练step。完整任务时间仍包含prefill、生成、工具、环境和用户批准等部分。

这条经验可概括为读者推论：执行变快后瓶颈会迁移。真正可迁移的工作方式是做分阶段测量，而不是让RepoHarness仿造同一部署服务和硬件。

<a id="project"></a>
## 6. 与后续版本的关系及项目含义

1.5强调交互速度、真实工具和高保真环境；1.6 Preview展示扩训练后的更高分，也暴露过度验证与人工批准负担；1.7换成已深度RL的K2.7基座并强化采样重放、长程与容错。**这是公开问题和技术叙事的演进，不是控制所有条件的三点scaling曲线。** 后续分数、长度baseline、QAT/R3、网络隔离或自压缩机制不可悄悄回填成本篇已披露配方。

对2026-09-14的RepoHarness（miles＋SGLang＋外部harness/rh2，约8×96GB）有三项最直接的候选：

| 候选问题 | 来源依据 | 小型可区分的实验 |
| --- | --- | --- |
| 训练与实际harness是否一致 | 图2及工具失败说明 | 同权重/任务在两接口检查tool parse、上下文和执行条件，先做合理adapter/prompt基线，再解释权重迁移 |
| tests之外的质量如何可靠评分 | tests/rubrics/browser三种机制 | 对既有一批任务人工核查误收/误杀，比较新增维度是否独立可靠；不立刻把LLM分数混进reward |
| rollout之外是否有明显工程开销 | 每步工具开销与速度优化 | 固定轨迹或请求replay，对prefill/decode/tool/grade分别计时；语义保持的优化不必伪称新模型能力 |

环境完整性和下游学习结果要分开；对上游framework与adapter准确归因，不把Cognition的规模数字作为我方预计收益。本文不批准新增browser环境、reward model或draft训练链。

## 7. 公开资产、未知项与检查状态

可取得正文、三幅原图和外部链接；未见本篇完整任务、权重、训练脚本、reward/optimizer配置或成本清单。整个产品使用的开放基座，与完整系统开放可复现是不同概念。原文沒有完整token/context/tool/wall-clock预算、组采样或baseline，不能借“unbiased”一词填充实现。

**已完成**：全部正文、三个图像原值、模型关系、训练/部署区别及引用身份核对。**未完成也未声称**：独立审查、训练/环境复现、引用链全文和私有代码检查。记录见[本组作者自查](reviews/cognition_swe1_5_1_7_self_check_20260914.md)。

本稿只负责该篇来源；三代对照的集中表见[1.7 §10](cognition_swe1_7.md#project)。共享索引、源资料和训练实现不在本轮修改范围。

[WEB]: https://cognition.com/blog/swe-1-5
[TEXT]: source_supplements/cognition_20260911/swe-1-5/reading_text.md
[VIS]: source_supplements/cognition_20260911/swe-1-5/VISUAL_INDEX.md
