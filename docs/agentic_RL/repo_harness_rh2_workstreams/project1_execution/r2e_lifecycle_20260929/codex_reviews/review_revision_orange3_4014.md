## orange3_4014：需小改，仅修订说明

**测试草案本身通过复核；更正下述依据转述后，可落正式修订单。新版正式评分尚未完成，不能据此解除 `on_hold`。**

### 1. 模板与公开依据

**R-c 用对，修改范围足够窄。** 只补“重复切点不能导致整个非恒定变量退化为单一区间”的检查；前两段原样保留，27 个测试键及期望映射不变。我在内存中重建修订文件，所得摘要与草案记录一致。没有涉及 R-a／R-b／R-e／R-f。

公开依据的行号准确：

- [题面第 26–27 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/orange3__4014f2483e3bab0621c9ae0f994947c008183253/user_prompt.txt:26)：要求切点唯一、区间有效。
- [docstring 第 125–132 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/orange3__4014f2483e3bab0621c9ae0f994947c008183253/worktree/Orange/preprocess/discretize.py:125)：规定近似等频及 `n` 的含义。
- [公开旧测试第 38–44 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/orange3__4014f2483e3bab0621c9ae0f994947c008183253/worktree/Orange/tests/test_discretize.py:38)：四个分开的值、`n=4` 时分别成区间。

**这些材料结合公开源码，支持本组输入的两侧分离断言；题面“唯一”一句本身不足以推出它。**

**必须小改的文字：**[修订说明第 51–52 行](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/orange3__4014f2483e3bab0621c9ae0f994947c008183253/revision_plan.md:51)误述了旧公开读者结论。[原文第 18、31 行](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/orange3__4014f2483e3bab0621c9ae0f994947c008183253/public_read.md:18)说的是“点数和取值没有约定”“允许区间数少于 n”，并非“要求去重”“只有文档允许时才能减少”。应改为：**旧公开读者支持保留正常行为、接受多种修复方式；新顺序断言由上述公开材料联合推出。** 此项不需改测试或重跑试跑。

### 2. 验收证据

逐份核对了 [8 份修订版试跑日志](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/orange3__4014f2483e3bab0621c9ae0f994947c008183253/trials)：均解析出完整 27 键，无 missing／unexpected，补丁应用成功。

| 对照 | 修订版试跑 | 判断 |
|---|---:|---|
| gold、C1、pyx_build | 1，27/27 | 正对照及不同修复位置均通过 |
| noop、pyx_only | 0，26/27 | 第 55 行，原缺陷仍在 |
| DG | 0，26/27 | 仅新断言第 80 行失败 |
| C4 | 0，26/27 | 第 64 行，原有保护保留 |
| C3 | 1，27/27 | 既有 S2 缺口未修复 |

DG 原版正式评分确为 1；补丁及日志摘要与账本相符。因此，**本次误判在试跑层面已纠正**。正对照使用 gold，不需要替代解豁免；新断言只比较区间顺序，没有抄写 gold 的点数、切点或区间编号。

仍须在正式修订材料及派生镜像上验收上述正负对照，核对测试树摘要、正式权限和候选身份，并沿用记录明确的 1200 s 控制面时限。

### 3. 是否过严、保 gold 或泄漏

- **`n=6` 合理。** 公开源码此时走相邻值中点分支。复算确认，`n=4` 时 gold 的区间编号为 `[0,1,1,2,2,2]`，并不保证右端点与整个簇分离。选择 `n=6` 是隔离有依据的去重问题，不是撤销要求来保 gold。
- **初稿确实太松。** 不断减小 `n` 的写法降到 3 后也得到 `[0,1,1,2,2,2]`：通过三个代表值的旧断言，却违反现稿第 81 行。此结论是源码核对和纯 Python 复算，不是 Orange 实跑。
- **未绑定 gold 实现层。** Python 层、公共构造函数层及重编 `.pyx` 路线均有通过证据；未规定簇内如何划分。
- 未改题面、未把隐藏输入或答案写入公开包，也未放宽原断言。**C3 可继续按 v1 §11 登记为 S2**，但不能写成已解决；循环分支非退化等未覆盖范围也须保留。

### 4. 最终处置

**需小改：纠正修订说明第 51–52 行的证据转述；测试草案无需调整。** 更正后可落正式修订单，正式评分通过后再重判准入。无需新增用户决策。

本次只读核对材料、日志和摘要，并运行纯 Python 算术核对；未修改任何文件，未启动容器。