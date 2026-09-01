#!/usr/bin/env bash
# W5a：launch 脚本 trap 用的 run-label 兜底清理 + 无残留检查（campaign supervisor 的全部替身）。
#
# 语义（就绪稿 §2.6 末段 / 06 计划 W5a 行）：训练进程正常或异常退出之后，按本 run 的
# 容器 label `rh2.run_id=<run_id>` 做**一次**有界兜底清理，再做**一次**"列出残留即失败"
# 的检查。没有常驻进程、不做授权判断、不写账本。两步的 JSON 报告落到 --out 目录：
#   <out>/run_residue_cleanup.json   清理动作（先记后删：被删的容器名/目录全部在案）
#   <out>/run_residue_check.json     清理后的残留检查（查询失败 ≠ 零残留，同样非零退出）
#
# 用法（launch.sh 侧的接线，一行）：
#   trap 'bash "$RH2/scripts/rh2_run_trap_cleanup.sh" "$RUN_ID" "$DOCKER_CLI_DIR/docker" "$EV" [tmp-glob ...]' EXIT
# 或在 post-run 段显式调用：
#   bash rh2/scripts/rh2_run_trap_cleanup.sh <run_id> <docker-bin> <out-dir> [tmp-glob ...]
#
# 退出码：0 = 清理成功且检查零残留；1 = 清理失败 / 仍有残留 / docker 查询失败；2 = 用法错误。
# 注意：本脚本只动带本 run label 的容器；没有 label 的旧容器（MILES_RH2_RUN_ID 未下发时
# 启动的）不在它的归属范围内——那是 postrun_probes.py shutdown 探针按名字前缀兜底的面。
set -uo pipefail

RUN_ID="${1:-}"
DOCKER_BIN="${2:-}"
OUT_DIR="${3:-}"
if [ -z "$RUN_ID" ] || [ -z "$DOCKER_BIN" ] || [ -z "$OUT_DIR" ]; then
  echo "用法: $0 <run_id> <docker-bin> <out-dir> [tmp-glob ...]" >&2
  exit 2
fi
shift 3
TMP_GLOB_ARGS=()
for g in "$@"; do
  TMP_GLOB_ARGS+=(--tmp-glob "$g")
done

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
RESIDUE_PY="$SCRIPT_DIR/../src/repoharness2/shutdown/run_residue.py"   # 纯 stdlib，按文件路径运行，不依赖 PYTHONPATH
PY="${RH2_PYTHON:-python3}"
mkdir -p "$OUT_DIR"

echo "[rh2-run-trap] cleanup run_id=${RUN_ID} docker=${DOCKER_BIN}"
"$PY" "$RESIDUE_PY" cleanup --run-id "$RUN_ID" --docker-bin "$DOCKER_BIN" \
  --out "$OUT_DIR/run_residue_cleanup.json" "${TMP_GLOB_ARGS[@]}"
CLEANUP_RC=$?
echo "[rh2-run-trap] cleanup rc=$CLEANUP_RC"

echo "[rh2-run-trap] check run_id=${RUN_ID}"
"$PY" "$RESIDUE_PY" check --run-id "$RUN_ID" --docker-bin "$DOCKER_BIN" \
  --out "$OUT_DIR/run_residue_check.json" "${TMP_GLOB_ARGS[@]}"
CHECK_RC=$?
echo "[rh2-run-trap] check rc=$CHECK_RC"

if [ "$CLEANUP_RC" -ne 0 ] || [ "$CHECK_RC" -ne 0 ]; then
  echo "[rh2-run-trap] FAIL: cleanup_rc=${CLEANUP_RC} check_rc=${CHECK_RC}（残留或查询失败，见 ${OUT_DIR}/run_residue_*.json）" >&2
  exit 1
fi
echo "[rh2-run-trap] OK: run ${RUN_ID} 无残留"
exit 0
