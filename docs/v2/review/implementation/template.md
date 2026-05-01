# Stage XX 只读审查记录

## 审查方式

说明审查 agent、是否只读、是否修改文件。

## 审查重点

- 是否符合当前阶段范围。
- 是否符合 `docs/v2/implementation-plan.md`、`docs/v2/scope-and-roadmap.md` 和相关设计文档。
- 是否破坏第一版 replay-only 路径。
- 是否存在隐藏字段、provider raw response、reward-only 字段或 oracle feedback 泄漏。
- 是否缺少阶段验收测试或机器可读证据。

## 审查发现

### P1

记录必须立即修复的问题。

### P2

记录提交前必须修复的问题。

### P3

记录可以修复或明确留作后续的问题。

## 审查正例证据

列出通过证据。

## 审查负例证据

列出没有越界、没有伪装能力或被正确拒绝的证据。

## 修复后验证

```bash
列出验证命令
```

## 结论

说明是否可以进入下一阶段或最终验收。
