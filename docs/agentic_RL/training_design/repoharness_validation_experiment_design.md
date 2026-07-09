# RepoHarness 验证实验设计（决策底稿）

本文是 `repo_harness_final_review_before_implementation.md` §5.1-D5 与 §6.3 定案的独立实验设计文档。当前处于**决策底稿阶段**：先列出全部待决事项与依赖关系，用技术报告调查校准候选项，再逐项定案。定稿后本文回答一个问题：**用什么最小可信实验证明 RepoHarness 这套环境与训练治理设施有效**。

与其他文档的关系：

- 基础设施范围与治理定案：`docs/harness_improve/repo_harness_final_review_before_implementation.md`（§3 范围、§5.1 D1~D7、§6 算法无关接口与在线 Anti-Hack）。
- 主架构：`docs/harness_improve/repo_harness_design_doc2_verifiers_based.md`。
- warm-start / 离线数据过滤：`docs/agentic_RL/training_design/warm_start_offline_data_filtering_design.md`。

时间基线：2026-07。S0 退出条件包含本文初稿完成（§6.3 定案）。

> **[S0-8 收口 2026-07-08]** S0 实测结论（V2/V3/V4，见 `../repo_harness_rh2_workstreams/s0/` 各报告）已回填本文：E1/E7/E10 已定案（落 §4.1），硬约束 C1/C2 按实测修正；其余 E 项（E2/E3/E4/E5/E6/E8/E9）的"定案"栏仍待用户拍板，其中哪些必须在 S1 冻结题单前定，见 `../repo_harness_rh2_workstreams/s0/s0_8_expdesign_review.md`。
>
> **[P3 收口 2026-07-09]** 八卡预实验实测结论已回填本文（落 §4.2）：训练侧四项未知关闭、放置定案 T3 分离（废弃 C1"必须 colocate"旧推论）、E6 墙钟表实测校准（整 step 23min，rollout-bound）、新增 batch schedule alignment 独立验收项。判定依据见 `../repo_harness_rh2_workstreams/preflight/preflight_report.md`。

---

## 1. 硬约束框架（先于一切调查，待项目所有者填写）

实验设计的根约束，技术报告无法替我们回答：

```text
C1 算力形态（2026-07 已填；[S0-8 收口 2026-07-08] 按 S0 实测修正）：
   训练目标形态 = 单机 8 × RTX Pro 6000 Blackwell 工作站卡，
   单卡 96GB，合计 768GB；PCIe 互联、无 NVLink。
   S0 实测口径：8 卡整机当期缺货，S0-5/6/7 以同型号单卡（96GB，sm_120）
   完成推理侧验证——30B-A3B bf16 加载约 60GB，单卡余量充足、无需量化；
   训练侧（多卡通信、权重同步、colocate 显存、训练 step 墙钟）完全未验证，
   留 S4 前 8 卡专项预实验（见 §4.1 第 4 条）。
   直接推论：
   - ~~必须 --colocate（训推同卡）+ CPU offload~~
     [P3 收口 2026-07-09 修正]：放置定案 = T3 分离（4 训 + 4 推）
     + train_async 双缓冲 + CPU offload，colocate 废弃（依据见 §4.2 第 2 条）；
   - PCIe 互联下 EP/TP 通信显著慢于服务器卡（NVLink），
     MoE all-to-all 是吞吐风险点，宜低 EP 度 + 长序列摊薄通信；
   - 30B-A3B 档初步核算可行：bf16 权重 60GB + 梯度 60GB，
     Adam 优化器状态走 CPU offload，单卡余量支撑 32k 上下文训练
     （[S0-8 收口 2026-07-08] 权重侧已由单卡实测印证约 60GB；
     梯度/优化器侧仍是纸面核算，归 S4 前预实验）；
     35B-A3B 升级选项关闭，仅在 S4 前预实验证明富余时重议（E1 已定）；
   - S0 验证项 V5（本文自设，未进入 S0 执行计划的 V1~V4 清单）：
     [S0-8 收口 2026-07-08] 推理半边已由 S0-5/6 顺带消除——vLLM 0.24.0
     与 SGLang 0.5.9 在 sm_120 均可跑，但默认参数不可用，必须用
     §4.1 第 3 条的固定参数/固定镜像；训练半边（Megatron 内核、
     EP all-to-all over PCIe 实际带宽、FP8 KV）归并 U-C 训练侧，
     留 S4 前预实验；slime patch 镜像在 sm_120 的可用性 = U-H（留 S1）。
C2 货币预算上限：[S0-8 收口 2026-07-08] GPU 为租用形态、非自有
   （原稿"租卡为零（自有 8 卡）"与 S0 事实不符：执行计划即按租机设计，
   S0 因 8 卡缺货改租单卡完成验证，8 卡整机租用留 S4）——
   租机成本随墙钟计，与 C3/E6 的"首训 ≤4 天"直接挂钩；
   API 面主要是 LLM judge，judge 额度充足。
   —— 重要资源补充：codex / claude code agent 额度充足，
   可大规模用于离线数据流水线（环境构建、修复、质检、PR 抓取的 agent 化），
   这直接改变 E4 数据策略的可行域（自产任务成为现实选项）。
C3 时间预算：从 S1 冻结到出 before/after 结果的日历时间上限
   —— 待填。个人项目建议以"单次完整实验 ≤ 1 周墙钟"为设计目标。
C4 已定约束（继承前序定案，不再讨论）：
   - 训练目标为 MoE 模型（D3），slime 为首选在线后端
   - S1 基建冻结集 20~50 题（D2；正式训练集另定，见 E4）
   - 训练接口算法无关，PPO / GRPO 都必须可接（§6.1）
   - 任务成败判定（outcome reward component）唯一来源是
     clean grading + verifier（D7/H5）；过程惩罚只能作为独立
     reward component / token_penalty_spans（重定位 §16.11 规则），
     不得篡改 outcome 判定——精确落点澄清见 E6
```

---

## 2. 决策清单（E1~E10，带依赖关系）

每项格式：问题 / 依赖 / 当前候选与倾向 / 需要调查回答的子问题 / 定案（空待填）。

> 编号说明 [S0-8 收口 2026-07-08]：本节 E1~E10 是**实验层**编号（原标题笔误 "E1~E9" 已更正，E10 为后补的一等决策）。执行计划（`../repo_harness_rh2_workstreams/01-s0-execution-plan.md`）另有执行层 E 系列编号，两套相互独立；跨文档引用时请写明"实验层 E4"/"执行层 E4"，防止混淆。

### E1 训练目标模型具体型号 【根决策，依赖 C1】

- **问题**：选哪个开源 MoE 模型做训练目标。
- **依赖**：C1 算力；反过来牵动 V2（renderer 覆盖）、V4（routing 透传）、E6（上下文与显存预算）。
- **候选与倾向（2026-07 调查后更新）**：
  - **首选 `Qwen3-30B-A3B` 档 MoE**：ROME 用同底座（30B-A3B）在 SWE-bench Verified 做到 57.4%，Composer 2 用 Qwen3-Coder-30B-A3B 做小规模代理实验证明该档足以观测 RL 信号——个人可负担规模里先验最强。
  - `Qwen3.6-35B-A3B`（slime 官方示例模型，配置卡见附录 A）：端到端配置现成，但示例是 8 节点 64 GPU（TP2/CP8/EP8 才吃下 96k 上下文）；C1 不足时需按 E6 大幅降上下文换可行性。
  - GLM 系 MoE（Air 级）：同生态加分，开源尺寸与 renderer 覆盖待核（V2）。
- **调查结论**：前沿报告 RL 的激活参数下限是 3B（Qwen3-Coder-Next 80B-A3B），与 30B-A3B/35B-A3B 同档——**3B 激活是有背书的下限，再小无任何先验**。slime 示例卡型未披露；显存需求由上下文长度主导（`max-tokens-per-gpu = context/CP`），上下文是第一可行性杠杆。
- **定案 [S0-8 收口 2026-07-08]**：**Qwen3-30B-A3B，32k 上下文起步**。S0 实测三项支撑：V2 通过——renderers `MODEL_RENDERER_MAP` 精确注册 `"Qwen/Qwen3-30B-A3B" → Qwen3Renderer`（hand-coded，非 DefaultRenderer），12 项渲染一致性 + 12 项 bridge 语义逐 token 实测通过，MoE 与 dense 共用同一渲染路径（chat template sha256 与 8B 一致）；V3 通过——单卡 96GB 上 bf16 加载约 60GB，token-in/out、logprobs 逐位对齐、Trace token identity 全链成立；V4 通过——routing tape 实测可透传。35B-A3B 升级选项关闭，仅在 S4 前 8 卡训练侧预实验证明显存/吞吐富余时重议。**随定案落地的守门要求（U-G）**：renderers 按 `tokenizer.name_or_path` 精确匹配注册表，用本地权重目录（如 `/models/Qwen3-30B-A3B`）加载会**静默降级 DefaultRenderer**（只打一条 INFO，bridge 恒 None、`sampled_mask` 全空，token 保真整体失效）——一切训练/评测脚本必须用 HF id 加载 tokenizer 或显式传 `Qwen3RendererConfig()`，并在启动时断言 `type(renderer).__name__ == "Qwen3Renderer"`。

### E2 算法族与后端配置 【依赖 E1、C1】

- **问题**：PPO with critic 还是 GRPO 起步；critic 的额外显存/卡数是否可承受。
- **依赖**：C1（critic 约多一份模型显存）、E6（轨迹长度——GLM-5.2 因 compaction 长轨迹弃 GRPO 改 PPO，但我们第一版任务较短且建议关 compaction，组语义可能仍成立）。
- **调查结论（一致性极高）**：GRPO 系是绝对主流——slime 示例（`--advantage-estimator grpo`、KL/熵全关、非对称 clip 0.2/0.28）、GLM-5（GRPO+IcePop，β=2、ε_low=0.2、ε_high=0.28）、Composer 2（Dr. GRPO：去长度归一、不除组 std）、MAI（GRPO+自适应熵+outer clip）、Nemotron（异步 GRPO，组 16）。唯一弃 GRPO 改 critic-PPO 的是 GLM-5.2，触发条件是 compaction 切碎超长轨迹——首版关 compaction 不触发。组尺寸锚点：slime 示例 8、Nemotron 16、GLM-5 reasoning 32、MAI 128（机构规模）。zero-advantage 标准处理：MAI early-exit（先采 16 估 pass-rate，[0.05,0.8] 内才补满）+ 组过滤 [0.1,0.8]。
- **定案建议**：GRPO；n=8；clip 0.2/0.28、KL/熵关、lr 1e-6 常数全部沿用 slime 示例初值；**"关 compaction ↔ 用 GRPO"绑定写入**——未来开 compaction 必须同步评估切 PPO（接口已算法无关，§6.1 的价值就在此）。**训练 rollout top_p = 0.95（2026-07-07 第四轮补定案建议，回应 S0-8 遗留）**：全部前沿配方与评测协议都在 0.95~0.97，训练用 1.0 偏离所有参照系并造成训练/评测采样错配；代价是激活 top-p tape 硬依赖 ⇒ **U-H（slime patch 镜像在 sm_120 可用性）升级为 S1 硬阻塞项**，回退梯按 E7 定案执行（手动打 patch → 临时 top_p=1.0 并在报告标注偏离 → 切形态 A 放弃 top-p replay）。
- **同规模公开配置锚点（线程 6 已核实）**：SkyRL-Agent SA-SWE-32B（2×8 H100、Qwen3-32B、R2E-Gym 4.5K 题）的确切配置：**group=8、train batch=64、lr=1e-6、KL/熵全关、advantage 不除 std、不做长度归一、超 context/step 轨迹 mask loss、32K 上下文、50 turns 上限**——与本文 E2/E6 定案几乎逐项重合，是"数十卡 SWE RL"的直接同款参照。DeepSWE（64×H100、6 天、同数据、Qwen3-32B）的 GRPO++ 配方同款，另加 Leave-One-Out advantage 与 Compact Filtering（超时/触顶轨迹 mask loss）。
- **slime 默认与该配方的三处差距（首训必须显式配置，不能用默认）**：slime 默认**除 std**（Dr.GRPO 去 std 需显式开 `--disable-grpo-std-normalization`）；默认对称 clip（clip-high 0.28 在示例脚本已显式开，核对即可）；**动态采样默认关**（需 `--dynamic-sampling-filter-path` 挂 `check_reward_nonzero_std` + `--over-sampling-batch-size`）。有报告标准 GRPO 中 58.77% 的训练步会产生零方差组——小任务集下动态采样不是可选项，**从"触发式"升级为首训默认开**。
- **其余稳定性预案（保持触发式）**：

```text
T1 动态采样开启后零方差组仍 >30%：收紧 pass-rate 预筛
   （[0.1,0.8] → [0.2,0.7]），必要时扩过采样倍率。
T2 熵塌缩：策略熵跌出 0.3~1.0 健康带（DeepSWE 给出的锚定区间）
   + 输出重复率上升 → clip-higher 已开（0.28）；再考虑降 lr 或
   极小 entropy bonus——注意 DeepSWE 反向教训：熵 loss 本身可致
   熵指数增长而崩溃，加了必须盯熵曲线。
T3 reward 全稀疏（各组几乎全 0）：先确认难度预筛未失效、
   环境验证门未漏坏环境 → 触发 E3 warm-start 回退。
T4 PCIe / offload 吞吐不足：优先降上下文（32k→24k）与单轨迹上限，
   不降组尺寸（n<8 组内统计太弱）；仍不足 → 离线导出 + 异步消费。
T5 MoE 下 token 级 ratio 震荡：切 slime 内置 gspo 估计器
   （序列级 IS，对 MoE / 长序列更稳）——一键切换，不改数据流。
监控面板最低集：策略熵（锚定 0.3~1.0）、零方差组占比、
   组内 reward 方差分布、输出重复率、pass@1 vs pass@k gap、
   response length 漂移、rollout 完成率、infra_failure 率、
   每步墙钟四段分解（生成 / 沙箱执行 / 评分 / 训练）。
```

- **定案**：（待）

### E3 warm-start / SFT 阶段是否纳入第一次实验 【依赖 E1】

- **问题**：直接从 instruct 模型 RL，还是先用离线导出 adapter 产 SFT 数据 warm-start 再 RL（对接 Stage 20 语义与 warm_start 文档）。
- **调查结论（存在张力，显式记录）**：全部机构报告（GLM-5/Qwen3/MiniMax/Kimi/Composer/MAI/Nemotron/ROME）都在 RL 前做 agentic SFT 或 mid-training（ROME 明说"SFT 把 RL 锚定在可靠策略区"；MAI 给出量级：self-distillation O(1M) 轨迹即足、更多边际递减）。但它们多从 base/mid 模型起步；**slime 官方示例本身就是从 instruct checkpoint 直接 RL、不做 SFT**——"直接 RL"路线有可复现模板。
- **定案建议（2026-07-07 第四轮修订：升级为三段式，pre-RL 诊断成为硬门）**：
  1. **第 0 段 pre-RL 行为诊断（硬门，必跑）**：与 pass-rate 难度预筛**合并为同一批 rollout**（预筛本来就要每题 8~16 次采样，诊断零额外成本）——在冻结候选池抽 50~100 题 × n8，统计 valid tool-call rate、submit rate、empty-patch rate、timeout rate、solve-none rate、非零方差组占比。若 valid action / submit 基本崩 → 先做小 SFT 修行为锚；若只是难度失配 → 调预筛区间与动态采样，不动 SFT。
  2. **第 1 段 direct RL from instruct**（最短路径 + slime 示例背书 + DeepSWE/SkyRL 的 Qwen3-32B 纯 RL 先例）。
  3. **第 2 段 SFT/RFT 回退**（量化触发见下）：目标是**修复行为锚点**而非提均分（Parallel-SFT 证据：功能等价导向的初始化比表面分布模仿的迁移更好）；只用 clean 成功轨迹 + 高质量 near-miss，1~5k 轨迹级。**措辞警示（第四轮核查纠偏）**：DeepSWE 原文是"在 Claude 轨迹 SFT 过的模型之上做 RL，100 iterations 无改进"——这是 **RL-on-SFT 停滞**的证据，不是"SFT 无用"，引用时必须写准。另有一个比 SFT 更便宜的中间选项：reward 稀疏而行为未崩时，混入 Hybrid-Gym 式辅助技能合成任务（函数定位/依赖搜索/上下文检索，agent 额度可产；其论文报 SWE-Bench Verified 绝对 +25.4pp 且与 in-domain 数据加性互补）。
- **回退触发量化（首训前预注册；线程 5 核实结论：前沿报告不存在"前 N 步 reward 不动"类公开诊断指标——以下阈值为自建预注册值，首训跑完后校准）**：

```text
观测窗：前 20 步（约 1280 条轨迹）。
触发条件（满足任一即回退）：
  (a) 训练集滚动平均 reward（10 步窗）绝对提升 < 0.02；
  (b) 非零方差组占比 < 30%，且经 E2-T1 干预 5 步无改善；
  (c) held-out 快评（每 10 步抽 10 题 × n4）连续两次无上行。
回退动作：暂停 RL → 离线导出 adapter 从已有 rollout 筛 SFT 候选
  （Nemotron 7 信号清洗：禁 git 操作 / edit-test 死循环 /
  lost-in-exploration / 工具调用卫生 / debug 残留 / 未验证提交等）
  + 可选 teacher 轨迹（agent 额度产）；
  SFT prompt 与 held-out 零重叠 → 轨迹级 1~5k 的小 SFT → 重启 RL。
```

- **线程 5 补充证据**：SFT→RL 回退在前沿是常备逃生舱而非例外——MAI 的 self-distillation 明确用于"从 RL 发散/崩溃中恢复"（收 RL rollout → SFT 回灌 midtrained checkpoint → 作为下一段 RL 起点，原文 "recover from occasional run failures" / "resetting numerics after a collapse"），并给出量级上界：**O(1M) 轨迹已足够匹配 teacher，更大数据集边际递减且会收窄输出分布、压制续训 RL 的探索**（只保留成功轨迹）；ROME 用 million 级两阶段 SFT 把 RL"锚定在可靠策略区"（§3.2.2）。我们 1~5k 轨迹的小 SFT 远低于该上界，方向安全。
- **定案**：（待）

### E4 训练数据构成与划分 【依赖 C2 agent 额度、第二轮数据调查】

- **重要澄清（2026-07）**：D2 的 20~50 题是 **S1 基础设施冻结集**（bring-up / smoke / 红队环境包载体），**不是正式训练集**——本项此前把两者混为一谈，现在拆开：
  - **S1 基建集**：20~50 题，可用 SWE-bench Verified 任务（此阶段只调基础设施不训练，无污染问题）；
  - **正式训练集**：规模与来源由第二轮数据专项调查定（§3 线程 3/4），数量级候选 200~2000 题；来源两路——(a) 开源可执行 SWE 数据集（SWE-Gym / SWE-rebench / R2E-Gym / SWE-smith 等，调查核实规模、镜像可得性、license）；(b) 用 C2 的 agent 额度把 5.4 环境生产线 agent 化自产任务（GitHub PR 抓取 + 环境构建修复 + 质检，MiniMax"agent 迭代建环境"与 GLM RepoLaunch 的个人版）——自产路线同时是简历亮点（环境生产线不再只是设计，是真跑过的流水线）。
  - **评测面切割**：正式训练集一律**不用 SWE-bench Verified**；Verified 整体保留为 held-out 评测面（E5），从源头杜绝训练/评测污染。
- **问题**：正式训练集规模与来源组合；难度分布；训练/评测集不重叠的冻结协议。
- **第一轮调查结论（超参侧）**：难度筛选"目标模型 pass-rate 中段"是全体共识（GLM-5 取目标模型 rarely-solve 下沿、Kimi 用 SFT 模型 pass@k 取 moderate、Qwen3 按 pass-rate 分布剔过易 + 噪声失败、MiniMax 按 reference solver pass-rate）；可操作区间锚点：MAI 组 pass-rate 过滤 [0.1, 0.8]。
- **第二轮调查结论（数据侧，线程 3+4，2026-07）**：
  1. **规模锚点**：ROME 是八份报告中唯一披露 RL 实际训练集数字的——**~2K 题**（60K 候选经难度筛 30× 坍缩），且同为 30B-A3B 底座、做到 Verified 57.4%。"环境池 → RL 有效集"普遍坍缩 1~2 个数量级；2K 以下无任何报告消融过——任务数消融确属社区增量。
  2. **开源数据集核实**（详见附录 B）：SWE-Gym（2,438 题 + Lite 234，SWE-bench 原生格式零改造走 `swebench` grader，仓库级与 Verified 无重叠）与 R2E-Gym-Subset（4,578 题去污子集，RL 战绩最硬：DeepSWE / SkyRL-Agent 在其上训到 Verified 39~42%）是安全首选；SWE-smith（~52K 合成，MIT，一 repo 一镜像最省盘）作多样性补充；**SWE-rebench V1/V2 只做时间去污、与 Verified 仓库大量重叠——不按 repo 过滤不得使用**。
  3. **agent 额度主战场**（线程 3）：全体报告的公共瓶颈步是"agent 建 Docker 环境 + 迭代自纠错"（MAI 实测建环境成功率仅 42.8%，是整条流水线最大损耗点）；其次是 LLM 生成语言感知测试日志解析器（GLM RepoLaunch）、问题陈述打分重写、合成增广（Qwen3：均 169.7 bug/仓库的杠杆）。唯一换不掉的 GPU 步是 pass-rate 难度筛选，可学 ROME 用开源基线模型粗筛以省自己的卡时。Nemotron 的 7 条轨迹过滤信号（禁 git 操作、edit-test 死循环、debug 残留等）是 warm-start SFT 清洗的现成清单，纯规则可跑。
  4. **治理层的第一个实战应用自动出现**：导入开源数据集必须先过我方环境验证门（golden patch 必过 / 空 patch 必败 / 重复执行确定）——社区反馈证实这些数据集普遍继承 flaky 测试与假阳性，**"导入集验证良率"因此成为可量化的治理指标**（纳入 E8 量化口径）。
- **定案建议（数据策略，2026-07-07 第四轮修订：拆 bring-up / success run，R2E 前移）**：

```text
静态质量预筛（新增，GPU 预筛之前，纯 agent 额度）：
  对候选题跑 SPICE 式三标签——issue clarity / test adequacy /
  solution leakage（SPICE arXiv:2507.09108 实测 $5.10/千题、与人工
  高一致；恰对应环境生产线子文档 task_quality_report 的三字段）——
  低分题先剔，再进 GPU pass-rate 预筛，省 rollout 预算。

Bring-up run（验证链路，不做能力结论）：
  SWE-Gym Lite(234) 经静态预筛 + pass-rate [0.1,0.8] + 环境验证门，
  得 ~100~200 题；只看非零方差组占比、有效轨迹率、导入良率、
  墙钟四段分解。协议走 swebench 官方 grader。

Success run（首个能力证明 run）：
  300~800 有效题，R2E-Gym-Subset 占比 ≥50%——依据 DeepSWE 逐字
  证据（"we observed limited performance improvements with the
  other datasets [SWE-Smith/SWE-Gym], often showing high
  solve-none rate ... R2E-Gym works best for RL training"，
  其解释是 R2E 提供了足够的课程难度梯度）；
  SWE-Gym Lite/Full 补多样性。R2E 走 scaleswe/eval_cmd。

扩容 run：上探 1~2K（R2E-Subset + SWE-Gym Full；SWE-smith 只作
  多样性补充）；触发条件 = success run 达到 E5 primary success。

并行（不阻塞首训）：agent 自产流水线作为 5.4 环境生产线的实战验证——
  "PR 抓取 → agent 建环境自纠错 → F2P/P2P 抽取 → 陈述重写 →
  环境验证门"，目标自产 50~200 题供第二轮。良率数据即简历证据。
  参考实现优先精读 Scale-SWE（arXiv:2602.09892——微调对象恰为
  Qwen-30B-A3B，与本项目同底座）。

冻结协议三条硬检查：训练集 repo ∩ Verified 12 repos = ∅；
  训练集 repo ∩ 主判据 held-out repos = ∅（E5 第四轮新增，
  held-out 从 R2E/SWE-Gym 按 repo 整体切出）；
  SFT/RL prompt 完全不相交（Qwen3 做法）。
```

- **污染核查清单（数据冻结前逐条执行；2026-07 线程 6 已核实）**：

```text
1. repo 级【已核实：三个首选集全部满足硬约束】：
   Verified 12 仓库 = django / sympy / sphinx / matplotlib /
   scikit-learn / xarray / astropy / pytest / pylint / requests /
   seaborn / flask。
   SWE-Gym 11 仓库（pandas/MONAI/moto/mypy/dvc/dask/modin/pydantic/
   conan/hydra/bokeh）、R2E-Gym-Subset 10 仓库（pandas/numpy/pillow/
   orange3/aiohttp/tornado/scrapy/pyramid/datalad/coveragepy，
   论文原文声明已移除与 SWE-bench test 重叠仓库）、
   SWE-smith 128 仓库（显式移除 12 个 originals）——
   与 Verified 交集均为 ∅。冻结时仍跑脚本断言（防数据集版本更新）。
2. 行内泄漏字段【已核实，物化时必须从模型可见面剥离】：
   SWE-Gym：patch（金标 diff）、test_patch、FAIL_TO_PASS、
     PASS_TO_PASS、hints_text（issue 评论，可能含修复方向甚至代码，
     默认整体不进上下文）。
   R2E-Gym：parsed_commit_content（金标 commit）、expected_output_json、
     execution_result_content、modified_files、
     modified_entity_summaries、relevant_files（答案或强定位泄漏）。
   两集镜像均构建在修复前状态（R2E 的 commit 字段映射待落地复核）。
3. 描述泄漏【已核实为最大隐性泄漏面】：SWE-Bench+ 实测 32.67% 的
   已解决实例在 issue 描述/评论里就有解法指针，4.3% 直接内嵌
   exact gold patch——problem_statement 必须扫描剔除修复 PR /
   commit URL、commit hash、"Fixes #NNN" 类指针；
   运行期断网 + anti-cheat 拦截兜底。这同时是 5.4 任务质量门
   （假阳性解检测）的又一实证依据。
4. 跨源去重【新增】：pandas 同时出现在三个训练集——池化多源时
   按 (repo, base_commit) 做去重/近重复检测，防同题重复采样
   （不违反 disjoint 硬约束，但影响多样性统计）。
5. 自产任务：teacher agent 生成任务时禁止把 solution hint 写进
   任务描述与环境文件（写入 5.4 生产线质检规则）。
```

- **定案**：（数据策略三段待确认后落 §4）

### E5 评测协议 【依赖 E4】

- **问题**：held-out 集大小、before/after 口径、方差控制。
- **调查结论**：口径高度一致——MAI：pass@1 取 4 次平均、T=1、top-p=0.97；MiniMax：SWE 4 trials、T=1.0/top-p=0.95；Nemotron：avg-8/16/32 抑方差；Kimi：Avg@4~64。方差硬数据：GLM-5 SWE-rebench 报 SEM ±1.06%~2.12%（数百题规模）——30 题小集单次评测分辨率很粗，多次采样必不可少。Composer 2 的补充呈现范式：best-of-4/16 曲线随训练同升（证明 RL 扩大可达解集而非只重排概率质量）。
- **定案建议（2026-07-07 第四轮修订：评测面拆双层，判据分级）**：

```text
主判据面（自建 frozen held-out——与训练同分布、同 harness、同推理栈）：
  从训练数据集按 repo 整体切出：建议 R2E-Subset 留出
  tornado(261) + pyramid(189)、SWE-Gym 留出 hydra(66) + bokeh(26)，
  共 ~540 候选，经同一套静态预筛 + 环境验证门后冻结 T≥50 题
  （资源不足 T≥30，须标注为低功效版本）。
  每题 n=8，T=1.0，top_p 与训练 rollout 同值（E2 定）。
  主指标 = Avg@n 解决率；按 task 配对 bootstrap（10k 次）给 Δ 与 95% CI。

外部参考面（公开可比性，不作主判据）：
  SWE-bench Verified 子集 30~50 题 +（可选）SWE-bench Pro public 子集。
  必须标注：OpenAI 2026-02-23 已公告 Verified 不再反映前沿能力
  （审计 o3 反复失败的 138 题中 ≥59.4% 存在拒绝功能正确答案的坏测试；
  前沿模型可复现题面与修复代码 = 预训练污染），其推荐替代即
  SWE-bench Pro。外部面只报方向与量级，不进成败判据。

成功判据分级（预注册，不允许事后降级）：
  primary success = 主判据面 Δ ≥ 8pp 且 bootstrap 95% CI 下界 > 0
  strong success  = Δ ≥ 10pp 且 CI 下界 > 0
  Δ ≥ 8pp 但 CI 跨 0 → 只能写"方向性信号，统计不充分"，不得称成功

必报的分布外指标（不进成败判据，两个面都零新增 harness）：
  scaffold transfer gap（mini-swe-agent 单向测一次）；
  prompt 改写面：用 agent 额度把主判据面题目 issue 改写成聊天式
  用户请求再评一遍（Saving SWE-Bench 实测该类改写使各模型相对
  成功率下滑 20~40%——本项目量化自己的下滑幅度作为附加发现）。

可选治理加分（agent 额度）：对 held-out 通过补丁跑 UTBoost 式
  增强测试复核假阳性（UTBoost 在 Verified 全集揪出 79 个误判通过）。
```

对照组两个（未训模型、若可复现再加 slime 示例原配置）；附 best-of-K 随训练曲线作为第二能力证据。
- **统计设计补强（2026-07）**：

```text
1. 术语：评测口径统一称 Avg@n（每题 n 次采样的平均解决率），
   不再写 pass@1 单次；best-of-K 曲线单独报。
2. 功效粗算（配对差分 + 二项近似，只计采样噪声的乐观下界）：
   设基线解决率 p≈0.3~0.4，每题 n 次采样、共 T 题：
   均值差 SE ≈ sqrt(2·p(1-p)/n) / sqrt(T)
   T=30, n=8  → SE≈4.4pp → 95% 可辨 Δ≈9pp
   T=30, n=16 → SE≈3.2pp → 可辨 Δ≈6.5pp
   T=50, n=8  → SE≈3.5pp → 可辨 Δ≈7pp
   （policy×task 交互方差未计入，真实阈值更高）
3. 判据预注册：首训成功判据 = before/after 提升 ≥8~10pp
   （30 题 × n8 可辨档）；若预期提升更小，必须先扩 T 或 n 再下结论，
   不允许事后降判据。
4. 检验方法：按题配对的 percentile bootstrap（重采样题目维度，
   10k 次）给 Δ 的 95% CI，以 CI 为准不依赖正态假设。
5. 分层报告：按 repo 分层给 Δ；单 repo 题数过少时只报聚合值并注明，
   防止分层后误读噪声。
```

- **定案**：（待）

### E6 rollout / 训练预算与上下文策略 【依赖 C1、E1、E2】

- **问题**：总训练步数、每步 rollout 数、单轨迹上下文上限、compaction 开关。
- **调查结论**：slime 示例的预算骨架——96k 上下文（autoCompact 80k 开启）/单轮生成 32k/每轨迹 agent 1800s + eval 600s/`--num-rollout 100` × 每步 8 prompt × 8 samples ≈ 全程 6400 条轨迹/总墙钟未披露（附录 A）。SWE-bench Verified 任务偏小（Composer：中位 7 行改动），96k 冗余；**降上下文直接砍训练侧 CP 需求（`max-tokens-per-gpu = context/CP`），是个人规模最大的可行性杠杆**。关 compaction 是 4/5 报告主流（preserved/interleaved thinking 或 turn 上限替代）。步数信号量级：Qwen3 约 220 步见收敛（旗舰规模），slime 示例 100 步。Qwen3 有两条低成本 reward shaping：未完成轨迹惩罚（turn 超限）、turn 级 tool-format 惩罚。
- **定案建议（2026-07-07 第四轮收紧：首训取保守档）**：上下文 **32k 起步、64k 不默认开**（DeepSWE 消融佐证：16K→128K 中超过 32K 边际收益不大；SkyRL 同用 32K/50 turns）、关 autoCompact；每轨迹 agent 预算 **600s 起步、900s 不默认**、eval 600s；步数 **30~50 步**；纳入两条过程处理（未完成/超限轨迹 → mask loss；tool-format 违规 → 独立负分量，精确落点见下条澄清）；对照组复现示例时沙箱可按 README 提示从 E2B 换本地 Docker（省 C2 API 费；形态 B 下我们自己的 rollout 走 RepoHarness Runtime，不受此影响）。64k / 900s / 更多步数只在 8 卡训练侧预实验（§4.1 第 4 条）与前 50 步曲线**同时**支持时开启。**Continuation rule（预注册）**：

```text
第 10 步：只查系统健康（墙钟四段分解、infra_failure 率、
  零方差组占比），不做任何能力结论。
第 30 步：若训练 reward、非零方差组占比、held-out 快评三者
  全无上行 → 触发 E3 回退或停训分析。
第 50 步：若快评 Avg@n 上行 + reward slope 为正 + 熵未塌 +
  墙钟低于 C3 预算 → 可延长至 75/100 步；否则停训进入分析。
```
- **过程惩罚落点澄清（线程 5 已按原文核实——四家四种落点，不可混谈）**：Qwen3 的未完成惩罚是**扣轨迹级 reward 标量**（原文 "the trajectory reward is penalized"），tool-format 是 token 级惩罚（原文措辞未明确是 advantage 还是 reward）；Nemotron 是唯一显式写 **negative advantage** 的（malformed 推理/工具调用的 token 施负优势），未完成轨迹则 **mask loss**；GLM-5 **完全不把过程惩罚放进 reward**——纯 loss mask（只算 model token）+ 样本剔除（环境崩溃）；MiniMax 把 process 惩罚做成**密集 process reward 分量**（r = α·process + β·speed + perf，α/β 未披露）；Composer 反其道：产品级惩罚放 reward 且**明确不 mask 超长轨迹**。本实验定案取 GLM-5/Nemotron 一侧（与 DeepSWE/SkyRL 的 Compact Filtering / 轨迹掩码实践一致）：**outcome component 由 clean grading 独占；未完成/超限轨迹 mask loss（不进 policy loss，先过滤）；`tool_format_penalty` 作为独立负分量经 adapter 透传、由后端合成 advantage（后惩罚）；两者不叠加于同一轨迹**。Qwen3 式"扣轨迹 reward"显式不采纳，避免污染 outcome 语义。
- **墙钟估算（回应"一周目标可能失真"）**：

```text
公式：总墙钟 ≈ 步数 × [ rollout 波次墙钟 + 训练 step 墙钟 ]
  rollout 波次墙钟 ≈ ceil(每步轨迹数 / 沙箱并发) × 单轨迹上限 + 评分尾波
示例（保守参数）：每步 8 prompt × n8 = 64 轨迹；沙箱并发 16；
  单轨迹上限 900s；评分 600s（与 rollout 重叠，计 1 个尾波）：
  rollout ≈ 4 波 × 900s + 600s ≈ 70min
  训练 step（8×Pro6000 PCIe + CPU offload，64 seq × ~20k token）
  ≈ 10~30min（[P3 收口 2026-07-09 实测校准]：纯训练段实测仅 252s
  ≈ 4min（n4/32 rollout 档），比纸面估算乐观得多；整 step 墙钟 1387s
  ≈ 23min 且 82% 是等 rollout——瓶颈在 harness 长尾而非训练，
  实测明细与 C3 反推见 §4.2 第 3 条）
⇒ 每步 ≈ 1.3~1.7h；
  100 步 ≈ 5.5~7 天（贴死一周上限，不可取）；
  30~50 步 ≈ 2~3.5 天（推荐首训档）。
杠杆排序：沙箱并发 16→32（吃 CPU/内存不吃 GPU，第一杠杆）
  > 单轨迹上限 900→600s > 降步数；
  评分队列反压（P11）防评分成为第二尾部；
  env_reset / 镜像冷启动按 M3 埋点实测后再优化。
结论：C3 默认定为"首训 ≤4 天墙钟、硬上限一周"；
  100 步档仅在并发 ≥32 且单轨迹 ≤600s 时可行。
```

- **定案**：（待）

### E7 接入形态（S0 已定案，此处回填）

- 形态 A（verifiers TrainClient + 协议 shim）vs 形态 B（slime custom_generate 直调）由 S0 验证定案；MoE 定案后形态 B 显著加分（§5.1-D3：vLLM wire 协议无 top-p ids 槽位，routing tape 穿 shim 存疑）。本文只记录：**实验配置必须在 S0 形态定案后填 E6 的具体启动方式**。
- **定案 [S0-8 收口 2026-07-08]**（依据 `../repo_harness_rh2_workstreams/s0/topology_ab_report.md` 四维实测）：**形态 B（SGLang 原生 `/generate` + slime patch 镜像，slime custom_generate 直调）为 MoE RL 训练主形态**；形态 A（vLLM `--tokens-only` 起 `/inference/v1/generate` + verifiers TrainClient）保留为协议基线与 dense 冒烟/调试路径（全链已验证可用，持有成本≈0）。两点实测更正上一行的旧推测：
  1. routing tape 并非"穿 shim 存疑"——两引擎都实测拿到语义一致的 tape（`[prompt−1+生成数, 48, 8]`），vLLM 侧薄 shim（base64-npy → `RoutedExpertsPayload{data,shape,start}`，几十行纯格式转换）已用真实 `Trace.commit` 证明可行；
  2. 真正的分水岭是 **top-p tape**：slime `loss.py:35-47` 在 `rollout_top_p != 1.0` 时硬性要求 `rollout_top_p_token_ids/offsets`，而 stock vLLM 0.24.0 与 stock SGLang 0.5.9 都不产出（SGLang 对该请求**静默忽略**，返回 200 不报错）——形态 B 的解是现成的 slime patch 镜像（`docker/patch/latest/sglang-top_p.patch`），形态 A 则是引擎 + wire 契约 + 消费端三端缺口。
- **硬性实施要求**：pin slime 镜像版本；服务启动后必跑一次 `top_p<1.0` 探针断言 `meta_info` 含 `top_p_token_ids`（防打到 stock server 的静默失败）；routing/top-p 两类 tape 的解码校验只在中立 `TrajectoryProjection` 层实现一次。
- **残余 U-H**：slime patch 镜像在 sm_120（RTX PRO 6000 Blackwell）上的实际可用性未验证，S1 接入时用同一探针关闭。U-H 失败的回退梯：手动对 stock SGLang 打 top-p patch → 临时 `top_p=1.0`（tape 需求消失，偏离主流采样配方需记录）→ 切回形态 A（放弃 top-p replay）。E6 的"具体启动方式"据此填写：rollout 推理栈 = slime 镜像内 SGLang；Blackwell 固化参数见 §4.1 第 3 条。

### E8 预期结论形态：什么算"证明设施有效" 【依赖全部】

- **问题**：简历叙事的收尾——最小可信的证据包是什么。
- **当前倾向**（证据包五件套，缺一不可；2026-07-07 第四轮由三件套升级）：
  1. **能力证据**：held-out 集 before/after **Avg@n 解决率**（统一用 E5 统计设计第 1 条口径，不再写 pass@1 单次 [S0-8 收口 2026-07-08]）有统计上可辨别的提升（配方差区间），附 best-of-K 随训练上升曲线（Composer 2 Fig 5 范式）；
  2. **治理证据**：训练全程的治理拦截统计（gate 拒绝分布、anti-cheat finding、红队环境包全部拦截成功）——证明提升不是靠作弊。调查带回必需性铁证：**Qwen3 Figure 7：不带 hack blocker 时 agent 用 git 回捞答案把分数虚高到 84.6%（真实 75.1%）**——治理证据不是锦上添花，是分数可信的前提；
  3. **解耦证据**：同批 rollout 经离线导出与在线 adapter 的 parity 校验通过（final_review §4.2）；
  4. **数据证据（2026-07-07 第四轮从"可选补充"升为必交付）**：开源数据导入良率与剔除原因分布（静态预筛 / golden-empty-确定性门 / 泄漏扫描各剔多少）+ agent 自产线 50~200 题的成功率与失败归因——设施型项目区别于"一次模型训练"的核心证据；
  5. **资源证据（第四轮新增）**：每步墙钟四段分解（生成/沙箱/评分/训练）、沙箱并发利用率、GPU 利用率、infra_failure 率——证明系统可诊断、可扩展，不只是"能跑"。
- **调查补充**：任务数消融（200 vs 1000~2000）保留为 **success run 达到 primary success 之后**的可选追加贡献，不作首训硬门（首训没起信号时不烧消融预算）。
- **定案**：（待；注意本项"三件套"已升级为五件套）

### E9 用户模拟与权限任务是否进第一次实验

- **当前倾向**：**不进**。第一次实验只用标准 SWE 修复任务（reward 面最干净）；交互式/权限任务留给 P2 白盒 harness 深化后的第二轮实验。
- **定案**：（待）

### E10 训练与评测 harness / scaffold 选择 【与 E7 联动，S0 后成对定案】

- **问题**（2026-07 补充，此前遗漏的一等决策）：训练 rollout 用哪个 harness/scaffold？训练 harness 与 held-out 评测 harness 是否一致？不同 harness 的工具格式、system prompt、上下文管理、文件编辑方式完全不同，Qwen3 图 3 已证明跨 scaffold 轨迹迁移很弱——训出的能力强绑定 scaffold，这直接决定 before/after 评测的有效性。
- **候选**：slime Claude Code harness / slime Codex harness / verifiers bash_edit harness / mini-swe-agent / RepoHarness 白盒 harness（P2 之后才存在）。
- **当前倾向**：
  1. **训练与 before/after 评测必须同一 harness**——自我对照的内部有效性优先，与公开榜单的可比性不是本实验目标（榜单口径的 scaffold 各不相同，本来就不可直接比）。
  2. harness 选择与 E7 接入形态**成对绑定**：形态 B → slime Claude Code harness（token 捕获已验证、治理层从外包裹）；形态 A → verifiers bash_edit harness（与设计文档 2 决策 3 一致）。
  3. 可选第二评测面：换一个 scaffold（如 mini-swe-agent）测 **scaffold transfer gap**——按 Qwen3 证据预期 gap 显著，作为附加发现记录，不作为成败判据。
  4. RepoHarness 白盒 harness 不进首训（P2 交付后的第二轮实验目标）。
- **调查结论（线程 5 已核实）**：前沿不存在"训练 harness 必须等于评测 harness"的统一要求，实践分两派——(A) **train=deploy 单一 harness**：Composer 2 明确 "training in the same Cursor harness that is used by the deployed model, with equivalent tools and structure"，以最小化 train-test mismatch 为纲；(B) **刻意多 harness 混训求泛化**：Qwen3 用 6 个框架采轨迹（SWE-agent / Mini-SWE / OpenHands / Claude-Code / Qwen-Code / Terminus），Nemotron SFT 用 4 harness 采集、RL 保证每个任务 vertical 至少覆盖 2/6 harness（附录 A.2 Harness Robustness）。**显式量化过 transfer gap 的只有 Qwen3（Fig.3：跨 scaffold 迁移 limited 且方向不对称）与 Nemotron（Fig.17 agent×model 矩阵）**——两家都实测出单 harness 训练跨 harness 掉点。
- **定案方向**：本实验取 (A) 派（Composer 式）——**单 harness、训练=评测**。理由：内部有效性是本实验的命题，且个人规模下多 harness 混训成本翻倍、要证明的也不是泛化性；(B) 派的多 harness 混训与 transfer 矩阵留作第二轮实验扩展项。倾向第 3 条的单向 transfer gap 附加测量保留（低成本，作附加发现）。
- **定案 [S0-8 收口 2026-07-08]（与 E7 成对锁定）**：形态 B ⇒ **训练 harness = slime Claude Code harness**（ClaudeCodeHarness + AnthropicAdapter，token 级捕获路径已由 slime 示例验证）；before/after 评测用**同一 harness、同一推理栈**（slime 镜像内 SGLang），保证内部有效性。注意与 E7 的措辞区分：形态 A 的"eval 路径"角色仅指**协议对照与 dense 冒烟**，不承担 before/after 主口径（否则跨引擎/跨采样栈差异会污染对照）。可选的 scaffold transfer gap 附加测量保留（如 mini-swe-agent 单向测一次，只作附加发现不作判据）。本定案同受 U-H 约束：若最终回退形态 A，harness 按绑定切 verifiers bash_edit，且必须在实验报告显式标注 harness 变更（前后不可直接比）。

依赖图小结：

```text
C1/C2/C3（用户填）
  └─ E1 模型型号 ── E2 算法族 ── E6 预算与上下文
        │                          │
        └─ E3 warm-start           └─ E5 评测协议 ── E8 结论形态
C4-D2 ── E4 数据构成 ──────────────┘
S0 ──── E7 接入形态 ══ E10 harness 选择（成对绑定，已定：
        形态 B + slime Claude Code harness [S0-8 收口 2026-07-08]）
E9 独立
```

---

## 3. 技术报告调查计划（本轮 sub-agent 分工）

与上一轮（设计缺口提取）不同，本轮提取目标是**实验配方与最小可信规模证据**。两个调查线程：

```text
线程 1（中式前沿报告配方）：R5 GLM-5、R3 Qwen3-Coder-Next、
  R4 MiniMax-M2、R7a Kimi K2 + glm5.2_blog_RL.md
  提取：RL 阶段模型规模、任务数、每题 rollout 数、组尺寸、上下文长度、
  算法与关键超参、SFT/warm-start 数据量级、评测采样协议、
  以及一切"多小规模就能看到信号"的消融证据。

线程 2（西式报告 + 最近尺度模板）：R9 Composer 2、R1 MAI、R2 Nemotron、
  R10 ROME + reference/slime/examples/coding_agent_rl 全部脚本与 README
  提取：同上配方要素；特别是 slime 示例的确切配置
  （模型、节点数、并发、步数、时长、reward 设置）——它是本项目
  最小可信实验的直接模板。
```

调查结果回填各 E 项的"调查子问题"，不改变依赖结构。

**状态（2026-07）：线程 1/2 已完成。** 结论已回填各 E 项"调查结论/定案建议"栏；slime 示例配置卡见附录 A。跨报告要点：GRPO 系全体一致（唯一反例 GLM-5.2 绑定 compaction）；难度筛选"目标模型 pass-rate 中段"全体一致；评测多次采样取均值全体一致；跳过 agentic SFT 的风险已在 E3 写入回退。

**第二轮数据专项调查（已完成，2026-07）**：线程 3（八份报告数据章节重读）与线程 4（开源数据集网络核实）结论已回填 E4"第二轮调查结论/定案建议"，数据集对比与落地坑固化在附录 B。两线程关键互证：报告侧点名的 RL 直用数据集（SWE-Gym / SWE-rebench / R2E-Gym / SWE-smith）与网络核实的安全可用名单一致；ROME 的 ~2K RL 有效集与开源数据集的可用规模（SWE-Gym 2,438 + R2E Subset 4,578 经筛选后）恰好匹配。

**第三轮补充核查（已完成，2026-07，回应 codex 评审七条）**：线程 5（报告原文核实）与线程 6（网络专项）结论已分别回填——过程惩罚四种落点原文对照（→E6）、SFT→RL 回退证据与 O(1M) 上界（→E3）、harness 两派实践与 transfer 量化先例（→E10）、三训练集 repo 清单与 Verified 交集 = ∅ + 行内泄漏字段清单 + SWE-Bench+ 32.67% 描述泄漏（→E4）、SkyRL-Agent 同款配置卡 + slime 默认三处差距 + 动态采样升级为默认开（→E2）。

**第四轮外部建议核查（已完成，2026-07-07，回应 gpt5.5pro 实验设计建议）**：对其 17 条文献引用逐条网络核实——**5 条承重引用全部成立**（DeepSWE 对 SWE-Gym "limited improvements / high solve-none" 为逐字原文；OpenAI 2026-02-23 公告 Verified 不再反映前沿能力、推荐 SWE-bench Pro；SPICE / UTBoost / Hybrid-Gym 均实）；两处措辞纠偏（DeepSWE 的 SFT 证据实为 "RL-on-SFT 停滞"非 "SFT 无用"；OpenAI 落点是"换 Pro"非"弃评"）；ProdCodeBench 数据未公开、不可自行复现，从副评测面候选剔除。据此完成第四轮修订：E2（top_p=0.95 定案建议）、E3（三段式 + 诊断硬门）、E4（bring-up / success run 拆分、R2E ≥50%、静态预筛）、E5（评测双层面 + 判据分级 + prompt 改写面）、E6（保守档 + continuation rule）、E8（五件套）。新文献速查见附录 C。

---

## 4. 定案记录

### 4.1 S0 实测定案回填 [S0-8 收口 2026-07-08]

证据来源：`../repo_harness_rh2_workstreams/s0/v2_renderer_report.md`（V2）、`v3_protocol_report.md`（V3）、`topology_ab_report.md`（V4）、`implementation-notes.md`（U-B/U-G/U-H 条目）。以下五条为 S0 实测已定，是本文各处引用的锚点；正文如有与本节冲突的旧表述，以本节为准。

1. **接入形态与 harness（实验层 E7 + E10，成对定案）**：形态 B（SGLang + slime patch 镜像，slime custom_generate 直调）为 MoE RL 训练主形态；形态 A（vLLM `/inference/v1/generate` + verifiers TrainClient）保留为协议基线与 dense 冒烟/调试路径。训练与 before/after 评测同用 slime Claude Code harness + 同一推理栈。判据、更正与回退梯详见 E7/E10 定案栏。
2. **模型（实验层 E1）**：Qwen3-30B-A3B（V2 渲染 12+12 项逐 token 实测、V3 全链 token 保真、V4 routing 透传三项支撑）。**renderer 守门为硬性要求（U-G）**：本地路径加载 tokenizer 会静默降级 DefaultRenderer（只打 INFO），必须用 HF id 或显式 `Qwen3RendererConfig()`，启动断言 renderer 类名 `== "Qwen3Renderer"`。
3. **Blackwell（sm_120）实测参数与镜像依赖**：
   - vLLM 0.24.0（形态 A / 协议基线）**默认参数不可用**，固化组合：`--tokens-only`（缺失则无 `/inference/v1/generate` 端点）+ `--enforce-eager` + 环境变量 `VLLM_USE_FLASHINFER_SAMPLER=0`，MoE 模型另加 `--moe-backend triton`；`CUDA_HOME` 指向 venv 内 nvidia/cu13 toolkit（机器无系统级 CUDA 开发栈时）。
   - SGLang（形态 B）：stock 0.5.9 实测可跑 30B-A3B，routing tape 原生（服务端 `--enable-return-routed-experts` + 请求侧 `return_routed_experts: true`），但 pip 安装对 CUDA 工具链路径极敏感 ⇒ 正式实现**必须固定 slime 官方 docker 镜像**（一步同时解决环境固化与 top-p patch 两件事）；**镜像在 sm_120 的可用性 = U-H，S1 接入时用探针关闭**。
   - tape 归一化契约：routing tape 两引擎语义一致（行数 = prompt−1+生成数，48 层 × top-8，专家 id 0..127），wire 差异（vLLM base64-npy / SGLang base64-int32）统一归一为 uint8 + `{data,shape,start}`；top-p tape 只有 slime patch 镜像产出。两类 tape 的解码/校验只允许在中立 `TrajectoryProjection` 层实现一次；服务启动后必跑 `top_p<1.0` 探针（stock server 静默忽略该请求，不报错，训练侧才会炸）。
4. **算力计划（C1/C2/E6）**：S0 已用**单卡** RTX PRO 6000 96GB（租用；8 卡缺货降配）实测 30B-A3B bf16 推理可行（权重加载约 60GB）。~~8×RTX PRO 6000（PCIe 无 NVLink）是 S4 训练目标形态，训练侧未做任何验证~~ **[P3 收口 2026-07-09 状态翻转]：训练侧四项未知已由 P3 八卡预实验实测关闭**（Megatron on sm_120 / PCIe all-to-all / CPU offload 全绿；colocate 显存水位以放置决策方式关闭——T3 分离定案后不再是候选），实测数值与判定见 §4.2。
5. **仍待用户拍板（S0 收口不代替用户决策）**：E2/E3/E4/E5/E6/E8/E9 的"定案"栏。其中 **E2（含训练 rollout 的 top_p 是否 ≠1.0——直接决定 top-p tape / U-H 依赖是否激活）、E4 首训数据策略、E5 成功判据预注册、E6 预算、C3 墙钟上限必须在 S1 冻结题单前定**；逐条清单与建议见 `../repo_harness_rh2_workstreams/s0/s0_8_expdesign_review.md`。

### 4.2 P3 八卡预实验实测定案回填 [P3 收口 2026-07-09]

证据来源：`../repo_harness_rh2_workstreams/preflight/preflight_report.md`（收口判定）+ `p3_remote_experiment_handoff_20260708.md`（原始事实）+ `remote_evidence_20260708/`。机器：8×RTX PRO 6000 Blackwell（sm_120，96GB/卡，PCIe）。以下实测数值是本文 C1/C3/E6 引用的锚点，与 §4.1 冲突处以本节为准。

1. **训练侧四项未知全部关闭（U-C）**：Megatron 内核在 sm_120 正常训练（J3 A4 TP4/CP2/EP8 + J4 replay + J5 完整 step）；PCIe all-to-all 实测 actor_train 174s / 训练段 252s（远低于 15min 绿灯线）；optimizer CPU offload 下 actor_train_tok_per_s=4528；colocate 显存水位不再需要实测——见第 2 条。
2. **放置定案：T3 分离（4 训 + 4 推）+ train_async 双缓冲，废弃"必须 --colocate"旧推论**。实测 rollout 是绝对瓶颈（wait_time_ratio=0.82，step 墙钟 1387s 里约 1135s 是 train 等 rollout），colocate 唯一优势=省跨分区权重同步 11.45s/step（仅占 step 0.8%），且 slime train_async 断言禁 colocate——用 0.8% 换不回双缓冲重叠。C1 的"必须 --colocate + CPU offload"修正为"**T3 分离 + train_async + CPU offload**"。
3. **E6 墙钟表校准（"训练 step 10~30min"纸面估算 → 实测）**：J5 gbs20（8 题 × n4 ≈ 32 rollout，30B-A3B）实测**整 step 墙钟 1387s ≈ 23min**，其中 rollout 段 1116s（rollout-bound）、训练段 252s、权重同步 11.45s@512MB buffer；单轨迹 harness 段 280~1116s（中位 ≈614s）；train_rollout_logprob_abs_diff≈0.036~0.039。**C3 反推：30~50 步 × 23min ≈ 12~19h**，远低于"首训 ≤4 天"上限——即使正式配置（n8=64 轨迹、更长轨迹、batch 准入过采样）使 step 时长翻 2~3 倍，仍在预算内。注意该实测为 n4 短题配置，n8 正式档开训前用 E6 公式按实测单轨迹分布重算一次波次数。
4. **新增独立验收项：治理过滤后的 batch schedule alignment**（P3 最重要教训）。fan-out + fail-closed 治理会使实际可训练样本数偏离名义值，slime `build_dp_schedule` 要求 microbatch 数对齐 `dp_size × mb_group`——formal J4 与 J5 gbs16 均死在此断言（`num_rollouts 19 < 32`、`23 mbs need 24`），J5 gbs20 只改 batch size 即通过，证明根因是调度对齐而非硬件。**开训前必须先跑纯 Python 的 batch schedule preflight**（协议 J4 判据第 0 项；实现归 S2 adapter 层）；严禁人工碰运气选 global_batch_size。
5. **尾部空闲实测 26~28% > 25% 注册阈值（双 run 一致）**：fully_async 升级触发条件成立；J4c 冒烟证明 fully_async 与我们的 fan-out 形状在补消费侧 `_key` 补丁后可启动（top-up 补采、无泄漏、2 个真实 step）。升级实施细节归 `preflight/slime_fully_async_upgrade_design.md`，不改本文 E6 首训定案（首训仍按同步 train_async 双缓冲预算）。

---

## 附录 A：slime 官方 coding_agent_rl 示例配置卡（精简）

来源：`reference/slime/examples/coding_agent_rl/`（README.md、`run_qwen36_35b_a3b_swe_8nodes.sh`、generate.py、swe.py）。本卡是 E1/E2/E6 的直接模板；完整参数以脚本为准。

```text
模型/硬件   Qwen3.6-35B-A3B（约 35B 总参 / 3B 激活，256 experts topk8）
            8 节点 × 8 GPU（卡型未披露）；--colocate 训推同卡
并行        训练 TP=2 PP=1 CP=8 EP=8 + sequence-parallel；
            SGLang rollout TP=8 DP=8 EP=8，mem-fraction 0.75；
            max-tokens-per-gpu = context/CP = 96000/8 = 12000
算法        GRPO（--advantage-estimator grpo）；KL/熵全关；
            非对称 clip 0.2 / 0.28（DAPO 式）；lr 1e-6 常数，wd 0.1
组织        --rollout-batch-size 8 × --n-samples-per-prompt 8 = 每步 64 轨迹；
            --num-rollout 100 步 → 全程约 6400 条；global-batch-size 64
上下文      --rollout-max-context-len 96000；单轮 --rollout-max-response-len 32768；
            claude-code autoCompactWindow=80000（开启）
时长        每轨迹 agent 1800s + eval 600s + 180s 守卫 ≈ 43min 上限；
            SWE_BOOT_CONCURRENCY=16；总墙钟未披露
harness     SWE_AGENT=claude_code（ClaudeCodeHarness + AnthropicAdapter，
            SGLang input_ids + return_logprob=True token 级捕获）或 codex
沙箱/评分   E2B（Sandbox 契约可换 Docker 重实现，README:188-200）；
            双沙箱 clean grading：agent 沙箱出 diff（排除 PROBLEM_STATEMENT.md
            与 .harness/），第二个干净同镜像沙箱 apply diff 后跑测试；
            reward 二值 0/1；评分协议 scaleswe（默认）或 swebench（官方 grader）
数据        swe_train.jsonl（prompt / label / metadata{image, workdir, ...}；
            题数未披露）；fan-out：每条 root-to-leaf 一个 Sample，
            reward/K 分摊，siblings 共享 rollout_id
```

---

## 附录 B：开源 SWE RL 训练数据集核实结果（2026-07，线程 4）

硬约束：评测独占 SWE-bench Verified ⇒ 训练集必须**仓库级** disjoint（仅时间去污不满足）。适配基准：slime `swe.py` 两套协议——`swebench`（官方 grader，SWE-bench 原生格式近零改造）与 `scaleswe`（自定义 eval_cmd / f2p_script）。


| 数据集                 | 可执行规模               | 镜像                                                 | 污染（vs Verified）             | RL 战绩                                    | 适配成本                       | 结论                    |
| ------------------- | ------------------- | -------------------------------------------------- | --------------------------- | ---------------------------------------- | -------------------------- | --------------------- |
| SWE-Gym（+Lite 234）  | 2,438               | DockerHub per-instance（OpenHands 发布，`xingyaoww/*`） | 仓库级无重叠                      | SkyRL-v0、OpenHands-LM                    | 低（原生 swebench 格式）          | **首选打底**              |
| R2E-Gym-Subset      | 4,578               | 行内自带 `docker_image`，300~500MB/个（`namanjain12/*`）   | 去污子集安全；**全量 8.1K 有重叠勿用**    | DeepSWE-32B、SkyRL-Agent（Verified 39~42%） | 低-中（自有 harness → scaleswe） | **扩容主力**              |
| SWE-smith           | ~52K 合成             | 一 repo 一镜像（全量 ~295GB，可取子集）                         | 无重叠（排除 SWE-bench originals） | SWE-agent-LM（SFT）                        | 低-中                        | 多样性/省盘补充              |
| SWE-rebench V1/V2   | 21K / 32K（V2 20 语言） | `swerebench` org / HF                              | **仅时间去污，与 Verified 仓库重叠**   | 榜单为主                                     | 低                          | **默认排除**（除非按 repo 过滤） |
| Multi-SWE-RL        | 4,723               | 公开容器                                               | 无 Python，天然无重叠              | 社区                                       | 中-高（多语言 grader）            | 留作多语言扩展               |
| SWE-bench-extra     | ~3,846 可建           | **无预构建镜像**                                         | 待核                          | —                                        | 中-高（自建镜像）                  | 不作首选                  |
| SWE-Fixer / SWE-Dev | 110K / 14K          | 无环境 / 待核                                           | —                           | SFT                                      | —                          | 不适用 / 观察              |


**落地坑（数据冻结前必须处理）**：

```text
1. 镜像限流：三个首选集的镜像都挂在个人 DockerHub 账号
   （xingyaoww / namanjain12 / jyangballin），免费额度约 100~200 pulls/6h，
   一个 batch 就能打满——首次把选中题的镜像全量同步到本机私有
   registry（registry:2 / Harbor），rollout 一律走本地。
2. 磁盘：SWE-bench 式镜像 1~2GB/题，2000 题约 0.5~2TB；
   /var/lib/docker 单独挂大盘；只拉选中题，不全量 pull。
3. 导入即验证：每题先跑 golden patch（必过）+ 空 patch（必败）
   + 重复执行确定性，剔除坏环境——5.4 环境验证门对第三方数据的
   直接应用，剔除率即 E8 的治理良率指标。
4. license：数据卡 license 之外每实例继承源 repo license；
   若发布模型/数据需逐 repo 核（个人实验风险低）。
```

**2026 新方向（观察项，不入首训）**：SWE-World（Docker-free 代理环境，与 slime 镜像路径不符）；SWE-Hub / SWE-Next（规模化环境生产系统）；MEnvAgent / DockSmith / EvoConfig（agent 自动建镜像基建——自产流水线的参考实现）。

**关键 URL 备查**：SWE-Gym `github.com/SWE-Gym/SWE-Gym`；R2E-Gym-Subset `huggingface.co/datasets/R2E-Gym/R2E-Gym-Subset`；SWE-smith `github.com/SWE-bench/SWE-smith`；SWE-rebench V2 `huggingface.co/datasets/nebius/SWE-rebench-V2`；Multi-SWE-RL `huggingface.co/datasets/ByteDance-Seed/Multi-SWE-RL`；DeepSWE `together.ai/blog/deepswe`；SkyRL `github.com/NovaSky-AI/SkyRL`。

---

## 附录 C：第四轮新增文献速查（2026-07-07 已逐条核实存在性与关键数字）

**改变决策的（已吸收进对应 E 项）**：

- **DeepSWE**（together.ai/blog/deepswe，"Other Attempted Experiments" 节）：R2E-Gym 优于 SWE-Gym/SWE-Smith（逐字原文见 E4）；"RL-on-SFT 100 iterations 停滞"（caveat 见 E3——不是"SFT 无用"）。
- **OpenAI 2026-02-23**《Why SWE-bench Verified no longer measures frontier coding capabilities》（openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/）：审计 o3 反复失败的 138 题中 ≥59.4% 为坏测试（35.5% narrow / 18.8% wide）+ 前沿模型预训练污染；推荐 SWE-bench Pro（→E5 双层评测面）。注：openai.com 反爬 403，正式引用逐字块需人工从浏览器复制。
- **SPICE**（arXiv:2507.09108）：issue clarity / test coverage / effort 自动标注，$5.10/千题、与人工高一致（→E4 静态预筛）。
- **UTBoost**（arXiv:2506.09289）：测试增强揪出 Verified 79 个假阳性通过、Lite 64 个；榜单排名变动 Lite 40.9% / Verified 24.4%（→E5 可选复核）。
- **Hybrid-Gym**（arXiv:2602.16819）：辅助技能合成任务（定位/依赖搜索/上下文检索）迁移 SWE-Bench Verified 绝对 +25.4pp、SWT-Bench +7.9pp，与 in-domain 加性互补（→E3 回退梯中间选项）。

**副评测面候选（首训不进，第二轮备选；除注明者均已核实公开可跑）**：

- FeatureBench（arXiv:2602.10975，开源 github.com/LiberCoders/FeatureBench；SWE 强者 74.4%→11.0%）
- ContextBench（arXiv:2602.05892，开源 github.com/EuniAI/ContextBench；过程级上下文检索，勿与 2602.08316 混淆）
- SWE-Together（arXiv:2606.29957，开源；多轮用户交互重放 + reactive 用户模拟——与 P2 白盒 harness 的用户模拟方向契合）
- RoadmapBench（arXiv:2605.15846，开源但超长程、30B 上 rollout 成本高）
- Harness-Bench（arXiv:2605.27922；106 任务 × 6 harness × 8 后端矩阵——官方代码仓身份有歧义，以论文链接为准）
- Self-Harness（arXiv:2606.09498；模型自迭代改 harness，Terminal-Bench-2.0 最高 +21.4pp——是方法不是评测面，作为第二阶段 "self-harness loop" 研究方向）
- ProdCodeBench（arXiv:2604.01527；**Meta 内部数据未公开、不可自行复现，从可执行清单剔除**，仅方法论参考）

**训练策略边界参考**：KLong（arXiv:2602.17547，极长程 trajectory-splitting SFT + progressive RL）；Tmax（arXiv:2606.23321，outcome-only GRPO 变体，9B 在 Terminal-Bench 2.0 达 27%，全开源）；Parallel-SFT（arXiv:2604.20835，功能等价导向初始化改善迁移）；Saving SWE-Bench（arXiv:2510.08996，聊天式改写致相对成功率降 20~40%——E5 prompt 改写面的依据）。

**数据方向观察项**：Scale-SWE（arXiv:2602.09892，实际标题 "Immersion in the GitHub Universe"；6M PR→100k 验证实例，微调对象恰为 Qwen-30B-A3B——自产流水线优先精读）；Open-SWE-Traces（arXiv:2606.16038，207k 多语言 agentic 轨迹）；SWE-Bench++（arXiv:2512.17419，11k 实例 / 11 语言生成框架）；SWE-MERA（arXiv:2507.11059，动态抗污染评测）。
---

## 定案批准记录（2026-07-08，项目所有者 + infra 线程会签）

用户批准第四轮修订全部推荐值：**E2**（GRPO n=8 + top_p=0.95，U-H 升为 S1 硬阻塞）、**E3**（三段式 + 行为诊断硬门 + 预注册回退阈值）、**E4**（静态预筛 + bring-up/success 拆分 + R2E≥50% + 三条冻结硬检查）、**E5**（双层评测面：主判据 = 自建 frozen held-out，Verified 降为外部参考面；判据分级预注册）、**E6+C3**（32k/600s/30-50 步 + continuation rule；首训 ≤4 天、硬上限一周）、**E8**（五件套证据包）、**E9**(用户模拟不进首训)。部分参数（吞吐/时长）留 8 卡预实验实测后动态微调。

infra 线程审查意见：无异议。两条落地后果记入 S1 执行计划：(1) E10"训练=主评测同 harness 同栈"意味着主评测面跑在 slime/Claude Code 路径的 eval 模式上，verifiers 评测路径承载第二 scaffold transfer 面与治理审计（架构说明 02 文档 §8 已同步精化）；(2) bring-up run 数据源（SWE-Gym Lite 预筛）的 ingestion 不阻塞 S1 闭环（闭环用已冻结 8 题），排期见 S1 计划 F3。SWE smoke 8 题题单同日冻结，无调整。
