# pillow `3ac9396e` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`F` = `runs/r2e_lifecycle_20260929/formal_v5`（完整评分日志在 `F/remote/<槽位>_logs/`），`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v5/pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605`，`C` = `runs/r2e_actor_20260925/grader_cands`，`B2` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：probe_ready**。五条都满足：正式评分 9 行全部与期望一致（正对照 gold）；devcheck 13 项全真；三处 S1 已按 R-c 修订（第 1 轮 A+B 经 Codex 判"需小改"，第 2 轮补 C 后通过），经正式评分验收，Codex 两轮都指出的"C 的反例须补完整往返与正式评分"已由完整日志确认；预检通过。
- **材料**：修订单 v5 的 `r2e-mr-046`（`hidden_test_text_replace`，`test_1.py` `887ed0de…` → `974e5bcc…`）与 `r2e-mr-047`（`expected_file_replace`，`11a66580…` → `ec40ba6c…`，11 → 14 键，新增 `TestFileTiffMetadata.test_div_zero_other_unregistered_tag`（A）、`…_in_rational_sequence`（C）、`test_unregistered_int_tag_type`（B））；A-only 草案已否决、未用。pins v6 `9a24b8693020…`，v6 逐字保留。派生镜像 `41e812d410bc`（`rh2-r2e-derived/pillow:3ac9396e8c99-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `3275d2fe1007…`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-046/047`），不当原 benchmark 报。

## 准入五条（README §3）

1. **正式评分**（`F/ledgers/` gold / noop / s1 / s2 / s3 第 7 行，s4 第 6 行，s5 第 3 行，s6 第 2 行，s7 第 1 行；`F/status.json` 本题 9 行 `match=true`；日志头 `RH2_SETUP_HIDDEN_TESTS_TREE=eb5fb284…`、入口 `cb5074a9…` 等于 v5 评分包摘要）：

   | 候选 | 角色 | 期望 | 实得 | 不符键与失败断言（正式日志） |
   | --- | --- | --- | --- | --- |
   | gold | 正对照 | 1 | 1（14/14） | — |
   | K1：未登记 tag 全是 `IFDRational` 时写类型 5 | 合理替代解 | 1 | 1（14/14） | — |
   | K1b：同上写类型 10 | 合理替代解（不固定类型码） | 1 | 1（14/14） | — |
   | noop | — | 0 | 0（11/14） | A、C、原键 ERROR：`struct.error: required argument is not an integer` |
   | K2：只在全部为零分母时选有理数 | C 的触发反例（第 4 步，原版 1） | 0 | 0（13/14） | 只有 C：在 `im.save` 抛 `struct.error`（`test_1.py:225`） |
   | K3：只给 `IFDRational` 加 `__index__` | 已知错误，兼退化方向（让打包不报错但写错值，原版 0） | 0 | 0（11/14） | A 与原键 `0 != 1`；C 读回 `[(0, 1), (1, 1)]` |
   | K4：只登记 41988（长度 1） | 已知错误（原版 0） | 0 | 0（11/14） | A、C `struct.error`；原键 `'IFDRational' object is not subscriptable` |
   | K4b：只登记 41988（长度 0） | A 的触发反例（第 2 步示例拟合，原版 1） | 0 | 0（12/14） | A、C `struct.error` |
   | RC6：整数也按有理数写 | B 的触发反例（第 4 步，原版 1） | 0 | 0（13/14） | 只有 B：`5.0 is not an instance of <class 'int'>` |

   各行 `git_apply` 成功、测试段完整、日志不截断、键集相等；补丁是试跑用过的同一份远端副本，账本补丁摘要与 `C/` 本地副本一致，失败键与试跑逐一相同。出处（`F/remote/`）：noop `noop_logs/…_62d656dc.eval.log` 第 52、75、98 行；K2 `s3_logs/…_b7f119cc` 第 29–53 行；K3 `s4_logs/…_bc91ef90` 第 41、63、74 行；K4 `s5_logs/…_826408ac` 第 53、76、87 行；K4b `s6_logs/…_4c28d694` 第 53、76 行；RC6 `s7_logs/…_daf879d2` 第 37 行。
   - **C 的反例已由完整往返与正式评分确认**：第 1 轮 Codex 指出 K2 的反例只有原函数证据（`L/codex_reviews/review_revision_pillow.md` 第 43 行），第 2 轮试跑补了保存与重开，第 2 轮复核仍写明"试跑通过不等于正式评分完成"（`review_revision_pillow_3ac9_r2.md` 第 39 行）；正式日志显示 K2 在 C 的 `im.save` 抛 `struct.error`，不是环境或收集失败。
2. **devcheck**：`D/orig/attempt.json` 13 项 checks 全真；9 条命令都符合预期。agent 身份下复现题面缺陷，也复现真实根因：41988 写 0/0 与 1/2 都抛 `struct.error`，已登记的 282 写 0/0 正常（pr3_2）；题面原例 rc=1（pr6_3）；`PYTHONPATH=Tests python -m unittest …` 42 个 OK（pr8_5）。pr7_4（9 failed / 33 passed）、pr9_6（1 failed）、pr9_7（13 failed + 2 errors）都是 Pillow 3.1 的 `Tests/helper.py` 与 pytest 8 不兼容（`'TestCaseFunction' object has no attribute 'errors'`），agent base 与私有 gold 对照计数相同，与 09-25 相同；私有 gold 下 pr3_2 三例都 OK、pr6_3 输出 `0 0`。
3. **S1 处理**：R-c 三处（revision_plan §2，第 20–50 行）：A 另一个未登记 tag 65000 存 0/0（第 2 步，堵 K4b）；C 同一 tag 存 `(0/0, 1/2)` 序列并逐项往返（第 4 步，堵 K2）；B 未登记 tag 存整数读回仍是 `int`（第 4 步，堵 RC6）。都不固定类型码 5 / 10，也不固定 LONG / SHORT 宽度。Codex 第 1 轮（`review_revision_pillow.md` 第 11–45 行）保留 A、B，要求堵 K2，A-only 不通过；第 2 轮（`review_revision_pillow_3ac9_r2.md` 第 1–37 行）确认 C 只补 K2 的混合序列、A 与 B 逐字未变，"通过，无需再改"。**限定**：K1、K1b 只在本次核心场景下是合理替代解，不等于所有数值范围都已验证（第 1 轮第 28 行）。
4. **公开包干净**：devcheck `r2e_preflight_ok`（三项 ok）；修订只动评分包，本题公开包行（`public_bundles_v0.jsonl` 第 40 行）在材料 v3、v4、v5 与当前摄入里哈希相同。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | yes | 开发路径与评分依据已核；按 `r2e-mr-046/047` 标明版本报告。revision_plan §9 写的"差新机器新镜像上的公开命令复验"已由 devcheck v5 补齐。批次运行条件属链路 |
| 训练候选 | yes | 核心要求有直接断言（revision_plan §6 第 161–166 行：示例 tag、另一个未登记 tag、含零分母的序列、未登记整数仍是整数）；当前版本 noop 0、gold 1；§4 第 2 步（A）与第 3 步（K3、K4b）已做，第 4 步候选 K2、RC6 均为 0；S2、X1 已登记。revision_plan §9 写的"再差正式评分"已补齐 |
| 留出评测候选 | conditional | 差：① D3 仓库划分未定，本题修复与测试在同仓 6 题初态里（X1），只能整仓同侧；② 若探针结果用于选模型、调提示或调配方即不再符合；③ 只能作标明版本的自建评测。revision_plan §9 记 `no`，理由是审查者看过 gold 与 X1；前者按 D3 只需记录暴露，后者靠整仓划分处理，都不在 v1 §2 的否决条件里，故改记 conditional（与 `pillow__3a61c9e9` 卡同一口径） |

## 剩余事项（已登记，不阻塞探针）

- **S2**（revision_plan 第 167–172 行）：只含非零分母有理数的未登记 tag（base 同样失败）不测，是否扩题是用户可选决定、不阻塞本题（§7 第 174–180 行，执行者建议不扩）；类型码 5 与 10 只在已测的非负值下等价；gold 把未登记小整数由 LONG 改为 SHORT（公开契约不固定宽度，不计缺陷）；JPEG / MPO 写 EXIF、`tiffinfo` 传普通 dict 未覆盖。
- **题面（P4，旧 I1）**：把原因归到零分母，实际是未登记 tag 的类型推断落到 LONG；base 上 41988 写 1/2 同样失败（`B2/card.md` 第 41 行；devcheck pr3_2）。不构成冲突。
- **公开测试噪声（旧 I4）**：提示要求 `python -m pytest`，但 Pillow 3.1 测试辅助与 pytest 8 不兼容，写临时文件的用例恒定假失败；`PYTHONPATH=Tests python -m unittest` 可用（`B2/card.md` 第 44 行）。探针分析时不要把这类失败当成模型改坏。
- **镜像**：`test_ifd_rational_save` 依赖 libtiff 编码器，重建镜像须保留 libtiff（`B2/card.md` 第 46 行）。
- **X1**（`B2/card.md` 第 45 行）：本题修复（演化形态）与 `test_exif_div_zero`、`test_ifd_rational_save` 出现在同仓 6 题（Pillow 8.0–10.1）公开初态中；逐字 gold 扫描因上游重构漏报。
- **链路**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行；Codex `L/codex_reviews/review_probe_chain_20260929.md` 第 1–3 行"改后可以"）：
  - 求解入口换 `rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v5 正式评分即此口径）。
  - 接真实模型前先收口 Codex 的两项 P1：去掉静止屏障里以 root 执行的 git（第 9–31 行）；往返核对不一致、评分 fatal、清理未知时停止派发（第 33–41 行）。正式链直评的基线摘要问题可递延（第 43–51 行）。
  - GPU 机须载入同一 image ID（按 tag→ID 核对），否则本卡评分资格重出。账本 `env_qualification=absent`，能力统计前补接资格账本或单列（Codex 第 78 行）。
  - 本题修复只需改 Python；若模型改 C 源码，pillow 以 agent 身份重编并随导出交付的链路未实测（只在 orange3 验过）。
  - 模型实际收到的题面消息未对本题捕获。本机开销：rollout 从起容器到可信初始化完成约 51 s；评分 trusted setup 19–53 s（该步 300 s 硬时限）；测试段不到 1 s。

## 证据索引

- 旧卡：`B2/{card.md,screening_record.json,review.md}`（旧 usage 只有 `intended_use`）
- 修订：`L/results/pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605/{revision_plan.md,revision_draft.json,trials/}`（`revision_draft_a_only.json` 已否决）；正式条目 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v5.json` 的 `r2e-mr-046`、`r2e-mr-047`
- Codex：`L/codex_reviews/review_revision_pillow.md` 第 11–45 行；`L/codex_reviews/review_revision_pillow_3ac9_r2.md` 第 1–39 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/ledger_*.jsonl`（行号见第 1 条）、`F/remote/*_logs/`
- devcheck：`D/orig/attempt.json`、`D/orig/captures/`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v5/summary.json`
