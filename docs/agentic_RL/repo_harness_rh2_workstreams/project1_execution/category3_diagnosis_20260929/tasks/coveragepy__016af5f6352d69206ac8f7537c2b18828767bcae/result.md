# R2E coveragepy__016af5f6：第3类质量调查结果（v2，按独立复核修订）

2026-09-29 / Claude（云端，第3类负责人）。原分类：第3类“题目质量调查未完成”。R2E 线的公开读者稿已经保存（[public_read.md](../../../r2e_lifecycle_20260929/results/coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae/public_read.md)），但文中提到的 `commands.json` 缺失，主审和独立复核都还没做。

**结论：问题和修法已明确，建议转第2类。** 修订测试已按独立复核的阻断项 B1 更新到 v2。

- **P4，已实跑确认**：题面原例照抄在 base 上不崩溃。
- **S1**：原测试下，**6 个错误候选得 1**：
  - `lines_only`：分支模式下仍然崩溃；
  - `ascii_only`：丢掉可编码的非 ASCII 文件名；
  - `wr_swallow_flush`、`wr_loop_abort`：吞掉错误，保存下来的数据丢失；
  - `wr_latin1`：按 Latin-1 判断，丢掉 `中` 等字符的文件；
  - `wr_hardcode`：只特判示例字符 `\udcff`。
- **修法**：
  - R-f 修正题面示例；
  - R-c v2 在原测试函数内补四类检查：分支模式、另一种不可编码名、执行顺序上排在它之后的可编码非 Latin-1 名、数据文件读回。

  私有评分下，6 个合理实现（跳过类与转换类各三个）都得 1，8 个错误候选都得 0。gold 仍作正对照。

公开读者担心的“隐藏测试只接受跳过或转换中的一种”已消除：两类做法在原测试、v1、v2 下都能通过。

## 1．公开要求与既有证据

题面要求：文件名不能按 UTF-8 编码时，`Coverage.save()` 不应抛 `UnicodeEncodeError`，“either by skipping them or handling the encoding error internally”。

环境记录：09-24 T0-1 修订 `r2e-mr-001` 把一个因来源宿主机缺 mock 而误记为 FAILED 的键改为 PASSED，状态为 `qualified_with_revision`，gold 15/15。gold 在 `inorout.check_include_omit_etc` 中返回“不跟踪”，理由是 `non-encodable filename`。

## 2．私有实测

- 源镜像：`namanjain12/coveragepy_final@sha256:71895ed4…5a39`，与冻结摘要一致。
- 方式：root、断网、一次性容器。隐藏测试取自镜像 `/r2e_tests`（`test_1.py` 的 sha256 为 `72b69833…`，与评分包一致）。
- **私有评分**：复制到 `/testbed/r2e_tests`，运行评分包里的 `run_tests.sh`（sha256 `0ed7b9a4…`），按 RH2 移植的上游解析器（`parse_log_pytest`＋`prime_calculate_reward`，[`grade_r2e.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/cov016/grade_r2e.py)），逐键对照评分包的期望映射（15 键，含 `r2e-mr-001`）。这是按同一命令和期望映射做的**私有模拟**，不是 R2E 正式评分链。
- 注意：各 `rc.json`、`summary.json` 里的值是容器内管道末端命令的退出码，**不代表测试结果**；得分以 `grades.jsonl` 为准。

**（1）示例复现**（`evidence/examples_v1/`）：
- 题面原例照抄：base 与 gold 都正常保存，只测到脚本本身；
- 修订后的示例：base 抛 `UnicodeEncodeError`（rc=1），gold 正常保存。

**（2）候选与得分**（`evidence/revised_v2/grades.jsonl`）：

| 候选 | 来源 | 做法 | 原测试 | v1 | **v2** |
| --- | --- | --- | --- | --- | --- |
| base | — | — | 0 | 0 | 0 |
| gold | 参考修复 | 在跟踪决策处跳过 | 1 | 1 | **1** |
| `skip_write` | 主审 | 写数据时跳过 | 1 | 1 | **1** |
| `convert` | 主审 | 转义后存储 | 1 | 1 | **1** |
| `rv_skip_write` | 复核 | 写数据时跳过，含 `touch_file` | 1 | 1 | **1** |
| `rv_convert` | 复核 | 转义后存储 | 1 | 1 | **1** |
| `rv_collector_warn` | 复核 | 在 collector 层跳过并告警 | 1 | 1 | **1** |
| `lines_only` | 主审 | 只在 `add_lines` 跳过 | **1** | 0 | 0（分支模式 `UnicodeEncodeError`） |
| `ascii_only` | 主审 | 跳过所有非 ASCII 名 | **1** | 0 | 0（`café_中.py` 不在数据中） |
| `catch_save` | 主审 | 在 `save()` 外层吞异常 | 0 | 0 | 0 |
| `wr_swallow_flush` | 复核 | 在 `flush_data` 外层吞异常，事务回滚，数据全丢 | **1** | **1** | 0 |
| `wr_loop_abort` | 复核 | 逐文件循环整体包进 try，不可编码名之后的文件全丢 | **1** | **1** | 0 |
| `wr_latin1` | 复核 | 按 Latin-1 判断可编码性 | **1** | **1** | 0 |
| `wr_hardcode` | 复核 | 只特判 `\udcff` | **1** | 0 | 0 |

复核候选由 `reviewer_cands/*.py` 编辑脚本生成补丁，脚本来自复核者，补丁由主审生成。

**（3）公开测试**：公开测试为 `tests/test_data.py`、`test_api.py`、`test_oddball.py::ExecTest`、`test_files.py`，用 `-o addopts=''` 运行（175 项）。主审的 7 个版本都是 175 passed / 1 skipped。复核补测：`wr_swallow_flush` 也全过，所以这组公开测试挡不住吞错类候选。

**（4）隐藏测试原文的覆盖**：`test_unencodable_filename` 只断言两点：`save()` 不崩溃；执行 exec 的 `bug891.py` 仍被记录。它**不检查** `\udcff.py` 是否留在数据里，所以跳过和转换两类实现都被接受。

## 3．判定（v1 §3–§4）

- **P4（已实跑确认）**：示例的 `exec(compile(..., "\udcff.py", ...))` 在 `cov.start()` 之前执行；测量期间只有文件名为 `<string>` 的代码，这类代码不被跟踪，所以照抄不会崩溃。这是题面对 base 行为的错误陈述。按用户对普通探针的口径（参照 mypy15184 已转第2类的处理），应中性修正，不能留给模型自己发现。
- **§4 第 2 步（D1 严格版）**：原断言只用了题面示例的文件名 `\udcff.py`，属于示例拟合。`wr_hardcode` 只特判这个字符就得 1，印证了这一点。
- **§4 第 3、4 步（S1）**：原测试下以下错误候选得 1。
  - `lines_only`：分支覆盖模式（公开的常用模式 `--branch`）下 `save()` 仍崩溃；
  - `ascii_only`、`wr_latin1`：丢掉可编码文件名的测量数据。题面只允许跳过“无法编码”的文件。另有两条公开依据（复核核对）：
    - 公开测试 `tests/test_process.py::UnicodeFilePathsTest` 在 `ascii_only` 下有 2 项失败，base 与 gold 都通过。它不在 §2（3）的选集里，只用了 `â`，所以挡不住 `wr_latin1`；
    - CHANGES 4.0.2 写明 “Files or directories with non-ASCII characters are now handled properly”（issue 432）；
  - `wr_swallow_flush`、`wr_loop_abort`：属于“吞掉错误、抑制症状”的退化方向。
    - `wr_swallow_flush` 在命令行下 `coverage run` 返回 0，随后 `coverage report` 输出 “No data to report.”；
    - `wr_loop_abort` 会丢掉执行顺序上排在不可编码文件之后的全部文件。

    这违反 `Coverage.save()` 的公开文档 “Save the collected coverage data to the data file”，也违反原测试 `bug891.py` 断言的本意。
- **误拒风险（公开读者 A1）已消除**：跳过与转换两类做法，共 6 个实现，都通过。
- **G1／T3，不补断言**：
  - 现象：`--source` 目录里有一个未执行、文件名含 `0xff` 字节的 `.py` 时，`coverage run` 在 gold 下仍经 `_post_save_work → touch_file` 抛 `UnicodeEncodeError`（rc=1）。
  - 版本对照：base、`skip_write` 相同；`convert`、`rv_skip_write` 不崩溃（`evidence/g1_v1/`）。
  - 结论：gold 没有覆盖这条罕见路径，但这不是回归。补断言需要按 D4 另找正对照，不值得。

## 4．修法（交第2类，走 R2E 已有的材料修订机制）

**R-c：`hidden_test_text_replace`，当前版本 v2**

- 修订后文件为 [`hidden_test_1_revised_v2.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/cov016/hidden_test_1_revised_v2.py)，sha256 `ccdd7d89…`。
- 版本链：原文件 `72b69833…` → v1 `c7f272d5…` → v2。v1 保留作历史。
- 在原 `test_unencodable_filename` 末尾追加一段：
  - 以 `branch=True` 运行一个模块。它先 exec `\udc80\udc81_other.py`，再 exec `caf\xe9_中.py`，也就是先不可编码名、后可编码的非 Latin-1 名；
  - 保存后断言：内存中的 `measured_files()` 含模块本身和 `café_中.py`；
  - 再用新的 `coverage.CoverageData().read()` 读回数据文件，断言两者都在。
- v1 → v2 的改动来自独立复核 B1：
  - 对调两行 exec 的顺序，挡住 `wr_loop_abort`；
  - 可编码名加入非 Latin-1 字符，挡住 `wr_latin1`；
  - 加入数据文件读回，挡住只保留内存、磁盘丢数据的吞错实现。

  v2 与复核者私测的 v1plus 只差一行注释。
- 不断言 `\udcff` 类文件是否被记录、以何种形式记录，所以跳过和转换两类做法都被接受。**以后的修订也不应断言 `coverage report` 成功**：转换做法之后报告会提示缺源码，这是 base 的既有行为，题面允许这类“内部处理”（复核 §2.3）。
- 键集不变，期望映射不用改。

**R-f：`statement_text_replace`**

- 修订题面为 [`revised_statement_v1.txt`](../../../../../../../rh2/experiments/category3_cloud_20260929/cov016/revised_statement_v1.txt)。父版本 sha256 `67c1899b…d410`，与 public bundle 一致；修订后 `e654fab9…d1e1`（v1 页误写为 `…e1e1`，已更正）。
- 改动只在示例代码块：补 `import coverage`，把 exec 移到 `start()` 与 `stop()` 之间，删去“Create a file…”这句不准确的注释。
- 已实跑确认，并归档到 `evidence/examples_v1/`：修订后的示例在 base 上抛 `UnicodeEncodeError`，在 gold 下正常保存。
- 新句没有泄露隐藏测试细节：没有 `bug891.py`、`measured_files`、`branch`、`café`、`\udc80`（复核逐行核对）。修正后示例崩溃位置随工作目录变化，题面 Error Message 中的“position 80”未改动，它只是示意。

**交接给第2类：**

1. 在 R2E 材料修订单中登记上述两项，并构建派生镜像。
2. **正式评分**：
   - noop 为 0；
   - gold、`skip_write`、`convert` 为 1，复核的 `rv_*` 建议至少跑一个；
   - `lines_only`、`ascii_only`、`catch_save`、`wr_swallow_flush`、`wr_loop_abort` 为 0，`wr_latin1`、`wr_hardcode` 建议一起跑。
3. 由一位新公开读者验收修订题面。
4. Codex 复核。

## 5．独立复核

复核者先封存初判 [review_initial.md](review_initial.md)，结论见 [review.md](review.md)。

- **总判断：部分同意**。以下各项复核都独立复现：P4、两类做法都被接受、`lines_only` 与 `ascii_only` 属 S1、v1 的 7 个结果、R-f 在边界内、证据层级如实。
- **阻断项 B1**：v1 放过吞错类候选。**已处理**：改为 v2，14 个候选重新做私有评分，结果与复核者的 v1plus 一致。
- **已处理的非阻断项**：
  - `wr_latin1`：v2 已挡住；
  - `ascii_only` 判 S1 的公开依据：已补上 `UnicodeFilePathsTest` 和 CHANGES 4.0.2；
  - G1：已补记并复验；
  - 修订题面 sha256 笔误：已更正；
  - 修订示例的运行输出：已归档；
  - `rc.json` 的含义：已写明。
- v2 本身还没有经过复核。v2 只按复核者提出的修法实现，所以交第2类时由 Codex 复核一并确认。

## 6．当前用途与未做

- **用途**：原版只作问题定位；能力比较和训练在修订落地并验收前为 no。
- **未做**：
  - R2E 正式评分链与派生镜像没有在云端重建，本页评分都是私有模拟；
  - 真实解题身份（UID 54321）的开发条件（R2E devcheck）未验；
  - 公开读者稿缺失的 `commands.json` 未重建。其中已给出全文的复现命令和公开测试命令，已按等价方式在 root 私有容器中执行。
- **已登记的非本题问题**（公开读者 A3–A5）：`source=` 未执行文件发现路径（即上文 G1）、直接调用 `CoverageData` API、不可编码的上下文名。这些都超出题面范围，不作要求。
- **证据**：[evidence/](evidence/)
  - `semantic_v1/`、`public_v2/`、`revised_v1/`：v1 阶段；
  - `revised_v2/`：14 个候选 × 原测试、v1、v2，逐键结果见 `grades.jsonl`；
  - `examples_v1/`：题面原例与修订示例；
  - `g1_v1/`：G1 复验；
  - `evidence_manifest.json`。

  补丁与脚本在 `rh2/experiments/category3_cloud_20260929/cov016/`，其中复核候选的编辑脚本在 `reviewer_cands/`。
