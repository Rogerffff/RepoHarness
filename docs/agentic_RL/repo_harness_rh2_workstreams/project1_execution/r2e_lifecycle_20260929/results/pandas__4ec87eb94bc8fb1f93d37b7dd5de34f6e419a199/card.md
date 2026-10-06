# pandas__4ec87eb9 题卡（v1 定稿；独立复核待做）

路径简写：
- `WT/` = `runs/r2e_static_prep_20260924/v3/public/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/worktree/`
- `INV/` = `runs/r2e_lifecycle_20260929/inv/pandas_4ec8/`
- `DC/` = `runs/r2e_lifecycle_20260929/devcheck_rev/unrev/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/`

**题目**：在 pandas 里，对含 `pd.NA` 的 `Float64` / `Float32` 列调用 `GroupBy.quantile` 会报 `TypeError`（base `baa10328`）。gold 在 `quantile` 的 `pre_processor` 里新增一条分支：用 `to_numpy(dtype=float, na_value=np.nan)` 把浮点扩展数组转成 float64，掩码位置置为 NaN。

**材料**：r2e-mr-006/007 补回了 fixture，期望 237 键全为 PASSED，与任务面 v6 相同。新机镜像 `85f550e6…`，配方 `r2e_derive_v1+material_v2+sysconfig_v1`。

## 结论

- **S1（T2b），已实跑确认。**
  - 退化候选 C0：在 gold 同一位置写 `out = vals._data`，把底层数组原样交给内核，不按 mask 置 NaN。
  - C0 正式评分 1.0（237/237），但对常见操作产生的 NA 会算错：

    | 输入 | 正确值（gold） | C0 |
    | --- | --- | --- |
    | `Int64` 转 `Float64` | 2.0 | 1.0 |
    | `reindex` 引入 NA | 2.5 | 0.0 |
    | `Int64` 除法 | 2.0 | 1.0 |

  - 原因：隐藏测试的输入都由列表构造，掩码位置恰好是 NaN。内核只用 mask 计数，排序却用底层数值，所以底层值不是 NaN 时会混进计算。
- **修订 R-c 必做，进训练前完成**。它属于预授权模板，草案见 §4。它不是问题定位和能力比较的前置条件，但建议在探针前做完。
- **dtype 问题（float64 还是 `Float64`）不交用户**，登记为 P3（有公开依据），理由见 §5。
- **disposition**：`needs_repair`，scope `static_review`。前稿是 `needs_review`，当时为 S1 conditional，等 C0 实跑。

## v1 四项用途

| 用途 | 结论 | 还差什么 / 依据 |
| --- | --- | --- |
| 问题定位 | yes | — |
| 能力比较 | conditional | 开发路径、评分、运行条件都已在新机核对。只差一条：R-c 之前，得 1 的补丁要预先登记事后审计（`INV/private_check_A2.py`，或公开命令 `variants_float_masked` 里的 `masked_slot_not_nan`），原始 reward 与语义结果分开记。R-c 验收后这条解除 |
| 训练候选 | no（当前版本） | 有未处理的 S1。R-c 验收并经 Codex 复核后，按新版本重新判定 |
| 留出候选 | no | 当前不满足训练候选的质量条件；修订后也只能作"标明版本的自建题"；有同源关联（X1）；有审查暴露 |

## 1. 关键映射

| 需求 | 公开依据 | 键 / 决定性断言 | 覆盖 | 执行证据 |
| --- | --- | --- | --- | --- |
| 部分 NA 被忽略（题面例子） | 题面 | `NA_float[Float64]`：输入 `[0.2, nan]`，期望 0.2 | 覆盖，但只覆盖底层是 NaN 的情形 | noop 以题面那条报错失败；gold PASSED |
| 列表形式的 q、Float32、全 NA 组得 NaN | 与上一行同一代码路径；内核逻辑；公开测试 | `NA_float[Float32/64]` 的第二个断言；`allNA_column[Float32/64]` | 覆盖 | 同上 |
| **忽略 NA 与底层存储无关** | 题面 "ignoring the pd.NA value"；`FloatingArray` 文档规定 mask 为 True 即缺失（`WT/pandas/core/arrays/floating.py:196-197`） | **无** | **缺失 → S1** | C0 得 1.0；`INV/pcheck_C0.json` 显示算错 |
| 结果 dtype 为 float64 | `Int64` / `boolean` 的公开测试（`WT/pandas/tests/groupby/test_quantile.py:215-236`）；base 上无 NA 的 `Float64` 返回 float64（devcheck 实测） | `dtype=float`，加上 `assert_series_equal` 默认检查 dtype | 覆盖（P3） | gold 在全部变体上都是 float64 |
| 旧行为（object 报错、可空整数、插值等） | 公开测试 | 与公开文件相同的 222 个键 | 覆盖 | noop、gold、C0、C1 全部 PASSED |

**v1 严重度五步**：
1. 核心要求有直接断言：不命中。
2. 断言是否只用题面示例的字面值：测试用 0.2 而不是 2.5，还有 Float32、列表 q、全 NA，不命中。
3. 退化探测：C0 得 1.0，且违反公开要求，**命中，T2b**。
4. 目前没有真实模型候选，无从判断。

## 2. 八方面

| 方面 | 结论 | 未查 / 未知 |
| --- | --- | --- |
| 公开需求 | 已查 | 模型实际收到的题面消息没有捕获。devcheck 的第一条消息是核对指令，不是题面 |
| 材料与初始问题 | 两台机器上，noop 的失败原因都是题面那条报错 | — |
| 测试强度 | 发现 S1 | — |
| 误拒 | C1（替代解）得 1.0；dtype 登记为 P3 | — |
| 回归与 gold | gold 在 8 个变体、公开测试（222 passed）、相关路径上都没有回归；T3 缺口已登记 | — |
| 开发条件 | agent 侧实测通过；numpy 1.20.3；公开测试约 2.4 s | 编译工具没查（本题用不到） |
| 交付边界 | 投影与补丁应用都正常 | 通用控制面没在本题测：候选能改 `pandas._testing`、能在根目录新建 `conftest.py`。属共享审查范围 |
| 题目关系 | X1：pandas `7dd34ea7` 的初始工作树里逐字包含本题 gold 和三个新测试；本题 base 也包含同仓其它题的修复 | 其它题的私有包按规定不读 |

## 3. 问题

| 编号 | 问题 | 严重度 | 去向 |
| --- | --- | --- | --- |
| T2b | 见"结论"一节 | S1，已实跑确认 | R-c |
| P3 | 题面没写结果 dtype | 登记 | 不修订，不交用户 |
| T3 | 以下情形没有断言：浮点扩展数组走 DataFrame 入口；混合列时不应丢掉浮点列；无 NA 时 dtype 保持 float64 的旧行为 | 登记 | 按 v1 §8 抽查；R-c 的第二个例子顺带覆盖"两组、多个有效值" |
| X1 | 见上一节 | 登记 | 训练时控制同源题的采样；按 D3 以仓库为单位划分 |
| P4 | 题面写 "group `1`"，实际标签是 1.0；题面也没提到先出现的 FutureWarning | 登记 | 不需处理 |

## 4. 修订建议 R-c（进训练前必做）

- **公开依据**：
  - 题面写明 "correctly handling and ignoring the pd.NA value"。
  - `FloatingArray` 的文档规定：mask 为 True 即为缺失。
  - `astype("Float64")`、`reindex`、`Int64` 除法都是常用的公开操作，它们都会让掩码位置留下非 NaN 的值（`INV/pcheck_*.json` 已实测）。
- **改动**：只针对这一个窄问题，不新增 dtype 约束，所以新断言用 `check_dtype=False`。
  1. **隐藏测试**：在 `r2e_tests/test_1.py` 做一处文本替换。找到唯一的锚点 `def test_groupby_timedelta_quantile():`（第 290 行），替换为"新测试函数 + 两个空行 + 原锚点"。新函数如下：

     ```python
     def test_groupby_quantile_NA_float_nonnan_storage():
         # GH#42849 的一般情形：是否缺失只看掩码，与掩码位置底层存的数值无关
         # Int64 转 Float64：NA 位置底层是 1.0
         ser = pd.Series(pd.array([1, None, 3], dtype="Int64").astype("Float64"))
         result = ser.groupby([0, 0, 0]).quantile(0.5)
         tm.assert_series_equal(result, pd.Series([2.0], index=[0]), check_dtype=False)

         # reindex 引入的 NA：底层是 0.0；两组，其中一组有两个有效值
         ser = pd.Series([2.5, 3.5, 4.0], dtype="Float64").reindex([0, 1, 2, 3])
         result = ser.groupby(["a", "a", "b", "b"]).quantile(0.5)
         tm.assert_series_equal(
             result, pd.Series([3.0, 4.0], index=["a", "b"]), check_dtype=False
         )
     ```

  2. **期望文件**：整份替换，`added` 里加一个键 `test_groupby_quantile_NA_float_nonnan_storage: PASSED`，合计 238 键。
  3. **镜像**：隐藏测试树的摘要会变，需按修订流程重建派生镜像。
- **验收矩阵**：

  | 候选 | 预期 reward | 预期不符的键 |
  | --- | --- | --- |
  | gold | 1（238/238） | 无 |
  | noop | 0 | 原来的 4 个目标键，加上新键 |
  | C0 | 0 | 只有新键 FAILED（第一段得 1.0，不是 2.0） |
  | C1 | 1 | 无 |

- **另外要核对**：
  - 新键确实执行了：日志里要有它的 PASSED / FAILED 行。
  - 保存新版本和父版本（父版本的期望为 `bdf1ddf5…`、隐藏测试树为 `6a859754…`）、修订理由，以及触发反例 C0（补丁 `cc92ca6f…`）。
  - 交 Codex 复核。
- **修订后仍受保护的公开要求**：部分 NA、列表 q、Float32、全 NA 组，再加上新增的"忽略 NA 与底层存储无关"。

## 5. dtype 要不要交用户：不需要

- **公开依据站在 float64 一边**：
  - 同一方法对 `Int64` / `boolean` 返回 float64，有公开测试。
  - base 上，无 NA 的 `Float64` 本来就返回 float64（devcheck 在 agent 侧实测）。
  - 1.1.0 修复同类整数问题时也用了这个约定（`WT/doc/source/whatsnew/v1.1.0.rst:1135`）。
- **归类**：属于 P3，不构成 T1（测试误拒合理解）。它是输出格式细节，不是任务目标层面的两种读法，所以也不是 P5。
- **另一种做法站不住**：返回 `Float64` 的补丁会连带改变"无 NA 时返回 float64"的既有行为。
- **什么时候重新考虑**：如果探针里出现"其余都对、只有 dtype 是 `Float64`"的真实补丁，把它单列为规格争议样本，原始 reward 保留；必要时再考虑用 R-f 在题面补一句有依据的说明。

## 6. 探针就绪差距

按派发规则我没有读本批 README；下表对照 v1 §2 与环境卡 §2 列出。

| 条件 | 状态 | 谁来补 |
| --- | --- | --- |
| 新机评分：noop 0 / gold 1，正式 profile 与默认预算 | 已满足：新机 L2 各 1 次，旧机各 2 次 | — |
| 公开开发路径：agent 身份、正式启动链、真实 CC + 桩 | 已满足：devcheck 全部命令符合预期 | — |
| 私有 gold 对照 | 已满足：8 个变体全部 OK，公开测试 222 passed | — |
| 测试强度（v1 §4） | **未满足：S1** | Claude 实施 R-c，Codex 复核 |
| R-c 之前就先进探针 | 需要预先登记事后审计 | 协调者 |
| 经 Qwen adapter 的链路、真实模型求解、模型实际收到的完整消息 | 未知（批次级） | A 线 / 协调者 |
| 每题独立复核（v1 §7.3） | 待做 | 新会话的复核者 |

## 7. 唯一优先的下一步

实施 R-c，重建派生镜像，按验收矩阵跑 4 次正式评分，然后交 Codex 复核。

**证据**：
- `INV/`：C0 / C1 的账本与日志、`pcheck_*.json`。
- `runs/r2e_lifecycle_20260929/env_verify/ledger_l2_{noop,gold}.jsonl` 第 8 行。
- `DC/`：devcheck 记录。
- 前稿 `analysis_before_history.md`，旧结论核对 `old_findings_delta.md`。
