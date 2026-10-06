# aiohttp 四题：当前准备入口

2026-10-03，Asia/Singapore。用户已指定“R2E | aiohttp 题目修订”为持续负责人；工作包 `r2e_aiohttp`，线程 ID `01a0fd63-99aa-7af0-94bb-591d3c151b17`。本轮只做本地材料准备和轻量检查，未启动容器、远端实验或模型；四题仍待相应验收，尚未提交 GPU 队列。

总协调维护工作包总表，本包只写本目录。历史证据、共享评分／ingest 代码、pins、正式修订单和探针脚本均未由本包修改。9月29日库存的 `next_action` 是快照；本页接续其中尚未关闭的缺口，不沿用更早的 `probe_ready` 或“可选修复”结论。

| 题目 | 本轮材料 | 可复用证据 | 等机器与复核的工作 |
|---|---|---|---|
| 4075c653 | 题面去掉字段名赋值处多余的 `.encode()` | v11 七方评分、136键逐项核对、ALT2/ALT1 正对照、已有 actor 开发与公开回归 | 干净公开读者；正式题面发布和实际消息核对；修后复现由 agent 对 base／ALT2 执行 |
| 1c1c0ea3 | 隐藏测试新增 cleanup 错误可观察性断言，接受抛出或报告；57→58键 | v5 六方正式对照和 cleanup 后检，原服务器启动失败断言与关闭顺序证据 | 非作者核新增断言；新材料正式六方评分和完整失败堆栈 |
| 240da100 | 无网络 mock 公开复现；草案移除两个真实 TCP/Unix 兼容失效测试，35→33键 | v7 七方正式对照、SC1 私有行为、mock 端口复现 | 非作者核移除范围；干净公开读者；新材料正式七方评分；agent 执行复现与目标相关开发路径 |
| 61833518 | 公开复现定义全部变量，检查 write 实参及 chunked 线上字节和解压载荷 | v5 六方评分、新断言对 AP1m 的提前 EOF 失败证据、既有 protocol 层复现 | 干净公开读者；agent 对最终复现和等效公开开发路径验证；正式交付与原工件接收 |

## 具体材料与验证边界

- [机器可读修订草案](revision_draft.json)：七条草案操作。`r2e-mr-990` 起的编号只用于本地解析，不是申请或预留的正式编号。`revised_file` 是未来发布路径，目前全文仅在本包 `materials/` 中。
- [材料清单](material_manifest.json)：固定父材料摘要、当前评分材料身份、各题修订文件摘要及期望键增删。四题题号不变。
- [本地检查结果](local_validation.json)：调用现有生产摄入纯函数，检查文本重放、摘要、键变化和公开／私有分离；不是正式摄入发布、评分、actor 验收或训练资格。
- [cleanup 控制流隔离检查](cleanup_control_flow_check.json)：执行原 web.py 与 gold/C1/C3 补丁中的 `run_app`／`_cancel_tasks`，以 async generator 替代 Application/AppRunner 和网络。新增断言接受 base／gold／C1、拒绝 C3；base 仅通过此新增断言，原目标仍失败。此检查使用本地 Python3.12，不顶替正式 Linux/Python3.9 环境的58键验收。
- 修订前后差异分别在 `materials/<题目前8位>/statement.patch` 和 `hidden_test.patch`。公开读者只接收对应的 `public_reader_bundle.json` 与原公开工作树；不得接收本页、私有测试、gold、候选或验收矩阵。
- [准备脚本](prepare_materials.py)与[检查脚本](validate_materials.py)只在本包输出。草案冻结后，不用重新生成覆盖已审版本；后续修正需保留旧版本及其结果。

## 逐题验收矩阵与已知限制

### 4075c653

评分与 expected 不变，复用 [独立验收](../../r2e/aiohttp4075_acceptance.md)及原件 `runs/r2e_lifecycle_20260929/codex_status_check_20260929_1020/formal_v11/`。不重复七方矩阵。ALT2 为主正对照，ALT1 为备选；原 gold 按已修订要求应为0，不把它作为正对照。

新增工作限于题面：base 接受修正后的非法字段名，ALT2 拒绝；以 actor 身份执行并保存完整输出。正式公开题面与实际送达文本须绑定新摘要。三个 C 扩展预期 FAILED 键保留既有纯 Python 范围解释；若启用新的 C 扩展构建路径，须另核其 expected，不能把环境变化当候选错误。

### 1c1c0ea3

新增测试复用公开 `patched_loop` 和 `stopper`，无需真实网络服务器。cleanup context 在 yield 后抛出新消息的 RuntimeError；必须实际走到 cleanup，且异常向调用者或 loop 异常处理器可见。不会强制与 gold 使用同一种路线。代码位于 `materials/1c1c0ea3/test_1.py`，差异只新增此函数。

新版本预期：gold／C1=1；noop／F1／C5／C3=0。C3 原 v5 得1，正是此次需要关闭的漏判；其余独立机制的候选继续保留。保存完整测试段、精确键集和异常／清理证据，不凭退出码或失败键名称推定原因。旧关闭顺序与后台异常报告断言不删。

### 240da100

选择 R-a 窄移除路线：私有测试中仅删除 `HttpClientConnectorTests.test_tcp_connector`、`test_unix_connector`，同步移除 expected 两个 FAILED 键。两项旧真实 client/server 路径受兼容改写影响而失效；本题代理端口、非示例端口、CONNECT 明确端口及其它31个旧有效键保留，总数为33。没有新增 skip，也没有改目标源码或把 FAILED 直接标成 PASSED。

此处不是宣称旧客户端／服务端兼容已修复。采用经已有行为证据支持的无网络 transport Future 复现作为目标相关开发路径，最终代码仍须以 agent 实测。原件 `runs/r2e_lifecycle_20260929/inv/aiohttp_240d/pcheck_*.json` 多为 root 私有对照，不能冒充 actor 验收。

新版本预期：gold／AL1／SC1=1；noop／DG1／WR1／WR2=0。七行各覆盖不同失真或实现路线，本轮不压缩为三行。正式复核必须确认仅移除上述两键，正常请求路径保留端口且 `req.host` 未被错误拼入端口。

### 61833518

评分材料不变，原 v5 gold／AP2／A1=1，noop／AP1／AP1m=0 的正式证据可复用。公开代码不再检查 `mock.call` 对象的恒真值；先检查实际 write 字节，再解析 chunked 线上数据，确认终止块在末尾且解压载荷完整。

此公开复现替换旧未定义 transport／compressed_data 的片段，不提供候选修法。目标相关开发路径选 protocol 层；其余真实 client/server 的 TypeError 不宣称已恢复，也不以无关 cookie 测试全绿作为本题条件。最终 agent 复现和相关公开 protocol 命令必须证明所声明的 deflate／chunked 行为可开发。HTTP/1.0、gzip 等原登记范围不在本次扩大。

## 共用入口的具体交接

现有 `statement_text_replace`、`hidden_test_text_replace`、`expected_file_replace` 能表达上述操作，当前未发现必须先改通用工具才能准备材料的缺口。

正式发布仍由共用维护者处理：分配正式修订号，将1c1c原 `r2e-mr-040/041` 和240d原 `r2e-mr-051/052` 替换成新版本条目，不能在同一题同一目标上直接叠加第二条。新全文进入不可变发布位置后，维护者更新材料修订单／pins／ingest，冻结后再重建受影响镜像并验收。4075／6183 仅改题面，不以此重跑不变评分矩阵，但题面编号联动后的材料身份及 consumer 接收仍需核对。

“负责处理分类二的明确问题”已回传确认：本包四题没有晚于库存的已落地新修订；共用 SWE/R2E 登记与发布由该线程统一维护。当前仍是 material_v11／pins_v12，没有新全局冻结版；Orange22隔离候选已占用064，本包不使用该号。

该线程可承担本包草案的非作者定向核查，但已有私有上下文，不能作为 fresh 公开读者。本轮已发送确切文件、四题改动范围和复核请求，结果待回；三份公开 bundle 均已单独生成，干净公开阅读仍未完成。CPU 准备就绪后，本包逐题完成验收；就绪一题提交一题给统一 GPU 执行者，探针后分析和修复仍归本线程。

四题均保留 aiohttp 同仓答案关联登记；训练／留出不得跨同仓拆分。这一轮没有授予训练或留出资格。
