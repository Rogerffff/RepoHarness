# 《MOPD: Multi-Teacher On-Policy Distillation》阅读摘要

## 论文信息

- arXiv：2606.30406（2026-06 提交批次）；论文将 MOPD 部署于小米 MiMo-V2-Flash 的后训练。
- 官方页面：<https://arxiv.org/abs/2606.30406>；本仓库无本地 PDF，本摘要依据 arXiv TeX 源码核实。

## 核心问题

多个领域各自用最合适的 RL 配方（math 用 verifiable-answer RL、SWE 用 sandbox agent RL、IF 用 rubric RL）都能训出强专家，但把能力合进一个模型仍是难题。现有四类做法各有结构性缺陷：MixRL（混合数据联合 RL）有跨域干扰的 see-saw 效应；SeqRL（顺序分域 RL）先训的能力会在后续阶段衰退；RFT（离线蒸馏 teacher rollouts 的 SFT）有 exposure bias；Parameter Merging 权重融合不稳定。MOPD 改为在 policy space 做整合：先并行训出各领域 RL teacher，再让 student 在自己的 rollout 上向按域路由的 teacher 做 on-policy distillation。

## 方法

1. 三阶段流水线：Stage 1 general SFT 得到共享 checkpoint；Stage 2 从同一 SFT checkpoint 出发并行训练各领域 RL teacher（各域可用各自的算法/reward/超参，互不耦合）；Stage 3 冻结全部 teacher，student 从 SFT checkpoint 重新初始化，在多域 prompt 上蒸馏。
2. 路由按任务 domain 进行：每条 prompt 按其所属领域派发给对应 teacher，teacher 对 student rollout 做 prefill 取得逐 token 分布。（注：任务提示中提到的 "(domain, effort)" 二维路由在论文正文未出现，未能核实；论文只有 per-prompt 的 domain 路由。）
3. 训练目标是 per-token reverse KL：L = E_{x, y~π_θ}[ (1/|y|) Σ_t Σ_v π_θ(v) log(π_θ(v)/π_φd(v)) ]。给出两种实现：
   - Policy-gradient 形式（沿 MiniLLM）：per-token advantage = sg[log π_teacher(y_t) − log π_student(y_t)]，双边 clip（默认 A_max=5），可直接塞进现有 PPO/GRPO 框架，只改 advantage 计算。
   - Top-k 蒸馏形式（默认 k=64）：只在 teacher top-k token 上算 reverse KL，并额外加 π_φd(v) − π_θ(v) 修正项，保证截断后损失仍在 π_θ=π_φd 处取最小；同时把 teacher 回传量压到接近 reward 信号的规模。
4. 基础设施：teacher 部署为独立 prefill 服务（性质等同 reward 计算），rollout 完成即异步请求，teacher 开销几乎全部隐藏在采样时间后面。

## 实验结果

- Qwen3-30B-A3B（Base + 自制 SFT）、三域：Math（AIME25/26）、IF（IFBench/IFEval）、SWE（SWE-bench Verified）。归一化分数定义为 student=0、per-domain teacher=1。
- 主结果：MOPD 0.937，领先最强基线 MixRL 0.882 约 5.5 个点；SeqRL 0.775、RFT 0.824、PM 线性平均 0.328 / Task Arithmetic 0.857。MOPD 三域归一化分数都落在 [0.91, 0.95]，是各方法中最均匀的（SeqRL 跨 0.57–0.98、RFT 跨 0.65–1.01）。
- 样本效率：MOPD 约 25K IF 样本、约 30K SWE 样本即达 teacher 水位；MixRL 每个域要吃满 150–180K 样本。
- 关键超参：各域 RL 用 on-policy GRPO + Dynamic Sampling，lr 3e-6，Math/IF BS 144×8 rollouts 约 175K 序列，SWE BS 80×8 约 150K 序列（R2E-Gym-Lite，64k 上下文、50 turns 上限）；MOPD 阶段 BS 2048、N=1、不用 Dynamic Sampling，域配比 Math:IF:SWE = 0.35:0.35:0.3。
- 同源 vs 跨源 teacher（消融）：把 Math teacher 换成更强但异源的 Qwen3-235B-A22B 后，初始 per-token KL 从约 0.04 升到约 0.19（约 5 倍）。PG 形式下 math 精度持续退化、entropy 从 0.30 缩到 0.21；top-k 形式约在第 18 步灾难性发散。同源 teacher 是稳定蒸馏的关键。
- 两种损失形式在同源设定下表现接近：归一化分数 0.909（top-k）vs 0.937（PG）。
- MiMo-V2-Flash（论文章节标题称 309B 规模）：teacher 覆盖 Math/Code/IF/SWE/Tool Use 五域。MOPD 学生多数基准追平或超过对应 teacher（如 HMMT25 +1.8、AIME25 +0.2、τ²-Bench +0.7），仅有两处回退：IFBench −2.2、SWE-Bench Verified −0.8。
- 多轮迭代：以第一轮 MOPD 学生为起点重训 Math/IF teacher（Iter-2 teacher 归一化 1.030），第二轮 MOPD 学生从 0.937 提升到 0.986。

## 重要限制

- 单轮 MOPD 学生仍略低于各域 teacher（归一化 0.937 < 1），需要多轮迭代继续榨取 headroom。
- 同源约束是硬前提：不能直接借用更强的外部 teacher，跨源蒸馏在论文自己的消融里就是失败案例。
- 评测方差控制不对称：AIME 用 avg@32，IFBench/IFEval/SWE-bench Verified 每题只测一次。
- 论文正文未见开源代码/权重发布声明；MiMo-V2-Flash 部分只给了 7 个基准的汇总表，训练细节远少于 Qwen3-30B-A3B 部分。

## 对 RepoHarness 的意义

- MOPD 的同源约束与我们的路径天然吻合：我们本来就是 SFT checkpoint → 分叉训练专家的结构，论文证明这条路径的分布对齐（初始 KL≈0.04 量级）正是蒸馏稳定收敛的前提，而借外部大模型当 teacher 的捷径有明确失败证据。
- Qwen3-30B-A3B 是我们的同底座，论文超参（A_max=5、k=64、MOPD 阶段 N=1/BS 2048、域配比）可作为直接起点。
- miles 已有 OPD 实现可用：`reference/miles/examples/on_policy_distillation/` 下含 `run-qwen3-8B-opd-multi-teacher.sh` 多 teacher 脚本与 `qwen3_5_35b_selfdistill/` 两阶段配方，工程侧不需要从零搭 teacher prefill 服务。
- PG 形式"只改 advantage 计算"即可复用 GRPO 训练栈，改造成本最低；teacher prefill 异步化与我们把 reward 计算移出训练循环的思路同构。
