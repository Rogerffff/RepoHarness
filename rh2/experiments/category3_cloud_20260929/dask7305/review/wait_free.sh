#!/usr/bin/env bash
# 共用机器规则：运行中的容器 >= 3 时等待（每 10 秒查一次，最多 30 分钟）。
for i in $(seq 1 180); do
  n=$(docker ps -q | wc -l)
  if [ "$n" -lt 3 ]; then exit 0; fi
  python3 -c "import time; time.sleep(10)"
done
echo "wait_free: still >=3 containers after 30 min" >&2
exit 1
