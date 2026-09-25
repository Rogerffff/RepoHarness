#!/bin/bash
# rh2 R2E 派生镜像的环境配方步骤 env_v2（2026-09-24 夜）。与 env_v1 只差"怎么读包版本"：env_v1 用
# `importlib.metadata`，它从 Python 3.8 起才有；orange3 9b5494e2 的解释器是 3.7.9，env_v1 装完 wheel 核版本时报
# ModuleNotFoundError。env_v2 改用下面 CODE 里只依赖标准库的读法：按 sys.path 逐项找 *.dist-info/METADATA 与
# *.egg-info 的 Name/Version；装完后同名分发必须恰好一份、且版本等于配方（两份会打印成 "a,b"，按不符处理）。
# CODE 与 build_r2e_derived.py 的 DIST_VERSIONS_PY 逐字相同（测试核对）。
# env_v1.sh 保留不改：numpy 43e333e2 的现有派生镜像按 +env_v1 构建，配方身份里记着它的摘要。
# 其余与 env_v1 相同：在 recipe_v1.sh（与材料步骤）之后以 root 执行，网络关闭。arg1 = 构建上下文里的 env 目录：
#   manifest.tsv  每行 "<分发名>\t<版本>\t<wheel 文件名>\t<wheel sha256 hex>"（构建工具按配方生成）
#   wheels/<文件名>（构建工具在宿主侧下载并核过摘要）
# 对每一行：再核一次 wheel 摘要 → 用镜像自带的 uv 离线安装（--no-deps --no-index --offline --no-cache）→ 核安装后的版本。
# 不碰 /testbed 工作树与隐藏测试。`RH2_ENV_*` 行进 build.log。
set -euo pipefail
ENV_DIR="${1:?env dir required}"
PY=/testbed/.venv/bin/python
UV=/root/.local/bin/uv
say() { echo "RH2_ENV_$1"; }
die() { say "ERROR=$1"; exit 3; }
CODE=$(cat <<'PYEOF'
import os, re, sys
def norm(n):
    return re.sub(r"[-_.]+", "-", n).lower()
seen, found = set(), {}
for entry in sys.path:
    base = entry or os.getcwd()
    try:
        names = sorted(os.listdir(base))
    except OSError:
        continue
    for name in names:
        path = os.path.join(base, name)
        if name.endswith(".dist-info"):
            meta = os.path.join(path, "METADATA")
        elif name.endswith(".egg-info"):
            meta = os.path.join(path, "PKG-INFO") if os.path.isdir(path) else path
        else:
            continue
        real = os.path.realpath(meta)
        if real in seen or not os.path.isfile(meta):
            continue
        seen.add(real)
        fields = {}
        with open(meta, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    break
                key, sep, value = line.partition(":")
                if sep and key in ("Name", "Version") and key not in fields:
                    fields[key] = value.strip()
        found.setdefault(norm(fields.get("Name", "")), []).append(fields.get("Version", "?"))
for dist in sys.argv[1:]:
    print(dist + "=" + (",".join(found.get(norm(dist), [])) or "absent"))
PYEOF
)
ver_of() { local out; out=$("$PY" -c "$CODE" "$1") || return 1; echo "${out#*=}"; }
[ -x "$UV" ] || die "no_uv"
[ -f "$ENV_DIR/manifest.tsv" ] || die "no_manifest"
N=0
while IFS=$'\t' read -r DIST VER WHEEL SHA; do
  [ -n "$DIST" ] || continue
  W="$ENV_DIR/wheels/$WHEEL"
  [ -f "$W" ] || die "wheel_missing:$WHEEL"
  [ "$(sha256sum "$W" | cut -d' ' -f1)" = "$SHA" ] || die "wheel_sha_mismatch:$WHEEL"
  BEFORE=$(ver_of "$DIST" 2>/dev/null || echo unknown)
  "$UV" pip install --python "$PY" --no-deps --no-index --offline --no-cache "$W" >/dev/null 2>&1 || die "install_failed:$DIST"
  AFTER=$(ver_of "$DIST") || die "version_probe_failed:$DIST"
  [ "$AFTER" = "$VER" ] || die "version_mismatch:$DIST:$AFTER"
  say "PINNED=$DIST:$BEFORE->$AFTER"
  N=$((N + 1))
done < "$ENV_DIR/manifest.tsv"
[ "$N" -ge 1 ] || die "nothing_pinned"
say "OK=1"
