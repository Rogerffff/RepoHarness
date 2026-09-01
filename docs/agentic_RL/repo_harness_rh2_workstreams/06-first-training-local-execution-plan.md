# 06 · 首训就绪本地执行计划（决策包 A + 05 替换条款 + 工作包 W0~W7）

日期：2026-09-01。状态：**草案——决策包 A 与 §2 替换条款经 codex 写码前审查、owner 拍板后，本文升为权威计划并回写 05**。范围依据（三份已对齐）：`miles_spike/formal_first_training_readiness_scope.md`（codex 就绪稿）、`miles_spike/first_training_readiness_alignment_claude.md`（Claude 对齐意见书）、`tmp/租卡前本地工作.md`（codex 分批建议）。进度权威沿用 `miles_spike/spike-log.md` 按批追加。

分批原则（协作协议 §近期冻结）：只冻结即将写码需要的 T0；决策包 B 在 W4/W5b 开工前、决策包 C 在 W7/租卡前分别拍板。

---

## §1 决策包 A（现在拍板，随后开 W0/W1a/W1b/W2）

### A1 Miles 正式取代旧 Slime FA 自建面；首训 profile 骨架

- **要决定什么**：确认训练后端正式面 = miles（integration base v3 谱系），首训 profile 骨架 = `fa_formal + faithful DIS（唯一训练目标）+ R3-on + retract + 单 engine + CP=1`。旧 Slime FA 自建面（worker/assembler/proxy 重生成/F2-4 原实现）不再是正式计划项。
- **代码事实**：迁移 spike 全绿（spike-log 全史）；retract 推荐依据 = #2783 的 in_place KV 复用 bug 修复需先移植 extra_key 进 rh2 请求且我们的 capture 路径绕过其修复点，retract 重算 KV 无陈旧风险、上游 fully-async 默认。
- **方案**：(i) 如上；(ii) 保留双后端并行——已在 T0-C1/形态甲定案中否决。
- **推荐**：(i)。**长期代价**：slime 回退面永久冻结（No-Go 场景才激活，届时需补 F2-3 终核）。**以后能改**：in_place 可在首训后作为 Conditional 项单独资格化。

### A2 组准入 = 全员合取

- **要决定什么**：只有**组内全部 member** `training_eligibility_class == online_policy_loss_eligible` 的组才进 loss；任一 member 不合格 → **整组拒绝 + producer 补采**（不拆组、不 branch 充数——与 FA-3 既有"禁止拆组"定案一致）。
- **代码事实**（已核实）：当前 miles 链零 eligibility 消费者；tier cap 封顶不触发 remove_sample（`generate.py:3827`），offline 样本今天照常进 loss——正确性级缺口。
- **方案**：(i) 整组合取拒绝+补采；(ii) 逐 member 剔除留组——破坏 GRPO n=8 组语义，否决。
- **推荐**：(i)。**代价**：不合格率高时补采变慢（有 dynamic filter 记账可观测）。**以后能改**：补采策略参数属 profile。

### A3 资格 cap 的解除 = owner 一行配置（2026-09-01 防御清理后的简化形态）

- **要决定什么**：`S1_TIER_CAP` 的解除不建任何机制——它是一个常量，owner 判断 reward 链可信时**直接修改并提交**（git commit 即审计记录）。原窄解封设计（Safety-Q artifact 门 + qualification manifest + GATE_VERSION 仪式）**整体删除**；S2-0 的"解除清单 fail-closed"不做。
- **保留的本体**：eligibility 分类的计算与消费（W1b）不受影响——分类是训练语义,被删的只是解封官僚。
- **推荐**：如上。**代价**：解除时点完全依赖 owner 判断（这正是意图）。

### A4 最小安全范围与故障分界

- **要决定什么**：首训安全必要集 = 就绪稿 §2.4（非 root + capabilities/pids/内存边界；隔离 docker 网络仅放行模型代理；hidden tests/golden patch/grader-only 永不挂入模型可见 workspace；按实测清理 future git history/reflog/remote refs；remote git/出网/受保护路径篡改真实阻断并记 attempted/executed；安全事件与 hygiene 真进 EligibilityGate）。**明确不做**：microVM、透明通用代理、LLM claim-check、完整五类展示型红队（不入首训前置，无默认排期）。故障分界：task-local 迟写/patch 不合格/篡改 = 该 attempt/group ineligible + refill（不以 reward 0 洗绿，也不让单任务成为拒绝服务入口）；execution scope 无法终止/grader 隔离失效/artifact 存储不可用/身份或安全边界破坏 = run-fatal。
- **代码事实**：现容器 bridge+root、`findings=()`（`generate.py:3800`）、无 CommandFilter/sanitizer；`--network none` 对需访模型代理的 CC 不成立（G7 已知）。
- **推荐**：按上范围。**代价**：安全结论只覆盖该最小集，S2 完整里程碑（`rh2_s2_signal_trusted`）另行推进。**以后能改**：红队/claim-check 按真实需求单独开范围。

### A5 三层 timeout 语义

- **要决定什么**：setup（materialize/harness 启动）、attempt/episode（从实际资源占用起绝对上限）、run（总墙钟）三层独立 deadline；episode 计时起点从"首次模型调用"改为"资源占用开始"；task 自身 deadline 到期 = attempt/group-local 拒绝+补采，无法终止 scope 才升 run-fatal。数值属 profile（C 包）。
- **代码事实**：现实现从首次模型调用起计，materialize/启动等待不设限（就绪稿登记）。
- **推荐**：如上。**以后能改**：数值随 profile。

### A6 masked / reward-only member 的分母与计数语义（FA-3 遗留延后项，现在结清）

- **要决定什么**：reward-only 成员（`present + unresolved`，可信 reward=0 负样本）与被 remove_sample 标记的成员，在 GRPO 组、GBS、rollout 分母中的地位。
- **代码事实**：miles stock 语义 = remove_sample 成员**留在组内参与 advantage 基线，rollout_mask_sums 置零、不进 loss 分母**（C0 纵切实测"remove_sample 清零"）；而我们 faithful DIS loss 的 fail-closed 现拒绝零 provenance execution 且 C1′-b 明确"不为 miles stock remove_sample 整卷置零场景留豁免"——**两处存在潜在冲突，W0 首项即验证**。
- **方案**：(i) 采纳 miles stock 语义：此类成员进组进基线、零分母零梯度，loss 侧对 **remove_sample 标记成员**加窄豁免（仅此一类，其余零 provenance 仍 fail-closed）；(ii) 此类成员从组中整体剔除——改变 advantage 基线构成，需重算组语义；(iii) 含此类成员整组拒绝——补采成本最高。
- **推荐**：(i)——与 E2"可信 reward=0 绝不是缺员"定案一致、改动面最小。GBS 计数：execution 级计数含 reward-only 成员（组完整性口径），branch 不计数维持原定案。**以后能改**：W0 验证若推翻"miles stock 如此工作"的前提，回本项重议。

### A7 【已删除——防御清理 2026-09-01】

原 run-scoped 准入公式、`formal_run_authorized(run)` manifest、FA JSON 账本、三判定概念**全部不做**。能否进入正式训练由 owner 依据 §3 完成情况直接判断,代码不设训练准入门;既有 s1 账本作历史记录冻结,今后不再产生任何"闸门语义"类决策项。就绪稿 §0.2 的公式提案按本条否决。

### A8 E2 clip-high 条款由 faithful DIS 信任区间取代（codex 提出，我同意）

- **要决定什么**：旧 E2 的 `clip 0.2/0.28`（PPO 非对称 clip）条款在正式路径**由 faithful DIS 预注册信任区间取代**，不在 launch 填 `--eps-clip-high`（它只被 stock PPO loss 消费，我们的 loss 不读——填了是无消费者假配置，违反"新配置指认消费者"自检）。
- **代码事实**：`--eps-clip-high` 消费点仅 `losses.py:213`（stock PPO）；faithful DIS 用自有预注册窗口（`faithful_dis_loss.py`，与标量权威同源）。`--disable-grpo-std-normalization` 有真实消费点（`train_data_conversion.py:288`）——它与 dynamic filter、rewards_normalization 一起进 W0 核对清单。
- **推荐**：取代（faithful DIS 是算法定案，不叠 PPO clip）。E2 文本的修订随 §2 回写。

---

## §2 05 计划替换条款（拍板后逐条回写 `05-fully-async-execution-plan.md`，原文保留删除线或"已由 06 取代"注记，不静默删）

1. **FA-1（持续 worker/有界队列/proxy 边界/D-FA-3 内部重生成）**→ 由 miles `FullyAsyncRolloutFn + DefaultDataBuffer` 承担；支持 profile 固定 `retract`（同一 HTTP 请求回队重算 KV 完成，spans 记录跨版本 token）；**proxy 级 turn 重生成与 TrainingRuntimeCoordinator 不再是正式面**——真正 abort/不可归因失败 = 该 attempt/group fail-closed + producer 补采，不做更新窗口透明重试。已实现的 rh2 async_worker 保留为冻结回退面组件。
2. **FA-2 / FA-2B（PromptGroupAssembler/合格组队列）**→ 不做；由 miles 组生产 + **W1b 唯一 group admission 点**（A2 合取语义）取代。
3. **FA-3（SlimeBatchAssembler/lease-ACK 状态机）**→ assembler 不做；批对齐预检降级为 launch preflight 调用既有差分预检器；准入语义由 W1b + dynamic filter + 守恒 judge 承担。§5 预注册参数中 lease/ACK 相关作废。
4. **FA-4** → 已由 miles 侧 faithful_dis_loss（含零信号语义、metamorphic 对拍）超额完成；对拍的分布式半边归 GPU H3。
5. **F2-4（决策包 v4 恢复语义实现）**→ 首训支持 profile **不实现 pending replay/精确 cursor resume**；由 W5b 的"published-boundary 联合 checkpoint + COMMITTED manifest + frontier-discard receipt + 空 buffer 新 segment + `(segment_id, numeric_version)` 复合身份"取代（决策包 B 批准后生效）。v4 语义文本保留并注记"在首训 profile 中被 06/W5b 合同 supersede"。
6. **F2-5/F2-6** → 组不变量由 miles 校验 + 证据守恒 judge 吸收；durable lineage 只保留验收真正读取的最小事件与 manifest；43 事件全接线明确不做。
7. **FA-5（短租集成验收）**→ 由 GPU 资格作业（就绪稿 §3 H1~H10 + campaign 结构）完整吸收，不另租。
8. **退出闸门条款废止**（防御清理 2026-09-01）：不再维护代码级训练准入闸门；就绪与否 = owner 依据 06 §3 完成清单直接判断。既有 s1 账本冻结为历史记录；"F2-1~6 完成前不得翻转"等附加条款一并废止。
9. **E 系定案联动修订**（写入实验设计文档修订注记，T1 实施）：E7/E10 的 slime 绑定条款按对齐意见书 §2.2 清单改写为 miles 载体；E2 clip-high 按 A8；`--max-weight-staleness` 在线语义归决策包 B。

---

## §3 工作包 W0~W8（范围/依赖/验收；每包 = 实现 agent 批 + codex 聚焦复核，进度落 spike-log）

> 映射完备性说明（2026-09-01 穷举核对）：本表与就绪稿 §5.1 十三条租前硬门逐条对映——第 11 条（eval 运输链）与 A5 实现归属为本次修订补入（W8、W2 扩项）；第 8 条后半（run-label 兜底清理）补入 W5a；W3 因体量与依赖差异拆为 W3a/W3b。profile 冻结时点澄清：**结构性骨架在 A（A1/A5/A6），数值在 C**——W6 的拒绝面机制只依赖结构。

**并行波次**：Wave1（A 批后）= W0 ∥ W1a ∥ W2 → Wave2 = W1b ∥ W5a → Wave3（B 批后）= W3a ∥ W3b ∥ W4 ∥ W5b → Wave4 = W6 ∥ W8 → Wave5（C 批后）= W7。粗量级：全程 2~3 周现行节奏。

| 包 | 范围 | 依赖 | 验收要点 |
|---|---|---|---|
| **W0 算法/config 核对** | E2 全部算法旋钮的 miles 消费路径逐一核对（std normalization/dynamic filter/rewards_normalization/max staleness 消费点）；**首项=A6 前提验证**（miles stock remove_sample 的组内基线+零分母行为实测）；"参数存在但当前 loss 不消费"即 fail-closed 或从配置删除——**范围限定 E2 旋钮清单，不建通用未消费配置检测器** | A | 每旋钮一个消费点证据+正反例；A6 验证结论回写决策记录 |
| **W1a 身份铸造** | miles submit/generate 边界铸造六字段（组身份+物理 attempt 两级，对照旧 async_worker+fa_bringup 的分工）；retry 换新 physical attempt/seq、不复用 session capability | A | 缺失/复用/retry/fan-out/canonicalize round-trip 负例；fa_formal 身份校验在真实路径通过 |
| **W1b eligibility 真准入** | 唯一 group admission 点（A2 合取）；拒绝原因+数量进事件流（解封无机制——cap 为 owner 直改常量,见 A3） | W1a | 单 member offline/cap 未解/metadata 缺失→整组零样本进 conversion；补采补满 batch |
| **W2 trusted 任务入口 + timeout 落地** | 去 8 题固定表；接 S2-1 可信 manifest resolver（216 题三分包）；`EnvironmentPackageV1.digest()` 贯穿 TaskSpec/baseline/patch/receipt/run manifest；四门 runner 最小闭环（T2-d/e：empty/golden/已知错误 patch/确定性门真实执行）；资格 taskset 冻结机制（题单内容 owner 后定）；**A5 三层 timeout 实现**（setup deadline、episode 计时起点改为资源占用、run 总墙钟——数值留占位待 C） | A | unknown task/漏包/digest mismatch fail-closed；四门对小集实跑；8 题探针在 formal preflight 被拒；timeout 三层各一正反例 |
| **W3a formal 评分冻结** | runtime owner 停止 execution scope 替换 NO-GO 屏障；git-free census/exporter；fresh grader 不读 live workspace；**formal B6 组合测试**（正常写完/后台/root 迟写/Git 注入/binary/symlink/mode/grader 隔离） | W2（真实环境包）；与 W3b 可并行 | B6 清单全绿；task-local vs run-fatal 分界测试 |
| **W3b 最小安全链** | A4 安全集落地：sandbox 加固（非 root/cap/pids/内存）+隔离网仅放行模型代理+hidden mount 防线+git sanitizer 最小+CommandFilter 拦截（block+dummy 观测+attempted/executed 记账）+findings 真进 EligibilityGate | W1b（gate 接线面） | 作弊不改 reward、正常轨迹不误拒正反例；出网/remote git 拒绝实测 |
| **W4 JIT/staleness** | publish 后 drain（miles 侧窄 commit）；持续 producer 保留；H5 硬门读取的最小计时事件（修剪后子集）；**一次性 CPU materialization benchmark**（真实 RH2 shape，为 H5 阈值提供量级参照） | B | B-ready/B-not-ready/publish/zero-signal/fresh-stale refill/事件配对负例 |
| **W5a shutdown** | 就绪稿 §2.6 关闭链（producer 停→cancel/await→grading/capture/HTTP/容器→evidence flush→dispose）；有界超时保首因；**campaign supervisor 按 run label 的有界兜底清理与残留核对** | A | 正常/异常关闭、关闭后禁 submit、无残留三分支；兜底清理幂等 |
| **W5b checkpoint 冷恢复** | 就绪稿 §2.7 合同：published-boundary 联合提交、COMMITTED manifest、frontier-discard receipt、空 buffer 新 segment、复合 version 身份、恢复 bootstrap 发布原版本号；**crash matrix 本地全做** | B | 各提交点 crash/坏 manifest/shard/digest fail-closed；Adam/scheduler/RNG/版本不混代 |
| **W6 证据最小集（防御清理后瘦身,原 gate 半边删除）** | 训练语义事件最小集（§2.8 修剪后）+ 资源闭包一次性取数；配置错误 assert（eval/训练 taskset 不得同集、探针题不入训练数据——普通断言非闸门）；**不做**：准入公式/授权 manifest/FA JSON 账本/授权类拒绝面 | W1~W3 主体 | 语义事件被 judge 真实消费;两条配置 assert 各一负例 |
| **W8 eval 运输链**（本次穷举核对补入,就绪稿 §2.9/§5.1 第 11 条） | 标准非 FA before/after eval 本地链：接同一 source/model/tokenizer/环境解析器；eval taskset 身份分离断言；eval 前 producer/grading/update 停止断言；结果绑定显式 checkpoint digest（拒绝 latest）；小模型/fixture 验证 base 与 post-update 双 checkpoint 全流程与失败传播 | W2（环境解析器）；checkpoint digest 约定对齐 W5b | 身份分离/producer 未停/latest 回退三负例；双 checkpoint fixture 正例 |
| **W7 实验包** | 从范围反向生成 launch/collector/judge/thresholds（不继承未审文件）；judge 只做训练语义判定（parity/守恒/R3 消费/零信号）,授权仪式类判定不再新写,反例限语义判定 | C、W1~W6、W8 | 双 base 全绿+self-test+preflight 正反例 |

**界外（本计划不含,另行排期）**：GPU pass-rate 预筛与 pre-RL 行为诊断（单卡作业或租期尾项,C 包定载体）；held-out 冻结与题单选定（数据线,依赖四门+预筛）；R2E ingestion（D3 闭环档下首训不做）。

## §4 决策包 B/C（内容冻结,时点后置）

**B（Wave3 前）**：提前 drain 关闭落账（已口头批准）；正常 shutdown 硬门落账（已口头批准）；`max_weight_staleness` 在线硬拒语义；W5b checkpoint 合同（published-boundary/新 segment/frontier discard）；明确不做 pending replay/精确 cursor/exactly-once；`update_weights_interval` 支持口径（推荐首版=1）。
**C（W7/租卡前）**：精确 GPU profile 或 qualified envelope（含 A5 timeout 数值、staleness/buffer/并发值）；staleness/成本/连续更新（≥3+≥3）/资源阈值；资格任务集选定（记录所用集合即可,无 digest 门）；H1~H10 预算与停止规则；D3 闭环档确认与预筛载体；**首训 harness 工具面（subagent/compaction/fork 开闭）及 fanout 覆盖判定项的去留**（就绪稿 §4.11 条件句的显式化）；launch/judge/thresholds 最终形态。

## §5 下一步

1. codex 对 §1/§2 做写码前审查 → owner 一次拍板 A；
2. 拍板即回写 05/04/00-status 修订注记 + E 系定案（E2/E7/E10/附录 A）迁移修订注记（单独提交）；
3. Wave1 三包并行开工（W0 ∥ W1a ∥ W2），照现行节奏：agent 批实现 → codex 聚焦复核 → spike-log 落账；
4. 防御清理落地项（随 Wave1 顺带,零决策负担）：删除 C3/C7 governed buffer/ledger 未接线原型;删除 fa_formal 启动挡板仪式;既有 lanes/证据系统冻结不扩建。

## §6 防御清理原则（2026-09-01 owner 裁定,长期有效）

保护训练结果科学有效性的校验（环境可信/reward 可信/进 loss 资格/逐位对齐/fail-closed）= infra 本体,保留;保护"操作者未授权操作"的机制（闸门公式/授权 manifest/解封仪式/账本扩建）= 不做——owner 即授权系统,判断不写进代码;溯源降级为被动记录（run log + git commit）。**今后任何 W 包或审查建议中出现授权官僚类设计,直接按本条拒绝,不再提请 owner 决策。**
