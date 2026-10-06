# coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5：旧主张对照（old_findings_delta）

- 角色：R2E 私有主审，2026-09-25。本文写于 `analysis_before_history.md` 保存之后。
- 历史来源（按 `v3/history/.../refs.json`）：09-24 环境审查的
  - `tasks/coveragepy__ea6906b0…/{findings.md, screening_record.json, facts.json}`
  - `known_issues.json`（族 `solver_condition:no_pip_in_venv`）
  - `decisions.md`、`results_20260924.md`、`packages/p1/README.md`
  - `repros/coveragepy__ea6906b0….py`
  - 另外打开了记录里引用的原始探针 `runs/r2e_env_repair_20260924/p1/dev_probe/coveragepy__ea6906b0…/dev_probe.json`。
- 新证据：协调者补跑的原样 pytest，位于 `runs/r2e_actor_20260925/devcheck/coveragepy__ea6906b092d9bb09285094eee94e/plainpytest/`。
- 历史审查的范围是**环境资格**，使用 R01–R20 编号，不做题意与测试强度审查。所以下面区分两类："旧主张被推翻"和"旧审查没覆盖到的新问题"。

## 1. 逐条对照

| # | 旧主张（出处） | 判定 | 新的决定性证据 |
| --- | --- | --- | --- |
| 1 | noop 为 0，6 个目标键都是 `HtmlDeltaTest.*`，失败原因都是 `.gitignore` 不存在；gold 为 1（46/46）（findings、R02、R16） | **确认** | 我复读了 R-f 的 noop / gold 日志（sha `91b121d3…` / `65fc3529…`）：noop 第 44 行是 `AssertionError: File 'htmlcov/.gitignore' should exist`，第 387–393 行 `6 failed, 40 passed`；gold 第 171 行 `46 passed` |
| 2 | 同条件重复两次，reward 与差异集合都一致（R13） | **确认** | envrepair 复跑日志 `3015bf0e…`（6 failed / 40 passed）和 `e7aa5e11…`（46 passed）；四个账本第 9 行的 reward 与 `expected_match` 一致 |
| 3 | 与 M3 加 09-09 的 5 份参考日志对账全部一致（R15） | **部分核实** | 我只读了 M3 的两份 gold 日志（`67bd5291…`、`bf8ea1e1…`，都是 46 passed）。`reconcile.json`、09-09 日志和 M3 的 noop 日志没有打开，这部分记**未核实** |
| 4 | venv 没有 pip，uv 不在 PATH，不联网；分类 `solver_condition`（findings、R05、R10、known_issues） | **确认** | devcheck `orig` 与 `plainpytest` 的 `env.out`：`No module named pip`；prelaunch 显示 `DNS_EXTERNAL=DENIED` |
| 5 | 公开提示写着"`pip` already points at it"，并带 conda 措辞（known_issues 的 solver_hints 族；facts `public_hints_mention_conda: true`，E09） | **过时** | v3 公开包的 `public_hints` 已改为 `.venv`、"`pip` may be unavailable"、不联网、`python -m pytest`（`public_bundle.json`）。这条已按环境卡 §2 修正。至于提示能否进入模型实际消息，是新的未知项，见 #13 |
| 6 | Python 3.7.9、pytest 6.2.5 加 xdist；coverage 是 editable finder 安装，在 `/tmp` 下也能导入；有 git、gcc、make（R05） | **确认**（gcc / make 未复核） | 正式启动路径的 devcheck：`cwd=/` 下导入 `/testbed/coverage/__init__.py`，有 `/usr/bin/git`，`pytest 6.2.5`，`import xdist, flaky` 成功。本题不需要 gcc 和 make |
| 7 | 公开测试证据是 `tests/test_annotate.py`：收集 4 个，rc 为 0（R09、solver_conditions.public_tests） | **过时**（证据不对题） | 那是与本题无关的测试文件，而且当时不是正式启动路径（探针 `activation=none`，临时探针容器）。现在已被取代：<br>• 正式路径、真实 CC、agent 身份下，原样 `python -m pytest --color=no -rfE tests/test_html.py -q`：46 个点，rc 0；<br>• `-k HtmlDeltaTest`：7 个点，rc 0；<br>• `tests/test_process.py -k UnicodeFilePathsTest`：2 个点；`tests/test_plugins.py -k test_local_files_are_importable`：1 个点，均 rc 0（`plainpytest/captures/*_plain.out`）；<br>• `-o addopts=""` 版本：46 passed（`orig/captures/pr5_6_pytest.out`） |
| 8 | 按公开题面复现，`REPRO_OBSERVED=1`（R03、repro 脚本） | **确认，并补强** | devcheck 的 C2 / C3 在 agent 身份下复现了"没有 `.gitignore`"，`git status` 列出 8 个 `??`；私有 gold 对照写出 `# Created by coverage.py\n*\n`，`git status` 对 htmlcov 无输出，说明复现命令能区分修复前后 |
| 9 | 控制面只有 `r2e_tests/` 加 `run_tests.sh`；gold 只动 `coverage/html.py`；"解题不需要改 r2e_tests 以外的测试辅助文件"；正式链按 census 求 delta（R04，代码阅读） | **确认，并补一个缺口** | `r2e_grading_scripts.py:274-279`（`test_globs=()`）；`generate.py:3479` 用 `export_frozen_patch`（census，不经 git）。<br>补充：隐藏测试导入的 base 辅助（`tests/coveragetest.py` 的 `assert_exists`、`tests/goldtest.py`、`tests/gold/html/*`）不在控制面内，候选改了会被重放；平台已登记这类缺口（`trusted_projection.py:18-20`）。旧的"pass"没有写出这个具体入口 |
| 10 | agent 可写 `/testbed`、site-packages、home、`/tmp`，不可写根文件系统，隐藏测试读不到（R07） | **确认** | 探针原件：`WRITE_SITE=ok`、`WRITE_VENV_BIN=ok`；devcheck 运行后 `.venv/.../_pytest/__pycache__` 出现新文件；`RH2_PREFLIGHT_HIDDEN_TESTS=ok`。补一句：census 排除 `.venv/`，所以 `.venv` 里的改动不会交付 |
| 11 | 6 个目标键与题面对应，R16 为 pass | **映射确认；覆盖强度问题是新增** | 对应关系成立。但隐藏测试相对公开 `tests/test_html.py` 只多一行 `self.assert_exists("htmlcov/.gitignore")`（`H/test_1.py:147`，本地 diff），而 `assert_exists` 就是 `os.path.exists`（`tests/coveragetest.py:276-279`）。<br>所以题面要求的"ignores all its contents"、CLI 路径和非默认目录都没有断言；空 `.gitignore` 预计也能拿 1（静态推断，待 C-B 实跑）。<br>旧审查不负责题意，这不算推翻它，而是它没覆盖到的问题 |
| 12 | 没有修复痕迹：HEAD 无子提交，refs、reflog、stash、remote 都为空（R17） | **确认** | devcheck 预检 `RH2_PREFLIGHT_GIT_HISTORY=ok`，prelaunch 的 `GIT_REFS/REFLOG/REMOTES=0`。packfile 里的对象没有逐个查（共享机制） |
| 13 | 解题侧条件（无 pip、无网络）应写进题包或系统提示（findings 建议，E10） | **已部分落实；新的未知项** | v3 hints 已包含这些条件。但 `render_user_prompt` 不含 hints（`envpack/bundles.py:282-289`）；按环境卡，hints 只写进容器的 `/rh2/public_task_bundle.json`；两次 devcheck 的首条用户消息都是 devcheck 指令。模型能否看到 hints：**未知**（共享机制） |
| 14 | 期望里没有非 PASSED 键（R11 不适用）；没有资产目录（R06 不适用） | **确认** | `expected_output.json` 46 个键全是 PASSED |
| 15 | 资源：峰值 357 MB / 4 GiB，测试约 2 s（R12） | **确认** | 四个账本第 9 行：`mem_peak_mb` 357–368，`test.seconds` 2.06–2.37 |
| 16 | 每次都是新容器；基线里 `coverage/__pycache__` 的 33 个文件被 census 剪掉，前后不变（R14） | **未核实** | 本审没有打开 diagnostics 与 `omitted_cache_count`；不影响结论 |
| 17 | "venv 无 pip"只适用于本镜像，另外 4 道 coveragepy 题有 pip（R20、results 表） | **未核实** | 没查其它题的镜像；与 known_issues 的列举一致 |
| 18 | 处置 `environment_qualified`（results_20260924） | **在其范围内确认；静态处置另记** | 环境资格证据成立，而且 actor 侧现在有正式启动路径的证据。本审的静态处置是 `needs_review`，理由是：目标检查只验存在性，比题面宽松；真实模型 / adapter 链路未验。两者范围不同，不冲突 |

## 2. 旧审查没有覆盖、本审新增的问题

1. **目标检查宽松**，对应 40 项清单的 25、32。空文件、`*.html` 这类错误内容，以及只写到默认目录并顺手建目录的实现，都会得 1（静态推断）。决定性证据见上表 #11；实跑见 card 中的 C-B。
2. **公开可见的实现约束**，对应 24。测试替身 `FileWriteTracker.open(self, filename, mode="r")`（`H/test_1.py:104`，在 :136 patch 进去）会让 `coverage/html.py` 中带 `encoding=` 的 `open` 在 7 个 `HtmlDeltaTest` 键上报 `TypeError`。公开测试同样会失败，所以不算隐藏测试独有的误拒（见 C-C）。
3. **gold 的边界风险**，对应 26。gold 无条件覆盖输出目录里已有的 `.gitignore`，例如 `-d .` 会把用户项目根目录的 `.gitignore` 换成 `*`。测试不涉及，也不影响得分（静态推断）。
4. **同仓包含关系**，对应 5。本题初态包含 5dbbe143、97997d2c、f5eb5f21 的 gold 行（`cross_task_gold_scan.json`；另抽查了 `coverage/control.py:355` 与 `coverage/jsonreport.py:65-66`），还可能包含 016af5f6 的修复（test scan 线索）。反过来，本题的修复不在任何其它题的初态里（5 个工作树 grep `gitignore` 均无命中）。划分训练 / 评测时应按同族处理。

## 3. 我对自己初判的修改

- **撤销一项未知**：初判把"原样 `python -m pytest tests/test_html.py` 和 C6 在 actor 下能否跑"列为未知。现在补跑证据显示三条命令在正式路径、agent 身份下都 rc 0。
  - 这三条都跑在 base 上（没加修复），证明的是开发验证路径可用，不证明任何修复能通过。
  - 当初的 rc=4 确认是协调者插入 `-p no:cacheprovider` 造成的伪影。
- **处置不变**：历史材料里没有证据改变"误拒风险低、目标检查宽松"的判断，暂定处置保持 `needs_review`（静态候选）。
- **措辞修正**：初判称"历史 dev 证据未知"。实际上旧探针确有 `WRITE_SITE=ok`，与我从 devcheck 推出的 `.venv` 可写一致，现在记为确认。
