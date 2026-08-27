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

## 阈值表（机器可读）

标 `calibrate` 的数值是租期开机后按机型校准的占位（校准动作 = 改本页 + 留痕），
其余为语义阈值，改动属 T0/T1 级决策，不是现场可调项。

```json
{
  "g1_min_rollouts": 3,
  "g1_min_applied_optimizer_steps": 2,
  "g1_worker_warm_across_steps": true,
  "g1_checkpoint_save_reload_delete": true,
  "g1_eval_smoke_after_worker_stop": true,
  "execution_mode_expected": "s1_compat",
  "pre_formal_note": "s1_compat 记 pre-formal，不翻正式闸门",

  "staleness_max_versions": 2,
  "weight_version_monotonic": true,
  "skipped_rollout_version_must_not_advance": true,

  "accepted_tokens_min_on_normal_step": 1,
  "token_accounting_must_balance": true,

  "logprob_same_version_mean_abs_diff_max": 0.05,
  "logprob_same_version_note": "behavior(support-normalized) vs current(support-renorm) 同权重版本逐 token 均值绝对差上限；跨版本样本不进此对拍，calibrate",

  "routing_tape_dtype": "int32",
  "routing_tape_num_layers": 48,
  "routing_tape_topk": 8,
  "routing_tape_rows_offset": -1,
  "routing_tape_note": "shape=(len(tokens)-1, 48, 8)；R3=off 时字段必须缺席",

  "positive_control_instances": ["django__django-11099", "django__django-16139", "django__django-11133"],
  "positive_control_min_groups_with_reward_std": 1,
  "zero_variance_groups_must_not_train": true,

  "max_consecutive_zero_signal_steps": 8,

  "shutdown_orphan_workers_max": 0,
  "unfinalized_deliveries_max": 0,
  "queue_duplicate_sample_ids_max": 0,

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
| `g1_min_rollouts` / `g1_min_applied_optimizer_steps` | ≥3 轮 rollout；≥2 个真实 applied optimizer step（SKIPPED_ZERO_SIGNAL 不计入 applied） | step_records.jsonl |
| `g1_worker_warm_across_steps` | rollout worker/actor 标识跨 step 不变（常驻，非每 step 重建） | step_records.jsonl `worker_ids` |
| `g1_checkpoint_save_reload_delete` | checkpoint 保存并 reload 验证一次，随后删除（探针 ckpt 不作任何后续起点） | evidence/checkpoint_probe.json（人工/脚本落盘） |
| `g1_eval_smoke_after_worker_stop` | worker 停止后 before/after eval 路径冒烟一次 | evidence/eval_smoke.json |
| `staleness_max_versions` | 每样本 behavior version 与 current version 差 ≤ N | sample_records.jsonl |
| `weight_version_monotonic` | 版本只前进；`skipped_rollout_version_must_not_advance`：全 SKIPPED 轮版本不变（F2 patch 0003 语义） | step_records.jsonl |
| `accepted_tokens_min_on_normal_step` | NORMAL step 的 dis_accepted_tokens ≥ 1；`token_accounting_must_balance`：accepted+rejected == provenance | step_records.jsonl（train.log 抽取） |
| `logprob_same_version_mean_abs_diff_max` | 同版本 behavior/support/current 对拍摘要 | sample_records.jsonl |
| `routing_tape_*` | R3=on：逐样本 shape/dtype/digest 记录且合形；R3=off：字段缺席 | sample_records.jsonl（rollout dumps 抽取） |
| `positive_control_*` | 见 positive_control.md：指定 3 组中 ≥1 组 reward std>0；全等 reward 组必须走 filter 丢弃或 SKIPPED_ZERO_SIGNAL，不得进入 applied step | sample_records.jsonl + step_records.jsonl |
| `max_consecutive_zero_signal_steps` | 熔断阈值与 custom_config.yaml 一致（配置漂移检测） | custom_config.yaml |
| `shutdown_*` / `unfinalized_*` / `queue_*` | 关停后无孤儿 worker/未终结交付/重复消费 | evidence/shutdown_probe.json + step_records.jsonl |
| `gpu_mem_peak_frac_max` / `throughput_min_tokens_per_sec` / `weight_update_seconds_max` | 显存峰值/吞吐/权重更新时间 | dmon CSV + step_records.jsonl |

## G1 最小规模摘录（范围建议 §5，供现场对照）

6+2 拓扑；n=8 组形态；≥3 轮 rollout；≥2 个真实 optimizer step；worker 跨 step
保温；checkpoint 保存+reload 验证一次后删除；worker 停止后 eval 路径冒烟；
`s1_compat` 必须记为 pre-formal，不翻正式闸门。数据形态须覆盖：正常线性多轮、
工具观察位单例 support、掉落轮、fan-out 多叶、非零 advantage 正控组、全零
advantage 拒绝/skip 对照、全单例 support 拒绝/skip 对照、dynamic filter 后
GBS 与组身份对账。
