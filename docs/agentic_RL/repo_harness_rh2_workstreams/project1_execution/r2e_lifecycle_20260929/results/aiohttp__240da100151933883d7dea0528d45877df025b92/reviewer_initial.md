# aiohttp__240da100 独立复核初判（第一步）

独立复核者，R2E 单题闭环试行，2026-09-29。本文在读主审产物、公开读者产物和历史引用**之前**写成，只依据下文 §1 列出的原件。没有运行项目代码或容器；文中凡写"预计得分"的，都是静态推断，要由协调者用正式评分实跑确认。

路径缩写（都相对仓库根）：

- `PUB` = `runs/r2e_static_prep_20260924/v3/public/aiohttp__240da100151933883d7dea0528d45877df025b92`；`W` = `PUB/worktree`
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/aiohttp__240da100151933883d7dea0528d45877df025b92`；`HT` = `PRIV/hidden_tests/test_1.py`
- `Ln-all` / `Lg-all` = `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-a_fd1119cd.eval.log` / `…-all-gold-a_508fe701.eval.log`
- `Ln-reps` / `Lg-reps` = 同目录 `evallog_replay-r2e-rf-reps-noop-_8d7cc1d6.eval.log` / `…-reps-gold-_5292482f.eval.log`
- `Ln-env` / `Lg-env` = `runs/r2e_env_repair_20260924/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_fb3ab1e2.eval.log` / `…_3031169c.eval.log`

## 0. 初判结论

| # | 结论 | 证据层次 |
| --- | --- | --- |
| 1 | 材料一致，当前 noop 0、gold 1 稳定。唯一目标键是 `ProxyConnectorTests.test_request_port`，noop 的失败信息与题面 Actual Behavior 逐字相同 | 历史真实 RH2 评分 6 次（current）+ M3 独立参考 2 次 |
| 2 | **S1（T2c，v1 §4 第 2 步直接命中）**：核心要求只有一条直接断言，输入和期望全是题面示例的字面值 | 静态对照，确定 |
| 3 | 第 3 步退化候选 C4（只在端口为 1234 时带端口）预计得 1，会再记 T2b | 静态推断，待实跑 |
| 4 | 新疑点（第 4 步）：错层修复 C3（把端口并进 `ClientRequest.host`）预计得 1，但它破坏公开旧测试 `test_host_port`，也让所有带端口的直连和带端口的代理失效 | 静态推断，待实跑；得 1 即 S1 |
| 5 | 两个期望 FAILED 键（`HttpClientConnectorTests.*`）的失败来自 Python 3.9 与 2014 年版 aiohttp 不兼容，与本题无关。合理修复（含 C1、C2）不会让它们翻转；只有越出题意去移植运行时才会被判 0 | 日志 + 静态推断；T5 登记，R-a 可选 |
| 6 | P4：题面示例在本 base 上原样跑不起来（先是 ImportError，再是 TypeError，最后无网），可以照公开测试的 mock 写法替代复现 | 静态 + 日志 |
| 7 | X1：本题 gold 和新测试逐字出现在 aiohttp `61833518` 的公开初态；aiohttp 3.x 的三题含同源的后继测试 | 已打开这几题的公开包核对 |

没有发现：漏修原例、gold 回归或无关改动、材料错配、题面泄漏修法、跨文件撞键；本题没有材料修订，(f) 不适用。

**暂定处置**：进训练前要做 R-c。R-c #1（补非示例实例）必做；R-c #2（加入公开 `test_host_port`）取决于 C3 实跑结果；R-a（删两个环境性 FAILED 键）可选。用途见 §8，唯一优先下一步见 §12。

## 1. 实际读取范围

- 角色与方法：`roles/reviewer_r2e.md` 全文。`roles/investigator_r2e.md` 由 Read 工具整份返回，口径只采用"R2E 的评分口径""材料""第二批补充规则""单题闭环试行补充"四节。另读 `quality_review_protocol_20260920.md`、`r2e_environment_card.md`、`task_screening_standard_v1_20260925.md`、`record_template.md`。
- 公开包：`PUB/user_prompt.txt`、`environment_brief.md`、`public_bundle.json`、`worktree_manifest.json`（前 200 行）。工作树里读了 `W/aiohttp/connector.py` 全文、`client.py` 第 1–530 行、`test_utils.py` 第 1–160 行、`__init__.py`，以及 `protocol.py` 第 705–800 行（只为跨题核对）；`W/tests/test_connector.py` 与 `HT` 做了 diff；`tests/test_client.py` 第 296–372 行加 grep；`tests/test_client_functional.py` 第 1–30 行加 grep；`process_aiohttp_updateasyncio.py`、`install.sh`、`run_tests.sh`、`setup.cfg`、`CHANGES.txt` 第 1–40 行；`docs/` 做了 proxy 相关 grep。
- 私有包：`gold.patch`、`expected_output.json`、`revisions.json`（`[]`）、`run_tests.sh`、`run_refs.json`、`grading_bundle.json`、`validation_bundle.json`、`HT` 全文，并核对了 sha256。
- 运行原件：`run_refs.json` 里 6 条 `material=current` 行，即 `runs/r2e_rf_20260923/remote/ledger_r2e_{all,reps}_{noop,gold}.jsonl` 和 `runs/r2e_env_repair_20260924/_rerun2/ledger_{noop,gold}.jsonl` 各自的第 3 行；对应 6 份 eval 日志（`Ln-all` 读全文，其余与它逐一 diff，只有对象地址和时间戳不同；sha256 都与 run_refs 一致）。M3 独立参考：`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl` 第 8、55 行，以及 `…/logs_r2e/aiohttp/240da1001519/gold/a{1,2}/test_output.txt`（grep）。
- 跨题比对：`cross_task_gold_scan.json`、`cross_task_test_scan.json` 中涉及本题的条目。
- 同仓其它题的公开包：`aiohttp__618335186f22…`（`worktree/aiohttp/connector.py` 第 585–606 行、`tests/test_connector.py` 第 1060–1082 行、`protocol.py` 第 708–805 行、题面开头）；`aiohttp__4075c653…`（`tests/test_proxy.py` 第 595–640 行、题面开头）；`aiohttp__1c1c0ea3…`、`aiohttp__22a12cc2…`（`tests/test_proxy.py` grep、题面开头）。
- **未读**：OUTPUT_DIR 的任何其它文件、`history/`、各审查目录、本批 README / `board.json` / `assignments.json`、devcheck 证据（本步没有提供）、账本指向的 `*.diagnostics.json`、M3 facts（含 `initial.diff`）、其它题的私有包。

## 2. 八方面

1. **公开需求**。题面（`PUB/user_prompt.txt:5-39`）要求：经 `ProxyConnector` 发出的请求，如果 URL 带显式端口，`_create_connection` 之后 `req.path` 应是含端口的绝对 URI，示例为 `'http://localhost:1234/path'`。公开旧测试 `W/tests/test_connector.py` 与 `HT` 除新增测试外逐字相同，固定了三条旧行为：无端口 URL 改写为 `'http://www.python.org/'`；连代理失败时不改 `req`；CONNECT 的目标是 `host:port`。`W/aiohttp/client.py:232-233` 的 `netloc` 是现成属性，注释也写明了用途，属于"查代码可知"，不必读隐藏材料。题面没有规定两件事：显式写出的默认端口（`:80`）要不要保留；HTTPS 走 CONNECT 后要不要改写 `req.path`。隐藏测试对这两点也都没断言，没有过度规定。
2. **材料与初始问题**。base `ef756ce2` 与题面一致。`W/aiohttp/connector.py` 的 blob 是 `d3582114`，等于 gold 的 `index d3582114..f20a8716`。镜像初态的改动只在 `client.py` / `server.py` / `worker.py`：安装脚本把 `asyncio.async(` 换成 `asyncio.create_task(`（`W/process_aiohttp_updateasyncio.py:9`、`Ln-all:1-6`），不碰 `connector.py`。原问题在 `W/aiohttp/connector.py:342-344`：这里用的是 `host=req.host`，而 `req.host` 在 `client.py:237-251` 已去掉端口。noop 目标键报 `AssertionError: 'http://localhost/path' != 'http://localhost:1234/path'`（`Ln-all:199-205`）。`HT`（`530b4631…`）、expected（`5444ee2a…`）、gold（`df75d1d2…`）、`run_tests.sh`（`8285765f…`）的 sha256 与 bundle 和账本都一致。
3. **测试是否测到要求**。`HT` 全部读过，它等于公开 `tests/test_connector.py` 加上新增的 `test_request_port`（`HT:570-584`）。6 次 current 运行的 mismatched 都只有这一个键。它直接断言了核心要求，但只用了题面示例的字面值（见 §5）。
4. **是否误拒合理解**。静态检查了以下候选，预计都得 1：C1（只在非默认端口时带端口）；C2（gold 加上给 `TCPConnector._create_connection` 补 `@asyncio.coroutine`）；顺带把代理请求的 Host 头改成 `netloc`；HTTPS 分支不改写 path；在 `client.__all__` 导出 `ClientRequest`，让题面的 import 能用。没有发现缺公开依据的精确断言。mock 形状耦合有两处：`HT:348-352` 用 `assert_called_with` 校验精确 kwargs；`_fake_coroutine`（`HT:305-312`）返回普通生成器。两者都来自公开旧测试，agent 跑公开测试就能看到；它们只会拒绝超出题意的 `async`/`await` 现代化改写。
5. **回归与 gold 完整性**。gold 只改一行。`netloc` 已去掉 userinfo（`client.py:228-233`）并做过 IDNA 编码；对无端口 URL，结果与旧行为相同。没有发现回归或无关改动。保护缺口：`ClientRequest.host` 不含端口这一语义只在公开 `W/tests/test_client.py:332-346` 里测，隐藏测试不测（对应 C3）；端到端直连本可以兜住 C3，但它在本环境里本来就 FAILED。
6. **agent 开发条件**：见 §9。
7. **交付与评分边界**。修复只涉及 `aiohttp/connector.py`，纯 Python，不用构建。账本字段 `observations.RH2_OBS_IMPORT_PATH=/testbed/aiohttp/__init__.py` 说明评分时导入的是候选工作树。`HT:17` 在模块级导入 base 的测试辅助 `tests.test_client_functional.Functional`，但它只被两个期望 FAILED 的键使用；候选若改坏该文件，整个模块会收集失败而全键 0（公开提示已禁止改测试文件）。`HT` 的 tearDown 调用 `aiohttp.test_utils.run_briefly`（`HT:300`）；`test_utils.py` 是包内的非测试文件，候选可以改，但没有找到借它翻转目标键的路径。
8. **题目关系**：见 §10。

## 3. 需求—断言双向表

| 公开要求或旧行为 | 公开依据 | 测试与决定性断言 | 覆盖 | 执行证据或下一步 |
| --- | --- | --- | --- | --- |
| 核心：URL 带显式端口时，代理改写后的 `req.path` 保留端口 | 题面 `:9`、`:29-31` | `test_request_port`，`HT:584` | 覆盖，但只用示例字面值（T2c） | noop FAILED（`Ln-all:199-205`），gold PASSED（`Lg-all:213`） |
| 同一核心要求的非示例实例（其它主机或端口） | 题面 `:9` 的一般表述 | 无 | **缺失** | C4 预计得 1；R-c #1 |
| 无端口 URL 仍改写为 `'http://www.python.org/'` | 公开旧测试 | `test_connect` `HT:341`、`test_auth` `:400`、`test_auth_from_url` `:438` | 覆盖（挡住"总是加端口"） | gold PASSED |
| 连代理失败时不改 `req.path` 和 headers | 公开旧测试 | `test_proxy_connection_error` `HT:373-374`、`test_auth__not_modifying_request` `:464-466` | 覆盖（挡住"连接前就改写"） | 同上 |
| CONNECT 目标为 `host:port` | 公开旧测试 | `test_https_connect` `HT:490-491` | 只覆盖默认端口 443 | 同上 |
| `ClientRequest.host` 不含端口，连接层按 `host` 和 `port` 分开解析 | 公开 `W/tests/test_client.py:332-346`；`connector.py:143,285` | 无 | **缺失** | C3 待实跑；R-c #2 |
| 代理请求的 Host 头 | 公开旧测试 | `HT:348-352`（无端口实例） | 覆盖；gold 和"改成 netloc"都能过 | — |
| 端到端的直连与 Unix 连接 | 公开旧测试 | `HttpClientConnectorTests`，期望 FAILED | 无效（T5） | §4(a) |

## 4. R2E 专项

**(a) 非 PASSED 的期望键**：`HttpClientConnectorTests.test_tcp_connector` 与 `test_unix_connector` 都期望 FAILED，原因如下。

- `test_tcp_connector`：`W/aiohttp/connector.py:274` 的 `TCPConnector._create_connection` 没有 `@asyncio.coroutine`。Python 3.9 下，它在 `:290` 对原生协程 `loop.create_connection` 做 `yield from`，抛出 `TypeError: cannot 'yield from' a coroutine object in a non-coroutine generator`（`Ln-all:76-84`）。
- `test_unix_connector`：连接建立后，`aiohttp/parsers.py:246` 创建 `asyncio.streams.StreamWriter` 时触发 Python 3.9 对 reader 类型的断言（`Ln-all:156-179`），writer 因此是 None，发送请求头时在 `protocol.py:650` 报 `AttributeError`（`Ln-all:151-154`）。
- 再往下还有一层：`client.py:512` 的 `asyncio.create_task(..., loop=...)` 是安装脚本改写的结果，Python 3.9 的 `create_task` 不接受 `loop` 参数。
- gold 日志与此相同（`Lg-all:214-216`），M3 在来源镜像上的参考结果也相同（`…/gold/a1/test_output.txt:195-197`）。

要让这两键 PASSED，至少得同时修好 `parsers` 与 Python 3.9 `StreamWriter` 的兼容、`create_task` 的 `loop` 参数，以及服务端的同类问题，这远超题意。C2 只会把 `test_tcp_connector` 的失败点从 TypeError 挪到与 `test_unix_connector` 相同的 AttributeError，状态仍是 FAILED（静态推断，建议实跑坐实）。结论：记 T5——按来源解释，这是环境不兼容造成的无效断言，但不算已证实的误拒；R-a 可选。

**(b) 题面报错是否出现在 noop 目标键**：出现，`Ln-all:200` 与题面 `:38` 逐字相同。

**(c) 题面是否泄漏修法**：没有。题面没提 `netloc`，也没给改法。但示例代码就是测试的形状：同样调用 `_create_connection`，字面值也相同，这一点归 T2c。另外，示例里的 `from aiohttp import ProxyConnector, ClientRequest` 在本 base 会导入失败：`client.py:3` 的 `__all__ = ['request', 'HttpClient']`，其它子模块的 `__all__` 也不含 `ClientRequest`（静态核对），归 P4。

**(d) 测试支撑、搬迁伪影与撞键**：`HT:17` 依赖 base 的 `tests.test_client_functional`。`tests/` 下没有 `__init__.py`，靠 `python -m pytest` 把 rootdir `/testbed` 放上 `sys.path`，按命名空间包导入。评分运行证实导入可用：共收集 33 项，两个期望 FAILED 键都走到了请求阶段才失败。只有一个隐藏测试文件，33 个键互不相同，没有撞键，也没有 conftest 依赖。

**(e) 时间、随机与资源敏感**：没有随机。`BaseConnectorTests.test_get` 用了 `time.time()` 和 30 s 的 keepalive（`HT:99-105`）；两个 `test_del` 依赖 CPython 引用计数的即时回收。它们在 8 次运行中都稳定。用 socket 和线程的两键本来就期望 FAILED。固定路径 `/tmp/aiohttp_unix.sock` 位于评分容器的 tmpfs 里，每次都是全新的。未见 E5。

**(f) 修订**：`PRIV/revisions.json` 为 `[]`，`run_refs.current_material` 里没有修订，`env_recipe` 和 `resource_recipe` 都是 null，没有可核对的修订。

## 5. 严重度（v1 §4）

1. 核心要求有直接断言（`HT:584`），不是 T2a。
2. 这条断言**只用题面示例的字面值**：代理 `'http://proxy.example.com'`（题面 `:21` 对 `HT:572,576`）；请求 `'http://localhost:1234/path'`（`:22` 对 `HT:582`）；期望是同一个字符串（`:24,31` 对 `HT:584`）；调用的也是题面里的 `connector._create_connection(req)`（`:23` 对 `HT:583`）。其它断言 `req.path` 的键都用无端口 URL，测的是旧行为，不是核心要求的另一个实例。按严格版判为 **S1（T2c）**。
3. 退化候选 C4 预计得 1；实跑确认后再记 T2b。
4. C3 预计得 1，并破坏有文档的常用行为；实跑确认即为 S1。C-hdr（用 `req.headers['HOST']` 拼 URI）只在调用方自定义 Host 头时出错，公开依据是 `W/tests/test_client.py:362-368`，属边缘路径，记 T3，定为 S2 并登记，不必专门实跑。
5. 前几步已命中，本步不适用。

**整体为 S1**：T2c 已命中；T2b 和第 4 步待实跑。

## 6. 可区分的候选（可直接改成补丁）

| 编号 | 改法 | 当前材料预计 | R-c #1 后预计 | 用途 |
| --- | --- | --- | --- | --- |
| C1 合理替代解 | `aiohttp/connector.py` 的 `ProxyConnector._create_connection`（第 342–344 行）：先算 `default = 443 if req.ssl else 80`，再令 `host = req.host if req.port == default else '{}:{}'.format(req.host, req.port)`，用 `host` 拼 `req.path` | 1 | 1 | 确认新断言不误拒"只在非默认端口带端口"的读法 |
| C2 合理修复加兼容改动 | gold 那一行，再在 `connector.py:274` 的 `TCPConnector._create_connection` 前加 `@asyncio.coroutine` | 1；`test_tcp_connector` 仍 FAILED，失败点变为 `protocol.py:650` 的 AttributeError | 1 | 坐实期望 FAILED 键不惩罚兼容修复。若实跑得 0，就是 T1，需走 R-a |
| C3 错层修复（第 4 步） | `aiohttp/client.py` 的 `ClientRequest.update_host`，第 251 行 `self.host = netloc` 改成 `self.host = self.netloc`；`self.port` 的解析保留，`connector.py` 不动 | **1**（`HT` 里带端口的 URL 只有 `test_request_port`，它的 mock 不检查连接主机） | 1（仍漏掉） | 违反：公开 `W/tests/test_client.py:343-345`；直连任何带端口 URL 时，`connector.py:285,290-295` 会拿 `'host:port'` 去解析和连接，得到 OSError；代理 URL 带端口时连不上，得到 `ProxyConnectionError`；HTTPS 经带端口代理时，`connector.py:361` 生成 `'host:8443:8443'`。得 1 即 S1，走 R-c #2 |
| C4 退化候选（第 3 步，唯一） | gold 的修改位置，第 342–344 行：`host = req.netloc if req.port == 1234 else req.host`，再用 `host` 拼 `req.path`。类型是"与输入无关的固定结果"，只对示例端口成立 | **1** | 0 | 违反题面 `:9` "a URL that includes a specific port" 的一般表述。输入 `'http://localhost:8080/path'` 会得到 `'http://localhost/path'`，端口丢失 |

协调者实跑时，要核对补丁确实交付（账本 `apply_ok`、`projection.included_paths`），并且 33 键全部被解析。

## 7. 修订建议（v1 §5）

**R-c #1（针对 T2c 与 T2b，必做）**

- 公开依据：题面 `:9` "a URL that includes a specific port"，以及 `:29` "should retain the port number"。
- 改动：在 `PRIV/hidden_tests/test_1.py` 的 `ProxyConnectorTests` 末尾，即 `test_request_port` 之后，加入下面的方法；`expected_output.json` 同时增加 `"ProxyConnectorTests.test_request_port_other_url": "PASSED"`。

```python
    @unittest.mock.patch('aiohttp.connector.ClientRequest')
    def test_request_port_other_url(self, ClientRequestMock):
        proxy_req = ClientRequest('GET', 'http://proxy.example.com')
        ClientRequestMock.return_value = proxy_req

        loop_mock = unittest.mock.Mock()
        connector = aiohttp.ProxyConnector('http://proxy.example.com', loop=loop_mock)

        tr, proto = unittest.mock.Mock(), unittest.mock.Mock()
        tr.get_extra_info.return_value = None
        self._fake_coroutine(loop_mock.create_connection, (tr, proto))

        req = ClientRequest('GET', 'http://www.python.org:8080/index.html')
        self.loop.run_until_complete(connector._create_connection(req))
        self.assertEqual(req.path, 'http://www.python.org:8080/index.html')
```

- 为什么选这个实例：8080 是非默认端口，不会误拒 C1；主机与路径都不同于示例。刻意不测显式默认端口和 HTTPS，因为题面对这两点没有依据，两种读法都合理。
- 验收：gold 为 1；noop 为 0（mismatched 应是 `test_request_port` 和新键）；C4 为 0；C1、C2 为 1；键集严格相等，没有 unexpected。

**R-c #2（只在 C3 于当前材料实跑得 1 时做）**

- 公开依据：公开旧测试 `W/tests/test_client.py:332-346`（`test_host_port`）；连接层分别用 `req.host` 和 `req.port` 解析（`connector.py:143,285`）。
- 改动：在 `HT` 里新建一个类 `ClientRequestTests(unittest.TestCase)`，把 `test_host_port` 的方法体原样放进去（不需要 setUp）；expected 增加 `"ClientRequestTests.test_host_port": "PASSED"`。
- 验收：gold 为 1；noop 为 0（该键在 noop 下也 PASSED，它是回归键）；C3 为 0；C1、C2 为 1。

**R-a（可选，针对 T5）**

- 依据：§4(a)，两键在 Python 3.9 下不管修没修本题都是 FAILED；先例是 v1 §10 的 scrapy `9a15fcf8`。
- 改动：删除 `HT:247-289`（整个 `HttpClientConnectorTests` 类）和 `HT:17` 的导入，expected 同时删除这两个键。附带的好处是去掉了对 base 测试辅助的依赖。
- 验收：gold 为 1、noop 为 0，没有 missing 或 unexpected；C2 为 1。

不建议走 R-d 去移植运行时，那会改变被测项目本身。本题没有需要用户决定的事项。

## 8. 用途（v1 §2）初判

- `problem_localization`：**yes**。
- `capability_comparison`：**conditional**。还差 actor 侧的开发核对（本步没有看到 devcheck）。在 R-c 落地前，得 1 的补丁要事后审计是否属于 C3 或 C4 的形态：只对 1234 或 localhost 特判，或者把端口并进 `req.host`。评分依据与本批的运行条件已核对（§2 第 2 项、附录）。
- `training_candidate`：**conditional**（按当前材料不满足，因为还有未处理的 S1 T2c）。条件：R-c #1 验收；C3 实跑，得 1 则 R-c #2 验收；记录 C4 的退化探测结果；完成 devcheck；登记 X1；修订经 Codex 复核。
- `heldout_candidate`：**conditional**。质量条件同训练候选。另有 X1：本题答案逐字出现在 aiohttp `61833518` 的公开初态，按 D3 两题必须同仓同侧；修订后只能作"标明版本的自建评测"。
- `intended_use`：`development_diagnostic`。

## 9. 开发需求

- **导入**：`/testbed` 必须在 `sys.path` 上（`PUB/environment_brief.md:13`），从 `/testbed` 用 `python -m pytest` 运行。
- **依赖与网络**：不需要新包；没有 pip，也不能联网（`environment_brief.md:11`），各阶段都不需要网络。
- **资产、构建、权限**：没有资产；纯 Python，不用构建；agent（uid 54321）可写 `/testbed`。
- **提交边界**：只改 `aiohttp/connector.py`。
- **最小公开验证**：`cd /testbed && python -m pytest tests/test_connector.py -q`。预期 31 passed、2 failed，失败的是 `test_tcp_connector` 和 `test_unix_connector`，为预先存在、与本题无关的失败。评分侧在同一镜像上 pytest 用时约 0.5 s（`Ln-all:241`）；actor 侧待验。
- **原例能否复现（P4）**：不能原样复现。第一，`from aiohttp import … ClientRequest` 导入失败（`client.py:3`）。第二，改成 `from aiohttp.client import ClientRequest` 后，真实事件循环会在 `connector.py:290` 抛 TypeError，与 `Ln-all:82-84` 是同一处。第三，即使补上装饰器，也会因为无网而得到 `ProxyConnectionError`。替代复现：照公开的 `W/tests/test_connector.py:468-493`（`test_https_connect`），用 `unittest.mock.Mock()` 作 loop、用 `_fake_coroutine` 伪造 `create_connection`，再调 `_create_connection(req)` 查看 `req.path`。
- **证据层次**：评分侧是镜像层面实测（6 条 current 运行）；解题侧 actor 待验。

## 10. 题目关系（第 8 方面）

- **正向包含（已核）**：`host=req.netloc,` 逐字出现在 `runs/r2e_static_prep_20260924/v3/public/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2/worktree/aiohttp/connector.py:599`，位于新增的 `if not req.ssl:` 分支里。新测试也出现在同一包的 `tests/test_connector.py:1063-1080`，只多了 `loop=self.loop` 参数。`61833518` 是 aiohttp 0.17.0a0，晚于本题的 0.9.1dev。记 X1：训练时控制重复采样，留出集按 D3 放在同侧。
- **同名测试**：`test_request_port` 的 3.x 后继版本在 `aiohttp__4075c653…/worktree/tests/test_proxy.py:600-637`、`aiohttp__1c1c0ea3…/worktree/tests/test_proxy.py:701-737`、`aiohttp__22a12cc2…/worktree/tests/test_proxy.py:702-738`，断言 `req.url == URL("http://localhost:1234/path")`。这是同源测试，但 API 不同，不是本 base 的现成答案；同时也说明上游一直只用这一个示例值。
- **反向命中（未核）**：gold 扫描称 `61833518` 的 gold 唯一新增行出现在本题工作树里。要核实必须读 `61833518` 的私有 gold，超出本角色可读范围。它对本题评分没有影响，是 `61833518` 自己的 X1 登记事项。
- 与同仓其它题没有同一问题或补丁派生关系。

## 11. 探针就绪差距

按派发规则，本批 README §3 没有读。下表按 v1 §2 的训练候选条件和复核卡的要求逐条对照；协调者可以再按 README §3 重排。

| 条件 | 状态 | 谁来补 |
| --- | --- | --- |
| 当前材料 noop 0、gold 1 | 已满足：6 条 current 运行，分属同一配方（`recipe_sha256` 为 `0da821a1…`）的两次镜像构建，reps 用 `2b75db7b…`，其余用 `0189a61d…`，结果一致 | 协调者确认探针用哪次构建 |
| 目标键失败原因与题面一致 | 已满足 | — |
| 核心要求有直接断言 | 已满足 | — |
| 第 2 步补非示例实例 | 未满足（T2c） | 协调者做 R-c #1，Codex 复核 |
| 第 3 步退化探测实跑 | 未满足 | 协调者用 C4，原版和修订版各跑一次 |
| 第 4 步 C3 | 未满足 | 协调者实跑，得 1 则做 R-c #2 |
| 期望 FAILED 键的来源 | 已解释（日志加静态推断）；实跑 C2 可以坐实 | 协调者（可选），R-a 由协调者决定 |
| actor 开发核对 | 没有看到证据 | 协调者（devcheck） |
| 跨题关联 | 正向已核，反向未核 | 主审或协调者登记 X1；反向由有权读 `61833518` 私有包的人核对 |

## 12. 未知与唯一优先下一步

- **未知**：C1–C4 的实际得分（目前都是静态推断）；actor 侧的真实环境行为；反向 X1 命中的是哪一行；安装期脚本对 `server.py` / `worker.py` 的改写在其它路径上的影响（与本题的键无关，没有深入）。
- **唯一优先下一步**：协调者先在当前材料上用正式评分实跑 C4 和 C3（每个的测试阶段约 1 s），据结果在一轮里做完 R-c（#1 必做，#2 看 C3），再在修订版上跑 gold、noop、C1–C4 完成验收。

## 附录：current 运行原件

| 账本（第 3 行） | run_id | 镜像 ID | reward / 匹配 | mismatched | 日志 sha256 |
| --- | --- | --- | --- | --- | --- |
| `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl` | `r2e-rf-all-noop` | `0189a61de356…` | 0.0 / 32 of 33 | `test_request_port` | `a6a94ef0…` |
| `runs/r2e_rf_20260923/remote/ledger_r2e_all_gold.jsonl` | `r2e-rf-all-gold` | `0189a61de356…` | 1.0 / 33 of 33 | — | `71a147e6…` |
| `runs/r2e_rf_20260923/remote/ledger_r2e_reps_noop.jsonl` | `r2e-rf-reps-noop` | `2b75db7b16ca…` | 0.0 / 32 of 33 | `test_request_port` | `43dd21c2…` |
| `runs/r2e_rf_20260923/remote/ledger_r2e_reps_gold.jsonl` | `r2e-rf-reps-gold` | `2b75db7b16ca…` | 1.0 / 33 of 33 | — | `9fb35878…` |
| `runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl` | `r2e-envrepair-rerun-noop` | `0189a61de356…` | 0.0 / 32 of 33 | `test_request_port` | `05e432de…` |
| `runs/r2e_env_repair_20260924/_rerun2/ledger_gold.jsonl` | `r2e-envrepair-rerun-gold` | `0189a61de356…` | 1.0 / 33 of 33 | — | `e7bea783…` |

六行的共同事实：`grader_version` 为 `r2e-gym-subset@e8b9fcbc+parser:prime-envs@c4d04dfe`；`policy` 为 `network=deny_all`、uid 54322、2 CPU / 4 GiB / tmpfs 1 GiB；`apply_ok=true`；missing 和 unexpected 都为空。

M3 独立参考在来源镜像 `bb629a91…` 上跑 gold 两次（`r2e_gold_m3.jsonl` 第 8、55 行），结果都是 reward 1、33 of 33，期望状态为 PASSED 31 个、FAILED 2 个。它只作对照，不代表当前材料。
