#!/bin/bash
# J0.5 训练内核最小冒烟（slime pin 容器内执行，单卡，时间盒 0.2h）。
#
# 对应协议条目（preflight/8gpu_preflight_protocol.md J0.5）：
#   把"Megatron 在 sm_120 一票否决"这个 U-C 核心疑点前置——镜像内单卡跑
#   tiny dense 模型 1 个 train step，避免 J1/J2 的 1.5h 白烧。
# 判据：train step 完成、日志出现有限 grad norm、无内核报错（sm_120 不可用
#   会在 gemm/attention/optimizer 内核处直接炸）。失败 = 红灯候选
#   （协议 §3："Megatron 在 sm_120 有不可绕过的内核缺陷"）。
#
# 实现：tiny dense 默认 Qwen3-0.6B（下载 <2GB，转换单卡秒级），用
#   --debug-train-only + 合成 rollout（lib/make_synth_rollout.py，不带 MoE
#   routing tape——dense 模型）纯训练侧过一个 step，完全不起 SGLang。
#
# 用法：bash j05_kernel_smoke.sh [--dry-run]
#   环境变量：J05_MODEL_HF / J05_MODEL_SCRIPT 可切到已就位的 Qwen3-4B（7a 遗产）。
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
. "${SCRIPT_DIR}/common.sh"

EV="${P3_EV}/j05"
J05_MODEL_HF=${J05_MODEL_HF:-/root/models/Qwen3-0.6B}
J05_MODEL_DIST=${J05_MODEL_DIST:-${J05_MODEL_HF}_torch_dist}
J05_MODEL_SCRIPT=${J05_MODEL_SCRIPT:-qwen3-0.6B.sh}
SYNTH="${EV}/synth_tiny_{rollout_id}.pt"
LOG="${EV}/j05_train.log"

p3_banner "J0.5 kernel smoke: ${J05_MODEL_HF} (script=${J05_MODEL_SCRIPT})"

# ---------------------------------------------------------------- 权重就位 + 转换（单卡）
if [ "${P3_DRY_RUN}" -eq 0 ]; then
  mkdir -p "${EV}"
  if [ ! -d "${J05_MODEL_HF}" ]; then
    hf download "Qwen/$(basename "${J05_MODEL_HF}")" --local-dir "${J05_MODEL_HF}"
  fi
  if [ ! -f "${J05_MODEL_DIST}/.p3_converted" ]; then
    cd "${P3_SLIME}"
    # shellcheck disable=SC1090
    source "scripts/models/${J05_MODEL_SCRIPT}"
    PYTHONPATH="${P3_SLIME}:${P3_MEGATRON}" python tools/convert_hf_to_torch_dist.py \
      "${MODEL_ARGS[@]}" --hf-checkpoint "${J05_MODEL_HF}" --save "${J05_MODEL_DIST}"
    touch "${J05_MODEL_DIST}/.p3_converted"
  fi
else
  echo "+ [dry-run] hf download + convert_hf_to_torch_dist（单卡，qwen3-0.6B）"
fi

# ---------------------------------------------------------------- 合成数据（tiny：8 条 × 1k token）
p3_run python3 "${SCRIPT_DIR}/lib/make_synth_rollout.py" \
  --out "${SYNTH}" --num-samples 8 --n-per-prompt 4 --total-len 1024 --prompt-len 128 \
  --num-rollouts 1

# ---------------------------------------------------------------- 1 个 train step
DEBUG_ARGS=(
   --debug-train-only
   --load-debug-rollout-data "${SYNTH}"
   --num-rollout 1
   --rollout-batch-size 2
   --n-samples-per-prompt 4
   --global-batch-size 8
)
CKPT_ARGS=(
   --hf-checkpoint "${J05_MODEL_HF}"
   --ref-load "${J05_MODEL_DIST}"
)
GRPO_ARGS=(
   --advantage-estimator grpo
   --disable-grpo-std-normalization
   --use-kl-loss
   --kl-loss-coef 0.00
   --kl-loss-type low_var_kl
   --entropy-coef 0.00
   --eps-clip 0.2
   --eps-clip-high 0.28
)
OPTIMIZER_ARGS=(
   --optimizer adam
   --lr 1e-6
   --lr-decay-style constant
   --weight-decay 0.1
   --adam-beta1 0.9
   --adam-beta2 0.98
)
PERF_ARGS=(
   --tensor-model-parallel-size 1
   --pipeline-model-parallel-size 1
   --context-parallel-size 1
   --expert-model-parallel-size 1
   --expert-tensor-parallel-size 1
   --recompute-granularity full
   --recompute-method uniform
   --recompute-num-layers 1
   --use-dynamic-batch-size
   --max-tokens-per-gpu 4096
)
ACTOR_ARGS=(
   --actor-num-nodes 1
   --actor-num-gpus-per-node 1
)
MISC_ARGS=(
   --attention-dropout 0.0
   --hidden-dropout 0.0
   --accumulate-allreduce-grads-in-fp32
   --attention-softmax-in-fp32
   --attention-backend flash
)

RUNTIME_ENV_JSON="{\"env_vars\": {\"PYTHONPATH\": \"${P3_MEGATRON}\", \"CUDA_DEVICE_MAX_CONNECTIONS\": \"1\", \"NCCL_NVLS_ENABLE\": \"0\"}}"

if [ "${P3_DRY_RUN}" -eq 1 ]; then
  echo "[p3][dry-run] 完整训练命令（MODEL_ARGS 由 source scripts/models/${J05_MODEL_SCRIPT} 展开）："
  echo "  ray job submit --address=http://127.0.0.1:8265 --runtime-env-json='${RUNTIME_ENV_JSON}' -- \\"
  echo "    python3 ${P3_SLIME}/train.py \"\${MODEL_ARGS[@]}\" \\"
  printf '      %s\n' "${DEBUG_ARGS[@]}" "${CKPT_ARGS[@]}" "${GRPO_ARGS[@]}" \
    "${OPTIMIZER_ARGS[@]}" "${PERF_ARGS[@]}" "${ACTOR_ARGS[@]}" "${MISC_ARGS[@]}"
  exit 0
fi

p3_ray_restart 1
cd "${P3_SLIME}"
# shellcheck disable=SC1090
source "scripts/models/${J05_MODEL_SCRIPT}"
p3_dump_args "${EV}/j05_full_args.txt" "${MODEL_ARGS[@]}" "${DEBUG_ARGS[@]}" "${CKPT_ARGS[@]}" \
  "${GRPO_ARGS[@]}" "${OPTIMIZER_ARGS[@]}" "${PERF_ARGS[@]}" "${ACTOR_ARGS[@]}" "${MISC_ARGS[@]}"

set +e
ray job submit --address="http://127.0.0.1:8265" \
  --runtime-env-json="${RUNTIME_ENV_JSON}" \
  -- python3 "${P3_SLIME}/train.py" \
  "${MODEL_ARGS[@]}" "${DEBUG_ARGS[@]}" "${CKPT_ARGS[@]}" "${GRPO_ARGS[@]}" \
  "${OPTIMIZER_ARGS[@]}" "${PERF_ARGS[@]}" "${ACTOR_ARGS[@]}" "${MISC_ARGS[@]}" \
  2>&1 | tee "${LOG}"
RC=$?
set -e

# ---------------------------------------------------------------- 判定
if [ ${RC} -eq 0 ] && grep -qiE "grad[ _-]?norm" "${LOG}" && ! p3_grep_oom "${LOG}"; then
  echo "J0.5 RESULT: PASS（U-C 内核项预检通过，日志 ${LOG}）"
else
  echo "J0.5 RESULT: FAIL（rc=${RC}）——按协议 §3 红灯候选：检查是否 sm_120 内核缺陷；失败不修不猜，摘要记入 preflight_report"
  grep -iE "error|assert|illegal|no kernel|unsupported" "${LOG}" | tail -20 || true
  exit 1
fi
