# 题卡：aiohttp `240da100`（R2E 单题闭环，统一标准 v1）

2026-09-29 · R2E 私有主审 · `disposition.scope=static_review`（含本批新镜像上的实跑证据）。

- 前稿：`analysis_before_history.md`；历史核对：`old_findings_delta.md`。
- 路径都相对仓库根。缩写：
  - `LIFE` = `runs/r2e_lifecycle_20260929`
  - `HT` = `runs/r2e_static_prep_20260924/v3/private/aiohttp__240da100151933883d7dea0528d45877df025b92/hidden_tests/test_1.py`

## 结论

- **处置 `needs_repair`**：测试层有可以复现的 S1，修法在预授权模板（R-c）之内。**R-c 两项必做，R-a 可选。**
- **v1 用途**：问题定位 yes，能力比较 conditional，训练候选 no，留出评测 no。各项条件见 §5。
- **环境不是阻塞项**：新镜像上 noop 得 0、gold 得 1，devcheck 全部通过。

## 1. 题目与版本

- **题面**：`ProxyConnector` 把明文目标改写成绝对 URL 时丢了显式端口，`http://localhost:1234/path` 变成了 `http://localhost/path`。
- **版本**：base `ef756ce2`（aiohttp 0.9.1dev，Python 3.9.21）。
- **gold**：只改一个词，`connector.py:343` 的 `host=req.host` 改为 `host=req.netloc`。
- **材料**：v3。本题没有修订，v3–v5 逐字相同。33 个键：31 个 PASSED，2 个期望 FAILED。目标键只有一个，`ProxyConnectorTests.test_request_port`。
- **当前环境**：配方 `r2e_derive_v1+sysconfig_v1`，image `a6dee334…`，grader profile `3ec1bfa8…`。09-28 实测 noop 0（32/33）、gold 1（33/33）。

## 2. 关键映射

| 需求或旧行为 | 公开依据 | 测试 / 决定性断言 | 覆盖 | 执行证据 / 下一步 |
| --- | --- | --- | --- | --- |
| 带显式端口的目标经代理后，`req.path` 保留端口 | 题面 `user_prompt.txt:9, 29-31` | `test_request_port`：`req.path == 'http://localhost:1234/path'`（`HT:584`），输入与题面示例逐字相同 | 部分：只测示例 | DG1 得 1 → R-c 第 1 项 |
| 无端口 URL 不补 `:80`；连代理失败时不改请求；认证头迁移 | 公开 `tests/test_connector.py:341, 363-374, 376-446` | 同名回归键（隐藏文件就是公开文件加 1 个测试） | 覆盖 | noop、gold 都 PASSED |
| `ClientRequest.host` 不含端口；CONNECT 目标是 `host:port` | 公开 `tests/test_client.py:332-346`（在 3.9 下不能收集）；`test_https_connect` 只测 443 | 显式端口没有断言 | 缺失 | WR1 得 1 → R-c 第 2 项 |
| 两个期望 FAILED 的端到端键 | 无（来自 py3.9 不兼容） | 真实 socket 请求 | 死键 | SC1 得 1，说明最可能的顺手改动不受罚 |

## 3. 八方面：已查与未查

- **公开需求**：已查题面、提示、代理文档和公开测试。未查模型实际收到的消息，因为 devcheck 用的是固定提示。
- **材料与初始问题**：各原件哈希一致；noop 的失败信息与题面逐字相同；脏树来自来源镜像的 3.9 兼容改写。
- **测试是否测到要求**：目标键逐行追到了源码，回归键按组读了断言；`BaseConnector` 没有逐个分支追。
- **是否误拒合理解**：没有只在隐藏测试里出现的约束；替代解 AL1（端口不是默认值时才补）得 1。
- **回归与 gold**：gold 正确且改动最小；WR1 暴露出 host/port 语义没有任何断言保护。
- **开发条件**：devcheck 以 agent 身份走正式启动路径，6 条公开命令的结果全部符合预期；两条相关 pytest 命令各自在 1 秒内完成。
- **交付与评分边界**：投影只含候选改动的文件。隐藏测试依赖 base 版的 `tests/test_client_functional.py` 和 `aiohttp/test_utils.py`，评分时这两个文件不重置，已登记。共享控制面没有逐题复审。
- **题目关系**：`618335186f22` 的初态已含本题的修复和测试；另有三道 3.x 题含它的后代测试（X1）。

## 4. 问题与证据层次

| 编号 | 问题 | 严重度 / 去向 | 证据 |
| --- | --- | --- | --- |
| T2c | 唯一的目标断言就是题面示例的字面值 | S1 → R-c 1 | 测试文本（静态判定） |
| T2b | 退化候选 DG1（只在端口为 1234 时补 `:1234`）正式评分 1.0 | S1 → R-c 1 | `LIFE/inv/aiohttp_240d/ledger_DG1.jsonl:1`；`pcheck_DG1.json` 在两个 8080 端口的用例上报 BAD |
| T2（v1 §4 第 4 步） | WR1（让 `ClientRequest.host` 带上端口）正式评分 1.0，但它破坏了直连显式端口和 host/port 语义 | S1 → R-c 2 | `ledger_WR1.jsonl:1`；`pcheck_WR1.json`：直连目标变成 `('localhost:1234', 1234)`。CONNECT 目标会变成 `host:8443:8443`，这一点是源码推断 |
| T5 | 两个期望 FAILED 的死键，原因是 py3.9 不兼容 | 已解释；R-a 可选 | 旧环境 3+3 次、新环境 1+1 次运行；SC1 得 1.0 |
| P4 | 题面示例原样跑不起来：顶层没有 `ClientRequest`，真实事件循环会抛 TypeError | 登记；有公开的替代复现 | devcheck 的 `literal_example_probe.out`、`repro_port_mocked.out` |
| T3 | 查询串、`user:pass@`、自定义 Host 头都没有断言 | 登记（边缘情形） | 静态 |
| X1 | 同仓跨题包含 | 登记；按仓库划分 | 公开包实读 |

环境侧的解题条件都已由 devcheck 在新镜像上复核：没有 pip、`/testbed` 必须在 `sys.path` 上、真实 socket 路径不可用、`tests/test_client.py` 不能收集。其中主要几条 v3 提示已经覆盖。这些条件不影响判分。

## 5. v1 用途结论

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| `problem_localization` | yes | 无门槛 |
| `capability_comparison` | conditional | 公开开发路径（devcheck）、评分依据、当前环境（noop 0 / gold 1）都已核对。还差下面二选一：（a）用原版，但预先登记后检：对得 1 的补丁跑附录 B 的私有行为对照，任何一行 BAD 就判语义不通过，原始 reward 与语义结果分列；（b）改用 R-c 验收后的修订版 |
| `training_candidate` | no | 当前材料有三条未处理的 S1。R-c 两项验收通过、经 Codex 复核后再重判；那时正面覆盖证据才齐全（核心断言、noop 0 / gold 1、第 2、3 步结果） |
| `heldout_candidate` | no | 理由同上。修订后的版本只能作为"标明版本的自建评测"；与 `618335186f22` 等同仓题必须按仓库分在同一组 |

## 6. 修订建议（v1 §5，预授权模板之内）

### R-c 第 1 项（必做；修 T2c、T2b）

- **公开依据**：题面的一般表述 "a URL that includes a specific port"（`user_prompt.txt:9`），以及期望行为（29-31 行）。
- **改动**：
  - 在隐藏的 `r2e_tests/test_1.py` 里，给 `ProxyConnectorTests` 加 `test_request_port_other_url`。它换了主机、端口和路径（`http://www.python.org:8080/some/path`），走公开入口 `connect()`，断言 `req.path` 保留端口。代码见附录 A。
  - 期望映射加 `"ProxyConnectorTests.test_request_port_other_url": "PASSED"`。
- **刻意不测**：显式默认端口、https 的 `req.path`、代理请求的 Host 头。这几处两种写法都合理。

### R-c 第 2 项（必做；修第 4 步的 S1）

- **公开依据**：
  - 公开的 `test_https_connect` 断言 CONNECT 目标是 `host:port`；
  - 源码注释 `connector.py:354-361`；
  - 公开 `test_client.py:332-346` 断言 host 不含端口。
- **改动**：
  - 同一个类里加 `test_https_connect_port`：目标用 `https://www.python.org:8443`，断言 CONNECT 目标是 `'www.python.org:8443'`。代码见附录 A。
  - 期望映射加 `"ProxyConnectorTests.test_https_connect_port": "PASSED"`。
  - 这是一条回归断言，noop 在这个键上也会通过。
- **备选方案**：把公开的 `test_host_port` 原样搬进隐藏测试，换一个不撞键的类名。它只挡得住 WR1，挡不住"在 `_create_connection` 里就地改 `req.host`"这一类，所以优先用上面的行为断言。

### 合并验收（两项一起做，键集为 35）

- gold 得 1，AL1 得 1。
- noop 得 0，不符的键是 `test_request_port` 和 `test_request_port_other_url`。
- DG1 得 0，因为第 1 项的新键 FAILED；WR1 得 0，因为第 2 项的新键 FAILED。
- SC1 仍得 1。
- 没有 missing 或 unexpected 键。
- 修订后仍受保护的公开要求：端口保留（两个实例）、无端口时不补端口、失败时不改请求、认证头迁移、CONNECT 目标（默认端口和显式端口）。
- 保存新版本、父版本（v3）、理由和触发反例（DG1、WR1），交 Codex 复核。

### R-a（可选）

- 删掉 `HttpClientConnectorTests` 的两个用例和对应的期望键。
- SC1 得 1，说明最可能出现的顺手改动不受罚；只有越界的 py3.9 移植才会让这两个键翻转。
- 若真实候选出现翻转，R-a 改为必做（先例：scrapy `9a15fcf8`）。

## 7. 进探针还差什么

按派发规则，我没有读本批 README §3；下面按 v1 §2 和角色卡列出。

**已满足**
- 公开开发路径：devcheck 以 agent 身份走正式启动路径，预检三项通过，6 条命令全部符合预期。
- 评分依据：目标键和两个死键都已解释清楚。
- 当前环境：新镜像上 noop 0 / gold 1。
- 答案不可达：git 净化后各项计数都为 0，隐藏测试对 agent 不可读。
- 资源：内存峰值 171 MB，测试约 2 s。

**未满足**
1. 测试层的 S1：R-c 两项实施并通过合并验收。由协调者实施和跑评分，Codex 复核。
2. 如果要在 R-c 之前用原版进探针：需要预先登记后检脚本和判读规则，附录 B 可以直接用。由协调者登记。
3. 独立复核（v1 §7.3）：由 reviewer 角色完成。
4. 真实题面的渲染和真实模型求解都还没有捕获，这是批次共性问题。在探针运行时补上。
5. 同仓划分登记（X1）：由协调者完成。

## 8. 复核与下一步

- 前稿的判断没有改。实跑只是把第 3、4 步从"待实跑"变成了"已命中"。
- 暂定处置从 `needs_review` 改为 `needs_repair`，理由见 `old_findings_delta.md` §2。
- reviewer 复核还没有进行。
- **唯一优先的下一步**：实施 R-c 两项，然后按合并验收，gold、AL1、noop、DG1、WR1 各跑一次（SC1 可以同批跑），再交 Codex 复核。

## 附录 A：R-c 测试代码

加在 `r2e_tests/test_1.py` 的 `ProxyConnectorTests` 末尾：

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

## 附录 B：私有行为对照（后检，不评分）

- **脚本**：`LIFE/inv/aiohttp_240d/private_check_9_2.py`，与前稿 §9.2 相同。
- **运行方式**：在应用候选后的容器里执行 `cd /testbed && python -B - < 脚本`。注意脚本要从标准输入读入；如果按文件路径运行，`sys.path[0]` 不是 `/testbed`，`import aiohttp` 会失败，这正是 `pcheck_try1/` 那次失败的原因。
- **判读规则**：退出码为 0 且没有 BAD 行，才算语义通过。
- **本轮结果**（`LIFE/inv/aiohttp_240d/pcheck_*.json`）：

| 候选 | 退出码 | 结果 |
| --- | --- | --- |
| base（无补丁） | 1 | 前三个 URL 报 BAD |
| gold | 0 | 全部 OK |
| AL1 | 0 | 全部 OK |
| SC1 | 0 | 全部 OK |
| DG1 | 1 | 两个 8080 端口的用例报 BAD |
| WR1 | 1 | 前三个 URL 的 host 报 BAD，直连目标 `('localhost:1234', 1234)` 也报 BAD |

## 附录 C：证据索引

| 运行 | 账本行 | 结果 | 日志 sha256 |
| --- | --- | --- | --- |
| noop（新镜像，09-28） | `LIFE/env_verify/ledger_noop.jsonl:3` | 0.0，32/33，只差 `test_request_port` | `c6171f57…`（远端日志） |
| gold（新镜像） | `LIFE/env_verify/ledger_gold.jsonl:3` | 1.0，33/33 | `7caf0195…`（远端日志） |
| DG1 | `LIFE/inv/aiohttp_240d/ledger_DG1.jsonl:1` | 1.0，33/33；补丁 `efa10536…` | `71b9158a…`（`logs_DG1/`） |
| WR1 | `…/ledger_WR1.jsonl:1` | 1.0，33/33；补丁 `b8b809c1…` | `c3a2f60b…` |
| AL1 | `…/ledger_AL1.jsonl:1` | 1.0，33/33；补丁 `a2e5e694…` | `f7c9110e…` |
| SC1 | `…/ledger_SC1.jsonl:1` | 1.0，33/33；补丁 `ab0d861d…`；tcp 键失败原因变成 AttributeError | `98500d34…` |
| devcheck | `LIFE/devcheck/aiohttp__240da100…/orig/attempt.json` | 13 项检查全部 true；预检三项 ok；私有 gold 对照见 `private_control.json` | — |
| 旧环境对照 | `runs/r2e_rf_20260923/remote/ledger_r2e_{all,reps}_{noop,gold}.jsonl:3`、`runs/r2e_env_repair_20260924/_rerun2/ledger_{noop,gold}.jsonl:3` | noop 0 ×3，gold 1 ×3（配方 `r2e_derive_v1`） | 见前稿附录 A |
