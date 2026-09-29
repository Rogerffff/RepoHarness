## 结论：通过，可落正式修订单

第 2 版断言无需修改；**通过的是修订草案，不是正式评分验收或探针准入**。全程只读，未修改文件、未新跑容器。

### 1. 模板与公开依据

**R-c 用对了**：两段断言都针对同一个窄问题——“忽略缺失值不能依赖掩码位底层恰好为 NaN”。不涉及删键、放宽旧断言、mock 替换或题面改写。

原文与行号核对成立：

- [题面第 22 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/user_prompt.txt:22)明确要求忽略 `pd.NA`；[FloatingArray 文档第 194–197 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/worktree/pandas/core/arrays/floating.py:194)明确规定 mask 为 True 即缺失。
- Int64 构造时在掩码位填 1：[integer.py 第 226–228 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/worktree/pandas/core/arrays/integer.py:226)；转浮点扩展类型时保留数据与掩码：[masked.py 第 312–320 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/worktree/pandas/core/arrays/masked.py:312)。
- `reindex` 对应的填充路径使用 `_internal_fill_value`：[masked.py 第 382–398 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/worktree/pandas/core/arrays/masked.py:382)；FloatingArray 将其定义为 0.0：上述 `floating.py` 第 242–243 行。

**期望不是抄 gold**：先按公开要求排除缺失，再按默认线性插值计算中位数，分别得到 `(1+3)/2=2`、`(2.5+3.5)/2=3`、单值 `4`。依据是 [GroupBy.quantile 第 2399–2419 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/worktree/pandas/core/groupby/groupby.py:2399)及 [NumPy 1.20 percentile 文档](https://numpy.org/doc/1.20/reference/generated/numpy.percentile.html)。

### 2. 验收证据

核对原始 JSON 后，修订版试跑结果为：

| 对照 | 观测结果 | 按期望映射对应判分 |
|---|---|---|
| [gold](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/trials/rev_gold.json) | 237 passed | 1 |
| [noop](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/trials/rev_noop.json) | 233 passed，原四个目标键失败 | 0 |
| [C0](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/trials/rev_C0.json) | 235 passed，仅两个 `NA_float[Float32/Float64]` 断言失败 | 0 |
| [C1](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/trials/rev_C1.json) | 237 passed | 1 |

四次均解析到全部 237 键，missing/extra 为空；两个既有 skip 未变。

- **C0 确为退化候选**：它绕过缺失值转换，将 `_data` 直接交给按数值排序的内核；[私有行为对照](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_lifecycle_20260929/inv/pandas_4ec8/pcheck_C0.json)实证其违反“忽略 NA”，不是仅凭补丁形状判错。原材料[正式评分为 1](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_lifecycle_20260929/inv/pandas_4ec8/ledger_C0.jsonl:1)，本次误放已在试跑中纠正。
- **C1 是合理替代解**：统一按掩码转换，并保留整数 `inference`；源码与行为对照一致。本题 gold 已通过，无须启用替代正对照例外。
- 两次单段诊断均能独立挡住 C0。但主试跑日志截断，**不能声称已直接看到第 272 行失败**；目前是源码推导、旧版通过、新版失败及行为对照共同支持。

### 3. 范围、dtype 与失败定位

没有扩大需求、为保 gold 放宽要求或新增答案泄漏。断言检查数值结果，**不要求内部必须存 1.0/0.0，也不绑定 gold 的实现方式**。

随参数取 dtype 合理：三个 NumPy 参数键在 noop 下仍通过，且新增覆盖 Float32；固定 Float64 会让这三个原有回归键也因目标错误失败。`check_dtype=False` 仅用于新增数值断言，原有 dtype 检查保留。

我在内存中应用草案并重算：目标文件摘要为 `719e63ae…`；期望映射仍为 237 键，内容及序列化字节均未变。006/007 不动，无同目标冲突。并入旧键使定位变粗，但二值评分不受影响；通过完整 traceback 区分断言即可接受。

### 4. 落地后的必要确认

按[落地计划](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/revision_plan.md:193)，更新正式材料及摘要、重建镜像，再正式跑 gold/noop/C0/C1，确认 **1/0/0/1、237 键严格相等，以及 C0 的完整失败位置和数值**。此前不能核销正式验收；既有 T3、dtype、跨题关联事项继续登记。

一处**非阻塞文案勘误**：[方案第 199 行](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/revision_plan.md:199)“两种结构对任何候选的得分相同”过强，应改成“当前四个对照得分相同”；第 2 版额外覆盖 Float32，不能宣称普遍等价。