# 06 · 首训就绪本地执行计划（决策包 A + 05 替换条款 + 工作包 W0~W8）

日期：2026-09-01。状态：**草案——决策包 A 与 §2 替换条款经 codex 写码前审查、owner 拍板后，本文升为权威计划并回写 05**。输入文档（历史草案,冲突以本 06 提案处理,owner 批准前均为提案）：`miles_spike/formal_first_training_readiness_scope.md`（codex 就绪稿）、`miles_spike/first_training_readiness_alignment_claude.md`（Claude 对齐意见书）、`tmp/租卡前本地工作.md`（codex 分批建议）。进度权威沿用 `miles_spike/spike-log.md` 按批追加。

分批原则（协作协议 §近期冻结,2026-09-02 按 codex wave1 建议细化为分时点）：**D0 = 现在拍板的最小集**（§1,允许 W0/W1a/W2a 开工）；**D1 在 W1b 写码前**（三终态映射表 + staleness 显式阈值 + A5 disposition,见 §4）；**D2 = W3a/W3b 开工确认点**（A4/评分正链无变化则不新增决策）；决策包 B 在 W4/W5b 开工前、决策包 C 在 W7/租卡前分别拍板。

---

## §1 决策包 A（2026-09-02 codex 四点复核后重划:**D0 = A1 + A7/§6 + A8 + W1a 身份边界 + W2a 所有权边界**;A2/A3/A6 内容冻结但批准时点=D1,A4=D2）

> D0 的准确构成（只含 W0/W1a/W2a 开工真正需要的边界）：**A1**（资源流向+CP 双支持）、**A7+§6**（防御清理）、**A8**（配置真实性）、**D0-2 = W1a 中立身份边界**（六字段两级身份/retry 换 attempt/fan-out 非 member/token 匹配仅校验——见 §3 W1a 行,不夹带任何 admission/算法决定）、**D0-3 = W2a 所有权边界**（trusted 入口+public/private 分离+termination 事实中立——见 §3 W2a 行）。A2/A3/A6 属 W1b 语义,内容照本文冻结、**批准时点归 D1**;A4 属评分/安全边界,**批准时点归 D2**。

### A1 Miles = 唯一开发与资格候选（2026-09-02 按 wave1 建议再拆:A1 只定资源流向,运行支持面移出）

- **要决定什么**：只批准"开发资源押在 Miles 候选链上"——Miles 成为**唯一开发与 GPU 资格候选**，Slime FA 自建线冻结不并行。**正式 Migration-Go 结论由 GPU 资格作业全绿后另行记录**；No-Go 则回本地，由 owner 决定修 Miles integration 重测或恢复 Slime 剩余。
- **移出 A1 的内容**：`fa_formal` 是身份/评分/资格链的载体前提（随 D0 生效）；R3-on 属 MoE routing replay 训练正确性要求（不依赖最终 loss 选择，随 D0 生效）；**faithful DIS/retract/单 engine 等"首个运行支持面"移到 B/C 按时点确认**（faithful DIS 保持"证据最完整的默认候选"地位,W0 保留两类 loss 的消费者事实,见 A8）。
- **CP 语义（owner 2026-09-02 拍板）**：目标链路必须**同时支持 CP=1 与 CP>1**（CP=2 是显存不足时的现实候选）,实际 CP 数值到 GPU 实测临场决定,**不在任何本地决策包冻结**。当前 `faithful_dis_loss.py:338-342` 对 cp.size≠1 fail-closed——CP 归约实现列为必做工作项 **W9**（见 §3）。
- **方案**：(i) 条件式 Miles-only 候选（两位审查者推荐）；(ii) 现在宣布永久迁移——预支 GPU 实验要回答的问题，否决；(iii) Slime/Miles 双线开发——重复建设，否决。**状态：建议，待 owner 决策。**

### A2 组准入 = 全员合取（批准时点=D1）

- **要决定什么**（2026-09-02 codex 修正精确表述——eligibility class 只是输入之一）：**组内全部 member 的 final admission 结论 = KEEP_FULL（= eligibility facts ∧ termination disposition ∧ finalize-time staleness 合取,W1b 薄处置边界产出）且 consume-time staleness 通过,整组才进 conversion/loss**；任一 member 非 KEEP_FULL → 整组拒绝 + producer 补采（不拆组、不 branch 充数——与 FA-3 既有"禁止拆组"定案一致）。
- **代码事实**（已核实）：当前 miles 链零 eligibility 消费者；tier cap 封顶不触发 remove_sample（`generate.py:3827`），offline 样本今天照常进 loss——正确性级缺口。
- **方案**：(i) 整组合取拒绝+补采；(ii) 逐 member 剔除留组——破坏 GRPO n=8 组语义，否决。
- **推荐**：(i)。**代价**：不合格率高时补采变慢（有 dynamic filter 记账可观测）。**以后能改**：补采策略参数属 profile。

**补采语义澄清（2026-09-02 修正——此前把两套作用域混为一谈）**：miles 有**两条互不相通的排出路径**（`fully_async_data_buffer.py:126-164` 已核实）——
- **dynamic filter `keep=False`（W1b 复合 filter 的合法排除,含 eligibility 不合格组/零方差组）→ 固定丢弃,不进 unused handler,没有 retry 选项**。持续 producer 用后续 prompt 补足 buffer——"整组拒绝 + 补采"精确含义即此,不是同 prompt 重试；
- **`async_unused_samples_handler` 只作用于两类**：put-time ABORTED 组、get-time 超龄组。handler 可选 `retry`（同 prompt 回数据源,无有界重试,确定性失败 prompt 会反复回队）或 `drop`（miles 默认值）。**该选择归决策包 B**；建议首版也用 `drop`（明确接受超龄 prompt 同样放弃,覆盖率影响记遥测）。未来真有 transient retry 需求再设计 typed、bounded retry。

### A3 S1_TIER_CAP 整体删除（批准时点=D1;codex 复审修正，取代"owner 改常量"方案）

- **要决定什么**：eligibility 只由轨迹事实决定——七维全过自然得到 online；`S1_TIER_CAP`/ceiling reason code/cap 应用分支/W1b"cap 未解"负例**全部删除**。`GATE_VERSION` 保留为被动的 eligibility 逻辑版本号（机械升版，非任何解锁）。
- **时序窗口防护（Claude 精化）**：cap 删除与 security 维度语义切换**必须同批**（W1b）——security 维从"无 findings 即过"改为"**正向能力事实在场且无违规**"（能力事实缺失 = 非 online，fail-closed）。W3b 落地前该维度自然拦截，不存在 findings=() 假过窗口。
- **推荐**：如上。**代价**：无（消除了一个 owner 决策点）。

### A4 安全边界与失败分类（批准时点=D2;codex 终核：消除与 W3b 的矛盾，收敛为一致方案）

- **强边界真实阻断**：出网、hidden/grader mount、future git refs/reflog/remotes——依赖 Docker/内核与镜像清洁性；被阻断操作**返回真实工具错误**。**不建** CommandFilter/dummy 观测/attempted-executed 平台（原 A4"真实阻断并记 attempted/executed"条款**删除**，与 W3b 统一）。
- workspace 内测试/禁区文件修改：不能影响 frozen grader，由 patch hygiene 最终检出。
- **负样本与 ineligible 的界线（分布正确性，codex 补充）**：普通 `tests_failed` 与可信 clean-grader 产生的 `patch_apply_failed` = **reward=0 负样本**，不得笼统归 ineligible；hygiene 实锤篡改/污染 → 该成员无 online 资格，按 A2 整组处理。
- **run-fatal 面**：grader 隔离失效、hidden 资产可见、跨 execution 身份错接、execution scope 无法终止、核心 admission record（identity/patch/GradingReport/EligibilityReport 及引用）持久化失败（样本不交付 + run-fatal，但**仍** revoke session/终止 scope/清容器）；timeline/telemetry 写失败不阻止 cleanup。
- **明确不做**：microVM、透明通用代理、LLM claim-check、完整展示型红队（原样）。

### A5 timeout / truncation 决策矩阵（2026-09-02 按 wave1 建议移出 D0——**决策时点 = D1 或 C,Wave1 只实现 termination 事实**；全部为建议,状态 pending_owner_decision）

**A5-a 确定性 policy horizon**（`task_token_budget_exhausted`/`max_turns_exhausted`/`context_limit_reached`；前提 = capture/quiescence/frozen snapshot/grading 完整 ⇒ `present_truncated`）：

| 选项 | 组成员 | reward/advantage | 自身梯度 | GBS | faithful DIS 分母 | 主要代价 |
|---|---|---|---|---|---|---|
| ① 完整训练 | 计入 | 计入 | 训练 | 计入 | 正常进入 | 预算内未解决 = 策略负样本。**Claude 与 codex 均倾向此项**（避免长度选择偏置；截断即评分是 B1-B5 既有方式） |
| ② 严格排除 | **整组拒绝（不允许 n-1）** | 排除 | 排除 | 不计 | 不适用 | 长度/难度选择偏置 + 补采成本 |

原 ② baseline-only masked（成员影响兄弟 advantage 但自身 mask 梯度）**从选择面删除**（2026-09-02,wave1 D1-1a）：算法不对称、无实验动机,W1b 处置边界不保留 `MASK_MEMBER` 终态——未来真要 baseline-only 实验再另行新增契约,事实层不受影响。

**A5-b `hard_wall_timeout` 单列**（可能由模型排队/API/容器/主机抖动触发；事实完整只证可评分，**不证归因于 policy**）：(1) 定义为环境 horizon，完整轨迹可训练——可能把 infra 抖动惩罚进策略；(2) **默认不作策略负样本，记录并排除**（推荐）——丢弃部分可评分样本、降低 GPU 有效利用。原选项 (3)"仅 policy-owned 计时区间才训练"**从选择面删除**（2026-09-02 codex 四点复核:W2a 只有粗粒度计时,无法区分 590s 排队+10s 行动与 600s 真实行动;不为无实验需求的选项建设计时归因系统）。C 在 (1)/(2) 之间选择。

**A5-c 其余 termination 映射**：`owner_cancelled`（正常 shutdown 取消的 active execution）→ 不评分不训练、不补采（run 已结束）；setup/infra timeout → 无可信轨迹，拒组+补采；execution scope 无法终止 → run-fatal；run 总墙钟 → 停新提交 + 正常 shutdown。episode 计时起点改为资源占用（不变）；数值属 C 包。

**批准前边界**：代码只实现 termination 事实与观测；A5 未拍板前不实现任何新的 admission/gradient mask/补采语义。

### A6 成员语义（批准时点=D1;codex 复审修正——推翻 Claude 原方案，Claude 复核后同意）

- **要决定什么**：两类对象严格分开——
  - **可信 reward=0 成员**（present+unresolved，真实 token/mask/provenance，remove_sample=False）→ **完整参与** group/GBS/advantage/loss。`[1,0,0,0,0,0,0,0]` 中 0 成员携带负 advantage 是 GRPO 关键训练信号，不得清零；
  - **任一 remove_sample/aborted/ineligible 成员** → conversion 前**整组拒绝 + 补采**（与 A2 合取一致；remove_sample 的 reward=0.0 非可信评分，入基线污染组统计）；
  - 全组 reward 相同 → dynamic filter 整组过滤。
- **faithful DIS 不加零 provenance 豁免**：组级拒绝使零 provenance 不可达，loss 严格性原样保持。W0 的 A6 验证项改为：断言 miles stock remove_sample 行为（留组零分母）在我们的准入下不可达。
- **推荐**：如上。**以后能改**：无需——这是 GRPO 语义的正确形态。

### A7 【提议删除——防御清理 2026-09-01 提案,owner 批准 D0 后生效】

提议:原 run-scoped 准入公式、`formal_run_authorized(run)` manifest、FA JSON 账本、三判定概念**全部不做**。能否进入正式训练由 owner 依据 §3 完成情况直接判断,代码不设训练准入门;既有 s1 账本作历史记录冻结,今后不再产生任何"闸门语义"类决策项。就绪稿 §0.2 的公式提案随本条一并**提议否决**（owner 确认前旧口径未被正式推翻）。

### A8 配置真实性条款（2026-09-02 按 wave1 建议改为条件式,不提前永久选定 loss）

- **要决定什么**：现在确认的是**配置真实性规则**,不是永久锁定某个 loss——
  - **当选定 faithful DIS profile 时**：`--eps-clip`/`--eps-clip-high` 无消费者（仅 stock PPO loss 读,`losses.py:213`）,launch/judge/文档不得把它们宣称为该 profile 的有效训练参数；旧 E2 clip 条款在该 profile 下由 faithful DIS 预注册信任区间取代（`faithful_dis_loss.py`,与标量权威同源）；
  - **若未来 C 改选 stock PPO**：PPO clip 参数由 stock loss 正常消费,合法有效；但须重新定义 behavior denominator、clip 参数与对应 GPU oracle,**不能继承 faithful DIS 的验收结论**；不为当前候选从 Miles 全局删除 PPO 能力；
  - **W0 落地**（原 §2.2 内容并入,owner 2026-09-02 拍板）：分别列清 faithful DIS 与 stock PPO 的**真实消费者清单**;loss/profile 必须显式选择——未知 loss、两套互斥参数同时声称生效、静默 fallback 均使 preflight 失败;不建通用"未消费参数检测器"。
- **loss 最终选择归 C**。faithful DIS 保持默认候选地位（behavior support/version spans/R3 replay/守恒 oracle 证据最完整）;C 选定它时再冻结信任区间数值与正反 oracle。
- **代码事实**：`--disable-grpo-std-normalization` 有真实消费点（`train_data_conversion.py:288`）——与 dynamic filter、rewards_normalization 一起进 W0 核对清单。

---

## §2 05 计划替换条款（拍板后逐条回写 `05-fully-async-execution-plan.md`，原文保留删除线或"已由 06 取代"注记，不静默删）

1. **FA-1（持续 worker/有界队列/proxy 边界/D-FA-3 内部重生成）**→ 由 miles `FullyAsyncRolloutFn + DefaultDataBuffer` 承担；pause mode（`retract | in_place`）与单/多 engine 支持面**归决策包 B**（W4 前）,具体卡数/TP/placement 归 C——retract 保持推荐（#2783 耦合、上游默认,spans 记录跨版本 token）但不在本条固定；**proxy 级 turn 重生成与 TrainingRuntimeCoordinator 不再是正式面**——**已归因的 task-local 失败** = 该 attempt/group 编码为 ABORTED,由 unused handler 按 B 包语义处理（建议 drop）;**不可归因/结构性损坏 = typed run-fatal,不补采**（2026-09-02 wave1 修正:静默补采会掩盖系统损坏）;不做更新窗口透明重试。已实现的 rh2 async_worker 保留为冻结回退面组件。
2. **FA-2 / FA-2B（PromptGroupAssembler/合格组队列）**→ 不做；由 miles 组生产 + **W1b 唯一 group admission 点**（A2 合取语义）取代。
3. **FA-3（SlimeBatchAssembler/lease-ACK 状态机）**→ assembler 不做；批对齐预检降级为 launch preflight 调用既有差分预检器；准入语义由 W1b + dynamic filter + 守恒 judge 承担。§5 预注册参数中 lease/ACK 相关作废。
4. **FA-4** → 已由 miles 侧 faithful_dis_loss（含零信号语义、metamorphic 对拍）超额完成；对拍的分布式半边归 GPU H3。
5. **F2-4（决策包 v4 恢复语义实现）**→ 首训支持 profile **不实现 pending replay/精确 cursor resume**；由 W5b 的"published-boundary 联合 checkpoint + 薄 COMMITTED marker + 空 buffer 新 segment + `(segment_id, numeric_version)` 复合身份"取代（frontier 丢弃只作普通 checkpoint metadata/恢复日志,不建独立 receipt——与 W5b 行、B 包术语统一）（决策包 B 批准后生效）。v4 语义文本保留并注记"在首训 profile 中被 06/W5b 合同 supersede"。
6. **F2-5/F2-6** → 组不变量由 miles 校验 + 证据守恒 judge 吸收；durable lineage 只保留验收真正读取的最小事件与 manifest；43 事件全接线明确不做。
7. **FA-5（短租集成验收）**→ 由 GPU 资格作业（就绪稿 §3 H1~H10 + campaign 结构）完整吸收，不另租。
8. **退出闸门条款提议废止**（防御清理 2026-09-01 提案,owner 批准 D0 后生效）：不再维护代码级训练准入闸门；就绪与否 = owner 依据 06 §3 完成清单直接判断。既有 s1 账本冻结为历史记录；"F2-1~6 完成前不得翻转"等附加条款一并废止。
9. **E 系定案联动修订**（写入实验设计文档修订注记，T1 实施）：E7/E10 的 slime 绑定条款按对齐意见书 §2.2 清单改写为 miles 载体；E2 clip-high 按 A8；`--max-weight-staleness` 在线语义归决策包 B。

---

## §3 工作包 W0~W8（范围/依赖/验收；每包 = 实现 agent 批 + codex 聚焦复核，进度落 spike-log）

> 映射完备性说明（2026-09-01 穷举核对）：本表与就绪稿 §5.1 十三条租前硬门逐条对映——第 11 条（eval 运输链）与 A5 实现归属为本次修订补入（W8、W2a 扩项）；第 8 条后半（run-label 兜底清理）补入 W5a；W3 因体量与依赖差异拆为 W3a/W3b。profile 冻结时点澄清：**结构性骨架在 A（A1/A5/A6），数值在 C**。（W6 已删除,旧"W6 拒绝面机制"表述作废。）

**并行波次**（2026-09-02 按 wave1 建议改:W3a/W3b 不等决策包 B,只等 D2 确认点）：Wave1（D0 批后）= W0 ∥ W1a ∥ W2a（T2-d/e 由数据线并行,W2b 条件式非 Wave1）→ Wave2（D1 批后）= W1b ∥ W5a ∥ W9 → Wave3 = (D2 确认后 W3a→W3b 串行或切所有权) ∥ (B 批后 W4→W5b 串行,W4 先冻结 train/publish/drain 顺序) → Wave4 = W8 → Wave5（C 批后）= W7。W6 已删除。粗量级：全程 2~3 周现行节奏。

| 包 | 范围 | 依赖 | 验收要点 |
|---|---|---|---|
| **W0 算法/config 核对** | E2 全部算法旋钮的 miles 消费路径逐一核对（std normalization/dynamic filter/rewards_normalization/max staleness 消费点）；**首项=A6 前提验证**（miles stock remove_sample 的组内基线+零分母行为实测）；"参数存在但当前 loss 不消费"即 fail-closed 或从配置删除——**范围限定 E2 旋钮清单，不建通用未消费配置检测器** | A | 每旋钮一个消费点证据+正反例；A6 验证结论回写决策记录 |
| **W1a 身份铸造** | miles submit/generate 边界铸造六字段（组身份+物理 attempt 两级，对照旧 async_worker+fa_bringup 的分工）；retry 换新 physical attempt/seq、不复用 session capability | A(D0) | 缺失/复用/retry/fan-out/canonicalize round-trip 负例；**临时启动挡板以下的**真实 generate/canonicalize 生产链通过（完整入口现状被 bringup.py:705 拒绝,挡板保留至 W1b+W3a+W3b+W4） |
| **W1b eligibility 真准入 + A3 落地**（2026-09-02 wave1 收编:三终态+两阶段 staleness+薄处置边界） | **三终态**（附录 A 映射表,D1 拍板确认）:① **结构性矛盾 → typed raise（run-fatal,不得压成 ABORTED 或 drop,须在编码为 ABORTED 之前抛出——ABORTED 在 put() 先于 filter 处理）**——slots/组形状错、fa_formal 身份缺失/跨组错配/重复/复用、fan-out 叶冒充新 member、EligibilityReport 与 trajectory/execution/environment 绑定错位、声称 online 却 remove_sample=True/零可训 provenance、reward/grading/eligibility 引用互相矛盾;② **已归因 task-local 失败 → 真实 ABORTED**（无可信完整轨迹:setup/API/tool/container 局部失败、capture 未闭合、grading infra 失败）,由 unused handler 处理;③ **完整 finalize 但不合格 → 保留真实 COMPLETED/TRUNCATED 样本 + typed admission payload,由复合 filter keep=False 整组排除**（现状 `generate.py:3830` 把 degraded 一律压成 abort 形状,须改——否则 filter 永远看不到这些组）。**薄处置边界（D1-1a）**:纯函数 `base eligibility facts ∧ termination disposition ∧ finalize-time staleness → KEEP_FULL/DROP_GROUP/FATAL`;**不设 MASK_MEMBER**;A5 未拍板时对 disposition 未显式注入即 fail-fast,本地测试对同一 present_truncated fixture 双注入 KEEP_FULL/DROP_GROUP 证明链路中立。**staleness 两阶段（D1-4）**:finalize-time 用 EligibilityReport 已有 policy_staleness 维（不忽略）,consume-time 由 buffer.get() 复查（归 W4）;两处引用**同一权威阈值配置,实现与测试要求显式传入,禁止继承隐式默认 4**（`generate.py:1823`）,数值由 B 确认后 W1b 才正式启用。**authoritative join 不变量**:filter 同步取得由 typed EligibilityReport 派生的最小 admission payload,核对 report id/facts digest/trajectory id/execution id/environment identity（载体=紧凑 metadata 或有界进程内映射,选择属 T1;不建 durable ledger,不热路径扫盘）。同批:删 S1_TIER_CAP 全套 + security 维切正向能力事实（A3,cap 删除与语义切换同批防假过窗口） | D1、W1a、W2a（task/environment identity 消费契约） | 结构类逐项 typed raise 负例;②③ 分流正反例（degraded 不再一律 abort）;disposition 未注入 fail-fast+双注入中立性;显式阈值缺失即拒;security 维缺能力事实=非 online |
| **W2a runtime 通用消费链 + timeout 事实**（codex 终核:与题单/GPU 数据选择解耦） | 与数据集规模无关的消费与身份传播。**最小所有权架构（2026-09-02 codex 四点复核:rollout actor 不得直调完整 loader——`ingest_swegym_lite.py:483-488` 无条件反序列化含 ValidationOnlyBundle 的全部四面）**:trusted ingest/controller 调完整 loader 并核对四面关系,构造 **training-only typed view**——rollout actor 只拿 public task + identity/digest,host grader 只拿 private grading ref/bundle;`ValidationOnlyBundle` 不发送到 rollout actor/sandbox/模型/正式 grader（剥离后 typed view + 泄漏负测试,不建新服务/权限平台）。入口 = `load_trusted_ingest_outputs`（不收未核可信 pins 的 caller objects）;解析并核对 package↔public↔grading 的 task/repo/base/image/digest 关系（运行输入一致性检查,非授权门）;模型可见面（prompt/mount/Sample metadata/projection）只含 public projection,`PrivateGradingBundleV2` 仅 host 侧 grading 控制面消费（RolloutTaskSpec 内嵌密封 spec 还是 opaque ref = T1,须有"private 内容绝不进模型侧"正反测试）;`ValidationOnlyBundle/golden_patch` 永不进 rollout/正式 grader;`EnvironmentPackageV1.digest()` 贯穿 baseline/grading/eligibility join 或等强 typed payload（不能只在入口核一次后丢失）;synthetic fixture 测消费/错误传播/泄漏边界;A5 未批部分只落 termination 事实记录。**注**:EnvironmentPackageV1 仅身份+digest（无 prompt/test_patch/eval_cmd）,完整 v2 评分链归 T2-d/W3a——W2a 不宣称单独产出可评分链（此两条代码事实为 codex 终核补充,实现批开工时逐行复核） | A;若数据线程在做 T2-d/e 先切文件/接口 ownership | unknown task/漏包/digest mismatch fail-closed;泄漏边界正反例;timeout 事实各一例 |
| **T2-d / T2-e**（数据线承接,非 Wave1） | v2 grader 正链（clean checkout→agent frozen patch→**official test_patch 后写**→vendor 复核 eval_cmd→SWE-Gym parser→GradingReport;grader 永不回读 live workspace;归 T2-d/W3a 串行）与四门 runner（T2-e）——由既有数据线程继续,RH2 Wave1 不重复造 | T2-c 已完成（216 bundle 稳定,事实纠正:非"未生成"） | — |
| **W2b 真实数据集成**（条件式,非 Wave1） | 真实资格数据进训练 runtime/GPU campaign 的集成层。**启动条件 = T2-d/e 完成且 owner 在 C 包确认 GPU spike 数据目标**（216 题是否进 GPU 未决,不预绑定） | T2-d/e ∧ C | — |
| **W3a formal 评分冻结** | runtime owner 停止 execution scope 替换 NO-GO 屏障;git-free census/exporter;fresh grader 不读 live workspace;formal B6 组合测试（正常写完/后台/root 迟写/Git 注入/binary/symlink/mode/grader 隔离）;**cleanup 优先级反转**:核心 admission record（identity/patch/GradingReport/EligibilityReport 及引用）写失败→样本绝不交付+run-fatal+**仍执行** revoke session/终止 scope/清容器,仅 cleanup 自身失败才 quarantine;timeline/telemetry 类降为 best-effort 不统治 cleanup | D2 确认、W2a、T2-d（v2 评分正链）;**不等决策包 B**;与 W3b 串行或先切文件所有权 | B6 清单全绿;核心记录写失败仍清理的负例;task-local vs run-fatal 分界 |
| **W3b 最小安全链**（codex 复审重构:正向能力事实,删 CommandFilter 平台） | 每个 sandbox 创建后**直接核实并记录正向能力事实**:non-root/capabilities/pids/CPU/内存/writable mount allowlist+quota/网络仅可达模型代理/hidden+grader 资产不在 mount/git future refs+reflog+remotes 已清——**缺任一项不产训练样本**,事实进 eligibility(接 W1b security 维)。**删除** CommandFilter+dummy 观测+attempted/executed 平台（python/subprocess 可绕;向量覆盖:出网→内核级网络隔离,reflog→镜像清理,改测试→patch hygiene,hidden→mount 隔离;被阻断操作返回真实工具错误）。H7 GPU 验收改形为真实 CC run 中的边界核实 | D2 确认、W1b;**不等决策包 B**;与 W3a 串行或所有权切分 | 每能力项一个"未生效即拦"负例;作弊向量逐条由保留机制覆盖的正反例;正常轨迹不误拒 |
| **W4 JIT/staleness** | publish 后 drain（miles 侧窄 commit）;持续 producer 保留;H5 硬门读取的最小计时事件;一次性 CPU materialization benchmark。**先于 W5b 执行以冻结 train/publish/drain 顺序** | B | B-ready/B-not-ready/publish/zero-signal/fresh-stale refill/事件配对负例 |
| **W5a shutdown + 资源闭包** | 就绪稿 §2.6 关闭链;有界超时保首因;campaign supervisor **缩为 launch trap + run-label 残留检查**;普通 evidence flush 失败不阻止 cleanup;承接原 W6 的资源闭包一次性取数（内存保守上界+fsync 延迟） | A | 正常/异常关闭、关闭后禁 submit、无残留三分支;flush 失败仍清理负例 |
| **W5b checkpoint 冷恢复**（codex 复审瘦身+补全） | **保留**:published-boundary checkpoint;model/optimizer/scheduler/RNG/last-published-version 同代;薄 COMMITTED marker;空 buffer 新 segment;(segment_id, numeric_version) 复合身份;不恢复旧 cursor;冷恢复后完成 optimizer step。**补全（codex 终核修正 off-by-one）**:updater/rank 的 version bootstrap——train_async 启动即有一次 update_weights 且 updater 在 publish 前先 +1,故恢复到已发布版本 p 时 updater 内部计数器应恢复为 **p-1**（bootstrap 重发该 checkpoint 标记 p,首次真实更新才 p+1）;若选择绕过 bootstrap publish 直接 load/tag p,须显式实现另一条启动路径——**不得把所有对象无差别设为 p**（p2p.py:61/mixin.py:358,覆盖全部 updater 不只 rollout manager）。**删除**:独立 frontier-discard receipt（改普通恢复日志行）/evidence watermark/全量 crash matrix→只测未完成 checkpoint、损坏 checkpoint、完整冷恢复三场景 | B;**在 W4 之后**（同触 train/publish 顺序） | 三场景正反例;五元组不混代;恢复后版本 p→p+1 |
| ~~**W6**~~（codex 复审:整包删除,职责分流——训练事件由 W1~W5 就地产生;资源闭包→W5a;train/eval 分离→W8;W7 直接消费最小指标;"probe 题不训"属实验选择非 runtime 断言） | — | — |
| **W9 faithful DIS CP 归约**（新增,owner 2026-09-02 拍板必做） | 目标链路必须同时支持 CP=1 与 CP>1（CP=2 是显存不足候选,数值临场定——A1）。当前 `faithful_dis_loss.py:338-342` 对 cp.size≠1 fail-closed:实现范围 = CP 切分下的**behavior logprob 对齐、advantage 广播、loss mask/sampling-support 的本地分片、逐 token 分子与 target∈support 断言**（不只笼统"归约";miles `math_utils` 已有 CP 感知模式可循,stock PPO 路径已用）,实现后移除该 fail-closed（改为真实语义）。**本地可测边界**:多进程 CPU process group / mock parallel_state 测归约逻辑与切分对齐;**真机 CP=2 端到端验证归 GPU spike**（C 包加一条 CP=2 短验证,W7 judge 覆盖 CP 语义） | D1 后（Wave2,独立于准入链,只触 faithful_dis_loss） | CP=1 结果与现实现逐位一致;CP=2 模拟切分下守恒/对齐正反例;fail-closed 移除后无 CP 静默降级路径 |
| **W8 eval 运输链** | 标准非 FA before/after eval 本地链:接同一 source/model/tokenizer/环境解析器;eval taskset 身份分离断言;eval 前 producer/grading/update 停止断言;结果绑定显式 checkpoint digest（拒绝 latest）;小模型/fixture 验证 base 与 post-update 双 checkpoint 全流程与失败传播。**skip 不得洗绿（codex 终核补）**:miles EvalDispatcher 把 busy/export_failed/crashed 记 skip 而非失败——W8 验收必须要求两个显式 checkpoint 的 eval **真正完成并产出绑定结果**,任一 skip/failure = 首训就绪验收失败,不得以"已 dispatch/已 drain"充数 | W2a（环境解析器）、T2-d/W3a（eval 走同一可信评分链）、W5a（producer/shutdown 语义）、W5b（checkpoint identity） | 身份分离/producer 未停/latest 回退/skip 洗绿四负例;双 checkpoint fixture 正例 |
| **W7 实验包** | 从范围反向生成 launch/collector/judge/thresholds（不继承未审文件）。**judge 覆盖 = 本计划声称合格的全部训练/系统正确性判定**（codex 终核纠正此前过窄口径）:parity/守恒/R3 消费/零信号 + fresh grading/eligibility + 安全正向能力事实 + consume-time staleness + optimizer→publish→version + 冷恢复 + 正常 shutdown + eval checkpoint 绑定;**不含**授权 manifest/阶段闸门类判定 | C、W0~W5、W8、W9（CP 语义进 judge 面）;**W2b 为条件依赖**（仅当 C 决定 GPU 用真实数据）（W6 已删除,旧依赖串作废） | 双 base 全绿+self-test+preflight 正反例 |

**界外（本计划不含,另行排期）**：GPU pass-rate 预筛与 pre-RL 行为诊断（单卡作业或租期尾项,C 包定载体）；held-out 冻结与题单选定（数据线,依赖四门+预筛）；R2E ingestion（D3 闭环档下首训不做）。

## §4 决策包 D1/D2/B/C（内容冻结,时点后置）

**D1（W1b 写码前）**：① **附录 A 七维降级原因 → 三终态映射表确认**（草案已备,owner+codex 确认——它决定哪些失败走静默排出、哪些停训,属拒绝路径/样本偏置 T0）；② **staleness 只定参数化接口**（2026-09-02 codex 修正:不许 D1/B/C 三次决策——D1 只确认"显式传入、finalize-time 与 consume-time 引用同一权威配置、禁止继承隐式默认 4"的接口形状;**唯一语义与阈值数值归 B**;C 只引用不再改）；③ A5-a/A5-b disposition 可在 D1 定,也可留 C——未定时 W1b 按 fail-fast+双注入中立实现。

**D2（W3a/W3b 开工确认点）**：评分正链（A4+W3a 的 clean checkout→frozen patch→official test_patch 后写→vendor eval_cmd→parser 链）与最小安全边界（A4/W3b 内容）——**若 D0 批准的 A4 无变化,D2 只是开工确认,不新增决策项**。

**B（W4/W5b 前）**：提前 drain 关闭落账（已口头批准）；正常 shutdown 硬门落账（已口头批准）；`max_weight_staleness` **唯一语义与阈值数值**（W1b 正式启用的前置;C 只引用）；**unused handler 的 retry/drop 选择**（作用域=ABORTED+超龄两类,推荐 drop——A2 澄清）；W5b checkpoint 合同（published-boundary/新 segment/frontier 丢弃日志）；明确不做 pending replay/精确 cursor/exactly-once；`update_weights_interval` 支持口径（推荐首版=1）。
**C（W7/租卡前）**：训练 objective 最终选择（faithful DIS 为默认候选——A8;若改选 PPO 须重定义分母/oracle,**且 GPU oracle 须验证 PPO+CP,不得沿用 faithful DIS 的 CP oracle**）；精确 GPU profile 或 qualified envelope（含 A5 timeout 数值、staleness/buffer/并发值、临场 CP 数值——CP=2 短验证项随 W9 进 GPU spike）；**有界 no-progress 停止规则数值**（连续无法成 batch 不得无限 warning 烧租期）；staleness/成本/连续更新（≥3+≥3）/资源阈值；资格任务集选定（记录 taskset 内容 digest 作被动身份,不当授权门）；H1~H10 预算与停止规则；D3 闭环档确认与预筛载体；**首训 harness 工具面（subagent/compaction/fork 开闭）及 fanout 覆盖判定项的去留**（就绪稿 §4.11 条件句的显式化）；launch/judge/thresholds 最终形态。

## §5 下一步

1. **D0 已拍板（2026-09-02,owner 按 wave1_决策1 §8 草案批准）**：A1 + A7/§6 + A8 + W1a 身份边界 + W2a 所有权边界;A2/A3/A6 内容冻结、批准归 D1;A4 归 D2;A5/loss/pause mode/拓扑后置。W0/W1a/W2a 即时开工；
2. 拍板即回写 05/04/00-status 修订注记 + E 系定案（E2/E7/E10/附录 A）迁移修订注记 + 以 append-only 注记结清 fa2a 决策包 D1b（仅限首训 profile 范围,不改写旧批准史）+ A4 注明取代旧 scope 的 CommandFilter/attempted-executed 方案（单独提交）；
3. Wave1 三包并行开工（W0 ∥ W1a ∥ W2a;T2-d/e 由数据线并行）,照现行节奏：agent 批实现 → codex 聚焦复核 → spike-log 落账;**Wave1 期间完成 D1 拍板**（附录 A 确认 + B-stale 定值）,随后 Wave2 = W1b ∥ W5a ∥ W9；
4. 防御清理落地项：C3/C7 governed buffer/ledger 未接线原型**可保留为 spike-only 代码或日后单独清理**——其删除不是 Wave1 前置,且不得与生产链改动混同一 commit（codex 终核）;既有 lanes/证据系统冻结不扩建。**bringup.py:705-715 的临时无条件拒绝只能在 W1b+W3a+W3b+W4 完成后删除**（2026-09-02 codex 补:consume-time staleness 与 publish→drain 顺序到 W4 才闭合）（不在 Wave1 提前删,且不得误删 fa_formal 的真实 version/barrier/security/config capability 检查——那些是本体不是仪式）。

## §6 防御清理原则（2026-09-01 Claude 提案,待 owner 确认;长期有效）

**删除**:谁批准过、项目处于哪个阶段、是否允许操作者启动（授权公式/manifest/解封仪式/账本扩建/闸门代码化）——owner 即授权系统,判断不写进代码。
**保留**:本次实际输入（taskset/env/grader/model/config digest 被动记录）、本次实际能力（sandbox 正向能力事实）、进入 loss 的逐层事实（身份/eligibility/分母/mask 对齐/reward 可信）、恢复代际（segment/version)。
今后任何 W 包或审查建议中出现授权官僚类设计,直接按本条拒绝,不再提请 owner 决策。

## 附录 A · 七维降级原因 → 三终态映射表（草案,D1 拍板确认;owner 2026-09-02 要求编制）

> 三终态定义见 W1b 行：① typed raise/run-fatal（系统损坏,停训）；② 真实 ABORTED（无可信完整轨迹,unused handler 处理）；③ completed-ineligible（完整 finalize,复合 filter keep=False 整组排除）。判据原则：**事实说明"系统/接线坏了" → ①；事实说明"这次执行没产出可信对象" → ②；事实完整可信、只是不合格 → ③**。现状 `generate.py:3830` 把全部 degraded 压成 abort 形状,本表即其替代语义。

| 维度 | 失败情形（reason_code 级） | 终态 | 依据 |
|---|---|---|---|
| 1 token_provenance | capture 未闭合/记录缺失（本次执行局部故障） | ② ABORTED | 无可信完整轨迹,已归因 task-local |
| 1 token_provenance | provenance 与 execution/身份矛盾（token 声称来自别的执行） | ① fatal | 身份错接=接线 bug |
| 2 logprob_alignment | 完整轨迹上 logprob 缺失/长度错位/NaN | ① fatal | 协议/装配 bug,不是样本属性（NaN parity 定案同向） |
| 3 loss_mask_integrity | mask=1 覆盖非采样或禁止角色 token | ① fatal | mask 由我方装配,违规=装配 bug |
| 4 reward_scope | scope=unknown/归属矛盾 | ① fatal | 评分归因矛盾,wave1 D1-1 明列 |
| 5 security_and_leakage | hidden/grader 资产可见、grader 隔离破坏（环境侧失效） | ① fatal | A4 run-fatal 面 |
| 5 security_and_leakage | agent executed 级违规/hygiene 实锤篡改（环境完好,agent 行为） | ③ ineligible | A4:成员无 online 资格,整组排除 |
| 5 security_and_leakage | 正向能力事实缺失（W3b 未产出或采集失败） | ③ ineligible | A3 fail-closed:缺事实=非 online,非系统损坏 |
| 6 clean_grading | grading infra 失败（评分容器/checkout 故障,无可信 reward） | ③ ineligible | **2026-09-02 codex 纠正**:公共契约要求保持 `present_* + grading_infra_failure`（⇒ reward_unavailable,`fa_runtime.py:547-549,603`）,不得改写为 ABORTED;由准入整组排除,训练结果与 drop 等价 |
| 6 clean_grading | hygiene 拒绝（可信检出污染,评分链本身完好） | ③ ineligible | 与维度 5 agent 侧违规同类 |
| 6 clean_grading | GradingReport 与 grading 身份/引用矛盾 | ① fatal | 归属矛盾 |
| 7 policy_staleness | finalize-time 超阈值 | ③ ineligible | 样本完整可信只是过期;consume-time 超龄另由 buffer.get() → handler（B 语义） |

**存疑项（codex 复核重点）**：维度 2/3 一律 ① 是否过严（也可论证为 ② task-local——我方立场:完整轨迹上出现即 bug,静默排出会掩盖系统性错位）。维度 6 infra 失败原草案归 ②,经 codex 以 `fa_runtime.py` 契约事实纠正为 ③（已核实,见表内）。普通 `tests_failed`/可信 `patch_apply_failed` **不在本表**——它们是 reward=0 负样本,七维全过,正常进组（A4）。
