# B5 最终静态审查报告

本夜最后固定两题已完成公开阅读 → 主审独立初判 → 自身历史核对 → fresh独立复核 → 协调者收口。两题均保留 `needs_review / static_review`，仅供 `development_diagnostic`。本批没有优先模型候选；先保留两项具体CPU对照，全部未执行。这是针对各自问题的优先顺序，不是永久拒绝或“全覆盖后才允许任何模型观察”的统一门槛。

| 任务 | 决定性结论 | 唯一优先后续 |
| --- | --- | --- |
| [python__mypy-11707](results/python__mypy-11707/card.md) | 题面明确普通.py两种改名导入都成功；公开旧文档要求同名as，gold静态上使两者拒绝。两项隐藏参考均为stub，未裁决普通.py语义。另有去掉真子模块豁免的具体回归漏测候选，未执行 | 原四文件base/gold×Y/X，分别保存诊断；结果验证行为，规格选择仍需明确 |
| [getmoto__moto-5406](results/getmoto__moto-5406/card.md) | backend已按地区存表，错误在ARN固定East1；gold核心合理。唯一地区断言改成East2，直接替换常量的错误修复可能满分；尚无该候选实际分数 | base/gold/固定East2候选的原27项评分，加既有公开East1 ARN断言；诊断与reward分开 |

两名reviewer从原件独立得出主要发现，在初稿封存后才看到公开读者、主审和自身旧记录。Mypy reviewer接受将首步从合并语义/粗改回归收窄为四文件对照；两项最终复核的状态/引用修订均已纳入card和record，无未解决的核心静态结论分歧。运行、公开语义取舍及actor条件仍不能靠审查者一致代替。

历史原件的适用条件分别保留：Mypy是install_wave1派生镜像 `e3e933e4…eab1f`，gold两项过/reward1、noop一过一失败/reward0；Moto是原baseline01，无derived条件，gold27过/reward1、noop26过1失败/reward0。两题原安装和目标断言链都有证据，不是零测试或安装失败凑出的分差。它们不是本轮重跑或正式actor验收。Moto历史actual image ID仍为null，manifest/tag不能代填。

源码初态也分别记录：Mypy真正共享差异是test-requirements的types-typing-extensions==3.7.3 pin；typeshed多文件diff位于git show，属于base提交。Moto的ThreadedMotoServer diff同样来自git show，noop显式diff为空。未来计划保留这些条件；旧/work路径、构建审计和镜像引用不等于当前载荷可达，Mypy原wheel context缺失明确列出。

旧结论的实质纠正：Mypy“没有公开反向线索”被文档反证，“字面解必得0”混淆.py与.pyi；Moto“26P2P全改名且不保护旧行为”错误，实际22改名、4原名，测试体仍有回归作用。旧hints/可见性转述、跨题去重和成本都不移植为本轮已验事实。

原40项check编号保持不变：两题3/7/24收窄为unknown，Mypy2与Moto26也收窄；规格问题归23，覆盖风险归25，未证gold新增回归。资源单位、Moto流测试路径和region仍用于默认加密键的细节更正保存在后稿；封存文件不改。当前actor消息、依赖/资产可用性、源码导入和权限仍未知，未增加路径排除或题目修订。

交付及链路：2题各7文件，共14结果文件；6个实际fresh角色、6份封存稿、2份最终review、4次实际材料放行。登记区间计算的并发峰值含协调者为3，未超过4。准备者的3426 blob、6源行、2prompt、4运行引用验核被明确复用；协调者对36环境文件核SHA256/bytes无差异，manifest/inventory身份一致。最终18个非自身输出摘要及核验详情记在[assignments.json](assignments.json)，不对assignments自身计算循环摘要。

入口：[静态候选与暂缓理由](probe_candidates.json)、[两项完整CPU计划](cpu_queue.json)、[方法与纠正](method_adjustments.md)、[Mypy复核](results/python__mypy-11707/review.md)、[Moto复核](results/getmoto__moto-5406/review.md)。CPU计划保留镜像/代码归档/入口/选择器/初态/预算/原始行定位和结果判据；新目标环境、重定位输入与执行调度尚未准备。

本批只写五份汇总及逐题七文件；没有项目运行/导入/测试、安装、网络、容器、SSH、GPU、模型实验、quota/reset、提交推送或B6。B1–B4、准备材料、源题/测试/gold/参考/评分均未修改。私有审查材料不进入独立solver上下文；未批准训练或正式评测。
