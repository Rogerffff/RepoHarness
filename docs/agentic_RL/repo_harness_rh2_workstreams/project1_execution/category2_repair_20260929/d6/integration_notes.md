# D6 首片如何接入后续探针

2026-09-29。首片CPU验收已完成，最终状态及逐题版本见 [handoff_mypy_v2.json](handoff_mypy_v2.json)。已合入本地共享代码，18个相关文件与封板逐字相同，130项集成检查通过；接收线程仍需纳入自己的下一版，不能热替换在途运行。公共评分安全、模型配置与GPU准入不由本片核销。

## 必须一同消费的内容

1. D6正式类型、可信摄入、prepared／host共同构造、材料资格及诊断代码。修订材料由固定登记单重建，不能只编辑P2P字符串列表。
2. 本次两题修订产物与登记SHA；公开题面仍为原字节。旧prepared和新host不能混用，应在新批重新prepare。
3. 经过验证的离线派生镜像。两个image ID同时适用于本片actor开发和grader；重建新镜像必须核来源及资产，不把名称相同当相同环境。
4. 候选前同源Git初始化修复。正式actor原已执行sanitize；新版replay与grader补齐。完整baseline摘要和HEAD比较不变，旧原actor工件直评已经单独验证。

候选集成补丁与逐文件前后SHA在 `runs/category2_repair_20260929/d6_integration_candidate_v2/`。它针对固定base commit `a31cdcd0adb0fab3e681201edfb928653fdf5b3c`；18文件补丁已在临时纯目录重放，输出全部等于封板源码。接收分支存在其它R2E／A改动时应按窄差异合并并复核，不能整树覆盖。A线的generate/quiescence已验修复是前提，未混入这份18文件补丁。

文件夹名保留准备阶段的 `candidate`；最终通过记录是其中的 `integration_acceptance.json`。本片固定代码清单SHA为 `4110b196c8df1f0e8d51595b525eed17f6487977d83e59e2fddd68f5f11d965b`，组合补丁SHA为 `2b1c2ff2149323482d4c2f05cb917d4577db6e80df6f9d2ea98fdcfd0651715d`。旧handoff v1仍记录当时阻塞，不继续消费它。

窄复验工具为 `runs/category2_repair_20260929/tools/d6_acceptance_v2/run_acceptance.py`，SHA `ea5ec52ce2d7f54f46d9f5673839213b987dbcfac5eb3ce208aecfcd9238e95f`。使用接收方新封板的 `--code-root`、`--code-manifest`／`--code-manifest-sha256`、本批 `--input-root`，另建未存在的 `--out` 和独立 `--run-id` 后 `--execute`。可用 `--only-task` 做单题窄验；必须读全部真实参考、安装和两层清理，不能只看脚本退出码。封板没有变化时不为交接机械重复已验矩阵。

交接JSON中的actor端点仅是已执行命令桩的证据值，不是下一轮模型地址。接收方应提供统一模型端点和预算，记录实际profile；不要复制该桩的端口。评分侧必须使用已验正式grader profile并保留完整基线比较。

## 正式配置与验证边界

- 使用正式sandbox profile。仓内正式replay CLI明确给manager传入grader profile；直接API把有profile的ReplayGrader候选与无profile的旧manager混用不在此片支持范围，不能依据FakeDocker测试把该组合说成已验。旧manager单独无profile行为未改变。
- actor原sanitizer继承镜像ENV，新replay／grader使用既有受信清环境前缀。两题原actor工件重建的全字段完全一致，证明本片两镜像适用；不能把它扩大为所有镜像或任意clone初态已经验证。其它题按同一严格比较逐题接入。
- 评分材料修订、runtime代码修订分别登记。旧分数仍属原版本；新的错误候选被拒记录不能回写成历史模型结果。
- 本片只证明合理公开开发操作、正式材料消费与确定性正反对照。模型预算、模型质量比较、miles训练消费／排空和全仓测试未由这组CPU实验验收。

## 本轮补上的流程检查

工具的“同一材料绑定通过”不等于真实actor工件已经能交给fresh grader。修订公共准备步骤时，应保留真实actor工件，直接运行完整重建和评分，再校验replay候选入口；不能靠删除摘要字段或改成diff运输核销。这里是实际发现的阻塞，已保留修前fatal和修后两题直评原件。
