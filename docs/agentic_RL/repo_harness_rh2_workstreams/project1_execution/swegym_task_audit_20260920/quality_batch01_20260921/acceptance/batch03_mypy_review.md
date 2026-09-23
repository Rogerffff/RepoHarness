# 第三批 mypy 三题根验收

2026-09-21。接受三题的静态角色链、有限结论和未执行 CPU 交接；不代表 actor、训练或测评准入。15184、10174保留受限候选，15139先做语义诊断。

- **15139：** 原1F2P只检普通赋值错误中的 `type[type]`；gold没有修复题面另外涉及的reveal输出路径。根已对原题、gold/test、TypeStrVisitor及历史两条日志定点核查。先比较base/gold原三行程序的完整note/error；不因有八个其它容器类型旧case而宣称TypeType回归受保护。
- **15184：** 接受最终纠正：`SupportsIndex`的fullname不同不意味着结构协议不等价。根核了assert_type调用、is_same_type的双向proper-subtype条件和两份桩的同形`__index__`声明。原例保持开放判据；历史2F2P/1P2P均为应报错用例，不能把P2P写成成功断言。现有名义类消歧缺陷不因原例可能失效而消失。
- **10174：** 接受有明确目的的单个过宽错误控制：仅在non-strict optional下跳过比较，配同开关的真实int/string不重叠负例。原两个P2P只保护未导入提示。根核了公开原题、gold/test、dangerous_comparison和公共负例，候选尚未构造或运行，不能写成已观察到满分错误补丁。

六条历史日志关键输出与来源摘要相符：15139为1/1实际节点；15184为3/3；10174为3/3，不能把全仓collected数当执行数。日志均有安装完成、对应普通测试RC和目标失败/通过；它们不是本轮新运行。

[最终元数据检查](batch03_mypy_metadata_final.json)：21份文件、9份封存、6个顺序记录、3份最终review匹配。初次对账发现三份可变record与中期摘要不同；协调者已登记仅收束checks.5的源码包含证据，最终清单匹配，封存稿未变。初次观察保留在[中期检查](batch03_mypy_metadata_check.json)，不隐藏也不当代码故障。

[CPU补审](batch03_mypy_cpu_handoff_review.md)未发现设计阻塞。实际运行解释器与mypy目标Python版本分别记录；固定grader语义诊断无须先全面验收actor。原镜像/载荷、冻结code-root和/work路径重定位仍待运行准备。元数据顺序与文件摘要只能支持记录的一致性，不证明操作系统层面的访问隔离。
