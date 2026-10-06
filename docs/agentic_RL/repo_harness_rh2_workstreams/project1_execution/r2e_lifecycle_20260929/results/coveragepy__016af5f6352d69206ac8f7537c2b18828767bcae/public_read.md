# coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae 公开读者报告

- 角色：R2E 公开读者（单题闭环试行 2026-09-29），按 `roles/public_reader_r2e.md` 执行。
- 依据：只读了角色卡和本题 `PUBLIC_DIR` 内的文件（清单见第 5 节）。没有运行项目代码，没有开容器或远端。下文路径都相对 `PUBLIC_DIR`；`worktree/...` 即解题者在 `/testbed` 看到的同名文件。
- 同目录 `commands.json` 列了 6 条命令，全部是**建议，未执行**。

## 结论速览

- **题意清楚**：测量期间执行过的代码，如果文件名含不能按 UTF-8 编码的字符（例如孤立代理字符 `\udcff`），`Coverage.save()` 不应再抛 `UnicodeEncodeError`。题面允许"跳过这些文件"或"内部处理编码错误"两种做法（`user_prompt.txt:24`）。
- **能从 base 源码读出崩溃点**：`CoverageData._file_id()` 把路径作为 str 参数交给 sqlite3（`worktree/coverage/sqldata.py:358-369`，插入语句在 `:367`）；`SqliteDb.execute()` 只捕获 `sqlite3.Error`（`:1031-1047`），`UnicodeEncodeError` 不属于它，于是原样冒到 `save()`。
- **题面示例照抄不能复现**：示例里文件名为 `\udcff.py` 的代码在 `cov.start()` **之前**执行；测量期间只执行了文件名为 `<string>` 的代码，而 `should_trace` 不跟踪以 `<` 开头的文件名（`worktree/coverage/inorout.py:237-242`）。解题者得自己把 exec 挪到 start/stop 之间。
- **最关键的未知**：题面没有约定可观察行为。不可编码的文件最后是否出现在数据里、要不要发警告、`source=` 的"未执行文件发现"路径和直接调用 `CoverageData` API 算不算范围内，都没说。隐藏测试（`worktree/run_tests.sh:1` 跑的 `r2e_tests`，工作树里没有）如果只认其中一种，另一种同样合理的实现可能不过。靠公开材料消除不了这个风险。

## 1. 需求表

类型说明：**明示**＝题面直接写了；**推知**＝可从公开仓库代码或测试合理推出；**多解**＝仍有多种合理解释。

### 1.1 要改变的行为

| 编号 | 要求 | 类型 | 依据 |
| --- | --- | --- | --- |
| R1 | 测量期间执行了文件名不能按 UTF-8 编码的代码之后，`Coverage.save()` 不再抛 `UnicodeEncodeError`。 | 明示 | `user_prompt.txt:5-8`、`:20`、`:24`、`:27-31` |
| R2 | 处理方式可以是跳过这些文件，也可以在内部处理编码错误，两种都算"优雅处理"。 | 明示 | `user_prompt.txt:24` |
| R3 | 不能把异常换成另一种异常再抛出，例如仿照 `SqliteDb.execute` 现有做法包成 `CoverageException`（`worktree/coverage/sqldata.py:1033-1047`）。对调用者来说这仍然是崩溃。 | 明示（由 "without crashing" 直接推出） | `user_prompt.txt:24` |
| R4 | 行覆盖和分支覆盖两条写入路径都要处理：`add_lines`（`worktree/coverage/sqldata.py:423-453`）和 `add_arcs`（`:455-480`）都经过 `_file_id(add=True)`；`flush_data` 按 `branch` 二选一（`worktree/coverage/collector.py:422-426`）。 | 推知 | 同左 |
| R5 | 同一次运行里其它文件的数据要照常保存，包括非 ASCII 但能按 UTF-8 编码的文件名（如 `café.py`）。题面说的是"跳过它们"，即只跳过出问题的文件。另外，`add_lines` 在同一个 `with self._connect()` 事务里逐个文件插入（`sqldata.py:439-453`），中途出异常时 `SqliteDb.__exit__` 会回滚整批（`:1020-1024`），所以在外层吞掉异常会连带丢掉整批数据。 | 推知 | `user_prompt.txt:24`；`sqldata.py` 同左 |
| R6 | 同一条崩溃路径还有别的入口：`get_data()`（`worktree/coverage/control.py:682-699`）除了被 `save()`（`:640-643`）调用，还被 `combine()`（`:670`）、`_analyze()`（`:770`）以及各报告器（`html.py:84/184`、`jsonreport.py:33`、`summary.py:20/44`、`xmlreport.py:58`、`annotate.py:54`）调用；动态上下文切换时 `Collector.switch_context` 会在运行中途 `flush_data`（`collector.py:373-382`，触发点在 `control.py:591`、`pytracer.py:109-114/177-179`）。只在 `save()` 外面包一层 try/except 的修法覆盖不到这些入口。 | 推知 | 同左 |

### 1.2 应保留的旧行为

| 编号 | 要求 | 类型 | 依据 |
| --- | --- | --- | --- |
| K1 | 普通文件名和能按 UTF-8 编码的非 ASCII 文件名照常测量、照常写入数据；exec 执行的代码按它自己的文件名记录。 | 推知 | `worktree/tests/test_oddball.py:534-563`（ExecTest）；`worktree/tests/test_process.py:744-764`（test_lang_c：LANG=C 下 exec 文件名 `wut\xe9\xea\xeb\xec\x01\x02.py`，只断言输出） |
| K2 | 数据文件格式和公开 API 不变：schema 里 `file.path` 是 `text`（`sqldata.py:31`、`:60-65`；`worktree/doc/dbschema.rst:66`）；`measured_files()` 返回 str 集合（`sqldata.py:763-765`）；`Coverage.save/get_data` 签名不变。改 schema 要升 `SCHEMA_VERSION`，还会破坏旧数据文件的兼容性，题面没有这种要求。 | 推知 | 同左 |
| K3 | 仓库仍声明支持 Python 2.7（`worktree/setup.py:28-29`、`:122`；`worktree/tox.ini:5`）。解题环境只有 3.7.9，Py2 兼容性在环境里验证不了，隐藏测试大概率也不查。 | 仓库约定 | 同左 |

### 1.3 仍有多种合理解释

| 编号 | 未约定的点 | 说明 |
| --- | --- | --- |
| A1 | 不可编码的文件最后是否出现在保存的数据里，出现时用什么形式 | 跳过：`measured_files()` 里没有它。内部转换后存储：里面有一个变换过的名字。题面两种都允许。 |
| A2 | 要不要发警告；警告的文本和 slug | 题面没提。现有机制是 `Coverage._warn(msg, slug=...)`（`control.py:337-361`），`CoverageData` 也接收 `warn` 回调（`sqldata.py:182-200`）。 |
| A3 | `source=` 模式下"未执行文件发现"遇到磁盘上真实存在、文件名不是合法 UTF-8 的 `.py` 文件 | 路径：`control.py:717-722` → `inorout.py:395-437` → `files.py:411-432`（正则 `:431` 不排除代理字符）→ `sqldata.py:532-547` `touch_file`。这同样发生在 `save()` 期间，但题面描述的场景是"跟踪文件"，没提这条路径。 |
| A4 | 直接调用 `CoverageData.add_lines/add_arcs/touch_file` 传入这类文件名 | 题面的场景是经 `Coverage` 使用。 |
| A5 | 不可编码的上下文名（`switch_context` / 动态上下文）在 sqlite 绑定时同样会失败（`sqldata.py:376`、`:404`） | 标题只说文件名，按范围外处理。 |

## 2. 合理实现范围

不猜标准答案，只按题面允许的两个方向和代码结构，列出应当接受的实现族，以及它们在可观察行为上的差别。

1. **在跟踪决策处跳过**：在 `InOrOut.should_trace` / `check_include_omit_etc`（`worktree/coverage/inorout.py:194-337`）遇到不能按 UTF-8 编码的文件名时，返回"不跟踪"及原因。
   - PyTracer（`pytracer.py:131-136`）和 C tracer（`ctracer/tracer.c:386-404`）都调用这个 Python 回调，所以不用改 C 代码，也不用重新编译。
   - 能覆盖 R1、R4、R6：数据根本不会进入 collector。
   - 本身覆盖不到 A3（未执行文件发现只检查 omit，`inorout.py:418-437`）和 A4。
2. **在写入时过滤**：在 `Collector.flush_data` / `mapped_file_dict`（`collector.py:392-429`）或 `CoverageData` 的写入方法（`sqldata.py:358-547`）里跳过不能编码的名字，可以附带警告。
   - 放在 `CoverageData` 层能同时覆盖 A3、A4；放在 collector 层覆盖不到这两条。
   - 使用文件追踪插件时，`add_file_tracers` 遇到没登记过的文件会抛 `CoverageException`（`sqldata.py:511-516`），跳过逻辑要和它保持一致。
3. **内部转换后存储**：用某种错误处理方式把名字变成能存进 sqlite 的 str。
   - 插入和查询两侧必须一致：`_file_id`、`_file_map`，以及 `lines/arcs/file_tracer/contexts_by_lineno`、`update`（`sqldata.py:358-944`，其中 `update` 在 `:549-715`）。否则 `measured_files()` 返回的名字和实际跟踪到的名字对不上。
   - 存下来的名字已不对应磁盘上的真实文件，报告阶段会找不到源码。可行，但改动面和语义风险都更大。

**不满足或值得怀疑的做法：**

- 把 `UnicodeEncodeError` 转成 `CoverageException` 等其它异常：仍然是崩溃（R3）。
- 只在 `Coverage.save()` 外层捕获并吞掉异常：因为事务回滚，同一批其它文件的数据会丢（R5）；`get_data()`、报告、`combine`、动态上下文 flush 仍然会崩（R6）。
- 用"是否 ASCII"代替"能否按 UTF-8 编码"作判断：会误伤 `café.py` 这类本来能存的名字（违反 K1）。题面写的是 "non-UTF8 encodable"。

**约定情况**：题面没有约定命名、警告文本、配置开关或默认行为，唯一明确的要求是不崩溃。不需要改 C 扩展，也不需要改 schema。

## 3. 题面质量与初态线索

### 3.1 题面是否直接给出或强烈暗示修法

- 题面只给了机制和两个处理方向："coverage.py tries to encode the filename in UTF-8 without handling encoding errors"（`user_prompt.txt:8`）以及跳过或内部处理（`:24`）。没有代码，也没有点出位置。属于中等提示，不是现成答案。
- 有一处小偏差：base 的保存路径里并没有显式的 `.encode("utf-8")`，编码发生在标准库 sqlite3 绑定 str 参数的时候（`worktree/coverage/sqldata.py:367` 的 `con.execute(..., (filename,))`）。靠 grep `encode` 找不到根因，要看 traceback。

### 3.2 题面描述的报错能否从 base 源码读出会发生

- **能。** 调用链如下：
  1. `Coverage.save()`（`control.py:640-643`）
  2. `get_data()`（`:682-699`）
  3. `Collector.flush_data()`（`collector.py:411-429`）
  4. `CoverageData.add_lines/add_arcs`（`sqldata.py:423-480`）
  5. `_file_id(add=True)`（`:358-369`）
  6. `SqliteDb.execute`（`:1026-1047`，在 `:1032` 调 `self.con.execute`，`:1033` 只捕获 `sqlite3.Error`）
- sqlite3 对含孤立代理字符的 str 参数抛 `UnicodeEncodeError: ... surrogates not allowed`，这是标准库行为，仓库里看不到。本报告据此推断，留待 `repro_exec_surrogate` 实测；它和题面给出的报错一致。
- 文件名进入数据前会被规范成绝对路径（`inorout.py:253` → `files.py:54-77`、`:161-171`），所以报错里的 position 取决于当前目录的长度。题面是 80（`user_prompt.txt:31`）；在 `/testbed` 下按 `repro_exec_surrogate` 执行，预计是 9。不要逐字比对这个数字。
- 现实中这类名字的来源（推断，仓库里没有直接说明）：Linux 上文件名含非 UTF-8 字节（例如 0xff）时，Python 用 surrogateescape 解码，得到的正是 `\udcff`。代码对象的 `co_filename` 或 `os.walk` 结果都可能带上它，这也是 A3 那条路径的现实来源。仓库已有处理路径编码问题的先例：`files.py:68-71`、`:164-167` 捕获 `UnicodeError`；另见 `CHANGES.rst:849` 的 issue 533。

### 3.3 题面示例在 base 接口下是否说得通

- **照抄不能复现**（静态判断，留待 `prompt_example_literal` 实测）：
  - `user_prompt.txt:13` 的 exec 在 `cov.start()`（`:17`）之前执行，所以不会被测量。
  - 测量期间执行的是 `exec("pass")`（`:18`），它的代码文件名是 `<string>`；`should_trace` 对以 `<` 开头的名字直接返回不跟踪（`inorout.py:237-242`）。
  - 因此 `cov.save()` 预计不抛异常，最多打印 "No data was collected." 警告（`control.py:713-715`）。
- 注释 "Create a file with a non-UTF8 encodable filename"（`user_prompt.txt:12`）不准确：`compile()` 只创建代码对象，不创建文件。不过 coverage 记录数据时不检查文件是否存在（`inorout.py:194-297` 里没有存在性判断），所以不需要真文件也能复现。
- 示例缺了 `import coverage`，是小问题。
- 解题者需要自己想到的修正：把 `exec(compile(..., "\udcff.py", "exec"))` 放到 `start()` 与 `stop()` 之间。`Coverage.start` 的文档说同一作用域里的语句不会被测量（`control.py:507-509`），但 exec 会新建栈帧，新帧会被跟踪。仓库已有测试就是这么写的：`test_process.py:755-763`、`test_oddball.py:546-556` 都在被测脚本里 exec。

### 3.4 复现与调查入口；哪些缺失信息真会阻碍开发

- **能定位**：题面给了异常类型和触发它的 API（`save`）。按 3.3 修正后可以在 `/testbed` 复现，traceback 会直接指到 `sqldata.py:367` 和 `:1032`。
- **只需要正常读代码的部分**（不算题面缺陷）：tracer → collector → data 的数据流；`source=` 的未执行文件发现路径。
- **真正影响"判分预期"的缺失**：A1–A4 的可观察行为没有约定（见"结论速览"）。这不妨碍写出一个合理的修复，但决定了哪一种合理修复能过隐藏测试。

### 3.5 初态

- `worktree_manifest.json:14-16` 的 `initial_diff` 为 0 字节：镜像初态和 base 提交一致，只多了未跟踪的 `install.sh`、`run_tests.sh`（`:20-33`）。
- 版本号是 5.0.2a1（`worktree/coverage/version.py:8`）；`worktree/CHANGES.rst:25-40` 的 Unreleased 段里没有与本题相关的条目。
- 工作树里没有编译好的 `coverage/tracer*.so`，也没有 `tests/zipmods.zip`（两者都在 `.gitignore` 里，`worktree/.gitignore:6`、`:34`；另见 `environment_brief.md:5-6`）。容器里有没有，取决于 `install.sh:18-21` 当时是否编译或生成成功；编译失败时 `setup.py:202-214` 会退回纯 Python 安装。这对本题修复没有影响，因为两种 tracer 共用 Python 的 `should_trace` 和数据层。
- `install.sh` 的函数名和实际版本对不上：`test_39_install` 实际建的是 3.7 环境（`install.sh:14-15`），`test_37_install` 建的是 3.10（`:27-28`）。以 `environment_brief.md:10` 写的 3.7.9 为准。

### 3.6 公开提示分类（`public_bundle.json:15`）

- **题目需求**：修复仓库里的一个真实 issue；找到根因，修改非测试源码。
- **给解题者的操作指令**：不要改仓库测试文件（修复由另一组测试判定）；测试尽量只跑单个文件或模块；在 `/testbed` 用 `python -m pytest` 运行；确认完成后简短总结并停止调用工具。
- **环境事实声明**：`/testbed/.venv` 是项目环境，`python` 和测试工具已指向它；没有网络；`pip` 可能不可用。
  - `environment_brief.md:11` 写的是"pip 有，但不能出网"，和"可能不可用"不矛盾，效果相同：装不了新包。
- **对合法解法的影响**：不许改测试文件，所以复现脚本放 `/tmp`。"窄范围运行"和 `worktree/setup.cfg:2` 默认的 `-n3` 并行不冲突；在 2 CPU 下可以加 `-n 0` 串行跑，更快，输出也更清楚。没有发现会限制合法解法的冲突。

## 4. 开发需求表

下表命令都是**建议，未执行**；完整命令文本和预期见同目录 `commands.json`（按 `id` 对应）。

| 操作 / 资产 / 服务 | 公开依据 | environment_brief 支持到哪一层 | 缺口 | 最小命令（建议，未执行）与预期 |
| --- | --- | --- | --- | --- |
| 解释器与已安装的 coverage | `install.sh:14-24`（`uv venv --python 3.7`、`uv pip install -e .`）；`coverage/version.py:8` | 只写到解释器路径和版本（`environment_brief.md:10`） | 是否是可编辑安装、C tracer 是否编译、文件系统编码、PATH 上有没有 `coverage` 命令，都没说 | `env_import`：预期 3.7.9、`coverage 5.0.2a1 /testbed/coverage/__init__.py`、`CTracer` 打印出类或 `None`、`fs utf-8 surrogateescape` |
| 复现 bug（经公开 API） | `user_prompt.txt:12-20`；`control.py:640-699`；`sqldata.py:358-369` | 不涉及 | 示例要先修正（3.3） | `repro_exec_surrogate`（全文见下）：修复前两次 `save()` 都报 `UnicodeEncodeError`（消息含 `surrogates not allowed`、`position 9`），退出码 1；修复后两次都 OK，`ok_exec.py` 和 `caf\xe9_ok.py` 都在 `measured_files` 里，退出码 0 |
| 核对示例原样执行的行为 | `user_prompt.txt:12-20`；`inorout.py:237-242` | 不涉及 | — | `prompt_example_literal`：修复前后都是退出码 0，`measured_files=[]`，stderr 可能有 "No data was collected." |
| 边界探针（看实现覆盖面，题面未要求） | `control.py:717-722`；`inorout.py:395-437`；`files.py:411-432`；`sqldata.py:532-547` | `/tmp` 可写，1 GiB（`environment_brief.md:12`）；在 `/tmp` 建含 0xff 字节的文件名依赖 Linux 文件系统，brief 没写文件系统类型 | 题面未要求这两条路径 | `boundary_source_and_data_api`：修复前 (a)(b) 都报 `UnicodeEncodeError`，退出码 1；修复后看实现，失败不等于不合格 |
| 公开测试（回归） | `setup.cfg:1-2`；`requirements/pytest.pip:7-17`；`requirements/dev.pip:13-14` | 公开提示说测试工具指向 `.venv`（`public_bundle.json:15`），但没列出装了哪些包 | pytest-xdist、flaky、mock、unittest-mixins 是否都装了，未验证（`setup.cfg` 的 `-n3`、`--no-flaky-report` 依赖前两者）。PyContracts 是用 git URL 安装的（`pytest.pip:13`），可能缺，但只有 `COVERAGE_TESTING=True` 时才会导入（`misc.py:55-60`、`env.py:103`、`inorout.py:168-178`；这个变量由 `igor.py:103-106` 设置，直接跑 pytest 时不会设） | `public_tests_data_api`：`cd /testbed && python -m pytest -n 0 -o cache_dir=/tmp/r2e_pytest_cache tests/test_data.py tests/test_api.py`，修复前后都应全部通过 |
| 与题意最近的公开测试 | `test_oddball.py:534-563`；`test_process.py:744-764`；`tests/coveragetest.py:355`、`:396-420`；`tests/helpers.py:20-37` | 同上 | `test_lang_c` 通过 shell 调 `coverage` 命令（`helpers.py:37` 的 `shell=True`），需要它在 PATH 上；brief 只说 `python` 指向 venv | `public_tests_exec_related`：`cd /testbed && python -m pytest -n 0 -o cache_dir=/tmp/r2e_pytest_cache tests/test_oddball.py::ExecTest tests/test_process.py::ProcessTest::test_lang_c tests/test_files.py`，修复前后都应通过 |
| 构建 | `setup.py:173-214`；`tox.ini:41-48` | brief 没提编译器 | 纯 Python 修复不需要重建；改 C 代码需要编译器，有没有未知 | 不给构建命令 |
| 服务 / 网络 | — | 没有网络（`environment_brief.md:11`） | 不需要 | — |

`repro_exec_surrogate` 全文（建议，未执行；和 `commands.json` 里的内容一致）：

```bash
cd /testbed && python - <<'PY'
import os, shutil, sys
import coverage
base = "/tmp/r2e_cov_repro"
shutil.rmtree(base, ignore_errors=True)
os.makedirs(base)
bad = 0
for branch in (False, True):
    cov = coverage.Coverage(data_file=os.path.join(base, "data_branch_%s" % branch), branch=branch, config_file=False)
    cov.start()
    exec(compile("a = 1", os.path.join(base, "ok_exec.py"), "exec"), {})
    exec(compile("b = 2", os.path.join(base, "caf\xe9_ok.py"), "exec"), {})
    exec(compile("c = 3", "\udcff.py", "exec"), {})
    cov.stop()
    try:
        cov.save()
    except Exception as exc:
        bad += 1
        print("branch=%s: save() raised %s: %s" % (branch, type(exc).__name__, ascii(str(exc))))
        continue
    files = sorted(cov.get_data().measured_files())
    print("branch=%s: save() OK, measured_files=%s" % (branch, ascii(files)))
    for name in ("ok_exec.py", "caf\xe9_ok.py"):
        if not any(f.endswith(name) for f in files):
            bad += 1
            print("branch=%s: encodable file %s missing from saved data" % (branch, ascii(name)))
sys.exit(1 if bad else 0)
PY
```

- 修复前预计输出两行 `branch=False/True: save() raised UnicodeEncodeError: ...surrogates not allowed`，退出码 1。
- 修复后预计两次都是 `save() OK`，`measured_files` 至少包含 `/tmp/r2e_cov_repro/ok_exec.py` 和 `caf\xe9_ok.py`，退出码 0。有没有 `\udcff` 的条目取决于实现（A1）。
- 这个脚本只写 `/tmp`，不在 `/testbed` 里建文件。`\udcff.py` 只是代码对象的文件名，不会落盘。

## 5. 阅读范围

- **打开过**：
  - 角色卡。
  - `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`。
  - `worktree_manifest.json`：只看了顶层键 `export`、`initial_diff`、`untracked_*`、`not_included`，以及 `files` 条目的样例。其中指向 `PUBLIC_DIR` 以外的路径（`initial_diff.source`、`public_bundle.json` 的 `source`）没有打开。
  - `worktree/` 下的构建、配置与说明文件：`install.sh`、`run_tests.sh`、`setup.cfg`、`setup.py`（部分）、`tox.ini`、`requirements/*.pip`、`.gitignore`、`igor.py`（grep 和 `do_zip_mods` 片段）、`CHANGES.rst`（开头和 grep）、`doc/dbschema.rst`（grep）。
  - `worktree/coverage/` 源码：
    - 通读：`__init__.py`、`version.py`、`env.py`、`data.py`、`sqldata.py`、`collector.py`、`inorout.py`。
    - 部分：`control.py`（1-730 行及 grep）、`files.py`（1-240 行和 `find_python_files`）、`pytracer.py`（60-236 行）、`misc.py`（1-170 行）、`python.py`（`source_for_file`）、`config.py`（515-545 行）、`ctracer/tracer.c`（grep 以及 380-470、835-870、965-985 行）。
  - `worktree/tests/`：`conftest.py`；`coveragetest.py`、`helpers.py`（片段）；`test_process.py`（730-800 行和类大纲）；`test_oddball.py`（534-566 行和大纲）；`test_api.py`（导入部分、979-1110 行）；`test_data.py`（导入和类大纲）。
  - 对 `coverage/` 和 `tests/` 做过若干 grep。
- **没查**：其余测试文件的全文、报告器实现（html/xml/json/summary）、`cmdline.py`、C tracer 的其余部分、大部分文档。
- **限制**：
  - `user_prompt.txt` 只是静态渲染，不是模型实际收到的消息。
  - `worktree/` 不是完整的运行容器：没有 `.venv`、编译好的扩展、`zipmods.zip` 和隐藏测试。
  - 模型实际消息、运行资源和开发条件都没有验证；`commands.json` 一条都没执行。
  - `commands.json` 里的 Python 脚本只在本机用 `python3 -m py_compile` 查过语法，没有运行。
  - sqlite3 对孤立代理字符的行为是按标准库知识推断的。
- **来源说明**：没有查上游仓库的后续提交或 PR，也没有做网络搜索。我对 coverage.py 的一般了解可能来自训练数据，但本报告的判断都以 `PUBLIC_DIR` 里的文件为依据，没有用它推断标准答案。没有读到任何私有材料。
