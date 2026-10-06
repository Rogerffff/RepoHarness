# 61833518 fresh 公开静态读题（2026-10-03）

仅使用本题 `public_reader_bundle.json` 与 `runs/r2e_static_prep_20260924/v3/public/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2/worktree/`。没有读取题目父目录的其它材料、私有题卡、review、候选、gold/hidden、历史 snapshot、4075 报告或其它线程；没有访问网络、调用模型工具、运行项目/测试、安装、SSH，或修改源码/题面。

## 输入核对

- 实际解码 `problem_statement` UTF-8 SHA-256：`ab73a3ec70cb08e3fd6846b8ceead6552ea82082d6f837fd9118787a0e4f004d`；与任务指定值及 bundle 字段一致。
- 实际 bundle 文件 SHA-256：`437f890e5e82959767ad5354d4b2c753cb1a8d43c5173c31408856ea7ef4a7ae`。
- 公开工作树存在。bundle 声明 base commit：`ff3dec422bd18b5e9078b5f29be1c9a6a1373f5a`；未读取工作树外 Git 元数据，因此没有独立核验 commit 对应关系。
- 下文“题面解码行”按 JSON 解码后的 `problem_statement` 从第 1 行 `[ISSUE]` 起计；源码和测试引用为指定工作树文件的实际行号。

## 结论

公开目标清楚，现行示例静态自洽，未发现与已读公开回归冲突的要求。目标是压缩响应的数据块不产生提前的零长度终止块，完整载荷发送后才发送合法终止块（题面解码行 5、8、46–52、56）。此结论只是静态读题；不是 actor 交付或 CPU 验收。

## 静态依据与边界

- `aiohttp/protocol.py:784–799` 压缩过滤器直接产出 `compress()` / `flush()` 的返回值；`:686–690` 把非 EOF/EOL 标记的输出直接交给 writer，未排除空字节。若压缩器暂时没有输出，`:713–728` 会按零长度数据生成 chunked 帧，之后 `write_eof()` 又生成正式终止块（`:704–720`）。因此提前 EOF 有公开源码依据；特定 zlib 的具体输出时机仍需实跑。
- 题面第一段（解码行 15–29）设置压缩后 Content-Length，先加分块过滤器再加 deflate。依据 `protocol.py:631–638`，这是定长 writer；`add_chunking_filter()` 只拆分数据，不决定 HTTP transfer encoding（`:406–421、760–781`）。它检查真实 `transport.write()` 字节是否为空，不能单独证明 HTTP chunked 无提前终止。第二段（题面解码行 31–52）不设 Content-Length，默认 HTTP/1.1（`protocol.py:821–823`），会启用 chunked；逐帧解析明确只允许末尾零块，并验证拼接数据可完整解压。两段覆盖互补，未把空写调用误等同于所有场景中的 HTTP 终止帧。
- 两段的 filter/API 调用与源码一致；过滤器顺序由 `protocol.py:423–434、439–475` 管道实现支持。示例使用 Mock transport，不依赖网络服务器。`call.args[0]` 读取的意图是实际 write 参数而非 mock.call 对象真值；目标环境的 `unittest.mock` 是否支持该属性、旧 aiohttp 能否导入、zlib 版本与具体运行结果均未验证。
- `tests/test_http_protocol.py:340–369` 要求普通 chunked 帧末尾保留合法 `0\r\n\r\n`；`:427–471` 要求 deflate 及两种过滤器顺序保留完整压缩字节。其中定长压缩断言拼接所有 write 参数，空字节对拼接结果没有影响，故这些测试可能未抓到本题的空写问题，但不要求保留空写。`:441–455` 的压缩后分块路径要求非空分块及末尾终止块，和题面一致。
- `tests/test_web_response.py:243–247` 要求写入空数据返回 `()`，没有要求 transport 必须收到空字节，未发现冲突。结论限于已读公开断言，不代表完整回归通过。
- 题面没有提供补丁位置、实现策略、隐藏测试名或私有验收数据。只凭公开内容即可理解合法末尾零块与非法提前零块的区别，无需猜隐藏规则；`all(chunks)` 是第一段公开观测要求，不应静默弱化成只检查最终拼接数据。

## 未执行的验证建议

同目录 `public_reader_commands_20261003.json` 仅列出题面原例及公开 protocol/web_response 回归。所有命令均未执行。base 上第一段预期可暴露空 write 参数；第一段断言失败后，同一脚本不会继续第二段，所以第二段的实际 wire 结果仍须另行观察或在修复后验证。修复后原例应整体退出 0，同时公开回归保留完整载荷和末尾终止块。依赖、收集、具体失败和退出状态均未知。

## 已读文件字节 SHA-256

只静态读取源码、公开测试及目录内文件名；SHA 用于锁定此次观察，不表示执行过文件。搜索匹配行不等同完整文件审查。

| 文件 | SHA-256 |
| --- | --- |
| `aiohttp/protocol.py` | `b8147e247a5fd628ae3d76739fc7546cb6309afc989bd7bac609066714d67aff` |
| `tests/test_http_protocol.py` | `5af72ee4479082b5f2fd56f11594f79904d14147320d97ef5d3a0f8742ee10b5` |
| `tests/test_web_response.py` | `f9c5e28d412a2af0cb0fd8d5a2597c68412224c563c43979ea7ffea5556bf71e` |
