# D6 两题真实 actor 原件独立复核

2026-09-29。**公开开发、真实 CC、静止屏障、冻结与纯材料绑定均有真实证据；最终 actor→fresh grader 接缝不通过，F1已由10424真实正式评分复现并独立核实。** 六行 CPU 材料矩阵的独立通过结论保持，不能把这个局部成功扩写为 actor 冻结工件已经能完成正式评分。新增反例原件与raw census重算见 [F1真实证据](d6_actor_to_grader_failure_review.md)。

本报告独立读取本地 `runs/category2_repair_20260929/remote/d6/actor_acceptance_v1/` 两题原件，逐文件重算各28文件manifest，核完整请求、轨迹、三份命令全文、baseline/frozen/projection及清理。未执行远端、Docker、模型或新评分；未修改生产代码。工具入口审查见 [runner审查](d6_actor_runner_review.md)，评分原件见 [六行CPU审查](d6_cpu_evidence_review.md)。

## F1：actor 与 fresh grader 的 Git 排除区初态不一致（阻塞，待处置）

**当前行为／违反不变量。** 正式 actor 在 baseline 前执行 Git sanitize，删除ref、reflog、无用对象并repack；replay候选与fresh grader初态不执行同一步骤。两题实际actor baseline与已完成CPU noop baseline逐字段比较，scoreable entries、policy、task/public/image/base/head全部相同，**只有 `excluded_census_digest` 不同**。该字段实际参与完整baseline digest。正式manager的fresh重建检查要求完整digest一致，所以当前actor工件不能由已验相同镜像初态重建，会在候选应用及测试前报 `baseline_digest_mismatch`。

**证据／位置。** 以下行号均来自冻结树 `runs/category2_repair_20260929/frozen_d6_v1/code_v1/`：

- `rh2/src/repoharness2/adapters/slime/generate.py:4939` 在 `_materialize_rollout_sandbox` 内执行 `run_git_sanitize`；`generate.py:3895` 先等待该物化，再在3917行生成baseline。因此actor工具的sanitize→baseline顺序与真实生产一致，不能靠移掉工具sanitize消除该差异。
- `adapters/slime/replay_grade.py:336` 起候选后只做trusted init、物化probe，351行直接baseline，没有Git sanitize。`grading/manager.py:2599` 只做grader trusted init；2880行的 `_clean_checkout` 对此镜像模式只做血缘probe，没有sanitize。
- 两题均为 `baseline_policy_v2`，排除命名空间为 `.git/`、`.harness/`。`adapters/slime/baseline_census.py:90` 对排除区输出普通文件的路径清单，247行排序后hash；不是源码内容hash，也不是可再生缓存计数。`.pytest_cache`／`__pycache__`另行整体省略，不进这个摘要。
- `contracts/baseline_manifest.py:225` 的 `compute_baseline_manifest_digest` 序列化全部manifest字段，未排除 `excluded_census_digest`。`grading/manager.py:3108` 重算原baseline和fresh重建baseline，3110行不等即抛 `BaselineIntegrityError("baseline_digest_mismatch")`；正式 `grade` 在2027行必经该检查。
- actor工具只在 `_verify_frozen_delta_binding` 中验工件内自洽和task/base/material关联，完全未调用 `_verify_baseline_rebuild`。其 `binding_checker_close.containers_created_total=0` 也清楚证明没有fresh grader；自动通过标记不能覆盖这个检查半区。

| 题目 | 真实actor baseline digest | 已完成CPU noop baseline digest |
| --- | --- | --- |
| 10424 | `sha256:e9d53030cc4462454733473159ddbc4c9044150847e9c3ff2039e3f865f8bfb7` | `sha256:cac65636ebf441ae4cb4900f6f80ef6614f2d8a568a13e31227712cf01d37c03` |
| 17071 | `sha256:d6f2ffc85b9caf4e2fbe0031e0e41a66afd0bca695b44e372c5a4be1f41378b0` | `sha256:e9b9dfcb06d1b62f36d64dd164ce7af3ff1d09786aa7755fed99ce25e5404c9a` |

对应排除区摘要，10424为actor `e782008a…`／replay `f94ee701…`，17071为actor `f75f7928…`／replay `f017be20…`。完整值可由下面只读探针重算列出。CPU noop评分已成功，结合生产重建硬相等条件，证明该批fresh grader通过的是replay初态；这构成实际数据上的接缝反例，并非仅构造不合法内存对象。当前未保留原始排除区路径清单，不能进一步逐路径断言差异只是哪几个文件；Git sanitize的删除与repack行为、两侧调用顺序差异均已直接核实。

**影响／分期／归属。** P1，首片正式actor接缝核销和两题转类前阻塞。它不是D6新增参考、parser或reward错误，而是共同actor/replay/grader初态归一化问题，可能早于D6；不能扩大说六行CPU无效，也不能因其是旧问题就忽略当前真实候选无法交付评分。实现归属由主线程与A线协调，本审查未动他人的 `generate` 或安全边界。

**最窄复现。** 从仓库根运行：

```bash
rh2/.venv/bin/python -B docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/reviews/d6_actor_evidence_probe.py
```

该程序只读实际工件，在核原始actor子链后输出两题唯一差异及完整摘要；不启动评分。首次审查时远端单条反例pending；随后主线程用已保存10424真实actor noop工件送fresh grader，已真实报同一 `baseline_digest_mismatch`、退出20并清理。独立原始census解析确认fresh摘要恰等于已完成replay的摘要，见新增报告；保留先前判断的证据顺序，不改任何原件。

**建议与修复验收。** 先保留这次成功子链和失败接缝证据。优先评估让受信候选前准备／fresh grader重建与正式actor使用同源的Git sanitize，而不是删掉actor既有防泄漏步骤。不能静默剔除原契约digest字段、覆写baseline或复用replay工件假称actor工件。修复后需新冻结身份、真实actor工件→fresh grader在不改原件的情况下越过完整baseline重建，并完成预期noop评分、材料关联与本run清理；两题的相应证据闭合后才可消除此阻塞。无需先机械重跑无关测试矩阵。

## 已核实的真实子链

两个run按顺序完成：10424为08:34:16–08:35:03 UTC，17071为08:36:06–08:36:52 UTC。runner SHA为 `96eabc4dc4d0a419c0f263c9a20bb4d97e8b5535fd4ca83dee7f6ef3b4fc9a8a`，生产清单SHA为 `43186d0d85f1eb4e7d28e51b92a9a2c82bf1d4ff178d785d8d4846795300460e`，与审过版本一致。

| 项目 | 10424 | 17071 |
| --- | --- | --- |
| CC及结果 | 2.1.205，真实exec退出0，result success | 同左 |
| 原始轨迹 | 19098字节，SHA `74a04a22e35615fc34f2dee0747b881fa3f2c36018d6fbb66f28feeade8e4b89` | 18994字节，SHA `5d1beac6dbd5b8b9708e7fa7e2a0c4024a0f4adb5c6012039c233eb1da4bd7ca` |
| 身份／模块／公开测试全文 | 530／480／778字节，全部rc0且SHA匹配 | 530／503／689字节，全部rc0且SHA匹配 |
| 公开case真实收集 | 5165项中2 selected，2 passed，0.87秒 | 6872项中1 selected，1 passed，0.90秒 |
| 冻结工件 | entries空，excluded_pathset_changed=false | 同左 |
| 本run清理 | actor移除0、relay无失败、容器/网络查询0且空、attempt释放 | 同左 |

两题原始CC请求均只有原公开题面、正常系统/工具说明、三个固定Bash命令及结束状态。每题四个模型请求与四个message_start完全对应；三个tool_use逐字匹配工具源码生成的公开命令，三个tool_result rc0，最终success；Engine inspect同时记录Running=false/ExitCode=0，stderr完整且0字节。公开prompt分别652／1745字节，与prepared源逐字一致。没有在请求中发现私有test patch、gold/C1或私有评分字段。桩usage造成CC输出名义costUSD，不能据此把此本地桩实验说成真实付费模型调用。

实际身份均UID/GID54321、`/testbed`、`HOME=/home/agent`、conda testbed、解释器 `/opt/miniconda3/envs/testbed/bin/python`。`/rh2`、激活脚本及公开bundle为root属主且agent不可写。prelaunch记录无宿主mount、无有效能力、no-new-privileges、2CPU/4GiB、仅relay连通、外部和upstream直连均拒绝。派生镜像ID、父层及实际容器image一致。

实际模块从 `/testbed/mypy/*.py` 导入，摘要与本次baseline entries相等。10424检查checker/meet，新公开文件SHA `709c22b2…`；17071先正常build初始化后检查checker/typetraverser，文件SHA `d189254a…`。真实公开case恰等于新增参考集合且全部PASSED，未执行私有F2P补丁。开发测试用有界 `-n0`，不改变CPU评分的正式命令。

桩退出0、唯一relay关闭无错误后，生产屏障执行终止检查：两题均一次观察residual0、未超时，双读census稳定。`pkill_status=1` 配合residual0表示当时已无目标进程，不是终止失败。冻结分别关联physical attempt `miles_g0_m0#p1-c0be078b`／`miles_g0_m0#p1-179284ca`，独立重算工件摘要为 `sha256:cb02239f6c7b270a2342ae96a464778b285f7b1fdf67ab5ad0dc14c8bf448b4e`／`sha256:781a85d50d1ca2ebe620a2903927bcf5cc68af58dc2217eee4e6cb3d850b58a0`，projection与baseline锚一致。

独立用本次CPU v1 prepared重新构建face、绑定原dispatch并resolve，再重建grading spec、projection、classification与manager纯绑定，均通过；两个材料身份与六行矩阵一致。错误环境回显被 `assignment_echo_mismatch` 拒绝，释放后不能再次解析。私有分区仍为 `not_evaluated`，没有把未评分的actor工件写成reward。两题的公开／冻结子链结论因此成立，但不会绕过F1。

## 结论范围

当前一项阻塞，owner为主线程协调A线，gate为实际actor冻结工件到fresh grader闭合；真实失败已独立核实，修复及新版本验证待完成。直连桩关闭只证明这个独立拓扑的会话停止，不证明训练capture/队列/orchestrator排空，更不是miles训练验收。既有CPU矩阵通过、工具可执行和actor最终接缝通过必须分开记录。
