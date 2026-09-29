# 独立复核初判：pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605

2026-09-25，独立复核者（第一步，读主审产物之前）。只做静态阅读和已有证据核对，没有运行代码或容器，也没有修改任何原件。

## 0. 初判结论（一屏）

- **题目目标**：在 TIFF 元数据里写入 `IFDRational(0, 0)`（示例中 tag 41988），保存再读回时不应报 `struct.error`，读回后 `tag_v2[41988][0]` 的分子和分母都应为 0。
- **目标键只有 1 个**：`TestFileTiffMetadata.test_exif_div_zero`。noop 下为 ERROR，报错正是题面所写的 `struct.error: required argument is not an integer`；gold 下为 PASSED。其余 10 个键在 noop 和 gold 下都是 PASSED，属于回归键。期望映射中 11 个键全部是 PASSED，没有 FAILED 或 ERROR 键，所以"更完整的修复把 FAILED 键翻成 PASSED、反而判 0"的 R2E 风险不存在。
- **目标断言与题面原例基本一一对应**：同一 tag、同一取值、同样使用 `compression='raw'`、同样按 `[0]` 取分子和分母。唯一差别是图片：测试用 `hopper.ppm`，题面用 `hopper.png`，不影响结论。`[0]` 的读回形状由公开示例直接给出，不属于隐藏要求。**没有发现合理修复被误拒**。
- **主要限度（不阻塞使用）**：
  1. 覆盖面窄。只测了 41988 这一个 tag 的 0/0。只登记 41988 的窄修复（候选 C3），以及把普通 int 也判成 RATIONAL 的错误修复（候选 C6），按静态推断都会得 1。
  2. 题面把问题框在"分母为零"上，比真实根因窄。真实根因是：未登记 tag 的类型被默认 `TagInfo.type=4` 固定为 LONG。devcheck 实测，41988 取 1/2 同样报错，而已登记的 282 取 0/0 本来就正常。
  3. 修复可以从其它题拿到。6 道同仓后续题的公开初态里已经带有本题修复（上游重构后的写法）和同名测试，gold 逐字比对没有报出，因为上游后来重构了写法。
- **暂定处置**：静态候选，可进入探针，等 actor 验证（needs_review，reason 为"静态候选待 actor 验证"）；不需要改题。**最值得先做的一步**：用正式评分代码实跑 §5 的 C3、C4、C6 三个候选（每个约 30 秒），确认"窄修复或错误修复被接受""违反示例形状的修复被拒绝"这两类静态预测。

## 1. 实际读取范围

- 角色与方法：`roles/reviewer_r2e.md` 全文；`roles/investigator_r2e.md` 全文（口径只取"R2E 的评分口径""材料""第二批补充规则"三节）；`quality_review_protocol_20260920.md`、`r2e_environment_card.md`、`record_template.md`。
- 公开包 `PUBLIC_DIR`：`user_prompt.txt`、`environment_brief.md`、`public_bundle.json`、`worktree_manifest.json`（结构与 untracked 部分）；worktree 中的 `PIL/TiffImagePlugin.py`（40–70、200–870、1290–1467 行）、`PIL/TiffTags.py`（全文）、`Tests/test_file_tiff_metadata.py`、`Tests/test_tiff_ifdrational.py` 与 `Tests/helper.py`（都只用来和隐藏测试 diff）、`Tests/images/` 目录列表、`docs/handbook/image-file-formats.rst`（495–520 行）、根目录 `run_tests.sh`。
- 私有包 `PRIVATE_DIR`：`hidden_tests/` 下全部 5 个文件、`expected_output.json`、`gold.patch`、`run_tests.sh`、`revisions.json`（为 `[]`）、`run_refs.json`、`grading_bundle.json`、`validation_bundle.json`。
- 运行原件（run_refs 中 material=current 的行）：
  - 账本 `runs/r2e_rf_20260923/remote/ledger_r2e_all_{noop,gold}.jsonl:40`、`ledger_r2e_reps_{noop,gold}.jsonl:2`、`ledger_r2e_requal_{noop,gold}.jsonl:1`、`runs/r2e_env_repair_20260924/_rerun2/ledger_{noop,gold}.jsonl:40`。
  - 对应的 8 份 `.eval.log`：RF all 两份全文读；其余读摘要行，并与 RF all 做了 diff，去掉临时文件名和时间戳后内容相同。
  - M3 独立 runner 的 gold 日志 `runs/env_overnight_20260916/M3/gold_ledger/logs_r2e/pillow/3ac9396e8c99/gold/a1/test_output.txt`（摘要行）。
  - diagnostic 行只看了 run_refs 里的摘要，没有打开日志。
- devcheck：`runs/r2e_actor_20260925/devcheck/pillow__3ac9396e8c991e7baab66187af2a35c3/` 下的 `orig/commands_with_preflight.json`、`orig/captures/*.out` 全部、`orig/attempt.json`（image 字段）、`orig/prelaunch.json`（image 字段）、`orig/bringup_artifacts/cc_version_observed.json`、`orig/stub/requests/messages_000.json`（只看消息结构）、`private_gold/private_control.json`、`private_gold/stdout.log`。
- 跨题比对：`cross_task_gold_scan.json`、`cross_task_test_scan.json`（只看与 pillow 有关的条目）。同仓 6 道题的**公开** worktree 里，`src/PIL/TiffTags.py`、`src/PIL/TiffImagePlugin.py` 用 grep 定位，`Tests/test_file_tiff_metadata.py` 只看了 `test_exif_div_zero`。
- **没有读**：`OUTPUT_DIR` 里的其它文件（包括 `public_read.md`）、任何 `history/`、`docs/.../r2e_env_repair_20260924/`、首批和 Codex 复核目录、其它 review 目录、本批 README、`assignments.json`、`grader_candidates.md`、同仓其它题的私有包，以及 `runs/` 下的分析与汇总文件。`runs/r2e_env_repair_20260924/_rerun2/` 下只打开了 run_refs 点名的两份账本行和两份日志。

## 2. 八方面

| 方面 | 已查 | 结论 |
| --- | --- | --- |
| 公开需求 | 题面、示例、预期与实际报错；公开文档 `docs/handbook/image-file-formats.rst:503-515`（写明"TIFF field type is autodetected for Numeric and string values"，并说明 rational 值应以 `IFDRational` 传入）；`TiffImagePlugin.py:367-371` 的 docstring（"guessed from the type added"） | 目标清楚。题面把问题框在"分母为零"上，比根因窄，但运行示例得到的 traceback 会指向写 LONG 的位置，读者能自行纠正。示例中的 `hopper.png` 在 `/testbed` 根目录下不存在，实际位置是 `Tests/images/hopper.png`，属于小摩擦。 |
| 材料与初始问题 | base 源码调用链（§3）；noop 日志 | 初态确有此 bug，路径已由执行证据确认：`test_1.py:194` → `TiffImagePlugin.py:1446 _save` → `:715 save` → `:571` 的 type-4 写函数（lambda）→ `:546 _pack` → `struct.error`（noop 日志第 27–49 行）。base commit `48e4e07`、gold 修改的路径 `PIL/...`、隐藏测试树的 sha `43f98461…` 三者对得上。 |
| 测试是否测到要求 | 11 个键全部读过；目标键 `test_1.py:188-198` | 原例覆盖到了。泛化没有覆盖：其它未登记 tag、非零分母、IFDv1 与 libtiff 写出路径都没测。gold 顺带改变的"未登记 tag 类型自动推断"（int → SHORT/LONG、float → DOUBLE、str → ASCII）完全没有测试。 |
| 是否误拒合理解 | 构造了 C1、C2（合理替代解）和 C4（登记 tag 时 length 取 1） | 没有发现误拒。C4 读回的是标量，会违反公开示例里的 `[0]`，被拒有公开依据，单列为"违反公开示例形状的候选"。 |
| 回归与 gold 完整性 | 追了 `TagInfo.type` 的全部使用者（只有 `_setitem:501`）、`_save:1314-1331`、`ImageFileDirectory_v1`；devcheck 的公开测试对照 | gold 修好了原例，而且对 1/2 同样有效（private_control `pr3_2`）。gold 的附带改动是"未登记 tag 走自动推断"，base 里这段代码实际是死代码，恢复它有文档依据，不算无关改动。公开 tiff 测试用 unittest 跑时 base 和 gold 都是 42 OK。libtiff 测试在 pytest 下被 helper 噪声遮蔽，只能说两边计数相同（§6）。 |
| agent 开发条件 | devcheck 的 orig 与 private_gold；`environment_brief.md` | 纯 Python 修改，不需要构建。`python` 与 `PIL` 都指向 `/testbed`，已在 actor 身份下实测。**公开提示建议用 `python -m pytest`，但在本仓库会产生假失败**，改用 unittest 则干净，详见 §6。 |
| 交付与评分边界 | `run_tests.sh`、runner、helper 的 diff、账本里的 projection 字段 | 隐藏的 `helper.py` 与 base 的 `Tests/helper.py` 完全相同（diff rc=0），并通过 `r2e_tests` 位于 sys.path[0] 被优先导入，所以候选改 `Tests/helper.py` 不影响评分。隐藏测试导入私有的 `_limit_rational`（`test_1.py:9`），这是隐含约束，风险低。worktree 中可见的 `run_tests.sh` 只暴露了 runner 文件名，不含答案。 |
| 题目关系与用途 | 两份跨题比对；6 道后续题的公开 worktree | 本题修复与测试都出现在 6 道后续 pillow 题的公开初态里（§8）。本题 base 不包含其它题的修复。 |

## 3. 核心需求—测试映射

| 需求或旧行为 | 公开依据 | 测试键 / 决定性断言 | 覆盖 | 执行证据 |
| --- | --- | --- | --- | --- |
| tag 41988 = `IFDRational(0,0)` 能以 raw 方式保存成功 | 题面示例与 Expected | `test_exif_div_zero`，`test_1.py:194` 的 `im.save(out, tiffinfo=info, compression='raw')` 不抛异常 | 覆盖 | noop 为 ERROR（`struct.error`，noop 日志 :49、:53）；gold 为 PASSED（gold 日志 :25） |
| 读回后 `tag_v2[41988][0]` 的分子、分母都为 0 | 题面示例的 print 行与 Expected | `test_1.py:197-198` 的两个 `assertEqual(0, …[0].numerator/denominator)` | 覆盖；`[0]` 的形状来自公开示例 | gold 为 PASSED；private_control 中 `pr6_3` 输出 `0 0` |
| 其它未登记 tag、非零分母的 IFDRational 也应能保存（题面泛称"rational metadata values"，文档写明会自动推断类型） | 题面 Description、`image-file-formats.rst:503-515` | 无 | **缺失** | devcheck `pr3_2`：base 下 41988=1/2 也会 FAIL，gold 下 OK。说明缺口真实存在，只是没有测试键 |
| 未登记 tag 的 int、float、str 自动推断出合理类型（旧行为是一律 LONG，gold 改为 SHORT/LONG/DOUBLE/ASCII） | 同上 | 无 | **缺失** | 无 |
| 已登记的 RATIONAL tag（XResolution）经 dpi 保存，libtiff 和 python 两条写出路径都正确 | 旧行为 | `Test_IFDRational.test_ifd_rational_save`（`test_2.py:49-60`），noop 下已通过 | 回归保护 | noop 与 gold 都是 PASSED |
| 从文件回写元数据时 rational 能往返（`_limit_rational` 的语义） | 旧行为 | `test_write_metadata`（`test_1.py:113-155`） | 回归保护 | 两边都是 PASSED |
| IFDRational 的相等比较和 `_val` 行为 | 旧行为 | `test_sanity`、`test_nonetype` | 回归保护 | 两边都是 PASSED |

反查关键断言的依据：目标键里每条断言都能从题面示例找到出处，没有"只能读隐藏材料才知道"的要求。

## 4. R2E 专项

- **(a) 非 PASSED 期望键**：没有。`expected_output.json` 中 11 个键全部是 PASSED，更完整的修复不会因为翻转失败键而判 0。
- **(b) 题面报错是否出现在 noop 目标键上**：出现了，且是逐字一致。RF all noop 日志第 27–49 行在 `test_exif_div_zero` 下报出 `struct.error: required argument is not an integer`，状态为 ERROR（异常不是断言失败）。reps、requal、env rerun2 三组 noop 相同。
- **(c) 题面是否泄漏修法**：没有。题面没有提到 `tagtype`、`TagInfo` 或类型推断。反而是"分母为零"的说法可能把读者引向 `_limit_rational` 或 `IFDRational.__init__`（见候选 C5），不过示例的 traceback 会指向正确位置。
- **(d) 测试支撑、搬迁伪影与撞键**：
  - `run_tests.sh` 是 `.venv/bin/python -W ignore r2e_tests/unittest_custom_runner.py`，**不是**环境卡 §1 写的 `pytest -rA r2e_tests`。unittest runner 打印的摘要行形如 `PASSED test_1::TestFileTiffMetadata::test_exif_div_zero`（`unittest_custom_runner.py:65-68,123`），parser 去掉模块名后得到键，账本记 `num_parsed_tests=11`，`num_parsed_outside_segment=0`。
  - 两个类名 `TestFileTiffMetadata` 与 `Test_IFDRational` 不同，**不会撞键**。
  - helper 是 base 版的原样副本。测试资产 `Tests/images/hopper{.ppm,.png,.tif,_g4.tif,.iccprofile.tif,.iccprofile_binary.tif}` 都在 worktree 中，按相对 `/testbed` 的路径读取。
  - `test_ifd_rational_save` 会改模块全局 `TiffImagePlugin.WRITE_LIBTIFF`，但它在最后一个模块里执行（discover 按文件名排序），不影响目标键。
- **(e) 时间、随机、资源敏感的键**：没有发现。测试总耗时 0.02s；临时文件很小，写在 `/tmp`。一个测试失败后，后续测试的临时文件不会被清理，只打印 "orphaned"，不影响键。`IFDRational(0,0)` 在 `cvt_enum` 里作为 dict 键时要算 `hash(nan)`，Python 3.9 下是确定值。
- **(f) 材料修订**：没有（`revisions.json` 为 `[]`，`grading_bundle.row.material_revisions` 为 `[]`）。
- **补充：镜像身份**。当前材料行分布在同一 tag `rh2-r2e-derived/pillow:3ac9396e8c99-r2e_derive_v1` 的三次构建上：
  - `74c3618c0072…`：RF reps 行；
  - `7a80aa717582…`：RF all、requal、env rerun2；
  - `c9ec14f75045…`：devcheck 的 orig 与 private_gold（`attempt.json:156`、`private_control.json` 的 image）。

  隐藏测试没有在 `c9ec14…` 这次构建上跑过，private_gold 只跑了公开命令。配方相同，风险低，但"actor 镜像上的评分结果"属于推断，没有实测。

## 5. 可区分候选（可直接改成补丁，请协调者实跑）

| 编号 | 改法 | 性质 | 预期得分 / 不符的键 |
| --- | --- | --- | --- |
| C1 | `PIL/TiffImagePlugin.py` 的 `ImageFileDirectory_v2._setitem`：不改 `TagInfo` 的默认值，把 `:499-503` 的 try/except 改为 `if tag in TAGS_V2: self.tagtype[tag] = info.type`，否则走自动推断，并在 int 判断之前加上 `all(isinstance(v, IFDRational))` → 5 | 合理替代解 | 预期 1（11/11） |
| C3 | 只在 `PIL/TiffTags.py` 的 `TAGS_V2` 中加 `41988: ("DigitalZoomRatio", RATIONAL, 0)`，不动类型推断 | **窄的部分修复**：其它未登记 tag（如 65000=`IFDRational(1,2)`）仍报 `struct.error`，违背题面泛称和文档里的"自动推断" | 静态预期 **1**，说明存在漏测 |
| C4 | 同 C3，但按 EXIF 规范写成 `("DigitalZoomRatio", RATIONAL, 1)` | 违反公开示例形状：length 为 1 时 `_setitem:527-530` 会存成标量，`tag_v2[41988][0]` 抛 `TypeError: 'IFDRational' object is not subscriptable`。上游后来的版本确实改成了标量读回（后续题 worktree 的 `test_exif_div_zero` 中没有 `[0]`），但本题 base 和题面示例都要求 `[0]` | 预期 **0**，`test_exif_div_zero` 为 ERROR。被拒有公开依据，不算误拒 |
| C6 | 按 gold 改动，但把 `isinstance(v, IFDRational)` 换成 `isinstance(v, Rational)`（`numbers.Rational`，已在 `:50` 导入） | **错误实现**：`int` 也是 `Rational`，未登记 tag 的整数会被写成 RATIONAL，读回变成 `IFDRational(n,1)`，违背文档里"数值自动推断"的旧行为。隐藏测试中没有键让未登记 tag 的 int 走自动推断后保留该类型：`test_write_metadata` 在 `_save:1319` 会用文件原类型覆盖推断结果 | 静态预期 **1**，说明存在漏测。区分实验：未登记 tag 65000=5，保存后读回，base 与 gold 得到 `(5,)`，C6 得到 `(IFDRational(5,1),)` |

另有一条已知会被拒绝的方向，不需要实跑：C5，只改 `_limit_rational`、`IFDRational` 对 0 分母的处理，但不改类型选择。这样 tag 41988 仍被判为类型 4，照样报 `struct.error`，预期 0，拒绝合理。C2（写出时把 type 3/4 且值为 IFDRational 的条目改成 5）是另一条合理路线，静态预期 1；它与 C1 结论相同，所以优先跑 C1。

## 6. gold 检查与开发需求

**gold**

- `TiffTags.py:26` 把 `type=4` 改为 `None`；`TiffImagePlugin.py:499-512` 把死掉的 try/except 改成 `if info.type`，并在自动推断里新增 IFDRational → 5。
- 能修好原例（private_control `pr6_3` 输出 `0 0`），也能修好 1/2（`pr3_2`），282 不受影响。
- 附带的行为变化：未登记 tag 的 int 从 LONG 变为小于 2^16 时写 SHORT；float、str、bytes 从报错变为 DOUBLE、ASCII、UNDEFINED。这些变化都有文档依据，没有测试。
- 公开测试的对照：用 unittest 跑 `test_file_tiff_metadata`、`test_tiff_ifdrational`、`test_file_tiff`，base 与 gold 都是 `Ran 42 tests … OK`（orig `pr8_5_cmd.out:122-124`；private_control `pr8_5`）。libtiff 与 jpeg/mpo 用 pytest 跑时，base 和 gold 计数相同：libtiff 13 failed / 9 passed / 2 errors（orig `pr9_7_pytest.out:472`，gold 的 tail 相同），jpeg/mpo 1 failed / 4 passed（`pr9_6_pytest.out:58`）。但这些失败都来自 helper 与 pytest 不兼容，会遮蔽测试体本身的结果。**所以 libtiff 无回归只是计数层面的证据**，要确认需用 unittest 跑 `test_file_libtiff`。

**开发需求**（除注明外，均为 actor 身份在镜像层面的实测，来源 devcheck orig）

- 身份 uid 54321，`VIRTUAL_ENV=/testbed/.venv`；`PIL` 在 cwd=/tmp 时也解析到 `/testbed/PIL/__init__.py`；`_imaging.cpython-39-…so` 已在 `/testbed/PIL` 中，并含 libtiff 编码器（`env.out`、`pr0_1_cmd.out`）。
- 没有 pip，pytest 版本 8.3.4。纯 Python 修改，不需要构建，也不需要联网。
- 预检三项都是 ok（`r2e_preflight.out`）。
- **开发缺口（不影响评分）**：公开提示说用 `python -m pytest` 跑测试，但 base 的 `Tests/helper.py:30-44` 中 `delete_tempfile` 依赖 `self.currentResult.wasSuccessful()`，在 pytest 8.3.4 下抛 AttributeError。结果是凡用到 `self.tempfile` 的测试，在 base 就被报成 FAILED（`pr7_4_pytest.out:7-9,14-22,304-314`：9 failed，其中包括 `test_rt_metadata`、`test_write_metadata`、`test_iccprofile`）。解题者可能把这些误认为是自己的改动造成的，或者被诱导去改测试 helper；改 helper 不影响评分，因为评分用的是隐藏副本。可用的验证方式：`PYTHONPATH=Tests python -m unittest test_file_tiff_metadata test_tiff_ifdrational test_file_tiff`（42 OK），或直接运行题面示例，图片路径改为 `Tests/images/hopper.png`。
- 提交边界：`PIL/TiffImagePlugin.py`、`PIL/TiffTags.py`。
- actor 待验：真实模型能否求解；模型实际收到的完整消息。devcheck 的 stub 请求里 user 消息是 "Devcheck run: …"，不是本题 prompt（`stub/requests/messages_000.json`）；经 Qwen adapter 的链路也未验。

## 7. 缺口与疑点汇总

| 编号 | 问题 | 影响 | 证据级别 |
| --- | --- | --- | --- |
| G1 | 只测 41988 的 0/0；gold 附带的推断变化没有测试；窄修复（C3）和错误修复（C6）预计都会得 1 | 漏测，可能放过部分或错误的修复；不影响正确修复得分 | 静态推断，加上 devcheck `pr3_2` 的执行事实（1/2 在 base 下也失败） |
| G2 | 题面的"zero denominator"框定比根因窄 | 可能误导解题方向，但示例的 traceback 可以纠正 | 执行事实（`pr3_2`：282 取 0/0 在 base 下正常，41988 取 1/2 失败） |
| G3 | 公开提示推荐的 pytest 在本仓库产生假失败 | 解题侧有噪声，并有诱导改测试的风险；不影响评分 | actor 身份实测 |
| G4 | 本题修复可以从 6 道后续 pillow 题的公开初态拿到 | 训练与评测拆分时要避免同时暴露 | 公开 worktree 的 grep 结果与 test_scan |
| G5 | 隐藏测试没有在 actor 实际使用的镜像构建 `c9ec14…` 上跑过 | 低风险，配方相同 | 账本与 attempt 中镜像 ID 不同 |
| G6 | 环境卡 §1 写的是 `pytest -rA r2e_tests`，本题实际用 unittest runner | 只是描述不一致，评分已由运行证据证明可用 | 私有 `run_tests.sh` 与日志 |

G1 的修订方向（可选，不建议为诊断用途改题）：以文档中的"自动推断"和题面泛称为依据，可以补一个"未登记 tag 取非零分母 IFDRational 的往返"键，用来区分 C3；如需区分 C6，再补一个"未登记 tag 的 int 读回仍为 int"键。

## 8. 题目关系

- `cross_task_gold_scan.json` 中没有本题条目。原因是上游后来把字面量换成了 `TiffTags.RATIONAL` 等常量，`TagInfo` 的签名也改成了 `length=None`，逐字比对达不到 80%，属于**漏报**。
- `cross_task_test_scan.json:763-823` 记录了本题新增的 `test_exif_div_zero`、`test_ifd_rational_save` 出现在以下 6 题的初态里：`pillow__2b061b68…`、`2d01f7d0…`、`3a61c9e9…`、`4bc64835…`、`a682ceaf…`、`f9d3ee0f…`。
- 在这 6 题的公开 `src/PIL/TiffTags.py:26` 中，签名都是 `type=None, length=None`；`src/PIL/TiffImagePlugin.py` 中都有 `if info.type:` 和 `if all(isinstance(v, IFDRational) for v in values): … TiffTags.RATIONAL`（2b061b68 在第 535–541 行，其余题在 556–592 行之间）。**结论：本题修复的等价实现是这 6 题公开初态的一部分**，本题 base 不包含其它题的修复（两份比对里都没有以本题为"被包含方"的条目）。
- 用途：R2E/SWE 型 bug 修复，改动位于公共元数据写出路径。静态阅读无法判断基座成功率。

## 附录：关键定位

- 根因：`worktree/PIL/TiffTags.py:26`（`type=4`）；`TiffTags.py:44-169` 的 `TAGS_V2` 中没有 41988，它只在旧的 `TAGS` 表 `:233` 里；`TiffImagePlugin.py:496-503` 中 `TAGS_V2.get(tag, TagInfo())` 返回的 `info.type` 为 4，永远不会触发 KeyError，所以 `:504-517` 的自动推断是死代码；`:570-576` 注册的 type 4 用 `"L"` 打包；`_save:1316-1321` 会把用户 IFD 里的 tagtype（4）复制过去。
- 0/0 的写出路径（gold 下）：`_limit_rational:217-220` 中 `abs(IFDRational(0,0))` 委托给 nan，`nan > 1` 为 False，于是调用 `IFDRational.limit_rational:293-294`，直接返回 `(0,0)`。
- 当前运行：`ledger_r2e_all_noop.jsonl:40` 与 `ledger_r2e_all_gold.jsonl:40`（reward 0/1，mismatched=`[TestFileTiffMetadata.test_exif_div_zero]`/`[]`，`RH2_OBS_IMPORT_PATH=/testbed/PIL/__init__.py`，uid 54322，gold patch sha `f5448ef9…` 与 validation bundle 一致）；reps（:2）、requal（:1）、env rerun2（:40）结果相同。M3 独立 runner 的 gold 日志也是 11 passed。
