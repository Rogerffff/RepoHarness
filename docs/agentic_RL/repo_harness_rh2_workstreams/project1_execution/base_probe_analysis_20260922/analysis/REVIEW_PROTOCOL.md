# 轨迹审查协议（基座探针 2026-09-22，B 线）

你是 RepoHarness 项目 B 线的轨迹审查员。任务：审查一次"真实 Claude Code 求解 SWE-Gym 题"的完整产物，判断求解过程、补丁质量、评分是否可信，并给出归因。**只读分析**：除了把报告写到指定路径，不修改任何文件；不运行容器、不联网、不 ssh。工作目录是仓库根（下文路径均相对它）。

## 背景（先读，约 5 分钟）
- `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/base_model_probe_run_20260922.md` 的 §2、§3、§6、§7（求解入口、固定条件、已知接缝、运行记录）。
- `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/base_model_probe_design_20260921.md` 的 §5、§6。

## 材料位置（派发消息会给出 TASK / SOLVER / ATTEMPT 与题卡目录）
- attempt 目录 `ADIR = runs/base_probe_20260922/remote/runs/matrix/attempts/<TASK>/<SOLVER>/<ATTEMPT>`：`attempt.json`（输入身份、阶段事实、终止原因、候选摘要、清理；其中 `attempt_id` 也是网关 session 名）、`prompt.txt`（模型实际收到的题面）、`transcript.md`（压缩转写；超长工具输出保留首尾）、`trajectory.jsonl`（CC stream-json 原件，含 partial 事件，很大，按需 grep）、`facts/`、`candidate/<TASK>.diff`、`grading/`（真实 RH2 评分：`ledger.jsonl`、`eval_logs/*.eval.log` 与 `*.diagnostics.json`、`artifacts/`、可能有 `recipe/`）。
- 网关留证 `runs/base_probe_20260922/remote/gateway/<deepseek|coder|q36>/<attempt_id>/`：`requests.jsonl`（每次模型请求全文）、`responses.jsonl`、`resp_*.sse`、`usage.json`。
- 自部署 solver（Coder / Qwen3.6）另有 adapter 逐轮记录 `runs/base_probe_20260922/remote/gateway/<coder_adapter|q36_adapter>/<attempt_id>.turns.jsonl`：每轮的 prompt/输出 token 数、finish_reason、**模型原始输出文本 `raw_output`** 与 adapter 解析后的 `parsed`。工具调用异常时，用它区分"模型写错了调用格式 / 参数"与"adapter 解析器丢了或解析坏了调用"。
- 私有材料（**第二阶段才能打开**）：gold 补丁 `runs/base_probe_20260922/remote/gold/<TASK>.gold.patch`；测试补丁与 FAIL_TO_PASS / PASS_TO_PASS 清单在 `docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/grading_bundles_v2_v0.jsonl` 里 instance_id 为本题的那一行（用 python 取，不要整文件打印）；静态题卡目录由派发消息给出（`card.md`、`review.md`、`analysis_before_history.md`、`public_read.md`）。
- 已完成的同题报告在 `runs/base_probe_20260922/analysis/<TASK>/`，第二阶段可参考，不要改。

## 两个阶段，顺序不能反
**阶段一（盲审）**：不要打开 `grading/`、gold、测试补丁、题卡、其它尝试与既有报告。只读 prompt、transcript（必要时查原件）、candidate diff、`facts/`、attempt.json 中与评分无关的字段、网关与 adapter 留证。回答：
1. 模型是否建立了公开复现（命令、现象）；
2. 是否读到相关源码，定位是否正确；
3. 编辑是否生效，是否运行了合理验证（验证了什么，结论是否被模型正确解读）；
4. 工具使用是否正常：逐类统计 `tool_result is_error` 的原因（参数缺失 / 类型错误 / 文件未先 Read / 字符串不唯一 / 命令失败等）、重复循环、并行调用、是否使用了与修 bug 无关的工具（Workflow、SendMessage、Cron*、ScheduleWakeup、TaskCreate、Skill 等）、是否读取 `/testbed/.harness/`（harness 自己的轨迹文件）、是否在 60 回合上限附近被截断；
5. 是否遇到环境障碍（解释器、依赖、权限、网络）以及如何应对；
6. 是否有答案渠道探测（联网、pip download / 安装被测项目新版本、读 site-packages 里的新实现、git 历史 / 未来对象等）及其结果；
7. 终止是否正常，最终交付说明与实际 diff 是否一致；
8. 自部署 solver 另答：上下文长度走势（是否逼近 131072）、单轮输出是否撞 `max_new_tokens`、thinking 是否异常冗长或空转、`raw_output` 里有没有未被解析成工具调用的调用文本。
先把阶段一结论写入报告文件，再继续。
**阶段二（核对）**：打开评分材料、gold、测试补丁、题卡与同题既有报告。回答：
1. RH2 原分、F2P / P2P 逐项状态，安装段是否成功，候选是否确实被测试；
2. reward=1：候选与 gold 的语义差异，哪些差异被参考测试覆盖、哪些没有；若存在与公开需求不符而未被覆盖的行为，属疑似假阳性，给出具体输入与预期 / 实际；
3. reward=0：逐个失败测试给出名称、失败断言 / 报错原文、由候选哪处改动（或缺失）引起；它能否从公开需求或仓库既有约定推出（模型真实失败，还是参考测试误拒了合理解）；是能力失败、工具使用失误、环境 / 接口故障、预算截断还是任务 / 测试争议；
4. 是否改了测试文件，RH2 的分类 / 投影如何处置（ledger 的 classification / projection 字段；注意 `projection.ignored_paths`）；
5. 题卡登记的已知风险是否在本轨迹显现；
6. 归因标签与置信度。

## 输出
写到 `runs/base_probe_20260922/analysis/<TASK>/<SOLVER>/<ATTEMPT>.md`（目录不存在就创建）。中文，先给 5 行以内的结论摘要，再分"阶段一""阶段二""证据指针表（文件 + 行号或事件序号）"。正文 1500 字以内。末尾附一个 JSON 代码块：
```
{"attempt_id": "...", "reward": 0或1, "process_quality": "good|mixed|poor", "repro_built": true/false, "verification_run": true/false, "tool_anomalies": ["..."], "env_obstacles": ["..."], "answer_channel_probe": true/false, "answer_channel_obtained": true/false, "labels": ["model_success"|"model_failure"|"tool_misuse"|"env_or_interface_fault"|"budget_truncation"|"task_or_test_dispute"|"suspected_false_positive"|"suspected_false_negative"], "confidence": "high|medium|low", "followups": ["..."]}
```
纪律：每个结论指向可核对的证据；推断要标明是推断；不确定就写未知。最终回复用 8 行以内复述结论并附同一 JSON。
