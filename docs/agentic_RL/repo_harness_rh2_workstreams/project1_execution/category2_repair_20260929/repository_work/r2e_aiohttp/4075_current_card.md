# 4075：首轮与行为分析完成，重复采样待安排

2026-10-03，Asia/Singapore。持续题主为 `R2E | aiohttp 题目修订`，任务 `aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a`。本轮关闭错误公开复现：去掉 `invalid_header` 赋值处第一次 `.encode()`，保留构造整个请求时的编码。没有加入候选修法。

用户随后增加行为分析与第二阶段重复要求。首轮两条完整轨迹的[方法／定位／工具／并行／验证／效率分析](4075_trajectory_analysis_20261003.md)已补，具体生成轮及原行号、累计token和分开计时均保留。Qwen3.6发现并修正UTF-8过严回归；Coder最终修法有效，但split解释、测试筛选与验证声称有不足。每模型只有一次，未下稳定性结论。首轮收口不回写，整批GPU仍依赖后续统一同条件重复采样；无需本题CPU修复或首轮重跑。

修订已登记为 `r2e-mr-069`，固定发布为 `cat2-cpu-r2e069-swe6-20261003-v1`。fresh 公开静态读者、CPU-b 公开开发与实际交付的[非作者核查](reviews/non_author_4075_cpu_r069_review_20261003.md)均通过。[探针请求](probe_request.json)保持提交时原件；统一执行者已完成 Qwen3.6 首轮 `gpu1003-aiohttp4075-qwen36-a1`，原 FrozenPatch 直评为136/136状态匹配、reward1。题主已核完整日志与候选语义，见[GPU作者读回](results4075_qwen36_a1_20261003.json)。独立执行证据复核也通过。Coder首轮 `gpu1003-aiohttp4075-coder-a1` 同样136/136状态匹配、reward1，题主语义及独立执行复核完成；[本轮结论](closure4075_20261003.json)固定两个结果。总回执已用总账工具ack，首轮活动交接清空；第二阶段样本由GPU按统一安排另记关联job。

该成绩由133 PASSED与3个固定C-only FAILED共同匹配构成，不能称136全PASS。Qwen3.6解题104.545秒；最终工件只修改 `aiohttp/http_parser.py`，新增字段名ASCII token校验与请求行解码前控制字符校验，没有只识别题面字面串。最初全ASCII请求行方案误拒UTF-8，公开回归检出两项失败后，模型修正了实现，最终公开parser为124 passed、5 skipped、3 deselected。当前未发现需要重修题目材料的新问题；这不宣称全HTTP协议正确。

## 实际结果

| 检查 | base | ALT2 主正对照 |
| --- | --- | --- |
| 修后题面非法字段名示例 | 未抛异常，公开断言失败 | 抛出 `InvalidHeader` |
| 修后题面 malformed status line 示例 | 未抛异常，公开断言失败 | 抛出 `BadStatusLine` |
| 公开 `test_http_parser.py` | 124 passed、5 skipped、3 deselected | 同左 |
| CC / 运行身份 | CC 2.1.205；UID/GID 54321；Python 3.9.21 | 同左 |
| 容器限额与清理 | 2 CPU / 4 GiB / 512 pids；容器、网络残留零 | 同左 |

两组各有完整输出与 13 项 harness 检查通过；公开症状根据实际输出判断，未把命令的 `expect=any` 或 runner 退出 0 当成修复成立。ALT2 补丁从宿主 stdin 以 agent 身份应用，CC 未收到补丁文件或私有验收材料。

独立的原 `probe_e2e --no-grade` 作业核实：实际首条模型请求的 user message 包含当前**完整题面**，UTF-8 SHA256 为 `c3253b921246dcb9c99490b35b129269eb54cf4276f67837a6bd14d73819d731`。预检、解释器激活、空工件冻结及运行清理完成。这里使用桩，只证明真实 CC 交付；没有运行基座模型或评分。旧固定版本还记录了私有命名空间变化，不用此作业宣称共享 Git 修复或原工件直评已验收；统一探针执行者另核其已修入口。

## 评分复用与用途边界

隐藏树、expected、测试入口与 v11 完全相同。复用[已独立验收的七方矩阵](../../r2e/aiohttp4075_acceptance.md)：ALT2/ALT1/ALT3/ALT4=1，原 gold/noop/DG1=0。expected 仍为 136 键、133 PASSED 与 3 FAILED；这轮未重跑评分矩阵。ALT2 为主正对照，原 gold 不能当正对照。

实际镜像无法导入 C parser；公开开发沿已验证的 Python 路径。三个正式 C-only FAILED 保留原范围解释，启用 C 扩展后必须重新核评分条件。旧镜像准备检查容器未有新增标签和限额，正常结束后已查无残留；历史事实保留，新 builder 由总协调统一验收。

当前允许用途是修订题目的探索性基座质量探针。Qwen3.6首轮的题主语义结论在既定纯Python范围内可接受；Coder候选也已核完整评分、公开工具结果和源码语义。其原9项工件包含源码与8项额外诊断/说明/.coverage，全部保持并实际投影评分；这属于整洁度问题，当前没有新材料阻断。Coder公开全套为124 passed、3 C-only failed、2 skipped、3 deselected，不能采用模型全PASS自述。没有训练或留出资格；aiohttp同仓题目仍整体划分。题主继续处理其余三题，不因排队移交而结束责任。

## 当前证据入口

- [作者实际结果清单](results4075_r069_20261003.json)：固定发布 812 成员、下载 87 原件均核 SHA，含逐控制输出与首请求证据索引。
- [fresh 公开静态阅读](materials/4075c653/public_reader_review_20261003.md)和[适配器非作者窄核](reviews/non_author_public_actor_wrapper_review_20261003.md)。
- [中性公开开发说明](public/4075_development_brief.md)：解释器、公开示例装配与公开回归命令；独立结果审查同时核其可交付性。
- 原件位于忽略证据目录 `runs/category2_repair_20260929/r2e_aiohttp/cpu-b/public_actor4075_r069_v1/final_artifacts/`。[结果独立审查](reviews/non_author_4075_cpu_r069_review_20261003.md)已逐项核原件并接受；作者结果JSON保留审查前冻结时点，不回写执行原件。
- GPU原件位于 `runs/ordinary_gpu_probe_20261002/remote/queue_v6/results/gpu1003-aiohttp4075-qwen36-a1/`；[独立执行复核](../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/aiohttp4075_qwen36_a1_execution_review.md)覆盖83份同步原件、原基线/FrozenPatch、133P+3F、清理与预算，未代替题主语义审计。模型与服务依据为[Qwen3.6运行验收](../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/qwen36_runtime_acceptance_v1.md)，固定模型revision为 `995ad96eacd98c81ed38be0c5b274b04031597b0`。

## 双模型回执与当前用途

[Coder题主读回](results4075_coder_a1_20261003.json)与[独立执行复核](../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/aiohttp4075_coder_a1_execution_review.md)分别核语义与运输；实际solve153.218秒、固定Coder revision `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`。两次均正常完成并清理，原FrozenPatch/基线保持。报告中的shared_entry路径/SHA错配已提供正确两对及code_v3依据，由统一执行者下次冻结处理，不重跑本题。

当前用途是既定无C扩展Python范围的探索性成功样本，两模型各一次不能估计可靠成功率。当前没有已知题目/环境缺陷或CPU复验；第二阶段同条件重复与稳定性分析仍待接续，不授予训练或留出资格。

