# MiMo 开放 harness、训练桥接与资产核查

日期：2026-09-23。类型：**固定版本源码／开放资产专题**，不是 MiMo-V2.6 报告的第二份摘要。

**结论摘要。** `mimoagent` 提供可运行的原生 agent 与黑盒 CLI 执行层，但其独立 `traj.json` 主要是消息快照，不能代替训练 tape。实际 coding RL 经 MiMo 的 verl 配方进入 Uni-Agent Gateway，后者捕获 token、组织 chain，再由 TransferQueue 交给 learner。当前启动配方采用四种原生 harness、colocated async、session 级 GRPO 和 prompt-mean loss；默认只选每个 session 的最长模型输出 chain，且允许回滚末次 assistant。这不是“所有动作都保留”的策略，也不是报告全部 RL／MOPD2 机制的完整复现。

两条评分路径也不同：`opensource-code` 在 actor 环境内执行后置测试；Datacurve DeepSWE 会捕获包含已提交修改的二进制 patch，在新环境评分。本次确认了代码、CLI 安装与模型卡入口，**未取得可冻结并逐行核验的 MiMo 约 3k coding 任务清单、对应镜像与完整 split**。没有运行 GPU、容器或真实 Claude Code；完成了有限 CPU 检查，其中复现了启动脚本默认过滤开关与校验器预期不一致。

导航：[版本与范围](#scope) · [架构](#architecture) · [原生路径](#native) · [真实 CLI](#cli) · [训练捕获](#capture) · [训练消费](#training) · [环境与评分](#grading) · [资产](#assets) · [检查与风险](#checks) · [项目映射](#project)

<a id="scope"></a>
## 1. 固定来源、阅读范围与证据身份

### 1.1 三库版本及依赖关系

| 代号 | 官方库与分支 | 本次固定 commit | 本专题中的职责 |
| --- | --- | --- | --- |
| M | `XiaomiMiMo/mimoagent`, `mimo-oss` | `467f0a19016f0ac4d63b8d17a1f0da9ba07f232c` | 原生／黑盒 agent、工具调用、环境、评分、独立运行与消息导出 |
| U | `XiaomiMiMo/uni-agent`, `mimo-oss` | `c63e0b01c375ebede95e01fe92bc367df24e5bf3` | Gateway、session、token 捕获、chain 组织、runner 管理与 TQ 输出 |
| V | `XiaomiMiMo/verl`, `mimo-oss` | `e2b9fc03c6e01247f5d93c44201b068ea320b7de` | coding 配方、数据 adapter、调度、优势计算与 trainer 接口 |

三份提交均在 2026-09-21。V 的 `third_party/mimoagent-osr` 与 `third_party/uni_agent` **gitlink 分别正好指向上述 M/U**；不是任取三个最新 main 拼接。V `.gitmodules` 的 M URL 仍使用 `XiaomiMiMo/MiMo-Agent.git` 名称，本轮未验证从零递归 clone 的重定向／安装行为。U 自己根目录另有历史 verl gitlink，不能在安装时不加区分地用它替换 V。[V0][V0]

项目基线：`codex/project-status-20260923@0554dafd633cd982288bd60a54f75da65e5c54d4`。本次工作分支 `pro/mimo-open-code-assets-20260923` 建自已有 MiMo 报告分支提交 `aa423327b76c541e744f2f0fb7ad3c9ceea8d32d`。项目事实以[9 月 23 日同步入口][P0]和相关文档为背景；没有重新审计全部 rh2 实现，也没有纳入未发布的本地工作。

### 1.2 哪些是本次独立核查，哪些不是

**独立核查：**三库目录与 gitlink、下表指定代码范围、启动配置覆盖、两种 agent 路径、两种 SWE scorer、模型卡可访问内容，以及文末 CPU 检查。

**借助既有成果：**[MiMo-V2.6 技术报告笔记](mimo_v2_6_technical_report.md)提供 GRS/GAR、MOPD2、Sample Mixer 和开放资产宣称的比较索引。本次没有重新通读其 44 页 PDF，因此报告实验结论应查该笔记及原文，而不由本专题的现代代码倒填。

**不是已完成事项：**整库逐行审计、完整 codec／Anthropic HTTP 适配审计、ReplayBuffer 全部策略、SGLang backend 与 Megatron 分布式数值对拍、完整上游 tests、K8s/Docker/CLI/GPU 运行、权重下载和镜像构建。未核这些范围不意味着它们不正确或未公开。

| 阅读面 | 实际范围 | 关键文件／符号 |
| --- | --- | --- |
| M 导航与配置 | README、AGENTS、目录；两种 demo 与 V 训练 mini-CC 配置 | [M0]、[M1]、[M2]、[V2]、[V3] |
| M 原生执行 | BaseAgent、CCAgent；DefaultAgent 1–300；工具具体实现未全部展开 | [M3]、[M4]、[M5] |
| M CLI | ClaudeCodeAgent 全文件、SDK runner、安装脚本与公共安装桥 | [M6]、[M7]、[M8]、[M9] |
| M 独立运行与导出 | batch 全路径及 save；OpenAIChatModel 1–270 | [M10]、[M11]、[M12] |
| M 环境 | registry；base 1–640；opensource-code；DeepSWE 主路径及尾部；rubric_judge 1–230 | [M13]–[M17] |
| M 资产转换 | Datacurve DeepSWE 转换器、LICENSE；其他 converter 只查目录 | [M18]、[M19] |
| U Gateway | Trajectory 类型、session 主文件；未全文核 codec 和 HTTP adapters | [U1]、[U2] |
| U framework | entry；framework 1–1350、1440–文件末尾；中间 dump 细节未全读 | [U0]、[U3] |
| V 配方 | train.yaml、完整 run_train.sh、validator、dataset/reward/runner | [V1]–[V8] |
| V trainer | main_ppo 1–170；colocate_async 全文；v1/utils；trainer_base 1–310、900–1150、1880–2420 | [V9]–[V12] |
| V loss | core_algos 1000–1270 及版权；只重点核 prompt 权重与 reduction | [V13] |

源码导航保留原始文件／符号和固定 commit。表中的“读到”不代表所有相邻功能都被验证；测试目录只完成定位，未执行其测试套件。全文搜索未能返回某些实际存在的函数，本次以固定文件内容为准，不以搜索零结果证明功能不存在。

<a id="architecture"></a>
## 2. 先区分两套产物流：独立运行和真实训练

### 2.1 独立评测／轨迹收集

```text
JSONL / parquet / HF rows + YAML
  → batch._process_instance / 每次 rollout 的输出目录
  → dataset registry → base environment → task setup
  → native agent/model.query 或真实 CLI/SDK
  → attach_rollout → dataset.calculate_reward
  → result 状态、msg/log、traj.json
```

M 的 batch 可以多线程跑多个实例、一个实例跑多次，也能按配置选择多个 harness；这是**执行与数据收集能力**，不能仅据线程池称为跨策略 fully-async RL。其独立多配置选择可按 rollout unit 哈希，同题不同 rollout 可能选不同 harness。resume 根据已有结果状态跳过成功处理的 unit；模型、配置变化后复用同一输出目录不自动提供科学上等价的重跑，应检查 `--redo` 和输出身份。[M10][M10]

standalone 状态汇总还将无 error_category 的非零 reward 视为 Pass。开启连续 rubric 分数后，这个 Pass 不能直接当成原 benchmark 的二元成功指标；应同时保留原始 score 和 resolved 语义。[M10][M10]

### 2.2 真正的 coding RL 路径

```text
V run_train.sh → main_ppo.TaskRunnerV1 → trainer mode
  → U AgentFrameworkRolloutAdapter / Gateway
  → V MimoAgentSWEDataset → tools_kwargs.instance
  → V mimoagent_runner → M environment + native/CLI
      ↘ model HTTP requests → U Gateway → trainer LLM client → inference backend
      ↘ test/verifier reward → session reward_info
  → Gateway finalize → trajectory selection → scalar scoring → TQ rows
  → GRPO: final row per session → per-session advantage → retained rows
  → global prompt token weights → actor worker update
  → colocated weight publication / generation resume
```

`mimoagent` 保存的消息文件不是此图的训练真值；训练 token 来源在 Gateway/backend。`AgentFrameworkRolloutAdapter` 对生成采用异步提交，learner 通过 TQ 消费；V 的 trainer mode 决定是否以及怎样与参数更新重叠。[U0][U0] [U3][U3] [V4][V4] [V9][V9]

| 层 | 负责 | 不应默认归给它 |
| --- | --- | --- |
| harness | 用户任务、工具、上下文变换、停机行为 | 正确的优势归一化或最终 grader 安全性 |
| dataset environment | setup、工件／测试规则、reward 与部分故障事实 | 任意 HF 题源的即插即用兼容 |
| Gateway | 实际送往后端的 token、生成结果、chain 与版本片段 | 原始 HTTP 到 token 的任意语义变换都已证明无损 |
| framework | session 生命周期、结果选择、reward 传播、TQ 字段 | 每个原始 rollout 必定完整保留，或所有错误已阻止进入学习 |
| trainer | 采样、优势、分母、更新及参数同步 | 报告中所有优化机制已在该 recipe 启用 |

<a id="native"></a>
## 3. 原生 mini-harness：`cc-agent` 不是真实 Claude Code

### 3.1 三种配置不能当作同一个实验

| 配置 | 实际执行者 | 工具与预算 | 关键区别 |
| --- | --- | --- | --- |
| M `example_configs/swe_cc_agent.yaml` | `CCAgent` 原生循环 | Bash/Read/Write/Edit/Grep/Glob/Agent/Compact；step_limit 500 | 可调用子代理和压缩，模型字段只是演示默认 |
| V `config/agent/code/mini-claude-code.yaml` | 同为原生 `cc-agent` | **仅六个基础工具**；step_limit 500 | 无 Agent、无 Compact；system 自称 Claude Code 不改变类身份 |
| M `example_configs/claude-code.yaml` | 真实 CLI，经 Agent SDK | 示例 max_turns 200、high effort、run_timeout 18000s | CLI 自带工具与上下文协议，默认模型和资源又不同 |

这些配置不是 matched-budget 或 matched-model 对照。V 默认 mix 的四个标签是 mini-mimocode、mini-bash、mini-claude-code、mini-codex；**不是四款真实 CLI 混训**。[M1][M1] [M2][M2] [V2][V2] [V3][V3]

### 3.2 原生调用如何变成工具观察

`BaseAgent.run` 维护消息和 agent 本地 step 预算；`DefaultAgent.step` 调用模型，解析 tool calls。无 tool call 时返回 Idle；一个调用同步执行，多个调用用线程池并行，但返回 observation 按原调用顺序写回。并行返回有序不等于对共享文件的写操作必定无竞争。[M3][M3] [M4][M4]

FormatError 可以生成恢复提示后继续，TransportError 升为终止型 InfraError，普通工具错误往往成为下一轮观察。单条工具输出默认最多 **40,000 字符**，不是 token；工具集合可以修改截断策略。`tool_call_errors` 标记的是 generation-step 的格式错误等特定事件，不是所有任务失败的标签。

模型调用数、agent step 数、工具数、子代理调用数不是同一计数。子代理共享模型连接不代表自动共享总 turn 上限。是否需要全局 budget 应看实际配置，而非仅凭 `step_limit` 推导。

### 3.3 Compact 是模型决策，不是自动窗口管理

`CCAgent` 的 Compact 工具请求下一次 query 前做摘要：使用原消息片段和摘要指令发起一个 **不带 tools 的 model.query**，然后以 system、原始任务锚点、边界和摘要替换当前 `messages`。它不是每到阈值就强制执行的滑动窗口，也不是本次已验证的学习得到的摘要策略。[M5][M5]

摘要调用不经过通常的 BaseAgent.query 计步／消息追加路径；因此只统计普通 steps 或最终 `messages` 可能漏掉一次调用及前史。若经训练 Gateway 发起，该请求仍可能被捕获，但工具 schema 改变、上下文重写以及最终 chain selection 会决定哪些 token 留在训练中。

配置里的 usage footer 和 wrap-up hint 是观察／提示机制，不能证明 backend 的真实 context capacity 一致。V 所选 mini-CC 根本没有 Compact，所以不能将 demo 中 100k 窗口、10k buffer 等设置写成该训练 recipe 的压缩参数。

### 3.4 Chat model wrapper 保留什么、丢弃什么

`OpenAIChatModel` 将 message、tool args、reasoning_content／reasoning_signature 发送或回放；返回给 agent 的 payload 是文本、工具和 reasoning 字段，**不携带原始输入 ID、输出 ID 或 choice.logprobs**。独立 M 层的 token_stats 是服务端 usage 汇总，不是可训练概率序列。[M12][M12]

SDK 内部重试默认关闭，但外层 tenacity 仍最多五次重试部分错误。重发同一前缀可能产生多个真实生成，不等于已实现 exactly-once。流式实现聚合 chunk；非空输出并不强制要求取得有效最终 finish_reason。因此“迭代器正常结束”与“生成完整结束”需要由更高层事实核对，本次未运行中断注入。

<a id="cli"></a>
## 4. 真正的 `claude-code`：安装、协议、结果与可见性

### 4.1 CLI 与 SDK 的版本是两件事

固定 M 提交的 CLI 默认 **2.1.269**，运行路径 `/opt/mimo-claude/claude`；与项目当前 CC 2.1.205 不同。SDK 在独立 CPython 3.12 环境中运行，避免替换题目自身 Python。CLI 版本会用 `claude -v` 检查，但 SDK 默认安装规格是未固定的 `claude-agent-sdk`，不是完全冻结的软件环境。[M6][M6] [M8][M8]

实际安装资源是 `install-claude-code.sh`（连字符）。曾按猜测查找的下划线文件不存在，后来已沿常量找到正确入口，不能据第一次 404 宣称缺安装脚本。

离线入口确实存在：通过 `install_env` 传入 `CLAUDE_CODE_PAYLOAD` 或 `CLAUDE_CODE_PAYLOAD_URL`，安装脚本将预构建内容放到固定路径并检查 CLI/SDK。也可预装后 `skip_install`。这些不是 ClaudeCodeAgent 的顶层 `payload_path` 字段；本次没有下载 payload、核验发行二进制或测试离线启动。[M8][M8] [M9][M9]

### 4.2 真实模型路径不经过 M 的 model.query

ClaudeCodeAgent 使用 `model` 对象读取 gateway URL、鉴权和模型名，随后由 SDK/CLI 自行请求；其工具由 CLI 管理。它保留内建 `claude_code` system preset，可追加 system prompt／CLAUDE.md，并使用 bypassPermissions。将 API 指向相同模型不保证两种 harness 的提示词、工具、思考管理或预算相同。[M6][M6] [M7][M7]

SDK runner 默认关闭 WebSearch，并将 AskUserQuestion 自动选为第一项。这是非交互执行策略，不是模型获得了真实用户确认。报告 human-in-the-loop 或问询能力时不能复用这种默认结果。

CLI wrapper 可续跑同一会话，原始 SDK 日志累积在 `/tmp/mimo-claude-logs/claude-code.txt`，随后复制到宿主。日志移到仓库外避免一部分 patch 污染，但仍在 actor pod 内；是否同 UID 可读需要实测，不是权限隔离证明。注入 CLAUDE.md 的 git exclude 也不能保证一个原本受跟踪的同名文件不进入工件。

### 4.3 “Completed” 的证据强度

SDK runner 只在看到 ResultMessage 时持久化结果；若流退出而没有该消息，其 main 仍可能返回 0。外层 wrapper 在退出码 0 时可先给 Completed，结果文件缺失则退到日志尾部。**这一静态路径不足以证明所有真实中断都被识别为错误。** 本次没有复现 SDK 中断，也没有用该观察评价历史 MiMo 训练结果。[M6][M6] [M7][M7]

timeout、stall watchdog、HTTP 空闲、模型输出结束、agent 完成和 grader 完成是不同事实。CLI 的 SDK `num_turns` 与 Gateway generation count 也不保证相等。训练 runner 对两个事实的明确拆分见 §6。

<a id="capture"></a>
## 5. 三种“轨迹”产物：消息快照、运行日志、训练 token tape

### 5.1 独立 `traj.json` 不是 Token-in/Token-out 凭证

M 的 `save_traj` 序列化 info 和按 agent 名索引的 messages／query kwargs。原生 agent 保存的是当前上下文；压缩前的旧 messages 不在最终快照里。真实 CLI 的主 messages 更主要是 task 与最终 result，详细操作在 SDK 日志中。没有原始 token/logprob/mask 的字段不能凭文件名“training schema”补成存在。[M11][M11]

| 产物 | 可以用途 | 单独不能证明 |
| --- | --- | --- |
| M msg/log、CLI 原始 SDK log | 运行诊断、工具与停机过程审查 | HTTP 原字节、所有真实生成 token 和概率 |
| M `traj.json` | 语义轨迹导出、部分 SFT 输入准备 | 历史改写前所有动作、behavior logprob、策略版本 |
| U Gateway Trajectory 与 TQ | 实际训练输入候选 | 捕获的全部动作最终都会被消费，或分布式 loss 已数值等价 |

### 5.2 Gateway 捕获链

`Trajectory` 包含 prompt_ids、response_ids、response_mask、generation_spans，可选 response_logprobs、routed_experts、消息与版本信息。response 区间不仅是模型生成，还包含轮间补入的观察；模型动作 mask=1，外部上下文 mask=0，后者的 logprob 用占位值而非模型行为概率。[U1][U1]

Gateway 将处理后的实际 context_ids 交给 backend，并记录生成 IDs；请求了 logprob 时检查返回与 token 长度。**完整 HTTP→规范化消息→模板→token 的一致性还涉及本轮未全文核查的 codec/adapters，不能据这一层推导任意 Anthropic/Responses 特性都已等价。**[U2][U2]

同一 session 的请求可并发执行，prepare/commit 有锁，backend 推理不一直占锁；完成顺序及其各自保留的 chain 身份参与提交。这不同于简单假设“第 n 条返回一定属于第 n 条发送”。

### 5.3 精确前缀与 rollback：有明确的训练取舍

匹配既有消息前缀与工具集合时，继续原 chain。末次 assistant 被 harness 改写、规范化或重发，且能唯一定位 rollback 边界时，默认配置允许回滚；工具变化或无法唯一匹配则建立新 chain。[U2][U2]

**rollback 会移除原末次 assistant 的 token、mask、logprob 与版本标记；传入的替代内容作为新上下文被编码，mask=0。** generation span 会保留必要的占位／索引信息。这不是 rh2“前缀不一致时保留旧行”的同一策略。

它可以减少重复前缀和 branch 数，但可能不再训练被改写的那次实际采样。是否值得采用，取决于想优化的行为单位及所需证据；不能只用“协议兼容”或“节省 token”判断对错。版本范围也反映保留下来的生成，不一定涵盖 session 曾发生而后被回滚的全部调用。

routed_experts 保存最新一次完整 prefill 路由结果的路径，与逐原始动作的生成时路由事实不能自动画等号。要用于 R3 等机制，仍需单独核对时间身份、切片和 trainer 消费。

### 5.4 默认只训练 `longest`，不是所有 chain

V 配方明确设置 `trajectory_selection=longest`。U 的选择以 **模型输出 mask 总数**为首要键，随后比较 response 长度、turns 和顺序；它可能选择较早的 chain，而不是最后一段主 agent 收尾，也不是最高 reward 的 chain。[U3][U3]

选择发生在 scoring／TQ 之前。未选中的内容可以留作语义调试文件，但不能计为已进入参数更新的经验。`all` 是另一个可配置选择；若要采用，还需核 row 数、optimizer batch 与 loss 语义，不能只改一个枚举。

同一 session 的多条 chain 与同题多个独立 rollout 也不同。以下三种数都应单列：原始模型调用数、Gateway materialized chain 数、实际 TQ 行数。

<a id="training"></a>
## 6. 从开放配方到 learner：哪些算法与异步机制实际启用

### 6.1 启动脚本覆盖 YAML，不能只抄 YAML

下面是 V `run_train.sh` 在相关环境变量未设置、无额外 CLI override 时的**声明默认值**；由于 §9.1 的校验冲突，这并不是本次已成功启动的 resolved recipe。[V1][V1] [V5][V5]

| 项目 | 脚本路径默认 | 限定 |
| --- | --- | --- |
| 模型／训练／验证数据 | MODEL_PATH / TRAIN_DATA / VAL_DATA 必填 | 是本地路径，不是已固定的公共数据 manifest |
| 模型推理后端 | SGLang；temperature 1、top_p .95、top_k 20 | 真实 gateway 参数传播仍需对拍 |
| 训练资源 | 4 节点×8 GPU；actor TP8/CP2/PP1/EP1；rollout TP4 | 不是八卡默认配方；不能只改节点数而不核并行约束 |
| 长度 | 总 262144；prompt 16384；response 245760 | YAML 里是另一组长度，必须按覆盖后配置讨论 |
| prompt batch / rollout n | 32 / 8；gen_batch=1 | YAML n=16，脚本覆盖为 8；行数还受失败与选择影响 |
| actor mini-batch | 32×8 的名义行预算 | prompt-mean 路径要求完整 sampled batch，见下文 |
| 优势与 loss | GRPO，不除组内 std；prompt-mean | 不是报告全部主模型方法 |
| 优化参数 | lr 1e-6、wd .01、clip low/high .2、clip_c 3；entropy coeff 0 | 计算 entropy 监控不等于加入 entropy 正则 |
| 调度 | `colocate_async`；warmup1；stale threshold2、drop | 异步范围由 trainer 控制，不是 M batch 线程池 |
| 训练步／评测 | 200 steps；save5；test_freq=-1；val_before_train=False；resume disable | 配置存在不等于已报告训练结果；默认不建立独立评测曲线 |
| 其他 | fp8_e4m3 KV、FlashInfer；MTP 默认关闭 | 没有在目标 GPU 验证精度、可用性或收益 |
| harness | 四种 native，step-hash | 并非真实 CLI 默认混训 |

脚本会 resolve Hydra config、调用 validator、写 run manifest；`PREFLIGHT_ONLY=1` 是 preflight 出口，不启动训练。脚本本身的设计目标值得借鉴，但当前默认值仍需要验证，而不能把“有 validator”当作配置必然自洽。

### 6.2 Harness 选择与 prompt group

训练 runner 的 step-hash 按题目身份与 harness_round 等决定配置，使同题同轮的兄弟 rollout 默认使用同一 harness；不同轮可更换。session/paired 模式则按 rollout 索引分配。若 `group_advantage_by_harness=true`，trainer 另用 harness 后缀细分优势组；默认 false。独立 M batch 的按 unit 哈希与这里不是同一抽样规则。[V4][V4] [V12][V12]

这可作为“同题组内先固定工具能力”的实现参照，但并没有证明该混合规则优于单 harness。需要保留配置标签、原始 uid、session 和最终数据消费分布，不能仅统计任务来源。

### 6.3 Session 完成不等于任务正确或 agent 自主完成

训练 runner 先检查不可判分的 agent status，然后通知 Gateway agent 阶段结束、执行 grader、POST reward_info。正常返回时 `finished=True` 表示这一轮处理／评分收口；`agent_completed` 与 `termination_kind` 单独说明 agent 是否因预算停止。于是一个截断但可评分的任务可以 finished=True、reward=0 或1。默认 `mask_unfinished_episode=false`，不能把这个字段解释成自动 horizon masking。[V4][V4] [U3][U3]

reward POST 有最多六次、独立超时与退避，4xx 不重试；这改善交付容错，但并不是跨进程崩溃后的完整 exactly-once 证明。Gateway 的 reward_info 更新是覆盖操作；是否重复产生任务尝试仍受外部生命周期影响。

框架并发执行同题 n 个 session，等待该组返回后写成功 session，失败 session 留在统计／诊断里；至少一个成功 session 时可把 uid 标为 finished。**这一层并不实行 rh2 那样的“一个成员无效即整组淘汰”。** 最后采到哪个 batch 还取决于 ReplayBuffer；本次未完整审计其准入与补采逻辑。

### 6.4 Token 到 TQ 的转换

`_trajectory_to_tq_field_and_tag` 写入 prompts、responses、input_ids、attention/position、response_mask/loss_mask、rollout_log_probs、可选 routing，以及 uid/session/global_steps 等。scalar reward 放在 response 末位 rm_scores；模型 mask 区分动作与外部观察。tool-error flags 对齐 generation spans 后形成辅助 mask；长度不符时给全零辅助 mask并记录对齐状态，**不是删除所有动作**。[U3][U3]

同一 session 多行输出时，部分 optional 字段只保留各行共有的键。缺 logprob／routing 的某行可能使该列整体被去掉，不能只看一条完整轨迹推定整个 batch 都有该信息。backend 没报告版本时，tag 可以回退到 dataloader global_steps；这只是兼容值，不等于补齐真实策略来源。

### 6.5 优势在 session 级算，loss 在 prompt token 级平均

V 的 `compute_advantage_for_multi_trajectories` 对 GRPO 先选每个 `{uid}_{session}` 的最终保留行来估计优势，再广播回该 session 的其他保留行，避免仅因一条 session 拆多行就增加其组统计次数。非 GRPO 走原函数，不自动继承相同保证。默认 longest 只留一行，所以这里的“final row”实际可能就是被选出的较早长 chain。[V11][V11]

`compute_prompt_loss_weights` 则在完整 optimizer batch 上统计每题所有有效动作 token。按代码展开（不是另一个论文公式）：

$$
T_g=\sum_{r\in g}\sum_t m_{r,t},\qquad
G=|\{g:T_g>0\}|,\qquad
w_r=\frac{1}{G T_{g(r)}}.
$$

$$
L_{\mathrm{prompt}}=\sum_r w_r\sum_t m_{r,t}\ell_{r,t}.
$$

零动作行权重为0；全 batch 没有有效 prompt 会报错。`agg_loss` 再乘 DP size，以配合之后的梯度平均；Megatron 的 CP／microbatch 处理还在别处，本次没有做分布式等价证明。[V13][V13]

**等权的是题目，不是 session 或训练行。** 同题长 rollout 的动作 token 较多，在该题内仍可能贡献较多总权重。无重复地拆行、保留同一 uid、每个 token 的 loss 不变时，上式对该拆分不变；若重复训练前缀、删除真实动作或改变上下文，这项代数性质不再足以证明等价。

trainer 在编辑 mask／优势后，将全局 prompt_loss_weights 写入 TQ，再传给 actor；`_update_actor` 要求 prompt-mean 下 len(batch) 等于配置的完整 optimizer minibatch 行数。不能一边允许任意 fan-out，一边假定这个数永远仍为题数×n。[V12][V12]

### 6.6 Colocated async 与报告完整系统的区别

`PPOTrainerColocateAsync` 在采样结束时 abort 未完成请求并 sleep 推理副本以释放权重和 KV；训练步结束后发布新权重，再恢复生成。它确有 partial rollout 与跨步骤消费机制，但训练／推理共享 GPU 仍是阶段性切换，不是大型报告中独立资源池连续同时运行的同义词。[V10][V10]

恢复代码可从 TQ checkpoint 重新派发未完成 prompt，并清掉相应旧输出；这不等于恢复了原有 K8s 环境中间状态。正式可恢复性要用包含工具副作用的任务验证，而不只是看 checkpoint 文件存在。[V12][V12]

### 6.7 哪些论文机制不能据此宣称开放复现

| 报告／宣传中的机制 | 本次代码证据 | 结论 |
| --- | --- | --- |
| mini-harness 与多 harness | 明确配置、选择器和训练 bridge | 有实际实现；收益仍不能只从代码推出 |
| GRS 式 programmatic×rubric | 通用 rubric 层可表达这种乘法 | 尚未核到报告的组条件触发和完整配方 |
| GAR 动态修订 rubric | 当前 coding 路径未找到相应生成／组级调用 | 不把静态 rubric judge 当 GAR |
| MOPD2 / teacher OPD | 底层 verl 有 distillation 模块，但所选 AgentFrameworkRolloutAdapter **拒绝非空 teacher_client** | 本路线不能靠一个开关启用报告 MOPD2 |
| Sample Mixer | 四 harness 配置和 TQ 存在 | 不等于报告全域 Sample Mixer 已复现 |
| tool/repetition/deep-failure 策略 | 有不同代码分支，默认关或 monitor | 不把实验性可选分支算成默认 recipe 或报告已消融机制 |

“在所查路径未找到”不等于整个组织未公开；以后发现其他入口，应另立来源、版本与训练路径补记。[U0][U0] [V1][V1] [V12][V12]

<a id="grading"></a>
## 7. 环境与评分：必须按 dataset_type 区分

### 7.1 Loader 通用，不代表 scorer 通用

固定 M registry 明确登记 arvo、deepswe、generic、opensource-code 等路径。支持从 HF/parquet 读 row，只解决运输，不能直接兼容所有 SWE-bench schema。V `MimoAgentSWEDataset` 要求 `extra_info.instance_json`（或兼容 instance）能展开成带 docker_image 的字典；JSON 字符串推迟展开用于避免 Arrow struct-union 问题。[M13][M13] [V7][V7]

这份 adapter 不下载镜像、不证明测试存在、不核任务 split，也不实现完整数据生产漏斗。`reward_model.ground_truth=""` 是桥接默认，不表示任务没有隐藏 verifier。

### 7.2 `opensource-code`：后置测试、原环境评分

主要字段为 dataset_type、instance_id、cwd、docker_image、problem_statement、test_patch、test_command，以及可选 verifier timeout。test_patch 可以同时携带隐藏测试与 verifier 脚本，评分时恢复相关路径后严格应用；test_command 的退出码0映射为1，其他映射0。**测试收集、F2P/P2P、skip/xfail 和断言含义由注入脚本负责，不由一个通用 exit code 自动保证。**[M15][M15]

环境从镜像当前仓库状态记录 base；该 schema 没有强制一个期望 base_commit 字段来独立核对镜像任务身份。Git 历史检查、清理和域名屏蔽可降低部分泄漏风险，但不证明不存在未来代码、不可达对象、包缓存或其他答案渠道。

base 的默认工件捕获为 `git add -A` 后 `git diff HEAD`，会包含部分新文件，却不等于相对目标 base 导出所有改动：agent 自己 commit 或移动 HEAD 后需额外检查；默认文本 diff 也不能当作已验证的任意二进制工件运输。原环境内评分可能与导出的 patch 不等价。[M14][M14]

### 7.3 Datacurve DeepSWE：反而是 fresh grader

此处 DeepSWE 是 **Datacurve benchmark**，不是 Agentica 的 DeepSWE 训练模型。转换器从 Harbor task.toml、instruction、tests、solution 等生成 M row；grader.py+config.json 同时存在时识别 v1.1，否则 v1.0。转换本身不重新验证任务。[M18][M18]

DeepSWEEnvironment 要求 base_commit。它先 soft-reset 到 base、保留已提交与未提交工作，再 `git add -A` 和 `git diff --cached --binary <base>`；通过文件／tar或base64取回 bytes，在新建的同镜像环境中应用并评分。文本版 patch 用于展示，bytes 是执行输入。**所以不能把全仓库概括为同容器评分或只支持未提交文本 patch。**[M16][M16]

v1.0 与 v1.1 的初始化、reset、grader 和输出协议不同。v1.1 会保留镜像构建产生的必要工作区变化，由 grader 做逐路径处理；全局 hard reset/clean 可能破坏这些资产。实现还修复 `/opt/venv` 的 PATH，并在 verifier 命令前清掉代理环境变量，说明 actor 网络配置可以干扰项目测试，而非仅影响下载。[M16][M16]

该路径默认将 verifier 时间下限提高到3200秒；这改变运行预算，不能不加说明地称为完全保持原始 task.toml 协议。`reward.txt=-1` 在 v1.1 被归为 verifier crash；缺失／损坏 reward.json 多数仍映射0并附诊断。这些返回语义应在实际训练入口再次核查，不能只接受模块注释“不会产生假0”。

### 7.4 Rubric judge：可表达丰富监督，但上下文与组合方式要追到 caller

本节依据 rubric 模块说明、解析器及 base 调用核对接口；没有全文审查 judge 执行器，也未实际运行评分。rubric 层可给每条义务二元 verdict、可选 solution 等级 S，再与平均二元分 B 组合。solution 支持加权或 S×B；与 programmatic P 又有独立组合：programmatic、rubric、product 或 weighted。**默认 scalar 仍是 programmatic，即使 judge 已经执行。**[M17][M17]

judge 在 doer pod 内检查最终状态、patch、response、rubric 和可用轨迹，通过 verdicts.json 交付，不靠聊天文本抽分。提示词要求可逆修改与不要代做，但并没有凭提示词建立独立执行隔离。当前调用先跑 judge 再跑 programmatic verifier，故需要检查 judge 的环境副作用和成本。

standalone batch 会 `attach_rollout` 提供 agent/task/result。V coding runner 没有这一调用，直接 `calculate_reward`；因此开启 judge 后不能假定它自动得到同样的最终回答和原生轨迹上下文。配方默认不配置 judge，所以这是条件性集成缺口，不是本次默认训练已使用错误 rubric 的证明。[M10][M10] [V4][V4]

### 7.5 故障被记录，不等于下游一定拒收

base 在部分明确故障时返回 error_category；另一些 TransportError 返回0+transport_error，普通异常也可能只返回0和日志。DeepSWE 有自己的 `_infra_error`，使已识别故障保留类型，但仍以数值0加 metadata 返回。[M14][M14] [M16][M16]

V runner 正常收下 calculate_reward 的 tuple，将 reward_info POST；U `_score_from_reward_info` 直接取数值 reward。**在已追踪这几层，未见一个统一依据 error_category 拒收的检查。** trainer 的可选 is_infra 分支也不是同一个字段。最终是否被 ReplayBuffer、过滤或 mask 排除仍需补核，不能由此断言已经污染梯度；但也不能把“日志里写了 infra”当成排除已闭合。[V4][V4] [U3][U3] [V12][V12]

这些边界恰好适合用已知坏评分输出做小规模故障注入：检查真实 tag、rm_scores、组统计、loss，而不是只检查 traceback 是否被捕获。

<a id="assets"></a>
## 8. 开放资产核查：可读代码、可下载模型与可训练数据分开

| 资产 | 本次实际核到 | 没有核到／不能推出 |
| --- | --- | --- |
| 三库源码 | 指定 commits、相互 gitlink、主执行／训练文件可读 | 从零完整安装、版本组合启动通过、报告结果复现 |
| 原生 harness | 明确工具配置、执行类、独立运行与训练 bridge | 任何 repo／模型均无需适配 |
| 真实 CLI | 固定版本安装、SDK、镜像内运行、offline payload入口 | 该版本 payload已下载验证；所有依赖均固定；当前项目 CC 行为等价 |
| `opensource-code` | schema、setup 与测试注入的可执行实现 | 自动附带约3k task rows、全部镜像和 reference/split |
| Datacurve 转换器 | 从本地 checkout 生成数据；v1.0/v1.1分开 | 输出数量固定；等于 MiMo 训练数据；转换已执行 |
| MiMo 约3k coding 发布宣称 | 既有报告笔记有记录，本次按官方仓库／HF入口检索 | **未定位并下载可冻结的完整 manifest**；不能宣布未发布，也不能宣布已可训练 |
| `MiMo-V2.6-Distill-Qwen-9B` | 官方模型卡与 config 索引存在；注明 Qwen3.5-9B 上 SFT | 非该报告四域RL统一最终权重；未下载、固定完整revision或检查权重张量 |
| 代码许可 | M LICENSE为MIT，注明 Xiaomi及mini-swe作者；V所读函数Apache-2.0 | 代码许可证不能替CLI、第三方任务、镜像内容与数据行授权 |
| 公开训练性能 | 脚本、配置、monitor/manifest机制存在 | 本次没有可核的该固定配方训练日志、硬件实测或等预算消融 |

模型卡明确将9B权重作为 agentic RL 的 **SFT 起点**，并包含多域训练说明。官方 config 索引是 Qwen3.5 架构；这不等于当前 miles/Megatron 已支持其全部混合注意力、模板或MTP细节。本专题不据第三方 GGUF/FP8/MLX 派生物判断官方权重性质，也不迁移其分数到未经匹配的 harness。[H1][H1] [H2][H2]

本轮 HF 完整 API／部分直接页面获取不稳定，使用官方可索引模型卡核身份；模型revision尚未固定，表中明确降级为入口证据。没有检索到某个数据清单只意味着本次访问范围未闭合，不作全网“未开源”的断言。

**数据接入前还需最少的实际资产证据：**准确来源／revision、实例数及split、实例行schema、镜像digest或可重建材料、题目repo/base、评分入口、reference/testpatch可见性、许可证与污染关系。本次不以猜测构造一份MiMo数据集ID。

<a id="checks"></a>
## 9. 可复核发现与实际执行的有限检查

### 9.1 默认 `FILTER_GROUPS_ENABLE` 不一致：已做最小 CPU 检查

V run_train.sh 的训练命令采用 `${FILTER_GROUPS_ENABLE:-True}`，调用 validator 时却采用 `${FILTER_GROUPS_ENABLE:-False}` 再转小写。validator 对 `algorithm.filter_groups.enable` 做严格相等检查。[V5][V5] [V6][V6]

在没有设置该环境变量、没有其他参数覆盖且执行到这项校验时，实际配置 True 与预期 False 冲突，理论上将拒绝启动。本次提取这两个 bash 展开式和原 `_get/_check` 函数，在 CPU 上得到：

| 输入 | 训练配置值 | 校验预期 | 最小检查结果 |
| --- | --- | --- | --- |
| 变量未设置 | True | False | ValueError：must resolve to False, got True |
| 显式 True | True | True | 通过该项 |
| 显式 False | False | False | 通过该项 |

这是一个固定提交的、可明确条件化的启动配置问题。**没有跑整个 launcher、Hydra、集群 precheck，也不能保证显式设值之后其他检查都通过。** 此外 validator 将 trainer mode固定为 colocate_async、MTP固定False；脚本暴露的相应覆盖变量不保证均被该 validator 接受。没有修改上游或提交 issue/PR。

### 9.2 prompt-mean 的分母检查

使用原 `compute_prompt_loss_weights` 函数体，构造A题两行4+2个动作、B题一行1个动作、全零PAD行。得到行权重 `[1/12,1/12,1/2,0]`，A/B各有0.5总权重。仅将A的第一行无重叠拆成两行、保持每token loss与uid不变，目标值前后均为 **5.25**；全零batch按实现报错。[V13][V13]

它验证的是函数与该构造样本，不验证整个optimizer、TP/CP/DP、重复前缀或不同上下文的梯度等价。

### 9.3 longest 选择示例

用已读排序元组构造两条 chain：较早chain有4个模型token，最后chain仅1个模型token但总response更长。选择前者，而不是最后chain。此项是读者按实现建立的例子，**不是调用完整U包**；用于避免将 `longest` 误解为 `final`。[U3][U3]

代码与复现说明见[离线检查脚本](reviews/mimo_open_code_assets_checks_20260923.py)。该脚本不联网、不调用模型、不启动shell安装或训练，只执行有限函数／表达式与示例。

### 9.4 尚待实际执行的条件性风险

| 观察 | 当前强度 | 最小下一步，不是已批准实现 |
| --- | --- | --- |
| CLI 无 ResultMessage 仍可能返回0 | SDK runner与wrapper静态路径 | 注入空终止／中断，核最终状态、reward和TQ |
| standalone snapshot没有原始token/logprob | 序列化字段已查 | 不用它替训练 tape；核Gateway实际输入输出 |
| rollback删除已生成动作，longest丢其他chain | 实现明确；未测实际损失比例 | 对项目自然rewrite/compaction轨迹统计删除、重复、保留token |
| returned grader error可能变成数值0 | 已查producer到score边界；最终buffer未全审 | 注入部署错误、收集失败与模型真实失败，追到优势及mask |
| judge缺少standalone的attach上下文 | 两条caller路径差异 | 小任务验证传入task/result/trajectory，记录副作用 |
| 二进制与已提交修改的处理不同 | base与DeepSWE override已查 | 一个newfile/commit/binary的roundtrip与两种grader对照 |

这些发现应按上游最新状态、相关issue和最小复现再次确认后，才讨论PR。既不把设计取舍统称bug，也不把代码注释当运行证据。

<a id="project"></a>
## 10. 对 RepoHarness 的意义：复用参照，不是替换方案

以下映射以项目9月23日同步材料为前提，不新增reward、不修改网络策略、不替换harness，也不批准训练基座变化。

**第一，原生 mini-harness 是可控对照面，不是默认更优。** V的mini-CC只用六工具，适合在相同底座、任务、预算下与真实CC比较接口和执行成本。两者system、工具语义、并行调用、用户问询和上下文行为必须列出；不能只固定模型URL便宣布公平。[M1][M1] [M2][M2] [V2][V2]

**第二，Gateway的保留策略值得与I01做受控比较。** rh2当前前缀漂移保留旧行，而此处rollback与longest会舍弃部分真实采样。可以先复用当前自然工具参数改写和thinking变化轨迹，比较真实动作覆盖、重复前缀与训练行数；不必先开展大规模训练，也不把某种策略称为必然正确。

**第三，数据适配宜按评分合同而不是schema字段数迁移。** opensource-code需要测试补丁+命令，DeepSWE则需base、二进制工件与freshgrader；现有SWE-Gym/R2E不能只改字段名就接入。B应核一个gold/noop/合法替代解及一个确定评分故障，A追踪其最终消费。

**第四，rich feedback仍应与可信事实分离。** 通用rubric engine可以试验更细的质量判断，但组条件、人工／程序判定依据、副作用与教师成本都未因engine存在而解决。当前Conan“通过但部分修复”和某些本地模型“全失败”是不同问题；不从MiMo报告自动选GRS/GAR。

**第五，可直接借鉴的工程产物很具体。** 固定gitlink、resolved config、run manifest、CLI独立Python/payload、binary patch运输、分session优势与全局prompt权重，都可以分别作为复用或对照候选。默认校验冲突又说明这些机制本身也需要小测试。使用它们不要求迁移整个verl/Uni-Agent技术栈。

建议优先的四个辨识实验是：①固定模型和任务比较六工具native与实际CC的可见输入及运行成本；②重放自然消息漂移，对比保留／回滚／选择的token覆盖；③固定几种工件与评分故障，核producer到训练张量的事实；④若确有需要，再开启rubric judge并单列其输入、状态改变与成本。这些是实验建议，不是本次已执行结果。

## 11. 如何继续核验而不重读整个专题

| 需要回答 | 先看本稿 | 尚需的直接证据 |
| --- | --- | --- |
| 真实CLI能否作为训练harness | §4–6 | 当前Anthropic adapter/codec、真实请求与输入ID、CLI终止故障测试 |
| 主训练recipe能否在八卡运行 | §6、§9 | 修改后的resolved config、并行可行性、镜像/数据、GPU运行；不能继承32卡默认 |
| 约3k数据是否可直接接入 | §8 | 官方manifest与revision、镜像与评分材料；当前未闭合 |
| 默认错误会不会产生假训练信号 | §7.5、§9.4 | 完整ReplayBuffer与真实fault injection，不能靠零方差过滤代替 |
| MOPD2/GRS/GAR能否复现 | §6.7 | 对应真实入口、教师接口、组级调用和公开实验；非泛用helper |
| packing后是否语义等价 | §6.5 | 保留相同token/样本权重的GPU梯度对拍；全局分母的跨rank传播 |

本稿作者自查完成，**尚未独立审查**，没有调用或声称创建独立sub-agent。逐项检查与访问限制见[自查记录](reviews/mimo_open_code_assets_self_check_20260923.md)。代码事实、作者注释、报告索引与项目建议分别保留；本稿不产生原论文没有的模型成绩或八卡性能预期。

## 固定来源链接

[P0]: https://github.com/Rogerffff/RepoHarness/blob/0554dafd633cd982288bd60a54f75da65e5c54d4/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/external_sync_20260923/README.md
[M0]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/README.md
[M1]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/example_configs/swe_cc_agent.yaml
[M2]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/example_configs/claude-code.yaml
[M3]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/src/mimoagent/agents/base.py
[M4]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/src/mimoagent/agents/default.py
[M5]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/src/mimoagent/agents/cc/cc_agent.py
[M6]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/src/mimoagent/agents/blackbox/claude_code.py
[M7]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/src/mimoagent/agents/blackbox/resources/run_claude_sdk.py
[M8]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/src/mimoagent/agents/blackbox/resources/install-claude-code.sh
[M9]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/src/mimoagent/agents/blackbox/install_common.py
[M10]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/src/mimoagent/run/extra/batch.py
[M11]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/src/mimoagent/run/utils/save.py
[M12]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/src/mimoagent/models/openai_chat.py
[M13]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/src/mimoagent/environments/datasets/__init__.py
[M14]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/src/mimoagent/environments/datasets/base.py
[M15]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/src/mimoagent/environments/datasets/opensource_code.py
[M16]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/src/mimoagent/environments/datasets/deepswe.py
[M17]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/src/mimoagent/environments/rubric_judge.py
[M18]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/scripts/convert_deepswe.py
[M19]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/LICENSE.md
[U0]: https://github.com/XiaomiMiMo/uni-agent/blob/c63e0b01c375ebede95e01fe92bc367df24e5bf3/uni_agent/framework/entry.py
[U1]: https://github.com/XiaomiMiMo/uni-agent/blob/c63e0b01c375ebede95e01fe92bc367df24e5bf3/uni_agent/gateway/session/types.py
[U2]: https://github.com/XiaomiMiMo/uni-agent/blob/c63e0b01c375ebede95e01fe92bc367df24e5bf3/uni_agent/gateway/session/session.py
[U3]: https://github.com/XiaomiMiMo/uni-agent/blob/c63e0b01c375ebede95e01fe92bc367df24e5bf3/uni_agent/framework/framework.py
[V0]: https://github.com/XiaomiMiMo/verl/tree/e2b9fc03c6e01247f5d93c44201b068ea320b7de/third_party
[V1]: https://github.com/XiaomiMiMo/verl/blob/e2b9fc03c6e01247f5d93c44201b068ea320b7de/recipes/code/config/train.yaml
[V2]: https://github.com/XiaomiMiMo/verl/blob/e2b9fc03c6e01247f5d93c44201b068ea320b7de/config/agent/code/mini-claude-code.yaml
[V3]: https://github.com/XiaomiMiMo/verl/blob/e2b9fc03c6e01247f5d93c44201b068ea320b7de/config/agent/code/mix-four-whitebox.yaml
[V4]: https://github.com/XiaomiMiMo/verl/blob/e2b9fc03c6e01247f5d93c44201b068ea320b7de/recipes/code/mimoagent_runner.py
[V5]: https://github.com/XiaomiMiMo/verl/blob/e2b9fc03c6e01247f5d93c44201b068ea320b7de/recipes/code/run_train.sh
[V6]: https://github.com/XiaomiMiMo/verl/blob/e2b9fc03c6e01247f5d93c44201b068ea320b7de/recipes/code/validate_resolved_config.py
[V7]: https://github.com/XiaomiMiMo/verl/blob/e2b9fc03c6e01247f5d93c44201b068ea320b7de/recipes/code/dataset.py
[V8]: https://github.com/XiaomiMiMo/verl/blob/e2b9fc03c6e01247f5d93c44201b068ea320b7de/recipes/code/reward.py
[V9]: https://github.com/XiaomiMiMo/verl/blob/e2b9fc03c6e01247f5d93c44201b068ea320b7de/verl/trainer/main_ppo.py
[V10]: https://github.com/XiaomiMiMo/verl/blob/e2b9fc03c6e01247f5d93c44201b068ea320b7de/verl/trainer/ppo/v1/trainer_colocate_async.py
[V11]: https://github.com/XiaomiMiMo/verl/blob/e2b9fc03c6e01247f5d93c44201b068ea320b7de/verl/trainer/ppo/v1/utils.py
[V12]: https://github.com/XiaomiMiMo/verl/blob/e2b9fc03c6e01247f5d93c44201b068ea320b7de/verl/trainer/ppo/v1/trainer_base.py
[V13]: https://github.com/XiaomiMiMo/verl/blob/e2b9fc03c6e01247f5d93c44201b068ea320b7de/verl/trainer/ppo/core_algos.py
[H1]: https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B/blob/main/README.md
[H2]: https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B/blob/main/config.json
