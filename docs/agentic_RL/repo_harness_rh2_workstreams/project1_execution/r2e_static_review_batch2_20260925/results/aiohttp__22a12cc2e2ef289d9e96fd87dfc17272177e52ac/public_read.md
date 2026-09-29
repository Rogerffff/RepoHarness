# 公开读者报告：aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac

- 角色：R2E 公开读者，做静态审查，不解题，也不给通过或淘汰标签。日期 2026-09-25。
- 材料：只读了角色卡和 `PUBLIC_DIR = runs/r2e_static_prep_20260924/v3/public/aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac/`。
- 路径约定：`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`worktree_manifest.json` 相对于 PUBLIC_DIR。代码和测试路径省略 `worktree/` 前缀，等同解题者在 `/testbed` 下看到的相对路径。行号按公开工作树。
- 题目：`aiohttp`，base 提交 `354153e9b706`（`aiohttp/__init__.py:1` 的版本是 `3.11.0.dev0`）。题面标题是 "Server Fingerprint Mismatch Not Properly Handled in HTTPS Connections"（`user_prompt.txt:5`）。解题环境是 Python 3.9.21（`environment_brief.md:10`）。
- 本报告没有运行任何项目代码。第 4 节的命令都是"建议，未执行"。

## 0. 要点

1. **题面示例在 base 上的现象与题面描述相反。** 执行 `aiohttp.TCPConnector(fingerprint='incorrect_fingerprint')` 时，构造函数就会抛 `ValueError("fingerprint has invalid length")`。原因是这个 `str` 长 21，不属于 16/20/32 字节这几种摘要长度（调用链：`aiohttp/connector.py:836` → `aiohttp/client_reqrep.py:190-202` → `aiohttp/client_reqrep.py:126-129`）。异常发生在任何网络 I/O 之前，所以题面说的 "No exception is raised"（`user_prompt.txt:30`）不成立。
2. **直连 HTTPS 时，指纹不匹配在 base 上已经会抛 `ServerFingerprintMismatch`**（`aiohttp/connector.py:1326-1343`）。公开功能测试 `tests/test_client_functional.py:626-648` 用真实 TLS 断言了这一点。
3. **base 上真正"配置了指纹却不校验、照常连通"的，是经 HTTP 代理 `CONNECT` 之后再升级 TLS 的路径。** `_create_proxy_connection`（`aiohttp/connector.py:1345-1470`）会走 `_start_tls_connection`（`1187-1247`）或 `_wrap_existing_connection`（`1085-1105`），这两处都不检查指纹。这符合题面的 "Actual Behavior"，但题面完全没提代理。
4. **最关键的未知是隐藏测试针对哪条路径、从哪一层观察。** 题面没写触发条件，解题者只能靠读代码推断。如果隐藏测试针对的不是代理路径，第 3 点的推断就不成立。

## 1. 需求表

类别含义：
- **明示**：题面直接写出。
- **接口/测试**：受现有代码接口或公开测试约束。
- **推知**：可以从公开仓库合理推出。
- **多解**：仍有多种合理解释。

| # | 行为 | 改变 / 保留 | 类别 | 依据 |
|---|---|---|---|---|
| R1 | 配置了指纹的 HTTPS 连接，如果服务器证书（DER 编码）的摘要与期望值不符，应抛 `aiohttp.ServerFingerprintMismatch`，而且不能把这条连接交给请求使用 | 改变（至少覆盖尚未校验的路径） | 明示 | `user_prompt.txt:7,26,30` |
| R2 | 具体需要补哪条建连路径 | — | 多解；代码给出一个候选 | 题面只给了直连示例（`user_prompt.txt:16-18`）；直连已经校验（`aiohttp/connector.py:1278-1279,1326-1343`）；没有校验的是代理 CONNECT 后的 TLS 升级（`aiohttp/connector.py:1379-1466`） |
| R3 | 两种配置入口都要生效：连接器级 `TCPConnector(ssl=Fingerprint(...))`（包括已弃用的 `fingerprint=`）和请求级 `session.get(..., ssl=Fingerprint(...))`，请求级优先 | 保留，并应延伸到新路径 | 推知 | `aiohttp/connector.py:1046-1053`（先看请求，再看连接器）；`docs/client_advanced.rst:536-538`；`aiohttp/client.py:480-482,499` |
| R4 | 异常携带 `expected`、`got`、`host`、`port` 四个字段，可以 pickle，`repr` 格式固定 | 保留 | 接口/测试 | `aiohttp/client_exceptions.py:267-280`；`tests/test_client_exceptions.py:268-297` |
| R5 | 代理路径上，异常里的 `host`/`port` 应该是代理地址还是目标站地址 | — | 多解 | 直连时取 transport 的 `peername`（`aiohttp/client_reqrep.py:146-147`）；经代理时，同样取法拿到的是代理地址（推断）；题面没有约定 |
| R6 | 直连多地址回退：某个地址指纹不符就关闭连接、换下一个地址，全部失败后才抛最后一个异常 | 保留 | 接口/测试 | `aiohttp/connector.py:1326-1343`；`tests/test_connector.py:603-747`（ip4 指纹不符，ip5 连通） |
| R7 | `Fingerprint` 构造契约：只接受 32 字节的 sha256；16/20 字节（md5/sha1）和其它长度都抛 `ValueError` | 保留 | 接口/测试 | `aiohttp/client_reqrep.py:118-133`；`tests/test_client_request.py:1367-1379`；`tests/test_client_fingerprint.py:18-27`；`tests/test_connector.py:1508-1519` |
| R8 | `Fingerprint.check` 遇到非 TLS transport（`get_extra_info("sslcontext")` 为假）时直接返回 `None` | 保留 | 接口/测试 | `aiohttp/client_reqrep.py:139-141`；`tests/test_client_fingerprint.py:30-35` |
| R9 | `_merge_ssl_params`：传 `fingerprint=` 时先发 `DeprecationWarning`，再转成 `Fingerprint`；它与 `verify_ssl`/`ssl_context`/`ssl` 互斥 | 保留 | 接口/测试 | `aiohttp/client_reqrep.py:156-208`；`tests/test_client_fingerprint.py:38-86` |
| R10 | 配置指纹时使用不校验证书链的 `_SSL_CONTEXT_UNVERIFIED`，指纹是唯一的校验。没配置指纹时，代理路径的 `start_tls` 使用 `_SSL_CONTEXT_VERIFIED` 和目标站的 `server_hostname` | 保留 | 接口/测试 | `aiohttp/connector.py:1013-1044`；`tests/test_connector.py:1583-1589`；`tests/test_proxy.py:765-824` |
| R11 | 指纹正确时照常连通 | 保留 | 接口/测试 | `tests/test_client_functional.py:605-623`（直连） |
| R12 | 示例里 21 个字符的 `str` 指纹应该得到 `ServerFingerprintMismatch` | 字面要求，与 R7 冲突 | 多解（字面读法与公开测试矛盾） | `user_prompt.txt:16,26`，对照 `tests/test_client_request.py:1367-1369` |
| R13 | 使用 `https://` 代理时，base 会把给目标站的指纹拿去校验代理自己的证书。原因有三：`proxy_req` 继承了 `req.ssl`（`aiohttp/connector.py:1358-1365`）；`_get_fingerprint` 会回退到连接器的 `_ssl`；代理 URL 是 https 时，`1326` 行的条件成立。修复后这一跳是否继续校验，没有约定 | — | 多解；本环境无法端到端验证 | SSLContext 两跳共用的先例：`docs/client_advanced.rst:608-615`、`tests/test_proxy_functional.py:115`。TLS-in-TLS 需要 Python 3.11+：`tests/test_proxy_functional.py:19`、`aiohttp/connector.py:1150-1185` |
| R14 | 指纹不匹配时，是否关闭 transport、是否登记到 `_cleanup_closed_transports`、代理路径是否"换地址重试" | — | 多解 | 题面只说 "preventing the connection from being established"（`user_prompt.txt:26`）；直连的现成做法是关闭并登记（`aiohttp/connector.py:1329-1338`） |

## 2. 合理实现范围

**检查放在哪一层。** 下面四种放法对 `session.get(...)` 和 `connector.connect(...)` 的外部行为是等价的，都应该接受：

1. 放在 `_start_tls_connection` 里，`start_tls` 返回之后、交出 transport 之前。
2. 放在 `_create_proxy_connection` 拿到升级后的 transport 时。
3. 放在 `_create_connection`（`aiohttp/connector.py:999-1011`），对直连和代理两条分支统一检查。这时要避免直连路径被重复检查。
4. 抽出一个公共 helper，让直连和代理路径共用。

如果把检查放到 `ClientSession` 层（也就是 `connect` 之后），就不符合题面 "the connector should raise" 的说法。而且以 `connector._create_connection` 或 `connector.connect` 为入口的测试也看不到这个检查：`tests/test_proxy.py` 里有 10 处直接调用 `connector._create_connection(...)`。

**其它自由度**

- `_wrap_existing_connection` 分支（事件循环没有 `start_tls` 时走这里，`aiohttp/connector.py:1448-1458`）：Python 3.7 起 asyncio 都有 `loop.start_tls`，所以本环境的 3.9.21 走不到这一分支。一并覆盖更完整，但本环境区分不出有没有覆盖。
- 异常类型：应该用已有的 `aiohttp.ServerFingerprintMismatch`（`aiohttp/__init__.py:39,158` 已导出），不需要新增公开名称。包装成 `ClientConnectorError` 等其它类型不符合题面。
- `host`/`port` 的取值（R5）、是否登记 cleanup、代理路径是否做地址重试（R14）、`https://` 代理那一跳怎么处理（R13）：题面都没有约定，不同选择都应接受。
- 命名、输出格式、默认行为：没有新的约定。没配置指纹时，行为不应改变。
- 变更记录：仓库惯例是在 `CHANGES/` 放一个片段（见 `CHANGES/README.rst`），但这不是功能要求。

**与公开测试冲突的做法。** 以下只是提示解题风险，不是在猜标准答案：

- 为了迎合示例而放宽 `Fingerprint` 的构造（接受 `str` 或任意长度）：与 R7 的公开测试冲突。
- 去掉 `Fingerprint.check` 对非 TLS transport 的提前返回：与 `tests/test_client_fingerprint.py:30-35` 冲突。
- 没配置指纹时也去读 TLS transport 的证书：`tests/test_proxy.py` 用 `mock.Mock()` 充当 TLS transport（第 290、359、426、806、882 行），这时 `getpeercert` 会返回一个 Mock，拿它算哈希会抛 `TypeError`（推断）。
- 指纹不匹配时不关闭升级后的 TLS transport：`setup.cfg:143-144` 设了 `filterwarnings = error`，遗留的 transport 可能以 `ResourceWarning` 或 unraisable 警告的形式让测试失败（推断，未验证）。

不修改 connector 的建连路径，就没法让"经代理的错误指纹"报错。我想不出这样的合理实现。

## 3. 题面质量与初态线索

### 3.1 题面是否直接给出或暗示了修法

没有。题面没提代理、`CONNECT`、`start_tls` 或任何内部函数，示例也不是修好后的实现。它的问题是信息不足、示例不成立，而不是泄漏了修法。

### 3.2 题面描述的行为能否从 base 源码读出

| 场景 | base 上的实际行为 | 与题面是否一致 |
|---|---|---|
| 原样运行题面示例（`user_prompt.txt:11-22`） | 构造 `TCPConnector` 时先发 `DeprecationWarning`（`aiohttp/client_reqrep.py:191-195`），再抛 `ValueError("fingerprint has invalid length")`（`aiohttp/client_reqrep.py:126-129`），根本不会发起连接。即使有外网也一样 | 不一致：题面说无异常、连接成功 |
| 直连 HTTPS，配置 32 字节的错误指纹 | TLS 建立后，`_create_direct_connection` 调用 `fingerprint.check(transp)`；不匹配就关闭连接、换下一个地址，最后抛 `ServerFingerprintMismatch`（`aiohttp/connector.py:1326-1343`）。公开测试 `tests/test_client_functional.py:626-648` 断言了这个行为 | 不一致：base 已经是正确行为 |
| 经 `http://` 代理访问 HTTPS，配置错误指纹 | 代理这一跳的 `proxy_req` 指向 http 地址，`proxy_req.is_ssl()` 为假，所以第 1326 行不做检查。`CONNECT` 成功后走 `_start_tls_connection`（`1460-1466` → `1187-1247`），这里只调用 `start_tls`，也不检查指纹 | 一致：连接照常建立。但题面没提代理 |

### 3.3 示例在 base 接口下是否说得通

- 类型不符：示例传的是 `str`，接口和文档都声明为 `bytes`（`aiohttp/connector.py:808`；`docs/client_reference.rst:1070`）。
- 示例用的是已弃用的参数 `fingerprint=`（`aiohttp/client_reqrep.py:190-195`；`docs/client_reference.rst:1077-1079`），推荐写法是 `ssl=aiohttp.Fingerprint(digest)`（`docs/client_reference.rst:2006-2024`）。
- 期望行为与构造契约冲突（见 R12），按字面实现会破坏公开测试。
- 示例依赖外网 `https://example.com`（`user_prompt.txt:18`），而解题环境没有外网（`environment_brief.md:11`、`public_bundle.json:15`）。
- 推断：这个示例像是按"错误指纹"的概念泛泛写成，没有对照 base 接口核对过。
- 旁证：仓库自带文档里的指纹示例同样跑不通。`docs/client_advanced.rst:512` 的 `b'0'*64` 是 64 字节，构造时就会抛 `ValueError`；第 517 行的 `aiohttp.FingerprintMismatch` 在包里不存在，实际名称是 `ServerFingerprintMismatch`。解题者参考这段文档会被误导，但它不是本题要修的对象。

### 3.4 能否定位调查入口；哪些缺失会真正阻碍开发

- **能定位，属于正常读代码的工作量。** 在 `aiohttp/` 里搜 `fingerprint`，会找到 `Fingerprint` 类（`aiohttp/client_reqrep.py:118-147`）和唯一的检查调用点（`aiohttp/connector.py:1326-1338`）。再对照 `_create_connection`（`999-1011`）的两条分支，就能看出代理分支没有调用点。沿调用链阅读、理解 `_get_fingerprint` 的优先级，都是正常工作量。
- **真正的阻碍：**
  1. 题面缺少触发条件，示例还会误导人。照示例复现，得到的是 `ValueError`；照"直连 + 32 字节错误指纹"复现，得到的是已经正确的 `ServerFingerprintMismatch`。两种结果都和 "Actual Behavior" 相反。解题者可能因此判断"无需修改"，也可能去改构造器，从而破坏公开测试。
  2. 没有外网，只能自建回环 HTTPS 源站和 `CONNECT` 代理来复现（见第 4 节 C4）。
  3. 修复后代理路径上异常字段的含义（R5）和 `https://` 代理那一跳的处理（R13）都没有约定。
  4. 从公开材料无法判断隐藏测试走的是哪条路径。

### 3.5 `public_hints` 的三类内容（`public_bundle.json:15`）

| 类别 | 内容 | 对合法解法的影响 |
|---|---|---|
| 题目需求 | 修复一个真实 issue；找到根因；只改非测试源码 | 与题面一致 |
| 给解题者的操作指令 | 不改仓库测试文件；测试范围保持窄；在 `/testbed` 用 `python -m pytest`；完成后写简短总结并停止调用工具 | 回归测试只能写成仓库测试目录之外的临时脚本，不影响合法修复 |
| 环境事实声明 | `.venv` 已就绪，`python` 和测试工具都指向它；无网络；`pip` 可能不可用；判分用另一套测试 | 无网络直接导致题面示例无法原样运行。`environment_brief.md:13` 说包没装进 venv、裸 `pytest` 收集会失败，所以 "test tools already point at it" 的说法偏乐观；但提示同时要求用 `python -m pytest`，影响不大。`environment_brief.md:11` 说 pip 在但装不了新包，与 "may be unavailable" 方向一致 |

### 3.6 初态线索（与题意关系不大，备查）

- `run_tests.sh` 的内容是 `.venv/bin/python -W ignore -m pytest -rA r2e_tests`。`r2e_tests` 不在工作树里（是隐藏测试），解题者跑不了这条判分命令。
- `setup.cfg:123-174` 的 pytest 配置：`addopts` 里有 `--cov=aiohttp --cov=tests/`（需要 pytest-cov），另有 `filterwarnings = error` 和 `xfail_strict = true`。
- 初态改动只有 `Makefile`（manifest 的 `initial_diff` 记为 modified；diff 本身在 PUBLIC_DIR 之外，没有读）。当前 `Makefile` 是构建和安装配方（含 `uv pip install`，`Makefile:50,53,77,92,173`），与题意无关。
- 镜像里另有两个未跟踪文件 `install.sh` 和 `process_aiohttp_updateasyncio.py`，不在公开工作树里（manifest 的 `untracked_missing`），我没读到。解题者在 `/testbed` 能看到它们。
- `vendor/llhttp` 是未检出的子模块空目录，编译扩展也不在工作树里。aiohttp 缺少 C 扩展时会回退到纯 Python 实现（`aiohttp/helpers.py:75` 的 `NO_EXTENSIONS`，以及各模块的 `ImportError` 回退），与本题无关。
- `examples/server.crt` 和 `examples/server.key` 是跟踪文件（权限 0644）。证书自签名，RSA 2048，签名算法 `sha256WithRSAEncryption`；私钥未加密，与证书匹配；有效期到 2026-08-05，已经过期。证书 DER 的 sha256 是 `5ac883dc65bb95222387c911418fc0aa1dceee6d795308aea7e85833b92522bc`。这些元数据是我用本机 `openssl` 读取公开文件得到的，没有运行项目代码。过期不影响指纹路径：配置指纹时客户端用 `CERT_NONE`，不检查主机名（`aiohttp/connector.py:743-762`）；服务端加载自己的证书时也不检查有效期。
- 公开测试的依赖：
  - `tests/conftest.py:20-40` 用 `trustme` 签发测试证书，缺少它时相关 fixture 会调用 `pytest.xfail`。
  - `tests/test_proxy_functional.py:10` 在模块顶层 `import proxy`（即 proxy.py），缺少它时整个文件收集失败。
  - `requirements/test.txt` 固定了 `trustme==1.1.0`、`proxy-py==2.4.8`、`pytest-cov==5.0.0`，但 `environment_brief.md` 没说 `.venv` 里实际装了哪些。

## 4. 开发需求表

| 操作 / 资产 / 服务 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 | 最小命令 |
|---|---|---|---|---|
| 从源码树导入 aiohttp | `environment_brief.md:13` | 支持（`/testbed` 在 `sys.path` 上即可） | 无 | C1 |
| 探查可选的测试依赖 | `tests/conftest.py:20-40`；`tests/test_proxy_functional.py:10`；`setup.cfg:138-139` | 没写 | 不知道 trustme、proxy.py、pytest-cov 是否已安装 | C0 |
| 确认题面示例在 base 上的真实现象 | `user_prompt.txt:11-22` | 不需要网络 | 示例依赖外网，而且在联网前就抛错 | C2 |
| 跑公开单测作为回归护栏 | `setup.cfg:123-174`；上表 R4–R11 涉及的测试 | 支持 `python -m pytest`（`environment_brief.md:13`） | 缺 pytest-cov 时 `addopts` 会报错；缺 trustme 时功能指纹测试会 xfail | C3 |
| 本地 TLS 源站证书 | `examples/server.crt`/`.key`，或 trustme | 没写 | 不知道有没有 trustme；可以用 examples 证书代替 | C4 已内置 |
| HTTP `CONNECT` 代理 | `tests/test_proxy_functional.py` 用的是 proxy.py | 没写 | 不知道有没有 proxy.py；可以用标准库自己写 | C4 已内置 |
| 外网 | 题面示例访问 `https://example.com` | 明确没有（`environment_brief.md:11`） | 示例无法原样运行 | 用 `127.0.0.1` 回环地址代替 |
| 回环 socket | 公开功能测试（`aiohttp_server`）依赖回环 | 没明说 | 如果回环不可用，功能测试和 C4 都做不了 | C4 本身就是检查 |
| 经 HTTPS 代理访问 HTTPS 目标（TLS-in-TLS） | `tests/test_proxy_functional.py:19` | Python 3.9.21 | asyncio 要 3.11+ 才支持，本环境无法端到端测试 R13 | 只能写 mock 单测 |
| C 扩展 / llhttp 构建 | `Makefile`；`vendor/llhttp` 是空目录 | 没写 | 本题不需要（有纯 Python 回退） | 无 |

以下命令都是**建议，未执行**，都能在 `/testbed` 下原样运行。

**C0：探查可选依赖**

```bash
cd /testbed && python -c "import importlib.util as u; print({m: bool(u.find_spec(m)) for m in ('trustme', 'proxy', 'pytest_cov', 'aiohappyeyeballs')})"
```

预计 `aiohappyeyeballs` 为 `True`，因为 `aiohttp/connector.py:34` 在顶层导入了它；其余几项未知。`trustme` 是否存在，决定了 C3 最后一条是 passed 还是 xfailed。

**C1：导入**

```bash
cd /testbed && python -c "import sys, aiohttp; print(sys.version.split()[0], aiohttp.__version__, aiohttp.__file__)"
```

预计输出 `3.9.21 3.11.0.dev0 /testbed/aiohttp/__init__.py`，修复前后相同。

**C2：题面示例在 base 上的真实现象（不需要网络）**

```bash
cd /testbed && PYTHONPATH=/testbed python - <<'EOF'
import asyncio, aiohttp
async def f():
    try:
        aiohttp.TCPConnector(fingerprint="incorrect_fingerprint")
    except Exception as e:
        print("RAISED", type(e).__name__, e)
    else:
        print("NO EXCEPTION at construction")
asyncio.run(f())
EOF
```

预计修复前 stdout 为 `RAISED ValueError fingerprint has invalid length`，stderr 可能多一行 `DeprecationWarning: fingerprint is deprecated, use ssl=Fingerprint(fingerprint) instead`。公开测试要求保留构造契约，只要修复遵守这一点，修复后输出不变。这条命令不能区分修复前后，只用来说明示例不成立。

**C3：公开单测回归护栏（修复前后都应通过，不能区分修复）**

```bash
cd /testbed && python -m pytest tests/test_client_fingerprint.py -q
cd /testbed && python -m pytest tests/test_connector.py -q -k "fingerprint or multiple_hosts_errors or get_ssl_context"
cd /testbed && python -m pytest tests/test_proxy.py -q
cd /testbed && python -m pytest tests/test_client_functional.py -q -k fingerprint
```

预计结果依次是：
1. 12 passed。
2. 10 passed。
3. `tests/test_proxy.py` 全部通过（共 17 个 test 定义）。
4. trustme 可用时 2 passed，不可用时 2 xfailed。

输出里还会带 `--cov` 覆盖率表和 `--durations` 列表。如果报 `unrecognized arguments: --cov=aiohttp`，说明缺 pytest-cov，在同一条命令里加 `-o addopts=""` 重跑即可。

**C4：区分修复前后。用回环 HTTPS 源站加最小 CONNECT 代理，全程只调用公开 API**

脚本只依赖标准库和仓库自带的 `examples/server.crt`、`examples/server.key`，只用 `127.0.0.1`。它依次测试四种情况：

1. 直连 + 连接器级错误指纹：对照组，base 已经正确。
2. 经代理 + 正确指纹：用来发现修过头。
3. 经代理 + 连接器级错误指纹。
4. 经代理 + 请求级错误指纹。

```bash
cd /testbed && PYTHONPATH=/testbed python - <<'EOF'
import asyncio, hashlib, ssl, sys
import aiohttp

CERT, KEY = "/testbed/examples/server.crt", "/testbed/examples/server.key"


async def origin_handler(reader, writer):
    # tiny HTTPS origin: read the request head, answer 200 "ok"
    try:
        await reader.readuntil(b"\r\n\r\n")
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
        await writer.drain()
    except Exception:
        pass
    finally:
        writer.close()


async def pipe(src, dst):
    try:
        while True:
            data = await src.read(65536)
            if not data:
                break
            dst.write(data)
            await dst.drain()
    except Exception:
        pass
    finally:
        dst.close()


async def proxy_handler(reader, writer):
    # tiny HTTP CONNECT proxy: answer 200, then relay raw bytes both ways (no TLS here)
    try:
        head = await reader.readuntil(b"\r\n\r\n")
        method, target, _ = head.split(b"\r\n", 1)[0].decode().split(" ", 2)
        if method != "CONNECT":
            writer.close()
            return
        host, port = target.rsplit(":", 1)
        up_r, up_w = await asyncio.open_connection(host, int(port))
        writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
        await writer.drain()
        await asyncio.gather(pipe(reader, up_w), pipe(up_r, writer))
    except Exception:
        writer.close()


async def main():
    sctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    sctx.load_cert_chain(CERT, KEY)
    with open(CERT) as f:
        good = hashlib.sha256(ssl.PEM_cert_to_DER_cert(f.read())).digest()
    bad = b"\x00" * 32
    origin = await asyncio.start_server(origin_handler, "127.0.0.1", 0, ssl=sctx)
    proxy = await asyncio.start_server(proxy_handler, "127.0.0.1", 0)
    url = "https://127.0.0.1:%d/" % origin.sockets[0].getsockname()[1]
    proxy_url = "http://127.0.0.1:%d" % proxy.sockets[0].getsockname()[1]
    print("python", sys.version.split()[0], "aiohttp", aiohttp.__version__, "cert_sha256", good.hex())
    print("origin", url, "proxy", proxy_url)
    cases = (
        # (name, connector-level fingerprint, request-level fingerprint, proxy)
        ("direct+bad_fp", bad, None, None),
        ("proxy+good_fp", good, None, proxy_url),
        ("proxy+bad_fp", bad, None, proxy_url),
        ("proxy+bad_fp_per_request", None, bad, proxy_url),
    )
    for name, conn_fp, req_fp, px in cases:
        conn_ssl = aiohttp.Fingerprint(conn_fp) if conn_fp else True
        kwargs = {"proxy": px}
        if req_fp:
            kwargs["ssl"] = aiohttp.Fingerprint(req_fp)
        try:
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=conn_ssl),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as session:
                async with session.get(url, **kwargs) as resp:
                    print(name, "-> CONNECTED status=%s body=%r" % (resp.status, await resp.text()))
        except aiohttp.ServerFingerprintMismatch as e:
            print(name, "-> ServerFingerprintMismatch got_is_cert=%s host=%s port=%s" % (e.got == good, e.host, e.port))
        except Exception as e:
            print(name, "-> OTHER %s: %r" % (type(e).__name__, e))
    origin.close()
    proxy.close()
    await asyncio.sleep(0.2)


asyncio.run(asyncio.wait_for(main(), 120))
EOF
```

预计输出如下。第一行是版本号和证书摘要，`origin`/`proxy` 行显示随机端口。

| 情况 | 修复前（base） | 修复后（假设修复覆盖了代理 CONNECT 路径） |
|---|---|---|
| `direct+bad_fp` | `ServerFingerprintMismatch got_is_cert=True host=127.0.0.1 port=<源站端口>` | 不变 |
| `proxy+good_fp` | `CONNECTED status=200 body='ok'` | 不变 |
| `proxy+bad_fp` | `CONNECTED status=200 body='ok'`（原 bug：错误指纹经代理仍能连上） | `ServerFingerprintMismatch got_is_cert=True host=… port=…`（host/port 可能是代理地址，也可能是源站地址，题面没有约定） |
| `proxy+bad_fp_per_request` | `CONNECTED status=200 body='ok'` | 同上 |

判读说明：
- 首行的 `cert_sha256` 应该是 `5ac883dc…22bc`。
- stderr 可能出现 asyncio 关于连接被对端关闭的日志，不影响判读。
- 如果任何一行出现 `OTHER`，或者 `direct+bad_fp` 不是 `ServerFingerprintMismatch`，说明脚本或环境有问题，不能据此判断修复是否有效。
- 这条命令只检验一种解读，即"代理 CONNECT 路径是否校验指纹"。如果标准修复针对的是别的路径，修复前后的输出可能完全一样。

## 5. 阅读范围

**实际打开的文件**

- 角色卡本身。没有打开卡里链接的 SWE-Gym 卡，也没有打开角色卡所在目录或上级目录里的其它文件。
- PUBLIC_DIR 顶层：通读了 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`；`worktree_manifest.json` 只看了结构（`export`、`initial_diff` 的元数据、`untracked_*`、个别文件条目）。没有打开其中指向 PUBLIC_DIR 以外的路径，包括 `public_bundle.json` 的 `source` 和 manifest 的 `initial_diff.source`。
- 源码：
  - `aiohttp/client_reqrep.py`：1-240、270-300、330-400、675-683 行。
  - `aiohttp/connector.py`：735-1475 行，另外看了第 34、245 行和 `BaseConnector.connect`（506-590 行）。
  - `aiohttp/client_exceptions.py`：150-290 行。
  - `aiohttp/client.py`：470-505、626-636、660-690 行，另有 grep。
  - `aiohttp/__init__.py`：用 grep 查了版本号和导出。
  - `aiohttp/helpers.py` 等：只 grep 了 `NO_EXTENSIONS`。
- 测试：
  - 通读 `tests/test_client_fingerprint.py`、`tests/conftest.py`。
  - `tests/test_connector.py`：560-760、1490-1620 行。
  - `tests/test_client_functional.py`：560-670 行。
  - `tests/test_client_request.py`：1340-1384 行。
  - `tests/test_client_exceptions.py`：260-305 行。
  - `tests/test_proxy.py`：1-120、240-440、760-910 行。
  - `tests/test_proxy_functional.py`：1-135、195-260、625-660 行，另外 grep 了测试名。
- 文档与配置：
  - `docs/client_advanced.rst`：500-620 行。
  - `docs/client_reference.rst`：1032-1082、2004-2030、2306-2318 行，另有 grep。
  - `CHANGES/` 下的全部片段。
  - `setup.cfg` 的 `[tool:pytest]` 段；`run_tests.sh`。
  - `requirements/test.in` 和 `test.txt`（grep）。
  - `Makefile`：前 80 行，另有 grep。
  - `examples/server.crt`/`server.key`：看了文件头，另用本机 `openssl` 读了证书元数据。
  - `vendor/` 的目录列表。
- 本机执行过的非项目命令：`ls`、`grep`、`sed`、`python3`（用来汇总 manifest JSON、计算示例字符串长度）、`openssl x509/rsa`（读公开证书的元数据）。没有联网，没有运行项目代码。

**没有查的范围**

- aiohttp 的其余模块：`web_*`、`http_*`、`client_proto.py`、`client_ws.py`、`pytest_plugin.py`、`test_utils.py` 等。
- `HISTORY.rst`、其余文档、`.github/`、`tools/`。
- 不在工作树里的内容：`install.sh`、`process_aiohttp_updateasyncio.py`、`.venv`、编译产物、`.git`、隐藏测试。
- `Makefile` 初态 diff 的正文。

**限制**

- `user_prompt.txt` 只是 `render_user_prompt` 的静态渲染结果，不是捕获到的模型实际消息。
- `worktree/` 不是完整的运行容器：没有 `.venv`、编译产物、`.git` 和隐藏测试，还缺两个未跟踪的构建文件。
- 本报告没有验证以下三项：模型实际收到的消息；运行资源（2 CPU / 4 GiB、`/tmp` 1 GiB）；开发条件（依赖是否已安装、回环和 TLS 是否可用）。第 4 节的所有预期都来自静态阅读。
