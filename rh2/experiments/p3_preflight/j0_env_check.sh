#!/bin/bash
# J0 环境就位检查（host 侧执行，租到卡后第一个跑）。
#
# 对应协议条目（preflight/8gpu_preflight_protocol.md）：
#   - J0：镜像/权重/GPU 可见性/`nvidia-smi topo -m` 拓扑留档（时间盒 2h 含下载）。
#   - P-1/P-9：slime 镜像 digest 必须命中 pin（a7317182…），P3 全程禁止升级。
#   - P-7：主机内存分档——>=512GB 推荐线（绿）；[400,512) 勉强最低线（黄）；
#          <400GB 直接红灯（30B 训练在本机不成立，进协议 §3 放弃线选项 (b)），
#          本脚本此时以退出码 2 硬失败。
#   - §5 记录模板首行：机器：卡型×8 / 驱动 / CUDA / PCIe 拓扑（topo -m 原文）。
# 判据：8 卡可见、驱动/CUDA 版本留档、topo -m 原文入 evidence、磁盘余量留档、
#       内存分档 GREEN/YELLOW（RED 即失败）、镜像 digest == pin。
#
# 用法：bash j0_env_check.sh [--dry-run]
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
. "${SCRIPT_DIR}/common.sh"

EV="${P3_EV}/j0"
p3_banner "J0 env check -> ${EV}"

if [ "${P3_DRY_RUN}" -eq 1 ]; then
  echo "[p3][dry-run] 将执行的检查（真机顺序）："
  echo "  1. nvidia-smi -L                        # GPU 可见性，判 8 卡"
  echo "  2. nvidia-smi --query-gpu=driver_version,name,memory.total"
  echo "  3. nvidia-smi topo -m > ${EV}/topo_m.txt # PCIe 拓扑原文留档"
  echo "  4. nvcc --version / cat /usr/local/cuda/version.json（若存在）"
  echo "  5. df -h（/root 与 docker root）磁盘余量留档（30B HF ~60GB + torch_dist 产物）"
  echo "  6. /proc/meminfo MemTotal 分档：>=512GB GREEN / >=400GB YELLOW / <400GB RED(exit 2)"
  echo "  7. docker inspect ${P3_IMAGE_PIN} digest 比对（未拉取则 docker pull，计入 J0 时间盒）"
  echo "  8. Ray object store 配置留档（P-7 拆账项，读 ray 默认 /dev/shm 大小）"
  exit 0
fi

mkdir -p "${EV}"
REPORT="${EV}/env_check.txt"
: > "${REPORT}"
FAIL=0

note() { echo "$*" | tee -a "${REPORT}"; }

# 1. GPU 可见性 --------------------------------------------------------------
note "== [1] GPU visibility"
nvidia-smi -L | tee -a "${REPORT}"
GPU_COUNT=$(nvidia-smi -L | wc -l | tr -d ' ')
if [ "${GPU_COUNT}" -ne 8 ]; then
  note "WARN: 可见 GPU=${GPU_COUNT}（协议按 8 卡设计，非 8 卡时 J1/J3 矩阵档位需手工裁剪）"
fi

# 2. 驱动 / CUDA -------------------------------------------------------------
note "== [2] driver / CUDA"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv | tee -a "${REPORT}"
(nvcc --version 2>/dev/null || cat /usr/local/cuda/version.json 2>/dev/null || echo "nvcc/version.json 不可见（host 侧可接受，容器内 J0.5 再验）") | tee -a "${REPORT}"

# 3. 拓扑留档（§5 模板要求 topo -m 原文） --------------------------------------
note "== [3] nvidia-smi topo -m -> ${EV}/topo_m.txt"
nvidia-smi topo -m > "${EV}/topo_m.txt" 2>&1 || note "WARN: topo -m 失败"
head -20 "${EV}/topo_m.txt" | tee -a "${REPORT}"

# 4. 磁盘 --------------------------------------------------------------------
note "== [4] disk"
df -h / /root /var/lib/docker 2>/dev/null | tee -a "${REPORT}"

# 5. 主机内存 P-7 分档 ---------------------------------------------------------
note "== [5] host memory tier (P-7)"
MEM_KB=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
MEM_GB=$((MEM_KB / 1024 / 1024))
note "MemTotal = ${MEM_GB} GB"
if [ "${MEM_GB}" -ge 512 ]; then
  note "P-7 tier: GREEN（>=512GB 推荐线）"
elif [ "${MEM_GB}" -ge 400 ]; then
  note "P-7 tier: YELLOW（400~512GB 勉强最低线：优化器 CPU offload 366GB + object store + SGLang host + 沙箱 + 双缓冲在途，余量极薄，须记录 Ray object store 配置并盯 OOM killer）"
else
  note "P-7 tier: RED（<400GB —— 30B 训练在本机不成立，协议 §3 放弃线选项(b)：改租云端 NVLink 机。本脚本按'缺一不租'硬失败）"
  FAIL=2
fi

# 6. 镜像 digest 比对（P-1/P-9 pin） ------------------------------------------
note "== [6] slime image digest vs pin"
note "pin = ${P3_IMAGE_PIN}"
if ! docker image inspect "${P3_IMAGE_PIN}" >/dev/null 2>&1; then
  note "镜像未就位，开始 docker pull（计入 J0 时间盒）..."
  if ! docker pull "${P3_IMAGE_PIN}"; then
    note "FAIL: docker pull pin 镜像失败"
    FAIL=1
  fi
fi
if docker image inspect "${P3_IMAGE_PIN}" --format '{{join .RepoDigests ","}}' > "${EV}/image_digest.txt" 2>&1; then
  note "RepoDigests: $(cat "${EV}/image_digest.txt")"
  if grep -q "a7317182c71d35712ee4edc86a5d1c313dc969efdf0026d339673299c186ea75" "${EV}/image_digest.txt"; then
    note "image digest: MATCH pin"
  else
    note "FAIL: image digest 与 pin 不符（P-9 禁止顺手升级）"
    FAIL=1
  fi
fi

# 7. Ray object store 配置留档（P-7 要求记录） ---------------------------------
note "== [7] /dev/shm（Ray object store 默认落点）"
df -h /dev/shm 2>/dev/null | tee -a "${REPORT}"

note ""
if [ "${FAIL}" -ne 0 ]; then
  note "J0 RESULT: FAIL (${FAIL}) —— 缺一不租，先解决再租机时"
else
  note "J0 RESULT: PASS（详情 ${REPORT}）"
fi
exit "${FAIL}"
