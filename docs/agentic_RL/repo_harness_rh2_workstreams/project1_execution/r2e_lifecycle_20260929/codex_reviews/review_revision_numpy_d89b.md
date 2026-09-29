## numpy_d89b：需小改

四项修订方向成立。**唯一需要改动测试的地方：R-c2 两处告警过滤应改为 `sup.filter(Warning)`，不要限定四种类别。** 当前草案尚不能原样落正式修订单。

### 1. 模板与公开依据

| 修订 | 核对结果 |
|---|---|
| **R-c1：排除离群样本后归一** | 成立。[题面第22行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/user_prompt.txt:22)明确要求 “the integral over the range is 1”；[2D 文档561–565、590–592行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/worktree/numpy/lib/twodim_base.py:561)明确离群值不计入，并给出密度公式。[公开测试110–117行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/worktree/numpy/lib/tests/test_histograms.py:110)同时验证带权、不带权的区间内积分。显式 bins 构造离群值没有越界。 |
| **R-c2：保留 `normed=True` 行为** | 成立。[ND 文档848–855行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/worktree/numpy/lib/histograms.py:848)与上述2D文档均公开承诺密度行为；[公开测试223–231行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/worktree/numpy/lib/tests/test_twodim_base.py:223)就是新增2D断言的来源。**行为要求有依据，告警类别限制没有。** |
| **R-b：逐位相等改为 allclose** | 用对。公开旧测试[738–745行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/worktree/numpy/lib/tests/test_histograms.py:738)针对旧 `normed` 路径，不能推出新 `density` 路径必须使用相同运算顺序。草案保留数值一致性（`rtol=1e-7, atol=0`）和边界精确相等；ORD 保留旧路径，只改变新路径的除法顺序，合理性依据充分。 |
| **R-c3：`density=False` 返回计数** | 成立，但属于**公开 API 先例推知，不是题面明示**。[一维文档607–609行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/worktree/numpy/lib/histograms.py:607)明确 “If False … number of samples in each bin”；[公开测试81–83行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/worktree/numpy/lib/tests/test_histograms.py:81)直接验证。 |

三项 R-c 各对应一个窄问题；同插入点合并为一次文本替换不改变这一点。本轮不涉及 R-a、R-e、R-f。

### 2. 验收证据

已独立复算：五处替换均唯一命中；父文件、修订文件及候选补丁摘要吻合；AST 收集恰好84个无重名键；原78键状态不变，仅新增6个 PASSED，无删除、missing 或 unexpected。

[试跑原件](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/trials)支持：

| 候选 | 修订版试跑 | 决定性结果 |
|---|---:|---|
| gold | 1，84/84 | 可继续作正对照，无须替代解 |
| noop | 0，74/84 | 恰好10个预期失败键 |
| DEG | 0，82/84 | 两个离群测试积分分别为约0.666667、0.571429 |
| REN | 0，82/84 | 两个 `normed` 键因缺失参数而抛 TypeError |
| D1 | 0，82/84 | 两个 False 键返回密度而非计数 |
| ORD、DEP、C1、DEPFW | 各1，84/84 | ORD误拒解除，已测合理候选通过 |

原版正式账本及日志摘要也核对一致。**上述修订版结果仍只是试跑验收，不是正式评分完成。** 正式材料重建后，还须确认摘要、权限、补丁交付和完整84键执行，至少复跑 gold、noop、DEG、REN、D1、ORD、DEP。

新期望不是抄 gold：独立分箱核算得到，R-c1区间内计数为 `[[1,0],[1,2]]`，ND带权为 `[[1,0],[2,4]]`；R-c3分别为全1矩阵、`[[3,9],[1,3]]`；密度由公开公式推出。R-c2复用公开测试及一维密度语义。

### 3. 告警、需求与泄漏

**应放行 UserWarning，建议直接用 `sup.filter(Warning)`，仅限这两个 `normed` 调用的上下文。**

当前[两处过滤块](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/revision_draft.json:52)会把未指定类别的 `warnings.warn(...)` 变成失败。公开材料没有规定弃用必须选这四类；“允许弃用但拒绝其默认告警类别”是在新增实现约束。公开测试的 warnings-as-error 设置也不能解释这种区别——它同样会拒绝已放行的 DEP、DEPFW。

我用本题原版 `suppress_warnings` 做了**内存最小探针**：四类名单拒绝 UserWarning；`Warning` 放行；两者均不吞 TypeError。FutureWarning消融证明需要过滤告警，**并不证明必须限制为四类**。

其余未发现扩大需求、保 gold 放宽要求或答案泄漏；题面未改，也没有强制 `normed`、`density` 同传时采用 gold 的策略。

### 4. 收口要求

- 两处改为 `sup.filter(Warning)`，同步草案说明、摘要及定点复验。
- 说明中将 R-c3 标为“公开先例推知”；将“挡住所有语义错误”收窄为“挡住所列错误候选”。

**完成小改并复核后可落正式修订单；正式评分完成前不记为探针准入通过。无需新增用户决策，也不必因该问题整题暂挂。**

本轮只读，未修改文件，未新跑容器或正式评分。