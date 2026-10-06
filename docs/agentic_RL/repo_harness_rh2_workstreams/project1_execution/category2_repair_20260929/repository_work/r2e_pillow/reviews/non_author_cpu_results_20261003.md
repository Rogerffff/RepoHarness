# Pillow：题级 CPU 原件与现有模型结果非作者复核

2026-10-03。**2d01、3a61、a682 CPU：PASS，没有 CPU 阻断；2d01 Qwen3.6／Coder 各 a1 现有结果窄核：PASS，正式 reward 均为 0、60/62，不存在本题评分或环境阻断。** 两份候选都保留了标签，但未修复图像内容往返。结果可消费不等于修复通过，也不据每模型一次结果推断整体能力或题目难度。CPU 验收、确定性 CC 桩对照与真实模型求解分别记录；此次只审已有模型原件，未新增运行或训练／留出资格。

## 复核身份、范围与方法

核查者不是本轮修订、装配或 CPU 运行的作者。启动时只收到题主的本次核查请求；可访问公开与私有材料，随后又收到两题在途状态、输入／结果归档及现有 Qwen3.6、Coder 各 a1 的结果指针。复核模型结果前已接触私有 CPU 正确解与隐藏材料，因此**不是 fresh 公开读者**，也不能将私有正确解视为模型产物。接续已有静态语义意见，只核本轮结果身份、逐参考结果、退出、真实阶段和清理；未机械重审题义。依据 [当前流程](../../../remaining_workflow_20261002.md) 与 [仓库分工](../../../repository_work_packages_20261002.md)。

仅本地读取原件、计算 SHA256、按固定 release 的生产纯函数 parser 重新解析日志、比较命令／轨迹／回读记录。未启动远端、Docker、模型或 Pillow 实验，未安装依赖，未改作者材料；本文件是唯一写入路径。作者验收 JSON 与 `static_checks.json` 仅用作导航，并逐项回到原件。

**暂停 checkpoint（2026-10-03）：** 收到用户全局暂停指令后停止新增核查与接续。保存边界前，三题 CPU 与两份 2d01 模型结果的上述窄核已完成；没有将暂停后未核事项改为 PASS。checkpoint 权重身份、长上下文／最大输出全链生效、Coder 排除面变化的具体路径，以及后续 3a61/a682 GPU 结果不在已验证范围；各节已有边界继续保留。等待用户恢复，不启动新运行或修改版本快照。

## 2d01：版本、材料与执行身份

完整题 ID：`pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96`。

原件根 `runs/category2_repair_20260929/r2e_pillow_cpu_b_20261003/`，下文称 CPU 根；其中 `2d01_cpu_core_v1/` 称 core。固定 release 为 `runs/category2_repair_20260929/releases_20261003/r2e_064_065_candidate_v1/`，运行版本 `cat2-cpu-r2e064065-swe5-20261003-v1`。已完成证据仍绑定首版，不因后续第五版自动改绑。

| 核查项 | 独立结果与原件 |
| --- | --- |
| core 清单 | `snapshot_manifest.json` SHA256 `25ea0718e60f7a6eaaf0d68d4cb611e669abed2ec2ef18f1acbddf1b88447c43`；123/123 个成员 SHA 与大小匹配，清单 omitted 为空。 |
| 固定 release | `manifest.json` SHA256 `282021962a92b510f077385660ac56acedcd7fac1d97e63db3baa98e4dcc057f`；794/794 个成员 SHA 与大小匹配。`release_binding_v1.json` 的三份 runner SHA 均与冻结文件一致，作业命令确实指向该 release。 |
| 输入包 | `cpu_input_manifest_v2.json` SHA256 `73591abdd66d2bfb72189043f766dbf05ef9e49d14a9262afdb19c4f8d764353`；逐项读取 `cpu_inputs_v2.tar`，38/38 个条目 SHA 匹配，包内清单与原件逐字相同。 |
| 正式材料 | prepared 私有任务面只列 `r2e-mr-063`；隐藏 `test_1.py` SHA256 `4beac7f3…` 与 release 修订单、构建 context 相同。三项文件摘要重建隐藏树得到 `bd62b707f7ef41bb21dcb4773e8206970773511eb9c819e7ae0adeb624f8fada`。入口原文重算得到 `8285765f…`，与构建及真实评分日志一致。 |
| 期望表 | 从 `prepared/2d01-release-v1/private/host_grading_views.jsonl` 读取完整原文，重算 SHA256 `28da3c259354012c9989afbeb731f9eea95a7913ac43ff8fd8a2a41ebce9df15`；归一化后 62 键。`test_closed_file`、`test_context_manager` 的 FAILED 期望保留，其余 60 键期望 PASSED。 |
| 镜像与配方 | 来源 digest `9af0401d…`；CPU-b 实际派生 ID `344103dc…`，在 facts、overlay、评分账本和三次 actor 的 inspect 中一致。配方 `r2e_derive_v1+material_v2+sysconfig_v1`；从构建 context 重算组合 SHA256 `54e35b094ecff3dffe724f34443a928519da09480152c21d60b44752b111845a`。 |
| 构建完整性 | `derived/pillow2d01-build-20261002T171740Z/…/facts.json` 的 21 项检查全部为真、failures 为空。另直接比较两份 `integrity_{base,derived}.txt`：1473 个工作树文件、3221 个 venv 非 bin 文件、17 个 bin 载荷及 git 四项摘要相同；差异限于记录的解释器 symlink 与 pyvenv home 搬迁。隐藏目录 root:root/700，agent/grader 读取被拒；两身份解释器可执行。 |

`2d01_preparation_receipt.json` 与 core 中 prepared 摘要／gold 原件一致；gold `190a8e47712345194ab36111eebae27a7229d79c16db5bb394e158ba596c4702` 逐字等于固定 release 的 validation 面。该补丁只含 `src/PIL/TiffImagePlugin.py`。

## 2d01：新正式评分按原日志重建

两项均来自 core 的 `controls/pillow2d01-controls-20261002T172853Z/`。使用首版 `rh2/src/repoharness2/envpack/r2e_parsers.py` 的 `parse_log_pytest` 与 `normalize_status_map` 读取真实 eval log，逐键比较期望和观测的并集。

| 候选 | 独立匹配／总数 | 实际日志摘要 | 判分 |
| --- | ---: | --- | --- |
| gold | 62/62 | `gold/logs/evallog_replay-pillow2d01-contro_32345e86.eval.log`，SHA256 `6e1215c54c2d1e0e97eec312144e6b192a6cdc2991b04e8cf63c0ec50942f00c`；60 passed、2 failed、2 skipped。 | reward 1；两个 FAILED 均为期望保留的旧 `pytest.warns(None)` 错误。 |
| noop | 60/62 | `noop/logs/evallog_replay-pillow2d01-contro_5e7c6fbe.eval.log`，SHA256 `8e81fad0ac3725984a5311a990975d7a32cd47cd16bf19ee041b23c62467c673`；58 passed、4 failed、2 skipped。 | reward 0；仅 `TestFileTiff.test_photometric[1]` 与 `[L]` 从期望 PASSED 变为 FAILED。 |

两份日志的 SHA 与各自 ledger 相同，期望／观测键集合完全相等，缺失和额外键均为 0。两个既定 FAILED 键不是缺席或跳过；64 个 collected items 中的两个历史 skip 不进入这张 62 键状态表。**reward 1 不等于所有私有测试 PASSED。**

真实阶段证据完整：候选 artifact 的 `stage.json` 记录完成 projection、stage_error 为空；随后日志分别只有一对 Start/End Test Output、一对测试起止时间和 `RH2_TEST_RC=1`。ledger 记 segment_completed=true、exec_exit_code=0、log.partial=false；replay driver 退出 0。测试 rc=1 与期望状态表判分并不冲突，不能据此改成基础设施失败。

`gold/driver.stdout`、`noop/driver.stdout` 的最终 footer 各记 created=removed=1、containers_open/supply_open/cleanup_failures 为空、final_status.exit_code=0；候选 ledger 的 cleanup.removed=true。CPU 根 `pillow2d01-controls-20261002T172853Z_final_readback.json` 与 core 对应记录相符。未见截断、deadline、stage error、残留容器或待完成评分。

## 2d01：真实 CC 开发返回与私有正确解

| 作业 | 独立核对结果 |
| --- | --- |
| `pillow2d01-actorbase-20261002T172129Z` | runtime_v1 宿主导入报 `No module named 'torch'`；supervisor rc=3，trajectory_bytes=0、stub messages=0，九条命令全部未运行。属于 CC 工具运行前的基础设施失败，不能计模型失败或 0 分。容器、网络、relay 与 stub 均已清理。 |
| `pillow2d01-actorbase-20261002T173349Z` | runtime_cpu_v2；真实 CC 2.1.205，九次 Bash 调用与九次 tool_result 一一关联；十次 message_start 与十份 stub request 相符；最终 result=success，harness／supervisor rc=0，stderr 空，轨迹 63133 字节与记录一致。 |
| `pillow2d01-actorpositive-20261002T173710Z` | 同 runtime_cpu_v2 与 CC；九次 Bash 和九次实际返回、十次 request；最终 success，harness／supervisor rc=0，stderr 空，轨迹 62615 字节与记录一致。私有正对照 stage 记录 UID 54321、固定 gold SHA、host stdin、目标 TIFF 源码、apply rc=0。 |

原件为 core `actor/<job>/attempt.json`、`harness/trajectory.jsonl`、`stub_script.json`、`stub/stub_log.json`、`stub/requests/`、`captures/*.out`、`prelaunch.json`、`activation_check.json` 与 `post_run_facts_root.txt`；CPU 根三个 `<job>_readback.json` 中的 attempt 与 core 逐结构相同，SHA 与[作者验收清单](../cpu_2d01_acceptance_v1.json)列值匹配。

对成功两次分别独立核对全部九个 rc：preflight、身份、可见面、import、默认保存、公开兼容、压缩观察均为 0；`L`／`1` 原例在 base 为 1，在正确解为 0。对应真实输出的标签由 1 变为 0，pixel00 保持 0；压缩观察也由 tag262=1 变为 0。默认保存输出均为 `L 1 77 | 1 1 255 | RGB 2 (1, 2, 3)`。

13 项入口检查不仅核作者布尔值：实际工具输出确认 `/testbed/.venv/bin/python`、UID 54321、BASH_ENV 写入被拒及三项 preflight；轨迹／requests 确认调用、返回、最终事件与完整字节；root 后检确认 harness/run marker 不在容器、agent 进程为 0；inspect 确认实际派生 image ID。两次解释器 Python 3.9.21、PIL 8.4.0.dev0、TIFF 模块及 `_imaging` 扩展均来自 `/testbed/src/PIL`，libtiff 4.3.0 可用、pytest 8.3.4。

观察到一个有解释的字节差异：CC 发出的七条 Bash 命令删去内层重复 `cd /testbed &&`。逐命令比较证明除此之外载荷及 input 均不变；外层 `cd /testbed` 和 init cwd 仍保留。被审兼容 heredoc 逐字保持，未用“命令完全相同”掩盖该差异。

两份公开兼容 capture 都明确为 **82 passed、2 skipped**，skip 为额外图片未安装和 Windows only。原 TIFF SHA `93f9c839…`、兼容副本 SHA `b02fd092…` 与冻结文件及已有[非作者静态意见](non_author_2d01_compat_review_20261003.md)一致。构建完整性 dump 中公开 `Tests/helper.py` SHA `6e00e34c…` 与原件相同；兼容 helper 只写临时副本，finally 核原 TIFF 不变并删除副本，真实 rc=0、后检只有 `Tests` 目录 mtime 变化而无残留临时文件。隐藏材料及两个 FAILED 期望没有被公开兼容工具替换。

私有装配与已有[窄核](non_author_2d01_positive_wrapper_review_20261003.md)绑定的 `7d78e50e…` 相同。代码在 driver 前显式要求实际 `id -u=54321`，以 `user="agent"` 与可信 env 分别执行 `git apply --check -`、`git apply -`；错误阻止 CC 继续。真实 stage、单文件 gold 原件、正对照后检仅新增 TIFF 源码修改与实际导入结果共同支持该身份。补丁未进入 stub 命令／solver 消息。正确解是私有开发对照，不能称为模型生成的修复。

三次 actor cleanup 均记 container_rm=0、stub_rc=0，网络／relay 失败、带标签容器／网络与 residual_after_force 全为空；成功轨迹完整返回后再清理。这里的“无残留”指本次清理记录和后检范围，没有以计划代替观察。

## 2d01：历史复用边界与后续用途

直接读取 `runs/r2e_lifecycle_20260929/codex_status_check_20260929_1020/formal_v11/` 的 `ledger_gold/noop/s1…s7.jsonl` 与对应九份 eval log，并核对应候选补丁 SHA。固定生产 parser 重算结果为 gold、C1、C1FO2 各 62/62；noop、D、C3、C2、A、B 各 60/62，负对照差异仍为两项 photometric。九份日志 SHA 全匹配、完整测试段、非 partial、cleanup.removed=true。日志隐藏树／入口、配方 SHA、PIL 导入身份与本轮一致。

因此可复用未变评分材料的九方判别结果。它们来自历史派生 ID `87d6e9a0…`，不能当 CPU-b 新 ID；本轮新 gold/noop 和真实 actor 补齐新宿主关键身份与公开兼容验证。此次没有声称九方全部在新宿主重新运行，也没有证明将来任何镜像或材料变更都可复用。

[探针请求](../probe_request_2d01_v1.json)独立 SHA256 为 `3a42d652e11cc86769c31bed9efea035d2310f730eb70c73d5201316a66070cc`；其中 registry、pins、隐藏文件、facts、gold、公开开发说明与 CPU acceptance 的逐文件 SHA 全匹配。请求明确普通诊断用途、`probe-wide-v1` 两模型各先一次、私有控制不算模型成绩；公开说明 SHA `ef6cd806…` 符合限定交付。CPU 复核结束时，GPU 宿主实际镜像／代码身份、真实消息交付与预算尚待执行者核查；接续收到的 Qwen3.6、Coder 各 a1 原件另见下两节。本复核不从同仓答案包含关系推导训练／留出资格。

**停止条件已满足：** 2d01 的必要 CPU 结果核查结束，没有要求重复实验或重跑不变九方矩阵。收到真实模型轨迹后，题主继续核候选行为与逐键评分；若身份或材料变化，只复核受影响项。

## 2d01：Qwen3.6 a1 已有模型结果窄核

**结果核查 PASS，候选 reward 0；没有本题评分或 Pillow 环境阻断。** 本节只核 `gpu1003-pillow2d01-qwen36-a1` 这一轮现有原件，不代表修复通过，不推断题目整体难度或模型总体能力。Coder 首轮在下节分开核查，本节不作两模型比较。没有重跑同机制候选、续模型或修改请求。

原件根为 `runs/ordinary_gpu_probe_20261002/remote/queue_v5/results/gpu1003-pillow2d01-qwen36-a1/`，下文称 GPU 结果根。公开／私有 prepared 在同一 remote 根的 `prepared_pillow2d01_v1/`；实际网关记录在 `services_v2/qwen36/gateway/gpu1003-pillow2d01-qwen36-a1/`，adapter 记录在 `services_v1/qwen36/adapter/gpu1003-pillow2d01-qwen36-a1.turns.jsonl`。这些服务版本按本轮真实路径核对，没有用后续版本替代历史证据。作者初读、执行者已有报告和模型最终回答均未作唯一证据。

| 核查项 | 独立原件结果 |
| --- | --- |
| 请求与入口 | `queue_v5/requests/<job>.json` SHA256 `f9a8d36320561695d8f8874f7fd096246a3ced593e4cd7dca9974ec840771cb4` 与 receipt 相同；8 项输入摘要全部与实际文件相符。普通入口 SHA `d5132780…` 与 `runtime_stage/rh2/experiments/ordinary_gpu_probe_20261002/entry.py` 相符；receipt 的任务、模型、参数和 exit=0 与结果一致。 |
| GPU 实际身份 | 实际镜像 `sha256:a473288fadb9440c5ad95c0bd7035dd6ea9e185eb20fd0f21dfe890da0dfee93` 在 prelaunch inspect、attempt、baseline、FrozenPatch 和 grader diagnostics 中一致；不是 CPU-b 的 `344103dc…`。GPU 派生 facts 的 21 项检查通过；另核两份 4730 行 raw integrity，仅解释器 symlink 与 pyvenv home 搬迁有差异。配方仍为 `54e35b09…`，基线 HEAD 为 `5db0969f6f9873bd15aededab9ef413f043f1ea4`。 |
| 同版评分材料 | GPU `private/host_grading_views.jsonl` SHA256 `3d71a627…` 与 CPU 正式任务面逐字一致；仍为 `r2e-mr-063`、隐藏 `test_1.py` `4beac7f3…`、hidden tree `bd62b707…`、入口 `8285765f…`、62 键期望 `28da3c25…`。实际 trusted setup 也记录该树／入口、restore=3、expected/actual=4、absent=0、apply=0。 |
| 求解前基线 | `attempt/frozen/baseline_manifest.json` canonical digest 重算为 `sha256:1e637a9b2ca207cfef88c25daad21af6846a144729cd8cd82e5ea09c836fc535`。`baseline.tar` SHA256 `c9ec6693…`，1466/1466 个条目的路径、对象类型、Git 执行位模式及内容摘要匹配，无额外条目。actor 与 grader 的完整 census 逐字一致；其中 3390 个排除路径重算得 `c83788a4…`。缓存计数与排除 namespace 按既定 policy 保留。 |
| 原 FrozenPatch | 从 JSON canonical 形态重算 `sha256:ca8cb133c0677e3fc942c084fc14f330c6600e9c459172ebc1d5eda04072bc76`；唯一条目为 `src/PIL/TiffImagePlugin.py` 的 regular modify、100644。base64 解码内容 SHA256 `4bca3a3d4e86d4512890e9446a5678004c61cc164d78c04f27f68f1d4384c5c9` 相符。projection 与 report 的实际应用子集 digest 均为 `5c4dcaef…`；无测试修改、非法路径或排除面变更。 |
| 审阅 diff | `attempt/candidate/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96.diff` 为 564 字节、SHA256 `5daef678c3cf7baf4961f764ba41b87ba07d371c9e00bca75f31b8c6e39a78a3`。独立由归档旧源码与 Frozen 新源码重建 diff、Git blob ID 均相同；只有一次 guard 替换。评分 source 明确为 `original_frozen_patch`，未用重建 diff 替代评分输入。 |
| 实际公开消息 | prepared 原 prompt SHA256 `73ac793c…` 完整保留；solver prompt 是该原文加限定说明与公开 brief `ef6cd806…`，只省略 brief 文件末尾换行。`solver_prompt.txt`、`attempt/prompt.txt` 和 preflight prompt SHA256 均为 `784cd77def70d0f34b26f000652cb0b2a8003a8f9e759052beb2775bd2ec80c7`；第一个真实网关请求的用户文本块逐字等于该 solver prompt。没有把私有 gold 或隐藏断言加入初始公开消息。 |

实际候选只将 `_save` 的无条件赋值改为：

```python
if PHOTOMETRIC_INTERPRETATION not in ifd:
    ifd[PHOTOMETRIC_INTERPRETATION] = photo
```

它确实保存了用户传入的标签 0，但没有转换写出样本。原源码 `SAVE_INFO` 的 `'1'`／`'L'` rawmode 未变；读出 tag 0 的 `OPEN_INFO` 仍分别选 `1;I`／`L;I`。因此标签保持与图像内容往返是两个不同观察。这里不以“格式非法”或“标签与数据矛盾”为拒绝依据。

从 `grading/eval_logs/evallog_gpu1003-pillow2d01-qwen3_66eae539.eval.log` 重新解析完整状态表。该原件为 13543 字节、SHA256 `04511904b518d2961b154d111fb79f58bddcadb5d80353a4c4d6f3c19475fa8d`，与 report 引用一致；本轮 parser 与已固定 CPU release 的生产 parser 逐字相同。

| 参考范围 | 期望与实际 | 匹配数 |
| --- | --- | ---: |
| `test_closed_file`、`test_context_manager` | FAILED → FAILED，旧 `pytest.warns(None)` 的 TypeError | 2/2 |
| `test_photometric[1]`、`test_photometric[L]` | PASSED → FAILED；两项都已通过标签为 0 和保存后源图不变的断言，均在 `test_1.py:460` 的 `assert_image_equal(original, reloaded)` 报 `got different content` | 0/2 |
| 其余参考键 | PASSED → PASSED | 58/58 |

总计 **60/62，missing/extra 均为 0**。真实 pytest 摘要为 **58 passed、4 failed、2 skipped**；两个历史 skip 不属于这张 62 键表，两个既定 FAILED 没有额外扣分。日志只有一对开始／结束标记和时间，test rc=1；外层 candidate exec rc=0、segment_completed=true、partial=false。report/status/result 三份报告相等，正式 unresolved/tests_failed/reward=0 没有被转换为 infra failure。完整结束和 rc=1 并不冲突。

这一失败机制在模型运行前已登记并审过：旧 [r2 非作者意见](../../../../r2e_lifecycle_20260929/codex_reviews/review_revision_pillow_2d01_r2.md) 明确 C2 在同一 460 行往返断言失败，[修订方案](../../../../r2e_lifecycle_20260929/results/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/revision_plan.md) 记录其在修订前原 457 行也因内容往返失败。不是看到模型 0 后添加了新断言；此次未要求再跑 C2。沿用方案的 P4：可将该样本登记为“疑似规格争议的待复核样本”，但原始 reward 0 保留；不机械推翻已有保存／往返语义意见。

实际 CC 轨迹 `attempt/harness/trajectory.jsonl` 为 276740 字节、SHA256 `90be374c…`，与 `attempt/trajectory.jsonl` 逐字相同；25 个 tool_use 各有唯一对应 tool_result，包含 21 Bash、3 Read、1 Edit。CC 2.1.205 完整最终 result=success、is_error=false、terminal_reason=completed，harness exit=0，stderr 为空。这个 success 仅证明求解返回，不能代替修复验收。

公开环境实际返回 Python 3.9.21、`/testbed/.venv/bin/python`、PIL 8.4.0.dev0、`/testbed/src/PIL` 与 `_imaging`、libtiff 4.3.0、pytest 8.3.4；UID 54321／激活／preflight 有真实原件，pip freeze 前后逐字不变。第十次工具实际执行的兼容 heredoc 逐字等于公开 helper（SHA256 `04830593…`），输出原 TIFF `93f9c839…`、临时副本 `b02fd092…`，**82 passed、2 skipped**，finally 删除副本并核原文件不变。其他 metadata／libtiff 现有测试也有真实 21／1／22 passed 返回。两次不存在的节点 `test_save_with_tiffinfo` 与 `test_save_seek` 都报 not found/no tests ran，后来恢复现有节点；它们不能计测试通过，即使管道末端 `tail` 让工具返回非错误。

另两次 tool_result.is_error 如实保留：一次是额外 RGB 临时 TIFF 的 `UnidentifiedImageError`，一次是 grep 无匹配。这些没有使 harness 截断，不能把该轨迹称为工具零错误。模型最后写“All tests pass”，且将 tag 0 误称 MINISBLACK；验收依据是上面的真实日志与现有源码，tag 0 的语义是 WhiteIsZero。

预算配置为 `probe-wide-v1`：context 196608、max_new_tokens 65536、turns 240、wall 10800 秒、网关请求 1024、首响应 1800 秒。真实 26 个请求全部 `max_tokens=65536`，model_sent=`Qwen3.6-35B-A3B`；26 个响应都是 200、attempt=1、无 stream_error、各有完整 message_stop，25 个 tool_use 之后一个 end_turn。adapter／网关／CC 的累计 input 342549、output 6399 相同；单次最大 input 19189、output 931，solve 49.725 秒、正式评分 50.193 秒，没有长度 stop、预算耗尽或上下文压缩。

清理证据来自原件而非新远端检查：quiescence 记录 agent 进程为 0、工作树两次摘要稳定，barrier_stop residual=0、未超时；gateway session 撤销并排空 active_requests=0，session_close 与 attempt 一致。actor container_rm=0、left 为空、网络／relay 失败和带标签容器／网络列表为空；grading manager created=removed=1、containers_open/supply_open/cleanup_failures 全空，cleanup_ok=true。

**必要限制：** 服务读回仍为 config_only、checkpoint_identity_verified=false；本轮证据确认实际请求和短上下文完整返回，未确认权重 checkpoint 摘要或 196K 长 prefill／最大输出的全链生效。CC 元数据 maxOutputTokens=32000 与实际每请求 65536 不一致，不能据它声称发生了 32K 截断。另有可由源码解释的记录标签缺口：`attempt.shared_entry` 被普通入口覆盖为 `r2e_solve_attempt.py`，但保留的 `shared_entry_sha256=00ca8499…` 实际属于 `base_probe_20260922/solve_attempt.py`；R2E 包装器的冻结源码实际为 `10a71cca…`。普通入口 `d5132780…` 的更新语句未同步改该字段，因此不能把这组路径/SHA 说成直接匹配。这个字段缺口不改变已逐字核实的 FrozenPatch、基线、评分材料和日志，也不构成本题 0 分的环境／评分阻断；不在本复核中修改执行者材料。

## 2d01：Coder a1 已有模型结果窄核

**结果核查 PASS，正式 reward 0、60/62；没有本题评分或 Pillow 环境阻断。** 此处核 `gpu1003-pillow2d01-coder-a1` 的实际原 FrozenPatch；候选未修复往返，不把模型最后“成功修复／所有 TIFF 测试通过”的陈述作验收。已接触私有 CPU 材料的身份披露同前，不是 fresh 公开读者。

原件根 `runs/ordinary_gpu_probe_20261002/remote/queue_v7/results/gpu1003-pillow2d01-coder-a1/`。实际配置 `config_v7`、执行代码仍为 `code_v3`；同 ID 网关和 adapter 都在 `services_v5/coder/`。queue 请求 SHA256 `2fed0ef2…` 与 receipt 相同，7 项请求输入 SHA 全部核实、receipt exit=0。普通入口 SHA 为已核 `d5132780…`；保留前节所述 shared_entry 路径／SHA 字段关联缺口。

实际 GPU image ID 仍为 `a473288f…`，prelaunch inspect、attempt、baseline／FrozenPatch 和 grader diagnostics 一致；实际 HEAD `5db0969f…`。host grading 原件 SHA `3d71a627…` 与 input_check／attempt 一致，仍为 `r2e-mr-063`、hidden tree `bd62b707…`、入口 `8285765f…`、62 键期望 `28da3c25…`；没有换掉两个期望 FAILED。solver prompt SHA256 `784cd77d…` 与 attempt prompt、Qwen 的实际公开消息逐字相同，第一个真实网关用户文本块也相同，确认原题面加公开 brief `ef6cd806…` 实际交付；没有加入私有答案。

基线 manifest canonical 重算为 `1e637a9b…`，与 Qwen 的清单逐字相同；本轮 `baseline.tar` SHA256 `131ddb87…`，独立逐项核 1466/1466 个路径、类型、Git 模式和内容 SHA，无额外项。tar 自身摘要不同不等于基线内容不同；actor／grader 完整 census 逐字相同，正式评分原件记 baseline_rebuild_passed=true。

FrozenPatch JSON 文件 SHA256 `2d3fe8ff…`，canonical 摘要独立重算为 `1201329fd2d91c1b4dec70d9d1fe74dd758fb79a91a7f63d4d4531d334c15763`。**它有 10 个条目，不是一个条目**：

| 条目 | 操作与独立内容 SHA256 前缀 |
| --- | --- |
| `src/PIL/TiffImagePlugin.py` | 唯一库源码 modify，100644；`624f5e0d…` |
| `comprehensive_test.py` | 新增诊断脚本；`bb9ad6fd…` |
| `reproduce_issue.py` | 新增诊断脚本；`4367f51b…` |
| `rgb_test.py` | 新增诊断脚本；`3503bbc3…` |
| `temp.tif` | 新增 TIFF；`48eed50b…` |
| `test1.tif` | 新增 TIFF；`15e55959…` |
| `test2.tif` | 新增 TIFF；`20408d33…` |
| `test3.tif` | 新增 TIFF；`13cc35e2…` |
| `test4.tif` | 新增 TIFF；`5e518891…` |
| `test5.tif` | 新增 TIFF；`d6ac0def…` |

10 个 base64 解码 SHA 全相符，grading projection 纳入全部 10 项，实际应用集合 digest 重算为 `a1a50fc3…`，与 report 一致。完整审阅 diff 为 6784 字节、SHA256 `ddcaf1d793e463a0e2e7e41148b811d8a1eb9e295adb8fdf0fcdf5672e423d4a`；独立重建四个文本段（包括脚本末尾无换行），解码六个 Git binary literal，所得每项内容与 FrozenPatch 相同，Git blob ID 均匹配。评分 source 明确 `original_frozen_patch`，没有过滤为一文件重评分。

唯一库源码行为改动是增加说明注释并在 `PHOTOMETRIC_INTERPRETATION not in info` 时赋默认值。它保留用户标签 0，但写出 rawmode／像素转换未变。实际原例与自写脚本都观察到标签由 1 变 0、默认值保持；正式两个模式均已通过保存后源图不变及标签断言，随后在原 `test_1.py:460` 内容往返断言报 `got different content`。与前节 C2 类机制相同，拒绝依据仍是保存／往返行为；保留 P4 登记与原 reward，不重新实验或新增断言。

`grading/eval_logs/evallog_gpu1003-pillow2d01-coder_3e7bebe5.eval.log` 为 13682 字节、SHA256 `2d12197afcc62c7e0c133829fe669d3c199481a85da2d51e8b86172abb532b96`，与 report 引用相同。固定生产 parser 独立解析出完整 62 键、missing/extra=0：58 个 PASSED 键匹配，两个既定 FAILED 键匹配，只 `test_photometric[1]`／`[L]` 不匹配。实际 collected 64、58 passed/4 failed/2 skipped；skip 是额外图片未安装和 Windows only，不进入 62 键表。

原日志只有一对开始／结束标记及时间、test rc=1；candidate exec rc=0、segment_completed=true、partial=false。trusted setup restore=3、expected/actual=4、absent=0、apply=0、setup ok；runner 前后摘要相同，report/status/result 三份相等，execution_failure_stage 和 infra_failure_detail 均为空。不能将两个期望 FAILED 额外扣分，也不能把 rc=1 误写为基础设施失败。

真实 CC 轨迹 `attempt/harness/trajectory.jsonl` SHA256 `06a1e19f…`、403735 字节，与另一 trajectory 逐字相同；27 个工具调用各有唯一返回（17 Bash、6 Write、2 Read、2 Edit）。保留的三个诊断脚本逐字等于相应最后一次 Write；工具清理确实删除了部分临时脚本／TIFF，但上述 10 项仍留在 FrozenPatch。CC 2.1.205 完整 success、is_error=false、terminal_reason=completed、28 turns，harness exit=0、stderr 空；完成求解不等于修复通过。

公开环境实际输出与 Qwen 相同：UID 54321 的 prelaunch／三项 preflight／激活均通过，Python 3.9.21、PIL 8.4.0.dev0、源码和 C 扩展来自 `/testbed/src/PIL`，libtiff 4.3.0、pytest 8.3.4，pip freeze 前后逐字相同。实际公开测试选择是 metadata 21 passed、TIFF `-k save` 6 passed/56 deselected、再选其中三项 3 passed；**没有执行公开兼容 82 passed/2 skipped 的那条方法**。同文 Edit、不存在的 `test_save` 节点、RGB 显式 tag 1 自测分别产生三个工具错误；后续继续且完整结束。自写脚本主要打印标签，不能据它们声称像素往返通过或“所有 TIFF 测试通过”。

预算仍为 `probe-wide-v1`。实际 28 次生成请求全部 max_tokens=65536、model_sent=`Qwen3-Coder-30B-A3B-Instruct`；另有一次 count_tokens HTTP 请求，不能算生成轮次。28 个生成响应均 200、attempt=1、无 stream_error、各有完整 message_stop，27 次 tool_use 后 end_turn；token 计数请求也正常返回。网关／adapter／CC 累计 input 931980、output 5906 一致，单次最大 input 42859、output 857；solve 68.092 秒、评分 46.754 秒。没有长度 stop、预算耗尽或压缩边界事件；并未验证 196K 长 prefill 的全链能力。

quiescence 的进程 0、工作树两次稳定、barrier residual=0 与未超时有原件；gateway session 撤销、active=0、drained=true，与 session_close 相同。actor container_rm=0、left 空，network/relay failures、带标签容器／网络列表全空；manager created=removed=1、open/supply/cleanup_failures 全空。清理验收针对原执行记录，没有新远端检查。

**本轮还需保留一个观察边界：** FrozenPatch 的 excluded_pathset_changed=true，classification 同时记 runtime_private_pathset_changed=true、verdict=projectable、reason_codes 为空。固定 projection 契约将该字段作为观察记录，阻断规则针对进入排除 namespace 的 entry 等不安全形状；本轮 10 项均不属于这些形状，因此全部纳入原评分。没有声称排除面完全未变，也没有猜测未归档的 post census 路径变化原因。这个字段不是本轮的评分拒绝原因；真实 test rc／两个目标断言与原 reward 均可独立复核。

checkpoint_identity_verified=false、服务 config_only、CC maxOutputTokens=32000 元数据与实际 65536 请求不一致、shared_entry 关联字段缺口，均沿用前节限制。作者 [audit](../model_audit_2d01_coder_a1_v1.json) SHA256 `b1fdde8c…` 的 13 项原件摘要／大小也重算相符；本节判断来自原补丁、归档、实际消息、工具与正式日志，不由 audit 替代。两个模型各只这一轮；即使两份候选机制相近，也不外推整体能力、任务难度或训练资格。

## 3a61/a682：已完成输入与结果消费窄核

**本节保留运行前的固定输入与消费方法核查；接续完整结果见下面逐题章节。** 在当时尚未收到完整结果时，没有把在途前三行、作业取得名额或构建完成写成整题 PASS。

CPU 根 `rgba_gif_inputs_core_v1/snapshot_manifest.json` 独立 SHA256 为 `f39e40d4d74af646dce1635b410ad9fe352e1a49e9e0fc91bcd1f826ca9c02e9`；35/35 项 SHA 与大小匹配、omitted 为空。包括构建 context／facts／raw integrity／overlay、第五版 prepared 和实际控制输入，不包含仍在变化的评分结果。

第四版 `r2e_070_077_swe6_candidate_v1`（manifest `621e7366…`）823/823 项、第五版 `r2e_078_079_swe7_git_candidate_v1`（manifest `80ee228d…`）837/837 项均逐 SHA 与大小匹配。两题 `070/071` 与 `072` 的登记条目在两版相等，实际修订文件逐字相同，public bundle 与 environment package 的题级记录相等；builder、replay、actor 与 `result_validity.py` 也逐字相同。这是第四版构建可接第五版新任务面的具体依据，不是只因版本相邻而复用。

| 题目 | 固定材料与构建事实 |
| --- | --- |
| 3a61 | `r2e-mr-070/071`；隐藏测试 `78631c73…`、期望 `af126a3c…`／74 键全期望 PASSED，hidden tree `9305a1b0…`。实际派生 ID `56a40ec9…`；从 context 重算配方 SHA `88d9f6ee…`，与 facts 相同。 |
| a682 | `r2e-mr-072`；隐藏测试 `3573f459…`，原期望 `a465b6c9…`／93 键全期望 PASSED，hidden tree `2cbad6d0…`。实际派生 ID `33f71f76…`；从 context 重算配方 SHA `6126f099…`，与 facts 相同。 |

两个 facts 各 21 项检查全部通过；另直接比较 raw integrity：分别 1525／1615 个工作树文件、各 3221 个 venv 非 bin 文件、17 个 bin 载荷及 git 四项摘要相同，差异仍仅是解释器 symlink 与 pyvenv home 搬迁。第五版 prepared 明确记录上述修订、完整期望、隐藏树和原入口摘要；不能将构建 facts 中仅列隐藏修订的 `070` 误读为遗漏期望修订 `071`，后者由宿主任务面供给。

`control_inputs/rgba-gif-acceptance-v2/` 的 `run_rgba_gif_matrix_v1.py`、`run_rgba_gif_task_v1.py`、`rgba_gif_acceptance_manifest_v2.json` 与 CPU 根实际输入逐字相同，actor 命令与 tracked `cpu/rgba_gif_actor_identity_commands.json` 相同。32 份非 noop 补丁逐一从 `cpu_inputs_v2.tar` 读出并核 SHA，均匹配实际矩阵；另有两个 noop。3a61 确为 18 项、a682 为 16 项，无补造 W4。

3a61 固定原正式 C1 `da1193af…` 为正对照，gold 与 A1u 预期 0；其余预期见题卡，消费代码没有假定名为 gold 的候选必得 1。a682 gold／alt_typeerror／r_kwtuple 预期 1，其余 13 项预期 0。此处只是固定预期，尚不是新运行判分。

消费代码逐个串行调用第五版整份 `replay_grade.py`，运行前核入口／prepared／overlay／候选摘要；不替换生产评分函数。每项核单行 ledger、既定 reward 与 expected_total、语义、参考完整、实际测试段、非 partial 日志及 SHA、agent 投递、实际派生 ID、driver/footer 和清理；任一不符则停止并保留已产生原件。矩阵成功后同槽调用冻结 `r2e_devcheck.py`，真实 CC 只执行 preflight 和公开身份／源码导入命令，不交付私有候选。本轮需从返回原件再核实际 rc、逐键及失败位置和全部清理字段，不能以这些消费检查的源码存在代替执行结果。

本节未发现输入或消费方法的阻断；后续完整结果仍逐题核原件，不以输入检查代替执行证据。不要求重建相同 Pillow 材料、重跑未受影响的旧开发命令或重新启动静态语义审查。

## 3a61：完整 CPU 结果

**PASS：18 项矩阵与真实 CC 最小开发检查完整，没有 CPU 阻断。** 这是 `070/071` 修订材料的题级运行验收；C1 是私有登记的主正对照，原 gold 仍为负对照，不把它的 0 改成 1，也不将这些确定性对照计模型成绩。

原件为 CPU 根 `3a61_cpu_core_v1/`；`core_manifest.json` SHA256 `48318e494eb81213ec07cf7e6039f10352ee6d3ecddc7ef28389e7977b50495f`，244/244 个成员 SHA／大小匹配、omitted 为空，无未列文件。主输出 `packages/r2e_pillow/acceptance/pillow3a61-accept-20261002T181422Z/`，下文称 3a61 输出；job status finished、supervisor rc=0，task_result 的 matrix rc=0、actor rc=0，与真实 driver footer／CC 返回一致。

沿原 inputs core 的第五版 prepared 重读期望，原文 SHA256 `af126a3c513f11efd3f78a89ff5f601a1c9bf401d078d43d569b2dfcc6650304`、74 键全期望 PASSED。18 次 driver 实际命令均指向 `cat2-cpu-r2e078079-swe7-git-20261003-v1` 的整份正式 `replay_grade.py`，使用原 prepared／overlay；每项 stage 完成 projection、无 stage error，实际 actor 投递为 agent/54321，非 noop 为 git_apply。17 份 staged candidate.patch 逐字等于 `cpu_inputs_v2.tar` 的固定输入，SHA 与计划／ledger 相同；noop 为空候选。18 份 FrozenPatch canonical 摘要、内容解码 SHA、baseline canonical 摘要及 projection 纳入路径均重算相符，无测试修改或非法 shape。

原 C1 必须是 `da1193af5bd57ea6dd7a52dc581120d230f40375848e28de8798e9959a6414fa`，本轮确实如此，没有换用云端重建字节。另直接读取第五版 `s2_r2e/ingest/validation_bundles_v0.jsonl`：原 gold 文本、上传包和 `rgba_gif_gold_source_receipt_v5.json` 的导出文本逐字相等，SHA256 均为 `2edc27cd…`；receipt 自身 SHA256 `2b1f3319…`，不是只信导出报告的布尔值。

对 18 份 `matrix/<candidate>/logs/*.eval.log` 使用第五版固定生产 parser 独立重解析，均为完整 74 键、missing/extra=0，逐键与 ledger／results 的匹配数相同。下表失败简称均以 `TestImage.test_remap_palette` 为前缀：`原项` 是该键本身，`重排` 为 `_rgba_reorder`，`透明` 为 `_rgba_transparency`，`GIF` 为 `_rgba_gif_save`。

| 候选 | 匹配／74 | reward | 非期望失败；eval log SHA256 前缀 |
| --- | ---: | ---: | --- |
| noop | 71 | 0 | 原项、重排、透明；`4aeaa8ff…` |
| C1 | 74 | 1 | 无；`2d06e9a2…` |
| gold | 73 | 0 | 透明；`74dd30d6…` |
| A1u | 73 | 0 | 透明；`ce7d61ac…` |
| U11 | 74 | 1 | 无；`0fe10d43…` |
| G_del | 74 | 1 | 无；`a7f8a660…` |
| G_cim | 74 | 1 | 无；`5c18d5bc…` |
| HYB | 74 | 1 | 无；`9325ed38…` |
| G_gif | 74 | 1 | 无；`fd4bde82…` |
| A0K | 73 | 0 | 透明；`d61575ff…` |
| A0D | 73 | 0 | 透明；`562db47a…` |
| FB | 73 | 0 | 透明；`ea198527…` |
| DROP | 73 | 0 | 透明；`8f21d618…` |
| G_small | 73 | 0 | 透明；`3d034bdd…` |
| W1 | 72 | 0 | 透明、GIF；`c716f8fc…` |
| W2 | 71 | 0 | 原项、重排、透明；`a5b96037…` |
| W3 | 72 | 0 | 重排、透明；`653f179c…` |
| W5 | 71 | 0 | 原项、重排、透明；`85400e65…` |

六项正对照均为 74 passed；十二项负对照分别有上表失败，没有混入基础设施失败。每份另有同一历史 skip `jpg_2000 not available`，不在 74 键表内。gold／A1u 的实际失败是原 `test_1.py:686` 调用引发 `ValueError: invalid palette size`；A0K／A0D／FB 在 688 行内容比较失败，DROP 在 691 行、G_small 在 714 行被透明路径挡住。没有用“gold 应过”覆盖真实结果，也没有补造 W4。

18 份日志 SHA 与 ledger 引用相同，只有一对开始／结束标记及测试时间；正对照 test rc=0、负对照 test rc=1，外层 exec rc=0、segment_completed=true、partial=false。每份日志 trusted setup 树为 `9305a1b0…`、入口 `8285765f…`；实际派生 ID 为 `56a40ec9…`、配方 `88d9f6ee…`，PIL 9.2.0.dev0 从 `/testbed/src/PIL` 导入、runner 前后摘要相同。逐个 driver.stdout 最末 footer 与 results 中相同：created=removed=1、open/supply/failures 空、exit=0；candidate cleanup.removed=true。18 次结果均按原顺序完成，无 deadline／halt／截断，matrix stderr 空。

真实 actor 原件在 3a61 输出的 `actor/`，attempt SHA256 `dbe6f2d4…`；轨迹 SHA256 `e398d16f…`、26331 字节。独立核四个 Bash tool_use、四个唯一关联 tool_result、五次 message_start 与五份 stub request；均有真实 rc=0。四条依次是 preflight、UID／解释器、公开激活可见面、公开模块源码导入；输入文件逐字等于已核 commands。CC 在第二、第四条命令中删除了内层重复 `cd /testbed &&`，其余 input／载荷不变，外层 cwd 与 cd 仍是 `/testbed`；不是凭命令计划断言执行。

全部 13 项检查均回到原件：真实输出确认 UID 54321、解释器 `/testbed/.venv/bin/python`、BASH_ENV 不可写及三项 preflight ok；源码导入确认 Python 3.9.21、PIL 9.2.0.dev0、ImagePalette／GifImagePlugin／C 扩展路径与 pytest 8.3.4；真实 inspect 为 `56a40ec9…`。四个 capture 与 tool_result 正文相等（只差终端换行）；CC 2.1.205 最终 success、is_error=false、harness exit=0、日志完整且 stderr 空。root 后检确认 harness/run marker 不在容器、agent 进程 0、新文件 0。

actor 仅做公开身份与导入，无私有候选交付，不能据此称正确解由模型产生。cleanup container_rm=0、stub_rc=0，网络／relay 失败、带标签容器／网络和 residual_after_force 全空。**本题必要 CPU 核查已结束，可按已授权范围继续普通探针；实际 GPU 镜像、原题面消息与生效预算仍由执行者逐次核验。** 原 gold 不再是有效正对照、gold 式自然写法得到 0 的难度变化继续登记；不据 CPU 验收授予训练或留出资格。

## a682：完整 CPU 结果

**PASS：16 项矩阵与真实 CC 最小开发检查完整，没有 CPU 阻断。** 固定第五版 `r2e-mr-072` 与原 93 键期望；没有新增候选、重派 CPU、改变正式评分或把私有对照计模型成绩。

两个原件归档分别为 CPU 根 `a682_matrix_core_v1/`、`a682_actor_core_v1/`。前者 `core_manifest.json` SHA256 `f4fd781148446d349aa7aad847ddabc2626a0d695b7c6f058f21157e82f0ae08`、195/195 项；后者 SHA256 `26da73cb8feaa228ef48d900f1174d47d0b7067d945d950c76b9025e5b9bbccc`、23/23 项。两者全部成员 SHA／大小匹配、omitted 为空，无未列文件；各 job status finished、returncode=0。

矩阵输出为 `packages/r2e_pillow/matrix/pillowa682-matrix-20261002T182205Z/`。第五版 prepared 的期望原文 SHA256 `a465b6c99cb3be23e4f9d9a4f602d6caa2ceea228f524532938a535f7401a096`，93 键全期望 PASSED。16 次实际 driver 命令使用同一第五版整份正式入口／prepared／overlay，stage 均完成 projection、error 为空；15 份非 noop staged patch 与输入 tar 逐字相同、摘要符合固定计划，真实投递为 agent/54321、git_apply。FrozenPatch canonical、各内容摘要、baseline canonical 和 projection 路径全部重算匹配，无测试修改或非法 shape。

本题原 gold SHA256 `c08adef17e02cbc9f68d1c7166d9f42bc946cf80dbfd22b2fb72699860888ecd`；第五版 validation 原文本、gold 来源 receipt、上传 tar 与实际 staged patch 逐字相同。没有借 a682 的 gold 通过把 3a61 gold 负对照改判。

独立重解析每份 `<candidate>/logs/*.eval.log`，93 键观测与期望键集完全相等，missing/extra=0；下表匹配数逐项与真实 ledger／results 相同。所有负对照都只差 `test_removed_transparency`，但由不同断言实际挡住，失败位置列的是隐藏 `test_1.py` 的触发行。

| 候选 | 匹配／93 | reward | 失败位置；eval log SHA256 前缀 |
| --- | ---: | ---: | --- |
| noop | 92 | 0 | 1098；`0f7cdb9e…` |
| gold | 93 | 1 | 无；`2094119d…` |
| alt_typeerror | 93 | 1 | 无；`3b530bfb…` |
| r_kwtuple | 93 | 1 | 无；`680952ad…` |
| w_literal | 92 | 0 | 1124；`ecdfc343…` |
| w_count256 | 92 | 0 | 1124；`d8b262aa…` |
| w_notin_image | 92 | 0 | 1124；`bec1d640…` |
| w_drop_full | 92 | 0 | 1138；`9bf40fa8…` |
| w_drop_big | 92 | 0 | 1148；`f925d8f9…` |
| w_mutate | 92 | 0 | 1104；`71ca3686…` |
| w_convert_mutate | 92 | 0 | 1104；`7ae17e0a…` |
| q_prestrip | 92 | 0 | 1098；`e597da78…` |
| w_mutate_kept | 92 | 0 | 1139；`edba6002…` |
| w_nosaveall | 92 | 0 | 1107；`a4a5a358…` |
| w_order_cache | 92 | 0 | 1118；`f9193756…` |
| w_filter_leak | 92 | 0 | 1098；`8f223ede…` |

三项正对照实际 93 passed、十三项负对照实际 92 passed/1 failed；每份另有两个原有 skip，均不进入 93 键表。逐项 log SHA 等于 ledger 引用，正式完整段只有一对开始／结束标记及时间；正项 test rc=0、负项 rc=1，外层 exec rc=0、segment_completed=true、partial=false。无 missing reference、stage error、deadline 或基础设施失败。实际 setup 树 `2cbad6d0…`、入口 `8285765f…`、派生镜像 `33f71f76…`，16 份配方摘要都等于已核输入 facts 的 `6126f09927658ef9a54bc0ea87ecf4b3c2c2d59244172844a6e6e38cef2d9a12`；没有机械改绑后续 release。

16 份 driver.stdout 实际 footer 逐项等于 results：created=removed=1、containers_open/supply_open/cleanup_failures 空、final exit=0；每份 ledger cleanup.removed=true、driver stderr 空。没有用 results 的 checks=true 代替这些原件。

actor 输出为独立归档的 `packages/r2e_pillow/actor/pillowa682-actor-20261002T184538Z/`，attempt SHA256 `44e267ad…`、轨迹 SHA256 `19df0413…`／26332 字节。四个实际 Bash 与四个唯一关联结果、五次 message_start／五份 request／五条 stub log 一致；顺序与三条固定公开 commands 加 preflight 相同，四个 rc 都为 0，capture 与 tool_result 正文相等（只差终端换行）。第二、第四条内层重复 cd 的同一规范化差异也独立确认，未改变其他载荷。

13 项检查均有真实支持：UID 54321、`/testbed/.venv/bin/python`、BASH_ENV 写入拒绝、三项 preflight ok；Python 3.9.21、PIL 10.1.0.dev0、ImagePalette／GifImagePlugin／C 扩展都从 `/testbed/src/PIL` 导入，pytest 8.3.4；inspect 镜像为 `33f71f76…`，与本题 overlay 一致。CC 2.1.205 完整 success、is_error=false、harness exit=0、stderr 空；root 后检无 harness/run marker，agent 进程 0、新文件 0。只核身份与公开源码导入，没有把矩阵私有候选带入 actor。

actor cleanup container_rm=0、stub_rc=0，network/relay failures、带标签容器／网络和 residual_after_force 全空。**本题必要 CPU 核查结束，可按已授权范围继续普通探针。** GPU 实际宿主身份、公开原题面交付与预算仍逐次核验；本次结果不自动成为训练／留出资格。
