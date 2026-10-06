# 240d：Qwen33/33，Coder最终候选收集失败

2026-10-03。任务 `aiohttp__240da100151933883d7dea0528d45877df025b92`，持续题主为 `R2E | aiohttp 题目修订`。CPU材料与首轮两模型结果、完整行为分析已核收：Qwen原分1、33键精确匹配；Coder正常结束但最终候选不可导入，原failed_to_grade/null保留，33参考均未执行。原请求已ack、活动交接为空；第二阶段同条件重复待安排，不授训练／留出资格。

Coder早期端口修法确有真实复现和公开13测通过；最后实际checkout撤回client/server/worker的预置兼容代码，冻结前两次自测已在client.py:140报SyntaxError，原Frozen和正式grade同错。原候选不清理，不把null改0，也不为通过重跑。Qwen也曾stash撤回，但随后pop恢复并重新实际验证，最终仅connector。两模型扩展HTTPS验证的旧API限制仍保留，手算端口不证明真实connect。见[完整行为](240d_trajectory_analysis_20261003.md)、[首轮收口](closure240d_20261003.json)及[一次非作者核收](review_acceptance1c1_240d_gpu_first_round_20261003.json)。本题无当前CPU依赖。

正式题面082用真实 `ClientRequest`、已完成 Future 与 `ProxyConnector.connect(req)` 修正复现；隐藏083／expected084仅删除两个失效 TCP／Unix 测试及其 FAILED 键，35→33键。其余旧有效键及 runner 保留，未新增skip或把FAILED标成PASSED。下列为已完成CPU材料验收依据。

第六版 `cat2-cpu-r2e080087-swe8-git-20261003-v1` 的匹配镜像已实际执行七方矩阵。完整33键无缺键或增键，按原日志重算：

| 候选 | PASSED／全部键 | reward | 结果含义 |
| --- | --- | --- | --- |
| gold | 33／33 | 1 | 用 netloc 保留端口 |
| AL1 | 33／33 | 1 | 用 host／port 和默认端口规则构造目标 |
| SC1 | 33／33 | 1 | gold 核心修法加兼容 decorator |
| noop | 31／33 | 0 | 丢失示例1234与其它8080端口 |
| DG1 | 32／33 | 0 | 硬编码示例，丢失8080 |
| WR1 | 32／33 | 0 | CONNECT 端口重复 |
| WR2 | 32／33 | 0 | CONNECT 端口重复 |

gold／AL1是两种独立端口修法；SC1是兼容变体，不能称为第三种独立修法。负对照均失败在目标字段比较，未由移除的旧测试故障驱动。完整原件见[七方结果](results240d_r6_matrix_20261003.json)，[CPU 核收裁决](cpu_result_acceptance_r6_20261003.json)是当前解释和独立报告入口；历史冻结结果不回写。候选／grader清理完成，本批标签回读无容器／网络残留。

[真实CC首请求](results240d_r082_delivery_20261003.json)已包含完整082题面，SHA256为 `d3ff12a9a27890831dcedc62d53e8c124647d6fe036c28712505ed247d7a272c`。历史 attempt 名含r084，实际版本由 consumer与SHA绑定，不为改名重跑。该CPU上游为stub、no-grade、Frozen为空、中性brief未送达，不能计模型成绩。

公开开发对照按原范围复用：[base／gold](results240d_public_development_20261003.json)分别观察到 `http://localhost/path`（断言失败）与 `http://localhost:1234/path`（通过），双方公开代理回归各13 passed、43 warnings。旧镜像上的13项不是新33键评分证据。[公开静态阅读](materials/240da100/public_reader_review_20261003.md)与[中性 brief](public/240d_development_brief.md)意见已核收；两模型首轮真实prompt均已核送达。

已结束固定请求 `aiohttp240d-r082084-probe-wide-v1-20261003`，两模型各一次、统一probe-wide-v1。固定[请求](requests/240d/probe_request.json) SHA256为 `ee21c0ca5e8cbe551d728572938efef0606ade8818153fb292f3dc4dd7642395`；[最初交接](probe_submission240d_20261003.json)保留，[原回执读回](aggregate_receipt_readback240d_20261003.json)、[Qwen结果](results240d_qwen36_a1_20261003.json)、[Coder候选失败](results240d_coder_a1_20261003.json)为当前依据。请求revision5已核收、题进度revision8，phase为result_analysis。

下一步按统一规则同条件重复，保留原始失败，不重判假想恢复后的候选。[自动分类观察](grading_classification_gap240d_20261003.json)只记录原字段缺少已知候选故障分类，不修改公共consumer或运行资格。本题已测端口行为通过不证明全仓客户端／服务端兼容或全部URL形式恢复；aiohttp仍整仓划分。
