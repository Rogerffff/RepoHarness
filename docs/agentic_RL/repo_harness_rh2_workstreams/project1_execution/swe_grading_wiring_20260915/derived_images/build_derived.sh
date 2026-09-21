#!/bin/bash
# 在机器上执行：等待基础镜像就绪 → 关 metacopy（B 线发现 chown/chmod → commit 在 metacopy 下内容全 0）→ 构建三个诊断镜像
# → 逐镜像做内容完整性对照（基础镜像与派生镜像里若干原有文件的 sha256 必须相同）→ 记录 image ID → 开回 metacopy。
set -u
cd "$(dirname "$0")"
declare -A BASE=( [moto-6913]=xingyaoww/sweb.eval.x86_64.getmoto_s_moto-6913:latest [pydantic-8500]=xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-8500:latest [monai-1121]=xingyaoww/sweb.eval.x86_64.project-monai_s_monai-1121:latest )
for k in "${!BASE[@]}"; do until docker image inspect "${BASE[$k]}" >/dev/null 2>&1; do sleep 30; done; done
echo "metacopy_before=$(cat /sys/module/overlay/parameters/metacopy)"; echo N > /sys/module/overlay/parameters/metacopy; echo "metacopy_build=$(cat /sys/module/overlay/parameters/metacopy)"
CHECK='sha256sum /opt/miniconda3/envs/testbed/bin/python3 /opt/miniconda3/envs/testbed/lib/libpython3*.so* /testbed/setup.py 2>/dev/null | cut -d" " -f1 | paste -sd,'
: > images.json; echo "{" >> images.json
for k in "${!BASE[@]}"; do
  tag="rh2-derived/$k:$(date +%Y%m%d)"
  echo "=== build $k -> $tag"
  if docker build --network host -t "$tag" -f "Dockerfile.$k" . > "build_$k.log" 2>&1; then
    base_sum=$(docker run --rm --network none "${BASE[$k]}" bash -c "$CHECK")
    der_sum=$(docker run --rm --network none "$tag" bash -c "$CHECK")
    id=$(docker image inspect -f '{{.Id}}' "$tag")
    ok=$([ "$base_sum" = "$der_sum" ] && echo true || echo false)
    echo "  integrity_same=$ok id=$id"
    echo "  \"$k\": {\"tag\": \"$tag\", \"image_id\": \"$id\", \"integrity_same\": $ok, \"base\": \"${BASE[$k]}\"}," >> images.json
  else
    echo "  BUILD_FAILED (see build_$k.log)"; tail -5 "build_$k.log"
    echo "  \"$k\": {\"tag\": \"$tag\", \"build_failed\": true}," >> images.json
  fi
done
echo "  \"_done\": true }" >> images.json
echo Y > /sys/module/overlay/parameters/metacopy; echo "metacopy_after=$(cat /sys/module/overlay/parameters/metacopy)"
echo DERIVED_DONE
