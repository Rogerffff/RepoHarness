# B 阅读切片：长程训练、系统与任务选择的关系

日期：2026-09-08。阅读基线为 RepoHarness `ac0e2e64163fbe49411540e901df439aea16b6b0`。本稿由 B 主线程完整阅读以下六份既有精读稿及对应检查记录后整理；没有再次全面核验原论文、上游实现或运行实验。来源各自的原文覆盖与未验证项继续有效。

## 1. 阅读范围

以下文件均从首行读到文件末尾，包含非 SWE 训练案例、负结果、资产、作者自查与项目映射。旧稿只作为历史问题线索，不反向补充论文缺项。

| 既有笔记 | 完整行范围 | 同时读完的检查记录 | 对 B 的主要用途 |
| --- | --- | --- | --- |
| [O01 SkyRL-Agent][O01] | 1–431 | `15_O01_self_check_20260907.md`、`15_O01_codex_quality_review_20260907.md` | SWE 直接 RL、工具增强、分阶段供给、horizon 与评测迁移 |
| [N11 miles][N11] | 1–323 | `05_N11_review.md` | 实际样本单位、Harbor 接入边界、失败结果、评测运输与成本 |
| [E10 Intern-S2][E10] | 1–463 | `10_E10_review.md` | task × harness、来源资产与消费量、两专家到 OPD、失败归因 |
| [N10 MiniMax Forge][N10] | 1–198 | `09_R4_N10_review.md`，含 R4 的相关审查 | 调度改变任务分布的可能性、吞吐与质量的共同口径 |
| [R14 CompactionRL][R14] | 1–507 | `14_R14_self_check_20260907.md` | 摘要训练与评测机制、长轨迹分段、不开压缩的退化 |
| [R15 SAO][R15] | 1–474 | `13_R15_self_check_20260907.md` | 采样组织、critic 代价、对照单位、SWE 配方披露上限 |

检查记录均位于精读库 `reading_notes/reviews/`。N11、E10、N10 有既有独立审查；O01 有 Codex 定点质量复核；R14/R15 只有作者自查。本轮是文献笔记整合，不统一升级它们的审查等级。

## 2. 六篇材料分别说明什么

### O01：先区分“运行慢”和“模型找不到成功路径”

笔记 §4–6 恢复了 Qwen3-32B 在 4.5K R2E-Gym 上直接 RL 的案例：训练加 AST 搜索与错误恢复提示，Simple ReAct 评测为 24.4%→39.4%。训练限制为 32K/50 turns，评测为 40K/100 steps；这是 dense 32B、指定工具和预算下的结果，不能代替我们 MoE 基座在 Claude Code 下的诊断。AST 撤除评测支持一定迁移，但没有完整隔离 AST、提示和调度各自的收益。

§3 的 1.55× 来自 Init/Run/Eval 流水线的 generation 阶段对照，SWE 更新仍 fully on-policy。B 应提供环境初始化、工具与评分的时延和失败分布；A 判断现有队列与上游能力如何调优。不能先假定换异步算法才能改善效率。

§5 的 horizon masking 保留原组 reward/advantage，只屏蔽样本自身梯度。这个例子要求 B 把“任务失败、预算停止、环境异常、评分无结果”讲清楚；随后由 A 按已批准算法处理组成员和分母，不能把论文规则直接移入本项目。§7 的三个独立案例还保留了 judge 敏感性、工具供给污染和 GUI 验证不改善；“支持多任务”不等于同一模型多域混训成功。

§8 是后发代码的静态检查。既有 Codex 复核指出：messages 路径先缓存 `finish_reason_list`，随后改字典的错误原因不自动回填列表。当前正文尚未加入这项限定；本稿引用 mask 行为时连同该复核理解，不声称所有后识别错误都会被清零。它不影响上述论文级 SWE 与调度结论。

### N11：样本运输正确与任务可评分是两件事

§3–6 区分逻辑 execution、重试分支、训练 leaf 和 action token。树中有多条叶、每叶复制 reward，不表示采到了多条独立执行；`response_length` 也可能包含工具观察增量。B 记录基座行为与学习机会时，分母应是任务和实际尝试，不能用训练段数充当尝试数。

§4 的 Harbor 转换器是格式接入，没有替我们验收题意、测试隔离、镜像和 parser。示例可能在 agent 错误后仍收集已有 token，并把缺 reward 与真正失败归入同一个默认 0；这只是所查版本的具体路径，不是推荐语义。B 需要保留评分原始状态和可复核工件，避免把“得了 0 分”当成已确认模型失败。

§5 的 OPD 能力也有版本和接线条件：v2 预填 scalar reward 可能跳过 teacher RM；student-side top-k 与当前 fully-async 参数组合受限。全失败的 GRPO 组仍可能包含蒸馏信号，因此“当前组无相对奖励差”不应被永久写成数据无价值。是否采用 OPD 属后续训练选择。

§7 的 shared engines、dedicated fleet、external checkpoint eval 有不同 GPU、同步、存储与排队成本。B 先定义评测题单、预算、指标与频率，A 再落实所用 checkpoint 和运输；外部 eval 没预留 GPU 不等于没有外部费用。上游 8 H200 示例没有给本项目成本或独立学习保证。

### E10：任务资产清单和真实训练消费量不能混在一起

§3、§6 的完整路线是同一 SFT 分出 reasoning/agentic experts，再生成 warmup 轨迹并做 OPD；并非所有项目都需要多专家。397B 主模型、35B 局部实验和其他独立模型也不能按名称合并。

§5 按 task × harness 描述 agent 数据。Table 1 七来源的 task/environment 数是库存口径，不能求和后称为独立有效训练题，更不能据此恢复最终混合比例。接口适配、私有材料隔离、执行与评分错误分类、离线 SFT 错误步骤 mask、在线正优势过程惩罚各有职责；它们不是一个通用“坏轨迹删除”按钮。

对 B 最有用的是来源表和任务合约的组织方式：记录来源版本、题面与评分材料、可见性、依赖和反馈。完整的技能图合成与细域专家训练可留作研究线索。原文没有给足合成产率、等成本消融和精确消费漏斗，现阶段不足以支持我们复制整套工厂。

§8 的成绩须与 harness 和预算一起引用：例如 Terminal-Bench 2.1、Terminus 2 与 SWE-Pro 的定制镜像是不同评测面。完整阅读也保留 memory/时序负结果；它们不要求项目一扩展到科学、多模态或长期记忆。

### N10：吞吐改变时，要检查到底训练了哪些任务

§4 的 Forge 消费窗口限制原始派发队列中的可消费范围，与当前 miles 按完成入池顺序 FIFO 不同。短任务先完成，固定训练时间下便可能占更大消费份额；是否最终都能进入 learner，不能回答早期训练分布是否改变。

因此 B 要分开记录任务机制、基座难度和运行成本。运行很慢的题可能只是依赖安装昂贵；较快的题也可能需要困难推理。A 提供派发、完成、丢弃、消费事件后，B 才能按任务族与耗时对照分布。这是项目假设与建议，不是本轮已经测出偏差。

§5 的前缀树最高量级加速不等于端到端训练加速，计算复用也不等于重复 token 的 loss 权重已保持。§6 的 speed reward 没有充分披露系数与质量取舍；现阶段先记录工具、子 agent 和推理成本，再决定是否把速度写进 reward。

### R14：长程能力必须连同评测机制一起解释

§7 给出有辨识度的训练 × 评测矩阵。GLM-4.7-Flash（30B-A3B）的 CompactionRL 在 compacted SWE 为 56.0%，同机制输入基线为 50.5%，增量为 +5.5 个百分点；不开压缩时训练模型为 43.7%，输入模型为 47.5%。另外一些普通长窗口 RL 对照在特定格子更好。不能只保留训练后最高一格，声称所有真实仓库任务都提升。

该论文使用随机 200 题 SWE 子集，不能称全 500 题 Verified；两次 evaluation 均值不是 pass@2。相同 peak context 也不是等生成 token、FLOPs 或费用：摘要和反复 prefill 都消耗预算。B 应先测真实 Claude Code 中有多少题触发 compaction、触发前后失败是什么；确有需要，再设计固定任务的上下文机制对照。

§4–5 区分首次采样摘要与后续复制摘要、一个 execution 与多个训练段。全局 token 分母消除固定 token 项的人为切段计数效应，却不让每题等权；跨段 GAE 是近似。相关实现归 A 的训练边界，不因“任务长”自动批准 critic、SAO 或摘要 loss。

§3 的 SWE-Dev 只是来源名称，具体 manifest、镜像、训练题数未恢复；106B 分支有额外 SFT，训练硬件和总费用未知。它不能当作现成八卡环境生产配方。

### R15：算法对照不能掩盖任务覆盖和计算量差别

§6 的 SWE 分数为 23.0→GRPO+DIS 27.0→SAO 29.8。SAO 相对稳定化对照是 +2.8 个百分点；SWE 没有独立 critic 消融和成本表。OpenHands 的 300 turns/128K 属 benchmark 条件，不证明训练具有相同接线。数学的长曲线、消融和写作偏好模拟不是 SWE 训练配方，写作分支还存在第一阶段 running mean 更高的反例。

每批 128 条轨迹在 SAO 是 128 个 prompt 抽样位置，在 GRPO 对照是 16×8；同时增加 critic 及更新，不能称为等 prompt 覆盖或等算力。B 在未来比较采样策略时至少要保留题目覆盖、尝试、action token、实际费用和独立质量，不能仅固定 batch 数。

§3、§8–9 未披露 SWE 任务来源、环境漏斗、完整 reward 和失败处置，也未给系统墙钟结果。DIS 的 detach/分母和部分 value 细节仍缺；不能用本项目 faithful DIS 反填原文。现在它帮助我们提出正确对照问题，不决定先换算法或采哪些仓库。

## 3. 对 B 首轮计划的共同约束

1. **决定要证明的能力和目标使用方式，再选诊断任务。** 先能解释真实 Claude Code 中一次任务的结果，才有依据说成功稀缺是模型、接口、环境还是预算问题。
2. **先留住可解释的完整执行事实。** 任务、attempt、生成请求、评分结果、结束原因与成本能够关联即可；训练分段、组准入和 learner 计权交 A 落实，不再建设第二套事件治理平台。
3. **固定对照中的模型、harness、grader 和预算。** 改工具、提示、上下文、评分规则或重试策略都可能改变任务难度或有效执行量；变化需单列，不能自动归为权重收益。
4. **按整个闭环计量效率。** 环境供给、初始化、评分、失败重试、推理、训练、评测分别计量；GPU utilization、step 时间、有效样本吞吐和达到指定质量的成本不能互相代替。
5. **保留简单训练候选与反事实。** 当前材料没有要求首轮同时实现 terminal 混训、动态课程、OPD、critic、可训练 compaction、多 harness。先用基座诊断找到确切缺口，再挑一个值得花预算验证的改动。

[O01]: ../../../../harness_improve/external_paper_references/reading_notes/O01_skyrl_agent_sa_swe.md
[N11]: ../../../../harness_improve/external_paper_references/reading_notes/N11_miles_agentic_rollout.md
[E10]: ../../../../harness_improve/external_paper_references/reading_notes/E10_intern_s2_preview.md
[N10]: ../../../../harness_improve/external_paper_references/reading_notes/N10_minimax_forge.md
[R14]: ../../../../harness_improve/external_paper_references/reading_notes/R14_compaction_rl.md
[R15]: ../../../../harness_improve/external_paper_references/reading_notes/R15_single_rollout_asynchronous_optimization.md
