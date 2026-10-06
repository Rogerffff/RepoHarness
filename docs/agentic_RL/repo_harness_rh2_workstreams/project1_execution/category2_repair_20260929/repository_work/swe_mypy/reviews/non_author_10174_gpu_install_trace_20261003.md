# 10174 GPU 安装缺陷：Production Tracer 独立追踪

日期：2026-10-03。角色：按 `review-standards.md` §10.4 追踪当前生产调用链、身份与异常传播。状态：**r16 完整原件独立核对后收口；GPU 供应修复与后续派发不在本报告验收范围内**。初次追踪之后，仅本次增量加入窄重评分与其编排失败记录；原 GPU 证据和旧成绩保持原样。

本报告没有修改 runner、材料、旧请求、旧结果或既有审查；没有执行 SSH、容器、模型或完整测试。检查限于本轮原件、GPU 冻结源码、R6 发布归档、本包旧 CPU 安装证据和 owner 提供的新窄重评分原件。以下“已证”指可由现存原件或本次本地只读重算证明；“静态推断”没有替代真机执行证据。

## 1. 当前结论与剩余边界

**已证：本轮 editable 安装真实失败，错误是读取供应 wheel 时的 `Permission denied`。该失败被记录到 diagnostics，测试仍执行，官方 parser 解析四个引用全部通过，原报告得到 reward 1.0。** 因而不能把这份原报告描述为“安装与评分全链验证完成”；也不能仅凭安装失败断言候选实际未被测试或 reward 一定错误。

**新窄复验已证：r16 在 CPU `9d63…` 可读 wheel 镜像上，保留原 FP、完整 baseline 和50条投影，以正式 manager 评分；前置三条原安装命令各自 rc0，正式原脚本安装无失败、四个相同引用全通过，reward 仍为1.0。** 完整1472条基线再次重建一致，候选 UID 的三个独立 Python probes 读取原候选 `meet/build/checkexpr` 的正确路径、loader 和 SHA，清理1建1移且无遗留。证据足以支持“同一候选在恢复安装的该 CPU 环境下仍得到同分”，本轮安装异常没有在这次窄复验中表现为分数变化。

原 GPU 原件没有关键模块在 pytest 进程内的实际 SHA。r16 的 probes 同样是测试前后的独立 Python 进程；且 owner 在正式脚本前额外执行了三条安装命令，形成安装预热。它验证“原候选可以正常安装并通过原评分”，不证明旧 GPU 进程实际导入字节、不证明无预热的单次原脚本环境完全等价，也不证明新 GPU 镜像已修复或派发。上述范围足以收口本轮窄问题，无需扩大模型重跑或整链审查。

## 2. 证据入口与版本

以下路径均从仓库根目录起算，避免把本机路径或凭据写进报告。

| 别名 | 路径与用途 |
| --- | --- |
| `G` | `runs/ordinary_gpu_probe_20261002/remote/queue_v12/results/gpu1003-mypy10174-qwen36-a1/`：本轮原 FP、baseline、projection、diagnostics、eval.log、report。 |
| `C` | `runs/ordinary_gpu_probe_20261002/frozen_code_v4/`：本次 GPU 冻结运行树。 |
| `R6` | `runs/category2_repair_20260929/host_setup_20261003/cat2-cpu-r2e080087-swe8-git-20261003-v1.tgz`：CPU R6 发布归档；源码成员前缀 `./repo/`。 |
| `B` | `runs/ordinary_gpu_probe_20261002/tools/build_swe_four_v1.py`：本次 GPU 四题准备 builder。 |
| `P` | `runs/ordinary_gpu_probe_20261002/remote/prepared_swe_four_v1/mypy10174/`：GPU source/build/image readback。 |
| `CPU` | `runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy10174-revised-r3-20261002T182535Z-f641d8/attempt/`：R6 noop/gold/bad 正式 CPU 矩阵原件。 |
| `N` | `runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/`：本轮窄重评分的逐 job 原件及 `.evidence.tgz`。 |
| `R16` | `N/mypy10174-gpu-original-regrade-r16-20261003T003832Z-5650b3/`：最终正式窄重评分原件；`attempt/` 为 grader 记录，`slot/`、`launch/` 为实际 admission/结束回执。 |
| `V` | `runs/category2_repair_20260929/repository_work/swe_mypy/gpu_install_revalidation_20261003/`：binding、上传校验及 r13 误通知更正记录。 |
| `W` | `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_mypy/gpu_original_regrade.py`：owner 窄验 worker；本次只读审查。 |

本次请求固定 `execution_snapshot=code_v4`；`G/attempt/attempt.json` 的入口 SHA 与本地 `C/rh2/experiments/ordinary_gpu_probe_20261002/entry.py` 重算一致：`a1efff44dc2cbedfc81d93b2da8d84a92f6c9c88b15c2a10bf96db2026a4e82c`。本次直接评分使用该入口，旧 CPU 使用 `rh2/scripts/replay_grade.py` CLI；二者都进入真实 `SWEGradingManager`。

本地直接读取 R6 tar 成员，与 GPU code_v4 文件比较字节 SHA；以下消费者相同：

| 相同文件（相对发布 repo 根） | 两侧共同 SHA256 |
| --- | --- |
| `rh2/src/repoharness2/grading/manager.py` | `b6b10f98bf0e1a7bbe4774ac705ece6bb2746da2b1ac4f20394673293f24bbb0` |
| `rh2/scripts/replay_grade.py` | `d36fa3367415e573305a7a03619f51e7cbd358627569f3844d5c203b70d66db3` |
| `rh2/src/repoharness2/adapters/slime/replay_grade.py` | `3bd574eed3da9372b8640eac48d5da0b1141375c21b6e492de822d494443ef66` |
| `rh2/src/repoharness2/adapters/slime/sandbox_profile.py` | `313bfd7691c5dca775aa0e9992f13561e20936f062ddfa3d269892b6bf4895ee` |
| `rh2/scripts/build_swe_revisions.py` | `d0206dab4a5396e8690954808fe190447ed1c07ff0588c675ead50a7fa1a34df` |

`spec_vendor.py`、`prepared_task_face.py`、`material_revision.py` 并非整文件相同。本次逐项 diff 看到的增量是其它题的 Pyd/DVC 固定安装分支和 Moto6114 context；本题使用的 `_v2_install_lines` 运行语句及 `SWEGradingRevisionContext` 没有变化。结论是**本题的目标消费逻辑可对照 R6，不是整棵 GPU 树等于 R6**。上述差异核对限于本轮安装/评分问题，没有扩展为 code_v4 全量审查。

## 3. 本次候选身份与基线：已证

| 身份项 | 本轮值 |
| --- | --- |
| task / execution / physical attempt | `swe_gym_lite::python__mypy-10174` / `gpu1003-mypy10174-qwen36-a1` / `gpu1003-mypy10174-qwen36-a1#p1` |
| materialized HEAD / base | `c8bae06919674b9846e3ff864b0a44592db888eb` |
| 原 FP runtime image | `sha256:32f313c82fd4f065517b8fd1faff22b79a8c1c8e108200c85c8de8188191baad` |
| canonical FP digest | `sha256:5772af211384a9828c83dd61c60c96a6447475e34c4b2bfb891f584ac4304664` |
| canonical baseline digest | `sha256:337be5fc6ed9a5013249a17bcfb9e48cf7dce2aa3ca27cb4b8b9fd9f0efb7172` |
| public bundle | `sha256:e1cc57aeabbf0261482d0d06da3c08509d54f12c32fc06b4cc6e8eedf8b9e41c` |
| grading bundle | `sha256:b24e783218afdcf37c4717cf2702ad195e999e120683483269ac94de10802255` |
| grading materials identity | `sha256:dca86b80c83f2e2e9c4eee8c4375952adef834008ad4cb7006ac60abeca58065` |
| revision / registry | `mypy10174-strict-equality-v1` / `sha256:a49edd0750cd45c880344bdda762bd757d8bdfddd09689c69cf2e46e316e3cf6` |

本次本地只读重算结果：

- 按 contracts 的 canonical JSON 规则重算 FP 和 baseline digest，与原 report/projection 绑定相同；51 个 FP entry 的 base64 内容 SHA 全部匹配。
- `G/attempt/frozen/baseline.tar` 有 1472 个普通文件；逐个读取并检查内容 SHA 与执行位规范化后的 mode，全部对应完整 manifest。这里 mode 是 census 的 `100644/100755` 语义，不是原 tar 的每一位 UNIX 权限。
- 独立解析 `G/grading/baseline_rebuild_census.txt` 得到 1472 条 entries，与原 manifest 完全相等；排除区路径集 digest 也相等。`result.json` 同时记录 `baseline_rebuild_passed=true`。这不是仅凭包装器布尔值采信。
- 原 baseline 记录 `/testbed/test-requirements.txt` 是镜像预置的 dirty tracked 文件；它在 1472 条完整核对中，不能只重建 Git base 后省略它。原工件的 baseline archive 标记 `captured_before_solver=true`。

FP 的 51 条变化是：49 条 `.mypy_cache/` 新增、`mypy/meet.py` 修改、`test-data/unit/check-expressions.test` 修改。实际评分 projection 有 50 条，含全部49条 cache与 `mypy/meet.py`，不含模型修改的测试文件。`.mypy_cache` 不在本轮 policy v2 的可再生目录名单内；名单只含 `__pycache__` 和 `.pytest_cache`。不得在声称“同一候选”的复验中额外清理这49条投影内容。

候选 `mypy/meet.py` 内容 SHA 为 `sha256:fda3ae751b225a484400198ff560bbaab9ec56d0dc5f54e3b2846a85c103a0a7`。与归档基线 `sha256:8df49240a0aeea302ed7f07fdbdab35a6e6ff1ef2614bcd5db6ded89721a38f2` 对照，唯一源码增量是在非 strict optional 的 Union 去除 None 后，再判断 `AnyType` 并返回 `True`，附两行解释注释。该身份来自原 FP 内容，不以供人审阅的 `candidate/*.diff` 代替。

## 4. 真实调用链、owner 与异常传播

### GPU 本次入口

`serial_dispatch(code_v4)` → `entry.execute` 求解/冻结 → `entry.grade_original` → `source_from_original` 从原 FP+完整 baseline 构造 `FrozenDeltaSource` → `SWEGradingManager.grade(workspace=None, frozen_delta=source)`。

`C/rh2/experiments/ordinary_gpu_probe_20261002/entry.py:224–241` 验证 attempt 身份、公开材料绑定、可投影性并重建可信 projection；`:244–289` 调真实 manager，观察但不替换其 baseline 重建检查，保存 census。该入口不把 review diff 当评分输入。只有 cleanup 与 baseline rebuild 成功后，包装器才正常返回。

### R6 CPU CLI 接缝

题包 `revised_matrix.py:49–60` → R6 `rh2/scripts/replay_grade.py prepare/run` → `ReplayGradeRunner`（重放预置 noop/gold/bad，先生成该次 baseline/FP/projection）→ 同一个 `SWEGradingManager.grade(workspace=None, frozen_delta=source)`。这解释旧 CPU 为什么能验证真实 grader，却不能被当成本轮 GPU 候选的重新执行记录。

### manager 内部顺序

1. `manager.py:2967–3085` 重算并对账 FP、baseline、projection digest、task/HEAD/材料血缘和投影路径集。FP↔baseline 的 runtime image 必须相等；source↔spec 的评分镜像故意不要求相等（`:3073–3076`），树等价随后由 census 证明。
2. `:2013–2039` 起 fresh grading 容器、核镜像、clean checkout、`_verify_baseline_rebuild`，再按允许的可再生目录规则规范化并应用投影。`:3088–3171` 在 fresh checkout 重建完整 manifest；digest 不同是 `BaselineIntegrityError`，不是模型负样本。
3. `:3198–3281` 将 FP 原字节逐路径写入；每次写入前验证内容 SHA；apply 失败为 `GradingInfraError`。
4. `:3388–3437` root 可信 setup 恢复评分测试、应用登记 test patch、核自证，再保护控制面；不达标立即 typed infra。本次 `RH2_SETUP_OK=1`、`RH2_PROTECT_OK=1`，受保护文件1个、祖先目录3个、缺失0个。原日志 `:242–287` 也显示成功恢复/应用评分文件。
5. `sandbox_profile.py:1634–1710` 把 `/testbed` 和候选安装前缀交 UID 54322；评分测试文件改回 root:root 0644，祖先目录 sticky 1777。该脚本没有把 `/opt/rh2/build-wheels` 交给候选或核其可读性。`manager.py:3450–3464,3500–3502,3562–3565` 中观测与候选代码都以候选 UID 执行，root 不导入候选包。
6. 本次 `supply=null`，走一份候选脚本的安装→测试路径。`prepared_task_face.py:189–223` 的 ERR trap 仅记录失败命令；`RH2_INSTALL_RC` 只保留安装串最后命令退出码，随后照常进入测试。不是 shell 的整体 fail-fast。
7. `manager.py:2059–2108` 先用官方 parser 得到 verdict，再按引用桶生成 reward。`execution_failure_trigger(:1427–1450)` 只在零解析或参考全部缺席时进入执行失败归因。本次4条引用都有状态，该钩子不触发，故 diagnostics 的 `execution_failure_decision=null` 与源码一致；`install_failed_commands` 没有单独挡下分数。

本次 manager 记录 `containers_created_total=1`、`containers_removed_total=1`、`leases_total=1`，close 后 open containers/supply/cleanup failures 均空。安装、测试、后观测按上述顺序执行；现存证据没有显示同一 grader 内有并发安装或多个候选竞争。这个 owner/生命周期结论仅限本次评分容器，不扩展到 GPU 服务或训练并发拓扑。

## 5. 安装错误本身：事实与静态因果

`G/grading/eval_logs/evallog_gpu1003-mypy10174-qwen36_193cc9fb.eval.log:426–461` 显示测试依赖已满足；`:462–486` 进入 `python -m pip install -e .` 的隔离构建依赖安装，处理 `setuptools-75.1.0-py3-none-any.whl` 时失败：

```text
ERROR: Could not install packages due to an OSError: [Errno 13] Permission denied: '/opt/rh2/build-wheels/setuptools-75.1.0-py3-none-any.whl'
RH2_INSTALL_CMD_FAILED=1 python -m pip install -e .
```

后续 `pip install pytest pytest-xdist` 已满足，末尾 `hash -r` 返回0，故 `:489–510` 的安装段末码为0。`:517–539` 显示测试执行，4 selected/4 passed，test rc 0。diagnostics 明确记录前面的 rc1、`candidate_segment_completed=true`、`log_partial=false`。失败没有被日志抽取遗漏，但也没有自动成为 infra。

**已证原因层级**：候选 UID 在本轮 pip 隔离构建中不能读取上述供应 wheel；错误发生在重新安装 mypy 本体之前。不能归因为候选 `meet.py` 的语法/运行错误、网络下载失败或缺少 wheel。

**静态推断**：`B:38` 设置 umask077，`:102–106` 生成 wheel 后显式 chmod0600。Dockerfile（`runs/ordinary_gpu_probe_20261002/prepared_swe_four_v1_payload/mypy10174/build_context/Dockerfile:1–4`）仅 `COPY wheels/ /opt/rh2/build-wheels/`，没有设置候选可读权限。`P/build.json` 确认此次镜像经过该 COPY 并得到 `32f313…`；`P/image_readback.json` 和 FP/runtime identity 对应同一镜像。该静态链足以解释原始 EACCES，且与保护脚本未触及供应目录一致。

**仍未由原件证明**：镜像内该 wheel 的实际 UID/GID/mode、每级目录权限，以及复制层权限与 EACCES 的逐项对应。不能把已准备的后续权限修法写成“本轮已经修好”。

## 6. 测试导入和 reward 适用范围

原 diagnostics 中 `RH2_OBS_IMPORT_PATH=/testbed/mypy/__init__.py`，runner 摘要前后相同；本轮 baseline 的 `mypy/` 没有 `.so/.pyd` 文件。原归档 `mypy/test/testcheck.py:10–23` 导入 `mypy.build` 等工作包，`:204–206` 直接调用 `build.build`。同文件 `:184–191` 的非 incremental 分支禁用增量、通常将 cache_dir 指向 `os.devnull`；本次四个引用是普通 case。由 `mypy/test/config.py:7–11`，测试数据根从测试模块的真实路径推导，指向相同工作树下 `test-data/unit`。

这些证据支持：即使 editable install 失败，已存在的测试入口仍可能直接读取投影后的 Python 源码；`.mypy_cache` 的存在本身不足以证明本次四个单元 case 被缓存冒充。该判断是源码路径的静态推断和原顶层 import 观测的组合，**不是旧 GPU 关键模块运行时 SHA 证据**。r16 已在新 CPU 窄验中补充 `mypy.meet`、`mypy.build`、`mypy.checkexpr` 的路径和源 SHA（见§8），但没有追溯补写旧 GPU 导入观测。

原报告可以保留为：“在这份环境及此次安装异常下，原材料四个评分引用被执行并解析为通过，reward 1.0。”它不能单独证明：供应与安装正常、GPU镜像已修复、同条件多次稳定、公开actor环境资格、完整mypy回归通过或正式训练准入。

## 7. 旧 CPU 安装证据及可复用范围

`CPU/noop/gold/bad` 的三份正式 eval.log 都显示隔离构建依赖安装完成、`Successfully installed mypy-0.820+dev.…dirty`；三份 diagnostics 的 `install_failed_commands=[]`，安装段末码均0。实际镜像为 `sha256:9d63f1ddcbd277fa62d49e10d800908cfec54544e890fc5fe741d2101ca8eb7e`。材料身份、revision、四个引用与本轮 GPU 相同，noop/gold/bad 的 test rc 为1/0/1，原矩阵 reward 为0/1/0。

该旧证据说明同材料及真实 manager 在已有 CPU 派生镜像上能够正常安装与区分控制候选，也支持将其用作最小复验的已知合格环境。它不证明 GPU `32f313…` 的 wheel 可读，旧CPU gold也不是本轮GPU模型候选。

## 8. r16 原候选正式窄重评分：已证与适用范围

`R16/slot/status.json` 记录实际 slot0、开始 `2026-10-03T00:38:39Z`、结束 `00:40:40Z`、returncode0；`launch/receipt.json` 的 wrapper_rc0。worker 绑定上传文件 SHA 为 `2dd00b90921ff0ff13e97237db2816ef5dc8d93d5ccdb7b2532a3fc063cb9a67`，本地 `W` 重算相同；`V/binding_v2.json` 重算为 `6bbcb0ea7d151a92e19a86f6294d25a4e6d9c30e40b4efa620cf60d4b19147cd`，与 state 内 binding 对象相同。

本次独立读取完整归档并重算 SHA `e99e28b328b77da775c1271e270a6fb1633fd4a2fea2cb298e52086af506fb19`；其中27个原始文件与解包目录内容逐字节相同。以下核对基于原文件，没有将 state 的 `raw_regrade_completed_pending_audit` 标签当作审查通过证据。

### 身份与材料没有换候选

- `W:49–50,87–101,213–214` 在评分前后检查原输入字节 SHA、canonical FP/baseline digest、原 execution/runtime/public 血缘以及完整 projection 对象。实际镜像只在 `spec` 改为 CPU `9d63…`（`:84–86`）；FP↔baseline 的 runtime 均保留原 GPU `32f313…`。这是 manager 既有跨评分镜像规则配合全树 census，不是把原 FP runtime 重绑到 CPU。
- 本次独立重算5个原输入文件 SHA和 FP/baseline canonical digest；独立解析 r16 census 得到1472条 entries，与原完整 baseline 每条 type/mode/SHA 一致，排除摘要也相同。r16 census 字节 SHA 与原 GPU census 相同。projection 对象及文件字节 SHA 与原件相同，包含全部49条 `.mypy_cache` 和 `meet.py`，没有清理投影 cache。
- r3 的严格 manifest 字节断言失败后，v2 仅允许 fresh `prepared_at_utc` 变化。r16 原 manifest 字节 SHA 为 `54ddb36d…`，fresh 为 `9712a5c400a73c731a02d6fd8c314f90212706a6ed0231404c92bb7819309831`，时间分别为 `2026-10-02T18:25:52.104300Z` 和 `2026-10-03T00:38:47.786292Z`。本次独立比较证明唯一差异是该字段；两个 public 成员和 private 文件 SHA 均相同。worker 保留两份真实 SHA 和时间、用 fresh SHA 加载，没有回填旧时间或放宽其它材料字段。
- diagnostics 的材料 identity、revision、registry、scripts digest `f111e77…`、test command 以及原四个引用均与旧 GPU 相同。正式 setup 恢复1个评分文件、apply rc0、setup/protect各为1；runner 摘要前后均 `2f4655b6933a219bb88c823bdc724ed84e84c89a2a23b39c1f399cb1da2b61c4`，`runner_integrity_changed=false`。

### 安装、导入与正式评分

`W:154–170` 在 manager 的 `pre_candidate_observation` 中，以候选 UID54322 先运行 probe，再额外逐条执行三条原安装命令，保存真实退出码，最后运行 after-install probe；正式 manager 随后运行未改的原候选脚本，包含原安装配方和测试。此接缝对环境进行了额外安装，不能称作纯只读观测。

| 证据 | 原件与结果 |
| --- | --- |
| 三条前置原安装命令 | `R16/attempt/install_step_1/2/3.json`：依次安装 test requirements、editable mypy、pytest/xdist，逐条 exit_code0；第2条日志显示隔离构建依赖和 editable wheel 完成、卸载旧 mypy 后成功安装。 |
| 正式原脚本 | `attempt/eval_logs/evallog_mypy10174-gpu-original-r_218c88d8.eval.log:425–512` 再次执行原安装，成功构建/安装 mypy；diagnostics `install_failed_commands=[]`、candidate exit0、install末码0、completed=true、partial=false。不是仅凭末码采信安装成功。 |
| 正式原引用 | 同一日志`:519–541` 显示4 passed、9419 deselected、test rc0。独立对照三个 partition，1条原F2P、1条新增P2P、2条原P2P全部 success；missing/skipped/unaccounted/failure均空，parsed4、outside0。diagnostics verdict为`RESOLVED_FULL`，report为resolved、reward1.0，F2P1/1、P2P0失败/3。 |
| 导入观测 | `candidate_before_install.json`、`candidate_after_install.json`、`candidate_after_formal_tests.json` 及各自 `.exec.json`：独立Python进程exit0，UID/GID54322、cwd `/testbed`、testbed解释器，模块都为 `/testbed/mypy/*.py`、`SourceFileLoader`；三个记录完全相同。 |
| 安装元数据 | 三次probe都读到解释器purelib下真实 `mypy-…dirty.dist-info/direct_url.json`，内容为 `file:///testbed`、`editable=true`，同时保存direct_url和METADATA字节SHA；不是cwd源码egg-info。但元数据安装前已存在且前后三次完全相同，不能说该观测证明它在本次首次创建。pip的实际build/install日志另行证明两轮安装成功。 |
| 可读wheel | 三次probe均以候选UID实际读入3个wheel并计算SHA；packaging24.1、setuptools75.1、wheel0.44为root:root0644，SHA精确对应绑定的原3个wheel。该mode证据只属于CPU `9d63…`，不反填旧GPU mode。 |
| 清理 | `regrade_state.json.manager_close`：1建1移、lease1，containers_open/supply_open/cleanup_failures为空；`cleanup_ok=true`，wrapper和slot都正常结束。 |

模块字节身份独立对照原 FP/原 baseline：

| 模块 | 本次三次观测共同 SHA256 | 身份来源 |
| --- | --- | --- |
| `mypy.meet` | `fda3ae751b225a484400198ff560bbaab9ec56d0dc5f54e3b2846a85c103a0a7` | 原FP候选源码；`is_overlapping_types.__code__.co_filename=/testbed/mypy/meet.py`。 |
| `mypy.build` | `24b5aa12e8f65e38f386af201f7cb4aaa4844e9dcbdd409048b6dea6dd938f4e` | 原完整baseline。 |
| `mypy.checkexpr` | `7489e688d1168dfde2c522a0cc70ccaf52c744f3f80940f081e2dd2217b76321` | 原完整baseline。 |

**范围限制**：这些模块观测没有嵌入 pytest 进程，不能改写为“逐测试进程实测 SHA”。前置安装加正式安装也不是 fresh 容器仅运行一次原脚本的实验；CPU镜像在此前还已有editable安装元数据。因此结论限于同一候选在该可读供应环境下能够按原配方成功安装、并由原正式评分得同分。`resource_facts=null`、`RH2_OBS_PKG_VERSION="?"` 和 `env_qualification=absent` 按事实保留，不能用dist-info文件名替换原ledger字段或补作环境资格。本轮不要求为这些边界新增复测。

### owner 编排失败和误通知，保留但不计为题目结果

| job（均在 `N` 下） | 实际停止点与归类 |
| --- | --- |
| `mypy10174-gpu-original-regrade-r3-20261002T235343Z-c0d3fd` | 实际slot0、wrapper/slot rc1；v1 在prepare后比较新旧manifest字节SHA的断言失败，尚未创建manager/评分容器。新旧manifest独立比较仅时间戳不同。没有正式report/eval.log；state遗留`running`不代表仍运行。属于owner身份比较逻辑失败。 |
| `mypy10174-gpu-original-regrade-r8-20261003T000817Z-cca2a8` | 实际slot1、rc1；1472条完整baseline通过、前置3 install各rc0，随后owner after-install probe对默认`distribution(...).direct_url=null`执行`json.loads(None)`而TypeError。原probe未保存distribution实际路径，cwd egg-info解释不能当路径实测。未进入正式脚本/tests；1建1移、清理空。属于owner观测解码失败。 |
| `mypy10174-gpu-original-regrade-r15-20261003T003159Z-762691` | 实际slot0、rc1；1472条完整baseline通过，before-install probe枚举stdlib/backport metadata finder时，旧`importlib_metadata`将`Context`传入`re.escape`，报`TypeError: decoding to str: need a bytes-like object, Context found`。前置install列表为空、未执行正式tests；1建1移、清理空。属于owner观测兼容失败。 |
| `mypy10174-gpu-original-regrade-r13-20261003T002448Z-557786` | 实际wrapper75、无slot。`V/incorrect_admission_notice_and_correction.json` 保存误发送admission及立即更正的投递记录，承认本地assert失败后编排未检查返回码而继续发送文本。实际receipt为75，不计admission或评分；没有可支持错误评分结论的回执。 |

v4 `W:108–125` 仅把 metadata finder 观测改为 `sysconfig.get_paths()['purelib']` 中 `mypy-*.dist-info/direct_url.json` 与METADATA的真实文件census/SHA；不调用distribution finder、不改变候选sys.path。after-install仍要求真实site-packages dist-info中存在指向`file:///testbed`的editable元数据。其余原FP/完整baseline/50投影、材料和scripts、模块loader/SHA、候选UID、wheel、binding_v2约束保留。早期默认元数据的null与TypeError原件未改写；v4也没有为原ledger补包版本。

## 9. 必核结果与停止条件

| 必核项 | 判据与当前状态 |
| --- | --- |
| 原候选身份 | 原FP canonical digest、完整baseline digest、原runtime字段、50条投影与全部cache保留。**r16已核对。** |
| 真实消费点 | 正式manager消费原FP；fresh census逐条对应1472条原baseline及排除摘要。**r16已核对。** |
| 安装补证 | 前置3条原命令分别rc0；正式脚本editable成功、失败命令为空；actual CPU image和3个wheel的0644/SHA明确。**r16已核对，有前置安装预热范围。** |
| 测试源码身份 | 候选UID独立Python probes的meet/build/checkexpr路径、loader和SHA符合原候选；控制面与runner正常。**r16已核对，未在pytest进程内观测，也未补写旧GPU。** |
| 原引用完整性 | 相同revision/material/test command、4/4原引用通过，无missing/skipped/outside；新reward1.0与旧reward相同。**r16已核对，旧结果未覆盖。** |
| GPU权限修正与派发 | 新GPU镜像供应可读、正式grader安装成功、新镜像和后续attempt应单独登记。**本轮未验证，仍由GPU现场回执负责。** |

停止条件已满足：在上述明确环境和观测边界内，原候选正常安装后仍得相同分数，本轮窄追踪收口。r3/r8/r15的编排失败和r13误通知更正保持独立，不能作为模型负样本或题目失败；未入slot的其它请求不计为评分。GPU供应修复与下一次实际派发需要GPU自己的证据，不从CPU窄验推定完成；不扩大为整链总审计，也不要求重复已通过的R6完整CPU矩阵。

### 原始字节封存校验

以下为文件字节 SHA256，与上面的 canonical object digest 是不同口径。

| `G` 下文件 | 字节 SHA256 |
| --- | --- |
| `attempt/frozen/frozen_patch.json` | `d72699b958fc0f688d5e6c4d4fd5e93006bd18c4a4ea86a2f76c998a4bbeae07` |
| `attempt/frozen/baseline_manifest.json` | `5fab6a0f7932073ac2f47d0c69e950c8e0e64949c4d043da4227918395b2a958` |
| `attempt/frozen/baseline.tar` | `714753b01aff10c04468da922f8e9e6bccb3e02223de96209cd9f532d7688437` |
| `grading/projection.json` | `8d61762ccbf5de9a0a3667d7e1cac48cd81d686b0246298843118d4133f8c77d` |
| `grading/baseline_rebuild_census.txt` | `67c508e55dd3aa024a3e1f1c9c2f5e5e09b370ea02757740724344978a19bcf7` |
| `grading/eval_logs/evallog_gpu1003-mypy10174-qwen36_193cc9fb.diagnostics.json` | `c63669cc3591000d77a6b84ffb7cd2af2e4849d2987765eeae4bc46edd5d475e` |
| `grading/eval_logs/evallog_gpu1003-mypy10174-qwen36_193cc9fb.eval.log` | `8e82fe4d557593d50e5027bd52f010ca2f2f512573216d0add13948ebbee9748` |

新增 r16 原件字节SHA：

| 文件 | 字节 SHA256 |
| --- | --- |
| `N/mypy10174-gpu-original-regrade-r16-20261003T003832Z-5650b3.evidence.tgz` | `e99e28b328b77da775c1271e270a6fb1633fd4a2fea2cb298e52086af506fb19` |
| `R16/attempt/regrade_state.json` | `2d5d775b16764cbcc3436a41753077a4864ff62d80e11488f14dd2eecc3a8bf2` |
| `R16/attempt/report.json` | `4a88bcec9c5bdf8f69cd9d059eff8944c29e111488cc68dffc77dcf49d6c5c7e` |
| 三份 `R16/attempt/candidate_*.json`（不含 `.exec.json`） | 三份相同：`170595489eac00c09f3c089744f9da83f83c8f45b33f624373131bb7b742f7c5`。 |
| `R16/attempt/projection.json` | 同原 projection：`8d61762ccbf5de9a0a3667d7e1cac48cd81d686b0246298843118d4133f8c77d`。 |
| `R16/attempt/baseline_rebuild_census.txt` | 同原 census：`67c508e55dd3aa024a3e1f1c9c2f5e5e09b370ea02757740724344978a19bcf7`。 |
| `R16/attempt/eval_logs/evallog_mypy10174-gpu-original-r_218c88d8.eval.log` | `6361be301a3e3d50c92e42024b64c654b363c31e9a35c2eb9f9fa2be670a8d29` |
