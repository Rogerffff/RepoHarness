# R2E 材料语义独立复核

2026-09-24，Codex 子审 / Falsifier。范围：`r2e_env_repair_20260924/decisions.md`、13 份 `material_revisions/`，并回查可信 raw 行、评分源码、既有脚本和原始日志。这里只新增审查文件；没有运行容器、连接远端、修改生产/摄入面/原证据。

**结论：根因调查有实质成果，可以作为用户决策依据；不能把“来源失败状态能稳定复现”概括成“相关环境与评分支撑缺口已经修好”。** T0-1、2、3、4 的主要事实与推荐成立；T0-5、6、7 需要把“本轮先不实施”与“接受现状进入后续使用”分开。orange3 T0-7 有一项影响推荐理由的证据过度归纳；scrapy T0-5 的 noop 失败位置写错，但不推翻搬迁缺陷结论。

## 1. 核验方法与范围

- [audit_materials.py](audit_materials.py) 从可信 `s2_r2e/raw/r2e_gym_subset_48_e8b9fcbc.jsonl` 取对应 13 行，以当前纯解析函数重新读取 R-f 的 26 份 noop/gold 日志；日志 SHA 全部与原账本一致。逐题输入行号、摘要、状态、差异及 fixture 诊断行在 [audit_results.json](audit_results.json)。这是离线重算，不是新运行。
- 13 题的来源 `new_commit_res_stdout` 全部能解析成各自 expected；这确认二者一致，**不能单独证明生成谱系或期望合理**。
- pandas 七题非 PASSED 键独立重计为 `17+1+13+2+4+9+12=58` 个 ERROR；各题 gold 日志 `fixture ... not found` 诊断行数分别与之相等。
- 直接读了 datalad 六份 dry-run 输出与执行脚本、scrapy over-fix 补丁和真实评分日志、pandas fixture_check 脚本与结果、orange3 版本及失败日志。没有把包摘要当新实测。
- `source_excerpts/` 是六道重点题的可信 raw 多行展开，便于逐行定位；来源行与哈希见 JSON。它们含 validation_only 材料，不应发给 solver。

重算命令（仓库根）：

```bash
python -B docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_review_20260924/materials_agent/audit_materials.py
```

适用维度：A（失败归因）、B（训练信号/选择偏置）、C（未决处置）、D/H（原件与修订唯一来源）、E（实验实际覆盖）、F（资格与本轮边界）、G（真实评分与沙盒实验区分）、I/K（分期及最小修改）、M/N（原因可观察性及历史依赖）均适用。J 只检查文字与行为是否一致；L 在本子审仅限既有资源证据，不重复主审/账本审的容量复核。没有新状态机、并发实现或恢复实现，相关运行时子维度不适用。

## 2. T0 事实与推荐矩阵

| T0 | 事实复核 | 对原推荐的判断 | 仍需证据 / 用户决定 |
| --- | --- | --- | --- |
| 1 coveragepy `016af5f6` | **成立**。raw 第 1 行期望含单个 FAILED；保存的来源 stdout 报子进程缺 mock；真实镜像 noop/gold 该键 PASSED，gold 仅此键不符。 | **接受 A**。优先版本化摄入修订一个 expected 值，复用既有 pins；无需为一题增加运行时覆盖机制。卸 mock 模拟历史坏环境没有益处。 | A 仍是待批提案；新版本需 fresh noop/gold，确认目标键仍区分且该回归检查能正常执行。13 次观测的每一份未由本子审重计，26 日志核验中的本题两份与材料一致。 |
| 2 datalad `58ba5165` | **成立**。raw 第 23 行 `test_1` 导入旧公开 `test_docs`；`test_2` 与上游新文件逐字节相同；原 gold 3/4。root dry-run 的 B1、A 都 gold 4/4，noop 2/4。 | **接受 B1，决定前 held_material**。一行相对导入比新增支撑材料契约小。dry-run 不能代替正式 grader 复验，提案已明确这一点。 | 新隐藏树/pins/镜像的真实 noop/gold 各两次。公开题面已包含其中一个 bracket 示例，不能把全部测试文本称为只能猜中的秘密；材料缺支撑文件的结论仍成立。 |
| 3 pillow `2b061b68` | **成立**。raw 第 11 行题面希望 JPEG 白名单打开 PNG 成功；隐藏目标要求拒绝。另两 FAILED 在进入 save/show 调用前由 `pytest.warns(None)` 引发。 | **接受 C**，题面修订留统一题意筛查。它是已发现矛盾，不是“尚未做题意筛查”本身阻塞。 | 若保留题目，版本化公开题面并重新核对实际 prompt；不自动把所有 pytest 伪影期望改 PASSED。 |
| 4 scrapy `9a15fcf8` | **成立且有真实反例**。gold+bytes 解码补丁只改业务源码；7/7 PASSED，原 expected 中两 FAILED 导致 reward 0。 | **接受本轮 D**。后续若保留，B 的局部材料修订即可，不需要立即引入通用 ignored_keys。 | 用户决定隔离/修订/接受风险。隔离少一题且减少早期 Python3 兼容问题的覆盖；不应把这种题全按“正常负样本”消费。 |
| 5 scrapy `cfed9b66` | **主要成立，原因表需更正**。缺 `test.egg` 与类自引用错位可核；但 instances 键 noop 先死在 `load_object(M2).rindex`，gold 才走到 M1 类身份错位。 | **A 仅可解释为本轮不改原件、等待决定**。这些是实际评分支撑缺陷；保持 FAILED 能复现来源，不代表中间件目标已被有效检查。若要作为后续真实训练题使用，更倾向 B 后再验，或 D 暂缓。 | “仅改 load_object 即满分”目前是有源码支持的推断，没有真实候选评分；不要写成已验证。无需为本轮调查结论新开重型实验。 |
| 6 pandas ×7 | **fixture 不可达事实成立**。58 ERROR 全在 setup，原位公开测试同名项可运行；`4ec87eb9` 两项 base 中没有，原位实验并未验证这两项。 | **不接受以 gold=1/来源可比性直接推荐六题长期 A**。A 可作为本轮原件保持；既然当前目标包括环境/评分支撑修复，建议 B 先作一题代表变体，再决定是否对七题批量修订。`4ec` 优先级更高合理。 | 用户在“保留来源对照”与“修订后供后续使用”之间定用途。私有 fixture 必须按各题实际 conftest 依赖补齐；重算参数化键集，做真实 noop/gold，不仅把 ERROR 文本改 PASSED。 |
| 7 orange3 `9b5494e2` | **部分成立**。4 FAILED 事实、版本事实成立；`test_coefficients` 的 str.decode 依赖故障直接可见；两个 scorer 根因仍未单独验证。 | **A 只可作为暂不改原件的阶段处置**；“所有正确候选恒 FAILED、假阴性低”的理由证据不足。若后续使用该题，应先做 B 的窄诊断/配方验证，或显式接受残余风险。 | 保留 inferred 标签；不要预承诺换 SciPy 四键都会 PASSED。先确认具体兼容组合及逐键行为，再版本化环境/expected。 |

13 份材料的逐题覆盖：coveragepy×1、datalad×1、pillow×1、scrapy×2、orange3×1、pandas×7 均已读。pandas 逐题数值为 `19c5eea5 17/155`、`294cbc8d 1/21`、`32dd55cb 13/92`、`4ec87eb9 2/226`、`7dd34ea7 4/34`、`87787609 9/34`、`f656217a 12/323`，与独立解析一致。

## 3. 需要更正的材料事实

### M1 / P2：orange3 从 solver 固定推导“正确候选的四键恒失败”不成立

- **当前行为**：[orange3 提案](../../r2e_env_repair_20260924/material_revisions/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040.md) 第 22 行把四键描述为所有通过目标测试的候选恒 FAILED，以此在第 34 行推荐 A；[decisions.md](../../r2e_env_repair_20260924/decisions.md) 第 32 行和该题 [screening_record.json](../../r2e_env_repair_20260924/tasks/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040/screening_record.json) 的 issues/处置理由沿用这一结论。
- **违反的证据边界**：noop/gold 两种候选的稳定失败不证明所有正确候选的状态不变；源码事实和未经实验的依赖同源推断不能合并成已证根因。
- **证据**：可信 raw 第 33 行展开的 [隐藏 test_auto_solver](source_excerpts/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040/test_1.py.txt) 第 135–153 行只构造 estimator 并检查 `.solver/.penalty`，没有拟合或固定 `max_iter`；[新源码](source_excerpts/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040/Orange__classification__logistic_regression.py.new.txt) 第 37–56 行表明 `max_iter`、预处理等并非上述断言的内容。
- **原始日志**：`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-gold-o_f0536903.eval.log:156` 明确是 `result.status != 0` 才执行 `.decode`；第 168–195 行的两个 scorer 已正常计算出 scores，只在特征名断言失败。材料第 11 行自身也承认这两项同源尚未验证。选择 lbfgs 不蕴含必然未收敛，更不蕴含特征排序不变。
- **影响**：用户可能基于“只损失 P2P、不会误伤正确修复”的错误确定性接受 A。实际可确认的是这两种候选存在四个共同 FAILED；候选行为、优化条件或依赖改变后如何判分仍未知。4/13=31% 是期望键比例，不能当作损失了 31% 奖励权重（二值奖励没有这种线性含义）。
- **分期 / 可达性**：P2 决策材料现在更正；来源失败已由真实 RH2 入口观测（production_observed），但另一个合法候选翻键尚未实测，不作为生产代码阻塞或新的当前 P0/P1。
- **最小复核**：运行本目录 `audit_materials.py`，再对照以上目标测试体和原日志条件分支，无需再租机。
- **验收条件**：去掉“所有正确候选恒 FAILED”的全称断言；分列直接证实的依赖异常与两个 scorer 的待验证根因；A 改成显式的阶段处置/残余风险选择，或在新环境变体后更新结论。

### M2 / P2：scrapy `cfed9b66` 把 noop 与 gold 的失败位置写成了同一原因

- **当前行为 / 位置**：[scrapy 提案](../../r2e_env_repair_20260924/material_revisions/scrapy__cfed9b6659c90e0799361911b1d72ed127edf471.md) 第 11–19 行的“gold/noop 原因”列把 instances 键归成两者都因 M1 类身份错位，继而称三键恒失败、不误伤。
- **应保持的不变量**：FAILED 是状态，不能替代异常位置与实际执行分支；同状态可能屏蔽了修复前后的不同缺陷。
- **证据**：noop 日志 `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-s_6f09d8ff.eval.log:124-150` 在 `load_object(M2)` 对类调用 `.rindex` 时就终止；gold 日志 `…all-gold-s_915fb3c8.eval.log:99-126` 已穿过构造，才在 `isinstance(..., M1)` 失败。可信隐藏源码 [test_2.py](source_excerpts/scrapy__cfed9b6659c90e0799361911b1d72ed127edf471/test_2.py.txt):95-105 与日志吻合。
- **影响**：这个共同 FAILED 不能检查中间件实例修复；因旧逻辑报错和因测试搬迁报错在当前奖励中都匹配。它支持“评分支撑缺陷尚存”，而不是证明该键天然无用。
- **分期 / 可达性**：P2 材料表更正，production_observed；不要求当前修改公共评分机制。是否修材料仍在 T0-5 内决定。
- **最小复核 / 验收**：读两份上述日志即可；原因表分别写 noop 与 gold，保留部分解满分的“推断、未实跑”标签。B 若实施，验收应含修复后新增 instances 键的真实 noop→gold 变化，而不只是 gold 全绿。

## 4. 基础环境、材料与训练信号的分界

1. R2E 精确映射含 FAILED/ERROR 合法，**不意味着这些状态都可以视为无环境缺口**。`scoring.py:463-475` 按逐键相等判分；重复 ERROR 的原因可以是来源测试搬迁缺 fixture，也可以是实际题目行为。前者需要保留为环境/评分支撑缺口，即使改法要通过材料修订 T0。
2. pandas 的公开原位开发测试可运行，说明公开包和 fixtures 并非完全缺失；失效的是私有测试的装配。该类缺口应归“评分支撑修复待决定”，可保留来源规则复现通过这一事实。不能根据归因已知、gold=1 把它消除；同时不必把整个包判成不可解、禁止继续调查。
3. `r2e_grading_scripts.py:11-16,22-23,79-84` 证明根目录 conftest 会随候选留下、隐藏目录则重建。因此 pandas 翻键存在静态可达路径；这不是本轮新发现的完整防作弊要求。当前保存的 `fixture_check/inner.sh:14` 是 root 下跑公开 base 文件，并没有 gold+根 conftest 的 RH2 评分对照。**不能把“会翻键”的分析再升级成“已实测正确解 reward 0”**。
4. `4ec87eb9` 的 [隐藏测试](source_excerpts/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/test_1.py.txt):251-277 正常体涉及浮点部分缺失值和扩展整型；第 280–287 行是仍正常运行的全 NA 例。原位诊断 `runs/r2e_env_repair_20260924/p3/fixture_check/pandas__4ec87eb9…/result.txt:5-6` 明确两目标在 base 不存在。更强的“部分解可满分”仍应作为题意/覆盖假设留后续验证，本轮不将未做的反例当代码阻塞。
5. pandas 七题选 A 会系统性削弱这些具体回归路径的行为检查；若恢复 fixture 的正确开发提交改变键集，精确匹配又可能给负信号。T0-6 已写出这一风险，但没有发生频率的实测依据，“概率低”应标为判断。orange3 同理，保留 FAILED 的兼容性收益与可靠训练信号的代价必须并列。无需新建评分通用平台来表达这个选择。
6. 公共复现：本子审回读的 pandas `4ec` 与 orange3 `9b` 脚本、原始输出支持相应题面错误确在 base 出现；pillow `2b` 的反证支持题面与目标不一致。其余 45 题未由本子审全量核，故不独立背书“46/48”总数，更不将其等同 46 道完整有效训练题。

## 5. T0 分类与停止条件

- **confirmed T0**：T0-1…7 都涉及材料、奖励参考或样本使用取舍，用户决定合理；工程实现载体不应额外拆成新的许可闸门。
- **experiment-required**：T0-7“单一依赖调整能修四键”；T0-6 具体 conftest 修订后的参数化键集与 noop/gold 行为。实验发生在用户选择修订路线后即可，本轮可先完成材料事实更正。
- **deferred T0**：题面统一修订策略、T0-5/6 的训练准入取舍可留其对应阶段，但必须标明未决定，不能用当前 environment_qualified 自动推出准入。
- 未发现需要新增通用 ignored_keys、平台或状态机的 missing T0；未把任何已明确递延的题意/反作弊/正式 actor 检查升级成当前生产代码阻塞。

**停止条件已满足**：完成 13 份材料对原件与关键日志的聚焦核验；交主审合并资格声明问题和以上两条材料更正。当前无需再跑全池、制作“证明一切正确解”的昂贵反例或继续占用远端。下一步由用户在既有 T0 决策中选择具体材料修订及用途，随后只复验受影响版本。
