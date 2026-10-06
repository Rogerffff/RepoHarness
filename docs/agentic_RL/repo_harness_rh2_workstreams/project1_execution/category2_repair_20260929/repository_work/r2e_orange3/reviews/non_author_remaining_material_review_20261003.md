# Orange3 三题剩余新材料非作者静态窄核

日期：2026-10-03。审查者：Codex，非材料作者；已读私有测试、修订与部分候选，不是 fresh 盲审。本轮仅核 4014f248、50f6a758、9b5494e2 的 preparation、revision_draft、完整测试文件和 acceptance_plan，按需定点读公开源码／题面及旧有效材料。不接触另行安排的 50f6 新上下文公开读者，不向其发送私有信息，未审 22e98。

**结论：未发现必须先改的具体误拒、漏判、fixture／调用或矩阵错误。材料可进入既有授权的维护者接续与 CPU 验收；三题新矩阵和 9b54 新概率关系均未运行。本报告不等于正式材料已激活、CPU 通过、actor 交付完成或探针／训练准入。**

## 4014：保留 057 后补小量级分箱

- 公开题面 `runs/r2e_static_prep_20260924/v3/public/orange3__4014f2483e3bab0621c9ae0f994947c008183253/user_prompt.txt` 要求近邻值生成有效、唯一切点；公开 `worktree/Orange/preprocess/discretize.py:125` 定义 EqualFreq 为近似等频分箱，`worktree/Orange/tests/test_discretize.py:30` 对 arange(100)、n=4 明确验 24.5／49.5／74.5。新增断言仅缩放这组互异等频输入，验可观察分箱，不规定切点去重位置或抄 gold 常量。
- 新 `tasks/4014f248/files/r2e_tests/test_1.py:68`–`:81` 完整保留 057 的混合近邻／远隔值保护；`:86`–`:90` 新增 arange(100)×1e-12、n=4，对 transform 结果验四组各 25 行。新旧标准量级输入均非边界歧义，也无重复值；返回一个区间不是允许的等频解。
- 本轮读取公开 `_discretize.pyx:12`–`:59` 与 digitize／transform 调用，静态计算正常切点位于第 24／25、49／50、74／75 项之间；`C3_round_dedupe.patch` 的 round(p,10) 将前两切点舍为 0、第三舍为 1e-10，100 个输入均处于同一区间，因此新增断言可拒绝这条具体错修。这是数学／源码推导，没有运行 Cython、Orange 或作者的数学转写。
- 独立从 v11 的 `r2e-mr-057` 应用唯一 edit，核得有效父 SHA `477e4252d38c780cab7edbc5e0ddfe40d236a9b06fecde9de5123692fb57ad6c`；父 target 方法 AST 是新方法的完整前缀。原两个近邻分支及 057 非退化保护均保留。目标外全文件 AST 不变，expected 27 键原字节不变。
- 八方计划覆盖 noop、gold、C1、DG、C3、C4、pyx_build、pyx_only，observed_score 全为空。合理去重在不同位置应允许；pyx_build／pyx_only 的分数仍取决于真实构建／导出／新 grader 加载。最终入口 actor 重编和冻结产物的待验要求没有被旧原型或 AST 替代。
- 接续限制准确：当前同题同目标已有057，不能直接追加第二条；新草案提供来源→合并最终文件的 edit，由唯一维护者确定合并取代或已授权接续并冻结新版本，不回写057或绕过重复目标约束。

## 50f6：格式放宽，但未用定义与匹配定义都要处理

- 本轮读私有修订及公开源码，身份已经不是 fresh 读者；另一个公开阅读角色保持独立。新 `files/problem_statement.txt` 明确要求 foo／bar 未使用警告，并解释公开旧 `test_parse_var_defs_no_rename` 最后未用变量不警告断言的冲突；没有让 actor 修改公开测试。
- 公开 owcolor `_parse_var_defs:661`–`:722` 遍历 categorical／numeric 两段，为存在变量建新描述，更新两个 model 后 `commit.now()`；未用变量现由 `continue` 静默忽略。原行为 capture 显示 warns=[]、crits=[]，失败发生在测试 assert 警告存在，支持将 TypeError 描述改成缺警告。只读该指定原件，不重做历史环境等效审计。
- 新 `tasks/50f6a758/files/r2e_tests/test_1.py:797`–`:838` 保留空定义不警告；shown_text 收集本次所有 warning，允许位置／keyword text、多条警告，不要求标点或顺序。每轮 reset_mock 防止旧名单警告补足当前结果；一／二个未用定义仍逐个点名，长名单允许缩略且不钉省略阈值／计数措辞。
- 混合场景经真实 widget `send_signal` 加载 iris，再解析匹配 class 变量 iris→species、未匹配 categorical foo／numeric bar。要求两段未用名都出现在本次警告，并从真实 Outputs.data 核 class_var.name 已改 species，拒绝警告后提前返回的路线。既有 setUp、decorator、匹配定义和 palette 写法均与公开测试／源码相容；未把模型／commit 替身当成完整 Qt 行为证据。
- 八方计划中 gold／K1 为合理格式正对照，noop／K2／K3／K4／Cdeg／K5 检无警告、有数据／混合抑制、漏 numeric、提前返回、不点名。目标外全文件 AST 不变，48 键 expected 原字节不变。原逐字名单格式被有意放宽，而有效的空输入与识别未用变量语义保留，未发现具体合理格式被误拒。
- 三项 statement edit 与原公开 problem_statement 唯一替换一致、前后 SHA 匹配；公开新正文仍待 fresh 阅读与实际 actor 交付。本轮没有接触其派发结果，也未自行给该角色结论。

## 9b54：保留 A＋B′，新关系必须真实拟合

- 公开题面要求 penalty=l1 自动选择可用 solver；公开 `Orange/classification/logistic_regression.py:36` 保留默认 lbfgs、multi_class=auto，公开 `Orange/tests/test_util.py:57`–`:60` 明确要求默认 repr 连调两次仍为无参数形式。
- 新 `tasks/9b5494e2/files/r2e_tests/test_1.py:135`–`:162` 的旧 A＋B′ 方法主体已与 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040/trials/inputs/test_1_revised_A2.py` 定点对比，为 AST 完整前缀。两类／三类 L1 真实拟合、penalty 保留、liblinear／saga 接受、L2 默认 lbfgs／l2、重复 repr、none 可拟合均保留。测试没有要求 auto 字面量、某个私有 helper 或必须在构造时选择 solver，V1／V3／V4／V5 所代表的不同修法静态相容。
- `:167`–`:173` 通过两个真实 `LogisticRegressionLearner(...)(self.iris)` 拟合，再用公开 Model.Probs 比较默认模型与显式 multinomial 的预测概率；不是 AST 的 multi_class 检查、不是参数布局检查、不是替身，也不抄 gold 数值。G1 patch 只将默认改 OvR、保留显式 multinomial 参数，因此这组比较针对其实际模型变化；**是否在固定版本上按当前容差拒绝 G1，仍需真实 CPU 结果**。
- 关系采用 rtol=1e-5／atol=1e-7。本轮未拟合、未调用 sklearn，也没有网络获取其文档；公开 constructor 的配置及材料引用的固定版本语义支持此设计，不能由此证容差或结果已验证。acceptance_plan 已要求先在 base／gold 确认关系，再做十方矩阵，这个顺序必须保留。
- 13 键 expected 与来源有效020版本逐字节相等，两个 scorer 仍为 FAILED，不能写成全测试通过；目标外全文件 AST 不变。十方 observed_score 全为空，正对照 gold／V1／V3／V4／V5、反例 noop／W1／V7／P1／G1 的角色与当前断言无明显静态矛盾。
- 保留 `r2e-mr-020`、SciPy1.5.4／+env_v2 和最终组合摘要登记要求。新增 material 步骤后的配方摘要不是旧批准摘要，维护者须核最终内容并定向运行、登记；不能仅凭后缀或存在020跳过批准内容绑定。

## 本轮实际检查、材料身份与停止条件

只执行标准库文本／JSON／SHA256／AST 检查。未执行项目／测试／候选函数／作者探针，未导入 Orange、NumPy、Qt、sklearn，未安装、联网、SSH、容器或 GPU；没有改生产、题主材料、期望或注册表。

三题均独立核得来源 hash、唯一 text edit、完整最终文件、Python3.7语法、目标外 AST 相等、expected 原字节与键数一致、计划 fixed_material 和全部 patch SHA 匹配、26 个 observed_score 全为空。057 与020的指针及必要接续边界分别核对；这些不是运行通过数。

实际 SHA256（均为完整文件字节，表中省略 sha256: 前缀）：

| 题目 | revision_draft.json | 完整 test_1.py | acceptance_plan.json |
| --- | --- | --- | --- |
| 4014f248 | `013bbc8b55c11595e47f3d2c5de387c3d936be16b77608615e6fe8c9b9bb89c0` | `ea9b779f3d1f34b31cec43a3b4fd57bf79d8bd19a25c7c4b4153d22659d72b47` | `d557cab89cd612dac79ab9f0415e6b8a47dad44115ff891ec7d910a655539561` |
| 50f6a758 | `8812bbcbca7b35873d7f375063706ef3b7f815f75f8125c74d3b4bb1053986c3` | `126f09f984b468b637d0d22524c89857a4950178cb8574935262aeb61df43cd9` | `a32b8100a008e403fd9c8cb7517fd0a41f58e9b4486e27bbd5ebfe98f6aaf38e` |
| 9b5494e2 | `13e4b46d4ea26885ea9bee70ab5cc64325880540decbf9500a77603568e950fa` | `b2bd45b7c11b63c19fa147e0fcc485aa5b80b540a460f36163a4d7331f6f87df` | `0fe8260168f220462e494bece67b953c6fc2f877560ea4698cbb815ecfc13d84` |

旧 A＋B′ 输入文件 SHA256：`be3b9ff02bf8b2f28371176844d6ff9cce940c1a9e1148406bf80cd7e46c19f4`。50f6 新题面 SHA256：`8d7ddab841c89504b41268db2e13aed59a67ac13aaa791f8c32c70a1a3a321ef`。

停止条件：三个指定材料问题已有静态答案，未发现需要先改草案的具体问题；继续由维护者完成4014接续／新版本冻结、50f6独立公开阅读与实际交付、9b54组合环境登记／base-gold概率关系，再按已备矩阵收取真实证据。遇到具体失败再定位，不增加候选凑数或扩大题意。唯一新增文件为本报告。
