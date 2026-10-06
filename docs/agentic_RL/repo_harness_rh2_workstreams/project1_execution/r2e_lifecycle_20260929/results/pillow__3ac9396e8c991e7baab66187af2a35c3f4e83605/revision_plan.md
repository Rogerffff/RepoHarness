# pillow `3ac9396e`：R-c 修订方案（第 2 轮：A + B + C）

2026-09-29，修订执行者（单题闭环试行）。**状态：第 2 轮草案定稿，试跑验收通过（试跑不是正式评分）；待协调者落正式修订单并跑正式评分。**

- **第 1 轮**（A+B）经 Codex 复核（`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/codex_reviews/review_revision_pillow.md` §1）判为"需小改"：A、B 保留；K2 仍是未处理的 S1，须补断言堵住；A-only 不通过。
- **第 2 轮**按复核补了 C，9 个候选全部重跑。第 1 轮试跑结果移到 `trials/round1/`，第 2 轮结果在 `trials/abc_*.json`。
- `revision_draft_a_only.json` 已标为否决，不得用于正式材料。

路径约定：`PUB/` = `runs/r2e_static_prep_20260924/v3/public/pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605/`，`W/` = `PUB/worktree/`，`PRI/` = `runs/r2e_static_prep_20260924/v3/private/pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605/`，`C/` = `runs/r2e_actor_20260925/grader_cands/`，`B2/` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/`，`T/` = 本目录 `trials/`。

## 1. 结论

- **模板**：R-c。三处窄修订都加在隐藏测试 `r2e_tests/test_1.py` 的 `TestFileTiffMetadata` 类里、`test_exif_div_zero` 之后，各成一个新键：
  - **A**（v1 §11 指定，§4 第 2 步）：另一个未登记 tag（私有 tag 65000）存 `IFDRational(0,0)`，读回分子、分母都是 0。
  - **C**（第 2 轮新增，§4 第 4 步）：同一个未登记 tag 存序列 `(IFDRational(0,0), IFDRational(1,2))`，读回两项的分子、分母与写入一致。
  - **B**（§4 第 4 步）：未登记 tag 存整数 5，读回仍是 `int`。
- **期望映射**：11 键 → 14 键，新增 3 键都是 PASSED，原 11 键不变。
- **试跑结果**（§5）：gold、K1、K1b 为 1；noop、K2、K3、K4、K4b、RC6 为 0，与 Codex 给的验收要求逐一相符。每个候选的失败键都与预测相同，没有 missing / extra 键。

## 2. 问题与判定

### A：只测了示例 tag（v1 §4 第 2 步，T2c）

- **公开要求**：题面描述的是一般情形——"When adding rational metadata values with a denominator of zero (e.g., `IFDRational(0, 0)`) to a TIFF image and attempting to save and reload the image, an error occurs."（`PUB/user_prompt.txt:8`）；41988 只是示例（`:16`）。公开文档：`tiffinfo` 的字段类型对数值自动识别，有理数用 `IFDRational` 传入（`W/docs/handbook/image-file-formats.rst:503-516`）；`IFDRational` 支持 0/0 本来就是为 EXIF 里的实际用法（`W/PIL/TiffImagePlugin.py:228-233`）。
- **现测试**：只断言 41988（`PRI/hidden_tests/test_1.py:188-198`）。
- **触发反例**：K4b 只在 `TAGS_V2` 登记 `41988: ("DigitalZoomRatio", RATIONAL, 0)`（`C/pillow_3ac9_K4b_tag_len_0.patch`），现材料上 11/11 得 1（`B2/grader_candidates.md:92`）。
- **为什么选 65000**：它既不在 `TAGS_V2`（`W/PIL/TiffTags.py:44-169`），也不在旧 `TAGS` 名表（`:173` 起），检查的是任意未登记 tag 上的类型自动识别，而不是"再多登记一个 EXIF 名字"。在私有 tag 上写数值是公开旧测试写明的用例（`W/Tests/test_file_tiff_metadata.py:16-20`："Use case is ImageJ private tags, one numeric, one arbitrary data"）。断言写法照抄原目标键，不限定类型码 5 还是 10。

### C：零分母值与普通有理数同在一个序列里（v1 §4 第 4 步；第 2 轮新增）

- **更正第 1 轮结论**：第 1 轮写的"K2 在题面范围内合规，只登记为 S2 缺口"不成立。**K2 是同一核心问题的 S1，现由 C 覆盖。**
- **K2 做了什么**：只有当值**全部**是零分母 `IFDRational` 时才选有理数类型（`C/pillow_3ac9_K2_zero_denominator_only.patch:9-11`）。
- **K2 错在哪**：同一 tag 的序列里只要混有非零分母的值，K2 就落回 LONG writer 抛 `struct.error`，零分母那一项同样存不下来。这仍是"含零分母的有理数元数据保存失败"，与题面描述的是同一个核心问题，不是要求修好所有非零分母输入。
- **K2 的旧分数**：现材料上 11/11 得 1（`B2/grader_candidates.md:89`），第 1 轮 A+B 下仍得 1（`T/round1/ab_K2.json`）。
- **公开依据**：
  - 题面第 8 行说的是一般的零分母有理数元数据值（同 A）。
  - `ImageFileDirectory_v2` 的公开接口文档写明"Individual values are returned as the strings or numbers, sequences are returned as tuples of the values"，类型"guessed from the type added"（`W/PIL/TiffImagePlugin.py:364-371`），即一个 tag 可以存值序列。Codex 复核已核对这一依据。
  - 有理数用 `IFDRational` 传入、类型自动识别（`W/docs/handbook/image-file-formats.rst:503-516`）。
- **期望怎么来的**：写入 `(0,0)` 与 `(1,2)` 两项；按上述公开语义，读回应是同样两项组成的元组，所以新键期望 PASSED。gold 的试跑结果用来核对，不是期望的来源。
- **断言写法**：
  - 比较 `(numerator, denominator)` 对，不直接比值。`IFDRational.__eq__` 委托给内部 `_val`（`W/PIL/TiffImagePlugin.py:305-306`），0/0 的 `_val` 是 `nan`（`:264`），所以 0/0 与 0/0 比较永远不相等。
  - 不查类型码：写成 5（gold、K1）或 10（K1b）都能通过，两种 writer 与 loader 都按分子、分母成对存取（`:601-632`）。
  - 不查 LONG / SHORT 宽度。
- **为什么仍用 65000**：沿用 Codex 给的最小反例原样。C 与 A、B 各在独立的测试方法与 IFD 里，互不影响。

### B：整数被当成有理数写入也能满分（v1 §4 第 4 步）

- **现象**：RC6 = gold，但把 `isinstance(v, IFDRational)` 写成 `isinstance(v, Rational)`（`numbers.Rational`，`int` 也算，`C/pillow_3ac9_RC6_gold_with_numbers_rational.patch`）。现材料上 11/11 得 1（`B2/grader_candidates.md:93`），但未登记 tag 上的整数被写成 RATIONAL：私有核对里 `int65000` 读回 `(5.0,)`、类型 5；base 读回 `(5,)`、类型 4；gold 读回 `(5,)`、类型 3（`runs/r2e_actor_20260925/grader/private_public_b2/p3ac9_ir_*.json`）。
- **公开依据**：文档说 `tiffinfo` 对数值自动识别字段类型（`W/docs/handbook/image-file-formats.rst:505-507`）；`ImageFileDirectory_v2` 文档说值按数字返回、类型"guessed from the type added"（`W/PIL/TiffImagePlugin.py:364-371`）；base 的 `_setitem` 已有"整数 → SHORT / LONG"的猜测分支（`:504-508`）。公开读者在读隐藏材料前就点出了这个陷阱（`B2/results/pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605/public_read.md:66`）。
- **断言约束**：不断言类型码。gold 把未登记小整数从 LONG 改成 SHORT，公开契约没有固定整数编码宽度；只断言读回值等于 5 且 `isinstance(value, int)`。Codex 复核确认这不是为保 gold 放宽要求。

## 3. 具体改动（完整测试代码）

一条 `hidden_test_text_replace`，目标 `test_1.py`（即 `PRI/hidden_tests/test_1.py`）。`old` 是 `test_exif_div_zero` 的最后三行（`:196-198`），在文件里恰好出现一次；`new` 是这三行原样保留，再接 A、C、B 三个新方法：

```python
        reloaded = Image.open(out)
        self.assertEqual(0, reloaded.tag_v2[41988][0].numerator)
        self.assertEqual(0, reloaded.tag_v2[41988][0].denominator)

    def test_div_zero_other_unregistered_tag(self):
        # Same zero-denominator round trip on another tag that has no
        # TAGS_V2 entry (private tag 65000), not only the example tag.
        im = hopper()
        info = TiffImagePlugin.ImageFileDirectory_v2()
        info[65000] = TiffImagePlugin.IFDRational(0,0)

        out = self.tempfile('temp.tiff')
        im.save(out, tiffinfo=info, compression='raw')

        reloaded = Image.open(out)
        self.assertEqual(0, reloaded.tag_v2[65000][0].numerator)
        self.assertEqual(0, reloaded.tag_v2[65000][0].denominator)

    def test_div_zero_in_rational_sequence(self):
        # A zero-denominator value inside a sequence of rationals on one
        # tag with no TAGS_V2 entry; every value must round trip.
        # 0/0 never compares equal, so numerator and denominator are
        # compared.
        im = hopper()
        info = TiffImagePlugin.ImageFileDirectory_v2()
        info[65000] = (TiffImagePlugin.IFDRational(0,0),
                       TiffImagePlugin.IFDRational(1,2))

        out = self.tempfile('temp.tiff')
        im.save(out, tiffinfo=info, compression='raw')

        reloaded = Image.open(out)
        self.assertEqual([(0, 0), (1, 2)],
                         [(v.numerator, v.denominator)
                          for v in reloaded.tag_v2[65000]])

    def test_unregistered_int_tag_type(self):
        # Integer values on a tag with no TAGS_V2 entry are still detected
        # as integers and read back as int. IFDRational(5, 1) == 5, so the
        # value type is checked, not only equality.
        im = hopper()
        info = TiffImagePlugin.ImageFileDirectory_v2()
        info[65000] = 5

        out = self.tempfile('temp.tiff')
        im.save(out, tiffinfo=info, compression='raw')

        reloaded = Image.open(out)
        value = reloaded.tag_v2[65000][0]
        self.assertEqual(5, value)
        self.assertIsInstance(value, int)
```

- 与第 1 轮相比只多了 C 这一个方法，A、B 逐字不变（生成脚本已核对：去掉 C 后与第 1 轮文本相同）。
- 三个新方法都沿用原测试的 `hopper()`、`self.tempfile`、`compression='raw'`。`test_1.py` 先于 `test_2.py` 运行，所以此时 `WRITE_LIBTIFF` 仍是默认值 False。
- 本机已对修订后文本做语法编译检查，没有执行。修订前后摘要见 `revision_draft.json` 的 `local_private_copy_sha256`（本机私有副本的摘要，仅供核对；正式修订单的 `sha256_before` 以来源行原文为准）。

## 4. 期望映射的逐键变化

| 键 | 修订前 | 修订后 | 来源 |
| --- | --- | --- | --- |
| `TestFileTiffMetadata.test_div_zero_other_unregistered_tag` | —（无此键） | PASSED | A |
| `TestFileTiffMetadata.test_div_zero_in_rational_sequence` | — | PASSED | C（第 2 轮新增） |
| `TestFileTiffMetadata.test_unregistered_int_tag_type` | — | PASSED | B |
| 其余 11 键 | PASSED | PASSED（不变） | — |

- **键数**：11 → 14（第 1 轮是 13）。
- **键名格式**：本题入口是自带的 unittest runner（`PRI/run_tests.sh`、`PRI/hidden_tests/unittest_custom_runner.py:121-126`），键为 `类名.方法名`，不带 ANSI。
- **不撞键**：三个新名字在 `test_1.py`、`test_2.py` 里都不存在。
- **期望来源**：三个新键的 PASSED 都来自公开要求（A：题面的一般情形；C：同上，加上公开接口允许值序列；B：base 旧行为与文档约定），不是照抄 gold 输出。

## 5. 验收（9 个候选的前后结果）

- **正对照**：gold。
- **试跑工具**：`rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`。
- **三列分数的来源**：
  - 现材料：09-25 的正式评分，11 键，出处见"来源"列。
  - 第 1 轮：A+B 试跑，13 键，文件在 `T/round1/`。
  - 第 2 轮：A+B+C 试跑，14 键，文件在 `T/`。

| 候选 | 补丁 | 现材料 | 第 1 轮 | 第 2 轮（应得 / 实得） | 第 2 轮失败的键（全部与预测一致） | 第 2 轮文件 |
| --- | --- | --- | --- | --- | --- | --- |
| gold（正对照） | `PRI/gold.patch` | 1（`B2/grader_candidates.md:56`） | 1 | 1 / **1**（14/14） | — | `abc_gold.json` |
| K1（合理替代，类型 5） | `C/pillow_3ac9_K1_rational_type_5.patch` | 1（`:87`） | 1 | 1 / **1**（14/14） | — | `abc_K1.json` |
| K1b（合理替代，类型 10） | `C/pillow_3ac9_K1b_rational_type_10.patch` | 1（`:88`） | 1 | 1 / **1**（14/14） | —（C 不固定类型码） | `abc_K1b.json` |
| noop | — | 0（`:55`） | 0 | 0 / **0** | A、C、`test_exif_div_zero` 都是 ERROR（`struct.error`）；B PASSED（base 整数读回整数） | `abc_noop.json` |
| K2（只特判全零分母；C 的触发反例） | `C/pillow_3ac9_K2_zero_denominator_only.patch` | 1（`:89`） | **1** | 0 / **0** | 只有 C ERROR：`struct.error: required argument is not an integer`，出在 C 的 `im.save` | `abc_K2.json` |
| K3（只加 `__index__`） | `C/pillow_3ac9_K3_index_on_rational.patch` | 0（`:90`） | 0 | 0 / **0** | A、`test_exif_div_zero` FAILED（`0 != 1`）；C FAILED（读回 `[(0, 1), (1, 1)]`） | `abc_K3.json` |
| K4（只登记 41988，长度 1） | `C/pillow_3ac9_K4_tag_len_1.patch` | 0（`:91`） | 0 | 0 / **0** | A、C ERROR（`struct.error`）；`test_exif_div_zero` ERROR（`'IFDRational' object is not subscriptable`） | `abc_K4.json` |
| K4b（只登记 41988，长度 0；A 的触发反例） | `C/pillow_3ac9_K4b_tag_len_0.patch` | **1**（`:92`） | 0 | 0 / **0** | A、C ERROR（`struct.error`） | `abc_K4b.json` |
| RC6（整数也按有理数写；B 的触发反例） | `C/pillow_3ac9_RC6_gold_with_numbers_rational.patch` | **1**（`:93`） | 0 | 0 / **0** | 只有 B FAILED（`5.0 is not an instance of <class 'int'>`） | `abc_RC6.json` |

- **误判纠正情况**：现材料上 K2、K4b、RC6 三个错误候选都得 1。第 2 轮三者都是 0，各自只在针对它的新键上失败（K4b 另在 C 上失败，原因相同：65000 没有登记）。
- **已知错误候选仍为 0**：K3、K4 在三列里都是 0。
- **合理替代解没有被误拒**：K1、K1b 在第 2 轮仍为 1。
- **逐项核对**（由生成 `revision_draft.json` 的脚本逐条断言）：
  - 每条试跑都 `RH2_APPLY_RC=0`（候选确已应用），`RH2_TRIAL_EDITS_APPLIED=1`（草案确已作用）；
  - 观测键数 = 期望键数 = 14，missing 与 extra 均为空；
  - 失败键集合与上表预测逐一相同；
  - 9 条试跑用的是同一张派生镜像。
- **现材料基线在新机器上的复核**：`T/round1/base_noop_current.json`（0，只有 `test_exif_div_zero` ERROR）与 `T/round1/base_gold_current.json`（1，11/11）。

## 6. 修订后仍受保护的公开要求与已知缺口

- **受保护的公开要求**：
  - 示例 tag 41988 的 0/0 往返（原目标键）；
  - 另一个未登记 tag 的 0/0 往返（A）；
  - 同一 tag 上含零分母的有理数序列的往返（C）；
  - 未登记 tag 上的整数仍读回整数（B）；
  - 原有回归键：显式 `tagtype` 优先（`test_rt_metadata`）、已登记 RATIONAL 往返（`test_write_metadata`）、v1 API 形状（`test_read_metadata`）、`dpi` 走 `IFDRational` 保存（`test_ifd_rational_save`）。
- **已知缺口（S2，登记，本轮不修）**：
  1. 整组都不含零分母的有理数（例如未登记 tag 上只写 `IFDRational(1, 2)`）不测。题面以零分母为中心；base 上这种输入同样失败，没有被任何候选改坏，是否纳入交用户（§7）。
  2. 类型码 5 与 10 只在已测的非负值下等价。负值与 SIGNED RATIONAL 的打包问题是 base 就有的。
  3. gold 把未登记小整数从 LONG 改成 SHORT，值不变，公开契约不固定编码宽度，不计缺陷（Codex 第二批复核 O-1）。
  4. `test_ifd_rational_save` 依赖 libtiff 编码器，今后重建镜像要保留 libtiff。
  5. JPEG / MPO 写 EXIF、`tiffinfo` 传普通 dict 的路径没有覆盖。

## 7. 需要决定的事项

- **模板内**：无。A、B 经 Codex 复核保留；C 按复核要求补入。A-only 已被否决，不再作为选项（`revision_draft_a_only.json` 已标注）。
- **用户（模板外，可选；不阻塞本题）**：是否把题意扩到"整组都不含零分母的有理数"（§6 第 1 条）。
  - 选项 (a)：不扩，登记为 S2。建议选这个。
  - 选项 (b)：扩。需要同时做 R-f（把题面改成一般有理数）和 R-c（加只含 1/2 的断言），属于改变任务目标。
  - 影响：(b) 能让奖励再区分"只修零分母路径"与"修根因"。但 C 已经拒绝了实际出现过的零分母特判 K2，(b) 的边际收益有限，而题面标题与描述都要改。

## 8. 试跑条件，以及与正式评分的差别

- **机器与镜像**：本批 R2E CPU 机；派生镜像 `sha256:6f98a901ad4e56f30f567b45ff1c4e39a234dc8a8d7ca89e1410de74cf2ba6f9`，配方 `r2e_derive_v1+sysconfig_v1`。第 1、2 轮用的是同一张镜像，见每个结果文件的 `image` 与 `recipe_id` 字段。
- **工具做了什么**（`rh2/experiments/r2e_lifecycle_20260929/trial_grade.py:2-9`）：在不联网的一次性容器里，按正式 grader 的顺序应用候选、换上隐藏测试、应用草案，以 uid 54322 跑来源入口，用正式解析器逐键比对。
- **与正式评分的差别**：
  - 不做基线重建比对；
  - 不核隐藏测试树与入口摘要；
  - 权限布置简化为整个 `/testbed` 交给评分用户。
- **所以还差正式评分**：这些结果只作修订依据。定稿后仍要走正式材料与正式评分，至少跑 gold、noop、K2、K4b、RC6。Codex 也指出 C 的反例此前只有原函数证据；本轮试跑补上了完整的保存与重开往返，正式评分仍待做。
- **耗时**：每次试跑约 80–90 秒，测试段本身不到 1 秒。

## 9. 探针就绪差距（对照本批 README §3）

1. **noop 0 / gold 1**：两轮试跑都满足。正式材料落地后的正式评分待协调者跑。
2. **真实解题身份的开发命令**：第二批 devcheck 已在旧机器、旧镜像上跑通（`B2/results/pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605/card.md` §3）；新机器新镜像上待协调者复验。
3. **S1**：A、B、C 已按模板修订并试跑验收；第 2 轮待协调者确认后落正式材料。
4. **公开包泄漏预检**：本修订只动隐藏测试与期望，公开包不变；R2E rollout 预检由协调者跑。
5. **题卡四项用途**（修订定稿、正式评分之后）：
   - `problem_localization=yes`；
   - `capability_comparison=conditional`：评分依据已核，差新机器新镜像上的公开开发命令复验；
   - `training_candidate=conditional`：再差正式评分；
   - `heldout_candidate=no`：审查者见过 gold 与隐藏测试，且本题与同仓 6 题有包含关系（`B2/results/pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605/card.md` §4 第 5 条）。
