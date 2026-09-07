# 07 / R2 Nemotron 3 Ultra 独立审查

审查日期：2026-09-07。结论：固定初稿未发现重大训练语义错误或整块后训练主题遗漏；有一处应收紧的事实表述（F1）。独立来源审查已完成；作者已于2026-09-07完成F1修订，具体处置见§6。

## 1. 身份、版本与方法

- 主任务：`01a07827-1e2f-78c3-8c14-1d222dda34c7`；实际 `gpt-6-astra / high`（主作者已核本地 session）。
- 审查子任务：`01a0782d-89ca-7723-ac6f-947eb979e7d7`；agent path `/root/r2_independent_review`；实际 `gpt-6-astra / high`。审查者直接读取自身 session 的 `session_meta` / `turn_context`，确认 UUID、父任务关系、model 与 effort。按本任务授权以干净上下文创建；未递归派出 agent。
- 来源：NVIDIA，*Nemotron 3 Ultra: Open, Efficient Mixture-of-Experts Hybrid Mamba-Transformer Model for Agentic Reasoning*，封面 2026-06-09，65 页；[官方 PDF](https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf)。本次直接读取指定本地原 PDF；线上同版 `cmp` 结果由主作者提供，不冒称审查者重复下载验证。
- 固定被审版本：[R2_nemotron_3_ultra_draft_20260907.md](../sources/R2/R2_nemotron_3_ultra_draft_20260907.md)，385 行。它是将来 `R2_nemotron_3_ultra.md` 的冻结内容副本；其中相对链接按最终笔记所在目录解释。未修改冻结副本或正文。
- 先从原文标题、章节与唯一附录建立以下覆盖，读完全部 §3 和附录后才打开初稿逐项比较；相关 §2/4/5 亦单独核对。PDF 页码均为物理页，等于该报告印刷页；通过 `pdftotext -f/-l` 按物理页提取，没有用全文中的 formfeed 个数推页码。
- 关键图形/公式回原始渲染页目视：p.2 图1、p.21 图10及式1–2、p.22 式3与 SWE 段、p.30 式4及表6、p.65 图17。其他表格以原 PDF 按页提取的完整表、表注与相邻正文交叉核查。
- 公共任务、模板、第一批质量报告已读。项目映射仅核 09-05 简报、09-07 项目一建议相关段与 `rh2/src/repoharness2/adapters/miles/group_admission.py` 的职责说明；没有全仓审计、训练运行或复现实验。

## 2. 独立覆盖结果

| 原文范围 | 从原文独立检查的内容 | 初稿对应与结论 |
|---|---|---|
| §3、§3.1，p.15–20 | 学生两阶段 SFT；long context、efficiency/control、安全、搜索、terminal、会话工具、SWE、数学/证明、science、chat、competitive code、CUDA、RTL、多语言；packing | §3.1–3.2 全覆盖；包括 chat 只训最后回应、截断 `</think>` mask、两条不同翻译流程；F1 为小幅证据收紧 |
| §3.2，p.20 | 统一 RLVR 全领域、profiling、Gaussian curriculum、异步 GRPO、batch/rollout/长度 | §3.1/3.3/5 覆盖；未把引用 Super 等同已披露完整 Ultra 算法 |
| §3.3.1–2，p.20–26 | 三 policy 与 sampled-token MOPD；全部 11 类 teacher；SWE/PivotRL、office、search、terminal、工具、usability、agentic safety、chat/GenRM、IF/factuality、STEM、competitive coding | §4–5 全覆盖；STEM 全部制数、40B token mixture、非 STEM RL 已核，无用 SWE 重点替代其他领域的问题 |
| §3.3.3–5，p.27–29 | warmup、两轮 teacher recovery、解释边界、logit matching 负结果、未做的 SFT foundations、长程 MOPD 低效与多数单轮 rollout | §6 全覆盖；区分未系统实验与实验无收益 |
| §3.4–5，p.29–31 | MTP 训练/推理状态不一致、冻结主干、forward KL 与分母、acceptance length；三种推理模式及 medium 奖励长度调整 | §5.3/3.3 覆盖；MOPD 与 MTP 的 KL 方向、分布粒度没有混淆 |
| §3.6.1–3，p.31–36 | MTP 加速、one-step async、故障构成、Slurm/Ray、拓扑/NUMA、checkpoint、JIT、vLLM、存储；future work | §7.1–7.2 全覆盖；局部速度与全训练成本分开，未来恢复功能未写成已完成 |
| §3.7.1–3，p.36–40 | 全套 agentic/推理知识/IF/长文/多语言评测；模型卡采样参数；held-out gates；数学 generate–verify–refine | §8 全覆盖；关键成绩保留任务、单位、预算、版本和最终/中间 checkpoint 区别 |
| A.1–2，p.64–65 | TauBench、ProfBench、BrowseComp、FAB 具体协议；五任务类别、至少两种训练 harness；跨 harness 图17 | §8.2 全覆盖；所有 Ultra 图像数值已逐项对读，图17未被误解成多 harness 训练的因果消融 |
| 相关 §2，p.3–14 | 架构/MTP、预训练数据、LC、两次发散与 routing 指标 | §2 准确概要；Nano/家族底座消融未冒充 Ultra 后训练收益 |
| §4.1–6、§5.1–2，p.41–51 | BPE/scale/cache/Hopper 负结果、PTQ 资源、精度与引擎、不同服务工作点、Mamba state、并行/PD/all-to-all/chunking/padding | §7.3–7.4/8.3/9 覆盖；Super 仿真缓存实验没有写成 Ultra 已发布方案 |

本篇报告没有另外隐藏的后训练附录；p.51–63 为结论、贡献者和参考文献区域，p.64–65 为唯一附录 A。未把每篇被引论文都纳入独立精读，也未用它们的默认参数补 Ultra 未披露项。

## 3. 八组关键核验

1. **模型关系准确。** 图10目视确认 coding teacher 的实线来自 STEM teacher；chat2、conversational-tool2、SWE2、office2 来自 MOPD1。p.26 competitive coding 文字也明确从 General Reasoning Teacher 继续 RL。p.23 office 初始化为完成 general SFT 的 Ultra。初稿保留概览图/概述与细节差异，未强制所有教师都从同一个 checkpoint 分叉。DeepSeek-V4-Pro 数据生成者也没有被混成在线 Ultra STEM teacher。
2. **公式、概率身份及分母准确。** 式1 为学生轨迹上的负 reverse KL；式2 的 advantage 是 stop-gradient 的 teacher 减 proximal logprob；式3 的 `c=prox/behav` 与 `r=current/prox` 分开，PPO clip 作用于后者，IcePop 为 `m_t`。印刷目标是 token sum 后取 expectation，没有 `1/H`，不能直接证明代码实际 normalization。式4 确认为 `KL(backbone || MTP)`、full distribution、`T²/(N_mtp|A|)`，T=2、N=7；初稿重写与原公式一致。
3. **预算与失败处置没有过度外推。** SFT 两阶段的长度/样本/LR/warmup，MOPD 1024 prompts×1、192K，SWE 192K/200 turns，MTP 12K steps/batch64/8K 均核对。§3.2 的 8192 原措辞与 STEM 128 prompts/global batch2048 的旁证并存，初稿保留单位歧义合理。p.22 未完成 loss mask 仅明列 max turns 或 agent/eval timeout；负 advantage 仅指 offending reasoning/tool tokens；group 统计、补采及通用 role mask 未给。初稿没有把这些空白填成确定规则。
4. **全域数据数字和训练领域正确。** 安全 135K、商业许可 OpenResearcher 21.7K、terminal 370K conversations、数学 1.8M/1.9M、code 1.2M/1.0M/1.3M、CUDA约100K、RTL约1.2M 单位不混。STEM 的 95,164 数学题、545,431 COT/TIR、5,751 proof 题/82,737 samples、40B generated tokens 四类配额、3,000题内部评测与 coding 3.5K 难题均吻合。语法/格式过滤没有升级为全部语义正确性证明。
5. **消融和负结果准确。** 表4 Warmup 为 warmup 后 MOPD 的结果；表5 recovery 的分母是 teacher−RLVR。HLE 16.9%、Terminal 172.7% 与表定义一致；LCB MOPD1→2 90→89、GDPVal持平、IMO SFT→RLVR下降都保留。teacher-support 解释标为作者解释，full/top-k matching 不佳没有推广为普遍定律，未系统评估 foundations 没有写成失败。
6. **系统速度和成本分母准确。** 图12 1.46×为 RLVR 平均每步 rollout generation；图16 2.89×为 BS1 的特定推理工作点。56/36/8 是软件故障内部构成。+20% 拓扑/+10% NUMA、checkpoint 暴露阻塞和 JIT 初始化均各自限定。表9组件合计38.4但总值38.8、表15正文42min/表45min均确为源内差异。p.1直接给5.9×/4.8×/1.6×，图1另提供引擎与测量条件；不应单凭图中四舍五入柱高重新改4.8×。
7. **评测与 harness 证据边界准确。** A.1 的 ProfBench 256K/无context management/16次，Tau用户GPT-5.2 low/8 trials，FAB 200 validation题而非337私有test、三次judge取mode均吻合。图17 Ultra SWE一行65.0/67.3/70.4/60.3/69.9/70.3/21.1/avg60.6，Terminal55.1/46.7/52.1/47.2/52.8/52.6/35.5/avg48.9逐项通过。表5 TB2.0与主表2.1、SWE71.7与70.7、图17另有差值均未擅自合并。数学173/210等为graded score，128起始证明尝试不是pass@1。
8. **旧稿纠错和项目边界有依据。** 对读旧《重定位审核》§2.3/T3与配方矩阵§7.2，确有 routing/top-p replay 归因及“不修改 provenance loss mask”的原句；本版 Ultra §3.6不支持前者，p.22不支持后者。初稿正确撤回过强结论，并保留 teacher sampled-token logprob、profiling、多 harness 等有来源事实。项目映射把 consume-time staleness 裁决留给 miles，符合所核 `group_admission.py` 注释；没有把 NeMo 通用优化升级成 rh2 必造组件。

## 4. 实际发现与修订建议

### F1（小修，事实限定）：安全生成的两阶段没有在本篇明确排序

- 初稿位置：§3.2 Safety 表格，冻结稿第72行，写“先回应/后推理的两阶段构造”。
- 原文依据：p.16 §3.1.1 Safety 称“two-stage response and reasoning generation framework”，随后说明 reasoning trace 会反思安全规范、final response 要一致且合规。这段没有显式写先生成 response、再生成 reasoning。
- 问题：初稿将英文并列顺序变成了确定的数据生成时序。本审查不能断言该顺序实际上错误；结论是它超出了本篇已读证据。报告引用 Super 也不能代替本次对相应外部段落的实际核查。
- 建议：改成“回应与推理的两阶段生成”，保留其安全反思与最终回应一致性的功能。如确需保留先后顺序，须另给已实际阅读、明确说明顺序的来源定位。
- 其他 safety 数量、翻译工具、阈值、过滤比例和语言均无修订需求。

没有为了凑发现数而将作者原有的已披露边界、合理精简或印刷数值差异列成初稿错误。没有发现需要新增整节后训练内容的遗漏。

## 5. 资产检查与剩余限制

审查者另读主作者补充的 HF metadata 快照及 Evaluator reproducibility 快照。四模型 public/non-gated 与各自 SHA 在 metadata 中可查，可由作者补到资产栏；这属于固定初稿之后的新查阅证据，不是冻结初稿错误。Evaluator 当前 v0.2/v0.3、Tau2与“Tau Bench 3未onboarded”并存、terminal Hard/2.0 等描述，初稿对当前入口和报告版本的区分准确。审查者没有独立在线验证这些快照，也未下载权重、检查许可证全文或运行配置。

来源仍不足以回答：SWE 环境/任务漏斗、完整训练 GPU-hour、失败样本 group 统计和补采、实际 loss normalization、IcePop阈值与完整 role/pivot/context-reset mask、精确 teacher 冻结规则、版本发布与消费协议、全套最终评测预算和生产配置。这些空白不是本轮遗漏；初稿已按相关正文与附录的实际披露范围处理。

## 6. 作者修订回填

2026-09-07，主作者收到真实审查结果后修订：

| 发现/补充 | 处置及证据 | 状态 |
|---|---|---|
| F1 安全生成顺序超出本篇披露 | [最终笔记](../R2_nemotron_3_ultra.md) §3.2 Safety由“先回应/后推理”改为“回应与推理的两阶段生成，使安全反思与最终回应保持一致”；依据p.16原段，未引入未读Super细节 | 已修订，主作者回读原段并检查差异；无需再作独立全文复审 |
| 审查期间新增资产证据 | 正文§9加入四模型HF public/non-gated及metadata revision链接，许可证仍只写metadata标签，保留未读全文边界 | 已补充；不改变论文训练事实 |
| 项目代码引用精确性 | 正文§11首次提DefaultDataBuffer.get时补 `reference/miles-rh2-integration/miles/rollout/fully_async_data_buffer.py`，主作者实际读get实现并沿用integration commit | 已补充；没有修改代码或扩大审计 |

固定初稿保持原385行未变；本节记录的是作者处置，不冒称审查者又逐句复核修订稿。作者完成最终正文、审查和来源说明的本地文件/导航链接、格式与授权写入范围检查后，将专属成品发布回主资料目录同相对位置。

发布核验（2026-09-07）：最终正文、审查、来源说明三份Markdown共32个本地文件链接/导航锚点已通过检查，无格式诊断或本机绝对路径。固定初稿385行保持原样，F1只修改最终正文。已按授权发布 `R2_nemotron_3_ultra.md`、`reviews/07_R2_review.md` 与 `sources/R2/` 到主资料目录同路径；未修改共享索引或其他任务成果。
