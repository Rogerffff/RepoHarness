# 决策包 D2 + B —— v2（owner 2026-09-04 已拍板）

日期：2026-09-04。状态：**已批准**（owner 于 2026-09-04 确认四个主方向并给出三条细化；v1 = Claude 2026-09-03 提案，经 codex 逐项复核修正——v1 的四处根本性缺失见 §0）。本文取代 v1；实现按本文，冲突以本文为准。

## §0 v1 的四处根本性缺失（codex 复核成立，已纳入本文）

1. 每轨迹 `SandboxCapabilityFacts` 证明系统是把"容器创建器是否正确"变成"每条样本是否带证明"——声明 ≠ 执行，先跑完昂贵 rollout 再 DROP_GROUP，补采还会重复失败。→ 改为创建期强制 + 启动前探针 + run 级记录（D2-2）。
2. "改测试路径 = 实锤 reward hacking"是错误前提——新增回归测试是正常 SWE 行为。→ 可信评分投影（D2-3）。
3. `TrajectoryProjection` 不是模型可见面，对它做 marker 扫描既测不到真实泄漏又会因字段名误报丢整组。→ 删除其资格语义（D2-4）。
4. finalize-time 第二套 staleness 阈值造成重复配置与政策所有权，解决不了 finalize 后继续变 stale。→ consume-time 唯一权威（B-1）。

另：v1 "该 prompt 本轮次不再出现"说错（换 epoch 会再采样）；"N=1 基本抹掉 async 收益 / N=2 保证 DIS 稳定"是推测，撤回；单 engine 是绕开 MilesRouter 错发的临时限制而非拓扑结论（B-5b）。

---

## D2（已批）

### D2-1 评分正链（W3a）

- 首个 SWE patch profile 采用 **fresh、断网、隔离 grader**，不做原地评分：`clean base checkout → 应用 candidate_solution_delta（见 D2-3）→ grader 侧后写 official test_patch → vendor 复核 eval_cmd → SWE-Gym parser → GradingReport`。
- **状态所有权转移**：FrozenPatchArtifact + baseline + 身份/digest 校验并持久化成功后，冻结产物即评分唯一权威，**立即释放 rollout 容器**，再进有界评分队列。删除"评分后回读原 workspace `verify_integrity()` 才承认 reward"的主链依赖（可保留为非阻塞 debug 探针或删除）。**验收前提**：测试证明 grader 拿不到 rollout 容器、唯一输入是持久化产物。
- **W3a 验收项：完整分段计时**（一次 physical attempt 的生命周期，最小可聚合记录，不建监控平台）：`runtime_quiescence / baseline_census / post_census / artifact_capture / artifact_persist / grading_queue_wait / grader_start_and_verify / grader_baseline_rebuild / delta_apply / test / parser_and_report / grader_cleanup / rollout_container_hold_after_freeze`（秒）。GPU spike 报告各段 p50/p95、评分队列打满次数、评分吞吐是否限制合格组进 trainer。
- 性能优化（grader 长驻复用、baseline 缓存、tar 流式重放）**等计时证据再做**。S1 旧链证据（评分 8.8s / attempt 124s）不代表 formal 链成本。
- "fresh" 定义 = 评分状态无 agent 污染、无跨 attempt 污染；每 attempt 新建容器是当前实现方式，不冻结为所有未来 Environment 的全局合同。SWE-Gym 真实 parser/selector/eval_cmd/install 流程、official test_patch 具体处理、repo-specific hygiene、reward 形态、真实镜像资格等 taskset 确定后再做（T2-d/W2b）。
- 事实：官方 swebench 4.1.0 对 SWE-Gym 11 仓库零覆盖，216 题 eval 常量来自 vendored fork（评分链"官方性"以 vendor 复核为准）。

### D2-2 最小安全边界（W3b）——owner 细化："sandbox profile 只做启动前验证和 run 级记录，不再建立任何逐轨迹 capability eligibility"

- **改判 A3 的实现机制**（目标不变：不许 `findings=()` 假过）：首训只支持**一个正式 rollout Docker profile + 一个独立 grader Docker profile**，安全与资源约束由 sandbox 创建器**直接配置**，并在模型进程/候选测试启动前做**最小实际核对**（docker inspect / 探针）。**配置缺失或实际未生效 → 不启动/停止 run**；不允许先完成 rollout 再靠 eligibility DROP_GROUP 补救。
- **删除**：`GenerateFn.sandbox_capability_facts_provider`、`finalize_rollout(sandbox_capability_facts*)` 训练语义、`sandbox_capability_facts_missing / sandbox_capability_unverified_* → DROP_GROUP`、每 attempt 能力事实与 trajectory/lease 绑定、`REQUIRED_SANDBOX_CAPABILITIES` 作为 eligibility 必需集。`SandboxCapabilityFacts` 类型仅保留为冻结历史 schema（S1 evidence/inspector 兼容读路径），不进新 formal 链。security 维改为只判"本次轨迹是否发生了影响 reward 可信的执行级事实"（executed 级泄漏/越权/结构不安全 artifact）。
- **保留一份 run 级记录**（§6 允许的"本次实际能力"被动记录，不是证明系统）：`runtime_profile_digest`（profile 参数摘要）+ 启动前探针报告引用 + 实际值（CPU/memory+swap/PID/存储预算/mount 清单/网络策略/用户/capabilities）写入 run evidence；样本/audit 只盖 `runtime_profile_digest` 供 join。
- **三层边界**：
  - reward 可信事实（rollout）：模型控制进程非 root（可信初始化可用 root）、CapEff=0 + no-new-privileges、**网络 egress allowlist**（loopback + 模型代理 + 环境声明的内部服务；公网/云 metadata/宿主服务默认拒；仅设代理 env 或普通 bridge 不算证明——须探针验证 direct-IP 不可达）、**hidden/grader 资产对模型不可访问**（核对 mount、镜像、env、public bundle、prompt/模型可见投影；用 canary 反例验证）、**solution-bearing Git 状态不可恢复**（删 refs/reflog/remotes 之外还要处理 dangling future object，`git fsck`/SHA 找回负测试；保留 base 之前正常历史）、宿主 bind mount 只来自安全清单。
  - 运行资源事实（rollout 与 grader 共同）：PID/CPU/memory+swap/容器可写存储总预算/bind mount 只读可写清单——保护宿主与吞吐，**数值归 C/profile 实测校准**，但强制能力必须在 W3b 接好、实际值进 run 记录；资源限额触发的 OOM/timeout = infra/resource failure（ABORTED），**不得伪装成 reward=0**；容器私有路径（/testbed、/tmp、/home/agent、缓存）可写不算违规。
  - 角色事实：rollout 与 grader **不同 profile、绝不复用同一活动容器**；grader 全断网（deny_all）、可读可信侧私有材料，执行候选代码的进程**要求非 root**（Claude 比 codex 更严：仅当镜像证明做不到时由探针记录实际用户并在 C 明示）、同受资源与权限限制、不得继承 agent 状态、不跨 attempt 污染。事实：grader 现状只有 `--network none`，用户 root，无 CPU/内存/PID/capability 限制——W3b 必修。
- **失败前移**：正式 profile 缺必需配置 → 启动失败；容器创建后核对发现未生效 → 不启动 CC/测试、停止 run（同 profile 补采不会修好它）；运行期真实发现隔离失效 → 停止 run；瞬时 Docker 创建失败 → 既有 task-local infra 语义；已在合格 sandbox 完成的轨迹不再因缺 sidecar 被 DROP。
- **W7/H7**：W7 只调用同一正式创建/验证入口（run 模式 / verify·dry-run 模式），不复制第二套规则。H7 租期只做两件事：在正式 profile 中复跑一组预先写好、判定确定的最小边界探针；跑一条真实 CC 多轮任务确认代理可达、工具/capture/cleanup 正常、限制不误伤。**不在租期设计红队**；Safety-Q 不进 policy loss。
- 保留的直接验收（本地）：docker inspect 证明 user/caps/PID/memory/mount/network；rollout 看不到 private/validation bundle；公网/direct-IP 不可达而代理可达；Git future solution 不可恢复；grader 独立 profile 且断网；正常 CC rollout 在同 profile 下可完成。

### D2-3 失败分类：可信评分投影——owner 细化："暂按当前 SWE adapter 实现，通用控制面定义等数据确定后再做"

- **公共不变量**：agent 对测试与评分控制面的修改**不能对最终 reward 产生因果影响**；不判断意图，不因测试路径变化自动 DROP_GROUP。
- **语义**：完整 frozen artifact 保存供审计/遥测；拆分为 `candidate_solution_delta`（重放到 fresh grader）与 `ignored_validation_delta`（测试/评分控制面：**不重放**）；grader 注入 official test_patch、执行可信 eval_cmd、正常产生 0/1。只改测试没修代码 → 自然 0；同时写测试且真修好 → 正常 1（轨迹级 credit assignment 的通用限制，不是 hacking 证据；若要惩罚无效增测试/过多工具调用，另设过程 reward，不改 0/1）。这不违反"评分不可得不得伪装 0 分"——评分并非不可得。
- **首训实现口径**：控制面 = 当前 SWE adapter 的 `HygieneRules`（official test_patch 精确文件 + 测试 glob + 保留路径 `.rh2*`/`rh2/*`），solution surface 按**排除法**（除控制面外皆重放）。已知不足（conftest.py/pytest.ini/tox.ini/setup.cfg·pyproject 的 pytest 段/插件/启动脚本等真正能改变测试收集的控制面未必覆盖）**登记不修**——通用 `allowed solution surface / evaluator·control surface / official test 恢复与注入规则` 由最终 environment adapter 在 taskset 确定后声明。
- **遥测**：每轨迹记录被忽略的控制面路径清单与计数（发现分布漂移）。
- **仍是 infra/security failure（fatal/隔离，不进评分投影）**：读取 hidden tests/golden/grader-only 材料；网络/mount/权限/Git 隔离失效；身份错接；symlink escape、FIFO/device 等结构不安全 artifact。`.rh2*`/`rh2/*` 路径命中 = 命名空间冲突不进投影，**不**单凭路径宣称安全边界被突破。
- 其余分类不变：普通 `tests_failed` 与可信 `patch_apply_failed` = reward=0 负样本正常进组；grader 隔离失效/hidden 可见/身份错接/scope 无法终止/核心 admission 记录写失败 = run-fatal（cleanup 仍执行）。

### D2-4 删除 `public_projection_marker_hit` 的资格语义

- `TrajectoryProjection` 是 rollout 结束后的 trainer/offline-export 中立投影（token 计数/span/mask/引用/reward facts/版本握手），**不是模型可见输入**；扫描发生在 rollout 与评分之后、不解引用 token/artifact 内容，测不到 prompt/mount/env/工具输出里的泄漏，却会因 `fail_to_pass_bonus` 这类字段名误报丢整组。
- **删除**：该 reason code 对 `security_and_leakage` 维的影响、admission 中的 DROP_GROUP 映射、附录 A/D2-4 对应行、`finalize_rollout()` 对 `ProjectionScanResult` 的强依赖、offline exporter 对 `scan_result.clean` 的重复门槛。旧 schema 只留冻结兼容读路径。
- **保留**：`scan_for_forbidden_markers()` 在真模型可见面（PublicTaskBundle、RolloutTaskView）的整树检查；hidden/grader 泄漏的主验证 = 结构与数据流证据 + **canary 反例**（向 private bundle 注入唯一串，检查最终模型请求、sandbox mount/env、工具可见面均无该串）；真实边界失效仍 run-fatal。
- "能力 producer 全局未接线 → 启动级 FATAL"随 D2-2 取消（producer 不存在了）；由创建入口的启动前核对取代。

---

## B（已批）

### B-1 staleness：consume-time 唯一权威——**改判 D1-4 的两阶段同阈值**

- **一次性语义**：采用 miles 的 group consume-time 定义与过滤：`group_staleness = current_published_rollout_weight_version − min(behavior_weight_version over every trainable token/turn/member)`，在 `DefaultDataBuffer.get()` 用 `--max-weight-staleness N` 做唯一过滤。`current_version` 是已发布给 rollout engine 的版本，仅在每 optimizer step 发布一次时才等于 step（B-4 固定 1，故首训一致）。
- **RH2 职责**：完整准确传递并校验每个可训练 token/turn 的 weight-version provenance（W1b 叶版本绑定保留：非空⟺Outcome 有版本、可解析 int、⊆ Outcome 版本、≤ current_version_at_finalize）；拒绝缺失/非法/未来版本；finalize-time lag 只记观测。**删除**：`SlimeBindingConfig.staleness_threshold` 作为 eligibility 阈值、W1b 的"显式阈值必传/载荷阈值≠权威即 FATAL"、eligibility 第七维改为"版本事实可用且合法"（契约语义修订，T0 已随本包批准）。
- **数值**：`--max-weight-staleness N` 是启动 profile 参数，必须显式传入并记入 run 配置/manifest；**不阻塞本地开发，改 N 不需要重走 B/T0**。W4 参数化覆盖 N=0/1/2/4、恰等/超阈/负 lag/跨版本/多 member；首次 GPU spike 起始 **N=2**（待实测）。GPU 记录：consume-time staleness 分布、stale 组丢弃比例、buffer 等待/补采/GPU 利用率、DIS 接受/拒绝比例、每 step 有效可训练 token。
- 负 lag/缺失/非法版本 = 版本账目错误（FATAL）；过期组处置由 B-2 统一。

### B-2 unused handler = `drop`

- `--async-unused-samples-handler drop`：put-time 含 ABORTED 的组与 consume-time 超阈组均不回队不立即重试；filter 拒绝组按既定语义直接丢弃。**准确语义**："本次 physical prompt group 不回队、不立即重试"——同一 dataset task 换 epoch 后可以新 group 再出现。首训不实现 retry/有界重试/sidecar 分区。
- **每次丢弃一条轻量结构化事件**（在 buffer 真正判定的三个分支记录：put ABORTED / get stale / filter keep=False）：task_id 或 opaque ref、`rh2_prompt_group_id`、group_index、drop_stage、reason_code、ABORTED 的 member_slot/physical_attempt_id、stale 的 oldest/current 版本与阈值、时间戳；不记 prompt/private/patch 内容。run 结束汇总各 reason 组数、总尝试/接受/丢弃、**按 task 的尝试/丢弃分母**（识别"长任务被系统性丢弃"的分布偏差）。事实：stock buffer 已有 `group_filtered` 事件（aborted/filter），stale 分支未发且不带版本差——W4 的 miles 侧窄 patch 补齐。不建 ledger/WAL，不成为新闸门。
- **no-progress**：简单运行参数 `max_time_without_accepted_group`——progress 指"获得一个最终可训练 group"，不因持续完成又持续 drop 而重置；数值归 C。

### B-3 冷恢复：**最小合同**（owner 细化："不建设联合 checkpoint、事务恢复或复合版本体系"）

- **依赖 miles 既有能力**：Megatron checkpoint（model/optimizer/scheduler/RNG）+ `RolloutDataSource.save/load`（sample_offset/epoch_id/group_index/index）+ `start_rollout_id`。
- **合同**：job death 后从**最近的 miles checkpoint** 重启；**buffer 与在飞组全部丢弃**（同 drop 语义）；不 replay、不精确 cursor resume、不 optimizer exactly-once、**不做 joint commit / COMMITTED marker / (segment_id, numeric_version) 复合身份**。
- **只修三个正确性点**（W5b 缩为此）：① updater 版本计数从恢复点继续——现状全部 updater `weight_version = 0`（`update_weight_from_tensor.py:103`、`update_weight_from_rdt.py:111`）且 bootstrap publish 把恢复权重错标 v1；改为按恢复的 rollout_id/已发布版本初始化（bootstrap 标 p，首次真实更新 p+1），使 spans/staleness 账目在重启后单调可比；② `data_source` 状态文件缺失 → **显式报错**而非静默从头（`data_source.py:146-149`）；③ 重启记录：新 run_id + 恢复自哪个 checkpoint/rollout_id 写入 evidence。
- **接受的残余**：checkpoint 保存点与"最后发布版本"之间若崩溃，重启后 bootstrap 重发 checkpoint 权重——因 buffer 已清空，对训练正确性无影响，只损失该窗口的样本；checkpoint 频率与可接受损失窗口归 C。
- 测试：完整冷恢复（版本从 p 继续、buffer 空、cursor 恢复）、状态文件缺失报错两场景。

### B-4 `update_weights_interval` = 1（固定）

每 optimizer step 发布一次，staleness 一代 = 一步。k>1 是 profile 扩展（须在 staleness/DIS 记账显式区分"步"与"发布代"）。

### B-5a pause mode = `retract`；B-5b engine 拓扑不在本地锁死

- **B-5a**：首个资格 profile `--pause-generation-mode retract`（权重更新期间在飞请求退回等待队列、重算 KV、跨 publish token 由 spans 如实记录）；GPU spike 量化重算 token、pause/update/resume 时间与吞吐损失。`in_place` 暂不资格化（旧 KV + 新权重在 RH2 custom request 路径未证明；非永久禁止）；`abort` 不用于 fully async。
- **B-5b（owner 已确认方向）**：**租卡前链路必须闭合多 engine 最小正确性**，不能只资格化单 engine。事实：P3 J4 = 4 训练卡 + 2×TP2 rollout engine；现有未批脚本把 `rollout_num_gpus_per_engine = rollout_num_gpus` 硬编码为单 engine 并 preflight 要求 `engine_count == 1`，是绕开 MilesRouter 忽略 `X-SMG-Routing-Key`（abort/版本查询错发）的临时限制，**不得转为正式资格语义**。新工作项 **W10**：abort 定向或广播（仿 miles abort-all：`/list_workers` 取全部 worker 广播同一 rid）；版本事实不经 router 随机查一台（随 B-1 删除单 engine 随机版本探测；如需 publish 后收敛事实，经 engine actor 查全部）；恢复 `rollout_num_gpus_per_engine` 普通配置、删 `engine_count == 1` 限制（只留整除/资源合法性检查）；两假 engine 本地反例（分发、rid abort 到达持有者、发布到全部 engine、版本不猜、单 engine 仍正常）；GPU 真多 engine e2e（生成/retract/发布/resume/跨 publish spans/mask/R3 tape 入 loss/有效 optimizer step）。**不做**：dead-engine 自动恢复、`/remove_worker` 弹性、在线缩扩容、FT 自动恢复、粘滞路由（首版）；任一 engine 死亡 = 停 run 按 B-3 重启。GPU 上同 rollout 卡数 matched comparison（如 1×TP4 vs 2×TP2）后定首训 engine 数。

### B-6 落账

提前 drain 关闭（W4）；正常 shutdown 硬门（W5a 已实现：残留/后到事实/双因进报告，不 ok 即非零退出；W7 读取口径 = `verdict.rh2` / `shutdown_report.json` 为时间首因，顶层 `primary_cause` 为 driver 视角；报告重写失败/事件漂移由 W7 用"退出码 + failure marker + canonical report"联合判断，不建 revision 状态机）；明确不做 pending replay/精确 cursor/exactly-once。

---

## 落地顺序（Wave3）

1. **前置清理批**（先于 W3/W4 开工，避免在将删机制上继续建设）：删每轨迹能力事实分支（provider/required/missing/unverified/lease 绑定）→ 删 finalize-time 阈值与 eligibility 第七维改语义 → 删 projection 扫描资格语义与 exporter 门槛 → 附录 A/W1b 行同步 → 相关测试 oracle 逐条登记 T1。
2. Wave3：**W3a**（D2-1 + D2-3 投影 + 计时）→ **W3b**（D2-2 双 profile + 创建期强制 + 启动前探针 + run 级记录）；∥ **W4**（consume-time 唯一权威接线、负 lag 拒绝、drop 事件、no-progress、JIT drain）→ **W5b**（最小冷恢复三点）；∥ **W10**（多 engine 最小正确性）。
3. 之后 W8 → C 包 → W7。
