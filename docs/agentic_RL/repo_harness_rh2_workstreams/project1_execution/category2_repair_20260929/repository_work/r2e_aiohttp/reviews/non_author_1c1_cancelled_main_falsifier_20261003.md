# 1c1 cancelled-main 公开输入：非作者 Falsifier / Simplifier 窄核

日期：2026-10-03。角色：同一次取消边界复核的 Falsifier / Simplifier，依 `review-standards.md` §10.4／10.5；已看过上一轮候选与私有评分信息，不是新的公开盲审。本轮只读本批固定输入、完整原 Frozen、三侧实际 capture／CC 轨迹及装配记录；未执行新模型采样、项目测试或评分，未修改原件和共享材料。

**裁决：原 Coder 1c1 候选确实新增了公开可达的取消清理回归，现有 58 键漏检。** 同一个公开 `run_app(coroutine)` 输入下，基线和完整原 Qwen 已清理 worker、async generator 和 loop；完整原 Coder 退出到调用方时留下未取消任务、开放 generator 和开放 loop。此前“缺少 cancelled guard”的静态风险已经成为本次实际生产入口上的语义失败。原 `raw=1`／`58/58` 仍是历史评分事实，不回写为 0，不为这次复现补造新 reward。

## 固定输入与完整候选可比性

读取 [input_manifest.json](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/inputs_v1/input_manifest.json)（SHA256 `921aebdb79dadef42c487e064b749de94a02242012c3cf05410e6f77f75a6517`）和 [archive_manifest.json](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/actual_artifacts_v1/archive_manifest.json)（`5e3c2344e4ae3b42684b56bd958620ece17abc7b6e4f197d4bb99884eab29ae9`）。用标准库重新核对 manifest 声明的 11 个输入及 96 个实际产物：bytes／SHA256 全部一致。archive 记录 whole job 已结束、launcher returncode 0；三侧 harness 均 returned／exit 0，容器和网络收尾均无残留。

独立读 baseline tar 的全部 307 个常规文件字节和模式，逐项与 baseline manifest 一致；重新计算 canonical baseline digest 为 `40b0956474180605d1f46cc2b59f3e4ae3dcef0fffd18f9f2ff24b539d007608`。三侧 `actual_initial_manifest.json` 均与固定 baseline JSON 对象完整相等，不用 Git HEAD 代替内容。对全部原 Frozen 的 base64 字节再哈希，并构造 baseline＋所有条目的预期路径／类型／模式／内容摘要映射；实际 candidate manifest 与完整 census 均精确匹配：

| 三侧 | 原 Frozen 条目 | 实际 scoreable 文件数 | `aiohttp/web.py` 实际内容 SHA256 |
|---|---:|---:|---|
| 基线 | 0 | 307 | `da7193c490d70bcaa96ee788ff434fdb60ea6a344ca2e32a08118b20405ec746` |
| 完整原 Coder | 7（1 修改、6 新增） | 313 | `279d0a2d2b733dcb0bce0530043de938ec3fc8148f98bcc2e9a1f76ce6ae8887` |
| 完整原 Qwen | 2（1 修改、1 新增） | 308 | `f7c5c1d1b2fd638d4527ca8e2c17a105512848d6da24d2b6220f5124dfd92933` |

Coder canonical Frozen digest `dc7a8f17e1b22988f2091bc882fb75fb28227a61bb97b26d713b03d69e70798d`，Qwen `77d02d948b6a6e003aba9a497d905189c15b174ddb02f5f10b3fa62362b036be`。候选自带 `.coverage`、文档及脚本全部保留，没有只抽出 web.py、删除不利条目或重写候选。原件入口：[baseline tar](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/inputs_v1/baseline.tar)、[Coder Frozen](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/inputs_v1/coder_frozen_patch.json)、[Qwen Frozen](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/inputs_v1/qwen_frozen_patch.json)。这里的完整候选重放遵循原 scoreable 语义，`.git/`／`.venv/` 等 excluded runtime 文件未按候选条目重放；并不声称重新执行了原模型求解。

## 探针没有自造回归

固定 [public_cancelled_main_probe.py](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/inputs_v1/public_cancelled_main_probe.py) SHA256 为 `50c09f6ee8e303a1521dbfc958be4cbcc67055e82f493cd70cde3d8ca23b598e`。第 63 行只调公开 `web.run_app(cancelled_app_factory(), loop=loop, handle_signals=False, print=None)`；没有替换库函数，也没有通过库私有字段取得或替换 main task。factory 中的 `asyncio.current_task()` 取得真实正在执行它的任务；冻结生产源码 `_run_app` 第 321–322 行确实 `await app`，因此取消发生在正式入口内部。

第 52–58 行先创建 worker 并让它进入 `try/finally`，再开启 async generator、实际取到首个 yield，保持强引用后才取消当前任务。实测三侧都出现 `worker_started → generator_started → main_self_cancel`，均 main done＋cancelled；不是未启动任务缺少 finally，也不是 generator 尚未开启或 GC 已代替库关闭。没有网络、信号调度或私有实现 mock 参与触发。

第 70–81 行在 observer 补清理前保存布尔状态、任务数及复制后的事件列表；第 84–97 行只负责回收本观察进程遗留资源，另列 `observer_cleanup`。因此 Coder 随后的 worker／generator 收尾不会写回前一快照。捕获 `BaseException` 让脚本能打印取消后的状态，所以 exit 0／`matches_expect=true` 只证明观察执行成功，不证明候选语义通过。

三侧实际 CC `trajectory.jsonl` 都是 28 行，只有第 6 行 preflight 与第 15 行公开输入两个 Bash tool call，第 19 行为探针实际 tool result。独立解开命令 shell quoting 后，三侧 here-doc 内探针字节均与固定文件逐字相同，只有 label／预期 web SHA 参数不同；capture JSON 均与 tool result 的 JSON 完整相等。实际采用 `cd /testbed; python -B -` 的 stdin 输入，未落入 `/tmp` 文件执行时的 import-path 歧义。

## 实测反证与源码因果链

以下均取 `after_run_app_before_observer_cleanup`，不采用 observer 之后的共同关闭状态：

| 观察 | 基线 | 完整原 Coder | 完整原 Qwen |
|---|---|---|---|
| caller exception | `CancelledError`，空 message | 同左 | 同左 |
| main done／cancelled | true／true | true／true | true／true |
| worker done／cancelled | true／true | **false／false** | true／true |
| generator closed／loop closed | true／true | **false／false** | true／true |
| pending task count | 0 | **1** | 0 |
| worker／generator finally 事件 | 两者均有 | **两者均无** | 两者均有 |
| loop handler | 空 | 空 | 空 |
| observer cleanup needed／error | false／null | **true／null** | false／null |

原始 capture：[基线](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/actual_artifacts_v1/outputs/baseline/captures/cancelled_main.out)、[完整原 Coder](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/actual_artifacts_v1/outputs/coder_full_frozen/captures/cancelled_main.out)、[完整原 Qwen](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/actual_artifacts_v1/outputs/qwen_full_frozen/captures/cancelled_main.out)。其 SHA256 依次为 `df9346b4f3dbe8bc26e8509559a5ddbdc83115f978c628c51b754fbc613aedb0`、`9614c5a40db742e757290b67db9649b5bb6558d95088b83e2b83d49b6daafa70`、`fbb41af07a8c3ad3e89a3ebc95f9cd7caaf9f506c489369aa7694a0aa555d016`。

**[P2] Coder 的新增判断使 cancelled main 中断整个 finally。** 当前行为、违反的不变量、证据及处置如下：

- 冻结 Coder `aiohttp/web.py:525` 新增 `if main_task.done() and main_task.exception() is not None:`，没有先排除 `main_task.cancelled()`。本输入确实 main done＋cancelled；Python 3.9 的 Task 在 cancelled 时读取 `exception()` 会抛 `CancelledError`。它发生在 `finally` 内，直接跳过第 530 行其余任务取消、第 531 行 `shutdown_asyncgens()` 和第 532 行 `loop.close()`。调用方仍看到同类取消异常，并不能识别这条内部二次抛出。
- 基线 `web.py:522` 先调用 `_cancel_tasks({main_task}, loop)`；helper 第 450–451 行先跳过 cancelled task，再读 exception。Qwen 第 534 行仍走该 helper，helper 第 458 行同样先检查 cancelled。两侧实际完成 worker／generator／loop 清理，是同输入的有效正对照；Qwen 的 `already_done` 分支未吞掉本次 pending worker 收尾。
- 应保留的不变量是：公开 coroutine app 被取消时，取消继续传播给 caller，同时 run_app 执行其既有资源收尾。当前 Coder 新改动造成这项原有行为退化。源码唯一生产修改与真实资源快照互相支持；“基线也失败”“探针不是真入口”“只删选候选”“观察者制造缺陷”均被本次证据反驳。
- 影响是这个公开可达路径留下 pending task、async generator 和 loop；真实应用发生频率 unknown，本输入发生在 coroutine startup 被取消阶段，未证明任意运行阶段或信号取消均有同样故障。不升级为全局 P0，也不把一条输入解释成 Qwen 的全部 cleanup 路径已经完备。
- 本项建议处置 `accepted`：这是本次修订实测新增的公开入口回归，已有单输入因果证据且守卫／P2P 成本很小，继续延后会保留题级漏判。建议本题 owner 保留此实测 P2P（pass-to-pass，基线已满足、修订须保留的行为）边界；不能继续以旧 58/58 独立宣称 Coder 修法完整正确。候选修法可以小到取消状态守卫或避免对 cancelled main 读取 exception，继续走原有收尾；无需新增状态机或扩大异常协议。该修法本轮未实施、未验证。
- 最小复现就是固定公开输入在三侧原完整候选上的现有实际命令；验收应在 observer 补清理前看到 caller 取消保留、worker finally、generator finally、loop 关闭且无 pending task。无需为因果归因再采样、再评分或再做另一轮审查。

## 环境／Git 替代解释与局限

三侧 image inspect 均绑定 `sha256:00ad3e96b2ec0cf385aba6e9b69b6335c5e1623c5c3235cd57c34d6300b87683`；实际 capture 均 UID 54321、Python 3.9.21、`/testbed/.venv/bin/python`，导入 `/testbed/aiohttp/web.py` 且内容 SHA 与上述原件完全一致。activation record 三侧 `ok=true`／violations 空；真实 CC Bash preflight 三项 interpreter／hidden tests／Git history 均 ok、rc 0。全树内容核对补足了“Git HEAD 正确但代码错误”的替代解释。实际工具调用没有 checkout、reset、改库或运行候选自带测试脚本。

**不能把一般 checks 全部写成 true。** 三侧 attempt 的 `interpreter_in_tool_result=false`、`bashenv_denied_for_agent=false` 原样保留。本次一般 DevRunner 旧 `RH2_SYS_EXECUTABLE` marker 未提供；可比性依据是本次真实 identity＋activation＋preflight，不宣称旧 marker 检查通过。`bashenv_denied_for_agent` 的否定值也不改写；prelaunch 可证 activation 写入被拒绝，但不据此替代该通用检查或出新的通用执行资格。相同否定字段不能解释仅 Coder 出现的、与其冻结源码一致的资源泄漏。本报告不重审共同 runtime／Git 机制，不核发新的 qualification。

装配脚本 [run_fixed_public_probe.py](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/inputs_v1/run_fixed_public_probe.py) SHA256 `91b2712747ac46b7f3ba2167c0e0cc6bb39eff74a8405a29397b29f43da98d48`。其 evaluate 只验证公开输入已执行和 JSON 已捕获，未按资源状态判 pass；三侧 `reward_computed=false`。完整实际入口：[基线 trajectory](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/actual_artifacts_v1/outputs/baseline/harness/trajectory.jsonl)、[Coder trajectory](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/actual_artifacts_v1/outputs/coder_full_frozen/harness/trajectory.jsonl)、[Qwen trajectory](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/actual_artifacts_v1/outputs/qwen_full_frozen/harness/trajectory.jsonl)及各 case 根目录的 attempt／prelaunch／activation 记录。没有用 owner readback 的 checks 代替上述独立核对。

## 最窄 P2P 方案与停止条件

建议只把这一个公开 coroutine 自身取消输入转为独立 P2P 测试键，保留旧 58 键及 R6 cleanup 新错误可观察性目标。测试先确保 worker 已进入等待、generator 已 yield 并保持引用，再让 coroutine app 取消；断言取消继续传播，worker／generator 的 finally 已执行，loop 已关闭、pending 为 0。main done＋cancelled 可作诊断；不要求候选采用 gold 的 helper、具体内部任务包装或 exception-report 路线。测试自身的最终补清理置于独立 finally，所有验收快照在其之前取得。

这条方案已有基线／原 Qwen 正对照和原 Coder 负对照的实际证据，覆盖的是原有取消资源收尾，不增加 URL、协议或异常包装范围。今后若采纳评分材料变更，应另建版本／expected PASSED 键，并明确题级遗漏；本报告仅提供方案，未修改或发布 080／081、expected、registry、旧首轮回执或原分数。未运行 gold／C1 在这条新增输入上的结果，也未证明未来材料发布／全部对照已验收；不能虚报。

**真正受阻的是本题“Coder 已完整正确”及“当前 58 键已经足以保留取消 cleanup 行为”的结论。** 历史首轮分数与执行回执有效性保留；此次新语义失败单列，不能把新实测遗漏压回纯理论 residual risk。既有材料的后续定案应处置这条具体 P2P 边界；它不构成对其他题、共同 CPU／GPU runtime 或新训练资格的额外结论。

停止条件已满足：同输入、完整原候选、固定像与实际身份、公开真入口、补清理前差异及生产源码因果链均齐全。剩余未知是现实触发频率、异常对象／traceback identity（capture 未记录）和未执行路径的兼容性；这些不改变当前 resource regression，按边界记录。本轮到此停止，不追加新反例、另一复核轮或全矩阵。
