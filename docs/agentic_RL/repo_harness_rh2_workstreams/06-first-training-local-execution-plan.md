# 06 · 首训就绪本地执行计划（决策包 A + 05 替换条款 + 工作包 W0~W8）

日期：2026-09-01。状态：**草案——决策包 A 与 §2 替换条款经 codex 写码前审查、owner 拍板后，本文升为权威计划并回写 05**。输入文档（历史草案,冲突以本 06 提案处理,owner 批准前均为提案）：`miles_spike/formal_first_training_readiness_scope.md`（codex 就绪稿）、`miles_spike/first_training_readiness_alignment_claude.md`（Claude 对齐意见书）、`tmp/租卡前本地工作.md`（codex 分批建议）。进度权威沿用 `miles_spike/spike-log.md` 按批追加。

分批原则（协作协议 §近期冻结）：只冻结即将写码需要的 T0；决策包 B 在 W4/W5b 开工前、决策包 C 在 W7/租卡前分别拍板。

---

## §1 决策包 A（现在拍板，随后开 W0/W1a/W1b/W2a）

### A1 Miles = 唯一开发与资格候选（codex 终核修正："正式取代"改为两时点分离）

- **要决定什么**：现在批准的是"开发资源押在 Miles 候选链上"——Miles 成为**唯一开发与 GPU 资格候选**，Slime FA 自建线冻结不并行；首训 profile 骨架 = `fa_formal + faithful DIS（唯一训练目标）+ R3-on + retract + 单 engine + CP=1`。**正式 Migration-Go 结论由 GPU 资格作业全绿后另行记录**（spike-log 现行记录即 Conditional Go）；No-Go 则回本地，由 owner 决定修 Miles integration 重测或恢复 Slime 剩余。
- **方案**：(i) 条件式 Miles-only 候选（两位审查者推荐）；(ii) 现在宣布永久迁移——预支 GPU 实验要回答的问题，否决；(iii) Slime/Miles 双线开发——重复建设，否决。
- **代码事实**：retract 推荐依据同前（#2783 耦合、上游默认）。**状态：建议，待 owner 决策。**

### A2 组准入 = 全员合取

- **要决定什么**：只有**组内全部 member** `training_eligibility_class == online_policy_loss_eligible` 的组才进 loss；任一 member 不合格 → **整组拒绝 + producer 补采**（不拆组、不 branch 充数——与 FA-3 既有"禁止拆组"定案一致）。
- **代码事实**（已核实）：当前 miles 链零 eligibility 消费者；tier cap 封顶不触发 remove_sample（`generate.py:3827`），offline 样本今天照常进 loss——正确性级缺口。
- **方案**：(i) 整组合取拒绝+补采；(ii) 逐 member 剔除留组——破坏 GRPO n=8 组语义，否决。
- **推荐**：(i)。**代价**：不合格率高时补采变慢（有 dynamic filter 记账可观测）。**以后能改**：补采策略参数属 profile。

**补采语义澄清（codex 终核新增，待 owner 决策）**：miles 的 unused-samples handler 有两义——`retry`（同 prompt 回数据源；**注意精确事实：miles 默认值是 `drop`**，retry 为可选项且无有界重试，确定性失败 prompt 会反复回队占满 producer）与 `drop`（弃当前组，持续 producer 用后续 prompt 补足 buffer）。**建议**：首训 profile 用 `drop`；未来真有 transient retry 需求再设计 typed、bounded retry。分布含义：drop 使该 prompt 本轮次不再出现（覆盖率影响记遥测）。

### A3 S1_TIER_CAP 整体删除（codex 复审修正，取代"owner 改常量"方案）

- **要决定什么**：eligibility 只由轨迹事实决定——七维全过自然得到 online；`S1_TIER_CAP`/ceiling reason code/cap 应用分支/W1b"cap 未解"负例**全部删除**。`GATE_VERSION` 保留为被动的 eligibility 逻辑版本号（机械升版，非任何解锁）。
- **时序窗口防护（Claude 精化）**：cap 删除与 security 维度语义切换**必须同批**（W1b）——security 维从"无 findings 即过"改为"**正向能力事实在场且无违规**"（能力事实缺失 = 非 online，fail-closed）。W3b 落地前该维度自然拦截，不存在 findings=() 假过窗口。
- **推荐**：如上。**代价**：无（消除了一个 owner 决策点）。

### A4 安全边界与失败分类（codex 终核：消除与 W3b 的矛盾，收敛为一致方案；建议，待 owner 决策）

- **强边界真实阻断**：出网、hidden/grader mount、future git refs/reflog/remotes——依赖 Docker/内核与镜像清洁性；被阻断操作**返回真实工具错误**。**不建** CommandFilter/dummy 观测/attempted-executed 平台（原 A4"真实阻断并记 attempted/executed"条款**删除**，与 W3b 统一）。
- workspace 内测试/禁区文件修改：不能影响 frozen grader，由 patch hygiene 最终检出。
- **负样本与 ineligible 的界线（分布正确性，codex 补充）**：普通 `tests_failed` 与可信 clean-grader 产生的 `patch_apply_failed` = **reward=0 负样本**，不得笼统归 ineligible；hygiene 实锤篡改/污染 → 该成员无 online 资格，按 A2 整组处理。
- **run-fatal 面**：grader 隔离失效、hidden 资产可见、跨 execution 身份错接、execution scope 无法终止、核心 admission record（identity/patch/GradingReport/EligibilityReport 及引用）持久化失败（样本不交付 + run-fatal，但**仍** revoke session/终止 scope/清容器）；timeline/telemetry 写失败不阻止 cleanup。
- **明确不做**：microVM、透明通用代理、LLM claim-check、完整展示型红队（原样）。

### A5 timeout / truncation 决策矩阵（codex 终核：补全 fa2a 决策包 D1b 保留的全部语义轴；**全部为建议，状态 pending_owner_decision**）

**A5-a 确定性 policy horizon**（`task_token_budget_exhausted`/`max_turns_exhausted`/`context_limit_reached`；前提 = capture/quiescence/frozen snapshot/grading 完整 ⇒ `present_truncated`）：

| 选项 | 组成员 | reward/advantage | 自身梯度 | GBS | faithful DIS 分母 | 主要代价 |
|---|---|---|---|---|---|---|
| ① 完整训练 | 计入 | 计入 | 训练 | 计入 | 正常进入 | 预算内未解决 = 策略负样本。**Claude 与 codex 均倾向此项**（避免长度选择偏置；截断即评分是 B1-B5 既有方式） |
| ② baseline-only masked | 计入 | 计入 | mask | 需 owner 明确 | 不进 | 影响兄弟 advantage 但不惩罚该成员——算法不对称，**两位审查者均不推荐**，仅为选择面完整列出 |
| ③ 严格排除 | **整组拒绝（不允许 n-1）** | 排除 | 排除 | 不计 | 不适用 | 长度/难度选择偏置 + 补采成本 |

**A5-b `hard_wall_timeout` 单列**（可能由模型排队/API/容器/主机抖动触发；事实完整只证可评分，**不证归因于 policy**）：(1) 定义为环境 horizon，完整轨迹可训练——可能把 infra 抖动惩罚进策略；(2) **默认不作策略负样本，记录并排除**（codex 倾向）——丢弃部分可评分样本、降低 GPU 有效利用；(3) 仅当计时区间证明为 policy-owned 才训练——需额外计时账。

**A5-c 其余 termination 映射**：`owner_cancelled`（正常 shutdown 取消的 active execution）→ 不评分不训练、不补采（run 已结束）；setup/infra timeout → 无可信轨迹，拒组+补采；execution scope 无法终止 → run-fatal；run 总墙钟 → 停新提交 + 正常 shutdown。episode 计时起点改为资源占用（不变）；数值属 C 包。

**批准前边界**：代码只实现 termination 事实与观测；A5 未拍板前不实现任何新的 admission/gradient mask/补采语义。

### A6 成员语义（codex 复审修正——推翻 Claude 原方案，Claude 复核后同意）

- **要决定什么**：两类对象严格分开——
  - **可信 reward=0 成员**（present+unresolved，真实 token/mask/provenance，remove_sample=False）→ **完整参与** group/GBS/advantage/loss。`[1,0,0,0,0,0,0,0]` 中 0 成员携带负 advantage 是 GRPO 关键训练信号，不得清零；
  - **任一 remove_sample/aborted/ineligible 成员** → conversion 前**整组拒绝 + 补采**（与 A2 合取一致；remove_sample 的 reward=0.0 非可信评分，入基线污染组统计）；
  - 全组 reward 相同 → dynamic filter 整组过滤。
- **faithful DIS 不加零 provenance 豁免**：组级拒绝使零 provenance 不可达，loss 严格性原样保持。W0 的 A6 验证项改为：断言 miles stock remove_sample 行为（留组零分母）在我们的准入下不可达。
- **推荐**：如上。**以后能改**：无需——这是 GRPO 语义的正确形态。

### A7 【已删除——防御清理 2026-09-01】

原 run-scoped 准入公式、`formal_run_authorized(run)` manifest、FA JSON 账本、三判定概念**全部不做**。能否进入正式训练由 owner 依据 §3 完成情况直接判断,代码不设训练准入门;既有 s1 账本作历史记录冻结,今后不再产生任何"闸门语义"类决策项。就绪稿 §0.2 的公式提案按本条否决。

### A8 E2 clip-high 条款由 faithful DIS 信任区间取代（codex 提出，我同意）

- **要决定什么**：旧 E2 的 `clip 0.2/0.28`（PPO 非对称 clip）条款在正式路径**由 faithful DIS 预注册信任区间取代**，不在 launch 填 `--eps-clip-high`（它只被 stock PPO loss 消费，我们的 loss 不读——填了是无消费者假配置，违反"新配置指认消费者"自检）。
- **代码事实**：`--eps-clip-high` 消费点仅 `losses.py:213`（stock PPO）；faithful DIS 用自有预注册窗口（`faithful_dis_loss.py`，与标量权威同源）。`--disable-grpo-std-normalization` 有真实消费点（`train_data_conversion.py:288`）——它与 dynamic filter、rewards_normalization 一起进 W0 核对清单。
- **推荐**：取代（faithful DIS 是算法定案，不叠 PPO clip）。E2 文本的修订随 §2 回写。
- **精确表述（codex 终核补）**：正式 launch 不把 `--eps-clip` 与 `--eps-clip-high` 作为有效训练语义配置（两者仅被 stock PPO loss 消费）；即便 argparse 默认字段存在，judge 与文档不得把它们解释为 faithful DIS 的有效参数。

---

## §2 05 计划替换条款（拍板后逐条回写 `05-fully-async-execution-plan.md`，原文保留删除线或"已由 06 取代"注记，不静默删）

1. **FA-1（持续 worker/有界队列/proxy 边界/D-FA-3 内部重生成）**→ 由 miles `FullyAsyncRolloutFn + DefaultDataBuffer` 承担；支持 profile 固定 `retract`（同一 HTTP 请求回队重算 KV 完成，spans 记录跨版本 token）；**proxy 级 turn 重生成与 TrainingRuntimeCoordinator 不再是正式面**——真正 abort/不可归因失败 = 该 attempt/group fail-closed + producer 补采，不做更新窗口透明重试。已实现的 rh2 async_worker 保留为冻结回退面组件。
2. **FA-2 / FA-2B（PromptGroupAssembler/合格组队列）**→ 不做；由 miles 组生产 + **W1b 唯一 group admission 点**（A2 合取语义）取代。
3. **FA-3（SlimeBatchAssembler/lease-ACK 状态机）**→ assembler 不做；批对齐预检降级为 launch preflight 调用既有差分预检器；准入语义由 W1b + dynamic filter + 守恒 judge 承担。§5 预注册参数中 lease/ACK 相关作废。
4. **FA-4** → 已由 miles 侧 faithful_dis_loss（含零信号语义、metamorphic 对拍）超额完成；对拍的分布式半边归 GPU H3。
5. **F2-4（决策包 v4 恢复语义实现）**→ 首训支持 profile **不实现 pending replay/精确 cursor resume**；由 W5b 的"published-boundary 联合 checkpoint + 薄 COMMITTED marker + 空 buffer 新 segment + `(segment_id, numeric_version)` 复合身份"取代（frontier 丢弃只作普通 checkpoint metadata/恢复日志,不建独立 receipt——与 W5b 行、B 包术语统一）（决策包 B 批准后生效）。v4 语义文本保留并注记"在首训 profile 中被 06/W5b 合同 supersede"。
6. **F2-5/F2-6** → 组不变量由 miles 校验 + 证据守恒 judge 吸收；durable lineage 只保留验收真正读取的最小事件与 manifest；43 事件全接线明确不做。
7. **FA-5（短租集成验收）**→ 由 GPU 资格作业（就绪稿 §3 H1~H10 + campaign 结构）完整吸收，不另租。
8. **退出闸门条款废止**（防御清理 2026-09-01）：不再维护代码级训练准入闸门；就绪与否 = owner 依据 06 §3 完成清单直接判断。既有 s1 账本冻结为历史记录；"F2-1~6 完成前不得翻转"等附加条款一并废止。
9. **E 系定案联动修订**（写入实验设计文档修订注记，T1 实施）：E7/E10 的 slime 绑定条款按对齐意见书 §2.2 清单改写为 miles 载体；E2 clip-high 按 A8；`--max-weight-staleness` 在线语义归决策包 B。

---

## §3 工作包 W0~W8（范围/依赖/验收；每包 = 实现 agent 批 + codex 聚焦复核，进度落 spike-log）

> 映射完备性说明（2026-09-01 穷举核对）：本表与就绪稿 §5.1 十三条租前硬门逐条对映——第 11 条（eval 运输链）与 A5 实现归属为本次修订补入（W8、W2a 扩项）；第 8 条后半（run-label 兜底清理）补入 W5a；W3 因体量与依赖差异拆为 W3a/W3b。profile 冻结时点澄清：**结构性骨架在 A（A1/A5/A6），数值在 C**。（W6 已删除,旧"W6 拒绝面机制"表述作废。）

**并行波次**（codex 复审改序:同触文件的包串行）：Wave1（A 批后）= W0 ∥ W1a ∥ W2a（T2-d/e 由数据线并行,W2b 条件式非 Wave1）→ Wave2 = W1b ∥ W5a → Wave3（B 批后）= (W3a→W3b 串行或切所有权) ∥ (W4→W5b 串行,W4 先冻结 train/publish/drain 顺序) → Wave4 = W8 → Wave5（C 批后）= W7。W6 已删除。粗量级：全程 2~3 周现行节奏。

| 包 | 范围 | 依赖 | 验收要点 |
|---|---|---|---|
| **W0 算法/config 核对** | E2 全部算法旋钮的 miles 消费路径逐一核对（std normalization/dynamic filter/rewards_normalization/max staleness 消费点）；**首项=A6 前提验证**（miles stock remove_sample 的组内基线+零分母行为实测）；"参数存在但当前 loss 不消费"即 fail-closed 或从配置删除——**范围限定 E2 旋钮清单，不建通用未消费配置检测器** | A | 每旋钮一个消费点证据+正反例；A6 验证结论回写决策记录 |
| **W1a 身份铸造** | miles submit/generate 边界铸造六字段（组身份+物理 attempt 两级，对照旧 async_worker+fa_bringup 的分工）；retry 换新 physical attempt/seq、不复用 session capability | A | 缺失/复用/retry/fan-out/canonicalize round-trip 负例；fa_formal 身份校验在真实路径通过 |
| **W1b eligibility 真准入 + A3 落地**（codex 终核:filter 内部分层） | 单个复合 group filter（miles 仅一个 dynamic_sampling_filter_path,不分接互相覆盖的两个）。**内部两层**:① **结构性矛盾 → typed raise（run-fatal,不得压成 ABORTED 或 drop）**——slots/组形状错、fa_formal 身份缺失/跨组错配/重复/复用、fan-out 叶冒充新 member、EligibilityReport 与 trajectory/execution/environment 绑定错位、声称 online 却 remove_sample=True、声称 online 却零可训 provenance、reward/grading/eligibility 引用互相矛盾（接线 bug 不得被持续补采静默掩盖;且须在编码为 ABORTED 之前抛出——ABORTED 在 put() 先于 filter 处理）;② **合法排除 → keep=False + 按 A2 补采语义**——完整判定的 offline/audit 组、有效 remove_sample 组、reward 零方差组。**authoritative join 不变量**:filter 同步取得由 typed EligibilityReport 派生的最小 admission payload,核对 report id/facts digest/trajectory id/execution id/environment identity（载体=紧凑 metadata 或有界进程内映射,选择属 T1;不建 durable ledger,不热路径扫盘）。同批:删 S1_TIER_CAP 全套 + security 维切正向能力事实（A3）。staleness 属 consume-time,归 W4 非本 filter | W1a、W2a（task/environment identity 消费契约） | 结构类逐项 typed raise 负例;合法类整组零样本进 conversion+补采;security 维缺能力事实=非 online |
| **W2a runtime 通用消费链 + timeout 事实**（codex 终核:与题单/GPU 数据选择解耦） | 与数据集规模无关的消费与身份传播:入口 = `load_trusted_ingest_outputs`（不收未核可信 pins 的 caller objects）;解析并核对 package↔public↔grading 的 task/repo/base/image/digest 关系（运行输入一致性检查,非授权门）;模型可见面（prompt/mount/Sample metadata/projection）只含 public projection,`PrivateGradingBundleV2` 仅 host 侧 grading 控制面消费（RolloutTaskSpec 内嵌密封 spec 还是 opaque ref = T1,须有"private 内容绝不进模型侧"正反测试）;`ValidationOnlyBundle/golden_patch` 永不进 rollout/正式 grader;`EnvironmentPackageV1.digest()` 贯穿 baseline/grading/eligibility join 或等强 typed payload（不能只在入口核一次后丢失）;synthetic fixture 测消费/错误传播/泄漏边界;A5 未批部分只落 termination 事实记录。**注**:EnvironmentPackageV1 仅身份+digest（无 prompt/test_patch/eval_cmd）,完整 v2 评分链归 T2-d/W3a——W2a 不宣称单独产出可评分链（此两条代码事实为 codex 终核补充,实现批开工时逐行复核） | A;若数据线程在做 T2-d/e 先切文件/接口 ownership | unknown task/漏包/digest mismatch fail-closed;泄漏边界正反例;timeout 事实各一例 |
| **T2-d / T2-e**（数据线承接,非 Wave1） | v2 grader 正链（clean checkout→agent frozen patch→**official test_patch 后写**→vendor 复核 eval_cmd→SWE-Gym parser→GradingReport;grader 永不回读 live workspace;归 T2-d/W3a 串行）与四门 runner（T2-e）——由既有数据线程继续,RH2 Wave1 不重复造 | T2-c 已完成（216 bundle 稳定,事实纠正:非"未生成"） | — |
| **W2b 真实数据集成**（条件式,非 Wave1） | 真实资格数据进训练 runtime/GPU campaign 的集成层。**启动条件 = T2-d/e 完成且 owner 在 C 包确认 GPU spike 数据目标**（216 题是否进 GPU 未决,不预绑定） | T2-d/e ∧ C | — |
| **W3a formal 评分冻结** | runtime owner 停止 execution scope 替换 NO-GO 屏障;git-free census/exporter;fresh grader 不读 live workspace;formal B6 组合测试（正常写完/后台/root 迟写/Git 注入/binary/symlink/mode/grader 隔离）;**cleanup 优先级反转**:核心 admission record（identity/patch/GradingReport/EligibilityReport 及引用）写失败→样本绝不交付+run-fatal+**仍执行** revoke session/终止 scope/清容器,仅 cleanup 自身失败才 quarantine;timeline/telemetry 类降为 best-effort 不统治 cleanup | W2a、T2-d（v2 评分正链）;**与 W3b 串行或先切文件所有权** | B6 清单全绿;核心记录写失败仍清理的负例;task-local vs run-fatal 分界 |
| **W3b 最小安全链**（codex 复审重构:正向能力事实,删 CommandFilter 平台） | 每个 sandbox 创建后**直接核实并记录正向能力事实**:non-root/capabilities/pids/CPU/内存/writable mount allowlist+quota/网络仅可达模型代理/hidden+grader 资产不在 mount/git future refs+reflog+remotes 已清——**缺任一项不产训练样本**,事实进 eligibility(接 W1b security 维)。**删除** CommandFilter+dummy 观测+attempted/executed 平台（python/subprocess 可绕;向量覆盖:出网→内核级网络隔离,reflog→镜像清理,改测试→patch hygiene,hidden→mount 隔离;被阻断操作返回真实工具错误）。H7 GPU 验收改形为真实 CC run 中的边界核实 | W1b;与 W3a 串行或所有权切分 | 每能力项一个"未生效即拦"负例;作弊向量逐条由保留机制覆盖的正反例;正常轨迹不误拒 |
| **W4 JIT/staleness** | publish 后 drain（miles 侧窄 commit）;持续 producer 保留;H5 硬门读取的最小计时事件;一次性 CPU materialization benchmark。**先于 W5b 执行以冻结 train/publish/drain 顺序** | B | B-ready/B-not-ready/publish/zero-signal/fresh-stale refill/事件配对负例 |
| **W5a shutdown + 资源闭包** | 就绪稿 §2.6 关闭链;有界超时保首因;campaign supervisor **缩为 launch trap + run-label 残留检查**;普通 evidence flush 失败不阻止 cleanup;承接原 W6 的资源闭包一次性取数（内存保守上界+fsync 延迟） | A | 正常/异常关闭、关闭后禁 submit、无残留三分支;flush 失败仍清理负例 |
| **W5b checkpoint 冷恢复**（codex 复审瘦身+补全） | **保留**:published-boundary checkpoint;model/optimizer/scheduler/RNG/last-published-version 同代;薄 COMMITTED marker;空 buffer 新 segment;(segment_id, numeric_version) 复合身份;不恢复旧 cursor;冷恢复后完成 optimizer step。**补全（codex 终核修正 off-by-one）**:updater/rank 的 version bootstrap——train_async 启动即有一次 update_weights 且 updater 在 publish 前先 +1,故恢复到已发布版本 p 时 updater 内部计数器应恢复为 **p-1**（bootstrap 重发该 checkpoint 标记 p,首次真实更新才 p+1）;若选择绕过 bootstrap publish 直接 load/tag p,须显式实现另一条启动路径——**不得把所有对象无差别设为 p**（p2p.py:61/mixin.py:358,覆盖全部 updater 不只 rollout manager）。**删除**:独立 frontier-discard receipt（改普通恢复日志行）/evidence watermark/全量 crash matrix→只测未完成 checkpoint、损坏 checkpoint、完整冷恢复三场景 | B;**在 W4 之后**（同触 train/publish 顺序） | 三场景正反例;五元组不混代;恢复后版本 p→p+1 |
| ~~**W6**~~（codex 复审:整包删除,职责分流——训练事件由 W1~W5 就地产生;资源闭包→W5a;train/eval 分离→W8;W7 直接消费最小指标;"probe 题不训"属实验选择非 runtime 断言） | — | — |
| **W8 eval 运输链** | 标准非 FA before/after eval 本地链:接同一 source/model/tokenizer/环境解析器;eval taskset 身份分离断言;eval 前 producer/grading/update 停止断言;结果绑定显式 checkpoint digest（拒绝 latest）;小模型/fixture 验证 base 与 post-update 双 checkpoint 全流程与失败传播。**skip 不得洗绿（codex 终核补）**:miles EvalDispatcher 把 busy/export_failed/crashed 记 skip 而非失败——W8 验收必须要求两个显式 checkpoint 的 eval **真正完成并产出绑定结果**,任一 skip/failure = 首训就绪验收失败,不得以"已 dispatch/已 drain"充数 | W2a（环境解析器）、W5a（producer/shutdown 语义）、W5b（checkpoint identity） | 身份分离/producer 未停/latest 回退/skip 洗绿四负例;双 checkpoint fixture 正例 |
| **W7 实验包** | 从范围反向生成 launch/collector/judge/thresholds（不继承未审文件）。**judge 覆盖 = 本计划声称合格的全部训练/系统正确性判定**（codex 终核纠正此前过窄口径）:parity/守恒/R3 消费/零信号 + fresh grading/eligibility + 安全正向能力事实 + consume-time staleness + optimizer→publish→version + 冷恢复 + 正常 shutdown + eval checkpoint 绑定;**不含**授权 manifest/阶段闸门类判定 | C、W0~W5、W8（W6 已删除,旧依赖串作废） | 双 base 全绿+self-test+preflight 正反例 |

**界外（本计划不含,另行排期）**：GPU pass-rate 预筛与 pre-RL 行为诊断（单卡作业或租期尾项,C 包定载体）；held-out 冻结与题单选定（数据线,依赖四门+预筛）；R2E ingestion（D3 闭环档下首训不做）。

## §4 决策包 B/C（内容冻结,时点后置）

**B（Wave3 前）**：提前 drain 关闭落账（已口头批准）；正常 shutdown 硬门落账（已口头批准）；`max_weight_staleness` 在线硬拒语义；W5b checkpoint 合同（published-boundary/新 segment/frontier discard）；明确不做 pending replay/精确 cursor/exactly-once；`update_weights_interval` 支持口径（推荐首版=1）。
**C（W7/租卡前）**：精确 GPU profile 或 qualified envelope（含 A5 timeout 数值、staleness/buffer/并发值）；staleness/成本/连续更新（≥3+≥3）/资源阈值；资格任务集选定（记录 taskset 内容 digest 作被动身份,不当授权门）；H1~H10 预算与停止规则；D3 闭环档确认与预筛载体；**首训 harness 工具面（subagent/compaction/fork 开闭）及 fanout 覆盖判定项的去留**（就绪稿 §4.11 条件句的显式化）；launch/judge/thresholds 最终形态。

## §5 下一步

1. codex 对 §1/§2 做写码前审查 → owner 一次拍板 A；
2. 拍板即回写 05/04/00-status 修订注记 + E 系定案（E2/E7/E10/附录 A）迁移修订注记 + 以 append-only 注记结清 fa2a 决策包 D1b（仅限首训 profile 范围,不改写旧批准史）+ A4 注明取代旧 scope 的 CommandFilter/attempted-executed 方案（单独提交）；
3. Wave1 三包并行开工（W0 ∥ W1a ∥ W2a;T2-d/e 由数据线并行），照现行节奏：agent 批实现 → codex 聚焦复核 → spike-log 落账；
4. 防御清理落地项：C3/C7 governed buffer/ledger 未接线原型**可保留为 spike-only 代码或日后单独清理**——其删除不是 Wave1 前置,且不得与生产链改动混同一 commit（codex 终核）;既有 lanes/证据系统冻结不扩建。**bringup.py:705-715 的临时无条件拒绝只能在 W1b+W3a+W3b 完成后删除**（不在 Wave1 提前删,且不得误删 fa_formal 的真实 version/barrier/security/config capability 检查——那些是本体不是仪式）。

## §6 防御清理原则（2026-09-01 Claude 提案,待 owner 确认;长期有效）

**删除**:谁批准过、项目处于哪个阶段、是否允许操作者启动（授权公式/manifest/解封仪式/账本扩建/闸门代码化）——owner 即授权系统,判断不写进代码。
**保留**:本次实际输入（taskset/env/grader/model/config digest 被动记录）、本次实际能力（sandbox 正向能力事实）、进入 loss 的逐层事实（身份/eligibility/分母/mask 对齐/reward 可信）、恢复代际（segment/version)。
今后任何 W 包或审查建议中出现授权官僚类设计,直接按本条拒绝,不再提请 owner 决策。