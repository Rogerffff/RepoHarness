# 15184：Qwen3.6 首臂原件与方法回读

2026-10-03。job `gpu1003-mypy15184-qwen36-a1`，原请求 `swe-mypy15184-nested-nominal-v2-20261003`，预算 `probe-wide-v1`。题主与两位非作者已独立核原件并[收口](qwen36_first_arm_acceptance_20261003.json)；Coder 首臂现已另核，整项请求 returned/ack，当前题级结论见[两模型首轮验收](two_model_first_round_acceptance_20261003.md)；本页旧原件及冻结JSON保持当时范围。

**同一候选的正式评分为1，五个参考全部通过，源码修法符合当前题意。** 模型只改 `assert_type_fail` 的错误消息，联合格式化实际类型和目标类型，复用已有 `format_type_distinctly`。该 helper 会遍历类型中的实例、找同短名的不同完整名称，支持嵌套消歧；不改 `assert_type` 的成功判定或表达式返回类型。正式新增嵌套 F2P 和有效断言 P2P 都通过。本次没有具体证据要求新 CPU、修题或重解。

本页原回传未证精确实际checkpoint：gateway发送Qwen3.6-35B-A3B、响应slime-actor、checkpoint_identity_verified=false。随后题主另写[Q13 40请求运营来源补证](q13_operational_identity_supplement_20261003.json)，由[非作者独立窄核](../reviews/non_author_15184_q13_identity_20261003.json)确认40请求/adapter/后端完成对应与适用共享服务事实；不冒称旧Q12审覆盖此job。事后capture、HTTP revision/checksum null、未全权重重hash及无GPU驻留证明等限制保留，旧false不改。有限运营归因支持当前观测，未见错绑证据，不据缺强证明机械重跑。

## 原件、公开交付和正式评分

闭包清单为 `runs/ordinary_gpu_probe_20261002/remote/gpu1003-mypy15184-qwen36-a1_closed_manifest_v1.json`。题主逐文件重算95件 SHA/大小，合计21,307,412字节，全相符；其中有共用配置及其它题 input check，不能把95件理解为95个本题执行记录。逐事件索引、原件身份、命令及输出见[机器回读](qwen36_first_arm_trace_20261003.json)。下面路径从仓库根起算：

- 本题原件：`runs/ordinary_gpu_probe_20261002/remote/queue_v13/results/gpu1003-mypy15184-qwen36-a1/`。
- 完整轨迹：上述目录 `attempt/harness/trajectory.jsonl`，603条事件；实际首条网关请求含逐字相同的 `solver_prompt.txt`。公开新例、有效断言要求和中性环境 brief 已实际交付，未含私有评分材料。
- 候选身份：FP `41adba1e…`，完整 baseline `fdd59f84…`，实际 GPU 镜像 `cda77e2d…`。1422个归档文件内容/执行位、求解前 census 和 grader 重建 census 均与完整 manifest 相同。
- FP 有 `mypy/messages.py` 和模型自己的测试修改两条；正式投影仅含源码，源码 SHA `2ca8bce8…`。模型测试修改没有成为评分依据；本次无投影缓存条目。
- 材料对应已验 R10：public `77b85678…`、grading `3a3c4e78…`、environment `de06cc63…`、materials identity `bf000616…`。正式命令精确选五 node，无 `-k` 混选。
- `grading/report.json`、diagnostics 和 eval.log：3/3 F2P通过、0/2 P2P失败；五键实际执行/解析，缺席/跳过/段外解析均0。安装失败列表为空，editable build/install成功，candidate/test RC0，可信测试恢复/应用/保护通过，runner前后同摘要。
- 求解正常 `completed/end_turn`，harness退出0；rollout容器/网络/relay清理正常，grader创建1/移除1且open/supply/cleanup failures均空。

| 正式参考 | 结果 |
| --- | --- |
| 原 `testAssertTypeFail1`、`testAssertTypeFail2` | PASSED |
| 新 `testAssertTypeFailNestedNominalTypes` | PASSED |
| 原 `testAssertTypeFail3` | PASSED |
| 新 P2P `testAssertType` | PASSED |

## 方法、定位和纠错

事件行号对应完整 harness 轨迹。工具编号是39个去重 tool_use 的顺序，不能用90条 assistant 事件当90回合。

| 维度 | 实际证据与判断 |
| --- | --- |
| 方法与根因 | 工具1（行15/19）用公开三文件复现C/C误报；工具2定位 `messages.py:1660`；工具6（行89/93）读取联合格式化 helper，工具8核 `find_type_overlaps`；工具14（行209/213）将分别格式化改为联合格式化。只有这一处源码编辑，没有取消断言错误或硬编码模块名。 |
| 定位效率 | 首次相关符号定位为工具2，helper读取为工具6，源码编辑为工具14。网关第6/14请求到达相对首请求为6.346/14.018秒；这是服务侧请求时点，不能冒称工具真正执行起止或“根因形成”的精确时刻。 |
| 工具使用 | Bash27、Read8、Edit4。8次error旗标中，工具1/15/18/19/37/38是有意制造类型不匹配，mypy退出1正确；工具23的自写多文件测试用了错误的 `--- a.py` 格式，工具29又用了桩不支持的 `typing_extensions.assert_type`。模型依次查公开格式、改为 `[file ...]` 和 `typing.assert_type`，工具32通过。没有支持把这些记为基础设施错误的证据。 |
| 并行机会 | 每次请求最多一tool，无实际工具并行；若干临时正负例和不同回归可独立运行，模型没有合并。实际执行层并行能力未核，不能从此推断全局能力；这里 pytest均 `-n0`。 |
| 验证质量 | 工具15/37同公开负例已变a.C/b.C但仍退出1；工具17/39有效同类型断言成功；工具20旧相关6项通过，32新增两项加旧五项共7项通过，33扩展8项通过。模型自己没直接测试嵌套，受信评分另证嵌套通过。工具34的 `-k distinct` 是其它“distinct”语义测试，不能当联合格式化的专门覆盖。 |
| 效率 | 62.946秒求解、40回合/40网关请求/39工具；两次测试作者错误引出修正和搜索，工具24/25搜索自己刚写的错误格式，部分重复验证可省。总体没有截断或无限重试。分段时间包含关系及token见下表，不折成未经校准的综合分。 |
| 结束与稳定性 | 最终“7项assert_type通过”对应工具32真实输出；正常end_turn，完整候选/评分/清理齐。单个首臂只记一次观测；Coder已另核，各模型一次，同条件稳定性未知。 |

工具35/36分别输出 check-basic 的44 passed、check-expressions 的181 passed，但命令通过 `| tail` 且无 `pipefail` 或 `PIPESTATUS`。尾部没有失败标记可作为当次输出观察，不能用工具成功标记证明独立 pytest RC0，更不能声称全仓测试通过。正式评分的五参考有独立 test RC0，不依赖这两个管道。

## 计量与边界

| 计量 | 实际值与范围 |
| --- | --- |
| 求解／CC／CC API | 62.946／59.483／39.784秒，存在包含关系，不相加。 |
| 网关响应累计 | 38.788秒，40次200响应、39次tool_use/1次end_turn，无stream error；亦不与CC API相加。 |
| attempt／评分 | 109.337秒含环境、求解、冻结、清理；评分96.780秒另列，评分test段3.969秒。排队和环境时间不能算作模型解题。 |
| token | 累计input528,184、output6,067，读/写cache均0。最大单请求input21,402；累计输入包含重复上下文，不是单次上下文长度。 |
| 预算 | 原配置196,608上下文、每请求max_tokens65,536；40份实际网关请求均65,536，无context recovery/截断。CC静态modelUsage maxOutputTokens32,000不作后端运行上限读回。 |
| 费用 | CC `total_cost_usd=2.792595`是alias/API估算，不能当本地BF16 GPU账单。 |

资源窗口为00:20:12–00:23:58 UTC，16次采样；rollout容器有7个采样，已观察memory.peak约882MiB、pids.peak24，采样中的oom事件为0。这是有限窗口、容器侧观测，不能当主机/引擎全生命周期审计或完整实际HostConfig核验；正式 diagnostics 的 `resource_facts=null`、`env_qualification=absent`保留。模块直接观测只有 `/testbed/mypy/__init__.py`，没有pytest进程内 `messages.py` 加载SHA；本轮未出现来源矛盾，不因此扩跑新探针。

CPU已验材料和本次原件均不回写。两位非作者已完成只读增量审查，最终题级结论见[首臂收口](qwen36_first_arm_acceptance_20261003.json)。当前仅保留版本固定的普通基座诊断用途，不增加训练或留出资格。
