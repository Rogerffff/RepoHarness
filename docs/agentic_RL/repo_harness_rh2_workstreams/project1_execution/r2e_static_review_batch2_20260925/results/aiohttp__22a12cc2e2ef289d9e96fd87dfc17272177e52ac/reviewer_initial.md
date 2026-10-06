# 独立复核·第一步初判：aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac

2026-09-25 · 独立复核者（Claude，干净上下文）· 本文写于阅读主审产物、公开读者产物和历史引用之前。本题没有材料修订（`revisions.json` 为 `[]`）。

## 0. 初判摘要

1. **题面场景写错，示例也不能用，这是本题的主要问题（有执行证据）。** 题面说“直连 HTTPS 时指纹不匹配却不抛异常”，示例是 `TCPConnector(fingerprint='incorrect_fingerprint')`。但在 base 上：
   - 这个示例在构造时就抛 `ValueError: fingerprint has invalid length`（devcheck `orig/captures/pr2_2_cmd.out`）。
   - 用合法的 32 字节错误指纹直连时，base 已经会抛 `ServerFingerprintMismatch`（`pr4_7_cmd.out` 的 `direct+bad_fp` 一行）。

   真实缺陷只在**经 HTTP 代理 CONNECT 隧道、再用 `loop.start_tls` 升级 TLS** 的路径上（同一输出里 `proxy+bad_fp -> CONNECTED`）。题面一次也没提到代理。隐藏目标键也只测这条代理路径。
2. **目标键只有 1 个：`TestProxy.test_https_connect_fingerprint_mismatch`。** 它是纯 mock 测试：`_get_fingerprint` 被替换成一个 mock，其 `check` 一被调用就抛异常；测试只断言抛出 `ServerFingerprintMismatch`。因此测试**区分不出**以下几种情况：
   - 检查的是 TLS transport，还是底层裸 TCP transport；
   - 指纹匹配时代理连接能否照常建立；
   - 不匹配时 TLS transport 有没有关闭。

   一种把检查写在错误 transport 上的补丁（真实环境里仍会连通）预计能拿 1 分。这是**漏测**，静态推断，待实跑。
3. **误拒风险较低，但确实存在。** 测试替身 `TransportMock` 只重写了 `close()`。如果补丁在不匹配时改用 `abort()` 或 `is_closing()`，会触发 stdlib 基类的 `NotImplementedError`，结果判 0。另外，只要补丁没有通过 `self._get_fingerprint(...)` 取指纹（例如内联写一份等价逻辑），也会判 0。
4. **评分侧材料一致，结果稳定。**
   - current 的 4 行运行中，noop 都是 17/18，只错目标键；gold 都是 18/18。M3 独立 runner 在来源镜像上跑 2 次也都是 18/18。
   - 18 个期望键全是 PASSED，没有非 PASSED 期望键，也没有撞键。
   - 同仓跨题比对没有发现包含关系。
5. **暂定处置：needs_review（题意/测试争议）。** 建议修订公开题面：写明代理场景，并把示例改成合法的 `ssl=aiohttp.Fingerprint(<32 字节>)`。另外可以考虑加强测试，断言 `check` 的参数是 TLS transport，并补一个指纹匹配时仍能连通的用例。**未修订前，不建议当作干净的探针题。**

## 1. 实际读取范围

- **角色与方法：**
  - `roles/reviewer_r2e.md` 全文。
  - `roles/investigator_r2e.md`：Read 工具返回了全文。我只把“R2E 的评分口径”“材料”“第二批补充规则”三节当作口径；另外两节“对每题按顺序完成”“边界”是通用流程，不含本题内容。
  - 八方面协议、R2E 环境卡、记录模板，三份全文。
- **PUBLIC_DIR：**
  - 全文：`user_prompt.txt`、`environment_brief.md`、`public_bundle.json`；`worktree_manifest.json` 只读了前段。
  - `worktree/aiohttp/connector.py`：读了 L800–850、L995–1480，其余靠 grep。
  - `client_reqrep.py`：L118–215。
  - `client_exceptions.py`：只看了类继承关系。
  - `setup.cfg` 的 `[tool:pytest]` 段；`run_tests.sh`。
  - `tests/test_proxy.py` 与 `tests/conftest.py`：与隐藏测试做了 diff。
  - `tests/test_client_request.py` L1365–1380。
  - `tests/test_client_functional.py`、`tests/test_connector.py` 中 fingerprint 相关行，只用 grep 定位。
  - `CHANGES/`、`docs/client_reference.rst`、`docs/client_advanced.rst`：fingerprint 相关行，grep。
- **PRIVATE_DIR：**
  - `gold.patch`、`run_tests.sh`、`revisions.json`、`run_refs.json`、`expected_output.json`；`grading_bundle.json` 与 `validation_bundle.json` 只看了键与摘要。
  - `hidden_tests/conftest.py`、`__init__.py`。
  - `hidden_tests/test_1.py`：读了 L1–120、L240–560 和全部 `def test_` 列表。其余部分经 diff 确认与 base `tests/test_proxy.py` 逐字相同：只差 import 行和新增的那一个测试。
- **运行原件：**
  - R-f：`ledger_r2e_all_{noop,gold}.jsonl` 第 2 行，以及两份 eval.log 全文。noop 日志的 sha256 已本地复算，与账本一致。
  - 环境轮 `_rerun2`：`ledger_{noop,gold}.jsonl` 第 2 行，两份 eval.log 用 grep 看关键行。
  - M3 a1/a2 `test_output.txt`：只用 grep 看了结果行。
- **devcheck：**
  - 全文：`commands_with_preflight.json`、`captures/*.out`（全部 9 份）、`attempt.json`、`private_gold/private_control.json`。
  - 部分：`prelaunch.json` 前段、`post_run_facts_root.txt` 前段、`cc_version_observed.json`。
  - 未读：stub 请求、`trajectory.jsonl`、harness stderr、`private_gold/stdout.log`。
- **跨题：**
  - 两份 scan 中与 aiohttp 相关的 pairs 与 method。
  - 同仓其它 4 题的**公开**工作树：对 `connector.py` 的 `fingerprint.check` 和 `tests/test_proxy.py` 里的目标测试名做 grep，并看了版本号。
- **未读：**
  - `public_read.md` 及 OUTPUT_DIR 里的其它文件；
  - 所有 history/ 目录、r2e_env_repair 文档、首批审查目录、Codex 复核目录；
  - README、`assignments.json`、`grader_candidates.md`；
  - 其它题的私有包。
- **只看了来源、没读全文的内容：** devcheck 的命令写着“来自公开读者建议”，我从 devcheck 里看到了这些命令本身，但没有读 `public_read.md`。

## 2. 题目与材料

- **base 与 gold：** base `354153e9b706`，aiohttp `3.11.0.dev0`。gold 只改 `aiohttp/connector.py`：在 `TCPConnector._start_tls_connection` 里，`start_tls` 成功之后做一次检查，具体是 `if isinstance(tls_transport, asyncio.Transport)` → `self._get_fingerprint(req)` → `fingerprint.check(tls_transport)`；不匹配时关闭 transport，按 cleanup 设置登记，然后重新抛出（gold.patch 的 hunk `@@ -1217`）。
- **调用关系：** `_start_tls_connection` 只有一个调用点，即 `_create_proxy_connection` 的 L1460（经 HTTP 代理访问 HTTPS 目标时）。
- **材料一致性（已核）：**
  - `expected_output.json` 的 sha256 是 `351982fc…`，与 `run_refs.current_material` 和 grading_bundle 一致。
  - 两次 current 运行的日志都记录了 `RH2_SETUP_HIDDEN_TESTS_TREE=80d242d6…`，与 current_material 一致。
  - `run_tests.sh` 的 sha256 是 `8285765f…`，与 grading_bundle 一致。
  - 隐藏测试里 `def test_` 共 18 个，对应 18 个期望键。
- **base 上的初始问题在哪里成立（执行证据）：**
  - `connector.py` 中 `fingerprint.check` 只出现在 `_create_direct_connection`（L1326–1338）。
  - `_start_tls_connection`（L1187–1251）和 `_wrap_existing_connection`（L1085）都没有这个检查。
  - devcheck 用 agent 身份在 noop 状态下跑 `pr4_7_cmd.out`，得到 `direct+bad_fp -> ServerFingerprintMismatch`、`proxy+bad_fp -> CONNECTED`、`proxy+bad_fp_per_request -> CONNECTED`。
  - 私有 gold 对照（`private_control.json` 的 `pr4_7_cmd`）中，这两条代理用例都变成了 `ServerFingerprintMismatch`；`proxy+good_fp` 仍是 `CONNECTED`。

## 3. 隐藏测试展开

**目标键 `TestProxy.test_https_connect_fingerprint_mismatch`**（test_1.py L381–479，新增）。测试步骤：

- 对 `enable_cleanup_closed` 取 True 和 False，各跑一个 `subTest`（L391、L394）。
- 代理请求是 `http://proxy.example.com`，目标是 `https://www.python.org`。
- `proxy_req.send` 与 `proxy_resp.start` 被 patch，返回 `status=200`。
- `connector._resolve_host` 被 patch。
- `connector._get_fingerprint` 被 patch（autospec、spec_set），返回 `fingerprint_mock`（L449–455）。`fingerprint_mock` 的 `check.side_effect` 固定抛 `ServerFingerprintMismatch(b"exp", b"got", "example.com", 8080)`。
- `loop.create_connection` 被 patch，返回 `(Mock, Mock)`。
- `loop.start_tls` 被 patch，返回 `TransportMock()`（L400–402、L462–467）。`TransportMock` 是 `asyncio.Transport` 的子类，只把 `close()` 重写成空操作。
- 唯一断言在 L474：`assertRaises(aiohttp.ServerFingerprintMismatch)` 包住 `connector._create_connection(req, [], ClientTimeout())`。

**测试没有断言的内容：**
- `check` 的调用次数和参数；
- `close` 是否被调用；
- `_cleanup_closed_transports` 的内容；
- 异常的字段。

**noop 下的失败位置：** `AssertionError: ServerFingerprintMismatch not raised`，出现在 `r2e_tests/test_1.py:475`。见 R-f noop 日志 L155/L172 和 `_rerun2` noop 日志 L155/L172；失败的是第一个 subTest（`cleanup = True`）。

**回归键（17 个）：** 与 base `tests/test_proxy.py` 逐字相同。
- 逐行读过的有：`test_connect`、`test_proxy_server_hostname_default`、`test_proxy_server_hostname_override`、`test_https_connect`。其余只按名称和 mock 形状抽查。
- 与本题相关的保护：这几个测试的 `start_tls` 都返回 `mock.Mock()`，也都没有 patch `_get_fingerprint`。所以在 req 与 connector 都是 `ssl=True`、没有设置指纹时，它们能挡住一类错误实现：没做 None 判断就直接调用 `fingerprint.check` 的补丁，会因 `AttributeError` 失败。
- 它们挡不住“指纹匹配时代理连接照常建立”这一行为出现回归。
- 隐藏集只有 `test_1.py` 一个测试文件，没有跨文件撞键。

## 4. 需求—测试映射

| 公开要求 / 合理旧行为 | 公开依据 | 测试 ID / 断言 | 判断 | 证据 |
| --- | --- | --- | --- | --- |
| HTTPS 连接遇到指纹不匹配时抛 `ServerFingerprintMismatch`：直连 | 题面 Expected Behavior | 隐藏集不测。公开 `tests/test_client_functional.py::test_tcp_connector_fingerprint_fail`（约 L626–648）测了，但不计分 | base 已满足，**题面所述场景不成立** | devcheck `pr4_7` noop：`direct+bad_fp -> ServerFingerprintMismatch`；`pr3_6` 两例都通过 |
| 同一要求：经 HTTP 代理（CONNECT + start_tls） | 题面**没有写**；只能读代码推断：唯一的检查点在直连路径 L1326 | 目标键 L474 | 覆盖，但方式是 mock：只测“到了某个时刻会调用 `_get_fingerprint(...).check(...)`” | noop 日志 L155；gold 18/18 |
| “阻止连接建立”：不匹配时不返回连接，并关闭 TLS transport | 题面 Expected；直连路径的先例 L1330–1332 | 只断言抛异常；`TransportMock.close` 不受监视 | 部分覆盖（关闭与 cleanup 漏测） | 静态 |
| 检查对象必须是 TLS 层证书 | `Fingerprint.check` 用 `get_extra_info("sslcontext"/"ssl_object")`（client_reqrep.py L139–147） | 不断言 `check` 的参数 | **缺失**：检查裸 transport 的错误补丁也能通过 | 静态推断，见 §7 候选 B |
| 指纹匹配时代理连接照常建立 | 合理旧行为与 docs 中的证书固定语义 | 无（mock 的 check 恒抛） | **缺失**：写死“有指纹就抛”的补丁也能通过 | gold 对照 `proxy+good_fp -> CONNECTED` 只证明 gold 满足 |
| 题面原例 `fingerprint='incorrect_fingerprint'` | 题面示例 | 无 | **与公开接口冲突**：`fingerprint` 参数按文档是 `bytes` 类型的 SHA256 摘要（docs/client_reference.rst L1070）；base 与 gold 下都是 `ValueError` | `pr2_2` noop 与 gold 对照都是 `RAISED ValueError fingerprint has invalid length`；公开测试 `test_client_request.py::test_bad_fingerprint` L1367 也固化了这一行为 |
| 未设置指纹时代理路径不受影响 | 旧行为 | 17 个回归键 | 覆盖 | gold 18/18 |

**反查：** 关键断言“经代理时抛 `ServerFingerprintMismatch`”的依据，只能是“题面说 HTTPS 连接要抛”加上“读代码发现只有代理路径漏检”。题面给的场景和例子都指向错误的方向。

## 5. 八方面

1. **公开需求：** 有问题，见 §0 第 1 条。
   - 题面标题只说“in HTTPS Connections”，没有提代理。
   - 示例的指纹参数不合法。
   - “Actual Behavior”说连接会成功，但在题面自己的场景下这不成立。
   - 不看隐藏材料、只读代码能否推断出代理路径？能：`fingerprint.check` 只有一处调用，`_start_tls_connection` 没有检查。devcheck 里那些按公开材料写出的命令也确实去复现了代理路径，这是间接证据。
   - 但一个照着题面复现的解题者，会得到 `ValueError`，或者看到直连已经在抛异常。这时它可能改错地方，也可能判断无事可修。
2. **材料与初始问题：** 版本对应，已核（§2）。原问题在 base 的代理路径上成立，有执行证据；题面描述的直连场景在 base 上已经修好，同样有执行证据。
3. **测试是否测到要求：** 部分测到。只测到抛异常；检查对象、关闭行为和匹配时的正向用例都缺，见 §4。
4. **是否误拒合理解：** 风险低。候选 C 和 E 预计判 0（§7）。它们都来自测试替身的形状或对私有 helper 名的依赖；需要实跑确认。
5. **回归与 gold 完整性：** gold 修到了代理路径，没有无关改动。小问题有三处：
   - 不匹配时，异常里的 host/port 是**代理**的对端地址，不是目标地址（私有对照 `proxy+bad_fp ... port=39183`，与代理端口 39183 一致；直连用例报的是 origin 端口）。未测，题面也没要求。
   - 没有覆盖 `_wrap_existing_connection` 分支（运行时没有 `start_tls` 时才走）。CPython 3.9 的默认 loop 有 `start_tls`，所以本环境走不到这个分支。
   - `isinstance(tls_transport, asyncio.Transport)` 这个保护条件在非标准 loop 下是否会跳过检查：未知，未查。
6. **开发条件：** 见 §8。
7. **交付与评分边界：**
   - 合法修复只涉及 `aiohttp/connector.py`，不会被投影忽略。
   - 隐藏 conftest 与 base `tests/conftest.py` 逐字相同，没有引用仓库测试模块里的辅助代码。
   - 依赖的只是包内的 `aiohttp.test_utils.make_mocked_coro` 和 `aiohttp.pytest_plugin`，候选可以改，但诚实的修复不会去碰。
   - `setup.cfg` 里有 `filterwarnings = error`（L143–144），命令行的 `-W ignore` 也覆盖不了 ini 配置。所以补丁如果在测试路径上新发出任何 warning，都会变成失败，这对所有补丁一样。
8. **题目关系与用途：** 见 §9。

## 6. R2E 专项

- **(a) 非 PASSED 期望键：** 没有，18 个全是 PASSED。更完整的修复（例如同时给 `_wrap_existing_connection` 补检查，或者异常里改报目标 host/port）不会翻转任何键。静态推断。
- **(b) 题面报错是否出现在 noop 目标键：** 题面描述的是“没抛异常”，noop 目标键的失败原因是 `ServerFingerprintMismatch not raised`，现象一致。但**场景不一致**：题面说的是直连（在 noop 状态下已经会抛），测试走的是代理路径。
- **(c) 题面是否泄漏修法：** 没有泄漏。反过来，题面连出问题的路径都没给。
- **(d) 测试支撑、搬迁伪影与撞键：** 没有问题。
  - 不依赖 base 版仓库测试辅助。
  - conftest 是原样拷贝；`pytest_plugins` 写在 `r2e_tests/conftest.py` 里，从 gold 的 18/18 看已经生效。
  - 单文件，没有撞键。
  - 测试 mock 了私有方法 `_get_fingerprint`，也依赖 `TransportMock` 的最小实现。这两点是误拒风险的来源（§7 C、E），不属于搬迁伪影。
- **(e) 时间、随机与资源：** 纯 mock，不涉及。`ClientTimeout()` 默认 `sock_connect=None`，每个键约 0.01–0.03 s。gold 在 current 下跑了 2 次，加 M3 的 2 次，都稳定为 18/18。
- **(f) 修订：** 无，不适用。

## 7. 候选（请协调者用正式评分代码实跑 A、B、C；D、E 可选）

以下都只改 `aiohttp/connector.py`。

- **A 合理替代（预期 1，18/18）：** 不改 `_start_tls_connection`。在 `_create_proxy_connection` 里，把 L1460 的 `return await self._start_tls_connection(transport, req=req, timeout=timeout)` 改成下面这段，然后 `return tls_transport, tls_proto`：

  ```python
  tls_transport, tls_proto = await self._start_tls_connection(transport, req=req, timeout=timeout)
  fingerprint = self._get_fingerprint(req)
  if fingerprint:
      try:
          fingerprint.check(tls_transport)
      except ServerFingerprintMismatch:
          tls_transport.close()
          # 按 _cleanup_closed_disabled 登记
          raise
  ```

  用途：确认测试没有绑死 gold 的插入位置。端到端再用 `pr4_7` 复核，应得到 `proxy+bad_fp -> ServerFingerprintMismatch`、`proxy+good_fp -> CONNECTED`。
- **B 错误实现，预期**误得 **1：** 位置与 gold 相同，但写成 `fingerprint.check(underlying_transport)`，即检查的是底层 transport。
  - 评分：mock 的 check 恒抛，所以 18/18。
  - 真实行为：裸 TCP transport 的 `get_extra_info("sslcontext")` 为空，`Fingerprint.check` 直接返回（client_reqrep.py L140–141）。所以 `pr4_7` 里 `proxy+bad_fp` 仍应是 `CONNECTED`，也就是没修好。
  - 变体 B′：`if self._get_fingerprint(req): raise ServerFingerprintMismatch(b"", b"", req.host, req.port)`，写死抛异常。预计 18/18，但会破坏 `proxy+good_fp`。
  - 这是本题最值得实跑的漏测证据，对 RL 的 reward 可利用性也有意义。
- **C 合理但预计被误拒（预期 0，错的是目标键）：** 与 gold 相同，只是不匹配时调用 `tls_transport.abort()`（立即断开，不再登记 cleanup），或者加一句防御 `if not tls_transport.is_closing(): tls_transport.close()`。
  - `TransportMock` 只重写了 `close`。stdlib 的 `WriteTransport.abort` 和 `BaseTransport.is_closing` 都直接 `raise NotImplementedError`（本机 3.12 源码已核；3.9 同样如此，属推断）。于是 `NotImplementedError` 取代了原本的 mismatch 异常，目标键 FAILED。
  - 真实环境里这两种写法的行为都正确。
- **D 照着题面示例改的候选（预期 0，错的是目标键，属于正确拒绝）：** 在 `client_reqrep._merge_ssl_params` 或 `Fingerprint.__init__` 里，让 `str` 类型的指纹不再抛 `ValueError`（例如先 encode），代理路径不改。
  - 目标键仍然失败。静态已能确定结果，可以不跑。
  - 它的意义在于说明题面会把解题者引向错误修改，应单列为“遵循冲突示例的候选”，不算合理修复。
- **E 内联取指纹（预期 0，错的是目标键）：** 不调用 `self._get_fingerprint`，而是在代理路径里内联等价逻辑（先看 `req.ssl`，再看 `self._ssl` 是否为 `Fingerprint`）。
  - 测试只通过 mock `_get_fingerprint` 注入指纹，而 req 与 connector 的 `ssl` 都是 True，所以不会触发检查，结果判 0。
  - 真实行为与 gold 相同。不过直连路径已有复用 `_get_fingerprint` 的先例（L1279），大多数解题者会直接复用，所以出现概率低。

## 8. 开发需求（依据：环境卡、`environment_brief.md`、devcheck）

- **镜像层面实测**（devcheck orig：agent uid 54321、真实 Claude Code 2.1.205 + 桩端点、正式启动路径、`--max-turns 12`）：
  - R2E 预检三项都是 ok。
  - `python` 指向 `/testbed/.venv/bin/python`（3.9.21）；aiohttp 从 `/testbed/aiohttp` 导入；pip 24.2 可用；pytest 8.3.3。
  - trustme、proxy、pytest_cov、aiohappyeyeballs 都已装（`pr0_1`）。
  - 公开测试都能跑：`test_proxy.py` 17 passed，`test_client_fingerprint.py` 12 passed，`test_connector.py -k …` 10 passed，`test_client_functional.py -k fingerprint` 2 passed。
  - 在回环地址上可以起本地 HTTPS origin 和 CONNECT 代理，用 `/testbed/examples/server.{crt,key}` 做端到端复现（`pr4_7`）。
  - 初始工作树：` M Makefile`，外加 3 个未跟踪文件；HEAD 为 `354153e9`。
- **构建与提交边界：** 只改纯 Python 的 `connector.py`，不需要重新构建；不需要网络。
- **仍需验证：** 真实模型求解、经 Qwen adapter 的链路、模型实际收到的消息，这三项都是 actor 待验。
- **缺项（未核）：** devcheck 用的镜像是 `sha256:2b571f22…`（derived9 overlays），current 评分运行用的是 `sha256:dfd6021f…`（R-f 机）。两者配方都是 `r2e_derive_v1`，来源镜像相同，HEAD 与初始 porcelain 一致。但两次构建的内容是否等价，我没有核。

## 9. 题目关系

- **机械比对：** `cross_task_gold_scan.json` 里没有以本题为 `task` 的条目，说明本题 gold 没有出现在同仓其它题的公开工作树里。
- **人工核对：** 看了其它 4 题的公开工作树。
  - `1c1c0ea3`（3.10.6.dev0）和 `4075c653`（3.9.0b0）的 `connector.py` 都只在直连路径里有 `fingerprint.check`，`tests/test_proxy.py` 里也没有目标测试名。
  - `240da100`（0.9.1dev）和 `618335186`（0.17.0a0）没有 `test_proxy.py`，也没有 fingerprint 检查。
  - 结论：没有其它题的初态里已经包含本题修复。
- **反方向：** 本题的初态包含 `1c1c0ea3` 的 gold（7/7 行），也包含 `240da100`、`4075c653` 新增的测试名。这说明那几题的修复已经存在于本题 base 中，只影响对那几题的判断，不影响本题。
- **外部答案可达性：** 上游修复是公开的 aiohttp 提交，模型可能在预训练时见过；解题环境不联网。未核。

## 10. 疑点、未知与下一步

- **未知：**
  - 候选 A/B/C/E 的实际得分。现在都只是源码推断。
  - pytest 8.3.3 在没有 subtests 插件时如何汇报 `subTest`。这不影响本题结论：noop 的首个 subTest 失败后，整个键就是 FAILED。
  - 两张派生镜像的内容是否等价。
- **暂定处置：** needs_review，原因归为“题意/测试争议”。
  - 题面问题已有执行证据，建议修订公开规格：写明“经 HTTP 代理访问 HTTPS 目标时”，示例改用 `ssl=aiohttp.Fingerprint(<错误的 32 字节 sha256>)` 加 `proxy=`。这只是把真实的用户可见场景写出来，不属于把测试要求抄进题面。
  - 可以考虑加强测试：断言 `fingerprint_mock.check` 恰好被调用一次、参数是 `start_tls` 返回的那个 transport；再加一个 check 不抛异常时连接能正常返回的正向用例。这会改变测试标准，需要按修订流程另行决定。
- **唯一最值得先做的下一步：** 用正式评分代码在同一派生镜像上跑候选 A、B、C，并对 B 追加 `pr4_7` 端到端复现。这能直接确认两件事：漏测是否可以被利用（B 得 1 但仍连通），以及替身误拒是否存在（C 得 0）。
