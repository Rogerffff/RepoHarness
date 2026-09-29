# dask__dask-9212 静态审查卡

**needs_review / static_review；development_diagnostic。** base `aa801de0f42716d977051f9abb9da2c9399da05c`。目标是Enum token稳定并区分成员。公开题面已有与gold核心相同的建议函数，宜记录为有修法提示的执行题，不能作为无提示定位指标。

| 需求/旧行为 | 公开依据及断言 | 结论 |
| --- | --- | --- |
| 同成员稳定、不同成员区别 | 题面及哈希用途；四类RED/BLUE关系 | Enum/Flag两F2P修复，int两类P2P保持通过 |
| 类型身份充分代表参数 | 文档；delayed(pure=True)按token建键 | gold只取类短名，同名不同模块Enum固定碰撞；用户结果回归尚未执行 |
| 非Enum语义保留 | 对象/容器/dataclass旧测试 | 已读局部P2P有正证据；复杂value及Enum hook交互未覆盖 |

八方面已查：公开目标/版本、完整新增断言与helper、全部expected状态和P2P风险抽查、非gold实现空间、全部gold/MRO及delayed调用者、开发条件、普通候选投影/恢复、关系与暴露。详细阅读边界见封存分析；actual actor输入、初态、权限、资产及资源unknown；主审出稿时未读reviewer，独立交叉复核现已完成。

历史compat_v2b：离线pins为pandas1.4.4/numpy1.24.4，Python3.10.14；noop两目标失败、gold126通过/3跳过，测试RC1/0，安装均0；105 expected无缺失/跳过。derived actual ID=5b694933…；完整digest/命令见分析。parser125与pytest129的差异保留，不能只凭总数证明非expected全部解析。

旧10项恒失败不适用于此修订pair；也不证明当前actor已修复。旧记录报告8792关联，本次未获跨题原件，不确认强制同侧。历史未改变类身份碰撞的静态证据级别。

**唯一优先下一步**：任务二私有CPU副本比较base/gold对两个module不同、同名Color枚举的token、同一pure delayed函数key及compute结果，确认或收窄用户可见回归。未执行或派发；无额外排除、题目修订或训练/评测批准。私有审查资料不得进入独立solver环境。


协调裁定：quality_first，ready_for_probe=false。不同module的同名枚举得到相同规范化表示是静态可证事实；同一个pure delayed函数的联合compute是否给出错误结果未运行，26/27保持unknown。独立review采用该具体私有对照，替代其初判的泛actor核验优先项。题面自带修法属计划公开材料，不冒称actual actor消息或私有泄露。
