# R2E 第二批环境卡（2026-09-25，静态审查用）

Claude（B 线，R2E 协调）。按[共用开发验证流程](../actor_development_validation.md) §1，由协调者核对当批共同条件，审查者引用本卡，不自行猜配置。每条注明它是**代码配置**、**实测**还是**未知**。逐题差异写在各题公开包的 `environment_brief.md`（中性说明）和私有包的 `run_refs.json`（评分侧运行证据）。与首批环境卡相比，变化在 §2：正式 actor 的 R2E 接线已实施，公开提示已换成 R2E 措辞。

## 1. 评分侧（grader）：已实测

| 项目 | 当前事实 | 证据级别 |
| --- | --- | --- |
| 镜像 | 每题一张派生镜像：来源镜像的解释器搬出 `/root`，隐藏测试移到 root 私有目录（0700），git 里清掉修复提交；11 题另有配方身份（datalad `58ba5165` `+material_v1`；scrapy `cfed9b66` 与 pandas 7 题 `+material_v2`；numpy `43e333e2` `+env_v1`；orange3 `9b5494e2` `+env_v2`） | 实测（派生构建复核 21 项） |
| 评分顺序 | 候选补丁应用后，grader 删 `/testbed/r2e_tests`，从私有目录放入当前生效的隐藏测试，属主给评分用户 54322，以该用户跑 `bash run_tests.sh`（`pytest -rA r2e_tests`） | 代码配置 + 实测 |
| 判定 | 解析 pytest 的 short test summary，键为 `类名.测试名[参数]`（丢掉文件名）；**观测映射与期望映射逐键完全相同才得 1**：键集合相同，PASSED / FAILED / ERROR 逐个相同；SKIPPED、XFAIL 不成键 | 代码配置（来源规则逐字移植）+ 实测 |
| 资源 | 默认 2 CPU / 4 GiB / `/tmp` 1 GiB；numpy `2f4a9650` 评分用资源配方（`/tmp` 6 GiB + 内存 12 GiB） | 实测 |
| 当前材料下的运行 | 48 题 gold 都是 1、noop 都是 0（各题当前材料与配方下，至少两次）；修订题与独立 runner 的同版本对照缺席，改用一次性容器试跑逐键对照 | 实测（见各题 `run_refs.json` 的 current 行） |

## 2. 解题侧（actor）：正式启动链已接（待 A 线审查）

| 条件 | 事实 | 证据级别 |
| --- | --- | --- |
| 镜像 | 正式 actor 按覆盖表里的派生镜像 image ID 启动，评分侧用同一张；R2E 题缺派生镜像记录即拒，不回退来源镜像 | 代码配置（待 A 审）；首批 8 题真实启动实测 |
| 解释器与激活 | 激活脚本与解释器前缀都是 `/testbed/.venv`；agent（uid 54321）的 `python` 是 `/testbed/.venv/bin/python`；激活文件 agent 不可写 | 首批 8 题实测（真实 Claude Code 2.1.205 + 桩端点） |
| 隔离 | R2E 预检三项：解释器可执行、隐藏测试不可读、HEAD 没有子提交 | 首批 8 题实测 |
| 公开提示 | `public_hints` 已换成 R2E 措辞：`.venv`、不联网、pip 可能没有、不要改仓库的测试文件、用 `python -m pytest`。它随公开包写进容器的 `/rh2/public_task_bundle.json`，不注入系统提示 | 代码配置；本批材料 v3 已是新提示 |
| 按题差异 | pip 有无、pytest 版本（8.3.4 / 7.4.4 / 4.6.6 等）、是否需要 `/testbed` 在 `sys.path` 上、Qt 测试的 xvfb 前缀、与本题无关的恒失败公开测试，逐题不同 | 首批实测；本批逐题见 `environment_brief.md` 与协调者提供的真实环境核对证据 |
| 候选可写前缀 | 正式 profile 的候选可写前缀是 `/opt/miniconda3/envs/testbed`（R2E 不存在，只记数）；R2E 的 venv 在 `/testbed/.venv` 内 | 代码配置 |
| 未验证 | 经 Qwen adapter 的链路、真实模型求解、模型实际收到的完整消息 | 未知 |

协调者会为本批每题跑一次真实环境开发核对：与首批同一入口，用公开读者建议的命令，另做私有 gold 对照。证据目录在派发时给出，是执行事实，不是审查结论。

## 3. 静态审查者怎样用本卡

- 写开发需求时，引用实测过的条件；需要真实模型或经 adapter 才能确认的，写"actor 待验"，不写"环境正常"。
- 影响合法解时分别说明，不据此判题目不可用。评分侧运行证据只证明评分条件，不能替代 actor 条件。
