# Conan13403：Qwen3.6 首次探针分析

2026-10-03。请求 `swe-conan13403-r12-briefv1-20261003-v1`，作业 `gpu1003-conan13403-qwen36-a1`；code8／R12、brief v1、`probe-wide-v1`，本模型仅一次。

**raw1，1F／0P唯一完整可信参考通过。生产修法增加所选目录参数，保留默认、命令参数、单次调用、异常传播与原cwd恢复。** 模型新增公开测试实际调用helper，但mock了chdir和底层run；79个GNU单测通过不能扩大成真实GNU构建成功。生产、验证质量与评分运输分别记录。

## 原件与评分范围

[固定请求](probe_request_20261003_r12_v1.json) SHA `bf8eb0004261dc97ebc7a0959b77e3c1b94c4b86a8d58a89469a23c3e4c2dacb`未改。权威原件根为 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/`，实际结果目录为`queue_qwen_next12_v1/results/gpu1003-conan13403-qwen36-a1/`。题主逐件核160件／14,472,896字节SHA／大小；完整diff3,687字节，SHA `c3aa89a94e8b40a614a420739d4f04b6c0f3a0b451c4d1f6c47441dee9f3f9ea`。完整候选两项modify／100644：生产`autotools.py`及原公开官方单测模块；旧公开模块原字节完整保留，只追加48行新测试。隔离应用完整diff等于Frozen全部内容，没有删除旧例或读私有材料。

完整Frozen canonical digest `8d9fb7fd1bb2d55907d473e392e93ce5d004eacdf6fcc033cb6bff32c5915f79`；完整baseline canonical digest `025760d35c701c25f189a4303579d2e2b337d11c1af63855112075d899859077`。正式投影只含生产文件；受保护官方单测从固定base恢复并应用当前云端v4，模型新单测不进入正式评分。安装0／测试0；完整原日志唯一nodeid `conans/test/unittests/tools/gnu/autotools_test.py::test_source_folder_works`为PASSED，尾部1 passed、无参考skip／missing，eval SHA `d28ac963eb33e810397b8f34a1f9a0ec3b4e152c441c3a564a7f4a7da8909569`。

这个完整参考内部含默认、source相对子目录、绝对build路径、args、重复调用、缺目录、正常／异常cwd恢复等分支。底层为_run recorder，不执行GNU；不是只有一项路径断言，也不是一次GNU端到端。当前材料、旧正式21候选矩阵与此前GNU诊断保持，不重跑或回写历史reward。

实际actor／grader为固定GNU config ID `b40849e11f0b85cc14a243ede47148c2b9bd7f49a8898640879ad724dd7ff4ff`。首gateway请求含原issue全文与完整brief v1，prompt2,711字节、SHA `88c598cd67a46643a39399f3460244f1bfc91ab15b9f066d34dfb32b3cfb1850`；brief SHA `4deeac2d97519ad9c0dfd9d2e0ba15bb6b034e0a5736d96cf2e86bfa0f1b37c5`。保留issue CRLF、brief末尾换行处理。模型自查实际源码导入和GNU工具版本，有真实原件，不仅是配置声明。

[本臂机械回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/conan13403_qwen36_execution_receipt_v2/execution_receipt.json) SHA `200a7ebcf61c9647dac5af5e5c72e0cd51affca2d7ef8dec7767e34304a8beca`；[双模型回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/swe-conan13403-r12-briefv1-20261003-v1_pair_execution_receipt_v1.json) SHA `da11eb09698c9ab49a97930189e5954c63d94a6041ee1171295bf8f2bea601a9`。回执角色字段不代替题主语义核收。私有SHA与完整工具原文见 `runs/category2_repair_20260929/conan_cpu_20261003/probe_analysis_13403_qwen36_a1_20261003_v1/`；下文为trajectory一基行。

## 七个维度

### 方法

行140唯一生产Edit增加`autoreconf(self, args=None, build_script_folder=None)`，复制既有configure的source相对／绝对路径选择。None或空串仍取source_folder，非空相对值join source，绝对路径由os.path.join保留。原`_autoreconf_args`与`cmd_args_to_string(args)`不变，`with chdir(self, script_folder)`内仍只调用一次run。未捕获错误、没有改source/build属性、没有添加ignore_errors或改返回值。

原chdir在try/finally恢复调用者cwd；不存在目录进入前失败、不偷偷退回别处。build目录应传绝对`self.build_folder`；`"src"`表示source相对而不是build相对。Qwen最终文档及示例按source相对表述，没有移植Coder的错误示例。完整生产字节与Coder不同：文档措辞及command／script_folder计算顺序不同，当前公开语义相同，不宣称任意非标准类型等价。

### 定位

首响应同批工具核源码导入与GNU版本，随后读GNU导出和生产，相关完整源码读取距首请求 **2.675秒**。改前运行原公开configure单测1P，只验证原行为，没有复现新增folder参数失败；再读toolchain及100行功能例，行136定位configure对照与source硬编码，对应第9响应完成 **10.215秒**，9工具后行140实施。该时间为响应完成上界，不是最早生成诊断的精确时刻。

### 工具与纠错

26工具为**Bash12、Read8、Edit6**；1次生产编辑、5次公开测试编辑。初版新增测试使用不存在的`last_folder`且造了`/path/to/sources`假目录，没先核mock；尚未运行便查mock后改成局部chdir记录，但默认分支仍未mock。行240实测FileNotFound，随后全分支mock；行272因从unittest.mock导入contextmanager而ImportError；修导入后行300是错误尾部空格预期，最后用strip比较正确原command。

三次显式失败均完整保存；改动只修本轮新增测试，生产保持正确，旧公开测试原字节未动。最终mock调用helper并记录选择目录和参数，与Coder仅构造对象的脚本不同；但它不执行os.chdir或GNU，也不核异常／真实cwd。纠错暴露mock与导入知识不足，不能因最后2P抹掉三个错误。

### 并行

26实际gateway／adapter请求、CC27回合、26工具；首响应含两个独立Bash工具，其后每响应一个工具，最后end_turn。首批原件只证明批量交付，工具结果时间不能证明执行重叠。工具版本与源码导入可独立核，后续只读代码亦有批量机会；生产编辑和新增测试迭代有先后依赖，pytest涉及同工作树及进程cwd，不从批量数推并行加速。

### 验证

| 轨迹行 | 实际结果与范围 |
| --- | --- |
| 23／24 | 当前工作树Python／conan导入；Autoconf2.71、Automake1.16.5、M41.4.18版本，未实际autoreconf项目 |
| 70 | 改前原公开configure单测1P；head管道仍保留完整footer，不是新增参数复现 |
| 240／272／300 | 三次各1P1F：假目录、contextmanager导入、尾部空格预期错误；无成功新增folder调用证据 |
| 328 | 2P：原公开configure例加本轮mock新例；默认、相对folder、args＋folder实际调用helper，非真实chdir／GNU |
| 364／378 | head只见79 collected与前段PASS；随后独立tail运行保留79 passed footer，为78旧例＋1新例，两个运行不算158独立通过；均没保存pytest自身退出码，管道尾命令成功不独自作完成证明 |
| 可信grader | 固定唯一完整参考1F全过；真实目录切换／调用记录／异常及cwd恢复，底层run为受控记录器，非GNU进程 |

最终“79 GNU unit tests pass”与tail原件一致，是当前目录的单测范围，没有功能构建成功声称。功能测试只读100行、从未运行，不套用Coder本臂两个GNU失败。最终未明确mock边界和先前三次纠错失败；本页补齐。新公开测试没有绝对路径、缺目录、异常或实际cwd断言；这些当前由独立可信参考覆盖。没有证据支持真实GNU运行或完整仓库回归通过。

### 效率

求解 **57.368秒**，harness54.158秒；CC53.446／API50.061秒，残差3.385秒不是纯工具时间。26请求累计输入 **408,214**／输出 **8,058 tokens**，最大单输入29,550；gateway、adapter、CC一致。生产一次完成；新增测试五次修改、三次失败和同GNU单测重复执行占额外工作。读mock和chdir契约后设计记录器可减少可预见纠错。

Git15.423秒、可信初始化6.689秒、网络1.366秒等准备单列；评分81.374秒，reset15.339／prep0.277／test2.069，排队0。CC费用2.242520美元为估算，不是GPU账单。实际26请求输出限65536、CC32000为display元数据；196608上下文、240回合、3小时预算未触及，不推出极限容量或稳定效率优势。

### 结束与稳定性

completed／success／end_turn、harness0；26HTTP均200、无stream error，没有截断／拒绝。SSE／CC共63 content block，62完全相等，唯一Edit参数由CC补replace_all:false，与schema缺省相同；usage／工具内容逐项对齐。退出、PID1 journal、actor／grader清理与gateway revoked／drained／active0按当前原件及独审核收，不以not-found和默认0代替实际成功。资源14个时间切片、actor／relay／grader各6个对象样本，间隙仍未知，不能证明连续峰值或完整配额；权重未重新全量hash及训练资格未知保留。

两模型各首次一次均raw1；两者生产路径语义成立，验证质量不同。本题两臂实际均code8，记录的source manifest字节相同；不同模型transport／profile并不相同。不能把其它Conan配对的code7→code8差异套到本题，也不能用两次raw1建立稳定胜率、训练／留出资格。

## 处置

题主已全文核收[非作者语义报告](../../reviews/non_author_13403_qwen36_a1_semantic_review_20261003.md) SHA `3e4a1ea6d06784a6a486e83f2ed2de060eac825cadb57d28f0e625f5ca347645`及[执行报告](../../reviews/non_author_13403_qwen36_a1_execution_review_20261003.md) SHA `a098ccff474fcdb2f7f2261b7591950cd2184cca111059126f4d1c54a3d49599`。当前无候选或材料具体阻断；采纳F13403Q-1 P2，处置为`no_fix_accept_residual_risk`：保留真实79P footer，同时披露管道不保存pytest自身退出码、mock与无GNU工程运行范围，不改冻结历史或新增实验。三个已纠正新测试错误不作为未修生产finding重复计算。原reward、完整候选及旧Coder失败／错误示例结论均保留；无需材料修订、重分或新CPU／GPU／模型样本。核总回执后先ACK再清活动指针；当前[配对结论](probe_pair_analysis_20261003.md)与[结果清单](result_manifest.json)单独汇合，旧pending字段不回写。
