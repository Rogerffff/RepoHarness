# pandas 4ec87eb9 独立复核：第二步（review.md）

2026-09-29 08:30 +08（本机时钟）。作者是独立复核者（Claude），补做 v1 §7.3 要求的每题独立复核；第一步初判见同目录 `reviewer_initial.md`。本步没有运行项目代码，没有开容器，也没有改任何原件；只读协调者列出的材料，以及修订单指向的修订后文件。

路径缩写（均相对仓库根目录）：

- `R` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199`
- `WT` = `runs/r2e_static_prep_20260924/v3/public/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/worktree`
- `F` = `runs/r2e_lifecycle_20260929/formal_v8`，`INV` = `runs/r2e_lifecycle_20260929/inv/pandas_4ec8`
- `D0` / `D` = `runs/r2e_lifecycle_20260929/devcheck_rev/{unrev,v8}/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199`
- `HT'` = 修订后的隐藏测试 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/files/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/r2e_tests/test_1.py`（343 行，sha256 `719e63ae…`，我已核对）
- `ING` = `rh2/src/repoharness2/envpack/ingest_r2e_subset.py`
- `CX` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/codex_reviews/review_revision_pandas_4ec8.md`
- 键名省略前缀 `test_groupby_quantile_`。

## 0. 结论

**同意的部分**

- 主审的 S1（T2b）在原材料上成立。退化候选 C0 在原材料上正式评分 1.0，行为对照证实它违反"忽略 NA"。
- `r2e-mr-055` 内容正确，正式验收通过：gold / noop / C0 / C1 = 1 / 0 / 0 / 1。它挡住了"直接读掩码数组底层缓冲"这一类候选。
- 同意：用 C1 作替代正对照、X1 登记、开发条件、T3 登记。

**要修改的部分：当前版本仍有未处理的 S1**

- 我初判的退化候选 D1，在当前材料（v9，已含 `r2e-mr-055`）上正式评分 1.0（237/237）。D1 的改法是把可空浮点并入整数分支，连带 `inference=int64`。
- 行为对照坐实它违反公开要求：题面原例加 `interpolation='lower'` 返回 int64 的 `[2]`，正确值是 `[2.5]`；无 NA 的 `Float64 [1.5, 2.5]` 配 `higher` 也返回 `[2]`。
- 按 v1 §4 第 3 步，当前版本仍是 S1（T2b）。主审第 4 步写的"暂无"已经过时。
- 准入卡的恢复条件"复核同意主审即改标 probe_ready"不成立。

**dtype 的定性：维持 P3，不判 T1，也不判 P5**

- 主审低估了反向依据：v1.2.0 whatsnew 第 224–225 行写明"可空整数 / 布尔的运算得到浮点结果时改用可空浮点"；groupby 的 mean / median 也保留可空 dtype。
- 但"返回 `Float64`"这种读法要改变同一调用在同一 dtype、无 NA 时的既有结果（base 返回 float64，devcheck 已实测）。两种读法并不对称，所以仍归 P3。
- 我给出一个判别标准，供与 f5eb 的口径对齐（第 5 节）。f5eb 的 Codex 复核我没有读。

**结构约束**

- 修 D1 需要的新断言无法并入 `test_1.py`，因为该目标已有 `r2e-mr-055`（`ING:415-417`）；也不能新增键，因为期望文件已有 `r2e-mr-007`。
- 现有机制下唯一技术可行的落法是"新增隐藏测试文件 + 通过即跳过的守卫"。这是新写法，有解析器上的脆弱点（第 7 节）。
- 因此交用户一个决定项，四个选项：A 维持现状（默认）、B 链式追加（我推荐）、C 合并取代、D 守卫文件。

**建议处置**

- 状态记 `needs_repair`（S1 未处理），维持 on_hold；用户决定前按 A 处理，不阻塞其它题。
- 当前版本的四项用途：问题定位 yes；能力比较 conditional（预登记 D1 型事后审计与 dtype 争议规则）；训练候选 no；留出候选 no。

## 1. 第二步的读取范围与证据核对

- **读了**：
  - 公开读者产物：`R/public_read.md`、`R/commands.json`。
  - 主审产物：`R/analysis_before_history.md`、`R/old_findings_delta.md`、`R/card.md`、`R/screening_record.json`、`R/cands/`（C0、C1、C1rev、D1rev、W2rev 补丁，以及 `private_check_A2.py`）。
  - 修订：`R/revision_plan.md`、`R/revision_draft.json`（摘要）、`R/trials/`（只看了文件清单与判读，没有逐份展开 JSON）、`CX` 全文、`material_revisions_v8.json` 中本题三条（006 / 007 / 055）与文件头 `purpose`、`HT'` 第 249–302 行。
  - 历史：`refs.json` 所列文件中的 `findings.md`、`material_revisions/pandas__4ec8….md`、`decisions.md` 的 E09 / E16 / E21 / T0-5 / T0-6 行。其余只看到名字，没有展开：`screening_record.json`、`facts.json`、`known_issues.json`、`results_20260924.md`、`repros/`、`packages/p3/README.md`。
  - 实跑：`F/status.json` 中本题 4 行；`F/ledgers/ledger_{gold,noop,s1,s2}.jsonl` 各第 2 行；`F/remote/{gold,noop,s1,s2}_logs/` 四份日志；`INV/ledger_{C0,C1}.jsonl`、`INV/ledger_{D1rev,W2rev,C1rev}_v9.jsonl` 各第 1 行及对应日志；`INV/pcheck_{none,gold,C0}.json`、`INV/pcheck_interp_{none,gold,D1rev,W2rev,C1rev}.json`、`INV/pcheck_interp.py`、`INV/run_rev.{sh,log}`；`D0` 与 `D` 的 `devcheck.log`、`orig/captures/{variants_float_masked,env_import_version,public_test_quantile}.out`、`D/private_control.json`；`runs/r2e_lifecycle_20260929/env_verify/ledger_l2_{noop,gold}.jsonl` 第 8 行；`R/probe_card.md`。
  - 代码（只读，为核对结构约束与解析口径）：`ING` 第 360–420、470–600 行；`rh2/src/repoharness2/envpack/r2e_parsers.py` 第 88–110 行；`rh2/src/repoharness2/envpack/scoring.py` 第 463–476 行；`rh2/experiments/r2e_lifecycle_20260929/formalize_revisions.py` 第 1–20、84–100 行。
  - 公开包补查：`WT/pandas/core/groupby/ops.py` 第 296–316、340–385 行；`WT/doc/source/whatsnew/v1.1.0.rst` 第 1133–1137 行、`v1.2.0.rst` 第 183–230 行；`WT/doc/source/user_guide/integer_na.rst` 第 100–150 行。
- **没读**：本批 README、`board.json`、`assignments.json`、除 `CX` 以外的 `codex_reviews/`（包括 f5eb 的 Codex 复核与本题的 `prompt_revision_pandas_4ec8.md`）、其它题的私有包。准入卡引用的 README 第 17–25 行与 f5eb 复核，我只能依据准入卡的转述。
- **身份核对**：
  - 正式第 5 轮 4 行，以及 D1rev / W2rev / C1rev 三行，镜像都是 `c057430b…`，评分日志的 `RH2_SETUP_HIDDEN_TESTS_TREE` 都是 `ec3a3499…`。所以 v9 与 v8 在本题上是同一份材料。
  - C0 / C1 的首轮评分与 `env_verify` 用的是修订前镜像 `85f550e6…`。
  - 行为对照 `pcheck_interp_*` 也在 `85f550e6…` 上跑。它只用源码行为，不用隐藏测试，所以镜像不同不影响结论；但它不是"v9 材料上的"运行，这里如实记下。

## 2. 逐项核对主审的决定性主张

| # | 主审主张 | 我的判断 | 证据 |
| --- | --- | --- | --- |
| 1 | 当前材料 noop 0、gold 1，4 个目标键以题面报错失败 | 同意 | 旧机两次；新机 `env_verify` 第 8 行 noop 233/237、gold 237/237（镜像 `85f550e6`）；v8 正式评分同样 |
| 2 | C0 只凭 gold 的修改位置写出，属于"抑制症状 / 作用在无关对象上"；原材料正式评分 1.0 | 同意 | `INV/ledger_C0.jsonl` 第 1 行：237/237，补丁 `cc92ca6f…`，投影只含 `groupby.py`。C0 与我初判的 W2 基本等价（W2 多了 `is_float_dtype` 条件，但整数和布尔掩码数组在前面的分支已被处理，效果相同） |
| 3 | C0 违反"忽略 NA" | 同意 | `INV/pcheck_C0.json`：astype / reindex / 除法依次得 `[1.0]` / `[0.0]` / `[1.0]`，gold 得 `[2.0]` / `[2.5]` / `[2.0]` |
| 4 | 第 2 步（只用示例字面值）不命中 | 同意，附一点说明 | 我初判记 conditional，理由是"同一输入形态"。`r2e-mr-055` 已补多组、多个有效值；剩下的单一形态是"浮点扩展数组只测默认 linear 插值"，它已由第 3 步的 D1 具体化（第 4 节），不必再按第 2 步重复判 |
| 5 | 第 4 步"目前没有真实模型候选，没有新增命中"（`R/analysis_before_history.md:151`，`R/card.md:52`） | **过时** | D1rev 在当前材料正式 1.0，且违反公开要求（第 4 节）。无论按第 3 步（退化）还是第 4 步（构造候选违反有文档的公开行为），都是 S1 |
| 6 | dtype 属 P3，不交用户（`R/card.md:119-127`） | 结论同意，理由修改 | 第 5 节 |
| 7 | R-c 草案（第 2 版并入已有键）正确，并已通过正式验收 | 同意 | 第 3 节 |
| 8 | 用途：训练 no（当前版本）（`R/card.md:35`） | 同意，并延续到修订后版本 v9 | 准入卡把训练写成 conditional，并写"复核同意即改 yes"（`R/probe_card.md:9, 36`）：不同意 |
| 9 | X1：`7dd34ea7` 初态逐字含本题 gold 与 3 个新测试；本题 base 含同仓 5 题的测试或修复 | 同意 | 与我初判的逐项核对一致 |
| 10 | T3：DataFrame 入口、混合列丢列、无 NA 时的 dtype、稀疏浮点路径 | 同意，需补充 | 非默认插值不是 T3，而是 S1（第 4 节）；"只在部分 NA 来源上把掩码位改成 NaN"的候选（`R/revision_plan.md:186-189`）保留在 T3 |

主审有没有"先看答案，再把隐藏要求说成显然"？没有。dtype 一节同时列了正反依据，只是反向依据举得不全（第 5 节）。

## 3. `r2e-mr-055` 的复核

- **内容**：在已有目标测试 `NA_float(any_float_dtype)` 的末尾并入两段断言（`HT':267-280`）：
  - 第一段：`Int64` 转浮点扩展类型，掩码位底层是 1.0，期望中位数 2.0；
  - 第二段：`reindex` 引入的 NA，掩码位底层是 0.0；分两组，其中一组有两个有效值，期望 `[3.0, 4.0]`。
  - 两段都用 `check_dtype=False`，期望映射不变（237 键）。
- **公开依据成立**：题面第 22 行；`FloatingArray` 文档（`WT/pandas/core/arrays/floating.py:194-197`）；`integer.py:225-228`；`masked.py:312-320, 380-387`。公开读者在没看隐藏材料的情况下，也把"忽略 NA 不应取决于掩码位底层存的是什么"列为合理推知需求（`R/public_read.md:25, 59`）。
- **没有扩大需求**：
  - 期望由"排除缺失后按线性插值取中位数"推出，不是照抄 gold；
  - `check_dtype=False` 不新增 dtype 约束；
  - numpy 浮点参数下，base 照旧通过（v8 正式 noop 日志第 1292–1294 行）。
- **正式验收**（`F/status.json` 本题 4 行；`F/ledgers/*` 第 2 行）：
  - gold 1（237/237）；
  - noop 0：mismatched 与修订前逐键相同，就是那 4 个目标键；
  - C0 0（235/237）：两个键都停在 `HT':272`，`[left]: [1.0]`、`[right]: [2.0]`（`F/remote/s1_logs/evallog_replay-r2e-v8-s1-0928223_908321f7.eval.log:33-72, 75-114`）；
  - C1 1。
  - 另外，我初判的两个候选在当前材料上也有了正式结果：W2rev 0（235/237，同样停在 `:272`，`INV/logs_W2rev/…_3c78ac5b.eval.log:60-72, 102-114`）；C1rev 1（237/237，`INV/ledger_C1rev_v9.jsonl` 第 1 行）。
- **仍然成立的限制**：
  1. 正式日志只能证明第一段挡住 C0；第二段能否单独挡住 C0，只有试跑诊断支持（`R/probe_card.md:24` 已写明）。
  2. 失败定位变粗：同一个键里现在有 4 组断言。
  3. 新断言全部用默认 `linear`，挡不住 D1（第 4 节）。
- **结论**：`r2e-mr-055` 是必要的修订，已完整验收，我同意；但它不足以解除本题的 S1。

## 4. D1：修订后仍未处理的 S1

- **补丁**（`R/cands/pandas_4ec8_D1rev.patch`，sha256 `c0292a95…`，与我初判的描述一致）：
  - 把 `pre_processor` 第一分支的条件改为 `is_integer_dtype(vals.dtype) or (isinstance(vals, ExtensionArray) and is_float_dtype(vals.dtype))`；
  - 分支体不变：可空浮点走 `to_numpy(dtype=float, na_value=np.nan)`，同时被设为 `inference = np.dtype(np.int64)`。
- **正式评分（当前材料）**：1.0，237/237（`INV/ledger_D1rev_v9.jsonl` 第 1 行）。
  - 补丁由 agent 身份 `git_apply` 应用，`RH2_SETUP_APPLY_RC=0`，投影只含 `groupby.py`；
  - 测试树 `ec3a3499…`；`NA_float` 的 5 个参数键都 PASSED，包括 `HT':272` 与 `:278-280` 的新断言（`INV/logs_D1rev/evallog_replay-r2e-inv-4ec8-D1re_05799b47.eval.log:3, 9, 11, 254-258, 272`）。
- **行为对照**（`INV/pcheck_interp_*.json`：root、断网、不是评分；脚本见 `INV/pcheck_interp.py`）：

  | 候选 | 原例 + `lower` | 无 NA 的 `[1.5, 2.5]` + `higher` | 可空整数除法后分组中位数 |
  | --- | --- | --- | --- |
  | none（base） | `TypeError`（题面那条） | 没执行到 | 没执行到 |
  | gold | `[2.5]` float64 | `[2.5]` float64 | `[1.5, 7.0]` float64 |
  | **D1rev** | **`[2]` int64** | **`[2]` int64** | `[1.5, 7.0]` |
  | W2rev | `[2.5]` | `[2.5]` | **`[0.5, 2.5]`** |
  | C1rev | `[2.5]` | `[2.5]` | `[1.5, 7.0]` |

  - **更正协调者的一句转述**："base 在无 NA 的 higher 这一例上本来正确"，这次没有执行证据。脚本第 3 行先抛错，后两行都没跑（`pcheck_interp_none.json` 的 stdout 为空）。
  - 这一点目前的依据是：源码推断（无 NA 时走 `np.asarray` → object → `astype(float)`，`inference=None`，不回写，`WT/pandas/core/groupby/groupby.py:2456-2457, 2461-2470`），加上 devcheck 在 base 上对无 NA `Float64` 的 linear 基线实测（`D0/orig/captures/variants_float_masked.out` 最后一行，`[3.0]`，float64）。
  - 如果需要直接证据：把 `pcheck_interp.py` 的三个用例各包一层 `try/except` 再跑一次 none，成本约 5 秒。
- **违反的公开要求**：
  - `GroupBy.quantile` 文档列出的五种 `interpolation`（`WT/pandas/core/groupby/groupby.py:2405-2408`）；公开旧测试对五种插值逐一对照（`WT/pandas/tests/groupby/test_quantile.py:12-55`）。
  - 题面的核心要求（NA 被忽略后给出正确分位数）在非默认插值这一实例上被违反：原例加 `lower` 应得 2.5，D1 得 2。
  - 还破坏了 base 上已有的行为：无 NA 的 `Float64` 在 `lower` / `higher` / `nearest` 下原本给出正确的浮点值，D1 截断成整数。
- **归类**：
  - 按第 3 步，D1 只凭 gold 的修改位置（同一个 `pre_processor` 的分派条件）就能写出，方向是"抑制症状"：借用现成的可空整数分支让 `TypeError` 消失，连带套用了整数的结果回写。它确已交付、相关测试确已执行，得 1 → S1（T2b）。
  - 如果有人认为 D1 不算"退化"，按第 4 步也一样：构造候选违反有文档的公开行为。
  - 它不是"边缘输入、罕见路径"：插值是被修方法的文档参数；公开测试对 numpy 浮点把五种插值都测了（198 个键）；受影响的是五种里的三种；错误是静默的错值加 int dtype，不会报错。
- **与 C0 的关系**：两类缺口相互独立。`r2e-mr-055` 管"掩码位底层值"，D1 管"结果回写类型"。W2rev 被挡住、D1rev 没被挡住，说明需要再加一处断言。

## 5. dtype：P3、T1 还是 P5

**两边的公开依据**（结果 dtype 是 float64 还是可空 `Float64`）：

- **支持 float64**：
  - 同一方法对可空 `Int64` / `boolean` 返回 float64，公开测试有断言（`WT/pandas/tests/groupby/test_quantile.py:215-236`）；
  - 同一调用在同一 dtype、无 NA 时，base 返回 float64（`D0/orig/captures/variants_float_masked.out`：`no_na_float64_baseline -> [3.0] | dtype: float64`）；
  - `post_processor` 只对整数推断做回写（`groupby.py:2461-2470`）；
  - v1.1.0 修同类可空整数问题时沿用了这一行为（`WT/doc/source/whatsnew/v1.1.0.rst:1135`）。
- **支持 `Float64`**：
  - groupby 的 mean / median / var 对可空浮点保留原 dtype，对可空整数与布尔返回 `Float64`（`WT/pandas/core/groupby/ops.py:307-311`，结果在 `373-382` 重建为扩展数组）；
  - `Series.quantile` 对掩码数组保留原 dtype（`WT/pandas/core/array_algos/quantile.py:44-46, 185`）；
  - **主审与我初判都没提到的**：v1.2.0 whatsnew 写明"可空整数或布尔的运算得到浮点结果时，现在也用可空浮点类型"（`WT/doc/source/whatsnew/v1.2.0.rst:224-225`，同段第 229 行标明为实验性）。
  - 题面说的"median"，与同一对象上 `.median()` 的 dtype（`Float64`）也能对上。

**不判 T1**：

- 按第二批补充规则第 1 条，要"满足全部公开要求、也不破坏受影响旧行为"的候选被判 0，才算合理误拒。
- 返回 `Float64` 的候选只有两种做法：
  - 对所有掩码输入保留 dtype：会破坏公开测试 `test_quantile.py:215-236`，以及对应的回归键 `nullable_array`、`NA_int`；
  - 只对浮点输入保留：会把无 NA 的 `Float64` 从 float64 改成 `Float64`，改变同一调用的既有结果。
- 两种都改变了受影响的旧行为，不属于"合理修复被误拒"。float64 断言也不是没有依据。

**不判 P5**：

- v1 的 P5 指"任务目标层面有两种读法"（`task_screening_standard_v1_20260925.md:79`）。本题的任务目标没有歧义：不报错、忽略 NA、数值正确。dtype 是输出格式。
- 更关键的是两种读法不对称：float64 读法 = "修 bug，不改已有行为"；`Float64` 读法 = "修 bug，同时改掉同一调用在无 NA 时的既有 dtype"。后者是超出本题范围的设计变更。
- 公开读者把它标为"多种合理解释"（`R/public_read.md:14, 36-41`），但同一节也写了"`float64` 与本方法现有约定最一致；改成 `Float64` 还会顺带改变 P2、P6 的现有结果"（第 41 行）。其实公开材料已经可以消除这一歧义。

**与 f5eb 的口径对齐**：f5eb 的 Codex 复核我没有读，下面是建议的判别标准，请 Codex 确认两题口径一致。

- 两种读法都是**新行为**、各有公开依据时 → P5（任务目标选择，交用户）。
- 其中一种读法是同一 API 对同类输入（只差触发缺陷的条件）的**既有可观察行为**时 → 保持既有行为是有依据的读法，另一种属于范围扩张 → P3（登记，不交用户）。
- 如果 Codex 在 f5eb 上的标准是"凡是输出形式二选一且两边都有依据就判 P5"，按那个标准本题也会成为 P5，结果是暂挂为问题定位并交用户。这是两个标准的实际分歧，需要统一。

**处理**（与主审一致，另加一条升级路径）：

- 登记为 P3，不修订。
- 探针与训练抽查时，把"其它都对、只有 dtype 是可空类型"的补丁单列为规格争议样本，原始 reward 保留。
- 出现 1 例真实模型的此类补丁，就改走 R-f：在题面补一句有公开依据的说明，例如"与可空整数输入一样，结果为普通 float64"。不要为此放宽已有的 dtype 断言，因为 R-b 不适用于有依据的约束。

## 6. D1 需要的修订（在我初判 R-c(a) 的基础上收窄并改变放置方式）

- **范围收窄**：`r2e-mr-055` 已覆盖"多组、多个有效值"，剩下的窄问题只有"可空浮点加 NA 在文档列出的插值方式下给出正确分位数"。
- **数据设计**：每组至少两个有效值；数值为非整数，这样截断会暴露；取 `q=0.4`，使两组的位置都落在两个有效值之间，而且没有等距平局。
- **公开依据**：题面的一般要求；文档里的五种插值；公开旧测试对插值的对照方式；无 NA `Float64` 在 base 上的既有行为。
- **不新增 dtype 约束**：断言用 `check_dtype=False`。
- **期望值**：两组有效值分别是 `[0.5, 1.5, 3.0]` 与 `[4.5, 9.5]`；位置 0.8 与 0.4；按 `group_quantile`（`WT/pandas/_libs/groupby.pyx:857-880`）手算，与 numpy.percentile 在没有平局时的结果一致。所用数值在 float32 下都能精确表示。

**写法一：并入宿主测试（用于第 7 节的 B / C）**。接在 `HT':280` 之后，仍在 `test_groupby_quantile_NA_float(any_float_dtype)` 内，不新增键：

```python

    # Documented interpolations on masked floats with NA: two groups, several
    # valid values each; q=0.4 falls strictly between valid values, no ties.
    ser = pd.Series([0.5, np.nan, 1.5, 3.0, np.nan, 4.5, 9.5], dtype=any_float_dtype)
    gb = ser.groupby([1, 1, 1, 1, 2, 2, 2])
    for interpolation, values in [
        ("linear", [1.3, 6.5]),
        ("lower", [0.5, 4.5]),
        ("higher", [1.5, 9.5]),
        ("nearest", [1.5, 4.5]),
        ("midpoint", [1.0, 7.0]),
    ]:
        result = gb.quantile(0.4, interpolation=interpolation)
        tm.assert_series_equal(
            result, pd.Series(values, index=[1, 2]), check_dtype=False
        )
```

numpy 浮点参数下，这段走 base 已有的 NaN 路径，照旧通过；noop 的观测映射与当前逐键相同。

**写法二：守卫文件（用于第 7 节的 D）**。新增隐藏测试文件 `r2e_tests/test_rh2_guard.py`：

```python
# rh2 material revision (R-c guard): GroupBy.quantile on nullable float data
# with NA must honour every documented interpolation. Convention: when every
# check holds the test ends with pytest.skip, so it adds no key to the expected
# map; any failure produces a key that is not in the expected map, which the
# exact-map rule scores 0. Keep upper-case status words out of the skip reason.
import numpy as np
import pytest

import pandas as pd
import pandas._testing as tm


@pytest.mark.parametrize("dtype", ["Float64", "Float32"])
def test_rh2_guard_quantile_masked_float_interpolation(dtype):
    ser = pd.Series([0.5, np.nan, 1.5, 3.0, np.nan, 4.5, 9.5], dtype=dtype)
    gb = ser.groupby([1, 1, 1, 1, 2, 2, 2])
    for interpolation, values in [
        ("linear", [1.3, 6.5]),
        ("lower", [0.5, 4.5]),
        ("higher", [1.5, 9.5]),
        ("nearest", [1.5, 4.5]),
        ("midpoint", [1.0, 7.0]),
    ]:
        result = gb.quantile(0.4, interpolation=interpolation)
        tm.assert_series_equal(
            result, pd.Series(values, index=[1, 2]), check_dtype=False
        )
    pytest.skip("rh2 guard ok")
```

**验收矩阵**（两种写法共用；"不符的键"一栏按写法一写，写法二的差异在备注里）：

| 候选 | 角色 | 预期 reward | 预期不符的键与失败位置 | 备注 |
| --- | --- | --- | --- | --- |
| gold | 正对照 | 1 | 无 | 写法二：日志里应有 `SKIPPED [2] r2e_tests/test_rh2_guard.py:…: rh2 guard ok`，作为守卫确已执行的证据 |
| C1（主审：统一的掩码数组分支，保留整数 `inference`） | 替代正对照 | 1 | 无 | 同上 |
| C1rev（我：浮点扩展数组单独分支，不设 `inference`） | 替代正对照 | 1 | 无 | 同上 |
| noop | — | 0 | 原来的 4 个目标键 | 写法二还会多出 2 个 unexpected 守卫键 |
| C0 / W2rev | 已知错误解（掩码位底层值） | 0 | `NA_float[Float32/Float64]`，仍停在 `HT':272` | 写法二：守卫 SKIPPED（构造器数据的掩码位是 NaN） |
| **D1rev** | 触发反例（整数回写） | 0 | `NA_float[Float32/Float64]`，停在新段的插值断言（`lower` 轮）；应显示类似 `[left]: [0, 4]`、`[right]: [0.5, 4.5]` | 写法二：原 237 键全部相符，另有 2 个 unexpected 守卫键 FAILED |

- 另外要核对：
  - 原有 237 个键的键名与状态不变；
  - 完整日志里 D1rev 的失败行号与数值；
  - 保存新旧版本、修订理由与触发反例（D1rev 补丁 `c0292a95…`，`INV/ledger_D1rev_v9.jsonl` 第 1 行）；
  - 交 Codex 复核。
- 最少正式评分 5 次：gold、noop、D1rev、C1rev、C0。建议 7 次，再加 C1、W2rev。

## 7. 结构约束：现有机制下能不能落

**机制事实**（只读代码）：

- 同一题同一目标只允许一条修订（`ING:415-417`）；`formalize_revisions.py` 遇到这种情况会停下，要求"人工合并为一条新修订"（第 5–6、89–91、125 行）。
- 隐藏测试的文本修订从**来源原文**重放 edits（`ING:535-543`），不从上一版修订后的文本重放。
- 期望修订的应用本来就是逐条接着上一条作用的（`ING:510`）；消费侧的 `effective_hidden_files` 也按顺序套用 `sha256_before` → `sha256_after`（`ING:573-585`）。
- `hidden_test_file_add` 允许新增来源清单里没有的文件（`ING:524-529`）。

**逐条看落法**：

| 落法 | 能否落 | 原因 |
| --- | --- | --- |
| 在 `test_1.py` 里再加断言（写法一） | 不能 | 目标 `test_1.py` 已有 `r2e-mr-055` |
| 新增测试函数、增加期望键 | 不能 | 期望目标已有 `r2e-mr-007`（用户批准），而且新函数也要改 `test_1.py` |
| 改私有 `conftest.py` | 不能 | 已有 `r2e-mr-006`（用户批准） |
| 新增隐藏测试文件，写正常测试 | 不能 | 会产生期望里没有的键，gold 也会得 0，除非改期望 |
| 新增文件，复用已有键名"撞键"覆盖状态 | 能落，但不采用 | 依赖解析器按行覆盖的顺序（`r2e_parsers.py:100-110`），属于撞键缺陷 |
| **新增文件，用守卫写法（写法二）** | **能落** | 目标是新文件，期望映射不变；正确解下守卫以 SKIPPED 结束、不成键；错误解产生 unexpected 键判 0（`scoring.py:463-476`） |

**守卫写法的代价**：

1. 期望映射不再列出全部评分要求，这条要求只写在隐藏测试代码里。
2. 它依赖两条口径：SKIPPED 不成键；解析器按**子串**识别状态词。跳过原因、文件名、函数名里都不能出现大写的 `PASSED` / `FAILED` / `ERROR`，否则会生成空键或错键（`r2e_parsers.py:100-110`）。
3. 诊断里失败显示为 `unexpected`，而不是 `mismatched`。
4. 以后如果解析器改为给 SKIPPED 行建键，本题的正确解会得 0。
5. 它给后续题开了先例。

我认为它仍属 R-c 模板内的"补隐藏测试"，但需要 Codex 先复核这种写法，并在环境卡登记这一约定。

**交用户的决定项**：本题的 D1 缺口要不要修，怎么落。不修不阻塞其它题。

| 选项 | 做法 | 后果 |
| --- | --- | --- |
| **A. 维持现状**（默认） | 当前版本（006 / 007 / 055）只作问题定位，以及带审计的能力比较；不进训练 | 零成本。pandas 少一道训练候选；D1 型补丁靠预登记审计识别。v1 §10 的 mypy10424 先例允许"有 S1、没修订机制"的题带审计作能力比较；用户也可以选更严的"只作问题定位" |
| **B. 链式追加**（我推荐） | 允许同一目标有多条修订，按编号依次作用：后一条的 `sha256_before` 等于前一条的 `sha256_after`。改 `ING:415-417` 的唯一性检查为"链式检查"；改 `ING:514-543`，从上一版修订后文本重放；`formalize_revisions.py` 不再遇冲突停下；补摄入单测。之后 D1 断言作为第 2 条 `hidden_test_text_replace`（写法一）落地 | 修订单继续逐轮只追加；已批准的 006 / 007 与已复核的 055 一字不改，每一环各有复核记录。机制可以复用：本批"修订后再复核"的流程还会碰到同目标二次修订。代价是改共享摄入代码（B 线），需要一次代码复核、一次重新摄入与镜像重建 |
| C. 合并取代 | 新版本修订单删去 055，追加一条合并了 055 与 D1 断言的新条目（从来源原文重放两处 edits）；不改代码 | 打破"逐轮只追加"；055 的 Codex 复核要对合并条目重做；新旧修订单版本要写清取代关系。适合一次性处理，不建议作为常规 |
| D. 守卫文件 | 新增 `r2e_tests/test_rh2_guard.py`（写法二，`hidden_test_file_add`）；不改代码，不动 006 / 007 / 055 | 见上面"守卫写法的代价"。需要 Codex 先认可写法，并在环境卡登记 |

**我的建议**：用户决定前按 A。如果希望本题以及以后的同类题能进训练，选 B。只有在既不想改代码、也不想破例改修订单时，才考虑 D，前提是 Codex 认可守卫写法。

## 8. 反查主审没想到的范围

- **非默认插值**：主审与公开读者都注意到了整数输入在 `lower` / `higher` / `nearest` 下会回写 int64（`R/public_read.md:31, 53`，"合并成一条掩码数组分支时必须保留整数的 inference"）。但没有人反过来查"浮点扩展数组被错误套上整数 inference"。D1 正是这一类。
- **dtype 的反向依据**：v1.2.0 whatsnew 的可空浮点政策、groupby mean / median 的结果类型、题面"median"与 `.median()` 的对应，见第 5 节。
- **行为对照的覆盖缺口**：`pcheck_interp.py` 在 base 上第一行就抛错，后两行没有 base 结果，见第 4 节。
- **T3，维持登记**：
  - 浮点扩展数组的 DataFrame 入口、混合列不丢列、无 NA 时的 dtype、稀疏浮点路径；
  - "只在部分 NA 来源上把掩码位改成 NaN、quantile 里仍直接读 `_data`"的候选；
  - `r2e-mr-055` 没用"可空整数除法"这一来源（与 astype 同类，行为对照已覆盖）。
- **通用控制面**（非本题）：隐藏测试依赖候选可改的 `pandas._testing`，候选能在 `/testbed` 根目录新建 `conftest.py`，交 A 线。守卫写法同样受这一点影响。

## 9. v1 §4 五步（当前版本 v9：006 / 007 / 055）

| 步 | 结果 | 证据 |
| --- | --- | --- |
| 1 核心要求有直接断言 | 有，不命中 | `NA_float[Float32/Float64]`（`HT':257, 265`） |
| 2 只用示例字面值 | 不命中 | 值、dtype、q 形式、NA 来源、多组都有示例之外的实例 |
| 3 退化探测 | **命中**。C0 在原材料 1.0，已被 055 挡住（v8 正式 0）；**D1rev 在当前材料 1.0**，违例已由行为对照证实 | `INV/ledger_D1rev_v9.jsonl` 第 1 行；`INV/pcheck_interp_D1rev.json` |
| 4 构造候选违反其它实例或有文档的行为 | 同第 3 步（D1）；W2rev 已被挡住；没有真实模型候选 | `INV/ledger_W2rev_v9.jsonl` 第 1 行 |
| 5 | 不适用 | — |

**当前版本严重度：S1（T2b），证据齐全（正式评分加行为对照），不是 conditional。**

## 10. 四项用途（当前版本 v9）与探针就绪差距

| 用途 | 结论 | 条件与依据 |
| --- | --- | --- |
| 问题定位 | yes | — |
| 能力比较 | conditional | 开发路径、评分依据、运行条件都已核（`D0`、`D` devcheck 全真；v8 正式 4 行与期望一致）。还差：①预先登记 D1 型事后审计，见下；②dtype 争议规则（第 5 节）；③按"006 / 007 / 055 标明版本"报告；④批次级链路条件（adapter、模型实际收到的消息）。原始 reward 与语义结果分列 |
| 训练候选 | no（当前版本） | 有未处理的 S1（D1）。按用户选定的 B / C / D 落地并按第 6 节矩阵验收、Codex 复核后，按新版本重判 |
| 留出候选 | no（当前版本） | 训练质量条件不满足；只能作标明版本的自建题；X1（`7dd34ea7` 初态含本题答案，须与 pandas 同仓题同侧）；有审查暴露 |

`intended_use` 保持 `development_diagnostic`。

**D1 型事后审计（预登记，修订落地前每个得 1 的补丁都跑）**：

- 在 `INV/pcheck_interp.py` 的基础上，把三个用例各包 `try/except`。
- 判语义 FAIL 的条件：`lower`（带 NA）不等于 2.5；或 `higher`（无 NA）不等于 2.5；或结果 dtype 为整数；或可空整数除法的结果不等于 `[1.5, 7.0]`（最后这一项现在已由 055 覆盖，保留作廉价的双保险）。
- 值都对、只有 dtype 为可空浮点的，记为 dtype 争议样本，不记 FAIL。

**探针就绪差距**（README §3 我没读，对照准入卡的五条与 v1 §2）：

| 条件 | 状态 | 谁来补 |
| --- | --- | --- |
| 正式评分与期望一致（v8：gold / noop / C0 / C1） | 已满足 | — |
| devcheck（修订前、后两次） | 已满足 | — |
| S1 处理 | **未满足**：C0 已修，D1 未修 | 用户选落法 → Claude 实施 → 按第 6 节矩阵正式评分 → Codex 复核 |
| 独立复核 | 本文完成 | 协调者收敛分歧（第 11 节） |
| dtype 口径与 f5eb 对齐 | 未完成 | Codex 确认第 5 节的判别标准 |
| 修订落地前进探针时的事后审计 | 需预登记 | 协调者 |
| 链路（adapter、模型实际收到的消息） | 未知（批次级） | A 线 / 协调者 |

## 11. 同意、修改、保留

- **同意**：
  - 原材料上的 S1（T2b，C0）；
  - `r2e-mr-055` 的内容与正式验收；
  - C1 作替代正对照；
  - 开发条件、X1、T3 登记（外加第 8 节的补充）；
  - dtype 不修订、不交用户（P3）。
- **修改**：
  - 当前版本仍是 S1（D1）；
  - 主审第 4 步的"暂无"过时；
  - 训练候选与留出候选在当前版本都是 no；
  - 准入卡"复核同意即 probe_ready"的恢复条件不成立；
  - dtype 的理由要补上反向依据，并按第 5 节的判别标准论证；
  - 我初判的 R-c(a) 收窄为只补插值，放置方式改为第 7 节 B / D 两种之一；我初判的 R-c(b) 已被 055 取代。
- **保留（未决，交协调者或 Codex）**：
  1. dtype 的 P3 / P5 判别标准与 f5eb 是否一致；
  2. 守卫写法可不可以作为模板内写法；
  3. 如有人把非默认插值视为"罕见路径"（从而 D1 只算 S2 / T3），我保留 S1 的判断，理由见第 4 节。
- **最小后续实验**：
  1. 用户选定落法后，按第 6 节矩阵正式评分，至少 5 次。
  2. 可选：给 `pcheck_interp.py` 各用例加 `try/except` 后重跑 none，直接取得"无 NA `Float64` + `higher` 在 base 上为 2.5"的执行证据。
  3. Codex 复核所选机制（B 的代码、C 的破例或 D 的写法），以及 D1 断言本身。
