# Project-MONAI__MONAI-1121 历史差异核对

root 在核验并封存本包全部初稿后明确 history release。本次只读取 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/history/Project-MONAI__MONAI-1121/refs.json` 精确指向的 `/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_monai_1/records/Project-MONAI__MONAI-1121.json` 全文，SHA256=`3b6d2003342f6bc369a7320d2d2a04a6964293e71adcc708329cb367dc45c0a9`；未沿历史记录链接读旧日志、索引、别题、汇总或reviewer。以下旧日志数字/报错如无本次授权原运行独立支持，均是旧记录自述，不能提升为本次运行事实。H/路径表示该历史JSON指针；P/S/V缩写同初稿。

冻结初稿SHA256=`2711d42d4bd6f6d02276d579d30492219afcc1ddd131d2110b0a7cc69fd0d062`；未改写。证据级别是静态源码推导、旧记录主张、或V/run_refs授权历史真实RH2，三者分开；本轮未执行项目/测试/安装/网络/模型/任务二。实际actor仍unknown，成本未观察null，reviewer未读。

## 逐项对照历史原文

| 历史位置/主张 | 本次判定 | 决定性证据与处理 |
|---|---|---|
| materials_refs：base、F2P、35 P2P、6测试文件、gold仅ahnet；checks1/2 | 确认本题身份与目标失败；旧stage1数字未独立重读 | V/grading与patch相符；新授权materials-v1 noop在ahnet.py:231报float属性接收int、gold该F2P通过。旧stage1日志不在本次release精确路径内，旧28/27通过等数字只作为旧记录自述 |
| checks3：没有AHNet点名/traceback，所以实际输入有问题；23“公开完全推不出F2P” | 收窄并纠正编号/措辞 | 公开请求要求所有网络TorchScript回环，公开源码能枚举网络并设计导出验证，未点名根因不等于不可解。实质问题是测试交付冲突和全网络目标被局部评分代替，归23/25。真实消息未获，3=unknown；原始hints_text空不能替代当前public_hints或actual消息 |
| public_view / checks4、23：题面补测试与禁改测试冲突 | 确认条件性冲突 | P/public_bundle明确禁测；历史grader实际恢复6测试路径；尚不知actor收到哪组指令。不得直接把公开任务改写成AHNet根因提示并称环境修复 |
| checks4/17、file_rules：测试恢复与gold不交叠、additional_exclusions空 | 确认历史该候选局部路径 | 原noop日志588–622恢复+apply；gold projection仅ahnet.py。仍不证明任意测试型合法候选交付；额外排除保持[] |
| checks5：26题无重复、提及另一题同族 | 未核 | 没读dupidx、其它题/汇总；同文件唯一也不能充分证明无派生/评测重叠，5=unknown |
| checks24：任意替代实现都能过，例如加类型注解或删dropout | 收窄 | 断言不查源码布局成立；未运行替代解、注解不保证消除脚本编译错误。删不可达dropout逻辑可讨论但不能据此证明合法解普遍不误拒。24=unknown |
| checks25：默认upsample_mode='trilinear'，F2P走PSP else，两处gold均被覆盖 | 纠正 | S/ahnet.py:377默认是'transpose'，new test未覆盖非transpose执行分支。PSP构造默认trilinear不能替代AHNet显式传入的模式；新F2P不能当该else数值回归证据 |
| checks25/26、proposed_regression_tests：要求AHNet(dropout_prob>0)输出不同、删dropout属于破坏语义 | 纠正 | AHNet公开签名没有dropout_prob；Pseudo3DLayer原forward无条件归零，所以比较“非0应生效”会新增原题未要求行为。旧shape覆盖缺口归25，不是26已证gold回归；26=unknown |
| checks27：gold正确完整 | 收窄 | ahnet两处局部修复有静态/历史正证据；并不交付所有网络新增测试。初稿已经区分局部正确与整体完整性，不沿旧pass批准全题 |
| checks29：无泄露 | 收窄 | prompt未含修复补丁可确认，但actor实际可见工作树/消息/网络未知，29=unknown；本审查见gold/隐藏测试/历史须单记usage |
| checks6/7/11/20、offline_blocker：8项P2P下载失败，gold无分差，先预置权重 | 对新授权条件已过时；旧失败事件未独立核原日志 | materials-v1 deny_all、numpy1.23.5条件下40项全部完成，gold1/1且35 P2P全过；预训练路径实际通过。证明该grader条件解决这些路径，不证明actor缓存位置或可访问性。不得删8项P2P代替修资产 |
| checks18/test_collection_noise：6个test_script_save被pytest收集，fixture net缺失 | 确认静态机制，旧错误仅历史记录级证据；新条件收窄 | 原test.patch顶层test_* helper确有误收集可能；旧记录明确列6项error，为初稿提出的收集差异提供旧解释。materials-v1实际仅40项、无error，未读取该配方的完整冻结实现，所以不宣称已验证如何修收集。不能靠忽略错误总数证明所有目标都执行 |
| checks9/image_dependency_drift：np.int造成Discriminator4项失败但不计参考 | 新授权条件已过时；编号纠正 | 新授权原日志显示4项全部PASS，numpy1.23.5；expected仍不含这4项，是评分覆盖范围问题。旧np.int失败属依赖兼容6，不直接证明9候选代码未生效 |
| proposed_regression_tests其余：旧shape与脚本保留；将离线2项代替下载8项 | 保留已有窄回归，拒绝自动削减 | 本轮所有相关原断言已读；材料条件已让预训练测试通过，没理由静默剔除；脚本自比也不能单独防全局劫持 |
| disposition needs_repair、costs.minutes=26 | 不沿用旧资格/成本 | 现态needs_review/static_review，题意优先；该分钟数属旧作者工作，不是本轮观察，当前costs=null |

## 对冻结初判的影响

初判主要结论不变：目标/交付错位优先于环境或模型探针。旧记录帮助解释原test_* helper为何可能造成6项收集错误，但当前materials-v1如何修复的实施证明仍缺，故维持有范围的unknown。新增明确纠正旧AHNet默认模式与dropout回归要求；不把旧“缺定位线索”当不可解定论。原初稿未经修改。

唯一优先下一步保持：由任务拥有者统一“所有网络新增测试”的公开目标、合法交付与验收范围；不先重跑CPU/模型。该建议不是本轮修改题目授权。
