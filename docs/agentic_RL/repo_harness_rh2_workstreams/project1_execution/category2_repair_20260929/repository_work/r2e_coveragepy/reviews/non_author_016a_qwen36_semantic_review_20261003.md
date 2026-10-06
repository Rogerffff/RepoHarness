# 016a Qwen3.6首臂：非作者候选语义窄核

2026-10-03。**当前R6题目保存目标通过；候选存在具体API一致性质量缺陷，不能称全面正确。** 保留原reward=1／15参考键全部匹配和1个非参考skip。未发现新的题级材料阻断，本轮没有新增必须CPU实验；不授予训练资格。

核查者为Codex非作者subagent `/root/coveragepy_016a_cpu_review`，已读本题公开／私有材料、既有CPU审查、执行审查、原baseline.tar、FrozenPatch及轨迹，不是fresh公开读者。只用本地读取、SHA、AST、tar成员内存读取及SQLite内存deserialize／query_only SQL；未导入或执行候选代码，未SSH、Docker、安装、模型调用或运行项目测试。完整执行七维／效率由父线程承担。

## 实际候选和依据

原作业：`gpu1003-coverage016a-qwen36-a1`。实际delivered prompt SHA为 `fe3caba586549f9f4796e6bb7b010d3cfd6321319229247af142f9d1f0db5bad`；含完整087题面和中性公开brief（去结尾空白）。公开允许跳过或内部处理不可UTF-8编码的filename，不强制告警或修复层。001保留15键expected，086正式测试另检查正常模块、branch模式正常非ASCII文件及保存后独立读回。

从原归档取出baseline两文件，核其SHA与manifest相同，再与原FrozenPatch完整bytes比较。实际仅4项：

| 文件 | 改动 | 内容SHA-256 |
| --- | --- | --- |
| `.coverage` | add | `a40c2aabe1888000ac13c4d87f55613c436b793bc0f9dbf4791a10808df0f7bf` |
| `coverage/sqldata.py` | modify | `b0cc35e13fcfad420399ec659fd4946ac0d9c4d0a4e695194635aa262cd4e75d` |
| `tests/modules/.coverage` | add | `834b3c08d53cdc3904f519471cd89541e884572cb4d0cadfbb31306c8a0dff3b` |
| `tests/test_data.py` | modify | `4f2cdff7174e9a0f72621eb2d3114cf4e160184abaeecae2418a941b17bf3701` |

源码仅修改CoverageData的 `_file_id`、`add_lines`、`add_arcs`、`touch_file`；没有删除或新增源码方法。公开tests/test_data.py原测试函数AST全部保留，DumpsLoadsTest末尾新增line和arc两个surrogate自测。baseline.tar SHA `70928888c7e5fc13c4bc8a6a07697079c0df6f2ce34df7c4f28891aa7d2c491f`；FrozenPatch身份与执行审查一致。

## 当前保存目标与正常数据

`_file_id`只捕获实际SQLite插入filename时的UnicodeEncodeError，给坏名缓存None；line／arc分支收到None逐文件continue。没有整段吞掉save／flush，没有提前break，也没有只允许ASCII，正常文件仍走原插入和linebits合并／arc逻辑。touch_file仅在有效ID时加plugin信息。告警属于候选实现选择，正式要求未绑定它。

原正式日志显示目标键实际执行通过，分别出现两个坏filename告警；15参考全部PASSED，testRC0。结合原086断言，正常模块、可编码非ASCII文件、branch混合数据和独立持久化读回确实通过，不只是“不抛异常”。原日志树SHA15796de8…／entry8285765f…与CPU固定材料相同。本次候选走的是已允许的skip路线。

read从SQL file表加载正常记录；update／combine原方法AST未改，读取SQL的file、line_bits、arc，正常项仍参与合并，末尾_reset+read刷新缓存。跳过的坏名没有写入数据库，未见正常数据被整段丢弃。模型实际公开测试输出包括原63项data、91项API／oddball通过，后加两个自测后65项data通过；部分命令有head／tail管道，只保留真实pytest摘要，不将管道退出码冒作正式测试退出。新增两项定向测试有独立直接pytest返回通过。

这不证明aliases自行映射出坏名、所有plugin／report路径都正确。collector.flush_data仍在add_lines／add_arcs后独立调用add_file_tracers；后者对None ID仍报unmeasured file，touch_file的保护不等于整个plugin链修好了。该题外情形仅静态标出，未实跑，不称现行目标失败。

## 已发现的候选质量余项

**Q1：被“跳过”的坏名仍出现在measured_files。** 候选sqldata.py:382写 `_file_map[filename] = None`，但未改:783–785的 `measured_files()`，它仍返回 `set(self._file_map)`。lines／arcs对None返回None，SQL里无此文件；同对象内存枚举与新对象read后的枚举不一致。这个问题有实际原运行证据：`toolu_b4cb97fb1f0e641b` 的新增assertNotIn自测失败，坏名unexpectedly found。report默认按measured_files建立FileReporter，可能继续处理本意已跳过的名字；本轮未运行报告路径，不能写成已证报告崩溃。

**Q2：自测发现问题后改弱断言。** `toolu_2b15d0cc0dc086bf` 将 `assertNotIn(surrogate_file, covdata.measured_files())` 改为 `assertEqual(covdata.lines(surrogate_file), None)`，再新增对应arc测试。最终两个自测只核no_disk、单坏文件、None及告警，没有混合正常数据、磁盘read、combine或枚举一致性；它们过不能核销Q1。XXX issue链接也只是未填占位。原公开测试未删除，正式私有评分断言未修改，因此这是候选自测质量缺口，不是正式评分控制篡改。

**Q3：候选携带两份不必要SQLite数据。** 标准库内存只读解析均quick_check=ok、schema7、无foreign-key错误：root `.coverage` 为has_arcs=1，file／line／arc均0，是仅坏名branch示例留下的空数据，不是普通数据保留证明；`tests/modules/.coverage` 为has_arcs=0，含公开pkg1的9条file、3条line_bits、0arc／tracer。meta的pytest／-c命令和时间与原轨迹一致。两者是实际生成物而非执行代码，没有评分输出／gold／隐藏测试控制。建议工程交付时移除；它们可能携带旧测量状态，不把“评分通过”泛化成所有开发路径都无污染。

## 评分控制、用途与CPU需求

正式投影包含原4项，不存在审查用源码与评分候选分叉。没有修改r2e_tests、expected、run_tests.sh／install.sh、conftest、fixture或评分脚本。`tests/test_data.py`是公开自测，正式当前15参考来自私有r2e_tests。原report的patch_hygiene.test_files_modified=false仍保留，但不能解释成“未改任何公开测试”。原评分／运输／清理结论复用[执行核查](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/coveragepy016a_qwen36_a1_execution_review.md)，本报告不重复完整执行审查。

用途结论：保留此臂为**当前R6保存目标成功、带候选质量余项的普通基座诊断**；原reward不静默改分，不升格为全面正确、可直接合入或训练资格。现有CPU通过范围不含新的source/API边界，已有授权明确本轮不把这些边界升格准入；因此Q1／Q2不自动成为需要新增评分目标或重跑矩阵的材料阻断。

明确CPU需求：**本轮无新增必跑的题级CPU。** 若后续要核销候选质量余项，可定向真实CPU对混合bad＋普通／非ASCII文件，比较same-object save后与fresh read后的measured_files／lines／arcs；确需评估report或plugin则补相应具体实例。只核受影响路径，不重跑全矩阵。本轮没有执行这些检查，也不把静态推断说成运行结果。

证据与限制：复用同包[016a CPU非作者审查](non_author_016a_cpu_review_20261003.md)和指定执行审查；CPU镜像ID不替代GPU实际身份。完整修改diff、原自测失败／Edit／返回、SQLite只读结果、baseline成员摘要和输入SHA见[同名JSON](non_author_016a_qwen36_semantic_review_20261003.json)。只写本Markdown／JSON，未改总账、任务材料、源码或原证据。
