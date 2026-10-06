# Dask9378：Qwen 首轮与双模型分析

2026-10-04T01:59:26.439112+08:00。Qwen原raw1/137参考全过；Coder原GPU None/同FP CPU1亦按用户B通过，旧可选参数限制分别保留。 [非作者核查](../../reviews/non_author_9378_qwen36_a1_candidate_review_20261004.md)与作者原件核一致：当前目标通过，未见新增材料/评分缺陷或正式评分污染。不追加CPU矩阵或模型重试；单次结果不授稳定能力或训练资格。

当前目标：用户B：da.ma存在则该入口须正确，否则接受顶层正确路线；默认mask逐元素一致、ones/zeros有效值正确，empty未初始化值不作判据。

实际修法：新增ma.ones_like/zeros_like/empty_like；默认按np.ma block操作保mask；显式dtype另用wrapper传dtype_arg，避免只改Dask元信息。 先复现顶层丢mask；主动发现computed dtype仍int，几轮重复传a引发错误后读取绑定map_blocks，去掉多余数组实参，最终float64实测正确。

验证：默认mask3项通过，dtype/普通数组4pass，最终masked公共141pass=134旧项+7自写项；原正式137=3F+134P单列。自写empty_like比较未初始化值的oracle不可靠，私有评分不沿用。 列新ma入口和dtype wrapper，与实际代码相符；原例标签换成da.ma属于题面容许B路线，最后NumPy参考标签实际调用Dask，不当独立交叉验证。 仅默认B资格通过。新Qwen签名只a/dtype，不接受chunks/name/shape/order；原Coder dtype失败、chunks/name/shape忽略及过宽说明是该旧臂边界。Qwen少量dtype实例不证明全部可选API或稳定能力。

求解112.663秒，49唯一响应/52 CC turns、51工具，累计输入1,346,685/输出13,027tokens，最大单请求输入55,372；正常完成，无预算耗尽。CC 109.128秒、累计API 85.34秒另列，API不是纯GPU时间。49唯一响应/52 CC turns保留；三次响应各给两项独立工具（L11/15、30/34、133/137），其余多串行。不能一概称全串行，亦不推广并发吞吐。

本地逐SHA/大小核163原件26,483,962B、33执行回执引用和17项Coder CPU关联；逐Edit重放等于实际两项FP，正式projection只纳生产文件。模型新增测试留在原FrozenPatch，但被正式评分排除并恢复固定测试，因此自测与正式通过分开。原模型材料/prompt/预算一致，旧通用hints交付范围沿用已对齐澄清，不能据未交“不改测试”判违令。

code9/R25实际材料、actor与grader镜像ID、完整single-shell脚本/预算已核；脚本与已验Coder CPU相同，仅setup900、selected_env=null，不套7305五键。评分406.519秒，trusted setup383.92093秒，安装rc0/测试rc0；环境时间不算模型能力。grader 27资源样本，PID峰8/max0、内存峰2,398,384,128B，未见OOM；自然结束、双层清理、manager1创建/1移除与drain0已核。

原policy image_inspect=false、mode=null、two_stage=false和diag resource_facts=null保持。声明2CPU/4GiB/pids512/断网与实际镜像ID/脚本/有限样本分别列出，不冒称完整Docker Config/内核profile或子进程env审计，after-install未执行。原Coder GPU None、同FP CPU派生分、历史控制与分析不回写；本次只有原件分析，没有新CPU或模型调用。

[结构化分析](model_probe_qwen36_a1_analysis_20261004.json)绑定完整轨迹索引/运行原件；[原Coder分析](model_probe_coder_a1_analysis_20261003.md)与[同FP CPU读回](coder_original_FP_CPU_recovery_readback_20261003.md)保持各自范围。[题卡](card.md)和[当前入口](../../preparation.md)维护后续状态。
