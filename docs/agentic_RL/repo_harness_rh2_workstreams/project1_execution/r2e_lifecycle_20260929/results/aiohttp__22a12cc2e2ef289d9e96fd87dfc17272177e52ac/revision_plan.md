# aiohttp 22a12cc2 修订方案（R-e：代理路径的指纹校验改成真实行为测试）

2026-09-29 · 修订执行者（Claude，单题闭环试行，统一标准 v1 §5 模板内）。

**状态：修订草案已定稿，试跑验收通过（试跑工具，不是正式评分）。** 待协调者落正式修订单与派生镜像材料、跑正式评分，再送 Codex 复核。

路径约定：
- 仓库根相对路径。`PUB` = `runs/r2e_static_prep_20260924/v3/public/aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac/`，`PRIV` = 同目录下 `private/…`。
- `trials/`、`cands/`、`revision_draft.json` 相对本目录。

## 1. 结论

| 项 | 内容 |
| --- | --- |
| 模板 | 主体是 R-e：把 mock 交互测试改成真实行为测试，正例（指纹正确）与反例（指纹错误）都覆盖。其中请求级 `ssl=` 那一对同时是 v1 §4 第 2 步要求的非示例实例（R-c 成分，见 §3） |
| 改动 | 重写目标测试 `test_https_connect_fingerprint_mismatch`（键名不变），新增 3 个测试、1 个辅助方法和 2 个模块级网络替身 |
| 期望映射 | 18 键 → 21 键；原 18 键仍是 PASSED |
| 试跑 | gold 1、noop 0、K3 0、K4 0；K1、K2、RC、IC 都是 1。当前材料上 K3、K4 是 1，K2、RC 是 0，四个误判都在本镜像上复现，修订后全部纠正 |
| 边界 | 不改题面，不断言 transport 的关闭方式，也不断言异常里的 host/port |

## 2. 要纠正的误判

- **原目标测试**（`PRIV/hidden_tests/test_1.py:381-479`）只检查 mock 交互：
  - 把私有方法 `connector._get_fingerprint` 换成返回 Mock（`:449-455`）；
  - 那个 Mock 的 `check` 对任何 transport 都抛异常（`:415-418`）；
  - TLS transport 替身只实现了 `close`（`:400-402`）。
- **后果**（历史 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/grader_candidates.md:76-81`；本镜像 `trials/cur_*.json`）：

  | 候选 | 做了什么 | 当前得分 | 实际行为 |
  | --- | --- | --- | --- |
  | K3 | 校验连到代理的原始 TCP transport | 1 | 什么都没修 |
  | K4 | 配了指纹就一律拒绝 | 1 | 正确指纹也被拒 |
  | K2 | 不经 `_get_fingerprint` 取指纹 | 0 | 语义等价，被误拒 |
  | RC | 不匹配时用 `abort()` 断开 | 0 | 合理做法，被误拒 |

- **真实握手对照**（`…/r2e_static_review_batch2_20260925/grader_candidates.md:220-228`）显示 K2、RC 与 gold 行为一致，K3、K4 行为错误。Codex 第二批复核也确认了这点（`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_batch2_review_20260925/aio_scrapy/README.md:66-76`），并给出修订的最低要求：
  - 经公开配置注入指纹；
  - 覆盖正确、错误两种指纹，以及请求级优先；
  - transport 替身支持 `abort()` / `is_closing()`；
  - 接受 close 或 abort 任一种关闭方式。

## 3. 公开依据

- **题面**（`PUB/user_prompt.txt`）：
  - 标题 `:5`；
  - 描述 `:7`：配置了服务器指纹的 HTTPS 连接，指纹不符时不抛预期异常，连接照常建立；
  - Expected `:26`：应抛 `aiohttp.ServerFingerprintMismatch`，不让连接建立；
  - Actual `:30`。
- **文档**（`PUB/worktree/docs/`）：
  - `client_reference.rst:2006-2024`：`Fingerprint` 是 DER 证书的 SHA256 摘要，用法是把它作为 `ssl=` 传给 `ClientSession.get` 等请求方法；
  - `client_reference.rst:1050-1058`：`TCPConnector(ssl=…)` 同样接受 `Fingerprint`；
  - `client_advanced.rst:505-525`：示例里异常的 `expected` 是配置的指纹，`got` 是服务器证书的实际指纹；
  - `client_advanced.rst:536-538`：`ssl` 可以作为默认值传给 `TCPConnector`，请求方法传入的值覆盖默认值。
- **代码**（`PUB/worktree/aiohttp/`）：
  - `client_reqrep.py:139-147`：`Fingerprint.check` 遇到非 TLS transport 直接返回；否则对 `ssl_object.getpeercert(binary_form=True)` 求摘要，不符就抛 `ServerFingerprintMismatch(expected, got, host, port)`。
  - `connector.py:1046-1053`：`_get_fingerprint` 先看请求、再看连接器。
  - `connector.py:1326-1338`：直连路径已经会校验。
  - `connector.py:1345-1466`：经代理 CONNECT 后在 `:1460` 调 `_start_tls_connection`，这一步不校验。
- **公开旧测试**：`PUB/worktree/tests/test_client_fingerprint.py:30-35`（非 TLS transport 上 `check` 返回 None），以及 `tests/test_proxy.py`（隐藏文件其余 17 个回归键）。
- **为什么补请求级实例**：
  - 如果只用连接器级配置，核心断言的输入形态就与题面示例相同（`PUB/user_prompt.txt:16`，示例在连接器上配指纹），按 v1 §4 第 2 步（D1 严格版）仍是示例拟合。
  - 请求级 `ssl=Fingerprint(...)` 是文档给出的主要用法（`client_reference.rst:2014-2022`），"请求值覆盖连接器默认值"也有文档（`client_advanced.rst:536-538`）。所以它属于 R-c 允许的"非示例实例、有文档的常用行为"，不是新需求。
- **不扩大需求**，以下都不加：
  - HTTPS 代理那一跳（公开读者 R13，TLS-in-TLS）；
  - 不支持 `start_tls` 时走的 `_wrap_existing_connection`；
  - 不匹配后必须关闭或登记 cleanup（R14 多解）；
  - 异常 host/port 取代理地址还是目标地址（R5 多解）。

## 4. 具体改动（目标文件 `r2e_tests/test_1.py`，一条 `hidden_test_text_replace`，三处 edit）

1. `import gc\n` → `import gc\nimport hashlib\n`。
2. 在 `class TestProxy(unittest.TestCase):` 之前插入网络替身：

```python
_PEER_CERT_DER = b"DER-encoded certificate presented by the server"
_PEER_FINGERPRINT = hashlib.sha256(_PEER_CERT_DER).digest()
_OTHER_FINGERPRINT = hashlib.sha256(b"some other certificate").digest()


class _SSLObjectStub:
    """``ssl_object`` of a TLS connection: only the peer certificate is used."""

    def getpeercert(self, binary_form: bool = False) -> Any:
        return _PEER_CERT_DER if binary_form else {}


class _TransportStub(asyncio.Transport):
    """In-memory transport that serves ``get_extra_info()`` and records closing.

    The connection to the proxy is plain TCP (no ``sslcontext``); the transport
    returned by ``loop.start_tls()`` exposes ``sslcontext``, ``ssl_object`` and
    ``peername`` the way a real TLS transport does.
    """

    _start_tls_compatible = True

    def __init__(self, extra: Any = None) -> None:
        super().__init__(extra)
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def abort(self) -> None:
        self.closed = True

    def is_closing(self) -> bool:
        return self.closed
```

3. 用下面的代码整段替换原目标测试（`:381-479`，连同两个装饰器）：

```python
    def _connect_via_proxy(
        self, connector_ssl: Any, request_ssl: Any = True, cleanup: bool = False
    ) -> Any:
        """``connector._create_connection()`` for https://www.python.org through
        the HTTP proxy http://proxy.example.com (CONNECT, then TLS upgrade).

        The fingerprint is configured only through the public ``ssl=``
        parameters and checked by the real ``Fingerprint``; only the network is
        replaced (see ``_TransportStub``).  Returns the protocol of the new
        connection.
        """

        async def start_tls(
            transport: Any, protocol: Any, sslcontext: Any, **kwargs: Any
        ) -> _TransportStub:
            return _TransportStub(
                {
                    "sslcontext": sslcontext,
                    "ssl_object": _SSLObjectStub(),
                    "peername": ("127.0.0.1", 80),
                }
            )

        async def make_conn() -> aiohttp.TCPConnector:
            return aiohttp.TCPConnector(
                ssl=connector_ssl, enable_cleanup_closed=cleanup
            )

        proxy_req = ClientRequest(
            "GET", URL("http://proxy.example.com"), loop=self.loop
        )
        proxy_resp = ClientResponse(
            "get",
            URL("http://proxy.example.com"),
            request_info=mock.Mock(),
            writer=None,
            continue100=None,
            timer=TimerNoop(),
            traces=[],
            loop=self.loop,
            session=mock.Mock(),
        )
        host = [
            {
                "hostname": "hostname",
                "host": "127.0.0.1",
                "port": 80,
                "family": socket.AF_INET,
                "proto": 0,
                "flags": 0,
            }
        ]
        with mock.patch(
            "aiohttp.connector.ClientRequest", return_value=proxy_req
        ), mock.patch(
            "aiohttp.connector.aiohappyeyeballs.start_connection",
            autospec=True,
            spec_set=True,
        ), mock.patch.object(
            proxy_req,
            "send",
            autospec=True,
            spec_set=True,
            return_value=proxy_resp,
        ), mock.patch.object(
            proxy_resp,
            "start",
            autospec=True,
            spec_set=True,
            return_value=mock.Mock(status=200),
        ):
            connector = self.loop.run_until_complete(make_conn())
            with mock.patch.object(
                connector,
                "_resolve_host",
                autospec=True,
                spec_set=True,
                return_value=host,
            ), mock.patch.object(  # Called on connection to http://proxy.example.com
                self.loop,
                "create_connection",
                autospec=True,
                spec_set=True,
                return_value=(
                    _TransportStub({"peername": ("127.0.0.1", 80)}),
                    mock.Mock(),
                ),
            ), mock.patch.object(  # TLS upgrade for https://www.python.org
                self.loop, "start_tls", start_tls
            ):
                req = ClientRequest(
                    "GET",
                    URL("https://www.python.org"),
                    proxy=URL("http://proxy.example.com"),
                    loop=self.loop,
                    ssl=request_ssl,
                )
                return self.loop.run_until_complete(
                    connector._create_connection(req, [], aiohttp.ClientTimeout())
                )

    def test_https_connect_fingerprint_mismatch(self) -> None:
        # Connector-level pin that does not match the server certificate.
        for cleanup in (True, False):
            with self.subTest(cleanup=cleanup):
                with self.assertRaises(aiohttp.ServerFingerprintMismatch) as ctx:
                    self._connect_via_proxy(
                        Fingerprint(_OTHER_FINGERPRINT), cleanup=cleanup
                    )
                self.assertEqual(ctx.exception.expected, _OTHER_FINGERPRINT)
                self.assertEqual(ctx.exception.got, _PEER_FINGERPRINT)

    def test_https_connect_fingerprint_match(self) -> None:
        # Connector-level pin that matches: the connection is established.
        proto = self._connect_via_proxy(Fingerprint(_PEER_FINGERPRINT))
        self.assertTrue(proto.is_connected())

    def test_https_connect_fingerprint_mismatch_request_ssl(self) -> None:
        # ssl= given with the request overrides the connector's default.
        with self.assertRaises(aiohttp.ServerFingerprintMismatch) as ctx:
            self._connect_via_proxy(
                Fingerprint(_PEER_FINGERPRINT),
                request_ssl=Fingerprint(_OTHER_FINGERPRINT),
            )
        self.assertEqual(ctx.exception.expected, _OTHER_FINGERPRINT)
        self.assertEqual(ctx.exception.got, _PEER_FINGERPRINT)

    def test_https_connect_fingerprint_match_request_ssl(self) -> None:
        # ssl= given with the request overrides the connector's default.
        proto = self._connect_via_proxy(
            Fingerprint(_OTHER_FINGERPRINT),
            request_ssl=Fingerprint(_PEER_FINGERPRINT),
        )
        self.assertTrue(proto.is_connected())
```

**哪里是真实行为，哪里是替身**：
- **真实的**：指纹只经公开的 `ssl=` 参数配置；连接器、代理 CONNECT 流程和 `Fingerprint.check` 全部是真实代码。
- **替身的**，只替换网络：
  - 代理那一跳是明文 TCP，没有 `sslcontext`，所以对它调 `check` 与真实情况一样是空操作；
  - `start_tls` 返回的 transport 像真实 TLS transport 一样提供 `sslcontext`、`ssl_object`、`peername`；
  - 两个替身都支持 `close`、`abort`、`is_closing`。
- **不断言的**：怎样关闭 transport、是否登记 cleanup、异常里的 host/port。
- **保留**：`cleanup` 为 True / False 两遍的循环，与原测试一致。
- **沿用的原有约束**：测试入口仍是 `connector._create_connection()`，与原测试及同文件其它代理测试相同。把校验放到更高一层 `connect()` 的实现测不到，但原测试同样如此，不是本次新增的约束。

**正反例分布**：连接器级、请求级各有一个正例和一个反例。
- 请求级的两例故意把连接器级设成相反的值，所以同时检验"请求值覆盖连接器默认值"。
- 反例还核对 `expected` / `got`（文档 `client_advanced.rst:517-523`），确认比较的是服务器证书的真实摘要。

## 5. 期望映射逐键变化

- `TestProxy.test_https_connect_fingerprint_mismatch`：仍是 PASSED，但测试内容已重写。
- 其余 17 个回归键：不变，全部 PASSED。
- 新增 3 键，均为 PASSED：
  - `TestProxy.test_https_connect_fingerprint_match`
  - `TestProxy.test_https_connect_fingerprint_mismatch_request_ssl`
  - `TestProxy.test_https_connect_fingerprint_match_request_ssl`
- 合计 21 键，完整映射见 `revision_draft.json`。
- **版本记录**：

  | 文件 | sha256 前 8 位 |
  | --- | --- |
  | 父版本 `test_1.py` | `987f9118` |
  | 父版本 `expected_output.json` | `351982fc` |
  | 修订后 `test_1.py` | `ff4bf0d8` |
  | 试跑用 `draft.json` | `20994e57` |
  | 试跑用 `expected_after.json` | `65e732be` |

  父版本隐藏测试树摘要为 `80d242d6…`。

## 6. 验收计划与试跑结果

**试跑环境**：
- 派生镜像 `sha256:776103467719…`，配方 `r2e_derive_v1+sysconfig_v1`；
- 工具 `rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`，只作试跑；
- 各候选 `git apply` 均成功，草案均报 `RH2_TRIAL_EDITS_APPLIED=1`。

**环境确认**（当前材料）：noop 只在目标键失败（`trials/env_noop_current.json`）；gold 18/18（`trials/env_gold_current.json`）。

**修订草案下的验收**：

| 候选 | 补丁 | 应得 | 应失败的键 | 试跑结果 | 当前材料 |
| --- | --- | --- | --- | --- | --- |
| gold（正对照） | `PRIV/gold.patch` | 1 | — | 1，21/21 | 1 |
| noop | 无 | 0 | 两个反例键 | 0，恰好 `…_mismatch`、`…_mismatch_request_ssl` | 0 |
| K3（已知错误：校验原始代理 transport） | `runs/r2e_actor_20260925/grader_cands/aiohttp_22a1_K3_check_raw_proxy_transport.patch` | 0 | 两个反例键 | 0，恰好这两键 | **1**（`trials/cur_K3.json`） |
| K4（已知错误：一律拒绝） | `…/grader_cands/aiohttp_22a1_K4_reject_any_fingerprint.patch` | 0 | 两个正例键，加两个反例键（`expected`/`got` 为空） | 0，恰好这 4 键 | **1**（`trials/cur_K4.json`） |
| K1（合理替代：在 `_create_proxy_connection` 里校验 TLS transport） | `…/grader_cands/aiohttp_22a1_K1_check_tls_transport_in_proxy_path.patch` | 1 | — | 1，21/21 | 1（历史） |
| K2（原误拒：不经 `_get_fingerprint`） | `…/grader_cands/aiohttp_22a1_K2_fingerprint_without_helper.patch` | 1 | — | 1，21/21 | **0**（`trials/cur_K2.json`） |
| RC（原误拒：不匹配时 `abort()`） | `…/grader_cands/aiohttp_22a1_RC_gold_but_abort.patch` | 1 | — | 1，21/21 | **0**（`trials/cur_RC.json`） |
| IC（替代写法：`if not is_closing(): close()`） | `cands/aiohttp_22a1_IC_gold_but_is_closing_close.patch` | 1 | — | 1，21/21 | 未跑 |

- 修订版每行的结果文件是 `trials/rev_<候选>.json`。
- **与真实握手对照一致**：修订后的判分与私有真实握手对照（`…/r2e_static_review_batch2_20260925/grader_candidates.md:224-228`）对每个已知候选都给出相同结论。
- **IC 为什么补跑**：它是复核 `review.md:121` 建议补的变体，确认替身不会再因 `is_closing()` 未实现而误拒。
- **失败原因从哪里判断**：试跑结果里的日志尾部被 pytest-cov 的覆盖率表占满，没有保留逐条断言信息。各候选失败在哪个断言，是从失败键的分布推出来的：
  - 同一条路径在 K3 的正例键里通过，所以 K3 在反例键上只能是"没有抛异常"；
  - K4 在正例键上一定会抛异常。

  正式评分的完整日志可以再确认一次。

## 7. 修订后仍受保护的公开要求

- **经 HTTP 代理访问 HTTPS 时，指纹不符要抛 `ServerFingerprintMismatch`**：两个反例键，连接器级与请求级各一。
- **指纹正确时照常连通**：两个正例键。这是 base 原有的合理行为，挡住"一律拒绝"。
- **请求级 `ssl=` 覆盖连接器默认值**：两个请求级键。
- **异常携带配置的指纹与证书的真实摘要**：反例键的 `expected` / `got` 断言。
- **代理请求的构造、`start_tls` 参数与错误分支**：原 17 个回归键不变。
- **未覆盖，登记为 T3**：
  - 不匹配后是否关闭或登记 transport（泄漏不被发现）；
  - HTTPS 代理那一跳；
  - `_wrap_existing_connection` 路径；
  - 不同 TLS 实现下的真实握手。私有对照脚本 devcheck `pr4_7_cmd` 仍可作探针判读的补充。

## 8. 边界与交接

- **只做 R-e，以及其中非示例实例的 R-c 成分，没有改题面。**
- **题面问题仍待处理**：示例用 21 字符的 `str` 作 `fingerprint=`，构造时就抛 `ValueError`；题面也没提代理这一触发条件（卡片 §4 问题 1）。这属于 P4 / P2 类题面问题，不在本包的模板授权里，照旧登记；是否另出 R-f 由协调者安排。
- **协调者待办**：
  1. 把 `revision_draft.json` 的 `revisions` 落为正式修订单；
  2. 重建材料；
  3. 按本表至少跑 gold、noop、K2、K3、K4、RC 的正式评分；
  4. 送 Codex 复核。

  本方案没有写 `s2_r2e` 下的正式材料，也没有改生产代码。
