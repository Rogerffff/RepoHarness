# AReaL 2.0：服务化架构、真实 Agent 接入与训练消费全链路

**结论摘要。** AReaL 2.0 值得借鉴的不是“多拆几个 HTTP 服务”，而是把用户会话、模型调用、训练轨迹、远程张量和权重发布拆成不同责任面。固定源码显示：默认 SWE 示例仍选择 **v1**；真正显式启用 **v2** 的 Hermes 在线示例是另一条路径。本文分别追踪两者，再说明 SWE 的 agent 如何被 v2 workflow 包装，避免把三者写成一套已经实测的 recipe。最重要的工程观察是：服务间返回成功不等于业务动作成功；session affinity 不等于可恢复状态；调度容量限制不等于逐 token staleness 检查。本文执行了 7 个 CPU 控制流刻画案例，复现了逻辑更新错误被上层忽略、ready 通知容量溢出等局部行为，**未运行真实集群、沙箱、模型训练或性能基准**。

阅读日期：**2026-09-08**。任务类型：固定版本源码专题，配套论文用于定位原型与研究愿景。本文不是 AReaL 全仓审计，也不是产品可部署性认证。

导航：[来源与覆盖](#sources) · [架构总览](#architecture) · [真实入口](#entries) · [会话与轨迹](#trajectory) · [异步与版本](#async) · [训练消费](#learning) · [故障与恢复](#failure) · [CPU 探针](#probes) · [项目映射](#project) · [未完成项](#limits)

<a id="sources"></a>
## 1. 来源、版本和实际覆盖

### 1.1 三个版本不能混用

| 对象 | 本次固定版本 | 作用 |
| --- | --- | --- |
| AReaL 官方主仓 | `f289b989bc5d1930d5c6d592d335e2ffaf8c2f01`，2026-09-08 | 本文所有主仓代码事实的边界；不是声称该提交就是 2.0 发布 tag |
| AReaL-SWEAgent | `f144900d5e0a019bf5381b624c442b49999ffa4d`，2026-07-01 | 实际 SWE workflow 调用的外部 agent／环境生命周期 |
| RepoHarness 阅读基线 | `da82518af1de11ebe6fa054c0cb7b73f9502a0a0`，`miles-migration` | 仅用于文末项目映射；不是 AReaL 实验版本 |

配套论文为 Ran Yan 等的 *Next-Generation Agentic Reinforcement Learning Systems Enable Self-Evolving Agents*，**arXiv:2607.01120v2**，v1 为 2026-07-01，v2 为 2026-07-02，作者来自 Ant Group、HKUST、Tsinghua。已阅读 PDF 全部 13 个物理页，包括正文 §1–7、Figure 1、参考文献尾页；该版没有单列技术附录或实验成绩表。PDF 关键图页已目视核对。未取得本地 TeX，未把原始 PDF 镜像提交仓库。[P]

### 1.2 论文是愿景／原型论证，不是完整服务化性能实验

按原文结构：§1–2 提出部署后学习问题及相关工作；§3 的 ATDP 用事件表示观测、有限内部状态、行动、结果、反馈与元数据；§4 讨论跨执行边界的数据代理；§5 将权重、harness、工具、记忆、回滚和不更新作为不同干预；§6 的 AReaL2.0 **只实现其中在线权重更新这一条原型路径**；§7 重申未完成的范围。Figure 1 位于 PDF p.9，展示原生 agent 的模型调用接到推理服务，再连接轨迹存储和训练服务。[P, pp.1–11, Fig.1]

本文据此把“完整 ATDP、企业隐私治理、自动选择干预、反事实回放”记为研究目标，**不从源码里出现 DataProxy/Controller 就推定全部落地**。论文没有提供足够的训练成绩、服务化消融或总费用来证明该架构在本项目八卡上更快。以下主体以公开代码、配置与本轮探针为依据，不能反向作为原论文新增实验。[P, §6, pp.8–10]

### 1.3 源码覆盖清单

下面列出实际审读入口；链接均固定提交。长文件有范围说明，不将未读部分算成完成。

| 材料 | 实际阅读范围与用途 |
| --- | --- |
| [主 README][C0]、[training service README][C1]、[agent service README][C2]、`areal/__init__.py`、`areal/infra/__init__.py`、`areal/trainer/__init__.py` | 架构、目录、公开入口与导出；不是凭目录名推定运行路径 |
| [SWE README][C3]、[SWE 启动代码][C4]、[SWE YAML][C5]、[SWE agent wrapper][C6] | 全读；构建入口、数据、采样所有权和默认版本 |
| [Hermes README][C7]、[train.py][C8]、[config.yaml][C9] | 全读；显式 v2 在线路径 |
| [Hermes agent][C10] | 从文件头到结构化运行与 chat 转接；末尾纯 JSON/SSE 序列化尾部未完整展开 |
| [RL trainer][C11] | 初始化、prepare/train、发布、资源生命周期、后端选择、保存／评测入口，约 L1–1650；未审完整底层 optimizer/backend |
| [v2 inference controller][C12] | 初始化、服务创建、session/online callback、pause/version、workflow resolution，L1–1910；不是整个调度器生态 |
| [v2 workflow][C13]、[inference data proxy][C14]、[session][C15]、[router state][C16] | 全读；分组运行、反馈、导出、回调、路由和内存状态 |
| [InfBridge][C17]、[SGLang bridge][C18] | 全读；原始 token 生成、abort continuation 与版本记录；未审 vLLM backend 全路径 |
| [interaction types][C19] | L1–300 的张量构造与 reward normalization；未审所有多模态分支 |
| [interaction cache][C20] | 全读；prefix parent、retry orphan、回报传播和两类 export |
| [staleness manager][C21]、[workflow executor][C22] | 前者全读；后者 L1–240、L400–810，格式检查、提交／回收、暂停、动态 batch；未完整审所有执行 wrapper |
| [training dispatcher][C23]、[training worker engine][C24] | 全读；分发、RTensor、collective 入口和实际 actor 方法 |
| [training controller][C25] | L680 至结尾，HTTP 消费、clear_batches、权重连接／更新和 teardown；初始化细节结合 C1/C11 |
| [PPO actor][C26] | L1–920，优势构建、概率身份、loss 选择和 v2 HTTP adapter；未独立核完每个 loss 的所有 backend 分母 |
| [weight controller][C27]、[weight gateway][C28] | 全读；AWEX/disk 控制协议、错误返回和版本提交 |
| [recovery][C29] | L1–245，持久状态与 v2 显式限制；未声称所有 v1 恢复路径均已验证 |
| [Agent DataProxy][C30] | 全读；历史、透传、上游凭证、会话超时 |
| [weight controller tests][C31] | 全读；成功路径、未连接、HTTP 错误；其余 GPU integration 测试只确认入口，未执行 |
| [外部 lifecycle][S1]、[外部训练 YAML][S2] | lifecycle L1–610，含本任务实际 `run_agent_with_reward` 全路径、静态 gold/empty helper 与另一条 retry helper 开头；YAML 全读 |

代码的 `SPDX-License-Identifier: Apache-2.0` 保留在配套 probe。外部环境镜像、数据、模型与 Hermes 依赖的使用许可没有在本轮逐项做法律审查。

<a id="architecture"></a>
## 2. 架构全景：四种服务域，三种 DataProxy，不是一个大代理

### 2.1 名字相同，责任不同

| 服务域 | 主要责任 | 状态／数据在哪里 | 不是它直接负责的内容 |
| --- | --- | --- | --- |
| **Agent Service** | 对外提供完整 agent turn；适配 WS、OpenResponses、chat completions | Agent DataProxy 的对话历史；具体 worker 可缓存 agent 对象 | 不自行创建训练 session，不决定 RL 更新，不替工具沙箱隔离 |
| **Inference Service** | session-affine 模型请求、精确生成记录、奖励到达与轨迹 export | Inference DataProxy 的 InteractionCache、ready trajectories；Router 的会话归属 | 不自动观察全部工具副作用，不天然验证 reward 正确性 |
| **Training Service** | 把算法调用分发到实际 Megatron/FSDP 类 worker | 远程张量 storage、worker fetch buffers、模型／优化器状态 | 不拥有业务对话历史，也不等于自动决定何时改变 harness |
| **Weight Update Service** | 建立 train↔infer 参数布局与传输关系，执行更新 | pair registry、元数据 KV、AWEX/NCCL 或 disk 路径 | 不应仅凭 HTTP 成功就代表所有 worker 已装入正确版本 |

依据 C1、C2、C12–C18、C23–C30。源码中还有 guard：由 scheduler 分配资源，再在 guard 上启动／回收服务进程。**Guard 是进程管理边界，不是 agent 命令权限或 hidden verifier 的安全沙箱。**

### 2.2 Hermes 在线路径的完整流向

以下是根据实际代码整理的示意，不是原论文图的复制：

```text
用户／反馈调用方
  ├─创建 inference session → 得到 sk-sess-* 凭证
  └─提交 agent turn，附 inference base_url + session key
       ↓
Agent Gateway → Agent Router → Agent DataProxy → Hermes Worker
                              （对话历史）        （内部 tool loop）
                                                    ↓ 模型调用
Inference Gateway → Inference Router → Inference DataProxy → SGLang Worker
                                      （token/logp/cache）
                                                    ↓ 生成结果返回原 agent
反馈调用方 → set_reward → 封存一条 ready trajectory
                         ↓ ready callback（只传身份）
RolloutControllerV2 → 拉取/导出 → RTensor/metadata → Training Gateway
                                                  ↓
                                 Training DataProxy → DP/MP Workers
                                                  ↓ 参数更新
                                      Weight Update Gateway
                                                  ↓ AWEX/disk
                                       Inference Workers
                                                  ↓
                                         发布版本、继续服务
```

两个 gateway 和两个 session key 空间不能混淆。Agent Service 的 `session_key` 保持用户对话／worker 亲和；Inference Service 的凭证把模型请求绑定到训练侧 session。一次用户 turn 内可以有多次模型调用，也可以有内部工具执行。**用户 turn、agent tool iteration、inference request、segment、training row、prompt group 六者不是同一个单位。**[C2, C9–C15, C30]

### 2.3 服务化的实际收益与代价

代码把高层业务与训练计算解耦：既有 agent 可以保持工具循环，只改模型上游；大张量不要求全部经过总控制器；会话身份让反馈找到相应生成记录；训练端可复用数值实现，而不重复编写一个新的 optimizer。[C10, C13–C15, C23–C27]

代价也具体存在：更多启动／健康检查、RPC、凭证传播和错误类型；session affinity 约束负载迁移；内存 cache 与远程张量有多个回收点；同一“暂停”在不同层有不同效果。这里的设计价值是**职责清楚后能定点调试**，不是证明进程数越多吞吐越高。本文没有对应 HTTP、序列化或服务启动的独立微基准。

<a id="entries"></a>
## 3. 实际入口：SWE 示例与 Hermes 在线示例必须分别阅读

### 3.1 默认 SWE 示例仍是 v1，不能称为“已跑通的 v2 SWE recipe”

`examples/swe/train_swe_rl.py` 读取任务与配置，建立 `PPOTrainer`，将 `examples.swe.agent.SWEAgent` 交给训练循环。`qwen3_30b_a3b_grpo.yaml` 没有设置 actor/rollout 的 `_version`；相应配置字段默认 **v1**。`PPOTrainer._init_rollout` 只有在 `_version == "v2"` 时才创建 `RolloutControllerV2`。[C4–C6, C11 的 `_init_rollout`；`areal/api/cli_args.py` 的版本字段]

`_version` 是框架路径选择，与 policy/weight version 不同。SWE agent 是普通 async `run()` 对象，可被 v2 包装；这证明接口有接通的代码基础，**不证明原 YAML 已经启用 v2，或只改两行就完成所有兼容验证**。例如该 YAML 的 recover 设置与 v2 限制冲突，见 §10。

| 字段 | SWE 示例事实 | 解释 |
| --- | --- | --- |
| 模型 | `Qwen3-Coder-30B-A3B-Instruct` 本地路径 | 不是无后缀的 Qwen3-30B-A3B，也不是论文中新训练 checkpoint |
| trainer／inference | Megatron／SGLang，默认 `_version=v1` | 不能把 Hermes 的实际 v2 路径移植成它的运行事实 |
| 题目 batch / 每题样本 | `train_dataset.batch_size=4`，`n_samples=4` | 名义为四个任务组，不是每个 LLM call 一组 |
| rollout 控制 | concurrent=32，head offpolicyness=4 | 容量指标单位需结合 group workflow，不能当逐 token 年龄上限 |
| learner | lr=3e-6，Adam，bf16、fp32 grad reduce，gamma/lambda=1 | 属当前示例参数，不是论文消融最优点 |
| 目标 | decoupled loss，prox recompute，clip .2/.28，token ratio mask upper=5，KL=0 | 不因文件名 GRPO 就忽略行为／prox／当前策略三种概率 |
| 归一化 | group reward mean/std、eps=1e-5；adv norm 不启用 | 与 inference 侧可选 group normalization 是不同位置 |
| 预算 | gconfig total/max_new=131071；SGLang context=131072；workflow timeout=3600s | 与外部 agent 每次生成和工具步数预算分开 |
| 资源声明 | cluster 注释“4×8 GPU，2 节点训／2 节点推”；backend 为 `sglang:d4t8p1` 和 `megatron:(attn:d4p1t4c2|ffn:d4p1e8)` | 注释与并行字符串存在需要实际 allocation parser 核验的张力；本文未运行资源分配，不推算墙钟或断言一定调度失败 |
| 评测／恢复 | train/valid 使用待替换路径；evaluator 未配置有效周期；recover 为 auto | 不提供可复用的独立 held-out 成绩；不能直接迁移到 v2 |

该示例包含 Slurm、共享路径、环境 URL、镜像和多个 `/path/to/…` 占位符；**不是八卡开箱即用实测配方**。[C3–C5]

### 3.2 数据入口不等于任务质量验证

`get_swe_dataset(..., min_items=64)` 验证 `instance_id` 与 `problem_statement`；`split` 在这个函数中是名称／日志语义，并不自动把同一文件切为训练和验证集。小列表会整份重复直到达到至少 64 条，故 3 条可变 66 条，但独立任务仍只有 3 个。README 提到的 `eval_script` 不是这个 loader 的强制完整性验证。[C3, C4]

启动文件还定义了一个 mean-reward 阈值过滤函数，但不能仅凭定义就宣称它在主链生效；真实过滤入口来自传给 trainer/workflow 的配置。正式评测应保存独立任务 ID 与 split，不能用重复行数包装环境规模。

### 3.3 真正的 SWE 环境、agent 与 grader 在外部

AReaL wrapper 通过显式参数传递 `base_url`、session API key 和模型名，调用外部 `aweagent.lifecycle.run_agent_with_reward`。其价值之一是避免并发任务通过进程级 `os.environ` 竞争凭证，导致请求串到另一 session。[C6, S1 的 override 参数]

实际路径为：创建 AEnvironment 实例 → 检查环境 → 创建 SWE/CC agent → 运行工具循环 → 收集 patch → 求 reward → finally 释放环境 → 保存轨迹及 exit_code/stats。环境镜像和集群由外部服务承担，不包含在 AReaL 仓库里。[C3, S1]

在固定外部提交，registry 只有 `swe`、`cc`。上层配置／代码中出现 `oh/opencode/codex` 名称并不代表这个外部 pin 能直接运行它们。

**评分分支需要看配置，而不是函数 docstring。** `run_agent_with_reward` 描述在原环境评分，但实现根据 `rl_test` 分支选择：false 时 `env.get_reward`；true 时调用 `pipeline.test_patch` 的独立 SWE-bench 评测入口。实际 `min-swe-agent-train-top1.yaml` 为 **`rl_test:true`**，默认 `swebench@1.0.4`，attempts=10、startup=300s、reward=530s、patch=500s。本轮追到该调用边界，没有继续审阅 `pipeline.test_patch` 内部镜像权限／测试重放，因此**不能据此证明 fresh grader 的完整反作弊隔离**。[S1 L300–610, S2]

同一文件有 gold/empty-patch helper，说明可以做这些检查，不说明当前所有训练实例都已经通过。允许条件、测试／配置修改限制在 prompt 里出现，也不等于 runtime 强制执行。

### 3.4 实际采样参数由谁拥有

外部 SWE YAML 为 temperature=1、top_p=1、单次 max_completion_tokens=16384、step_limit=200，no-tool 与 multiple-tools 容忍各 20 次；工具输出超过 10,000 字符采用头尾截断。这不是训练过的 compaction policy。[S2]

上层 `SWEAgent` 接收并保存 `gen_args`，但所查 `.run()` 路径没有把它逐字段应用给外部 agent 的请求。评测代码把 `gen_args.temperature` 改为 0，**不能单凭这行证明外部实际生成是 greedy**。须在 proxy 记录的真实请求上核验。三个预算层分别是：learner/engine 总长度、单次 LLM 生成限制、外部 agent 工具步数／墙钟。[C4, C6, S2]

这也是一个可以复用的工程检查：记录“最终实际请求”，而不是只保存最外层 YAML。

## 4. 显式 v2 的 Hermes：在线反馈训练，不是自动 verifier SWE 训练

### 4.1 当前配置与执行角色

`examples/hermes/train.py` 直接创建 `PPOTrainer(config)` 后调用 `train()`，没有离线 task dataset，也不传入 agent workflow。在线模式中，learner 等待真实 agent session 的反馈与导出。Agent Service 是另行启动的服务，不由空 dataset 自动生成业务任务。[C7–C9, C11–C13]

| 字段 | Hermes 示例 |
| --- | --- |
| 模型 | Qwen2.5-1.5B-Instruct；不是 30B coding 训练结果 |
| 版本选择 | actor 与 rollout 显式 `_version:v2` |
| 资源 | local，1 节点 2 GPU，Megatron:d1 + SGLang:d1 |
| 输入方式 | online；无固定训练题单；不支持此模式下直接配置 valid dataset |
| batch / group | 1 / 1；reward_norm 和 adv_norm 均不启用 |
| reward | bias=-0.5、scaling=10；标量反馈来自调用方 |
| 导出 | individual；每次模型调用可能成为单独训练行 |
| 生成 | max_new=2048，context=32768；具体 agent loop 另有配置 |
| 恢复 | disabled，与 v2 明确限制一致 |
| 权重同步 | YAML 写 xccl，但 v2 非 LoRA 实际选择 AWEX |

因此“组大小 1”不必产生全零信号：这里没有减去自身作为 group mean。它不是把单样本照搬进 mean-normalized GRPO 的结果。

### 4.2 两个会话与三段责任

**调用方**先取得 Inference Service 的 `sk-sess-*`，在 agent turn body 中传 `inf_base_url` 和 `session_api_key`。**Agent DataProxy**只缓存并透传这些字段，注入 `metadata['areal_inference']`，不会偷偷向训练服务创建另一条 session。**Hermes worker**为该会话构建绑定上游的 `AIAgent`，后续 LLM 请求才真正经过 Inference Gateway。[C10, C30]

这保证了“业务会话”和“训练捕获会话”能够显式关联；但凭证绑定不是已验证的租户隐私、授权边界或训练同意管理。内部端点的网络可信前提仍需部署方处理。

### 4.3 “原生 harness”并非每一项产品行为原封不动

Hermes adapter 关闭自动 context files、memory、session DB 和 trajectory 保存，并以 DataProxy 重放的历史作为每个 turn 的输入。它把同步 `run_conversation` 放到 `asyncio.to_thread`，按 session lock 串行执行，同一 session 缓存一个 AIAgent；上游信息改变时重建该对象。[C10]

所以 Agent Service 文档中的“worker stateless”应理解为历史的协议所有权，而不是 Python 对象绝无会话缓存。

结构化路径只把 user、最终 summary 和实际发出的标准事件写回 Agent DataProxy 历史。Hermes 内部工具调用只作为 metadata 暴露，故意不发送不成对的 tool_call/tool_result 事件。raw chat passthrough 路径则不更新该历史，依赖调用方携带消息与 session affinity。[C10, C30]

**结果：Agent DataProxy 的历史不等于全部工具执行证据；Inference DataProxy 中捕获的模型请求也不自动拥有文件状态、工具副作用与完整验证记录。** 两条记录应各自命名，不假称实现了论文完整 ATDP。

<a id="trajectory"></a>
## 5. v2 workflow 与 session：从一次任务到一批训练数据

### 5.1 离线／任务驱动路径

v2 controller 接受带 async `run()` 的 agent 对象、类或 import path；**不直接接受传统 `RolloutWorkflow` 子类**。它将 agent 包成 `InferenceServiceWorkflow`，从配置注入 group_size、export_style、turn_discount、group reward normalization 和 retry-orphan 选项。[C12 的 `_resolve_workflow/_wrap_agent`, C13]

一次流程：创建 group session → 每个成员获得独立凭证 → 并发或串行执行 `agent.run` → 提交 reward → 导出并移除 session → 转训练数据。如果某成员抛异常，wrapper 记录失败并尝试提交 0；收尾导出后，整组返回 `None`。这与用户 agent **正常返回标量 0** 不同：后者可以是可消费的失败经验。

如果 agent 返回 reward 字典，该 wrapper 取最后插入项作为本次终局反馈，而不是将字典自动解释成逐步骤信用。本接口细节应与自定义 reward provider 对齐。

`drop_incomplete_group=True` 在当前 v2 入口会显式报不支持；不能因为别处有这个参数就声称支持所有 v1 的组处置。外部 model API 模式也限定 online/group=1，不是任意离线训练后端的替代。[C12–C14]

### 5.2 在线路径：reward 是封存触发，不只是一个训练数值

Inference DataProxy 为 session 维护 active InteractionCache、ready trajectories 和递增 trajectory ID。reward 到达后按 cutoff 窗口将 active 内容封存；ready callback 传输 session_id 与 trajectory_id，控制器再按身份 export。[C14, C15]

重复给已封存的最近交互设 reward，在当前特定分支会返回既有结果，并不会自动把新分数覆盖到已封存轨迹上。这里的 delayed reward 支持有具体生命周期边界，不能写成“任意晚到评分都可无损改写训练目标”。

ready 数据保留在内存；周期清理会跳过仍有 ready trajectories 的会话以免未消费数据立即过期。这能保护待拉取数据，但不是磁盘持久化，也不能恢复 controller 已丢失的通知身份。

### 5.3 Export 是破坏性消费边界

`SessionData.export_trajectory` 会先从 ready 集合 pop，再执行 cache export／张量构造；未指定 ID 时取最近的一条而非 FIFO。网络重试与 ready-notification 重试必须和这个语义一起理解。[C15]

如果 pop 之后转换报错、响应丢失或消费进程消失，仅重复 HTTP export 不自动保证拿回原数据。本文没有完整复现这些分布式故障，但源码没有在所查路径显示“导出后等待持久 ACK 再删除”的协议。**因此只能说存在重试机制，不能称 exactly-once durable training consumption。**

### 5.4 RTensor：总控制器传身份，worker 取实际张量

DataProxy 将 tensor 转成远程引用；reward 与部分 scalar metadata 保留在 envelope 中。Training DataProxy 做组感知分配，实际 worker 再取所属张量。这避免把全部多轮 tensor 反复通过主控制器搬运。[C14, C23–C25]

回收需要同时清远程 storage 与 worker fetch buffer。`GatewayTrainController.clear_batches` 收集 shard、删除远端、再向所有 worker drain；失败的 storage delete 跨调用保留有限重试，耗尽后报错。**只释放最初 DataProxy 对象，不意味着所有数据副本已经释放。**[C25]

## 6. 精确 token、树状轨迹与 reward：哪些是事实，哪些仍依赖假设

### 6.1 原始生成边界

SGLang bridge 使用 input_ids，开启返回 logprob，读取 `meta_info.output_token_logprobs` 的 token／概率对。缺少完整概率在正常完成分支会报错，而不是当成合法训练记录；abort-before-prefill 允许空结果。InfBridge 保留输出 token/logprob，并在中断后把已生成前缀接回下一次请求。[C17, C18]

这比重新 tokenize 最终可见回答有更强保真基础。但“记录到 token”仍不等于所有模板转换、概率温度定义、top-p 支持集、MoE routing 与 trainer 数值都已相同。本文未做 train/infer 对拍，也未审完客户端全部 tokenizer 路径。

外部 API 的 proxy 分支可保存字符串／SSE 内容；这不提供与本地 engine 相同的真实 sampled token 概率记录。**能代理某个模型不等于能直接对该服务的输出进行本地 on-policy RL。**[C14]

### 6.2 Prefix matching、concat 与 individual 是两个独立维度

InteractionCache 按消息前缀找 parent；默认 matcher 是严格 prefix，可注入自定义 matcher。匹配失败会告警并可选择性保存调试内容，不会直接把任意相似文本判成相同生成历史。[C20]

`chat_template_type` 影响 token 构造，`export_style` 影响哪些节点变成训练数据：

| 条件 | 代码行为 | 需要保留的边界 |
| --- | --- | --- |
| concat template + 已匹配 parent | 子节点继承父生成段的 mask/logprob/version，再追加新观察与生成 | 消息前缀关系不自动证明任意 renderer 都 token 等价 |
| 新观察／工具结果 | loss_mask=0、非采样版本标记 | 工具文字不是策略采样动作 |
| 当前生成 token | loss_mask=1，记录行为 logprob、version、turn ID | turn ID 与 policy version 是不同轴 |
| concat export | 只导出完整树的叶节点 | 共享父段可能出现在多个叶路径；不是自动完成无偏去重或训练树 attention |
| individual export | 导出各完整 interaction，可按配置传播 reward | 行数可能随工具调用数变化，不能用训练 row 数当独立 rollout 数 |

代码会检查 concat export 的 template 类型；不完整 interaction 会跳过，interaction key 不一致会报错。[C19, C20]

### 6.3 Retry orphan 是启发式归因，不是凭请求体就能恢复真实消费关系

可选 `drop_retry_orphans` 将相同 input messages 的生成分组。有后继 parent 证据时，删除未被后继采用的叶 sibling；全组都是叶时，保留创建时间最新者，时间相同则用插入顺序破同分。[C20]

这适合某类 SDK timeout 后重试，却不能自动区分“相同请求的重传”和“用户／agent 合法再次发起相同请求”。全叶时本来就缺消费证据，源码也将最新者描述为最可能的重试。

与本项目最相关的启示不是禁止这一启发式，而是：**若用它改变训练成员，必须知道它在哪个 workload 上有足够的请求／交付身份支撑。** 本轮没有运行真实 SDK 重试来测 precision/recall。

### 6.4 回报传播不是跨分支 GAE

`apply_reward_discount` 按 cache **反向插入顺序**执行 `current = current × turn_discount + local_reward`，不是按任意因果 DAG 做价值回传；未给 local reward 的节点按 0 处理。`drop_retry_orphans` 必须在传播之前，避免已删除节点影响其他节点的回报。[C20]

group reward normalization 的函数则先从每条 rollout 的最后有 reward 的 interaction 取一个标量，按组 mean 和 population std（unbiased=False，eps=1e-8）归一化，再赋给相应 interaction 并保留 original_rewards。[C19]

这与 actor 配置中的 group reward normalization 是两个位置。不能同时开启后就假定“只是同一件事的两种写法”：应逐配置核验有无重复归一化、分支叶复制和实际组边界。本文不把这些机制命名为 CompactionRL 的 cross-trajectory GAE。

<a id="async"></a>
## 7. 异步、背压与版本：必须按对象和时序理解

### 7.1 StalenessManager 主要是调度额度，不是逐 token 准入器

当前源码的可提交容量可写成：

$$
C_{submit}=\min\left(\max(1,C)-R,\ (K+v+1)\max(1,B)-A-R\right).
$$

其中 C 是最大并发，R 是 running，K 是 max_staleness，v 是控制器版本，B 是 consumer_batch_size，A 是累计 accepted 数。提交、完成、拒绝和版本推进更新计数；恢复时将 accepted 基线设为 vB，避免恢复后从零计数产生大幅超前派发。[C21]

这个式子限制可提前生成／接受的工作量。**它没有直接读取每条待训练 token 的真实权重版本并拒绝超龄数据**。一条很慢的旧工作流晚于新任务完成时，单凭容量约束不能推出其所有 token 都满足某个消费时年龄阈值。组 workflow、单个生成请求和 token 的计数还需分别解释。

### 7.2 队列、动态 batch 与过滤

WorkflowExecutor 的 producer 在未暂停且容量足够时取 pending task；consumer 回收已完成结果，按配置选取并把未选结果放回，不把全部 ready 结果无条件丢弃。`pause()` 停止新任务启动，**已经运行的 workflow 继续到完成**。[C22]

`dynamic_bs=False` 以足够多 accepted results 为目标，拒绝样本需要补齐；`dynamic_bs=True` 以尝试数（接受+拒绝）达到预算后结束，返回可小于 B 的 batch。两者不是纯吞吐开关：过滤率高时，它们改变实际样本数、等待时间和更新频率。

格式检查函数的 tensor 维度不一致有些只产生 warning，强制必备字段也不覆盖 reward/版本/评分身份的全部语义。因此这不能直接替代 rh2 的可信输入和训练消费验证。

### 7.3 三种暂停

| 调用层 | 实际作用 | 不等于 |
| --- | --- | --- |
| `rollout.pause()`／executor pause | 暂停新 workflow 提交 | 所有外部工具停止、所有在途生成完成 |
| `pause_generation()` | 对 inference worker/bridge 暂停与 abort；新请求在 bridge 等待 | 业务 agent 已保存可恢复 checkpoint |
| training/offload 资源交接 | 按共置策略释放 optimizer／weights／KV 等内存区域 | 不同后端上任何配置都自动保持缓存与模型一致 |

实际训练期间是否还能继续 rollout，要看 actor/rollout 是否分离、是否启用 offload 和控制器分支。服务化不是“永远不停止推理”。[C11, C12, C17, C28]

### 7.4 Partial generation 是内存内续生成，不是故障恢复

InfBridge 在 abort 后保留已经生成的 token/logprob，等待恢复，再提交完整前缀与剩余预算；每个段的版本在请求返回后按 bridge 当时的 `_version` 填入。abort 重试耗尽时使用 `length` 结束原因，可能进一步成为 `is_truncated`。[C17, C18]

这允许一条输出由多个版本的段组成，但版本标签是否对应实际执行权重，仍依赖权重更新／暂停时序。它不保存外部 sandbox 快照，也没有将进程重启后恢复同一 in-flight request 的能力从这个函数中证明出来。

## 8. 权重更新：传输、标签发布和恢复服务是三个动作

### 8.1 实际 transport 不能只看 YAML

PPOTrainer 初始化时，v2 非 LoRA 创建 AWEX 元数据；v2 LoRA 选择 disk。`actor.weight_update_mode` 在这个分支不是最终选择依据，所以 Hermes YAML 写 `xccl`，运行选择仍是 AWEX。LoRA/disk 路径存在也不表示本轮验证了整个 LoRA rollout/加载闭环。[C11, C25, C27, C28]

AWEX 连接先收集 train/infer 的并行布局与参数 metadata，按参数名合并各 FSDP rank 的 shards，建立通信关系。inference 的总 rank 数由每个 engine 的并行大小乘 engine 数得到；rendezvous 端口放到实际 rank0 所在的 inference guard。控制 HTTP 搬运的是元数据和命令，不是宣称完整权重经 JSON 发送。[C25, C28]

disk 路径保存不含 optimizer 的 HF 权重，再通知推理加载；LoRA 保留有限版本并 best-effort 卸载过旧 adapter。元数据布局、权重内容、版本标签和 KV 处理必须共同一致。

### 8.2 当前 v2 成功时序

固定代码中，最外层 `_update_weights_and_publish_version` 先调用 actor.update_weights，然后发布 actor/critic/rollout/eval 的版本。v2 GatewayTrainController 的内部顺序则是：

```text
pause_generation
→ WeightUpdateController.update_weights
→ continue_generation
→ 返回上层
→ actor.set_version
→ rollout.set_version（及其他配置角色）
```

因此 **v2 的恢复生成发生在外层版本发布之前**。CPU probe 验证了这一调用次序；真实系统中是否存在旧标签／新权重的请求窗口，需要结合 pending requests、backend pause 实现和并发调度再测，不能从顺序单独宣称已经出现错标 token。v1 AWEX colocate 有另一条“发布后恢复 KV/生成”分支，不能把它的顺序借给 v2。[C11, C25, §11 探针]

### 8.3 逻辑失败可能没有穿透 HTTP 边界

Weight Gateway 捕获 transfer exception 时，返回 `WeightUpdateResult(status="error", ...)`，但该 endpoint 没有把这种业务失败改成非 2xx。WeightUpdateController 只检查 HTTP status，再返回 typed result。GatewayTrainController 没有检查 `result.status`，照常 continue_generation 并记录 completed；外层随后继续 set_version。[C25, C27, C28]

**这是一条可定位的固定提交控制流缺口。** 本轮以相同函数体、HTTP/worker 桩输入验证：HTTP 200 + `status=error` 不抛异常，恢复生成并推进标签；HTTP 500 对照则抛异常、不推进标签。没有真实失败的 NCCL 传输，因此不宣称复现了部分权重损坏、训练崩溃或具体能力回退。

修复应先明确成功合同：接收所有 worker 的实际完成、检查返回版本与错误，再决定发布和恢复。简单加 `finally: continue_generation()` 未必正确——不完整权重下自动恢复可能比保持暂停更危险。是否涉及幂等重试或重新初始化，需要后续真实 backend 设计，不能用这次阅读直接批准。

### 8.4 部分 worker 控制失败与整组训练 RPC 的策略不同

Inference Controller 对 pause/continue/version 等扇出操作，会收集异常；部分 worker 失败只记录，**全部失败才 raise**。Training dispatcher 对计算 RPC 的 worker 失败则会使整个调用失败。[C12, C23]

控制面有时可以容忍部分可用性，但训练中的权重／版本发布需要判断是否允许幸存与失败 worker 继续共同接收请求。这是值得做故障注入的边界，不应仅依赖“至少一个成功”。本文没有复现 worker 下线隔离或自动恢复，不能声称当前所有失败 worker 一定继续服务。

<a id="learning"></a>
## 9. Training Service：分发、概率身份与实际梯度

### 9.1 主控制器的 world_size=1 不代表只训练一张卡

GatewayTrainController 向高层暴露兼容属性，controller 自身可用 singleton process group；真正的 DP/TP/PP/CP 布局在远程 worker。Training DataProxy 对 list-of-dict batch 做分组保留的切分／均衡，同一组分配索引应用到所有相关参数；原位置映射用于恢复输出顺序。[C23–C25]

non-head rank 也会收到调用入口以进入 collective，而不是只让 DP head 调用可能阻塞全体的计算。训练 worker 将 RTensor 本地化、在专用 engine 执行线程调用数值方法，输出再远程化。算法与 RPC 包装分离，是这一层主要可复用的设计。[C24, C26]

### 9.2 一次训练迭代的顺序

按 PPOTrainer 主循环：

```text
prepare_batch（离线任务或在线反馈）
→ 按条件 forward ref/critic/teacher
→ prox logprob（依配置重算或近似）
→ compute_advantages
→ actor.ppo_update + lr scheduler；可选 critic update
→ pause 新 rollout 提交
→ 权重更新与版本发布
→ save/evaluate/统计/clear_batches
→ resume 新 rollout（若仍有下一步）
```

ref/critic/teacher 的配置存在不意味着每次都使用，例如 KL=0 的 ref 不应被凭 YAML 声称为额外 KL 正则阶段。具体共置与 offload 会在该顺序中插入资源交接。[C11]

### 9.3 三种概率与截断语义

PPOActor 在 decoupled loss 下保留 rollout 行为 logprob，另有 update 前 proximal logprob，以及训练 forward 得到的当前 logprob。当前函数还支持近似 prox、CISPO/SAPO/MOPD 等选项；**本文只追实际示例选择，不把同文件全部方法算作这次训练使用**。[C26]

mask/logprob/turn_id 会 shift 到 next-token 预测位置；观察 token 不产生 policy gradient。无 critic 时 value 用 0；选择 turn-level GAE 则要求 turn_id，不能只按 mask 的连续片段盲猜 turn。

`mask_no_eos_with_zero` 的实际含义是把截断序列的 **outcome reward 置零**，不是删除原组，也不是清空所有 token 梯度；仍可能有 KL 等其他项。`is_truncated` 优先来自明确 metadata，legacy 无此字段时才根据 padded width 回退。它与 SkyRL-Agent 的“保留 reward/advantage、屏蔽自身梯度”不是同一种训练规则。[C26]

`_ppo_update` 传给 engine 的 loss_weight_fn 是有效 mask token 数；不同 microbatch／DP 后端如何合并该权重，本轮未做完整数值审计。不能根据函数名字给出未经验证的全局归一化公式。

### 9.4 相同提示、不同 row 数：需要独立测试的优化单位

v2 group reward normalization、prefix leaf fan-out、individual 导出、actor 的实际 `traj_group_sizes` 分别位于不同层。它们足以提供灵活接入，但不能凭元数据字段存在就证明所有非线性工具循环都保留了预期的 prompt group 和 rollout 权重。[C13, C19–C20, C23, C26]

针对特定 workload，最小检查是：固定同一组逻辑轨迹，只改变合法片段划分／padding／分片，比较 reward、advantage、mask 和声明目标的梯度。若目标本来按 token 加权，不应错误要求每条长短轨迹等权；先写清目标，再做等价性测试。

<a id="failure"></a>
## 10. 故障、取消、重试、恢复和评测的边界

### 10.1 失败语义矩阵

| 边界 | 当前固定代码行为 | 需要避免的误读 |
| --- | --- | --- |
| SWE 内部环境／agent／评分异常 | 外部 helper 多处捕获、保留 exit_code/stats、标量 reward 默认0；上层 wrapper 又捕获部分异常返回0 | 所有0都是模型诚实解题失败，或所有 infra failure 已被过滤 |
| 外层 episode timeout | `asyncio.wait_for` 超时抛出 | 取消 Python coroutine 自动证明外部 sandbox/阻塞线程均已停止 |
| v2 group 成员异常 | 清理并导出后整组 None | 与正常 reward0 一样，或有 `drop_incomplete_group` 参数就代表当前可用 |
| HTTP 重试 | 部分传输入口有 retry | 所有 endpoint 幂等、所有业务动作可以安全重复 |
| inference abort | 内存内续 token，受剩余预算和重试次数限制 | 冷启动后恢复完整 agent／环境状态 |
| ready 通知满队列 | maxlen deque append 会淘汰旧描述符，仍 ACK ok | “队列有上界”自动等于正确背压 |
| export | ready pop 后再构造／返回 | HTTP重试等于 exactly-once 消费 |
| 权重业务失败 | 当前可能被 HTTP200 包住，上层继续 | transport成功代表weight成功 |
| version/pause 部分扇出失败 | 只全部失败才 raise | 所有仍参与 rollout 的 worker 都已一致 |
| 远程张量回收失败 | storage 与 worker buffer 分两处清、有限跨步重试后raise | controller不再引用即无泄漏 |

其中 export、版本标签窗口、取消后的实际副作用仍是待系统验证的风险；§11 明确限定已执行测试。

### 10.2 v2 当前显式不支持通用训练恢复

`RecoverHandler._ensure_recover_supported` 遇到 GatewayTrainController 会抛 `NotImplementedError`，提示关闭 recover 或使用 v1。Hermes 配置关闭恢复；默认 SWE 的 auto-recover 则不能不作处理就迁移为 v2。[C29]

已有 save/load API 不能替代恢复协议。至少有四种不同状态：模型／优化器／dataloader、controller 队列、推理 session/cache、业务 agent/sandbox。Router 与 DataProxy 的内存会话在进程重启后不会因 checkpoint 存在自动回来。本文未找到、也不主张完整跨这些状态的原子恢复。

析构有正面设计：训练 worker 先一起销毁 engine／process group，再退出进程，避免 rank0 TCPStore 先死造成其他 rank 的 teardown 问题；各资源回收路径尽量在异常下继续。但这属于**有序关闭**，不是对中途失效进行容错恢复。[C25]

### 10.3 评测事实与资源披露

| 证据 | 可以说什么 | 不可以说什么 |
| --- | --- | --- |
| 配套论文 | 在线权重更新原型与架构论证 | 该架构已带来某个精确 SWE 提升或单节点加速比 |
| SWE 示例 | 模型／优化器／任务接口／部署依赖可审读 | 本文已运行训练、构建所有镜像或重现 benchmark |
| Hermes 示例 | 小模型、真实 harness adapter 与在线标量反馈链 | 已有可靠的自动奖励、安全提升或长期个性化实验 |
| 当前训练代码 | 支持多 backend 与多目标的公开实现 | 同一任务跨 backend 数值等价已实证 |
| 本轮 CPU probes | 指定函数体和输入下的控制流行为 | NCCL可靠性、实际权重内容、梯度或模型能力 |

未披露／未取得：这条 v2 SWE 工作负载的最终任务 manifest、冻结镜像、精确依赖锁、任务资格统计、训练 GPU-hours、CPU/API总成本、held-out主结果、多种子和控制变量消融。参数表不应被当成这些事实的替代。

<a id="probes"></a>
## 11. 本轮实际执行的 CPU 控制流探针

文件：[可运行脚本](probes/areal_v2_control_flow_probe.py)；[实际结果 JSON](probes/areal_v2_control_flow_results.json)。运行环境 Python 3.13.5，无第三方训练依赖：

```bash
python docs/harness_improve/external_paper_references/reading_notes/probes/areal_v2_control_flow_probe.py \
  --output /tmp/areal_v2_control_flow_results.json
```

脚本把从固定 connector 源码手工转录的 **4 个完整方法体**装入隔离 namespace，HTTP、worker 和 logger 使用桩；不是把结论重新写成一个人为 toy 算法。四个方法为 C27 的 `update_weights`、C25 的 `update_weights`、C11 的 `_update_weights_and_publish_version`、C12 的 `_handle_online_ready_callback`。源码归属和 Apache-2.0 标识在文件头保留。

本轮没有本地完整 upstream checkout，因此 **source-AST checkout 校验未运行**。脚本提供 `--source-root /path/to/AReaL`，会要求 HEAD 与本 pin 一致、比较方法 AST 并验证队列 maxlen；只有实际跑过后才能追加这一完成状态。

| 案例 | 本次结果 | 证据含义 |
| --- | --- | --- |
| 200 + `status=ok` | 恢复生成；actor/rollout标签到1 | 正常对照 |
| 200 + `status=error` | 同样不抛异常、恢复生成、标签到1 | 逻辑失败未被上层成功条件拦截 |
| HTTP500 | 抛FakeHTTPError；维持暂停；标签仍0 | 区分 HTTP 失败与业务失败 |
| 成功更新顺序 | continue_generation 早于 rollout.set_version | 顺序已验证；真实错标竞争窗口未验证 |
| 无 waiter 时1025个ready callback | 全部ACKok；只保留1024项，最旧保留ID=1 | 第0描述符被淘汰；不是已经测得真实训练丢样本率 |
| 相同callback两次 | 产生两个相同导出描述符 | 该handler没有去重；第二次真实export行为未在本探针运行 |
| 缺trajectory_id | 明确raise | 输入错误对照 |

**7 个案例通过，是指断言成功刻画当前行为，其中包含不希望发生的行为，不是 AReaL 正确性认证。** 通知过载推论还需要结合 DataProxy 的“HTTP成功即标已通知”、ready保留和实际消费者进度；本轮未启动这些服务。

所查上游 `test_wu_controller.py` 覆盖成功、未连接、HTTP500，没有在该文件中覆盖 HTTP200+逻辑error及最外层版本发布链；不据此声称整个上游测试库都没有相似测试。[C31]

### 11.1 如何变成有价值的上游贡献候选

最清楚的候选是先补“业务error不能成功发布新版本”的回归测试，再决定由哪个控制器抛异常／维持暂停。第二候选是 ready callback 明确背压和去重，使 ACK 与保留承诺一致；不必一开始建通用WAL平台。版本发布顺序与部分worker失败需要真实backend故障注入再定方案。

这些仍是固定pin的候选。提交外部issue/PR前需再检查最新主分支、现有issue/PR及维护者期望；本轮没有向外部仓库发送问题或修改。没有为了“必须找到bug”而将所有架构取舍都标成缺陷。

<a id="project"></a>
## 12. 对 RepoHarness 项目一的启示：优先少量验证与简化

项目映射基于 [CURRENT-STATE-BRIEF](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md) 的 2026-09-05 快照，读取commit为本稿 §1 所列；它是导航而非最新实验定案。当前项目复用 miles/SGLang/外部 harness，rh2 负责环境、评分和训练消费可信性。本次不建议换成 AReaL，也不将论文里的完整企业控制平面变成八卡项目前置任务。

### 12.1 三个最值得迁移的工程思想

**沿实际入口验证，不按仓库功能表归因。** SWE默认v1、Hermes显式v2、gen_args未成为最终外部请求、weight_update_mode被v2分支替代，都是“字段存在≠路径生效”的具体例子。rh2可把已有启动核验和运行快照对准实际对象类型、最终请求参数与消费位置，不必新增通用配置治理系统。

**明确数据对象与反馈对象。** 业务会话、模型请求、逻辑rollout、分支叶、训练行和远程tensor应保持可追踪关系；runtime失败的标量0应与正常失败分开。AReaL的explicit per-session credentials、remote tensor metadata、group前置归一化提供实现参照，但不能直接代替rh2自己的评分隔离和组合同。

**控制完成条件与数据平面完成条件一起验证。** HTTP200、通知已ACK、controller version已更新、源storage已删除，都只是某一层事实。权重安装、样本仍可导出、所有参与worker一致和fetch buffer回收还需自己的证据。现有miles相关窄测试应优先扩展这些实际反例，而不是重新造服务平台。

### 12.2 适合本项目的小实验与责任边界

| 候选 | 低成本先验证什么 | 何时需要GPU／学习结果 | 谁应承担实现 |
| --- | --- | --- | --- |
| 失败更新不发布版本 | 注入逻辑error、部分engine错误、错误版本回执 | 多engine真实权重/标签一致性需要GPU；无须先长训 | 优先上游更新／通信层，rh2检查实际响应 |
| 轨迹切分与组消费 | 固定逻辑组，改变合法切段，检查mask、reward、分母 | 同样本梯度需要短GPU；若改变目标再做学习对照 | 复用miles样本层，rh2仅验证适配增量 |
| 取消／重试身份 | 相同请求两次、timeout后重试、后继引用、export响应丢失 | 特定backendabort/caching需短GPU，工具副作用需沙箱 | 在已存在生命周期边界补测试，不建新全域IR |
| 背压与无效工作 | 固定trace回放，测ready保留、consumer阻塞、拒绝／补齐数量 | 真实吞吐需相同任务与资源；改变采样分布后补质量 | 上游调度主责；rh2记录任务/丢弃分布 |
| 内存／资源释放 | 导出、评分、训练后各owner状态与失败路径 | 显存与多rank缓存回收需要实际worker | 优先复用上游clear/teardown，避免重复持有 |

### 12.3 当前不值得直接复制的内容

多套gateway/router/guard、持久在线用户反馈、跨租户隐私控制、动态多surface自演化不是当前RepoHarness必须具备的能力。单节点离线SWE训练可用更简单的进程边界实现相同责任；是否服务化应由部署、隔离和复用需求决定，不由架构图复杂度决定。

AReaL的v2恢复限制也提醒我们：**更多服务边界会扩大状态协调问题，并不自动增加可靠性。** 反过来，能定位并验证这些问题，本身就是后训练系统工程能力，不必把每个修复都包装成新模型能力命题。

<a id="limits"></a>
## 13. 已读证据、局限与后续定点复核

| 问题 | 本轮状态 | 不应填补的结论 |
| --- | --- | --- |
| 论文全文／关键图 | 13页全部读；关键图与设计／局限页目视检查 | 不是完整ATDP已实现，亦无新增性能实验 |
| 当前服务代码 | 固定pin、明确路径和读取范围 | 不代表全仓无其他实现或后续主分支不变 |
| 默认SWE与显式v2 | 入口、配置、后端选择已对照 | 没有执行迁移后SWE任务 |
| token/prob/版本 | 桥接、cache、types、消费已静态追踪 | 没有跨engine同token logprob/梯度对拍 |
| 外部SWE评分 | 追到实际rl_test分支与调用参数 | test_patch内部隔离、镜像构建与全集验证尚未审计 |
| 7个CPU案例 | 实际运行、结果保留 | 未启动HTTP服务、CUDA、NCCL或sandbox；不是独立复现论文 |
| 稳定性与吞吐 | 提出具体测量边界 | 无八卡速度估计、无学习曲线和cost-to-score |
| 恢复与隐私 | 显式v2恢复限制；多处内存状态 | 不代表企业级持久恢复或完整隐私／训练资格管理 |
| 独立审查 | 仅作者自查 | 不继承前两批独立review标签 |

后续最有价值的复核不是再读一次整篇：先用完整固定checkout跑配套AST校验；再沿SGLang pause/abort真实实现做版本窗口故障注入；如准备实际采用SWE资产，再专门读外部test_patch及镜像。以上是明确未完成项，不是本轮已经执行的工作。

[作者自查与交付记录](reviews/areal_v2_services_self_check_20260908.md)记录实际检查、修正和文件范围。本稿为本专题维护入口，未改其他来源笔记、共享索引、项目实现或训练定案。

## 14. 固定来源索引

所有 C 编号属于 AReaL `f289b989…`，所有 S 编号属于 AReaL-SWEAgent `f144900…`。链接后的文件／符号定位在各节与覆盖表中给出；没有使用当前聊天专属引用代替可回访来源。

[P]: https://arxiv.org/pdf/2607.01120v2
[C0]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/README.md
[C1]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/v2/training_service/README.md
[C2]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/v2/agent_service/README.md
[C3]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/examples/swe/README.md
[C4]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/examples/swe/train_swe_rl.py
[C5]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/examples/swe/qwen3_30b_a3b_grpo.yaml
[C6]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/examples/swe/agent.py
[C7]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/examples/hermes/README.md
[C8]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/examples/hermes/train.py
[C9]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/examples/hermes/config.yaml
[C10]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/examples/hermes/hermes.py
[C11]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/trainer/rl_trainer.py
[C12]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/v2/inference_service/controller/controller.py
[C13]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/v2/inference_service/controller/workflow.py
[C14]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/v2/inference_service/data_proxy/app.py
[C15]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/v2/inference_service/data_proxy/session.py
[C16]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/v2/inference_service/router/state.py
[C17]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/v2/inference_service/inf_bridge.py
[C18]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/v2/inference_service/sglang/bridge.py
[C19]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/experimental/openai/types.py
[C20]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/experimental/openai/cache.py
[C21]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/infra/staleness_manager.py
[C22]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/infra/workflow_executor.py
[C23]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/v2/training_service/data_proxy/dispatcher.py
[C24]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/v2/training_service/worker/engine.py
[C25]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/v2/training_service/controller/controller.py
[C26]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/trainer/ppo/actor.py
[C27]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/v2/weight_update/controller/controller.py
[C28]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/v2/weight_update/gateway/app.py
[C29]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/utils/recover.py
[C30]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/areal/v2/agent_service/data_proxy/app.py
[C31]: https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/tests/v2/weight_update/test_wu_controller.py
[S1]: https://github.com/areal-project/AReaL-SWEAgent/blob/f144900d5e0a019bf5381b624c442b49999ffa4d/aweagent/lifecycle.py
[S2]: https://github.com/areal-project/AReaL-SWEAgent/blob/f144900d5e0a019bf5381b624c442b49999ffa4d/aweagent/configs/1_0_0/min-swe-agent-train-top1.yaml
