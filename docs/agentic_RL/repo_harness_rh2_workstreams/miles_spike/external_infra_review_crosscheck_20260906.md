# 对 Claude 2026-09-05 审查的交叉复核

日期：2026-09-06。比较对象：[我的前轮审查](external_infra_review_20260905.md)与 [Claude 总报告](../tmp/external_review_20260905/00_FINAL_REVIEW.md)及同目录 A–G 切片报告。基线仍是主仓库 `ce2009f879cf38071d7898a1387e01d4e27741d6`，miles 集成 HEAD `98a0272e4158b2c20e3a34d210c79b50159af0f6`，没有实现变更。

## 1. 直接回答：有遗漏，而且有一项重要遗漏

**有。最重要的是我没有检查“生成了哪些轮、最终训练了哪些轮”的覆盖率。** 我上一轮证明的是剩余可训 token 与 capture 的对应，以及给定 mask 后 loss/分母的计算；这些检查不能证明之前生成的响应没有在 REALIGN 中丢失训练信号。我也没有充分展开多重预算、重复权限操作、额外 actor forward 和部分诊断指标的实际消费。

但 Claude 的报告不能整体照单采纳。它把几类不同问题混成了 P0：真实遗漏、已明确待 C/W8/W7 完成的入口、任务/环境侧已知递延、尚未证明发生的极端情形。部分推荐还依据错误的生产模板、配置读取或不完整的数学前提。正确处理是吸收具体增量，修正严重度与方案，而不是把“猜想全部成立”当作审查结论。

| Claude 的项目 | 我前轮是否漏掉 | 本轮裁定 |
|---|---|---|
| REALIGN 丢掉前序响应训练信号 | **重要遗漏** | 当前真实模板与 manager 可复现；不是所有多轮必丢，所推荐 thinking 开关对当前模板无效 |
| 截断策略无生产注入 | 已登记 C 待定，但未明确写出配置构造缺口 | 缺口存在；属于已计划的 C/W7 接线，不能称现成正式作业已出现 P0 |
| 25 次 SID 上限、不同 deadline 与 drain 的关系 | **遗漏** | 25 次模型请求后 429、无相应 termination producer；另确证排队可越过 deadline |
| 评分 timeout / zero-parsed 归为 infra | 前轮对通用失败归因排除得过宽 | 值得补审；全部改 reward 0 的建议缺少归因条件；SWE-Gym parser 缺口仍属已知 T2-d |
| assemble 自洽异常变 ABORTED | **重复发现** | 对应我 F2；不采纳“所有 drain/capture 错误都 fatal”或任意假设直接 P0 |
| R3 捕获成本 | **重复发现** | 对应我 F1；我已做真实 CPU 测量；不能按 session 只留最后一轮 |
| 额外 actor forward | **遗漏的优化候选** | 当前零 KL GRPO/custom loss 可消除部分重复计算，但该 pass 还产诊断证据，不是完全无用 |
| singleton support / 有效信号指标 | **遗漏的诊断缺口** | accepted>0 不证明非零梯度；不因此自动批准删零信号跳过机制 |
| shutdown 的 60 秒与后续清理预算 | 前轮已有故障覆盖，未突出默认预算差异 | 可重现超时后晚清理成功仍判失败；符合现有 B-6 合同，不能宣称正常结束必失败 |
| 19 次核对、130 拒绝点、三分之一可删 | 前轮没有全面做结构压缩清单 | 可作为进一步简化线索；现有计数不能证明这些比例均可无语义删除 |
| 在线 mismatch 完全缺失、零信号熔断未配置 | 没有这种遗漏 | **明确误报**：已有 `logprob_compare`，候选 YAML 已配连续 8 次熔断 |

## 2. 新增证据：REALIGN 丢失的是训练覆盖，不是剩余 token 对齐

### 2.1 当前路径可以复现；“所有多轮必丢”不能成立

生产链来源经第二角色复核：`bringup.py:828,861` 从 **vendored slime** 加载 HF tokenizer，并交给 adapter；不是 miles 自己的 tokenizer loader，也没有在这里装载 `qwen3_fixed.jinja`。`trajectory.py:180–190` 在漂移落入最近响应区间且**新一轮输出**短于阈值时选择 REALIGN；`:216–224` 将上一轮整个响应区域替换为新 prompt 内容，mask/logprob 归零。

主审重跑 [realign_probe.py](external_infra_review_crosscheck_20260906/realign_probe.py)，使用本机缓存的 Qwen3-30B-A3B tokenizer revision `ad44e777bcd18fa416d9da3bd8f70d33ebb85d39`、真实 Anthropic 消息翻译、真实模板渲染、真实 `TrajectoryManager` 和 RH2 identity span 导出。消息是合成输入，没有调用 Claude Code 或 GPU。

| 输入条件 | t0 / t1 生成 token | 分类 | 最终可训 token |
|---|---:|---|---:|
| 正常 tool-only 回放，保留 thinking | 27 / 2 | CLEAN | **29 / 29** |
| tool result 后增加独立 system-reminder text block | 27 / 2 | REALIGN | **2 / 29** |
| 同样 reminder，但新一轮输出达到 1024 | 27 / 1024 | FORK | **1051 / 1051**，两条 leaf |
| 上一轮很长、新一轮很短，带 reminder | 1125 / 2 | REALIGN | **2 / 1127** |
| 后续消息直接省略上一轮 thinking | 27 / 2 | REALIGN | **2 / 29** |

因此 Claude 指出的覆盖问题成立，且 REALIGN 可以删除远多于阈值的旧响应 token；阈值判断的对象是新输出长度。但“所有多轮必掉首轮”“只有上一轮超过 1024 才保留”等概括不成立。不同切片对阈值对象的表述也不一致，应以真实代码为准。

另有 `trajectory.py:370–426` 的 assistant rewrite merge：在特定树结构下，回放改写也会删除旧 generated TurnRecord；该分支判断的是旧响应长度。上表最后一行同时涉及这条路径，`REALIGN` 是 builder 的分类，不能认为只修改 `_align_to_prompt` 就覆盖了所有丢失来源。验收应分别覆盖这两条路径。

### 2.2 历史 run8 也不能证明唯一根因是 thinking 剥离

run8 是 Qwen3-4B + 旧 slime 的历史作业；“60/60 交付分支不含 t0”来自其实现报告。本地只保留一份完整 trajectory projection，不能把其余 59 条当成本轮重新核对过的 raw 证据。

[原始 token 探针](external_infra_review_crosscheck_20260906/run8_raw_probe.py)对保留样本读取 t0/t1 token 二进制、重算并核对 capture SHA256 后，得到：t0 响应从索引 18508 开始、长 624；t1 输出长 606；后续 prompt 与此前 token 流的首次分歧在 19064，即 **t0 的前 556 个 token 原样保留，却仍整轮移出 loss**。[辅助解码](external_infra_review_crosscheck_20260906/run8_decode.py)把差异定位到工具参数 JSON 键顺序（`file_path` / `replace_all`），不是 thinking 开头被剥离。辅助解码使用当前缓存 tokenizer，二进制前缀与 SHA 结论不依赖解码。

这说明至少存在“尾端重渲染变化导致整轮训练信号损失”的实际历史样本。Claude 总报告末尾承认两种根因未决，这一限定应保留在结论中，不能在开头又写成 thinking 唯一确定原因。

### 2.3 我修正前轮结论的范围

新增为**训前高优先级训练语义问题（建议 P1）**：生产条件可达且有历史信号损失，不等于当前全部样本已观察到相同比例。受影响的是真实生成响应的训练覆盖；给剩余 mask 正确计算 execution 分母不能补回被删除的动作。

建议先定义目标：允许哪些上下文重写、旧响应是否必须以独立分支保留、如何避免共享 response 重复计 loss，再选择最小修法。验收必须同时对比 generated/trained/dropped 的按轮计数与 token 数，覆盖 CLEAN、REALIGN、FORK、消息回放与多 leaf；不能只检验剩余 token 的逐位对应。

不能立即采纳 `clear_thinking=False`：当前实际 HF 模板没有读取该变量，本轮传入前后渲染结果完全相同。更改 system-reminder 的角色、换模板或改变 FORK 规则都会改变上下文/训练分布，需要 T0；TITO 也不能简单覆盖黑盒 harness 的真实上下文重写。这里没有选择具体修法，更没有修改 vendor。

## 3. 新增运行时漏项：模型请求预算与重复权限操作

### 3.1 25 次上限存在，但报告把模型请求与工具调用混在一起

当前 adapter 按 SID 计模型请求；真实 `_check_turn_cap` 探针前 25 次放行，第 26/27 次返回 429。生产没有 `max_turns_exhausted` 事实 producer。这种限制可能被上层当 API/harness 故障处理，无法直接进入 A5 的 policy horizon 处置，是我前轮应指出的配置真实性/失败分类缺口。

但 30–80 次工具调用不等于 30–80 次模型请求，一次响应可能包含多个工具调用；CC 2.1.205 接到 429 后具体如何重试/退出，本轮没有实测。不能从 cap 存在推成“正常任务第 26 轮必被判 harness_crash”。应在 C 中明确模型请求预算及终止出口，再验证真实 harness 行为。

### 3.2 交叉核查进一步确认：限流排队不受现有 deadline 覆盖

`async_worker.py:735–756` 在获取 `model_call` semaphore **之前**计算剩余 timeout，等待 semaphore 不受该 deadline 限制，拿到后仍使用旧 timeout 发请求。

[runtime_probe.py](external_infra_review_crosscheck_20260906/runtime_probe.py) 调真实 `ModelCallProxy.call`，设置绝对 deadline=20ms、先持有 semaphore 40ms，释放后 `send` 仍被调用并成功。这不是 Claude 用“900 秒请求上限大于 30 秒 drain”就能直接推导的情形，而是本轮实际证明的排队边界缺口。

建议 P1，在启用相应预算的 formal profile 前局部处理。应让现有 deadline 覆盖限流等待，并在发出请求前重新确认余量；不新增独立 clock owner。验收为已过期的排队请求不再进入 send，释放许可且按选定的终止语义收口。真实等待频率与长跑影响未知，没有把毫秒探针当生产延迟分布。

对 Claude 的原有推断需纠正：无排队时，proxy 本来就使用 `min(attempt_timeout, deadline-now)`，不是无条件等 900 秒。harness 起表与首次模型调用起表的差值、排队与取消完成时间才决定 30 秒 drain 是否不足。不能据两个 timeout 常量大小直接删除 proxy deadline。

### 3.3 重复 chown 是确定的正常路径浪费

`bringup.py:355–362` 与 vendored `sandbox.py:375–384` 使用 `id agent || useradd ... && chown ...`。shell 按左结合处理，已有用户时仍执行 chown。真实脚本配合无副作用 shell 替身证实调用了 `CHOWN` 和 `GIT`；“id 短路后成为 no-op”的注释错误。

rollout 侧有三处递归 chown，fresh grader 另有独立的一处。可以先减少 rollout 的重复动作，保留必要权限设置；无需以删除评分安全边界作为前提。三次 census、逐文件 hash、CLI 重装与轮询也值得 profile，但固定“53 次”和“节省多少秒”是静态估算，没有真机测量。

`model_call=32` 与在飞 execution=64 不是同一种占用：execution 包含工具执行和评分。评分并发 4 也不能单凭比 64 小就认定 GPU 必空转。贸然把 grader 内存和并发各提高 4 倍可能放大主机压力，应按 C/W7 的服务时间、排队和资源预算决定。

## 4. 额外 actor forward 与训练信号诊断：吸收增量，纠正误报

### 4.1 forward 有优化空间，但并非完全没有消费者

实际 `actor.py:625–666` 在 `use_rollout_logprobs=false` 时会额外算 actor logprob；当前零 KL GRPO + faithful DIS 配方里，优势计算主要用它取 shape，custom loss 自己重算 current logprob。[独立 CPU 探针](external_infra_review_crosscheck_20260906/extra_actor_zero_probe.py)将该列改成不同数值，并以非零梯度与抵消两种样本对比开关，优势、loss 与梯度保持一致；生产 `train_actor` 的 AST 控制流探针也确认开关影响。

| use_rollout_logprobs | get_mismatch_metrics | 额外 actor forward | 当前 logprob_compare 来源 |
|---|---|---|---|
| false | false | 执行 | 保留 |
| true | false | 跳过 | **同时消失** |
| true | true | 仍执行 | 保留 |

R3 填充仍先执行，训练仍进入 replay_backward；该探针用引擎/model 替身，不证明真实 GPU replay 消费。优化前提限定为当前零 KL GRPO、自定义 loss、无其它消费者的 profile；不能推广到 PPO、OPD、reference KL 或其它配置。

这项优化我前轮漏掉了。但“20–30% step 时间”没有本项目实测，而且这个 pass 也产数值对拍证据。应在 W7 区分训练 profile 与对拍 profile，保留所需诊断后再关；不能把去掉验证证据称为无条件等价。

### 4.2 在线 mismatch 并非完全缺席

`actor.py:483–521,665` 已按 rollout 发 `logprob_compare`；`miles/utils/logprob_compare.py` 记录 same_version、length_mismatch、provenance token 数与 mean_abs_diff。候选 launch 已启用事件目录。因此“只有一次离线检查、在线完全没有”是误报，准确说法是：**custom loss 的在线指标不够丰富，已有事件尚需最终 collector/judge/图表消费。**

可以补 DIS ratio 的上下尾、支持集大小、拒绝原因和按长度分布；但 current/behavior 的 log-ratio 同时包含策略变化与训推数值差，不能把一个新加的 KL 名称当作已完成两种原因的分离。同版本对拍仍有必要。

### 4.3 accepted 不等于有效梯度，这项遗漏成立

[singleton_signal_probe.py](external_infra_review_crosscheck_20260906/singleton_signal_probe.py) 经真实 loss dispatcher 得到 `dis_accepted_tokens=2`，但 loss=0、logits 梯度=0。因为 singleton support 上归一化 logprob 恒为 0，ratio 可合法为 1。这是已选目标的数学性质，不是 loss 公式错误。

Claude 建议区分 singleton 与多候选支持集是有价值的，但 `accepted ∧ support_size>1` 也不等于最终参数梯度非零。独立两组 n=8 的简化模型探针构造相反任务奖励：16 token 均 accepted、support 都为 2、优势均非零，参数梯度仍因相互抵消精确为 0。这个数学反例不证明 30B 真实任务常发生抵消，却足以推翻“精确零梯度只可能全 DIS 拒绝或全 singleton/系统 bug”的推理。

### 4.4 连续零信号熔断已配置，不能依据不存在的无限跳过删机制

库函数缺省阈值确实为 0，但 `custom_config.yaml:27` 已设 `max_consecutive_zero_signal_steps: 8`；`launch.sh:239` 检查它，`:424` 经 `--custom-config-path` 注入。Claude 的“候选 launch 未设”与源码冲突。

跳过一次、连续熔断或立即 fail-fast 可以讨论取舍，不能因为非零 advantage 就断言必须推翻已批 F2。`grad_norm==0` 是否能替代当前检查还取决于归约/optimizer 调用时点与数值精度，没有“一行必等价”的证据。本轮不批准删除 patch 0002/0003。

## 5. 评分通道：我排除得过宽，但不能全部改成 reward 0

SWE-Gym 11 仓库的 parser/spec 不受已安装官方表支持，是简报已登记的 T2-d；任务 adapter 正链与环境质量仍不在原审查范围。把尚未完成 T2-d 的任务直接上线再失败，不能算发现新的正式训练事故。

不过 **通用 grader 对模型失败与 infra 故障的归因** 属于训练 infra，我前轮不该全部留到环境审查。实际 `_exec_bash_checked` 对 test/setup 的 TimeoutError 均判 infra；`test_execution_timeout` 类型已有，producer 未实现。确定性不支持的 parser 配置被运行期 broad catch 变成单成员失败，也应在选定 adapter 后尽早暴露。

[官方 parser 探针](external_infra_review_crosscheck_20260906/grading_classification_probe.py) 使用已安装 swebench 4.1.0 真函数与 RH2 真分类器，构造两种有 Start/End 标记的日志：

| 合成输入 | 官方当前 PASS_AND_FAIL 模式 | RH2 manager |
|---|---|---|
| 候选源码 SyntaxError | apply_ok=true，空 status map，reward=0 | test_log_parse_failed |
| 环境中 python 命令缺失 | **完全相同** | **完全相同** |

Claude 指出“空解析默认会 silent-success”的注释不符合当前调用模式，这一点正确。但这两个输入也证明：**空解析自身不能证明责任在 agent patch。** 官方另有 FAIL_ONLY 模式，不能对其所有模式作同一概括。

已批 timeout→0 的三条件是 clean grader 正常启动、预算确定、**超时可归责 agent patch**，见 `fa/fa2a_decision_package.md:149–163` 和 `contracts/grading.py:41–47`。仅按 `phase==test` 改 0，省略了第三条件。应明确哪些可证明的候选失败进入负样本，哪些配置错误提前 fatal，哪些真正暂态错误保留 infra；若 owner 决定无论原因一律 0，那是主动接受误归因的 T0，不是修一条显然错误的 if。

同理，stdout/plugin 尚可影响评分，不推出 root-owned official 文件和非 root 执行边界可以删除。它们保护的是已声明的文件边界，未宣称封住所有 evaluator 控制面。可以减重复操作；不能因另一条攻击面尚未闭合就默认撤掉已有防线。

## 6. 哪些 P0/删除建议应降级或重新论证

### 6.1 已知未完成入口：仍是训前阻塞，但不是新发现的运行事故

`DispositionPolicy` 当前没有生产构造点，只有 `args.rh2_disposition_policy` 消费接口；未注入的合格 truncated member 确实会停 run。主审重跑 **45 项相关测试通过**，其中真实组链已覆盖缺注入失败以及 KEEP_FULL/DROP_GROUP 双注入。它证明接口中立，不证明部署配置已就绪。

06 A5 明确禁止 C 拍板前实现裁决，W7 随后负责实验包；W8 负责 eval 运输。我的前轮已标这些开放项，Claude 又从未审 launch 的 s1_compat/stock filter、eval 身份缺口推成 P0，会误导为代码已声称可以正式运行。

这里不能用“已经登记”否认缺口，也不能因当前未启用就放过训前接线。双方 P0/P1 口径可能不同；实质裁定是这些事项必须在对应 formal/eval 入口启用前完成，且不应与意外回归混为一类。

值得补充的是：C 完成后需要显式配置 producer，并可将适用项的缺配置错误前移到启动期。但“现在没有 producer”不支持提前把 policy_horizon/hard_wall 合成一个旋钮，两者的归因差异正是既有 A5 刻意保留的。

### 6.2 60 秒失败后晚清理成功：实际存在，是否算失败是合同选择

真实 aclose/RH2 关闭链的缩时探针结果：清理 2ms、第一期限 30ms 时成功；清理 60ms、第一期限 10ms 时，最终任务和清理都完成，但 verdict 仍保留第一期限超时而失败。没有使用真实 Docker。

这证明早期超时事实不会被晚成功抹去，也揭示两个预算需要一致解释。但现行 D2/B 的 B-6 正是要求 shutdown 不 ok 则非零退出。上限 120 秒不代表每个清理都会用满；取消并发执行，W3a 也已在评分前释放 rollout 容器。“正常结束必有 64–256 容器待删且必失败”不成立。

可在 C/W7 用统一总预算或明确阶段预算做压力退出验证。若想让退出码仅反映训练、忽略 shutdown 失败，是 T0 改判；不能直接以此删整个关停链。我的 F3 receipt 失败跳过清理仍需单独处置。

### 6.3 简化方向有增量，删除比例没有被证明

`TerminationFacts` 的重复运输与同源对账值得合并，这是 Claude 比我更充分的结构审查。但它还携带 receipt/冻结/静止事实，并非 `outcome` 完整副本；合并要保留 receipt 成功与交付的先后，以及实际 Sample 的 identity/reward/version/shape 绑定。

把准入改为只运输 verdict 的方案目前缺少叶版本来源、fan-out reward、同组同题与跨组串样等消费约束。slot 完整不代表其它绑定天然成立。`AttemptAssignmentRegistry` 也不是同一调用栈立即查回：它跨整个 await rollout 生命周期，并供任务与评分材料解析读取。可用不可变 context 简化，而不是只删校验后继续信任 mutable metadata。

“只防本进程 bug”不能直接定义为无用；否则和报告要求暴露 assemble 自身 bug 的结论矛盾。应逐边界证明事实已不可变、检查可前移或由另一消费者承接，再删重复验证。19 个位置并不等于一次 execution 重复执行 19 次；130 点的“不到 10% 真实”是分类口径，不是生产概率。

“三分之一可删”混合了当前未用原型、公开 CLI/历史复核能力、离线导出、schema、模式、安全与恢复语义变更，最多是方案预算。报告 E 引用的 import graph/统计原始文件不在交付目录，本轮未复核这些大数字；它还把自己列为加载不可达的模块计为每个 Ray 进程导入成本，前后矛盾。

已有明确窄删除面仍可先做；更多候选应标注放弃什么能力，而不是统一 T2。旧 CLI/exporter 不在当前训练根上，仍不等于没有消费者或已经获准删除。

### 6.4 性能与前沿性建议也要保留证据边界

最小负载 router 不使用 session key 是事实，但不是均匀独立随机路由，不能直接推出 cache 命中率=1/N。另一 engine 还可能缓存更早的同轨迹前缀，也不等于每次切换全 miss。profile 应测实际 cached tokens、prefill 与排队；无状态 hash 仍改变亲和/负载策略，不能靠“15 行”免除取舍分析。

“样本可信层超过多数实验室”“fully async + retract + spans 等价于 K3 partial rollout”都应收窄。公开报告披露少，不证明它内部保障更弱；跨权重续生成解决部分相似问题，不证明 token/trajectory 调度、恢复与上下文状态合同完全相同。本项目尚无当前完整 GPU 闭环，更不宜先作全面领先主张。

Claude 的“第一批不改语义”应重写：默认 formal、换 filter、eval bypass、删除公开 schema/重要依赖、改变 shutdown verdict、扩大 grader 资源，不能混作一批普通死代码清理。W8/W7 内落实已批事项可以继续，但必须保留各自前置；加诊断计数与删未接线原型可单独推进。

## 7. 修正后的工作优先级与审查停止条件

1. **补上我遗漏的 generated→trained 覆盖审查**，并把 REALIGN 处置列入首训 harness profile 的训练语义决策。R3 路由来源问题继续保留，两者不同，不能互相替代。
2. 对 25 次 cap 与多重计时给出明确 producer/归因；局部修正限流排队越过 deadline。异常分流沿我原 F2 收敛，避免新增一长串 fatal 白名单和第二个按次数补救层。
3. 局部修重复 chown，评估额外 actor forward，并保留同版本对拍；增加真正用于 C 决策的轮/token 覆盖、singleton、drop 长度/原因信息。不要把 accepted 数直接当梯度证明。
4. 将通用评分失败归因补回审查范围；具体 SWE parser、控制面与镜像验证仍随数据/环境工作流。原 F1 R3 捕获成本和 F3 receipt 清理继续成立。
5. W8 → C → W7 → GPU 主线继续；没有理由先批准十一项大规模 T0 重构。宽泛压缩方案与新调度/重试放入有证据的独立决策。

本轮没有修实现，也没有 GPU/Docker 实测。新增复现材料在 [证据目录](external_infra_review_crosscheck_20260906/README.md)。已完成一次独立交叉核查并重跑关键证据；剩余未知明确交给 profile、真实 harness 请求和 GPU 资格，停止继续扩大审查面。
