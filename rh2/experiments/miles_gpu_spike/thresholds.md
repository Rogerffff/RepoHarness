# miles GPU spike 机器验收阈值（P0-6，单页事实源）

> 用途：`g1_acceptance.py judge` 的**唯一**阈值来源（脚本解析本页第一个 ```json
> 代码块；改阈值只改这里，不改脚本常量——避免双事实源）。
> 依据：tmp/codex_miles_gpu_spike_scope_recommendation_20260826.md §4 P0-6 与
> §5 G1（最小规模/数据形态/异步行为逐条抄录）；正控判据见同目录
> positive_control.md。
> 纪律：**不在租卡现场临时决定什么日志算通过**。租期内如确需调阈值（机型差异），
> 修改本页并在 `evidence/launch_facts.txt` 旁留 `thresholds_amended.md` 说明
> 改了什么、为什么——判定结果须注明使用的是修订版。

## 判定档位

- `PASS`：该项证据在场且满足阈值。
- `FAIL`：证据在场但不满足阈值。
- `MISSING_EVIDENCE`：证据缺失。**缺证据不算绿**——总判定只有全部检查 PASS 才是
  PASS；存在 MISSING_EVIDENCE 时总判定为 `INCOMPLETE`（不得记作通过）。
- `NOT_APPLICABLE`：按执行模式设计上不存在的观测面（当前只有 s1_compat 的
  finalization store 检查），如实标注、不冒充零、不影响总判定档位（租前审查
  PR-P0-3B：该项在 s1_compat 下不构成 F5 内存 pending draft 收口证据）。

## 阈值表（机器可读）

标 `calibrate` 的数值是租期开机后按机型校准的占位（校准动作 = 改本页 + 留痕），
其余为语义阈值，改动属 T0/T1 级决策，不是现场可调项。

```json
{
  "g1_min_rollouts": 3,
  "g1_min_applied_optimizer_steps": 2,
  "g1_sglang_engines_stable_across_steps": true,
  "g1_checkpoint_save_reload_delete": true,
  "g1_eval_smoke_post_train": true,
  "execution_mode_expected": "s1_compat",
  "pre_formal_note": "s1_compat 记 pre-formal，不翻正式闸门",

  "staleness_max_versions": 2,
  "weight_version_monotonic": true,
  "skipped_rollout_version_must_not_advance": true,
  "update_weights_interval": 1,
  "update_weights_interval_note": "publish 守恒的 interval 口径：launch 不带 --update-weights-interval（miles 默认 1）；改 launch 拓扑时必须同步改这里",

  "accepted_tokens_min_on_normal_step": 1,
  "token_accounting_must_balance": true,

  "logprob_same_version_mean_abs_diff_max": 0.05,
  "logprob_alignment_required": true,
  "logprob_same_version_note": "behavior(support-normalized) vs current(support-renorm) 同权重版本、loss_mask=1 训练 token 口径逐 token 均值绝对差上限；length_mismatch 一票 FAIL；同版本训练样本必须全覆盖；跨版本样本不进此对拍，calibrate",

  "routing_tape_dtype": "int32",
  "routing_tape_num_layers": 48,
  "routing_tape_topk": 8,
  "routing_tape_rows_offset": -1,
  "routing_tape_note": "shape=(len(tokens)-1, 48, 8)；R3=off 时字段必须缺席，且 trainer 侧 replay 事件必须缺席",

  "g1_min_multileaf_fanout_runs": 1,
  "g1_min_multileaf_fanout_runs_note": "聚焦修复批 #1：G1 数据形态的 fan-out 覆盖必须真实出现——训练批中 ≥N 个 agent run 拥有 ≥2 个不同 leaf_ordinal 的叶；全线性数据不算覆盖。leaf 唯一身份 = (sample_index, leaf_ordinal)（fan-out 叶继承同一 Sample.index，leaf_ordinal 由 miles convert/rollout_group 按同一扁平顺序计算）",

  "positive_control_instances": ["django__django-11099", "django__django-16139", "django__django-11133"],
  "positive_control_min_groups_with_reward_std": 1,
  "positive_control_must_be_consumed_by_applied_step": true,
  "positive_control_requires_accepted_tokens": true,
  "zero_variance_groups_must_not_train": true,

  "integration_tree_identity_required": true,
  "identity_required_role_prefixes": ["driver", "megatron_train_", "rollout_manager", "sglang_engine"],
  "identity_role_note": "聚焦修复批 #3：launch.sh 钉 broadcast 传输——SGLangServerActor（role=sglang_server）只在 RDT 分支创建，broadcast 下要求它必然假红。sglang_engine 由 SGLangEngine actor 在两种传输模式下都发（miles/backends/sglang_utils/sglang_engine.py init()）；若未来切 RDT，本列表按实际模式增补 sglang_server",

  "max_consecutive_zero_signal_steps": 8,

  "shutdown_orphan_workers_max": 0,
  "expected_dp_ranks": 2,
  "expected_dp_ranks_note": "6 actor GPU / (TP1*PP3*CP1) = dp 2；改拓扑时必须同步改这里（P0-8 rank 完整性判据）",
  "expected_trainer_global_ranks": 6,
  "expected_trainer_global_ranks_note": "run topology 声明的 trainer global rank census（= actor GPU 数 6）；replay fill/consume/exhausted 必须逐 (rollout, rank[, step]) 齐全（P0-5 聚焦复核：只查 rollout/step 级存在性会被部分 rank 缺失洗绿）；改 launch 拓扑必须同步改这里",

  "gpu_mem_peak_frac_max": 0.97,
  "gpu_mem_note": "calibrate：dmon 峰值/物理显存",
  "throughput_min_tokens_per_sec": 100,
  "throughput_note": "calibrate：steady-state 全局 token 吞吐下限，首开机实测后回填",
  "weight_update_seconds_max": 300,
  "weight_update_note": "calibrate：单次 broadcast 权重更新墙钟上限"
}
```

## 各键对应的检查（判定逻辑在 g1_acceptance.py，键名一一对应）

| 键 | 检查内容 | 证据来源 |
|---|---|---|
| `g1_min_rollouts` / `g1_min_applied_optimizer_steps` | ≥3 轮 rollout；≥2 个 `optimizer_step_applied=True` 的 step（独立事实：真实 optimizer.step() 执行成功；NORMAL 枚举不作 applied 证据——found-inf/debug 路径可为 NORMAL 而未更新；judge 另以 `optimizer_step_progress_consistent` 交叉验证 Adam/scheduler 前后计数） | step_records.jsonl（miles train_step 事件） |
| `train_step_global_rank_census` / `optimizer_state_continuity_per_rank` / `train_step_metrics_coverage` | 聚焦修复批 #2（trainer per-rank oracle，聚合面无法证明"所有 rank 的 optimizer 状态齐全且持续"）：① 每个 (rollout, step, attempt) 恰好覆盖全部 `expected_trainer_global_ranks`（缺失/额外 FAIL，重复由 collect 记 conflict），rank→DP/PP 映射跨 step 稳定、dp 覆盖 0..D-1（反例：删 rank5 全部 train_step 而保留 replay/consume，旧判定 PASS）；② 逐 rank 按真实 step 顺序 next.before==prev.after（Adam+scheduler 双链），applied 步 Adam 恰 +1、scheduler 恰 +`num_rollouts`（train_step 事件新字段；反例：每步 Adam 0→1、scheduler 0→32 模拟每步重建 optimizer——单步自洽但链断裂）；③ pp-last 各 dp 都必须携带 metrics 且逐 rank 一致（DP all-reduce 事实，不得只取第一条），applied 步 grad_norm（全 rank）与 metrics.loss（pp-last）在场且有限（反例：NaN loss/grad_norm） | collected/step_rank_records.jsonl（train_step 事件逐 rank 保留） |
| `leaf_identity` / `g1_min_multileaf_fanout_runs` | 聚焦修复批 #1：leaf 唯一身份 = (sample_index, leaf_ordinal)——slime fan-out 多叶继承同一 Sample.index，纯 index 口径把合法双叶判成"重复消费"（假红），digest multiset 又检不出两叶 tape 对调（假绿）。训练面任一事件（rollout_group/train_step_consumed/logprob_compare/sample_dis_accounting/replay_fill）缺 leaf 身份 → `leaf_identity` MISSING（INCOMPLETE）；`g1_fanout_multileaf_coverage`：训练批必须真实出现 ≥N 个多叶 run，全线性数据 FAIL | sample_records.jsonl + collect_report.json（leaf_identity_missing） |
| `g1_sglang_engines_stable_across_steps` | SGLang engine actor 身份集合跨 step 不变（引擎常驻，非每 step 重建）。P1-1 改名：rollout_workers 事件记录的是引擎 actor 身份，不是 fully-async producer task 的保温证据，键名如实描述证据对象 | step_records.jsonl `worker_ids`（rollout_workers 事件） |
| `g1_checkpoint_save_reload_delete` | checkpoint 保存并 reload 验证一次（P0-2：DCP `.metadata` 用 FileSystemReader 结构化反序列化，torch.load 读法对正常 checkpoint 必假红），随后删除（探针 ckpt 不作任何后续起点） | evidence/checkpoint_probe.json（postrun_probes.py checkpoint） |
| `g1_eval_smoke_post_train` | 训后 eval 冒烟必须绑定最后一轮 + 期望终版权重版本（P0-3A：train_async 默认先跑 rollout 0 的 pre-train eval，不绑定版本时可冒充训后 eval）；`run_identity`：verdict 绑定唯一 run（manifest/collect run_id 与 thresholds digest 三方一致，P0-1；聚焦修复批 #5：manifest 的 thresholds_sha256 **缺失/空/非法直接 FAIL**——阈值页无外部锚点不得声称三方一致） | collected/eval_smoke.json + publish 守恒推导的终版；evidence/run_manifest.json |
| `staleness_max_versions` | 每训练样本必须有完整版本事实（缺版本 FAIL，不豁免）；逐 turn 版本列表**逐项**验证存在、可解析、≤ current（聚焦复核 finding 3：`["1","99"]`+current=1 之类的 future/损坏项不得被 min 折叠隐藏），全部合法后才用最旧版本算 staleness，0 ≤ s ≤ N | sample_records.jsonl |
| `weight_version_spans_coverage`（V2，无阈值键，纯语义检查） | per-token 权重版本区间证据独立审计面（staleness 的 min-over-spans 修复由上行检查自身承担，本检查证明记账层没有丢失或改写引擎报告的区间）：任一训练样本带 spans 证据（引擎已证明支持）⇒ 每个样本都必须有——逐轮校验区间结构（缝隙/重叠/空或倒置区间/首 start≠0/相邻同版本/版本不可解析 = FAIL），展平版本序列与 `behavior_versions` **逐项相等**（跨更新 turn 只记单数末版本的低报形态必红），engine_spans 轮的区间覆盖 token 总数与 logprob_compare 的 loss_mask=1 训练 token 数交叉相等（行无对拍/长度错位时跳过交叉，由对拍检查负责）；全无 spans 证据 ⇒ 看更新窗口：存在 mid-run 权重前进（publish updates 中 rollout_id 非 None，bootstrap 豁免）= FAIL（single_version_only 无法排除 turn 内跨更新低报），无 mid-run 更新 = PASS（单版本记账合法窗口），publish 事实缺失 = MISSING_EVIDENCE。诚实边界：引擎自身漏报区间无法从事件层证伪，由 pin 的 sglang 侧测试覆盖（SGLANG_COMMIT=4e230c3d 已含 weight_versions.py） | sample_records.jsonl（rollout_group 事件 `weight_version_spans` 列，源头 = 引擎 `meta_info.weight_versions` 经 canonicalize 落 `Sample.metadata`）+ collected/publish_records.json（更新窗口判定） |
| `weight_version_monotonic` | 版本只前进；`skipped_rollout_version_must_not_advance`：全 SKIPPED 轮版本不变（F2 patch 0003 语义）；`update_weights_interval` + `weight_publish_conservation`（P0-6）：interval 内有 applied step ⇔ 恰一次 weight_update（版本 +1、链续接）⇔ 恰一次 weight_publish、零 skip；全 skipped ⇔ 恰一次 weight_publish_skipped、零 update/publish。聚焦复核 finding 2 收紧：bootstrap update（rollout_id=None）**有且唯一**；每个 interval 的 `update.version_before` 与发布后版本都必须与 train_rollout 的 trainer current 双向锚定（发布账本自洽、但与 trainer 版本两本账 = FAIL） | step_records.jsonl + collected/publish_records.json（weight_update / weight_publish / weight_publish_skipped 三类原始事实） |
| `accepted_tokens_min_on_normal_step` | NORMAL step 的 dis_accepted_tokens ≥ 1；`token_accounting_must_balance`：accepted+rejected == provenance | step_records.jsonl（train_step 事件 metrics） |
| `logprob_same_version_mean_abs_diff_max` | 同版本 behavior(support-normalized) vs current(support-renorm，trainer 复算) 对拍，**只统计 loss_mask=1 训练 token**；`logprob_alignment_required`（P0-8）：任何 length_mismatch 一票 FAIL、同版本训练样本必须全覆盖、masked token 总数 > 0 | sample_records.jsonl（logprob_compare 事件） |
| `routing_tape_*` | R3=on：逐训练批样本 shape/dtype/digest 记录且合形；R3=off：字段缺席且 trainer 侧 replay 事件缺席。`routing_replay_trainer_consumption` + `routing_replay_source_linkage`（P0-5）：replay_fill（stream 注册>0、record 数=期望 microbatch 数）、logprob 前向逐 microbatch pop、每 optimizer step forward/backward pop=该 step microbatch 数、rollout 末队列耗尽、trainer fill digest multiset == rollout tape digest multiset——source tape 运到门口不再单独作数。聚焦复核 finding 1 收紧：按 `expected_trainer_global_ranks`/`expected_dp_ranks` 建立预期 rank census，上述链逐 (rollout, global rank[, step]) 齐全（少一个 rank、少某 rank 的一个 step 都 FAIL）；rank→dp 映射自洽、dp 覆盖齐全。聚焦修复批 #1 再收紧：source linkage 由 digest multiset 升级为 **leaf_id→digest 精确联结**（fill 事件带 sample_indices+leaf_ordinals），两个 fan-out 叶 tape 对调（multiset 不变）必红；同 dp 组 PP/EP 副本的 leaf→digest 映射必须一致 | sample_records.jsonl + collected/replay_records.json |
| `positive_control_*` | 见 positive_control.md：指定 3 组中 ≥1 组 reward std>0，且该组全部样本被消费、≥1 样本进入 `optimizer_step_applied=True` 的 step（方差 ≠ 驱动更新）；`positive_control_requires_accepted_tokens`（P0-8）：正控组自身 accepted token > 0（共批 ≠ 归因，applied step 可能全由别的组驱动）；全等 reward 组必须走 filter 丢弃或 SKIPPED_ZERO_SIGNAL | sample_records.jsonl + step_records.jsonl（sample_dis_accounting 事件） |
| `integration_tree_identity_required` | 四类生产 role（`identity_required_role_prefixes`：driver/megatron_train_*/rollout_manager/**sglang_engine**）必须全部出现（P0-4：事件写失败只告警不停训，少 role = 无证据），expected digest 必须非空且来自审计 manifest（launch preflight 对 manifest `miles_source_tree_digest` + git expected_tree 双重核对，运行目标不许自我背书），全部一致。聚焦修复批 #3：sglang_engine 由 SGLangEngine actor 发（broadcast/RDT 两种传输模式都创建）；sglang_server 只在 RDT 分支存在，broadcast 启动下不作必需角色（见 `identity_role_note`） | evidence/actor_identity.json + integration_base_manifest.json |
| `max_consecutive_zero_signal_steps` | 熔断阈值与 custom_config.yaml 一致（配置漂移检测） | custom_config.yaml |
| `shutdown_orphan_workers_max` / `shutdown_finalization` / `queue_*` / `expected_dp_ranks` | 关停探针：docker/ray **查询失败显式 FAIL（无法观测 ≠ 观测为零，P0-3B）**，查询成功且孤儿=0 才 PASS；聚焦修复批 #4：孤儿容器面同时覆盖 rollout（rh2-rollout）与真实评分（rh2-grading）名前缀，并按本 run owner label `rh2.run_id=<run_id>` 精确归属（launch 传 --run-id；只查仍运行容器，`docker ps -a` 已退出未删容器留 P1）；finalization 在 s1_compat 如实 NOT_APPLICABLE（bringup 设计不建 store，不冒充零、不构成 F5 收口证据），fa_* 模式 store 必须在场且空。`queue_multiset_conservation`（P0-8 + 聚焦修复批 #1）：admitted **leaf** multiset == 消费 leaf multiset（少/多一个 FAIL；合法 fan-out 双叶不再假红，同一 leaf 双消费仍必红），filtered 按 sample_index 与训练/消费面不相交；`train_step_rank_coverage`：每 step 的 dp 分片 = 0..expected_dp_ranks-1 齐全 | evidence/shutdown_probe.json + step_records.jsonl + sample_records.jsonl |
| `gpu_mem_peak_frac_max` / `throughput_min_tokens_per_sec` / `weight_update_seconds_max` | 显存峰值/吞吐/权重更新时间（train_step 另带 `zero_signal_scan_seconds` 独立计时，P1-2——scan 开销单独可见，阈值留待 GPU 实验设计轮） | dmon CSV + train_step/weight_update 事件 |

## 拓扑登记（W10 / 决策包 D2+B v2 B-5b，2026-09-04：engine 数不再钉死）

不进上方 json 表（judge 没有对应消费键，加死键违反"新配置指认消费者"纪律），
但属于开机前须明确的拓扑事实：

- **rollout engine 数 = rollout 卡数 / per-engine 卡数，是普通启动配置**：launch.sh 读
  `RH2_SPIKE_ROLLOUT_GPUS_PER_ENGINE`（默认 2），preflight P11(d) 只做正整数 / 不超过
  rollout 卡数 / 整除检查。此前"钉死 1"是绕开 MilesRouter 忽略 X-SMG-Routing-Key
  （`/abort_request` 与版本探测逐请求最小负载错发）的临时限制，owner 裁定不得转为正式
  资格语义；两处缺口已由 W10 关闭：rh2 的 rid 级 abort 改为 router `/list_workers` 全部
  worker 广播（`engine_router_client.py`，绕过 router 选路），经 router 随机探测版本的路径
  删除（bringup `_observed_current_version` 只用引擎回包观测），publish 后版本收敛经
  engine actor 逐台核对（integration tree `RolloutManager.set_weight_version`，事件
  `engine_versions_after_publish`）。逐端点状态见 `router_targeting_audit.md` §0。
- **首训 engine 数由 GPU matched comparison 决定**（同 rollout 卡数的两种切法，如 4 卡
  1×TP4 vs 2×TP2）：sglang 推理 TP = per-engine 卡数，两种切法的吞吐 / 更新窗口 / 重算
  token 口径不同——`throughput_min_tokens_per_sec`、`weight_update_seconds_max` 等
  calibrate 组绑定 engine 拓扑，比较结论与所选拓扑一并留痕后再定阈值。
- 既有 `g1_sglang_engines_stable_across_steps` 判定不受影响（它断言 engine actor 身份
  集合跨 step 稳定，与 engine 数无关）；多 engine 下该集合为 N 元素，同样要求跨 step 不变。
  startup_evidence.json 的 `router_workers.count` 应等于 engine 数（W10 GPU 清单核对项）。
- 明确不做（首版）：dead-engine 自动恢复、`/remove_worker` 弹性回收、在线缩扩容、FT 自动
  恢复、会话粘滞路由；任一 engine 死亡 = 停当前 run，按 B-3 冷恢复重启。

## G1 最小规模摘录（范围建议 §5，供现场对照）

6+2 拓扑；n=8 组形态；≥3 轮 rollout；≥2 个真实 optimizer step；sglang 引擎跨
step 稳定；checkpoint 保存+reload 验证一次后删除；训后 eval 冒烟绑定末轮+终版；
`s1_compat` 必须记为 pre-formal，不翻正式闸门。数据形态须覆盖：正常线性多轮、
工具观察位单例 support、掉落轮、fan-out 多叶、非零 advantage 正控组、全零
advantage 拒绝/skip 对照、全单例 support 拒绝/skip 对照、dynamic filter 后
GBS 与组身份对账。
