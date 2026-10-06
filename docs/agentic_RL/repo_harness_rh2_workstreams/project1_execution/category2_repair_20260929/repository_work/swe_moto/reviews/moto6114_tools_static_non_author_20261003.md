# Moto6114 工具非作者静态窄核

2026-10-03。审查者：Codex 非作者 subagent。依据当前 `coordination_workflow_20261003.md` 的题主安排独立核查授权，仅核 `tools/moto6114_cli_matrix_v3/` 四件文件及 `tools/moto6114_uid_smoke_v1.py`，对照固定 R7 源码；仅新增本报告。已读取私有评分补丁、反例／gold 摘要和修订登记，**不是公开题面的干净上下文盲读者**。

**当前结论（含同日一次最小修后复核）：v3 三臂编排未发现阻止既定 CPU 执行的静态问题；UID smoke 的错误导入已修正，静态阻断已关闭，其余静态范围未发现新阻断。** 修复没有修改共享 consumer、评分语义或预算，无需重新审批。v3 当前尚未运行，修后 UID smoke 尚未运输／运行；本报告不授予 CPU 验收、真实 actor、探针或训练资格。

复用 [新测试非作者审查](non_author_new_tests_review_20261003.md) 的材料语义结论，以及 [v2 维护者回执](moto6114_cli_v2_maintainer_review_receipt_20261003.json) 的既有入口核查。本轮核了 v3 差异及所需实际 API，没有重审整份修订材料、其它题目或历史 CPU 矩阵。

## 原 finding：UID smoke 导入不存在的模块（修后已关闭静态阻断）

**[P1，UID smoke 执行前]**

以下保留原审查行为和修法依据；当前处置为 `accepted`。题主修正后，本审查者按授权进行一次最小复核：修后 SHA 为 `da3798980fc199315b0977a49792769cd042869eab7e57d7ebc5b846af8dc2b0`，正确导入恰出现一次，原错误导入为零；把这一处正确导入逆替换为原导入后，完整脚本 SHA 恰恢复原值 `6ffdd64a27e2f872037489610e9dd43c5fb55b27e657b63ae70a0a0579252e35`，证明本次只有所述单处字节差异。固定 R7 的 `envpack/materialize.py` 存在、定义恰出现一次，文件 SHA 仍与 R7 清单匹配；v3 manifest 和三件成员 SHA／长度均未变。**静态导入阻断关闭，运行验收仍未执行。** 本次未导入项目、未连接远端或调用 Docker，未重核材料语义。

- 当前行为：`tools/moto6114_uid_smoke_v1.py:69` 执行 `from repoharness2.adapters.slime.materialize import BASH_ENV_PATH`。固定 R7 中没有该模块。若此前启动、sanitize、trusted init 成功，脚本仍会在写激活文件、激活核查、UID／导入检查之前以 `ModuleNotFoundError` 退出。
- 违反的不变量：新宿主检查须真实到达生产同形的激活与 UID54321 导入路径，不能把容器初始化或脚本静态存在当作完成检查。
- 证据：固定 R7 的 `rh2/src/repoharness2/envpack/materialize.py:53` 定义 `BASH_ENV_PATH = "/rh2/bash_env"`；`adapters/slime/generate.py:140` 和 `adapters/slime/replay_grade.py:58` 均从 `repoharness2.envpack` 导入 `materialize`。生产写入位置见 `generate.py:4976`–`:4988`。
- 影响：当前 smoke 无法提供新宿主身份／激活证据；不影响独立 v3 CLI 三臂入口。异常发生在 `try` 内，现有 `finally` 会尝试检查归属并移除本 job 容器，不能因该错误宣称清理失败已发生，也不能宣称清理已实际通过。
- 修法与分期：题主现在把导入改为 `from repoharness2.envpack.materialize import BASH_ENV_PATH`，保留固定 R7 和现有检查范围；无需改生产模块或增加兼容 shim。
- 最小静态复核：在固定 R7 `rh2/src` 中搜索 `BASH_ENV_PATH` 定义，并核该导入指向现存文件。此轮已经完成该文本核查，未实际导入项目。
- 修复验收条件：记录修后脚本 SHA，窄核正确导入和其余字节差异；随后实际 smoke 原件应显示激活通过、UID54321、指定 conda 解释器及 `/testbed/moto/rds/models.py` 原文件摘要正确，最后自有容器／网络查询成功且均为空。导入修好只关闭静态阻断，不能直接核销运行验收。

## v3 编排与 R7 的一致性

固定对照树为 `runs/category2_repair_20260929/releases_20261003/r2e_088_swe12_git_candidate_v1/`。外部 manifest SHA 为 `f9dfcd16c9c88e4f514512e61781856b7d6f1a71a20b64cd1843d20546c5009b`，清单含 905 件；本轮只核了本题相关 7 个 API 源文件与 `verify_release.py` 的字节摘要，全部匹配清单，**没有执行发布验证程序或重核全部 905 件**。

| 检查项 | 静态证据与结论 |
| --- | --- |
| 工具身份 | v3 manifest SHA `5ac3782449a69083f38dc50c38aba08211798813db6a7045d692a3fb5c4cb5bd`；清单的三件成员 SHA／长度全部匹配，`matrix.py` SHA `fbfab088780b74c994af980cee7972204782eabccc1d42c37f422333c7126740`。 |
| 原入口 | `matrix.py:98`–`:100`、`:153`–`:155`、`:168`–`:173` 依次调用原 `scripts/replay_grade.py prepare / export-gold / run`。CLI 参数名、`load_context` 与 `build_grading_spec_from_host_view` 签名均与 R7 相符；唯一 task ID、repeat=1、三个独占输出目录和各自 run ID 明确。 |
| v3 修正 | 相对 v2，只新增正式 `derive_test_command_for_bundle` 导入、用它替换 `gview.grading.eval_cmd` 读回，并在核对前保存实际消费信息。R7 `spec_vendor.py:215`–`:238` 的接口存在；生产测试脚本也在 `prepared_task_face.py:219` 调同一函数。 |
| 完整命令／安装 | 固定 vendor JSON SHA `0da8f9caeec18e3b41386fb66e677807335c0fe12c41d811dd9fb65f9bfcc925`，Moto 4.1 原安装为 `make init`，命令前缀为 `pytest -n0 -rA`，本补丁唯一测试路径为 `tests/test_rds/test_rds_clusters.py`。因此完整派生命令与 expected 相符；修订没有安装替换分支。 |
| R7 材料身份 | producer manifest SHA `9bf50d0a4e14ace49eac459c50ad630d9e228365d606e0dcfc9d9f529b88615e`、本题 registry SHA `27e1b01dfec9aa2284e79fec753f70b62f6bd45462346483484f98785a59ae22` 与脚本常量相符。公开／评分／环境身份、父评分身份及 registry 绑定与 expected 的对应字段相符。 |
| 原参考保留 | 固定 producer 本题的原 F2P、原 P2P 与 revision 和 expected context 三处逐项、逐序相等，数量为 1／34。原补丁 SHA `32beadd88d5189dcab69b796980a93c464cb7b6f9d16bc8329d5da3e80571b61`、有效补丁 SHA `fe211059864c661a557758f5c5ed4106016c767cbe98eaef4718733008a87d5f` 均按内容重算匹配；没有新增或重分参考。 |
| 脚本摘要 | `matrix.py:135`–`:140` 会从正式 spec 对五份脚本逐份求 SHA 并比较 expected：eval、trusted setup、candidate test、candidate install、test after install。生产 spec 确实由相应五个 renderer 构造。本轮核了这条消费／比较路径，**未执行 renderer，未将 expected 中的摘要冒作本轮实际生成结果**。 |
| gold／反例 | 固定 validation 中 gold SHA 为 `bfae681e1044acffe64d7d65c1615b5545f4b62b2625961b7a6fe7d0ad591bbc`，与导出后断言相符；私有 wrong-first 原文件 SHA `5c042121e4bf56693c71f418c139b628d108b0c1fcd67bc0af48201e471c6451` 已重算匹配。 |
| SWE 派生路径 | 原 CLI `--derived-image` 传入实际 image ID。R7 `ReplayGrader.replay_one:513`–`:571` 切 grader spec 到 local build 并 inspect 实际 ID；候选侧 `:332` 使用同一派生引用。该引用自身为不可重指的 ID；未使用只支持 R2E 的 rollout overlay。`:124` 的 actor spec 只是构造，未启动 actor。 |
| 镜像／配方 | binding 的来源和派生 receipt SHA 均匹配原文件，base ID、derived ID、Dockerfile SHA、wheel manifest 及三件 wheel 清单与回执逐项相符。编排会检查来源 RepoDigest、linux/amd64、基底层前缀、仅增加一层及离线 wheel ENV；原安装仍为 `make init`。这些证明供应绑定，不能证明测试安装成功。 |
| 限额／预算 | 编排要求 rollout／grader 均 2 CPU、4 GiB、512 PIDs，grader shm 64 MiB；spec 默认 setup/apply/test 为 300/120/1800 秒。CLI 显式传入候选 900、整次 grading 1800、候选清理 120、镜像 1800 秒，与 R7 参数一致。实际容器限额仍需读原件。 |
| 两层清理 | candidate ledger 要求 `cleanup.removed=true`；CLI `finally` 必调 manager.close，`final_exit_status` 对未关闭 grader 容器返回非零，编排要求其 exit_code=0、无 halted／aborted。两类容器均从 `MILES_RH2_RUN_ID` 取得 run label；每臂另查同 run 标签容器和网络均为空。manager 累计清理诊断与最终残留应分别读回，不能只看 candidate 字段。 |

## UID smoke 的其余检查和边界

调用签名与 R7 一致，原错误导入已按上述最小复核修正：`docker_run_args` 包含首个 `run`，`default_docker_runner` 支持 `input_bytes`，sanitize／trusted init 返回 key-value 事实，activation 返回带 `to_dict()` 的报告。脚本使用原 rollout profile、network none 和 job 标签；在真实 agent UID 下用与生产同形的 HOME／BASH_ENV 运行非交互 bash，检查解释器、导入路径及 base 文件摘要。2 CPU／4 GiB／512 PIDs 由 profile 的实际 run 参数下发，并保存容器 HostConfig；CPU／内存另有实际值断言。

每次 Docker 调用有 300 秒外层等待限制；sanitize／init／activation 还受各自生产 helper 的超时约束。`RolloutTaskSpec.time_budget_seconds=300` 在本工具中没有 orchestrator 消费，**不能解释成整个 smoke 的 300 秒总期限**。本轮没有把这一点升级为阻断或要求新增公共预算；实际派发需如实保留外层作业时限。

清理只针对唯一 `rh2-<job>` 名称，先检查 `rh2.run_id`；归属不同则拒删。成功路径与 `try` 内异常路径均进入 `finally`，保存移除返回码及自有容器／网络查询；零残留查询不是容器创建／删除的实际运行证明。修后执行须同时检查这些查询返回码、stdout 和全过程失败信息。smoke 仅补新宿主 UID／激活／导入条件，没有 CC、模型调用、冻结导出或评分，不能称真实 actor 或 actor→grader 验收通过。

## 运行后的窄验收读回

这些是既定验收的证据要求，不是新的审批闸门，也不是必须扩写编排的 finding：

1. 三臂各核实际 R7／prepared 材料身份、派生 image ID、script SHA、预算、候选冻结和 apply 记录，确认使用的有效补丁及完整 35 参考与本次 expected 相符。
2. 逐条核 1 F2P／34 P2P，无参考缺席、意外 skip 或 collection／parser 错误。noop 为目标 F2P 失败、34 P2P 通过；gold 全 35 条通过；wrong-first 必须因新增集群身份断言被拒，原 34 P2P 保持。只得到 0／1／0 不足以接受。
3. 核完整安装日志中的每条失败信息及实际导入／候选绑定，不能仅凭 `RH2_INSTALL_RC=0`；核真实测试命令、测试退出码、Start/End 标记及可信 footer。区分正常负对照失败与基础设施失败。
4. 核 candidate 清理、manager_close 的 containers_open／supply_open／清理历史、最终退出状态，以及同 run 标签资源零残留原件。出错时保存该次原件，按原因处置，不自动把零分当题目失败。
5. 修后 UID smoke 须按新 SHA 运输和执行，保存身份与清理原件；与 [历史 actor 条件记录](moto6114_historical_actor_conditions_20261003.json) 的适用范围分别对账，不能把新宿主导入成功替代真实 CC 或新冻结工件证据。

本轮及一次最小修后复核只进行了文本／JSON／SHA256／AST 静态检查；没有连接远端、导入项目／Moto／SDK、运行项目／测试／发布验证、调用 Docker、安装或修改生产与题主材料。UID 原审查字节 SHA 为 `6ffdd64a27e2f872037489610e9dd43c5fb55b27e657b63ae70a0a0579252e35`，修后 SHA 为 `da3798980fc199315b0977a49792769cd042869eab7e57d7ebc5b846af8dc2b0`。当前停止点为静态导入阻断已关闭、v3 静态入口无阻断；由题主继续既定执行及原件读回。
