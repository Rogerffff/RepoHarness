# Prime 栈源码精读：作者自查与交付记录

日期：2026-09-08。对应正文：[prime_stack_20260908.md](../prime_stack_20260908.md)。

**状态：定界源码精读、作者自查与19个读者自建CPU语义检查完成；没有独立reviewer，没有上游测试执行，没有真实GPU／sandbox／训练复现。** 这不是一份“全部四仓库审计通过”证书。

## 1. 任务与文件范围

用户指定任务3：prime-rl × verifiers × renderers，从环境轨迹到不同训练目标。沿实际SWE配置额外补读其依赖prime-envs的R2E-Gym任务，不将范围扩为所有环境、所有模型或所有推理后端。

本轮只负责四份新文件：

- `prime_stack_20260908.md`：正式维护正文。
- `reviews/prime_stack_self_check_20260908.md`：本记录。
- `checks/prime_stack_semantic_probes_20260908.py`：读者自建参考检查。
- `checks/prime_stack_semantic_results_20260908.json`：实际执行结果。

共享README、来源总数、其他线程笔记、训练实现、依赖pin和项目实施决定均不在写入范围内。分支写入以最新head为基线、非force推进，保留并行任务更新。

## 2. 固定来源

| 对象 | commit |
| --- | --- |
| prime-rl | `04a61d3b75c3c99f263b2c133e822f998909adf7` |
| verifiers | `828488fffe31aa3332b9d1bd4bd9ee320e375cf1` |
| renderers | `f91c3e7061ce50ea405cdf54fd419a45cb51a152` |
| prime-envs | `1f1e050ab0cd273bca39eed5c3e5315e6a8ae9d1` |
| RepoHarness读取基线 | `32b615c4e4f869b448174e5974e7a8d29fc4612c`，`miles-migration` |

前三个依赖代码版本取自prime-rl实际gitlinks，不从各repo最新main任意拼装。配套官方Algorithms Layer文章为2026-07-05，正文按九月代码区分新增内容、名称与阶段。RepoHarness项目映射只依据当前简报，不声称本轮重新审查rh2实现。

## 3. 已覆盖的实际链路

从SWE TOML和配置继承出发，追到orchestrator taskset ownership、EnvClient typed task data、verifiers Agent与Trace、TrainClient原始token调用、Qwen3 renderer和graph commit；随后追八个算法、episode/group finalization、curriculum、gate、branch展开、三目标流、batch运输、packing、trainer全局计数、真实loss和backward调用。

覆盖较长文件的具体行区间与未展开部分在正文§13，不将目录扫描或搜索命中算成完整源码阅读。相关上游测试只读取：算法、compaction路径、ECHO、混合loss、空目标、权重语义；没有执行。

额外案例是reverse-text配置，明确组大小与改名模型的renderer选择。SWE任务完整加载和评分函数已读，但bash harness内部、安全runtime与完整server生命周期未审。

## 4. 关键自查结果与解释修正

| 检查 | 处理结果 |
| --- | --- |
| 版本0.9.0与main快照 | 标为main提交，不把pyproject版本当release tag |
| 库默认renderer | 区分renderers库fallback与Prime自动配置拒绝；不制造不存在的默认静默问题 |
| SFT／OPD生成与teacher身份 | generation source、scoring source和target loss分别记录；冻结endpoint不等于已核验词表与权重 |
| OPSD命名 | 记录其文档链接SDFT；不与SDPO或另一篇OPSD混为一谈 |
| GRPO统计单位 | 按实际eligible traces计算，不按branch数量重算；执行错误不是补reward0 |
| group_size未设置 | 记录SWE TOML/default冲突需要resolved配置确认，不声称实际作业已失败 |
| MaxRL singleton | 代码公式与docstring存在可检查差异；只形成文档／真实单测候选 |
| 门控与目标 | 内置prune保留CE/ref；可选AdvRangeGate可提前拒绝ECHO全0组；默认gates为空 |
| is_content | body缺失有整节点fallback，不声称始终只训body或始终fail-closed |
| sharedprefix | 存储、梯度和前向计算去重分别描述；长度代理与actual call usage也分开 |
| loss分母 | 每分量非零成员数，不是权重和或trust过滤后数；同CE混合仍改变均值 |
| RL与ref-KL | IPO绝对概率trust与ref单侧阈值分别恢复；不是经典PPO/DIS；detach影响实际梯度 |
| packing截断 | never-truncate只描述bin packing；上游prepare_sample仍会切长样本 |
| dummies | 清action mask不够，所有CE/ref流与身份也要清；已有代码确有处理 |
| 全局计数 | 分母、CP gather和FSDP补偿作为一套；CPU算术不是CP/FSDP实测 |
| R2E-Gym来源 | 实际默认Verified而非文件头RL；HF/镜像资产未全部冻结 |
| R2E-Gym评分 | host保管测试与原runtime评分分别记；不等同rh2 freshgrader |
| 测试名称 | GRPO/GSPO测试名不证明两个论文loss分别被实现；实际读取IPO调用 |
| 状态恢复 | curriculum保存不等于所有算法状态保存；RAE重启清零为源码约定 |
| 性能/学习结果 | 没有把文档规模、代码存在或19检查转成吞吐、显存或模型增益 |

上述条目不是“发现20个上游bug”。包含已有正确防护、合法设计取舍、文档/默认值对账和待实验风险，正文明确分开。

## 5. 实际执行的检查

运行环境：Python `3.13.5`、PyTorch `2.10.0+cpu`，没有GPU或联网需求。

```bash
python prime_stack_semantic_probes_20260908.py \
  --output prime_stack_semantic_results_20260908.json
```

**结果：19/19 passed。** 脚本是读者独立编写的小参考模型；不import upstream三仓库，不替换它们的函数，不安装完整依赖。因此只验证本稿解释的代数／结构后果，不能写“Prime测试19项通过”。

覆盖：错误与0reward区别、效率shaping、singleton、EMA顺序、sharedprefix、gate/prune、CE/ref保留、权重与分母、目标混合、absolute trust、ref detach、loggap符号、支持集、dummy、pool概率、staleness、token分叉、截断零梯度、简单DP计数。详细数值在JSON及正文§11。

Torch autograd仅用于ref signal detach和空目标anchor两个小例子；其他主要是Python算术/集合。DP例没有模拟实际通信或CP。没有真实tokenizer parity、teacher接口、HF数据、Docker、推理服务或训练收敛测试。

## 6. 实际工具限制与后续复查

GitHub连接器可以读取固定提交并写入本项目。容器直接联网下载源代码失败，Files materialize也不可用，因此没有完整checkout；源码通过连接器按路径/范围读取。这是工具访问限制，不是作者没有公开代码。

最有价值的下一次独立复查，不是再写一遍框架概览，而是从干净上下文核对：

1. 用固定真实函数重跑gate／CE、sharedprefix、dummy和token流fixtures。
2. 安装对应依赖后解析SWE完整resolved配置，确认group_size、SLURM和命令行overlay。
3. 对三分量loss做实际trainer的单卡／DP／CP参考对拍，核分母、温度、support与gradient scaling。
4. 对source版本之间的差异做定点检查，再判断是否有必要向上游提交文档或测试PR。

独立复查若未执行，不补写线程ID、审查模型或通过标签。后续改动优先落在本篇与本记录，不改历史交接快照，也不自动实施项目建议。
