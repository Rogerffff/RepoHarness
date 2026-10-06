# 两个确切基座的继续训练证据与 coding-agent 数据调查

整理日期：2026-10-03（Asia/Singapore）。本页为独立调查与建议，不是训练决策、题目准入或执行指令。机器可读事实、版本、获取记录与限制见 [evidence.json](evidence.json)。

## 结论与建议

1. **两个模型都有继续训练的外部正面证据，不能把 Qwen3.6 判为已饱和。** 对 `Qwen3-Coder-30B-A3B-Instruct`，Uni-Agent 报告 R2E-Gym 上继续 RL 后验证分数 **46.2→52.0**；RTMC 报告同模型 **46.8→52.2**，但采用三次运行多数票和最佳 checkpoint，不能当普通单次 pass@1。对 `Qwen3.6-35B-A3B`，KAT-Dev 的 SFT＋RL、PACT 的 RL、ROSS 的 RL 后选择性 SFT 均有同一研究内的前后收益。它们支持“仍可训练”，不保证在 RH2、现有题单和小预算下复现收益。见下方逐项证据。
2. **“Qwen3.6 更强”和“当前已试题偏易”可以暂作工作假设；“这些来源对它没有训练价值”证据不足。** 本地配对样本只有 11 道 R2E、5 个仓库，主要是一题一采样，且有评分遗漏与候选运行异常。缺少覆盖整池、重复成功率和训练前后对照。
3. **Coder 的第一优先级是 R2E，其次是 Uni-Agent 使用的 SWE-reBench 分支；Qwen3.6 应优先扩展来源和任务类型。** 后者优先调查 MiMo 开源 code 环境、多语言 SWE-reBench、OpenSWE，再用 SWE-smith 的组合/跨文件任务补足。SWE-Gym 仍可保留，但不建议为得到更多“容易且通过”的题继续无上限修补 Lite。
4. **MiMo 的“约 3k 开源代码任务”现在已有实物。** 当前公开 `code` split 是 **2,698 行**，另有镜像映射、公开 Docker Hub 标签和评分实现；不是只有宣传页。六条静态抽查均有题面、测试补丁、测试命令和镜像标识，均未见显式 `repo`、`base_commit` 或参考修复字段。它值得优先做小规模适配调查，但尚不能称为 RH2 可直接训练的 2,698 道合格题。
5. **现有 52 题应继续完成有边界的质量收口，同时减少为难度筛选而做的低信息重复。** 先关闭已知假阳性与异常归因，保留 Coder 的区分题；可靠易题可用于链路冒烟和回归。新来源建议先固定 24 题、96 次配对尝试，预留 32 次预先选定的重复，总上限 128 次。此处仅提出方案，没有启动实验、改队列或变更现有授权。

## 调查范围与证据等级

本轮先读已有精读和项目记录，再核作者论文、模型卡、官方代码与数据仓库。仅获取网页、代码、元数据、MiMo 的六条样本及小型镜像映射；未下载完整数据集或容器镜像，未做模型求解、环境评分或训练实验，未接受 gated 数据使用条款。

| 标记 | 含义 | 不能据此声称什么 |
| --- | --- | --- |
| 作者报告 | 论文、作者模型卡或项目结果 | 不是我方复现；无误差条不等于收益稳定 |
| 代码可核 | 实现、配置或脚本可读 | 不等于脚本与某个结果逐项绑定，也不等于已在 RH2 运行 |
| 资产可定位 | 元数据、文件、镜像标签或少量行已核 | 不等于全量可拉取、评分可信或训练准入 |
| 项目既有实测 | 引用本地固定快照与题级证据 | 原始 reward 不自动等于语义正确，本轮没有新增实测 |

### 锁定的是哪两个模型

| 模型 | 当前官方说明 | 本轮读取的 HF revision |
| --- | --- | --- |
| [Qwen/Qwen3-Coder-30B-A3B-Instruct](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct) | 已后训练；约 30.5B 总参数、3.3B 激活；原生 262,144 context；仅非 thinking 模式；Apache-2.0 | `b2cff646eb4bb1d68355c01b18ae02e7cf42d120` |
| [Qwen/Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | 虽无 Instruct 后缀，仍是已后训练模型；35B/3B；混合架构、原生 262,144 context，含多模态能力；Apache-2.0 | `995ad96eacd98c81ed38be0c5b274b04031597b0` |

这些 revision 固定的是本轮所读发布物，**不能反推作者历史实验使用了相同权重 revision**。`Qwen3-30B-A3B-Instruct`、`Qwen3-32B`、`Qwen3.5-35B-A3B`、`Qwen3-Coder-Next` 均不是这两个 checkpoint。

## A. 对确切 checkpoint 的继续训练证据

下表的箭头仅表示同一来源内的对照，不能跨行拼接成排行榜；pp 为百分点。

| 研究与起点 | 数据与训练阶段 | 作者结果及口径 | 证据强度与缺口 |
| --- | --- | --- | --- |
| **Uni-Agent / Coder** | R2E-Gym；GSPO；fully async、100 turns、128K | 验证指标 **46.2→52.0，+5.8pp** | 官方结果表明确模型和来源；确切任务 manifest、采样次数及运行配置未完整绑定。不能用非 Coder 的代表曲线补齐。 |
| **Uni-Agent / Coder** | SWE-reBench；GSPO；colocate async、200 turns、128K | 验证指标 **47.4→54.2，+6.8pp** | 当前可读 quickstart 用 `swe-rebench-filtered-1150`、SWE-bench Verified 验证。结果表仍提示不同运行可能不同配置，不能自动认作 Claude Code 结果。 |
| **RTMC / Coder** | 作者称 8.1K R2E-Gym 子集、无 SWE-bench 重叠；GRPO→step reward→rollout-tree credit | SWE-bench Verified：**46.8→49.0→50.4→52.2**，即 234/245/252/261 ÷500 | **三次评测多数票、每方法选择最佳 checkpoint**。作者称 pass@1，但不等于标准单次 pass@1；任务清单与完整可复现 run 未定位。 |
| **NeMo Gym / Coder** | SWE-Gym；mini-SWE-agent；图中标记 GRPO | SWE-bench Verified 验证奖励曲线，step 0→30 约 **0.17→0.28** | 官方 README＋图像可核，仅近似读图，没有精确数表、完整 run 绑定或方差。弱于明确前后评测表。 |
| **KAT-Coder-V2.5-Dev / Qwen3.6** | **127K SFT examples 后 RL 10 epochs**；沿用 KAT 数据/训练设计并加入模型特定奖励调整 | SWE Verified **64.4→69.4**；Multilingual **57.0→63.0**；Pro **40.63→45.96** | 同作者统一 Claude Code 评测，有公开衍生权重。属于 **SFT＋RL 总收益**，没有消融可把收益全部归给 RL；127K 数据和 RL 任务 manifest 未找到。 |
| **PACT / Qwen3.6** | OpenSWE；Codex＋Harbor；Dressage/slime；对比 GRPO、PPO、SAO、PACT | SWE Verified pass@1：base **60.8**；GRPO **65.4**；PPO **65.0**；SAO **63.6**；PACT **67.4** | 同论文、同起点的 RL 证据。未定位 coding 训练任务精确数量/清单、GPU 总时长或发布权重；数学实验的 3,200 题不能移用。 |
| **ROSS / Qwen3.6** | 过滤后的 OpenSWE **4,048 题**做上游 RL；再复用成功轨迹，选择 assistant 片段做 SFT | SWE Verified：base **60.8**→RL **64.2**；全成功轨迹 SFT **65.2**；ROSS **68.4** | 作者明确四策略固定 Codex、Harbor、工具和执行预算。+3.4pp 是上游 RL；+4.2pp 是 RL 后选择性 SFT，合计 +7.6pp。精确 4,048 IDs 未找到。 |

来源：[Uni-Agent 固定版结果页](https://github.com/verl-project/uni-agent/blob/00b20d72d35816a3d66e6137c424a5b60e92d062/docs/source/benchmark/rl-training.md)、[RTMC v1 §5/Table 3](https://arxiv.org/html/2604.11037v1#S5)、[NeMo 固定版 README](https://github.com/NVIDIA-NeMo/Gym/blob/3ef478df1ee163134d32a3f291f0a9e5981d0e52/responses_api_agents/mini_swe_agent/README.md)、[KAT-Dev 模型卡](https://huggingface.co/Kwaipilot/KAT-Coder-V2.5-Dev/tree/7be56fe773e72b6f5ca93c1ae45d828ddb893922)、[PACT v1 §5/Table 2](https://arxiv.org/html/2609.26355v1#S5)、[ROSS v1 Table 2/Appendix C.4](https://arxiv.org/html/2609.35954v1).

### 预算、harness 与复现注意事项

- **Uni-Agent。** 当前 Coder quickstart 有 ReAct 和真实 Claude Code 两套配置。ReAct 脚本默认 8 节点×8 GPU、64 prompts×8 rollouts、学习率 `1e-6`、10 epochs；文档用 GSPO 覆盖默认 loss，并使用 TIS/router replay。**这些是当前示例，不是已核对的历史 R2E 运行预算**。不要把 README 的调度提速图或非 Coder 曲线当作 Coder 结果复现。[当前 quickstart](https://github.com/verl-project/uni-agent/blob/00b20d72d35816a3d66e6137c424a5b60e92d062/docs/source/quickstart/rl-training.md)
- **RTMC。** ROLL、32 GPU、ROCK 中的 SWE-agent 风格执行/R2E 工具；8 prompts×8 rollouts、学习率 `1e-7`、20 warmup steps。其收益既可能来自任务训练，也包含 credit-assignment 方法差异；非普通 pass@1 的选择口径必须与数字同存。[论文 §5](https://arxiv.org/html/2604.11037v1#S5)
- **NeMo。** README 给 16 nodes、32 prompts 和 “Num rollouts per step: 16”；不擅自解释为每 prompt 16 次。另一个训练集 profiling 写 `Accuracy 0.10 / Resolved 276 / Total 2401`，但 **276/2401≈11.50%**；它既不等于 0.10，也不等于曲线起点。2,401 与数据总量 2,438 相差 37，文档未解释排除原因。[官方 README](https://github.com/NVIDIA-NeMo/Gym/blob/3ef478df1ee163134d32a3f291f0a9e5981d0e52/responses_api_agents/mini_swe_agent/README.md)
- **KAT-Dev。** 统一评测为 `claude_code@2.1.195`、temperature 1、top_p .95、256K、pass@1，每集合只跑一次，明显错误才重测。作者描述二元奖励早期出现并行工具调用失控，随后调整分层奖励与行为惩罚；这不是 RH2 应照搬惩罚项的证据。Dev 的 RL task count、GPU 数和完整配方仍缺。KAT-V2.5 技术报告是数据构造参考，不能把其中所有算法细节无条件归于 Dev。[Dev 后训练说明](https://huggingface.co/Kwaipilot/KAT-Coder-V2.5-Dev#post-training)、[KAT 技术报告 v1](https://arxiv.org/html/2607.05471v1)
- **PACT。** 每轮 64 prompts×8＝512 trajectories，优化 batch 128；128K context、**每个交互 turn**最多生成 64K；actor/critic 学习率 `1e-6/5e-6`。总 steps、GPU-hours 和评测重复数未明确到可复现运行。[论文 §5.1、Appendix E.4](https://arxiv.org/html/2609.26355v1)
- **ROSS。** 剔除暴露 `.git` 历史或其他可作弊工件及低质量题后得到 4,048 题；thinking 开启。后续 SFT 从上游 iteration 29 开始，64 GPU/8 nodes、8 epochs、65,536 sequence limit；只对选定 assistant token 计 loss。该预算属于**后续 SFT**，不是上游 RL 总预算。PACT 和 ROSS 同属 AllSpark，不能当两个独立团队复现，也不能假定训练子集完全相同。[Appendix C.4](https://arxiv.org/html/2609.35954v1)

此外，[slime 的 coding_agent_rl 示例](https://github.com/THUDM/slime/blob/8c17b676cb57af1d17ee4402e91e9209af84b60b/examples/coding_agent_rl/README.md)已明确支持 Qwen3.6＋Claude Code＋SGLang，使用独立执行/评分环境。它仍要求调用者提供训练 JSONL 与环境服务；**没有对应可下载题单和量化前后收益**。这是可借鉴实现，不是第八项效果证据。

### 不属于两个目标模型、但值得借鉴的工作

| 工作 | 正确归属与训练 | 能借鉴什么；不能外推什么 |
| --- | --- | --- |
| [Agentica/Together DeepSWE](https://www.together.ai/blog/deepswe) | **Qwen3-32B**，R2E 约 4.5k，纯 RL；64 H100、约 6 天；SWE Verified 单次成功率约 23→42.2，后者按 16 次运行平均 | 支持 R2E 的训练用途；59% 的测试时选择和 71% pass@16 不能与单次成绩混用。不是 Coder 30B。 |
| [SWE-smith v2](https://arxiv.org/html/2504.21798v2) | **Qwen2.5-Coder-32B-Instruct**，5,016 条 Claude 3.7 成功轨迹做 SFT；Verified 6.8→40.2；75 steps、temperature 0；训练最多 3 epochs、32K、2–8 H100 | 证明可执行合成任务可产有效示范；不是两个目标的 RL 收益，也不能用旧模型难度评级替代当前实测。 |
| [MiMo-V2.6-Distill-Qwen-9B](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B) | **Qwen3.5-9B** 的 MiMo 轨迹 SFT；77.4B 加权总 token/27.2B loss token；Verified avg@3 60.0→61.1，Pro 32.0→44.6 | 公开的是 SFT 起点权重；2,698 环境不是这 77.4B token 的公开 SFT 全集。不能把别处的后续 RL 结果归到该权重。 |
| [CodeMidas v1](https://arxiv.org/html/2609.22068v1) | **MiMo-V2.5** 做 GRPO；5,545 个功能实现任务、3,185 仓库、23 语言；DeepSWE 10.0→21.7；32 prompts×32、500 turns 的大预算 | 借鉴“从已有功能构造缺失功能＋独立测试＋多解验证”。公开全量 5,545 题未定位；也没有证据证明它等于 MiMo 的 2,698 行。 |

Qwen3-Coder-Next 的大规模环境训练可作方法参考，但它是 80B/3B 的另一模型。LegoRL 公开结果的训练起点是 Qwen3.5-35B-A3B。二者均不补入上面的确切 checkpoint 证据表。

### 对“更强所以饱和”的判断

**基准分数较高、某个已清洗子集多数通过、可用于 RL 的学习信号较少，是三个不同命题。** 最后一个命题需要在固定模型/工具/预算下测量题级重复成功率，并最终通过训练前后泛化对照验证。外部论文已经提供 Qwen3.6 继续学习的反例，但不足以证明所有来源都值得接入。

Qwen 官方模型卡的 SWE Verified **73.4** 与 KAT 的基线 **64.4** 来自不同 harness/设置。不能计算成“继续训练下降 4pp”，也不能把作者解释的差距当作已独立验证的归因。[Qwen 官方评测说明](https://huggingface.co/Qwen/Qwen3.6-35B-A3B)、[KAT 自测说明](https://huggingface.co/Kwaipilot/KAT-Coder-V2.5-Dev)

## B. 八类值得考虑的数据与环境资产

数量均注明当前资产或论文口径；下面的接入成本是调查判断，不是实测报价。F2P 指原状态失败、有效修复后应通过的测试，P2P 指修复前后均应通过的回归测试。数据卡许可证不替代每个原仓库、镜像依赖和附加条款的核对。

### 可获得性、构造方式与评分材料

| 来源 | 当前资产与许可 | 构造、环境、参考与评分 | 训练用途 |
| --- | --- | --- | --- |
| **1. R2E-Gym** | [V1](https://huggingface.co/datasets/R2E-Gym/R2E-Gym-V1) 8,101；[Subset](https://huggingface.co/datasets/R2E-Gym/R2E-Gym-Subset) 4,578；Apache-2.0 | Python commit-based 任务，合成问题/测试；有 `docker_image`、commit、变更内容和 expected test outputs，非标准 SWE `patch/test_patch` schema。现有 RH2 已有 ingest。 | **现成 RL 任务池**；两个表述“8.1k”和“4.6k”不是同一 subset。Coder 有直接外部效果。 |
| **2. SWE-Gym Full/Lite** | [Full](https://huggingface.co/datasets/SWE-Gym/SWE-Gym) 2,438，MIT；[Lite](https://huggingface.co/datasets/SWE-Gym/SWE-Gym-Lite) 230，自身卡未列 license | 11 个 Python 仓库的人类 issue/PR；base commit、gold patch、test patch、F2P/P2P；有容器构建/执行体系。Lite 是选择子集，不代表更难。 | **现成 RL/SFT 环境**；继续复用已修资产，Full 可补覆盖。 |
| **3. SWE-reBench 系列** | [Uni 1150](https://huggingface.co/datasets/dyyyyyyyy/swe-rebench-filtered-1150)：1,150、Apache-2.0；[Prime V2 Filtered Verified](https://huggingface.co/datasets/PrimeIntellect/SWE-rebench-V2-Filtered-Verified)：**6,272/32,079**，CC-BY-4.0＋逐 repo license | 两个不同发布物。Prime 有 patch/test_patch、install_config、log_parser、image_name、质量标签及验证日志；来源上游覆盖 17 语言，但本轮未统计删选后语言数；镜像名已转成 Prime registry。 | **现成 RL 任务候选**；Coder 的 Uni 效果不证明 Prime V2 子集同样有效。 |
| **4. SWE-smith** | 旧总仓已提示迁移至分语言库；[Python](https://huggingface.co/datasets/SWE-bench/SWE-smith-py) 50,908、[Go](https://huggingface.co/datasets/SWE-bench/SWE-smith-go) 8,212，MIT；[TS](https://huggingface.co/datasets/SWE-bench/SWE-smith-ts) 5,032，卡未列 license | 程序变异、LM 重写、PR mirror、组合 bug；同仓复用镜像。**数据字段 `patch` 是注入 bug 的补丁**，不能直接当 gold repair；原健康状态/反向补丁构成参考。有 F2P/P2P。 | **现成任务＋可扩展构造工具**；可产 RL 环境或成功示范，训练论文主要是 SFT。 |
| **5. MiMo-V2.6-RL-oss code** | [官方数据](https://huggingface.co/datasets/XiaomiMiMo/MiMo-V2.6-RL-oss) **2,698**；Apache-2.0；code.parquet 约 13.3MB；镜像映射公开 | 多仓工程任务；六条抽查有题面、test_patch、test_command、cwd、镜像；无显式 gold patch/repo/base commit。mimoagent 提供评分实现。 | **公开 RL 环境候选**，不是代码 SFT 轨迹集；缺参考闭环时先隔离调查。 |
| **6. OpenSWE / daVinci-Env** | [数据入口](https://huggingface.co/datasets/GAIR/OpenSWE) gated-auto，需身份/用途及条款同意；卡标 mixed permissive＋CC-BY-4.0，按 LICENSE/原仓库区分 | [论文 v2](https://arxiv.org/html/2603.13023v2) 报 45,320 环境、12.8k Python 仓库，约 9k 筛选环境和 13k 轨迹；Dockerfiles/eval scripts；可再分可重分发和其他仓库。未登录读取原始数据返回 401。 | **有条件可获得的 RL 环境/SFT 轨迹**；ROSS 4,048 是再次筛选子集，不能由总量推得精确 IDs。 |
| **7. Datacurve DeepSWE** | [官方 GitHub](https://github.com/datacurve-ai/deep-swe)、[HF](https://huggingface.co/datasets/datacurve/deep-swe)；**113** 道、5 语言；gated-auto，明确 evaluation use；license 字段未列 | 原创长程工程任务；Harbor 格式，含环境、测试和 solution 目录。v1.1 的补丁送独立 grader；提交捕获规则会影响未 commit 改动。 | **只作保留评测**，不放入 RL 池。它与 Agentica 的 DeepSWE 模型是不同项目。 |
| **8. CodeMidas 构造路线** | [论文 v1](https://arxiv.org/html/2609.22068v1) 5,545 题/23 语言；本轮未找到可下载完整任务 manifest、统一镜像集合和相应许可 | 从原有功能构造实现任务，以原实现和替代解检查测试；有多次 no-op/reference 检查。大跨度语言/应用是潜在覆盖优势。 | **当前为方法候选**，不计入现成可用题数；需要另建数据工程，不是短期拿来即训。 |

### 难度、重叠与 RH2 接入成本

| 来源 | 对两模型难度的现有依据 | 重叠/泄漏问题 | 成本与维护判断；优先动作 |
| --- | --- | --- | --- |
| R2E | Coder 有 Uni/RTMC 直接收益；本地配对结果仍有 Coder 失败。Qwen3.6 的全池难度未知 | 与现有题直接同源；同仓相邻 commit、题面/测试生成共源；作者“无 benchmark 重叠”不等于模型从未见过仓库 | **低新增接线、中等题级维护**。优先用已知有效配方找更多仓库/不同变更，而非重复挑同仓易题。 |
| SWE-Gym | NeMo Coder profiling/训练曲线提示有空间；我方已试 SWE 子集偏易但少且不配对 | Lite/Full 包含关系；与其他 GitHub PR 数据跨源重复；同仓版本高度相关 | **低新增接线、中高历史环境维护**。先复用验收材料，再少量试 Full 中不同任务。 |
| SWE-reBench | Uni 对 Coder 正面；Prime 的 GLM 采样标签不是两目标的成功率 | V1/V2/不同筛选发布重叠；与 SWE-Gym/OpenSWE 的 issue/PR 重复要单独查 | **中等适配，registry 搬运可能升高成本**。先核可访问镜像/可重建配方，再选语言/仓库分层样本。 |
| SWE-smith | 旧 Qwen2.5 SFT 收益是迁移证据；两目标需新测；“组合 bug”不自动等于语义更难 | 同一 repo/base 上衍生大量 bug，随机按行切分会泄漏；题面可能透露局部改法 | **中等初始适配、同仓摊薄环境成本**。限制每仓题数，按 repo/base/bug family 分组；检查注入方向。 |
| MiMo code | 作者的整体 MiMo/9B 结果不能映射到两目标或公开子集；六行抽查只证明结构 | 显式来源身份不足，尚不能可靠跨库去重；测试、git 历史或参考代码可能在镜像内 | **中高首次审计成本**。先补 repo/base/有效参考与隔离评分，再判断困难是否来自能力而非环境。 |
| OpenSWE | PACT/ROSS 对 Qwen3.6 直接训练证据；Coder 未找到同级直接对照 | 论文说过滤 SWE-rebench/SWE-bench 已有实例；仍需 manifest 复核和仓库保留；ROSS 特别过滤暴露历史 | **中高**，先解决合法数据获取与镜像分发；有既有权限时可提高优先级，不能假定 45k 都干净可用。 |
| Datacurve DeepSWE | 任务结构和 MiMo 等外部评测提示更长程；没有本轮两模型的匹配预算实测 | 应一直 held-out；接触参考解、反复调参都会削弱后续评测意义 | **中等 harness 转换/较高单题预算**。仅留作后续泛化核验，不用训练成功率挑题。 |
| CodeMidas | 长功能实现和多文件是难度代理；不能代替题级测量 | 原实现可能通过历史/依赖暴露；构造和评测仓库应隔离 | **高**。先借鉴构造/测试原则，不立即重建数千题。 |

Prime 当前卡还提供 gold 两轮验证、no-edit 排除和失败题复核记录；去除了部分坏镜像语言/转换失败任务。它**不是简单地把强模型全部做错的题删除**：16 次 GLM-5.2 全失败题会进一步检查可解性。使用其标签时应保存产生标签的模型与预算，而不是直接称为“Qwen3.6 难题”。[Prime 数据卡与附属日志](https://huggingface.co/datasets/PrimeIntellect/SWE-rebench-V2-Filtered-Verified/tree/6a0d56b425a893b018616587cdb71aa499c5fc99)

### MiMo：本轮新增、可复查的实物结论

固定数据 revision：`639865fd3374018d6cb29b9fb82dd531406fcf5f`；最后修改为 2026-09-26。`code.parquet` LFS 大小 **13,314,620 bytes**，SHA-256 为 `e15733cf2451cfbc5492a4120f7f8cfddbad818aa9f0b324c79888dd1fece161`。这是文件元数据，未下载 parquet。[固定树](https://huggingface.co/datasets/XiaomiMiMo/MiMo-V2.6-RL-oss/tree/639865fd3374018d6cb29b9fb82dd531406fcf5f)

读取 viewer 的第 0、1、1348、1349、2696、2697 行，六个 ID 分别为 `format-code-task-001457`、`001240`、`000448`、`000804`、`000578`、`000193`。这是固定位置结构抽查，**不是随机抽样或难度测评**。三份 viewer 响应各报告 code 总数 2,698；响应不自带不可变 revision，因而 evidence 中保留获取 URL、响应摘要哈希与同时读取的仓库版本，不把 viewer 响应伪称为 commit-bound。

六条内层 `instance_json` 均含 `cwd/dataset_type/docker_image/instance_id/problem_statement/test_command/test_patch/verifier_timeout_sec`，超时字段均为 1,800 秒；未见 gold repair、repo 或 base commit。完整映射有 **3,764 个唯一入口：2,698 code＋1,000 arvo＋65 general＋1 webdev**。总映射数和全数据集行数都不能当作 code 题数。[镜像映射](https://huggingface.co/datasets/XiaomiMiMo/MiMo-V2.6-RL-oss/resolve/639865fd3374018d6cb29b9fb82dd531406fcf5f/image-mapping.jsonl)

六个对应 Docker Hub 标签均返回 active/linux-amd64 元数据和 digest。样本中的 `format-code-task-…:latest` 需经映射转换成 `docker.io/xiaomimimo/mimo-v2.6-rl-oss:format-code-task-…`；不能直接拉取裸别名。**没有拉镜像，也没有检查全部 2,698 个标签**；digest 及六个查询 URL 存在 evidence 中。[Docker Hub 入口](https://hub.docker.com/r/xiaomimimo/mimo-v2.6-rl-oss/tags)

`mimoagent` 的 `opensource_code.py` 会重置相关测试文件、应用测试补丁，再在当前环境执行测试命令，退出码驱动奖励，并检查历史泄漏。它的执行方式不等于 RH2 独立新 grader 的物理隔离。[固定源码](https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/src/mimoagent/environments/datasets/opensource_code.py)

因此建议先验三件事：**能重建任务身份；能得到有效正对照；能在隔离评分中保留原测试语义。** 若公开材料确实没有参考修复，应记录缺口、核查原项目/镜像提供的参考路径，不能凭测试退出 0 或用自己随手写的解替代充分验证。旧 [09-23 MiMo 资产调查](../../../../harness_improve/external_paper_references/reading_notes/mimoagent_execution_and_training_assets_20260923.md)当时“未定位约 3k manifest”的状态已被本次新证据更新；旧记录作为历史保留。

## C. 分模型优先级与最小试点

### 每个模型优先考虑什么

| 顺序 | Coder 30B-A3B | Qwen3.6 35B-A3B |
| --- | --- | --- |
| 1 | **R2E V1/Subset**：确切模型有继续 RL 收益；利用现有接线验证能否保留足够有效差异 | **MiMo code**：已发布、任务类型可补充当前 PR 修复池；先做小规模参考/评分审计，不预设一定更难 |
| 2 | **Uni 1150 SWE-reBench**：最接近另一条确切 Coder 配方；再扩展 Prime V2 | **Prime SWE-reBench V2**：多语言、多仓库、现成质量记录；先确认镜像运输 |
| 3 | **SWE-Gym Full**：复用现有资产，寻找 Lite 以外差异；NeMo 提供支持性线索 | **OpenSWE 筛选子集**：确切 Qwen3.6 的 RL 证据最直接；已有合规访问与可用镜像时，可升至第一梯队 |
| 4 | **MiMo code**：评估功能实现、工具行为和跨语言迁移 | **SWE-smith**：限制简单变异，覆盖组合/跨文件/不同语言，验证是否仍有真实失败 |
| 5 | **SWE-smith**：补足可控难度与成功轨迹；避免只学注入模式 | **R2E 中已确认的较难、有效任务**：保留桥接对照及已修资产，不再只围绕现有少数仓库扩量 |

排序综合了证据、接入成本和补充覆盖，不是预测收益排行榜。OpenSWE gated 访问未解决、MiMo 有效正对照未建立时，均不能直接推进依赖它们的模型实验。此处不请求现在购买算力或接受条款。

### 固定预算的小试点建议（尚未执行）

**第一步先验证输入，不消耗模型 rollout。** 为 R2E、SWE-reBench、MiMo、SWE-smith 各列出 6 道候选，共 24 道，每源尽量覆盖至少 3 个仓库、每仓最多 2 道。SWE-reBench 六题可分 Uni 1150 和 Prime V2 各三，分别记录；不是把它们当同分布。MiMo 若有关键参考缺口，本批不硬补人数；预先固定一次替补规则或缩小批次。OpenSWE 是访问就绪后的替换来源，不自动追加预算。

逐题冻结模型可见材料、镜像 digest、任务/原仓库身份、参考补丁、测试命令和评分版本。先验证 no-op 不能被误收、有效参考能被接受、必要行为与回归测试确实覆盖需求；对不稳定迹象做针对性重复。这只是拟议试点的输入要求，本报告没有替题目做准入。

**第二步是 96 次配对探针，最多加至 128 次。** 24 题×2 模型×2 独立尝试＝96。事先从每源选 2 题，共 8 题；这些题每模型再加 2 次，总共再 32 次。重复对象按仓库、语言、任务类型预先选定，不能见到失败后反复跑到成功。来源缩小时等比例减少预算，不挪为无上限重试。

建议优先复用当前已验的 Claude Code＋RH2 普通探针配置；若需为新试点立数值基线，可用以下**待定提案**：128K context、每条轨迹累计最多 64K 生成 token、最多 100 次模型请求、求解 30 分钟。这里 64K 是整条轨迹上限，不是 PACT 的每 turn 上限；工具执行计入 wall time，评分单独设上限并登记参考运行时长。该配置要先确认 RH2 当前预算实现能准确计数，再冻结，不能在报告中当作已落地能力。

Coder 保持官方非 thinking；Qwen3.6 固定 thinking 设置并单独报告其 token/time 成本。相同外部预算不意味着完全相同推理策略。固定采样参数、seed（若服务支持）、服务版本、精度、harness 版本和工具权限；记录达到哪项预算上限。多调用/并行工具也计入预算，不靠调用方式绕开上限。

**试点回答“有没有可信、可负担的能力信号”，不回答最终训练收益。** 每题保留全部尝试，输出 reward、候选语义审计、异常归因、token、时间和环境成本。分别统计有效评分分母、基础设施异常、候选导致的运行失败、假阳性/假阴性和预算终止；不把 null 转 0 或删除后报高成功率。

每源只有 6 题、每模型每题 2–4 次，不足以估计稳定难度分布。全过、全错和混合成功用于下一轮分层线索；不能把“混合成功率约 50%”当唯一准入条件。持续全错但参考可靠的题可能需要 SFT/课程过渡；全过题也可能有工具效率或回归用途。最终要优化的是**单位完整成本下的可靠学习与保留集收益**。

真正验证“可训练”还需后续小训练对照：固定训练 task manifest，按仓库/基础版本隔离保留集，用同一 harness/预算比较起点与训练 checkpoint；训练曲线上升不能代替泛化提升。先比较成熟奖励/算法配方，再单独研究 KAT/PACT/ROSS 的算法改变，避免一次同时换数据、harness、奖励和预算而无法归因。涉及训练语义的具体实施仍按已有 T0 决策流程，本报告未发起变更。

### 现有 52 题如何继续用

这里仅引用 **2026-10-03 13:32 SGT** 的固定快照，不追认成当前实时状态：[analysis_summary.json](../../../../../runs/category2_repair_20260929/overnight_watch_20261003/difficulty_analysis_20261003/analysis_summary.json)。52＝SWE 34＋R2E 18；覆盖 28、未试 24；39 次尝试不等于 39 个有效语义判决。

| 固定快照 | Qwen3.6 | Coder |
| --- | ---: | ---: |
| 全部尝试：reward 1 / 0 / null | 22 / 4 / 0（26 次） | 7 / 4 / 2（13 次） |
| 共同 11 道 R2E：reward 1 / 0 / null | 9 / 2 / 0 | 5 / 4 / 2 |

配对题仅 5 仓库，按就绪顺序进入，非随机样本，没有配对 SWE。快照没有观察到预算截断，但这不消除不同采样/thinking、题面版本或评分遗漏的影响。

- **先关闭已知错误计分。** Qwen 的 Moto6114 原 reward 1 候选存在 Neptune 回归，另一次 CPU 诊断已确认；Pydantic6283 有 PrivateAttr 回归与 v2 控制证据，但原 GPU FrozenPatch 尚未实际按 v2 重评；Coder 的 aio1c1 清理行为回归仍在验证。三者不能直接计入“模型正确通过”。
- **保留原始异常。** Coder 的 aio6183/aio240d 两次 null 被归因为候选撤回兼容改动后产生 SyntaxError；它们是有价值的端到端行为失败，不能静默丢掉或改成正式 reward 0。coverageEA69 的旧题面漏了公开要求，旧失败不能作干净难度证据。
- **保留有区分度的题。** Pillow3a61/a682 在快照上 Qwen1、Coder0，适合在语义和版本收口后保留为配对观察；Pillow2d01、NumPy d805 两者均0，先归因，不能仅凭全错称高质量难题。
- **减少无新增问题的重复修补与探针。** 未试题首次覆盖通常比易题的第三、第四次同版本运行更有信息；只在已验、不同仓库的固定小子集上补缺失模型臂或重复。可靠易题进入冒烟/回归候选，训练资格另行判定。
- **不撤销既有 52 题安排。** 继续遵守[当前剩余工作方案](../category2_repair_20260929/remaining_workflow_20261002.md)中的版本绑定、独立核查和“一版修订＋一次定向修正”的投入检查点；它不是 CPU 自动放行线或模型 token 预算。此调查未停队列、移交题目、改变评分或缩减已授权工作。

## D. 溯源、未解问题与自查

### 本轮实际修正的认识

| 原线索或容易混淆的说法 | 本轮可支持的表述 |
| --- | --- |
| “Qwen3.6 太强，没什么可训” | 同 checkpoint 已有 KAT、PACT、ROSS 正向对照；RH2 上是否值得训仍需可靠任务与小训练验证。 |
| “R2E 对 Coder 有用” | 至少 Uni/RTMC 支持，但子集、harness、度量与预算要分别看，不能照搬收益数值。 |
| “MiMo 只有约 3k 的口头承诺” | 当前 code 2,698 行与映射可定位，六个镜像标签可查；参考修复和 RH2 可运行性仍未闭环。 |
| “SWE-smith 只有 Python 50,137” | 这是论文历史口径；当前分语言资产另有 Python/Go/TS 等，数量与旧总仓不可相加。 |
| “Uni 1150 和 Prime V2 是同一配方” | 两个不同发布物、不同筛选与版本；外部效果证据不能转移。 |
| “CodeMidas 5,545 就是 MiMo 开源题” | 目前无任务级对应证据；保留为独立构造路线。 |

仍缺的关键证据：作者精确 training manifests 与历史模型权重 hash；多数实验的重复数/方差与 GPU-hours；MiMo 的参考修复和完整仓库身份；Prime registry 在我方环境的实际运输；OpenSWE gated 许可/文件内容；两模型在新增来源上的真实难度和训练迁移收益。未定位不是证明不存在，检索截止日为本页日期。

复用的本地入口包括 [基座探针设计](../base_model_probe_design_20260921.md)、[精读索引](../../../../harness_improve/external_paper_references/reading_notes/README.md)、[来源目录](../../../../harness_improve/external_paper_references/reading_notes/SOURCE_CATALOG.md)及 R2E、SWE-smith、SWE-reBench v2、Qwen3-Coder-Next、MiMo 既有笔记。新网页版本和资产事实均记在 evidence；旧笔记未回写。

作者自查：确切 checkpoint 与邻近模型分开；RL/SFT/蒸馏阶段分开；多数票、单次、avg@k 和测试时选择分开；纸面数量、可定位资产、少量抽查、运行复现分开；本地 raw reward 与语义正确分开。完成 JSON、来源 ID、数字与本地链接一致性检查。本报告为单人研究与自查，**没有声称另有独立审查或复现**。
