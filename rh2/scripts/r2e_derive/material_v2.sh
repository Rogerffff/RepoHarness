#!/bin/bash
# rh2 R2E 派生镜像的材料修订步骤 material_v2（2026-09-24 晚）。v1 只能替换已有的隐藏测试文件；v2 另支持新增文件
# （例：scrapy cfed9b66 把随测试搬迁丢掉的夹具 test.egg 放回 r2e_tests/；pandas 4ec87eb9 新增私有 conftest.py；
# 用户批准 T0-5 / T0-6）。v1 脚本保留不改：datalad 58ba5165 的现有派生镜像是用它构建的，配方身份里记着它的摘要。
# 在 recipe_v1.sh 之后以 root 执行，网络关闭，此时隐藏测试已在 /rh2_private/r2e_tests。arg1 = 构建上下文里的 material 目录：
#   manifest.tsv   每行 "<相对 r2e_tests/ 的路径>\t<修订前 sha256 hex，或 - 表示新增>\t<修订后 sha256 hex>"（构建工具按修订单生成）
#   files/<路径>   修订后的全文（可为二进制；ingest 已核对过摘要）
# 对每一行：先核 files/ 里的内容摘要 == 修订后；替换 = 私有目录里原文件摘要 == 修订前 → cat 覆盖（保留原属主与权限）；
# 新增 = 目标原本不存在 → 写入后 root:root 0644。两种都要求写后摘要 == 修订后。任一步不符即非零退出、docker build 失败。
# 不碰 /testbed、不碰清单外的隐藏测试文件。`RH2_MATERIAL_*` 行进 build.log。
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
  case "$REL" in /*|./*|../*|*/./*|*/../*|*/.|*/..|.|..|*__pycache__*) die "unsafe_path:$REL" ;; esac
  SRC="$MAT/files/$REL"
  [ -f "$SRC" ] && [ ! -L "$SRC" ] || die "revised_file_missing:$REL"
  [ "$(sha256sum "$SRC" | cut -d' ' -f1)" = "$AFTER" ] || die "revised_file_mismatch:$REL"
  TGT="$PRIVATE_TESTS/$REL"
  if [ "$BEFORE" = "-" ]; then
    [ ! -e "$TGT" ] && [ ! -L "$TGT" ] || die "add_target_exists:$REL"
    mkdir -p "$(dirname "$TGT")"
    cat "$SRC" > "$TGT"
    chown root:root "$TGT"
    chmod 0644 "$TGT"
    say "ADDED=$REL"
  else
    [ -f "$TGT" ] && [ ! -L "$TGT" ] || die "target_missing:$REL"
    [ "$(sha256sum "$TGT" | cut -d' ' -f1)" = "$BEFORE" ] || die "before_mismatch:$REL"
    cat "$SRC" > "$TGT"
    say "APPLIED=$REL"
  fi
  [ "$(sha256sum "$TGT" | cut -d' ' -f1)" = "$AFTER" ] || die "after_mismatch:$REL"
  N=$((N + 1))
done < "$MAT/manifest.tsv"
[ "$N" -ge 1 ] || die "nothing_applied"
find "$PRIVATE_TESTS" -type d -name __pycache__ -prune -exec rm -rf {} +
say "TREE=$(cd "$PRIVATE_TESTS" && find . -type f -not -path '*/__pycache__/*' -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)"
say "OK=1"
