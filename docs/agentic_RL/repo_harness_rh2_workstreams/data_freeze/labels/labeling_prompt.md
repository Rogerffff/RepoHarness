# DF-4/5 静态质量打标 Prompt v1（SPICE 式三标签 + 泄漏扫描）

用途：对 SWE 任务的 problem_statement（含 hints_text 仅用于泄漏判定，不判定其他维度）做静态质量三标签 + 描述泄漏扫描。单题一次调用，输出严格 JSON。批量执行由 claude headless（`claude -p`）驱动，每题填充下方模板。

## Prompt 模板

```text
你是软件工程任务质量审计员。给定一个 GitHub issue 修复任务的题面，输出三个质量标签和一个泄漏判定。只依据给定文本判断，不要臆测仓库内容。

【题面开始】
{problem_statement}
【题面结束】
【issue 评论区（仅用于泄漏判定）开始】
{hints_text}
【issue 评论区结束】

按以下定义逐项判定：

1. issue_clarity（题意清晰度）：
   pass = 明确说了"什么行为错了/期望什么行为"，有可操作的复现或定位线索
          （报错信息、代码片段、具体 API 名、复现步骤任一即可）。
   warn = 能看懂要修什么，但缺复现线索或期望行为表述含糊，需要 agent 自行猜测边界。
   fail = 题面含糊到无法确定改什么（如只有一句抱怨、断链引用、或需要外部上下文才能理解）。

2. test_adequacy（可验证性，仅从题面推断）：
   pass = 题面描述的是可被测试断言的具体行为差异（错误输出/异常/返回值）。
   warn = 行为差异存在但边界模糊（如"性能更好""更合理"），测试可能只覆盖狭窄实现细节。
   fail = 题面诉求本质上不可由自动测试判定（纯风格/文档/主观体验）。

3. solution_leakage（解法泄漏，题面 + 评论区一起判）：
   pass = 无解法信息。
   warn = 有方向性提示（指出了大概哪个函数/模块该改，或贴了相关但非答案的代码）。
   fail = 含直接答案：完整/部分修复 diff、逐行改法描述、指向修复 commit/PR 的
          URL 或 hash、"Fixes #N 已在 X 修复"类表述。

4. leakage_evidence：若 solution_leakage 非 pass，摘录触发判定的原文片段（≤200 字符）；否则 null。

输出（严格 JSON，无其他文字）：
{"issue_clarity": "...", "clarity_reason": "≤50字",
 "test_adequacy": "...", "adequacy_reason": "≤50字",
 "solution_leakage": "...", "leakage_reason": "≤50字",
 "leakage_evidence": "... 或 null"}
```

## 判定规则（消费侧）

- 三标签任一 fail → 题目剔除（进剔除漏斗，记原因）。
- solution_leakage=warn → 保留但打 `leakage_watch` 标记，进入 DF-5 正则层交叉核对；正则层同时命中 → 升级 fail。
- 全 pass / 含 warn 的保留题：warn 计数进入 freeze manifest 统计。

## 校准协议

1. 本线程先亲自标 5 题（分层抽样，不看模型输出）→ `labels/calibration_human.jsonl`。
2. claude headless 跑 20 题试点（含那 5 题）→ 与人工对照，三标签逐项一致率 ≥80% 才放行批量；不足则改 prompt 锚点重试。
3. 批量跑 Lite 230 全量 → `labels/swe_gym_lite_quality_v0.jsonl`；抽 10% 复检。

## 正则层（DF-5，与 LLM 层独立运行后合并）

```text
命中即 leakage_regex=true：
  https?://github\.com/\S+/(commit|pull)/\S+
  \b[0-9a-f]{40}\b            （40 位 commit hash）
  (?i)fixe?[sd]?\s+(by|in)\s+#?\d+
  ^diff --git | ^--- a/ | ^\+\+\+ b/   （diff 片段特征，多行模式）
预期基线：SWE-Bench+ 报告同类数据 32.67% 实例含解法指针、4.3% 内嵌完整 patch。
若我们对 Lite 230 的总命中率（LLM fail+warn ∪ 正则命中）远低于 ~20%，
优先怀疑扫描漏检而非数据干净。
```
