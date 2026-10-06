# DVC4166／6954：Qwen首臂语义与有限双模型独立复核

2026-10-04 SGT。限定本机离线标准库读回；已见私有材料及既有结论，不是fresh公开读者。没有运行候选、模型、测试、CPU、Docker／SSH或新评分，也没有改材料、总账或执行ACK。新Qwen执行身份、完整成员核及清理复用已完成的[执行报告](non_author_dvc4166_6954_pair_execution_review_20261004_v1.md)，本次从完整轨迹、原FP／baseline、评分日志、gateway及资源原件独立核语义；不重核852成员或旧四题全套。

**未发现新增材料、断言或评分阻断。4166是局部根因正确、修复仍不完整的有效0；6954是冻结合法负数行为上的有效1，但模型验证报告遗漏扩展失败。** 作者两份七维及新双模型总结与原件一致，没有需要作者更正的新增事实错误。支持题主按当前范围核收本次首轮；不授予稳定性、训练／留出资格或追加采样要求。

## 1. 身份与当前结果

| 题目 | 原候选与正式投影 | 正式结果 | 语义判断 |
| --- | --- | --- | --- |
| 4166 Qwen | FP2项：`dvc/ignore.py`及公开`tests/unit/test_ignore.py`；projection仅业务项 | raw0；66节点=64pass／2fail；63参考=F1/3、P60/60；3额外全过 | 否定目录恢复已修到，正向剪枝及原父目录场景仍失败 |
| 6954 Qwen | FP仅`dvc/utils/serialize/_py.py`，projection相同 | raw1；26节点全过；15参考=F3/3、P12/12；11额外全过 | 合法负数递归与CLI正确，扩展自测失败和非法operand边界另列 |

F2P是原本失败、修复应通过的参考；P2P是应保留通过的参考。无参考缺席／skip。当前完整eval的`-rA`状态行再次重建66／26节点，逐ID和状态与独立执行报告一致；一条FAILED末尾` - Asse...`是pytest异常摘要，不是node ID，JSON保留该后缀。未以作者节点摘要重建。4166测试修改被正式投影剔除，`test_files_modified=false`和hygiene clean不能解释为模型未改测试；原两项FP不变。6954 `/tmp`临时仓库未进入FP。

把baseline文本与成功Edit逐次在内存替换，不导入候选：4166有效Read10、成功Edit9；6954有效Read5、成功Edit1。15次带编号Read逐行匹配当时源码，最终各FP内容逐字相同。两个重复Read“Wasted call”及一个不存在路径Read分别保留，不能计入有效Read。这支持作者新增source-read记录，而非仅接受其声明。

## 2. DVC4166七维核查

**根因、修法与公开边界。** 原pathspec0.8.1目录regex如`^scripts/.*$`不能匹配裸目录，这是pattern输出和修前mock共同支持的局部根因。最终`_fix_negation_slash(ignore, pattern)`只对否定规则改写：尾部`/.*$`替为`(?:$|/.*)$`，简单前缀另加裸路径分支；`ignore=True`直接返回原regex。它没有给文件与目录不同匹配路径，也未修正正向目录规则。issue列举多种写法，不授权将普通子文件否定解释为重入已剪掉的父目录，或把全部例子扩成相同规格。

两项正式失败落在行为断言，不是导入／收集故障：

- `tests/func/test_ignore.py::test_ignore_file_in_parent_path[data_struct2-pattern_list2-result_set2]`：本应空集合，实际仍有`dir/subdir/should_ignore`（eval719–725行）。正向`subdir/`未剪父目录，后续否定错误保留该文件。
- `tests/func/test_ignore.py::test_directory_rule_prunes_directory`：`assert not dvc.tree.isdir("blocked")`实际为True（eval746–752行）。

新增`test_negated_directory_rule_recovers_non_example`通过，与最终否定regex修法一致；60个P全过。因此是可解释的部分正确错解，不能把0包装为服务噪声，也无需为取得1改冻结断言。

**定位与纠偏。** 工具7／8读到尾斜杠规则的实际不匹配；17初Edit带`utf=8`，18即修正。27／30先后引入转义及元字符前缀错误，28／31出现`nothing to repeat`／不闭合分组；36捕获堆栈后继续诊断。41收紧前缀，46处理隐式通配前缀。48公开测试暴露自己引入的`test_remove_ignored_file`回归，54／55只改否定规则，56恢复29项通过。它纠正了自身回归，但保留原正向目录缺陷。58／59的边界预期和dirname错误有60后续纠正，未删断言掩盖。

**工具使用。** 1055行，67工具=Bash46／Read12／Edit9；`is_error`两项只是工具标记，36捕获打印的regex堆栈、48管道内pytest失败同样是失败观察。mock使用公开`mock_open`，实际`readlines()`读到规则，没有旧Coder空规则mock失真。但相近regex试验、重复读取及六例重跑较多，末尾63／64两次Read被告知未变，65仍cat。新增8项是真断言，仅核平面`matches()`和名称例子，没有真正目录遍历、同名文件／目录区分、正向剪枝或父目录回归。

**并行。** 前两份SSE分别为搜索＋列目录、源码＋公开单元读取，各2个tool_use；第一组结果逆序到达，均在后续生成前返回。其余64请求至多1工具。66请求／67工具与CC原`num_turns=68`同时保留。没有工具起止跨度，不能推物理重叠量或时间收益。独立初读可成组；修改→测试→修正有依赖，同工作区DVC测试也需考虑共享状态。

**自测与终述。** 修前公开29项通过；末尾公开29＋新8断言共37项通过，不累计各次复测，也不是正式66节点。工具67／轨迹1041行的37pass和最终1051行总结有原输出支持；最终准确说明只修否定regex及两处文件修改。但“all patterns…work”和完成修复主张越过平面例子，两个正式目录目标仍失败。没有新增WorkingTree／CleanTree遍历复现，37pass不能代替目标行为。

**效率与资源。** solve201.240s；CC197.657s／API174.746s；重新加总66响应173.172s。累计输入2,082,248／输出27,645token，单次最大53,374／1,939；累计输入含重复上下文，美元字段是估算metadata。HTTP200／attempt1／完整SSE，无本轮预算截断；trusted setup246.668s不是模型思考或纯chown。有限资源范围见第4节。

**结束原因。** actual install0／test1、UID54322预检0、completed／end_turn／exit0及两层cleanup已在执行报告核定。正式测试失败与求解正常结束同时成立，支持有效候选0；已退役unit的默认0不替代精确completed／PID1 journal退出证据。

## 3. DVC6954七维核查

**根因、修法与范围。** baseline `_get_ast_value`只处理Num／Str／NameConstant，合法负数是UnaryOp；外层忽略ValueError／AttributeError导致参数缺失。唯一Edit递归读取operand，USub执行`-operand`，UAdd执行`+operand`，其它一元操作ValueError；既有容器分支调用该helper，合法负整数、浮点及相应容器元素生效。源码与26个正式通过一致。此修法不等于完整表达式求值／任意嵌套容器支持，原sum／constructor拒绝不能重新解释为应支持。

没有数字类型保护，字符串／None正负号可静态推出TypeError，原外层不捕获它。本轮未运行该边界为新增失败，冻结目标没有要求扩非法operand规范，不据此改材料／断言。Coder UAdd直接返回operand，Qwen执行真正`+operand`；合法数字一致、非数字边界不同，不能称逐字同一修复。

**定位与纠偏。** 5读LOADERS接线，6路径错误后转向serialize目录，10读_py.py；11／12定位UnaryOp，19／21核Python3.9 Constant兼容旧Num。22唯一业务Edit，23即六例真实parser断言。轨迹没有修前parse缺参／CLI故障执行，只有源码和AST根因证据；修后CLI不能回填修前复现。37stash仅为实验单项基线对照，38恢复，最终diff、Read及FP一致。

**工具使用。** 609行，42工具=Bash35／Read6／Edit1。唯一`is_error`是不存在路径Read；管道里pytest失败不自动进入此标记。定位广泛find／grep和AST枚举有重复，后段第二临时仓库仅初始化未使用；源码和六例parser重复新增信息有限。没有Coder那种失败二元表达式断言改为无断言打印的过程。

**并行。** 43请求每个至多1工具，无成组／可证后台重叠。接线检索、独立阅读和AST例子可合并；init→写文件→repro→lock、stash→基线测试→pop须保持顺序。不能按文件数要求同状态仓库无条件并发。

**自测、失败与终述。** 23（轨迹319／323行）六例及31（431／435行）四容器调用真实`parse_py`，均有`assert result == expected`。27实际issue CLI成功；28（389／393行）lock读回`my_int:-1`。29 force repro后30（417／421行）lock还有`my_float:-3.14`、`my_positive:42`、字典a:-10。值可见但无自动lock断言；force repro不证明不变值跳过或改负数后自动依赖触发。正式新增测试不能补记成模型自测。

24 dependency20、25 params show11通过，40合并31通过不累计；32 serialize目录仅2个YAML测试，不是Pythonparser回归覆盖。**33（459／465行）experiments选9项，4pass／5fail，`head -80`仅留下第一失败的部分堆栈。** 四个`test_modify_params` changes2–5和`test_update_py_params`真实FAILED；37（517／521行）stash后仅后者仍fail，38恢复。只能证明这一项不是本补丁才引入；其余四项不能笼统归因环境／已证无回归，也不能在证据不足时断言都是补丁错误。

最终605行说31项在两个指定模块通过，数值／范围成立，lock负数也有原值支持；但遗漏扩展五fail，验证报告不完整。正式合法负数正确与验证披露缺口同时保留，没有需要本轮材料修复的新阻断。

**效率与资源。** solve56.742s；CC53.119s／API38.013s；43响应加总37.060s。累计输入695,745／输出5,648token，单次最大29,352／550。HTTP200／attempt1／完整SSE，无预算耗尽或长度终止证据。累计输入、成本和setup范围限制与4166相同，有限取样见第4节。

**结束原因。** actual install0／test0、UID54322预检0、completed／end_turn／exit0及两层cleanup与有效1一致；不以31项自测覆盖全仓。退出证据复用执行审查，不以退役unit默认0补造。

## 4. 资源更正、有限双模型比较与限制

直接按`resources.jsonl`的container run_id重建：actor／relay用原job，grader用`job-grade`。4166共35行、actor16／grader18／relay16，采到memory.peak最大分别1,091,866,624／1,173,024,768／27,836,416B，pids.peak35／30／7；6954共22行、6／14／6，分别952,459,264／929,918,976／27,459,584B、25／8／7。已采样本OOM kill及PID limit事件均0。v1按actor ID筛grader为0是筛选错误，v2更正与raw一致；旧v1保留，不是新采样／候选重跑。6954采样grader峰值低于report1017.270MiB，未覆盖终点，不推全生命周期、最低配置或全程零事件；resource_facts null保留。

复用[旧Coder独立语义报告](non_author_dvc_three_coder_a1_semantic_review_20261003.md)及已核执行，不重审旧轨迹：4166 Coder改regex分组、原分组已保序，F0/3；Qwen实际加载mock并部分修到否定目录，F1/3；两者P60/60、raw0，失败语义有区别。Coder FP23项含22脚本，Qwen FP2项含测试修改；正式投影各按原件解释，hygiene不等于完整FP没有残留。6954两者F3/3、P12/12、raw1；Coder修前缺参复现更直接，但无lock值读回且弱化二元表达式断言，FP含5脚本；Qwen修前仅AST根因，修后断言／lock值更充分，FP仅业务项，仍遗漏扩展失败。不能由raw1抹平验证差异。

工具／请求／solve原观测：4166 Coder89／90／293.626s、Qwen67／66／201.240s；6954 Coder36／37／60.305s、Qwen42／43／56.742s。每题每模型仅一次，不是稳定能力／速度排名，也无物理并行节省的因果证明。profile参数仅proxy18081→18082不同不等于全runtime只差端口：同题公开prompt原字节、baseline、镜像／HEAD、code8、材料及宽松预算已核，checkpoint、parser和sampling服务不同。

Qwen作业前live engine／adapter capture、readonly mount／argv／HTTP及固定revision复用独立执行报告；download声明40、实际列表37，其中26safetensors分片，列明size一致。没有新的逐权重SHA或GPU内存权重证明；不称37文件为37权重／40已核全量。8GiB writable quota配置未证明强制，baseline环境包digest null及env qualification未另跑保持。公共题面／中性brief原CRLF文本一致，不授fresh公开读者资格。

## 5. 固定证据与结论范围

同名JSON保存109个工具ordinal／原行／结果行、输入及结果canonical JSON SHA（UTF-8，排序key、紧凑分隔、保留非ASCII）、全部模型可见文本陈述、内存Read／Edit链、109个SSE逐请求工具分组、92个实际节点、有限资源重建及216个精确路径／SHA／size。执行报告91个引用本次逐SHA／size核相同；完整member核复用执行报告，不冒称本次再全量读权重或全源码。

| 固定材料 | 实际SHA256 |
| --- | --- |
| 作者4166 Qwen七维 | `f40d12c7160d21721eea4135ac8eb6a9701191cba14d37c34a3b0c01455bf6e0` |
| 作者6954 Qwen七维 | `e595bf32a9a82339cb515054288bceab8e90d95176b8e058b0c4940f358186fb` |
| 作者双模型首轮总结 | `bac3e6b543fa23caa06e12d26976f74d3d6ac14d44f58a49cc7b59b410c234a5` |
| 资源owner v2 | `1c3f40bb23366f78c918749738d9ff54f8897e13ca29323a87f3afc9f3709922` |
| 文本source-read一致性记录 | `29b2a504868e0a2f7b969aee5d37fc0db838819d8a56a2889b9c096c4893a188` |
| 独立pair执行MD／JSON | `d259fe83df623c383bf9d2ad43688069a7499e5cdb8a3e20d08969dc4089febd`／`74b992760a01bd59adbded9096c9029ee297e5118206b23f4db017e5046e0df8` |
| 旧Coder独立语义MD | `f67401f24fc7a60bd8a2f3a1e2f62c34e5b4e77d0faf86452cbe4c2a2a134a05` |
| 4166／6954原resource JSONL | `3d6c06a21d8ff56e31601f96cfb6107511bdf88a477cb01e82cc2cf9b354c908`／`5966abb283253251f483a20e5163f786714a06f22a1b8457385028c69ac2a841` |
| 4166／6954完整eval | `65a95989e22595bc320fd3142b10ba5456c06d8deded730379aee152276282b3`／`cecdf3e986beca2873b09f1525b2a89bc32d4494c73b0d8b3ac2edbc7842e51d` |
| 4166 FP／baseline canonical | `90b6ce6e6b04ef062b40b34bc4192a91750ee98d8e2e719c8c47725475565867`／`16f108c365097d36390d40ff2b06c47fcf186b13c0e4cae2381ebfe6048ab6db` |
| 6954 FP／baseline canonical | `1bcd6de39c9ad447208100b8c023afd361a248beaf5f073d74a10f262639f487`／`be0c03047652bd7c8ac13b696722f056a7b498ca5dd3c12fceba519a642c8625` |

主要指针：两题封存根`runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dvc{4166,6954}-qwen36-a1/`；其`queue_qwen_next12_v1/results/<job>/attempt/trajectory.jsonl`、`attempt/frozen/{frozen_patch.json,baseline.tar}`、`grading/{projection.json,eval_logs/*.eval.log}`；gateway的`services_qwen_code8_v1/qwen36/gateway/next12-v1/<job>/{requests.jsonl,responses.jsonl,resp_N.sse}`；资源`qwen_next12_closed_v1/<job>/resources.jsonl`。JSON精确列明每个实际路径，花括号仅是此处导航缩写。

作者两份七维与双模型总结可按本轮范围核收。4166两个正式失败保留为错解；6954正确修法、最终披露遗漏和未核四项扩展失败同时保留。此报告没有执行ACK／释放指针／操作资源，不重审其它题，不要求机械重复，不授稳定性或训练／留出资格。

配套独立读回JSON：`non_author_dvc4166_6954_qwen_pair_semantic_review_20261004_v1.json`，SHA256 `fe892760306ba31bf5fb33fa3bc430595db0058b51731c4472a291bb7491f66a`。
