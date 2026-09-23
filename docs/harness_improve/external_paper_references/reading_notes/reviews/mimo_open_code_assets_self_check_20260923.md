# MiMo 开放代码与资产专题：作者自查记录

日期：2026-09-23。正文：[mimoagent_execution_and_training_assets_20260923.md](../mimoagent_execution_and_training_assets_20260923.md)。

**状态：指定源码路径精读、资产入口核查、有限 CPU 检查完成；没有独立审查、完整上游测试或 GPU／容器／CLI 复现。** 本次没有创建独立 sub-agent，未取得可用于记录的独立 reviewer ID；不继承其他笔记的审查标签。

## 1. 固定版本和交付范围

| 来源 | 固定标识 |
| --- | --- |
| XiaomiMiMo/mimoagent | `467f0a19016f0ac4d63b8d17a1f0da9ba07f232c` |
| XiaomiMiMo/uni-agent | `c63e0b01c375ebede95e01fe92bc367df24e5bf3` |
| XiaomiMiMo/verl | `e2b9fc03c6e01247f5d93c44201b068ea320b7de` |
| 项目同步背景 | `0554dafd633cd982288bd60a54f75da65e5c54d4` |
| 已有 MiMo 报告／本分支父提交 | `aa423327b76c541e744f2f0fb7ad3c9ceea8d32d` |
| 专属工作分支 | `pro/mimo-open-code-assets-20260923` |

检查了 V 的 submodule gitlink，M/U 均与本次阅读版本一致。没有将它们认定为原报告内部生产版本，也未把 U 自己的历史 verl gitlink当成 V 的替代。

正文不重新讲解整份 MiMo-V2.6 报告，而是核查：两种实际 harness、独立日志与训练捕获、Gateway→TQ→优势／分母、两类 SWE scorer、安装与数据资产。既有报告笔记只作为机制和资产宣称的比较入口；没有独立复读原 PDF。

本轮只新增本专题、本文和离线检查脚本，不修改项目实现、训练配置、环境定义或既有报告。共享 README／总数暂不改，避免独立分支覆盖并行阅读汇总；最终交付提供正文入口供统一索引。

## 2. 实际覆盖和未覆盖

完整文件或主路径：M 的 README、AGENTS、BaseAgent、CCAgent、ClaudeCodeAgent、SDK runner、CLI installer及安装桥、batch/save、dataset registry、opensource-code、Datacurve converter和DeepSWE评分主路径；U entry、Trajectory/session及framework关键范围；V run_train、train.yaml、四白盒mix/mini-CC配置、runner、dataset/reward、validator、colocate_async、GRPO多行工具函数。

显式部分阅读：M DefaultAgent 1–300、OpenAIChatModel 1–270、dataset base 1–640、rubric_judge 1–230；U framework 1–1350、1440–末尾；V main_ppo 1–170、trainer_base 1–310/900–1150/1880–2420、core_algos 1000–1270与版权。较大响应出现截断后，对关键末段分范围补取；未核区间在正文保留，不称为全库审计。

没有完整读取 Gateway codec 和 HTTP adapters、ReplayBuffer 策略、Megatron/SGlang kernel调用、全部工具和测试目录。仅定位 upstream tests，**没有跑其测试套件**。没有下载全库、权重、CLI payload或镜像。容器直接联网读取失败，后续使用 GitHub 连接器读取固定源码；这不表示官方仓库不公开。

## 3. 阅读中实际修正的解释

| 容易发生的误读 | 本稿修正及依据 |
| --- | --- |
| cc-agent 就是真实Claude Code | 类注册、配置与CLI wrapper区分；native prompt的自我描述不改变实现身份 |
| M演示配置等于V训练配方 | demo有Agent/Compact，四白盒mini-CC只有六工具；shell又覆盖YAML采样数和预算 |
| `training schema`含完整原始token/logprob | save.py只保存语义messages等；真正token来源在U Gateway/backend |
| token被捕获就全部用于训练 | 默认rollback删除末次assistant采样；longest在TQ前选择chain |
| longest就是final | 实际排序首先看模型输出mask数量，示例验证可选较早chain |
| 每行等权或每session等权 | GRPO按session估计，prompt-mean在每题全部动作token上归一化；两者职责分开 |
| 全部M评分都在actor pod | opensource-code如此；DeepSWE override有新环境、base锚定和binary工件运输 |
| 未看到顶层payload字段就没有离线CLI安装 | 沿真实连字符installer查到install_env/payload入口；第一次猜错文件名的404不作为缺失证据 |
| 所有grader错误都会变成无效样本 | 部分错误返回数值0；runner、score和最终buffer需分别核查，未声称已污染梯度 |
| rubric engine就是论文GAR/GRS | 通用组合与组条件生成分开；本次未核到后者完整路径 |
| verl底层有distillation就能运行本recipe的MOPD2 | 所选adapter明确拒绝teacher_client；不扩大为整库没有蒸馏 |
| 有preflight就保证默认启动自洽 | 明确找到过滤变量两处相反默认值，并以最小函数检查确认 |
| 开放约3k就意味着已验证数据清单 | 有发布宣称和schema；本次没有定位并下载完整manifest，保留未闭合状态 |

这些不是“发现十三个框架bug”。其中包含正常设计取舍、读者早期假设的修正、文档与实现差异，以及需要进一步运行核查的风险。均绑定固定提交，不指控历史论文实验。

## 4. 实际执行的 CPU 检查

脚本：[mimo_open_code_assets_checks_20260923.py](mimo_open_code_assets_checks_20260923.py)。运行方式：

```bash
python docs/harness_improve/external_paper_references/reading_notes/reviews/mimo_open_code_assets_checks_20260923.py
```

需要Python、Bash和PyTorch；不联网、不下载模型、不运行Hydra/Ray/K8s。文件保留被摘取函数的版权／Apache-2.0归属。

### 4.1 启动变量与严格校验

实际执行 `run_train.sh` 中两个同名变量的默认展开表达式，再调用原validator的 `_get/_check` 函数体：

- 环境变量未设置：配置True、期望False，抛出 `algorithm.filter_groups.enable must resolve to False, got True`。
- 显式True：该项通过。
- 显式False：该项通过。

这不是完整launcher或真实resolved Hydra运行。它验证的是固定脚本中直接可达的两处默认值冲突；若其他preflight先失败，实际运行可能根本到不了这一项。

### 4.2 prompt-mean函数

调用原 `compute_prompt_loss_weights` 函数体。A两行4+2个动作，B一行1个动作，PAD无动作：权重为 `[0.08333333333333333, 0.08333333333333333, 0.5, 0.0]`。A、B总质量各0.5。无重复拆分一行后，构造目标前后都是5.25；全零batch按实现报错。

不是完整训练backward，也不证明不同上下文、重复token、DP/CP或微批次实现等价。

### 4.3 chain选择示例

按源码排序元组构造例子，模型输出token最多的较早chain被选中，最后chain未选。这是读者构造的语义示例，没有导入整个Uni-Agent包；不计为upstream单元测试。

三项检查均按预期结束，JSON结果保留在当前会话本地；主要结果已写入正文，不上传大量运行缓存。

## 5. 尚需独立核查的高价值点

优先核review范围和两种真实路径，再查主文强结论是否都有caller证据：longest与rollback的先后、session GRPO与prompt分母、returned error是否在最终buffer被排除、rubric缺attach的实际后果。需要真实运行的部分应另标，不要求审查者凭静态阅读宣称关闭。

如果准备正式复用，建议运行一组小反例：SDK缺ResultMessage；参数改写和压缩后的token覆盖；newfile/commit/binary工件往返；合法模型失败与grader故障分别进TQ。对当前框架可能已修的地方，先查最新commit及相关issue，不凭这份固定快照直接提PR。

HF模型卡只核身份和公开配置索引，没有冻结完整模型revision；约3k任务入口仍待取得。这两处是实际访问范围限制，不以“模型能力足够”或“官方说开源”填补。

## 6. 文本与远程交付检查

本地检查包含引用定义、导航、成对数学／代码块、无替换字符和行尾空格；离线脚本实际运行。远程写入将采用基于当前专属分支的新增文档提交，回读文件并核对差异，不把提交前的计划标为已经发布。

最终commit由交付回复记录。这个专题完成表示指定范围已精读成文和作者自查完成，不表示整个MiMo开放生态已经部署、数据已验收或项目设计已定案。
