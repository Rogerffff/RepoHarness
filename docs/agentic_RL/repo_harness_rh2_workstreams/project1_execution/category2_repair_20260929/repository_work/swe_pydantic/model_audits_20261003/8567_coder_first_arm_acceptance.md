# 8567：保留 serializer 时破坏 PlainValidator 的内层跳过能力

2026-10-03。**公开bool示例改善，但正式162项参考中158通过、4失败，原奖励0保留。** 生产修复无条件调用`handler(source_type)`，使本应被PlainValidator替代的内层类型强制生成schema；未知类、未解析forward reference与Python3.8 stdlib TypedDict因此报错。当前拒绝合理，没有需要改版材料或重跑CPU的新证据。

题主完整阅读517条原轨迹对应的2901行非重复正文、43次工具及返回，核全部377件封存成员／25,272,259字节、458项真实baseline、完整FP与逐参考状态。[独立执行复核](../reviews/non_author_8511_8567_coder_q24_execution_review_20261003.md)通过并获核收；[题主读回](../coordination_20261003/8567_coder_first_arm_owner_readback_v1.json)保存绑定。权威是`closed_snapshots/gpu1003-pyd8567-coder-a1`。Qwen首次臂待，整请求仍claimed，不ACK、不清活动指针。

| 诊断方面 | 结论与证据范围 |
| --- | --- |
| 目标源码语义 | 候选先生成inner schema，再复制其serialization到新的info/no-info plain validator。bool示例得到`{"x":"0","y":"1"}`，但PlainValidator的既有含义是替代内层验证，不能普遍要求内层schema可生成。新`functional_validators.py:157`的handler路径使两个Unsupported F2P创建类失败；另两个保护P2P分别因NotDefinedAnywhere8567未定义、Python<3.12应使用typing_extensions.TypedDict而失败。这些错误由候选新强制路径产生，不能按错误中出现Python版本改记infra。 |
| 完整候选与验证 | FP共8项：1生产文件＋7个自写诊断文件。`debug_issue.py`缺GenerateSchema的types_namespace，`fix_plain_validator.py`把一参lambda交给with_info接口；两次真实运行失败，文件最终未修正或删除且仍运输。另两次工具错误是typing.Annotated的3.8导入与不存在的pytest节点，之后修正。公开所选1/1/8/11/1项及2个自写pytest测试通过，不支持“all existing tests/backward compatibility”。失败调试文件是交付缺陷，与正式四节点拒绝分别记录。 |
| 评分一致性 | install RC0、test RC1；两F2P均失败，原158P2P全通过，新增2P2P均失败，无参考缺席／skip。原F2P是多个子场景的同一节点，先前bool断言已执行，到WithUnsupported才失败；后续Replaced/Between/Both未执行，不能把0/1解释为bool修复失败或后续均失败。正式命令只跑`tests/test_validators.py`，全文件164 passed／4 failed包含6个非参考项；没有收集根目录调试脚本。原FP摘要`a54c75aa…`及全部8项投影保持，hygiene.clean不代表附带脚本正确。 |
| 公开要求与求解依据 | 首HTTP原题面块逐字节保持，私有patch／新增保护节点未进入HTTP正文，私有文件没有挂入actor。模型读PlainValidator源码和“instead of inner validation”的公开文档说明，却按AfterValidator的handler模式推断所有validator都应生成inner schema，修法判断不完整。既有重排／事后补挂正对照已通过CPU，不扩大多PlainValidator、自定义包装或可选WrapSerializer交叉场景为新评分要求。 |
| 环境与运行身份 | queue_v24／题级code_v8；actor与grader同`bc5d796f…`镜像，Python3.8.19/core2.15.0。actor UID54321激活、prelaunch及wheel读取通过；grader UID54322固定前置、editable／testing requirements安装和源码导入成功，保护／runner摘要一致。固定probe-wide-v1与whole/setup/apply/test3600/300/120/1800保持，没有准备或测试超时。baseline环境digest为null，不回填typed资格。 |
| 效率与并行 | 44生成HTTP/SSE均200，无count_tokens；43工具为10 Read、7 Write、24 Bash、2 Edit，全串行、无子agent，4次工具错误。累计输入1090100、输出7246、合计1097346；最大单请求输入39227。首HTTP到唯一生产编辑38.099秒，solve79.529秒，CC75.945秒及嵌套API64.276秒不相加。重复查读同一schema和多个临时脚本增加成本，之后没有利用这些验证暴露内层schema回归。 |
| 模型来源、资源与清理 | 派发前实测engine／adapter身份、只读固定Coder revision `b2cff646…`和HTTP服务关联获独立复核；两次inspect不作为作业结束后checkpoint证明，adapter的code_v4与题级code_v8分开。旧checkpoint flags保持，未重读权重或GPU内存哈希。26个有限资源采样按CID/run关联：actor7、relay7、grader17，其中grader1个PID0/资源null保留空值；安装3.629秒／测试2.785秒各0采样，缺口未知。report峰值653.457与外部采样分开。quiescence、drain active0、actor/relay/network及manager1建1删无本job残留，不声明全宿主空闲。 |

准备时已存在的pdm.lock／pyproject.toml差异属于458项真实baseline，并非FP改动。原分、原候选和失败调试文件保持；本轮只做本地读回，没有新CPU/GPU/模型调用。后续沿原请求排Qwen首次臂；已发现的候选缺陷不自动触发重采样、题外测试扩张或训练准入。
