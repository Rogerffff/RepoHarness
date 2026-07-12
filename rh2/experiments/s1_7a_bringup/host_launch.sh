#!/bin/bash
# S1-7a host 侧准备 + slime pin 容器拉起（远程 GPU 机执行）。
# 用法： bash host_launch.sh prepare   # 下载 tarball/docker CLI（幂等）
#        bash host_launch.sh start    # 起容器（不跑训练）
#        bash host_launch.sh train    # 容器内执行 container_train.sh（前台阻塞）
set -exo pipefail

SLIME_IMAGE="slimerl/slime@sha256:a7317182c71d35712ee4edc86a5d1c313dc969efdf0026d339673299c186ea75"
REPO=/root/claude-code-verl-stage0h
NODE_VER=v22.20.0
DOCKER_CLI_VER=27.5.1

prepare() {
  mkdir -p /root/tarballs /root/bringup /root/models
  # Node 22（slime ClaudeCodeHarness 的沙箱内运行时）
  if [ ! -s /root/tarballs/node-${NODE_VER}-linux-x64.tar.xz ]; then
    rm -f /root/tarballs/node-${NODE_VER}-linux-x64.tar.xz
    curl -fL -o /root/tarballs/node-${NODE_VER}-linux-x64.tar.xz \
      https://nodejs.org/dist/${NODE_VER}/node-${NODE_VER}-linux-x64.tar.xz
  fi
  # Claude Code CLI：2.x 的 npm 主包只是 bootstrap（postinstall 拉平台二进制），
  # 直接下载 linux-x64 平台包——里面是自包含原生二进制，rollout 容器内免 Node/npm。
  # codex 轮次 8 P0-8：**固定版本 + 校验 sha256**（原 `latest` 不可复现；FA-5
  # 的 CC 行为画像绑定 2.1.205，见 fa/claude_code_retry_timeout_source_guided_
  # validation.md §4）。升级 CC 必须先重跑探针套件生成新证据、人工裁决差异。
  CC_VER="${RH2_CLAUDE_CODE_VERSION:-2.1.205}"
  CC_LINUX_SHA256="${RH2_CLAUDE_CODE_LINUX_SHA256:-d3dadfa9cde294ac82c755eb6d889291228849180bac5d677ad1a4027aca1bc4}"
  if [ ! -s /root/tarballs/claude-code-linux-x64.tgz ]; then
    echo "claude-code platform package pinned version: ${CC_VER}"
    curl -fL -o /root/tarballs/claude-code-linux-x64.tgz \
      "https://registry.npmjs.org/@anthropic-ai/claude-code-linux-x64/-/claude-code-linux-x64-${CC_VER}.tgz"
    ACTUAL_SHA=$(sha256sum /root/tarballs/claude-code-linux-x64.tgz | awk '{print $1}')
    if [ "${ACTUAL_SHA}" != "${CC_LINUX_SHA256}" ]; then
      echo "FATAL: claude-code-linux-x64 sha256 mismatch: got ${ACTUAL_SHA} want ${CC_LINUX_SHA256}" >&2
      rm -f /root/tarballs/claude-code-linux-x64.tgz
      exit 1
    fi
    echo "${CC_VER}" > /root/tarballs/claude-code-version.txt
    echo "claude-code-linux-x64 sha256 verified: ${ACTUAL_SHA}"
  fi
  # 静态 docker CLI（挂进 slime 容器用，daemon 走宿主 socket）
  if [ ! -x /root/tarballs/docker-cli/docker ]; then
    mkdir -p /root/tarballs/docker-cli
    curl -fL https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_CLI_VER}.tgz \
      | tar -xz -C /root/tarballs/docker-cli --strip-components=1 docker/docker
  fi
  ls -la /root/tarballs
}

start() {
  docker rm -f rh2-bringup 2>/dev/null || true
  docker run -d --name rh2-bringup \
    --gpus all --net host --ipc host --shm-size 32g \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /root/models:/root/models \
    -v /root/bringup:/root/bringup \
    -v /root/tarballs:/root/tarballs \
    -v ${REPO}/rh2:/workspace/rh2 \
    -v ${REPO}/reference/renderers:/workspace/renderers \
    "${SLIME_IMAGE}" sleep infinity
  docker exec rh2-bringup nvidia-smi -L
}

train() {
  docker exec \
    -e RH2_BRINGUP_HARNESS="${RH2_BRINGUP_HARNESS:-claude_code}" \
    -e RH2_INJECT_INFRA_INSTANCE="${RH2_INJECT_INFRA_INSTANCE:-django__django-11133}" \
    -e SWE_AGENT_TIME_BUDGET_SEC="${SWE_AGENT_TIME_BUDGET_SEC:-600}" \
    -e RH2_ATTENTION_BACKEND="${RH2_ATTENTION_BACKEND:-flash}" \
    -e RH2_ROLLOUT_CONCURRENCY="${RH2_ROLLOUT_CONCURRENCY:-8}" \
    -e RH2_MAX_CONTEXT_LEN="${RH2_MAX_CONTEXT_LEN:-32768}" \
    -e RH2_MAX_TOKENS_PER_GPU="${RH2_MAX_TOKENS_PER_GPU:-32768}" \
    -e RH2_MAX_RESPONSE_LEN="${RH2_MAX_RESPONSE_LEN:-2048}" \
    rh2-bringup bash /workspace/rh2/experiments/s1_7a_bringup/container_train.sh
}

case "${1:-}" in
  prepare) prepare ;;
  start) start ;;
  train) train ;;
  *) echo "usage: $0 {prepare|start|train}"; exit 2 ;;
esac
