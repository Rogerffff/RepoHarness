# 决策包 D2 + B（Wave3 前置；owner 拍板用）

日期：2026-09-03。性质：**Claude 提案，待 owner 拍板**（codex 可先复核）。范围来源：`06-first-training-local-execution-plan.md` §1 A4、§4 D2/B、§3 W3a/W3b/W4/W5b 行、附录 A。每项按协作协议格式：要决定什么 / 代码事实 / 方案 / 推荐及理由 / 长期代价 / 以后能改什么。**不含**任何 C 包事项（A5 timeout disposition、loss 终选、GPU 数值、taskset）。

> 一句话：D2 只有一个真正的训练语义选择（篡改测试轨迹"整组排除 vs 负样本"），其余是已写在 A4 里的边界确认；B 有六项，其中只有 staleness 数值和 unused handler 是需要你选值的，其余是结构确认与落账。

---

## D2（W3a/W3b 开工前拍板）= A4：评分正链 + 最小安全边界 + 失败分类

### D2-1 评分正链（W3a 冻结；T2-d 提供链本体）

- **要决定什么**：正式评分只走这一条链——`clean base checkout → 应用 agent 的 canonical frozen patch → grader 侧后写 official test_patch → 执行 vendor 复核过的 eval_cmd → SWE-Gym F2P/P2P parser → GradingReport`。fresh grader **永不回读 agent 的 live workspace**；`ValidationOnlyBundle/golden_patch` 永不进入正式 grader。
- **代码事实**：W2a/切片一已把 grading 材料剥离到 host 侧 `HostGradingView`（A9 共址于可信 RolloutManager）；grading spec/parser 已在 actor 内由 `PrivateGradingBundleV2` 构造（closure 无 golden）。**官方 swebench 4.1.0 对 SWE-Gym 11 个仓库零覆盖，216 题的 eval_cmd/常量全部来自 vendored fork**（W2a 复核事实）——评分链的"官方性"以 vendor 复核为准，不是上游 swebench。
- **方案**：(i) 如上（推荐）；(ii) 允许 grader 读取 live workspace 做增量评分——违反 reward 可信原则，否决；(iii) 首训改用 golden_patch 相似度打分——不是任务结局，否决。
- **推荐**：(i)。**长期代价**：每次评分一次 clean checkout（容器时间），首训可接受。**以后能改**：eval_cmd 来源若上游 swebench 补齐 SWE-Gym 覆盖，可切官方常量（T1，换来源不换链）。

### D2-2 最小安全边界（W3b 落地；九项正向能力事实）

- **要决定什么**：每个 sandbox 创建后**直接核实并记录**九项正向能力事实（W1b 第二段已把它定义为消费契约 `REQUIRED_SANDBOX_CAPABILITIES`，W3b 必须恰好产出这九项，并绑定本次 `SandboxLease.lease_id`）：non-root、capabilities 限制、pids 限制、CPU 限制、内存限制、writable mount allowlist+quota、网络仅可达模型代理、hidden/grader 资产不在 mount、git future refs/reflog/remotes 已清。**缺任一项不产训练样本**（eligibility security 维 = 非 online → DROP_GROUP）；违规 = FATAL。被阻断的操作对 agent **返回真实工具错误**。
- **代码事实**：W1b 第二段 gate 已切到"能力事实在场且无违规"，`findings=()` 不再算过；lease 绑定已核对（codex 复核 #5 修复）。CommandFilter/dummy 观测/attempted-executed 平台已按 A4/W3b 删除（python/subprocess 可绕，四个作弊向量各由保留机制覆盖：出网→内核级网络隔离，reflog→镜像清理，改测试→patch hygiene，hidden→mount 隔离）。
- **方案**：(i) 九项正向事实 + Docker/内核强边界（推荐）；(ii) 加 CommandFilter/审计代理层——可绕且是展示型平台，否决；(iii) microVM——首训明确不做。
- **推荐**：(i)。**长期代价**：Docker 边界不是 VM 级隔离——威胁模型 = 防 agent 作弊拿 reward，不是防敌意代码逃逸宿主（与 A9 同一口径）。**以后能改**：能力项可增（T1，改 W3b producer + 常量清单同批）；换 microVM 是新 T0。

### D2-3 失败分类（附录 A 已定其余；此处是**唯一需要你选的训练语义**）

- **要决定什么**：agent **实锤篡改测试/禁区文件**（patch hygiene 检出 `patch_test_tampering` / `patch_forbidden_contamination`，环境本身完好）的轨迹怎么处置。其它分类已定：普通 `tests_failed` 与可信 clean-grader 的 `patch_apply_failed` = **reward=0 负样本，正常进组**；hidden/grader 泄漏、隔离失效、身份错接、scope 无法终止、核心 admission 记录写失败 = run-fatal（cleanup 仍执行）。
- **代码事实**：现状 unsafe 形状 = `present_* + unsafe_artifact_permanent_rejection`，**reward_unavailable、无 EligibilityReport**（契约封闭豁免集）→ 附录 A 已定为 DROP_GROUP。要改成"负样本"必须先改 producer：clean grader 真正评分（官方 test_patch 后写会覆盖 agent 的测试改动）并出 EligibilityReport；**若 agent 篡改测试同时真的修好了代码，clean grader 会给 reward=1**——"负样本"选项实际上是"按真实结局评分"，不是"一律 0 分"。
- **方案**：
  - (i) **整组排除**（DROP_GROUP，不评分，不进任何统计）：实现最简（现状即是），训练分布上把"篡改"轨迹连同其兄弟组一起丢弃；代价 = 每出现一个篡改成员损失一整组（n=8）的采样算力，且模型学不到"篡改没有收益"的信号。
  - (ii) **按真实结局评分进组**：clean grader 评分（篡改被官方 test_patch 覆盖后按真实修复结果给 0/1），成员正常参与 baseline/advantage；代价 = 需要改 producer（unsafe 路径走完整评分 + EligibilityReport），并接受"篡改 + 真修好 → reward=1"——模型可能学到"篡改是中性的"。
  - (iii) 篡改一律 reward=0 进组：需要新的 reward 覆盖语义（P4 原则"评分不可得不得伪装 0 分"要改成"篡改惩罚为 0 分"），是新的 reward 规则，T0 且影响分布。
- **推荐**：**首训取 (i) 整组排除**。理由：reward 语义干净（篡改轨迹的 reward 归因本就含糊），零实现成本，无新 reward 规则；先用遥测统计篡改率——若首训中篡改率可观（如 >2% 成员），再以 D2 修订走 (ii)（需改 producer，T1 实现 + owner 确认分布变化）。**长期代价**：篡改率高时算力浪费与"篡改无惩罚"两种损失都存在，但首训目标是验证闭环不是最大化能力。**以后能改**：(i)→(ii) 是 producer 改动 + 附录 A 一行；(iii) 需新 T0。

### D2-4 与 D2 同批确认的小项（无需你选值，确认即可）

- `public_projection_marker_hit`：默认 ineligible（DROP_GROUP）；若证实为**环境侧**泄漏（hidden 资产真进了模型可见面）→ FATAL。（附录 A 已写。）
- "能力 producer 全局未接线 → 启动级 FATAL"落在 W7 preflight（不在 W1b 代码里），W3b 只负责产出事实。
- H7 的 GPU 验收形态改为"真实 CC run 中的边界核实"（不做展示型红队）。
- 明确不做：microVM、透明通用代理、LLM claim-check、完整红队（原样）。

---

## B（W4/W5b 开工前拍板）

### B-1 staleness：唯一语义 + 阈值数值（**W1b formal 启用的前置**）

- **要决定什么**：(a) staleness 的**定义**与两阶段检查的口径；(b) **数值**。
- **代码事实**：miles `--max-weight-staleness` **默认 None = 不过滤**（`arguments.py:686`），消费点在 `DefaultDataBuffer.get()`：`staleness = current_version − group 内最老 weight_version`，超阈组交 unused handler；per-token spans（patch 0008/0009）已把跨更新 turn 的全部版本并入 `Sample.weight_versions`，所以"最老版本"不再低估。RH2 侧 finalize-time 用 EligibilityReport 的 `policy_staleness` 维（BackendHandshake：`policy_version − min(weight_versions_seen)`），阈值权威 = `SlimeBindingConfig.staleness_threshold`（W1b 已改为**必须显式传入**，旧隐式默认 4 已禁止；未传 → formal 启动即拒）。W1b filter 已核对叶版本 ⊆ Outcome 版本且 ≤ current_version_at_finalize；**consume-time 负 lag 拒绝归 W4**（miles get() 侧窄 patch）。
- **方案（语义）**：单一权威配置 `rh2_max_weight_staleness = N`，同时驱动 miles `--max-weight-staleness N` 与 RH2 `staleness_threshold N`（W4 接线并断言两处相等）；**finalize-time 超阈 → 该成员非 online → DROP_GROUP**（下界检查，早拒省 buffer）；**consume-time 超阈 → 交 unused handler（按 B-2）**；consume-time 出现负 lag → FATAL（版本事实矛盾）。不做"stale 但降权训练"（那是新的 loss 语义）。
- **方案（数值）**：
  - N=1：近 on-policy，async 收益基本丧失（一次 publish 期间只允许一代差），补采率高；
  - **N=2**（推荐）：允许两代差，faithful DIS 的重要性权重在支持集上仍稳定，信任区间（0.8/3.0）触发拒绝的比例可控；
  - N=4：现旧隐式默认，async 吞吐最好，但 DIS 拒绝/零信号风险上升，首训没有数据支撑。
- **推荐**：语义如上；数值 **N=2**。理由：首训要的是闭环可信而非吞吐；2 给 fully-async 留出真实的跨 publish 重叠（否则 W4 的 JIT drain 语义无法被验证），又不至于让 DIS 校正面过大。**GPU spike 记录 staleness 分布与 DIS 拒绝率后，数值可作为 profile 参数经 B 修订调整**（不是 C 悄悄改）。**长期代价**：N 偏小 → GPU 利用率下降；N 偏大 → 训练信号偏离当前策略。**以后能改**：数值随时（B 修订）；语义（如加 stale 降权）是新 T0。

### B-2 unused handler：`retry` 还是 `drop`

- **要决定什么**：put-time ABORTED 组与 get-time 超龄组的处置。（dynamic filter 的 keep=False 组**固定丢弃，不经 handler，没有选项**——A2 已澄清。）
- **代码事实**：miles 默认 `drop`（`arguments.py:720`）；`retry` 把 prompt 回数据源重生成，**无有界重试**——确定性失败的 prompt 会反复回队。W5a 复核 F2：若选 retry，`generate.py` 的 sidecar 按 trajectory_id 固定文件名覆盖写，attempt 2 会改写 attempt 1 的 eligibility/projection/capture sidecar——必须先按 physical_attempt_id 分区。
- **方案**：(i) **drop**（推荐）：ABORTED/超龄组直接放弃，持续 producer 用后续 prompt 补足；该 prompt 本轮次不再出现（覆盖率影响记遥测）；同时**显式禁用 retry 支持面**并修订 W1a 报告口径。(ii) retry：需先做 sidecar 分区 + 有界重试计数（新工作项）。
- **推荐**：(i) drop。理由：零实现成本、无重试风暴、与 miles 默认一致；首训不需要同 prompt 重试语义。**长期代价**：transient 故障导致的 prompt 损失不可回收（记遥测即可）。**以后能改**：切 retry = sidecar 分区 + bounded retry 的 T1 工作项 + B 修订。
- **同批**：有界 no-progress 停止规则（连续无法成 batch 不得无限 warning 烧租期）——**必须有**，数值归 C。

### B-3 W5b checkpoint 冷恢复合同

- **要决定什么**：崩溃/job death 后从 checkpoint 恢复的语义边界。
- **代码事实**：miles 恢复链三连断（已核实）：无 joint commit；data_source cursor 缺失时静默从头（`data_source.py:146-149`）；**所有 updater 启动 version=0 且 bootstrap publish 把恢复的旧权重错标为 v1**（`p2p.py:61`、`mixin.py:358`）——这会直接摧毁 spans/staleness 审计。train_async 启动即有一次 update_weights，updater 在 publish 前先 +1。
- **方案**：
  - (i) **published-boundary 联合 checkpoint**（推荐）：model/optimizer/scheduler/RNG/last-published-version 同代写入 + 薄 COMMITTED marker；恢复后 **buffer 清空开新 segment**（不恢复旧 cursor、不 replay 在飞组）；身份用 `(segment_id, numeric_version)` 复合键；updater 计数器恢复为 **p−1**，bootstrap publish 标 p，首次真实更新 p+1（或显式绕过 bootstrap 的另一条启动路径，不得无差别设 p）；frontier 丢弃只作普通恢复日志；冷恢复后完成一次 optimizer step 作为活性验证。测试只覆盖三场景：未完成 checkpoint、损坏 checkpoint、完整冷恢复。
  - (ii) 精确恢复：pending replay + 精确 cursor resume + optimizer exactly-once——复杂度高、首训无需，**明确不做**。
  - (iii) 不做冷恢复（job death = 从头）：省 W5b，但就绪稿 campaign 的"预期 job death → Segment B"资格项无法验证，且 updater 错标 v1 的 bug 不修会污染任何重启后的 staleness 账——否决。
- **推荐**：(i)。**长期代价**：崩溃时丢失 buffer 内未消费组与在飞组（可接受，按 drop 语义）；segment 复合身份让所有版本比较多一个维度。**以后能改**：加 replay 是新 T0；三场景外的 crash matrix 按需补（T1）。

### B-4 `update_weights_interval` 支持口径

- **要决定什么**：每几次 optimizer step 发布一次权重。
- **代码事实**：miles 默认 1（`arguments.py:794`）。间隔 >1 时"policy version"与"optimizer step"脱钩，staleness 的代数含义变成"发布代"而非"步"，DIS 的 behavior/target 差距被放大。
- **方案**：(i) **首版固定 1**（推荐）：语义最简，staleness 一代 = 一步；(ii) 支持 k>1：需在 staleness 定义与 DIS 记账里显式区分"步"与"发布代"。
- **推荐**：(i)。**以后能改**：支持 k>1 是 profile 扩展（T1 实现 + B 修订说明语义）。

### B-5 pause mode 与 engine 支持面

- **要决定什么**：权重更新时在飞请求的处置模式；首个资格 profile 的 engine 数。
- **代码事实**：miles `--pause-generation-mode` 默认 `retract`（`arguments.py:800-809`）：running 请求退回等待队列、恢复后重算 KV（spans 记录跨版本 token）；`in_place` 冻结请求并沿用已有 KV cache——**RH2 custom request 路径（AnthropicAdapter → rh2_call_sglang_generate）下 in_place 的 KV/weight-version 隔离尚未证明**；fully-async 禁止 `abort`（`arguments.py:62`）。#2783 上游耦合同样指向 retract。
- **方案**：(i) **retract + 单 engine**（推荐）作为首个资格支持面；(ii) in_place：需先证明隔离（新验证项）；(iii) 多 engine：数据点归 C（卡数/TP/placement）。
- **推荐**：(i)。**长期代价**：retract 重算 KV 有吞吐损失（GPU spike 量化）。**以后能改**：in_place 与多 engine 都是 profile 扩展，不改训练语义。

### B-6 落账项（已口头批准，无需再决定，只需在拍板时一并确认写入）

- **提前 drain 关闭**：publish 后才 drain（W4 miles 侧窄 commit），不再有"跨 publish 提前 drain 使 staleness 低报一代"的路径。
- **正常 shutdown 为硬门**：campaign 每段必须以 `shutdown_report.json ok=true` 结束（W5a 已实现：残留/后到事实/driver 与 worker 双因均进报告；不 ok 即 run 非零退出）。
- **明确不做**：pending replay、精确 cursor resume、optimizer exactly-once（B-3 (ii)）。

---

## 拍板格式建议

你可以直接回复类似：

```text
D2：D2-1 (i)、D2-2 (i)、D2-3 (i) 整组排除、D2-4 确认。
B：B-1 语义如提案，N=2；B-2 drop；B-3 (i)；B-4 固定 1；B-5 retract+单 engine；B-6 落账。
```

拍板后我：① 回写 06 §1 A4/§4 B 为"已批准"并注明日期；② 把 B-1 数值与 B-2 选择接进 W1b formal 启动配置（显式传入，不留默认）；③ 开 Wave3：W3a→W3b（等 T2-d 交接）∥ W4→W5b。
