# RepoHarness 新架构实施计划 V1（草案，待讨论定稿）

本文是执行层计划文档。输入是两份已定稿文档：主设计文档 `repo_harness_design_doc2_verifiers_based.md`（架构与定案）和 `repo_harness_final_review_before_implementation.md`（范围 P0/P1/P2/backlog、D1~D7 与 GLM-5.2 增补定案）。本文不重复论证"为什么"，只回答"按什么顺序做、每步做完怎么算数、还有哪些执行层决策要定"。

本文自身的待讨论决策集中在第 8 章（E1~E8），定稿前本文标注"草案"。

---

## 1. 执行总策略

四条原则，全部继承自项目已验证的工作方式：

1. **每个阶段一个最小可验证增量**。阶段完成的判据不是"代码写完"，而是有一个可以独立运行、有产出物、能被复核的验收动作。
2. **验收继承 inspector fail-closed 范式**（16G 系列的成果）：每阶段产出 acceptance summary + source digests + 独立 inspector 命令；字段白名单严格枚举；forbidden marker 扫描。但 evidence 体系全新建立（E6），不复用旧 stage16g 目录。
3. **先闭环后加固**：S0/S1 先跑通端到端（允许安全隔离不完备），S2/S3 加固到训练信号可信。任何"训练资格"字段从 S1 第一天就存在，但在加固完成前一律标注降级——fail closed 从第一条轨迹开始，而不是加固后补。
4. **数据驱动后续决策**：计时埋点（agent / grading_prep / grading_test / env_reset / image_pull）和失败归因从 S1 强制开始积累，backlog B1~B7 与 prewarm、评分服务化等决策全部由实测数字触发。

阶段与设计文档 §10 方向阶段的关系：本文把 S0、S1 细化到任务级，S2~S5 只给概要（等 S0/S1 的实测反馈再细化，避免提前锁死错误假设）。

---

## 2. 新包结构提案（对应决策 E1）

按 D1 定案：留在当前仓库，新开清晰边界的模块。推荐布局：

```text
src/repoharness2/                  # 包名待定（E1），下称 rh2
  contracts/                       # 全部 pydantic schema（extra="forbid"）
    trajectory.py                  #   ★中立投影契约：TrajectoryProjection / BranchProjection /
                                   #    CompactedSubTraceLineage / TokenSpan / LossMaskSpan /
                                   #    LogprobProvenance / RoutingTensorRef / SamplingMaskRef / RewardFacts
                                   #    治理层与所有 adapter 只消费它，不直接碰 verifiers Trace / slime Sample
    eligibility.py                 #   EligibilityReport / TrainingEligibilityGate 输入事实
    grading.py                     #   GradingReport / grading_failure_category
    findings.py                    #   AntiCheatFinding / TrajectoryQualityFinding（D7/红队共用）
    anti_hack.py                   #   AntiHackEvent / blocked_tool_call_ref / dummy_observation_ref /
                                   #    attempted|executed（S1 落 schema，S2 才接真实 command filter）
    handshake.py                   #   后端握手字段（policy version / staleness / logprob_source / 组信号）
    timing.py                      #   五类计时埋点 schema
  runtime/
    swe_see_docker.py              #   子类 verifiers DockerRuntime：断网/非root/seccomp/资源限制
    event_log.py                   #   轻量命令事件日志 + provenance（P1 档）
    network_policy.py              #   白名单出网代理配置（预装为主 + 代理为辅）
  taskset/
    swebench.py                    #   SWE taskset（借 harbor 模板、隔离评分版）
    materialize.py                 #   workspace 物化 + git 清洗挂点
  grading/
    manager.py                     #   SWEGradingManager（prepare/grade/gc；backend-neutral 接口）
    queue.py                       #   有界评分队列 + 反压（P11）
  governance/
    gate.py                        #   TrainingEligibilityGate（双拓扑共享 finalize 关口）
    projection.py                  #   public projection 扫描（继承 L4/L5 语义）
    wrapper.py                     #   Episode 外层 wrapper（gate + grading + artifact writer 宿主）
  adapters/
    project_from_verifiers.py      #   verifiers Trace → TrajectoryProjection（S1 唯一实现的投影 adapter）
    project_from_slime.py          #   slime Sample/树 → TrajectoryProjection（形态 B 启用时才写）
    offline_export/                #   TrajectoryProjection → 离线样本（S1 最早闭环；对接 warm-start 过滤）
    slime/                         #   首个在线后端（形态 A/B 由 S0 定）
    verl/                          #   S5
  anticheat/
    git_sanitizer.py               #   物化期 time-travel 净化
    command_filter.py              #   运行期在线拦截（block + dummy + 继续）
    claim_check.py                 #   谎报成功规则检测（读 event_log）
  envprod/                         # 离线环境生产线
    validation.py                  #   empty/golden/F2P-P2F/假阳性解/非功能verifier/确定性
    freeze.py                      #   环境包 digest 冻结 + benchmark card
    redteam/                       #   红队环境包 fixtures（D4）

tests/repoharness2/
  contract_verifiers/              # verifiers pin 行为契约测试（升级 verifiers 前必须先过）
  unit/ integration/
```

要点：`contracts/` 先行——它是治理层的宪法，S1 的所有组件围绕它写；`wrapper.py` 是设计文档 §5.6 定案的"双拓扑共享 finalize 关口"的物理位置。

---

## 3. S0 详细计划：可行性验证（时间盒建议 1~2 周，E8）

S0 的性质是**验证实验，不是建设**——允许代码是一次性脚本，产出物是结论报告。

| # | 任务 | 做法 | 验收产出物 |
| --- | --- | --- | --- |
| S0-0 | 文档与接手上下文切换 | 改写 AGENTS.md / README 进度章节（§1.5 承诺）：声明 16G 线终止、新架构阶段体系、旧代码冻结为 legacy——**放在所有实验之前**，否则接手线程仍被旧 16G 状态误导 | AGENTS.md / README 新版 |
| S0-1 | 依赖底座 | uv 固定 verifiers commit（E3，pin `5885ab9c`）；装通 prime-sandboxes / prime-tunnel / renderers；确认 Docker runtime 可用 | 环境清单 + V1 结论（prime 依赖能不能用 → 方案 A 是否可行） |
| S0-2 | verifiers 行为契约测试 | 以 `5885ab9c` 为准为四个依赖行为写 pytest：token identity fork 分叉行为、Rollout 生命周期顺序（`Taskset.setup(task,trace,runtime)`→run→finalize→score→teardown，**注意 setup 新增 trace 参数**）、EnvServer wire 格式、TrainClient 请求协议 | `tests/repoharness2/contract_verifiers/` 全绿；升级 verifiers 的守门测试 |
| S0-3 | 玩具闭环 | verifiers `default` harness（bash+edit）+ `null` harness（纯 chat）各跑一次玩具 taskset，in-process 跑通 rollout（subprocess 与 docker runtime 各一次），检查 Trace 的 token/mask/logprob 字段 | 一份 Trace dump + 字段核对记录（同时验证"harness 注入本地工具"与"Taskset MCP 工具归属"两种边界） |
| S0-4 | V2 renderer 覆盖 | 对候选模型型号（E5）核实 renderers 是否有 hand-coded renderer、bridge_to_next_turn 是否可用 | V2 结论（决定 token 保真上限与模型短名单） |
| S0-5 | V3 协议 shim 试验 | 起真实推理端点（需 GPU，E4）：先用 vLLM 原生端点直连 TrainClient 走通全链；再对 SGLang 写最小 shim 原型验证 token ids / logprobs 无损透传 | V3 结论 + shim 原型代码 |
| S0-6 | V4 MoE 张量穿透 | 形态 B：静态核实 slime custom_generate 契约下 routing/top-p tape 完整（已源码确认，补动态最小验证）；形态 A：核实 vLLM 协议能否携带 routed_experts（top-p ids 已知无槽位） | V4 结论 + **形态 A/B 评估报告**（S0 最重要的单一产出） |
| S0-7 | smoke taskset | 从 SWE-bench Verified 挑 5~10 个简单题（E2），物化 workspace + 跑通评分（允许同容器评分，不要求隔离） | 题目清单 + 每题一次成功 rollout 记录 |
| S0-8 | 实验设计文档 | 与 S0-4/5/6 并行推进；已有另一线程的草案 `docs/agentic_RL/training_design/repoharness_validation_experiment_design.md`（其内部 E1~E10 是实验层决策，与本文 E1~E8 执行层决策是两套编号，勿混）。本步是复核该草案 + 与 S0 实测结果对齐收口 | 实验设计文档定稿（S1 冻结前必须完成） |

**S0 退出条件**：S0-0 文档切换完成 + V1~V4 四份结论 + 形态 A/B 评估报告 + smoke taskset 跑通 + 实验设计文档定稿。任何 V 项失败都有预案（V1 失败→切方案 B 剥离；V3 失败→形态 B；V4 形态 A 失败→形态 B 定案）。

**S0 的本地/远端边界（重要）**：本机是 macOS，只能做 S0-0（文档）、S0-2（契约测试，不需真实模型）、部分 S0-3（subprocess runtime 玩具闭环）。S0-1 的 Docker runtime、S0-3 的 docker 分支、S0-5/6（真实推理端点、协议 shim、MoE 张量穿透）、S0-7（SWE 镜像物化评分）都需要在租用的 8×RTX Pro 6000 整机上做。因此 S0 启动顺序：先在本机推进 S0-0 / S0-2 / S0-3(subprocess)，GPU 机就绪后再做其余。

---

## 4. S1 详细计划：端到端最小闭环

S1 开始是正式建设，全部代码进 `src/repoharness2/`，每个任务有单测。

| # | 任务 | 内容 | 验收 |
| --- | --- | --- | --- |
| S1-1 | contracts 先行 | `contracts/` 全部 schema 落地：**trajectory（中立投影，最优先）** / eligibility / grading / findings / **anti_hack（AntiHackEvent 等，即使 S2 才接真实 filter）** / handshake / timing，含字段白名单与 forbidden marker 常量（继承 L4/L5 语义） | schema 单测 + 一个最小 inspector 命令能校验样例 artifact |
| S1-2 | SWE taskset 冻结 | 20~50 题 SWE-bench Verified 子集：物化 recipe、per-task 镜像、digest 冻结；训练/评测集不重叠划分（按实验设计文档） | taskset manifest + digest + 每题 smoke 通过 |
| S1-3 | SWEGradingManager 最小版 | 同生命周期评分（Taskset.score 内委托 manager）、独立 grading runtime（经 Runtime 契约创建）、clean checkout + patch replay、P1~P11 逐条对照落成测试或显式豁免记录 | P1~P11 对照表（每条：已实现/测试路径/豁免理由） |
| S1-4 | 治理最小闭环 | EligibilityReport sidecar + Gate（wrapper 关口）+ 投影扫描；S1 阶段所有轨迹默认 `offline_or_sft_candidate` 或更低（加固未完成，fail closed） | gate 单测：默认降级、字段白名单拒未知、双拓扑都过关口 |
| S1-5 | 投影 + 离线导出 adapter | verifiers Trace → `TrajectoryProjection`（中立契约，S1-1）→ 过滤 → 离线样本（对接 warm_start_offline_data_filtering_design.md 的 OfflineFilterReport）。离线导出消费中立投影，不直接碰 Trace.branches | project_from_verifiers 单测 + 一批真实 rollout 导出的样本包 + 检验脚本 |
| S1-6 | 埋点与归因 | 五类计时埋点 + grading_failure_category 三分，写入 artifact | 一次批量 rollout 的埋点报表（验证 M3 假设：冷启动 vs test run 占比） |
| S1-7 | 在线后端 adapter | 按 S0 定的形态接 slime，跑通"环境 → rollout → slime Sample/训练步" | 一次最小训练 step 完成（不要求收敛，只要求数据链路正确） |
| S1-8 | parity 对照（按形态拆开） | **形态 A**（都从 verifiers Trace 出发）：token ids / loss mask / reward facts 逐位一致。**形态 B**（slime 原生路径）：治理事实 / reward facts / eligibility / logprob_source / routing 与 sampling provenance 一致；token 逐位一致仅在同 renderer/tokenizer 路径时作为强验收（slime 原生的 tokenization / renderer / compaction 边界不一定与离线导出同源） | parity 脚本 + 报告（简历亮点 4.2 的证据；S1 只接一个形态，另一形态的 parity 判据先写进验收标准待形态启用时执行） |

**S1 退出条件**：S1-1~S1-8 全部验收 + 一份 S1 acceptance summary + inspector。此时闭环存在但训练信号未加固，正式训练闸门保持关闭。

---

## 5. S2~S5 概要（细化推迟到 S1 复盘后）

```text
S2 安全加固（把闭环变可信）
   SWE-SEE Runtime（断网/非root/seccomp/资源限制/事件日志）
   anti-cheat 全套：git 清洗、在线拦截（block+dummy+继续、attempted/executed
   区分）、test reset、谎报成功规则版（claim_check 读事件日志）
   红队环境包：5 类作弊注入 fixture，逐条演示治理层拦截（D4）
   → 退出判据：红队环境包全部被正确拦截/降级，gate 开始发放
     online_policy_loss_eligible

S3 治理完备 + 生产线最小版收尾
   三档分级全量语义、审计报表、组修复信号握手（条件化）
   环境验证四门全落地：empty/golden、F2P>0∧P2F=0、假阳性解、非功能 verifier
   → 退出判据：新闸门体系（E6）达到"正式训练允许"状态

S4 正式训练实验 + 生产线深化
   按实验设计文档执行 before/after 训练实验（简历叙事收尾）
   backlog B1~B7 按 S1/S2 实测数据拉取
   白盒 harness（结构化工具 + 权限 + 确定性用户模拟）视余力

S5 第二后端 + 服务化（按需）
   verl adapter；EnvServer 服务化（heartbeat、PD 分离、多任务采样比、
   镜像缓存二档、独立评分池、完整确定性重放）
```

注意一个刻意的顺序调整：设计文档 §10 把"环境生产线深化 + 白盒 harness"放 S4、训练实验隐含在后。本计划把**正式训练实验提前为 S4 的主体**——因为简历项目的核心证据是"训练跑通且设施有效"，白盒 harness 和生产线深化都可以在实验之后继续。此调整需确认（E7）。

---

## 6. 验收与证据体系（对应决策 E6）

```text
1. 每阶段产出：<stage>_acceptance_summary.json（含 source_digests、
   闸门字段）+ implementation-notes.md（设计决策/偏离/权衡/开放问题）
2. inspector：每阶段一个 CLI 子命令（inspect-rh2-s0 / inspect-rh2-s1 ...），
   遵循四步范式：重算 source digest → 重构关键 report 对照 → 字段白名单
   严格枚举 → forbidden marker 扫描 fail closed
3. 新闸门字段（替代旧 17B/20/21）：
   rh2_s0_complete → rh2_s1_closed_loop → rh2_s2_signal_trusted
   → rh2_formal_training_allowed（≈旧 stage21 语义）
4. evidence 目录（E6 已定）：docs/agentic_RL/repo_harness_rh2_workstreams/<stage>/
   （延续 repo_harness_verl_workstreams evidence 区惯例，与 harness_improve 设计区区分）
```

---

## 7. 风险与回退

| 风险 | 预案 |
| --- | --- |
| prime-sandboxes 在部署环境不可用（V1 失败） | 切方案 B：fork 固定 commit、剥离 prime 依赖（设计文档 §6 已预留） |
| GPU 资源不足以支撑 S0-5/6 与 S4 训练 | V3 可先用小 dense 模型验证协议正确性；V4 形态 B 静态核实先行、动态验证后置；训练实验规模按 E4 算力定 |
| SWE-bench per-task 镜像构建成本超预期 | S0-7 从官方预构建镜像可覆盖的题目里挑；构建失败题直接换题（S0 阶段题目可换，S1 冻结后不可换） |
| verifiers 上游升级破坏子类 | 钉 commit + S0-2 契约测试守门；升级动作本身作为独立任务走契约测试 |
| 评分吞吐拖垮闭环（Nemotron 教训） | S1-6 埋点先行；P11 反压兜底；prewarm/服务化由数据触发 |
| 范围蔓延（生产线深度项诱惑大） | backlog B1~B7 铁律：没有实测数据支持不拉取 |

---

## 8. 本阶段待讨论决策（E 系列）

| # | 决策 | 推荐 | 需要你输入的点 |
| --- | --- | --- | --- |
| E1 | 新包名与布局 | `src/repoharness2/`，布局按第 2 章 | 包名是否有偏好（`repoharness2` / `rh2` / 其他） |
| E2 | smoke 任务来源 | SWE-bench Verified 里官方预构建镜像可用的简单题 5~10 个 + 保留 1 个玩具任务做回归 | 无异议即定 |
| E3 | verifiers pin | **已定：pin `5885ab9c`**（本地已快进；含 config-level judges、`bash`/`bash_edit`→`default`/`null` 合并、`Taskset.setup` 加 trace 参数）。契约测试范围按 S0-2 四项，以此 commit 为准 | 已定 |
| E4 | 算力形态 | **已定：租用 8 × RTX Pro 6000 Blackwell 整机**（整机而非 docker 实例，保证 Docker 可用）；LLM judge 额度充足；codex / claude code agent 额度充足。风险见下方"算力风险"一段 | 已定 |
| E5 | 训练模型型号 | **暂定 Qwen3-30B-A3B**（MoE，符合 D3）。稳定训练与训推显存是否够用留 S0-5/6 + S4 实验验证；不达标的回退候选见下方 | 暂定，S0 验证 |
| E6 | evidence 目录与闸门命名 | **改为 `docs/agentic_RL/repo_harness_rh2_workstreams/<stage>/`**（延续项目 `repo_harness_verl_workstreams` 的 evidence 区惯例，与 `harness_improve` 设计区区分）+ 第 6 章闸门字段 | 已定 |
| E7 | S4 顺序调整 | 正式训练实验提前为 S4 主体，白盒 harness/生产线深化让位（第 5 章说明） | 确认或否决 |
| E8 | S0 时间盒 | 1~2 周；到期未完成项显式降级为"带风险进 S1"或砍掉 | 无异议即定 |

**算力风险（RTX Pro 6000 Blackwell 专项，S0 必须实测）**：这是工作站/服务器卡（96GB GDDR7，支持 FP8），但**卡间互联是 PCIe Gen5、无 NVLink**——相比 8×H100 SXM，Megatron 的张量并行通信和 RL 每步 actor→rollout 权重广播（30B bf16 权重约 60GB）会显著更慢。这是本配置最大的不确定性。Qwen3-30B-A3B 训推显存估算：full-FT 模型状态（bf16 权重 60G + fp32 master 60G + Adam 240G + 梯度 60G ≈ 420G）分 8 卡约 52G/卡，加激活与 rollout 侧 SGLang KV，单卡 96G 理论够但余量不大；训推共卡（colocate + sleep 切换）还是训推分离要在 S0-5/6 定。回退候选：显存/通信不达标时降到更小 MoE 或更激进并行（TP+offload），最坏情形用 LoRA 验证链路正确性再议 full-FT。

**E4/E5 已提供，实验设计文档初稿（S0-8）的输入已齐**；E7 待你确认；其余按推荐执行。注意本文 E 编号（执行层）与实验设计文档的 E 编号（实验层）是两套独立体系。

---

## 9. 定稿流程

1. 本文 E1~E8 讨论定案（E3/E4/E6 已定，E5 暂定待 S0 验证，E7 待确认，E1/E2/E8 无异议即定）→ 更新本文去掉"草案"标注。
2. S0 启动，第一个动作是 S0-0 的 AGENTS.md / README 改写（让任何接手线程看到新事实，不再被旧 16G 状态误导）。
3. 本机可立即推进 S0-0 / S0-2 / S0-3(subprocess)；GPU 整机就绪后做 S0-1(docker) / S0-5/6/7。
4. S0 结束出四份 V 结论 + 形态评估报告 → 回写设计文档 2 的对应开放项 → S1 细节按需微调后执行。
