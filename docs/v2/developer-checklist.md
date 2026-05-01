# RepoHarness V2 Developer Checklist

## 修改前

- 阅读 `docs/v2/implementation-plan.md`、`docs/v2/scope-and-roadmap.md` 和 `docs/11-object-model-config-and-data-flow.md`。
- 确认当前阶段范围，不提前实现后续阶段能力。
- 检查 `git status --short`，不要回滚或提交无关既有改动。

## 修改中

- 保持 Task Adapter、Workspace Adapter、Agent Loop、Verifier、Exporter 的对象边界。
- 不让 hidden metadata、gold patch、baseline raw log、reward-only 字段进入模型上下文或训练 payload。
- 不让 provider raw request、raw response、reasoning summary 或 Authorization header 进入训练数据。
- 不把 `oracle_hidden_feedback` 默认样本标记为 trainable。
- 不把 Docker execution mode 表述为生产级安全沙箱。

## 阶段结束

- 运行当前阶段定向测试。
- 运行必要的第一版 replay 回归。
- 生成或更新该阶段机器可读产物。
- 更新 `docs/v2/implementation-log/` 阶段日志。
- 高风险阶段安排只读 sub agent 审查。
- 修复 P1 和 P2；P3 如果不适合当前阶段修复，记录为后续项。

## 提交前

```bash
git status --short
git diff --check
git diff --cached --check
```

只 stage 当前阶段相关文件。不要提交 `reference/claude-code-typescript-src/`，不要提交本地 secret 文件，不要提交与当前阶段无关的旧文档迁移。

## 最终验收

最终验收必须通过：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance \
  runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json \
  --assert-complete
```
