# 016A Qwen 首臂：题主七维分析

2026-10-03。**原评分1／15参考键全匹配，符合当前保存目标；候选留有measured_files不一致、自测断言弱化及两份SQLite生成物，不能称全面正确或直接合入。** 当前仅Qwen首臂已完成，Coder未执行，活动请求未按双臂完成ACK。本轮不授训练资格。

固定材料R6／['r2e-mr-001', 'r2e-mr-086', 'r2e-mr-087']，原作业`gpu1003-coverage016a-qwen36-a1`。完整版本、原件SHA、各工具ID与返回时间见[JSON](model_analysis_qwen36_a1_20261003.json)。题主核推理、参数、诊断摘要和完整源码／公开测试改动；[非作者语义核查](../../reviews/non_author_016a_qwen36_semantic_review_20261003.md)与[执行核查](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/coveragepy016a_qwen36_a1_execution_review.md)分别核候选和运输／评分闭环，本轮未新跑CPU、模型或远端。

## 修法与根因

SQLite插入filename处只捕获UnicodeEncodeError；_file_id给坏名缓存None，add_lines/add_arcs逐文件continue，touch_file保护plugin追加。没有整段吞掉save、break或排斥正常非ASCII文件。正式086检查正常数据、branch非ASCII和独立持久化读回通过。坏名仍是_file_map的key，measured_files返回set(_file_map)，所以同对象枚举坏名而fresh read没有它；候选质量缺陷真实存在。本批既定目标不升格新API边界，保留原1。collector独立add_file_tracers/report路径未实际验证；静态风险不是已证崩溃。

## 定位与纠错

第5次工具调用先运行原示例，L61真实UnicodeEncodeError精确指向sqldata._file_id；L67直接确认SQLite UTF-8插入根因。L79读源码后L85给出正确解释；L259识别None会影响add_lines/arcs并补逐文件保护，L385核plugin路径。其后L503新增枚举断言真实失败，模型L509/L523合理化为尝试测量并L531弱化测试，没有修复已发现API不一致。

工具返回时间相对首条gateway请求：L61：2.767秒；L79：3.57秒；L503：51.762秒。这是可定位证据的到达时间，不代表纯模型思考时间或工具执行时长。

## 工具使用

40调用：Bash21、Read13、Edit6。初始find扫描.venv造成噪声；整文件Read sqldata/collector/misc/test_data反复扩大上下文，后续短Read可有明确目的但相邻add_arcs两次可合并。两项is_error分别是改前原示例异常和模型新增measured_files断言失败，都是有效诊断；第二项后的断言弱化属于验证质量问题。没有安装/联网/私有材料读取。

原FP包含公开测试改动；`patch_hygiene.test_files_modified=false`不是“没有改公开测试”的证据。完整投影包含原候选，无审查源码与正式评分候选分叉。没有runner/conftest/私有评分修改；具体质量与污染路径按非作者全文核查保留。

## 并行机会与执行能力

共有2个同一助手消息内的双工具批次，工具ID和返回逐一对应；批次中是独立检索/读取。回传顺序有倒置，可确认多调用协议支持；没有工具开始时间，实际重叠与节省时长不可判断。依赖源码状态的修改和验证须按先后执行；可能共享目录／测量库的测试不机械并行。

## 验证质量

先复现原save崩溃，源码改后同示例成功；原data 63通过，API/oddball 91通过1跳过。新增line自测失败后改弱，再新增arc自测，直接单节点两项通过。改后data65通过；API/oddball又跑一次同91通过1跳过，这次期间只改公开data测试，不是新增独立覆盖。末尾重复line示例、branch及touch_file成功。模型自测只覆盖单坏名、no_disk/告警，不证明混合正常保存/read或报告；当前目标的混合数据证据由正式086提供。最后“all/full suite”实际仅上述三个模块，不能当全仓回归。两份SQLite原产物保持不动，工程交付建议移除。

## 完成效率

| 口径 | 实际值 |
| --- | --- |
| 累计输入／输出token | 1600841／8990 |
| cache read／creation | 0／0 |
| 生成HTTP／count_tokens | 39／2 |
| CC回合／工具调用 | 41／40 |
| solve／CC wall／CC API 秒 | 75.666／71.625／63.024 |
| gateway生成响应累计秒 | 62.077 |
| actor开始至清理收口秒 | 124.25 |
| trusted init／Git sanitize秒 | 25.957／2.613 |
| grader总计／实际测试秒 | 29.933／2.911 |
| grader报告peak_memory_mb原字段值 | 284.281 |

cache为0，反复整文件读入会增大累计上下文，但没有对照运行，不能量化可省token。gateway累计含adapter／运输，不等于纯GPU推理；CC API外残差8.601秒也不能当纯工具时间。actor准备／清理和grader独立核，不混作模型效率；各阶段子项不穷尽总时长。grader queue_wait=0仅是本次评分器排队，不是全批模型队列等待。CC估计费用8.228955 USD是本地别名估计，真实账单未知。

## 结束、用途与接续

completed、CC success/end_turn、harness exit0、正式testRC0，无预算/链路截断。当前材料下可作保存目标成功且带质量余项的单次基座诊断。Coder未执行，不能称配对或稳定；本轮无新增必跑CPU，额外API定向实验仅在要核销具体质量余项时安排。

**CPU动作：**本轮无新增必跑CPU；候选API一致性余项未核销，不扩成材料阻断。

实际context/output/turn/wall预算196608／65536／240／10800秒；实际生成、权重revision及BF16/TP1服务按固定执行证据关联。上限配置不等于实测196K能力；gateway checkpoint_identity_verified=false保留为身份链限制。资源仅闭批有限采样，未采间隙未知，宿主GPU字段不归因每题。全部原件、旧分数和各次自测失败保留，不能以重复成功替换失败，不能把单臂当稳定能力或训练准入。
