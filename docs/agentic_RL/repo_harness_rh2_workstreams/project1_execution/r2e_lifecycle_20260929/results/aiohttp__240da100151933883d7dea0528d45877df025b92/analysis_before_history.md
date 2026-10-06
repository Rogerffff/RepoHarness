# 私有主审初判（读历史前）：aiohttp__240da100151933883d7dea0528d45877df025b92

- 角色：R2E 私有主审（`roles/investigator_r2e.md`，单题闭环试行，按统一标准 v1），2026-09-29，干净上下文。本文件在读任何历史调查之前保存。
- 性质：静态阅读，加上复读已有运行原件。没有运行项目代码，没有开容器或远端，没有改任何原件。候选得分都是源码推断，等协调者正式评分。
- 路径约定（相对仓库根）：
  - `PUB` = `runs/r2e_static_prep_20260924/v3/public/aiohttp__240da100151933883d7dea0528d45877df025b92`；`WT` = `PUB/worktree`（即解题者看到的 `/testbed`）
  - `PRIV` = `runs/r2e_static_prep_20260924/v3/private/aiohttp__240da100151933883d7dea0528d45877df025b92`；`HT` = `PRIV/hidden_tests/test_1.py`
  - `LOG_NOOP` / `LOG_GOLD` = `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-a_fd1119cd.eval.log` / `…-all-gold-a_508fe701.eval.log`
  - `PR` / `CMDS` = 本目录的 `public_read.md` / `commands.json`
- 候选命名：DG = 退化候选，AL = 合理替代，WR = 可能蒙混的错误实现，SC = 顺手改动探针。刻意不用 D1、P1 这类名字，以免与 v1 的根因编号撞名。

## 0. 暂定结论

- **题目**：base `ef756ce2`（aiohttp 0.9.1dev）。`ProxyConnector._create_connection` 把明文目标改写成绝对形式 URL 时，用了不含端口的 `req.host`（`WT/aiohttp/connector.py:342-344`），显式端口因此丢失。gold 只把 `host=req.host` 改成 `host=req.netloc`（`PRIV/gold.patch:9-10`）。
- **严重度：S1（T2c，示例拟合）**。唯一目标键 `ProxyConnectorTests.test_request_port`（`HT:570-584`）与题面示例逐字相同：同一 URL、同一代理、同样直接调用 `_create_connection`、同一期望串（`PUB/user_prompt.txt:18-24, 29-31`）。隐藏测试里没有第二个带显式端口的目标 URL。按 v1 §4 第 2 步（决定 D1 的严格版），只看测试文本就能判定。
- **待实跑**：
  - 第 3 步：退化候选 DG1（只在端口为示例的 1234 时补 `:1234`）预测得 1；实跑得 1 就再记 T2b。
  - 第 4 步：还没有真实模型候选。审查中构造的 WR1（让 `ClientRequest.host` 带上端口）预测得 1。实跑得 1 就另记一个 S1：它破坏了同一功能下 https 显式端口的 CONNECT 目标，也破坏了直连显式端口这一常用行为（公开测试 `test_host_port` 有断言）。
- **其它登记**：
  - T5：两个期望 FAILED 的键是 py3.9 不兼容造成的死键，已按日志解释；只有越界的 py3.9 移植才会让它们翻转。
  - P4：题面示例原样不能运行；公开读者已给出 mock 替代复现。
  - X1：本题修复与测试原样出现在同仓 `618335186f22` 的初态里。
  - 未见 T1、P1、P2、P3、P5、P6、G1、X2 或交付类 D1 的证据。
- **修订**：
  - R-c 第 1 项（补非示例实例）必做。
  - R-c 第 2 项（https 显式端口的 CONNECT 目标）在 WR1 得 1 时做。
  - R-a（删掉两个死键）可选。
  - 草案见 §10。
- **暂定处置**：`needs_review`（`scope=static_review`）。原因有三：
  1. 测试层的 S1 要等 R-c。
  2. actor 条件要等本批 devcheck。
  3. 当前材料已有 noop 0 / gold 1 各 3 次执行证据，但都在旧机器的派生镜像上跑的；新机器重建镜像后需要复跑。
- **v1 用途初判**：
  - `problem_localization`：yes。
  - `capability_comparison`：conditional。还差重建镜像上的 devcheck 与 noop/gold；R-c 完成前，得 1 的补丁要走预登记后检，查非示例端口和 host/port 语义。
  - `training_candidate`：no。当前版本有未处理的 S1，R-c 验收后重判。
  - `heldout_candidate`：no。理由同上；另外必须与 `618335186f22` 等同仓题按仓库分在同一组。
- **最关键未知**：DG1 与 WR1 的正式得分；新镜像上 actor 侧公开命令的实跑结果。**唯一优先下一步**：在重建的派生镜像上同批正式评分 gold、noop、DG1、WR1（AL1、SC1 可以同批），同时跑 devcheck。

## 1. 公开读者产物核对（第 1 步）

`PR` 的需求表 R1–R10、合理路线和 U1–U4 与我读到的公开包一致。关键引用我都核过：`connector.py:331-384`、`client.py:215-251, 268-314`、`tests/test_connector.py:292-568`、`tests/test_client.py:332-368`、`user_prompt.txt`。`CMDS` 的 6 条命令在静态上没发现写错，引号、`-p no:cacheprovider` 和退出码预期都合理。

公开读者的静态推断里，下面几条已有评分侧运行旁证。注意这些是 grader 身份下的事实（uid 54322，`.venv/bin/python -m pytest -rA r2e_tests`），不等于 actor 条件：

- py3.9 下 `TCPConnector._create_connection` 没加 `@asyncio.coroutine`（`connector.py:274`），对真实事件循环 `yield from` 原生协程会抛 `TypeError`：见 `LOG_NOOP:76-84`。
- `ProxyConnectorTests` 的 13 个公开用例在 base 上全过：`LOG_NOOP:225-237`。隐藏文件就是公开文件加一个测试，见 §2。
- 环境是 Python 3.9.21、pytest 8.3.4，插件 cov / mock / asyncio：`LOG_NOOP:24-27`。

公开读者没有、也无法捕获的条件：

- **模型实际收到的消息**：`user_prompt.txt` 只是静态渲染；`public_hints` 只写进容器里的 `/rh2/public_task_bundle.json`（`PUB/environment_brief.md:3-4`）。环境卡 §2 把"模型实际收到的完整消息"列为未验证。
- **actor 容器条件**：uid 54321、`/testbed/.venv`、没有 pip、`/testbed` 必须在 `sys.path` 上、裸 `pytest` 收集会失败（`PUB/environment_brief.md:10-13`，这是环境阶段的描述）。此外还有 R2E 预检三项，以及 6 条公开命令的实际输出和墙钟时间。这些都要等本批 devcheck。
- **初态脏树怎样呈现给解题者**：`git status` 会列出 3 个已修改文件和 3 个未跟踪文件（`LOG_NOOP:1-6`），题面和提示都没有说明。影响见 §6。

U1–U4 在隐藏测试中的落点：U1（显式默认端口）、U2（https 的 `req.path`）、U3（代理请求的 Host 头带不带端口）都没有断言。U4 不影响评分，因为隐藏测试从 `aiohttp.client` 导入 `ClientRequest`（`HT:14`）。

## 2. 隐藏测试展开（第 2 步）

`PRIV/hidden_tests/` 下只有空的 `__init__.py` 和 `test_1.py`（584 行）。`test_1.py` 就是公开的 `WT/tests/test_connector.py`（568 行），逐字不变，再在末尾加上 `test_request_port`（`HT:569-584`）；两者 diff 只有这 16 行新增。所以 33 个键里有 32 个与公开可跑的同名测试完全相同，行号也相同。

### 2.1 目标键：`ProxyConnectorTests.test_request_port`

这是唯一一个 noop 与 gold 结果不同的键。

- **调用路径**：
  1. `mock.patch('aiohttp.connector.ClientRequest')`（`HT:570`）让 connector 内部构造代理请求时，拿到测试预先建好的真实 `proxy_req`（`HT:572-573`）。
  2. `_fake_coroutine`（`HT:305-312`）把 `loop_mock.create_connection` 换成一个立即返回 `(tr, proto)` 的生成器（`HT:578-580`）。
  3. 目标请求用测试模块导入的真实 `ClientRequest` 类构造（`HT:14, 582`）。
  4. `run_until_complete(connector._create_connection(req))`（`HT:583`）进入 `ProxyConnector._create_connection`（`connector.py:331-384`），再进入 `TCPConnector._create_connection`（274-298）。其中 `_resolve_host` 没打桩，但默认 `resolve=False`，不查 DNS（251-272）。
  5. 调用 `loop_mock.create_connection` 后，回到 342-344 行改写 `req.path`；没有代理认证，也不是 ssl，于是直接返回。
- **最终断言**：`req.path == 'http://localhost:1234/path'`（`HT:584`）。它既不检查代理请求的构造参数，也不检查 `req.host` / `req.port`。
- **依据**：题面的 Description 与 Expected Behavior（`user_prompt.txt:9, 29-31`）。
- **执行证据**：noop 的失败信息是 `AssertionError: 'http://localhost/path' != 'http://localhost:1234/path'`（`LOG_NOOP:199-205`），与题面的 Actual / Expected 逐字相同；gold 下 PASSED（`LOG_GOLD:213`）。

### 2.2 回归键（32 个，逐字来自公开文件）

| 组 | 键 | 关键断言 | 对本题的约束 |
| --- | --- | --- | --- |
| 代理改写 | `test_connect`、`test_auth`、`test_auth_from_url` | 无端口 URL 改写为 `'http://www.python.org/'`（`HT:341, 400, 438`）；`test_connect` 精确断言代理请求的构造参数 `('GET', 'http://proxy.example.com', auth=None, headers={'Host': 'www.python.org'}, loop=loop_mock)`（`HT:348-352`）；认证头迁到 `PROXY-AUTHORIZATION`（`HT:401-404, 439-442`） | 挡住"总是补端口"，也挡住改代理请求参数 |
| 失败时不改请求 | `test_proxy_connection_error`、`test_auth__not_modifying_request` | 解析抛 `OSError` 时转成 `ProxyConnectionError`，`req.path == '/'`，请求头不变（`HT:371-374, 462-466`） | 挡住"连上之前就改写" |
| HTTPS CONNECT | `test_https_connect` 及 `_runtime_error`、`_http_proxy_error`、`_resp_start_error` | 默认端口下 CONNECT 目标是 `'www.python.org:443'`，检查 `pause_reading` / `get_extra_info` 调用和三种异常（`HT:490-493, 516-518, 542-544, 567-568`）；不断言 https 的 `req.path` | 只约束默认端口 |
| 构造与认证 | `test_ctor`、`test_ctor2`、`test_proxy_auth`、`test_auth_utf8` | 代理 URL 与 `proxy_auth` 的校验（`HT:314-322, 354-361, 411-415`） | 基本无关 |
| 连接池 | `BaseConnectorTests` ×14、`HttpConnectionTests` ×3 | `_get` / `_release` / `_cleanup` / `connect` / 析构（`HT:20-244`） | 只防误改 `BaseConnector` |
| 端到端（期望 FAILED） | `HttpClientConnectorTests.test_tcp_connector` / `test_unix_connector` | 真实 socket 请求返回 200（`HT:260-289`） | 死键，见 §4(a) |

阅读范围：目标键和 `ProxyConnectorTests` 逐行读完，并追到了源码。`BaseConnectorTests` / `HttpConnectionTests` 只读了断言，没有逐个分支追 `BaseConnector`；它们与改写行没有交集，noop 和 gold 下状态也相同。

## 3. 双向映射（第 3 步）

### 3.1 公开要求 / 合理旧行为 → 断言

| 编号 | 要求或旧行为 | 公开依据 | 测试 / 决定性断言 | 覆盖 | 证据或下一步 |
| --- | --- | --- | --- | --- | --- |
| R1 | 带显式端口的 http 目标经代理建连后，`req.path` 是含端口的绝对 URL | `user_prompt.txt:9, 29-31` | `HT:584` | **部分：只用了示例字面值** | noop F / gold P；DG1 待跑 |
| R1' | R1 的非示例实例（其它主机、端口、路径） | `user_prompt.txt:9` 的一般表述 | 无 | 缺失（T2c） | R-c 第 1 项 |
| R2 | 改写在 `_create_connection` 内完成 | `user_prompt.txt:23-24`（示例直接调它，随后读 `req.path`） | `HT:583-584` | 覆盖 | gold P |
| R3 | 无端口 URL 不补 `:80` | 公开 `tests/test_connector.py:341, 400, 438` | 同行号 | 覆盖（公开可跑） | noop/gold P |
| R4 | 连代理失败时 `req.path` 和请求头不变 | 公开 `test_connector.py:363-374, 448-466` | 同左 | 覆盖 | P |
| R5 | 代理认证头迁移 | 公开 `test_connector.py:376-446` | 同左 | 覆盖 | P |
| R6 | 代理请求的构造参数不变 | 公开 `test_connector.py:348-352` | 同左 | 覆盖（只测无端口） | P |
| R7 | HTTPS 走 CONNECT，目标是 `host:port` | 公开 `test_connector.py:468-568`；`connector.py:354-361` | 同左（只测默认端口 443） | 部分：显式端口没有断言 | 由 WR1 决定；R-c 第 2 项 |
| R8 | `ClientRequest.host` 不含端口；直连显式端口时按 `(host, port)` 连接 | 公开 `tests/test_client.py:332-346`（该文件 647 行有 `asyncio.async`，在 3.9 下整个文件不能收集）；`connector.py:143, 285, 290-291` | 无 | 缺失 | 由 WR1 决定 |
| R9 | 查询串随 `req.path` 保留 | `client.py:268-294` | 无（示例不带查询串） | 缺失（T3） | 私有对照顺带核 |
| R10 | URL 里的 `user:pass@` 不进请求行 | `client.py:227-230` | 无 | 缺失（T3，边缘） | 登记 |
| R11 | 用户自定义 Host 头时，请求行仍按 URL 生成 | 公开 `test_client.py:352-368`（Host 头可以被用户覆盖） | 无 | 缺失（T3，边缘） | 登记 |
| U1 | 显式默认端口是保留还是省略 | 两种写法都是合法的绝对 URI | 无 | 合理空白，不应断言 | — |
| U2 | https 目标的 `req.path` | 上游后来对 ssl 不再改写（§7） | 无 | 合理空白，不应断言 | — |

### 3.2 反查：关键断言 → 公开依据

- `HT:584` 的依据是题面示例。它也是唯一只出现在隐藏测试里的断言。
- 其余 32 个键全部来自公开、可跑的 `WT/tests/test_connector.py`。没有只在隐藏测试里出现的文案、helper 名、mock 形状或调用顺序要求，所以没有 T1 / P3 的证据。
- `mock.patch('aiohttp.connector.ClientRequest')` 带来一个 mock 形状约束：如果在 connector 里通过 `ClientRequest` 这个名字读类属性，读到的会是 MagicMock。这个约束在可跑的公开测试里同样存在（公开 `test_connector.py:324, 376, 417, 448, 468, 495, 520, 546`），解题者自己能发现，不算隐藏约束。
- 两个期望 FAILED 的键不来自任何公开要求，见 §4(a)。

### 3.3 替代解与可能蒙混的实现（源码推断）

| 候选 | 做法 | 预测 | 违反什么 |
| --- | --- | --- | --- |
| gold | `host=req.netloc` | 1（已实测） | — |
| AL1 | 端口不是该 scheme 的默认端口时才补 `:port` | 1 | 不违反；与 gold 只在 U1 上不同 |
| AL2 | 在 gold 基础上再加 `if not req.ssl:`，只改写明文目标（上游 0.17 的写法） | 1（https 测试不断言 `req.path`） | 不违反；不单独实跑 |
| AL3 | 在 `ClientRequest` 上加实例属性或方法来算绝对 URL | 1 | 不违反。若改成经类名 `ClientRequest.xxx(req)` 调用，公开测试就会失败，解题者看得到 |
| **DG1**（退化） | 只在 `req.port == 1234` 时补 `':1234'` | 1 | 违反 R1 的一般表述：`http://localhost:8080/path` 仍得到 `http://localhost/path` |
| **WR1** | 改 `ClientRequest.update_host`，让 `host` 带端口 | 1 | 违反 R7、R8：直连显式端口时会去连主机串 `'localhost:1234'`；https 经代理时 CONNECT 目标变成 `'www.python.org:8443:8443'`，TLS 的 `server_hostname` 也带上端口（`connector.py:361, 382`）；公开 `test_client.py:343-345` 断言 `host == 'python.org'` |
| WR2 | 在 `_create_connection` 里先做 `req.host = req.netloc`，再格式化（就地改坏输入） | 1 | 与 WR1 同样破坏 CONNECT 目标和 `server_hostname`；R-c 第 2 项能同时挡住，不单独跑 |
| WR3 | 用 `req.headers['HOST']` 拼请求行 | 1 | 违反 R11，只在自定义 Host 头时出错（T3） |
| WR4 | 用 `urlsplit(req.url).netloc` | 1 | 违反 R10：目标 URL 带 `user:pass@` 时凭据会进请求行，也不做 IDNA 编码（T3） |

下面这些做法会被公开测试挡住。解题者看得到，不是隐藏陷阱：

- 总是补端口（`test_connect:341`）。
- 把改写移出 `_create_connection`（与示例用法和 `HT:583-584` 冲突）。
- 直接用 `req.url`（缺尾斜杠，`test_connect:341`）。
- 改代理请求的参数（`test_connect:348-352`）。

## 4. R2E 专项（第 4 步）

**(a) 非 PASSED 的键**

- `HttpClientConnectorTests.test_tcp_connector` 失败于 `TypeError: cannot 'yield from' a coroutine object in a non-coroutine generator`，位置在 `connector.py:290`（`LOG_NOOP:33-84`）。原因：`TCPConnector._create_connection` 没加 `@asyncio.coroutine`，而 py3.9 的 `loop.create_connection` 是原生协程。
- `HttpClientConnectorTests.test_unix_connector` 的失败链：
  1. `UnixConnector._create_connection` 有装饰器，所以连接能建立。
  2. 但 `StreamProtocol.connection_made` 在 py3.9 的 `asyncio.streams.StreamWriter` 里断言失败（`parsers.py:246`；`LOG_NOOP:156-179`），`writer` 一直是 None。
  3. 随后 `send_headers` 抛 `AttributeError: 'NoneType' object has no attribute 'write'`（`protocol.py:650`；`LOG_NOOP:85-154`）。
- **运行一致性**：noop 和 gold 在这两个键上的失败输出逐字相同。把地址和时间戳归一化后做 diff，只剩 connector.py 的 status 行和目标键的差别。3 次 noop、3 次 gold 各自一致；M3 在来源镜像上跑 gold 两次，也是这两个 FAILED。
- **会不会翻转**：正确修复都不碰这条路径，所以不会翻转；这包括 AL2 这类更完整的修复，以及让代理 Host 头带端口的改法。要让它们变成 PASSED，至少得同时移植 `connector.py:274`（装饰器）、`parsers.py:246`（StreamWriter）、`server.py:109` 和 `client.py:512-513`（`create_task(loop=)`），完整清单我没有查。这属于越界工作。
- **最可能出现的顺手改动**：给 `connector.py:274` 加 `@asyncio.coroutine`。解题者照题面示例用真实循环运行时，正好会撞上 290 行的 `TypeError`。静态推断：加了以后，tcp 用例会走到与 unix 用例相同的 `AttributeError`，仍然是 FAILED。这一点由 SC1 实跑确认。
- **判断**：T5，已按来源解释。这两个键是死键：它们既不区分 noop 与 gold，也不提供回归保护，唯一的作用是惩罚越界移植。暂不算 S1；R-a 可选（先例是 v1 §10 的 scrapy `9a15fcf8`）。

**(b) 题面描述的报错是否出现在 noop 目标键的失败里**

是。`LOG_NOOP:200-203` 与 `user_prompt.txt:31, 38` 逐字对应。

**(c) 题面是否泄漏修法**

- 题面没给代码，不是 P1。
- 但修法几乎是直接给出的，只需改一个词：
  - 题面点名了 `ProxyConnector`、`_create_connection` 和 `req.path`。
  - 仓库里只有 `connector.py:342-344` 一处改写。
  - `ClientRequest` 上现成就有 `netloc`，注释写明它记录完整的 netloc（`client.py:232-233`）。
- 题面示例的类名和方法名与隐藏测试相同（`user_prompt.txt:18-19` 对 `HT:292, 571`），等于把唯一的目标断言公开了，这正是 T2c 的成因。
- 题目难度低，训练价值另评。

**(d) 测试辅助、搬迁伪影与撞键**

- **依赖 base 版测试辅助**：
  - 隐藏测试导入 `tests.test_client_functional.Functional`（`HT:17`），依赖工作树里 base 版的 `tests/test_client_functional.py`（`Functional` 从 883 行开始）。
  - 它还依赖 `aiohttp/test_utils.py` 的 `run_server` 和 `run_briefly`。`run_briefly` 在 `ProxyConnectorTests` 和 `HttpClientConnectorTests` 的 tearDown 里调用（`HT:298-303, 253-258`）。
  - 评分时这两个文件都不重置。候选改坏它们，键状态就会变；例如 `run_briefly` 出错会让 ProxyConnectorTests 的 tearDown 失败，状态变成 FAILED 或 ERROR。
  - 提示禁止改测试文件，但 `aiohttp/test_utils.py` 是包内模块，不在"测试文件"的字面范围内。这里只登记依赖，不算缺陷。
- **导入方式**：`tests/` 没有 `__init__.py`，靠 `/testbed` 在 `sys.path` 上、按命名空间包导入。评分时 33 项都正常收集了（`LOG_NOOP:25-28`）。
- **撞键**：只有一个隐藏文件，四个类名互不相同，没有撞键。
- **搬迁伪影**：不依赖 conftest。`/tmp/aiohttp_unix.sock` 是绝对路径，而且 `run_server` 绑定前会先 unlink（`test_utils.py:117-121`）。

**(e) 时间、随机、资源敏感的键**

- `test_get` 用真实的 `time.time()`，但窗口有 30 秒。
- `test_get_expired` 用 `time.time()-1000`。
- `test_release*`、`test_cleanup` 都给时间打了桩。
- 析构类测试依赖 CPython 的引用计数，结果确定。
- 真实 socket 只出现在两个死键里。
- 当前材料的 6 次运行里，键状态完全一致；测试阶段约 1 秒，内存峰值约 171 MB（见账本 `resource`）。
- 没有 E5 疑点。

**(f) 材料修订**

没有。`PRIV/revisions.json` 为 `[]`，`grading_bundle.json` 里 `material_revisions` 也为空。

## 5. gold 与初态（第 5 步）

- **gold 的内容**：只改了 `connector.py:343` 的一个词（`PRIV/gold.patch`），与 `PRIV/validation_bundle.json` 里的 `golden_patch` 一致。M3 账本的 `gold_meta` 显示，上游修复提交还改了 `tests/test_connector.py`，那部分被当作测试剥离了。这与"隐藏测试 = 公开文件 + 新测试"吻合。
- **按公开要求检查 gold**：
  - 修到了题面意图，示例断言能通过。
  - `netloc` 已经剥掉了 `user:pass@`（`client.py:227-230`），也做过 IDNA 编码（221-225），不会引入 R10 的问题。
  - 显式写了默认端口时会保留 `:80`（U1），这是合法写法。
  - 修复对 https 目标同样生效。改写本来就在 `if req.ssl` 之前，这是既有行为，不是回归。
  - 没有无关改动。
- **gold 没修、也不属于本题的既有问题**：
  - https 经代理时仍被改写成绝对形式。
  - 连接池复用时不会调用 `_create_connection`，所以复用连接的请求行仍是源形式（`connector.py:148-157`）。
  - CONNECT 请求的 Host 头不带端口（335 行）。
  - 这些都在题面范围之外，记为未测的旧行为，不算 G1。
- **初态**：
  - 镜像相对 base 改了 `client.py` / `server.py` / `worker.py`，把 `asyncio.async(` 换成了 `asyncio.create_task(`（`runs/env_overnight_20260916/M3/facts/240da1001519/facts/initial.diff`，与 `PUB/worktree_manifest.json:14-23` 的摘要一致）。
  - `connector.py` 没有被改动，gold 可以干净应用（`LOG_GOLD:10`）。
  - 这次替换是 3.9 下能导入的前提，因为 `async` 从 3.7 起是关键字。但替换后仍带着 `loop=` 参数，一旦运行到就会 `TypeError`，这也是端到端路径不可用的原因之一。
- **执行证据（当前材料）**：
  - noop 得 0（32/33，唯一不符的是目标键），共 3 次；gold 得 1（33/33），共 3 次。
  - 它们用的是同一配方 `r2e_derive_v1`（recipe sha256 `0da821a1…`）的两次构建，image 分别是 `0189a61de356…` 和 `2b75db7b16ca…`；grader profile 为 `1bb8e0cf…`。
  - 两者的测试退出码都是 1（因为有两个死键），得分由逐键映射决定。
  - M3 独立 runner 在来源镜像上跑 gold 两次，都是 31 passed / 2 failed。
  - 新机器重建的镜像还没有运行记录。
- **证据层次**：上面的失败位置和状态是执行证据；§3.3 和 §4(a) 里的候选预测是源码推断。

## 6. 开发需求（第 6 步）

| 项 | 需求 | 依据 | 证据级别 |
| --- | --- | --- | --- |
| 导入 | 在 `/testbed` 下用 `python -c` / `python -m pytest`，或设 `PYTHONPATH=/testbed` | `environment_brief.md:13`；账本 `RH2_OBS_IMPORT_PATH=/testbed/aiohttp/__init__.py` | 镜像层面实测（grader 侧）；actor 待验 |
| 依赖 | 只用现有 venv：Python 3.9.21、pytest 8.3.4、pytest-mock / asyncio / cov；标准库 `unittest.mock` 就够用 | `LOG_NOOP:24-27`；`environment_brief.md:10-11` | grader 实测；actor 待验 |
| 资产 | 不需要，相关测试全用 mock | 公开 `test_connector.py:292-568` | 源码 |
| 权限 | agent（54321）写 `/testbed`；评分身份是 54322 | `environment_brief.md:12`；账本 `policy` | 描述加 grader 实测；actor 待验 |
| 网络 | 各阶段都不需要；grader 为 `deny_all` | 账本 `policy.network` | grader 实测 |
| 构建 | 不需要（纯 Python，`setup.py` 没有扩展模块） | `WT/setup.py` | 源码 |
| 提交边界 | 改 `aiohttp/connector.py` 或 `client.py`，都是非测试文件；正式导出按字节差异，gold 的投影只含 `aiohttp/connector.py` | gold 账本 `projection.included_paths` | grader 实测；actor 侧导出待验 |
| 最小公开验证 | `CMDS` 里的 `repro_port_mocked`（能区分修复前后）和 `public_proxy_tests` | `PR` §4 | 待 devcheck |
| 初态注意 | 不要回退那三处初态改动。回退成 `asyncio.async(` 在 3.9 是 SyntaxError，整个包导入失败，所有键出错，得 0。这是候选自己把代码改坏，判 0 是对的，不是误拒 | `initial.diff` | 源码推断 |
| 与本题无关的恒失败 | 公开 `tests/test_connector.py` 里的两个端到端用例；`tests/test_client.py`、`tests/test_worker.py` 不能收集 | `LOG_NOOP`；`PR` §3.5 | 前者 grader 实测；后者待 devcheck |
| 答案可达 | 来源镜像的 `.git` 能访问到修复提交（M3 账本 `facts.fix_reachable=commit`、`commits_after_head=11410`）。派生镜像按环境卡 §1 清掉了修复提交，预检会查 HEAD 没有子提交。本题的特殊之处：上游此后所有版本都含这个修复（§7），只要残留任何未来对象，答案就会暴露 | 环境卡 §1–2 | 共享机制；本题以 devcheck 预检结果为准 |

## 7. 题目关系（第 8 方面）

- **本题修复被别题包含**：
  - `618335186f22`（base `ff3dec42`，0.17.0a0）的公开工作树里，`aiohttp/connector.py:597-600` 有 `if not req.ssl:` 加 `host=req.netloc`；`tests/test_connector.py:1063-1080` 有同一个 `test_request_port`（只多了 `loop=` 参数）。
  - 这与 `cross_task_gold_scan.json` 的条目一致：gold 新增 1 行，命中 1 行。
  - 含义：训练 618 这道题会暴露本题答案；按仓库划分（v1 D3）时，两题必须同组。
- **同名的后代测试**：
  - `cross_task_test_scan.json` 还列了三道题：`1c1c0ea3`（3.10.6.dev0，`tests/test_proxy.py:701`）、`22a12cc2`（3.11.0.dev0，`test_proxy.py:702`）、`4075c653`（3.9.0b0，`test_proxy.py:601`）。
  - 我打开了 `4075c653` 和 `1c1c0ea3` 的公开测试。它们都是用同一 URL `http://localhost:1234/path` 的后代测试，但代码已经大幅重构（改用 yarl URL，`TCPConnector` 内建代理），不含本题代码层面的修复。
  - 属于弱关联，登记即可。
- **反向命中**：
  - 扫描称 `618335186f22` 的 gold（1 行）逐字出现在本题的公开工作树里。
  - 该题讲的是 deflate 分块压缩（见其公开 `user_prompt.txt`），与本题无关。本题 base 比它早好几个版本，不可能包含它的"修复"，除非那一行是通用代码，或者它的修复恢复的正是旧代码。
  - 我没读该题的私有包，具体是哪一行没有核对；这不影响本题。
- 两份扫描都只比逐字的行和函数名，结果只是下限。

## 8. v1 §4 严重度五步（初判）与问题登记

| 步 | 结论 | 证据 |
| --- | --- | --- |
| 1 核心要求有没有直接断言？ | 有（`HT:584`） | — |
| 2 核心断言是否只用了示例字面值？ | **是 → S1（T2c）** | `HT:570-584` 对照 `user_prompt.txt:18-24, 29-31`；其余目标请求的 URL 都不带显式端口（`HT:326, 369, 395, 433, 460, 487, 515, 541, 566`） |
| 3 退化探测 | DG1 预测得 1，待实跑；得 1 即 T2b | §9 |
| 4 已有候选 | 没有真实模型候选。构造的 WR1 预测得 1，待实跑；得 1 即 S1，因为 https 显式端口是同一核心要求的另一个实例，直连显式端口和 `test_host_port` 属于有文档的常用行为。WR3 / WR4 只影响边缘输入，记 T3 | §3.3、§9 |
| 5 | 不适用（第 2 步已命中） | — |

| 编号 | 内容 | 严重度 / 去向 | 证据层次 |
| --- | --- | --- | --- |
| T2c | 唯一的目标断言就是题面示例 | S1 → R-c 第 1 项 | 测试文本（静态）；noop/gold 执行 |
| T2b（待定） | 退化候选 DG1 | 得 1 即 S1，由同一个 R-c 修 | 源码推断，待评分 |
| 第 4 步 S1（待定） | WR1 / WR2 这一类：有显式端口时破坏 host/port 语义 | 得 1 → R-c 第 2 项 | 源码推断，待评分 |
| T5 | 两个期望 FAILED 的死键 | 已解释；R-a 可选 | 执行（RH2 6 次 + M3 2 次） |
| P4 | 题面示例原样不能运行：顶层没有 `ClientRequest`；真实循环在 3.9 下撞上 `TypeError`；也没有网络 | 登记；替代复现是 `CMDS` 的 `repro_port_mocked` | 静态加评分侧旁证；actor 待 devcheck |
| T3 | R9、R10、R11 没有断言 | 登记 | 静态 |
| X1 | `618335186f22` 的初态含本题修复与测试；三道 3.x 题含后代测试 | 登记；按仓库划分 | 公开包实读 |
| 环境（不是缺陷） | 端到端 socket 路径在 3.9 下不可用；`test_client.py`、`test_worker.py` 不能收集；初态脏树不能回退 | 登记。这限制了解题者自查的范围，例如 R8 对应的公开测试跑不了 | grader 执行加源码 |

## 9. 请协调者实跑（第二步）

**9.0 基线**：在重建的派生镜像上，gold 和 noop 各跑 1 次，记录 image ID / RepoDigests、配方哈希和 profile 摘要。预期与 §5 相同：noop 得 0（只有目标键不符），gold 得 1。

**9.1 正式评分候选**：只列能区分结论的几个。补丁全文见附录 B；每个都已在 base 文件副本上通过 `git apply --check`，改后的文件也能正常解析。

| ID | 位置 | 改法 | 预期（当前材料） | 预期不符的键 | 结果怎样改变判断 |
| --- | --- | --- | --- | --- | --- |
| DG1（第 3 步退化候选） | `aiohttp/connector.py` 的 `ProxyConnector._create_connection`，343 行 | `host=req.host,` 改为 `host=req.host + (':1234' if req.port == 1234 else ''),` | 1 | 无 | 得 1 → T2b；R-c 后应为 0 |
| WR1 | `aiohttp/client.py` 的 `ClientRequest.update_host`，251 行 | `self.host = netloc` 改为 `self.host = self.netloc`；connector.py 不动 | 1 | 无 | 得 1 → 第 4 步 S1，做 R-c 第 2 项 |
| AL1（替代正对照） | `connector.py` 342-344 行 | 端口等于该 scheme 的默认端口（ssl 时 443，否则 80）时用 `req.host`，否则用 `'{}:{}'.format(req.host, req.port)` | 1 | 无 | 得 0 说明有误拒，需要查；R-c 验收时它必须仍为 1 |
| SC1（可选） | gold 加上：在 `connector.py` 274 行前加 `@asyncio.coroutine` | — | 1 | 无（`test_tcp_connector` 仍是 FAILED，失败原因预计变成 `protocol.py:650` 的 `AttributeError`） | 若得 0（该键变成 PASSED 或别的状态），说明死键会惩罚合理的顺手改动，R-a 改为必做 |

**DG1 违反什么、怎么看出来**：它违反 `user_prompt.txt:9` 的一般表述，即带显式端口的 URL 不应丢掉端口。输入 `http://localhost:8080/path` 或 `http://www.python.org:8080/some/path` 时，DG1 给出的结果仍然不带端口，正是题面 Actual Behavior 描述的症状。源码推导：DG1 只在 `req.port == 1234` 时才补后缀。

**WR1 违反什么**：

- 公开 `test_client.py:343-345` 断言 `https://python.org:960/` 的 `host` 应为 `python.org`。
- 直连 `TCPConnector` 请求 `http://localhost:1234/path` 时，会去连主机串 `'localhost:1234'`（`connector.py:285, 290-291`）。
- https 经代理且带显式端口时，CONNECT 目标变成 `'www.python.org:8443:8443'`（361 行），TLS 的 `server_hostname` 也带上端口（382 行）。

**每次评分请核对**：补丁确实已应用（APPLY_RC=0，投影的 `included_paths` 含改动文件）；33 个键全部解析出来；目标键确实执行了（日志里有它的 PASSED / FAILED 行）。

**9.2 私有行为对照**：不评分，只作违例证据，不进解题者材料。在应用候选后的容器里，于 `/testbed` 运行：

```bash
cd /testbed && python -B - <<'EOF'
import asyncio
from unittest import mock
import aiohttp
from aiohttp.client import ClientRequest
loop = asyncio.new_event_loop()
lm = mock.Mock()
done = asyncio.Future(loop=loop)
done.set_result((mock.Mock(), mock.Mock()))
lm.create_connection.return_value = done
proxy = aiohttp.ProxyConnector("http://proxy.example.com", loop=lm)
bad = 0
cases = [
    ("http://localhost:1234/path", "http://localhost:1234/path", "localhost", 1234),
    ("http://www.python.org:8080/some/path", "http://www.python.org:8080/some/path", "www.python.org", 8080),
    ("http://localhost:8080/path?q=1", "http://localhost:8080/path?q=1", "localhost", 8080),
    ("http://www.python.org", "http://www.python.org/", "www.python.org", 80),
]
for url, want_path, want_host, want_port in cases:
    req = ClientRequest("GET", url)
    loop.run_until_complete(proxy.connect(req))
    got = (req.path, req.host, req.port)
    ok = got == (want_path, want_host, want_port)
    bad += not ok
    print("OK " if ok else "BAD", url, "->", got)
direct = aiohttp.TCPConnector(loop=lm)
lm.create_connection.reset_mock()
loop.run_until_complete(direct.connect(ClientRequest("GET", "http://localhost:1234/path")))
target = lm.create_connection.call_args[0][1:3]
ok = target == ("localhost", 1234)
bad += not ok
print("OK " if ok else "BAD", "direct TCPConnector target", target)
raise SystemExit(1 if bad else 0)
EOF
```

预期结果：

- base：退出 1，前三个 URL 报 BAD。
- gold / AL1 / SC1：退出 0。
- DG1：第 2、3 个 URL 报 BAD。
- WR1：前三个 URL 因 host 报 BAD，最后的 direct 行也报 BAD。

**9.3 devcheck 关注点**（`CMDS` 原样执行）：

- `repro_port_mocked` 在 base 上应退出 1，私有 gold 对照应退出 0。
- `public_proxy_tests` 应为 13 passed。
- `public_connector_file` 应为 30 passed / 2 failed（就是那两个死键）。
- `public_client_file_collect` 应在收集阶段失败，退出码 2。
- `literal_example_probe` 应显示 `ImportError` 和 `TypeError`，以此证实 P4。
- 另外记录：每条命令的墙钟时间、R2E 预检三项、`git status` 显示的脏树。

## 10. 修订建议草案（v1 §5；定稿写进 card.md）

### R-c 第 1 项（S1-T2c，必做）

- **公开依据**：`user_prompt.txt:9`（"a URL that includes a specific port"，一般表述）和 29-31 行。
- **改动**：在 `r2e_tests/test_1.py` 的 `ProxyConnectorTests` 末尾加：

```python
    @unittest.mock.patch('aiohttp.connector.ClientRequest')
    def test_request_port_other_url(self, ClientRequestMock):
        proxy_req = ClientRequest('GET', 'http://proxy.example.com')
        ClientRequestMock.return_value = proxy_req

        loop_mock = unittest.mock.Mock()
        connector = aiohttp.ProxyConnector('http://proxy.example.com',
                                           loop=loop_mock)

        tr, proto = unittest.mock.Mock(), unittest.mock.Mock()
        self._fake_coroutine(loop_mock.create_connection, (tr, proto))

        req = ClientRequest('GET', 'http://www.python.org:8080/some/path')
        self.loop.run_until_complete(connector.connect(req))
        self.assertEqual(req.path, 'http://www.python.org:8080/some/path')
```

  同时在 `expected_output.json` 加 `"ProxyConnectorTests.test_request_port_other_url": "PASSED"`。
- **设计说明**：这个实例换了主机、端口和路径，并走公开入口 `connect()`；`test_connect` 已经用同一入口断言过 `req.path`。
- **刻意不测**：显式默认端口（U1）、https 的 `req.path`（U2）、代理请求的 Host 头（U3），因为这几处两种写法都合理。
- **验收**：gold 1；AL1 1；noop 0；DG1 0（新键 FAILED）；键集严格相等（34 键）；Codex 复核。

### R-c 第 2 项（WR1 得 1 时做）

- **公开依据**：
  - 公开 `test_connector.py:468-493`：CONNECT 目标是 `host:port`；对应源码 `connector.py:354-361`。
  - 题面说请求要发往带指定端口的地址（`user_prompt.txt:9`）。
  - 可以另外引用公开 `test_client.py:332-346`。
- **改动**：在 `ProxyConnectorTests` 加：

```python
    @unittest.mock.patch('aiohttp.connector.ClientRequest')
    def test_https_connect_port(self, ClientRequestMock):
        loop_mock = unittest.mock.Mock()
        proxy_req = ClientRequest('GET', 'http://proxy.example.com',
                                  loop=loop_mock)
        ClientRequestMock.return_value = proxy_req

        proxy_resp = ClientResponse('get', 'http://proxy.example.com')
        proxy_req.send = send_mock = unittest.mock.Mock()
        send_mock.return_value = proxy_resp
        proxy_resp.start = start_mock = unittest.mock.Mock()
        self._fake_coroutine(start_mock, unittest.mock.Mock(status=200))

        connector = aiohttp.ProxyConnector(
            'http://proxy.example.com', loop=loop_mock)

        tr, proto = unittest.mock.Mock(), unittest.mock.Mock()
        self._fake_coroutine(loop_mock.create_connection, (tr, proto))

        req = ClientRequest('GET', 'https://www.python.org:8443')
        self.loop.run_until_complete(connector._create_connection(req))

        self.assertEqual(proxy_req.method, 'CONNECT')
        self.assertEqual(proxy_req.path, 'www.python.org:8443')
```

  同时在 expected 加 `"ProxyConnectorTests.test_https_connect_port": "PASSED"`。这是回归断言，noop 在这一键上也会通过，但不影响 noop 总分为 0。
- **备选**：把公开的 `ClientRequestTests.test_host_port`（`test_client.py:332-346`）原样搬进隐藏测试，换一个不撞键的类名。它只能挡住 WR1，挡不住 WR2，所以优先用上面的行为断言。
- **验收**：gold 1；AL1 1；noop 0；WR1 0；DG1 0；Codex 复核。

### R-a（可选；SC1 得 0，或真实候选让死键翻转时改为必做）

- **依据**：这两个键在 noop 和 gold 上都因同一个 py3.9 不兼容而失败（§4(a)），不来自任何公开要求。
- **改动**：删掉 `HT:247-289` 的 `HttpClientConnectorTests`，以及 expected 里对应的两个键。可以顺手删掉只为它服务的 `from tests.test_client_functional import Functional`（`HT:17`），减少对 base 测试辅助的依赖。
- **验收**：gold 1；noop 0；没有 unexpected 键；SC1 仍为 1。

## 11. 八方面覆盖与阅读范围

| 方面 | 已查 | 未查 / 缺口 |
| --- | --- | --- |
| 公开需求 | 题面、提示、环境说明、`docs/client.rst` 的代理一节、`CHANGES.txt` 顶部、公开测试（connector 的全部，client 的 host / port 部分） | 模型实际收到的消息 |
| 材料与初始问题 | 各原件的哈希与字段一致；noop 的失败位置与题面一致；初态 diff 已读 | — |
| 测试是否测到要求 | 目标键全程追到源码；回归键按组读了断言 | `BaseConnector` 的分支没有逐条追 |
| 是否误拒合理解 | 没有只在隐藏测试里的约束；AL1–AL3 预测得 1 | AL1 待实跑 |
| 回归与 gold | gold 正确且最小；发现 WR1 这一类缺口 | WR1 待实跑 |
| agent 开发条件 | 环境说明加 grader 侧事实 | actor 侧全部待 devcheck |
| 交付与评分边界 | 投影；`run_tests.sh` 按 `RH2_SETUP_ENTRY_SHA256` 恢复；base 测试辅助不重置 | 共享控制面（根目录 conftest、parser）没有逐题复审 |
| 题目关系与用途 | 两份扫描逐条核对；打开了 3 道他题的公开包 | 反向单行命中的具体是哪一行 |

**40 项清单预映射**（供 screening_record 用）：

- pass：1、2、9、11、13、14、16（grader 侧）、17（附依赖登记）、18、19、20、21、22、24、27。
- issue：5（X1）、23（P4）、25 和 32（T2c）。
- unknown：26（看 WR1）；3、6、7、8、10、29（actor 待验）。
- not_checked：31（共享机制）。

**实际读过的材料**：

- 角色卡和五份方法文档；`PR`、`CMDS`。
- 公开包：全部元数据文件。`WT` 下读了：
  - 源码：`connector.py` 全文，`client.py` 相关段，`__init__.py`，`parsers.py:230-255`，`test_utils.py:1-130`。
  - 测试：`tests/test_connector.py` 全文，`test_client.py:296-372`（外加 grep），`test_client_functional.py:1-30` 和 883 行起的部分。
  - 其它：`install.sh`、`process_aiohttp_updateasyncio.py`、`run_tests.sh`、`setup.cfg`、`.gitignore`、`docs/client.rst:295-340`、`CHANGES.txt:1-30`。
- 私有包的全部文件。
- 运行原件：
  - `run_refs.json` 指向的 6 份评分日志：noop 和 gold 读了全文，其余 4 份归一化后与它们逐行 diff。
  - 6 行账本。
  - M3 账本第 8 行与 a1 日志；a2 日志只核了哈希。
  - M3 的 `initial.diff`。
- 两份跨题扫描中涉及本题的条目。
- 他题公开包：
  - 618335186f22：`user_prompt.txt`、`connector.py:585-610`、`test_connector.py:1055-1085`。
  - 4075c653：`test_proxy.py:595-625`。
  - 1c1c0ea3：`test_proxy.py:698-730`。
  - 五道 aiohttp 题的 base 与版本号。

**没读**：任何 history、审查目录、本批的 README / board / assignments、他题私有包，以及 runs/ 下的分析汇总文件。会话启动时自动载入的本机说明里出现过本题 ID（09-24 为"核对脏树"拉取镜像的清理记录），其中不含任何结论，本文没有使用。

## 附录 A：证据索引

| 运行 | 账本行 | 候选 | image | 得分 | 匹配 | 日志 sha256（与 `run_refs.json` 一致） |
| --- | --- | --- | --- | --- | --- | --- |
| R-f 全池 | `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:3` | noop | `0189a61de356…` | 0 | 32/33（`test_request_port`） | `a6a94ef0…` |
| R-f 全池 | `…/ledger_r2e_all_gold.jsonl:3` | gold | `0189a61de356…` | 1 | 33/33 | `71a147e6…` |
| R-f 重复 | `…/ledger_r2e_reps_noop.jsonl:3` | noop | `2b75db7b16ca…` | 0 | 32/33 | `43dd21c2…` |
| R-f 重复 | `…/ledger_r2e_reps_gold.jsonl:3` | gold | `2b75db7b16ca…` | 1 | 33/33 | `9fb35878…` |
| 环境轮复跑 | `runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl:3` | noop | `0189a61de356…` | 0 | 32/33 | `05e432de…` |
| 环境轮复跑 | `…/_rerun2/ledger_gold.jsonl:3` | gold | `0189a61de356…` | 1 | 33/33 | `e7bea783…` |
| M3 来源镜像 | `runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:8`、`:55` | gold | 来源 `bb629a91…` | 1 | 31 passed / 2 failed | `1f4fcecc…`、`b5d991f7…` |

以上各行的配方都是 `r2e_derive_v1`（`0da821a1…`），profile 都是 `1bb8e0cf…`（2 CPU / 4 GiB / `/tmp` 1 GiB / `deny_all` / uid 54322）。M3 那一行除外，它用的是来源镜像和独立 runner。

## 附录 B：候选补丁全文（相对 base；空的上下文行是单个空格）

DG1：

```diff
diff --git a/aiohttp/connector.py b/aiohttp/connector.py
--- a/aiohttp/connector.py
+++ b/aiohttp/connector.py
@@ -340,7 +340,7 @@ class ProxyConnector(TCPConnector):
         except OSError as exc:
             raise ProxyConnectionError(*exc.args) from exc
         req.path = '{scheme}://{host}{path}'.format(scheme=req.scheme,
-                                                    host=req.host,
+                                                    host=req.host + (':1234' if req.port == 1234 else ''),
                                                     path=req.path)
         if 'AUTHORIZATION' in proxy_req.headers:
             auth = proxy_req.headers['AUTHORIZATION']
```

WR1：

```diff
diff --git a/aiohttp/client.py b/aiohttp/client.py
--- a/aiohttp/client.py
+++ b/aiohttp/client.py
@@ -248,7 +248,7 @@ class ClientRequest:
                 self.port = HTTP_PORT
 
         self.scheme = scheme
-        self.host = netloc
+        self.host = self.netloc
 
     def update_version(self, version):
         """Convert request version to two elements tuple.
```

AL1：

```diff
diff --git a/aiohttp/connector.py b/aiohttp/connector.py
--- a/aiohttp/connector.py
+++ b/aiohttp/connector.py
@@ -339,8 +339,11 @@ class ProxyConnector(TCPConnector):
             transport, proto = yield from super()._create_connection(proxy_req)
         except OSError as exc:
             raise ProxyConnectionError(*exc.args) from exc
+        default_port = 443 if req.ssl else 80
+        host = (req.host if req.port == default_port
+                else '{}:{}'.format(req.host, req.port))
         req.path = '{scheme}://{host}{path}'.format(scheme=req.scheme,
-                                                    host=req.host,
+                                                    host=host,
                                                     path=req.path)
         if 'AUTHORIZATION' in proxy_req.headers:
             auth = proxy_req.headers['AUTHORIZATION']
```

SC1（gold 加上装饰器）：

```diff
diff --git a/aiohttp/connector.py b/aiohttp/connector.py
--- a/aiohttp/connector.py
+++ b/aiohttp/connector.py
@@ -271,6 +271,7 @@ class TCPConnector(BaseConnector):
             return [{'hostname': host, 'host': host, 'port': port,
                      'family': self._family, 'proto': 0, 'flags': 0}]
 
+    @asyncio.coroutine
     def _create_connection(self, req, **kwargs):
         """Create connection.
 
@@ -340,7 +341,7 @@ class ProxyConnector(TCPConnector):
         except OSError as exc:
             raise ProxyConnectionError(*exc.args) from exc
         req.path = '{scheme}://{host}{path}'.format(scheme=req.scheme,
-                                                    host=req.host,
+                                                    host=req.netloc,
                                                     path=req.path)
         if 'AUTHORIZATION' in proxy_req.headers:
             auth = proxy_req.headers['AUTHORIZATION']
```
