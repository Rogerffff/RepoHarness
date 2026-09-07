# N11 Miles「Agentic Rollout (TITO) / Fully Async RL」：版本化官方实践精读

## 1. 来源、版本与完整覆盖图

本文是 **RadixArk / radixark/miles 官方文档与关键代码专题**，不是模型论文，也不是一套新训练配方。正式网页标题分别为 **Agentic Rollout (TITO)**、**Fully Async RL**；网页无独立作者表、论文版号或统一发布日期。读取日期 **2026-09-07（Asia/Singapore）**。两份页面均无附录；正文全部阅读，没有因当前 SWE 需求而跳过后训练内容。原文未设 SFT、安全偏好对齐、数学 RL 或多模态 RL 实验章节；不能为填模板虚构这些阶段。OPD 是沿实际训练代码补读的相关能力，单列于 §5。

### 1.1 三层版本不能混用

| 证据层 | 本次实核版本 | 如何引用与边界 |
| --- | --- | --- |
| 本地上游 `reference/miles` | **f2b7c79298a53c53861514d099f7def73bd29f4a**，提交日期 2026-08-24，`Log compaction-aware rollout metrics (#2710)`；工作树干净 | 以下 **U** 表示此 commit；[上游固定树](https://github.com/radixark/miles/tree/f2b7c79298a53c53861514d099f7def73bd29f4a)。绝大多数机制解释以它为据 |
| 本地 `reference/miles-rh2-integration` | **98a0272e4158b2c20e3a34d210c79b50159af0f6**，提交日期 2026-09-04；工作树干净 | 以下 **I** 表示此版本。构造为 U + 四项上游选材 + 0001–0016 窄 patch；不是在线 main 的镜像 |
| 在线页面与远端定位 | [Agentic](https://miles.radixark.com/docs/user-guide/agentic-rollout)、[Fully Async](https://miles.radixark.com/docs/user-guide/fully-async)，读取当日 `git ls-remote HEAD` 为 **d2fc97ce581577e255e494801d7568747d5a10d7** | 以下 **W** 表示网页快照。远端仅下载核验该 SHA 的 agentic 文档和 `arguments.py` 中相关约束；未审查整个最新框架，不能声称项目已采用此版本 |

可离线复查：[U Agentic](sources/N11/agentic-rollout.pin-f2b7c7929.md)、[U Fully Async](sources/N11/fully-async.pin-f2b7c7929.md)、[W Agentic](sources/N11/agentic-rollout.online-20260907.md)、[W Fully Async](sources/N11/fully-async.online-20260907.md)、[远端固定版 Agentic](sources/N11/agentic-rollout.remote-d2fc97ce.md)、[远端固定版参数代码](sources/N11/arguments.remote-d2fc97ce.py)。这是 Markdown/代码资料，**没有 PDF 物理页与印刷页差别**；文档以原始小节名定位，代码以 commit + 文件 + 符号定位，行号只针对该版本。快照来源和 SHA256 见 [来源记录](sources/N11/PROVENANCE.md)。首次网页解析返回的正文与直接 `.md` 端点有旧新差异，因此版本比较以存档 `.md` 及固定 SHA 文件为准，不把缓存文本拼成单一版本。

复用线索：[2026-09-02 Harbor–miles 审计](../env_discovery_20260902/analysis/harbor_miles_integration_audit_20260902.md)。其 I HEAD 是较早的 `63c7a94e7`，不是本次 HEAD；其 Harbor 源码结论本次没有重做完整核验。当前集成事实来自 [manifest](../../../agentic_RL/repo_harness_rh2_workstreams/miles_spike/integration_base_manifest.json)、[patch 目录说明](../../../agentic_RL/repo_harness_rh2_workstreams/miles_spike/patches/README.md)及 I 实际代码；不把旧稿推断作为外部事实。

### 1.2 从原文目录建立的覆盖表

以下各行均精读 U 与 W 对应正文；代码只追到足够解释机制的边界。没有独立附录需要另补。

| 原文 | 完整章节/子节 | 本文位置 |
| --- | --- | --- |
| Agentic 导言与 Warning | exact token/logprob/expert 捕获；无图像/视频输入支持，VLM 转 `/generate` | §2、§3、§9 |
| Configure the wrapper | generate 入口、agent 入口、session、prompt 不预套模板 | §3.1 |
| Write the agent loop | 函数合同、base_url、sampling、metadata、返回值 | §3.1、§4 |
| Optional teardown hook | oversampling abort 与外部环境清理 | §4.2、§6.3 |
| TITO / Leave token ownership to Miles | 首轮、后续 token 复用、收集、控制字段 | §3.2 |
| Choose the session behavior | v1 回滚、v2 树、length、partial、权重暂停 | §3.3、§6.3 |
| Pick your `--tito-model` | 固定模板、模型族、自定义模板边界 | §3.4 |
| Verify a new model TITO | CPU 与 GPU 两类验证 | §3.4、§8 |
| Choose replay matching | 四类 matcher、存储前缀权威、tool-call ID | §3.4 |
| Example | SWE/Harbor 入口、reward 与资源生命周期 | §4、§7.3 |
| Fully Async 导言 / When to use it | 长尾、吞吐、off-policy 代价、调试时同步建议 | §2、§6 |
| Usage & Examples / Basic usage / Examples / Customizations | train_async、三个可见示例、可替换接口 | §6.1、§7.3 |
| The fully async schedule / How generation is scheduled | 两循环、sample backfill、权重更新 | §6.1–§6.3 |
| Arguments: Scheduling options | batch/concurrency/granularity 单位 | §6.1 |
| Data path / The data buffer | put/get/filter/retry、排序、批过滤 | §6.2 |
| Arguments: Buffer options | 容量、staleness、unused、自定义 buffer | §6.2 |
| Evaluation / Mode 1 / Mode 2 / Mode 3 | shared/fleet/external 三模式 | §7.1 |
| The weight snapshot pipeline | export、复用 HF、背压、跳点、保留、串行 | §7.1 |
| Metrics / Async rollout / Async eval / Performance | 队列、版本、skip、cache、耗时诊断 | §7.2 |
| Arguments: Logging options | 两个自定义 logger 返回值与默认日志 | §7.2 |

补读代码覆盖：U `agentic_tool_call.py`、`openai_endpoint_utils.py`、session `core.py`/`linear_trajectory.py`/`samples/{merge,codec}.py`、v2 `core.py`/默认 picker/postprocessor；`generate_utils/sample_utils.py`、`fully_async_{rollout,data_buffer}.py`、`submission_scheduler.py`；`inference_rollout_common.py` 的生成评分链；Harbor 示例 README、run 配方段、converter、agent function、reward/metrics；训练 `train_data_conversion.py` 的 reward/mask 转换段、`loss.py`、`cp_utils.get_sum_of_sample_mean`、`loss_hub/{advantages,opd,corrections}.py`、`losses.policy_loss_function` 与 `math_utils.compute_policy_loss`、完整 `on_policy_distillation.py`、参数校验与 Megatron teacher 装载/前向定位；I 上述 buffer/session 关键差分及 `train_async.py`。评测架构按完整官方文档总结，未冒称逐个审完 fleet/dispatcher 的所有代码。

## 2. 核心问题与结论

TITO（Token-In-Token-Out，输入与输出均保留 token 身份）的目标是：harness 可以继续说 OpenAI messages 协议，训练端仍使用推理实际生成的 token 与 logprob。它避免每轮把历史模型输出还原成文本再分词后，拿不同 token 序列配旧 logprob。**TITO 解决的是序列运输与装配，不自动证明评分可信、采样支持集完备或行为版本覆盖完整。**[U Agentic：导言、Leave token ownership；U `session/samples/merge.py::_compute_sample_from_openai_record`]

Fully Async 则使 rollout worker 持续生产、trainer 消费已完成的 prompt group。逐样本释放调度额度缓解长尾，但训练仍按完整组收集；持续生成跨过权重更新，因而必然需要认真处理行为策略版本和 off-policy 校正。原文的吞吐收益是机制解释，没有受控实验给出通用加速倍数。[U Fully Async：When to use it、How generation is scheduled]

三条最重要边界：**树叶不等于新 rollout，环境失败不等于统一 ABORTED，代码支持某 OPD 选项不等于它能与当前 fully-async/session 路径任意组合。**当前 rh2 路径仍是 `Rh2MilesGenerateFn → rh2_custom_generate`，不是把官方 `agentic_tool_call.generate` 换进去即完成接入。项目映射详见 §10，不据本笔记更改训练语义。

## 3. Agentic 轨迹：从请求到训练 Sample

### 3.1 外部 agent 合同与 session 生命周期

官方 wrapper 配置 `--custom-generate-function-path miles.rollout.generate_hub.agentic_tool_call.generate`、`--custom-agent-function-path my_agent.run`、`--use-session-server`、checkpoint 与 `--tito-model`。不设 `--apply-chat-template`；文档要求 `Sample.prompt` 为 messages 列表。agent 合同为 `async run_agent(base_url, prompt, request_kwargs, metadata, **kwargs) -> dict | None`。`base_url` 已含 `/sessions/<id>`，调用时只追加 `/v1/chat/completions`。返回字典并不是已经标准化的 reward：v1 先合入 sample metadata，再由所选 RM 读取。[U Agentic：Configure/Write；U `agentic_tool_call.generate`]

`OpenAIEndpointTracer.create` 按 session 一次选择 owning session-server port，之后所有收集/删除重用这个 URL。wrapper 把 `max_seq_len`、session instance 和 server identity 传给 agent；`build_chat_request_kwargs` 映射 `max_new_tokens→max_tokens`、`min_new_tokens→min_tokens`、`sampling_seed→seed`，丢掉不在 `ChatCompletionRequest` 字段集合中的键，不代表外部 harness 必然遵守这些采样参数。

agent 结束后 `POST /sessions/<id>/samples` 取服务端装配的 safetensors，随后 `finally` 中 DELETE session。收集请求超时为 **120 秒**，删除也有 120 秒等待上限；并非整个 episode 的预算。wire 只运输白名单字段，随后覆盖输入 Sample 的 deepcopy。U 的 token 为 int64、loss mask 为 uint8、rollout logprob 为 float64、routing/indexer tensors 为严格 int32；v2 另运输 reward。metadata 是 JSON，不意味着所有 SessionRecord.request 内容都自动留存。[U `openai_endpoint_utils.py:23,47–94`；`session/samples/codec.py::SAMPLES_VALUE_SPEC`]

### 3.2 哪些 token 与 logprob 被保留、哪些进入 loss

首轮用选定模板渲染输入 ID，后续用存储 checkpoint 的实际 token 前缀，加上新追加的工具/用户等 suffix。session 强制 `logprobs=True`、`return_meta_info=True`、`no_stop_trim=False`，根据开关请求 routing/indexer replay；客户端 `input_ids` 被服务端覆盖。TITO session 不应设 `logprob_start_len=0`，否则全 prompt 打分损害 prefix cache；这与 §5 teacher 的离线 scoring payload 使用 0 是不同请求目的。[U `session/core.py::prepare_chat_request/chat_completions`]

响应必须有 `meta_info.output_token_logprobs`，且其条数等于 `completion_tokens`；token ID 与 logprob 分别取每项的第二、第一元素，不能从响应字符串推回。每轮 sample 初始模型输出 mask 全 1；工具调用、reasoning 若属于实际模型输出亦在此范围，没有另一个默认“thinking 不训练”开关。后续客户端注入的 assistant 消息也只是 prompt history，不会凭 role 自动变训练 completion。[U `extract_completion`；`merge.py::_compute_sample_from_openai_record`；`linear_trajectory.LinearTrajectory`]

多轮合并时 `tokens` 取后轮完整 TITO 序列，第一轮 prompt 之后的 observation/tool/template 增量计入 `response_length`，其 `loss_mask=0`、logprob 数值填 0 作占位；旧模型输出仍保留采样 logprob。故 **response_length 不等于参与 policy loss 的模型 token 数**。模型特定末尾 delimiter 可在允许的 `max_trim_tokens` 内裁剪；最后一轮允许裁剪量为 0。检查失败不是“猜一个 token 修回来”，而是 assert/422。[U `sample_utils.py::_merge_sample_pair`；`merge.py::compute_samples_from_openai_records`]

`max_seq_len` 包含 prompt、输出与环境观察。收集先逐轮检查预算，再 merge：某轮 prompt 已用满预算便不保留该轮；若还有输出余量则截断这轮输出，标 TRUNCATED，后续轮丢掉。merge 遇前轮非 COMPLETED 或新轮缺已启用的 routing/indexer replay 时停止在可用前缀。因此“所有模型调用全部成为训练 token”不是无条件保证。[U `truncate_samples_by_total_tokens`、`sample_utils.merge_samples`]

R3 是重放推理路由 expert 信息的能力，不是文本重分词。`merge_samples_with_addition_r3` 按连续 row patch 收集，最终覆盖 `len(tokens)-1` 行；控制面不能把 routed-experts 当每条 response 的独立、等长文本字段。返回给 agent 的响应会剥掉 routing/indexer 大载荷，原 SessionRecord 保留训练使用。[U `session/core.py::_strip_replay_payloads`、`merge.py::merge_samples_with_addition_r3`]

### 3.3 v1 线性轨迹与 v2 树不是同一种统计单位

v1 只允许尾部扩展，重试最多回滚 **一个本 session 生成的 assistant checkpoint**；第一次回复可回滚到空 session。跨多个 checkpoint 的历史回写被拒绝；客户端注入 assistant 并不增加这个回滚计数。返回一条 Sample。[U Agentic：Choose the session behavior；`linear_trajectory.py::MAX_ASSISTANT_ROLLBACK_STEPS/_try_detect_and_rollback_to_assistant_checkpoint`]

v2 是实验性 append-only tree：寻找完整 message path 能作请求前缀的最深节点，新 suffix 挂成分支；已有节点保留，length 终止的路径不能继续延长。原始每叶样本先经过 picker，再 postprocessor；wrapper 可以给一个原始 rollout 返回多条 Sample，保持同 rollout_id（代码仍留 index 问题 FIXME）。[U Agentic 同节；`session/v2/core.py::collect_samples`；`agentic_tool_call.generate`]

代码额外披露的默认语义不可遗漏：

- `picker_hub/drop_retries.drop_retries`：若一个叶子的同父节点存在更晚 commit 的 sibling，则它被视作被重试替代，按 commit 序号裁掉，长度或墙钟回退只作诊断；根叶保留。存储“未删除”不等于训练“都保留”。该规则是启发式 picker，不能解释为识别了任意分支的业务含义。
- `default_postprocess`：**picker 后**，共享 completion 只在保留叶中 commit 最早的一个叶拥有训练 mask，其他叶对应区间置 0；若 agent metadata 给了 trajectory reward，该标量赋给全部保留叶。不会自动提供每分支的独立 verifier reward。
- 服务端关键 metadata 保留权威；picker 只能无重复地选择输入对象的子集。hook 异常带 hook 身份返回 422。v2 参数显式排除 `group_rm`、partial、prefill 重算。[U 两个默认 hook、`arguments.py` v2 校验]

### 3.4 模型族、replay matcher 与验证

U 注册族覆盖 Qwen3/Qwen3.5/QwenNext、GLM-4.7 至 5.2、Nemotron3、Kimi2.5/2.6、MiniMax2.5/2.7、DeepSeek3.2/V4、Inkling。**不会自动推断模型族**；命名族绑定 `FIXED_TEMPLATE`、固定 kwargs、reasoning/tool parser，拒绝冲突模板覆盖；`default` 是自定义或 checkpoint 原生模板的 best-effort 路径。W 增列 Qwen3.6、Qwen3.8-27B (`qwen38small`) 和 Qwen3.8-Flash-Next (`qwen4exp`)，不能据此说 U 或当前 rh2 支持这些注册。

`strict` 对 role/content/reasoning/tool_calls 作既定归一化；`loose_tool_call` 额外接受 tool arguments 的等价 JSON 对象写法，仍检查 call ID、名称、顺序等；`role_content_only` 会忽略工具/思考差别，可能把不同历史压成同 lineage；也可加载可信同步自定义 matcher。匹配后存储前缀仍权威，仅 suffix 从客户输入新分词；Miles 不替部署方协调 stored call ID A 与工具结果 ID B。[U/W Agentic：Pick model、Choose replay matching]

验证应包括 `verify_chat_template.py` 的 CPU append-only token 序列检查和 `verify_session_tito_tokenizer.py` 的真实 GPU 推理检查。两者缺一不能称新增模型已通过官方要求。本任务没有运行这些模型验证。`tito_session_mismatch` 是 canonical 全量渲染与实际累计 token 的诊断，U `SessionCore._session_metadata` 记录它却不据其非空自动拒收；与此同时前缀/装配 invariant 的失败仍会硬报错。不要把“诊断不阻断”扩大成“完全没有 token 检查”。

## 4. 数据、Harbor 环境与 reward

### 4.1 官方示例真正提供的东西

U `examples/swe-agent-harbor-docker/README.md` 描述 GLM-4.7-Flash 同步 GRPO 与 Harbor agent server：每任务一个 sandbox、模型请求走 Miles session、Harbor 返回 verifier reward。README 指定 Harbor 分支 `harbor-miles-v0.20.0`，未在这份示例中钉 Harbor commit；旧稿记录的 `53a6e92` 是其当时取样，本次不把它提升为已重新核验的 Harbor 当前实现。

数据入口要求 `prompt`、`metadata.instance_id`，后者必须对应 agent server 已有任务目录。converter 可从 HF 或 JSONL 读数据，把原字段全放 metadata，加 `agent_name`/`split`，prompt 在配置键、problem_statement/instruction/prompt 间回退，支持 limit 与 append。**这是格式转换，不是去重、污染检查、环境可构建/可解性过滤或可信 public/private 材料划分。**它可原样写字符串 prompt；generic agentic 文档的 messages 合同仍需在真实 agent/loader 边界满足，不能把 converter 输出误写成已完成 messages 规范化。[U `download_and_process_data.py::convert_to_miles_format`]

| 漏斗对象 | 已披露 | 未提供的证据 |
| --- | --- | --- |
| 输入任务 | 支持 SWE-bench、Terminal-Bench、自定义 Harbor task，按 instance_id 寻目录 | 实际题单 revision、任务数、镜像数、许可审查、去重与污染方案 |
| 构建/验证 | 外部 Harbor 创建 sandbox 并执行任务/verifier | 构建成功率、gold/no-op/alternate-solution、flakiness、合法解误杀统计 |
| 训练消费 | README 运行形状为每步 4 prompt × 8 trajectory | 累计有效组、被过滤数、重复任务量、独立 held-out 题数 |

这些未知是检查两份正文、Harbor 示例 README/converter/调用端后仍不存在的实验披露，不表示整个 Harbor 生态从未实现过验证工具。没有沿来源无边界扩成 Harbor 安全审计。

### 4.2 失败不能一律映成 0 或一律 ABORTED

U `swe_agent_function.run` 向 `/run` 传 metadata、session URL（含 `/v1`）、`model=openai/<name>`、sampling_params 和 max_seq_len。正常响应提取 reward、exit_status、eval_report、agent_metrics；若响应无 reward 默认 0。配套 `generate.reward_func` 也是 metadata.get("reward", 0.0)。因此 reward missing 与任务真失败在示例标量层可能都表现为 0；示例不是严格四态评分合同。

该函数超时、取消或其他请求异常会返回 None；**generic wrapper 仍在 finally 收集此前 token**。agent 异常本身只记 warning；只有 collect 的 TimeoutError/TransportError 或空结果在 wrapper 中明确转 ABORTED。非 2xx collect 仍抛异常；422 装配错误不在该软失败分支。若已有完成轨迹被成功收集，Harbor 异常可能留下非 ABORTED Sample，随后示例 RM 用缺省 0 评分。只有 Sample 真为 ABORTED 时，fully-async buffer 才整组走 unused handler。[U `swe_agent_function.run`、`agentic_tool_call.generate`、`inference_rollout_common.generate_and_rm`]

README 建议 `--agent-timeout` 为外部权威 timeout，客户端 `AGENT_TRIAL_TIMEOUT` 默认 **7200 秒**且要更大；启动示例是 agent timeout **5400 秒**。这是避免客户端先放弃但远端 sandbox 仍占位的资源纪律。README 将客户端先超时表述为 aborted，代码如上存在条件性差异；以实际路径解释为准。oversampling 的可选 `abort(args)` 会按 session-server instance 调 Harbor `/flush`，可带 `HARBOR_ADMIN_SECRET`，缺 server URL 或 instance_id 则 no-op；flush 失败记 warning。不能将此 hook 当作任意崩溃下都成功释放环境的证明。

## 5. 训练语义、模型关系与 OPD

### 5.1 这不是固定 base→SFT→RL 配方

两份官方主文只定义 rollout/消费框架；输入 checkpoint 的预训练、SFT、mid-training 来源和顺序未披露。policy actor 更新后向 rollout engine 发布；若使用参考 KL，reference 与正在优化的 actor 分开；若选 PPO 还需要 value/critic；GRPO 不由这两份文档规定独立 critic。框架支持多种 estimator 与 custom loss，不能从 `--fully-async` 推出“固定 GRPO+某 IS 算法”。SFT loss 在训练 dispatcher 中有入口，但主资料没有 SFT 数据与训练实验。多模态在 TITO 明确不支持图像/视频，不能把 Miles 整体 VLM 能力移植为 session 能力。[U `loss.py::compute_advantages_and_returns/loss_function`、主文 Warning]

U 训练端先得到 reward/reference KL 与选定 estimator 的 advantage，若启用 OPD 再施加逐 token penalty，最后按开关做 masked advantage whitening。`use_rollout_logprobs` 决定旧 student 打分用 rollout logprob 还是 trainer forward 的 `log_probs`；不是所有配置都用同一分母。GRPO/GSPO 的 scalar reward 广播为逐 token returns，reward 组归一化属于上游 reward processing，不能仅看到此处广播就断言未做组统计。[U `loss.py:55–120`、`loss_hub/advantages.py::compute_advantages`]

进一步沿真实 batch 转换核对：默认 `train_data_conversion._post_process_rewards` 在 rewards_normalization 开启且 estimator 为 GRPO/GSPO/REINFORCE++ baseline 时，按 prompt group 分组，再按 rollout_id（回退 index/row）把兄弟叶折成一个 reward，要求同 rollout 各叶 reward 相等。先减组内 rollout reward 均值；GRPO/GSPO 且 grpo_std_normalization 开启、组内 rollout 数>1、std>0 时，再除以 `torch.std()` 的样本标准差加 **1e-6**，然后广播回叶。不是将每个树叶当独立采样计入组 baseline。自定义 reward postprocessor（包括 OPD 示例）优先返回，可替换这条归一化。若 group_index 和完整固定布局都缺失，代码回退为整批一组；不能当成身份缺失会自动 fail-closed。[U `train_data_conversion.py:172–271`]

同文件在 reward processing **之后**才将 `remove_sample` 的 loss mask 清零。因此 remove_sample 可能仍影响 reward 组统计，和 buffer 的整组 drop、v2 picker 删除叶、TRUNCATED 标记是不同处置。默认转换总会生成 `rollout_mask_sums`，把每个 rollout 的各叶有效 mask 求和再广播，下面的共享分母不是只存在于未接入的辅助函数。[U `train_data_conversion.py:59–101,162–169`]

标准 policy loss 先计算当前策略与选定 old score 的比率 ρ=exp(log p_new−log p_old)，逐 token（GSPO 另用序列级聚合）取 `max(−ρA, −clip(ρ,1−eps_clip,1+eps_clip_high)A)`；可选 dual-clip 对负 advantage 另截断。以上 ρ 是理想比率；U 实际 `_safe_exp_neg_ppo_kl` 先将 log-ratio 转 float、处理 NaN/±Inf，并夹到 **[-20,20]** 再 exp；这是 PPO ratio 的数值保护，不是后续 policy clipping 或 TIS ratio clipping。[U `math_utils.py:18–32,254–278`] 内建 TIS 再乘 `clip(exp(log p_trainer_old−log p_rollout),tis_clip_low,tis_clip)`；它和 PPO ratio 是不同的比率，内建 TIS 不改 loss mask。`icepop_function` 把区间外 IS 权重置 0；其他 custom TIS 可能改 mask。可另加 reference KL loss 与减 entropy bonus。这些是 U 默认 policy loss 的代码解释，**不是 rh2 faithful DIS 的替代定义，也不是 fully-async 自动选定的算法**。[U `loss_hub/losses.py::policy_loss_function`、`math_utils.py::compute_policy_loss`、`corrections.py`]

标准聚合（**非 rh2 faithful DIS 定义**）可写成代码等价式：

\[
S=\sum_i \frac{\sum_{t=1}^{R_i} m_{it}\ell_{it}}{\max(D_i,1)}.
\]

这里 i 是装配后的 sample，R 包含 response 对齐位置，m 为 loss mask，D 缺省为该 sample 的 mask sum，也可被 `rollout_mask_sums` 覆盖，使同 rollout 多叶共用分母。`calculate_per_token_loss=True` 则此函数返回 masked token loss **总和**，后续由训练后端完成归约；不能把上述 S 直接称最终 loss。`loss_function` 还按 num_rollouts/动态或固定 global_batch_size、microbatch 和并行布局缩放，token 日志计数对每个 mask sum 至少钳为 1。叶去重与分母是两个不同层次。[U `cp_utils.py::get_sum_of_sample_mean`；`loss.py:160–224`]

### 5.2 OPD 已有能力及当前路径的硬边界

OPD（on-policy distillation）让学生自己的轨迹接受 teacher 的分布监督；这是框架已有实现，不是 N11 两份网页额外证明的一组模型结果。补读 U 完整 `on_policy_distillation.py` 与 `loss_hub/opd.py`，以及参数校验和 teacher 前向调用。

| 能力 | U 实现与限制 |
| --- | --- |
| SGLang teacher | 外部 scoring endpoint 接收 **student 的 token IDs**，`temperature=0,max_new_tokens=0,return_logprob=True,logprob_start_len=0`；抽取 response 位置 teacher logprob。无异 tokenizer 翻译层，使用者必须保证 ID/词表语义可比 |
| Megatron teacher | `opd_type=megatron` 要求 teacher checkpoint；actor 装载 `teacher` backup，切模型 forward 得 teacher_log_probs，再回 actor 路径。teacher score detach，本段没有 teacher 优化更新规则 |
| 多 teacher | `--opd-teacher-urls NAME=URL` 按 metadata 配置键选一个 teacher；未知/缺名走保留 `default`，没有 default 就报错。是逐样本路由，不是对多个 teacher logits 做融合 |
| sampled-token | top-k=0：只取实际 sampled token 的 teacher score。默认 pure OPD postprocessor 将 scalar task reward 全设 0，学习信号来自 KL penalty；不是自动混入 Harbor task reward |
| top-k | 五种集合：only-student、only-teacher、intersection、union、xor；权重模式 student_p、teacher_p、none。需要的分布可从 teacher top-k 或交叉 scoring 取得 |
| 兼容性 | U 只允许 SGLang top-k。除 only-teacher 外的 top-k student-side strategy 需要 legacy rollout v1 的 `opd_student_top_logprobs`，而 fully-async 明确拒绝 legacy API。因此 **U 当前 fully-async 不能直接搭这些 top-k strategy**。这里的 legacy rollout v1 与 session v1 是两个不同“v1” |

代码等价的 sampled-token 信号为：

\[
k_t=\log p_{\mathrm{old}}(y_t\mid h_t)-\log q(y_t\mid h_t),\qquad A'_t=A_t-\beta k_t.
\]

p_old 是固定 student scoring 分布（由上述 logprob 开关选取），q 是 teacher，β 为 `opd_kl_coef`。这不是在当前策略 logits 上直接反传的 full-vocab KL；score detach 后作为 advantage 修正进入所选 policy loss。理想同分布采样条件下，取期望对应 student→teacher reverse KL；实际异步/不同 score 来源时不能不加条件地称其无偏 on-policy KL。[U `loss_hub/opd.py::apply_opd_kl_to_advantages`]

top-k 代码计算
\[
\hat k_t=\sum_{v\in S_t} w_{tv}(\log p_{tv}-\log q_{tv}).
\]

除 xor 外 w 在所选集合内按 exp(student logp)、exp(teacher logp) 或均匀权重归一化；xor 则不归一化，none 模式权重各为 1。空集合产生 0。**它是可选的加权截断估计，不保证是非负或完整词表 KL**，尤其 teacher_p/none 不应统称标准 reverse KL。`opd_topk_per_position` 可避免全局 token-ID union 在每位置密集评分，需打过对应补丁的 server，默认关闭。[U `on_policy_distillation.py::_compute_topk_reverse_kl/_reward_weights/reward_func`]

session wire 没有自动带 teacher_log_probs/opd_reverse_kl；这些可由下游 reward processing 产生。但 v2 默认 postprocessor 若已把 Harbor trajectory reward 赋为 `Sample.reward`，`generate_and_rm` 仅给 reward=None 的 leaf 调 RM，因而原样 Harbor v2 + OPD RM **不会自动调用 teacher**。要组合任务 reward 与蒸馏信号，须明确评分/后处理接口，不能靠两个 flag 叠加。`sample_utils` 存在 OPD 对齐合并支持也不证明本 session wrapper 已生产 student top-k。未查到本资料为特权上下文、self-distillation、异 tokenizer 或 teacher 持续更新给出的 agentic 实验配置；不能把可编程 hook 说成已验证的算法。

## 6. Fully Async：调度、消费、权重与 staleness

### 6.1 三个容易混淆的单位

入口 `train_async.py --fully-async` 使用 class-based rollout API。U `_resolve_rollout_functions` 排除 legacy API、多 LoRA、colocate、另指定 rollout-function-path、partial、abort、prefill logprob 重算和 rollout-all-samples-process hook；这些是该版本组合约束，不等于框架永久不支持相关功能。

设 B=`rollout_batch_size`（**prompt group 数**），G=`n_samples_per_prompt`（每组 trajectory 数），C=`async_max_concurrent_samples`（trajectory 额度）。缺省 in-flight group budget 为 B；指定 C 时 U 实际代码为 `max(1, C // G)`，有效额度是其乘 G，**不是恰好 C，也不能把 C<G 时说成零并发**。[U `FullyAsyncRolloutFn._max_in_flight_groups`]

sample granularity 下完成一个 `generate_and_rm` task 就释放一个 slot（非 group_rm 时包括其逐样本评分阶段，且 callback 在成功/异常/取消均运行；group_rm 的组级 RM 在这些 task 完成后执行，所以 slot 可先释放），空余足够 G 才整体提交新 prompt group，释放者可来自不同旧组。group granularity 则等整个 group 完成。trainer 仍等 B 个完整 group，绝非单个完成叶就立即 optimizer step。group 由 `asyncio.gather` 汇集，子 task 抛错会取消并等待 siblings，然后向上传播。[U `submission_scheduler.SampleBackfillSubmission`、`inference_rollout_common.generate_and_rm_group`]

worker 首次 train 调用时启动，此后持续 `_worker_loop`；它将完成组 put，trainer `_drain` 等足 B、按 first sample index 排序、再运行批级 filter。持续生产只消掉部分等待：空队列无数据仍要等，满队列 put 背压会阻塞生产端。理论上循环时间可从 rollout+train 向二者 max 靠近，是 U 文件 docstring 的理想解释，不是测得加速比。

### 6.2 put 与 get 的处理责任

| 阶段 | 默认行为 | 对训练/补采的含义 |
| --- | --- | --- |
| put：任意 member/leaf ABORTED | 全 group 不入存储，走 unused handler | drop 丢弃；retry 重置原 prompt samples 后回 data source 重新生成 |
| put：dynamic filter reject | 全 group 丢弃 | **不走 retry**，不是只把一个成员 mask 归零 |
| bounded FIFO | 容量 `floor(factor×B)`，factor 默认 2.0 且容量至少 1 | 单位 finished group；存满等消费，不是淘汰最老元素 |
| get：staleness>N | 出队后判 stale，走 unused handler，继续找组 | N 缺省 None，关闭该过滤；等于 N 可用 |
| full batch：sample filter | B 组齐并排序后调用 | 外部 batch hook，与 buffer 三方法合同分开；本体未保证任意 hook 删除后自动补回 |

staleness 的代码定义：
\[
d(g)=v_{\mathrm{published}}-\min_{s\in g,\,v\in s.\mathrm{weight\_versions}} v.
\]

版本是 engine 已发布的计数，不是 wall-clock 秒数或 optimizer mini-step 数；嵌套 leaf 会展开取最老值，`Sample.oldest_weight_version` 只保留能按非负整数字串解析的项。U/I 的 group helper 都忽略没有可解析版本的成员：整组没有任何可解析版本时才得到 None。U 在 oldest 或 current 缺失时跳过判定；I 对声称 formal 的组在**整组 oldest 缺失或 current 缺失**时 typed fatal，并对任何组的负 lag typed fatal，记录 drop/consumed 事件。**此处本身不证明 formal 每个 member/leaf 都有完整版本事实**；那是其他交付校验的职责，不能由 buffer 这一检查反推。[U/I `fully_async_data_buffer.py::group_oldest_weight_version/get`]

自定义 `DataBuffer` 拥有 put/get/get_metrics 的全体 group 语义，不能继续假定默认容量/过滤 flag 对它生效。retry 是 prompt 重新生成，**不恢复已完成 token，也不是 partial resume**。只有所消费组才进入常规 batch reward/advantage 处理；被 buffer 丢掉的组不参与该训练 batch 的 group statistics。

### 6.3 权重暂停、partial 与版本记录

Fully Async 文档给出每 `update_weights_interval` 步暂停、同步、恢复：`retract` 将在飞 request 放回等待队列并重算 KV；`in_place` 冻住后沿用 KV；abort 杀请求，因此 U/W 的 fully-async 都拒绝 abort。更新期间仍有短暂停顿，不能逐字把导言的“never waits”解作从不暂停。

**版本差异/文码差异**：U Agentic 说两个 session 版本均拒绝 partial 和 abort、使用 in-place；U args 明确全 session 拒绝 abort，v2 拒绝 partial，但没有全 session v1 partial 校验，也没有强制全部 session 必须 in_place。W Agentic 改成所有 session 拒绝 partial，并解释 R3：非 retract 取增量 rows，retract 每轮取完整 rows 且提示大 payload。远端 d2fc97ce `arguments.py` 的全 session partial 断言与 retract warning 支持这一更改；warning 还明确保留 **SGLang retract-mode weight-update R3 存在已知问题待修复** 的 TODO，不能将该组合描述为已无条件验证。U `session/server.py:46` 则仅在 in_place 时启用增量 R3。未把 W 解释套到 I。[U/W Choose the session behavior；U args:2887–2911；远端 args 相关断言]

U session merge 仅读逐轮单数 `meta_info.weight_version`，没有把跨权重更新请求的 per-token `weight_versions` spans 送到 sample；I session merge 仍是此点，虽然 I 的通用 `Sample.update_from_meta_info` 经 0008/0009 加入 spans 校验。**后者不自动修复前者：session merge 有 TODO unify，走不同入口。**I 还新增 sampling mask 运输，亦不等于逐轮实际 sampling 参数完整导出。

U `train_async.py` 提前发起下一批 generate/drain，publish 前等这批返回；因此 buffer `get` 可能按 publish 前版本判下一批。I patch 0014 对 fully-async 改为上一轮 publish 后 just-in-time drain；背景 worker 仍持续，改变的是取 batch 时点。I 0002/0003 对全局零信号优化步及 weights_dirty 门控避免虚增 publish；0015 检查每个 engine 版本收敛；0016 只续接冷恢复已发布计数，不重放 pending 队列。均属当前集成改动，不是 TITO 官方原文承诺。[I `train_async.py::train`；manifest 对应 patch；§10]

## 7. 评测、度量与已披露运行预算

### 7.1 三种评测与快照代价

| 模式 | 原文合同 | 不能省略的代价/约束 |
| --- | --- | --- |
| Shared engines（缺省） | 暂停 producer **新提交**，在飞请求可完成并入 buffer；eval 后恢复 | 耗用 rollout engines，生产约损失一次 eval 时长；不是统一 abort 在飞请求 |
| Dedicated fleet | `--eval-num-gpus N` 独立 router/fleet，从 HF snapshot 加载 | GPU 从 job 预算分出；eval async，但 export collective 和 overflow backpressure 仍可卡 trainer，所以表格“training never pauses”需读后文限定 |
| External checkpoint backend | `CheckpointEvalFn.evaluate_checkpoint(checkpoint_dir,input)`，可 `EvalSkip(reason)` | 不在训练 job 划专用 fleet，不等于评测资源免费；外部 API/自启服务仍有资源和费用 |

fleet 与 external checkpoint backend 互斥；普通 custom eval function 则可照常对 fleet generate。fleet 继承 rollout SGLang 参数并允许 `--eval-sglang-*` 覆盖；TP 由 `eval-num-gpus-per-engine` 单独决定，TP 不同时 dp/pp/ep/attn_cp 默认重置 1，避免继承不合法布局。[U Fully Async：Evaluation 全节]

snapshot 有每点新 export（`eval-hf-dir`，可 tmpfs）与复用 periodic HF save 两路；后者要求 eval_interval 为 save_interval 的倍数。export 是全 train actor collective，主循环要等；默认 overflow backpressure 等最早 pending eval，skip 则丢该点。eval 内部串行，`eval-max-in-flight` 只允许 export 领先更多点，不增加同时 eval 数。保留占位为 keep-snapshots + max-in-flight，默认共 **4 个 model-size 目录**；原文估 **4B bf16 约 32 GB**，这是快照存储而非训练显存预算。

### 7.2 指标要以真正分母解释

- 队列：queue_size 是存储中的完成组数；aborted/stale filter counters 是组数。zero queue 提示 rollout 或任务/评分/过滤供给不足；full queue 提示消费慢，不能仅凭这一个数判定某 GPU 内核低效。30 秒 `No completed rollout groups` 是 starvation warning，U 本身不是 30 秒自动熔断。
- **文码口径冲突**：U/W 文档说 avg/max_staleness 对已消费组，buffer_avg/max 对仍在队列组。U `DefaultDataBuffer.get` 在比较 N **之前** append `_metric_consumed_staleness`；I:300 附近同样如此，所以前一对实际包括 get 扫过但因 stale 拒收的组。若有 lag=5 的丢组及 lag=1 的收组，报告 avg=3，不是 consumed-only 的 1。该例是代码推演，非实测；I 的 `group_consumed` 事件才可另算被接受组口径。本任务不修改该代码。
- eval：skipped_busy/export_failed/ckpt_missing（无 `.complete`）/crashed，以及 EvalSkip 自定义 reason；lag_steps 说明点完成晚了几步。`weight_version/mean == eval/step` 且 mixed_version_ratio=0 是官方预期权重诊断；shared 使用最近广播权重，checkpoint backend 使用该 snapshot。**I 零信号跳 publish 与冷恢复让 rollout step 和发布计数关系需要按项目事件映射核对**，不机械搬这条等式作 rh2 准入。
- 性能：engine `sglang_num_running_reqs` 比较并发分布；cache 指标 `sglang_cache_hit_rate` / rollout `prefix_cache_hit_rate`；后者源于累计 cached prompt tokens / total prompt tokens。原文 coding workload 的 **>90%** 是调优预期，不是实验保证、训练收益或统一阈值。排查 router、KV 空间、rollout/train/工具耗时。
- 自定义 rollout/eval log function 返回 True 才跳默认日志；只转发应返回 False。改变 buffer 指标内容须改 get_metrics，不只是 logger。Harbor agent metrics 忽略未报告值而非补 0；`total_tool_time` 若有则进入 `Sample.non_generation_time` 供吞吐会计扣除，不能把扣除环境耗时后的数冒充端到端 SWE 成本。[U Metrics 全节；`generate.py::aggregate_agent_metrics`、`agentic_tool_call.generate`]

### 7.3 数字属于哪个 workload

| 来源/实验形状 | 已披露数字 | 解释边界 |
| --- | --- | --- |
| Harbor README §3，同步 GLM-4.7-Flash + mini-swe-agent + TB2 | 1 节点 **8 H200**；每 GRPO step **4×8=32 trajectories**；max seq **65536**；示例 num-rollout **200**、save interval **20**；约 **10 分钟/step**，长尾可数倍 | 作者多日运行经验，非 fully-async 对比、非准确 GPU-hours 总账。未给 score 曲线、held-out 或重复误差 |
| 同示例 U `run.py` | temperature **0.8**，单次 response max **8192**；trainer TP4/EP8/PP1/CP1；dynamic batch max tokens/GPU **16384**；CPU optimizer offload；Adam lr **1e-6**，weight decay **0.1**，β1 **0.9**/β2 **0.98**；GRPO，KL loss **0.01 low_var_kl**，entropy **0**，clip lower **0.2** / upper **0.28** | 是公开启动配方段，不冒充所有历史 run exact resolved args。rollout engine 1 GPU、mem fraction **0.7**；65536 是 session 总上下文，不是每次新生成上限 |
| Fully Async Examples：Qwen3-30B-A3B | TP8/EP8，一台 8-GPU rollout engine | 文档拓扑示例，不是 rh2 的 8 卡机器可原样照搬的分配 |
| Fully Async Examples：GLM-5.2 744B-A40B Daytona | **16 GB300 节点**，8 train/8 inference；**128 在飞 trajectory**，**64-sample train batch**，shared eval | 文档披露的示例配置，本次未读完该 launcher，不能推出数据量/通过率或其总 GPU 时长 |
| Qwen3.5-4B eval 示例 | fleet/external 两后端切换 | 是入口示例，没有给同预算性能消融 |

Fully Async Examples 文案说“四个”脚本，U/W 可见表实际 **三行**，本文按三行记录，没有补造第四个。资料没有 pass@1/pass@k/avg@k 数字、固定 benchmark revision、对照消融、显著性或负向学习结果；不能用 >90% cache 或“多日运行”替代能力评估。

## 8. 开放资产、成本与复现程度

官方仓库提供 session、buffer、training hooks、model registrations 和示例代码；本地 U/I 使版本行为可读，但不意味着训练完整可复现。本任务只做文档和静态源码检查，没有训练、GPU 租用、Docker task 验证或吞吐测试。GPU 型号/拓扑与局部时间有披露，总 rollout/训练/teacher/数据生产/eval 成本没有完整分母，不能将 8×H200×约 10 分钟乘示例步数当作作者实测总成本。

复现一个相近 run 仍需模型 checkpoint/revision、SGLang/Megatron 构建组合、Harbor 精确版本、任务目录与镜像、agent 版本、实收采样参数、resolved args、评分与 held-out 协议。I 的依赖 pin 可从 manifest 复用，但这是本项目固定组合，不等于全部上游示例版本。

官方给出的验证入口分两层：新模板 CPU+真实推理 TITO checks；运行时看 Miles rollout 与 Megatron train/step、trace 文件。Harbor README §4 特别提醒 W&B 部分上传失败会伪装成 reward 曲线停滞，先检查 `train_data/<step>` 和 `rollout_data/<step>.pt`。文件有增长只能证明执行进度，不证明 token/reward/梯度语义正确。

## 9. 证据边界、冲突与未知项

| 问题 | 已查范围 | 可说与不可说 |
| --- | --- | --- |
| 新网页是不是本项目采用版本 | U/I HEAD、工作树、W 快照、远端 d2 参数相关段、manifest | 已分清三版本；未验证最新整树、未升级集成 |
| partial/pause 是否兼容 | U/W Agentic、Fully Async、U/远端 args | 有明确版本/文码差异，详 §6.3；不发明 v1 partial 可用的运行保证 |
| 是否保证不丢 token | U core/checkpoint/merge/v2/codec | 有 exact token 主路径及硬检查，但 mismatch 诊断、截断、picker、关闭竞态等有边界 |
| 是否导出逐 token 行为版本/采样来源 | U/I session merge/codec、I update_from_meta_info 与 manifest | session 单数版本残余尚在；通用 spans patch 不等于 session 已补齐；逐轮请求参数未自动跨 wire |
| OPD 是否适配 FA+黑盒 agent | U OPD producer、consumer、arguments、session fields | sampled/top-k/teacher routing 确实存在，student-side top-k 与 class API 有约束；未验证端到端 teacher latency、漂移、特权上下文或异 tokenizer |
| 安全、DPO/RLHF偏好、多模态/数学配方 | 两份全正文、上述训练链与示例 | 主文无这类训练实验；TITO 明确无 image/video。不能推成 Miles 全框架无这些能力 |
| 环境可信与 benchmark 成绩 | Harbor 示例 README/converter/client/RM，旧稿仅线索 | 没有 verifier 对抗/污染/held-out 实验足以背书本项目 reward；不替 Harbor 全生态下安全结论 |

额外的代码边界：U v1 `chat_completions` 在 backend 返回后若 session.closing 或 checkpoint 已改变，会向 client 返回响应但跳过 state update；v2 同样检查 closing。这支持旧稿“特定关闭竞态有已交付未记账可能”的窄表述，不能外推为任何正常请求都会丢 token。原始 `stream=true` 是 backend 完整返回后合成单 SSE chunk，不是真逐 token 在线 streaming。session 身份 UUID/URL 与认证/attempt 撤销是两类问题；本任务没有重新审查网络部署与 Harbor 安全边界。[U `session/core.py` 模块说明与 `chat_completions`，v2 同名符号]

旧稿保留不删，主要更正/限定如下：

1. 旧稿 I HEAD `63c7a94e7` 已过时，补录到 `98a0272e4`；session per-token span 缺口仍成立，不因新 patch 名称而消失。
2. 旧稿/示例文案把客户端超时直接视为 ABORTED，必须改成 §4.2 的分支语义；成功收集旧轨迹可能保留 completed/truncated 并默认 reward 0。
3. “token 不经 Harbor，由 Miles session 捕获”这一基本归因成立；“Harbor 不回 token 所以只能重分词”不成立。现有 exact token、树叶去重、queue/backfill、OPD 不应列成 rh2 必造组件。
4. 旧稿将补齐 TITO 缺口等价成“必然重建形态乙”、terminal 评分“必然在被 agent 碰过的原容器内”，都是具体方案判断，不是上游代码证明的唯一可行性结论；本篇不沿用工作量估计或据此新定案。
5. 新增文码冲突记录：staleness 指标分母、v1 partial 校验与 session in-place 文案；不能照网页复制为当前代码事实。

## 10. 对 RepoHarness 项目一的意义（2026-09-07 映射）

状态基线来自 [CURRENT-STATE-BRIEF（2026-09-05）](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md) 与较新的 [2026-09-07 项目一设计建议](../../../agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md)。后者明确是咨询建议，不改 06/C 包：首训 taskset、loss 终选、staleness N、工具面与 GPU 预算等未因本文定案。主资料提供的仓库 HEAD 为 `ce2009f879cf38071d7898a1387e01d4e27741d6`，未提交状态文档按其明确日期使用。未全仓检索来断言不存在更近更新。

本次窄读 `rh2/src/repoharness2/adapters/miles/generate_fn.py::__call__`、`adapters/slime/capture_wire.py::install` 与 vendored `slime/agent/trajectory.py` REALIGN 段，核定当前入口复用 `rh2_custom_generate` 和捕获接线；不是 U 的 OpenAIEndpointTracer。REALIGN 用重分词 prompt 替换最近 response span 并 mask=0，是当前路径对 drift 的处理；TITO 的存储实际 token 前缀思路可以减少这种 drift 来源，但移植收益与协议适配尚未实测。

| 候选借鉴 | 已核来源 | 归属与适用条件 | 最小验证/指标（建议，非新定案） |
| --- | --- | --- | --- |
| TITO exact token + template/matcher 接口 | §3、U session | **上游已有**；rh2 增量应限于当前黑盒 harness 的调用事实/采样参数/身份/spans 边界，先评估窄接线，不默认重造轨迹系统或升级整 fork | 固定一段真实多轮 trace，含 tool JSON 重排/reasoning replay，对拍实际 token、loss mask、版本跨度；计 REALIGN 丢训练 token 比例 |
| 完整组 FIFO + sample backfill | §6 | **上游已有**；I 已有 consume-time 与事件窄增量，不再建第二套 staleness authority | 按原 prompt group 对比提交/完成/拒收/消费；看端到端有效 policy token/GPU-hour，而非发起数 |
| 评分与 task 控制面 | §4、§9 | **rh2 应用层职责**：trusted task、fresh grader、失败分类；官方 RM 的默认 0 是示例行为，不是项目可信评分合同 | 同任务区分 test fail、环境故障、collect 失败、missing reward，核它们实际如何进入/退出组 |
| eval fleet/external dispatcher | §7 | **上游已有，按预算选择**；8 卡首训不能为“异步”强行另划 fleet | 记录 export 时间、eval lag/skip、实际 snapshot/发布版本；held-out 与环境/采样预算一致 |
| OPD producer/consumer/routing | §5 | **上游已有；当前配方暂未采用**，student-side top-k 组合受 U 限制；不能只加 flag 宣称 FA+TITO+MOPD 就绪 | 若以后选 OPD，先做同 ID 词表、masked positions、teacher timeout 与版本固定的离线/小样本 contract 验证 |
| staleness metric 口径校正 | §7.2 U/I 代码 | **窄可靠性候选**，本任务只登记不修 | 基于 group_consumed 与 consume_stale_drop 各算分布，对照内建聚合，避免用错误分母调 N |

可支持项目叙事的是：识别并验证真实 harness→推理→训练消费的静默错误边界，诚实区分成熟上游与窄集成贡献。不能据本笔记声称自研 fully-async/TITO/OPD，不能将本地测试数、patch 数或上游运行经验写成自身学习收益。有效任务生产成本、吞吐改善、held-out 学习结果仍需项目实测。

## 11. 快速定位与关联阅读

- token/logprob/mask/树叶 → §3；U `session/samples/merge.py`、`generate_utils/sample_utils.py`、v2 默认 postprocessor。
- reward/timeout/Harbor → §4；U 示例 `swe_agent_function.py`、`generate.py`、README §1/§4。
- OPD 公式与组合限制 → §5；U `on_policy_distillation.py`、`loss_hub/opd.py`、`arguments.py`。
- queue/消费/版本 → §6；U/I `fully_async_data_buffer.py` 与 `train_async.py`。
- eval/预算/诊断 → §7；原文 Fully Async 的 Evaluation/Metrics 和 Harbor README §3。
- 相关资料编号：N10 Forge（队列策略比较）、N12 版本化错误案例、N04 verifiers/prime-rl、E7 MOPD、R14/R15 compaction/SAO。未产出文件不造链接。

## 12. 独立检查与修订记录

按用户 2026-09-07 的要求，初稿后在本任务内安排 **GPT-6 Astra / high、干净上下文（fork_turns=none）** 独立审查。审查者先从两份 U/W 原文目录建立覆盖表，再读初稿与关键源码；不修改作者正文，不递归扩大团队。[完整审查与作者逐项处理](reviews/05_N11_review.md)。

独立审查确认两份主文的后训练章节覆盖完整，没有遗漏的大块正文/附录；提出五项需要收紧的事实，均已修订：

| 发现 | 处理与证据 |
| --- | --- |
| R1：缺版本检查被概括得过强 | §6.2 改成整组无可解析 oldest/current 缺失才走相应 formal fatal，部分成员缺版本不由该 helper 保证；U/I group helper 与 I `_judge_consume_time_staleness` |
| R2：v2 已赋 reward 会跳过 teacher RM | §5.2 补 reward=None 才评分及组合 OPD 所需的显式接线；U v2 postprocessor、`generate_and_rm`、OPD postprocessor |
| R3：sample slot 是否等评分 | §6.1 区分逐样本 RM 与 callback 后才执行的 group_rm；U `generate_and_rm_group` |
| R4：真实符号与数值保护 | §5.1 修正为 `policy_loss_function`，补 PPO log-ratio 非有限值处理及 [-20,20] clamp；U `losses.py:62`、`math_utils.py:18–32,254–278` |
| R5：retract/R3 限制 | §6.3 明确远端 warning 的 SGLang 已知问题，以及 U 仅 in_place 启用增量 R3；远端参数代码、U `session/server.py:46` |

审查期间另沿源码补全组级 reward normalization、默认 rollout 共享 mask 分母及 remove_sample 在 reward processing 之后的顺序，审查者已核对。R1/R2/R3/R5 在正式审查中已复读确认；R4 按其指定原始代码完成修正，并已由同一独立审查者在审查文件 §7 复核确认。R1–R5 均已完成修订与独立复读。

**阅读质量边界**：所有结论仍是注明版本的文档/静态代码事实或明确标注的推论；没有产生 GPU、训练或环境实测。没有完整核验最新远端整树、完整 Harbor verifier/安全面、Daytona launcher 的 resolved 配方或所有 eval 内部代码；这些缺口在 §8–§9 和审查文件保留。本任务没有修改训练代码、共享索引或项目决策。

**本任务精读完成（2026-09-07）**：主文覆盖、版本区分、独立审查及全部修订已完成；实际运行与来源范围限制保持上述口径。
