# 公开读者报告：aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2

- 角色：R2E 公开读者（静态审查，不解题）；日期 2026-09-25。
- 材料范围：只读了角色卡和本题 `PUBLIC_DIR`。没有运行任何代码，没有联网，也没有修改 `worktree/`。
- base：`ff3dec422bd18b5e9078b5f29be1c9a6a1373f5a`，与 `user_prompt.txt:1` 的短哈希 `ff3dec422bd1` 一致。
- 除非另注，下文路径都相对 `PUBLIC_DIR/worktree/`。所有"base 下会发生什么"的结论都来自读代码的推断，没有实跑；把握较低的地方另外标了"推断"。

## 背景：base 中的相关代码路径（后文引用）

1. 写出器选择：`HttpMessage.send_headers()` 在 `aiohttp/protocol.py:631-641` 选写出器。条件是 `self.chunked` 为真，或者"无 Content-Length、HTTP/1.1 及以上、状态码不是 304/204"时，用 `_write_chunked_payload`；有 Content-Length 时用 `_write_length_payload`；其余情况用 `_write_eof_payload`。
2. 过滤器串接：`add_chunking_filter` 和 `add_compression_filter` 都是 `wrap_payload_filter`（391-436）包装的生成器。后加的过滤器接在先加的后面，即 `filter_pipe(旧, 新)`（430 行）。
3. 空块的来源：`add_compression_filter` 对每个输入块都直接 `yield zcomp.compress(chunk)`，不检查结果是否为空（797-799 行）。`filter_pipe`（463-465）和 `HttpMessage.write()`（686-690）会把 `EOF_MARKER`/`EOL_MARKER` 以外的任何值，包括 `b''`，原样交给下游或写出器。
4. 空块的后果：
   - `_write_chunked_payload` 遇到空块照样依次写 `b'0\r\n'`、`b''`、`b'\r\n'`（723-727 行）。线上字节是 `0\r\n\r\n`，和 `write_eof()` 写的结束块（719 行）一样。aiohttp 自己的 `parse_chunked_payload` 读到 size 0 就结束正文（330-331 行）。
   - `_write_length_payload` 在剩余长度非零时，对空块调用 `transport.write(b'')`（738-742 行）。`_write_eof_payload` 也一样（756 行）。
5. zlib 行为（按常规行为推断）：raw deflate（`wbits=-zlib.MAX_WBITS`，787-788 行）在默认 `Z_NO_FLUSH` 下会缓冲小输入，`compress()` 返回 `b''`，数据要等到 `flush()`（794 行）才输出。gzip 模式第一次 `compress()` 会输出 gzip 头，之后的小输入同样可能返回 `b''`。
6. 过滤器顺序决定会不会出空块：
   - **压缩在最后**（只有压缩过滤器，或者像题面示例那样先分块、后压缩）：压缩产生的 `b''` 直接进入写出器。
   - **先压缩、后分块**：这是文档推荐的顺序（406-413 行、489-493 行），`aiohttp/web_reqrep.py:554-563` 在设置了 chunk_size 时、`aiohttp/client_reqrep.py:429-434` 也都用这个顺序。分块过滤器收到 `b''` 后，缓冲不满一块就只 yield `EOL_MARKER`（774-781 行）；到 EOF 时只有 `if buf:` 为真才输出（768-769 行）。所以空块被吸收掉了。公开测试 `test_write_payload_deflate_and_chunked`（tests/test_http_protocol.py:441-455）的期望输出里，也没有提前出现的 0 块。
7. 生产代码中的触发路径（读代码推知，题面没有提到）：`web.StreamResponse.enable_compression()` 生效、但 `enable_chunked_encoding()` 没给 chunk_size 时，只会加压缩过滤器（web_reqrep.py:554-563；`ResponseImpl` 就是 `protocol.Response`，见 web_reqrep.py:21）。如果此时是 HTTP/1.1 且没有 Content-Length，`send_headers()` 会自动选 chunked 写出器。

## 1. 需求表

| # | 行为 | 改变 / 保留 | 依据 | 明确度 |
|---|---|---|---|---|
| R1 | 题面示例配置下，每次 `transport.write` 的字节参数都非空。示例配置是：Content-Length = 压缩后长度，先 `add_chunking_filter(2)` 再 `add_compression_filter('deflate')`，然后 `write(b'data')`、`write_eof()` | 改变 | 题面 Example / Expected（user_prompt.txt:10-24）。按背景第 3、4 条推断，base 下会出现两次 `transport.write(b'')` | 需求本身是题面明说的。但示例断言按字面写错了，需要理解成"检查每次调用的第一个参数"，这一步是推知（见 3.2） |
| R2 | 启用压缩并使用 chunked 传输编码时，`write_eof()` 之前不能写出 size 为 0 的块，也就是不能提前出现 `0\r\n\r\n` | 改变 | 题面标题、Description、Actual（user_prompt.txt:4-7、26-27）；protocol.py:713-728、330-331 | 标题和描述明说了；但题面示例本身不走 chunked 写出器 |
| R3 | 最终写出的压缩字节流不变，拼接后仍等于原来的 raw deflate 流 | 保留 | tests/test_http_protocol.py:424-439、457-471 与 `_COMPRESSED` 比较；441-455 逐字节比较 `b'2\r\nKI\r\n2\r\n,I\r\n2\r\n\x04\x00\r\n0\r\n\r\n'` | 公开测试明示 |
| R4 | chunked 模式下，`write_eof()` 仍然恰好写一次结束块 `0\r\n\r\n` | 保留 | protocol.py:717-721；tests/test_http_protocol.py:340-369、386-422、441-455 | 公开测试明示 |
| R5 | 分块过滤器的切分方式不变；Content-Length 的截断语义不变 | 保留 | tests/test_http_protocol.py:371-384（期望 `da`）、386-422 | 公开测试明示 |
| R6 | 过滤器协议不变：收到字节后产出 0 个或多个数据块，再给 `EOL_MARKER`；收到 EOF 时输出剩余数据，再给 `EOF_MARKER`。两种过滤器顺序的现有结果也不变 | 保留 | protocol.py:416-421 的文档、439-475。分块过滤器已经有"只给 `EOL_MARKER`、不产出数据"的先例（774-781） | 可推知 |
| R7 | gzip 压缩同样不能产生空块 | 改变 | 标题只写了 Deflate，但 gzip 和 deflate 共用 787-799 行同一段代码。按 zlib 行为推断，gzip 在第一块之后也会产出 `b''` | 推知，题面没有明说 |
| R8 | 非空块的 `transport.write` 调用粒度保持不变：chunked 下长度行、数据、CRLF 分三次写 | 建议保留 | protocol.py:725-727；tests/test_client_request.py:480-484、499-503、593-597、630-634 固定了最后三次调用的形态。该文件在 Python 3.9 下无法收集，见 3.7 | 推知 |
| R9 | 不经压缩、调用方直接 `HttpMessage.write(b'')` 时，是否也要吞掉空块？chunked 下这同样会写出 `0\r\n\r\n`。`wsgi.py:135-138` 会把 WSGI 应用的每个 item 直接交给 `resp.write` | 未定 | 题面只谈压缩。web 层已经在 web_reqrep.py:581-584 跳过空数据，tests/test_web_response.py:247 断言 `resp.write(b'')` 返回 `()` | 有多种合理解释 |
| R10 | 不需要新增或改名任何公开 API、参数或异常 | 保留 | 题面没有给出任何新接口 | 推知 |

## 2. 合理实现范围

以下几种做法都应该被接受，前提是满足 R1–R6：

- **在压缩过滤器处处理**：压缩结果为空时不产出数据块，直接给 `EOL_MARKER`。这和分块过滤器已有的"只给 EOL"写法一致（R6），而且能同时覆盖两种写出器和 gzip。
- **在 `filter_pipe` 处处理**：不把空块转发给下游或写出器，同时要保持 `EOL_MARKER`/`EOF_MARKER` 的推进逻辑正确。
- **在 `HttpMessage.write()` 处处理**：把块交给写出器之前跳过空块。这种做法顺带覆盖了 R9。
- **在写出器处处理**：`_write_chunked_payload` 不为空块写 0 长度块，同时 `_write_length_payload`（以及 `_write_eof_payload`）也不为空块调用 `transport.write`。按 HTTP 语义，size 0 的块本来就是结束块，base 的解析器也这样处理（330-331 行），所以在 chunked 写出器里跳过空块不会丢掉任何合法用法。
- 以上做法的组合。`aiohttp/multipart.py:699-702` 有同样的写法（直接 `yield zcomp.compress(chunk)`），但题面没有要求改它。它的公开测试（tests/test_multipart.py:680-707）只比较拼接结果，改不改都不应算错。

以下做法不够，或者与公开证据冲突：

- **只改 `_write_chunked_payload`**：线上不再提前 EOF，R2 满足；但题面示例用的是 Content-Length 写出器，那两次 `transport.write(b'')` 仍然存在，R1 不满足。
- **只改 `add_chunking_filter`**：示例里分块在前，空块是压缩之后才产生的，改分块过滤器没有效果。
- **只改高层**（`web_reqrep.py` / `client_reqrep.py`，例如强制在压缩后面再加分块过滤器）：`protocol.Response` 这一层的示例行为不变，R1 不满足。
- **每次 write 都用 `Z_SYNC_FLUSH` 或 `Z_FULL_FLUSH`，让压缩器总有输出**：这会改变压缩字节流，424-471 行里与 `_COMPRESSED` 的比较和逐字节的 chunked 比较都会失败（R3），压缩率也会下降。
- **把 chunked 写出器合并成一次 `transport.write`**：不影响正确性，但改变了 R8 的调用形态，可能与既有测试冲突。

命名、输出和默认行为：题面没有约定新的名称、日志、异常或开关。唯一明确的输出约定是"不出现空块"；公开测试另外固定了字节流和 chunk 格式。我想不出有哪种合理实现需要新增接口。

仍然有多种解释的地方：R9 的范围，以及"chunk"究竟指什么（见 3.3）。如果隐藏检查也覆盖"不压缩、直接 `write(b'')`"的情况，那么只在压缩过滤器处修的实现就会不满足。公开材料无法判断这一点，记为未知。

## 3. 题面质量与初态线索

### 3.1 题面是否直接给出或强烈暗示修法

- 题面没有给出修好后的代码。Expected Behavior 只给了一个不变量："所有块的长度大于 0"。它暗示要"跳过空块"，但没说在哪一层做。第 2 节已经说明，放在不同的层会影响能否满足示例，所以这不算泄题。
- 示例几乎逐行照搬公开测试 `test_write_payload_chunked_and_deflate`（tests/test_http_protocol.py:457-471），只多了最后一行断言。这直接把复现入口指向了 `protocol.Response` 和两个过滤器。

### 3.2 题面描述的行为能否从 base 源码读出

- **"有空块"：能读出。** 按背景第 3–5 条推断，示例配置下 `transport.write` 的参数序列是 `[<状态行和头部>, b'', b'', b'KI,I\x04\x00']`。两段 2 字节输入各压出一个 `b''`，压缩数据要到 `write_eof()` 调用 `flush()` 时才输出。`KI,I\x04\x00` 与 441-455 行测试期望的三段拼起来一致。以上未运行。
- **"提前 EOF / 截断"：只在 chunked 写出器下成立。**
  - 示例设置了 Content-Length，所以 `send_headers()` 选的是 `_write_length_payload`（protocol.py:591-592、637-638）。空块只会变成 `transport.write(b'')`，线上不写任何字节，也不会产生 EOF 信号。
  - 要看到提前 EOF，需要满足三个条件：HTTP/1.1；没有 Content-Length，或者调用了 `enable_chunked_encoding()`；压缩过滤器在最后。这时推断线上正文是 `b'0\r\n\r\n6\r\nKI,I\x04\x00\r\n0\r\n\r\n'`，开头第一段就是结束块。
  - aiohttp 自己的解析器会在 330-331 行结束正文，后面的压缩数据要么被丢掉，要么被当成下一条消息误读。`DeflateBuffer.feed_eof()` 还可能因为压缩流不完整而抛出 `ContentEncodingError`（382-386 行，推断）。
- **示例断言按字面写不会失败。** `chunks = [chunk for chunk in write.mock_calls]` 拿到的是 `unittest.mock.call` 对象。它是长度为 3 的 tuple 子类 `(name, args, kwargs)`，真值恒为 True，所以 `assert all(chunks)` 在 base 下也会通过（按 `unittest.mock` 语义推断，未运行）。要真正复现，需要像公开测试那样取出参数 `c[1][0]`（例如 tests/test_http_protocol.py:469）。照抄示例的解题者会以为"复现不了"，这是题面最大的误导点。

### 3.3 示例在 base 接口下是否说得通

- 示例用到的方法在 base 里都存在，签名也对得上：`Response(transport, status)`（821-822）、`add_headers`（617）、`add_chunking_filter(chunk_size)`（759-761）、`add_compression_filter(encoding)`（783-785）、`send_headers()`（622）、`write()`（667）、`write_eof()`（704）。
- 示例里 `transport`、`write`、`compressed_data` 三个名字没有定义，要按公开测试补上：
  - `transport = unittest.mock.Mock()`（14 行）
  - `write = transport.write = unittest.mock.Mock()`（458 行）
  - `compressed_data` 对应 raw deflate 的 `_COMPRESSED`（424-425 行）
- 用词有混用：
  - 标题和描述里的 "chunked responses" 指 HTTP chunked 传输编码；示例里的 "chunked" 其实只是分块过滤器，响应本身带 Content-Length，并不是 HTTP chunked。
  - "chunk" 一词可以指 HTTP 块、过滤器的一次输出，或一次 `transport.write`。示例检查的是最后一种。
- 标题只写了 Deflate，但按背景第 5 条推断，gzip 同样受影响（R7）。

### 3.4 `public_hints` 的分类（public_bundle.json 第 15 行）

- 先说明一点：`user_prompt.txt` 只有首行说明加 issue 正文（1-29 行），**不包含** `public_hints`。解题者实际能否看到这些提示取决于 harness，公开材料无法确认。
- **题目需求**："Explore the code, find the root cause, and edit NON-TEST source files to fix the issue."
- **给解题者的操作指令**：
  - 不要修改测试文件；
  - 测试只跑单个文件或模块；
  - 确认完成后简短总结，并停止调用工具。
- **环境事实声明**：
  - "checked out at /testbed (your bash tool already runs there)"：与 environment_brief.md 第 10 行一致。
  - "fixing a real GitHub issue"：与角色卡说的"R2E 题面由模型根据修复提交和测试生成"不符，但不影响解法。
  - "pre-activated conda env named `testbed` … `pip` …"：与 environment_brief.md 第 10-13 行不符。实际情况是：Python 3.9.21 装在 `/testbed/.venv`；没有 pip 或 uv，也不能出网；包没有装进 venv，`/testbed` 必须在 `sys.path` 上；跑测试要用 `python -m pytest`。
  - "grading resets the test files … test edits never count"：角色卡说明这不是本来源的实际机制。公开材料里能看到的评分入口是 `run_tests.sh`，它只跑 `r2e_tests`（run_tests.sh:1），而工作树里没有这个目录。
- **对合法解法的影响**：本题只需要改 `aiohttp/protocol.py` 这类纯 Python 源码，复现只用到标准库的 `zlib` 和 `unittest.mock`，不需要装包。conda/pip 的错误说法最多让解题者白试几步；"只跑窄测试"的指令反而是必要的（见 3.7）。不能据此判定题目不可用。

### 3.5 复现与调查入口

- 入口是充分的。题面里的方法名直接指向 `aiohttp/protocol.py` 中的 `HttpMessage.write`、`filter_pipe`、两个过滤器和三个写出器；tests/test_http_protocol.py:424-471 提供了现成的测试夹具。复现不需要网络、服务进程，也不需要编译扩展。
- 公开测试没有覆盖"压缩在最后 + chunked 写出器"这个组合，也就是 R2 的场景。441-455 行测的是先压缩后分块，这个顺序本来就不会出空块。验证 R2 需要自己写几行脚本（第 4 节的 C3）。这属于正常的开发工作，不是题面缺陷。

### 3.6 哪些缺失会真正阻碍开发，哪些只需读代码

- **可能真正误导人的**：
  - 示例断言按字面写不会失败（3.2）；
  - 示例配置和标题描述的"提前 EOF"走的不是同一条写出路径（3.2、3.3）。
  
  仔细读完 `send_headers()` 就能理清这两点。但如果实现只修 chunked 写出器，会满足标题而不满足示例（第 2 节）。
- **仍然未知的**：R9 是否在检查范围内；隐藏检查看的是每次 `transport.write`，还是线上的 chunk 帧。
- **只需正常读代码的**：过滤器协议、写出器的选择逻辑，以及 web_reqrep.py 和 client_reqrep.py 中添加过滤器的顺序。

### 3.7 初态线索（只列影响开发的部分）

- **初态改写留下的运行时错误**：
  - `worktree_manifest.json` 的 `initial_diff.files` 列出了 `aiohttp/client.py`、`client_reqrep.py`、`server.py`、`worker.py`。
  - `process_aiohttp_updateasyncio.py:9,30` 只在 `aiohttp/` 目录下把 `asyncio.async(` 替换成 `asyncio.create_task(`，但保留了 `loop=` 参数（server.py:147、client_reqrep.py:447-448、client.py:171、worker.py:31）。
  - Python 3.9 的 `asyncio.create_task` 不接受 `loop` 参数，所以真实服务器建立连接、或者客户端发请求时，会在运行时报 `TypeError`（推断，未运行）。
  - `protocol.py` 不在改写范围内，协议层的复现不受影响。但如果用真实的 `aiohttp.web` 或 `aiohttp.server` 做端到端复现，会先撞上这个与本题无关的错误。
- **测试目录没有被改写**：`tests/test_connector.py:612`、`tests/test_client_request.py:524,561,589,609`、`tests/test_websocket_client.py:690`、`tests/test_worker.py:48` 里仍然有 `asyncio.async`。这在 Python 3.9 下是语法错误，这些文件在收集阶段就会失败。所以全量跑 `tests/` 会冒出与本题无关的错误。
- **评分入口跑不起来**：`run_tests.sh:1` 跑的是 `r2e_tests`，工作树里没有这个目录（清单写明不含隐藏测试）。
- **安装脚本与编译扩展**：`install.sh:4` 调用 `make .develop`，但 `Makefile` 只有 `develop` 这个目标（10-11 行），这与环境说明里"包没有装进 venv"一致。两个 Cython 扩展都有纯 Python 回退（aiohttp/multidict.py:346-362、aiohttp/websocket.py:190-197），不需要编译。
- **导入时的依赖**：
  - `aiohttp/multipart.py:13` 的 `from collections import Mapping, Sequence` 在 3.9 下仍能导入，只会给出 DeprecationWarning（3.10 才移除）。
  - 导入整个包时，`aiohttp/client_reqrep.py:12` 需要 `chardet`。`install.sh:6` 会安装它，但公开材料没有说安装是否成功。

## 4. 开发需求表

| 操作 / 资产 / 服务 | 公开依据 | environment_brief.md 支持到哪一层 | 缺口 | 最小命令（建议，未执行）→ 预期现象 |
|---|---|---|---|---|
| 导入 `aiohttp.protocol` | tests/test_http_protocol.py:8；`aiohttp/__init__.py:6-16` 会连带导入 client、connector、multipart 等模块 | Python 3.9.21 在 `/testbed/.venv`；`/testbed` 需要在 `sys.path` 上（第 10、13 行） | 导入链需要 `chardet`（client_reqrep.py:12），环境说明没写是否已装 | C1 → 打印 `0.17.0a0 /testbed/aiohttp/protocol.py`。如果报找不到 `chardet`，是环境问题，不是题目问题 |
| 复现 R1：示例配置下的空 `transport.write` | 题面示例；tests/test_http_protocol.py:424-425、457-471 | 只需要标准库 `zlib` 和 `unittest.mock` | 无 | C2 → 见下方命令后的预期 |
| 复现 R2：chunked 写出器提前 EOF | 题面标题和描述；protocol.py:631-635、713-728、330-331 | 同上 | 公开测试没有覆盖，需要自己写脚本 | C3 → base 下预计正文是 `b'0\r\n\r\n6\r\nKI,I\x04\x00\r\n0\r\n\r\n'`；修复后结尾之前不应再出现 `0\r\n\r\n`，例如 `b'6\r\nKI,I\x04\x00\r\n0\r\n\r\n'`。把 `'deflate'` 换成 `'gzip'` 并分两次写入，可以检查 R7 |
| 跑相关公开测试 | tests/test_http_protocol.py | 用 `python -m pytest`，直接敲 `pytest` 收集会失败（第 13 行）；资源默认 2 CPU / 4 GiB | 公开材料没说 base 下这个文件能否全部通过 | C4 → 修复前后都应通过。重点看 424-471 行的 deflate 和分块用例：如果修复改变了压缩字节或 chunk 切分，这些用例会失败 |
| 周边回归（可选） | `tests/test_wsgi.py`、`tests/test_web_response.py` 会用到 protocol 或 web 层，且不含 `asyncio.async` | 同上 | base 下的基线未知 | C5：先在未改动的代码上跑一次，记下基线；修复后对比，只关注新增的失败 |
| 全量测试 / 评分入口 | run_tests.sh:1（跑 `r2e_tests`） | 环境说明没有提到 `r2e_tests` | 隐藏测试不在工作树里；全量跑 `tests/` 时有若干文件会收集失败（3.7） | 不建议跑 `bash run_tests.sh` 或 `python -m pytest tests/`。前者预计报找不到 `r2e_tests`；后者预计出现与本题无关的 SyntaxError 收集错误 |
| 端到端的服务器 / 客户端 | server.py:147、client_reqrep.py:447-448 | 不能出网（第 11 行）；没说本机回环能否使用 | 初态改写会导致运行时 `TypeError`（推断） | 不需要做端到端复现。C2、C3 用 mock transport 就足以复现和验证 |
| 安装、编译、新依赖 | install.sh、setup.py、Makefile | 没有 pip 或 uv，也不能出网（第 11 行） | 无：只改纯 Python 代码，扩展有纯 Python 回退 | 不需要任何操作 |
| 用 git 自查改动 | 无 | 导出的工作树不含 `.git`；环境说明没写容器内的 `/testbed` 有没有 `.git` | 未知，但不是必需的 | `cd /testbed && git status --short`，只有存在 `.git` 时才有用 |

以下命令都在 `/testbed` 下执行，**均为建议，未执行**：

```bash
# C1（建议，未执行）：导入检查
cd /testbed && python -c "import aiohttp, aiohttp.protocol as p; print(aiohttp.__version__, p.__file__)"
```

```bash
# C2（建议，未执行）：题面示例配置（Content-Length 写出器），检查每次 transport.write 的参数
cd /testbed && python - <<'EOF'
import unittest.mock, zlib
from aiohttp import protocol
c = zlib.compressobj(wbits=-zlib.MAX_WBITS)
comp = c.compress(b'data') + c.flush()
t = unittest.mock.Mock(); w = t.write = unittest.mock.Mock()
m = protocol.Response(t, 200)
m.add_headers(('content-length', str(len(comp))))
m.add_chunking_filter(2)
m.add_compression_filter('deflate')
m.send_headers(); m.write(b'data'); m.write_eof()
args = [x[1][0] for x in w.mock_calls]
print(args[1:], all(args), b''.join(args[1:]) == comp)
EOF
```

C2 的预期：
- base 下推断打印 `[b'', b'', b'KI,I\x04\x00'] False True`。
- 修复后，列表里不应再有 `b''`，第二项应为 `True`，拼接结果仍为 `True`，例如 `[b'KI,I\x04\x00'] True True`。

```bash
# C3（建议，未执行）：HTTP/1.1、无 Content-Length → chunked 写出器，只加压缩过滤器
cd /testbed && python - <<'EOF'
import unittest.mock
from aiohttp import protocol
t = unittest.mock.Mock(); w = t.write = unittest.mock.Mock()
m = protocol.Response(t, 200)
m.add_compression_filter('deflate')
m.send_headers(); m.write(b'data'); m.write_eof()
raw = b''.join(x[1][0] for x in w.mock_calls)
print(raw.split(b'\r\n\r\n', 1)[1])
EOF
```

```bash
# C4 / C5（建议，未执行）
cd /testbed && python -m pytest tests/test_http_protocol.py -q
cd /testbed && python -m pytest tests/test_wsgi.py tests/test_web_response.py -q   # 先在未改动时跑，记录基线
```

## 5. 阅读范围

**实际打开过的文件：**

- 角色卡 `r2e_static_review_20260925/roles/public_reader_r2e.md`。卡里链接的 SWE-Gym 公开读者卡，以及同目录和上级目录的其它文件，都没有打开。
- `PUBLIC_DIR` 下的 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`worktree_manifest.json`。清单里引用的 `initial_diff.source` 等包外路径没有打开，所以初态 diff 的具体内容只能从 grep 结果间接看到。
- `worktree/` 中完整读过的文件：`aiohttp/protocol.py`、`tests/test_http_protocol.py`、`aiohttp/__init__.py`、`install.sh`、`run_tests.sh`、`process_aiohttp_updateasyncio.py`、`Makefile`、`.gitignore`、`setup.py`、`tox.ini`、`setup.cfg`、`requirements-dev.txt`。
- `worktree/` 中只读过片段的文件：
  - `aiohttp/web_reqrep.py`：1-22 行的导入部分（grep）、400-640 行
  - `aiohttp/client_reqrep.py`：208-226、250-345、360-455 行
  - `aiohttp/wsgi.py`：125-145、195-216 行
  - `aiohttp/server.py`：130-160 行
  - `aiohttp/client.py`：165-175 行
  - `aiohttp/worker.py`：25-35 行
  - `aiohttp/multipart.py`：10-16、680-715 行
  - `aiohttp/multidict.py`：340-362 行
  - `aiohttp/test_utils.py`：270-300 行
  - `examples/srv.py`：45-75 行
  - `tests/test_client_request.py`：335-400、460-640 行
  - `tests/test_client_functional.py`：1280-1330 行
  - `tests/test_multipart.py`：678-712 行
  - `CHANGES.txt`：前 40 行
- grep 过的范围：在 `aiohttp/`、`tests/`、`examples/`、`docs/*.rst` 中搜索了以下内容：过滤器和写出器的标识符、`asyncio.async`/`create_task`、`chardet`、`compress`/`zlib`、Cython 回退、`mock_calls`、`b''`。

**没有查的范围：**

- 其余模块的全文，例如 connector、parsers、streams、websocket、web_urldispatcher；
- docs 的正文，以及其余测试文件的全文；
- 上游仓库的历史和后续提交；
- 任何私有材料，包括 gold 补丁、隐藏测试、期望结果和旧的审查结论。

**限制：**

- `user_prompt.txt` 只是 `render_user_prompt` 的静态渲染结果，不是模型实际收到的消息。
- `worktree/` 不是完整的运行容器，缺少 `.git`、`.venv`、编译产物和隐藏测试。
- 本报告没有运行任何代码。所有关于"base 下会输出什么"的说法，都来自读代码，再结合 `unittest.mock`、zlib 和 Python 3.9 的语义推断得出。模型实际收到的消息、运行资源和开发条件都没有验证。

**关键未知：**

1. 隐藏检查看的是什么：每次 `transport.write` 的参数（示例的口径）、线上的 chunk 帧（标题的口径），还是两者都看。这决定了"只改 chunked 写出器"够不够。
2. 是否也要求吞掉不经压缩、直接 `write(b'')` 产生的空块（R9）。
3. base 下 `tests/test_http_protocol.py` 在该镜像里能否全部通过（环境说明没有给出这个文件的基线），以及 `chardet` 是否已经安装。
