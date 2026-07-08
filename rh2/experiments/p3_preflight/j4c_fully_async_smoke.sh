#!/bin/bash
# J4c fully_async 冒烟（slime pin 容器内执行，时间盒 0.5h，口径按升级设计 I-2 收窄）。
#
# 对应协议条目（preflight/8gpu_preflight_protocol.md J4c，2026-07-08 修订）：
#   官方示例配置起 fully_async（--rollout-function-path
#   slime.rollout.fully_async_rollout.generate_rollout_fully_async，
#   examples/fully_async/ 同款"唯一旋钮"），设计成强制触发 abort
#   （长生成 + --update-weights-interval 1 + --save-debug-rollout-data）。
#   判定口径：标准路径 token 级续跑已静态确证（升级设计 §3 缺口①），
#   J4c 真正未知 = 我方 custom_generate 对 ABORTED 组的实际行为——
#   入口打点 sample.status / len(tokens) / response_length 三元组
#   （lib/j4c_probe.py 包装 s1_7a_bringup.glue.generate）。
#   顺带采集（I-3/N1/N2）：output_queue size 曲线（worker 日志 queue_warm=）
#   + done_cb task 异常计数（"process task raised"/"task crashed"）。
# 判据：可启动性（fully_async 起得来、能出样本）+ 三元组分类结论
#   （"带旧 token 重开"= 旧 token 悬挂最坏形态 / "干净重开" / 未见重入）。
#
# 设计决策（记入 implementation-notes）：默认用 Qwen3-4B（7a 已就位资产）——
#   J4c 验证的是机制（abort 回灌 + custom_generate 行为），与模型规模无关，
#   0.5h 时间盒内 30B 起服务太贵；模型可用 J4C_MODEL_* 覆盖为 30B。
#
# 防误用断言（协议 §1.6 预注册，本脚本自身先执行一遍）：fully_async 路径
#   静默忽略 --dynamic-sampling-filter-path / --over-sampling-batch-size
#   （缺口③），误配即 fail。
#
# 用法：bash j4c_fully_async_smoke.sh [--dry-run]
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
. "${SCRIPT_DIR}/common.sh"

EV="${P3_EV}/j4c"
BRINGUP=${BRINGUP:-${P3_RUN_ROOT}/preflight_j4c}
J4C_MODEL_HF=${J4C_MODEL_HF:-/root/models/Qwen3-4B}
J4C_MODEL_DIST=${J4C_MODEL_DIST:-/root/models/Qwen3-4B_torch_dist}
J4C_MODEL_SCRIPT=${J4C_MODEL_SCRIPT:-qwen3-4B.sh}
J4C_MODEL_ID=${J4C_MODEL_ID:-Qwen/Qwen3-4B}
J4C_ACTOR_GPUS=${J4C_ACTOR_GPUS:-1}
J4C_ROLLOUT_GPUS=${J4C_ROLLOUT_GPUS:-3}
J4C_ROLLOUT_TP=${J4C_ROLLOUT_TP:-1}
TOTAL_GPUS=$((J4C_ACTOR_GPUS + J4C_ROLLOUT_GPUS))
LOG="${EV}/j4c_train.log"
PROBE_LOG="${EV}/probe_triples.jsonl"

p3_banner "J4c fully_async smoke: ${J4C_MODEL_ID}, ${J4C_ACTOR_GPUS}+${J4C_ROLLOUT_GPUS}, 强制 abort"
p3_require_large_storage_path "EV" "${EV}"
p3_require_large_storage_path "BRINGUP" "${BRINGUP}"
p3_require_large_storage_path "P3_RAY_TMP" "${P3_RAY_TMP}"

# ---------------------------------------------------------------- 防误用断言（§1.6）
if [ -n "${RH2_DYNAMIC_SAMPLING_FILTER_PATH:-}" ] || [ -n "${RH2_OVER_SAMPLING_BATCH_SIZE:-}" ]; then
  echo "FATAL: fully_async 路径会静默忽略动态采样/over-sampling 参数（升级设计缺口③）——" >&2
  echo "       不许在 J4c 配置这两个参数，防止误以为 DAPO 过滤仍生效。" >&2
  exit 3
fi

# ---------------------------------------------------------------- slime 参数
CKPT_ARGS=(
   --hf-checkpoint "${J4C_MODEL_HF}"
   --ref-load "${J4C_MODEL_DIST}"
)
# 强制触发 abort 的组合：长生成（budget/turns 放大）+ interval=1（每步必
# update_weights -> 引擎 pause/abort 在途请求）+ 2 步（保证至少一次更新落在
# 生成中途）。fully_async 唯一旋钮 = rollout-function-path（官方示例同款）。
ROLLOUT_ARGS=(
   --rollout-function-path slime.rollout.fully_async_rollout.generate_rollout_fully_async
   --prompt-data "${BRINGUP}/swe_bringup_8.jsonl"
   --input-key prompt
   --label-key label
   --metadata-key metadata
   --num-rollout 2
   --rollout-batch-size 8
   --n-samples-per-prompt 4
   --rollout-max-response-len "${RH2_MAX_RESPONSE_LEN:-4096}"
   --rollout-max-context-len "${RH2_MAX_CONTEXT_LEN:-20480}"
   --rollout-temperature 1.0
   --rollout-top-p 0.95
   --global-batch-size 32
   --custom-generate-function-path p3_preflight.lib.j4c_probe.generate
   --save-debug-rollout-data "${BRINGUP}/rollout_dumps/rollout_{rollout_id}.pt"
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
   --max-tokens-per-gpu "${RH2_MAX_TOKENS_PER_GPU:-32768}"
   --log-probs-chunk-size 1024
)
SGLANG_ARGS=(
   --rollout-num-gpus-per-engine "${J4C_ROLLOUT_TP}"
   --sglang-mem-fraction-static "${RH2_SGLANG_MEM_FRACTION:-0.75}"
   --sglang-server-concurrency "${RH2_ROLLOUT_CONCURRENCY:-8}"
   --sglang-tool-call-parser qwen25
   --sglang-reasoning-parser qwen3
   --sglang-attention-backend triton
   --sglang-sampling-backend pytorch
   --sglang-disable-cuda-graph
)
WEIGHT_SYNC_ARGS=(
   --update-weight-mode full
   --update-weight-transport nccl
   --update-weights-interval 1
   --update-weight-buffer-size "${RH2_UPDATE_WEIGHT_BUFFER:-536870912}"
)
ACTOR_ARGS=(
   --actor-num-nodes 1
   --actor-num-gpus-per-node "${J4C_ACTOR_GPUS}"
   --rollout-num-gpus "${J4C_ROLLOUT_GPUS}"
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
    \"NCCL_NVLS_ENABLE\": \"0\",
    \"ADAPTER_PUBLIC_HOST\": \"${ADAPTER_PUBLIC_HOST:-172.17.0.1}\",
    \"ADAPTER_PORT\": \"${ADAPTER_PORT:-18001}\",
    \"RH2_MODEL_ID\": \"${J4C_MODEL_ID}\",
    \"RH2_BRINGUP_ARTIFACT_DIR\": \"${BRINGUP}/artifacts\",
    \"RH2_BRINGUP_HARNESS\": \"${RH2_BRINGUP_HARNESS:-claude_code}\",
    \"SWE_AGENT_TIME_BUDGET_SEC\": \"${SWE_AGENT_TIME_BUDGET_SEC:-900}\",
    \"RH2_MAX_TURNS_PER_SID\": \"${RH2_MAX_TURNS_PER_SID:-25}\",
    \"J4C_PROBE_LOG\": \"${PROBE_LOG}\",
    \"SLIME_AGENT_NODE_TARBALL\": \"/root/tarballs/node-v22.20.0-linux-x64.tar.xz\",
    \"SLIME_AGENT_CC_TARBALL\": \"/root/tarballs/claude-code.tgz\",
    \"SLIME_AGENT_CC_PLATFORM_TARBALL\": \"/root/tarballs/claude-code-linux-x64.tgz\",
    \"SLIME_AGENT_CC_EXTRA_ARGS\": \"--disallowedTools Task WebFetch WebSearch\",
    \"PATH\": \"/root/tarballs/docker-cli:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"
  }
}"

if [ "${P3_DRY_RUN}" -eq 1 ]; then
  echo "[p3][dry-run] J4c 完整命令（MODEL_ARGS 由 source scripts/models/${J4C_MODEL_SCRIPT} 展开）："
  echo "  ray job submit ... -- python3 ${P3_SLIME}/train_async.py \"\${MODEL_ARGS[@]}\" \\"
  printf '      %s\n' "${ACTOR_ARGS[@]}" "${CKPT_ARGS[@]}" "${ROLLOUT_ARGS[@]}" "${GRPO_ARGS[@]}" \
    "${OPTIMIZER_ARGS[@]}" "${PERF_ARGS[@]}" "${SGLANG_ARGS[@]}" "${WEIGHT_SYNC_ARGS[@]}" "${MISC_ARGS[@]}"
  echo "[p3][dry-run] 跑完后：python3 lib/j4c_metrics.py --log ${LOG} --probe ${PROBE_LOG} --out ${EV}/j4c_report.json"
  exit 0
fi

mkdir -p "${EV}" "${BRINGUP}/rollout_dumps" "${BRINGUP}/artifacts"
PYTHONPATH="${P3_RH2}/src" python "${P3_RH2}/experiments/s1_7a_bringup/make_prompt_data.py" \
  --out "${BRINGUP}/swe_bringup_8.jsonl"
p3_ray_restart "${TOTAL_GPUS}"
cd "${P3_SLIME}"
# shellcheck disable=SC1090
source "scripts/models/${J4C_MODEL_SCRIPT}"
p3_dump_args "${EV}/j4c_full_args.txt" "${MODEL_ARGS[@]}" "${ACTOR_ARGS[@]}" "${CKPT_ARGS[@]}" \
  "${ROLLOUT_ARGS[@]}" "${GRPO_ARGS[@]}" "${OPTIMIZER_ARGS[@]}" "${PERF_ARGS[@]}" \
  "${SGLANG_ARGS[@]}" "${WEIGHT_SYNC_ARGS[@]}" "${MISC_ARGS[@]}"

set +e
ray job submit --address="http://127.0.0.1:8265" \
  --runtime-env-json="${RUNTIME_ENV_JSON}" \
  -- python3 "${P3_SLIME}/train_async.py" \
  "${MODEL_ARGS[@]}" "${ACTOR_ARGS[@]}" "${CKPT_ARGS[@]}" "${ROLLOUT_ARGS[@]}" \
  "${GRPO_ARGS[@]}" "${OPTIMIZER_ARGS[@]}" "${PERF_ARGS[@]}" "${SGLANG_ARGS[@]}" \
  "${WEIGHT_SYNC_ARGS[@]}" "${MISC_ARGS[@]}" 2>&1 | tee "${LOG}"
RC=$?
set -e

# ---------------------------------------------------------------- 三元组 + I-3 指标
python3 "${SCRIPT_DIR}/lib/j4c_metrics.py" \
  --log "${LOG}" --probe "${PROBE_LOG}" --out "${EV}/j4c_report.json"

echo "J4c RESULT: rc=${RC}，报告 -> ${EV}/j4c_report.json（可启动性 + ABORTED 行为分类 + queue_size 曲线 + task 异常计数）"
