# datalad__19f5b450：R2E 静态审查短卡

2026-09-25 · 私有主审（静态）。详细证据见同目录的 `analysis_before_history.md`（读历史前写）与 `old_findings_delta.md`（读历史后写）。

## 1. 题目、版本与建议用途

- **题目要求**：从 CLI 调用 `datalad run` 时，如果被执行的命令以非零码 N 退出，datalad 进程也应以 N 退出。base 统一退出 1。
- **材料**：base `b07ea09`（datalad 1.1.3 之后），无材料修订，派生配方 `r2e_derive_v1`，默认资源。
- **gold**：只改 `datalad/cli/main.py::_run_with_exception_handler` 的 `IncompleteResultsError` 分支，从失败记录里取第一个非零的 `exit_code` 作为退出码。
- **建议用途**：开发诊断 / 基座探针候选（`development_diagnostic`）。这不等于批准正式训练或评测。

## 2. 关键需求—测试映射

| 需求或旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖 | 执行证据或下一验证 |
|---|---|---|---|---|
| 原例：`run --explicit 'exit 3'` 应退出 3 | 题面示例 | `test_run_exit_code`：`cm.value.code == 3` | 覆盖 | noop 两次均 FAILED（`assert 1 == 3`）；gold 两次均 PASSED，M3 参考另有两次 PASSED |
| 失败时 Python 层 `sys.stderr` 为空 | 示例用 `run_main`，其默认参数为 `expect_stderr=False` | 同一测试：`stderr == ""` | 覆盖（隐含约束） | K4 待跑，预期 0 |
| 任意 N，以及不带 `--explicit` 的情形 | 题面 Expected Behavior；`run.py:105`；`cli.rst:65` | 无 | 部分 | 私有 gold 对照：`run 'exit 3'` 退出 3。K3 预期得 1 |
| 非命令失败仍退出 1 | `cli.rst:61`（Incomplete results，exit 1） | 无 | 缺失 | 私有 gold 对照：输入缺失时退出 1。K3 预期得 1 |
| Python API 与 rerun 行为不变 | 公开 `test_run.py`、`test_rerun.py`；`CHANGELOG.md:1191` | 无 | 缺失 | gold 下 pr4 通过。K2 预期得 1 |
| `--on-failure ignore` 退出 0 | `--on-failure` 帮助文字（`common_args.py:95-99`） | 无 | 缺失 | 私有 gold 对照：退出 0 |
| 其它 CLI 退出码，以及 help、version、completion 等旧行为 | 公开 `test_main.py`，与隐藏文件只差两行导入写法 | 其余 18 个键 | 覆盖（回归） | noop 与 gold 下全部 PASSED |

## 3. 八个方面的核查范围

1. **公开需求**：已查题面、公开提示、docstring、changelog、`cli.rst`；未查模型实际收到的渲染消息。
2. **材料与初态**：已查。哈希一致；base 是修复提交的父提交；noop 在目标键上的失败原因符合题面；agent 身份下可以复现问题。
3. **测试覆盖**：20 个收集项全部读完。目标键只覆盖题面原例。
4. **误拒合理解**：只有一处精确约束（Python 层 stderr 必须为空），有公开依据。K1 与 K4 待跑。
5. **回归与 gold**：私有 gold 对照完整输出显示，C1 五例依次退出 3/3/0/1/0，console script 退出 3。gold 本身没有问题，但上表中缺失的几条都不受隐藏测试保护。
6. **开发条件**：已在正式链 devcheck 中实测，条件包括：agent uid 54321，解释器为 `.venv`，editable 安装，git、git-annex 与 console script 可用，没有 pip，不联网。git 身份缺失，需要解题者自行设置。真实模型求解未测。
7. **交付与评分**：投影与 git 清理都正常。测试辅助文件在评分时不重置（这是通用问题）。SKIPPED 键的判定依赖 stdin 不是 TTY。
8. **题目关系**：gold 不出现在同仓其它题的公开包中；另一题 58ba5165 的修复已在本题初态里。

## 4. 具体问题与证据层次

1. **测试偏窄，存在漏测**（清单 25、26、32）。证据为静态推断：隐藏测试全文里没有任何用例触发没有 `exit_code` 的 `IncompleteResultsError`，也没有用例检查 ignore 模式或 Python API。影响：reward=1 只能证明题面原例已修好。回归实现（K2）、部分实现（K3）以及硬编码 3 预期都会得 1。这对训练奖励用途影响较大；用于诊断探针时，应对通过的补丁另做公开回归复核。
2. **公开文档互相矛盾**（清单 23，静态）：docstring 说失败时仍抛 `CommandError`；0.16.0 changelog 说 Python API 改为抛 `IncompleteResultsError`；`cli.rst` 把命令失败列为转发退出码的一类。题面没有说明 Python API 是否要改，因此 K2 这条路线是可能出现的。示例的三处导入写错（历史已确认）。
3. **stderr 精确约束**（清单 24，低风险）：通过 `print(..., file=sys.stderr)` 输出说明会判 0；通过日志、`ui.error` 或 `os.write(2, …)` 输出不受影响。这一约束有公开依据。
4. **解题侧条件：缺 git 身份**（历史探针实测，本批正式链仍然如此）：不设身份时 `create` 报 `Author identity unknown`，公开提示里没有提到。不影响评分。
5. **题目关系**：本题初态已包含 58ba5165 的修复，划分数据时应把两题记为同族。

**环境修复**：不需要。引用的条件（评分用 `r2e_derive_v1` 加默认资源；解题侧用正式链 devcheck）已经覆盖本题。

## 5. 建议与下一步

- **静态建议**：`needs_review`。理由是这是静态候选，还需 actor 验证，并且测试偏窄。它与历史结论 `environment_qualified` 不冲突，后者只针对环境维度；主要分歧在测试质量和文档矛盾。
- **独立复核**：尚未进行。
- **唯一最值得先做的下一步**：用正式评分代码实跑下面的候选，其中 K2 与 K3 是关键。
  - **K1**（正对照，合理替代解）：在 `datalad/cli/main.py::_run_with_exception_handler` 的 `IncompleteResultsError` 分支中，`lgr.debug(...)` 之后遍历 `exc.failed or []`。遇到第一条 `action == 'run'`、`exception` 是 `CommandError` 且 `.code` 非零的记录时，先调用 `_communicate_commanderror(e)`，再令 `exit_code = e.code`，然后 `break`。预期 19/19，reward 1，没有不符的键。若得 0，按误拒合理解调查。
  - **K2**（沿用冲突 docstring 的回归实现）：只改 `datalad/core/local/run.py::_execute_command`，删掉其中的 `try/except CommandError`，让 `runner.run(command)` 抛出的 `CommandError` 直接向上传播；`cli/main.py` 不动。预期 19/19，reward 1，没有不符的键，即漏测成立。可选的公开侧对照：在同一镜像中应用 K2 后运行 pr4，`test_basics` 与 `test_run_failure` 应当失败。
  - **K3**（部分实现）：只在 `datalad/cli/main.py::_run_with_exception_handler` 的 `IncompleteResultsError` 分支中加一行 `exit_code = exc.failed[0].get('exit_code')`，缺字段时不回退到 1。预期 19/19，reward 1，没有不符的键。可选的公开侧对照：pr1 第 4 例（`-i does-not-exist`）的输出由 `EXIT 1` 变成 `EXIT None`，即进程以 0 退出。
  - **K4**（负对照，检验 stderr 约束）：在 gold 的 `if non0_codes: exit_code = non0_codes[0]` 之后加一行 `print(f"datalad: command exited with code {exit_code}", file=sys.stderr)`。预期 18/19，reward 0。唯一不符的键是 `test_run_exit_code`：期望 PASSED，实际 FAILED，失败在 `test_1.py:86-87`。
  - **K5**（可选，硬编码）：在同一分支中直接写 `exit_code = 3`。预期 19/19，reward 1，没有不符的键。
- **其它**：
  - 若本题要进入训练奖励，可以按公开要求补测，例如 `exit 5` 应退出 5、输入缺失应退出 1、ignore 模式应退出 0、Python API 仍抛 `IncompleteResultsError`。补测属于 T0 修订，需用户决定，并须用 gold 和 K1–K5 做双向复验。
  - 用真实模型求解一次，观察它是否走 K2 路线。
