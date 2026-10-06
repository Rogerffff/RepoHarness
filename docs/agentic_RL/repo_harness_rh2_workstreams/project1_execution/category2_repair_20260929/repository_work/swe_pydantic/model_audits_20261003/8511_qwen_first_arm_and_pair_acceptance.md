# 8511：Qwen 原分1与字段信息保留缺口

2026-10-03。**两模型首次执行已完整核收；Qwen173条正式参考全通过/raw1，但候选丢失原有字段信息的静态路径阻断完整正确结论。** Coder 原0分由隐藏字段继承 TypeError 支持；Qwen 原1分与既有评分一致，不改历史分数。新问题是 `repr=False` 与 `default_factory`、约束、别名的组合未被当前参考覆盖，已提交[最小 CPU 诊断](../cpu_acceptance_20261003/8511_fieldinfo_retention_diagnostic_v1/plan.md)，真实结果尚未返回。

题主完整阅读727条轨迹中的非重复思考、文本、45次工具参数和返回，包括完整公开fields/dataclasses源码和长失败输出；209件封存成员共24,921,954字节、452项完整 baseline 逐件核 SHA/类型/执行位。FP仅 `pydantic/dataclasses.py`，实际四次 Edit、stash/pop与checkout的作用从基线重建后与原FP字节相同。shell 后半段失败不表示前面的 stash/checkout 没执行。[非作者独立报告](../reviews/non_author_8511_8567_qwen_first10_execution_semantic_review_20261003.md)与[题主读回](../coordination_20261003/8511_qwen_pair_owner_readback_v1.json)保留执行与语义范围。

| 诊断方面 | 结论和证据范围 |
| --- | --- |
| 候选语义 | 最终修法把 FieldInfo 的真实default或MISSING交给普通dataclasses.field，只保留repr/kw_only；随后收集函数不再走保留原FieldInfo的分支，无法恢复已丢的工厂/metadata。静态预测隐藏工厂变必填、显式0失去gt验证、别名输入失效。此轮尚未运行这些组合，不能写成运行已复现；也不能把现有173全过当作完整语义成功。 |
| 定位与纠错 | 最初用FieldInfo作为stdlib default包装，遇旧字段顺序错误后做真实基线对照；旧基线同样失败，应与最终候选回归分开。随后改用MISSING避开必填顺序，却丢掉字段对象；公开测试发现无annotations类AttributeError，最后改用getattr修好。这些纠错解释当前分数，但没有验证工厂/约束/别名的隐藏组合。 |
| 完整候选、自测和交付 | 没有Write或临时文件留在FP，也未修改正式测试。最终公开dataclasses166 passed/11 skipped、加fields172 passed/11 skipped；head/tail管道exit0不独立证明pytest成功，`--timeout`不识别的输出也不能算通过。正式评分另核完整173。模型最终“fully compatible”之类范围应收窄，字段保留缺口仍在。 |
| 评分与公开范围 | 实际install0/test0、1F2P和172P2P全PASSED，raw1、FP摘要 `4c305765…` 保持。四个新增P覆盖隐藏必填继承、非隐藏工厂继承和默认repr，没有保护隐藏工厂/约束/别名组合。保留这些已有公开行为不需要扩写题面。首HTTP原题面逐字节匹配，完整私有patch与新增节点标记未出现在全部请求；没有把新诊断交给solver。 |
| 环境与配对 | code_v8、base e4fa099d…、actor/grader精确df6c3aff…镜像与Coder一致；同452项baseline canonical `40135f28…`，tar头时间不同不冒称tar SHA相同。Python3.8.19/core2.14.5，UID54321/54322、实际/testbed源码导入及可信安装前置通过。前后pip freeze相同，solver前pdm/pyproject差异不当模型改动。whole3600/setup300/apply120/test1800不变；env qualification仍absent，不授typed资格。 |
| 效率与并行 | 44生成+1count_tokens、45工具（31Bash/10Read/4Edit）、CC46回合；两个各2工具的并行组，其余串行，无子agent，六个工具error。累计输入1847294/输出14972，共1862266 token，单次输入峰60480。读完整fields及多轮顺序排查放大上下文；首Edit19.108秒，solve114.923秒、CC111.403秒/嵌套API99.860秒，grader186.226秒，安装2.494秒/pytest2.565秒。不相加，不由一次观察推稳定效率差异。 |
| 模型、资源和收尾 | 派发前14:08:16.394→.545 UTC实际捕获 Qwen3.6 engine/adapter CID、PID、restart0和只读revision，真实HTTP/配置一致。清单实际37文件大小已核，头40的元数据差异保留；无逐权重或显存字节证明。actor9/grader13有限采样，短安装/测试各零采样，缺口未知；report峰648.445MiB另记。单job actor/relay/network清理无残留、drain active0、manager1建1删；exact PID1成功14:13:48.437364 UTC，不用not-found默认0证明退出。 |

旧探针的两模型交接可ACK，以表示完整原件和题主分析已收到，不表示题目已处理完或材料覆盖充分。[CPU支持输入](../coordination_20261003/8511_fieldinfo_retention_cpu_support_input_v1.json)绑定原Qwen FP、真实baseline、narrow和诊断脚本。先在既有cpu-a剩余槽比较原base/narrow/Qwen四项保留行为，身份或基础设施异常记hold；结果支持后再正常提出最小私有P2P新版本，不热改已封材料、不扩大预算、不重采样。旧Coder继承回归与原Qwen分数都保持。
