# DVC5839：双模型首轮判断

2026-10-03 15:10 SGT。R10 材料 `dvc5839-precision-values-v1`；请求 `swe-dvc5839-precision-values-r10-v1-20261003` 只安排两模型各一次。本页汇总本次首轮，不覆盖旧报告的历史待核快照；Coder 独立语义报告尚待封存。

**两次正式评分均 1，23/23 参考通过；两份业务源码逐字相同，均正确补传 precision。当前没有题目、测试或公开说明的新增阻断。** 自测质量存在差别，完整 FrozenPatch 也不同，不能只用两个得分概括候选质量。一轮各一次尚不足以认定稳定通过或训练资格。

| 可观察事实 | Qwen3.6 首臂 | Coder 首臂 |
| --- | --- | --- |
| job | gpu1003-dvc5839-qwen36-a1 | gpu1003-dvc5839-coder-a1 |
| 正式结果 | raw 1，2F／21P 全通过 | raw 1，2F／21P 全通过 |
| 实际业务修复 | CmdMetricsShow 补传 precision | 同一业务源码、同一行修复 |
| 原 FP | 仅业务文件 | 业务文件＋3 个生成的 .dvc/tmp 文件 |
| 自身验证 | 原单元 22 项＋临时真实 CLI 默认／3／8 | 原单元 22 项＋2 普通功能项；mock 未断言精度，两个示例直接调用 helper |
| 定位与工具 | 14 工具／15 API 轮，无工具错误 | 20 工具／21 API 轮，一次空 precision 筛选 exit5，随后纠正测试选择 |
| 正常 solve | 25.07 秒 | 33.683 秒 |
| 输入／输出 token 累计 | 168905／2257 | 279091／3190 |
| 结束原因 | completed／end_turn／exit0 | completed／end_turn／exit0 |
| 当前候选判断 | 符合公开契约 | 符合公开契约，自测和最终陈述有缺口 |

公开契约是“小数点后 n 位、默认 5”，不追加科学记数法有效数字要求。两份源码都沿用原 helper，未改测试或固定数值。Qwen 实际跑了真实 CLI；Coder 的 helper 输出在修复前就可能相同，mock 只检查成功返回和 logger 被调用。两者都没有保存修复前 CLI 故障的同路径对照，也没有新增持久回归测试。Coder 最终“所有功能保持完整”超出自己的验证范围。grader 新增真实数值 F 的结果不冒充模型自测。

对原件的核对包含 Qwen 70 件／4,796,381 字节、Coder 152 件／7,657,883 字节，各自原 baseline tar 的 547 个条目，以及原 FP 字节。共用 baseline canonical SHA 相同，不以原 tar 封装 SHA 不同误判基线不同。Coder 的两个缓存数据库捕获主文件相同，Cache 表无行仅限捕获字节，不证明完整运行时缓存状态；不静默删掉三项生成文件再称候选最小。

## 可比范围和身份限制

实际 R10 material／cb175 镜像／评分 scripts／UID54322 prerequisite／23 参考分区／baseline／公开 prompt／声明预算相同，两臂均安装 0、测试 0、double cleanup 完成。entry、solve、frozen transport 四个关键入口 SHA 相同；完整 runtime 却是 Qwen code_v5 与 Coder code_v7，七个共享 consumer／manager 文件有增量，采样参数也不同。因此时间和 token 是本次轨迹描述，不能构成模型速度的因果排名或普遍能力高低判断。

Coder 有本次 before-job operational capture，绑定 engine／adapter、只读 mount、BF16／context196608 argv、HTTP 读回和下载清单；无逐权重重复 SHA 或 GPU 内存权重证明。Qwen 的 15 轮原始 transport／终态已核，旧记录没有 fresh per-job model capture。已有 before-start 配置和启动收据不能升级为这次运行的实时权重证明，也不能借用 Coder capture 补齐 Qwen。该限制保留在题级结论中；无需新模型生成来伪造历史捕获。

共同声明宽预算为 context196608、单响应65536、240 轮、3 小时、1024 请求；实际 max_tokens 均65536，两臂无截断／压缩／恢复或预算耗尽。Qwen 原 engine HTTP sock_read900s 仍存在，gateway first-byte1800s 不保证全链1800s。报告资源峰值和有限采样各保原来源，不把 null 填零、不声称连续监测。

双模型执行回执 [two_model_v1](../../../../../../../../../runs/ordinary_gpu_probe_20261002/receipts/swe-dvc5839-precision-values-r10-v1-20261003_two_model_v1.json) SHA 为 `82aeb40464ceb5c8e83a186f15f4b405c38bf769c4eacd6a2e6961670d30e467`。实际 `draft=false`、执行复核与 board return 已完成；其中 scope 文案仍写 draft／board untouched，视为旧描述，不改原件，也不据此覆盖实际状态。本页只接收执行事实与候选语义，不把 executor returned 当成题级全部收口。

## 当前处理

本轮保持题目和断言，不进行为求通过的重采样。题主已写 [Qwen 七维报告](qwen36_a1_semantic_audit_v1.md)、[Coder 七维报告](coder_a1_semantic_audit_v1.md)及两份逐件读回；Qwen 非作者语义核查已完成，Coder 核查仍待正式报告。该独立报告读回后核收首轮请求并更新题卡／总账。

依据 2026-10-03 14:01 SGT 更新的[覆盖与研究巡检规则](../../../../overnight_watch_20261003.md)，优先未测题和缺另一模型的首轮，暂缓未开始的普通追加采样；旧默认三次／模型要求已失效。后续只按明确问题安排少量校准，不为了得到通过或凑满次数重复。5839 本轮没有必须新增 GPU 运行的语义依赖，核收首轮后将 `still_needs_gpu` 置 false；这仅表示当前没有已授权必跑缺项，不宣称稳定性、训练资格或禁止未来定向校准。用途待题组分析，不用全量精修或旧退租门槛作收口条件，也不操作云资源。若出现评分与真实修法不一致，先看原候选，再区分评分边界与环境错误。
