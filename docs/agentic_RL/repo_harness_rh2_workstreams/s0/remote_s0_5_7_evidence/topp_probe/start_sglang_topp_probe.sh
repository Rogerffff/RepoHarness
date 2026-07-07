#!/usr/bin/env bash
# S0-6 top-p 动态探针专用 SGLang 启动脚本（复用 codex 既有环境，不重装）
set -euxo pipefail
export HF_HOME=/workspace/hf_cache
export TRANSFORMERS_CACHE=/workspace/hf_cache
export CUDA_HOME=/workspace/s0_inference_envs/vllm024/lib/python3.12/site-packages/nvidia/cu13
export CUDA_PATH=/workspace/s0_inference_envs/vllm024/lib/python3.12/site-packages/nvidia/cu13
export PATH=/workspace/s0_inference_envs/vllm024/lib/python3.12/site-packages/nvidia/cu13/bin:$PATH
export LD_LIBRARY_PATH=/workspace/s0_inference_envs/vllm024/lib/python3.12/site-packages/nvidia/cu13/lib:/workspace/s0_inference_envs/vllm024/lib/python3.12/site-packages/nvidia/cu13/lib64:${LD_LIBRARY_PATH:-}
exec /workspace/s0_inference_envs/sglang/bin/python -m sglang.launch_server \
  --model-path Qwen/Qwen3-30B-A3B \
  --host 127.0.0.1 \
  --port 30000 \
  --dtype bfloat16 \
  --mem-fraction-static 0.90 \
  --max-total-tokens 4096 \
  --disable-cuda-graph \
  --attention-backend triton \
  --sampling-backend pytorch \
  --moe-runner-backend triton \
  --enable-return-routed-experts
