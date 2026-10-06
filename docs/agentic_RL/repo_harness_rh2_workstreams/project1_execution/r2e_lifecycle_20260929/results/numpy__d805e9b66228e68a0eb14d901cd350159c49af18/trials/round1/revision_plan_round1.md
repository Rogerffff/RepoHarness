# numpy d805e9b6：R-c 修订方案（补非示例的大数组实例；补默认阈值以下全量显示）

2026-09-29 · 修订执行者（Claude，单题闭环试行；统一标准 v1 §5 模板内，Claude 执行、Codex 复核）。

**状态：R-c 两处合并为一轮修订。隐藏测试改动原样采用主审 `card.md` 附录 A，复核 `review.md` §3.1 已认可。期望映射不变。修订草案下 8 个候选的试跑全部与预期一致；另在当前材料上跑了 4 次对照。共 12 次，都用试跑工具，不是正式评分。不需要用户决定。** 下一步由协调者落正式修订单与派生镜像材料、跑正式评分，并用完整 eval log 逐行核对失败断言，再送 Codex 复核。P4 的 R-f 本轮不做。

路径约定（仓库根相对；`trials/`、`cands/`、`revision_draft.json` 相对本目录）：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/`；`W` = `PUB/worktree`，即解题者看到的 `/testbed` 初态。
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/`；`HT` = `PRIV/hidden_tests/test_1.py`（父版本，4401 行）；`HT'` = 修订后的 `test_1.py`（4418 行）。
- `INV` = `runs/r2e_lifecycle_20260929/inv/numpy_d805/`：协调者的正式评分账本，以及私有行为核对 `pcheck_*.json`。

## 1. 模板与要纠正的误判

**模板：R-c**（v1 §5）。两处修改各对应一组 S1，逐项写依据，合并在同一轮完成。两处都加在唯一的目标键 `TestMaskedArray.test_str_repr` 里，所以期望映射不变。

| 项 | 要纠正的 S1 | 触发反例（当前材料上得 1） | 出处 |
| --- | --- | --- | --- |
| R-c 1：非示例的大一维数组也要摘要 | T2c：唯一的核心断言 `HT:454-461` 就是题面示例原样（`PUB/user_prompt.txt:14-15, 22-24`）。v1 §4 第 4 步：部分修复 K-DF 只提高截角门槛，n=100000 时仍只显示 100 个值，也没有省略号 | K-DF 正式评分 1.0（`INV/ledger_KDF.jsonl:1`）；DG-e（只修 `__repr__`）试跑得 1（`trials/cur_DGe.json`） | `card.md` §3–§4；`review.md` §2、§4 |
| R-c 2：默认阈值以下全量显示，不丢值、不重复 | T2b：退化候选 K-DE 把截取量写死为 750，n=500 时每个值显示两次。第 4 步：K-DC 只处理 n>1000，n=500 时仍静默丢掉 400 个值 | K-DE、K-DC 正式评分都是 1.0（`INV/ledger_KDE.jsonl:1`、`INV/ledger_KDC.jsonl:1`）；DG-g（全局阈值改成 99）试跑得 1（`trials/cur_DGg.json`） | `card.md` §3–§4；`review.md` §2、§4、§5 |

私有行为核对在同一派生镜像上进行（root 身份、一次性容器，只证明输出事实，不是评分）：
- K-DE：n=500 输出 1000 个 token，n=100000 正确；
- K-DC：n=500 输出 100 个 token，n=100000 正确；
- K-DF：n=500 正确，n=100000 只有 100 个值；

出处为 `INV/pcheck_{KDE,KDC,KDF}.json`。

**不在本轮**：
- **P4 的 R-f**：题面 Actual 块与 base 的实际输出不符。它不阻塞 R-c（`review.md` §6），与本修订的关系见 §6。
- **自定义 printoptions 与多维数组的断言**：题面没有要求（标题限定 1D，也没提 printoptions），gold 也通不过。补这类断言需要 D4 替代正对照，还会扩大题意（`card.md` §4 "不做"，`review.md` §6）。

## 2. 公开依据

期望值都由下列公开语义推出，不是照抄 gold 的输出；gold 通过是验证结果，不是依据。

### R-c 1：非示例的大一维数组

- **题面的一般表述**：
  - 标题 `PUB/user_prompt.txt:5`：大的一维掩码数组的字符串表示不对；
  - 描述 `:8`："When creating and printing a large 1D masked array"，字符串表示没有按预期截断；
  - Expected `:20`：repr 应在一定数量的元素之后截断，并 "using an ellipsis to indicate omitted values"。
  - 示例 n=2000、`a[1:50]` 被掩（`:14-15`），只是其中一个实例。
- **为什么断言 `str`**：
  - 标题说的是字符串表示，描述说的是 printing；
  - repr 的 data 段就是 `str(self)`（`W/numpy/ma/core.py:3827-3828`）；
  - 公开旧测试对掩码数组也断言 `str(a) == '[0 -- 2]'`（`W/numpy/ma/tests/test_core.py:447-449`）。
- **期望串从哪里来**：
  - 格式照题面 Expected 的示例（`:22`）：前 3 个值，接 ` ..., `，再接后 3 个值；被掩的值显示为 `--`；值之间不补齐宽度。
  - 这与 numpy 的公开规则一致：
    - 默认 `edgeitems=3`、`threshold=1000`（`W/numpy/core/arrayprint.py:37-38`，文档见 `:62-67`）；
    - 元素总数大于 threshold 才摘要，并插入 `"..., "`（`:252-254`）；
    - 一维时取首尾各 edgeitems 个（`:208-213`）；
    - `--` 来自 `masked_print_option`（`W/numpy/ma/core.py:2370`）。
  - 所以 `np.ma.arange(100000)` 掩掉最后两个值后，`str` 应为 `'[0 1 2 ..., 99997 -- --]'`。
- **为什么选这个实例**：
  - 规模（100000）和掩码位置（末尾两个）都与示例不同；被掩的值落在显示出来的尾部，顺带检查 `--` 的位置。
  - 它远大于默认阈值，也大于 K-DF 这类"提高截角门槛"补丁所用的门槛（`size > 10000`）。复核指出 n=10000 恰好拦不住 K-DF（`review.md` §3.3）。
  - 开销可以忽略，见 §5 的测试耗时。

### R-c 2：默认阈值以下全量显示

- **题面**：Expected `:20` 要求被省略的值用省略号标出。
  - K-DC 在 n=500 时省略了 400 个值却没有省略号，直接违反这一句；
  - K-DE 把每个值显示两次，显示的已经不是数组本身的内容。
- **numpy 文档对 threshold 的定义**：`W/numpy/core/arrayprint.py:62-64` 写的是 "Total number of array elements which trigger summarization rather than full repr (default 1000)"，实现见 `:38`、`:252-257`。500 个元素没到阈值，应当全量显示。
- **截角只是优化，不应改变显示结果**：
  - `W/numpy/ma/core.py:3797-3798` 的注释说明，截角是为了 "avoid a costly conversion to the object dtype"；
  - 1.11 发布说明把它记为掩码数组的内存与速度优化（`W/doc/release/1.11.0-notes.rst:252-257`）。
- **与 base 的其它路径一致**：
  - 没有掩码时直接打印底层 ndarray（`W/numpy/ma/core.py:3777-3778`），500 个值会全量显示；
  - 同一个 repr 里的 mask 行也按 ndarray 的规则打印（`:3828`）。
- **独立佐证**：没看隐藏测试和 gold 的公开读者也写了"100 < n ≤ 1000 时，按 R3、R4 应显示全部 n 个"（`public_read.md:28, 89`）。它标为"多解"，是因为题面没提这个区间，而不是存在相反的依据。
- **读法选择（不是 P5）**：
  - 另一种读法是 K-DG："只要截过角，就一律摘要"。它唯一的依据是私有类属性 `_print_width = 100`（`W/numpy/ma/core.py:2712-2713`），以及题面 "a certain number of elements" 这句模糊的话。
  - 主审与独立复核都判定：严格读法有公开依据，K-DG 依据弱，不构成 P5（`card.md` §6，`review.md` §5）。
  - 按严格读法，K-DG 式实现会在第 2 处得 0，这是本修订有意的结果。
  - 若 Codex 复核坚持宽松读法（"要么全量显示，要么带省略号"），退路是 `review.md` §5 的宽松版。它仍能拦住 K-DE、K-DC、DG-e，只放过 DG-g 与 K-DG；这时要把 DG-g 当前得 1 记为已知缺口。
- **只比 token，不比折行**：不惩罚折行方式不同的实现。期望 token 由输入推出：`arange(500)` 且 `a[1:50]` 被掩，所以依次是 `0`、49 个 `--`、`50` 到 `499`。
- **适用范围**：只针对默认打印选项。第 2 处借用 threshold 的文档作依据，不代表本题要求遵守自定义阈值（`review.md` §6）。

## 3. 具体改动

- **目标文件**：`r2e_tests/test_1.py`，即 `HT`。同目录的 `__init__.py` 是空文件。
- **草案条目**：一条 `hidden_test_text_replace`，只有一处 edit：
  - `old` = `HT:456-461`，即示例的 repr 断言整句（从 `assert_equal(` 到 `)`，含结尾换行），全文只出现一次；
  - `new` = 原句，加上一个空行和下面 16 行，位置在 `test_str_repr` 末尾、`test_pickling` 之前。
- **与主审 diff 等价**：本条目应用后的文件，与 `card.md` 附录 A 的 diff（sha256 `1092cedb…`）应用后的文件逐字节相同，sha256 都是 `ea62cd09…`。两者都在仓库外的副本上核对过。
- **修订后位置**：
  - R-c 1 在 `HT'` 463–468 行，断言在 468 行；
  - R-c 2 在 470–478 行，`'...'` 检查在 476 行，token 断言跨 477–478 行。

新增内容（`HT'` 463–478 行）：

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
```

**设计说明**：
- **只用文件里已有的名字**：`np`（`HT:18`），`assert_` 与 `assert_equal`（`HT:25-28`，来自 `numpy.ma.testutils`）。
- **不新增测试函数**：按 AST 数，类内 225 个、模块级 4 个，共 229 个测试函数，修订前后相同，对应期望里的 229 个键。
- **没有顺序与稳定性风险**：不改全局打印选项，不依赖测试顺序，也没有随机、时间或资源因素。
- **476 行在逻辑上被 477–478 行蕴含**：输出里只要出现 `...`，token 里就会多出一个不在期望列表中的项。保留 476 行，是为了让"阈值以下被摘要"这类失败先报成一条含义明确的断言；它不是额外约束。
- **测试辅助的暴露没有增加**：新断言和原有断言一样，依赖候选可以修改的 `numpy/ma/testutils.py`。这是通用 E3，已交 A 线，事后审计时标记改动它的补丁。
- **刻意不测**：
  - 自定义 threshold / edgeitems（G1→T3）；
  - 多维数组（题外）；
  - 非示例长度的 `repr`：data 段就是 `str(self)`，只改 `__repr__` 的补丁已经被示例 repr 与两处 `str` 断言夹住（`review.md` §9 第 4 条）；
  - 子类打印、10^7 规模的性能（T3）。

## 4. 期望映射逐键变化

- **不变**：229 键全部为 `PASSED`，与父版本逐键相同。新断言都在已有的键 `TestMaskedArray.test_str_repr` 里。
- **正式修订单**：只需要 `hidden_test_text_replace`。expected 部分的 `added`、`changed`、`removed` 都为空，`expected_output.json` 原样保留。
- **完整映射**：见 `revision_draft.json` 的 `expected_after`，与父版本 `expected_output.json` 内容和顺序都相同。
- **期望从哪里来**：见 §2。这次新增的是断言，不是键，键的期望状态仍是 PASSED。
- **版本记录**：

  | 文件 | sha256 |
  | --- | --- |
  | 父版本 `test_1.py`（`HT`，4401 行） | `72f865c4…` |
  | 父版本 `expected_output.json`（229 键） | `4ed3f5bc…` |
  | 父版本隐藏测试树 | `088fe58b…`，`material_revisions` 为空 |
  | 修订后 `test_1.py`（`HT'`，4418 行） | `ea62cd09…` |
  | 等价 diff（`card.md` 附录 A） | `1092cedb…` |
  | 试跑用 `draft.json` | `991c0449…` |
  | 试跑用 `expected_after.json`（229 键） | `a17d53c5…` |

  父版本这三项与当前正式材料 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl:21` 一致，也与协调者正式评分日志头部的 `RH2_SETUP_HIDDEN_TESTS_TREE` 一致（例如 `INV/logs_KDE/` 下的 eval log 第 4 行）。本题至今没有材料修订。全长哈希见 `revision_draft.json`。

## 5. 验收计划与试跑结果

**试跑环境**：
- **工具**：`rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`，只作试跑。它与正式评分的差别见文件头：不做基线重建比对，不核隐藏测试树与入口摘要，权限布置也做了简化。
- **镜像**：派生镜像 `sha256:c080fc6b7fd0…`，配方 `r2e_derive_v1+sysconfig_v1`，与 `INV/ledger_*.jsonl:1` 里的 `image_id_actual` 相同。
- **补丁校验**：
  - 所有补丁都先在仓库外的 base 副本上 `git apply --check -v` 通过，输出列出了被改文件。副本中 `numpy/ma/core.py` 的 blob 为 `35c1ec79`，等于 gold 补丁的 index 行；`numpy/core/arrayprint.py` 的 blob 为 `282fbd1c`。
  - DG-e、DG-g 的补丁从 `review.md` §4 原样取出，存进 `cands/`；sha256 分别为 `b89992b3…`、`1a7d3c94…`，与复核记录相同。
  - 试跑时都是 `RH2_APPLY_RC=0`。应用的文件是 `numpy/ma/core.py`，DG-g 是 `numpy/core/arrayprint.py`。
- **修订草案的应用**：修订版试跑都报 `RH2_TRIAL_EDITS_APPLIED=1`。每次都解析出 229 个键，没有 missing，也没有 extra。
- **耗时与并发**：单次试跑墙钟 33–49 s，测试阶段 3.0–4.3 s；pytest 自报 2.0–3.0 s，修订前后没有可见差别。同一时间最多 2 个试跑。

### 5.1 当前材料上的对照（不进 acceptance）

| 候选 | 结果 | 出处 |
| --- | --- | --- |
| noop | 0：只有 `test_str_repr` FAILED | `trials/env_noop_current.json` |
| gold | 1：229/229 | `trials/env_gold_current.json` |
| DG-e | **1**：229/229（触发反例） | `trials/cur_DGe.json`（试跑） |
| DG-g | **1**：229/229（触发反例） | `trials/cur_DGg.json`（试跑） |
| K-DE、K-DC、K-DF、K-A5b | 都是 1.0，229/229 | `INV/ledger_{KDE,KDC,KDF,KA5b}.jsonl:1`（协调者正式评分） |
| noop、gold（正式评分） | 0（228/229）、1（229/229） | `runs/r2e_lifecycle_20260929/env_verify/ledger_l0_{noop,gold}.jsonl:6` |

### 5.2 修订草案下的验收

结果文件为 `trials/rev_<候选>.json`。"应失败的断言"一列写的是 `HT'` 的行号。

| 候选 | 补丁 | 角色 | 应得 | 应失败的断言 | 试跑结果 | 当前材料 |
| --- | --- | --- | --- | --- | --- | --- |
| gold | `PRIV/gold.patch` | 正对照 | 1 | — | 1，229/229 | 1 |
| K-A5b | `cands/numpy_d805_KA5b.patch` | 补充正对照：由主审编写、协调者只改了 `max` 一行，不是独立求解 | 1 | — | 1，229/229 | 1（正式） |
| noop | 无 | — | 0 | 456–461 示例 repr（回溯报 458） | 0，只有 `test_str_repr` FAILED | 0 |
| K-DE | `cands/numpy_d805_KDE.patch` | 第 3 步退化候选；R-c 2 的触发反例 | 0 | 477–478 token 断言（1000 个 token） | 0，只有 `test_str_repr` FAILED | **1**（正式） |
| K-DC | `cands/numpy_d805_KDC.patch` | 第 4 步错误候选；R-c 2 的触发反例 | 0 | 477–478 token 断言（100 个 token） | 0，只有 `test_str_repr` FAILED | **1**（正式） |
| K-DF | `cands/numpy_d805_KDF.patch` | 第 4 步错误候选；R-c 1 的触发反例 | 0 | 468 | 0，只有 `test_str_repr` FAILED | **1**（正式） |
| DG-e | `cands/numpy_d805_DGe.patch` | 已知相关的错误候选（只修 `__repr__`），复核要求加跑 | 0 | 468 | 0，只有 `test_str_repr` FAILED | **1**（试跑） |
| DG-g | `cands/numpy_d805_DGg.patch` | 可选，本轮已跑；作用在无关对象上（全局阈值改成 99） | 0 | 476 | 0，只有 `test_str_repr` FAILED；失败信息与其它候选不同（§5.3） | **1**（试跑） |

### 5.3 失败断言的定位依据

**限制**：试跑结果只保留 stdout 的最后 8000 个字符。229 个键的 short summary 已经占满，回溯不在里面；summary 行只给出失败信息的第一行。因此失败行按下面的证据链确定；正式评分时，要用完整 eval log 逐行核对。

1. **顺序执行**：`test_str_repr` 里的断言按顺序执行，第一处失败就停止。
2. **示例及其之前的断言都通过**：候选在当前材料上得 1，说明 `HT':449-461` 都通过。K-DE、K-DC、K-DF、K-A5b 有正式评分为证，DG-e、DG-g 有试跑为证（§5.1）。修订只在 461 行之后插入内容，这些断言的位置不变。
3. **私有行为核对**（`INV/pcheck_*.json`）给出新断言所用输入在各候选下的真实输出：
   - K-DE：n=100000 正确；n=500 为 1000 个 token，且没有 `...`。所以 468、476 通过，477–478 失败。
   - K-DC：n=100000 正确；n=500 为 100 个 token，且没有 `...`。同样失败在 477–478。
   - K-DF：n=100000 不正确，只有 100 个值。失败在 468。
   - DG-e 不改 `__str__`，它的 `str` 输出与 base 相同；base 在 n=100000 时不正确（`INV/pcheck_none.json`）。失败在 468。
4. **失败信息的类型**：
   - `assert_equal` 失败时，消息以换行开头（`W/numpy/testing/utils.py:233-235`、`W/numpy/ma/testutils.py:125-130`），summary 显示为 `AssertionError: `；
   - `assert_` 不带消息，失败时抛 `AssertionError('')`（`W/numpy/testing/utils.py:58-63`），summary 显示为 `AssertionError`；
   - 试跑中只有 DG-g 显示为 `AssertionError`，其余都显示为 `AssertionError: `。`test_str_repr` 里唯一的 `assert_` 调用在 `HT':476`，所以 DG-g 失败在 476，这也说明它通过了 468。
5. **回溯行号**：跨行的调用，Python 3.7 的回溯预计报最后一个另起一行的参数所在的行。当前材料上，noop 在示例断言（456–461）的失败就报在 458（`runs/r2e_env_repair_20260924/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_0338a8c6.eval.log:47`）。按此，477–478 的 token 断言预计报 478。

### 5.4 判读

- **正对照 1、noop 0**：成立。
  - gold 本身满足公开要求：n=500 全量显示，n=100000 摘要正确（`INV/pcheck_gold.json`，`card.md` 附录 B）。
  - K-A5b 在自定义阈值下也不丢值，但这只是静态推断，没有实跑。
- **误判已纠正**：K-DE、K-DC、K-DF 在当前材料上正式评分 1.0，修订后都得 0，只在 `test_str_repr` 失败，并且各自失败在针对它的那一处（§5.3）。
- **已知相关的错误候选为 0**：DG-e、DG-g 在当前材料上试跑得 1，修订后得 0。
- **两处各自必要**：
  - 只有第 1 处能拦住 K-DF，因为 K-DF 在 n=500 时正确；
  - 只有第 2 处能拦住 K-DE、K-DC、DG-g，因为三者在 n=100000 时都正确；
  - DG-e 两处都拦得住：它先在 468 失败；它的 `__str__` 与 base 相同，所以在 n=500 上也会失败。
- **DG-g 说明了什么**：
  - 它通过示例和第 1 处，只在第 2 处被拦。
  - 宽松版（"要么全量显示，要么带省略号"）会接受它在 n=500 上的摘要输出。所以"阈值以下必须全量显示、不得出现 `...`"这一半要求是承重的。
  - 在修订后的文件里，这一要求由 476 行和 477–478 行共同表达，476 行只是先报。
- **没有误拒**：gold、K-A5b 仍得 1。另外两种合理实现没有实跑，只有静态判断，预计都得 1（`review.md` §3.2）：
  - K-A4：去掉截角，整体转成 object；
  - ALT-1：把 `_print_width` 改为不小于 1002。
- **旧键不受影响**：所有修订版试跑中，其余 228 个键都是 PASSED，`status_diff` 只含 `test_str_repr`。新断言不改全局状态，不影响其它键。

## 6. 修订后仍受保护的公开要求与剩余事项

**受保护的公开要求**（都在 `TestMaskedArray.test_str_repr` 内）：
- 示例的 repr 逐字等于 Expected，包括模板对齐、结尾换行、mask 行和 fill_value 行（`HT':454-461`）；
- 非示例的大一维数组，`str` 摘要为首尾各 3 个值加 `..., `，尾部被掩的值显示为 `--`（`HT':463-468`）；
- 默认阈值以下的一维掩码数组全量显示：没有省略号，不丢值，也不重复（`HT':470-478`）；
- 小数组的 str / repr（`HT':448-452`），以及 0 维、结构化、mvoid、自定义显示字符等打印回归键（`card.md` §2 所列 8 个）不变。

**仍未覆盖，维持登记**：
- **G1→T3**：threshold 调到 1500 以上时，gold 仍会静默丢值；多维数组没有改动，属题外。第 2 处借用阈值文档作依据，只针对默认打印选项，不代表要求遵守自定义阈值。
- **T3**：子类打印（解题者可以用公开的 `test_subclassing.py` 自测，隐藏测试不含）；10^7 规模的性能。
- **P4 与第 2 处的关系**：
  - 题面 Actual 块说 "displaying up to 1000 elements before cutting off"（`PUB/user_prompt.txt:28`），把"显示约 1000 个值"说成了缺陷本身。这可能把解题者引向 K-DG 式补丁，而修订后这类补丁会在第 2 处得 0。
  - 复核判断这还不构成 P2，因为题面没有要求 500 个元素也要摘要；但 R-f 的优先级应上调（`review.md` §6）。
  - R-f 落地之前，探针与训练分析里要把"n≤1000 也被摘要"式的失败单独标为"P4 相关"，不当作干净的能力失败证据；原始 reward 不变。
- **X1**：
  - 同仓 5 题（`18b7cd9d`、`2f4a9650`、`43e333e2`、`5e8301c2`、`d89bc4bb`）的公开初态含本题 gold 与原示例断言，照旧登记。影响按 `review.md` §7：答案暴露与留出方向。
  - 两处新断言是新写的。按 `99997 -- --`、`np.ma.arange(100000)`、`range(50, 500)` 三个字面值，grep 了 v3 中 7 个 numpy 公开工作树的 `numpy/ma/tests/test_core.py`，都没有命中。
- **E3（通用）**：隐藏测试依赖候选可以修改的 `numpy/ma/testutils.py`，已交 A 线。
- **池级**：模型实际收到的消息与 adapter 链路尚未验证。

## 7. 边界与交接

- **只做 R-c**：
  - 不改题面，不删键，不放宽已有断言，没有复制 gold 输出作期望；
  - 两处都有公开依据；读法选择经主审与独立复核一致判定不属于 P5，**不需要用户决定**。
- **没有越界**：
  - 没写 `s2_r2e` 下的正式材料与 pins，没改生产代码；
  - 远端只在 `/work/r2e/trials/lc_numpy_d805/d805e9b6/` 下上传文件并运行试跑工具，共 12 次。
- **协调者待办**：
  1. 把 `revision_draft.json` 的 `revisions` 落为正式修订单（`hidden_test_text_replace`）。expected 不变，不需要 `expected_file_replace`；若机制要求显式条目，则 `added`、`changed`、`removed` 都为空。
  2. 重建材料与派生镜像。
  3. 正式评分至少跑 gold、K-A5b、noop、K-DE、K-DC、K-DF、DG-e；DG-g 建议一起跑，它的 projection 应只含 `numpy/core/arrayprint.py`。
  4. 用完整 eval log 核对失败行：noop 为 458；K-DE、K-DC 为 478（跨行调用，报 477 也算对）；K-DF、DG-e 为 468；DG-g 为 476。
  5. 送 Codex 复核；保存父版本、新版本、理由与触发反例（K-DE、K-DC、K-DF、DG-e、DG-g）。
- **之后按 `review.md` §8、§10 第 5 条改题卡**：
  - 训练候选：R-c 验收并经 Codex 复核后改为 conditional，只剩池级条件；
  - X1 改写为"答案暴露与留出方向"；
  - 加一句说明：第 2 处只针对默认打印选项；
  - 验收集加入 DG-e；
  - P4 的 R-f 优先级上调。
