#!/bin/bash
# GPU 利用率/显存 1s 采样（P-6 独立工具；j*.sh 内部走 common.sh 的
# p3_dmon_start/p3_dmon_stop，本文件供手工/screen 里长跑用）。
#
# 口径与 lib/tail_idle.py 的输入契约一致：
#   timestamp, index, utilization.gpu [%], memory.used [MiB], memory.total [MiB]
#
# 用法：bash dmon_sample.sh <输出csv> [gpu列表如 4,5,6,7] [--dry-run]
set -eo pipefail

OUT="${1:?用法: dmon_sample.sh <输出csv> [gpu列表] [--dry-run]}"
GPUS="${2:-}"
ID_ARG=""
if [ -n "${GPUS}" ] && [ "${GPUS}" != "--dry-run" ]; then ID_ARG="-i ${GPUS}"; fi

CMD="nvidia-smi --query-gpu=timestamp,index,utilization.gpu,memory.used,memory.total --format=csv,nounits -l 1 ${ID_ARG}"
echo "+ ${CMD} > ${OUT}"
for a in "$@"; do
  if [ "$a" = "--dry-run" ]; then exit 0; fi
done
mkdir -p "$(dirname "${OUT}")"
exec ${CMD} > "${OUT}"
