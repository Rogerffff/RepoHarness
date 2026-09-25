#!/bin/bash
# rh2 R2E 派生镜像的材料修订步骤 material_v1（2026-09-24）。只用于带"隐藏测试修订"的题（例：r2e-mr-002，
# datalad 58ba5165 的 test_1.py 改一行导入；用户批准 T0-2）。在 recipe_v1.sh 之后以 root 执行，网络关闭，
# 此时隐藏测试已在 /rh2_private/r2e_tests。arg1 = 构建上下文里的 material 目录：
#   manifest.tsv   每行 "<相对 r2e_tests/ 的路径>\t<修订前 sha256 hex>\t<修订后 sha256 hex>"（由构建工具按修订单生成）
#   files/<路径>   修订后的全文（取自 s2_r2e/revisions/files/…，ingest 已核对过摘要）
# 对每一行：私有目录里的原文件摘要 == 修订前 → 覆盖写入（cat 覆盖，保留原属主与权限）→ 摘要 == 修订后。任一步不符
# 即非零退出、docker build 失败。不碰 /testbed、不碰其它隐藏测试文件。`RH2_MATERIAL_*` 行进 build.log。
set -euo pipefail
MAT="${1:?material dir required}"
PRIVATE_TESTS=/rh2_private/r2e_tests
say() { echo "RH2_MATERIAL_$1"; }
die() { say "ERROR=$1"; exit 3; }
[ -d "$PRIVATE_TESTS" ] || die "no_private_tests"
[ -f "$MAT/manifest.tsv" ] || die "no_manifest"
N=0
while IFS=$'\t' read -r REL BEFORE AFTER; do
  [ -n "$REL" ] || continue
  case "$REL" in /*|../*|*/../*|*/..|..) die "unsafe_path:$REL" ;; esac
  TGT="$PRIVATE_TESTS/$REL"
  [ -f "$TGT" ] && [ ! -L "$TGT" ] || die "target_missing:$REL"
  [ "$(sha256sum "$TGT" | cut -d' ' -f1)" = "$BEFORE" ] || die "before_mismatch:$REL"
  [ "$(sha256sum "$MAT/files/$REL" | cut -d' ' -f1)" = "$AFTER" ] || die "revised_file_mismatch:$REL"
  cat "$MAT/files/$REL" > "$TGT"
  [ "$(sha256sum "$TGT" | cut -d' ' -f1)" = "$AFTER" ] || die "after_mismatch:$REL"
  say "APPLIED=$REL"
  N=$((N + 1))
done < "$MAT/manifest.tsv"
[ "$N" -ge 1 ] || die "nothing_applied"
find "$PRIVATE_TESTS" -type d -name __pycache__ -prune -exec rm -rf {} +
say "TREE=$(cd "$PRIVATE_TESTS" && find . -type f -not -path '*/__pycache__/*' -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)"
say "OK=1"
