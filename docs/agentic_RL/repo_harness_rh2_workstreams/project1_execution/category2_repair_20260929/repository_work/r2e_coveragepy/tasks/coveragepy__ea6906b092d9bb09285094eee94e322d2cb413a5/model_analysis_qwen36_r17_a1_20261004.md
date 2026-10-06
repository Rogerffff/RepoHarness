# EA69：R17 Qwen 首臂与评分边界

整理：2026-10-04。原 job `gpu1003-coverageea69-r17-qwen36-a1` 属于 R17 当前公开题面，不能与旧 R6 Qwen 混用。原评分 **raw1、49/49、test0**，安装明确跳过、RC 为 null。运输和正常终止成立；候选没有完整满足“所有报告产物被 Git 忽略”的公开目标。新评分草稿为51键，尚未发布或重算完整分数。

## 方法与定位

候选只修改 `coverage/html.py` 的生产逻辑：在 `report()` 完成静态文件后调用新增方法；无文件时写 `/*`，已有文件时保留内容并条件追加。用 `"/*" in existing_content` 决定跳过追加，混淆了文字子串和 Git 的实际规则：注释里的 `/*`、`cache/*`、`!/*`，以及已被后续 `!index.html` 覆盖的 `/*` 都不能证明产物会被忽略。

CPU-A 在与原 GPU 完全相同的 `e23fbbed…` 镜像恢复360项基线和原完整两项 FrozenPatch，实际 UID54321、2CPU/4GiB、网络关闭、无挂载；三臂23组fixture、每组生成两次共46报告。safe_append 10/10；Qwen 6/10。前三种失败均每轮8个报告文件漏忽略，第四种每轮漏 `index.html`；quiet Git exit1及status对应。普通内容、有效规则最后生效、4种CSS文件名均通过。已有内容前缀保留，只是报告忽略行为失败；不以空行、CRLF、顺序、重复模式为新扣分项。

模型两次搜索后读完整生产源码与公开HTML测试，两次Edit后未再修生产逻辑。Git自测第一次错误使用 `git add -f`，它主动stage忽略文件；模型意识到这一点，随后改为未stage的status观察，仍未验证上述已有规则。

## 工具与候选卫生

完整303行轨迹、48条assistant事件、17工具（Bash11/Read4/Edit2），0个tool_result error。公开spy兼容命令仅在本进程转发open参数，原写跟踪断言和46测试均通过；未编辑公开测试或私有控制。

原 FrozenPatch 为 `a237757b…`，含生产html.py及53248B `.coverage` SQLite残留；不能写成“只改html.py”。数据库只读核84个file表路径、2条line_bits、0 arc，全部/testbed来源，无私测/控制路径；84是路径记录数量，与84个公开测试或84个有效覆盖文件均不同。候选没有清理该自测数据。CPU窄验恢复完整DB，但每个fixture使用明确的新data_file，不声称检验原DB污染的全部消费路径。原评分projection确实保留两项。

## 验证质量与并行机会

公开HTML46项跑4次（baseline一次、修改后三次）；`test_coverage.py` 84项跑一次，共130个不同公开用例。另有5个inline断言场景（创建、保留、重复、无末尾换行、嵌套新目录）和2次Git观察，不能和回归数相加。临时source在cwd之外、`Coverage(source=".")`与无filename的exec削弱了采集针对性；但报告与字符串断言实际完成。两次Git观察没有assert/检查子命令RC，后一次还用绝对路径对相对status作文字判断；正常Git空status是有效观察，结尾“全部正确”的说法超出该证据。两次no-data警告及兼容运行的assert-rewrite警告保留。

原正式49键逐项PASSED，footer `49 passed in 1.25s`，原分正确反映旧fixture。新增两方法的八次窄验：baseline两败、safe两过、Qwen CSS过/已有规则败、Coder CSS败/已有规则过。旧49键与旧50草稿方法AST保留；只新加一个已有规则方法，5种输入每轮真实Git检查。此窄验尚非完整51键正式评分。

轨迹每次单工具，独立源码/测试读取、回归可合并；编辑与其验证依赖顺序。init工具列表不含多agent，未测试工具并发支持或估算加速收益。

## 消耗、身份与结束

18次生成加1次count；累计429634输入/5597输出token，峰单次33495/926，缓存0。solve54.147s，CC50.441s/API36.670s，gateway响应累计36.141s；累计输入包括反复携带上下文，不能当作新增文本量。CC标示费用2.288095美元是别名估价，实际租卡/账单未知。actor118.722077s、完整job168.661135s；actor trusted_init40.666s、grader trusted_setup42.901988s说明环境准备占比高，不能把整段当纯模型推理。

模型为 `Qwen/Qwen3.6-35B-A3B`、revision `995ad96eacd98c81ed38be0c5b274b04031597b0`；bf16/TP1，实际adapter qwen3_coder/qwen3 parser，sampling 1.0/0.95/top_k20。实际服务与HTTP读回在任务开始前捕获，37个权重文件数量/大小核，未重复哈希所有权重或做显存权重证明。gateway audit 的 checkpoint false 不是实际capture的身份结论。actor/grader使用code8、同基线/配方/公开prompt19aa60c7…，模型端点是预期差别；历史绑定时间不冒充本job运行时间。

统一probe-wide-v1：10800s、240回合、context196608、每请求max_tokens65536、gateway1024；原CC metadata maxOutputTokens32000与实际请求65536分列。评分whole3600/setup300/apply120/test1800秒。未耗尽任何已知预算。

正常completed/end_turn/harness0，actor和grader清理通过，drain revoked/drained且活动0，pre_drain残余0；pkill1是未找到进程，不是残余。原test marker1.766s、grading test1.958s、total48.817s是不同计时边界。formal grader peak348.84MB；13个资源slice中actor8行仅7行有效，观察峰1057497088B/pids22，有限观测不归因为完整峰或GPU耗用。

## 当前用途与后续

原R17两臂总回执已returned并机械ACK，旧R6 Qwen不改绑。Coder的CSS字面规则失败与Qwen的已有规则失败均已实际复现；单次49/49不能用于完整语义成功率或训练资格。独立核查只审本次新增范围，复用既有Coder结论。

下一步固定51键私有评分修订，普通请求交发布线程登记/冻结/部署，再以原两份完整FrozenPatch作CPU补评分，并验正负控制；没有新模型求解或a2/a3派发。R17评分完整性阻断保留，直到新材料实际消费复验。原报告、原分、历史50键提案均保留。

证据入口：[Qwen原件核](../../../../../../../../../runs/category2_repair_20260929/coveragepy_owner_cpu/ea69_r17_qwen_analysis_20261004_v1/owner_integrity_readback.json)、[CPU边界闭批](../../../../../../../../../runs/category2_repair_20260929/coveragepy_owner_cpu/ea69_r17_qwen_boundary_cpu_20261004_v1/archive_receipt.json)、[51键草稿窄验](../../../../../../../../../runs/category2_repair_20260929/coveragepy_owner_cpu/ea69_r17_criterion_cpu_20261004_v3/archive_receipt.json)。完整路径/SHA及七维结论见同名JSON。
