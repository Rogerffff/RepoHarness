## 结论：需小改

**现有两处 R-c 断言可以保留；主要问题是把非默认 `threshold` 一概归为 T3，依据不足。** 本轮只读，未修改文件、未运行容器。

### 1. 模板与公开依据

两处均符合 R-c 的窄修改边界，未涉及 R-a／R-b／R-e／R-f。我在内存中应用草案，确认仅增加这两处断言，结果摘要为 `ea62cd09…`；测试键及 expected 均仍为 **229 键，逐键不变**。

- **n=100000 摘要：依据成立。** [题面第 5、8、20 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/user_prompt.txt:5)描述一般的大一维数组行为；`arrayprint.py` 第 62–67、252–257 行规定阈值及首尾显示规则；`ma/core.py:3828` 确认 repr 的 data 使用 `str(self)`。
- **n=500 全量显示：严格读法成立，不构成 P5。** [公开文档](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/worktree/numpy/core/arrayprint.py:62)规定默认阈值为 1000，源码以 `size > threshold` 才摘要。私有优化常数 `_print_width=100` 不能推翻这项公开行为。DG-g 证明断言具有区分力，**不是严格读法的规格依据**。

两个期望分别来自公开摘要规则、输入元素及掩码位置，不是照抄 gold 输出。

### 2. 验收证据

重新逐键核对了 12 份试跑记录。修订版结果如下，均无 missing／extra：

| 候选 | 修订版试跑 | 失败位置：目前仍为推定 |
|---|---:|---|
| gold、K-A5b | 各 229/229，等价于 1 | — |
| noop | 228/229，等价于 0 | 原示例，458 |
| K-DE、K-DC | 各 228/229，等价于 0 | token 比较，477–478 |
| K-DF、DG-e | 各 228/229，等价于 0 | 468 |
| DG-g | 228/229，等价于 0 | 476 |

K-DE／K-DC／K-DF 的原版正式评分确为 1，补丁摘要、应用身份、目标测试执行及键集均能对应；现有试跑支持这三项误判已被纠正。

**K-A5b 作为现草案的补充正对照，核实充分。** 补丁仅将错误调用模块内 `max` 改成条件表达式；默认配置下，n=500 不裁剪，n=100000 保留 1002 个元素后由 NumPy 摘要。原版正式评分、私有行为对照和修订版试跑一致。K-A5 的崩溃确属候选错误，不是误拒；K-A5b 也不应称为独立求解。见[补丁](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/cands/numpy_d805_KA5b.patch:13)。

**尚不能写成正式验收完成：** 新材料摘要、正式权限与交付路径，以及完整日志中的失败断言，仍须正式评分确认。DG-g 已成为已知相关错误候选，应纳入正式矩阵，不再选做。

### 3. 需求边界与剩余问题

两处新增断言本身没有扩大需求、放宽要求或泄漏答案。但以下排除理由不能接受：

> 自定义 threshold 没在题面提及、gold 也通不过，所以补测会扩大题意。

这出现在 [revision_plan.md 第 30、79、229 行](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/revision_plan.md:30)。**公开 Quickstart 第 262–267 行明确介绍通过 `set_printoptions` 强制全量显示**，不能仅凭“非默认”认定为罕见路径。[原文](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/worktree/doc/source/user/quickstart.rst:262)

具体反例：`threshold=2000`，`a=np.ma.arange(2000)`，掩掉 `a[1:50]`。按源码及本轮内存中的宽度逻辑核算，**gold 只留下 1500 个元素，再全量打印这 1500 个，静默丢掉 500 个**；K-A5b 不裁剪。这里是静态证据，不冒充容器实跑。它属于已知 gold 对有文档常用行为的不完整修复，应按 [v1 §4 第 4 步](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md:97)处理，不能靠限定 gold 的覆盖范围豁免。

其他登记：

- **P4 足够，不阻塞本轮 R-c。** base 实际输出已有证据；Expected 可消解错误 Actual。保留 P4 相关失败单列，后续 R-f 优先处理。
- **二维窄轴可以继续登记不修**，标题明确限定一维。
- 非默认阈值缺口的边界还应更正为 **`threshold ≥1500`**，不只是 `>1500`。

### 4. 需要的小改及通过条件

1. 保留现两处断言；补一处上述“提高阈值后全量显示”的窄 R-c，按输入构造 token 期望，并用 `finally` 恢复打印选项。
2. 用 K-A5b 验证新场景；若通过，按已授权 D4 将其作为主正对照，**记录 gold 在新版应为 0**，不为保 gold 放宽断言。
3. 更新草案、用途记录和验收矩阵；补试跑后复核，再落正式材料并完成正式评分。

**在此之前维持 `needs_repair`，不宣布 `probe_ready`。无需新增用户决策；若替代正对照不能通过，再暂挂。**