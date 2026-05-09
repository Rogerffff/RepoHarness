# 第 0 章：V4 最新状态校准

## 本章链路图

```text
closure commit e0da89c
-> runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json
-> runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json
-> runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json
-> docs/v4/final-acceptance.md 和 docs/v4/walkthrough.md 当前哈希被 doc-sync bundle 绑定
```

## 本章实际运行或查看的命令

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v4-inputs \
  runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json \
  --assert-complete

PATH=.venv/bin:$PATH repo-harness inspect-v4-acceptance \
  runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json \
  --assert-complete

PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle \
  runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json \
  --assert-immutable

git rev-parse --short HEAD
git show -s --format='%h %s' e0da89c
```

运行结果：

- `inspect-v4-inputs`：`complete`，`passed`，共 26 个 input categories。
- `inspect-v4-acceptance`：report status 为 `passed`，`complete`，`passed`。
- `inspect-acceptance-bundle`：`immutable`，`passed`。
- 当前 HEAD 为 `e0da89c`。
- closure commit 是 `e0da89c test: refresh V4 acceptance evidence after hardening`。

## 源码入口和对象流

本章主要不是读源码，而是确认当前讲解口径的 evidence 根目录：

- `runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json`
- `runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json`
- `runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json`
- `runs/v4-final-rerun-20260504T194758Z/acceptance/final_acceptance_command_log_doc_sync_20260505T075410Z.jsonl`

与文档口径相关的文件：

- `README.md`
- `AGENTS.md`
- `docs/v4/final-acceptance.md`
- `docs/v4/walkthrough.md`

关键理解：

- `acceptance_inputs` 显式绑定所有输入 evidence，避免从 latest run 自动发现。
- `acceptance_report` 给出 role-level pass / fail 结论。
- `acceptance_bundle_manifest_doc_sync_20260505T075410Z.json` 额外绑定当前版本的 post-acceptance documentation refs，解决文档同步后旧 bundle 哈希不再对应当前文档的问题。

## 面试追问与推荐回答

问：为什么要有 doc-sync bundle，不能继续用旧 bundle 吗？

答：`docs/v4/final-acceptance.md` 和 `docs/v4/walkthrough.md` 是 post-acceptance documentation refs。文档同步后文件 sha256 会变化，如果继续声称旧 bundle 绑定当前文档，就是不可审计的。V4 的做法是在同一个最新验收目录下生成新的 doc-sync bundle，让当前文档哈希也能通过 immutable inspect。

问：当前 V4 到底是什么状态？

答：V4 已完成复核问题修复，并通过修复后最终验收。最新 closure commit 是 `e0da89c`，最新验收目录是 `runs/v4-final-rerun-20260504T194758Z/`，完整测试结论是 `712 passed`，并且 V4 acceptance report 和 doc-sync bundle inspect 都通过。

问：这个项目能不能说是完整 SWE-Bench 复现？

答：不能。RepoHarness 当前重点是软件工程智能体训练和评测轨迹的生产、审计和导出基础设施；它有固定 SWE-Bench-like 子集和真实仓库任务，但不宣称为官方 SWE-Bench harness、公开榜单系统或生产级安全沙箱。
