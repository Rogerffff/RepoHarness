#!/bin/bash
# J4 全要素训练 step（S1-7b 本体，slime pin 容器内执行，时间盒 3h）。
#
# 对应协议条目（preflight/8gpu_preflight_protocol.md J4 + "J4 判据（六项断言）"）：
#   custom_generate，8 题 × n=4（n=2 会被动态采样饿死 batch——A2 条款同款坑；
#   若必须 n=2 则显式关 filter 并记录偏离），E2 生产 flags，真实训练 step，
#   在 T3（分离 4 训 + 4 推，官方 fully_async 示例同款放置）执行。
#   关闭：S1-7b（routing tape + top-p tape 首次真实进 loss）+ tape 消费。
# 六项断言（lib/j4_assert.py 自动检查，全过才 PASS）：
#   1. rollout（8×4，top_p=0.95）经 S1 链路产出合格 Sample；
#   2. 启动期探针：renderer 类名断言（U-G）+ top-p tape 探针（U-H 同款）通过；
#   3. loss 消费 rollout_top_p_token_ids/offsets 与 rollout_routed_experts
#      无 raise、loss 有限值；
#   4. 训练 step 完成且 grad norm 非 NaN；
#   5. 训练分区与推理分区各自显存水位留档、全程无 OOM；
#   6. checkpoint 用后即弃（8 题来自 Verified 仓库——A1/D5 条款），
#      acceptance 记录该声明。
#
# 形态：复用 S1-6 编排（s1_7a_bringup.glue.generate 的 custom_generate 链路 +
#   container_train_disaggregated.sh 的分离放置模板），换 30B 模型/并行参数。
#   训练侧并行 = J3 的 A2 组（TP2×DP2·EP4·ETP1，T3 训练半边）；
#   rollout 侧 = TP2×2 引擎（§1.5 官方示例形态）。
#   MoE 特有：RH2_EXPECT_MOE_ROUTING=1（探针/会话请求 routing tape）+
#   --use-rollout-routing-replay（V4/M1 硬前提，必开）。
#
# 用法：bash j4_full_step.sh [--dry-run]
#   环境变量：J4_DYNAMIC_FILTER=0（当前 custom_generate 返回嵌套 group，
#   slime 内置 check_reward_nonzero_std 只支持平铺 Sample 列表；动态采样
#   要单独提供兼容过滤器后再开启）、
#   J4_MISMATCH_METRICS=0（M2 监控默认关；当前 slime 要求同时提供
#   J4_CUSTOM_TIS_FUNCTION_PATH 才能开启 --get-mismatch-metrics）、
#   RH2_MAX_RESPONSE_LEN/RH2_MAX_CONTEXT_LEN、SWE_AGENT_TIME_BUDGET_SEC。
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
. "${SCRIPT_DIR}/common.sh"

EV="${P3_EV}/j4"
BRINGUP=${BRINGUP:-${P3_RUN_ROOT}/preflight_j4}
J4_ACTOR_GPUS=${J4_ACTOR_GPUS:-4}
J4_ROLLOUT_GPUS=${J4_ROLLOUT_GPUS:-4}
J4_ROLLOUT_TP=${J4_ROLLOUT_TP:-2}
J4_DYNAMIC_FILTER=${J4_DYNAMIC_FILTER:-0}
J4_MISMATCH_METRICS=${J4_MISMATCH_METRICS:-0}
J4_CUSTOM_TIS_FUNCTION_PATH=${J4_CUSTOM_TIS_FUNCTION_PATH:-}
J4_NUM_ROLLOUT=${J4_NUM_ROLLOUT:-1}
# 严格验收默认锚点：--n-samples-per-prompt 4；快速 probe 才覆盖此值。
J4_ROLLOUT_BATCH_SIZE=${J4_ROLLOUT_BATCH_SIZE:-8}
J4_N_SAMPLES_PER_PROMPT=${J4_N_SAMPLES_PER_PROMPT:-4}
J4_EXPECTED_SAMPLES=$((J4_NUM_ROLLOUT * J4_ROLLOUT_BATCH_SIZE * J4_N_SAMPLES_PER_PROMPT))
TOTAL_GPUS=$((J4_ACTOR_GPUS + J4_ROLLOUT_GPUS))
LOG="${EV}/j4_train.log"

p3_banner "J4 full step (T3: ${J4_ACTOR_GPUS} train + ${J4_ROLLOUT_GPUS} rollout, TP${J4_ROLLOUT_TP} engines, samples=${J4_EXPECTED_SAMPLES})"
p3_require_large_storage_path "EV" "${EV}"
p3_require_large_storage_path "BRINGUP" "${BRINGUP}"
p3_require_large_storage_path "P3_RAY_TMP" "${P3_RAY_TMP}"

# ---------------------------------------------------------------- 依赖 + 数据面（与 7a 同）
if [ "${P3_DRY_RUN}" -eq 0 ]; then
  mkdir -p "${EV}" "${BRINGUP}/rollout_dumps" "${BRINGUP}/artifacts" "${BRINGUP}/ckpt"
  python -c "import swebench" 2>/dev/null || pip install --no-cache-dir "swebench>=4.1,<5"
  python -c "import tiktoken" 2>/dev/null || pip install --no-cache-dir tiktoken
  python -c "import openai" 2>/dev/null || pip install --no-cache-dir "openai>=1.108.1"
  python -c "import pydantic_config" 2>/dev/null || pip install --no-cache-dir "prime-pydantic-config>=0.3.0.dev83"
  export PATH=/root/tarballs/docker-cli:$PATH
  docker version --format '{{.Server.Version}}'
  PYTHONPATH="${P3_RH2}/src" python "${P3_RH2}/experiments/s1_7a_bringup/make_prompt_data.py" \
    --out "${BRINGUP}/swe_bringup_8.jsonl"
else
  echo "+ [dry-run] pip 依赖就位 + make_prompt_data.py --out ${BRINGUP}/swe_bringup_8.jsonl（P-4：8 题冻结集）"
fi

# ---------------------------------------------------------------- slime 参数（四组清单落实）
# ① checkpoint/model：双路径（P-3）——HF 给 rollout/tokenizer，torch_dist 给训练
CKPT_ARGS=(
   --hf-checkpoint "${P3_MODEL_HF}"
   --ref-load "${P3_MODEL_DIST}"
   --load "${BRINGUP}/ckpt"
   --save "${BRINGUP}/ckpt"
   --save-interval 1
)
# 默认 8 题 × n=4 = 32 条；可用 J4_ROLLOUT_BATCH_SIZE/J4_N_SAMPLES_PER_PROMPT
# 缩小为快速 probe，严格验收仍保留默认规模。
ROLLOUT_ARGS=(
   --prompt-data "${BRINGUP}/swe_bringup_8.jsonl"
   --input-key prompt
   --label-key label
   --metadata-key metadata
   --num-rollout "${J4_NUM_ROLLOUT}"
   --rollout-batch-size "${J4_ROLLOUT_BATCH_SIZE}"
   --n-samples-per-prompt "${J4_N_SAMPLES_PER_PROMPT}"
   --rollout-max-response-len "${RH2_MAX_RESPONSE_LEN:-2048}"
   --rollout-max-context-len "${RH2_MAX_CONTEXT_LEN:-32768}"
   --rollout-temperature 1.0
   --rollout-top-p 0.95
   --global-batch-size "${J4_GLOBAL_BATCH_SIZE:-32}"
   --custom-generate-function-path s1_7a_bringup.glue.generate
   --custom-convert-samples-to-train-data-path p3_preflight.rh2_convert.convert_samples_to_train_data
   --save-debug-rollout-data "${BRINGUP}/rollout_dumps/rollout_{rollout_id}.pt"
)
# E2 定案动态采样 filter（标准路径有效；fully_async 下静默失效的对称坑归 J4c）
if [ "${J4_DYNAMIC_FILTER}" = "1" ]; then
  ROLLOUT_ARGS=("${ROLLOUT_ARGS[@]}"
   --dynamic-sampling-filter-path slime.rollout.filter_hub.dynamic_sampling_filters.check_reward_nonzero_std
  )
fi
# 算法 flags = E2 定案（写死不现场配）+ routing replay 必开（V4/M1 硬前提）；
# --use-tis 决策挂 M2 实测（J4 先只开 --get-mismatch-metrics 观测不改 loss）
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
if [ "${J4_MISMATCH_METRICS}" = "1" ]; then
  if [ -z "${J4_CUSTOM_TIS_FUNCTION_PATH}" ]; then
    echo "J4_MISMATCH_METRICS=1 requires J4_CUSTOM_TIS_FUNCTION_PATH for this slime pin" >&2
    exit 2
  fi
  GRPO_ARGS=("${GRPO_ARGS[@]}" --get-mismatch-metrics)
  GRPO_ARGS=("${GRPO_ARGS[@]}" --custom-tis-function-path "${J4_CUSTOM_TIS_FUNCTION_PATH}")
fi
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
# ② 训练并行 = J3 的 A2 组（T3 训练侧）+ 长上下文三件套
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
# ③ rollout SGLang（模式甲 TP-only 多引擎：TP2×2；sm_120 规避三件套沿用 7a）
SGLANG_ARGS=(
   --rollout-num-gpus-per-engine "${J4_ROLLOUT_TP}"
   --sglang-mem-fraction-static "${RH2_SGLANG_MEM_FRACTION:-0.75}"
   --sglang-server-concurrency "${RH2_ROLLOUT_CONCURRENCY:-16}"
   --sglang-tool-call-parser qwen25
   --sglang-reasoning-parser qwen3
   --sglang-attention-backend triton
   --sglang-sampling-backend pytorch
   --sglang-disable-cuda-graph
)
# ④ async + weight sync（分离基线 = full + nccl；buffer 512MB 起，J5 扫两档）
WEIGHT_SYNC_ARGS=(
   --update-weight-mode full
   --update-weight-transport nccl
   --update-weights-interval 1
   --update-weight-buffer-size "${RH2_UPDATE_WEIGHT_BUFFER:-536870912}"
)
ACTOR_ARGS=(
   --actor-num-nodes 1
   --actor-num-gpus-per-node "${J4_ACTOR_GPUS}"
   --rollout-num-gpus "${J4_ROLLOUT_GPUS}"
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
    \"RH2_MOE_NUM_LAYERS\": \"48\",
    \"RH2_MOE_ROUTER_TOPK\": \"8\",
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
  echo "[p3][dry-run] J4 完整命令（MODEL_ARGS 由 source scripts/models/${P3_MODEL_SCRIPT} 展开）："
  echo "  ray job submit --address=http://127.0.0.1:8265 --runtime-env-json='<见上 RUNTIME_ENV_JSON>' -- \\"
  echo "    python3 ${P3_SLIME}/train_async.py \"\${MODEL_ARGS[@]}\" \\"
  printf '      %s\n' "${ACTOR_ARGS[@]}" "${CKPT_ARGS[@]}" "${ROLLOUT_ARGS[@]}" "${GRPO_ARGS[@]}" \
    "${OPTIMIZER_ARGS[@]}" "${PERF_ARGS[@]}" "${SGLANG_ARGS[@]}" "${WEIGHT_SYNC_ARGS[@]}" "${MISC_ARGS[@]}"
  echo "[p3][dry-run] 跑完后：python3 lib/j4_assert.py 六项断言 + rm -rf ${BRINGUP}/ckpt（判据 6）"
  exit 0
fi

# ---------------------------------------------------------------- 实跑
p3_ray_restart "${TOTAL_GPUS}"
mkdir -p "${EV}" "${BRINGUP}/rollout_dumps" "${BRINGUP}/artifacts" "${BRINGUP}/ckpt"
PYTHONPATH="${P3_RH2}/src" python "${P3_RH2}/experiments/s1_7a_bringup/make_prompt_data.py" \
  --out "${BRINGUP}/swe_bringup_8.jsonl"
test -s "${BRINGUP}/swe_bringup_8.jsonl"
cd "${P3_SLIME}"
# shellcheck disable=SC1090
source "scripts/models/${P3_MODEL_SCRIPT}"
p3_dump_args "${EV}/j4_full_args.txt" "${MODEL_ARGS[@]}" "${ACTOR_ARGS[@]}" "${CKPT_ARGS[@]}" \
  "${ROLLOUT_ARGS[@]}" "${GRPO_ARGS[@]}" "${OPTIMIZER_ARGS[@]}" "${PERF_ARGS[@]}" \
  "${SGLANG_ARGS[@]}" "${WEIGHT_SYNC_ARGS[@]}" "${MISC_ARGS[@]}"

# 判据 5：两分区显存水位分开留档（GPU 编号按 ray 实际分配核对，dmon 全采、
# 分区归属由 j4_assert.py 结合日志判断）
p3_dmon_start "${EV}/dmon_all.csv"
T0=$(date +%s)
set +e
ray job submit --address="http://127.0.0.1:8265" \
  --runtime-env-json="${RUNTIME_ENV_JSON}" \
  -- python3 "${P3_SLIME}/train_async.py" \
  "${MODEL_ARGS[@]}" "${ACTOR_ARGS[@]}" "${CKPT_ARGS[@]}" "${ROLLOUT_ARGS[@]}" \
  "${GRPO_ARGS[@]}" "${OPTIMIZER_ARGS[@]}" "${PERF_ARGS[@]}" "${SGLANG_ARGS[@]}" \
  "${WEIGHT_SYNC_ARGS[@]}" "${MISC_ARGS[@]}" 2>&1 | tee "${LOG}"
RC=$?
set -e
T1=$(date +%s)
p3_dmon_stop
echo "j4_wall_seconds=$((T1 - T0)) rc=${RC}" | tee -a "${EV}/j4_wall.txt"

# ---------------------------------------------------------------- 离线转换边界检查 + 六项断言自动检查
set +e
python3 "${SCRIPT_DIR}/lib/j4_converter_offline.py" \
  --dumps-dir "${BRINGUP}/rollout_dumps" \
  --expect-routing \
  --rollout-top-p 0.95 \
  --rollout-batch-size "${J4_ROLLOUT_BATCH_SIZE}" \
  --n-samples-per-prompt "${J4_N_SAMPLES_PER_PROMPT}" \
  --out "${EV}/j4_converter_offline.json"
CONVERTER_RC=$?
set -e

set +e
python3 "${SCRIPT_DIR}/lib/j4_assert.py" \
  --log "${LOG}" \
  --dumps-dir "${BRINGUP}/rollout_dumps" \
  --artifacts-dir "${BRINGUP}/artifacts" \
  --dmon-csv "${EV}/dmon_all.csv" \
  --ckpt-dir "${BRINGUP}/ckpt" \
  --expected-samples "${J4_EXPECTED_SAMPLES}" \
  --out "${EV}/j4_assertions.json"
ASSERT_RC=$?
set -e

# 判据 6：checkpoint 用后即弃（Verified 8 题 A1/D5 条款——不得作为后续起点）
p3_run rm -rf "${BRINGUP}/ckpt"
echo "checkpoint_discarded=true  # A1/D5：8 题来自 Verified 仓库，checkpoint 不得作为任何后续起点" \
  >> "${EV}/j4_assertions_acceptance.txt"

if [ ${RC} -eq 0 ] && [ ${CONVERTER_RC} -eq 0 ] && [ ${ASSERT_RC} -eq 0 ]; then
  echo "J4 RESULT: PASS（六项断言 -> ${EV}/j4_assertions.json）"
else
  echo "J4 RESULT: FAIL（train rc=${RC}, converter rc=${CONVERTER_RC}, assert rc=${ASSERT_RC}）——失败不修不猜，摘要进 preflight_report"
  exit 1
fi
