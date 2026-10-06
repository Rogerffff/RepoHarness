# Dask7138：Qwen 首轮与双模型分析

2026-10-04T01:59:26.439112+08:00。Qwen raw1/470参考全过，完整正式module562passed；Coder原GPU None/同FP CPU0因漏array=兼容保留。 [非作者核查](../../reviews/non_author_7138_qwen36_a1_candidate_review_20261004.md)与作者原件核一致：当前目标通过，未见新增材料/评分缺陷或正式评分污染。不追加CPU矩阵或模型重试；单次结果不授稳定能力或训练资格。

当前目标：ravel接受标量/array-like、正确展开并返回Dask Array；保留array=旧关键字，题面已有转换引导。

实际修法：保留ravel(array)签名，将array.reshape改为asanyarray(array).reshape；转换与旧调用兼容。 正确复现list无reshape并读取同文件转换惯例；一行生产改动、一次新增公共测试，未反复换算法。

验证：三个聚焦用例各过、ravel选择11pass/550deselected及二维Dask实例通过；模型未跑完整module、未显式测标量或array=，正式私有470项另确认。 只称array-like转换与11个ravel相关测试通过，与轨迹相符；新增测试注释issue/XXXX为占位，无评分作用。 本轮有限输入，不证明全部NumPy选项兼容、稳定能力或训练资格；不新增零拷贝要求。

求解26.193秒，20唯一响应/20 CC turns、19工具，累计输入126,475/输出2,505tokens，最大单请求输入9,349；正常完成，无预算耗尽。CC 22.627秒、累计API 16.008秒另列，API不是纯GPU时间。19工具逐项串行；可批量独立读取，但依赖编辑/测试应串行。

本地逐SHA/大小核139原件14,318,038B、33执行回执引用和16项Coder CPU关联；逐Edit重放等于实际两项FP，正式projection只纳生产文件。模型新增测试留在原FrozenPatch，但被正式评分排除并恢复固定测试，因此自测与正式通过分开。原模型材料/prompt/预算一致，旧通用hints交付范围沿用已对齐澄清，不能据未交“不改测试”判违令。

code9/R25实际材料、actor与grader镜像ID、完整single-shell脚本/预算已核；脚本与已验Coder CPU相同，仅setup900、selected_env=null，不套7305五键。评分487.486秒，trusted setup464.814026秒，安装rc0/测试rc0；环境时间不算模型能力。grader 32资源样本，PID峰8/max0、内存峰1,931,325,440B，未见OOM；自然结束、双层清理、manager1创建/1移除与drain0已核。

原policy image_inspect=false、mode=null、two_stage=false和diag resource_facts=null保持。声明2CPU/4GiB/pids512/断网与实际镜像ID/脚本/有限样本分别列出，不冒称完整Docker Config/内核profile或子进程env审计，after-install未执行。原Coder GPU None、同FP CPU派生分、历史控制与分析不回写；本次只有原件分析，没有新CPU或模型调用。

[结构化分析](model_probe_qwen36_a1_analysis_20261004.json)绑定完整轨迹索引/运行原件；[原Coder分析](model_probe_coder_a1_analysis_20261003.md)与[同FP CPU读回](coder_original_FP_CPU_recovery_readback_20261003.md)保持各自范围。[题卡](card.md)和[当前入口](../../preparation.md)维护后续状态。
