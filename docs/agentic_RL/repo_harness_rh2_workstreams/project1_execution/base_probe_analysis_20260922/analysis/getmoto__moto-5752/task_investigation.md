# getmoto__moto-5752 任务级调查（基座探针 2026-09-22，B 线）

## 结论摘要

1. **判定：task_or_test_dispute（规范欠说明型误拒），置信度 high。** 拒绝机制是确定性证据；"标签 BeginsWith 是否应算本题验收范围"属规范裁定，留给用户。
2. 失败的 F2P 是 `test_describe_parameters__multiple_tags`。4 次都通过了它的前两个断言（即题面 MWE 的两种顺序），都死在第 3 个断言：`tag:hello` + `BeginsWith ["w"]` 期望 2、实得 0。
3. 题面里 BeginsWith 出现 0 次。第 3 断言检验的是 base 上另一处独立旧缺陷（标签分支不看 `Option`），与过滤器顺序无关。
4. 4 个候选是同一种自然窄修复（未命中 `return False`、命中 `continue`），与上游 issue 讨论里被回帖致谢为 "the solution" 的修法思路相同。
5. 没有环境 / 接口障碍。补丁小、用时短，是因为公开缺陷只需改几行，不是截断或敷衍。
6. 题卡的静态预测（窄候选修好公开顺序、只在 w/world 处被拒）被今晚 4/4 实测证实。

## 1. 失败测试、报错原文、候选与 gold 的差异

4 次报错原文相同：`AssertionError: the length of [] should be 2, but is 0`，位置 `tests/test_ssm/test_ssm_boto3.py:1069`，汇总行 `1 failed, 79 passed`。

| 尝试 | 候选做了什么 |
| --- | --- |
| deepseek a1 | 先收集同键标签值再判等值；未命中 False，命中 `continue`；另加顺序回归测试 |
| deepseek a2 | 单个 `not any(...)` 等值判断，其余同上 |
| qwen3.6 a1 | 同 deepseek a2 写法，只改源码 |
| qwen3.6 a2 | 同上，多一个 `tag_found` 变量 |

同机对照：noop 死在 1062 行（第 2 断言，"should be 1, but is 2"），gold 80 passed。pytest 在首个失败断言处终止函数，所以候选走到 1069 行，就证明 1053、1062 两条公开断言在正式评分条件下已通过。

与 gold 的差异：gold 把标签值收成列表并入通用 `Option` 比较，Equals 与 BeginsWith 都生效；4 个候选保留 base 的 `tag["Value"] in values`（不看 `Option`），只去掉了提前 `return True`。

## 2. 断言要求能否从公开材料唯一推出

| 行为 | 题面说了什么 | 测试要什么 | 候选给了什么 |
| --- | --- | --- | --- |
| 两个 Equals 标签过滤，两种顺序 | 标题、MWE、Expected：两种顺序都恰好 1 个 | 断言 1、2：长度 1 | 4/4 通过 |
| 标签 + BeginsWith 前缀 | 无 | 断言 3：`hello`/`w` 得 2 | 0，与 base 行为相同 |
| 同上，前缀恰为完整值 | 无 | 断言 4：`x`/`a` 得 1 | 未执行；静态可过（`"a" in ["a"]`） |

断言没有绑定消息文本、异常类型、字段名或排序，绑定的是一项题面未提的功能。

仓库内线索有，但不足以定范围。校验器（`models.py:1462-1468`）对非 Path 键放行 BeginsWith，通用分支对其它键按 `Option` 比较，所以"标签分支忽略 Option"是看得见的相邻缺陷。反方向的线索同样存在：base 里唯一的标签过滤测试用默认 Equals，BeginsWith 只测过其它键；同函数的 Label 分支就是"忽略 Option 加 continue"的先例，Qwen a1 正是照它写的。沙箱断网，模型无法核对 AWS。结论为 **partial**：缺陷可被发现，但"它属于本 issue 的验收"无法从公开材料推出。

## 3. 误拒的最小可区分证据与处置选项

- 三点对照：noop 死于 1062，4 候选死于 1069，gold 全过，P2P 均 79/79。候选修好了公开缺陷，只被断言 3 拒绝。
- Qwen a1 修复后打印两种顺序的返回 Name，都是 `['test_my_param_01_b']`；修复前第二种顺序返回 a 和 b。
- 断言 3 在 base 上同样得 0（`"world" in ["w"]` 为假）。这是静态推断，noop 没执行到该行。

额外要求的来源是 gold PR 的范围扩展，测试补丁注释原文为 `# tag begins_with should also work`。上游讨论（hints.txt，模型不可见，无署名）只有一段窄修法和一句致谢，没提 BeginsWith；该片段有 `parameter.tag` 笔误且缺 `continue`，只能说思路相同。AWS 真实行为未核实（本调查不联网）；凭记忆，AWS 文档允许 DescribeParameters 用 Equals/BeginsWith，未见 tag 例外，需另行确认。

处置选项（不替用户决定）：
- A：保留原题原测试，标"规范欠说明"，留诊断旁路，不进模型比较分母和训练池。
- B：另版本，题面补一句维护者说明（标签过滤应按 Option 生效，含 BeginsWith），原版保留；宜先核实 AWS 行为。
- B′：另版本，F2P 只留断言 1、2；这偏离 SWE-Gym 官方评分，属评分依据变更。
- C：仅作评测不作训练，报告时并列含与不含本题的分母。
- D：淘汰。

风险：原样进训练池比以上各项都差。全 0 组在组内相对优势下没有梯度；偶发通过的只会是"顺手扩范围"的补丁，被奖励的是超出题面的改动，不是修 bug 的能力。

## 4. 若按"模型共同失败"看

不成立为能力失败。共同点是对题面的字面解读，这也是最自然的解读：3/4 没有考察标签的 Option 语义；DeepSeek a1 考察了，以"issue 只涉及 Equals、最小改动、保留既有行为"为由明确放弃，其中"AWS 对 tag 可能只支持 Equals"是它未核实的猜测。对 RL：全 0 的原因是未公开要求，这样的题要等要求进入题面（B）或测试收窄（B′）后才有训练价值。

## 5. 环境 / 接口排查

无障碍。4 次均 `completed`，10–14 回合（上限 60），网关响应全部 200；解释器、pytest、源码导入与离线 mock 均正常。唯一的 `is_error` 是 Qwen a1 修复前的复现脚本按预期断言失败。没有联网、pip、git 历史、harness 目录访问或无关工具。Qwen 无截断，工具调用都被解析。

4 次都跑了既有测试且全过：DeepSeek a1 全文件 80 项（含自加测试），a2 为 28 与 79 项；Qwen a1 为 20 与 28 项，a2 为 20 与 79 项。Qwen 两次都跑了题面 MWE。

不影响结果的瑕疵：Qwen 最终文本尾部漏出 `<|im_end|>`；DeepSeek a2 总结称"79 passed 含新测试"，实际 79 是加测试之前跑的。DeepSeek 两次往官方测试文件里加了回归测试，RH2 投影按 `official_test_file` 忽略，只评源码文件。

## 6. 与题卡静态结论是否一致

一致，题卡预见了这个问题。题卡把本题定为范围待定的受限候选，写明"静态预测窄候选修复公开顺序而被 w/world 拒绝"；只读公开材料的那份阅读记录也独立判断标签 BeginsWith 是"相邻疑义"，不能自动扩大为必修。今晚等于用 4 个独立求解做完了题卡的"唯一优先实验"，拒绝点、P2P 保持、返回 Name 都与预测相符。

题卡没有的新信息：两款模型 4/4 都走窄路线，其中 1 次是明确权衡后放弃扩展。这支持"窄解读是自然解读"，但不能替代规范裁定。题卡记的 5134 版本关系与本次失败无关；它担心的 actor 条件今晚没出问题。

## 证据指针表

路径前缀：`M` = `runs/base_probe_20260922/remote/runs/matrix/attempts/getmoto__moto-5752`，`X` = `runs/base_probe_20260922/remote/runs/x1_controls/getmoto__moto-5752`，`G` = `runs/base_probe_20260922/remote/gateway`，`CARD` = 题卡目录 `.../expansion/batch02/results/getmoto__moto-5752`，`PUB` = `runs/swegym_quality_batch02_20260921_v2/public/getmoto__moto-5752`。

| 结论 | 证据 |
| --- | --- |
| 题面未提 BeginsWith；Expected 只要求两种顺序各 1 个 | `M/*/*/prompt.txt`（四份 md5 相同）第 3、77–79 行；`grep -c BeginsWith` 为 0 |
| F2P 四个断言与注释 `# tag begins_with should also work` | `docs/.../s2/ingest/grading_bundles_v2_v0.jsonl` 本题行 `test_patch`；补丁后文件 1053 / 1062 / 1069 行为断言 1 / 2 / 3 |
| deepseek a1 失败原文与位置 | `M/deepseek-v4-pro/a1/grading/eval_logs/*.eval.log`:954、994–996、1102–1103 |
| deepseek a2 同上 | `M/deepseek-v4-pro/a2/grading/eval_logs/*.eval.log`:956、996–998、1104–1105 |
| qwen a1 同上 | `M/qwen3.6-35b-a3b/a1/grading/eval_logs/*.eval.log`:953、993–995、1101–1102 |
| qwen a2 同上 | `M/qwen3.6-35b-a3b/a2/grading/eval_logs/*.eval.log`:957、997–999、1105–1106 |
| noop 死于第 2 断言；gold 全过 | `X/noop/eval_logs/*.eval.log`:930、963–965、1072；`X/gold/eval_logs/*.eval.log`:1041；两份 `ledger.jsonl` |
| 评分有效：安装 rc=0、候选已应用、80 项被解析、P2P 0 失败 | `M/*/*/grading/ledger.jsonl` 的 `install`、`report`、`verdict_diagnostics`；a1 eval.log:416–417（候选 hunk）、428–430、904 |
| DeepSeek 的测试改动被投影忽略 | `M/deepseek-v4-pro/{a1,a2}/grading/ledger.jsonl` 的 `projection.ignored_paths` |
| 4 个候选与 gold | `M/*/*/candidate/getmoto__moto-5752.diff`；`runs/base_probe_20260922/remote/gold/getmoto__moto-5752.gold.patch` |
| base 标签分支不看 Option；校验器放行 BeginsWith；Label 先例 | `PUB/base/moto/ssm/models.py`:1608–1613、1462–1468、1601–1607 |
| base 无 tag+BeginsWith 既有测试 | `PUB/base/tests/test_ssm/test_ssm_boto3.py`:1039（唯一标签过滤，默认 Equals）；BeginsWith 仅见 175、705、753 行 |
| DeepSeek a1 看到并明确放弃 BeginsWith | `M/deepseek-v4-pro/a1/transcript.md`:500–502、944 |
| 其余 3 次未考察标签 Option | 对四份 `trajectory.jsonl` 的 thinking / text 检索 `BeginsWith`：a1 以外为 0 命中 |
| Qwen a1 修复前后两种顺序的返回 Name；照 Label 先例写 | `M/qwen3.6-35b-a3b/a1/transcript.md`:484–498、622–626、540–549 |
| 既有测试运行结果 | transcript：deepseek a1:1034、1070；a2:820、858、920；qwen a1:696、774；a2:347、389、433 |
| 上游讨论只有窄修法与致谢（模型不可见） | `runs/env_overnight_20260916/L1_moto_2/mat/getmoto__moto-5752/hints.txt` |
| 无接口故障、无截断 | `M/*/*/attempt.json`（termination、num_turns、tool_result_errors）；`G/{deepseek,q36}/<attempt_id>/responses.jsonl` 全 200；`G/q36_adapter/<attempt_id>.turns.jsonl` |
| 题卡的预测与范围疑点 | `CARD/card.md` 第 5、9、13 行；`CARD/review.md` 第 16–17、22、48 行；`CARD/public_read.md` 第 18、38 行 |
| prompt 不含 public_hints | `docs/.../project1_execution/base_model_probe_run_20260922.md` 第 33 行 |

```json
{"task": "getmoto__moto-5752", "verdict": "task_or_test_dispute", "confidence": "high", "failed_test": "tests/test_ssm/test_ssm_boto3.py::test_describe_parameters__multiple_tags", "requirement_derivable_from_public": "partial", "per_attempt": [{"attempt": "deepseek-v4-pro/a1", "candidate_summary": "标签分支改为收集同键标签值、未命中 return False、命中 continue；保留不看 Option 的等值匹配；另加顺序回归测试（被投影忽略）。thinking 中看到校验器放行 BeginsWith，以 issue 只涉及 Equals 为由明确不扩展", "failure_reason": "F2P 第 3 断言 tag:hello BeginsWith ['w'] 期望 2 实得 0（test:1069）；前两条公开顺序断言已通过；P2P 79/79"}, {"attempt": "deepseek-v4-pro/a2", "candidate_summary": "not any(键相等且值在 values 内) 则 False，否则 continue；另加顺序回归测试（被投影忽略）；未考察标签 Option 语义", "failure_reason": "同上：仅第 3 断言（题面未提的标签前缀匹配）失败"}, {"attempt": "qwen3.6-35b-a3b/a1", "candidate_summary": "照 Label 分支先例写的单行 not any(...) 加 continue，只改源码；修复前后都跑了题面 MWE 并打印返回 Name", "failure_reason": "同上：仅第 3 断言失败"}, {"attempt": "qwen3.6-35b-a3b/a2", "candidate_summary": "tag_found = any(...)，未命中 False、命中 continue，只改源码；跑了题面 MWE 与全文件 79 项", "failure_reason": "同上：仅第 3 断言失败"}], "disposition_options": ["A 保留原题原测试，标注规范欠说明，留诊断旁路，不进模型比较分母与训练池", "B 另版本：题面补充维护者说明（标签过滤按 Option 生效，含 BeginsWith），原版保留；先核实 AWS 行为", "B′ 另版本：F2P 只留与题面对应的断言 1、2；偏离 SWE-Gym 官方评分，属评分依据变更", "C 仅作评测不作训练，报告并列含与不含本题的分母", "D 淘汰"], "followups": ["核实真实 AWS 对 tag 键加 BeginsWith 的行为（本调查未联网，未核实）", "把今晚 4 个窄候选的实测结果回填题卡的唯一优先实验（由题卡归属方执行）", "若选 B：新版本需重做 noop/gold 对照，且不得把新版结果回填为原版成功", "Qwen adapter 最终文本漏出 <|im_end|>，回交 A 线确认是否只是展示层问题", "candidate_test_like_paths 为空而 projection.ignored_paths 含测试文件，两字段口径请 A 线确认"]}
```
