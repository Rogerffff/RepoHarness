# aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac 审查卡（静态）

## 1. 目标、版本与建议用途

- **目标**：通过 HTTP 代理（`CONNECT`）访问 HTTPS 时，如果配置的服务器指纹不匹配，应抛 `aiohttp.ServerFingerprintMismatch`，而不是照常连通。
- **版本**：base `354153e9b706`（aiohttp 3.11.0.dev0，Python 3.9.21，pytest 8.3.3），派生镜像 `r2e_derive_v1`，本题没有材料修订。
- **建议用途**：可以作开发诊断，但结论要带两条限制。
  1. 题面误导：示例是直连，还用了一个 21 字符的 `str` 指纹，在 base 上构造时就抛 `ValueError`；直连路径本来就会校验。缺陷只在代理路径上，题面没提。
  2. 目标键只检查 mock 交互，reward=1 不能证明修复有效。

  暂不作评测题。

## 2. 关键映射

| 需求或旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖 | 执行证据或下一步验证 |
| --- | --- | --- | --- | --- |
| 经代理访问 HTTPS 时，指纹不符要抛 `ServerFingerprintMismatch` | 题面 L7/L26/L30（没提代理）；`connector.py:1379-1466` 缺少检查调用 | `TestProxy.test_https_connect_fingerprint_mismatch` / `assertRaises`；`_get_fingerprint` 与 `check` 都被 mock | **部分**：不检查被校验的是哪个 transport | noop 报 "not raised"；gold 对照 C4 抛出异常；**K3 待跑** |
| 经代理 + 正确指纹仍能连通 | 合理旧行为 | 无 | **缺失** | gold 对照 C4 显示 CONNECTED；K4 待跑 |
| 请求级指纹优先于连接器级，两者都要生效 | `_get_fingerprint`（`connector.py:1046-1053`） | 被 mock 掉 | **缺失** | gold 对照 C4 两种都覆盖 |
| 代理请求的构造、`start_tls` 实参、错误分支保持不变 | 公开 `tests/test_proxy.py` | 17 个回归键（整份公开文件） | 覆盖 | gold 18/18 ×2；base 公开跑 17 passed |
| `Fingerprint` 构造契约、直连校验 | 公开 `test_client_fingerprint.py`、`test_connector.py` | 不在隐藏集里 | 缺失（公开测试可用） | devcheck 在 base 上：12 passed、10 passed |

## 3. 八方面已查 / 未查

- **公开需求**：静态渲染和示例的两处错误已查（执行证据）；模型实际收到的消息没有捕获。
- **材料与初态**：已查。隐藏测试树摘要一致，gold 可干净应用；初态缺陷由 agent 身份运行 C4 实测确认。
- **测试是否测到要求**：隐藏测试全部读完，并与公开文件 diff。目标键是 mock 交互测试（见 §4 问题 2）。
- **误拒合理解**：检查点放在哪一层都能过。唯一的硬约束是必须经 `self._get_fingerprint(...)` 取指纹、调用 `.check(...)`（K2 待跑）。
- **回归与 gold**：gold 在可达路径上是正确的。以下几点未覆盖，也都不在测试里：`_wrap_existing_connection`（本环境不可达）；`https://` 代理那一跳；异常里的 host/port 取的是代理地址；`isinstance(asyncio.Transport)` 守卫在非标准 transport 上会放行而不校验（未核实）。
- **开发条件**：devcheck 在正式启动路径下以 agent 身份实测了导入、依赖（trustme、proxy.py、pytest-cov）、四组公开测试和离线复现。真实模型求解待验。
- **交付与评分**：修复文件是非测试源码；preflight 三项都是 ok；没有泄漏。非 gold 候选的完整交付链没有实跑。`aiohttp.pytest_plugin` 这类候选可改的包代码是同仓共有通道，未验证。
- **题目关系**：本题在池内同仓 5 题里 base 最新，本题修复不在其它题的初态里。反过来，本题初态包含 `1c1c0ea3` 的修复，以及 `4075c653`、`240da100` 的测试名，影响的是那几题的暴露面，需要登记。上游答案是否可达没有查（actor 不联网）。

## 4. 具体问题与证据层次

1. **题面误导且欠明确**（清单 3、23）。示例抛 `ValueError`，直连已经会校验（执行证据：devcheck `pr2_2`、`pr3_6`）；代理路径才有缺陷（执行证据：base 上 C4 `proxy+bad_fp -> CONNECTED`）。公开读者靠读代码推出了代理路径，所以可以推知，但照题面复现会得出"base 没问题"。与历史结论一致。
2. **目标键会误收未修复的实现**（清单 25、32）。测试把 `connector._get_fingerprint` 换成返回 Mock，把 `check` 设成直接抛异常，所以"对原始代理 TCP transport 调 `check`"也能通过。而真实的 `Fingerprint.check` 遇到非 TLS transport 会直接 return（`client_reqrep.py:139-141`），这种实现在现实中是空操作。**静态推断，K3 待实跑。** 历史没有审查过这一点。
3. **正例缺失**（清单 26）。"经代理 + 正确指纹仍能连通"没有测试保护，一律拒绝的实现（K4）也会通过。静态推断。
4. **mock 耦合**（清单 24，可能性较低）。语义等价、但没经过 `_get_fingerprint` 取指纹的实现（K2）会判 0。静态推断。
5. 环境：没有需要修的地方。历史的环境资格（`environment_qualified`）经本次新证据全部确认。唯一的解题侧条件是须把 `/testbed` 放进 sys.path，v3 环境说明已经写入。

## 5. 静态建议与下一步

**处置：`needs_review`**。理由有两层：一是静态候选待 actor 验证；二是测试标准偏弱，需要先实跑 K3，再决定是否修订。

**唯一优先的下一步**：用正式评分代码实跑 K1–K3（K4 可选），并在私有容器里对同样的代码状态跑 C4 行为核对。

**请协调者实跑的候选**。补丁全文在附录 A，都已在 base `connector.py`（blob `6bc3ee54`）上 `git apply --check` 通过，改后文件能正常解析：

- **K1，合理替代（正对照）**：在 `aiohttp/connector.py::_create_proxy_connection` 里，把 `return await self._start_tls_connection(transport, req=req, timeout=timeout)` 改成先接收 `tls_transport, tls_proto`，然后 `fp = self._get_fingerprint(req)`；如果 `fp` 为真就执行 `fp.check(tls_transport)`，捕获 `ServerFingerprintMismatch` 后关闭 transport、在 cleanup 启用时登记、再抛出；最后返回二元组。**预期 reward 1，没有不符的键。**
- **K2，语义等价但 mock 耦合**：位置与 gold 相同（`_start_tls_connection` 里 `start_tls` 之后），但指纹改成直接取：`req.ssl` 是 `Fingerprint` 就用它，否则 `self._ssl` 是 `Fingerprint` 就用它，都不是则为 `None`。其余与 gold 一致。**预期 reward 0，不符键 `TestProxy.test_https_connect_fingerprint_mismatch`（FAILED，"not raised"）。**
- **K3，错误修复（负对照，关键）**：在 `aiohttp/connector.py::_create_proxy_connection` 里，`transport, proto = await self._create_direct_connection(proxy_req, …)` 之后紧接着加 `fp = self._get_fingerprint(req)`；如果 `req.is_ssl() and fp` 就执行 `fp.check(transport)`，也就是去校验连到代理的原始 TCP transport。**预期 reward 1（误收），没有不符的键。**
- **K4，过度拒绝（次要负对照）**：在 `_start_tls_connection` 里 `start_tls` 之后加：只要 `self._get_fingerprint(req)` 为真，就关闭 transport，并 `raise ServerFingerprintMismatch(b"", b"", req.host, req.port)`，不做任何比较。**预期 reward 1（误收），没有不符的键。**
- noop、gold 的现有结果（0 与 1）就是基线对照，不必重跑。

**私有容器行为核对（区分 K3 与 gold）**：用与 `private_gold` 相同的做法，即同一派生镜像的一次性私有容器，root 身份，不联网。在 `/testbed` 上分别应用 K1、K2、K3、K4（每次都从 base 开始，`git apply`），然后运行 devcheck 已有的命令 `pr4_7_cmd`：也就是公开读者的 C4 脚本，原文在 `runs/r2e_actor_20260925/devcheck/aiohttp__22a12cc2e2ef289d9e96fd87dfc1727/orig/commands_with_preflight.json` 中 `id=pr4_7_cmd` 的 `cmd`，在 `cd /testbed` 下执行。预期输出如下（`SFM` 指 `ServerFingerprintMismatch`；base 与 gold 两行是已观测的结果）：

| 代码状态 | direct+bad_fp | proxy+good_fp | proxy+bad_fp | proxy+bad_fp_per_request |
| --- | --- | --- | --- | --- |
| base（已观测） | SFM got_is_cert=True | CONNECTED 200 | CONNECTED 200 | CONNECTED 200 |
| gold（已观测） | SFM got_is_cert=True | CONNECTED 200 | SFM got_is_cert=True（port=代理端口） | SFM got_is_cert=True |
| K1 | 同 gold | 同 gold | 同 gold | 同 gold |
| K2 | 同 gold | 同 gold | 同 gold | 同 gold |
| **K3** | **同 base** | **同 base** | **CONNECTED 200** | **CONNECTED 200** |
| K4 | SFM got_is_cert=True | **SFM got_is_cert=False** | SFM got_is_cert=False | SFM got_is_cert=False |

判读：如果 K3 的 reward 是 1，而 C4 仍然显示 CONNECTED，问题 2 就坐实了。如果 K2 的 reward 是 0，而 C4 与 gold 相同，问题 4 就坐实了。

**修订建议（进建议队列，属于测试标准与公开规格的变更，需要用户决定）**：
1. 目标测试改用真实的 `Fingerprint`，并让 `TransportMock` 提供 `sslcontext`、`ssl_object.getpeercert(binary_form=True)`、`peername` 这些 extras，使校验错 transport 的实现（K3）失败；同时加一个正确指纹经代理照常返回的正例（挡住 K4）。修订后要用 gold、K1、K2、K3、K4 重新核对。
2. 题面补上触发条件"通过 HTTP 代理（CONNECT）访问 HTTPS"，并把示例改成 `ssl=aiohttp.Fingerprint(<32 字节>)`。只补题面，不能解决问题 2。

如果不修订，开发诊断时应标注：reward=1 可能是 K3 类的误收；reward=0 中可能混有被示例误导的轨迹（改了构造器，或判断无需修改）。

## 附录 A：候选补丁（相对 base `aiohttp/connector.py`）

K1：
```diff
--- a/aiohttp/connector.py
+++ b/aiohttp/connector.py
@@ -1457,13 +1457,23 @@ class TCPConnector(BaseConnector):
                         req=req,
                     )
 
-                return await self._start_tls_connection(
+                tls_transport, tls_proto = await self._start_tls_connection(
                     # Access the old transport for the last time before it's
                     # closed and forgotten forever:
                     transport,
                     req=req,
                     timeout=timeout,
                 )
+                fingerprint = self._get_fingerprint(req)
+                if fingerprint:
+                    try:
+                        fingerprint.check(tls_transport)
+                    except ServerFingerprintMismatch:
+                        tls_transport.close()
+                        if not self._cleanup_closed_disabled:
+                            self._cleanup_closed_transports.append(tls_transport)
+                        raise
+                return tls_transport, tls_proto
             finally:
                 proxy_resp.close()
```

K2：
```diff
--- a/aiohttp/connector.py
+++ b/aiohttp/connector.py
@@ -1217,6 +1217,20 @@ class TCPConnector(BaseConnector):
                     # chance to do this:
                     underlying_transport.close()
                     raise
+                if isinstance(tls_transport, asyncio.Transport):
+                    fingerprint = (
+                        req.ssl
+                        if isinstance(req.ssl, Fingerprint)
+                        else self._ssl if isinstance(self._ssl, Fingerprint) else None
+                    )
+                    if fingerprint:
+                        try:
+                            fingerprint.check(tls_transport)
+                        except ServerFingerprintMismatch:
+                            tls_transport.close()
+                            if not self._cleanup_closed_disabled:
+                                self._cleanup_closed_transports.append(tls_transport)
+                            raise
         except cert_errors as exc:
             raise ClientConnectorCertificateError(req.connection_key, exc) from exc
         except ssl_errors as exc:
```

K3：
```diff
--- a/aiohttp/connector.py
+++ b/aiohttp/connector.py
@@ -1369,6 +1369,10 @@ class TCPConnector(BaseConnector):
             proxy_req, [], timeout, client_error=ClientProxyConnectionError
         )
 
+        fingerprint = self._get_fingerprint(req)
+        if req.is_ssl() and fingerprint:
+            fingerprint.check(transport)
+
         auth = proxy_req.headers.pop(hdrs.AUTHORIZATION, None)
         if auth is not None:
             if not req.is_ssl():
```

K4：
```diff
--- a/aiohttp/connector.py
+++ b/aiohttp/connector.py
@@ -1217,6 +1217,9 @@ class TCPConnector(BaseConnector):
                     # chance to do this:
                     underlying_transport.close()
                     raise
+                if self._get_fingerprint(req):
+                    tls_transport.close()
+                    raise ServerFingerprintMismatch(b"", b"", req.host, req.port)
         except cert_errors as exc:
             raise ClientConnectorCertificateError(req.connection_key, exc) from exc
         except ssl_errors as exc:
```

预测依据：
- 在回归测试里，`_get_fingerprint(req)` 都返回 `None`（没有配置指纹），所以 K1–K4 都不会改变那 17 个键。
- 在目标测试里，`_get_fingerprint` 对任何参数都返回 Mock，`check` 对任何 transport 都抛异常。所以只要有代码"经 helper 取到指纹并调用 check 或直接 raise"就会通过（K1、K3、K4），不经 helper 就不会通过（K2）。

## 附录 B：主要证据

- 当前 noop/gold 日志：`runs/r2e_env_repair_20260924/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_{306d8c84,b98f2211}.eval.log`；R-f：`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-{noop-a_f456eb30,gold-a_11caaf09}.eval.log`。
- devcheck：`runs/r2e_actor_20260925/devcheck/aiohttp__22a12cc2e2ef289d9e96fd87dfc1727/orig/captures/{env,pr0_1_pytest,pr2_2_cmd,pr3_*_pytest,pr4_7_cmd}.out`；gold 对照在 `…/private_gold/private_control.json`。
- 镜像身份：评分用的是 `sha256:dfd6021f…`，devcheck 与对照用的是 `sha256:2b571f22…`。两者 tag 与配方相同、重建后 ID 不同，版本事实一致，没有逐层比对。
- 分析全文：`analysis_before_history.md`；与历史结论的差异：`old_findings_delta.md`。
