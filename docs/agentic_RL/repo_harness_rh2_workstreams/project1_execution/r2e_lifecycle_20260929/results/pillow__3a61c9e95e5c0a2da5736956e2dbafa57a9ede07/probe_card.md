# pillow `3a61c9e9` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`F` = `runs/r2e_lifecycle_20260929/formal_v4`，`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v4/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：probe_ready**。五条都满足：正式评分 8 行全部与期望一致（正对照 gold）；devcheck 13 项全真；四处 S1 已按 R-c 修订，经 Codex 复核与正式评分验收；预检通过。
- **材料**：修订单 v4 的 `r2e-mr-024`（`hidden_test_text_replace`，`test_1.py` `17ececcd…` → `04f44d8a…`）与 `r2e-mr-025`（`expected_file_replace`，`0421915b…` → `3d86300f…`，71 → 73 键，新增 `TestImage.test_remap_palette_rgba_reorder`、`…_rgba_gif_save`）；pins v5 `2324c4c4ab82…`，v5 逐字保留。派生镜像 `bf8ad772f191`（`rh2-r2e-derived/pillow:3a61c9e95e5c-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `41cff231714e…`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-024/025`），不当原 benchmark 报。

## 准入五条（README §3）

1. **正式评分**（`F/ledgers/`：gold / noop / s1 / s2 / s3 第 4 行，s4 第 3 行，s5 / s6 第 2 行；`F/status.json` 本题 8 行 `match=true`）：

   | 候选 | 角色 | 期望 | 实得 | 不符键 |
   | --- | --- | --- | --- | --- |
   | gold | 正对照 | 1 | 1（73/73） | — |
   | C1：RGB 写回 + `putpalettealphas` | 合理替代解 | 1 | 1（73/73） | — |
   | A1u：不补齐到 256 项 | 合理替代解 | 1 | 1（73/73） | — |
   | noop | — | 0 | 0（71/73） | `test_remap_palette`、`…_rgba_reorder` |
   | W1：显式 `source_palette` 也按 RGBA 步长读 | 触发反例（原版 1） | 0 | 0（72/73） | `…_rgba_gif_save` |
   | W2：C 层只写 RGB | 触发反例（原版 1） | 0 | 0（71/73） | `test_remap_palette`、`…_rgba_reorder` |
   | W3：恒等映射直接返回副本 | 触发反例，兼 §4 第 3 步退化探测（提前返回，原版 1） | 0 | 0（72/73） | `…_rgba_reorder` |
   | W5：先把原图改成 RGB | 触发反例，兼退化探测（就地改坏输入，原版 1） | 0 | 0（71/73） | `test_remap_palette`、`…_rgba_reorder` |

   各行 `git_apply` 成功、测试段完整、键集相等；失败键与试跑逐一相同。A1u 用的是试跑实际用过的远端副本 `sha256:12e49af5e367…`；本目录的本地副本只差空白上下文行（`F/plan.json` 该行注记；revision_plan 第 122 行）。
2. **devcheck**：`D/orig/attempt.json` 13 项 checks 全真；9 条命令都符合预期。agent 身份下复现题面缺陷：恒等映射后调色板 1024 → 768 字节、RGBA 渲染不等；`[1,0]` 交换后前 6 字节是 `[50, 60, 70, 10, 20, 30]`；GIF 往返 `True`（base 本来正确）。公开 `Tests/test_image.py -k remap_palette` 在 base 上 2 passed，公开测试抓不到本题缺陷。私有 gold 对照（root）全部 rc=0，输出与修订依据一致。
3. **S1 处理**：R-c 四处（revision_plan §2，第 17–28 行）：调用前快照（堵 W5）、C 层调色板保留 alpha（堵 W2）、非恒等 RGBA 重排（堵 W3）、GIF 保存不回归（堵 W1）。Codex 复核通过（`L/codex_reviews/review_revision_pillow.md` 第 47–64 行）：期望来自调用前快照、交换关系与输入颜色计算，没有固定补齐长度、未使用项 alpha 或 GIF 文件字节，没有放宽旧断言；C1、A1u 用来查误拒。Codex 写明"目前不能称正式验收或探针准入已完成"，今晚正式评分与 devcheck 已补齐这两项。
4. **公开包干净**：devcheck `r2e_preflight_ok`（三项 ok）；修订只动评分包，公开包在材料 v3 → v4 之间逐字未变。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | yes | 开发路径与评分依据已核；按 `r2e-mr-024/025` 标明版本报告。批次运行条件属链路 |
| 训练候选 | yes | 核心要求有直接断言（revision_plan §6 第 128 行）；当前版本 noop 0、gold 1；§4 第 2 步与第 3 步（W3、W5）已做；S2、X1 已登记。revision_plan §9 写的"再差 Codex 复核与正式评分"已补齐 |
| 留出评测候选 | conditional | 差：① D3 仓库划分未定，本题与同仓 6 题有包含关系（X1），只能整仓同侧；② 若探针结果用于选模型、调提示或调配方即不再符合；③ 只能作标明版本的自建评测。revision_plan §9 记 `no`，理由是审查者看过 gold 与 X1；前者按 D3 只需记录暴露，后者靠整仓划分处理，都不在 v1 §2 的否决条件里，故改记 conditional |

## 剩余事项（已登记，不阻塞探针）

- **S2**（revision_plan §6 第 129–133 行）：显式 `source_palette` 在 GIF 以外的格式约定没有公开依据，不测；部分映射时 Python 层调色板总长度与补齐项 alpha 有意不约束；gold 在 GIF `palette=` 分支里调色板 mode 与字节格式可能不一致（旧 I5，静态推断，未测）；PNG 等其它插件的 RGBA 调色板保存路径未覆盖；"把所有 P 图都输出为 RGBA 调色板"一类候选没跑。
- **后检**：只有打印型命令 `runs/r2e_actor_20260925/grader_cands/pillow_3a61_extra_commands.json`；Codex 第二批复核 NP-1 要求后检先做调用前快照，不能只看 rc 或调用后两对象相等。
- **X1**（旧卡 `card.md` 第 24–28 行）：本题 gold 13/13 行与测试块在 `f9d3ee0f` 初态，`a682ceaf` 含 10/13 行（机械比对漏报）；本题初态含 `2b061b68`、`2d01f7d0`、`4bc64835` 的修复和 `3ac9396e` 的测试。
- **共享机制**：`.venv` 对 agent 可写，根 `conftest.py` 以插件加载 `Tests.helper`（R2E 通用问题，旧卡第 19 行）。
- **链路**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行）：
  - 求解入口换 `r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v4 正式评分即此口径）；GPU 机须载入同一 image ID，否则本卡评分资格重出。
  - 本题修复只需改 Python；若模型改 `src/libImaging` 等 C 源码，pillow 以 agent 身份重编并随导出交付的链路未实测（只在 orange3 验过；Codex 第二批复核 `numpy_pillow/README.md` §6 也指出 pillow 重建未验证）。
  - 模型实际收到的题面消息未对本题捕获。
  - 本机开销：rollout 可信初始化约 88 s；评分 trusted setup 61–114 s，是本批 7 题里最高的（该步 300 s 硬时限），GPU 机并发评分时要留意；测试段约 2–4 s。

## 证据索引

- 旧卡：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/{card.md,screening_record.json,review.md}`（旧 usage 只有 `intended_use`）；Codex 第二批复核 `…/r2e_static_batch2_review_20260925/numpy_pillow/README.md` NP-1
- 修订：`L/results/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/{revision_plan.md,revision_draft.json,trials/,pillow_3a61_A1u_unpadded_putpalette.patch}`；正式条目 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v5.json` 的 `r2e-mr-024`、`r2e-mr-025`
- Codex：`L/codex_reviews/review_revision_pillow.md` 第 47–64 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/ledger_*.jsonl`（行号见第 1 条）
- devcheck：`D/orig/attempt.json`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v4/summary.json`
