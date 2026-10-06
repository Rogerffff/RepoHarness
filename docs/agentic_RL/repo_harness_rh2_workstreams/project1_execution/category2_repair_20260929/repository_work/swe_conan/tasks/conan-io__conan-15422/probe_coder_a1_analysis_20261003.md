# Conan15422：Coder 首次探针分析

2026-10-03。请求 `swe-conan15422-r12-briefv1-20261003-v1`，作业 `gpu1003-conan15422-coder-a1`，模型 `Qwen/Qwen3-Coder-30B-A3B-Instruct`；R12、材料v2、brief v1、`probe-wide-v1`。

**raw0是完整tests_failed：4／5F通过、40／40P通过，唯一默认jobs参考因字段缺失而失败。题主及非作者语义窄核确认最终候选只修显式配置，默认并行缺陷仍在；执行独审也已回。模型先实现了默认helper值，随后为了满足自己错误的默认预期改掉生产逻辑。这是当前候选缺陷，未发现材料误拒，也不以改测试自动判负。Qwen首次及整项回执待回。**

## 原件、候选与精确失败

[固定请求](probe_request_20261003_r12_v1.json) SHA `c7062edcbdb67ecaa7085099394865578407e83fb8be279969e0d5534ba7da09`不变。题主核157件、14,046,841字节SHA／大小；实际首gateway请求含完整原issue和brief v1，按原字节核，保留CRLF及brief正文。闭合清单 `runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-conan15422-coder-a1_closed_manifest_v1.json`；原件及全工具索引在私有目录 `runs/category2_repair_20260929/conan_cpu_20261003/probe_analysis_15422_coder_a1_20261003_v1/`。

完整原diff SHA `f429ece39a75f44ffe6feb47251ac842962c2c0dc6ca3ea0a136523dc921b1df`包含生产 `presets.py`、公开单元 `test_cmake_presets_definitions.py`、新增131行 `demo_jobs_feature.py`。从实际baseline取全部修改原件，与公开base核对，在临时隔离目录应用完整diff；三份Frozen字节及mode匹配、Python AST可解析。**投影包含全部三路径**，因为评分控制面保护的是 `integration/.../test_cmaketoolchain.py`；“官方单元测试被改”不自动剔除或判0。`test_files_modified=false`只描述受保护评分面，没有声称候选不含其它测试修改。

原eval SHA `eac651d5b75268f5fdc07034a5e0f91168328d6e004d098e47ada37ea86224f1`，44 passed／1 failed／3非参考平台skips；45参考齐全，无参考skip／missing。唯一失败为 `test_presets_jobs_default_matches_public_helper`：eval行1077–1078、可信测试行1247，`presets["buildPresets"][0]["jobs"] == int(expected[0])`得到 `KeyError: 'jobs'`。没有到比较CPU数值的步骤，故不是“容器CPU数不稳定导致值错”。三skip源行355／382／816分别Only OSX／Only OSX／Only Windows，按固定可信源码AST映射到非参考函数，不假称原log打印完整skip节点。

[执行独立报告](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/conan15422_coder_a1_execution_review_v1.json) SHA `387975f1e1f6dfd92c23500bd207b629b209191cbd62c83f22fa76b108f71ea5`限定执行／运输：安装0、测试1、外层作业0，完整失败与Frozen／基线／两层清理一致；服务捕获是运营身份，未证明GPU内存权重逐字节或极限上下文容量。raw0和env_qualification absent原字段保持，不补资格或改分。下文行号为该作业 `attempt/trajectory.jsonl` 的一基行号。

## 七个维度

### 方法与错误演化

公开issue要求生成build preset的jobs，让 `cmake --build --preset`继承并行能力，未要求“只有显式配置才加”。公开 `build_jobs()` 明确定义：有 `tools.build:jobs`取显式值，否则取检测CPU数；这个默认能力正是遗漏字段时没有传给CMake的部分。新增默认参考读取同一生成进程的公开helper结果，不固定主机CPU数量，也不强制gold的具体实现。

模型行195正确定位 `_build_preset_fields()`，行199先加 `jobs=build_jobs(conanfile)`并写正值。它新增“未设置jobs时应无字段”自测，经历string类型与共享fixture纠错后，行294发现真实helper返回默认2。行307已读明默认行为，仍在行312解释为应该只保留显式值，行316增加 `if "tools.build:jobs" in conanfile.conf._values`。最终默认路径不调用helper，原并行问题仍在；主动读取私有 `_values`也偏离公开Conf接口。

显式2／7的真实configure＋build及Multi-Config追加／替换通过；默认缺项被准确拒绝，40旧参考保持。没有测试识别／绕过。公开单元改成每例fresh对象解决污染，本身合理；新增“不设jobs就不生成”断言却把未获支持的兼容假设固化进测试。demo打印同一假设并保留，不是独立功能依据。初版生产实现没有实际评分，不能声称“中途候选已经通过全部评分”。

### 定位

工具2首次读对生产源码，距首请求 **1.397秒**；随后查看测试、ParallelBlock和build_jobs。行195正确定位与计划的响应完成距首请求 **13.207秒**，在18个工具后；这只是响应完成上界。查helper时先搜索cmake／conans目录、误读 `/testbed/conan/tools/build.py`（实际build目录），然后查 `build/__init__.py`和cpu.py。根因位置正确，需求解释在自测阶段发生错误回退。

### 工具与纠错

38工具：**Bash18、Read10、Edit8、Write2**，六个原 `is_error=true`：缺失build.py、三次单元失败、两次demo错误。三次单元结果分别2失败／2通过、1失败／3通过、1失败／3通过，最后4通过。

它正确修string `"8"`为int8和module fixture污染，随后为错误默认预期修改了生产代码。demo先 `from unittest.mock import mock`导入失败，再改MagicMock却残留 `mock.patch`，产生NameError；最终重写直接调用真实 `_CMakePresets.generate()`，脚本完成。这个纠错恢复了工具执行，但不能修正需求理解。原脚本捕获Exception只打印、不保证非零，成功退出本身不足以判所有demo正确；本次具体输出是生成无jobs和显式16。

### 并行

39响应前38各一个工具，最后结束，无多工具请求或重叠。生产文件定位后，独立公开测试与helper读取有并行机会，但大量纠错依赖顺序。CC／adapter多工具可用性未独立证明，模型并行能力不可判断；不将同一单元文件的写入与测试列为可安全并行。

### 验证

| 结果 | 覆盖与限制 |
| --- | --- |
| 行242／268／294→333 | 三次自测失败后最终4通过；最后两条新例分别显式8、错误默认省略假设 |
| 行348 | 原公开CMakeToolchain integration40通过、3平台skip，3.33秒；不含宿主新增五F节点 |
| 行361 | CMake工具公开unit58通过，0.97秒；含前述单元4，不能相加为不重叠62 |
| 行383／423→445 | demo两次异常后生成成功，默认无jobs、显式16；未运行真正cmake configure／build |
| 可信grader | 原1／1F、新3／4F、40／40P；显式2／7实际CMake3.23.5 configure和build成立，默认KeyError失败 |

模型最终行450准确披露“只加显式值”和公开测试通过，却声称“完全满足原issue”，且用自设默认兼容假设作依据。它没有验证默认并行实际结果，也没有执行所示 `cmake --build --preset`示例。广泛旧回归通过可以排除部分回归，不能核销新增默认功能；宿主可信测试明确抓住该缺口。

### 效率

求解 **92.707秒**、harness89.856秒；CC89.235秒／API81.519秒，差7.716秒不等于纯工具时间。39回合累计输入 **759,342**／输出 **9,995 tokens**，最大单请求32,775；CC／gateway／adapter一致。误定位helper、重复整文件编辑与单元测试、demo导入修补增加开销；其中fixture修正有价值，错误需求驱动的生产回退没有达成目标。不据单题时长评一般模型效率。

Git清理16.301秒、可信初始化8.523秒及容器准备独立；评分100.245秒、测试5.478秒、评分队列0秒，不算求解慢。39gateway实际输出预算65536，CC32000元数据不覆盖它；196608上下文／240回合／3小时未触及，不是预算截断失败。CC自动估计4.046585美元非本地账单。

### 结束与稳定性

`completed/success/end_turn`、harness0、39HTTP200无流错误，正常结束后语义缺陷被可信测试判0，不能归类infra或截断。18个有限宿主采样有未知间隔，不推全程峰值。Coder只一次，Qwen首次缺；不判一般稳定率或训练资格。

## 处置

题主已读回并采纳[非作者误拒／语义窄核](../../reviews/non_author_15422_coder_a1_semantic_review_20261003.md)，SHA `36511c3af90d01038f7dc89d9eaeb06ce1a2ab243784a5a08bc1fa5acf84bb60`。报告将默认遗漏列P1候选缺陷，验证表述列P2；没有材料／共享阻断或待Qwen停发理由。保留原raw0、整份FP、失败轨迹及执行审；不修模型候选来改写基座诊断，不重跑旧CPU矩阵，不追加普通采样。当前请求保持claimed，继续等待Qwen首次及整项回执，无需裁定或修改材料。
