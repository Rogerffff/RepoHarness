#!/bin/bash
# J0 权重就位 + HF -> torch_dist 转换（slime pin 容器内执行）。
#
# 对应协议条目（preflight/8gpu_preflight_protocol.md）：
#   - P-3 双路径：rollout 侧用 HF checkpoint（P3_MODEL_HF）；训练侧必须先用
#     slime 的 tools/convert_hf_to_torch_dist.py 转成 Megatron torch_dist 格式
#     （P3_MODEL_DIST）。转换命令、模型脚本、路径与 digest 全部入 evidence。
#   - 转换需要 GPU/大内存，计入 J0 时间盒（2h 含下载）。
# 判据：HF 权重完整（safetensors index 校验）；转换产物目录生成且被
#   j3/j4 的 --ref-load 可用；双路径 + digest 记录写入 evidence。
#
# 转换命令形态锚（不许发明）：
#   reference/slime/slime/utils/external_utils/command_utils.py:52
#   （官方 30B 测试 test_qwen3_30B_A3B.py prepare() 即走这条：source 模型脚本
#     + torchrun --nproc-per-node 8 tools/convert_hf_to_torch_dist.py
#     ${MODEL_ARGS[@]} --hf-checkpoint ... --save ...）
#
# 用法：bash j0_convert_weights.sh [--dry-run]
#   环境变量：P3_CONVERT_GPUS（默认 8）、P3_FULL_DIGEST=1（对全部权重文件算
#   sha256，~60GB 顺序读，NVMe 上约几分钟；默认只对小文件算 sha256 +
#   大文件记 size manifest，见 implementation-notes 设计决策）。
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
. "${SCRIPT_DIR}/common.sh"

EV="${P3_EV}/j0"
P3_CONVERT_GPUS=${P3_CONVERT_GPUS:-8}
p3_banner "J0 weights: HF=${P3_MODEL_HF} -> torch_dist=${P3_MODEL_DIST} (gpus=${P3_CONVERT_GPUS})"

# ---------------------------------------------------------------- 1. HF 权重就位
# P-3 旁注：~60GB，现场拉取还是对象存储中转由租用机带宽实测后决定；这里默认
# hf download 现场拉取（幂等，已存在则跳过），下载墙钟记入 evidence。
if [ "${P3_DRY_RUN}" -eq 0 ] && [ ! -f "${P3_MODEL_HF}/model.safetensors.index.json" ]; then
  DL_T0=$(date +%s)
  p3_run hf download Qwen/Qwen3-30B-A3B --local-dir "${P3_MODEL_HF}"
  DL_T1=$(date +%s)
  mkdir -p "${EV}"
  echo "hf_download_wall_seconds=$((DL_T1 - DL_T0))" >> "${EV}/weights_evidence.txt"
else
  echo "+ [skip-or-dry] hf download Qwen/Qwen3-30B-A3B --local-dir ${P3_MODEL_HF}"
fi

# ---------------------------------------------------------------- 2. HF -> torch_dist
# CONVERT_EXTRA_ARGS 留空位：显存不够时可按官方 command_utils 的 extra_args
# 形态追加（例如更小的 --nproc-per-node 配合更多 CPU 内存）。
CONVERT_ARGS=(
   --hf-checkpoint "${P3_MODEL_HF}"
   --save "${P3_MODEL_DIST}"
)

if [ "${P3_DRY_RUN}" -eq 1 ]; then
  echo "[p3][dry-run] 转换命令（容器内实际执行形态）："
  echo "  cd ${P3_SLIME} && source scripts/models/${P3_MODEL_SCRIPT} && \\"
  echo "  PYTHONPATH=${P3_SLIME}:${P3_MEGATRON} torchrun --nproc-per-node ${P3_CONVERT_GPUS} \\"
  echo "    tools/convert_hf_to_torch_dist.py \"\${MODEL_ARGS[@]}\" ${CONVERT_ARGS[*]}"
  echo "[p3][dry-run] MODEL_ARGS 来自 source scripts/models/${P3_MODEL_SCRIPT}，实跑时展开值 dump 到 ${EV}/convert_model_args.txt"
  exit 0
fi

mkdir -p "${EV}"
if [ -f "${P3_MODEL_DIST}/.p3_converted" ]; then
  echo "[p3] torch_dist 产物已存在（.p3_converted 标记），跳过转换"
else
  cd "${P3_SLIME}"
  # shellcheck disable=SC1090
  source "scripts/models/${P3_MODEL_SCRIPT}"
  # 协议 J3 附①：dump 展开后的 MODEL_ARGS 入 evidence
  p3_dump_args "${EV}/convert_model_args.txt" "${MODEL_ARGS[@]}"
  CV_T0=$(date +%s)
  PYTHONPATH="${P3_SLIME}:${P3_MEGATRON}" torchrun --nproc-per-node "${P3_CONVERT_GPUS}" \
    tools/convert_hf_to_torch_dist.py \
    "${MODEL_ARGS[@]}" \
    "${CONVERT_ARGS[@]}" 2>&1 | tee "${EV}/convert_hf_to_torch_dist.log"
  CV_T1=$(date +%s)
  echo "convert_wall_seconds=$((CV_T1 - CV_T0))" >> "${EV}/weights_evidence.txt"
  touch "${P3_MODEL_DIST}/.p3_converted"
fi

# ---------------------------------------------------------------- 3. digest 记录（P-3）
# 设计：小文件（config/index/tokenizer，<8MB）逐个 sha256；大权重文件默认记
# (path,size) manifest；P3_FULL_DIGEST=1 时全量 sha256。
digest_dir() {
  _d="$1"; _out="$2"
  : > "${_out}"
  find "${_d}" -type f | sort | while read -r f; do
    sz=$(stat -c %s "$f" 2>/dev/null || stat -f %z "$f")
    if [ "${P3_FULL_DIGEST:-0}" = "1" ] || [ "${sz}" -lt 8388608 ]; then
      h=$(sha256sum "$f" | awk '{print $1}')
    else
      h="size-only"
    fi
    echo "${h}  ${sz}  ${f}" >> "${_out}"
  done
  # manifest 本身的 sha256 作为该目录的单值 digest
  sha256sum "${_out}" | tee -a "${EV}/weights_evidence.txt"
}
echo "== HF checkpoint manifest" >> "${EV}/weights_evidence.txt"
digest_dir "${P3_MODEL_HF}" "${EV}/hf_manifest.txt"
echo "== torch_dist manifest" >> "${EV}/weights_evidence.txt"
digest_dir "${P3_MODEL_DIST}" "${EV}/torch_dist_manifest.txt"
{
  echo "hf_checkpoint=${P3_MODEL_HF}"
  echo "torch_dist=${P3_MODEL_DIST}"
  echo "model_script=scripts/models/${P3_MODEL_SCRIPT}"
  echo "convert_gpus=${P3_CONVERT_GPUS}"
} >> "${EV}/weights_evidence.txt"
echo "J0-convert RESULT: PASS（evidence: ${EV}/weights_evidence.txt）"
