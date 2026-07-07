# slime fully_async 升级设计（四缺口实现分析 + 机制知识沉淀）

日期：2026-07-08。定位：P3 预注册升级档（分离 + fully_async + 自建三件）的**实现设计文档**——只分析不写代码；同时把三轮 slime 源码调研的机制知识持久化（此前散在对话与 task 输出中，易失）。触发条件不变：J4b 或首训实测 rollout 尾部空闲 > 每步墙钟 25%。

所有 `file:line` 相对 `reference/slime/`，基于 pin `e848052a`；上游影响见 §2。

## 0. 结论先行

```text
1. 升级可行，总工作量 ~7-9 人日（不含真续跑；含真续跑 12-16 人日），
   四缺口中三个可落我方 adapter 层或极轻 core 改动。
2. 反转性发现：README "starts over" 对标准 generate 路径不准确——
   token 级续跑静态可证会生效（reuse_existing_input_ids 链）；但我们的
   custom_generate 完全绕过该机制，续跑与否由我方代码决定。
   缺口① = 在我方 custom_generate 写 resume 分支，不是等上游。
3. 缺口①升级为正确性问题：starts-over 有系统性长度偏置
   （短轨迹更易在权重更新间隔内完成——DeepSeek-V4 不变量的 slime 版）。
   过渡方案 = starts-over + 丢弃（配自动补采），杜绝纯 starts-over。
4. 新发现一个隐性 bug 风险：fully_async worker 的 task 崩溃时样本
   静默泄漏（不进 queue 也不回 buffer），长训练累积后某些 prompt
   永不被训——升级时必须兜底。
```

## 1. slime 异步机制知识汇总（三轮调研沉淀，file:line 为证）

```text
放置与档位：
  --colocate 强制同步（train_async.py:11 断言禁 colocate）；
  分离放置一等公民（--rollout-num-gpus 独立指定，arguments.py:1858-1894；
  引擎数 = rollout_num_gpus ÷ per-engine TP，须整除，http_utils.py:201-210）。
train_async 双缓冲时序（train_async.py）：
  :31 预启下一轮 generate → :34 等上一轮 → :38 先启下一轮 → :49 训当前 →
  :65-69 按 interval 先 drain 再 update_weights（"防止更新发生在生成中途"）。
  结构性 staleness ≈ 1 × update_weights_interval。
fully_async worker（rollout/fully_async_rollout.py）：
  进程级单例（:49/:56-62），后台线程 + 独立 asyncio loop（:115-167）；
  max_concurrent = sglang_server_concurrency × 引擎数（:59）；
  loop = reap（:126-133）+ top-up get_samples(1)（:136-152）+ 1s poll（:154）；
  ABORTED 组整组回 data_buffer（done_cb :183-188），正常组进 output_queue
  （maxsize=1000，阻塞式 put，:85/:189）；消费侧收满 batch 即返（:194-248）；
  worker 不参与 abort/pause——权重更新对它透明，靠引擎侧兜底；
  eval 模式直接 raise（:254-255）。
权重更新（update_weight/*.py）：
  统一时序 pause_generation → flush_cache → 发权重（带 weight_version）→
  continue_generation（tensor 路径 :156-190；distributed 路径 :110-133）；
  colocate=CUDA IPC，分离=NCCL 跨 PG broadcast；
  --update-weight-buffer-size 默认 512MB（arguments.py:515，MoE 关键旋钮）。
版本记账：
  Sample.weight_versions: list（types.py:120），每次 append_response_tokens
  收到 finish_reason 记一条（:381-382）——粒度 = 一次 /generate 一段，
  非 per-token；全仓无任何下游消费（mask/准入都要新写）；
  _convert_samples_to_train_data 不透传（ray/rollout.py:735）→
  采集必须在 projection 层（S1 交接 H-1 已定）。
  current version 在 rollout 侧唯一来源 = engine.get_weight_version
  （sglang_engine.py:363-369）；训练侧 weight_updater.weight_version
  不跨进程可见。
partial rollout（标准路径专属，sglang_rollout.py）：
  abort 收集 + start_rollout_id 标记（:357-368）→ 回灌 buffer（:637-639）；
  重入时 reuse_existing_input_ids（:46-60）token 级续跑；
  mask-offpolicy 在 generate_and_rm 入口把旧 response loss_mask 清零（:231-232）；
  组完整性由 add_samples 断言保证（data_source.py:206-209）。
动态采样（标准路径专属）：
  dynamic_filter + over_sampling 全在 generate_rollout_async（:394-440）；
  fully_async 路径零调用（静默失效）。
buffer_filter 插入点：
  data_source.py:172-175 注册、:195 调用——注意调用时 rollout_id 传 None，
  默认 pop_first（:225-229）。
```

## 2. 上游动态（pin e848052a → origin/main 领先 8 commit，2026-07-08 fetch）

| commit | 影响 | 处置 |
| --- | --- | --- |
| **680824dd** `routed_experts_start_len` | **高**：routing tape 支持中段偏移拼接（`expected_rows = len(tokens)-1-start_len` + `torch.cat` 中段拼接，types.py:352-369）——**续跑场景的 tape 基建**，也改变 tape 归一化契约 | ① S1-3 的 tape 归一化留 start_len 扩展位（现在留位一行事）；② 若做真续跑必须 cherry-pick |
| **c7487788** `--release-train` | **中**：新增每步 update_weights 分支（train_async.py:39-69）——若启用，缺口②的跨版本盲区急剧恶化 | 升级档明确不默认启用；若用，TIS 兜底从建议变必须 |
| **2d909df5** cleanup | 排雷项：删 ppo_utils.py 63 行等 | 升级 rebase 前精读 diff 确认未删依赖 API |
| 474861aa /pull_weights、f27ef35c source_names、3× docker patch | 低/无 | 记录即可 |

F6 纪律的第一个真实案例：pin 之后上游确实在动我们的契约面，升级必须走契约测试先行。

## 3. 四缺口实现设计

### 缺口① partial 续接（正确性问题，非纯吞吐）

**新确证**：ABORTED 组回收全程不重置状态（done_cb `:183-186` → add_samples → pop_first 原样弹回，tokens/status/loss_mask 保留）；标准 generate 路径重入**确定真续跑**（`generate_and_rm:235` 不短路 ABORTED + `generate:162` 允许入场 + `reuse_existing_input_ids:46-60`）；**custom_generate 路径完全绕过**（`:251-259` 直接 dispatch）——我们的 SWE agent 是否续跑由我方代码决定，最坏组合是"带旧 token 但 agent 重开沙箱从头跑"（旧 token 悬挂）。

**长度偏置评估**（starts-over 系统性偏短：短轨迹更易在更新间隔内完成，长尾饥饿 + stale 污染）：

| 选项 | 偏置 | 结论 |
| --- | --- | --- |
| 真续跑 | 近无偏 | 最优但最贵：需缺口② mask 配合 + **沙箱中间态恢复**（token 续跑对沙箱 agent 意味着 checkpoint/restore workspace，代价可能高于重跑） |
| starts-over（现状） | 最差 | 尽快废弃 |
| **starts-over + 丢弃**（不回收，直接放弃该组，靠补采补组） | 中性偏短但无 stale 污染、无重算浪费 | **推荐过渡方案**（~0.5 人日，复用缺口③的 drop 机制） |

正式接线（若长轨迹占比证明必要）：我方 custom_generate 开头加 resume 分支（判 `status==ABORTED ∧ tokens ∧ metadata.start_rollout_id`，30-80 行 + agent 中间态序列化）+ done_cb 补 start_rollout_id 标记（~5 行碰 core）+ cherry-pick 680824dd。

### 缺口② mask-offpolicy 盲区

**物理根因确证**：weight_version 每段记一条、无 token 级边界（types.py:381-382）——单次 generate 内的 pause/continue 跨版本边界在 meta_info 里不存在，token 级 mask 需 SGLang patch（不现实）。

**但对我们的多轮 SWE agent 有一个关键利好**：每轮 = 一次 /generate = 一次 append = 一条 weight_versions 记录，**段边界我方 custom_generate 完全掌握** → **turn 级版本感知 mask 在 projection 层可行**（~50-100 行，零碰 core），盲区收窄到"单轮内部跨版本"。

**推荐组合**：turn 级版本 mask（我方 projection，覆盖主要场景）+ TIS 兜底单轮内部（slime 有 `--use-tis`，arguments.py:1047；E2 定案已预留"M2 失配大则开"钩子）+ 版本跨度超阈值整轨迹硬丢弃（buffer_filter，~20-40 行）。**前置验证**：实测跨版本 token 比例（J5b-M1 的直方图正是此数）。

### 缺口③ 动态采样失效

**关键确证：补采在 fully_async 下天然成立**——worker top-up 的 `get_samples(1)` 在 buffer 空时自动落到全局 prompt 数据集读新组（data_source.py:177-189），drop 不会饥饿。

**推荐**：done_cb 内接 dynamic_filter，drop 的组不 put queue（类比 ABORTED 回收路径，~30-50 行碰 core 但语义精确复刻原生 over-sample→drop→补采）。custom_generate 组内自否决可作补充，buffer_filter 消费侧过滤（只丢不补）不推荐。

### 缺口④ staleness 准入

**关键障碍确证**：buffer_filter 调用时 `rollout_id=None`（data_source.py:195）且拿不到 engine 句柄——**current policy version 无现成管道**。两个方案：(i) worker top-up 时缓存 `engine.get_weight_version`（~20 行碰 worker）；(ii) 用 buffer 内最大版本近似 current（零管道但偏旧）。推荐 (i)。

准入形态：`staleness_filter`（我方 `--buffer-filter-path`，~40-80 行）——`cur - max(weight_versions) ≤ α`（α=1，RollArt 实证），被拒**丢弃**（依赖缺口③补采），不回收重跑（踩缺口①循环）。

## 4. 未注意点（四缺口清单外，本轮新扫出）

```text
N1 task 崩溃样本静默泄漏（重要）：done_cb 里 task 异常只 log 后 return
   （fully_async_rollout.py:172-175），样本不进 queue 也不回 buffer——
   长训练累积后部分 prompt 永不被训。升级时 done_cb 必须加异常兜底
   （回收进 buffer 或至少计数告警）。可考虑给 slime 上游提 issue。
N2 output_queue 阻塞死锁点：put 是阻塞式（:189），消费侧长时间不 drain
   → worker 线程卡死在 put → reap/top-up 全停。监控 queue_size。
N3 worker 1s poll（:154）：SWE 分钟级任务可忽略；升级档若混短任务
   需降到 50-100ms 或事件驱动。
N4 eval 干扰：eval 走标准同步路径不受 fully_async raise 影响（主判据
   评测安全），但 eval 与后台 worker 共享引擎与全局 semaphore
   （sglang_rollout.py:95 SingletonMeta）——eval 时延会被后台 rollout
   干扰，正确性无损；评测配置严禁误配 fully_async rollout function。
N5 组完整性不变量：add_samples 断言组长（data_source.py:206-209）——
   未来任何 sample 级（非组级）过滤都会破坏它，过滤一律组级。
N6 worker 崩溃恢复：线程死亡会重建（:56），但 in-flight 与 buffer 内
   回收样本随旧 event loop 丢失——长训练需外层对账（prompt 覆盖率审计）。
```

## 5. 触发升级后的实施顺序与工作量

```text
0. 验证轮（0.5-1 人日，J4c 扩展执行）：
   custom_generate 对 ABORTED 的实际行为 / 跨版本 token 比例 /
   TIS 配置现状 / worker 补采速率
1. 缺口③ done_cb dynamic_filter（1-1.5 人日，碰 core 极轻）
2. 缺口① 过渡态 starts-over+丢弃（0.5 人日，复用 ③ 的 drop）
3. 缺口② turn 级版本 mask + TIS 开关（1-2 人日，主要在我方 projection）
4. 缺口④ staleness 准入 + worker 版本缓存管道（1-2 人日）
5. N1 泄漏兜底 + N2 监控（1 人日）
—— 至此 ~7-9 人日，升级档可用 ——
6. （可选）缺口① 真续跑：cherry-pick 680824dd + resume 分支 +
   沙箱中间态恢复（2-5 人日，高不确定；仅当长轨迹占比实证必要）
```

必须实验验证（静态不可判）：custom_generate ABORTED 行为、训练侧 TIS 现状、跨版本 token 比例（release-train 下尤甚）、worker 补采速率 vs drop 率、engine.get_weight_version 调用开销、N1 泄漏实际发生率。

## 6. 对当前阶段的三条即时影响（不等升级触发）

```text
I-1 S1-3 tape 归一化留 routed_experts_start_len 扩展位（上游 680824dd
    已改契约；现在留位一行事，随 §8/H 系列交接给执行线）。
I-2 J4c 判定口径可以更精确了：标准路径续跑已静态确证，J4c 的真正
    未知只剩"我方 custom_generate 对 ABORTED 的行为"——验证点收窄为
    在 custom_generate 入口打点 sample.status / len(tokens) /
    response_length 三元组。
I-3 首训监控加一项：queue_size 与 task 异常计数（N1/N2 是双缓冲档
    也可能间接暴露的问题面，监控成本一行）。
```
