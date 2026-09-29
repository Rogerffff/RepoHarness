#!/usr/bin/env bash
# sysconfig_v1.sh（2026-09-29，R2E 单题闭环试行；统一标准 v1 R-d，用户 09-25 批准"C 扩展重建可以修"）
#
# recipe_v1 把 uv 解释器从 /root/.local/share/uv/python/<PYDIR> 复制到 /opt/py/<PYDIR>，但解释器自带的构建配置
# 仍写着 /root 下的原前缀：_sysconfigdata_*.py 里的 prefix / LIBDIR / LIBPL / INCLUDEPY 等，以及 lib/pkgconfig/*.pc。
# 解题身份（uid 54321）读不到 /root（700），编译扩展时链接器报 `cannot find -lpython3.7m`（orange3 4014f248 实测）。
#
# 本步只把 /opt/py/<PYDIR> 内文本文件里的旧前缀改成新位置，再以 root 重编被改的 _sysconfigdata 字节码。
# 不动 /testbed、.venv 与 /root，不装包，不改入口；二进制文件不改。做完后若仍有文本文件含旧前缀即失败。
set -euo pipefail
UVROOT=/root/.local/share/uv/python
die() { echo "sysconfig_v1: $*" >&2; exit 1; }

[ -d /opt/py ] || die "opt_py_missing"
mapfile -t DIRS < <(find /opt/py -mindepth 1 -maxdepth 1 -type d -printf '%f\n')
[ "${#DIRS[@]}" -eq 1 ] || die "expected_one_pydir:${#DIRS[@]}"
PYDIR=${DIRS[0]}
OLD="$UVROOT/$PYDIR"
NEW="/opt/py/$PYDIR"

mapfile -t FILES < <(grep -rlI --exclude-dir=__pycache__ -F "$OLD" "$NEW" 2>/dev/null || true)
echo "sysconfig_v1: files_with_old_prefix=${#FILES[@]}"
for f in "${FILES[@]}"; do
    [ -L "$f" ] && continue
    sed -i "s#$OLD#$NEW#g" "$f"
    echo "sysconfig_v1: rewrote ${f#"$NEW"/}"
done

# 旧字节码按源码 mtime 自动失效；这里以 root 重编一次，免得解题身份每次导入都在内存里重新编译
"$NEW/bin/python3" - "$NEW" <<'PY'
import glob
import py_compile
import sys

for path in glob.glob(sys.argv[1] + "/lib/python3*/_sysconfigdata*.py"):
    py_compile.compile(path, doraise=True)
PY

# grep 无命中返回 1，set -e + pipefail 下要显式放行（与 recipe_v1.sh 同一个坑）
LEFT=$( { grep -rlI --exclude-dir=__pycache__ -F "$OLD" "$NEW" 2>/dev/null || true; } | wc -l)
[ "$LEFT" -eq 0 ] || die "old_prefix_left:$LEFT"
chmod -R a+rX "$NEW"
echo "sysconfig_v1: ok"
