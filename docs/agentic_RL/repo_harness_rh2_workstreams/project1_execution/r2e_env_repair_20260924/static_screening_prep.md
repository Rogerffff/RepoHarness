# R2E 48 题：进入题意与评分质量静态筛查之前（2026-09-24 夜）

Claude（B 线）。本页回答两件事：环境阶段交给静态筛查的是什么；静态筛查开工前还缺哪一步。静态筛查本身尚未开始；本页的流程是建议，不是用户决定。09-24 夜更新：T0-6 第二步与 T0-7 已按用户决定实施，第 5 节的固定材料已准备好。

## 1. 边界

- **环境侧状态不等于入池。** 在题意与评分质量静态筛查、基座探针和后续可能的修复之前，没有筛选好的环境池（用户 09-24 晚）。[结果表](results_20260924.md)里的 `environment_qualified` 等只说明环境侧检查到了哪一步。
- 环境阶段已没有待用户决定的事项：T0-6 第二步（另 6 道 pandas 补私有 conftest、期望按修复后 gold 重新核定）与 T0-7 方案 B（orange3 `9b5494e2` 固定 SciPy 1.5.4、修订 2 个期望键）09-24 夜已实施，见 [decisions.md](decisions.md) E21–E24。

## 2. 移交给静态筛查的已知事项

| 题 | 事项 | 现有证据 |
| --- | --- | --- |
| pillow `2b061b68` | T0-3：题面与目标测试矛盾，并把 `pytest.warns(None)` 的伪影写成库缺陷；用户决定留给本阶段 | [提案](material_revisions/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8.md) |
| scrapy `9a15fcf8` | T0-4：2 个期望 FAILED 键会惩罚更完整的正确修复（已实测判 0）；用户决定留给本阶段 | [提案](material_revisions/scrapy__9a15fcf89a151811de8ac783419df0512c863d5e.md)、`runs/r2e_env_repair_20260924/p4/ledger_overfix.jsonl` |
| coveragepy `5dbbe143` | 隐藏测试依赖修复前版本的测试辅助 `tests/coveragetest.py`；gold 不受影响，顺带用 `once=True` 的改法可能被误判（推断） | [记录](tasks/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/screening_record.json)、`runs/r2e_t0_batch2_20260924/scan/` |
| datalad `16c1ffc3`、`9ba5de09` | 隐藏 conftest 的 `path` fixture 与 nose 风格装饰器冲突，各 5 个死键；评分一致，但验证强度打折 | [known_issues](known_issues.json) `hidden_test_relocation_artifacts` |
| pandas 另 6 题 | T0-6 第二步已修（`r2e-mr-008`…`019`）：56 个 ERROR 键全部可达，修复后 gold 全 PASSED，期望里不再有 ERROR 键，候选建根目录 conftest 翻转键的路径随之消失。本阶段只需复核题意与活键是否够用 | [decisions E21](decisions.md)、`runs/r2e_t0_batch3_20260924/` |
| orange3 `9b5494e2` | 两个恢复键已按 T0-7 方案 B 修订（`r2e-mr-020`，只在 `+env_v2` 镜像上成立）；两个 scorer 键在兼容 SciPy 下仍失败，原因未定位；目标测试要求 `solver="auto"` 字面值，题面只说自动选择 | [decisions E23](decisions.md)、`runs/r2e_t0_batch2_20260924/diag_orange3/`、`runs/r2e_t0_batch3_20260924/dryrun_b3o/` |
| orange3 `22e98f8f` | 答案泄漏候选：题面的 Example Buggy Code 逐行等于 gold 修复，优先级最高 | [known_issues](known_issues.json) `prompt_quality_candidates` |
| 其余题面线索 | aiohttp `22a12cc2`（没点明 CONNECT 路径）、datalad `19f5b450`（示例导入位置不存在）、numpy `2f4a9650`（题面说 3D 也抛错，base 上不抛）、pandas `32dd55cb`、`87787609`、orange3 `f237f968`、`50f6a758` | 同上 |

scrapy `cfed9b66` 与 pandas `4ec87eb9` 修订后，原先"部分解也能满分"的两条推断都有了对应的活键，本阶段只需复核，不必重做。

## 3. R2E 解题环境卡（给协调者与私有审查者）

公开读者只拿中性的环境说明，不看本表的证据链。

| 项目 | 环境阶段已确认 | 不能据此声称 |
| --- | --- | --- |
| 镜像与身份 | 每题一张派生镜像：解释器搬出 `/root`、隐藏测试放进 root 私有目录、修复提交从 git 里清掉；带隐藏测试修订或依赖配方的 11 题另有配方身份（datalad `58ba5165` 为 `+material_v1`；scrapy `cfed9b66` 与 pandas 7 题为 `+material_v2`；numpy `43e333e2` 为 `+env_v1`；orange3 `9b5494e2` 为 `+env_v2`）；numpy `2f4a9650` 另需资源配方；coveragepy `016af5f6` 只改期望、镜像不变 | 正式 actor 已经消费这些派生镜像（A 线接缝） |
| 解释器 | `python` 经镜像 ENV 落在 `/testbed/.venv/bin/python`；解题身份 agent/54321 可执行 | 公开提示里写的 conda 环境对 R2E 成立（E09，交 A 线） |
| 包管理 | 27/48 的 venv 没有 pip，pip / pip3 / uv 命令都不在 PATH；全池无出网 | 解题者能装包 |
| 导入与测试入口 | aiohttp ×5、numpy ×7 只有 `/testbed` 在 sys.path 上才能导入；跑测试要用 `python -m pytest`，裸 `pytest` 收集即失败 | 其它题都能用裸 `pytest` |
| 其它条件 | orange3 widget 测试要带入口里的 xvfb 前缀；datalad ×5 的 agent HOME 没有 git 身份；13 题的仓库公开测试有与本题无关的失败或收集问题 | 公开测试全绿 |
| 资源 | 只有 numpy `2f4a9650` 需要逐题资源配方（`/tmp` 6 GiB + 内存 12 GiB） | 训练规模并发下的资源余量 |
| 评分 | 来源评分两轮复现、与独立 runner 逐键一致；48 题在当前材料与配方下 gold 都是 1、noop 都是 0 | 所有正确解都会得 1、所有错误解都会得 0 |

逐题的解题侧条件在 `tasks/<instance_id>/screening_record.json` 的 `solver_conditions`。

## 4. 建议的流程（沿用 SWE-Gym，外加 R2E 特有检查）

**沿用**：[SWE-Gym 静态筛查流程](../swegym_task_audit_20260920/static_screening_workflow_20260921.md)的八方面协议与三角色（公开读者先写需求与疑义；私有主审做"公开要求 → 测试断言"的双向映射；独立复核者先初判再交叉），小批分波：先用有线索的题加按仓库固定抽样的无线索题校准，再扩到全部 48 题。

**R2E 要额外查的**：

- 题面是否泄漏修法。R2E 的题面由模型根据提交补丁与测试结果生成，本轮已见两种失败：题面把修复写成示例（orange3 `22e98f8f`），题面把测试框架的报错写成库缺陷（pillow `2b061b68`）。
- 题面描述的报错，是否真的出现在 noop 目标键的失败原因里。
- 死键多的题，剩下的活键够不够验证题面要求；环境阶段的逐键归因可以直接复用。
- 替代解、部分解、错误解用 RH2 实跑，不只停在推断。
- 本阶段决定 T0-3、T0-4 与第 2 节其余事项的去留。

**环境阶段已经做了、本阶段不必重做的**：解题侧开发条件 48/48 实测；隐藏测试支撑缺口的全池扫描；期望来源三方比对；非 PASSED 期望键的逐键归因。

## 5. 固定材料（SWE-Gym 流程的步骤 ①）

**09-24 夜已准备**：[r2e_static_prep_20260924/materials.md](../r2e_static_prep_20260924/materials.md)（产物 `runs/r2e_static_prep_20260924/v1/`）。48 题的实际解题工作树按下面的取法导出，15 张镜像逐文件比对一致（覆盖三类脏树）；私有包 120 个隐藏测试文件逐个核过评分面摘要；33 题因为没有镜像缺 `install.sh` 等未跟踪文件，逐题写明。下表与取法是 09-24 晚的原计划，保留作依据：

| 包 | 内容 | 来源 | 现状 |
| --- | --- | --- | --- |
| 公开包 | 冻结的 public bundle、由 `render_user_prompt` 渲染的用户提示、中性环境说明、**实际解题工作树**（见下） | 前三项在本地；工作树见下 | 未导出 |
| 私有包 | 当前生效的隐藏测试（含修订）、期望映射（含修订）、gold 补丁、`run_tests.sh`、修订单条目、R-f / 中央复跑 / 修订后正式运行的日志定位 | 全部在本地（`s2_r2e/`、`runs/`） | 未打包 |
| 历史包 | 本轮逐题记录与 findings（主审自己的分析保存后才开放） | `tasks/<instance_id>/` | 已有 |

**公开包给的是实际解题工作树，不是上游提交树**（09-24 按 Codex 批次二复核 F2 更正；原写"按 base 提交导出、用 HEAD 与已拉镜像抽查"不够）。两者在 12 题上不同，只核 HEAD 看不出来：

| 题 | 镜像初态相对 base 提交的跟踪文件改动 |
| --- | --- |
| pandas 7 题 | 删除 `pyproject.toml`；修改 `pandas/__init__.py`、`pandas/_version.py`、`setup.cfg`、`versioneer.py` |
| aiohttp `1c1c0ea3`、`22a12cc2`、`4075c653` | 修改 `Makefile` |
| aiohttp `240da100` | 修改 `aiohttp/client.py`、`aiohttp/server.py`、`aiohttp/worker.py`（来源镜像为新版 Python 做的兼容改写） |
| aiohttp `61833518` | 修改 `aiohttp/client.py`、`aiohttp/client_reqrep.py`、`aiohttp/server.py`、`aiohttp/worker.py`（同上） |

另外 48 题的工作树里都有未跟踪的构建文件：`install.sh`、`run_tests.sh`，aiohttp 另有 `process_aiohttp_updateasyncio.py`。

**取法**：克隆 8 个上游仓库，导出 base 提交的跟踪文件作底稿；对上表 12 题叠加 M3 事实采集在镜像内对 HEAD 取得的完整初始差异（逐题清单见 Codex 复核的 `r2e_t0_batch2_review_20260924/main/dirty_base_facts.json`；差异原文 `runs/env_overnight_20260916/M3/facts/<commit12>/facts/initial.diff`，记录的字节数与文件一致；其余 36 题该差异为空），要求在 base 上干净应用，删除项保留为删除；`run_tests.sh` 取评分面原文，`install.sh` 等只存在于镜像里的未跟踪文件，从已拉的镜像补取，拿不到的在包说明里写明缺什么。验收：手上有镜像的题（pandas `4ec87eb9`、aiohttp `1c1c0ea3` 等）对导出的工作树做逐文件摘要全量比对，脏树题至少各抽一题；只核 HEAD 不能作为通过证据。公开包说明里写清"这是实际解题工作树"。不需要为此默认重拉 48 张镜像。

## 6. 可直接复用的工具与数据

- 逐题记录与机械核对：`rh2/scripts/r2e_env/check_records.py`；结果表生成：`render_results.py`。
- 支撑缺口扫描：`scan_hidden_support.py`；期望来源三方比对：`expected_provenance.py`。
- 替代解、部分解、错误解的实跑：正式评分链 `rh2/scripts/replay_grade.py run --candidate patch:<文件>`（配合派生镜像覆盖表），结果进账本、可逐键对账。
- 修订草稿在封板前的试跑：做法记在 [decisions E16](decisions.md)（一次性容器按 grader 顺序准备隐藏测试、以评分 uid 跑来源入口；先确认对原材料能逐字重现来源期望）；本轮脚本与日志在本机证据目录 `runs/r2e_t0_batch2_20260924/`。
- 修订机制：修订单 v3（格式同 v2，四类修订，见 [decisions E16](decisions.md) / E24），派生步骤 `material_v2.sh`；环境配方步骤 `env_v1.sh` / `env_v2.sh`（E22）。
- 缺失 fixture 的静态清单：`rh2/scripts/r2e_env/extract_fixtures.py --tests <隐藏测试>`（`requested_fixtures`，一次算全，不靠报错逐轮补）。
- 固定材料：`r2e_static_prep_20260924/prepare_materials_r2e.py`（fetch / image-hashes / prepare / verify）。
