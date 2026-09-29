# orange3 4014f248：R-c 修订方案（补"去重不能丢掉不同值之间的切点"的非退化断言）

2026-09-29 · 修订执行者（Claude，单题闭环试行；统一标准 v1 §5 模板内，Claude 执行、Codex 复核）。

**状态：一项 R-c，并进已有目标测试 `TestEqualFreq.test_below_precision`，不新增键，期望映射不变。修订草案下 8 个候选试跑，结果全部与预期一致（用的是试跑工具，不是正式评分）。不需要用户决定。** 下一步由协调者落正式修订单和派生镜像材料，按放宽的时限跑正式评分，再送 Codex 复核。

路径约定（相对仓库根；`trials/`、`cands/`、`probe_card.md`、`static_check_seg3.py`、`revision_draft.json` 相对本目录）：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/orange3__4014f2483e3bab0621c9ae0f994947c008183253/`，`W` = `PUB/worktree`。
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/orange3__4014f2483e3bab0621c9ae0f994947c008183253/`；`HT` = `PRIV/hidden_tests/test_1.py`（父版本，347 行）；`HT'` = 修订后的 `test_1.py`（362 行）。
- `B2` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/orange3__4014f2483e3bab0621c9ae0f994947c008183253/`。
- `INV` = `runs/r2e_lifecycle_20260929/inv/orange3_4014/`；`P` = `runs/r2e_lifecycle_20260929/probe_proto/runs/`；`G` = `runs/r2e_actor_20260925/grader/`；`GC` = `runs/r2e_actor_20260925/grader_cands/`。

## 1. 模板与要纠正的误判

**模板：R-c**（v1 §5）。一处修改，对应一个 S1。

| 项 | 要纠正的 S1 | 触发反例（当前材料） | 出处 |
| --- | --- | --- | --- |
| R-c 1 | T2b（v1 §4 第 3 步）。目标测试两段都只断言 `len(np.unique(points)) == len(points)`（`HT:57`、`:66`），所以把切点全部丢掉也算"唯一" | DG（`cands/orange3_4014_DG_dup_to_empty.patch`）：在 `EqualFreq.__call__` 的非 SQL 分支、`split_eq_freq` 之后，只要切点有重复就置 `points = []`。正式评分 1.0（27/27），见 `INV/ledger_DG_budget1200.jsonl:1`；日志 `INV/logs_DG/evallog_replay-r2e-inv-4014-DG-0_e15585e8.eval.log` 第 26 行 `PASSED …test_below_precision`、第 53 行 `27 passed` | `probe_card.md` 第 29、47 行；`B2/review.md` 第 95–97 行（09-25 复核者只做了静态判断，没有实跑） |

**本轮不做**：
- **C3 的小量级分辨率缺口**（`round(p, 10)` 后再去重）：v1 §11 记为 S2，不是 S1。新断言不针对它，C3 修订后仍得 1（§5.2）。复核者提的可选修订（`arange(100)*1e-12`、n=4、每个区间 25 个值，`B2/review.md` 第 121–125 行）照旧只作可选项，见 §6。
- **I1（编译交付）**：已由探针原型结案（`probe_card.md` 第 8 行）。本轮只确认修订不会误拒编译路径的正确解。

## 2. 公开依据

**DG 违反的公开要求。** 数据里有一簇只差 1 ulp 的值，两侧另有明显分开的值。DG 会把全部切点丢掉，整个变量只剩一个 `single_value` 区间，于是分开的值和近重合簇落进同一个区间。

1. **题面**（`PUB/user_prompt.txt`）
   - `:7` 描述的问题是 "generates non-unique threshold points"；
   - `:26-27`（Expected）要求 "all threshold points are unique … the resulting `points` list should contain distinct values, allowing the creation of valid intervals where each interval has a lower bound less than its upper bound"。
   - 这条要求针对的是切点之间的重复：让切点互不相同，从而建出有效区间。它没有允许丢掉本来就互不相同的切点，也没有允许把一个有多个不同值的变量整个退成一个区间。
2. **`EqualFreq` 的 docstring**（`W/Orange/preprocess/discretize.py:125-132`）
   - 原文 "Discretization into bins with approximately equal number of data instances"；
   - 对 n 的说明是 "Number of bins … The actual number may be lower if the variable has less than n distinct values"。
   - 文档只说明了一种区间变少的情形：不同值少于 n。n ≥ 不同值个数时，明显分开的值应分进不同区间（与第 3 条的公开测试一致）。相邻的近重合值之间没有可表示的中点，按中点切分时合并其中一部分是去重的自然结果（gold 也如此），但这不延伸到明显分开的值。
   - 公开文档意思相同：
     - `W/doc/visual-programming/source/widgets/data/discretize.md:20`："splits the attribute into a given number of intervals, so that they each contain approximately the same number of instances"；
     - `W/doc/data-mining-library/source/reference/preprocess.rst:53-54`：默认是 "four bins with approximatelly equal number of data instances"。
3. **公开旧测试**（`W/Orange/tests/test_discretize.py`，同时也是隐藏测试里的回归键）
   - `:38-44` `test_equifreq_with_k_instances`：4 个不同值、n=4，得到 4 个区间、切点 `[1.5, 2.5, 3.5]`。n ≥ 不同值个数时，每对相邻的不同值都在中点切开；
   - `:20-28` `test_equifreq_with_too_few_values`：两个值得到 2 个区间，切点 `[0.5]`；
   - `:68-74` `test_equalwidth_const_value`（实际测的是 EqualFreq）：只有常数列才得到 `[]`、1 个区间；
   - `:155-159` `test_discretizer_computation`：`compute_value.transform` 把值映射为区间序号。新断言用的就是这个公开接口。
4. **切点为 `[]` 的公开后果**（说明 DG 不只是"少了几个切点"）
   - `W/Orange/preprocess/discretize.py:69-77`：切点为空时，变量只有 `"single_value"` 一个取值；
   - `W/Orange/preprocess/preprocess.py:71-73、96-99、111`：默认的 `Discretize()` 用 EqualFreq；`remove_const=True` 的文档写的是去掉 "features with constant values"，实现上按 `len(new_var.values) >= 2` 判断；
   - `W/Orange/preprocess/discretize.py:704-713、742、748`：`DomainDiscretizer` 默认用 `EqualFreq(n=4)`，`clean=True` 时会去掉 "discretized into a single interval" 的特征；
   - 所以在 DG 下，一个不是常数、只是含几个近重合值的特征，会被默认预处理静默删掉，与"只删常数特征"的文档不符。
5. **旧公开读者的结论**（`B2/public_read.md`；读者没看过隐藏测试和 gold）：支持保留正常行为、接受多种修复方式，但不能单独推出本修订的两侧分离断言。
   - 第 18 行：修复后切点的个数和取值没有约定（去重剩 2 个点，或保持 3 个点、把相撞的点换成其它可表示的浮点数，都满足"唯一"）；
   - 第 30、31 行：正常数据的结果保持不变（R5）；允许区间数少于 n（R6，间接依据是 docstring）；
   - 第 45–48 行：列出的四类合理实现（A–D）都保留不同值之间的切点，没有一类丢掉全部切点。
   新断言由第 1–4 条的公开材料（题面、docstring、公开旧测试与公开源码）联合推出，不依赖本条。（协调者 09-29 07:02 按 Codex 复核 `codex_reviews/review_revision_orange3_4014.md` §1 更正本条转述；原稿把第 18、31 行误述为"要求去重""只在文档允许时才能减少"。测试草案不变。）

**为什么选这组数据。**
- 数据是 `X = [0, 1, 1+ε, 1+2ε, 1+3ε, 2]`，调用 `EqualFreq(n=6)`。6 个不同值，n ≥ 不同值个数，走的是和题面原例同一个分支：相邻值取中点（`W/Orange/preprocess/_discretize.pyx:16-17`）。
- 近重合簇沿用题面原例的四个值。它们相邻中点按就近取偶舍入后会相撞，这是重复切点的来源。0 和 2 是明显分开的值。
- 按 `_discretize.pyx:12-57` 逐行转写成纯 Python（`static_check_seg3.py`，不导入项目代码），base 的切点是 `[0.5, 1, 1+2ε, 1+2ε, 1.5+2ε]`。重复只出现在簇内；0.5 和 1.5+2ε 两个切点不重复，任何只做去重的实现都会保留它们。
- **为什么 n 要取 6，而不是默认的 4**：
  - n < 不同值个数时走循环分支，等频切分本来就可能把 2 和簇里的值分进同一区间。例如 n=4 时 base 切点是 `[0.5, 1+2ε, 1+2ε]`，gold 去重后是 `[0.5, 1+2ε]`，2 与 1+2ε、1+3ε 在同一区间。
  - 所以区间顺序断言只在 n ≥ 不同值个数时有依据（§2 第 2、3 条）。
- **断言只要求一件事**：0 所在区间低于簇里每个值的区间，2 所在区间高于簇里每个值的区间。它不规定：
  - 切点的个数和位置；
  - 簇内怎么切分；
  - 标签，以及有没有空区间；
  - 修在哪里：`discretize.py`、`create_discretized_var`，或者重编后的 `_discretize.pyx` 都行。

## 3. 具体改动

- **目标文件**：`r2e_tests/test_1.py`，也就是唯一的隐藏测试文件 `HT`。
- **草案条目**：一条 `hidden_test_text_replace`，一处 edit。
  - `old` 是 `HT:64-66`：第二段 `EqualFreq(n=8)`、`points`、唯一性断言这三行，含换行。因为 `n=8`，它在全文只出现一次；
  - `new` 是原三行，加一个空行，再加下面的第三段。
- **修订后位置**：第三段在 `HT'` 第 68–81 行，仍在 `TestEqualFreq.test_below_precision` 里。新断言在第 80、81 行。

```python
        # Test with near-duplicate values among clearly distinct values
        # (n >= number of distinct values): making the points unique must
        # not drop the thresholds between the distinct values, so 0 and 2
        # still fall into intervals below and above all values around 1
        X = np.array([[0], [1], [1 + eps], [1 + 2 * eps], [1 + 3 * eps], [2]])
        # Test the test: check that these are indeed distinct values
        assert len(np.unique(X).flatten()) == 6
        table = data.Table.from_numpy(None, X)
        var = discretize.EqualFreq(n=6)(table, table.domain[0])
        points = var.compute_value.points
        self.assertEqual(len(np.unique(points)), len(points))
        bins = var.compute_value.transform(X.flatten())
        self.assertLess(bins[0], min(bins[1:5]))
        self.assertGreater(bins[5], max(bins[1:5]))
```

**设计说明**：
- **写法沿用前两段**：同样的 "Test the test" 输入校验和唯一性断言，只多两条区间顺序断言。不新增导入，不依赖 base 版测试辅助，没有随机或时序因素。
- **并进已有目标测试、不新增键**（协调者要求优先这样做）。
  - 好处：期望映射不变，R2E"键集必须完全相同"的约束不受影响。
  - 代价：一个键里有三段，失败出在哪一段要看日志行号。目前行号能区分：noop 和"只改 `.pyx` 不重编"停在第 55 行，C4 停在第 64 行，DG 停在第 80 行（§5.2）。修订前 noop、不重编补丁、C4 失败的键完全相同，现在反而更好区分。
- **初稿与定稿**：
  - 初稿的区间断言是"`[0, 1, 2]` 三个值落在三个不同区间"。定稿前用纯 Python 转写核对，发现它太松：一种"不断减小 n 直到切点唯一"的写法（n 降到 3，切点 `[1, 1+2ε]`）会把 2 与 1+2ε、1+3ε 放进同一区间，却仍满足"三个值三个区间"。
  - 所以定稿改为"0 低于簇内每个值、2 高于簇内每个值"，与注释和依据一致。
  - 初稿只上传过远端，没有用它跑过试跑；草案下的所有试跑都用定稿（sha256 见 §4），DG 日志里打印的测试源码就是定稿内容。
- **刻意不测**：
  - 切点个数、簇内切点的位置；1 与 1+ε 能否分开（两者之间没有可表示的中点）；
  - 空区间、区间标签（R11）、EqualWidth（R10）、SQL 分支；
  - 循环分支（n < 不同值个数）上的非退化，理由见上面"为什么 n 要取 6"；
  - 小量级分辨率（C3，S2）。

## 4. 期望映射逐键变化

- **无变化**：27 个键全为 PASSED，`TestEqualFreq.test_below_precision` 仍是唯一的目标键。`added`、`changed`、`removed` 都为空；正式修订单只需要 `hidden_test_text_replace`，不需要 `expected_file_replace`。完整映射见 `revision_draft.json` 的 `expected_after`，与父版本逐键相同。
- **期望从哪里来**：新断言的要求来自 §2 的公开依据。gold 通过是验证结果，不是依据。断言不涉及切点的值或个数，所以没有复制 gold 的输出。
- **版本记录**：

  | 文件 | sha256 |
  | --- | --- |
  | 父版本 `test_1.py`（`HT`，347 行） | `4321647a…` |
  | 父版本 `expected_output.json`（27 键） | `07f34ad4…` |
  | 父版本隐藏测试树 | `98a4a29e…`，`material_revisions` 为空 |
  | 修订后 `test_1.py`（`HT'`，362 行） | `477e4252…` |
  | 试跑用 `draft.json` | `43bfc0ea…` |
  | 试跑用 `expected_after.json`（27 键） | `fdd48c66…` |
  | 静态核对脚本 `static_check_seg3.py` | `c6f4300e…` |

  - 父版本三项与当前正式材料 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl` 第 24 行一致；本题至今没有材料修订。
  - `expected_after.json` 与父版本内容相同，只是排版不同，所以文件哈希不同。
  - 全长哈希见 `revision_draft.json`。

## 5. 验收计划与试跑结果

**试跑环境**：
- **工具**：`rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`，只作试跑。据文件头，它与正式评分有四点不同：
  - 不做基线重建比对；
  - 不核隐藏测试树与入口摘要；
  - 以 root 身份应用补丁（正式评分用 agent/54321）；
  - 权限布置简化为把整个 `/testbed` 交给 54322。
- **派生镜像**：`sha256:3cab63e6b382…`（`rh2-r2e-derived/orange3:4014f2483e3b-r2e_derive_v1s`，配方 `r2e_derive_v1+sysconfig_v1`）。与 DG 正式账本、`budget_v5` 和探针原型记录的 `image_id_actual` 相同。
- **补丁核对**：
  - gold、DG、C1、C3、C4 先在仓库外的 base 副本上跑 `git apply --check -v`，全部通过。副本里 `discretize.py` 的 blob 是 `75656829`，`_discretize.pyx` 的是 `071a3f68`，与各补丁的 index 行一致；
  - 两份探针原型补丁按协调者指定直接用远端原件。本地副本的 sha256 与探针正式账本的 `candidate_patch_sha256` 相同；远端原件的哈希没有另测，因为远端只允许建目录、上传、试跑三类命令；
  - 试跑时 `git apply -v` 对这两份补丁分别列出 5 个和 1 个文件，全部显示 `Applied … cleanly`。
- **每次试跑的完整性**：
  - 除 noop 外都是 `RH2_APPLY_RC=0`；
  - 修订版试跑都报 `RH2_TRIAL_EDITS_APPLIED=1`；
  - 27 个键全部解析，没有 missing / extra。
- **耗时**：单次墙钟 255–345 s，几乎都花在属主改写上；测试本身 3.1–5.0 s。同一时间最多跑 2 个。

### 5.1 当前材料上的对照（不进 acceptance）

| 候选 | 结果 | 出处 |
| --- | --- | --- |
| noop | 0：只错 `test_below_precision`，`test_1.py:55` → `discretize.py:53`，`low = high = 1.0000000000000004` | `trials/env_noop_current.json`（试跑）；正式评分 `runs/r2e_lifecycle_20260929/budget_v5/ledger_noop.jsonl` 第 7 行 |
| gold | 1：27/27 | `trials/env_gold_current.json`（试跑）；正式评分 `budget_v5/ledger_gold.jsonl` 第 7 行 |
| DG | **1**：27/27（本次的触发反例） | 正式评分 `INV/ledger_DG_budget1200.jsonl:1` |
| 重编补丁 | 1：27/27 | 正式评分 `P/orange3_4014_pyx_build/grade_cc2/`（`summary.json` 的 `regrade.2.cc`） |
| 不重编补丁 | 0：26/27，只错 `test_below_precision` | 正式评分 `P/orange3_4014_pyx_only/grade_cc2/` |
| C1 / C3 / C4 | 1 / 1 / 0（C4 停在第二段 `test_1.py:64`） | 09-25 在旧镜像 `22558531…` 上的正式评分（配方少 `+sysconfig_v1`，材料相同）：`G/ledger_o4014_*.jsonl` |

### 5.2 修订草案下的验收

结果文件为 `trials/rev_<候选>.json`。"失败位置"指 `HT'` 的行号。

| 候选 | 补丁 | 角色 | 应得 | 应在哪里失败 | 试跑结果 | 当前材料 |
| --- | --- | --- | --- | --- | --- | --- |
| gold | `PRIV/gold.patch` | 正对照 | 1 | — | 1，27/27 | 1 |
| noop | 无 | — | 0 | 第一段 `:55`，与修订前相同 | 0，只错目标键；`:55` → `discretize.py:53` | 0 |
| DG | `cands/orange3_4014_DG_dup_to_empty.patch` | 第 3 步退化候选，本次的触发反例 | 0 | 只在新断言 `:80` | 0，只错目标键；`:80` 报 `AssertionError: 0.0 not less than 0.0` | **1**（正式评分） |
| 重编补丁 | 远端 `/work/r2e/probe_proto/runs/orange3_4014_pyx_build/attempt/candidate/orange3__4014f2483e3bab0621c9ae0f994947c008183253.diff`（5 个文件，含新 `.so`） | 编译路径上的正确解，不能误拒 | 1 | — | 1，27/27 | 1（正式评分） |
| 不重编补丁 | 远端 `/work/r2e/probe_proto/runs/orange3_4014_pyx_only/attempt/candidate/orange3__4014f2483e3bab0621c9ae0f994947c008183253.diff`（只有 `.pyx`） | 修复没有生效 | 0 | 第一段 `:55`，与 noop 同一调用栈 | 0，只错目标键；`:55` → `discretize.py:53`，`low = high = 1.0000000000000004` | 0（正式评分） |
| C1 | `GC/orange3_4014_C1_dedupe_in_create_var.patch` | 合理替代解（修改位置不同、范围更大） | 1 | — | 1，27/27 | 1（09-25 正式评分） |
| C4 | `GC/orange3_4014_C4_unique_only_when_n_ge_len.patch` | 已知错误候选（只修示例分支） | 0 | 第二段 `:64`，与修订前相同 | 0，只错目标键；`:64` → `discretize.py:53` | 0（09-25 正式评分） |
| C3 | `GC/orange3_4014_C3_round_dedupe.patch` | S2 缺口候选，本轮不针对 | 1 | — | 1，27/27 | 1（09-25 正式评分） |

**判读**：
- **正对照 1、noop 0**：成立。gold 本身满足公开要求：`list(np.unique(points))` 只去掉重复的切点，保留其余切点，结果仍是 list（`B2/analysis_before_history.md` 第 112–116 行）。按转写，gold 在第三段得到的区间序号是 `[0, 2, 2, 3, 3, 4]`。
- **误判已纠正**：DG 在当前材料上正式评分为 1，修订后试跑为 0，而且只在新断言失败——前两段仍然通过，第 80 行报 0.0 不小于 0.0，因为切点为空时 `transform` 把所有值都映射到区间 0（`W/Orange/preprocess/discretize.py:40`）。
- **编译路径不被误拒**：重编补丁仍为 1；不重编补丁仍为 0，失败位置与修订前相同，都在第一段。
- **已知错误候选仍为 0**：不重编补丁和 C4 各自停在修订前的同一段，第三段没有改变它们的结论。
- **没有新的误拒**：gold、C1、重编补丁都得 1。C3 仍为 1，所以本轮不改变它的 S2 登记。
- **旧键不受影响**：各候选另外 26 个键修订前后都是 PASSED；`status_diff` 要么为空，要么只有目标键。
- **只做了静态判断、没有实跑的写法**（`python3 static_check_seg3.py` 的输出；它对实跑过的候选给出的结论与试跑全部一致）：
  - 相撞的切点上移 1 ulp、保留 n−1 个点（`nextafter` 写法）：第三段区间序号 `[0, 2, 2, 3, 4, 5]`，得 1；
  - 相撞的切点一个不留：`[0, 2, 2, 2, 2, 3]`，得 1；
  - 不断减小 n 直到切点唯一：降到 n=3 时切点是 `[1, 1+2ε]`，2 与 1+2ε、1+3ε 在同一区间，`:81` 失败，得 0。它丢掉了簇两侧本来不重复的切点（0.5、1.5+2ε），违反的依据与 DG 相同（§2 第 2、3 条），属于应当拒绝的一类；目前没有真实候选这样写。

## 6. 修订后仍受保护的公开要求与剩余事项

**受保护的公开要求**：
- **原例不抛错，且切点唯一**：第一段，`HT'` 第 50–57 行。
- **示例外实例也唯一**（循环分支，n < 不同值个数）：第二段，第 59–66 行，挡住 C4。
- **去重时不丢掉不同值之间的切点**：第三段，第 68–81 行，挡住 DG。
- **正常数据的结果不变，`points` 仍是升序 list**：26 个回归键，例如 `TestEqualFreq.test_equifreq_100_to_4`、`TestDiscretizeTable.test_discretize_exclude_constant`。

**仍未覆盖，维持登记**：
- **S2（C3）**：小量级分辨率。可选的 R-c 做法照旧（`B2/review.md` 第 121–125 行），只在本题用于训练或评测、又在意评分宽松度时再做。
- **T3**：循环分支上的非退化没有单独断言。
  - 例如一种写法在 n ≥ 不同值个数时正确去重，只在循环分支上遇到重复就返回 `[]`，它仍能得 1；
  - 目前没有真实候选这样写，按 v1 §8 抽查；
  - 循环分支上怎样才算"应当分开"，依据弱于 n ≥ 不同值个数的情形（见 §2 "为什么 n 要取 6"），所以本轮不补。
- **题面范围外或未测的项，照旧**：空区间、标签重复（R11）、EqualWidth 同类崩溃（R10）、SQL 分支。
- **X1**：
  - 新测试是新写的：按 `EqualFreq(n=6)`、`[1 + 3 * eps], [2]`、`assertLess(bins` grep 了 v3 的 7 个 orange3 公开工作树，没有命中；
  - 原目标测试和 gold 仍逐字出现在 22e98f8f、50f6a758、c3fb72ba、f5026689 的公开初态里，照旧登记（`probe_card.md` 第 42 行）。
- **链路条件**：本修订不改变它。本机缺省 300 s 下，评分控制面保护基本都会超时（`probe_card.md` 第 24 行）。正式评分沿用 1200 s 的放宽时限，单独记账。

## 7. 边界与交接

- **只做了 R-c**：
  - 不改题面，不删键、不改期望，前两段原样保留，没有放宽已有断言，也没有复制 gold 输出；
  - 依据都是公开材料，不涉及 P5 或其它模板外事项，**不需要用户决定**。
- **没做的事**：
  - 没写 `s2_r2e` 下的正式材料，没改生产代码，也没改 `probe_card.md`；
  - 远端只用了建目录、上传、试跑三类命令。远端 `/work/r2e/trials/lc_orange3_4014/4014f248/` 留有上传件和 10 份试跑结果，本地副本在 `trials/`。
- **协调者待办**：
  1. 把 `revision_draft.json` 里的 `revisions` 落为正式修订单（`hidden_test_text_replace`，target 是 `test_1.py`）。期望不变，不需要 `expected_file_replace`。
  2. 重建材料与派生镜像。本题原配方是 `r2e_derive_v1+sysconfig_v1`，与 v4 七题同类，预计走 `+material_v2+sysconfig_v1`。落地时请核对组合配方摘要在批准集合里，避免 9b5494e2 那种 `env_recipe_not_approved`（`README.md` 09-29 04:25 一行）；这一条是提醒，我没有核实。
  3. 用 1200 s 放宽时限跑正式评分，至少跑 gold、noop、DG、重编补丁、不重编补丁、C1，可再加 C4、C3，按 §5.2 判读。
  4. 送 Codex 复核。
- **之后重判 v1 用途**（`probe_card.md` 用途表）：
  - 第 3 步从"未做"改为"已做、命中、已修订"；
  - 能力比较条件 ②"得 1 的补丁要加后检"，可按正式验收的结果重判；
  - 链路条件（评分时限、必须用 R2E 求解入口）仍然在。
