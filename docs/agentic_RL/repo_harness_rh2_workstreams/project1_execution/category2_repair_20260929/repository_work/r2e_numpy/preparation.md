# R2E NumPy 工作包：当前入口

2026-10-03。本线程负责唯一题目 `numpy__d805e9b66228e68a0eb14d901cd350159c49af18` 的修订、CPU验收、基座探针分析及必要修复。

**078／079修订材料的两模型首轮质量诊断已收口。** CPU十行正式对照与公开CC交付均通过独立核查；两份真实模型原候选和完整轨迹已回收，执行及语义分别核实。两模型正常完成、有效评分，均raw0、228／229键通过。没有新题级阻断，本轮没有修改材料或追加运行。CPU通过和模型诊断完整都不代表训练／留出资格。

| 本次验收 | 实际结果及含义 |
| --- | --- |
| 修订隐藏测试078、公开题面079 | 补全printing options保留条件，校正题面Actual；CPU K-A5c=1，其余九项=0，每行完整229键。 |
| Coder首轮 | 仍把数字显示成字符串，省略槽位被mask覆盖；固定100项裁剪未修。正式公开大例失败。 |
| Qwen3.6首轮 | 默认大例的首尾、mask、省略提示正确，但省略号后少公开约定逗号；格式兼容失败。 |
| 完成／原成功分母 | 各模型1／1正常完成、1／1有效评分、0／1原成功；总共2次，无截断或基础设施失败。 |
| 效率及验证 | solve墙钟Coder233.310秒、Qwen102.466秒；报告分列token、工具、环境与grading，保留错误诊断和错误完成声明。 |

完整结论、七项轨迹分析、T／G／E事件锚点、原件和限制见[首轮结果与轨迹报告](gpu_pair_analysis_20261003.md)及[可机读索引](gpu_pair_analysis_20261003.json)。[非作者语义核查](reviews/gpu_pair_semantic_review_20261003.md)确认两次原零分有公开失败依据；没有为了得到正分放宽判据。

## 当前下一步与资源

本包只有一题，原请求 `r2e-numpy-d805-078079-cpu-v1-20261003` 已returned并由题主ack，active request为空。通知此前未送达，执行侧已恢复交付；已有回执按原身份接续，不重做CPU矩阵或补交相同探针。当前无必须运行的CPU修复，也无缺失的两模型首轮。

按[现行覆盖优先规则](../../overnight_watch_20261003.md)，先扩大共同题组；普通追加采样暂缓。NumPy**值得小批校准但不是必做**：覆盖后若仍需要分辨“修法机制反复失败”和“公开Expected字面漏验”是否偶发，可按原材料及每个模型自己的设置各额外一次；由巡检结合共同题组判断价值。本线程本轮没有提交追加请求。旧默认累计三次、27／52自动门槛和自动退租职责已失效；后续资源操作等待用户新指示，本题不自行停机或销毁。

本报告仅使用完整首轮样本解释失败。两模型各一次、采样参数不同，不支持稳定能力排名或训练收益结论。两臂同一正式测试在458行首败，后续threshold／edgeitems断言未执行；不能由228／229推断这些内部断言通过。二维、性能及完整dtype／subclass兼容未验。X1同仓答案暴露／留出划分、E3共享控制保护延后及code3 formal lineage字段缺口仍保留，不能据质量诊断授予训练或holdout资格。

## CPU修订与历史证据

本版十行：K-A5c **1**；K-A5b、hybrid、gold、noop、K-DE、K-DC、K-DF、DG-e、DG-g均 **0**。gold是已知边界不足的来源候选，保留为负对照，不充当健全性正对照。外层作者matrix job rc1来自错误假设DG-g只改core.py；十个正式driver均rc0，原arrayprint.py投影经作者离线和非作者核对确认，原rc1保留，不重评分。

- [CPU原件索引](cpu_acceptance_v1.json)、[验收矩阵](acceptance_matrix.json)、[当前结果清单](result_manifest.json)、[CPU独立核查](reviews/cpu_acceptance_review.md)。CPU原件索引字节未改，历史pending文字由当前清单解释。
- [发布回执](publication_receipt.json)、[修订依据与范围](revision_notes.md)、[正式公开题面](public/user_prompt.txt)、[中性开发说明](public/solver_environment_brief.md)。实际GPU首请求交付已在两份执行核查中确认。
- [冻结原探针请求](probe_request.json)、[非作者材料核查](reviews/static_revision_review.md)、[公开题面读取](reviews/public_read.md)、[开发说明公开读取](reviews/solver_environment_brief_review.md)。
- [发布前CPU证据](cpu_prepublication_evidence.json)和[发布前独立核查](reviews/prepublication_cpu_review.md)仅适用其父版／草案身份；[暂停检查点](pause_checkpoint_20261003.md)及[恢复检查点](resume_checkpoint_20261003.md)保留为当时事实。

CPU固定release5 `cat2-cpu-r2e078079-swe7-git-20261003-v1`、manifest `80ee228d…`，837成员和48R2E／216SWE可信读回通过；CPU镜像 `e5c5233c…`、配方 `r2e_derive_v1+material_v2+sysconfig_v1`。image实际应用隐藏078，host grading材料含078＋079。GPU实际镜像 `0121ac12…`及code3／model／budget另在首轮报告与可机读索引记录；不混用CPU、父056或历史v8身份。历史对照、开发检查、暂停与原请求均按原路径保留。
