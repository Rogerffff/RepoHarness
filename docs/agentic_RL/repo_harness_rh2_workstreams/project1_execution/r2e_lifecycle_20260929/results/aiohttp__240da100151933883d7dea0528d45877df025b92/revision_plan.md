# aiohttp 240da100：R-c 修订方案（补非示例端口实例；补 https 显式端口的 CONNECT 目标断言）

2026-09-29 · 修订执行者（Claude，单题闭环试行；统一标准 v1 §5 模板内，Claude 执行、Codex 复核）。

**状态：R-c 两项合并为一轮修订，试跑验收 7 个候选全部与预期一致（试跑工具，不是正式评分）。不需要用户决定。** 待协调者落正式修订单与派生镜像材料、跑正式评分，再送 Codex 复核。R-a 本轮不做。

路径约定（仓库根相对；`trials/`、`cands/`、`revision_draft.json` 相对本目录）：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/aiohttp__240da100151933883d7dea0528d45877df025b92/`，`W` = `PUB/worktree`。
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/aiohttp__240da100151933883d7dea0528d45877df025b92/`；`HT` = `PRIV/hidden_tests/test_1.py`（父版本，584 行）；`HT'` = 修订后的 `test_1.py`（629 行）。
- `INV` = `runs/r2e_lifecycle_20260929/inv/aiohttp_240d/`；`DC` = `runs/r2e_lifecycle_20260929/devcheck/aiohttp__240da100151933883d7dea0528d45877df025b92/`。

## 1. 模板与要纠正的误判

**模板：R-c**（v1 §5）。两处修改各对应一个 S1，逐项写依据，合并在同一轮完成。

| 项 | 要纠正的 S1 | 触发反例（当前材料） | 出处 |
| --- | --- | --- | --- |
| R-c 1 | T2c：唯一目标断言 `HT:584` 只用题面示例 `http://localhost:1234/path`（`PUB/user_prompt.txt:22`）。T2b：退化候选 DG1（只在端口为 1234 时补 `:1234`）得 1 | DG1 正式评分 1.0（`INV/ledger_DG1.jsonl:1`） | `card.md` §4、§6；`review.md` §1 第 1–2 行 |
| R-c 2 | v1 §4 第 4 步：得 1 的候选破坏了有文档的常用行为。让 `ClientRequest.host` 带上端口后，直连显式端口的目标变成 `('localhost:1234', 1234)`，https 经代理的 CONNECT 目标变成 `host:port:port` | WR1 正式评分 1.0（`INV/ledger_WR1.jsonl:1`）；WR2 当前材料试跑得 1（`trials/cur_WR2.json`） | `card.md` §4、§6；`review.md` §0 第 1–2 点、§5 第 2 条 |

**不在本轮：R-a。** 两个期望 FAILED 的死键（T5）照旧。SC1 得 1，说明最可能出现的顺手改动不受罚；"真实候选让死键翻转时改为必做"的触发条件保留（`review.md` §2.2）。

## 2. 公开依据

### R-c 1：非示例端口实例

- **题面的一般表述**：
  - 标题 `PUB/user_prompt.txt:5`；
  - 描述 `:9` 说的是 ProxyConnector 连接 "a URL that includes a specific port" 时丢端口，没有限定主机或端口；
  - Expected `:29-31`：`req.path` 应保留端口。
- **示例只是其中一个实例**（`:22`：`localhost`、`1234`、`/path`）。现有目标断言 `HT:582-584` 与它逐字相同。
- **公开旧测试** `W/tests/test_connector.py:324-352`（`test_connect`）：同一主机 `www.python.org`，经公开入口 `connect()`，断言无端口时 `req.path == 'http://www.python.org/'`（`:341`）。新实例就是它带显式端口的对应情形。
- **选择理由**：主机、端口（8080，非默认）、路径（`/some/path`）、入口（`connect()`）都与示例不同；不涉及显式默认端口（U1）和 https（U2）。

### R-c 2：https 显式端口的 CONNECT 目标

- **公开测试** `W/tests/test_connector.py:468-493`（`test_https_connect`）：https 经代理时发 CONNECT，目标是 `host:port`（`:490-491`，`'www.python.org:443'`）。
- **公开源码与注释** `W/aiohttp/connector.py:350-361`：注释写明请求行 `CONNECT www.python.org:443 HTTP/1.1`、`Host: www.python.org`；`:361` 按 `'{}:{}'.format(req.host, req.port)` 生成目标。
- **公开测试** `W/tests/test_client.py:332-346`（`test_host_port`）：`https://python.org:960/` 的 `host == 'python.org'`、`port == 960`，即 `host` 不含端口。这个文件在 3.9 下一收集就 SyntaxError（`W/tests/test_client.py:647` 的 `asyncio.async(`；`DC/orig/captures/public_client_file_collect.out`），解题者跑不到它。
- **公开文档**：`W/docs/client.rst:309-327`（Proxy support），`W/CHANGES.txt:65`（Proxy 'CONNECT' support）。
- **题面** `:9`：请求要发往带指定端口的地址。https 经代理时，这个地址就是 CONNECT 目标，端口应出现且只出现一次。
- **独立佐证**：没看隐藏测试的公开读者也把"CONNECT 目标带端口"（R7）和"`ClientRequest.host` 不含端口"（R8）列为需要保留的旧行为（`public_read.md:28-29`）。
- **这是回归断言，不扩大需求**：base 本来就对（noop 在这个键上 PASSED），只是把公开 `test_https_connect` 的默认端口 443 换成显式端口 8443。
- **为什么选它，而不是搬 `test_host_port` 或断言直连目标**：
  - 这两种写法都只挡得住 WR1（改 `ClientRequest`），挡不住 WR2（在 `ProxyConnector._create_connection` 里就地改 `req.host`）；
  - CONNECT 断言对两者都成立，试跑已证实（§5.2）。

## 3. 具体改动

- **目标文件**：`r2e_tests/test_1.py`，即唯一的隐藏测试文件 `HT`。
- **草案条目**：一条 `hidden_test_text_replace`，一处 edit。
  - `old` 是文件最后一行 `HT:584`（`        self.assertEqual(req.path, 'http://localhost:1234/path')` 加换行），全文只出现一次；
  - `new` = 原行 + 下面两个测试；
  - `ProxyConnectorTests` 是文件里最后一个类，两个测试都追加在该类末尾。两项放在同一个 edit 里，只是因为插入点相同；逐项依据见 §2。
- **修订后位置**：R-c 1 在 `HT'` 586–602 行，R-c 2 在 604–629 行。

R-c 1（新键 `ProxyConnectorTests.test_request_port_other_url`）：

```python
    @unittest.mock.patch('aiohttp.connector.ClientRequest')
    def test_request_port_other_url(self, ClientRequestMock):
        # Not the issue's example: another host, port and path, through the
        # public connect() entry.  The explicit port must stay in req.path.
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

R-c 2（新键 `ProxyConnectorTests.test_https_connect_port`）：

```python
    @unittest.mock.patch('aiohttp.connector.ClientRequest')
    def test_https_connect_port(self, ClientRequestMock):
        # Same as test_https_connect but with an explicit non-default port:
        # the CONNECT target is still host:port, with the port given once.
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

**设计说明**：
- 写法沿用同文件。R-c 1 仿照 `HT:570-584` 的 mock 方式，入口换成公开 `test_connect` 用的 `connect()`。R-c 2 照搬公开 `test_https_connect`（`HT:468-493`），只把目标换成 `https://www.python.org:8443`，并去掉与本问题无关的 `pause_reading` / `get_extra_info` 调用断言。
- 只依赖类内的 `_fake_coroutine`（`HT:305-312`）和文件头已有的导入（`HT:11-14`），不新增对 `tests/` 下 base 测试辅助的依赖；不起 socket、没有定时器，没有时序因素。
- 代理请求由 mock 的 `ClientRequest` 返回，构造参数不被检查，所以不约束代理请求的 Host 头（U3）。
- **刻意不测**：
  - 显式默认端口（U1）：gold 保留、AL1 省略，两种都合理；
  - https 的 `req.path`（U2）、代理请求的 Host 头（U3）；
  - TLS `server_hostname`、直连 `TCPConnector` 的目标；
  - 查询串、目标 URL 里的 `user:pass@`、自定义 Host 头（T3）。

## 4. 期望映射逐键变化

- **原 33 键不变**：31 个 PASSED；`HttpClientConnectorTests.test_tcp_connector`、`HttpClientConnectorTests.test_unix_connector` 仍为 FAILED。
- **新增两键**：
  - `ProxyConnectorTests.test_request_port_other_url`: `PASSED`（R-c 1）；
  - `ProxyConnectorTests.test_https_connect_port`: `PASSED`（R-c 2）。
- **合计 35 键**，完整映射见 `revision_draft.json` 的 `expected_after`。正式修订单的 expected 部分：`added` 为这两键，`changed`、`removed` 为空。
- **期望从哪里来**：R-c 1 是题面 Expected 的非示例实例；R-c 2 是 base 已有、公开测试测过默认端口的行为。gold 通过是验证结果，不是依据；没有复制 gold 输出作期望。
- **版本记录**：

  | 文件 | sha256 |
  | --- | --- |
  | 父版本 `test_1.py`（`HT`） | `530b4631…` |
  | 父版本 `expected_output.json`（33 键） | `5444ee2a…` |
  | 父版本隐藏测试树 | `b74735a5…`，`material_revisions` 为空 |
  | 修订后 `test_1.py`（`HT'`，629 行） | `5ad37c35…` |
  | 试跑用 `draft.json` | `50364a10…` |
  | 试跑用 `expected_after.json`（35 键） | `2ad2304c…` |

  父版本三项与当前正式材料 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl:3` 一致；本题至今没有材料修订。全长哈希见 `revision_draft.json`。

## 5. 验收计划与试跑结果

**试跑环境**：
- 工具 `rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`，只作试跑。它与正式评分的差别见文件头：不做基线重建比对，不核隐藏测试树与入口摘要，权限布置简化。
- 派生镜像 `sha256:a6dee3349d27…`，配方 `r2e_derive_v1+sysconfig_v1`。与 `INV` 下四份正式账本的 `image_id_actual` 相同。
- 所有候选补丁先在仓库外的 base 副本上 `git apply --check -v` 通过，输出都列出了被改文件。试跑时 `RH2_APPLY_RC=0`，修订草案都报 `RH2_TRIAL_EDITS_APPLIED=1`，每次 35 键全部解析，没有 missing / extra。
- 单次试跑墙钟 18–26 s，其中测试 2.5–3.2 s。

### 5.1 当前材料上的对照（不进 acceptance）

| 候选 | 结果 | 出处 |
| --- | --- | --- |
| noop | 0：只差 `test_request_port`（FAILED，`'http://localhost/path' != 'http://localhost:1234/path'`） | `trials/env_noop_current.json` |
| gold | 1：33/33 | `trials/env_gold_current.json` |
| WR2 | **1**：33/33（触发反例） | `trials/cur_WR2.json`（试跑） |
| DG1、WR1、AL1、SC1 | 都是 1.0，33/33 | `INV/ledger_{DG1,WR1,AL1,SC1}.jsonl:1`（协调者正式评分） |

### 5.2 修订草案下的验收

键名省略类名前缀 `ProxyConnectorTests.`；结果文件为 `trials/rev_<候选>.json`。

| 候选 | 补丁 | 角色 | 应得 | 应不符的键 | 试跑结果 | 当前材料 |
| --- | --- | --- | --- | --- | --- | --- |
| gold | `PRIV/gold.patch` | 正对照 | 1 | — | 1，35/35 | 1 |
| noop | 无 | — | 0 | `test_request_port`、`test_request_port_other_url` | 0，恰好这 2 键 | 0 |
| DG1 | `cands/aiohttp_240d_DG1.patch` | 第 3 步退化候选，R-c 1 的触发反例 | 0 | `test_request_port_other_url` | 0，恰好此键。`HT':602` 报 `'http://www.python.org/some/path' != 'http://www.python.org:8080/some/path'` | **1**（正式） |
| WR1 | `cands/aiohttp_240d_WR1.patch` | 第 4 步错误候选，R-c 2 的触发反例 | 0 | `test_https_connect_port` | 0，恰好此键。`HT':629` 报 `'www.python.org:8443:8443' != 'www.python.org:8443'` | **1**（正式） |
| WR2 | `cands/aiohttp_240d_WR2.patch`（本轮新写） | 就地改坏输入，复核要求加跑 | 0 | `test_https_connect_port` | 0，恰好此键，断言信息同 WR1 | **1**（试跑） |
| AL1 | `cands/aiohttp_240d_AL1.patch` | 合理替代解 | 1 | — | 1，35/35 | 1（正式） |
| SC1 | `cands/aiohttp_240d_SC1.patch` | gold 加顺手补的 `@asyncio.coroutine` | 1 | — | 1，35/35。死键仍 FAILED，`test_tcp_connector` 的失败原因变成 AttributeError | 1（正式） |

**判读**：
- **正对照 1、noop 0**：成立。正对照 gold 本身满足公开要求：只改一个词（`host=req.netloc`），私有行为对照全部 OK（`card.md` 附录 B）。
- **误判已纠正**：DG1、WR1、WR2 在当前材料得 1，修订后都得 0，而且各自只在针对它的那个新键失败。WR1 破坏 CONNECT 目标一事，由此从源码推断变成了执行证据，这是 `review.md` §0 第 1 点要的；目前是试跑层面，正式评分待协调者跑。
- **没有误拒**：AL1、SC1 仍得 1。
- **旧键不受影响**：
  - noop、gold、WR2 的旧 33 键状态，修订前后逐键相同；其余候选修订后旧键全部与期望一致（`status_diff` 只含新键）。
  - 新测试各自建 loop 与 mock、不改全局状态。所以在当前材料上因旧键得 0 的候选，修订后仍为 0；例如"总是补端口"会被 `test_connect`（`HT:341`）挡住。
- **未跑**：
  - AL2（gold 加 `if not req.ssl:`）：静态判断得 1；
  - WR3 / WR4（T3）：静态判断得 1；
  - "总是补端口"：静态判断得 0。
  这些不改变本轮结论，沿用 `review.md` §2.3 的静态判断。

**WR2 补丁**（`cands/aiohttp_240d_WR2.patch`，sha256 `1b8a32eb…`）：
- **改法**：在 `aiohttp/connector.py` 的 `ProxyConnector._create_connection` 里、原 342 行 `req.path = …` 之前插入 `req.host = req.netloc`，343 行仍用 `host=req.host`。
- **违反的公开要求**：`req.host` 被就地改成带端口的 netloc，随后 CONNECT 目标（`W/aiohttp/connector.py:361`）变成 `host:port:port`，TLS `server_hostname`（`:382`）也带上端口，与 §2 R-c 2 的依据冲突。
- **校验**：在仓库外的 base 副本上 `git apply --check -v` 通过，改后文件可以正常解析。该副本的 `aiohttp/connector.py` blob 是 `d3582114`，与 gold 补丁的 index 行一致。

## 6. 修订后仍受保护的公开要求与剩余事项

**受保护的公开要求**（键名省略 `ProxyConnectorTests.`）：
- **显式端口保留在 `req.path`**：
  - 示例实例 `test_request_port`（`_create_connection` 入口）；
  - 非示例实例 `test_request_port_other_url`（`connect()` 入口，另一主机、端口、路径）。
- **无端口时不补 `:80`**：`test_connect`、`test_auth`、`test_auth_from_url`。
- **连代理失败时不改请求**：`test_proxy_connection_error`、`test_auth__not_modifying_request`。
- **代理认证头迁移**：`test_auth`、`test_auth_from_url`。
- **CONNECT 目标是 `host:port`**：默认端口 `test_https_connect`，显式端口 `test_https_connect_port`。CONNECT 的失败路径：`test_https_connect_runtime_error`、`test_https_connect_http_proxy_error`、`test_https_connect_resp_start_error`。

**仍未覆盖，维持登记**：
- **T5 死键**：R-a 可选，本轮不做，触发条件保留。
- **T3**：
  - 查询串、目标 URL 里的 `user:pass@`、自定义 Host 头；
  - 直连 `TCPConnector` 的显式端口目标、TLS `server_hostname` 没有直接断言。WR1、WR2 这一类已由 CONNECT 键挡住；只改直连路径、不碰 CONNECT 的候选，目前没有具体实例。
- **U1 / U2 / U3**：刻意不测。
- **P4**（题面示例原样跑不起来）：照旧登记。
- **X1**：`618335186f22` 的公开初态含本题修复与原目标测试，照旧登记。两个新测试是新写的：按新测试名和两个新 URL 字面值 grep 了 v3 的 5 个 aiohttp 公开工作树，没有命中。

## 7. 边界与交接

- **只做 R-c**：
  - 不改题面，不删键，不放宽已有断言，没有复制 gold 输出作期望；
  - 两项都有公开依据，不涉及 P5 或其它模板外事项，**不需要用户决定**。
- 没写 `s2_r2e` 下的正式材料，没改生产代码。
- **协调者待办**：
  1. 把 `revision_draft.json` 的 `revisions` 落为正式修订单（`hidden_test_text_replace`），另加 `expected_file_replace`（`added` 两键）；
  2. 重建材料与派生镜像；
  3. 正式评分至少跑 gold、noop、DG1、WR1、WR2、AL1、SC1，按 §5.2 判读；
  4. 送 Codex 复核。
- **之后重判 v1 用途**：按 `card.md` §5 重判。
  - 训练候选要的正面证据（核心断言、noop 0 / gold 1、第 2、3 步结果）届时齐全；
  - 留出评测仍受 D3 按仓库划分和"标明版本的自建评测"的限制；
  - 能力比较的 X1 标注按 `review.md` §2.1 补上。
