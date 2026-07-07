#!/bin/bash
# P3 预实验公共库（被所有 j*.sh source，不单独执行）。
#
# 对应协议：docs/agentic_RL/repo_harness_rh2_workstreams/preflight/8gpu_preflight_protocol.md
#   - §4 执行纪律：每作业独立日志 + 配置 dump；失败不修不猜，记录后继续。
#   - P-6：nvidia-smi/dmon 采样脚本备好（p3_dmon_start/p3_dmon_stop）。
#
# 约定（tests/check_p3_scripts.py 的静态断言依赖这些约定）：
#   1. 所有传给 slime（train.py / train_async.py / convert 工具）的 CLI flag，
#      一律写在名字以 _ARGS 结尾的 bash 数组里（例如 GRPO_ARGS=(...)）。
#      非 slime 命令（sglang.launch_server、nccl-tests、docker 等）的 flag
#      不得放进 *_ARGS 数组，避免静态核对误报。
#   2. 每个脚本支持 --dry-run：打印完整解析后的命令与参数，不执行任何
#      需要 GPU/docker/网络 的动作。实现方式 = 一切外部动作都过 p3_run。
#   3. 兼容 bash 3.2（macOS 本地静态验证）：不用关联数组、不用 ${var,,}。
set -eo pipefail

# ---------------------------------------------------------------- dry-run 解析
P3_DRY_RUN=0
for _p3_arg in "$@"; do
  case "${_p3_arg}" in
    --dry-run) P3_DRY_RUN=1 ;;
  esac
done
export P3_DRY_RUN

# ---------------------------------------------------------------- 路径约定
# evidence 目录（协议 §4：所有脚本与判据版本进 evidence 目录）。
# 真机默认 /root/preflight_evidence；本地 dry-run 可用 P3_EV 覆盖。
P3_EV=${P3_EV:-/root/preflight_evidence}
# slime 仓库在 pin 镜像内的位置（与 s1_7a_bringup 相同）。
P3_SLIME=${P3_SLIME:-/root/slime}
P3_MEGATRON=${P3_MEGATRON:-/root/Megatron-LM}
# rh2 仓库挂载点（host_launch.sh 把 rh2/ 挂到 /workspace/rh2）。
P3_RH2=${P3_RH2:-/workspace/rh2}
# 30B 模型双路径（协议 P-3：rollout 侧 HF，训练侧 torch_dist 转换产物）。
P3_MODEL_HF=${P3_MODEL_HF:-/root/models/Qwen3-30B-A3B}
P3_MODEL_DIST=${P3_MODEL_DIST:-/root/models/Qwen3-30B-A3B_torch_dist}
P3_MODEL_SCRIPT=${P3_MODEL_SCRIPT:-qwen3-30B-A3B.sh}
# 镜像 pin（协议 P-1 / P-9，S1-0 产物，与 s1_7a_bringup/host_launch.sh 一致）。
P3_IMAGE_PIN="slimerl/slime@sha256:a7317182c71d35712ee4edc86a5d1c313dc969efdf0026d339673299c186ea75"

# ---------------------------------------------------------------- 执行封装
p3_banner() {
  echo ""
  echo "================================================================"
  echo "== $*"
  echo "================================================================"
}

# p3_run <cmd...>：dry-run 时只打印，不执行；实跑时打印并执行。
p3_run() {
  echo "+ $*"
  if [ "${P3_DRY_RUN}" -eq 0 ]; then
    "$@"
  fi
}

# p3_run_sh '<shell pipeline>'：带管道/重定向的命令用这个。
p3_run_sh() {
  echo "+ $*"
  if [ "${P3_DRY_RUN}" -eq 0 ]; then
    bash -c "$*"
  fi
}

# p3_dump_args <文件> <数组元素...>：把解析后的参数逐行 dump 进 evidence
# （协议 J3 附①：在 evidence 中 dump 展开后的 MODEL_ARGS；J3 主轴 A：
# 每个组合的启动配置必须完整写出）。dry-run 时 dump 到 stdout。
p3_dump_args() {
  _p3_dump_file="$1"; shift
  if [ "${P3_DRY_RUN}" -eq 0 ]; then
    mkdir -p "$(dirname "${_p3_dump_file}")"
    printf '%s\n' "$@" > "${_p3_dump_file}"
    echo "[p3] args dumped -> ${_p3_dump_file}"
  else
    echo "[p3][dry-run] args dump (${_p3_dump_file}):"
    printf '    %s\n' "$@"
  fi
}

# p3_csv_append <csv文件> <header行> <数据行>：首次写入时补 header。
p3_csv_append() {
  _p3_csv="$1"; _p3_header="$2"; _p3_row="$3"
  if [ "${P3_DRY_RUN}" -eq 0 ]; then
    mkdir -p "$(dirname "${_p3_csv}")"
    if [ ! -f "${_p3_csv}" ]; then echo "${_p3_header}" > "${_p3_csv}"; fi
    echo "${_p3_row}" >> "${_p3_csv}"
  else
    echo "[p3][dry-run] csv append -> ${_p3_csv}: ${_p3_row}"
  fi
}

# ---------------------------------------------------------------- dmon 采样（P-6）
# p3_dmon_start <输出csv> [gpu列表如 0,1,2,3]：后台 1s 采样 GPU 利用率与显存。
# 口径：协议"rollout 尾部空闲占比"定义指明 nvidia-smi dmon 1s 采样；
# 这里统一用 --query-gpu 轮询（字段名稳定、带 ISO 时间戳，方便 lib/tail_idle.py 解析）。
p3_dmon_start() {
  _p3_dmon_out="$1"; _p3_dmon_gpus="${2:-}"
  _p3_dmon_id_arg=""
  if [ -n "${_p3_dmon_gpus}" ]; then _p3_dmon_id_arg="-i ${_p3_dmon_gpus}"; fi
  echo "+ [background] nvidia-smi --query-gpu=timestamp,index,utilization.gpu,memory.used,memory.total --format=csv -l 1 ${_p3_dmon_id_arg} > ${_p3_dmon_out}"
  if [ "${P3_DRY_RUN}" -eq 0 ]; then
    mkdir -p "$(dirname "${_p3_dmon_out}")"
    # shellcheck disable=SC2086
    nvidia-smi --query-gpu=timestamp,index,utilization.gpu,memory.used,memory.total \
      --format=csv,nounits -l 1 ${_p3_dmon_id_arg} > "${_p3_dmon_out}" 2>/dev/null &
    P3_DMON_PID=$!
    echo "[p3] dmon pid=${P3_DMON_PID}"
  fi
}

p3_dmon_stop() {
  echo "+ kill dmon (pid=${P3_DMON_PID:-none})"
  if [ "${P3_DRY_RUN}" -eq 0 ] && [ -n "${P3_DMON_PID:-}" ]; then
    kill "${P3_DMON_PID}" 2>/dev/null || true
    P3_DMON_PID=""
  fi
}

# ---------------------------------------------------------------- ray 生命周期
p3_ray_restart() {
  _p3_num_gpus="$1"
  p3_run_sh "ray stop --force || true"
  p3_run_sh "pkill -9 sglang || true"
  p3_run_sh "sleep 2"
  export MASTER_ADDR=${MASTER_ADDR:-127.0.0.1}
  p3_run ray start --head --node-ip-address "${MASTER_ADDR}" --num-gpus "${_p3_num_gpus}" \
    --disable-usage-stats --dashboard-host=0.0.0.0 --dashboard-port=8265
}

# ---------------------------------------------------------------- 结果解析辅助
# p3_grep_oom <日志>：返回 0 表示日志里有 OOM 痕迹。
p3_grep_oom() {
  grep -qiE "out of memory|CUDA error: out of memory|OutOfMemoryError" "$1" 2>/dev/null
}
