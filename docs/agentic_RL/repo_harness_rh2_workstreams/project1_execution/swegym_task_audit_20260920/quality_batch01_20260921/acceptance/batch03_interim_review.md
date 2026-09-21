# 第三批根阶段检查

2026-09-21 05:23 heartbeat实到；05:24后核验。第三批仍在正常推进，独立复核整包尚未交付，**本记录不是整题验收**。已核8份公开稿摘要、4份主审封存摘要和保存早于历史开放的登记，无不一致；后续新文件不包含在此计数。

根读取DVC6954/3665、mypy15139短卡，并对后两题独立读公开题面、完整test/gold patch及决定性源码：

- DVC3665：4个新测试确实直接调用base没有的`Config._to_relpath`。原`_save_paths`闭包与`PathInfo.as_posix`提供内联实现路线；隐藏helper形状要求与公开跨平台持久化目标可分离。Linux金补丁通过不能证明Windows行为；主审已把窄模拟与原生Windows区分。后续CPU交接也应区分Linux原grader分数与Windows语义证据，不承诺现成Linux容器就是Windows复现。
- mypy15139：公开例明确包含reveal note；新增测试只查赋值错误，gold仅改`messages.py`错误formatter。根核`messages.py:1630–1632`的`TypeStrVisitor`调用与`types.py:3188–3189`固定`Type[...]`。支持单独核原题CLI的建议；未实际执行，不能填写gold公开原例已实证失败。

暂不把根的这些原件观察输入fresh reviewer，待其独立初判封存后再综合。当前没有需要打断协调者的材料或方法阻塞。活动assignments比尚未刷新的batch_report更近，不因中间汇总滞后而判交付失败。

可见周额度用41%剩59%，其他窗口不可见；本夜重置授权已消耗，不再兑换。只另准备后备第四批3题材料（原池排除前三批后DVC/mypy/Moto各1题，固定seed），尚未派发质量审查。能否启用取决于第三批验收与剩余时间；不为用额度重审旧题。本轮没有项目/测试/容器/SSH/模型执行。
