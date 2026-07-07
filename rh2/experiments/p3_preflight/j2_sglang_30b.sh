#!/bin/bash
# J2 推理侧 30B serving 冒烟（slime pin 容器内执行，时间盒 1h）。
#
# 对应协议条目（preflight/8gpu_preflight_protocol.md J2）：
#   SGLang 起 Qwen3-30B-A3B，TP2×2 引擎起步（§1.5 rollout 分区"4 卡 TP2×2
#   引擎"= 官方 fully_async 示例形态），32k 上下文，记 tokens/s 与显存。
#   关闭"训推共存的推理半边"。
# 判据：两引擎健康、32k 上下文单请求成功、bench tokens/s 与显存水位入
#   evidence（无判死线，画像输入——喂 J4b 拓扑决策与 E6 回填）。
#
# 说明：本作业直接用裸 SGLang（python3 -m sglang.launch_server），不经 slime
#   训练栈——J2 只画推理半边；sglang.launch_server / bench_serving 的 flag
#   不是 slime flag，故不放 *_ARGS 数组（静态核对约定见 common.sh 头注）。
#   sm_120 已知规避项沿用 S1-0/7a 验证过的组合：--attention-backend triton
#   --sampling-backend pytorch --disable-cuda-graph（对应 slime 侧
#   --sglang-attention-backend/--sglang-sampling-backend/--sglang-disable-cuda-graph）。
#
# 用法：bash j2_sglang_30b.sh [--dry-run]
#   环境变量：J2_ENGINES（默认 2）、J2_TP（默认 2）、J2_CTX（默认 32768）、
#   J2_MEM_FRACTION（默认 0.75，§1.5 显存账口径）、J2_NUM_PROMPTS（默认 32）。
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
. "${SCRIPT_DIR}/common.sh"

EV="${P3_EV}/j2"
J2_ENGINES=${J2_ENGINES:-2}
J2_TP=${J2_TP:-2}
J2_CTX=${J2_CTX:-32768}
J2_MEM_FRACTION=${J2_MEM_FRACTION:-0.75}
J2_NUM_PROMPTS=${J2_NUM_PROMPTS:-32}
J2_BASE_PORT=${J2_BASE_PORT:-30001}
CSV="${EV}/j2_serving.csv"

p3_banner "J2 sglang 30B serving: ${J2_ENGINES} engines x TP${J2_TP}, ctx=${J2_CTX}"

SGL_COMMON_OPTS="--model-path ${P3_MODEL_HF} --tp ${J2_TP} --context-length ${J2_CTX} \
--mem-fraction-static ${J2_MEM_FRACTION} --attention-backend triton --sampling-backend pytorch \
--disable-cuda-graph --host 127.0.0.1"

SERVER_PIDS=""
launch_engine() {
  _idx="$1"
  _port=$((J2_BASE_PORT + _idx))
  _gpu_lo=$((_idx * J2_TP))
  _gpu_hi=$((_gpu_lo + J2_TP - 1))
  _gpus=$(seq -s, "${_gpu_lo}" "${_gpu_hi}")
  echo "+ CUDA_VISIBLE_DEVICES=${_gpus} python3 -m sglang.launch_server ${SGL_COMMON_OPTS} --port ${_port} > ${EV}/engine_${_idx}.log 2>&1 &"
  if [ "${P3_DRY_RUN}" -eq 0 ]; then
    CUDA_VISIBLE_DEVICES="${_gpus}" python3 -m sglang.launch_server ${SGL_COMMON_OPTS} --port "${_port}" \
      > "${EV}/engine_${_idx}.log" 2>&1 &
    SERVER_PIDS="${SERVER_PIDS} $!"
  fi
}

wait_healthy() {
  _port="$1"
  echo "+ wait http://127.0.0.1:${_port}/health_generate (<=600s)"
  if [ "${P3_DRY_RUN}" -eq 0 ]; then
    for _i in $(seq 1 120); do
      if curl -sf "http://127.0.0.1:${_port}/health_generate" >/dev/null 2>&1; then return 0; fi
      sleep 5
    done
    echo "FAIL: engine on port ${_port} 未在 600s 内健康（M7 素材：记入 evidence 后退出）"
    return 1
  fi
}

cleanup() {
  if [ "${P3_DRY_RUN}" -eq 0 ]; then
    # shellcheck disable=SC2086
    kill ${SERVER_PIDS} 2>/dev/null || true
    pkill -9 sglang 2>/dev/null || true
  fi
}
trap cleanup EXIT

if [ "${P3_DRY_RUN}" -eq 0 ]; then mkdir -p "${EV}"; fi

# ---------------------------------------------------------------- 起引擎
i=0
while [ "${i}" -lt "${J2_ENGINES}" ]; do
  launch_engine "${i}"
  i=$((i + 1))
done
i=0
while [ "${i}" -lt "${J2_ENGINES}" ]; do
  wait_healthy $((J2_BASE_PORT + i))
  i=$((i + 1))
done

# 显存水位（serving 稳态）
p3_run_sh "nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv | tee ${EV}/mem_serving_idle.txt"

# ---------------------------------------------------------------- 32k 上下文探针（单请求）
# 28k 输入 + 512 输出：验证 32k 上下文真实可服务（KV 池账 §1.5：TP2 引擎 ~27 条满 32k）。
PROBE_PORT=${J2_BASE_PORT}
echo "+ python3 32k-probe against port ${PROBE_PORT}"
if [ "${P3_DRY_RUN}" -eq 0 ]; then
  python3 - "$PROBE_PORT" "$EV" <<'PYEOF'
import json, sys, time, urllib.request
port, ev = sys.argv[1], sys.argv[2]
body = {"input_ids": list(range(100, 28772)), "sampling_params": {"max_new_tokens": 512, "temperature": 1.0, "top_p": 0.95}}
t0 = time.time()
req = urllib.request.Request(f"http://127.0.0.1:{port}/generate", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
resp = json.load(urllib.request.urlopen(req, timeout=1200))
dt = time.time() - t0
meta = resp.get("meta_info", {})
out = {"wall_s": dt, "completion_tokens": meta.get("completion_tokens"), "prompt_tokens": meta.get("prompt_tokens")}
print("[j2] 32k probe:", out)
open(f"{ev}/probe_32k.json", "w").write(json.dumps(out, indent=2))
PYEOF
fi

# ---------------------------------------------------------------- 吞吐 bench（每引擎）
i=0
while [ "${i}" -lt "${J2_ENGINES}" ]; do
  _port=$((J2_BASE_PORT + i))
  BENCH_LOG="${EV}/bench_engine_${i}.log"
  p3_run_sh "python3 -m sglang.bench_serving --backend sglang --host 127.0.0.1 --port ${_port} \
    --dataset-name random --num-prompts ${J2_NUM_PROMPTS} --random-input-len 4096 --random-output-len 1024 \
    --random-range-ratio 0.5 2>&1 | tee ${BENCH_LOG}"
  if [ "${P3_DRY_RUN}" -eq 0 ]; then
    TPS=$(grep -iE "output token throughput" "${BENCH_LOG}" | grep -oE "[0-9]+\.[0-9]+" | head -1)
    p3_csv_append "${CSV}" "engine,tp,ctx,num_prompts,output_tokens_per_s" \
      "${i},${J2_TP},${J2_CTX},${J2_NUM_PROMPTS},${TPS:-parse_failed}"
  fi
  i=$((i + 1))
done

# 显存水位（bench 后，观察 KV 池占用）
p3_run_sh "nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv | tee ${EV}/mem_serving_after_bench.txt"

echo "J2 RESULT: tokens/s -> ${CSV}；32k probe -> ${EV}/probe_32k.json；显存 -> ${EV}/mem_serving_*.txt"
