# I01 补充讨论：miles TITO、真实成本与 thinking 保留策略

日期：2026-09-08。最新状态：**用户已确认首版采用 B，C 暂缓，不排专门 B/C 对比实验；实现与接入验证待办。** 见 [A 决策记录](../infra.md#6-用户决定)。下文保留此前的证据与建议，历史“未定/未批准”措辞不覆盖本次新决定。训练实现、配置与依赖尚未修改。

回应：[Claude 建议](../tmp/问题1claude_adv.md)。前序：[I01 总讨论](README.md)。本轮沿用主仓库 `ac0e2e64163fbe49411540e901df439aea16b6b0`、miles integration `98a0272e4158b2c20e3a34d210c79b50159af0f6`，没有升级 reference。

## 1. 修正我的遗漏，也收紧 Claude 的结论

**上一轮漏查 miles 自带的进程内 TITO tokenizer，是实质遗漏。** 当前已选集成基座里就有该组件；不需要为了使用它重开被否决的 session server 路线。在线追加的前置工作应据此重新估计，不能只拿 slime #2287 或外部框架说明可行性。

但这不等于 C 已经完成接入验证：

| Claude 的主张 | 本轮裁定 |
|---|---|
| 可直接复用 `Qwen3TITOTokenizer` 与 matcher，不用新服务 | 成立。还有已有 session/v2 的 prepare/commit 代码可参考；工具模块在当前 integration 中已经存在。 |
| C 是纯库函数、约 150–250 行 | tokenizer/matcher 可以进程内调用；完整 C 还需要请求身份、检查点提交与清理，以及下游消息树处理。行数只是估计，不是闭环证据。 |
| loose 能处理 run8 键顺序 | 能处理等价 JSON 对象表示。但 RH2 当前工具参数已经是 dict，单纯 dict 键序连 strict 也认为相等；关键收益是复用原 token，而非一定需要更宽的 matcher。 |
| B 的计算量约为 k+1 倍 | 只能作为特定假设下的粗略直觉，不能作一般成本公式。单条 run8 的真实表示量本轮已算出，见 §3。 |
| C 让一个任务始终只有一条 Sample | 普通连续段有希望合并；合法分支、历史改写和消息树分叉仍可能产生多行。只换 renderer 不保证这一点。 |
| 首次正式训练前必须完成 C，不能长期停在 B | 证据不足。是否值得由重复计算、实际瓶颈和上下文策略的效果决定。 |
| C 也给 I18 自然解决方案 | 按轮 token 记录有帮助；不会自动完成 MoE 路由的真实来源、切片和前缀重算核验。 |

推荐调整为：**B 是训练表示的参照和未匹配时的保留办法，C 是经过验证后减少漂移与重复计算的在线优化。二者可以组合。** 现在无需承诺长期使用 B，也不应先批准“忽略所有 thinking 回放变化”的宽合同。

## 2. “引擎 token 为准”应拆成两个决定

**训练事实层：** 对已经发生的每次调用，用引擎实际使用的输入和实际采样的输出、logprob 表达它。这是正确性要求。

**未来上下文层：** 下一次请求是否继续保留旧 thinking、是否接受 harness 的删减和改写、哪些消息变化仍算同一前缀。这是推理行为和实验配方。

例如：

```text
第一轮实际：P1 → A1（包含 thinking 与工具调用的完整原始输出）

路径一：第二轮按 harness/原模板得到较短 P2 → A2
        训练保留 [P1, A1] 和 [P2, A2]。

路径二：第二轮先构造 P1+A1+新观察 → A2_new
        训练使用这份实际输入与 A2_new。
```

两条路径都能正确训练。第二条保留更多历史，但不能由“训练必须忠实”推出它的任务表现一定更好。第一条在未来窗口里去掉 thinking，也不要求从过去那次调用的 loss 中删除 thinking。

反过来，若按第一条采样 A2，却在训练时才把旧 thinking 塞回其输入，仍会出现前序报告指出的条件错配。

因此更准确的候选合同是：**只在明确允许的历史等价关系与上下文政策内复用原始 token；真实改写则使用新的实际上下文，保留旧训练段。** 不把“引擎过去看过”解释成“以后必须永远看见”。

## 3. B 的成本：这次已有一条真实数值

主审用 run8 唯一留存样本的六轮原始 token，直接重放 vendor `_SampleBuilder`。五个边界中，只有 `t0→t1` 漂移，其余四个完全 CLEAN。

| 无截断、无 padding 的表示量 | 现状 1024 | B：阈值 0 |
|---|---:|---:|
| 训练行数 | 1 | 2 |
| 各行总长度 | 26,283 | 19,132＋26,283 |
| 总输入 token | 26,283 | 45,415 |
| 可训练动作 token | 2,148 | 2,772 |
| 最长单行 | 26,283 | 26,283 |

**B 的总输入 token 为现状的 1.728 倍，恢复了首轮 624 个动作 token。** 参照项本身欠覆盖，所以这不是等训练目标的性能对比，更不是 GPU 时间或峰值显存增加 72.8% 的证明。

证据：[运行脚本](run8_cost_probe.py)、[完整结果](run8_cost_result.json)、[原始 capture](../../s1/7a_artifacts/artifacts_run8/rollouts/4a25c5a4-f07f-422b-a6a4-/capture_records.json)。重放仅验证已知调用序列的 token builder；没有恢复完整 CC 请求体、执行消息树接入或测 C 的真实采样。

对于一条长度单调增长、没有截断的线性链，B 的 token 表示量是各次关闭训练行的长度之和。若一次漂移关闭长度为 L1 的旧行，末行长度 L2，总量就是 L1＋L2；相对末行是 `1+L1/L2`，不是固定翻倍。多次漂移同理。

这部分重复 token 通常仍需要训练端 forward；mask=0 不会自动免掉它们作为后续动作上下文的计算。但 packing、attention 计算、microbatch 调度和显存峰值不能由 token 总数直接换算。fully-async 下如果 rollout 仍是瓶颈，额外训练计算也未必同比降低端到端吞吐；需要测实际资源占用与等待。

原始 token 若完整保存，B 的表示可以离线重建。run8 就是这样的例子。因此“按现状采集后所有被删动作都不可恢复”过强；准确说法是：**只剩最终投影而未保存原始调用时，通常无法恢复。** 用 C 改变未来输入后的另一条随机行为轨迹，则确实不能靠旧输出恢复。

## 4. rollout 与 SGLang：不要混淆 CPU 渲染和 GPU prefill

B 只改训练轨迹组装，给定同一批请求，不改变送入 SGLang 的 prompt 或采样参数。它可能增加组装工作和后续训练负担，但不会直接改善 SGLang 的 token 前缀。长期作业的调度/权重发布节奏可受间接影响。

C 的“追加”指如何构造下一次输入，不等于改成只往引擎发送新 token；当前 wire 仍可发送完整 `input_ids`，由 SGLang 自己查找可复用的 KV。不要把进程内 TITO 与引擎上常驻的会话缓存混为一项能力。

C 的性能影响有四部分：

1. **CPU 与主机内存：** 只渲染新增消息有机会减少长历史 tokenize 时间；同时新增检查点查找、消息比较和 token 快照保存。上游树节点保存完整 token 快照，不能只按新增后缀估计整个接入的成本。应测净收益。
2. **prefill：** 更稳定的 token 前缀可提高 KV 复用；但现有全量重渲染，只要输出 token 相同，也能命中缓存，不是每次都重算整个 prompt。
3. **decode 与容量：** 长期保留 thinking 会增加实际上下文、KV 占用和后续 attention 成本，可能更早触发预算/压缩；缓存命中不会消除这部分历史对未来 attention 的成本。
4. **训练：** 连续段减少独立行与重复前缀；仍要看实际分叉频率、packing 和合格动作量。

run8 的首个边界尤其能说明两侧成本不同：旧 `P0+A0` 长 19,132，下一轮 prompt 长 19,169，两者共同前缀已经有 **19,064** 个 token。分歧只影响旧尾部 68 个 token，新 prompt 在分歧后有 105 个 token。若旧 KV 仍在同一引擎且可复用，SGLang 并非因此失去前面约 19k 的缓存；训练端却要额外保存完整 19,132-token 行以训练旧动作。

这只是相邻调用的 token 复用机会，不是实际 cache-hit 计数。当前多引擎路由不保证同一 sid 落同一 engine；选定的 retract 权重发布路径也会清缓存，容量淘汰还会进一步影响收益。[本地路由说明](../../../../../rh2/src/repoharness2/adapters/slime/engine_router_client.py#L1)、[权重更新清缓存](../../../../../reference/miles-rh2-integration/miles/backends/megatron_utils/update_weight/update_weight_from_distributed/mixin.py#L310)

本轮核到项目钉死的 SGLang `4e230c3d85cefdab5b65eeb6f6f87793a707a6fb`：`init_next_round_input` 以 token key 调用 `match_prefix`；`_compute_max_prefix_len` 至少留末 token，指定 prompt logprob 范围还会限制复用。RH2 发完整 `input_ids`，本身不等于缓存失效。[固定 SGLang 源码](https://github.com/sgl-project/sglang/blob/4e230c3d85cefdab5b65eeb6f6f87793a707a6fb/python/sglang/srt/managers/schedule_batch.py#L1327)、[官方缓存原理](https://www.lmsys.org/blog/2024-01-17-sglang/)

所以不能预先说 C 对 SGLang 一定只是小影响，也不能承诺大幅加速。靠后的 JSON 漂移与很早开始删除历史 thinking，影响可能完全不同。

## 5. Qwen3TITOTokenizer 和 matcher 到底可靠到哪一步

本轮用缓存的真实 `Qwen/Qwen3-30B-A3B@ad44e777bcd18fa416d9da3bd8f70d33ebb85d39` tokenizer，执行原始 miles 匹配模块和抽取的 Qwen TITO 路径。为绕开未安装的 SGLang，只隔离无关模型分支与 `tools=None` 下未执行的 schema 入口；没有模拟 tokenizer，也没有做 CLI 或 GPU 复现。

| 合成消息变化 | strict | loose_tool_call |
|---|---|---|
| dict 工具参数只改键顺序 | 接受 | 接受 |
| JSON 字符串工具参数只改键顺序 | 拒绝 | 接受 |
| 原本非空的 reasoning_content 消失 | 拒绝 | 拒绝 |
| 工具名或普通实参实际改变 | 拒绝 | 拒绝 |

`role_content_only` 甚至会接受工具名/实参变化，因此不适合用它来实现“只容忍 thinking 缺失”。不能把“宽松”当成一个不影响行为的默认优化。

“最长匹配检查点”也不是找一段最相似的文字。上游查的是满足所选消息等价关系的完整节点路径；同深度多命中时按较新的节点选择。这是一种定位规则，不能单独证明两个内容相同的采样事件属于同一分支。接入 RH2 时仍需保存本次请求选中的父检查点，不能在并发请求返回后再拿 sid 的“最新节点”当父节点。[检查点树](../../../../../reference/miles-rh2-integration/miles/rollout/session/v2/tree_trajectory.py#L14)

还有一个条件风险：strict 的 Python dict 相等会把布尔 true 与整数 1 视为相等，loose 的 strict 早返回也接受这组对象；JSON 字符串版本则能区别。探针证明这个实现边界，**未证明 CC 实际改过参数类型**，也不据此否决整个组件。若采用 matcher，应明确定义所需等价关系，并复用其已有检查而非笼统宣称完全可靠。

另有两处接入细节：

- `merge_tokens` 内部仍调用 strict append 检查。上游先按 loose 匹配，再传入 `stored_prefix + request_tail`；直接把“loose 已接受的原始回放”交给 merge，仍可能报错。
- 构造 `Qwen3TITOTokenizer` 只注入 `clear_thinking=False`，**不自动替换 tokenizer 的 chat template**。HF 原生模板不读取这个参数，完整渲染仍可删历史 thinking；fixed 模板与原生模板是两个实际选择。

不过，不应反向夸大成“原生模板就无法增量追加”。真实 tokenizer 探针中，**原生和 fixed 的 reminder 追加都保留了完整旧 token 前缀**，并补 `<|im_end|>` 后的换行。原生模板的 dummy 前缀从一开始就没渲染 dummy thinking，故后缀差分仍成立。这个局部结果不证明所有角色组合/模板配置都成立，但已说明无需凭猜测强制更换 fixed 模板。

脚本与结果：[miles_c_probe.py](miles_c_probe.py)、[详细结果](miles_c_probe_result.json)、[主审复跑](miles_c_probe_root.json)。实现依据：[TITO](../../../../../reference/miles-rh2-integration/miles/utils/chat_template_utils/tito_tokenizer.py#L186)、[matcher](../../../../../reference/miles-rh2-integration/miles/utils/chat_template_utils/message_matcher_hub/funcs.py#L79)、[上游 effective_messages](../../../../../reference/miles-rh2-integration/miles/rollout/session/v2/session_state.py#L88)。

## 6. thinking 是否丢掉，不能归结为“Claude 是黑盒”

必须分别观察：

1. **CLI 回放：** 新 Anthropic 请求体是否仍含旧 `thinking` block。
2. **adapter 翻译：** block 是否被转换为 `reasoning_content`，工具结果和 reminder 被转换成什么 role。
3. **模板/续接：** 模型真正收到的 prompt 是否保留该内容。

已查到当前翻译器会保留收到的 thinking block；没有收到则不会凭空恢复。reminder 文本则可能被翻成独立 user。run8 已证工具参数 token 漂移，但仅凭 token 差异不能唯一定位是 CLI、翻译还是序列化环节改变了表示。[实际翻译器](../../../../../rh2/src/slime/agent/adapters/anthropic.py#L88)

**Qwen3 官方 Best Practices 明确建议多轮历史保留最终输出而不必包含旧 thinking，由模板实现。** 这不证明在我们的 SWE RL 配方里删 thinking 最优，却足以反对“旧 thinking 以后必须一直保留，才算 RL 正确”的判断。[固定版本模型说明](https://huggingface.co/Qwen/Qwen3-30B-A3B/blob/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39/README.md#best-practices)

保留 thinking 可能减少重复推理、保持计划连续性；也可能占用窗口、保留错误计划、增加 decode 成本。这里是待验证的行为取舍，不能只看 token 捕获是否完整。

还要避免套用错误的外部默认：Anthropic 文档中的 thinking 清理有服务端行为，而我们使用自己的 adapter＋Qwen/SGLang，不会自动执行 Anthropic 服务端相同逻辑。官方 Claude Code 文档也明确说明 compaction 会替换历史、一些工具配置变化会改变前缀；这些是合理上下文变化，不能统统当作回放噪声忽略。[API 清理层](https://platform.claude.com/docs/en/build-with-claude/context-editing)、[CLI 上下文变化](https://code.claude.com/docs/en/prompt-caching)

因此，现阶段不建议把“省略 thinking 一律容忍”写成默认规则。先在三层记录上查清真实发生了什么；若要恢复省略的 thinking，应作为显式候选上下文策略，与训练和 eval 一起验证。

## 7. C 还要越过一个真实的下游接缝

一个窄反例已运行：假设 TITO 已经保证 `P2=P1+A1+观察`，但 CLI 回放只省略 A1 的 thinking，原始 translated 消息仍原样交给 vendor manager。

| manager 阈值 | token 前缀 | 旧生成记录 | 实际可训练动作 token |
|---|---|---|---:|
| 1024 | 完全 CLEAN | 消息 rewrite merge 仍清掉旧 TurnRecord | 仅新 20 |
| 0 | 完全 CLEAN | 旧记录保留 | 旧 4＋新 20 |

这证明**token 连续与消息树动作保留是两个接缝**。现有 loose 本来不容忍 thinking 缺失；此例针对 Claude 所提“未来放宽该匹配”的条件，而不是当前 C 已上线发生的故障。[原探针](tito_clean_rewrite_probe.py)、[主审复跑结果](tito_clean_rewrite_probe_root.json)

所以，只替换 `_render_token_ids` 不足以声称“C 已经杜绝动作丢失”。该函数也没有 sid/请求提交/清理参数。最小接入仍须把以下几点串起来，但不需要新建服务或复杂恢复平台：

- 请求开始时，拿到正确的已提交检查点；并行请求不会互相使用对方尚未完成的输出。
- 响应成功交付并进入现有记录边界后才提交检查点；失败/取消/内部重生成不会提前污染可见历史。
- 复用时确认实际模型、模板配置、工具定义与历史关系适用，避免只匹配 messages 却忽略工具表变化。
- 生成记录与下游消息树使用一致的关系，未匹配时真正保留旧段，不落回 REALIGN/rewrite 删除。

这使 C＋B 式保留成为自然组合：C 减少可避免的漂移；真正改写或尚未支持的续接保留为多行。并非要求把所有不支持的上下文都变成丢组或 fatal。

## 8. 现在怎样推进，才不需要凭猜测选 B/C

下一步建议先做**比较与接入验证**，补足决定所需的证据；永久上下文政策可以后定。本轮没有替用户批准这些实现。

**同日续问澄清：下列路径是评估 C 时的验证菜单，不是直接选择 B 的前置条件。** 可以依据已有源码与 CPU 证据先选 B，暂缓 C；无需先实现 C、收集一批新 rollout 或做 B/C GPU 对比。具体建议见 §10。

1. **已有成果可直接复用：** B 的离线参照、真实 tokenizer 的 TITO 小例子、消息树反例已经完成。没有必要为证明库可调用先跑长训练，也不需要先把 B 改成正式默认。
2. **拿一小批真实 CC 请求补齐三层信息。** 初始可取约 8–16 个开发执行，覆盖普通 Edit/Read、reminder、长输出与目标支持面；用于诊断，不作为漂移率的精确统计。首要回答 CLI 是否真省略 thinking、工具表是否变化、C 能匹配哪些边界。
3. **先验证不涉及 thinking 政策争议的普通工具续接。** 确认原始 token 可保留、真实观察后缀正确、消息树没有独立删动作；其余合法变化保留分段。不要为了提高命中率先扩大 matcher。
4. **再做窄 GPU 比较。** 对原生上下文＋B，以及候选 TITO 上下文，测 renderer 时间、实际 prompt 长度、cache/TTFT、decode、训练行/packing/显存、有效动作量和任务结果。保留 thinking 的效果必须用新上下文下的新采样来测，不能沿用旧输出的 logprob 宣称等价。

Claude 的“run8 第一边界改 CLEAN、其余逐位不变”需要明确对象：新观察后缀可对照；修正首轮历史会传播到后续 prompt，不应要求后续完整 prompt 与旧记录逐位相同。旧记录可做构造/形状探针，不能恢复 C 下本来会生成的响应和最终奖励。

届时的选择依据很直接：

- B 的额外训练负担可接受、C 的上下文收益仍不明：B 可以继续作为基线，没有“必须尽快换掉”的时间表。
- 漂移普遍、训练端明显受限，C 的匹配与任务行为稳定：让 C 成为常见路径，保留 B 式分段。
- thinking 保留显著改变成本或表现：单独选定它，不把其效果混进“JSON 漂移修复”的收益。

指标应看每单位时间/成本产出的合格训练动作和任务结果，不单追求 Sample 数最少。也无需为了此问题先引入新的拒绝规则、长期账本或训练前缀树内核。

## 9. 验证状态

本轮主审运行 run8 真实 token 成本重放，独立复跑 miles matcher/TITO 探针与真实消息树反例，均正常退出；没有 GPU/Docker、真实 CLI 模型调用或标准测试套件扩充。TITO 探针不覆盖 tools schema 的真实 SGLang 导入路径，不能当成 C 的端到端验收。

独立切片：[Production Tracer](miles_c_production_tracer.md)、[Falsifier](miles_c_falsifier.md)。本轮只有文档和窄证据脚本，没有训练源码/配置/依赖修改，没有提交或推送。

两位独立角色另完成本稿的窄收口复核；已修正示意中的 A1 定义，使其始终表示完整原始输出，没有据此扩大验证范围。

## 10. 续问：能否直接选 B，省去比较实验

**可以，且当前更建议这样收敛：B 作为 I01 的首版处理路线，C 暂缓；不以 B/C 对比或长期学习消融作为选 B 的前提。** 用户本次仍是询问方案，没有据此修改源码或记录为批准。

选择 B 有独立的工程理由：保留实际采样条件与动作；保持现有 harness/模板的推理行为；复用已有阈值和分段表示；避免在 I01 中同时引入新的上下文策略与检查点生命周期。代价是重复前缀计算，已明确但尚未测出总体成本。无需先证明 B 全面优于 C，才能把它用作当前基线。

本机能完成真实 tokenizer、已有 capture 重放、动作覆盖、身份、组/member 和分母归约等验证，其中 manager＋identity＋backfill 八案及 run8 重放已完成。选 B 后只补实际 bringup 传参和训练消费的必要接入验证，不重复建立一套 C 探针。真实目标模型下的新 Claude Code 行为仍需该模型服务；用固定响应或其他模型代替，不能说明目标模型的真实漂移分布。

GPU 的必要性取决于要回答的问题。目标模型能否实际完成 forward/backward、packing 后是否 OOM、真实计算耗时，需目标后端 GPU；不要求数学上必须八卡，但要满足模型、长度与并行配置。整体吞吐、权重发布和多 engine 缓存行为，则需代表性的完整拓扑。当前八卡是目标机器规格，具体 train/rollout 拓扑仍未定；最省工作的做法是并入原定 GPU spike，验证 B 的真实消费和资源成本，不为 I01 单独搭小模型拓扑或安排 C 对照。

外部依据应收紧：Agent Lightning 的已核 adapter 明确比较完整 `prompt+response` 前缀，失败就结束旧行；verifiers/Prime RL 也有精确 token 前缀分支保留。Polar 已核 builder 有自己的重建方式与条件前缀边界，不能笼统说三者就是同一算法。采用的是经本地核对的原则，不是照搬框架标签。

不能省掉的接入验证很窄：阈值确实作用于两个销毁点；旧动作在训练行并集中按实际采样身份只计一次；新增行仍属原 member，优势和分母继续按现有口径；新增行没有被后续长度/准入处理意外丢掉。I18 路由和 I19 压缩仍独立处理。GPU spike 中顺手记录每 execution 行数、重复 token、step 耗时和显存，若重复前缀成为显著瓶颈，再提高 C 的优先级；没有必要为此新增固定阈值或训练闸门。
