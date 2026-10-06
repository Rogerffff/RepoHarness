# NumPy d805e9b6：本轮窄修订与验收安排

2026-10-03。工作包 `r2e_numpy`，仅负责 `numpy__d805e9b66228e68a0eb14d901cd350159c49af18`。发布前父版两行正式评分和草案三行私有试跑已通过非作者核查；078／079发布后，新镜像、正式十行和实际公开CC交付也已通过最终独立核查，见 `reviews/cpu_acceptance_review.md`。统一探针请求见 `probe_request.json`，实际状态见 `result_manifest.json`。不再向cpu-a发新作业，不修改公共生产代码、库存、pins 和历史证据。下列轻量检查仍只代表先前静态范围；发布前与新版CPU原件分别保留在两份索引，不改写历史或预期。

## 依据与材料身份

按当前工作包与 `category2_repair_20260929/r2e/r2e_inventory.md` §7 接续。旧 `r2e_lifecycle_20260929/results/<本题>/probe_card.md` 的 `probe_ready` 仅代表它列明的旧验收范围；本轮需要处理工作包新增的三项余项，不能沿用旧标签放行。

已核父 pins v12 → 修订单 v11；本题仍只有 `r2e-mr-056`。父测试 `test_1.py` 的摘要为 `14d78a1c74be07bf5e62a81c5383b3d408dbf597f6a54d3bfe48ac5e6d9516c7`，来源原文摘要为 `72f865c42fba15679442951d772b9213dc4fc5d4ad16170f486ed6aac7e8deb1`；229 个 expected 键逐键不变。完整核对在 `static_checks.json`。这是本轮读到的版本快照，后续由维护者确认正式冻结版本。

CPU父基线已确认：`cat2-cpu-r2e064065-swe5-20261003-v1`（manifest SHA `282021962a92b510f077385660ac56acedcd7fac1d97e63db3baa98e4dcc057f`）改用material_v13／pins_v14；本题056条目及public、grading、environment、validation四行均与原快照相同，完整expected文本和229键相同。cpu-b重新核794文件及48／216可信读回通过。本题新测试和题面不在该release中；它只作为已登记父版与私有草案试跑的基线。详细绑定在 `result_manifest.json` 的 `current_cpu_preparation.frozen_release`。

公开依据来自 `runs/r2e_static_prep_20260924/v3/public/<本题>/worktree/`：

- `numpy/core/arrayprint.py:62–67` 说明 threshold 与 edgeitems；`:252–257` 在元素数大于阈值时摘要；`:208–213` 和一维格式化分支按首尾数量取值。
- `doc/source/user/quickstart.rst:262–267` 明确可用 `set_printoptions` 强制全量显示。
- 题面一般的一维摘要要求与原示例保持；不扩展为二维修复、性能达标或新内部接口。

## 三项修改

1. **提高阈值后仍须摘要。** 在原 `TestMaskedArray.test_str_repr` 的打印选项 `try/finally` 中追加 `n=3000, threshold=2000`。期望首尾各三项，中间为省略号：`[0 -- -- ..., 2997 2998 2999]`。已有三处断言保留。新构造的 hybrid 候选在未超过阈值时不截取，超过时固定截到 1500，在此处静默丢值。父056正式评分已核实其误放，新草案私有试跑在新增判据失败；登记后新版正式得0，失败位置499已独立核实。
2. **核实大 edgeitems 并修正正对照。** 旧 K-A5b 在默认阈值下裁为 1002 项；`edgeitems=501` 恰好等于每侧 501 项，使 NumPy 不再插省略号，中间 1998 项丢失。新增 `n=3000, threshold=1000, edgeitems=501` 的 token 断言，保留 501 个首项、501 个尾项及中间省略号，允许正常折行。不修改全局打印阈值，也不按实现中的私有常量评分。新 K-A5c 在原一维修法上同时保留超过 threshold 和 `2*edgeitems` 的截取长度；避免调用 `numpy.ma.core` 内被同名函数覆盖的 `max`。父056正式评分、完整草案私有试跑及登记后新版正式评分均通过229键，新版K-A5c=1、K-A5b=0已独立核实。不能声明在所有配置下完整正确；二维原行为未修，性能仍未验。
3. **R-f 改正描述和 Actual。** `public/` 只改描述、补一句有公开文档依据的打印选项说明、替换错误 Actual；原示例、Expected 示例、hints 和 base 不变。Actual 来自旧 v8 agent 开发验证的 `orig/captures/repro_issue_repr.out`，不是手算输出。隐藏输入 `n=3000`、阈值 2000、edgeitems 501 和私有 helper 均未写入题面。新公开读者只接触 `public/` 与公开初态源码。

## 轻量检查

`prepare_materials.py` 只写本独占目录，可从仓库根执行。它重放原 `r2e-mr-056` 加本轮增量，核前后摘要、Python 3.7 AST、229 个测试键及函数范围；在仓库外临时目录检查九份补丁能应用。没有导入或执行本题 NumPy，没有运行测试，没有生成评分。

新公开读者与非作者修订核查均完成，未发现本轮准备的静态阻断，报告分别在 `reviews/public_read.md` 与 `reviews/static_revision_review.md`。公开读者从干净上下文仅看公开材料；私有核查确认新测试摘要 `09d0aa6d…`、229 键与旧断言保留、两类新反例的源码推导及合并发布方式。它们不替代真实容器结果与后续运行证据复核。

`private/test_1.py` 是完整新测试草案；`private/trial_delta.json` 只供**确认含 r2e-mr-056 的父镜像**使用。不能不核材料版本就交给会从多个镜像里挑第一个的旧 `trial_grade.py`。`revision_draft.json` 也不是可直接加载的正式修订单。

## 最小正式验收矩阵

完整补丁路径、摘要和新版实际运行结果在 `acceptance_matrix.json`。下表原计划的十项预期均已由正式driver核实；完整229键、真实失败位置、应用与清理在 `cpu_acceptance_v1.json`。外层作者投影检查错误及离线重核分列；最终非作者独立重核通过，同意关闭检查错误并接续探针，原外层rc1保留。

| 候选 | 新版预期 | 最先应触发的判据／用途 |
| --- | ---: | --- |
| K-A5c | 1 | 新主正对照；所有 229 键应符合 expected |
| K-A5b | 0 | 新 edgeitems 断言；旧版正式得 1 的记录保留 |
| hybrid | 0 | 新 n=3000／threshold=2000 摘要断言 |
| gold | 0 | 原 threshold=2000／n=2000 全量显示断言 |
| noop | 0 | 原题面示例 repr |
| K-DE、K-DC | 各 0 | 原 n=500 token 断言 |
| K-DF、DG-e | 各 0 | 原 n=100000 摘要断言 |
| DG-g | 0 | 原 n=500 不应摘要 |

另外在含 `r2e-mr-056` 的父版上跑 hybrid（预期 1）和 K-A5c（预期 1）；旧 K-A5b 等八行父版正式证据按版本复用，不机械重跑。若父镜像无法可靠恢复，则记录身份缺口，不能把新机的近似镜像当旧版。

每行需确认非空补丁由 agent 正确应用、投影符合预期、229 键严格相等、完整日志含评分段且实际执行到决定性断言。失败补丁应用、infra_failure 或未执行断言都不算负例验收。`private/check_printing.py` 可以独立检查五个行为，特别核新增两个场景；它只在本题 Python 3.7、`/testbed/numpy` 容器中运行，输出与 raw reward 分列，不替代正式评分。

## 已执行的CPU流程与GPU接续

1. 按全机共用名额运行；固定镜像 ID、材料、配方和公共入口版本。原镜像 `c596cd48…` 是旧 v8 验收身份，不能冒称已存在于新机。
2. 先在父镜像做新增候选和私有行为检查，明确 hybrid 的误放与 K-A5b 的 edgeitems 缺陷；修正实际暴露的问题后再发布，不追着分数放宽判据。
3. 由维护者发布合并的新修订单、pins 和派生镜像，再走现有 `replay_grade run` 加冻结 image overlays 的正式入口验上述矩阵。作者执行证据后交非作者核查失败位置与正对照边界。
4. 新宿主核 agent 解释器、包导入及关键身份；复用未受影响的旧公开开发命令，不重跑无关性能或整个仓库。捕获实际 solver 题面，确认 R-f 文本及中性开发提示真正交付，私有材料不可进入上下文。 旧 `r2e_devcheck.py` 默认使用通用 `ns.prompt`，不能仅核材料文件。本轮改用现有 `r2e_probe_e2e.py --no-grade`，由正式任务面提供 `spec.prompt`，核真实网关首请求与保存题面一致；经CC的Bash读公开bundle提示，并核它进入后续请求。保留env、import_version、公开问题复现和六项相关公开测试，另用原入口生成的R2E预检；正常静止、FrozenPatch和清理一并核。空候选不重复评分，noop由正式十行覆盖。独立的GPU开发说明见 `public/solver_environment_brief.md`，已通过仅公开静态核查；它的GPU实际交付留给统一执行回执，不冒称CPU已经送入该独立说明。
5. CPU 正式验收和必要独立核查通过后，提交统一探针线程。引用其统一模型配置，不在本包另设预算；本题 gold 预期 0，健全性检查必须用已验的新正对照。结果回传后仍由本题主分析和继续修复。

## 具体共享入口事项

正式 ingest 已支持 `hidden_test_text_replace` 与 `statement_text_replace`，**无需新增生产能力或先重构平台**。但 parser 拒绝同一题同一 target 两条修订；`r2e-mr-056` 必须在新版本里由合并条目替换，不能直接追加。`publication_handoff.json` 已给出从原始来源重放的完整 edits，正式编号留给维护者分配。

新测试必须发布到新的版本化 `s2_r2e/revisions/` 路径，保留旧全文；本独占目录不满足正式 `revised_file` 路径约束。旧 `formalize_revisions.py` 固定历史 results 目录，且会拒绝本题同目标冲突，不能直接调用；这只是本包的发布接入事项，不阻塞其他题。

保留的用途限制：自建修订题须按材料版本报告；gold 的旧／新评分不回写。同仓答案暴露 X1 与留出方向、共享测试控制面 E3、二维与性能边界沿用旧卡，探针不能自动赋予训练资格。E3 通用保护延后不妨碍本轮准备，但实际候选若触碰共享测试控制，原分与行为审计分列。
