# Conan13230：两模型首轮当前结论

2026-10-03。固定请求 `swe-conan13230-r11-briefv2-20261003-v1`，R11、brief v2、`probe-wide-v1`，每模型一次。原CPU矩阵及历史首臂原件保持；本页汇合当前配对状态，旧Qwen分析中“另一臂／执行审待回”是当时快照。

**两模型均raw1，分别3F／34P共37参考全部通过；两份生产补丁都修复了host目标系统判断，当前没有具体材料修订／重跑依据。执行与语义分别留证，本轮配置诊断通过不代表真实交叉编译、稳定成功率或训练资格。**

| 首臂 | 生产修法 | 实际原候选与验证边界 |
| --- | --- | --- |
| [Qwen3.6](probe_qwen36_a1_analysis_20261003.md) | 改为host属于四Apple目标时生成相关参数 | 公开测试新增保留在FP，可信投影只含生产文件；有真实配置生成前后原件与有限公开回归，非SDK／编译／链接验收。首臂语义审复用，不重审旧CPU |
| [Coder](probe_coder_a1_analysis_20261003.md) | 调用既有`is_apple_os()`，使用host设置 | 两开发脚本与生产三项全投影；类构造前后复现成立。native新例无行为断言，functional的autoreconf阶段127失败、Apple8例skip；这些不包装为完整回归 |

两者保留外层cross判断、compiler／triplet、SDK处理和旧公开行为，没有测试识别或绕过。Coder非阻断P2记录native例无有效断言及最终验证披露不足，实际失败和skip原文保持；不将这些模型质量问题自动改成材料缺陷。Qwen原测试改动的警示保持，不因评分report的`test_files_modified=false`声称整个原FP未改测试。

## 执行核收与身份

[GPU总回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/receipts/swe-conan13230-r11-briefv2-20261003-v1_two_model_v1.json) SHA `a148a1864a603426c72a25609ad2432969871ce243709cdcde35ca541ece5f3e`，题主核其16项文件引用SHA／大小和实际两臂冻结输入。Qwen的78原件／10,030,451字节及既有题主读回按范围复用；Coder另根核140原件／12,397,859字节、完整diff至FP及逐37参考。两臂安装／测试0，完成模型终止、actor／grader收尾及gateway drain，无预算截断。

[Qwen执行独立报告](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/conan13230_qwen36_a1_execution_non_author_review_v1.json)已回，SHA `88e6d421a1b4d9d98781ff284f05d200aaa7a13b8ebec9b0f8200383feb8ed68`，所有checks通过、failed_checks空；其旧“配对未完成”只覆盖当时Qwen首臂。[Coder执行独立报告](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/conan13230_coder_a1_execution_review_v1.json) SHA `e757a65bf924ce2342959c28732cc3f2dbf32557ed4d55974d00108122286660`，无执行阻断。报告不替代题义／候选语义；环境资格absent与有限资源采样限制保留。

两臂使用同一请求SHA、材料、实际470b镜像、完整baseline、原issue＋brief、37参考及预算。**实际runtime分别code5／code7，完整代码树不同**；同字节的四关键运输文件与七处shared consumer差异由执行报告列明，不宣称全树同版。求解39.548／51.047秒只描述两次尝试，不用于模型性能排名；n=1／模型不建立稳定成功率。

总回执原字节中的`not_sent=true`、`request_returned=false`为旧状态字段，comparison说明中的“5参考”也与逐臂37参考不符。当前CLI已直接核实`returned`、`safe_closed=true`及已发送return notice，数量按冻结分组和完整原日志为37；原回执不改写，差异另留私有`pair_receipt_readback.json`。这些元数据不用于推翻已核的完整执行事实。

## 题级处置

[Qwen语义独立窄核](../../reviews/non_author_13230_qwen36_a1_semantic_review_20261003.md)复用原范围；题主已全文读回并采纳[Coder语义独立窄核](../../reviews/non_author_13230_coder_a1_semantic_review_20261003.md)，SHA `0648b1c34c0c4372c7520af48aea7de904f3df491487db36af2568b946645aa2`。它另核完整三项候选、实际投影、公开边界和原轨迹；两项P2均按`no_fix_accept_residual_risk`保留准确验证范围，无材料阻断。本轮报告处置及请求ACK／活动指针状态由当前[结果清单](result_manifest.json)和总账保存；候选／材料finding分开，不用已回执自动清缺陷。

本题首轮两模型覆盖已齐，无CPU作业或已授权GPU续跑待办。继续同仓其它题首轮接续，普通追加采样按覆盖优先暂缓；未来具体修订或新授权再安排实验。整批资源操作由对应负责线程按现行授权决定，本页不授退租／销毁权限。本题配置诊断本轮收口，正式训练／留出资格仍未建立。
