# 公开读者报告：aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a

- 角色：R2E 公开读者（单题、干净上下文），2026-09-29。只读了角色卡和本题公开包。
- 路径约定：下文路径都相对本题公开包根目录；`worktree/` 就是解题者在 `/testbed` 看到的初始工作树。行号以公开包里的文件为准。
- 基本事实：仓库 `aiohttp`，base 提交 `e181a0e468d4…`（`public_bundle.json` L9），包版本 `3.9.0b0`（`worktree/aiohttp/__init__.py` L1）。镜像初态相对 base 只改了 `Makefile`（`worktree_manifest.json` 的 `initial_diff.files`），与题目无关。
- 执行情况：本文所有命令都是"建议，未执行"。我没有运行项目代码；只用本机 python3 标准库核对了 `str.split()`、f-string 和两条正则的语义，没有导入 aiohttp。

## 0. 结论摘要

题意清楚，缺陷可以从 base 源码直接读出来。纯 Python 请求解析器（`HttpRequestParserPy`）有两处放行：

1. 头字段名里的非 ASCII 字节不会被拒绝；
2. 请求行用 `str.split()` 按任意空白切分，所以 `GET\n/path\x0cHTTP/1.1` 会被当成合法的 `GET /path HTTP/1.1`。

修复点集中在 `worktree/aiohttp/http_parser.py`。

主要未知有两项：

- 镜像里有没有编译好的 C 扩展（llhttp 解析器）；
- 隐藏测试会不会把"状态行"要求延伸到响应解析器。

题面例 1 的示例代码写错了：它把 bytes 塞进了 f-string。照字面执行，base 上已经会抛异常，复现不出问题。题意应以文字说明为准，即字段名里含 `ÿ`。

## 1. 需求表

### 1.1 要改变的行为

| # | 行为 | 类别 | 依据 | base 现状（读码） |
|---|---|---|---|---|
| R1 | 请求头行是 `"\xffoo: bar"` 的 UTF-8 编码（字段名以字节 `\xc3\xbf` 开头）时，`feed_data` 抛 `BadHttpMessage`。子类如 `InvalidHeader` 也满足 `pytest.raises(BadHttpMessage)` | 明示 | `user_prompt.txt` L11-14、L22 | `HDRRE`（`worktree/aiohttp/http_parser.py` L68）只含 `\x00-\x1F`、`\x7F` 和分隔符，不含 `\x80-\xFF`。L149-150 放行，L205 以 `surrogateescape` 解码，L212 加入 headers，全程不报错 |
| R2 | 请求 `b"GET\n/path\x0cHTTP/1.1\r\n\r\n"` 抛 `BadStatusLine` | 明示 | `user_prompt.txt` L16-18、L23 | 请求解析器只以 `\r\n` 分行（L283、L304），所以整段 `GET\n/path\x0cHTTP/1.1` 是第一行。L550 的 `line.split(maxsplit=2)` 把 `\n` 和 `\x0c` 都当分隔符，切出 `GET`、`/path`、`HTTP/1.1`；L560 的 `METHRE` 与 L564 的 `VERSRE` 都能通过，最后返回正常消息 |
| R3 | 要修的是纯 Python 解析器，C 解析器预计已经满足 R1、R2 | 可推知，未验证 | 公开测试的 `parser` fixture 同时参数化 Py 和 C 两种解析器（`worktree/tests/test_http_parser.py` L32-41、L56-66）。C 解析器把 `HPE_INVALID_HEADER_TOKEN` 映射为 `BadHttpMessage`，把 `HPE_INVALID_METHOD` 映射为 `BadStatusLine`（`worktree/aiohttp/_http_parser.pyx` L811-836）。请求解析器不设 lenient 标志（L574-586），只有响应解析器设（L651-655） | llhttp 源码不在工作树：`worktree/.gitmodules` L1-4 指向子模块，`worktree/vendor/llhttp/` 是空目录。镜像里有没有 `aiohttp/_http_parser*.so` 也未知，所以 C 侧的行为只能推测 |
| R4 | 在服务端，这两种请求应得到 400，不再进入 handler | 可推知 | `worktree/aiohttp/web_protocol.py` L349-356 捕获 `HttpProcessingError` 并转成 400；错误响应借用的占位消息 `ERROR` 是 HTTP/1.0（L64-75、L517-520） | base 上用 Py 解析器时，两例都会进入 handler |

### 1.2 应保留的旧行为

证据来自公开测试。隐藏测试可能改写这些用例，这一点未知。

| # | 应保留的行为 | 依据 |
|---|---|---|
| P1 | 头字段的**值**含非 ASCII 仍然接受，包括 UTF-8 的 `x-test:тест` 和 cp1251 字节（按 `surrogateescape` 解码）。所以新校验只能针对字段名 | `worktree/tests/test_http_parser.py` L697-729、L798-811 |
| P2 | 非 ASCII 或非法的请求目标仍抛 `InvalidURLError`，例如 `GET \xff HTTP/1.1`、`GET ! HTTP/1.1`。它和 `BadStatusLine` 是兄弟类（`worktree/aiohttp/http_exceptions.py` L96-106），改成抛 `BadStatusLine` 会让这两条测试失败 | tests L761-768 |
| P3 | Py 解析器仍接受路径里的原始 UTF-8，例如 `GET /путь?ключ=знач#фраг HTTP/1.1`。C 解析器在这条用例里是 xfail | tests L1086-1096 |
| P4 | `getpath ` 抛 `BadStatusLine`，且消息里不出现转义的 `\n` | tests L674-679 |
| P5 | 超长时仍抛 `LineTooLong`，消息里的字节数沿用现有口径：分别按字段名、值和请求目标的长度计算 | tests L573-580、L601-608、L629-636、L771-777；代码 L151-158、L554-557 |
| P6 | 现有的拒绝都要保留：字段名前后有空白、`test[]` 这类含分隔符的字段名、值里有 CR/LF/NUL、带 `+`/`-` 的 Content-Length、坏方法、坏版本 | tests L171-186、L253-256、L560-570、L746-758 |
| P7 | 没有冒号的 `\xff` 头行仍抛 `InvalidHeader`，而且 `e.message.encode("utf-8")` 不能报错，即消息里不能出现裸代理字符 | tests L189-203 |
| P8 | 响应解析器的宽松行为保持不变：值里允许 `\x01`，允许只用 LF 分行，允许没有 reason 短语，reason 超长时抛 `LineTooLong` | tests L814-857、L868-876 |
| P9 | 字段名含 `\xd9` 且超长时，抛 `LineTooLong` 或 `BadHttpMessage` 都算对。因此把非 ASCII 检查放在长度检查之前也不冲突 | tests L259-264 |

### 1.3 有多种合理解释的点

| # | 问题 | 公开材料能说明到哪 |
|---|---|---|
| A1 | 响应状态行要不要一起拒绝非 SP 空白和控制字符？`HttpResponseParser.parse_message`（`worktree/aiohttp/http_parser.py` L653-679）同样用 `split(maxsplit=1)` | 标题写 "Malformed Status Lines"（`user_prompt.txt` L4），描述写 "improperly formatted status lines"（L7），但例子和期望只给了请求行。响应解析器在非 DEBUG 模式下是故意宽松的（L639-651，见 P8）。aiohttp 自己也把请求行叫 status line（L541-552 抛的就是 `BadStatusLine`），所以标题可以只指请求行 |
| A2 | 字段名校验放在共享的 `HeadersParser` 里，还是只对请求生效？请求、响应和 multipart 分段头都经过 `HeadersParser`（L258；`worktree/aiohttp/multipart.py` L691-701） | 题面只说请求（"mishandling of HTTP requests"，L7）。公开测试里，响应和 multipart 都没有字段名含非 ASCII 的用例 |
| A3 | 请求行里的其他空白是否也要拒绝：HTAB、VT、裸 CR、`\x1c-\x1f`、连续多个 SP | `str.split()` 会把这些全当分隔符（本机 python3 已核对）。题面只说 "improper whitespace and control characters"。按单个 SP 切分会一并拒绝这些；只拒绝示例里两个字符的实现也能通过示例 |
| A4 | 分隔符都正确、但请求目标或版本里夹了控制字符，算不算 R2 的范围？例如 `GET /pa\x0cth HTTP/1.1`、`GET / HTTP/1\x0c1` | 按读码推测，如果只改成按单 SP 切分，这两例仍会被接受：请求目标由 `URL.build(..., encoded=True)` 构造（L583-588），这里不做字符校验（yarl 不在工作树，是否另有校验未核对）；`VERSRE` 里的 `.` 没有转义，`\d` 还会匹配 Unicode 数字（L67）。本机 python3 核对过，`HTTP/1\x0c1` 和 `HTTP/١.١` 都能 fullmatch。题面没有这类例子，属于可选加固 |
| A5 | 具体抛哪个子类、消息怎么写 | 题面只给了基类名 `BadHttpMessage` 和 `BadStatusLine`，没有给消息格式。如果隐藏测试用 `match=` 匹配消息，公开材料推不出来 |

## 2. 合理实现范围

**头字段名（R1）**：下面几种做法都应该接受。

- 给 `HDRRE`（L68）的字符类补上 `\x80-\xFF`。
- 改成按 RFC 9110 token 的白名单做 `fullmatch`。字符集可以参照同文件 L59-66 为 `METHRE` 写的注释，改成 bytes 版本。
- 用 ASCII 解码字段名，把 `UnicodeDecodeError` 转成 `InvalidHeader`。

抛 `InvalidHeader` 与现有代码一致（L142、L146、L150），直接抛 `BadHttpMessage` 也满足题面。校验放在 `HeadersParser` 里还是只对请求生效，见 A2。校验放在长度检查之前或之后都可以（P9），但字段名全是合法 token 字符只是超长时，仍然要得到 `LineTooLong`（P5）。

**请求行（R2）**：下面几种做法都应该接受。

- 按 RFC 9112 的 `method SP request-target SP HTTP-version`，用单个空格切分，例如 `split(" ", maxsplit=2)`。解包失败时沿用 L551-552 的 `BadStatusLine(line)`。
- 保留现有切分，但在切分前检查请求行里有没有控制字符或非 SP 空白，有就抛 `BadStatusLine`。
- 用正则校验整行。

不管用哪种，都有三条约束：

- 请求目标含非 ASCII 时不能改判成 `BadStatusLine`（P2、P3）；
- 不能改变 L554-557 计算长度的口径（P5）；
- `getpath ` 的错误消息里不能出现转义换行（P4）。

**没有约定的部分**：新常量或新函数的命名、异常消息的文本、要不要加 `CHANGES/` 片段都没有约定（`worktree/CONTRIBUTING.rst` L23 讲的是贡献流程，不是判分要求）。不需要新增公共 API。

**不需要，也做不到**：修改或重新编译 C 扩展。llhttp 子模块是空的；按 `worktree/vendor/README.rst` L7-21，重建需要 `git submodule`、`npm` 和 cython，而环境不能联网。

**响应解析器（A1）**：收紧或保持宽松都说得通。如果收紧，必须保住 P8。

**顺带观察（题面没有要求）**：在 base 上，如果头行以 `:` 开头（字段名为空），L145 的 `bname[0]` 会抛 `IndexError`，而不是 `InvalidHeader`。在 L145 之前用 token 白名单做 `fullmatch` 的实现会顺带修掉这个问题；其他实现不修它也符合题面。

## 3. 题面质量与初态线索

### 3.1 题面是否直接给出修法

没有。"Example Buggy Code" 是测试形态的调用（`parser.feed_data(...)`），不是实现。"improper whitespace and control characters"（L23）指向了切分方式，但仍属于正常的症状描述。

### 3.2 题面描述的行为能否从 base 源码读出来

- **例 2**：能，逐行推演见 R2（L283、L304、L550、L560、L564）。
- **例 1 的意图**（字段名含 `ÿ` 却没有报错）：能，见 R1（L68、L149-150、L205、L212）。
- **例 1 的字面代码**：不能。`invalid_header = "\xffoo: bar".encode()` 先得到 bytes，再插进 f-string 时变成了 bytes 的 repr 文本。实际发出的请求是 `b"POST / HTTP/1.1\r\nb'\\xc3\\xbfoo: bar'\r\n\r\n"`（本机 python3 核对）。这时字段名是 `b'\xc3\xbfoo`，里面有字面的反斜杠，`HDRRE` 在反斜杠处命中（L149-150），所以 base 的 Py 解析器已经会抛 `InvalidHeader`，它是 `BadHttpMessage` 的子类。
  - 因此对字面的例 1，"Actual Behavior: No exceptions are raised"（L26）不成立。解题者照抄这段代码去复现，会误以为 bug 不存在。
  - 正确理解应以 L22 的 "invalid character `ÿ`" 为准：头行是 `"\xffoo: bar"` 这个字符串本身做 UTF-8 编码。
- **C 解析器**：题面说"不抛异常"。但从 `_http_parser.pyx` 的错误映射推测，C 解析器会拒绝这两例（未验证），缺陷实际只在 Py 解析器上。

### 3.3 示例在 base 接口下是否说得通

- `parser` fixture 和 `feed_data(bytes)` 的用法与公开测试一致（tests L56-66）。
- 示例函数叫 `test_invalid_header`，公开测试里已有同名用例（tests L560-563），但测的是没有冒号的头行，内容不同。不能据此推断隐藏测试的名字或位置。
- 题面把请求行称作 "status line"，与仓库的用法一致：请求行解析失败时抛的就是 `BadStatusLine`。

### 3.4 初态与仓库线索（只是背景，不是修法）

- 初态改动只有 `Makefile`（见 manifest 的 `initial_diff`；工作树 `Makefile` L49-53、L77、L92、L177 改成了 `uv pip install`），与题目无关。
- `worktree/run_tests.sh` L1 跑的是 `r2e_tests` 目录，它不在工作树里，属于隐藏测试。
- 从 `worktree/CHANGES/` 下的片段看，仓库正在逐项加固纯 Python 解析器，本题属于同一方向：
  - `7700.bugfix`：方法和版本校验不足；
  - `7712.bugfix`：绝对 URI 必须带 scheme；
  - `7715.bugfix`：Py 解析器遇到裸代理字符时出错。
- 公开测试里有几处注释说 C 与 Py 行为不一致、以后再对齐（tests L237、L862-863、L1087-1088），说明 C 解析器（llhttp）是行为的参照。其中 L1087-1088 提到以后可能让 Py 解析器也拒绝路径里的原始 UTF-8。但在当前公开测试里，Py 解析器必须接受它（P3）。

### 3.5 定位入口与缺失信息

调查入口很清楚：

- `worktree/aiohttp/http_parser.py` 的 `HeadersParser.parse_headers`（L127-215）和 `HttpRequestParser.parse_message`（L546-629）；
- 异常类在 `worktree/aiohttp/http_exceptions.py`；
- 回归测试在 `worktree/tests/test_http_parser.py`。

真正缺的信息有两项，都不妨碍写出 Py 解析器的修复：

- 镜像里有没有 C 扩展。它决定公开测试会不会跑 `c-parser` 参数，以及 3 个只测 C 的用例能不能通过（见 §4）。
- A1、A2 的范围到底有多大。

下面这些只需要正常读代码，不算题面缺陷：共享 `HeadersParser` 的调用方（multipart），以及服务端怎样把解析异常转成 400。

### 3.6 `public_hints` 分三类（`public_bundle.json` L15）

- **题目需求**：找到根因，修改非测试源码。
- **给解题者的操作指令**：
  - 不要改仓库的测试文件，判分用的是另一套测试；
  - 测试范围要窄，在 `/testbed` 下用 `python -m pytest`；
  - 完成后简短总结，停止调用工具。
- **环境事实声明**：`python` 指向 `/testbed/.venv`；无网络；"`pip` may be unavailable"。`environment_brief.md` L11 的说法是 pip 有但不能出网，两边口径略有出入，对本题没有影响。
- **对合法解法的影响**：装不了包，所以无法重建 C 扩展；不能改测试文件，所以自测脚本应放在 `/tmp`。这两点都不妨碍修复 Py 解析器。

## 4. 开发需求表

| 操作 / 资产 / 服务 | 公开依据 | `environment_brief.md` 支持到哪 | 缺口 | 最小命令（建议，未执行）与预期 |
|---|---|---|---|---|
| Python 解释器和运行依赖（multidict、yarl、attrs 等） | `worktree/setup.cfg` L49-55；`public_bundle.json` L15 | L10-11：`.venv`、Python 3.9.21、pip 有但不能出网 | 没有逐项列出依赖。本题不需要新依赖 | `env_import_versions`：退出码 0，打印 3.9.21、`/testbed/aiohttp/__init__.py` 和 3.9.0b0 |
| 从源码树导入 aiohttp | brief L13 | 已说明：`/testbed` 要在 `sys.path` 上 | 无 | 同上 |
| C 扩展 `aiohttp._http_parser` | `worktree/aiohttp/http_parser.py` L985-999；`worktree/setup.py` L27-45；tests L32-41、L99-162 | 未提及 | 不知道是否已编译；也无法重建，因为 llhttp 为空且不能联网 | `env_import_versions` 会打印 `c_parser_available` 和 `aiohttp/*.so` 列表 |
| pytest 和插件 | `worktree/setup.cfg` L115-171：`addopts` 含 `--cov`（需要 pytest-cov）和 `-m "not dev_mode"`，并设了 `filterwarnings = error`；`worktree/tests/conftest.py` L25；`worktree/requirements/test.in` L8-10 | L13：用 `python -m pytest`；裸 `pytest` 收集会失败 | 没说 pytest-cov 是否安装；默认的 `--cov` 还会在 `/testbed` 写出 `.coverage` | 用 `-o addopts=""` 去掉 `--cov`，再手动补回 `-m "not dev_mode"`。不补的话，dev_mode 用例会在非 dev 模式下运行，至少 `test_http_response_parser_bad_chunked_strict_py`（tests L888-901）会失败 |
| 复现：解析器层 | `user_prompt.txt` L11-18 | 可行 | 无 | `repro_parser_issue_cases`：base 上退出码 1 |
| 复现：服务端，走公开 API `aiohttp.web` | `worktree/aiohttp/web_protocol.py` L349-356；仓库自带的功能测试本来就依赖回环端口（如 `worktree/tests/test_web_functional.py` L802-812） | 没提回环端口 | 不知道能否监听本地端口，但仓库自带测试同样依赖这一点 | `repro_server_400_py_parser`：base 上退出码 1。如果打印 `SETUP_ERROR` 且退出码为 3，说明环境不能监听本地端口，与题目无关 |
| 公开回归测试 | tests 整个文件 | 可行（`python -m pytest`） | 这 3 个用例按 `NO_EXTENSIONS` 而不是按 C 扩展是否可用来决定跳过（tests L99-162）：`test_c_parser_loaded`、`test_invalid_character`、`test_invalid_linebreak`。C 扩展缺失又没设 `AIOHTTP_NO_EXTENSIONS` 时，它们在修复前后都会失败 | `public_http_parser_tests` 先探测 C 扩展，缺失时导出 `AIOHTTP_NO_EXTENSIONS=1`。预期修复前后退出码都是 0 |
| 相关回归 | `HeadersParser` 的 multipart 调用方、异常类、客户端的响应解析 | 可行 | 无 | `public_related_tests`：修复前后退出码都是 0 |
| 写临时文件 | brief L12：`/tmp` 有 1 GiB | 不涉及 | 不涉及 | 所有命令都设 `PYTHONDONTWRITEBYTECODE=1`；pytest 加 `-p no:cacheprovider` 并去掉 `--cov`，不在 `/testbed` 留下缓存或覆盖率文件 |

### 4.1 命令明细（与同目录的 `commands.json` 一致，全部为建议，未执行）

1. **`env_import_versions`**（expect `zero`）：确认导入路径和版本，并记录 C 扩展是否可用、pytest-cov 是否安装。修复前后输出应该一样。
2. **`repro_parser_issue_cases`**（expect `nonzero`）：对每个可用的请求解析器（先 py；C 扩展可用时再加 c）喂 6 个原始请求，逐行打印 OK 或 FAIL。
   - **修复前**，py 解析器的预期：

     | 用例 | 预期输出 | 判定 |
     |---|---|---|
     | `new_hdr_name_nonascii` | `parsed [('POST', '/', [('\xffoo', 'bar')])]`（输出经 `ascii()` 转义，即字段名 `ÿoo` 被接受） | FAIL |
     | `new_reqline_lf_ff` | `parsed [('GET', '/path', [])]` | FAIL |
     | `issue_ex1_literal`（题面例 1 的字面写法） | `InvalidHeader`（原因见 §3.2） | OK |
     | 三个 `keep_*` | 行为不变 | OK |

     退出码为 1。如果有 c 解析器，预计它的 6 行全部 OK（未验证）。
   - **修复后**：全部 OK，`FAILS 0`，退出码 0。如果修复后只剩 c 解析器的行 FAIL，说明已编译的 C 扩展本身不拒绝这些输入，需要单独记录。
3. **`repro_server_400_py_parser`**（expect `nonzero`）：
   - 做法：设 `AIOHTTP_NO_EXTENSIONS=1`，让服务器使用纯 Python 请求解析器；在 `127.0.0.1` 的随机端口启动 `aiohttp.web` 应用，发送题面的两种原始请求，读取状态行。
   - 修复前：两例都返回 `HTTP/1.1 200 OK`，退出码 1。
   - 修复后：两例都返回 `HTTP/1.0 400 Bad Request`，退出码 0。这里是 HTTP/1.0，是因为错误响应沿用了 HTTP/1.0 的占位消息。stderr 里出现 "Error handling request" 日志属于正常。
4. **`public_http_parser_tests`**（expect `zero`）：跑 `tests/test_http_parser.py`，C 扩展缺失时自动设 `AIOHTTP_NO_EXTENSIONS=1`。修复前后都应全部通过。修复后如果出现失败，多半是破坏了 P1-P9 中的某条保留行为。
5. **`public_related_tests`**（expect `zero`）：跑 `tests/test_http_exceptions.py`、`tests/test_multipart.py`、`tests/test_client_proto.py`，用来发现改动共享的 `HeadersParser`、异常类或响应解析器时带来的回归。修复前后都应全部通过。

## 5. 阅读范围与限制

**实际打开的文件**（完整或部分，含 grep）：

- 角色卡；公开包里的 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`。
- `worktree_manifest.json`：只看了元数据段和文件清单，没有打开其中指向公开包以外的路径。
- `worktree/` 下的构建与配置文件：`run_tests.sh`、`.gitmodules`、`.gitignore`、`Makefile`、`setup.py`、`setup.cfg`、`pyproject.toml`、`CONTRIBUTING.rst`、`CHANGES/*`、`vendor/README.rst`（另确认 `vendor/llhttp/` 为空）、`requirements/test.in`；`.github/workflows/ci-cd.yml` 只做了 grep。
- `worktree/aiohttp/` 下的源码：
  - 完整读过：`http_parser.py`、`http_exceptions.py`、`http.py`；
  - 读过相关段落：`_http_parser.pyx`（初始化、头部完成回调、`feed_data`、错误映射）、`helpers.py`（L60-90、L495-515）、`multipart.py`（L680-712）、`web_protocol.py`（导入、`ERROR`、解析器构造、`data_received`、错误处理）、`web_runner.py`；
  - 只做了 grep：`web_app.py`、`web_server.py`、`web_response.py`、`pytest_plugin.py`、`__init__.py`。
- `worktree/tests/` 下的测试：
  - `test_http_parser.py`：读了 L1-1140；
  - 读过相关段落：`conftest.py`、`test_client_proto.py`、`test_web_server.py`、`test_web_functional.py`；
  - 只做了 grep 或字符扫描：`test_http_exceptions.py`、`test_multipart.py`。

**没有查的范围**：

- 其余源码和测试、`docs/`、`examples/`、`tools/`；
- llhttp 和 yarl 的实际行为（源码都不在工作树）；
- 镜像的实际内容，包括编译产物、已安装的包，以及 `install.sh` 与 `process_aiohttp_updateasyncio.py`（这两个文件没有收进公开包）；
- 隐藏测试。

我没有读任何 private 或 history 目录、其他题的材料或审查结论，也没有做网络搜索。

**限制**：

- `user_prompt.txt` 只是静态渲染的结果，不等于模型实际收到的消息。
- `worktree/` 不是完整的运行容器。
- 本文没有验证运行资源、开发条件、C 扩展是否存在，也没有验证任何命令的实际输出。所有"预计"都来自读码和本机标准库语义核对。
