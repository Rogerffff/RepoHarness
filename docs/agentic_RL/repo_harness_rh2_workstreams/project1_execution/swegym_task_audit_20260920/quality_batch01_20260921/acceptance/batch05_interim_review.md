# B5 根原件抽查（独立复核尚未结束）

根在协调回调后直接读取两题完整公开prompt、gold和test补丁，并定位以下公开源码。尚未读取B5角色结论；本页不是批次验收、CPU实测或最终处置。不得提前交给未封存的fresh角色。

- **mypy11707**：公开Expected明确要求X-as-W、Y-as-W均成功；base的`docs/source/command_line.rst:556–576`正文虽泛称from-as，例子明确`bar as bang`不导出，只有同名alias或`__all__`才导出。`mypy/semanal.py:1841–1845`与该例一致；`1895`旧豁免仅看fullname是否模块，gold新增MypyFile类型约束。隐藏新增stub case显式要求改名类alias不可见。因此“统一为都拒绝”与公开期待之间存在直接张力；这是题面与仓库既有规则的方向冲突，不能直接归为gold新增回归，也不能靠gold得1自动决定题面错。附近1879–1911公开case保留真实子模块导出豁免；后续若构造删掉整个豁免的候选，须同时看这些控制。根只作源码推断，未跑四文件原例。
- **Moto5406**：公开复现创建表名与预期ARN末段不同，属于需注明的小不一致；region目标本身清楚。base `models/__init__.py:1200–1207`已把backend region传给Table，`568–569`将显示ARN硬编码为us-east-1，`580–589`原样输出它；gold存region并用于ARN。test补丁把唯一TableArn断言的region改成us-east-2，其余大量改名不等于新增跨region验收。将常量改为us-east-2是具体待验证的过拟合候选，但没有运行，不声称其实际拿满分；亦不据此否定整题价值。公开mock客户端多region核验可检出该行为，无需真实AWS。

材料入口：`runs/swegym_quality_batch05_20260921_v1/`。本次没有读取或执行项目测试、容器或模型；历史日志的安装与结果仍沿准备证据，根最终验收时再定点核查。保留mypy的install_wave1与Moto的原baseline差异，不把任一grader记录当actor开发证明。
