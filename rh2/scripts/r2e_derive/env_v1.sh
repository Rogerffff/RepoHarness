#!/bin/bash
# rh2 R2E 派生镜像的环境配方步骤 env_v1（2026-09-24）。只用于环境配方里登记了依赖固定的题（例：numpy 43e333e2 把
# hypothesis 固定回仓库自己 test_requirements.txt 写的 6.24.1——来源镜像装的是不固定版本的 6.124.1，它的弃用警告被
# numpy 的 pytest.ini filterwarnings=error 变成错误，仓库自带测试收集即失败）。在 recipe_v1.sh 之后以 root 执行，
# 网络关闭。arg1 = 构建上下文里的 env 目录：
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
[ -x "$UV" ] || die "no_uv"
[ -f "$ENV_DIR/manifest.tsv" ] || die "no_manifest"
N=0
while IFS=$'\t' read -r DIST VER WHEEL SHA; do
  [ -n "$DIST" ] || continue
  W="$ENV_DIR/wheels/$WHEEL"
  [ -f "$W" ] || die "wheel_missing:$WHEEL"
  [ "$(sha256sum "$W" | cut -d' ' -f1)" = "$SHA" ] || die "wheel_sha_mismatch:$WHEEL"
  BEFORE=$("$PY" -c "import importlib.metadata as m; print(m.version('$DIST'))" 2>/dev/null || echo absent)
  "$UV" pip install --python "$PY" --no-deps --no-index --offline --no-cache "$W" >/dev/null 2>&1 || die "install_failed:$DIST"
  AFTER=$("$PY" -c "import importlib.metadata as m; print(m.version('$DIST'))")
  [ "$AFTER" = "$VER" ] || die "version_mismatch:$DIST:$AFTER"
  say "PINNED=$DIST:$BEFORE->$AFTER"
  N=$((N + 1))
done < "$ENV_DIR/manifest.tsv"
[ "$N" -ge 1 ] || die "nothing_pinned"
say "OK=1"
