# DVC9395 R20 题级准备预算支持差异窄核（非作者）

2026-10-03。R20 `cat2-cpu-r2e093-swe40-prepare900-20261003-v1`，parent 为 R19 `cat2-cpu-r2e093-swe40-pyd6283-moto6114-20261003-v1`。

**结论：未发现阻断题主使用固定 R20 new-prepare、接续真实正式控制的实现问题。** policy 只绑定当前 9395 behavior-v2-draft／c093 镜像和固定 8316，对两题既有 `env_reset_timeout_seconds` 作 300→900；其它 262 个 spec 快照完整相同。9395 的正式 revision、grading digest、test patch、image+None 和请求 input SHA 闭合；replay 账本保存实际 spec 的900，评分入口继续接收同一个 spec，没有仅改账本数字而运行仍用300的迹象。

这仍是**版本化支持接线核查，未验证正式 CPU 恢复或900足够**。既有两次 R14 noop 保 infra/null；隔离242秒成功不补成正式恢复。已见私有材料和旧 actor／失败原件，不是 fresh 公开读者。本轮只用 stdlib 离线读取／SHA／AST／JSON和差异比较，不运行 CPU、SSH、Docker、测试或任何 release 入口，不重审题义／旧全仓，不改输入或共享文件，只创建本报告。

## 1. 实际变化范围

实读新 manifest SHA 与回执一致：`2a4ceb0315ea959232151d70f29ccc48bd34bdb0cb7dcfbb4aa177fec07bd393`；parent manifest 为 `2cfdd9b4f1134c0915346b727b729665482c4c1121b550764833f16f2982402e`。两 manifest 的成员表无删除，变更恰为 SNAPSHOT_ID、prepared_task_face.py、replay_grade.py；新增 policy.py、policy JSON和一份窄维护测试。6 个变更／新增实际文件的 SHA／size 均与 R20 manifest 相符，Python 仅作 stdlib AST 解析，未执行。未重新读回全部1479成员，题主的冻结成员核查与部署 loader 事实分开保留。

实际 source diff：prepared face 在原各题镜像登记分支结束后核 closed policy，原档位必须等于300才赋900；replay 仅对 policy 两题新增 `budgets.env_reset_timeout_seconds` 和 policy/request SHA来源。没有改 manager。manager 与 sandbox_profile 实际字节和 R19相同，SHA分别 `1783533e1e3b66a57fcaa5a599a1da4f8e4e886318e24f040c6df91f294c1c1e`、`313bfd7691c5dca775aa0e9992f13561e20936f062ddfa3d269892b6bf4895ee`。

所以900适用于**九处既有 reset 消费**，包含 trusted setup、控制面保护、git/environment reset、候选预检及前后观测等；它不是只给 chown 的新专用参数。其它题默认300保持，原已900的 Dask7656也未变。ownership／official file/SHA／祖先sticky／root保护判据未改；原资源／网络和安装、测试、apply、whole、cleanup预算没有放宽。增加的是这两个精确绑定目标的准备/reset时间额度，不能表述成所有预算完全不变。

## 2. DVC closed policy 身份链

固定 JSON 文件 SHA `d417dbb8d3140e6a0082f2f12cda02fd492feb14db9375ace3d69222e48acdab` 在源码 `POLICY_SHA256` 钉死；每次 load先核全字节SHA，再用 StrictModel 和 Literal闭集模型解析。固定两条目标及顺序，不接受其它task、自由timeout或CLI覆盖。`preparation_budget_record` 对非目标直接返回None；目标调用 `HostGradingView.revalidated()`，消费时重验 task/source/instance/嵌入grading摘要，再核以下精确条件，任一错配抛ValueError。

| 9395 条件 | 实际绑定 |
| --- | --- |
| task | `swe_gym_lite::iterative__dvc-9395` |
| revision | `dvc9395-behavior-v2-draft` |
| grading_bundle_digest | `sha256:b939c2ea3070d0187a663891f33affc5347ee0029c048cf0c984be4f0d02f8f8` |
| test patch UTF-8 SHA | `964c80ef786b71091fcc722d8b3fdcd8afe8ba7e3f5fb511d6cb9661a25c2777` |
| grader image ID | `sha256:c093861f62b8071b3c1e5b3142abd5843888421364e69dd728cb80856f621b60` |
| image_manifest_digest | 必须为 None，保留派生 local-build 身份 |
| 支持 request | `dvc9395-control-protect-timeout-support-20261003-v2` |
| request_input_sha256 | `3bf174133d17334cc752c4a9775acf9782fc2017b76cd4682d5202081c1ddf57` |
| 原档位／新档位 | Literal300／Literal900 |

实际 publisher prepare 的9395 private host行中 revision、grading digest与policy一致，独立 hash test_patch 得到上述固定SHA。它与旧R14 recovery host行、公开task view和prompt行按JSON对象逐项相同；本轮不以source预算policy改动制造材料／public digest变更，也不重写旧证据。

`checks/policy_fixed_inputs.json` 列的两份支持输入和 root design 实际SHA均匹配；root设计 `f85a1edb7a1363effc174fb79d16e949355b89623edffde715e7e992d05e845b` 明确选定这两个固定材料／镜像的300→900，禁止泛化覆盖、保护／资源放宽和旧release热改。请求 SHA由固定policy文件闭合并写入账本，运行时不会重新访问题主请求原件；这是固定来源标记，不是请求文件可动态操控预算的接口。

## 3. 独立复算 scope，不直接信 root_scope 摘要

完整读取 parent_snapshot_attempt01.json 与 candidate_snapshot_attempt02.json，各264条，key集合相同。独立比较所有行和32项 `spec_all_fields`：恰好两条变化，9395／8316均只有 `env_reset_timeout_seconds:300→900`；顶层重复预算字段随之变化。其余262完整行相等，所有264的 public/environment/material/grading/host/rollout摘要和脚本SHA相同。root_scope_readback 与消费差异摘要的计数和字段相符，R20回执附本与release checks附本字节相同。

这是原件快照的独立JSON比较，未重新执行264 consumer。快照生成器将 callable记录为module/qualname，并保存targeted compile renderer结果，不保存任意函数全部行为；因此不能把“32项相同”扩大为全部Python闭包语义证明。两处source实际diff仅新增closed预算接入，未改现有parser／renderer函数体，与这一证据范围相容。

## 4. 实际 spec 与 ledger900接线

source静态路径：`replay_one` 504–507行构造spec；569–577行重新核目标policy，并将 `spec.env_reset_timeout_seconds`（非字面量900）写入 row.budgets。镜像inspect后仅dataclasses.replace镜像身份字段，保留该预算；644行候选阶段用该spec，717–720行 `manager.grade(..., spec=spec)`继续传同一spec，未再构造一个默认300的评分spec。

读取实际 replay 8例原件和生成脚本：调用真实 `ReplayGrader.replay_one`，替代Docker／candidate stage／cleanup，主动停止在完整spec捕获点，没有进入真实评分。它从临时 ledger文件重读并断言saved==returned row；不是只打印一份手写期望。9395四例如下：

| 路径 | 捕获完整spec | 落盘 reset | 实际结论 |
| --- | --- | --- | --- |
| 默认已登记grader | 32项／900 | 900 | 固定c093，synthetic_stop_after_complete_spec_capture |
| 精确override | 32项／900 | 900 | 同上 |
| 错inspect ID | 无进入candidate | 900 | 保留实际错误ID，inspect_id_mismatch，report=null |
| 错override | 无进入candidate／无inspect调用 | 900 | explicit_override_not_registered，report=null |

错误路径的ledger900表示已选择的政策预算，不代表镜像匹配或执行成功；scope readback已明确complete_spec=false，不能漏掉这个区分。正常路径捕获spec与candidate快照32项精确相同。外部替代依赖8例只支持真实入口接线／落盘和拒绝行为；不算CPU、安装、pytest或正式矩阵结果。发布者维护5例通过原件已读，未在本轮重新执行，不与其它轮次测试计数相加。

## 5. 实际部署读回及限制

CPU-a部署receipt固定同R20 release／manifest，记录transfer1479文件、SHA及exact-member-set通过；trusted loader returncode0，stdout原件与receipt result相同，stderr实际为空，状态 `material_and_source_readback_passed_cpu_not_run`。这支持发布材料／source部署读回，不等于正式任务已跑。

grader_image_readback记录实际只读image inspect，9395actualID与固定c093匹配，new_container/install/test/taskCPU=false；其原copy与support镜像读回对象一致。本轮实读该回执／镜像摘要，未在线inspect；镜像摘要给出stdout/stderr SHA但没有在此次入口明确交付对应原stdout文件，因此不把摘要单独扩为本轮已逐字核完整Docker输出或容器HostConfig。部署loaderstdout原件已另读，不与镜像stdout混淆。

当前尚无题主新R20正式CPU结果。900充分性、两次旧失败具体chown子步／宿主原因、实际安装和测试、正式三方／六控制及新运行两层cleanup仍待真实原件。政策不解决准备效率，也不改变候选判题；900若仍超时应保失败停止，不自动再升档或机械重试。题主可依当前固定支持范围new-prepare，核新summary/spec与真实ledger900，再串行接续未有效完成控制；首个infra或清理未知停后续。

本核仅确认新支持无静态阻断，不能清除“正式恢复待验”状态。旧R14失败null、旧隔离成功和既有actor证据保留各自范围；不授予fresh公开验收、新actor／模型probe、训练或稳定性资格。

## 6. 实读SHA及最少证据入口

以下是文件字节SHA；未把发布者全成员核对计成本轮1479件独立重核。

| 文件 | 实读SHA256 |
| --- | --- |
| [R20 9395 回执](../../../../../../../../runs/category2_repair_20260929/publication_cpu_takeover_20261003/r20/dvc9395_publication_receipt.json) | `dd6e6894a4079e141d2fe54ab3775d012d58f3b0adbfedfede8813598f0447cb` |
| [R20 release manifest](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_093_swe40_prepare900_v1/manifest.json) | `2a4ceb0315ea959232151d70f29ccc48bd34bdb0cb7dcfbb4aa177fec07bd393` |
| [R19 parent manifest](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_093_swe40_pyd6283_moto6114_v1/manifest.json) | `2cfdd9b4f1134c0915346b727b729665482c4c1121b550764833f16f2982402e` |
| [typed policy consumer](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_093_swe40_prepare900_v1/repo/rh2/src/repoharness2/envpack/preparation_budget_policy.py) | `51fcd3a9439ba0bfe0d8425076ef6f370788b32308d113adc42906f344db5d2b` |
| [固定 policy JSON](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_093_swe40_prepare900_v1/repo/rh2/src/repoharness2/envpack/preparation_budget_policy_v1.json) | `d417dbb8d3140e6a0082f2f12cda02fd492feb14db9375ace3d69222e48acdab` |
| [spec 构造消费](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_093_swe40_prepare900_v1/repo/rh2/src/repoharness2/adapters/slime/prepared_task_face.py) | `190616105945f649c102aa15d7b86a810a63f77c6723b297e062378ada1f24cc` |
| [replay 账本消费](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_093_swe40_prepare900_v1/repo/rh2/src/repoharness2/adapters/slime/replay_grade.py) | `22836b6ac9d57dde0717880a77af829e620a8674bb9cf8fb400e808e49f87ef5` |
| [root scope readback](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_093_swe40_prepare900_v1/checks/root_scope_readback.json) | `958dd51483d4320bff8b13d269b3fb8d568a13e3e6f0b41ccd70a516d3a81e56` |
| [264 parent 快照](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_093_swe40_prepare900_v1/checks/parent_snapshot_attempt01.json) | `cd47164aaab41e577dd107a863e24692727d8477d7fb164956abaf092bc65a88` |
| [264 candidate 快照](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_093_swe40_prepare900_v1/checks/candidate_snapshot_attempt02.json) | `373e4ad252f71876bd782cd3da385d3e3ee10719b5dabe3dc46f7aba510711d1` |
| [外部替代依赖的 replay 8 例原件](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_093_swe40_prepare900_v1/checks/actual_replay_attempt01_rows.json) | `09fa5b50cd32b9fde491213f83c0f3ebec98e698ca10a9f11ebca164a2c42fa5` |
| [CPU-a 部署回执](../../../../../../../../runs/category2_repair_20260929/host_setup_20261003/cpu-a/release_receipts/cat2-cpu-r2e093-swe40-prepare900-20261003-v1.json) | `7668f440ecd965f4a6f8b219ad14d56a58e46b79f980777d8c64f9d384e546a8` |
| [实际镜像读回](../../../../../../../../runs/category2_repair_20260929/publication_cpu_takeover_20261003/r20/grader_image_readback.json) | `4a876ed34ed1a43f2002b555b97cca73eb56e251538b9e85f213c44acd891a28` |
