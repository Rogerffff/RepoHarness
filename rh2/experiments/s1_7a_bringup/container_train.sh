#!/bin/bash
# S1-7a debug training transport step —— slime pin 容器内启动脚本。
# 前提：host_launch.sh 已把本仓库/模型/工件目录挂载好（见该脚本注释）。
set -exo pipefail

RH2_SRC=/workspace/rh2
BRINGUP=/root/bringup
MODEL_HF=/root/models/Qwen3-4B
MODEL_DIST=/root/models/Qwen3-4B_torch_dist
export PYTHONUNBUFFERED=1

# ---------------------------------------------------------------- 依赖就位
python -c "import swebench" 2>/dev/null || pip install --no-cache-dir "swebench>=4.1,<5"
python -c "import tiktoken" 2>/dev/null || pip install --no-cache-dir tiktoken
python -c "import openai" 2>/dev/null || pip install --no-cache-dir "openai>=1.108.1"
python -c "import pydantic_config" 2>/dev/null || pip install --no-cache-dir "prime-pydantic-config>=0.3.0.dev83"
export PATH=/root/tarballs/docker-cli:$PATH
docker version --format '{{.Server.Version}}'   # docker CLI + socket 必须可用（评分/沙箱硬依赖）

# ---------------------------------------------------------------- 权重转换（幂等）
if [ ! -f "${MODEL_DIST}/.rh2_converted" ]; then
  cd /root/slime
  source scripts/models/qwen3-4B.sh
  PYTHONPATH=/root/Megatron-LM python tools/convert_hf_to_torch_dist.py \
    "${MODEL_ARGS[@]}" \
    --hf-checkpoint "${MODEL_HF}" \
    --save "${MODEL_DIST}"
  touch "${MODEL_DIST}/.rh2_converted"
fi

# ---------------------------------------------------------------- 数据面（8 题冻结集）
mkdir -p "${BRINGUP}/rollout_dumps" "${BRINGUP}/artifacts" "${BRINGUP}/ckpt"
PYTHONPATH=${RH2_SRC}/src python ${RH2_SRC}/experiments/s1_7a_bringup/make_prompt_data.py \
  --out "${BRINGUP}/swe_bringup_8.jsonl"

# ---------------------------------------------------------------- ray
ray stop --force || true
pkill -9 sglang || true
sleep 2
export MASTER_ADDR=127.0.0.1
ray start --head --node-ip-address ${MASTER_ADDR} --num-gpus 1 \
  --disable-usage-stats --dashboard-host=0.0.0.0 --dashboard-port=8265

cd /root/slime
source scripts/models/qwen3-4B.sh

CKPT_ARGS=(
   --hf-checkpoint ${MODEL_HF}
   --ref-load ${MODEL_DIST}
   --load ${BRINGUP}/ckpt
   --save ${BRINGUP}/ckpt
   --save-interval 1
)

# 8 题 × n=4 = 32 条 rollout；global-batch-size 32 => 恰好 1 个 optimizer step
ROLLOUT_ARGS=(
   --prompt-data ${BRINGUP}/swe_bringup_8.jsonl
   --input-key prompt
   --label-key label
   --metadata-key metadata
   --num-rollout 1
   --rollout-batch-size 8
   --n-samples-per-prompt 4
   --rollout-max-response-len ${RH2_MAX_RESPONSE_LEN:-2048}
   --rollout-max-context-len ${RH2_MAX_CONTEXT_LEN:-32768}
   --rollout-temperature 1.0
   --rollout-top-p 0.95
   --global-batch-size 32
   --custom-generate-function-path s1_7a_bringup.glue.generate
   --save-debug-rollout-data "${BRINGUP}/rollout_dumps/rollout_{rollout_id}.pt"
)

# E2 flags：disable-grpo-std-normalization + clip 0.2/0.28
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
   --max-tokens-per-gpu ${RH2_MAX_TOKENS_PER_GPU:-32768}
   # top-p replay 的 loss 路径按 vocab 全宽做 masked_fill：不分块时一个
   # micro-batch 直接吃 ~12GB（run6 实测 OOM），按 1024 token 分块后 <1GB。
   --log-probs-chunk-size ${RH2_LOG_PROBS_CHUNK:-1024}
)

# serving 侧三件套（triton attention / pytorch sampling / 关 cuda graph）
# 逐字沿用 S1-0 在同型号 GPU（sm_120）上验证过的配置（uh_probe_report.md §服务启动）。
SGLANG_ARGS=(
   --rollout-num-gpus-per-engine 1
   --sglang-mem-fraction-static ${RH2_SGLANG_MEM_FRACTION:-0.6}
   --sglang-server-concurrency ${RH2_ROLLOUT_CONCURRENCY:-8}
   --sglang-tool-call-parser qwen25
   --sglang-reasoning-parser qwen3
   --sglang-attention-backend triton
   --sglang-sampling-backend pytorch
   --sglang-disable-cuda-graph
)

MISC_ARGS=(
   --attention-dropout 0.0
   --hidden-dropout 0.0
   --accumulate-allreduce-grads-in-fp32
   --attention-softmax-in-fp32
   --attention-backend ${RH2_ATTENTION_BACKEND:-flash}
)

RUNTIME_ENV_JSON="{
  \"env_vars\": {
    \"PYTHONPATH\": \"/root/Megatron-LM:${RH2_SRC}/src:${RH2_SRC}/experiments:/workspace/renderers\",
    \"CUDA_DEVICE_MAX_CONNECTIONS\": \"1\",
    \"NCCL_NVLS_ENABLE\": \"0\",
    \"ADAPTER_PUBLIC_HOST\": \"${ADAPTER_PUBLIC_HOST:-172.17.0.1}\",
    \"ADAPTER_PORT\": \"${ADAPTER_PORT:-18001}\",
    \"RH2_MODEL_ID\": \"${RH2_MODEL_ID:-Qwen/Qwen3-4B}\",
    \"RH2_BRINGUP_ARTIFACT_DIR\": \"${BRINGUP}/artifacts\",
    \"RH2_BRINGUP_HARNESS\": \"${RH2_BRINGUP_HARNESS:-claude_code}\",
    \"SWE_AGENT_TIME_BUDGET_SEC\": \"${SWE_AGENT_TIME_BUDGET_SEC:-600}\",
    \"RH2_MAX_TURNS_PER_SID\": \"${RH2_MAX_TURNS_PER_SID:-25}\",
    \"RH2_INJECT_INFRA_INSTANCE\": \"${RH2_INJECT_INFRA_INSTANCE:-django__django-11133}\",
    \"SLIME_AGENT_NODE_TARBALL\": \"/root/tarballs/node-v22.20.0-linux-x64.tar.xz\",
    \"SLIME_AGENT_CC_TARBALL\": \"/root/tarballs/claude-code.tgz\",
    \"SLIME_AGENT_CC_PLATFORM_TARBALL\": \"/root/tarballs/claude-code-linux-x64.tgz\",
    \"SLIME_AGENT_CC_EXTRA_ARGS\": \"--disallowedTools Task WebFetch WebSearch\",
    \"PATH\": \"/root/tarballs/docker-cli:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"
  }
}"

ray job submit --address="http://127.0.0.1:8265" \
   --runtime-env-json="${RUNTIME_ENV_JSON}" \
   -- python3 /root/slime/train.py \
   --actor-num-nodes 1 \
   --actor-num-gpus-per-node 1 \
   --colocate \
   "${MODEL_ARGS[@]}" \
   "${CKPT_ARGS[@]}" \
   "${ROLLOUT_ARGS[@]}" \
   "${OPTIMIZER_ARGS[@]}" \
   "${GRPO_ARGS[@]}" \
   "${PERF_ARGS[@]}" \
   "${SGLANG_ARGS[@]}" \
   "${MISC_ARGS[@]}"
