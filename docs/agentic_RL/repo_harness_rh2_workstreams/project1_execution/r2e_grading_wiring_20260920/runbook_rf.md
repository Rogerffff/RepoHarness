# R2E 真机对账（R-f）runbook

2026-09-23，Claude（B 线）。配套：[R2E 接线计划](../r2e_grading_wiring_20260920.md) §5.2 / §11.4；[Codex 本机复核 §8](../r2e_local_review_20260922/README.md)。机器地址、密钥路径只在 `CLAUDE.local.md` / `tmp/API.md`（git-ignore），本文不写。

## 0. 前提

- 本机切片（R-0…R-e）已通过 Codex 复核；派生镜像配方 `rh2/scripts/r2e_derive/recipe_v1.sh` 与构建 / 复核工具 `rh2/scripts/build_r2e_derived.py` 已在本机（Apple Silicon，amd64 仿真）对 coveragepy `016af5f6`、pillow `3ac9396e`（自定义 runner）、aiohttp `240da100`（脏树 3 个已跟踪改动）各建一张并跑通 noop / gold（计划 §11.4）。
- 机器：x86_64 CPU Docker 机，≥ 16 vCPU / ≥ 32 GB / **200 GB 即够**（来源镜像 75.9 GB + 派生层 ≤ 25 GB（解释器副本 + gc 后的新 pack，典型 0.25 GB/题、最坏 0.65 GB/题）+ 评分期临时可写层 ≤ 10 GB（每个容器因 `chown -R /testbed` 涨 0.35–2.3 GB，用完即删）+ 系统 / venv / 证据 ~10 GB ≈ 120 GB 最坏；不需要额外 volume）。开机第一步核 `df -h /` 与 `docker info | grep "Docker Root Dir"`，确认 Docker data-root 在这块 200 GB 盘上。spot 机器：每批任务结束把账本 / eval_logs / artifacts / overlays.jsonl / 逐题 facts.json rsync 回本机（账本追加写，回收后按未完成的 task_id 续跑）；"no stop" 机器跑完即终止。默认 overlay2；**不开 metacopy**，先记录 `cat /sys/module/overlay/parameters/metacopy` 与 `docker info` 的存储驱动（构建工具会记进 results.json）。
- 代码快照：R2E 文件**尚未提交**，`codex/environment-pipeline-20260922` 分支也不含它们；必须从本工作区按清单同步并核 sha256。

## 1. 同步代码与输入（本机 → 机器）

```bash
# 本机：生成清单（仓库根执行；-c 校验内容而不是 mtime）
cd <repo>
find rh2/src rh2/scripts rh2/tests rh2/pyproject.toml rh2/uv.lock \
     docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e \
     -type f -not -path '*/__pycache__/*' -not -path '*/.pytest_cache/*' -print0 \
  | LC_ALL=C sort -z | xargs -0 shasum -a 256 > /tmp/r2e_snapshot.sha256
rsync -azc --delete --exclude __pycache__ --exclude .pytest_cache --exclude .venv \
      rh2/ <machine>:/work/code/rh2/
rsync -azc --delete docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ <machine>:/work/code/docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/
scp /tmp/r2e_snapshot.sha256 <machine>:/work/code/
# 机器：逐文件核对——直接看 sha256sum -c 的退出状态（非 0 = 有 FAILED / 缺文件，不能开工）
cd /work/code && sha256sum --quiet -c r2e_snapshot.sha256 && echo SNAPSHOT_OK
cd /work/code/rh2 && uv sync --locked
```

R2E 的可信加载只读 `s2_r2e/`（pins → 四项输入 → 提交记录 → 四个数据文件），不需要 `s2/`、`data_freeze/`。
机器烟测只跑不依赖 SWE 材料的用例（`test_ingest_r2e_subset.py` 里有两例读真实 SWE 材料，全新机器缺 `s2/` 时会失败，那不是 R2E 加载回归；SWE 不变性留完整工作区验证）：

```bash
.venv/bin/python -m pytest tests/envpack/test_ingest_r2e_subset.py -q -k test_real_48_tasks_load_through_the_trusted_entry
.venv/bin/python -m pytest tests/envpack/test_r2e_parsers.py -q     # 336 份全量对拍那例在机器上没有 runs/ 会 skip，属预期
```

## 2. 派生镜像（DR3）

```bash
cd /work/code/rh2
# 先代表题（覆盖：纯 pytest、xvfb、自定义入口、脏树、期望含 ERROR/FAILED、gold=0 的两题）
.venv/bin/python scripts/build_r2e_derived.py --repo-root /work/code --out-dir /work/r2e_derived \
  --task-ids coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae,pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605,aiohttp__240da100151933883d7dea0528d45877df025b92,orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b4237,pandas__19c5eea5db0046276bfc0eef8a67febf090eeaaf,datalad__58ba5165234cb16de0e8463ee75097362099835f
# 全量
.venv/bin/python scripts/build_r2e_derived.py --repo-root /work/code --out-dir /work/r2e_derived --all
```

每题：按 manifest digest 拉来源镜像 → `docker build --network=none`（`FROM <ref>@<digest>`）→ 宿主侧 21 项复核（导层完整性逐文件 sha256、隐藏测试树摘要 == 评分面、run_tests.sh 摘要、HEAD == base_commit、git 清理、两种 uid 的解释器 / 私有目录不可读、driver 预检脚本）。全过才进 `overlays.jsonl`；失败的题看 `<out>/<iid>/facts.json` 的 `failures` 与 `build.log`。`overlays.jsonl` 按目录下全部 `facts.json` 汇总——**同一输出目录同一时刻只跑一个构建进程**（工具有目录锁 `.build.lock`，锁在场即拒绝启动）；串行多次调用同一目录安全。本次 R-f 用一个 `--all` 进程串行建。

## 3. 对账运行

```bash
cd /work/code/rh2
.venv/bin/python scripts/replay_grade.py prepare --repo-root /work/code --out-dir /work/replay/prepared_r2e --private-dir /work/replay/private_r2e --sources r2e_gym_subset
.venv/bin/python scripts/replay_grade.py export-gold --ingest-dir /work/code/docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest \
  --instance-ids <逗号分隔 48 个 instance_id> --out-dir /work/replay/gold_r2e
# 代表题 → 48 题；noop 与 gold 分开账本；--task-ids 可用裸 instance_id
MILES_RH2_RUN_ID=r2e-rf-noop-$(date +%Y%m%d) .venv/bin/python scripts/replay_grade.py run \
  --prepared-summary /work/replay/prepared_r2e/replay_summary.json --image-overlays /work/r2e_derived/overlays.jsonl \
  --task-ids <…> --candidate noop --eval-log-dir /work/replay/eval_logs_r2e --artifacts-dir /work/replay/artifacts_r2e \
  --ledger /work/replay/ledger_r2e_noop.jsonl
MILES_RH2_RUN_ID=r2e-rf-gold-$(date +%Y%m%d) .venv/bin/python scripts/replay_grade.py run ... --candidate gold-dir:/work/replay/gold_r2e --ledger /work/replay/ledger_r2e_gold.jsonl
```

收尾摘要 `final_status.exit_code`：0 正常；2 停批（基线契约矛盾 / grader scope 无法确认终止，账本行仍带已落盘的日志 / sidecar 引用）；3 收口时仍有未关评分容器；4 driver 带未捕获异常 / 取消退出——此时**进程本身**仍以 traceback 退出（shell 退出码 1），4 只出现在 JSON 摘要里。没有覆盖条目的 R2E 题会被预检①拦下（`stage_error=r2e_preflight:…`），不评分。

## 4. 逐键对账

```bash
.venv/bin/python scripts/reconcile_r2e.py --repo-root /work/code --ledger /work/replay/ledger_r2e_noop.jsonl --ledger /work/replay/ledger_r2e_gold.jsonl \
  --m3-root /work/reference/M3 --old-root /work/reference/env_probe_20260909_ledger --out /work/replay/reconcile_r2e
```

两侧原始日志都用同一套固定规则重新解析，逐题比较观测映射与相对期望的 missing / unexpected / mismatched；`agree` 要求 reward 相同、三个差异集合逐条相同、且观测状态映射逐键相同。靶子：noop 48 个 0；gold 46 个 1，coveragepy `016af5f6` 与 datalad `58ba5165` 保持 0（来源缺陷，DR4 不修）。分歧只登记原因，不改 expected。参考语料（M3 的 `facts/<c12>/noop_x2`、`gold_ledger/logs_r2e`；09-09 的 `ledger/logs_r2e`）从本机 `runs/` 同步到机器上的 `/work/reference/`。

## 5. 错误对照（一题）

同一题、同 image ID 与脚本摘要：① 用成功行构造临时资格（`--qualification-ledger` 指向本批 gold 账本），候选改成语法错误 → 期望 `candidate_execution_failed / 0`；② 不给资格 → 期望 `failed_to_grade / test_log_parse_failed / None`；③ 人为超时（`--grading-deadline-seconds` 小于测试耗时）→ infra / None，`log.partial=true`、`test.segment_completed=false`，容器清理干净。临时资格只用于本次机制验证，不冒充流水线资格。

## 6. 记录与交接

- 逐题耗时：账本 `phases`（grader 六段）与候选阶段；两侧初始化 / census / 测试 / 清理耗时和可写层增长（`docker system df` 前后）——据此定整批资源与期限，不按 M3 的测试中位 9 s 推。
- 交接内容：代码快照清单摘要、机器 / Docker / 存储事实（`results.json.host`）、配方与 overlay（`overlays.jsonl` + 逐题 `facts.json`）、账本与 sidecar / 日志引用、reconcile 结果、成本与最终清理事实。区分"按来源一致""环境资格""题目质量""actor 可用"，不合并成一个通过标签。
- 结束前 `docker ps -a` 无 `rh2-*` 容器；证据 rsync 回本机 `runs/r2e_rf_<date>/`。

## 7. 09-23 实跑后的备注

- 远端后台进程一律 `systemd-run --unit=<名> --collect --working-directory=/work/code/rh2 --setenv=MILES_RH2_RUN_ID=… -p StandardOutput=append:<log> -p StandardError=append:<log> <绝对路径命令>`；不要在 ssh 里 `nohup … &`（ssh 会被挂住；`a && b && cmd &` 会把整段放进子 shell，后续命令的 cwd 不对）。等待时用 `systemctl is-active <unit>`，不要 `pgrep -f`（会匹配到自己）。
- Docker 29 默认 containerd 镜像存储：磁盘占用约为 `docker inspect Size` 合计的 1.6 倍（48 来源 + 48 派生 = 128 GB）。
- 本次重建派生镜像换了 image ID（缓存全命中、config 摘要不变，变的是 OCI index / attestation manifest 的摘要，containerd 存储下 `.Id` 即 index digest）；覆盖表以最后一次构建为准，旧 ID 的资格行随之失效——错误对照要用同一次构建产出的 noop/gold 行。始终以目标机器实际 inspect 的 ID 为准，不假设别的构建器 / 存储也如此。
- 逐题资源：numpy `2f4a9650` 的 `test_big_arrays` 在默认 `/tmp` 1 GiB tmpfs 下 OSError；**已验证配置 `/tmp` 6 GiB + 内存 12 GiB**（`RH2_GRADER_TMP_TMPFS_BYTES=6442450944 RH2_GRADER_MEMORY_BYTES=12884901888`），最小充分配置待流水线测量（两个副本合计略大于 4 GiB，内存峰值约 4.3 GiB）；其余 47 题默认 profile 即可。
- 实测：两进程并行 96 次尝试 92 min（每进程约 1.9 min/次尝试）；可信 setup 段（含 `chown -R /testbed`，计的是整段而非孤立的 chown）占 grader 时间约 59–90%，orange3 最慢（grader 中位 153 s、setup 136 s）。
