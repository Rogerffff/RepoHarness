# 公开读者记录：aiohttp__240da100151933883d7dea0528d45877df025b92

- 角色：R2E 公开读者（`roles/public_reader_r2e.md`），2026-09-29，单题、干净上下文。
- 材料：`PUBLIC_DIR = runs/r2e_static_prep_20260924/v3/public/aiohttp__240da100151933883d7dea0528d45877df025b92`。下文路径都相对 `PUBLIC_DIR`；`worktree/…` 就是解题者看到的 `/testbed/…`。
- 性质：全部是静态阅读。凡涉及 Python 3.9 运行行为的判断，都是按源码和 CPython 3.9 语义推断，未执行。命令一律"建议，未执行"，机器可读版本在同目录 `commands.json`。
- 题目：base `ef756ce29cc4`（aiohttp `0.9.1dev`，`worktree/aiohttp/__init__.py:3`）。`ProxyConnector` 把目标请求改写成绝对形式 URL 时丢了端口。

## 0. `public_hints` 分类（`public_bundle.json:15`）

| 类别 | 内容 | 对合法解法的影响 |
| --- | --- | --- |
| 题目需求 | 修一个真实 issue；找根因，只改非测试源码 | 修复落在 `aiohttp/connector.py`（必要时加上 `aiohttp/client.py`），不冲突 |
| 给解题者的操作指令 | 不改仓库测试文件；测试跑窄（单文件或单模块）；在 `/testbed` 用 `python -m pytest`；确信修好后简短总结并停止 | 不冲突。相关公开测试集中在一个类 `tests/test_connector.py::ProxyConnectorTests`，符合"跑窄"。想加回归用例只能写到 `/tmp` 脚本里 |
| 环境事实声明 | `.venv` 已就绪，`python` 和测试工具都指向它；无网络；`pip` 可能没有；由另一组测试评判 | 与 `environment_brief.md:10-13` 一致，后者更具体：包没装进 venv，要靠 cwd 在 `sys.path` 上才能导入；裸 `pytest` 收集会失败。提示里"测试工具已指向 venv"与"裸 `pytest` 不可用"有轻微张力，但提示本身也要求用 `python -m pytest`，不影响解题。本题不需要网络或新包，因为公开测试本来就 mock 了代理连接 |

`user_prompt.txt` 只含题面，不含上述提示（`environment_brief.md:3-4`）。

## 1. 需求表

| 编号 | 行为 | 改变 / 保留 | 依据类型 | 依据 |
| --- | --- | --- | --- | --- |
| R1 | 明文 http 目标经 `ProxyConnector._create_connection(req)` 成功返回后，`req.path` 应为含端口的绝对形式 `http://localhost:1234/path`；base 得到的是 `http://localhost/path` | 改变 | 明示 | `user_prompt.txt:22-24, 27-39`。根因：`worktree/aiohttp/connector.py:342-344` 用 `req.host` 拼接，而 `req.host` 不含端口（`worktree/aiohttp/client.py:237-251`） |
| R2 | 改写要在 `_create_connection` 内部生效，因为题面直接调 `_create_connection`，然后读 `req.path` | 保留（位置约束） | 明示（示例用法） | `user_prompt.txt:23-24`；base 的改写点 `connector.py:342` 本来就在这里 |
| R3 | URL 不带端口时结果仍是 `http://www.python.org/`，不补 `:80` | 保留 | 公开测试 | `worktree/tests/test_connector.py:326-341, 395-400, 433-438` |
| R4 | 连代理失败（`OSError` 转成 `ProxyConnectionError`）时，`req.path` 和 `req.headers` 不变 | 保留 | 公开测试 + 代码顺序 | `test_connector.py:363-374, 448-466`；`connector.py:338-344` |
| R5 | 代理认证：`proxy_req` 上的 `AUTHORIZATION` 移到 `req` 上，改名为 `PROXY-AUTHORIZATION` | 保留 | 公开测试 | `connector.py:345-348`；`test_connector.py:376-409, 417-446` |
| R6 | 代理请求的构造调用保持原样：`ClientRequest('GET', proxy, auth=…, headers={'Host': req.host}, loop=…)`。对无端口 URL，测试精确断言 `headers={'Host': 'www.python.org'}` | 保留 | 公开测试 | `connector.py:333-337`；`test_connector.py:348-352, 406-409, 444-446` |
| R7 | HTTPS 目标走 `CONNECT`：`proxy_req.path == 'www.python.org:443'`（本来就带端口）；非 200 抛 `HttpProxyError`；transport 不暴露 socket 时抛 `RuntimeError`；`start` 的异常原样透传 | 保留 | 公开测试 | `connector.py:350-382`；`test_connector.py:468-568` |
| R8 | `ClientRequest.host` 不含端口，`port` 是 int，`HOST` 头逐字等于 netloc（显式写的 `:80` 也保留） | 保留 | 公开代码 + 公开测试（该测试文件在 3.9 下预计无法收集，见 §3.5） | `client.py:232-251, 312-314`；`worktree/tests/test_client.py:332-346, 352-368`。连接池 key 和主机解析也依赖这一语义：`connector.py:143, 285` |
| R9 | 查询串随 `req.path` 一起保留，包括 `params=` 合并进来的部分 | 保留 | 可从代码推知 | `client.py:268-294`；base 的拼接串已经保留 path 和 query |
| R10 | URL 里的 `user:pass@` 不进入请求行 | 保留 | 可从代码推知 | `client.py:227-233`：`netloc` 已剥掉 userinfo，并转成 `AUTHORIZATION` 头 |

仍有多种合理解释（题面和公开测试都没覆盖）：

- **U1**：URL 显式写了默认端口（`http://host:80/p`、`https://host:443/p`）时，改写结果保留还是省略端口。现有 `HOST` 头的约定是逐字保留 netloc（`test_client.py:356-357`），但那是 Host 头，不是请求行。两种写法都是合法且等价的绝对 URI。
- **U2**：题面只举了 http。https 目标同样经过这行改写（改写在 `if req.ssl` 之前，`connector.py:342-350`），修复是否一并作用于 https 没有约定。自然的改法会一起生效；公开测试不断言 https 请求的 `req.path`。
- **U3**：代理请求的 `Host` 头（`connector.py:335` 用 `req.host`，只在 `CONNECT` 时真正发出）要不要带端口。题面没提；公开测试只约束了无端口的情形。
- **U4**：题面示例从 `aiohttp` 顶层导入 `ClientRequest`，但 base 不导出它（§3.3）。题面的 Expected/Actual 只谈 `req.path`，没有要求新增导出；公开测试都从 `aiohttp.client` 导入。

## 2. 合理实现范围

以下实现都应接受。它们在题面例子和全部公开测试上结果相同，只在 U1 上有差别：

- 拼绝对 URL 时用 `req.netloc` 代替 `req.host`。显式端口逐字保留，显式写的默认端口也保留。
- 仍用 `req.host`，只在 `req.port` 不是该 scheme 默认端口（`client.py:28-29` 的 80/443）时追加 `:port`。
- 在 `ClientRequest` 上加辅助属性或方法来算绝对 URL，再由 `ProxyConnector._create_connection` 调用；也可以直接在 connector 里内联格式化。命名没有约定。

以下做法不可接受，或按公开材料有明确风险：

- 总是追加端口：无端口 URL 会变成 `http://www.python.org:80/`，违反 R3。
- 把改写挪到 `BaseConnector.connect`、`request()` 或 `ClientRequest.send()`：违反 R2。
- 直接用原始 `req.url` 重建：可能把 `user:pass@` 带进请求行（违反 R10），并丢掉 `params=` 合并进 `req.path` 的查询串（违反 R9）。
- 改 `ClientRequest.host` 的语义，让它含端口：违反 R8，会连带破坏连接池 key、`_resolve_host`、`HOST` 头以及 `test_client.py:332-346`。
- 在 `connector.py` 里通过 `ClientRequest` 这个名字读类属性或调类方法：公开测试会把 `aiohttp.connector.ClientRequest` 替换成 `MagicMock`（`test_connector.py:324, 376, 417, 448, 468, 495, 520, 546`），那时读到的是 mock。读 `req` 实例的属性不受影响。
- 改动代理 `ClientRequest(...)` 构造调用的参数（增删关键字参数、让 `Host` 总带端口）：违反 R6 的精确断言。

输出只有一个明确约定，即题面给出的字符串；没有新 API 的命名要求，也没有约定默认端口怎么处理。这里不给"标准写法"。U1–U4 是否被评分测试钉住，公开材料无从得知。

## 3. 题面质量与初态线索

### 3.1 题面是否给出或强烈暗示了修法

题面没有给修复代码，示例也不是修好后的实现。但它点名了 `ProxyConnector`、`_create_connection` 和 `req.path`，而仓库里改写 `req.path` 的只有 `connector.py:342-344` 一处，所以位置几乎是直接给出的，修改量可能只有一行。本题的难点主要在于不破坏 R3–R8。

### 3.2 题面描述的行为能否从 base 源码读出

能。以 `'http://localhost:1234/path'` 为例：

1. `update_host` 得到 `host='localhost'`、`port=1234`、`netloc='localhost:1234'`（`client.py:233-251`）。
2. `update_path` 得到 `path='/path'`（`client.py:293-294`）。
3. `connector.py:342-344` 拼出 `'http://localhost/path'`，与 `user_prompt.txt:36-39` 一致。
4. `send()` 把 `self.path` 直接用作请求行（`client.py:498`）。

与此同时，同一请求的 `HOST` 头是 `localhost:1234`（`client.py:312-314`），所以 base 发给代理的请求是"请求行无端口、Host 头有端口"。按一般 HTTP 代理语义（这是背景知识，不来自本包材料），代理以绝对形式请求行里的主机和端口为准，因此会转发到 80 端口。这与题面"发到了错误的 URL"（`user_prompt.txt:9`）相符。

### 3.3 题面示例在 base 接口下说不通的地方

- `user_prompt.txt:16` 的 `from aiohttp import ProxyConnector, ClientRequest` 在 base 上会抛 `ImportError`。原因：`client.py:3` 的 `__all__` 只有 `request` 和 `HttpClient`，`aiohttp/__init__.py:6-12` 只做星号导入，其它子模块的 `__all__` 也不含 `ClientRequest`。公开测试都写成 `from aiohttp.client import ClientRequest`（`test_connector.py:14`、`test_client.py:13`）。
- `user_prompt.txt:20-23` 用真实事件循环直接调私有的 `_create_connection`，会真的去连 `proxy.example.com`。预计在 Python 3.9 下先抛 `TypeError`：`TCPConnector._create_connection`（`connector.py:274-298`）没加 `@asyncio.coroutine`，是普通生成器，却对 3.9 的原生协程 `loop.create_connection` 做 `yield from`（静态推断）。即使绕过这一点，无网环境里也只会得到 `ProxyConnectionError`（`connector.py:338-341`）。两种情况都执行不到 `print(req.path)`，修复前后输出相同。
- 因此这个示例只能当"意图说明"，不能原样复现。要区分修复前后，必须像公开测试那样 mock 掉代理连接（`test_connector.py:305-312, 329-339`）。另外，示例写成了 `TestCase`，却只 `print` 不断言，这是小问题。
- 如果评分测试真按示例从顶层导入 `ClientRequest`，那么只改 `req.path` 的正确修复也会在导入阶段失败。公开材料无法排除这种可能，列为关键未知（U4）。

### 3.4 调查入口与缺失信息

- 题面加上 `connector.py:331-384` 就足以定位。`ProxyConnectorTests` 提供了现成的 mock 模板。不需要网络、真代理或新依赖。
- 可能真正影响"合法解能否通过"的缺失信息只有 U1 和 U4，其次是 U2、U3。其余内容（`host`/`port`/`netloc` 的含义、改写时机、认证头迁移）读 `client.py` 和现有测试就能得到，不算题面缺陷。

### 3.5 初态线索

以下都不是本题的修复内容，但会影响开发和验证：

- **镜像初态改动来自一个替换脚本。** `worktree_manifest.json:14-23` 列出的改动文件是 `client.py`、`server.py`、`worker.py`，来源是 `process_aiohttp_updateasyncio.py:9, 30`：它把 `aiohttp/` 下的 `asyncio.async(` 换成了 `asyncio.create_task(`。替换后仍带 `loop=` 参数（`client.py:140, 512-513`、`server.py:109`、`worker.py:29`），而 3.9 的 `asyncio.create_task` 不接受 `loop`。所以真实发送请求（`ClientRequest.send`）和服务端处理预计都会抛 `TypeError`（静态推断）。再加上 §3.3 里 `TCPConnector._create_connection` 的问题，在这个环境里经真实 socket 做端到端验证基本不可行；本题也不需要这样验证。
- **同文件里有与本题无关的既有失败。** 出于同样原因，`tests/test_connector.py` 里走真实 socket 的 `HttpClientConnectorTests`（`test_connector.py:247-289`，含 `test_tcp_connector`、`test_unix_connector`）在 base 上可能就会失败。验证时只看 `ProxyConnectorTests`。顺手修这些兼容问题属于范围外改动。
- **两个测试文件预计无法收集。** 转换脚本只处理了 `aiohttp/`，`tests/test_client.py:647, 682, 701` 和 `tests/test_worker.py:46, 97` 里仍有 `asyncio.async`，这在 3.7+ 是语法错误。因此 `ClientRequest` 的 host/port/Host 头测试（`test_client.py:332-368`）只能读、不能跑。
- **评分与安装相关。** `run_tests.sh:1` 跑的是 `r2e_tests`，它不在工作树里；这是评分测试，解题者看不到，属于正常情况。`install.sh:4` 的 `make .develop` 在 `Makefile:10-63` 里没有对应目标，这与 `environment_brief.md:13` 说包没装进 venv 一致。`Makefile`、`.travis.yml`、`setup.cfg` 还停留在 Python 3.3 + nose 的年代，按 `environment_brief.md` 用 `python -m pytest` 即可。
- **无需构建。** 这是纯 Python 包，`setup.py:28-47` 没有扩展模块。

## 4. 开发需求表

| 操作 / 资产 / 服务 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 | 最小命令（建议，未执行） |
| --- | --- | --- | --- | --- |
| 从源码树导入 `aiohttp` | `aiohttp/__init__.py` | 支持：在 `/testbed` 下用 `python -c`，或设 `PYTHONPATH`（第 13 行） | 无 | `import_version` |
| 复现题面（mock 代理连接） | `user_prompt.txt:13-39`；`test_connector.py:305-339` | 支持：只需标准库 `unittest.mock`，不联网 | 题面示例不能原样使用（§3.3） | `repro_port_mocked`（核心）；`literal_example_probe`（核对示例本身） |
| 相关公开测试 | `test_connector.py:292-568` | 支持 `python -m pytest`（第 13 行） | 同文件的真实 socket 用例在 base 上可能就失败（§3.5） | `public_proxy_tests`；`public_connector_file` |
| `ClientRequest` 解析测试 | `test_client.py:298-450` | 文件预计无法收集 | 只能读 | `public_client_file_collect` |
| 真代理 / 外网端到端 | `docs/client.rst:309-327` | 不支持：无出网（第 11 行） | 本地回环端到端也受 3.9 兼容问题阻碍（§3.5） | 不需要 |
| 构建 | `setup.py` 无扩展模块 | 不涉及 | 无 | 不需要 |
| 评分入口 | `run_tests.sh:1` | 工作树里没有 `r2e_tests` | 解题者跑不了 | 不适用 |

下面的命令与 `commands.json` 相同，都在 `/testbed` 下原样运行。`-B` 和 `-p no:cacheprovider` 只是为了不在仓库里写 `.pyc` 和 `.pytest_cache`。

1. **`import_version`**（expect `zero`）：预计依次打印 `3.9.21`、`0.9.1dev`、`/testbed/aiohttp/__init__.py`，修复前后相同。
2. **`literal_example_probe`**（expect `any`）：原样核对题面示例，用来证实 §3.3，不用来判断修复。
   - 预计先打印顶层导入失败：`ImportError: cannot import name 'ClientRequest' from 'aiohttp' ...`。
   - 改从 `aiohttp.client` 导入后，用真实循环调 `_create_connection`，预计得到 `TypeError ... non-coroutine generator`；环境不同时也可能是 `ProxyConnectionError`。此时 `req.path` 仍是 `'/path'`，修复前后相同。
3. **`repro_port_mocked`**（base 上 expect `nonzero`，修复后应为 `zero`）：像公开测试那样 mock `loop.create_connection`，分别经公开方法 `connect()` 和题面使用的 `_create_connection()` 各走一遍。
   - 先打印三条参考结果：无端口、显式 `:80`、带 userinfo 和查询串。其中 `http://localhost:80/path` 的结果取决于实现（U1），只看不判。
   - 然后断言：无端口 URL 仍是 `http://www.python.org/`；题面 URL 得到 `http://localhost:1234/path`。
   - base 上预计两条题面结果都是 `'http://localhost/path'`，以 `AssertionError` 退出，退出码 1。修复后打印 `OK`。
4. **`public_proxy_tests`**（expect `zero`）：跑 `tests/test_connector.py::ProxyConnectorTests` 的 13 个用例，修复前后都应全部通过。
5. **`public_connector_file`**（expect `any`）：整个文件跑一遍，看 base 上已有的失败（预计集中在 `HttpClientConnectorTests`）。修复后失败集合不应变大。
6. **`public_client_file_collect`**（expect `nonzero`）：预计在收集阶段因 `SyntaxError`（`test_client.py:647`）中断，退出码 2，修复前后相同。

## 5. 阅读范围与限制

实际打开的文件：

- 角色卡；`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`worktree_manifest.json`（全文）。
- `worktree/aiohttp/connector.py`、`client.py`、`__init__.py`（全文）；`aiohttp/test_utils.py:1-200`；`protocol.py:1-12` 和 `errors.py:1-10`（只看 `__all__`）。
- `worktree/tests/test_connector.py`（全文）；`tests/test_client.py:296-450, 640-704`；`tests/test_client_functional.py:1-40`。
- `install.sh`、`run_tests.sh`、`process_aiohttp_updateasyncio.py`、`Makefile`、`setup.py`、`setup.cfg`、`.travis.yml`、`.gitignore`（全文）；`docs/client.rst:280-339`；`CHANGES.txt:1-40`。
- 在 `worktree/` 内 grep 过：各模块的 `__all__`、`ClientRequest`、`proxy`、`create_task(` / `asyncio.async`、`async` / `await` 关键字、`netloc` / `port` / `host` 的用法、`setup.py` 里的扩展模块、`docs/api.rst` 的 automodule。

没查的范围：

- `aiohttp/` 其余模块（`protocol.py`、`parsers.py`、`streams.py`、`server.py`、`wsgi.py`、`websocket.py`、`worker.py`、`multidict.py`、`helpers.py`）只做了 grep。
- `tests/` 的其余文件和 `examples/` 只做了 grep；`docs/` 的其余部分没读。
- `worktree_manifest.json` 里 `initial_diff.source` 指向 `PUBLIC_DIR` 之外，没有打开。初态改动的内容只从工作树现状和转换脚本推断。

限制：

- `user_prompt.txt` 只是静态渲染，不是捕获的模型消息；`worktree/` 也不是完整的运行容器（没有 `.venv`、`.git` 和隐藏测试）。本记录没有验证模型实际收到的消息、运行资源或开发条件。
- 所有 Python 3.9 行为判断（`ImportError`、`TypeError`、`create_task(loop=)`、`SyntaxError`、公开测试的通过数）都是静态推断，以协调者照跑 `commands.json` 的结果为准。
- 会话启动时自动载入的本机说明文件里出现过本题的实例 ID，但只是镜像拉取和清理记录，不含补丁、测试或审查结论；本记录没有使用其中任何信息。我没有读任何 private / history 材料。

## 关键未知

1. U1：URL 显式写默认端口时是否保留端口，以及评分测试是否钉住了其中一种写法。
2. U4：题面示例从顶层导入 `ClientRequest`，这在 base 上不成立。如果评分测试照此导入，只修 `req.path` 不够。
3. §3.5 的环境推断（真实 socket 路径和 `test_client.py` 在 3.9 下不可用）需要由命令 2、5、6 证实。
