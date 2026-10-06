# cancelled-main P2P：非作者材料 Falsifier / Simplifier 窄核

日期：2026-10-03。范围：本次已批准的单项 P2P 材料、精确父 R6 080／081及裁定；依审查标准 §10.4／10.5 做一次有界材料复核。未重开已结束的取消归因，未执行项目测试、远端命令、新反例或候选矩阵，未改材料与旧报告。

**未发现当前阻塞材料缺陷，可继续已授权的发布及五行验证。** 本轮确认的是材料结构和判据：父 R6 旧 58 键／状态全部保留，只新增一个公开 coroutine 取消资源收尾函数；所有评分断言均先于观察者补清理。59 键及新增 `[pyloop]` 键尚未实际 collect 或正式评分，不能据此宣称新材料通过、gold／C1 通过或发布完成。

## 固定版本与实际增量

裁定 [aiohttp1c1_cancelled_main_p2p_decision_20261003.json](../../../../../../../../../runs/category2_repair_20260929/overnight_watch_20261003/aiohttp1c1_cancelled_main_p2p_decision_20261003.json) SHA256 `5200cfc2b0edfba7ae50cc1c869eb9982b2ec19e37b5c9c359ba29cd36062ef0`。已明确授权实施／发布／五行验证；不需要新增批准或未改题面的 reader。

父 release 为 `cat2-cpu-r2e080087-swe8-git-20261003-v1`。直接读取固定 release 的 [080／081 原登记项](../../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_080_087_swe8_git_candidate_v1/repo/docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v18.json)及其实际两份材料：父 test SHA256 `5b38ccd1dd8083acbcb8db229a471517512434a5caccdddf0461f418c181910d`，父 expected `1bc0a6c74ee6fceb75b695d4d269c90f752deccf60b842db647a3602e1499370`。本次 manifest 引用与 bytes／SHA 均相符。

独立标准库比对结果：

- `test_1.py` 精确等于父文件在 `class TestShutdown` 前插入 `new_test.txt` 一次；反向移除此插入逐字回到父文件。父 68 个顶层 AST 节点完整保留，新文件 69 个节点，唯一新增函数为 `test_run_app_cancelled_coroutine_cleans_resources`（第 977–1046 行）。新函数与 `new_test.txt` AST 相同，Python 3.9 grammar 静态解析通过；这不是实际环境 collection。
- `hidden_test.patch` 与父→新文件独立生成的 unified diff 逐字相同，只有该函数的一个插入 hunk。
- expected 父 58 个键及其状态逐项相同，没有删除或改状态；唯一新增草案为 `test_run_app_cancelled_coroutine_cleans_resources[pyloop]: PASSED`，文件总 59 键。
- manifest 所指裁定、两份父材料、两份新材料、函数、patch 和发布操作的 bytes／SHA 全匹配；`local_material_checks_v1.json` 引用的 manifest bytes／SHA 也匹配。没有仅照抄作者 checks。

主要材料锚点：

| 文件 | SHA256 |
|---|---|
| [test_1.py](../materials_v1/test_1.py) | `3f57f362fd8d43cfd384386c1ecdc2f8c85b04aec88364a0859bbc2e2e6d3f52` |
| [expected_output.json](../materials_v1/expected_output.json) | `4872a730f3a8ffce94869108668c0a7dd20a68c368ee2141bb5ae47981060adf` |
| [new_test.txt](../materials_v1/new_test.txt) | `3fc428084788c59ef7bef3d8364ef32a25659cdc7a80b00418cdfcb25794eeba` |
| [hidden_test.patch](../materials_v1/hidden_test.patch) | `afdbadd724b860250d2ecf29e7a85c2852b2d3322c75c0c3589bc49e72731c3b` |
| [material_manifest_v1.json](../material_manifest_v1.json) | `dc8fbb51b852b0a70aee335a6f03cb5c6a7c5dc262e8a689e0c658b713ead330` |
| [publication_operations_v1.json](../publication_operations_v1.json) | `7f840a76da709711010442efd7e3145a26292ae4adcd4095bdb5c9a669108fbc` |
| [local_material_checks_v1.json](../local_material_checks_v1.json) | `b0c6cc726ebf1196ac8192fcdc44fcb15c219623a2f4d89a71ba9ae22e7fb4dc` |

## 判据是否误锁合理实现

新函数使用公开 `web.run_app(cancelled_app_factory(), loop=loop, handle_signals=False, print=None)`。worker 创建后让出一次调度，generator 保持强引用且已实际 `__anext__()`；factory 再通过公开 `asyncio.current_task().cancel()` 取消正在执行自己的任务。这保持已批准的公开触发方式，不读取库的私有 main task 字段或替换库函数。

第 1008–1011 行 `pytest.raises(asyncio.CancelledError)` 检查取消继续传播。第 1026–1031 行六项断言分别检查 worker 已 done、worker finally 已执行、generator 已闭、generator finally 已执行、loop 已闭、无 pending task。它们全部位于外层 try 的正文，早于第 1034 行起的 observer finally；不借 pytest fixture teardown 或 observer 清理满足判据。

第 1016–1025 行打印 main done／cancelled 和 worker cancelled 等状态；这些值没有进入断言、分支判定或 expected key。触发用的 main 对象可以是库直接 await factory 的任务，也可以是合理包装后执行 factory 的任务；评分不要求它等于库某个具体内部对象。worker 的 cancelled 状态也只诊断，评分保留其完成与 finally 的实质行为。新函数没有候选 label、源码 SHA、UID、指定 helper、异常 message／traceback 或报告次数的 oracle。

父 R6 的原 `test_run_app_cleanup_error_is_observable_after_interrupt` 逐字保留：仍先确认进入 cleanup，最后接受 `message in raised or reported`。因此原先合理的向 caller 抛出和向 loop handler 报告两条路线未被改写；新增 P2P 的取消传播要求不会替代旧 cleanup 新错误可观察性判据。静态不能据此预告全部合理解法运行结果；裁定已要求 gold／C1／Qwen 的实际正对照，结果由本批 Production Tracer 与 owner 核收。

## 失败后的观察者清理

第 1034–1046 行 observer finally 不含断言成功后的重新判分、return 或异常抑制。若资源断言失败，随后补清理不会撤销已发生的失败；清理若再抛错，至多改变失败栈，不能把失败变通过。它只在 loop 尚开时取消剩余任务、`gather(return_exceptions=True)`、关闭 async generators，内层 finally 关闭 loop，随后清除当前 event loop。

所以失败候选的补清理事件不会进入之前已经完成的判定。若某实现提前关 loop 但留下任务，finally 不再重开已关 loop；测试仍因 worker／pending 等实质断言失败。本轮没有执行这种新反例，不把它升级为额外材料需求。

## 发布操作与停止条件

两条 operation 明确 supersede 原 `r2e-mr-080`／`081`，保留原 consumer 的 `sha256_before`，并把当前父 SHA 单列为 `parent_current_sha256`。080 的前两个 edits 与固定父登记项完全相同，第三个才是本次新增函数；从原 consumer 的 SHA `26317e3d…` 顺序应用三条后，逐字得到本次新 test。081 的 `expected_change` 同样累计保留原两项 added，再新增本次一项，changed／removed 均空；相对当前父文件仍仅新增一个键。081 的 `sha256_before` 与精确父登记项一致；本次 expected 的实质验证是旧 58 键／状态逐项保留及新增一键，未声称重新装配原 consumer JSON 字节。

这避免把旧 080／081 与新 revision 叠加应用，也说明 operation 中“3 个 added”不是本批增加三项。正式 revision 当前仍 `assign_by_publication`，`key_actual_collection_verified=false`，本地检查 `actual_collect_or_formal_grade_executed=false`；这些未完成状态按原件保留。

停止条件已满足：单函数增量、旧 58 键、断言／补清理顺序、诊断与 oracle 分离、旧两种错误报告路线和替换发布操作均完成静态核对。本轮没有阻塞材料 finding，不要求另一个 reader、归因复核或新矩阵。按现有裁定继续发布与 baseline／gold／C1／完整原 Coder／完整原 Qwen 五行的实际核收；正式键名、完整消费和实际结果尚未知，由已分工的窄核处理。旧 raw 1／58、旧 Frozen 与报告继续保留，本报告不授予训练资格。
