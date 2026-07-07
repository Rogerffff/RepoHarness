# P3 8 卡预实验执行脚本包

协议实体化：`docs/agentic_RL/repo_harness_rh2_workstreams/preflight/8gpu_preflight_protocol.md`
（作业序列 J0~J5b）的"租到卡照单执行"脚本。所有脚本头部注释写明对应协议
条目与判据；slime 参数逐个对照 `reference/slime`（pin `e848052a`）源码，
参数核对差异记录在 `docs/.../preflight/implementation-notes.md`。

## 执行顺序（协议 §2，总时间盒 ≤ 24h 墙钟）

| 序 | 脚本 | 执行位置 | 时间盒 | 预期产物（`$P3_EV` 默认 `/root/preflight_evidence`） |
| --- | --- | --- | --- | --- |
| 1 | `j0_env_check.sh` | **host** | 计入 J0 2h | `j0/env_check.txt`、`j0/topo_m.txt`（topo -m 原文）、`j0/image_digest.txt`；P-7 内存分档 <400GB 直接 exit 2 红灯 |
| 2 | `j0_convert_weights.sh` | 容器 | 计入 J0 2h | `j0/weights_evidence.txt`（下载/转换墙钟 + 双路径声明）、`j0/hf_manifest.txt`、`j0/torch_dist_manifest.txt`、`j0/convert_model_args.txt`（MODEL_ARGS 展开值） |
| 3 | `j05_kernel_smoke.sh` | 容器 | 0.2h | `j05/j05_train.log`、`j05/j05_full_args.txt`；PASS/FAIL（FAIL = sm_120 红灯候选，别再烧 J1/J2） |
| 4 | `j1_nccl.sh` | 容器 | 0.7h | `j1/j1_bandwidth.csv`（3 原语 × 2/4/8 卡 × msg size）、`j1/<op>_<g>gpu.log` |
| 5 | `j2_sglang_30b.sh` | 容器 | 1h | `j2/j2_serving.csv`（tokens/s）、`j2/probe_32k.json`、`j2/mem_serving_*.txt`、`j2/engine_*.log` |
| 6 | `j3_matrix/run_j3.sh` | 容器 | 4h | `j3/j3_matrix.csv`（每格 step 墙钟/显存峰/tokens/s/OOM/内核报错）、`j3/<cell>/full_args.txt` + `train.log` + `dmon.csv` |
| 7 | `j4_full_step.sh` | 容器 | 3h | `j4/j4_assertions.json`（六项断言逐条）、`j4/j4_full_args.txt`、`j4/dmon_all.csv`、`j4/j4_train.log`、checkpoint 即弃声明 `j4/j4_assertions_acceptance.txt` |
| 8 | `j4b_topo_compare.sh` | 容器 | 2.5h | `j4b/j4b_topo.csv`（T3→T1→T2′ 每步墙钟 + 尾部空闲占比）、`j4b/<topo>/tail_idle.json` + `dmon.csv` + `train.log` |
| 9 | `j4c_fully_async_smoke.sh` | 容器 | 0.5h | `j4c/j4c_report.json`（ABORTED 三元组分类 + queue_size 曲线 + task 异常计数）、`j4c/probe_triples.jsonl` |
| 10 | `j5_weight_sync.sh` | 容器 | 1h | `j5/j5_update_weights.csv`（两档 buffer）、`j5/buf_*/update_weights.json` + `dmon.csv`；`J5_COLOCATE=1` 附加 t1 offload/onload 曲线 |
| J5b | `lib/m1_staleness_hist.py` / `lib/m2_mismatch_collect.py` | 容器（分析段） | 并入 J3/J4 | `m1_report.json`（staleness 直方图 + turn/版本边界对齐）、`m2_report.json`（失配指标） |
| J6 | 人工汇总 | — | 不占机时 | `preflight_report.md`（§5 模板骨架，机器可先退租） |

执行纪律（协议 §4）：每作业独立日志 + 配置 dump；失败不修不猜，记录后按
矩阵继续；J1~J3 合成数据，J4 才碰真实链路。

## 静态验证（本地无 GPU）

- 全部脚本 `bash -n` 通过；全部脚本支持 `--dry-run`（打印完整解析后的
  命令与参数，不执行任何 GPU/docker/网络动作）。
- `cd rh2 && uv run pytest tests/check_p3_scripts.py -q`：
  slime flag 逐个能在 `reference/slime` 源码/官方脚本里 grep 到、
  A1~A5 并行乘积 = 卡数、E2 flags 与实验设计定案一致、J4c 防误用断言在场。

## 约定（写新脚本时必须遵守）

1. 传给 slime 的 CLI flag 一律放在 `*_ARGS=( ... )` bash 数组里；
   非 slime 命令（sglang.launch_server / nccl-tests / docker）的 flag
   不得进 `*_ARGS`（静态核对靠这个约定区分）。
2. 一切外部动作走 `common.sh` 的 `p3_run` / `p3_run_sh`，保证 `--dry-run`
   干净；兼容 bash 3.2（本地 macOS 校验）。
3. 30B 训练脚本必须 `source scripts/models/qwen3-30B-A3B.sh` 并把
   MODEL_ARGS 展开值 dump 进 evidence（J3 附①）。

## J5b 分析段用法示例

```bash
# M1（J4 跑完后）：staleness 直方图 + 轮间/单轮内部跨版本对齐
python3 lib/m1_staleness_hist.py \
  --dumps-dir /root/preflight_j4/rollout_dumps \
  --events /root/preflight_j4/artifacts/bringup_events.jsonl \
  --out $P3_EV/j5b/m1_report.json

# M2（J4 已开 --get-mismatch-metrics）：训推 logprob 失配
python3 lib/m2_mismatch_collect.py \
  --log $P3_EV/j4/j4_train.log \
  --dumps-dir /root/preflight_j4/rollout_dumps \
  --out $P3_EV/j5b/m2_report.json
```

## 结果回填（协议 §7）

跑完把 `j3_matrix.csv` 最优行 + `j4_assertions.json` + `j4b_topo.csv` 汇进
`preflight_report.md`（§5 骨架），按 §3 判绿/黄/红灯，回填实验设计 E6/C3
与 final_review 的 U-C 关闭记录。
