**结论：D1 的 S1 成立；暂挂正确。四个选项基本完整，但 B 的实施范围被低估、C 与“回写历史”的关系需澄清；dtype 按 f5eb 的既有口径应按 P5 处理。**

本次只读核对了源码、账本和行为记录，并做了内存解析探针；未修改文件、未重跑容器。`055` 的原验收仍有效，但不能解除新发现的 D1。

## 1. 四个选项是否公允

| 选项 | 复核意见 |
|---|---|
| **A 维持现状** | 合理的暂缓选项，但“零成本”应改为“无修订实施成本”，后续审计仍有成本。不能默认取得能力比较资格。 |
| **B 链式追加** | 可作为长期方案，但不只是改唯一性检查和文本重放；还有构建、归档和消费端的单修订假设。 |
| **C 合并取代** | 可以违反“新版本必须包含全部旧条目”，**而不违反“历史 evidence 不回写”**。两条规则不能混为一谈。 |
| **D 守卫文件** | 当前解析规则下技术上成立，但除了误拒风险，还存在**守卫未执行却无法由评分映射发现**的风险。 |

**B 漏列了三个具体改点：**

- `revised_file` 必须按版本或修订号另存；覆盖 `055` 所指文件会破坏旧版摘要校验。
- 构建端现在按 `target` 写文件，后条会覆盖前条；manifest 又按整行排序，不保证修订顺序。因此只修改摄入器仍会构建失败。可选择逐环存储，或核验完整链后生成“原始→最终”的单次构建替换。[构建代码](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/scripts/build_r2e_derived.py:269)
- 若开放的是**所有目标**的链式修订，消费端目前还要求最终期望／题面摘要等于**每一条**修订的 `sha256_after`，也要调整；可以先只支持本题需要的隐藏测试文本链。[消费检查](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/envpack/ingest_r2e_subset.py:836)

**B／C 都要发布新材料、新 pins、新摄入提交记录及对应代码锚点，重建受影响镜像、重新验收。**旧修订单、被引用文件、pins、摄入产物、日志和审查原件均保留；旧证据不改分、不改版本归属。C 只在新版本中明确取代 `055`，不是抹掉它。现有安装脚本强制追加、编号连续且禁止覆盖文件，C 也不能直接沿用原安装流程；“不改代码”最多指“不改摄入逻辑”。[安装流程](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/r2e_lifecycle_20260929/install_round.py:74)

所以没有必须新增的第五大类，但应补列 **B 的窄实现**与 **C 的不可变历史＋新版有效快照**。仅救一道题，C 未必比 B 不合理。

## 2. D 是否属于 v1 §5 模板内

**可以归入 R-c，但“模板内”不等于“实现已通过验收”。**它补的是有公开依据的插值断言，没有修改 parser 或精确映射判分规则；不能仅因采用 `skip` 就自动判为模板外。[R-c 边界](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md:120)

我用现有解析函数做内存探针，确认：

- 全部断言成功后 `SKIPPED`：不新增键；
- 断言失败：产生 unexpected 键，判 0；
- skip 原因含 `PASSED`：会产生空键，误拒；
- **未收集守卫、提前 skip、正常执行后 skip：可以得到完全相同的评分映射。**

最后一点是原报告的重要遗漏：材料树摘要证明文件存在，不证明断言执行。D 至少要核验正式完整日志中的执行证据，登记漏执行风险与 parser 版本依赖；当前不宜作为默认写法。[解析器](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/envpack/r2e_parsers.py:90)

## 3. dtype：按 P5 处理，不直接判 T1

**我不支持 review §5 给出的 P3／P5 分界。**

- f5eb 同样有公开测试锁定的**既有输出**——每文件七键；并非“两种都是新行为”。所以“其中一边是旧行为”不足以区分两题。
- dtype 是可观察的接口行为，不只是显示格式；“不是核心数值目标”不能排除 P5。
- pandas 保持普通 `float64` 的依据更直接，足以成为**推荐选择**；但可空类型政策、相邻聚合行为和公开读者的判断提供了反向依据。尚不足以把另一读法直接排除为不合理。[公开读者的双向依据](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/public_read.md:36)

因此，**按此前 f5eb 的尺度，本题也应按 P5 暂挂，推荐保持 `float64`，但不把推荐当已定规格。**这不等于已证实 T1，也不能等真实模型首次命中后就自动用 R-f 选择读法。[此前裁定](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/codex_reviews/review_revision_coveragepy_f5eb.md)

## 4. 当前处置是否成立

**成立，并应明确为：**

- `needs_repair`／`on_hold`；问题定位 yes，当前不进正式能力比较、训练或留出候选。
- D1 审计可以预登记，但本次只读复核**没有实际登记**。各用例独立捕获异常，给出 PASS／FAIL／UNKNOWN；原始 reward 保留，语义结果另列。
- 数值正确、仅返回可空浮点的样本列为规格争议，不混入 D1 错值。
- 审计不能替代修订验收，也不能豁免未决 P5。修好 D1 后仍须处理 dtype 读法。

另有直接依据：本批准入规则已要求“没有未处理的 S1”，所以不能借一般的带审计比较先例直接标成 `probe_ready`。[本批准入规则](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md:17)