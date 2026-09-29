#!/usr/bin/env bash
# 只在本批专用 CPU 机器上执行。源码已经单独冻结；所有下载均在远端完成。
set -euo pipefail
ROOT=/work/swegym_cpu_preprobe_20260929
mkdir -p "$ROOT"/{setup,cc,inputs,results,logs}
exec > >(tee -a "$ROOT/setup/bootstrap.log") 2>&1
trap 'rc=$?; printf "%s\n" "$rc" > "$ROOT/setup/bootstrap.rc"' EXIT
date -u +%FT%TZ > "$ROOT/setup/started_at"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git rsync curl jq xz-utils python3-venv python3-pip
if ! [ -x /root/.local/bin/uv ]; then
  curl -fsSL https://astral.sh/uv/install.sh -o "$ROOT/setup/install_uv.sh"
  sh "$ROOT/setup/install_uv.sh"
fi
export PATH=/root/.local/bin:$PATH
uv --version
cd "$ROOT/code_v1/rh2"
uv sync --locked --python 3.12 --group swe --group dev
.venv/bin/python -c 'import importlib.metadata as m; print({p: m.version(p) for p in ("swebench", "verifiers", "pydantic", "torch")})'
uv pip freeze > "$ROOT/setup/python_freeze.txt"
cd "$ROOT/cc"
f=claude-code-linux-x64-2.1.205.tgz
curl -fsSL -o "$f" "https://registry.npmjs.org/@anthropic-ai/claude-code-linux-x64/-/$f"
curl -fsSL -o npm_metadata.json https://registry.npmjs.org/@anthropic-ai/claude-code-linux-x64/2.1.205
python3 - <<'PY'
import hashlib, json, base64
from pathlib import Path
p=Path('claude-code-linux-x64-2.1.205.tgz')
want=json.loads(Path('npm_metadata.json').read_text())['dist']['integrity']
got='sha512-'+base64.b64encode(hashlib.sha512(p.read_bytes()).digest()).decode()
assert got==want, (got,want)
Path('integrity.json').write_text(json.dumps({'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'integrity':got,'bytes':p.stat().st_size},indent=2)+'\n')
print('CC 2.1.205 integrity verified')
PY
docker pull -q python@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea
cd "$ROOT/code_v1/rh2"
.venv/bin/python -m pytest tests/envpack/test_vendor_specs.py tests/envpack/test_swegym_parsers.py -q > "$ROOT/setup/source_checks.log" 2>&1
date -u +%FT%TZ > "$ROOT/setup/finished_at"
