# dask__dask-8801：第3类诊断结果

2026-09-29 / Claude（云端，第3类第二批主审子代理）。原分类：第3类“已有具体疑点，缺辨别实验”。登记的下一步是：只把报错文字换成同义措辞，保留路径、异常类型和原因，运行公开行为检查与正式评分，核实隐藏测试会不会误拒（T1）。

**结论：问题和修法已明确，建议转第2类。独立复核尚未进行。**

- **T1 已坐实（正式评分）**：只改措辞的 `syn_repr` 得 0，失败在 `assert "is malformed" in ...`。它的消息里有带引号的路径、解析器原因和类型名，异常仍是 `ValueError`。只把路径的引号去掉、措辞与 gold 逐字相同的 `gold_plain` 也得 0，失败在 `assert repr(fil_path) in ...`。另外 4 个合理实现同样得 0：换成 `TypeError`、改用显式异常链、让 PyYAML 自带文件名，以及措辞和引号都改。
- **S1：原测试放过 7 个错误或不完整的实现，它们都得 1。**
  - 只拒 `list`：题面原例的顶层 `str` 仍然在 `import dask` 时报同一个 `AttributeError`；
  - 空文件或全注释文件也报错：文档描述的全注释配置文件会让 `import dask` 失败；
  - 只包装 `ParserError`：制表符缩进等 `ScannerError` 仍然不点名文件；
  - 报错时点名了错误的文件；
  - 模块导入时吞掉错误；
  - 不可读文件变成致命错误：只有两个不在参考名单里的权限测试会失败；
  - 只拒 `list` 与 `str`：顶层数字仍然崩溃。
- **P5 按第一分支处理，不交用户**：出错时是报错还是警告后跳过，测试采用的“报错”读法有公开依据（见 §3），所以走 R-f 补一句说明。**这是本页最需要复核的判断**：09-21 的三份审查都认为这一政策“未唯一规定”。
- **修法（草案）**：
  - R-b＋R-c 测试补丁 v3，测试编号不变；
  - 把两个现成的权限测试加入 P2P；
  - R-f 在题面末尾补一句。
  - 修订版诊断评分（正式链）：gold 与 6 个合理实现都是 1；noop、“警告并跳过”和 11 个错误候选中，除 `oserr_fatal` 外都是 0。`oserr_fatal` 在 v3 下仍是 1，要靠 P2P 加入权限测试才能拦下；按同一份正式日志推算，加入后为 0。

## 1．公开要求

题面是一份求助报告，标题为“Dask config fails to load”。报告者新建 conda 环境、安装 dask 后，`import dask` 失败。调用栈经 `refresh → collect → merge → update` 走到 `for k, v in new.items()`，报 `AttributeError: 'str' object has no attribute 'items'`。报告者问：“Any idea of what is happening?”

题面没有说修好后应当怎样，也没有给出坏文件的内容。下表逐项列出公开材料对各个验收约束的支持程度（base 为 `9634da11`）。

| 约束 | 公开依据 | 判断 |
| --- | --- | --- |
| 顶层不是映射的配置文件要在读取处识别，不能拖到 `update` 里崩溃 | 调用栈；`collect_yaml` 标注返回 `list[dict]`（`dask/config.py:150`）；`update`／`merge` 的参数是 `Mapping`；文档里的配置文件都是键值映射 | 成立 |
| 出错时报错，而不是警告后跳过 | 见 §3 的 P5 分析 | 测试的读法有公开依据，用 R-f 写明 |
| 报错点名出问题的文件 | 配置从多处搜索：`_get_paths` 包括 `/etc/dask`、`sys.prefix/etc/dask`、`~/.config/dask`、`DASK_CONFIG`（文档 `configuration.rst`）。报告者恰恰不知道是哪个文件坏了 | 成立。§2 的 `wrong_file` 说明，点错文件比不点名更误导 |
| 报错说明原因 | 报告者问“what is happening”。base 解析失败时本就显示 PyYAML 的原因，丢掉它属于退步 | 成立（按语义检查） |
| YAML 语法错误也要点名文件 | 标题“config fails to load”的一般理解。base 下语法错误同样中止 `import dask`，但消息写的是 `in "<unicode string>"`，不含文件名（私有对照已实测） | 原测试已经要求。题面没有直接写，属于 P3，由 R-f 写明 |
| 异常类型必须是 `ValueError` | `dask/config.py` 里唯一的先例是 `check_deprecations` 对已删除键抛 `ValueError`。题面未提 | **无唯一依据**：`TypeError`、PyYAML 自己的异常同样合理 |
| 消息含 `is malformed`、`original error message`、`must have a dict` | 无 | **无依据（T1）** |
| 路径带 `repr` 引号 | 无 | **无依据（T1）** |
| 空文件、全注释文件照常加载 | 文档 `configuration.rst` 写明下游库用 `ensure_file(source=fn, comment=True)` 把默认配置以全注释形式复制到 `~/.config/dask/`；base 对它们返回空配置 | 成立：既有的、有文档的行为 |
| 不可读的目录或文件照常忽略 | `collect_yaml` 两处 `except OSError: # Ignore permission errors`；公开测试 `test_collect_yaml_permission_errors[directory|file]` | 成立：既有的、有公开测试的行为 |

## 2．实测

### 环境与版本

- 镜像按原名拉取，得到 `xingyaoww/sweb.eval.x86_64.dask_s_dask-8801:latest`：
  - `RepoDigests` 为 `sha256:21e77aea…d48483`，与 ingest 冻结值一致；
  - 本机 image ID 为 `sha256:695d2cc2…`，已打标签 `c3keep/dask8801:src`；
  - 09-19 修复目录中没有本题，因此不用配方，也不用派生镜像。
- 镜像内是 Python 3.9.19、PyYAML 6.0.2、pytest 8.3.2。`distributed` 已安装但无法导入，不影响本题。`/etc/dask`、`sys.prefix/etc/dask`、`~/.config/dask` 都不存在。
- 代码：
  - 运行期间，分支 `claude/category3-20260929` 的 HEAD 从 `fb0b3de` 起经过负责人的几次快照提交。
  - 正式评分路径与 `a31cdcd` 逐字相同，已用 `git diff` 核对。核对范围是 `grading/`、`adapters/slime/replay_grade.py`、`prepared_task_face.py`、`envpack/`（R2E 摄入除外）和 `scripts/replay_grade.py`。
  - 诊断包装是 `semantic_control.py`（`b8cce4c3…`）和 `replay_with_install_recipe.py`（`fc570d89…`），与环境说明所记相同。
  - 评分 profile 为 UID 54322（`rh2grader`）、deny_all、2 CPU／4 GiB。
- 原材料的哈希：
  - gold `e8124cc2…5ce8`；
  - test_patch `43d46603…29a1`；
  - 题面 `aabbe2d7…cc8a`。

  三者都与 ingest 一致。
- 候选由 [`make_candidates.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask8801/make_candidates.py) 生成：先在内存里套上 gold，再逐处替换，每处都断言恰好命中一次。内存 gold 与官方 gold 经 `git apply` 后的结果逐字相同，sha256 为 `ad89a854…`。各候选的 sha256 见 `candidates.json`。

### （1）私有行为对照

在 root、断网的一次性容器中运行 [`behavior.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask8801/behavior.py)，工具是 `semantic_control.py`。pytest 以 nobody（UID 65534）身份运行，这样权限测试才有意义。

表中“无路径”指异常消息不含该文件的路径。“新进程 import”在隔离 `HOME` 与 `DASK_ROOT_CONFIG` 后，让 `DASK_CONFIG` 指向对应目录。

| 候选 | 顶层 `str`／`list`／`int` | 语法错误 `{`／制表符 | 空文件／全注释 | 坏 a.yaml＋好 b.yaml | 新进程 import：坏 str | 新进程 import：全注释默认配置 | 权限测试 [file] |
| --- | --- | --- | --- | --- | --- | --- | --- |
| base | AttributeError 无路径（三者） | ParserError／ScannerError，无路径 | 正常 | AttributeError | rc=1，`AttributeError` | rc=0 | 通过 |
| gold | ValueError（三者） | ValueError／ValueError | 正常 | ValueError 点名 a | rc=1，点名文件 | rc=0 | 通过 |
| **合理实现** | | | | | | | |
| `syn_repr`：只改措辞 | 同 gold | 同 gold | 正常 | 点名 a | rc=1 | rc=0 | 通过 |
| `gold_plain`：只去掉路径引号 | 同 gold | 同 gold | 正常 | 点名 a | rc=1 | rc=0 | 通过 |
| `syn_plain`：措辞与引号都改 | 同 gold | 同 gold | 正常 | 点名 a | rc=1 | rc=0 | 通过 |
| `typeerror`：顶层非映射抛 `TypeError` | TypeError（三者） | ValueError | 正常 | 点名 a | rc=1 | rc=0 | 通过 |
| `chain_cause`：`raise ... from exc` | ValueError | ValueError，原因在 `__cause__` | 正常 | 点名 a | rc=1 | rc=0 | 通过 |
| `stream_load`：`yaml.safe_load(f)`，语法错误不包装 | ValueError | ParserError／ScannerError，**消息含文件路径与行列** | 正常 | 点名 a | rc=1 | rc=0 | 通过 |
| **另一种政策** | | | | | | | |
| `warn_skip`：警告（含路径、原因）并跳过 | 跳过，1 条警告 | 跳过 | 正常 | 只加载 b | **rc=0** | rc=0 | 通过 |
| **错误或不完整** | | | | | | | |
| `silent_skip`：静默跳过 | 跳过，无诊断 | 跳过 | 正常 | 只加载 b | rc=0 | rc=0 | 通过 |
| `lists_only` | **str、int：AttributeError 无路径** | ValueError | 正常 | str：AttributeError | **rc=1，仍是原 `AttributeError`** | rc=0 | 通过 |
| `str_only` | list、int：AttributeError | ValueError | 正常 | ValueError | rc=1 | rc=0 | 通过 |
| `list_str_only` | **int：AttributeError 无路径** | ValueError | 正常 | ValueError | rc=1 | rc=0 | 通过 |
| `none_raises`：去掉 `None` 例外 | ValueError | ValueError | **ValueError** | ValueError | rc=1 | **rc=1**（点名 `dask.yaml`） | 通过 |
| `oserr_fatal`：去掉 `OSError` 例外 | 同 gold | 同 gold | 正常 | 点名 a | rc=1 | rc=0 | **失败** |
| `typeonly`：不包装语法错误 | ValueError | **ParserError／ScannerError 无路径** | 正常 | 点名 a | rc=1 | rc=0 | 通过 |
| `noreason`：只给路径 | ValueError，无原因 | ValueError，`from None` 隐去解析器原因 | 正常 | 点名 a | rc=1 | rc=0 | 通过 |
| `parsererror_only`：只包装 `ParserError` | ValueError | ValueError／**ScannerError 无路径** | 正常 | 点名 a | rc=1 | rc=0 | 通过 |
| `wrong_file`：读完再查，用循环变量报路径 | ValueError | ValueError | 正常 | **点名 b.yaml** | rc=1 | rc=0 | 通过 |
| `import_swallow`：`collect_yaml` 同 gold，模块导入时捕获并警告 | 同 gold | 同 gold | 正常 | 点名 a | **rc=0**（用户配置全部丢弃） | rc=0 | 通过 |

**补充事实**：

- `key value`（漏写冒号）这样的文件会被 PyYAML 读成顶层 `str`，这是题面崩溃最可能的来源。制表符缩进、`a: b: c` 这类常见错误抛的是 `ScannerError`，不是 `ParserError`。
- 以 root 运行时，两个权限测试在 base 上就失败（`semantic_root_perm/`），原因是 root 不受 `chmod` 限制。这很可能就是来源参考名单没有收录它们的原因。RH2 的评分以 UID 54322 运行，两项都通过。
- base 的公开 `test_config.py` 共 43 项。以 nobody 身份运行时，除 `oserr_fatal` 的 `[file]` 外，20 个版本全部通过。

### （2）原材料正式评分

`replay_grade.py run`，原材料：F2P 2 项，P2P 41 项。20 次评分（noop、gold 与 18 个候选）的共同情况：

- 参考缺席 0；
- 安装 rc=0；
- 测试段完整，解析出 45 项；
- 清理成功。

表中“权限 [dir]/[file]”是日志里两项未计分权限测试的状态。

| 候选 | reward | F2P | 权限 [dir]/[file] | 失败位置（评分日志逐字） |
| --- | --- | --- | --- | --- |
| noop | 0 | 0/2 | 通过／通过 | `yaml.parser.ParserError` 未被 `pytest.raises(ValueError)` 捕获；顶层 list 时 DID NOT RAISE |
| gold | 1 | 2/2 | 通过／通过 | |
| `syn_repr` | **0** | 0/2 | 通过／通过 | 两项都是 `assert "is malformed" in str(rec.value)`。消息为 `Invalid Dask configuration at '<路径>': while parsing a flow node ...` 与 `...: expected a mapping at the document root, got list` |
| `gold_plain` | **0** | 0/2 | 通过／通过 | 两项都是 `assert repr(fil_path) in str(rec.value)`。消息是 gold 原句，只是路径不带引号 |
| `syn_plain` | **0** | 0/2 | 通过／通过 | 同上两类 |
| `typeerror` | **0** | 1/2 | 通过／通过 | `TypeError` 未被 `pytest.raises(ValueError)` 捕获 |
| `chain_cause` | **0** | 0/2 | 通过／通过 | `is malformed` |
| `stream_load` | **0** | 1/2 | 通过／通过 | `yaml.parser.ParserError`（消息含文件名）未被 `pytest.raises(ValueError)` 捕获 |
| `warn_skip` | 0 | 0/2 | 通过／通过 | `UserWarning`（setup.cfg 把 dask 警告升级为错误），不是 `ValueError` |
| `silent_skip` | 0 | 0/2 | 通过／通过 | DID NOT RAISE |
| `lists_only` | **1** | 2/2 | 通过／通过 | |
| `str_only` | 0 | 1/2 | 通过／通过 | 顶层 list 时 DID NOT RAISE |
| `list_str_only` | **1** | 2/2 | 通过／通过 | |
| `none_raises` | **1** | 2/2 | 通过／通过 | |
| `oserr_fatal` | **1** | 2/2 | 通过／**失败** | 失败项不在参考名单内 |
| `typeonly` | 0 | 1/2 | 通过／通过 | 语法错误的 `ParserError` 未被捕获 |
| `noreason` | 0 | 0/2 | 通过／通过 | `is malformed` |
| `parsererror_only` | **1** | 2/2 | 通过／通过 | |
| `wrong_file` | **1** | 2/2 | 通过／通过 | |
| `import_swallow` | **1** | 2/2 | 通过／通过 | |

用 2×2 设计把两个因素分开：`syn_repr` 只改措辞，`gold_plain` 只改引号，两者分别得 0。因此“英文词组”和“路径引号”**各自都足以**让合理实现得 0。

## 3．判定（v1 §3–§4）

**T1（误拒合理解，走 R-b）**：

- 三个英文词组和 `repr` 引号没有任何公开依据，只改其中任一项的合理实现就正式得 0。
- `ValueError` 类型没有唯一依据：`typeerror` 与 `stream_load` 在文件点名、原因和既有行为上都合格，也得 0。`stream_load` 对语法错误保留了 PyYAML 自己的异常类，调用方原先捕获 `yaml.YAMLError` 的代码不受影响，兼容性反而更好。

**P5：报错还是警告后跳过，按第一分支处理。** 测试采用“报错”读法，公开依据如下：

1. **旧行为**：base 下，PyYAML 解析不了的配置文件本就让 `import dask` 失败（私有对照：base 新进程 import 语法错误目录，rc=1）。
2. **跳过的范围**：`collect_yaml` 里唯一的“跳过”是 `except OSError: # Ignore permission errors`，与之配套的公开测试只针对不可读的目录和文件。没有文档、API 或旧测试说内容有问题的文件应当被跳过。
3. **报告者的诉求**：报告者问的是“what is happening”，要的是诊断。

“跳过”读法只能从“报告者想要 import 成功”和“权限错误也被跳过”间接类推，与 dask-9378 中“只修顶层”的情形相同。

上游佐证（不作为公开依据）：PyPI 上的 dask 2022.3.0 与 2024.12.1 的 `_load_config_file` 与 gold 逐字相同，模块末尾仍是裸 `refresh()`，坏文件照样让 `import dask` 失败。wheel 的 sha256 分别为 `52e9f8a4…8597`、`1f32acdd…8e19`。

如果复核认为两种读法都有依据，本题就改为 P5 第二分支，交用户在三个选项中选择：

- A：报错，即本草案；
- B：警告并跳过，需要另写测试；
- C：不修订。

**P3**：原测试要求语法错误也点名文件，这超出了题面示例。它符合标题的一般理解，base 下语法错误同样中止导入却不点名文件，所以不判 T1，由 R-f 写明。

**S1（§4 第 1、4 步，D1 严格版）**：下列已构造的候选在原材料上正式得 1，但违反了公开要求。

| 候选 | 违反的公开要求 | 步 |
| --- | --- | --- |
| `lists_only` | 题面原例的顶层 `str` 在 `import dask` 时仍报原 `AttributeError`。原测试没有 `str` 实例 | 第 1 步（原例类型无直接断言，T2a）＋第 4 步 |
| `list_str_only` | 顶层数字标量仍崩溃，属于同一核心要求的其它实例 | 第 4 步。按 D1 严格版计入；即使记作边缘输入（T3），修法也只是在同一循环里多加一个实例 |
| `none_raises` | 破坏有文档的常用行为：下游库写入 `~/.config/dask/` 的全注释配置文件让 `import dask` 失败 | 第 4 步 |
| `parsererror_only` | 制表符缩进、`a: b: c` 等 `ScannerError` 仍不点名文件，属于同一要求的其它实例 | 第 4 步 |
| `wrong_file` | 坏文件不是最后一个时，报错点名的是另一个正常文件。多文件配置目录是常态 | 第 4 步 |
| `import_swallow` | 题面场景 `import dask` 仍然成功，坏文件连同全部用户配置被丢弃（按第一分支的读法） | 第 4 步（在导入路径上吞掉错误） |
| `oserr_fatal` | 不可读文件变成致命错误，破坏了有公开测试的既有行为。那两项测试不在参考名单内（T6） | 第 4 步 |

**不判问题的部分**：

- **G1**：gold 通过全部修订断言，可以继续作正对照。
- gold 相对 base 有两处行为变化：
  - 顶层假值（`0`、`false`、`[]`、`''`）由原来的静默当作空配置改为报错；
  - 空文件时 `collect_yaml` 的返回值由 `[{}]` 变为 `[]`，合并结果不变。

  公开材料对这两点都没有承诺，登记为 T3，不作处置依据。

## 4．修法（交第2类）

### R-b＋R-c：修订版测试草案 v3

- 草案文件：[`revised_test_v3.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask8801/revised_test_v3.patch)，sha256 `bf9ff681…1c48`，由 `make_revised_test.py … v3` 生成；
- 父版本为原 test_patch `43d46603…29a1`；
- 两个 F2P 的编号不变，测试命令不变。

| 断言 | 依据 | 拦下的候选 |
| --- | --- | --- |
| 语法错误两例（`{` 抛 `ParserError`，制表符抛 `ScannerError`）：加载失败；消息含该文件路径，不要求引号；解析器给出的原因（`problem`）出现在消息或 Python 显示的异常链中 | R-b 替换两个词组和 `repr`；R-c 补 `ScannerError` 实例 | noop、`typeonly`、`parsererror_only`、`noreason`、`silent_skip`、`warn_skip` |
| 顶层非映射三例（`[1234]`、`hello`、`1234`）：加载失败；消息含该文件路径；去掉路径后的消息提到 `dict`、`mapping` 或实际类型名 | R-b 替换 `must have a dict`；R-c 的 `str` 来自题面原例，数字来自一般表述 | noop、`lists_only`、`str_only`、`list_str_only`、`noreason`、`silent_skip`、`warn_skip` |
| 坏文件 `a.yaml` 之后放一个正常的 `b.yaml`：报错必须点名 `a.yaml` | R-c | `wrong_file` |
| 空文件、全注释文件照常视为空配置 | R-c；`configuration.rst` 与 base 行为 | `none_raises` |
| 检查“加载失败”时用 `warnings.catch_warnings()` 忽略警告 | 与 R-b 配套：`setup.cfg` 有 `filterwarnings = error:::dask[.*]`，否则 `pytest.raises(Exception)` 会把升级后的警告当成报错 | `warn_skip`（v1 漏掉，见下文） |
| 新进程 `import dask`：`DASK_CONFIG` 指向含顶层 `str` 的目录，隔离 `HOME` 与 `DASK_ROOT_CONFIG`；要求导入失败，且 stderr 点名该文件 | 题面场景 | `import_swallow`、`warn_skip`、`silent_skip` |

异常类型放宽为任意异常，但警告不算。修订后仍受保护的公开要求：

- 报错并点名出问题的文件；
- 给出原因；
- 在导入路径上同样报错；
- 空文件与全注释文件合法；
- 正常映射的合并与优先级，由原 41 项 P2P 保护；
- 权限错误照常忽略，由下文的 P2P 追加保护。

**草案演进**（v1、v2 只做了私有模拟，没有正式评分）：

| 版本 | 私有模拟中漏掉的候选 | 原因与处理 |
| --- | --- | --- |
| v1 `20a52243…` | `warn_skip`（得 1） | `setup.cfg` 把 dask 发出的 `UserWarning` 升级为异常，被 `pytest.raises(Exception)` 接住。v2 加入忽略警告 |
| v2 `1101172e…` | `import_swallow`（得 1） | 只测 `collect_yaml`，没测导入路径。v3 补上新进程 `import dask` |
| v3 `bf9ff681…` | `oserr_fatal`（得 1） | 失败的权限测试不在参考名单内，靠下面的 P2P 追加解决 |

### R-c：把两项现成的公开测试加入 P2P

追加以下两项：

- `dask/tests/test_config.py::test_collect_yaml_permission_errors[directory]`
- `dask/tests/test_config.py::test_collect_yaml_permission_errors[file]`

这属于改参考分组，`--materials` 不支持，所以没有做正式诊断评分。两项测试本来就在每次评分中执行，下文 v3 表的“推算”列直接取自同一份正式日志中这两项的状态。

**适用范围**：两项在 root 下运行时，连 base 都失败，所以只适用于非 root 的评分 profile（RH2 为 UID 54322）。

### 修订版诊断评分（正式链，v3）

用 `replay_with_install_recipe.py --materials materials_revised_v3.json` 评分。评分器版本带后缀 `+c3-dask8801-diagnosis-semantics-v3`，F2P／P2P 名单与测试命令不变。

20 次评分全部满足以下条件：

- 参考缺席 0；
- 安装 rc=0；
- 测试段完整，解析出 45 项；
- 清理成功；
- 候选补丁 sha256 与 `candidates.json` 一致。

“推算”列是在 v3 基础上再把两项权限测试加入 P2P 后的结果，按同一份日志逐项计算。

| 候选 | 原材料 | v3 reward | v3 F2P | 推算：v3＋P2P 追加 | v3 失败位置（评分日志逐字；“哪一例”由私有对照对应） |
| --- | --- | --- | --- | --- | --- |
| noop | 0 | 0 | 0/2 | 0 | 语法错误：`assert fil_path in str(rec.value)`，消息是 `while parsing a flow node ...`，不含路径；顶层非映射：`DID NOT RAISE <class 'Exception'>` |
| gold（正对照） | 1 | **1** | 2/2 | 1 | |
| `syn_repr` | 0 | **1** | 2/2 | 1 | |
| `gold_plain` | 0 | **1** | 2/2 | 1 | |
| `syn_plain` | 0 | **1** | 2/2 | 1 | |
| `typeerror` | 0 | **1** | 2/2 | 1 | |
| `chain_cause` | 0 | **1** | 2/2 | 1 | |
| `stream_load` | 0 | **1** | 2/2 | 1 | |
| `warn_skip` | 0 | 0 | 0/2 | 0 | 两项都是 `DID NOT RAISE <class 'Exception'>` |
| `silent_skip` | 0 | 0 | 0/2 | 0 | 同上 |
| `lists_only` | **1** | 0 | 1/2 | 0 | `DID NOT RAISE`（`hello` 一例） |
| `str_only` | 0 | 0 | 1/2 | 0 | `DID NOT RAISE`（`[1234]` 一例） |
| `list_str_only` | **1** | 0 | 1/2 | 0 | `DID NOT RAISE`（`1234` 一例） |
| `none_raises` | **1** | 0 | 1/2 | 0 | 空文件一例抛 `ValueError: ... got a NoneType instead` |
| `oserr_fatal` | **1** | **1** | 2/2 | **0** | v3 的 F2P／P2P 全部通过；未计分的 `permission_errors[file]` 失败 |
| `typeonly` | 0 | 0 | 1/2 | 0 | `assert fil_path in str(rec.value)`，消息是原 `ParserError`，不含路径 |
| `noreason` | 0 | 0 | 0/2 | 0 | `assert parse_error.value.problem in _displayed_error(...)`；`assert "dict" in rest or ...`，消息为 `invalid dask config file ''` |
| `parsererror_only` | **1** | 0 | 1/2 | 0 | `assert fil_path in str(rec.value)`，消息是 `while scanning for the next token`／`found character '\t' that cannot start any token` |
| `wrong_file` | **1** | 0 | 1/2 | 0 | `assert fil_path in msg`：消息点名的是 `b.yaml` |
| `import_swallow` | **1** | 0 | 1/2 | 0 | `assert proc.returncode != 0`，实际 `0 != 0` |

**合计**：

- gold 与 6 个合理实现在 v3 上都是 1。
- noop、`warn_skip` 与 11 个错误候选中，12 个在 v3 上正式得 0。
- `oserr_fatal` 在 v3 上仍为 1，把权限测试加入 P2P 后推算为 0。
- 原材料上得 1 的 7 个错误候选里，6 个已被 v3 拦下，第 7 个 `oserr_fatal` 要靠 P2P 追加。

审计记录 `formal_revised_v3/audit_*/materials.json`：原评分摘要 `sha256:4c2e4615…7370`，修订后评分摘要 `sha256:84b80660…fcf7eb`。

### R-f：修订题面草案 v1（尚未由新公开读者验收）

草案文件：[`revised_statement_v1.txt`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask8801/revised_statement_v1.txt)。

- 父版本题面 sha256 为 `aabbe2d7…cc8a`，与 public bundle 的 `problem_statement_sha256` 一致；
- 修订后 sha256 为 `f6e85880…5375`；
- 原文结尾是 LF，只在末尾新增一段：

> Expected behavior: when a Dask configuration file cannot be used as configuration (for example, it is not valid YAML, or its top level is not a mapping of keys to values), loading the configuration, including `import dask`, should fail with an error that names the offending file and says what is wrong with it, instead of an unrelated error such as the `AttributeError` above.

逐句核对 R-f 边界：

- **没有写入隐藏测试的细节**：
  - 没有测试输入（`{`、制表符、`[1234]`、`hello`、`1234`、空文件、全注释）；
  - 没有英文词组、异常类型或 helper 名。
- **每项要求都有依据**：
  - “报错”：§3 的 P5 依据；
  - “点名文件”：多处搜索路径；
  - “说明原因”：报告者的问题，以及 base 本就显示解析器原因；
  - “不是有效 YAML”：base 下同样中止导入；
  - “包括 `import dask`”：题面场景本身。
- **解题必需**：不写这句，报错还是跳过、语法错误是否在范围内，都要靠猜。

### 交接给第2类

1. 落地需要 D6 的三项能力：
   - 测试补丁替换（v3 补丁）；
   - 追加 P2P 两项（改参考分组）；
   - `statement_replace`（R-f）。

   三项都不在首片内，情况与 conan-14177、dask-9378 相同。
2. 请一名新公开读者读修订后的题面，确认推出的需求与 v3 断言一致，并且不需要猜测隐藏细节。
3. 复验：
   - noop 0，gold 1；
   - 6 个合理实现为 1；
   - `warn_skip` 与 11 个错误候选为 0，其中 `oserr_fatal` 依赖 P2P 追加。
4. Codex 复核。
5. 正对照为 gold。6 个合理实现是作者自写的 T1 探针，不作正对照；若要用作正对照，须由他人独立核实。

## 5．当前用途（v1 §2，D6 落地前）

| 版本 | 问题定位 | 能力比较 | 训练候选 | 留出评测 |
| --- | --- | --- | --- | --- |
| 原版 | 是 | 否 | 否 | 否 |
| 修订版 | 经 D6 入库并通过验收后重新评估 | | | |

原版不能用于能力比较或训练，原因有两个：

- 合理实现因措辞、引号或异常类型得 0（T1）；
- 7 个错误实现得 1（S1）。

## 6．登记的缺口（T3，按 §8 抽查，本轮不修）

- **顶层假值**（`0`、`false`、`[]`、`''`）：gold 拒绝，base 当作空配置。公开材料没有承诺，修订版不做断言。
- **其它标量类型**：`float`、`bool`、日期等，修订版只测了 `int`。
- **非 UTF-8 或二进制配置文件**：会抛 `UnicodeDecodeError`，不做断言。
- **直接传入文件路径**：私有对照已跑，各版本与目录路径一致，但测试里没有。
- **类型错误的原因检查按词判断**：若消息只写“must be a key-value object”，不含 `dict`、`mapping` 或类型名，就会被拒。这是残余的 T1 风险，估计很少见。
- **导入检查依赖运行环境**：要求评分环境的 `sys.prefix/etc/dask` 与 `site.PREFIXES` 下没有其它坏配置。本镜像中这些目录都不存在。

## 7．未做与证据

**未做**：

- 独立复核；
- 真实 actor 开发条件；
- 模型求解；
- R-f 的新公开读者验收；
- P2P 追加项的正式诊断评分（只从日志推算）；
- 修订测试在 root 下的表现只查了 gold 与 noop（`semantic_root_v3/`）：
  - v3 的两个 F2P 分别为通过和失败，与非 root 时一致；
  - 权限两项在 root 下失败，base 同样如此。

  其余候选在 root 下未查。

**证据**：

- 代码与运行环境：见 [环境说明](../../environment.md)。
- 候选补丁、生成脚本、修订草案：`rh2/experiments/category3_cloud_20260929/dask8801/`。
- 原始证据：[evidence/](evidence/)。
  - `formal/`：原材料评分，20 份账本与日志；
  - `formal_revised_v3/`：v3 诊断评分；
  - `semantic_v1/`、`semantic_v2/`、`semantic_v3/`：私有对照，v3 覆盖全部 20 个版本和 5 组测试；
  - `semantic_root_perm/`、`semantic_root_v3/`：root 下的权限测试与 v3 测试；
  - `testfiles/`：各版本 `test_config.py`；
  - 全部文件的 sha256 见 `evidence_manifest.json`。
