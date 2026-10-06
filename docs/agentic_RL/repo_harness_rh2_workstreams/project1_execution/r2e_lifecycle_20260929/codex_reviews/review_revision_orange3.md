## 结论

- **`9b5494e2`：需小改。** A 的方向正确，建议采用 B′；但 G1 不能按现有理由降为 S2，正式落地还存在配方摘要阻塞。
- **`22e98f8f`：R-f 草案通过。** 可编制正式修订单；新公开读者验收完成前不启用，训练／探针资格仍待补齐证据。

本次全程只读：重算草案摘要、核对 20 份试跑及历史评分原件，做了内存探针；未修改文件、未运行容器或正式评分。

## 一、`orange3__9b5494e2`

### 1. 模板与公开依据

**A 符合 R-b／R-e，没有放宽 L1 核心要求。**

- [题面第 20 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040/user_prompt.txt:20)要求选择支持指定 penalty 的 solver，不是把 L1 换成 L2。实际拟合后检查 `penalty` 能保留这项要求。
- 默认 L2／lbfgs 来自[公开构造函数第 37–40 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040/worktree/Orange/classification/logistic_regression.py:37)。去掉 `"auto"`、私有钩子和“必须 liblinear”合理；将无效的 `None` 拟合要求换成 `'none'` 也有对应版本 API 依据。[scikit-learn 0.22 文档](https://scikit-learn.org/0.22/modules/generated/sklearn.linear_model.LogisticRegression.html)
- 正例为真实 L1 拟合，反例 W1、V7 分别检查“偷换 penalty”和“无条件更换默认 solver”，不是仅检查“不报错”。

**B′ 符合 R-c，建议保留。** 默认 `repr` 的精确要求确实在[本题公开测试第 57–60 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040/worktree/Orange/tests/test_util.py:57)，无需借后续题快照证明。P1 属已评分的公开行为回归，应处理。

v1 没有“一键只能承载一种要求”的规定；两个窄问题已分别列依据，B′ 可接受。失败定位较 B 粗，但日志行号能区分，可加断言说明；**不必仅为拆键采用 B**。

### 2. 验收证据

核对结果与草案一致：

| 方案 | 试跑支持的结论 |
|---|---|
| A | gold＝1、noop＝0；V1/V3/V4/V5＝1；W1/V7＝0 |
| A＋B′ | gold＝1、noop＝0；P1＝0、V4＝1 |
| A＋B | gold＝1、noop＝0；P1＝0；14 键无缺失或多余 |

A／B′ 的 13 键及 expected 不变；没有删测试后遗留 `unexpected`。新断言来自公开要求、默认值和公开测试，**不是照抄 gold 输出**。但“13/13”是状态匹配，包含两个预期 FAILED，不能写成全部测试通过。

**最终合并版本仍须正式评分**；B′ 的四次试跑不能替代全部修订验收矩阵。

### 3. 两项必须修正

**① G1 应按 S1 处理，不能以“题外改动”豁免。**

[草案第 190–193 行](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040/revision_plan.md:190)的分级理由不成立：公开默认是 `multi_class="auto"`；对应版本文档明确，默认 lbfgs 在多分类时采用 multinomial，G1 改成 OvR 是改变常用默认训练行为，不是罕见输入差异。[版本文档](https://scikit-learn.org/0.22/modules/generated/sklearn.linear_model.LogisticRegression.html)

G1 的[历史正式评分](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_actor_20260925/grader/ledger_or_G1.jsonl:1)确为 1，本轮 A 试跑仍为 1，命中 §4 第 4 步。补一个独立列明依据的 R-c：例如比较默认多分类模型与显式 multinomial 的行为／系数；先验证该关系在 base、gold 成立，**不要抄 gold 数值作期望**。

**② B′ 也不能免除配方摘要更新。**

即使不加 `sysconfig`，隐藏测试修订仍会加入 `material_v2`。[构建逻辑](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/scripts/build_r2e_derived.py:502)会改变组合摘要，而[批准集合](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/envpack/environment_overlay.py:55)只有旧摘要。

我用现有函数内存复算：

- 原配方 `512277…`：通过。
- A `b3f672…`、A＋B′ `51e410…`：均返回 `env_recipe_not_approved:r2e-mr-020`。

因此“保留修订号即可保持绑定可用”不成立。须为**最终材料组合**完成内容绑定与复验，不能绕过摘要检查。

### 4. 裁定

**需小改，当前不能作为完整修订包通过。** 收口条件：

- 采用 A＋B′，补 G1 的窄回归断言；
- 修正配方身份与绑定安排；
- 最终版本正式评分：gold、四个合理替代解为 1；noop、W1、V7、P1、G1 为 0。

未见 A／B′ 扩大需求、泄漏答案或为保 gold 放宽要求；当前缺陷是漏掉已知回归及落地身份不配套。

## 二、`orange3__22e98f8f`

### 1. 模板与公开依据

**符合 R-f。** 三处替换分别是删答案实现、改正 base 症状，以及配合新示例调整期望的呈现方式；期望数值未变，没有新增要求。

已核实：

- 导入路径及函数契约见[公开源码第 150–158 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b4237/worktree/Orange/widgets/data/owcreateclass.py:150)。
- 新 Actual Behavior 逐字对应[已有 agent 身份运行输出第 3 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_actor_20260925/devcheck/orange3__22e98f8f4cccc25f0d0217f9f4251b6/orig/captures/mcve_repo_function.out:3)。
- 三处替换各命中一次，前后摘要与草案一致；gold 的八行新增实现已全部移除，没有写入隐藏新增输入或求解算法。

### 2. 验收与“不附 R-c”

评分材料确实不变；历史三组正式对照均为 noop＝0、gold＝1，原日志摘要一致。**不必仅因 R-f 重跑这些评分**，但历史结果不替代本批新环境验收。

“**尚无已有评分证据证明的 S1，因此目前不附 R-c**”成立；“已经完成无 S1 判定”不成立，因为 §4 第 3 步尚缺正式评分。已有测试包含重复元素等非示例输入，不是只检查题面原例。

### 3. 退化候选与剩余事项

`mapping=np.arange(len(a))` 是有效的错误候选：[公开测试第 83–85 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b4237/worktree/Orange/widgets/data/tests/test_owcreateclass.py:83)要求 `[42,42] → [0,0]`，它却返回 `[0,1]`。内存执行目标断言也确认它在第 85 行失败；这不是正式评分证据。

**建议落地前先正式评分这一候选**：评分材料未变，可以直接在父版完成。它是训练资格的必做证据，**不是新增的 R-f 文本审批前提**；有效得 0 后无需为它补 R-c。

### 4. 裁定

**R-f 草案通过，无须修改正文。** 保留新公开读者验收、版本／pins、实际题面消息核对；读者须同时推出“按首次出现排序”和正确映射规则。完成退化评分及本批环境条件前，用途保持 `conditional`，不能写成已可训练。