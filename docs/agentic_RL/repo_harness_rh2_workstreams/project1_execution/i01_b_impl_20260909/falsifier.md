# I01 B 补丁独立反证审查

日期：2026-09-09。角色：Falsifier。基线：`2a533b1f9b8e7cc8a9aca1a90b8ea1b32afb31f8` 加本次未提交补丁。只读核对三份生产补丁与新增测试；本报告和同目录 `falsifier_probe.py` 是本审查者唯一新增文件。未运行 Docker、GPU、付费服务，未改生产源码、被审测试或提交。

## 结论与停止条件

未证明 I01 B 新增了训练 token 重复、capture 错绑、样本拒绝或 execution/member 计权回归。真实 `AnthropicAdapter` 会话面与 `make_per_rollout_adapter` 包装的 CPU 探针确认：四轮共享前缀加消息改写产出三行，`c1`～`c4` 仍各回填一次；连续两次 token FORK 产出三行，三次动作也各训练一次。

确认两项当前生产可达的 **P2 观测口径问题**：成本字段不能泛化解释为 B 相对旧阈值的增量；共享前缀会重复报告同一个生成轮的 token FORK。另有一个裁剪后的覆盖计数缺口，但其反例违反当前真实生成预算，不升为当前阻塞。

**停止条件**：主审独立复现并裁决以下两项观测修正后，本角色的聚焦反证结束。建议在本批观测功能收口前处理两项 P2；不需要重开 B/C 实验、重审 I18/I19、修改 vendor 或引入第三份线性化。裁剪缺口登记即可；以后若加入独立于推理预算的训练裁剪上限，再将其纳入该变更的验收。

## F-01：成本字段把假设的末行基准写成了 B 路线成本增量

- **当前行为**：`turn_identity.py:268–270` 始终计算 `sum(row_tokens) - row_tokens[-1]`。`TurnCoverageSummary` 的说明（同文件 `99–100`）及 Owner Brief §3 把它解释为 B 相对“REALIGN 单行”的额外输入量。
- **违反的不变量**：新增行成本的解释应区分“相对保留末行的算术差”与“由阈值 1024 改成 0 造成的差”。当旧阈值本来就 FORK 时，旧路线不存在所声称的单行基准。这里公式本身没有算错，错在把条件成立时的解释推广到了所有 execution。
- **证据与反例**：两轮会话，第一轮 prompt 长 2、output 长 4；第二轮 prompt 长 7，在上一响应的偏移 2 处漂移，第二轮 output 长 **1024**。阈值 0 和 1024 均产出 `[6, 1031]`，总输入同为 **1037**，真实增量 **0**；新字段两种情况下都报告 **6**。`trajectory.py:189` 仅在新输出长度严格小于阈值时 REALIGN，故这不是罕见非法输入。探针输出键：`long_output_b`、`long_output_old_threshold`、`actual_b_delta_against_1024`。
- **生产可达性**：`production_reachable`。真实入口以 `bringup.py:905–908` 的阈值 0 构造 adapter；模型回复经 `common.py:344,384` 记录到 manager；finish 在 `bringup.py:740–755` 产出并携带统计。长度 1024 小于现有默认 `max_new_tokens=4096`；探针给定 cap=2000，全部轮均符合推理预算，也没有上下文收缩。无需新能力或异常引擎行为。CPU 探针直接代入 TurnRecord，未声称已测真实 CLI/GPU 频率。
- **影响与分期**：P2，建议本批观测收口前校正。训练行、mask、身份没有因此变化，但按该字段估计 B 的成本会系统性把既有 FORK 成本归给 B；多消息叶时末行还是树遍历顺序的结果，解释更弱。频率未知，不据此声称 GPU 成本规模。
- **位置**：`rh2/src/repoharness2/adapters/slime/turn_identity.py:99`、`:268`；`rh2/tests/adapters_miles/test_i01_fork_wiring.py:239`。
- **复现**：从仓库根运行 `rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/i01_b_impl_20260909/falsifier_probe.py`。
- **最小修正与验收**：优先明确字段只是“全部行相对末行的额外 token”，同步删除其代表旧阈值实际增量的说明，或删除冗余字段而保留逐行长度；不建议为此在线重放旧 manager。若坚持声称旧阈值差额，以上例必须为 0，并需处理消息树也随阈值变化的事实。测试应比较两种阈值的独立总输入，不能只复写当前求和式。

## F-02：共享前缀上的同一 token FORK 被每个后继叶重复记录

- **当前行为**：`turn_identity.py:153` 对每条 routing leaf 重放祖先链，在 `182–194` 无条件附加 FORK 事件。`claimed` 只防重复训练，不防重复记事件。
- **违反的不变量**：作为每 execution 的生成轮漂移事实，单个历史生成轮上的同一次漂移不应因后来多一片叶而变成两次。若有意记录每条叶链内部的重放分裂，则需明确该口径并携带足以区分叶链的字段，不能让两条完全相同的 `turn_index` 事件看起来像两次模型行为。
- **证据与反例**：四轮顺序执行；t2 的 prompt 在 t1 响应中 token 漂移；t3 正常扩展 t2；t4 的消息历史改写 t3，保留原 t3 叶并另开一叶。阈值 0 最终行长 `[6,12,15]`，mask 总量分别 `[4,4,2]`；`fork_events` 却含 **两条完全相同的 `turn_index=2`、偏移 2、前响应长 4、下轮输出长 2**。两条叶共同经过 t2，它只实际生成一次。探针输出键：`shared_prefix_token_fork_then_message_rewrite`。
- **生产可达性**：`production_reachable`。依赖的是 I01 已涵盖的 token drift 与消息 rewrite 两类既有输入按顺序出现，不需要 subagent、compaction、并发或 future I19；prompt 长度依次为 2、7、10、13，无收缩，cap=100。真实 manager 的 `trajectory.py:394–395` 在阈值 0 保留 rewrite 分枝，`456–476` 对每片叶重新走共享祖先；wrapper 随后执行同序统计。CPU 探针使用真实 manager、真实 finish 包装与 backfill；模型输出本身为人工给定。
- **影响与分期**：P2，建议本批观测收口前校正。会夸大 token 漂移次数，并使漂移率分母若采用 `turns_generated` 时前后口径不同；错误大小取决于后继叶数。**没有重复训练**：同一探针 `c1`～`c4` 均仅回填一次，`turns_generated=turns_trained=4` 正确。
- **位置**：`rh2/src/repoharness2/adapters/slime/turn_identity.py:153`、`:182`。
- **复现**：同 F-01 命令。
- **最小修正与验收**：若保留当前“生成轮漂移事实”语义，按当前树内 node/turn 身份只记一次即可，不需新 owner、状态机或拒绝路径。上述例应仅留一条 t2 事件，且 `[6,12,15]`、mask 与 capture 使用次数不变。再保留探针中的连续两个 FORK 用例，事件应依次为 t2、t3，防止过度去重。

## R-01：最终裁剪未反映到 turns_trained，但当前有效生成路径不触发

`turn_identity.py:225` 在 append 时加入 `trained_ids`；`233–242` 裁剪并丢弃空 span 后不更新它，`264` 因而仍统计裁剪前的训练轮。探针人为给 cap=7、第一轮长 6、第二轮 prompt 长 7 加非空 output 长 2，最终仅剩 c1 的 4 个训练 token，却报告 `turns_trained=2`。

这证明新 helper 的文字契约“最终训练行中的轮数”过宽，但不能证明当前正常训练丢轮未报。生产 `common.py:457–468` 在同一个 `max_context_tokens` 下生成：prompt 已达 cap 时直接返回空输出，否则限制 `max_new_tokens` 为剩余容量。B 的 CLEAN/FORK builder 对每轮最终持有的 token 正是该轮的 prompt+output；遵守引擎预算时，非空响应不能被同一个 cap 从中裁掉。故人工非空 t2 在真实请求面不会产生。

**标签**：当前反例为 `test_only`；引擎超额返回或未来新增独立训练裁剪预算才是 `conditional_future`。不作为本批 P0/P1 或拒绝路径理由。若以后修正，可由最终 surviving spans 派生轮数，并明确部分裁剪轮算“部分覆盖”还是“覆盖”；不应借此悄悄改变现有截断准入语义。位置：`turn_identity.py:225,233,264`。验收例：该人工裁剪输入保留的不同 capture 只有 c1，最终覆盖计数不得仍等于 2。

## 测试、成本和未发现问题的依据

- `rh2/.venv/bin/python .../falsifier_probe.py`：退出码 0；五次真实会话面组装均完成，确认以上反例及两组 capture 唯一性断言。没有调用 engine HTTP。
- 在 `rh2/` 运行 `.venv/bin/python -m pytest tests/adapters_miles/test_i01_fork_wiring.py -q`：**13 passed in 0.68s**，无 skip。这说明原新增测试在两个反例存在时仍全绿。其两轮八案没有“先 token drift、后 message rewrite”的共享历史；成本测试 `:239` 只是复写公式。新测试对 token/mask/capture 的断言有价值，不能因此否定整份测试。
- B 的两个销毁点确实关闭：`trajectory.py:189` 的 `len(output)<0` 不成立，`:394` 关闭消息 merge。连续两次 FORK 的独立探针核对了三轮各一次、可训 token 总量 8；本角色未发现新增身份重放偏差。未在此重审 miles loss 分母或组准入全链，交主审/对应角色负责。
- 观测计数新增的是局部集合、列表、一次树扫描及 FORK 时再次扫描公共前缀；没有长期 owner、异步任务或新异常守卫，也没有修改推理请求。`_common_prefix_len` 在每个 FORK 多算一次，`asdict` 在导出时复制少量统计；它们有 CPU 成本，但相对既有逐叶 token builder 重放没有提高复杂度阶。当前默认每 sid 25 轮（`bringup.py:229`），未测出或声称有吞吐退化；没有证据将此列为 hot-path 阻塞。
- 本角色重点覆盖 B/E/G/H/J/L/M；A 的训练 token 唯一性只覆盖上述确定性输入。安全边界、跨进程生命周期和下游训练分母不在本角色重复审查范围，不能把本报告当作全链验收。

本次没有提出新 T0；没有新增挡板；没有推翻 B 已批定案。R-01 是新观测计数未完整描述既有裁剪能力，不是本批新增裁剪行为。
