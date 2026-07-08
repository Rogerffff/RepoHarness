#!/bin/bash
# J4 train-only replay：复用已保存的 rollout dump，不重新运行黑盒 harness。
#
# 用途：
#   - J4 严格端到端失败后，用同一份 rollout_*.pt 快速验证训练侧是否能消费
#     top-p tape / routing tape、产生有限 loss 和 grad norm。
#   - 不替代严格 J4；它只回答“trainer consumption 是否成立”。
#
# 用法：
#   J4_REPLAY_SOURCE_RUN=j4_formal_... bash j4_train_replay.sh
#
# 关键环境变量：
#   J4_REPLAY_SOURCE_RUN              必填；默认 dump 路径为
#                                     ${P3_RUN_ROOT}/${J4_REPLAY_SOURCE_RUN}/rollout_dumps/rollout_{rollout_id}.pt
#   J4_REPLAY_GLOBAL_BATCH_SIZE       默认 16；用于绕过严格 J4 中 trainable rollout
#                                     少于 32 的调度问题，验证训练消费本身。
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
. "${SCRIPT_DIR}/common.sh"

J4_REPLAY_SOURCE_RUN=${J4_REPLAY_SOURCE_RUN:-}
J4_REPLAY_ID=${J4_REPLAY_ID:-j4_replay_$(date -u +%Y%m%dT%H%M%SZ)}
J4_REPLAY_GLOBAL_BATCH_SIZE=${J4_REPLAY_GLOBAL_BATCH_SIZE:-16}
J4_REPLAY_NUM_ROLLOUT=${J4_REPLAY_NUM_ROLLOUT:-1}
J4_REPLAY_ROLLOUT_BATCH_SIZE=${J4_REPLAY_ROLLOUT_BATCH_SIZE:-8}
J4_REPLAY_N_SAMPLES_PER_PROMPT=${J4_REPLAY_N_SAMPLES_PER_PROMPT:-4}
if [ -z "${J4_REPLAY_DUMP_TEMPLATE:-}" ]; then
  J4_REPLAY_DUMP_TEMPLATE="${P3_RUN_ROOT}/${J4_REPLAY_SOURCE_RUN}/rollout_dumps/rollout_{rollout_id}.pt"
fi

EV="${P3_EV}/${J4_REPLAY_ID}"
BRINGUP=${BRINGUP:-${P3_RUN_ROOT}/${J4_REPLAY_ID}}
LOG="${EV}/train_replay.log"

p3_banner "J4 train-only replay: source=${J4_REPLAY_SOURCE_RUN}, global_batch_size=${J4_REPLAY_GLOBAL_BATCH_SIZE}"
p3_require_large_storage_path "EV" "${EV}"
p3_require_large_storage_path "BRINGUP" "${BRINGUP}"
p3_require_large_storage_path "P3_RAY_TMP" "${P3_RAY_TMP}"

if [ -z "${J4_REPLAY_SOURCE_RUN}" ]; then
  echo "FATAL: J4_REPLAY_SOURCE_RUN is required, for example j4_formal_20260708T160749Z" >&2
  exit 2
fi

CKPT_ARGS=(
   --hf-checkpoint "${P3_MODEL_HF}"
   --ref-load "${P3_MODEL_DIST}"
   --load "${BRINGUP}/ckpt"
   --save "${BRINGUP}/ckpt"
   --save-interval 1
)
DEBUG_ARGS=(
   --debug-train-only
   --load-debug-rollout-data "${J4_REPLAY_DUMP_TEMPLATE}"
   --num-rollout "${J4_REPLAY_NUM_ROLLOUT}"
   --rollout-batch-size "${J4_REPLAY_ROLLOUT_BATCH_SIZE}"
   --n-samples-per-prompt "${J4_REPLAY_N_SAMPLES_PER_PROMPT}"
   --rollout-top-p 0.95
   --global-batch-size "${J4_REPLAY_GLOBAL_BATCH_SIZE}"
   --custom-convert-samples-to-train-data-path p3_preflight.rh2_convert.convert_samples_to_train_data
)
PARALLEL_ARGS=(
   --tensor-model-parallel-size 2
   --pipeline-model-parallel-size 1
   --context-parallel-size 1
   --expert-model-parallel-size 4
   --expert-tensor-parallel-size 1
   --sequence-parallel
   --micro-batch-size 1
   --max-tokens-per-gpu "${RH2_MAX_TOKENS_PER_GPU:-32768}"
   --log-probs-chunk-size 1024
   --use-dynamic-batch-size
   --recompute-granularity full
   --recompute-method uniform
   --recompute-num-layers 1
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
   --use-rollout-routing-replay
)
OPTIMIZER_ARGS=(
   --optimizer adam
   --lr 1e-6
   --lr-decay-style constant
   --weight-decay 0.1
   --adam-beta1 0.9
   --adam-beta2 0.98
   --optimizer-cpu-offload
   --overlap-cpu-optimizer-d2h-h2d
   --use-precision-aware-optimizer
)
ACTOR_ARGS=(
   --actor-num-nodes 1
   --actor-num-gpus-per-node 4
)
MISC_ARGS=(
   --attention-dropout 0.0
   --hidden-dropout 0.0
   --accumulate-allreduce-grads-in-fp32
   --attention-softmax-in-fp32
   --attention-backend flash
)
RUNTIME_ENV_JSON="{
  \"env_vars\": {
    \"PYTHONPATH\": \"${P3_MEGATRON}:${P3_RH2}/src:${P3_RH2}/experiments:/workspace/renderers\",
    \"CUDA_DEVICE_MAX_CONNECTIONS\": \"1\",
    \"NCCL_NVLS_ENABLE\": \"0\"
  }
}"

if [ "${P3_DRY_RUN}" -eq 1 ]; then
  echo "[p3][dry-run] J4 replay 命令（MODEL_ARGS 由 source scripts/models/${P3_MODEL_SCRIPT} 展开）："
  echo "  ray job submit --address=http://127.0.0.1:8265 --runtime-env-json='<见 RUNTIME_ENV_JSON>' -- \\"
  echo "    python3 ${P3_SLIME}/train.py \"\${MODEL_ARGS[@]}\" \\"
  printf '      %s\n' "${CKPT_ARGS[@]}" "${DEBUG_ARGS[@]}" "${PARALLEL_ARGS[@]}" \
    "${GRPO_ARGS[@]}" "${OPTIMIZER_ARGS[@]}" "${ACTOR_ARGS[@]}" "${MISC_ARGS[@]}"
  echo "[p3][dry-run] 训练结束后删除 ${BRINGUP}/ckpt"
  exit 0
fi

mkdir -p "${EV}" "${BRINGUP}/ckpt"
if [ ! -f "${J4_REPLAY_DUMP_TEMPLATE//\{rollout_id\}/0}" ]; then
  echo "FATAL: replay dump not found: ${J4_REPLAY_DUMP_TEMPLATE//\{rollout_id\}/0}" >&2
  exit 2
fi

p3_ray_restart 4
cd "${P3_SLIME}"
# shellcheck disable=SC1090
source "scripts/models/${P3_MODEL_SCRIPT}"
p3_dump_args "${EV}/replay_args.txt" "${MODEL_ARGS[@]}" "${CKPT_ARGS[@]}" "${DEBUG_ARGS[@]}" \
  "${PARALLEL_ARGS[@]}" "${GRPO_ARGS[@]}" "${OPTIMIZER_ARGS[@]}" "${ACTOR_ARGS[@]}" "${MISC_ARGS[@]}"

p3_dmon_start "${EV}/dmon.csv"
T0=$(date +%s)
set +e
ray job submit --address="http://127.0.0.1:8265" \
  --runtime-env-json="${RUNTIME_ENV_JSON}" \
  -- python3 "${P3_SLIME}/train.py" \
  "${MODEL_ARGS[@]}" "${CKPT_ARGS[@]}" "${DEBUG_ARGS[@]}" "${PARALLEL_ARGS[@]}" \
  "${GRPO_ARGS[@]}" "${OPTIMIZER_ARGS[@]}" "${ACTOR_ARGS[@]}" "${MISC_ARGS[@]}" > "${LOG}" 2>&1
RC=$?
set -e
T1=$(date +%s)
p3_dmon_stop

echo "replay_wall_seconds=$((T1 - T0)) rc=${RC}" | tee "${EV}/replay_wall.txt"
if [ -d "${BRINGUP}/ckpt" ]; then
  find "${BRINGUP}/ckpt" -maxdepth 2 -type f | head -20 > "${EV}/ckpt_files_before_delete.txt" || true
fi
p3_run rm -rf "${BRINGUP}/ckpt"
echo "checkpoint_discarded=true" > "${EV}/checkpoint_discarded.txt"

LOSS_COUNT=$(grep -Eo "pg_loss[=: ][^, ]+|loss[/:a-zA-Z_]*[=: ][-+0-9.eE]+" "${LOG}" 2>/dev/null | wc -l | tr -d ' ')
GRAD_COUNT=$(grep -Eo "grad_norm[=: ][-+0-9.eE]+" "${LOG}" 2>/dev/null | wc -l | tr -d ' ')
cat > "${EV}/replay_summary.json" <<EOF
{
  "rc": ${RC},
  "source_run": "${J4_REPLAY_SOURCE_RUN}",
  "global_batch_size": ${J4_REPLAY_GLOBAL_BATCH_SIZE},
  "loss_marker_count": ${LOSS_COUNT},
  "grad_norm_marker_count": ${GRAD_COUNT},
  "checkpoint_discarded": true
}
EOF

if [ ${RC} -eq 0 ]; then
  echo "J4 REPLAY RESULT: PASS -> ${EV}/replay_summary.json"
else
  echo "J4 REPLAY RESULT: FAIL rc=${RC} -> ${EV}/replay_summary.json"
  exit ${RC}
fi
