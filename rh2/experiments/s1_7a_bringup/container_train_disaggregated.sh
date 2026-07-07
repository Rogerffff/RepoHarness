#!/bin/bash
# S1-9 H-2 交接契约模板：slime 启动配置的"分离放置 + train_async"同构形态。
#
# 背景（preflight/8gpu_preflight_protocol.md §8 H-2，对照 §1.5/§1.6 定案）：
#   - S1-7a 实跑用的是 container_train.sh（单卡 --colocate + train.py），那是
#     已产出 evidence 的历史脚本，**不回改**；本文件是面向 S4 目标形态的配置
#     模板——首训档位定案 = 分离放置 + train_async 双缓冲 + staleness 记账
#     （只记录不准入，库层已由 H-1 落地：projection.handshake 携带
#     Sample.weight_versions 原始 list + max_lag，gate 把分布写进
#     policy_staleness 维 evidence）。
#   - 同构的意义：7a 验过的 custom_generate 编排配置（ROLLOUT/GRPO/SGLANG 各组）
#     原样保留，只换放置与入口，避免到 S4 换形态重验一遍。
#   - train_async.py 自身断言禁 colocate（reference/slime/train_async.py:11
#     "Colocation is not supported for async training"）——本模板不含 --colocate。
#
# 拓扑参数（preflight §1.5 候选，J3/J4b 实测后定 T2'/T3）：
#   双卡最小同构形态（本模板默认）：RH2_ACTOR_GPUS=1 + RH2_ROLLOUT_GPUS=1、
#     rollout 引擎 TP=1（Qwen3-4B 单卡装得下）。
#   T3（S4 预实验 J4 执行形态，官方 fully_async 示例同款放置）：
#     RH2_ACTOR_GPUS=4 + RH2_ROLLOUT_GPUS=4 + RH2_ROLLOUT_TP=2（TP2 x 2 引擎；
#     rollout_num_gpus 必须被 per-engine TP 整除）。
#   T2'（rollout-heavy 候选）：RH2_ACTOR_GPUS=2 + RH2_ROLLOUT_GPUS=6 + RH2_ROLLOUT_TP=2。
set -exo pipefail

RH2_SRC=/workspace/rh2
BRINGUP=/root/bringup
MODEL_HF=/root/models/Qwen3-4B
MODEL_DIST=/root/models/Qwen3-4B_torch_dist
export PYTHONUNBUFFERED=1

# 分离放置的 GPU 划分（训练分区 + 推理分区，二者不重叠）
RH2_ACTOR_GPUS=${RH2_ACTOR_GPUS:-1}
RH2_ROLLOUT_GPUS=${RH2_ROLLOUT_GPUS:-1}
RH2_ROLLOUT_TP=${RH2_ROLLOUT_TP:-1}
TOTAL_GPUS=$((RH2_ACTOR_GPUS + RH2_ROLLOUT_GPUS))

# 防误用断言（preflight §1.6 预注册纪律，升级档位才会踩到）：
# fully_async 路径会**静默忽略** --dynamic-sampling-filter-path 与
# --over-sampling-batch-size（过滤逻辑只在 sglang_rollout 标准路径），
# 误配会让人以为 DAPO 过滤仍生效。本模板走 train_async（标准 rollout 路径，
# 动态采样有效）；若显式切到 fully_async rollout function，启动即 fail。
if [[ "${RH2_ROLLOUT_FUNCTION_PATH:-}" == *fully_async* ]]; then
  if [[ -n "${RH2_DYNAMIC_SAMPLING_FILTER_PATH:-}" || -n "${RH2_OVER_SAMPLING_BATCH_SIZE:-}" ]]; then
    echo "FATAL: fully_async rollout 路径会静默忽略动态采样/over-sampling 参数（preflight §1.6 缺口③）" >&2
    exit 3
  fi
fi

# ---------------------------------------------------------------- 依赖就位（与 7a 相同）
python -c "import swebench" 2>/dev/null || pip install --no-cache-dir "swebench>=4.1,<5"
python -c "import tiktoken" 2>/dev/null || pip install --no-cache-dir tiktoken
python -c "import openai" 2>/dev/null || pip install --no-cache-dir "openai>=1.108.1"
python -c "import pydantic_config" 2>/dev/null || pip install --no-cache-dir "prime-pydantic-config>=0.3.0.dev83"
export PATH=/root/tarballs/docker-cli:$PATH
docker version --format '{{.Server.Version}}'

# ---------------------------------------------------------------- 权重转换（幂等，与 7a 相同）
if [ ! -f "${MODEL_DIST}/.rh2_converted" ]; then
  cd /root/slime
  source scripts/models/qwen3-4B.sh
  PYTHONPATH=/root/Megatron-LM python tools/convert_hf_to_torch_dist.py \
    "${MODEL_ARGS[@]}" \
    --hf-checkpoint "${MODEL_HF}" \
    --save "${MODEL_DIST}"
  touch "${MODEL_DIST}/.rh2_converted"
fi

# ---------------------------------------------------------------- 数据面（8 题冻结集，与 7a 相同）
mkdir -p "${BRINGUP}/rollout_dumps" "${BRINGUP}/artifacts" "${BRINGUP}/ckpt"
PYTHONPATH=${RH2_SRC}/src python ${RH2_SRC}/experiments/s1_7a_bringup/make_prompt_data.py \
  --out "${BRINGUP}/swe_bringup_8.jsonl"

# ---------------------------------------------------------------- ray
ray stop --force || true
pkill -9 sglang || true
sleep 2
export MASTER_ADDR=127.0.0.1
ray start --head --node-ip-address ${MASTER_ADDR} --num-gpus ${TOTAL_GPUS} \
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

# 8 题 x n=4 = 32 条 rollout；custom_generate 编排配置与 7a 逐字相同（同构点）
ROLLOUT_ARGS=(
   --prompt-data ${BRINGUP}/swe_bringup_8.jsonl
   --input-key prompt
   --label-key label
   --metadata-key metadata
   --num-rollout 1
   --rollout-batch-size 8
   --n-samples-per-prompt 4
   --rollout-max-response-len ${RH2_MAX_RESPONSE_LEN:-2048}
   --rollout-max-context-len ${RH2_MAX_CONTEXT_LEN:-20480}
   --rollout-temperature 1.0
   --rollout-top-p 0.95
   --global-batch-size 32
   --custom-generate-function-path s1_7a_bringup.glue.generate
   --save-debug-rollout-data "${BRINGUP}/rollout_dumps/rollout_{rollout_id}.pt"
)

# E2 flags（与 7a 逐字相同）
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
   --log-probs-chunk-size ${RH2_LOG_PROBS_CHUNK:-1024}
)

# serving 侧三件套（与 S1-0/7a 同卡验证配置逐字相同）+ 分离拓扑的引擎划分
SGLANG_ARGS=(
   --rollout-num-gpus-per-engine ${RH2_ROLLOUT_TP}
   --sglang-mem-fraction-static ${RH2_SGLANG_MEM_FRACTION:-0.75}
   --sglang-server-concurrency ${RH2_ROLLOUT_CONCURRENCY:-8}
   --sglang-tool-call-parser qwen25
   --sglang-reasoning-parser qwen3
   --sglang-attention-backend triton
   --sglang-sampling-backend pytorch
   --sglang-disable-cuda-graph
)

# 分离放置的权重同步（preflight §1.6 / J3 附④：分离基线 = full + nccl；
# interval=1 使双缓冲的结构性 staleness 上界 ~= 1 个版本，天然落在行业
# 最紧实践 alpha=1 内——staleness 只记账不准入，账在 projection.handshake）
WEIGHT_SYNC_ARGS=(
   --update-weight-mode full
   --update-weight-transport nccl
   --update-weights-interval 1
   --update-weight-buffer-size ${RH2_UPDATE_WEIGHT_BUFFER:-536870912}
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
    \"SLIME_AGENT_NODE_TARBALL\": \"/root/tarballs/node-v22.20.0-linux-x64.tar.xz\",
    \"SLIME_AGENT_CC_TARBALL\": \"/root/tarballs/claude-code.tgz\",
    \"SLIME_AGENT_CC_PLATFORM_TARBALL\": \"/root/tarballs/claude-code-linux-x64.tgz\",
    \"SLIME_AGENT_CC_EXTRA_ARGS\": \"--disallowedTools Task WebFetch WebSearch\",
    \"PATH\": \"/root/tarballs/docker-cli:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"
  }
}"

# 入口 = train_async.py（双缓冲）；分离放置 = actor 分区 + rollout 分区显式划分，
# 不带 --colocate（train_async 断言禁用）。
ray job submit --address="http://127.0.0.1:8265" \
   --runtime-env-json="${RUNTIME_ENV_JSON}" \
   -- python3 /root/slime/train_async.py \
   --actor-num-nodes 1 \
   --actor-num-gpus-per-node ${RH2_ACTOR_GPUS} \
   --rollout-num-gpus ${RH2_ROLLOUT_GPUS} \
   "${MODEL_ARGS[@]}" \
   "${CKPT_ARGS[@]}" \
   "${ROLLOUT_ARGS[@]}" \
   "${OPTIMIZER_ARGS[@]}" \
   "${GRPO_ARGS[@]}" \
   "${PERF_ARGS[@]}" \
   "${SGLANG_ARGS[@]}" \
   "${WEIGHT_SYNC_ARGS[@]}" \
   "${MISC_ARGS[@]}"
