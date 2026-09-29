# numpy d805e9b6：R-c 修订方案（第 2 轮：三处断言，主正对照改为 K-A5b）

2026-09-29 · 修订执行者（Claude，单题闭环试行；统一标准 v1 §5 模板内，Claude 执行、Codex 复核）。

**状态**：第 2 轮，按 Codex 复核"需小改"（`CR/review_revision_numpy_d805.md`）补做。
- 第 1 轮的两处断言原样保留，新增第 3 处"提高阈值后全量显示"。期望映射仍是 229 键，逐键不变。
- gold 在第 3 处失败：threshold=2000 时它只保留 1500 个元素并全量打印，静默丢掉 500 个。按已授权的 D4，主正对照改为 K-A5b；不为保 gold 放宽断言。
- 第 2 轮修订版试跑 8 个候选，全部与预期一致：K-A5b 得 1；gold、noop、K-DE、K-DC、K-DF、DG-e、DG-g 都得 0。都用试跑工具，不是正式评分。
- **不需要用户决定。** 下一步由协调者落正式修订单、跑正式评分（用完整 eval log 核对失败行），再送 Codex 复核。在此之前维持 `needs_repair`，不宣布 `probe_ready`。
- 有一个同族实例没有断言：提高阈值后数组仍大于阈值（`n > threshold ≥ 1500`）。本轮按要求不扩，见 §6。

路径约定（仓库根相对；`trials/`、`cands/`、`revision_draft.json` 相对本目录）：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/`；`W` = `PUB/worktree`，即解题者看到的 `/testbed` 初态。
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/`；`HT` = `PRIV/hidden_tests/test_1.py`（父版本，4401 行）；`HT'` = 第 2 轮修订后的 `test_1.py`（4434 行）。
- `INV` = `runs/r2e_lifecycle_20260929/inv/numpy_d805/`：协调者的正式评分账本，以及私有行为核对 `pcheck_*.json`。
- `CR` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/codex_reviews/`。

## 0. 与第 1 轮的差异

| 项 | 第 1 轮 | 第 2 轮 |
| --- | --- | --- |
| 隐藏测试断言 | 两处（`HT'` 463–478 行） | 三处：原两处不动，新增第 3 处（480–494 行） |
| 修订后 `test_1.py` | 4418 行，sha256 `ea62cd09…` | 4434 行，sha256 `14d78a1c…`；前 478 行与第 1 轮逐字节相同 |
| 试跑草案 | `draft.json`，`991c0449…` | `draft_r2.json`，`71c8dc2d…` |
| 主正对照 | gold（K-A5b 作补充） | K-A5b（D4）；gold 修订后应得 0 |
| DG-g | 可选 | 必跑的已知错误候选 |
| 自定义打印选项 | 一概归 T3，并称补测会扩大题意 | **更正**：公开 Quickstart 明文介绍用 `set_printoptions` 强制全量显示，不能只因"非默认"就当罕见路径。gold 在 `threshold ≥ 1500` 且 `n > 1500` 时静默丢值，属 v1 §4 第 4 步的 S1，由第 3 处覆盖。缺口边界按 Codex 更正为 `≥ 1500`（原写 `> 1500`） |
| 试跑记录 | — | 第 1 轮 12 份结果移到 `trials/round1/`，第 1 轮的方案与草案也存在那里（`revision_plan_round1.md`、`revision_draft_round1.json`）；第 2 轮 8 份在 `trials/round2/` |

## 1. 模板与要纠正的误判

**模板：R-c**（v1 §5）。三处修改各对应一组 S1，逐项写依据，合并在同一轮完成。三处都加在唯一的目标键 `TestMaskedArray.test_str_repr` 里，所以期望映射不变。

| 项 | 要纠正的 S1 | 触发反例（修订前得 1） | 出处 |
| --- | --- | --- | --- |
| R-c 1：非示例的大一维数组也要摘要 | T2c：唯一的核心断言 `HT:454-461` 就是题面示例原样（`PUB/user_prompt.txt:14-15, 22-24`）。v1 §4 第 4 步：部分修复 K-DF 只提高截角门槛，n=100000 时仍只显示 100 个值，也没有省略号 | K-DF 正式评分 1.0（`INV/ledger_KDF.jsonl:1`）；DG-e（只修 `__repr__`）试跑得 1（`trials/round1/cur_DGe.json`） | `card.md` §3–§4；`review.md` §2、§4 |
| R-c 2：默认阈值以下全量显示，不丢值、不重复 | T2b：退化候选 K-DE 把截取量写死为 750，n=500 时每个值显示两次。第 4 步：K-DC 只处理 n>1000，n=500 时仍静默丢掉 400 个值 | K-DE、K-DC 正式评分都是 1.0（`INV/ledger_KDE.jsonl:1`、`INV/ledger_KDC.jsonl:1`）；DG-g（全局阈值改成 99）试跑得 1（`trials/round1/cur_DGg.json`） | `card.md` §3–§4；`review.md` §2、§4、§5 |
| R-c 3：提高阈值后全量显示 | v1 §4 第 4 步（Codex 复核）：gold 对有文档的常用行为修复不完整。按 Quickstart 用 `set_printoptions` 提高阈值、强制打印整个数组时，n>1500 的一维掩码数组只显示 1500 个值，没有省略号 | gold：当前材料正式评分 1（`runs/r2e_lifecycle_20260929/env_verify/ledger_l0_gold.jsonl:6`），第 1 轮修订版试跑 1（`trials/round1/rev_gold.json`） | `CR/review_revision_numpy_d805.md` §3–§4 |

**私有行为核对**：在同一派生镜像上进行（root 身份、一次性容器，只证明输出事实，不是评分），出处为 `INV/pcheck_{KDE,KDC,KDF}.json`。
- K-DE：n=500 输出 1000 个 token，n=100000 正确；
- K-DC：n=500 输出 100 个 token，n=100000 正确；
- K-DF：n=500 正确，n=100000 只有 100 个值。

**gold 缺口的边界**（静态推导，本轮试跑证实了 threshold=2000、n=2000 这一点）：
- n>1500 时，gold 保留首尾各 750 个，共 1500 个元素；
- 之后只有 `1500 > threshold` 时 numpy 才摘要；
- 所以 `threshold ≥ 1500` 时，这 1500 个元素被全量打印，没有省略号，n−1500 个值被静默丢掉。

**不在本轮**：
- **P4 的 R-f**：维持登记（`CR/review_revision_numpy_d805.md` §3），与本修订的关系见 §6。
- **二维窄轴**：标题限定一维，继续登记不修（同上）。
- **同族的另一个实例 `n > threshold ≥ 1500`**：见 §6。

## 2. 公开依据

期望值都由下列公开语义推出，不是照抄 gold 的输出。gold 或 K-A5b 通过与否是验证结果，不是依据。

### R-c 1：非示例的大一维数组

- **题面的一般表述**：
  - 标题 `PUB/user_prompt.txt:5`：大的一维掩码数组的字符串表示不对；
  - 描述 `:8`："When creating and printing a large 1D masked array"，字符串表示没有按预期截断；
  - Expected `:20`：repr 应在一定数量的元素之后截断，并 "using an ellipsis to indicate omitted values"。
  - 示例 n=2000、`a[1:50]` 被掩（`:14-15`），只是其中一个实例。
- **为什么断言 `str`**：标题说的是字符串表示，描述说的是 printing；repr 的 data 段就是 `str(self)`（`W/numpy/ma/core.py:3827-3828`）；公开旧测试对掩码数组也断言 `str(a) == '[0 -- 2]'`（`W/numpy/ma/tests/test_core.py:447-449`）。
- **期望串从哪里来**：
  - 格式照题面 Expected 的示例（`:22`）：前 3 个值，接 ` ..., `，再接后 3 个值；被掩的值显示为 `--`；值之间不补齐宽度。
  - 这与 numpy 的公开规则一致：
    - 默认 `edgeitems=3`、`threshold=1000`（`W/numpy/core/arrayprint.py:37-38`，文档见 `:62-67`）；
    - 元素总数大于 threshold 才摘要，并插入 `"..., "`（`:252-254`）；
    - 一维时取首尾各 edgeitems 个（`:208-213`）；
    - `--` 来自 `masked_print_option`（`W/numpy/ma/core.py:2370`）。
  - 所以 `np.ma.arange(100000)` 掩掉最后两个值后，`str` 应为 `'[0 1 2 ..., 99997 -- --]'`。
- **为什么选这个实例**：规模（100000）和掩码位置（末尾两个）都与示例不同，被掩的值落在显示出来的尾部。它远大于默认阈值，也大于 K-DF 这类"提高截角门槛"补丁所用的门槛（`size > 10000`）；复核指出 n=10000 恰好拦不住 K-DF（`review.md` §3.3）。

### R-c 2：默认阈值以下全量显示

- **题面**：Expected `:20` 要求被省略的值用省略号标出。K-DC 在 n=500 时省略了 400 个值却没有省略号；K-DE 把每个值显示两次，显示的已经不是数组本身的内容。
- **numpy 文档对 threshold 的定义**：`W/numpy/core/arrayprint.py:62-64` 写的是 "Total number of array elements which trigger summarization rather than full repr (default 1000)"，实现见 `:38`、`:252-257`。500 个元素没到阈值，应当全量显示。
- **截角只是优化，不应改变显示结果**：`W/numpy/ma/core.py:3797-3798` 的注释说明，截角是为了 "avoid a costly conversion to the object dtype"；1.11 发布说明把它记为掩码数组的内存与速度优化（`W/doc/release/1.11.0-notes.rst:252-257`）。
- **与 base 的其它路径一致**：没有掩码时直接打印底层 ndarray（`W/numpy/ma/core.py:3777-3778`），500 个值会全量显示；同一个 repr 里的 mask 行也按 ndarray 的规则打印（`:3828`）。
- **独立佐证**：没看隐藏测试和 gold 的公开读者也写了"100 < n ≤ 1000 时，按 R3、R4 应显示全部 n 个"（`public_read.md:28, 89`）。
- **读法选择（不是 P5）**：
  - 另一种读法是 K-DG："只要截过角，就一律摘要"。它唯一的依据是私有类属性 `_print_width = 100`（`W/numpy/ma/core.py:2712-2713`），以及题面 "a certain number of elements" 这句模糊的话。
  - 主审、独立复核与 Codex 都判定严格读法成立，不构成 P5（`card.md` §6，`review.md` §5，`CR/review_revision_numpy_d805.md` §1）。
  - 规格依据是公开的阈值规则。DG-g 只证明这条断言有区分力，不是严格读法的依据（Codex 的表述）。
- **只比 token，不比折行**：不惩罚折行方式不同的实现。期望 token 由输入推出：`0`、49 个 `--`、`50` 到 `499`。
- **范围**：第 2 处测默认打印选项；提高阈值的情形由第 3 处测。

### R-c 3：提高阈值后全量显示

- **Quickstart**：
  - `W/doc/source/user/quickstart.rst:247-251`：数组太大时，NumPy 自动跳过中间，只打印四角（`print(np.arange(10000))` 的例子）；
  - `:262-267`：要关闭这一行为、"force NumPy to print the entire array"，可以用 `set_printoptions` 修改打印选项。
- **`set_printoptions` 的文档**：threshold 的定义（`W/numpy/core/arrayprint.py:62-64`）；修改阈值的例子（`:120-124`）；恢复默认值的写法（`:146-150`）。
- **摘要规则是 `size > threshold`**：`:38` 的注释写 "total items > triggers array summarization"，实现在 `:252`。所以 threshold=2000 时，2000 个元素应当全量显示。
- **题面**：Expected `PUB/user_prompt.txt:20` 要求被省略的值用省略号标出。gold 在这一设置下省略了 500 个值，却没有省略号。
- **截角只是优化**：依据同 R-c 2。无掩码时（`W/numpy/ma/core.py:3777-3778`），同一个数组在 threshold=2000 下会全量显示。
- **为什么不用 Quickstart 的字面写法**：`threshold='nan'`（`:267`）在 Python 3 下不能用。numpy 自己的 `a.size > _summaryThreshold`（`arrayprint.py:252`）会因为 int 与 str 比较而抛 TypeError（静态推断）。所以测试用整数阈值，依据是文档所说的目的（强制全量显示）加上 `size > threshold` 规则。
- **输入**：按 Codex 的反例（`CR/review_revision_numpy_d805.md` §3），threshold=2000、`np.ma.arange(2000)`、掩掉 `a[1:50]`。
  - 这是能让这个数组全量显示的最小阈值，正好落在 `size == threshold` 的边界上，依赖文档写明的严格 `>`。
  - 按 `>=` 判断是否摘要的实现，会在这里摘要，并在 489 行失败。普通 `np.arange(2000)` 在 threshold=2000 下全量显示，所以判它失败有依据。
  - 若复核希望避开边界，把阈值改成严格大于 n（例如 5000）也能测同一缺口；gold 与 K-A5b 的结果不变（静态推断）。
- **期望 token 由输入推出**：`0`、49 个 `--`、`50` 到 `1999`，共 2000 个；不是 gold 的输出（gold 只给出 1500 个）。
- **打印选项的恢复**：
  - `get_printoptions()` 返回全部 8 项（`arrayprint.py:198-205`），`set_printoptions(**opts)` 逐项设回；
  - formatter 每次调用都会被设成传入值（`:110`、`:171`），所以也能恢复；
  - 隐藏测试文件里没有其它测试调用 `set_printoptions` / `get_printoptions`（grep 核过）；
  - 第 3 处在 `finally` 里恢复，失败时也不影响其它键。

## 3. 具体改动

- **目标文件**：`r2e_tests/test_1.py`，即 `HT`。同目录的 `__init__.py` 是空文件。
- **草案条目**：一条 `hidden_test_text_replace`，只有一处 edit：
  - `old` = `HT:456-461`，即示例的 repr 断言整句（从 `assert_equal(` 到 `)`，含结尾换行），全文只出现一次；
  - `new` = 原句，加上三处新增内容（各以一个空行分隔），位置在 `test_str_repr` 末尾、`test_pickling` 之前。
- **与第 1 轮的关系**：第 1 轮的 `new` 原样保留，第 2 轮只在它末尾追加第 3 处。所以修订后文件的前 478 行与第 1 轮逐字节相同；第 1 轮的结果文件又与主审 `card.md` 附录 A 的 diff（sha256 `1092cedb…`）应用后的文件相同。
- **修订后位置**：
  - 第 1 处：`HT'` 463–468 行，断言在 468 行；
  - 第 2 处：470–478 行，`'...'` 检查在 476 行，token 断言跨 477–478 行；
  - 第 3 处：480–494 行，`'...'` 检查在 489 行，token 断言跨 491–492 行，`finally` 在 493–494 行。

新增内容（`HT'` 463–494 行）：

```python
        # A large 1d array other than the issue example is summarized too:
        # the data shows the leading/trailing items with an ellipsis, and
        # masked values at the end are shown as `--`.
        a = np.ma.arange(100000)
        a[-2:] = np.ma.masked
        assert_equal(str(a), '[0 1 2 ..., 99997 -- --]')

        # Below the default summarization threshold (1000 items) a 1d masked
        # array is printed in full: no ellipsis, and no value is dropped or
        # repeated.
        a = np.ma.arange(500)
        a[1:50] = np.ma.masked
        s = str(a)
        assert_('...' not in s)
        assert_equal(s.replace('[', ' ').replace(']', ' ').split(),
                     ['0'] + ['--'] * 49 + [str(i) for i in range(50, 500)])

        # The printing options can be changed to force NumPy to print the
        # entire array.  As long as the threshold is not exceeded, every item
        # of a 1d masked array is shown: no ellipsis, and no value is dropped.
        opts = np.get_printoptions()
        try:
            np.set_printoptions(threshold=2000)
            a = np.ma.arange(2000)
            a[1:50] = np.ma.masked
            s = str(a)
            assert_('...' not in s)
            expected = ['0'] + ['--'] * 49 + [str(i) for i in range(50, 2000)]
            assert_equal(s.replace('[', ' ').replace(']', ' ').split(),
                         expected)
        finally:
            np.set_printoptions(**opts)
```

**设计说明**：
- **只用已有或公开的名字**：`np`（`HT:18`），`assert_` 与 `assert_equal`（`HT:25-28`，来自 `numpy.ma.testutils`）；`np.get_printoptions` / `np.set_printoptions` 是公开 API。
- **不新增测试函数**：按 AST 数，类内 225 个、模块级 4 个，共 229 个测试函数，修订前后相同，对应期望里的 229 个键。
- **没有顺序与稳定性风险**：第 3 处只在 `try` 块内改打印选项，并在 `finally` 里恢复；没有随机、时间或资源因素。
- **`'...'` 检查被 token 断言蕴含**：476 行被 477–478 行蕴含，489 行被 491–492 行蕴含。输出里只要出现 `...`，token 里就会多出一个不在期望列表中的项。保留这两行，是为了区分"不该摘要时摘要了"和"静默丢值"两类失败；它们不是额外约束。
- **格式**：新增行最长 78 字符，没有只含空白的行。
- **测试辅助的暴露没有增加**：新断言和原有断言一样，依赖候选可以修改的 `numpy/ma/testutils.py`。这是通用 E3，已交 A 线。
- **刻意不测**：
  - `n > threshold ≥ 1500` 的摘要实例（见 §6）；
  - 很大的 edgeitems（T3，见 §6）；
  - 多维数组（题外）；
  - 非示例长度的 `repr`：data 段就是 `str(self)`，只改 `__repr__` 的补丁已被夹住（`review.md` §9 第 4 条）；
  - 子类打印、10^7 规模的性能（T3）。

## 4. 期望映射逐键变化

- **不变**：229 键全部为 `PASSED`，与父版本逐键相同。新断言都在已有的键 `TestMaskedArray.test_str_repr` 里。
- **正式修订单**：只需要 `hidden_test_text_replace`。expected 部分的 `added`、`changed`、`removed` 都为空，`expected_output.json` 原样保留。
- **完整映射**：见 `revision_draft.json` 的 `expected_after`，与父版本 `expected_output.json` 内容和顺序都相同。
- **版本记录**：

  | 文件 | sha256 |
  | --- | --- |
  | 父版本 `test_1.py`（`HT`，4401 行） | `72f865c4…` |
  | 父版本 `expected_output.json`（229 键） | `4ed3f5bc…` |
  | 父版本隐藏测试树 | `088fe58b…`，`material_revisions` 为空 |
  | 第 2 轮修订后 `test_1.py`（`HT'`，4434 行） | `14d78a1c…` |
  | 第 2 轮试跑用 `draft_r2.json` | `71c8dc2d…` |
  | 试跑用 `expected_after.json`（229 键，两轮相同） | `a17d53c5…` |
  | 第 1 轮修订后 `test_1.py`（4418 行） | `ea62cd09…` |
  | 第 1 轮试跑用 `draft.json` | `991c0449…` |

  父版本这三项与当前正式材料 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl:21` 一致，也与协调者正式评分日志头部的 `RH2_SETUP_HIDDEN_TESTS_TREE` 一致（例如 `INV/logs_KDE/` 下 eval log 第 4 行）。本题至今没有材料修订。全长哈希见 `revision_draft.json`。

## 5. 验收计划与试跑结果

**试跑环境**：
- **工具**：`rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`，只作试跑。它与正式评分的差别见文件头：不做基线重建比对，不核隐藏测试树与入口摘要，权限布置也做了简化。
- **镜像**：派生镜像 `sha256:c080fc6b7fd0…`，配方 `r2e_derive_v1+sysconfig_v1`，与 `INV/ledger_*.jsonl:1` 里的 `image_id_actual` 相同。两轮都用它。
- **输入**：
  - 第 2 轮开跑前，从磁盘原件重新上传了 7 个补丁、`expected_after.json` 与 `draft_r2.json`。补丁没有经过 Write 工具；DG-e、DG-g 的 sha256 分别为 `b89992b3…`、`1a7d3c94…`，与复核记录相同。
  - 所有补丁都在仓库外的 base 副本上 `git apply --check -v` 通过（第 1 轮核对，补丁此后未变）。副本中 `numpy/ma/core.py` 的 blob 为 `35c1ec79`，等于 gold 补丁的 index 行；`numpy/core/arrayprint.py` 的 blob 为 `282fbd1c`。
- **应用与解析**：
  - 试跑时都是 `RH2_APPLY_RC=0`。应用的文件是 `numpy/ma/core.py`，DG-g 是 `numpy/core/arrayprint.py`。
  - 第 2 轮都报 `RH2_TRIAL_EDITS_APPLIED=1`，草案路径为 `draft_r2.json`。每次都解析出 229 个键，没有 missing，也没有 extra。
- **耗时与并发**：第 2 轮单次墙钟 27–30 s，测试阶段 2.7–3.2 s，pytest 自报 1.7–2.2 s。同一时间最多 2 个试跑。

### 5.1 当前材料上的对照（第 1 轮已跑，不进 acceptance）

| 候选 | 结果 | 出处 |
| --- | --- | --- |
| noop | 0：只有 `test_str_repr` FAILED | `trials/round1/env_noop_current.json` |
| gold | 1：229/229 | `trials/round1/env_gold_current.json` |
| DG-e | **1**：229/229（触发反例） | `trials/round1/cur_DGe.json`（试跑） |
| DG-g | **1**：229/229（触发反例） | `trials/round1/cur_DGg.json`（试跑） |
| K-DE、K-DC、K-DF、K-A5b | 都是 1.0，229/229 | `INV/ledger_{KDE,KDC,KDF,KA5b}.jsonl:1`（协调者正式评分） |
| noop、gold（正式评分） | 0（228/229）、1（229/229） | `runs/r2e_lifecycle_20260929/env_verify/ledger_l0_{noop,gold}.jsonl:6` |

### 5.2 第 2 轮修订版验收

结果文件为 `trials/round2/rev_<候选>.json`。"应失败的断言"一列写的是 `HT'` 的行号。

| 候选 | 补丁 | 角色 | 应得 | 应失败的断言 | 第 2 轮试跑 | 第 1 轮修订版 | 当前材料 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| K-A5b | `cands/numpy_d805_KA5b.patch` | **主正对照**（D4 替代正对照） | 1 | — | 1，229/229 | 1 | 1（正式） |
| gold | `PRIV/gold.patch` | 原 gold，按 D4 记 0 | 0 | 491–492 token 断言（1500 个 token） | 0，只有 `test_str_repr` FAILED | **1** | **1**（正式） |
| noop | 无 | — | 0 | 456–461 示例 repr（回溯报 458） | 0，同上 | 0 | 0 |
| K-DE | `cands/numpy_d805_KDE.patch` | 第 3 步退化候选 | 0 | 477–478 token 断言（1000 个 token） | 0，同上 | 0 | **1**（正式） |
| K-DC | `cands/numpy_d805_KDC.patch` | 第 4 步错误候选 | 0 | 477–478 token 断言（100 个 token） | 0，同上 | 0 | **1**（正式） |
| K-DF | `cands/numpy_d805_KDF.patch` | 第 4 步错误候选 | 0 | 468 | 0，同上 | 0 | **1**（正式） |
| DG-e | `cands/numpy_d805_DGe.patch` | 已知相关的错误候选（只修 `__repr__`） | 0 | 468 | 0，同上 | 0 | **1**（试跑） |
| DG-g | `cands/numpy_d805_DGg.patch` | 必跑的已知错误候选（全局阈值改成 99） | 0 | 476 | 0，同上；失败信息不同（§5.3） | 0 | **1**（试跑） |

### 5.3 失败断言的定位依据

**限制**：试跑结果只保留 stdout 的最后 8000 个字符。229 个键的 short summary 已经占满，回溯不在里面；summary 行只给出失败信息的第一行。因此失败行按下面的证据链确定；正式评分时，要用完整 eval log 逐行核对。

1. **顺序执行**：`test_str_repr` 里的断言按顺序执行，第一处失败就停止。
2. **前 478 行两轮相同**：
   - gold 与 K-A5b 在第 1 轮修订版上得 1（`trials/round1/rev_{gold,KA5b}.json`），所以它们通过了 478 行以前的全部断言；
   - 其余候选在第 1 轮就失败在 478 行以前，第 2 轮的失败信息与第 1 轮逐字相同，失败行不变。
3. **私有行为核对**（`INV/pcheck_*.json`）给出第 1、2 处所用输入在各候选下的真实输出：
   - K-DE：n=100000 正确；n=500 为 1000 个 token，且没有 `...`。所以 468、476 通过，477–478 失败。
   - K-DC：n=100000 正确；n=500 为 100 个 token，且没有 `...`。同样失败在 477–478。
   - K-DF：n=100000 不正确，只有 100 个值。失败在 468。
   - DG-e 不改 `__str__`，它的 `str` 输出与 base 相同；base 在 n=100000 时不正确（`INV/pcheck_none.json`）。失败在 468。
4. **失败信息的类型**：
   - `assert_equal` 失败时，消息以换行开头（`W/numpy/testing/utils.py:233-235`、`W/numpy/ma/testutils.py:125-130`），summary 显示为 `AssertionError: `；
   - `assert_` 不带消息，失败时抛 `AssertionError('')`（`W/numpy/testing/utils.py:58-63`），summary 显示为 `AssertionError`；
   - **gold**：显示为 `AssertionError: `，所以失败在第 3 处的 `assert_equal`（491–492），而不是 489 的 `assert_`。这与 gold 打印 1500 个值、没有省略号相符。
   - **DG-g**：两轮都显示为 `AssertionError`。`test_str_repr` 里的 `assert_` 调用在 476 与 489；DG-g 执行到 476 时的状态与第 1 轮相同，第 1 轮它失败在 476（当时唯一的 `assert_`），所以第 2 轮也失败在 476。
5. **回溯行号**：跨行的调用，Python 3.7 的回溯预计报最后一个另起一行的参数所在的行。当前材料上，noop 在示例断言（456–461）的失败就报在 458（`runs/r2e_env_repair_20260924/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_0338a8c6.eval.log:47`）。按此，477–478 预计报 478，491–492 预计报 492。

### 5.4 判读

- **正对照 1、noop 0**：成立。
  - K-A5b 经 Codex 核实（`CR/review_revision_numpy_d805.md` §2）：默认配置下 n=500 不裁剪；n=100000 保留 1002 个，再由 numpy 摘要。
  - 在第 3 处的场景下，`data.size`（2000）不大于 threshold（2000），截取宽度取 `data.size`，不裁剪，2000 个值全量打印；试跑证实。
  - K-A5b 不是独立求解；它的已知罕见路径缺口见 §6。
- **gold 为 0，已记录**：按 D4 用 K-A5b 作主正对照，没有为保 gold 放宽任何断言。
- **误判已纠正**：
  - 第 1 轮：K-DE、K-DC、K-DF 在当前材料上正式评分 1.0，修订后得 0；
  - 第 2 轮：gold 在第 1 轮修订版上得 1，第 2 轮得 0，失败在第 3 处；
  - 同属固定截取宽度的 ALT-1（`_print_width` 改为不小于 1002）也会在第 3 处失败（静态推断）。
- **已知相关的错误候选为 0**：DG-e、DG-g 在当前材料上试跑得 1，两轮修订版都得 0。
- **三处各自必要**：
  - 只有第 1 处能拦住 K-DF（K-DF 在 n=500 时正确）；
  - 只有第 2 处能拦住 K-DE、K-DC、DG-g（三者 n=100000 都正确）；
  - 只有第 3 处能拦住 gold（gold 通过第 1、2 处）；
  - DG-e 第 1、2 处都拦得住。
- **没有误拒**：K-A5b 仍得 1。K-A4（去掉截角、整体转成 object，完全按 numpy 自己的规则打印）预计三处都通过（静态推断，未跑）。
- **旧键不受影响**：第 2 轮所有试跑中，其余 228 个键都是 PASSED，`status_diff` 只含 `test_str_repr`；第 3 处在 `finally` 里恢复打印选项。

## 6. 修订后仍受保护的公开要求与剩余事项

**受保护的公开要求**（都在 `TestMaskedArray.test_str_repr` 内）：
- 示例的 repr 逐字等于 Expected，包括模板对齐、结尾换行、mask 行和 fill_value 行（`HT':454-461`）；
- 非示例的大一维数组，`str` 摘要为首尾各 3 个值加 `..., `，尾部被掩的值显示为 `--`（`HT':463-468`）；
- 默认阈值以下的一维掩码数组全量显示：没有省略号，不丢值，也不重复（`HT':470-478`）；
- 用 `set_printoptions` 提高阈值后，未超过阈值的一维掩码数组全量显示（`HT':480-494`）；
- 小数组的 str / repr（`HT':448-452`），以及 0 维、结构化、mvoid、自定义显示字符等打印回归键（`card.md` §2 所列 8 个）不变。

**仍未覆盖，维持登记**：
- **同族未断言的实例 `n > threshold ≥ 1500`**：
  - 例如 threshold=2000、n=3000，应摘要为首尾各 3 个值加省略号。gold 在这里打印 1500 个值，没有省略号。
  - 第 3 处只测了 `n ≤ threshold`。一种混合实现能通过全部三处断言，却在这一实例上静默丢值（静态推导）："n ≤ threshold 时不截角，否则固定截到 1500"。
  - v1 §4 第 4 步只要求用已有候选取证，这个混合实现不是已有候选，所以本轮按要求不扩。
  - 如要补：在第 3 处的 `try` 块里加一个 n=3000 的摘要断言，期望 `'[0 -- -- ..., 2997 2998 2999]'`（K-A5b 静态推导能通过），并再跑一轮验收。
- **很大的 edgeitems（T3，静态推导）**：
  - edgeitems 达到截取宽度的一半时，截出的数组长度不再大于 2×edgeitems，numpy 就不插省略号，于是静默丢值。base、gold、K-A5b 都有这个问题：
    - K-A5b：默认阈值下保留 1002 个元素，edgeitems ≥ 501 时出现；阈值不超过 98 时只保留 100 个，edgeitems ≥ 50 就出现；
    - gold：保留 1500 个，edgeitems ≥ 750 时出现。
  - 要让每侧显示 50 或 500 个以上的值才会触发，属罕见组合，登记不测。
  - 这也说明 K-A5b 是"对本题已测要求正确"的正对照，不是在所有打印选项下都正确的实现。
- **二维窄轴**：标题限定一维，登记不修。
- **T3**：子类打印（解题者可以用公开的 `test_subclassing.py` 自测，隐藏测试不含）；10^7 规模的性能。
- **P4 与第 2 处的关系**：
  - 题面 Actual 块说 "displaying up to 1000 elements before cutting off"（`PUB/user_prompt.txt:28`），把"显示约 1000 个值"说成了缺陷本身。这可能把解题者引向 K-DG 式补丁，而这类补丁会在第 2 处得 0。
  - 复核判断这不构成 P2，R-f 后续优先处理（`review.md` §6，`CR/review_revision_numpy_d805.md` §3）。
  - R-f 落地之前，探针与训练分析里要把"n≤1000 也被摘要"式的失败单独标为"P4 相关"；原始 reward 不变。
- **X1**：
  - 同仓 5 题（`18b7cd9d`、`2f4a9650`、`43e333e2`、`5e8301c2`、`d89bc4bb`）的公开初态含本题 gold 与原示例断言，照旧登记。影响按 `review.md` §7：答案暴露与留出方向。
  - 新断言都是新写的：按 `99997 -- --`、`np.ma.arange(100000)`、`range(50, 500)`、`threshold=2000`、`range(50, 2000)` grep 了 v3 中 7 个 numpy 公开工作树的 `numpy/ma/tests/test_core.py`，都没有命中。
  - **修订后本题比上游更严**：上游后续版本仍保留固定宽度 1500 的设计（`numpy__d89bc4bb…` 公开工作树的 `numpy/ma/core.py:2769-2770, 3844-3852`）。所以上游的修复及其后续版本，在第 2 轮修订版上都会得 0。这在 D4 授权范围内，本题本来也只能作"标明版本的自建题"；但它提高了题目难度，训练价值评估时应知道这一点。
- **E3（通用）**：隐藏测试依赖候选可以修改的 `numpy/ma/testutils.py`，已交 A 线。
- **池级**：模型实际收到的消息与 adapter 链路尚未验证。

## 7. 边界与交接

- **只做 R-c**：
  - 不改题面，不删键，不放宽已有断言，没有复制 gold 输出作期望；
  - 三处都有公开依据。第 2 处的读法选择经主审、独立复核与 Codex 一致判定不属于 P5；第 3 处按 Codex 的更正与已授权的 D4 执行。**不需要用户决定。**
- **没有越界**：
  - 没写 `s2_r2e` 下的正式材料与 pins，没改生产代码；
  - 远端只在 `/work/r2e/trials/lc_numpy_d805/d805e9b6/` 下上传文件并运行试跑工具：第 1 轮 12 次，第 2 轮 8 次，结果名为 `r2_rev_<候选>.json`。
- **协调者待办**：
  1. 把 `revision_draft.json` 的 `revisions` 落为正式修订单（`hidden_test_text_replace`）。expected 不变，不需要 `expected_file_replace`；若机制要求显式条目，则 `added`、`changed`、`removed` 都为空。正对照写 K-A5b，并按 `gold_status.reason` 记录 gold 的失败（D4）。
  2. 重建材料与派生镜像。
  3. 正式评分：K-A5b（1），gold、noop、K-DE、K-DC、K-DF、DG-e、DG-g（都为 0）。DG-g 的 projection 应只含 `numpy/core/arrayprint.py`。
  4. 用完整 eval log 核对失败行：noop 458；K-DE、K-DC 478（报 477 也算对）；K-DF、DG-e 468；DG-g 476；gold 492（报 491 也算对）。
  5. 送 Codex 复核；保存父版本、新版本、理由与触发反例（K-DE、K-DC、K-DF、DG-e、DG-g，以及 gold）。
- **之后改题卡**（按 `review.md` §8、§10 第 5 条与 `CR/review_revision_numpy_d805.md` §3–§4）：
  - 正对照改为 K-A5b（D4），记录 gold 在修订版上为 0；
  - 删去"自定义阈值一概归 T3、补测会扩大题意"的说法，缺口边界写成 `threshold ≥ 1500`；
  - 登记 `n > threshold ≥ 1500` 的未断言实例与大 edgeitems 的 T3；
  - X1 补一句"修订后比上游更严"；
  - 训练候选：R-c 验收并经 Codex 复核后改为 conditional，只剩池级条件；
  - 验收集加入 DG-e，DG-g 改为必跑。
