#!/bin/bash
# J4b 拓扑/异步对比（slime pin 容器内执行，时间盒 2.5h）。
#
# 对应协议条目（preflight/8gpu_preflight_protocol.md J4b，第三轮修订）：
#   T1 colocate 同步 vs T3 双缓冲 vs T2′ 双缓冲，各连跑 2~3 步，记每步墙钟
#   分解、GPU util 曲线、rollout 尾部空闲占比。
#   预注册优先序：T3 先（直接复用 J4 的步数作 T3 数据点）→ T1 → T2′ 时间
#   允许才做；允许结论"T2′ 数据缺失，按 T3/T1 先定主案"。
# 判据（协议 §3 绿灯项）："J4b 产出明确的放置模式决策"——每拓扑的每步墙钟 +
#   尾部空闲占比进 CSV；升级档位触发条件口径 = 尾部空闲 > 每步墙钟 25%。
# 尾部空闲占比口径（协议原文，lib/tail_idle.py 照抄实现）：
#   （rollout 阶段内，推理分区 GPU 平均利用率 < 30% 阈值的尾段时长）/ step 总墙钟；
#   尾段起点 = 最后 25% 轨迹开始完成的时刻（bringup_events.jsonl 的 ts 字段
#   给出每条轨迹完成时间戳；dmon 1s 采样给出利用率曲线）。
#
# 拓扑映射（§1.5 候选）：
#   t3  = train_async.py 4 训 + 4 推（训练侧 A2：TP2×DP2·EP4）——复用 J4 形态
#   t1  = train.py --colocate 8 卡（训练侧 A4：TP4×CP2·EP8，官方 30B 测试同款；
#         colocate 在 slime 里无双缓冲，纯同步——train_async.py:11 断言禁 colocate）
#   t2p = train_async.py 2 训 + 6 推（训练侧 A1：TP2×DP1·EP2；TP2×3 引擎）
#
# 用法：bash j4b_topo_compare.sh [--dry-run]
#   环境变量：J4B_TOPOS="t3 t1 t2p"（预注册顺序，时间不够砍尾）、J4B_STEPS=2。
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
. "${SCRIPT_DIR}/common.sh"

EV="${P3_EV}/j4b"
BRINGUP_BASE=${BRINGUP_BASE:-${P3_RUN_ROOT}/preflight_j4b}
J4B_TOPOS=${J4B_TOPOS:-"t3 t1 t2p"}
J4B_STEPS=${J4B_STEPS:-2}
J4B_GLOBAL_BATCH_SIZE=${J4B_GLOBAL_BATCH_SIZE:-32}
CSV="${EV}/j4b_topo.csv"
CSV_HEADER="topo,entry,actor_gpus,rollout_gpus,steps,job_wall_s,step_wall_s,tail_idle_pct,oom,rc"

p3_banner "J4b topo compare: ${J4B_TOPOS} (steps=${J4B_STEPS})"
p3_require_large_storage_path "EV" "${EV}"
p3_require_large_storage_path "BRINGUP_BASE" "${BRINGUP_BASE}"
p3_require_large_storage_path "P3_RAY_TMP" "${P3_RAY_TMP}"

run_topo() {
  _topo="$1"
  case "${_topo}" in
    t3)  ENTRY=train_async.py; COLOCATE=0; A_GPUS=4; R_GPUS=4; R_TP=2; TP=2; CP=1; EP=4; ETP=1; ROLLOUT_GPU_IDX="4,5,6,7" ;;
    t1)  ENTRY=train.py;       COLOCATE=1; A_GPUS=8; R_GPUS=8; R_TP=8; TP=4; CP=2; EP=8; ETP=1; ROLLOUT_GPU_IDX="0,1,2,3,4,5,6,7" ;;
    t2p) ENTRY=train_async.py; COLOCATE=0; A_GPUS=2; R_GPUS=6; R_TP=2; TP=2; CP=1; EP=2; ETP=1; ROLLOUT_GPU_IDX="2,3,4,5,6,7" ;;
    *) echo "unknown topo ${_topo}"; return 1 ;;
  esac
  TOPO_EV="${EV}/${_topo}"
  BRINGUP="${BRINGUP_BASE}/${_topo}"
  LOG="${TOPO_EV}/train.log"
  p3_banner "J4b ${_topo}: ${ENTRY} actor=${A_GPUS} rollout=${R_GPUS} (TP${TP}/CP${CP}/EP${EP})"

  CKPT_ARGS=(
     --hf-checkpoint "${P3_MODEL_HF}"
     --ref-load "${P3_MODEL_DIST}"
  )
  ROLLOUT_ARGS=(
     --prompt-data "${BRINGUP}/swe_bringup_8.jsonl"
     --input-key prompt
     --label-key label
     --metadata-key metadata
     --num-rollout "${J4B_STEPS}"
     --rollout-batch-size 8
     --n-samples-per-prompt 4
     --rollout-max-response-len "${RH2_MAX_RESPONSE_LEN:-2048}"
     --rollout-max-context-len "${RH2_MAX_CONTEXT_LEN:-32768}"
     --rollout-temperature 1.0
     --rollout-top-p 0.95
     --global-batch-size "${J4B_GLOBAL_BATCH_SIZE}"
     --custom-generate-function-path s1_7a_bringup.glue.generate
     --custom-convert-samples-to-train-data-path p3_preflight.rh2_convert.convert_samples_to_train_data
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
     --tensor-model-parallel-size "${TP}"
     --pipeline-model-parallel-size 1
     --context-parallel-size "${CP}"
     --expert-model-parallel-size "${EP}"
     --expert-tensor-parallel-size "${ETP}"
     --sequence-parallel
     --recompute-granularity full
     --recompute-method uniform
     --recompute-num-layers 1
     --use-dynamic-batch-size
     --micro-batch-size 1
     --max-tokens-per-gpu $((${RH2_MAX_CONTEXT_LEN:-32768} / CP))
     --log-probs-chunk-size 1024
  )
  SGLANG_ARGS=(
     --rollout-num-gpus-per-engine "${R_TP}"
     --sglang-mem-fraction-static "${RH2_SGLANG_MEM_FRACTION:-0.75}"
     --sglang-server-concurrency "${RH2_ROLLOUT_CONCURRENCY:-16}"
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
     --actor-num-gpus-per-node "${A_GPUS}"
  )
  if [ "${COLOCATE}" -eq 1 ]; then
    ACTOR_ARGS=("${ACTOR_ARGS[@]}" --colocate)
  else
    ACTOR_ARGS=("${ACTOR_ARGS[@]}" --rollout-num-gpus "${R_GPUS}")
  fi
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
    echo "[p3][dry-run] ${_topo} 完整命令（MODEL_ARGS 由 source scripts/models/${P3_MODEL_SCRIPT} 展开）："
    echo "  ray job submit ... -- python3 ${P3_SLIME}/${ENTRY} \"\${MODEL_ARGS[@]}\" \\"
    printf '      %s\n' "${ACTOR_ARGS[@]}" "${CKPT_ARGS[@]}" "${ROLLOUT_ARGS[@]}" "${GRPO_ARGS[@]}" \
      "${OPTIMIZER_ARGS[@]}" "${PERF_ARGS[@]}" "${SGLANG_ARGS[@]}" "${WEIGHT_SYNC_ARGS[@]}" "${MISC_ARGS[@]}"
    echo "[p3][dry-run] 跑完后：lib/tail_idle.py --dmon ... --events ${BRINGUP}/artifacts/bringup_events.jsonl --rollout-gpus ${ROLLOUT_GPU_IDX}"
    return 0
  fi

  mkdir -p "${TOPO_EV}" "${BRINGUP}/rollout_dumps" "${BRINGUP}/artifacts"
  PYTHONPATH="${P3_RH2}/src" python "${P3_RH2}/experiments/s1_7a_bringup/make_prompt_data.py" \
    --out "${BRINGUP}/swe_bringup_8.jsonl"
  p3_ray_restart 8
  cd "${P3_SLIME}"
  # shellcheck disable=SC1090
  source "scripts/models/${P3_MODEL_SCRIPT}"
  p3_dump_args "${TOPO_EV}/full_args.txt" "${MODEL_ARGS[@]}" "${ACTOR_ARGS[@]}" "${CKPT_ARGS[@]}" \
    "${ROLLOUT_ARGS[@]}" "${GRPO_ARGS[@]}" "${OPTIMIZER_ARGS[@]}" "${PERF_ARGS[@]}" \
    "${SGLANG_ARGS[@]}" "${WEIGHT_SYNC_ARGS[@]}" "${MISC_ARGS[@]}"

  p3_dmon_start "${TOPO_EV}/dmon.csv"
  T0=$(date +%s)
  set +e
  ray job submit --address="http://127.0.0.1:8265" \
    --runtime-env-json="${RUNTIME_ENV_JSON}" \
    -- python3 "${P3_SLIME}/${ENTRY}" \
    "${MODEL_ARGS[@]}" "${ACTOR_ARGS[@]}" "${CKPT_ARGS[@]}" "${ROLLOUT_ARGS[@]}" \
    "${GRPO_ARGS[@]}" "${OPTIMIZER_ARGS[@]}" "${PERF_ARGS[@]}" "${SGLANG_ARGS[@]}" \
    "${WEIGHT_SYNC_ARGS[@]}" "${MISC_ARGS[@]}" > "${LOG}" 2>&1
  RC=$?
  set -e
  T1=$(date +%s)
  p3_dmon_stop

  WALL=$((T1 - T0))
  STEP_WALL=$(python3 "${SCRIPT_DIR}/lib/parse_step_metrics.py" --log "${LOG}" \
    --fallback-wall "${WALL}" --steps "${J4B_STEPS}" 2>/dev/null || echo "parse_failed")
  TAIL_IDLE=$(python3 "${SCRIPT_DIR}/lib/tail_idle.py" \
    --dmon "${TOPO_EV}/dmon.csv" \
    --events "${BRINGUP}/artifacts/bringup_events.jsonl" \
    --rollout-gpus "${ROLLOUT_GPU_IDX}" \
    --steps "${J4B_STEPS}" \
    --out "${TOPO_EV}/tail_idle.json" 2>/dev/null || echo "parse_failed")
  OOM=no; p3_grep_oom "${LOG}" && OOM=yes
  p3_csv_append "${CSV}" "${CSV_HEADER}" \
    "${_topo},${ENTRY},${A_GPUS},${R_GPUS},${J4B_STEPS},${WALL},${STEP_WALL},${TAIL_IDLE},${OOM},${RC}"
  echo "[j4b] ${_topo}: wall=${WALL}s step=${STEP_WALL}s tail_idle=${TAIL_IDLE} oom=${OOM} rc=${RC}"
}

for topo in ${J4B_TOPOS}; do
  run_topo "${topo}"
done

echo "J4b RESULT: -> ${CSV}"
echo "放置模式决策（协议 §3）：预期主案 = 分离（T2′/T3 按每步墙钟 + 尾部空闲占比定）+"
echo "train_async 双缓冲；colocate 仅当跨分区 update_weights 开销吃掉全部重叠收益才回退。"
echo "升级档位触发预注册：尾部空闲 > 每步墙钟 25%（本表 tail_idle_pct 列 + 首训双处测量）。"
