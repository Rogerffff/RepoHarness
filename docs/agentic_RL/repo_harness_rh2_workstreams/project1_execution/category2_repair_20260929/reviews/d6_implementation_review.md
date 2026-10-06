# D6 首片独立实现审查

2026-09-29。审查对象：本工作区 SWE 材料修订实现及首批 mypy10424／17071 登记；基准 HEAD 为 `a31cdcd0adb0fab3e681201edfb928653fdf5b3c`，审查包含未提交改动。审查者为 fresh 独立上下文，先读实际 diff、源码、登记资产与测试，再读实施 Brief 和作者的 `ingest_implementation.md`；未修改生产文件、未运行远端／Docker／模型，未提交。

## 结论与停止条件

**没有发现阻止两题进入真实 CPU 验收的生产代码问题。** 已确认正式入口有固定来源重放与三层 pin、两侧消费共用材料、额外公开测试进入选择／恢复／保护、仅参考变化使旧资格失效。此结论不等于两题已通过正式评分或可进入训练。

本地检查曾发现 **1 项非阻塞的测试异常契约回归 N1，现已修复并经独立补核关闭**。后续六行CPU原件已在 [独立CPU复核](d6_cpu_evidence_review.md) 收口；真实actor原件复核发现共同初态接缝 **F1阻塞**：actor sanitize后的排除区路径摘要与fresh grader不同。详细实际路径和证据见 [actor证据审查](d6_actor_evidence_review.md)。因此当前不能将首片整体标为通过或转类；D6材料实现本身未出现新增blocking finding。

停止条件：六次真实结果及必要 actor 证据按 Brief 核齐后，独立复核实际节点、候选生效、材料身份和清理事实；不用再机械重跑全216题或扩展新修订类型。若真实运行揭示新的安装／节点问题，围绕该反例补证据。

## N1：未知 view 的防御性异常契约回归（非阻塞，已关闭）

- **发现时行为／位置**：`prepared_task_face.py:418` 新增 `view.revalidated()`，在原有未知 grading 类型检查之前运行。既有 `_Alien` 反例因此抛 `AttributeError`，不再抛 `GradingMaterialsError(reason_code="grading_bundle_type_unknown")`。原测试在 `tests/adapters/test_r2e_grading_scripts_unit.py:161`。
- **受影响的不变量与证据**：未知输入仍被拒绝，但原防御性入口的 typed 错误约定不再满足。实跑结果为 `1 failed, 59 passed in 7.65s`，唯一失败即该用例；同一用例的真实 R2E `HostGradingView` 构造、分派、entry script 检查此前已成功。
- **可达性／影响**：`test_only`。正式 prepared loader 先构造严格 `HostGradingView`；actor 与 replay 的正常消费路径不产生 `_Alien`，不能据此认定真实 R2E 评分失败或未知材料被放行。影响是兼容测试失败及错误 API 的变化，无已证实 reward／分布影响。
- **建议分期**：本片交付前窄修，不阻塞 CPU 证据采集。优先保留原 typed 拒绝并继续对合法 view 重验；若明确选择更严格的函数输入约定，也需说明为何调整测试，不可把真实 R2E 断言删掉。
- **复现**（在 `rh2/`）：`.venv/bin/python -m pytest -q tests/adapters/test_r2e_grading_scripts_unit.py::test_real_view_dispatches_to_the_r2e_builder_and_unknown_bundle_types_are_rejected`。
- **验收**：该反例与真实 R2E 构造同时通过；新增 SWE view 消费期重验仍存在。无需引入新状态、fallback 或改变正常输入。

**处置：accepted，已关闭。** 主线程在调用 `revalidated()` 前增加 `isinstance(view, HostGradingView)` 检查，不支持的对象抛原 reason code；合法 view 继续重验。独立只读核对工作区及冻结副本，并重跑真实 R2E／未知类型用例与 `test_forged_selector_is_rejected_at_consumption`，**2 passed in 0.48s**。主线程另报告 R2E 全文件＋SWE consumer 共20项通过、ruff通过；该20项为主线程证据，不冒充独立复跑。修复为局部 typed guard，无新状态或正常训练分布变化。

## 实际调用链与所有权

```text
host trusted-prep / replay prepare（单次准备）
  TrustedTaskController.from_repo_root
    → load_trusted_swe_revision_outputs
      → 原 load_trusted_ingest_outputs + 固定修订单 + 确定性重放 + 新 manifest
    → prepare_tasks
      → 公开 prompt / rollout / manifest；私有 host_grading_views

actor（既有执行进程与 event loop，没有新增服务或状态机）
  bringup attempt_assignments.resolve_for_sample
    → _face_for(assignment).grading_spec
      → manifest dispatch 三元组核对 + host environment digest + view 重验
      → build_grading_spec_from_host_view
    → generate 缓存本 attempt 的 spec
      → 同一 spec.hygiene 构造候选投影 → manager.grade(frozen_delta, spec)

replay（既有 driver / event loop）
  load_context → 同一 prepared 三个 loader
    → 同一 build_grading_spec_from_host_view
    → 候选冻结 / 投影 → 同一 manager.grade
    → 私有账本预建材料身份；正常／取消／故障收口补评分事实
```

可信准备进程拥有来源与修订单；actor 只读已经封板的公开／私有产物。测试恢复与权限布置由既有 root setup 执行，候选安装和测试仍以既有候选身份执行。没有修改网络、运行器可写策略或清理所有权；`generate.py`／`quiescence_barrier.py` 的在制改动和 R2E 生命周期／摄入改动均不属于本审查的实现归属。

## 跨边界不变量与核查结果

| 不变量 | 实际证据与结果 |
| --- | --- |
| 只能消费批准的首片修订 | 注册器固定 SHA，操作为 `append_mypy_p2p`，模型禁止额外字段和任意 shell／路径表达式；来源核 instance/repo/base、parent grading、public 与 test_patch SHA。新 manifest 及五个输出文件须等于原件重放结果。自洽但未登记的内存变体仍被正式消费校验拒绝。 |
| 原件及未修订题不变 | 新测试实比原始 JSONL 含换行字节：public／validation／重复簇原样；只有两题 grading／environment 行改变，其余214行不变。另由独立探针调用 `git show HEAD` 的旧 renderer 与当前 renderer，对原216题的5种脚本做 **1080次逐字节比较，全部相等**。 |
| 新增参考确实进入执行材料 | 两题新增 case 与原 test_patch case 取并集，原 vendor 命令前缀不变；完整 eval、候选测试和供应分段测试脚本用同一派生选择式。仅登记 nodeid 不会替代实际 case 选择。真实 mypy 收集／运行仍由六条 CPU 证据确认。 |
| 新增 oracle 不随候选替换 | `check-isinstance.test`／`check-typevar-unbound.test` 并入 `hygiene.test_files`，在候选投影中剔除对应改动；可信 setup 逐文件恢复 immutable base、校验普通文件及固定 SHA，再 apply 原 test_patch；既有 attestation 和权限保护消费同一清单。定向本地 shell 测试覆盖新增文件不在原 patch、内容／symlink 篡改、错误 SHA 在候选测试前退出。 |
| actor／replay 材料不能错配 | 共享 prepared loader 与 builder；私有文件 SHA 同时对启动输入和 manifest，逐行核环境包摘要，actor 再对 authoritative assignment。新测试覆盖旧 manifest／新 host、改 host SHA 后仍旧环境摘要、旧分派／新 face 三种混配。 |
| FrozenPatchArtifact 不带环境摘要不造成当前隐式混配 | `bringup.py:2092` 按本 attempt 绑定取 face；`PreparedTaskFace.grading_spec` 对分派环境摘要；`generate.py` 为同次 attempt 缓存 spec，投影和 manager 使用同份 spec。manager 还重算工件／baseline／projection 及 public、镜像、代码血缘。当前没有一个无材料选择的“任意旧工件恢复评分”生产入口，因此没有仅因缺少字段就成立的漏洞。显式旧候选重评仍应生成新版账目，不改历史结果。 |
| 仅参考改变也不能套用旧资格 | 独立探针取真实10424修订，仅将一个精确 nodeid 改成模型允许的带文件形式：执行脚本摘要相同，grading 材料身份与环境包摘要不同，旧资格返回 `grading_materials_identity_mismatch`。该未登记变体同时被来源重放校验拒绝；不是新增可用材料。parser／binding 的独立身份测试亦通过。 |
| 分区不把缺席或未执行当成功 | `SWEGradingRevisionContext.diagnostics` 分原F2P／原P2P／新增P2P，保留 success、failure、missing、skipped、unaccounted；无 verdict 为 `not_evaluated`、结果 `None`。正常 manager sidecar 与起容器前 image failure 反例均通过；公共联合 reward 和 `swe_f2p_p2p` 不变。 |
| R2E 与原 v2 仍可用 | 原216题脚本字节比较通过；初次兼容命令的真实 R2E 路径通过，唯一失败 N1 已窄修，独立补核通过。未声称独立验收其他线程正在修改的 R2E 材料。 |

早退覆盖的精确边界：新 `GradingInfraError` 收口即使没有日志，也落空日志与 `not_evaluated` sidecar，`eval_log_available=false` 区分未产出和空输出。manager 的无日志取消仍不单独落 sidecar；replay 在任何异步阶段前已建立版本与分区行，actor 的 attempt／prepared 绑定仍可回溯身份。legacy diff 的 `patch_apply_failed` 返回仍不落 sidecar，但正式 frozen 路径应用失败走 infra。未将这些现有边界误报为“每次早退必有独立 sidecar”，也未发现它们会把未执行的新增参考记作成功。

## 本地验证与复核范围

在 `rh2/` 执行：

```bash
.venv/bin/python -m pytest -q tests/envpack/test_swe_material_revisions.py tests/adapters/test_swe_revision_consumers.py tests/grading/test_material_revision.py tests/contracts/test_full_registry.py
# 88 passed in 10.53s

.venv/bin/python -m pytest -q tests/adapters/test_r2e_grading_scripts_unit.py tests/adapters/test_w1b_prepared_task_face_v2.py tests/test_w2a_trusted_views.py tests/test_w1b_prepared_tasks.py
# 初次审查：1 failed, 59 passed in 7.65s；唯一失败 N1。无 skip／xfail。

.venv/bin/python -m pytest -q tests/adapters/test_r2e_grading_scripts_unit.py::test_real_view_dispatches_to_the_r2e_builder_and_unknown_bundle_types_are_rejected tests/adapters/test_swe_revision_consumers.py::test_forged_selector_is_rejected_at_consumption
# N1 修复后独立补核：2 passed in 0.48s。
```

独立反例与兼容复核脚本：[d6_independent_probe.py](d6_independent_probe.py)。从仓库根执行：

```bash
rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/reviews/d6_independent_probe.py
```

结果：`old_head_script_comparisons=1080`、`original_tasks=216`、`all_original_scripts_byte_equal=true`；仅参考变体脚本摘要不变、材料／环境摘要变，旧资格拒绝，正式 controller 返回“package 与从来源重放的修订材料不符”。该探针未写原件或修改登记 pin。

A～N 适用性：A/D/E/F/G/H/M/N 为本片主要核查项，证据见上表和 N1；B 核到新增拒绝仅针对损坏／未知／混配材料，旧资格不匹配仍沿用既有未知环境归因，不新增奖励或整组策略；C/I 按真实 CPU 与 actor gate 留待项，不增加用户批准闸门；J/K 当前窄型别与单 loader 足以表达首片，没有扩建修订平台；L 没有新增队列或并发 owner，摄入只在准备阶段发生，实际测试耗时仍待 CPU。此轮不是整体训练验收，不重做与改动无关的 crash／重启／队列故障矩阵。发现的问题由 E/N 覆盖，无需修改审查标准。

## 六行验收工具补核（未执行远端）

只读核查运行工具 `runs/category2_repair_20260929/tools/d6_acceptance_v1/run_acceptance.py`，当前 SHA-256 为 `f22865a56e68b35a52bb694c1fef63bf59ff54c6f08bd8fafeb9285fac78a538`。实际导入／参数与返回字段对照生产 `prepare_for_replay`、`load_context`、`PreparedTaskFace`、`CandidateInput`、`ReplayGrader.replay_one`、`SWEGradingManager._observe/_exec_bash`、`candidate_segment_facts`、`FrozenPatchArtifactV1` 和 `lookup_parser`，未发现不匹配。

- 运行前封板检查涵盖逐文件代码清单、题级私有素材 SHA／长度和两题有效 F2P/P2P；actor／replay 的脚本、身份、hygiene、预算逐项比较。
- 六行通过条件结合完整日志的精确节点集与预期状态模式、安装事实、候选源文件实际导入路径／摘要、新增测试恢复后的 SHA／root属主／不可写、冻结工件与投影及 public／镜像关联；没有只以 reward 或外层 exit code 代验。
- 补充观察由 `_observe(..., phase="post_candidate_observation")` 的既有调用触发，以相同候选 UID 执行，限时25秒，并不回写 parser、reward 或 spec 摘要。该观察仍是候选进程输出，适用于本次固定候选核验，不应扩称为抗任意恶意候选的可信证明。
- 脚本自动结论明确保留“待独立复核与 actor”；清理失败、单行验收失败和残留未知都会停止后续派发。具体失败断言原因、完整安装文本与实际测试断言仍需结果出来后审阅。

独立读取并重算 `runs/category2_repair_20260929/frozen_d6_v1/code_v1_manifest.json`：SHA-256 为 `43186d0d85f1eb4e7d28e51b92a9a2c82bf1d4ff178d785d8d4846795300460e`，**659个文件与冻结目录逐项匹配**，其中包含 N1 修复。此处确认冻结身份，未扩大为对冻结树中其他线程改动的独立审查。

## 原真实证据门槛与当前状态

Owner：主线程／第2类负责人；公共初态接缝由主线程协调A线。Gate：首片正式验收、逐题转类前。以下前三项已由六行CPU独立复核完成；第4项真实公开开发／冻结子链完成，但fresh grader重建接缝受F1阻塞，不能核销。

1. 两题各 noop、gold／可信正确修法、已证错误补丁共六次完整 CPU 评分，目标联合 `0/1/0`；核完整日志而非只看 reward。
2. 原F2P／原P2P／新增P2P 的准确 nodeid、missing／skip／原始状态，与 case 选择、固定文件 SHA、修订材料摘要逐项一致；新增公开 P2P 在未修 base 应通过，在相应退化上失败。
3. 正确候选实际安装／导入生效、完整测试退出码、资源／超时归因、候选及评分两层清理；不能复用旧材料的得分来代替本轮。
4. 两题 actor 开发入口窄核或可适用的既有同版本证据，加本轮 prepared 运输／冻结 join 证明。当前本地 spec 字节一致只能证明接线，不能替代真实工具链。

六次完成后按实际材料版本收口；无需为进入这一步另设授权。后续 MONAI／题面／精确参考绑定仍按对应能力切片实施，首片通过不能写成其余题已完成。
