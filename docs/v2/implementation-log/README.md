# RepoHarness V2 Implementation Log Index

第二版按 15 个阶段提交和审查。每个阶段日志记录目标、实现内容、主要文件、机器产物、验证命令、正例证据、负例证据、降级项、限制、sub agent 审查和是否可以进入下一阶段。

## 阶段日志

- [Stage 01](stage-01.md): 第二版 schema、版本常量和基础测试。
- [Stage 02](stage-02.md): run config facts、最终 run metadata、本地环境指纹和 tool schema snapshot。
- [Stage 03](stage-03.md): inspect-run 第二版展示和 legacy metadata 兼容。
- [Stage 04](stage-04.md): export audit、training eligibility、manifest 和 Markdown audit。
- [Stage 05](stage-05.md): preference pair 硬门控和 compare scope。
- [Stage 06](stage-06.md): ExperimentConfig 最小多 rollout runner。
- [Stage 07](stage-07.md): ModelClient 协议、replay/fake 兼容层和 scaffold registry。
- [Stage 08](stage-08.md): single_shot_patch scaffold。
- [Stage 09](stage-09.md): planner_coder_verifier scaffold。
- [Stage 10](stage-10.md): mock provider 和 provider artifact。
- [Stage 11](stage-11.md): DeepSeek primary real provider、OpenAI fallback 和 smoke report。
- [Stage 12](stage-12.md): repo materialization、命令环境策略门和 parser policy。
- [Stage 13](stage-13.md): replay task set 扩展到 20 个任务。
- [Stage 14](stage-14.md): Workspace backend path 和 Docker interface-only 状态检查。
- [Stage 15](stage-15.md): 最终验收、文档、示例和审查收口。

## 审查记录

审查记录位于 `docs/v2/review/implementation/`。高风险阶段 Stage 04、Stage 07、Stage 10、Stage 11、Stage 12、Stage 13、Stage 14 和 Stage 15 均安排了只读审查。

## 最终验收

最终验收报告：

- `runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json`

最终验收检查命令：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance \
  runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json \
  --assert-complete
```
