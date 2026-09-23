# iterative__dvc-3576

**保留诊断备选，本包不优先列为静态候选**；状态 **needs_review / static_review**，仅用于 development_diagnostic。固定 base `a338fad036bd9ac8bdd79ecec964f8c5558609c4`。目标是缺旧指标仍可比较、JSON容缺、诊断有意义，并把非结果消息送至 STDERR。完整证据见 [历史前分析](analysis_before_history.md) 与 [历史差异](old_findings_delta.md)。

| 关键要求 | 决定性验收与结论 |
| --- | --- |
| 非结果消息的流向 | 唯一F2P仅断言 `_show_diff({}) == ""`，没有流捕获。gold删除提示；公开文本也可合理允许沉默，不能仅因未发stderr认定gold错误。 |
| 缺旧值显示新值、Change为 `-` | base已有缺侧容错和old=None；实际参考只测试造好的diff。gold仍显示 `diff not supported`。 |
| 正常行为保持 | 6 P2P实际为5个表格断言加1个Mock参数转发；真实Git比较、JSON序列化及CLI流向未受本次参考保护。 |

八方面已查范围：①公开需求和base部分既有行为；②全部新增/修改断言、7个参考测试及fixture/Mock；③保留helper旧返回、由caller分流的合理路线，存在静态误拒假设；④gold及生产调用链、公开func和logger回归源码；⑤本地Python/Git/小JSON/临时目录需求及原安装日志；⑥gold投影只含业务文件，官方恢复一份unit文件；⑦同题版本对应，跨题关系未核；⑧已见gold/隐藏测试/旧讨论，不能作未暴露评测。

09-19原件证明修订grader配方安装成功，no-op为0、gold为1，七个测试身份齐全；身份是rh2grader/54322。actor/54321的实际镜像、解释器、工具消息、资产权限仍未知。旧记录“安装干净”“status_map无污染键”被其原始日志推翻；这与新配方改善分开记录。

若安排后续实验，优先固定已引用grader配方，对base/gold/命令层替代解做窄CLI输出与原RH2评分对照；先核外部行为，再判断helper断言是否误拒。实际actor核验是模型开发前的独立条件。

独立[复核](review.md)已完成，协调者采纳其对stderr解释和实验顺序的收窄。保留helper约束与数字展示疑点，未写成实测误拒或确定gold错误。没有新运行，未改题面、测试或reward；附加排除为空。
