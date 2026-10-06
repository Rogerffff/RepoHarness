# DVC5839：Coder 首臂与有限双模型比较非作者语义窄核

2026-10-03。请求 `swe-dvc5839-precision-values-r10-v1-20261003`；Coder job=`gpu1003-dvc5839-coder-a1`；R10 材料=`dvc5839-precision-values-v1`，预算=`probe-wide-v1`。

**结论：Coder 的真实业务候选正确，与已核 Qwen3.6 首臂业务源码逐字相同；当前23/23参考通过与公开契约一致，没有需要修改题面、公开说明或冻结评分断言的新增阻断。** Coder 自建验证没有直接检验命令精度，最终“所有功能保持完整”超过自身证据；完整 FrozenPatch 还有三个生成文件。两项均应保留为非阻断质量缺口，不能抹去或据此把正确业务修法判错。作者新增 Coder 七维报告及更新后的双模型总结已明确这些边界，与本次原件读回相符。

本核已读私有材料、既有 CPU／actor 及 Qwen 审计，**不是 fresh 公开读者验收**。只用本机 Python stdlib读取、SHA、tar、原 FP严格解码、AST及日志／轨迹重建；未运行候选、pytest、模型、CPU、SSH、Docker或重评分，未改输入、旧报告或原工件。执行层152件／7,657,883B完整核对、547基线成员、运行身份／服务／资源／清理由已固定独立执行报告复用，本轮不重复全152原件或整个代码树。

按当前14:01 SGT覆盖优先规则，本题首轮两模型各一次已完成且无必须新增GPU运行的语义依赖，支持题主读回本报告后核收本请求，并将当前 `still_needs_gpu=false` 作为“没有已授权必跑缺项”记录。**不宣称稳定成功率、训练／留出资格或精确能力排名；不要求机械三次／模型，也不操作云资源。** 后续校准只针对明确问题决定。

## 1. 原候选、公开契约与完整工件

直接从 Coder baseline.tar读取 `dvc/command/metrics.py`，与原 FrozenPatch解码字节独立diff：业务文件仅在 CmdMetricsShow.run表格分支的 `_show_metrics(...)` 调用补一行：

```python
precision=self.args.precision,
```

原 argparse已有整数precision选项，帮助明确 `after the decimal point`，DEFAULT_PRECISION=5；原helper在None时回落到5，对float执行round(val, precision)。同文件metrics diff原已补传参数。候选沿用已有算法、无固定8位／例子特判／测试改动；默认、JSON分支、repo指标读取、diff业务源码未改。公开issue中科学记数法的两个备选展示方案不能追加有效数字规格。AST独立比较确认 `_show_metrics` 本体修前修后完全相同。

实际业务字节 SHA：baseline=`a15322b578260579b778aacab78dbef930ff616a1fa7099361afdaa1a371a589`，candidate=`eae955c811fd9d2567b64bae39a40c0496d14fe20937cefa1da9cdcdf5981c49`；后者与 Qwen 原 FP中相同文件逐字节相等。baseline canonical SHA=`e9062a880a5d58acc4e0edc5f1fb014cc13c0c5c33daef1e70b35b39451942f1`，HEAD=`daf07451f8e8f3e76a791c696b0ea175e8ed3ac1`；两臂baseline manifest字节相同。两份tar封装SHA不同，不等于基线内容不同；全部547成员的闭合核查复用独立执行报告。

Coder原 FP canonical SHA独立重算=`cc7022fa9a8215627058c0cdca8c0546d783d1d0f6ab56d4a1e4363dcfc5003c`，与baseline digest及实际 projection一致。**原FP和实际projection都含以下四项**，并非一条目候选：

| path | operation／类型／mode | 解码字节数 | content SHA256 |
| --- | --- | ---: | --- |
| `.dvc/tmp/links/cache.db` | add／regular／100644 | 32768 | `830d212dbb01f77aaba066b9f75361e9c3e16d9222353d5f3e7b79d206398d39` |
| `.dvc/tmp/md5s/cache.db` | add／regular／100644 | 32768 | `830d212dbb01f77aaba066b9f75361e9c3e16d9222353d5f3e7b79d206398d39` |
| `.dvc/tmp/updater.lock` | add／regular／100644 | 6 | `f0a4c703ca2a1ca4d921c179752b6ffc27d3eac3a05ae88fd01ae33c7327f7ce` |
| `dvc/command/metrics.py` | modify／regular／100644 | 9855 | `eae955c811fd9d2567b64bae39a40c0496d14fe20937cefa1da9cdcdf5981c49` |

两DB捕获主文件相同，8页／4096B页、WAL格式标记。仅对严格解码的原字节内存读SQLite schema/B-tree，独立得到Settings root3有16行、Cache root5有0行；未改header、未写副本或读取运行时sidecar。此处只证明捕获主文件，不证明完整live缓存、WAL状态或运行时无数据。lock原字节为 `b' 2439\n'`。三个临时Python脚本清理有轨迹结果，三个DVC生成文件却仍在FP；不猜测具体哪一步生成，更不删除后重评分。

raw report的hygiene clean表示本次未触犯测试／forbidden path约束、重放于clean checkout；不等于完整候选只有一行、不等于无生成残留。`git diff`只显示业务源码不能取代原工件；result.source=original_frozen_patch及四项projection保持原样。

## 2. 首请求和完整工具时间线

Coder `solver_prompt.txt`实际2882B，SHA=`255e60e5e83280276d7c3c60389b43871ea487265bd394be6de9ecfb321122d0`，与Qwen逐字节相同。首gateway请求user content有独立306B日期reminder块和2882B题面块；后者精确等于上述字节，包含原CRLF issue与中性brief。不能称整个HTTP body只有题面。brief只含公开环境／公开测试及真实CLI建议，没有新增私测内容。

完整Coder轨迹254条JSONL，attempt与harness副本字节相同。规范assistant tool_use共20个唯一ID，都有对应user tool_result；13 Bash、3 Read、1 Edit、3 Write。stream_event不重复计数。21个gateway请求／响应对应21轮，前20次tool_use、最后end_turn。以下给可定位调用／结果行：

| 调用／结果行 | 动作及真实结果 |
| --- | --- |
| 10／14 | 搜索Python中metrics.*show；命中目标command文件及相关公开测试 |
| 23／27 | Read完整metrics.py，取得helper、show、diff和parser上下文 |
| 36／40 | Read公开单元test_metrics.py |
| 49／53 | 修前单helper precision测试，1 passed in 0.08s |
| 62／66 | 修前公开helper对，2 passed in 0.02s |
| 75／79 | 唯一Edit补传precision，成功，无回滚 |
| 88／92 | 修后同helper对，2 passed in 0.02s |
| 101／105 | Write mock command脚本test_precision_fix.py |
| 110／114 | 跑mock脚本，打印passed；实际断言只有rc0／logger.called |
| 123／127 | 公开metrics command完整单元模块，22 passed in 0.17s |
| 136／140 | 再搜索相关公开功能测试 |
| 145／149 | 功能文件-k precision，exit5／18 deselected，没有匹配测试 |
| 158／162 | Read完整功能test_show.py，纠正选择 |
| 171／175 | test_show_simple＋test_show，2 passed in 0.46s；普通repo指标行为 |
| 184／188 | Write manual_precision_test.py，直接调用helper，无数值assert |
| 193／197 | 打印helper默认／3／8数值 |
| 206／210 | Write scientific_precision_test.py，仍直接调用helper |
| 215／219 | 打印科学记数法helper默认／8／3数值 |
| 228／232 | 删除三个临时Python脚本，正常无输出 |
| 241／245 | git diff仅见业务一行；没有盘点ignored/untracked生成工件 |

## 3. 七维判断与作者报告差异核

**根因与修法。** 源码漏传参数的定位和一行修法成立，符合decimal/default5；raw1不是本判断的语义依据。当前行为评分亦支持，不需扩规格／改断言。

**定位与纠偏。** 完整源码结果后，第3轮已正确解释漏传，与diff正确路径对照；没有错误修法或回滚。Edit第6请求起约5.900s，结果进入下一请求约7.315s。这是可见传输边界，不是内部推理阶段计时。公开题面／brief提供命令和测试线索，不能据此评价无提示的大仓定位能力。空precision筛选后读文件、改跑现有功能测试是实际纠偏，但只纠正测试选择，没有补足precision CLI验证。

**工具使用。** 20调用均有结果；唯一is_error对应筛选exit5，无依赖安装或无效修法循环。再次搜索、单helper后又helper对、三独立脚本有小量重复；工具能完成源码读取和准确编辑。最终git diff是业务变更审阅，不是整个候选卫生检查。

**并行行为。** 每轮至多一个工具，无多工具并发／后台重叠。实现和单元文件读取可批量；两个直接helper例子可同脚本完成。Edit、验证、清理有依赖，测试／command会写同一DVC workspace/cache，不能笼统要求所有验证安全并发。这里仅记录未用少量批量机会，不推断模型无并行能力或精确并行收益。

**验证质量。** 模型自己执行的公开单元模块22项和两个普通功能项通过；helper测试本就修前通过。自建mock虽parse precision8并构造CmdMetricsShow，但只assert result==0、mock_logger.info.called，不核输出／precision／helper转发。按未改helper和旧调用路径，旧实现同样可满足这两个断言；这是静态推导，未实际运行旧脚本。manual/scientific脚本只打印原本正常的helper，AST已证helper本体未变，不能支持“命令修复已被自测验证”。exit5/18 deselected不计precision功能测试通过。没有修前真实CLI失败→修后同路径通过，没有持久新增回归。模型250行最终陈述中“22模块通过”“helper能处理precision”有证据；若“scientific notation works”指CLI则验证不足，“all functionality intact”由22模块＋2普通功能无法保证。**验证陈述过强是非阻断质量观察，不是业务候选错误；grader的真实数值覆盖不补写成模型自主执行。**

**效率与预算。** gateway21响应均HTTP200、attempt1、stream_error=null；实际请求max_tokens均65536，usage累计input279091/output3190，最大单次input18022/output444。累计输入含重复上下文，不表示逼近196608单次上下文。system记录仅init/status，无压缩／恢复记录。solve33.683s来自执行原记录；CC duration30.139s/API24.918s，gateway响应耗时合计24.44s、首请求到末响应30.079s。这些范围不能相减命名纯工具／纯推理时间；CC估算cost1.475205美元不是实付账单。CC metadata32000不替代实际65536请求或说明截断。评分总253.002s／pytest正文0.40s，trusted聚合231.836s是环境成本，不归为模型慢；无保护子步计时，不推断chown。

**结束主张与用途。** 轨迹254行success/is_error=false、end_turn/completed，未见长度／预算或infra中断。执行报告的harness0、manager created1/removed1、gateway drain/revoke/active0、actor/relay/network双层清理及有限资源范围按该报告复用，不重复现场证明。正常完成不保证全部功能、稳定性或训练价值。当前可接受一次正确业务候选及明确验证／工件缺口，不为取得通过重采样。

作者Coder报告SHA `5edb7f640801f59e44bf5ae1c0070c79e5b0f72b858a1bfb321264ee3f0e9650`的上述候选、工具顺序、时间、验证弱点及残留结论可从原件核对，没有新增需返修的实质审计错误。分区精确为**original_f2p1＋added_f2p1＋original_p2p21**；作者“原2个F2P”按原评分工件总数2理解，不应据此写成历史原题有两项F2P。

## 4. 当前评分为何支持候选，且无需改测试

完整eval.log独立重建23个唯一PASSED（757–779行），与diagnostics三分区精确相等；无额外、FAILED、SKIP、missing或unaccounted。完整节点前缀=`tests/unit/command/test_metrics.py::`。23项如下：

| 节点后缀 | 分区 | 结果／eval行 |
| --- | --- | --- |
| `test_metrics_diff` | original_p2p | PASSED／757 |
| `test_metrics_show_json_diff` | original_p2p | PASSED／758 |
| `test_metrics_show_raw_diff` | original_p2p | PASSED／759 |
| `test_metrics_diff_no_diff` | original_p2p | PASSED／760 |
| `test_metrics_diff_no_changes` | original_p2p | PASSED／761 |
| `test_metrics_diff_new_metric` | original_p2p | PASSED／762 |
| `test_metrics_diff_deleted_metric` | original_p2p | PASSED／763 |
| `test_metrics_show` | original_f2p | PASSED／764 |
| `test_metrics_diff_precision` | original_p2p | PASSED／765 |
| `test_metrics_diff_sorted` | original_p2p | PASSED／766 |
| `test_metrics_diff_markdown_empty` | original_p2p | PASSED／767 |
| `test_metrics_diff_markdown` | original_p2p | PASSED／768 |
| `test_metrics_diff_no_path` | original_p2p | PASSED／769 |
| `test_metrics_show_with_valid_falsey_values` | original_p2p | PASSED／770 |
| `test_metrics_show_with_no_revision` | original_p2p | PASSED／771 |
| `test_metrics_show_with_non_dict_values` | original_p2p | PASSED／772 |
| `test_metrics_show_with_multiple_revision` | original_p2p | PASSED／773 |
| `test_metrics_show_with_one_revision_multiple_paths` | original_p2p | PASSED／774 |
| `test_metrics_show_with_different_metrics_header` | original_p2p | PASSED／775 |
| `test_metrics_show_precision` | original_p2p | PASSED／776 |
| `test_metrics_show_default` | original_p2p | PASSED／777 |
| `test_metrics_show_md` | original_p2p | PASSED／778 |
| `test_metrics_show_precision_real_values` | added_f2p | PASSED／779 |

780行23 passed in0.40s，784行RH2_TEST_RC=0。raw report resolved/reward1、F2/2、P失败0/21、无infra，与分区／日志一致；diagnostics install_rc0、未跳安装、无失败命令、完整candidate segment、test0。正式UID54322四wheel prerequisite及R10cb175镜像／清理按独立执行报告复用，不继承R7–R9安装假设。

冻结effective_test.patch SHA=`1acc81a67bca0511b78f515d0d777a00ceeca3725b7907ee741764d1e623540f`：原test_metrics_show检查显式8的转发，以spec绑定helper签名；新增真实数值测试读YAML、parse_args→CmdMetricsShow.run→捕获logger数字，不mock formatter，覆盖默认5／3／8／8+Markdown。这一新增F2P检测了Coder自建脚本没检测到的命令路径。它与一行源码修法相互支持；无需修改材料或为此加新模型样本，也不宣称覆盖所有precision边界／所有替代实现。旧原版固定8位正式reward仍未知，不能从当前两次1倒推。

## 5. 有限两模型比较和当前收口

复用已封存Qwen语义审查（SHA `7cb5056458021160a857b2b7a5687b45cb9138c3628cee94ef1ef6297fb7af84`）及独立执行复核；只另核本次新增Coder候选与差异，不把Qwen重新当fresh读者。

| 可观察事实 | Qwen3.6首臂 | Coder首臂 |
| --- | --- | --- |
| 业务源码 | 补传precision | 同字节同修法 |
| 完整原FP | 仅业务文件 | 业务文件＋3个.dvc/tmp生成文件 |
| 自主命令验证 | 修后真实CLI默认／3／8 | mock断言不足＋直接helper输出，无真实CLI precision验证 |
| 自主公开回归 | 单元模块22项 | 单元模块22项＋2普通功能项；空precision筛选另记失败 |
| 修前真实CLI／新增持久回归 | 均缺 | 均缺 |
| 规范工具／请求 | 14／15 | 20／21 |
| 本次solve秒 | 25.07 | 33.683 |
| 本次累计输入／输出token | 168905／2257 | 279091／3190 |
| 当前正式结果 | 23/23，raw1 | 23/23，raw1 |

独立比较两input_check：task、budget、public_delivery、assignment、baseline_policy、prepared_manifest/host_artifact SHA、材料／grading_revision／grading budgets均相等；solver_prompt字节相同；两diagnostics.scripts_digest=`e5fbf6049fc46649e367fbfb7ae9f0ebc30d47305981d1155f9d6a80567ca2be`相同，FP镜像同 `sha256:cb175daafabb7ab1c5d0e357823057161ae9f0f5bf0a0d3860c7c6a53db72e8f`。关键entry、r2e_solve_attempt、solve_attempt、frozen_transport同字节的执行层核查复用当前固定JSON。

完整runtime仍是Qwen code5/Coder code7，不能说完全同版本。执行报告逐列的7个变化文件为prepared_task_face.py、adapters/slime/replay_grade.py、bundles_v2.py、environment_overlay.py、spec_vendor.py、swe_material_revisions.py、grading/material_revision.py；本轮不重审全树。采样参数／模型服务也不同。这些时间、token、工具数仅描述本次轨迹，不作速度因果排名、普遍能力或题级稳定性判断。

Coder执行报告包含本次before-job operational capture：实际engine/adapter、只读mount、argv/HTTP与checkpoint manifest关联；未重复逐权重SHA／GPU内存权重证明。本报告复用这一执行层结论，不自行复核模型权重。**Qwen无新的fresh per-job capture**，原静态／启动／transport证据保留原范围，不能借Coder capture补成Qwen本次实时权重证明。共同声明gateway1800也不消除Qwen原engine sock_read900生效限制。有限资源采样和diagnostics.resource_facts=null不填零，不升级连续监测。

最新作者双模型总结SHA `227636d8ca1fbf0576e6f2f84e95c1a4bd47c15a08732127f2f717074b967a99`已经修正旧机械重复采样政策，符合实读14:01覆盖优先规则；不再使用本轮先见的旧SHA9d0e版本作当前依据。回执draft=false、root_review_and_board_return_pending=false属于执行回告状态；旧scope中的draft/board untouched文案按原件保留，不由此覆盖当前布尔，也不把executor回告自动当题级全部验收。本核支持题主核收本次首轮，无当前必跑GPU语义依赖；题卡／总账和后续用途由题主按已授权流程更新，本人未写登记或操作资源。

## 6. 实读SHA、依据和未验证范围

作者readback用作导航；候选／轨迹／分区判断从原件重建。以下为文件字节SHA，区别于前文canonical artifact SHA；全152成员核查明确复用执行者，不冒充本轮逐件重核：

| 文件 | 实读SHA256 |
| --- | --- |
| Coder题主完整七维报告 | `5edb7f640801f59e44bf5ae1c0070c79e5b0f72b858a1bfb321264ee3f0e9650` |
| 题主双模型总结当前版 | `227636d8ca1fbf0576e6f2f84e95c1a4bd47c15a08732127f2f717074b967a99` |
| 题主readback | `5bd3906f9f54cfcf7e841366b448b7cfc70dc747a74a5b75dacaa47fa9483f72` |
| Coder独立执行JSON | `a13fc6960500cf69b236bf56bfd6feb294234a5ee10d244e090486b0bd615b8f` |
| 双模型执行回执 | `82aeb40464ceb5c8e83a186f15f4b405c38bf769c4eacd6a2e6961670d30e467` |
| 152件闭合清单 | `fec049a53d42f39419ae97ed4da6a07540563b81988e06842ae8b04660284c77` |
| 原FrozenPatch | `7db7dd112ef3476c706bc060d5d779500da3f5fb283a5da98a0ada93aa8c3b20` |
| 原baseline manifest | `9aa72902e5ed80b571ac0009db445bd350e198f594834da86b22d4f7dead376d` |
| 原baseline tar | `66f37d44b69a5965a06f300396968700db69a8236db8f7dcc58b6f3a5dbffa78` |
| 实际四项projection | `cae98688cd3f715759de5dd61139c506460410b7b794d5612850069d6c8a636c` |
| 完整254行trajectory | `2ef10bcef96e31a44708c57bf00b50f24f5dcd08806be87e4a3e34b51bdd619b` |
| 21请求 | `e0b0e2ad4e5494b0a2dc5f637ca3b73acbfc8e028ac3735de99a01df0a9d071b` |
| 21响应 | `ad06c05db4c594806429713a50b214dae214e0d0622a0703cfdaf3bd75d280e7` |
| 正式report | `d56f72ffd15bf84ef40db957161cffc56635026576b08496a8ead0e0e7d8dc8c` |
| 完整eval.log | `0b1d567ce8ac0db1b684ddcfacb2a8abaddafdb74c7a61ada3f7f5a6031183ce` |
| diagnostics | `57b5ed8972c1db8c5cb4e7e5bc5c5a650a97fb9a846d8dff84a651ba94e4a2e8` |
| 现行覆盖政策 | `03c84f77a8e472e074cf6692f8e28b366075ad6e0ccfd15d3c8efc24a1c7ffcc` |

Coder原件根：`runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-dvc5839-coder-a1/`；首请求／响应根：`runs/ordinary_gpu_probe_20261002/remote/services_v18/coder/gateway/gpu1003-dvc5839-coder-a1/`。轨迹行号见第2节；23参考日志定位见第4节；作者与旧Qwen报告位于本包tasks/reviews目录。唯一新增提交文件是本报告，未修改已冻结证据。

未验证：整个代码树/所有152原件的新独立重审、GPU现场状态／权重／全程资源、历史原版正式分数、真实CLI修前失败复现、Coder自测未覆盖组合、同条件重复稳定性、训练／留出用途。上述限度不伪造补齐，不产生为取得raw1的重采或改断言要求。
