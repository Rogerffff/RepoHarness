#!/bin/bash
# e2 之后：modin-6937 零解析（pytest 在第一条测试前静默退出 rc=1）的定向探针。fresh 容器 + grader profile 同参数，
# 分开捕获 stderr、读 cgroup memory.events / pids，并对比放宽 shm（1 GiB）与 pids（4096）后的表现。只诊断，不评分。
set -o pipefail
E=/work/replay; OUT=$E/probe_modin; mkdir -p $OUT
IMG=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep "modin-6937" | head -1)
echo "image=$IMG"
run_variant() {  # name, extra docker args
  local name=$1; shift
  local c=rh2-probe-modin-$name-$$
  docker run -d --name $c --network none --cpus 2 --memory 4g --pids-limit ${PIDS:-512} --shm-size ${SHM:-64m} "$@" $IMG sleep infinity >/dev/null
  docker exec $c bash -c 'source /opt/miniconda3/bin/activate && conda activate testbed && cd /testbed && (timeout 600 pytest -n0 -rA modin/pandas/test/test_io.py -x -k "test_read_csv" 2> /tmp/err.txt; echo "RC=$?") ; echo "--- stderr tail"; tail -40 /tmp/err.txt; echo "--- memory.events"; cat /sys/fs/cgroup/memory.events 2>/dev/null; echo "--- pids"; cat /sys/fs/cgroup/pids.current /sys/fs/cgroup/pids.max 2>/dev/null; echo "--- engine"; python -c "import modin.config as c; print(c.Engine.get(), c.StorageFormat.get())" 2>&1 | tail -2' > $OUT/$name.log 2>&1
  docker inspect -f '{{.State.OOMKilled}}' $c >> $OUT/$name.log
  docker rm -f $c >/dev/null
  echo "== $name"; grep -E "^RC=|OOM|oom_kill|Ray|ray|shm|memory|Error|error" $OUT/$name.log | head -20
}
run_variant default
SHM=1g run_variant shm1g
PIDS=4096 run_variant pids4096
echo PROBE_MODIN_DONE
