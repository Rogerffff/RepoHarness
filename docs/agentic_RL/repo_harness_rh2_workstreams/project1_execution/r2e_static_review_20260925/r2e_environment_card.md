# R2E 当批环境卡（2026-09-25，静态审查用）

Claude（B 线，R2E 协调）。按[共用开发验证流程](../actor_development_validation.md) §1，由协调者核对当批共同条件，审查者引用本卡，不自行猜配置。每条注明它是**代码配置**、**实测**还是**未知**。逐题差异写在各题公开包的 `environment_brief.md`（中性说明）和私有包的 `run_refs.json`（评分侧运行证据）。

## 1. 评分侧（grader）：已实测

| 项目 | 当前事实 | 证据级别 |
| --- | --- | --- |
| 镜像 | 每题一张派生镜像：来源镜像的解释器搬出 `/root`，隐藏测试移到 root 私有目录（0700），git 里清掉修复提交；11 题另有配方身份（datalad `58ba5165` `+material_v1`；scrapy `cfed9b66` 与 pandas 7 题 `+material_v2`；numpy `43e333e2` `+env_v1`；orange3 `9b5494e2` `+env_v2`） | 实测（派生构建复核 21 项） |
| 评分顺序 | 候选补丁应用后，grader 删 `/testbed/r2e_tests`，从私有目录放入当前生效的隐藏测试，属主给评分用户 54322，以该用户跑 `bash run_tests.sh`（`pytest -rA r2e_tests`） | 代码配置 + 实测 |
| 判定 | 解析 pytest 的 short test summary，键为 `类名.测试名[参数]`（丢掉文件名）；**观测映射与期望映射逐键完全相同才得 1**：键集合相同，PASSED / FAILED / ERROR 逐个相同；SKIPPED、XFAIL 不成键 | 代码配置（来源规则逐字移植）+ 实测 |
| 资源 | 默认 2 CPU / 4 GiB / `/tmp` 1 GiB；numpy `2f4a9650` 评分用资源配方（`/tmp` 6 GiB + 内存 12 GiB） | 实测 |
| 当前材料下的运行 | 48 题 gold 都是 1、noop 都是 0（各题当前材料与配方下，至少两次）；修订题与独立 runner 的同版本对照缺席，改用一次性容器试跑逐键对照 | 实测（见各题 `run_refs.json` 的 current 行） |

## 2. 解题侧（actor）：镜像层面实测；正式启动链 09-25 凌晨已接（待 A 审）

> **09-25 03:00 更新（协调者）**：下表后两行描述的是开工时的代码。当晚已改为：R2E 题的正式任务面用覆盖表里的派生镜像 image ID、`.venv` 激活与前缀、R2E 专用提示措辞（[接线说明](../r2e_actor_wiring_20260925.md)，待 A 审）；首批 8 题都经真实 Claude Code 启动链（桩端点）跑过开发命令，预检、解释器前缀、导入来源都成立，逐题结果见 [actor_devcheck.md](actor_devcheck.md)。原表保留作开工时的记录。

环境阶段的开发条件探针在**派生镜像**里以 agent/54321、rollout profile 数值和可信初始化步骤跑过 48/48 题（`docker exec -u 54321`）。这是**独立诊断入口**：没有经过 Claude Code 的非交互 shell，也没有 `/rh2/bash_env`，只能证明镜像层面的条件。

| 条件 | 事实 | 证据级别 |
| --- | --- | --- |
| 解释器 | `python` 经镜像 ENV 指向 `/testbed/.venv/bin/python`（3.7.9 / 3.8.20 / 3.9.21 / 3.10.16，逐题见 brief） | 镜像层面实测 |
| 包管理 | 27/48 题 venv 没有 pip，`pip` / `pip3` / `uv` 都不在 PATH；全池无出网（回环可用） | 镜像层面实测 |
| 导入与测试入口 | aiohttp ×5、numpy ×7：`/testbed` 须在 `sys.path` 上，跑测试要 `python -m pytest`，裸 `pytest` 收集失败 | 镜像层面实测 |
| 其它 | orange3 widget 测试要 xvfb 前缀；datalad 的 agent HOME 没有 git 身份；13 题仓库公开测试有与本题无关的失败或收集问题 | 镜像层面实测 |
| **正式 actor 用哪张镜像** | `rollout_spec_from_view` 取 `public.image`，即**来源镜像**：`/r2e_tests` 所有用户可读（就是隐藏测试），git 的 main 分支上有修复提交。派生镜像目前只在回放评分里消费 | 代码事实（09-25 核对）；**R2E 进正式 actor 前必须改**，B 线今晚实现、A 审 |
| 解释器前缀与提示 | `RolloutTaskSpec.expected_interpreter_prefix` 默认 conda，R2E 的 `.venv` 会被启动前核对拒绝；`PUBLIC_SYSTEM_HINTS` 与 `public_hints` 写的是 conda（E09） | 代码事实；B 线今晚实现、A 审 |
| 候选可写前缀 | 正式 profile 的候选可写前缀是 `/opt/miniconda3/envs/testbed`（R2E 不存在，只记数）；R2E 的 venv 在 `/testbed/.venv` 内 | 代码配置；actor 侧可写性未经正式链验证 |

## 3. 静态审查者怎样用本卡

- 写开发需求时，镜像层面实测过的条件可以引用本卡；需要经过正式启动链才能确认的（非交互 shell 的 PATH、`/rh2/bash_env`、提示措辞），写"actor 待验"，不写"环境正常"。
- `public_hints` 里"conda 已激活、pip 可用"对 R2E 不成立；"测试文件会被重置、测试改动永不计分"不是 R2E 的机制：R2E 评分只删掉并重放 `r2e_tests/` 与入口 `run_tests.sh`（候选放在 `r2e_tests/` 下的文件，包括新建的 conftest，都会被清掉），不做其它 reset / clean，仓库自己的测试文件与候选对它们的改动都保留（`rh2/src/repoharness2/adapters/slime/r2e_grading_scripts.py` 的 `_restore_lines`）。隐藏测试若导入仓库测试模块里的辅助代码，候选改这些辅助代码会影响评分。影响合法解时分别说明，不据此判题目不可用。
- 评分侧运行证据只证明评分条件；不能替代 actor 条件。
