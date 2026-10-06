# EA69 R17 Coder 首臂：题主七维分析

2026-10-03。**现行49键全部通过，原reward1保留；正常用户两行内容和两次生成后的真实Git检查通过，但候选未完整保留任意用户内容，不能称全面语义正确。** 新版Qwen尚无回执，R17请求继续claimed，不与旧公开缺项的Qwen配对，也未ACK、重评分或追加采样。

作业`gpu1003-coverageea69-r17-coder-a1`，材料R17/073–075+093。完整参数、29个有效工具调用与返回、原件引用及实际身份见[JSON](model_analysis_coder_r17_a1_20261003.json)；[非作者语义核查](../../reviews/non_author_ea69_r17_coder_semantic_review_20261003.md)另审候选。题主本轮只读原件和派生记录，无CPU项目运行、SSH、Docker、模型或重评分。原分析、原FP和评分均保留。

## ① 修法、目标与缺口

原HTML生成路径没有写`.gitignore`。候选新增`HtmlReporter._create_gitignore`，在报告的index/status、静态文件及extra_css复制后调用。集合覆盖五个静态文件、index、status和extra_css basename，另加`*.html`覆盖按`flat_rootname`生成的页面；每次生成都会执行。原无数据异常先于此调用，无数据不创建目录的路径保留。

现行preserve测试原内容是`# User-owned rules\ncustom.tmp\n`，两轮均检查原字节串仍在且真实Git不枚举报告产物；这一范围有实际通过证据。实现却把已有文件读为文本、splitlines、过滤空白行和等于生成文件名的行，再用w重写。源码直接可见它会删除用户空行、归一化换行、移动同名规则；不是对任意用户内容的完整保留。`*.html`不属于过滤集合，每轮再加一次，重复生成会累积。这些不是环境或预算失败，也不能用49/49抹去。

extra_css是配置文件名的basename，候选直接把它当Git模式写入，没有转义。`!custom.css`、`#custom.css`等合法文件名可能变成反向规则或注释，无法确保该生成CSS被忽略；这是根据配置复制路径和Git模式的静态风险推导，本轮没有真实运行这些边界。现行正常extra.css与preserve fixture不覆盖它。原题写“all its contents”；现行测试核对报告产物，明确排除`.gitignore`本身，没有验证任意额外文件。这里保留这项覆盖范围，不把测试范围等同于完整公开目标。

当前结论分三层：原评分49/49正确记录现行参考键；常规创建/保留/再次生成场景实际通过；广义公开preserve和特殊文件名边界仍有候选缺口及疑似覆盖盲区。未改公共评分，不把单候选缺口直接改成整题不可运行。后续定向验收应比较普通内容、空行/CRLF/已含静态规则/无末尾换行，以及特殊extra_css的真实Git状态，再决定是否补材料；未完成前不授全面正确或训练资格。

## ② 定位与纠错

L23完整读html实现，L36读完整公开HTML测试；首生成请求后1.851秒已取得实现，再用解释器路径确认从工作树导入。L58正确指出缺少创建路径和preserve目标，L62挂调用，L75一次写出方法，约15.341秒后模型已发完生产改动；此后没有生产修正。

L140临时脚本用exec字符串收集不到数据，L149实际rc1；改导入并调用函数后L171成功。L210的preserve脚本把已有`.gitignore`建在临时根目录，输出却在htmlcov，L219实际断言失败。这不是正确输出目录的反例。模型识别目录不一致后，L232只打印新文件，既没有在htmlcov预置内容，也没有重跑修正后的保留/再次生成场景，随后却宣称已验证保留，证据不足。

L284的verify脚本要求动态页面文件名直接出现，L293因`helper2_py.html`不在文本中失败；L306改成静态名和`*.html`子串，L315成功。用模式替代逐文件名可符合题目，本次调整不自动判作弊；然而只检查字符串仍不能证明Git的真实效果。以上行号为原JSONL一基行号，时间为推理/工具/运输合计到达时间，不是纯思考时长。

## ③ 工具使用与交付

29个工具为Bash19、Read3、Edit4、Write3；3个is_error均为上述自测失败，无工具超时。find包含.venv，无需扫描整个环境来定位已有明确模块。整html.py及1121行公开测试读回扩大后续重复上下文；结束两段长总结重复，而且比实际验证更强。

临时`test_gitignore.py`、`test_existing_gitignore.py`、`verify_fix.py`均被模型删除；临时数据/报告放在TemporaryDirectory并收尾。原FrozenPatch只有`coverage/html.py`一项19622字节；公开tests、runner、conftest没有改动，没有根数据库或调试产物进入FP。原基线install.sh/run_tests.sh是既有未跟踪文件，不能记作模型新增污染。排除路径集变化为缓存等观测事实，未据此虚称完整环境未变。

## ④ 并行机会与执行支持

每个模型助手消息最多一个工具调用；独立源码和测试读取可合并，生产Edit及后继测试依赖须顺序。pytest默认启动gw0/1/2属于项目xdist，并非模型多工具并行，不能推断模型并行能力或节时效果。独立回归具备合并命令机会；测试共享工作目录及coverage数据，不能机械并发。没有本题并行支持实测或对照。

## ⑤ 验证质量与原评分

开发验证为HTML单项1、另一单项1、选择5、Delta7、HtmlTest10、完整HTML46的重叠序列；末尾test_report另3，通过覆盖范围为49个公开测试的并集，不能把重复次数相加成独立项，也不是全仓回归。最后两次用了qq抑制摘要，46/3依据点数、源码方法及完整返回判断，不伪称这些返回带正式footer。原公开helper只接收filename/mode；候选未传encoding，原helper直接运行可用，中性兼容brief未改HTML断言或提供私有答案。

三个自测脚本在临时目录跑真实报告，但没有Git调用、修正后的已有内容测试、再次生成检查。新脚本的错误预期被调整，原公开tests没有削弱；正式评分独立还原保护评分树，只应用原FP唯一生产项。现行expected与实际49键相等，参考skip/missing/unexpected均0，正式testRC0、完整`49 passed in 1.27s`。保留原正式1，不把失败开发自测当infra，不把正式通过扩展为所有输入正确。

## ⑥ 完成效率与消耗

| 口径 | Coder实际值 |
| --- | --- |
| 累计输入／输出token | 800415／6971 |
| cache read／creation | 0／0 |
| 生成HTTP／count_tokens | 30／1 |
| CC回合／工具 | 30／29 |
| solve／CC wall／CC API秒 | 72.704／69.149／60.668 |
| gateway生成响应累计秒 | 59.993 |
| actor开始至清理收口秒 | 135.291 |
| actor trusted init／Git sanitize秒 | 39.532／2.733 |
| grader总计／报告测试／测试段标记秒 | 45.223／1.980／1.794 |
| grader container_peak_memory_mb | 347.699 |

输入峰值33583、单响应输出峰值914；累计输入重复包含上下文，不是新信息量。30次实际max_tokens均65536；CC modelUsage元数据32000不替代实际网关上限。CC非API残差8.481秒不是纯工具时间，gateway累计包含adapter/运输，不是纯GPU推理。CC别名估价4.176350USD，实际账单未知。

14份有限宿主切片含相邻题与relay，已只选本题actor名称：8个actor切片的所见memory.peak最大1152385024字节、pids.peak23，所见OOM为0；3个grader切片memory.peak仅134008832字节，与正式grader峰值347.699MB的来源/采样范围不同，不能替代后者。未采间隙未知，共用GPU读数不归因本题，也不据短样本宣称196K上下文峰值已实测。

## ⑦ 结束、实际条件与接续

completed、CC success/end_turn、harness0，无截断/partial/timeout；install明确SKIPPED、RCnull，不能写安装成功0。actor容器/relay/网络、gateway revoked/drained/active0、静止屏障以及grader created1/removed1/open0均核。闭包506文件/48,458,118字节逐SHA/bytes一致；原FP canonical digest591da512…、基线7d9fea8…一致，360个tar基线文件逐内容SHA通过。评分为原FP运输，审阅diff不是替代候选。

实际GPUactor/grader镜像e23fbbed…、base7fd1ea39925f0856ff607bb30796bc948a8c829d、配方85b488e5…、公开bundle53deb1de…、delivered prompt19aa60c7…；首网关请求精确含新版题面和未改brief。CPU镜像9877b37…保留其原身份，不改写成GPU实值。actor/grader代码为code8，实际Coder adapter仍code4，gateway为services27、adapter证据services14；不称所有运行树同版。

实际模型Qwen3-Coder-30B-A3B-Instruct，revision b2cff646eb4bb1d68355c01b18ae02e7cf42d120，BF16/TP1、reasoning_parser null，采样0.7/0.8/top_k20/repetition1.05。CC请求adaptive/high是wire字段，不据此声称Coder开启Qwen3.6思考。预算probe-wide-v1：196608 context、65536输出、240回合、10800秒、1024请求、first_byte1800秒、adapter_idle14400秒，grader whole3600/setup300/apply120/test1800秒。启动绑定、实际配置/只读挂载/25文件大小及HTTP读回匹配；未重复哈权重文件或GPU显存逐字验证，gateway checkpoint_identity_verified=false保留。code_snapshot_id、grading_materials_identity及qualification仍缺，不补造。

R17新Qwen待回传，故不能判同条件双模型稳定性或配对完成；旧公开缺项Qwen原0/48-of49只属旧版。原活动请求继续claimed，等待新版缺首臂，普通追加a2/a3仍按统一GPU覆盖优先暂缓，本轮没有新probe。候选保留/模式边界只作可追溯的质量和验收余项，现行原分不回写；后续CPU定向验证及可能材料修订另记版本，所有历史尝试保留。
