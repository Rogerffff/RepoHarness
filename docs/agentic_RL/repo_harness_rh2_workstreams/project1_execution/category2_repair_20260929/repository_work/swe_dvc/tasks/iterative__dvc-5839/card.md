# DVC5839 当前题卡

2026-10-03 15:21 SGT。**R10 CPU验收与双模型首轮诊断完成：两模型各一次 raw1、23/23参考通过；题主七维分析、执行复核和非作者语义报告均已核收，首轮请求已ack。** 两份业务修法逐字相同，符合公开小数位数契约，当前没有需改材料或必跑GPU的缺项。普通追加采样按最新覆盖优先规则暂缓；一次各模型不支持稳定性或训练／留出资格，最终用途尚未决定。

## 目标、修订与CPU验证

`metrics show --precision n` 应按小数点后n位生效，默认5；公开CLI及helper源码是依据，不追加科学记数法有效数字规格。原题面及中性[开发说明](public_development.md)字节未改。材料为 `dvc5839-precision-values-v1`，CPU release为 `cat2-cpu-r2e089092-swe14-preflight-20261003-v1`。

有效测试保留原1个F2P／21个P2P，新增1个F2P：读取真实YAML，经命令解析和 CmdMetricsShow.run 核默认5／3／8及Markdown数值，不mock formatter，不固定传参实现或表格空格。当前总计2F／21P、23执行／23参考。

| R10正式候选 | 评分 | 完整测试行为 |
| --- | --- | --- |
| noop | 0 | 两个F失败，21P通过 |
| gold | 1 | 23项全通过 |
| 固定8位错解 | 0 | 仅新增F失败，原22项通过 |

[正式矩阵](formal_matrix_r10_v1.json)、[运行原件导航](formal_cpu_r10_v1.json)、[CPU验收](cpu_acceptance_r10_v1.json)：三项实际UID54322四wheel预检verified／0、安装0、测试完整；同一成功prepare和新summary，精确job清理完成。材料、正式运行及actor的非作者核查均已完成。

[公开actor](public_actor_r10_v1.json)用真实CC配合固定控制桩执行四条公开命令，原基线测试2项通过；原CRLF题面与公开说明逐字交付，SHA guard及清理通过。这是公开工具交付检查，不是模型求解。

## 两模型首轮与语义判断

| 事实 | Qwen3.6 | Coder |
| --- | --- | --- |
| 当前正式结果 | raw1，23/23通过 | raw1，23/23通过 |
| 业务候选 | 补传precision一行 | 与Qwen业务源码逐字相同 |
| 完整FrozenPatch | 仅业务文件 | 业务文件及三个生成的.dvc/tmp文件 |
| 自主验证 | 原单元22项及修后真实CLI默认／3／8 | 原单元22项、两个普通功能项；mock和helper示例未直接验证CLI精度 |
| 结束 | completed／end_turn／exit0 | completed／end_turn／exit0 |

[双模型判断](two_model_first_round_semantic_audit_v1.md)、[首轮验收记录](two_model_first_round_acceptance_v1.json)、[最新结果](results.json)是当前入口。[Qwen七维报告](qwen36_a1_semantic_audit_v1.md)和[Coder七维报告](coder_a1_semantic_audit_v1.md)保留各自审计快照；[Qwen非作者报告](../../reviews/non_author_dvc5839_qwen36_a1_semantic_review_20261003.md)与[Coder非作者报告](../../reviews/non_author_dvc5839_coder_a1_semantic_review_20261003.md)已完整读回。Qwen70件／4,796,381B、Coder152件／7,657,883B及各547基线条目均已逐件核SHA／内容／类型与执行位，原FP未删改。

两模型都没有修复前真实CLI失败的同路径对照，也没有新增持久回归测试。Coder mock只核rc0与logger.called，直接helper脚本打印的行为本已正常；最终“所有功能保持完整”超出自测证据。正确业务修法与这些非阻断验证习惯缺口分别保存，不把grader覆盖冒充模型自测。

[双模型执行回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/receipts/swe-dvc5839-precision-values-r10-v1-20261003_two_model_v1.json)与[总账核收记录](../../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/5839_board_first_round_acceptance_update_v1.json)固定本次回告／ack及progress13。首轮请求活动指针已释放，没有给GPU发送普通ACK消息。原验收／作者报告中的当时pending是历史快照，不覆盖此处当前核收状态。

## 必要限制与历史

两臂实际材料、cb175镜像、scripts／UID54322 prerequisite、23参考、baseline、公开prompt和宽预算相同；关键entry／solve／冻结运输SHA相同，但完整runtime是code5／code7、七个共享文件有差异，采样参数也不同。耗时／token只描述本次轨迹，不作模型速度因果排名。两臂均无截断或infra终止。

Coder有fresh before-job operational capture，绑定实际服务、只读model mount、BF16／context196608 argv、HTTP及下载清单；无逐权重重复SHA／GPU内存权重证明。Qwen旧首臂没有fresh per-job capture，不能借Coder证据补成实时权重验收。Qwen原engine sock_read900s仍生效，gateway1800s不是全链保证。资源有限采样、报告峰值和null各保原范围；8GiB writable-layer quota配置未证明强制生效。

[R7正式失败](formal_cpu_r7_v1.json)是UID切换与受限cap冲突、reward null，未安装／测试；R10修复由现有UID54322 exec预检，不加cap。旧R7／R8／R9仍阻断，prepared与FP未热改绑。[旧私有诊断](cpu_diagnostics_v1.json)证明原测试漏掉固定8位错解；旧原版正式reward仍未知，不用新材料倒推。原断言可能限制其他合理实现，后续评分与候选不一致时仍须语义审查。

按最新[覆盖巡检规则](../../../../overnight_watch_20261003.md)，当前没有必须追加的GPU运行；稳定性未知、用途待题组分析。只在明确校准问题出现时再安排样本，不机械三次、不恢复旧退租条件、不操作云资源。

模型文件计数见[更正](coder_a1_model_file_count_correction_v1.md)：旧报告误称25权重，实际25个模型文件含16权重分片，declared28与列表25不同；原审计／验收SHA及评分／核收不变。
