# 6043 历史差异复核

root release 后只读本题 refs 所列L1（09-16）和pilot（09-20）两份记录；SHA与refs一致。没有沿记录去读旧fake.diff、verification.json、L7日志、其他题、根汇总或reviewer。这些旧实验结果只能以历史记录转述级别引用。

| 旧主张 | 处置 | 证据、理由与边界 |
|---|---|---|
| 无示例、只有散文，任务不可解，应reject_revision | 反驳；确认pilot的收窄 | 题面给确定排序目的及递归处理方向，公开generate/generate_definitions可定位；缺示例不等于不可执行。封存前稿未主张不可解或自动剔除。 |
| L1 check3把措辞不足判成实际输入错误 | 纠正编号与范围 | 实际actor输入没有捕获，check3 unknown；措辞/旧契约优先级归check23。 |
| gold保留list位置就是少实现一半；所有列表排序会破坏allOf/anyOf语义 | 反驳该一概解释；确认pilot的prefixItems理由 | json_schema.py:601–621和完整tuple测试证明prefixItems按位置解释；enum/examples旧测试保序。合理做法是递归值而不重排列表。不能靠“keys and items”字面把任意列表排序变成要求，也不能笼统把所有allOf/anyOf列表等同位置数组。 |
| 唯一非平凡键序断言仅test_by_alias；只排序properties即可骗过递归要求 | 确认静态覆盖缺口；旧满分实验未直接复核 | 前稿核完整patch/决定性测试、风险P2P和keys/list检索：缺根键、嵌套schema、$defs和批量出口的次序断言。pilot声称旧独立脚本fake通过304个参考ID、纯字典局部实验区分fake/gold；其原件未在本次release范围内，不能升级为当前RH2满分实证。 |
| 所有303个P2P都是dict相等；没有任何其他有用约束 | 收窄 | 元组prefixItems、enum/examples/required列表、引用/模式、generator复用错误等确有内容/次序护栏；它们保护语义但不足以证明映射递归排序。前稿按风险抽查，未通读所有303项，保留范围。 |
| 测试不要求唯一实现，check24可pass（L1与pilot） | 部分确认，新增实质冲突 | 不强制helper名/算法属实；但公开docs/usage/models.md:964明确保schema字段顺序，私有test_by_alias却要求字母序。保properties声明序而递归整理普通键是合理非gold路线，会在唯一F2P被拒；这是行为范围误拒风险。旧两份记录都没处理该公开承诺。 |
| 影响全schema出口即证明gold新回归（L1 check26） | 纠正；新增更具体证据 | 跨文件范围不是回归证明。本次按gold完整递归分支证实z,a字段会变a,z，和明确旧文档契约冲突；行为改变可静态证明，是否被新需求授权仍待规格裁决。无需把tuple保序错误地列为gold回归。 |
| 先补嵌套/$defs/批量顺序测试，随即进入探针 | 调整优先次序 | 补覆盖方向合理，但应先裁决properties保序与新排序要求优先级，否则补测试会把私有选择固化成新增规格。唯一下一步是规格裁决，非CPU重跑。 |
| install rc=2/必须联网仍阻断 | 已被09-19本题原grader对照替代 | 两次install RC0、noop唯一F2P失败/gold PASS、deny_all离线wheel和准确image ID已在前稿核验；旧R2失败位置未获得原栈，actual actor仍unknown。 |
| 与6126/9066无重复、version字段时间排序异常、R4残余 | 具体旧跨题/控制面结论未核 | 不读取其他题，版本锚定本题base与digest；check5/31保留unknown，不沿旧描述扩读。 |
| 题面给算法使难度低、应剔除或正式可用 | 难度/收益未核，不继承准入 | 未有本轮模型或成本事实；保持needs_review/static_review、development_diagnostic，无题目修改。 |

对前稿的影响：主要判断不变。明确接受pilot对“无示例不可解”和“列表保序必定错”的纠正；旧fake实验仅增加转述上下文，不把静态风险升级为当前实测。独立新增的字段保序契约冲突保留，并改变相较pilot的优先下一步：先定规格再决定覆盖修订。没有修改前稿、题面、gold或测试。


已读历史原件（仅以下路径，均核SHA）：
- `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_pydantic/records/pydantic__pydantic-6043.json` — `d70d6dadddbb76760aa7bb2d8a0d52cd27a1008c64a8300836432b5fc49d4a33`
- `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/pydantic_pilot/records/pydantic__pydantic-6043.json` — `6ccbb512ba171740bd923589e779d7c5f9f2339c128596d6b748fe82caa24d60`

封存前稿SHA256：`4e24beb223a49e4b19725196b232f9675b2f4445657b850e1c750098d05c03cf`。前稿未改；无新项目执行。全部证据定位以本题analysis_before_history.md的PUBLIC/PRIVATE与原日志附录为准。
