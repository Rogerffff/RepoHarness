# coveragepy `016af5f6` 独立复核结论

2026-09-29 / 独立复核者（Claude，新会话，不继承作者上下文）。复核对象：[result.md](result.md)、`evidence/`、`rh2/experiments/category3_cloud_20260929/cov016/` 中的补丁、修订测试 v1 与修订题面 v1。

**顺序**：先读原件并实跑，封存[初判](review_initial.md)；再在一次性容器里自行核实；最后读作者材料逐条核对。初判写完后没有改动。

**证据层级**：本文所有评分都是**私有模拟**，不是 R2E 正式评分链。做法如下：

- 容器：`docker run --rm --network none`，身份 root，每次新开一次性容器；镜像 `namanjain12/coveragepy_final@sha256:71895ed4…5a39`（Image ID `sha256:e87a1ab6…`），Docker 29.3.1，存储后端 overlay2，实际使用 CTracer。
- 评分：`cp -r /r2e_tests /testbed/r2e_tests` 后运行 `bash run_tests.sh`，用 RH2 自带的 `parse_log_pytest` 与 `normalize_status_map`（`rh2/src/repoharness2/envpack/r2e_parsers.py`）解析，再按"期望键 ∪ 观测键"逐键比较。期望映射为评分包原件（15 键全 PASSED，含 `r2e-mr-001`）。
- 规模：共 62 次评分运行，每次墙钟 2–5 秒；另有 13 组行为探针与若干 CLI 对照。日志留在复核者本地 scratch，未入库。
- 未做：正式评分链、派生镜像、解题身份 UID 54321 下的开发条件、Codex 复核、新公开读者验收。

## 总判断：部分同意

**同意的部分：**

- 问题定位成立：题面原例在 base 不复现（P4）；原测试只用示例字面值（§4 第 2 步，S1）；`lines_only`、`ascii_only` 能拿 1（§4 第 4 步，S1）。
- "跳过"与"转换"两类合理做法都被接受。
- 修订测试 v1 的 7 个正负结果，我逐一复现，完全一致。
- R-f 修订题面在模板边界内，没有泄露隐藏测试细节。
- 证据层级基本如实交代。

**不同意"修法已明确"：** 修订测试 v1 仍放过一类"吞错"候选。这类候选在原测试和 v1 下都得 1，但保存下来的数据文件是空的，或者丢掉排在不可编码文件之后的所有文件。它是"已知相关错误候选"，按 §5 R-c 验收要求应为 0，所以 **v1 不能按现状落地**。修法很小：把追加段里两行 `exec` 的顺序对调，不可编码的文件名先执行。我已做私有验证，见第 3 节。转第2类的方向不变，但交接的修订测试需要改成 v2。

## 1. 逐条核对

| # | 作者主张 | 判断 | 依据 |
| --- | --- | --- | --- |
| 1 | **P4 已实跑**：题面原例照抄在 base 上不崩溃 | 同意 | 我在 base 上照抄运行原例（补 `import coverage`）：作为脚本运行时 `save()` 正常返回，`measured_files()` 只有脚本本身；用 `python -c` 运行时只告警 `No data was collected`。原因是示例里的 `exec(compile(...))` 在 `cov.start()` 之前执行，而测量区间内的 `exec("pass")` 文件名为 `<string>`。作者证据 `evidence/semantic_v1/*/e1_literal_example.out` 的结果与此相同 |
| 2 | 修订题面的示例在 base 上抛 `UnicodeEncodeError`，在 gold 下正常 | 同意（本人实跑）；作者证据缺件 | 我从 `revised_statement_v1.txt` 提取代码块，分别按脚本和 stdin 两种方式运行：base 抛 `UnicodeEncodeError … '\udcff' in position 7`，rc=1；gold 与 `convert` 正常，rc=0。`evidence/` 里没有 `revised_example_v1.py` 的运行输出，只有语义相近的 `e2_repro_both_modes` |
| 3 | **跳过和转换两类做法都被接受** | 同意 | 原测试与 v1 下，gold（跟踪决策处跳过）、`skip_write`（写入时跳过）、`convert`（转义后存储）都得 1。我另写三种合理实现也都得 1：`rv_skip_write`（`add_lines`、`add_arcs`、`touch_file`、`add_file_tracers` 都跳过）、`rv_convert`、`rv_collector_warn`（在 `Collector.flush_data` 过滤并发 coverage 告警）。隐藏测试不查 `\udcff.py` 的去向，也不查告警 |
| 4 | **`lines_only`、`ascii_only` 在原测试下得 1，属 S1** | 同意，并补充公开依据 | 两者在原测试下都得 1。`lines_only` 在 `branch=True` 时 `save()` 仍抛 `UnicodeEncodeError`（我的探针行模式正常、分支模式崩溃），属于同一核心要求的另一实例。`ascii_only` 丢掉 `café.py`、`中文.py`，`coverage run --source=. 中.py` 告警 No data。补充：base 公开测试 `tests/test_process.py::UnicodeFilePathsTest` 在 `ascii_only` 下 2 项失败，base 与 gold 都通过；CHANGES.rst 4.0.2 也写明 "Files or directories with non-ASCII characters are now handled properly"（issue 432）。这是"有文档、有公开测试的行为"的直接依据，作者原文只引了题面措辞 |
| 5 | §4 第 2 步（D1 严格版）命中 | 同意 | 隐藏测试就是 base `tests/test_oddball.py` 加上游 `test_unencodable_filename`，输入与题面示例同为 `exec(compile("pass", "\udcff.py", "exec"))`，默认行模式 |
| 6 | **修订测试 v1 的正负结果**：base 0，gold／`skip_write`／`convert` 1，`lines_only`／`ascii_only`／`catch_save` 0 | 数字同意；"已足够"不同意 | 7 个结果逐一复现（gold 与 `convert` 在 v1 下各重复 4 次，全为 1）。失败原因也一致：`lines_only` 为分支模式 `UnicodeEncodeError`；`ascii_only` 为 `assert 'café.py' in ['bug891b.py']`；`catch_save` 为测试随后调用 `get_data()` 时再次抛错。但 v1 仍放过第 2 节的 `wr_swallow_flush`、`wr_loop_abort`，以及次要的 `wr_latin1` |
| 7 | 键集不变，期望映射不用改 | 同意 | 追加的断言都在同一个测试函数里；我用原期望映射对 v1 评分，gold 为 15/15，没有 missing 或 unexpected |
| 8 | **R-f 修订符合边界** | 同意 | 逐行 diff：只改示例代码块，补 `import coverage`，把 `exec(compile("pass", "\udcff.py", "exec"))` 挪进 `start()`／`stop()` 之间，删掉不准确的 "Create a file…" 注释。这属于"改正对 base 行为的错误陈述"，已实跑证实（第 1、2 行）。没有出现 `bug891.py`、`measured_files()`、`branch=True`、`café.py`、`\udc80` 等隐藏测试细节。`\udcff.py` 原题面就有。未改的 "position 80" 是原题面已有的示意，不是本次新增的泄露。按题面一般读法，示例外实例（分支模式、其它代理字符、可编码的非 ASCII 名）已被题面覆盖，不需要写进题面。R-f 验收还差新公开读者与 Codex 复核，作者已列为交接项 |
| 9 | 引用用户口径"原例不复现应中性修正（参照 mypy15184）" | 同意，有出处 | `task120_status_20260929/classification_change_v2.md:17`："继续让模型自行发现原例失配不是对该缺陷的处理" |
| 10 | **证据层级如实** | 基本同意，有三处小问题 | 正文写明"私有模拟，不是 R2E 正式评分链"，并列出未验 UID 54321 与派生镜像，这是诚实的。小问题：(a) 各 `rc.json` 与三份 `summary.json` 的值全为 0，包括 base 目标键 FAILED 的运行。这些是管道末端命令的退出码，不代表测试结果，单独读会误导。(b) 修订题面 sha256 写成 `e654fab9…e1e1`，实际是 `e654fab9…d1e1`（引用笔误）。(c) 第 2 行所说的修订示例运行没有归档输出 |
| 11 | 公开测试（175 项）全过 | 同意 | 我用同一选集、`-o addopts=''` 重跑：base、gold、`convert`、`skip_write`、`lines_only`、`ascii_only`、`catch_save` 都是 175 passed / 1 skipped。`wr_swallow_flush` 也全过，所以这组公开测试挡不住吞错类候选 |
| 12 | 公开读者 A3–A5（`source=` 未执行文件发现路径等）超出题面范围，不作要求 | 同意不作要求；建议补记 G1／T3 | 实跑发现 gold 本身在 A3 路径上仍然崩溃：`--source` 目录里有一个未执行、文件名含 `0xff` 字节的 `.py`，`coverage run` 经 `_post_save_work → touch_file → _file_id` 抛 `UnicodeEncodeError`，rc=1。作者的 `skip_write` 也一样。`convert` 与 `rv_skip_write`（含 `touch_file`）不崩。这是罕见路径，按 §4 第 4 步记 T3，另记 G1（gold 不完整）。不宜补断言，否则需要按 D4 另找正对照 |
| 13 | 用途：原版只作问题定位，能力比较与训练在修订落地前为 no | 同意 | 与第 9 行的用户口径，以及 S1 未关闭的状态一致 |

## 2. 反例与新问题

### 2.1 吞错类候选在原测试和 v1 下都得 1（主要问题）

`wr_swallow_flush`：在 `Collector.flush_data` 外层吞掉 `UnicodeEncodeError`。它属于 §4 退化方向里的"吞掉错误、抑制症状"。公开读者稿 R5 已预警过这一风险；作者的 `catch_save` 吞在 `save()` 这一层，会被测试随后的 `get_data()` 挡住，但往下一层就挡不住。

```diff
--- a/coverage/collector.py
+++ b/coverage/collector.py
@@ -419,10 +419,13 @@ class Collector(object):
-        if self.branch:
-            self.covdata.add_arcs(self.mapped_file_dict(self.data))
-        else:
-            self.covdata.add_lines(self.mapped_file_dict(self.data))
+        try:
+            if self.branch:
+                self.covdata.add_arcs(self.mapped_file_dict(self.data))
+            else:
+                self.covdata.add_lines(self.mapped_file_dict(self.data))
+        except UnicodeEncodeError:
+            pass
```

| 检查 | 结果 |
| --- | --- |
| 原测试 | 1 |
| 修订测试 v1 | 1（4 次，均为 1） |
| 隐藏测试同形场景：内存里的 `measured_files()` | 含 `bug891.py`，所以测试通过 |
| 同一场景：用新的 `CoverageData().read()` 读回数据文件 | **空**。`add_lines` 的事务被回滚，保存下来的数据里一个文件都没有 |
| 不可编码文件先执行、再 `import` 另一个模块 | 另一个模块在内存和磁盘里都丢失 |
| CLI：`coverage run main.py`（main.py 先 exec `\udcff.py`，再 `import helper`），行模式和 `--branch` 都试 | `run` 的 rc=0，随后 `coverage report` 输出 **"No data to report."**；gold 与 `skip_write` 正常报告 `main.py`、`helper.py` |

**违反的公开要求**：题面只允许跳过"不能编码的那些文件"。`Coverage.save()` 的公开文档是 "Save the collected coverage data to the data file"。原隐藏测试断言 `bug891.py` 仍被记录，本意正是其它文件的数据不能丢。这是主路径上的违例，按 §4 第 4 步（审查中构造的候选）判 S1。

`wr_loop_abort` 是同类变体：在 `CoverageData.add_lines`／`add_arcs` 的连接块内部，用 try/except 包住逐文件循环。它不回滚，但第一个不可编码文件之后的文件全部丢失。

- 原测试、v1、"v1 加磁盘读回"三种测试下都得 1。
- 只有让不可编码文件先于可编码文件执行，才能挡住它。

### 2.2 次要反例：按 Latin-1 判断可编码性

`wr_latin1`：在 `check_include_omit_etc` 里，文件名不能按 `latin-1` 编码就跳过。

- 原测试与 v1 都得 1，因为 v1 用的 `é` 属于 Latin-1。
- 实际后果：`中文.py` 不被测量；`coverage run --source=. 中.py` 告警 No data。公开的 `UnicodeFilePathsTest` 只用 `â`，同样挡不住它。
- 这种写法不太自然，记为边缘缺口。

### 2.3 其它观察

- **转换类实现与报告**：`convert` 把 `\udcff.py` 存成转义名。之后 `coverage report` 默认会报 "No source for code … Aborting report output, consider using -i"。这与 base 对其它缺源码的伪文件名的既有行为一致，题面也允许"内部处理"，所以不是缺陷。但以后的修订**不要断言报告成功**，否则会误拒题面允许的转换做法（P5 风险）。
- **G1**：gold 在 `--source` 未执行文件路径上仍然崩溃，见第 1 节第 12 行。

## 3. 已做私有验证的修法

下表都是私有模拟：原期望映射，同一 `run_tests.sh`，同一解析器。测试变体只放在复核者 scratch 里，没有写入仓库的修订文件。

| 测试变体 | 改动（相对作者 v1） | base | gold | `skip_write` | `convert` | 其它合理实现 | `lines_only` | `ascii_only` | `wr_swallow_flush` | `wr_loop_abort` | `wr_latin1` | `wr_hardcode`（只特判 `\udcff`） |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 作者 v1 | — | 0 | 1 | 1 | 1 | 1（`rv_skip_write`、`rv_convert`、`rv_collector_warn`） | 0 | 0 | **1** | **1** | **1** | 0 |
| **v1swap（建议的最小修法）** | 对调追加段两行 `exec`：`\udc80\udc81_other.py` 先执行，`café.py` 后执行 | 0 | 1 | 1 | 1 | 1（`rv_collector_warn`） | 未跑 | 未跑 | **0** | **0** | 未跑 | 未跑 |
| v1plus（加固版） | 对调顺序；可编码名改为 `caf\xe9_中.py`；另用 `coverage.CoverageData().read()` 读回数据文件，断言 `bug891b.py` 与该名都在 | 0 | 1 | 1 | 1 | 1（`rv_skip_write`、`rv_convert`、`rv_collector_warn`） | 0 | 0 | 0 | 0 | 0 | 0 |

说明：

- v1swap 下 `lines_only`、`ascii_only`、`wr_hardcode` 未跑。对调顺序不改变分支模式、`café.py` 和 `\udc80` 这三处检查本身，预计仍为 0，但这只是推断。
- 两个变体都不断言 `\udcff` 类文件是否被记录，也不断言它以什么形式记录，因此跳过与转换两类做法仍都被接受。
- 依据仍是题面的一般表述，加上原测试自身的 `bug891.py` 断言，属于 R-c 的同一窄问题："跳过不可编码文件后，其它文件照常保存"。

## 4. 阻断项与建议

**阻断项（1 项）**

- **B1 修订测试 v1 不能按现状落地。**
  - 问题：吞错类候选（`wr_swallow_flush`、`wr_loop_abort`）在 v1 下得 1。它们在主路径上丢失保存数据，属于 S1，而 §5 R-c 验收要求"已知相关的错误候选仍为 0"。
  - 最小修法：对调追加段两行 `exec` 的顺序（v1swap，已做私有验证）。
  - 落地前：由第2类按正式评分链复验。noop 为 0；gold、`skip_write`、`convert` 为 1；`lines_only`、`ascii_only`、`catch_save`、`wr_swallow_flush`、`wr_loop_abort` 为 0。
  - 另外保存父版本 v1、理由和触发反例。

**非阻断建议**

1. 把可编码名换成含非 Latin-1 字符的名字，例如 `caf\xe9_中.py`，挡住 `wr_latin1` 这类判断。成本极低。
2. 可选：加一次数据文件读回。它能挡住"顺序有利但事务回滚"的变体；我验证过，这不会误拒 `convert` 和 `skip_write`。
3. 在题卡补记 G1／T3：gold 在 `--source` 未执行文件路径上崩溃。不补断言。
4. 证据整理：
   - `summary.json`／`rc.json` 改记真实判定（`match` 字段），或注明它们只是退出码；
   - 归档 `revised_example_v1.py` 的 base／gold 输出；
   - 把修订题面 sha256 缩写改为 `e654fab9…d1e1`。
5. `ascii_only` 判 S1 的依据补上公开测试 `UnicodeFilePathsTest`（在该候选下 2 项失败）和 CHANGES 4.0.2（issue 432）。
6. 以后若再补断言，不要要求 `report()` 成功，也不要断言 `\udcff` 类文件被跳过或以某种形式保留。
7. `semantic_spec*.json` 含本机绝对路径。它们在未跟踪的实验目录里，保持不入库即可。

**尚待完成（作者已列，非本次新增）**：

- 正式评分链与派生镜像；
- UID 54321 下的开发条件；
- 新公开读者验收修订题面；
- Codex 复核。

## 5. 未查

- R2E 正式评分链、派生镜像构建；
- 非 root 解题身份；
- PyTracer 路径（镜像实际使用 CTracer）；
- Python 2 兼容性；
- 插件文件追踪器（`add_file_tracers`）与动态上下文名（公开读者 A5）；
- v1swap 下 `lines_only`、`ascii_only`、`wr_latin1`、`wr_hardcode` 的实跑结果。

## v2 聚焦复核（2026-09-29）

**对象**：
- 修订测试 `hidden_test_1_revised_v2.py`（sha256 `ccdd7d89…`）；
- 主审生成的 7 个复核候选补丁；
- `evidence/revised_v2/grades.jsonl`、`evidence/examples_v1/`、`evidence/g1_v1/`；
- 重写后的 `result.md`（10:02 版）。

**方式**：同前，一次性容器、断网、root，私有模拟，没有跑正式评分。本节新增评分运行共 34 次：
- v2 × 14 个候选；
- gold、`convert`、`rv_collector_warn` 在 v2 下各重复 2 次（连同首轮各 3 次，全为 1）；
- 2 个边缘候选 × v2；
- 可选加固变体 × 12 个候选。

另做 7 组补丁等价检查和 3 组边缘探针。

**总判断：同意 v2 作为修订草案交第2类，无阻断项。** v2 如实实现了 B1 的修法，也吸收了建议 1、2。我没有发现新的误拒；与 v1 相比，没有候选从 0 变为 1。grades.jsonl 与 result.md 的表格 42 格全部一致。result.md 对复核意见的处理基本准确，只剩几处措辞和引用瑕疵（见第 4 点）。v2 仍需正式评分链、新公开读者验收与 Codex 复核。

### 1. v2 是否如实实现修法，有无新的误拒或放过

**文件对照**：
- v2 与复核者私测的 `reviewer_probe_v1plus.py` 只差第 579–580 行注释；
- 相对 v1 有三处改动：对调两行 `exec`，让 `\udc80\udc81_other.py` 先执行（B1）；可编码名改为 `caf\xe9_中.py`（建议 1）；用 `coverage.CoverageData().read()` 读回数据文件并断言（建议 2）；
- 仍在同一个测试函数内，键集不变。

**实跑**：我用 v2 原文件对 14 个候选各跑一次，结果与 `grades.jsonl` 的 `h2_rev2` 逐一相同。

- **得 1（6 个）**：gold、`skip_write`、`convert`、`rv_skip_write`、`rv_convert`、`rv_collector_warn`。
- **得 0（8 个），失败位置都在预期断言上**：
  - base、`catch_save`：原测试部分的 `\udcff` `UnicodeEncodeError`；
  - `lines_only`、`wr_hardcode`：分支模式下 `\udc80\udc81` 的 `UnicodeEncodeError`；
  - `ascii_only`、`wr_latin1`、`wr_swallow_flush`、`wr_loop_abort`：`assert 'café_中.py' in ['bug891b.py']`。

**误拒**：没有发现新的误拒。
- 得 1 的合理实现覆盖跳过类 4 个（gold、`skip_write`、`rv_skip_write`、`rv_collector_warn`）和转换类 2 个（`convert`、`rv_convert`）。
- v2 仍然不断言不可编码文件是否被记录、以何种形式记录，也不断言报告成功。
- 读回断言只检查 `bug891b.py` 和 `café_中.py` 两个可编码名。
- gold、`convert`、`rv_collector_warn` 各 3 次全为 1。

**放过**：
- grades.jsonl 中没有候选从 v1 的 0 变为 v2 的 1，合理实现也没有从 1 变为 0。
- 我另造了 2 个边缘错误候选，它们在 v2 下都得 1。这两个缺口在原测试和 v1 下同样存在，不是 v2 引入的：
  - `wr_escape_range`：只把 U+DC80–U+DCFF 当作不可编码。探针中 `\ud800.py`、`\udc00.py` 仍然崩溃。这类孤立代理只能由人为的 `compile()` 名得到，从文件系统按 surrogateescape 解码不会产生；
  - `wr_basename_only`：只检查 basename。探针中 `/tmp/\udcff_dir/x.py`（目录名不可编码）仍然崩溃。

  两者都属于边缘输入，建议记 T3，不阻断。
- **可选加固（已私测）**：把 `"\udc80\udc81_other.py"` 改为 `"\udc80\udc81_dir/other.py"`。结果：gold、`skip_write`、`convert`、三个 `rv_*` 为 1；base、`lines_only`、`wr_swallow_flush`、`wr_loop_abort`、`wr_basename_only` 为 0；`wr_escape_range` 仍为 1。按 §5"不追着候选改分"，这不是必需项。

**补充**：在 v2 的 14 个候选里，没有一个是被读回断言判负的。两个吞错候选都因为顺序对调，先在内存断言 `café_中.py` 处失败。读回断言的拦截作用只在 v1 顺序下演示过：本文第 3 节的 v1disk 中，`wr_swallow_flush` 失败于 `assert 'bug891b.py' in []`。在 v2 里它是加固项。

### 2. 生成的补丁是否与复核构造等价

**等价。**
- `reviewer_cands/` 下 8 个文件（含 `_lib.py`）与复核者原件的 sha256 逐一相同。
- 7 个候选分别在 base 上执行两种方式：一是跑我的编辑脚本，二是 `git apply` 主审生成的 `.patch`。两种方式改动的文件相同，改后文件的 sha256 也相同。
- 7 个候选是 `rv_collector_warn`、`rv_convert`、`rv_skip_write`、`wr_hardcode`、`wr_latin1`、`wr_loop_abort`、`wr_swallow_flush`。

### 3. grades.jsonl 与 result.md 表格是否一致

**一致。**
- result.md §2（2）表的 14 行 × 3 列共 42 格，与 `grades.jsonl` 全部相同。
- 我的独立结果也与之吻合：原测试、v1 两列此前已逐项跑过（相同候选全部相同）；v2 列本节重跑，14 格全部相同。
- 日志也证实各列用的测试版本正确：`ascii_only` 的 `h1_rev1.out` 失败于 `'café.py'`，`h2_rev2.out` 失败于 `'café_中.py'`。
- 说明：`grade_r2e.py` 的 `reward` 用的是 `prime_calculate_reward`，即上游口径。RH2 模块注明它只用于对拍，生产判定用 `scoring.expected_map_matches`（并集口径）。我逐条核查了 42 条记录，都是 `n_parsed = n_expected = 15`、`unexpected` 为空，两种口径结论相同。建议在 result.md 注明这一点。

### 4. result.md 对复核意见的处理

| 复核意见 | result.md 的处理 | 判断 |
| --- | --- | --- |
| B1 对调 `exec` 顺序，正式评分复验，保留父版本与触发反例 | 已改为 v2；版本链 `72b69833…` → v1 `c7f272d5…` → v2 `ccdd7d89…`；交接单列出正式评分的预期值 | 准确 |
| 建议 1 非 Latin-1 字符 | v2 已用 `café_中.py`，`wr_latin1` 为 0 | 准确 |
| 建议 2 数据文件读回 | 已加入 | 已实施。措辞需修正：result.md 写"v1 → v2 的改动来自独立复核 B1"，又说读回"挡住只保留内存、磁盘丢数据的吞错实现"。实际上 B1 只要求对调顺序，另两项来自建议 1、2；在 v2 中挡住两个吞错候选的是顺序对调，读回不是任何候选的决定性断言 |
| 建议 3 G1／T3 | 已补记；`evidence/g1_v1/` 显示 base、gold、`skip_write` 在 run 时崩溃（rc=1），`convert`、`rv_skip_write` 不崩溃 | 准确，与我的探针一致。附注：`g1_v1/*.out` 中的 `[report rc=…]` 是 `tail` 的退出码；`convert` 的报告实际以 "No source for code … Aborting" 中止，却显示 rc=0 |
| 建议 4 证据整理 | 已写明 `rc.json`／`summary.json` 是退出码，得分以 `grades.jsonl` 为准；`examples_v1/` 已归档（原例在 base、gold 下都正常保存，修订示例 base rc=1、gold rc=0）；sha256 已更正为 `e654fab9…d1e1`（我重算相符） | 准确 |
| 建议 5 `ascii_only` 的公开依据 | 已补 `UnicodeFilePathsTest` 与 CHANGES 4.0.2 | 准确 |
| 建议 6 不断言报告成功或处置形式 | 已写入 §4 | 准确 |
| 建议 7 本机绝对路径 | 没有提及。`grade_r2e.py` 第 3 行与 4 份 `semantic_spec*.json` 含 `/home/user/RepoHarness/...`，现已随 cov016 目录提交 | 未处理，非阻断：建议改为相对路径 |

**其它小瑕疵（非阻断）**：
- 首段说"6 个合理实现（跳过类与转换类各三个）"，实际是跳过类 4 个、转换类 2 个。
- 首段说"8 个错误候选都得 0"，这 8 个里含 noop（base），应写"noop 与 7 个错误候选都得 0"。
- 开头"主审和独立复核都还没做"已过时；§5"v2 本身还没有经过复核"应改为指向本节。
- §2 写"run_tests.sh（sha256 `0ed7b9a4…`）"，这是带结尾换行的本地副本的值；评分包字段为 `8285765f…`，两者只差结尾换行。

### 结论

- **阻断项：无。**
- **非阻断建议**：
  - 按上表修正措辞与引用；
  - 把 `wr_escape_range`、`wr_basename_only` 记为 T3；目录名实例的加固可选；
  - 去掉提交文件中的本机绝对路径。
- **未查**：
  - 正式评分链与派生镜像；
  - UID 54321 下的开发条件；
  - 新公开读者对修订题面的验收；
  - v2 在 PyTracer 下的行为。
