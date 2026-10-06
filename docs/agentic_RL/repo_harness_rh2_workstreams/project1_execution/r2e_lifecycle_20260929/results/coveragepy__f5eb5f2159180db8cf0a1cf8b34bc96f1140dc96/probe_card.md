# coveragepy `f5eb5f21` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`R` = `L/results/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96`（本题全部审查产物，含独立复核 `reviewer_initial.md`、`review.md`；没有旧审查卡），`F` = `runs/r2e_lifecycle_20260929/formal_v8`（本题在 `F/ledgers/ledger_{gold,noop,s1,…,s6}.jsonl` 各第 1 行，完整日志在 `F/remote/<槽位>_logs/`），`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v8/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96`（v8 镜像），`D0` = `runs/r2e_lifecycle_20260929/devcheck/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96`（修订前镜像），`INV` = `runs/r2e_lifecycle_20260929/inv/coveragepy_f5eb`（协调者实跑），`CX` = `L/codex_reviews/review_revision_coveragepy_f5eb.md`。键名省略类名 `JsonReportTest.`：BC = `test_branch_coverage`（原目标键），K1 = `test_branch_totals_count_branch_arcs`，K2 = `test_branch_totals_from_saved_branch_data`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：on_hold**（用户裁定 C1 之前只作问题定位，不进探针、正式能力比较与训练）。R-c 已落地并验收，准入五条按字面都成立：正式评分 8 行全部与期望一致（正对照 gold，缺省 300 s 时限），两次 devcheck 13 项全真，预检通过。卡住的是 C1（每文件 `summary` 也加这两个计数，被判 0）：只改 `totals` 与每文件对称加两键，两种读法都有公开依据。复核曾认为 R-b 在模板内，Codex 不同意，定为 v1 §3 P5 的输出范围选择，并写明"未裁定前应暂挂为问题定位，不能直接放入正式能力比较／`probe_ready`"（`CX` 第 39–44、50 行）。处理方式与 `5dbbe143` 相同。
- **恢复条件**（决定包 `R/revision_plan.md` §6–§7，第 216–372 行；主审、复核、执行者都倾向 A，属建议，本卡不替用户选；裁定后的用途按第 263–270 行）：
  - **选 R-b 窄版（A：每文件 summary 可以带这两键，带了必须成对且值对）**：①用 `R/revision_draft_rb.json` 的合并条目（5 处 edit，第 1 处与 `r2e-mr-053` 逐字相同）整体替换 `r2e-mr-053`，因为同一题同一目标只许一条修订（`rh2/src/repoharness2/envpack/ingest_r2e_subset.py:415-418`）；`r2e-mr-054`（6 键）不变；出新修订单与 pins，重建派生镜像。②正式条目须与 Codex 看过的草案逐字一致（Codex 认可草案够窄：成对、验值、保留旧字段与行模式约束，`CX` 第 44 行），有改动就再送复核。③新镜像上正式复验（缺省时限）：gold 1、A1 1、noop 0、D0 0、C2 0、C3 0、W2 0、**C1 1**、**C1swap 0**。R-b 下 C1、C1swap 只有试跑（`R/trials/rb_*.json`），W2、A1 连试跑都没有，都不能算已验证（`CX` 第 33、52 行）；失败位置按 revision_plan 第 359–367 行逐键核（C1swap 只错 K1，在每文件核对行 `assert 2 == 4`）。④新镜像补 devcheck，重写本卡。这是新题目版本，v8 的结果不能替它作资格（v1 §2）。
  - **选保持键集（C：本题目标只改 `totals`，每文件 summary 保持 7 键）**：材料就是现在的 v8，C1 = 0 按所选范围是违例（`CX` 第 51 行）。不需要再评分：v8 正式日志已显示 C1 只错 BC，差异只在每文件 summary 多出两键（下文第 1 条）。还差：①把裁定写进批次记录与修订说明（P5 属模板外，要有 decision_ref）；②按裁定改写 `R/screening_record.json` 的 I5；③预登记探针分析规则：得 0、只错 BC、差异只在每文件多两键的结果单列，原始 reward 保留，每文件两值用 `INV/private_P3_branchy.py` 核（revision_plan 第 275–277 行），因为题面没写这个范围，解题者看不到；④登记训练风险：`ea6906b0` 的初态就是"每文件也有两键"的形态，同池训练可能让 C1 型输出更常见（推测，未实测；执行者意见是不建议此选项用于训练，第 309 行）。做完即可改标 probe_ready。若同时在题面补一句（B，草稿第 279–284 行），另需：没看过隐藏测试与 gold 的新公开读者验收、逐行核对、Codex 复核具体题面、新修订单与 pins，并在新版本上重跑预检、devcheck 与正式评分（至少 gold、noop、C1）。
- **材料**：修订单 v8 的 `r2e-mr-053`（`hidden_test_text_replace`，`test_1.py` `ee874f37…` → `73ad2f27…`，159 → 220 行，在 `JsonReportTest` 末尾加夹具 BRANCHY 与 K1、K2）、`r2e-mr-054`（`expected_file_replace`，`9e555e51…` → `755e53ba…`，4 → 6 键，新增 K1、K2 均 PASSED，无改删）；pins v9 `9b766c2aec84…`（其后 v10 只改 orange3 `4014`）；评分日志头 `RH2_SETUP_HIDDEN_TESTS_TREE=ea6a4e14…` 等于当前评分包（`docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl` 第 10 行）。派生镜像 `7c53d85b691c`（`rh2-r2e-derived/coveragepy:f5eb5f215918-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `e39a49c21430…`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-053/054`），不当原 benchmark 报；gold 在修订版上仍为 1。本题此前没有材料修订；选 A 或 B 会再出新版本。

## 准入五条（README §3）

1. **正式评分**（`F/status.json` 本题 8 行 `match=true`）：

   | 候选 | 角色 | 期望 | 实得 | 不符键与失败断言（正式日志） |
   | --- | --- | --- | --- | --- |
   | gold（`coverage/jsonreport.py` 两行，取 `n_executed_branches` / `n_missing_branches`） | 正对照 | 1 | 1（6/6） | — |
   | A1：逐文件累加 `branch_stats()`，不用 gold 的写法 | 合理替代解（补充证据） | 1 | 1（6/6） | — |
   | noop | — | 0 | 0（3/6） | BC：totals 缺两键（`test_1.py:35`）；K1、K2：`KeyError: 'covered_branches'`（`:211`、`:219`） |
   | D0：两值硬编码 1/1 | §4 第 3 步退化候选（原版 1） | 0 | 0（4/6） | K1、K2：`assert 1 == 4`（`:211`、`:219`） |
   | C2：用"部分弧"口径 | 第 4 步（原版 1） | 0 | 0（4/6） | K1、K2：`assert 6 == 4` |
   | W2：两值对调 | 已知相关错误候选（原版试跑 1），Codex 定为必跑 | 0 | 0（4/6） | K1、K2：`assert 2 == 4` |
   | C3：按配置 `branch` 而不是数据 `has_arcs()` 门控 | 第 4 步（原版 1） | 0 | 0（5/6） | 只有 K2：`KeyError: 'covered_branches'`（`:219`），K1 通过 |
   | C1：每文件 summary 也加两键 | **P5 争议读法的对照，不是已确认的错误候选** | 0（只落 R-c，按设计） | 0（5/6） | 只有 BC（`:35`）：`Differing items` 只有 `files`，totals 与 gold 相同（`F/remote/s4_logs/…_2b2adf98.eval.log` 第 91–94 行）；K1、K2 通过，说明 R-c 没有替 P5 选边 |

   "原版"指修订前材料上的协调者正式评分（`INV/ledger_{D0,C2,C3,C1}.jsonl` 第 1 行：D0、C2、C3 均 1.0（4/4），C1 0.0（3/4），镜像 `98b19b5a`）；W2 原版只有试跑（`R/trials/cur_W2.json`）。各行由 agent/54321 `git_apply` 成功，投影只含 `coverage/jsonreport.py`，测试段完整、日志不截断，解析 6 键且 `keys_equal=true`（无 missing / unexpected）；补丁摘要等于 `R/cands/` 本地副本（`F/remote/slots_manifest.json`），gold 为 `c8fa460d…`。复核（`R/review.md` 第 87–93 行）与 Codex（`CX` 第 27、33 行）要求的逐键核对都已由正式日志确认：gold 6 键都是 PASSED 行；D0、C2、W2 两个新键都失败；C3 只在 K2 以 `KeyError` 失败；noop 恰好 3 键。账本可信 setup + 保护 33–41 s，测试段 5–8 s（4 路并发）。
2. **devcheck**：v8 镜像（`D/orig/attempt.json`，`7c53d85b…`，与正式评分同一 ID）13 项 checks 全真，8 条命令都符合预期；修订前镜像（`D0/orig/attempt.json`，`98b19b5a…`）同一组命令同样全过（修订只动评分包）。agent 身份下：`repro_api_totals` rc 1（totals 缺两键，复现问题）；公开 `tests/test_json.py` 4 passed。私有 gold 对照（root、断网）：`public_test_json` rc 1，原因是公开 BC 锁定了旧 totals，任何正确修复都会让它失败（P6，与修订前相同，预期内）；其余 rc 0，`repro_cli_json` 走文档的 CLI 流程也给出 1/1。非编译题。
3. **S1 处理**：R-c 两项合并一轮（`R/revision_plan.md` §1–§3，第 15–142 行）：①非示例计数：夹具 BRANCHY 上 num 6 / partial 0 / covered 4 / missing 2，四个值两两不同、都不等于示例的 1，堵 D0、C2、W2（§4 第 2、3、4 步）；②按数据门控：先保存分支数据，再用不设 `branch` 的新报告对象出报告，对应文档写明的"先 `coverage run --branch`、再单独 `coverage json`"流程，堵 C3。期望由公开口径推出（`results.py` 定义、XML 报告的独立计数），不是抄 gold 输出。独立复核同意两项都必做（`R/review.md` 第 14–16 行）。Codex：R-c 通过（`CX` 第 3–12 行），**限定**：①gold 仍是正式正对照，A1 只是补充证据（第 30 行）；②公开测试与新 totals 冲突的 P6 仍在，只是没有加重（第 37 行）；③R-b 属 P5，"推荐不等于已授权"（第 39–44 行）；④"尚不能声称正式验收完成"（第 33 行）：今晚 v8 正式矩阵 8 项已完成，W2 已按要求正式跑。决定包三处措辞已按 Codex 更正（revision_plan 第 274、291–296、399 行）。
4. **公开包干净**：两次 devcheck 都 `r2e_preflight_ok`（解释器、隐藏测试、git 历史三项 ok）；git sanitize 后 refs / remotes / reflog / 不可达对象都为 0；修订只动评分包，本题公开包行（`docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/public_bundles_v0.jsonl` 第 10 行）在 09-29 各次摄入（v4 前、v8 前、v9 前的备份与当前）逐字相同；题面与 gold 无逐行重叠（`runs/r2e_static_prep_20260924/statement_gold_overlap_scan.json`）。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛。裁定前只能作此用途，运行结果单列，不并入能力分数 |
| 能力比较 | conditional | 差 C1 的用户裁定（P5），裁定前不进比较分母（`CX` 第 50 行）。开发路径、评分依据、本批运行条件都已核（第 1、2 条）。选 C：当前版本即转 yes，C1 型结果按上面预登记的规则单列；选 A / B：新版本按"恢复条件"验收后再定。批次运行条件属链路 |
| 训练候选 | conditional | 差 P5 裁定，以及 X1 训练侧登记（`97997d2c` 初态与本题逐字节相同，要控制同初态的重复采样；`ea6906b0` 初态含本题答案，且是"每文件也有两键"的形态，与 C1 的选择直接相关，`R/review.md` 第 138–145 行）。正面覆盖证据已齐：两键存在（BC、K1、K2）、口径的非示例实例（K1、K2）、按数据门控（K2）、行模式形状（其余 3 键）都有决定性断言（revision_plan 第 376–381 行）；v8 上 noop 0、gold 1；§4 第 2、3、4 步已做；T3 已登记 |
| 留出评测候选 | conditional | 差：①P5 裁定与训练候选的质量条件；②D3 仓库划分未定，`ea6906b0` 初态含本题答案，两题须同侧；③若探针结果用于选模型、调提示或调配方即不再符合；④只能作标明版本的自建评测（选 B 还要标明题面版本） |

## 剩余事项

- **P5 / C1 待用户决定**（阻塞，见"结论"）。三个选项的前提、验收、成本与对用途的影响见 revision_plan 第 252–277 行。
- **T3**（`R/card.md` I9；revision_plan 第 383–384 行）：多文件时 totals 的汇总、`report()` 返回值（`--fail-under` 用）没测；在 `report_one_file` 里用赋值代替累加的写法，单文件测试看不出来（`R/review.md` 第 80 行）。
- **P6**（I6）：公开 `tests/test_json.py::test_branch_coverage` 锁定旧 totals；分析探针时，模型改它不算钻空子，它失败也不算模型改错。
- **P4**（I7）：题面把功能补充说成"测试断言失败"，在 base 的公开测试上不出现；示例里的 "execute some code" 是占位；替代复现是 `repro_api_totals`。
- **X1**（I8）：见用途表；本题初态还含 `016af5f6`、`5dbbe143` 的修复，反向关系要在那两题卡上登记（`5dbbe143` 的准入卡第 48 行已登记，`016af5f6` 未审）。
- **共享控制面**：隐藏测试（含新测试）依赖评分时不重置、候选可改的 base 测试辅助（`make_file`、`start_import_stop`）；agent 可写 `.venv`（`R/review.md` 第 153–156 行，交 A 线清单 #31）。
- **稳定性**：新测试是确定性的；每个候选正式评分 1 次；原有"报告时间在 10 秒内"的断言历次无抖动。
- **链路（恢复后才适用，同批共同项）**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行；Codex `L/codex_reviews/review_probe_chain_20260929.md` 第 1–3 行"改后可以"）：求解入口换 `rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v8 正式评分即此口径）；接真实模型前先收口 Codex 的两项 P1（去掉静止屏障里以 root 执行的 git，第 9–31 行；往返不一致、评分 fatal、清理未知时停止派发，第 33–41 行）；GPU 机须载入同一 image ID（按 tag→ID 核对），否则本卡评分资格重出；账本 `env_qualification=absent`，能力统计前补接资格账本或单列（第 78 行）。本机开销：rollout 从起容器到可信初始化完成约 51 s（`D/orig/attempt.json` 的 `stages`）；评分见第 1 条。模型实际收到的题面消息未对本题捕获。

## 证据索引

- 审查产物：`R/{public_read.md,commands.json,analysis_before_history.md,old_findings_delta.md,card.md,screening_record.json,reviewer_initial.md,review.md}`（`card.md` 与 `screening_record.json` 的 v1 用途是修订前结论，已由本卡取代）
- 修订与决定包：`R/{revision_plan.md,revision_draft.json,revision_draft_rb.json,trials/,cands/}`；正式条目 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v8.json` 的 `r2e-mr-053`（第 1653 行起）、`r2e-mr-054`（第 1677 行起）
- Codex：`CX` 第 1–54 行
- 修订前实跑：`INV/ledger_{D0,C1,C2,C3}.jsonl`、`INV/logs_*/`、`INV/pcheck_P{1,2,3}_*.json`；`runs/r2e_lifecycle_20260929/env_verify/ledger_l1_{noop,gold}.jsonl` 第 2 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/`、`F/remote/*_logs/`、`F/remote/slots_manifest.json`
- devcheck：`D/orig/{attempt.json,captures/}`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v8/{summary.json,lane.log}`；`D0/`（修订前镜像）
