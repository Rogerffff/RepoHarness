#!/bin/bash
# J1 PCIe 通信微基准（slime pin 容器内执行，时间盒 0.7h）。
#
# 对应协议条目（preflight/8gpu_preflight_protocol.md J1 / P-5）：
#   nccl-tests：alltoall_perf + broadcast_perf + all_reduce_perf，2/4/8 卡三档。
#   权重同步走 broadcast、MoE dispatch 走 all-to-all、梯度走 all-reduce——
#   只测 all-to-all 画像不完整。关闭 U-C 的 "PCIe all-to-all 实测带宽" 项。
# 判据：三个原语 × 三档卡数全部产出带宽表（§5 模板：GB/s，msg size 两档），
#   无判死线——J1 是画像输入（喂给 J3 的 dispatcher 选择与 E6 回填）。
#
# P-5：nccl-tests 二进制或构建脚本备好——本脚本优先用已备好的二进制目录
#   （J1_BIN_DIR），否则从 /root/tarballs/nccl-tests.tar.gz 解包构建，
#   最后才回退 git clone（租用机可能无外网，靠前两条路径）。
#
# 用法：bash j1_nccl.sh [--dry-run]
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
. "${SCRIPT_DIR}/common.sh"

EV="${P3_EV}/j1"
J1_BIN_DIR=${J1_BIN_DIR:-/root/nccl-tests/build}
J1_SRC_TARBALL=${J1_SRC_TARBALL:-/root/tarballs/nccl-tests.tar.gz}
J1_GPU_TIERS=${J1_GPU_TIERS:-"2 4 8"}
# msg size 扫 16M ~ 1G（-f 4 步进），报告取 64M / 1G 两档（§5 模板"msg size 两档"）
J1_MSG_MIN=${J1_MSG_MIN:-16M}
J1_MSG_MAX=${J1_MSG_MAX:-1G}
CSV="${EV}/j1_bandwidth.csv"

p3_banner "J1 nccl-tests: alltoall/broadcast/all_reduce x gpus(${J1_GPU_TIERS})"

# ---------------------------------------------------------------- 构建（如需）
if [ "${P3_DRY_RUN}" -eq 1 ]; then
  echo "[p3][dry-run] 构建路径（按优先级）："
  echo "  1. 直接用 ${J1_BIN_DIR}/{alltoall_perf,broadcast_perf,all_reduce_perf}"
  echo "  2. tar xzf ${J1_SRC_TARBALL} -C /root && cd /root/nccl-tests && make -j MPI=0 CUDA_HOME=/usr/local/cuda"
  echo "  3. git clone https://github.com/NVIDIA/nccl-tests /root/nccl-tests && make -j MPI=0"
else
  mkdir -p "${EV}"
  if [ ! -x "${J1_BIN_DIR}/alltoall_perf" ]; then
    if [ -f "${J1_SRC_TARBALL}" ]; then
      tar xzf "${J1_SRC_TARBALL}" -C /root
    elif [ ! -d /root/nccl-tests ]; then
      git clone --depth 1 https://github.com/NVIDIA/nccl-tests /root/nccl-tests
    fi
    (cd /root/nccl-tests && make -j"$(nproc)" MPI=0 CUDA_HOME=/usr/local/cuda) 2>&1 | tee "${EV}/build.log"
  fi
fi

# ---------------------------------------------------------------- 跑三原语 × 三档
HEADER="op,gpus,msg_size,algbw_GBps,busbw_GBps"
for op in alltoall_perf broadcast_perf all_reduce_perf; do
  for g in ${J1_GPU_TIERS}; do
    LOG="${EV}/${op}_${g}gpu.log"
    p3_run_sh "${J1_BIN_DIR}/${op} -b ${J1_MSG_MIN} -e ${J1_MSG_MAX} -f 4 -g ${g} 2>&1 | tee ${LOG}"
    if [ "${P3_DRY_RUN}" -eq 0 ]; then
      # nccl-tests 数据行以字节数开头，结尾两组 (time algbw busbw #wrong)：
      # 取行尾 in-place 组的 algbw=$(NF-2) / busbw=$(NF-1)（#wrong 是最后一列）。
      # 抽取全部行进 CSV，报告阶段再挑 64M/1G 两档。
      awk -v op="${op}" -v g="${g}" \
        '$1 ~ /^[0-9]+$/ && NF >= 8 { print op "," g "," $1 "," $(NF-2) "," $(NF-1) }' \
        "${LOG}" | while read -r row; do
          p3_csv_append "${CSV}" "${HEADER}" "${row}"
        done
    fi
  done
done

echo "J1 RESULT: 带宽表 -> ${CSV}（§5 模板：报告挑 64M 与 1G 两档 busbw；DeepEP 决策输入给 J3 --moe-token-dispatcher-type）"
