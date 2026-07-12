# FA 工作流 implementation-notes（三节制）

范围：`05-fully-async-execution-plan.md` 的 FA-0~FA-5 实现期记录。每任务一节，
只记重要事项。

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
