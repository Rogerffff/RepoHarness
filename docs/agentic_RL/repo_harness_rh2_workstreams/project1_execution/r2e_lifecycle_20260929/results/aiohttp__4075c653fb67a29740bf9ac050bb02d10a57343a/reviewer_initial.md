# aiohttp__4075c653 独立复核初判（reviewer_initial）

2026-09-29 · 独立复核者（Claude，干净上下文）· 单题闭环试行第一步。写于读主审产物、公开读者产物与历史之前。

**材料版本**：当前材料就是来源版（`revisions.json` 为 `[]`）。expected `sha256:79a761b4…`、隐藏测试树 `eb81f695…`、gold `f99fe925…`、`run_tests.sh` `8285765f…`，与 `grading_bundle.json` / `validation_bundle.json` 两行、四条 current 账本、日志开头的 `RH2_SETUP_HIDDEN_TESTS_TREE` / `RH2_SETUP_ENTRY_SHA256` 逐项一致（本地 `shasum` 核对）。派生镜像 `rh2-r2e-derived/aiohttp:4075c653fb67-r2e_derive_v1`（image id `0d785442…`，recipe `r2e_derive_v1`）。

**证据层级说明**：“日志复读”是重读已有 RH2 运行原件，不是独立重跑；“源码推断”是读代码推出的行为；“本地标准库核对”是在 scratchpad 里只用 Python 标准库 `re` / `str.split` 复现正则与分割语义（不导入 aiohttp，不是项目代码运行，也不是评分证据）。

## 0. 初判摘要

| 项 | 初判 | 证据层级 |
| --- | --- | --- |
| 题目目标 | R1：请求头**名**含非法字符（示例 `ÿ`）时 `feed_data` 抛 `BadHttpMessage`；R2：请求行用不当空白 / 控制字符分隔（示例 `GET\n/path\x0cHTTP/1.1`）时抛 `BadStatusLine` | 公开题面 |
| 严重度 | **S1（T2c）**：两条核心要求的新断言都只用题面示例的字面值。§6 的退化候选按源码推断会得 1（T2b，待正式评分） | 断言对照 + 源码推断 |
| 误拒（T1） | 未发现。目标键只断言异常类型，类型与题面 Expected Behavior 逐字一致 | 源码推断 |
| 非 PASSED 期望键 | 3 个 FAILED 都因 C 扩展缺失（`HttpRequestParserC` 不可导入）；在 Python 解析器里的正确修复（含更完整的修复）不会翻转它们 | 日志复读 |
| 题面 | **P4**：示例 1 的字面代码把 bytes 放进 f-string，得到的头名含反斜杠，而 base 的 `HDRRE` 已拒绝反斜杠，所以示例 1 照抄在 base 上会抛异常、不复现；文字“invalid character ÿ”足以消解 | 源码推断 + 本地标准库核对（未在 base 实跑） |
| 题目关系 | **X1**：本题修复（重构后形式）和两处新测试已在 aiohttp__1c1c0ea3、aiohttp__22a12cc2 的公开初态里；gold 逐字扫描漏报 | 同仓公开包核对 |
| 材料 / 回归 / gold | 未发现材料错配或错误回归键；gold 修到两个原例；gold 对响应头名、multipart 部件头名的连带影响未测，登记 | 日志 + 源码 |
| 用途（v1） | 问题定位 yes；能力比较 conditional；训练候选 no（R-c 前）；留出评测 no | — |
| 唯一优先下一步 | 对当前材料正式评分 §6 退化候选 1 次；随后同一轮实施 §7 的 R-c-1 / R-c-2，并用同一候选做“已知错误候选仍为 0”的验收 | — |

## 1. 实际读取范围

- **角色与方法**：`roles/reviewer_r2e.md` 全文。`roles/investigator_r2e.md` 由 Read 一次载入全文（53 行）；口径只采用“材料”“R2E 的评分口径”“第二批补充规则”“单题闭环试行补充”四节，其余开头说明、“对每题按顺序完成”“边界”是角色说明，不含任何主审产物。`quality_review_protocol_20260920.md`、`r2e_lifecycle_20260929/r2e_environment_card.md`、`quality_batch01_20260921/record_template.md`、`task_screening_standard_v1_20260925.md` 全文。
- **PUBLIC_DIR**：`user_prompt.txt`、`environment_brief.md`、`public_bundle.json` 全文；`worktree_manifest.json` 的 export / initial_diff / untracked 字段与文件清单；工作树 `aiohttp/http_parser.py` 1–720、975–999 行，`aiohttp/http_exceptions.py` 全文，`aiohttp/helpers.py` 77、490–520 行，`aiohttp/multipart.py` 685–705 行，`setup.py` 全文，`setup.cfg` 的 `[tool:pytest]`，`Makefile` 1–60 行，`vendor/`（`vendor/llhttp` 是空目录）与 `vendor/README.rst`，`CHANGES/` 下 6 个片段；`tests/test_http_parser.py`、`tests/conftest.py` 与隐藏测试逐行 diff；`tests/` 下若干 grep。
- **PRIVATE_DIR**：`gold.patch`、`run_tests.sh`、`revisions.json`、`run_refs.json`、`expected_output.json`（129 键全列）、`hidden_tests/test_1.py`（全文）、`hidden_tests/conftest.py`（全文）、`hidden_tests/__init__.py`（空）、`grading_bundle.json`、`validation_bundle.json`。
- **运行原件**（`run_refs.json` 的 4 条 current 与 2 条 independent_reference）：4 个账本第 4 行全部字段；R-f noop 日志全文；R-f gold 日志的头部、FAILURES 段与摘要；环境轮 noop / gold 日志的关键行（grep）；M3 两份 `test_output.txt` 的摘要行（grep）。6 份日志的 sha256 与 `run_refs.json` 一致。
- **跨题**：`cross_task_gold_scan.json`、`cross_task_test_scan.json` 中涉及本题的对；同仓公开包 aiohttp__1c1c0ea3 的 `worktree/aiohttp/http_parser.py`（60–80、160–180、562–600 行）与 `worktree/tests/test_http_parser.py`（150–240、800–840 行），aiohttp__22a12cc2 同两文件的 grep；5 个 aiohttp 公开包 `public_bundle.json` 的标题行。未读任何其它题的私有包或审查产物。
- **未读**：OUTPUT_DIR 其它文件、`history/`、各审查目录、本批 README / `board.json` / `assignments.json`、`runs/` 下分析与汇总文件；`initial.diff` 原件未打开（manifest 记载初态只改 `Makefile`）；本题 devcheck 目录（本次未提供）。

## 2. 八方面：查了什么、没查什么

| 方面 | 已查 | 未查 / 未知 |
| --- | --- | --- |
| 公开需求 | 两条需求与异常类型；P4 示例 1；范围歧义（请求 vs 响应、头名 vs 头值）；base 注释引用 RFC 9110 token 定义（`http_parser.py:59–66`） | 模型实际收到的完整消息（环境卡：代码配置，未见捕获） |
| 材料与初始问题 | base `e181a0e4`；初态只改 `Makefile`；noop 目标键失败原因＝题面“未抛异常”；哈希全部一致 | 示例 1 字面代码未在 base 实跑 |
| 测试是否测到要求 | 2 个目标键的断言与 fixture（`parser` 只含 Py 解析器，`test_1.py:32–66`）；129 键逐个过了名称与状态，与头名 / 请求行相关的约 20 个读了测试体 | payload / deflate 类回归键只核名称与 noop / gold 状态 |
| 是否误拒合理解 | 4 条不同实现路线（§3 表后），都按源码推断 | 未实跑任何替代解 |
| 回归与 gold | gold 两处改动；`HeadersParser` 同时服务响应解析与 multipart（`multipart.py:699–700`）；响应状态行未改 | 响应头名非 ASCII、multipart 部件头、请求目标内 CTL 均无测试 |
| agent 开发条件 | `environment_brief.md:10–13`；评分侧 pytest 7.4.2、pytest-asyncio 0.23.8、pytest-cov 4.1.0、brotli 可用（rf noop 日志 18–23、67） | actor 侧未见 devcheck；brief 没写 3 个 C 解析器公开测试恒失败 |
| 交付与评分边界 | gold 只改 `aiohttp/http_parser.py`，账本 `projection.included_paths` 相符；隐藏 conftest 依赖候选可改的 `aiohttp.pytest_plugin` 与根 `setup.cfg` addopts（通用边界，逐题只核适用性） | 平台级审计不重做 |
| 题目关系与用途 | X1 两对（§10）；类型：HTTP/1.1 解析器输入校验加固，小改动、定位明确 | 基座难度、成败混合（需真实模型） |

## 3. 需求—断言双向表

| 公开要求 / 合理旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖 | 执行证据 |
| --- | --- | --- | --- | --- |
| R1 请求头名含 `ÿ` → `BadHttpMessage` | `user_prompt.txt:4,7,12,22` | `test_bad_headers[py-parser-pyloop-\xffoo: bar]`（`test_1.py:171–187`），`pytest.raises(BadHttpMessage)` | 部分：只有示例字面值（UTF-8 `\xc3\xbf`） | noop FAILED `DID NOT RAISE`（rf noop 日志 236–240）；gold PASSED（rf gold 日志 39） |
| R1 的非示例实例：其它非 token / 非 ASCII 头名字节 | 同上；`http_parser.py:59–68`（tchar 为 ASCII，已有头名黑名单） | 无 | **缺失 → T2c** | 待 R-c-1 |
| R2 请求行 `GET\n/path\x0cHTTP/1.1` → `BadStatusLine` | `user_prompt.txt:4,7,17,23` | `test_http_request_bad_status_line_whitespace[py-parser-pyloop]`（`test_1.py:683–686`） | 部分：只有示例字面值 | noop FAILED（rf noop 日志 251–254）；gold PASSED（rf gold 日志 89） |
| R2 的非示例实例：HTAB、VT 作分隔符 | 同上 | 无 | **缺失 → T2c** | 待 R-c-2 |
| 旧行为：头值接受 UTF-8 与非 UTF-8 字节 | surrogateescape 解码（`http_parser.py:205–206`）；公开同名测试 | `test_http_request_parser_utf8` / `_non_utf8`（`test_1.py:704–736`） | 覆盖 | noop / gold PASSED |
| 旧行为：响应头值宽松（`\x01`） | `lax = not DEBUG`（`http_parser.py:640`）；公开同名测试 | `test_http_response_parser_lenient_headers`（`test_1.py:858–864`） | 覆盖 | PASSED |
| 旧行为：非 UTF-8 头行报 `InvalidHeader` 且消息可编码 | `CHANGES/7715.bugfix` | `test_unpaired_surrogate_in_header_py`（`test_1.py:190–204`） | 覆盖 | PASSED |
| 旧行为：非 ASCII 请求目标 → `InvalidURLError`；Py 解析器接受 UTF-8 路径 | 公开同名测试；`CHANGES/7712.bugfix` | `test_1.py:768–775`、`1093–1103` | 覆盖 | PASSED |
| 旧行为：超长名 / 值 / 请求行 → `LineTooLong`（带消息） | 公开同名测试 | `test_1.py:574–655`、`778–802` | 覆盖（超长名只含 `t`，与新校验先后无关） | PASSED |
| 旧行为：方法 / 版本校验，坏状态行消息不被转义 | `CHANGES/7700.bugfix` | `test_1.py:675–680`、`753–765` | 覆盖 | PASSED |

反查：两个目标键的断言都能追到题面（异常类名逐字出现在 Expected Behavior，`InvalidHeader`、`BadStatusLine` 都是 `BadHttpMessage` 子类，`http_exceptions.py:88、96`）。没有精确文案、内部 helper 名、mock 形状或执行顺序要求。

**不同实现路线（误拒检查，源码推断）**

- **A1（合理替代解）**：头名改用 tchar 白名单（解码后 `TOKENRE.fullmatch`，即后来上游在 aiohttp__1c1c0ea3 公开初态的写法，该包 `http_parser.py:73–74、172`）＋ `line.split(" ", maxsplit=2)`。129 键预计全部一致：`test_parse_headers_longline` 接受 `LineTooLong` 或 `BadHttpMessage`（`test_1.py:260–265`），超长名测试只用 `t`。可作 R-c 的替代正对照。
- **A2**：请求行出现任何 ASCII CTL 就抛 `BadStatusLine`，保留空白分割：目标键过。若改用 `str.isprintable()`，`GET \xff HTTP/1.1` 会变成 `BadStatusLine` 而不是 `InvalidURLError`，`test_http_request_parser_bad_nonascii_uri` 失败；该测试在公开测试文件里，属公开依据，不算误拒。
- **A3**：另外拒绝请求头值里的 CTL。只作用于请求方向时得分不变；改在共用的 `HeadersParser` 会破坏公开的 `test_http_response_parser_lenient_headers`，不算误拒。
- **A4**：拒绝头值中的非 ASCII：破坏公开的 utf8 / non_utf8 测试（RFC 允许 obs-text），不算误拒。

## 4. R2E 专项

- **(a) 非 PASSED 期望键**：`test_c_parser_loaded`、`test_invalid_character[pyloop]`、`test_invalid_linebreak[pyloop]` 期望 FAILED。原因是 `aiohttp._http_parser` 扩展没有构建，`http_parser.py:985–999` 的导入落空。三键在 noop、gold、M3 独立 runner 上都以同样原因失败（rf noop 日志 159–213：`AssertionError` 与 `NameError: name 'HttpRequestParserC' is not defined`；M3 a1 / a2 `test_output.txt` 455–457）。Python 解析器内的正确修复不会翻转它们。能翻转的只有：放入可导入的 C 扩展（同时给 `parser` / `response` fixture 增加 `c-parser` 参数化键 → unexpected → 0）；改 `NO_EXTENSIONS` 让它们变 SKIPPED（键缺失 → 0）；把 `HttpRequestParserC` 指到 Py 类（参数化 ID 重复，键全变 → 0）。三者都不是合理修复。公开工作树 `vendor/llhttp` 为空（gitlink 未导出；`setup.py:20–42`、`vendor/README.rst:7–23` 要求子模块和 npm 构建），镜像里有无子模块内容未知。**风险低，登记**；但 `environment_brief.md` 没写这 3 个公开测试在本环境恒失败（环境卡 §2 要求逐题写明），建议补一句中性说明，减少 agent 去“修”它们的诱因。
- **(b) 题面报错是否出现在 noop 目标键**：是。两目标键 noop 都是 `DID NOT RAISE`，输入分别为 `b'POST / HTTP/1.1\r\n\xc3\xbfoo: bar\r\n\r\n'` 与 `b'GET\n/path\x0cHTTP/1.1\r\n\r\n'`（rf noop 日志 236–240、251–254；环境轮 noop 日志同行号），与题面“No exceptions are raised”一致。示例 1 的字面代码不是这个输入，见 §5 P4。
- **(c) 修法泄漏**：题面没有修复代码（`HDRRE`、`split(" ")` 都未出现）。“Example Buggy Code”就是隐藏测试的输入，所以不是 P1，但直接造成 T2c。
- **(d) 测试支撑、搬迁伪影、撞键**：只有一个隐藏测试文件，不会跨文件撞键；隐藏 conftest 与公开 `tests/conftest.py` 逐字相同；不从 `tests.*` 导入 helper。依赖候选可改的 `aiohttp.pytest_plugin`（`loop` fixture 与 `pyloop` 参数）和根 `setup.cfg` addopts：`-m "not dev_mode"` 使 3 个 dev_mode 测试被 deselect（rf noop 日志 24；`setup.cfg:134`），`filterwarnings = error`（`setup.cfg:135–136`），`xfail_strict = true`（`setup.cfg:169`）。合理修复不碰这些；候选若删掉 `-m` 会多出键而得 0，属于候选侧行为。
- **(e) 时间、随机、资源敏感**：纯解析单测，pytest 用时 4.4–4.6 秒，内存峰值约 434–443 MB（账本 `resource.mem_peak_mb`），没有时序或随机键。
- **(f) 修订**：无（`revisions.json` 与 `run_refs.json` 的 `material_revisions` 都为空）。

## 5. 严重度（v1 §4）与其它问题

1. **第 1 步**：两条核心要求都有直接断言 → 不命中 T2a。
2. **第 2 步：命中。** R1 唯一的新断言输入 `"\xffoo: bar"`（`test_1.py:181`）就是题面的 `"\xffoo: bar"`（`user_prompt.txt:12`）；R2 唯一的新断言输入 `b"GET\n/path\fHTTP/1.1\r\n\r\n"`（`test_1.py:684`）与题面 `b"GET\n/path\x0cHTTP/1.1\r\n\r\n"`（`user_prompt.txt:17`）逐字节相同。`test_bad_headers` 其余 7 个参数在 base 上已通过（rf noop 日志 31–37），不是本缺陷的实例。→ **S1（T2c）×2，走 R-c。**
3. **第 3 步**：退化候选见 §6，源码推断得 1 → 预计 T2b，待正式评分确认。
4. **第 4 步**：现有得 1 的候选只有 gold。gold 对 §7 列出的非示例实例都正确（本地标准库核对：`\x7F-\xFF` 覆盖所有 ≥0x80 字节；`split(" ")` 让 HTAB、VT、裸 CR、`\x1f`、NBSP 分隔都报错）。gold 仍接受“单空格分隔、但请求目标里含 CTL”（如 `GET /pa\x01th HTTP/1.1`）。它是否属于“status line contains ... control characters”的同一核心要求，我判为**解读未定、倾向否**：示例里的两个控制字符都用作分隔符，标题强调 malformed，且 Py 解析器对请求目标内容一向宽松（`test_1.py:1093–1103`）。登记为 T3 / 待定，不升 S1，也不写进 R-c。
5. **结论**：**S1（T2c；T2b 待测）**，进训练前必须完成 R-c。

**其它问题**

- **P4（登记）**：示例 1 先 `invalid_header = "\xffoo: bar".encode()`，再写进 f-string（`user_prompt.txt:12–13`）。bytes 在 f-string 里按 `b'...'` 形式展开，请求头行变成 `b'\xc3\xbfoo: bar'`（反斜杠是字面字符），头名 `b"b'\\xc3\\xbfoo"` 含反斜杠；base `HDRRE`（`http_parser.py:68`）已包含反斜杠，`http_parser.py:149–150` 会抛 `InvalidHeader`。所以照抄示例 1 在 base 上**会抛异常**，与题面“Actual Behavior: No exceptions are raised”不符（本地标准库核对：base 正则在 span (2, 3) 命中 `\\`；未在 base 实跑）。公开文字“due to the invalid character `ÿ`”能消解：按字面构造 `"...\xffoo: bar...".encode()` 或 `b"...\xc3\xbfoo..."` 就能复现。风险是 agent 照抄示例、误以为头名部分已经正常，只修请求行，结果 0 分；公开测试也不会暴露这一点（公开测试没有 `ÿ` 参数）。
- **范围歧义（登记，不扩大需求）**：题面说“The HTTP parser”，示例都是请求方向。响应状态行（`http_parser.py:656`，仍按任意空白分割）、请求头值里的 CTL、请求目标里的 CTL 都不在明确要求内，也都没有测试。
- **开发缺口（轻）**：见 §4(a)，brief 未列 3 个 C 解析器公开测试恒失败。
- **未发现**：T1 误拒、错误回归键、材料错配（X2）、P1 / P2 / P6。

## 6. 退化候选 D（第 3 步，只凭 gold 修改位置写出）

文件 `aiohttp/http_parser.py`，两处，都在 gold 的修改位置：

1. 第 68 行 `HDRRE`：不扩字符类，只在末尾追加题面示例字节序列的交替分支：
   ```python
   HDRRE: Final[Pattern[bytes]] = re.compile(rb"[\x00-\x1F\x7F()<>@,;:\[\]={} \t\"\\]|\xc3\xbf")
   ```
   只拦 UTF-8 编码的 `ÿ`，其余非 ASCII 头名照旧放行（硬编码示例值）。
2. `HttpRequestParser.parse_message`（第 546–552 行）：保留 `line.split(maxsplit=2)`，在 `try:` 前插入
   ```python
   if "\n" in line or "\x0c" in line:
       raise BadStatusLine(line)
   ```
   只拦题面示例的两个字符。

**违反的公开要求与可见输入**：
- R1（“headers with invalid characters” → `BadHttpMessage`）：`b"POST / HTTP/1.1\r\n\xe4\xb8\xadoo: bar\r\n\r\n"`、`b"POST / HTTP/1.1\r\nFo\xe9: bar\r\n\r\n"` 在 D 下正常解析，不抛异常。
- R2（“improper whitespace and control characters” → `BadStatusLine`）：`b"GET\t/path HTTP/1.1\r\n\r\n"`、`b"GET /path\x0bHTTP/1.1\r\n\r\n"` 在 D 下仍被 `str.split()` 当作空白分隔而接受。

**预计当前材料得分**：1（129/129）。源码推断：两个目标键命中新分支；回归键里没有含 `\xc3\xbf` 的头名，也没有含 `\n` / `\x0c` 的请求行。
**协调者核对项**：账本 `projection.included_paths == ["aiohttp/http_parser.py"]`、日志 `RH2_SETUP_APPLY_RC=0`、日志摘要里两个目标键为 PASSED、`expected_match` 为 129/129。得 1 即 T2b 成立。

## 7. 修订建议（v1 §5，预授权模板内）

**R-c-1（R1 非示例实例）** 放进 `hidden_tests/test_1.py`，紧接 `test_bad_headers` 之后：

```python
@pytest.mark.parametrize(
    "name",
    (b"\xe4\xb8\xadoo", b"F\xc3\xa9o", b"Fo\xe9"),
    ids=("utf8-cjk", "utf8-e-acute", "raw-latin1-byte"),
)
def test_bad_header_name_non_ascii(parser: Any, name: bytes) -> None:
    text = b"POST / HTTP/1.1\r\n" + name + b": bar\r\n\r\n"
    with pytest.raises(http_exceptions.BadHttpMessage):
        parser.feed_data(text)
```

- 公开依据：题面把 `ÿ` 当作“invalid character”的例子，要求“headers with invalid characters”抛 `BadHttpMessage`（`user_prompt.txt:4,7,22`）；base 注释引用 RFC 9110 token 定义、tchar 全为 ASCII（`http_parser.py:59–66`），且已有头名黑名单（`:68`、`:149`），`ÿ` 除了“不是 token 字符”没有任何特殊之处；base 刻意用 surrogateescape 处理非 UTF-8，`CHANGES/7715.bugfix` 要求不出现未处理异常，所以原始非 UTF-8 字节也应得到 `BadHttpMessage` 而不是崩溃。
- 三个实例各挡一类特判：CJK 与示例没有共享字节；`é` 与 `ÿ` 共用 UTF-8 首字节 `\xc3`（挡“只拦 `\xc3\xbf`”）；原始 `0xE9` 不是合法 UTF-8（挡“只看解码后字符”）。
- expected 增 3 键，状态 PASSED（依据是语义要求“应抛异常”，不是照抄 gold 输出）；键名预计为 `test_bad_header_name_non_ascii[py-parser-pyloop-utf8-cjk]` 等，以 gold 日志为准。

**R-c-2（R2 非示例实例）** 同一文件，紧接 `test_http_request_bad_status_line_whitespace` 之后：

```python
@pytest.mark.parametrize(
    "line",
    (b"GET\t/path HTTP/1.1", b"GET /path\x0bHTTP/1.1"),
    ids=("htab", "vtab"),
)
def test_http_request_bad_status_line_ctl_separator(parser: Any, line: bytes) -> None:
    with pytest.raises(http_exceptions.BadStatusLine):
        parser.feed_data(line + b"\r\n\r\n")
```

- 公开依据：题面要求“improperly formatted status lines”、“improper whitespace and control characters”抛 `BadStatusLine`（`user_prompt.txt:4,7,23`）。HTAB、VT 与示例里的 `\n`、`\f` 同类：都是 ASCII 空白控制字符，也都是 base 的 `str.split()` 会当成分隔符的字符。
- 刻意不放：裸 CR（RFC 9112 §2.2 允许接收方把裸 CR 替换成 SP，放进来会误拒这类实现）、双空格（可争议）、请求目标内 CTL（§5 第 4 步解读未定）。
- expected 增 2 键 PASSED。

**验收（两项同一轮）**：gold 为 1（5 个新键 PASSED，原 129 键不变）；noop 为 0（5 个新键为 `DID NOT RAISE` FAILED）；退化候选 D 为 0（5 个新键全失败；修订前应为 1，存为触发反例）；替代正对照 A1（§3，参照 aiohttp__1c1c0ea3 公开初态 `http_parser.py:73–74、172、572` 移植两处）为 1；键集严格相等，不改其它测试；保存新版本、父版本与理由；Codex 复核。

**P4 的可选 R-f（低优先）**：把示例 1 的两行改成 `request = "POST / HTTP/1.1\r\n\xffoo: bar\r\n\r\n".encode()`，使“Actual Behavior”对字面代码成立。前提是协调者先在 base 上实跑证实字面示例会抛异常；这不是新增信息（输入本来就等于隐藏测试），按 R-f 验收。若不做，至少在 devcheck 里记录“原例不复现”与替代复现。

**模板外、待用户决定**：无。§5 列的范围扩展（响应状态行、头值 CTL、请求目标 CTL）不建议现在加。

## 8. gold 检查

- 只改 `aiohttp/http_parser.py` 两处：`HDRRE` 加 `\x7F-\xFF`；请求行改为 `line.split(" ", maxsplit=2)`。两个原例都修到（rf gold 日志 39、89）。没有无关改动。
- 未测的连带影响（登记，不作问题）：`HDRRE` 在共用的 `HeadersParser` 里，响应头名（客户端 lax 模式）与 multipart 部件头名（`multipart.py:699–700`）也会拒绝 0x80–0xFF 字节。公开材料既不要求也不禁止。
- 请求行在请求目标前后出现额外空格、前导空格时 gold 也会报 `BadStatusLine`（经 `METHRE` / `VERSRE` 校验），与加固方向一致，未测。
- 响应状态行未改，属题面范围外。

## 9. 开发需求（actor 侧待验）

- 导入：`/testbed` 必须在 `sys.path` 上；用 `python -m pytest`（`environment_brief.md:13`）。评分侧由 `.venv/bin/python -m pytest` 满足（账本 `RH2_OBS_IMPORT_PATH=/testbed/aiohttp/__init__.py`）。
- 依赖：multidict、yarl、pytest 7.4.2、pytest-cov、pytest-asyncio、pytest-mock、brotli 都已在镜像（评分侧实测）；无需装新包、无需联网。
- 构建：无需（纯 Python 修复）。C 扩展不需要，也不应尝试构建（§4(a)）。
- 权限：agent（uid 54321）可写 `/testbed`（brief）；修改只在 `aiohttp/http_parser.py`。
- 公开验证：`python -m pytest tests/test_http_parser.py` 在 base 上预计有 3 个与本题无关的 C 解析器失败（按评分侧同一镜像推断，actor 侧待 devcheck 核实）；原例复现需自行构造正确的字节串（P4）。
- 耗时：评分侧整套约 5 秒，开发回合成本很低。

## 10. 题目关系（X1）

- `cross_task_test_scan.json` 的 `pairs[5]`、`pairs[6]`（从 0 计）：本题两处新测试（`test_http_request_bad_status_line_whitespace`，以及同文件里的 `"\xffoo: bar"` 参数）已出现在 aiohttp__1c1c0ea3（公开 `tests/test_http_parser.py:210、823`）和 aiohttp__22a12cc2（`:211、824`）的公开初态。
- 核对两题公开 `aiohttp/http_parser.py`：头名改为 `TOKENRE.fullmatch(name)` 白名单（1c1c0ea3 `:73–74、172`；22a12cc2 `:172`），请求行 `line.split(" ", maxsplit=2)` 逐字相同（1c1c0ea3 `:572`；22a12cc2 `:577`）。即本题修复以重构形式包含在这两题的初态里。
- `cross_task_gold_scan.json` 没有本题的对：gold 三条非平凡新增行里只有 `split` 一行逐字出现（约 1/3，低于 80% 阈值），`HDRRE` 已被上游改成 `TOKENRE`。这是逐字扫描的已知漏报形态。
- 反向：`pairs[3]` 显示 aiohttp__240da100 的新测试 `test_request_port` 在本题初态里，说明本题 base 已含 240da100 的修复；这影响 240da100 的关系记录，不影响本题。
- 影响：训练时控制与 1c1c0ea3、22a12cc2 的重复采样（后两题的初态含本题答案）；按仓库划分留出（D3）时三题须同侧。

## 11. 用途结论（v1 §2，`intended_use` 仍为 `development_diagnostic`）

| 用途 | 结论 | 差什么 / 依据 |
| --- | --- | --- |
| `problem_localization` | yes | 无门槛 |
| `capability_comparison` | conditional | 评分依据已核（current 材料 noop 0 / gold 1 各两次）；还差：① 本题 actor devcheck（正式启动路径、公开命令、原例复现记录），我未见证据；② R-c 之前，示例特判补丁也能得 1，若用于比较须预登记事后审计（对 §7 的 5 个非示例输入跑后检），原始 reward 与语义结果分列；③ P4 登记 |
| `training_candidate` | no | 当前材料有未处理的 S1（T2c，T2b 待测）；R-c 验收加 Codex 复核后重评，并需登记 X1 |
| `heldout_candidate` | no | 同上；修订后只能作标明版本的自建评测；与 aiohttp__1c1c0ea3、22a12cc2 须同侧 |

## 12. 探针就绪差距

按指示我没有读本批 README，以下按 v1 §2 与角色卡推断 §3 可能的条目，协调者对照原标准调整。

- 已满足：当前材料 noop 0 / gold 1（两组 current 运行，日志复读）；材料哈希一致；R2E 专项无阻断；X1 已写明。
- 未满足：退化候选正式评分 1 次（协调者）；R-c-1 / R-c-2 实施与验收（协调者实施，Codex 复核）；actor devcheck 与 P4 原例复现记录（协调者）；brief 补“3 个 C 解析器公开测试恒失败”的中性说明（协调者，可选）；X1 与 T3 待定项写入 `screening_record.json`（主审，协调者收口）。

## 13. 未知与疑点

- 镜像里 `vendor/llhttp` 是否有内容、是否有 Cython 与编译器：决定 agent 能否构建 C 扩展，从而翻转 3 个 FAILED 键（§4(a)）。
- actor 侧公开测试的实际结果，以及题面字面示例在 base 上的实际行为（P4 结论目前是源码推断）。
- 退化候选 D 的正式得分（预计 1）。
- “控制字符”是否覆盖请求目标内的 CTL、“The HTTP parser”是否覆盖响应方向：我倾向都不属于核心要求，登记待定。
