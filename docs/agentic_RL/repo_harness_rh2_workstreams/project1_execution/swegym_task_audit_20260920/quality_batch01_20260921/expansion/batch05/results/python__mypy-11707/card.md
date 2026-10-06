# python__mypy-11707

**独立静态复核完成；保留 `needs_review / static_review`，暂不列模型优先候选。** base=`5d71f58b9dc5a89862253fef3d82356a7370bf8e`。题面要求关闭隐式再导出后，两种普通 `.py` 改名导入都成功；公开文档规定只有同名 as 才导出，gold 静态上使两者均拒绝。必须保留这一方向冲突，不能用gold满分代替规格裁决。

| 需求/旧行为 | 覆盖与结论 |
| --- | --- |
| 原四文件Y/X两版均成功 | 没有原例运行；与公开旧契约/gold静态方向冲突 |
| stub同名导出保留类身份、改名符号隐藏 | F2P两条类型/诊断断言；历史gold过、noop缺隐藏错误 |
| 非公开C隐藏，D仍可用并保留类型 | 唯一P2P，两侧历史均过 |
| 真子模块仍可导入 | 公开 `testReExportChildStubs` 未被选择；删去模块豁免的粗改可能过评分却破坏它，尚未实测 |

八方面已独立核读：公开目标、材料初态、全部两参考与helper、替代解边界、gold及相关回归、开发依赖、交付评分、暴露用途。未验原例实际行为、合法/错误替代解、全仓回归、跨题关系及真实actor。check2/3/7/24因此收窄为unknown；静态发现和历史运行事实仍保留。

历史install_wave1派生镜像 `e3e933e4…eab1f` 的grader gold=1/noop=0、安装与清理闭合。两侧初态均保留 `types-typing-extensions==3.7.3` pin；typeshed的git show不是环境脏改。当前actor是否消费该配方、实际消息/权限/源码导入与资产仍未知。峰值只记原 `mem_peak_mb`；封存稿单位表述由review更正。

复核同意纠正旧“无公开反向线索”和“字面解必得0”：文档已有明确线索，而全部隐藏参考为stub，不能排除区别普通.py/stub的实现。未证gold新增回归，也未改任何题面、测试或参考。

**唯一优先未来CPU：原四文件base/gold×Y/X。** 四项诊断只验证行为，不能自行选择规格；粗改加真子模块对照另作后续窄校准，不要求全族测试先于所有模型观察。两个独立问题均保留，实验尚未执行。

证据：[封存初判](analysis_before_history.md)、[历史差异](old_findings_delta.md)、[独立复核](review.md)、[结构化记录](screening_record.json)。仅 `development_diagnostic`；审查者已见gold/隐藏测试/旧记录，不能提供给独立solver；未批准正式训练或评测。
