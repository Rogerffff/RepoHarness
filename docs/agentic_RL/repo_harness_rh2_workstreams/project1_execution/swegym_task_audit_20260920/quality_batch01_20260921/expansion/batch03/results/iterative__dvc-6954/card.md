# iterative__dvc-6954

目标：base `28dd39a1a0d7` 的 Python 负数参数能用于 run/repro。建议 **needs_review / static_review**，仅作 development_diagnostic 静态候选；正式 actor 未验。

| 需求/旧行为 | 参考与覆盖 | 证据 |
| --- | --- | --- |
| 负整数读取 | F2P `test_parse_valid_types[UNARY_OP` 比较 -1，直接命中 | noop 日志:667-673；gold:707 |
| 原类型、容器、class/self、忽略调用/算术 | 12 P2P 比较返回值，均通过；不锁实现 | test.patch:14-50；base _py.py:89-181 |
| CLI、lock、负 float/容器负元素、更新 | 共用路径已查，冻结参考未覆盖 | param.py:64-138；stage/serialize.py:109-125；分析 §2–3 |

八方面已核公开要求、精确材料、全部新增断言/必要 fixture、合理替代路线、gold 与相关调用者、安装消费、官方恢复和暴露用途；未核正式消息/actor、全仓回归、可见资产泄漏及跨题谱系。新 P2P 可以保护旧行为；忽略调用/算术有公开源码依据，旧“必须补题面”不采纳。

历史固定 grader 的两 ledger 第1行：gold 13 passed/reward1，noop 1 failed+12 passed/reward0，missing/skipped=[]。13 个参考 ID 均为空白截断但当前逐项无碰撞；未来增用例须重审身份。原输入为 dvc_install_v1c/recipes/iterative__dvc-6954.json，wrapper 替换安装段；真实日志证明离线 editable 安装成功，不能以 COPY wheels 代替。运行资格均 absent，rh2grader/54322 的成功不等于 agent 可用。

仅整数负号的部分修复可能过参考而漏负 float；尚未跑反例。优先下一步是在明确正式 actor 条件下跑公开 repro→lock/不变跳过→改值流程，并以同形 -0.5 验证负浮点。无新依赖/远端资产，无新增排除；独立 reviewer 已完成，协调者收束同意受限静态候选。详见 [封存分析](analysis_before_history.md)、[历史差异](old_findings_delta.md) 与 [结构化记录](screening_record.json)。本审查已见 gold/隐藏测试/旧结论，不能充当 solver。

协调者复核：独立初判与最终复核的封存关系见 [review](review.md)。3665核心helper/保存接线出现在4785公开base中，6954为演化版本；这是具体代码包含关系，尚非完整Git谱系、重复题或实际solver泄漏证明。
