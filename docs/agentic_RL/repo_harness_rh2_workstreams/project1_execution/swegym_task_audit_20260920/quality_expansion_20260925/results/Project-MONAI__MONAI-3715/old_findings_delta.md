# 历史主张对照：Project-MONAI__MONAI-3715

本包三份初稿封存且协调者明确release后，只读取本题history/refs.json指定L1_monai_1记录；hash匹配。未读其链接、stage1日志、3690记录或索引、reviewer。封存稿不变。

| 旧主张/字段 | 判定 | 原件理由与处理 |
|---|---|---|
| base、文件、参考测试与整文件命令 | 确认 | P/V、历史w05-1 ledger15/16与日志相互一致；旧创建日期未独立确认 |
| 普通Enum与原始mode比较导致字符串失败 | 确认 | evaluator.py117–123、enums207–213、look_up_option47–121；历史实际失败是eval字符串 |
| 题面诉求train、缺陷可定位 | 确认，限定规格 | 标题/公开API同样支持eval，不能把eval测试当无公开依据的要求；saliency动机不等于需修全部显著图实现 |
| “self.mode最终应是什么，公开材料无法确定” | 可消解 | evaluator.py260、397明确with self.mode(network)，公开源码已要求callable上下文管理器；不必从gold才知道 |
| check3由题面完整记pass | 纠正 | 公开语义清晰属23；本批实际actor消息未知，check3=unknown；当前public_hints存在，不能沿用旧raw hints空推断 |
| 纯测试恢复/additional_exclusions空 | 确认有限历史路径 | gold投影仅evaluator.py，stage/log/setup一致；未全面验证评分控制面 |
| 与3690相邻、base包含其gold和测试，必须同侧 | 未核实线索 | 允许材料中确有空epoch返回和test_empty_data，但这不能独立证明另一题的来源/补丁/时间关系。未读3690、dupidx或旧链接，不据此认证/否定分组；提交协调者另按授权边界处理 |
| check23 P1“评分不是题面用例” | 确认遗漏，纠正归类 | train确实完全没有验收，但eval有公开文档/类型依据；这是check25覆盖缺口，不是已证隐藏规格冲突 |
| F2P跑出正确output | 限定 | test_content只断言image/label，不断言prediction、training、grad或退出恢复；TestNet为identity，不能以“正确output”推导模式效果正确 |
| 无条件self.mode=eval_mode可过当前参考却不满足train | 确认静态机制 | F2P仅eval，P2P默认且空流程。旧记录未给mutant运行原件，本轮也未执行，故记录为静态反例，不给真实分数 |
| “只把elif train那一支删掉也满分” | 按字面推翻/条件不足 | 对原base仅删除train分支仍保留原始字符串eval与Enum比较，F2P仍报错。只有先使eval路径通过再删/破坏train，才能构成满分风险；不能把这个省略前提的说法当执行事实 |
| check26因P2P仅一条必须补train | 纠正 | 缺覆盖归25，不证明gold新增回归；26=unknown。gold单行归一化静态上保留两模式/枚举/非法输入 |
| check27单行gold正确 | 确认静态范围 | 规范化局部mode后选上下文，两个子类共享路径；历史只测eval，不能声称train已实测 |
| 改Enum基类、直接比较value等都可过 | 不强制实现确认，普遍合法性未证 | 这些改法可能更广影响Enum调用者；当前断言不锁实现不等于每种方案无回归。public_read函数身份检查同样不能直接当验收 |
| traceback定位精确算check29泄漏/降低难度 | 不认定答案泄漏 | 原始报错定位是合法问题上下文，没有给出修复代码；难度变化没有模型证据。实际actor未来历史/工具泄漏unknown，私有审查答案应隔离 |
| stage1环境完全干净、离线4.75s、CPU无随机 | 旧数值未核实；本次有限历史支持 | 本次引用不同run，noop1fail1pass/gold2pass、RC1/0、无missing/skip；可证明该grader执行成功，不能写actor环境完全通过。device条件可选择CUDA，CPU充分不代表接口禁止GPU |
| 安装RC=0即依赖可恢复/不需网络 | 限定 | 本次历史deny_all/本地依赖成功；末命令RC非逐步RC；实际actor解释器/安装供应/资源待验。无需外部数据和权重是公开用例事实 |
| 补train+枚举、非法值及集成回归，needs_repair | 部分采纳 | 先补用户API train行为是有依据的唯一优先提案；枚举/非法值合理回归。无需扩成全工作流通过门槛。当前交付只能static_review/needs_review，独立review待完成，非正式修题决策 |
| 旧成本20分钟 | 不迁移 | 本轮成本未观测，null |

相对初判没有改变核心结论：train验收缺失、gold静态合理、actual actor未知。新增的是3690关联线索（未核实）以及对旧反例文字的限定；初稿保持原hash。

历史唯一来源：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_monai_1/records/Project-MONAI__MONAI-3715.json`；SHA256 `e5ccf77b0870e4a046a3da0ec195ecd7b2b764490794248098ed8e3c488c38b0`。封存初稿SHA256 `984e1fff5ba2da925eb85762eade8880bbda15d5de26e3a59b6748cd8ee255d2`。

## 封存后的编号修正（协调者提醒）

协调者在阅读封存初稿后提醒：按授权流程，私有审查者见到gold/test并不等于actor本地发生答案泄漏。采纳此区分：初稿不改；后稿check29改为unknown（实际actor可见材料未取得），审查者见过的gold/隐藏测试/旧记录只记在usage与读取范围，不计成题目质量缺陷。此修正来自协调者封存后提醒，不冒称独立review结论。独立review仍待完成。
