# 第3类云端运行环境与复现方法

2026-09-29 / Claude（云端会话）。本页只记录本目录各题实际使用的运行条件，不是新的通用运行手册。

## 1．机器与容器后端

| 项目 | 实际值 | 与此前 CPU 批次的差异 |
| --- | --- | --- |
| 机器 | Claude Code 云端临时容器：4 CPU、15 GiB 内存、可写盘约 26–29 GiB（固定额度） | 09-29 SWE CPU 机为 38 CPU／98 GiB／767 GB。本机只宜 1–2 路评分并发，同时存放约 9 张 SWE 镜像 |
| Docker | 29.3.1，经 `/etc/docker/daemon.json` 设为 **overlay2 经典存储**（关闭 containerd snapshotter），cgroupfs、**cgroup v1** | 历史批次为 Docker 28.1.1、overlay2、cgroup v2。存储后端一致；cgroup 版本不同，资源观测字段可能与历史不同，本批不以资源数据下结论 |
| 镜像来源 | Docker Hub 对共享出口 IP 限流（`ratelimit-remaining: 0`，返回 429），因此把 `https://mirror.gcr.io` 设为 `registry-mirrors`，按原名拉取 | 拉取后 `RepoDigests` 为原仓库名加 manifest 摘要，与 ingest 冻结的 `image_manifest_digest` 逐一核对一致。评分链的摘要校验（`evaluate_image_digest` 只比较 `@` 之后的部分）照常 fail-closed |
| 网络 | 容器只能经 HTTPS 代理出网；TCP 22 不通，因此不能 SSH 到外部机器。pypi.org 与 files.pythonhosted.org 可直连 | 评分容器仍按正式 grader profile 设为 deny_all，不受影响 |
| 派生镜像 | 在本机按原配方重建，例如 install_wave1：原 Dockerfile 文本加固定版本 wheel，wheel 的 SHA256 与此前登记逐一核对 | 派生 image ID 是本机 ID，历史 ID 不适用；跨机身份以配方、wheel 摘要和 base 层保留为准 |

`dockerd` 由本会话手动启动（`nohup dockerd`），容器回收后需重新执行同样的配置。

## 2．代码版本

- 工作分支 `claude/category3-20260929`，从 `codex/pro-review-20260929`（`4a969c3`）创建。
- 正式评分路径逐字等于已提交的 `a31cdcd`，包括 `rh2/src/repoharness2/grading/`、`adapters/slime/replay_grade.py`、`adapters/slime/prepared_task_face.py`、`envpack/`（R2E 摄入除外）和 `rh2/scripts/replay_grade.py`，已用 `git diff a31cdcd HEAD` 核对。快照提交 `287bc09` 中未验收的改动只涉及 rollout 普查、静止屏障和 R2E 摄入，SWE 评分不经过这些代码。
- 诊断包装沿用既有工具：
  - `rh2/experiments/task2_swegym_dev_20260925/semantic_control.py`：私有 root 对照；
  - `rh2/experiments/env_recipe_repair_20260919/replay_with_install_recipe.py`：`--materials` 版本化诊断评分。

  两者都来自快照提交，在历史批次中用过；本目录未修改它们。
- rh2 虚拟环境：`uv sync --frozen --no-dev --group swe --group data --python 3.12`。评分不需要 torch 等开发依赖，因此不装 dev 组。

## 3．证据层级（本目录统一用法）

| 称呼 | 含义 | 不能说明什么 |
| --- | --- | --- |
| 私有对照 | root、断网、一次性容器，在原镜像上直接执行命令（`semantic_control.py`） | 不证明解题身份（UID 54321）的开发条件，也不是正式分数 |
| 正式评分 | `replay_grade.py run`：真实 `SWEGradingManager`、正式 grader profile（UID 54322、deny_all、2 CPU／4 GiB）、真实安装与测试、逐参考核对和清理 | 不是修订后的正式材料；也不是训练资格 |
| 修订版诊断评分 | 同一正式链路，通过 `--materials` 替换版本化的测试补丁，F2P／P2P 名单和测试命令不变；grader 版本带诊断后缀 | 尚未经 D6 入口入库，不能当作正式修订版本使用 |

每题都记录：镜像摘要、派生配方、候选 SHA256、账本行（reward、F2P／P2P、参考缺席、安装、测试退出码、清理），以及评分日志中关键失败原因的逐字摘录。

## 4．证据保存

`runs/` 被 git 忽略，而云端容器是临时的。因此每题的小型原件由 `rh2/experiments/category3_cloud_20260929/archive_evidence.py` 复制到 `tasks/<id>/evidence/`，包括账本、评分日志、诊断 JSON、私有对照输出和审计文件；其余文件只登记 SHA256。未复制的有：

- 候选／评分容器导出的 `artifacts/`；
- 可从 ingest 重建的 `prepared/`、`private/` 任务面；
- 超过 2 MB 的单个文件。

复制前扫描过凭据字样。
