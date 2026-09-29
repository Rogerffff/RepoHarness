# coveragepy `016af5f6` 独立复核：初判（读作者材料前封存）

2026-09-29 / 独立复核者（Claude，新会话，不继承作者上下文）。

**封存声明**：本文写于阅读作者 `result.md`、`evidence/`、`rh2/experiments/category3_cloud_20260929/cov016/` 与公开读者稿之前，写完后不再修改。依据只有下列原件和镜像只读运行：

- 题面与公开提示：`s2_r2e/ingest/public_bundles_v0.jsonl`（`problem_statement_sha256 = sha256:67c1899b…`）。
- gold：`validation_bundles_v0.jsonl`（`golden_patch_sha256 = sha256:fa506eaa…`），只改 `coverage/inorout.py` 的 `InOrOut.check_include_omit_etc`：`filename.encode("utf8")` 抛 `UnicodeEncodeError` 时返回 `"non-encodable filename"`，即**该文件不被追踪**。
- 期望映射与 `run_tests.sh`：`grading_bundles_r2e_v0.jsonl`（`expected_output_json_sha256 = sha256:f353157e…`，已含 `r2e-mr-001`：`MockingProtectionTest.test_os_path_exists` 由 FAILED 改为 PASSED）。15 个键全部为 PASSED。`run_tests.sh` 为 `PYTHONWARNINGS='ignore::UserWarning,ignore::SyntaxWarning' .venv/bin/python -W ignore -m pytest -rA r2e_tests`。
- 镜像 `namanjain12/coveragepy_final@sha256:71895ed4…`（Image ID `sha256:e87a1ab6…`），coverage 5.0.2a1，Python 3.7.9，`sys.getfilesystemencoding() == 'utf-8'`；`/r2e_tests/test_1.py` 的 sha256 为 `72b69833…`，与评分包一致。
- 隐藏测试 `test_1.py` 与 base 公开的 `tests/test_oddball.py` 逐行对比：只多了 `import os.path` 和 `ExecTest.test_unencodable_filename` 一个测试；其余 14 个键是现成公开测试（回归）。

## (a) 题面核心要求

标题：非 UTF-8 可编码的文件名会让 coverage 以 `UnicodeEncodeError` 崩溃。期望行为：遇到**不能编码为 UTF-8 的文件名**时，coverage.py 要平稳处理，"either by skipping them or handling the encoding error internally without crashing"。

按题面一般表述理解，核心要求是：

1. 追踪期间遇到任意一个不可编码文件名，`save()`（以及取数据）不崩溃；
2. 平稳处理指的是正常的覆盖率记录仍然有效：同一次运行中其它文件的数据仍然被记录、保存。这一条题面没有逐字写，但"graceful"和"without crashing"的一般读法包含它，而且不丢其它文件的数据是 coverage 的基本公开行为；
3. 题面明确允许两种做法：**跳过**该文件，或在内部**处理/转换**编码错误。测试不能只接受其中一种。

题面没有限定只在行覆盖模式下生效，也没有限定只针对 `\udcff` 这一个字符。

## (b) 隐藏测试断言了什么、没断言什么

目标键 `ExecTest.test_unencodable_filename`：

```python
self.make_file("bug891.py", r"""exec(compile("pass", "\udcff.py", "exec"))""")
cov = coverage.Coverage()
self.start_import_stop(cov, "bug891")
cov.save()                                  # 断言 1：不抛异常
files = [os.path.basename(f) for f in cov.get_data().measured_files()]
assert "bug891.py" in files                 # 断言 2：发起 exec 的文件仍被记录
```

**断言了**：默认行覆盖模式下，示例中的同一个输入（`\udcff.py`，经 `exec(compile(...))` 触发）不会让 `save()` 与随后的 `get_data()` 崩溃；`bug891.py` 出现在 `measured_files()` 里。

**没断言**（按源码阅读，待第二步实跑核实）：

- `\udcff.py` 本身被跳过还是被转换后记录：不查。因此跳过与转换两种做法都应能通过，这一点是好的。
- `measured_files()` 在 base 上直接返回内存里的 `set(self._file_map)`（`coverage/sqldata.py`），**不读磁盘上的 `.coverage` 文件**。数据是否真的写进 SQLite、换一个进程能否读回，测试不查。
- `bug891.py` 的行数据（如 `lines()` 是否为 `[1]`）不查。
- 分支模式（`branch=True`，走 `CoverageData.add_arcs`）不查；base 上行模式走 `add_lines`，两条路径都在 `_file_id(add=True)` 处插入文件名。
- 示例以外的不可编码字符（如 `\udc80`、目录名中的代理字符）不查。
- 合法的非 ASCII、可 UTF-8 编码的文件名仍被正常测量：不查。这是有公开依据的已有行为：base 公开测试 `tests/test_process.py::UnicodeFilePathsTest`（`h\xe2t.py`、`\xe2/accented.py`），CHANGES.rst 4.0.2 "Files or directories with non-ASCII characters are now handled properly"（issue 432）。
- 失败文件在迭代顺序中排在其它文件前面的情形：不查。测试里 `bug891.py` 总是先被追踪、先写入。
- 另外 14 个键是 `test_oddball.py` 的原有测试，只作回归。

结论：核心断言**完全使用题面示例的字面输入**（同一个 `\udcff`、同一种 `exec(compile(...))` 形态、默认行模式）。

## (c) 题面示例照抄能否在 base 上复现

**不能。** 实跑（镜像只读、`--network none`，在容器内 `/tmp/x` 下运行）：

| 写法 | base 结果 |
| --- | --- |
| 题面示例原样存为脚本，`python example_literal.py` | `save()` 正常返回，不抛异常；`measured_files()` 只有脚本自身 |
| 同一段代码用 `python -c 'exec(open(...).read())'` 运行 | `save()` 正常返回，并告警 `No data was collected. (no-data-collected)` |
| 替代复现：把 `exec(compile("pass", "\udcff.py", "exec"))` 挪到 `cov.start()` 与 `cov.stop()` 之间 | `save()` 抛 `UnicodeEncodeError: 'utf-8' codec can't encode character '\udcff' in position 7: surrogates not allowed` |

原因（源码阅读）：示例里的 `exec(compile(...))` 在 `cov.start()` **之前**执行，不被追踪；`start/stop` 之间的 `exec("pass")` 的文件名是 `<string>`，被 `should_trace` 以 "not a real file name" 排除（或被归到调用方脚本）。示例注释 "Create a file with a non-UTF8 encodable filename" 也不准确：`compile(..., "\udcff.py", ...)` 不创建文件，只给代码对象设文件名。

初判归类：**P4**（原例在 base 不复现、描述有误导），公开材料可以消解：题面已给出触发机制（被追踪期间执行文件名不可编码的代码）和报错信息，按题面把 `exec(compile(...))` 放进测量区间即可复现；base 公开的 `ExecTest.test_correct_filename` 也展示了"被追踪模块内 exec"的写法。题面对 base 行为的陈述（"This line raises UnicodeEncodeError"）对示例原文是错误陈述，可以用 R-f 第一种（改正对 base 行为的错误陈述，须实跑证实）修；按 §3 P4 这不是必须修的阻断项。

## (d) 合理实现及隐藏测试能否全部接受

| 合理做法 | 预期结果（待第二步实跑） |
| --- | --- |
| R1 gold 式：在 `should_trace` / `check_include_omit_etc` 判定不可编码文件名不追踪 | 通过 |
| R2 写入时逐文件跳过：在 `CoverageData._file_id` / `add_lines` / `add_arcs` / `touch_file` 等处跳过不可编码的文件名，其它文件照常写入 | 通过 |
| R3 转换：用 `surrogateescape`、`surrogatepass`、`backslashreplace` 之类得到可存储的表示，照常记录 | 通过（测试不查 `\udcff.py` 的去向） |
| R4 在 `Collector.flush_data` 等上游过滤不可编码文件名 | 通过 |
| 上述做法再加一条 coverage 告警 | 通过（测试不查告警与 stderr） |

初判：隐藏测试对"跳过"与"转换"两类合理做法都接受，没有看到误拒合理实现的断言（T1 初判不命中）。在 R2E 精确映射下，另 14 个回归键不受这些做法影响（预计）。

gold 的范围备注（G1 线索，待核实）：gold 只在 `check_include_omit_etc` 拦截；`InOrOut._find_executable_files`（`--source` 下未执行文件的 `touch_file` 路径）不调用 `check_include_omit_etc`。若 `--source` 目录里有一个名字不可 UTF-8 编码、且未被执行的 `.py` 真实文件，gold 可能仍在保存时崩溃。这属于罕见路径，初判倾向记 T3 / G1 登记，不作为本题阻断条件。

## (e) 可能拿到 1 的错误实现

| 错误候选 | 违反的公开要求 | 预期能否拿 1 |
| --- | --- | --- |
| W1 只特判示例字符：文件名含 `\udcff` 才跳过 | 其它不可编码字符（如 `\udc80`）仍崩溃 | 能（示例拟合） |
| W2 `ascii_only`：凡是非 ASCII 文件名都跳过 | 破坏有文档、有公开测试的非 ASCII 文件名测量（`UnicodeFilePathsTest`、issue 432） | 能 |
| W3 `lines_only`：只修 `add_lines`，不修 `add_arcs` | `branch=True`（有文档的常用选项）下同一问题仍崩溃 | 能 |
| W4 整段吞错：在 `flush_data` / `get_data` / `add_lines` 整个循环外捕获 `UnicodeEncodeError` 后继续 | 排在不可编码文件之后的文件数据丢失；外层捕获时事务可能回滚，磁盘数据可能缺 `bug891.py` | 能（测试里 `bug891.py` 先写入，且只查内存 `_file_map`） |
| W5 只保内存、不保磁盘：如让 `_file_map` 保留、SQLite 写入失败被吞 | 保存的数据文件内容不完整 | 能（`measured_files()` 读内存） |

测试能挡住的：noop（崩溃）、"一律不记录任何文件"、`save()`/`get_data()` 变空。

## 初判严重度（§4，D1 严格版）

- 第 1 步：核心要求（不崩溃、其它文件仍被记录）有直接断言 → 不命中。
- 第 2 步：核心断言只用了题面示例的字面输入（同一个 `\udcff`、同一种触发形态、默认行模式）→ **命中，S1（T2c）**。
- 第 3 步：W4 属于"吞掉错误、抑制症状"的退化候选，预计能拿 1；是否构成已确认违例，取决于能否在其它顺序或磁盘读回上实际证明数据丢失 → 待第二步实跑。
- 第 4 步：若作者已构造 W2 / W3 并得 1，则分别破坏有文档的公开行为、在同一核心要求的其它实例上违反 → **S1**。

初判去向：**S1 → R-c**。补的断言应只针对有公开依据的窄问题：示例外的不可编码文件名（不同代理字符或出现在目录名里）、`branch=True`、合法非 ASCII 文件名仍被测量；可考虑从磁盘读回数据以挡住 W4 / W5。修订**不得**断言 `\udcff.py` 被跳过或被转换成某种形式，否则会误拒题面允许的另一种做法（P5 风险）。题面示例可按 R-f 第一种改正（把 `exec(compile(...))` 挪进测量区间、删掉"Create a file"这类错误说法），但不得写入隐藏测试的模块名 `bug891.py`、`measured_files()` 断言形态等细节。

未查（写初判时）：候选的实际评分、gold 在 `--source` 未执行文件路径上的行为、作者的修订测试与修订题面。
