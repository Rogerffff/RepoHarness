# EA69 R17 两模型首轮结论

2026-10-04。当前公开题面下，Coder和Qwen各首轮原分均为raw1、49/49；请求已returned/ACK，安装跳过/RCnull、test0及清理通过。**两个候选均存在已实测的公开目标失败；旧49键的通过不能解释为完整语义成功。** 旧R6 Qwen不计入本轮，原分、FrozenPatch与旧报告不改。

| 模型 | 实际行为与缺口 | 求解记录 |
| --- | --- | --- |
| Coder | 普通内容/报告通过；未转义extra_css字面名称，`!custom.css`、`#custom.css`、`custom[ab].css`各两轮漏Git忽略 | 30回合、29工具、3工具失败；800415/6971 token，solve72.704s；只生产html.py |
| Qwen3.6 | 追加`/*`正常通过；已有文本含该子串就跳过，注释、子目录规则、反向规则和尾随例外共4情形实际漏忽略 | 18回合、17工具、0工具失败；429634/5597 token，solve54.147s；另留53248B `.coverage` |

相同基线360项、实际actor/grader镜像e23fbbed…、公开prompt19aa60c7…和统一probe-wide-v1；模型身份/采样按各自固定配置。一次样本、不同候选完整性缺陷及计时边界不支持稳定性、成功率或模型性能排序。

最小私有评分草稿保留旧49键/方法，增加CSS字面名称和已有规则两键至51。精确原GPU镜像、完整原FP下，八次新增方法对照为：baseline两败，safe两过，Coder仅CSS败，Qwen仅已有规则败。失败方法会首错停止，完整四Qwen反例另由23fixture/46报告边界作业证实；新完整51正式成绩尚未产生。不加字节/幂等要求，不改公开题面或修补候选。

本次非作者语义、CPU及草稿差异核查通过。下一步普通发布请求冻结新身份、部署CPU-A，随后只原两FP补评分并验正负控制；不新增模型采样。原R17评分盲区阻断保留到实际新材料消费复验，不授训练资格。

证据：[Coder原分析](model_analysis_coder_r17_a1_20261003.md)、[Coder边界收口](cpu/candidate_boundary_r17_coder_cpu_closeout_20261003_v2.json)、[Qwen原分析](model_analysis_qwen36_r17_a1_20261004.md)、[本次CPU/51草稿收口](cpu/qwen_boundary_and_scoring51_closeout_20261004_v1.json)、[本次非作者报告](../../reviews/non_author_ea69_r17_qwen_semantic_review_20261004.md)。完整摘要和SHA见同名JSON。
