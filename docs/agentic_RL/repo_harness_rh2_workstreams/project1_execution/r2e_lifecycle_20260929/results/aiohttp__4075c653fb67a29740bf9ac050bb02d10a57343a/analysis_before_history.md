# aiohttp__4075c653：私有主审读历史前分析

- 角色：R2E 私有主审（单题闭环试行，干净上下文），2026-09-29。本文在打开任何历史调查之前封存。
- 口径：统一标准 v1（§3 根因编号、§4 五步、§5 修订模板）+ R2E 评分口径（观测映射与期望映射逐键全等才得 1）。
- 执行情况：没有运行项目代码，没有开容器或远端。本机只做了三件事：读文件；用本机 python3 标准库核对 `str.split` 与正则语义（没有导入 aiohttp）；在临时目录里对 base 文件副本做 `git apply --check` 与 `py_compile`，确认附录补丁能直接应用、语法正确。
- 证据层次：【源码】读码推断；【stdlib】本机标准库语义核对；【运行】已有 current 运行原件（账本与日志）；【待跑】需协调者实跑。

路径简写（都相对仓库根）：

- `PUB` = `runs/r2e_static_prep_20260924/v3/public/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a`，`WT` = `PUB/worktree`
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a`，`HT` = `PRIV/hidden_tests/test_1.py`
- `NOOP_LOG` = `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-a_ad0193bb.eval.log`
- `GOLD_LOG` = `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-gold-a_075a4ed9.eval.log`
- `HP` = `WT/aiohttp/http_parser.py`（base 版本，blob `0a1586b8`，与 gold 的 index 行一致）

## 0. 结论（暂定）

- **题目**：加固 aiohttp 3.9.0b0 的纯 Python 请求解析器，共两条核心要求。
  - R1：请求头的字段名含非 ASCII 字符（题面例子是 `ÿ`）时，抛 `BadHttpMessage`。
  - R2：请求行（仓库和题面都叫 status line）含不当空白或控制字符时，抛 `BadStatusLine`。题面例子是 `GET\n/path\x0cHTTP/1.1`。
  - gold 改了两处：`HDRRE` 的字符类加上 `\x7F-\xFF`；请求行从 `split(maxsplit=2)` 改成 `split(" ", maxsplit=2)`。
- **评分材料本身健康**：
  - 材料哈希全部对得上。
  - 当前材料上 noop 得 0、gold 得 1，各跑过两次【运行】。noop 只错 2 个目标键，失败原因都是 "DID NOT RAISE"，与题面描述一致。
  - 3 个期望 FAILED 键是镜像里没有 C 扩展造成的恒失败，正确修复不会让它们翻转。
  - 没有发现误拒合理解（T1）。
- **主要问题（按 v1 §4）**：
  1. 第 2 步命中两次（S1，T2c）。两个目标键的输入就是题面两个示例的字面值，其余 127 个键没有一个检查"别的非 ASCII 字段名"或"别的不当空白"。
  2. 第 3 步的退化候选 DG1 只把示例里的 `c3 bf`、LF、FF 加进拒绝条件，逐键推演能拿到 129/129，预测得 1（S1，T2b）【待跑】。
  3. 第 4 步 conditional：gold 自己把 base 原本拒绝的请求（请求目标里夹 LF、CR、FF 或 TAB）改成了接受。
     - 例如 `GET /pa\nth HTTP/1.1`：base 抛 `BadStatusLine`，gold 把它当成合法请求【源码+stdlib；yarl 行为待跑确认】。
     - 按题面的一般表述（"the status line contains improper whitespace and control characters"），这是同一核心要求的另一个实例，判 S1。
     - 如果复核认定题面只指分隔位置，就降为 G1/T3 登记（S2）。
- **修订建议**：
  - R-c #1 必做：换一个非示例的非 ASCII 字段名。
  - R-c #2 必做：FF 单独作分隔、VT 作分隔，各一例。
  - R-c #3 看第 4 步复核结果：请求目标里的 LF/FF 必须被拒。gold 过不了这条，按 D4 用替代解 ALT1 作正对照。
  - 可选 R-f：题面例 1 的字面代码把 bytes 塞进了 f-string，照抄复现不出问题（P4）。
- **暂定处置**：`needs_review`。测试层的 S1 要等 R-c；actor 条件要等新机器的 devcheck。
  - 用途（详见 §11）：问题定位 yes，能力比较 conditional，训练候选 no，留出候选 no。
- **最关键的未知**：
  - DG1 的正式评分是否真的得 1；
  - 在真实 yarl 下，gold 是否确实接受请求目标里的 LF/FF；
  - 新机器重建的镜像上，actor 开发核对的结果。

## 1. 公开读者没有捕获的真实条件（第 1 步）

| 条件 | 事实与出处 | 对本题的影响 |
| --- | --- | --- |
| C 扩展 | 评分侧镜像里没有 C 扩展：`test_c_parser_loaded` 断言失败，两个只测 C 的用例报 `NameError: HttpRequestParserC`（`NOOP_LOG` L164-169、L185-213）。所有期望键都只有 `py-parser` 参数（`PRIV/expected_output.json`） | 公开读者的推测成立。解题侧用同一张镜像，所以不设 `AIOHTTP_NO_EXTENSIONS` 时，这 3 个公开用例在修复前后都失败。这是环境造成的，不是题目缺陷；commands.json 已经按此处理 |
| pytest 与插件 | pytest 7.4.2，插件有 asyncio 0.23.8、cov 4.1.0、mock 3.11.1（`NOOP_LOG` L18、L22） | 公开读者列为未知的 pytest-cov 实际已经装了。`-o addopts=""` 不必要，但也无害 |
| 评分命令读哪份配置 | `run_tests.sh` 在 `/testbed` 下运行，所以 `WT/setup.cfg` 的 `[tool:pytest]` 生效（L115-171）：<br>- `--cov`（L130-131）<br>- `-m "not dev_mode"`（L134），因此收集时 3 个 dev_mode 用例被排除（`NOOP_LOG` L24）<br>- `filterwarnings = error`（L135-136） | 候选如果在导入期触发 DeprecationWarning（例如非 raw 字符串里的无效转义），收集阶段就会报错，整份测试判 0。公开测试也会暴露这一点，所以不算题目缺陷 |
| DEBUG 模式 | 评分命令没开 dev mode；`HttpResponseParser.lax = not DEBUG`（`HP` L639-651） | 响应解析保持宽松，相关回归键按宽松行为断言 |
| 没导出的镜像文件 | `install.sh` 和 `process_aiohttp_updateasyncio.py` 在镜像里，但不在公开包里（`PUB/worktree_manifest.json` 的 `untracked_missing`；`NOOP_LOG` L1-4 的 git status） | 内容未知，清单第 29 项记 unknown |
| 模型实际收到的消息 | 只有静态渲染的 `user_prompt.txt` | actor 待验 |
| 镜像身份 | current 运行用的是旧机器上的派生镜像 `rh2-r2e-derived/aiohttp:4075c653fb67-r2e_derive_v1`，image ID `sha256:0d785442…`（各账本 L4）。新机器已经重建，ID 可能变了 | noop/gold 事实要用新机器 devcheck 的私有 gold 对照复核 |

- 公开读者把"请求目标或版本里夹控制字符"列为可选加固（A4），但没注意到一件事：对"请求目标里夹空白"这类输入，gold 的行为是从拒绝变成接受（见 §5）。
- 公开读者的其它判断都与私有材料一致，包括 A1、A2 两种做法都能得 1，以及 P1–P9 都受回归键保护。

## 2. 隐藏测试展开（第 2 步）

### 2.1 结构

- `HT` 共 1419 行，我全部读过。它与公开的 `WT/tests/test_http_parser.py` 相比只多两处：
  - `test_bad_headers` 的参数表多了 `"\xffoo: bar"`（`HT` L181）；
  - 新增 `test_http_request_bad_status_line_whitespace`（`HT` L683-686）。
  - 另外 `test_http_request_upgrade` 的签名加了类型注解，不影响行为。
- `PRIV/hidden_tests/conftest.py` 与 `WT/tests/conftest.py` 逐字相同。
- 收集结果：共 134 项，其中 3 项 dev_mode 被排除，2 项因 C 解析器不可用而跳过，剩下 129 个键（`NOOP_LOG` L24、L510-511）。期望映射里是 126 个 PASSED 和 3 个 FAILED。
- 键里只有 `py-parser` 参数：C 扩展导入失败时，`REQUEST_PARSERS` 只含 Py 类（`HT` L32-41）。

### 2.2 目标键

目标键指 noop 与 gold 结果不同的键。两轮 current 运行给出的目标键一致。

| 键 | 调用路径与输入 | 断言 | 公开依据 | noop 失败原因 |
| --- | --- | --- | --- | --- |
| `test_bad_headers[py-parser-pyloop-\xffoo: bar]` | fixture `parser` 构造 `HttpRequestParserPy(Mock, loop, 2**16, max_line_size=8190, max_headers=32768, max_field_size=8190)`（`HT` L56-66）。测试调用 `feed_data(f"POST / HTTP/1.1\r\n{hdr}\r\n\r\n".encode())`，实际字节是 `POST / HTTP/1.1\r\n\xc3\xbfoo: bar\r\n\r\n`（`HT` L184-187；`NOOP_LOG` L240）。调用链为 `feed_data` → `HttpRequestParser.parse_message` → `HeadersParser.parse_headers`（`HP` L127-215） | `pytest.raises(BadHttpMessage)`，不检查消息 | `user_prompt.txt` L4、L22 | "DID NOT RAISE BadHttpMessage"（`NOOP_LOG` L236-242） |
| `test_http_request_bad_status_line_whitespace[py-parser-pyloop]` | 同一个 fixture。`feed_data(b"GET\n/path\x0cHTTP/1.1\r\n\r\n")`（`HT` L684 用的是 Python 的 FF 转义）。代码走到请求行切分（`HP` L546-552） | `pytest.raises(BadStatusLine)`，不检查消息 | `user_prompt.txt` L4、L16-18、L23 | "DID NOT RAISE BadStatusLine"（`NOOP_LOG` L251-256） |

两个目标键的输入都与题面示例一致：

- 请求行与题面的 `malformed_status` 逐字节相同。
- 头字段按题面的文字意图构造：`"\xffoo: bar"` 以字符串放进 f-string，再整体做 UTF-8 编码。它不是题面代码的字面写法，见 §4(b)。

### 2.3 回归键

其余 127 个键的测试体我都读过，下面按受影响的接口分组。

- **字段名检查（`HDRRE` 所在路径）**：
  - `test_bad_headers` 的其余 7 个参数：带正负号的 Content-Length，值含 CR/LF/NUL，字段名前后有空白；
  - `test_invalid_header`（没有冒号）、`test_invalid_name`（`test[]`）、`test_whitespace_before_header`；
  - `test_unpaired_surrogate_in_header_py`：没有冒号的 `\xff` 头行，异常消息必须能做 UTF-8 编码；
  - `test_parse_headers_longline`：字段名含 `\xd9` 且超长，抛 `LineTooLong` 或 `BadHttpMessage` 都算对；
  - `test_max_header_field_size[40960/8191]` 与 `_under_limit`：全 ASCII 长字段名的长度口径。
  - **这一组没有任何键使用题面示例以外的非 ASCII 字段名。**
- **头字段值（不应受本题影响）**：
  - `test_http_request_parser_utf8`、`_non_utf8`、`test_http_response_parser_utf8`：值里的 UTF-8 或 cp1251 字节必须接受；
  - `test_http_response_parser_lenient_headers`：响应头值含 `\x01` 必须接受。
- **请求行（切分所在路径）**：
  - `test_http_request_bad_status_line`：`getpath ` 抛 `BadStatusLine`，且消息里没有转义的 `\n`；
  - `_bad_method`、`_bad_version`、`_bad_version_number`；
  - `_bad_ascii_uri`、`_bad_nonascii_uri`：这两个要求抛 `InvalidURLError`；
  - `test_http_request_max_status_line[...]` 与 `_under_limit`；
  - `test_parse_uri_utf8`：Py 解析器必须接受路径里的原始 UTF-8；
  - `test_parse_uri_percent_encoded`（6 个参数）、`_two_slashes`、`test_url_connect`、`test_url_absolute`、`test_partial_url` 等。
  - **这一组没有任何键使用题面示例以外的不当空白或控制字符，也没有键检查请求目标里夹空白的请求。**
- **响应解析**：gold 没改响应解析，但它与请求解析共用 `HeadersParser`。`test_http_response_parser_*` 共 14 个键，字段名全是 ASCII，不受 gold 影响。
- **与本题无关**：`TestParsePayload.*`（18 个键）、`TestDeflateBuffer.*`（7 个键），以及连接、压缩、分块等用例。

## 3. 双向映射（第 3 步）

| # | 公开要求或合理旧行为 | 依据 | 键与决定性断言 | 覆盖 | 证据 |
| --- | --- | --- | --- | --- | --- |
| R1 | 请求头字段名含非 ASCII 字符 → `BadHttpMessage` | `user_prompt.txt` L4、L22；RFC 9110 规定 field-name = token（`HP` L59-65 的注释引用了同一套 tchar 定义） | `test_bad_headers[...\xffoo: bar]`（`HT` L181、L184-187） | **部分**：只有示例的 `ÿ`（UTF-8 `c3 bf`，位于字段名首位） | 【运行】noop F / gold P |
| R2 | 请求行含不当空白或控制字符 → `BadStatusLine` | `user_prompt.txt` L4、L7、L23 | `test_http_request_bad_status_line_whitespace`（`HT` L683-686） | **部分**：只有示例那一行（LF 在方法后，FF 在版本前） | 【运行】noop F / gold P |
| R2' | 按同一条一般表述，请求目标里夹 LF/CR/FF/TAB 的请求行也要拒绝 | 同上；而且 base 本来就用 `BadStatusLine` 拒绝这类请求（§5） | 无 | **缺失**；gold 还把这类请求从拒绝改成了接受（与一般表述冲突） | 【源码+stdlib】【待跑】 |
| P1 | 头字段**值**里的非 ASCII 仍然接受 | 公开测试 `WT/tests/test_http_parser.py` L697-729、L798-811 | `test_http_request_parser_utf8`、`_non_utf8`、`test_http_response_parser_utf8` | 覆盖 | 【运行】P |
| P2 | 非法或非 ASCII 的请求目标仍抛 `InvalidURLError` | 公开测试 L761-768 | `_bad_ascii_uri`、`_bad_nonascii_uri` | 覆盖。能拦住"只要请求行含非 ASCII 就一律抛 `BadStatusLine`"这种过度修复 | 【运行】P |
| P3 | Py 解析器接受路径里的原始 UTF-8 | 公开测试 L1086-1096 | `test_parse_uri_utf8` | 覆盖 | 【运行】P |
| P4 | `getpath ` 抛 `BadStatusLine`，消息里没有转义换行 | 公开测试 L674-679 | `test_http_request_bad_status_line` | 覆盖 | 【运行】P |
| P5 | `LineTooLong` 的长度口径不变 | 公开测试 L573-636、L771-777 | `test_max_header_*`、`test_http_request_max_status_line*`（用 `match=` 检查消息前缀） | 覆盖 | 【运行】P |
| P6 | 已有的各项拒绝保持不变 | 公开测试 L171-186、L253-256、L560-570、L746-758 | 见 §2.3 | 覆盖 | 【运行】P |
| P8 | 响应解析保持宽松 | 公开测试 L814-876 | `test_http_response_parser_*` | 覆盖 | 【运行】P |
| A1、A2 | 响应状态行要不要一起收紧；字段名检查放进共享的 `HeadersParser`，还是只对请求生效 | 公开读者 §1.3 | 没有键区分 | 两种做法都判 1，不构成 T1 | 【源码】 |

**反查（关键断言有没有公开依据）**：

- 两个目标断言都只来自题面，异常类也是题面点名的（`BadHttpMessage`、`BadStatusLine`）。
- 所有带 `match=` 的断言（`LineTooLong` 的消息、Transfer-Encoding 相关消息）在公开测试里原样存在，不是本题新增的。
- 没有新增 mock 调用形状、内部 helper 名或精确消息之类的要求。

**替代实现与可能蒙混的候选**：

- **替代解 ALT1**（附录 B）：
  - 字段名改用 RFC token 白名单做 `fullmatch`。这比 gold 更严，也会拒绝 `/` 和 `?`。
  - 请求行先拒绝任何 C0 控制字符或 DEL，再按单个 SP 切分。
  - 逐键推演，129 个键全部相等，预测得 1【待跑】。它同时是 R-c #3 的 D4 正对照。
- **可能蒙混的 DG1**（附录 A）：只把示例里的字节加进拒绝条件，预测得 1【待跑】。
- **其它推演过、没列为实跑候选的做法**：
  - 这些都应得 1：用 `bname.isascii()` 或 `name.isascii()` 检查；检查放在长度检查之前或之后；直接抛 `BadHttpMessage`；用正则 `fullmatch` 校验整个请求行。
  - "只要请求行含非 ASCII 就一律抛 `BadStatusLine`"会被 P2、P3 两个键拒绝。它违反了公开测试记录的行为，所以不属于合理解。

## 4. R2E 专项（第 4 步）

**(a) 期望映射里的非 PASSED 键**

共 3 个 FAILED，原因都是"镜像里没有 C 扩展，又没设 `AIOHTTP_NO_EXTENSIONS`"：

- `test_c_parser_loaded`（`HT` L99-104）：它按 `NO_EXTENSIONS` 决定是否跳过，而不是按扩展是否可用。所以它会运行，并在断言 `HttpRequestParserC` 在模块里时失败（`NOOP_LOG` L164-169）。
- `test_invalid_character[pyloop]` 和 `test_invalid_linebreak[pyloop]`（`HT` L125-162）：直接报 `NameError`（`NOOP_LOG` L185-213）。

这 3 个键只取决于扩展是否可用。只改 Py 解析器的修复，包括 ALT1 这种更完整的修复，都不会让它们翻转。

- 唯一的翻转方式：候选改动了扩展检测。例如在 `aiohttp/helpers.py` 里让 `NO_EXTENSIONS` 在扩展导入失败时为真，这 3 个键就变成 SKIPPED，期望键缺失，判 0。这已经超出题目范围。
- M3 独立 runner 在来源镜像上也得到同样的 3 个 FAILED（`runs/env_overnight_20260916/M3/gold_ledger/logs_r2e/aiohttp/4075c653fb67/gold/a1/test_output.txt` L458）。
- 处置：登记为 T5（已解释、稳定）。不建议做 R-a，因为没有误拒案例。

**(b) 题面描述的报错是否出现在日志里**

- noop 的两个目标键都是 "DID NOT RAISE"（`NOOP_LOG` L236、L251），与题面的 "No exceptions are raised" 一致。
- 但题面例 1 的**字面代码**有问题：它先 `.encode()` 得到 bytes，再把 bytes 放进 f-string，实际发出的头行是 `b'\xc3\xbfoo: bar'` 这段 repr 文本。
  - 这段文本里的反斜杠会命中 base 的 `HDRRE`（`HP` L68、L149-150），所以 base 已经抛出 `InvalidHeader`（`BadHttpMessage` 的子类）。【源码+stdlib；公开读者得出同样结论；devcheck 里 `repro_parser_issue_cases` 的 `issue_ex1_literal` 一行可以实证】
  - 因此照抄例 1 复现不出问题，记为 P4。题面 L22 的文字（"invalid character `ÿ`"）能消解这个误导。

**(c) 题面有没有泄漏修法**

没有。题面只给了测试形态的调用和症状。"improper whitespace" 暗示问题出在切分方式，但没有给出代码。不属于 P1。

**(d) base 版测试辅助、搬迁伪影、跨文件撞键**

- 隐藏测试只导入 `aiohttp.*`、`multidict` 和 `yarl`。
- conftest 通过 `pytest_plugins = ["aiohttp.pytest_plugin", "pytester"]`（conftest L25）加载仓库自己的 `aiohttp/pytest_plugin.py`，由它提供 `loop` fixture 和 `pyloop` 参数。`setup.cfg [tool:pytest]` 也来自候选工作树。这两处候选都能改，评分时也不会重置。
  - 正常修复不会碰这两处。但候选一旦改了，可能改变键集（判 0）或影响判定。
  - 这是 R2E 通用的控制面暴露（清单第 31 项），本题只记适用性。探针的事后审计应标记对 `aiohttp/pytest_plugin.py`、`aiohttp/test_utils.py`、`setup.cfg` 的改动。
- 只有一个隐藏测试文件，不存在跨文件撞键。conftest 与原目录逐字相同，也没有搬迁伪影。

**(e) 时间、随机、资源敏感的键**

没有。这些都是纯解析器单元测试，协议对象是 mock，不联网、不计时。测试段约 5.3–5.6 秒，内存峰值约 440 MB（见账本）。

**(f) 材料修订**

`revisions.json` 为空，`run_refs.json` L4 的 `material_revisions` 也是 `[]`，不适用。

## 5. gold 检查与运行原件（第 5 步）

**原例是否修到**：修到了。

- gold 下两个目标键都通过（`GOLD_LOG` L39、L89；L475 的汇总为 3 failed、126 passed）。
- 两次 current 运行结果一致：
  - `runs/r2e_rf_20260923/remote/ledger_r2e_all_gold.jsonl` L4；
  - `runs/r2e_env_repair_20260924/_rerun2/ledger_gold.jsonl` L4。
- M3 独立 runner 的两次运行也都是 reward 1（`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl` L18、L67）。

**改动范围**：

- gold 只改了 `aiohttp/http_parser.py` 两处。
- 上游修复提交另外改了 `CHANGES/7719.bugfix` 和测试文件，这两部分已从 gold 中排除（M3 账本 L18 的 `gold_meta.excluded`）。
- 没有无关改动。

**G1：gold 引入了一个未被测试覆盖的回归**

- 机制：
  - base 用 `str.split(maxsplit=2)` 切分请求行。如果请求目标里夹了任何空白，目标会被切成两段，剩下的部分落进版本位，于是 `VERSRE.fullmatch` 失败，抛 `BadStatusLine`（`HP` L550、L564-566）。
  - gold 改成只按 SP 切分后，这类请求行切出的三段都合法，请求目标原样进入 `URL.build(..., encoded=True)`（`HP` L583-588）。
  - 这条路径不检查字符：`test_parse_uri_utf8` 能通过，说明原始 UTF-8 可以原样进入。因此请求被接受。
- 证据层次：切分结果已用 stdlib 核对；yarl 的行为是上述推断，待实跑确认。

| 请求行 | base | gold | 说明 |
| --- | --- | --- | --- |
| `GET /pa\nth HTTP/1.1` | `BadStatusLine` | 接受，path 为 `/pa\nth` | 回归 |
| `GET /pa\rth HTTP/1.1` | `BadStatusLine` | 接受 | 回归 |
| `GET /pa\x0cth HTTP/1.1` | `BadStatusLine` | 接受 | 回归 |
| `GET /pa\tth HTTP/1.1` | `BadStatusLine` | 接受 | 回归 |
| `GET /path\x0c HTTP/1.1`（FF 后面跟 SP） | 接受，path 为 `/path` | 接受，path 为 `/path\x0c` | 两者都有的旧缺口 |
| `GET /path HTTP/1\x0c1`（版本里夹 FF；`VERSRE` 的 `.` 没转义） | 接受 | 接受 | 两者都有的旧缺口 |
| `GET /pa\x01th HTTP/1.1` | 接受 | 接受 | 两者都有的旧缺口 |

- **前四行是 gold 相对 base 的真实回归**：base 原本符合题面的预期，gold 不符合。
  - LF 和 CR 正是请求走私常用的字符。LF 和 FF 也正是题面示例里的字符。
- **这不是上游后来修掉的笔误**：上游到 3.10.6.dev0 仍是同样的实现（同仓题 1c1c0ea3 的公开工作树，`aiohttp/http_parser.py` L570-575）。这说明上游的实现范围比题面表述窄。
- 按 v1 的规则，"核心要求按题面的一般表述理解，gold 的实现范围不决定核心要求"，所以判为第 4 步命中（§8 的 I4）。

**其它未测到的影响面**：

- `HeadersParser` 被响应解析和 multipart 分段头共用（`HP` L258；`WT/aiohttp/multipart.py` L699）。gold 让它们也拒绝非 ASCII 字段名。
- 请求行里有多个 SP，或以 SP 开头时，gold 由接受改为拒绝（stdlib 核对）。
- 这些变化与 RFC 一致，也没有公开要求反对，登记为未测范围即可。

**初态失败与退出情况**：

- noop 的测试段正常结束，129 个键全部解析，`keys_equal=true`，`mismatched` 恰好是两个目标键（`runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl` L4）。
- test rc=1 是那 3 个环境 FAILED 键造成的，gold 同样是 rc=1。

## 6. 开发需求（第 6 步）

| 项 | 事实 | 证据级别 |
| --- | --- | --- |
| 导入 | 包没有装进 venv，`/testbed` 必须在 `sys.path` 上；在 `/testbed` 下用 `python -m pytest` 或 `python -c` 即可。评分侧实际从 `/testbed/aiohttp/__init__.py` 导入，版本 3.9.0b0（账本 `observations`） | 评分侧实测；解题侧依据 `PUB/environment_brief.md` L13 和首批镜像实测；本题 actor 待验 |
| 依赖 | 不需要新依赖。multidict、yarl、brotli（`test_compression_brotli` 通过）、pytest 7.4.2 及其插件都已安装 | 评分侧实测 |
| 资产 | 无 | 源码 |
| 构建 | 不需要构建。C 扩展不存在，也无法重建：`WT/vendor/llhttp` 是空子模块，重建需要 npm 和网络。所以修复只能落在 Py 解析器 | C 扩展缺失为评分侧实测；无法重建为读源码推断 |
| 权限 | agent 可以写 `/testbed`（`PUB/environment_brief.md` L12） | 首批实测；本题 actor 待验 |
| 网络 | 准备、解题、测试三个阶段都不需要；评分时 `deny_all` | 评分侧实测 |
| 提交边界 | 修复只涉及 `aiohttp/http_parser.py`；gold 的投影 `included_paths` 为 `["aiohttp/http_parser.py"]`（gold 账本 L4） | 评分侧实测 |
| 公开验证 | commands.json 共 5 条：<br>1. 导入与版本；<br>2. 解析器层复现（题面两例、字面的例 1、3 个保留用例）；<br>3. 服务端 400 复现（用回环端口）；<br>4. 跑 `tests/test_http_parser.py`（C 扩展缺失时设 `AIOHTTP_NO_EXTENSIONS=1`）；<br>5. multipart、异常类、客户端相关测试 | 待 devcheck |

对公开命令的意见（供协调者读 devcheck 输出时参考）：

- 这些命令足以复现题面两例，也能保护主要的旧行为。但它们只用示例的字面值，提示不出 §5 的回归。这不怪公开读者，公开材料里没有依据要求它。
- `repro_server_400_py_parser` 写的是 `expect=nonzero`，分不清"复现成功（rc=1）"和"不能监听回环端口（rc=3，打印 SETUP_ERROR）"，要读 stdout 判定。
- 评分时测试段约 5 秒，最小公开验证预计十几秒量级，以 devcheck 的墙钟为准。

## 7. 八方面覆盖（含 40 项清单编号）

| 方面 | 已查 | 未查或未知 | 清单编号与暂定状态 |
| --- | --- | --- | --- |
| 公开需求 | 题面、公开测试、调用方、C 解析器的错误映射 | 模型实际收到的消息 | 3 issue（P4）；23 issue（P4，另外 R2 一般表述的范围见 I4） |
| 材料与初始问题 | 哈希、隐藏测试与公开测试的 diff、gold 的来源、noop 的失败位置 | 新机器镜像上的复验 | 1 pass、2 pass、27 issue（G1） |
| 测试是否测到要求 | `HT` 全部 1419 行，129 个键逐组看过 | — | 18 pass、19 pass、20 pass、25 issue（T2c/T2b）、32 issue |
| 是否误拒合理解 | 异常类有题面依据；没有消息、mock、helper 约束；3 个 FAILED 键不受修复影响；推演了 5 类替代实现 | ALT1 待跑 | 24 pass（以 ALT1 实跑为条件）；28 暂不适用 |
| 回归与 gold 完整性 | 请求行、字段名两条路径；响应与 multipart 的共用部分 | multipart 和客户端的实际行为没跑 | 26 issue（G1 未测回归）；27 issue |
| agent 开发条件 | 评分侧实测；环境卡与 brief | 本题 actor 条件（新机器 devcheck） | 6 pass、8 unknown、9 pass、10 unknown、11 pass、13 pass、14 pass（noop/gold 各 2 次，另有 M3 两次）、15 not_checked |
| 交付与评分边界 | 投影、测试恢复、解析 | 两个没导出的 untracked 文件的内容 | 4 pass、16 pass、17 pass（`RH2_SETUP_RESTORED=3`）、21 pass、22 pass（M3 结果同形）、29 unknown、30 pass、31 issue（通用控制面暴露，本题只记适用性） |
| 题目关系与用途 | 两份跨题比对；打开 4 个同仓公开包核对 | — | 5 issue（X1）；33–36 not_checked（需要真实模型） |

## 8. 问题与严重度（v1 §3、§4）

| ID | v1 编号 | 内容 | 证据 | 严重度 |
| --- | --- | --- | --- | --- |
| I1 | T2c | R1 的核心断言只用题面示例的 `ÿ` | `HT` L181、L184-187；§2.3 | S1（第 2 步） |
| I2 | T2c | R2 的核心断言只用题面示例那一行 | `HT` L683-686；§2.3 | S1（第 2 步） |
| I3 | T2b | 退化候选 DG1 只拒绝示例里的字节，推演得 129/129 | 附录 A；逐键推演 | S1（第 3 步）【待跑】 |
| I4 | G1，经第 4 步 | gold 让请求目标里夹 LF/CR/FF/TAB 的请求从拒绝变成接受 | §5 的表；`HT` 里没有对应键 | S1 conditional（待实跑并经复核）；不成立则 S2（T3） |
| I5 | P4 | 题面例 1 的字面代码复现不出问题 | §4(b) | 登记；可选 R-f |
| I6 | T5 | 3 个期望 FAILED 键是环境造成的恒失败 | §4(a) | 登记；原因已查明 |
| I7 | T3 | 既有缺口，不属本题核心要求：<br>- 字段名里的 `/`、`?`；<br>- 版本里的 FF；<br>- 请求目标里的 `\x01`；<br>- 空字段名（`: v`）在 `HP` L145 抛 `IndexError` | 源码；上游到 1c1c0ea3 才加上空名检查和 `TOKENRE` | 登记 |
| I8 | X1 | 同仓题 1c1c0ea3、22a12cc2 的公开初态含本题修复和两个目标测试的原文；另外 240da100 的新测试名出现在本题初态里 | 见下文 | 登记 |
| I9 | E3（交 A 线，通用问题） | 评分时会加载候选能改的 `aiohttp/pytest_plugin.py` 和 `setup.cfg` | §4(d) | 不算题目缺陷；列为事后审计项 |

§4 五步汇总：

1. 第 1 步未命中：两条核心要求都有直接断言。
2. 第 2 步命中：I1、I2。
3. 第 3 步预测命中：I3。
4. 第 4 步 conditional 命中：I4。
5. 第 5 步不适用。

**X1 详情**：

- **机械 gold 比对漏报了本题。** `cross_task_gold_scan.json` 里没有本题的配对，原因是：
  - gold 新增的 3 行里，只有 `split(" ", maxsplit=2)` 这一行在后来的版本里逐字保留；
  - `HDRRE` 在上游被改写成了 `TOKENRE.fullmatch(name)`；
  - 所以逐字命中率达不到 80% 的阈值。
- **测试名比对命中。** `cross_task_test_scan.json` 显示，`test_http_request_bad_status_line_whitespace` 出现在 1c1c0ea3（3.10.6.dev0）和 22a12cc2（3.11.0.dev0）的初态里。我打开两题的公开包核对过：
  - 两题的 `aiohttp/http_parser.py` 都有 `line.split(" ", maxsplit=2)`（1c1c0ea3 在 L572，22a12cc2 在 L577），也都用 `TOKENRE.fullmatch(name)` 检查字段名（都在 L172）；
  - 两题的 `tests/test_http_parser.py` 都含 `"\xffoo: bar"`（L210 / L211），以及本题目标测试的原文（L823-826 / L824-827）；
  - 两题的题面与本题无关，分别讲 run_app 的日志和 HTTPS 指纹。
- **反向关系。**
  - 240da100（0.9.1dev，ProxyConnector 端口问题）的新测试名 `test_request_port` 出现在本题的 `WT/tests/test_proxy.py` L601。这只是名字层面的命中，语义无关。
  - 618335186（0.17.0a0）与本题没有关系。
- **影响。**
  - 按 D3 按仓库划分时，这几题落在同一侧，不需要额外处理。
  - 但如果本题作留出、1c1c0ea3 或 22a12cc2 进了训练，训练初态就会暴露本题的答案和隐藏目标测试。
  - 训练时要控制重复采样。

## 9. 修订建议（v1 §5）

**R-c #1（对应 I1）**

- 公开依据：题面标题和 L22 的一般表述（字段名里的无效字符应当被拒绝）；RFC 9110 规定 field-name = token，`HP` L59-65 的注释引用了同一套 tchar 定义。
- 改动：在 `HT` 的 `test_bad_headers` 参数表里加一个非示例的非 ASCII 字段名 `"f\N{CYRILLIC SMALL LETTER O}o: bar"`。
  - 这个字符的 UTF-8 编码是 `d0 be`：它不在首位，首字节不是 `c3`，也不含 `bf`。
  - 补丁见附录 C。
- expected 新增这个键，状态为 PASSED。状态按语义确定，不照抄 gold 的输出。
  - 键名以实跑的 short summary 为准：pytest 会把 U+043E 转义成 ASCII。
- 为什么选这个字符：它能同时拦住三类示例拟合——只拒 `ÿ` 或 `c3 bf`；只检查首字节；只往字符类里加 `\xc3` 或 `\xbf`。

**R-c #2（对应 I2、I3）**

- 公开依据：
  - 题面 L23 把示例里的 LF 和 FF 都称为不当空白、控制字符；
  - RFC 9112 的请求行语法要求用单个 SP 分隔。
  - RFC 9112 §3 允许接收方宽松地把 HTAB、VT、FF、裸 CR 当作 SP。但本题题面明确把 FF 判为不当，而 VT 与 FF 属于同一类，所以按题面要求拒绝是有依据的。
- 改动：新增参数化测试 `test_http_request_bad_status_line_other_whitespace`，两例都要求抛 `BadStatusLine`：
  - `b"GET /path\x0cHTTP/1.1"`：只有 FF，作为版本前的分隔；
  - `b"GET\x0b/path HTTP/1.1"`：VT 作为方法后的分隔。
  - 补丁见附录 C。
- expected 新增这 2 个键，状态为 PASSED。
- 两例各自的作用：
  - FF 单独一例说明"只拒 LF"不够；
  - VT 一例说明"只拒示例里那两个字符"不够。

**R-c #3（对应 I4，conditional）**

- 公开依据：题面 L23 的一般表述，即请求行含不当空白或控制字符就应当拒绝；而且 base 对这些输入本来就抛 `BadStatusLine`。
- 改动：新增 `test_http_request_ctl_in_target_rejected`，两例是 `b"GET /pa\nth HTTP/1.1"` 和 `b"GET /pa\x0cth HTTP/1.1"`，断言抛 `BadHttpMessage`。补丁见附录 D。
  - 断言用父类 `BadHttpMessage` 的原因：题面措辞对应 `BadStatusLine`，而 C 解析器把非法 URL 映射为 `InvalidURLError`（`WT/aiohttp/_http_parser.pyx` L829-834）。两个都接受，才不会在子类上造出 T1。
- expected 新增这 2 个键，状态为 PASSED。
- 正对照：
  - gold 预期失败（DID NOT RAISE），按 D4 改用 ALT1 作正对照，并记录 gold 的失败；
  - noop 预期通过。这两个键是回归保护键，不是目标键。
- 前提条件：
  - 先用私有矩阵实跑，确认 gold 确实接受、base 确实拒绝；
  - 独立复核同意"请求目标里的控制字符"属于核心要求。
  - 复核不同意，就不做 #3，I4 降为 G1/T3 登记（S2），探针分析时对 gold 式补丁注明这个缺口。

**R-f（对应 I5，可选）**

- 改动：把题面例 1 的 `invalid_header = "\xffoo: bar".encode()` 改成 `invalid_header = "\xffoo: bar"`。
- 类别：属于"改正对 base 公开行为的错误陈述"。
- base 上的实证有两处：
  - devcheck 的 `issue_ex1_literal` 一行：字面代码在 base 上已经抛 `InvalidHeader`；
  - `NOOP_LOG` L236-240：改正后的字节在 base 上不抛异常。
- 不改也不阻塞，P4 默认只登记。

**不建议**：对 3 个环境 FAILED 键做 R-a。没有误拒案例，按 v1 §5，没有误拒案例的修订不必专门去造。

**验收计划（R-c）**：

| 候选 | 当前材料 | 加上 R-c #1、#2 后 | 再加上 R-c #3 后 |
| --- | --- | --- | --- |
| noop | 0（2 个目标键 F） | 0（新增 3 个键也 F） | 0（#3 的两个键 P） |
| gold | 1 | 1 | 0（#3 两个键 F，记录在案） |
| ALT1 | 1（预测） | 1 | 1 |
| DG1 | 1（预测，即 T2b 命中） | 0（西里尔字母键和 vt 键 F） | 0 |

- 还可以加一个"只拒 LF"的部分解作第二个已知错误候选：保留 gold 的 `HDRRE`，请求行只加 `if "\n" in line`。它在当前材料上得 1，加 #2 后得 0。
- 需要保存：新版本；父版本（expected sha256 `79a761b4…`、hidden tree `eb81f695…`）；修订理由；触发反例（DG1 在当前材料上得 1，以及私有矩阵里 gold 接受请求目标内 LF/FF 的输出）。然后交 Codex 复核。
- 修订后仍受保护的公开要求：R1（两个非 ASCII 实例）；R2（示例、FF 单独、VT）；R2'（如果采用 #3）；以及 §3 列出的 P1–P8。

## 10. 需要协调者实跑的内容

**A. 当前材料（v1 §4 第 3 步 + T1 核对）**

1. 正式评分 DG1（附录 A），预期 reward 1、129/129。
   - 有效性核对：`projection.included_paths` 含 `aiohttp/http_parser.py`；`num_parsed_tests=129`；`keys_equal=true`；测试段正常完成。
   - 得 1 即 S1（T2b）命中。
2. 正式评分 ALT1（附录 B），预期得 1。如果得 0，看是哪些键失败：
   - 字段名相关的键失败，说明 token 白名单与某个回归键冲突，要重新审查 T1；
   - 请求行相关的键失败，说明控制字符检查太宽。
3. 私有行为矩阵（附录 E）。在同一张派生镜像里，依次对 base（noop）、gold、DG1、ALT1 运行，记录每个输入是"被接受"还是"抛了哪类异常"。决定性的几行：
   - `target_lf`、`target_ff`、`target_cr`、`target_tab`：gold 预期被接受，base 预期抛 `BadStatusLine`；
   - `hdr_name_cyr_o`、`reqline_vt_sep`：DG1 预期被接受。

**B. 修订后的材料**（仅当 A 的结论成立时）

- noop、gold、ALT1、DG1 各跑一次正式评分，对照 §9 的表。
- 新键的键名以实跑的 short summary 为准，再写进 expected。

**C. 读 devcheck 输出时看这几点**

- `env_import_versions` 的 `c_parser_available`，预期为 False；
- `repro_parser_issue_cases` 修复前打印 `FAILS 2`，且 `issue_ex1_literal` 一行为 OK（这可以证实 P4）；
- `repro_server_400_py_parser` 有没有打印 SETUP_ERROR；
- `public_http_parser_tests` 是否走了 `AIOHTTP_NO_EXTENSIONS=1` 分支，修复前后是否都全部通过；
- 每条命令的墙钟时间；
- 私有 gold 对照在新机器的镜像上是否仍然 noop 0、gold 1。

**D. 可选（清单第 29 项）**

以 agent 身份读 `/testbed/install.sh` 和 `/testbed/process_aiohttp_updateasyncio.py`，确认里面没有答案线索。

## 11. 暂定用途与处置

- `problem_localization`：yes。
- `capability_comparison`：conditional。还差两项：
  - 新机器 devcheck 证明公开开发路径可用，且私有 gold 对照为 noop 0、gold 1；
  - R-c 落地之前，比较报告要对得 1 的补丁做预登记的事后审计：是不是只拒示例字节；有没有让请求目标里的 LF/CR/FF 通过。
- `training_candidate`：no。I1–I3 尚未处理（S1）。满足以下三条后可以改为 yes：R-c #1、#2 验收通过；I4 经复核定案（修掉，或登记为 S2）；devcheck 通过。
- `heldout_candidate`：no。原因有三：同上的 S1；修订后只能作"标明版本的自建题"；X1——答案和目标测试出现在同仓两题的初态里，留出时要按仓库整体划分，并核对训练集初态。
- `intended_use`：`development_diagnostic`。
- 处置：`scope=static_review`，`state=needs_review`。原因是测试层的 S1 待 R-c，属于"静态候选待 actor 验证"。

## 12. 缺口与未查范围

- 没有运行任何项目代码。DG1、ALT1 的得分，以及 gold 接受请求目标内 LF/FF，都是推演结果。
- 没在镜像里核对 yarl 的版本和 `URL.build(encoded=True)` 的实际行为。推断依据是：`test_parse_uri_utf8` 能通过，说明这条路径不校验字符。
- 本题的 actor 条件（新机器）等 devcheck；模型实际收到的消息与真实求解（清单第 33–36 项）没查。
- gold 下 multipart 和客户端响应解析的行为变化没跑。
- 两个没导出的 untracked 文件，内容未知。
- 唯一最值得先做的下一步：在新机器的同一张派生镜像里执行 §10 A，即 DG1 正式评分加私有矩阵（ALT1 可以同批），一次性确认 I3 和 I4。

## 附录 A：退化候选 DG1（只拒示例字节，对应 v1 §4 第 3 步）

- 写法：只看 gold 的两个修改位置（`HDRRE` 常量、请求行切分），外加题面示例，就能写出这个补丁。
- 它违反的公开要求有两条，都能用具体输入看出来：
  - R1：`POST / HTTP/1.1\r\nf\xd0\xbeo: bar\r\n\r\n` 会被接受；
  - R2：`GET\x0b/path HTTP/1.1\r\n\r\n` 会被当成 `GET /path` 接受。
- gold 对这两个输入都会抛异常。已在 base 副本上验证 `git apply --check` 与 `py_compile` 通过。

```diff
diff --git a/aiohttp/http_parser.py b/aiohttp/http_parser.py
--- a/aiohttp/http_parser.py
+++ b/aiohttp/http_parser.py
@@ -65,7 +65,9 @@ ASCIISET: Final[Set[str]] = set(string.printable)
 #     token = 1*tchar
 METHRE: Final[Pattern[str]] = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")
 VERSRE: Final[Pattern[str]] = re.compile(r"HTTP/(\d).(\d)")
-HDRRE: Final[Pattern[bytes]] = re.compile(rb"[\x00-\x1F\x7F()<>@,;:\[\]={} \t\"\\]")
+HDRRE: Final[Pattern[bytes]] = re.compile(
+    rb"[\x00-\x1F\x7F()<>@,;:\[\]={} \t\"\\]|\xc3\xbf"
+)
 HEXDIGIT = re.compile(rb"[0-9a-fA-F]+")
 
 
@@ -546,6 +548,8 @@ class HttpRequestParser(HttpParser[RawRequestMessage]):
     def parse_message(self, lines: List[bytes]) -> RawRequestMessage:
         # request line
         line = lines[0].decode("utf-8", "surrogateescape")
+        if "\n" in line or "\x0c" in line:
+            raise BadStatusLine(line)
         try:
             method, path, version = line.split(maxsplit=2)
         except ValueError:
```

## 附录 B：合理替代解 ALT1（比 gold 更完整；R-c #3 的 D4 正对照）

- 字段名：改用 RFC token 白名单做 `fullmatch`。
- 请求行：先拒绝 C0 控制字符和 DEL，再按单个 SP 切分。
- 已在 base 副本上验证 `git apply --check` 与 `py_compile` 通过。

```diff
diff --git a/aiohttp/http_parser.py b/aiohttp/http_parser.py
--- a/aiohttp/http_parser.py
+++ b/aiohttp/http_parser.py
@@ -66,6 +66,10 @@ ASCIISET: Final[Set[str]] = set(string.printable)
 METHRE: Final[Pattern[str]] = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")
 VERSRE: Final[Pattern[str]] = re.compile(r"HTTP/(\d).(\d)")
 HDRRE: Final[Pattern[bytes]] = re.compile(rb"[\x00-\x1F\x7F()<>@,;:\[\]={} \t\"\\]")
+# field-name = token (RFC 9110 section 5.1); ASCII tchar only
+HDR_NAME_TOKEN: Final[Pattern[bytes]] = re.compile(rb"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")
+# request-line must not contain C0 controls or DEL (incl. HTAB, LF, VT, FF, CR)
+REQUEST_LINE_CTL: Final[Pattern[str]] = re.compile(r"[\x00-\x1f\x7f]")
 HEXDIGIT = re.compile(rb"[0-9a-fA-F]+")
 
 
@@ -146,7 +150,7 @@ class HeadersParser:
                 raise InvalidHeader(line)
 
             bvalue = bvalue.lstrip(b" \t")
-            if HDRRE.search(bname):
+            if not HDR_NAME_TOKEN.fullmatch(bname):
                 raise InvalidHeader(bname)
             if len(bname) > self.max_field_size:
                 raise LineTooLong(
@@ -546,8 +550,10 @@ class HttpRequestParser(HttpParser[RawRequestMessage]):
     def parse_message(self, lines: List[bytes]) -> RawRequestMessage:
         # request line
         line = lines[0].decode("utf-8", "surrogateescape")
+        if REQUEST_LINE_CTL.search(line):
+            raise BadStatusLine(line)
         try:
-            method, path, version = line.split(maxsplit=2)
+            method, path, version = line.split(" ", maxsplit=2)
         except ValueError:
             raise BadStatusLine(line) from None
 
```

## 附录 C：R-c #1 与 #2 的隐藏测试修订

- 路径按评分容器里的 `r2e_tests/test_1.py` 写；在私有包里对应 `PRIV/hidden_tests/test_1.py`。
- 已在副本上验证：它与附录 D 以任意顺序叠加都能 `git apply`，结果能通过 `py_compile`。

```diff
diff --git a/r2e_tests/test_1.py b/r2e_tests/test_1.py
--- a/r2e_tests/test_1.py
+++ b/r2e_tests/test_1.py
@@ -179,6 +179,7 @@ def test_c_parser_loaded():
         "Foo : bar",  # https://www.rfc-editor.org/rfc/rfc9112.html#section-5.1-2
         "Foo\t: bar",
         "\xffoo: bar",
+        "f\N{CYRILLIC SMALL LETTER O}o: bar",  # non-ASCII inside the name (d0 be)
     ),
 )
 def test_bad_headers(parser: Any, hdr: str) -> None:
@@ -686,6 +687,21 @@ def test_http_request_bad_status_line_whitespace(parser: Any) -> None:
         parser.feed_data(text)
 
 
+@pytest.mark.parametrize(
+    "line",
+    (
+        b"GET /path\x0cHTTP/1.1",  # FF alone as a separator
+        b"GET\x0b/path HTTP/1.1",  # VT as a separator
+    ),
+    ids=("ff-separator", "vt-separator"),
+)
+def test_http_request_bad_status_line_other_whitespace(
+    parser: Any, line: bytes
+) -> None:
+    with pytest.raises(http_exceptions.BadStatusLine):
+        parser.feed_data(line + b"\r\n\r\n")
+
+
 def test_http_request_upgrade(parser: Any) -> None:
     text = (
         b"GET /test HTTP/1.1\r\n"
```

预计新增的键（键名以实跑为准），语义状态都是 PASSED：

- `test_bad_headers[py-parser-pyloop-f?o: bar]`，其中 `?` 代表 pytest 对 U+043E 的 ASCII 转义；
- `test_http_request_bad_status_line_other_whitespace[py-parser-pyloop-ff-separator]`；
- `test_http_request_bad_status_line_other_whitespace[py-parser-pyloop-vt-separator]`。

## 附录 D：R-c #3 的隐藏测试修订（conditional）

```diff
diff --git a/r2e_tests/test_1.py b/r2e_tests/test_1.py
--- a/r2e_tests/test_1.py
+++ b/r2e_tests/test_1.py
@@ -775,6 +775,20 @@ def test_http_request_parser_bad_nonascii_uri(parser: Any) -> None:
         parser.feed_data(b"GET \xff HTTP/1.1\r\n\r\n")
 
 
+@pytest.mark.parametrize(
+    "line",
+    (
+        b"GET /pa\nth HTTP/1.1",  # LF inside the request-target
+        b"GET /pa\x0cth HTTP/1.1",  # FF inside the request-target
+    ),
+    ids=("lf-in-target", "ff-in-target"),
+)
+def test_http_request_ctl_in_target_rejected(parser: Any, line: bytes) -> None:
+    # BadStatusLine (issue wording) or InvalidURLError (C-parser mapping) both ok
+    with pytest.raises(http_exceptions.BadHttpMessage):
+        parser.feed_data(line + b"\r\n\r\n")
+
+
 @pytest.mark.parametrize("size", [40965, 8191])
 def test_http_request_max_status_line(parser, size) -> None:
     path = b"t" * (size - 5)
```

预计新增的键：`test_http_request_ctl_in_target_rejected[py-parser-pyloop-lf-in-target]` 和 `[...-ff-in-target]`，语义状态都是 PASSED。

## 附录 E：私有行为矩阵

- 用法：在派生镜像里，对每个候选（noop、gold、DG1、ALT1）各应用一次补丁，然后运行下面的命令。只作私有对照，不进解题者的环境说明。
- 脚本全部用 ASCII 字节字面量，已在本机做过语法编译检查，没有执行。

```bash
cd /testbed && PYTHONDONTWRITEBYTECODE=1 /testbed/.venv/bin/python - <<'EOF'
import asyncio
from unittest import mock

import aiohttp.http_parser as hp

CASES = [  # (name, parser kind, raw bytes)
    ("ex_hdr_name_ff", "req", b"POST / HTTP/1.1\r\n\xc3\xbfoo: bar\r\n\r\n"),
    ("hdr_name_cyr_o", "req", b"POST / HTTP/1.1\r\nf\xd0\xbeo: bar\r\n\r\n"),
    ("hdr_name_raw_e9", "req", b"POST / HTTP/1.1\r\nf\xe9o: bar\r\n\r\n"),
    ("hdr_name_slash", "req", b"POST / HTTP/1.1\r\nFo/o: bar\r\n\r\n"),
    ("ex_reqline_lf_ff", "req", b"GET\n/path\x0cHTTP/1.1\r\n\r\n"),
    ("reqline_ff_sep", "req", b"GET /path\x0cHTTP/1.1\r\n\r\n"),
    ("reqline_vt_sep", "req", b"GET\x0b/path HTTP/1.1\r\n\r\n"),
    ("reqline_tab_sep", "req", b"GET\t/path HTTP/1.1\r\n\r\n"),
    ("target_lf", "req", b"GET /pa\nth HTTP/1.1\r\n\r\n"),
    ("target_ff", "req", b"GET /pa\x0cth HTTP/1.1\r\n\r\n"),
    ("target_cr", "req", b"GET /pa\rth HTTP/1.1\r\n\r\n"),
    ("target_tab", "req", b"GET /pa\tth HTTP/1.1\r\n\r\n"),
    ("target_ctl01", "req", b"GET /pa\x01th HTTP/1.1\r\n\r\n"),
    ("version_ff", "req", b"GET /path HTTP/1\x0c1\r\n\r\n"),
    ("double_sp", "req", b"GET  /path HTTP/1.1\r\n\r\n"),
    ("keep_plain", "req", b"GET /path HTTP/1.1\r\n\r\n"),
    ("keep_utf8_value", "req", b"GET /path HTTP/1.1\r\nx-test:\xd1\x82\xd0\xb5\xd1\x81\xd1\x82\r\n\r\n"),
    ("keep_utf8_path", "req", b"GET /\xd0\xbf\xd1\x83\xd1\x82\xd1\x8c HTTP/1.1\r\n\r\n"),
    ("keep_nonascii_uri", "req", b"GET \xff HTTP/1.1\r\n\r\n"),
    ("keep_getpath", "req", b"getpath \r\n\r\n"),
    ("resp_nonascii_name", "resp", b"HTTP/1.1 200 OK\r\n\xc3\xbfoo: bar\r\n\r\n"),
    ("resp_no_reason", "resp", b"HTTP/1.1 200\r\n\r\n"),
]

loop = asyncio.new_event_loop()
for name, kind, data in CASES:
    cls = hp.HttpRequestParserPy if kind == "req" else hp.HttpResponseParserPy
    p = cls(mock.Mock(), loop, 2**16, max_line_size=8190, max_headers=32768, max_field_size=8190)
    try:
        msgs = p.feed_data(data)[0]
        out = "ACCEPT " + ascii([(getattr(m, "method", None), getattr(m, "path", None), list(m.headers.items())) for m, _ in msgs])
    except Exception as e:
        out = type(e).__name__ + " " + ascii(str(e))[:90]
    print(name.ljust(20), out)
loop.close()
EOF
```

各候选在决定性几行上的预期（推演）：

| 行 | base（noop） | gold | DG1 | ALT1 |
| --- | --- | --- | --- | --- |
| `ex_hdr_name_ff`、`ex_reqline_lf_ff` | ACCEPT | 抛异常 | 抛异常 | 抛异常 |
| `hdr_name_cyr_o` | ACCEPT | `InvalidHeader` | ACCEPT | `InvalidHeader` |
| `reqline_ff_sep` | ACCEPT | `BadStatusLine` | `BadStatusLine` | `BadStatusLine` |
| `reqline_vt_sep` | ACCEPT | `BadStatusLine` | ACCEPT | `BadStatusLine` |
| `target_lf`、`target_ff` | `BadStatusLine` | ACCEPT | `BadStatusLine` | `BadStatusLine` |
| `target_cr`、`target_tab` | `BadStatusLine` | ACCEPT | `BadStatusLine` | `BadStatusLine` |
| `keep_*` 各行 | 不变：接受，或 `InvalidURLError`、`BadStatusLine` | 不变 | 不变 | 不变 |
| `resp_nonascii_name` | ACCEPT | `InvalidHeader`（未测范围） | ACCEPT | `InvalidHeader` |

## 附录 F：阅读范围

- **方法**：角色卡；八方面协议；R2E 环境卡；记录模板；40 项清单；统一标准 v1。
- **公开读者产物**：`OUTPUT_DIR/public_read.md`、`commands.json`。
- **公开包**：
  - `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`；`worktree_manifest.json` 只看了元数据段。
  - `HP`：读了 L1-760、L960-999。
  - `WT/aiohttp/http_exceptions.py`：全文。
  - `_http_parser.pyx`、`helpers.py`、`web_protocol.py`、`multipart.py`、`pytest_plugin.py`：只读了相关段或 grep。
  - `setup.cfg`：读了 L100-171。
  - `WT/tests/test_http_parser.py` 与 `WT/tests/conftest.py`：与隐藏测试做了 diff。
- **私有包**：全部文件都读过（`hidden_tests` 两个文件读全文）。
- **运行原件**：
  - `run_refs.json` 列出的 4 行 current 账本和对应日志：noop 读了全部失败段，gold 读了汇总；
  - M3 账本 L18、L67，以及 M3 a1 日志的汇总行；
  - 所有日志都核对了 sha256。
- **跨题材料**：两份跨题比对；另外打开了 1c1c0ea3、22a12cc2 的 `http_parser.py` 相关段和测试 grep，240da100 的题面开头，618335186 只做了 grep。
- **没有读**：任何历史调查、`history/`、`r2e_env_repair_20260924` 文档目录、各审查目录、本批 README、board、assignments；`OUTPUT_DIR` 里其它文件；其它题的私有包；`runs/` 下的分析或汇总文件；`docs/`、`examples/`；yarl 与 llhttp 源码。
