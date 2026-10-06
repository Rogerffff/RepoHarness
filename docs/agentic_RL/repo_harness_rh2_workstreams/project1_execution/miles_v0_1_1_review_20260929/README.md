# miles v0.1.1：项目一复用与迁移审查

日期：2026-09-29。状态：**审查完成；以下是建议，未升级依赖、修改生产代码或批准新训练语义。**

## 1. 结论与建议顺序

**有值得复用的内容，但没有发现必须先整体升级，才能继续当前 SWE 闭环的功能缺口。** 建议短期吸收少量有实际消费者的修复和观测口径；完整升级另作一次集成迁移，不能直接更换镜像或覆盖 fork。训练底座升级与替换 Claude Code 捕获层应当分开，前者不要求同时采用新版 SessionCore/TITO。

近期最明确的两项是：

1. **回移 #3125 的 PP 阶段判定。** PP 是流水线模型并行。当前效率档的非末级也可能持有 rollout logprob，旧代码据此执行本应只在末级进行的优势计算。新版改为查询真实 PP stage。本机原函数对照已确认分支差异；当前零 KL 配方没有证据表明既有 loss 算错，收益先按消除无用计算和错误阶段假设理解。
2. **吸收 #3334 中“只统计实际消费组”的修正。** 当前 fork 的 `avg_staleness` 在丢弃过旧组之前就累计，混入了未训练组。现有逐组事件能区分，训练准入没有因此改变。可先移动统计位置，再用 RH2 已有版本事实补有用的派生指标；不必更换整个 buffer。

其次是按需要复用多叶轨迹展示与按 execution 汇总的长度指标（#2881/#2765），接到 I01/I20/E5 的现有数据上。BF16 logits、增量路由、原生 session、NVMe、LoRA 等分别有入口、配方或硬件前提，不能作为“升级后自动获得”的收益。

**不建议现在打断 B 线环境筛查和已排定的 A 线收口，转成无边界的框架升级。也不建议长期不断给旧底座加补丁。** 合理节点是最小真实闭环与其验收样本固定后，安排独立迁移；若最终选中的训练模型或设备必须依赖新版栈，则提前迁移底座，但仍保留当前 RH2 捕获与评分边界。

## 2. 比较的到底是哪两个版本

| 对象 | 本次核对结果 |
| --- | --- |
| 官方发布 | [v0.1.1](https://github.com/radixark/miles/releases/tag/v0.1.1)，2026-09-26 UTC 发布 |
| 固定审查提交 | `2806267d060d51b1d3b62f85a1f9b145047aeef9`；未将后续 main 混入结论 |
| 当前实际上游基线 | `f2b7c79298a53c53861514d099f7def73bd29f4a`，不是干净的 v0.1.0 |
| 当前使用的 fork | `reference/miles-rh2-integration`，`275e31eb21ecceeb27cb0d1a522c6a59f348dc2e` |
| fork 构成 | 基线 + 4 个上游选材 + 20 个 RH2 patch；以 [manifest](../../miles_spike/integration_base_manifest.json) 为准 |
| RH2 代码基准 | `a31cdcd0adb0fab3e681201edfb928653fdf5b3c`；共享工作区其它未提交工作未改动 |
| 相对当前基线的体量 | 442 个提交，1,290 个文件变化；这是 Git 差集，不是发布稿的 PR 数 |

审查覆盖发布清单的 15 类、122 条详细条目及 3 项高亮模型；逐项分类见 [release_coverage.md](release_coverage.md)。针对当前真实路径，另做了 [运行时追踪](runtime_trace.md)、[session 反证与简化审查](session_review.md)、[训练语义审查](training_review.md)，主审独立重跑三个探针并核对关键源码。

“完整检查”在这里指**发布面完整盘点、与本项目的实际相关性核对、关键迁移接缝深入检查**，不指逐行审计全部上游新增代码，也不意味着在所有模型、传输协议和硬件上验证。未运行 GPU、远端训练或新版镜像，未宣称上游性能数据可复现在本项目。

## 3. 值得吸收的内容，以及真正能得到什么

| 项目与上游来源 | 当前情况 | 建议与验收边界 |
| --- | --- | --- |
| **PP 末级判定** [#3125](https://github.com/radixark/miles/pull/3125) | 当前效率档在非末级也会进入优势计算；CPU 已复现 | 窄回移候选。保留末级数值，非末级不造优势；诊断/效率档都覆盖。正式作业若 PP=1 则没有这项节省。 |
| **消费时陈旧度统计** [#3334](https://github.com/radixark/miles/pull/3334) | 当前旧指标混入被 stale 过滤的组；逐组事件更准确 | 先修统计位置。新版的最老/最新 lag、版本跨度、token 加权 lag、版本覆盖率可按 I20 缺口吸收。不要重写治理 buffer；新旧曲线注明分母变化。 |
| **按原始 execution 汇总长度** [#2765](https://github.com/radixark/miles/pull/2765) | I01 B 一条执行可分多行；RH2 已有 `turn_coverage` | 复用聚合函数或口径，统一挂现有报告。训练行 response 总量含 masked 区域，不等于真实生成账单，也不等于总输入 token；不能拿它直接计算 B 相对旧阈值的成本增量。 |
| **多叶轨迹可视化** [#2881](https://github.com/radixark/miles/pull/2881) | 相同 sample index 的多个训练行需要分别展示 | 可以复用上游离线 viewer/dump reader，避免自建训练看板。其 `(index, occurrence)` 标识需与 RH2 leaf ordinal 对齐；生产者和读取端配套核对，避免展示端覆盖旧叶。不是当前首训的前置。 |
| **模型精度 logits** [#2764](https://github.com/radixark/miles/pull/2764)、[#2818](https://github.com/radixark/miles/pull/2818) | 默认训练优化只给 `policy_loss/sft_loss`；RH2 是 `custom_loss`。新版诊断额外 forward 可部分受益 | 若 E5 显示 logits 是峰值显存大头，值得单独适配 custom loss。需比较 masked logprob、温度、DIS、fanout、TP/CP 与实际梯度；不能照搬发布中的显存降幅。 |
| **logprob 分块** [#2825](https://github.com/radixark/miles/pull/2825) | 修的是 `true_on_policy_mode` 忽略 chunk；现有 spike 未开此模式，默认 chunk=-1 | 有相应配方时再用。CPU TP=1 的 masked logprob/entropy/梯度分块对照一致；仍先 gather 全词表，不能宣称全链显存严格受 chunk 限制。 |
| **独立训推差异统计** [#3655](https://github.com/radixark/miles/pull/3655) | 修掉默认 policy loss 中 rollout baseline 与自身比较的假零；不调用 RH2 faithful loss | 借用“独立 producer”原则，别直接新增重复指标。效率档没有同版本对拍来源时仍是不可用；更新后的 current-vs-behavior 差不能标为纯数值误差。 |
| **不变 payload 解码移出事件循环** [#3339](https://github.com/radixark/miles/pull/3339) | 是新版 tracer 客户端的 safetensors decode，RH2 不走此路径；E3 已降低部分 tape 成本 | 只有量到当前剩余解码阻塞时，才借鉴线程化；不是升级就自动加速，也不意味着服务端整棵树的装配可无锁搬到线程。 |
| **单组取消隔离** [#3319](https://github.com/radixark/miles/pull/3319) | 上游将被取消的单组转 ABORTED；当前直接读 task.result。尚未证明正常 RH2 有独立单组取消场景 | 先确定取消来源再考虑回移；不能吞整体关停或未知内部错误、自动重采。保留当前活动组 owner、close gate、丢组分母。不是本轮确认的生产故障。 |
| **统一发布/保存组件** [#2752](https://github.com/radixark/miles/pull/2752)、[#3198](https://github.com/radixark/miles/pull/3198)、[#3342](https://github.com/radixark/miles/pull/3342) | 新 WeightUpdater、HfWeightIterator、SnapshotPublisher 可减少重复实现；与新 controller 紧密相连 | 完整迁移时复用，避免 RH2 自建权重传输平台。保留实际 dirty、所有引擎收敛、冷恢复版本与失败清理合同；HF 导出重叠写盘的实际收益随 checkpoint 阶段测量。 |

具体例子：若两个组的版本差为 1 和 9，而上限为 3，只有前者进入训练，当前旧 `avg_staleness` 仍可能报 5。新版 selected 口径会报 1，被丢组另外记 9。这个修正有利于判断训练真正吃到多旧的数据，**不要求改变 staleness 上限或重新准入被丢弃的组**。当前落点在 `fully_async_data_buffer.py:299`，新版先过滤后累计。

## 4. 容易误认为“本项目还缺”的几件事

### 4.1 Sampling-support replay 不是这次才获得

当前已含 #2200 原语、#2595 运输和后续 bounded replay 选材，RH2 自定义 loss 已使用采样时的支持集归一化。上游 #3354 完善默认 policy、FSDP、session 等入口，可以在迁移时减少旧选材负担，但**不能替代 custom loss 的运输补丁 0001**。

旧选材 #2596 没有作为同一提交合入 v0.1.1，不能按 PR 名称直接判定内容相同。新开关覆盖 `top_p<1 OR top_k>0`，当前 RH2 仍要求自身已定的采样范围；不应为了沿用新 validator 暗改配方。

一个值得更正的口径：top-k 不一定是实际支持集基数的严格上界，cutoff ties 可能超 K；真实容量另受 SGLang `sampling-mask-max-tokens` 约束。现有 spike 的 K=151936 是接近全词表的兼容配置，不能拿“小 K 的内存收益”推算它。先量 support 大小与字节量，再讨论降低 K；裁剪 mask 会改 loss 概率空间。[上游 replay 契约](https://github.com/radixark/miles/blob/2806267d060d51b1d3b62f85a1f9b145047aeef9/docs/advanced/sampling-support-replay.md)

另外，新版仍明确拒绝 replay 与 reference KL/OPD 同开。当前 GRPO/DIS 不受此限制新增影响，但以后做 OPD 仍需定义 full-policy 与 support-normalized 两种 score，不能把发布说明当作该组合已经支持。

### 4.2 发布后 JIT drain、压缩观测与部分依赖已具备

- #3343 的“发布后再 drain”关键顺序已由 patch 0014 实现；新版不是首次修复本项目该问题，也没替代 0014 的其余合同。
- #2682 bridge 恢复、#2710 压缩统计、#2535 Mooncake 数据传输文档及对应能力已经在当前基线。
- SGLang 0.5.18 选材与 FLA 0.5.2 已提前接入；当前 Docker 默认也已是 CUDA 13。不能把发布稿相对 v0.1.0 的全部变化算作本项目增量。
- `loss_hub` 目录拆分已在当前 fork；新版没有移除 custom loss 的全部 API，主要失配是调用方字段与状态容器。

**I27 的多轮 KV 局部性也没有自动解决。** RH2 已发送 `X-SMG-Routing-Key`，但 v0.1.1 的 `MilesRouter._use_url()` 仍按最少在飞请求选 worker，不按这个 key 固定会话。新 session 会加 header，不等于当前所选 router 会使用它。采用支持相应策略的 router 时可复用现成机制；是否切换仍看 E5 的缓存命中、负载不均与尾延迟实测，不必先自造粘滞路由平台。[路由选择源码](https://github.com/radixark/miles/blob/2806267d060d51b1d3b62f85a1f9b145047aeef9/miles/router/router.py#L229)

### 4.3 原生 Anthropic + TITO 值得关注，但不能直接接管 CC

本轮用已有真实流量核对：旧基座 22 次尝试的 **617/617** 个生成请求含 `thinking` 和 `output_config`；修后正式启动条件的真实 CC 2.1.205 + 剧本引擎验收中，**3/3** 个请求也含两字段。新版入口原函数明确拒绝它们；`tool_result.is_error=true` 也被拒。后一个字段在旧语料的 **374/617 个请求**中出现，历史内容会重复，不能解释成 374 次独立工具失败。不是靠猜测可能的请求面判不兼容。

TITO 通过消息匹配复用旧采样 token 来构造下一轮输入；当前 I01 B 对当轮请求完整重渲染，只在精确 token 前缀时合行，漂移时保留旧行。这是**改变未来模型输入**与**改变训练表示**的区别。上游默认 picker 对相同 prompt 重试只保留后次输出；CPU 对照中，输出 `[3]`、`[4]` 的两次真实采样，默认上游仅留 `[4]`，当前 B 两者都留。上游 identity picker 能保留两者，不必重造树，但仍未消除输入语义差异。

因此建议保留当前捕获链；未来如果重新讨论 I01 C，可复用上游 tokenizer、matcher、请求参数解析与 v2 森林，避免重复实现。**本审查不重启已暂缓的 B/C 专门实验。** 详细来源、原函数反例、能力边界见 [session 审查](session_review.md)。

### 4.4 增量 R3 不等于解决 I18

上游 #2834 在非 `retract` 模式使用增量路由片段；`retract` 分支仍有“最终全量 tape 覆盖”的处理。逐调用权重版本 span 也只是版本运输，不证明每个历史动作的路由恰好来自其行为 forward。其 session + R3 + retract 组合仍有已知问题提示。

它是 I18 的有用设计材料，可减少未来实现量，但不能据此批准当前路由来源、改变异步暂停方式或把 I18 标完成。E3 的紧凑存储、路由来源选择、SGLang 实际计算必须继续分别判断。

## 5. 完整升级的主要成本

这次是 controller/worker 架构重构：旧 RolloutManager 被分为 InferenceController 与 RolloutExecutor，trainer 变为 cell-based TrainerController，engine 调用从 Ray actor 转为 HTTP client。新公共组件值得依赖，但 RH2 的 owner 和证据必须迁到新的真实消费者。

机械预演（只运行 `git merge-tree`，未合并/checkout）出现 **36 条冲突消息**。这不是 36 个独立 bug，也不能拿来估工期；有些是文件搬迁或 CI，另一些没有文本冲突却会改变语义。静态扫描 27 个 RH2→miles 导入项发现 6 个位置失配，含自定义事件模块的可选回退；不是 6 个都必然启动崩溃。[证据](../../../../../runs/miles_v0_1_1_review_20260929/merge_tree.txt)

| 必须保留的合同 | 新版直接替换的具体后果 | 本轮证据 |
| --- | --- | --- |
| custom DIS 收到真实 sampling mask | 新版 backward caller 仅给 `policy_loss` 选 mask 字段；RH2 reader 明确抛缺字段异常 | 原函数/表达式 CPU 对照；不能靠关掉校验使其运行 |
| execution 等权和逐动作归属 | 新 dispatcher 仍有兼容接口，可保留；Sample 版本字段已从字符串列表改为每调用绝对区间 | 2 executions/3 rows/2 microbatches 的线性分子缩放与梯度相同；不是完整 DIS 验证。旧版本列表直接写新版 Sample 会失败 |
| 精确零梯度不 step、不增 scheduler、不发布 | 上游没有 0002/0003；漏移植会有 Adam 动量/weight decay/版本语义差异 | 逐消费者源码；合法 all-skip 配合新发布守卫，第 4 次 get 可被拒 |
| 异常和正常结束都关闭 RH2 在飞任务与外部资源 | 新 driver 只有正常尾部 dispose；executor 不调用 RH2 aclose | 同一 trainer 异常：当前 driver 执行 dispose，新版不执行；外部服务替身，未宣称已实测真实泄漏 |
| 独立固定 checkpoint 评测零训练派发 | 新 train_async 在零轮循环前仍 eager 提交训练 get | 同一 I21 配置，真实函数体 CPU 对照出现额外提交；尚未经过真实 Ray/GPU |
| infra 评测结果与模型零分分开 | 新默认 metrics 仍将 `None` 映射为 0；无 RH2 宿主 eval stamp | 代码追踪；保留 0018/0019 和自定义 eval report |
| 全引擎版本收敛及冷恢复状态 | 新版通用发布、save/load 接缝没有等价的 RH2 全引擎回读与已发布版本恢复账 | 实际 owner/消费者追踪；0015/0016/0020 需重新安放 |

这些都属于**迁移后的条件风险**，不是当前已经修好的主链突然出现同样故障。三个控制流反例在 [runtime_contract_probe.json](../../../../../runs/miles_v0_1_1_review_20260929/runtime_contract_probe.json)，训练接缝在 [training_probe.json](../../../../../runs/miles_v0_1_1_review_20260929/training_probe.json)。

### 20 个 patch 是否可以删

[运行时报告 §5](runtime_trace.md#5-指定的-16-个补丁逐项承接表) 逐项覆盖 0002–0006、0010–0020，共 16 项。其余四项如下；与训练报告合起来覆盖当前全部 20 项。

| patch | 上游能否替代 | 迁移处理 |
| --- | --- | --- |
| 0001 自定义 loss 的 mask 运输 | 不能；新版仍按 loss_type 限制 | 在新 `run_forward_backward_pass` 调用方恢复 replay-only 条件，保持缺字段失败 |
| 0007 SGLang/Megatron pin | 新 release-lock 可承接主要来源锁定职责，但普通 Dockerfile 默认 commit 为空 | 改为消费 release-lock 或固定镜像 digest，不照搬旧 SHA，也不能只 checkout miles tag 后裸 build |
| 0008 逐 token 版本账 | 新 `WeightVersionsPerCall` 可承接运输表示，不能直接接收旧 `list[str]` | 映射 RH2 capture/identity spans 到训练行的绝对区间，处理 FORK/压缩/工具 gap，随后减少重复容器 |
| 0009 严格版本载荷验证与文档 pin 修正 | 新 Sample 有验证，但空版本来源可成为空表、部分检查仍为 assert | 保留正式链缺来源/越界/覆盖错误的处置；新表示验证通过不等于原 provenance 合同成立。旧文档修补按新 lock 重写 |

**结论不是“20 个原补丁永久照搬”。** 应按语义合并重排，能由新公共结构承担的容器与运输代码可以删；已有 CPU/GPU 反例是删补丁的依据。此轮没有证据支持按功能名称批量删除。

## 6. 其它发布项的项目价值

| 方向 | 当前建议 | 原因与触发条件 |
| --- | --- | --- |
| Harbor / E2B / Daytona、Terminus2 压缩示例 | 作为 B 线 terminal 补充评测/未来 harness 的参考，不替换当前 SWE 执行与评分链 | 可以复用 in-process Trial 接口和资源配置；示例把一些 generic exception/timeout 记 0，与本项目 infra 无 reward 冲突。供应、题目资格、可信测试与 owner 清理仍需自己的边界。 |
| 新模型与 Qwen3.5/3.6/3.8 TITO | 等模型选择实际需要时采用匹配的整栈 | 训练模型、tokenizer 和 checkpoint 转换、MoE/kernel/量化路径应成套核验；发布大模型在 GB300 上的结果不推出当前 8 卡任务可用。基座探针用过某 API 模型，不等于已决定训练它。 |
| colocate host-memory 优化 | 当前训推分离路径不使用；若因容量改为同卡交替再评估 | 把 CPU 峰值转到 GPU 交接余量，有取舍；不能无前提套内存下降数字。 |
| Adam/Muon NVMe offload | 目标机真的受 host/optimizer 内存约束时复用 | Adam 的流式初始化值得记入容量工具箱；Muon 还涉及优化器选择。真实 NVMe、page cache、I/O 与恢复成本需测。 |
| NVFP4/QAT、TE 量化缓存 | 当前 BF16 配方后置 | 量化、offload 与硬件路径均有前提；不是无语义变化的默认加速开关。 |
| LoRA / Multi-LoRA v2 / Tinker | 单 LoRA 可在资源需要时另议；多租户服务当前不建 | 当前单作业全参没有多租户需求，不为展示平台广度转向项目二。 |
| Mooncake rollout 数据传输 | 当前基线已具备；跨机/大 payload 有实测瓶颈再启用 | 数据运输与权重传输不同；服务内存、网络与回收不能省略。无需为了获得这份文档升级。 |
| 自动故障恢复 | 不自动启用 | 上游正在重构，tag 的 FT 文档自标过时；当前批准的是引擎故障停 run 与冷恢复。升级组件不批准改变失败处置。 |
| AMD、多模态、PPO/MTP等 | 对应任务/设备/配方出现时再评估 | 当前未使用的消费者没有即时收益；完整盘点不等于将所有发布功能加入项目路线。 |

尤其不应把 Harbor 的默认 orphan 回收直接搬回 RH2：本项目刚删除跨 manager 按年龄误删容器的逻辑。不同 provider 的 ownership 合同需分别看，不能因上游示例使用清扫就恢复旧行为。

## 7. 镜像、依赖与启动形态

| 依赖 | 当前 fork | v0.1.1 核对值 |
| --- | --- | --- |
| SGLang | 0.5.18，`4e230c3d85cefdab5b65eeb6f6f87793a707a6fb` | Docker 基底 0.5.20，lock `880e3d2453eb7ef1738350e8c35ba2b956cc93a9` |
| Megatron | `235952df607b3820716e5e67728a5ab470ca33ae` | `f148a32b4385b758b66a77c9c3ad1641f1295d4b` |
| Megatron-Bridge | `7f0fb345…` | `8cd3466d…` |
| torch_memory_saver | `f05a8754…` | `b5588e83…` |
| TileLang / FLA | 0.1.8 / 0.5.2 | 0.1.14 / 0.5.2（另有配套 patch） |
| CUDA | 当前 Docker 默认已经 13 | 版本化发布仅 CUDA 13；本次不是首次从 CUDA 12 跨代 |

来源：[release-lock.json](https://github.com/radixark/miles/blob/2806267d060d51b1d3b62f85a1f9b145047aeef9/release-lock.json)、[Dockerfile](https://github.com/radixark/miles/blob/2806267d060d51b1d3b62f85a1f9b145047aeef9/docker/Dockerfile)、实际 fork 同文件。tag 内 `docs/developer/versions.md` 的 SGLang 表仍写 0.5.16，本次采用实际 Dockerfile/lock；文档存在不代表依赖已严格锁住。

发布 CI 会把 lock 传给 Docker build args；普通 Dockerfile 的 SGLang/Megatron commit 默认为空。正式迁移应消费完整 lock，或固定 release 镜像内容 digest。2026-09-29 只读查询 DockerHub 得到 manifest `sha256:6355834f16bacd35d5d40c43f142e3758376f7b2e8d678bccfe870c092bd96bf`；各架构 digest 在 [docker_tag.json](../../../../../runs/miles_v0_1_1_review_20260929/docker_tag.json)。没有 pull 镜像，不能当运行时核验。

SGLang 最后一次 release pin 包含 KV 清理 kernel 完成后再 unmap 内存的同步修正，实际触发面是 KV offload/release，不是所有 fully-async rollout 都自动受益。[固定提交](https://github.com/sgl-project/sglang/commit/880e3d2453eb7ef1738350e8c35ba2b956cc93a9)

六类 breaking change 都已核对，迁移时与我们相关的处理是：

- 外部 router 配置被移除，改由 miles 启动每模型 router；**不等于 `--use-miles-router` 被移除**。单模型仍将首个实际 router 地址回填 `args.sglang_router_ip/port`，然后构造 RolloutExecutor，当前 RH2 的 URL 读取有兼容承接，不需要因字段名就重写。若旧命令显式指定外部 IP，则必须调整；多模型/专用 eval fleet 另核所绑定的 router。[回填源码](https://github.com/radixark/miles/blob/2806267d060d51b1d3b62f85a1f9b145047aeef9/miles/ray/rollout/rollout_server.py#L22)
- session port/count 独立，默认 worker 数变化；保持 RH2 捕获层时不因升级而额外起一组不用的 session workers。
- control API 参数改名及绑定地址变化，按实际远控需求配置，不直接复制旧命令。
- CUDA 版本、LoRA v1 移除分别只影响采用相应形态的作业。
- checkpoint 对已存在目录的覆盖会先删除旧目录；使用唯一保存路径保留上次可用 checkpoint，不把覆盖写当原子替换。[写盘变更](https://github.com/radixark/miles/pull/3198)

## 8. 建议怎样整合，避免把项目拖进第二次搭架构

### 近期窄切片

给 Claude 的下一份短 Brief 可以只包含 #3125 与 #3334 的统计位置修正。两个改动分开提交，各有原函数正反控，保留现有 fork 构建与双 lane。若报告已经从逐组事件得出正确消费指标，只修上游旧指标或明确停用它，不再建第二条同名统计链。

#2765/#2881 按当前可读性需求选择；先检查现 `turn_coverage` 和离线报告是否足够。它们没有“必须在首训前做完”的理由。现有 E5 八卡清单增加所选优化的前提核对和测量维度即可，不为本次发布再建一套平台。

### 真正升级时的最小边界

1. **固定旧版本验收输入和新版本依赖。** 使用现有 reference 回放与 failure probes；保留可回退的旧 integration manifest。新底座固定到此 tag，不追逐每日 main。
2. **迁移 runtime/训练消费者，保留 RH2 harness 层。** 按第 5 节语义表迁移，而不是逐个解决 Git 冲突后即认为完成。利用新公共类型减少重复表示，但保留原错误分级和关停 owner。
3. **先完成本机最小证明。** import/配置接线；I01 多行身份与版本映射；custom loss 真 mask；零梯度/发布；缺评分 None；零样本与零训练轮评测；异常关闭；冷恢复编号/版本对账。这些来自既有合同，无需另造泛化测试平台。
4. **接既定真实 GPU 验收。** 真 tokenizer/引擎的 output IDs、支持集、路由、版本；训练梯度和执行计权；发布后的每引擎状态；共享/独立 eval；checkpoint 恢复；峰值内存与各阶段耗时。正式模型、作业参数与 I18 仍按原流程决定。

若某个上游优化只在新 controller 路径容易采用，优先随完整迁移整合，避免将新 controller 的半套机制硬移植回旧架构。反之，纯指标、PP stage 小修不必等待一次大升级。

## 9. 本轮实际验证与停止条件

- 读取固定 tag、官方 release、依赖 lock 与构建流程；核对当前 manifest 和 fork 实际 HEAD。
- 发布面 122 条分类，173 个不同 PR/issue 引用；其中 164 个可由 tag 历史的 PR subject 定位，17 个已在当前 base。未定位的 Multi-LoRA 系列不按提交标题强行推算祖先关系，而按已存在源码/发布说明归类。另核 3 项高亮模型的需求前提。
- 机械 merge-tree 与 27 项静态 import 扫描，仅作为迁移范围证据。
- 三个角色按审查标准独立核对 runtime、session 与训练，主审阅读报告、源码并重跑三套 CPU 探针，全部成功；[主审重跑记录](../../../../../runs/miles_v0_1_1_review_20260929/parent_recheck.json)。探针的外部替身、原函数提取与 TP/CP 范围在各子报告中明确，不将重叠检查数相加。
- **没有运行**新版镜像、真实 Ray/分布式/GPU、目标 SGLang support cap、NVMe、任何新模型或完整训练；没有将发布数字列为本项目性能证据。
- 本次只新增审查文档、探针/快照，并追加 A 线账本。生产代码、当前 miles fork、B 线在制品未修改；未提交/push。

本轮达到“哪些值得用、为何有用、怎么接、哪些不能直接替换”的停止条件。仍待的是选择实施范围后的 Brief 与实际集成验收，**不是发现更新就必须采用全部功能**。项目一应继续把上游通用能力接成可解释、可复现的真实 agent 训练闭环；闭环证据与可量化瓶颈改善，比自建与上游重复的服务更有价值。
