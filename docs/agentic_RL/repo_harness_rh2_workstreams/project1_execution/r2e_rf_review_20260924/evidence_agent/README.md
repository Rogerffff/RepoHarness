# R-f 判分证据独立复核（2026-09-24）

结论：**未发现阻塞本批 R-f 限定验收的问题，也未发现虚假通过。** 正式 48×noop/gold 的 96 行原始账本完整；固定来源 parser 独立重解析支持 94/96 与参考逐键一致。另两行准确限定为 numpy `2f4a9650` 的同一资源差异。两处文案需更正，见下；无需为此重跑整批。

本复核只读本机已有证据，未访问远端、未启动容器、未改生产代码或维护测试、未提交。按审查标准聚焦 A/E/F/G/H/I/M/N（失败判定、证据有效性、口径、producer、来源与分期），补核 L 的 numpy 资源边界；未重审题目质量、已批准语义或 actor 入口。主审负责快照、导层、当前调用链与远端清理事实。

## 实测与独立重算

执行命令（仓库根目录）：

```bash
python3 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_rf_review_20260924/evidence_agent/audit_evidence.py
```

[探针](audit_evidence.py) **不导入 RH2 的 parser、scoring 或 reconcile**：先核四份 T1 输入 pin，再从固定 vendor 原文件按 AST 提取 `parse_log_pytest / _decolor / calculate_reward / extract_gold_patch`。来源 SHA-256 为 `b928139eb0e9b4da9ca5d0ad927e17cf32727a6d18bc444ed57d63ca1a273bed`。期望映射直接读封板原始 48 行，逐字核对 ingest 的 `expected_output_json`；RH2 侧只解析首个完整 Start/End 测试段，独立按键并集重算计数及差异集合。

最终运行退出码 0，`issues=[]`。结果见 [summary.json](summary.json)、[逐行结果](row_results.json)、[来源与摘要核对](provenance_checks.json)、[控制台摘要](console_summary.txt)。

| 范围 | 重算结果 |
| --- | --- |
| 正式原始账本 | noop/gold 各 48 行，题集均恰等于封板 48 题；无重复 task、遗漏、额外 task、report ID 或日志引用复用 |
| 原始日志与报告 | 正式 96/96 日志 sha256 与账本一致；日志段、测试 rc、sidecar、expected-map 计数与报告互相一致；gold 候选摘要 48/48 等于固定来源函数重建结果 |
| 判分 | noop 48 个 0；gold 45 个 1、3 个 0；所有 96 行均符合独立重算，没有 resolved 与映射不一致的行 |
| 参考原始日志 | 独立发现并解析 336 份；M3 gold 96 条账本的日志摘要/reward 全核对；09-09 v3 144 条账本的日志摘要/reward 全核对。M3 noop 的 96 份日志没有对应本脚本消费的自报 reward 账本，不把这部分说成“账本互核通过” |
| 逐键结果 | 正式 noop 47/48、gold 47/48 与各自所有参考映射相同。两条分歧均为第 17 行 numpy `2f4a9650`，每行相对其 5 份参考都只差 `TestSavezLoad.test_big_arrays`：RH2 FAILED、参考 PASSED |
| 代表题 | 6×noop/gold 共 12 行，全数与参考逐键相同；全部日志摘要正确 |
| bigtmp | noop/gold 各一行，均与 5 份参考逐键相同；noop=0（141/142），gold=1（142/142） |
| 最终 coveragepy 对照 | a/b/c 共 3 行，日志摘要、sidecar 和实际 producer 事实相符，详见下段 |
| 本地路径副本 | 10 份 `_local`/`_local_local` 均只差两处日志/sidecar 路径字段，不是新增运行，也无报告字段被改写 |
| driver 收尾 | 原始 `run_all_{noop,gold}.log` 与 `run_reps_{noop,gold}.log` 的逐行输出、最终行数与账本一致；四份摘要 `final_status.exit_code=0`、无开放 grader 容器或 cleanup failure。此项仅证明 driver 所记收口，宿主全局 `docker ps` 由主审复核 |

全计 113 个不同 report/log 的本批尝试（96 正式 +12 代表 +2 bigtmp +3 最终对照）；没有把较早失败的 pillow/overlay 尝试当成这 113 行的成功证据。

## 代表题与错误对照的实际 producer

代表 gold 的非零测试 rc 不等于评分失败：aiohttp `240da100` 观测为 31 PASSED+2 FAILED，rc=1，映射 33/33；pandas `19c5eea5` 为 138 PASSED+17 ERROR，rc=1，映射 155/155。两者 resolved 均符合已批准 expected-map 语义。coveragepy `016af5f6` 则 15 个 PASSED、rc=0，却因期望包含 FAILED 而只有 14/15、reward=0；不存在把测试进程成功当作评分成功的问题。

coveragepy a/b/c 的 task、image identity、scripts digest、profile 均与资格行一致。资格来自正式 noop 第 6 行 `rpt_grading_493fab23`，不是另一次构建。a/b 候选 sha256 相同；原日志均有 `/testbed/coverage/inorout.py:466` 的 SyntaxError。本机仅编译证据文件也在第 466 行报错，不执行候选。

- **a**：真实 parser 实际产出 `{"": "FAILED"}`，即有 1 个空的观测键、15 个参考键全缺席，**不是零解析**。原日志另有 collection failure，资格及编译复证齐全，产生 `candidate_execution_failed / 0`。
- **b**：同样的原始错误和候选，无资格；sidecar 的 `compile_probe=null`，产生 `test_log_parse_failed / None`。
- **c**：补丁在文件末尾追加 `time.sleep(3600)`；本机编译该文件通过，排除第一版 sleep 补丁的 SyntaxError 问题。原始日志到 `bringing up nodes...`，只有 Start、没有 End/rc；账本期限 150 s、partial=true、segment_completed=false，产生 `grading_deadline_exhausted:test:candidate_phase=test / None`，清理 removed=true。这个未完成尝试没有 post-test runner 摘要，不能外推它也有前后摘要一致证据。

详情：[contrast_producers.json](contrast_producers.json)。这三行证明本题上的实际分支，不外推为所有自定义 runner 的候选归因覆盖。

## 两处非阻塞更正

**E1（P2，运行配置建议）：runbook 的 `/tmp ≥3 GiB` 不能作为已验证的可用配置。**

- 当前文字：[runbook_rf.md](../../r2e_grading_wiring_20260920/runbook_rf.md) 第 91 行。
- 违反的证据边界：本批只有 1 GiB tmpfs/4 GiB 内存失败，以及 6 GiB tmpfs/12 GiB 内存成功；没有 3 GiB 实跑。
- 原始证据：`ledger_r2e_all_{noop,gold}.jsonl:17` 与 `ledger_r2e_numpy_bigtmp_{noop,gold}.jsonl:1`；前者日志明确报 `Not enough free space to write 2147583648 bytes`，后者逐键通过。四行 image identity、脚本和对应候选保持一致，profile 资源改变。
- **代码推断，非新增真机结果**：封板 gold 的 `numpy/lib/npyio.py::_savez`（660–715 行）先在目标旁写临时 `.npy`，然后写 `ZIP_STORED` 的 `.npz`，直到 `zipf.write` 返回才删除临时文件。两份 payload 同时在 `/tmp`，仅数据下界已达 `2×2147583648=4295167296` 字节（略大于 4 GiB），不含头部；3 GiB 不是充分配置。源摘录与 profile 见 [numpy_source_and_profiles.json](numpy_source_and_profiles.json)。
- 影响与分期：照 runbook 配 3 GiB 可能重复遇到环境失败；不改变现有 R-f 判分验收，在下次照此 runbook 配资源前更正即可。
- 修复验收：写为“本批验证 `/tmp=6 GiB、memory=12 GiB` 可运行；最低资源阈值未测，流水线阶段定标”，不为文案补全套实验、不改默认 profile。

**E2（P2，记录准确性）：pandas 代表 gold 的 rc 应为 1。**

- 当前文字：[计划](../../r2e_grading_wiring_20260920.md) 第 398 行写 `155/155，rc=0`。
- 原始证据：`remote/ledger_r2e_reps_gold.jsonl:5` 的 `test.rc=1`；原始 `evallog_replay-r2e-rf-reps-gold-_d631092e.eval.log` 结尾为 `138 passed, 9 skipped, 1 xfailed, 17 errors` 和 `RH2_TEST_RC=1`。正式 gold 第 30 行也相同。
- 影响：写成 0 会掩盖“期望含 ERROR、入口非零仍可 resolved”这一实际覆盖；报告 reward 和 parser 均正确，不是运行缺陷。
- 分期与验收：交接文案改为 `155/155，rc=1` 即可；上述独立探针可复核，无需重跑容器。

Stop condition：本范围的证据已经足以支持 R-f 的限定通过；保留默认资源批的 45/48 和 94/96，不把 bigtmp 改写为原批结果。最低资源阈值、正式流水线资格、题目质量和 actor 接入沿原分期处理；不以这些未验范围继续阻塞本批。
