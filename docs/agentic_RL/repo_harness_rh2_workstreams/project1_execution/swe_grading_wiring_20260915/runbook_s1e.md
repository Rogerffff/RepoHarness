# S1-e 机器运行手册（冒烟 e1 → 代表批 e2）

前提：用户重新开机/重租 CPU 机器（C4）；凭据只从 `project1_execution/tmp/API.md` 读取；机器地址放本机 `CLAUDE.local.md`，不进本文。以下路径沿用昨夜布局 `/work/{data,code,ledger,logs,secrets}`，新增 `/work/replay`。

## 0. 同步代码与数据（本机 → 机器）

```bash
# 本机：同步 rh2（源码、脚本、tests/envpack/data 的 oracle 与语料、uv.lock、requirements-replay.lock）、整个 s2/（ingest 四面产物、
# raw 3.5 MB 原始行、image_manifest_keyed.json、vendor）与 data_freeze/；tests/envpack 与 test_vendor_specs 都会读这些文件（R2）。不同步 runs/、tmp/
rsync -az --delete --exclude '.venv' --exclude '__pycache__' rh2/ root@<box>:/work/code/rh2/
rsync -az --delete docs/agentic_RL/repo_harness_rh2_workstreams/s2/ root@<box>:/work/code/docs/agentic_RL/repo_harness_rh2_workstreams/s2/
rsync -az --delete docs/agentic_RL/repo_harness_rh2_workstreams/data_freeze/ root@<box>:/work/code/docs/agentic_RL/repo_harness_rh2_workstreams/data_freeze/
```

机器上建 rh2 运行环境，**按锁文件复现本机已测环境**（R2）：`rh2/uv.lock` 固定全部版本，`[tool.uv.sources]` 把 `verifiers`
钉在 commit `5885ab9c54152e707af2a11797aa52c3eb1752da`；`pip --group` 只按范围解析、不读锁文件，因此不用它。

```bash
pip install -U uv                                   # 或 curl -LsSf https://astral.sh/uv/install.sh | sh
cd /work/code/rh2 && uv sync --locked --group swe --group dev    # 在 rh2/.venv 里精确复现 uv.lock（含 verifiers 的 Git pin）
PY=/work/code/rh2/.venv/bin/python
# 没有 uv 时的备选：本机 `uv export --frozen --no-hashes --no-emit-project --group swe --group dev` 导出的 requirements-replay.lock
#   python3.12 -m venv /work/code/rh2/.venv && $PY -m pip install -r requirements-replay.lock && $PY -m pip install -e . --no-deps
$PY -c "import importlib.metadata as m; print(m.version('swebench'), m.version('verifiers'))"   # 期望 swebench 4.1.0
cd /work/code/rh2 && $PY -m pytest tests/envpack/test_vendor_specs.py tests/envpack/test_swegym_parsers.py -q   # 零 Docker 自检
```

下文所有 `$PY` 一律改用 `$PY`。

`TrustedTaskController.from_repo_root` 需要仓库根下的 `docs/.../s2/ingest` 与 `data_freeze`，所以 `--repo-root /work/code`。

## 1. 受信准备与 gold 导出（一次）

```bash
cd /work/code/rh2
$PY scripts/replay_grade.py prepare --repo-root /work/code \
  --out-dir /work/replay/prepared_e1 --private-dir /work/replay/private_e1 \
  --task-ids swe_gym_lite::python__mypy-12741,swe_gym_lite::conan-io__conan-13326,swe_gym_lite::iterative__dvc-5822,swe_gym_lite::pandas-dev__pandas-48106
$PY scripts/replay_grade.py export-gold \
  --ingest-dir /work/code/docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest \
  --instance-ids python__mypy-12741,conan-io__conan-13326,iterative__dvc-5822,pandas-dev__pandas-48106 \
  --out-dir /work/replay/gold
```

`prepare` 不覆盖已有目录：重跑换目录名。

## 2. 冒烟 e1（4 题 × gold/noop）

```bash
export MILES_RH2_RUN_ID=replay-e1-$(date +%Y%m%d)
export RH2_GRADER_SHM_BYTES=67108864          # 默认 64 MiB；MONAI-763 对照时改 1073741824
# 候选可写前缀默认 /opt/miniconda3/envs/testbed（D3=A）；显式设空串 = 不交出任何前缀
for cand in noop gold-dir:/work/replay/gold; do
  $PY scripts/replay_grade.py run --prepared-summary /work/replay/prepared_e1/replay_summary.json \
    --candidate "$cand" --repeat 1 --candidate-stage-seconds 900 --grading-deadline-seconds 3600 \
    --eval-log-dir /work/replay/eval_logs --artifacts-dir /work/replay/artifacts --ledger /work/replay/ledger_e1.jsonl
done
```

镜像首次拉取由 driver 在候选阶段之前完成（`--image-pull-seconds`，默认 1800 s，独立预算，不消耗候选阶段预算）；也可先手动 `docker pull` 四个镜像。pandas 重编译约 700 s（旧条件），安装段与测试段共用 `test_timeout_seconds`（1800 s，A2），超时会以 infra 记录、保留部分日志并在归因里注明 `candidate_phase=install|test`；e1 要按 sidecar 的 install/test 秒数核对 1800 s 是否够。

每题看四样东西：账本行（`report.outcome`、`candidate.apply_method`、`install.install_rc_last_command`、`observations.RH2_OBS_IMPORT_PATH`、`runner_integrity_changed`）、`eval_logs/<ref>.eval.log`、`eval_logs/<ref>.diagnostics.json`、`artifacts/<task>/a1-*/`。

e1 通过标准（进入 e2 前）：
- 4 题 noop → `unresolved/tests_failed`，gold → `resolved`（pandas-48106 gold 预期 NO：参考 ID 脆弱，账本 `verdict_diagnostics.reference_missing` 非空）；
- `install.install_rc_last_command` 为 0 且 `RH2_OBS_IMPORT_PATH` 在 `/testbed` 下；pandas 的 `RH2_OBS_PKG_VERSION` 带 `.dirty`；
- `control_surface.WRITABLE_PREFIXES_DONE=1`；conda 前缀 chown 耗时（`phases.grader_trusted_setup`）记录下来；
- `runner_integrity_changed` 为 false（gold/noop 不该改运行器）。

## 3. 代表批 e2

按接线页 §6.4：A 组 9 题 gold/noop ×2，B 组 24 条候选（`--candidate patch-dir:/work/replay/cc_patches`，先从 `env_probe_20260909/ledger/cc_patches/` 同步），C 组反例逐题。D4 派生镜像见 `derived_images/README.md`，用 `--derived-image <ref> --derived-image-recipe <说明>`。并发：先单路；账本按 `run_id` 分文件。

## 4. 回传与对账

```bash
rsync -az root@<box>:/work/replay/ledger_*.jsonl runs/swe_grading_wiring_20260915/ledger/
rsync -az root@<box>:/work/replay/eval_logs/ runs/swe_grading_wiring_20260915/eval_logs/      # 含 *.diagnostics.json
rsync -az root@<box>:/work/replay/artifacts/ runs/swe_grading_wiring_20260915/artifacts/      # frozen_patch / baseline / projection / classification
```

若 `run` 因候选容器无法确认清理而停止（退出码 2，账本 `candidate_container_cleanup_failed`），先在机器上 `docker ps -a --filter label=rh2.run_id=<run_id>` 处理残留，再继续。

对账脚本（待写）：rh2 账本 × 昨夜 oracle 账本（原组/投影组分开）→ `reconcile.md`。
