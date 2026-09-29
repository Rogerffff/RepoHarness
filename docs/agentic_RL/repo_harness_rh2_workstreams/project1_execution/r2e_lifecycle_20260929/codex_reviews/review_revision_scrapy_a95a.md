## 结论：需小改

**R2 属于现行预授权 R-a，不需要新增授权。阻塞点另在 R1：草案排除了一个已有证据的同接口漏判。**

### 1. 模板与公开依据

- **R1 的新增断言属于 R-c**：位置绑定、关键字绑定的带返回值生成器应判为 True，有[题面第 8、32 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/scrapy__a95a338eeada7275a5289cf036136610ebaf07eb/user_prompt.txt:8)及 [docstring 第 218–219 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/scrapy__a95a338eeada7275a5289cf036136610ebaf07eb/worktree/scrapy/utils/misc.py:218)支持。
- **R2 可归 R-a 的测试支撑恢复与期望纠正**。“R-a 只准删测试、删键”不符合[现行 §5 第 124 行](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md:124)：原文明确允许凭独立语义或环境证据改期望状态。这里断言不变、过滤器按测试恢复、五键不变，不改通用评分规则；不属于 R-d。
- 公开依据核实成立：[news.rst:1919–1921](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/scrapy__a95a338eeada7275a5289cf036136610ebaf07eb/worktree/docs/news.rst:1919)支持正常警告；`IndentationError` 回退警告依据是[公开测试:251–256](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/scrapy__a95a338eeada7275a5289cf036136610ebaf07eb/worktree/tests/test_utils_misc/test_return_with_argument_inside_generator.py:251)，不能单凭新闻条目推出。
- 因此 **§8 无需启动**。其中 B 比保留死键、重复断言或全池改 runner 更直接；A/E 挡不住 C2 的判断正确。

### 2. 验收证据

逐份核对原始日志、输入及摘要，草案报告的 **8 次试跑结果准确**：

| 候选 | 试跑结果 | 决定性失败 |
|---|---:|---|
| gold ×2、C1 | 1 | 五键全过 |
| noop ×2 | 0 | `test_partial:272`，原始 TypeError |
| D | 0 | `test_partial:278` |
| C2 | 0 | 两个恢复键，`:87`、`:264` |
| C3 | 0 | True 断言 `:79`、partial 断言 `:278` |

均无 missing／unexpected；草案与试跑输入一致，父／子测试树摘要复算一致。**D/C2/C3 的已登记误判确已纠正。**

新期望不是照抄 gold：R1 来自公开契约；R2 恢复的公开测试在 **base 的解题环境**已经通过，修订试跑中 noop 的两个恢复键也通过。

但这尚非完整验收：正式材料、镜像重建、摘要检查和正式权限下的评分仍待完成。

### 3. 阻塞项：不能直接排除绑定方法实例

[revision_plan.md:45](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/scrapy__a95a338eeada7275a5289cf036136610ebaf07eb/revision_plan.md:45)把 partial 包装绑定方法列为“没有要求，增加断言属于扩大需求”。这个判断依据不足：

- 已有 [Python 3.9.21 诊断 F](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_lifecycle_20260929/devcheck_rev/unrev/scrapy__a95a338eeada7275a5289cf036136610ebaf07eb/private_control.json:30)明确显示：方法含 `yield` 和 `return 1`，gold 对 `partial(Holder().meth_ret, 1)` 却返回 False；当前草案仍让 gold 得 1。
- 这是**同一目标接口、同一 partial 判定要求**，不是新增 `warn_on_…` 接口能力。题面的一般表述没有排除绑定方法；“示例没写”“Python inspect 如此”“gold 会失败”均不足以排除它。
- 按 v1 §4 第 4 步，应处理这个已知漏判，不能以保留 gold 为正对照来缩小需求。

当前 R1/R2 修改本身没有泄漏答案或放宽断言。UserWarning 类别限制、既有 mock／文案约束仍应保留登记。

### 4. 最小修订与收口条件

1. 在 R1 中补 **partial 包装带返回值绑定方法应为 True** 的窄断言，并更正上述范围说明。
2. 将 **C1 作为替代正对照**核实：它先展开 partial 再识别生成器，源码及本机内存函数级核对支持此路径；仍须在目标镜像的新草案上验收。
3. 新版要求 **C1=1；noop、D、C2、C3=0；原 gold 因该已知遗漏为0并留档**，再完成正式材料与正式评分。

补齐后可复核收口；若对该实例的范围仍有分歧，按既有规则暂挂本题，**不必重开 R2 授权讨论**。

全程未修改文件，未重跑容器。