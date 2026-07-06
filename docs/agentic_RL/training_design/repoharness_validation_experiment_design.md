# RepoHarness 验证实验设计（决策底稿）

本文是 `repo_harness_final_review_before_implementation.md` §5.1-D5 与 §6.3 定案的独立实验设计文档。当前处于**决策底稿阶段**：先列出全部待决事项与依赖关系，用技术报告调查校准候选项，再逐项定案。定稿后本文回答一个问题：**用什么最小可信实验证明 RepoHarness 这套环境与训练治理设施有效**。

与其他文档的关系：

- 基础设施范围与治理定案：`docs/harness_improve/repo_harness_final_review_before_implementation.md`（§3 范围、§5.1 D1~D7、§6 算法无关接口与在线 Anti-Hack）。
- 主架构：`docs/harness_improve/repo_harness_design_doc2_verifiers_based.md`。
- warm-start / 离线数据过滤：`docs/agentic_RL/training_design/warm_start_offline_data_filtering_design.md`。

时间基线：2026-07。S0 退出条件包含本文初稿完成（§6.3 定案）。

---

## 1. 硬约束框架（先于一切调查，待项目所有者填写）

实验设计的根约束，技术报告无法替我们回答：

```text
C1 算力形态（2026-07 已填）：单机 8 × RTX Pro 6000 Blackwell 工作站卡，
   单卡 96GB，合计 768GB；PCIe 互联、无 NVLink。
   直接推论：
   - 必须 --colocate（训推同卡）+ CPU offload（slime 示例已带该选项）；
   - PCIe 互联下 EP/TP 通信显著慢于服务器卡（NVLink），
     MoE all-to-all 是吞吐风险点，宜低 EP 度 + 长序列摊薄通信；
   - 30B-A3B 档初步核算可行：bf16 权重 60GB + 梯度 60GB，
     Adam 优化器状态走 CPU offload，单卡余量支撑 32k 上下文训练；
     35B-A3B 需 S0 实测后定；
   - 新增 S0 验证项 V5：SGLang / Megatron 对 RTX Pro 6000（Blackwell
     工作站 sm_120）的内核支持（attention kernel、FP8 KV、
     EP all-to-all over PCIe 的实际带宽）。
C2 货币预算上限：租卡为零（自有 8 卡）；API 面主要是 LLM judge（如有）。
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

## 2. 决策清单（E1~E9，带依赖关系）

每项格式：问题 / 依赖 / 当前候选与倾向 / 需要调查回答的子问题 / 定案（空待填）。

### E1 训练目标模型具体型号 【根决策，依赖 C1】

- **问题**：选哪个开源 MoE 模型做训练目标。
- **依赖**：C1 算力；反过来牵动 V2（renderer 覆盖）、V4（routing 透传）、E6（上下文与显存预算）。
- **候选与倾向（2026-07 调查后更新）**：
  - **首选 `Qwen3-30B-A3B` 档 MoE**：ROME 用同底座（30B-A3B）在 SWE-bench Verified 做到 57.4%，Composer 2 用 Qwen3-Coder-30B-A3B 做小规模代理实验证明该档足以观测 RL 信号——个人可负担规模里先验最强。
  - `Qwen3.6-35B-A3B`（slime 官方示例模型，配置卡见附录 A）：端到端配置现成，但示例是 8 节点 64 GPU（TP2/CP8/EP8 才吃下 96k 上下文）；C1 不足时需按 E6 大幅降上下文换可行性。
  - GLM 系 MoE（Air 级）：同生态加分，开源尺寸与 renderer 覆盖待核（V2）。
- **调查结论**：前沿报告 RL 的激活参数下限是 3B（Qwen3-Coder-Next 80B-A3B），与 30B-A3B/35B-A3B 同档——**3B 激活是有背书的下限，再小无任何先验**。slime 示例卡型未披露；显存需求由上下文长度主导（`max-tokens-per-gpu = context/CP`），上下文是第一可行性杠杆。
- **定案**：（C1 已填后倾向收紧为：**Qwen3-30B-A3B 档，32k 上下文起步**——8×96GB 单机下 30B-A3B 是"有前沿先验 + 显存可行"的交集；35B-A3B 仅在 S0 实测显存/吞吐允许时升级。最终锁定等 S0 的 V2/V4/V5 验证。）

### E2 算法族与后端配置 【依赖 E1、C1】

- **问题**：PPO with critic 还是 GRPO 起步；critic 的额外显存/卡数是否可承受。
- **依赖**：C1（critic 约多一份模型显存）、E6（轨迹长度——GLM-5.2 因 compaction 长轨迹弃 GRPO 改 PPO，但我们第一版任务较短且建议关 compaction，组语义可能仍成立）。
- **调查结论（一致性极高）**：GRPO 系是绝对主流——slime 示例（`--advantage-estimator grpo`、KL/熵全关、非对称 clip 0.2/0.28）、GLM-5（GRPO+IcePop，β=2、ε_low=0.2、ε_high=0.28）、Composer 2（Dr. GRPO：去长度归一、不除组 std）、MAI（GRPO+自适应熵+outer clip）、Nemotron（异步 GRPO，组 16）。唯一弃 GRPO 改 critic-PPO 的是 GLM-5.2，触发条件是 compaction 切碎超长轨迹——首版关 compaction 不触发。组尺寸锚点：slime 示例 8、Nemotron 16、GLM-5 reasoning 32、MAI 128（机构规模）。zero-advantage 标准处理：MAI early-exit（先采 16 估 pass-rate，[0.05,0.8] 内才补满）+ 组过滤 [0.1,0.8]。
- **定案建议**：GRPO；n=8；clip 0.2/0.28、KL/熵关、lr 1e-6 常数全部沿用 slime 示例初值；**"关 compaction ↔ 用 GRPO"绑定写入**——未来开 compaction 必须同步评估切 PPO（接口已算法无关，§6.1 的价值就在此）。
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
- **定案建议**：第一次实验保留直接 RL from instruct（最短路径 + slime 示例背书），但写入**回退预案**：若触发下述量化条件，插入一轮小规模 agentic SFT warm-start——回退同时提前兑现离线导出 adapter 的价值叙事，与原第二轮实验计划合并。
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
- **定案建议（数据策略三段）**：

```text
首训（S1 后第一次正式训练）：纯开源起步——
  SWE-Gym Lite(234) 经目标模型 pass-rate [0.1,0.8] 预筛
  + 我方环境验证门，得约 150~200 有效题；
  扩容时叠加 SWE-Gym 全量(2,438) + R2E-Gym-Subset(4,578)，
  上探 1~2K（ROME 上沿锚）。
  协议：SWE-Gym 走 swebench 官方 grader；R2E 走 scaleswe/eval_cmd。

并行（不阻塞首训）：agent 自产流水线作为 5.4 环境生产线的实战验证——
  用 codex/claude code 额度跑"PR 抓取 → agent 建环境自纠错 →
  F2P/P2P 抽取 → 陈述重写 → 环境验证门"，目标自产 50~200 题
  供第二次实验。自产不再是首训必需品，而是环境生产线的证明材料
  （简历叙事：生产线真跑过，且有良率数据）。

消融与冻结：任务数可扫变量定档 200 vs 1000~2000 两档；
  冻结协议含两条硬检查——训练集 repo ∩ Verified 12 repos = ∅、
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
- **定案建议**：held-out ≥30 题（按仓库与训练集零重叠）；每题采样 n=4~8 取均值，T=1.0、top-p 0.95~0.97；报告均值 ± 置信区间；对照组两个（未训模型、若可复现再加 slime 示例原配置）；附 best-of-K 随训练曲线作为第二能力证据。
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
- **定案建议**：上下文 32k~64k、关 autoCompact；每轨迹 agent 预算 600~900s（示例 1800s 对 Verified 偏松）、eval 600s；步数靶 30~100 步——下限以 reward 曲线出现趋势为准，上限由 C3 反推；纳入两条过程处理（未完成/超限轨迹 → mask loss；tool-format 违规 → 独立负分量，精确落点见下条澄清）；对照组复现示例时沙箱可按 README 提示从 E2B 换本地 Docker（省 C2 API 费；形态 B 下我们自己的 rollout 走 RepoHarness Runtime，不受此影响）。
- **过程惩罚落点澄清（线程 5 已按原文核实——四家四种落点，不可混谈）**：Qwen3 的未完成惩罚是**扣轨迹级 reward 标量**（原文 "the trajectory reward is penalized"），tool-format 是 token 级惩罚（原文措辞未明确是 advantage 还是 reward）；Nemotron 是唯一显式写 **negative advantage** 的（malformed 推理/工具调用的 token 施负优势），未完成轨迹则 **mask loss**；GLM-5 **完全不把过程惩罚放进 reward**——纯 loss mask（只算 model token）+ 样本剔除（环境崩溃）；MiniMax 把 process 惩罚做成**密集 process reward 分量**（r = α·process + β·speed + perf，α/β 未披露）；Composer 反其道：产品级惩罚放 reward 且**明确不 mask 超长轨迹**。本实验定案取 GLM-5/Nemotron 一侧（与 DeepSWE/SkyRL 的 Compact Filtering / 轨迹掩码实践一致）：**outcome component 由 clean grading 独占；未完成/超限轨迹 mask loss（不进 policy loss，先过滤）；`tool_format_penalty` 作为独立负分量经 adapter 透传、由后端合成 advantage（后惩罚）；两者不叠加于同一轨迹**。Qwen3 式"扣轨迹 reward"显式不采纳，避免污染 outcome 语义。
- **墙钟估算（回应"一周目标可能失真"）**：

```text
公式：总墙钟 ≈ 步数 × [ rollout 波次墙钟 + 训练 step 墙钟 ]
  rollout 波次墙钟 ≈ ceil(每步轨迹数 / 沙箱并发) × 单轨迹上限 + 评分尾波
示例（保守参数）：每步 8 prompt × n8 = 64 轨迹；沙箱并发 16；
  单轨迹上限 900s；评分 600s（与 rollout 重叠，计 1 个尾波）：
  rollout ≈ 4 波 × 900s + 600s ≈ 70min
  训练 step（8×Pro6000 PCIe + CPU offload，64 seq × ~20k token）
  ≈ 10~30min（S0 实测项 V5 的一部分）
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

### E7 接入形态（记录依赖，不在本文定案）

- 形态 A（verifiers TrainClient + 协议 shim）vs 形态 B（slime custom_generate 直调）由 S0 验证定案；MoE 定案后形态 B 显著加分（§5.1-D3：vLLM wire 协议无 top-p ids 槽位，routing tape 穿 shim 存疑）。本文只记录：**实验配置必须在 S0 形态定案后填 E6 的具体启动方式**。

### E8 预期结论形态：什么算"证明设施有效" 【依赖全部】

- **问题**：简历叙事的收尾——最小可信的证据包是什么。
- **当前倾向**（三件套，缺一不可）：
  1. **能力证据**：held-out 集 before/after pass@1 有统计上可辨别的提升（配方差区间），附 best-of-K 随训练上升曲线（Composer 2 Fig 5 范式）；
  2. **治理证据**：训练全程的治理拦截统计（gate 拒绝分布、anti-cheat finding、红队环境包全部拦截成功）——证明提升不是靠作弊。调查带回必需性铁证：**Qwen3 Figure 7：不带 hack blocker 时 agent 用 git 回捞答案把分数虚高到 84.6%（真实 75.1%）**——治理证据不是锦上添花，是分数可信的前提；
  3. **解耦证据**：同批 rollout 经离线导出与在线 adapter 的 parity 校验通过（final_review §4.2）。
- **调查补充**：可选第四件交付——任务数消融（E4 定档 200 vs 1000~2000 两档），全部前沿报告都没有的小规模信息增量。量化口径新增一项：**导入开源数据集的环境验证良率**（多少题被 golden/empty/确定性门剔除）——治理层对第三方数据的第一个可量化实战指标。
- **定案**：（待）

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
- **定案**：（待 S0 形态定案后与 E7 一并锁定）

依赖图小结：

```text
C1/C2/C3（用户填）
  └─ E1 模型型号 ── E2 算法族 ── E6 预算与上下文
        │                          │
        └─ E3 warm-start           └─ E5 评测协议 ── E8 结论形态
C4-D2 ── E4 数据构成 ──────────────┘
S0 ──── E7 接入形态 ══ E10 harness 选择（成对绑定，S0 后定）
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

---

## 4. 定案记录

（待逐项讨论后填写。）

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