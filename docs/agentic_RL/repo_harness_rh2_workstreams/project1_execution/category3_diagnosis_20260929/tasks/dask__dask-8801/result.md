# dask__dask-8801：第3类诊断结果

2026-09-29 / Claude（云端，第3类第二批主审子代理）。原分类：第3类“已有具体疑点，缺辨别实验”。登记的下一步是：只把报错文字换成同义措辞，保留路径、异常类型和原因，运行公开行为检查与正式评分，核实隐藏测试会不会误拒（T1）。

> **当前状态（09-30 更新）**
>
> - **v4 已完成正式诊断评分与私有对照，结果与预期逐项一致**（09-30 重跑，证据在 `evidence/rerun_0930/`）：
>   - 正式评分 23 次：gold 与 7 个合理实现为 1；noop、2 个另一政策候选与 12 个错误候选为 0。v3 漏过的 `oserr_fatal`、`rv_dir_only` 在 v4 为 0，v3 误拒的 `rv_kv_pairs` 在 v4 为 1；
>   - 私有对照 24 个版本（base、gold、18 个作者候选、4 个复核者候选）：以 nobody 与 root 两种身份运行 v4 测试，按参考名单计分，与正式评分一致；只做私有对照的 `rv_enum_types` 为 1，是已登记的 T3（N5）；
>   - 复核者 3 个候选的原材料正式评分已补：`rv_kv_pairs` 0、`rv_dir_only` 1、`rv_import_warn` 1，与复核者当初的私有结果一致。
> - **还差**：v4 的聚焦复核（由新的独立复核者按 review.md 进行，原复核者的上下文已不可用）；R-f 修订题面的新公开读者验收；Codex 复核（含 P5 第一分支的判断）。

**结论：问题和修法已明确；v4 正式诊断评分符合预期，待聚焦复核通过后转第2类。** 独立复核的意见是“部分同意”：诊断成立，P5 按第一分支处理也成立，另有 1 项阻断和 5 条非阻断意见。本页已按负责人的决定改为修订版 **v4**，v3 留档。

- **T1 已坐实（正式评分）**：7 个合理实现在原材料上都正式得 0，在 v4 上都正式得 1。其中 6 个是作者写的，第 7 个是复核者的 `rv_kv_pairs`。
  - 只改措辞的 `syn_repr`：消息里有带引号的路径、解析器原因和类型名，异常仍是 `ValueError`，失败在 `assert "is malformed" in ...`。
  - 措辞与 gold 逐字相同、只去掉路径引号的 `gold_plain`：失败在 `assert repr(fil_path) in ...`。
  - 其余 5 个：换成 `TypeError`；显式异常链；让 PyYAML 自带文件名；措辞与引号都改；复核者的 `rv_kv_pairs`（自定义 `ValueError` 子类，消息写 “must contain key: value pairs”）。
- **S1：原测试放过 7 个错误或不完整的实现，它们都得 1。**
  - 只拒 `list`：题面原例的顶层 `str` 仍在 `import dask` 时报原来的 `AttributeError`；
  - 只拒 `list` 与 `str`；
  - 空文件或全注释文件也报错；
  - 只包装 `ParserError`；
  - 报错点名了错误的文件；
  - 模块导入时吞掉错误；
  - 不可读的条目变成致命错误。

  另有复核者构造的 `rv_dir_only`（直接给出的文件路径不校验）在原材料上也正式得 1，属边缘情形，本轮一并修。
- **P5 按第一分支处理，不交用户（复核同意）**：出错时报错还是警告后跳过，测试采用的“报错”读法有公开依据（§3 依据 1、2），走 R-f 补一句说明。
- **v4 修法**：
  - R-b＋R-c 测试补丁，测试编号不变；
  - R-f 在题面末尾补一句；
  - **不再追加 P2P**，落地只需 D6 的“测试补丁替换”和 `statement_replace`。
- **v4 诊断评分（正式链，23 次：noop、gold 与 21 个候选）**：gold 与 7 个合理实现为 1；noop、2 个另一政策候选与 12 个错误候选为 0。v3 曾漏过 `oserr_fatal`、`rv_dir_only`（均为 1），并误拒 `rv_kv_pairs`（为 0），v4 都已纠正。

## 1．公开要求

题面是一份求助报告，标题为“Dask config fails to load”。报告者新建 conda 环境、安装 dask 后，`import dask` 失败。调用栈经 `refresh → collect → merge → update` 走到 `for k, v in new.items()`，报 `AttributeError: 'str' object has no attribute 'items'`。报告者问：“Any idea of what is happening?”

题面没有说修好后应当怎样，也没有给出坏文件的内容。下表逐项列出公开材料对各个验收约束的支持程度（base 为 `9634da11`）。

| 约束 | 公开依据 | 判断 |
| --- | --- | --- |
| 顶层不是映射的配置文件要在读取处识别，不能拖到 `update` 里崩溃 | 调用栈；`collect_yaml` 标注返回 `list[dict]`（`dask/config.py:150`）；`update`／`merge` 的参数是 `Mapping`；文档里的配置文件都是键值映射 | 成立 |
| 出错时报错，而不是警告后跳过 | 见 §3 的 P5 分析 | 测试的读法有公开依据，用 R-f 写明 |
| 报错点名出问题的文件 | 配置从多处搜索：`_get_paths` 包括 `/etc/dask`、`sys.prefix/etc/dask`、`~/.config/dask`、`DASK_CONFIG`（文档 `configuration.rst`）。报告者恰恰不知道是哪个文件坏了 | 成立。§2 的 `wrong_file` 说明，点错文件比不点名更误导 |
| 点名要求同样适用于直接给出的文件路径 | `collect_yaml` 的 `else: file_paths.append(path)`；P2P `test_collect_yaml_paths` 直接传文件；`DASK_CONFIG` 可以指向文件 | 成立（复核 N2） |
| 报错说明原因 | 报告者问“what is happening”。base 解析失败时本就显示 PyYAML 的原因，丢掉它属于退步 | 成立（按语义检查） |
| YAML 语法错误也要点名文件 | 标题“config fails to load”的一般理解。base 下语法错误同样中止 `import dask`，但消息写的是 `in "<unicode string>"`，不含文件名（私有对照已实测） | 原测试已经要求。题面没有直接写，属于 P3，由 R-f 写明 |
| 异常类型必须是 `ValueError` | `dask/config.py` 里唯一的先例是 `check_deprecations` 对已删除键抛 `ValueError`。题面未提 | **无唯一依据**：`TypeError`、PyYAML 自己的异常同样合理 |
| 消息含 `is malformed`、`original error message`、`must have a dict` | 无 | **无依据（T1）** |
| 路径带 `repr` 引号 | 无 | **无依据（T1）** |
| 空文件、全注释文件照常加载 | 文档 `configuration.rst` 写明下游库用 `ensure_file(source=fn, comment=True)` 把默认配置以全注释形式复制到 `~/.config/dask/`；base 对它们返回空配置 | 成立：既有的、有文档的行为 |
| 读不到的条目照常忽略 | `collect_yaml` 两处 `except OSError: # Ignore permission errors`；公开测试 `test_collect_yaml_permission_errors[directory|file]` | 成立：既有的、有公开测试的行为。v4 用“配置目录里名为 `c.yaml` 的子目录”检查，与是否 root 无关 |

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
- 原材料的哈希：gold `e8124cc2…5ce8`；test_patch `43d46603…29a1`；题面 `aabbe2d7…cc8a`。三者都与 ingest 一致。
- 候选由 [`make_candidates.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask8801/make_candidates.py) 生成：先在内存里套上 gold，再逐处替换，每处都断言恰好命中一次。内存 gold 与官方 gold 经 `git apply` 后的结果逐字相同，sha256 为 `ad89a854…`。各候选的 sha256 见 `candidates.json`。
- **复核者的候选**：复核者的补丁未入库，本页的 `rv_*` 按 review.md 附录的文字描述重建。
  - `rv_enum_types` 与复核者的补丁逐字节相同（`5b03ae4c…`）。
  - `rv_kv_pairs`、`rv_dir_only`、`rv_import_warn` 是等效重建，哈希与复核者的不同。
  - `rv_dir_only` 首次重建（`c23637bc…`）用了 `set()`，而 `dask.config` 里的 `set` 被同名上下文管理器遮蔽，结果连 P2P 都通不过，已作废。改用 `builtins.set()` 后重建为 `dcb3bea8…`，所有分数都用重建版重跑。09-29 作废的 `*_setbug` 运行未归档；09-30 重跑只用重建版。

### （1）私有行为对照

在 root、断网的一次性容器中运行，工具是 `semantic_control.py`：
- v1–v3 使用 [`behavior.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask8801/behavior.py)；
- v4 使用 [`behavior_v4.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask8801/behavior_v4.py)，比前者多两项：配置目录里有一个名为 `c.yaml` 的子目录；新进程 `import dask` 时 `DASK_CONFIG` 直接指向坏文件。

pytest 以 nobody（UID 65534）运行；v4 测试另以 root 再跑一遍。

**证据范围**：v1–v3 的运行在 `evidence/semantic_v1/`–`semantic_v3/`，其中 `semantic_v3/` 覆盖 base、gold 与 18 个作者候选。下表中“目录里的 `c.yaml` 子目录”“import：`DASK_CONFIG` 直指坏文件”两列，以及 4 个复核者候选的行，来自 `behavior_v4.py` 的运行（09-30 重跑，`evidence/rerun_0930/semantic_v4/`，24 个版本），负责人已逐格核对。复核者候选的行为另见 review.md §3 中复核者本人的私有探针。

表中“无路径”指异常消息不含该文件的路径。“新进程 import”在隔离 `HOME` 与 `DASK_ROOT_CONFIG` 后，让 `DASK_CONFIG` 指向对应目录或文件。

| 候选 | 顶层 `str`／`list`／`int` | 语法错误 `{`／制表符 | 空文件／全注释 | 坏 a.yaml＋好 b.yaml | 目录里的 `c.yaml` 子目录 | import：目录含坏 str | import：`DASK_CONFIG` 直指坏文件 | import：全注释默认配置 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base | AttributeError 无路径（三者） | ParserError／ScannerError，无路径 | 正常 | AttributeError | 跳过 | rc=1，`AttributeError` | rc=1，`AttributeError` | rc=0 |
| gold | ValueError（三者） | ValueError／ValueError | 正常 | ValueError 点名 a | 跳过 | rc=1，点名文件 | rc=1，点名文件 | rc=0 |
| **合理实现** | | | | | | | | |
| `syn_repr`：只改措辞 | 同 gold | 同 gold | 正常 | 点名 a | 跳过 | rc=1 | rc=1 | rc=0 |
| `gold_plain`：只去掉路径引号 | 同 gold | 同 gold | 正常 | 点名 a | 跳过 | rc=1 | rc=1 | rc=0 |
| `syn_plain`：措辞与引号都改 | 同 gold | 同 gold | 正常 | 点名 a | 跳过 | rc=1 | rc=1 | rc=0 |
| `typeerror`：顶层非映射抛 `TypeError` | TypeError（三者） | ValueError | 正常 | 点名 a | 跳过 | rc=1 | rc=1 | rc=0 |
| `chain_cause`：`raise ... from exc` | ValueError | ValueError，原因在 `__cause__` | 正常 | 点名 a | 跳过 | rc=1 | rc=1 | rc=0 |
| `stream_load`：`yaml.safe_load(f)`，语法错误不包装 | ValueError | ParserError／ScannerError，**消息含文件路径与行列** | 正常 | 点名 a | 跳过 | rc=1 | rc=1 | rc=0 |
| `rv_kv_pairs`（复核者）：`ConfigFileError(ValueError)`，“must contain key: value pairs” | ConfigFileError | ConfigFileError，`from exc` | 正常 | 点名 a | 跳过 | rc=1 | rc=1 | rc=0 |
| **另一种政策** | | | | | | | | |
| `warn_skip`：警告（含路径、原因）并跳过 | 跳过，1 条警告 | 跳过 | 正常 | 只加载 b | 跳过 | **rc=0** | rc=0 | rc=0 |
| `rv_import_warn`（复核者）：API 抛错；导入时警告并只跳过坏文件 | 同 gold | 同 gold | 正常 | 点名 a | 跳过 | **rc=0**（警告，其余配置生效） | rc=0 | rc=0 |
| **错误或不完整** | | | | | | | | |
| `silent_skip`：静默跳过 | 跳过，无诊断 | 跳过 | 正常 | 只加载 b | 跳过 | rc=0 | rc=0 | rc=0 |
| `lists_only` | **str、int：AttributeError 无路径** | ValueError | 正常 | str：AttributeError | 跳过 | **rc=1，仍是原 `AttributeError`** | rc=1，无路径 | rc=0 |
| `str_only` | list、int：AttributeError | ValueError | 正常 | ValueError | 跳过 | rc=1 | rc=1 | rc=0 |
| `list_str_only` | **int：AttributeError 无路径** | ValueError | 正常 | ValueError | 跳过 | rc=1 | rc=1 | rc=0 |
| `none_raises`：去掉 `None` 例外 | ValueError | ValueError | **ValueError** | ValueError | 跳过 | rc=1 | rc=1 | **rc=1**（点名 `dask.yaml`） |
| `oserr_fatal`：去掉 `OSError` 例外 | 同 gold | 同 gold | 正常 | 点名 a | **ValueError（Is a directory）** | rc=1 | rc=1 | rc=0 |
| `typeonly`：不包装语法错误 | ValueError | **ParserError／ScannerError 无路径** | 正常 | 点名 a | 跳过 | rc=1 | rc=1 | rc=0 |
| `noreason`：只给路径 | ValueError，无原因 | ValueError，`from None` 隐去解析器原因 | 正常 | 点名 a | 跳过 | rc=1 | rc=1 | rc=0 |
| `parsererror_only`：只包装 `ParserError` | ValueError | ValueError／**ScannerError 无路径** | 正常 | 点名 a | 跳过 | rc=1 | rc=1 | rc=0 |
| `wrong_file`：读完再查，用循环变量报路径 | ValueError | ValueError | 正常 | **点名 b.yaml** | 跳过 | rc=1 | rc=1 | rc=0 |
| `import_swallow`：`collect_yaml` 同 gold，模块导入时捕获并警告 | 同 gold | 同 gold | 正常 | 点名 a | 跳过 | **rc=0**（用户配置全部丢弃） | rc=0 | rc=0 |
| `rv_dir_only`（复核者）：只校验目录里找到的文件 | 目录：同 gold；**直接给文件：AttributeError 无路径** | 目录：同 gold；直接给文件：原异常 | 正常 | 点名 a | 跳过 | rc=1，点名文件 | **rc=1，原 `AttributeError`，无路径** | rc=0 |
| `rv_enum_types`（复核者，只做私有对照）：只拒 list、str、int | ValueError | ValueError | 正常 | ValueError | 跳过 | rc=1 | `1.5`：rc=1，`AttributeError: 'float'…`，无路径 | rc=0 |

**补充事实**：

- `key value`（漏写冒号）这样的文件会被 PyYAML 读成顶层 `str`，这是题面崩溃最可能的来源。制表符缩进、`a: b: c` 这类常见错误抛的是 `ScannerError`，不是 `ParserError`。
- 以 root 运行时，两个权限测试在 base 上就失败（`semantic_root_perm/`），原因是 root 不受 `chmod` 限制，这很可能就是来源参考名单没有收录它们的原因。v4 的 `c.yaml` 子目录检查不依赖权限：`open()` 在 root 下同样抛 `IsADirectoryError`。
- base 的公开 `test_config.py` 共 43 项。以 nobody 身份运行时，除 `oserr_fatal` 的 `[file]` 外，所有版本全部通过。

### （2）原材料正式评分

`replay_grade.py run`，原材料：F2P 2 项，P2P 41 项。共 23 次有效评分（noop、gold 与 21 个候选）：09-29 的 20 次在 `evidence/formal/`，复核者 3 个候选的 3 次是 09-30 补跑，在 `evidence/rerun_0930/formal/`。全部运行的共同情况：
- 参考缺席 0；
- 安装 rc=0；
- 测试段完整，解析出 45 项；
- 清理成功。

分数与失败位置见 §4 的汇总表“原材料”列。关键的失败位置（评分日志逐字）：

- `syn_repr`：两项都是 `assert "is malformed" in str(rec.value)`，消息为 `Invalid Dask configuration at '<路径>': while parsing a flow node ...` 与 `...: expected a mapping at the document root, got list`。
- `gold_plain`：两项都是 `assert repr(fil_path) in str(rec.value)`，消息是 gold 原句，只是路径不带引号。
- `typeerror`：`TypeError` 未被 `pytest.raises(ValueError)` 捕获。
- `stream_load`：`yaml.parser.ParserError`（消息含文件名）未被 `pytest.raises(ValueError)` 捕获。
- `warn_skip`：`UserWarning` 不是 `ValueError`。setup.cfg 有 `filterwarnings = error:::dask[.*]`，会把 dask 发出的警告升级为错误。

用 2×2 设计把两个因素分开：`syn_repr` 只改措辞，`gold_plain` 只改引号，两者分别得 0。因此英文词组和路径引号**各自都足以**让合理实现得 0。

## 3．判定（v1 §3–§4）

**T1（误拒合理解，走 R-b）**：

- 三个英文词组和 `repr` 引号没有任何公开依据，只改其中任一项的合理实现就正式得 0。
- `ValueError` 类型没有唯一依据：`typeerror` 与 `stream_load` 在文件点名、原因和既有行为上都合格，也得 0。
- `stream_load` 对语法错误保留了 PyYAML 自己的异常类，原先捕获 `yaml.YAMLError` 的调用方代码不受影响，兼容性反而更好。

**P5：报错还是警告后跳过，按第一分支处理（复核同意）。** 测试采用“报错”读法，公开依据有两条：

1. **旧行为**：base 下，PyYAML 解析不了的配置文件本就让 `import dask` 失败（私有对照：base 新进程 import 语法错误目录，rc=1）。
2. **跳过的范围**：`collect_yaml` 在同一函数里把两类问题分开处理。读不到的文件（`except OSError: # Ignore permission errors`，配套公开测试只针对不可读的目录和文件）被跳过；内容坏的文件让导入失败。没有文档、API 或旧测试说内容有问题的文件应当被跳过。

报告者问“what is happening”，这一点两边都能解读：可以理解为要诊断，也可以理解为想让 import 成功。因此它不作依据。“跳过”读法只能从权限错误的先例跨类别类推，与 dask-9378 中“只修顶层”的情形相同。

上游佐证（不作为公开依据）：PyPI 上的 dask 2022.3.0 与 2024.12.1 的 `_load_config_file` 与 gold 逐字相同，模块末尾仍是裸 `refresh()`，坏文件照样让 `import dask` 失败。两个 wheel 的 sha256 为 `52e9f8a4…8597`、`1f32acdd…8e19`。

如果 Codex 复核不同意第一分支，就交用户在 A（报错，即本草案）、B（警告并跳过）、C（不修订）中选择。选 B 的代价：
- gold 会抛错，不再是正对照，要按 D4 另找经独立核实的替代正对照；
- 两个 F2P 与导入断言都要反向重写。

**导入断言与 P5 同进同退（复核 N1，登记）**：

- v4 的新进程导入断言（`assert proc.returncode != 0`）只能靠 P5 第一分支立足。它与 R-f 中的 “including `import dask`” 同进同退：要撤就一起撤。
- 复核者的 `rv_import_warn`（API 抛错，导入时警告并只跳过坏文件、其余配置生效）在原材料上正式得 1，在 v3 上因这条断言得 0（复核者私有对照），在 v4 上正式得 0。它属于“另一种政策”，不是错误实现，被拒是 P5 裁定的直接结果。
- 作者的 `import_swallow` 另有与 P5 无关的缺陷：`refresh()` 整体失败后，全部 YAML 与环境变量配置都被丢弃。

**P3**：原测试要求语法错误也点名文件，超出了题面示例。它符合标题的一般理解，base 下语法错误同样中止导入却不点名文件，所以不判 T1，由 R-f 写明。

**S1（§4 第 4 步，D1 严格版）**：下列已构造的候选在原材料上正式得 1，但违反公开要求。

| 候选 | 违反的公开要求 | 严重度 |
| --- | --- | --- |
| `lists_only` | 题面原例的顶层 `str` 在 `import dask` 时仍报原 `AttributeError`。原测试用 `[1234]` 直接断言了“非映射顶层”，缺的是原例 `str` 这一实例 | S1（第 4 步；复核指出不属第 1 步，已改） |
| `list_str_only` | 顶层数字标量仍崩溃，属于同一核心要求的其它实例 | S1（按 D1 严格版计入；即使记作边缘输入，修法也只是在同一循环里多加一个实例） |
| `none_raises` | 破坏有文档的常用行为：下游库写入 `~/.config/dask/` 的全注释配置文件让 `import dask` 失败 | S1 |
| `parsererror_only` | 制表符缩进、`a: b: c` 等 `ScannerError` 仍不点名文件，属于同一要求的其它实例 | S1 |
| `wrong_file` | 坏文件不是最后一个时，报错点名的是另一个文件。多文件配置目录是常态 | S1 |
| `import_swallow` | 题面场景 `import dask` 仍然成功，坏文件连同全部用户配置被丢弃（按第一分支的读法） | S1（在导入路径上吞掉错误） |
| `oserr_fatal` | 读不到的条目变成致命错误，破坏有公开测试的既有行为。那两项权限测试不在参考名单内（T6） | S1 |
| `rv_dir_only`（复核者） | 直接给出文件路径时（`DASK_CONFIG` 指向文件、`collect_yaml(paths=[file])`），仍报原 `AttributeError` 且不点名文件 | 复核按第 4 步判为边缘（S2／T3）。修法只需一两行，本轮一并修 |

**不判问题的部分**：

- **G1**：gold 在 v3、v4 上都正式得 1，可以继续作正对照。
- gold 相对 base 有两处行为变化，公开材料都没有承诺，登记为 T3，不作处置依据：
  - 顶层假值（`0`、`false`、`[]`、`''`）由原来的静默当作空配置改为报错；
  - 空文件时 `collect_yaml` 的返回值由 `[{}]` 变为 `[]`，合并结果不变。

## 4．修法（交第2类）

### R-b＋R-c：修订版测试草案 v4

- 草案文件：[`revised_test_v4.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask8801/revised_test_v4.patch)，sha256 `91baa55d…b440`，由 `make_revised_test.py … v4` 生成。
- 父版本为原 test_patch `43d46603…29a1`；v3（`bf9ff681…1c48`）留档。
- 两个 F2P 的编号不变，测试命令、F2P／P2P 名单都不变，不追加 P2P。

| 断言 | 依据 | 拦下的候选 |
| --- | --- | --- |
| 语法错误两例（`{` 抛 `ParserError`，制表符抛 `ScannerError`），按目录和文件路径各加载一次：都要失败；消息含该文件路径，不要求引号；解析器给出的原因（`problem`）出现在消息或 Python 显示的异常链中 | R-b 替换两个词组和 `repr`；R-c 补 `ScannerError` 实例与直接文件路径 | noop、`typeonly`、`parsererror_only`、`noreason`、`silent_skip`、`warn_skip`、`rv_dir_only` |
| 顶层非映射三例（`[1234]`、`hello`、`1234`），按目录和文件路径各加载一次：都要失败；消息含该文件路径；去掉路径后的消息提到 `dict`、`mapping`、`key` 或实际类型名之一 | R-b 替换 `must have a dict`（`key` 对应 R-f 的 “mapping of keys to values”）；R-c 的 `str` 来自题面原例，数字来自一般表述 | noop、`lists_only`、`str_only`、`list_str_only`、`noreason`、`silent_skip`、`warn_skip`、`rv_dir_only` |
| 坏文件 `a.yaml` 之后有正常的 `b.yaml` 和 `c.yaml` 条目：报错必须点名 `a.yaml` | R-c | `wrong_file`（它点名的是最后一个条目） |
| 配置目录里有一个名为 `c.yaml` 的子目录（`open()` 抛 `IsADirectoryError`）、一个正常的 `b.yaml`，`a.yaml` 为空或全注释：加载结果为 `{"x": 1}` | 阻断 B1 的方案 1：读不到的条目照常跳过，与 base、gold 一致，与是否 root 无关；空文件与全注释文件的依据是 `configuration.rst` 与 base 行为 | `oserr_fatal`、`none_raises` |
| 检查“加载失败”时用 `warnings.catch_warnings()` 忽略警告 | 与 R-b 配套：否则 `pytest.raises(Exception)` 会把被 setup.cfg 升级的警告当成报错 | `warn_skip`（v1 漏过） |
| 新进程 `import dask`：`DASK_CONFIG` 指向含顶层 `str` 的目录，隔离 `HOME` 与 `DASK_ROOT_CONFIG`；要求导入失败，且 stderr 点名该文件 | 题面场景。依赖 P5 第一分支，与 R-f 的 “including `import dask`” 同进同退 | `import_swallow`、`rv_import_warn`、`warn_skip`、`silent_skip` |

异常类型放宽为任意异常，但警告不算。修订后仍受保护的公开要求：
- 报错并点名出问题的文件，目录与直接文件路径两种形态都算；
- 给出原因；
- 导入路径上同样报错；
- 空文件、全注释文件合法；
- 读不到的条目照常跳过；
- 正常映射的合并与优先级，由原 41 项 P2P 保护。

**`c.yaml` 检查的边界（复核 N4）**：它断言“`OSError` 一律忽略”，与 base 的 `except OSError` 一致，但比注释写的 “permission errors” 宽。只捕获 `PermissionError` 的实现会被拒，这本身是对 base 边缘行为的回归，可以接受。

**草案演进**（v1、v2 只做私有模拟；v3、v4 做了正式诊断评分）：

| 版本 | sha256 | 漏过的候选 | 原因与处理 |
| --- | --- | --- | --- |
| v1 | `20a52243…` | `warn_skip`（私有模拟得 1） | setup.cfg 把 dask 发出的 `UserWarning` 升级为异常，被 `pytest.raises(Exception)` 接住。v2 加入忽略警告 |
| v2 | `1101172e…` | `import_swallow`（私有模拟得 1） | 只测 `collect_yaml`，没测导入路径。v3 补新进程 `import dask` |
| v3（留档） | `bf9ff681…` | `oserr_fatal`、`rv_dir_only` 为 1；`rv_kv_pairs` 被误拒为 0 | 原拟追加 P2P 权限测试，但那两项在 root 下连 gold 都会失败（复核阻断 B1）；只测目录形态（N2）；词表没有 `key`（N3） |
| **v4** | `91baa55d…` | 无（已知候选范围内，09-30 正式评分确认） | 改用 `c.yaml` 子目录检查并撤掉 P2P 追加；每个实例另按文件路径加载；词表加 `key` |

### 诊断评分汇总（正式链）

- **原材料**：`replay_grade.py run`。
- **v3 与 v4**：`replay_with_install_recipe.py --materials materials_revised_v{3,4}.json`，评分器版本分别带后缀 `+c3-dask8801-diagnosis-semantics-v3`、`-v4`，F2P／P2P 名单与测试命令不变。
- 复核者的 3 个候选没有在 v3 上正式评分，表中 v3 列用私有模拟结果并标 *。
- 原材料与 v3 两列取自 09-29 的 `evidence/formal*/formal_summary.json`；复核者候选的原材料分数是 09-30 补跑的正式评分，与复核者的私有结果一致。
- v4 列取自 09-30 的 `evidence/rerun_0930/formal_revised_v4/`（逐次失败原因见同目录 `failure_reasons.txt`）。

| 候选 | 性质 | 原材料 | v3 | v4 |
| --- | --- | --- | --- | --- |
| noop | — | 0 | 0 | 0 |
| gold | 正对照 | 1 | 1 | **1** |
| `syn_repr`、`gold_plain`、`syn_plain`、`typeerror`、`chain_cause`、`stream_load` | 合理（作者） | 全 0 | 全 1 | 全 **1** |
| `rv_kv_pairs` | 合理（复核者） | 0 | 0* | **1** |
| `warn_skip` | 另一政策 | 0 | 0 | 0 |
| `rv_import_warn` | 另一政策（复核者） | 1 | 0* | 0 |
| `lists_only`、`list_str_only`、`none_raises`、`parsererror_only`、`wrong_file`、`import_swallow` | 错误 | 全 **1** | 全 0 | 全 0 |
| `oserr_fatal` | 错误 | **1** | **1** | 0 |
| `silent_skip`、`str_only`、`typeonly`、`noreason` | 错误 | 全 0 | 全 0 | 全 0 |
| `rv_dir_only` | 错误，边缘（复核者） | **1** | 1* | 0 |

原材料与 v3 各 20 次正式运行都是：参考缺席 0，安装 rc=0，测试段完整、解析出 45 项，清理成功；P2P 全部 41/41。

### R-f：修订题面草案 v1（未变；尚未由新公开读者验收）

草案文件：[`revised_statement_v1.txt`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask8801/revised_statement_v1.txt)。
- 父版本题面 sha256 为 `aabbe2d7…cc8a`，与 public bundle 的 `problem_statement_sha256` 一致；
- 修订后 sha256 为 `f6e85880…5375`；
- 只在末尾新增一段。原正文用 CRLF，新增段用 LF，落地时 `statement_replace` 要按字节保留（复核 N6）。

> Expected behavior: when a Dask configuration file cannot be used as configuration (for example, it is not valid YAML, or its top level is not a mapping of keys to values), loading the configuration, including `import dask`, should fail with an error that names the offending file and says what is wrong with it, instead of an unrelated error such as the `AttributeError` above.

逐句核对 R-f 边界：
- **没有写入隐藏测试的细节**：没有测试输入（`{`、制表符、`[1234]`、`hello`、`1234`、空文件、全注释、`c.yaml` 子目录），没有英文词组、异常类型或 helper 名。
- **每项要求都有依据**：
  - “报错”：§3 的 P5 依据 1、2；
  - “点名文件”：多处搜索路径；
  - “说明原因”：base 本就显示解析器原因；
  - “不是有效 YAML”：base 下同样中止导入；
  - “包括 `import dask`”：题面场景本身，与导入断言同进同退。
- **解题必需**：不写这句，报错还是跳过、语法错误是否在范围内，都要靠猜。

### 交接给第2类

1. 落地需要 D6 的两项能力：测试补丁替换（v4 补丁）、`statement_replace`（R-f）。不需要改参考分组。两项都不在首片内，情况与 dask-9378 相同。
2. 请一名新公开读者读修订后的题面，确认推出的需求与 v4 断言一致，并且不需要猜测隐藏细节。
3. 复验：
   - noop 0，gold 1；
   - 7 个合理实现为 1；
   - 2 个另一政策候选与 12 个错误候选为 0。
4. Codex 复核，其中包括 P5 第一分支的判断。
5. 正对照为 gold。7 个合理实现是作者或复核者自写的 T1 探针，不作正对照；若要用作正对照，须由他人独立核实。

## 5．当前用途（v1 §2，D6 落地前）

| 版本 | 问题定位 | 能力比较 | 训练候选 | 留出评测 |
| --- | --- | --- | --- | --- |
| 原版 | 是 | 否 | 否 | 否 |
| 修订版 | 经 D6 入库并通过验收后重新评估 | | | |

原版不能用于能力比较或训练，原因有两个：
- 合理实现因措辞、引号或异常类型得 0（T1）；
- 7 个错误实现得 1（S1）。

## 6．独立复核与处理

复核结论为“部分同意”，全文见 [review.md](review.md)，初判封存稿见 [review_initial.md](review_initial.md)。

- **同意的部分**：
  - 原版 T1 坐实；
  - 7 个错误实现得 1（S1）；
  - P5 按第一分支处理；
  - v3 的 40 份账本与日志逐一核对一致。
- **负责人对各项意见的决定及处理**：

| 项 | 内容 | 决定 | 处理 |
| --- | --- | --- | --- |
| B1（阻断） | 拦下 `oserr_fatal` 依赖三个条件：非 root 评分、尚未实现的改参考分组、只有推算。root 下 gold 在“41＋权限两项”口径下为 0 | 采用复核的方案 1 | v4 在 `test_collect_yaml_no_top_level_dict` 函数体内加 `c.yaml` 子目录检查，撤掉 P2P 追加。`oserr_fatal` 在 v4 正式得 0；私有对照中 v4 以 root 运行，gold 与 7 个合理实现为 1、`oserr_fatal` 为 0（按参考名单计分，root 下不在名单内的两项权限测试照常失败） |
| N1 | 导入断言只靠 P5 第一分支立足 | 登记 | §3 已写明它与 R-f 的 “including `import dask`” 同进同退，`rv_import_warn` 按第一分支被拒 |
| N2 | 没测直接文件路径，`rv_dir_only` 在 v3 得 1 | 采纳 | 每个实例另按文件路径加载一次，`rv_dir_only` 在 v4 正式得 0 |
| N3 | 按词判断“原因”会误拒 `rv_kv_pairs` | 采纳 | 词表加 `key`，`rv_kv_pairs` 在 v4 正式得 1；已知错误候选仍为 0 |
| N4 | `c.yaml` 检查比 “permission errors” 宽 | 随 B1 | 已写入 §4 的边界说明 |
| N5 | `rv_enum_types`（只拒 list、str、int）在 v3、v4 都得 1 | 不补 `1.5`，维持 T3 | 私有对照确认它在 v4 仍为 1；顶层 `1.5` 的文件直接给 `DASK_CONFIG` 时，导入报 `AttributeError: 'float'…` 且不点名文件。见 §7 |
| N6 | `lists_only` 应记第 4 步；R-f 的 CRLF／LF；stderr 中的 `dubious ownership` 提示 | 采纳 | 步号已改；落地按字节保留；该提示不影响断言 |
| 建议 4 | P5 只用依据 1、2 | 采纳 | §3 已改，依据 3 注明两边都能解读 |

v4 的评分已完成；尚待聚焦复核。

## 7．登记的缺口（T3，按 §8 抽查，本轮不修）

- **顶层假值**（`0`、`false`、`[]`、`''`）：gold 拒绝，base 当作空配置。公开材料没有承诺，修订版不做断言。
- **其它标量类型**（`float`、`bool`、日期等）：修订版只测 `int`。`rv_enum_types` 在 v3、v4 上仍为 1（v4 为私有对照结果；N5，负责人决定不补）。自然写法是 `not isinstance(x, dict)`，只有针对测试凑类型才会恰好枚举这三种。
- **非 UTF-8 或二进制配置文件**：会抛 `UnicodeDecodeError`，不做断言。
- **按词判断原因**：词表是 `dict`、`mapping`、`key` 或类型名，仍是词法检查。例如只写 “expected an object／got a sequence” 的消息会被拒，这是残余的 T1 风险。
- **`c.yaml` 检查要求一切 `OSError` 都被忽略**：只捕获 `PermissionError` 的实现会被拒，见 §4。
- **导入检查依赖运行环境**：要求评分环境的 `sys.prefix/etc/dask` 与 `site.PREFIXES` 下没有其它坏配置。本镜像中这些目录都不存在。

## 8．未做与证据

**未做**：
- v4 的聚焦复核；
- 真实 actor 开发条件；
- 模型求解；
- R-f 的新公开读者验收；
- root 身份下的正式评分。正式评分器固定以 UID 54322 运行；root 下只有私有对照：v3 只跑了 gold 与 noop；v4 的 24 个版本都跑过（`evidence/rerun_0930/semantic_v4/`）。

**证据**：
- 代码与运行环境：见 [环境说明](../../environment.md)。
- 候选补丁、生成脚本、修订草案：`rh2/experiments/category3_cloud_20260929/dask8801/`。v4 的测试文件是其中的 `test_config_revised_v4.py`。
- 原始证据：[evidence/](evidence/)。
  - `formal/`：原材料评分 20 次（noop、gold、18 个作者候选）；
  - `formal_revised_v3/`：v3 诊断评分 20 次；
  - `semantic_v1/`–`semantic_v3/`：私有对照；
  - `semantic_root_perm/`、`semantic_root_v3/`：root 下的权限测试与 v3 测试；
  - `testfiles/`：base、原版与 v1–v3 的 `test_config.py`；
  - 全部文件的 sha256 见 `evidence_manifest.json`。
  - `rerun_0930/`：09-30 重跑，含 `formal_revised_v4/`（23 次）、`formal/`（复核者 3 个候选）、`semantic_v4/`（24 个版本，含 `semantic_summary.json`）、`testfiles/`（含 v4 测试文件）、各目录的 `failure_reasons.txt`，以及本目录自己的 `evidence_manifest.json`。
- 09-29 作废的 `rv_dir_only_setbug` 运行未归档。
- v3 结论页留档：见提交 `d7afdce` 中的本文件。
