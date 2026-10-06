# 1c1／240d R6 非作者反证核查

日期：2026-10-03。角色：Falsifier / Simplifier。结论：**评分语义方面可进入探索性 GPU 探针；未发现当前矩阵中的已知误拒或漏判阻断。** 本次结论只适用于固定 R6 材料和已核的 13 行 CPU 原件，真实执行与交付身份由并行 Production Tracer／主审查者合并核定，不授予训练或留出资格。

本审查接触私有测试、gold 和候选，属于非作者结果／语义审查，不能登记为 fresh 公开盲审。按 `review-standards.md` §10.4／§10.5 做一次离线窄核：只读文件，使用 `PYTHONDONTWRITEBYTECODE=1 python -B` 的标准库进行摘要、AST（语法树）和日志解析；未运行项目 pytest、候选代码、新矩阵、SSH、Docker、模型或安装。只新增本报告与 ignored 的本机摘要。

## 固定依据与独立方法

[固定 handoff](../review_handoff_1c1_240d_r6_cpu_20261003.json) SHA256 为 `dc7c0ac318fc1020ff0fdebb8e4b4b14aaba3ac5460ab6c9257563ca63ee50cb`。其中 92 个带 SHA 的引用全部逐字节匹配；另核 16 个公开控制原件，合计 108 个摘要检查，无不一致。两份作者 matrix JSON 仅用于定位材料与原件，没有继承其裁决。

- 固定 release：`cat2-cpu-r2e080087-swe8-git-20261003-v1`；manifest SHA256 `ab0a3a13fd65e0ea4cd60541ea3b37b01196170477e25832df246f33ea208828`。
- [1c1 作者读回](../results1c1_r6_matrix_20261003.json)：SHA256 `ad4f9744d9b696dd9015f6ab482c2443588a11d7f9896c02330622e9bde01508`。
- [240d 作者读回](../results240d_r6_matrix_20261003.json)：SHA256 `15a343c078ace43ddcc0569111453457d7183f59aadce55561da75c44809ccd1`。
- 固定 parser 源码 SHA256 `339b7c80cca516dc7d1bcf9c11e3ff9a42f1bc993b5027a0d06c41c85d024b58`。读取其首个 `short test summary info`、类名以点连接和失败说明截断规则，再用独立标准库解析重建状态；本角色没有 import／执行项目模块。

13 份完整日志均有唯一 Start／End Test Output 段、完整 pytest 收尾与 `RH2_TEST_RC`；状态集精确等于各题 expected 集合，没有缺键、意外键、SKIPPED 或 ERROR。日志状态独立重算后与 ledger 的 reward／expected_match 一致；reference_missing 均为 0、runner_integrity_changed 均为 false、日志均非 partial，setup 的隐藏树与文件完整性标记成立。原始补丁与实际 applied patch 字节相等；FrozenPatch 与 projection 只包含生产源码路径，没有候选测试／fixture 改动。逐键状态、失败段原始行号／摘要、全部相关 SHA 和路径保留在本机摘要；handoff 保存 13 份完整日志与各自 ledger／patch／FrozenPatch／projection 的固定路径。

## 1c1：关闭 C3 漏判，接受两条合理路线

隐藏材料 080、expected 081 只有一个增量：`test_run_app_cleanup_error_is_observable_after_interrupt[pyloop] = PASSED`，57→58。新 expected SHA256 为 `1bc0a6c74ee6fceb75b695d4d269c90f752deccf60b842db647a3602e1499370`，隐藏 `test_1.py` SHA256 为 `5b38ccd1dd8083acbcb8db229a471517512434a5caccdddf0461f418c181910d`。对旧固定源与新材料做字节 diff，结果恰好等于已固定 hidden_test.patch；移除新增函数后，两份模块 AST 完全相等。57 个旧键的状态期望和其它隐藏文件均保持，runner 字节不变；release 文件、实际 prepare context 文件与本包材料字节一致。

新测试先确认 yield 后的 cleanup 真正被执行，然后接受调用者收到带错误消息的 Exception，或 loop 的 exception handler 收到该消息。它没有要求特定异常类型、相同 task 操作、gold 的 suppress 路线或固定 loop 报告文案。

| 候选 | 完整状态 | 重算 reward | 实际区分的行为 |
| --- | --- | --- | --- |
| gold | 58 PASSED | 1 | 取消 main 后直接等待；只抑制 CancelledError，新 RuntimeError 可向调用者传播 |
| C1 | 58 PASSED | 1 | 已完成 main 不再重复报告；中断时待取消 main 仍由原 `_cancel_tasks` 报告新 cleanup 错误 |
| noop | 56 PASSED／2 FAILED | 0 | startup RuntimeError 与 server-start OSError 抛出后又调用异常处理器 |
| F1 | 57 PASSED／1 FAILED | 0 | 只特判 RuntimeError，server-start OSError 仍重复报告 |
| C5 | 51 PASSED／7 FAILED | 0 | 删除 main 的先行取消，全部 pending tasks 一起取消，破坏关闭顺序 |
| C3 | 57 PASSED／1 FAILED | 0 | 只 gather 并吞掉 main cleanup 的新异常 |

正对照是实质有效的：gold 与 C1 的 FrozenPatch 显示两条不同的异常可观察路线，且两者本轮都完整通过 58 键。成功测试没有另打印选择了哪条路线；上表的路线解释来自冻结源码与 asyncio 控制流，通过状态来自实际日志，并未补跑本地控制流模拟。

C3 的唯一失败栈在新测试末尾：`cleanup_reached = [True]`、`raised = ''`、`reports = []`、`reported = False`，断言为 `cleanup exception was silently lost`。它并非未到 cleanup 或环境失败；57 个旧键全部 PASSED。C3 的 `gather(main_task, return_exceptions=True)` 消费错误后没有报告，后续 `all_tasks()` 已不包含完成的 main，因此新错误丢失与候选改法相符。

noop 失败键为 `test_run_app_raises_exception[pyloop]` 和 `test_run_app_raises_exception_on_server_start_failure[pyloop]`，F1 只有后者失败；失败都在 `assert not m.called`，不是预置、网络或导入失败。C5 失败均在 `TestShutdown`：`test_shutdown_wait_for_handler`、`test_shutdown_timeout_handler`、`test_shutdown_timeout_not_reached`、`test_shutdown_new_conn_rejected`、`test_shutdown_pending_handler_responds`、`test_shutdown_close_websockets`、`test_shutdown_handler_cancellation_suppressed`。其中六项最终为 test task 的 CancelledError，websocket 项为 `client_finished=False`，与同时取消 cleanup 正在等待的测试／请求任务吻合。同镜像 gold／C1 通过这些旧键，且 C5 新键通过；不能把这七项候选关闭回归解释成新断言失效。

因此此次对 C3 从旧材料得 1 改为新材料得 0 有具体证据，原 noop／F1／C5 区分能力没有被删弱。

## 240d：只窄移除失效兼容测试，端口目标保留

隐藏 083、expected 084 仅删除 `HttpClientConnectorTests.test_tcp_connector` 与 `HttpClientConnectorTests.test_unix_connector` 两个已登记 FAILED 键及对应测试函数，35→33。新 expected SHA256 为 `8dab59950c1837a195f854e669fc3778200025beaf29431864e58a2ebe3a3c70`，隐藏 `test_1.py` SHA256 为 `77b15aea1c9557adb5c686c4ff12055609578eecacfd754a2001cbe32dc8b18a`。未新增 skip，未将 FAILED 改成 PASSED。移除旧模块的这两个函数后，模块 AST 与新模块完全相等；33 旧有效键的期望状态和其它隐藏文件保留，runner 字节不变，release／prepare context／本包材料字节一致。

| 候选 | 完整状态 | 重算 reward | 实际区分的行为 |
| --- | --- | --- | --- |
| gold | 33 PASSED | 1 | 用 req.netloc 构造代理绝对请求路径 |
| AL1 | 33 PASSED | 1 | 用 req.host／req.port 与默认端口规则构造路径，保留非默认端口 |
| SC1 | 33 PASSED | 1 | 与 gold 相同的 req.netloc 修复，另补协程 decorator |
| noop | 31 PASSED／2 FAILED | 0 | 两条 HTTP 请求路径分别丢掉 1234 和 8080 |
| DG1 | 32 PASSED／1 FAILED | 0 | 只硬编码示例 1234，非示例 8080 丢失 |
| WR1 | 32 PASSED／1 FAILED | 0 | 全局 req.host 带端口，CONNECT 端口重复 |
| WR2 | 32 PASSED／1 FAILED | 0 | 代理内将 req.host 改成 netloc，CONNECT 端口重复 |

DG1 唯一失败 `ProxyConnectorTests.test_request_port_other_url`：实际 `http://www.python.org/some/path`，期望 `http://www.python.org:8080/some/path`。WR1／WR2 唯一失败 `ProxyConnectorTests.test_https_connect_port`：CONNECT method 的断言已通过，随后 actual `www.python.org:8443:8443` 对 expected `www.python.org:8443`。noop 的两个失败也分别是缺少 1234／8080 的 req.path。这些全部是候选语义断言，执行已经到目标字段比较；未被失效 TCP／Unix 环境故障驱动。

**需收紧正对照的说明：** 当前证据证明 gold 与 AL1 两种端口构造路线可以通过；SC1 是 gold 核心修法加兼容变体，不能把三项正对照算成三种独立端口修法。AL1 证明测试不要求访问 req.netloc 或照抄 gold；SC1 证明附加合理兼容改动未被此次窄删除误拒。这里认可的是本题已测端口行为，不是所有 URL 形式、端口拼写保留或整个旧客户端／服务端兼容性。

公开 Future 复现没有换目标：真实 `ClientRequest`、已完成 Future 与 `ProxyConnector.connect(req)` 最终观察 req.path；公开控制实际命令片段与 `materials/240da100/public_repro.py` 字节相等，且该片段存在于 082 正式题面。公开 base 原件实际打印 `http://localhost/path` 并触发 AssertionError，gold 实际打印 `http://localhost:1234/path`。它与正式私有的示例端口／非示例端口测试观察同一字段，mock 替换 transport 只移除了网络需求。复用公开 13 项回归及已审 brief／fresh 阅读意见，未重复做新的公开盲审，也未把公开 13 项当完整 33 键评分。

## 剩余未知、比例裁决与停止条件

没有新增当前阻断性 finding。按 §10.5，保留 `no_fix_accept_residual_risk`：单个 RuntimeError cleanup 场景未覆盖所有未来异常包装形式；只把原异常消息放在 `__cause__`、而顶层 str 和 handler context 均不带消息的实现可能被此断言拒绝。这是尚无本轮实际候选或 GPU 轨迹证明的条件性边界，现阶段不为它扩候选或新增兼容协议。若后续真实候选出现这种可辩护的可观察路线，再用具体轨迹开启对应题目的窄核。

240d 的公开 Future／33 键矩阵不证明删除的真实 TCP／Unix 能力已修复，也不证明所有端口、默认端口文本形式或 URL 类型全覆盖。两题矩阵各只执行本轮固定一组；本次离线读回不能提供重跑稳定性频率。

停止条件已满足：材料只有授权增删，13 行精确键集完整，已知错误候选被拒，有不同合理实现的正对照通过，失败均能定位到候选目标行为。本角色建议复用当前 CPU 证据进入同 R6 身份下的探索性 GPU；不重复 13 行、不新添候选、不扩到 4075／6183、训练或留出准入。GPU 仍核公开题面和 brief 的实际送达，并保留模型原始补丁直评证据；若真实运行产生已知误拒／漏判或新材料身份偏离，此建议停止适用。并行主审查者的具体执行身份检查若不成立，也不能凭本报告放行。

## 本轮日志摘要与完整证据入口

下表的 SHA256 均为完整 eval.log，而非截取尾部。完整路径、所有 ledger／候选原件／FrozenPatch／projection 摘要由固定 handoff 定位，本机摘要另保留各失败段行号和逐键状态。

| 题目／候选 | 完整日志 SHA256 |
| --- | --- |
| 1c1c0ea3／gold | `7318d696013ed6ae6453ac1183fc36b6d0236dac797068b05c3a2d32c5807a08` |
| 1c1c0ea3／noop | `f7f17971e436c6d033e713d7dc56beb6d0350f997ddc5cc438be319acba5a6db` |
| 1c1c0ea3／F1 | `d7b81ab9866ce63d81d8e4807a2e740b0073e3a77cabde06483bc5d2daa7277a` |
| 1c1c0ea3／C5 | `7761fe5d038bf86db82c6ea63078e36b3b3c8f0d502e63d82190d7d37718900f` |
| 1c1c0ea3／C1 | `48ddda668052cf07c79ddc0a282c41de847780cd65f68875f00ddd079374aa1c` |
| 1c1c0ea3／C3 | `f6222a230b818a4864a2fe7114e7b92c84160684f0cd5349f48ffe0f3771a1e8` |
| 240da100／gold | `a05fe90a78bd256bc62825cb32e4036b913e7023aeb0b1243987650593707efb` |
| 240da100／noop | `a2270a0338562969b30cb101feeb5557c7c1e863d3ad7dcf060cc6ce0d360c7c` |
| 240da100／DG1 | `dea710b4272a1a165c00df3326db173098b86ce6528f46fd533be3a415bdf0d1` |
| 240da100／WR1 | `d362d63ded9ecfb5612bd4ebe707e365005f8d37bdcbd34c26bf436f24c1e321` |
| 240da100／WR2 | `fdd0d503b39efc98b03236049c65643c936e4b464029fa89448f8d614e324ec5` |
| 240da100／AL1 | `f670b69e33df73ee7d4317bca59a5c3b900f33fcc80c6e3fb65585f945f6fc00` |
| 240da100／SC1 | `704e14243e5dc0b62d01a624e36d960cac70935a07bee084c024a98a845145e9` |

本机摘要：`runs/category2_repair_20260929/r2e_aiohttp/non_author_r6_falsifier_20261003/summary.json`，SHA256 `623aa20fc13b43a664af53b7ceb0da8da8f5d1bcf65b5e829eba78fe0eec7997`。摘要是 ignored 的本轮证据索引，不回写历史原件。

本轮未改变已定案评分语义、材料、生产实现、共享 registry 或训练／留出资格。
