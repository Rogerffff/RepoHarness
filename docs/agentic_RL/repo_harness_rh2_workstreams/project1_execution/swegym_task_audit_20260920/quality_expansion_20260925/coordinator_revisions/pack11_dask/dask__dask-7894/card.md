# dask__dask-7894 静态审查卡

**needs_review / static_review；development_diagnostic。** base `bf4bc7dd8dc96021b171e0941abde7a5f60ce89f`。目标是map_overlap删除轴后同步重排depth、boundary，使计算值与裁剪轴一致。

| 需求/旧行为 | 公开依据及断言 | 结论 |
| --- | --- | --- |
| depth重新编号 | 题面；新增七参数均值比较 | 五F2P失败→通过，两新增P2P保持通过 |
| boundary重新编号 | 题面明确要求；trim区分none | **漏测**：七参数边界均非none，不能拦住只改depth |
| no-drop、trim=False、零depth | 公开源码分支及已读P2P | 历史局部正证据，非全部组合证明 |
| 懒数组元数据一致 | chunks公开契约 | 新测试先compute，未直接检查其chunks/shape元数据 |

八方面已查：公开目标、静态版本/初态、完整新增断言与helper、全部expected状态和风险抽查P2P、合理非gold路线、全部gold及裁剪调用链、开发需求、交付/可信测试恢复与答案暴露。未读范围和双向表见封存分析；actual actor消息、工作树、权限、资产、资源均unknown，reviewer未读。

09-19原pair：noop 5失败/75通过、RC1；gold80通过、RC0；安装RC均0。命令为 `pytest -n0 -rA --color=no dask/array/tests/test_overlap.py`，Python3.9.19。源manifest为e66d08cf…，actual image ID=null；不能据旧grader认定当前actor可用。精确日志/账本/完整digest见analysis_before_history.md。

历史对照确认09-20的boundary漏测判断，纠正早期“depth-only会失败”和“kwargs.pop修改外部字典”的说法。new_axis是邻近未验边界，无已证gold新增回归；不以无seed直接判抖动。无额外排除或题目修订。

**唯一优先下一步**：任务二在私有CPU副本对base/gold/depth-only候选做原选择＋确定性混合none边界例，核值、shape、chunks，验证是否实际漏接收不完整修复。仅建议，未执行或派发。审查资料已含gold/隐藏测试/旧记录，不交独立solver；无训练或正式评测资格。
