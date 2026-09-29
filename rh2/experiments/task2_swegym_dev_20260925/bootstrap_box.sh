#!/usr/bin/env bash
# 任务二 CPU 机一键准备（在本机执行）：装 Docker、同步代码与数据、uv 环境、CC 2.1.205 平台包、relay 镜像。
# 用法：bootstrap_box.sh <host> [docker_hub_user]；凭据只从 git 忽略的 tmp/API.md 读取，不回显。
set -euo pipefail
HOST=${1:?host}; DHUB_USER=${2:-fangjianju666}
R=$(cd "$(dirname "$0")/../../.." && pwd)
D=$R/docs/agentic_RL/repo_harness_rh2_workstreams
KEY=$HOME/.ssh/vastai_ed25519
SSH=(ssh -o BatchMode=yes -o IdentitiesOnly=yes -o ServerAliveInterval=30 -i "$KEY" "root@$HOST")
RSYNC_E="ssh -o BatchMode=yes -o IdentitiesOnly=yes -i $KEY"
DTOKEN=$(python3 -c "import re,sys;m=re.search(r'(dckr_pat_[A-Za-z0-9_\-]+)',open(sys.argv[1]).read());print(m.group(1) if m else '')" "$D/project1_execution/tmp/API.md")
[ -n "$DTOKEN" ] || { echo "API.md 缺 docker token"; exit 1; }

echo "== 1. Docker（官方 apt 源）与工具"
"${SSH[@]}" 'set -e; export DEBIAN_FRONTEND=noninteractive
command -v docker >/dev/null || { apt-get update -qq; apt-get install -y -qq ca-certificates curl >/dev/null
  install -m 0755 -d /etc/apt/keyrings; curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release; echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -qq; apt-get install -y -qq docker-ce docker-ce-cli containerd.io >/dev/null; }
apt-get install -y -qq tmux jq git rsync xz-utils python3-venv >/dev/null
mkdir -p /work/code /work/secrets /work/task2/{cc,recipes,derived,replay,runs,logs} && chmod 700 /work/secrets
docker --version; docker info 2>/dev/null | grep -E "Storage Driver|Cgroup Version|Docker Root"'
printf '%s' "$DTOKEN" | "${SSH[@]}" "docker login -u $DHUB_USER --password-stdin >/dev/null && echo docker_login_ok"

echo "== 2. 同步代码与数据"
rsync -az --delete -e "$RSYNC_E" --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' --exclude '.ruff_cache' "$R/rh2/" "root@$HOST:/work/code/rh2/"
"${SSH[@]}" "mkdir -p /work/code/docs/agentic_RL/repo_harness_rh2_workstreams"
for sub in s2 data_freeze; do rsync -az --delete -e "$RSYNC_E" "$D/$sub/" "root@$HOST:/work/code/docs/agentic_RL/repo_harness_rh2_workstreams/$sub/"; done
for batch in dvc_install_v1c sqs_v1 install_wave1 compat_v1 pydantic_v1 pandas_meta_v3; do
  [ -d "$R/runs/env_recipe_repair_20260919/$batch/recipes" ] && rsync -az -e "$RSYNC_E" "$R/runs/env_recipe_repair_20260919/$batch/recipes/" "root@$HOST:/work/task2/recipes/$batch/" || true
done

echo "== 3. rh2 运行环境（锁文件）"
"${SSH[@]}" 'command -v uv >/dev/null || [ -x $HOME/.local/bin/uv ] || (curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1); export PATH=$HOME/.local/bin:$PATH; cd /work/code/rh2 && uv sync --locked --group swe --group dev >/dev/null 2>&1; .venv/bin/python -c "import importlib.metadata as m, aiohttp; print(\"swebench\", m.version(\"swebench\"), \"aiohttp\", aiohttp.__version__)"'

echo "== 4. CC 2.1.205 平台包（npm 直取 + integrity）"
"${SSH[@]}" 'set -e; cd /work/task2/cc; f=claude-code-linux-x64-2.1.205.tgz; [ -s $f ] || curl -fsSL -o $f https://registry.npmjs.org/@anthropic-ai/claude-code-linux-x64/-/$f; want=$(curl -fsSL https://registry.npmjs.org/@anthropic-ai/claude-code-linux-x64/2.1.205 | python3 -c "import sys,json; print(json.load(sys.stdin)[\"dist\"][\"integrity\"])"); got="sha512-$(openssl dgst -sha512 -binary $f | base64 -w0)"; [ "$want" = "$got" ] && echo "cc_tarball_integrity_ok $(stat -c %s $f)" || { echo "cc integrity mismatch"; exit 1; }'

echo "== 5. relay 镜像"
"${SSH[@]}" 'docker pull -q python@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea; ip -4 addr show docker0 | grep -o "inet [0-9.]*"; df -h / | tail -1'
echo "== done"
