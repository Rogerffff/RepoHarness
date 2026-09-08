# Prime 栈源码精读：从环境轨迹到不同训练目标

**日期：2026-09-08。对象：prime-rl × verifiers × renderers，并沿一个真实 SWE 配置补读 prime-envs。** 本文追踪配置、任务、episode、trace、消息图、训练样本、打包张量和最终 loss 的实际关系，而不是逐仓库罗列功能。最有用的设计是：将执行事实、组信用、目标成员与梯度消费分开；同一工具输出可以是不可用于 policy gradient 的 observation，却是 ECHO 的合法 CE 目标。最重要的边界是：这些分层不自动证明环境评分可信，也不保证任意算法、门控、采样与教师可以自由组合。

本次完成定界源码精读、作者自查及 **19 个自建 CPU 语义检查**；**未安装并运行完整 Prime 栈，未执行上游测试，未做 GPU／sandbox／模型训练复现，没有独立 reviewer**。源码能力、博客主张、读者推导和项目候选分别标注。本文不批准更换 miles、升级 rh2 或新增训练目标。

导航：[版本与范围](#versions) · [架构与真实入口](#architecture) · [数据单位](#units) · [环境与评分](#environment) · [token 与图](#tokens) · [八种算法](#algorithms) · [门控与供给](#admission) · [打包与 loss](#loss) · [异步边界](#async) · [检查与适用性](#checks) · [项目映射](#project) · [源码定位](#sources)

<a id="versions"></a>
## 1. 固定的是一套依赖组合，不是三个各自最新的仓库

| 对象 | 本次固定版本 | 身份与用途 |
| --- | --- | --- |
| prime-rl | `04a61d3b75c3c99f263b2c133e822f998909adf7` | 2026-09-07 的 main 快照；pyproject 的版本字段为 0.9.0，**不等于纯 v0.9.0 release** |
| verifiers | `828488fffe31aa3332b9d1bd4bd9ee320e375cf1` | prime-rl 的实际 gitlink，不使用独立 main 的更新替代 |
| renderers | `f91c3e7061ce50ea405cdf54fd419a45cb51a152` | 同上，负责本次模型模板、解析与 token 归属 |
| prime-envs | `1f1e050ab0cd273bca39eed5c3e5315e6a8ae9d1` | 同上，只扩读 R2E-Gym 任务实现以闭合 SWE 数据／评分入口 |
| RepoHarness | `32b615c4e4f869b448174e5974e7a8d29fc4612c`，`miles-migration` | 项目读取基线；写入可能基于更新分支头，不能将其他线程后续改动视为本轮已审 |

依赖关系来自 [.gitmodules][P02]、[pyproject][P01] 和 [packages git tree][P00]。同一组合还固定 pydantic-config 与 prime-kernels 子模块；本轮没有审查其完整实现。Python／Torch／vLLM 依赖应按这一快照安装，不能把本地 Python 3.13、Torch 2.10 CPU 的参考检查称为其正式运行环境。

**配套官方文章。** 2026-07-05 的 [The Algorithms Layer][B01] 用 sampling、scoring、group credit 和 loss streams 组织六种算法。它提供设计动机，不是本次九月代码的完整说明：当前枚举已经增加 hierarchical GRPO 和 RAE，存在 curriculum、typed episode 与更细消费路径。文章中的未来计划要回代码核对。本文没有重新精读所有被这些算法引用的论文；尤其不会用同名算法论文补写当前实现。

### 1.1 阅读范围及不能声称的事情

完整追读重点为：选定 TOML 及配置默认；八个 orchestrator 算法；group finalize、curriculum、train sink；trace→sample；batch wire；packing 主路径；三分量 loss 与真实 trainer 归一化／反向调用；TrainClient 和 Qwen3 renderer；消息图提交与分支；一个 R2E-Gym taskset；相关测试。

对较长文件按主路径定点阅读，范围详见 §13。没有逐行审计所有模型 renderer、推理内核、完整 launcher、eval checkpoint 状态机、所有 runtime、安全隔离、多模态处理器和分布式 collective 实现。**“从环境轨迹到训练目标的路径读通”不等于“整个四仓库均审计完成”。** 没有训练曲线或等预算对照能从源码本身产生，因此本文对算法支持主要给出代码层证据，不宣称在本项目硬件上有效。

<a id="architecture"></a>
## 2. 架构：事实由环境产生，目标由算法解释，参数由 trainer 更新

```text
rl TOML + 配置解析／继承
  ├─ trainer：模型、并行、优化器、loss 实现
  ├─ inference：policy 的模型服务、token API、权重接收
  └─ orchestrator
       ├─ 加载 Taskset → 选择 Task → 派发 episode group
       ├─ GenerationSource：live policy 或 frozen generation endpoint
       └─ EnvClient ──task_data/client/model/sampling──> verifiers EnvServer
                Env.run(task, agents)
                  → Agent = harness × model client × runtime
                  → TrainClient → renderer → token-native generate
                  → PendingTurn/MessageNode/ModelCall → Trace(s)
                  → task finalize / reward → Episode
       Episode → finalize_episode → 等待组终态 → finalize_group
               → curriculum.observe → admission gates
               → trainable branches → TrainingSample + 三类权重流
               → pruning / buffering / stale check / batch selection
               → packing → per-rank MicroBatch → transport
  trainer：forward → 对齐 token logprob → 三分量 loss
           → 全局计数归一化 → backward → optimizer → 发布权重
```

这是所读代码的调用关系概述，不代表每个箭头都进行了实际服务运行。[环境客户端][P05]明确将 taskset 放在 orchestrator 一侧，服务器只接收经类型化的任务数据并执行 agent；不是每个 worker 再下载一份完整数据集，也不是仅凭本地行号读取任务缓存。[Env][V01]、[Trace][V02]与算法层各自承担不同事实。

| 层 | 本次代码拥有的职责 | 不应由此推断 |
| --- | --- | --- |
| prime-envs Task/Taskset | 任务加载、setup、工件捕获、具体 reward/validate | 所有任务都经过同样严格的隔离或质量验证 |
| verifiers | Env／Agent／Runtime 协作，调用记录、消息图、评分与错误表达 | 已保证每个 reward 与用户意图一致 |
| renderers | 确定模板 token、原始输出解析、历史桥接、body/scaffold 归属 | 任意模型/API 都能无损映射到该接口 |
| prime-rl orchestrator | 任务供给、算法信用、loss routing、组终态、准入、staleness、发批 | 采样分布或门控选择一定最优 |
| trainer | packed forward、概率、各分量 loss、全局缩放、参数更新 | 上游错误 metadata 可由 loss 自动纠正 |

### 2.1 主案例：仓库中确实存在的 Qwen3-30B-A3B SWE 配置

[examples/advanced/qwen3-30b-a3b/swe.toml][P03]选择：

| 字段 | 文件显式设置 | 正确解释 |
| --- | --- | --- |
| 模型 | `Qwen/Qwen3-30B-A3B-Thinking-2507` | 不是自动对应 rh2 所有 checkpoint 的模板与能力 |
| 序列长度 | 131072 | trainer／orchestrator 的训练序列预算，不等于任务累计 token 无上限 |
| 部署 | 2 train nodes + 2 infer nodes | MultiNode 默认每节点 8 GPU；按默认即 32 GPU 规模，不是八卡 recipe |
| 训练 | custom model、FA3、EP8、CP2、compile、activation offload、lr=1e-6 | 只是配置，未在本轮硬件上启动 |
| 供给 | batch_size=512、max_off_policy_steps=16、initial_inflight=1024 | batch 单位需回 TrainSink，不能直接认定 512 个独立题目 |
| 训练来源 | `r2e-gym` taskset、`bash` harness | 没有在此文件覆盖数据集名称；需要读取 taskset 默认 |
| 评测 | `swebench-verified`、bash、interval=25 | 不是独立验证了该配置对应公开成绩 |
| 权重与推理 | NCCL、TP8 | 完整运行仍需要对应 SLURM、服务与资源配置 |

**不把示例当作自包含成功配方。** 该文件未显式设置 `group_size`，而当前 OrchestratorConfig 默认是 1、算法默认 GRPO；source 未显式指定组大小时继承该值。没有外部 override 时，纯 singleton centered reward 产生零优势。文件也没有给出其多节点验证器所要求的完整 SLURM 设置。这里只能说“必须检查 launcher／额外配置最终如何解析”，不能因为静态默认有这个结果，就声称复现过失败训练。应先用完整依赖环境的 `--dry-run` 保存 resolved config。[P03][P04][P06]

### 2.2 辅助小案例：明确给出组大小与 renderer 的配置

[examples/basic/reverse-text/rl.toml][P07]显式给出 max_steps=20、seq_len=2048、batch=128、group=16、每次最大输出128、`null` harness、`subprocess` runtime、每5步评测256例，模型为 `PrimeIntellect/Qwen3-0.6B-Reverse-Text-SFT`。其显式选择 `prime-qwen3` renderer，因为改名 checkpoint 不在 exact-match 表中。

这个小案例提供更便宜的接口参照；本文没有启动它，也不拿它证明真实多轮 SWE 成功。**真正该复用的是保存 resolved config、沿实际 source 追依赖的方法，不是某个默认 batch 数。**

<a id="units"></a>
## 3. 八种单位：为什么一条 rollout 不能始终等于一行训练数据

| 单位 | 所读实现中的含义 | 关键位置 |
| --- | --- | --- |
| Task | 具有数据与 key 的任务实例；可来自有限序列或无限生成器 | [Env/taskset loading][P05] |
| Group | 同一任务的多次 episode 请求；完成、请求失败和取消共同决定组终态 | [TrainSink][P08] |
| Episode | 一次 environment run，可包含多个角色／agent trace | [Env][V01]、[Env.run wrapper][P05] |
| Trace | 一个 agent 的图、调用、reward、错误与运行信息 | [trace.py][V02] |
| ModelCall | 一次实际模型服务调用，带 usage 和图节点关系 | [trace.py][V02] |
| MessageNode | 被模型看到或实际生成的一段消息 token，带物理／语义父关系 | [graph.py][V03] |
| Branch / TrainingSample | 一条物理 root→leaf token 序列；去重后决定哪些位置产生目标信号 | [trajectories.py][P09] |
| MicroBatch | 多个样本 packed 后的前向单元；序列边界、各 token stream 与身份并行保存 | [types.py][P10]、[batch.py][P11] |

**信用在 graph 展平前计算，不能对展平后的 branch 行重新当作独立 rollout 求均值。** 同一逻辑 trace 因重分词、上下文压缩、分叉而产生多行，是表示变化，不应无意改变其同题统计身份。

### 3.1 共享前缀：去重存储、去重梯度、去重计算是三件事

`trace_to_samples` 按 trainable branch 展平，对 shared sampled node 按对象身份去重，并分别处理各 loss stream。已经在前一条 sample 上训练过的前缀 token，在后续 sample 中仍作为上下文存在，但不再次承接同一分量梯度。工具 observation 的 CE 权重也需要独立去重，不能只去重 action mask。[P09][P13]

读者示例：两条长度4的分支共享3个节点，总前向 token 位置为8、唯一节点为5；去重后3个 action 节点产生一次 RL 信号，公共 tool body 只承接一次 CE。**这仍是8个前向位置，不是自动获得 prefix-tree attention 计算复用。** 19个检查中的第5项验证的是这一语义模型，不是 GPU 时间。

也不能将去重后统计称为“每条 trace 等权”：token-level loss 会让 action 更多的 trace 提供更多目标成员；去重避免的是同一节点因表示复制而重复训练，并不消除所有长度权重。

### 3.2 分支与实际开销不应混用

当前 Trace 的 `usage` 按实际 ModelCall 汇总一次；`num_output_tokens` 和 `num_total_tokens` 则按 branch 视图求和，公共调用可能出现在多条分支中。`num_input_tokens` 又使用自己的增量和去重逻辑。GRPO 长度惩罚读取的是 `num_total_tokens - num_output_tokens`，不是直接调用这个去重 input 属性。[V02][A02]

因此图拓扑变化可能改变长度惩罚代理量，即便实际付费调用未等比例变化。它可能是作者有意选择的训练预算代理，也可能需要调整，**不能不加区分地把这些字段称为唯一 token 成本或实际服务账单**。

<a id="environment"></a>
## 4. 环境、评分与错误：算法不拥有任务真值

### 4.1 R2E-Gym 的实际默认不是文件头的文字

[prime-envs 的 R2E-Gym 实现][E01]文件头描述 `R2E-Gym-Subset-RL`，实际 `DATASET` 常量却是 **`PrimeIntellect/R2E-Gym-Subset-Verified`**，split 默认为 train。主 SWE TOML 没有覆盖这个字段，所以读取时必须按配置和常量，而不是 README 名称推断数据。

Taskset 从 HF row 取得 prompt、docker_image、expected_output_json、parsed_commit_content，资源声明为每任务4 CPU、4GB内存、10GB磁盘。加载处未固定 HF revision，镜像也从 row 字段取得；本文没有审计数据集当日全部行或镜像 digest，不能把固定代码提交等同于任务资产全部冻结。

### 4.2 评分路径与 rh2 的 fresh grader 不相同

这条任务路径先整理 venv、清 pycache，将 `/r2e_tests` 打包到 host 并从 agent 文件系统移走。完成后先捕获 patch，再将测试放回 **原 runtime**，执行 `run_tests.sh`，解析 pytest map，与 `expected_output_json` 的 map 精确匹配得到0或1。[E01]

这里有两项真实防护：运行期测试文件不直接留给 agent；patch 在测试恢复前捕获。但它**不是另起 clean grader、将候选 delta 投影到干净 checkout**。同一个 runtime 中的测试启动脚本、依赖、配置等是否受到充分保护，需要另审；本轮没有执行攻击探针，也不将潜在攻击面等同于实际 reward hacking 发生。

评分是“与 expected map 匹配”，并非简单要求所有测试 PASSED；expected 数据可包含其他状态。`validate` 实现的是应用 gold source patch 再调用 solved 得到1。这个函数本身不构成完整 no-op、flakiness、alternative solution 与资产可见性审计；其他工具是否补足应独立查证。

### 4.3 任务失败、执行错误、历史错误记录是三个不同对象

`Trace.reward` 汇总非 None 的加权 reward；None 可表示没有执行评分。`has_error` 实际定义为 `not trace.ok`，不是 `errors` 列表非空。因此发生过可恢复错误但最终 ok 的 trace，不会仅因历史错误记录存在就被算法排除。[V02]

`Env.run` 的 prime wrapper 对失败的 multi-trace episode，将其原本 clean 的 sibling trace 也标成失败，避免部分 episode 被当作正常完整结果训练。随后 `iter_trainable_traces` 去除 errored、frozen agent 和没有 sampled tokens 的 trace。[P05][A01]

但 **group 内的某个 episode 请求失败，不自动等于整个 group 被丢弃**：TrainSink 记请求失败／取消，使组可以结束，算法在剩余 eligible traces 上计算信用。被过滤的执行错误不会被自动补成一个 task reward=0。这与 rh2 当前 all-member KEEP_FULL 策略不是同一种约定。应按统计目标和失败机制比较，而不是认定某一方更“严格所以必然更正确”。[P08]

<a id="tokens"></a>
## 5. renderers 与消息图：保真不等于永远维持线性历史

### 5.1 真实训练路径使用 token API，不只是返回字符串后再 tokenize

[TrainClient][V04]将 typed chat prompt 经 renderer 变为 token IDs，调用 `/inference/v1/generate`，保留 completion IDs、logprobs、routing、sampling mask 与 attribution；再将解析后的 assistant message 交还 harness。解析器输出服务于工具执行，原始 token 流服务于训练，两者职责不同。

本提交 TrainClient **只接受 ChatDialect**。对于 Responses 或 Anthropic dialect，代码显式拒绝未经验证的语义转换，提示使用其他客户端或增加 renderer 支持。因此，存在 API interception 框架不等于此训练客户端可直接无损接所有闭源协议。[V04]

tokenizer encode 会修改内部状态，`ElasticRendererPool` 将 render/bridge 放到有锁的线程，decode 侧则不使用同一锁；池按模型、配置和模板参数共享。这个实现提供了事件循环阻塞与可变 tokenizer 状态的工程参照，不是已经测得本项目吞吐改善。

### 5.2 三种标记不可合并

| 字段 | 回答的问题 | 例子 |
| --- | --- | --- |
| `node.sampled` | 此节点是否来自实际模型生成事件 | 重新呈现的历史 assistant 文本可以是 nonsampled |
| `node.mask` / sample mask | 哪些 token 来自模型采样，而非模板注入 | assistant role header 不应成为 sampled token |
| `is_content` | 哪些 token 是消息 body，而非协议 scaffolding | tool 输出 body 可用于 CE；tool wrapper 默认不应混入 body CE |

`sampled` 是 provenance，不是 `role == assistant` 的别名；body 标记也不是 gradient 资格。CE/ref/RL 的最终成员还由各 weight stream 决定。[V03][R01][R02]

### 5.3 Qwen3 的 bridge 与 deliberate deviation

[Qwen3Renderer][R02]主要将模板写成可检查的 Python，保留工具 JSON、thinking 与特殊 token 的位置。`bridge_to_next_turn` 尝试在已有 token 历史之后追加合法工具／用户尾部；如果 thinking retention 要求重新呈现历史，或尾部不适合桥接，就返回 None，走完整 render。不是每个下一轮都强制维持同一个 prefix。

代码明确记录一个与 HF Jinja 的差异：thinking disabled 时，对没有 reasoning_content 的历史 assistant turn 重新保留空 thinking wrapper，以保持与生成时 token 历史稳定。**因此“token faithful”不是所有设置下与某个 Jinja 模板逐字一致，而是明确选择并维护实际训练使用的模板协议。** 不应把文档中的 parity 概括成无条件保证。

Qwen3 的 assistant role/header 被标为 scaffold；生成 body、工具调用标记和结束信号具有 sampled 语义；模板附加的末尾换行不是采样。工具 body 通过连续文本编码保持 BPE 边界，再进行 content attribution。本文没有下载真实 tokenizer 运行 parity test，不能用下面的符号 fixture 代替该验证。

### 5.4 库的 fallback 与训练框架的校验是不同层

renderers 库按 exact canonical model name 选择实现；改名 checkpoint 不能依靠架构前缀推断模板。库本身可 fallback 到 DefaultRenderer，**但 prime-rl 当前默认 auto 配置会在未知模型时直接报错**，要求显式选择 default 或某一具体 renderer。[R01][P04]

因此“任意改名模型都会静默走有风险的默认路径”不适用于本次 Prime 默认入口。显式 default 仍是用户选择，其 bridge、body attribution 与工具解析能力应另核。

### 5.5 消息相同以后，还要核对实际 token 前缀

`prepare_turn` 先按消息 hash 寻找已知路径；`_commit_turn` 在拿到本次真实 prompt IDs 后，再按**完整节点的 token 相等性**收紧可复用 prefix。BPE、thinking 剥离或工具重写造成 token 分歧时，从分歧处建立新物理分支，而不继承不真实的旧 token。[V03]

新输入节点的 mask 为 False；本次 assistant 节点保存未归入输入节点的 generation scaffold 加 completion，前者 False、后者 True。并发请求在 prepare 后提交相同前缀时，commit 再对账，避免仅依据旧缓存制造重复／错误父关系。

这条路径的重要性质是：**失去 prefix reuse 可以降低效率，但不能因此使用模型本轮没有看到的 token 来训练。** 正确性允许分叉，不意味着每次分叉都是 bug。

### 5.6 Compaction 的语义边不等于自动实现细粒度 GAE

Trace 另存 semantic parent links；ACP 请求身份用于识别 compaction attempt 和被后续续跑实际采用的摘要。`Trace.branches` 将未被采用的压缩尝试标为不可训练，已采用摘要和后续 continuation 可分别训练。[V02]

上游算法测试构造了 rejected summary、accepted summary 与 answer，检查最终训练 token 只包含真正被采用的路径。它避免训练未消费的恢复尝试，但没有因此实现 CompactionRL 的跨段 GAE。组 reward 怎样分配仍由当前算法负责。[U01]

### 5.7 分析 JSON 不是精确训练运输格式

graph 中部分大数组、浮点字段具有面向 JSON 展示的压缩／舍入行为；Python/msgpack 路径保留训练所需数据。[V03][P10] 因此用于网页查看的 JSON dump 不应未经验证重新充当 faithful replay 输入。应检查导出格式是否携带完整精度、routing 与 sampling support；本文没有对全部序列化路径执行 round-trip 测试。

<a id="algorithms"></a>
## 6. 八种算法：名字决定 sampling 与信用，trainer 仍有独立目标实现

[算法基类][A01]区分 episode 级 scoring 和 group 级 credit；最终 action routing 决定 policy token 进入 `rl`、`ce` 还是 `ref_kl`。下面按当前代码，不按外部论文通用定义描述。

| `algo.type` | 生成来源／额外模型 | 信用与训练目标 | 关键限制 |
| --- | --- | --- | --- |
| `grpo` | live policy | reward 减组均值，可选效率 shaping；action→RL | 没有标准差归一化，也不是 LOO；trainer 默认不是经典 clipped PPO |
| `max_rl` | live policy | 组中心化再除正的组均值；action→RL | 组均值非正时为零；singleton 实际为零 |
| `hierarchical_grpo` | live policy | 按角色与 episode 分桶求均值；action→RL | 不是任意消息 DAG 的自动因果 credit |
| `rae` | live policy | 角色历史 EMA baseline；action→RL | 依赖完成顺序，baseline 当前重启清零 |
| `opd` | live policy + frozen teacher | 给学生真实采样分支补 ref logprob；action→ref-KL | 非通用聊天 API；需要兼容 token ID 与评分接口 |
| `opsd` | live policy，也作 hint 条件下教师 | 单独 prepend demonstration hint，给同一采样 token 评分；action→ref-KL | 这里链接 SDFT，不应与已读 SDPO 当同义词 |
| `sft` | frozen generation endpoint | 教师在环境里生成的 action→CE | 这一入口是在线生成式 SFT，不是整个离线 SFT 数据加载器 |
| `echo` | live policy | GRPO action→RL，指定后续 observation body→CE | 无 body attribution 时有整节点 fallback；零优势 gate 会改变保留行为 |

### 6.1 GRPO 与效率惩罚

设有效 trace reward 为 $r_i$，共 $G$ 个。普通版本为

$$
A_i=r_i-\bar r,\qquad \bar r=\frac{1}{G}\sum_jr_j.
$$

这是 [grpo.py][A02] 的组均值，不是减去其余 $G-1$ 个成员，也不除以组标准差。若执行错误排除了某些 traces，$G$ 是实际参与统计的数量，不是 TOML 名义 group_size。

可选 length penalty 使用组内最大值归一化 output/input/turn 三个代理量：

$$
c_i=\sum_{d\in\{out,in,turn\}}w_d\frac{l_{i,d}}{\max(1,\max_jl_{j,d})},\qquad
\tilde r_i=r_i-\bar r c_i,\qquad A_i=\tilde r_i-\overline{\tilde r}.
$$

因此所有任务成功时仍可能因效率差异产生信用；二元 reward 全零时，乘上的 $\bar r=0$ 使惩罚不能凭空造出该类信号。原 trace.reward 没被这一局部 shaping 改写，curriculum 后续读取的仍是原 reward。[A02][C03]

默认可选惩罚对象的 output/input/turn 权重为0.25/0.1/0.1；**配置是否启用该对象与对象内部默认是两回事**。这些值是实现参数，不是对所有任务验证最优的结论。[P12]

### 6.2 MaxRL、Hierarchical GRPO、RAE

MaxRL 为 $A_i=(r_i-\bar r)/\bar r$（$\bar r>0$），否则为零。源文件 docstring 把 group_size=1 与 REINFORCE 联系起来，但本实现 singleton 分子恒为零。19个参考检查验证的是这个代数差异，适合后续做文档／测试对账，不是证明对应外部算法论文错误。[A03]

Hierarchical GRPO 的 bucket 由 agent name 与配置决定：列在 episode_agents 中的角色按 episode.id 再分桶，其他角色跨 episode 对比。Proposer 与 Solver 等角色可以拥有不同统计范围，但算法没有从 semantic edges 自动推导每个工具步骤的价值。[A04]

RAE 在每个角色的历史 baseline 更新前计算优势，再按 decay 更新 EMA，当前默认 decay=0.95。它是算法实例内的状态，不会因为 curriculum 保存了自己的 RNG 和 task reward 就自动一起保存。源码明确允许重启时从零 baseline 重新开始。完成顺序、源实例范围和 restart 会影响信用；不是无状态替代组均值。[A05]

### 6.3 OPD：兼容性是接口事实，不是“能够调一个强模型”

[opd.py][A06]在 episode finalize 阶段为学生产生的 trainable branches 请求教师评分，再赋给相应采样节点；之后才到 group admission。某些描述用 ship time 概括教师调用，但真实代码在 gate 前已经支付教师成本。拒绝的任务可能仍消耗 teacher forward。

[PrefillScorer/prefill_logprobs][P14]使用 `/inference/v1/generate` 的 prompt_logprobs：发送原 token IDs、max_tokens=1、temperature=1、top_p=1，按位置取得 scalar logprob，首 token 无前置上下文用占位0。它不是从聊天接口请求一段答案，也不是获得完整词表或 top-k logits。

教师必须能理解学生 token ID 对应的词表、特殊 token 与序列约定；代码里的模型名、健康检查与 endpoint 类型不能替代 tokenizer compatibility 检验。本轮没有核对教师 checkpoint 资产或跑 teacher/student 对拍。冻结 endpoint 是配置角色，不是证明远端权重永远不变的加密协议。

当前配置对 **OPD/OPSD 与 live truncated sampling 的组合显式拒绝**：学生 replay 会在保留集上重新归一化，但教师 prefill 是 full-vocab 分数，直接相减会混合概率定义。这个拒绝范围作用于整组 live source 配置，不能认为所有多源组合都可同时启用。[P04]

### 6.4 OPSD：本栈的名字对应什么

本栈文档将 `opsd` 指向 **Self-Distillation Enables Continual Learning / SDFT（2601.19897）**，不是已读的 SDPO（2601.20802），也不能自动等同另一篇 OPSD（2601.18734）。这里只核实现引用与行为，不重新审查这几篇论文。[P15]

[opsd.py][A07]从 trace.info 或 task data 取得 demonstration hint，缺失时显式报错。它将 hint 独立编码并放在原分支 token 之前，再用 live policy 对拼接序列评分，切回原分支区间；原学生 token ID 序列被保留，而不是把整份学生文本改写成另一套教师答案。

教师与学生是同一在线模型的不同条件输入，但本轮没找到对所有 episode/branch 评分统一冻结 self-teacher checkpoint 的保证。不能仅凭 on-policy 名称宣称异步运行中所有评分与生成版本完全相同。它也没有自动实现任意环境错误反馈提炼或跨 tokenizer 对齐。

### 6.5 SFT：生成来源与 action loss 联合约束

[sft.py][A08]使用 frozen generation source，action 路由到 CE，不读取组 reward 来构造优势。当前配置禁止把 frozen generation 当作 live-policy RL 的正常来源。教师产生的轨迹不需要为了喂 trainer 伪造 policy advantage，但仍必须保留 token 与训练目标的对应关系。[P12][P16]

这一 SFT 算法入口本身没有“只收 reward=1”的隐含规则；对成功轨迹进行 rejection sampling 是另一个筛选决策。它也不是整个仓库离线 SFT trainer 的完整审查。不要把算法层统一表示理解为每种数据供给都由同一个入口实现。

### 6.6 ECHO：工具内容成为 CE 目标，但没有变成 action

[echo.py][A09]继承 GRPO，另为 trainable branch 中**第一次 sampled node 之后**、选定 role 的 nonsampled observation 赋 CE 权重。默认只选 tool、alpha=0.1；配置任意 roles 表会替换整张默认表，user feedback 需要显式选择。初始 prompt 不因角色相同就自动进入 observation CE。

若 `is_content` 长度与节点 token 一致，只训练 body；缺该信息时实现回退为整个选中节点，而非总是 fail-closed。此时 wrappers 也可能进入 CE，目标已从 body-only 改变。额外 filter 只能在当前 selection 内缩小，并对分支数与长度做检查。[A09][U01]

CE token 的 sample mask 仍可为 False，policy gradient 仍只针对 action。两者没有冲突：一个字段表达采样事实，另一个表达辅助学习目标。共享 observation 在多分支中也按目标流去重，不能让同一输出因 fan-out 反复提高 CE 权重。

本栈中存在这一实现和测试，不等于复现了 ECHO 论文的完整 recipe、模型收益和资源结果；原论文阅读仍以 [E8 笔记](E8_echo.md) 为准。

<a id="admission"></a>
## 7. 从完整组到批次：准入、目标信号和数据分布相互影响

### 7.1 实际阶段顺序

[TrainSink][P08]处理请求成功、失败和取消，组终态满足后再 finalize_group。它不会把所有失败当作永远等不到的 rollout，也不会无条件补一个虚构失败 reward。正常组完成后：

```text
finalize_episode（包括可能的 teacher/CE 标注）
→ finalize_group（计算实际有效 trace 的组信用）
→ curriculum.observe（采样器先观察结果；各 gate 再判断）
→ trace_to_samples（按 trainable branch 展平）
→ stamp loss routing / prune / pending trace bucket
→ batch selection + stale check
→ packing / trainer
```

不同算法是否在 episode 阶段读取 reward，由各自实现决定；不能把所有 finalize 都叫“评分”。因 stale 被取消的组可绕过 curriculum，不应把它作为模型能力低的观测。[P08][C01]

### 7.2 `batch_size` 不等于当前分支行数

pending_batch 以 trace ID 为 bucket；选批主要按 logical trace 或 token 预算，而非看到几条物理分支就算几次独立采样。branch 展平后，一次 optimizer batch 仍可能包含不同数量的 TrainingSample/MicroBatch。token budget 按真实送训的 branch 长度计，重复的 context 仍占前向计算。

**先计算组信用，再把不同 trace 发往不同训练 batch**，在统计上不同于“只拿本 batch 恰好完成的组成员重算均值”。算法可以选择前者；不能将“发批时组不在一起”自动判为组统计错误。对应的 policy age、mask 与分母仍需另外验证。[P08]

### 7.3 内置 zero-advantage pruning 与可选 gate 不同

内置 `_prune_zero_advantages` 将零优势 action 从 RL 权重流去掉，但若样本还有 CE/ref-KL 成员则保留。没有 advantage 的合法蒸馏样本不需要伪造非零 A。constant_trainer_batch_size=True 时在补足批次前做 pruning；False 时在选批后去掉但不补足，两者有效消费量不同。[P08]

可选 [AdvRangeGate][C02]则只检查合法 trainable trace 的 advantage 是否全在指定范围，默认范围[0,0]；有优势且全在范围内便拒绝整个组，完全没有 advantage stream 时放行。它不综合查看 CE/ref-KL 信号。

因此 **ECHO 的 all-zero RL group 可以被内置 pruning 保留，却被用户显式启用的 AdvRangeGate 提前拒绝**。默认 curriculum.gates 为空，所以不是所有 ECHO 配置的默认错误。它可能是有意只在可对比任务上进行混合训练，也可能违背用户想利用失败观察的目标；关键是显式命名并测试。[C02][P04]

另一个容易忽略的影响：默认 IPO 的 RL 分量除了 PG 还有 mismatch 正则。prune 掉 A=0 token 时，连该分量的正则也不再计算。因此它不是在所有定义下都“完全语义不变地去除无用算力”。[P08][T01]

### 7.4 Curriculum 很简单，也因此适合作为强基线

[Curriculum][C01]先让 sampler 观察每个正常完成组，再收集所有 gate 结果；所有 gate 都执行，不因首个拒绝短路。因此被拒绝组仍可更新任务难度，除非在更早的 stale／执行逻辑中跳过。

[DifficultyPoolSampler][C03]要求有限非空任务集、唯一 task key，存每个任务最近一次有效 trainable trace 原 reward 均值；按 threshold 落入 pool，未知任务权重1。默认 hard≤0.25 权重0.2、normal≤0.75 权重1、其余 easy 权重0.2。[P04]

这些是**每个任务的权重，不是先按 pool 概率抽桶**。9个 easy 任务各0.2、1个 normal 权重1，则总 easy 概率为1.8/2.8≈64.3%，不是16.7%。题目数变化会改变 bucket 总质量。权重设0还可能令任务不再被复测，除非其他流量更新它。

该实现没有 posterior、不确定度、policy-age 校准或 EMA reward；是 latest-group 的直接启发式。它保存任务分数与 RNG，不能因此宣称保存了 RAE 等所有算法状态。每次抽样遍历任务集的成本需要 profile 后再判断是否值得优化，不能凭 O(N) 就认定真实训练瓶颈。

<a id="loss"></a>
## 8. 运输与 packing：训练目标是逐 token 的，不是每行一个字符串标签

### 8.1 wire contract

[TrainingSample/MicroBatch][P10]通过 msgspec 位置编码保存 full token IDs、mask、inference logprob、temperature、advantages、ref logprob、三分量权重，以及可选 routing、sampling masks、多模态 sidecar 和 trace/branch identity。字段追加顺序涉及兼容性，不能任意重排。

`rl_weights=None` 表示在 sampled mask 上默认权重1，**不是关闭 RL**；`ce_weights=None/ref_kl_weights=None` 才表示相应分量缺席。混合打包时某条流一旦存在，其他样本按对应 identity fill 补齐：RL=1、CE/ref=0；最终 RL 仍与 sampled mask 求交。[P10][P11]

### 8.2 packing 的几个不同目标

[batch.py][P11]先准备每个 sample，再 first-fit-decreasing packing；模型 cost 近似为 $a\sum L_i+b\sum L_i^2$，不是将拼接总长直接平方。后续按估计工作量平衡 rank，并尽量通过拆 bin 达到合适的 microbatch 数。

不同 loss 类型与 temperature 可以混合，因为是逐 token 流；有 routing 的样本不与无 routing 的随意拼接，多模态 sidecar 需要形状兼容。分布到各 rank 时还保证同一 step index 的 modality 对齐，避免某 rank 进入 vision encoder collective 而其他 rank 不进入。

为平衡 microbatch 数补的 dummy 必须清空 **所有目标流、loss mask、sampling replay 和身份**。只清 action mask 无法阻止 CE/ref 仍训练这些 token；沿用 trace identity 还可能重复写回 annotation。[P11]

### 8.3 “packing 不截断”只描述其中一层

bin packing 函数声明 never truncating，但其上游 `prepare_sample` 对超过 seq_len 的样本会切片，连同所有 token-aligned streams 一起截断；多模态还需避免切开图像占位块。[P11]

因此完整路径不是“不可能丢 token”。如果全部目标 token 都在被裁掉的后缀，先前有效样本会变为无目标 batch。loss 的零梯度 anchor 能保证 backward 不崩溃，但这不等于该次运行仍提供了有效学习。应分开统计表示合法与有效目标量。

## 9. trainer 实际算什么：GRPO 配信用，IPO/ref-KL/CE 配梯度

本节公式按 [loss.py][T01]和 [train.py 的实际调用][T02]重新写出，**不是某篇论文的原公式编号，也不宣称是完整优化理论证明**。

### 9.1 概率与 membership

令 $t_i=\log\pi_\theta(y_i\mid h_i)$ 为 trainer 当前 logprob，$b_i$ 为 inference 行为 logprob，$q_i$ 为 teacher/reference logprob；$\rho_i=\exp(t_i-b_i)$，$d_i=t_i-b_i$。它们要求 token、上下文、temperature 与采样支持集的定义一致。不能把 $q_i$ 叫成 rollout old policy。

三个分量的成员：

$$
m_i^{RL}=\text{sampled\_mask}_i\land(w_i^{RL}\ne0),\quad
m_i^{CE}=(w_i^{CE}\ne0),\quad m_i^{ref}=(w_i^{ref}\ne0).
$$

各分母为当前训练步全局非零成员数量 $D_c=\max(1,\sum_i m_i^c)$，**不是 $\sum_iw_i^c$，不是分支数，也不是 trust-region 过滤后幸存数**。CE/ref 不再额外与 action mask 求交，因此 observation CE 可以合法存在。

### 9.2 默认 RL 分量是本代码定义的 IPO

默认 trust predicate 为绝对概率差：

$$
k_i=\mathbf1\{|e^{t_i}-e^{b_i}|\le\epsilon\},
\quad
L_{RL}=\frac1{D_{RL}}\sum_i m_i^{RL}w_i^{RL}
\left[-k_i\,\tau_A A_i\rho_i+\tau_{KL}d_i^2\right].
$$

因此这不是经典 PPO 的 ratio clip，也不是 rh2 faithful DIS。罕见 token 的行为概率0.001→0.02，ratio为20但绝对差仅0.019，在 epsilon=0.1 的示意条件下仍被保留。被 trust predicate 排除的 token 仍可承接平方 log-ratio 正则；分母也没有随 predicate 缩小。[T01]

`trainer.loss` 的 custom hook 只替换 RL 分量；CE 与 ref-KL 有固定路径。配置名“GRPO”主要定义如何取得 A，不能据此忽略 trainer 真正执行的 surrogate。

### 9.3 ref-KL 分量：sampled-token 的蒸馏信号

当前实现固定一侧绝对概率阈值：$k_i^{ref}=\mathbf1\{e^{t_i}-e^{b_i}\ge-0.2\}$，计算

$$
L_{ref}=\frac1{D_{ref}}\sum_i m_i^{ref}w_i^{ref}
\left[-k_i^{ref}\operatorname{sg}(q_i-t_i)\rho_i+10^{-3}d_i^2\right].
$$

`sg` 是 stop-gradient；这里不读取 scalar outcome advantage。删掉 detach 会改变导数，甚至在具体数值例中翻转方向。19个检查中的第11项用 CPU autograd 验证了这一差异。

这是用采样 token 提供 reverse-KL 风格 PG 信号及修正／正则，**不是直接对整个词表求 KL**。日志中的 `ref_kl` 为采样位置 $q_i-t_i$ 的均值，可以为负，不应拿数学 KL 非负性判定日志错误。`mismatch_kl=\rho_i-\log\rho_i-1` 又是另一个诊断量，不等于实际平方正则。

### 9.4 CE、混合与计数的影响

$$
L_{CE}=-\frac1{D_{CE}}\sum_i m_i^{CE}w_i^{CE}t_i,
\qquad L=L_{RL}+L_{CE}+L_{ref}.
$$

两枚 tool token 的 NLL 为2、4，权重均0.1，CE 为 $(0.2+0.4)/2=0.3$；若错误地除以权重和0.2，会得到3并抵消 alpha。[T01]

独立分母保证加入纯 RL 样本不会直接稀释 CE 的 token mean，但**不保证同一 CE 分量的多源比例互不影响**。再加入两枚 NLL=1、权重1的 SFT token，CE 会成为 $(0.2+0.4+1+1)/4=0.65$。它也不消除共享参数、梯度裁剪和优化器状态带来的目标交互。

trainer 的 t 使用逐 token temperature；所以非1温度下应明确 CE 是对哪个分布取 NLL。默认普通配置温度1较容易比较，不能忽略来自不同生成来源的 temperature 对齐。

### 9.5 全局分母必须和分布式梯度缩放配套

train.py 在一个训练步开始时，对全部本地 microbatch 分别计三类成员，用一次向量 all-reduce 在 `dp_cp` 组求全局数量，再将同一组分母传入每个 microbatch loss。没有某类 token 的 rank 仍执行一致的 collective。[T02]

反向后，非 gradient-offload 路径通过 `fsdp_gradient_divide_factor` 补偿 FSDP 的 rank averaging；offload 路径则把对应因子交给 gradient manager。**全局计数和 FSDP averaging 只能作为一套看，不能只复制其中一项。**

简单 DP 算术例：两 rank 各1和9个 token，局部梯度和1和18，正确全局 token mean 为1.9；先各自除局部计数再等 rank 平均得到1.5。参考检查验证这项算术，**没有模拟 CP gather 的 backward、实际 FSDP 或 GPU collective**。对应实现的完整数值一致性仍需真实并行测试。

### 9.6 labels、routing 与 sampling support

trainer 将 labels 左移到 next-token，再在计算后将 logprob 右移回 token 自身位置；sampling mask 与 labels 一起移位／CP 切分，routing replay 与模型输入分片对应。[T02]

当前 top-p/top-k replay 记录保留 token ID 集，trainer 在可用位置使用 `target_logit - logsumexp(kept_logits)`，不是用 full-vocab old probability 假装采样分布未截断。非法／不可用 replay 行的 fallback 与 NaN 处理也在 loss helper 中显式表达。[T01]

配置在 top-p 截断但无 top-k 上界时注入512，以限制运输与显存成本；**这本身可能改变原 top-p 支持集**，“通常变化很小”不是算法严格等价保证。OPD/OPSD 因 reference normalization 不匹配而被配置拒绝，也是组合约束，不应绕过检查后仍宣称标准配方。[P04]

<a id="async"></a>
## 10. 异步生命周期与恢复：本轮检查到的边界

### 10.1 staleness 的单位与时间点

[orchestrator/utils.py][P17]定义训练 batch step $s$ 对应被更新前策略 $v_{s-1}$。若 episode 的 policy span 为 start/end，则

$$
\text{age}=\max(0,(s-1)-start),\quad
\text{inflight}=\min(\text{age},\max(0,end-start)),\quad
\text{queue}=\text{age}-\text{inflight}.
$$

阈值 N 对应最早允许 dispatch 版本 $(s-1)-N$。queued 与 in-flight 数据都可能被处理；frozen-source episode 无 policy span，被视为不因学生版本变化而 stale。[P08][P17]

这个标记是 episode 运行跨度，**不是逐 token 精确标注每一枚由哪版参数生成**；实际修正仍依赖 token 行为 logprob 等事实。不能把一个 start/end 区间当成整个区间内所有 token 同源的证明。

### 10.2 数据平面与管理平面分开

[InferenceClient/AdminPlane][P14]为正常推理和权重管理使用不同客户端；管理请求绕过 router，直接按 engine/rank 顺序访问。权重更新大致为 pause engines→执行更新→finally resume。NCCL/NIXL/filesystem 等配置不在本轮做底层性能比较。

这一结构避免管理请求排在长生成之后，但 `finally resume` **并不能单独证明部分 engine 更新失败后的全局原子性或 rollback**。本轮没有运行相关故障场景，也未完整阅读 weight watcher／eval handoff，所以不将“可恢复一致性”写成已验证事实。

LoRA 路径包含有界请求／总重试限制，prefix cache 按权重版本加 salt；这些机制各自覆盖不同问题。不要把缓存盐、权重成功发布和教师 checkpoint 冻结混成一个版本号。

### 10.3 resume 状态不是自动包含所有可学习状态

curriculum 明确保存 task rewards 和 RNG；RAE baseline 明确重置。当前代码是有意允许这种恢复行为，不是所有 restart 都承诺精确复现 uninterrupted credit sequence。对项目应问“需要怎样的恢复语义”，而不是无条件要求构建联合事务平台。[C01][C03][A05]

### 10.4 部分工程注释与当前上游的关系

[PrimeRlServingTokens][P18]继承 vLLM 的 tokens-in/out 服务，保留 routing compact byte export，并临时桥接 KV transfer 参数。文件注明对应 vLLM 修复未进入所用发布版本、升级后可删除该 shim。它是良好的窄 backport 参照；本文没有重新核对相关 PR 当前合并状态，也不将注释中的性能数量级当作本轮实验结果。

<a id="checks"></a>
## 11. 实际检查、实现限制与可进一步验证的点

### 11.1 已读上游测试，不等于已执行上游测试

[tests/unit/orchestrator/test_algorithms.py][U01]覆盖默认算法角色、冻结来源限制、流路由、优势长度、compaction accepted/rejected、ECHO role/body/filter。它使用符号 token 和构造 trace，证明测试意图与接口期待，不是最终模型质量。

[tests/unit/train/rl/test_loss.py][U02]包含 CE 数值、权重、None 与显式 RL 权重、混合分量、空目标 backward 等测试。本文件标记 GPU，本轮未执行。其中 `test_grpo_loss` 与 `test_gspo_loss` 都调用 IPO 路径并主要检查 scalar shape，**不能只按测试函数名就宣称两种论文算法已各自实现并被数值验证**。

本轮没有遍历全部测试，所以“这里没有看到某项”只表示已审范围的缺口，不声称整个上游从来没有测试。

### 11.2 19 个作者自建 CPU 语义检查

源码与结果分别见 [检查脚本](checks/prime_stack_semantic_probes_20260908.py)、[结果 JSON](checks/prime_stack_semantic_results_20260908.json)。运行环境 Python3.13.5、Torch2.10.0+cpu，19/19通过。它们是依据本次阅读写出的独立参考模型，**没有导入／替换 upstream prime-rl 或 verifiers 函数，不能替代集成测试**。

| # | 检查内容 | 观察或预期差异 |
| --- | --- | --- |
| 1 | 排除执行错误 vs 伪造 reward0 | 有效组(1,0)优势±0.5；补0以后均值／全部优势改变 |
| 2 | 全成功时效率信用 | 原 reward全1仍可因长度差产生±0.0625示例 |
| 3 | MaxRL singleton | reward1仍得到优势0，不是 REINFORCE reward |
| 4 | RAE 顺序 | 用示意 decay0.5，交换完成顺序改变信用 |
| 5 | shared prefix | 梯度成员去重不减少展开的 forward token 位置 |
| 6 | 可选 gate 与 ECHO | 全0优势gate拒绝，内置 CE-aware prune可保留 |
| 7 | 三种零优势场景 | 纯RL去掉；有CE保留；无A但有ref保留 |
| 8 | alpha 与计数分母 | 两个0.1权重 NLL=2/4，CE为0.3而非3 |
| 9 | 混合目标 | 加RL不改变CE分母；加SFT CE会改变同分量均值 |
| 10 | IPO absolute trust | 大 ratio仍可能被保留；被拒token仍有平方正则 |
| 11 | ref signal stop-gradient | 删除detach改变导数，示例由负转正 |
| 12 | sampled loggap | 可为负，与完整KL非负性不矛盾 |
| 13 | full-vocab/kept-set混用 | 相同基础分布也能产生伪loggap |
| 14 | action maskFalse | 不阻止显式CE权重的目标成员 |
| 15 | difficulty pools | 9 easy对1normal时easy总概率约64.3% |
| 16 | age分解 | batch10、start7/end8时age2=1inflight+1queue |
| 17 | token prefix | 消息不变但token改变仍必须在完整节点边界分叉 |
| 18 | 截断后无目标 | 零梯度anchor支持合法backward，但无学习量 |
| 19 | 简单DP分母 | 全局token均值1.9与局部rank均值1.5不同 |

独立语义检查可以揭示理解错误，但若我们的参考模型也抄错了源码，两者不会自动互相揭穿。后续最有价值的补充是把相同 fixtures 接到真实 upstream 函数和 resolved 配置，而不是再次增加解释性算术数量。

### 11.3 文档差异、组合约束与潜在 PR 分开登记

| 事项 | 本次证据等级 | 下一步是否值得做 |
| --- | --- | --- |
| MaxRL singleton 描述与公式不符 | 直接源码＋代数检查 | 可先补真实单元测试并讨论 docstring；不需完整RL训练 |
| SWE TOML未写group_size／SLURM | 配置静态对账，未执行完整解析 | 先保存真实 resolved config；确认 overlays 后再判断文档或recipe问题 |
| ECHO＋AdvRangeGate丢CE-bearing组 | 两条源码路径＋参考检查；非默认 | 可加组合测试／文档，先尊重用户可能有意限定学习区间 |
| content attribution缺失时扩大CE范围 | 实现有明确fallback | 可考虑显式strict选项或warning；先测自家renderer是否实际缺字段 |
| 同一sharednode的成本字段按branch累计 | 直接读usage／长度属性与penalty消费者 | 需要真实分支fixture比较成本定义；不把设计取舍直接称bug |
| 库fallback与Prime校验不同 | 两层源码均有明确处理 | 应纠正跨层概括，不宜提重复“静默fallback”bug |
| accepted summary被训练、rejected不训练 | 源码＋现有上游测试 | 值得复用测试形状，不再把compaction全部视为无因果归属 |
| 三个全局分母＋FSDP补偿 | trainer实际消费代码＋参考DP算术 | 需要真实CP／DP梯度对拍才能声称并行等价 |
| gate前教师评分的成本 | 实际finalize顺序 | profile拒绝率和teacher开销，再决定前移廉价检查是否值得 |
| 部分权重更新失败后resume | 仅管理路径静态观察 | 如成为项目需求再做故障注入；本轮不声称已复现事故 |

任何外部 PR 前仍需重查最新分支、已有 issue/PR 与维护者目标。本次没有向 Prime 官方仓库提交 issue、代码或 PR。

<a id="project"></a>
## 12. 对 RepoHarness 的条件化建议

项目映射基于本轮读取的 [CURRENT-STATE-BRIEF][H01]，不是重审 rh2 全部代码。现有 miles/SGLang 路线、all-member KEEP_FULL 和 faithful DIS 分母约定都不因本文自动改变。

### 12.1 最值得吸收的是责任拆分，而不是再造中立平台

Prime 提供一个具体参照：**环境是否可信、轨迹是否结构正确、某个目标有没有信号、梯度是否按预定权重计算，是不同决定。** 但这种拆分不要求 rh2 立即扩成通用 IR 或多算法平台。

当前只有 outcome-GRPO 时，保留简单路径可以合理；真正加入 ECHO、SFT 或 OPD 时，再为相应消费目标建立窄、可测试的扩展。不能把全0 outcome 样本一律称为无效数据，也不能为了保留它而伪造非零 reward。Prime 的 optional gate 反例恰好说明“新增目标”必须重新检查前面的旧过滤规则。

### 12.2 三个优先候选，不是三个批准实施项

| 候选 | 为什么与现有系统有关 | 最小检查 | 不需要做什么 |
| --- | --- | --- | --- |
| **目标专属成员与分母对拍** | rh2已有明确组／loss语义；辅助目标可能改变“无信号”的定义 | 固定两条多轮trace，含tool body、sharedprefix、全0reward，检查实际转换和最终loss | 不改faithful DIS分母来迁就另一框架默认 |
| **真实token与解析结果双轨检查** | 外部harness可能改写history或toolcall | 从模型调用端取实际IDs，与训练端逐节点对拍；加入thinking变化和一次合法分叉 | 不要求所有历史永远线性，也不把模型文本重新tokenize当真值 |
| **按逻辑成本评估采样／门控** | 组失败、stale、fan-out会改变有效供给 | 分别统计原始任务、episode、trace、branch、独立call、目标token和丢弃原因 | 不先建复杂curriculum，不预设latest-reward pool优于静态分层 |

如果只是为了评估思想，可先离线使用现有轨迹；需要宣称代码正确则接实际函数，需要宣称吞吐则运行同条件工作负载，需要宣称学习效果则最终保留训练对照。三种证据不能互相替代。

### 12.3 不建议直接搬的内容

不将 Prime 的全局token均值替换为项目已冻结的另一种分母；不将其缺员组均值当作 rh2 全组准入的自动替代；不为接入新的ECHO层就升级整个环境栈；不把32GPU SWE例的并发1024或131K长度当八卡起点；不假设同一教师接口能同时支持聊天生成、rawtoken prefill和top-k/full-vocab蒸馏。

同样，不把本篇小范围静态差异夸成“成熟框架不可靠，所以必须自研全部系统”。更好的个人贡献是：准确复用已有设计，说明自己的工作负载在哪个边界不同，给出真实反例，再提供最小必要修改。

### 12.4 这份阅读新增了什么已有笔记没有的证据

相对 miles／SkyRL-Agent／Agent Lightning，新增的是**同一训练栈怎样把多种目标接到同一条逐token数据管线**，以及目标混合后准入、计数与dummy语义如何改变。相对 SDPO／ECHO 论文，新增的是具体接口、teacher prefill、body attribution、配置互斥和实际trainer分母；不新增任何模型效果证明。

因此本篇对项目一最直接的价值是代码与实验设计，不是选定一种新算法。它支持优先完善少量可复用的训练语义测试，并提示数据／反馈扩展应该按已观察到的瓶颈推进。

<a id="sources"></a>
## 13. 源码覆盖与快速定位

以下范围是**实际阅读范围**；“全”表示该较短文件已完整读取，长文件只列读过的区段／符号。行号随代码版本改变，链接固定commit；可用表中符号直接定位。

| 标识 | 文件／对象 | 覆盖与承重问题 |
| --- | --- | --- |
| P00–P02 | packages tree、pyproject、.gitmodules | 全；一致checkout与依赖，而非独立main拼装 |
| P03/P07 | SWE / reverse-text TOML | 全；实际配置、组大小、renderer与资源条件 |
| P04 | configs/orchestrator.py | 1–末；继承、curriculum、采样支持、batch、staleness、renderer校验 |
| P06 | configs/rl.py | 1–225、280–540；部署与shared config，不宣称完整launcher审计 |
| P05 | orchestrator/envs.py | 全；taskset ownership、typedtaskdata、失败episode处理 |
| P08 | train_sink.py | 全；组终态、credit/gate、prune、逻辑trace批次、stale |
| P09/P13 | trajectories.py、algo/routing.py | 全；按node去重、流对齐、action routing |
| P10 | transports/batch/types.py | 全；position编码与各stream |
| P11 | trainer/batch.py | 1–245、310–末；cost、prepare、packing、dummy、rank分发；中间helper未全部展开 |
| P12 | configs/algorithm.py | 1–300；已读算法类型／关键约束；不将未展开字段写为已审 |
| P14 | orchestrator/clients.py | 1–240、370–末；client/admin、prefill与LoRA重试；中部helper未全读 |
| P15 | docs/algorithms.md | 1–450中实际返回的相关段；模块、命名、三stream；不是所有链接论文已读 |
| P16/P17/P18 | generation_source / utils / serving_tokens | 全；live/frozen、版本年龄、vLLM薄扩展 |
| A01–A09 | algo/base与八算法 | 全；score_episode/group、公式、teacher及CE标注 |
| C01–C03 | curriculum/base、gate/adv、sampler/pool | 全；观察顺序、组合门控、任务加权与保存 |
| T01 | trainer/rl/loss.py | 全；membership、IPO、ref-KL、CE、空目标anchor |
| T02 | trainer/rl/train.py | 290–740；真实count/forward/loss/backward/update调用；不含完整启动／恢复 |
| V01 | verifiers/v1/env.py | 1–260；抽象／角色执行边界，不是完整env生命周期审计 |
| V02 | verifiers/v1/trace.py | 1–250、370–620；身份、reward/usage、branch、semanticedge |
| V03 | verifiers/v1/graph.py | 1–240、500–末；节点流、commit、prefix和routing；中间helper未全读 |
| V04 | verifiers/v1/clients/train.py | 全；协议限制、bridge/render、tokenAPI和pool |
| R01 | renderers/base.py | 1–230、440–690、890–1100；数据类型、body/role、parser、注册；非所有factory/helper |
| R02 | renderers/qwen3.py | 1–590；render、bridge、thinking、toolbody，末尾少量未展开 |
| E01 | prime-envs/r2e_gym/taskset.py | 全；数据默认、setup、gold验证、原runtime评分 |
| U01 | tests/unit/orchestrator/test_algorithms.py | 1–495相关测试；读取非执行 |
| U02 | tests/unit/train/rl/test_loss.py | 1–275相关测试；GPU标记，未执行 |
| B01 | 官方Algorithms Layer文章 | 全文网页；设计背景，当前代码与当时主张分开 |

其他已读 README／AGENTS 只用于仓库导航与术语；不将其宣传规模作为实测结果。没有额外追读所有模型类、`bash` harness 内部命令实现、完整 EnvServer 进程协议、底层 attention 或所有测试目录。

## 14. 未知项与交付边界

**需要原样保留的未知**：本快照哪些组合实际用于作者生产训练；各算法在同一SWE任务的匹配对照；完整GPU/API/环境成本；教师词表与温度一致性实测；具体SWE例完整overlay；环境anti-hacking完整性；实际CP/FSDP梯度等价；权重发布部分失败与完整resume的行为；所有可选renderer的parity。

本文从未获得这些结果，因此不能标成“未披露但按惯例可以补齐”。代码暴露的数据字段也不意味着每条实际请求都填写正确；测试存在更不等于当前运行一定通过。

本轮仅新增本笔记、[作者自查记录](reviews/prime_stack_self_check_20260908.md)、CPU参考脚本和结果。不改共享README/count，以避免并行线程覆盖；不改训练实现、依赖pin或项目定案。后续独立审查可以沿固定commit和fixtures补真实函数测试，再更新本篇具体结论。

<!-- Stable primary-source links; no session-only citation tokens below. -->

[P00]: https://github.com/PrimeIntellect-ai/prime-rl/tree/04a61d3b75c3c99f263b2c133e822f998909adf7/packages
[P01]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/pyproject.toml
[P02]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/.gitmodules
[P03]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/examples/advanced/qwen3-30b-a3b/swe.toml
[P04]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/packages/prime-rl-configs/src/prime_rl/configs/orchestrator.py
[P05]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/envs.py
[P06]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/packages/prime-rl-configs/src/prime_rl/configs/rl.py
[P07]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/examples/basic/reverse-text/rl.toml
[P08]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/train_sink.py
[P09]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/trajectories.py
[P10]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/transports/batch/types.py
[P11]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/trainer/batch.py
[P12]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/packages/prime-rl-configs/src/prime_rl/configs/algorithm.py
[P13]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/algo/routing.py
[P14]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/clients.py
[P15]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/docs/algorithms.md
[P16]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/generation_source.py
[P17]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/utils.py
[P18]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/inference/vllm/serving_tokens.py
[A01]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/algo/base.py
[A02]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/algo/grpo.py
[A03]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/algo/max_rl.py
[A04]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/algo/hierarchical_grpo.py
[A05]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/algo/rae.py
[A06]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/algo/opd.py
[A07]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/algo/opsd.py
[A08]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/algo/sft.py
[A09]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/algo/echo.py
[C01]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/curriculum/base.py
[C02]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/curriculum/gates/adv.py
[C03]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/curriculum/samplers/pool.py
[T01]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/trainer/rl/loss.py
[T02]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/trainer/rl/train.py
[U01]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/tests/unit/orchestrator/test_algorithms.py
[U02]: https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/tests/unit/train/rl/test_loss.py
[V01]: https://github.com/PrimeIntellect-ai/verifiers/blob/828488fffe31aa3332b9d1bd4bd9ee320e375cf1/verifiers/v1/env.py
[V02]: https://github.com/PrimeIntellect-ai/verifiers/blob/828488fffe31aa3332b9d1bd4bd9ee320e375cf1/verifiers/v1/trace.py
[V03]: https://github.com/PrimeIntellect-ai/verifiers/blob/828488fffe31aa3332b9d1bd4bd9ee320e375cf1/verifiers/v1/graph.py
[V04]: https://github.com/PrimeIntellect-ai/verifiers/blob/828488fffe31aa3332b9d1bd4bd9ee320e375cf1/verifiers/v1/clients/train.py
[R01]: https://github.com/PrimeIntellect-ai/renderers/blob/f91c3e7061ce50ea405cdf54fd419a45cb51a152/renderers/base.py
[R02]: https://github.com/PrimeIntellect-ai/renderers/blob/f91c3e7061ce50ea405cdf54fd419a45cb51a152/renderers/qwen3.py
[E01]: https://github.com/PrimeIntellect-ai/prime-envs/blob/1f1e050ab0cd273bca39eed5c3e5315e6a8ae9d1/environments/swe/r2e_gym/r2e_gym/taskset.py
[B01]: https://www.primeintellect.ai/blog/algorithms-layer
[H01]: https://github.com/Rogerffff/RepoHarness/blob/32b615c4e4f869b448174e5974e7a8d29fc4612c/docs/agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md
