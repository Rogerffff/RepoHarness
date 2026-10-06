# I01 B 实施补丁：Production Tracer 独立报告

日期：2026-09-09。审查角色：Production Tracer。主仓库基线 `2a533b1f9b8e7cc8a9aca1a90b8ea1b32afb31f8`；miles 集成基线 `98a0272e4158b2c20e3a34d210c79b50159af0f6`。审查对象为三个源码文件、两个测试文件的未提交补丁；没有修改被审源码或测试，没有运行 Docker、GPU 或付费调用。

## 1. 结论与停止条件

**本角色未发现 I01 新增的生产训练交付缺陷。** `fork_threshold_tokens=0` 已接入真实 manager；非空动作经身份回填保留，新增训练行仍属于原 execution/member；覆盖统计进入 execution audit 后从训练样本剥除。下文的小型 CPU 接缝探针证实了两成员、每成员两行的真实编排与 miles 消费路径。

本结论限于配置接线、身份/训练行保留与诊断运输，不替代 Falsifier 对统计口径的检查，也不证明目标 GPU 上的 packing、显存或吞吐。I18 路由、I19 压缩及 C 路线不在本次范围。

**停止条件：** 本文源码链与 CPU 探针足以支持本批训练接线进入主审收口；诊断口径问题由主审与 Falsifier 单独裁决。没有证据支持为这条运输链增加状态机、重试或新的轨迹拒绝路径。

## 2. 当前生产调用链

当前实现实际使用的类名为 `TrajectoryManager`。从配置到消费的关键位置如下；路径均相对仓库根目录。

| 环节 | 当前事实与源码位置 |
|---|---|
| 配置进入 manager | `adapters/slime/bringup.py:234` 定义常量 0，`:908` 传给 `AnthropicAdapter`；vendor `slime/agent/adapters/common.py:164–166` 明确判断 `is not None`，所以 0 不会被当成未设置。 |
| token 精确前缀才合并 | vendor `slime/agent/trajectory.py:180–191`：只有旧 builder token 全部成为新 prompt 前缀才是 CLEAN；非前缀若阈值为 0，`len(output_ids)<0` 永远不成立，必为 FORK。`:394–395` 同时禁用消息 rewrite-merge。 |
| 推理上下文不改 | vendor `slime/agent/adapters/common.py:341–344` 仍每轮重渲染并发送完整实际 prompt；本补丁没有改请求构造。 |
| 冻结与身份导出 | `adapters/slime/generate.py:2794–2812` 在正式链先经过已有 drain owner；`bringup.py:708–744` 再读同一 manager 的树根、阈值和 session 上限，随后调用真实 finish 与身份导出。不是两套独立默认值。 |
| 动作唯一归属 | vendor `trajectory.py:468–476` 用 `response_trained` 让共享前缀只训练一次；`turn_identity.py:149–225` 用同序 `claimed` 集合重放。`:298–311` 检查重放样本数及完整 tokens/mask 一致，`:314–328` 按 turn index 绑定 capture id。 |
| 回填真实凭据 | `bringup.py:647–663` 将每叶身份 span 转为 `LeafFacts`；`generate.py:2904–2941` 仅按该叶 capture id 获取 tape 并交给 `backfill_leaf_sample`。新行不会借用其他分支的生成凭据。 |
| 覆盖统计运输 | `bringup.py:740–755` 将同一统计 dict 附到每叶；`generate.py:2815–2817` 立即剥除并保存到 `RolloutAudit`，早于 poison、exit、capture 等后续判定。身份 span 的临时属性在完成装配后于 `:3009` 单独剥除。 |
| audit 落盘 | `generate.py:3760–3787` 调用既有 audit sink 并保留原失败语义；`bringup.py:1577–1581` 调用 writer，`:590–596` 写入统计并执行 flush/fsync。该统计没有新增训练判定分支。 |
| 转成 miles 样本 | `adapters/miles/generate_fn.py:172–194` 在编排返回后执行 canonicalize；`canonicalize.py:321–327` 继续拒绝未知属性，`:403–418` 复制 `index/group_index/rollout_id`、tokens、mask 与版本事实。没有为诊断字段扩白名单。 |
| member 与计权 | `group_admission.py:386–453` 将每个外层元素解释为一个 member，核同 member 各叶身份、载荷和 reward；`:484–506` 每 member 只记一次准入/reward。miles `train_data_conversion.py:209–216` 按 rollout_id 跨叶求 mask 总和；`:235–241,269–297` 在 prompt group 内按 rollout_id 去重 reward 后广播。 |

上表中的 rh2 文件均位于 `rh2/src/repoharness2/`，vendor 文件位于 `rh2/src/`，miles 消费文件位于 `reference/miles-rh2-integration/miles/ray/rollout/`。

并发与所有权方面，本补丁没有增加 await、线程、跨轮可变 owner 或恢复状态。树在原有排空屏障之后读取；统计使用函数局部集合与计数，临时属性只附在本 execution 的叶样本。未重审原有 drain owner 的完整实现。

## 3. `max_sample_tokens` 裁剪的生产可达性

`turn_identity.py:225` 在最终裁剪前把节点加入 `trained_ids`，而 `:233–242` 可以裁掉其 span。因此，直接给 manager 一个超出上限的非空 turn，确实能构造“统计已训练，但最终 span 不在”的 helper 反例；**不能仅凭该反例判当前生产会吞动作**。

当前真正安装的 capture wire 在 `rh2/src/repoharness2/adapters/slime/capture_wire.py:1046–1058` 保留了生成前上限：

1. `remaining = session.max_context_tokens - len(prompt_ids)`。
2. `remaining <= 0` 时返回空输出。
3. 否则将 `max_new_tokens` 压到不超过 remaining。

该 session 上限由 `generate.py:2723–2728` 传入，finish 包装与 vendor finish 使用同一值。阈值为 0 时，CLEAN/FORK 后的 builder 等于本轮实际 `prompt_ids + output_ids`（vendor `trajectory.py:193–214`）。在引擎遵守请求长度上限的前提下，每个非空响应的最终位置都不超过裁剪边界；末轮若只追加超限 prompt，其新增部分为 mask=0，裁剪不会删除已有动作。空输出的独立 FORK builder 不会交付，因为没有训练位。

因此裁剪前计数的问题应按条件性风险处置：需要引擎超预算返回、session 上限被中途改写，或未来新增绕过当前 capture wire 的入口。当前源码未显示后两种路径。本报告没有用 GPU 实测证明引擎绝不违反上限，也没有把它当成新增训练阻塞项。

## 4. 测试证据的真实范围

- `test_bringup_vendor_only.py:80–86` 验证真实 `BringupService` 构造出的 manager 为 0；其注释提到 finish 同源，但该用例没有实际调用 finish，同源关系由源码和下面的探针核实。
- 新 `test_i01_fork_wiring.py` 的八案使用真实 manager 与生产 `make_per_rollout_adapter`，底层会话生命周期是 stub；它验证 finish→身份→backfill，并直接调用 `take_turn_coverage`。它没有实际走 `_generate_attempt` 或 audit writer；这与 Brief §5(c) 的完整落盘表述有差距。
- `test_w1b_group_admission.py:538–557` 在 canonicalize 之后 deepcopy 一条 miles 叶，验证多叶准入与伪造拒绝。它能支持未改动的组准入语义，单独不能证明真实 FORK 和临时属性能经过 canonicalize。
- 既有 `test_vertical_slice.py:39–95` 覆盖 vendor fan-out→canonicalize→buffer→训练转换，明确断言共享 rollout_id、mask 分母与 reward。已有 consumer 测试与本批新 finish 测试互补；不能把它们描述为原先已经存在的一条完整 I01 端到端测试。

按主审分工，本角色没有重复运行其定向 pytest。为补上述新增运输接缝，独立执行了 [production_transport_probe.py](production_transport_probe.py)：

```bash
cd rh2
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/i01_b_impl_20260909/production_transport_probe.py
```

**实际结果：exit 0，全部断言通过。** 探针复用既有 W1b 的 prepared fixture、fake Docker、评分与排空屏障；替换为真实 `AnthropicAdapter(0)`、真实 BaseAdapter finish 和生产 per-rollout 包装，经过真实 formal orchestrator、audit writer、canonicalize、组准入/buffer 与训练转换。生成响应、消息脚本和 capture commit 绑定是合成输入，没有运行 HTTP 引擎。

主审已独立重跑，结果存于 [review_transport.json](review_transport.json)；本角色再次读取该 JSON，核对状态、rollout 身份及分母与独立运行一致。

| 观测 | 实际结果 |
|---|---|
| 两个 member 的训练行数 | `[2, 2]` |
| 每 member 行长 / 可训 token | `[22, 35]` / `[10, 8]` |
| 两条 execution audit | 各自 `turns_generated=turns_trained=2`，两种 dropped 均为 0，训练 token 总数 18 |
| 转换后 rollout_ids | `[0, 0, 1, 1]` |
| 转换后 rollout_mask_sums | `[18, 18, 18, 18]` |
| 转换后 raw_reward | `[1.0, 1.0, 0.0, 0.0]` |
| miles 临时属性 | 每叶均不含 `rh2_turn_coverage`、`rh2_turn_identity_spans`，metadata 也不含覆盖属性 |

日志只有该测试环境缺少 deep_ep/megatron 的既有 import 提示；没有把这些替身条件解释成真实训练环境验证。探针可作为本次审查证据，是否提升为常驻回归由实现者安排，不需要新增测试替身体系。

## 5. 适用维度与边界

| 维度 | 本角色处理 |
|---|---|
| A / D / G / H | 沿实际构造、冻结与消费路径核同源阈值、生命周期和身份；补 CPU 接缝验证。 |
| B / F | 核已批 B：保留动作、推理上下文不改、execution/member 不增；没有新拒绝策略。 |
| C | 没有新增临时挡板；0 为本批已批常量。 |
| E | 区分真实生产组件、stub 和直接 helper 调用，明确现有测试未覆盖的 audit 接缝。 |
| I | 以当前生产可达性裁决裁剪计数反例；不扩大到 I18/I19 或新的恢复设计。 |
| J / K | 重放继续直接使用 vendor `_SampleBuilder`；新增统计未重写第三份 drift 算法。未做风格审查。 |
| L | 新增局部集合与一次树扫描，没有新队列/后台任务；多行 GPU 成本未验证，仍属既定实机观测范围。 |
| M | 验证 audit 运输和训练面剥除；统计口径本身由 Falsifier/主审核查，本角色不宣称全部正确。 |
| N | 没有修改 vendor/miles 字节；独立探针使用当前集成基线。没有重审全部外部依赖契约。 |

## 6. 被审源码指纹

运行探针后重读的 SHA-256：

```text
bringup.py        edd55bfd2a76a6559d1819c3f9961917494c24e0fd4c04577629d4f15885e98b
generate.py       58a343b63cbd6068d1abd43714a12088f35ffc1ce26a29657244583e64e83eff
turn_identity.py  6530c61d4a85f6135f3f079bdf93acbe02d71e18b71499928354a8374891046b
test_i01_fork_wiring.py 7c1862a02a889d13d8d026775e7eb52b7438c06500e9f2ef72569bb9f72c9566
```
