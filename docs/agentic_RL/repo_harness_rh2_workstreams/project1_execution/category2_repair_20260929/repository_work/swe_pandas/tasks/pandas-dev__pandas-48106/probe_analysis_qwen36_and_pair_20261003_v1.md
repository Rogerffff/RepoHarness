# 48106：Qwen3.6首轮与两模型对照

2026-10-03 23:36 SGT。适用于 Qwen job `gpu1003-pandas48106-qwen36-a1` 及已验 Coder job `gpu1003-pandas48106-coder-a1`。两臂消费同一公开任务、baseline和正式材料 `pandas48106-complete-bindings-e19-v1`，各一次，均正常结束。作者已逐件重算新增Qwen快照229件、177,875,796字节，所有大小/SHA一致；旧Coder作者和独立审查按其既有范围复用，GPU在本次总回执另记录旧546件再次核SHA。新增非作者窄核另存，不将作者分析冒作其结论。

**两模型都是可靠的部分修复／语义失败，原0分均可信。** 两者均修好了数值0插入的公开样例，却把应保留的类别变为object，剩余15项F2P未修好。Qwen确实比Coder运行了更多有效公开pytest，并纠正了错误测试路径；测试数量和工具成功没有使它识别缺失值与类别元数据的验收目标。这一对照支持“验证目标和边界断言不足”的有限能力观察，不支持稳定失败率、模型总体强弱或训练增益结论。

## 原评分与实际补丁

| 范围 | Qwen结果 | 与Coder的关系 |
| --- | --- | --- |
| 公开数值样例 | 新元素0、dtype object；F2P1/16 | 同样修好这一例 |
| 插入已有类别值 | 失败1项，object与category不符 | 同一个未修好目标 |
| 数值扩展类型类别插NaN | 失败10项 | UInt/Int/Float参数与Coder相同 |
| 缺失值扩大／原位置赋值一致性 | 失败4项 | 同一组None/nan/na1/na3 |
| 来源P2P | 1020/1020成功，缺席／跳过／未归类0 | 同一参考与五组13个完整绑定成员均PASSED |

原 `reward=0/unresolved/tests_failed`，安装RC0／测试RC1、execution/infra failure null。物理pytest为15失败、1029通过、1 XFAIL，4.94秒；来源1020 P2P对应1028个完整PASSED物理节点，不能把两种计数混为一个分母。逐失败traceback均为dtype不同，F2P成功／失败列表与Coder逐字相同；这些是原F2P未修好，不是新增15个P2P回归。

Qwen仅增加一个无条件 `isinstance(dtype, ExtensionDtype)` 分支，直接返回object和原值；它位于原 `isna(fill_value)` 分支之后。已有类别值被新分支强制转object；缺失值先走旧NA分支，同样丢失category。仅收窄新分支也不能声称NA问题已解决。这个条件还覆盖其它ExtensionDtype，范围比Categorical更宽；本轮正式P没有新增失败，不把静态风险写成已发生回归。模型演示Int64／DatetimeTZ／Interval三种具体插入仍保留dtype，也不能证明所有直接promotion调用都不受影响。

完整FP为 `sha256:46b9e4d2ffdda1fd752eaf4bbca5a1bc2886be11cd5bf0b8bf706a97e1d62123`，baseline与Coder相同，为 `sha256:e3b6318de246349fb5314e4a1c93e90fd05f3756350ca1ddcff56804df10ab49`。仅两个成员：修改 `pandas/core/dtypes/cast.py`，新增 `test-data.xml`；后者是最后四项公开DataFrame pytest生成的报告，两项均在正式projection中。没有修改正式测试／conftest或评分保护面，不称为整个候选只有五行源代码。

## 定位、纠错与测试边界

行号均指原 `attempt/trajectory.jsonl`，不是去流式重复副本。

| 原行／工具 | 实际行为 | 判断 |
| --- | --- | --- |
| 15–24，工具1/2 | 并行读取indexing调用点与cast局部源码 | 有具体调用链定位，没有先完整读取整个cast文件 |
| 38–154，工具3–11 | 发现Categorical没有numpy_dtype；检查类型；复现 `_ensure_dtype_type` 的metaclass构造异常 | 两次探索调用错误后纠正；根因定位成立，异常不是缺环境 |
| 168–177，工具12/13 | 同时读helper及检索ExtensionDtype使用 | 第二组真实批量工具并行 |
| 205–259，工具15–18 | 原样例复现；一次Edit新增广泛fallback，样例立即修好 | 没有Coder的先丢值再撤回过程，但最终条件仍过宽 |
| 273–291，工具19/20 | 自测打印NaN插入后object；第一脚本被不允许的iloc扩大中断，再去掉该项重跑 | 已观察缺失值dtype变化，却无category断言；测试字符串用类别外`d`，没有已有类别`a` |
| 305–395，工具21–27 | 跑公开categorical；选错 `test_maybe_promote.py` 后报选项错误；搜索到真实 `test_promote.py` 并跑1427通过 | 确有路径恢复与有效pytest，不能沿用Coder“pytest未恢复”的结论 |
| 405–493，工具28–33 | 再跑astype、loc setitem、DataFrame categorical；演示三类EA与原例 | 旧公开路径通过，但没有补类别内值／NA类别保留目标 |
| 503／507 | 最终以“All tests pass”结束，声称不影响其它扩展类型 | 完成声明超出已覆盖范围；正常end_turn，非预算截断 |

八次pytest调用中，一次是不存在路径的选项错误；其余原stdout分别有113、25、72＋1 XFAIL、1427、17、199、4通过的完整footer。不同selector和模块之间可能重叠，不把这些数相加为唯一覆盖或成功率。命令均接 `head`／`tail` 管道，没有单独捕获pytest退出码；错误调用的tool `is_error=false`实际是管道表面成功，不能当pytest成功。成功footer仍是已运行测试的有效观察，不因没有独立RC就全部否认它们。

16项正式F2P对应的四个测试函数名均不在实际公开baseline的 `test_loc.py`，而由受信评分补丁加入。Qwen无权在公开环境运行隐藏测试，不能以“没跑隐藏测试”指责它。可判断的缺口是没有依公开category语义自己设计已有类别值和缺失值的dtype断言，自测已打印NaN变object仍未追问。大量旧测试通过与15个新目标失败因此不矛盾，也不构成删减正式参考的理由。

## 效率、并行与评分成本

| 指标 | Coder首轮（既有已验） | Qwen3.6首轮 |
| --- | --- | --- |
| 求解墙钟 | 135.975秒 | 96.005秒；CC92.336秒、API52.936秒 |
| 实际生成请求 | 42 | 32；原gateway请求／响应32条逐一HTTP200，无stream_error |
| CC记录回合／工具 | 42／41 | 34／33：Read6、Bash26、Edit1；工具error3 |
| 累计input／output | 1,807,416／12,378 | 500,628／8,526；cache0，单请求已报告input峰值24,017 |
| 工具并行 | pending峰值1 | pending峰值2；两组各两调用，余下串行 |
| 正式评分总耗时 | 1241.206秒 | 1199.113秒；受信准备796.779秒，评估包装329.294秒 |
| 原安装／测试包装／pytest自身 | 323.765／7.665／4.76秒 | 319.988／7.830／4.94秒 |

Qwen的34个CC回合不能冒写成34次生成：32个assistant message ID及gateway生成中，两次响应各包含两个工具调用，合计33工具加终结回合。累计input不是单次上下文；本次所读源码较窄、生成和输入总量较少是实际记录，单次不能归因为模型普遍更高效。两臂都有Bash/Edit/NotebookEdit/Read/Write，没有子agent入口；Qwen用到了批量工具能力，跨agent能力仍不可评估。

原宽预算仍为196,608上下文、65,536输出／响应、240回合、10,800秒求解；gateway实际32请求输出上限均65536，未看到预算耗尽。CC `maxOutputTokens=32000` 原元数据不改，不能反推截断。queue_wait字段0不等于用户总等待0；受信准备、后续安装、测试包装及pytest自身分列，不将329秒称为纯测试。清理／parser计时原null保持。

## 身份、收尾及用途

实际actor仍原source `0e706113…c4b8`，grader为固定E19 `53b17fe2…860a`；当前job精确名字／run_id匹配14个actor、80个grader采样，各角色容器ID稳定。采样有未知间隙，不推全程资源状态。code_v8、材料 `15859c…4315`、bindings及实际NoOp资格 `ok:noop_ledger.jsonl:rpt_grading_3268a121` 与Coder一致。actor／grader清理true，manager创建1／移除1、无open/supply；gateway revoked/drained且active0。当前完整RC0与精确PID1 journal的systemd成功终止相符，不用默认0或历史终态代替本job结束证据。

同期engine／adapter及服务读回绑定 `Qwen/Qwen3.6-35B-A3B`、revision `995ad96eacd98c81ed38be0c5b274b04031597b0`；下载manifest原 `files_count=40`、实列37条，与现场37条大小相符。保留这个计数差异，不推丢权重或40件全部已核；没有重复大权重SHA或GPU显存权重认证。原 `checkpoint_identity_verified=false`、input-check仅配置的运行标记及 `compile_probe=null` 保留，不升级训练typed actor或训练资格。

本题两模型各一次的执行已returned；作者成对分析完成，新增Qwen非作者窄核另留报告。当前没有需改材料、重跑CPU或重解模型的问题；正常失败保留为可解释的诊断样本。旧全量三次不自动继续，是否增加少量采样仍需围绕明确不确定性按现行覆盖优先裁定。50319缺模型首轮是本包下一项在途工作；48106闭合诊断不等于训练准入或所有未来回归已穷尽。

## 新增证据入口

- [两模型总回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/probe-swe-pandas-48106-20261003-v1_pair_execution_receipt_v1.json)：SHA `d207c88635ee7f7d7d9f5bd2856665a0e933f1ea4d8eb5d2d2d594708ab6c6f0`。
- [本臂机械回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/pandas48106_qwen36_execution_receipt_v1/execution_receipt.json)：SHA `3ccedb8ccf5da4d291ee5ba65db39f8352b51ca7f20074adc4095671c65a455b`。它只对账执行，不代替本分析。
- [作者核验与计数原件](../../../../../../../../../runs/category2_repair_20260929/pandas_cpu_20261003/gpu_analysis_20261003/pandas48106_qwen36_a1_v1/evidence.json)：SHA `64e57e539630f6b51844d7d9304f08fb16443a9930a805ede67b61a7cb43f630`；[轨迹阅读副本](../../../../../../../../../runs/category2_repair_20260929/pandas_cpu_20261003/gpu_analysis_20261003/pandas48106_qwen36_a1_v1/trace_normalized.json)、[源diff阅读副本](../../../../../../../../../runs/category2_repair_20260929/pandas_cpu_20261003/gpu_analysis_20261003/pandas48106_qwen36_a1_v1/source_delta.patch)。
- [原候选diff](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pandas48106-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-pandas48106-qwen36-a1/attempt/candidate/pandas-dev__pandas-48106.diff)、[原评分日志](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pandas48106-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-pandas48106-qwen36-a1/grading/eval_logs/evallog_gpu1003-pandas48106-qwen_82c7dbba.eval.log)、[既有Coder分析](probe_analysis_coder_20261003_v1.md)。所有原件不回写。
