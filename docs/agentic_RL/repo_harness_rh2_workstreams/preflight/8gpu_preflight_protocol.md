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
候选拓扑：T1 colocate 8 卡（对照基线）/ T2 分离 6 训+2 推 / T3 分离 4+4
时间换显存旋钮清单（按代价从小到大）：
  --sglang-mem-fraction-static 下调 / FP8 KV / --recompute-granularity full
  （已默认）/ --optimizer-cpu-offload（必开）/ --offload-train·--offload-rollout
  （colocate 换入换出）/ CP=2 / mbs=1 + --use-dynamic-batch-size
```

## 2. 作业序列（按信息量排序，总时间盒 ≤ 24h 墙钟）

| # | 作业 | 时间盒 | 关闭什么 |
| --- | --- | --- | --- |
| J0 | 环境就位：镜像/权重/GPU 可见性/`nvidia-smi topo -m` 拓扑留档 | 2h（含下载） | — |
| J1 | PCIe all-to-all 微基准（nccl-tests `alltoall_perf`，2/4/8 卡三档） | 0.5h | U-C 带宽项 |
| J2 | 推理侧 8 卡 serving 冒烟：SGLang 30B，TP/DP/EP 按 slime 示例缩配，32k 上下文，记 tokens/s 与显存 | 1h | 训推共存的推理半边 |
| J3 | **训练侧并行配置扫描（核心矩阵）**：合成固定 batch 过 Megatron train step | 4h | U-C 内核/显存/step 时间 |
| J4 | **全要素（S1-7b 本体）**：custom_generate，8 题 × n=2，E2 生产 flags，真实训练 step——在 T2（分离 6+2）拓扑上执行 | 3h | S1-7b + tape 消费 |
| J4b | **拓扑/异步对比（2026-07-08 增补）**：T1 colocate 同步 vs T2 分离+train_async 双缓冲，各连跑 3 步，记每步墙钟分解与 GPU util 曲线 | 2h | 放置模式决策 |
| J5 | 权重同步与切换：**跨分区 update_weights 耗时（分离拓扑的关键成本项）**、colocate 的 offload/onload 显存曲线（并入 J4/J4b 尾部） | 0.5h | U-C 切换项 + 权重同步 |
| J6 | 吞吐画像汇总与 E6 回填（分析，不占机时；机器可提前退租） | — | E6/C3 |
| J7 | 可选：若本机即训练机，按 DF-6 runbook 批量同步镜像（与 J3/J4 并行，吃网络不吃 GPU） | 后台 | 数据侧准备 |

### J3 矩阵（先粗后细，OOM 立即降档不恋战）

```text
固定：Qwen3-30B-A3B bf16、E2 生产 flags、--optimizer-cpu-offload、
     sequence-parallel 开、合成 batch = 64 条 × 目标长度
主轴 A 训练分区规模 × 并行组合（对应 §1.5 三种拓扑的训练侧）：
     A1 6 卡 · TP2×DP3       （T2 首选：DP3 摊薄 offload 优化器带宽）
     A2 4 卡 · TP2×DP2       （T3）
     A3 8 卡 · TP2×DP4       （T1 colocate 的训练态，兼作对照）
     A4 6 卡 · TP2×EP2 变体   （仅当 EP 通信在 J1 实测中可接受才试）
     A5 任一 · CP=2          （仅当 32k 显存不够时启用）
主轴 B 上下文：32k（目标档）→ 24k（降级档）
副轴 mbs：1 → 2（显存允许才试）
每格记录：step 墙钟 / 显存峰值（train 态）/ tokens/s /
     是否 OOM / 内核报错摘要
执行序：A1×32k×mbs1 起步；通过 → 扫 A2/A3 比速度；
     OOM → 先 mbs 后 CP 后 24k，记录降档路径
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
  预期主案 = T2 分离 + train_async 双缓冲（一步 off-policy，staleness
  字段照 handshake schema 记录）；colocate 仅当 J4b 显示分离的
  update_weights 跨分区开销吃掉全部重叠收益时才回退。
  异步二档（fully_async_rollout + partial-rollout + mask-offpolicy）
  作为 S4 中期若尾部仍主导时的升级项，本轮只验证其可启动性（30min 冒烟）。
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
