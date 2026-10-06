# 5662：新Coder候选与版本明确的首轮核收

2026-10-03。**新Coder只改变非BaseModel相等比较的返回值，当前范围未见具体语义回归；实际安装／测试RC0，129正式参考全部通过。** 题主完整阅读191条轨迹的全部非重复文本及15次工具返回，核收[独立执行复核](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/pydantic5662_coder_a1_execution_review_v1.md)、[版本明确的双候选回执](../../../../../../../../runs/ordinary_gpu_probe_20261002/receipts/swe-pydantic5662-behavior-v1-20261003_versioned_two_model_v1.json)及[137件绑定读回](../coordination_20261003/5662_coder_versioned_two_model_owner_readback_v1.json)。原Qwen候选的完整轨迹审阅和权限修复后原FP评分沿用已有核收，没有新Qwen样本。两臂求解环境不同，本次交接收口不代表同条件模型比较、稳定成功率或训练资格。

| 诊断方面 | 当前结论与范围 |
| --- | --- |
| 源码语义 | `pydantic/main.py`唯一生产变更是非BaseModel分支的`False`改为`NotImplemented`，让Python比较协议尝试对方的相等判断。其余类型、泛型、字段和私有属性相等逻辑逐字保持；没有特判ANY、对象名或把结果改为总真。当前公开问题范围修复有效。 |
| 实际环境 | code_v8与实际37260470… actor/grader，agent UID54321、Python3.8.19、公开源码可写且环境前缀不可写，激活检查通过。grader实际离线安装Pydantic2.0a3/core0.27.0成功；安装RC0、测试RC0，原setup300、whole3600/apply120/test1800不变。baseline环境身份字段null及candidate prerequisite=null保留，不冒作完整训练环境lineage。 |
| 评分和完整交付 | 2F2P＋127P2P逐键全PASSED，无正式参考缺席或跳过；全文件143 passed／26 skipped另列。FP五项全部进入评分投影：一份生产源码、三个根目录验证脚本、一个Hypothesis Unicode缓存。四个作者修改文件均从成功Write/Edit逐条重建并与FP相符；缓存摘要、gzip和JSON可读性通过。三个脚本实际通过，无8316／6283那类已知失败附带脚本，但仍保留附加文件而未清理。正式命令只收集`tests/test_main.py`，不把附带脚本视为正式参考。 |
| 公开问题与定位 | 首HTTP包含逐字原prepared prompt，SHA efb9c73f…与旧Qwen相同，无额外brief或私有补丁。题面明确给出`return NotImplemented`修法；模型读完整1083行main.py，先复现ANY断言失败，再按提示修复。能证明理解、实施和验证公开修法，不能证明无提示独立发现根因。 |
| 验证质量 | 模型真实运行原复现、一般自定义相等对象、非BaseModel直接返回NotImplemented、普通模型相等／不等及三个新脚本。`pytest tests/ -k test_eq`只选中颜色测试，单独这个检查与目标问题关系弱；随后完整公开test_main真实141 passed／26 skipped，正式私有评分再验证新增一般matcher及旧127保护。模型声称无性能影响、无副作用，没有benchmark或全项目验证支撑，结论只限已审范围。 |
| 效率与并行 | 16生成请求和16组完整SSE均200，另一次`count_tokens` HTTP，不算新模型轮。累计输入331422、输出3463、合计334885上报token；2 Read、3 Write、8 Bash、2 Edit共15工具，全串行、无子agent。入口solve39.450秒；CC35.857秒、嵌套API29.215秒不相加；首次HTTP到生产编辑完成7.078秒。整文件读取后下一请求输入4396→18235，后续验证和总结增长至26176。两次工具错误是修复前预期断言失败，以及总结后一次新旧文本完全相同的无效Edit；后者没有改变源码，增加了检查轮次。CC成本字段是CLI计量信息，不是GPU账单。 |
| 身份、运输与清理 | 执行前后固定只读Coder服务的engine／adapter身份、revision及实际HTTP配置关联获独立执行核查，未重新哈希全部权重或证明显存字节。新闭合128件共8,564,737字节逐SHA／尺寸一致；288项baseline tar逐路径／类型／执行位／内容及actor→grader census一致，FP摘要5395e129…、baseline1bfd37e6…保持。19个有限采样按实际CID／窗口分列actor5、relay5、grader12；安装2.026秒、测试1.257秒各0采样，间隙未知，report峰值534.027MiB单列。actor／relay／网络清理无残留、gatewaydrained/revoked/active0，manager1建1删且无open/supply/failures，单job终态exit0；没有独立全宿主PID0／网络原始读回，不从旧dispatcher PID推断。 |

原Qwen[完整候选初审](5662_qwen36_a1_preliminary.md)和[原FP补评分核收](5662_original_fp_regrade_acceptance.md)继续有效：旧425a…/code_v4求解时安装RC1、raw1保持；同一原FP f1423fd9…及baseline6e536f26…后来只在37260470… grader完整安装／评分，129参考全过、raw1。新Coder在37260470…/code_v8求解，baseline和累计输入也不同，不能把30.606与39.450秒或两个raw1解释为能力／效率优劣。旧Qwen来源仍为有限运营谱系补证，不回写成当时逐job checkpoint快照；旧重评缺grader采样和关闭后网络原件继续保持未知。

当前修订通过CPU正负对照拒绝ANY特判漏奖，并接受两个原始候选的一般比较委托；没有发现需要新增评分要求或再跑CPU的具体缺口。可关闭本次版本明确的首轮交接，保留两个完整候选与条件差异。题面强提示、一行修法及单次通过说明本题对独立定位难度的诊断作用有限；当前用途仍是普通基座题目质量诊断。后续重复按总协调覆盖门槛另排，不能自动进入训练或留出集。
