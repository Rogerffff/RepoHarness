# 016A Coder首臂：题主七维分析

2026-10-03。**当前R6保存目标满足，原reward1、15/15保留；候选数据库确有一条无文件归属的行数据，自测脚本也有假成功风险，不能称全面正确或直接合入。** 两模型各一次首轮均已回传并ACK；本轮无新增必跑CPU或题级材料阻断，不授训练资格。

固定001+086+087、R6、作业`gpu1003-coverage016a-coder-a1`。完整身份、原件SHA、全部工具参数/返回索引及资源见[JSON](model_analysis_coder_a1_20261003.json)。[非作者语义窄核](../../reviews/non_author_016a_coder_semantic_review_20261003.md)沿用非作者上下文，未新跑CPU/SSH/Docker/模型；执行核查另在GPU原回执中。

## 修法与根因

仅在`_file_id`的SQLite插入捕获UnicodeEncodeError，告警使用repr，返回None而不缓存坏名。没有整段吞掉save、break或排斥正常非ASCII。正式086支持正常数据、branch非ASCII及独立持久化read，当前目标成功。

后续add_lines/add_arcs没有检查None。只读原FrozenPatch的`.coverage`确认`line_bits`中一条`file_id=NULL`数据行，同时正常`normal.py`的文件项存在；这已经是实际保存原件的问题，不只是静态风险。它不改变当前保存/read目标原分。与Qwen不同，Coder未缓存坏名，源码上避免了Qwen的measured_files枚举不一致；本臂未新增枚举运行核查。`add_file_tracers`在无file_id时抛异常，touch_file带plugin仍调用它；这一坏名plugin路径未实际执行，只列静态风险，不称已证再次崩溃。

## 定位与纠错

第三个工具L36复现编码失败，返回距首gateway生成2.293秒；L54直接解释SQLite插入根因。L97先成功写入hash替代方案，L106自行判断过复杂，转skip/warn；没有运行验证hash方案。L110用过时old_string改失败，L123/L132读回后L145替换完整方法，L162同例不再崩溃。L141“部分应用”解释不准确：上次编辑实际完整成功，是下一次编辑仍引用原文。

## 工具使用

30调用：Bash17、Write4、Read6、Edit3。三条is_error分别是原例预期失败、过时文本替换失败、Git身份未设置；后两项均收尾。整份sqldata/backward及泛化编码检索在直接traceback之后增加上下文，后续短读有效确认编辑状态。L313读回和L322 diff核最终源码；三次重复长总结未增加验证。源文件最终在actor内提交，但所有四个未跟踪helper及两份SQLite仍进入正式FrozenPatch，不能因Git commit只列一文件就称交付只改源码。

完整候选没有修改既有公开tests，也未改runner/conftest/私有评分控制；新增四个根目录验证脚本和两份数据库保留。`patch_hygiene.test_files_modified=false`不能单独证明没有测试改动，结论来自全部七项投影与diff。

## 并行机会

模型没有同一助手消息内多工具批次，不能证明或否定模型并行能力。独立读取/检索可合并，修改后验证和提交有依赖，须有序。两次单节点pytest输出gw0/gw1/gw2，是测试runner自身并行，不是模型多工具并行；无实际节省时长证据。

## 验证质量

原例先失败，最终源码改后无崩溃；普通helper保存成功。三个公开模块154通过1跳过，用时2.43秒；随后普通adding_lines与adding_arcs各1通过，均已属于154集合，不是坏名branch新覆盖。comprehensive脚本只验证分别保存不崩，未断言内容或fresh read；其测试函数返回False本身不会使pytest失败。final_test三段except Exception只打印，末尾无条件“全部成功”且退出0，是弱判据；本次实际三段均成功，不能说模型掩盖了实际失败。

混合正常/坏名示例实际成功，但缺正常数据断言；目标所需的混合数据与独立read由正式086支持。没有为既有tests新增持久回归，四helper、SQLite均是工程交付余项；部分helper顶层save会在导入时写默认数据库，更宽测试收集时有静态副作用风险，本次未复现。末尾“all existing tests”仅这三个模块，不能称全仓回归；warn读取和检索也未独立验证回调策略。

## 完成效率

| 口径 | 实际值 |
| --- | --- |
| 累计输入／输出token | 708679／5496 |
| cache read／creation | 0／0 |
| 生成HTTP／count_tokens | 31／1 |
| CC回合／工具调用 | 31／30 |
| solve／CC wall／CC API秒 | 57.462／54.044／47.253 |
| gateway生成响应累计秒 | 46.490 |
| actor开始至清理收口秒 | 104.492 |
| trusted init／Git sanitize秒 | 25.482／2.183 |
| grader总计／实际测试秒 | 32.552／2.677 |
| grader peak_memory_mb原字段 | 283.938 |

观测输入峰值31234、单响应输出峰值632；实际每条gateway max_tokens为65536，CC元数据32000不替代wire生效值。gateway累计含运输/adapter，不是纯GPU推理；CC非API残差6.791秒不等于纯工具执行。actor7次、relay7次、grader2次有限资源切片，间隙未知；grader峰值字段与采样memory.peak来自不同来源，不能混写。CC估价3.680795USD为别名估计，实际账单未知。

## 结束、用途与接续

completed、CC success/end_turn、harness exit0、正式testRC0，无预算截断；另1非参考SKIP保留，安装明确跳过，installRC为空，不称安装复验。当前可作“保存目标成功且代码质量有余项”的版本化普通诊断。两首臂只证明两份候选，不证明同条件稳定或训练资格；按统一第二阶段策略每模型再两次，先未覆盖/缺臂、自然同模型批边界。无需重跑历史CPU矩阵，若后续确有具体新材料缺陷再定向处理。

Coder固定revision `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`、BF16/TP1，采样0.7/0.8/top_k20/repetition_penalty1.05；Qwen模式与采样不同，不能当同内部计算排名。code_snapshot_id、grading_materials_identity与env qualification缺项保持。实际配置上限不等于196K峰值实测，未重复weights文件SHA或验证GPU显存内逐字身份。全部失败、原分及候选保持。
