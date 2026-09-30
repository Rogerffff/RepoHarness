#!/usr/bin/env bash
# 相邻既有缺陷的探针（私有、断网、一次性容器，base 镜像，未打补丁）：
# 用自动分块创建零大小数组时，auto_chunks 在某个规模以上自身除零并发 RuntimeWarning。
# 另记录 array.chunk-size 默认值（dask/array/core.py:81 设为 128MiB）与 1kB、0.1Mb 的字节数。
# 用法：probe_auto_chunks.sh <输出文件>
set -uo pipefail
OUT=$1; mkdir -p "$(dirname "$OUT")"
while [ "$(docker ps -q | wc -l)" -ge 3 ]; do sleep 20; done
docker run --rm --network none c3keep/dask8597:src bash -c 'cd /testbed && /opt/miniconda3/envs/testbed/bin/python -c "
import warnings, numpy as np, dask, dask.array as da
from dask import utils
print(\"chunk-size default:\", dask.config.get(\"array.chunk-size\"), utils.parse_bytes(dask.config.get(\"array.chunk-size\")), \"1kB:\", utils.parse_bytes(\"1kB\"), \"0.1Mb:\", utils.parse_bytes(\"0.1Mb\"))
def warns(make):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter(\"always\")
        make()
    return [x.category.__name__ + \": \" + str(x.message)[:50] for x in w]
for n in [100, 120, 1000, 1200, 2000, 4000, 5000, 8000, 12000, 100000]:
    print(\"from_array(np.zeros((%d, 0)))\" % n, warns(lambda: da.from_array(np.zeros((n, 0)))))
print(\"from_array(np.zeros((0, 12000)))\", warns(lambda: da.from_array(np.zeros((0, 12000)))))
print(\"da.zeros((12000, 0))\", warns(lambda: da.zeros((12000, 0))))
print(\"from_array(np.zeros((12000, 0)), chunks=-1)\", warns(lambda: da.from_array(np.zeros((12000, 0)), chunks=-1)))
"' > "$OUT" 2>&1
cat "$OUT"
