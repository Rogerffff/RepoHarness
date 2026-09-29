# coveragepy `97997d2c` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`F` = `runs/r2e_lifecycle_20260929/formal_v5`（完整评分日志在 `F/remote/<槽位>_logs/`），`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v5/coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266`，`C` = `runs/r2e_actor_20260925/grader_cands`，`B2` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：probe_ready**。五条都满足：v5 材料、新派生镜像上正式评分 7 行全部与期望一致（正对照 gold）；devcheck 13 项全真；三处 S1 已按 R-c 修订，经 Codex 复核与正式评分验收；预检通过。
- **材料**：修订单 v5 的 `r2e-mr-034`（`hidden_test_text_replace`，`test_1.py` `acae864f…` → `b4824fe1…`）与 `r2e-mr-035`（`expected_file_replace`，`2388143c…` → `747ed597…`，44 → 47 键，新增 `ConfigTest.test_tweaks_paths_on_config_object`、`…_used_by_combine`、`…_replaces_config_file_paths`）；pins v6 `9a24b8693020…`。修订单 v6（pins v7）逐字保留这两条，本题评分包、公开包行与 v5 摄入逐字相同。派生镜像 `3d40fa69697f`（`rh2-r2e-derived/coveragepy:97997d2cd680-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `6aa35fb13506…`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-034/035`），不当原 benchmark 报。按"合并"实现的修法在此版本得 0（依据见第 3 条）。

## 准入五条（README §3）

1. **正式评分**（`F/ledgers/` 各槽第 1 行；`F/status.json` 本题 7 行 `match=true`；日志头 `RH2_SETUP_HIDDEN_TESTS_TREE=7d6afd3a…` 等于 v5 评分包摘要）：

   | 候选 | 角色 | 期望 | 实得 | 不符键与失败断言（正式日志） |
   | --- | --- | --- | --- | --- |
   | gold | 正对照 | 1 | 1（47/47） | — |
   | A1：set 时复制并 `expanduser`，get 返回副本 | 合理替代解 | 1 | 1（47/47） | — |
   | noop | — | 0 | 0（43/47） | 原目标键 + 3 个新键，都是 `No such option: 'paths'` |
   | W1：只改 `control.py` 转发层 | 触发反例（原版 1） | 0 | 0（46/47） | `…_on_config_object`：`config.get_option("paths")` 抛 `No such option`（`test_1.py:361`） |
   | W2：值存到旁路属性 | 触发反例，兼 §4 第 3 步退化探测（作用在无关对象上，原版 1） | 0 | 0（46/47） | `…_used_by_combine`：`['/remote/src/pkg/mod.py'] != ['/local/src/pkg/mod.py']`（`:383`） |
   | M：`paths.update(value)` 合并 | 触发反例（原版 1） | 0 | 0（46/47） | `…_replaces_config_file_paths`：读回多出 `first`、`second`（`:408`） |
   | N1：把 `paths` 加进 `CONFIG_FILE_OPTIONS` | 已知错误（原版 0） | 0 | 0（18/47） | 原 28 个读配置文件的键 + 新替换键，29 处 `not enough values to unpack` |

   各行 `git_apply` 成功、测试段完整、日志不截断、键集相等；补丁是试跑用过的同一份远端副本，账本补丁摘要与 `C/` 本地副本一致，失败键与试跑逐一相同。出处（`F/remote/`）：noop `noop_logs/…_bbafc9d5.eval.log` 第 295–298 行；W1 `s2_logs/…_a70ec79e` 第 32、63 行；W2 `s3_logs/…_4c12be95` 第 40 行；M `s4_logs/…_67598943` 第 50 行；N1 `s5_logs/…_f1dc9612` 第 1872 行。
2. **devcheck**：`D/orig/attempt.json` 13 项 checks 全真；9 条命令都符合预期。agent 身份下复现题面缺陷：两种对象 `get_option("paths")` 都抛 `No such option`（pr1_1）；插件路径同样报错（pr4_2，rc=1）；`combine` 不重映射（pr7_7 输出 `['ci/girder/g1.py']`）；`-o addopts=""` 跑公开 `tests/test_config.py` 43 passed（pr6_6）。pr5_3–pr5_5 的 rc=4 是命令伪影（`-p no:cacheprovider` 与 `setup.cfg` 的 `--failed-first` 冲突），私有 gold 对照（root）同为 rc=4，与 09-25 相同；gold 下 pr1_1、pr4_2、pr7_7 输出与修订依据一致。
3. **S1 处理**：R-c 三处（revision_plan §1，第 24–30 行）：G1 `CoverageConfig` 读写（第 4 步，堵 W1）、G2 `combine()` 用上新值（第 3、4 步，堵 W2）、G3 从配置文件起步先取回再替换（第 2 步，堵 M）。Codex 通过（`L/codex_reviews/review_revision_coveragepy.md` 第 5–17 行），支持保留替换断言，依据是公开 `set_option` 的 "new value" 契约与既有选项整体赋值（第 10 行）。**限定**：题面第 23 行示例从空映射开始、插件"取出后修改再 set"样例都不能单独区分替换与合并（第 11 行）；revision_plan §2.1 第 1 条与第 3 条里的插件样例把它们列为依据，表述偏强，以 Codex 收紧后的为准。Codex 要求的正式复验（第 17、48 行：绑定修订单、pins、测试摘要与镜像身份，确认正负对照与触发反例）今晚已完成，见第 1 条。
4. **公开包干净**：devcheck `r2e_preflight_ok`（三项 ok）；修订只动评分包，本题公开包行（`public_bundles_v0.jsonl` 第 8 行）在材料 v3、v4、v5 与当前摄入里哈希相同。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | yes | 开发路径（devcheck v5）与评分依据（v5 正式评分 + Codex）已核；按 `r2e-mr-034/035` 标明版本报告，合并实现在此版本得 0。批次运行条件属链路 |
| 训练候选 | yes | 核心要求有直接断言（revision_plan §7 第 215–225 行：两种对象读写、combine 生效、取回配置文件值、替换）；当前版本 noop 0、gold 1；§4 第 2 步（G3）与第 3 步（W2）已做；S2、X1 已登记 |
| 留出评测候选 | conditional | 差：① D3 仓库划分未定，本题与同仓 4 题有包含关系（X1），只能整仓同侧；② 若探针结果用于选模型、调提示或调配方即不再符合；③ 只能作标明版本的自建评测 |

## 剩余事项（已登记，不阻塞探针）

- **未覆盖**（revision_plan 第 212 行）：configurer 插件修改其它选项的既有流程（K5）；多组 `[paths]` 的顺序决定 combine 结果（K6）。不要求返回 `OrderedDict` 类型或同一对象，不要求 `~` 展开（第 157 行）。
- **G1 的一个边界**：只改转发层、同时让插件总拿到 `Coverage` 的写法会被 G1 拒绝。revision_plan 第 148 行判它不合理（`control.py:272-276` 的随机二选一是有意设计）并请 Codex 核对，Codex 复核没有单独表态。
- **题面小瑕疵**：Actual 说异常在 set 时抛出，示例实际在 get 处报错；只修 set 的候选得 0 有公开依据，不构成规格争议（`B2/review.md` 第 110–113 行）。
- **共享控制面**：隐藏测试导入候选可改的 `tests/coveragetest.py`，`TestCase` 基类来自非测试路径的 `coverage/backunittest.py`，评分时 pytest 读候选可改的 `setup.cfg`（`B2/review.md` 第 98–101 行；`B2/card.md` 第 35 行）。
- **X1**（`B2/review.md` 第 102–109 行）：初态与 `f5eb5f21` 逐字相同；本题修复与加强版目标测试在 `ea6906b0` 初态中；本题初态含 `5dbbe143`、`016af5f6` 的修复（公开包行为层面已核）。同族必须同侧。
- **解题侧**：公开命令加 `-p no:cacheprovider` 会与 `--failed-first` 冲突，要用 `-o addopts=""`；有 pip，不联网。
- **链路**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行；Codex `L/codex_reviews/review_probe_chain_20260929.md` 第 1–3 行"改后可以"）：
  - 求解入口换 `rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v5 正式评分即此口径）。
  - 接真实模型前先收口 Codex 的两项 P1：去掉静止屏障里以 root 执行的 git（第 9–31 行）；往返核对不一致、评分 fatal、清理未知时停止派发（第 33–41 行）。正式链直评冻结补丁的基线摘要问题可递延（第 43–51 行）。
  - GPU 机须载入同一 image ID（按 tag→ID 核对），重建换 ID 则本卡评分资格重出。账本 `env_qualification=absent`（回放未接 `--qualification-ledger`），能力统计前补接或单列（Codex 第 78 行）。
  - 模型实际收到的题面消息未对本题捕获。本机开销：rollout 从起容器到可信初始化完成约 88 s（devcheck 阶段时间戳）；评分 trusted setup 41–57 s（该步 300 s 硬时限）；测试段 5–6 s。

## 证据索引

- 旧卡：`B2/{card.md,screening_record.json,review.md}`（旧 usage 只有 `intended_use`）
- 修订：`L/results/coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266/{revision_plan.md,revision_draft.json,trials/}`；正式条目 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v5.json` 的 `r2e-mr-034`、`r2e-mr-035`
- Codex：`L/codex_reviews/review_revision_coveragepy.md` 第 5–17、48 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/ledger_{gold,noop,s1,s2,s3,s4,s5}.jsonl` 第 1 行、`F/remote/*_logs/`
- devcheck：`D/orig/attempt.json`、`D/orig/captures/`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v5/summary.json`
