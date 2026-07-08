#!/bin/bash
# J5 权重同步与切换测量（slime pin 容器内执行，时间盒 1h）。
#
# 对应协议条目（preflight/8gpu_preflight_protocol.md J5）：
#   跨分区 update_weights 的耗时、节奏与字节量（pause/flush/continue 三段
#   停顿分解）；--update-weight-buffer-size 512MB 默认对 MoE 两遍 pass 的
#   敏感度扫 2 档；colocate 的 offload/onload 显存曲线（J5_COLOCATE=1 附加段）。
#   关闭：U-C 切换项 + 权重同步未知；M3（update 停顿吞吐塌陷）顺带采集。
# 判据：两档 buffer-size 各产出 update_weights 耗时表（§5 模板"J5：
#   update_weights 耗时 / sleep-resume 前后显存"）。
#
# 三段分解的实现口径（如实说明，详见 implementation-notes）：
#   pin e848052a 的 update_weight_from_distributed.py:110-133 时序 =
#   pause_generation → flush_cache → _send_weights（TP pass + EP pass）→
#   continue_generation，但源码只有 @timer 的总耗时打点
#   （日志键 perf/update_weights_time，train_metric_utils.py:27）。
#   lib/j5_parse.py：总耗时从 perf 键取；三段近似 = 引擎侧日志的
#   pause/flush/continue 时间戳（若 pin 镜像的 SGLang 引擎日志含这些行）+
#   trainer 侧 tqdm "Update weights" 进度时间窗（_send_weights 段）；
#   缺日志行时降级记录总耗时并在报告标注"三段不可分"。
#
# 用法：bash j5_weight_sync.sh [--dry-run]
#   环境变量：J5_BUFFER_SIZES="536870912 2147483648"（512MB / 2GiB 两档）、
#   J5_STEPS=2（interval=1 -> 每步一次 update_weights）、J5_COLOCATE=0。
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
. "${SCRIPT_DIR}/common.sh"

EV="${P3_EV}/j5"
BRINGUP_BASE=${BRINGUP_BASE:-${P3_RUN_ROOT}/preflight_j5}
J5_BUFFER_SIZES=${J5_BUFFER_SIZES:-"536870912 2147483648"}
J5_STEPS=${J5_STEPS:-2}
J5_COLOCATE=${J5_COLOCATE:-0}
J5_GLOBAL_BATCH_SIZE=${J5_GLOBAL_BATCH_SIZE:-32}
CSV="${EV}/j5_update_weights.csv"
CSV_HEADER="buffer_size_bytes,steps,update_weights_time_s_list,pause_flush_s,send_s,continue_s,three_phase_resolved,rc"

p3_banner "J5 weight sync: buffer sweep (${J5_BUFFER_SIZES}), steps=${J5_STEPS}"
p3_require_large_storage_path "EV" "${EV}"
p3_require_large_storage_path "BRINGUP_BASE" "${BRINGUP_BASE}"
p3_require_large_storage_path "P3_RAY_TMP" "${P3_RAY_TMP}"

run_buffer() {
  _buf="$1"
  BRINGUP="${BRINGUP_BASE}/buf_${_buf}"
  RUN_EV="${EV}/buf_${_buf}"
  LOG="${RUN_EV}/train.log"
  p3_banner "J5 run: --update-weight-buffer-size ${_buf}"

  CKPT_ARGS=(
     --hf-checkpoint "${P3_MODEL_HF}"
     --ref-load "${P3_MODEL_DIST}"
  )
  ROLLOUT_ARGS=(
     --prompt-data "${BRINGUP}/swe_bringup_8.jsonl"
     --input-key prompt
     --label-key label
     --metadata-key metadata
     --num-rollout "${J5_STEPS}"
     --rollout-batch-size 8
     --n-samples-per-prompt 4
     --rollout-max-response-len "${RH2_MAX_RESPONSE_LEN:-2048}"
     --rollout-max-context-len "${RH2_MAX_CONTEXT_LEN:-32768}"
     --rollout-temperature 1.0
     --rollout-top-p 0.95
     --global-batch-size "${J5_GLOBAL_BATCH_SIZE}"
     --custom-generate-function-path s1_7a_bringup.glue.generate
     --custom-convert-samples-to-train-data-path p3_preflight.rh2_convert.convert_samples_to_train_data
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
  PERF_ARGS=(
     --tensor-model-parallel-size 2
     --pipeline-model-parallel-size 1
     --context-parallel-size 1
     --expert-model-parallel-size 4
     --expert-tensor-parallel-size 1
     --sequence-parallel
     --recompute-granularity full
     --recompute-method uniform
     --recompute-num-layers 1
     --use-dynamic-batch-size
     --micro-batch-size 1
     --max-tokens-per-gpu "${RH2_MAX_TOKENS_PER_GPU:-32768}"
     --log-probs-chunk-size 1024
  )
  SGLANG_ARGS=(
     --rollout-num-gpus-per-engine 2
     --sglang-mem-fraction-static "${RH2_SGLANG_MEM_FRACTION:-0.75}"
     --sglang-server-concurrency "${RH2_ROLLOUT_CONCURRENCY:-16}"
     --sglang-tool-call-parser qwen25
     --sglang-reasoning-parser qwen3
     --sglang-attention-backend triton
     --sglang-sampling-backend pytorch
     --sglang-disable-cuda-graph
  )
  # 分离基线 = full + nccl（J3 附④）；interval=1 -> 每步一次 update_weights
  WEIGHT_SYNC_ARGS=(
     --update-weight-mode full
     --update-weight-transport nccl
     --update-weights-interval 1
     --update-weight-buffer-size "${_buf}"
  )
  ACTOR_ARGS=(
     --actor-num-nodes 1
     --actor-num-gpus-per-node 4
     --rollout-num-gpus 4
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
      \"RH2_MODEL_ID\": \"Qwen/Qwen3-30B-A3B\",
      \"RH2_EXPECT_MOE_ROUTING\": \"1\",
      \"RH2_BRINGUP_ARTIFACT_DIR\": \"${BRINGUP}/artifacts\",
      \"RH2_BRINGUP_HARNESS\": \"${RH2_BRINGUP_HARNESS:-claude_code}\",
      \"SWE_AGENT_TIME_BUDGET_SEC\": \"${SWE_AGENT_TIME_BUDGET_SEC:-600}\",
      \"RH2_MAX_TURNS_PER_SID\": \"${RH2_MAX_TURNS_PER_SID:-25}\",
      \"SLIME_AGENT_NODE_TARBALL\": \"/root/tarballs/node-v22.20.0-linux-x64.tar.xz\",
      \"SLIME_AGENT_CC_TARBALL\": \"/root/tarballs/claude-code.tgz\",
      \"SLIME_AGENT_CC_PLATFORM_TARBALL\": \"/root/tarballs/claude-code-linux-x64.tgz\",
      \"SLIME_AGENT_CC_EXTRA_ARGS\": \"--disallowedTools Task WebFetch WebSearch\",
      \"PATH\": \"/root/tarballs/docker-cli:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"
    }
  }"

  if [ "${P3_DRY_RUN}" -eq 1 ]; then
    echo "[p3][dry-run] buffer=${_buf} 完整命令（MODEL_ARGS 由 source scripts/models/${P3_MODEL_SCRIPT} 展开）："
    echo "  ray job submit ... -- python3 ${P3_SLIME}/train_async.py \"\${MODEL_ARGS[@]}\" \\"
    printf '      %s\n' "${ACTOR_ARGS[@]}" "${CKPT_ARGS[@]}" "${ROLLOUT_ARGS[@]}" "${GRPO_ARGS[@]}" \
      "${OPTIMIZER_ARGS[@]}" "${PERF_ARGS[@]}" "${SGLANG_ARGS[@]}" "${WEIGHT_SYNC_ARGS[@]}" "${MISC_ARGS[@]}"
    return 0
  fi

  mkdir -p "${RUN_EV}" "${BRINGUP}/artifacts"
  PYTHONPATH="${P3_RH2}/src" python "${P3_RH2}/experiments/s1_7a_bringup/make_prompt_data.py" \
    --out "${BRINGUP}/swe_bringup_8.jsonl"
  p3_ray_restart 8
  cd "${P3_SLIME}"
  # shellcheck disable=SC1090
  source "scripts/models/${P3_MODEL_SCRIPT}"
  p3_dump_args "${RUN_EV}/full_args.txt" "${MODEL_ARGS[@]}" "${ACTOR_ARGS[@]}" "${CKPT_ARGS[@]}" \
    "${ROLLOUT_ARGS[@]}" "${GRPO_ARGS[@]}" "${OPTIMIZER_ARGS[@]}" "${PERF_ARGS[@]}" \
    "${SGLANG_ARGS[@]}" "${WEIGHT_SYNC_ARGS[@]}" "${MISC_ARGS[@]}"

  p3_dmon_start "${RUN_EV}/dmon.csv"
  set +e
  ray job submit --address="http://127.0.0.1:8265" \
    --runtime-env-json="${RUNTIME_ENV_JSON}" \
    -- python3 "${P3_SLIME}/train_async.py" \
    "${MODEL_ARGS[@]}" "${ACTOR_ARGS[@]}" "${CKPT_ARGS[@]}" "${ROLLOUT_ARGS[@]}" \
    "${GRPO_ARGS[@]}" "${OPTIMIZER_ARGS[@]}" "${PERF_ARGS[@]}" "${SGLANG_ARGS[@]}" \
    "${WEIGHT_SYNC_ARGS[@]}" "${MISC_ARGS[@]}" > "${LOG}" 2>&1
  RC=$?
  set -e
  p3_dmon_stop

  ROW=$(python3 "${SCRIPT_DIR}/lib/j5_parse.py" --log "${LOG}" --buffer-size "${_buf}" \
    --steps "${J5_STEPS}" --out "${RUN_EV}/update_weights.json" 2>/dev/null || echo "${_buf},${J5_STEPS},parse_failed,-,-,-,no,${RC}")
  p3_csv_append "${CSV}" "${CSV_HEADER}" "${ROW},${RC}"
  echo "[j5] buffer=${_buf}: rc=${RC} -> ${RUN_EV}/update_weights.json"
}

for buf in ${J5_BUFFER_SIZES}; do
  run_buffer "${buf}"
done

# ---------------------------------------------------------------- 可选：colocate offload/onload 显存曲线
if [ "${J5_COLOCATE}" = "1" ]; then
  p3_banner "J5 附加段：colocate offload/onload 显存曲线（T1 一步，dmon 全程）"
  echo "复用 j4b_topo_compare.sh 的 t1 拓扑（sleep/wake_up 的 perf 计时 + dmon 显存曲线即 J5 所需）："
  J4B_TOPOS=t1 J4B_STEPS=1 p3_run bash "${SCRIPT_DIR}/j4b_topo_compare.sh"
fi

echo "J5 RESULT: -> ${CSV}（§5 模板：update_weights 耗时 / sleep-resume 前后显存）"
echo "字节量口径：30B bf16 权重 ~61GB / 次全量推送（mode=full）；敏感度 = 两档 buffer 的耗时差"
