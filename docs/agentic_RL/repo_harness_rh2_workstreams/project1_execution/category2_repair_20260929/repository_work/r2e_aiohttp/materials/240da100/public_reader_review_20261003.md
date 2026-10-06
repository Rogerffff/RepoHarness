# 240da100 fresh 公开静态读题（2026-10-03）

仅使用本题 `public_reader_bundle.json` 与 `runs/r2e_static_prep_20260924/v3/public/aiohttp__240da100151933883d7dea0528d45877df025b92/worktree/`。没有读取题目父目录的其它材料、私有题卡、review、候选、gold/hidden、历史 snapshot、4075 报告或其它线程；没有访问网络、调用模型工具、运行项目/测试、安装、SSH，或修改源码/题面。

## 输入核对

- 实际解码 `problem_statement` UTF-8 SHA-256：`d3ff12a9a27890831dcedc62d53e8c124647d6fe036c28712505ed247d7a272c`；与任务指定值及 bundle 字段一致。
- 实际 bundle 文件 SHA-256：`0dbe259cecdfe87950b5a9ad815251b9cdd0044c2b30a2ec5162c66a9b3102be`。
- 公开工作树存在。bundle 声明 base commit：`ef756ce29cc40a9b69e5e794eda722e252a62b4d`；未读取工作树外 Git 元数据，因此没有独立核验 commit 对应关系。
- 下文“题面解码行”按 JSON 解码后的 `problem_statement` 从第 1 行 `[ISSUE]` 起计；源码和测试引用为指定工作树文件的实际行号。

## 结论

公开目标清楚，示例与可见源码静态自洽，未发现阻止开展修复的题面问题。目标是通过 HTTP 代理连接时，`http://localhost:1234/path` 的 `req.path` 保留目标端口（题面解码行 7、27–30、38–47）。此结论只是静态读题；不是 actor 交付或 CPU 验收。

## 静态依据与边界

- `aiohttp/client.py:215–251` 分离 `host` 与 `port`，同时保存 `netloc`；`:268–294` 生成 `/path`。`aiohttp/connector.py:342–344` 拼接 scheme、host、path 而没有端口，与题面所述丢失 `:1234` 一致。这里是对可见 base 的推导，未运行复现。
- 示例使用真实 `ClientRequest` 和 `ProxyConnector.connect()`；`connector.py:213–220、251–272` 的默认 `resolve=False` 避开显式 DNS 调用，`:290–295` 的连接调用由题面已完成 Future 替代。`connect()` 的无超时分支（`:140–157`）可沿该路径获取模拟 transport/protocol。未见需要真实代理、遗漏 await 或与源码 API 名称冲突的问题。
- 示例仅检查连接后的路径，没有发出 HTTP 请求；题面关于“发往错误 URL”的网络后果未被此例直接验证。返回的 `Connection` 未保存，但它的关闭回调不改写 `req.path`（`connector.py:19–30`），静态上不影响所列断言。运行时清理、事件循环与旧版 asyncio 兼容性仍未知。
- 公开 `tests/test_connector.py:324–352` 明确要求无显式端口 URL 保持 `http://www.python.org/`；不能把本题解释为所有目标 URL 都必须追加默认端口。该文件 `:487–493` 仍要求 HTTPS CONNECT 使用 `www.python.org:443`。`tests/test_client.py:332–346` 要求 host 与 port 分离。这些回归与保留显式端口不矛盾，不能只为示例硬编码 `1234`。本次未把 HTTPS 或其它 URL 格式扩为新增题面要求。
- 题面提供可观察失败和预期输出，没有给出补丁、内部修法、隐藏测试名或私有验收值。对该公开目标，读者无需猜隐藏规则；更广覆盖和隐藏评测是否通过未核实。

## 未执行的验证建议

同目录 `public_reader_commands_20261003.json` 仅列出题面原例及公开 connector/client 回归。所有命令均未执行；例子在 base 上预期触发路径断言，修复后应通过。公开回归是否可收集、依赖是否齐全、具体失败与退出状态，均需在题面指定的 `/testbed` 环境实跑后确认。

## 已读文件字节 SHA-256

只静态读取源码、公开测试及目录内文件名；SHA 用于锁定此次观察，不表示执行过文件。搜索匹配行不等同完整文件审查。

| 文件 | SHA-256 |
| --- | --- |
| `aiohttp/connector.py` | `795fa39448073913a6ebea3f5cfeedea80794f7dbf2bce072a66a481df9ce623` |
| `aiohttp/client.py` | `10a13ca9e4fad3800860b98440fc57896217cf12a5bc09870497ca81019151ea` |
| `aiohttp/protocol.py` | `a4ec023ec23fe8b8f4b5cd236f04af57735d0ba2765af1ef77b6143706a1c76e` |
| `aiohttp/__init__.py` | `98cfca4cd18e33cc6fa10f2603d7aa8ec12d7e1756bed85fc376bed4fbe0c9e2` |
| `tests/test_connector.py` | `485cf8cf9c143be9e77a50e9d038362876f06e3815fe6209f9bc1cc60c16629d` |
| `tests/test_client.py` | `42f61a425fc39f6877ae0e74fab52460c57f026a00acc44394efcc92a35f54a0` |
