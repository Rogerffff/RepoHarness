# D4=A：诊断性派生 grader 镜像配方（moto-6913、pydantic-8500、MONAI-1121）

目的：让 deny_all 下的安装段能离线完成（wheel 缓存）、让 pydantic 的 PDM 对候选用户可用、让 MONAI 权重对候选用户可读。
产物只用于对账，**不是正式环境包**；driver 以 `--derived-image <ref> --derived-image-recipe <说明>` 使用（隐含 `image_local_build=True`，manager 跳过 RepoDigest 比对）并记录实际 image ID。tag 在检查与启动之间被重指是有条件的剩余风险：构建后立即记录 image ID，运行前后各 inspect 一次核对。
正式固定环境版本（D4 的 B）留到流水线阶段。

## 通用步骤（联网，一次）

```bash
BASE=xingyaoww/sweb.eval.x86_64.getmoto_s_moto-6913:latest     # 原环境包镜像（digest 见 environment_packages_v0.jsonl）
docker run --rm -it --name prov "$BASE" bash -lc '
  source /opt/miniconda3/bin/activate && conda activate testbed && cd /testbed &&
  mkdir -p /rh2/wheels &&
  # 让来源 install 串（make init → pip install …）所需的一切先下载到本地目录：先在线跑一遍安装记录 pip 的解析结果
  pip download -d /rh2/wheels -r <(pip freeze) 2>&1 | tail -3'
```

实际做法按仓库分三份配方（下面是骨架，e1/e2 时按实际安装失败日志补齐）：

| 仓库 | 需要预置什么 | 派生层做法 | 验证 |
| --- | --- | --- | --- |
| moto-6913 | `make init` 触发的 pip 解析（安装串逐字不变） | 联网跑一次 `make init`，再 `pip download` 其依赖到 `/rh2/wheels`；镜像 ENV `PIP_NO_INDEX=1 PIP_FIND_LINKS=/rh2/wheels` | deny_all 下 `RH2_INSTALL_RC=0` 且 `RH2_OBS_IMPORT_PATH` 在 /testbed |
| pydantic-8500 | PDM（原来由 pipx 装在 root 的 `~/.local/bin`）对候选用户可用；`pdm add pre-commit; make install` 的离线依赖 | 把 `/root/.local` 复制到 `/opt/rh2/pdm` 并 chmod 755，镜像 ENV `PATH=/opt/rh2/pdm/bin:$PATH`（安装串里的 `export PATH="$HOME/.local/bin:$PATH"` 仍逐字执行，只是多一个可用路径）；wheel 缓存同上 | 同上 |
| MONAI-1121 | torchvision ResNet 权重（sha256 `0676ba61…`）与 Hippocampus 测试数据（3205） | 放到候选用户可读路径并用 ENV `TORCH_HOME=/opt/rh2/torch` 指过去（不能只放 `/root/.cache`） | gold 在 deny_all 下 FULL（昨夜 root 预置对照 FULL） |

派生镜像命名：`rh2-derived/<instance>:<yyyymmdd>`；记录 `docker image inspect -f '{{.Id}}'` 到账本 `image_id_actual`，Dockerfile/配方文本放本目录并写入账本 `derived_image_recipe`。
派生构建不得改动 `/testbed` 内容与 HEAD（否则 baseline 重建检查会拒）；缓存一律放工作区外。
