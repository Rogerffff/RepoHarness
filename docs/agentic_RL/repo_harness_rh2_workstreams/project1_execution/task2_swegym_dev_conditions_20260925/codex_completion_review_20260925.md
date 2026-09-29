# 任务二完成复核 / Codex / 2026-09-25

**结论：接受这轮逐题开发验证的主要结果；探针脚本尚需小范围修正，不能把“任务二完成”理解为下一轮模型批次已完整验收。无需重跑全部 21 题。**

复核范围：作者的计划、结果、实际脚本与本地原始证据；独立 Tracer / Falsifier 检查运行接缝，根任务复现关键反例并裁定。本轮没有租机器、运行题目容器或模型，也没有修改被审代码。下列运行错误标为 `production_reachable`：调用的是将用于探针的真实函数，故障由本地替身注入；**不是声称昨晚实际发生了这些错误，也不指正式 miles 训练已受污染。**

## 1. 已核实什么

- **21 题、7 个仓库**的最终条件共 **96 条开发命令**均有结果，无缺失或命令超时。预检和激活通过，实际身份为 UID 54321，CC 2.1.205，工具集合为 Bash/Edit/NotebookEdit/Read/Write，实际镜像与记录一致，容器配置为 2 CPU / 4 GiB。
- 六个最终 actor 派生镜像确实被消费；逐题输出支持 pytest、boto3/botocore、pygit2、pathspec/networkx、Conan CLI/CMake 的修订效果。Pandas56849 的 actor 日志实际包含 Cython→C→链接，耗时 19 秒，不只是成功 import 的推断。
- 逐题读了相关测试摘要和目标失败：例如 Dask 118 pass、DVC6954 params 24 pass、DVC4166 ignore 29 pass；Conan 的 **2 fail**仍明确保留，未因脚本外层 rc=0 当作全绿。
- 21 份私有 gold 对照均存在，apply 记录为成功；Pandas53958 的公开 API 测试在 gold 下失败也保留了。最终条件的清理记录均无残留。
- `diag_sigterm` 已记录 Bash 工具启动、任务取消和无残留清理，故作者结果页 R6 的“还没专门验证”应更新。

逐题原表仍见 [results.md](results.md)。数据对账见 [evidence_reconciliation.json](../../../../../runs/task2_swegym_dev_20260925/codex_review_20260925/evidence_reconciliation.json)，被审脚本摘要见 [source_hashes.json](../../../../../runs/task2_swegym_dev_20260925/codex_review_20260925/source_hashes.json)。这些是本地证据，不是新增训练准入规则。

## 2. 下一模型批前应修的两项

### F1 · P1：导出失败被送去做 noop 评分

`solve_attempt.py:471–482` 导出命令失败时记录 `export_exit_code!=0 / bytes=0 / empty=false`，但此前的 `result=ran` 保留，`run:365–366` 仍返回 solve 的结果。`run_matrix.py:164–166` 用“没有 bytes”判断空补丁，连导出失败或候选记录缺失都转换成 `--candidate noop`。

**根复现：**真实导出函数收到受控 rc=1 后，无补丁文件，却被真实 `Matrix.grade` 传成 noop；独立 reviewer 另用 rc=124 得到同样结果，并对照了合法空补丁。没有真的执行 grader；已证明的是**错误候选类型被交给评分器**。在 noop 本应得 0 的题上，这会把导出故障算成模型没解出，污染能力统计。

**推荐 / accepted：**成功导出且确认为空才允许 noop；导出失败或工件缺失保留 infra 事实、不给模型分数。producer 和调度入口都消费这个状态，不增加重试或补采。不要笼统拒绝所有 CC 非零退出——预算结束但成功导出有效候选，是另一种情况。

证据：[根复现](../../../../../runs/task2_swegym_dev_20260925/codex_review_20260925/root_reproduction/export_failure/result.json)、[独立正常空补丁对照](../../../../../runs/task2_swegym_dev_20260925/codex_review_20260925/falsifier/export_failure/result.json)。

### F2 · P1：清理失败没有阻止继续派发

`solve_attempt.py:492–511,605–614` 记录残留或清理异常，但保留原结果/退出码；`run_matrix.py:110,135–146` 又只依赖 `ran` 和完成时间，不消费清理结果，子进程返回 4 也能继续评分和派下一题。

同族的 task2 runner 问题：`devcheck.py:176–190,239–243` 强删网络失败后仅再次检查容器；Docker 查询自身失败也会被空 stdout 表示为“无残留”。`run_batch.sh` 只识别 rc=4，因而可能继续。

**根复现：**清理记录有容器/网络残留时 `_amain` 返回 0；Matrix 在受控 rc=4 下执行了 `solve→grade→solve→grade`。本批真实清理记录无该现象；未来频率未知，但继续累积容器会干扰资源条件和后续实验。

**推荐 / accepted：**确认清理失败或无法确认时停止新的派发，保存已有候选和现场；恢复入口也检查这一状态。无需新建恢复状态机。网络/容器查询失败保留“未知”，不能等价于零残留。

证据：[根生命周期复现](../../../../../runs/task2_swegym_dev_20260925/codex_review_20260925/root_reproduction/check_lifecycle/lifecycle_result.json)、[网络与查询失败对照](../../../../../runs/task2_swegym_dev_20260925/codex_review_20260925/root_reproduction/check_seams/result.json)。

## 3. 两项有界修正

| 项 | 已确认的条件与后果 | 建议 |
| --- | --- | --- |
| **F3 · P2：SSE 终局按子串判断** | `model_gateway.py:221–227` 搜整个响应是否包含 `message_stop`。正文有这个词、实际终止事件缺失时，下游正常 EOF、`stream_error=null`；相同流去掉正文中的词则正确报错。当前探针路径可达，组合发生率未知，未见本批实际命中。 | **accepted，下一次网关修订顺手修。** 按完整 SSE 事件识别终局即可，不需要复杂状态机。[根对照](../../../../../runs/task2_swegym_dev_20260925/codex_review_20260925/root_reproduction/check_seams/result.json) |
| **F4 · P2：编辑镜像原有 dirty 文件时导出基线不对** | 未编辑的初态 dirty 文件已正确排除；但 agent 再编辑后，`solve_attempt.py:466–469` 仍相对 HEAD 导出，混入镜像自带改动。真实 replay 候选阶段 `replay_grade.py:333–375` 保留镜像初态，直接 `git apply --check`；小型 Git 对照确认会 apply 失败。本批 6 题初态 dirty：DVC4166、mypy10174/10308/10424/11236、pydantic8511。 | **accepted，扩量前修导出接缝。** 相对实际物化基线导出候选变更，复用现有正式导出能力或局部修正。不能把 apply 失败当模型 0 分，也无需清掉镜像原有依赖修订。仅改目标源码的候选不受该反例影响。[根对照](../../../../../runs/task2_swegym_dev_20260925/codex_review_20260925/root_reproduction/tracked_dirty/result.json) |

## 4. 已知未完成项与结果口径

1. **超窗 400 仍未接。** W1–W3 支持构造、计数和 EOS 的窄结论；W4 实际观察到 HTTP 200 空回复，**不是超窗行为验收通过**。交接页“W1–W4 通过”应更正。接 A 线共用函数后补窄验收；两款真实模型的工具/推理解析和首请求配置仍留给 GPU 冒烟。
2. **Conan noexec 事实成立。** `/tmp`、`/home/agent` 实际挂载及 Permission denied 日志一致。是否改变挂载执行权限属于既有 A 线/用户决定；未决定前 Conan 仍是受限诊断题，不能称所有公开功能测试可用。其余题不必一起等待。
3. **私有 gold 是辅助对照，不是同条件 actor 对照。** `private_control.py:17,24` 未指定 agent 用户，也没有正式 tmpfs/资源配置，执行的是镜像默认用户下的容器命令；不能仅由两边变绿就断言“唯一原因必是 patch”。现有 actor 目标 traceback、窄测试和 gold 输出共同支持主要结论，未发现因此需要全部重跑的题。今后需要严格区分权限、编译或资源原因时，补同身份、同 profile 的定点对照。
4. **清单并非所有版本逐字相同。** DVC6954 的坏命令已有 `orig2`；DVC4166 的 MWE 断言改正了原先对 gitignore 的错误理解；Conan 改的是日志筛选。历史版本均留在 attempt 中，不应把这些变化写成纯单变量实验。另有 Moto5960/6408 的两条 CC 工具参数去掉重复的 `cd /testbed &&`，外层仍先进入该目录，相关测试实际执行；本次未见语义变化，不新增阻塞。
5. **外层 rc 不等于每个子命令的 rc。** Conan functional 管道末端为 `head`，DVC5839 是多步骤脚本；本次靠输出中的失败数/内部 rc 正确读回。后续复用时保存各子步骤退出码，避免自动汇总只看外层 0。

## 5. 21 题如何使用 / 收口条件

沿用当前分类：**16 个可选探针题（含 4 个受限项），2 个前提未完成，3 个争议项。** 这不是 21 题都已适合模型比较或训练：mypy10424/pydantic8511 的前置语义对照，Moto5752/mypy11236/mypy17071 的处置，以及 Conan 等限制都未由本轮开发验证核销。

下一步只需：修 F1/F2，顺手修 F3/F4；用失败导出/合法空补丁、清理失败/正常收口、真实终局/正文同名词、dirty 未改/再改做窄对照。接好超窗处理后，用更新的 **solve_attempt→导出→评分** 路径做一条真实 CC + 桩的完整冒烟，再在 GPU 上验证两款模型的解析与实际窗口。任务二的 devcheck 复用了正式 helper 和 CC driver，但没有走这个完整探针派发链，也没有跑 miles 训练。

**达到上述范围就进入下一切片；不要求重新审完 21 题、重跑全套测试或解决所有题意争议才开始受控小批。** 本轮只新增审查文档和本地证据，未提交。

## 6. G1 追加复核：接受修复与定向验证 / 2026-09-25

**结论：`83760b15` 的 G1 修复可以收口，未发现新增阻塞。** 本节更新上文 §4.2 的待定状态；不核销 F1–F4、超窗处理或题意覆盖问题。本次核对提交、Linux 回传原件与源码摘要，并在本机复跑定向测试；没有重新连接远端或改生产代码。

- **实现已落地且就在当前分支。** actor 的 `/tmp`、`/home/agent` 与 grader 的 `/tmp` 显式设置 `exec,nosuid,nodev`。容量、权限位、UID/GID、capability 配置及 `no-new-privileges` 未变。两类 profile 的参数均纳入挂载标志；启动前检查以实际 agent / 候选身份直接执行新建脚本，并检查有效挂载，未用 `sh 文件名` 绕过执行权限。
- **代码与真机证据对应。** 远端 `sandbox_profile.py` 的完整 SHA256 与本机、提交一致（`7ffec82e…`）；四次 actor 运行均为 UID 54321，预检零违规，实际 `/proc/mounts` 保留 nosuid/nodev、没有 noexec。脚本在两目录执行成功，`/tmp` 中 gcc 产出的 ELF 也实际执行成功。
- **Conan 的原失败已消除。** `actor_v2` 与本次 `conan_full` 的镜像 ID、base commit、CC 包、激活脚本、命令清单、2 CPU / 4 GiB 均一致。`test_cmake_presets_with_conanfile_txt` 与 `test_add_env_to_presets` 从 Permission denied 变为 PASSED；`-k 'preset or jobs'` 选择由 8 pass / 2 fail 变为 10 pass / 0 fail，另有 8 skip / 27 deselected。额外不经管道的 `conan_rc` 记录确认 pytest 自身 rc=0。**这是选定功能测试组，不是 Conan 全仓测试。** 前后整体代码还有 relay / bringup 差异，不能把整轮说成严格单变量；挂载微对照与具体错误、执行事实共同支持 G1 归因。
- **grader 的验证范围清楚。** 真实 Conan 公开镜像下 verify 完整通过，UID 54322 在 `/tmp` 和 HOME 执行成功；HOME 在可写层，只有 `/tmp` 是本次改动的 tmpfs。尚未在 grader 中重跑 Conan 整题评分，不将启动预检等同于该题完整评分验收。python-slim 的另一次 verify 因缺 git 失败，作者已保留，未计作完整通过。
- **本次独立复跑：**在 `rh2/` 执行 `.venv/bin/python -m pytest -q tests/adapters/test_g1_tmpfs_exec.py`，**9 passed / 1.39 s，无跳过**，包含真实 Docker 下同探针的新挂载通过、旧默认挂载复现四项违规。作者的更大回归套件本次未重复运行。

证据入口：[作者真机记录](../../../../../runs/task2_swegym_dev_20260925/g1_exec/README.md)；关键原件在其 `evidence/devcheck/g1_mounts/`、`evidence/devcheck/conan_rc/`、`evidence/verify/conan_public/runtime_profile.json`，源码摘要在 `evidence/setup/env_facts.txt`。

**余项不阻塞 G1：**正式 `generate.py` 成功 audit 只保留 ok / violations / seconds，完整挂载事实仅失败时保存；检查确实执行，可在下次观测改动时补保存。本次回传的 prelaunch 原件已经包含事实。远端约 59 MB 独立工作副本是清理选项；四次 actor 记录中的清理结果均为空残留，本次未实时复查远端。

**部署提醒：**本地当前分支已含该提交，但此次真机使用的是 A 的独立代码副本。回传摘要显示 B 原远端代码目录仍是修复前版本；后续沿用 B 入口时要同步新代码、按新 profile 创建容器，不能把 A 验证通过理解为 B 原目录已自动升级。此项是挂载配置变化，无需为 G1 重建题目镜像。

**B 线后续：**采用新代码/profile 后，Conan 的这两项开发限制可撤销，但其题意／测试覆盖缺口仍单独保留。旧 `bash_env_v1` 的解释器、导入结论不因此失效，它未覆盖的构建产物执行条件用新 profile 定点补测即可；其余题只追查有 noexec 症状的历史失败，不为此重跑全部 21 / 216 题。也不承诺旧 gold 分数必然单调改善——恢复执行后仍可能暴露后续断言问题，以实际重测为准。
