# Dask7138 R15 三行正式 CPU 增量独立核查

依据日期：2026-10-03。结论：本轮实际正式评分矩阵 **noop 0 / compatible_ravel 1 / source gold 0**，与 `dask7138-array-keyword-v1` 的 **1F469P** 相符；本窄核未发现阻断。这里只确认固定 R15 consumer 下三份 CPU 评分原件与题级矩阵，不确认 GPU 部署、模型解题或训练资格。无需因这份复核重跑已终止的 CPU 原件。

核查者未参与作者修改或远端运行；已读私有 gold 和旧报告，所以是非作者复核，不是公开盲审。本轮只做本机 SHA/大小核算、原日志逐参考解析、冻结代码静态追溯及纯本机模型/spec 重建；未跑 SSH、Docker、远端或本地题目 CPU 测试、模型推理。仅写这份报告与[同名 JSON](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_dask/reviews/non_author_7138_formal_cpu_r15_review_20261003.json)，旧审查保留。

## 实际评分与参考完整性

逐一复算[原件清单](/Users/roger/Desktop/claude-code-verl-stage0h/runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask7138-formal-cpu-c-20261003-v1/remote/readback_manifest.json)的 45 个成员，合计 1,449,916 字节，无排除、大小/SHA 不一致。清单 SHA 为 `02c6904a59418cebb976ea309d359f29a8743a67ca290528881561ee51d856c5`；固定[作者读回](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_dask/tasks/dask__dask-7138/formal_cpu_readback_r15_20261003.json) SHA 为 `54a27294c7efc4f717ff4200085e1a06fc780b2c7857780f91ca8f341e851aa7`。结论来自原件，未用作者摘要替代解析。

每份 eval 恰有一个 Start/End 区间，仅解析区间内 `-rA` 状态；每份模块各有 562 个实际节点，评分参考各 470 个均出现，无重复、缺失或跳过。三行的完整参考状态、分区、原件 SHA 和 artifact 绑定在 JSON。

| 候选 | reward / test rc | 原 F2P | 原 468P | 新 keyword P | 实际完整模块 |
|---|---|---|---|---|---|
| [noop](/Users/roger/Desktop/claude-code-verl-stage0h/runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask7138-formal-cpu-c-20261003-v1/remote/run/noop/eval_logs/evallog_replay-dask7138-formal-c_62ef44e8.eval.log) | 0 / 1 | 0/1 | 468/468 | 1/1 | 1 failed, 561 passed, 92 warnings；14.11s |
| [compatible_ravel](/Users/roger/Desktop/claude-code-verl-stage0h/runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask7138-formal-cpu-c-20261003-v1/remote/run/compatible_ravel/eval_logs/evallog_replay-dask7138-formal-c_c48d38d4.eval.log) | 1 / 0 | 1/1 | 468/468 | 1/1 | 562 passed, 92 warnings；14.37s |
| [source gold](/Users/roger/Desktop/claude-code-verl-stage0h/runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask7138-formal-cpu-c-20261003-v1/remote/run/gold/eval_logs/evallog_replay-dask7138-formal-c_8c70fd7d.eval.log) | 0 / 1 | 1/1 | 468/468 | 0/1 | 1 failed, 561 passed, 92 warnings；14.04s |

noop 在首个 `da.ravel(0)` 抛 `AttributeError: 'int' object has no attribute 'reshape'`；同一 F2P 的后续类型、list/tuple/nested 和非零负值断言没有在 noop 行执行。compatible 与 gold 均完整通过该 F2P。gold 唯一失败是新 `test_ravel_keyword_array` 的 `da.ravel(array=array)`，实际 `TypeError: ravel() got an unexpected keyword argument 'array'`；不是 array-like 转换失败，也不是旧 468P 回归。

[替代正对照](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_dask/tasks/dask__dask-7138/compatible_ravel.patch)只改 `routines.py`，保留 `def ravel(array)`，以 `asanyarray(array).reshape((-1,))` 转换输入。它通过标量、list、tuple、嵌套非零/负数、返回 Dask Array 类型、既有 `array=` 调用与所有旧参考；没有编辑测试。其 patch 原件 SHA `031783b6576e9410160e8ac515dbf49cedb7e5938facd0b9c9d7967d95d467e4` 与实际 candidate.patch 相等。gold patch SHA `d68ca41cd89d5607d0db853a76b4161314033cc70aeefaa59385e828bcf6644b` 与冻结 source gold 相等；它改名为 `array_like`，所以是本题 API 兼容性的负例。测试验收公开行为，不强制该正对照实现或零拷贝方式。

## 冻结身份与正式 consumer

R15 release manifest SHA `2b788d1ce84228a27894e04886ade347e91993f48ddc9bdeeb8f92de4aa92917`。远端 verify 原件记录 1305 文件匹配；我独立重算其中 36 个本题相关 release 资产（18 个题级资产、producer 及三份输出、14 个 consumer/契约代码），未声称本机重核整个 release 的其它题目。

冻结 producer SHA `9f56ab144ff9a6c8a811a406ab8f799270c5e7981a9fd388ca518165e822692e`；其 7138 单题 grading/public 对象与本轮实际 host/public view 完全相等。冻结 registry SHA `c6a9d747f0ed3a2ad49851ec524389786e703f8bc3572e65be26374126714d13`。原 1F/468P 保持，唯一追加 `test_ravel_keyword_array`；有效 test.patch 与 registry、host view 及当前题包相等，在内存应用到固定公开 base 测试后精确等于完整有效文件。

用冻结 R15 模块重新构造并 revalidate HostGradingView/RolloutTaskView/spec，实际所得与 binding/三份 ledger 相符：

- grading bundle：`sha256:ab58a76b4d8fa60add16e3217d0a2d8e10c9bff2667dfcdc67c61e1cddc0175a`；environment package：`sha256:bb77d20f8e384eaf09a31183d0c05bf2fa1590a94a65ffa8a7f1d260140ebb63`。
- public bundle：`sha256:02e3a996c88ecb46121a606d5c910986ad2d22ceec7b4663babaeaf3ad6b8c8b`；material identity：`sha256:3e94408ef02d1c2fb6c9113a5c86920325280b2a80962bf579d98087e283136e`。
- scripts digest：`sha256:6f61a742aacc681b4e07e2b1825cd1d8cba5450da1791e2aae7b9eee659c0d5b`；固定 local_build grader：`sha256:625b404c6c1c40da31df4edfea6052a10fbd30b7fb49d58072b6ee2b215fab13`，三行 `image_id_actual` 均相等，manifest digest 为 null。
- revision 文件 SHA `fb29e9e0f0a6457d974256b95678b753f9c700e7051c5fb3d8c2dfec61b767cc`；matrix `2e581e4a566d0b909796fa803f5722c166f5714798c041bcb9b2c1fdaf564586`；test.patch `2f3c5c539816149a06b6c460b5d79d6b3223f452cd5862bcdbac41faf76bc44a`；完整有效测试 `70c4e3bbadcdda5e78b624b7c51c49976485a1110f0952558c5c41b0f7231fae`。

三份 frozen artifact 的 canonical digest、public/image/head 锚、included paths 均与实际 ledger/projection 匹配。两份候选完整正文反推到同一 base `routines.py` 内容 SHA `659fc6c5789ffadc8f8a1755765ac0d9dd90c9359e420a4594c6329559938ff9`；noop 没有 delta。实际 prepared artifact SHA 与 manifest/binding 相等。run/status 的 verify、prepare、三次 grade 都 rc0。

config 引用不可变 input snapshot `aad49b96eaf19265`；本机给定 45 份读回没有独立 snapshot helper 清单/本体，因此不声称核算了缺席的远端 helper 字节。revision/matrix 输入 SHA、真实 consumer、实际候选 artifact/测试/评分身份已有上述原件绑定，未发现影响这三行 CPU 结论的身份错配。

## 非 root、安装、退出与清理

三份 ledger 的 candidate apply_user 均为 `agent/54321`，冻结 replay 按 rollout profile 数字 UID 执行补丁应用；candidate artifact 与实际输入一致。本轮没有另附 candidate `id -u`/prelaunch 输出，因此这部分是 ledger 加冻结执行路径的证据，不能用历史 actor 的 UID 探针冒充本轮的新探针。

三份 diagnostics 都有真实 prerequisite：固定隔离 Python 断言 `os.geteuid()==54322`，以 O_NOFOLLOW 打开 regular 离线 wheel，核精确 SHA `b090cdf5ed60bf4c45261be03239c2c1c22df034fbffe691abe93cd80cea01d8`，rc0 且打印 `RH2_DASK7138_OFFLINE_PREREQUISITE_OK=1`。冻结 manager 把 prerequisite/install/test 都送到 `54322`；root 负责可信 setup、工作区物化、权限、官方测试恢复和控制面保护，不能把 root setup 写成候选评分执行。

真实 recipe `dask7138-pytest744-fixed-v1` 要求候选安装离线 `pytest==7.4.4`，再执行原 `python -m pip install --no-deps -e .`。三份 eval 都记录成功安装，install rc0、failed_commands 空、未 skip、安装和测试起止标记齐全、segment_completed=true、log_partial=false；test rc 为 1/0/1，外层 exec rc 均0，失败均归 tests_failed，无 stage_error、infra_failure_detail 或 execution_failure_decision。

实际测试为 Linux Python3.8.15/pytest7.4.4/pluggy1.5；候选导入路径 `/testbed/dask` 是观测。三行都保留 **runner_integrity_changed=true**，前摘要 `0f3527…68f43`，后摘要 `a7b7f1…509cc`。冻结脚本覆盖 pytest/_pytest/pluggy 包路径和文件内容，排除 pyc/__pycache__；脚本在候选可写环境、候选身份下运行，属于诊断线索。安装日志与可信 recipe 表明 pytest7.4.4 被实际安装；摘要变化与该操作一致，但读回没有逐文件前后 diff，所以归因是推断。没有静默改成 false，也没有据此证明共享 runner 安全。

资源 policy 是2 CPU、4GiB、pids512、network deny；peak memory 观测为4096/3090.293/3470.758MB，`resource_facts=null`。这不是新的独立 cgroup 证明或内存余量保证；完整退出中无 OOM/infra 归因。各候选容器 removed=true/rm:ok；各 grade 的 manager_close created1/removed1、open containers/supply/cleanup failures 都空，regrade0、final_status rc0。作业原件已终止。

## 历史公开 actor、公开语义与后续范围

复用旧非作者审查，并重新核了 22 份相关公开 actor 原件的 SHA/大小。历史 actor 的 UID54321 实际 prelaunch/identity 输出、base HEAD `9bb586a6…`、Python3.8.15/numpy1.17.5/pytest7.4.4、Claude Code2.1.205、第一请求与原 public_hints+problem_statement 精确相等均成立。它执行公开 list 原例（rc1、list 缺 reshape）、公开旧 `array=` 调用（rc0）和原公开 routines 模块（560passed），退出与容器/网络/stub 清理完成。

历史 actor 镜像 `fdd298…0881` 与发布 actor 资产同锚；source manifest `91df52…7736` / source config `8da379…ef3e` 与本轮固定 recipe 来源相同。本轮 replay 在固定 grader625 暂存候选，不是重跑历史 actor；角色镜像必须区分。这些材料证明同一来源/配方关系，不证明历史 Dockerfile 层或旧 wheel 字节被原样复刻。历史公开 actor 是真实 CC 配合脚本 stub 的5个请求，没有模型推理；本轮也没有模型解题。

旧 pip check rc1 的三项冲突仍保留：distributed2021.7.2 需要 dask2021.07.2，实际2021.1.1+6；zarr2.15 需要 numpy>=1.20，实际1.17.5；chest0.2.3 平台限制。不能从本次 routines 模块通过推广为整个环境依赖兼容。

原问题正文已经给转换后 reshape 的修法提示（含 `asasanyarray` 原拼写和 `array_like` 改名建议），本轮未新增提示或改题面。正对照满足 array-like 目标并保留公开旧签名；gold 因改名成为负例。后续基座探针必须披露题面已有引导，不能把本 CPU 矩阵解释成模型能力。

接探针仍需实际目标 GPU/rollout 部署的镜像/config/激活/profile 与固定 release/public/material 绑定，以及真实模型推理轨迹、frozen patch 和正式评分的关联原件。历史公开诊断不能替代这些证据。三份 ledger 的 env_qualification 仍为 absent；训练消费与资格沿主链已有授权办理，本报告不另授训练 reward 或环境资格，也不新增准入闸门。
