# orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b4237 · 独立复核（review）

独立复核者（Claude）· 2026-09-25 · 第二步。本文是在读过以下材料之后写的：公开读者的 `public_read.md`，主审的 `analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json`，以及 `history/…/refs.json` 所列的历史记录。我的封存初判 `reviewer_initial.md` 没有改动。

全程只读：没有运行项目代码或容器，没有修改原件。路径都相对仓库根。

## 0. 结论

**同意（核心结论成立）**

- 题面把 gold 当作 "Example Buggy Code" 给出：函数体 9 行逐字节相同，按字面运行得到期望值。所以题面既泄漏了修法，又自相矛盾。
- 评分侧在已读范围内没有问题：
  - 目标键直接测题面原例；
  - 23 个期望键全部是 PASSED；
  - 断言不限定返回类型；
  - 没有发现会被误拒的合理解。
- 处置 `needs_review`，按当前题面不列为探针候选。
- 修订只改公开题面，隐藏测试和 expected 不动；这不会扩大原需求。

**修改（4 处）**

1. **题目关系的记录只写了一个方向，影响也写重了。**
   - "同批 3 道 orange3 题的初态已含本题修复"属实，我独立核过。
   - 但关系是双向的：本题初态也已经含有 `4014f248`、`9b5494e2` 两题的修复（机械比对，见 §2）。
   - 7 道 orange3 题里，另外 6 道的 gold 都没改 `owcreateclass.py`，隐藏测试不导入它，题面也没提 Create Class。所以这只是同一仓库按时间先后的快照包含关系，暴露途径弱。
   - 结论：划分应按仓库或时间统一处理（见清单第 5 项），不宜只把这 4 题单列成一组。
2. **"修订后可进入 actor 验证"的剩余条件列得不全。**
   - 短卡漏了第 16 项：真实编辑之后的冻结与投影，目前是 unknown。
   - 短卡也漏了"正式 rollout 使用派生镜像"。这一项按协调者说明已实施，但还在等 A 线审查。
   - 修改公开面是一类新的修订，此前的修订只动过评分面和环境面。改了题面，还要确认修订后的文本真的送到模型。
3. **修订方案需要补两点细节。**
   - 如果删掉代码块，示例要改成导入仓库函数，否则 Example usage 调用的是不存在的本地函数。
   - 这项决定宜并入 T0-3 留下的"题面问题统一规则"，不要单题拍板。
4. **流程与表述上的小问题。**
   - 第 15 项从封存稿的 not_checked 改成了 pass，但没有写理由。
   - 个别事实引用漏了"按协调者说明"的限定。

**保留为未决分歧**

- 数据划分口径：是"这 4 题同组"，还是"按仓库或时间统一处理"。
- 第 5 项该记 issue 还是"pass，关系已记录"。

**新的高影响问题：没有。** 泄漏本身已被主审和我分别独立发现。

## 1. 主审决定性主张逐项核对

| # | 主张（出处） | 我的核对 | 判定 |
|---|---|---|---|
| C1 | 题面代码块与 gold 函数体逐字节相同（analysis §4c） | 封存初判时已用脚本逐行比对：`user_prompt.txt:14-23` 去掉 def 行后的 9 行，与 gold 后像完全一致，只缺 docstring | 同意 |
| C2 | 按字面运行输出期望值（H1） | `DEVCHECK/orig/captures/mcve_statement_code.out:1-2`。条件：agent 54321、派生镜像 `50fd6e31…`、CC 2.1.205、桩模型 | 同意 |
| C3 | 09-23 的 prepared 题面与 `user_prompt.txt` 逐字节相同（H1、check 3） | `runs/r2e_rf_20260923/remote/prepared_r2e/prompts.jsonl:23`：label 是本题，`prompt` 长 1575，sha256 前缀 `41f0004ba40d968e`，与 `user_prompt.txt` 相同 | 同意。"正式链路消费这份 prepared 题面"是协调者的说法，实际消息没有捕获 |
| C4 | noop 在 `test_1.py:94` 失败，得到 `[2, 0, 1]`：RH2 3 次，独立参考 5 份（H3、H4、§3 更正） | RH2 的 3 份日志去掉时间戳后逐字相同。reconcile.json 本题 noop 行列出 5 份参考日志（M3 `noop_x2/out1,2`，09-09 旧探针 `noop/a1–a3`）。我逐份 grep：都是 `test_1.py:94: AssertionError`、`x: array([2, 0, 1])`、1 failed / 22 passed / 3 skipped | 同意。主审把自己初判里"M3 没有 noop 参考"的错误更正了，更正正确 |
| C5 | gold 3 次 23/23，独立参考 gold 5 份一致 | RH2 3 份日志一致。reconcile 的 gold 行 `observed_maps_equal=true`，`reference_ledger_consistent=true`。我看过 M3 两份的汇总行（23 passed, 3 skipped） | 同意 |
| C6 | 期望里没有非 PASSED 键（H6） | `expected_output.json` 23 键全 PASSED | 同意 |
| C7 | 断言不限定返回类型；numpy 取逆的替代解能通过（§3，check 24） | 与我的初判一致，只是静态推断 | 同意（未实跑） |
| C8 | 部分实现分别在 L85/L88/L91/L94 被拒；只剩 `p^5` 这类不自然写法的理论缺口（§3，check 25） | 我重算了 `inv`、`idx[inv]`、`p[p][inv]`、`range(len(a))` 的首个失败行，都对。测试只用到阶数 ≤3 的置换，所以阶数整除 6 的置换上 `p^5 = p^{-1}`，这个缺口成立但不现实 | 同意 |
| C9 | 隐藏测试依赖仓库里可改的 `Orange/widgets/tests/base.py`（H15） | 与我的初判 P3 相同 | 同意 |
| C10 | 同批 `50f6a758`、`c3fb72ba`、`f5026689` 的初态已含本题修复（check 5，issue task_relation） | 我从 7 道 orange3 题的公开工作树里取出该函数的全文（含 docstring），与"本题 base + gold"后的全文比较：这 3 题的哈希 `7101d741…` 与 gold 后像相同；另外 3 题没有这个函数 | 事实同意；关系范围与影响判断需要修改，见 §2 |
| C11 | 历史探针的复现其实带了 xvfb 前缀，"纯库调用不需要前缀"从未验证（H13） | `rh2/scripts/r2e_env/dev_probe_agent.sh:90` 写的是 `env $PREFIX python '$REPRO'`，`PREFIX` 按脚本注释是入口里解释器之前的前缀。日志没有打印本题实际的 PREFIX 值 | 同意（脚本层面推断） |
| C12 | 内存峰值主体是 chown 产生的页缓存，这是同仓推论（H7，check 13） | P3 README §2.3 实测的是 c3fb72ba、f5026689，本题没测；主审已标"未核实" | 同意（表述透明） |
| C13 | 测试阶段 4.8–5.6 s（§4e） | 6 行 ledger 的 `phases.test` 为 4.84–5.60 s。我初判写的 3.4–4.0 s 是 `test.seconds`，量的是另一段时间，两者都对 | 同意 |
| C14 | DEVCHECK 从容器启动到初始化完成约 68 s（H8） | `attempt.json`：`container_started` 到 `sanitize_and_init` 为 68.2 s | 同意 |
| C15 | DEVCHECK 是按正式任务面跑的（delta 头部；facts_ref） | `attempt.json` 显示：派生镜像（`image_is_overlay_derived_id`）、`.venv` 前缀、检查层是 `experiments/r2e_actor_20260925/r2e_devcheck.py`、`prelaunch.json` 里 `WORKDIR_OWNER=54321`、`DNS_EXTERNAL=DENIED`。"这就是最终的正式代码"只能按协调者说明，仍待 A 线审查 | 同意事实。建议 `screening_record.facts_ref` 里这一条也加上"按协调者说明"的限定（delta 头部已经写了） |

**是否先看答案、再把隐藏要求说成"显然"：没有。**

- 隐藏测试新增的两组断言（`[2,3,1,1]` 和 `[2,3,1,2]`）依赖一般规则 `u[m[i]] == a[i]`。
- 公开读者在接触私有材料之前，就从 docstring、公开用例 `[2,1,2,3]→[0,1,0,2]` 和调用方独立推出了这条规则（`public_read.md` R2），并主动指出单个原例有歧义、可以消除（§3.3）。
- 这条推导没有用到泄漏的代码块。所以修订题面、删掉代码块之后，隐藏要求仍然能从公开材料推出。

**公开读者的疑义能否从公开材料消除：**

- 返回类型、比较方式：公开测试同样用 `np.testing.assert_equal`，可以合理消除。
- Cython 是否构建、pytest 是否安装：actor 已实测。
- 不带前缀能否导入 widget 模块：仍未知，但只影响开发时方不方便。
- 真正的题目问题只有代码块泄漏一项。

## 2. 修改：题目关系（本轮新证据）

| 题 | `setup.py` VERSION / CHANGELOG 最近发布 | 该函数在初始工作树里的状态 | 与本题修复的关系 |
|---|---|---|---|
| `9b5494e2` | 3.26.0 / 3.25.0（2020-04） | 函数不存在（CHANGELOG 没有 #5283） | 反向：它的 gold 后像（1/1 hunk）逐行出现在本题工作树里，前像不在 → **本题初态已含它的修复** |
| `f237f968` | 3.26.0 / 3.25.0（2020-04） | 函数不存在 | 反向不确定：前像、后像都没有逐行出现（该处后来又改过） |
| `4014f248` | 3.28.0 / 3.27.1（2020-10） | 函数不存在 | 反向：它的 gold 后像（1/1 hunk）在本题工作树里 → **本题初态已含它的修复** |
| **本题 `22e98f8f`** | 3.29.0 / 3.28.0（2021-03） | 修复前版本 | — |
| `50f6a758` | 3.32.0 / 3.31.0（2021-12） | = gold 后像 | 正向（主审已记）；它的 gold 前像在本题工作树里，符合时间顺序 |
| `f5026689` | 3.37.0 / 3.36.0（2023-09） | = gold 后像 | 正向（主审已记） |
| `c3fb72ba` | 3.37.0 / 3.36.1（2023-09） | = gold 后像 | 正向（主审已记） |

**关系的性质：**

- 另外 6 题的 gold 各只改 1 个文件，没有一个是 `owcreateclass.py`。
- 它们的隐藏测试都不导入 `owcreateclass`。
- 它们的 `user_prompt.txt` 都没提 Create Class 或这个函数（grep 计数都是 0）。
- 所以这是同一仓库按时间先后的快照包含关系，不是同一修复、同一函数或派生题。解题者只有在翻看无关的 `owcreateclass.py` 时才会看到修复后的函数，暴露途径弱。
- 对本题来说，题面泄漏远比这层关系严重。

**建议修改的写法：**

- **screening_record 的 `task_relation` 与第 5 项：**
  - 同时记两个方向：`50f6a758`、`c3fb72ba`、`f5026689` 的初态含本题修复；本题初态含 `4014f248`、`9b5494e2` 的修复；`f237f968` 不确定。
  - 注明"无共享文件或函数"。
  - 清单第 5 项原文是"维护同族关系，再依拟测的泛化能力划分；同仓库不必自动全排除"。据此，划分建议应改成：如果需要留出评测，按仓库或按时间截止点统一处理 orange3 这 7 题；不要单列这 4 题同组，因为单列既不完整，也会让人误以为其余同仓题互不相关。
- **状态：** 我倾向把第 5 项记为 pass（关系已记录），影响写进 usage 或划分说明。主审记的是 issue。这一点作为分歧保留，不影响处置。

## 3. 修改：修订方案与"可探针"条件

**修订不扩大原需求**，只去掉泄漏、纠正标签，期望行为不变，同意。要让修订真正起效，还需要补上以下几点：

1. **示例保持可运行、前后自洽。**
   - 如果换成仓库真实实现（`owcreateclass.py:155-157`）：Example usage 调用的是这份本地拷贝，打印结果是 ndarray 的 `[2 0 1]`，与 Actual Behavior 自洽，也不用导入 Qt 模块。
   - 如果直接删掉代码块：Example usage 必须改成从 `Orange.widgets.data.owcreateclass` 导入仓库函数，否则示例调用的是未定义的函数。导入 widget 模块要不要 xvfb 前缀仍未知。
   - Expected 保持 list 写法没问题，因为测试不限定类型。
2. **公开面修订是新的修订类型。**
   - 已有的修订单只改过评分面和环境面（`decisions.md` E24："公开面、验证面 48 题逐字节不变"）。
   - 改题面需要重新生成 public bundle，更新 `problem_statement_sha256`、prepared 题面及其 `public_bundle_digest`，并更新 pins。
   - 修订后要捕获一次正式链路的真实消息，确认模型收到的是修订后的文本。
   - 评分材料不变，不需要重跑 noop/gold 来验证评分正确性。
3. **决策归属：并入统一规则。**
   - `decisions.md` T0-3：用户 09-24 晚决定把题面问题"留给后续题意与评分质量筛查"，理由是"可能是同源数据的系统性问题…先定统一规则再批量处理"。本题是这类问题里泄漏最严重的一例。
   - 建议在统一规则下决定，先用 §6 的第 1 项全池扫描估计同类泄漏有多少。
4. **"可探针"的剩余条件，短卡 §4 应补全。**
   - 主审把静态候选和 actor 验证分开了，这是对的；但下面第 3、4 条在 `card.md` 里没有列：
     1. 修订版需经新的公开读者阅读（已列）；
     2. 正式链路的实际消息需要捕获（已列）；
     3. **第 16 项：真实编辑之后的冻结与投影**，仍是 unknown（`screening_record` 里有，短卡没列）；
     4. **正式 rollout 使用派生镜像**：环境卡 §2 写的是"R2E 进正式 actor 前必须改"，按协调者说明已实施，待 A 线审查；
     5. 不带前缀导入 widget 模块：只影响开发时方不方便。

## 4. 流程与表述小问题（不影响处置）

- **第 15 项**：封存稿 §7 记为 not_checked，定稿 JSON 改成了 pass，但 `old_findings_delta.md` §3 没说明原因。
  - 清单原文要求比较"独立运行、连续复用和小规模并发"。现有证据只有多次 fresh 容器的独立运行，以及历史 R14 的缓存计数前后相同；没有专门做复用或并发对照。
  - 建议二选一：写明理由并限定范围（"只覆盖 fresh 独立运行"），或者改回 not_checked 或 unknown。
- **身份稳定性表述**：analysis §4e 说回归键在"三种身份下全部稳定"。其中 actor（54321）和私有对照（root）跑的是公开文件 `Orange/widgets/data/tests/test_owcreateclass.py`，不是 `r2e_tests` 的评分键。两者的 widget 测试体相同，结论可以接受，但措辞应改成"同一批 widget 测试体"。
- **私有对照的身份**：以 root 执行（`private_control.json` 的 env 输出是 uid 0）。主审已注明，这里只是提醒：它证明的是 gold 在该镜像里生效，不证明 agent 身份下的情况。

## 5. 反查范围（主审没写到、我已查过的）

- **顶层 `datasets` 软链**：历史记录说它指向 `Orange/tests/datasets/`。`Table("zoo")` 等按 `dataset_dirs = ['', get_sample_datasets_dir()]` 查找（`Orange/data/table.py:43`）。`FileFormat.locate`（`Orange/data/io_base.py:756-786`）只试 `<dir>/<name>` 和 `<dir>/<name><ext>`，不进 `datasets/` 子目录。`Orange/tests/datasets/` 里也没有 `zoo.tab`、`iris.tab`、`heart_disease.tab`。所以这个软链不影响评分；我初判时"内容未知"的缺项就此消除。
- **widget 层的其它触发场景**：公开读者指出，默认标签编到 `C10` 时字典序 `C10 < C2`，同样会触发 bug。widget 层没有这类用例；修好 helper 即可覆盖，不构成漏测。
- **其它合法路线**：用 pandas 因子化等依赖。actor 与 grader 用的是同一配方的派生镜像，候选在本地能跑通，评分时也能跑通，不存在误判风险（静态推断）。
- **历史的其它主张**（H8–H18）：我只抽查了 H11、H13、H14（软链）和 H8（68 s）。H16（sql 测试）与本题无关，没查。

## 6. 与我初判的差异

- **题目关系**：初判写的是"未查"；现在已核实并扩展（§2）。
- **独立参考**：初判只用了 `run_refs.json` 列出的 M3 gold ×2；现在确认 noop 和 gold 各有 5 份独立参考，并逐份核过 noop 的失败行。
- **测试耗时**：初判的 3.4–4.0 s（`test.seconds`）与主审的 4.8–5.6 s（`phases.test`）并不矛盾，量的是不同时段。
- **未导出的 `datasets/`**：已消除（§5）。
- **其余判断不变。** 我初判的 Q1（全池比对题面代码块与 gold 新增行），与主审 issue 4（`pipeline_check_gap`）是各自独立提出的同一建议。

## 7. 最小后续实验（按优先级）

1. **全池静态扫描（成本低，不需要容器）**：48 题逐题计算"题面代码块"与"gold 新增行"的逐行重合率，找出同类泄漏；结果作为 T0-3 统一规则的输入。
2. **用户决定**：在统一规则下，本题是修订公开题面，还是标注"题面给修法"后只作易题或链路对照。
3. **如果修订**：重新生成公开面、prepared 题面和 pins；由新的公开读者阅读；捕获一次正式链路的真实消息。
4. **可选（CPU，低优先）**：用 numpy 取逆的替代解走一次 RH2 评分，预计 1 分。
5. **共性项（不限本题）**：用代表题验证第 16 项（actor 真实编辑 → 冻结 → 投影 → grader）。

## 8. 第二步实际读取范围

**本批产物（全文）**

- `public_read.md`
- `analysis_before_history.md`
- `old_findings_delta.md`
- `card.md`
- `screening_record.json`

**历史（按 `refs.json`）**

- 全文：本题历史 `findings.md`、`screening_record.json`；`facts.json`（身份、运行、参考、自动检查、flags 各段）；复现脚本。
- 部分：
  - `known_issues.json`：只看了 `source`、`note` 和 `prompt_quality_candidates` 族；
  - `decisions.md`：前约 12 行，外加 grep 命中的行（E12、E14、E17、E20、E22–E24、T0-2、T0-3、T0-5、T0-6、T0-7）；
  - `results_20260924.md`：grep 命中的 orange3 行；
  - P3 `README.md`：grep 命中的行（§0、§1 表、§2.2–2.5、§4、§6–8 的片段）。

**为核对主张另开的原件**

- `runs/r2e_rf_20260923/remote/prepared_r2e/prompts.jsonl:23`（label、metadata，prompt 只做相等比较）
- `runs/r2e_rf_20260923/reconcile_all/reconcile.json`（本题两行的关键字段）
- 5 份独立 noop 参考日志（只 grep 失败行和汇总行）
- `rh2/scripts/r2e_env/dev_probe_agent.sh`（grep `PREFIX`）
- 历史 `agent_probe.log`（grep 复现、导入和前缀行）
- 6 行 ledger 的 `phases`
- DEVCHECK `prelaunch.json` 的 `probe_facts`
- 本题工作树的 `Orange/data/io_base.py:756-786` 和 `Orange/tests/datasets/` 文件名
- 40 项清单第 5、13–16、22、23、29、31、37 项的原文行

**为核对题目关系读到的其它题材料（暴露记录）**

同批 6 道 orange3 题的以下内容：

- 公开工作树 `owcreateclass.py` 的函数全文，只取哈希；
- `setup.py` 的 VERSION 与 CHANGELOG 版本头；
- `public_bundle.json` 的 `base_commit`；
- `user_prompt.txt`，只 grep 计数；
- 私有 `gold.patch`，用脚本只输出改动文件路径，以及各 hunk 前像、后像是否出现在本题工作树中的计数，没有显示补丁内容；
- 私有 `hidden_tests/`，只 grep `owcreateclass` 的计数。

本文只写关系结论，不写其它题的修复内容。本上下文不宜再作这些题的公开读者。

**没读**

- `r2e_static_review_20260925/` 下的 README、`assignments.json`、`actor_devcheck.md`、`grader_candidates.md`
- `refs.json` 以外的环境轮文件
- 其它题的题面全文与隐藏测试内容
