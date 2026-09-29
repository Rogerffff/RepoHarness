# conan-io__conan-14177 独立复核结论

2026-09-29，独立复核会话（Claude，Opus 5.5），不继承作者上下文。

**总判断：部分同意。**

- **同意的部分**：作者的分类与处置方向，即 P2/T1＋T2b＋G1、不属 P5、不需要 R-f、转第2类按 R-b＋R-c 修订、以 `pubcand` 作 §9 D4 替代正对照。所有实测数字我都逐项核对过，并做了独立复现。
- **不同意的部分**：修订草案 v1 还不能按现状交付正式化。有三件事要先做：
  - 删掉一处无公开依据的约束；
  - 验收矩阵补一个能单独验证 T2b 修正断言的候选；
  - 交接写明本题依赖的是 D6 首片**不支持**的两种修订能力。

## 阅读顺序与独立性

1. **先封存初判**：只读原件（题面、gold、test_patch、F2P/P2P、既有 quality_batch01 调查、镜像内 base 源码），写成 `review_initial.md`（9407 字节，sha256 `3f38c442…1850`）。写本文时复算，哈希未变。
2. **再读作者材料**：`result.md`、`evidence/` 全部文件、`rh2/experiments/category3_cloud_20260929/conan14177/` 的候选与草案，以及第2类的 `d6/implementation_brief.md`。
3. **初判与作者结论的关系**：大体一致，差异见文末。

## 逐条主张核对

| 主张 | 判断 | 依据 |
| --- | --- | --- |
| 1. 私有行为矩阵：gold 对 `verbose` 抛 `TypeError`，默认输出新增 `(file)` 行（result.md:15-21） | **同意** | `evidence/semantic_v2/gold/c1_matrix.out`：<br>• `kw_false`、`kw_true` 抛 `TypeError: … unexpected keyword argument 'verbose'`，`pos_true` 抛 `takes 1 positional argument but 2 were given`；<br>• `omitted` 的日志多出 `demo/1.0: Apply patch (file): patches/0001-first.patch`，第二份文件名不出现，两份文件真实改动，输入不变。<br>我用非示例名（`0001-a.patch`、`0002-b.patch`、描述 `desc b`）复现：gold 默认输出 `'demo/1.0: Apply patch (file): patches/0001-a.patch\ndemo/1.0: Apply patch (backport): desc b\n'`，`verbose=True` 抛同一 `TypeError`，且没有应用任何补丁。<br>base 版公开测试上 gold 失败 3 项、`pubcand` 13/13，见 `semantic_v2/*/c2_public_unit.out`。 |
| 2. `pubcand` 在原材料正式评分得 0，失败原因全是默认日志断言（result.md:29、36） | **同意**，措辞需精确化（见 N5） | `evidence/ledger_pubcand.jsonl`：`reward=0.0`、`f2p_pass=0/3`、`p2p_fail=0/10`、`reference_missing_count=0`、`cleanup.removed=true`、`apply_ok=true`、`num_parsed_tests=13`、候选 sha `22906325…` 与文件一致。<br>`eval_logs/evallog_replay-c3-conan14177-pub_020044e3.eval.log` 的三处失败：<br>• `:579-585`：直接 `patch()` 输出缺 `(file)` 标签；<br>• `:605-611`、`:649-655`：省略参数的默认调用里没有 `Apply patch (file): patches/0001…` 行。<br>三处都不涉及 `verbose`。同一日志 `:288-331` 显示候选 diff 只改 `patches.py`，测试补丁 clean apply。我在一次性容器中私有复跑原测试，结果同为 3 failed / 10 passed，失败行相同。 |
| 3. 退化候选 `gold_log_only`（只打印、不应用）在原材料得 1（result.md:30、37） | **同意** | `evidence/ledger_gold_log_only.jsonl`：`reward=1.0`、`3/3`、`p2p_fail=0`、参考缺席 0、清理成功、候选 sha `82c1cbe3…` 一致。<br>日志 `evallog_replay-c3-conan14177-log_07e16a1b.eval.log:311` 显示文件项分支只调用 `output.info("Apply patch ({}): {}")`，不再调用 `patch()`；`:582-595` 显示 13 passed。私有复跑同为 13 passed。<br>它是在 gold 两处修改位置构造的退化候选，违反 `apply_conandata_patches` 的文档化职责"Applies patches"（base `patches.py:71-79`）。§4 第 3 步命中，S1（T2b）成立。 |
| 4a. `test_single_patch_description` 恢复 base 原断言（R-b） | **同意** | 修订版与 base `test_patches.py:118-124` 逐字相同，去掉了无公开依据的 `(file)`。base 上已通过，应改记 P2P（作者交接第 2 条已写）。 |
| 4b. 省略参数与 `verbose=False` 保持原输出（`==` 全等） | **同意** | 依据：题面签名 `verbose=False` 与 "when `verbose=True`"；base 公开测试 `:161-177`、`:208-214` 本来就是 `==`。`always_log` 在此处被拒（`rev_a593cbf7.eval.log:569-570`），合理。 |
| 4c. `verbose=True` 时两份文件名带 `mocked/ref: ` 前缀、按序可辨认，不锁 `Applying:` 措辞 | **同意** | 依据是题面示例（带引用前缀、conandata 相对路径、逐补丁一行）。我的探针：<br>• 成功后打印 `Applied: …`（`post`）→ 13 passed；<br>• 打印绝对路径（`abspath`）→ 13 passed；<br>• 只打 basename（`basename`）或用 `print()`（`print_plain`）→ 失败。<br>后两者偏离示例形态，拒绝有依据。 |
| 4d. `verbose=True` 的位置参数写法 | **有依据，但非核心**（N2） | 依据是题面 diff 原文 `def apply_conandata_patches(conanfile, verbose=False):`。探针 `kwonly`（`*, verbose=False`，其余同 `pubcand`）在 `test_multiple_no_version` 失败，报 `takes 1 positional argument but 2 were given`，整题 0。 |
| 4e. `verbose=True` 时仍须含**整行** `_BACKPORT_LINE`（`revised_tests.py:102、146`） | **依据偏弱**（N1） | 题面没有规定 verbose 下描述行的组合方式。既有 quality_batch01 `public_read.md:17` 也写"新文件名日志与其组合方式可以不同"。探针 `merged`（有描述的补丁把文件名并入描述行，其余同 `pubcand`）因这条被拒。 |
| 4f. 记录型 mock 核对每次调用真实应用两份补丁（`revised_tests.py:104、147`） | **同意断言本身；作者证据未证明它起作用**（B2） | 作者矩阵里的只打印类候选都先被别的断言拦下：<br>• `print_only` 失败在 `_BACKPORT_LINE in log`（`rev_0961a5ac.eval.log:580-581、627-628`）；<br>• `gold_log_only` 失败在 `(file)` 标签、默认输出与 `TypeError`（`rev_10a1bf65.eval.log:571-621`）。<br>删掉这条 `_applied` 断言，这两个候选照样是 0。我补的探针 `logonly_v`（接受 `verbose`、各模式日志都对、自己复现描述行、但从不调用 `patch()`）只在 `assert _applied(calls) == _EXPECTED_APPLIED * 4` / `* 2` 处失败，说明断言有效。这是私有运行，不是正式评分。 |
| 4g. 版本缺失与版本不匹配时，`verbose=True` 调用后累计输出须为空（`revised_tests.py:128-133`） | **不同意：无公开依据**（B1） | base 公开测试 `:206-209` 的 `len == 0` 针对的是**省略参数**的调用，v1 改成 `verbose=True` 后新增了"verbose 下无匹配时不得有任何输出"。题面只说 verbose 时记录应用了哪些补丁，没有禁止其它行；v1 在匹配版本时也允许额外行（只查存在与顺序），两处标准不一致。探针 `header`（`pubcand` 加一行 `apply_conandata_patches(): N patch(es) selected`）其余全过，只在 `assert len(str(output.getvalue())) == 0` 处失败（`assert 60 == 0`），整题 0。 |
| 4h. 匹配版本不输出 `0003-only-for-1.12`，输入不被修改 | **同意** | 依据是 base 版本选择语义（`patches.py:88-94`）与 base 公开测试 `:216-217`。 |
| 4i. `output_verbose` 判不满足 | **同意**，理由要写全（N6） | `ConanOutput` 默认等级 `LEVEL_STATUS`（`output.py:52`），`verbose()` 只在 ≤30 时输出（`output.py:170`）。题面示例的上下文行都是 NOTICE 级：`Calling source()` 为 `highlight`（`conans/client/source.py:78`），标题与子标题为 `title` / `subtitle`（`installer.py:235、311`），与默认等级一致，但示例没给出命令行，是否带 `-v` 只能推断。更强的理由是：`verbose=True` 是逐调用的显式开关，若再受全局等级门控，默认构建里看不到，与"recorded in the build log"的目的冲突。正式日志 `rev_a8e410ce.eval.log:589-590` 确认失败原因就是看不到文件名行。 |
| 5. 修订版诊断评分：正对照 1，其余为 0（result.md:59-70） | **同意数字**；证据范围见 4f | 8 份 `formal_revised_v1/ledger_*.jsonl`：<br>• `pubcand` 为 1（3/3）；<br>• noop、always_log、never_log、print_only、output_verbose 为 0（F2P 1/3，那 1 项是 base 上本就通过的 `test_single_patch_description`）；<br>• gold、gold_log_only 为 0（0/3）。<br>全部 `p2p_fail=0`、参考缺席 0、`segment_completed=true`、日志完整、清理成功，`grader_version` 带 `+c3-conan14177-public-verbose-v1`。8 份 `audit_*/materials.json` 字节相同，绑定原补丁 sha `23d0fb5b…`（与 ingest 一致）和修订补丁 sha `51c9bd79…`（与 `revised_test_v1.patch` 一致）。诊断包装 `rh2/experiments/env_recipe_repair_20260919/replay_with_install_recipe.py:48-57` 先核原补丁 sha，只替换 `test_patch`，并断言候选测试命令不变，F2P/P2P 名单不动。<br>小出入：result.md:70 说私有矩阵"逐项一致"，但私有矩阵只有 7 项，不含 `gold_log_only`（`revised_matrix_spec.json`）。 |
| 6. 转第2类及交接事项（result.md:3、72-78） | **同意转第2类；交接不完整**（B3） | 结论成立：题面清楚，无 P5，测试可按公开依据修订，替代正对照已核（见下行）。但 D6 方案写明首片"不接受测试替换操作"、"不删原参考、不改原分组"（`category2_repair_20260929/d6/implementation_brief.md:47-48、56`），测试补丁替换排在 MONAI5932 之后（`:117`）。本题恰好需要两者：整段替换 test_patch，以及把 `test_single_patch_description` 从 F2P 改记 P2P。result.md 只写"依赖 D6"，没写明依赖的是首片之外的能力。 |
| 7. `pubcand` 可作替代正对照（交接第 3 条） | **核实通过** | 代码层面：`pubcand.patch` 只加 `verbose=False`（位置或关键字均可），True 时用 `conanfile.output.info` 按 conandata 相对路径逐文件记录，其它路径不变，未改 `patch()`。<br>行为层面：<br>• 作者真实文件矩阵中四种调用都真实改文件、输入不变；<br>• 我的非示例名探针同样默认不变、True 时两名俱全、两份均应用；<br>• base 版公开单元测试 13/13，功能窄选 7/7（这项只读了证据，未复跑）；<br>• 修订版正式评分为 1。<br>局限：`patch_string` 条目在 verbose 下不记录（题面未规定，中立）；在应用前打印（"Applying" 表示尝试）。都不影响作正对照。 |
| 8. 运行身份与代码 | **同意** | 本机镜像 RepoDigest 为 `…@sha256:e83f64f4…41db8`，与 public bundle 冻结值一致。评分路径（`rh2/src/repoharness2/grading/`、`adapters/slime/replay_grade.py`、`prepared_task_face.py`、`rh2/scripts/replay_grade.py`）与 `a31cdcd` 做 `git diff --quiet` 无差异，工作区也无改动。`evidence_manifest.json` 163 项：104 项已归档，逐一复算 sha256 全部一致；59 项标明未归档。 |

## 我运行的检查（全部是 `--rm --network none` 一次性容器，挂载只读输入，未跑正式评分）

- **原测试复现**：
  - noop：3F/10P，失败行同上；
  - gold：13P；
  - `pubcand`：3F/10P，失败全在默认输出断言；
  - `gold_log_only`：13P。
- **行为探针**：
  - base、gold、`pubcand` 各测"省略参数"与 `verbose=True`；
  - 用记录型 `patch_ng` mock 记下实际应用的文件；
  - 结果见主张 1、7。
- **修订测试 v1**（`revised_test_v1.patch`，sha `51c9bd79…`）：
  - 复现作者候选：noop 2F（`TypeError`）；`pubcand` 13P；gold 与 `gold_log_only` 均 3F（标签、默认输出、`TypeError`）；`print_only` 2F（`_BACKPORT_LINE in log`）。
  - 我的探针（在 base `apply_conandata_patches` 上做字符串替换生成）：

    | 探针 | 做法 | 结果 |
    | --- | --- | --- |
    | `logonly_v` | 日志全对、不应用 | 2F，只在 `_applied` 处 |
    | `kwonly` | 仅关键字参数 | 1F，位置调用处 |
    | `header` | verbose 下多一行选中数 | 1F，`len == 0` 处 |
    | `merged` | 文件名并入描述行 | 2F，`_BACKPORT_LINE in log` 处 |
    | `post` | 应用成功后打印 | 13P |
    | `abspath` | 打印绝对路径 | 13P |
    | `basename` | 只打文件名 | 2F |
    | `print_plain` | 用 `print()`，无前缀 | 2F |

  - 每次运行不超过 11 秒墙钟。

## 发现的新问题或反例

1. **反例 `header`**：修订版 v1 把合理的 verbose 实现判 0，属于修订材料中的 T1，是阻断项 B1 的依据。verbose 下对"本版本无补丁"给出一行说明是自然的写法，base 里就有 `apply_conandata_patches(): No patches defined in conandata` 这类提示。
2. **反例 `merged`**：把文件名并入已有描述行的实现被判 0，依据偏弱（N1）。
3. **`kwonly` 被判 0**：有题面签名原文作依据，但不是核心要求（N2）。
4. **证据缺口**：T2b 的修正断言 `_applied(...)` 在作者全部正式与私有运行中从未单独决定结果（B2）。我的 `logonly_v` 私有运行证明它有效，但这还不是正式验收证据。
5. **更正我自己的初判**：
   - 初判 (d) 第 4 条"未匹配版本不打印、不应用"与作者 v1 犯了同样的过度约束，经 `header` 探针后收窄为"不打印任何补丁文件名、不应用"；
   - 初判引用 `info = status` 为 `output.py:170`，实际在 `:181`（`:170` 是 `def verbose`）。

   初判文件按约定不改，在此更正。

## 必须修改（阻断）

- **B1**：删除 v1 中"`verbose=True` 且版本缺失或不匹配时累计输出为空"的约束（`revised_tests.py:127-133`）。建议改为：
  - 版本不匹配时保留 base 的省略参数调用及其 `len == 0`；
  - 另加一次 `verbose=True` 调用，断言输出中不出现 `_FIRST`、`_SECOND`、`0003-only-for-1.12`，且 `_applied(calls)` 没有新增；
  - 版本缺失的调用只断言 `AssertionError` 文案，不再计入空输出检查。

  改后重跑验收：`pubcand` 1、noop 0、gold 0，现有错误候选全为 0，`header` 类变体应为 1。
- **B2**：验收矩阵补一个"接受 `verbose`、各模式日志都对、复现描述行、但不应用补丁"的候选（与本复核 `logonly_v` 同形），正式评分应为 0，且失败点落在 `_applied(...)`。只有这样才能证明 T2b（只打印不应用得 1）是被针对它的断言纠正的，而不是顺带被 `TypeError` 或输出断言拦下。
- **B3**：交接补写本题依赖的 D6 能力：整段替换 test_patch，以及调整参考分组（`test_single_patch_description` 从 F2P 改记 P2P）。这两项 D6 首片明确不支持（`implementation_brief.md:47-48、56、117`），需要后续切片落地。落地前本题原版仍只作问题定位，不进入能力比较分母与训练，因为照题面做判 0，不能用事后审计豁免。若后续切片也不支持改分组，要写明替代办法（例如保留在 F2P 并登记"base 上已通过"的例外），不能静默处理。

## 建议修改（非阻断）

- **N1**：`verbose=True` 下的 `_BACKPORT_LINE in log` 建议放宽为"描述内容仍可见"，例如去掉前缀与结尾换行，只查 `'Apply patch (backport): Needed to build with modern clang compilers.'`；或者在依据表中写明"verbose 只新增、不改写既有描述行"的依据。放宽后 `print_only` 仍会被内容检查与 `_applied` 拦下。
- **N2**：位置参数调用保留的话，在依据表中注明依据是"题面签名原文"、属非核心；也可以去掉，免得 keyword-only 写法仅因此判 0。两种选择都应在修订说明里写明。
- **N3**：补一张需求—断言依据表，每条断言写公开依据及它拦下的错误候选（R-c 要求逐处有依据）。当前 result.md §4 只列了行为，位置参数、整行描述、空输出、前缀、相对路径、顺序各自的依据都没写。
- **N4**：result.md §3 补列 T2a：原测试没有任何 `verbose` 调用，§4 第 1 步即为 S1。
- **N5**：两处措辞精确化：
  - result.md:29 写三个 F2P"原因都是缺少默认新增的 `Apply patch (file)` 行"，但 `test_single_patch_description` 是直接 `patch()` 的 `(file)` 标签不符；
  - result.md:70 的"逐项一致"只覆盖私有矩阵的 7 项。
- **N6**：`output_verbose` 的判定建议写全两条理由（见主张 4i），并注明"示例未带 `-v`"属于推断，便于 Codex 复核。
- **N7**：修订补丁把 `test_single_patch_description` 移到后面，并在原位留下 4 个空行（flake8 E303）。可以原位保留以缩小 diff，纯外观问题。

## 未查

- 未跑任何正式评分（`replay_grade.py`）。
- 未复跑作者的真实文件行为矩阵（`semantic_v2`），也未复跑功能测试窄选，只读了证据文件；我的探针用的是 mock。
- 未查真实 actor 条件（UID 54321、激活环境、写权限），作者同样未查。
- 未查 Conan15422 跨题关系，未看上游 issue/PR 讨论（断网）。
- 未看同批 moto-7584。

## v2 聚焦复核（2026-09-29）

**范围**：只核 B1/B2/B3、N1–N7 是否落实，作者重建的探针是否与我的等价，以及 v2 有没有新引入过严或过宽的断言，不重审其它部分。

**材料**：
- `revised_test_v2.patch`：sha256 `ee614041…2d8c`，与生成源 `revised_tests_v2.py`、`make_revised_test_patch_v2.py` 对应；
- 7 个 `probe_*.patch`；
- `evidence/formal_revised_v2/` 下的 15 份账本、日志和 audit；
- 更新后的 `result.md`。

**我做的检查**：
- 在只读一次性容器里私有跑 v2 测试，共 23 个变体，墙钟 17 秒：
  - 作者的 8 个既有候选；
  - 我自己版本的 8 个探针；
  - 作者重建的 7 个探针。
- 未跑正式评分。

**结论：B1、B2、B3 均已落实，没有剩余阻断项。** N1–N7 都已落实，只剩三处文字小问题（下表"剩余"一栏），不影响交第2类。

| 项 | 结论 | 依据 |
| --- | --- | --- |
| B1 | **已落实** | `revised_tests_v2.py:119-130` 省略参数部分恢复为 base 原形：版本缺失断言、不匹配版本 `len == 0`、匹配版本 `==`。`:132-136` 在 `verbose=True` 下只断言版本缺失的 `AssertionError` 文案，不捕获输出。`:137-144` 在不匹配版本下只断言不出现 `_FIRST`、`_SECOND`、`_OTHER_VERSION`，且 `_applied` 没有新增。正式账本 `ledger_probe_header.jsonl` 为 `reward=1.0`、3/3，日志 `rev_b740715f` 13 passed；私有复跑中我的 `header` 与作者的 `probe_header` 都是 13 passed。 |
| B2 | **已落实** | `probe_logonly_v` 正式为 0（1/3）。日志 `rev_f0814f99.eval.log:582-583` 失败在 `assert _applied(calls) == _EXPECTED_APPLIED * 4`，`:645-646` 失败在 `… * 2`，没有别的失败点：输出全等、文件名辨认、描述内容、不匹配版本检查都通过。私有复跑中我的 `logonly_v` 与作者版失败位置相同。 |
| B3 | **已落实** | `result.md:130-137` 写明两项依赖：整段替换 test_patch、F2P→P2P 分组调整。它也写明了落地前只作问题定位，以及不支持改分组时要登记例外。<br>**文字精确化（非阻断）**：brief `:117` 原文是"后续先接 MONAI5932：在同一注册器增加受信测试补丁替换类型"，即替换类型**随 MONAI5932 切片（首片之后的下一片）引入**，不是排在它之后；分组调整在 brief 中没有排期。result.md:132 的"排在 MONAI5932 之后的下一切片"沿用了我前文（本文件主张表第 6 行）的不准确说法，两处都以此为准更正。 |
| N1 | **已落实** | `_BACKPORT_TEXT`（`revised_tests_v2.py:36`）只查描述内容，不带前缀和换行，见 `:78`。`probe_merged` 正式为 1（`rev_11832eb9` 13 passed）。`print_only` 仍为 0，失败在 `assert _BACKPORT_TEXT in log`（`rev_2362e1da.eval.log:594-595、670-671`），同时它也会被 `_applied` 拦下。 |
| N2 | **已落实**；剩余一处交叉引用 | 依据表 `result.md:88` 与边界说明 `:121` 写明依据是签名原文、非核心、可删。表中"（非核心，见 §5）"应改指 §4"两处边界判断"，§5 没有这部分内容。 |
| N3 | **已落实**；剩余一处 | 依据表 `result.md:80-90` 各行依据与拦下的候选，同正式日志逐行核对一致。第 7 行"拦下的错误候选：版本范围错误类候选"没有实际构造的候选，宜注明"未构造具体候选"。 |
| N4 | **已落实** | `result.md:61` 补列 T2a（S1，§4 第 1 步）。 |
| N5 | **已落实** | `result.md:52-57` 分列三个失败原因，其中 `test_single_patch_description` 写成 `patch()` 的 `(file)` 标签。"私有矩阵逐项一致"一句已删。 |
| N6 | **已落实** | `result.md:118-120` 写全两条理由，并注明"是否带 `-v` 属于推断"。 |
| N7 | **已落实** | v2 补丁不触及 `test_single_patch_description`，与 base 字节相同，位置不变。辅助代码插在 `test_multiple_no_version` 之前，两个 multiple 测试原位替换。打补丁后的文件中，既有测试的定义顺序不变，没有连续 3 个及以上空行。镜像里没有 flake8 或 pycodestyle，这一项是用脚本检查的。 |

**探针等价性**：作者的 7 个 `probe_*.patch` 与我的版本语义等价，每份 patch sha 与正式账本记录一致。唯一文字差异是 `merged` 用 `[name]`，我用的是 `(name)`；两者在 v1 与 v2 下判定相同。私有复跑中，两套探针在 v2 下逐一同结果：
- post、abspath、merged、header 为 13P；
- kwonly 为 1F（位置调用）；
- basename 为 2F；
- logonly_v 为 2F（只在 `_applied`）。

我另有的 `print_plain` 为 2F，失败在带前缀的文件名辨认处。

**正式 v2 矩阵**（15 份账本，逐项核对）：

| 结果 | 候选 |
| --- | --- |
| 为 1 | `pubcand`、`probe_post`、`probe_abspath`、`probe_merged`、`probe_header` |
| 为 0 | noop、gold、`gold_log_only`、`always_log`、`never_log`、`print_only`、`output_verbose`、`probe_basename`、`probe_kwonly`、`probe_logonly_v` |

共同事实：
- 全部 `p2p_fail=0`、`reference_missing_count=0`、`num_parsed_tests=13`；
- 两段都完整，日志 sha 与账本一致；
- `run_*.out` 均为 exit 0，容器创建与删除均为 1/1，无清理失败；
- 15 份 `audit_*/materials.json` 字节相同，绑定原补丁 `23d0fb5b…`、v2 补丁 `ee614041…`，父版本为 v1。

**是否新引入过严或过宽的断言：未发现。**
- **过严**：v2 相对 v1 的改动，只有放宽和恢复 base 公开断言两类：
  - 省略参数部分恢复 base 原形；
  - verbose 版本缺失的调用不再查输出；
  - verbose 不匹配版本从"输出为空"放宽为"不出现补丁名、不新增应用"；
  - 描述检查从整行放宽为内容。

  因此凡能通过 v1 的候选，都能通过 v2 的这些位置。
- **过宽**：10 个错误候选仍为 0，各自失败在依据表所列的断言上。放宽只额外接受三类行为：
  - verbose 下出现不含补丁名的说明行；
  - 版本缺失时的任意输出；
  - 同内容但换了行格式的描述。

  这三类都不违反公开要求。
- **遗留低风险边界**（非 v2 新增，不阻断）：
  - 位置参数调用：已登记为边界。
  - verbose 输出不得出现未应用补丁的文件名。v1 在匹配版本已有此检查，v2 扩到不匹配版本；base 代码根本不读其它版本的条目，合理实现很少会去列出它们。
  - 描述内容按 base 的 `Apply patch (type): description` 文本核对：把既有描述行改写成别的格式的实现会被拒，题面没有要求改动既有输出。
  - `output_verbose`：判定不变。

**是否仍有阻断：无。** 三处文字小问题建议顺手改：
1. MONAI5932 切片的表述，按上表 B3 行更正；
2. N2 的交叉引用；
3. 依据表第 7 行的"未构造"说明。

**本节未查**：
- 未跑正式评分；
- 未复跑真实文件行为矩阵；
- 未核 `evidence_manifest.json` 的更新内容；
- 未审 result.md 中 v2 聚焦范围以外的改动。
