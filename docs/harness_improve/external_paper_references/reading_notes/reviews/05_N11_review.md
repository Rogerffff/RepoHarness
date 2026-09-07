# N11 独立正确性与覆盖审查

审查日期：2026-09-07。对象：[N11 初稿](../N11_miles_agentic_rollout.md)，包括审查期间作者补入的 §5.1 reward normalization、两类 IS ratio、默认共享分母，以及 §6.3 R3 warning。只写本审查文件，未修改作者笔记、源码或运行配置；未另派审查者。

当前结论（主线程按下方 §7 的最终复核更新）：两份官方正文的后训练章节覆盖完整，主要机制解释可靠；**R1–R5 均已按证据修订并独立复读确认**。下方保留首次审查时 R4 待修的历史记录，其最终处置见 §7。不能把本记录当成端到端运行验证或无条件“通过”。未发现把示例配置冒充受控能力增益或总成本的数字错误。

## 1. 独立来源与目录清单

先读模板和两份官方正文快照，列出以下目录及必须覆盖的事实，再打开初稿比对。两份资料都是工程文档，没有独立附录、实验附录或论文页码；也没有可供补读的 SFT/DPO/安全偏好/数学 RL 实验章节。OPD 属沿代码扩展的相关训练能力，不能倒写成两份网页的实验结论。

证据简称：**U**=`reference/miles`，commit `f2b7c79298a53c53861514d099f7def73bd29f4a`；**I**=`reference/miles-rh2-integration`，commit `98a0272e4158b2c20e3a34d210c79b50159af0f6`。审查实际核过两者 HEAD 与干净状态。下面代码路径相对各自仓库根；快照路径相对 reading_notes。**W** 为 `sources/N11/*online-20260907.md`。远端固定 `d2fc97ce581577e255e494801d7568747d5a10d7` 只核本题涉及的 Agentic 文档及参数约束，不代表审完最新整树。

官方来源：[Agentic Rollout](https://miles.radixark.com/docs/user-guide/agentic-rollout)、[Fully Async RL](https://miles.radixark.com/docs/user-guide/fully-async)。本审查的网页工具成功打开后者，前者返回 safe-open 错误；Agentic 正文核查依赖已存官方 `.md` 快照和固定 U 文件，没有用工具失败填出不存在的原文事实。

| 原文目录（独立列出） | 从原文建立的必查事实 | 初稿覆盖 |
| --- | --- | --- |
| Agentic 导言及 VLM Warning | exact token/logprob/routed experts；session 无 image/video，另走 `/generate` | §2、§3、§9，完整 |
| Configure the wrapper | 两个函数入口、session flag、checkpoint/tito-model；messages 不预套模板 | §3.1，完整 |
| Write the agent loop | async 合同；URL 已含 session；sampling 映射；metadata 和 dict/None 返回 | §3.1、§4，完整 |
| Optional teardown hook | oversampling 先停止在飞推理，再清理外部环境；hook 可选 | §4.2、§6.3，完整 |
| TITO / Leave token ownership to Miles | 全消息重放；首轮模板；复用实际 token checkpoint；只分词新 suffix；控制字段和 prefix cache | §3.2，完整 |
| Choose the session behavior | v1 尾扩展和单 checkpoint 回滚；v2 最深前缀树、不删分支、length 不续；Sample/list；partial/pause/R3；总上下文上限 | §3.3、§6.3，覆盖且区分版本冲突 |
| Pick your `--tito-model` | 无自动识别；固定模板及 parser；自定义 default；模型族注册表 | §3.4，完整且没有把 W 新族套给 U |
| Verify a new model TITO | 注册 tokenizer/FIXED_TEMPLATE；CPU append-only 和 GPU 实际推理两项均须通过 | §3.4、§8，完整，明确未运行 |
| Choose replay matching | strict、loose_tool_call、role_content_only、自定义；匹配失败回滚/分支；存储 token 权威；不协调跨边界 call ID | §3.4，完整 |
| Example | Harbor/SWE launcher、reward、length 和清理接线 | §4、§7.3，补读范围明确 |
| Fully Async 导言 / When to use it | rollout 长尾、两循环、off-policy 代价；调试 loss/reward 时建议同步 | §2、§6，完整 |
| Usage & Examples / Basic usage | train_async + fully-async + class API | §6.1，完整 |
| Examples / Customizations | 三个可见 launcher 的规模与 eval 入口；调度、buffer、eval、metrics 四类自定义入口 | §6–§7，完整；原文“四个”与三行冲突已登记 |
| The fully async schedule / How generation is scheduled | 常驻 worker；整组提交，按 sample 释放额度；trainer 等完整组；定期暂停发布；跨版本 | §6.1–§6.3，见修订 R3 的 group_rm 限定 |
| Arguments: Scheduling options | B 为组，C 为 trajectory，G 为每 prompt 采样数；sample/group 释放方式 | §6.1，完整；代码 `max(1,C//G)` 比网页 floor 更精确 |
| Data path / The data buffer | put/get/get_metrics；aborted/dynamic 在 put，stale 在 get；排序及批级 filter | §6.2，完整 |
| Arguments: Buffer options | factor×B 容量、满时背压；默认 staleness 关闭；drop/retry；dynamic reject 不 retry；custom buffer 接管 | §6.2，完整；版本缺失需按 R1 收紧 |
| Evaluation / Mode 1: Shared engines | 暂停新提交，在飞继续完成；共用上次广播权重 | §7.1–§7.2，完整 |
| Mode 2: Dedicated fleet | 独立 GPU/router/HF snapshot；继承与覆盖 SGLang；不同 TP 重置相关并行量；异步点和 lag | §7.1–§7.2，完整 |
| Mode 3: External backend | CheckpointEvalFn；EvalSkip；调度/日志/回收；外部 API 或服务资源 | §7.1，完整 |
| The weight snapshot pipeline | export/periodic HF 两来源；interval 关系；collective 等待；backpressure/skip；retired+in-flight 存储；串行 eval | §7.1，完整且限定“training never pauses” |
| Metrics / Async rollout metrics | queue/filter/staleness 分母；空/满/过期；30s starvation warning | §7.2，完整；代码与文档分母冲突核验成立 |
| Async eval metrics | skip 各 reason；lag；目标权重与 mixed-version 检查；checkpoint/广播版本区别 | §7.2，完整且没有照抄为 I 准入等式 |
| Performance metrics | engine 并发均衡、cache、router/KV、train/rollout 瓶颈；>90% 是调优预期 | §7.2，完整 |
| Arguments: Logging options | 两个 logger hook；True 跳默认；False 保留；buffer 指标内容另改 get_metrics | §7.2，完整 |

## 2. 发现与修订依据

以下保留发现时的表述与证据，避免已修内容掩盖审查记录；末尾表格记录本审查者实际看到的最新处理状态。

### R1：缺失行为版本的判定必须区分“整组全缺”与“部分成员缺”（中）

初稿 §6.2 的“U 缺版本返回 None，跳过判定；I 对 formal 组缺版本……typed fatal”容易被读成任何成员缺版本都会触发该分支。U/I 的 `miles/rollout/fully_async_data_buffer.py::group_oldest_weight_version`（U:40–43，I:42–45）实际上先**忽略** `oldest_weight_version is None` 的成员，再对剩余版本取 min。I `::_judge_consume_time_staleness`（407–435）只在整组无可解析版本，或 current_version 缺失且组声称 formal 时触发相应 fatal。

应明确：部分成员缺版本而其他成员有版本时，两者仍按已知成员判定；buffer 本身不证明每个 member/leaf/turn 的版本覆盖完整。全缺与缺 current 的 U 回退也应分别说明。公式最好标成“已记录的可解析版本集合的 min”，防止把数据缺口抹成完全可观测。I 对负 lag 的 fatal 不限 formal 组，此点可保留。

### R2：v2 预填 reward 会跳过下游 OPD teacher 评分，需补真实接线条件（中）

§3.3 已正确记录默认 postprocessor 把 agent 的 trajectory reward 写到各叶，§5.2 则说 teacher 字段可由下游 reward processing 产生；两者之间还缺一个实际分支条件：

- U `miles/rollout/session/v2/postprocessor_hub/default_postprocess.py::assign_reward/default_postprocess`：非 None 的 agent reward 写入 `Sample.reward`。
- U `miles/rollout/inference_rollout/inference_rollout_common.py::generate_and_rm`（122–131）：只对 `sample.reward is None` 的样本调用 RM。
- U `miles/rollout/on_policy_distillation.py::post_process_rewards`（403–436）：期待 RM 返回的 teacher scoring payload，再抽取 teacher logprob 或 top-k penalty；普通 float task reward 不是该 payload。

因此，原样保留 Harbor reward 的 v2 路径再把 custom RM 指向 OPD，不会自动补打 teacher 分数；后面的 OPD postprocessor 也不能把 scalar reward 解释为 teacher 响应。补一句须跳过默认 reward 预填或用显式组合评分/postprocessing 接线即可，不需要声称整条 OPD 不可用。也不应通过编写新代码来修这篇阅读笔记。

### R3：sample slot 释放“包括评分”须限定非 group_rm（低）

§6.1 写 sample callback 包括评分阶段。普通逐样本 RM 是如此，但 U `inference_rollout_common.py::generate_and_rm`（110–113）在 `group_rm=True` 时直接返回；组级 RM 在 `generate_and_rm_group` 的 gather 完成之后才调用（179–181），故 sample callback 已释放额度。Fully-async 参数校验没有禁用 group_rm；禁用它的是 session v2。

建议写“通常包括逐样本评分；若启用 group_rm，额度先随 sample task 完成释放，组级评分随后执行，整组评分结束后才作为完成组入 buffer”。这不改变 trainer 消费完整组的正确结论。

### R4：新增 policy loss 段修正函数定位，并标出数值保护（低）

§5.1 引用 `loss_hub/losses.py::policy_loss`，实际符号是 `miles/backends/training_utils/loss_hub/losses.py::policy_loss_function`。rho 的理想定义和 PPO/TIS 两种 ratio 的区分正确，但既然称“代码解释”，应补 U `loss_hub/math_utils.py:18–32` 的保护：PPO 计算 exp 前对 log-ratio 作非有限值处理并 clamp 到 `[-20,20]`；`compute_policy_loss` 再进行 PPO clip。这与 TIS 对 ratio 本身的 clamp 是不同层，不能笼统混成同一个 clipping。

### R5：R3 已知问题补丁已核；U 增量路由条件仍建议明确写入（低）

作者审查期间补入的远端 warning 正确：`sources/N11/arguments.remote-d2fc97ce.py:2992–2998` 不只提示大 payload，还明确 TODO：retract-mode weight updates R3 在 SGLang 有已知问题。不能把“参数能解析”解释为这种组合已验证。

U `miles/rollout/session/server.py:46` 的 `use_addition_r3` 仅在 `pause_generation_mode == "in_place"` 为 True。§6.3 已对 W 的“非 retract 用增量”做版本隔离；再明确这一行 U 条件，可避免读者误把 W 的完整规则应用于 U/I。最新 server 整体实现本审查未核。

## 3. 可保留且已独立核验的内容

1. **Token/训练 mask。** U `session/samples/merge.py::_compute_sample_from_openai_record` 从 output_token_logprobs 取 ID/logprob，生成 mask=1；`generate_utils/sample_utils.py::_merge_sample_pair` 对 observation 增量填 mask/logprob 0。response_length 含对齐增量、不能当 policy token 数；模型 delimiter trim、总序列截断、routing gap 截止前缀等限制解释正确。session 请求与 teacher scoring 的 logprob_start_len=0 用途被清楚分开。
2. **Session/tree 统计。** U v2 `picker_hub/drop_retries.py` 以 commit 序号判 sibling supersession；`default_postprocess.py` 在 picker 后分配共享 completion mask。存储保留分支不等于训练保留全部分支；共享 reward 不等于独立 verifier，均成立。
3. **训练样本转换与损失。** 新增 §5.1 已覆盖 U `miles/ray/rollout/train_data_conversion.py:161–277`：按 prompt 分组、按 rollout 合并同 reward，样本 std+1e-6，identity fallback，custom reward 优先；reward processing 早于 remove_sample 清 mask；默认 rollout_mask_sums 已接入。此处没有把叶当独立采样，也没有把“mask 清零”错写成不影响 baseline。`cp_utils.get_sum_of_sample_mean` 的分母公式与后端另作缩放说明正确。除 R4 的定位/数值细节，PPO 与 TIS 双 ratio、icepop 的新段落与源码一致。
4. **OPD 公式和边界。** U 完整 `on_policy_distillation.py`、`loss_hub/opd.py` 支持 sampled-token、五类 top-k 集合、三类权重、xor 不归一化、multi-teacher 路由。teacher/student scoring detach 后作 advantage penalty 的解释正确；并未把 teacher_p/none 截断估计冒称完整非负 KL。U arguments:2988–3006 的 student-side top-k 需要 legacy API，与 fully-async 排除 legacy 的冲突确实存在。另加 R2 即可补足一个重要的 v2 接线条件。
5. **Queue 与 staleness。** U `fully_async_data_buffer.py` 的 put/get 分工、FIFO 背压、retry 回原 prompt、dynamic reject 不 retry、N 默认关闭和 `lag>N` 的边界均准确。`_metric_consumed_staleness.append` 在接受判定之前，因此“消费 staleness”混入 stale rejected 组的文码冲突确实成立；I 同样存在该顺序。初稿 lag=5/1→avg=3 已明确标成代码推演，未冒称实测。
6. **失败与 timeout。** U `agentic_tool_call.generate`、`OpenAIEndpointTracer.collect_samples` 核实 collect 的 timeout/transport/empty 特殊分支；agent 失败后可成功收集已有 token，并不统一 ABORTED。120s 是 collect/delete 的各自边界，不能当 episode timeout。Harbor README 的 5400s 与客户端默认 7200s 已分清。
7. **版本与发布。** U session merge 只 append 单数 weight_version；I 的普通 Sample span 支持不会自动穿透该独立 merge 入口。该缺口的限定合理。最新参数文档读取范围明确，没有假称整个最新框架已审完。
8. **评测、性能与预算。** 三种 eval、snapshot collective/overflow 会等待、默认四份目录与 4B bf16 约32GB、串行 eval、共享广播版本边界均与完整官方文档一致。Harbor README 的 8 H200、4×8、65536、示例200/20及约10min/step，与 run.py 的 response8192、temperature0.8、TP4/EP8、lr1e-6、KL0.01、clip0.2/0.28 等相符。初稿清楚分开 README 调用示例与 launcher 默认/配方段，没有把局部成本乘成实测总账。GB300 大运行只被当作文档例子，没有补造成绩。

## 4. 残余未核与交付边界

- 本审查做静态原文/代码检查，没有运行 GPU inference、TITO 验证脚本、Harbor sandbox、teacher endpoint、训练或 eval；因此不证明版本组合实际能跑，也不产生任何吞吐/学习收益。
- 没有重新审完整 Harbor 源码、网络认证/隔离、verifier 对抗、flakiness 或污染。初稿将这些列为该文档/示例的披露缺口合理，不能扩大成全生态“不存在”。
- fleet/dispatcher/checkpoint eval 内部实现主要按两份完整官方原文复核，未逐行审查全部评测代码；GLM5.2 Daytona launcher 没有做完整依赖与 resolved args 审计。
- 对 I 完整 patch 链、冷恢复/weights_dirty/逐 engine 发布，以及 rh2 REALIGN 接线没有重新执行测试或做全差分审计；本次直接核 I 的 buffer/staleness 与相关版本入口，初稿其余项目映射的证明依赖作者所列源码/manifest，不应将本审查表述为再次全项目背书。
- 未核最新 d2fc97ce 整树的 session server、loss、buffer 全部行为；下载整份 arguments.py 不等于全量阅读。
- 本文审查的是阅读质量，R1–R5 修订后作者还须核对最终链接、真实符号和交付文件。不得写成新的训练准入制度，也不得在修订前把待修项标为已解决。

## 5. 作者修订对照建议

| 编号 | 笔记位置 | 实际复读状态 |
| --- | --- | --- |
| R1 | §6.2 | 已修并复核：区分整组缺/部分成员缺、current 缺及负 lag；明确不证明所有成员版本覆盖 |
| R2 | §5.2 | 已修并复核：v2 reward 预填会跳过下游 RM/teacher，组合评分须明确接线 |
| R3 | §6.1 | 已修并复核：区分逐样本评分与 group_rm 在 callback 之后 |
| R4 | §5.1 | 待修：`policy_loss_function` 符号、PPO log-ratio 数值保护 |
| R5 | §6.3 | 已修并复核：known R3 issues 与 U in_place-only 增量条件均明确 |

章节覆盖没有待补的大块主文。上表是本次独立审查的具体修订清单；作者修订与最终确认应记录在笔记 §12。

## 6. 作者逐项处理记录（2026-09-07）

此节由笔记作者追加，保留上方独立审查原文及发现时状态。所有变动限于 N11 笔记，不修改训练代码。

| 发现 | 实际处理 | 原始证据与结果 |
| --- | --- | --- |
| R1 | §6.2 已区分整组/部分成员缺失、current 缺失及任意组负 lag | U/I `group_oldest_weight_version`；I `_judge_consume_time_staleness`，独立审查已复读确认 |
| R2 | §5.2 已补 v2 reward 预填→跳过 RM→不会自动调 teacher；不将 scalar 当 teacher payload | U `default_postprocess.assign_reward`、`generate_and_rm:122–131`、OPD postprocessor，独立审查已复读确认 |
| R3 | §6.1 已明确 group_rm 在 sample callback 之后，完成组仍等组级评分 | U `generate_and_rm:110–113`、`generate_and_rm_group:179–181`，独立审查已复读确认 |
| R4 | §5.1/阅读清单修正真实符号；补 log-ratio 浮点、非有限值及 [-20,20] clamp，再 exp；区分 PPO clip/TIS clip | 作者重新读 U `losses.py:62`、`math_utils.py:18–32,254–278`，与修订一致；请求同一审查者复核此窄项 |
| R5 | §6.3 已补 known issues TODO 与 U in_place-only 增量条件 | 远端 d2fc97ce arguments:2992–2998；U server:46，独立审查已复读确认 |

额外补读：默认 reward 先按 prompt group，再按 rollout_id 合并 sibling 并归一化；默认生成 rollout_mask_sums；remove_sample 在 reward processing 后清 mask。依据 U `train_data_conversion.py:59–101,162–271`，独立审查 §3.3 已核实。残余未核范围保持 §4，不因修订改成已验证。

## 7. R4 独立窄复核（2026-09-07）

同一审查者重新读取笔记 §5.1 与 §1.2 阅读清单，并直接对照 U（`f2b7c79298a53c53861514d099f7def73bd29f4a`）`miles/backends/training_utils/loss_hub/losses.py:62`、`math_utils.py:18–32,254–278`。**R4 已修并复核一致**：函数名为 `policy_loss_function`；笔记已区分理想 rho 与代码的 float 转换、非有限值处理、log-ratio `[-20,20]` clamp 后 exp，以及后续 PPO policy clipping 和另一条 TIS ratio clipping。

该结果更新 §1、§5 中保留的“R4 待修”历史状态：本次 R1–R5 均已有对应修订及独立复读确认。此次仅复核 R4，没有重新开展全面审查，也没有更改笔记正文；§4 残余未核范围保持不变。
