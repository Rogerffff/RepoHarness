#!/usr/bin/env bash
# x86 探针机一键准备（在本机执行；目标是一台干净的 Ubuntu 22.04 VM，有 Docker）。
# 用法：bootstrap_box.sh <ssh_port> <host> [docker_hub_user]
#   需要本机存在：~/.ssh/vastai_ed25519、仓库根下的 s2 产物；Docker Hub token 从 API.md 读取（不回显）。
# 不做的事：不拉镜像、不跑评分、不上传 DeepSeek key（阶段 1 不需要）。
set -euo pipefail
PORT=${1:?ssh port}; HOST=${2:?host}; DHUB_USER=${3:-fangjianju666}
R=$(cd "$(dirname "$0")/../../.." && pwd)
D=$R/docs/agentic_RL/repo_harness_rh2_workstreams
SSH="ssh -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -i $HOME/.ssh/vastai_ed25519 -p $PORT root@$HOST"
TOKEN=$(python3 - "$D/project1_execution/tmp/API.md" <<'PY'
import re,sys
t=open(sys.argv[1]).read()
m=re.search(r'(dckr_pat_[A-Za-z0-9_\-]+)', t); print(m.group(1) if m else "")
PY
)
[ -n "$TOKEN" ] || { echo "docker hub token not found in API.md"; exit 1; }

echo "== 1. 机器事实"; $SSH 'uname -m; nproc; free -g | sed -n 2p; df -h / | tail -1; docker --version; cat /sys/fs/cgroup/cgroup.controllers'
echo "== 2. docker login + 工具"; echo "$TOKEN" | $SSH "docker login -u $DHUB_USER --password-stdin >/dev/null && export DEBIAN_FRONTEND=noninteractive && apt-get update -qq && apt-get install -y -qq tmux jq python3-venv python3-pip git rsync curl xz-utils >/dev/null && mkdir -p /work/data /work/logs /work/ledger /work/code /work/tarballs && echo tools_ok"
echo "== 3. venv + 官方 fork (pin 242429c1)"; $SSH 'cd /work && [ -x venv/bin/python ] || python3 -m venv venv; ./venv/bin/pip install -q --upgrade pip; ./venv/bin/pip install -q "git+https://github.com/SWE-Gym/SWE-Bench-Fork.git@242429c188fcfd06aad13fce9a54d450470bf0ac" pyarrow huggingface_hub; ./venv/bin/python -c "from swebench.harness import log_parsers as lp; print(\"fork ok\", len(lp.MAP_REPO_TO_PARSER))"'
echo "== 4. 数据与代码同步"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
# 阶段一重放已验证的旧题单。final_sync 只有最终日志；完整输入在 codex_backup/data。
DATA_SOURCE="$R/runs/env_probe_20260909_codex_backup/data"
for f in public_bundles_v0.jsonl grading_bundles_v2_v0.jsonl validation_bundles_v0.jsonl swe_gym_lite_full_f70b1a29.jsonl image_manifest_keyed.json candidate_manifest.jsonl swegym_core12.txt swegym_backup12.txt swegym_all216.txt swegym_keep24.txt; do
  cp "$DATA_SOURCE/$f" "$TMP/"
done
rsync -az -e "ssh -o BatchMode=yes -o IdentitiesOnly=yes -i $HOME/.ssh/vastai_ed25519 -p $PORT" "$TMP/" root@$HOST:/work/data/
rsync -az -e "ssh -o BatchMode=yes -o IdentitiesOnly=yes -i $HOME/.ssh/vastai_ed25519 -p $PORT" "$R/rh2/experiments/env_probe_20260909/" root@$HOST:/work/code/
rm -rf "$TMP"
$SSH 'cd /work && ls data | wc -l && ./venv/bin/python -c "import ast; [ast.parse(open(f).read()) for f in (\"code/swegym_probe.py\",\"code/r2e_probe.py\",\"code/diff_runs.py\")]; print(\"code ok\")"; [ -f /work/data/swegym_all216.txt ] || ./venv/bin/python - <<'"'"'PY'"'"'
import json
ids=[json.loads(l)["instance_id"] for l in open("/work/data/grading_bundles_v2_v0.jsonl")]
open("/work/data/swegym_all216.txt","w").write("\n".join(ids)+"\n"); print("all216 list rebuilt")
PY'
echo "== done. 阶段 1 主批命令见 cpu_followup_stages_20260910.md 附录。"
