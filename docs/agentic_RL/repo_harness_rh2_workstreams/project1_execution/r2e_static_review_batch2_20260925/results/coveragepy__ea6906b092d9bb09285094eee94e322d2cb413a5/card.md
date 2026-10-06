# coveragepy__ea6906b0 审查卡（static_review，2026-09-25）

## 1. 题目与建议用途

- **题目目标**：生成 HTML 覆盖率报告时，在输出目录写一个 `.gitignore`，让 git 忽略该目录的全部内容。
- **版本**：base `7fd1ea39`（coverage 6.1a0），派生镜像配方 `r2e_derive_v1`，没有材料修订。
- **gold**：只改 `coverage/html.py::make_local_static_report_files`，写入 `"# Created by coverage.py\n*\n"`。
- **建议用途**：`development_diagnostic`，可作低难度的链路或开发诊断候选。
- **使用限制**：目标检查只验"文件存在"，比题面宽松；不宜当作能区分能力的评测题；用于 reward 时要注明这一点。

## 2. 关键需求—测试映射

| 需求或旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖 | 执行证据或下一步验证 |
| --- | --- | --- | --- | --- |
| 生成报告后输出目录里有 `.gitignore`（API，默认目录） | 题面 Expected Behavior | 6 个 `HtmlDeltaTest` 目标键 → `assert_htmlcov_files_exist` 的 :147 `assert_exists("htmlcov/.gitignore")`，即 `os.path.exists` | 覆盖（只测存在） | noop 两次 FAILED、gold 两次 PASSED（R-f 与 envrepair 日志） |
| 内容要忽略全部文件 | 题面 "ignores all its contents" | 无 | **缺失** | C-B |
| CLI 路径、非默认目录 | 由 `cmdline.py:636-645`、`control.py:950-987` 推知 | 无；`HtmlGoldTest` 只能在实现写错目录且因此崩溃时发现问题 | 缺失 / 部分 | C-E |
| 原有页面、静态文件、增量写入、返回值、无数据报错 | 公开旧测试 | 40 个回归键，与公开 `tests/test_html.py` 逐字相同 | 覆盖 | base 与 gold 都通过 |
| 成功时 stdout 不多出消息 | 公开 `test_process.py` / `test_plugins.py` | 不在隐藏集中 | 缺失（公开测试可查） | 公开命令在 base 上 rc 0 |

## 3. 八方面：已查与未查

| 方面 | 已查 | 未查 |
| --- | --- | --- |
| 公开需求 | 题面有两处小瑕疵，都不影响理解：示例写成模块级调用；"被 git 跟踪"的说法不准确 | 模型实际消息里有没有 `public_hints`（共享机制，未知） |
| 材料与初态 | 摘要、blob、隐藏测试树都已核对；noop 失败位置就是题面描述的问题 | — |
| 测试是否测到要求 | 隐藏测试 = 公开测试 + 1 行；6 个目标键实际只测一件事 | — |
| 误拒 | 合理变体（覆盖或保留已有文件、改写入位置、换内容写法）都预计通过；只有替身签名这一条公开可见的约束 | 均未实跑 |
| 回归与 gold | gold 正确；无条件覆盖已有 `.gitignore`，这一风险未被测试 | xml、json、annotate 没读，本题也不要求 |
| 开发条件 | 正式路径、真实 CC、agent 身份下，复现命令和原样公开测试（base 上 46、7、2+1 个点）都 rc 0；无 pip、无网络 | 真实模型与 Qwen adapter 未验 |
| 交付与评分 | 候选只改非测试源码，不会被控制面剥离；正式导出用 census，不经 git | 本题候选的正式导出未实跑；`tests/` 下的 base 辅助可被改动并重放（共享缺口） |
| 题目关系 | 本题初态包含 5dbbe143、97997d2c、f5eb5f21（很可能还有 016af5f6）的修复；本题修复不在其它题里 | 016af5f6 那一对只有测试函数名线索 |

## 4. 具体问题与证据级别

- **中：目标检查宽松**（清单 25、32）。只要 `htmlcov/.gitignore` 这个路径存在就能拿 1。证据是静态推断，置信度高；决定性事实见 `H/test_1.py:147` 与 `tests/coveragetest.py:276-279`。
- **低：公开可见的实现约束**（24）。在 `coverage/html.py` 里用 `open(..., encoding=...)` 会让 7 个 `HtmlDeltaTest` 键报 `TypeError`；公开测试同样失败，所以不算误拒。
- **低：gold 风险**（26）。gold 会无条件覆盖用户已有的 `.gitignore`（比如 `-d .` 的情况）；未被测试，不影响得分。
- **共享机制**：
  - 3：hints 能否进入模型消息，未知；
  - 31：`tests/coveragetest.py` 等 base 辅助可被改动并重放；
  - 5：同族划分需要处理。
- **环境修复**：本次引用的条件已覆盖。历史的"无 pip"条件已经写进 v3 hints；此前的 rc=4 是命令伪影，补跑后已消除。

## 5. 给协调者实跑的候选

每条都可以直接改成补丁；除 C-A 外都在 gold 的基础上改。

- **C-A（合理替代，正对照）**：
  - 改法：在 `coverage/html.py` 的 `HtmlReporter.report()` 开头、`self.incr.read()` 之前加一行 `self.directory_was_empty = not os.path.isdir(self.directory) or not os.listdir(self.directory)`；在 `self.make_local_static_report_files()` 之后加：若 `self.directory_was_empty`，就用 `open(os.path.join(self.directory, ".gitignore"), "w")` 写 `"*\n"`（不用 gold 的写法）。
  - 预期：**1**（46/46），没有不符的键。
- **C-B（错误实现，负对照，检验宽松判定）**：
  - 改法：在 `coverage/html.py` 的 `make_local_static_report_files()` 里，STATIC_FILES 循环之后只加一行 `open(os.path.join(self.directory, ".gitignore"), "w").close()`，写出的是空文件，什么都不忽略。
  - 预期：**1**（46/46），没有不符的键。得 1 就确认存在"错误实现也拿满分"的漏测。
- **C-C（公开约束对照）**：
  - 改法：与 gold 相同，只是改成 `open(os.path.join(self.directory, ".gitignore"), "w", encoding="utf-8")`。
  - 预期：**0**。不符的键是 `HtmlDeltaTest` 全部 7 个，都会从 PASSED 变成 FAILED，原因是 `TypeError`：
    - `test_html_created`
    - `test_html_delta_from_source_change`
    - `test_html_delta_from_coverage_change`
    - `test_html_delta_from_settings_change`
    - `test_html_delta_from_coverage_version_change`
    - `test_file_becomes_100`
    - `test_status_format_change`
  - 其余 39 个键 PASSED。
- **C-E（可选，写错目录的负对照）**：
  - 改法：不改 `html.py`；把 `coverage/control.py::Coverage.html_report` 里的 `return ret` 移到 `with override_config(...)` 块之后，并在块外、`return` 之前用 `open(os.path.join(self.config.html_dir, ".gitignore"), "w")` 写 `"*\n"`。离开 `with` 块后 `html_dir` 已恢复为默认的 `htmlcov`，所以会写错目录。
  - 预期：**0**。不符的键是 `HtmlGoldTest` 的 13 个：`test_a`、`test_b_branch`、`test_bom`、`test_isolatin1`、`test_omit_1` 到 `test_omit_4`、`test_other`、`test_partial`、`test_styled`、`test_tabbed`、`test_unicode`，都会 FAILED，原因是 `FileNotFoundError`（`htmlcov/` 不存在）。
  - `test_omit_5` 会通过，因为它的目录来自配置文件。目标键都通过。
  - 结果能说明：非默认目录只在实现崩溃时才会被回归键间接抓到。

## 6. 静态建议与下一步

- **处置**：`needs_review`，理由是"静态候选，待 actor 验证（真实模型 / adapter 未验）；目标检查只验存在性"。这不是题意或测试争议，不需要改题就能用于开发诊断。
- **可选修订（需用户决定，属于测试标准变更）**：补一条语义断言，要求 htmlcov 里除 `.gitignore` 外的所有生成文件都能被 `git check-ignore` 命中。
  - 这样 `*`、`/*`、`**` 以及加 `!.gitignore` 的写法都能通过，C-B 会被拒；
  - 修订后要用 C-A 与 C-B 做正反校验；
  - 先确认评分用户在评分镜像里能用 git。
- **与历史的分歧**：09-24 环境审查的结论 `environment_qualified` 在环境范围内成立。但它的 R16 只核对了"目标键与题面对应"，没有发现目标断言只查存在性；它当时用的开发验证证据 `tests/test_annotate.py` 与本题无关，现在已被 `tests/test_html.py` 的正式路径证据取代。
- **唯一最值得先做的下一步**：用正式评分实跑 C-B，同批带上 C-A 和 C-C。
