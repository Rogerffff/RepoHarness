# W1a 实现报告 · miles 路径 formal 六字段身份铸造

日期：2026-09-02。范围：计划 06 §3 W1a 行 + §1 D0-2（只做中立身份事实，不夹带任何 admission/loss/timeout/staleness 决定）。

## 0. 交付物一览

| 文件 | 性质 |
|---|---|
| `rh2/src/repoharness2/adapters/miles/identity.py` | 新增：六字段铸造模块（`mint_attempt_identity` + `stamp_identity_on_outputs`），零 miles/slime import |
| `rh2/src/repoharness2/adapters/miles/generate_fn.py` | 修改：`Rh2MilesGenerateFn.__call__` 接入铸造（80-84 行铸造、117-118 行输出盖章） |
| `rh2/src/repoharness2/adapters/miles/__init__.py` | 修改：导出身份符号 |
| `rh2/tests/adapters_miles/test_w1a_identity_minting.py` | 新增：铸造契约测试（27 例） |
| `rh2/tests/adapters_miles/test_w1a_formal_chain.py` | 新增：挡板以下真实 fa_formal 生产链验收（3 例） |

**未触碰**：`rh2/src/repoharness2/adapters/slime/generate.py`（2366-2378 强校验原样）、`rh2/src/slime/` vendored 代码、envpack/contracts/governance、reference/、`bringup.py:705` 挡板。无 git commit/stash。

## 1. 六字段来源表（铸造语义）

| 字段 | 来源 | 跨 retry | 对照旧链 |
|---|---|---|---|
| `rh2_prompt_group_id` | `f"miles_g{sample.group_index}"`（miles data_source 的组级单调计数器） | 稳定 | fa_bringup `fa_g{seq}`（进程内计数器）→ 改为样本组事实的确定性推导 |
| `rh2_group_index` | `sample.group_index` 原值 | 稳定 | fa_bringup 从 `payload.group_index` 读，同源 |
| `rh2_rollout_execution_id` | `f"{prompt_group_id}_m{slot}"` | 稳定（逻辑执行身份） | fa_bringup `{gid}_m{slot}` 同形制 |
| `rh2_member_slot` | `sample.index - sample.group_index * n_samples_per_prompt`，越界 fail-closed | 稳定 | fa_bringup 用组内枚举序；miles 路径单成员调用看不到组列表，改为算术推导 + 越界拒绝 |
| `rh2_physical_attempt_id` | `f"{execution_id}#p{seq}-{uuid8}"`，每次派发全新 | **必换新** | async_worker dispatch 铸造同形制 |
| `rh2_physical_attempt_seq` | metadata 里上一次 seq + 1（首次 = 1），历史损坏 fail-closed | **必换新（单调递增）** | async_worker 进程内 per-execution 计数器 → 改为 metadata 续铸（见 T1-3） |

推导算术的依据（已核实代码事实）：`reference/miles/miles/rollout/data_source.py` 组装配循环里 `sample_group_index`（每组 +1）与 `sample_index`（每样本 +1）同步递增、同存同取于 checkpoint state_dict，因此 stock 数据源上 `index == group_index * n + slot` 恒成立；`Sample.reset_for_retry()`（`miles/utils/types.py`）保留 identity 字段与 metadata，retry 后组/成员推导恒等、attempt 续铸有载体。

## 2. T1 决策及理由

1. **铸造点 = `Rh2MilesGenerateFn.__call__`（generate 边界），不建组级 submit 钩子。** miles 的组级 submit（`fully_async_rollout._submit_one_group`）是只读 miles 代码，rh2 在 miles 派发路径上唯一拥有的每 attempt 必经点就是 generate fn。组身份改为从样本自带组事实**确定性推导**——同组成员各自推导出相同组身份，与一次组级铸造等价，且天然跨 retry 稳定、无跨成员协调状态。
2. **铸造门控 = `execution_mode != "s1_compat"`，与 generate.py:2366-2378 的强校验同一门控。** s1_compat（含 config 缺失的老测试面）零行为改变；非 s1 模式（fa_audit_only/fa_formal）必铸造。这不放宽任何校验——只是让铸造面与消费面的适用范围逐字对齐。
3. **seq 续铸载体 = 样本 metadata，而不是进程内计数器。** miles 的 retry 路径（`_recycle` → `reset_for_retry` → 重新派发）保留 metadata，上一次 `rh2_physical_attempt_seq` 就是天然的 per-member 单调基准：新 seq = 旧 seq + 1。相比旧 async_worker 的进程内 dict（无界增长、进程重启归零），metadata 续铸无全局状态、可跨进程延续；attempt id 带 uuid8 后缀，即使 metadata 全丢导致 seq 从 1 重来，id 也不可能撞车。
4. **稳定四字段冲突 = fail-closed，不沿用 fa_bringup 的"系统字段覆写旧值"先例。** 旧链组身份出自进程内计数器，跨 batch 必然不同，覆写是常态；本实现的四字段是样本自身组事实的纯函数，跨 retry 恒等——metadata 已带不同值只可能是跨组错配/身份串样，静默覆写会掩盖结构性污染（与 W1b 三终态①的方向一致，但 W1a 只在铸造边界抛错，不定义准入语义）。
5. **round-trip 落点 = canonicalize 之后在 generate_fn 内统一盖章（`stamp_identity_on_outputs`），canonicalize.py 语义不动。** 已核实：vendor 叶链 metadata 由 `to_sample` 从 extra_metadata 重建（`rh2/src/slime/agent/trajectory.py:247`），输入样本的六字段**不会**自动传播到输出叶；由铸造结果统一回写是唯一不改 vendored 代码的无损路径。fan-out 各叶盖同一份身份（同 member 同 attempt 的分支）；叶上已带不同值（伪造独立 attempt/冒充新 member）fail-closed 拒绝整次交付。
6. **"token 内容匹配降级为校验断言"的落实方式**：身份传播完全走铸造字段（输入 metadata → generate.py 消费 → 输出盖章），不新增任何按 token/index 内容反推身份的路径；canonicalize 既有的 `index/group_index` 一致性检查与 backfill 的 token 锚定保留原语义——它们此后只承担"输出确属本次输入"的校验，不承担身份来源。W1a 未删除任何现存代码：核查确认 miles 适配层内本就没有以 token 内容做身份推断的实现（generate.py 的叶-轮内容匹配已在 F1 被身份 span 直取路径取代，属既有事实）。
7. **session capability 不复用的实现依据**：`generate.py:2301` 每次 generate 按当次 `physical_attempt_id` 调 `mint_session_capability`（128-bit 随机、每次全新）。W1a 保证每次派发 attempt id 必换新，internal sid（`s-{paid}`）随之隔离——formal 链测试断言两次 attempt 的 `audit.session_id` 不同。

## 3. 偏离说明

- 无对计划语义的偏离。一处实现层面的选择值得指出：`rh2_member_slot` 依赖 stock 数据源的 `index == group_index * n + slot` 算术。这不是新假设的引入，而是把隐含事实显式化并配 fail-closed（越界即拒），见开放问题 3。

## 4. 开放问题

1. **eval 路径的身份事实**（归 W8）：非 s1 模式下 `evaluation=True` 同样走铸造（E10 定案训练评测同链路）。若 eval 数据源给出的样本缺 `group_index/index`，铸造会 fail-closed 拒绝。W8 eval 运输链落地时需确认 eval 样本的组事实来源，或明确 eval 在该模式的身份口径。
2. **`prompt_group_id` 的唯一性作用域 = 单个训练 run/segment**：`group_index` 由 data_source state 决定，checkpoint 恢复时延续，但全新冷启动会从 0 重来，跨 run 撞名。这与旧 `fa_g{seq}`（进程内计数器）强度相同；跨 segment 全局身份按计划归 W5b 的 `(segment_id, numeric_version)` 复合身份，W1a 不越权设计。
3. **自定义数据源**：若未来引入不满足 index 算术的合法数据源（或 per-sample 组大小），`member_slot_underivable` 会把它整体拒掉——届时 slot 来源需要重新定义，因涉及组形状语义，建议按 T0 提决策包，不在铸造层静默放宽。
4. **seq 单调性依赖 metadata 存续**：进程崩溃且 metadata 丢失的冷路径下 seq 从 1 重来（attempt id 仍唯一）。"seq 全局单调"若未来被任何消费者依赖（目前无），需另行评估。

**T0 升级项：无。** 六字段键名与语义是 generate.py 既有事实（消费面已冻结），W1a 只补生产面，未触碰公共 schema/契约。

## 5. 测试证据（2026-09-02 实跑）

新增测试（30 例全绿）：

- `tests/adapters_miles/test_w1a_identity_minting.py`（27 例）：两级身份推导正例、同组成员组身份一致；身份事实缺失/异型、组大小缺失、metadata 不可写、slot 越界各负例；retry 经真实 `reset_for_retry` 换 attempt/seq 三连正例；attempt 历史损坏（半缺/非 int/0/bool）5 参数化负例；跨组错配冲突负例；fan-out 统一盖章正例 + 伪造 attempt/冒充 member 负例 + 残缺身份盖章负例；generate_fn 集成（铸造先于生成、round-trip 无损、retry、缺组大小 fail-closed、s1_compat 零写入）。
- `tests/adapters_miles/test_w1a_formal_chain.py`（3 例，**挡板以下真实 fa_formal 生产链**：真实 `RolloutOrchestrator`（execution_mode=fa_formal + 屏障 + finalization store + 单 owner drain）+ 真实 capture 钩子/backfill/评分收口/canonicalize，替身只在文档化注入点）：
  - 铸造身份使 `generate.py:2366-2378` 强校验真实通过——audit 零失败、九步走满、真实评分交付、Outcome v2 身份与铸造逐字同源、交付 miles 样本六字段 round-trip 无损；
  - retry 换新 attempt/seq/session（`audit.session_id` 隔离），member/trajectory 身份稳定；
  - 对照负例：同链路未铸造样本必然 `fa_identity_incomplete` fail-closed（不评分不交付）——证明强校验未被放宽，铸造是使其通过的唯一差异。

回归（全部通过）：

```
tests/adapters_miles/（默认 pin base reference/miles）        266 passed, 185 skipped
tests/adapters_miles/（RH2_MILES_PATH=miles-rh2-integration） 451 passed
tests/adapters/                                               307 passed
tests/ 其余全部目录                                            799 passed, 15 skipped
ruff check（全部改动文件）                                     All checks passed
```

integration base 451 全绿含 B2/F1 两条经 `Rh2MilesGenerateFn` 的既有 e2e 纵链（其配置默认 s1_compat，本改动对其零行为影响，实测确认）。
