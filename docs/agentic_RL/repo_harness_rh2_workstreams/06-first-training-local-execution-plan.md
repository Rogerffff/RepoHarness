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

### A3 资格 cap 的窄解封机制

- **要决定什么**：`S1_TIER_CAP` 的解除不走"完整 S2 验收后改常量"，改为窄解封：**Safety-Q 安全 artifact（GPU 上产出、不进 policy loss）在场 ∧ 不可变 `qualification_run_authorized` manifest 授权** → gate 对资格任务发放 online eligibility（GATE_VERSION 升版 + fail-closed：artifact/manifest 任一缺失、digest 漂移、过期即拒）；**禁止任何环境变量旁路**。正式首训则走 A7 的 run-scoped 公式。
- **代码事实**：`gate.py:77-86` 现行解除方式 = S2 全验收后显式改常量；S2-0 的解除清单未定义。
- **方案**：(i) 窄解封（就绪稿 §2.2.5）；(ii) 等完整 S2——把 claim-check/红队全套变成首训前置，已在对齐中否决。
- **推荐**：(i)。**代价**：出现两级解封语义（资格窄口 + 正式公式），须在 gate 注释与账本写清。**以后能改**：S2 全量完成后可收敛回单一机制。

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

### A7 正式准入公式方向

- **要决定什么**：采用就绪稿 §0.2 的 run-scoped 公式（`formal_path_infrastructure_qualified ∧ rh2_fully_async_training_path_verified ∧ rh2_online_reward_integrity_minimum_qualified ∧ formal_run_authorized(run)`）；旧 `rh2_s2_signal_trusted` 保持 false、继续表示更宽的 S2 里程碑但不再阻塞首训 profile；`rh2_fully_async_training_path_verified` 补 JSON 账本落位。**实现形态钉死为**：授权 manifest 文件 + 一条公式改 inspector/preflight，不建 gate 框架（对齐意见书修剪 2）。
- **代码事实**：现公式 = FA ∧ S2 两布尔（`04-s2:13`）；FA 闸门无 JSON 账本。
- **推荐**：采用。**代价**：闸门语义文档需一次性全面同步（05/04/00-status/inspector）。**以后能改**：S2 完整后公式可再收敛。

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
8. **退出闸门条款**：`rh2_fully_async_training_path_verified` 翻转条件改为"GPU 资格作业判定级清单全绿"（A7 公式框架内），并补 JSON 账本；"F2-1~6 完成前不得翻转"的旧附加条款废止。
9. **E 系定案联动修订**（写入实验设计文档修订注记，T1 实施）：E7/E10 的 slime 绑定条款按对齐意见书 §2.2 清单改写为 miles 载体；E2 clip-high 按 A8；`--max-weight-staleness` 在线语义归决策包 B。

---

## §3 工作包 W0~W7（范围/依赖/验收；每包 = 实现 agent 批 + codex 聚焦复核，进度落 spike-log）

**并行波次**：Wave1（A 批后）= W0 ∥ W1a ∥ W2 → Wave2 = W1b ∥ W5a → Wave3（B 批后）= W3 ∥ W4 ∥ W5b → Wave4 = W6 → Wave5（C 批后）= W7。粗量级：全程 2~3 周现行节奏。

| 包 | 范围 | 依赖 | 验收要点 |
|---|---|---|---|
| **W0 算法/config 核对** | E2 全部算法旋钮的 miles 消费路径逐一核对（std normalization/dynamic filter/rewards_normalization/max staleness 消费点）；**首项=A6 前提验证**（miles stock remove_sample 的组内基线+零分母行为实测）；"参数存在但当前 loss 不消费"一律 fail-closed 或从配置删除 | A | 每旋钮一个消费点证据+正反例；A6 验证结论回写决策记录 |
| **W1a 身份铸造** | miles submit/generate 边界铸造六字段（组身份+物理 attempt 两级，对照旧 async_worker+fa_bringup 的分工）；retry 换新 physical attempt/seq、不复用 session capability | A | 缺失/复用/retry/fan-out/canonicalize round-trip 负例；fa_formal 身份校验在真实路径通过 |
| **W1b eligibility 真准入** | 唯一 group admission 点（A2 合取）；拒绝原因+数量进事件流；A3 窄解封机制（gate 侧）＋ GATE_VERSION 升版 | W1a | 单 member offline/cap 未解/metadata 缺失→整组零样本进 conversion；补采补满 batch；解封 fail-closed 负例 |
| **W2 trusted 任务入口** | 去 8 题固定表；接 S2-1 可信 manifest resolver（216 题三分包）；`EnvironmentPackageV1.digest()` 贯穿 TaskSpec/baseline/patch/receipt/run manifest；四门 runner 最小闭环（T2-d/e：empty/golden/已知错误 patch/确定性门真实执行）；资格 taskset 冻结机制（题单内容 owner 后定） | A | unknown task/漏包/digest mismatch fail-closed；四门对小集实跑；8 题探针在 formal preflight 被拒 |
| **W3 formal 评分冻结+最小安全链** | W3a：runtime owner 停止 execution scope 替换 NO-GO 屏障；git-free census/exporter；fresh grader 不读 live workspace；**formal B6 组合测试**（正常写完/后台/root 迟写/Git 注入/binary/symlink/mode）。W3b：A4 安全集落地（sandbox 加固+隔离网+hidden mount 防线+git sanitizer 最小+CommandFilter 拦截+findings 真进 gate）；正反例（作弊不改 reward、正常轨迹不误拒） | W1b、W2 | B6 清单全绿；拦截 attempted/executed 记账；task-local vs run-fatal 分界测试 |
| **W4 JIT/staleness** | publish 后 drain（miles 侧窄 commit）；持续 producer 保留；H5 硬门读取的最小计时事件（修剪后子集） | B | B-ready/B-not-ready/publish/zero-signal/fresh-stale refill/事件配对负例 |
| **W5a shutdown** | 就绪稿 §2.6 关闭链（producer 停→cancel/await→grading/capture/HTTP/容器→evidence flush→dispose）；有界超时保首因 | A | 正常/异常关闭、关闭后禁 submit、无残留三分支 |
| **W5b checkpoint 冷恢复** | 就绪稿 §2.7 合同：published-boundary 联合提交、COMMITTED manifest、frontier-discard receipt、空 buffer 新 segment、复合 version 身份、恢复 bootstrap 发布原版本号；**crash matrix 本地全做** | B | 各提交点 crash/坏 manifest/shard/digest fail-closed；Adam/scheduler/RNG/版本不混代 |
| **W6 gate/evidence** | A7 公式落 inspector/preflight+FA JSON 账本；qualification manifest 机制；formal preflight 拒绝面全套（就绪稿 §2.1 清单）；证据最小集（§2.8 修剪后）+资源闭包一次性取数 | W1~W3 主体 | 每拒绝面一个负例；缺授权/过期/漂移/越界全拒 |
| **W7 实验包** | 从范围反向生成 launch/collector/judge/thresholds（不继承未审文件）；洗绿反例全套 | C、W1~W6 | 双 base 全绿+self-test+preflight 正反例 |

**界外（本计划不含,另行排期）**：GPU pass-rate 预筛与 pre-RL 行为诊断（单卡作业或租期尾项,C 包定载体）；held-out 冻结与题单选定（数据线,依赖四门+预筛）；R2E ingestion（D3 闭环档下首训不做）。

## §4 决策包 B/C（内容冻结,时点后置）

**B（Wave3 前）**：提前 drain 关闭落账（已口头批准）；正常 shutdown 硬门落账（已口头批准）；`max_weight_staleness` 在线硬拒语义；W5b checkpoint 合同（published-boundary/新 segment/frontier discard）；明确不做 pending replay/精确 cursor/exactly-once；`update_weights_interval` 支持口径（推荐首版=1）。
**C（W7/租卡前）**：精确 GPU profile 或 qualified envelope；staleness/成本/连续更新（≥3+≥3）/资源阈值；qualification taskset digest；H1~H10 预算与停止规则；D3 闭环档确认与预筛载体；launch/judge/thresholds 最终形态。

## §5 下一步

1. codex 对 §1/§2 做写码前审查 → owner 一次拍板 A；
2. 拍板即回写 05/04/00-status 修订注记（单独提交）；
3. Wave1 三包并行开工（W0 ∥ W1a ∥ W2），照现行节奏：agent 批实现 → codex 聚焦复核 → spike-log 落账。
