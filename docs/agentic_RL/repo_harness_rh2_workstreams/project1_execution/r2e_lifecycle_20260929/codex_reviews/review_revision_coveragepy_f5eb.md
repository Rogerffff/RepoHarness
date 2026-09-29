## 结论

**R-c 通过，可先落正式修订单，不必等待 C1 裁定。R-b 窄版技术上可行，但本题属于 P5 输出范围选择，不能直接按预授权落地。决定包需小改。**

本轮只读核对了源码、补丁、草案与日志，并在内存中重放修订、复算摘要和解析结果；未修改文件、未重跑容器。

### 1. 模板与公开依据

**R-c 用对了。** 一条文本替换只是承载方式；两个新增测试分别针对“非示例计数”和“报告配置与已保存数据不同”两个窄问题，依据分别成立。原四个测试未改，expected 从四键增至六键，没有删键或遗留 unexpected。内存重放得到的两个版本摘要均与草案一致。

- **BRANCHY 的 6/0/4/2 不是抄 gold。** 三个 `if` 各有两个出口，共六条分支弧；`f/g` 的四条全部执行，未调用的 `h` 留下两条未执行弧，其条件行也未执行，因此部分分支数为零。公开 `results.py:35–36、201–204` 区分 missing、partial 和 executed；公开测试还明确验证“未调用函数：partial=0、missing=2”。题面第 21 行没有把数值限定为示例的 1/1。参见[题面](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/user_prompt.txt:21)、[计数定义](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/worktree/coverage/results.py:35)、[公开测试](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/worktree/tests/test_api.py:964)。
- **保存后另起报告对象仍须输出 4/2，有公开依据。** `doc/branch.rst:38–54` 描述先测量、后报告；`cmdline.py:374–388` 的 JSON 子命令没有 `--branch`，随后构造对象、`load()`、`json_report()`（532–545、578、602–609）。现有 JSON 分支字段本来就按数据 `has_arcs()` 门控。参见[文档](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/worktree/doc/branch.rst:38)、[CLI](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/worktree/coverage/cmdline.py:374)、[现有门控](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/worktree/coverage/jsonreport.py:59)。

### 2. 验收与候选

日志复算支持草案报告的全部试跑结果：

| 候选 | R-c | R-c＋R-b |
|---|---:|---:|
| gold | 1 | 1 |
| A1 | 1 | 未跑 |
| noop、D0、C2、C3 | 0 | 0 |
| W2 | 0 | 未跑 |
| C1 | 0 | 1 |
| C1swap | 未跑 | 0 |

修订版每次均解析六键，无 missing/extra；C3 **只在保存后报告测试因缺键失败**；C1 在 R-c 下仅原 BC 失败；C1swap 在 R-b 下确实失败于 BRANCHY 的每文件计数。[试跑证据](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/trials)

- **W2 合理**：交换两个不同语义的计数；原示例 1/1 掩盖错误，BRANCHY 的 4/2 能识别。
- **A1 合理**：逐文件累加 `branch_stats()` 的 `taken` 和 `total−taken`，与公开计数定义及 XML 算法等价，不依赖 gold 的属性读取写法。gold 仍是正式正对照，A1 是补充证据。
- 原材料上 D0/C2/C3 的正式满分及 C1 的零分，补丁、日志摘要和执行完整性均核对一致。

**尚不能声称正式验收完成。** 落材料、重建镜像后仍须正式评分。W2 已成为已知相关错误候选，[计划第 399 行](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/revision_plan.md:399)不宜继续把它列为可选；采用 R-b 后还须正式复验 C1、C1swap。

### 3. 需求边界与 R-b 裁定

R-c 没有扩大需求、为保 gold 放宽要求或泄漏答案；原有公开测试与新增 totals 冲突的 P6 仍在，但没有加重。

**我不同意既有复核“R-b 属于模板内”的结论：**

- 每文件七键约束来自公开 `tests/test_json.py:35、50–58`，是可见输出形状，不是纯内部实现细节。totals 部分过时，不能自动证明每文件部分也无效。[公开原文](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/worktree/tests/test_json.py:35)
- 对称扩展也有合理依据，但**“依据弱”不等于 R-b 要求的“没有公开依据”**。允许扩展还是保持键集，是输出范围选择；不因 totals 数值相同就排除 P5。[v1 边界](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md:125)

R-b 草案本身足够窄：成对、验值，保留旧字段与行模式约束。**可推荐 A，但推荐不等于已授权。** B 的题面句子没有泄漏隐藏细节，然而选择该读法同样须用户决定，之后再做新公开读者验收。

### 4. 决定包需小改之处

选项、成本、双方依据及未来提交不可作公开依据，整体呈现公允；需修正：

1. **[§6.5 第 296 行](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/revision_plan.md:296)**：既按 P5 处理，未裁定前应暂挂为问题定位，不能仅以“非核心附加输出”为由交协调者直接放入正式能力比较／`probe_ready`。这不阻塞 R-c 落单。
2. **第 274、309 行措辞**：“与题意无关的奖励噪声”应改为条件判断；当前只能确定规格有争议。若用户选择保持键集，C1 就是违反所选范围。跨题材料使 C1 更常见也只是风险推测，尚非实测。
3. 正式验收矩阵把 **W2 改为必跑**，不要把 R-b 下未跑的 W2/A1写成已验证。

因此：**R-c 放行；R-b 暂待 P5 裁定；整题尚未获得正式探针准入结论。**