# I01：官方实现对照与替代方案反证

日期：2026-09-08。角色：Falsifier / Simplifier。范围：侧边栏讨论第 8 轮、I01–I20 中与动作覆盖、上下文、GRPO 有关的边界；不替 owner 决定表示或实现方案。本轮只核固定官方源码及最小 CPU 夹具，没有改训练实现、依赖或既有定案。

**主要结论：保留原始输出 token，与保留该输出生成时的完整条件前缀，是两个要求。** 有条件的追加式推理可以同时满足两者；在训练装配时把旧输出替换回已经发生过的另一份输入，则不能自动满足第二个要求。官方实现提供了“完整前缀成立才合并，否则保留另一条训练序列”的直接参照，无须先建长期状态机。

## 1. 固定版本与证据等级

以下 main 均在本轮联网读取，未更新本地 `reference/` 工作树。不要用本地中文导览中的“最新”替代这些 pin。

| 范围 | 本轮固定版本 | 解释 |
|---|---|---|
| verifiers 官方 main | `27bbd216df0af719a43705866b2cf6139bcc95de` | [固定提交](https://github.com/PrimeIntellect-ai/verifiers/commit/27bbd216df0af719a43705866b2cf6139bcc95de)。本地参考仍是 `5885ab9c`。 |
| Prime-RL 官方 main | `04a61d3b75c3c99f263b2c133e822f998909adf7` | [固定提交](https://github.com/PrimeIntellect-ai/prime-rl/commit/04a61d3b75c3c99f263b2c133e822f998909adf7)。本地参考仍是 `df2acf48`。 |
| Prime-RL 实际 verifiers 子模块 | `828488fffe31aa3332b9d1bd4bd9ee320e375cf1` | 此 pin 的 `clients/train.py`、`graph.py`、`trace.py` 与上述独立 main **逐字节相同**；只核了这三个文件，不能外推整个仓库等同。 |
| Prime-RL 实际 renderers 子模块 | `f91c3e7061ce50ea405cdf54fd419a45cb51a152` | 以下 bridge 结论使用此依赖版本。 |
| verl 官方 main | `0d3f56a8980a55bfbbf1214ea54fa1b32ca1405c` | [固定提交](https://github.com/verl-project/verl/commit/0d3f56a8980a55bfbbf1214ea54fa1b32ca1405c)。本地参考仍是 `ba8cfb6d`。 |
| verl-recipe 官方 main | `7f14b203934a981664b295696e930f9276825bf0` | LangGraph recipe 的 [REQUIRED_VERL.txt](https://github.com/verl-project/verl-recipe/blob/7f14b203934a981664b295696e930f9276825bf0/langgraph_agent/REQUIRED_VERL.txt#L6) 固定的是旧 core `bcb638649a50e58494a8ddd92085ad1174f674b8`；本轮没有验证它与最新 core 的兼容性。 |

下文“官方声明”指文档/注释中的设计主张；“源码实证”指明确函数与条件；“推论”是对本项目的含义，不能当作该框架的实测结果。

## 2. verifiers → Prime-RL：有条件追加，完整前缀失败时分叉

**源码实证：精确捕获发生在训练客户端。** `renderers.client.generate` 发送 `token_ids`，取引擎返回的 `choice.token_ids`；`_parse_completion_logprobs` 检查长度、每项 `token_id:<id>`、数值有限性。`TrainClient.response_from_generate` 把实际 prompt、completion 和 logprobs 放入 `TurnTokens`，不是对最终 transcript 重新分词来恢复动作。[生成与检查](https://github.com/PrimeIntellect-ai/renderers/blob/f91c3e7061ce50ea405cdf54fd419a45cb51a152/renderers/client.py#L137)、[TurnTokens 构造](https://github.com/PrimeIntellect-ai/verifiers/blob/27bbd216df0af719a43705866b2cf6139bcc95de/verifiers/v1/clients/train.py#L101)。

**源码实证：追加有明确前提，不是所有历史都强制追加。** `TrainClient.get_response` 只有在存在 `PendingTurn`、prompt 无多模态内容、尾部为若干 tool 消息加可选末尾 user 消息时尝试 bridge。`PendingTurn.previous_token_ids()` 还要求匹配路径末端是实际 sampled assistant，且 sampled mask 是连续后缀；返回的是该路径的**完整旧 prompt 与原始 completion**。[客户端条件](https://github.com/PrimeIntellect-ai/verifiers/blob/27bbd216df0af719a43705866b2cf6139bcc95de/verifiers/v1/clients/train.py#L381)、[锚点构造](https://github.com/PrimeIntellect-ai/verifiers/blob/27bbd216df0af719a43705866b2cf6139bcc95de/verifiers/v1/graph.py#L457)。

`prepare_turn` 从根开始按 `(parent, message_hash)` 解析消息路径。hash 包括早期 user/tool 内容、reasoning、工具调用及调用 ID；普通工具 JSON 的键顺序和空白被规范化。因而正常工具参数格式变化可以匹配已有采样节点；真正的早期消息变化不会仅凭“最后一条 assistant 的位置”继续旧路径。[消息匹配](https://github.com/PrimeIntellect-ai/verifiers/blob/27bbd216df0af719a43705866b2cf6139bcc95de/verifiers/v1/graph.py#L264)、[路径解析](https://github.com/PrimeIntellect-ai/verifiers/blob/27bbd216df0af719a43705866b2cf6139bcc95de/verifiers/v1/graph.py#L524)。这仍只是本轮检查的消息身份规则，不是所有模型配置与工具 schema 变化的完整正确性证明。

`bridge_to_next_turn` 返回 None 时，客户端完整重渲染。`DefaultRenderer` 恒返回 None；Qwen renderer 在 thinking-retention 规则要求重渲染时也返回 None，并有模型特定的回合结束边界处理。所以“Prime 从不重渲染”超出了源码。[客户端 fallback](https://github.com/PrimeIntellect-ai/verifiers/blob/27bbd216df0af719a43705866b2cf6139bcc95de/verifiers/v1/clients/train.py#L415)、[DefaultRenderer](https://github.com/PrimeIntellect-ai/renderers/blob/f91c3e7061ce50ea405cdf54fd419a45cb51a152/renderers/default.py#L231)、[Qwen bridge](https://github.com/PrimeIntellect-ai/renderers/blob/f91c3e7061ce50ea405cdf54fd419a45cb51a152/renderers/qwen3.py#L308)。

**源码实证：训练合并检查的是完整条件前缀。** `_commit_turn` 在生成后从 offset=0 逐节点比较存储 token 与这次实际 `prompt_ids` 的对应切片；第一个不等的节点起不再复用。随后用此次实际输入建立 mask=False 的新节点，用实际输出建立 mask=True 的 sampled 节点。旧节点没有被 REALIGN 清零，也没有因为新输出短而被删除。[关键循环](https://github.com/PrimeIntellect-ai/verifiers/blob/27bbd216df0af719a43705866b2cf6139bcc95de/verifiers/v1/graph.py#L658)。

这不只是保存 `A1`：若 `P2` 的**初始 prompt** 改变，即使其中仍出现相同的 `A1`，也不能把旧整条路径作为 `A2` 的条件。官方 `test_renderer_level_break_forks_by_token_id` 明确检查漂移后留下 `[1,2,3,4,5]` 和 `[1,2,3,99,5,6,7,8]` 两条真实路径。[官方测试](https://github.com/PrimeIntellect-ai/verifiers/blob/27bbd216df0af719a43705866b2cf6139bcc95de/tests/v1/test_graph.py#L364)。

**官方声明与当前落点要分开。** Prime-RL 算法文档把它称为 best-effort interleaving：前缀断裂则开始另一条 sample。当前代码中的精确匹配主要在上述 verifiers graph；Prime-RL 的 `trace_to_samples` 消费已有 branch，不再凭文本重建。文档中极端重复前缀的成本描述只表达规模趋势，不能直接当本项目 GPU 吞吐预测。[官方说明](https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/docs/algorithms.md#L454)、[转换入口](https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/trajectories.py#L136)。

**源码实证：分支中的 mask=0 可能是正确去重。** `iter_trainable_branches` 用 `trained_nodes` 让同一个 sampled 节点只在第一个可训练 branch 中计算 loss；后续 branch 保留其 token 作为上下文。这与“旧动作在所有 sample 中都被 mask 掉”不同。若分段，必须统计同一次实际采样动作在**全部 sample 的并集**中是否仍有一次 loss，而不是要求每份重复前缀都 mask=1。[去重实现](https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/trajectories.py#L91)。

## 3. branch、subagent、compaction 的实际边界

**源码实证：物理分支不等于语义 subagent。** graph 的 `parent` 表示精确 token 前缀；当前还另有 `semantic_parents`，通过 harness 提供的请求 ID 与 ACP metadata 声明 `continuation`、`subagent_call/return`、`compaction_attempt/compaction` 等关系。普通请求没有这些 metadata 时仍可形成物理训练分支，但框架不会因此自动知道某次调用是不是被接受的摘要或某个子 agent。[语义边契约](https://github.com/PrimeIntellect-ai/verifiers/blob/27bbd216df0af719a43705866b2cf6139bcc95de/verifiers/v1/semantic.py#L63)。

`Trace.branches` 会把标为 `compaction_attempt` 的叶子设为不可训练，除非最终语义图中有 `compaction` 边说明 harness 实际从它继续。Prime 的转换再跳过不可训练 branch。因此“最新 Prime 对所有捕获动作一律不丢信号”也不成立；存在显式、语义驱动的排除规则。[接受条件](https://github.com/PrimeIntellect-ai/verifiers/blob/27bbd216df0af719a43705866b2cf6139bcc95de/verifiers/v1/trace.py#L492)。这是其具体选择，不是 RH2 已批准的规则。

另有 bundled chat program 的 `Compactor.compact()`：调用模型形成摘要，再把历史改成 system 加摘要 user 消息。这证明官方确实有非追加上下文的生产者；不能由此推断任意外部 CLI 都自动提供相同语义 metadata，或 RH2 只取消历史收缩拒绝就正确支持压缩。[上下文重建](https://github.com/PrimeIntellect-ai/verifiers/blob/27bbd216df0af719a43705866b2cf6139bcc95de/verifiers/v1/harnesses/utils/compaction.py#L219)。

**关键限制：有 Claude Code harness，不等于当前训练客户端原生接受 Claude Code。** 官方 `ClaudeCodeHarness.prepare_acp` 设置 `ANTHROPIC_BASE_URL`，当前默认 CLI pin 为 2.1.232；同版本 `TrainClient.get_response` 明确只允许 `ChatDialect`，对 Anthropic/Responses 抛 `NotImplementedError`，理由就是这些协议未验证能忠实通过 chat renderer。普通 eval relay 与训练客户端必须分别讨论。[Claude Code 入口](https://github.com/PrimeIntellect-ai/verifiers/blob/27bbd216df0af719a43705866b2cf6139bcc95de/verifiers/v1/harnesses/claude_code/harness.py#L69)、[训练协议拒绝条件](https://github.com/PrimeIntellect-ai/verifiers/blob/27bbd216df0af719a43705866b2cf6139bcc95de/verifiers/v1/clients/train.py#L337)。

## 4. verl：自管循环与外部框架接入分别成立

**源码实证：当前 `ToolAgentLoop` 已使用 Continuous Token。** `_handle_pending_state` 构造初始 token；生成调用使用累计 `prompt_ids`；返回的 `output.token_ids` 通过 `ct_merge_assistant_token` 加入运行上下文；工具消息通过 `ct_merge_context_msg` 进入下一次推理。原始动作的保留发生在**下一次推理之前**。[生成路径](https://github.com/verl-project/verl/blob/0d3f56a8980a55bfbbf1214ea54fa1b32ca1405c/verl/experimental/agent_loop/tool_agent_loop.py#L211)、[合并包装](https://github.com/verl-project/verl/blob/0d3f56a8980a55bfbbf1214ea54fa1b32ca1405c/verl/experimental/agent_loop/agent_loop.py#L359)。

`ContinuousTokenBuilder._assert_append_only` 明确拒绝消息缩短、既有消息前缀变化以及不允许的新增角色。`render_delta_token_id` 检查模板渲染的局部前缀是否成立，否则报错。它不是“收到任意重写就自动保留前段”的黑盒协议；工具循环自己持有 previous/updated messages，知道新增观察在哪。[追加约束与模板检查](https://github.com/verl-project/verl/blob/0d3f56a8980a55bfbbf1214ea54fa1b32ca1405c/verl/utils/tokenizer/continuous_token.py#L241)。

**追加也需要模型边界语义。** Qwen builder 在 `<|im_end|>` 后补换行；GLM builder 可移除旧末尾的 `<|observation|>`/`<|user|>`，`align_response_metadata` 同步裁旧 mask/logprob、给新插入或上下文 token 置 0。这种有限边界编辑不等于 RH2 整轮 REALIGN，但它也反证“只做 list 追加就能适配所有模型、所有输出 token 必有 loss”。[Qwen/GLM](https://github.com/verl-project/verl/blob/0d3f56a8980a55bfbbf1214ea54fa1b32ca1405c/verl/utils/tokenizer/continuous_token.py#L537)、[mask 对齐](https://github.com/verl-project/verl/blob/0d3f56a8980a55bfbbf1214ea54fa1b32ca1405c/verl/utils/tokenizer/continuous_token.py#L363)。

**外部框架已有窄例子，不能外推任意 harness。** 官方 `langgraph_agent.ChatModel._preprocess` 从最新 AIMessage 的 `response_metadata` 取累计原始 token，只编码之后的 tool/human；`_postprocess` 追加原始输出，再把状态交回消息 metadata。这是对外部 LangGraph 的定制桥，不要求改 trainer。但支持的 parser 仅为 `hermes/gpt-oss`，输出转换取最终一条 AIMessage 的累计记录；`ReactAgentLoop.run` 明写 multiple trajectories 尚待处理。[消息桥](https://github.com/verl-project/verl-recipe/blob/7f14b203934a981664b295696e930f9276825bf0/langgraph_agent/chat_model.py#L155)、[多轨迹边界](https://github.com/verl-project/verl-recipe/blob/7f14b203934a981664b295696e930f9276825bf0/langgraph_agent/react_agent_loop.py#L154)。

历史侧边栏提到的 `schemas.py.get_generation_prompt_ids(use_inference_chat_template=True)` 在当前文件中仍有完整重渲染分支；本轮未建立它在最新版中的生产调用路径，**不能用残留 helper 证明当前 ToolAgentLoop 实际会走它**。[辅助分支](https://github.com/verl-project/verl/blob/0d3f56a8980a55bfbbf1214ea54fa1b32ca1405c/verl/workers/rollout/schemas.py#L376)。本轮可确认的自管路径与 LangGraph 接入已经足以反对“verl 全部入口等价”这一概括。

## 5. GRPO 下，“mask 前轮无影响”为什么不成立

**源码实证：最终结果奖励会分配给可训练动作。** Prime `GRPOAlgorithm.score_group` 默认把 reward 减组均值，再由 `assign_advantages` 广播到每个可训练 sampled token。verl 的 outcome-GRPO 同样把组内标量扩到 `response_mask`。Prime 默认是否除标准差与 RH2 配方不同，不应顺手照搬；这里引用的是“动作 mask 决定哪些策略项存在”这一共同边界。[Prime GRPO](https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/algo/grpo.py#L25)、[广播](https://github.com/PrimeIntellect-ai/prime-rl/blob/04a61d3b75c3c99f263b2c133e822f998909adf7/src/prime_rl/orchestrator/algo/routing.py#L11)、[verl GRPO](https://github.com/verl-project/verl/blob/0d3f56a8980a55bfbbf1214ea54fa1b32ca1405c/verl/trainer/ppo/core_algos.py#L268)。

**推论：** 忽略 clipping/重要性权重细节，策略更新包含 `A_i × Σ_t m_it ∇log π(a_it | P_i, a_i,<t)`。假设 8 次执行中一次成功、七次失败，不除标准差时成功的优势为 0.875、失败为 −0.125；第一轮“选择正确文件/工具”的 token 本应与该最终结果相关联。把它们在所有 sample 中置 0，就移除了这些动作的直接策略梯度项；保留第二轮的相同优势不能恢复它们。

后轮仍能通过共享参数、上下文表征产生间接梯度，所以“前轮参数永远不受更新”也太强。正确结论是**原先动作选择对应的直接学习项缺失，目标与覆盖发生变化**。若组内奖励全相同，原本优势就可能为 0；这只说明特定组无信号，不能证明一般情况下丢前轮无影响。

**分段可以保持结果奖励语义，但不能把段当新的独立组成员。** 一次 rollout 的多个段应继承该 rollout 的最终 reward/advantage，保持原组比较关系；共享动作去重，并让 loss 分母继续按既定口径归一化。否则段数多的执行可能被重复计权。是否允许遗漏摘要、子 agent 或边界 token，仍是 owner 的训练覆盖决策。

## 6. 反证“只要 append token 就解决所有 harness 问题”

1. **追加改变的是实际状态。** 若旧路径 `P2` 不含 thinking，新路径保留它，第二轮会看到不同上下文，长度也变了。这是推理行为调整，训练和 eval 要使用同一规则；不能仅称训练文件压缩优化。
2. **事后替换不能补造采样条件。** 例如 `P1=[10], A1=[20,99], P2=[10,21,99,30], A2=[40,99]`。若训练装配把 `A1` 放回第二轮前缀，A2 的条件变成 `[10,20,99,30]`，但它的采样 logprob 来自 `[10,21,99,30]`。所有输出 ID 都原样保留，也不能证明条件分布相同。只有推理前就使用新的追加前缀，才没有这项事后错配。
3. **压缩、改写、分支需要边界识别。** 若只保存一个 `last_turn_ids`，多个并行请求及 subagent 不能当然共享同一条“最新”历史；若忽略合法的早期 user/tool 修改，又会让模型看到客户端未请求的上下文。现有会话/TurnRecord 是否够用，应由真实调用链决定，不能先引入新长期 owner。
4. **token 条件正确不等于 I18 已解决。** MoE 行为路由、权重版本、staleness、评分归因和组准入仍需各自证据；精确 token 不能推导这些事实。

对主审提供的 Polar `PrefixMergingBuilder` 条件判断，本轮阅读未找到反证：`_find_extendable_chain` 与 `_finalize_chain` 只比较旧 prompt；`_slice_interstitial` 按 EOT 跳过 canonical 旧 assistant，再接原始输出。因此上述数值例子确实能改变 A2 条件。此结论限于该 builder 和“P2 是真实采样输入”的前提，不推断它的生产发生率或整个框架的质量；对应固定来源与运行探针由主审记录。

## 7. 比新增长期状态机更小的选项

| 选项，均未获本轮批准 | 能解决什么 | 代价与不能省掉的验收 |
|---|---|---|
| 维持真实推理；每次调用保留完整 `P_i+A_i`；只合并精确前缀，否则留下另一段 | 不改变模型已见上下文，同时保住旧动作；可先依托已有 TurnRecord/分支表示 | 重复前缀增加训练 token/显存；核动作一次计权、组身份、版本/路由、分母。并非要求新图数据库。 |
| 上一项作为正确性基线，再只对普通线性交互追加原始历史 | 减少人为重分词漂移及重复训练前缀 | 新增的是下一次推理的上下文规则；需消息对应、模板边界、并发分支与 eval 一致性。仍保留精确分段 fallback。 |
| 暂不支持 subagent/compaction；在实际不支持边界明确停止 | 收窄黑盒支持面，使追加规则可验证 | 不能消除普通工具往返的 JSON/thinking 漂移；停止/丢弃会改变训练分布，不能作为 T2 私自加入。 |
| 接入完整语义图/长期会话恢复机制 | 支持更丰富的子 agent、摘要接受关系与恢复 | 只有目标能力明确需要才有理由；I01 本身尚不能证明必须新增这些机制。 |

需要 owner 先选的是“哪些实际采样动作必须有 loss、哪些上下文重写属于合法 harness 行为、首训是否允许哪些高级能力”，不是先选一个框架名。分段与追加可以先后实施，也可以仅保留分段；本报告不替 owner 选择。

## 8. 本轮一次验证与停止范围

固定源码的 AST 被抽取后在最小 CPU 数据夹具中执行；仅容器对象使用 stub，不替换所测分叉、去重或 mask 条件。验证成功退出：线性、旧 assistant 漂移、**初始 prompt 漂移**三组均保留全部 3 个 sampled token；真实路径分别保留，未事后改 A2 条件；Prime 共享节点两分支训练数为 `[3,1]`；verl 历史缩短与前缀变更均抛预期 ValueError。

GLM 边界夹具还确认：旧结束 token 被裁后，对应旧 mask/logprob 也被裁；新 context token 为 0。这只验证该边界记账，未做模型语义或 GPU 数值对拍。已下载的 37 份官方文件与固定 tree 的 Git blob SHA 全部相同；Prime pin 与独立 verifiers main 的上述三个文件相同。

本轮到此停止：未运行 GPU、Docker、外部模型 API、真实 Claude Code/ACP，也未验证这些上游方案接入 RH2 后的吞吐、发生率或完整能力兼容性。不能把源码支持或 CPU 夹具扩写成“官方已经替我们跑通首训”。
