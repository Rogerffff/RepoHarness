# 8 卡预实验协议（P3）：训练侧未知关闭 + 吞吐画像

定位：一次性 8×RTX Pro 6000 租用的**测量协议**——租卡按墙钟计费，本文把"测什么、按什么顺序、每项的通过判据与放弃线"预先定死，租到卡照单执行。姊妹单卡作业（pass-rate 预筛 + pre-RL 诊断）规格见 §6。

**执行时机**：最早 = S1 闭环收口后（依赖 S1-6 编排胶水与 7a 验证过的链路）；截止 = S4 开训前。**推荐贴前不贴后**——本协议的放弃线带"重议 E1 / 换硬件"的推翻性结论，越早知道越好；它不依赖 S2/S3（安全加固与治理评分不碰训练内核），预实验数据即弃。

要关闭的未知（对账清单）：

```text
U-C  训练侧四项：Megatron 内核在 sm_120 可用性 / PCIe all-to-all 实测带宽 /
     colocate 训推显存水位与 sleep-resume 切换 / CPU offload 的 step 时间代价
S1-7b  30B-A3B 全要素训练 step（routing tape + top-p tape 首次真实进 loss）
E6 回填  "训练 step 10~30min" 纸面估算 → 实测；C3 墙钟反推的输入
权重同步  update_weights 到 rollout 引擎的耗时
```

---

## 1. 前置条件（租卡前完成，缺一不租）

```text
P-1 slime 镜像 digest 已 pin（S1-0 产物）且 U-H 已关闭
P-2 S1 闭环代码 commit 固定；7a 报告在手（bring-up 链路已验证）
P-3 Qwen3-30B-A3B 权重的获取方案确认（~60GB：租用机带宽实测后
    决定现场拉取还是对象存储中转；下载时间计入 J0 时间盒）
P-4 8 题冻结集镜像引用与 J4 运行配置写成脚本（复用 S0 探针形态）
P-5 nccl-tests 二进制或构建脚本备好（J1 用）
P-6 记录模板（本文 §5）与 nvidia-smi/dmon 采样脚本备好
P-7 主机内存确认 ≥ ~400GB（优化器 CPU offload 需 fp32 master 122GB
    + Adam m/v 244GB ≈ 366GB；不足即提前红灯——30B 训练在本机不成立，
    直接进 §3 放弃线选项 (b)）
```

## 1.5 拓扑候选与显存账（2026-07-08 增补：分离放置 + 异步为主案候选）

背景：colocate 同步模式下 agentic rollout 的长尾空等是已知吞吐杀手（用户 verl 实战教训）；slime **原生支持分离放置**（`--rollout-num-gpus N` 不带 `--colocate`）与四档长尾武器（train_async 双缓冲 / over-sampling+动态采样 / `--partial-rollout` + `--mask-offpolicy-in-partial-rollout` / `fully_async_rollout` in-flight 池跨步保活）。显存粗账（Qwen3-30B-A3B：权重 bf16 61GB，KV 96KB/token，32k 单序列 KV 3.0GB）：

```text
训练分区（TP2，权重+梯度 61GB/卡 + 激活 5~15GB @full recompute）：
  6 卡 TP2×DP3 ✓ / 4 卡 TP2×DP2 ✓ / 2 卡 TP2×DP1 ✓（但无 DP，step 慢）
  优化器一律 CPU offload（见 P-7 主机内存硬预检）
rollout 分区（mem-fraction 0.75）：
  2 卡 TP2×1 引擎：权重 30.5GB/卡，KV 池 ~83GB ≈ 27 条满 32k（bf16 KV）
  4 卡 TP4×1 引擎：权重 15GB/卡，KV 池 ~228GB ≈ 76 条
  FP8 KV 使容量翻倍；GRPO n=8 同组共享 prompt 前缀（radix cache），
  实际并发容量显著高于上述下界
候选拓扑（2026-07-08 第三轮修订，rollout-heavy 对齐行业惯例）：
  T1 colocate 8 卡  ——纯同步对照（slime train_async.py:11 断言禁
     colocate：colocate 模式下没有双缓冲，只有 train.py 全同步）
  T2′ 分离 2 训 + 6 推 ——对齐 MAI 推理:训练 5.3:1（4096:768 GB300）
     与 RollArt 3:1 的 rollout-heavy 惯例；风险 = 2 卡训练 step 变慢
     反而拉长双缓冲周期，J3 实测定夺
  T3 分离 4 + 4     ——slime fully_async 官方示例同款
     （examples/fully_async：ACTOR 4 / ROLLOUT 4 / TP2×2 引擎）
时间换显存旋钮清单（按代价从小到大）：
  --sglang-mem-fraction-static 下调 / FP8 KV / --recompute-granularity full
  （已默认）/ --optimizer-cpu-offload（必开）/ --offload-train·--offload-rollout
  （colocate 换入换出）/ CP=2 / mbs=1 + --use-dynamic-batch-size
```

## 1.6 异步档位决策（2026-07-08 第三轮调研定案，证据两线程交叉）

**行业证据**：bounded-staleness 异步是分离式大规模 SWE RL 主流（MAI/GLM-5/Composer/RollArt/MiniMax 全带显式准入界），但**上限很紧**——RollArt 默认 α=1 且实测 α=2 后期退化；MiniMax lag 上限个位数；最松的 MAI 也只有 8 次推理更新（40 梯度步）。反例：Kimi K2 同规模刻意选 colocate 同步 + partial rollout（<30s 全参更新）。正确表述是"尽量异步 + 很紧的界"。

**slime 现状（源码级核查）**：分离 + fully_async 是官方支持形态，但四个缺口——
① partial-rollout 的 token 级续接**未接入** fully_async 路径（README 明示 aborted 组"starts over"；样本 tokens 保留使续跑可能意外生效但官方不支持）；
② `--mask-offpolicy` 在 fully_async 下有盲区（引擎 pause/continue 使单次 generate 内 token 跨版本且不被 mask）；
③ **`--dynamic-sampling-filter-path` 与 `--over-sampling-batch-size` 在 fully_async 路径静默失效**（过滤逻辑只在 sglang_rollout 标准路径）——E2 定案的"动态采样默认开"在该路径不成立，需自建；
④ 无原生 staleness 准入旋钮——但记账字段齐全（`Sample.weight_versions` list，types.py:120/382）+ 天然插入点（`--buffer-filter-path`）。

**定案**：
```text
首训档位 = 分离放置（T2′/T3 由 J3/J4b 定）+ train_async 双缓冲
  + staleness 记账（不准入，只记录）。
  理由：双缓冲结构性 staleness 上界 ≈ 1×update_interval 个版本，
  天然落在行业最紧实践（α=1）内，不需自建准入；
  fully_async 的四缺口不该由首训背。
staleness 记账从 S1 起做：weight_versions → TrajectoryProjection
  handshake 字段 → gate 记录分布（为升级决策与 E8 资源证据备数）。
升级档位（预注册触发）= fully_async + 自建三件
  （buffer_filter staleness 准入 α=1 / custom_generate 内重写
  DAPO 过滤 / 整组同版本准入策略）。
  触发条件：J4b 或首训实测 rollout 尾部空闲 > 每步墙钟的 25%。
```

## 2. 作业序列（按信息量排序，总时间盒 ≤ 24h 墙钟）

| # | 作业 | 时间盒 | 关闭什么 |
| --- | --- | --- | --- |
| J0 | 环境就位：镜像/权重/GPU 可见性/`nvidia-smi topo -m` 拓扑留档 | 2h（含下载） | — |
| J1 | PCIe all-to-all 微基准（nccl-tests `alltoall_perf`，2/4/8 卡三档） | 0.5h | U-C 带宽项 |
| J2 | 推理侧 8 卡 serving 冒烟：SGLang 30B，TP/DP/EP 按 slime 示例缩配，32k 上下文，记 tokens/s 与显存 | 1h | 训推共存的推理半边 |
| J3 | **训练侧并行配置扫描（核心矩阵）**：合成固定 batch 过 Megatron train step | 4h | U-C 内核/显存/step 时间 |
| J4 | **全要素（S1-7b 本体）**：custom_generate，8 题 × n=2，E2 生产 flags，真实训练 step——在 T3（4+4，官方示例同款）执行 | 3h | S1-7b + tape 消费 |
| J4b | **拓扑/异步对比（第三轮修订）**：T1 colocate 同步 vs T3 双缓冲 vs T2′ 双缓冲，各连跑 2~3 步，记每步墙钟分解、GPU util 曲线、**rollout 尾部空闲占比**（升级档位触发条件的基线数） | 2.5h | 放置模式决策 |
| J4c | **fully_async 冒烟（30min）**：官方示例配置起 fully_async，验证可启动 + **实测 aborted 组重取时 token 复用行为**（README 称 starts over，但 tokens 保留可能意外续跑——记录真实语义供升级档位用） | 0.5h | 升级档位可行性 |
| J5 | 权重同步与切换：跨分区 update_weights 的**耗时、节奏与字节量**（pause/flush/continue 三段停顿分解；`--update-weight-buffer-size` 512MB 默认对 MoE 两遍 pass 的敏感度扫 2 档）、colocate 的 offload/onload 显存曲线 | 1h | U-C 切换项 + 权重同步 |
| J5b | **异步正确性与质量测量（两线程调研增补）**：见下方专项清单 | 并入 J3/J4 | staleness/数值正确性 |
| J6 | 吞吐画像汇总与 E6 回填（分析，不占机时；机器可提前退租） | — | E6/C3 |
| J7 | 可选：若本机即训练机，按 DF-6 runbook 批量同步镜像（与 J3/J4 并行，吃网络不吃 GPU） | 后台 | 数据侧准备 |

### J3 矩阵（先粗后细，OOM 立即降档不恋战）

```text
固定：Qwen3-30B-A3B bf16、E2 生产 flags、--optimizer-cpu-offload、
     sequence-parallel 开、合成 batch = 64 条 × 目标长度
主轴 A 训练分区规模 × 并行组合（对应 §1.5 拓扑的训练侧，第三轮修订）：
     A1 2 卡 · TP2×DP1       （T2′ 训练侧：必测——它决定 rollout-heavy
                              是否被训练步反噬；重点记 offload 带宽瓶颈）
     A2 4 卡 · TP2×DP2       （T3 训练侧，官方示例同款）
     A3 6 卡 · TP2×DP3       （回退候选：仅当 A1/A2 step 过慢）
     A4 8 卡 · TP2×DP4       （T1 colocate 的训练态，对照）
     A5 任一 · CP=2          （仅当 32k 显存不够时启用）
主轴 B 上下文：32k（目标档）→ 24k（降级档）
副轴 mbs：1 → 2（显存允许才试）
每格记录：step 墙钟 / 显存峰值（train 态）/ tokens/s /
     是否 OOM / 内核报错摘要
执行序：A1×32k×mbs1 起步；通过 → 扫 A2/A3 比速度；
     OOM → 先 mbs 后 CP 后 24k，记录降档路径
```

### J5b 专项清单（报告实践 + slime 源码两轮调研的增补测量，随 J3/J4/J4b 顺带采集）

```text
M1 staleness 直方图：Sample.weight_versions 的长度与版本跨度分布
   （一条 SWE 轨迹平均跨几个 policy version——升级档位 α 定档的实测依据）
M2 训推 logprob 失配：同批 token 的 rollout logprob vs trainer 重算
   logprob 的逐 token 差分布（MAI 一等监控项："小失配跨长轨迹复合
   会破坏 IS 校正"；这是 GRPO 正确性项）
M3 update 停顿吞吐塌陷：单次 update_weights 造成的 rollout 吞吐
   下陷深度与恢复时长（pause/flush 清 KV 后前缀重算的代价）
M4 abort 回收率与浪费：每次权重更新 abort 的在途组数、被丢弃重算的
   token 量（有效算力利用的直接扣减项）
M5 router 排队与 prefix cache 命中率：X-SMG-Routing-Key 一致性路由下
   GRPO 同组是否稳定命中同引擎（组内 8 兄弟共享前缀的 KV 收益实测）
M6 DP 序列打包失衡：各 DP rank 的 token 负载差（Composer 每步全局
   packing 的动因；失衡即空泡）
M7 生成引擎故障率：SGLang 引擎崩溃/超时次数与恢复行为
   （MAI 三层看门狗的动因；Nemotron 56% 故障来自生成引擎）
M8 优化器状态与权重推送的交互观察：若采用 per-step 推送，
   记录 loss/grad-norm 在推送前后的行为（GLM-5 每次推送后重置
   优化器的动因——slime 无此机制，观察是否需要）
```

### J4 判据（全要素 step 的六项断言）

```text
1. rollout（8 题 × n2，top_p=0.95）经 S1 链路产出合格 Sample；
2. 启动期探针：renderer 类名断言（U-G）+ top-p tape 探针（U-H 同款）通过；
3. loss 路径消费 rollout_top_p_token_ids/offsets 与 rollout_routed_experts
   无 raise、loss 有限值；
4. 训练 step 完成且 grad norm 非 NaN；
5. colocate 全程显存不 OOM（rollout 态与 train 态水位分别留档）；
6. checkpoint 用后即弃（8 题来自 Verified 仓库——A1/D5 条款，
   不得作为任何后续起点；acceptance 记录该声明）。
```

## 3. 通过判据与降级阶梯

```text
绿灯（S4 可按 E6 现行预算排期）：
  J3 最优配置的训练 step（64 轨迹 × ~20k token、32k 上下文）≤ 15min
  且 J4 六项全过，**且 J4b 产出明确的放置模式决策**——
  预期主案 = 分离（T2′ 或 T3，按 J4b 的每步墙钟与尾部空闲占比定）
  + train_async 双缓冲 + staleness 记账（§1.6 定案；双缓冲的
  结构性 staleness 上界即行业最紧实践 α≈1，无需自建准入）。
  colocate 仅当 J4b 显示跨分区 update_weights 开销吃掉全部重叠收益
  时才回退（注意 colocate 在 slime 里无双缓冲，纯同步）。
  升级档位（fully_async + 自建三件）触发条件预注册：
  rollout 尾部空闲 > 每步墙钟 25%（J4b 与首训双处测量）；
  本轮 J4c 只验证可启动性与 aborted 组 token 复用真实语义。
黄灯（可开训但重排预算）：step ∈ 15~30min → E6 步数上限按 C3 反推收紧，
  或采纳 24k 上下文档；沙箱并发杠杆（16→32）优先于降步数。
红灯（触发放弃线，停下与用户重议）：
  所有配置在 24k/mbs1 仍 OOM，或最优 step > 45min，或 Megatron
  在 sm_120 有不可绕过的内核缺陷。
  重议选项：(a) E1 降档（无先验背书，最后选择）；
  (b) S4 训练改租云端 NVLink 机（8×A100/H100 短租），本机专职
      数据/评分/单卡推理；
  (c) 每步轨迹数 64→32，拉长步数换显存/时间。
```

## 4. 执行纪律

- 每作业独立日志 + 配置 dump；失败不修不猜，记录后按矩阵继续（排障留给分析阶段，机时只用来采数）。
- J1~J3 用合成数据，J4 才碰真实链路——链路问题与硬件问题不混查（F2 原则的预实验内延续）。
- 所有脚本与判据版本进 evidence 目录：`preflight/`（本目录），报告 `preflight_report.md`，implementation-notes 三节制随执行建立。

## 5. 记录模板（preflight_report.md 骨架）

```text
机器：卡型×8 / 驱动 / CUDA / PCIe 拓扑（topo -m 原文）
J1：2/4/8 卡 all-to-all 带宽表（GB/s，msg size 两档）
J3：矩阵表（配置 × 上下文 × mbs → step 时间 / 显存峰 / tokens/s / 备注）
J4：六项断言逐条 + rollout 态/train 态显存水位 + 单步端到端墙钟分解
J5：update_weights 耗时 / sleep-resume 前后显存
结论：绿/黄/红灯判定 + E6 回填数字 + C3 反推结果
     （30 步/50 步全程墙钟预测，含 rollout 段）
```

## 6. 姊妹单卡作业：pass-rate 预筛 + pre-RL 行为诊断（A3 归属落地）

**时机（2026-07-08 修订）**：**S2 末 / S3 初——环境验证门完成之后**，不与 8 卡作业同期提前。理由（用户评审提出，采纳）：
1. pass-rate 有效性依赖环境门先行——golden patch 跑不通的坏环境 pass-rate 恒 0，分不清"题难"还是"环境坏"；flaky 环境的 pass-rate 是噪声。漏斗顺序以 DF-7 为准：静态门 → 环境验证门 → GPU pass-rate 筛。
2. 无关键路径收益——预筛的消费者（bring-up 题单）本来就等 S2 ingestion。
3. 30B 早期行为信号由本协议 J4 覆盖（8 题 × n2 全要素即迷你行为冒烟），不需为此提前烧完整诊断。

```text
输入：static_gate_survivors 216 题中**通过 S2 环境验证门**的存活集
配置：训练路径 eval 模式（同 harness 同栈）；T=1.0、top_p=0.95
预算分层（控制单卡墙钟 ≈ 1 天，按环境门存活数等比缩放）：
  存活全量 × n=4  → pass-rate 粗估，过滤 [0.1,0.8]
  诊断子集 60 题（分层抽）追加 × n=4 → 合计 n=8 的细估 + 诊断指标
产出：
  per-task pass-rate JSON（bring-up 题单的最终输入）
  诊断指标（E3 第 0 段硬门）：valid tool-call rate / submit rate /
    empty-patch rate / timeout rate / solve-none rate / 零方差组占比 /
    平均 turn 与 token——对照 E3 触发条件预演
判据：诊断指标若显示行为崩坏（valid action / submit 大面积失败），
  按 E3 定案先修行为锚，不进 RL。
后续批次（不在本作业）：held-out 候选与 R2E success-run 池的预筛，
  等题单范围确定后按同规格分批（同样以各自环境验证门为前置）。
```

## 7. 结果回填清单（执行后逐项勾）

```text
[ ] 实验设计文档 E6：墙钟表"训练 step（纸面）"→ 实测值；C3 反推更新
[ ] 实验设计文档 §4.1 第 4 条：训练侧"完全未验证"状态翻转
[ ] final_review V 清单：U-C 关闭记录
[ ] S1/S4 执行文档：7b 判据引用本报告（由执行线程操作，本线程只交报告）
[ ] E1 定案栏：35B-A3B 升级选项重议（仅当 J3 显存/速度富余显著时）
```
