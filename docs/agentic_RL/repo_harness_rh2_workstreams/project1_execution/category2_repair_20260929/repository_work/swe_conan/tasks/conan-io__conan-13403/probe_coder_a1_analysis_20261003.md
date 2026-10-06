# Conan13403：Coder 首次探针分析

2026-10-03。请求 `swe-conan13403-r12-briefv1-20261003-v1`，作业 `gpu1003-conan13403-coder-a1`，模型 `Qwen/Qwen3-Coder-30B-A3B-Instruct`；实际code8、R12、brief v1、`probe-wide-v1`。

**raw1，当前1F／0P的唯一可信参考完整通过。题主源码核查支持新增所选目录参数、原args／单次调用／异常与cwd恢复语义；参考内部是多分支受控调用记录，不等于真实GNU构建成功。模型自测只构造Autotools对象，未调用autoreconf；两个真实功能试验失败，最终相对路径示例亦被说成build相对。验证与说明问题单独记录，Qwen首次仍缺，请求保持活动。**

## 原件与评分范围

[固定请求](probe_request_20261003_r12_v1.json) SHA `bf8eb0004261dc97ebc7a0959b77e3c1b94c4b86a8d58a89469a23c3e4c2dacb`未改。题主核138件、12,567,859字节闭合原件SHA／大小；原件根 `runs/ordinary_gpu_probe_20261002/remote/queue_v23/results/gpu1003-conan13403-coder-a1/`，清单 `runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-conan13403-coder-a1_closed_manifest_v1.json`。完整原issue和brief v1在实际首gateway请求按原字节交付，保留CRLF，仅去brief末尾换行；prompt SHA `88c598cd67a46643a39399f3460244f1bfc91ab15b9f066d34dfb32b3cfb1850`。

完整diff 4,042字节，SHA `a1dd6f69d494906ee9221a8f592f08ac172c3c6c67c557b042026b8acef25814`，两项为生产`conan/tools/gnu/autotools.py`及新增64行`test_autoreconf_fix.py`。题主从实际baseline取生产原字节、核公开base并隔离应用完整diff，结果逐字节等于两份Frozen内容。**两项均实际投影**；脚本未被清洗掉，但固定pytest只收可信`autotools_test.py`，不执行这个脚本。模型在过程中改过公开测试，最后完全恢复；不能据最终未改测试忽略过程，也不按新增test-like脚本自动判作弊。

FP canonical digest `4e88d1e2ed520dffd01397e3534ec05c008c00d098b49a0a6836c6913328df97`，baseline canonical digest `025760d35c701c25f189a4303579d2e2b337d11c1af63855112075d899859077`。唯一完整key `conans/test/unittests/tools/gnu/autotools_test.py::test_source_folder_works`为PASS，无missing／skip，安装0／测试0及完整1 passed尾部；eval SHA `f3ffb739f0961de00f8fd946c3b3da40b38963da3b41e8b1b822b0892f386b62`。一个key内部核多次默认／相对／绝对路径、参数、只调用一次、错误传出和cwd恢复，不将其内部calls另计多个评分节点。

实际actor／grader为固定GNU镜像 `b40849e11f0b85cc14a243ede47148c2b9bd7f49a8898640879ad724dd7ff4ff`，UID54322 prerequisite实际verified／exit0。[执行独立报告](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/conan13403_coder_a1_execution_review_v1.json)按原件、安装／测试、完整baseline、身份／运输、两层清理和gateway drain范围复用，不授候选语义或训练资格。[部分回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/receipts/swe-conan13403-r12-briefv1-20261003-v1_partial_coder_a1_v1.json) SHA `ab1d5b4975346eac84c04013ab41821a296418ffe1149db9e621ca74a7c3fd58`只收Coder执行；其`not_sent=true`旧字段保持，实际消息已交题主，不能因此改写原件或核销整项。

完整SHA／指标与工具原文见私有目录 `runs/category2_repair_20260929/conan_cpu_20261003/probe_analysis_13403_coder_a1_20261003_v1/owner_readback.json`／`tool_events.json`；下文行号指原 `attempt/trajectory.jsonl` 一基行号。

## 七个维度

### 方法

生产加`autoreconf(self, args=None, build_script_folder=None)`，保留args第一个位置参数。非空folder用`os.path.join(source_folder, folder)`，省略／None／空串仍source；绝对folder按join行为选择绝对目录，与已有configure的路径逻辑一致。run命令仍拼原默认`_autoreconf_args`和额外args，在原`chdir()`内调用一次。公共context manager的`finally`恢复调用者实际cwd，异常不吞掉；不改recipe的source／build属性。

题面允许指定configure.ac所在位置，不要求默认改为caller cwd。传绝对`conanfile.build_folder`即可选择build；caller已经chdir(build)再给相对`some/subfolder`仍解析source下目录。模型最终行275／288示例的“会在build找”不准确；是说明P2，不据此新增与既有configure相冲突的参数语义。没有测试识别、评分绕过或扩大原要求。

### 定位

工具1找到GNU实现，工具2读对生产源码，工具3读旧公开测试。首次相关源码读取距第一模型请求 **1.403秒**；行45正确定位source目录硬编码和configure对照，对应第四响应完成 **2.901秒**，是3工具后的完成上界，不是最早生成判断的精确时刻。再读用例后行75一次生产编辑即成为最终实现，后续没有生产回退。

没有在修改前实际调用新目录复现；读取旧实现与既有公开用例是定位依据。后续两个functional使用默认参数，不是原issue所选build目录的前后复现。

### 工具与纠错

22次工具：**Bash12、Read4、Edit5、Write1**；其中生产Edit1、公开测试Edit4。原`is_error=true`有5次：行118／170／183为自己新增例缺真实目录及不合适的错误断言，行235／248为GNU功能试验失败。未用shell掩盖。

行101新例指向不存在`/path/to/sources`，默认调用先失败，未到新参数；行140改成简化默认调用，行153又换成signature例，用不存在`./some/subfolder`调用，捕获异常后错误地要求文本含“argument”等字眼。行170及更广目录行183仍失败。行192删掉的是自己新增失败例，恢复原公开模块字节，没删原回归或修改生产来吞错；但也放弃了新增参数的有效自测。

最终独立脚本在临时cwd生成toolchain配置、构造对象并打印默认／新参数成功，**没有一次`autoreconf()`调用，也没有签名检查或行为断言**。即使旧API也能打印这些成功句；行270退出0仅证明脚本执行。它含捕获异常与总成功文字，并将cwd留在退出后被删除的TemporaryDirectory内，不能当新参数、目录、run或恢复的验证器。本次独立进程随即结束，正式grader未执行它；脚本作为原候选保留，正式评分依据来自独立可信参考。

### 并行

23响应前22各一个工具、最后结束，实际无重叠。生产读完后，公开unit与functional用例可独立只读；本次串行，CC／adapter多工具并发支持未独立建立，能力不可判断。新增例修改、失败分析、恢复旧测试与其后的pytest有顺序依赖；Conan工作树／缓存及测试自身cwd操作共用，不直接列这些测试为安全并行机会。

### 验证

| 轨迹行 | 实际结果与范围 |
| --- | --- |
| 88→92 | 改后原公开configure例1P、0.16秒；不调用新autoreconf功能 |
| 114→118、166→170、179→183 | 新例分别1F／1P、1F／1P、1F／78P；目录不存在／错误消息断言，GNU目录输出曾截断，但完整footer存在 |
| 192、205→209、218→222 | 删除自己的新例后，原unit1P、0.09秒；GNUunit目录78P、0.16秒，同一例有重叠，非全仓回归 |
| 231→235 | option_checking到build→autoreconf --force --install；automake因LIBTOOL未定义退出1，测试1F、1.87秒 |
| 244→248 | arguments_override到autoreconf --verbose --install、aclocal／autoconf／automake；同类错误退出1，测试1F、1.83秒 |
| 266→270 | 两次对象构造及成功打印，未调用autoreconf，非新接口／行为测试 |
| 279→283 | 最后git diff核生产改动，完整候选另包含未跟踪的新脚本 |
| 可信grader | 当前唯一1F参考完整PASS，内部受控calls独立核所选目录、args、次数、异常／cwd；零P2P范围保持 |

两个functional日志完整可见`Libtool library used but 'LIBTOOL' is undefined`及LT_INIT/aclocal建议，不是“缺autoreconf”。真实GNU链路可达，但构建未完成，且两者都调用默认路径；新增folder没有真实GNU成功运行。模型称失败与改动无关，当前原件没有基线对照来独立证明该归因，也未确定准确缺失包／宏配置。默认路径源码未改变是有限静态依据，不把失败改写成通过或当前评分误拒。

最终“所有既有unit通过”仅在GNU目录78例内成立；“新参数 works／完全解决”不能由该自测支持，生产语义另由源码与可信受控参考核。受控参考不是一次完整GNU端到端，旧21候选矩阵和旧实际actor证据不在本轮重跑。

### 效率

求解 **64.881秒**，harness61.962秒；CC61.334秒／API53.839秒，差7.495秒不是纯工具时间。23回合累计输入 **421,855**／输出 **6,668 tokens**，最大单输入34,238；gateway、adapter和CC一致。根因定位快、生产改动一次完成；三个失败验证和四次测试编辑未得到有效新例，最后假阳性脚本及重复总结可减少。观察仅适用本次，不作一般能力排名。

Git清理14.667秒、可信初始化8.151秒等准备单列；评分总91.158秒、reset15.322秒／prep0.333秒／测试2.025秒／队列0秒，不混入求解。23实际gateway输出预算均65536，CC32000只是元数据。196608上下文／240回合／3小时未触及，不能证明极限容量。CC费用2.275975美元是自动估算，非GPU账单。

### 结束与稳定性

`completed/success/end_turn`、harness0，23gateway响应HTTP200且无stream error、截断／拒绝。actor／grader收尾及gateway revoked／drained／active0已核，只证明本job终态。15个有限资源切片按实际角色：actor／relay各7、grader6，安装／测试窗口0样本；未知间隙与测试内存不写零，也不把host GPU内存当项目测试配额。仅一次Coder，Qwen3.6首次与整项回执尚缺，不下稳定性或训练资格结论。

## 处置

题主已全文核收[非作者语义窄核](../../reviews/non_author_13403_coder_a1_semantic_review_20261003.md)，SHA `32e013c1dd45dc40afccbfed27188a54fb4a1e44b396f47f4f2138972c284352`。完整候选、当前唯一参考和轨迹范围未发现P0／P1候选或材料阻断。删除原测试的嫌疑为`rejected_with_evidence`：四次Edit最后精确恢复原公开模块，只删本轮自己新增的失败case。

逐项采纳两项P2：① 自测无autoreconf调用、GNU真实功能失败及最终披露不足；② 将source相对参数误说为build相对。处置均为`no_fix_accept_residual_risk`：如实收窄验证／示例结论，保留冻结候选，不为这两项新增实验或材料修订。正确选择build根应传绝对`self.build_folder`，build子目录应传绝对`os.path.join(self.build_folder, "some/subfolder")`。不据raw1自动核销问题，也不为使错误注释成立而改变生产路径契约。

保持claimed、不ACK／不清活动指针，等待Qwen首次和整项回执，覆盖优先暂缓普通追加采样；当前本题无CPU作业，未来具体修订再核资源需求。实际首臂使用登记的同一GNU镜像ID已核，不据此宣称两镜像archive供应全量收口；训练资格尚未建立。
