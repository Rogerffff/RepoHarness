## 总结

**三题均通过草案复核，可按当前完整草案落正式修订单；尚不等于正式评分验收通过或可以进探针。**

全程只读。已核对公开原文、候选补丁、父版与修订版摘要，并用正式解析器重解析 **32 份试跑记录中的日志段**：均与记录一致，无缺键、额外键或期望映射变化；未重跑容器。

## 1. `numpy__18b7cd9d`：通过

1. **模板与依据成立。** 两处分别属于 R-c 的非示例实例、公开行为回归保护。
   - 非 `None` 比较：[题面第 7、18 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9/user_prompt.txt:7)明确泛指非 `poly1d` 对象。
   - 不同对象按系数相等：[公开回归测试第 18–21、74–79 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9/worktree/numpy/lib/tests/test_regression.py:18)确实依赖这项行为，不是从 gold 倒推要求。
2. **试跑支持验收预期。** gold、A 为 1；noop、D、N、I 为 0。N、I 在原版为 1，修订后分别因非 `None` 比较、按值相等断言失败；其余 10 键不变。[试跑原件](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9/trials)
3. **未扩大需求或泄漏答案。** 断言比较表达式的行为，不强迫内部返回 `NotImplemented`；A 返回 `False` 也通过。新增期望来自公开语义，不是抄 gold 输出。未因此证明所有 list／ndarray 比较情形均已覆盖。
4. **结论：通过，可落正式修订单。** 通过范围包含两处修改；不能删掉第二处后仍声称已消除 I 的已知漏判。

## 2. `numpy__5e8301c2`：通过，正对照使用 C-A

1. **R-c 用法正确。** 交换操作数、双操作数单例求和维分别针对两个窄问题。[题面第 7 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb/user_prompt.txt:7)泛指 singleton dimensions，没有排除求和维；[公开测试第 578、586、692 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb/worktree/numpy/core/tests/test_einsum.py:578)确实以非优化路径作数值参照。也符合 v1 §10 对本题的既定处理。
2. **C-A 的独立核实依据充分，限本次范围。** [补丁第 13–18、26–29 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_actor_20260925/grader_cands/numpy_5e83_CA_gold_plus_blas_guard.patch:13)支持双向广播、保留不兼容尺寸拒绝，并将需要广播的收缩交给 `c_einsum`。补丁摘要与历史正式评分账本一致，历史日志摘要也吻合。当前试跑 C-A、UP 为 1；noop、C-C、原 gold 为 0；C-C、gold 从原版的 1 变为 0。[试跑原件](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb/trials)
3. **没有为保 gold 放宽要求。** 新期望可独立推导：内积为 `5×(1+2+3)=30`，矩阵结果为行和乘广播行；小整数浮点值可精确表示。未绑定 BLAS/helper，实现不同的 UP 也通过。15 个失败键重复执行同一新增块，**不代表新增了 15 种 dtype 覆盖**。
4. **结论：通过，可落正式修订单。** 正式材料须登记 C-A 为替代正对照并保留 gold=0；不能只豁免 gold 失败而省略替代正对照验收。多操作数与路径规划不在本次通过范围内。

## 3. `numpy__a5ea773e`：通过

1. **两处 R-c 均有公开依据。** [题面第 7、21 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/numpy__a5ea773e66110cf335c9ed37e8ccdc14f8e56764/user_prompt.txt:7)要求全 1 重复因子下修改结果不影响输入；[docstring 第 796–807、813–814 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/numpy__a5ea773e66110cf335c9ed37e8ccdc14f8e56764/worktree/numpy/lib/shape_base.py:796)明确支持 array-like `reps` 和前补轴升维。因此元组输入与 `(1,5)` 形状要求均成立。
2. **试跑支持验收预期。** gold、A 为 1；noop、D、B、RC2、C、RC3 为 0。四个触发候选均从原版的 1 变为 0：B／RC2 被变异隔离检查拒绝，C／RC3 被形状检查拒绝；其余 31 键不变。[试跑原件](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/numpy__a5ea773e66110cf335c9ed37e8ccdc14f8e56764/trials)
3. **未扩大需求或拟合 gold。** 检查实际修改后的输入和值的形状，不要求特定复制实现或对象身份；无条件复制的 A 也通过。题面未改，无新增答案泄漏。
4. **结论：通过，可落正式修订单。** 两处应一起保留；删去形状断言会重新放行 C／RC3。

## 正式落地仍需完成

三题均须在**正式修订单、材料摘要及派生镜像落实后**，通过正式评分重跑上述正负对照，确认候选交付、测试完整性及严格键集匹配。试跑工具明确省略了这些完整性检查，不能代替该步骤。无需新增用户决定。