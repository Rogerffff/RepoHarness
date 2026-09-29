<!-- 协调者注（2026-09-25）：宿主不允许子会话写报告文件（"Subagents should return findings as text"），本文由协调者从该会话被拒的写入调用中原样取出保存，未改一字。 -->
# 私有主审初判（读历史前）：aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac

- 角色：R2E 私有主审，静态审查，2026-09-25。本稿保存于读取任何历史调查之前。
- 版本：base `354153e9b706`（`aiohttp/__init__.py` 为 `3.11.0.dev0`），来源修复提交 `22a12cc2e2ef`；Python 3.9.21，pytest 8.3.3（插件 cov 5.0.0、mock 3.14.0、asyncio 0.25.2）。本题没有材料修订（`revisions.json` 为 `[]`）。
- 证据级别用语：**静态推断**（读代码）、**解析状态**（账本或 short summary）、**执行证据**（日志或 devcheck 输出）。

## 0. 暂定处置与要点

**暂定处置：`needs_review`。可作开发诊断的静态候选，但有两处必须带着的限制；建议先跑反例 K3，再决定是否修订测试。**

1. **真实缺陷存在，但题面把人引向错误的路径。** 缺陷在"经 HTTP 代理 `CONNECT` 后升级 TLS"的路径上：`_start_tls_connection` 不校验指纹。devcheck 以 agent 身份在 base 上执行 C4，结果是 `proxy+bad_fp -> CONNECTED`；私有 gold 对照里同一场景变成 `ServerFingerprintMismatch`（执行证据）。题面示例却是直连，而且用了 21 个字符的 `str` 指纹。在 base 上这个示例会在构造时抛 `ValueError`（devcheck `pr2_2_cmd`）；直连路径本来就会校验（公开功能测试在 base 上 2 passed，见 `pr3_6_pytest`）。题面全文没有提到代理。公开读者只靠公开材料就推出了代理路径，说明读代码可以推知，但题面属于"误导且欠明确"（清单 3、23）。
2. **目标键只检查 mock 交互，不检查指纹校验本身。** 唯一目标键 `TestProxy.test_https_connect_fingerprint_mismatch` 把 `connector._get_fingerprint` 替换成返回 Mock，把 `Fingerprint.check` 改成直接抛异常，只断言代理路径上"调用了 check，并把异常传了出来"。它不检查被校验的是 TLS transport 还是原始代理 transport。所以有一个在现实中什么都没修的候选，按推断会拿到 1：在 `_create_proxy_connection` 里对原始 TCP transport 调用 `check`。真实的 `Fingerprint.check` 遇到非 TLS transport 会直接 `return`（`aiohttp/client_reqrep.py:139-141`）。这个候选就是下面的 K3（静态推断，待实跑）。另外，"代理 + 正确指纹仍能连通"没有任何隐藏测试保护。
3. 评分侧材料一致，结果稳定：当前材料下 noop 两次都是 0，只错目标键；gold 两次都是 1（18/18）。M3 独立 runner 在来源镜像上跑 gold 两次，都是 18 passed。期望映射全是 PASSED，不存在"更完整的修复反被翻转"的键。
4. 最关键的未知项：K3 在正式评分代码下是否真拿 1。另外，模型实际收到的完整消息仍没有捕获；devcheck 的 user 消息是脚本指令，不是题面。

## 1. 八方面覆盖（已查 / 未查）

| 方面 | 已查 | 未查 / 缺口 |
| --- | --- | --- |
| 公开需求（3、23） | 通读 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md` 和 `public_read.md`。核对了题面示例的两处错误：`str` 长度 21 会触发构造期 `ValueError`（执行证据）；直连路径本来就会校验（执行证据）。缺陷真正所在的代理路径题面没有提到。 | 模型实际收到的消息：devcheck 的 `messages_000.json` 是 devcheck 脚本指令，不是渲染后的题面。静态渲染已核对，实际渲染没有核对。 |
| 材料与初始问题（1、2、27） | eval 日志里的 `RH2_SETUP_HIDDEN_TESTS_TREE=80d242…` 与 `run_refs.json` 一致；gold 用 `git apply` 应用，rc=0。base 上的缺陷有两份执行证据：agent 身份的 C4，以及 noop 目标键的失败原因 `AssertionError: ServerFingerprintMismatch not raised`（`r2e_tests/test_1.py:475`，`cleanup=True` 子例）。初态唯一的改动是 `Makefile` 里的 `pip`→`uv pip`，与题意无关。 | — |
| 测试是否测到要求（18–20、25、32） | 逐行读了隐藏测试 `test_1.py`，并与公开 `tests/test_proxy.py` 做了 diff：只多了 import 行、新增的目标测试，以及 `test_https_connect` 签名上的类型注解。`conftest.py` 与公开的 `tests/conftest.py` 逐字相同。目标键的调用链追到了 `_create_connection → _create_proxy_connection → _start_tls_connection`。 | 目标键是 mock 交互测试（见 §2）；K3、K4 类错误实现能否蒙混，还没有实跑。 |
| 误拒合理解（24、28） | 检查点放在哪一层都能过：放在 `_start_tls_connection`、`_create_proxy_connection` 或 `_create_connection` 都行（静态推断）。硬约束有两条：必须经 `self._get_fingerprint(...)` 取指纹，必须调用返回对象的 `.check(...)`。 | K2（语义等价、但不经 `_get_fingerprint`）预计判 0，待实跑。 |
| 回归与 gold 完整性（26、27） | 17 个回归键就是整个公开 `tests/test_proxy.py`，覆盖代理请求的构造参数、`start_tls` 的实参、代理认证和各类错误分支。gold 在 HTTP 代理 + `start_tls` 路径上修对了（私有对照 C4）。 | 下面这些 gold 未覆盖，隐藏测试也不测：`_wrap_existing_connection` 分支（本环境不可达）；`https://` 代理那一跳；异常的 host/port 实际是代理地址；"代理 + 正确指纹"的正例。 |
| 开发条件（6–15） | devcheck 在正式启动路径下以 agent 身份执行：依赖探查、题面示例、四组公开测试、回环 TLS + CONNECT 复现（§6）。 | 真实模型求解；Qwen adapter 链路。 |
| 交付与评分边界（4、16–17、21–22、29–31） | 修复只涉及 `aiohttp/connector.py`，属非测试源码。preflight 三项都是 ok（HEAD 无子提交、隐藏测试不可读、解释器可执行）。`CHANGES/` 里没有指纹相关的片段；公开 `test_proxy.py` 不含新测试。 | 非 gold 候选经 actor 冻结 → 投影 → grader 的完整交付，本题没有实跑。 |
| 题目关系（5、29–30、37–40） | 核对了跨题比对（§7）；打开同仓 4 题的公开包，确认版本与相关代码。 | 上游 PR 编号与外部答案可达性未查（actor 不联网）。 |

## 2. 隐藏测试展开

**目标键 `TestProxy.test_https_connect_fingerprint_mismatch`**（`hidden_tests/test_1.py:381-479`）

- 入口是 `connector._create_connection(req, [], ClientTimeout())`。`req` 是 `https://www.python.org`，代理是 `http://proxy.example.com`。
- 依次用 `enable_cleanup_closed=True` 和 `False` 各跑一个 subTest。pytest 8.3.3 没有装 subtests 插件，`subTest` 在这里不起作用，第一个失败就结束整个测试；noop 日志里停在 `cleanup=True`。
- mock 的范围：
  - `aiohttp.connector.ClientRequest` 返回真实的 `proxy_req`，其 `send` 与 `proxy_resp.start` 被替换（后者返回 `status=200`）。
  - `_resolve_host` 被替换；`loop.create_connection` 返回 `(Mock(), Mock())`。
  - `loop.start_tls` 返回 `TransportMock()`，它是 `asyncio.Transport` 的子类，`close` 什么都不做，`get_extra_info` 一律返回 `None`。
  - **`connector._get_fingerprint` 被整体替换**（autospec），任何参数都返回 `fingerprint_mock`，其 `check.side_effect = ServerFingerprintMismatch(b"exp", b"got", "example.com", 8080)`。
- 唯一的断言是 `assertRaises(aiohttp.ServerFingerprintMismatch)`（子类也算通过）。
- 对应的公开要求：题面 Expected Behavior 说"指纹不匹配时连接器应抛 `ServerFingerprintMismatch`"。触发条件（代理）在公开材料里只能从代码推出。

**测不到的内容（静态推断）**

1. **被校验的是哪个 transport**：`check` 是 mock，传原始 TCP transport 也会抛。
2. **正确指纹经代理能否连通**：隐藏集里没有正例，"对代理路径上所有配置了指纹的连接一律抛错"也能通过。
3. **请求级与连接器级指纹的优先级**：`_get_fingerprint` 被整体替换，测不到。
4. 是否关闭 TLS transport、是否登记到 `_cleanup_closed_transports`（两种 `cleanup` 取值都不作断言）。
5. 异常里的 host/port 取值。

**回归键（17 个）**，与公开 `tests/test_proxy.py` 逐字相同，只差类型注解。受影响接口有三处：

- `test_connect` 与 `test_proxy_headers` 断言 `ClientRequest(..., ssl=True)`，即代理请求继承 `req.ssl`。
- `test_https_connect_pass_ssl_context` 断言 `start_tls(ANY, ANY, _SSL_CONTEXT_VERIFIED, server_hostname=..., ssl_handshake_timeout=ANY)`。
- 多个测试让 `start_tls` 返回 `mock.Mock()`。这时如果没配指纹也去读证书，就会出错。

通读了全部回归测试体。公开 devcheck 显示 base 上这 17 个是 17 passed，agent 自己能跑。

## 3. 双向映射（核心表）

| 公开要求 / 合理旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖 | 执行证据或下一步 |
| --- | --- | --- | --- | --- |
| 经 HTTP 代理访问 HTTPS 时，指纹不符应抛 `ServerFingerprintMismatch`，不交出连接 | 题面 L7、L26、L30（没提代理）；代码 `connector.py:1379-1466` 缺少调用点 | 目标键 / `assertRaises` | **部分**：只测"调用 check 并传出异常"，不测校验的是哪个 transport | noop 失败"not raised"；gold 对照 C4 抛错；K3 待跑 |
| 经代理 + 正确指纹仍能连通 | 合理旧行为；公开功能测试只覆盖直连正例（`test_client_functional.py:605-623`） | 无 | **缺失** | gold 对照 C4 `proxy+good_fp -> CONNECTED`；K4 待跑 |
| 请求级优先于连接器级，两者都要生效 | `_get_fingerprint`（`connector.py:1046-1053`）；公开读者 R3 | 目标键 mock 掉了 `_get_fingerprint` | **缺失**（只能间接要求"用这个 helper"） | 公开读者 C4 的四种情况都已覆盖（gold 对照） |
| 直连指纹校验与多地址回退保持不变 | `connector.py:1326-1343`；公开 `test_connector.py` | 不在隐藏集 | **缺失**（隐藏集不测，公开测试可用） | devcheck `pr3_4` 10 passed、`pr3_6` 2 passed（base） |
| `Fingerprint` 构造契约（只收 32 字节 sha256） | 公开 `test_client_fingerprint.py`、`test_client_request.py` | 不在隐藏集 | **缺失**；按题面示例放宽构造器不会被扣分 | 属于"遵循冲突示例"的风险，见 §5 |
| 代理请求的构造参数、`start_tls` 实参与错误分支保持不变 | 公开 `tests/test_proxy.py` | 17 个回归键 | 覆盖 | 当前材料 gold 18/18 |
| 异常字段的含义（代理地址还是目标地址） | 无约定（公开读者 R5） | 无 | 不适用 | gold 对照：host/port 是代理地址（`port=39183` 是代理端口） |

**反查**：目标键的每个断言都能对到题面 Expected Behavior 的异常类型。它对 `_get_fingerprint` 和 `.check` 这两个调用形状有依赖，依据是现有的内部 helper（直连路径就用它，`connector.py:1279`），而不是公开规格。

## 4. R2E 专项

- **(a) 非 PASSED 键**：没有。18 个键全是 PASSED。更完整的修复（例如同时处理 `https://` 代理那一跳、覆盖 `_wrap_existing_connection`）不会翻转任何键。前提是不改变 `ClientRequest(..., ssl=True)` 这个断言：在这些回归测试里 `req.ssl` 是 `True`，只在 `req.ssl` 为 `Fingerprint` 时才换值的改法不受影响。
- **(b) 题面描述的报错是否出现在 noop 失败原因里**：失败原因是 `AssertionError: ServerFingerprintMismatch not raised`，与题面 "No exception is raised" 一致。但这个现象只出现在代理路径上；照题面示例本身得到的是 `ValueError`（执行证据）。
- **(c) 题面是否泄漏修法**：没有。问题出在信息不足，而且示例会误导。
- **(d) 依赖 base 版测试辅助、搬迁伪影或撞键**：
  - 隐藏 `conftest.py` 与公开的相同，通过 `pytest_plugins` 加载 `aiohttp.pytest_plugin`，属于候选可改的包代码，这是同仓共有的通道。
  - 测试导入 `aiohttp.test_utils.make_mocked_coro`、`aiohttp.helpers.TimerNoop`、`aiohttp.connector._SSL_CONTEXT_VERIFIED`、`aiohttp.client_reqrep.Fingerprint`，都是包代码。候选如果改名或移动这些对象，会导致收集失败，但没有合理的修复需要这样做。
  - 不依赖相对路径资源。只有一个测试文件，不会撞键。
- **(e) 时间、随机、资源敏感**：没有。全是 mock，不联网、不 sleep，单例约 0.02 s；`key_data` 用了 `os.urandom`，但 `TestProxy` 用不到。两次 noop、两次 gold 与 M3 两次结果一致。
- **(f) 材料修订**：本题没有。

## 5. gold 检查与候选反例

**gold**（`aiohttp/connector.py` 的 `_start_tls_connection`，在 `start_tls` 之后插入）的逻辑：

1. 先判断 `isinstance(tls_transport, asyncio.Transport)`。
2. 用 `self._get_fingerprint(req)` 取指纹。
3. 调用 `check`；不匹配时关闭 transport，并在启用 cleanup 时登记，然后重新抛出。

评价：

- 修复了题意所指、本环境可达的路径（私有对照 C4 中两个错误指纹的情况都抛错，正确指纹照常连通）。没有无关改动。
- 未覆盖的部分：`_wrap_existing_connection` 分支（只有事件循环没有 `start_tls` 时才会走到，Python 3.9 asyncio 走不到）。
- `https://` 代理那一跳：`proxy_req` 继承目标站指纹，这是既有行为，gold 没改；TLS-in-TLS 在 3.9 上本来就不可用。
- 异常的 host/port 取自 TLS transport 的 `peername`，经代理时是代理地址。
- `isinstance` 守卫对"不继承 `asyncio.Transport` 的 TLS transport"会放行而不校验（fail-open，可能出现在第三方事件循环上，未核实）。它的实际作用看来是让回归测试里 `start_tls` 返回 `mock.Mock()` 时不进入检查。

**供协调者实跑的候选**（K1–K3 能区分结论，K4 次要）：

| ID | 改哪里、怎么改 | 真实行为（静态推断） | 预期得分 / 不符键 |
| --- | --- | --- | --- |
| K1 合理替代 | `aiohttp/connector.py::_create_proxy_connection`：把 `return await self._start_tls_connection(transport, req=req, timeout=timeout)` 改成先接收 `tls_transport, tls_proto`，再执行 `fp = self._get_fingerprint(req)`；`if fp:` 就 `try: fp.check(tls_transport)`，捕获 `ServerFingerprintMismatch` 时 `tls_transport.close()`，cleanup 启用则登记，然后 `raise`；最后 `return tls_transport, tls_proto`。这段代码仍在外层 `try/finally: proxy_resp.close()` 之内 | 与 gold 等价；公开 C4 的两个代理错误指纹情况都抛错 | 预期 1 |
| K2 语义等价但不经 helper | 同 gold 的位置（`_start_tls_connection` 里 `start_tls` 之后），但指纹这样取：`fp = req.ssl if isinstance(req.ssl, Fingerprint) else (self._ssl if isinstance(self._ssl, Fingerprint) else None)`，其余与 gold 相同 | 与 gold 完全相同（逻辑就是 `_get_fingerprint` 展开） | **预期 0**，不符键 `TestProxy.test_https_connect_fingerprint_mismatch`（"not raised"）。用来量化 mock 耦合（清单 24）；这种写法不太常见 |
| K3 错误修复蒙混 | `_create_proxy_connection` 里，在 `transport, proto = await self._create_direct_connection(proxy_req, …)` 之后立刻加 `fp = self._get_fingerprint(req)`；`if req.is_ssl() and fp: fp.check(transport)`，也就是校验连到代理的原始 TCP transport | `Fingerprint.check` 遇到非 TLS transport 直接 `return`，缺陷原样保留；公开 C4 的 `proxy+bad_fp` 仍是 CONNECTED | **预期 1（误收）**。这是可信的误诊：解题者看到代理这一跳因 `proxy_req.is_ssl()` 为假而跳过检查，就可能这样"补"（公开读者 §3.2 也注意到这一点） |
| K4 过度拒绝（次要） | `_start_tls_connection` 里 `start_tls` 之后：只要 `self._get_fingerprint(req)` 为真，就关闭 transport 并 `raise ServerFingerprintMismatch(b"", b"", req.host, req.port)`，不做比较 | 正确指纹经代理也被拒；C4 的 `proxy+good_fp` 变成异常 | 预期 1（误收）；可信度低，只用来说明正例缺失 |

**遵循冲突示例的候选**（单列，不算"合理修复被误拒"）：如果只按题面示例放宽 `Fingerprint` 构造器、让 `str` 或任意长度都能通过，目标键仍然失败，得 0，这个 0 是合理的。如果同时放宽构造器、又修了代理路径，就会得 1，而它破坏了公开的构造契约测试（隐藏集不包含这些测试，属于未测回归）。"判断无需修改"的候选得 0，也是合理的，因为缺陷确实存在（C4）。

## 6. 开发需求（逐题）

| 项目 | 事实 | 证据级别 |
| --- | --- | --- |
| 导入 | 在 `/testbed` 下 `python -c 'import aiohttp'` 得到 `/testbed/aiohttp/__init__.py` 和 `3.11.0.dev0`。包没有装进 venv，需要 cwd 在 `/testbed` 或设 `PYTHONPATH=/testbed` | 镜像层面实测（devcheck `env`，agent uid 54321） |
| 依赖 | `trustme`、`proxy`（proxy.py）、`pytest_cov`、`aiohappyeyeballs` 都在；pip 24.2 可用，但不联网；pytest 8.3.3 | 镜像层面实测（`pr0_1`、`env`） |
| 公开测试 | `test_client_fingerprint.py` 12 passed；`test_connector.py -k …` 10 passed；`test_proxy.py` 17 passed；`test_client_functional.py -k fingerprint` 2 passed。以上都是 base、agent 身份的结果；gold 对照下结果相同 | 镜像层面实测 |
| 复现资产与服务 | 回环 TLS 源站（`examples/server.crt/.key`，证书虽过期但不影响指纹路径）加标准库写的 CONNECT 代理，可以在不联网的情况下区分修复前后：base 三个代理情况都是 CONNECTED，gold 两个错误指纹情况抛错 | 镜像层面实测（base 以 agent 身份跑；gold 对照以 root 身份在一次性私有容器里跑） |
| 权限与资源 | agent 可写 `/testbed`；`/rh2/bash_env` 不可写（DENIED）。容器配置：2 CPU、4 GiB（无 swap）、`/tmp` 1 GiB、pids 512、`cap_drop ALL`、`no-new-privileges`。评分时内存峰值约 520 MB | 实测（prelaunch inspect；账本 `resource`） |
| 网络 | 准备、解题、测试、评分各阶段都不需要联网；题面示例的 `https://example.com` 可以用回环地址代替 | 实测 + 静态 |
| 构建 | 不需要编译 C 扩展（`vendor/llhttp` 是空子模块；本题代码是纯 Python） | 静态 |
| 提交边界 | 只改 `aiohttp/connector.py`；改仓库里的 `tests/` 不影响评分（隐藏测试另放在 `r2e_tests/`） | 静态；非 gold 候选的完整交付链没有实跑 |
| 镜像身份 | 评分运行用的是 `sha256:dfd6021f…`（R-f 机器）；devcheck 与私有对照用的是 `sha256:2b571f22…`。两者 tag 与配方都是 `rh2-r2e-derived/aiohttp:22a12cc2e2ef-r2e_derive_v1`，重建后 ID 不同。Python、pytest 与插件版本以及 `git status` 输出都一致，但没有逐层比对 | 实测 + 推断 |
| 真实模型求解 | 需要真实模型或经 adapter 才能确认的部分，一律 actor 待验 | 未知 |

devcheck 命令是否足够：足以确认导入、依赖、公开测试和离线复现这四项开发条件，其中 C4 能直接区分修复前后。它没有覆盖实际的题面渲染和非 gold 候选，这两项不影响开发条件的结论。

## 7. 题目关系

- 本题 base（3.11.0.dev0）是池内同仓 5 题里最新的；其余几题分别是 3.10.6.dev0（`1c1c0ea3`）、3.9.0b0（`4075c653`）、0.17.0a0（`61833518`）、0.9.1dev（`240da100`）。`cross_task_gold_scan.json` 里没有以本题为 `task` 的行，也就是说本题 gold 没有逐字出现在其它题的初态里。我查了其它 4 题的公开 `connector.py`：`_start_tls_connection` 里都没有指纹检查，其中两题连 `tests/test_proxy.py` 都没有。所以不存在"本题修复已经包含在别题初态"的情况。
- 反向关系：本题初态包含 `1c1c0ea3` 的 gold（7/7 行）和它的新测试 `test_run_app_raises_exception`，也包含 `4075c653` 的新测试名 `test_http_request_bad_status_line_whitespace`，以及 `240da100` 的测试名 `test_request_port`（只比对了名字，可能是同名巧合）。这些影响的是那几题的暴露面（本题工作树等于它们的"未来"），不影响本题是否有效。如果同批同时使用，需要登记。
- 任务类型：安全相关的连接层缺陷修复，题面误导，需要读代码自己找到触发条件。上游修复是公开的，但 actor 不联网（外部答案可达性这里没有核实）。

## 8. 缺口与建议队列

1. **唯一优先的下一步**：用正式评分代码实跑 K3（加上 K1、K2 作对照）。如果 K3 得 1，就坐实"测试会放过未修复缺陷的实现"（清单 25、32）。
2. 修订建议（需要用户决定，属于测试标准变更；本稿只提建议）：
   - 保留目标测试的结构，但给 `TestProxy` 的 TLS transport 提供真实的 `sslcontext`、`ssl_object.getpeercert`、`peername` extras，并使用真实的 `Fingerprint`，让"校验错了 transport"的实现失败。
   - 另加一个"经代理 + 正确指纹照常连通"的正例；这两条可以参照公开读者 C4 改写成回环功能测试。
   - 题面补充"经 HTTP 代理（CONNECT）访问 HTTPS 时"这一触发条件，并修正示例（改成 `ssl=Fingerprint(32 字节)`）。这一条改的是公开规格，需要单独登记。
3. 如果不修订，作开发诊断时应标注：reward=1 不能证明修复有效（K3 类），reward=0 里可能混有被示例误导（改构造器或判断无需修改）的轨迹。
4. 未查项：实际渲染的消息；非 gold 候选的完整交付链；真实模型轨迹；上游 PR 与外部可达性。

## 9. `checks` 草稿（40 项编号，稀疏）

- pass：1、2、4、5、6、7、8、9、10、11、13、14、17、18、19、20、22、29
- issue：23（题面误导、缺触发条件）、25（K3 类会误收，静态推断待实跑）、26（正例与构造契约不在隐藏集）、32（verifier 只检查 mock 交互）
- unknown：3（实际消息未捕获）、16（非 gold 候选的交付链）、24（K2 待实跑，可信度低）、27（gold 在可达路径上正确；fail-open 边界未核实）、31（`aiohttp.pytest_plugin` 等包代码候选可改，是同仓共有通道）
- not_applicable：12、28、37
- not_checked：15、21（只看了成功与断言失败两种形态）、30、33–36、38–40

## 附：阅读范围

- 方法文件：角色卡、八方面协议、R2E 第二批环境卡、记录模板、40 项清单。
- 公开侧：`public_read.md`；PUBLIC_DIR 下的 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`worktree_manifest.json`（只看了结构），以及 manifest 指向的 `initial.diff`（原始事实文件，只涉及 `Makefile`）。
- 公开源码与测试：`aiohttp/connector.py` 第 990–1475 行及 grep 结果；`aiohttp/client_reqrep.py` 第 125–150 行；`aiohttp/client_exceptions.py` 的类层次；`aiohttp/base_protocol.py` 的 `connection_made`；`tests/test_client_functional.py` 第 626–650 行；`tests/test_proxy.py`（与隐藏测试做了全文 diff）；`tests/conftest.py`（全文 diff）。
- 私有侧：`gold.patch`、`expected_output.json`、`run_tests.sh`、`revisions.json`、`run_refs.json`、`grading_bundle.json`、`validation_bundle.json`；隐藏测试 `conftest.py` 与 `test_1.py` 全文。
- 运行原件：R-f（09-23）和环境轮复跑（09-24）的 noop/gold 账本第 2 行（字段抽取）；两份当前 noop/gold 的 eval 日志（sha256 与 `run_refs.json` 一致）；R-f 两份日志的汇总行；M3 gold a1/a2 日志的汇总行。
- devcheck：`commands_with_preflight.json`、`captures/*.out`、`prelaunch.json`、`attempt.json`（grep）、`activation_check.json`、`cc_version_observed.json`、`stub/requests/messages_000.json`（只看了 user 文本）、`private_gold/private_control.json` 与 `stdout.log`。
- 跨题：两份比对 JSON 里 aiohttp 的行；同仓其它 4 题公开包的 `public_bundle.json`（base）、`aiohttp/__init__.py`（版本）和 `connector.py`（grep 指纹）。
- 没有读：任何历史调查或审查目录、本批 README、`assignments.json`、`grader_candidates.md`、其它题的私有包。没有运行项目代码，也没有开容器。
