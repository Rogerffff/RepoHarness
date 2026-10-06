# aiohttp 四题：非作者静态材料窄核

2026-10-03，Asia/Singapore。审查身份：Codex 非作者；已接触私有测试、历史候选与验收记录，**不是 fresh 公开读者**。

结论：1c1、240d、4075 的本轮材料在限定问题上可接受；6183 的复现代码中性且覆盖约定行为，但题面 Expected Behavior 应在正式冻结前澄清“数据 chunk”和“终止 chunk”的区别。本次没有发现需要扩大评分范围、增加候选或修改公共摄入工具的问题。四题仍未完成新版本 CPU 验收或正式公开发布，本报告不授予训练／留出资格。

## 范围、身份与检查方法

只审 [preparation.md](../preparation.md)、[revision_draft.json](../revision_draft.json)、[material_manifest.json](../material_manifest.json) 与 `materials/`；按需对照 9月29日库存、4075 专项验收、三题题卡的精确片段及已有复现命令。重点为测试有效性、公共目标一致性、真实入口、材料身份和公开／私有分离。没有开展 A~N 全量切片或集成审计；性能、训练运行时、正式发布消费路径等不在此次静态任务范围。

审查版本：

- `revision_draft.json`：`sha256:7317999c74f70569e56f2c5f8c3433494bc4df284cb5d8724b11125a4823abe4`。
- `material_manifest.json`：`sha256:8c55ff3b55eac4ca07942c4109d63d4381beb0dc0f8c10c820caf0e59db5e935`。

检查仅使用文本读取、JSON 解析、SHA256 重算与 AST 比较，未执行题目代码、项目／维护测试或作者验证脚本；未 SSH、启动容器、安装依赖或访问网络。唯一新写文件为本报告，创建前确认不存在，并用排他创建防止覆盖。

静态结果：

- 清单登记的四个父材料文件 SHA256 与当前文件一致；全部 `local_files` 摘要一致。
- 从 raw 原测试按 v11 的现行正式 edits 重建父版本，再做 AST 比较：1c1 只新增一个测试函数；240d 只删除两个方法；其余函数 AST 均相同。没有凭草案自称的 patch 范围下结论。
- 直接对当前 grading bundle 的 expected 映射比较：1c1 为 57→58，只新增 `test_run_app_cleanup_error_is_observable_after_interrupt[pyloop]=PASSED`；240d 为 35→33，只删除两个原 FAILED 键，其余值逐项不变。
- 四个 `public_reader_bundle.json` 均只包含原公开字段；1c1 原样，另三题只改变 `problem_statement` 与其摘要。公开题面全文与对应 bundle 一致，240d／6183 的 `public_repro.py` 与题面代码块一致。没有附加私有测试、gold、候选或验收矩阵。
- 两份修改后私有测试及两份独立公开复现代码均可作 AST 解析。此结果不是目标 Linux 镜像中的导入、收集或执行成功。

## 1c1c0ea3：抛出或报告均可，静默吞错不满足断言

材料：[test_1.py](../materials/1c1c0ea3/test_1.py)，新增函数第946–974行；[hidden_test.patch](../materials/1c1c0ea3/hidden_test.patch)。

第952–955行在 cleanup context 的 `yield` 后记录 `cleanup_reached`，再抛出新消息的 `RuntimeError`。第962–964行走 `web.run_app()`，复用第58–77行的 `patched_loop` 和 `stopper`：server 创建被 mock 替代，停止通过事件循环调度的 `KeyboardInterrupt` 触发，未把异常直接从测试主体抛出当作目标复现。

第965–966行接受抛给调用者的异常；第959及969–973行收集 loop 异常处理器报告。第974行用 OR 接受任一路线，没有要求与 gold 相同的报告方式、固定 traceback、任务名称或 handler context 全字段。第968行要求实际走到 cleanup，避免未清理就正常返回的假通过。

对已登记 C3 的静态反查：`runs/r2e_actor_20260925/grader_cands/aiohttp_1c1c_C3_gather_swallow.patch` 将主任务取消后交给 `gather(return_exceptions=True)`，结果被忽略；随后其他任务清理不再检查该主任务错误。若沿既有行为执行，`cleanup_reached` 为真，而抛出消息和 handler 报告均为空，必定不满足第974行。它不是仅凭错误测试名或退出码“推定拒绝”。实际新材料下 C3=0、gold／C1=1 仍需正式六方运行证明。

原服务器启动失败“不重复报告”测试第926–943行，后台任务报告测试第826–856行，以及原关闭顺序测试均保留；AST 比较未发现修改。原公开题面未变。结论：**本轮断言设计可接受；执行拒绝效果待 CPU 验收。**

## 240da100：只删两项兼容失效方法，Future 复现沿旧有效入口

材料：[hidden_test.patch](../materials/240da100/hidden_test.patch)、[expected_output.json](../materials/240da100/expected_output.json)、[public_repro.py](../materials/240da100/public_repro.py)。

对父版本的实际差异仅删除 `HttpClientConnectorTests.test_tcp_connector`、`test_unix_connector`，包括后者原 AF_UNIX skip 装饰器；没有新增 skip、修改现存方法、调整其它期望值或把 FAILED 改为 PASSED。两个失效方法留下的空测试类只保留原 setUp／tearDown，不产生新测试键。其余33个有效键及全部代理／CONNECT 方法保留，包括原题面端口、非示例8080端口和显式8443 CONNECT 的断言（最终测试第556–600行）。

草案 `r2e-mr-994/995` 相对 raw 仍包含上一版添加的两个代理测试，所以其 `expected_change.added` 不等于“本轮又加两键”；对当前 v11 grading bundle 的真实变化只有删除两键。`publish_replaces` 登记替换原 `r2e-mr-051/052` 与这个事实一致。

R-f 的第6–15行将 mock transport／protocol 装入由真实 loop 创建的已完成 Future，mock 的仅是 `create_connection()` 返回值；仍调用真实 `ProxyConnector.connect(req)`，未 mock `req.path`、代理 URL 拼接或目标函数返回值。它沿原代码 `BaseConnector.connect()` → `ProxyConnector._create_connection()` → transport connection 的路径执行。

旧对应原件为 `runs/r2e_lifecycle_20260929/devcheck_rev/v7/aiohttp__240da100151933883d7dea0528d45877df025b92/orig/commands_with_preflight.json` 中 `repro_port_mocked`：同样用已完成 Future 返回 transport／protocol，经 `connect()` 得到路径。其 `orig/captures/repro_port_mocked.out` 第7–8行实录 base 两入口均为 `http://localhost/path`，第1–3行有完整断言失败。新片段把 `asyncio.Future(loop=loop)` 改为 `loop.create_future()`，显式将同一 loop 传给 `ClientRequest`，并加关闭步骤；没有改代理行为或增加默认端口／Host 目标。

题卡 `probe_card.md` 第26行记录该旧命令 agent base 非零和私有 gold 零；后者是 root 私有对照，本报告没有将其升级成新公开 actor 验收。结论：**范围与历史复现路线可接受；新材料七方评分、SC1 正对照及最终 agent 复现仍待执行。**

## 4075c653：只去掉第一次 encode，未泄露修法

材料：[statement.patch](../materials/4075c653/statement.patch)，[problem_statement.txt](../materials/4075c653/problem_statement.txt) 第10–11行。

唯一改动为 `invalid_header = "\xffoo: bar"`，保留整个 request 的 `.encode()`。这样插入的是字符串字段名，UTF-8 编码后真实包含非 ASCII 字节；旧写法会将 bytes 的文本表示插进 f-string，实际输入与题面宣称不符。没有修改第二例、异常类型、原要求或评分材料，也没有指向修改函数／给出源码补丁。

[4075专项验收](../../../r2e/aiohttp4075_acceptance.md) 的“尚未通过的公开复现”已经核定此精确修法，并保留 v11 七方评分和 ALT2 正对照结论。结论：**此 R-f 可接受；最终 agent 对 base／ALT2 的复现、干净公开阅读和实际题面交付仍待完成。**

## 61833518：代码中性；Expected Behavior 需消除终止块歧义

材料：[public_repro.py](../materials/61833518/public_repro.py)、[problem_statement.txt](../materials/61833518/problem_statement.txt)。

代码第1–19行定义全部变量，通过 `transport.write.call_args_list` 读取实际字节，替代旧 `all(write.mock_calls)` 的恒真检查。第一段保留原 Content-Length 与 chunking filter 配置，没有把原样例范围丢掉。第二段第21–42行走无 Content-Length 的 HTTP/1.1 chunked 路径，检查线上 header、分块字节、终止块位置及 deflate 解压后载荷完整性。

第36–38行接受末尾合法零终止块，同时拒绝后面仍有数据的提前 EOF；合并非空 write、却把空数据块编码成 `0\r\n\r\n` 的 AP1m 仍会违反该断言。它检查线上语义，不规定源码应在 compression filter 还是 writer 修复，也不规定 write 次数。对应行为已登记于旧题卡第25行和 revision_plan 第156–163行；未新增 gzip、HTTP/1.0、大载荷或未经过滤器的 `write(b'')` 要求。公开代码没有候选名称、私有路径、补丁、函数修法提示。

### Finding AIO-MAT-01：澄清数据块与合法终止块（P2，正式题面冻结前）

- **当前行为／位置：**`materials/61833518/problem_statement.txt:56` 仍写 `All chunks sent in the compressed, chunked response should have a size greater than zero`；同页第8行明确末尾零终止块合法，第46–48行的代码也接受它。相同文字已进入 `materials/61833518/public_reader_bundle.json` 的 `problem_statement`。
- **违反的不变量：**公开验收要求应与复现断言一致，不能让“全部 chunk 大于零”的字面要求覆盖合法的终止 chunk。这里可以推断原文说的是数据块，但正式材料不应要求读者自行消歧。
- **具体反例／证据：**旧题卡第25行记录私有 gold 的完整正文为 `6\r\nKI,I\x04\x00\r\n0\r\n\r\n`。它包含 size=0 的末尾终止块，符合本页第8行与新增代码，也符合原题“不提前 EOF”的目标；若按第56行的 all chunks 字面读法，却不符合 Expected Behavior。此反例来自已有原件，本轮没有执行代码。
- **影响与可达性：**`test_only`／公开材料语义；影响正式送达题面的需求理解，不是已观测的评分错误。没有证据表明应推翻 v5 评分或重跑不变六方矩阵。
- **建议分期：**正式 R-f 冻结前仅澄清为非终止数据块必须非空，零终止块应在末尾且之前应交付完整载荷。无需新候选、新行为目标或源码修改；现在修是因为这正属于本轮修订的同一份公开题面。
- **验收条件：**只修改相关 Expected Behavior 句子并同步公开 bundle、statement patch、修订摘要与清单；保留既有两段代码和原评分材料。后续干净公开读者能读出“合法零终止块允许，提前 EOF 不允许”，且最终 actor 分别执行两段以证明目标行为。该文字修正后的新摘要不由本报告自动背书。

因此 6183 的**复现代码窄核可接受，题面文字保留上述待修项**。

## 停止条件与交接

本次限定材料窄核已完成，没有重新审查历史完整矩阵、沿理论反例扩展候选或改作者材料。作者的 [local_validation.json](../local_validation.json) 明确是生产摄入纯函数重放，`cpu_acceptance=not_run`、未捕获实际 solver 消息；本报告仅增加非作者静态证据，未将其升级成 CPU 或正式发布验收。

继续事项沿准备入口既有安排：1c1／240d 新材料分别做原登记六方／七方 CPU 验收；4075／6183 复用不变评分证据，完成最终公开复现、fresh 公开阅读和正式发布／实际送达核对。公开读者应只收到相应 `public_reader_bundle.json` 与原公开工作树，不应收到本报告或其它私有材料。没有新增审批闸门。
