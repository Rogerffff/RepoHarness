# F5EB Coder 首臂：题主七维分析

2026-10-03。**当前A/rb3h语义与8参考键均通过，原reward1保留；生产只加totals两字段，公开测试同步合理。** 两模型首对已returned/ACK，未发现新材料阻断或必跑CPU；交付仍留调试产物，开发失败和验证限制保留，不授训练资格。普通追加采样按GPU覆盖优先安排暂缓。

作业`gpu1003-coveragef5eb-coder-a1`，R6/076+077、196608/65536的probe-wide-v1。完整身份、指标及41个工具参数/返回见[JSON](model_analysis_coder_a1_20261003.json)，[非作者语义核查](../../reviews/non_author_f5eb_coder_semantic_review_20261003.md)与GPU执行核查分别核候选和运输/评分。本轮只读已有原件，无CPU/SSH/Docker/模型/重评分。

## 修法与根因

在原`coverage_data.has_arcs()`的totals块加入`self.total.n_executed_branches`、`self.total.n_missing_branches`。`report_one_file`仍逐报告文件累加Numbers；covered为总目的地分支数减missing，未拿partial行数替代。使用数据是否有弧而非当前report对象的branch配置，支持保存后读回；原report子集仍限定总计。正式8键支持保存数据、非示例分支弧、多文件/子集和零分支。

每文件summary不增加可选两字段，符合用户已选A；Qwen增加成对正确字段也符合A，不判其中一种更正确。公开`test_branch_coverage`只向totals完整预期补1/1，四方法、原精确比较和旧字段均保留。没有隐藏评分/runner/conftest控制改动；不能凭hygiene字段false说没改公开测试。

## 定位与纠错

L27的源码返回已给准确缺字段位置（距首请求1.180秒）；L45却误称公开预期已有两字段，L75和L101改前1/4pass及源码否定该说法。L123把outfile误作file对象；改路径后L145执行同作用域语句无测量数据。L184改临时文件导入后L193真正复现缺字段，21.079秒。

正确复现后，L202/L211又重复先前outfile/无数据错误；L224忘记start，返回branch=false/0-of3，不能作为分支证据。L254直接调用公开测试，捕获异常仍退出0，本次确实通过。L280误传Numbers的n_executed参数，L289修正得到1/1，L294形成正确判断，L302完成生产修改（38.540秒）。定位信息早已具备，反复复现占用步骤；这些到达时间包含推理/工具/运输，非纯思考时长。

## 工具使用与并行机会

41调用为Bash25、Read7、Write5、Edit4，9条is_error：outfile两次、无数据三次、Numbers构造一次、公开预期字典差异一次、空测试集两次。生产修改一次成功，后续不改生产；格式差异后同步预期是合理开发反馈，不称作弊。

find扫到.venv、整Numbers和测试基类读取及多份临时脚本扩大上下文，结尾两次长总结重复。L490删除五个test/demo脚本，FP仍保留a.py、三个JSON、.coverage及两份正式改动，合计7项；没有题主另修候选来替代正式原件。

没有同一助手消息内多调用批次，不能证明或否定模型并行能力。独立源/测试读取可合并，源码修改和后继验证须顺序；测试可能共享默认覆盖数据库，不机械并行。pytest输出gw0/1/2属于项目xdist，不是模型多工具并行，也无节省时长实测。

## 验证质量

改前JSON4通过，正确临时导入示例确认缺字段；改后原完整预期1失败3通过，再补两字段后4通过。test_report与API -k json各空集rc5，不能记为扩测成功。results35通过，最终合并JSON/results39通过是4+35的并集，不另加成78项或全仓回归。

非branch示例实际无两字段；末尾同作用域“exact example”再次无数据失败，随后临时函数导入demo实际total1/1成功。多数demo只打印存在与值、失败分支也不主动nonzero；不代替精确保存/多文件/子集测试。原a.json保留未start导致的0/3、branch=false，是失败开发路径副产物；demo和nonbranch JSON分别对应实际成功输出。

根SQLite是final_demo留下的临时文件8弧，无NULL弧，临时源码已被模型删除；它与a.py/JSON都应从未来生产整合交付剔除，但这里完整保留原FP。默认数据文件含已删除临时源码路径，后续显式load/CLI报告可能受影响，这是消费关系推断的工程风险，未运行复现；正式rb3h用自身临时fixture及显式data_file，不消费这些根调试文件。没有新增现行评分污染或生产阻断，无须重跑CPU矩阵。

## 完成效率

| 口径 | Coder实际值 |
| --- | --- |
| 累计输入／输出token | 770729／8213 |
| cache read／creation | 0／0 |
| 生成HTTP／count_tokens | 42／0 |
| CC回合／工具 | 42／41 |
| solve／CC wall／CC API秒 | 81.393／78.067／66.643 |
| gateway生成响应累计秒 | 65.852 |
| actor开始至清理收口秒 | 129.548 |
| trusted init／Git sanitize秒 | 25.912／2.196 |
| grader总计／实际测试秒 | 31.560／2.322 |
| grader container_peak_memory_mb | 268.148 |

输入峰值28533、单响应输出峰值643；实际gateway max_tokens65536，CC元数据32000不替代生效值。CC非API残差11.424秒不是纯工具时长，gateway累计含adapter/运输，不是纯GPU推理。CC别名估价4.058970USD，实际账单未知。13个有限宿主切片，未采间隙未知，不把共用GPU利用率归因单题；grader报告内存峰值按自身来源保留。

## 结束、同条件边界与用途

completed、CC success/end_turn、harness0、正式testRC0，无截断，安装明确SKIPPED/RCnull。actor/relay/network、gateway drain、静止屏障和grader关闭已核；174原件/11,078,409字节题主SHA/bytes复核一致。原评分只表示8键匹配，结合完整代码语义才支持本次目标成功；单次不支持稳定能力或训练资格。

两模型同材料、镜像、基线、公开prompt/brief、评分脚本和预算实值；实际Qwen code4、Coder code7，保留共用材料/评分消费者等差异，不能称整树逐字同版。关键entry/solve/frozen运输源一致，本题prerequisite为空，执行方复用既有差异窄核。Coder实际adapter仍code4，BF16/TP1，revision b2cff646eb4bb1d68355c01b18ae02e7cf42d120，采样0.7/0.8/top_k20/repetition1.05；Qwenthinking/采样不同，不作相同内部计算排名。

code_snapshot_id、grading_materials_identity与qualification缺项保持；gateway checkpoint_identity_verified=false保留，启动及前后inspect/只读挂载/配置/文件大小绑定不是GPU显存逐字证明，未重哈权重文件，engine sock_read900未改。上下文上限不等于196K峰值实测。下一步普通重复按覆盖优先暂停，保留各a1，恢复时按固定材料和各模型条件额外2次补总3次；本轮没有新重复执行或提交。
