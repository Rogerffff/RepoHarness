# 下一轮可以继续深挖的问题

这个文件用来记录后续你想继续追问的实现细节。这里的问题不是基础概念，而是适合做代码 walkthrough、面试追问准备和实现审查的问题。

## 建议优先深挖

1. 真实 PR / issue 任务目前哪些候选已经有完整 source archive、baseline verifier、post-patch verifier 和 flaky probe evidence？

2. 当前 Docker image 默认偏 Python / pytest，Go、Node.js、Rust 候选任务要进入正式 run-task，需要扩展哪些配置、镜像、命令 policy 和 verifier parser？

3. `PermissionSystem` 当前对 `bash` 的 allowlist 是否会限制真实 agent 调试能力？哪些命令应该保持禁止，哪些命令可以以更结构化工具形式开放？

4. SWE-Bench-like final verifier 中 baseline verifier workspace、verifier patch reference、selector cache 和 agent final patch 的绑定关系是否足够清楚？

5. `ContextManager.prepare_messages` 的 deterministic preview replacement 会不会影响训练样本的可解释性？export 时怎样标注上下文压缩前后的边界？

6. provider raw request / response artifact 当前脱敏粒度是否足够？哪些字段允许训练，哪些字段只允许审计？

7. `RewardMetadata` 的字段 allowlist 是否已经在实现层真正校验字段路径？如果要防 reward hacking，最小可靠策略是什么？

8. preference pair trainability 应该怎样证明“同任务、同源码、同 verifier plan、同策略可比较性”？

9. 当前 V4 final acceptance 重新生成需要哪些命令？每个命令会读取哪些 evidence，写出哪些新产物？

10. 如果面试官要求现场画架构图，最合理的是画 run-task 单任务链路，还是画 V4 evidence pipeline？两张图分别应该怎样画？

## 我建议下一次讲解的顺序

如果继续往下过，我建议不要再扩展新范围，而是直接拿一条真实产物做纵向追踪：

```text
runs/v3-core-realrepo-deepseek-20260504T000000Z/agent_loop_runs/...
```

或者：

```text
runs/v3-final-swebench-agent-loop-20260503T035615Z/agent_loop_runs/...
```

逐个打开：

- `task.yaml`
- `run_config_facts.json`
- `docker_backend_facts.json`
- `container_execution_facts/manifest.json`
- `events.jsonl`
- `transcript.jsonl`
- `artifacts.json`
- `baseline.json`
- `resolved_verifier_plan.json`
- `final_verifier_result` artifact
- `run_metadata.json`

这样可以把这批讲义里的静态代码链路，变成你亲眼看过的真实运行证据链。
