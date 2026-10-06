# scrapy `9a15fcf8` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`F` = `runs/r2e_lifecycle_20260929/formal_v4`，`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v4/scrapy__9a15fcf89a151811de8ac783419df0512c863d5e`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：probe_ready**。五条都满足：正式评分 5 行全部与期望一致（正对照 gold）；devcheck 13 项全真；原来锁成 FAILED 的两个死键已按 R-a 删除，另两处 S1 按 R-c 补齐，经 Codex 复核与正式评分验收；预检通过。
- **材料**：修订单 v4 的 `r2e-mr-031`（`hidden_test_text_replace`，`test_1.py` `5a84fa9f…` → `bb261b3d…`，删 `test_from_headers`、`test_from_args`，加 `test_from_content_type_x_json`）、`r2e-mr-032`（`hidden_test_file_add`，`test_2.py` `686d5738…`，与公开 `tests/test_http_headers.py` 逐字相同）、`r2e-mr-033`（`expected_file_replace`，`2fefa8a5…` → `759f98e0…`：删 2 键、加 18 键，7 → 23 键，全部 PASSED）。pins v5 `2324c4c4ab82…`，v5 逐字保留。派生镜像 `e46e3f653558`（`rh2-r2e-derived/scrapy:9a15fcf89a15-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `bf7b7f3614bf…`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-031/032/033`），不当原 benchmark 报。

## 准入五条（README §3）

1. **正式评分**（`F/ledgers/ledger_{gold,noop,s1,s2,s3}.jsonl` 第 7 行；`F/status.json` 本题 5 行 `match=true`）：

   | 候选 | 角色 | 期望 | 实得 | 不符键 |
   | --- | --- | --- | --- | --- |
   | gold | 正对照 | 1 | 1（23/23） | — |
   | P4：在输入边界解码 bytes 的更完整修复 | 被纠正的误拒（原版 0） | 1 | 1（23/23） | — |
   | noop | — | 0 | 0（21/23） | `test_from_content_type`、`test_from_content_type_x_json` |
   | `bad_headers_str`：gold + `Headers.normvalue` 改返回 str | 已知错误（只做 R-a 时会得 1） | 0 | 0（10/23） | `HeadersTest` 13 键 |
   | 逐字特判示例字符串 | §4 第 3 步退化探测（原版 1） | 0 | 0（22/23） | `test_from_content_type_x_json` |

   各行 `git_apply` 成功、测试段完整、键集相等；失败键与试跑逐一相同。
2. **devcheck**：`D/orig/attempt.json` 13 项 checks 全真；5 条命令都符合预期，agent 身份下题面原例返回 `Response`（`mcve_assert` rc=1，本就预期非零）。私有 gold 对照（root）中 `test_responsetypes` rc=1 是预期内：公开 `tests/test_responsetypes.py` 的 `test_from_args`、`test_from_headers` 在 py3 下无论修不修都抛 `TypeError`，正是 R-a 从隐藏测试里删掉的那两个死键；其余命令 rc=0。
3. **S1 处理**：revision_plan §0、§1（第 7–21 行）：R-a 删两个死键（T5 → 无效断言，上游 `tests/py3-ignores.txt:40` 在 py3 下整文件忽略）；R-c-1 把公开 `HeadersTest` 17 个方法加入评分（只做 R-a 时 `bad_headers_str` 会得 1，§4 第 4 步）；R-c-2 补不带参数、带别的 charset 的 `application/x-json`（§4 第 2 步，逐字特判原版得 1）。Codex 复核通过（`L/codex_reviews/review_revision_scrapy.md` 第 27–38 行），限定：**删除死键不意味着要求 header 路径继续出错，该路径仍未覆盖，应保留登记**；17 个 Headers 方法属同一 API 既有契约，不越出 R-c。Codex 列的正式复验（第 46 行）今晚已全部与期望一致，按第 48 行本次修订验收可以核销。
4. **公开包干净**：devcheck `r2e_preflight_ok`（三项 ok）；来源镜像原先 `/r2e_tests` 可读、修复提交可达的问题已由派生镜像消除；修订只动评分包，公开包在材料 v3 → v4 之间逐字未变（`test_2.py` 本就是公开测试，不算泄漏）。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | yes | 开发路径与评分依据已核；按 `r2e-mr-031/032/033` 标明版本报告。批次运行条件属链路 |
| 训练候选 | yes | 核心要求有直接断言：原例 + 两个非示例实例（revision_plan §6 第 90 行）；当前版本 noop 0、gold 1；§4 第 2、3 步已做；S2、X1 已登记。训练价值另看：题面加表里相邻的 `application/json` 几乎点明修法，属易题 |
| 留出评测候选 | conditional | 差：① D3 仓库划分未定，本题修复出现在同仓 4 题初态（X1），只能整仓同侧；② 若探针结果用于选模型、调提示或调配方即不再符合；③ 只能作标明版本的自建评测 |

## 剩余事项（已登记，不阻塞探针）

- **S2 / T3**（revision_plan §6 第 92 行）：header 路径（`from_headers` / `from_args`、`content_encoding → Response`）没有测试；`application/json` 等其余表项没有保护，"把 `application/json` 改名成 `application/x-json`"静态推断可得 1、未实跑（旧 K1′，低）。
- **公开测试诱因（按 P6 读）**：显式跑公开 `tests/test_responsetypes.py` 会看到两个 `TypeError`，gold 下也一样。修订后改 header 路径不再被扣分（P4 得 1）；探针分析时模型改这两处不算越界，这两个公开测试失败也不算模型改错。
- **后检**：没有本题的结构化后检或命令文件；旧的 A′ 判读规则因死键已删而不再需要。
- **X1**（`runs/r2e_static_prep_20260924/cross_task_gold_scan.json`）：本题一行修复出现在同仓 `75450e75`、`a95a338e`、`cfed9b66`、`e9387529` 的公开初态。
- **解题侧条件**：无 pip、不联网；Scrapy 1.1 与 Twisted 24.11、zope.interface 7.2 不兼容，抓取类公开测试恒失败；相关公开测试要显式给文件路径才会运行（`collect_ignore`）。
- **链路**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行）：求解入口换 `r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v4 正式评分即此口径）；GPU 机须载入同一 image ID，否则本卡评分资格重出；模型实际收到的题面消息未对本题捕获；根 `conftest.py`、`pytest.ini` 在评分时生效且不重置（共享机制，旧卡 `card.md` 第 58 行）。本机开销：rollout 可信初始化约 39 s；评分 trusted setup 38–43 s（300 s 硬时限）；测试段约 3 s。

## 证据索引

- 旧卡：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/scrapy__9a15fcf89a151811de8ac783419df0512c863d5e/{card.md,screening_record.json,review.md}`（旧 usage 只有 `intended_use`；旧处置里的"待用户 T0-4"已由 v1 §9 D4 与 §10 本题一行覆盖）
- 修订：`L/results/scrapy__9a15fcf89a151811de8ac783419df0512c863d5e/{revision_plan.md,revision_draft.json,trials/,cands/}`；正式条目 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v5.json` 的 `r2e-mr-031`、`r2e-mr-032`、`r2e-mr-033`
- Codex：`L/codex_reviews/review_revision_scrapy.md` 第 27–38、40–48 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/ledger_*.jsonl`（本题均为第 7 行）
- devcheck：`D/orig/attempt.json`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v4/summary.json`
