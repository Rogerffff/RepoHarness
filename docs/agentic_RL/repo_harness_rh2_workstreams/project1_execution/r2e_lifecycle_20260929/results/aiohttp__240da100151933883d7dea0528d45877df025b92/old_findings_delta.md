# 旧结论核对与改判记录：aiohttp__240da100151933883d7dea0528d45877df025b92

- 角色：R2E 私有主审，第 7 步后半，2026-09-29。前稿是本目录的 `analysis_before_history.md`（读历史前保存，协调者已原样存档）。本文路径都相对仓库根；`HIST` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924`，`LIFE` = `runs/r2e_lifecycle_20260929`。
- 本步新读的材料：
  - 历史引用（`runs/r2e_static_prep_20260924/v3/history/aiohttp__240da100151933883d7dea0528d45877df025b92/refs.json` 所列）：
    - `HIST/tasks/aiohttp__240da100…/` 下的 `findings.md`、`screening_record.json`、`facts.json`；
    - `HIST/known_issues.json` 中本题所在的 5 个族，以及 `expected_provenance_mixed` 条目；
    - `HIST/decisions.md`、`HIST/results_20260924.md`、`HIST/repros/aiohttp__240da100….py`、`HIST/packages/p1/README.md`。
  - 今晚新机器的实跑：
    - `LIFE/env_verify/ledger_{noop,gold}.jsonl` 第 3 行；
    - `LIFE/devcheck/aiohttp__240da100…/` 下的 `orig/attempt.json`、`orig/captures/*.out`、`orig/stub/requests/messages_000.json`、`devcheck.log`、`private_control.json`；
    - `LIFE/inv/aiohttp_240d/` 下的 `ledger_{DG1,WR1,AL1,SC1}.jsonl`、`logs_*/*.eval.log`、`aiohttp_240d_*.patch`、`pcheck_*.json`、`private_check_9_2.py`、`run.sh`。
  - 以下不作证据：`pcheck_try1/`（协调者已说明无效），`_old_noenv_*`（只作参考，未读）。
- 当前环境身份：
  - 派生镜像 `rh2-r2e-derived/aiohttp:240da1001519-r2e_derive_v1s`，image `sha256:a6dee334…`，配方 `r2e_derive_v1+sysconfig_v1`（`sha256:e2e17bf1…`）。
  - grader profile `sha256:3ec1bfa8…`：2 CPU / 4 GiB / `/tmp` 1 GiB / `deny_all` / uid 54322；预算 900/3600 s。
  - 本题材料 v3–v5 逐字相同，没有修订。
  - 四个候选运行的补丁摘要与我前稿附录 B 的补丁逐字一致：DG1 `efa10536…`、WR1 `b8b809c1…`、AL1 `a2e5e694…`、SC1 `ab0d861d…`。

## 1. 旧主张逐条核对

| # | 旧主张（出处） | 结论 | 决定性证据 |
| --- | --- | --- | --- |
| 1 | 处置 `environment_qualified`："环境支持本题的解题与判分"（`HIST/tasks/…/findings.md:3`；record `disposition`） | **环境层确认；作为用途结论已过时** | 新镜像上 noop 0（32/33，只差目标键）、gold 1（33/33）：`LIFE/env_verify/ledger_noop.jsonl:3`、`ledger_gold.jsonl:3`。devcheck 全部命令符合预期。但这是 09-24 环境审查的状态词（E03 / E11），只说明环境可用。按统一标准 v1，本题测试层有 S1，处置改为 `needs_repair` |
| 2 | "缺口：无影响判分的缺口"（`findings.md:12`） | **按 v1 口径推翻** | 旧审查只查环境，没评测试强度。唯一目标断言就是题面示例；退化候选 DG1 正式评分 1.0，33/33（`LIFE/inv/aiohttp_240d/ledger_DG1.jsonl:1`）；WR1 也得 1.0（`ledger_WR1.jsonl:1`）。私有对照证明两者都违反公开要求（`pcheck_DG1.json`、`pcheck_WR1.json`） |
| 3 | noop 0 只差目标键、gold 33/33、入口 rc=1 属正常、重复一致（`findings.md:6`；R02 / R08 / R13 / R15） | **确认** | 旧证据 3+3 次；新镜像又 1+1 次。四个候选运行里两个死键的状态也都一致 |
| 4 | R06：两个期望 FAILED 键是 2014 年代码在 3.9 上本就会失败；"要翻成 PASSED 需要同时修多处，顺手改到的概率低"（`findings.md:7`；record `R06`） | **确认；由推断升为执行证据** | SC1（gold + 给 `TCPConnector._create_connection` 加 `@asyncio.coroutine`）正式评分 1.0。`test_tcp_connector` 的失败原因从 `TypeError`（connector.py:290）变成 `AttributeError`（protocol.py:650），状态仍是 FAILED（`LIFE/inv/aiohttp_240d/logs_SC1/evallog_replay-r2e-inv-240d-SC1-_68d7cf9a.eval.log:94, 250`）。`HIST/known_issues.json` 的 `expected_non_passed_keys` 族说"多数死键不会被合法修复翻转仍是推断"；对本题最可能出现的顺手改动，现在有了实测支持 |
| 5 | 公开复现：顶层导入 `ClientRequest` 报 ImportError；真实连接在 3.9 上 TypeError；mock 父类连接后能复现端口丢失（`findings.md:8`；R03；`HIST/repros/…py`） | **确认** | devcheck 以 agent 身份、走正式启动路径：`orig/captures/literal_example_probe.out` 出现 ImportError 和 TypeError，`req.path` 仍是 `'/path'`；`repro_port_mocked.out` 在 base 上退出 1，两条题面用例都得到 `'http://localhost/path'`；私有 gold 对照同一命令退出 0（`private_control.json`） |
| 6 | 公开测试：`tests/test_client.py` 在 647 行 SyntaxError；`tests/test_connector.py` 30 passed / 2 failed（`findings.md:9`；R09） | **确认** | devcheck：`public_client_file_collect.out` 显示 647 行 `asyncio.async`，Interrupted，rc 2；`public_connector_file.out` 为 2 failed、30 passed；`public_proxy_tests.out` 为 13 passed |
| 7 | 脏树来自来源镜像的兼容改写，保留了 `loop=`，没有修复痕迹（`findings.md:10`；R17） | **确认** | devcheck `attempt.json` 的 `image_facts.initial_worktree` 与 `env.out`，porcelain 都是 6 行；gold 只改 connector.py |
| 8 | R17 / R07：HEAD 没有子提交，refs / reflog / stash 都为 0，`fix_present=no`；agent 读不到私有目录，工作区里没有 `r2e_tests` | **在新镜像上确认** | devcheck 的 `git_sanitize`：`REFS_REMAINING=0`、`REMOTES=0`、`REFLOG_ENTRIES=0`、`UNREACHABLE_OBJECTS=0`，历史 366 条前后不变；预检三项都 ok。这也关闭了我前稿 §6 里"答案是否可达"的待验项 |
| 9 | R05（issue）：Python 3.9.21、pytest 8.3.4、没有 pip、`/testbed` 要在 `sys.path` 上；目标测试用 mock，不受影响 | **确认** | devcheck `env.out`：uid 54321、`VIRTUAL_ENV=/testbed/.venv`、`No module named pip`、pytest 8.3.4、aiohttp 从 `/testbed/aiohttp/__init__.py` 导入 |
| 10 | 建议把解题侧条件写进题包或提示（`findings.md:15`；`HIST/decisions.md` E10） | **大部分已落实，原建议已过时** | v3 的 `public_hints` 已经写明：`.venv`、无网、pip 可能没有、在 `/testbed` 用 `python -m pytest`、只跑单个文件或模块（`runs/r2e_static_prep_20260924/v3/public/aiohttp__240da100…/public_bundle.json`）。只差"放在 /testbed 以外的脚本要设 PYTHONPATH"这一条，影响很小：CC 的 Bash 默认 cwd 就是 `/testbed`，devcheck 的全部命令在这里都正常 |
| 11 | 旧 facts 记 `public_hints_mention_conda: true` | **过时** | v3 提示已换成 R2E 措辞（环境卡 §2） |
| 12 | "不修来源镜像的改写（会改变期望 FAILED 键的语义，属于材料修订）"（`findings.md:16`；`HIST/packages/p1/README.md:59`） | **确认** | 与本轮"R-a 可选"一致；SC1 得 1 说明最可能出现的顺手改动不会受罚 |
| 13 | R04："来源镜像既有的脏改动属于基线，正式链按基线 census 求 delta，不会卷进候选补丁"（原文注明"代码阅读，未经真实 rollout 验证"） | **仍未核实，但有旁证** | 本轮候选走的是 `patch:` 重放路径：以 agent 身份应用补丁 → 冻结 / 投影 → fresh grader。投影只含候选改动的文件（DG1 / AL1 / SC1 是 connector.py，WR1 是 client.py），脏树的三个文件都没进投影。这支持原主张，但不是真实 CC 编辑后的导出；devcheck 本身没改文件（post_run 的 git status 仍是 6 行） |
| 14 | R12：峰值约 171 MB，测试约 1 s | **确认** | 新镜像峰值仍约 171 MB；测试阶段 2.0–2.7 s（新机器 CPU 较慢）；grader 全程约 26 s（noop / gold）、35–41 s（候选），按账本 `phases` 相加 |
| 15 | `known_issues.json` 的 `expected_provenance_mixed` 族："期望与来源宿主机执行记录逐键相同" | **未核实** | 本轮没有读来源的原始执行记录；这不影响本题结论 |
| 16 | `solver_conditions.network`：`--network none` 下仍保留回环接口 | **本题不适用，未核实** | 本题各阶段都不需要网络。devcheck 走正式的隔离网络加 relay，没有单独测出网 |

## 2. 我前稿的判断与实跑结果

| 前稿判断（`analysis_before_history.md`） | 实跑结果 | 是否改判 |
| --- | --- | --- |
| DG1 预测得 1 → 命中 T2b（§9.1） | 正式评分 1.0（33/33）。补丁经 git_apply 应用（APPLY_RC=0），投影为 connector.py，目标键 PASSED（`logs_DG1/…eval.log:213`）。pcheck 在两个 8080 端口的 URL 上报 BAD，端口照样丢失，正是题面描述的症状 | 不改判。T2b 由待定变为已证实 |
| WR1 预测得 1 → 第 4 步 S1 | 正式评分 1.0，投影为 client.py（`logs_WR1/…eval.log:212`）。pcheck 显示 `req.host` 变成 `'localhost:1234'`，直连 `TCPConnector` 的目标变成 `('localhost:1234', 1234)` | 不改判，已证实。https CONNECT 目标被破坏仍只是源码推断，pcheck 没有测 https |
| AL1 预测得 1，说明没有误拒 | 1.0；pcheck 全部 OK | 不改判 |
| SC1 预测得 1，tcp 键的失败原因变成 AttributeError | 1.0，失败原因正是 `protocol.py:650` 的 AttributeError | 不改判；R-a 保持可选 |
| §9.3 列出的 devcheck 预期 | 全部符合：13 passed；30 passed / 2 failed；rc 2；ImportError + TypeError；repro 在 base 上 rc 1，私有 gold 对照 rc 0 | 不改判。P4 由"静态推断加评分侧旁证"变为 actor 侧实测 |
| 答案是否可达（§6 待验） | git 净化的各项计数都为 0，预检 ok | 关闭 |
| actor 条件全部"待 devcheck" | uid 54321、解释器前缀、无 pip、pytest 8.3.4、`/rh2/bash_env` 对 agent 不可写、预检三项 ok，都已实测 | 关闭（限新镜像） |
| 模型实际收到的消息 | devcheck 用的是固定的 devcheck 提示：`orig/stub/requests/messages_000.json` 里的用户消息只有 "Devcheck run: execute exactly the tool calls you are given, then stop."；真实题面的渲染仍没有捕获 | 仍未知（批次共性） |
| 暂定处置 `needs_review` | 运行条件已核实，缺陷可复现 | **改为 `needs_repair`**。理由：定义文件 §4 中 `needs_review` 用于语义分歧或证据不足；现在测试层缺陷已由正式评分复现，修法是预授权的 R-c，更符合 `needs_repair`（"已有可复现的……材料缺陷，记录修复与影响范围；保留原结果，新变体另验"） |

## 3. 结论

- 严重度维持 S1，根因有三条：T2c（静态判定）、T2b（DG1 实跑命中）、v1 §4 第 4 步的 T2（WR1 实跑命中）。
- 历史记录没有改变我的判断。它的环境事实与本轮实测全部一致，而且补上了"死键为何失败"与"脏树由来"的独立来源。
- 旧的 `environment_qualified` 在环境层继续成立，新镜像（`+sysconfig_v1`）复验一致；但它不构成训练资格。
