# coveragepy__5dbbe143：静态审查短卡

> 第二步由接续会话完成：原主审会话在封存初判后因 API 错误中止。
> - 前稿：[analysis_before_history.md](analysis_before_history.md)，未改动。
> - 历史核对：[old_findings_delta.md](old_findings_delta.md)。
> - reviewer 的初判没有读，复核结论由协调者收口。
>
> 2026-09-25。

## 1. 目标、版本与用途

- **题目**：coverage.py 5.0.2a1（base `8240c58c`，Python 3.7.9）。题面要求私有方法 `Coverage._warn` 接受 `once` 参数，并让 `once=True` 的警告"只显示一次"。
- **gold**：只改 `coverage/control.py` 的一个函数，约 15 行，与上游提交中非测试文件的改动逐字节相同。
- **评分**：期望结果共 75 个测试键，全部为 PASSED。目标键只有 `ApiTest.test_warn_once`，其余 74 个是同一测试文件里的回归键。
- **用途**：`development_diagnostic`。去重键问题解决之前，不作为基座探针候选。

## 2. 关键映射

| 需求或旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖情况 | 执行证据或下一步验证 |
| --- | --- | --- | --- | --- |
| 传 `once=True` 不再抛 `TypeError` | 题面第 7、13–14、21 行 | `test_warn_once` 中的两次调用（`test_1.py:545-546`） | 覆盖 | noop：当前材料 2 次、M3 来源镜像 2 次，都在第 545 行抛 TypeError。gold：同样 2+2 次，全部通过 |
| 第一条警告照常输出 | 题面第 18 行；`control.py:345-350` | `assertIn("Warning, warning 1!", err)` | 覆盖（只查子串） | gold 日志的 stderr 只有 `Coverage.py warning: Warning, warning 1! (bot)` |
| 重复的警告不再输出——**按什么判定"重复"** | 题面第 18 行只写了 "only once each, preventing duplicate warnings" | `assertNotIn("Warning, warning 2!", err)`（`test_1.py:549`）：同 slug、不同消息的第二条也必须被压掉 | **冲突 / 欠明确** | 静态推断：按消息去重（CE1）、按（消息, slug）去重（CE2）都判 0。尚未实跑 |
| 不同 slug 的警告各显示一次 | 题面中的 "each" | 无 | 缺失 | 静态推断：过粗的实现 CE4 判 1。尚未实跑 |
| 不传 once 的调用行为不变 | 现有调用点都不传 once | `test_warnings` 等回归键 | 覆盖。未测：同一 slug 先有 once 调用、后有非 once 调用的情形 | noop 与 gold 下这些键全部 PASSED |

## 3. 八方面：已查与未查

- **公开需求**：已查题面、hints、docstring、`disable_warnings` 与公开读者报告，结论是去重键缺失。模型实际收到的完整消息没有查到；只核对了 user prompt 与 R-f 的 `prompts.jsonl` 逐字节相同。
- **材料与初态**：哈希全部一致；gold 与来源镜像中的 `git diff HEAD 修复提交` 逐字节相同；noop 失败在题面所述的报错上。
- **测试是否测到要求**：目标键全读。与 `_warn` 相关的 7 个回归键逐条读过；其余 67 个只核对了 import、fixture 和状态。
- **误拒合理解**：CE1、CE2 预计判 0（静态推断，未实跑）。
- **回归与 gold**：gold 有 1 个未被测试覆盖的旧行为变化（G1），另有 2 个潜伏行为（G2、G3），见附录。
- **开发条件**：评分侧已实测；解题侧只在镜像层面实测过（历史探针）；正式链下的 actor 待验。
- **交付与评分边界**：合法修复只需改 `control.py`。隐藏测试会导入 base 版 `tests/coveragetest.py`，而这个文件候选可以改。共享机制没有重新审查。
- **题目关系**：本题的 gold 出现在同批另外 4 道 coveragepy 题的 base 中。

## 4. 问题与证据层次

1. **题意与测试不一致（主要问题）。** 题面没说按什么判定重复，测试却强制按 slug 判定，最字面的读法反而判 0。证据有四层：
   - 静态推断；
   - gold 在历史真实 RH2 运行中的 stderr；
   - 来源行的 `prompt` 字段显示，题面生成器的输入里有 "(determined by the slug.)"，生成的题面却漏掉了这一句；
   - 公开读者在隔离条件下判断"无法裁决"。
2. **漏测（次要）。** CE4（第一次 once 之后，所有 once 警告都不显示）会得 1。证据是静态推断。
3. **gold 的副作用 G1（低）。** gold 在第一次调用 `_warn` 时把 `disable_warnings` 复制一份，之后再用 `set_option` 修改它就不生效。证据是静态推断；这不影响评分，也不作为判定任何候选的依据。
4. **旧测试辅助（历史 R04，低）。**
   - 只影响"给现有调用点加 `once=True`"的改法，而题面没有要求这样改。
   - 建议不修订，并关闭这个未完成项。
   - 若以后仍要修，不能照搬 datalad 那样改导入：`TESTS_DIR` 是由 `__file__` 推出的（`test_2.py:38`），改导入会让依赖 `tests/modules` 的键失效。
5. **共享问题（本题适用，不按单题修）。**
   - 候选可以改 `tests/coveragetest.py`，不修源码也让目标键通过（静态推断）。
   - 正式 actor 仍取来源镜像，其中隐藏测试可读、修复提交可达。工作树里已有未提交的修复改动，尚未验证。
   - hints 里的 conda 措辞与本环境不符。
6. **题目关系。** 本题与 016af5f6、97997d2c、ea6906b0、f5eb5f21 同族，划分数据集时要一起处理。

**环境侧**：本题没有配方，也没有材料修订。环境阶段的结论（评分可复现、镜像层面的开发条件满足）适用于当前材料，已逐条核实。

## 5. 建议与下一步

**处置**：`needs_review`，理由是题意与测试不一致。与封存前稿相同。读历史后只补了证据、做了更正，处置没有变，详见 delta §2。

**建议**（都未决定）：

- (a) 在公开规格里补一句："是否已经显示过，按 slug 判定；同一 slug 的后续 once 警告，即使消息不同也不显示。"这属于 T0 修订，由用户决定。
- (b) 历史 R04 不修订。
- (c) 可选：修订时一并补上"不同 slug 的警告各显示一次"的断言。
- (d) 划分数据集时按同族处理。

**唯一最值得先做的下一步**：在当前派生镜像上用 RH2 回放评分，跑三个候选：

| 候选 | 做法 | 预期得分 |
| --- | --- | --- |
| CE1 | 按消息去重 | 0 |
| CE3 | 按 slug 去重，用独立集合；作正对照 | 1 |
| CE4 | 过粗：第一次 once 之后，所有 once 警告都不显示 | 1 |

目的是把误拒和漏测从静态推断变成执行证据，再据此提交题面修订提案。

## 附录：证据位置与 gold 细节

- 隐藏测试：`runs/r2e_static_prep_20260924/v2/private/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/hidden_tests/test_1.py:542-549`。同目录下还有 `gold.patch` 和 `expected_output.json`（sha256 `c65a3c08…`）。
- 当前材料的运行（`run_refs.json` 中 `material=current` 的 4 行）：
  - `runs/r2e_rf_20260923/remote/ledger_r2e_all_{noop,gold}.jsonl` 第 7 行；
  - `runs/r2e_env_repair_20260924/_rerun2/ledger_{noop,gold}.jsonl` 第 7 行；
  - 以及对应的 `.eval.log`，sha256 已核对。
- M3 参考运行（来源镜像）：
  - `runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl` 第 23、70 行；
  - `runs/env_overnight_20260916/M3/facts/5dbbe1430c16/noop_x2/out{1,2}.txt`；
  - `runs/env_overnight_20260916/M3/gold_ledger/logs_r2e/coveragepy/5dbbe1430c16/gold/a1/git_gold.diff`，与 `gold.patch` 逐字节相同。
- 来源原始行：`docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/raw/r2e_gym_subset_48_e8b9fcbc.jsonl` 中本题这一行的 `modified_files`、`commit_message`（"Warnings can be marked to only display once."）和 `prompt`。
- 解题侧的镜像层面证据：`runs/r2e_env_repair_20260924/p1/dev_probe/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/{dev_probe.json,agent_probe.log}`。
- gold 的三个副作用：
  - **G1**：依次执行 `_warn("a", slug="x")`、`set_option("run:disable_warnings", ["y"])`、`_warn("b", slug="y")`。base 不显示 `b (y)`，gold 会显示。
  - **G2**：某个 slug 以 once 方式显示过之后，同一 slug 的非 once 警告也会被压掉。
  - **G3**：`once=True, slug=None` 会把 `None` 记入列表，之后所有不带 slug 的警告都被压掉。

  G2、G3 在当前代码中没有调用点触发，所以只是潜伏行为。
- 同族证据：同批另外 4 题公开 worktree 的 `coverage/control.py`。016af5f6、97997d2c、f5eb5f21 在 `337-361` 行有相同的 `_warn`，首个 `once=True` 调用者在 `589` 行；ea6906b0 对应 `355-381` 行和 `620` 行。
