# aiohttp 4075c653：公开材料独立静态阅读

整理日期：2026-10-03。instance：`aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a`。

## 结论与适用范围

**两个示例的目标明确，足以开展实现；按示例的窄范围理解，没有发现公开测试要求与目标直接冲突。题面的概括措辞存在边界歧义，不能据此全面收紧 header 值或响应解析。** 本报告只证明公开目标可理解及其与可见源码、测试的静态关系，不证明修复正确、actor 已交付、CPU 验收通过或训练资格。

题面实际包含在 `public_reader_bundle.json`，不是缺材料。其 base_commit 声明为 `e181a0e468d4fb35f2c990c604566089a7afe945`；本次未读 git 元数据、未独立验证 checkout 与该提交一致，以所列文件 SHA 绑定实际输入。

只读了指定 bundle 和公开 worktree 的文件。未读取题卡、preparation、私有结论、gold/hidden/candidates、其他线程、仓库共享文档或网络；未安装依赖、SSH、运行目标代码/测试、调用模型工具或修改源码。读取过程仅用了文件列举、文本查找/分段展示及标准库 SHA 计算。新增文件仅为本报告及同目录命令清单。

## 公开目标及 base 对照

1. 题面 `invalid_header = "\xffoo: bar"` 经默认 `.encode()` 转为 UTF-8 字节，非法字符位于 **header 名**，不是 header 值。期望 `feed_data()` 抛出 `BadHttpMessage`。`aiohttp/http_parser.py:68,149-150` 的 header 名规则是黑名单，未列入高位字节；205 行再按 UTF-8 解码。从源码静态推断，该路径无法凭现有名称检查拒绝题面的 `ÿoo`。这是实现与预期的差距，不是题面与公开回归的矛盾。`InvalidHeader` 是 `BadHttpMessage` 的子类（`http_exceptions.py:88`），因此用它拒绝名称符合题面所给异常类别。
2. `b"GET\n/path\x0cHTTP/1.1\r\n\r\n"` 实际是 **HTTP 请求行**；题面和源码都沿用 “status line” 及 `BadStatusLine` 这个名称。它包含字段间 LF 和 form feed。`http_parser.py:280-315` 默认以 CRLF 切行，内部 LF 留在首行；550 行无指定分隔符的 `split(maxsplit=2)` 会把 LF、form feed 当空白分隔，得到正常的三个字段。从静态语义推断可解释题面问题。未运行该输入，不把推断写成实测。
3. Cython 路径的 `feed_data()` 委托 `llhttp_execute`（`_http_parser.pyx:531`），错误映射在811-836行；本次没有精读 llhttp 的实现，也没有编译/执行扩展，故不声称 C parser 在两个例子上必然如何。公开测试的请求/响应 fixture 同时覆盖 Python 和可导入的 C parser（`tests/test_http_parser.py:32-85`）；验收必须记录实际 parser 覆盖范围。

## 公开回归和歧义

- 已有 `test_bad_headers`（171-186行）、`test_invalid_header`（560行）及 `test_invalid_name`（566行）要求拒绝非法 header 格式，但没有复刻题面两个示例。特别是同名的公开 `test_invalid_header` 检查的是缺冒号，不能拿该测试通过代替 `ÿoo` 的验收。
- `test_http_request_parser_utf8`、`test_http_request_parser_non_utf8`（697、714行）和响应 UTF-8 测试（798行）要求保留非 ASCII 的 **header 值** 和 raw bytes。把整个 header 强制为 ASCII 会违背公开回归。题面的 “invalid characters” 未给完整字符集合，示例及已有规则足以确定名称/值必须区分；更宽字符规则仍须公开说明依据。
- `test_parse_headers`（107行）接受 continuation；`test_http_response_parser_lenient_headers`（851行）接受值中的 `\x01`；`test_http_response_parser_bad_crlf`（868行）接受 LF 分行；`test_http_response_parser_no_reason`（843行）接受无 reason phrase。源码也明确响应端默认 lax（`http_parser.py:639-651`；`_http_parser.pyx:651-655`）。题面没有授权废除这些兼容行为。若把 “malformed status lines” 扩成所有响应格式的严格化，就会与公开回归冲突；这不是必须跳过该题的理由，应保留回归并限定实际改动。
- 题面未逐项列明允许的请求行空白、完整 header 名字符集及是否涉及响应端。两个例子足以给出最低明确目标；完整行为边界应由公开说明和可见源码/测试约束，不能要求实现者猜隐藏例子的集合，也不能承诺所有隐藏规则均已确定。
- `setup.cfg:133-134` 默认排除 `dev_mode`；严格响应测试在861行带此 marker 且 Python 路径显式 xfail。`helpers.py:79-81` 表明 DEBUG 受开发模式/环境变量影响。因此常规模式与开发模式结果应分别解释，已有 xfail/skip 应报告其具体原因和范围，不能用整项跳过或扩大排除掩盖矛盾。

## 实现提示和材料完整性

公开 hints 只包含工程流程：使用现有虚拟环境、无网络、修改非测试源码、窄范围运行 pytest、最终简述。它们没有给出补丁、源码定位、gold 行为或隐藏断言。问题示例本身属于公开目标证据；异常名属于可见 API。未发现需要跟随包外私有路径才能获得题面的情况。

## 后续验证建议（全部未执行）

同目录 `public_reader_commands_20261003.json` 提供三个建议命令，均假定在公开运行环境 `/testbed` 执行：题面两个示例的 Python 路径检查、整个公开 parser 模块的常规回归、开发模式下该模块的 `dev_mode` 回归。使用 `-o addopts=''` 是为了清除默认 coverage/marker 命令选项后显式选择原有两种模式，不删测试、不新增排除。环境、导入、collection 问题需要原样报告；C 扩展缺失时必须标明仅覆盖 Python，不能报成双实现验收。现有公开 tests 对两个新例子无直接断言，命令清单因此保留单独示例检查。

本次没有执行上述命令，没有生成运行日志或通过数。

## 实际读取范围及输入 SHA

`rg --files` 只列举公开 worktree 的文件名。内容读取范围：bundle 全文；`tests/test_http_parser.py` 的关键词查找及 1-275、550-575、655-778、790-950 行；`aiohttp/http_parser.py` 的 1-240、265-352、500-720 行（另一次1005-1060区间没有内容）；`aiohttp/_http_parser.pyx` 的关键词查找及520-565、638-661、808-838行；`aiohttp/http_exceptions.py` 的关键词查找及46-108行；`aiohttp/_cparser.pxd` 的关键词查找及1-8、150-165行；`tests/conftest.py`、`setup.cfg`、`aiohttp/helpers.py` 的指定关键词查找，后两者另读120-175、73-85行。为固定输入，以下九个文件额外读取完整字节仅用于 SHA，不执行或导入。

problem_statement 解码后的 UTF-8 SHA 已核对为 `sha256:c3253b921246dcb9c99490b35b129269eb54cf4276f67837a6bd14d73819d731`，与 bundle 声明相同。

| 输入 | SHA-256 |
| --- | --- |
| `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/r2e_aiohttp/materials/4075c653/public_reader_bundle.json` | `sha256:f863c651bb4f72b2d923a1cb3e01d3b06e1404c2d27f1017887c3e16aa49657e` |
| `runs/r2e_static_prep_20260924/v3/public/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/worktree/aiohttp/http_parser.py` | `sha256:61d589e110e1806cfc3c1b14c2498f616626148952d69df8b2cd75b05c1b6f13` |
| `runs/r2e_static_prep_20260924/v3/public/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/worktree/tests/test_http_parser.py` | `sha256:aefe5110a197bc853d0381c17c9542606531cf978d1fe583783ab74faa4f7d41` |
| `runs/r2e_static_prep_20260924/v3/public/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/worktree/aiohttp/_http_parser.pyx` | `sha256:7f32b0c1595c1a71957a218ece8d3977ed9171caad97df8fcd82aa80addfc5d2` |
| `runs/r2e_static_prep_20260924/v3/public/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/worktree/aiohttp/http_exceptions.py` | `sha256:ecb385154c2ad387d9b27640f8d3f99ee91de9cda2f1d68cf3e7a38f79dd6d24` |
| `runs/r2e_static_prep_20260924/v3/public/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/worktree/aiohttp/_cparser.pxd` | `sha256:f2318883e549f69de597009a914603b0f1b10381e265ef5d98af499ad973fb98` |
| `runs/r2e_static_prep_20260924/v3/public/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/worktree/tests/conftest.py` | `sha256:c13598f6166bb0d6ff8292a38f8fb37506e5ccf65103cd09fbbbb18ec261e5ac` |
| `runs/r2e_static_prep_20260924/v3/public/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/worktree/setup.cfg` | `sha256:74a2bc2c8708fe151a654684b364d52c86f0aad6c04e813a6687632534580262` |
| `runs/r2e_static_prep_20260924/v3/public/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/worktree/aiohttp/helpers.py` | `sha256:7d05410a3141e84543b7bb66d8c7fc645e2d3ce876a6b7bd4df0df10df781b37` |
