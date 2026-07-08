#!/bin/bash
# J3 训练侧并行配置扫描驱动（slime pin 容器内执行，核心矩阵，时间盒 4h）。
#
# 对应协议条目（preflight/8gpu_preflight_protocol.md J3 + "J3 附：四组启动参数清单"）：
#   固定：Qwen3-30B-A3B bf16、E2 生产 flags、--optimizer-cpu-offload、
#         sequence-parallel 开、合成 batch = 64 条 × 目标长度。
#   主轴 A：a1~a5（j3_matrix/a*.sh，TP/CP/DP/EP/ETP 逐组显式）。
#   主轴 B：32k（目标档）→ 24k（降级档）。副轴 mbs：1 → 2（显存允许才试）。
#   执行序：A1×32k×mbs1 起步；通过 → 扫 A2/A3 比速度；OOM → 立即降档不恋战，
#           记录降档路径（本驱动 OOM 时不重试，只记 CSV 继续下一格）。
#   每格记录：step 墙钟 / 显存峰值（train 态）/ tokens/s / 是否 OOM / 内核报错摘要。
# 判据（协议 §3）：最优配置 step（64 轨迹 × ~20k token、32k）<=15min 绿灯；
#   15~30min 黄灯；全配置 24k/mbs1 仍 OOM 或 step>45min 红灯。
#
# 四组参数清单落实位置：
#   ① checkpoint/model args     -> CKPT_ARGS + source scripts/models/qwen3-30B-A3B.sh
#                                  （MODEL_ARGS 展开值 dump 到 evidence）
#   ② train parallel + MoE args -> PARALLEL_ARGS + PERF_ARGS（TP/PP/EP/ETP/CP 逐组、
#                                  --use-rollout-routing-replay 必开、长上下文三件套：
#                                  mbs / --log-probs-chunk-size 1024 / max-tokens-per-gpu=CTX/CP；
#                                  --moe-token-dispatcher-type alltoall 在 MODEL_ARGS 内，
#                                  DeepEP 视 J1 结果换）
#   ③ rollout SGLang args       -> J3 为 --debug-train-only 纯训练侧，不起 SGLang，
#                                  ③ 组由 J2/J4 落实（协议 J1~J3 用合成数据的 F2 纪律）
#   ④ async + weight sync args  -> 同上归 J4/J5；J3 不涉权重同步
#   算法 flags（E2 定案）        -> GRPO_ARGS（grpo / clip 0.2/0.28 /
#                                  --disable-grpo-std-normalization / top_p 0.95）
#
# 用法：bash run_j3.sh [--dry-run]
#   环境变量：J3_CONFIGS="a1 a2 a3 a4"（默认；a5 仅显存不够时启用）、
#   J3_CTXS="32768 24576"、J3_MBS_LIST="1"（副轴 mbs=2 显存允许才加）、
#   J3_STEPS=2、J3_CELL_TIMEOUT=2400（秒/格）。
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
. "${SCRIPT_DIR}/../common.sh"

EV="${P3_EV}/j3"
CSV="${EV}/j3_matrix.csv"
CSV_HEADER="config,train_gpus,tp,pp,cp,dp,ep,etp,ctx,mbs,steps,step_wall_s,mem_peak_mib,tokens_per_s,oom,rc,kernel_err"
J3_CONFIGS=${J3_CONFIGS:-"a1 a2 a3 a4"}
J3_CTXS=${J3_CTXS:-"32768 24576"}
J3_MBS_LIST=${J3_MBS_LIST:-"1"}
J3_STEPS=${J3_STEPS:-2}
J3_CELL_TIMEOUT=${J3_CELL_TIMEOUT:-2400}
J3_NUM_SAMPLES=${J3_NUM_SAMPLES:-64}

p3_banner "J3 matrix: configs=(${J3_CONFIGS}) x ctx=(${J3_CTXS}) x mbs=(${J3_MBS_LIST})"

run_cell() {
  _cfg="$1"; _ctx="$2"; _mbs="$3"
  # shellcheck disable=SC1090
  . "${SCRIPT_DIR}/${_cfg}.sh"   # 注入 J3_NAME/J3_TRAIN_GPUS/J3_TP/J3_PP/J3_CP/J3_DP/J3_EP/J3_ETP
  CELL="${J3_NAME}_ctx${_ctx}_mbs${_mbs}"
  CELL_EV="${EV}/${CELL}"
  LOG="${CELL_EV}/train.log"
  SYNTH="${EV}/synth_ctx${_ctx}_{rollout_id}.pt"
  p3_banner "J3 cell ${CELL}: gpus=${J3_TRAIN_GPUS} TP${J3_TP} PP${J3_PP} CP${J3_CP} DP${J3_DP} EP${J3_EP} ETP${J3_ETP}"
  if [ "${P3_DRY_RUN}" -eq 0 ]; then mkdir -p "${EV}"; fi

  # 合成数据（按 ctx 缓存，一次生成多格复用；含 routing tape + top-p tape，
  # 形状锚 types.py:352-369 / :122-125）
  if [ "${P3_DRY_RUN}" -eq 1 ] || [ ! -f "${EV}/synth_ctx${_ctx}_0.pt" ]; then
    p3_run python3 "${SCRIPT_DIR}/../lib/make_synth_rollout.py" \
      --out "${SYNTH}" --num-samples "${J3_NUM_SAMPLES}" --n-per-prompt 4 \
      --total-len "${_ctx}" --prompt-len 512 --num-rollouts "${J3_STEPS}" \
      --num-layers 48 --moe-topk 8 --num-experts 128 \
      --with-routing-tape --with-top-p-tape
  fi

  # ① checkpoint/model args（双路径：HF 供 tokenizer，torch_dist 供 --ref-load）
  CKPT_ARGS=(
     --hf-checkpoint "${P3_MODEL_HF}"
     --ref-load "${P3_MODEL_DIST}"
  )
  # 合成数据直通训练 step（不起 SGLang）
  DEBUG_ARGS=(
     --debug-train-only
     --load-debug-rollout-data "${SYNTH}"
     --num-rollout "${J3_STEPS}"
     --rollout-batch-size $((J3_NUM_SAMPLES / 4))
     --n-samples-per-prompt 4
     --global-batch-size "${J3_NUM_SAMPLES}"
     --rollout-top-p 0.95
  )
  # ② 并行 + MoE（逐组显式；MODEL_ARGS 已带 --moe-token-dispatcher-type alltoall
  #    / --num-experts 128 / --moe-router-topk 8 / --moe-router-dtype fp32 /
  #    --moe-grouped-gemm / --moe-permute-fusion，dump 为证）
  PARALLEL_ARGS=(
     --tensor-model-parallel-size "${J3_TP}"
     --pipeline-model-parallel-size "${J3_PP}"
     --context-parallel-size "${J3_CP}"
     --expert-model-parallel-size "${J3_EP}"
     --expert-tensor-parallel-size "${J3_ETP}"
     --sequence-parallel
  )
  # ② 长上下文显存三件套（每拓扑必填）：mbs / log-probs-chunk / max-tokens-per-gpu=CTX/CP
  PERF_ARGS=(
     --micro-batch-size "${_mbs}"
     --log-probs-chunk-size 1024
     --max-tokens-per-gpu $((_ctx / J3_CP))
     --use-dynamic-batch-size
     --recompute-granularity full
     --recompute-method uniform
     --recompute-num-layers 1
  )
  # 算法 flags = E2 定案（写死不现场配）；--use-rollout-routing-replay 必开（V4/M1 硬前提）
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
  # 优化器：CPU offload 必开（协议 J3 固定项 + P-7 主机内存前提；
  # 三连 flag 锚：tests/test_qwen3_30B_A3B.py optimizer_args）
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
     --actor-num-gpus-per-node "${J3_TRAIN_GPUS}"
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
    echo "[p3][dry-run] cell ${CELL} 完整命令（MODEL_ARGS 由 source scripts/models/${P3_MODEL_SCRIPT} 展开）："
    echo "  timeout ${J3_CELL_TIMEOUT} ray job submit --address=http://127.0.0.1:8265 \\"
    echo "    --runtime-env-json='${RUNTIME_ENV_JSON}' -- python3 ${P3_SLIME}/train.py \"\${MODEL_ARGS[@]}\" \\"
    printf '      %s\n' "${CKPT_ARGS[@]}" "${DEBUG_ARGS[@]}" "${PARALLEL_ARGS[@]}" \
      "${PERF_ARGS[@]}" "${GRPO_ARGS[@]}" "${OPTIMIZER_ARGS[@]}" "${ACTOR_ARGS[@]}" "${MISC_ARGS[@]}"
    return 0
  fi

  mkdir -p "${CELL_EV}"
  p3_ray_restart "${J3_TRAIN_GPUS}"
  cd "${P3_SLIME}"
  # shellcheck disable=SC1090
  source "scripts/models/${P3_MODEL_SCRIPT}"
  # 协议要求：每个组合的启动配置完整写出 + dump 展开后的 MODEL_ARGS
  p3_dump_args "${CELL_EV}/full_args.txt" "${MODEL_ARGS[@]}" "${CKPT_ARGS[@]}" "${DEBUG_ARGS[@]}" \
    "${PARALLEL_ARGS[@]}" "${PERF_ARGS[@]}" "${GRPO_ARGS[@]}" "${OPTIMIZER_ARGS[@]}" \
    "${ACTOR_ARGS[@]}" "${MISC_ARGS[@]}"

  p3_dmon_start "${CELL_EV}/dmon.csv"
  T0=$(date +%s)
  set +e
  timeout "${J3_CELL_TIMEOUT}" ray job submit --address="http://127.0.0.1:8265" \
    --runtime-env-json="${RUNTIME_ENV_JSON}" \
    -- python3 "${P3_SLIME}/train.py" \
    "${MODEL_ARGS[@]}" "${CKPT_ARGS[@]}" "${DEBUG_ARGS[@]}" "${PARALLEL_ARGS[@]}" \
    "${PERF_ARGS[@]}" "${GRPO_ARGS[@]}" "${OPTIMIZER_ARGS[@]}" "${ACTOR_ARGS[@]}" \
    "${MISC_ARGS[@]}" > "${LOG}" 2>&1
  RC=$?
  set -e
  T1=$(date +%s)
  p3_dmon_stop

  # 每格记录（失败不修不猜：解析后按矩阵继续）
  WALL=$((T1 - T0))
  STEP_WALL=$(python3 "${SCRIPT_DIR}/../lib/parse_step_metrics.py" --log "${LOG}" \
    --fallback-wall "${WALL}" --steps "${J3_STEPS}" 2>/dev/null || echo "parse_failed")
  MEM_PEAK=$(awk -F', *' 'NR>1 && $4 ~ /^[0-9]+$/ {if ($4>m) m=$4} END {print m+0}' "${CELL_EV}/dmon.csv" 2>/dev/null || echo 0)
  OOM=no; p3_grep_oom "${LOG}" && OOM=yes
  KERR=$(grep -icE "no kernel image|unsupported|illegal instruction|cutlass|CUBLAS_STATUS" "${LOG}" 2>/dev/null | head -1 || true)
  TOKENS_TOTAL=$((J3_NUM_SAMPLES * _ctx * J3_STEPS))
  if [ "${STEP_WALL}" != "parse_failed" ] && [ "${RC}" -eq 0 ]; then
    TPS=$(python3 -c "print(f'{${TOKENS_TOTAL}/${J3_STEPS}/${STEP_WALL}:.1f}')" 2>/dev/null || echo "-")
  else
    TPS="-"
  fi
  p3_csv_append "${CSV}" "${CSV_HEADER}" \
    "${J3_NAME},${J3_TRAIN_GPUS},${J3_TP},${J3_PP},${J3_CP},${J3_DP},${J3_EP},${J3_ETP},${_ctx},${_mbs},${J3_STEPS},${STEP_WALL},${MEM_PEAK},${TPS},${OOM},${RC},${KERR:-0}"
  echo "[j3] cell ${CELL}: rc=${RC} step_wall=${STEP_WALL}s mem_peak=${MEM_PEAK}MiB oom=${OOM}"
}

# 执行序：外层 config（a1 起步）、中层 ctx（32k -> 24k）、内层 mbs（1 -> 2）
for cfg in ${J3_CONFIGS}; do
  for ctx in ${J3_CTXS}; do
    for mbs in ${J3_MBS_LIST}; do
      run_cell "${cfg}" "${ctx}" "${mbs}"
    done
  done
done

echo "J3 RESULT: 矩阵表 -> ${CSV}（§5 模板：配置 × 上下文 × mbs -> step 时间/显存峰/tokens/s/备注）"
echo "绿黄红判定（协议 §3）：<=15min 绿 / 15~30min 黄 / >45min 或全 OOM 红——判定写进 preflight_report.md"
