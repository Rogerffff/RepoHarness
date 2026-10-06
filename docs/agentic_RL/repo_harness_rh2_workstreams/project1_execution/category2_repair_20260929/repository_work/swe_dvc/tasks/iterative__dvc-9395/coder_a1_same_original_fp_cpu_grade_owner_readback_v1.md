# DVC9395 同原 Coder 候选的 CPU 补评分

2026-10-03 21:14 SGT。**补评分得到有效 0：40 个正式参考中，3 个 F2P 失败、37 个 P2P 通过。实际 pytest 执行 41 个测试，4 失败、37 通过；额外未计分的原 import 测试也失败。** 候选问题与此前静态分析一致。GPU 原轮次的 entry RC1、cleanup=false、reward=null 保留，新 CPU 评分以关联记录保存，不新增模型样本。

本次 job 为 `dvc9395-original-fp-cpu-grade-20261003-v1`，关联原 `gpu1003-dvc9395-coder-a1` 和请求 `swe-dvc9395-behavior-r20-v1-20261003`。GPU 已明确确认没有重复评分／新求解，并将补评交题主；CPU 单槽 q01 完成，returncode=0。原求解215.507秒保持，CPU评分246.473秒另记，不混作新的模型求解时间。

## 输入与正式运行

- 完整原 FP 三项均在实际投影中：`dvc/stage/__init__.py`、`test_comprehensive.py`、`test_pull_fix.py`。FP canonical 为 `sha256:1cad35171d386f0d905859d0232d29d7df9a398872d62e6e71e98ffc8d0cd456`；没有裁剪两项根目录生成脚本，也没有另做补丁。
- 原 baseline canonical 为 `sha256:0c75caa0ac9790c739e0250f37125f342241d19d57bb430e6a6c7fa009acf0ec`。CPU 的真实重建 census 与其615项对象类型、执行位和内容SHA逐一相等；不是用CPU新建manifest替代原件。
- 实际消费冻结code8、R20原material identity、public/prepared/host grading摘要、四个参考分区及严格prepare900政策。只有宿主文件的物理路径重定位；原 manifest 和材料字节不改。镜像仍是已验 `sha256:c093861f62b8071b3c1e5b3142abd5843888421364e69dd728cb80856f621b60`，本地镜像的registry manifest仍为null。
- 原资源与时限保持：2CPU、4GiB、PID512、UID54322，whole/setup/apply/test为3600/900/120/1800秒。无supply、无模型服务启动，实际single-shell脚本digest为 `sha256:ec5f61cf288b78aaafd469b40013bcd571e93e1ab5db7c32c8852b6a83f035f3`。
- 可信setup恢复两份官方测试，apply与控制面保护均通过；候选UID轮子预检为0，安装0、实际test1、外层candidate exec0，segment完整且非partial。外层0表示运输完成，不表示测试通过。

| 正式分区 | 实际结果 |
| --- | --- |
| 原 F2P 两项 | missing-source与restore-pull均失败 |
| 新增 F2P 一项 | frozen输出恢复失败 |
| 原 P2P 27项 | 全部通过 |
| 新增 P2P 10项 | 全部通过 |

四分区列表与原 input_check 相同，没有missing、skip、unaccounted或未执行后补猜结果。额外原 `test_repro_pulls_mising_import` 失败，未加入计分分母。

## 候选与故障的区别

原missing-source、import及新增frozen恢复的真实堆栈均进入 `Stage.run` 的 `_check_missing_outputs()`，随后抛出 `MissingDataSource`（foo或raw），没有先执行新增恢复逻辑。restore-pull在保存输出时抛出 `OutputDoesNotExistError: bar`，本地checkout未解决真实恢复。这支持既有“恢复顺序不对、helper没有cloud pull”的错修判断；不将业务异常误称为pytest收集或基础设施失败。

原轮次只有已完成的模型求解，因relay删除60秒超时未进入grader，原reward保持null。后来GPU清理证明与本次CPU有效评分是两个关联事件；本次不声称修复了GPU relay超时的根因，也不重写原失败状态。

## 资源、清理与计数边界

本次51条cgroup观测和关闭前原件记录：memory.peak为1033506816B，pids.peak为11，pids限额事件0，OOM／OOM-kill计数0，OOMKilled=false。实际HostConfig核同2CPU/4GiB/PID512和deny-all网络；manager创建／移除均1，没有open/supply/cleanup failure，slot结束后的精确owner label查询也无容器残留。采样范围属于这次CPU grader，不能推广到原GPU solver；diagnostics.resource_facts仍为null，不用新观测覆盖它，writable-layer总配额也没有新增强制生效证明。

原官方parser的 `num_parsed_tests=42` 保持：它额外解析了捕获日志 `ERROR dvc.commands.freeze:freeze.py:19`。实际pytest footer及逐节点为41，正式参考为40；计数分开，逐参考状态一致，不改官方原结果。hygiene clean只表示投影边界通过，不代表候选最小或正确。baseline的environment_package_digest依然null，普通诊断不授训练资格。

第一次纯构造因tar提取使私有文件0644而被guard拒绝，没有候选执行。修复只收紧私有文件0400／目录0700并核全部SHA不变，pure_v2通过。首份只读归档脚本另有字符串SyntaxError，未创建归档或再执行评分；v2修运输脚本后回收38件闭合原件。两份失败证据保留，原code8、评分脚本、材料和候选未因这些运输修复变化。

## 收口范围

题主已逐项核38件闭合原件、完整615基线与41实际节点，并完整读回[非作者运行审查](../../reviews/non_author_dvc9395_same_original_fp_cpu_runtime_20261003_v1.md)。53个独立报告原件指针及41个节点日志行号均再次匹配；本次评分／清理已核收，见[验收摘要](coder_a1_same_original_fp_cpu_grade_acceptance_v1.json)。本次可信准备聚合156.179秒，不能据单次时点证明旧300秒争用根因或效率问题已经根治。

本次只补齐Coder首臂评分。Qwen首轮仍待返回，成对请求保持claimed，不提前ACK，不推断稳定性或训练／留出用途。既有[候选／七维轨迹审计](coder_a1_semantic_audit_v1.md)及其非作者结论复用；没有修改模型候选，也不为使错解通过而放宽题目。

原件入口：[完整题主读回](../../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/dvc9395_same_original_fp_cpu_recovery_20261003_v1/owner_complete_readback_v1.json)；[真实官方report](../../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/dvc9395_same_original_fp_cpu_recovery_20261003_v1/actual_readback_v1/grade_v1/report.json)；[完整eval日志](../../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/dvc9395_same_original_fp_cpu_recovery_20261003_v1/actual_readback_v1/grade_v1/eval_logs/evallog_dvc9395-original-fp-cpu-_f3ede5fb.eval.log)；[闭合清单](../../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/dvc9395_same_original_fp_cpu_recovery_20261003_v1/actual_readback_v1/closed_manifest.json)；[非作者逐节点JSON](../../reviews/non_author_dvc9395_same_original_fp_cpu_runtime_20261003_v1.json)。
