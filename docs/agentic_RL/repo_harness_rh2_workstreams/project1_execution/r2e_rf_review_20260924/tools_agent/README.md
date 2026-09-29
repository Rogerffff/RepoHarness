# R-f 小工具独立复核（2026-09-24）

结论：**旧 F1、F2 关闭；runbook 原三处更正完成。没有新增 R-f 阻塞项。** M3 账本互核有一项非阻塞 P2：混入 `--old-root` 的不同参考结果时，会误报 M3 账本与自己的日志矛盾；空 reward 的“未知”处理一并建议修正。锁元数据写入失败后的残留仅列低优先维护注，不建议增加锁系统。

范围：只读 `rh2/scripts/reconcile_r2e.py`、`rh2/scripts/build_r2e_derived.py`、相关维护测试、runbook 与旧 closeout；必要的合成输入及探针仅写本目录。未改生产代码、旧探针或历史真机证据，未提交、连接远端、租机、执行 Docker 或启动容器。主审另核实际 96 条及镜像／资格／快照。

## 1. 旧问题核销

| 项 | 本轮证据 | 结论 |
| --- | --- | --- |
| F1：相同差异键不能代表相同状态 | 真实对账 CLI：期望键 PASSED，RH2 FAILED、参考 ERROR；`reward_equal=True`、`diff_sets_equal=True`、`observed_maps_equal=False`、`agree=False` | 关闭 |
| F1：M3 账本自报与日志互核 | 真实 CLI：两侧日志相同且重算 0、M3 自报 1；日志层 `agree=True`，另列 `reference_ledger_consistent=False`，Markdown 明确计 1 条矛盾 | 关闭；`agree` 与“账本是否自洽”分列符合旧建议 |
| F2：同目录并行读写丢条目 | 独立进程 A 持有锁；进程 B 分别使用 `--all`、`--regenerate-overlays`，均退出 2 / `output_dir_locked`，原 overlays/results 未变化；A 释放后正常汇总且删锁 | 关闭 |
| F2：锁覆盖范围 | `main` 获取锁后才调用 `_main_locked`；实际 results 读写、facts 读写、循环内及末尾 `write_overlays` 全在锁内。CPU 探针只替换 Docker 叶节点，保留真实入口、目录扫描及文件读写，并逐次断言锁在场 | 覆盖当前 CLI 的全部汇总读写；旧 results 条目保留 |
| F2：主体异常释放 | RuntimeError、KeyboardInterrupt、SystemExit、坏 facts JSON、overlays/results 写入 ENOSPC 共 6 种异常均释放锁 | `_main_locked` 的异常释放成立；锁说明写入另见维护注 |
| runbook：全新机器缺 SWE 材料 | §1 改为只选 `test_real_48_tasks_load_through_the_trusted_entry`，加 R2E parser 文件；该例 fixture 只加载 R2E 材料，本轮通过 | 关闭；本轮未另外构建隔离的空机器副本 |
| runbook：摘要 4 与 shell 1 | §3 明确 `final_status.exit_code=4` 是 JSON 摘要，异常 traceback 的真实 shell 退出码为 1 | 旧缺补丁异常案的文案已更正；本轮未重跑 driver |
| runbook：sha 校验 | §1 直接 `sha256sum --quiet -c ... && echo SNAPSHOT_OK`，移除吞错误的 `grep ... || echo ALL_OK` | 关闭 |

两份工具及 `test_reconcile_r2e.py` 的 SHA-256 均与 `runs/r2e_snapshot_20260923.sha256` 对应条目一致。工具摘要保存在探针结果中。

## 2. P2：参考账本互核混用了不同来源的参考日志

- **当前行为／位置**：`reconcile_r2e.py:77–86` 从所有 `comparisons` 构造 reward 集合，其中包含 `reference_logs` 在 `:37–47` 收集的 M3 与 `--old-root` 日志；只要集合有两个 reward，`reference_ledger_consistent` 即为 False。`:164–165` 却写成“参考账本自报 reward 与其日志重算不符”。
- **违反的不变量**：M3 账本与自身原始日志的互核，应与“不同参考来源之间有分歧”区分。前者不能用全部来源的 reward 是否唯一替代。
- **复现／证据**：合成同题 gold，M3 日志重算 0、M3 账本自报 0，旧参考日志重算 1。真实 CLI 仍把 M3 的 `reference_ledger_consistent` 标 False，并计为 1 条账本自相矛盾。见 [混合来源 CLI 结果](probe_output_20260923T165341082503Z/mixed_reference_sources/out/reconcile.json) 及 [Markdown](probe_output_20260923T165341082503Z/mixed_reference_sources/out/reconcile.md)。
- **可达性／影响**：`production_reachable`，现有 `--old-root` 入口可达，使用合成输入复现；会误导分歧归因，但总体 `agree=False` 仍正确，不把真实差异放行。本次固定 M3 账本 96 行 reward 全为整数，不能把此反例当作已发现真机账本矛盾。
- **同项未知边界**：`ledger_rewards=[None]` 时，`:86` 过滤 None 后对空集合 `all(...)` 得 True，缺少可互核 reward 反而被标为一致；见 [空值 CLI 结果](probe_output_20260923T165341082503Z/null_reward/out/reconcile.json)。应记 None／未知，当前 M3 96 行未触发。
- **建议／分期**：非阻塞 P2，归 B 线工具维护，在下次扩充或重用对账语料前修。只用 M3 对应日志互核 M3 账本；不同参考来源间的分歧沿已有 comparisons 展示。没有有效账本 reward 时给 None，无需改变生产评分或训练准入。
- **修复验收**：上述“自身一致、旧参考不同”案应保留总体 `agree=False`，而 M3 自核为 True；M3 自报 1、自身日志 0 仍为 False；全空 reward 为 None。

## 3. 低优先维护注

`build_r2e_derived.py:399–400` 的锁说明写入发生在清理 `try/finally` 之前。对该写入注入 ENOSPC 后，主逻辑尚未开始，留下 0 字节 `.build.lock`；之后重试退出 2。见 [探针汇总](probe_output_20260923T165341082503Z/summary.json) 的 `F2_lock_header_write_error_observation`。这是当前入口可达的受控异常反例，**没有共享文件被覆盖**，已有锁冲突提示允许操作者确认无其它进程后删除残留。

建议在顺手维护时把锁说明写入纳入现有 `try/finally`；或接受这类 I/O 故障后需手工清锁的剩余风险。不需要自动解锁、PID 存活判断、恢复状态机或新平台。主体异常释放与旧 F2 互斥核销不受影响。

另有一处 T2 文案：`runbook_rf.md:74` 仍用旧的“两条件”概述 `agree`，宜补上“观测状态映射逐键相同”；脚本和实际生成摘要已经采用三条件。

## 4. 验证与停止条件

- 维护测试：`test_reconcile_r2e.py` 两例与真实 48 题可信加载一例，**3 passed，0 skipped／xfailed**；[输出](maintenance_pytest.log)。
- CPU 探针：[源码](probe_tools.py)、[最终 stdout](probe_final_stdout.log)、[最终结构化结果](probe_output_20260923T165341082503Z/summary.json)。使用真实对账 CLI；构建探针显式替换 Docker 叶节点，未验证实际容器生命周期、SIGKILL 后恢复或文件系统崩溃一致性。
- 本轮没有重跑全量套件或 336 份 parser 语料。最初探针遗漏 pytest summary 格式，产生双空映射；该版失败记录保留于 `probe_initial_invalid.log` 及首个输出目录。最终版在生成日志时断言重新解析映射与输入相等，旧 F1 的有效反例以最终目录为准。
- 停止条件已满足：旧两个对账反例被正确区分，同目录正常调用与重汇总互斥成立，原三处 runbook 更正到位。后续工具边界登记维护，不据此阻塞本批 R-f，也不扩大为评分、题目质量或正式 actor 的新闸门。

复跑命令（仓库根，产物自动使用本目录下新的时间戳目录）：

```bash
PYTHONDONTWRITEBYTECODE=1 rh2/.venv/bin/python -B docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_rf_review_20260924/tools_agent/probe_tools.py
```
