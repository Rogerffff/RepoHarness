# 第3类第二批：作者须知（主审子代理用）

2026-09-29 / Claude（云端，第3类负责人）。第二批由主审子代理并行完成作者诊断，每题再由不继承上下文的独立复核子代理把关。本文是交给作者子代理的统一要求，也是本批方法的记录。规则以[统一标准 v1](../task_screening_standard_v1_20260925.md)为准，本文不重复条文，只写本批的做法与试点教训。

## 1．交付

每题落到三种结论之一：
- 疑点已消除，可申请转第1类；
- 问题和修法已明确，转第2类并交接；
- 仍有具体问题：写明缺什么证据、下一条命令或需要谁决定。

只有公开材料确实无法消解的目标选择才交用户（P5 第二分支）。

写入位置（只写这些，不改其它任何文件）：

| 内容 | 路径 |
| --- | --- |
| 结论页 | `docs/.../category3_diagnosis_20260929/tasks/<instance_id>/result.md` |
| 归档证据 | 同目录 `evidence/`，由 `archive_evidence.py` 从 `runs/` 复制 |
| 补丁、脚本、修订草案 | `rh2/experiments/category3_cloud_20260929/<短名>/` |
| 运行产物 | `runs/category3_cloud_20260929/<短名>/`（被 git 忽略） |

不要 git commit 或 push，提交由负责人统一做。

## 2．方法（按顺序）

1. **读原件，先形成判断**：题面、gold、test_patch 与参考名单（SWE 在 `s2/ingest/` 的 `public_bundles_v0.jsonl`、`validation_bundles_v0.jsonl`、`grading_bundles_v2_v0.jsonl`；R2E 在 `s2_r2e/ingest/` 与 `s2_r2e/revisions/`）。再读工作项引用的旧题卡、复核与状态说明；旧结论可能过时，要用代码与运行核对。
2. **私有行为矩阵**：用 `rh2/experiments/task2_swegym_dev_20260925/semantic_control.py` 在一次性、断网、root 容器里对比 base、gold 与候选。
3. **候选集**：除了题卡已有的候选，默认覆盖试点反复出现的几类错误，每类至少想一个与本题相关的构造：
   - 吞掉错误、抑制症状（try/except 后报告成功）；
   - 只对部分规模或阈值有效的修复；
   - 依赖执行顺序或插入顺序的写法；
   - 只覆盖编码、类型或数据形态子集的写法；
   - 只处理题面示例字面值的写法；
   - 至少一个“合理但与 gold 不同”的实现，用来查误拒（T1）。
4. **行为矩阵的覆盖面**：函数自己显式处理的相邻属性（例如 pillow 的 `transparency`）、超过阈值的规模、数据存在／缺失／被修改三种状态、交互与非交互路径。
5. **上游对照（可选，低成本）**：用 PyPI 发布的后续版本查上游最终写法，可以判断 gold 缺陷是否真实，或提供上游式替代正对照。只作佐证，不当公开依据。GitHub 页面在本容器读不到；raw.githubusercontent.com 可用。
6. **正式评分**（SWE）：对原材料跑 noop、gold 和关键候选；需要修订时，用 `--materials` 跑修订版诊断评分。命令模板见 §4。
7. **修订草案**：按 §5 的 R-a 至 R-f 起草，测试 ID 尽量不变（D6 目前支持测试补丁替换；改参考分组需要后续切片）。gold 若通不过有依据的新断言，按 D4 找替代正对照：它必须由他人独立核实，你写的实现要在结论页注明“待他人核实”。
8. **归档与自查**：`python rh2/experiments/category3_cloud_20260929/archive_evidence.py runs/category3_cloud_20260929/<短名> docs/.../tasks/<instance_id>/evidence`。归档后扫描凭据字样（proxy、authorization、token 等），不写入本机私有路径与密钥。

## 3．环境规则（多个子代理共用一台机器）

- 4 CPU、15 GiB、磁盘约 28 GiB 可用。拉镜像前先 `df -h /`，可用不足 8 GiB 时停下来报告，不要自行删除别人的镜像。
- 镜像按原名拉取（Docker Hub 经 `mirror.gcr.io`），核对 `RepoDigests` 与 ingest 冻结摘要一致。按摘要拉取的镜像要打 `c3keep/<短名>:src` 标签。**禁止 `docker image prune`、`docker system prune`**，只能删除自己本题创建的派生镜像。
- 每次正式评分前先等机器空闲一些：`while [ $(docker ps -q | wc -l) -ge 3 ]; do sleep 20; done`。每题同一时间只跑一个正式评分；单次运行超过 60 分钟就停下来报告。
- `MILES_RH2_RUN_ID` 用 `c3b2-<短名>-<候选>`，保证唯一。
- rh2 虚拟环境在 `rh2/.venv`，命令从 `rh2/` 目录运行。

## 4．命令模板

```bash
cd /home/user/RepoHarness/rh2
W=/home/user/RepoHarness/runs/category3_cloud_20260929/<短名>
# 准备与导出 gold
.venv/bin/python scripts/replay_grade.py prepare --repo-root .. --out-dir $W/prepared --private-dir $W/private --task-ids swe_gym_lite::<instance_id>
.venv/bin/python scripts/replay_grade.py export-gold --ingest-dir ../docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest --instance-ids <instance_id> --out-dir $W/gold
# 原材料正式评分（候选：noop | gold-dir:$W/gold | patch:/绝对路径）
MILES_RH2_RUN_ID=c3b2-<短名>-noop .venv/bin/python scripts/replay_grade.py run --prepared-summary $W/prepared/replay_summary.json \
  --task-ids <instance_id> --candidate noop --eval-log-dir $W/formal/eval_logs --artifacts-dir $W/formal/artifacts --ledger $W/formal/ledger_noop.jsonl
# 需要安装配方时：加 --recipe（09-19 配方 JSON）与派生镜像
.venv/bin/python experiments/env_recipe_repair_20260919/replay_with_install_recipe.py --code-root $(pwd) --recipe <配方.json> \
  --audit-dir $W/formal/audit_<候选> -- run ...同上... --derived-image <derived_id> --derived-image-recipe <标签>
# 修订版诊断评分：加 --materials（JSON：{"version":..., "tasks":{iid:{"original_patch_sha256","test_patch","revised_patch_sha256","reason","positive_control"}}}），可与 --recipe 同用
```

派生镜像的重建：
- install_wave1 类：`rh2/experiments/category3_cloud_20260929/rebuild_install_wave1.py --instance-id <iid> --out $W/derived`（固定版本见 `env_recipe_repair_20260919/installation_wave1.json`）；
- pydantic_v1 类：`rebuild_wheel_layer.py --kind build`，固定版本与 pydantic-9066 相同，Python 3.8：hatchling 1.21.1、hatch-fancy-pypi-readme 24.1.0、packaging 23.2、pathspec 0.11.2、pluggy 1.3.0、trove-classifiers 2024.3.3、tomli 2.0.1、editables 0.5。这是等效重建，不是 09-19 原版的逐字节重建，结论页要写明；
- compat 类（compat_v1、compat_v2b）：`rebuild_wheel_layer.py --kind compat --pin ...`，固定版本见 `env_recipe_repair_20260919/<批>/recipes/<iid>.json`。

试点用过的完整命令可参考 `tasks/pydantic__pydantic-9066/result.md` 与 `tasks/getmoto__moto-7584/result.md`。

R2E 题在云端没有正式评分链：用私有模拟评分，即运行评分包里的 `run_tests.sh`，再用 `rh2/experiments/category3_cloud_20260929/pillow3a61/grade_r2e.py` 逐键对照期望映射。结论页要标明“私有模拟”。

## 5．结论页格式

参照试点各题的 `result.md`，中文，保留标识符。依次写：
- 开头的结论与要点；
- 公开要求；
- 实测：私有与正式分开写，写明摘要、配方、候选 sha256；
- 判定：对应 v1 的哪一步，S1、S2、T 类标签；
- 修法与交接给第2类的清单；
- 当前用途；
- 未做与证据。

报告区分建议、已实施、已验证；私有模拟与正式评分分开写；没查的写“未查”。

## 6．交回内容

回复负责人：结论（三选一）、关键证据与数字、需要负责人或用户决定的事项、未做的事。
