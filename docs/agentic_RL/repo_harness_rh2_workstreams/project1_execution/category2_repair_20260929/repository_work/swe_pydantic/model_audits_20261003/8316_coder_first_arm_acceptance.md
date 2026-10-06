# 8316：Coder 首臂的目标修复与交付缺陷

2026-10-03。**目标源码修复有效，正式144项参考全通过；完整候选留下一个已知失败的临时测试文件，交付仍有缺陷。** 题主完整阅读262条原始轨迹的全部非重复文本、20次工具调用及返回，核收[独立执行复核](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/pydantic8316_coder_a1_execution_review_v1.md)。[题主读回](../coordination_20261003/8316_coder_first_arm_owner_readback_v1.json)绑定140件证据，包含已闭合133件原件、11,386,168字节，以及新增核收依据。Qwen首臂尚无原件，整请求继续claimed，没有ACK或成对完成。

`gpu1003-pydantic8316-coder-a1`在code_v8、原固定v3材料及CPU同一`f939c266…`镜像上实际安装RC0、测试RC0；1个F2P及143个P2P全部PASSED，无参考缺席或跳过。全文件pytest摘要159 passed／14 skipped的分母不同；14项skip不在正式144项参考中。原raw reward=1保留，评分事实与完整候选交付质量分别记录。

| 诊断方面 | 当前结论与证据范围 |
| --- | --- |
| 目标源码语义 | 模型增加`([A-Z]+)([A-Z][a-z])`缩写结束边界，再处理小写／数字到大写和字母到数字，整体小写化。正则扫描完整输入，没有示例硬编码、长度／次数上限或只修串首。原17个公开snake参数、原CAMELToSnake及现有v3的11个断言共29项纯函数重放全过；`to_camel`／`to_pascal` AST保持。当前约定范围未见生产源码回归。 |
| 完整候选与验证缺陷 | 原FP有源码、`tests/test_utils.py`和新增`test_fix_verification.py`三项。工具14实际运行新增脚本RC1：其`to_camel`模型生成别名`httpResponseCode`，脚本却期待原始`HTTPResponseCode`直接匹配。随后模型正确收窄到`to_snake`目标，但没有修正／删除失败脚本，最终说明也未披露遗留文件。不能称完整候选所有新增测试均通过。 |
| 评分一致性 | 原FP摘要`0d5d2829…`、451项baseline摘要`159f3843…`保持，逐项tar路径／类型／执行位／内容及actor→grader census核一致。正式投影剥离`tests/test_utils.py`修改，保留源码和根目录临时脚本；实际命令只测试`tests/test_utils.py`，没有收集失败脚本。`hygiene.clean/test_files_modified=false`描述投影，不能改称actor未修改测试。评分正确识别目标修复，同时没有覆盖这项交付文件缺陷。 |
| 公开要求与求解依据 | 首HTTP的一个文本块与原2650字节prompt逐字节一致，另有CC系统提醒；原private补丁及4个非公开标记未出现在21个HTTP body解码字符串中。模型从公开源码发现缩写边界并复现HTTPResponse，而非收到私有修订。题卡已规定`to_camel`附注为P4，不提升为另一个必修目标；不新增单字母缩写、非ASCII边界、kebab或大写字母–数字规则。临时脚本是模型自己添加的错误验证文件，与另加P4评分要求分开。 |
| 环境与运行身份 | actor UID54321、Python3.8.19、源码可写、激活与prelaunch通过；grader实际导入`/testbed/pydantic/__init__.py`、版本2.6.0a1、UID54322前置及真实安装测试成功。CPU同ID公开wheel身份采用既有固定证明关联，没有新GPU两UID安装矩阵。实际900秒准备政策精确匹配f939／本题／v3，whole3600、apply120、test1800不变。 |
| 效率与并行 | 21次HTTP/SSE均200，累计输入299694、输出4274、合计303968上报token；20工具为15 Bash、2 Read、2 Edit、1 Write，全串行，无子agent。首次HTTP到生产编辑完成10.745秒，入口solve45.311秒；CC报告41.770秒、嵌套API33.897秒，不相加。读取完整680行公开测试后下一请求输入由5027升至13142；结束前读取含既有依赖差异的git diff，最后请求输入再升至25953。两次工具错误分别是pytest `-k`语法和失败临时脚本；前者修正，后者未清理。 |
| 模型来源、资源与清理 | 运行前后engine／adapter实际身份、固定只读Coder revision `b2cff646…`及服务HTTP／配置关联已获独立执行复核；不把原checkpoint_verified=false等flag回填，也未重复哈希71GB权重或证明显存字节。21个有限外部采样按实际CID／run ID／时间关联：actor5、relay5、grader14；短安装2.057秒和测试1.710秒各0采样点，缺口未知。report峰值655.422MiB与外部采样分别保存。actor／relay／网络清理无残留、gateway revoked/drained/active0、manager创建1删除1且open/supply/failures为空；终态只证明本臂entry0，不声明在途队列或全宿主PID0。 |

`pdm.lock`和`pyproject.toml`的依赖差异在solver启动前已存在，属于451项真实baseline；本次FP没有它们，不能把末尾git diff中这些差异归因给模型。新增临时文件未被该`git diff`展示，但完整FP已捕获，审查以完整FP为准。

本轮核收不修改模型原件、不把临时脚本静默删除，也不为这一已知问题增加CPU矩阵或模型样本。正式分数保留；候选交付缺陷另记，训练／留出资格未授予。下一步由GPU线程沿原请求排Qwen首次臂，题主继续核完整轨迹、候选、逐参考评分和效率；首臂不足以估计稳定成功率或比较模型。
