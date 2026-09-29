# scrapy `e9387529` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`F` = `runs/r2e_lifecycle_20260929/formal_v4`，`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v4/scrapy__e938752973b4fc53e0fa0c0bc68a431613b987e4`，`C` = `runs/r2e_actor_20260925/grader_cands`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：probe_ready**。五条都满足：正式评分 6 行全部与期望一致，正对照是经独立核实的替代解 C1（v1 §5 / D4），**原 gold 在修订版上为 0，已登记**；devcheck 13 项全真；S1 已按 R-c 修订，经 Codex 复核与正式评分验收；预检通过。
- **材料**：修订单 v4 的 `r2e-mr-026`（`hidden_test_text_replace`，`test_1.py` `21ec99b1…` → `fe29720c…`）与 `r2e-mr-027`（`expected_file_replace`，`51436068…` → `447b5892…`，62 → 65 键，新增 `PythonItemExporterTest.test_export_binary_{dict_item,empty_fields,serializer_output}`）；条目 reason 写明正对照为 C1、gold 不满分。pins v5 `2324c4c4ab82…`，v5 逐字保留。派生镜像 `94a52b4ef9db`（`rh2-r2e-derived/scrapy:e938752973b4-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `f14a6ae54ce1…`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-026/027`）。修订后 gold 得 0，不能与原 benchmark 混报。

## 准入五条（README §3）

1. **正式评分**（`F/ledgers/`：gold / noop / s1 / s2 / s3 第 5 行，s4 第 4 行；`F/status.json` 本题 6 行 `match=true`）：

   | 候选 | 角色 | 期望 | 实得 | 不符键 |
   | --- | --- | --- | --- | --- |
   | C1：binary 时只把顶层键转 bytes（`C/scrapy_e938_C1_bytes_keys_when_binary.patch`） | 正对照（替代解，D4） | 1 | 1（65/65） | — |
   | RC2：嵌套 dict 的键也转 | 合理替代解 | 1 | 1（65/65） | — |
   | gold | 原 gold，按 D4 记录失败 | 0 | 0（63/65） | `…_empty_fields`、`…_serializer_output` |
   | noop | — | 0 | 0（61/65） | `test_export_binary` 与 3 个新键 |
   | C2：只处理 `Item`、漏 dict item | 触发反例（原版 1） | 0 | 0（64/65） | `…_dict_item` |
   | C3：不看 `binary` 总转 bytes | 已知错误，兼 §4 第 3 步退化探测（原版就是 0） | 0 | 0（62/65） | `test_nested_item`、`test_export_list`、`test_export_item_dict_list` |

   各行 `git_apply` 成功、测试段完整、键集相等；失败键与试跑逐一相同。gold 失败的原因是 binary 时对 `None` 与 int 值调用 `to_bytes` 抛 `TypeError`，依据试跑日志（revision_plan 第 80 行）；正式日志在远端未取回。
2. **devcheck**：`D/orig/attempt.json` 13 项 checks 全真；6 条命令都符合预期。agent 身份下复现题面缺陷：`binary=True` 导出的键仍是 `str`；公开 `tests/test_exporters.py` 61 passed。私有 gold 对照（root）全部 rc=0，键变成 bytes。
3. **S1 处理**：R-c 一处 edit 加三个测试（revision_plan §1，第 12–20 行）：dict item（§4 第 4 步，同一核心要求的其它实例，堵 C2）；`export_empty_fields` 缺省值为 `None`、serializer 返回值原样保留（§4 第 4 步，有文档的常用行为；gold 过不了，按 D4 用 C1 作正对照）。Codex 复核通过（`L/codex_reviews/review_revision_scrapy.md` 第 7–15 行），限定：C1 只转换顶层键、不二次处理值，其合理性有源码、历史对照与独立复核支持，不是凭满分认定；**没有替嵌套普通 dict 键、非字符串键、serializer 返回字符串三处争议选边**；题面"keys and values … bytes"要结合既有 serializer / 非文本值契约理解，不能推成任意值都必须字节化。Codex 列的正式复验（C1 / noop / gold / C2 / C3，同文件第 44 行）今晚已全部与期望一致，按第 48 行本次修订验收可以核销。
4. **公开包干净**：devcheck `r2e_preflight_ok`（三项 ok）；修订只动评分包，公开包在材料 v3 → v4 之间逐字未变。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | yes | 开发路径与评分依据已核；按 `r2e-mr-026/027` 标明版本报告（gold 式修法在此版本得 0）。批次运行条件属链路 |
| 训练候选 | yes | 核心要求有直接断言：原例 + dict item + 两个新测试里的 bytes 键（revision_plan §6 第 96–97 行）；当前版本 noop 0、正对照 C1 1；§4 第 2、3 步已做；S2、X1 已登记 |
| 留出评测候选 | conditional | 差：① D3 仓库划分未定，本题修复与 `test_export_binary` 出现在同仓 `75450e75`、`a95a338e` 初态（X1），只能整仓同侧；② 若探针结果用于选模型、调提示或调配方即不再符合；③ 只能作标明版本的自建评测 |

## 剩余事项（已登记，不阻塞探针）

- **刻意不测**（revision_plan §6 第 98–102 行）：嵌套普通 dict 的键（R6）、非字符串键（R9）、键的编码（R10）；serializer 在 binary 下返回 `str` 时要不要再编码（题面与文档指向不同，gold 编码、C1 保留）；`fields_to_export` 在 binary 下的键（R8，没有已知错误候选）。
- **题面措辞留意**：题面写"keys and values … should be in bytes"，新断言要求 `None` 与 int 值原样保留。Codex 判定不构成 P5（文档写明非 unicode 值原样传递，`to_bytes` 拒收非文本）。探针里若出现因把 `None` / int 字节化而得 0 的补丁，按 v1 §4 复核后再下结论。
- **后检**：只有打印型命令 `C/scrapy_e938_extra_commands.json`（含 E1 gold 回归对照），按 v1 §8 抽查时要先写明判读规则。
- **X1**（旧卡 `card.md` 第 62–66 行）：本题修复（5 行中 4 行逐字）与 `test_export_binary` 在 `a95a338e`、`75450e75` 初态；本题初态含 `9a15fcf8` 的一行修复。
- **解题侧条件**：无 pip；Scrapy 1.1 与镜像里的 Twisted 24.11 不兼容，`tests/test_closespider.py` 等抓取类公开测试恒失败，与本题无关。
- **链路**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行）：
  - **本题 gold=0**：探针或批次若拿 gold 作健全性对照，须改用 C1（sha256 `c218113f5dfb…`）。
  - 求解入口换 `r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v4 正式评分即此口径）；GPU 机须载入同一 image ID，否则本卡评分资格重出。
  - 模型实际收到的题面消息未对本题捕获。本机开销：rollout 可信初始化约 56 s；评分 trusted setup 44–93 s（300 s 硬时限）；测试段约 3 s。

## 证据索引

- 旧卡：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/scrapy__e938752973b4fc53e0fa0c0bc68a431613b987e4/{card.md,screening_record.json,review.md}`（旧 usage 只有 `intended_use`）
- 修订：`L/results/scrapy__e938752973b4fc53e0fa0c0bc68a431613b987e4/{revision_plan.md,revision_draft.json,trials/}`；正式条目 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v5.json` 的 `r2e-mr-026`、`r2e-mr-027`
- Codex：`L/codex_reviews/review_revision_scrapy.md` 第 7–15、40–48 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/ledger_*.jsonl`（行号见第 1 条）
- devcheck：`D/orig/attempt.json`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v4/summary.json`
