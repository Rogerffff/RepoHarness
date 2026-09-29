# dask__dask-8801：独立复核

2026-09-29，独立复核者（新会话，不继承作者上下文）。初判先于读作者材料写成并封存：[review_initial.md](review_initial.md)。

**总判断：部分同意。** 诊断主结论成立，并经独立复跑确认：原版 T1 误拒坐实、原测试放过 7 个错误实现（S1）、P5 按第一分支处理、转第 2 类。修订草案（v3＋P2P 追加＋R-f）在验收前还有 **1 个阻断项**：拦下 `oserr_fatal` 同时依赖三个条件——非 root 评分、尚未实现的 P2P 追加机制、没有正式评分过的推算。root 下评分时，gold 在这个口径下会得 0。另有 3 个非阻断缺口，都有具体候选作证据，修法各只需一两行：直接给文件路径的形态没测；按词判断“原因”会误拒一个照 R-f 原句写的合理实现；导入断言对 P5 的依赖需要登记。

## 1. 复核范围与方法

- **读**：先读原件（标准 v1、ingest 三件、09-21 既有调查、镜像内 `config.py`／`test_config.py`／`configuration.rst`），写完初判后才读 `revised_test_v3.patch`、`materials_revised_v3.json`；第三步读作者 `result.md`、`evidence/`（账本、20＋20 份正式日志）、`candidates.json`、`make_candidates.py` 中 `warn_skip`／`import_swallow` 两段、`revised_statement_v1.txt`。
- **跑**：
  - 环境：在一次性容器 `rv8801-review-*` 里跑，镜像 `c3keep/dask8801:src`，image ID `695d2cc28e30`，`--network none`。
  - 身份：同一组合分别以 root 和新建的非 root 用户 `rvuser`（UID 1001）运行。
  - 命令：`python -m pytest -p no:cacheprovider -n0 -rA --color=no dask/tests/test_config.py`，每次不到 1 秒。
  - 判分：按 F2P 2 项＋P2P 41 项；另外按两种追加口径各算一次：“＋权限两项”和“＋root 无关的 OSError 项”。
  - **这不是正式评分**：没有走 `replay_grade.py`，也没有用 `rh2grader` profile。容器用完即弃，`/testbed` 已恢复干净。
- **测试版本**：原 test_patch `43d46603…`；作者 v3 `bf9ff681…`；复核者变体 v3rv `e0be3233…`（未入库，改动见附录）。三份的 hash 与 ingest、`materials_revised_v3.json` 一致。
- **候选**：
  - base 与 gold；
  - 作者 18 个：patch 的 sha256 与 `candidates.json` 逐个一致；
  - 复核者 6 个：其中 `rv_oserr_fatal` 与作者 `oserr_fatal` 字节相同（sha256 `f5da83fe…`），算独立复现，不算新候选。

## 2. 逐条主张核对

| # | 作者主张 | 核对 | 结论 |
| --- | --- | --- | --- |
| 1 | T1：只改措辞的 `syn_repr`、只去引号的 `gold_plain` 在原版各自得 0 | 正式账本：两者 reward 0，F2P 0/2；复核者非 root 复跑结果相同 | 同意 |
| 2 | 另 4 个合理实现（`typeerror`、`chain_cause`、`stream_load`、`syn_plain`）原版得 0 | 账本与复跑一致 | 同意。复核者的 `rv_kv_pairs` 原版同样得 0 |
| 3 | 三个英文词组、`repr` 引号没有公开依据；`ValueError` 没有唯一依据 | 与初判 (b)(c) 一致；v3 已放宽为任意异常，R-f 不写类型 | 同意 |
| 4 | S1：7 个错误候选原版得 1 | 账本：`lists_only`、`list_str_only`、`none_raises`、`parsererror_only`、`wrong_file`、`import_swallow`、`oserr_fatal` 都是 reward 1、F2P 2/2；复跑一致。复核者的 `rv_dir_only`、`rv_enum_types` 原版也得 1 | 同意，而且证据更强。小修正：`lists_only` 应记第 4 步。原测试已用 `[1234]` 直接断言“非映射顶层”，缺的是题面原例 `str` 这一实例，不属于第 1 步的“无直接断言”（T2a）。不影响 S1 结论 |
| 5 | `none_raises` 破坏有文档的行为 | `configuration.rst` 写明下游用 `ensure_file(source=fn, comment=True)` 写入全注释文件 | 同意 |
| 6 | P5 按第一分支处理 | 见 §5。初判独立得出同一方向 | 同意。作者依据 3（“报告者要诊断”）偏弱，因为报告者的直接诉求是能 import，可两边解读；建议只以依据 1、2 立论 |
| 7 | P3：语法错误点名文件，由 R-f 写明 | base 实跑：`{` 抛 `ParserError`，消息里是 `in "<unicode string>"`，不含文件名，导入即失败 | 同意 |
| 8 | v3 正式评分：gold 与 6 个合理实现得 1；其余 12 个得 0；`oserr_fatal` 得 1 | 20 份 v3 账本：grader 后缀 `+c3-dask8801-diagnosis-semantics-v3`，uid 54322，参考缺席 0，清理成功，分数与表中一致；复跑 20 个版本全部一致 | 同意 |
| 9 | “推算”：v3 追加权限两项后 `oserr_fatal` 为 0，其余不变 | 20 份 v3 日志的 hash 与账本一致。只有 `oserr_fatal` 的 `[file]` 为 FAILED，其余版本两项都是 PASSED；复跑相同 | 推算成立。但只有 `[file]` 有区分力：gold 没改目录枚举那段代码，所以 `[directory]` 拦不下任何在 gold 修改位置上构造的候选 |
| 10 | 权限两项只适用于非 root | root 复跑：base、gold、`oserr_fatal` 两项全部 FAILED。gold 在“41＋2”口径下为 0 | 事实成立，处理不够，见阻断项 B1 |
| 11 | R-f 只在末尾追加一段，sha 为 `f6e85880…` | 字节级核对：原文是修订版的前缀，只追加一段（原正文用 CRLF，新增段用 LF）；sha 一致。句中没有测试输入、英文词组、异常类型或 helper 名 | 在边界内。但“says what is wrong with it”与 v3 的词表不完全对应，见 N3 |
| 12 | 导入检查要求评分环境中没有其它坏配置 | 镜像中 `/etc/dask`、`sys.prefix/etc/dask`、`/root/.config/dask` 都不存在 | 同意登记 |
| 13 | 上游 wheel 佐证 | 断网未核；作者已注明不作为公开依据 | 不影响结论 |
| 14 | 原版只作问题定位；修订版等 D6 落地后重评 | 符合 §2、§11 的 SWE-Gym 条 | 同意 |
| 15 | T3 登记：假值、其它标量、非 UTF-8、直接文件路径、按词判断、导入环境 | 复核者已为其中“直接文件路径”“按词判断”“其它标量”三项构造出具体候选并实跑 | 同意登记；前两项建议本轮顺手修（N2、N3） |

## 3. 复核者运行结果（非正式；非 root 为主）

| 候选 | 性质 | 原版 | v3 | v3＋权限两项 | v3rv＋新 OSError 项 | root 下 |
| --- | --- | --- | --- | --- | --- | --- |
| base | noop | 0 | 0 | 0 | 0 | 0 |
| gold | 正对照 | 1 | 1 | 1 | 1 | 41 项口径为 1；**加权限两项后为 0**；v3rv＋新项为 1 |
| 作者 6 个合理实现 | 合理 | 0 | 1 | 1 | 1 | 抽查 `syn_repr`：v3rv＋新项为 1 |
| 作者其余 11 个（`warn_skip` 与 10 个错误候选） | 另一政策或错误 | 6 个为 1 | 0 | 0 | 0 | 未跑 |
| `oserr_fatal`（作者与复核者相同） | 错误 | 1 | 1 | **0** | **0** | 41 项口径为 1；v3rv＋新项为 **0** |
| `rv_dir_only` | 错误：只校验目录里找到的文件 | 1 | **1** | **1** | 0 | 未跑 |
| `rv_enum_types` | 错误：只拒 list、str、int | 1 | **1** | **1** | **1** | 未跑 |
| `rv_import_warn` | 只在第一分支下算错 | **1** | 0 | 0 | 0 | 未跑 |
| `rv_kv_pairs` | 合理 | 0 | **0** | **0** | 1 | v3rv＋新项为 1 |
| `rv_kv_pairs_mapping` | 合理（对照） | 0 | 1 | 1 | 1 | 未跑 |

v3rv 在 v3 基础上改了三处（见附录）：词表加 `"key"`；每个非映射实例再以文件路径直接调用一次；新增“配置目录中名为 `c.yaml` 的子目录应被忽略”。

私有行为探针（`collect(paths=[目录或文件], env={})`，以及隔离 `HOME`／`DASK_ROOT_CONFIG` 后新进程 `import dask`）用来证明上面的“错误”确实违反公开要求：

- `rv_dir_only`：
  - 目录形态与 gold 相同；
  - 直接给文件时，`collect(paths=[bad.yaml])` 和 `DASK_CONFIG=<bad.yaml> import dask` 都报原来的 `AttributeError: 'str' object has no attribute 'items'`，rc=1，不点名文件（str、list、float、date 四种输入都一样）。
- `rv_enum_types`：顶层 `1.5` 或 `2020-01-01` 在 merge 里报 `AttributeError: 'float'…`、`'datetime.date'…`，不点名文件，import rc=1。
- `rv_import_warn`：
  - `collect_yaml`／`collect` 抛错与 gold 相同；
  - `import dask` 时对坏文件发出点名文件的 `UserWarning`（“…This file is ignored.”），只跳过这一个文件，其它文件与环境变量照常生效，rc=0。
- `rv_kv_pairs`：
  - 所有非映射顶层都抛 `ConfigFileError(ValueError)`，消息为 `Dask config file <路径> must contain key: value pairs at the top level, found [1234]`；
  - 语法错误抛 `Could not parse Dask config file <路径>`，并用 `from exc` 保留 PyYAML 原因；
  - import rc=1 且点名文件；空文件与正常映射不受影响。
- 新 OSError 项：配置目录里建一个名为 `c.yaml` 的子目录，`open()` 会抛 `IsADirectoryError`。base 与 gold 在 root 和非 root 下都返回 `{'y': 3}`（跳过它）；`oserr_fatal` 在两种身份下都抛 `ValueError … [Errno 21] Is a directory`。

## 4. 反例与新问题

- **N1：v3 的导入断言把 P5 收得比原测试更紧。**
  - 现象：原测试只要求 `collect_yaml` 抛错；“API 抛错、`import dask` 时警告并只跳过坏文件”的 `rv_import_warn` 在原版得 1，在 v3 因 `assert proc.returncode != 0` 得 0。
  - 作者用 `import_swallow` 说明这条断言有必要，但它另有与 P5 无关的缺陷：`refresh()` 整体失败，全部 YAML 与环境变量配置都被丢弃，混进了第二个因素。
  - 结论：导入断言只能靠 P5 第一分支立足。我同意第一分支，所以不阻断；但必须登记“R-f 句中 `including import dask` 与这条 rc 断言同进同退”。
- **N2：没有覆盖直接文件路径。**
  - `collect_yaml` 公开支持文件路径：代码里有 `else: file_paths.append(path)`，P2P 的 `test_collect_yaml_paths` 就传文件路径，`DASK_CONFIG` 也可以指向文件。v3 的全部实例只传目录，所以 `rv_dir_only` 在 v3 得 1。
  - 这个候选是构造的，不太自然，路径也不常用，按 §4 第 4 步属边缘（S2／T3）。但它现在已是“已知相关错误候选”，而修法只要每个实例多调用一次 `collect_yaml(paths=[fil_path])`：v3rv 中 `rv_dir_only` 变为 0，gold 与全部合理实现仍为 1。
- **N3：按词判断“原因”，会误拒一个照 R-f 原句写的合理实现。**
  - `rv_kv_pairs` 点了名，也说了原因（期望 `key: value pairs`，并给出实际内容），v3 只因消息里没有 `dict`／`mapping`／类型名而得 0。它的措辞正好顺着 R-f 句中的“a mapping of keys to values”。作者估计这类情况“很少见”，但 R-f 自己的措辞就在引导这种写法。
  - 词表加 `"key"` 后，`rv_kv_pairs` 为 1；作者其余 11 个错误或另一政策候选（含 `noreason`）在 v3rv 下仍为 0，`oserr_fatal` 由新 OSError 项拦下，与词表无关。
  - 词表终究是词法检查，“expected an object／got a sequence”这类措辞仍会被拒，这部分保持 T3 登记。
- **N4：`oserr_fatal` 的拦截方案脆弱（阻断项 B1 的依据）。**
  - 现行方案要同时满足三个条件：非 root 评分、D6 实现“改参考分组”、正式评分（目前只有推算）。
  - `[directory]` 对 gold 修改位置的候选没有区分力，在 root 下却同样会让 gold 失败。
  - 有 root 无关的替代：新 OSError 项在 root 和非 root 下都能拦下 `oserr_fatal`，gold 与合理实现在 root 下也得 1。如果把它写进某个 F2P 测试函数体，这一项连 P2P 追加都不需要。
  - 代价：它断言的是“`OSError` 一律忽略”（与 base 的 `except OSError` 一致），比注释里的“permission errors”宽。把捕获收窄为 `PermissionError` 的实现会被拒；这本身是对 base 边缘行为的回归，可以接受，但要写明。
- **N5：`rv_enum_types`（只拒 list、str、int）在 v3 和 v3rv 都得 1**，`float`、日期仍会崩。这与作者登记的“其它标量类型”T3 一致：自然写法是 `not isinstance(x, dict)`，只有针对测试凑类型才会恰好枚举这三种。可选修法是加一个 `1.5` 实例，不要求。
- **N6：小事项。**
  - `lists_only` 的步号应为第 4 步（见 §2 第 4 行）；
  - 原题面正文是 CRLF，追加段是 LF，落地时 `statement_replace` 要按字节保留；
  - 非 root 下，新进程 `import dask` 的 stderr 里夹有 versioneer 调 git 产生的 `dubious ownership` 提示，不影响断言。

## 5. P5：同意第一分支，不交用户

base 在同一函数里已经把两类问题分开处理：

- **读不到**（`OSError`，注释写明 “Ignore permission errors”，有公开测试）→ 跳过；
- **内容坏**（语法错误）→ 让 `import dask` 失败。实跑：base 下新进程 import 语法错误目录，rc=1。

“报错”读法因此有直接依据：同一函数、同一类输入的现行行为，外加 `list[dict]`／`Mapping` 的类型契约。“跳过”只能从权限错误的先例跨类别类推，达不到“两种读法都有依据”的程度。这是判断，不是无争议事实：09-21 三份审查写的是“未唯一规定”，说的是唯一性，没有说“跳过”有同等依据。

若 Codex 复核不同意第一分支，可沿用作者列出的 A（报错）、B（警告并跳过）、C（不修订）三个选项交用户。需要补充 B 的代价：gold 会抛错，在 B 下不再是正对照，需要按 D4 另找经独立核实的替代正对照；两个 F2P 与 N1 的导入断言都要反向重写。

## 6. 阻断项

- **B1：`oserr_fatal` 的拦截在验收前必须落实，不能停在“推算＋非 root 说明”。** 两种做法任选其一：
  1. **采用 root 无关的实例（推荐）**：把 N4 的 `c.yaml` 子目录断言写进某个 F2P 测试函数体；权限两项的 P2P 追加降为非 root 下的可选加固。
  2. **保留现方案**：修订版记录里写入“评分身份必须为非 root”这一硬前提，并附“在有效 profile 下 gold=1”的前置检查。

  无论哪种，都要在最终参考分组下正式评分，不能沿用推算。否则一旦用 root 评分，gold 就得 0，违背 §0“环境不会让正确解失败”。

## 7. 非阻断建议

1. **N3**：v3 的原因词表加 `"key"`，与 R-f 句“mapping of keys to values”对应。已实跑：不放过任何已知错误候选。
2. **N2**：每个非映射实例再以文件路径直接调用一次。已实跑：拦下 `rv_dir_only`，不影响 gold 与合理实现。
3. **N1**：在修订记录中把 `rv_import_warn` 列为“按 P5 第一分支拒绝”的候选，并注明 R-f 的 `including import dask` 与 rc 断言同进同退。
4. P5 依据只用作者的第 1、2 条，第 3 条删去或注明可两边解读。
5. `lists_only` 的步号改为第 4 步。
6. 可选：非映射实例加一个 `1.5`（N5）。
7. 以上改动若采纳，v3 应升为新版本，并重做 R-b／R-c 验收：noop 0、gold 1、6 个合理实现加 `rv_kv_pairs` 为 1，已知错误候选（含 `rv_dir_only`、`oserr_fatal`）为 0。仍需新公开读者读 R-f，并交 Codex 复核。

## 8. 证据

- 本复核只写了两个文件：本文件与 [review_initial.md](review_initial.md)。按任务约束，复核者的候选、脚本与日志留在会话临时目录，未入库；sha256 如下：
  - `rv_dir_only.patch` `f24b4dcc…`
  - `rv_enum_types.patch` `5b03ae4c…`
  - `rv_import_warn.patch` `a6c791f6…`
  - `rv_kv_pairs.patch` `079005d5…`
  - `rv_kv_pairs_mapping.patch` `c9089dc3…`
  - `rv_oserr_fatal.patch` `f5da83fe…`（与作者 `oserr_fatal.patch` 相同）
  - `test_v3rv.patch` `e0be3233…`
- 作者材料的核对依据：`evidence/formal/ledger_*.jsonl`、`evidence/formal_revised_v3/ledger_*.jsonl`，以及对应 `eval_logs/*.eval.log`（40 份日志的 sha256 与账本 `log.sha256` 逐一相等）。

## 附录：复核者候选与 v3rv 的关键改动（相对 base 或 gold）

```text
rv_dir_only     gold 的 _load_config_file 只用于目录枚举到的文件（from_dirs 集合）；
                直接给出的文件路径仍走 base 的 `yaml.safe_load(...) or {}`。
rv_enum_types   gold 中 `config is not None and not isinstance(config, dict)`
                → `isinstance(config, (list, str, int))`
rv_import_warn  gold ＋ collect_yaml/collect 增加 on_error="raise"；on_error="warn" 时
                warnings.warn(f"{exc}\n\nThis file is ignored.") 并跳过该文件；
                模块末尾 `refresh()` → `refresh(on_error="warn")`
rv_kv_pairs     class ConfigFileError(ValueError)；OSError → None；
                yaml.YAMLError → ConfigFileError(f"Could not parse Dask config file {path}") from exc；
                非 Mapping → ConfigFileError(f"Dask config file {path} must contain key: value
                pairs at the top level, found {config!r}")
rv_kv_pairs_mapping  同上，消息改为 "must contain a YAML mapping (key: value pairs) ..."
rv_oserr_fatal  gold 删去 `except OSError: return None`（与作者 oserr_fatal 字节相同）

v3rv（在 v3 上）：
  1) assert any(w in rest for w in ("dict", "mapping", "key", type_name))
  2) 每个非映射实例后追加：
       with pytest.raises(Exception) as rec: ... collect_yaml(paths=[fil_path])
       assert fil_path in str(rec.value)
  3) 新增 test_collect_yaml_unreadable_entry_ignored：目录内 b.yaml("y: 3") 与子目录 c.yaml，
     断言 merge(*collect_yaml(paths=[dir_path])) == {"y": 3}（本次作为追加 P2P 计分；
     建议落地时并入 F2P 函数体）
```
