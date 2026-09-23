# L2 · 参考 ID 脆弱题专项（SWE-Gym 10 题）

2026-09-16 夜 · 工作包 `L2_reference_ids` · 全部离线复算，未连任何远程机器、未启 Docker、未改数据文件与 `rh2/src`、`rh2/tests`。

## 0. 结论速览

- **10 题共 18 个缺席参考 ID，全部是 P2P；F2P 缺席 0。**
- **18/18 可证明一一映射，歧义 0。** 统一规则：参考 ID 恰等于日志实际 nodeid 的 `unicode_escape` 解码结果。
- 差异只在 **pytest nodeid 的 ASCII 转义层数**，不是测试没被收集或没执行：18 个对应的完整 nodeid 在 gold 与 empty 日志里都有 `PASSED` 摘要行。
- parser 复现无偏差：`swegym_parsers@242429c1` 对 **181 份**阶段一 gold 日志重算，与当时落盘的 `status_map.json` **逐条相等**（181/181）。
- 缺席参考 ID 的题**恰为**这 10 题（全量扫描确认）。另有 6 题"参考 ID 在场但状态非 PASSED/XFAIL"，全部是 `FAILED`，**无 SKIPPED / ERROR**（见 §5，只列不判）。
- 离线模拟：加上"缺席才回退、且要求唯一命中"后，10 题 gold 全部由 `RESOLVED_NO` 变 `RESOLVED_FULL`，**empty 侧 10 题仍全部 `RESOLVED_NO`**（F2P 仍失败），不会把 no-op 洗成通过。

## 1. 逐题结果

`collapsed` = 该完整 nodeid 所在的截断键在同一份日志里被几条摘要行写入（>1 即 dict last-wins，覆盖度有损）。
`ORIG`/`MAPPED` 用 Python `repr()` 展示；`'\\\\'` 表示字符串里有两个反斜杠。

| # | 任务 | 缺席数 | 差异类型 | 判定 | collapsed | gold/empty 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `getmoto__moto-5417` | 1 | E1 | 可证明一一映射 | 1 | PASSED / PASSED |
| 2 | `getmoto__moto-5545` | 1 | E1 | 可证明一一映射 | 1 | PASSED / PASSED |
| 3 | `getmoto__moto-5562` | 1 | E2 | 可证明一一映射 | 1 | PASSED / PASSED |
| 4 | `getmoto__moto-5701` | 1 | E2 | 可证明一一映射 | 1 | PASSED / PASSED |
| 5 | `getmoto__moto-6308` | 1 | E1 | 可证明一一映射 | 1 | PASSED / PASSED |
| 6 | `iterative__dvc-4185` | 1 | E3 | 可证明一一映射 | 1 | PASSED / PASSED |
| 7 | `modin-project__modin-6780` | 3 | E3 + T1 | 可证明一一映射 ×3 | 1,1,1 | PASSED / PASSED |
| 8 | `pandas-dev__pandas-48106` | 3 | E3 + T1 + **T2** | 键级可证明；**语义一对多** | 2 / 3 / 2（2017 / 2019 / 2018） | PASSED / PASSED |
| 9 | `pandas-dev__pandas-50319` | 1 | E3 + T1 | 可证明一一映射 | 1 | PASSED / PASSED |
| 10 | `pydantic__pydantic-8977` | 5 | E4 + E5（+V1 旁证） | 可证明一一映射 ×5 | 1×5 | PASSED / PASSED |

逐条 `原 ID → 映射 ID → 证据（日志路径:行号 + 原始行 repr）`：`id_mapping_proposals.json`（18 条，schema `rh2.l2.id_mapping_proposals.v0`）。

关键样本（repr）：

```
E1  ORIG   'tests/test_s3/test_s3_multipart.py::test_multipart_upload_with_copy_key[the-unicode-💩-key]'
    MAPPED 'tests/test_s3/test_s3_multipart.py::test_multipart_upload_with_copy_key[the-unicode-\\U0001f4a9-key]'
E2  ORIG   'tests/test_s3/test_s3.py::test_key_with_special_characters[/the-key-unîcode/test]'
    MAPPED 'tests/test_s3/test_s3.py::test_key_with_special_characters[/the-key-un\\xeecode/test]'
E3  ORIG   'tests/func/test_run_multistage.py::test_run_with_invalid_stage_name[\\]'
    MAPPED 'tests/func/test_run_multistage.py::test_run_with_invalid_stage_name[\\\\]'
E4  ORIG   'tests/test_types.py::test_constrained_bytes_too_long[âª¶â\x93²â½·01-False]'
    MAPPED 'tests/test_types.py::test_constrained_bytes_too_long[\\xe2\\xaa\\xb6\\xe2\\x93\\xb2\\xe2\\xbd\\xb701-False]'
E5  ORIG   'tests/test_types.py::test_default_validators[uuid_check-\x124Vx\x124Vx\x124Vx\x124Vx-result96]'
    MAPPED 'tests/test_types.py::test_default_validators[uuid_check-\\x124Vx\\x124Vx\\x124Vx\\x124Vx-result96]'
T1  ORIG   'pandas/tests/tslibs/test_parsing.py::test_is_iso_format[%Y\\%m\\%d'
    MAPPED 'pandas/tests/tslibs/test_parsing.py::test_is_iso_format[%Y\\\\%m\\\\%d'
    完整行  'PASSED pandas/tests/tslibs/test_parsing.py::test_is_iso_format[%Y\\\\%m\\\\%d %H:%M:%S-True]'
```

## 2. 差异类型分类与统计

| 代号 | 差异 | 出现题 | 缺席 ID 数 |
| --- | --- | --- | --- |
| E1 | 非 BMP 字符（U+1F4A9）→ `\U0001f4a9` ASCII 转义 | moto-5417 / 5545 / 6308 | 3 |
| E2 | latin-1 范围字符（U+00EE）→ `\xee` | moto-5562 / 5701 | 2 |
| E3 | 字面反斜杠被双写（`\` → `\\`） | dvc-4185、modin-6780、pandas-48106 / 50319 | 8 |
| E4 | bytes 参数逐字节 `\xNN` 转义（参考侧呈 latin-1 mojibake） | pydantic-8977 | 2 |
| E5 | 控制字符 U+0012 / U+0081 → 字面 `\x12` / `\x81` | pydantic-8977 | 3 |
| T1 | nodeid 含空格 → parser 按空白切分截断（参考侧也已截断） | modin-6780、pandas-48106 / 50319 | 7（与 E3 重叠） |
| T2 | 截断键碰撞：多条完整用例写同一键，dict last-wins | pandas-48106 | 3（与 E3/T1 重叠） |
| — | **Unicode NFC/NFD 规范化差异** | 无 | 0（全 216 题参考 ID 均为 NFC，`not_applicable`） |

按"每个缺席 ID 的主因"去重后：转义类（E1–E5）18 个，其中 7 个同时带空格截断（T1），3 个所在键还发生碰撞（T2）。

**统一规律（可执行）**：所有 18 条都满足

```python
original_reference_id == log_nodeid.encode("latin-1", "backslashreplace").decode("unicode_escape")
```

这与 pytest `_pytest.compat.ascii_escaped` 的行为一致（`bytes` 走 `decode('ascii','backslashreplace')`，`str` 走 `encode('unicode_escape')`）。换句话说：**镜像里的 pytest 做了 ASCII 转义，而 SWE-Gym 生成参考 ID 时的那次运行没有（或转义形态不同）。**

必须注意的三点：

1. **不能无条件对所有参考 ID 做解码/转义**。同一批任务里 `dask__dask-10972` / `dask__dask-6818` 的参考 ID 本身就带 `\n`、`\t` 转义序列且**直接命中**日志；实测这类参考 ID 一旦被解码（`\n` → 真换行）或被再转义（`\n` → `\\n`）就都对不上。所以规则必须是"**直接命中优先，只对缺席项回退一次，且唯一命中才采用**"。
2. **两个方向都成立，选哪个都行，但要各自验过**。反向"把参考 ID 用 `str.encode('unicode_escape')` 再比日志键"在这 18 条上同样 18/18 唯一命中；全池检查里两个方向的假别名数都是 **0**（"直接命中的参考，其解码/转义形式又是另一个键"的情况一次都没有）。本包把正向（解码日志键）作为推荐实现，因为它的全池歧义检查（`global_checks.json`）是按这个方向做的。
3. **潜在陷阱（未观测到，但留个记号）**：`parse_log_pytest_pydantic` 会删掉行内 `chr(1)`–`chr(31)`。本批日志里控制字符都是字面 `\x12` / `\x81` 四字符转义，所以不受影响；但若某次日志的 nodeid 带的是**真**控制字符，键会被静默截改，两个方向都救不回来。样例与说明见 `parser_samples/E5_control_char_escape.*`。

## 3. 建议处置（每题一行）

前提：本包只提供候选，**不改 expected、不改任何数据文件、不改 `rh2/src`**。全部 10 题 `disposition.state = needs_repair`（缺陷可复现、原因明确、修法可全池验证），记录见 `screening_records.json`。

| 任务 | 建议 |
| --- | --- |
| `getmoto__moto-5417` | 接受第二类 ID 映射（E1），修后 gold=FULL / empty=NO。 |
| `getmoto__moto-5545` | 同上（E1）。 |
| `getmoto__moto-5562` | 接受第二类 ID 映射（E2）。 |
| `getmoto__moto-5701` | 同上（E2）。 |
| `getmoto__moto-6308` | 接受第二类 ID 映射（E1）。 |
| `iterative__dvc-4185` | 接受第二类 ID 映射（E3）；同组另外 8 个参数不含反斜杠，唯一性无争议。 |
| `modin-project__modin-6780` | 接受 3 条映射（E3+T1）；该题另有 102 个参考 ID 本就落在碰撞截断键上，覆盖度问题按 §4 第 2 条统一处理。 |
| `pandas-dev__pandas-48106` | 接受 3 条映射（键级唯一），但**同时记 P2 欠验证**：这 3 个截断键分别折叠 2 / 3 / 2 条完整用例（共 7 条），实际只核到最后一条。 |
| `pandas-dev__pandas-50319` | 接受第二类 ID 映射（E3+T1）。 |
| `pydantic__pydantic-8977` | 接受 5 条映射（E4/E5）；该题 parser 走 `parse_log_pytest_pydantic` 行尾状态词分支，另见 §5 的 V1 形态。 |

如果不接受自动映射，替代方案（按推荐度排序）：

- **A（推荐）**：在 `envpack/scoring.py` 的 `parse_eval_log_v2` 里给参考 ID 匹配加"缺席 → `unicode_escape` 解码 → 唯一命中才采用"的回退，并把采用次数写进诊断字段（如 `reference_remapped`），reward 口径不变。落点在 `status_map = parser(segment)` 与 `get_eval_tests_report(...)` 之间（本机工作树约 `rh2/src/repoharness2/envpack/scoring.py:250-270`，行号会变，按函数名定位）。
  **实施前须协调**：`rh2/src/repoharness2/envpack/swegym_parsers.py` 目前还是**未跟踪**文件（`git status` 显示 `??`），`scoring.py` 有 **+158 行未提交改动**，`contracts/grading.py`、`grading/manager.py` 等也在 ` M` 状态——整条 v2 评分路径都还在别的会话的工作树里，本包只读、未改。
- **B**：在 ingest 阶段按镜像实际 nodeid 重生成参考集，产出带版本号的任务修订（第三类），与原版分别计数。成本高，且需要每题真跑一次镜像。
- **C**：排除这 10 题并记录原因。代价是丢掉 10 题（占阶段一有记录题的 5.5%），且同类问题会在新 ingest 里复发。

## 4. 需要用户决定的问题

1. **是否接受第二类 ID 映射，以及落在哪一层。** 映射证据齐全（18/18 唯一、全池无副作用），但它改变了"参考 ID 如何与日志对账"，属于评分语义相关改动，按协作协议应由用户决定。若接受，还需定：修在 scoring 的匹配层（方案 A，任务数据不动），还是形成带版本的任务修订（方案 B）。
2. **截断键碰撞（T2）的处置口径。** 这是比 10 题大得多的面：**72 题、505 个碰撞截断键，其中 388 个参考 ID 字面上就是一个碰撞键**（`modin-5940` / `modin-6937` 各 127 个，`modin-6780` 102 个，其中一个键折叠了 **108** 条完整用例）。这些参考 ID 现在只核到最后一条用例的状态，属于系统性**欠验证**（不会造成假失败，但会放过真回归）。是否要换 runner 输出（JUnit XML / CTRF）或改 parser 为"按完整行匹配"，需要用户定方向——这会改变很多题的判定，不是本包能自行决定的。清单：`truncation_collisions_summary.json`（每题计数）+ `runs/env_overnight_20260916/L2_reference_ids/truncation_collisions_full.json`（逐条，含行号）。
3. **非 pytest 行污染 status_map 的风险等级（N1/V1）。** 53 题的 status_map 里有"状态"不是五个状态词之一的垃圾条目（最常见来源：被测程序自己打印的 `ERROR: ...` 行，75 条；pydantic 行尾分支遇到含空格 nodeid 时把 nodeid 里的单词当状态）。**当前 181 份日志里没有任何参考 ID 命中这类垃圾条目**，所以不影响既有判定；但它说明 parser 会把候选可控的 stdout 当摘要行解析——候选只要打印 `PASSED <nodeid>` 就能写进 status_map。是否要在 v2 路径加"只认 pytest 摘要区"的收紧，请用户定。清单：`nonstatus_values_summary.json`。
4. **`python__mypy-10401` 没有阶段一 gold 日志**（`empty` 有、`gold` 目录缺 `test_output.txt`），182 个目录里只有 181 份 gold 可复算。本包未去查原因，标 `unknown`，请协调者决定是否补跑。

## 5. 附带扫描：全量 gold 日志

范围：`runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/` 下 182 个任务目录（216 题中 34 题无阶段一记录），其中 181 题有 gold `test_output.txt`。

- **parser 复现**：181/181 与落盘 `status_map.json` 逐条相等。明细 `runs/env_overnight_20260916/L2_reference_ids/sweep_182.json`。
- **缺席参考 ID 的题**：恰为本包这 10 题，无遗漏、无多余。
- **回退规则全池安全性**（`runs/env_overnight_20260916/L2_reference_ids/global_checks.json`、`direction_checks.json`）：
  - 两个不同日志键解码到同一字符串：**0**
  - 解码结果撞上日志里已存在的另一个键：**0**
  - 解码抛异常：**0**
  - 181 份 gold 日志共 **20379** 个参考 ID 直接命中；回退只在 **18** 个缺席项上触发（正/反两个方向都是 18 且唯一）。
  - "直接命中的参考，其解码/转义形式又恰好是另一个键"（会造成误绑定）：正向 **0**、反向 **0**。
- **gold / empty 一致性**：10 题两侧缺席集合完全相同，说明这是环境/parser 确定性现象，与是否打 gold 补丁无关。
- **参考 ID 在场但状态非 PASSED/XFAIL（只列，不判）**：6 题，状态全部是 `FAILED`，**没有 SKIPPED / ERROR 参考项**。

  | 任务 | F2P 非 OK | P2P 非 OK |
  | --- | --- | --- |
  | `Project-MONAI__MONAI-1121` | 0/1 | 8/35 |
  | `Project-MONAI__MONAI-3205` | 1/1 | 0/0 |
  | `getmoto__moto-4799` | 0/1 | 2/19 |
  | `getmoto__moto-4833` | 0/2 | 2/23 |
  | `getmoto__moto-7105` | 1/11 | 0/1 |
  | `modin-project__modin-5940` | 0/4 | 1/1931 |

- **真机交叉印证**：`pandas-dev__pandas-48106` 在 e1 真机（走生产 v2 路径、日志带 `>>>>> Start/End Test Output` 标记）复现同样 3 个缺席 ID，`num_parsed_tests=1037`、`parser_source=swegym_parsers@242429c1`、`resolution=RESOLVED_NO`。证据：`runs/swe_grading_wiring_20260915/e1/eval_logs/evallog_replay-replay-e1-pandas-_de414139.diagnostics.json`（`verdict.reference_missing`）。说明这不是阶段一离线 harness 的产物。
- **口径说明**：阶段一的 `eval.sh` 不打 `>>>>> Start/End Test Output` 标记（`grep -c "Test Output" … = 0`），所以阶段一是整份日志解析；本包复算沿用同一口径才得到逐条相等。生产 v2（`parse_eval_log_v2`）只解析标记之间的段。这不影响本包结论（摘要行都在段内），但 §4 第 3 条的污染面在生产里只限段内。

## 6. parser 回归样例

`parser_samples/`，9 组，每组 `<名字>.log.txt`（逐字节取自真实日志，未改写）+ `<名字>.expected.json`（`swegym_parsers` 实跑出的期望状态映射 + 来源日志路径 + 关注的参考 ID 及其是否直接命中）。**本包未改 `rh2/tests/envpack/test_swegym_parsers.py`**，样例仅供以后接入。

| 样例 | 覆盖 | 行数→键数 |
| --- | --- | --- |
| `E1_unicode_astral_escape` | `\U0001f4a9` 转义 | 4→4 |
| `E2_unicode_latin1_escape` | `\xee` 转义 | 3→3 |
| `E3_backslash_doubling` | 反斜杠双写 | 9→9 |
| `E4_bytes_param_byte_escape` | bytes 逐字节转义 + pydantic 行尾状态词 | 4→4 |
| `E5_control_char_escape` | U+0012 / U+0081 转义；同时含一处 `[str_check-` 截断键碰撞（16 行→15 键） | 16→15 |
| `T1_space_truncation_unique` | 空格截断但无碰撞 | 17→17 |
| `T2_truncated_key_collision` | 截断键碰撞 2/3/2 | 7→3 |
| `V1_pydantic_trailing_status_value_is_word` | 行尾分支把 nodeid 单词当状态 | 2→2 |
| `N1_non_pytest_line_parsed` | 程序自身 `ERROR:` 行被当摘要行 | 3→2 |

## 7. 产物清单与复算方式

包目录 `docs/.../env_overnight_20260916/L2_reference_ids/`：
`L2_reference_ids.md`（本文）、`id_mapping_proposals.json`（18 条映射 + 证据）、`screening_records.json`（10 题题级记录）、`fallback_simulation.json`（修前/修后判定模拟）、`direction_checks.json`（正/反两个回退方向的全池假别名检查）、`truncation_collisions_summary.json`、`nonstatus_values_summary.json`、`parser_samples/`。

大文件目录 `runs/env_overnight_20260916/L2_reference_ids/`：
`sweep_182.json`（182 目录逐题复算）、`global_checks.json`（全池安全性）、`truncation_collisions_full.json`（逐条碰撞含行号）、`work/`（复算脚本：`common.py` / `sweep.py` / `cands.py` / `rawlines.py` / `hypo.py` / `global_checks.py` / `direction_checks.py` / `mksamples.py` / `records.py` / `screening.py` / `simulate.py`）。

复算：`rh2/.venv/bin/python runs/env_overnight_20260916/L2_reference_ids/work/<脚本>.py`（只读，不触网、不起容器）。

> 环境提醒（只读观察，本包未改任何 `rh2/` 文件）：
> 1. 复算时 `rh2/src/repoharness2/contracts/grading.py` 有**未提交的语法错误**——第 317 行在一个已经闭合的 `if/else` 之后又多出一个 `else:  # resolved`，`python -c "import repoharness2.envpack"` 直接 `SyntaxError`。该文件 `git status` 为 ` M`，疑似另一会话正在编辑。本包因此按文件路径独立加载 `swegym_parsers.py`（见 `work/common.py`）。
> 2. `rh2/src/repoharness2/envpack/swegym_parsers.py` 还是**未跟踪**新文件，`scoring.py`（+158 行）、`spec_vendor.py`、`grading/manager.py`、多个 `rh2/tests/` 文件都在未提交状态。也就是说本包复算依赖的 parser 与 v2 评分路径都只存在于当前工作树，不在任何提交里。请协调者转告相关会话，并在引用本包结论时带上这个前提。
