# NumPy d805：登记后 CPU 验收独立核查

2026-10-03。仅核 `numpy__d805e9b66228e68a0eb14d901cd350159c49af18`。本核查者已阅读先前私有修订、候选与父版验收上下文，沿用本包静态与登记前 CPU 核查；**不是 fresh solver**。未参与作者修订或执行本轮实验；本次只读冻结材料和下载原件，未 SSH、未运行 Docker／pytest、未重跑评分，只写本报告。

## 结论

**本轮 CPU 材料、正式评分矩阵和公开开发交付验收通过，未发现需阻止接续统一探针的实质缺陷。** 正式 K-A5c=1，其余九项=0；每行完整评分段均有 229 个严格一致的测试键，九个负例仅 `TestMaskedArray.test_str_repr` 失败，决定性位置符合预期。实际镜像、材料、配方、候选投影、原 FrozenPatch／基线锚、driver 退出与两层清理均能对齐原件。

**外层矩阵 job 实际 rc=1，不能改写为成功。** 十个正式 driver 已分别 rc=0 完成；失败发生在 DG-g 的作者事后路径检查。独立重核源输入和原冻结源码确认 DG-g 只改 `numpy/core/arrayprint.py`，原件没有评分失败、异常投影或残留。按逐输入路径纠正汇总足以关闭该作者检查错误，无需评分重跑；原失败及原始归档继续保留。

公开交付使用真实 Claude Code 2.1.205 和脚本桩端点，是开发与消息交付检查，**不是模型求解成绩**。CPU 通过不等于训练资格、留出准入或模型探针完成；独立 GPU 环境 brief 仅有公开读者静态意见，尚未在 GPU 求解请求中实际交付。

## 材料与证据身份

入口 `[cpu_acceptance_v1.json](../cpu_acceptance_v1.json)` 的原始 SHA 重算为 `91edb0038c2a8c021b959656a2034afdedf808086452e2394613c1c23f1e291c`；其引用的本地原件／归档摘要逐一吻合。原件根为 `runs/category2_repair_20260929/r2e_numpy/cpu_b_20261003/remote_evidence/`，下文 `F` 指其 `packages/r2e_numpy/acceptance/new078079-formal-v1/`，`A` 指 `packages/r2e_numpy/acceptance/new078079-public-v1/`。

- 固定 release5 manifest 为 `80ee228d…`，837 个文件逐一核对 size／SHA 一致；registry 为 v17、pins 为 v18。冻结源码包含本轮共用 git 初始化修复，不用当前可变工作区替代实际运行版本。
- 本题正式条目为 **078 隐藏测试**与 **079 题面**；registry 中仅这两条本题条目。测试全文 `09d0aa6d…` 位于新的 `files_20261003_v17/` 路径，`sha256_before` 为原来源 `72f865c4…`；题面为 `0d6302a3…`。旧 r2e-mr-056 同目标条目未在新版重复保留。
- build facts 实际应用的镜像材料只有 **078**；正式 host grading 的修订列表是 **078+079**。题面进入公开面，不能要求镜像隐藏材料列表也包含 079。build context 的测试全文逐字等于已审草案及当前本包文件。
- 实际镜像为 `sha256:e5c5233cedd4a61525d87bb4f967b2a93f106c6826494bc14326782062b004ac`；配方 `r2e_derive_v1+material_v2+sysconfig_v1`，摘要 `5c426425…`。正式矩阵与公开 actor 均使用这一身份，不复用旧 v8 或登记前父镜像身份。
- 正式评分恢复的 hidden tree 为 `4a5af057…`，入口为 `8285765f…`，与 host grading 和 build overlay 一致；expected 为 `4ed3f5bc…`，229 键全为 PASSED。公开题面摘要、准备产物、actor prompt 与实际请求能串联核对。

## 十行正式评分原件

逐行读取 `F/formal/<候选>/` 的 ledger、完整 eval log、stage、projection、baseline manifest、frozen artifact、保存的 candidate.patch、driver command 与 stdout 末尾管理器记录。没有只采信作者的 accepted 标签或离线审计脚本。

| 候选 | 正式 reward | 首个失败行 | 原始机制与实际投影 |
| --- | ---: | --- | --- |
| K-A5c | 1 | 无 | 229 项通过，含两个新增断言；`numpy/ma/core.py`。 |
| K-A5b | 0 | 511 | edgeitems=501：实际 1002 个 token、预期 1003；`numpy/ma/core.py`。 |
| hybrid | 0 | 499 | 提高阈值后仍应摘要，却输出截取后的全量内容；`numpy/ma/core.py`。 |
| gold | 0 | 492 | n=2000／threshold=2000 应全量，实际 1500 个 token、预期 2000；`numpy/ma/core.py`。 |
| noop | 0 | 458 | 原题面 repr 的数据区没有应有的省略号；空投影。 |
| K-DE | 0 | 478 | n=500 实际 1000 个 token、预期 500，截取重复；`numpy/ma/core.py`。 |
| K-DC | 0 | 478 | n=500 实际 100 个 token、预期 500，静默丢值；`numpy/ma/core.py`。 |
| K-DF | 0 | 468 | n=100000 的摘要断言失败；`numpy/ma/core.py`。 |
| DG-e | 0 | 468 | 只改 repr，str 的非示例摘要断言失败；`numpy/ma/core.py`。 |
| DG-g | 0 | 476 | n=500 不应摘要，实际触发省略号；`numpy/core/arrayprint.py`。 |

每行独立从唯一 Start／End 评分段重取 229 个状态，键集合严格等于 expected，无 missing／extra。K-A5c 无差异；其它九项均只有上述唯一差异键。日志完整 SHA 与 ledger／入口清单一致，测试 rc 分别为 0 和 1；driver rc=0 表示评分过程完成，不能把负例测试 rc=1误写为 driver 失败。

九份非空补丁均以 agent/54321、git_apply 应用，摘要与原输入一致；noop 的 FrozenPatch 条目为空。逐输入推导的预期路径与实际投影完全一致，没有 ignored 或 unsupported path。解码每份 FrozenPatch 的源码后，字节内容等于原输入补丁应用到指定公开初态的结果，也等于保存的 candidate.patch 应用结果。

完整 baseline manifest 的 canonical SHA 为 `9131f39d…`，与每份 FrozenPatch 的锚相等；FrozenPatch canonical SHA 与 ledger／projection 相等，实际镜像、HEAD 和公开 bundle lineage 对齐。公开 actor 捕获的同一完整基线归档含 1447 项，本次逐项核 regular 内容／symlink 目标摘要与 manifest 一致，没有用截取的少数路径代替完整基线。正式行无 stage_error，runner integrity 未变。

每行候选层清理记录为 `removed=true`、`rm:ok`；原 driver stdout 末尾的 manager_close 记录创建／移除各 1、containers_open／supply_open／cleanup_failures 均空，最终 exit_code=0，未 halted 或 aborted。十行的 command、stdout、ledger、日志和关键 artifact 与**首轮原始归档**逐字一致，离线纠正没有替换原运行。

## 两次作者操作异常怎样处理

首次矩阵 job01 在候选执行前的 facts 修订列表检查失败：CLI 错把 079 也列为镜像已应用材料。原 stderr 指向 `formal_acceptance.py:70`，位于 out 创建／prepare／候选循环之前；它没有题级成绩，原失败保留，不能计作负例。

第二次 job02 的外层 rc=1与原 stderr 保留，指向 `formal_acceptance.py:144` 的硬编码 `["numpy/ma/core.py"]`。DG-g 位于计划末行，十行原 driver 均已完成。其原源输入只改 arrayprint，实际 FrozenPatch 与投影同样只含 arrayprint；报错属于作者汇总假设错误。`audit_completed_matrix.py` 是离线读取原件，按每份输入补丁的路径核十行；本核查另外独立重做摘要、字节投影、状态、退出及清理核对，因此不依赖“离线 audit 通过”单一标签。**关闭的是这项检查错误，不是把外层 rc=1覆盖为 0。**

构建／actor 曾收到队列忙 75的记录也保留，不计作候选成绩；本次核的是最终已完成 attempt，没有据此要求重跑。

## 真实 Claude Code 公开检查

直接核 `A/actor/gateway/.../requests.jsonl`、原始 CC trajectory、attempt 和 frozen 原件：

- 七个实际生成请求中，**首个请求逐字包含正式 R-f prompt**，包括改正后的 Actual 与打印选项说明；不是只核准备文件。随后第二条 Bash 从 `/rh2/public_task_bundle.json` 读取 `public_hints`；该完整文本进入第 3 个生成请求。私有候选、两个新增输入、测试摘要或评分细节没有进入这些消息。
- 原 CC trajectory 有六个完成的 Bash 调用，tool_use ID 与 tool_result 对齐；实际轨迹和 harness 原始轨迹逐字相等，harness stderr 为空、exec 已退出 0、日志完整。它使用真实 Claude Code 2.1.205，模型响应来自脚本桩，不据此推断模型能力。
- 预检返回解释器、隐藏测试隔离、git 历史三项 ok；启动前的 agent 预检、activation 和环境事实也与之吻合，隐藏测试不可读、子提交不可见。
- agent 为 uid 54321；Python 实际为 `/testbed/.venv/bin/python`、3.7.9；NumPy 从 `/testbed/numpy/__init__.py` 导入。BASH_ENV 写入被拒绝，pip 不可用的实际记录与公开提示相容。
- 题面原例实际 rc=1，表示初态不满足 Expected，**是预期复现结果**。其完整打印内容逐字对应正式 R-f 的 Actual 块：0、49 个遮蔽项、1950–1999，数据区无省略号。不是把题面修正后的说明当已修好源码。
- 实际以 `python -m pytest` 运行公开打印相关选择，原 tool_result 为 **6 passed、234 deselected、2 warnings**，rc=0；没有把私有测试冒作公开开发检查。
- 静止记录确认 agent 进程为零和工作区摘要双读稳定；FrozenPatch 空、完整基线锚与正式矩阵一致。空的是纳入评分的文件 delta，attempt 同时保留 excluded_pathset_changed=true，不能声称所有排除区也完全无变化。
- 网关原 session_close 记录 revoked／drained、active_requests=0，与 attempt 回执一致；端点停止 rc 为 0／0。容器移除 rc=0、container_left 为空，relay／network 清理失败与带标签残留均为空，e2e residuals 明确清洁。公开 actor 的这些关键原件与原始归档逐字一致，actor driver／job 均 rc=0。

独立 GPU 环境 brief **没有**在本轮实际 actor 消息中交付；本次验证的是正式题面、正式 public_hints 与公开开发命令。这一边界已在 CPU 入口清楚记录，后续 GPU 请求仍需按统一探针安排实际交付并保存消息证据。

## 当前用途与剩余事项

可以接续固定 078／079、镜像与配方的统一探针申请，无需为关闭本轮 CPU 项再造候选或重跑容器。K-A5c 是本轮一维实例及完整 229 键已验的主正对照；不扩称所有 dtype、子类、打印参数、二维或性能都完整正确。gold 已正式核实预期 0，健全性检查应使用 K-A5c，历史 gold／K-A5b 分数不回写。

本题按 **078／079 自建修订版本**报告，不能与原 benchmark 分数直接混算。统一 GPU 模型探针、独立 brief 的实际交付、模型候选行为分析尚待进行；X1 答案暴露／留出划分与 E3 共享控制边界继续保留。CPU 验收不自动解决这些用途条件。
