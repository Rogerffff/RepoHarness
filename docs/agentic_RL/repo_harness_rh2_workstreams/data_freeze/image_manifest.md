# DF-6 镜像清单与本地 registry 同步方案

## 产物范围

本次只生成和查询镜像 manifest，没有执行任何全量 `docker pull`。

已生成文件：

| 文件 | 来源 | 行数 | 说明 |
|---|---:|---:|---|
| `meta/image_refs_swegym.txt` | `meta/swe_gym_full.jsonl` | 2438 | SWE-Gym Full 全量镜像引用；Lite 的 230 条是 Full 子集，未另写独立清单。 |
| `meta/image_refs_r2e.txt` | `meta/r2e_subset.jsonl` | 4578 | R2E 镜像引用，直接使用 `docker_image` 字段。 |

SWE-Gym 生成命令形态：

```bash
jq -r '"xingyaoww/sweb.eval.x86_64." + (.instance_id | ascii_downcase | gsub("__"; "_s_")) + ":latest"' \
  meta/swe_gym_full.jsonl > meta/image_refs_swegym.txt
```

R2E 生成命令形态：

```bash
jq -r '.docker_image' meta/r2e_subset.jsonl > meta/image_refs_r2e.txt
```

## SWE-Gym 镜像命名规则实测结论

实测结论：SWE-Gym/OpenHands 发布在 `xingyaoww` 命名空间下的 `sweb.eval.x86_64.*` 镜像没有沿用官方 SWE-Bench 常见的 `_1776_` 替换规则，而是把 `instance_id` 中的双下划线 `__` 替换成 `_s_`，并整体转成小写。

规则为：

```text
xingyaoww/sweb.eval.x86_64. + lower(instance_id).replace("__", "_s_") + :latest
```

实测样例：

| instance_id | 通过的镜像引用 | 查询结果 |
|---|---|---|
| `getmoto__moto-5752` | `xingyaoww/sweb.eval.x86_64.getmoto_s_moto-5752:latest` | Docker Hub API HTTP 200；`docker manifest inspect` 成功；压缩层体积 1,146,016,016 bytes。 |
| `getmoto__moto-7365` | `xingyaoww/sweb.eval.x86_64.getmoto_s_moto-7365:latest` | Docker Hub API HTTP 200；`docker manifest inspect` 成功。 |
| `python__mypy-9903` | `xingyaoww/sweb.eval.x86_64.python_s_mypy-9903:latest` | Docker Hub API HTTP 200。 |
| `Project-MONAI__MONAI-3837` | `xingyaoww/sweb.eval.x86_64.project-monai_s_monai-3837:latest` | Docker Hub API HTTP 200。 |

反例验证：

| 候选形式 | 样例 | 结果 |
|---|---|---|
| 原样保留 `__` | `xingyaoww/sweb.eval.x86_64.getmoto__moto-5752` | Docker Hub tag API 返回 404；`docker manifest inspect` 未取得 manifest。 |
| 替换为 `_1776_` | `xingyaoww/sweb.eval.x86_64.getmoto_1776_moto-5752` | Docker Hub tag API 返回 404；`docker manifest inspect` 未取得 manifest。 |
| 替换为点号 | `xingyaoww/sweb.eval.x86_64.getmoto.moto-5752` | Docker Hub tag API 返回 404；`docker manifest inspect` 未取得 manifest。 |

本次体积查询使用 Docker Hub tag API 的 `full_size` 字段。对 `getmoto_s_moto-5752` 和 R2E 的 `aiohttp_final:4b6ff...` 又用 `docker manifest inspect` 对 `.layers[].size` 求和复核，结果分别与 API 返回的 1,146,016,016 bytes 和 474,398,568 bytes 一致。因此下面的体积表按压缩层体积统计，适合估算 registry 存储和下载量。

## 抽样体积表

抽样方法：

1. SWE-Gym：固定随机种子 `606`，从 `meta/image_refs_swegym.txt` 的 2438 条 Full 清单中随机抽 10 个。
2. R2E：固定随机种子 `606`，因为 `meta/r2e_subset.jsonl` 正好包含 10 个不同 `repo_name`，所以每个仓库随机抽 1 个，保证跨不同仓库。

| 数据集 | 实例或仓库 | 镜像引用 | 压缩体积 bytes | 压缩体积 GiB |
|---|---|---|---:|---:|
| SWE-Gym | `getmoto_s_moto-5406` | `xingyaoww/sweb.eval.x86_64.getmoto_s_moto-5406:latest` | 1,118,933,479 | 1.042 |
| SWE-Gym | `pandas-dev_s_pandas-49637` | `xingyaoww/sweb.eval.x86_64.pandas-dev_s_pandas-49637:latest` | 3,267,304,268 | 3.043 |
| SWE-Gym | `pandas-dev_s_pandas-47747` | `xingyaoww/sweb.eval.x86_64.pandas-dev_s_pandas-47747:latest` | 3,885,316,797 | 3.618 |
| SWE-Gym | `pandas-dev_s_pandas-48702` | `xingyaoww/sweb.eval.x86_64.pandas-dev_s_pandas-48702:latest` | 3,883,970,913 | 3.617 |
| SWE-Gym | `python_s_mypy-14093` | `xingyaoww/sweb.eval.x86_64.python_s_mypy-14093:latest` | 1,046,749,427 | 0.975 |
| SWE-Gym | `pandas-dev_s_pandas-51131` | `xingyaoww/sweb.eval.x86_64.pandas-dev_s_pandas-51131:latest` | 2,958,924,013 | 2.756 |
| SWE-Gym | `bokeh_s_bokeh-13258` | `xingyaoww/sweb.eval.x86_64.bokeh_s_bokeh-13258:latest` | 2,426,472,332 | 2.260 |
| SWE-Gym | `pandas-dev_s_pandas-51335` | `xingyaoww/sweb.eval.x86_64.pandas-dev_s_pandas-51335:latest` | 2,955,512,154 | 2.753 |
| SWE-Gym | `conan-io_s_conan-15422` | `xingyaoww/sweb.eval.x86_64.conan-io_s_conan-15422:latest` | 1,052,474,059 | 0.980 |
| SWE-Gym | `iterative_s_dvc-9246` | `xingyaoww/sweb.eval.x86_64.iterative_s_dvc-9246:latest` | 1,353,094,772 | 1.260 |
| R2E | `aiohttp` | `namanjain12/aiohttp_final:4b6ff686b6d032aff74174e3c96712230172f1c7` | 474,398,568 | 0.442 |
| R2E | `coveragepy` | `namanjain12/coveragepy_final:2e63e41be0774e51b7683457f31500d99c75c9f1` | 291,993,333 | 0.272 |
| R2E | `datalad` | `namanjain12/datalad_final:553892df7fb3c1650f960c70c547342a77527440` | 636,723,408 | 0.593 |
| R2E | `numpy` | `namanjain12/numpy_final:d9c1a1f91a3983469de7086ff589a6aeaa353b3e` | 570,194,695 | 0.531 |
| R2E | `orange3` | `namanjain12/orange3_final:0abb16004532d21fe183b8c905fc8c4f7db57243` | 901,064,717 | 0.839 |
| R2E | `pandas` | `namanjain12/pandas_final:17ad7916b970e7117fcaf36b37e113d6aff9b4fb` | 946,039,614 | 0.881 |
| R2E | `pillow` | `namanjain12/pillow_final:4459dfadcbf5a137d9497e1bfbc325999ef46a63` | 609,290,430 | 0.567 |
| R2E | `pyramid` | `namanjain12/pyramid_final:0a2701247146a57cba33683c6c386a04f51a6fa8` | 365,715,660 | 0.341 |
| R2E | `scrapy` | `namanjain12/scrapy_final:c961438d5d9998344460d930ea502fae40553043` | 371,615,268 | 0.346 |
| R2E | `tornado` | `namanjain12/tornado_final:5eb39608dff69b49ff3219f9016120568d558226` | 351,733,536 | 0.328 |

## 三档磁盘占用外推

单位说明：GiB 和 TiB 都按二进制单位计算，`1 GiB = 1024^3 bytes`，`1 TiB = 1024 GiB`。

| 数据档位 | 样本数 | 样本平均压缩体积 | 样本范围 | 外推镜像数 | 朴素外推压缩体积 |
|---|---:|---:|---:|---:|---:|
| SWE-Gym Lite | 10 个 SWE-Gym Full 样本 | 2.230 GiB | 0.975 到 3.618 GiB | 230 | 512.99 GiB，约 0.501 TiB |
| SWE-Gym Full | 10 个 SWE-Gym Full 样本 | 2.230 GiB | 0.975 到 3.618 GiB | 2438 | 5437.72 GiB，约 5.310 TiB |
| R2E | 10 个跨仓库样本 | 0.514 GiB | 0.272 到 0.881 GiB | 4578 | 2352.98 GiB，约 2.298 TiB |

不确定性说明：

1. 上表是“逐镜像压缩体积求和”的朴素外推。`registry:2` 实际按 content-addressed blob 存储，完全相同 digest 的层只存一份，所以同源镜像之间如果共享大量基础层，实际 registry 占用会低于朴素总和。
2. 反过来，如果用 `docker pull -> docker tag -> docker push` 作为同步路径，中转机器的 Docker daemon 还会产生本地镜像存储和解包后的 snapshot 占用；这部分不等同于 registry 压缩 blob 体积，短时间内可能高于上表。
3. Lite 的 230 条全部是 Full 的子集，但仓库分布不同：Lite 中 `getmoto/moto`、`python/mypy`、`iterative/dvc` 占比更高，Full 中 `pandas-dev/pandas` 和 `Project-MONAI/MONAI` 占比更高。本次 Lite 外推沿用 SWE-Gym Full 抽样均值，只能作为粗估，不应当作为最终容量承诺。
4. 规划磁盘时建议把 registry 数据盘按朴素外推值再预留 30% 到 50% 的余量。如果采用 pull-tag-push 中转，还应给 Docker daemon 的数据目录单独留出临时空间，并在每个批次结束后清理本地 tag。

## Docker Hub 限流规避方案

Docker 官方文档当前说明：Unauthenticated 用户按 IP 地址或 IPv6 `/64` 子网计数；Personal authenticated 用户有每 6 小时 200 次 pull 的限制；Pro、Team、Business authenticated 用户的 pull rate limit 显示为 unlimited，但仍受 fair use 和 abuse rate limit 约束。官方也说明 abuse rate limit 会随负载变化，触发时通常表现为简单的 `429 Too Many Requests`。参考文档：https://docs.docker.com/docker-hub/usage/

建议策略：

1. 同步前执行 `docker login`，不要用匿名 pull 执行 7016 个镜像的批量同步。
2. 如果只能使用 Personal authenticated 账号，批次规模建议控制在 150 到 180 个镜像，每 6 小时最多跑一个批次；7016 个镜像按 180 个一批约需要 39 个批次，时间跨度接近 10 天。
3. 如果使用 Pro、Team 或 Business 账号，仍建议保留每个镜像之间 1 到 3 秒的间隔，并对 `429`、`5xx`、网络超时做指数退避，避免撞上 abuse rate limit。
4. 单机批量同步时不要并发开太大。建议从 `CONCURRENCY=1` 开始；如果连续数小时没有 `429`，再提高到 `2` 或 `4`。对 Docker Hub 来说，大量小镜像并发和少量大镜像并发的风险不同，应该以实际错误率调节。
5. 每个批次结束后记录成功列表和失败列表。失败镜像下一批重试，不要在同一时间窗口内无限重试。
6. 对训练集长期使用，优先把 Docker Hub 作为源站，把本地 registry 作为训练集固定镜像源。训练任务只访问本地 registry，避免每次实验重新消耗 Docker Hub pull 配额。

## 本地 registry:2 同步 runbook

下面是后续真正同步时的执行方案。注意：本次 DF-6 没有执行这些 `docker pull` 命令。

### 1. 启动本地 registry

```bash
export REGISTRY_HOST=localhost:5000
export REGISTRY_DIR=/mnt/repoharness-registry

mkdir -p "$REGISTRY_DIR"

docker run -d \
  --name repoharness-registry \
  --restart unless-stopped \
  -p 5000:5000 \
  -e REGISTRY_STORAGE_DELETE_ENABLED=true \
  -v "$REGISTRY_DIR:/var/lib/registry" \
  registry:2

curl -fsS "http://${REGISTRY_HOST}/v2/" >/dev/null
```

如果训练机器不在同一台主机，建议在局域网内给 registry 配置固定域名和 TLS。只在本机使用时，`localhost:5000` 足够。

### 2. 拆分批次

```bash
mkdir -p batches
split -l 150 meta/image_refs_swegym.txt batches/swegym_
split -l 150 meta/image_refs_r2e.txt batches/r2e_
```

`150` 是面向 Personal authenticated Docker Hub 账号的保守批次大小。如果使用更高等级账号，可以把批次调大，但仍建议保留断点续传和退避逻辑。

### 3. 批量 pull-tag-push 脚本形态

```bash
#!/usr/bin/env bash
set -euo pipefail

LIST_FILE="${1:?usage: sync_images.sh <image-list>}"
REGISTRY_HOST="${REGISTRY_HOST:-localhost:5000}"
PLATFORM="${PLATFORM:-linux/amd64}"
DONE_FILE="${DONE_FILE:-sync.done}"
FAILED_FILE="${FAILED_FILE:-sync.failed}"
SLEEP_SECONDS="${SLEEP_SECONDS:-2}"

touch "$DONE_FILE" "$FAILED_FILE"

while IFS= read -r src; do
  [ -n "$src" ] || continue

  if grep -Fqx "$src" "$DONE_FILE"; then
    echo "skip already synced: $src"
    continue
  fi

  dst="${REGISTRY_HOST}/mirror/${src}"
  ok=0

  for attempt in 1 2 3; do
    echo "sync attempt=${attempt}: $src -> $dst"
    if docker pull --platform "$PLATFORM" "$src" \
      && docker tag "$src" "$dst" \
      && docker push "$dst"; then
      echo "$src" >> "$DONE_FILE"
      grep -Fvx "$src" "$FAILED_FILE" > "${FAILED_FILE}.tmp" || true
      mv "${FAILED_FILE}.tmp" "$FAILED_FILE"
      docker image rm "$dst" "$src" >/dev/null 2>&1 || true
      ok=1
      break
    fi

    sleep "$((attempt * 60))"
  done

  if [ "$ok" -ne 1 ]; then
    grep -Fqx "$src" "$FAILED_FILE" || echo "$src" >> "$FAILED_FILE"
  fi

  sleep "$SLEEP_SECONDS"
done < "$LIST_FILE"
```

这个脚本把源镜像：

```text
xingyaoww/sweb.eval.x86_64.getmoto_s_moto-7365:latest
```

映射为本地 registry 镜像：

```text
localhost:5000/mirror/xingyaoww/sweb.eval.x86_64.getmoto_s_moto-7365:latest
```

R2E 镜像也使用同一映射规则，例如：

```text
namanjain12/orange3_final:2d9617bd0cb1f0ba61771258410ab8fae8e7e24d
localhost:5000/mirror/namanjain12/orange3_final:2d9617bd0cb1f0ba61771258410ab8fae8e7e24d
```

### 4. 断点续传

断点续传依赖三个事实：

1. `sync.done` 逐行记录已经完整 pull-tag-push 成功的源镜像。
2. `sync.failed` 逐行记录连续三次失败的源镜像，后续可以单独重试。
3. Docker registry 按 blob digest 存储。某次 push 中途失败后，下一次 push 会跳过已经存在的 blob，只补齐缺失部分。

重新运行同一个批次时，脚本会跳过 `sync.done` 中已有的镜像，因此可以安全恢复。

### 5. 校验方式

校验分三层：

第一层，检查任务清单与完成列表行数：

```bash
wc -l meta/image_refs_swegym.txt meta/image_refs_r2e.txt sync.done sync.failed
```

第二层，对本地 registry 做 manifest 存在性检查，不拉取镜像层：

```bash
while IFS= read -r src; do
  dst="localhost:5000/mirror/${src}"
  docker manifest inspect "$dst" >/dev/null || echo "missing manifest: $dst"
done < meta/image_refs_swegym.txt
```

R2E 使用同样命令，只需要把输入文件换成 `meta/image_refs_r2e.txt`。

第三层，抽样对比源端和本地端的 manifest 层 digest：

```bash
src="xingyaoww/sweb.eval.x86_64.getmoto_s_moto-7365:latest"
dst="localhost:5000/mirror/${src}"

docker manifest inspect "$src" | jq -r '.layers[].digest' > /tmp/src.layers
docker manifest inspect "$dst" | jq -r '.layers[].digest' > /tmp/dst.layers
diff -u /tmp/src.layers /tmp/dst.layers
```

如果源镜像未来发生 tag 漂移，源端和本地端 digest 可能不同。因此正式冻结后建议把源 manifest digest 另存为不可变审计表；训练时优先使用本地 registry 的固定 tag 或 digest 引用。

