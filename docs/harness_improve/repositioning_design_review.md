# RepoHarness 重定位与目标架构设计审核报告

本报告是对 `docs/harness_improve/repo_harness_repositioning_after_polar.md`（下文简称"重定位文档"）的独立架构审核。审核问题只有一个：**这份高层次定位与目标架构设计，是否存在架构冗余、设计不当、或与当前模型训练实践不符的地方。**

审核明确不涉及执行层面：重定位文档的里程碑只是方向示意，后续执行计划会按已完成阶段、现有测试、acceptance gate 和最小可验证增量另行重排、拆分或合并，本报告不对执行顺序提意见（个别与执行相关的观察统一放在第 7 章备注，不构成审核结论）。

审核依据：

1. 三份原始 PDF 定向精读——Polar 论文（arXiv 2605.24220，17 页全文）；MAI-Thinking-1 技术报告（§3.3 Agentic Climb、§3.6 RL Infrastructure、附录 D/F）；Nemotron-3 Ultra 技术报告（§3.2 RLVR、§3.3 MOPD 与 SWE teacher、§3.3.5 Limitations、§3.6.2 Scaling RL Infrastructure）。精读同时核对了此前各建议文档的转述是否失真。
2. 七个外部参考仓库的导览与关键源码抽查（核实了 `verifiers/v1/env.py` 的 `EnvConfig`、`polar/trajectory/models.py` 的 `Trace`、`verl/experimental/agent_loop/agent_loop.py` 的 `AgentLoopOutput`）。
3. 对 `src/repo_harness` 关键模块的轻量核对（`rl/training_view.py`、`rl/gateway.py`、`rl/visibility.py`、`rl/episode.py`、`evaluation/episode_projection.py`、`stage16g_tool_profile.py`），用于判断新契约与已验证资产的关系。

---

## 1. 总体结论

**定位和架构主方向成立，不需要推翻。** "Prime-style 可组合环境 + Polar-style rollout 服务与 model 边界捕获 + renderers-style token fidelity + 训练框架解耦 adapter"这个组合，与三份一线报告披露的实践方向一致；§16 的硬边界（训练资格三档、token provenance 一等字段、reward attribution 硬规则、fail closed 取向）经原文核对全部站得住。此前建议文档对 Polar / MAI 的关键转述**核实无误**（核对明细见 §2.2）。

在架构层面，审核发现三类问题，共 13 条：

- **架构冗余 4 条（R1~R4）**：同一规格对象在解析结果中三重包含、同一事实在三个层级重复存储且无权威来源声明、CompletionRecord 把三种捕获体制折叠成一个约 35 字段的全能对象、EnvConfig 与 ComposableEnvSpec 职责重合。
- **设计不当与内部不一致 5 条（D1~D5）**：主架构图只描述了 service_driven 一种拓扑而文档自认的近期主模式是 trainer_native、§16.2 宣布的独立安全平面没有进入主图、用户模拟与权限在执行平面没有落点、白盒路径缺少 token tape 构造者（renderer）组件归属、训练资格被三个平面共同拥有而无最终合成者。
- **与当前训练实践不符 4 条（T1~T4）**：环境质量验证不变量（空 patch 必失败、golden patch 必成功、确定性过滤、reward profiling）缺失——这是对照 MAI 与 Nemotron 实践后最重要的一条；reward 归一化的归属越过了训练框架边界；TrainTrace 契约没有为 MoE routing replay、teacher logprobs、多模态这类当前实践已经需要的张量留扩展点；评分环境 prewarm 未被列为一等机制。

这 13 条都不动摇主方向，全部可以通过修订契约和平面定义解决。其中 **D1（双拓扑）、T1（环境验证不变量）、R3（CompletionRecord 拆分）** 三条建议优先处理，因为它们直接决定后续所有数据契约的形态。

---

## 2. 审核方法与转述忠实度

### 2.1 材料覆盖

- 重定位文档全文（2182 行，含 §16 前两轮复核补充）。
- `docs/harness_improve/` 下全部建议与分析文档（external_reference_code_analysis、full_pull_advice、polar_advice、bash_tool_advice、env_design、harness_env_design、harness_design_advice、codex_vs_claude_code、16G-3_advice、16G-3_plan_V1）。
- 三份原始 PDF（定向精读，范围见开头）；七个参考仓库导览 + 三处源码抽查；六个本项目源码模块。

### 2.2 转述忠实度核对结果

逐条核对后，建议文档对原始材料的关键转述**基本忠实，未发现实质性失真**：

| 核对项 | 原始出处 | 结论 |
| --- | --- | --- |
| Polar `Trace` 字段（prompt_ids / response_ids / loss_mask / response_logprobs / messages / tools / finish_reason / reward / metadata） | Polar §3.4 + 附录 A.4 + 源码 | 一致 |
| per_request + outcome reward 广播导致显著 reward hacking（noisy credit assignment） | Polar §4.1 原文 | 一致 |
| prefix merging 数字（1185→218 条更新、189.5→35.2 分钟、5.39×、rollout GPU 利用率 87.7% vs 20.4%） | Polar §4.1 | 一致 |
| 四 harness SWE-Bench Verified 增益（+22.6 / +4.8 / +0.6 / +6.2） | Polar Table 1 | 一致 |
| MAI 工具面 = bash + str_replace_editor；bash schema 为 `command: string` 全功能 shell，无命令白名单 | MAI §3.3.1 + 附录 D Figure 23/24 | 一致 |
| MAI 三类 reward hacking 与防线（网络隔离+缓存代理、time-traveled repo、grading 前 reset tests + hidden test changes 仅评分时 apply、LLM monitor） | MAI §3.3.1 | 一致 |
| MAI SEE：每任务 fresh container、用毕销毁、默认断网 | MAI §3.3 | 一致 |

一个归属修正：配套分析文档把 Polar gateway lifecycle 写成四阶段 `INIT -> READY -> RUNNING -> POSTRUN`；论文正文（§3.3.1）的精确表述是 INIT / RUNNING / POSTRUN 三类 worker pool 加一个**有界 READY 缓冲**，READY 不是独立 worker pool。重定位文档本身只引用了基本流程，未受影响。

### 2.3 精读新增的关键事实（建议文档未覆盖）

1. **Polar 的全部 RL 实验只用 prefix_merging**（§4.1 与 Table 4）；per_request + 广播只在 ablation 中尝试并因 reward hacking 被放弃。Table 4 还显示 TIS（截断重要性采样）默认开启——印证 response_logprobs 的实际用途是训推数值差校正。
2. Polar 附录 A.3 的代表性 payload 使用 `"network": "host"`——"Polar 安全模型不能照搬"有原文依据。
3. **MAI 的 harness 自己维持严格前缀不变量**（§3.3："All the previous steps' tokens are preserved in context and they are strict prefixes for the next steps"），credit assignment 在单条轨迹所有 policy-step token 上统一施加。白盒一等 agent loop 中 token tape 天然 append-only，不需要事后重建。
4. **MAI 的环境流水线产出率**：102M PR → 4.87M（带 issue 链接）→ 2.08M（42.8% 构建成功）→ 745,452（15.3% 提取出评分信号）→ 265,617（5.5% 通过环境与 grader 验证），横跨 94,044 个仓库；环境构建基础设施约 3 万 CPU 核（附录 F）。
5. **MAI 的环境验证不变量**：空 code patch 必须让 grader 失败、golden patch 必须通过，各自跨多次运行验证；过滤跨重复执行表现非确定的环境。MAI 评分在**同一容器内**执行（reset tests 后），不是独立评分环境。
6. **Nemotron §3.2 为多 harness 训练提供一手佐证**："we construct training data using a diverse collection of harness implementations and interaction formats … reducing overfitting to any particular harness design"；并且"perform reward profiling prior to training"。
7. **Nemotron §3.3.5 的长程混合训练困境**：端到端 agentic 环境与单轮 reasoning 混训时 rollout 时长方差导致严重低效，实践中多数 agentic 任务退化为单轮 rollout（PivotRL 风格）。
8. **Nemotron SWE teacher 的做法**：屏蔽未完成轨迹（超 turn / 超时）的 loss；对 malformed reasoning / tool call 的 token 施加**负优势**（token 级 process penalty）；防泄漏双通道——物理删除 base commit 之后的 git 对象（低层恢复命令也无法找回）+ 运行时命令过滤器拦截 remote git 与 GitHub web/raw/Pages 下载。
9. **Nemotron §3.6.2 故障归因**：RL 软件故障 56% 来自生成引擎失败/超时、36% 来自 sandbox / tool calling，合计约 92%。
10. **Nemotron 训练需要 MoE routing replay 与 top-p mask replay**（§3.6 引述其训练稳定性做法）；MOPD 需要 teacher logprobs 逐 token 进入训练数据流。这两点在 T3 中使用。

### 2.4 材料缺失说明

审核输入清单引用的 `reference/mini-swe-agent/AGENTS.md` 实际不存在（该目录只有 README、docs、src、tests）。重定位文档 §3.5 对 mini-swe-agent 的描述与其余材料转述一致，未发现矛盾，但这部分没有经过本地导览交叉验证。建议补一份导览或修正引用清单。

---

## 3. 与训练实践相符、应保持不动的设计

以下设计经原文核对确认正确，后续实施不应弱化：

1. **Ownership hard contract（§6.2）**："定义任务成功条件的归 TaskSet/Rubric，定义 agent 如何行动的归 Harness，Env 只组合"——与 verifiers v1 的代码纪律一致（`EnvConfig` 在 `__pydantic_init_subclass__` 中主动拒绝任何 root 级额外字段，源码核实）。
2. **训练资格三档分级（§16.1）**：与 Polar 实践（per_request 不进 online RL、SFT 走 binary verifier 过滤）和现有 `rl/visibility.py` 的 `OFFLINE_PROVIDER_ALLOWED_USES` 天然衔接。
3. **Token provenance 一等字段化（§16.3）与 prefix merging 硬边界（§16.10）**：是 Polar 正确性不变量（"Every trainable token matches the behavior policy during rollout, and any non-generated tokens are masked out"）的可审计展开；MAI 的严格前缀做法（§2.3 第 3 条）从白盒侧印证。
4. **Reward attribution 硬规则（§16.11）**：精确对应 Polar 观察到的失败模式和 Polar 自己的实际做法（只用 prefix_merging）；Nemotron 对 malformed tool call token 的负优势做法支持"process reward 须有明确 token attribution"一条。
5. **`backend_receive_mechanism` 抽象（§6.8 / §11.9）**：从 verl（MessageQueue）与 slime（Ray future + data buffer）的真实差异得出，正确。
6. **Model proxy 局限的如实承认（§16.4）**：与 Polar 只在 SGLang/vLLM 可控后端验证、streaming 走"非流式上游 + 合成 SSE"的事实一致。
7. **干净评分语义与可配置的 `patch_replay_policy`（§8.4 / §16.8）**：方向正确（成本问题见 T4）。
8. **多 harness 训练目标（§4.2）**：除 Polar 四 harness 实验外，新增 Nemotron §3.2 一手佐证（§2.3 第 6 条），研究价值是实的。
9. **logprob 缺失即不进 formal online RL（§16.1 第 2 条）**：与三个训练框架的实践一致——logprobs 服务于训推数值差校正（Polar TIS、verl rollout correction、slime rollout_log_probs），缺失时重要性采样无法成立。

---

## 4. 架构层问题

### 4.1 架构冗余

#### R1 `ResolvedRolloutTaskRequest` 对同一规格的三重包含（§8.2）

解析后的请求对象同时持有：

```text
env_config: EnvConfig          # 内含 harness: HarnessConfig、rubric: RubricConfig、scoring: ScoringConfig
env: ComposableEnvSpec         # 组合清单，同样组合了 harness / rubric
harness: HarnessSpec           # 顶层又一份
evaluator: EvaluatorSpec       # 与 env_config.rubric / env_config.scoring 平行
```

同一个 harness 规格可以从三条路径取到，evaluator 与 rubric/scoring 配置平行存在。文档在 §8.2 的文字部分已经意识到"互相抢 ownership"的风险并提出 registry 解析方案，但 schema 本身保留了冗余。这正是它自己想避免的问题：实施时必然出现"哪份拷贝是权威"的分歧，inspector 也要为三份拷贝写一致性互检——把本可以靠结构消除的错误变成靠校验兜底。

建议：解析结果只保留一棵树（`env: ComposableEnvSpec`，其内部引用 `EnvConfig` 的各 section digest），顶层不再平铺 `harness` / `evaluator`；需要快速访问时提供只读访问器而不是字段拷贝。

#### R2 同一事实在三个层级重复存储，缺单一权威来源声明

例子（按 §8.5 ~ §8.8 草案）：

```text
staleness：TrainingRuntimeRecord.staleness_status
           + TrajectoryArtifact.policy_staleness_class（§16.3 补充）
           + CompletionRecord.behavior_policy_version / weight_version_seen_by_engine

训练资格：TrainTrace.training_eligibility_class
           + TrajectoryArtifact.training_eligibility（dict）
           + TrainingRuntimeRecord.consumed_by_policy_loss

reward：   TrainTrace.reward / reward_components
           + TrajectoryArtifact.score_report_ref
```

每一层各有读取场景，冗余本身不一定错；问题是文档没有声明**派生方向**——哪一层是原始事实、哪一层是聚合视图、不一致时以谁为准。现有代码里这个问题已经有解法可参考：`episode_projection.py` 的 `policy_loss_candidate` 在 manifest / route_report / status_report 三处出现，但有五处互检逻辑明确"任何一处不一致即 fail"。新契约应当把"原始事实层 + 派生视图层 + 互检规则"写成约定，而不是默认三份独立维护。

#### R3 `CompletionRecord` 是三种捕获体制折叠成的全能对象（§8.5 + §16.3）

合并 §8.5 与 §16.3 的补充后，`CompletionRecord` 约有 35 个字段，实际服务三种互斥的 provenance 体制：

```text
native capture：  prompt_ids_seen_by_backend、sampled_response_ids、behavior_policy_version、
                  weight_version_seen_by_engine
proxy capture：   provider_api、model_requested/model_used、raw_request_ref/raw_response_ref、
                  request/response transform 类诊断
renderer bridge： renderer_name/version/config_digest、message_indices、sampled_mask、is_content、
                  bridge_status、bridge_source/target_completion_id、prefix_preservation_check
```

任何一条真实记录里，三组字段总有两组为 null。这种 omnibus 设计的代价是：每个消费者（builder、inspector、eligibility 判定）都要处理全部可空组合，schema 校验无法表达"native capture 模式下 sampled_response_ids 必填"这类条件约束。

建议：以 `tokenization_source` 作为判别字段，把 `CompletionRecord` 拆成**薄核心**（session/completion id、时间戳、prompt_ids、response_ids、logprobs、finish_reason、policy version）加三个按体制的扩展段（discriminated union），每个体制的必填约束在各自扩展段上表达。这也与现有 `GenerationRecord`（本质就是 native capture 的薄核心）平滑衔接。

#### R4 `EnvConfig` 与 `ComposableEnvSpec` 职责重合（§6.2 / §8.1）

两者都声称表达"环境由什么组成"：`EnvConfig` 是七个 namespace 的可校验配置树，`ComposableEnvSpec` 是"组合出一个可执行环境"的清单，§8.1 只说后者"可以引用"前者。组合关系（谁持有谁、谁派生谁、digest 记在谁身上）没有定义。参考 verifiers 的做法可以收敛：config（声明，可序列化、可 diff）与 instance（由 loader 从 config 构造的运行对象）是两层，名字应该体现这层关系（例如 `EnvConfig` → `load_environment()` → 运行期 env 对象），而不是两个看起来都像"声明"的平行物。

### 4.2 设计不当与内部不一致

#### D1 主架构是单拓扑的，但文档自认的近期主模式是另一种拓扑（§5 vs §6.7/§6.8）

§5 的两张主图描述的数据流是 service_driven 拓扑：Control → Composition → Runtime → Capture → Trajectory → Verification → Training Interface → 训练框架。但 §6.7 明确说近期现实优先级是 trainer_native——在这种拓扑里：

- 训练框架（verl `FullyAsyncRollouter`）拥有外层循环，**调用进** RepoHarness，不存在 RolloutServer/Gateway 环节；
- Capture Plane 的形态是 agent loop 内的逐轮记录（现有 `GenerationRecord` 即此物），不是 proxy；
- Trajectory Plane 的 builder（PerRequest / PrefixMerging）不出现——builder 本质是为黑盒 proxy 路径发明的**事后重建**机制（Polar 的处境：看不见 harness 内部，只能从 completion 序列重建链条）。白盒 loop 自己维持 append-only token tape（MAI 的严格前缀做法，§2.3 第 3 条），需要的是逐轮记录与校验，而非重建；
- Training Interface 不是"打包器"，而是 AgentLoop 适配器，verl 消费的对象是 `AgentLoopOutput`。

文档目前用 §6.8"横切补充层"来容纳 trainer_native，等于把主模式当成了主架构的补丁。更准确的架构表述是：**两种拓扑共享同一个核心（环境组合 + 运行时 + 验证 + artifact/资格契约），服务平面（RolloutServer、Gateway、ModelProxy、TrajectoryBuilder）只是 service_driven 拓扑的组件**。这不是改方向，是把图画对——否则后续实施会试图在 trainer_native 路径上强行穿过为 service_driven 设计的平面。

与此直接相关的数据契约问题：当前存在三套字段高度重叠的 token 契约且无映射定义——verl `AgentLoopOutput`（prompt_ids/response_ids/response_mask/response_logprobs/reward_score/num_turns/extra_fields，源码核实）、现有 `TrainingView`（与前者逐字段对齐，本就是 trainer_native 投影）、新 `TrainTrace`（改用 Polar 的 `loss_mask` 命名并扩字段）。§6.5 给出的派生式 `loss_mask = sampled_mask AND role_policy AND training_eligibility_policy` 是好的，但必须声明它落在现有 `response_mask + ResponseSpan.source_type` 机制上的方式，并给出三者的字段映射，否则就是三套账本。

#### D2 §16.2 宣布的独立安全平面没有进入主架构图

§16.2 明确写"新架构应该把 artifact 和 visibility 作为独立安全平面"，并定义了五类可见性边界和六条检查。但 §5 的两张 mermaid 主图都没有这个平面。这是文档内部不一致：按 §16.2 的自我要求，Artifact And Visibility Safety Plane 应作为横切平面出现在主图中（与所有产出 artifact 的平面相交），其检查点（公开投影扫描、opaque ref、hidden verifier 不挂载、clean replay、manifest、inspector）应标注在对应边上。

顺带指出一个相关的继承问题：这一平面在现有代码中已有完整实现可作种子——`rl/visibility.py` 的 `FORBIDDEN_FIELD_MARKERS`（L4）、`episode_projection.py` 的公开扫描（L5）、`rl/episode.py` 的 `EpisodeVisibilityPolicy`（model_visible / trainer_tensor / trainer_non_tensor_filter / audit_only / forbidden 五类字段分层，与 §16.2 的五类几乎同构）。文档通篇没有声明这些是新平面的继承基础。若实施时平行重写而不是扩展改名，已验证的防线反而会倒退。

#### D3 用户模拟与权限是一等规格对象，但在执行平面没有落点

三处不一致拼在一起构成这个问题：

1. §3.1 的 ownership 表把"用户模拟"列在 TaskSet 名下；§8.1 又把 `UserSimConfig` 提升为与 taskset 平级的 root namespace。哪些属于任务数据（每题不同的 persona、隐藏约束）、哪些属于可复用引擎（审批策略执行器），没有切开。
2. §6.3 Runtime / Execution Plane 的对象清单（EnvironmentRuntime、SandboxInstance、HarnessRunner、PrepareRecipe……ExecutionEventLog）里**没有任何 user-sim 执行者和权限拦截器**。对照 verifiers：`User.get_response(task, state, messages)` 由 rollout 循环在模型回合之间调用——"谁在什么时机调用用户"是执行平面的结构性问题，不是配置细节。权限同理：§6.2 说 PermissionSpec 拥有"工具调用前的权限拦截"，但拦截器（PermissionGate）在工具执行链路中的位置没有出现在任何平面对象里。
3. 训练运行时的绑定缺失：若用户模拟由 LLM 驱动，GRPO 风格训练（Polar/Nemotron 均为每题 16 rollouts）会把用户模型调用量放大一个数量级——这个模型挂在哪里（冻结模型同推理池：slime `sglang-config` 的 `update_weights: false` 是现成机制；独立 endpoint；或确定性规则引擎）、是否确定（不确定的用户行为会给同 group 的 advantage 比较注入噪声）、其 token 的 mask 归类（现有 `ResponseSpan` 三类 included span 中没有 `user_message`，只能挂在 `environment_observation` 下），都是架构决策。值得注意的对照：MAI 的 tool-use 环境用 **mocked 确定性后端** + LLM judge 评分，而不是 LLM-in-the-loop 的逐回合用户——一线实践在训练循环内倾向确定性环境组件。

建议：在 Composition 层把 UserSim 拆成"任务侧事实（persona、隐藏约束，归 TaskSet）+ 可复用行为引擎（审批策略执行器，root spec）"；在 Runtime 层补 `UserSimRunner` 与 `PermissionGate` 两个对象及其在 agent loop 中的调用时机；声明训练期默认档位（建议第一版 deterministic policy）和 user token 的 span 类型。

#### D4 白盒路径缺少"token tape 构造者"（renderer / chat template）的组件归属

`CompletionRecord` 草案带有 `renderer_name / renderer_config_digest / chat_template_digest / bridge_status` 等字段，但全部七个平面的对象清单中，**没有任何组件负责 chat template 渲染和多轮 token tape 续接**。这在 proxy 路径下说得通（token 由外部 harness + 推理后端产生，RepoHarness 只记录）；但在 trainer_native 白盒路径下，工具结果如何 tokenize、下一轮 prompt 如何在不重渲染历史的前提下续接（renderers 仓库 `bridge_to_next_turn` 解决的正是这个问题），是决定 token fidelity 的**真正部件**——字段记录的是结果，构造行为本身却无人拥有。建议在 Harness 层（或 Capture 层）显式命名这个组件（例如 `TokenTapeBuilder` 或 `RendererBinding`），声明它的两种实现（依赖推理后端 token-in/token-out；或本地 renderer），并把 §16.10 的 prefix preservation 检查挂在它身上。

#### D5 训练资格判定被三个平面共同拥有，缺最终合成者

按文档：Verification / Reward Plane 拥有"training eligibility 判定"（§6.2 ownership），Trajectory Plane 负责 token provenance 资格（§6.5），Training Runtime Coordination 负责 staleness 资格（§6.8 职责 4）。三个平面各管一个维度是合理的（事实产生在哪里就在哪里记录），但**最终的 `training_eligibility_class` 由谁合成、在哪个对象上落账**没有定义。§16.11 要求 `credit_assignment_strategy`、`reward_scope`、`reward_event_refs`、`reward_components`、`training_eligibility_class` 必须一起通过 inspector 校验——这隐含了一个合成点的存在，但架构里没有这个角色。建议显式声明：资格是各平面贡献的合取（security AND provenance AND reward_scope AND staleness），由 Training Interface 的单一 eligibility gate 合成并落在 TrainTrace 上，各平面只产出自己维度的事实，不得直接写最终分级。

### 4.3 与当前训练实践不符

#### T1 环境质量验证不变量缺失（最重要的一条）

`EnvironmentPackageSpec`（§8.1）只有 `smoke_test_command`；§16.8 的九问也没有覆盖环境有效性验证。对照两份一线报告的实际流程：

```text
MAI（§3.3.1 Environment and grader verification）：
  空 code patch 必须让 grader 失败；golden patch 必须通过；各自跨多次运行；
  在与训练相同的 SEE 基础设施内重新验证（防构建沙箱与训练沙箱的环境差异）；
  过滤跨重复执行非确定的环境（减少 reward 噪声）。
  这一步把 74.5 万候选筛到 26.6 万（产出率从 15.3% 落到 5.5%）。

Nemotron（§3.2）：
  "perform reward profiling prior to training"——训练前对 reward 信号做画像。
```

这不是流水线细节，而是环境作为训练数据的**质量门槛**：一个 golden patch 都过不了的环境产生的全是假负样本，一个空 patch 也能通过的环境产生的全是假正样本，非确定环境直接污染 GRPO 的组内比较。重定位文档把大量篇幅给了轨迹侧的训练资格（§16.1），但环境侧的"这个环境本身是否配产生训练信号"完全缺位。

建议在 `EnvironmentPackageSpec` / `TaskPackSpec` 增加验证不变量字段，例如：

```text
empty_patch_must_fail: passed | failed | not_run
golden_patch_must_pass: passed | failed | not_run
determinism_check: passed | failed | not_run        # 同一输入重复 N 次结果一致
verified_in_training_runtime: bool                   # 在训练同款 runtime 内复验
reward_profile_ref: str | None                       # 训练前 reward 画像
```

并把"验证不通过的环境不得进入训练采样池"写成与 §16.1 平行的环境级 fail-closed 规则。

#### T2 reward 归一化的归属越过了训练框架边界（§6.7）

§6.7 把"做 reward normalization"列为 Training Interface 职责并设 `RewardNormalizer` 对象。对照三个训练框架的实际分工：

```text
verl： advantage / GRPO 组归一化在 trainer driver 端计算（core_algos.py）
slime：reward post-process 在 RolloutManager（训练框架内部），advantage 在 Megatron actor
Polar：reward post-process 在 slime_bridge（训练桥接侧），且只在收到完整 group、
       把失败轨迹 advantage 置零之后做
```

组归一化在数学上依赖 group 完整性（同题 16 个 rollout 哪些成功、哪些 abort/超时），而 group 的生命周期（partial rollout、staleness 丢弃、buffer 回填）由训练框架管理。环境服务在看不到最终 group 成员的位置做归一化，要么算错，要么和训练侧重复归一化。文档 §11.8 自己写了"RepoHarness 不应自己重写训练框架已有的机制"，`RewardNormalizer` 与这条防线冲突。

建议：RepoHarness 核心输出 raw reward + reward_components + group_id / parent_rollout_id（已有），归一化职责显式划给训练后端；adapter 层最多在 service_driven 离线导出场景做可选归一化，且必须以"group 完整性已确认"为前置条件。

#### T3 TrainTrace 契约是纯文本 RL 形态，缺少当前实践已需要的张量扩展点

对照三个训练栈的样本契约：

```text
verl AgentLoopOutput：  routed_experts、multi_modal_data（源码核实）
slime Sample：          rollout_routed_experts（MoE routing replay）、
                        multimodal_train_inputs、teacher_log_probs（on-policy 蒸馏）
Nemotron 实践：         MoE routing replay 与 top-p mask replay 用于训练稳定性；
                        MOPD 需要 teacher logprobs 逐 token 进入数据流
```

`TrainTrace`（§8.6 + §16.3 补充）没有任何对应槽位。考虑到候选训练模型很可能是 MoE（Qwen3.5 / Nemotron 系），routing replay 不是远期需求；teacher logprobs 则是 warm-start / 蒸馏路线（项目 Stage 20 方向）的硬需求。如果这些将来散落进 `metadata: dict`，§16.3 "关键训练资格信息不得塞进松散 metadata"的原则就会在第一次扩展时破例。

建议：给 `TrainTrace` 增加一个有类型的扩展机制（例如 `backend_tensors: dict[str, TensorRef]`，key 进白名单注册表），把 routed_experts / teacher_log_probs / multimodal 作为首批注册项，校验规则（与 response_ids 对齐等）随注册项声明。

#### T4 评分环境 prewarm 未被列为一等机制（§6.3 / §6.6）

文档默认 SWE 任务走 clean grader checkout + cleaned final patch replay（§16.8：没有 clean grading checkout 则训练资格默认降级）。这个语义本身是对的且比一线更严格——但要注意一线实践的形态和原因：MAI 在**同一容器内**评分（reset tests + hidden tests 仅评分时注入），Polar 支持 fresh eval runtime 但专门做了 **evaluator prewarm**（§3.3.2：agent 还在运行时就开始准备评分 runtime），否则评分环境准备会吃掉吞吐。在每题 16 rollouts 的 RL 设定下，评分环境数量与 rollout 容器同量级；Nemotron 的故障归因（§3.6.2：36% 故障来自 sandbox / tool calling）也说明 sandbox 生命周期是 RL 基础设施的主要故障源之一。

文档的 Runtime Plane 对象清单里有 `RuntimePool` 和 `EvalPrepareRecipe`，但没有"评分环境与 rollout 并行预热"的机制表达。建议在 `SandboxLifecyclePolicy` 或 `ScoringSandboxSpec` 中加入 prewarm 策略字段（例如 `scoring_runtime_prewarm: during_agent_run | on_demand`），并在 §11 风险清单中补一条：长程 rollout 时长方差与评分环境准备成本会共同压垮训练吞吐（Nemotron §3.3.5 因此退化为单轮 rollout 的教训，是这条风险的实证）。

---

## 5. §12 十个验收问题逐条复核

重定位文档 §12 用 10 个问题作为设计成功判据。逐条检查设计草案能否支撑正面回答：

| # | 验收问题 | 复核结论 |
| --- | --- | --- |
| 1 | 同一 SWE TaskSet 能否用 native harness 和 mini-swe-agent baseline 分别跑 | **能**（ownership contract 支持） |
| 2 | 同一 native harness 能否换不同 TaskSet | **能** |
| 3 | 外部 harness 不改工具 loop、只经 proxy 产出 CompletionRecord | **能**，但 token id 可得性依赖推理后端，§16.4 已如实承认——准确表述是"能产出记录，不保证可训练" |
| 4 | 每条进 policy loss 的 trace 能否证明 response_ids 来自真实采样 | **能，且现有代码已实现**：`validate_formal_sample_token_provenance` 已逐 span 比对 `GenerationRecord.output_token_ids` 与 logprobs。新设计应扩展它而不是新建（见 D2 末段） |
| 5 | loss mask 能否区分模型生成 / 工具结果 / 用户 / harness 插入四类 token | **基本能，有一个类型缺口**：现有 `ResponseSpan.source_type` 只有 assistant_generation / tool_observation / environment_observation 三类，用户中途消息只能归入 environment_observation。若用户模拟是一等能力，应增加 `user_message` span 类型（与 D3 关联） |
| 6 | Rubric 能否独立运行、不依赖 harness 自我声明成功 | **能**（§6.6 + §16.9 第 3 条禁令） |
| 7 | 用户模拟和权限能否影响 reward 和训练资格而不只是日志 | **设计上能**（§6.6 + §16.1 第 7 条），但受 D3 影响：执行落点和训练期档位未定，第一版只能在 deterministic policy 档位下正面回答 |
| 8 | trainer 能否只消费 TrajectoryArtifact、不 import 内部 runner | **按拓扑分叉**：service_driven 下能；trainer_native 下 verl 必然调用 RepoHarness 内部 agent loop、消费 AgentLoopOutput。这条验收问题应按两种拓扑分别表述（D1 的另一面），否则 trainer_native 永远"不达标" |
| 9 | artifact 能否追踪 taskset_id / harness_id / rubric_id / policy_version / rollout_step / builder_strategy / verifier 版本 | **能**（§8.7） |
| 10 | provenance 不完整、验证失败、权限违规、过旧时能否 fail closed | **能，且现有代码已部分实现**（`validate_training_view_for_online_rl` 的拒绝原因码体系） |

补充一条本审核建议新增的验收问题（对应 T1）：**一个环境包能否证明"空 patch 必失败、golden patch 必通过、重复执行确定"？** 当前设计回答不了。

---

## 6. 对三份原始材料吸收程度的评价

1. **Polar**：吸收最充分（服务边界、Trace 契约、prefix merging 硬条件、reward 广播风险、trainer bridge 外置全部进入文档）。建议补充引用两点：全部 RL 实验只用 prefix_merging（支撑 per-request builder 的 debug/SFT 定位）；evaluator prewarm 机制（支撑 T4）。
2. **MAI-Thinking-1**：工具面与防作弊吸收充分（经 `bash_tool_advice.md`，转述准确）。尚未吸收的高价值点：环境验证不变量与产出率数据（T1 的直接依据）；harness 自身维持严格前缀（D1 中白盒路径不需要 builder 的论证）；同容器评分 + reset 的吞吐取舍（T4）。
3. **Nemotron-3 Ultra**：此前没有任何文档消化过，本次补上。对架构有直接意义的四点：多 harness 训练佐证（支持 §4.2）；reward profiling（T1）；MoE routing replay 与 MOPD teacher logprobs（T3）；长程混合训练效率困境与 92% 故障归因（T4 与 §6.8 握手字段的必要性佐证）。

---

## 7. 开放问题与执行层备注

以下不构成架构审核结论。

**开放问题**（需项目所有者后续决策）：

1. 与 Stage 16G.3 ~ 16G.6 及 17B / 20 / 21 闸门的衔接（16G.3 的 SEE 等价底座与新架构 Runtime Plane 是同一块工作的两种表述，先后与命名归属待定）。
2. §14 的"现有模块到新架构映射"何时执行；本报告 D2 末段与第 5 章第 4 条提供了部分映射证据。
3. 命名演进决策：`TrainingView`→`TrainTrace`、`GenerationRecord`→`CompletionRecord` 是原地扩展改名（保留 inspector）还是新旧并存过渡。
4. evaluation worktree 在新架构中的接口（`EnvironmentPackage` 的 smoke test / benchmark card 是否就是为评测侧准备的消费面）。
5. user simulator 第一版档位（deterministic / 冻结 LLM / 混合）。

**执行层备注**（按用户说明，里程碑只是方向示意，此处仅记录一项文档内部一致性观察供修订时参考）：§10 的里程碑顺序（M4 rollout service、M5 model proxy 先于 M7 verl trainer-native）与 §6.7"近期第一优先级是 trainer_native"的声明方向相反；若保留里程碑章节，建议至少标注每个 milestone 属于哪条拓扑（对应 D1 的双拓扑表述），执行计划自会按 gate 与最小增量另行裁剪。

---

## 8. 审核结论汇总

| 编号 | 类别 | 问题 | 建议 |
| --- | --- | --- | --- |
| R1 | 冗余 | `ResolvedRolloutTaskRequest` 三重包含 harness / 平行包含 evaluator 与 rubric（§8.2） | 只保留一棵 spec 树，去掉顶层平铺拷贝 |
| R2 | 冗余 | staleness / 训练资格 / reward 在三个层级重复存储，无权威来源与派生方向 | 声明"原始事实层 + 派生视图 + 互检规则"（现有 policy_loss_candidate 五处互检是范本） |
| R3 | 冗余 | `CompletionRecord` 把三种捕获体制折叠成约 35 字段全能对象（§8.5+§16.3） | 薄核心 + 按 `tokenization_source` 判别的扩展段；与现有 `GenerationRecord` 衔接 |
| R4 | 冗余 | `EnvConfig` 与 `ComposableEnvSpec` 职责重合（§6.2/§8.1） | 收敛为 config（声明）→ loader → 运行对象两层 |
| D1 | 不当 | 主架构图只画了 service_driven 拓扑；trainer_native 被降格为横切补丁；三套 token 契约无映射 | 声明双拓扑共享核心；服务平面归属 service_driven；给出 AgentLoopOutput ↔ TrainingView ↔ TrainTrace 映射 |
| D2 | 不当 | §16.2 宣布的独立安全平面未进主图；现有 L4/L5/EpisodeVisibilityPolicy 未声明为继承基础 | 安全平面入图；写明继承不变量清单，禁止平行重写 |
| D3 | 不当 | UserSim/Permission 的 ownership 内部矛盾（§3.1 vs §8.1）；执行平面无 UserSimRunner / PermissionGate；训练期运行档位未定 | 任务侧事实归 TaskSet、行为引擎归 spec；Runtime 层补两个执行对象；首版限定 deterministic |
| D4 | 不当 | 白盒路径缺 token tape 构造者（renderer）组件归属 | 命名 `TokenTapeBuilder`/`RendererBinding`，挂接 §16.10 prefix 检查 |
| D5 | 不当 | 训练资格被三平面共有、无最终合成者 | 声明资格为各平面事实的合取，由单一 eligibility gate 合成 |
| T1 | 实践不符 | 环境验证不变量缺失（空 patch 必失败 / golden patch 必通过 / 确定性 / reward profiling；MAI+Nemotron 均为一等流程） | `EnvironmentPackageSpec` 增加验证不变量字段 + 环境级 fail-closed 规则 |
| T2 | 实践不符 | `RewardNormalizer` 越过训练框架边界（组归一化依赖 group 完整性，三个框架均在训练侧做） | 核心只出 raw reward + components + group_id；归一化划给训练后端 |
| T3 | 实践不符 | `TrainTrace` 无 MoE routing replay / teacher logprobs / 多模态扩展点（verl、slime、Nemotron 均已需要） | 增加有类型的 `backend_tensors` 注册制扩展槽 |
| T4 | 实践不符 | 评分环境 prewarm 缺位；默认最严评分隔离的吞吐代价未被架构承接 | `SandboxLifecyclePolicy` 加 prewarm 策略；§11 补时长方差风险 |

**最终建议**：主方向与 §16 硬边界保持不动。优先修订三处——D1（把双拓扑画进主架构，并给出三套 token 契约的映射）、T1（环境验证不变量入契约）、R3（CompletionRecord 拆分）——因为它们决定后续所有数据契约的形态；其余各条可在契约细化时随手吸收。修订后，这份文档就可以作为"现有模块到新架构映射"（§14）的稳定基准。

---

## 9. 修订复核（针对重定位文档修订版的二次检查）

重定位文档按本报告完成了一轮修订（修订后约 2588 行）。本章逐条复核修订是否解决了第 4/8 章的问题，并记录复核中发现的新问题。

### 9.1 13 条问题的解决状态

| 编号 | 状态 | 修订位置与质量评价 |
| --- | --- | --- |
| R1 | **已解决** | §8.2：`ResolvedRolloutTaskRequest` 移除了顶层 `harness` / `builder` / `evaluator` / `training_runtime` 平铺字段，改为单棵 spec 树 + `resolved_section_digests` + 只读访问器约定 |
| R2 | **已解决** | §8.8 末新增"原始事实层 / 派生视图层 / 最终合成层"派生方向声明 + 派生视图不一致即 fail closed |
| R3 | **已解决（但见 9.2 新问题 N1）** | §8.5：薄核心 + 按 `tokenization_source` 判别的 `capture_extension`（Native / Proxy / RendererBridge 三种），还补了 `captured_text_only` 降级态 |
| R4 | **已解决** | §6.2 末段：`EnvConfig` = 可校验声明树，`ComposableEnvSpec` = loader 解析结果，禁止平行保存两份规格 |
| D1 | **已解决** | §5 双拓扑声明 + 共享核心清单 + 两条拓扑流程；§6.5 声明 builder 非 trainer_native 必经环节 + 四契约字段映射表；§6.7 双接入模式；§7 数据流补 trainer_native 替代说明；§11.10 新风险；M3~M6 拓扑标注；§12 Q8 按拓扑分叉 |
| D2 | **已解决** | §5 新增安全平面横切图（含 eligibility gate 七维合取）；明确继承 `visibility.py`、`episode_projection.py`、`EpisodeVisibilityPolicy` 现有资产，"不是新建平行机制" |
| D3 | **已解决** | §6.2 拆分"UserSimSpec owns 可复用引擎 / TaskSet owns user-side task facts"；§6.3 新增 `UserSimRunner`、`PermissionGate` 及调用时机；首版限定确定性用户模拟（并给出 GRPO 噪声理由）；§6.5 `ResponseSpan.source_type` 增加 `user_message` 和 `harness_interstitial` |
| D4 | **已解决** | §6.3 新增 `TokenTapeBuilder` / `RendererBinding`，并区分了它与 service_driven `TrajectoryBuilder` 的本质差异 |
| D5 | **已解决** | §6.6 声明该平面只产出 facts；§6.7 `TrainingEligibilityGate` 为唯一合成者（七维 AND）；§8.6 新增 `TrainingEligibilityReport` 审计实体 + `eligibility_report_ref` 回链 |
| T1 | **已解决（超出建议）** | §8.1 `EnvironmentValidationReport`（空 patch 必失败 / golden patch 必通过 / 确定性 / 训练 runtime 复验 / reward profile），并增加了 `patch_validation_applicability` 判别，避免非 patch 型任务被迫套用 patch 门槛；§11.11 + §12 Q11 配套 |
| T2 | **已解决** | §6.7：`RewardNormalizer` 改为 `RewardSignalPackager` + `RewardNormalizationPolicyRef`（只记录不执行）；归一化默认归训练后端；离线导出场景须先确认完整 group；§11.12 配套 |
| T3 | **已解决** | §8.6 `TensorRef` / `backend_tensors` 注册制（含 alignment / visibility_class / validator_ref）；§16.12 硬边界 + §11.13 风险 |
| T4 | **已解决（超出建议）** | §6.3 `ScoringRuntimePrewarmer` + prewarm 防泄漏约束（hidden verifier 路径/文件名/测试数量等不得经 prewarm 泄漏——这条是修订自行补充的，正确且必要）；§8.4 `scoring_runtime_prewarm` 字段；§11.14 风险 |

结论：13 条全部得到实质性解决，多处修订质量超出本报告的建议（prewarm 防泄漏、patch 验证适用性判别、`captured_text_only` 状态）。

### 9.2 复核发现的新问题与遗留问题

#### N1（中）：§8.5 与 §16.3 出现同名扩展类的分叉定义

修订把 capture extension 同时写进了 §8.5（主契约）和 §16.3（补充章节），两处的字段集和枚举不一致：

```text
1. token_provenance_status / logprob_alignment_status：
   §8.5 放在 CompletionRecord 核心层（对三种捕获方式都生效，正确）；
   §16.3 放在 RendererBridgeExtension 内部（错位——native / proxy 模式同样需要这两个状态）。

2. bridge_status 枚举：§8.5 为 3 值（无 not_needed）；§16.3 为 4 值（含 not_needed）。

3. 字段集：§8.5 NativeCaptureExtension 有 inference_engine_version、native_gateway_route，
   §16.3 没有；§8.5 ProxyCaptureExtension 有 model_requested / model_used / raw_request_ref /
   raw_response_ref，§16.3 没有；§8.5 扩展字段多为必填，§16.3 多为可空。
```

这恰好违反了修订自己在 §8.8 末新立的"同一事实不得多处独立维护"规则。建议：§16.3 删除重复的类定义，只保留"为什么这些字段必须一等化"的论证并引用 §8.5 为唯一权威定义（或反向指定 §16.3 为权威）。`bridge_status` 的 `not_needed` 值应保留并并入权威定义（native capture 场景确实不需要 bridge）。

#### N2（中）：`loss_mask` 派生式仍把轨迹级资格折叠进 token 级 mask（未采纳的建议）

§6.5 保留了 `loss_mask = sampled_mask AND role_policy AND training_eligibility_policy`。这与文档其余部分有三处具体矛盾：

```text
1. 与 §16.1 冗余冲突：资格不通过的轨迹按三档分级本来就不进 formal batch（fail closed），
   再 AND 进 mask 会制造"全 0 mask 但仍在 batch 里"的歧义样本。

2. 与 §6.5 自己的映射表冲突：表中 response_mask ↔ loss_mask 对应；
   若资格清零 loss_mask 而 response_mask 不变，跨契约对应关系断裂。

3. 与现有代码冲突：rl/training_view.py 的 ResponseSpan 校验强制
   assistant_generation span 的 response_mask_value=1；
   资格清零 mask 会让已验收的 span 校验直接失败。
```

建议修订为：`loss_mask = sampled_mask AND role_policy`（纯 token 级语义）；轨迹级资格只通过 `training_eligibility_class` 表达，由 gate 在 batch 准入处拒绝整条轨迹，不折叠进 mask。

#### N3（轻）：trainer_native 旁路审计 artifact 缺一句"必须"

M7 完成标准（TrajectoryArtifact 记录握手字段）和 §16.7 的 verl 边界（RepoHarness owns TrajectoryArtifact）都隐含了 trainer_native 路径也要写 artifact，但没有任何一处用"必须"句式写成不变量。缺这一句，实施者可能把 trainer_native 的 artifact 写盘当可选优化省掉，导致同一条轨迹在 service_driven 下可审计、在 trainer_native 下只剩 AgentLoopOutput——两拓扑事实分裂。建议在 §6.7 trainer_native 段或 §16.7 加一句："trainer_native 即使直接向训练框架返回 AgentLoopOutput / Sample，也必须旁路写出（或可确定性重建）同等语义的 TrajectoryArtifact。"

#### N4（轻）：builder / evaluator 配置从 §8.2 移除后没有声明新家

R1 修复移除了 `ResolvedRolloutTaskRequest` 的 `builder: TrajectoryBuilderSpec` 和 `evaluator: EvaluatorSpec`，但 `EnvConfig` 的七个 section 里没有 trajectory builder 的位置（builder 策略是 service_driven 的处理选项，不是环境语义，放 rubric/scoring 也不合适）；§8.2 文字提到 `resolved.training_runtime_request` 访问器但其数据来源未定义；`TrajectoryArtifact.builder_strategy` 仍要求记录。建议声明：builder 策略放在 `RolloutTaskRequest.overrides` 或 service 级配置；evaluator 配置等于 `EnvConfig.rubric` / `scoring` section 的派生视图。

#### N5（轻，可接受的残留）：§5 前两张主图本体未改

双拓扑通过图后的免责声明（"上面两张图画的是长期 service_driven 拓扑的主路径"）和补充流程文字表达，前两张 mermaid 图本身仍画着全链路。快速读者只看图仍可能误读。可选改进：在两张图的标题或首个节点上直接标注"service_driven 长期拓扑"。

#### N6（轻，前次报告未列入故未修复）：`HarnessSpec.tool_surface` 仍是裸 `str`

与现有 4 档 profile × 27 条 capability registry 的颗粒度不匹配（本报告第一版曾列出，架构版未保留）。建议至少注明该字段取值域为 profile id、真实定义由 registry 持有。

### 9.3 复核结论

13 条架构问题全部解决，修订质量整体高于预期（三处超出建议的自发补强）。剩余 6 条中：**N1（消除 §8.5/§16.3 分叉）和 N2（loss_mask 派生式修正）建议在文档定稿前处理**，因为 N1 违反文档自己新立的单一权威规则、N2 与已验收代码直接冲突；N3/N4 各加一句话即可；N5/N6 可选。处理完 N1/N2 后，文档可以进入 §14 的"现有模块映射"阶段。
