# aiohttp 三个新增公开开发 brief：非作者窄核

2026-10-03（Asia/Singapore）。结论：**1c1、240d、6183 的指定 SHA 版本均可按原流程用于后续公开交付；本轮没有阻断项，也没有必须修正文案的事实错误。** 这仅核销新增 brief 的内容依据和公开边界，不是新正式矩阵、最终题面送达、基座能力或训练资格验收。

## 范围与审查身份

固定入口为 `review_handoff_briefs_20261003.json`（SHA256 `18f4e8fdb80f0544877c0a0087cdb7c8fda17389e60275199d1bdde5685c729b`）。仅审三个 `new_brief`；4075 未重审。本轮只使用本地文本、stdlib JSON/SHA256 和公开日志抽取，没有 SSH、Docker、模型调用、安装、项目测试或新增运行。只新增本报告及 ignored 机器摘要，未改 brief、原件、材料或共享登记。

这是**非作者窄核，不是 fresh／盲审**。首次读取作者结果导航时输出包含 gold 控制结果、私有材料摘要／数量和补丁摘要；复用既有静态审查时见到候选名称及 hidden 断言片段。没有打开候选补丁、hidden 实现或私有评分原件正文。后续事实核对选用公开题面、公开固定命令、base 的公开 actor 输出及生命周期记录；摘要只作导航，关键事实来自原件。

按审查标准 §10.5 的比例原则，本轮主要核 E（命令及输出有效性）、F/H（事实及版本一致性）、G（真实公开入口）、I（验证范围）及公开／私有边界。不是新 CLI、公共机制、训练运行时或完整题级审计，不展开其余维度、不重做已完成静态／CPU 证明。停止条件为三个新增 brief 各完成一次核对。

## 摘要绑定与复用

以下 SHA256 省略统一的 `sha256:` 前缀，均重新计算并匹配交接包。

| 题目 | brief | public bundle | 解码 problem_statement | public commands |
| --- | --- | --- | --- | --- |
| 1c1 | `8fa9daeae7d032d109ea073f53e8a2131567352318ba015c32ccae655da22909` | `d171e62df4ef8d9869d7e253043522400e1156328f05381d0ce73b0cecf94b47` | `b66629f137ff1c11b95f9c4cadc257ae2963b40abdbd54a735077dbb16039d85` | `d753da991cd42bfbf6323393058810e0159f572bf7ccf450ec8563ede4439277` |
| 240d | `d99fa9ea660d6321729f26cf87542da4fda02674ec06426af9a676f2b0631908` | `0dbe259cecdfe87950b5a9ad815251b9cdd0044c2b30a2ec5162c66a9b3102be` | `d3ff12a9a27890831dcedc62d53e8c124647d6fe036c28712505ed247d7a272c` | `eaf37eb58e028a4cd7145b31825221ee0f64adaa924d3381de0ebb8a8b8f3850` |
| 6183 | `f1636164b5669015333ba0281f73dc696c8ac803c0b914246fb1a083b01b233e` | `437f890e5e82959767ad5354d4b2c753cb1a8d43c5173c31408856ea7ef4a7ae` | `ab73a3ec70cb08e3fd6846b8ceead6552ea82082d6f837fd9118787a0e4f004d` | `97ed5bd8c54db71108610e81cee4ef84816d0e78216bd2ecadb08e4793177c2f` |

复用资料及 SHA：

- [材料窄核](non_author_material_review_20261003.md)：`4fde363c448756516b0738be9423e05bf610ab9606ad315fda51e348c13730d4`。只复用相关静态结论；6183 首版 finding 的历史待修状态由下述修正报告核销。
- [公开 actor wrapper 窄核](non_author_public_actor_wrapper_review_20261003.md)：`c7c5dbd6b79b10073bbaf62116a9256dea8556e67a515f3225f60b46d7b8999b`。固定 wrapper 文件当前 SHA 为 `fdaa801421ff52a030eac3680603a73a0658e4dba4c1cf9ecb653e4973828263`，与其审查绑定一致；没有重审或换版重跑。
- [240d 公开读题](../materials/240da100/public_reader_review_20261003.md)：`8b12dde7962ef0af4ae2e33b3e08790a266dc27d67c3ad686378bf1b51fe159d`。
- [6183 公开读题](../materials/61833518/public_reader_review_20261003.md)：`515c50204afa4465e1e1d430b0c20f3d29daa6665f8128582dece154641a51b4`。
- [6183 文案修正复核](non_author_6183_correction_review_20261003.md)：`15566e634b98c19551ff13aa5418d3cc169aa961c8ce7670fbfa113bd67f460a`。当前题面明确允许末尾合法零终止块，与 brief 第13行一致。

原件根目录：

- **R5**：`runs/category2_repair_20260929/r2e_aiohttp/cpu-b/public_actor1c1_240d_draftdev_r5_v1/final_artifacts/`。receipt SHA `81399508021d47a51f882caba1aba560f266357f4515f4af7ca4c1c3dfb67e7d`；99/99 登记原件的字节摘要与长度吻合。
- **R4**：`runs/category2_repair_20260929/r2e_aiohttp/cpu-b/public_actor6183_draftdev_r4_v1/final_artifacts/`。receipt SHA `5aca3f0466fb395fd6810aba312d0bbaca07546263e57441199a7e313f509e3b`；59/59 登记原件的字节摘要与长度吻合。

上述摘要核对包含 receipt 登记的私有文件字节，但未解析其正文。两份 receipt 合计158个登记原件；1c1 和240d 共用同一份99文件 receipt，不重复计数。逐题 base 的 `commands_with_preflight.json` 与指定公开 commands 逐命令一致；从 `harness/trajectory.jsonl` 抽取实际 Bash 的 `bash -c` 参数后，同样逐字节匹配全部公开命令。完整输出均小于 capture 的200000字节上限。

## 1c1：可用；退出零不能核销重复日志

对应 [公开 brief](../public/1c1_development_brief.md) 第3、5、10–14行。证据路径以 R5 根目录下的 `aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/base/` 为前缀。

- `captures/public_environment.out:1` 实录 Python 3.9.21、`/testbed/.venv/bin/python`、aiohttp `3.10.6.dev0`、源码 `/testbed/aiohttp/__init__.py` 和 UID/GID54321；第3行是 `RH2_BASHENV_WRITE=DENIED`。`prelaunch.json` 的 PATH／VIRTUAL_ENV、工作区和外网拒绝探针支持第3行环境说明。
- `captures/pr1_1_cmd.out:1–2` 为 `raised: RuntimeError('Unexpected error occurred')` 和1条相关 `asyncio` 日志。`attempt.json.commands_result` 实录该命令 rc=0：因为脚本捕获异常后报告结果。因此第5行要求分别看传播与日志、不凭 rc0 判修复，直接受到原件支持。
- `captures/public_run_app_tests.out:192` 是55 passed、32.48s；第181–190行列出关闭、等待 handler、websocket／keepalive 和信号测试，其中9.53s、4.03s、2.52s等等待支持第14行说明。公开固定命令恰为 `tests/test_run_app.py`。
- `attempt.json` SHA `05d8d99f3d65c57800c3f6b50139bbaee73dd8a27a37a37277ba5e9adb37b44b`；结束于18:05:00Z，termination=returned，cleanup 显示 container_rm=0、stub_rc=0，network／relay失败及容器／网络残留列表全部为空。

**阻断：无。非阻断：无必改文案。未覆盖：**新58键正式矩阵、全部修法正确性、实际模型求解、最终送达与训练／留出资格。55项公开回归在有症状的 base 上也通过，不能替代目标症状或新评分结论。brief 没有作出这些扩大宣称，也没有附 hidden 名称、私有评分、gold 或候选修法。

## 240d：可用；明确限制为 mock transport 代理测试

对应 [公开 brief](../public/240d_development_brief.md) 第3、5、11–15行。证据前缀为 R5 下的 `aiohttp__240da100151933883d7dea0528d45877df025b92/base/`。

- `captures/public_environment.out:1` 实录相同解释器与身份、aiohttp `0.9.1dev`；`prelaunch.json` 外网拒绝探针和已结束命令支持旧版、已装依赖与无外网说明。
- 题面与实际 `proxy_port_example` 命令都从 `aiohttp.client` 导入 `ClientRequest`，创建已完成 Future，并调用真实 `connector.connect(req)`；替换的是 `create_connection` 的返回值。没有启动代理或 mock 目标路径结果。`captures/proxy_port_example.out:1、4` 实录 `http://localhost/path` 与 AssertionError，rc=1，支持第5行所述观察路线。
- `captures/public_proxy_tests.out:140` 为13 passed、43 warnings、0.44s；警告正文包含旧 `@coroutine` API 的弃用警告。固定命令只选择 `tests/test_connector.py::ProxyConnectorTests`，第15行主动披露其它 TCP／Unix 客户端和服务端模块未验证，与执行范围一致。
- `attempt.json` SHA `255777e815292f85d2eb63e1f0824d9ce978be656e70572f670e0e34a3684ef1`；结束于18:07:03Z，termination=returned；cleanup 与1c1相同，失败及残留列表为空。

**阻断：无。非阻断：无必改文案。未覆盖：**新33键正式矩阵、真实网络请求后果、最终新题面实际送达、模型求解和训练／留出资格。brief 没有宣称真实 TCP／Unix 验证，不暴露私有评分或指定实现策略。

## 6183：可用；分别观察空 write 与提前终止块

对应 [公开 brief](../public/6183_development_brief.md) 第3、5、8–13、19–23行。证据前缀为 R4 下的 `base/`。

- `captures/public_environment.out:1` 实录 Python 3.9.21、相同解释器与UID/GID、aiohttp `0.17.0a0`；`prelaunch.json` 支持工作区、PATH和外网拒绝说明。
- 公开题面的两段共享 imports／payload；固定 commands 将它们拆为两个独立脚本，分别完整导入，并在第二段定义 `payload = b'data'`。`captures/length_write_example.out:3` 实录两个 `b''` write 参数，rc=1；`captures/chunked_wire_example.out:3` 是 `AssertionError: data after the terminating chunk`，rc=1。实际 actor 轨迹也分别执行两段，因此第5行拆开观察、第13行区分实际 write 参数与线上帧的说明有直接依据。
- `captures/public_protocol_tests.out:266` 为47 passed、63 warnings、0.41s；正文包含旧 `@coroutine` API 弃用警告。第23行只说这一条命令的开发范围，未把47项公开回归说成目标修复或全仓验收。
- `attempt.json` SHA `8f12e3696409c4b06ca67de376cb1df4935c9a622a8ed95f5d5fd2528dd7cd97`；结束于17:56:31Z，termination=returned；cleanup 删除结果正常，无失败或残留。

**阻断：无。非阻断：无必改文案。未覆盖：**R4 prepared 使用旧公开题面，`run_summary.json` 明确 `final_revised_statement_delivery_proven=false`；本轮不能据此验收最终085/R6送达。HTTP/1.0、gzip、其它客户端／服务端、全仓兼容、模型求解和训练资格均未覆盖。两段代码与当前题面完全对应、公开语义中性，brief 没有暴露评分、gold、候选名或补丁位置，也没有限定只能修改某个内部函数。

## 后续用途与停止条件

本轮结论只到“这三个指定版本 brief 可作为后续公开交付的开发说明”。R5 为 `cat2-cpu-r2e078079-swe7-git-20261003-v1`，R4 为 `cat2-cpu-r2e070077-swe6-20261003-v1`；与最终 R6 的发行、prepared、正式材料及交付状态差异保留。既有静态／wrapper／公开读题结论按相同SHA复用，不强制因正式发行更新而重新跑不变工具检查。正式新1c1／240d矩阵和6183最终085交付按原流程另核，本报告不提前批准。

三个新增 brief 均完成一轮窄核，已达到本任务停止条件；没有新增准入要求。机器摘要为 `runs/category2_repair_20260929/r2e_aiohttp/non_author_public_briefs_20261003/summary.json`，保存逐题摘要、base原件SHA、实际命令匹配、清理和158个receipt登记原件的核对结果。
