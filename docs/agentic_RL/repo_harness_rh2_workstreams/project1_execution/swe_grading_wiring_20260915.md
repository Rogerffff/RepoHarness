# 第一步：接通真实 RH2 评分

更新：2026-09-15。状态：**计划已整理，接线尚未实施**。后续实施安排、决定、进展及 A 线程复核集中维护本页；长日志和证据只放链接。

## 1. 目标与后续顺序

先让已有候选补丁经过真实 RH2 代码完成评分，再设计和校准环境筛查流水线，随后安排 agent 分批逐题调查。大规模镜像分发、跨机迁移按需后做。

**建议 SWE-Gym、R2E 同批推进：SWE-Gym 先跑通公共路径，R2E 同步准备来源适配，随后接入同一入口。** R2E 能提前暴露接口对 SWE 评分格式的假设；两个来源共用评分执行，不各造一套 grader。

实际路径：**物化候选工作区 → 重放已有补丁 → 真实冻结与投影 → fresh grader → 安装/构建/测试 → 解析与结果记录。** 脚本暂时代替模型写补丁，其余复用生产实现；本阶段可在 CPU Docker 上验证，无需 GPU learner。

## 2. 首批接线范围

| 部分 | 要接什么 |
| --- | --- |
| 公共路径 | 复用 `SWEGradingManager`、冻结工件、投影和正式 grader profile；保留实际候选、逐测试状态、安装/测试退出情况、资源条件及原始日志。明确期限与清理方式。 |
| SWE-Gym | 接齐固定官方 fork 的 parser、测试选择器、安装/构建、`eval_commands`、可信测试材料及 F2P/P2P 参考列表，不能只换 parser 字典。 |
| R2E | 接入镜像初始状态、可信测试及辅助 fixture、测试命令和 expected 状态映射；明确公共结果的表达。expected 可含 FAILED/ERROR，不能强转成“所有测试都应 PASSED”。 |
| 必需环境条件 | 为首批案例准备必要依赖/资产，验证非 root 用户实际可访问；分别记录准备、解题、评分安装/构建、测试执行四段条件。正式出网策略沿既有决定。 |

当前代码已有冻结候选评分接口；SWE-Gym 来源配方尚未接齐，R2E 的现有验证主要在实验 runner。来源 runner 保留作独立对照，不能把它通过当作 RH2 已通过。

## 3. 实施顺序与完成标准

1. **明确材料与接口。** 列出拟修改文件、代表题、输入/输出、必要环境条件；R2E 结果表达和共享代码修改者先明确。沿本页细化即可。
2. **跑通 SWE-Gym，再接 R2E。** 来源配方可并行准备；共享 `grading`、投影和契约由一个实际实现者修改，另一方独立复核。
3. **用真实正反例对账。** 从已有数据选各仓库配方代表、no-op、gold、真实候选及已知异常；先小批验证，再扩覆盖。逐项比较重放文件、测试材料、测试选择和状态，解释总分差异。

**接线验收看四件事：**

- 正常候选修改确实进入 grader，安装/构建后测的是候选代码。
- no-op、gold 和真实候选运行了正确测试，失败原因可定位。
- 依赖、解析、资源故障保留具体事实；不为跑通而伪装成正常 reward。
- 来源 runner 与 RH2 的差异有解释；已知坏参考或 fixture 问题可准确复现并登记，不要求把所有异常题改到通过。

已有 **SWE-Gym 216 题、R2E 两批共 48 题**可供后续流水线试运行；全量处理不作为最小接线的前置，也不在此冻结正式训练题单。

## 4. A 线程复核重点与待定事项

建议 A 检查：是否真正走冻结/投影和正式 grader；候选安装/构建是否保持非 root；错误、期限和清理是否沿用既有语义；R2E 的结果表达是否兼容训练消费。

与 A 的[第四组评分讨论](batch4_scoring_20260910/README.md)共用决定：候选执行失败如何表达、合法源码被测试路径规则过滤等。相关行为验收前需解决对应问题，其他接线可先准备。

**本计划不自动批准**修改 expected/测试/题面、放开正式网络或新增排题规则。优先重验证来源定义；确需修订时，说明依据并保留原始/修订结果。共享契约调整在实施前列明，不藏在“接 parser”中。

## 5. 接线之后怎样安排 agent

先用已知反例和正常题校准检查流程，再按“来源＋仓库＋环境版本”分配，每题留下具体记录。统一工具运行真实评分；调查 agent 检查依赖、parser、资源、网络需要、题面与测试合理性，并主动补充清单外发现。独立复核覆盖改判、修订和随机正常题；Docker 并发统一管理。

额度充足时优先增加独立复核和可执行反例。调查 agent 可查看 gold/私有测试，正式求解 agent 只使用公开材料。流水线细则和大批量任务安排在接线后单独讨论。

## 6. 实施计划（Claude，2026-09-15 修订版：已合入 §8 A 线审查、§9 B 线复核、§10 A 线终审；待用户决定后开工）

本节把 §1–§5 落成可执行的切片。"代码事实"都在本机 worktree 核对过（`git status` 下 `rh2/src` 无未提交改动，只有未跟踪的 `rh2/experiments/`）；§8–§10 的每条意见的处理见 §6.9，本节正文已按处理结果改写，不再另存"原稿"。

### 6.1 核对后的代码事实与缺口

| 缺口 | 代码事实 | 本片处理 |
| --- | --- | --- |
| 评分脚本没有安装/构建段 | 候选段只有一行 `eval_cmd + 测试文件`，见 [prepared_task_face.py:108](../../../../rh2/src/repoharness2/adapters/slime/prepared_task_face.py#L108)；可信 setup 段只做恢复 official 测试文件与应用 test_patch（同文件 129–170 行）；bundle 字段说明明写"不走官方 checkout/install"，见 [bundles_v2.py:91](../../../../rh2/src/repoharness2/envpack/bundles_v2.py#L91)。今天生产根本不跑安装，因此"安装是否作用于候选"是**未验收**，不是"被记成候选失败" | 在候选段加安装段（D2），记录段末退出码的准确含义与逐配方的生效检查 |
| 安装命令与 `eval_commands` 已在仓库内，只是没被消费 | 包内 `envpack/data/swegym_specs_242429c1.json` 每条 spec 含 `install`、`pre_install`、`eval_commands`、`test_cmd`、`python` 等键；`spec_vendor.derive_eval_cmd` 只取 `test_cmd`。例：moto 5.0 `install = make init`；pandas 3.0 `install = python -m pip install -ve . --no-build-isolation -Ceditable-verbose=true; pip uninstall pytest-qt -y`；conan 1.51/2.0/2.1 `eval_commands = ['export PYTHONPATH=${PYTHONPATH:-}:$(pwd)']`；pydantic 2.x `install = export PATH="$HOME/.local/bin:$PATH"; pdm add pre-commit; make install;`（PDM 由镜像构建期 pipx 装在 root 的 `$HOME/.local/bin`） | 新增 `derive_install_cmd` / `derive_eval_commands` / `derive_test_command`，仍从同一 pinned JSON 派生，注册表不变；`pre_install` 属镜像构建阶段，不在评分时重跑 |
| 测试选择器与来源不一致：**43 条** | 当前用 `patch_touched_paths(test_patch)` 当测试文件。官方 fork：`python/mypy` 用 test_patch 里的 `[case X]` 拼 `-k "A or B"` 且不带文件（40 题）；其余仓库 = `test_cmd + get_test_directives`，后者按 `NON_TEST_EXTS`（.json/.png/csv/.txt/.md/.jpg/.jpeg/.pkl/.yml/.yaml/.toml）剔除资源文件——moto-4847、moto-7607、dvc-5336 当前把 `.txt/.json/.yml` 传给了 pytest（B 线 216 条真实 prepared 链对照，`exact_mismatches=43`）。官方 216 行存于 [official_cmd_contract_216.json](B_materials_20260908/official_cmd_contract_216.json) | `derive_test_command` 复用来源筛选；**可信 setup 恢复/保护的文件清单不随之缩减**（资源文件仍是官方测试 fixture）；契约测试 216/216 逐字相等 |
| parser 与日志边界 | `scoring.parse_official_eval` 走 4.1.0 `make_test_spec`，SWE-Gym 仓库先在 4.1.0 的 spec 注册表 `MAP_REPO_VERSION_TO_SPECS` 抛 KeyError，尚未到 parser 映射。fork 242429c1 映射：8 仓库 `parse_log_pytest`，pydantic `parse_log_pytest_pydantic`。**4.1.0 `get_logs_eval` 在标记段解析为空时回退解析整份日志**（B 线合成反例：段内只有收集失败文字、段外两行 PASSED → FULL，且 `num_parsed_tests` 非零，manager 零解析保护不触发）。report 语义（4.1.0 与 fork 一致）：参考 ID **缺席计失败**；PASSED/XFAIL 计成功；SKIPPED 两桶都不进，全部 SKIPPED 可得 FULL；`scoring.py` 顶部注释"不在日志出现按通过计"与实测不符 | vendored 两个 parser 函数与映射（D1）；v2 入口**只以标记段为状态来源**，段外输出留作诊断，坏码与缺标记沿 4.1.0；report 复用 4.1.0 `get_eval_tests_report / get_resolution_status`；manager 零解析 → infra 保留；顺手改正 `scoring.py` 注释 |
| 非 root 安装没有证据 | grader 候选用户 `rh2grader/54322`，候选段 `HOME=/home/rh2grader`（manager.py 2380 行）；控制面布置只 `chown -R /testbed`（[sandbox_profile.py:1265](../../../../rh2/src/repoharness2/adapters/slime/sandbox_profile.py#L1265)）；`/opt/miniconda3/envs/testbed` 对 54322 是否可写未验证；pydantic 配方需要 root `$HOME/.local/bin` 里的 PDM；MONAI 权重的旧验证只覆盖 root 缓存。**更正**：昨夜探针 `grader_user` 变体是"root 做 setup/install，只有测试命令以 54322 执行"（`swegym_probe.py` 第 15 行），我之前说"非 root 安装退出码 0 ×24 证明可行"是错的 | D3 决定后按实际 UID/HOME/PATH 做资产预检（B5），缺什么补什么；验收项 5 |
| 离线安装 | 阶段一 root+离线：安装退出码非 0 共 116 次（moto 74、pydantic 40、dask 2），测试仍跑且判定不变；moto-6913 gold 日志 install 返回 2 后仍有 18 项测试通过。正式 grader deny_all 会复现同类失败 | D4 决定预置方式；段末退出码不单独证明成功或失败（多命令串 `false; true` 段末为 0） |
| 资源旋钮缺 shm | `GraderSandboxProfile` 有 cpus/memory/tmpfs/pids，无 shm；MONAI-763 在 64 MiB 下 DataLoader SIGBUS；profile 参数进入 `to_parameters()/digest()`，即 `runtime_profile_digest` 会随之变化 | 加 `shm_size_bytes`、`--shm-size`，同时进 `to_parameters/digest`，验收用 `docker inspect` 核实；默认保持 Docker 默认 64 MiB，环境变量 `RH2_GRADER_SHM_BYTES` 覆盖；账本注明 digest 变化不是异常 |
| 超时时丢部分输出；内存 0 语义 | `run_docker` 被取消即 kill 子进程、不回传已捕获 stdout（manager.py 108–118 行）；`_run_eval` 只在正常返回才取候选日志（2374–2383 行）；B 线替身对照：候选已输出安装退出码和测试标记后超时 → 落盘日志不含二者、`test` 段耗时为空。`container_peak_memory_mb` 是 [timing 契约](../../../../rh2/src/repoharness2/contracts/timing.py)必填 `float ge=0`，读不到只能折成 0。安装进候选段后，manager 的 `test` 分段与 `test_timeout_seconds`（1800 s）都会包含安装；N2a 评分期限默认 3600 s | S1-m：manager 最小观测出口（超时也持久化已捕获输出；按阶段标记拆 install/test 计时）；账本 `mem_peak_mb=0` 标 `unavailable_or_zero`；候选超时今天归 infra（reward=None），无 reward 风险，但第四组 A 若加候选超时 producer 必须把安装段排除在归因窗口外 |
| driver 前置：结构分类与容器所有权 | `build_trusted_scoring_projection` 的前置条件是 `classify_frozen_patch` 已判 projectable（[trusted_projection.py:190](../../../../rh2/src/repoharness2/grading/trusted_projection.py#L190)）；生产 rollout 先分类再投影（generate.py 3441→3512）。A 线对照：`src/link -> ../../outside` 经分类器为 `unsafe_artifact`，直接调 builder 仍会把 `src/link` 放进投影。`grade(deadline_monotonic)` 只约束 manager 内部；manager 不拥有 driver 自建的候选容器 | S1-d：先分类后投影，unsafe 保存证据不评分；候选容器唯一 owner、独立预算、导出持久化后释放、`finally` 有界清理 |
| 派生镜像身份（仅 D4） | manager 校验 RepoDigests（manager.py 1852 行）；`image_local_build=True` 是唯一豁免且与 `image_manifest_digest` 在 `GradingEnvSpec` 互斥；本地 image ID 不是 registry manifest digest | D4 选 A 时 driver 用 `image_local_build=True` 并记录实际 image ID，账本区分原环境包身份与实际 grader 镜像；或发布后取得 RepoDigest |
| 报告契约 | `GradingReport` 要求 resolved/tests_failed 四计数齐全，只有 `patch_apply_failed`、`test_execution_timeout` 允许无计数的 0；infra 族 reward=None，见 [contracts/grading.py](../../../../rh2/src/repoharness2/contracts/grading.py) | 本片**不改契约**：安装退出码、参考 case 缺席/跳过计数、运行器完整性等只进 driver 账本与 eval 日志 |
| 真实入口 | `SWEGradingManager.grade(trajectory_id, workspace=None, spec, frozen_delta, deadline_monotonic)`；`GradingManagerConfig(eval_log_dir, sandbox_profile=grader_profile_from_env(env))` 与 bringup 同构；`FrozenDeltaSource(frozen_patch, baseline_manifest, projection, frozen_patch_digest)` 由 `export_frozen_patch` + 分类 + `build_trusted_scoring_projection` 组装；直连 manager 会走 N2b 的一次追加评分（transport 暂态）；`MILES_RH2_RUN_ID` 在环境中时评分容器带 run 标签 | driver 逐字复用这些入口；账本记 `regrade_total`；机器上设置 `MILES_RH2_RUN_ID` 便于残留清扫 |
| 任务与 gold 加载 | `python -m repoharness2.envpack.trusted_prep --task-ids …` 产出 prepared/private 两目录；actor 侧 `load_prepared_manifest` → `load_host_grading_views` → `build_grading_spec_from_host_view`；镜像与 digest 来自 `EnvironmentPackageV1`。**prepared/private 不含 gold**（B 线对照 `gold_field_count=0`） | driver 走 actor 同一读取口；gold 由受信准备步骤从 validation bundle 导出为绑定 task 的候选补丁文件（含 digest），再作为普通候选输入 |
| 数据与证据 | 216 题按仓库：moto 59、mypy 40、dvc 35、MONAI 26、pydantic 20、dask 14、conan 12、modin 5、pandas 5。24 条 DeepSeek 候选补丁有两组 oracle：**原组 FULL 13 / NO 7 / PARTIAL 3 / UNPARSED 1**，**投影组 13 / 8 / 3 / 0**，不能混用；其中 7 题原补丁历史上 `git apply --check` 失败、靠 `patch --fuzz=5` 应用（pydantic-8500/9214/8793/5706、MONAI-6975、mypy-11236/11352）。本机 `runs/env_probe_stage1_20260910/ledger/` 有 441 份 SWE-Gym `test_output.txt` + fork 产出的 `status_map.json`（43 MB），它们经 fork 的 applied-patch 包装产生，适合检验 parser 函数，不能不加区分地要求直接通过 v2 标记入口 | 代表批、真实候选（先重建候选工件再对账）、parser 函数回归语料 |

### 6.2 切片与顺序

| 切片 | 内容 | 依赖 | 产出与验证 |
| --- | --- | --- | --- |
| **S1-a 命令配方派生 + 契约测试**（零 Docker） | `spec_vendor.py` 新增 `derive_install_cmd`、`derive_eval_commands`、`derive_test_command`（mypy `-k` 与来源 `make_test_command` 对齐；其余仓库复用来源 `get_test_directives` 的 `NON_TEST_EXTS` 筛选）；`tests/envpack/test_vendor_specs.py` 增加 216 行契约：测试命令 == `official_test_line`（含 moto-4847/7607、dvc-5336 三条资源文件案例）、安装行 == spec `install`、conan 12 题含 `eval_commands`；另断言可信 setup 的恢复/保护清单仍等于 test_patch 触碰的全部路径 | 无，可立即开工 | `cd rh2 && .venv/bin/pytest tests/envpack/test_vendor_specs.py -q` 全绿 |
| **S1-b vendored parser + v2 入口 + 回归语料**（零 Docker） | 新模块 `envpack/swegym_parsers.py`（两个函数 + 9 仓库映射，注明来源 commit 与 sha256；LICENSE 与 provenance 放 `docs/.../s2/vendor/`）；`scoring.py` 新增 `parse_eval_log_v2(grading, log_text)`：按 `spec_vendor_id` 取 parser，**只解析 Start/End 标记段**，坏码与缺标记沿 4.1.0，不做整份日志回退；`grader_version` 记 `swebench-4.1.0+swegym_parsers@242429c1`；改正 `scoring.py` 顶部"silent success"注释。回归分两层：441 份本机语料只核 parser 函数的状态映射（环境变量 `RH2_SWEGYM_PARSER_CORPUS` 指向 `runs/` 目录时全量跑，精选 ≤ 3 MB 子集入库到 `rh2/tests/envpack/data/swegym_parser_dumps/`（A1 后随 rh2 测试树走），每仓库 ≥ 2 份，含 pydantic 带 ANSI 的日志）；v2 入口用小样例核完整判定：参考缺席、全部 SKIPPED、零解析、段内空而段外有 PASSED、坏码、缺标记 | D1 | 语料 0 条不一致或逐条解释；六个小样例判定与 §6.1 所述语义一致 |
| **S1-p gold 静态分类预检**（零 Docker） | 对 §6.4 A 组 9 题的 gold 与 B 组 24 条候选，用现有 `HygieneRules` / `classify_frozen_patch` 静态分类，列出会被投影忽略的路径（test_glob 命中、unsafe），先解释预期例外 | 无 | 预检表进 `swe_grading_wiring_20260915/precheck.md` |
| **S1-c 评分脚本渲染改造** | `prepared_task_face.py`：可信 setup 段与候选段都加入 `eval_commands`；候选段 = 安装段（来源 `install` 字符串逐字执行、`RH2_PHASE=install` 起止标记、`RH2_INSTALL_RC=<段末 rc>` 行，语义只是段末命令的退出码）→ 官方 Start/End 标记 → 派生测试命令；安装生效检查作为诊断线索由 root 侧读取（见 S1-m），候选 stdout 自报不作可信事实；`sandbox_profile.py` 加 shm（字段、`--shm-size`、`to_parameters/digest`）与（若 D3 通过）conda 前缀属主布置并写自证键；新增 `tests/adapters/test_w1b_prepared_task_face_v2.py` 断言阶段顺序、命令、执行用户、标记与退出码事实（不做整段文本快照）；`tests/grading/test_w3b_grader_profile_docker.py` 加 fixture 镜像用例：安装段以 54322 执行且 `RH2_INSTALL_RC` 被记录、official 测试文件仍 root:root 0644、`docker inspect` 显示 `--shm-size` | D2、D3 | 单测 + 本机 Docker fixture 测试全绿；`ruff` 无新告警 |
| **S1-m manager 最小观测出口**（A 线共享文件，登记后由 Claude 实现、A 复核） | 只做三件事：(i) `_exec_bash_checked` 超时/取消时把已捕获的候选输出写入 `record.eval_log_partial` 并随日志落盘；(ii) 按 `RH2_PHASE` 标记把候选段拆成 install/test 两段计时（只进阶段计时与账本，不改 `timing_parts` 契约口径）；(iii) 候选段结束后一次 root 观测 exec：读取安装生效证据（包导入路径、编译产物 mtime/版本串）与测试运行器完整性摘要（`site-packages` 下 `pytest/_pytest/pluggy` 文件 sha256 与候选段前对比），写入诊断，不改判定 | §7 登记归属；不阻塞 S1-a/b/p/f | `tests/grading/test_manager_unit.py` 用 FakeDocker 覆盖"输出后超时仍留证据"；验收项 10 |
| **S1-d 真实链 driver** | 新模块 `envpack/replay_grade.py` + CLI `rh2/scripts/replay_grade.py`。输入：`--prepared-dir/--private-dir/--manifest-sha256`（trusted_prep 产物）、`--task-ids`、`--candidate noop|patch:<file>`（gold 由受信步骤 `export_gold_candidate` 先导出为补丁文件）、`--repeat N`、`--candidate-stage-seconds`（创建、物化、census、apply、export 的总预算）、`--grading-deadline-seconds`（只给 `grade(deadline_monotonic)`，两者不共用一份预算）、`--eval-log-dir`、`--ledger`、`--derived-image <ref> --image-local-build`（仅 D4，记录实际 image ID）。流程：fresh 候选容器（driver 唯一 owner，创建请求前记账）→ `materialize` 血缘探针 → `generate_baseline_manifest` → 以候选用户（agent/54321）`git apply --check` 后写入补丁，失败即记 `apply_failed` 停止、**不 fuzz、不改补丁**；账本记 `apply_method` → `export_frozen_patch` → **`classify_frozen_patch`**（unsafe 保存证据、不评分；契约矛盾按既有 fatal 停止）→ `build_trusted_scoring_projection` → `FrozenDeltaSource` 持久化 → 释放候选容器 → `SWEGradingManager.grade(workspace=None, …)` → 账本行。外层 `finally` 用独立有限时间清理候选容器与 manager；`MILES_RH2_RUN_ID` 给容器盖 run 标签。单元测试用 `grading_fixtures.FakeDocker` | S1-a/b/c/m | `tests/envpack/test_replay_grade.py` 覆盖：创建回包丢失、apply/export 超时、评分取消，均保留首个失败原因且无容器残留；本机 fixture 镜像端到端一次 |
| **S1-e1 机器冒烟** | 先跑 mypy-12741、conan-13326、dvc-5822 的 gold/noop，再加 pandas-48106（编译型）；确认新用户权限、安装产物、初始化与安装耗时、账本可解释 | 机器可用；D3 | 冒烟四题全部有可解释账本行，才进入 e2 |
| **S1-e2 代表批对账** | §6.4 的条件矩阵；每题账本 + eval 日志 + `reconcile.md`（rh2 vs oracle 逐题、逐 ID） | e1 通过；D4 决定的预置 | §6.6 验收清单逐项打勾，差异逐条解释 |
| **S1-f R2E 结果表达决策包**（并行，只写文档） | GradingReport 如何表达 expected 状态映射（加来源语义字段 + 专用计数，或泛化为"参考 id → 期望状态 + 观测 + 规则"）；影响 RewardFacts、eligibility 消费者；附 coveragepy/datalad 两个反例 | 无 | 决策包文档；R2E 代码在第二片 |

可先开工：S1-a、S1-p、S1-f，以及 S1-b 的 pinned 提取与语料整理；S1-b 的代码等 D1；S1-c 等 D2/D3；S1-m 先在 §7 登记；S1-d 等 S1-m 接口定型；S1-e 等机器与 D4。

### 6.3 拟修改与新增文件及归属

| 文件 | 改动 | 归属与复核 |
| --- | --- | --- |
| `rh2/src/repoharness2/envpack/spec_vendor.py` | 新增 `derive_install_cmd`、`derive_eval_commands`、`derive_test_command`（mypy `-k` 与来源 `make_test_command` 对齐；其余复用来源 `get_test_directives` 筛选） | Claude 实现；B 线 Codex 复核 |
| `rh2/src/repoharness2/envpack/swegym_parsers.py`（新） | vendored `parse_log_pytest`、`parse_log_pytest_pydantic`、`MAP_REPO_TO_PARSER_SWEGYM`；模块头记录来源 commit、文件 sha256 | Claude；B 线复核 |
| `rh2/src/repoharness2/envpack/scoring.py` | 新增 `parse_eval_log_v2`：按 `spec_vendor_id` 取 parser，只解析标记段，坏码与缺标记沿 4.1.0；`grader_version` 带来源 revision；改正顶部注释；旧 `parse_eval_log` 保留给 v1 路径 | Claude；A/B 复核（评分入口） |
| `rh2/src/repoharness2/adapters/slime/prepared_task_face.py` | 渲染改造（安装段、`eval_commands`、测试命令派生、阶段标记）；`build_grading_spec_from_host_view` 的 `parse_log` 改绑 v2 入口 | Claude；A 线复核（与 rollout actor 共用） |
| `rh2/src/repoharness2/adapters/slime/sandbox_profile.py` | `GraderSandboxProfile.shm_size_bytes`（字段、`docker_run_args`、`to_parameters/digest`）；D3 通过时在 `grader_protect_control_surface_script` 之前加 conda 前缀属主布置并写自证键 | Claude；A 线复核（安全边界） |
| `rh2/src/repoharness2/grading/manager.py` | **S1-m 三项最小观测出口**（超时保留已捕获输出；install/test 分段计时；候选段后一次 root 观测 exec）。不改判定、不改契约、不改期限语义 | A 线所有；Claude 在 §7 登记后实现，A 复核 |
| `rh2/src/repoharness2/adapters/slime/replay_grade.py`（新；**实施时从 envpack 移到 adapters/slime**：driver 组合的是 prepared_task_face、baseline_census、patch_exporter、sandbox_profile 这些 adapter 层部件，放 envpack 会形成 envpack→adapters 的反向依赖）、`rh2/scripts/replay_grade.py`（新） | driver 与 CLI（`prepare` / `export-gold` / `run` 三个子命令），含 `export_gold_candidates` 受信步骤 | Claude；A 线复核是否真正走分类/冻结/投影/正式 profile 与清理 |
| `rh2/tests/envpack/test_vendor_specs.py`、`test_swegym_parsers.py`（新）、`test_replay_grade.py`（新）；`rh2/tests/adapters/test_w1b_prepared_task_face_v2.py`（新）；`rh2/tests/grading/test_w3b_grader_profile_docker.py`、`test_manager_unit.py` | 见 6.2 | Claude |
| `docs/.../s2/vendor/`、`rh2/tests/envpack/data/swegym_parser_dumps/`（A1 后随 rh2 测试树走）（新） | parser 来源文件、LICENSE、provenance；精选回归语料 | Claude |
| `docs/.../project1_execution/swe_grading_wiring_20260915/` | 已有审查探针；新增 `precheck.md`、对账账本快照、`reconcile.md`、机器与镜像清单 | Claude；Codex 复核 |

共享文件（`prepared_task_face.py`、`sandbox_profile.py`、`scoring.py`、`manager.py`）在本片由 Claude 一人修改；A 线若同期要改同一文件，先在 §7 登记顺序。

### 6.4 首批代表题与条件矩阵

条件固定：正式 grader profile（deny_all、rh2grader/54322、2 CPU、4 GiB、tmpfs 1 GiB、pids 512），shm 默认 64 MiB；候选来源三类。B 组 24 条候选在对账前先经受信准备步骤重建候选工件（原补丁 → `git apply --check` → 记录应用方式），对账绑定候选版本；原组、投影组与真实 RH2 结果三者分开列。

| 组 | 题 | 候选 | 重复 | 要回答的问题 |
| --- | --- | --- | --- | --- |
| e1 冒烟（4） | mypy-12741（`-k`）、conan-13326（`eval_commands`）、dvc-5822（纯 Python）、pandas-48106（编译型） | gold、noop | ×1 | 新用户权限、安装产物、初始化与安装耗时、账本可解释 |
| A 仓库配方代表（9） | 上述 4 题 + dask-7894、moto-6913、modin-6937、pydantic-8500、MONAI-6975 | gold、noop | ×2 | 每仓库配方在真实链下能否得到"noop 未解决、gold 解决"，重复是否一致；gold 例外先由 S1-p 预检解释 |
| B 真实候选（24） | 昨夜 24 条 DeepSeek 补丁（`ledger/cc_patches/`），其中 7 题严格 apply 可能失败 | 重建后的候选工件 | ×1（其中 6 题 ×2） | rh2 判定与两组 oracle 逐题对照；不一致逐 ID 解释 |
| C 反例与边界 | MONAI-1121 gold（无预置 / 预置权重，D4）、MONAI-3205 gold、moto-4799 gold（服务依赖）、MONAI-763 gold（shm 64 MiB / 1 GiB）、MONAI-2454 候选（同名测试文件 → 投影是否丢解答）、pandas-50319 与 48106 候选（ID）、mypy-11236/11352/16869 候选（`-k`）、conan-14296 候选（`eval_commands`）、pydantic-5706 候选（官方通过但覆盖不足，只记录） | 按题 | ×1 | 每类反例在真实链下的表现与归因标签 |

规模约 85 次评分。阶段一耗时（中位 2–3 分钟、pandas 重编译约 700 秒、modin 最长 18 分钟）是 root、无安装段、不同 profile 下的旧条件估计，**不作为已验证的预算**；e1 实测安装与初始化耗时后再定 e2 并发与总时长。

### 6.5 账本字段（每次评分一行 JSONL）

```text
run_id, task_id, source, image_ref, image_digest_expected, image_digest_actual,
image_local_build (bool), image_id_actual, derived_image_recipe (nullable)
candidate: {kind: gold|noop|cc|contrast, patch_sha256, origin, apply_method: git_apply|apply_failed, apply_user}
classification: {verdict, reasons}
projection: {included_paths, ignored_paths, projection_digest}
policy: {profile_id, runtime_profile_digest, network, user, cpus, memory_bytes, shm_bytes, tmpfs}
budgets: {candidate_stage_seconds, grading_deadline_seconds}
report: {report_id, outcome, failure_category, reward, f2p_pass, f2p_total, p2p_fail, p2p_total, grader_version, regrade_total}
phases: {candidate_stage, grader_start_and_verify, grader_baseline_rebuild, delta_apply, grader_trusted_setup, install, test, parser_and_report, grader_cleanup}
install: {rc_last_command, seconds, effect: {kind: import_path|rebuilt_artifact|version_string, value, source: root_observation}}
test: {rc, seconds}
diagnostics: {reference_missing_f2p, reference_missing_p2p, reference_skipped, parsed_cases_in_segment, parsed_cases_outside_segment, runner_integrity_changed (bool|null)}
resource: {mem_peak_mb, mem_peak_unavailable_or_zero (bool)}
log: {path, sha256, partial (bool)}
reference: {oracle_group: original|projected, oracle_run_tag, oracle_verdict, per_id_diff_count}
notes
```

`diagnostics`、`install.effect`、`runner_integrity_changed` 都是观察，不进入 reward；`reference` 来自昨夜与阶段一的 oracle 账本，`oracle_group` 必填。

### 6.6 验收清单与命令

在 §3 四条之上具体化为十一项，全部满足才算"接线完成"；第四组 A、B 未决的两类行为单列"未验收"，不计入总括结论：

1. **命令契约**：216/216 渲染测试命令 == `official_test_line`（含 3 条资源文件案例）；安装行 == spec `install`；conan 12 题含 `eval_commands`；恢复/保护清单未缩减。命令：`cd rh2 && .venv/bin/pytest tests/envpack/test_vendor_specs.py -q`。
2. **parser 函数回归**：441 份本机语料 0 条状态映射不一致（或逐条解释）；入库子集在无语料时也跑。命令：`RH2_SWEGYM_PARSER_CORPUS=<runs 目录> .venv/bin/pytest tests/envpack/test_swegym_parsers.py -q`。
3. **v2 入口判定小样例**：参考缺席 → NO；全部 SKIPPED → FULL 且诊断记 `reference_skipped`；零解析 → manager infra；段内空、段外有 PASSED → 状态映射为空、`parsed_cases_outside_segment` 非零；坏码/缺标记 → `apply_ok=False`。
4. **渲染与 fixture Docker**：安装段以 54322 执行且 `RH2_INSTALL_RC` 被记录；official 测试文件 root:root 0644；`docker inspect` 显示 `--shm-size` 且 `runtime_profile_digest` 随之变化。命令：`.venv/bin/pytest tests/adapters/test_w1b_prepared_task_face_v2.py tests/grading/test_w3b_grader_profile_docker.py -q`。
5. **候选真的进了 grader**：预期路径 = 当前控制面规则下的 candidate entries（含普通新增文件）；fixture 中核对重放后的内容、mode、增删与 symlink；至少含一个普通新增文件、一个"测试文件改动被忽略但修复保留"的对照；`git diff <base>` 只留作日志。
6. **安装作用于候选**：root 观测 exec 记录包导入路径在 `/testbed` 下（可编辑安装）或编译产物更新（pandas 版本串带 `.dirty` 或 `.so` mtime 晚于容器启动）；`rc_last_command` 只记段末命令退出码，不单独定"成功"或"失败"；未证明生效的题记"安装未验收"，不改成 0、None，也不新增排题规则。
7. **noop/gold/候选判定**：noop → `unresolved/tests_failed` 且 F2P 失败集合 == 官方 F2P；gold → `resolved`，例外先由 S1-p 与 D4 解释（预期例外：MONAI-1121 无预置、pandas-48106 ID、MONAI-3205、moto-4799）；24 条候选 rh2 判定与对应 oracle 组逐题对照，例外逐 ID 解释（MONAI-2454 的 UNPARSED 单独说明；7 题严格 apply 失败的按 `apply_failed` 记录，不改补丁）。
8. **链路稳定**：A 组 ×2 的 outcome 与四计数完全一致；不一致的题标 `chain_unstable` 并附两份日志。
9. **不伪装**：所有 reward=None 都有 infra 族归因与阶段；没有为跑通而伪造的 0；`mem_peak_mb=0` 一律带 `unavailable_or_zero`。
10. **超时证据可查**：候选已输出安装退出码与测试标记后超时的案例，落盘日志含这两项、`log.partial=true`、清理成功、reward=None（FakeDocker 单测 + e1 至少一例人为超时）。
11. **差异有解释**：`reconcile.md` 对每条 rh2≠oracle 给出归因（parser、投影、安装、网络、资源、参考集、候选重建），不要求改 rh2 追平总分。

### 6.7 需要用户决定的事项

**用户决定（2026-09-15）**：D1 = A（vendored）；D2 = A（候选段安装，最小改动；后续发现问题再修）；D3 = A（conda 前缀交给候选用户，运行器完整性只作观察）；D4 = 先 A（诊断性派生镜像验证准备方案），B（正式固定环境版本）留到流水线阶段完成后再做。C1–C6 未提出异议，按其执行。以下保留决策包原文供追溯。

**D1 · vendored fork parser（T0：引入 fork 代码）**
- 要决定：SWE-Gym 9 个仓库的日志 parser 从哪来。
- 代码事实：安装的 swebench 4.1.0 在 spec 注册表就缺这些仓库；fork 不能与 4.1.0 同名共装；需要的只有两个函数与一张映射，共约 60 行；两线审查都支持只复制同一已选来源的实现，不引入新的评分规则。
- 方案：A. vendored 进 `envpack/swegym_parsers.py`，pin commit 与 sha256，配回归语料（推荐）；B. 另建含 fork 的 venv，评分时子进程调用（多一套环境，跨进程传日志，慢且难测）；C. 运行时 monkeypatch 4.1.0 的映射（脆弱，升级即断）。
- 长期代价：SWE-Gym 更新 parser 时重新 vendored 并跑语料；以后可换成 B/C 而不影响账本格式。

**D2 · 安装段放在候选段（T1，但偏离官方顺序，请确认）**
- 官方顺序：安装 → 恢复测试文件 → 应用 test_patch → 测试。rh2 拆分后可信 setup 先做恢复与 test_patch，安装只能放在其后的候选段。这是有意的顺序调整，**尚未证明等价**：pandas-48106 历史日志里 empty 构建的版本串为 `g8b72297c87`、gold 为 `g8b72297c87.dirty`，说明安装会读取 Git 工作区状态；但它没有证明交换顺序会改变分数。
- 方案：A. 候选段安装（推荐；候选用户执行，符合 D2-3；e1/e2 对账检查安装产物与逐测试结果，未见实质差异前不加 manager 阶段）；B. 在 manager 加一个可信 setup 之前的候选安装阶段（候选代码在控制面保护前运行，且要改 manager）；C. root 安装（违反 D2-3，不采）。

**D3 · 候选用户对 conda 环境的写权限（T0：安全边界，这是实际的权限扩张）**
- 要决定：是否让候选用户能写 `/opt/miniconda3/envs/testbed`，以便非 root 安装能写 site-packages 与 `bin`。
- 代码事实与真实代价：今天 site-packages 是 root 属主，候选代码在测试阶段以 54322 运行、**改不了 pytest 及其插件**；前缀交给 54322 后，候选可以在安装段替换或 monkeypatch 测试运行器，official 测试文件保护（root:root 0644）挡不住"运行器本身被换掉"。只交出 site-packages 子目录或改用 `--user` 安装都不能消除这一点：pytest 就住在 site-packages，而用户 site 在 `sys.path` 里排在系统 site 之前。因此 D3 实质是"接受候选能安装依赖，就等于接受候选能影响测试运行器（仅限本次 fresh grader）"，与"不安装"二选一。fresh 容器只消除跨次污染。
- 方案：A. 可信初始化 `chown -R 54322 /opt/miniconda3/envs/testbed` 并写自证键，official 文件保护保持，S1-m 的运行器完整性摘要作为观察而非闸门（推荐；不新建反作弊工程）；B. 只交出 `lib/python*/site-packages`（console scripts 与编译型可能失败，运行器可改写的代价相同，A 线已指出不要预先承诺此收窄）；C. 不安装（验收项 6 对编译型与依赖变化题不成立）。
- 成本：整前缀 chown 的耗时未实测；grader 现有 init 预算 300 秒不是实测依据（rollout 的 900 秒是另一个配置）。e1 记录实际耗时，不预先调整正式资源数值。
- 若选 A，本片非目标增加一条："测试运行器完整性不在 F2 保护范围内"。

**D4 · 离线安装的预置方式（T0：改变评分输入）**
- 要决定：moto、pydantic、dask 在 deny_all 下安装失败，本片怎样处理。
- 方案：A. 在机器上为代表题手工构建诊断性派生 grader 镜像（联网跑一次 `pip download` 得到 wheel 缓存，安装段用 `PIP_NO_INDEX=1 PIP_FIND_LINKS=/rh2/wheels`，缓存放工作区外；pydantic 另需把 PDM 放到候选用户可用的 PATH；MONAI-1121 权重放候选用户可读的缓存路径），运行时仍 deny_all；driver 用 `image_local_build=True` 启动并记录实际 image ID，账本区分原环境包身份、派生配方与实际 grader 镜像（推荐，本片只为 moto-6913、pydantic-8500 与 MONAI-1121 做）；B. 现在就产出正式的新环境包行（需要 ingest 工具与 lineage 变更，延迟接线）；C. 不预置，只记录安装退出码，三个仓库 93 题不宣称"安装作用于候选"。
- 长期代价：A 的产物是诊断镜像，不进正式数据，不能充当原环境已合格的证据；正式环境包版本机制留到流水线定案。

**需确认（不是新决定）**
- C1 reward 语义不变；口径按实测改写：参考 ID 缺席计失败，PASSED/XFAIL 计成功，SKIPPED 不进两桶（全部 SKIPPED 可得 FULL），manager 零解析仍是 infra；严格计数只作诊断。
- C2 R2E 只写决策包，代码放第二片。
- C3 第四组 A 覆盖"可归因于候选的编译、导入、收集与安装失败如何表达"，B 覆盖"合法解答与测试配置、插件、构建配置等控制面的划分"；它们各自阻塞对应行为的正式验收，不阻塞命令派生、来源 parser、shm、driver 或无关题的对账；未决项在报告里单列，不被总括结论掩盖。
- C4 机器：现有实例 SSH 连接被关闭，需要重新开机或重租，`bootstrap_box.sh` 可复用，凭据仍只从 `tmp/API.md` 读；机器上设置 `MILES_RH2_RUN_ID`。
- C5 本片不新增数据源枚举，仍是 `swe_gym_lite`。
- C6 S1-m 是 A 线共享文件上的 T1 改动，先在 §7 登记归属再做；不改判定、契约或期限语义。

### 6.8 本片不改变的语义与非目标

不改 `GradingReport`、timing 契约与二值 reward；不改 D2-1～3 与 deny_all；不放开任何阶段的网络；不修改 expected、测试或题面；不新增排题规则；不写 R2E 代码；不改评分队列与期限语义；不为接线另造通用 shell 命令解析器、全树校验闸门或反作弊平台；诊断性派生镜像不等于正式环境资格；不要求 216 题全量通过（全量在流水线实施阶段做）；不把 driver 通过当作 Claude Code、训练或 GPU 链验收。若 D3 选 A：测试运行器完整性不在 F2 保护范围内，只作观察。

### 6.9 对 §8–§10 审查意见的回应（四选一）

| 意见 | 回应 | 落在哪里 |
| --- | --- | --- |
| A-R1 分类后再投影 | accepted | 6.1 driver 前置行；S1-d 流程 |
| A-R2 候选容器期限、持久化与清理 | accepted | S1-d 的两份预算、owner、释放与 `finally`；验收项 10 |
| A-R3 派生镜像身份 | accepted（仅 D4 分支） | 6.1 派生镜像行；D4 方案 A；账本 `image_local_build/image_id_actual` |
| A-R4 Git diff 不是投影 oracle | accepted | 验收项 5 改写 |
| A-R5 silent success 口径 | accepted | 6.1 parser 行；C1 改写；验收项 3 |
| A §8.2 D2 删除"九仓库无影响" | accepted | D2 改写，保留 pandas `.dirty` 证据及其边界 |
| A §8.2 D3 如实说明权限扩张与成本 | accepted | D3 改写；成本改为未实测 |
| A §8.3 安装 RC 不能单独证明成功/失败 | accepted | S1-c/S1-m；验收项 6；账本 `rc_last_command` |
| A §8.3 gold 输入、shm 记录、grader_version、契约测试形态 | accepted | S1-d `export_gold_candidate`；S1-c shm 进 digest；S1-b `grader_version`；S1-a/S1-c 测试断言事实而非快照 |
| A §8.4 顺序与 85 次估计不作已验证 | accepted | S1-e 拆 e1/e2；6.4 备注 |
| B-B1 43 条测试命令不同 | accepted | 6.1 选择器行；S1-a；验收项 1 |
| B-B2 新 parser 日志边界 | accepted | S1-b 只解析标记段；验收项 3 |
| B-B3 旧候选重建与两组 oracle | accepted | 6.1 数据行改正计数；6.4 B 组重建步骤；账本 `apply_method/oracle_group` |
| B-B4 账本数据出口与内存 0 语义 | accepted | 新增 S1-m；验收项 9/10；账本 `partial/unavailable_or_zero` |
| B-B5 非 root 资产预检 | accepted | 6.1 非 root 行；D3/D4 与 e1 预检；`pre_install` 不重跑 |
| B §9.2 三处说明改写（KeyError 位置、gold 输入、"记成候选失败"） | accepted | 6.1 对应行 |
| A-Claude §10.2 D3 的运行器完整性代价 | accepted | D3 改写；S1-m 运行器摘要；6.8 非目标 |
| A-Claude §10.3 五条遗漏（安装计时与期限、gold 静态预检、profile digest、补丁应用用户、重评分与标签） | accepted | 6.1 超时行；新增 S1-p；6.1 shm 行；S1-d 以候选用户应用；账本 `regrade_total` 与 `MILES_RH2_RUN_ID` |
| A/B 均指出：审查意见不代替用户批准 D1–D4 | accepted | 6.7 保持为决策包 |

没有 rejected 或 deferred 项；没有以"接受残余风险"处理的项。

### 6.10 实施状态（2026-09-15，Claude；待 A/B 复核）

| 切片 | 状态 | 证据 |
| --- | --- | --- |
| S1-a | **已实施、已验证** | `spec_vendor.py` 新增 `derive_install_cmd / derive_eval_commands / derive_test_directives / derive_test_command(_for_bundle)`；`tests/envpack/test_vendor_specs.py` 216/216 官方行逐字相等（含 moto-4847/7607、dvc-5336 资源文件案例），恢复/保护清单未缩减 |
| S1-b | **已实施、已验证** | `envpack/swegym_parsers.py`（fork 两函数 + 13 仓库映射，来源文件逐字节副本与 provenance 在 `s2/vendor/`）；`scoring.parse_eval_log_v2` 只解析标记段，`EvalVerdict` 新增四个带默认值的诊断字段（T1）；入库语料 18 份 + 本机 441 份全部与 fork 状态映射一致；六个判定小样例通过；`scoring.py` 顶部"缺席按通过计"注释已改正 |
| S1-p | **已实施** | `swe_grading_wiring_20260915/precheck_gold_classification.py` → `precheck.md`：A 组 9 题 gold 无被忽略路径；37 份补丁中 21 份部分被忽略（DeepSeek 候选写的测试文件按 D2-3 不重放；pydantic 候选改了 `pdm.lock/pyproject.toml`，将进入安装段） |
| S1-c | **已实施、已验证（含 Docker）** | 候选段 = vendor env → 安装段（`RH2_PHASE_START/END=install`、`RH2_INSTALL_RC`、`RH2_TS_*`）→ 官方标记 → 派生测试命令；可信 setup 段加入 `eval_commands`；`GraderSandboxProfile.shm_size_bytes` 与 `candidate_writable_prefixes`（进 `to_parameters/digest`、`--shm-size`、`RH2_GRADER_SHM_BYTES` / `RH2_GRADER_CANDIDATE_WRITABLE_PREFIXES`）；权限布置脚本 chown 存在的前缀并自证 `WRITABLE_PREFIXES_DONE/MISSING`；`inspect_facts.shm_size`；`scripts/sandbox_probes/grader-protect-control-surface.sh` 已重新 dump。fixture Docker：安装段以 54322 执行、可写前缀写入成功、`RH2_SHM_KB=131072`、official 文件仍 root 0644、`false; true` 段末 rc=0 |
| S1-m | **已实施、已验证（含 Docker）** | manager：候选输出 `tee` 到 `/rh2/candidate/eval.log`（候选属主），超时时 root 读回部分日志进 `eval_log_partial`；`candidate_facts_from_log` 抽安装退出码与 install/test 秒数；候选段前/后 root 观测脚本（`RH2_OBS_*`，非致命）；`<ref>.diagnostics.json` sidecar（候选事实、观测、控制面/可信 setup 自证、解析诊断、`peak_memory_unavailable_or_zero`、`runner_integrity_changed`）。真实容器：候选输出后 `sleep 120` 超时（6 s 预算）→ reward None、日志含 `RH2_INSTALL_RC=0`、sidecar `log_partial=true`、无容器残留 |
| S1-d | **已实施、FakeDocker 验证；真实链端到端待机器（e1）** | `adapters/slime/replay_grade.py` + `scripts/replay_grade.py`：走 actor 同一读取口、fresh 候选容器（rollout profile 参数 + 可信初始化）、materialize 探针、B1 census、候选用户 `git apply --check`（失败即 `apply_failed` 停止，不 fuzz）、B2 导出、`classify_frozen_patch`、D2-3 投影、持久化后释放容器、`grade(workspace=None, deadline_monotonic=…)`、账本行（§6.5）。六个单测：noop 经派生镜像分支评分成功、apply 失败不评分、候选阶段超时记录 `candidate_stage_timeout:<stage>` 且容器清理、digest 路径、评分异常记录不吞行、gold 导出。**偏离**：计划里的"本机 fixture 镜像端到端一次"没有做——fixture 仓库不在 SWE-Gym vendor 映射内，driver 真实端到端只能在机器上对真实镜像做（e1） |
| S1-f | **已写决策包** | [r2e_result_expression_decision_20260915.md](swe_grading_wiring_20260915/r2e_result_expression_decision_20260915.md)：推荐泛化为"参考状态表"（方案 B，两步落地），A/C 为备选；R2E 代码放第二片 |
| S1-e | **待机器（C4）** | [runbook_s1e.md](swe_grading_wiring_20260915/runbook_s1e.md)（同步、venv、prepare/export-gold/run、e1 通过标准、回传）；[derived_images/README.md](swe_grading_wiring_20260915/derived_images/README.md)（D4=A 三份配方骨架） |

测试与静态检查（本机，2026-09-15）：`ruff check src tests scripts` 无告警；非 Docker 套件 842 passed / 1 skipped；Docker 套件 `test_w3b_grader_profile_docker.py` + `test_manager_docker.py` 30 passed（含 S1-c/S1-m 新增 4 例）。全量 441 份语料用 `RH2_SWEGYM_PARSER_CORPUS=runs/env_probe_stage1_20260910/ledger` 跑过一次通过。

其它 T1 记录：`official_cmd_contract_216.json` 的 `install_step_in_eval` 是 2026-09-09 的 `pip install` 子串启发式，pydantic 20 题被记成 False，不作 oracle（测试注释已说明，JSON 不改写）；`GradingEnvSpec` 新增两个可选观测脚本字段；`_ContainerRecord` 新增 `observations / candidate_facts / diagnostics`；`GraderPhaseTiming` 分段集合未动，install/test 秒数只在 sidecar。

### 6.11 对 §11–§12 实施复核的回应与修正（2026-09-15，Claude）

逐项按源码核实，全部成立；处理与证据如下（都已实施，本机通过；真实镜像仍待 e1）。

| 项 | 回应 | 修正与证据 |
| --- | --- | --- |
| I1 观测脚本以 root 执行候选代码 | accepted | `manager._observe` 增加 `user/home`，前/后观测都以候选 UID/HOME 执行（前观测也必须：候选 delta 已应用、`cd /testbed` 让 cwd 进 sys.path）；渲染器文档改为"以候选身份执行、只作诊断线索"。单测 `test_i1_observation_scripts_run_as_candidate_user` 断言两次观测 exec 都带 `-u 54322` 与 `HOME=/home/rh2grader`；fixture Docker 观测用例在候选身份下仍通过 |
| I2 候选容器清理失败仍继续 | accepted | driver `_remove_container` 改为 rm → inspect → running 则 kill → 再 rm，有界、CLI 异常只留痕；不能确认移除时写账本行 `candidate_container_cleanup_failed` 并抛 `ReplayHaltError` 停止本批（CLI 退出码 2）。持久化改到释放容器之前（`finally` 先落 artifact 再 rm）。单测 `test_i2_cleanup_failure_halts_batch_after_recording` |
| I3 运行手册装不出环境 | accepted | runbook 改为 `pip install -e . --group swe --group dev`（pip ≥ 25.1）或显式同 pin 列表，并核对 swebench 4.1.0；同步清单不再需要 docs 下的 oracle（见 A1）；镜像预拉由 driver 单独预算完成；回传补 `artifacts/`；派生镜像页删掉不存在的 `--image-local-build` |
| I4 总期限耗尽丢部分日志 | accepted | `_read_candidate_log_partial` 不再看评分期限剩余，用独立有界收口预算（min(30 s, cleanup_timeout)）；外部取消（`CancelledError`）路径同样读回后原样上抛 |
| I5 零解析丢 parser 诊断 | accepted | `_parse_eval_log` 先把 verdict 存到 `record.parsed_verdict` 再抛零解析 infra；`_diagnostics(None)` 回退到它。单测 `test_i5_zero_parsed_keeps_parser_diagnostics_in_sidecar`：sidecar `verdict.num_parsed_outside_segment=1`、`reference_missing` 非空、reward 仍 None |
| I6 取消无账本行 | accepted | driver 捕获 `CancelledError`：候选阶段记 `cancelled:<stage>`、评分阶段记 `cancelled:grading`，落账后原样上抛。单测 `test_i6_cancellation_writes_row_then_propagates` |
| I7 测试退出码无出口 | accepted | 渲染器在测试命令后立即 `RH2_TEST_RC=$?`，End 标记之后 `echo` 出来；`candidate_facts_from_log` 抽 `test_rc`；driver 账本 `test={rc, seconds}`。只进诊断，不作闸门 |
| A1 契约 oracle 未跟踪 | accepted | `official_cmd_contract_216.json` 复制到 `rh2/tests/envpack/data/`（测试读它；docs 下 B_materials 原件存在时断言逐字节相同），入库语料从 `docs/s2/` 移到 `rh2/tests/envpack/data/swegym_parser_dumps/`（19 项含 MANIFEST）。两者随 rh2 代码一起提交即可 |
| A2 安装段共用 test 预算与标签 | accepted（部分） | 超时归因文字追加 `:candidate_phase=install|test|unknown`（按部分日志的阶段标记，`candidate_phase_at`）；预算仍共用一份 1800 s，拆分留到 e1 拿到 sidecar 的 install/test 秒数之后（runbook 已写核对项）。legacy 路径文案不变（`test_manager_docker` 的精确断言仍成立） |
| A3 root 读 tee 文件跟随符号链接 | accepted | 读回命令改为 `[ -f ] && [ ! -L ]` 守卫，否则视为不可用（返回空串）。单测 `test_a3_partial_log_read_refuses_symlink_and_ignores_deadline` |
| §11.3 driver 单测未覆盖正式 profile 组合 | accepted | 新增 `test_formal_profile_combination_fills_install_test_and_observations`（可信 setup / 权限布置 / 候选段替身 + 候选容器初始化）：账本 `install`、`test`、`observations`、`runner_integrity_changed` 全部填充 |
| §11.3 首次拉镜像消耗候选预算 | accepted | driver 在候选阶段前 `image inspect || pull`，独立 `--image-pull-seconds`（默认 1800 s）；单测 `test_image_pull_uses_its_own_budget` |
| §11.3 R2E 决策包三处事实 | accepted | 决策包已更正：SWE 不是精确映射特例（XFAIL 计成功、SKIPPED 不入桶）；A 也改契约（只是不改旧字段）；C 是暂缓接入。用户已选 A |
| §11.3 派生镜像 tag 重指 | no_fix_accept_residual_risk | 有条件剩余风险；派生镜像页要求构建后立即记 image ID、运行前后各 inspect 一次 |

本轮验证（本机）：`ruff check src tests scripts` 无告警；`tests/adapters` + grading 单测 + `tests/envpack` 827 passed / 1 skipped，另 `test_w3b_grader_profile_unit.py` + `test_replay_grade.py` 33 passed；Docker 套件 30 passed；全量 441 份语料从新位置复跑通过。未提交、未租机器。

### 6.12 对 §13 修复复核的回应与修正（2026-09-15，Claude）

四项都按源码核实成立（R1 两条中断点、R2 两处手册缺口、R3 取消路径无落盘、R4 inspect 无预算）；全部 accepted 并已修：

| 项 | 修正 | 证据 |
| --- | --- | --- |
| R1 候选收口两个中断点 | `finally` 内持久化用 try 包住（失败只记 `persist_failed:<exc>`），清理一律执行；清理 `await` 用 `asyncio.shield` 包住，清理期间首次取消先等这个有界清理跑完、记 `cancelled:cleanup` 与结果，再传播取消；持久化失败在清理完成后停止本批（`ReplayHaltError`）。派生镜像 inspect 失败/超时也改为落账返回，不再以异常逃出 `replay_one` | `test_r1_persist_failure_still_removes_container_then_halts`（artifacts 目录换成普通文件 → `NotADirectoryError`，rm 仍执行、一行账本、停止本批）；`test_r1_cancel_during_cleanup_waits_for_removal_and_records`（rm 延迟 0.6 s、0.3 s 取消 → 容器已移除、账本 `cancelled:cleanup`、取消照常传播） |
| R2 手册同步与安装 | 同步清单改为整个 `s2/`（含 `raw/swe_gym_lite_full_f70b1a29.jsonl`、`image_manifest_keyed.json`）与 `data_freeze/`；安装改为 `uv sync --locked --group swe --group dev`（消费 `uv.lock` 与 `[tool.uv.sources]` 的 verifiers Git pin），备选 `requirements-replay.lock`（本机 `uv export --frozen --no-hashes --no-emit-project --group swe --group dev` 导出，506 行，含 `swebench==4.1.0`、`verifiers@5885ab9c…`，已放 `rh2/`） | 文档与导出文件；未在新机器实跑（机器未租） |
| R3 取消后日志不落盘 | manager `_grade_within_deadline` 增加 `except CancelledError`：把 `_infra_log_text()`（完整或部分候选日志）与诊断 sidecar 落盘（纯文件 IO），引用挂 `record.cancelled_eval_log_ref` 后原样传播；候选段正常结束即先把完整日志放到 `record.eval_log_partial`，后观测期间取消也不丢；driver 取消评分时从该引用填账本 `log` / `diagnostics_ref` / `install` | `test_r3_cancel_during_post_observation_persists_full_log`、`test_r3_cancel_during_candidate_exec_persists_partial_log`（manager）；`test_r3_cancelled_grading_row_references_persisted_log`（driver 正式 profile 组合） |
| R4 镜像预算未包住 inspect | `image inspect + pull` 整体用 `--image-pull-seconds` 包住，超时记 `image_pull:timeout`；拉取期间取消记 `cancelled:image_pull` 落账后传播；派生镜像 inspect 同预算 | `test_r4_image_budget_covers_inspect_and_cancel_during_pull`（inspect 延迟 0.5 s / 预算 0.05 s → 未创建候选；拉取期间取消 → 有账本行） |

本轮验证（本机）：ruff 无告警；grader-profile 单测 + driver 单测 39 passed；adapters + grading 单测（含 grader-profile）+ envpack 856 passed / 1 skipped；Docker 套件 30 passed。真实 x86 镜像端到端仍待机器。

### 6.13 夜间连续执行状态（2026-09-16，Claude；用户 09-16 确认"可以开始执行"）

| 项 | 状态 | 证据 / 位置 |
| --- | --- | --- |
| e2 代表批 | **已完成（机器 1，78 行，无 halt）**：28 张镜像 → 三张派生镜像（metacopy 关、完整性核对通过）→ 双 lane。B 组 24 条候选：可比 15 题 15/15 与投影组 oracle 一致、7 题 apply 失败（既知 fuzz 题）、2 题 modin 环境侧 infra；A 组 9 题 7 题 gold/noop ×2 达标，pandas（脆弱 ID）与 modin（环境）例外；C 组反例与派生镜像按预期（MONAI-1121 派生 resolved；MONAI-763 shm 1 GiB 触 4 GiB OOM） | 证据 `runs/swe_grading_wiring_20260915/e2/`；报告 [e2_report_20260916.md](swe_grading_wiring_20260915/e2_report_20260916.md)；对账 [reconcile.md](swe_grading_wiring_20260915/reconcile.md) |
| e2 代码版本与回归 | e2 = P-B 之后、P-C/P-D/P-A 之前；**真机回归已完成**（25 行，`rh2/experiments/run_regression_post_e2.sh`，新代码同步到机器 `/work/code/rh2_next`）：7 题 gold → 6 条资格，noop / 候选结论与 e2 逐题一致；人为语法错误补丁 dvc-5822 带资格 → `candidate_execution_failed`（test_startup，复证行指到 `dvc/repo/__init__.py:145`）、无资格 → infra None；moto-6913 同类补丁只造成逐测试失败，照常 tests_failed | 回归账本 `runs/swe_grading_wiring_20260915/e2/reg/`；e2 报告 §6 |
| 第四组 P-B / P-C / P-D / P-A | **已实施、本机验证**（ruff 无告警；contracts+adapters+governance 1118 passed；grading+envpack 非 Docker 287 passed / 1 skipped；Docker 3 + 30 passed） | [batch4 实施记录 §9](batch4_scoring_20260910/impl_plan_20260915.md#9-实施记录2026-09-16-夜间claude已实施本机验证真机回归待-e2-之后) |
| P-A 账本新列（§6.5 增补） | `image_identity`、`scripts_digest`、`env_qualification`（`absent` / `ok:<来源>` / `*_mismatch`）、`reference_missing_count`、`execution_failure_decision`（trigger / kind / rule / missing / resource / compile_probe）、`resource_facts`；`report` 块增 `execution_failure_stage`、`execution_failure_evidence`、`grading_semantics`；CLI `run --qualification-ledger <path>`（可重复） | `adapters/slime/replay_grade.py`、`scripts/replay_grade.py` |
| A2 预算拆分 | e2 实测：安装段中位 9 s / p90 40 s / 最大 597 s（pandas），测试段中位 7 s / p90 32 s / 最大 742 s（MONAI-1121 派生）；建议安装 900 s + 测试 1800 s 两份预算（T1，待 A 线复核） | e2 报告 §5 |

## 7. 实施与复核记录

| 日期 | 进展/决定 | 下一步 |
| --- | --- | --- |
| 2026-09-15 | 按用户要求建立本页；仅形成计划，未改代码、运行新实验或派发 A 复核。 | 在本页补具体修改范围、代表题与实施分工，再推进接线。 |
| 2026-09-15 | Claude 补 §6 实施计划：核对代码事实（安装段缺失、mypy `-k` 渲染错误、parser 映射缺 9 仓库、shm 缺旋钮、契约不改）；六个切片、文件归属、代表批矩阵、账本字段、九项验收、D1–D4 决策包。更正：昨夜 `grader_user` 变体的安装由 root 执行，非 root 安装尚无证据。未改代码、未跑实验。 | A/B 两线复核 §6；用户决定 D1–D4 与确认 C1–C5；S1-a、S1-f 可先开工。 |
| 2026-09-15 | A 线 Codex 完成 §8 计划审查：独立 Production Tracer / Falsifier 追踪，主审运行四类窄 CPU 对照。方向认可，需补分类、候选容器生命周期、派生镜像身份与验收口径；D3 权限扩张必须如实说明。未改生产代码、未启动机器或评分批次。 | Claude 按 §8 修订本页后分片实施；现有授权内的 S1-a、S1-f 和 parser 回归材料准备可继续。审查意见不代替用户批准 D1–D4。 |
| 2026-09-15 | B 线 Codex 独立复核见 §9：保留 R1–R5；补充非 mypy 选择器、日志解析边界、旧候选重建、异常日志出口与非 root 资产预检。主审复跑 CPU 接缝对照；未改生产代码或运行远端评分。 | Claude 将 §8–9 的最小修订合入 §6，再按小切片实施；不新增一套审批或筛查平台。 |
| 2026-09-15 | Claude 按 §8–§10 修订 §6：合入 A-R1～R5、B-B1～B5、§10.2/§10.3 全部意见（§6.9 逐条 accepted）；改正候选 oracle 计数为原组 13/7/3/1、投影组 13/8/3/0；新增 S1-p（gold 静态预检）与 S1-m（manager 最小观测出口，A 线共享文件，待登记）；S1-e 拆冒烟与矩阵；D2/D3/D4 与 C1/C3 按审查改写，D3 写明运行器完整性代价。未改代码、未跑实验。 | 用户决定 D1–D4、确认 C1–C6；S1-a、S1-p、S1-f 与语料整理可立即开工；S1-m 归属登记后实现。 |
| 2026-09-15 | 用户决定 D1=A、D2=A（最小改动，问题后修）、D3=A、D4=先 A 后 B（B 留到流水线阶段）；C1–C6 无异议。Claude 登记 S1-m（`grading/manager.py` 三项最小观测出口）的修改归属：Claude 实现、A 线复核，实施顺序在 S1-c 之后、S1-d 之前。开工顺序：S1-a → S1-b → S1-p → S1-c → S1-m → S1-d → S1-f；S1-e 等机器。 | 按切片实施；每片完成后在本表登记验证结果。 |
| 2026-09-15 | Claude 实施 S1-a/b/p/c/m/d/f（见 §6.10）：命令派生与 216 契约、vendored parser 与 v2 入口、gold 静态预检、安装段与 shm/可写前缀、manager 观测出口与 sidecar、真实链 driver 与 CLI、R2E 决策包、S1-e 运行手册与派生镜像配方骨架。ruff 无告警；非 Docker 842 通过；Docker 30 通过。未提交。 | A/B 两线复核 §6.10 与代码；用户看 R2E 决策包；机器恢复后按 runbook 跑 e1。 |
| 2026-09-15 | 用户决定 R2E 结果表达先选 A。Claude 按 §11–§12 修正 I1–I7、A1–A3 与 §11.3 三项（§6.11 逐条 accepted，仅派生镜像 tag 重指记为接受剩余风险）；oracle 与语料移入 `rh2/tests/envpack/data/`；driver 加镜像预拉预算、清理失败停止本批、取消落账；manager 观测以候选身份执行、超时读回不受期限限制且不跟随符号链接、零解析保留诊断、归因注明阶段。本机 ruff 无告警、单测 827+33 通过、Docker 30 通过、441 语料通过。 | A/B 复核 §6.11；用户租机器后按 runbook 跑 e1。 |
| 2026-09-15 | Claude 按 §13 修正 R1–R4（§6.12 逐条 accepted 并已修）：候选收口在持久化失败与清理期间取消下仍完成有界清理并落账；运行手册改为整个 `s2/` + `data_freeze/` 同步与 `uv sync --locked`（备选 `rh2/requirements-replay.lock`）；manager 取消路径落盘日志与 sidecar 并挂引用；镜像 inspect 与 pull 同预算、拉取期间取消落账。本机 ruff 无告警、单测 856 通过 1 跳过（含 39 项 grader-profile/driver）、Docker 30 通过。未提交、未租机器。 | A/B 复核 §6.12；用户租机器后按 runbook 跑 e1。 |
| 2026-09-15 | e1 真机冒烟（Claude）：机器 bootstrap + `uv sync --locked`，noop/gold 各 4 题；mypy、conan、dvc 三题全部满足冒烟标准（noop unresolved、gold resolved、参考缺席 0、导入路径 /testbed、运行器未变）；pandas 因脚本头 `set -u` 与镜像 conda 激活钩子冲突失败 → T1 去掉 `-u`（对齐 fork），复跑 noop 又因 overlay copy-up 超 300 s 权限布置预算 → 打开内核 overlay metacopy（chown 180 s→11 s，pandas 前缀 5.5 s），gold 复跑（metacopy 后）：setup 22 s、离线重编译 560 s、F2P 16/16、P2P 失败 3/1020 全是脆弱参考 ID，`unresolved` 与 oracle 的 NO 一致且原因可定位。另按 §13 修正后的 driver 在真机跑通；第四组实施计划按 §5–§6 审查修订并先行实施 S1（exporter 形状错误 typed 化）。报告见 [e1_report_20260915.md](swe_grading_wiring_20260915/e1_report_20260915.md)。 | e2 在 P-B（与可选 P-C）之后跑，机器前置 metacopy；用户决定是否开工 P-B 与 S1 通道选择。 |
| 2026-09-15 | Codex 完成 §6.12 聚焦复核，结论见 §14：原 e1 阻塞核销，可以进入 e1。主审 140 项相关测试通过/1 跳过、30 项 Docker 通过；新版同步目录 26 项通过/1 跳过，四题 prepare/export-gold 成功，Linux 锁解析 dry-run 通过。 | 租 x86 CPU Docker 机器跑四题 gold/noop；全文日志留存、派生检查取消账本及 partial 口径按 §14.2 分期处理，不再阻塞 e1。 |
| 2026-09-16 | 夜间连续执行（Claude，用户确认）：e2 在机器 1 启动（镜像预拉 → 派生镜像 → 双 lane）；本机实施第四组 P-B/P-C/P-D/P-A 并通过全部套件（§6.13、batch4 §9）；P-A 三路判定（已证候选 → `candidate_execution_failed` reward 0；已证资源终止 / 事实不足 → infra、None）、环境资格记录、编译复证、账本新列与 CLI 资格来源；核实 fork 判定在 F2P 桶为空时给 FULL、但真实 pytest 输出下被跳过的参考测试按缺席计失败（伪键 `[N]`），可利用面是候选进程 stdout 可伪造状态行（与 B 线 M2 的 conftest hook 满分同族），记为 T0 待拍板（batch4 §9.6 第 5–6 条）。未提交。 | e2 结束后同步证据、写对账与报告；跑 P-C/P-D/P-A 真机回归；早报列复核清单。 |
| 2026-09-16 | e2 完成（78 行）与真机回归完成（25 行），证据同步到 `runs/swe_grading_wiring_20260915/e2/`；写 e2 报告与对账；P-A 判据按 e2 实测加"安装段偏离资格基线"；modin 定向探针见 e2 报告 §8。未提交。 | 早上：用户裁定 T0（stdout/conftest 伪造、正式链资格来源）与 A2 预算拆分；A/B 线复核 batch4 §9 与 e2 报告；B 线接手 modin / pandas / MONAI-3205 / moto-4799 的清洗规则。 |
| 2026-09-19 | Claude 按 A 线实施审查（R1–R7、三条旧余项）与 B 线 216 题诊断修评分链路：grader 加 `--init`（dvc-2141 gold 在默认 512 配额下 0→1，僵尸 0）；P-A 只复证失败文字点名的候选路径、复证器 `python -I -S`、终止事实未知不归因、参考全缺席但测试正常完成按来源规则；`pids.events` 进资源事实（含超时 sidecar）；安装段 ERR trap 逐命令失败记录；R6 缓存目录一致规范化；R7 结构化冲突证据；正式 actor 资格入口与派生镜像 ID 资格键；日志全文落盘后释放。本机 1401+ 非 Docker、34 Docker 通过；新机器真机对照见 batch4 §10.3。modin 是引擎并发/配额问题（`--init` 不解决）。同日 A 线聚焦复核后窄修 CR1（只认语法异常实际位置并要求复证行号相符）、CR2（剥离 Captured 块、顶层异常规则只限零解析）、CR3（缓存规范化先剪排除命名空间），formal 缓存计数进持久 audit；本机 1407 非 Docker / 34 Docker 通过，真机坏补丁对照复验一致（batch4 §10.4）。再按 CR1–CR3 复核余项修 CR2'（嵌套子 pytest 标题：以外层会话正常完成的收尾行为来源计分依据，batch4 §10.5），并按 footer 复核补两条：收尾行认 `-q` 裸行与 pytest-pretty 块、外层完成必须同时有测试命令退出码 0/1（batch4 §10.6）；本机 1413 非 Docker / 34 Docker 通过，59 份真机日志离线复核无结果变化。用户 09-19 决定：PID 配额与 modin 配方归入后续流水线，参考键按问题类别分位置修（batch4 §10.2）。未提交。 | 用户决定：PID 默认配额、`MODIN_CPUS` 配方注入、参考键逐例处理；B 线继续环境配方修复；正式资格记录随流水线接入。 |
| 2026-09-20 | 本页范围内的代码与文档已提交（`58a14b00`、`e3d120b5`，本地未推送）。下一片 R2E 接线另起一页：[第二步：R2E 经真实 RH2 评分与训练运输闭环](r2e_grading_wiring_20260920.md)（计划稿，含 DR1–DR4 决策包）。 | A/B 线 Codex 复核 R2E 计划；用户决定 DR1–DR4。 |

背景按需查阅：[既有 CPU 证据](env_probe_20260909/morning_followup_20260911.md) · [流水线重排分析](env_probe_20260909/environment_pipeline_redesign_20260911.md)。

## 8. A 线计划审查 / Codex / 2026-09-15

**结论：接线方向合理，§6 需要做以下修订后分片实施；不必等第四组全部定案，也不建议直接把约 85 次评分作为第一次运行。** 本节保留原提案供对照，不将建议改写为用户决定。

审查基线为 `4529ebd77fa27bc4c3bb4f1bffe9657c0af78abb` 与当时工作区中的本计划、既有决定。按审查标准安排了独立 Production Tracer / Falsifier：分别核对实际入口与资源所有权、反例与语义边界；主审复核结论并运行下述 CPU 对照。未复审第三组代码，未修改生产源码、维护测试、配置或依赖，未运行 Docker、SSH、Claude Code、API、GPU 或新评分批次。

### 8.1 实施前应补清的三个接缝

以下是拟议 driver 的 `conditional_future` 问题，不能记成当前生产链已经存在的 P1。

**R1 / P1：S1-d 必须调用已有结构分类器，不能从 export 直接进入可信投影。**

`build_trusted_scoring_projection` 的[前置条件](../../../../rh2/src/repoharness2/grading/trusted_projection.py#L190)就是已经通过 `classify_frozen_patch`；它自身只按控制面规则拆路径。真实 rollout 在 [generate.py](../../../../rh2/src/repoharness2/adapters/slime/generate.py#L3433) 先分类再拆投影。manager 的 digest、血缘和路径集核对不等于 symlink 目标安全检查。

主审 CPU 对照已确认：`src/link -> ../../outside` 或 `../.git/config` 经分类器均为 `unsafe_artifact`，但直接调用 builder 仍会把 `src/link` 放入 projection。最小修订是补回已有分类调用：unsafe 保存证据、不调用 grader；契约矛盾沿既有 fatal 原则停止 driver。合法相对链接仍正常重放，无需给 builder/manager 再增加一份重复检查。

**R2 / P1：S1-d 补上候选容器的期限、冻结持久化与释放责任。**

`grade(deadline_monotonic=...)` 只约束 manager 内部；前面的创建、materialize、census、apply 和 export 不会自动继承其期限。manager 也不拥有 driver 自己创建的候选容器。

计划需明确：候选容器从发出创建请求前记账；候选阶段有界；`--deadline-seconds` 究竟表示整个重放预算还是评分预算，不能进入下一步就重置同一预算。复用现有冻结序列化，保留可重放的工件与 baseline，成功导出并持久化后释放候选容器，评分只依赖冻结输入。外层 `finally` 负责候选容器残留与 manager 收尾；清理使用独立的有限时间，不能因工作期限已过而完全不清理。

验收覆盖创建回包丢失、apply/export 超时、评分取消；保留首个失败原因，两类容器均无运行残留，无法确认停止时结束本批。driver 只同步应用补丁、不启动候选程序时，以唯一写者完成作为冻结的静止前提即可，不必复制整套 rollout barrier、训练队列或恢复系统。

**R3 / P1，仅 D4 分支：手工派生镜像的身份接法尚不完整。**

计划同时写了本地 build 和仅接受 `<ref>@<digest>`。但本地 image ID 不是 registry manifest digest；[manager 实际校验的是 RepoDigests](../../../../rh2/src/repoharness2/grading/manager.py#L1852)。账本中的 `non_formal_image=true` 不会改变这项校验。

最小修订二选一：发布镜像后取得真实 RepoDigest；或在这个非正式 driver 中显式使用已有的 `image_local_build=True` 路径，并记录、核对实际 image ID，不伪造 manifest digest。`GradingEnvSpec` 已有二选一约束，不需要增加通用豁免。保留原环境包身份、派生构建配方和实际 grader 镜像身份三者的对应关系。

现有 manager **允许 rollout 与 grader 镜像不同**，不要额外加同镜像限制。但派生构建若改变 `/testbed` HEAD 或基线文件，仍必须满足已有 baseline 重建检查；缓存尽量放在工作区外。验收一份真实派生镜像能按选定路径运行、错误身份被拒、账本可区别原镜像与实际镜像。

### 8.2 对 D1–D4 的意见

| 项 | 审查意见与最小处理 |
| --- | --- |
| D1 / parser 来源 | 支持方案 A：同一 pinned 来源的少量函数与映射，加许可证和代表语料，维护成本小于另起 venv 或 monkeypatch。只复制同一已选来源的实现并不自动引入新的评分规则；是否需要新的依赖/fork 批准按已有来源授权与协作协议落实，本审查不代用户新增批准。提取与回归材料准备不依赖第四组。 |
| D2 / 安装顺序 | 推荐先按候选段安装推进诊断，但删除“九个仓库都无影响”的结论。官方顺序确为 install → 恢复/注入测试 → test；RH2 方案是可信 setup/保护 → 非 root install/test，是有意的顺序调整，尚未证明等价。代表题对账应检查安装产物及逐测试结果；未见实质差异前，不预先为此增加一个 manager 阶段。 |
| D3 / conda 写权限 | **这是实际权限扩张，需用户批准明确范围。** 候选原来能执行代码，不等于本来就能修改整个 conda prefix；方案 A 同时开放解释器、bin、pytest 与依赖。fresh 容器只消除跨次污染，不能证明本次评分不受影响。若选 A，明确仅 fresh grader 的该前缀交给候选、official 文件保护保持，并实测权限及初始化耗时；不要承诺“以后只 chown site-packages 即可”，安装可能还会更新 console scripts。也不据此扩展成通用防作弊工程。 |
| D4 / 离线预置 | 支持先为明确代表题制作诊断性派生 grader 镜像，保持运行时 deny_all；接法按 R3 补全。这个批准与替换正式环境包应分开，不必现在建设全套正式版本流水线。wheel/权重来源与构建配方可追溯，诊断结果不能直接充当原环境已合格的证据。 |

D2 的具体反证来自既有 pandas-48106 日志：empty 构建的 wheel 版本为 `g8b72297c87`，gold 为 `g8b72297c87.dirty`；empty 在构建之后才应用官方测试补丁。这证明安装不只可能读取测试内容，还可能读取 Git 工作区状态；**它没有证明交换顺序会改变分数**。证据分别在 `runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/pandas-dev__pandas-48106/{empty,gold}/offline/a1/test_output.txt` 的 6022、6044 行。官方配方见 [pinned test_spec.py](https://raw.githubusercontent.com/SWE-Gym/SWE-Bench-Fork/242429c188fcfd06aad13fce9a54d450470bf0ac/swebench/harness/test_spec.py)。

D3 的成本说明也要改：rollout 的初始化超时配置为 900 秒，grader 现有 300 秒预算不是整 conda prefix chown 的实测结果；不能把两者当作已有充分证据。本片测实际开销即可，不预先调整正式资源数值。

### 8.3 安装、评分与验收口径的修订

**安装 RC 既不能单独证明安装成功，也不能直接决定 reward。**

现有 moto-6913 gold 日志中，install 返回 2，随后仍有 18 项测试通过。另一方面，pandas 配方含 `pip install ...; pip uninstall pytest-qt -y`，段末 `$?=0` 只能说明最后一个命令成功；主审用 `false; true` 的真实 shell 对照确认了这个边界。因此，§6.6(5) 保留“安装未验收”与来源分数分开是正确的，但还需覆盖**前面的必要构建失败、末尾命令成功**的情况，不能只排除非零 RC。

最小做法是保留来源配方的执行语义、记录段末 RC 的准确含义，针对已选配方检查必要构建是否完成以及实际导入/编译产物。`RH2_INSTALL_EFFECT` 作为诊断线索，不把候选 stdout 中的一行自报当作新的可信评分事实。未证明安装作用于候选的题不算接线验收通过，不自动改成 0、None 或新增排题规则；正式候选执行失败 producer 仍由第四组 A 决定。不建议为了本次接线另造通用 shell 命令解析器。

**R4 / P2：§6.6(4) 的路径相等验收会误判正常新增文件。**

主审在独立临时仓库中 `git apply` 新增 `new.py`：文件真实存在，但普通 `git diff HEAD --name-only` 为空，因为新增文件尚未进入 index。RH2 冻结包含这类未跟踪文件；此外，materialized 基线与任务 base 之间可能已有镜像内差异。`git diff <base>` 可以保留作日志，不能作为冻结投影完整性的验收 oracle。

将预期路径定义为**当前控制面规则下的 candidate entries**，并在 fixture 中检查重放后的内容、mode、增删及 symlink，而非只比“非测试路径”或 Git diff。复用已有 census/冻结/应用能力，不增加一轮全树生产校验。至少含一个普通新增文件、一个测试文件改动被忽略但正常修复保留的对照；第四组 B 尚未批准的 testing 辅助源码仍如实记录现状。

**R5 / P2：C1 中的 silent success 要改成准确的状态口径。**

对安装的 swebench 4.1.0 `get_eval_tests_report` 默认分支的实测，以及对 [pinned fork grading.py](https://raw.githubusercontent.com/SWE-Gym/SWE-Bench-Fork/242429c188fcfd06aad13fce9a54d450470bf0ac/swebench/harness/grading.py) 的核查均表明：参考 ID 缺席计失败；PASSED/XFAIL 计成功；SKIPPED 不进入这两类桶。两个参考项均 SKIPPED 的直接 report 函数结果可为 FULL。这与“日志没写就算成功”不同。

另外 RH2 manager 还有零解析 → infra 的既有规则；本片保留，不能通过“沿用官方”暗中取消。回归要分开检查 parser 的状态 map、标记/坏码处理和最终 verdict；只比较两函数输出不足以证明完整新入口等价。既有 441 份语料可复用，另用小样例覆盖缺席、SKIPPED、零解析，不额外扩出大测试平台。

**C3 的第四组边界应恢复完整表述。** 第四组 A 不只涉及“安装失败”，还包括可归因于候选的编译、导入和收集失败；B 不只涉及 testing helper，还涉及合法解答与测试配置、插件、构建配置等控制面的划分。它们各自阻塞对应行为的正式验收，不阻塞命令派生、来源 parser、shm、driver 或无关题的对账。未决问题不能被一份“接线全部通过”的总括结论掩盖。

其它低成本接线细节：

- gold 输入要写清。当前 prepared/private 产物不保存 validation bundle；正式 safe view 边界继续保留。可在受信准备步骤把指定 gold 导出为绑定 task 的普通候选补丁，再交 driver，或明列独立 validation 输入；仅给当前两个目录不能假装能读取 gold。
- shm 同时接入环境变量读取、`to_parameters()/digest()` 与实际容器 inspect；不能只加 `--shm-size` 而令记录仍显示旧 profile。
- 新 parser 绑定后，`grader_version` 不应仍只写 `swebench-4.1.0`；记录实际来源 revision 与所用 report 实现/配方版本，复用现有字段或诊断账本即可。
- 216 条来源命令逐字比对有明确的独立 oracle；整份渲染脚本则优先测阶段顺序、命令、用户和退出事实，避免只把实现文本抄成大快照。

### 8.4 推荐实施与复核顺序

1. S1-a 和 S1-f 先做，S1-b 可先准备 pinned 提取与语料；对已获授权的等价修复不重复设闸门。D1–D4 按本页修订后的真实含义落实批准。
2. 修订 S1-c/d，先跑 CPU 对照和一个 fixture 镜像闭环。集中核对结构分类、候选已释放仍可评分、安装多命令事实、正式 profile 与取消清理，不要求训练 GPU。
3. 机器可用后，先选 mypy/conan 及一个纯 Python 配方，再加 pandas 编译型代表；确认新用户权限、产物、耗时和账本可解释后，展开 §6.4 的矩阵。约 85 次、3 路并发、4–6 小时目前只是旧条件估计；首批据实际安装/初始化耗时调整，不宣称已验证。
4. 每片按共享文件归属提交与聚焦复核；第四组未决行为单列未验收，其余结果可先交付。SWE 接线通过与正式环境资格、真实 CC 基座诊断、GPU 训练通过分别报告。

### 8.5 本轮证据与停止条件

可复跑 [review_probe.py](swe_grading_wiring_20260915/review_probe.py)，结果为 [review_probe_result.json](swe_grading_wiring_20260915/review_probe_result.json)。从仓库根目录运行：

```bash
rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swe_grading_wiring_20260915/review_probe.py
```

| 对照 | 实际观察 | 能支持的结论 |
| --- | --- | --- |
| 真实分类器 vs 直接 builder，三个 symlink 目标 | 合法目标 projectable；逃逸及进入 `.git` 为 unsafe；直接 builder 三案都包含该路径 | driver 必须满足现有调用前置条件；没有测试尚未编写的 driver |
| swebench report 函数四案 | 缺席 NO；全部 SKIPPED FULL；全部 PASSED FULL；F2P FAILED 则 NO | 确认状态到 report 的语义，不代替完整 manager 或新 parser 的验收 |
| `set -o pipefail; false; true` | 最终 RC=0 | 复合安装段末 RC 不能证明每个必要步骤成功；没有真实运行安装 |
| 临时 Git 仓库应用新增文件补丁 | 新文件存在，Git diff 不含它，untracked 列表含它 | §6.6(4) 不能以普通 Git diff 作完整投影 oracle |

既有 pandas/moto 日志只用于查验历史行为，未重写历史 evidence，也未宣称新 RH2 路径已经复现这些结果。审查后的停止条件是：补清 §8.1、修正 §8.2–3 的事实与验收说明、落实实际权限/镜像范围，即可进入上述小切片；不追加通用防作弊系统、全树哈希闸门或 GPU 前置验收。

## 9. B 线独立复核 / Codex / 2026-09-15

**结论：§8 的 R1–R5 均有依据，没有应撤销的项；但不能把它们全部记成现有生产故障或新的安全工程。** 两名独立 reviewer 分别追踪调用链、尝试推翻结论，主审回读源码并复跑关键对照。基线仍为 `4529ebd7`；本轮只审计划、补证据，未实施接线。

### 9.1 A 线意见是否真实需要处理

| 意见 | B 线裁定 | 最小处理 |
| --- | --- | --- |
| R1 分类后投影 | 成立，`conditional_future`。当前正式 rollout 已先分类；拟议 driver 漏了。真实 manager 不补 symlink 目标分类。 | driver 调用已有分类器，不给 manager/builder 再加重复防线。 |
| R2 候选容器期限与清理 | 成立，`conditional_future`。manager 不拥有 driver 创建的容器，评分期限也不覆盖之前的物化。 | 明确唯一所有者、候选阶段预算、持久化后释放和异常清理；不用复制训练队列或 rollout barrier。 |
| R3 派生镜像身份 | 成立，仅选择 D4 派生镜像时触发。image ID 与 RepoDigest 不同。 | 复用已有本地镜像路径；可直接用实际 image ID 启动并记录，或发布取得 RepoDigest。不要求候选与 grader 同镜像。 |
| R4 投影验收 | 成立，是验收方法错误。普通 Git diff 漏未跟踪新增文件，且不等同于物化基线的差分。 | 用现有冻结 entries 与代表 fixture 核对实际重放，不新增全树核验。 |
| R5 silent success | 成立，是状态解释错误。缺席计失败，SKIPPED 不入成功/失败桶；不能按旧注释理解。 | 修正文案与小样例，不顺带改变 reward；零解析保护的适用前提另见 B2。 |

D1 的少量 pinned vendoring 合理。D2 的 pandas 证据只说明安装可能读取 Git 状态，**没有证明交换顺序改变分数**，不值得据此预先增加 manager 阶段。D3 整个 conda prefix 可写确属权限扩张，应如实决定范围；fresh 容器不消除本次影响，也不因此要求建设完整抗作弊系统。D4 保留诊断镜像与正式环境资格的区别即可。

### 9.2 还需补入 §6 的内容

**B1 / P1 · 测试选择器不只缺 mypy 特判（`production_reachable`）。** 主审通过真实 trusted-prep → 双视图读取 → spec 构造，对照全部 216 条命令：**43 条不同，而非只有 mypy 的 40 条**。另三题为 moto-4847、moto-7607、dvc-5336，当前分别把 `.txt`、`.json`、`.yml` 资源文件传给 pytest；根因在 `prepared_task_face.py:108,181`。S1-a 应同时复用来源 [get_test_directives 的文件筛选](https://raw.githubusercontent.com/SWE-Gym/SWE-Bench-Fork/242429c188fcfd06aad13fce9a54d450470bf0ac/swebench/harness/utils.py#L267)。**测试命令的选择列表与可信 setup 需恢复/保护的材料列表不能一起缩减**，这些资源文件仍可能是官方测试所需 fixture。原定 216 条命令契约足以覆盖，无需新增大测试矩阵。本轮未在真实镜像执行这三条错误命令。

**B2 / P1 · 明确新 parser 的日志边界（`conditional_future`，依赖函数行为已复现）。** S1-b 写“与 4.1.0 `get_logs_eval` 同语义”还不够：该函数在测试标记内解析为空时，会回退解析**整份日志**。主审真实函数对照中，标记内只有收集失败文字、标记外有两行 PASSED，最终得到 FULL；`num_parsed_tests` 已非零，manager 的零解析保护不会触发。这是合成反例，不是声称旧 24 题已发生该误判。推荐新入口只把实际测试段作为状态来源，段外输出留作诊断，并明确与旧 wrapper 的差异；不扩展成通用 stdout 防伪。另 [Gym fork 的日志包装](https://raw.githubusercontent.com/SWE-Gym/SWE-Bench-Fork/242429c188fcfd06aad13fce9a54d450470bf0ac/swebench/harness/grading.py#L29)使用 applied-patch 条件，旧 441 份语料适合检验来源 parser，不能不作区分地要求它们直接通过新 v2 标记入口。验收加“段内空、段外有测试样式输出”一例即可。

**B3 / P2 · 先明确旧候选如何重建及对照哪一组（历史 `production_observed`，新 driver 尚未实测）。** 账本是原候选 24 行与 `candidate_projected` 对照 24 行；前者为 **FULL 13 / NO 7 / PARTIAL 3 / UNPARSED 1**，后者为 **13 / 8 / 3 / 0**。§6.1 的 13/8/3/1 混用了两组。24 个现存原补丁的字节摘要均与原组一致，但 **7 题历史 `git apply --check` 失败、靠 `patch --fuzz=5` 才应用成功**（含 pydantic-8500、MONAI-6975）；S1-d 直接严格 apply 不能假定能重建同一候选。最小处理是在受信准备步骤保存原补丁、实际应用方式及所得候选工件，再走正式冻结/投影；不能静默改补丁、沿用旧身份或把准备失败记作模型 0 分。对账绑定候选版本和运行条件；原组、实验性去测试组、真实 RH2 投影三者分开。

**B4 / P2 · 账本字段需要实际数据出口（`production_reachable`；不是新 reward 决策）。** `manager.py:108–118` 的取消路径不交付部分 stdout，`:2374–2383` 只有正常返回才取到候选日志。主审复跑真实 manager/子进程捕获路径、Docker 使用替身：进程已输出安装 RC 和测试阶段标记后超时，reward 正确为 None、清理成功，但落盘日志丢失这两项、test 阶段耗时为空。因此只改 renderer、并承诺 manager 完全不动，尚未给出可行的异常诊断方案。S1-c/d 应明确正常测试 RC、逐 ID map、超时部分日志及资源事实从哪里取得；给真实路径补最小持久化/观测出口，涉及共享文件先登记归属。安装加入候选脚本后，现有 manager `test` 时长包含安装，账本要区分。内存读取当前也会把缺失折成 0（`:2409–2435`），不能再当实测零值。验收覆盖输出后超时且证据仍可查；未取得项标 unavailable，不改变失败归因规则。

**B5 / 代表题预检补充 · conda 可写与 wheel 缓存不等于非 root 安装可用（`conditional_future`）。** Pydantic 来源配方由 pipx 安装 PDM，运行依赖 `$HOME/.local/bin`（`swegym_constants_242429c1.py:1950–1960`）；正式 manager 切换为 `/home/rh2grader`（`:2380`）。MONAI 的旧权重验证也只覆盖 root 缓存。D3/D4 增加实际 UID/HOME/PATH 下的工具、缓存和离线安装检查，缺什么补什么；不能只凭 chown conda 或 `PIP_FIND_LINKS` 宣称完成。本轮未在真实镜像证明 PDM 必然不可用。`pre_install` 属来源镜像构建阶段，见 [固定版本实现](https://raw.githubusercontent.com/SWE-Gym/SWE-Bench-Fork/242429c188fcfd06aad13fce9a54d450470bf0ac/swebench/harness/test_spec.py#L110)，不应为补工具而在每次评分中重跑整套 apt/联网构建。

另两处直接改说明即可：九仓库的 parser 调用实际先在 4.1.0 **spec 注册表**抛 KeyError，尚未到 parser map；拟议 v2 入口绕开旧 spec 构造即可，不再补一套注册表。prepared/private 不含 gold，§8 所提独立候选输入方案已足够。§6.1“离线安装失败会被记成候选失败”尚无当前生产证据，应改为“安装是否生效未验收”。

### 9.3 建议收口与验证范围

保留 §8.4 的分片顺序：先完成命令/来源 parser 与 R2E 结果说明；driver 和观测接缝明确后跑一个 fixture，再做少量真实仓库。B1/B2 随对应接线修正，B3 在重放旧候选前解决，B4 随 driver 完成，B5 纳入代表题预检。无需等全部 216 题通过、第四组全部决定或 GPU 训练；这些补充也不批准新的 reward、权限或正式镜像规则。

主审独立复跑 A 的四类对照、真实 manager 的分类前置条件对照，以及本节两份探针：[日志边界与旧候选核对](swe_grading_wiring_20260915/b_review_probe.py) / [结果](swe_grading_wiring_20260915/b_review_probe_result.json)；[216 题真实 prepared 接线与超时输出](swe_grading_wiring_20260915/b_prepared_timeout_probe.py) / [结果](swe_grading_wiring_20260915/b_prepared_timeout_result.json)。从仓库根用 `rh2/.venv/bin/python <探针路径>` 复跑；详细临时产物位于 `runs/swe_grading_wiring_b_review_20260915/`。**未运行真实 Docker、SSH、模型 API、GPU 或新评分批次；未修改生产源码、既有测试或历史 evidence。**

## 10. A 线 Claude 终审 / 2026-09-15

**结论：§8 R1–R5 与 §9 B1–B5 没有一项应撤销，但只有 B1 是当前代码里已存在、接线一开始就会踩到的缺陷；其余是新 driver 的设计前置、验收口径措辞或 D 决定的条件项。不必在 D1–D4 决定前修生产代码。** 逐项核对方式：读实际入口源码并复跑 §8.5 / §9.3 的 CPU 探针结果；未运行 Docker / 机器 / 评分。

### 10.1 逐项裁定

| 项 | 是否真实可达 | 现在要做什么 |
| --- | --- | --- |
| A-R1 分类后再投影 | 成立，但只对拟议 driver：`build_trusted_scoring_projection` 的 docstring 明写前置条件是 `classify_frozen_patch` 已判 projectable；生产 rollout（generate.py 3441→3512）先分类再投影。 | S1-d 设计项：driver 调 `classify_frozen_patch`，unsafe 保存证据不评分。不改 builder / manager。 |
| A-R2 候选容器期限与清理 | 成立，driver 设计项：`grade(deadline_monotonic)` 只约束 manager 内部（N2a），manager 不拥有 driver 自建的候选容器。 | S1-d 写清唯一 owner、候选阶段预算、导出后释放、finally 有界清理（可直接借用 grading manager 的 D-2 收口套路，不复制 rollout barrier）。 |
| A-R3 派生镜像身份 | 成立，仅 D4 分支：manager 校验 RepoDigests，`image_local_build=True` 是唯一豁免，二者在 `GradingEnvSpec` 已互斥。 | D4 选 A 时 driver 用 `image_local_build=True` 并记录实际 image ID；账本区分原环境包身份与实际 grader 镜像。 |
| A-R4 Git diff 不是投影 oracle | 成立（措辞 / 验收方法）。 | §6.6(4) 改为按控制面规则的 candidate entries 与重放后内容核对。 |
| A-R5 silent success 口径 | 成立（措辞）：缺席计失败、SKIPPED 不进两桶、manager 零解析仍是 infra。 | 改 C1 文案与小样例；不改 reward。 |
| B-B1 43 条测试命令不同 | **成立且当前可达**：`build_grading_spec_from_host_view` 用 `patch_touched_paths(test_patch)` 当测试文件，资源文件（.txt/.json/.yml）也被传给 pytest；mypy 40 + moto 2 + dvc 1。 | S1-a 必修：测试选择复用来源 `get_test_directives` 的筛选；可信 setup 恢复 / 保护的文件清单**不**随之缩减。216 行契约足够。 |
| B-B2 新 parser 的日志边界 | 成立，条件项：4.1.0 `get_logs_eval` 在标记段为空时回退整份日志（B 探针 `passed_only_outside_test_markers` → FULL）。当前 SWE-Gym 在 spec 注册表就 KeyError，新入口才会遇到。 | S1-b 设计项：v2 入口只以标记段为状态来源，段外留诊断；验收加"段内空、段外有 PASSED"一例。 |
| B-B3 旧候选重建 | 成立（历史证据）：7 题原补丁需 `patch --fuzz=5` 才能应用；两组 oracle（13/7/3/1 与 13/8/3/0）不能混用。 | S1-d/e 前：受信准备步骤保存原补丁、实际应用方式与所得候选工件；对账绑定候选版本。 |
| B-B4 超时丢部分日志 | **成立且当前可达**：`run_docker` 被取消时 kill 子进程不返回已捕获 stdout；`_run_eval` 只在正常返回取日志。B 探针：候选已输出安装 RC 与测试标记后超时 → 持久化日志不含二者、`test` 段耗时为空。另 `container_peak_memory_mb` 是契约必填 float（ge=0），缺失只能折成 0。 | 不阻塞 S1-a/b/f。要让账本在超时案例可查，需要 manager 侧最小改动（超时时也持久化已捕获输出 / 单独 install 段计时），这是 A 线共享文件，先在 §7 登记顺序再做；内存峰值"未取得"要改契约才能表达，先在账本注明 0 = 未取得或为零。 |
| B-B5 非 root 资产预检 | 成立，条件项：manager 以 `HOME=/home/rh2grader` 执行候选段（manager.py 2380），pydantic 配方依赖 pipx 装在 `$HOME/.local/bin` 的 PDM。 | D3/D4 决定后在机器上按实际 UID/HOME/PATH 预检；不在每次评分重跑 `pre_install`。 |

### 10.2 两份审查都没有写透、需要用户在 D3 时看到的一点

D3 方案 A（`chown -R 54322 /opt/miniconda3/envs/testbed`）不只是"权限扩张"：候选代码在测试阶段以 54322 运行，今天改不了 root 属主的 site-packages，因此**改不了 pytest 及其插件**；prefix 交给 54322 后，候选可以在安装段替换或 monkeypatch 测试运行器，official 测试文件保护（root:root 0644）挡不住"运行器本身被换掉"这条路。这不是要建反作弊平台，而是 D3 的真实代价：接受"候选能安装依赖"就等于接受"候选能影响测试运行器"。可选缓解只有两种，都各有代价：只交出 site-packages 子目录（console scripts / 编译型仍可能失败，A 线 §8.2 已指出不要预先承诺）；或不做 D3、验收项 5 对编译型题不成立。建议 D3 按这个代价决定，并把"运行器完整性不在 F2 保护范围"写进本片非目标。

### 10.3 遗漏项补充（都小，随对应切片处理）

1. **安装进入候选段后的计时与期限**：安装时间会计入 manager 的 `test` 分段与 `test_timeout_seconds`（1800s），也计入 N2a 评分期限（默认 3600s = 排队 + 镜像 + 准备 + 测试余量）。今天测试超时归 infra（reward=None，无 `test_execution_timeout` producer，与 FA-2A 一致），所以没有 reward 风险；但 pandas 类 700s 编译会明显压缩测试预算，S1-e 要记录实际耗时，第四组 A 若以后加候选超时 producer，必须把安装段排除在归因窗口外。账本 `phases.install` 需要 manager 增加分段（同 B4 登记）。
2. **gold 触碰 test_glob 路径会被投影丢弃**（第四组 B 未决）：9 个代表题的 gold 补丁先用现有 `HygieneRules` / `classify_frozen_patch` 静态分类一遍，把会被忽略的路径列出来，再解释组 A "gold 应 resolved" 的例外；这是零 Docker 的预检，比事后解释便宜。
3. **shm 旋钮改变 profile digest**：`runtime_profile_digest` 随 `GraderSandboxProfile` 参数变化，账本与对账要注明前后 digest 不同不是异常。
4. **driver 里的补丁应用用户**：候选补丁写入应以候选用户（rollout 里是 `agent`）执行，不用 root，保持与生产一致的文件属主，否则投影 / 权限布置的对照失真。
5. **重评分与容器标签**：driver 直连 manager 会走 N2b 的一次追加评分（transport 暂态），账本记 `regrade_total`；设置 `MILES_RH2_RUN_ID` 让 grader 容器带 run 标签，机器上的残留清扫脚本才找得到。

### 10.4 可以先开工的部分（不等 D1–D4）

S1-a（含 B1 的选择器修正）、S1-f、parser 回归语料整理、§10.3 第 2 条的 gold 静态分类预检。S1-b 等 D1，S1-c 等 D2/D3（含 §10.2 的代价说明），S1-d 的 driver 设计按 A-R1/R2 与 B-B3/B4 修订后再写，S1-e 等机器与 D4。本节是审查意见，不代替用户对 D1–D4 的批准。

## 11. B 线实施复核 / Codex / 2026-09-15

**结论：接线主体成立，但还不能认定“本地工作全部验收”。先修 I1–I3 再跑 e1；I4–I7 在扩大 e2 前补齐。** D1–D4 已批准，不重开；以下是实现修正建议，尚未修改生产代码、提交或运行远端评分。审查基线 `acb0e4bf` 加当前 18 个 RH2 改动/新增文件，文件摘要及反例结果见[证据汇总](swe_grading_wiring_20260915/implementation_review_evidence.json)。

### 11.1 e1 前修正

**I1 / P1：观测脚本以 root 加载候选代码（`production_reachable`）。** 实际绑定是 `build_grading_spec_from_host_view` → 前/后观测脚本 → `manager._observe` → `_exec_bash`；[manager.py:2513](../../../../rh2/src/repoharness2/grading/manager.py#L2513) 没传候选 `user/home`。[renderer:225–279](../../../../rh2/src/repoharness2/adapters/slime/prepared_task_face.py#L225) 激活已交给候选写入的 conda 环境、进入 `/testbed`、启动 Python；后观测还直接 import 候选包。这会执行包初始化/环境启动代码，已经越过“候选代码以 54322 执行”的边界；D3 接受运行器可变，不等于接受候选代码以 root 执行。

最小修法：主动 Python/import 观测使用候选 UID/HOME，root 只读取不执行候选代码的静态事实；不要把 import 输出升级为可信安装证明。若暂不实现，可先删除主动观测、明确记为未测，保留 e1 其它验证。观测调用每次可达，触发副作用的频率未知；缩小执行权限即可，不需要新的反作弊平台或审批规则。本项依据静态调用链，未实测受保护文件被改写。

**I2 / P1：候选容器清理失败仍继续（`production_reachable`，CPU 故障注入复现）。** replay_grade.py:354–417（对应生产源码未随本批发布：`rh2/src/repoharness2/adapters/slime/replay_grade.py`） 只把 `rm` 失败写成 `removed=false`，之后继续评分；manager 不拥有这些候选容器。主审重跑正式 grader profile 的替身路径：连续两次均产生 resolved，两个候选都未移除，而 `manager.close()` 的 `containers_open=[]`。daemon 故障频率未知，但扩大批次时会累积资源残留。

最小修法是保存证据并停止本批；如不能确认容器已终止，不继续新尝试，无需新增恢复服务或重试状态机。顺便把现有“先 remove、后持久化”（417 → 428 行）改回批准的持久化后释放。只影响异常收口，正常 reward 不变。

**I3 / P1：新机器照运行手册安装不出所需环境（`production_reachable`）。** [runbook:20–22](swe_grading_wiring_20260915/runbook_s1e.md#L20) 使用 `pip install -e '…[swe]'`，但 `swe/dev` 在 `[dependency-groups]`，并非 extras；本机包元数据也没有 `Provides-Extra`。因此这条命令不会引入指定 SWE 组，也未安装后面调用的 pytest；“与本机同 pin”同样不成立。改成消费锁文件的依赖组安装并显式带上所需测试工具。同步清单还缺 `B_materials_20260908/official_cmd_contract_216.json` 与 `s2/swegym_parser_dumps/`，后面的两个测试文件会实际读取它们。

同次修正文档即可：派生镜像页的 `--image-local-build` 不存在于 CLI（`--derived-image` 已隐含该行为）；首次拉镜像实际可能发生在候选 `docker run`，消耗 candidate 预算，应先预拉或明确预算；证据回传补上 `artifacts/`。不需另建环境部署系统。

### 11.2 扩大 e2 前补齐诊断

以下都是现有入口可达的 P2；修正证据出口，不改变 reward、来源判定或失败归因。

| 项 | 具体事实与最小修正 |
| --- | --- |
| **I4 总评分期限仍丢候选日志** | [manager.py:2528–2530](../../../../rh2/src/repoharness2/grading/manager.py#L2528) 在期限耗尽后直接返回空串。主审真实 Docker 对照：分段超时保留安装标记；总期限耗尽时容器 tee 文件确有相同标记，评分日志却丢失，随后容器移除。用独立且有界的收口预算保存已产生的日志，不延长安装/测试期限；同时覆盖外部取消路径。 |
| **I5 零解析时丢掉最需要的 parser 诊断** | parser 已算出段外 18 项、参考缺席 18 项，但 manager 判零解析 infra 后在 [1489 行](../../../../rh2/src/repoharness2/grading/manager.py#L1489) 调 `_diagnostics(None)`，sidecar 的 `verdict=null`。主审 v2 绑定 → 真实 manager、Docker 替身复现；reward=None 正确。保留已计算的 verdict 供诊断即可。 |
| **I6 取消的 attempt 没有账本行** | replay_grade.py:449–468（对应生产源码未随本批发布：`rh2/src/repoharness2/adapters/slime/replay_grade.py`） 的 `CancelledError` 绕过落账。主审取消探针中清理成功，但账本为 0 行；无法区分没启动与执行中取消。最小修法是记取消阶段和现有证据引用，再原样上抛，不吞取消、不重新评分。 |
| **I7 测试退出码尚无出口** | [renderer:148–150](../../../../rh2/src/repoharness2/adapters/slime/prepared_task_face.py#L148) 在测试命令后直接打印 End/时间戳，未保存测试 RC；外层 `PIPESTATUS[0]` 是整个脚本的最终 RC。driver 的 `test` 字段始终为 null。测试命令之后立即保存 RC、送入诊断即可；不把非零 RC 新增为评分闸门。 |

### 11.3 已确认的部分与验证范围

- 主审相关套件 **169 passed / 1 skipped**；新增 Docker 用例 **4 passed**。另做分段/总期限两次真实容器对照，均清理成功。独立来源核对：216 条命令零差异，18 份入库及 441 份本地语料对保存 oracle、固定版本源函数均零差异。这支持命令/parser 接线，不代表 216 题真实评分已通过。
- driver 放 adapter 层合理，真实调用了 census/export/classify/投影/manager；但现有成功路径单测的 manager 未传 `sandbox_profile`，没验证 CLI 使用的正式组合。修正时补正式 profile 的组合覆盖；x86 真实镜像仍留 e1。独立反证确认 `SandboxProfileViolation`、`GradingScopeTerminationError` 属于 `BaselineIntegrityError`，会记账上抛，**不接受“这两类被通用 except 吞掉”的怀疑**。
- R2E 决策包先修事实再讨论：SWE 不是“全部 PASSED 的精确映射特例”（现有 XFAIL 成功、SKIPPED 不入桶）；A 方案也改契约，C 只是暂缓接入，不代表永久放弃训练用途。新增字段能否保持旧序列化逐字节不变，需要具体迁移实现保证。本片无需据此决定 R2E 新契约。
- 派生镜像 tag 在检查与启动间重指，属于有条件的剩余风险；未证明正常运行中发生，不作为当前阻塞。pydantic-8977 控制字符 ID 不匹配已存在于来源/阶段一证据，不算本批新增 parser bug。`.dirty` 也不能单独证明扩展已重新编译，e1 的安装生效判断仍要对照实际产物。

处理状态：I1–I7 为 `accepted`（审查确认并建议修正，**不代表已修复**），由本批实现者修改后按对应反例复核；不扩大到 GPU、全量筛题或新 reward 决策。原始探针/日志在 `runs/swe_grading_wiring_impl_review_20260915/`（git 忽略），以上 JSON 保留可共享的结果和代码快照。权限反例子任务被自动安全检查拦截，未执行受保护文件改写；I1 只按源码可达结论报告，不冒充 Docker 攻击复现。

## 12. A 线 Claude 对 §11 的复核 / 2026-09-15

**结论：§11 I1–I7 全部真实可达、没有应撤销的项；严重度排序同意"I1–I3 先修再跑 e1"。另补三项 §11 没有覆盖的缺口（A1–A3），其中 A1 会让新检出的 216 契约测试在任何干净 checkout 里直接报错，应与代码一起处理。** 方法：逐项读实际源码与工作区 diff（不依赖 §11 的行号），复跑非 Docker 全量与 Docker 用例（见 §12.3）；未租机器、未跑真实镜像评分。

### 12.1 对 I1–I7 的裁定

| 项 | 核对结果 | 是否需要现在修 |
| --- | --- | --- |
| I1 root 观测执行候选代码 | 成立。`manager._observe` 用 `_exec_bash(record, script)`，没有 `user/home`；后观测脚本先 `conda activate testbed`（D3=A 后该前缀已交给候选）再 `python -c "import <pkg>"`，即在候选跑完之后以 root 导入候选包。前观测在候选段之前，风险主要在后观测。容器有 cap-drop / no-new-privileges / deny_all，爆炸半径有限，但确实越过 D2-3 的"候选代码非 root"边界，且是生产路径（`build_grading_spec_from_host_view` 绑定，actor 与 driver 共用）。 | 是，e1 前。最小修法：主动 import / 运行器摘要以候选 UID/HOME 执行；root 只做不执行候选代码的静态读取（属主、文件摘要可以由 root 算，但 `find_spec` 要在候选身份下跑或改成按已知路径遍历）。 |
| I2 候选容器 rm 失败仍继续 | 成立。`_remove_container` 只记 `removed=false`，`replay_one` 随后照常评分；候选容器不在 manager 记账里。 | 是，e1 前。rm 失败或超时 → 记证据后结束本批（或至少不再开新尝试）；可直接借用 manager `_close_container_scope` 的 rm→inspect→kill→rm 套路，不新建状态机。"先 remove 后持久化"是小问题：artifact 已在内存，只在进程崩溃窗口丢，随手改顺序即可。 |
| I3 runbook 安装命令 | 成立。`rh2/pyproject.toml` 的 `swe` / `dev` 在 `[dependency-groups]`（PEP 735），不是 extras；`pip install -e 'rh2[swe]'` 不会装 swebench 与 pytest。派生镜像页写的 `--image-local-build` 在 CLI 里不存在（`--derived-image` 已隐含）。 | 是，文档级；用 `uv sync --group swe --group dev` 或锁文件导出安装，并把 `official_cmd_contract_216.json`、`s2/swegym_parser_dumps/` 加入同步清单（见 A1）。 |
| I4 总期限耗尽丢部分日志 | 成立。`_read_candidate_log_partial` 在 `grading_deadline_left() <= 0` 时直接返回空串，而总期限耗尽正是最需要它的场景；分段超时的路径正常。 | 是，e2 前。读回改用独立有界的收口预算（与 D-2 清理预算同源），不延长工作期限。 |
| I5 零解析丢 parser 诊断 | 成立。零解析 → `GradingInfraError` 后 except 分支用 `_diagnostics(None)`，v2 parser 已算出的段外行数 / 参考缺席等诊断字段被丢。 | 是，e2 前。在抛 infra 前把 verdict 传入 diagnostics。 |
| I6 取消无账本行 | 成立。`replay_one` 只捕获 `TimeoutError` / `ReplayStageError`，`CancelledError` 经 `finally` 清理后直接上抛，没有 `_append`。 | 是，e2 前。记录取消阶段与已有证据引用后原样上抛。 |
| I7 测试退出码无出口 | 成立。`_v2_candidate_test_lines` 在测试命令后直接打 End 标记与时间戳，没有 `RH2_TEST_RC=$?`；exec 退出码是整脚本最后一条命令的。 | 是，e2 前。测试命令后立即保存 RC 进日志事实；只进诊断，不作闸门。 |

### 12.2 §11 没有覆盖的三项

**A1 / P1（测试基础设施）：新增 216 契约测试读取一个未跟踪的文档文件。** `tests/envpack/test_vendor_specs.py` 的 `CONTRACT_216` 指向 `project1_execution/B_materials_20260908/official_cmd_contract_216.json`；该文件目前不在 git 里（`git ls-files` 为 0），fixture 直接 `read_text`，没有缺失即 skip。代码一提交，任何干净 checkout / lanes / 机器都会在这个测试报错。同类还有 `s2/swegym_parser_dumps/`（未跟踪）与语料环境变量路径（已 skip，正确）。处理：把契约 JSON 与入库语料一并提交，或改成缺失即 skip 并在 runbook 明确同步；建议前者，它就是验收 oracle。

**A2 / P2：安装段仍共用 `test_timeout_seconds` 与 `test` 阶段标签。** 候选段 exec 仍是 `phase="test"`、`timeout=spec.test_timeout_seconds`（1800s）。安装耗时（pandas 类 700s 级）直接压缩测试预算；安装期间超时会记成 `grading_test_timeout_after_1800s`，归因文字误导（今天仍是 infra、reward=None，无 reward 风险）。§10.3 第 1 条已说明，实现只把 install/test 秒数放进 sidecar。e1 至少要按 sidecar 时间核对 1800s 是否够；标签改成 `candidate_segment` 或按 `RH2_PHASE` 标记拆分归因。以后第四组 A 若加候选超时 producer，安装段必须排除。

**A3 / P3（小加固）：root 读回候选 tee 文件时跟随符号链接。** `_read_candidate_log_partial` 以 root `cat /rh2/candidate/eval.log`；目录与文件都是候选属主，候选可以把它换成指向容器内任意 root 可读文件的符号链接，内容会进入落盘的 eval 日志。容器里目前没有凭据，且该路径只在超时（reward=None）时使用，不影响判定；读取前加 `[ ! -L ]` 判断即可，顺手做。

### 12.3 我的验证与不确定项

- 非 Docker 全量（双 lane，含 B 的全部工作区改动）：**2307 passed / 1 skipped**（skip = 未设语料环境变量的 441 份语料例；单独设 `RH2_SWEGYM_PARSER_CORPUS` 后 `test_swegym_parsers.py` + `test_vendor_specs.py` 27 passed，441 份语料与 216 条命令契约在本机独立复跑通过）。
- Docker 用例（本机 Docker 29.4.1）：`test_w3b_grader_profile_docker.py` + `test_manager_docker.py` **30 passed（35.7s）**，与 B 自报一致；这只证明 fixture 镜像上的安装段身份、可写前缀、shm 与超时读回，不是 x86 真实 SWE 镜像。
- 未做：机器、真实镜像、e1；I1 只按源码可达判断，没有构造 root 提权演示。

其它核对为真、无需再议：`parse_eval_log_v2` 只服务 SWE-Gym vendor（其它 vendor 抛 ValueError → manager 包成 `test_log_parse_failed` infra，不会静默）；vendored parser 源文件 sha256 与 provenance 由测试钉死；候选补丁以 `agent` 用户应用、候选容器带 run 标签、rollout profile 参数（含 `--init`）沿用；`regrade_total` 已进账本（是 manager 累计值，不是本行增量，读账本时注意）。§11 说 driver 单测未覆盖正式 profile 组合，属实（四处 `GradingManagerConfig(eval_log_dir=…)` 都没传 `sandbox_profile`），补一例即可。

处理归属：I1–I7 与 A1–A3 均由本批实现者（B 线 Claude）修改；涉及 `grading/manager.py` 的 I1/I4/I5 已在 S1-m 归属登记内。本节是审查意见，不改变 D1–D4 决定，也不代替 e1 的真实镜像验证。

## 13. B 线修复复核 / Codex / 2026-09-15

**多数原项已核销，但“机器是唯一前置”还不成立。建议 e1 前补 R1 候选收口与 R2 运行手册；R3/R4 在扩大 e2 前处理。** 不新增 T0，不重开 R2E 已选 A 的决定。本轮只写审查记录与[复跑证据](swe_grading_wiring_20260915/fix_review_evidence.json)，未改生产代码、提交或租机。

### 13.1 e1 前的两项局部修正

**R1 / P1：候选收口仍有两个直接可达的中断点。** driver 的 finally（对应生产源码未随本批发布：`rh2/src/repoharness2/adapters/slime/replay_grade.py`）先持久化，再 await 移除容器，两步之间没有异常隔离。① 持久化抛 `OSError` 就跳过移除；主审用实际 CLI/driver、FakeDocker 运输层，将工件目录设为普通文件，复现 `NotADirectoryError`、候选已创建、零次 rm、零行账本，CLI 最后的 manager.close 也不掌管该候选。运行中磁盘满/写入失败走同一路径；仅加启动目录预检不能解决。② 第一次取消恰好落在清理 await 内，同样中断移除且不落账；事件屏障反例只发了一次取消，不依赖重复取消。

最小修正：持久化失败仍进入有界清理，随后保留原错误停止本批；清理期间首次取消也应等这个已有清理预算收口，记录结果后传播取消。无需增加新的恢复服务。正常 rm 失败时停止本批的 I2 修正已通过：CLI 返回 2、只创建一个候选、不开始评分、有一行失败账本，且 rm 前工件已落盘。

**R2 / P2：运行手册仍不能完整搬到新机器。** 两处都属于安装/同步说明修正：

- 同步清单漏 `docs/agentic_RL/repo_harness_rh2_workstreams/s2/raw/swe_gym_lite_full_f70b1a29.jsonl`，`test_vendor_specs.py` 的既有 fixture 仍读取它。主审按清单搭隔离目录运行指定两份测试，得到 **23 passed / 1 skipped / 3 errors**；只补这一个约 3.5 MB 文件后变为 **26 passed / 1 skipped**。A1 的契约与语料迁移本身已通过，不需要搬回旧位置。
- `pip --group` 已修正 extras 错误，但不消费 `uv.lock` 或 `[tool.uv.sources]`。现命令仍按范围安装 `swebench`，`verifiers` 的 Git pin 也不会由 pip 自动采用，不能保证与已测环境相同。建议在 `rh2/` 使用 `uv sync --locked --group swe --group dev`，或安装锁文件导出的依赖；主审离线 frozen export 已确认可导出 `swebench==4.1.0` 与 `verifiers@5885ab9c54152e707af2a11797aa52c3eb1752da`。本轮没有新建环境执行 pip 安装，结论是手册缺少版本保证，不是已观测到新版本故障。

### 13.2 e2 前余项与已核销内容

| 项目 | 复核结果与处理建议 |
| --- | --- |
| **R3 / P2：取消后的评分日志仍未落盘** | manager 在候选执行取消时读回 tee，但随后直接传播 `CancelledError`，没有经过持久化分支；若取消发生在后观测，刚完成的完整测试日志也丢失。两条主审反例均为零日志文件、无诊断引用；driver 有取消账本，容器也正常移除。应先保存已有日志/sidecar并让账本能引用，再传播取消，不构造 reward。**总评分期限耗尽丢日志已修复**，不要与此混为一项。 |
| **R4 / P2：镜像预算未包住 inspect** | `_ensure_image` 与派生镜像检查的 `image inspect` 没有期限；配置 0.02 秒镜像预算的反例在 0.10 秒后仍停在 inspect，尚未创建候选。镜像拉取期间取消也无账本。将 inspect/pull 一起纳入已有镜像预算，记录取消阶段即可；无需另建调度机制。 |
| I1 / I5 / I7 | 两次观测确实使用候选 UID/HOME；零解析保留 parser 诊断；测试 RC 立即捕获并入诊断。均已核销。观测仍只作线索，不是可信安装证明。 |
| I2 / I6 | 正常清理失败停止、候选执行期间取消和评分期间取消落账均已通过；R1 是遗漏的 finally 边界，R3 是账本以外的日志持久化。 |
| A1 / A2 / A3 | 新位置语料/契约可独立使用；install/test 超时归因后缀有效，共用 1800 秒仍待 e1 校准；读回有普通文件/非符号链接检查，按本次 P3 范围核销，不声称它具备并发替换下的原子保证。 |

**主审验证：** 相关测试 **134 passed / 1 skipped**；两份 Docker 套件 **30 passed**；441 份语料单独复跑通过。另独立重跑 7 个 driver 反例、观测/取消反例与上述同步目录对照。真实本机 Docker 的分段超时、总期限超时两条反例均保留已产生的安装/测试标记，并完成容器移除。子审还在函数内存副本中验证了嵌套 finally 能在写盘报错后执行清理；这是建议修法的对照，未写入生产源码。

边界：本机 Docker 是 ARM fixture；FakeDocker 反例证明 Python 调用/生命周期，不证明 x86 镜像性能或环境适配。S1-e 真实镜像端到端仍待远端 CPU Docker。建议 B 线实现者先补 R1/R2，再进入 e1；R3/R4 登记为 e2 前余项。此处是复核建议，不是新增用户授权要求；e1 不需要完整 GPU 训练卡组。

## 14. B 线本地复核收口 / Codex / 2026-09-15

**通过进入 e1 的本地复核，可以租 x86 CPU Docker 机器执行四题 gold/noop。** §13 的 e1 阻塞已核销；本轮不要求继续修代码后才能租机。三项余项见下，不把本结论扩展成真实 x86 环境、e2 或训练链验收。D1–D4、R2E 选 A 不变，无新增 T0。

### 14.1 四项修复的核销证据

| 原项 | 主审复核 |
| --- | --- |
| R1 写盘失败与清理取消 | 用同一工件目录故障复跑真实 CLI：返回 2、只建一个候选、已移除、不评分、有失败账本。用 Event 固定首次取消发生于清理 await：等待清理完成、落 `cancelled:cleanup`、传播取消。正常清理失败仍停止本批。新的 cleanup task 只活到本次收口，没有增加长期 owner。 |
| R2 同步与依赖 | 按新版清单搭隔离目录：**26 passed / 1 skipped**；四题 `prepare` 与 `export-gold` 均退出 0，得到四份补丁。`uv sync --locked --group swe --group dev --dry-run --offline` 在本机和 Linux x86_64 目标解析均通过；重导出的有效依赖行与 `requirements-replay.lock` 相同，只有命令注释多 `--offline`。这证明清单与锁解析，不是已在新 Linux 环境安装成功。 |
| R3 取消日志 | 候选执行中取消保留部分日志，后观测中取消保留完整日志；日志、sidecar 均真实存在，引用摘要匹配。driver 取消账本能引用它们；取消继续传播、容器被移除、不构造 reward。 |
| R4 镜像预算 | 普通 inspect 在 0.02 秒预算下约 0.021 秒返回超时、零候选；拉取中取消落一行账本。独立子审另验证 inspect/pull 共预算及派生 Id inspect 超时。派生检查取消遗漏见下。 |

本轮主审相关测试 **140 passed / 1 skipped**、Docker 两套 **30 passed**、改动文件 ruff 通过。跳过项为未指定全量 441 语料目录；parser 相对上一轮没有修改，本轮不重复声称该扩展语料已跑。两个独立子审分别追踪生命周期与尝试推翻结论；关键反例均由主审复跑。[证据摘要与源码版本](swe_grading_wiring_20260915/fix2_review_evidence.json)保留具体结果；原始探针位于 `runs/swe_grading_wiring_fix2_review_20260915/`（忽略提交）。

### 14.2 三项余项，不阻塞 e1

| 余项 / 可达性 | 影响、最小处理与验收 |
| --- | --- |
| **P2：完整日志留在内存记录中**；`production_reachable`，`grading/manager.py:2530` | 新增赋值在正常评分后仍被 `_records` 引用，gc/close 不清全文。主审三次约 64 KiB 日志对照：当前每条保留 65,920 字符；只在函数内存副本移除新增赋值后各 189 字符，落盘和 reward 不变。不是 RSS/OOM 实测，但长批会随累计输出增加内存。**B 线在扩大长批/训练前处理**：完成日志/sidecar 持久化后释放全文缓存，保留取消期间的暂存和落盘引用；验收正常累计留存不再随全文增长，两条取消证据仍完整。e1 每个 CLI 进程只跑四题，进程退出会释放，故不升为租机前阻塞。 |
| **P2：派生 Id inspect 取消缺账本**；`production_reachable`，`adapters/slime/replay_grade.py:418` | 此 inspect 在 row 建立前，只捕获超时；主审 Event 反例取消传播、零账本、零容器、未评分。**B 线在 e2 的 D4 派生分支前补齐**：沿用已有 row/append，取消时恰好一行且仍传播，不增加恢复/重试。e1 不走此分支。两次镜像检查各有预算，总前置耗时可超过一份预算；目前都有限期，仅记录此口径。 |
| **P3：完整日志被标成 partial**；`production_reachable`，`adapters/slime/replay_grade.py:582` | 后观测取消时，账本 `log.partial=True` 被硬编码，但 sidecar 与 `install.log_partial=False` 正确、完整文件也在。主审已复现。**B 线在汇总取消诊断前顺手修正**：读已有候选事实，不硬编码；无需重跑环境矩阵。 |

停止条件已满足：原阻塞反例闭合，当前入口、取消传播、清理与搬运清单已验证，下一份关键证据应来自 e1 真实镜像。日志留存是这次修复直接引入的容量问题，登记局部处理即可，不回退取消日志能力或新建缓存管理器。本轮没有修改生产代码、提交、租机或执行远端任务。

## 15. e1 真机独立复核 / Codex / 2026-09-16

**e1 经补测可以收口。** [短复核报告](swe_grading_wiring_20260915/e1_codex_review_20260916.md)与[证据摘要](swe_grading_wiring_20260915/e1_codex_review_evidence_20260916.json)：补齐 pandas noop（F2P 0/16，与 gold 16/16 对照、逐参考状态符合 oracle）和 §6.6.10 人为超时（安装/测试标记保留、partial、reward=None、清理完成）。主审 82 项相关测试通过/1 跳过，S1 正式 integration CPU 探针 5 项通过。

新发现当前 metacopy/native-diff 组合在 `chown → docker commit` 后把文件内容变成全 0，完整写回对照正常；已撤回 runbook 的通用开关要求。此路径不在普通 e1 评分中，不推翻结果；D4 前需验证具体构建路径。S1 旧 unsafe/整组 DROP 已获授权，不重开，但 P-D 的合法 file→dir 支持仍未完成。另更正 pandas ID“一一映射”、mypy 安装证明与内存口径。生产代码未改，原始证据未改写；未启动 P-B/e2、未提交，机器保持运行且无残留容器。下一步按已审范围推进 P-B，再同步当前源码跑 e2；§14.2 余项按原分期处理。


## 16. e2 与第四组夜间实现独立审查 / Codex A 线 / 2026-09-16

统一报告：[第四组实施审查](batch4_scoring_20260910/implementation_review_20260916/README.md)。e2 78 行、回归 25 行、92 份评分日志及诊断引用已独立核对；15 个可比候选全部与投影 oracle 一致，新旧代码 21 行对照无分数/计数变化。Linux 三个新增容器往返、本机 1392 项相关测试通过（1 跳过），机器最终无运行容器、metacopy=Y。

**这些结果不构成“剩余接线和第四组全部完成”。** P-A 有三项必须修正的归因缺陷；正常完成但参考 ID 全变化的 None 处置需对齐范围；formal 资格入口和构建归因尚未完成，P-C/P-D 有两个窄余项。§14.2 的全文内存留存、派生 inspect 取消无账本、完整日志 partial 标记三项仍在当前源码，沿原分期处理。stdout/hook 伪造由用户另定策略；仅改 XML 通道不足以根治。具体实现建议、证据与后续复核停止条件均以统一报告为准，不重开已收口 e1 或已批准 D1–D4。
