# 8511：repr 修复引入继承回归，首 Coder 拒绝有效

2026-10-03。**公开示例修好，正式173项参考中172通过、1失败，原奖励0保留。** 唯一失败是无本地注解的子类继承隐藏字段时构造报错，属于候选源码回归。当前材料正确拒绝此候选，没有需要改版材料或重跑CPU的新证据。

题主完整阅读276条原轨迹对应的2662行非重复正文、22次工具及返回，核全部356件封存成员／23,240,483字节、452项真实baseline、全部正式参考及成功写入／编辑／删除到FP的一致性。[独立执行复核](../reviews/non_author_8511_8567_coder_q24_execution_review_20261003.md)通过并获核收；[题主机器读回](../coordination_20261003/8511_coder_first_arm_owner_readback_v1.json)保存逐件绑定。权威是`closed_snapshots/gpu1003-pyd8511-coder-a1`，旧remote副本不覆盖它。另一模型首次结果尚待，整请求仍claimed，不ACK、不清活动指针。

| 诊断方面 | 结论与证据范围 |
| --- | --- |
| 目标源码语义 | 新包装将`FieldInfo(repr=False)`转为stdlib field，公开输出从`a(b=1,c=2)`改善为`a(b=1)`，原F2P通过。但最终两个版本分支均使用`getattr(cls, '__annotations__', {})`，无本地注解的Child因此读到父类注解，并把继承FieldInfo包装成子类本地field。stdlib按子类本地注解检查，抛`TypeError: 'x' is a field but has no type annotation`。实际失败链为私有测试2671→候选dataclasses.py235→Python3.8 dataclasses.py885。继承保护保留，不把基线已能隐藏repr作为额外要求。 |
| 完整候选与验证 | 初稿在Python3.8直接读取`cls.__annotations__`导致6个公开失败，模型随后改用getattr，公开基本3项、metadata4项、其余162通过／11跳过／4 deselected。最后未覆盖新增私有继承情况；“所有测试通过”仅符合所选公开范围。三个自写复现脚本运行成功后实际删除，完整FP仅有`pydantic/dataclasses.py`一项，没有遗留失败脚本或正式测试改写。 |
| 评分一致性 | install RC0、test RC1；1F2P通过，172P2P中唯一hidden inheritance失败，另3个新增P2P通过；全部参考有实际状态，无missing或skip。完整文件摘要是172 passed／1 failed／11 skipped，skip不在173正式参考内。452项tar路径／类型／规范执行位／内容和actor→grader census一致；原FP摘要`b8f75c2c…`，全部FP投影运输。原parser对非参考空白参数／跳过项的限制未修复，不用其总键数替代逐参考核查。 |
| 公开要求与求解依据 | 首HTTP有与原prompt逐字节一致的文本块，无新增hints；private有效补丁和新增P2P标记未进入请求正文，私有评分文件没有挂入actor。模型读完整1137行fields、313行dataclasses及270行内部dataclasses，独立提出包装并自测。继承失败来自未处理公开可理解的类属性继承语义，没有新增题外要求。 |
| 环境与运行身份 | queue_v24／题级code_v8；实际actor与grader同`df6c3aff…`镜像，Python3.8.19/core2.14.5。actor UID54321、激活／prelaunch和公开wheel读取通过；grader UID54322固定前置及editable／testing requirements安装成功，源码导入正确，runner保护前后摘要相同。固定wall10800、240回合、context196608、输出65536；正式whole/setup/apply/test为3600/300/120/1800，没有超时。baseline环境digest仍null，不补填typed资格。 |
| 效率与并行 | 23生成HTTP/SSE＋1 count_tokens均200；22工具为3 Read、3 Write、12 Bash、4 Edit，全串行、无子agent，1次工具失败是初稿公开测试。累计输入629984、输出5063、合计635047，上下文重复计入累计输入；最大单请求输入38587。首HTTP到首次生产编辑11.406秒，solve57.322秒；CC53.763秒及其中API45.636秒不相加。完整大文件读取和末尾既有依赖git diff增加上下文，不能把累计token当单请求占用。 |
| 模型来源、资源与清理 | 派发前实测engine／adapter身份、只读固定Coder revision `b2cff646…`及真实HTTP服务关联获独立复核；两次inspect属于派发前capture，不称作作业结束后checkpoint证明。adapter仍运行code_v4服务，不能混称题级code_v8。旧checkpoint_verified=false保持，未重算权重或GPU内存哈希。按本job实际CID关联22个有限采样：actor6、relay6、grader14；安装2.041秒／测试2.105秒各0采样点，缺口未知。report峰值643.926与外部grader采样峰值分开记录。quiescence、gateway revoke/drain active0及actor/relay/network、manager1建1删无本job残留，未宣称全机PID0。 |

`pdm.lock`与`pyproject.toml`在求解前已脏，其字节属于真实baseline，本次FP没有它们；末尾git diff不能归因给模型。本轮没有新CPU/GPU/模型调用，也没有修改原候选、测试或分数。继续原固定请求的Qwen首次臂，随后分析两模型在本题上的失败信号；首臂不证明稳定成功率、训练或留出资格。
