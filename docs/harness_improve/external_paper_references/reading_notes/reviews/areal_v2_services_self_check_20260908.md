# AReaL 2.0 服务化与真实 Agent 训练：作者自查记录

日期：2026-09-08。正文：[areal_v2_services_control_flow.md](../areal_v2_services_control_flow.md)。

**状态：固定版本源码精读、配套论文阅读与作者自查完成；7 个隔离 CPU 控制流案例已执行。没有独立 reviewer，没有 GPU／真实 HTTP 集群／SWE 环境或模型训练复现。** 当前线程没有独立子 agent 工具，不沿用早期批次的独立审查标签。

## 1. 范围与版本

- AReaL：`f289b989bc5d1930d5c6d592d335e2ffaf8c2f01`。
- AReaL-SWEAgent：`f144900d5e0a019bf5381b624c442b49999ffa4d`。
- RepoHarness 阅读基线：`da82518af1de11ebe6fa054c0cb7b73f9502a0a0`，分支 `miles-migration`。
- 配套论文：`2607.01120v2`，13 个物理页。正文 §1–7、Figure 1 及参考文献读到末尾；无单列技术附录。关键设计／局限图页已目视核查；末页截图一次失败，但参考文献文本完整取得，不影响技术图的覆盖。未取得本地 TeX/PDF 副本。
- 代码覆盖使用正文 §1.3 的文件／范围表；未把长文件未读尾段、vLLM、Megatron/FSDP 内核和外部 test_patch 隔离实现算成已审计。

## 2. 本次核对后保留或修正的关键判断

| 问题 | 对账结论 |
| --- | --- |
| 论文标题是否代表完整自演化系统已完成 | 不代表。§6 明确限定在线模型权重更新原型；没有完整 ATDP、自动干预选择或成绩消融 |
| SWE 是否就是 v2 recipe | 默认 YAML 无 `_version`，配置默认 v1；Hermes 明确设置 v2。SWE普通run对象能被v2包装，不等于默认路径已采用 |
| YAML是否代表最终采样与传输 | SWE gen_args未实际覆盖外部agent采样；v2非LoRA实际AWEX，不由Hermes中的xccl字段决定 |
| 模型/API/agent/训练session是否同一对象 | 不是。分别记录 Agent DataProxy 历史、Inference session/token cache、训练RTensor和权重pair |
| Hermes是否完全无状态、完整保留原生产品行为 | Worker缓存每session的AIAgent；adapter关闭部分memory/context/sessionDB功能；raw透传与结构化history不同 |
| SWE评分是否总在原环境 | 实现有rl_test分支，实际外部YAML为true；读到test_patch调用边界，没有审完其内部隔离 |
| reward0是否必然是模型失败 | 外部与上层均有异常转0的路径；timeout抛出与正常返回0又不同，不能统称已过滤 |
| staleness是否逐token硬门 | 主要是调度容量计数；不能凭额度公式断言所有实际消费token都满足年龄限制 |
| 异步暂停是否等于checkpoint | executor暂停只停止新任务；abort续生成在内存中；v2通用recover明确不支持 |
| 更新成功怎样判断 | 网关逻辑error可用HTTP200返回，上层缺status检查。隔离函数案例显示继续恢复并发布版本 |
| ready队列是否已有可靠背压 | maxlen=1024的deque在无waiter过载时淘汰旧描述符且ACK成功；单handler无去重 |
| 源码风险是否代表历史实验失败 | 不代表。固定版本控制流问题、推断的分布式后果、实际实验三者分开 |

这些不是“发现十二个上游bug”。多数是责任与证据边界；只有少数是可定位的回归测试候选。

## 3. 实际运行了什么

脚本：[areal_v2_control_flow_probe.py](../probes/areal_v2_control_flow_probe.py)。
结果：[areal_v2_control_flow_results.json](../probes/areal_v2_control_flow_results.json)。

运行：

```bash
python areal_v2_control_flow_probe.py --output areal_v2_control_flow_results.json
```

环境为 Python 3.13.5，仅标准库。4个方法体从GitHub connector返回的固定源码手工转录，随后用HTTP／worker桩装配；`logger`无操作，v1专属恢复分支明确排除。没有偷换成完整上游单元测试执行。

7个案例分别为：成功更新、HTTP200逻辑错误、HTTP500对照、恢复生成与版本发布顺序、1025条通知过载、重复通知、缺ID拒绝。断言成功刻画了当前行为；**PASS并不意味着生产系统健康**。

手工转录的4个方法在成文后回固定源码重新核对，保留函数签名及控制流。完整checkout尚不可用，所以脚本的`--source-root` AST/HEAD校验明确为`not_run`，不能改成已校验。脚本既支持带类型声明的队列赋值，也支持普通赋值，避免仅因注解格式产生虚假校验失败。

未测：真实HTTP进程、worker部分失联、AWEX/NCCL数据传输、模型实际权重或logprob、同样本梯度、callback并发waiter竞争、远端export失败恢复、sandbox取消后的副作用、训练收益及吞吐。

## 4. 文档检查

正文保留源码提交、路径／符号、实际读取范围；链接指向固定官方来源。论文概述与当前实现分开，项目建议仅在文末，不补未披露成本和模型结果。

已检查配套文件可解析、Python语法、JSON结果、引用式链接定义、章节导航目标、数学分隔符、Unicode替换字符、相对链接和Git blob身份；未使用“字数很多”作为技术正确性证明。

本次只新增本专题正文、此记录、probe脚本与结果。共享README/SOURCE_CATALOG由汇总线程维护，避免并行写覆盖；未修改项目训练实现、任务包或外部AReaL仓库。

## 5. 独立复核建议

优先用固定完整checkout跑AST校验，再审逻辑error→恢复→版本发布三层方法；确认真实backend是否需要保持暂停、回滚或重新初始化。其次检查callback ACK与导出生命周期，以及ready队列过载的实际生产速率。最后核默认SWE入口到外部grader的失败分类与采样配置。

若后续发现当前上游已修复，保留本pin记录并追加新版差异，不悄悄修改历史事实。是否提交issue/PR另行决定，本轮没有对外发出问题或补丁。
