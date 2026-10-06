# D6 原 actor 工件直评 v2 工具窄审

2026-09-29。**无执行阻塞，可在独立封板修复代码下逐题调用正式 grader。** 本结论不是实际接缝已通过；F1 的旧失败原件保持有效，实际结果另审。

对象 `runs/category2_repair_20260929/tools/d6_actor_to_grader_v2/actor_to_grader.py`，独立重算 SHA-256 `c19ef71b55ad52dfd37dd817b50583db38aec7eb6a9c39ca142d222deae56c0f`，27508 字节，语法编译通过。此次阅读 v1→v2 完整 diff 及 execute/finally，基于 [v1 完整工具审查](d6_actor_to_grader_runner_review.md)，不重复既有原件全文，不调用远端或 Docker。

## 输入不替换

- 10424／17071 分别固定原 actor 的 28 文件记录清单 SHA、原镜像和原 CPU spec join SHA；逐件核 SHA／长度，保留原 baseline、frozen、projection 和物理 attempt 身份。
- `actor_origin_code_manifest_sha256` 固定旧 actor 代码来源；`execution_code_manifest_sha256` 来自外部固定的新封板 SHA，再逐件核代码清单。两者分列，实际执行明确不接受旧代码清单作为修复版本，不将新评分代码伪写成原 actor 来源。
- 同一 prepared face/assignment 生成正式 spec；七份脚本摘要、三项预算、hygiene、材料身份与原 CPU join 对照。profile 摘要和镜像保持原值；禁止 overlay 覆盖，不重建替代 source baseline。
- 仍每次只一题、一次 `manager.grade(workspace=None, frozen_delta=source)`；没有新 actor、模型、候选补丁或工具层评分重试。

## 成功判据不止 reward=0

`PhaseObservedManager._verify_baseline_rebuild` 先 await 生产 super，只有正常返回后才写 `baseline_rebuild_passed=True`；进入阶段或纯 binding 成功均不算通过。super 失败仍保留 traceback／phase 并非零退出。

`validate_report` 要求 baseline 已通过、正常 unresolved/tests_failed/reward0、clean frozen replay、完整日志 SHA／长度与侧车、每个安装子命令成功、测试段完成且实际 test rc=1。它独立从完整日志的正式 test segment 用 mypy parser 得到逐参考状态，要求精确等于原 F2P 全失败／其余原及新增 P2P 全成功，核实际 selected 数、分区无 missing/skipped/unaccounted、正式 parser 完整计数和 report 分母。材料身份及修订 registry/digest 仍逐项相等。

这避免了“baseline 根本没过”“安装失败但最后一条命令 rc=0”“只跑了部分节点”的 0 分误通过。raw eval.log、diagnostics、Docker 原始输出和新旧代码身份仍须独立再读，自动 review 只是验收辅助。

## 异常与清理

v1 的 fatal20／其他 fatal21／异常22／意外或不完整报告23保持；finally 有界 manager.close，精确按本次独占 `rh2.run_id` 查询容器与网络。任何清理残留、未知查询或 close 异常把最终退出码改为24，并保留此前评分退出码。未新增按共享前缀清理其它 run 的行为。

输出目录仍不得覆盖代码、原 actor 或 CPU 证据；执行结束再次核原输入。v2 新输出独立保存，不回写 v1 的真实 fatal。下一步验收需确认新封板 SHA、真实 raw census 与原 actor 完整 manifest 相等、sanitizer 自证／安装／逐参考状态和本 run 清理全部闭合。
