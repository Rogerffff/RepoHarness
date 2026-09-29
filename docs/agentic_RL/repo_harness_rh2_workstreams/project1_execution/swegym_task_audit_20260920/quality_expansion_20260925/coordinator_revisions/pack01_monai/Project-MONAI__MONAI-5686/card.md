# Project-MONAI__MONAI-5686

`needs_review`：flag漏测真实梯度且gold留下多通道缺陷；仅development_diagnostic，独立review待完成。base `25130db17751…`。gold绕过loss最外层metric.detach，对题面单通道路径合理，但C>1内部递归仍走带detach入口。

| 需求/旧行为 | 公开依据与验收 | 判断 |
|---|---|---|
| 单通道输出requires_grad | 题面；F2P test_grad_0/1仅验flag | noop双失败、gold双通过；CPU两项语义重复 |
| 梯度到输入、值正确 | Loss用途；八个2D/3D常量P2P | 数值双方通过；没有backward/正确导数检查 |
| C5公开用法可微 | loss docstring:69–74；regression:329–345 | gold递归再次detach，静态漏修；非新增回归 |

八方面已查：公开目标、版本初态、全部新增fixture与2F2P/8P2P、非gold纯计算路线及错修、gold/metric调用链与边界、合成CPU张量需求、投影可信恢复、用途暴露。没有运行项目、mutant、多通道或数值导数实验。batch拼接还有base既有缺陷，不归咎gold。

check25包含flag不能代表梯度正确、B>1/C>1/3D梯度未测；check27的依据是公开C5残留，不是“调用私有helper”本身；check26未知。给输出加0*y.sum()甚至可得到存在但错误的零梯度。CUDA只追加测试，既有参考ID与含义不变，不能仅因总数变长宣布CPU参考错配。旧5908关联未跨题核实。

原w06-1 ledger3/4确有目标两失败→通过、8P2P双方pass；无缺席/skip，投影只含loss.py。实际image ID缺失；actor消息、准备后初态、解释器/源码/权限资源均unknown，历史grader不等于actor资格。审查含私有答案与旧结论，须隔离solver。

唯一优先下一步：私有CPU用公开B1C1/B1C5例做gold对照，固定无梯度data_range，记录loss flag、backward/y.grad和前向值，确认多通道残留以决定参考/验收修订；本轮只提案，不执行。完整映射和范围见analysis_before_history.md，历史差异见old_findings_delta.md。
