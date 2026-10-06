# Dask6626 / mypy15139 接续脚本窄审

**当前结论：修订版停止条件已通过窄复核，可交root派发。** 当前脚本SHA256为`38c81608aa1b1307c119329f931565feccbc2375ceca1115a77d8d696cb53b82`；下文原审记录保留为历史，原阻断已关闭。运行结果仍待逐题复核。

2026-09-29 / Codex，交叉复核；未运行远端、容器或目标项目。审阅版本：`rh2/experiments/swegym_cpu_preprobe_20260929/dask_mypy_followups.py`，SHA256 `542b6ba55a77773a0ca67d87eb17173f20073d46df00fda7adf262983a534f8a`。本稿只审执行编排与输入，不授予两题最终用途资格。

**结论：发现一项自动续跑阻断，修后可派发；CLI、题级输入、runner清单和公开／私有材料分离未见新增阻断。** 这不是要求新增通用闸门，只需让本批实验满足已约定的“准备／执行完整性未知时停本题”。

## 需修：预期非零与执行失败未分开，可能自动进入后续阶段

脚本 `actor()` 第138–143行仅依赖 `all_commands_ran/all_match_expect`；第146–149行 `behavior()` 只检查私有helper进程退出码，不读取逐命令状态。

- 冻结 `devcheck.py` 的 `collect()` 将rc124/137标为timeout，但 `matches_expect` 仍按是否为零比较。于是Dask `metadata_assert`、mypy三个policy命令的timeout会满足`expect=nonzero`；mypy `issue_original` 的`expect=any`也会满足。其余命令成功时，`actor_revised`可把这种执行不完整送入私有阶段。`purpose`说须核具体断言，但代码没有在阶段间核它。
- 当前 `tools_v1/private_behavior.py` 的对应源码（本地 `rh2/experiments/swegym_cpu_preprobe_20260929/private_behavior.py:75–85`）只记录命令rc；普通timeout124、ImportError rc1、pytest收集rc2都不会触发helper失败，仍写`executed_interpret_separately`并继续下一个variant。接续脚本随后直接正式评分。只有准备步骤非零或Docker/清理异常才使helper本身失败。
- 这是实际可达的判据缺口，不是说两题当前已发生上述故障。`executed_pending_review`避免了冒称合格，但不能满足此次无人值守续跑的停止条件。

窄修方向：revised actor逐命令先排除not_run/timeout/截断/收集或导入失败，再核最少决定性输出。Dask metadata需先出现`PUBLIC_COMPUTE_PASS`且失败确在类别metadata断言；mypy policy应是预期assignment诊断，原例应有对应reveal输出而非任意非零。私有按variant／命令区分已知行为失败与执行不完整，在后者发生后停止本题；不应把预期错误候选的有效断言失败统一当infra。可在这个新编排文件封装，不要求改公共helper或生产评分。

## 已核对且无需新增门槛

| 范围 | 核对结果与边界 |
| --- | --- |
| 冻结CLI | 直接读 `runs/swegym_cpu_preprobe_20260929/frozen_code_v1/rh2/` 下devcheck、build_derived、build_actor、recipe wrapper、replay CLI及manager调用。参数名、plan列表形状、`compat_v1/install_wave1` style、gold文件命名及结果路径与消费者一致。 |
| 构建与镜像 | 两题计划使用固定registry digest和逐wheel SHA；grader为COPY-only，actor只安装公开依赖。build_derived会因层不保留或wheel hash不符返回非零；build_actor也拒wheel mismatch。没有为题目补丁升级目标库。全环境pip_check只记录、不直接判目标阻塞的处理合理。 |
| 公开材料隔离 | actor仅接public_commands；两个actor build计划只有公开第三方wheel、没有run/files私有载荷。gold及错误补丁只在随后私有helper的`/in`和正式grader可达；未见将整个task_inputs挂入actor的路径。读取宿主私有gold作哈希比较不会自动使actor可见。 |
| Dask输入 | 实际base有`test_utils_dataframe.py`。两条set_index路径核计算值及类别metadata；固定object空类别候选另用numeric-empty dtype检查，有具体公开不变量依据。不能因metadata命令任意非零就称原bug已复现。 |
| mypy输入 | 实际base存在`--force-uppercase-builtins`，三个`-k`名称匹配公开case。对JSON解码后再shlex解析，`-c`源码包含真实换行，不是字面反斜杠n。身份命令核多个模块来自`/testbed`；是否.so遮蔽仍应读实际输出，不能只看路径前缀。 |
| runner清单 | `private_runner_inventory.py` 的遍历、包顺序、路径+内容hash、跳过pyc/cache及缺包标记，与冻结`prepared_task_face.py`的`_V2_RUNNER_DIGEST_PY`一致。逐文件对照覆盖pin前、pin后、editable后；不能将此次重建倒签为历史缺失清单已恢复。Dask pin pytest本就可能改变摘要，不能机械要求`runner_integrity_changed=False`。 |
| 正式参考 | 本次读取的原grading为Dask F2P1/P2P14、mypy F2P1/P2P0；是否逐键实际执行仍由回传日志／冻结parser复核。mypy单键得1不代表题面reveal与force/旧版本政策都修好。 |
| 原安装串 | mypy继续原`pip test-requirements; pip editable; hash -r`；不能只凭最后install_rc为0断言前两条都成功。这里未把已知来源安装形式改成新机制；结果复核须看原安装输出。 |
| 收尾 | 父脚本中断会向子进程组发TERM并留300秒收尾，强杀后停止；私有helper独立容器、无网络、最后查询残留。准备/清理失败停止路径已有，不要求再重构。 |

## 已撤回的初步疑点

最初向root提过“`patch_apply_failed`可以reward0而无测试，grade可能继续”。继续追到冻结replay实际调用后撤回：本批始终传`FrozenDeltaSource`，candidate预应用失败不会进入评分、report为空；manager的该reward0分支属于legacy cleaned-patch路径，本批不可达。不得把这点列为本脚本阻断或借此新增门槛。

## 输入版本与剩余复核

决定性输入SHA256：

- Dask公开命令 `dd9a8d9fca22477e18cd36f928d2dc8b25dea5363a025fd1894a6af15cd1c606`；私有spec `c7007a0ba3dba5d7911710ce4c193ed1365eee11310154292cf2121374e22394`；runner清单脚本 `942e65be52c905f8ffe4878d6dc72eff1ee552bf684061ed775c0dd0b88ad61f`。
- mypy公开命令 `2052dde6ed7a01491cf7dbecd7cb06008a7a1733fe4fd96e55bec5ccb8f7d764`；私有spec `b3862adb7a4e601120a5ae025d049dea02dd0443c94737922c8a0e9f83123673`。

修订后窄核以上停止条件即可，不重做整套静态审查。实际actor公开输入/工具流、依赖和导入、私有正负对照、runner文件差异、正式逐参考及清理需待root回传；本稿没有运行结果或最终题目资格结论。

## 修订后窄复核（2026-09-29）

仅回查上述阻断的修订路径，未重做完整审查、未改实验脚本：

- actor现在核命令ID顺序、缺失、timeout124/137和截断。修订环境增加`check_diagnostic`，Dask类别断言需先有计算完成标记；mypy需两个reveal结果或预期assignment诊断。原环境故障继续进入已明确的依赖修复是本任务既定流程，不冒充修订环境通过。
- 私有helper每次只运行一个variant；matrix内逐命令检查，遇不完整或非目标异常即非零，不再运行后续命令。父脚本随后核matrix退出码、完成标记与rm/query/remaining，失败不续派下个variant或正式评分。runner库存文件仍从完整matrix分段落回原路径。
- 正式阶段现在核安装、test segment完整、参考缺失、apply_ok及noop/gold控制结果；Dask仍以文件证据解释pytest变更，没有新增`runner_integrity_changed=False`通用要求。
- 只运行了此新编排脚本的纯判据fixture及AST检查：timeout124/137、rc2、None、ImportError、收集／内部错误均被拒绝；预期metadata AssertionError、numeric-empty退化失败、mypy assignment错误及双reveal完成输出可保留。没有运行目标项目或任何远端／容器操作。

原自动续跑阻断已关闭；本次未发现新的具体阻断。允许派发仅指这份编排方案，`executed_pending_review`仍需读取真实输出，不能直接当两题资格。
