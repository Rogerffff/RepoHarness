## 结论

**两题均通过草案复核，可落正式修订单；尚不等于正式评分验收或探针准入。**

已只读核对公开原文、草案差异、父子摘要和候选补丁，并用正式解析器复算 **26 份存档试跑日志**，结果一致。未修改文件，未新跑容器。

## datalad `19f5b450`

1. **R-c 使用正确，三个实例均有公开依据。**

   - `exit 5 → 5`：题面要求转发底层命令退出码，3 只是示例；不限定 `--explicit`。[题面 L22](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb/user_prompt.txt:22)、[CLI 设计 L65–71](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb/worktree/docs/source/design/cli.rst:65)。
   - 输入缺失 `→1`：输入准备失败，不执行底层命令，属于 incomplete results。[CLI 设计 L61–63](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb/worktree/docs/source/design/cli.rst:61)、[run.py L105–109](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb/worktree/datalad/core/local/run.py:105)。
   - ignore `→0`：帮助文字明确规定失败不导致非零退出码。[common_args.py L95–101](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb/worktree/datalad/cli/common_args.py:95)。

   准确分类是：第一项为核心要求的非示例实例，后两项为同一失败处理链必须保留的公开行为；不能统称为“所有失败都转发底层退出码”。

2. **试跑满足语义验收，正式验收待补。** gold、K1 均为 **22/22**；noop、K2、K3、H、K4 均为 0。K2 被 ignore 键拒绝，K3 被缺输入键拒绝，H 被两个新键拒绝；原 19 键不变，仅新增三个 PASSED 键，无缺键或 unexpected。[试跑原件](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb/trials/)。期望来自上述公开语义，不是照抄 gold。

3. **去掉新增路径的 stderr 约束合适。** `expect_stderr=True` 实际是不检查 stderr，而非要求非空。[公开 helper L86–90](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb/worktree/datalad/cli/tests/test_main.py:86)。这避免把原有争议扩到新路径；gold 在更严的 v0 也通过，并非为保 gold 放宽。题面未改，无新增泄漏或矛盾。**K4 仍应称“stderr 规格争议候选”，不能因其仍为 0 就认定它已被证明是错误解。**

4. **通过，可落正式修订单。** 无材料层阻塞项；原 stderr 争议继续单列。

## pandas `32dd55cb`

1. **R-b 与两项 R-c 均合规。**

   - 两条报错文字对应同一种行为：Period 均值必须抛 `TypeError`，不是把相反任务目标用“或”合并。旧文字有 [DataFrame 公开测试 L896–900](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0/worktree/pandas/tests/frame/test_analytics.py:896) 支持；另一条有 [PeriodArray 源码 L1639–1645](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0/worktree/pandas/core/arrays/datetimelike.py:1639)及公开 `test_period_mean` L38–60 支持。datetime/timedelta 均值断言保留。
   - sum 属题面“reduction operations (e.g., mean)”的非示例实例；公开开发日志也确认 base 抛同一 ValueError。[题面 L7](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0/user_prompt.txt:7)。
   - 缺失值均值有默认 `skipna=True` 文档和 Int64 公开归约测试支持，**虽未在 §11 单列，仍在 §5 R-c 授权范围内**。[generic.py L10420–10421](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0/worktree/pandas/core/generic.py:10420)、[test_integer.py L236–245](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0/worktree/pandas/tests/extension/test_integer.py:236)。

2. **验收与候选重建证据充分，限试跑层。** gold、C1 均 **92/92**；noop、C3、C3g、C4 均为 0，无缺键或多余键。C1 误拒得到纠正，C3g 原先满分的漏判被纠正。C3 是 C1 加 mean 条件；C3g 对所有 EA 仅分派 mean；C4 仅扩展 `IntegerArray.sum` 参数——均忠实于历史描述。

   **仅凭“只放宽 T2 时 C3、C4 得 1”不足以证明两条各自必要；已存档的逐项移除对照补足了证明：**

   | 从完整草案移除 | 重新得 1 的错误候选 |
   |---|---|
   | sum 断言 | C3、C3g |
   | 缺失值均值断言 | C4 |

   因此，对当前草案及已知反例，两条都不能直接删掉。[对照试跑原件](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0/trials/)。均值 2、和 4 可由公开语义直接计算；C4 的 4/3 是源码推导，截断日志未直接保留该实际值。

3. **未扩大需求，也不是保 gold。** gold 修订前后都通过；sum 不锁 dtype。`mr-016` 恢复私有 fixture，`mr-017` 将相应 13 个 ERROR 期望改为 PASSED；本次只改 `test_1.py`，92 键映射不变，**不冲突、不需要合并旧条目**。[既有修订](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/private/pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0/revisions.json:3)。题面与 gold 未改，无新增泄漏。

4. **通过，可落正式修订单。** R-b、sum、缺失值均值应一起落。

## 正式使用前的剩余事项

固定正式材料摘要、pins 与派生镜像后，补正式评分：

- **datalad**：noop、gold、K1–K4、H。
- **pandas**：noop、gold、C1、C3、C3g、C4。

试跑未验证正式控制面保护和摘要检查。datalad 的 `chown -R` 超时应单列为 `infra_failure`，不能充当候选得 0，也不能据此否定本题材料。当前证据足以结束本轮草案复核，无需继续扩大补测。