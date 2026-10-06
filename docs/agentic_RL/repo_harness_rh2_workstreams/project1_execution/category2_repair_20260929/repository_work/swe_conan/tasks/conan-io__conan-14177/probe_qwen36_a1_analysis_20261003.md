# Conan14177：Qwen3.6 首次探针分析

2026-10-03。请求 `swe-conan14177-r11-briefv2-20261003-v1`，作业 `gpu1003-conan14177-qwen36-a1`；实际code8／R11、brief v2、`probe-wide-v1`，本模型仅一次。

**raw1，2F／11P原13完整参考均通过；候选只改生产文件，增加verbose=False默认参数和文件名输出，保留原metadata与patch调用。** 手工自测使用patch_ng mock，没有实际应用补丁文件；这个范围与功能正确性、评分运输分别记录。当前为题主分析，独审核收与ACK见处置及配对页。

## 原件与评分范围

[固定新版请求](probe_request_20261003_r11_briefv2_v1.json) SHA `478ba02b7ead3aabda7a6493694434c350a694c1600e0f71851eabef5d8ffff7`未改。权威快照 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan14177-qwen36-a1/`，题主逐件核137件／10,757,623字节SHA／大小一致。完整diff1,822字节、SHA `e56a787281b6ba1dbc58c716607fbbb940f5c82aca800a101ba338661d89772c`，只有`conan/tools/files/patches.py` modify／100644；实际baseline与公开base原字节一致，隔离应用完整候选等于Frozen，正式projection完整含唯一生产路径。未新增、修改或删除测试、fixture或开发辅助文件，也未访问私有评分。

FP canonical digest `c7bd035d8a2bb831118b06a90eb756c29439c0c71f4ef20161fcd1542da75eac`，baseline canonical digest `6fdad6e91c67e236fae68334aaa479344f4669406564d26b032f9c5b466497a3`。安装0／测试0，原日志13完整nodeid与`13 passed`尾部，missing／skip为空，eval SHA `6b4410d72934942da8821c0cde5e0c7073418f21029c0d474ef4dd748094b238`。材料保留云端v2原字节，单补丁description从F移入P，原13节点均保留；不是原2F10P之外又添一个新的P测试。

actor／grader实际config ID `4ca5aeae4e588c89008e6ca335500ffa71aea77bd6eab0b7491d514534696bb0`。真实首gateway请求包含完整原issue＋brief v2，prompt SHA `afff730a0f16d7adac65375ddbb0620f0ac4e30859d80b7a20f04e2c5d37dae3`，brief SHA `da4b3670c36a87e03a441055e4a18c39c6d0aa1f2f2b06f5f11dabc5710957e8`，issue CRLF保留、brief末尾换行被strip。旧brief v1误拒请求安全取消且未执行，不能计为这个新请求的失败样本。

[新臂机械回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-conan14177-qwen36-a1_execution_receipt_v1/execution_receipt.json)与[双模型回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/swe-conan14177-r11-briefv2-20261003-v1_pair_execution_receipt_v1.json)（SHA `3ad116601fa17ecc48259eaa3b098388198871e3ed0eac76485906b43be6c17a`）按执行范围保留，不代替候选语义／训练判断。私有原件读回及完整工具内容在 `runs/category2_repair_20260929/conan_cpu_20261003/probe_analysis_14177_qwen36_a1_20261003_v1/`；以下为原trajectory一基行。

## 七个维度

### 方法

行79一次生产Edit增加`verbose=False`和文档；在现有patch_file分支复制entry后，先保存原相对文件名，verbose时调用`conanfile.output.info('Applying: ...')`，再pop一次并按原export_sources_folder join，向原`patch()`传剩余metadata。没有第二次pop错误，也没有mutate原conan_data。

版本筛选、无version时list行为、缺conandata／无patches／非法类型／非法entry、strip／fuzz／base_path、异常传播及patch_string支路未改。False仅不增加文件名日志，旧patch_type／description日志仍输出；不能说False为全程静默。用户要看输出文件名，不要求本轮显示机器全路径或改变真实补丁应用。

### 定位

工具1搜索当前helper，工具2完整读生产，首次源码读取距第一模型请求 **1.880秒**；工具3读原13公开单测和mock设计，工具4确认files导出。行75明确实现可选verbose，四工具后行79编辑，第5模型响应完成上界 **10.679秒**。没有改前运行verbose失败复现；基于issue与明确签名扩展定位，生产改动一次保持到最终，无回退。

### 工具与纠错

14工具为**Bash8、Read5、Edit1**。唯一显式错误行137：内联脚本造了patch_file路径但没实际文件，真实patch_ng.fromfile触发FileNotFoundError，没到后面的日志assert，也没应用第二补丁。这不是helper应吞异常的证据。

模型随后按公开测试的mock方法替换patch_ng.fromfile/fromstring，MockPatchset.apply返回True，try/finally恢复patch_ng原函数。行155两文件日志及默认不增Applying检查通过；行173按指定version选两文件，另一版本文件不输出、type旧日志仍在，patch_string无Applying。未更改生产或删旧例迎合缺文件。mock不记录apply的实际路径／参数和文件变更，覆盖限日志与分支；公开旧单测及可信参考分别补参数与旧行为。

### 并行

15实际gateway／adapter请求、CC15回合，前14响应各一个工具，最后结束；无实际多工具批次或重叠证据。生产与公开测试读取后files导出可独立批量读取，本次串行。mock替换和try/finally恢复在各独立Python进程中，编辑／改后检查依赖前一步；重复pytest涉及同工作树，不能据无显式依赖推安全并发或并行加速。

### 验证

| 轨迹行 | 实际结果及范围 |
| --- | --- |
| 119／191 | 公开files目录两次各61 collected／48 deselected／13P，为同组旧patch例重复运行，不算26独立例或61P |
| 137 | 初次内联真实fromfile缺文件，脚本非零；未完成两日志assert或False检查 |
| 155 | mock成功：两文件verbose日志，默认False不新增Applying；不验证实际文件补丁 |
| 173 | mock成功：版本筛选两文件、排除另一版本、type旧日志仍输出、patch_string无文件名输出；不证明完整真实patch_string可解析 |
| 209／223 | CLI显示Conan2.1.0-dev；直接原模块13P，与前两次同13节点，没有扩大独立覆盖 |
| 可信grader | 保留13完整节点2F11P全P，verbose文件名顺序、False旧metadata及路径／参数／异常回归；patch_ng仍受控mock，非真实补丁文件应用 |

最终“13 existing pass”与原输出相符，versioned／nonversioned及patch_string日志观察也确有mock原件。应明确mock底层，不称原issue两份真实补丁已应用；False句子按“无额外输出”理解，不能抹掉原metadata日志。本臂没有新增测试落盘，自测并非可信评分来源；原评分依赖固定云端测试消费。

### 效率

求解 **36.810秒**，harness33.880秒；CC33.268／API30.250秒，残差3.018秒不是纯工具时间。15请求累计输入 **169,819**／输出 **5,028 tokens**，最大单输入17,520，gateway／adapter／CC核同。源码定位清晰，唯一错误通过完善mock而非改坏生产纠正；公开13例运行三次、生产全文重复Read无新行为范围，存在减少空间。

Git15.298秒、可信初始化8.138秒等准备单列；评分94.183秒，reset16.072／prep0.277／test2.162，队列0。实际15请求max_tokens65536，CC32000只是元数据；196608上下文、240回合和3小时未触及，不证明极限容量。费用0.974795美元为CC估算，非GPU账单。

### 结束与稳定性

completed／success／end_turn、harness0，15HTTP均200，无stream error或截断／拒绝。完整退出、实际PID1成功journal、actor／grader清理及gateway revoked／drained／active0合读；not-found／默认0不能单独证明。有限资源间隔采样、权重未重hash及完整限额边界保留，不据短样本推出容量或全程峰值。

两模型各首次一次均raw1；Qwen仅生产，Coder完整候选还有公开新增测试和demo，但实际保护投影与原13参考独立成立。不同runtime code7／code8及方法质量分别记录，不建立稳定成功率、模型排名、训练／留出资格；普通追加采样按覆盖优先暂缓。

## 处置

题主已全文核收[非作者语义报告](../../reviews/non_author_14177_qwen36_a1_semantic_review_20261003.md)（SHA `381e880517cdfdf23a07c2cdb13c76a1e1e366cfa49b19b5c9160e184ec34e5b`）及[执行报告](../../reviews/non_author_14177_qwen36_a1_execution_review_20261003.md)（SHA `0b0cd2666f19c72d3c72d4254311a3add3e19b77bbded128883f1dc29f7d2022`）。两份均无新增P0／P1／P2 finding，无当前候选或材料阻断；failed inline、mock范围、重复同13节点和有限资源／权重范围保持。实际磁盘补丁应用未知不补造；原candidate／reward／历史误拒原件保持。本轮无需修材料、重分或新跑CPU／GPU，不补模型样本。总回执核对后先ACK再清活动指针，当前状态汇合在[配对页](probe_pair_analysis_20261003.md)及[结果清单](result_manifest.json)，旧首臂pending字段保持历史。
