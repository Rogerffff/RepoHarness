# Kimi K3 技术报告 + AgentEnv 对 rh2 的相关性笔记（2026-07-24 首轮阅读）

> 来源：`pdfs/k3_tech_report.pdf`（47 页，Kimi Team）+
> `reference/AgentEnv/`（浅克隆，kvcache-ai/AgentENV，Rust/Go，
> Firecracker microVM 沙箱平台，K3 训练所用，Apache 开源）。
> 本笔记是首轮相关性筛选（重点读了 §4 后训练、§4.2 环境体系、§5.3
> RL infra、AgentENV 三设计目标与 README）；逐节深读与对 05/S2 计划的
> 增补提案留给专门线程。

## 0. 一句话定位

K3 是 2.8T MoE（104B 激活）+ 1M 上下文的开源前沿模型；对 rh2 有价值的
不是模型本身，而是它**公开了 frontier lab 的 agentic RL 基础设施与环境
生产实践**——其中三块（partial rollout + per-token 正则、AET 验证器
隔离、AgentENV 沙箱三操作）与 rh2 已定决策高度同构，可作为设计佐证与
演进方向。

## 1. 直接印证 rh2 已定决策的部分（证据增强，不改设计）

| K3 实践 | rh2 对应 | 含义 |
|---------|----------|------|
| partial rollout：λ 比例轨迹完成即暂停生成、进入训练，未完轨迹**下一迭代续跑**——"单条长轨迹天然跨多个迭代，引入 staleness"，靠 **per-token 正则**（局部邻域约束）稳住极端 off-policy（§4.1.2） | 逐 turn weight_version + faithful DIS（D-FA 系列） | 两条不同的系统路径（co-located+partial rollout vs 分离+fully async）收敛到**同一算法需求**：轨迹跨版本 + token 级修正。我们的正式链方向是 frontier 同类项 |
| 未完成轨迹是一等公民（暂停续跑而非丢弃） | 决策包决策 1（episode_time_limit 截断有效） | frontier 实践不把"没跑完"当废样本——决策 1 方案 A 的外部佐证 |
| Reasoning Effort RL：per-problem token 预算 b0(x)，超预算 **reward=-1**（不是作废）（§4.1.2） | 同上 | 超预算作为训练信号的另一种实现（预算语义下的负 reward） |
| AET：奖励只来自**独立 verifier 对最终环境状态**的评估（不信 agent 自报完成）；public verifier 给诊断反馈 + **hidden verifier 评 held-out 场景**；有限提交预算 + 罚分（§4.2.6） | 双沙箱 clean grading + anti-cheat + G 系列 | 验证器隔离是行业共识；"public/hidden 双 verifier"是我们可借鉴的增量模式 |
| kernel 任务的 reward hacking 检测系统：惩罚 CUDA graph replay/输入缓存/精度削减，**随新 hacking 策略持续扩充**（§4.2.4） | anti-cheat 红队路线（简历亮点 2） | "作弊检测是持续演进的系统而非一次性清单"——与我们审查标准演进机制同构 |
| QAT 贯穿 SFT+RL，rollout 与训练**共享量化方案**："消除 train-inference mismatch"（§4.1.4） | weight_version/精度运行事实（P0-2 serving 字段） | 训推一致性是 frontier 显式工程目标，佐证我们把精度事实纳入 eligibility 的方向 |
| 统一 white-box 环境：harness = 可组合模块（工具面/系统提示词/上下文管理/skills/subagents），可实例化 Kimi Code/Claude Code/Codex/OpenClaw；**按任务组动态换 harness 配置防单 harness 过拟合**（§4.2.1） | 我们 v1 绑定 CC 单 harness | 与 Qwen3-Coder-Next 跨 scaffold 结论互证；"harness 多样性作为泛化手段"记入远期实验设计与简历叙事（v1 不动） |

## 2. 可借鉴进 FA/S2 的 infra 模式（候选增补，走 T1/T0 流程）

1. **Rollout auto-throttling**（§5.3.1）：并发不是静态配置——用活跃
   请求数/排队数/KV cache 利用率动态控制发给推理引擎的请求量（早期
   吃满、KV 压力升高时降并发，免手工调参防欠饱和与过载）。rh2 当前
   ResourceLimits 是静态信号量；候选演进：FA-5 把 KV utilization 列入
   观测项，正式训练期把 model_call 限额升级为压力感知节流。映射审查
   维度 L；与熔断规则"staleness 偏高→反压"同构。
2. **AgentENV 三操作**（§5.3.2 + 仓库 README）：
   - **Pause/Resume**（<100ms 暂停/<50ms 恢复）：agent 等模型推理时
     沙箱挂起、不占 CPU/内存——K3 实测这段占 sandbox 生命周期
     **高达 98%**。rh2 的 sandbox 并发限额本质上在为 idle-while-
     waiting 买单；microVM 暂停把这项成本趋零。
   - **Fork**：从运行中沙箱的精确状态分叉新沙箱，"用于评分且无副作用"
     ——正是我们双沙箱 clean grading 的 VM 级实现（我们现在是起第二个
     容器重放 workspace；fork 更快且状态保真更强）。
   - **Snapshot**：定期快照做错误恢复——对应 F2-4 恢复语义的 sandbox
     侧（我们 v1 的 docker 沙箱不可恢复进行中进程，K3 的 paused
     rollouts enqueued and resumed 证明"续跑"需要这层基建）。
   - 规模佐证：全程 51,219,741 个沙箱、1,505,678 个镜像——"环境生产
     与镜像管理是 frontier 真实瓶颈面"，支持 rh2 的定位叙事。
3. **集成路径薄**：AgentENV 暴露 **E2B 兼容 HTTP API**，slime agent 栈
   本就支持 E2B sandbox——理论上指个 E2B_API_URL 即接上。
4. **硬约束（当前不可行的原因）**：Linux 6.8+ / **/dev/kvm**（Firecracker）
   ——租用 GPU 云 VM 普遍无嵌套虚拟化（vast.ai 容器实例无 KVM）。
   定位：v1 不采用；作为"训后/扩展阶段基础设施选项"登记，简历叙事中
   作为 known frontier practice 引用。

## 3. 实验设计可借鉴

- 训练曲线双指标：score + **平均 assistant 步数**随 RL FLOPs 同涨
  （Fig 8）——before/after 实验可加 avg tool-call steps 维度。
- 评测配置披露方式：注明"Claude Fable 5 在 35% 任务上触发 fallback"
  这类 harness 行为披露（§6.1.3）——我们评测报告的诚实披露样板。
- Agentic GRM 的防 hacking：verbosity 预算控制（超长自动输负）——
  与我们长度偏置监测方向相反但同源（他们防奖励冗长、我们防惩罚过长）。

## 4. 不适用/不要被带偏的部分

- 模型架构（KDA/AttnRes/LatentMoE/QB）、3T 预训练 infra（MoonEP、
  activation offload）、KDA prefix cache、fleet scheduling：全在引擎层
  以下——rh2 的层不做 KV 池/内核优化，SGLang 用 slime patch 版即可。
- **co-located vs 分离不因此重议**：K3 选 co-located 是 2.8T 模型 +
  几百 GPU 的约束产物；rh2 是 8 卡 30B-A3B，T3 分离放置 + version-aware
  fully async 已定案且约束完全不同（规模差三个量级）。
- 1M 上下文与 KG 任务合成体系：远超 v1 范围，只作阅读背景。

## 5. 对 FA-2A 决策包的影响

- 决策 1（episode timeout）：**推荐不变（A：截断有效）**，新增两条外部
  证据（K3 未完轨迹续跑不丢弃；预算超限 reward=-1）。另确认 05 计划
  §6 递延项"true-resume conditional path"是 frontier 成熟路径（K3 的
  partial rollout 即是），但依赖可恢复沙箱基建——维持递延，注明依赖。
- 决策 2（F2-4 恢复）：不变；K3 的"paused rollouts enqueued + resumed"
  为 pending-state checkpoint 提供实践佐证。
- 决策 4（熔断）："staleness 偏高→反压"规则与 K3 auto-throttling 同构，
  分类框架获得外部印证。

## 6. 拆线程建议（留给专门线程的工作清单）

1. K3 §4.2（环境体系）逐节蒸馏进 S2/数据面参考（与 MiniMax-M2/
   Qwen3-Coder-Next/GLM-5 的既有蒸馏并列）；
2. AgentENV 深读：E2B API 面覆盖度、snapshot 持久化格式、与 slime
   E2B 适配层的真实兼容性（含"无 KVM 环境的降级路径是否存在"）；
3. 产出对 05 计划（FA-5 观测项 + 递延项注释）与 S2 计划（AET 双
   verifier 模式、hacking 检测演进机制）的增补提案，走 T1/T0 流程。
