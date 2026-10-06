# dask__dask-8801：v4 聚焦复核

2026-09-30，聚焦复核者（新会话，不继承作者与首轮复核者的上下文）。本轮按首轮复核 [review.md](review.md) 的意见（B1、N1–N6、建议 4）核对作者的 v4，结论页见 [result.md](result.md)。

**总判断：部分同意。阻断 1 项（B2）。**

- **B1 已真正解决。** `c.yaml` 子目录检查与评分身份无关：
  - 正式评分（UID 54322）中 `oserr_fatal` 为 0，gold 为 1；
  - 本复核以 nobody（UID 65534）与 root 各跑一次：gold 与 7 个合理实现为 1；`oserr_fatal` 与另写的 `wr_open_unguarded`（把 `open()` 移出 try）为 0。
  - 只有“权限错误致命、其它 OSError 照常跳过”的 `wr_perm_fatal` 拦不住。这种写法要主动违背代码注释与公开测试，建议登记 T3。
- **N1–N6 与建议 4 的处理得当。**
  - 导入断言与 R-f 的 “including `import dask`” 同进同退，表述一致；
  - 直接文件路径的断言没有引入新误拒；
  - R-f 只写需求，没有泄露测试细节。
- **新阻断 B2：v4 仍会放过“点名错误文件”的实现。**
  - 复核者构造的 `wr_zip_misalign` 在读完所有文件后，用 `zip(file_paths, configs)` 检查类型。它在 v4 上两种身份都得 1。
  - configuration.rst 记载的下游做法会用 `ensure_file(comment=True)` 在 `~/.config/dask/` 写入全注释的默认配置文件。只要这样的文件（探针里叫 `distributed.yaml`）在搜索顺序上排在用户的坏文件之前，它的报错和新进程 `import dask` 点名的都是那个全注释的正常文件。
  - `wr_all_files` 在报错里列出全部文件，不指明哪个坏，在 v4 上同样得 1。
  - **归类：同一问题的新实例，不是新的独立缺陷。**
    - 它与作者 S1 表中的 `wrong_file` 都属于“报错点名错误文件”。v3 起的顺序断言只检查了坏文件之后还有文件的情形。
    - 它不是 v4 修复引入的：`wr_zip_misalign` 在原测试上也得 1，按 v3 的测试结构推断同样得 1。
    - 它与 B1 的状态边界（不可读条目、评分身份）无关。
    - 修法只改同一测试函数里的两处（不可读条目改名排到坏文件之前；加一条“不点名后面的正常文件”），已在两种身份下做私有验证。
- **非阻断：原因词表仍会误拒两个合理实现。**
  - 两个实现的措辞分别是 “must contain an object …” 和 “should be a YAML map of settings …”。
  - 这与 N3 是同一问题，属于首轮已同意登记的词法残余。
  - 建议随 B2 一并把词表放宽为 `dict`、`map`、`key`、`object` 或实际类型名。已验证：放宽后没有任何原本为 0 的错误候选变成 1。

## 1. 核对范围与证据层级

**读过的材料**：
- 首轮复核 review.md、result.md（v4）；
- `revised_test_v4.patch`：sha256 为 `91baa55d…`，与 `materials_revised_v4.json` 内嵌的补丁逐字相同；套在 base 测试文件上，得到 `test_config_revised_v4.py`（`38e8f4d1…`）；
- `revised_statement_v1.txt`、`behavior_v4.py`、作者与首轮复核者的候选补丁；
- 标准 v1 的 §3–§5 与 P5、review-standards、本目录 README 的“第二批复核补充的校准”。

**作者的正式证据：只核对，不重跑。**

- **v4 诊断评分的 23 份账本**：
  - 每份的 `log.sha256` 都与归档日志一致；
  - 我从日志重新解析 PASSED／FAILED，按参考名单算分，结果与账本的 reward 和 F2P 计数一致；
  - 每份都是 UID 54322、评分器后缀 `-v4`、参考缺席 0、解析出 45 项、清理成功、安装 rc=0；
  - 候选补丁的 sha256 与实验目录中的文件一致；
  - 23 份 `audit_*/materials.json` 内嵌的测试补丁都是 `91baa55d…`。
- **`failure_reasons.txt`**（v4 共 23 行，原材料补跑 3 行）：分数、F2P 计数和 sha 前缀都与账本一致。逐份失败位置与 result.md §4 一致，例如：
  - `oserr_fatal` 失败在第一段的 `merge(...) == {"x": 1}`，消息是 `[Errno 21] Is a directory: …/c.yaml`；
  - `import_swallow`、`rv_import_warn` 失败在 `assert proc.returncode != 0`；
  - `noreason` 同时失败在解析器原因和词表两处。
- **09-29 的账本**：原材料 20 份、v3 20 份也一并核对，同样一致，分数与 result.md 的汇总表相同。
- **私有对照 `semantic_v4/`**：root 组（b8）和 nobody 组（b7）都按参考名单计分。23 个做过正式评分的版本逐一与正式分数相同；`rv_enum_types` 为 1。

**本复核的运行：私有对照和私有模拟评分，不是正式评分。**

- **环境**：
  - 镜像 `c3keep/dask8801:src`（image ID `695d2cc2…`），`--network none`，一次性容器；
  - 3 个容器依次处理 42 个版本；
  - 每个版本开始前先 `git checkout` 还原，并断言工作树干净、`dask/config.py` 的摘要等于 base 的 `689e71ce…`；然后 `git apply`，各补丁的 sha256 都已核对。
- **每个版本跑的内容**：
  - 行为探针 `behavior_review.py`，nobody 与 root 各一次；
  - 原版、v4、v4rva、v4rvb 四份测试文件，各以 nobody 和 root 运行 `python -m pytest -p no:cacheprovider -n0 -rA --color=no dask/tests/test_config.py`。
- **判分**：
  - 按参考名单逐项判，F2P 2 项、P2P 41 项；
  - 336 次 pytest 都解析出 45 项；
  - root 下不在名单内的两项权限测试照常失败，不计分。
- **版本**：base、gold、作者 18 个、首轮复核者 4 个（用作者重建的补丁）、本复核者 18 个。
- **总体结果**：
  - 所有格子两种身份的结果都相同；
  - 我对 v4 的复跑与 23 次正式评分逐一相同。
- **证据位置**：`rh2/experiments/category3_cloud_20260929/dask8801/review_v4/`，包括：
  - 生成与运行脚本；
  - 候选补丁与 `candidates_review.json`；
  - 测试草案与 `tests_review.json`；
  - `out/private/` 下的逐版本输出；
  - `scores.json`、`scores_table.txt`、`behavior_summary.json`、`behavior_table.txt`。

## 2. B1 与 N1–N6 的核对结果

| 项 | 首轮意见 | v4 的处理 | 核对 | 结论 |
| --- | --- | --- | --- | --- |
| B1 | 拦下 `oserr_fatal` 要同时依赖非 root 评分、P2P 追加和推算 | 在 F2P 函数体内加 `c.yaml` 子目录检查，撤掉 P2P 追加 | 正式评分（UID 54322）：`oserr_fatal` 为 0，失败在 `c.yaml`。私有运行（nobody、root）：gold 与 7 个合理实现为 1，`oserr_fatal`、`wr_open_unguarded` 为 0 | **已解决**；残余的 `wr_perm_fatal` 见 §3.1 |
| N1 | 导入断言只靠 P5 第一分支立足 | §3 登记同进同退，`rv_import_warn` 列为按第一分支拒绝 | 正式 v4：`rv_import_warn`、`import_swallow` 为 0，都失败在 `returncode` 断言 | 得当，见 §3.5 |
| N2 | 没测直接文件路径 | 每个实例另按文件路径加载一次 | `rv_dir_only` 正式为 0，私有两种身份也为 0；本复核的合理候选在文件路径形态下没有新失败 | 得当 |
| N3 | 词表缺 `key` | 加入 `key` | `rv_kv_pairs` 正式为 1；但仍有同类误拒 2 例 | 基本得当，建议再放宽（§3.3） |
| N4 | `c.yaml` 检查比注释里的 “permission errors” 宽 | §4 写明边界 | 与 base、gold 的 `except OSError` 一致 | 得当 |
| N5 | `rv_enum_types` 得 1 | 负责人决定不补 `1.5`，维持 T3 | 私有两种身份 v4 都为 1；顶层 `1.5` 在 merge 里报 `AttributeError`，不含路径 | 同意维持 T3 |
| N6 | 三个小事项 | 已改步号，已说明 CRLF／LF 与 `dubious ownership` | §3 已改为第 4 步；原题面 164 行中，首行标题与末行（代码块结束的三个反引号）用 LF，其余 162 行用 CRLF；新增段落用 2 个 LF。与“原正文 CRLF、新增段 LF”的说明大体一致，落地按字节保留即可 | 得当 |
| 建议 4 | P5 只用依据 1、2 立论 | 已改 | §3 已注明依据 3 两边都能解读 | 得当 |

## 3. 新增断言的依据与过严检查

### 3.1 `c.yaml` 子目录（B1）

- **依据**：
  - base 有两处 `except OSError: # Ignore permission errors`，`IsADirectoryError` 是 `OSError` 的子类；
  - gold 保留了同样的 except；
  - 公开测试 `test_collect_yaml_permission_errors[directory|file]` 在非 root 下体现了“读不到的条目要跳过”。
- **与身份无关**：对目录调用 `open()`，root 下同样抛 `IsADirectoryError`，root 的权限绕过不影响 EISDIR。两种身份的私有结果相同，与正式链（UID 54322）也相同。
- **能拦下的写法**：
  - `oserr_fatal`：全捕获后包装成 `ValueError`；
  - `wr_open_unguarded`：重写循环时把 `open()` 移出 try，这是另一种自然写法。
- **拦不住的写法**：`wr_perm_fatal` 只把 `PermissionError` 变成致命错误，其它 OSError 仍跳过。
  - 它在两种身份下 v4 都得 1；
  - nobody 下公开的 `[file]` 权限测试会失败，但这一项不在参考名单内；
  - 这种写法要主动违背代码注释和公开测试，自然度低，建议登记 T3；
  - 若日后 D6 支持追加 P2P，且评分身份固定为非 root（正式 profile 是 UID 54322），可以把两项权限测试加入 P2P，作为首轮所说的“可选加固”。
- **过严的一面**：只捕获 `PermissionError` 的实现会在 `c.yaml` 处崩溃而被拒。result.md §4 已写明，这属于对 base 边缘行为的回归，我同意这样处理。
- **警告也会失败**：setup.cfg 的 `filterwarnings = error:::dask[.*]` 会把 dask 发出的警告升级为错误，所以“跳过不可读条目时发警告”的实现也会在第一段失败。这是推断，未另造候选实跑；作者 v1 的 `warn_skip` 被当成报错，走的是同一机制。公开权限测试在非 root 下的要求相同，不算新增的过严。

### 3.2 直接文件路径（N2）

- **依据**：
  - `collect_yaml` 有 `else: file_paths.append(path)` 分支；
  - P2P 的 `test_collect_yaml_paths` 直接传文件；
  - `DASK_CONFIG` 可以指向文件。
- **过严检查**：作者与首轮复核者的 7 个合理实现、本复核的 6 个合理候选，在文件路径形态下都能通过。两个词表误拒发生在目录形态的第一处词表断言上；放宽词表后，文件路径形态也通过。未发现新误拒。

### 3.3 原因词表（N3）

**现状**：v4 要求消息去掉路径后，含 `dict`、`mapping`、`key` 或实际类型名之一。

**新误拒**：下面两个合理候选在两种身份下 v4 都得 0，都失败在词表断言。

- `ok_object_value`，消息为 “Dask config file … must contain an object at the top level, found [1234]”；
- `ok_map_settings`，消息为 “… should be a YAML map of settings, but its top level is [1234]”。

它们都点名了文件，说明了期望什么、实际是什么，`import dask` 会失败并点名文件，行为与 gold 同样合格。

**这类措辞并不罕见**：
- `collect_yaml` 也读 `.json`，JSON 把映射叫作 object；
- 仓库里的 `dask/dask-schema.yaml` 有 8 处用 `type: object` 描述嵌套配置，P2P 的 `test_schema` 会读这个文件。

**放宽的效果**：v4rvb 把词表改为 `("dict", "map", "key", "object", type_name)`。
- 这两个候选变为 1；
- 所有候选中，没有任何原本为 0 的错误候选变成 1。作者的 `noreason`、本复核的 `wr_wrong_reason`（原因写错）仍为 0；`rv_enum_types`、`wr_perm_fatal`、`wr_null_raises` 在 v4 上本来就是 1，放宽前后不变。

**评估**：
- 这与 N3 是同一问题的新实例。首轮已同意把词法残余登记为 T3，§5 也写明“不追着候选改分”，所以不列为阻断。
- 放宽没有额外成本，建议随 B2 一并改；如果不改，至少把这两个具体例子写进 §7。

**与 R-f 用词的关系**：R-f 写的 “a mapping of keys to values” 与词表里的 `mapping`、`key` 重合。
- 这是对齐，不是泄露，因为题面没有要求消息必须含哪个词；
- 但它也说明现有词表部分依赖解题者沿用题面的用词，这是再放宽一步的另一个理由。

### 3.4 解析器原因（`problem`）

- **现状**：断言把“原因”落到纯 Python 版 PyYAML 的 `problem` 文字上。
- **误拒例子**：镜像装有 libyaml（`yaml.__with_libyaml__` 为 True）。`gr_csafe_loader` 只在 gold 上把解析器换成 `yaml.CSafeLoader`，两种身份 v4 都得 0。libyaml 给出的原因文字不同，分别是：
  - “did not find expected node content”；
  - “found a tab character that violates indentation”。
- **处理建议**：换解析器与本题无关，也少见，列为 T3。若要消除，可以在测试里同时接受 `CSafeLoader` 的 `problem`（libyaml 可用时）。
- **另一个更少见的例子**：消息用 `{exc!r}` 并 `from None` 时，制表符例子里的反斜杠会被转义，断言也会失败，一并登记。

### 3.5 导入断言、P5 与 R-f

- **一致性**：
  - R-f 写的是 “loading the configuration, including `import dask`, should fail with an error that names the offending file …”；
  - 断言要求 `returncode != 0`，且 stderr 含该文件路径，正好对应“失败”和“点名”；
  - 导入路径上不查原因，原因由 `collect_yaml` 的断言覆盖，这样安排合理。
- **同进同退**：result.md §3、§4 都写明了。若 P5 改为“警告并跳过”，R-f 的 “including `import dask` … should fail” 与这条断言要一起撤，两个 F2P 也要反向重写。两处表述一致。
- **P5**：同意第一分支。
  - base 下语法错误本来就会让 `import dask` 失败。作者的私有探针（`evidence/rerun_0930/semantic_v4_table.txt`）显示：base 用新进程 import 含语法错误文件的目录，rc=1。
  - 跳过只适用于读不到的条目。
- **小措辞**：result.md §4 第 6 行把 `warn_skip`、`silent_skip` 列为被这条断言拦下的候选。实际上它们在同一函数里更早的“加载必须失败”处就失败了，建议改为“若执行到此，也会被拦下”。
- **R-f 的边界**：
  - 没有写入测试输入：`{`、制表符、`[1234]`、`hello`、`1234`、空文件、全注释、子目录、直接文件路径都没有出现；
  - 没有英文词组、异常类型或 helper 名；
  - 只写了两类失败的一般说法，以及“点名文件、说明原因、包括 import”。
  - 结论：在 R-f 模板的边界内。
- **可选的措辞改进**：
  - 现有写法 “when a Dask configuration file cannot be used as configuration” 可能被理解为“读不到的文件也算”。解题者因此可能把权限错误做成致命错误，而这会被 `c.yaml` 检查和公开权限测试拒绝。
  - 建议改为 “when the contents of a Dask configuration file cannot be used …”，并请新公开读者专门核对这一点。

## 4. 复核者构造的候选与私有结果

### 4.1 本复核的 18 个候选

- 补丁与生成脚本在 `review_v4/`，sha256 见 `candidates_review.json`。
- 表中每格都是 nobody 与 root 各跑一次，两者结果全部相同。
- “原版”指原 test_patch。

| 候选 | 写法 | 判断 | 原版 | v4 | v4rva | v4rvb |
| --- | --- | --- | --- | --- | --- | --- |
| `ok_object_value` | 自定义 `ConfigFileError(Exception)`；非映射报 “must contain an object at the top level, found [1234]”；语法错误用 `from exc` | 合理 | 0 | **0**（词表） | **0** | 1 |
| `ok_map_settings` | 在循环内校验；语法错误用隐式异常链；非映射抛 `TypeError`，报 “should be a YAML map of settings, but its top level is [1234]” | 合理 | 0 | **0**（词表） | **0** | 1 |
| `ok_dictionary_typeerror` | 在循环内校验，流式加载；非映射抛 `TypeError`，报 “must be a dictionary, not list” | 合理 | 0 | 1 | 1 | 1 |
| `ok_aggregate` | 先检查全部文件，再一次抛出一个 `ValueError`，列出每个坏文件及原因 | 合理 | 0 | 1 | 1 | 1 |
| `ok_yamlerror_subclass` | 异常类继承 `yaml.YAMLError`，用 pathlib 读取；报 “must contain key/value pairs … got list” | 合理 | 0 | 1 | 1 | 1 |
| `ok_falsy_empty` | 保留 `or {}`，顶层假值照旧当空配置 | 合理（假值已登记 T3） | 0 | 1 | 1 | 1 |
| `gr_attr_wrap` | 不写类型检查，用 `update({}, data)` 试合并；任何异常包装成 “Could not load Dask config file <路径>: 'str' object has no attribute 'items'” | 灰区，不判错：点名正确，原因就是原 `AttributeError` 的文字，但含类型名 | 0 | 1 | 1 | 1 |
| `gr_basename_only` | 在 gold 上只把完整路径换成文件名 | 拒绝合理：多个搜索目录里可以有同名文件 | 0 | 0 | 0 | 0 |
| `gr_csafe_loader` | 在 gold 上只把解析器换成 `yaml.CSafeLoader` | 边缘误拒（T3，§3.4） | 1 | **0** | 0 | 0 |
| `wr_zip_misalign` | 读完后用 `zip(file_paths, configs)` 检查；None 与不可读条目被跳过后，两个列表错位 | **错误**（B2） | 1 | **1** | 0 | 0 |
| `wr_zip_misalign_orempty` | 同上，但保留 `or {}`，只有不可读条目会导致错位 | 错误，边缘 | 1 | **1** | 0 | 0 |
| `wr_all_files` | 整个循环外包一层，报错列出找到的全部文件 | **错误**（B2） | 0 | **1** | 0 | 0 |
| `wr_dir_named` | 只点名搜索目录，不点名文件 | 错误 | 0 | 0 | 0 | 0 |
| `wr_import_only` | API 静默跳过坏文件，只在模块导入时另做检查并报错 | 错误 | 0 | 0 | 0 | 0 |
| `wr_wrong_reason` | 顶层非映射也报 “is not valid YAML” | 错误 | 0 | 0 | 0 | 0 |
| `wr_open_unguarded` | 把 `open()` 移出 try，是 `oserr_fatal` 的另一种写法 | 错误 | 0 | 0 | 0 | 0 |
| `wr_perm_fatal` | 在 gold 上把权限错误改为致命，其它 OSError 跳过 | 错误，自然度低（T3） | 1 | **1** | 1 | 1 |
| `wr_null_raises` | 按文本判断空文件与全注释；显式 `null`、`~`、只含 `---` 与注释的文件会报错 | 错误，边缘（T3） | 0 | **1** | 1 | 1 |

**判断依据：`behavior_review.py` 的 nobody 与 root 探针。**

- **`wr_zip_misalign`**：
  - 探针目录里有一个 `ensure_file(source=…/distributed.yaml, destination=d, comment=True)` 写出的全注释文件，再加一个顶层为 str 的 `mine.yaml`；
  - `collect_yaml` 报 “A dask config file at '…/distributed.yaml' is malformed … got a str instead”；
  - 新进程 `import dask` 的 stderr 最后一行也点名 `distributed.yaml`，不含 `mine.yaml`；
  - gold 与所有合理候选点名的都是 `mine.yaml`；
  - base 在同一场景报原来的 `AttributeError`。
- **`wr_zip_misalign_orempty`**：名为 `0.yaml` 的子目录排在坏的 `a.yaml` 之前时，它点名的是 `0.yaml`。
- **`wr_all_files`**：坏 `a.yaml` 后面还有 `b.yaml`、`c.yaml` 时，消息是 “Could not load Dask configuration from ['…/a.yaml', '…/b.yaml', '…/c.yaml']: …”。
- **`wr_perm_fatal`**：nobody 下，不可读的文件报 “Cannot read Dask config file …: [Errno 13] Permission denied”；root 下照常加载。
- **`wr_null_raises`**：只含 `---` 与注释的文件报 “… got NoneType”，而 base 把这类文件当空配置。
- **`wr_import_only`**：`collect(paths=[坏目录], env={})` 静默返回 `{'x': 1}`。

### 4.2 作者与首轮复核者的候选（24 个版本）

- **v4**：私有复跑两种身份的结果都与正式评分相同：
  - noop 为 0，gold 为 1；
  - 6 个作者合理实现与 `rv_kv_pairs` 为 1；
  - `warn_skip`、`rv_import_warn` 为 0；
  - 12 个错误候选为 0；
  - `rv_enum_types` 为 1（T3）。
- **v4rva、v4rvb**：24 个版本的结果与 v4 完全相同，没有新误拒，也没有新放过。

## 5. 阻断项

### B2：v4 放过点名错误文件的实现

**当前行为**：
- `test_collect_yaml_no_top_level_dict` 里，坏文件 `a.yaml` 在目录中排第一，后面是 `b.yaml` 和名为 `c.yaml` 的子目录（`test_config_revised_v4.py` 第 183 行）。
- 因此只检查了“坏文件之后还有文件”时的点名（第 201 行 `assert fil_path in msg`）。
- 另外两种情形都没有检查：
  - 坏文件之前有被跳过的条目；
  - 报错把所有文件都列出来。

**违反的公开要求**：报错必须点名出问题的文件。依据是 R-f，以及 result.md §1 表中“报错点名出问题的文件”一行；作者 S1 表中的 `wrong_file` 违反的也是这一条。

**证据（私有模拟评分，两种身份相同）**：
- `wr_zip_misalign`：原版 1，v4 1；
- `wr_all_files`：原版 0，v4 1；
- 行为证据见 §4.1。在全注释默认文件排在坏文件之前的配置里，`wr_zip_misalign` 的报错和 `import dask` 都点名那个全注释文件。

**影响**：
- **按 §4 第 4 步（D1 严格版）判 S1**：这是同一核心要求的其它实例，而且输入不是边缘输入。configuration.rst 写明，下游库用 `ensure_file(source=fn, comment=True)` 在 `~/.config/dask/` 写入全注释文件，并提示 “The user can investigate `~/.config/dask/*.yaml` to see all of the commented out configuration files”。
- **误导更严重**：用户的坏文件只要排在这样的文件之后，就会被引向错误的文件。作者 §1 的原话是“点错文件比不点名更误导”。
- **修订验收不再满足**：§5 的 R-c 验收要求“已知相关的错误候选仍为 0”，v4 现在做不到。

**归类（供熔断判断）**：
- 与作者 S1 中的 `wrong_file` 是同一问题的新实例；v3 加入的顺序断言只覆盖了一个方向。
- 不是 v4 修复引入的：`wr_zip_misalign` 在原测试上得 1；v3 的目录里只有 `a.yaml`，之后是 `b.yaml`，坏文件之前没有条目，按结构推断同样得 1（未实跑）。
- 与 B1 的状态边界（不可读条目、评分身份）不同。
- 修复只动同一测试函数，不跨 ownership 边界。
- 结论：按协作协议熔断条款的字面，三条触发条件都不满足。但本题确实是连续第二轮出现新阻断；README 记录 dvc-9395 时，把“同一题连续两轮出现新阻断”当作熔断处理。是否按那个先例收口，由负责人决定。

**修法**：采用 v4rva，改动两处，都在 `test_collect_yaml_no_top_level_dict` 内。草案文件是 `review_v4/test_config_v4rva.py`（`a5cdf87c…`）；相对 base 测试的补丁是 `revised_test_v4rva.patch`（`e33aab43…`）。

```diff
-    os.mkdir(os.path.join(dir_path, "c.yaml"))
-    with open(os.path.join(dir_path, "b.yaml"), mode="wb") as f:
+    os.mkdir(os.path.join(dir_path, "0.yaml"))  # 不可读条目排在 a.yaml 之前
+    other_path = os.path.join(dir_path, "b.yaml")
+    with open(other_path, mode="wb") as f:
         f.write(b"x: 1\n")
 ...
             assert fil_path in msg
+            assert other_path not in msg
```

- **改名**：不可读条目改名后排到坏文件之前，原有的“跳过不可读条目”检查（B1）作用不变。基于 `zip` 的错位写法都会点名 `0.yaml`。
- **新断言**：拦下列出全部文件的写法。

**修后预期（已在两种身份下私有验证）**：
- noop 为 0，gold 为 1；
- 作者 6 个合理实现与 `rv_kv_pairs` 为 1；
- `warn_skip`、`rv_import_warn` 为 0；作者与首轮复核者的 12 个错误候选为 0；
- `wr_zip_misalign`、`wr_zip_misalign_orempty`、`wr_all_files` 由 1 变为 0，失败位置分别是：
  - 前两个在 `assert fil_path in msg`，报错点名的是 `0.yaml`；
  - `wr_all_files` 在 `assert other_path not in msg`；
- 本复核的 4 个合理候选与灰区的 `gr_attr_wrap` 仍为 1；
- `rv_enum_types`、`wr_perm_fatal`、`wr_null_raises` 仍为 1（T3）；
- 若同时采纳 §3.3 的词表放宽（v4rvb），`ok_object_value`、`ok_map_settings` 变为 1，其余不变。

**修复验收**：
- 新版本（建议记为 v5，父版本为 v4 `91baa55d…`）要做一轮正式诊断评分，覆盖：
  - noop、gold、作者 18 个候选、首轮复核者的 3 个候选；
  - 本复核的 `wr_zip_misalign`、`wr_zip_misalign_orempty`、`wr_all_files`；
  - 若采纳 v4rvb，再加 `ok_object_value`、`ok_map_settings`。
- 私有对照再以 root 跑一遍。

## 6. 非阻断建议

1. **原因词表放宽为 `dict`、`map`、`key`、`object` 或类型名（v4rvb，§3.3）**。这与 N3 是同一问题，建议与 B2 同批修改。若不修改，至少把 `ok_object_value`、`ok_map_settings` 写进 result.md §7。
2. **§7 的 T3 补登**：
   - `wr_perm_fatal`：权限错误致命，`c.yaml` 检查拦不住，可选加固见 §3.1；
   - `wr_null_raises`：显式 `null`、`~`、只含 `---` 与注释的文件报错；
   - `gr_csafe_loader`，以及 `{exc!r}` 加 `from None` 的写法：原因检查依赖纯 Python 版 PyYAML 的文字；
   - `gr_attr_wrap`：灰区，原因文字就是原来的 `AttributeError`，但含类型名，不判错。
3. **R-f 措辞**：改为 “when the contents of a Dask configuration file cannot be used …”，由新公开读者核对，看会不会有人把“读不到”理解为“应报错”（§3.5）。
4. **result.md 的文字更正**：
   - §4 “草案演进”表 v4 行的“漏过的候选：无”需要更新：`rv_enum_types` 在 v4 为 1（T3），本复核又发现了 §4.1 中 v4 列为 1 的错误候选；
   - §4 断言表第 6 行“拦下的候选”的措辞（§3.5）。

## 7. 未查事项

- **正式评分**：按任务要求没有运行。本复核的候选、v4rva 和 v4rvb 只有私有模拟评分，身份是 nobody（UID 65534）与 root，没有在 UID 54322 的正式 profile 下跑过。
- **尚未进行的环节**：真实模型候选、R-f 的新公开读者验收、Codex 复核（含 P5）。
- **上游 wheel 佐证**：断网，未复核。
- **平台差异**：没有核对 `/tmp` 为符号链接的平台（如 macOS）。在那里，用 `realpath` 输出路径的实现可能过不了“路径原样出现在消息里”的检查；评分镜像里的 `/tmp` 不是符号链接，本环境不受影响。
- **判断者**：`gr_attr_wrap` 与 `gr_basename_only` 的灰区判断只代表本复核的意见，没有交第三方裁定。
- **复现命令**：在 `rh2/experiments/category3_cloud_20260929/dask8801/review_v4/` 下依次运行：
  - `python3 make_review_candidates.py <evidence>/base/config.py .`
  - `python3 make_review_tests.py <evidence>/base/test_config.py ../test_config_revised_v4.py .`
  - `python3 run_review.py out/private <版本名…>`
  - `python3 score_review.py out/private`
  - `python3 summarize_behavior.py out/private`

  其中 `<evidence>` 是本题的 `evidence/` 目录；`run_review.py` 启动容器前会先等本机运行中的容器少于 3 个。
