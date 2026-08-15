# FA 工作流 implementation-notes（三节制）

范围：`05-fully-async-execution-plan.md` 的 FA-0~FA-5 实现期记录。每任务一节，
只记重要事项。

## ⚡ 当前权威状态（2026-07-20，每次大轮次后更新——先读这页再读历史）

> 下面的历史轮次是**流水账**：早期结论可能已被后续轮次推翻。凡与本页冲突，
> 以本页为准；被推翻的机制在括号里标注了替代它的轮次。

**阶段状态**：FA-0 完成；FA-1 本机实现完成（codex 轮次 6~14 九轮审查全部
处置，closure 批次已落地）；FA-3 离线/FA-4 对拍完成（接线未做）；
**FA-2A 决策包 v4 已批准（2026-08-07，用户拍板 D1=A 带修订/D2=A/D3=A/
D4=A；D1b 延后清单见决策包 owner_decision）**；**F2-0 纯迁移已完成**
（commit f8580789，测试 917→921：capture_wire/glue→bringup/
docker_sandbox 三模块提升 src，experiments 留带 parity 测试的薄兼容壳，
GPU 链模块路径经壳保持可解析）；**F2-1a 四层身份：完成，codex 终核通过**（e5ddd13a 主体；一审 63e2772c；
二审 P0 触发修复循环熔断→所有权收敛重构 4e704d03；终核仅剩 P1
SessionAdapter Protocol 签名同步，已修）。**F2-2 验收前置登记**：稳定
SID 在 slime closed 集合下不可复用，需 F2-2 的每 physical attempt 新
session_auth_capability 解决（05 计划 F2-2 节已钉验收）。**F2-0b Observability V0：基础字段完成，生产接线未完成**（codex F2-0b
复核 4 P1 修正后的诚实口径——契约与提取器就位，但 43 个事件中生产代码
只命中约 4 个，其余按 owner 分批接线：**服务启动 6 事件归 BringupService
（startup_evidence timeline）**、execution 事件随各切片、model
调用区间填值随 F2-3、group/batch 事件随 F2-5/F2-6）。已闭合：clock_
domain=进程实例（同进程线程可互减，owner_role 区分线程）+ 原始
monotonic 时间戳；ModelCallAttempt 四原始区间（成对 start/end +
timing_clock_domain，**区间⟺domain 双向一致校验**——脱离时钟域的区间
拒绝构造）；server_timing = 严格模型 ServerTiming（白名单六键 + 非负
有限，污染键/负值挡在契约外；提取器只捕 ValidationError，程序错误照常
暴露）；audit 落**双时钟 wall 起止**（wall_start/end_monotonic +
epoch 副本 + wall_clock_domain_id，写 record 时各只读一次）不派生
chargeable。训前处理项（codex 复核二轮登记）：proc-{pid} 非严格进程
incarnation（fork 继承同值/pid 复用），F2-3/F2-4 前改含 incarnation 且
fork 后刷新的 ID；非法遥测计数随 F2-3。**F2-1b Outcome v2 与 crosswalk：
schema + crosswalk 完成（producer 接线不在本切片，归 F2-2 起——见 05
计划完成口径）**；codex F2-1b 审查三 P1 已闭合：① failure category
三分封闭集合（执行事实 7 值 = missing 唯一合法归因池 / grading 1 值 =
present_* 唯一 / 准入·控制·审计 5 值不进 finalize Outcome——staleness
是消费时刻判定，混入会把完整成员算成缺员）+ 13×3 显式矩阵测试；
② v2 强制四层身份（physical_attempt_id 必填、branch_id 必须 None），
crosswalk 加结构性前置门（branch 视角/身份不可重建 → legacy_unmappable，
证据可补 paid）；③ crosswalk fail-closed（证据 evidence_refs ≥1；结果
validator 强制 status ⟺ v2 在场性；permanent_rejection 迁移产物 =
**migrated_audit_only** 独立状态——只读 status/v2 的消费者拿不到被禁
轨迹）。二轮复核再闭 2 P1：④ 提取口改名 **migrated_v2()**（原名
trainable_v2 违反 v1 既有原则"训练资格唯一权威在 EligibilityReport"
——migrated 含 missing 迁移，迁移成功≠可训练；接口只过滤 audit-only
维）；⑤ 身份血缘矛盾 fail-closed（v1 与证据都带 paid 且不一致 →
identity_evidence_conflict/legacy_unmappable，不静默取舍）。非阻塞
递延：termination×failure 完整交叉表未拍板（schema 暂允许
completed+harness_crash+missing 组合），F2-2 producer 接线测试先行
兜底证明真实路径不产矛盾组合（05 计划已钉）。
`contracts/fa_runtime.py` 新增 TerminationKind 五族（与决策包 D1a 逐字
一致，集合等式测试保证并集=全集且两两不交）+ RolloutAttemptOutcomeV2
（completion 三值事实层 present_complete/present_truncated/missing；
三层分离钉子 model_call_regeneration_exhausted→model_proxy_failure→
max_regenerations_exceeded；勘误 2 通道 = reward_unavailable ⟺
task_outcome=unknown，评分基建故障不倒写 completion）；v1 冻结不改。
`contracts/outcome_crosswalk.py` = v1→v2 穷举规则表（42 组合全覆盖测试；
无证据不捏造→legacy_unmappable；permanent_rejection 永不映射 missing，
可迁移时落 present_* + legacy_admission_verdict 审计传递）+ 双版本读取
read_rollout_attempt_outcome。registry 注册 v2；"正式链只产 v2"守卫 =
src 扫描测试（v1 构造只许出现在契约定义/registry/crosswalk 三文件）。
待 S2 协调项：GradingFailureCategory 新值 test_execution_timeout
（contracts/grading.py S2 线程优先，D1a 第 2 条要求的三条件构造门随
其落地）。下一切片 = **F2-2 session capability + Runtime quiescence**
（验收已钉：旧 capability 被拒/新 attempt 不受 slime closed 集合与
turn counter 影响）；FA-5 未开工。闸门
`rh2_fully_async_training_path_verified` = **false**。测试基线 955。

**FA-2A 批准要点（实现必须遵守的边界）**：Observability V0 只记录不改
行为；audit_only 不放宽任何守卫、不产正式训练 batch；hard_wall 仅
termination trigger（completion 按事实推导，present_truncated 处置留
D1b）；不定义 chargeable_policy_seconds；不导出 trajectory.jsonl；
profile 选择/watchdog 数值/masked member 算法语义/熔断阈值全部延后
（D1b/FA-4/pre-RL）。

**当前有效的关键机制**（历史轮次里的旧形态全部作废）：

- capture 暂存：stage 单槽 + overlap **fail-closed**（轮次 9；轮次 8 的
  FIFO 已废弃）；commit 事务化 PENDING→COMMITTING→COMMITTED/ABANDONED
  （轮次 13）；registry/proxy 短临界区锁（轮次 13/14；终局 = FA-2A 单
  owner 重构，锁是明知要重写的脚手架）。
- poison 生命周期：active 绝不容量淘汰 → orchestrator 在**容器清理完成后**
  release 归档（轮次 11/12；轮次 10 的"unregister 即 release"已废弃）；
  poison 触发跨线程主动取消 harness（call_soon_threadsafe，轮次 10）。
- 交付定案：finalize 在 **commit（record_turn 成功）时刻**（轮次 8；stage
  时 finalize 已废弃）；abandon 事务化先关账再抛（轮次 12）。
- 模型边界：未知 SID fail-closed + 会话守卫 middleware 403（轮次 13）；
  404 一律转 503 + x-should-retry:false（轮次 9/10）。
- 审计：execution 终态 audit sink（含 timeline/timing/disposition）+
  attempt ledger **snapshot→写成功→ack** 事务（轮次 14；先 drain 后写已
  废弃）；正式链审计写失败 = FatalExecutionInfrastructureError → worker
  停机（轮次 14）。
- 非零 harness exit：与正式链的启动断言**硬耦合已解除**（轮次 14 推翻
  轮次 9——slime episode 超时返回 EXIT_TIME_BUDGET_EXCEEDED=-1 是正常
  终止；旋钮保留、glue 默认仍联动；结构化终止枚举是 FA-2A 前置定义项）。
- 恢复语义：halt → **整个 rollout actor 重启**（进程内线程重建不存在）。

**临时挡板登记（每个都有替代任务与移除条件；FA-2A 完成时逐个显式裁决）**：

| 挡板 | 加于 | 移除条件 |
|------|------|----------|
| overlap fail-fast（并行 subagent 被拒） | 轮次 9 | F2-3 request 级归属落地；且列入 `rh2_formal_training_allowed` 前置 |
| DuplicateActiveSessionError | 轮次 12 | **F2-2**（身份与 capability 真正分离后才可拆；F2-1a 只落了身份，二审确认移除条件后移） |
| 中毒 SID（含归档）拒绝 register | 轮次 11 | F2-1/F2-2 身份与凭证分离（poison 改绑 session/attempt） |
| StaticActiveCoordinator（永远 ACTIVE，只保守缺员） | 轮次 7 | FA-4 真协调器（consensus version） |
| ~~capture_wire/glue 住在 experiments/~~ | S1 沿革 | **已解除**（2026-08-07 F2-0，commit f8580789——src 唯一权威 + 薄兼容壳；壳兼容范围 = 导出对象 identity + 旧动态入口可解析，**不承诺旧模块全局变量重绑传播**） |
| ruff F401 豁免（s2_1_ingestion/resolve_image_digests.py） | 2026-07-24 | owner = S2 线程；S2 收敛后清理并删豁免；gate = 训前总审计前 |
| physical_attempt_seq 重启后从 1 重数 + `_attempt_seq` 随执行数无界 | 2026-08-07 F2-1a | owner = F2-4 checkpoint（seq 纳入 pending checkpoint / 有界化）；gate = 训前总审计前（codex F2-1a 复核递延项） |
| V0 timeline 43 事件仅约 4 个有生产调用点 | 2026-08-07 F2-0b | owner = 各切片（execution 事件随切片接线 / model 区间填值 F2-3 / group·batch 事件 F2-5-F2-6）；gate = 训前总审计前（codex F2-0b 复核 P1-1） |

**未闭合项**：见 05 计划 §6.1 递延表（P1×8 + P2×4）与 FA-2A 批次定义。

## FA-0 身份、版本与执行结果契约（2026-07-12 完成）

**交付**：`contracts/fa_runtime.py`（ExecutionIdentity / RolloutAttemptOutcome /
TrainingRuntimeWindow / ModelCallAttempt 四契约 + 三层身份与 mask 分离的模块级
定义）；真实 weight_version 管道（TurnTape/capture 记录逐轮透传 →
backfill 逐入训轮回填 → 握手 staleness 真实计算）；正式链启动断言；
`routed_experts_start_len` 扩展位（非 0 fail-closed）；D-FA-6 环境注入 helper +
上下文收缩检测；fully_async 表面契约测试 7 条。测试 647 → 684 全绿。

### 设计决策

1. **FA 契约注册走 CLI 聚合表**（`registry.EXTRA_SCHEMA_REGISTRY`），S1 核心
   registry 保持验收口径的 15 个冻结。`inspect_s1` 的收编对照相应改为
   "S1-9 五个是下界 + `rh2.fa.*` 前缀放行、未知前缀仍 FAIL"——S1 账本对
   S1 面的保护强度不变，FA 面归未来 `inspect-rh2-fa`。
2. **上下文收缩不加 gate 第八维**：七维是封闭枚举（`failed_dimensions`
   校验器拒绝未知名），加维度牵动 `GATE_VERSION`——而升版机制是 S2-0/S2-7
   的 TIER_CAP 解封职责，FA 不越权。改为**装配期 fail-closed**：
   `detect_context_shrink` 检出 → `SlimeBindingError("context_shrink_detected")`
   → 既有 abort 收口（`remove_sample=True`），语义同样是"轨迹退出基线"。
   检测默认只记录（`reject_context_shrink=False`，S1 行为逐字不变），
   正式 GRPO 基线配置必须置 True。
3. **fully_async 表面契约测试是源码级结构断言**：本地 venv 无 torch，
   slime 模块不可 import；文本 pin 足以在升级 pin 时抓住承重事实漂移
   （N1 吞异常形态、组长断言、阻塞 put、`_key`、pause/continue 端点、
   weight_version 记账）。行为级验证归 FA-5。
4. **weight_versions 回填语义**：逐入训轮真实值优先 → 缺失回退
   policy_version → 部分轮两者皆无则**整字段不写**（宁可无事实让 gate
   降级，不拼"真实+猜测"混合序列）。正式链（require_real_weight_versions）
   下任何入训轮缺真实值直接 fail-closed。
5. **staleness 真实计算只在正式链启用**（current − min(seen)，数值版本），
   S1 兼容路径恒 0/True 逐字不变——避免翻动 S1 已验收的握手 evidence 语义。
6. **consume-time 字段冻结禁令**：Outcome 的 `current_version_at_consume` /
   `worst_token_lag` 在 finalize 校验器强制 None；FA-3 assembler 消费时另行
   落账，不回写冻结记录。

### 偏离说明

- 计划原文写"上下文收缩 → gate 维度"，实现为装配期 fail-closed（理由见
  决策 2）；语义等价、机制不同，05 计划不改文（该节本就写的是目标语义）。
- "DISABLE_COMPACT inspector 探针在本地 harness 冒烟中验真"以 **stub 子进程**
  实现（`test_compaction_disabled_env_reaches_child_process`：env 准备 →
  子进程读回 `SLIME_AGENT_CC_EXTRA_ENVS`）；真实 CC 子进程的验真按计划
  挂 FA-5 短租。glue 的实际接线（在 GPU 机器的启动路径调用
  `ensure_claude_code_compaction_disabled`）留 FA-1——本地无法冒烟真实
  glue 路径，helper 与探针已就绪。
- `RolloutAttemptOutcome` 本任务只交付契约与测试，编排循环的发射接线归
  FA-2（PromptGroupAssembler 是它的消费者，先有消费者再接生产者）。

### 权衡

- 三层身份暂未强制挂进 TrajectoryProjection（会动 S1 冻结契约的必填面）；
  FA-1/FA-2 接线时以 sidecar/metadata 承载，投影 schema 是否升版随
  FA-2 定。
- `BackendHandshake` 未加 `attempt_outcome_ref` 字段（codex 轮次 3 曾建议
  方向）：等 FA-2 的 Outcome 发射点定了再挂引用，避免先造空字段。

### 开放问题

- `context_shrink_ratio=0.6` 是预注册黄线，FA-5 用真实 CC 轨迹校准
  （thinking 剥离的真实收缩幅度分布未实测）。
- P3 夹具往返测试依赖本地 evidence 目录（浅 checkout 自动 skip）——
  `inspect-rh2-fa` 建账时把该测试列为必跑项（evidence 在库，正常 clone
  不会 skip）。

## FA-0 follow-up（2026-07-12，codex FA-0 审查全 12 项采纳；原文存档
## `../s2/codex_reviews.md` 轮次 4）

- **严重 1（staleness 事实矛盾被 clamp 掩盖）**：`max(current-min(seen), 0)`
  的 clamp 删除——任何 seen 版本比 current 新即
  `weight_version_ahead_of_current` fail-closed（codex 反例 current=3/
  seen=[5] 现在必炸）。新增 `current_policy_version_provider` 注入点
  （FA-1 接 `engine.get_weight_version` 包装）；provider 缺席时回退
  config 值，注释明确该口径是"相对启动版本"、不得称实时 staleness。
- **严重 2（session 级收缩检测误杀子 agent）**：核实 CC 子 agent 与主
  agent 共享 session id（`claude_code.py` ANTHROPIC_AUTH_TOKEN=session_id
  → adapter 按 token 归组）。重构：session 级检测降为纯 audit 信号；
  **硬拒绝只在叶链自己的入链轮序列上执行**（lineage 内比较，子 agent 是
  独立叶链天然免疫）。负测试：主 agent 长上下文 + 子 agent 短上下文不拒；
  真 e2e：叶链内坍缩 → abort 形状 remove_sample=True。已知边界（诚实
  记录）：compaction 延续分支若经 REALIGN 把压缩前轮全部掉落，叶链级
  检测也看不见——正式基线的完整防线 = DISABLE_COMPACT 验真 + session
  级 audit 信号复核 + 叶链级硬拒绝三层，缺一不可。
- **严重 3（评分枚举统治执行期归因）**：新增 `RuntimeFailureCategory`
  13 值（proxy/推理服务/沙箱/harness/worker/评分基建/capture/对齐/
  staleness/安全/身份/契约/清理），`RolloutAttemptOutcome.failure_category`
  改用之；评分故障映射 grading_infra_failure + evidence 回链 GradingReport。
- **一般项**：present 强制 `current_version_at_finalize`；窗口
  old==target 拒绝（无前进的更新窗口是事实矛盾）；delivered attempt 强制
  weight_version；aborted attempt 加 `abort_fencing_token`（窗口归因双
  凭据）；`shrink_ratio` 域校验 (0,1) 开区间；正式链启动断言强制
  `reject_context_shrink=True`（不再只是注释）；混合序列注释改为精确
  两档口径（正式链 100% 真实、非正式链允许显式回退混合）。
- **测试项**：pin 守卫测试（reference/slime HEAD 必须 e848052a，在场即
  校验；缺席仍 skip，`inspect-rh2-fa` 建账后升为 fail）；误名的收缩测试
  重写为真 e2e（orchestrator 全链 + remove_sample 断言）+ audit-only
  对照。测试 684 → 692。

## FA-3 离线部分（2026-07-12 完成；接线部分待 FA-2）

**交付**：`adapters/slime/batch_admission.py`（预检器 + 层次化归一化 +
三视图纯函数）+ P3 事件夹具加载器 + 21 条测试（单元 15 + 差分 6）。
测试 692 → 713。

### 设计决策

1. **差分测试是预检器的正确性权威**：slime `utils/dp_schedule.py` 模块
   自述纯 Python、CPU-only 可测——差分测试直接 import **真函数**，同一
   输入比对成功/失败类别 + step 数 + 每 rank microbatch 数三项（J4/J5
   夹具 + 200 例随机扫，seed 固定）。预检器镜像 first-fit 装箱与对齐
   判定；`balance_by_flops`/`balance_data` 未镜像（P3/首训均关闭），
   开启即 fail-closed 拒绝——防止镜像面静默失真。
2. **B 类失败的机制确认**：J5 gbs16 的 "could only produce 23 mbs;
   need 24" = step0 恰 23 个样本（前 16 个有效 rollout 的真实 fan-out
   分布，事件元数据核实）+ align_to=dp2×1=2 + K0=23（全单箱）→
   round_up(23,2)=24 > 可拆分上限 23。夹具结构 100% 真实；样本 token
   总长不在事件元数据里（.pt 未同步），用校准值 20000 保持全单箱——
   报错里的 23/24 两个数字由结构决定，与校准值无关（测试 docstring
   已声明口径）。
3. **归一化实现放 adapter 纯函数层**（不进契约、不碰队列）：五条 E
   不变量以构造保证 + 属性测试钉死；广播不一致/身份矛盾 fail-closed。
   group5×8branch 定向回归直接吃 J4 真实事件（8 branch = 1 execution，
   分母 = 8 branch token 和）。
4. **torch 加入 dev 依赖组**（torch 2.13 CPU）：dynamic_filter 真调用
   测试（P3 崩溃形状复现 + 平铺形状通过）与 FA-4 torch 对拍都需要；
   运行时依赖面不变（只进 dependency-groups.dev）。

### 偏离说明

- 05 计划离线验收 5 要求 dynamic_filter 与 `_key` 都做真函数直接单测：
  **`_key` 的真调用做不到**——import 链穿 `sglang_rollout`（需要 sglang/
  ray，本机不装）。dynamic_filter 真调用已做；`_key` 保持源码级 pin
  （test_fully_async_surface），真调用留 FA-1 的 GPU 环境。如实降级，
  不冒充。

### 开放问题

- J5 gbs20 对照在预检器下 num_steps=1（41 样本中后 9 个 rollout 不足
  第二个 step 被真函数同款丢弃）——"尾部 rollout 静默丢弃"是 stock
  语义，FA-3 接线的 assembler 必须把它变成显式记账（丢弃即 log）。

## FA-4 对拍部分（2026-07-12 完成；custom loss 接线待 GPU 环境）

**交付**：`training/faithful_dis.py`（参考 loss + 解析梯度 + 指标）+
11 条对拍测试。测试 713 → 724。

### 设计决策

1. **三方对拍**：手算逐位 / 冻结权重有限差分（专测 detach 语义——若实现
   忘了 detach，接受 token 上必失配）/ torch autograd 同构实现
   （`ratio.detach()`，loss 与逐 token 梯度 1e-9 容差逐位）。torch 同构
   函数就是未来 Megatron custom loss 的形状雏形与对拍权威。
2. **denominator 语义预注册 v1 = provenance_tokens**（被拒 token 留分母、
   梯度为零）：与 slime stock TIS 的 `rollout_mask_sums` 口径一致，使
   IcePop 近似对照可同分母比较；`accepted_tokens` 第二实现保留用于消融。
   **FA-4 接线时须对照论文原文最终定死并回写**（codex 轮次 3 #7 的
   预注册要求——两档差异测试证明它直接改变有效学习率，不能含糊）。
3. ε 区间 0.8/3.0 按 codex 引注写入常数并标注"接线时对照原文复核"；
   区间语义 = 闭区间（边界测试用实际 ratio 值构造，避开 exp/log 浮点
   回环的 1ulp 假失败——这是实现细节里唯一踩过的坑）。
4. 全零有效 token → `zero_grad_step=True` + loss 0 + 无除零：FA-4 接线
   的"跳过 optimizer step"信号在参考层就位。

### 开放问题

- 论文忠实性只到"公式语义"层：denominator 档位、以及 top-p replay 是否
  参与 current logprob 计算（对拍清单第 5 项）要在接线时对照实测定死——
  参考实现把每个自由度做成显式参数，就是为了那时不需要改结构。

## FA-3/FA-4 follow-up（2026-07-12，codex 审查 12 项全部采纳；原文存档
## `../s2/codex_reviews.md` 轮次 5）

- **严重 1（DIS 区间勘误——本轮最重要修正）**：对照 SAO 论文 p.4 原文
  裁决，式 3 = `f(x)=x if 1−ε_ℓ < x < 1+ε_h else 0`——**开区间、
  (1−ε, 1+ε) 参数化**；coding 配置 ε=(0.8, 3.0) → 信任区间 **(0.2, 4.0)**。
  轮次 3 的"直接 ratio 边界"读法与我方闭区间实现 [0.8, 3.0] 都是错的，
  已改并在 05 计划 §5 勘误。注：论文正文写 "[1−ε_ℓ, 1+ε_h]" 闭括号与
  式 3 严格不等号自相矛盾，预注册以正式定义（式 3）为准并留注。
  detach 补记为 RH2 显式算法决策（论文未写 stop-gradient）。
- **严重 2（selected/deferred 报告）**：预检 `ok` 现在返回逐 step
  selected_rollout_ids + deferred_rollout_ids + 双侧 sample positions
  ——尾部不足一 step 的 rollout 是"延后"不是"丢弃"，lease/ACK 接线
  的 READY 回队语义有了数据面。差分测试同步比对 selected 集合
  （真函数 partitions 并集 == 预检 selected）。
- **严重 3（prompt_group_id 权威键）**：BranchDelivery 补 FA-0 稳定身份，
  归一化/三视图全部改键 prompt_group_id（group_index 降为 slime 批次内
  编号）；重复 (pg, exec, branch) 身份 fail-closed。
- **严重 4（execution 级归约层次）**：新增 `faithful_dis_loss_by_execution`
  ——branch 分子 → execution 共享分母（与 FA-3 rollout_loss_denominator
  互检）→ batch 按 execution 等权平均；branch-split 不变性、fan-out 隔离
  （对照平铺单分母的可区分差异）、DP 分区加权重组不变性三组测试钉死。
  CP/VPP 分布式归约留接线期真实并行环境。
- **严重 5（torch 全零 NaN）**：codex 实测属实——torch 对拍 helper 改
  clamp+门控（全零 → 可微零，backward 不断图，无 NaN），加专测。
- **输入校验全套**：NaN reward/advantage、重复 branch、零 token
  execution、非法并行/装箱参数全部 fail-closed；DIS 阈判移到 log-ratio
  空间（巨大 logp 差先拒绝、不执行 exp，溢出免疫）。
- **遗漏项处置**：失败类别差分比对（不再只"两边都失败"）；P3 分母回归
  改用 `loss_mask_ones`（可训练 token 口径，不是 response_lengths）；
  跨版本双 turn 场景测试（同 execution 内逐 token 各判各的）。
  仍留接线期的：top-p replay 进对拍、DIS 旁路启动负测试（接线配置面）、
  CP/VPP 分布式归约、lease/ACK 本体（FA-3 接线，等 FA-2）。
- codex 附加验证留档：5000 例随机调度差分全部一致（我方 200 例 seed 扫
  的独立加强）。测试 724 → 732。

## FA-1 持续 worker、有界队列与 proxy 边界（2026-07-12 完成；slime 薄壳入口留 FA-5）

**交付**：`adapters/slime/async_worker.py`（ContinuousExecutionWorker /
BoundedDeliveryQueue / ResourceLimits / ModelCallProxy / 重试白名单）+
17 条故障注入测试 + glue 两处接线。测试 732 → 749。

### 设计决策

1. **零 slime import 的运行时层**：所有组件可注入（task_source /
   execute_fn / coordinator / send_fn），本地故障注入即 FA-1 验收；
   slime `--rollout-function-path` 薄壳在 FA-5 短租的 glue 层落地——
   与 FA-0"slime 不可本地 import"的诚实分界一致。
2. **N1/N2 修复形态**：worker 账目守恒（dispatched == delivered + failed，
   异常执行必经 failure_sink 落账，sink 自身异常也不炸 worker）；交付
   走非阻塞 try_put + 待投列表，队列满只计数反压并暂停 top-up（反压
   传导到生产侧），reap 与主循环永不停摆。ABORTED 回队完全不使用
   （abort 在 proxy 层内部重生成，worker 面不存在 ABORTED 样本）。
3. **ModelCallProxy 守卫三条件的协议化**：重叠判定 = 失败时刻窗口
   phase != ACTIVE 或 update_epoch 相对发起时刻前进；版本前进等待 =
   phase==ACTIVE ∧ active_version 数值 > 发起时刻版本 ∧ fencing 与观测
   abort 窗口一致（epoch 更新时放行新窗口）。上限 max_regenerations=3
   （更新风暴防线），超限/超时/围栏不符/非重叠一律不可归因缺员。
   delivered 缺 weight_version 也按不可归因处置（契约强制 provenance）。
4. **半截输出的物理隔离**：non-delivered attempt 的响应只进
   proxy.audit_artifacts（审计面），capture_record_ref 强制 None——
   旧 token 悬挂负测试断言交付面只含最终 attempt 的 token。
5. **重试白名单代码化**（讨论稿 §4 逐行）：默认不在表中 = 只执行一次；
   评分段 max_attempts=2（首次+1）；full-jitter 封顶 min(8s, 0.5·2^k)。

### 偏离/递延说明

- `_key` 真函数单测仍不可本地做（import 链穿 sglang_rollout）——FA-1 的
  GPU 侧遗留，与 FA-3 时的口径一致；源码 pin 在位。
- glue 接线两处：async_start 急切合并 DISABLE_COMPACT（幂等，evidence 记
  `cc_compaction_guard_envs`）+ SlimeBindingConfig 两旋钮
  （RH2_REQUIRE_REAL_WEIGHT_VERSIONS / RH2_REJECT_CONTEXT_SHRINK，默认 0
  = S1 行为逐字不变）。glue 在本机不可冒烟（aiohttp/slime/docker 链），
  改动为静态审查级——FA-5 短租首个验证项。
- 协调器的**生产端**（trainer 侧发布 TrainingRuntimeWindow 的 Ray actor）
  属 FA-4 接线/FA-5；本轮交付其消费端协议（CoordinatorView）与全部
  边界行为。

### 开放问题

- worker 退出语义 = 显式 stop + 账目清零；若消费者死亡且队列满，run()
  不自行放弃（待投样本不丢）——FA-2 assembler 侧需要配 watchdog/超时
  策略（组 deadline 已在计划内）。
- max_regenerations=3 是预注册值（更新间隔 » 单轮解码时长时理论上
  1 次就够）；FA-5 实测更新风暴形态后校准。

## FA-1 follow-up（2026-07-13，codex 审查全项采纳；原文存档
## `../s2/codex_reviews.md` 轮次 6）

- **严重 1（组件未进生产路径）**：新建 `experiments/fa_bringup/rollout_entry.py`
  ——slime `--rollout-function-path` 的真实 FA 入口，组装 worker/queue/
  limits，从 data_buffer 取组、逐 execution 分派 `args.rh2_orchestrator.
  generate`、interim 聚合器按组收齐/整组显式弃置/收满批次返回。**零
  slime import**（Sample 全程鸭子类型）→ 本地假件测试覆盖全部编排逻辑，
  GPU 侧只剩"slime 真把它当入口调"（FA-5 首检项）。FA-2 接缝显式：
  interim 聚合器整体替换为 assembler，worker 输出形状保持。开发中自查
  补了一个真缺口：源枯竭 + 批次未满会永久空转 → 加 `batch_starved`
  饥饿超时。
- **严重 2（sink 失败静默）**：failure_sink 抛异常 → worker 内部
  `unrecorded_failures` durable fallback + **run-halt**（停止 top-up、
  drain 后抛 `WorkerHalted`）——"账平但无记录"形态被消灭。
- **严重 3（生命周期）**：取消的 execution 按失败落账；task_source 异常
  → halt（在途照常收尾）；worker 自身被取消 → finally 取消并 await 全部
  在途、逐个落账再传播；stop 后消费者死亡 → `drain_timeout_seconds` 到期
  把未投样本进 `abandoned` 显式记账退出。账目守恒扩为
  dispatched == delivered + failed + abandoned。
- **严重 4（attempt 身份）**：`proxy.call(execution_scope, turn, send)`
  ——attempt id = `{scope}/{turn}_a{n}`，并发 rollout 同名 turn 不冲突
  （交错鲁棒的并发测试）。
- **严重 5（capture 事务）**：delivered 改**两阶段**——proxy 返回
  `DeliveredDraft`，调用方 capture 持久化后 `finalize_delivered(ref)` 落账；
  未 finalize 的交付在 `unfinalized_deliveries` 对账可见。悬空 evidence
  修复：所有 evidence_refs 先 `_store_artifact` 再引用（存在性测试）。
- **严重 6（版本放行漏洞）**：恢复必须**达到 abort 窗口 target_version**
  ——同 epoch 要求 active==target（fence 一致）；更晚 epoch 要求
  active>=target；codex 反例（before 3/target 5/恢复 4）现在正确拒绝
  （version_regressed_across_epochs），另加同 epoch overshoot 矛盾检查。
- **遗漏项**：audit_artifacts 改有界（digest+256B 预览，FIFO 淘汰计数，
  完整体交可注入 artifact_sink）；ResourceLimits 真实接入（worker 的
  execution 圈 sandbox 类、proxy 的 send 圈 model_call 类，各有生效
  测试）；`max_pending_out` 改 `>=` 并校验；retry 加 `NonRetryableError`
  + `retryable` 谓词（永久错误不烧预算）+ RetrySpec 域校验；proxy 加
  `attempt_timeout_seconds`；glue 布尔旋钮改 `parse_bool_env_flag` 严格
  解析（只认 0/1，拼错即炸）；glue 注入 `current_policy_version_provider`
  （= capture registry 逐轮引擎版本的数值最大值，回退启动探针值）。
- **场景 21 的落点修正（重要）**：初版把 eval fail-fast 放进
  `orchestrator.generate`，被既有测试当场揪出——**eval 占位形状是 S1 的
  正式面**（E10 定案：训练与评测同链路）。拒绝移到 FA 入口
  `generate_rollout_async(evaluation=True)`（与 stock fully_async 的
  raise 同位）；S1 路径支持 eval、FA 路径拒绝 eval 是设计差异，两条路径
  各有测试钉死。
- 测试 749 → 768（worker/proxy 重写 29 条 + 薄壳 7 条）。

## FA-1 follow-up 2（2026-07-13，codex 轮次 7 全项采纳；原文存档
## `../s2/codex_reviews.md` 轮次 7——五个 P0 全部属实）

- **P0-1（同步接口不兼容）**：slime `call_rollout_fn` 不 await——注册路径
  改为同步 `generate_rollout`（内部用 slime `run()` 驱动，本地回退
  asyncio.run）。**真 slime 契约测试**落地（torch dev 依赖使
  `slime.rollout.base_types` 可本地 import）：用 slime 自己的
  `call_rollout_fn` 调我们的入口，断言产物是 `RolloutFnTrainOutput` 且
  samples 不是 coroutine——codex 探针的直接回归。
- **P0-2（启动挂载缺失）**：glue 新增 `ensure_fa_started(args)`（与
  custom_generate 首调用共用 BringupService 单例）+
  `build_fa_sampling_params(args)`（从 slime args 字段构造，缺字段
  fail-closed——仓库此前没有任何代码写 rh2_sampling_params）；FA 入口
  缺挂载时先经 glue 引导再 fail-fast。
- **P0-3（预取丢失）**：FaRolloutService 持久化——worker/queue/collector
  跨 collect_batch 保温（真 fully-async：训练时后台继续生成），多出的
  完整组留在队列/结余表供下批消费；显式 `shutdown()` 走 drain 协议。
  codex 探针（batch=1/concurrency=8 丢 15 个执行）转为零丢失回归测试
  （5 组 5 批全取回）。
- **P0-4（proxy 未接线）**：capture_wire 的 `rh2_call_sglang_generate`
  现在经 proxy 调用（send 闭包抽出，原直连路径仅在 proxy 未装配/非 rh2
  会话时保留）；glue 启动时装配 proxy + StaticActiveCoordinator（真协调
  器 FA-4 接线前的保守替身：**任何中断不可归因 → poison + 缺员**——
  没有窗口事实就不猜归因）。新增：`SessionPoisonRegistry`（不可归因/
  预算耗尽/客户端取消 → 整 session 中毒，后续 CC 退避重试快速拒绝——
  codex 实测 CC 2.1.205 对 5xx 指数退避且 20s 不放弃，仅 turn 去重不够）；
  **episode deadline 传播**（attempt 超时与等待超时被剩余预算截断，
  不足一次重生成即 poison+缺员）；**发前 ACTIVE 等待**（明知更新中不发
  注定被 abort 的请求）；CancelledError 原样传播但先落账+poison（aiohttp
  handler_cancellation 链保持）；两阶段 finalize 接到 stage 点（暂存即
  本进程持久化点）。
- **P0-5（provider 语义）**：`_latest_engine_version` 权威化——先取引擎
  `/get_weight_version`（trainer 更新后即便无新成功响应也是新版本）；
  registry 最大值降为**交叉检查**（大于权威值 = 版本管道错乱 fail-closed）；
  HTTP 失败时正式链 fail-closed、bring-up 如实降级为"相对最近观测"。
- **一般项**：audit 淘汰改 live-count + digest tombstone（`audit:` 引用
  永远可解析；sink 成功直接返回持久外部引用）；`abandon_delivered(reason)`
  给 unfinalized draft 显式出口；interim collector 弃置即删桶 + 迟到成员
  计数（100 组泄漏回归）；dead-consumer 测试改真实分派后 stop（原
  dispatched=0 空验证）；`_build_service` 构造并传入 ResourceLimits。
- **CC 重试实测留档**（codex 本机 2.1.205，fake endpoint）：连接保持时
  至少等 12s 不重试；对 500 指数退避（0.58/1.17/2.08/4.80/8.20s，20s 内
  6 次不放弃）。FA-5 用容器内同一 tarball 复测；本地 fake-endpoint 故障
  注入战役（30/60/120/300s 延迟、429+Retry-After、半 SSE 断连、重试 body
  一致性等）列为 FA-5 前的独立本地任务。
- 测试 768 → 797。仍留 FA-2/FA-5 的：assembler 替换 interim 聚合器、
  真机验证 slime 调用入口与 CC 真实二进制行为。

## FA-1 follow-up 3（2026-07-13，codex 轮次 8：6 P0 + 源码引导 CC 实验；原文
## 存档 `../s2/codex_reviews.md` 轮次 8，CC 行为证据见本目录两份报告）

- **P0-1（finalize 早于真实 SSE flush）**：finalize_delivered 从 wire 的
  stage 时刻移到 **commit（record_turn 成功）时刻**——CC 的 SSE flush 发生
  在 slime `_respond()`（wire 返回之后），stage 时 finalize 会造成"delivered
  但 CC 没收到"虚假交付。ProxyCallResult 挂进 PendingTurn；unregister 对
  未 commit 的 draft 显式 `abandon_delivered`。capture ref 改用真实
  request_id（不再是复用的 `staged:sid:tN`）。
- **P0-2（poison/非零 exit 不强制拒绝）**：orchestrator 加可注入
  `session_poison_check`（glue 接 `registry.poison.is_poisoned`），harness
  返回后复检——执行期中毒即整 execution 缺员（SlimeBindingError 收口成
  abort 形状），已捕获的 partial trace 全部作废；正式链另加
  `reject_on_nonzero_harness_exit`（默认 False = S1 兼容，非零退出可能是
  合法任务失败负样本；True 时训练守卫下的非零退出可疑到拒绝）。
- **P0-3（不可归因分支漏 poison + 恢复等待无视 episode deadline）**：
  call() 改薄包装——**任何** UnattributableModelCallError 在外层统一 poison
  （发前等待超时/版本恢复超时/fencing 不符/版本回退此前漏 poison）；
  `_wait_version_advance` 接 episode 绝对 deadline（此前独立固定 60s，
  与 attempt1+attempt2 生成叠加可远超 episode 预算）。
- **P0-4（重生成复用同一 rid）**：rid 生成移进 `_send_once`——每个 attempt
  独立 rid，`/abort_request` 精确指向被 abort 的那次。
- **P0-5（worker 跨 batch 崩溃静默重启）**：`_ensure_worker` 发现旧 task
  已 done 时**先 `.result()` 传播异常**——WorkerHalted 必炸给启动方，
  正常退出则报 `worker_already_exited`（已 shutdown 不自动重启）；重启只
  能走显式新建 service。"故障后训练不得继续"成为硬规则。
- **P0-6（同 session 并发覆盖 capture）**：`pending` 改 **FIFO 队列**
  （dict[sid, list]）——并发暂存不再静默覆盖丢数据，commit 按序弹最旧，
  `concurrent_overlap_seen` 计数。完整 request/turn 级归属（record_turn
  传 request_id）需改 slime 签名，留 FA-2/FA-5；本版消除的是静默丢数据。
- **CC 训练守卫升级**：`ensure_claude_code_compaction_disabled` →
  `ensure_claude_code_training_guards`（四变量：DISABLE_COMPACT=1 +
  CLAUDE_CODE_MAX_RETRIES=0 + DISABLE_NONSTREAMING_FALLBACK=1 +
  UNATTENDED_RETRY=0，源码 + CC 2.1.205 实测背书）；冲突检测（用户不得
  覆盖）；`assert_adapter_status_not_404`（CC 对流式创建阶段 404 绕过
  fallback 开关，adapter 任何错误路径不得返 404）。
- **P1**：host_launch.sh 固定 **CC 2.1.205 + sha256 校验**（原 `latest`
  不可复现）；session_deadlines/turn_seq 在 unregister 时清理（有界）；
  provider 同步 requests.get 保持同步但注释澄清它只在握手构造时算一次、
  不在 wire finalize 热路径。
- **CC 行为证据入库**（codex 本机 2.1.205 + fake endpoint，两份报告 +
  探针套件 + 34 个 JSON 证据）：500/429/断连指数退避实测、120s+ 无重试
  等待下界、404 fallback 例外、`proxy_deadline < CC API timeout <
  harness hard-kill` 不变量。**探针套件是版本画像/漂移检测器**，升级 CC
  必须先生成新证据人工裁决，不许改旧期望值让测试变绿。
- 测试 797 → 831。**明确留 FA-5 真机**（本机 fake endpoint 代替不了）：
  真 CC 二进制被 execution owner 主动终止（sandbox kill）、真 SGLang
  rid/abort_request 四方对账、容器内 tarball sha256/版本 fail-fast、
  pause_generation abort/hold 语义、Linux x64 vs macOS arm64 行为差异。
  **明确留 FA-2**：request/turn 级 capture 归属（改 slime record_turn 签名）、
  interim collector 替换为 assembler、worker 显式 recovery API。

## FA-1 follow-up 4（2026-07-13，codex 轮次 9：2 个确定性 P0 + 4 个接线缺口；
## 原文存档 `../s2/codex_reviews.md` 轮次 9）

- **P0-1（deadline 仍漏传——轮次 8 修复失败的修复）**：守卫 3 调用点真正
  传入 `deadline_monotonic`。**过程教训（重要）**：轮次 8 的修复用了无
  assert 的文本替换（静默未生效），而配套测试设 deadline=3 < 发前预算 5，
  在进入恢复等待前就以预算不足退出——**修复没生效 + 测试假阳性双重漏网**。
  新测试断言三件事：send 恰被调用一次（真进入 abort→恢复分支）、失败原因
  是 `version_did_not_advance`、失败时钟 ≤ episode deadline（不是独立 500s）。
  规矩固化：文本替换必须带 assert；修复测试必须证明"真走到了目标分支"。
- **P0-2（FIFO 乱序串账）**：轮次 8 的 FIFO 在并发完成乱序时会把请求 A 的
  token/logprob/weight_version 记到 B 名下（slime 同 session 请求是独立
  asyncio task、record_turn 按完成序到达；串账比丢数据更危险——结构合法
  内容错误的训练轨迹）。改 **fail-closed**：stage 遇 overlap → poison +
  两轮全 abandon（完成序未知，都不可信）+ `CapturePendingOverlapError`。
  含义：request 级归属（record_turn 传 request_id，改 slime 签名）落地前，
  并发同 session 模型调用（CC 并行 subagent）会 fail-fast——这是**正确性
  优先于可用性**的显式取舍，request 级归属定为 **FA-2 第一验收项**。
- **P0-3（formal 链没启用非零 exit 拒绝）**：接受 codex 对我轮次 8 理由的
  纠正——任务失败负样本 = CC **exit 0** + grader reward=0；CC 非零退出只
  可能是 harness/API/进程失败。启动断言强制耦合：`require_real_weight_
  versions=True` 必须同时 `reject_on_nonzero_harness_exit=True`；glue 默认
  联动（RH2_REJECT_NONZERO_HARNESS_EXIT 默认随 require 旗标）。
- **P0-4（poison 不主动终止）**：SessionPoisonRegistry 加 `subscribe/
  unsubscribe`（poison 同步回调通知，已中毒立即回调）；orchestrator 把
  harness run 包成 task，poison 即 `task.cancel()`——不再等 CC 自退（404
  fallback 已证明客户端自退不可靠）。取消区分：poison 触发 → 收口缺员
  abort；外层取消 → 原样传播。e2e 测试：挂起 driver 被主动取消 + abort
  形状 + 订阅清理 + sandbox 照常清理。
- **一般项**：404 守卫真接线——`rh2_no_404_middleware`（纯 aiohttp，路由级
  本地测试：未知路径/显式 404 → 503 + `x-should-retry:false`）+ install 时
  patch `BaseAdapter.__init__` 挂进 app；host_launch.sh **每次校验** sha256
  （缓存坏文件不再绕过）+ 临时文件下载 + 校验通过原子 mv；
  StaticActiveCoordinator 加 TTL 缓存（默认 2s——provider 是同步 HTTP，
  此前 proxy 热路径每次窗口读取都打一次引擎端点，32 路并发会串行阻塞
  event loop；版本至多滞后 TTL 秒，FA-4 用 consensus version 取代）；
  有界性收口：poison registry max_entries=4096 FIFO 淘汰、audit tombstone
  上限 8×max_artifacts（超限丢最旧只留计数）、weight_versions 随会话清理
  （registry 交叉检查从此只覆盖存活会话，如实降级）。
- 测试 831 → 835（+deadline 真分支、overlap fail-closed、poison 主动取消
  ×2、404 路由级、订阅即回调；净数受重写抵消）。
- FA-2 验收项排序更新：**第一项 = request 级 capture 归属**（改 slime
  record_turn 签名或 ContextVar 传 rid），落地后解除 overlap fail-fast。

## FA-1 follow-up 5（2026-07-13，codex 轮次 10：双线程拓扑 2 P0 + registry
## 并发/生命周期 2 P0；原文存档 `../s2/codex_reviews.md` 轮次 10）

本轮主题：**所有既有测试都跑在单事件循环里，而生产是"Ray actor loop +
aiohttp adapter 线程"双线程拓扑**——四个问题全是这个盲区的产物。

- **P0-1（跨线程取消不生效）**：poison 从 adapter 线程发出，回调里直接
  `harness_task.cancel()` 非跨线程安全（codex 双线程探针：task 未取消、
  账面却显示 subscriber 已处理——`_invoke` 吞异常加重了误导）。修复：
  orchestrator 捕获 `owner_loop = get_running_loop()`，回调走
  `owner_loop.call_soon_threadsafe(task.cancel)`；`notify_failures` 计数
  取代纯吞。新测试从**真 threading.Thread** 发 poison，断言 owner loop
  中的 task 收到 CancelledError（修复前该测试永久挂起）。
- **P0-2（middleware 没装到唯一的生产 adapter）**：glue 顺序是先
  `AnthropicAdapter(...)` 再 `install_capture_wire()`——构造器 patch 只
  影响之后创建的 adapter，对已存在的生产 adapter 无效（codex 探针：
  before=false / after=true）。修复：`ensure_no_404_middleware(app)`
  幂等直挂 + `assert_no_404_guard_installed` 启动前断言；glue 按生产序
  直挂到 `self.adapter.app`；测试按生产序复现（裸 app 断言先红后绿）。
- **P0-3（registry 跨线程丢通知竞态）**：check-then-subscribe 与
  poison-then-extract 之间的窗口会让回调永不执行。修复：threading.Lock
  原子化全部状态转换，回调复制后**锁外**调用（防死锁）；200 轮双线程
  barrier 交错测试钉死。
- **P0-4（FIFO 淘汰活跃毒）**：max_entries 淘汰假设"最旧已终止"但没有
  termination ACK（反例：max=1 时 A 被 B 挤出，A 的后续请求重新通过
  check）。重构生命周期：**active poison 绝不容量淘汰**（数量受 rollout
  并发自然约束），`release()`（= CaptureRegistry.unregister 的清理 ACK）
  后转有界归档摘要（归档后 is_poisoned 仍真，audit 面保留）。
- **一般项**：glue 配置**持久 artifact_sink**（落盘 ARTIFACT_DIR/
  model_call_audit/{attempt}.json，evidence_refs 从此指向外部持久路径，
  不受内存 tombstone 上限影响；正式链断言 sink 在场）；容器内
  `claude --version` **精确比较**（观测值含 RH2_CLAUDE_CODE_VERSION=
  2.1.205 才放行，结果存 self.cc_version_observed 供 startup evidence）；
  TTL 轮询的残余同步阻塞如实记录——FA-4 用 coordinator 发布的全引擎
  ACK consensus version 彻底替换（05 计划 FA-4 增补项）。
- 测试 835 → 852（+真线程取消、竞态窗口 200 轮、active 不淘汰、
  unregister→release、生产序 middleware；847 基线含并行 S2 变更）。
- codex 确认已修好的部分（轮次 9 全项）与"FA-2 第一验收项 = request 级
  capture 归属"维持不变。artifact sink 与容器版本断言已按其要求在租卡
  前完成，不留真机现场。

## FA-1 follow-up 6（2026-07-13，codex 轮次 11：2 正式链阻塞 + 2 身份/生命
## 周期项；原文存档 `../s2/codex_reviews.md` 轮次 11）

- **P0-1（启动探针必崩）**：轮次 8 把 `registry.pending` 改成
  `list[PendingTurn]` 时漏改了 `_run_startup_checks` 的消费点（仍按单对象
  取 `.raw_response`）——真实 GPU 启动会在训练前 AttributeError。修复：
  新增形状权威 `CaptureRegistry.single_pending_turn(sid)`（恰好一条；空/
  多条显式报错），glue 探针改走它；本地测试覆盖三种形状。**这是"改容器
  形状必须全仓搜消费点"的教训**——852 条测试没有一条走到该入口。
- **P0-2（正式链 sink fail-open）**：`_store_artifact` 此前吞 sink 磁盘
  错误退回内存 `audit:` 引用（磁盘满/权限错时训练继续、evidence 悬空）。
  修复：`ModelCallProxy(sink_required=True)`（glue 接
  `require_real_weight_versions`）下 sink 写失败抛
  `ArtifactSinkWriteError`（UnattributableModelCallError 子类 → 外层统一
  poison + 缺员）；bring-up 保留退回。glue sink 加固：sha256(attempt_id)
  文件名（清洗截断不再碰撞）、临时文件 + fsync + os.replace 原子落盘、
  内容含完整 payload sha256（repr 截断只是预览）、返回相对 opaque 引用
  （不泄漏绝对路径）；async_start 做一次 write/read/delete 启动探针。
- **身份 3（SID 复用 vs 毒归档）**：`_session_id` 的稳定 ID（task+index+
  group）跨补采/epoch 会复用。registry 侧兜底两条：`subscribe` 对**归档
  毒**也立即回调；`CaptureRegistry.register` 对中毒 SID（含归档）直接
  SessionPoisonedError（不让 harness 带毒起跑）。**execution 唯一身份
  （SID 绑 RolloutExecutionIdentity + nonce，poison 以 execution 为键）
  与 request 级 capture 归属并列为 FA-2 第一项硬验收**。
- **身份 4（release 不是真 ACK）**：轮次 10 把 release 挂在 unregister
  （drop_session 时）——但容器清理在其后。修正时序：unregister 只关会话
  不释放；orchestrator 注入 `session_poison_release`，在 finally 的
  `cleanup_completed` 之后调用（harness 终止 + 会话撤销 + 容器清理全完成
  才归档）。
- **一般项**：容器版本改 **token 精确比较**（子串判断会放过
  `12.1.205-x`）；`cc_version_observed` 落盘为独立 evidence 文件
  `cc_version_observed.json`（安装晚于 startup_evidence.json 写出，修正
  轮次 10 "进 startup evidence"的不实表述）；notify_failures 上锁 + 有界
  失败记录（64 条）；TTL 轮询/consensus version 如实递延 FA-4。
- 测试 852 → 870。codex 确认轮次 10 四项修复全部成立。
- **FA-2 第一项硬验收（更新）**：execution 唯一身份 + request 级 capture
  归属（两者一体：SID/poison/capture 都以 execution identity 为键）。

## FA-1 follow-up 7（2026-07-13，codex 轮次 12：abandon 绕过 fail-closed 的
## P0 + 重复注册守卫；原文存档 `../s2/codex_reviews.md` 轮次 12）

- **P0（abandon 路径绕过 sink fail-closed）**：轮次 11 的 sink fail-closed
  只覆盖 call() 内部；`abandon_delivered` 在 call() 返回**之后**被调，sink
  失败会抛 ArtifactSinkWriteError 但不经过外层统一 poison——draft 仍
  pending、账上零记录，且 unregister 的清理路径把异常当普通 cleanup
  failure 吞掉，**构造好的训练样本可能带着不完整交付账继续走**（codex
  确定性探针复现）。按其建议落三层防线：
  1. **评分/Gate 前边界断言**：`CaptureRegistry.assert_session_clean(sid)`
     （pending 暂存轮或该 sid 前缀的 unfinalized draft 在场 → poison +
     拒绝），orchestrator 注入 `capture_boundary_check` 在 assemble 前调用；
  2. **unregister 先 poison 再 abandon**：leftover draft 存在即先
     `uncommitted_draft_at_unregister` poison，abandon 的 sink 异常不传播
     （`abandon_evidence_failures` 计数可见）；
  3. **abandon 事务化**：先关 draft、落最小 FailureFact（evidence_refs=[]），
     再抛 ArtifactSinkWriteError——"抛了异常但 draft 还 pending"的中间态
     被消灭。组合测试按 codex 点名补齐（成功交付 + flush 失败 + sink 失败）。
- **重复注册守卫（FA-2 硬阻塞的临时挡板）**：健康 SID 并发重复 register
  此前会静默覆盖 hook/pending/weight_versions——现抛
  `DuplicateActiveSessionError`（顺序关旧开新仍放行）。FA-2 第一项验收含：
  并发同题组不共享 SID、attempt id 全局唯一、artifact 禁静默覆盖、poison
  按 execution 隔离。
- **一般项**：`_cleanup_container` 意外异常（docker socket OSError 等）
  结构化收口——CleanupFailureRecord(step=container_cleanup_exception) +
  `cleanup_quarantine` 隔离队列，异常不再覆盖 rollout 结果；**清理未确认
  成功时 poison 不 release**（active 保持拒绝力）。版本 evidence：进程内
  只写一次 + 临时文件原子 replace（并发竞写消除）+ 失败计数打印不静默。
  artifact digest 统一 canonical 口径（`canonical_artifact_bytes` 内外共
  用）；sink 文件已存在时 digest 相同幂等返回、不同即身份碰撞报错（禁
  静默覆盖）；契约显式定名 **digest-only evidence**（刻意不存完整私有
  payload——与密钥/最小化纪律一致，preview 有界）。
- codex 澄清其看到的 inspect 失败是并行 S2 线程的瞬时脏工作树（我方验证
  当前 PASS，bundles_v2/spec_vendor 已由 S2 线程收敛）。
- 测试 870 → 878。codex 认可"可以开始 FA-2，但先修本 P0 + SID 唯一化为
  FA-2 第一个提交"——本 P0 已闭合。

## FA-1 closure（2026-07-13，codex 轮次 13 完整审计第一批；原文存档
## `../s2/codex_reviews.md` 轮次 13——全链路审计，非增量 diff 审查）

codex 本轮从 slime 调用入口走完全链（RolloutManager→entry→worker→
orchestrator→adapter 线程→proxy→SGLang→capture→评分→collector→转换器），
判定："FA-1 不是失败实现……问题主要来自把局部正确组件接入真实三线程
拓扑、长运行状态和安全边界时的所有权缺口"。按其实施顺序执行第一批：

- **P0-1（未知 SID 直连 SGLang 的安全旁路）**：wire 对未注册 SID 从
  "直连放行"改 **fail-closed**（`UnknownSessionError`——旧行为 = 绕过
  proxy/poison/版本/deadline/限额/capture 的未登记推理代理，adapter 又
  绑 0.0.0.0）；新增 `build_session_guard_middleware`（bearer 能力预检：
  未知/已关/中毒会话 HTTP 层 403 + x-should-retry:false，不产生 SGLang
  请求；/healthz 放行），glue 挂到生产 adapter app。启动探针的会话是
  显式 register 的，不受影响。绑定地址默认值改动风险大（容器桥接可达性
  依赖 GPU 环境），FA-5 用 ADAPTER_BIND_HOST 显式设定——递延已登记。
- **P0-2（边界检查在 drain 屏障之前）**：`finish_session`（内部
  shutdown_session 才等/取消 in-flight turn）**前移**到一切检查之前；
  顺序改为 drain → poison 复检 → 非零 exit → 边界断言 → 冻结
  hook.records 快照。消除 false reject（正常轮还在 flush 就被拒）与
  false accept（drain 期间才 commit/overlap/sink 失败无第二次检查）。
- **P0-3（CaptureRegistry/proxy 非线程安全 + commit 中点悬挂）**：
  registry 全部共享容器进短临界区 `threading.Lock`（锁内只移动所有权，
  hook/磁盘/回调全在锁外）；commit 事务化 PENDING→COMMITTING→
  COMMITTED/ABANDONED——hook 中点异常 poison + abandon draft（codex 探针
  的"永久悬挂"消灭）；hook 后复检会话仍在（与 unregister 竞态时本轮
  poison+abandon，不给已销毁会话追加版本——KeyError('race_sid') 根修）；
  重复 finalize 不再静默吞 ValueError（poison + 计数 = 契约违规可见）。
  proxy 的 attempts_ledger/_pending_drafts 加 `_ledger_lock`。50 轮真双
  线程压力测试 + 中点异常 + 竞态复检三条回归钉死。
- **P0-4（limiter 假配置）**：model_call 限额真接生产 proxy（glue
  `model_call_limits`，env RH2_FA_LIMIT_MODEL_CALL；所有权 = adapter
  线程 loop）；评分并发接 GradingQueueConfig（env RH2_FA_LIMIT_GRADING）；
  FA 入口删掉无消费者的 model_call/grading_container 假键（只留 worker
  真消费的 sandbox 类，绑 AsyncLoopThread）——**不跨 loop 共享 semaphore**。
- **P0-5（FA 路径审计只在内存）**：orchestrator 注入 `audit_sink`，每个
  execution 终态写一次 `fa_execution_audit.jsonl`（steps/失败/清理/收缩
  + **按 execution drain 的 ModelCallAttempt ledger**——drain 后热内存即
  清，P1-4 的 ledger 项随之闭合）；正式链落盘失败 fail-closed 上抛。
  audit 增 `session_id` 字段（drain 键）。
- **P1-6（open_session 泄漏）**：glue PerRolloutAdapter.open 事务化——
  底层 open 失败回滚 registry 注册。
- **05 计划更新**：FA-2 分批重排（第一批 = F2-1~6 身份基座：身份贯穿/
  身份凭证分离/request 级归属/预取恢复语义三选一/collector 组不变量/
  attempt manifest；第二批才是 assembler 状态机）；§6.1 新增 P1×8+P2×4
  递延登记表；FA-5 验收增项 10 条；闸门重申（P0 已闭但 F2 完成前
  `rh2_fully_async_training_path_verified` 保持 false；StaticActive 在位
  期间不得声称生产透明重生成）。
- 测试 878 → 895。codex §8 确认的 15 项正确实现保持不动。

## FA-1 closure 批次 2 + 过度防御评估落地（2026-07-20，codex 轮次 14；
## 原文存档 `../s2/codex_reviews.md` 轮次 14——含对"过度防御"评估的裁决）

本轮双重输入：codex 对轮次 13 的复查（4 项仍需修正 + 测试缺口）+ 它对
我方"过度防御/可维护性"评估的裁决（八成同意，给出可执行设计规则）。

- **仍需修正 1（provider 无锁遍历）**：`_registry_max_version` 直接遍历
  `weight_versions.values()`——并发 commit/unregister 复现
  `dictionary changed size during iteration`（变成未归因 adapter 500）。
  新增 `CaptureRegistry.snapshot_weight_versions()`（锁内深拷贝）；
  `session_deadline`/`next_turn_seq`/overlap 路径 stats 增量一并补锁。
  双线程 churn+reader 回归测试。
- **仍需修正 2（审计非事务）**：先 `drain_attempts()` 再写 JSONL——磁盘
  满时既拒 rollout 又丢内存证据。改 **snapshot → 持久写成功（fsync）→
  ack 移除**（proxy 新增 snapshot_attempts/ack_attempts，drain 降为二者
  合成）。写失败回归测试断言 ledger 完好。
- **仍需修正 3（审计失败没有真 run-halt）**：正式链裸 raise 被 worker 当
  普通成员失败（codex 探针：failed=4、halt=None、继续 top-up）。新增
  `FatalExecutionInfrastructureError`；orchestrator 审计失败（正式链）
  包装之；worker `_account_failure` 识别后置 halt（WorkerHalted）。
- **仍需修正 4（审计丢时间线）**：记录补 `timeline_dicts()` /
  `timing_summary()` / disposition / eligibility_report_ref /
  delivered_sample_count / lease_released。
- **测试缺口**：drain 先于边界断言的顺序录制测试、生产装配 limiter 测试、
  open rollback 测试、审计成功/失败/Fatal 三态测试、worker fatal 停机
  测试——为此把 glue 的三个装配件提取为模块级可测函数
  （`build_production_model_call_proxy` / `make_per_rollout_adapter` /
  `write_execution_audit_record`，也是 F2-0 提升方向的第一步）。
- **设计规则采纳（写入 05 计划 FA-2A 节）**：F2-4 恢复语义先于 F2-1 编码
  定案（replay-stable 公开 id + 每会话新 capability + cursor 语义，拒绝
  裸 at-least-once）；F2-0 代码提升；poison 只绑 session/attempt 不绑
  任务槽位；**结构化终止枚举**（episode_time_limit 可为截断有效样本——
  事实纠正：slime 超时返回 EXIT_TIME_BUDGET_EXCEEDED=**-1**（sandbox.py:60），
  非我方评估里说的 SIGKILL/137；Docker RPC 超时才是 124）；require ↔
  非零 exit 启动断言**硬耦合解除**（轮次 14 推翻轮次 9，代码已改，glue
  默认联动保留）；熔断按 **fault domain** 六分类（不隔离任务的类别明确
  列出），载体 = Outcome + 纯函数 RecoveryPolicy + AdmissionReport，不
  新增报告层；正式训练闸门补两条前置（overlap 挡板已替代 + 熔断在位）。
- **文档收敛**：notes 顶部新增"⚡ 当前权威状态"页（有效机制 + 临时挡板
  登记表含移除条件 + 被推翻结论标注）——历史轮次保留为流水账但不再是
  现状权威；05 计划重启语义统一为"halt → 整 actor 重启"（FA-5 N6 场景
  改写）、顶部状态行更新；AGENTS/00-status 进度与测试数刷新。
- **环境漂移排查（本轮额外）**：全量跑出 1 个与 FA 无关的失败——
  `test_request_carries_token_ids_not_messages` 断言 `X-Session-ID` 精确
  大小写，而依赖重锁后新版 httpx/h11 把线上头名规范成 `X-Session-Id`。
  HTTP 头名按 RFC 9110 大小写不敏感，属测试过度约束；改为小写键匹配。
  排查过程排除了 openai 2.44/verifiers pin/renderers pull 三个嫌疑
  （逐层最小复现定位到 wire 大小写）。
- 测试 903 → 911。


## F2-1a 二审（2026-08-07，codex 复核 P0 → **修复循环熔断首次触发**；
## 原文存档 `../s2/codex_reviews.md`）

**熔断事实**：一审的 P0-1 修复（fail-closed setter）自身引入新 P0——
预登记的 paid 在 materialize 失败后永久残留（session_open 未置位 →
finally 不清理），而 fail-closed 又拒绝 replay 的新 paid → 可恢复的
基建故障变成该 SID 永久拒绝 + prompt group 持续缺员。按协议 §5"修复
引入新 P0"触发熔断：停止给 setter 叠补丁。

**根因分析**：paid 生命周期被拆成两个 owner——orchestrator 在 audit
构造时（T1）经 registrar 预登记，registry 在 open_session（T3）绑
hook，清理却统一挂在 T3 之后才置位的 session_open 标志。T1~T3 之间
任何失败（materialize 在 T2）都产生无主状态；一审只是把无主状态的
症状从"可被覆盖"改成"永久拒绝"，没有消灭无主窗口本身。

**替代设计（所有权收敛，codex 处方 + 实施）**：paid 与 hook **同生命
周期**——`register(sid, hook, physical_attempt_id)` 单锁原子绑定；
绑定发生在 open_session 事务内（materialize 之后），underlying open
失败走既有 rollback unregister 连带清 paid；drop 后整体释放。**删除**
预登记 setter 与 registrar 注入点——无预登记 = 无残留窗口（消灭状态而
不是防御状态）。验收：materialize 失败无残留、replay 新 paid 畅通、
open 失败整体回滚、活跃冲突仍拒绝、失败均有结构化审计。测试 930→931。

**提交纪律违规自查（codex 指出）**：`63e2772c` 因 `git add -A` 混入
约 2600 行非本切片内容。provenance 声明：`python_async_concurrency_
foundations.md`、`repo_harness_code_walkthrough.md`、
`rh2_training_path_and_batch_scheduling_tutorial.md`（增量）、
`training_design/repoharness_validation_experiment_design_review.md`
（增量）属**并行教学/设计线程**产出；`fa/fa_onboarding_walkthrough.md`
是本线程此前的走读文档。内容全部保留（不删并行线程成果），但该
commit 不可作为干净切片回滚单元——回滚 F2-1a 一审需按文件而非按
commit。纪律修正：此后 git add 只用显式路径清单，禁 `-A`。
