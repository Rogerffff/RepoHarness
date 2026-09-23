#!/usr/bin/env bash
# 基座探针机器一键准备（在本机执行；目标：Ubuntu 22.04 VM，有 Docker；GPU 可选）。
# 用法：bootstrap_probe_box.sh <ssh_port> <host> [docker_hub_user]
# 凭据只从 git 忽略的 project1_execution/tmp/API.md 读取，不回显、不写入任何文档。
set -euo pipefail
PORT=${1:?ssh port}; HOST=${2:?host}; DHUB_USER=${3:-fangjianju666}
R=$(cd "$(dirname "$0")/../../.." && pwd)
D=$R/docs/agentic_RL/repo_harness_rh2_workstreams
KEY=$HOME/.ssh/vastai_ed25519
SSHO=(-o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -i "$KEY" -p "$PORT")
SSH=(ssh "${SSHO[@]}" "root@$HOST")
RSYNC_E="ssh -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -i $KEY -p $PORT"
read_secret() { python3 - "$D/project1_execution/tmp/API.md" "$1" <<'PY'
import re, sys
t = open(sys.argv[1]).read()
pat = {"docker": r"(dckr_pat_[A-Za-z0-9_\-]+)", "deepseek": r"DeepSeek:\s*(sk-[A-Za-z0-9]+)"}[sys.argv[2]]
m = re.search(pat, t); print(m.group(1) if m else "")
PY
}
DTOKEN=$(read_secret docker); DSKEY=$(read_secret deepseek)
[ -n "$DTOKEN" ] && [ -n "$DSKEY" ] || { echo "API.md 缺少 docker token 或 DeepSeek key"; exit 1; }

echo "== 1. 机器事实"
"${SSH[@]}" 'uname -m; nproc; free -g | sed -n 2p; df -h / /work 2>/dev/null | tail -2; docker --version; docker info 2>/dev/null | grep -E "Storage Driver|Cgroup|Runtimes" ; cat /sys/fs/cgroup/cgroup.controllers 2>/dev/null; (nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null || echo "no nvidia-smi")'

echo "== 2. 工具、目录、docker login、密钥落盘（0600）"
printf '%s' "$DTOKEN" | "${SSH[@]}" "docker login -u $DHUB_USER --password-stdin >/dev/null && echo docker_login_ok"
"${SSH[@]}" 'export DEBIAN_FRONTEND=noninteractive; apt-get update -qq >/dev/null && apt-get install -y -qq tmux jq git rsync curl xz-utils python3-venv python3-pip >/dev/null; mkdir -p /work/code /work/secrets /work/probe/{cc,recipes,derived,replay,runs,gateway,logs} && chmod 700 /work/secrets && echo tools_ok'
printf '%s' "$DSKEY" | "${SSH[@]}" 'umask 077; cat > /work/secrets/deepseek.key; chmod 600 /work/secrets/deepseek.key; echo deepseek_key_written'

echo "== 3. 同步代码与数据（不含 .venv / runs / tmp）"
rsync -az --delete -e "$RSYNC_E" --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' --exclude '.ruff_cache' "$R/rh2/" "root@$HOST:/work/code/rh2/"
"${SSH[@]}" "mkdir -p /work/code/docs/agentic_RL/repo_harness_rh2_workstreams"
rsync -az --delete -e "$RSYNC_E" "$D/s2/" "root@$HOST:/work/code/docs/agentic_RL/repo_harness_rh2_workstreams/s2/"
rsync -az --delete -e "$RSYNC_E" "$D/data_freeze/" "root@$HOST:/work/code/docs/agentic_RL/repo_harness_rh2_workstreams/data_freeze/"
for batch in dvc_install_v1c sqs_v1 install_wave1 compat_v1 pydantic_v1; do
  [ -d "$R/runs/env_recipe_repair_20260919/$batch/recipes" ] && rsync -az -e "$RSYNC_E" "$R/runs/env_recipe_repair_20260919/$batch/recipes/" "root@$HOST:/work/probe/recipes/$batch/" || true
done

echo "== 4. rh2 运行环境（按锁文件）"
"${SSH[@]}" 'command -v uv >/dev/null || (curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1); export PATH=$HOME/.local/bin:$PATH; cd /work/code/rh2 && uv sync --locked --group swe --group dev >/dev/null 2>&1; /work/code/rh2/.venv/bin/python -c "import importlib.metadata as m, aiohttp; print(\"swebench\", m.version(\"swebench\"), \"aiohttp\", aiohttp.__version__)"'

echo "== 5. Claude Code 2.1.205 平台包（npm registry 直取 + integrity 核对）"
"${SSH[@]}" 'set -e; cd /work/probe/cc; f=claude-code-linux-x64-2.1.205.tgz; [ -s $f ] || curl -fsSL -o $f https://registry.npmjs.org/@anthropic-ai/claude-code-linux-x64/-/$f; want=$(curl -fsSL https://registry.npmjs.org/@anthropic-ai/claude-code-linux-x64/2.1.205 | python3 -c "import sys,json; print(json.load(sys.stdin)[\"dist\"][\"integrity\"])"); got="sha512-$(openssl dgst -sha512 -binary $f | base64 -w0)"; [ "$want" = "$got" ] && echo "cc_tarball_integrity_ok $(stat -c %s $f) bytes" || { echo "cc tarball integrity mismatch"; exit 1; }'

echo "== 6. relay 镜像与前三题镜像"
"${SSH[@]}" 'set -e; docker pull -q python@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea; for i in conan-io_s_conan-15422 iterative_s_dvc-5839 getmoto_s_moto-5134; do docker pull -q xingyaoww/sweb.eval.x86_64.$i:latest; done; docker images --format "{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}" | head -8; ip -4 addr show docker0 | grep -o "inet [0-9.]*"'
echo "== done"
