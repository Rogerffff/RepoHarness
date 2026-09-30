#!/usr/bin/env bash
# 开发路径的等效核对（私有、断网、一次性容器；不是正式 actor 入口）。
# 正式入口要 CC 2.1.205 与桩端点（devcheck.py），云端没有；这里在同一镜像内按 actor_dask8597_v1 的做法
# （公开镜像 + 离线 pytest 7.4.4，同一 wheel sha256）装好开发依赖，再以 UID 54321 逐条执行
# task2_swegym_dev_20260925/commands/dask__dask-8597.json 的 5 条开发命令；之后模拟一次源码修改，
# 核对解题者能看到的实际数组（shape、dtype、类型、三种 split 配置）。原公开镜像（pytest 8.3.2）另跑 narrow 作对照。
# 用法：devpath_check.sh <输出目录>
set -uo pipefail
OUT=$1; mkdir -p "$OUT"
ROOT=/home/user/RepoHarness
E=$ROOT/rh2/experiments/category3_cloud_20260929/dask8597
CMDS=$ROOT/rh2/experiments/task2_swegym_dev_20260925/commands/dask__dask-8597.json
GOLD=$ROOT/runs/category3_cloud_20260929/dask8597/gold/dask__dask-8597.gold.patch
PY=/opt/miniconda3/envs/testbed/bin
run_cmds() {  # $1=容器名 $2=输出前缀
  python3 - "$CMDS" <<'PY' > "$OUT/.cmds.tsv"
import json, sys
for c in json.load(open(sys.argv[1])):
    print(c["id"] + "\t" + str(c["timeout_s"]) + "\t" + c["expect"] + "\t" + c["cmd"])
PY
  while IFS=$'\t' read -r id t expect cmd; do
    docker exec -u 54321:54321 -e HOME=/tmp/agent-home -e PATH=$PY:/usr/local/bin:/usr/bin:/bin -w /testbed "$1" \
      timeout "$t" bash -c "$cmd" > "$OUT/$2_$id.out" 2>&1
    echo "$2 $id rc=$? expect=$expect" | tee -a "$OUT/summary.txt"
  done < "$OUT/.cmds.tsv"
  rm -f "$OUT/.cmds.tsv"
}
: > "$OUT/summary.txt"
while [ "$(docker ps -q | wc -l)" -ge 3 ]; do sleep 20; done
# (1) actor 等效：派生镜像 + root 离线装 pytest 7.4.4（与 actor_dask8597_v1 相同的 pin 与 wheel）
N=c3b2-dask8597-devpath-$$
docker run -d --name $N --network none --entrypoint sleep rh2-envrepair/compat-v1-dask__dask-8597:c3cloud infinity > /dev/null
docker exec $N bash -c "$PY/python -m pip install -q --no-index --find-links=/opt/rh2/compat-wheels --no-deps pytest==7.4.4 && $PY/python -m pip check; sha256sum /opt/rh2/compat-wheels/*.whl; mkdir -p /tmp/agent-home && chown 54321:54321 /tmp/agent-home && chown -R 54321:54321 /testbed" > "$OUT/actor_setup.out" 2>&1
echo "actor_setup rc=$? (pip check 预期仍报 base 原有的 distributed/dask 版本冲突)" | tee -a "$OUT/summary.txt"
run_cmds $N actor
# (2) 以 UID 54321 模拟一次源码修改（gold），核对解题者能看到的实际数组
docker cp "$GOLD" $N:/tmp/edit.patch
docker exec -u 54321:54321 -e HOME=/tmp/agent-home -e PATH=$PY:/usr/local/bin:/usr/bin:/bin -w /testbed $N bash -c '
git apply /tmp/edit.patch && git status --porcelain && python - <<"PYX"
import warnings, numpy as np, dask, dask.array as da
warnings.simplefilter("error")
for split in (None, False, True):
    with dask.config.set({"array.slicing.split-large-chunks": split}):
        for xn, idx in [(np.zeros((3, 0)), ([0],)), (np.zeros((0, 3)), (slice(None), [2, 0])), (np.zeros((6, 0, 4), dtype="i4"), ([5, 0, 5],))]:
            r = da.from_array(xn, chunks=2)[idx]
            c = r.compute()
            print(split, xn.shape, idx, type(r).__name__, r.shape, r.dtype, "->", type(c).__name__, c.shape, c.dtype, "numpy:", xn[idx].shape, xn[idx].dtype)
PYX
' > "$OUT/actor_after_edit.out" 2>&1
echo "actor_after_edit rc=$?" | tee -a "$OUT/summary.txt"
docker rm -f $N > /dev/null
# (3) 对照：原公开镜像（pytest 8.3.2）上同一 narrow 命令
while [ "$(docker ps -q | wc -l)" -ge 3 ]; do sleep 20; done
N2=c3b2-dask8597-devpath-orig-$$
docker run -d --name $N2 --network none --entrypoint sleep c3keep/dask8597:src infinity > /dev/null
docker exec $N2 bash -c "mkdir -p /tmp/agent-home && chown 54321:54321 /tmp/agent-home && chown -R 54321:54321 /testbed"
run_cmds $N2 origimage
docker rm -f $N2 > /dev/null
echo done | tee -a "$OUT/summary.txt"
