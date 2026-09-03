#!/usr/bin/env bash
# W3b / H7：在 GPU 主机的正式 profile 上**复跑**同一组确定性最小边界探针（不在租期设计新探针）。
#
# 做的事（与 bringup 启动时调用的是同一个入口 `verify_sandbox_profiles`，不复制第二套规则）：
#   1. 起本 run 的 egress relay（默认 bridge，只转发到 --upstream-host:--upstream-port）；
#   2. 用真实任务镜像起一个 rollout 容器（isolated internal 网络 + 全部 profile 参数）与一个 grader 容器；
#   3. 跑本目录里的探针脚本：rollout-trusted-init / git-sanitize / git-future-probe / rollout-prelaunch-probe /
#      rollout-extended-probe / storage-quota-probe / grader-trusted-init / grader-prelaunch-probe；
#   4. 写 <out>/runtime_profile.json（digest + 参数 + 每项实际值），任一必需项不符即非零退出；
#   5. 清掉自己起的容器与网络。
#
# 用法：
#   RH2_SANDBOX_*/RH2_GRADER_* 环境变量与训练 launch 同一份（数值归 C），然后
#   bash rh2/scripts/sandbox_probes/h7_boundary_probes.sh <任务镜像> <上游地址> <上游端口> <输出目录> [--expect-upstream-http]
# 例：
#   bash rh2/scripts/sandbox_probes/h7_boundary_probes.sh sweb.eval.x86_64.django_1776_django-11099:latest 172.17.0.1 18001 /root/h7 --expect-upstream-http
#
# 本目录的 *.sh 只是探针脚本的**离线副本**（`python -m repoharness2.adapters.slime.sandbox_profile dump-probes`
# 生成；tests/adapters/test_w3b_sandbox_profile.py 断言与包内文本一致），执行时由 verify 入口按容器内
# 身份（root / agent / 候选执行用户）分别 `docker exec` 注入，不要手工在宿主上跑它们。
set -euo pipefail
IMAGE="${1:?任务镜像}"; UPSTREAM_HOST="${2:?上游地址}"; UPSTREAM_PORT="${3:?上游端口}"; OUT="${4:?输出目录}"
shift 4
PY="${RH2_PYTHON:-python3}"
exec "$PY" -m repoharness2.adapters.slime.sandbox_profile verify \
  --image "$IMAGE" --upstream-host "$UPSTREAM_HOST" --upstream-port "$UPSTREAM_PORT" --out "$OUT" \
  --run-id "h7-$(date -u +%Y%m%dT%H%M%SZ)" "$@"
