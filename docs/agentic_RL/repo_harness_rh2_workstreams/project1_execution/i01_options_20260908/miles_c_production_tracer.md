# I01：miles TITO 进程内方案 C 生产接缝核查

日期：2026-09-08。角色：Production Tracer；只核 [Claude 候选稿](../tmp/问题1claude_adv.md) 的 C 接缝及与 B 的相关边界，未实现 adapter。
本地 RH2 基线 `ac0e2e64163fbe49411540e901df439aea16b6b0`；miles integration 基线 `98a0272e4158b2c20e3a34d210c79b50159af0f6`，分支 `rh2-integration-v3`。
以下 miles 结论针对已集成源码，不把它称为当前 upstream main；无需通过网络推断本地实现。只运行文末两案 CPU 探针。

## 1. 结论

**C 的进程内库路线可行性有源码依据；完整 RH2 接入尚未实现或验证。** miles 提供增量 tokenizer、消息 matcher、树形检查点及 prepare/commit helper，它们不要求启动 session HTTP server。可是 `_render_token_ids` 只是同步渲染函数，没有 sid、请求归属、已交付输出或清理入口。“替换这一函数约 150–250 行”没有闭环证据；不能从 tokenizer 的短调用推算完整变更范围。[渲染入口](../../../../../rh2/src/slime/agent/adapters/common.py#L58)、[v2 状态实现](../../../../../reference/miles-rh2-integration/miles/rollout/session/v2/session_state.py#L30)

**“C 顺便解决 I18”不成立。** C 可以提供连续 token 前缀；I18 还涉及路由行来自哪次 forward，以及请求内部 retract。当前 RH2 的路由选择不会因为替换渲染函数而改变。详见 §6。

## 2. 已有组件具体提供了什么

| 组件 | 已证行为与限制 |
|---|---|
| `Qwen3TITOTokenizer.merge_tokens` | 保留传入的真实旧 token，仅渲染新增消息的后缀；旧末 token 为 `<\|im_end\|>` 时补一个换行。它不管理会话、捕获身份、logprob 或路由。[实现](../../../../../reference/miles-rh2-integration/miles/utils/chat_template_utils/tito_tokenizer.py#L240) |
| 增量渲染 | 用 dummy system/assistant 构造边界，分别渲染基底与追加内容后取字符串后缀；并非重新渲染全部历史。其内部 append 校验仍默认 **strict**。[后缀构造](../../../../../reference/miles-rh2-integration/miles/utils/chat_template_utils/tito_tokenizer.py#L160)、[严格校验](../../../../../reference/miles-rh2-integration/miles/utils/chat_template_utils/tito_tokenizer.py#L185) |
| v2 `prepare_pretokenized` | 找到检查点后，先组成 `stored_messages + request_suffix`，再传入增量 tokenizer。因此外层 loose 匹配与内层 strict 可以配合；不能直接把变形的整份历史传给 `merge_tokens`。[实现](../../../../../reference/miles-rh2-integration/miles/rollout/session/v2/session_state.py#L87) |
| v2 `find_attach_point` | 搜索完整节点路径的最深匹配前缀；不匹配则新 root；同深度多命中选最新 `seq`。这是确定性选择规则，不能证明两个同文采样事件的身份相同。节点保存整段 token 快照，树有 1024 节点上限；与 slime 的 token 阈值不是一回事。[树结构与搜索](../../../../../reference/miles-rh2-integration/miles/rollout/session/v2/tree_trajectory.py#L14) |

**键序与 thinking 必须分开说。** RH2 Anthropic 翻译后 `tool_calls[].function.arguments` 已是 dict；仅 dict 插入顺序变化，miles strict 的字典比较就能通过。loose 主要新增 JSON 对象字符串/对象表示等价，仍比较 `reasoning_content`、工具名、调用顺序等；它**不接受非空 thinking 被省略**。`role_content_only` 虽会接受，却也忽略整份 tool_calls，不能称为只放宽 thinking。[RH2 翻译](../../../../../rh2/src/slime/agent/adapters/anthropic.py#L99)、[三个 matcher](../../../../../reference/miles-rh2-integration/miles/utils/chat_template_utils/message_matcher_hub/funcs.py#L21)

**固定模板不是 factory 自动安装的。** Qwen3 TITO 声明 `qwen3_fixed.jinja` 与 `clear_thinking=False`；factory 只实例化类，使用的仍是传入 tokenizer 的模板。miles CLI 另做模板/kwargs 解析，而且非默认 `--tito-model` 当前要求 `--use-session-server`；不能靠给现有 RH2 启动命令加一个参数获得进程内 C。RH2 自己 `load_tokenizer(hf_checkpoint)` 后构造 AnthropicAdapter，尚未接这套模板配置。[类与 factory](../../../../../reference/miles-rh2-integration/miles/utils/chat_template_utils/tito_tokenizer.py#L252)、[factory](../../../../../reference/miles-rh2-integration/miles/utils/chat_template_utils/tito_tokenizer.py#L814)、[CLI 约束](../../../../../reference/miles-rh2-integration/miles/utils/arguments.py#L2962)、[RH2 初始化](../../../../../rh2/src/repoharness2/adapters/slime/bringup.py#L861)

## 3. 当前 RH2 请求链：渲染函数之外的必要接缝

| 边界 | 当前可达路径与 C 尚缺的证明 |
|---|---|
| sid 与请求身份 | HTTP guard 把 capability 映射为内部 sid，并设置每请求独立 `_capture_request_key`；`_run_turn` 又取得 sid。渲染函数没收到这些字段。检查点必须属于正确会话，选中的父节点还须属于当前请求，不能用全局“最新请求”。[guard](../../../../../rh2/src/repoharness2/adapters/slime/capture_wire.py#L885)、[调用链](../../../../../rh2/src/slime/agent/adapters/common.py#L325) |
| 同 sid 并发与分支 | `_run_turn` 跟踪多个 task，并未整轮串行化。miles v2 在锁内 position/prepare，**await backend 前保存 attach_parent**，结束后在锁内向这个父节点提交。单个可变 `active_leaf` 不足以跨 await 保证归属；借用 helper 不能省略这个协议。[RH2](../../../../../rh2/src/slime/agent/adapters/common.py#L335)、[v2 两阶段调用](../../../../../reference/miles-rh2-integration/miles/rollout/session/v2/core.py#L149) |
| abort 与交付提交 | RH2 先获得代理最终结果、stage 实际 prompt/response，再 flush 客户端响应；flush 失败/取消不调用 record。之后 `record_turn → registry.commit → capture_id/turn_index` 绑定。仅“渲染完成”或“引擎返回”都不是已有交付门；代理 abort/重生成的未交付中间结果不能成为已提交检查点。[stage](../../../../../rh2/src/repoharness2/adapters/slime/capture_wire.py#L1220)、[flush](../../../../../rh2/src/slime/agent/adapters/common.py#L359)、[commit](../../../../../rh2/src/repoharness2/adapters/slime/capture_wire.py#L1284) |
| 借用 v2 commit 的区别 | v2 server 在返回客户端 response 前提交树节点，和 RH2 的 flush 后提交顺序不同。可复用数据操作，不代表可以照搬 server 的提交时点；新检查点与现有 capture/manager 失败路径如何一致，候选稿未证明。[v2 commit](../../../../../reference/miles-rh2-integration/miles/rollout/session/v2/core.py#L188) |
| cleanup 与线程 | RH2 finish/drop 先关闭 sid 并 drain/cancel 在飞任务，再导出或删除 manager 状态；RH2 drop 最终 unregister capture。新检查点状态未被现有清理覆盖；其生命周期还须遵守 adapter loop 与 owner loop 分离。debug callback 会吞异常，不能凭它证明状态提交失败必然可见。[drain/drop](../../../../../rh2/src/slime/agent/adapters/common.py#L225)、[RH2 finish/drop](../../../../../rh2/src/repoharness2/adapters/slime/bringup.py#L688)、[callback](../../../../../rh2/src/slime/agent/adapters/common.py#L310) |

这些是替换渲染后的既有生产边界，不是要求引入 session server 或另一套 Sample 管道。现有 `attach_turn_identity_spans` 仍从 vendor 消息树和 capture 绑定导出身份；借用 miles v2 检查点不会自动替代它。[身份导出](../../../../../rh2/src/repoharness2/adapters/slime/bringup.py#L696)

## 4. token CLEAN 与消息树一致是两项条件

vendor `record_turn` 接收的是原始 `translated`，不是 TITO 恢复后的 stored 前缀，也不读取 miles matcher。消息树按 dict 相等匹配；短 assistant rewrite 会清除旧 `turn`/`turn_index`。因此若未来 matcher 被放宽以接受 thinking 省略，**即使生成 prompt 保留真实旧 token，旧动作仍可能在消息树阶段消失**。现有 loose 本身不接受省略 thinking，本反例不是声称默认 loose 已触发这个场景。[原消息记录](../../../../../rh2/src/slime/agent/adapters/common.py#L384)、[树匹配与销毁](../../../../../rh2/src/slime/agent/trajectory.py#L352)

真实 manager 两轮窄探针：首轮输出 4 token，第二轮 prompt 严格为 `P1 + A1 + observation`，新输出 20 token；回放仅省略 thinking。真实 `_SampleBuilder` 均判 CLEAN，结果如下：

| threshold | 消息树叶 | Sample | 保留 turn | 旧动作 mask=1 | 全部 mask=1 |
|---:|---:|---:|---|---:|---:|
| 1024 | 1 | 1 | 2 | 0 | 20 |
| 0 | 2 | 2 | 1、2 | 4 | 24 |

它证明 token 层成功不足以推出“一个轨迹一个 Sample”或“生成动作全保留”。另一个限制是：候选稿的“匹配失败，原生渲染并 FORK”不是当前默认行为保证；原生渲染后若满足 REALIGN 条件，1024 仍会 REALIGN，消息 rewrite 也仍可能合并。[token 分流](../../../../../rh2/src/slime/agent/trajectory.py#L169)

## 5. tools、模板参数及 B/C 成本语义

matcher 与树定位只比较 messages；tools schema 和 `chat_template_kwargs` 不在检查点匹配依据中。v2 prepare 使用当前 tools，已有前缀却是旧 token；工具定义若写在模板前部，schema 变化不会自动重写旧前缀。miles 会按请求克隆模板 kwargs，但同样未在树定位时核对旧 kwargs。RH2 当前渲染函数连 kwargs 参数都没有。候选稿尚未规定这些变化何时仍允许复用。[prepare](../../../../../reference/miles-rh2-integration/miles/rollout/session/v2/session_state.py#L87)、[请求 kwargs](../../../../../reference/miles-rh2-integration/miles/rollout/session/core.py#L220)

| 比较项 | B：threshold=0 | C：复用真实 token 前缀 |
|---|---|---|
| 上下文语义 | 保留当前全历史重渲染得到的模型输入；关闭两个阈值销毁点。 | 模型继续看到已保存的真实历史 token；包括原生模板可能清掉的 thinking，可能改变下一轮采样分布。 |
| 训练成本 | 漂移可增加 Sample，重复前缀参与训练 forward；“k+1”是特定链的段数估算，不是普遍 GPU 时间倍数。 | 对匹配成功且消息树也一致的链，可减少这种拆段；新增历史检查点复制/驻留和更长 prompt 也有成本，未实测净收益。 |
| 覆盖保证 | 只关闭这两个销毁点，不能覆盖长度截断、capture/资格拒绝等其它路径；也不保证所有分支等价。 | 只保证增量构造所复用的 token 前缀；消息树、分支身份、合法压缩及资格语义仍需独立成立。 |

上述 B 行为已由 [原八案探针](threshold_probe.py) 证明；RH2 当前构造器仍未显式传 0。C 的树 helper 保存每个节点完整 token 快照，内存按各检查点长度之和增长；不能只比较“新增后缀 tokenize”与“全历史 tokenize”来宣布总成本更低。[快照字段](../../../../../reference/miles-rh2-integration/miles/rollout/session/v2/tree_trajectory.py#L17)

## 6. I18 与验收证据的限制

当前 `backfill_leaf_sample` 仍取 `turns[-1].routed_experts_flat` 并按最终 Sample 长度裁剪；即使 token 前缀完全一致，后续 prefill/retract 的路由也未必来自早轮原始采样 forward。[RH2 路由选择](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L1427)、[I18 已有边界](../issue_inventory_20260908/README.md#i18r3-路由形状对齐不等于仍来自原始采样-forward)

miles 的确另有 optional addition R3：请求传 `routed_experts_start_len`，逐段保存并检查行区间连续，再沿叶路径拼接。**这是一条独立 wire + sample merge 能力，不在 Qwen3 TITO tokenizer 内**；RH2 `capture_wire` 当前只请求 `return_routed_experts`，没有接该增量参数/拼接函数。该机制存在也不能单凭静态源码证明请求内部 retract 后整条行为路由因果路径保真。[请求参数](../../../../../reference/miles-rh2-integration/miles/rollout/session/core.py#L289)、[拼接校验](../../../../../reference/miles-rh2-integration/miles/rollout/session/samples/merge.py#L151)、[RH2 wire](../../../../../rh2/src/repoharness2/adapters/slime/capture_wire.py#L1060)

候选稿“t0 边界变 CLEAN，其余逐位不变”若指后续完整 prompt，不能作为正确验收条件：修复 A0 的旧前缀会传播到 P2、P3 等。旧 run 的后续输出、logprob 是在旧 prompt 下采样的；离线回放能验证匹配、构造、token 数与分段成本，不能把旧采样当成新 C 上下文下有效的行为轨迹。真实 C 下的采样与训练影响仍未验证。

## 7. 可复现证据

脚本：[tito_clean_rewrite_probe.py](tito_clean_rewrite_probe.py)；结果：[tito_clean_rewrite_probe.json](tito_clean_rewrite_probe.json)。在仓库根目录运行：

```bash
PYTHONDONTWRITEBYTECODE=1 rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/i01_options_20260908/tito_clean_rewrite_probe.py
```

最终运行 exit 0，两案断言通过。真实调用 Anthropic 翻译器和 vendor manager；token/logprob 为合成输入，未构造 C adapter、未调用模型、未运行 GPU/Docker/全套测试。输出绑定 vendor `trajectory.py` SHA256 `6dbb7bec446d81fa0542a4c954d458b4a11edab6776b45a63bc33bca08dd0469`。
