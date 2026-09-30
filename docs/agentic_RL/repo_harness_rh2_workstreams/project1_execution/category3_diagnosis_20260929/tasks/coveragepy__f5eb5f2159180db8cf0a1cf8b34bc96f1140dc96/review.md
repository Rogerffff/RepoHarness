# coveragepy `f5eb5f21` 独立复核结论

2026-09-30 / 独立复核者（Claude，新会话，不继承作者上下文）。

**复核对象**：
- [result.md](result.md)、[initial_judgment.md](initial_judgment.md)、`evidence/`；
- `rh2/experiments/category3_cloud_20260929/cov_f5eb/` 下的候选、`revision_draft_rc2.json`、`revision_draft_rb2.json`、`revision_draft_statement_B.json` 和隐藏测试草案；
- R2E 线的本题材料：`r2e_lifecycle_20260929/results/coveragepy__f5eb…/` 与 `codex_reviews/review_revision_coveragepy_f5eb.md`。

**顺序**：
1. 先读原件并实跑，封存[初判](review_initial.md)。sha256 `5f3515a0520bc4cf10f57df898c107989a6fdffa6600950f1d03834e661e4ab3`，写完未改。
2. 再读作者与 R2E 线材料。
3. 最后另造候选，在一次性容器里核对。

复核者的脚本、候选和日志都在 `rh2/experiments/category3_cloud_20260929/cov_f5eb/review/`。

## 总判断：部分同意，阻断项 2 项

**同意的部分**：
- **P5 第二分支的归类成立。** 我初判倾向“R-b 模板内放宽”，读了作者与 Codex 的依据后改判，理由见 §3。三个选项里 C1 的得分描述准确，推荐 A 也合理。
- **新 S1 成立。** 作者的 LF 在现行 v8 得 1。我另造的两个自然变体在 v8 也得 1：
  - `wr_loopvar`：在 gold 的修改处改用循环结束后残留的 `analysis`（最后一个文件），属于 §4 第 3 步“作用在无关对象上”；
  - `wr_first`：只记第一个有分支的文件。

  违例落在主路径上：题面示例在本镜像原样运行，得到的就是 3 文件报告。gold 给出 `num_branches` 54、covered 5、missing 49，LF 给出 1、1。K3 的 8/1/5/3 正确，也有公开依据。
- **R-c v2、R-b v2 不过严。**
  - 5 个只改 totals 的合理实现在两版都得 1：gold、A1，以及复核者的 `rv_accum`、`rv_sumlist`、`rv_results`（改 `results.py`）；
  - 2 个对称实现（C1，复核者的 `rv_sym_xml`）在 R-b v2 得 1，在 R-c v2 只错 BC，符合设计。

**不同意“修法已明确”**：R-c v2 与 R-b v2 仍放过两个已知错误候选，三个选项都受影响。
- **B1**：作者自己构造的 NB（零分支时省略两键）两版都得 1，作者只登记为 T3。按 §5 R-c 验收“已知相关的错误候选仍为 0”，以及负责人补充原则第 2 条，不能只登记。
- **B2**：复核者构造的 `wr_alldata_proj` 两版都得 1。它把两个新计数按数据里全部被测的项目文件求和，不看本次报告选中了哪些文件。`coverage json --include=branchy.py` 时它输出 `num_branches` 6、covered 5、missing 3。

两处修法都很小，已私有验证（§5）：
- 新增零分支报告键 K4；
- 在 K3 里加一次子集报告。

修后，5 个合理实现仍为 1；noop 与全部 19 个错误候选都为 0。C1 与 `rv_sym_xml` 在 R-b 版为 1，在 R-c 版只错 BC。

本题结论仍是“需要用户就 P5 作决定”。B1、B2 是对修法的补正，不改变这一结论。

**停止条件**：
- 修订测试采用 B1＋B2 后，本题测试层不再需要聚焦复核。
  - 可以直接用复核者草案：`rh2/experiments/category3_cloud_20260929/cov_f5eb/review/materials/` 下的 `test_1_rc3h.py`、`test_1_rb3h.py` 与 `expected_rc3.json`；
  - 也可以在作者草案上做逐字等价的改动。
- 之后第2类正式评分的逐键结果，与 §4 表的 R-c v3／R-b v3 两列一致即可。
- 此后再想出的反例进 backlog（review-standards §10.5 第 8 条），除非它落在主路径、并能给出具体违例。
- P5 仍等用户裁定。B1、B2 与裁定无关，三个选项都要带上。

## 1．复核范围与证据层级

- **全部是私有模拟，不是 R2E 正式评分链。**
  - 每次评分开一个全新容器：`docker run --rm --network none`，root 身份；
  - 镜像 `c3keep/coveragepy_f5eb:src` = `namanjain12/coveragepy_final@sha256:fb0335af…`，与冻结摘要一致；Image ID `45810d8d…`，CTracer；
  - 流程：把 `/r2e_tests` 复制到 `/testbed/r2e_tests`，换入对应版本的 `test_1.py`，运行评分包的 `run_tests.sh`（`8285765f…`）；
  - 计分：用 RH2 的 `parse_log_pytest`＋`normalize_status_map` 解析，同时算上游口径 `prime_calculate_reward` 与生产口径 `expected_map_matches`（键集并集）。两种口径在所有运行上一致，每次都解析到全部期望键，没有多余键。
- **材料版本（8 版隐藏测试）**：
  - 原版 `ee874f37…`；
  - 现行 v8 `73ad2f27…`；
  - 作者 R-c v2 `2cbeb5f2…`、R-b v2 `b1d83e2b…`，从作者目录原样复制；
  - 复核者 rc3／rb3：只加 K4；
  - 复核者 rc3h `c58b71e3…`／rb3h `fd4d6ac9…`：K4＋K3 子集。下文称 R-c v3／R-b v3，期望映射 `expected_rc3.json`（`e150a338…`，8 键）。
- **候选**：
  - 作者与 R2E 线的 12 个补丁，原样 `git apply`。其中 7 个与 `r2e_lifecycle…/cands/` 逐字节相同，已核 sha256；
  - 复核者 15 个：gold 副本（与官方 gold 逐字节等价）、`rv_sym`（与 C1 逐字节等价）、4 个合理实现、9 个错误候选。
- **规模**：
  - root 评分 208 次（候选 × 材料版本），其中 10 次跑在写初判之前；
  - uid 54322 重跑 8 次：gold、C1、NB、`wr_alldata_proj` × R-c v3／R-b v3，与 root 逐键相同。做法同作者：一次性容器里 `chmod 755 /root`，再用 `setpriv` 换身份；
  - gold、C1、A1 在 v3 两版另各重复 2 次，结果稳定；
  - 行为探针 12 个候选，最多 15 种情形：API 进程内、保存后读回、CLI、`--include`／`--omit`、零分支、行模式、题面示例原样。
- **上游对照**（只作佐证）：从 PyPI 下载 `coverage-5.1.tar.gz`（`f90bfc4a…`）。
- **结果文件**：`review/grades.jsonl`（`83ba0e5b…`），汇总表 `review/summary_table.txt`，原始日志在 `review/logs/`。
- **未做**：正式评分链与派生镜像、UID 54321 开发条件、Codex 复核、选项 B 的新公开读者（§7）。

## 2．作者主张逐条核对

| # | 作者主张 | 判断 | 依据 |
| --- | --- | --- | --- |
| 1 | totals 两键、计数口径（covered＋missing＝num_branches）、按 `has_arcs()` 门控，都有公开依据 | 同意 | `jsonreport.py:38、59、94`；`results.py:35-36、201-204`。C3、`wr_inproc` 在读回与 CLI 路径都缺键（探针 S5、C1） |
| 2 | 多文件时 totals 按文件累加：有依据，但现行材料没测 | 同意 | 所有键都只报告一个模块。补充一条主路径证据：题面示例原样运行时，报告里有被测模块和 venv 的两个导入钩子文件（`_distutils_hack/__init__.py`、`_virtualenv.py`）；gold 为 54/3/5/49，LF 与 `wr_loopvar` 为 covered 1、missing 1（探针 E0） |
| 3 | 行模式不出现分支键；不另加题面没点名的键（XP） | 同意 | 行模式 3 键与公开测试相同，base 下全过。XP 另加的是新指标，不是题面要的两个计数在每文件的对称出现，拒绝它有依据（题面只点名两键；公开读者 §2 已预警） |
| 4 | 题面错误信息就是 noop 上 pytest 的 “Differing items” 一行 | 同意 | 作者证据 `h0_orig.out` 第 77–80 行；我的原版 noop 日志相同，另有 “Omitting 2 identical items” |
| 5 | 每文件 `summary` 恰好 7 键属 P5 第二分支 | **同意**（改了我的初判） | 见 §3 |
| 6 | C1 的 `jsonreport.py` 与上游 5.1 发布版逐字相同 | 同意 | 我独立下载 sdist，`base＋C1` 与 5.1 的 `jsonreport.py` diff 为空；5.1 的 `test_json.py` 每文件也有两键 |
| 7 | **LF 是新 S1** | 同意，另补依据 | LF 与 `wr_loopvar`、`wr_first`、`wr_split` 在原版与 v8 都得 1，在 K3 都得 0。`wr_loopvar` 只改 gold 所在的 totals 块，属 §4 第 3 步的退化方向，所以 v8 上第 3 步也命中（T2b），不只第 4 步 |
| 8 | K3 的期望 8/1/5/3 | 同意 | 推导：BRANCHY 共 6 个去向，走到 4 个；h 的 `if` 未执行，其 2 个去向都缺，但不算部分分支；主文件 2 个去向，走到 1 个，部分分支 1 个。实测：gold 在两文件、顺序对调、读回、CLI 下都给 8/1/5/3；作者的 XML 独立计数给出 `branches-valid=8`、`branches-covered=5` |
| 9 | 历史 R-b 放过 FC，R-b v2 已补 | 同意 | FC 在 R-b v2 下只错 K3。历史 R-b 我未重跑 |
| 10 | R-c v2、R-b v2 草案字段齐全，可由 RH2 重放 | 同意 | 用 `ingest_r2e_subset._apply_edits` 重放，得到 `2cbeb5f2…`、`b1d83e2b…`；字段集合等于 `_REVISION_FIELDS` |
| 11 | 私有矩阵结果 | 同意 | 在 R-c v2／R-b v2 上重跑 gold、A1、C1、C1swap、FC、LF、NB、noop，逐键与作者 `grades.jsonl` 相同。C2、C3、D0、W2、LM、XP 我只在复核版（rc3／rb3 或 v3）上跑，失败键与作者在 v2 上的一致；D0 另多错 K4 |
| 12 | **NB 登记为 T3，不补断言** | **不同意** | 阻断项 B1 |
| 13 | R-c v2、R-b v2 下“9 个已知错误候选都是 0” | 数字属实，结论不完整 | 这 9 个里不含 NB。NB 与 `wr_alldata_proj` 两版都得 1（B1、B2） |
| 14 | 选项表：C1 在 A 为 1，在 B、C 为 0；额外工作；训练信号 | 同意 | C1：原版 0、v8 0、R-c v2 0（只错 BC）、R-b v2 1；修后 R-c v3 0（只错 BC）、R-b v3 1 |
| 15 | “LF 是 A1 的一字之差” | 小误 | A1 用 `branch_stats()` 累加；LF 用 `nums` 的属性并写成赋值。与复核者 `rv_accum`（`+= nums.n_executed_branches`）才是一字之差 |
| 16 | §4 第 3 步“现行 v8 为 0，已处理” | 不完整 | D0 在 v8 为 0，但 `wr_loopvar` 在 v8 为 1（第 7 行）。结论同为 S1，不改去向 |
| 17 | 证据层级如实 | 同意 | 正文写明是私有模拟、uid 近似做法与未做事项。小处：`-n3` 来自 `setup.cfg` 的 addopts，不在 `run_tests.sh` 里 |

## 3．P5 归类意见：成立（第二分支）

**两种读法的依据都来自公开材料**，不是训练记忆，也不是上游代码：

- **读法 K：每文件保持原来 7 键。**
  1. 题面在描述、期望、实际三处都只说 totals。
  2. 题面的错误信息，正是 noop 上 pytest “Differing items” 列出的唯一一项（只有 `totals`）。熟悉 pytest 输出的解题者能据此读出“期望与现状只差在 totals”。这条信号不强：题面删掉了 “Differing items:” 表头，公开读者据此判为不确定。
  3. 公开 `tests/test_json.py:50-58` 写明了分支模式下的每文件形状。
- **读法 S：每文件也带这两个计数。**
  1. 同一个公开测试同时显示：每文件 `summary` 与 `totals` 键集完全相同；已有的两个分支计数，在 `jsonreport.py:59-63` 与 `:94-98` 以同一个 `has_arcs()` 条件成对加入。
  2. 标题泛称 “JSON coverage report missing branch attributes”。

同一份公开测试能同时支撑两种读法，这正是真正的两义。作者把上游 5.1 与 X1（`ea6906b0` 的初态）都标为“不算依据的佐证”，处理正确。

**我初判倾向 R-b，现在改判，理由有两条：**

1. **R-b 的前提是约束“没有公开依据”。** 读法 K 有直接的文字依据（上面第 1、2 条），只是强度一般。“依据弱”不等于“没有依据”，这一点同意 Codex。
2. **我初判援引的 F2 第 4 条“两种实现都符合确定需求时可以都接受”，在这里用不上。**
   - 每文件是否保持不变，本身就是两种读法的分歧：按读法 K，它属于需求；
   - 把它排除在“确定需求”之外，已经是替读法 S 选了边；
   - 所以这条不能用来绕开 P5。

我初判里用 dask-9378 作对照，那也只能说明“这里不是无问题”：本题测试确实惩罚两处都改。至于算 T1 还是 P5，要看约束有没有公开依据，按上面第 1 条是 P5。

**我初判的一处更正**：我原以为 XML 只在根节点给计数，可算读法 K 的弱先例。作者说得对：XML 的行计数同样只在根节点，所以这一点对两种读法中性。

**对三个选项的意见**：
- **A（R-b v2）不是 F2 禁止的“把相反输出 OR 起来”。** totals 仍完全约束；每文件只允许多出这两个同名计数，而且要成对、值正确。这与“合并还是替换”那种核心行为相反的情形不同。所以 A 是用户可以选的正当选项。但 A 超出了 R-b 模板的字面边界，需要用户的 decision_ref，这一点作者写得对。
- **推荐 A 合理**：C1 就是上游发布的写法；A 不改题面，放宽很窄，而且验值。
- **B 的题面句子**逐行看过，没有隐藏测试的细节，公开依据是旧测试里的每文件形状。它能让题目对解题者无歧义，但同样需要用户选择，再经新公开读者验收。
- **C** 保留了一个公开读者已经指出的歧义，却由判分暗中选边。作者对 C 的训练代价写得如实（C1 型解稳定得 0）。
- 三个选项的影响描述中，只有“已知错误候选全 0”一行在 B1、B2 修正前不成立。修正后三个选项的隐藏测试都是 8 键，sha256 要同步更新。

## 4．反例与新问题（私有结果表）

键名：BC = `test_branch_coverage`，K1 = 计数（BRANCHY），K2 = 保存后读回，K3 = 两文件累加，K4 = 零分支（复核者新增），LINE、CTX = 行模式 3 键。“0(K3)”表示得 0、失败键为 K3。`*` 表示该格取自作者的 `grades.jsonl`，复核者未在该版本重跑。

| 候选 | 来源 | 做法 | 原版 | v8 | 作者 R-c v2 | 作者 R-b v2 | 复核 R-c v3 | 复核 R-b v3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gold | 参考修复 | totals 用 `self.total` | 1 | 1 | 1 | 1 | 1 | 1 |
| A1 | R2E 线 | 逐文件累加 `branch_stats()` | 1 | 1 | 1 | 1 | 1 | 1 |
| `rv_accum` | 复核 | 逐文件 `+= nums` 的两个属性 | 1 | 1 | 1 | 1 | 1 | 1 |
| `rv_sumlist` | 复核 | 收集 Analysis，末尾求和 | 1 | 1 | 1 | 1 | 1 | 1 |
| `rv_results` | 复核 | `Numbers` 新增存储字段，`__add__` 正确 | 1 | 1 | 1 | 1 | 1 | 1 |
| C1 | R2E 线 | 对称（＝上游 5.1） | 0(BC) | 0(BC) | 0(BC) | 1 | 0(BC) | 1 |
| `rv_sym_xml` | 复核 | 对称，按 XML 的 `branch_stats` 口径 | 0(BC) | 0(BC) | 0(BC) | 1 | 0(BC) | 1 |
| noop | — | — | 0(BC) | 0 | 0 | 0 | 0 | 0 |
| LF | 作者 | 逐文件赋值代替累加 | 1 | 1 | 0(K3) | 0(K3) | 0(K3) | 0(K3) |
| `wr_loopvar` | 复核 | gold 处改用残留的 `analysis`（最后一个文件） | 1 | 1 | 0(K3) | 0(K3) | 0(K3) | 0(K3) |
| `wr_first` | 复核 | 只记第一个有分支的文件（依赖顺序） | 1 | 1 | 0(K3) | 0(K3) | 0(K3) | 0(K3) |
| `wr_split` | 复核 | missing 取最后一个文件，covered＝num−missing（和仍对，拆分错） | 1 | 1 | 0(K3) | 0(K3) | 0(K3) | 0(K3) |
| **NB** | 作者 | 零分支时省略两键 | 1 | 1 | **1** | **1** | 0(K4) | 0(K4) |
| `wr_alldata` | 复核 | 按数据里全部被测文件求和 | 1 | 1 | 0(K3)※ | 0(K3)※ | 0(K3) | 0(K3) |
| **`wr_alldata_proj`** | 复核 | 同上，滤掉 site-packages | 1 | 1 | **1** | **1** | 0(K3) | 0(K3) |
| `wr_inproc` | 复核 | 只有本对象亲自测量时才输出（只在 API 进程内对） | 1 | 0(K2) | 0(K2) | 0(K2) | 0(K2) | 0(K2) |
| C3 | R2E 线 | 按 `config.branch` 门控 | 1* | 0(K2)* | 0(K2)* | 0(K2)* | 0(K2) | 0(K2) |
| C2 | R2E 线 | 部分分支口径 | 1* | 0* | 0* | 0* | 0(K1,K2,K3) | 0(K1,K2,K3) |
| D0 | R2E 线 | 硬编码 1/1 | 1* | 0* | 0* | 0* | 0(K1–K4) | 0(K1–K4) |
| W2 | R2E 线 | 两值对调 | 1* | 0* | 0* | 0* | 0(K1,K2,K3) | 0(K1,K2,K3) |
| `wr_brlines` | 复核 | 按分支行而不是去向计数 | 0(BC) | 0 | 0 | 0 | 0 | 0 |
| FC | 作者 | 每文件写累计到当前的总数 | 0(BC) | 0(BC) | 0(BC) | 0(K3) | 0(BC) | 0(K3) |
| C1swap | R2E 线 | 每文件两值对调 | 0(BC) | 0(BC) | 0(BC) | 0(K1,K3) | 0(BC) | 0(K1,K3) |
| `wr_sym_c2file` | 复核 | 每文件用部分分支口径，totals 对 | 0(BC) | 0(BC) | 0(BC) | 0(K1,K3) | 0(BC) | 0(K1,K3) |
| `wr_sym_last` | 复核 | 每文件对，totals 取最后一个文件 | 0(BC) | 0(BC) | 0(BC,K3) | 0(K3) | 0(BC,K3) | 0(K3) |
| LM | 作者 | 行模式也输出两键 | 0* | 0* | 0* | 0* | 0(LINE,CTX×2) | 0(LINE,CTX×2) |
| XP | 作者 | totals 另加分支百分比 | 0* | 0* | 0* | 0* | 0(BC) | 0(BC) |

※ `wr_alldata` 在作者 v2 上得 0 是偶然的：K3 里的 `import branchy_sum` 触发了镜像 venv 的导入钩子，钩子文件因此被测量，总数被抬高（`assert 24 == 5`）。`wr_alldata_proj` 只多了“滤掉钩子文件”这一步，就在 v2 得了 1。由此推断，在没有这类钩子的环境里，`wr_alldata` 也会得 1；这一点没有实测。

中间版 rc3／rb3 只加了 K4，在上面跑过 24 个候选（LM、XP、`wr_brlines` 未跑）。除 `wr_alldata_proj` 仍为 1 外，其余与 v3 两列相同。

**行为探针**（与测试无关、按公开需求判对错；数值为 `num_branches`／`num_partial_branches`／covered／missing）：

| 情形 | gold、C1、`rv_sym_xml` | LF、`wr_loopvar` | `wr_first` | C3、`wr_inproc` | NB | `wr_alldata` | `wr_alldata_proj` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 题面示例原样（3 文件） | 54/3/5/49 | 54/3/**1/1** | 54/3/**3/29** | 54/3/5/49 | 54/3/5/49 | 54/3/5/49 | 54/3/**1/1** |
| 两文件，进程内（a.py＋BRANCHY） | 8/1/5/3 | 8/1/**4/2** | 8/1/**1/1** | 8/1/5/3 | 8/1/5/3 | 8/1/**10/68** | 8/1/**6/20** |
| CLI：`coverage run --source=. --branch`，再 `coverage json` | 8/1/5/3 | 8/1/**0/0** | 8/1/**1/1** | 8/1/**缺键** | 8/1/5/3 | 8/1/5/3 | 8/1/5/3 |
| CLI：`coverage json --include=branchy.py` | 6/0/4/2 | — | — | — | — | 6/0/**5/3** | 6/0/**5/3** |
| 零分支（进程内与读回） | 0/0/0/0 | 0/0/0/0 | 0/0/0/0 | 进程内 0/0/0/0，读回**缺键** | 0/0/**缺键** | 0/0/**5/65** | 0/0/**1/17** |

表注：
- “—”表示该情形没有对这些候选跑。
- C1 这一列用的是与它逐字节相同的 `rv_sym` 的探针；C1 的零分支一格，由 K4 评分代替（C1 在 R-b v3 为 1）。
- C3 在 rc 文件写了 `[run] branch = True` 时为 5/3，与原判一致。
- `wr_alldata` 两列在进程内偏大，是因为调用方脚本与 venv 导入钩子文件也被测量了。

**“吞错”方向**：新代码路径上没有会抛异常的调用，`Numbers`／`Analysis` 直接给出计数，所以没有造出自然的吞错候选。“抑制症状”方向由 D0（硬编码）、NB（零分支省略）、`wr_inproc`（非进程内省略）覆盖。

## 5．阻断项

### B1：修订测试放过 NB（零分支时省略两键）

- **反例**：作者的 NB（`NB.patch`，`07d0b1ff…`）在 R-c v2、R-b v2 都得 1。探针显示：分支模式下报告一个没有分支的模块，`meta.branch_coverage` 为 True、`num_branches` 为 0，但 totals 缺 `covered_branches`、`missing_branches`；进程内、读回两条路径都一样。
- **违反的公开要求**：
  - 题面的条件是 “with branch coverage enabled”，要求 totals 包含这两个键，没有“有分支才输出”的例外；
  - base 在 `has_arcs()` 为真时总会输出 `num_branches`、`num_partial_branches`，值为 0 也输出。
  - gold、A1、C1 与复核者全部合理实现都给出 0/0。
- **规则依据**：
  - §5 R-c／R-b 验收要求“已知相关的错误候选仍为 0”；
  - 负责人补充原则第 2 条：不能因“少见”只登记 T3。
- **修法**：新增键 K4 `test_branch_totals_without_branches`，期望映射 7 → 8 键。
  - 分支模式下测量一个只有两行赋值的 `straight.py`，只报告它；
  - 断言 `meta.branch_coverage is True`、`num_branches == 0`，这两条是 base 已有行为，作锚点；再断言 covered、missing 都为 0；
  - R-b 版另加每文件条件核对：出现两键时必须是 (0, 0)。
  - 草案：`review/materials/test_1_rc3h.py:256-274`、`test_1_rb3h.py:279-300`、`expected_rc3.json`。
- **修后预期（已私有验证）**：
  - NB 为 0，只错 K4；
  - noop 在 K4 先通过两个锚点，再以 `KeyError: 'covered_branches'` 失败；
  - gold、A1 与复核者 3 个合理实现为 1；C1 在 R-b 版为 1，在 R-c 版只错 BC；
  - 其余候选结果不变；uid 54322 下相同。

### B2：修订测试放过“按全部被测文件求和、不按本次报告文件”的写法

- **反例**：复核者的 `wr_alldata_proj`（`review/cands/wr_alldata_proj.patch`）在原版、v8、R-c v2、R-b v2 都得 1。
  - 探针：先 `coverage run --source=. --branch main.py`（测到 a.py、branchy.py），再 `coverage json --include=branchy.py`；
  - gold 为 6/0/4/2，它为 6/0/5/3，covered＋missing ≠ num_branches。
- **违反的公开要求**：
  - `json_report(morfs)`、`coverage json --include／--omit`、配置 `[report] omit` 都是文档化的常用报告选择；
  - totals 其余各键都只汇总本次报告的文件（`self.total += nums`）。
  - 这与 K3 是同一核心要求（totals 汇总被报告的文件）的另一实例，按 §4 第 4 步判 S1。
- **修法**：不新增键，在 K3 同一测试函数的 totals 断言之后加 8 行：只报告 `main.branchy_sum`，断言 `(num_branches, covered_branches, missing_branches) == (6, 4, 2)`。
  - 这一处与 K3 针对同一个窄问题；
  - 它也让 `wr_alldata` 的拒绝不再依赖 venv 导入钩子。
  - 草案：`test_1_rc3h.py:247-254`、`test_1_rb3h.py:264-271`。
- **修后预期（已私有验证）**：
  - `wr_alldata_proj` 为 0，只错 K3，失败在新加的子集断言 `assert (6, 5, 3) == (6, 4, 2)`；
  - `wr_alldata` 仍在 K3 前面的两文件断言处失败（`24 == 5`，钩子文件）；没有钩子的环境里，它会落到子集断言；
  - 5 个合理实现与 2 个对称实现结果不变；
  - uid 54322 下相同。

**两项合并后的正式验收清单（交第2类）**：
- 按所选选项，落 R-c v3 或 R-b v3：可以用复核者文件，也可以在作者 `_build_materials.py` 上做逐字等价的改动；
- 正式评分预期：
  - gold、A1 为 1；
  - noop、D0、C2、W2、C3、LF、FC、C1swap、LM、XP、NB、`wr_alldata_proj` 为 0；
  - C1：选 A 为 1，选 B、C 为 0（只错 BC）；
- 失败位置：NB 只错 K4，`wr_alldata_proj` 只错 K3，LF 只错 K3，C3 只错 K2；
- 可选加跑 `wr_loopvar`、`wr_first`、`wr_inproc`、`wr_alldata`。

## 6．非阻断建议

1. **result.md §4**：
   - 第 3 步改写为“v8 上 `wr_loopvar`（gold 修改处改用最后一个文件）得 1，第 3 步也命中”，把 T2b 补进 S1 的依据；
   - “LF 是 A1 的一字之差”改为“A1 式的独立计数，把 `+=` 写成 `=`”。
2. **主路径证据**：LF 的 S1 论证可以直接引用“题面示例原样在本镜像就是 3 文件报告”（探针 E0），比两文件夹具更直接。
3. **选项表与交接清单**：
   - 修后三选项的隐藏测试都是 8 键；
   - “已知错误候选全 0”一行改为按修后版本陈述；
   - §5.3 第 3 条里 NB 从“1（T3，可选跑）”改为“0（只错 K4）”，并加 `wr_alldata_proj`；
   - NB 从 T3 登记中移除。
4. **事后审计**：若在修订落地前把本题纳入能力比较，预登记的事后审计要再加两项：零分支报告是否仍有两键；按 `--include` 子集报告时，两值是否只算被报告的文件。
5. **措辞**：`run_tests.sh（…，带 -n3）` 改为“`-n3` 来自 `setup.cfg` 的 addopts”。

## 7．未查事项

- R2E 正式评分链与派生镜像。B2 修后，K3 的结论已不依赖派生镜像里是否保留 venv 导入钩子。
- 解题身份 UID 54321 的开发条件、devcheck；PyTracer 路径；Python 2。
- 历史窄 R-b（`hidden_test_1_hist_rb.py`）没有重跑，沿用作者结果。C2、C3、D0、W2、LM、XP 在原版到 v2 四版上的分数沿用作者结果（表中带 `*`）。
- 选项 B 题面的新公开读者验收、Codex 复核。
- `combine` 后的数据、`report()` 返回值：T3，沿用 R2E 线登记。
- 三个以上文件、配置文件里的 `[report] omit` 走 API 的路径：只做了 CLI `--include`／`--omit` 探针。
- 上游 5.1 之前的中间提交：云端读不到 GitHub，只核了 PyPI 发布版。
