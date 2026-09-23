# I21 修复聚焦复核：IR1–IR3（2026-09-20，Codex A 分叉）

**结论：IR1、IR2、IR3 均核销，本轮没有新增阻塞项或用户决策。** 公共评测入口与共享引擎适配的本机修复审查通过；A 独立作业的驱动证据、固定模型加载、I22 与真实引擎验证维持原分期。不能据此把 I21 的全部交付或 GPU 链路写成完成。

对象为主仓库 `bac7659ea70cc07a3a8c872a29e7659a894afc5a` 上的 I21 未提交改动，加 miles fork `227806cfbf8ae1743ff0243dadb030ead7b87509`。fork 工作树干净；13 个相关源文件在探针与测试结束后的摘要一致。详见 [verification.json](verification.json)。本轮只写审查工件与导航，未改生产代码、维护测试、配置或 fork，未提交、push、运行 Docker/GPU/远端作业，也未向其它任务发送消息。

## 1. 三项核销依据

| 问题 | 修复与独立证据 | 判断 |
| --- | --- | --- |
| IR1 / P1：unsafe 评测结果误撞训练 mask 检查 | 编排出口用输入样本承载评测结果，随后盖 termination 事实。原探针的同 top-p unsafe、不同 top-p unsafe、不同 top-p 正常产物三案分别得到 `None / None / 1.0`，没有转换异常，绑定均释放；unsafe 不调用评分。维护测试另证实只有一条输入样本交付、无训练 admission、保留 termination 事实；训练 top-p<1 真缺 mask 仍拒绝。 | 核销；没有给评测补伪造 mask 或放松训练检查。 |
| IR2 / P1：过滤后的存活题目冒充计划、零样本日志崩溃 | 计划来自题包，成员按 `(task_id, sample_slot)` 核对；0019 将调用事实保留在数据集结果。独立探针使用真实 prepared 题包、真实 Dataset 过滤、真实派发函数体及外层 miles 日志 → RH2 钩子，覆盖下表。 | 核销；部分过滤如实缺失，全部过滤仍有评测点、不回落默认日志。 |
| IR3 / P2：评测重评分计入训练 | 报告在单个 run 内按 trajectory 与 audit 连接。训练、评测、无 audit 各一条事件，三类均为 1；仅评测重评分时训练计数为 0。补做两个 run 重用同名 trajectory 的对照，未串账。 | 核销；未知归属单列，不猜成训练。 |

实现锚点：`adapters/slime/generate.py:2554`（出口顺序）、`adapters/slime/eval_result.py:132,150`（占位与载体）；`adapters/miles/eval_report.py:76,257,322`（成员集合、题包、钩子）；`adapters/miles/run_report.py:275,865`（分流与 run 范围）。路径均在 `rh2/src/repoharness2/` 下。fork 的调用级事实见 `miles/rollout/inference_rollout/inference_rollout_eval.py:171`。

顺带的简化也接受：`generate_fn.py:102` 只读已加载宿主模块标记，生产路径中的静态源码识别已移回测试。`FullyAsyncRolloutFn` 将数据集结果原样包装为 `RolloutFnEvalOutput.data`，RolloutManager 原样传给日志；0019 的调用事实在这些消费者之间没有被删去。

## 2. 过滤与日志运输的独立对照

下表均由真实日志钩子读取题包，未使用上一轮不带题包的直接 helper 调用作为完整性证明。两题的长度由假 tokenizer 控制，模型、Docker 与 harness 为 CPU 替身。

| 场景 | planned / received / graded | complete | missing / 未加载题数 | 评分比例 / 计划解决比例 |
| --- | --- | --- | --- | --- |
| 两题均不过滤 | 2 / 2 / 2 | true | 0 / 0 | 1 / 1 |
| 第二题被过滤 | 2 / 1 / 1 | false | 1 / 1 | 1 / 0.5 |
| 全部过滤 | 2 / 0 / 0 | false | 2 / 2 | None / 0 |
| 第一题被过滤，每题采样两次 | 4 / 2 / 2 | false | 第一题的槽 0、1 / 1 | 1 / 0.5 |
| 有结果但日志侧题包不可读 | 1 / 1 / 1，来源明确为加载后宿主数量 | false | 计划未知 / None | 1 / 1，不能据此声称完整 |
| 两题均派发，reward 为 `[1, None]` | 2 / 2 / 1 | false | 0 / 0；另列 reward_unavailable=1 | 1 / 0.5 |

六次调用都使用 rollout 标签 0，仍各有不同的 `eval_point_id`。全过滤时绑定为 `unverified`，其余有观察版本的场景为 `verified`；完整性和绑定没有混为一个结论。合法非空 s1_compat 的不接管正控在维护测试中通过。

**澄清交接表述：** “没有任何 0 分”应理解为不伪造样本 reward=0、不把缺失记成模型答错。全过滤时 `rewards=[]`、`unresolved=0`、`resolved_rate_graded=None`，但 `resolved_rate_planned=0.0` 确实会记录，表示既定题单的解决比例下界。当前代码与既定双分母口径一致，不需要为这句话改算法或再加闸门。

## 3. 验证与边界

| 验证 | 本轮独立结果 |
| --- | --- |
| 8 个 I21 测试文件 | **73 passed**，零 skip，见 [focused_tests.log](focused_tests.log)。包含训练真缺 mask 的拒绝对照、三类结果、混合 None 与 s1_compat 正控。 |
| 完整 C5 双 lane | **A 461 passed / 329 skipped；B 790 passed / 0 skipped**。A 的 skip 来源检查、fork 干净工作树与树摘要、18 个语义 patch 存档摘要、原始 pin 检查均通过。见 [integration_lanes.log](integration_lanes.log)。 |
| 独立探针 | **11 组通过**，包括原 unsafe 反例、6 个题包/过滤/日志场景、仅评测与混合重评分（含跨 run 对照）。见 [probe.py](probe.py)、[results.json](results.json)、[probe.log](probe.log)。 |
| 相关源码与 8 个 I21 测试的 ruff | 通过，见 [ruff.log](ruff.log)。 |
| 未重复或未运行 | 未重跑全 CPU、评分/Docker/GPU/远端作业。上一轮已证明六项 dp_schedule 导入失败来自 I21 之前的共享工作树；本轮不再扩大复查，不声称全 CPU 绿色。 |

探针第一次执行时，新增的跨 run 夹具漏了输入 `_bundle`，导致 audit 按既有规则被归为未知；修正夹具为每个 run 独立 bundle 后通过。保留 [probe_fixture_error.log](probe_fixture_error.log)，这不是生产回归；没有为通过探针修改生产归属规则。

可重跑命令（从仓库根目录）：

```bash
bash rh2/scripts/miles_integration_lanes.sh
cd rh2
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" uv run pytest -q tests/adapters/test_i21_eval_{delivery,wiring}.py tests/adapters_miles/test_i21_eval_{bringup_vertical,entry,fork_seams,identity,report,run_report}.py
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch5_launch_eval_20260919/i21_fix_followup_20260920/probe.py
```

## 4. A–N 适用性与停止条件

本轮为三项修复的聚焦复核，沿用[上轮切片审查](../i21_implementation_review_20260920/README.md)，不重新启动全链审计。

| 维度 | 本轮证据与界限 |
| --- | --- |
| A / E / G：正确性、测试有效性、真实入口 | 原 unsafe 反例仍走真实入口与 canonicalize；过滤走真实 Dataset 与日志运输。设备替身范围已明确，不把 AST/CPU 证据当作真实引擎运行。 |
| B / C / F：分布、挡板、决定一致性 | 训练缺 mask 仍拒绝；漏测长题保留在计划中。未增加长度过滤禁止项或 train/eval 互斥，未修改训练 loss、评分或处置决定。 |
| D / H：所有权与事实来源 | 结果载体归输入样本；既定任务来自 prepared 题包，加载后数量与调用身份来自宿主；重评分使用现有事件和 audit，未知保持未知。 |
| I / J / K：分期、可读性、演进成本 | IR1–IR3 收口；源码静态探测从生产移回测试；未为修复引入新调度服务或评分契约。A/I22/GPU 后置项继续明确登记。 |
| L / M：效率与观测 | 读取题包发生在每次评测汇总，未放到逐 token 路径；本轮不测设备吞吐。计划、缺失、零结果、重评分归属可解释；共享引擎与在飞训练竞争仍留真实 GPU 诊断。 |
| N：依赖兼容 | 0019 仅给结果 dict 增调用事实，原字段保留；两条 lane、pin 和 patch 存档核验通过。 |

**停止条件已满足：** 不继续扩审这三个问题。后续如果源码再改、真实引擎出现新证据，按相应边界再审；不以本机修复通过替代独立作业接线、模型加载或正式训练前验证。
