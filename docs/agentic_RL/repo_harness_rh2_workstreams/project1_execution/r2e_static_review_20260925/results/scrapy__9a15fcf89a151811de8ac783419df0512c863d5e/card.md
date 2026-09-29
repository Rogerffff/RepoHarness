# 短卡：scrapy__9a15fcf89a151811de8ac783419df0512c863d5e

> **2026-09-25 协调者更正（按 Codex 复核 r2e_static_actor_review_20260925/README.md）**：第 91 行附近的 A′ 规则不能直接用作免责：A′ 改为筛选规则：得 0 且不符的恰好是这两个键从 FAILED 变为 PASSED、其余键都匹配时，只标'疑似过度修复误判'；再核候选是否只改库源码、是否保持公开行为契约（例：把 Headers.normvalue 改为返回 str 的错误实现也命中这个模式，但公开 HeadersTest.test_single_value 的 bytes 契约失败），核实后才记'过度修复误判'。原始 reward 保留。 以下原文保留不改。

私有主审，静态审查，2026-09-25。第二步（本卡、`old_findings_delta.md`、`screening_record.json`）由接续会话写成：原主审会话封存初判后，在读历史阶段因 API 错误中止。

本卡的暴露范围：看过 gold、隐藏测试、期望映射、P4 候选和历史记录。**不得提供给求解模型。**

## 1. 目标、版本与建议用途

**题目要求**：`responsetypes.from_content_type('application/x-json; encoding=UTF8;charset=UTF-8')` 应返回 `TextResponse`。base 下返回的是 `Response`。

**版本与环境**：
- 代码：Scrapy 1.1.0dev1，base `3fc4e0b3`，2015 年的代码，运行在 Python 3.9.21 上。
- 材料：来源版，无修订。
- 镜像与资源：派生镜像 `r2e_derive_v1`（`fe908bed…`），默认资源。

**评分键（共 7 个）**：
- 目标键 1 个：`test_from_content_type`。
- 回归键 4 个。
- 期望为 FAILED 的键 2 个：`test_from_headers`、`test_from_args`。

**建议用途**：`development_diagnostic`。
- 作 reward 之前，先做修订 **B**。
- 修订前如果拿来做诊断，按判读规则 **A′** 解读分数（见 §5）。
- 正式 actor 链目前使用来源镜像，改用派生镜像之前，这道题不能进探针。这是全池共享的问题。

## 2. 关键映射

| 需求或旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖情况 | 执行证据或下一步验证 |
| --- | --- | --- | --- | --- |
| R1：题面原例 x-json → `TextResponse` | `user_prompt.txt:10-14` | `test_from_content_type` 第 7 个映射（`test_1.py:38`，断言在 `:42`） | 覆盖 | noop 在 `:42` 失败，报错文字与题面一致；gold 通过（RH2 ×2，M3 ×2） |
| K1：html / xml / xhtml / wap / octet-stream 的映射不变 | `responsetypes.py:18-31`；公开测试 | 同一测试的前 6 个映射 | 覆盖 | 所有运行都通过 |
| K1′：`application/json` 等其余表项不变 | `responsetypes.py:20-28` | 无 | 缺失 | 反例“把 json 改名为 x-json”静态推断可得 1，未实跑 |
| K2 与 header 路径：`content_encoding` → `Response`；Content-Type / Content-Disposition 判型 | `responsetypes.py:54-55, 67-76` | `test_from_headers`、`test_from_args`（期望 FAILED，是死键：测试在断言前就抛错，不检查任何行为） | 缺失 | 两个测试都在第一个带头映射处抛 `TypeError`，noop 和 gold 下相同 |
| A2（题外）：py3 下接受 bytes 头值 | 无 | 上面两个键被期望为 FAILED | **冲突** | P4 更完整修复经真实评分：7/7 PASSED，reward 0（诊断实测） |

## 3. 八方面：查了什么、没查什么

- **公开需求**
  - 已查：题面、提示、brief、公开读者稿。原例可以从 base 源码推出。
  - 未查：实际渲染出来的消息没有捕获。
- **材料与初态**
  - 已查：各材料哈希一致；M3 显示修复提交只改了 `responsetypes.py` 和对应测试文件；noop 的失败位置与题面一致；镜像层面复现成功，并经过两次独立探针确认。
- **测试是否测到要求**
  - 已查：7 个键都追到了具体断言。
  - 结论：目标键只覆盖 str 版的 `from_content_type`。
- **是否误拒合理解**
  - 已查：更完整的修复会被判 0（诊断实测）；另外三种不同写法都能得 1（静态推断）。
- **回归与 gold**
  - 已查：gold 只加一行，没有无关改动。
  - 缺口：K1′ 和 K2 都没有有效保护（静态推断）。
  - 阅读范围：调用者只读了 grep 命中的行。
- **开发条件**
  - 已查（镜像层面实测）：解释器、没有 pip、没有网络、导入正常；显式给出路径运行公开测试，结果 5 过 2 败。
  - 未查：正式启动链上的 actor 条件（待验）。
- **交付与评分边界**
  - 已查：投影只包含 `responsetypes.py`。根目录的 `conftest.py` 和 `pytest.ini` 在评分时生效，且不会被重置，这属于共享机制。
  - 未查：没有做控制面攻击。
- **题目关系与用途**
  - 已查：题面加上表里相邻的 `application/json` 条目，几乎直接点明了修法，难度低。来源镜像存在答案通道。
  - 未查：同族题关系、预训练暴露。

## 4. 具体问题与证据层次

1. **主问题：期望把两个死键锁成了 FAILED。**
   - 失败原因：`Headers` 在 py3 下存 bytes，`responsetypes.py:56` 却用 str 去切分。
   - 进入期望的原因：上游在 `tests/py3-ignores.txt:40` 让 py3 忽略了整个测试文件；R2E 把测试搬到 `r2e_tests/`，绕开了这条忽略。
   - 后果：更完整的正确修复会被判 0；只修 content_type 的部分修复仍得 1。也就是说，分数取决于题外修复做得完不完整。
   - 证据：历史真实 RH2（诊断）、离线重算、静态推断。
2. **回归覆盖弱。** 见 K1′ 和 K2。证据为静态推断，影响较小。
3. **诱因。** 显式运行公开的 `tests/test_responsetypes.py`，就能看到这两个 `TypeError`，报错位置正是题面点名的函数。
   - 证据：历史镜像层面实测。
   - 求解者会不会因此去修，要看真实轨迹（清单 34/35）。
4. **共享问题。**
   - 正式链使用来源镜像：`/r2e_tests` 可读，修复提交可达（M3 facts）。
   - 解释器前缀默认是 conda。
   - 提示中关于 conda、pip 和“会重置测试文件”的说法对本题不成立（代码事实）。

**环境修复**：本题不需要环境配方。环境阶段已经把条件核清。T0-4 尚未实施。

## 5. 建议、分歧与下一步

**处置**：`needs_review`，原因有两条：
- 题意/测试争议；
- 共享的 actor 条件待验。

**建议**：选项按历史编号——A 不改，B 修改隐藏测试和期望，C 评分时对称忽略指定键，D 隔离；A′ 是本审查提出的判读规则。
- **B**：私有 `test_1.py` 删除这两个方法，期望同步删掉这两个键，走 `material_v2` 实施。
  - 不建议用 skip：parser 按子串识别状态，skip 理由里如果出现 `PASSED`、`FAILED` 或 `ERROR`，这一行就会被当成键。
  - 代价：修订后不再与 M3 同版本，对账时要单独列出。
- **D**：退路。
- **A′**：只用于诊断。规则是：得 0，但不符的恰好是这两个键从 FAILED 变成 PASSED，其余键都匹配，就记为“过度修复误判”。

**与历史的分歧**：
- 历史推荐 D，理由是 B 要为一题重建镜像和 pins。
- 这条成本论据已部分过时：E16 的 `material_v2` 已经建好，同仓的 `cfed9b66` 已按它修订并通过验收。
- 这两个键是死键，去掉它们不损失任何有效覆盖；而且有上游的 py3-ignores 作依据。
- 最终由用户按 T0 决定。
- 历史只提升了证据级别，没有改变处置。前稿与理由见 `old_findings_delta.md` §2。

**reviewer**：按指示没有读 `reviewer_initial.md`，由协调者收口。

**唯一优先的下一步**：用户就 T0-4 拍板，推荐 B。
- 如果选 B：在修订后的材料上跑 4 个候选，各跑 2 次，并核对键集只剩 5 个。预期如下：

  | 候选 | 预期 |
  | --- | --- |
  | noop | 0 |
  | gold | 1 |
  | P4 更完整修复 | 1 |
  | 只修 content_type 的部分修复 | 1 |

**保留项**（不能因为“只做一步”而删掉）：
- K1′ 反例，低优先级；
- 搬迁扫描补一条“原文件在 collect_ignore / py3-ignores 中”的规则；
- 正式链切换后，以 actor 身份核对开发条件。

## 附录：证据索引

**当前材料的运行：**
- R-f：
  - noop：`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-s_49e74388.eval.log`，账本 `ledger_r2e_all_noop.jsonl:45`。
  - gold：`…-all-gold-s_798f95c6.eval.log`，账本 `ledger_r2e_all_gold.jsonl:45`。
- 中央复跑：`runs/r2e_env_repair_20260924/_rerun2/`，其中 `ledger_{noop,gold}.jsonl:45`、`eval_logs/…rer_92f27267`、`eval_logs/…rer_14d83f49`。

**独立参考**：`runs/r2e_rf_20260923/reconcile_all/reconcile.json` 第 44、92 项，均来自 M3：
- noop：`runs/env_overnight_20260916/M3/facts/9a15fcf89a15/noop_x2/out{1,2}.txt`
- gold：`M3/gold_ledger/r2e_gold_m3.jsonl:31,78`

**诊断：**
- `runs/r2e_env_repair_20260924/p4/ledger_overfix.jsonl:1`
- `…/p4/eval_logs/evallog_replay-r2e-envrepair-p4-_1acaf88b.eval.log`
- `…/p4/overfix/<iid>.diff`（sha256 `81cedada…`）
- `…/p4/offline_rescore_9a15fcf8.json`

**镜像层面：**
- `…/p4/dev_probe/<iid>/agent_probe.log`
- `…/p4/targeted_public_tests/<iid>/agent_probe.log`
- `…/p4/targeted2_cmds/<iid>/agent_probe.log`
- `…/_accept/p4/dev_probe/<iid>/`

**来源镜像泄漏**：`M3/facts/9a15fcf89a15/facts/{git_fix,git_contains,r2e_tests_list}.txt`

**历史记录**：`docs/…/r2e_env_repair_20260924/` 下的：
- `tasks/<iid>/`
- `material_revisions/<iid>.md`
- `decisions.md`（T0-4、E16）
- `known_issues.json`

**评分代码**：`envpack/scoring.py` 中的 `expected_map_matches`，以及 `envpack/r2e_parsers.py` 中的 `parse_log_pytest`。两者与 `runs/r2e_snapshot_20260923.sha256` 逐字节相同。
