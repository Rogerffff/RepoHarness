# Dask7305：Qwen 首轮与双模型结果分析

2026-10-04。两模型各一次首轮已齐：Qwen原正式分0，Coder原GPU准备失败None保留、同原FP的CPU派生分0。两候选均未满足公开的大整数精确端点目标；105参考完整、104P通过。未发现本次新增题面/测试缺陷、评分误拒或控制污染，不追加CPU矩阵或模型重试。单样本不证明稳定能力，不授训练资格。

Qwen的真实首次失败是原二值uint64、1输入/3输出分区，最小端点预期`612509347682975743`、实际`612509347682975744`。此前1→1和本次dtype检查通过；最大端点、排序、set_index区间/行量和后续auto未到达。全模块1failed/104passed/3个原slow skip；三个skip位于正式参考外。

实际FrozenPatch只改`partitionquantiles.py`：钉回输入分区摘要的min/max。欠采样合并分支仍用`np.interp`后转整数，源码与正式失败值相符。该机制是原件静态路径加实际失败证据，未重新插桩运行。三次Edit在baseline逐字重放等于FP；临时array修改已完整撤回。正确替代解`gold_full_auto`的既有正式正对照通过，不能因为两模型同处失败判题目不合理。

模型先定位第一层float64精度损失；全局修改array._percentile引发普通quantile失败后，它读取core并主动撤回，纠错有效。但最终验证只选择array、dataframe quantile/repartition和少量输出1/2分区实例，没有shuffle目标模块、1→3欠采样、auto及完整行归属。若干uint64直接比较Pythonint可能掩盖精度差异，所测实例已有正确打印，不能一概说自测假通过。最终“fix is complete”超出证据。

Qwen求解120.362秒；39响应/39 CC turns、38工具（8 Read/27 Bash/3 Edit），累计输入1,092,050、输出14,782tokens，最大单请求输入46,696。CC116.863秒、累计API94.332秒另列，API时间不是纯GPU耗时。正常完成，无预算耗尽；工具错误标记0不能否认内容中真实测试失败。环境评分508.037秒，实际trusted setup477.917478秒；安装0/0.887秒、测试1/15.174秒。

本地逐SHA/大小核148原件17,888,313B、33回执引用和18项Coder CPU关联证据。code9/R25实际输入及完整single-shell脚本`a071ed0d…00450`与已验Coder CPU相同，setup900、五个export均在激活/安装后且pytest之前；actor/grader实际镜像ID为b4f1…8b99。grader33资源样本PID峰19、事件max0、内存峰2,261,078,016B、memory事件全0；actor10样本PID46，均未见OOM。PID1自然结束、双层清理、manager1创建/1移除和drain active0已核。

以上实际镜像ID/脚本/样本不能替代完整Docker Config、内核profile或子进程环境审计。原policy的actual_image_inspect_verified=false、actual_execution_mode=null、two_stage=false和原diag resource_facts=null保持；声明的2CPU/4GiB/pids512/断网、观察的single-shell/supply=null分别列出，子进程env/BLAS内部计数未直接测。after-install仍只有静态身份，本次未执行分段模式。

原Coder GPU setup300 None、setup900/PID143、同FP CPU0及原17行控制证据分别保留。Qwen新臂是缺失模型的首次覆盖；本次作者/非作者分析没有新增模型、CPU或控制运行。双模型结果以独立候选核和完整原件为依据，当前没有新题级阻断；后续仅按最新全局规则与具体新缺陷决定是否额外处理。

证据：[结构化分析](model_probe_qwen36_a1_analysis_20261004.json)、[非作者核查](../../reviews/non_author_7305_qwen36_a1_candidate_review_20261004.md)、[Coder同FP CPU读回](coder_original_FP_CPU_recovery_readback_20261003.md)。原始封存、完整轨迹索引、实际五脚本/材料/profile和逐参考均链接在结构化分析中；[题卡](card.md)与[当前入口](../../preparation.md)维护后续状态。
