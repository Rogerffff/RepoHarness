# GPU Spike 实验内容设计 v1（Claude 版，供 owner 与 codex 版对齐）

日期：2026-09-01。性质：**只回答"测什么、为什么、能证明什么"**；运行环境、启动脚本、验证器实现是内容定稿后的下一步，本文不引用既有 `launch.sh`/`thresholds.md`/`g1_acceptance.py` 的任何实现细节作为前提（它们未经 owner 审查，届时按本文重新对表）。证据底稿：本地验证边界盘点（2026-09-01，会话报告，关键结论已内嵌）。

## 0. 唯一主交付与判定框架

本次 GPU spike 只回答一个问题：

> **RH2 的真实 SWE agent 训练链，能否在目标硬件上完整跑在 Miles fully-async 栈上，并保持训练数据与更新语义正确——从而让 fully-async 开发主线正式迁到 Miles？**

主交付 = **Migration-Go / Conditional Go / Migration-No-Go** 三分类结论 + 支撑每项判定的机器证据。它**不是**：正式训练开闸（`rh2_s2_signal_trusted`/`rh2_formal_training_allowed` 保持 false，执行模式 s1_compat 全程标注 pre-formal）、模型能力验证（短跑 reward 不构成任何判据）、生产恢复能力验收（run-fatal 即合格）。

每个测试项标注判定角色：
- 【判定级】失败直接影响 Go/No-Go 结论；
- 【数据级】采集决策数据（拓扑选择、T0-A 回填、阈值校准），失败不否决迁移但缺数据即对应决策关不了；
- 【条件级】失败降级为 Conditional Go 的显式限制项，owner 按代价决定。

## 1. 方法论：为什么这些必须上 8 卡远程 GPU

本地段（403 个 integration-base 测试 + 全部负测试）证明的是**语义与接线在"单进程、构造数据、探针件"世界里的逐位正确性**。盘点确认本地**从未运行过任何一次**：真实 token 生成（全部 canned 应答）、真实模型 forward（current logprob 全部来自构造 logits 或 17-vocab 探针模型）、Megatron 融合核/BF16/任一并行维度（megatron 整包 auto-stub、进程组全是 world_size=1 自归约）、真实 megatron optimizer/scheduler（AdamW 探针替身）、真实 `train_async` driver 进程（publish 门控只有源码文本锚定）、真实权重更新（`pause_generation` 全仓零调用、跨更新在途请求从未存在）、Megatron replay 的 forward/backward pop、CC 二进制、真 Docker 容器、真评分、Ray actor 生命周期、真实 fan-out 触发、镜像构建与 sm_120 上的任何执行、一切性能量。

因此 GPU spike 的每一项都对应一个明确的"替身背后的真实面"。反过来说：凡是本地已逐位证明的语义，GPU 上**不重测语义本身**，只测"真栈是否改变了输入"——这是控制租期规模的原则。

## 2. 测试内容（五层）

### 层 A：部署真值——"能不能起来"

**A1【判定级】sm_120 训练侧内核栈可用**
- 测什么：miles 官方镜像 + 重编 kernel wheels（FA2/apex 等，S3 清单）在 8×RTX PRO 6000 上完成 Megatron 30B-A3B 的真实训练 step（不是编译通过，是执行通过——含 attention/优化器/通信内核各至少真跑一次）。
- 为何必须 GPU：内核 arch 支持只能在目标 ISA 上执行验证。本地零 GPU；S3 是纯文献侦察（wheels arch list 无 12.0 是读出来的，不是跑出来的）。**P3 绿灯不可迁移**：这是新组合（TE 2.17 vs P3 的 2.16、FA2 2.7.4 vs 2.8.3、sglang 0.5.18 vs 0.5.13、radixark/Megatron vs NVIDIA 上游），P3 的经验只证明"重编路径可行"这个方法，不证明这套版本。
- 证明什么：MQ-1 部署闭合的执行半边（源码坐标半边本地已由 manifest 钉死）。不证明：hermetic 复建（镜像 digest/wheel hashes 记录属于本轮产出物，逐字节复现验证不是）。
- 失败含义：先诊断 wheel/单内核级（可现场重编的算普通修复），系统性 sm_120 不兼容才升级为 No-Go 证据。

**A2【判定级】30B 引擎三凭据出站真值**
- 测什么：sglang@4e230c3d 在 sm_120 起 30B-A3B，真实请求返回三凭据：sampling mask（`output_token_sampling_mask` + support-normalized logprob）、weight version spans、R3 routed experts tape，形态与我们 fail-closed parser 的合同一致。
- 为何必须 GPU：本地所有引擎应答都是 canned dict；wire 合同只做过**源码阅读级**核实（gh api 读上游实现与单测）。真实采样器（flashinfer/triton 后端在 sm_120 的实际选择）下 mask 的 force-include、spans 的注入条件、R3 行数与 token 对齐，只有真引擎能证。uh_probe 的先例是 slime v0.5.13 patch 栈，不覆盖本栈。
- 证明什么：数据面三凭据的生产端真值——我们整条 capture→训练链的输入合法性。失败含义：单凭据失败可 R3-off/降级诊断分流；mask 失败 = faithful DIS 无法忠实，判定级阻断。

### 层 B：训练语义真值——本地用替身证过的，真栈下是否成立

**B1【判定级】三方逐 token logprob parity（同权重 ratio≈1）**
- 测什么：同一权重版本下，引擎 support-normalized behavior logprob ↔ 训练侧经 rollout_sampling_mask 的 masked current logprob ↔ capture 记录三方逐 token 对拍；loss/grad norm 有限。
- 为何必须 GPU：本地 parity 的 current **从来不是真模型 forward**（构造 logits 或 TinyModel），且走 true-on-policy 全词表路径——**Megatron 融合核路径零执行**、BF16/TP/PP 归约零执行（P0-3 当年就把分布式 bitwise 显式归硬件段）。这是 faithful DIS ratio 的分子分母根基：本地证了公式，GPU 证输入。
- 证明什么：MQ-3 训练数学在真栈成立。同权重 ratio≈1 是一锤定音检验——任何测度不一致（top_k 配置、renorm 口径、并行归约）都会直接体现为系统性偏离。失败含义：判定级阻断，按"引擎侧/训练侧/capture 侧"三分诊断。

**B2【判定级】R3 replay 真消费**
- 测什么：R3-on 下，同一份 tape 经 capture→canonicalize→train wire→Megatron replay 的 **forward/backward pop 真实执行并耗尽**，与 ≥2 个 applied optimizer step 联结；R3-off 对照路径字段保持 None。
- 为何必须 GPU：replay pop 只在真 GPU forward/backward 里发生；本地只证到"运到 trainer 门口 + oracle 会抓缺失"，连"backward pop 数=microbatch 数"所依赖的 recompute 触发假设都从未真实发生。R3 是选这套栈的核心理由（MoE 训推一致性），不真消费的 Migration-Go 是空心的——**R3-off 成功不得替代本项**（已定案）。
- 失败含义：R3-off 对照 + stock 探针隔离"上游 replay 机制 vs 我们的运输"；上游机制性失败是 Conditional/No-Go 级证据。

**B3【判定级】F2 零信号跨 rank 一致性 + optimizer 真值**
- 测什么：目标并行拓扑（多 rank NCCL）下注入一个全局零梯度 step：全 rank 同判 SKIPPED_ZERO_SIGNAL，真实 Megatron optimizer/scheduler/weight version/publish 全不前进；前后各一个正常 step 正确前进恰 +1（D5 负控：先形成 momentum 再注零）。
- 为何必须 GPU：本地跨 rank 归约是 world_size=1 gloo 自归约 no-op；momentum 验收用的是真 AdamW 但**不是 megatron DistributedOptimizer/混合精度 optimizer**，found-inf 分支与真实 grad_norm 交互从未执行；publish 门控只有源码文本锚定，真 `train_async` driver 从未整进程跑过。
- 注意：主链开 dynamic filter 后全等 reward 组进不了 trainer，所以这必须是**独立的基础设施负控**（受控注入），不能等自然出现。
- 失败含义：不一致判 = 训练正确性阻断；publish 门控失效 = 版本账全线失真，判定级。

**B4【判定级】权重更新语义 + spans 真值（合并场景）**
- 测什么：在真实权重更新窗口内保持 ≥1 个在途 CC 请求继续生成（拍板后的主模式 retract 或 in_place），验证：(a) 更新期间在途请求的实际行为与该模式文档语义一致；(b) 引擎对跨更新请求报**多区间 spans**，我们的版本账/oracle 正确（含一个**受控跨更新单请求探针**：故意在长请求中触发更新，断言 spans 恰为两段——这是对"引擎漏报"这一本地不可证伪面的直接证伪手段）；(c) 更新后新请求取得新版本；(d) 若选 in_place：增量 R3（`routed_experts_start_len`）正确。
- 为何必须 GPU：`pause_generation` 全仓零真实调用；跨更新在途请求本地从未存在过；spans fixture 只验合同不验行为。这同时是 E1 生命周期项的语义半边。
- 失败含义：主模式行为与假设相悖 → 按实测简化或切另一模式（FA-5 场景 3 的既定出口）；spans 漏报 = staleness 账不可信，判定级。

**B5【判定级】发布链守恒真 driver**
- 测什么：真 `train_async` 进程上 applied↔update↔publish↔version 双向守恒（interval 语义）；全 skip 轮真的不调用 updater、版本不增；真实 update_weights 的耗时顺带采集（D 层数据）。
- 为何必须 GPU：真 driver/updater 从未执行；"updater 一进入就递增版本"类坑只有真栈暴露。

### 层 C：真实纵链真值——形态甲全链

**C1【判定级】RH2+Miles 主资格 E2E**
- 测什么：真 CC 二进制多轮（Anthropic 协议经 vendored adapter）+ 真 Docker sandbox + 真 SWE 探针任务（S1 已验证集）+ 真 grading + capture/stage/commit/身份链/eligibility → miles stock buffer → train conversion → faithful DIS → ≥2 optimizer step → 权重更新 → 新版本继续 rollout。覆盖数据形态：正常线性多轮、工具观察位单例 support、掉落轮（rewrite）、正控组（保证 reward 方差）、全零对照（走 filter 丢弃路径）；fan-out 若可促发（见 §4）。
- 为何必须 GPU：本地 e2e 的"模型"是 canned 固定 token 的 fake HTTP——**CC 从未启动过**（HARNESS_KIND="simple"）、Docker 全 fake、grading 返回 canned reward。CC 面对真实模型输出的行为（工具调用格式波动、上下文增长、重试）、adapter/capture 在真并发下的表现、评分容器与训练进程的资源共存，只能真机闭环。这是 R4 就登记的"形态甲集成闭环"最后一步。
- 证明什么：MQ-2 真实纵链闭合——生产入口发生一切，零 fake 注入。这是主交付的主体。
- 失败含义：按"stock miles 可跑 / RH2 链失败"与"stock 也失败"分流定位（机器 vs 栈 vs 我们的 adapter）。

**C2【判定级】fully-async 行为真值**
- 测什么：worker 常驻跨 step（producer 保温，不是每 step 重建）、rollout 与 training 真实墙钟重叠、ready queue 无重复消费、staleness 账目可解释、无泄漏无死锁。
- 为何必须 GPU：重叠/保温是墙钟与多进程行为；本地 asyncio 测试证明逻辑不死锁，不证明真 Ray 多进程 + 真生成延迟下成立。miles fully-async 从未在我们手上任何 GPU 跑过（上游 6+2 CI 是 H100 且非我们的链）。

### 层 D：容量/成本真值——决定拓扑与 T0-A（本地完全空白，盘点确认）

**D1【数据级→条件级】显存装载**：30B 训练侧（4/6 卡两种切分）+ optimizer + 激活，与 rollout 侧引擎 + KV cache 的真实峰值。4+4 需要重选并行拓扑（world=4 与 TP×PP×CP 整除约束）。装不下 → 该拓扑降 Conditional 限制项。
**D2【数据级】吞吐与等待比**：steady-state tokens/s、rollout wait ratio、权重更新耗时。**这直接裁决初始生产拓扑**：P3 实测我们的负载 rollout-bound（wait 0.82），6+2 意味着更少 rollout 卡——先验上 4+4 可能才是对的，用数据说话而不是默认 6+2。
**D3【数据级，T0-A 回填必交付】top_k=vocab-size 实测**：mask 体积/显存/带宽/延迟；加 top_k=32 一个诊断对照点。不交此数据，T0-A（正式实验采样配置）关不了。
**D4【数据级】zero-gradient scan 独立耗时**（P1-2 遗留，决定是否需要 fused 优化）。

### 层 E：生命周期真值——三项，不扩矩阵

**E1【判定级】更新打断在途 turn**（与 B4 同场景采集，单列为判定项）。
**E2【条件级】graceful shutdown**：停止后无孤儿 rollout worker/adapter 线程/未终结交付/容器（含评分容器）。本地 probe 是桩 docker——真值只有真机。
**E3【条件级】Ray rollout actor kill**：run-fatal 安全停机 + 缺口可观测（不承诺恢复——F2-4 递延语义原样）。

## 3. 明确不测（反 scope 蔓延）

S2/安全拦截（G10 独立，条件都不满足则明确 not_ready）；正式训练闸门翻转；模型能力提升；完整恢复矩阵/exactly-once/WAL；多 engine（单 engine 钉死，解锁前置已审计登记）；FSDP/VPP/CP>1；eval 质量（只做路径冒烟）；governed buffer/ledger 接线（首跑 stock buffer + run-fatal，既定范围收缩）；hermetic 逐字节复建验证（只记录 digest 作产出物）。

## 4. 内容依赖的拍板项（T0/确认级，随本文提请）

1. **retract vs in_place**（B4/E1 主模式）。**推荐 retract**：#2783 的 in_place 旧权重 KV 复用 bug 修复需先把 `extra_key=weight-version` 思路移植进 rh2 请求（额外前置工作且我们的 capture 路径绕过其修复点）；retract 重算 KV 无陈旧风险、语义保守、上游 fully-async 默认。in_place + 增量 R3 留作 Conditional 后续项。
2. **`--max-weight-staleness` 在线剔除**。**推荐 spike 不启用**（保持只算不拒 + 后置 judge 校验）：首跑样本量小，在线剔除让 batch 凑不齐会引入新变量；启用属训练准入语义，留正式训练前单独 T0。
3. **fan-out 覆盖失败的预注册处置确认**：真实触发依赖 compaction fork（Task 已禁用），首跑可能如实覆盖失败——处置 = 促发 fork（构造长上下文任务）或 owner 拍板当次豁免留痕，不删判定。
4. **6+2 与 4+4 的判定权重**：建议 6+2 作 bring-up 稳定配置（上游 CI 先例），4+4 作**目标拓扑数据采集**（D2 的 rollout-bound 论证）；两者都不单独构成 No-Go，拓扑最终选择由 D1/D2 数据 + owner 决定。

## 5. 失败分流原则（简）

任一早期硬门失败不消耗剩余租期重复同一失败：stock miles 失败 → 跑预置 P3/slime 短控制区分机器问题；stock 成功 RH2 失败 → 保全 artifacts 收卡回本地（不在 GPU 现场大段改码）；R3-on 失败 → 同配置 R3-off + stock R3 探针三角定位；判定为需本地开发 → 尽早释放 GPU。No-Go 的诚实回退路径 = 回本地完成 slime FA 剩余（FA-2 后续→接线→FA-5 本地），不假装租期内可切换。
