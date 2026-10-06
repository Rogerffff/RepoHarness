# DVC9395：Qwen首臂七维与同题配对独立语义复核

2026-10-04 SGT。仅读本机封存原件、标准库离线文本／SHA重建；已见私有材料和既有结论，不是fresh公开读者。没有候选执行、测试／评分／模型重跑、CPU、Docker／SSH／云操作，也未改源码、board、current、总账或执行ACK。新执行链按[同题独立执行报告](non_author_dvc9395_pair_execution_review_20261004_v1.md)固定身份复用；本次独立核完整新轨迹、88份SSE、候选／基线与正式失败，不机械重复429成员或旧Coder全套。

**Qwen本轮是部分修复的有效raw0，不能接受为正确解；未发现需要修改冻结材料、断言或评分的新增阻断。** 作者七维及新配对总结当前版本的主要数值、失败阶段和七维判断与原件一致。P2P是36/37，通过总数37不能写成P37/37；旧GPU错误转述已单列更正，原机械回执始终正确。旧Coder GPU null／entry1／cleanupfalse及同原FP CPU raw0各自保留。

## 1. 原候选、公开边界与正式节点

原FP canonical `bca0a3a7a04f2259a21b1f0aa7904b12ceff777f234dc2bde16f28345f45d476`；baseline canonical `0c75caa0ac9790c739e0250f37125f342241d19d57bb430e6a6c7fa009acf0ec`。完整FP三项：`dvc/stage/__init__.py`、`dvc/commands/repro.py`、`tests/func/test_run_cache.py`。正式projection只应用前两项；测试修改仍在原FP，report的`test_files_modified=false`及hygiene clean不表示模型未改测试。

完整eval的6309–6349行重新逐节点重建：**41实际=37passed／4failed；40参考=F1/3、P36/37；唯一未计分原import FAILED。** 以本题固定`host_grading_views.jsonl`实际3F／37P绑定，没有missing／skip。pytest两条FAILED后的` - ...`／` - dvc.exceptions.Repro...`是异常摘要，不是node ID；JSON保留后缀。官方parser42含captured日志`dvc.commands.freeze:freeze.py:19=ERROR`伪条目，不改原diag、评分或parser，也不算第42个测试。

| 实际失败 | 分区／状态行 | 行为与堆栈位置 |
| --- | --- | --- |
| `test_repro_pulls_mising_data_source` | F；6346行 | 普通source及modified、有远端前半段已经通过；939–946行后段`imported.dvc`失败，872–905行新helper→checkout缺缓存 |
| `test_repro_pulls_mising_import` | 未计分；6347行 | 额外原import同类失败；1611–1641行helper→checkout，1665行reproduce，1776行ReproductionError |
| `test_pull_without_remote_preserves_modified_source` | P；6348行 | 已修改且存在的source仍被请求远端；1999–2006行helper→cloud.pull→get_remote，2056行NoRemoteError，2066–2069行目标调用 |
| `test_restore_pull` | F；6349行 | 2404行push(run_cache=True)，2415–2418删除本地run-cache再reproduce；2373–2386行run→save→save_outs，bar不存在 |

前三节点属于`tests/func/test_repro_multistage.py`，末项属于`tests/func/test_run_cache.py`；同名JSON记录完整ID、分区及41个状态行。新增frozen下游F通过；其余36P通过。失败均是测试已执行后候选业务错误，不是导入／收集基础设施故障；本轮曾有的临时候选ImportError已在求解期间修掉。

公开prompt要求pull本次repro所缺且必要的文件，并给中性环境说明／已有公开测试入口；它不授权在没有缺失时强加远端，或忽略仓库导入与远端run-cache。模型193项公开通过与私有正式失败分别评价，不为取得1放宽断言。

## 2. 根因与修法

候选正确看到了data-source／frozen分支只做`_check_missing_outputs()`，并在该检查之前、`not dry`内、`pull=True`条件下加helper。这修正旧Coder“缺失检查先抛错，恢复不可达”的次序；实际普通数据源恢复和新增frozen目标通过，说明是有实质局部效果的修法。

但helper先对整个stage的`get_used_objs()`调用`repo.cloud.pull(objs)`，之后才对`out.hash_info and not out.exists`做checkout。是否缺失的筛选太晚：modified但存在的source可触发reproduce，cloud.pull先解析远端，造成P失败。无变化、无远端节点通过是reproduce提前skip，不能证明modified边界正确；日志没有证明源内容已被覆盖。

baseline `Output.get_used_objs()`1078–1079行对repo_import返回空映射，stage聚合后也没有可拉对象。候选没有走`repo.fetch`的imports恢复路径，直接checkout缺缓存，解释复合F后段及额外原import失败。`StageCache.restore`175–213行仍在本地_load成功后才pull数据对象，未补获取远端run-cache；本轮正式版本删除本地runs后落入执行／save，bar缺失。公开原test_restore_pull仅删输出缓存、保留本地runs，故通过不能覆盖正式场景。没有材料无效或需重跑的证据。

## 3. 定位与纠偏

19已读StageCache.restore，29／31读缺失检查及抛错，37读changed路径，43读到cloud.pull会先解析remote。50先加本地checkout，52把恢复放在检查前，54加cloud.pull但凭空导入`big_file_size/big_file_traceback`并错误导入OutputDoesNotExistError。

55／56原公开10＋17通过，57真实恢复脚本却打印`os.system`状态65280、output未创建；58有唯一`is_error=true`，exit255／ImportError。59–61检索真实定义，62删除不存在导入、改从`dvc.output`导入并合并helper；63起普通真实恢复成功。之后业务实现不再改，只补测试／帮助，没有继续检查repo_import、远端run-cache、modified／无远端边界。是有效纠偏，但没有完成契约。

本次按615条基线tar中的文本与8次成功Edit顺序在内存替换，29次Read所有编号行均匹配当时源码，最终三FP解码字节完全相同。没有导入／执行候选；作者source-read回放记录与独立结果一致。

## 4. 工具使用与并行

1264行完整轨迹，88工具=Bash51／Read29／Edit8。仅58标记错误不能解释为其余均成功：5不存在目录被管道掩盖、20grep正则错误、57恢复失败、71／73／74追加测试失败都在正文。模型本轮真实Git＋DVC仓库、local remote、push、删除workspace／缓存及repro比旧Coder弱mock更有信息；也有多次宽检索、重复读和重建同一/tmp仓库。

第一份SSE含工具1／2，其余86个工具请求各1，最后请求纯总结：88requests／88tools与CC原num_turns89同时保留。所有tool ID／name对应闭合；缺工具精确起止，不能证明物理重叠或省时。源码／帮助检索可合并，依赖候选变更的恢复核对需顺序；同一/tmp/test_pull反复操作要顺序或隔离。

独立重建SSE完整input_json后，**86个参数对象与CC轨迹相同，另两项保留原差异**：工具50轨迹补`replace_all=false`，SSE没有该字段；工具57轨迹没有SSE的`cd /testbed && `前缀，其后脚本自行chdir临时目录。分别保存两侧canonical SHA和完整参数，不笼统称88个输入逐字相同，也不据此推改了候选／评分或泛化正常化其它差异。作者目前仅称工具身份匹配，没有这种全参数字节同一的误述。

临时CLI没有逐次显式写公开说明的PYTHONPATH；工具1证明/testbed/dvc，58实际候选导入错误及62改后恢复成功也支持使用该源码。没有逐命令独立import-path证明，不把公开要求写成每次显式完成。

## 5. 自测、测试修改与最终陈述

70仅追加两个真恢复测试，原test_restore_pull内容未改。71为1fail／1pass：裸target=data被当成dvc.yaml stage；72改data.dvc，73仍1fail／1pass，74明确是`Stage is Stage`身份断言。**75（轨迹1056／1060行）只把`assert stage is data_stage`改为addressing相等；文件存在及`read_text()=="data content"`均保留。** 76两项通过，是修正目标与不合理跨加载对象身份判断，不是删恢复断言掩盖失败。

最终五组公开测试：77 run_cache12，78 multistage17，82 repro80，83 unit command2，88 unit stage目录82，共193项，含追加2。每组有完整终局pass摘要，55／56／67的重复27项不另计；第五组是目录中的多个测试模块，不称193个正式引用或全仓回归。head／tail管道本身不隔离pytest RC，完成摘要支持这里的观察范围。

63／64／65／66有真实普通source恢复日志／文件结果，66明确output为hello world。86最后命令的`grep -v "^!\\|"`含空正则分支，抹掉全部repro输出；原件仍显示修前data不存在、修后data／output存在及output精确为source data，不能依过滤结果单独证明repro退出码或重新出现了某日志。87不带pull明确缺source错误、文件仍不恢复，是有效反例观察。

最终1260行正确列出三个改动、恢复位于检查前和两项新测试，没有声称已看到正式引用全过。但“all missing files needed”完成判断过宽：缺repo_import、远端runs及modified无remote边界。评分在solve之后，不能将模型未见的私有失败指控为隐瞒已知失败。公开自测完整、边界覆盖不足与有效正式0应同时保留。

## 6. 效率、身份与资源

solve260.000s；CC256.437s／API116.264s；88响应秒数重新加总114.399s。累计输入3,068,590／输出16,725token，单次最大60,117／1,110；输入含重复上下文，cost15.761075美元是metadata估算，不是实付。88响应均HTTP200／attempt1／SSE完整／无stream_error，实际请求max_tokens65536；metadata32000分开保留，短输出不能证明65536上限可达。本轮未见context／240turn／10800s／1024request预算耗尽、截断或恢复。

独立执行报告已核同题公共prompt原CRLF字节、baseline、base c75a5583b3840ba90a8e800a0f42c1cb120916db、code8、材料R20及固定image `sha256:c093861f62b8071b3c1e5b3142abd5843888421364e69dd728cb80856f621b60`。profile仅proxy18081→18082不同，不把模型checkpoint／parser／sampling服务差异写成全runtime仅端口不同。模型服务live capture／挂载／argv／HTTP按该报告复用，不再重审权重；Qwen声明40、实际列表37，其中26分片，size匹配，未逐片重哈希或证明GPU内存。baseline lineage null、config-only及checkpoint_identity_verified=false保持。

正式grading268.066s；install3.933／test16.848s，pytest正文15.87s；setup228.024776s低于900也低旧300，不能据成功断言900必要或旧保护超时根因已解决。2CPU／4GiB／PID512及3600／900／120／1800预算未放宽。

直接重建39行有限resource：actor20／grader18／relay20（grader用job-grade），memory.peak已采最大990,486,528／1,004,756,992／28,016,640B，pids.peak26／12／7，已采OOM kill／PID limit事件0。report960.875MiB与已采grader约958.211MiB范围不同；不推全程峰值／全程无事件／最低配置，resource_facts null保留。80项48.63s、27项13.65s、82项10.35s是日志pytest等待段，不是solve减API得到的工具时间或并行收益。

## 7. 结束、配对用途与未验证范围

新Qwen CC success／end_turn、harness0／completed；UID54322前置0／install0／test1及segment completed，solver停止屏障residual0／双读稳定、gateway revoked／active0、solver清理true；grader created1／removed1、open／supply／cleanup_failures空、cleanuptrue。精确PID1成功journal支持退出，退役unit默认0不是证明。执行证据链正常且业务失败有效，不因raw0重采。

旧Coder按[已有语义报告](non_author_dvc_three_coder_a1_semantic_review_20261003.md)及[同原FP CPU报告](non_author_dvc9395_same_original_fp_cpu_runtime_20261003_v1.md)复用：缺失检查在恢复前、helper没有新增远端能力；原GPU求解completed但relay删除超时造成entry1／cleanupfalse／rawnull，未被CPU或Qwen覆盖。CPU同原FP仅评分一次raw0，F0/3／P37/37、41实际37pass／4fail；不是新增solve／模型样本。Qwen F1/3／P36/37，同为实际37／4却通过不同节点，不合并为同质0。

Coder FP stage＋2根脚本，CPU投影三项；Qwen stage＋帮助＋追加测试，GPU投影两源码。Coder44工具／45请求，Qwen88／88；solve215.507s与260.000s两次单次观察且验证覆盖不同，不能给稳定速度、能力或吞吐排名。旧GPUrelay超时没有由本次成功清理证明已根治。

作者七维和配对总结可按上述固定版本核收。本报告没有ACK、释放指针、操作资源或要求机械普通追加采样；不授训练／留出资格、稳定性、题目饱和或硬件级模型身份。候选错误不等于材料错误；没有新的材料修订依据。

## 8. 固定证据身份

同名JSON有143个精确路径／SHA／size，88工具完整输入及结果UTF-8 SHA／结果行、全部模型可见陈述、29Read／8Edit文本链、88完整SSE分组／两侧参数差异、41节点／40引用和有限资源重建。独立执行报告重点pins本次逐SHA／size一致；429成员全核按执行报告复用，不冒称本次重复全仓或逐权重核验。

| 证据 | 实际SHA256 |
| --- | --- |
| 作者Qwen七维 | `87d0a81c929cd00eeae0a2632c2bae927fc83290f8fa7d7b3a21a9830d72d602` |
| 作者完整owner readback | `52b0a14e91451c197fd5b73cd0d05581627d35ce36aee0610b0ba9d3785ddad1` |
| 作者同题配对总结 | `551de1a9ce0a8a09de2e390df1d566330ecbea47ee6a9bcb7390b7f28914420a` |
| 作者source Read/Edit回放 | `3443cb1d1fabd7661d81ac6601375f7273572b311d7bbd214c8f0b2cd8c5be80` |
| 作者operational读回 | `1d973ecc693b065e29697630cfcc65795c5a1f1faf16f28faf41af5adf6f16c7` |
| 独立pair执行MD／local JSON | `84729404b5aa67df5a7793594039b2792324ac7d3133e1c9143f522a72d19052`／`983903c2ca0573459839b5a84066bdb9911cd2f0a2790efcc9bf58745dbd5c6b` |
| 原完整eval | `e69b70cd673b8df8c6c30f812798ef1eed01bcfd9a08178c7e3384ed7ca272fd` |
| 原FP文件／baseline tar | `f64380b3567fd0e7967a4ff46f1062910a2682a8912861e97940dc99b8295ab0`／`a91aea77992a789ede590526ffd72200106afb99ff10ccc1cc655e139d1eb3ce` |
| 原pair回执／Qwen执行回执 | `eed35d58c543a7ef411042cbe310b4d5553034658ccbf75166354e6f53bbfe4c`／`55f1bfda379232313c6c187af4926d791ad95ec1514542f3c2b8604118ca29fe` |
| P2P转述更正记录 | `1b294e5b5bbb2e686ec7fd39a64fdf21e082e9d8cb725a91628b631fd694f8df` |
| 旧Coder语义／CPU runtime MD | `f67401f24fc7a60bd8a2f3a1e2f62c34e5b4e77d0faf86452cbe4c2a2a134a05`／`d9704016a0b4ee5f649a3744b678d96afed03ac8fe5e7ad3125eb76e68d634b5` |

原件导航根为`runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dvc9395-qwen36-a1/`：轨迹／FP／baseline／projection／eval在`queue_qwen_tail2_v1/results/gpu1003-dvc9395-qwen36-a1/`；gateway在`services_qwen_code8_v1/qwen36/gateway/tail2-v1/gpu1003-dvc9395-qwen36-a1/`；resource在`qwen_tail2_closed_v1/gpu1003-dvc9395-qwen36-a1/resources.jsonl`。精确指针以JSON为准，所有历史原件保持。

配套JSON `non_author_dvc9395_qwen_pair_semantic_review_20261004_v1.json`，SHA256 `1d65ca51cb7d17de39f550920da67da5218b210463f6e868ca2e97f0ae44e907`。
