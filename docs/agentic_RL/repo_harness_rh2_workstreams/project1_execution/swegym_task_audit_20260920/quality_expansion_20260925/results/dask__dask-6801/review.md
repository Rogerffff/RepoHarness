# dask__dask-6801 cross-review

最终裁决：**needs_review / static_review；仅 development_diagnostic**。公开目标是共享 delayed 上游在联合写入时每个只执行一次，包含 schema inference 造成的重复执行；评分主要检查列裁剪图结构。完整 gold 有合理局部机制，但不足以宣称目标完整修复。

## 独立发现与交叉后的补充

封存初稿已独立发现以下事实，并非看到主审或历史后追认：四个 F2P 都是 getitem 图结构代理；没有上游计数；新建 out 未被测试尾部 compute；Arrow infer 仍同步采样；gold 保留高层图依赖；同路径不同写选项的 token 风险未证明为新增回归。交叉后与主审核心技术结论一致，不按意见人数决定。

| 公开需求或被验性质 | 断言、helper、调用者依据 | 最终判断 |
| --- | --- | --- |
| 两个 dataframe 联合写时共享 delayed 各执行一次 | 公开两 delayed 示例；test.patch 全部改动只建立读取、getitem、写出图 | 缺失计数；四个参数组合不等于四项独立语义目标 |
| schema='infer' 不追加重复上游执行 | parquet/arrow.py:836–873，object 列经 to_delayed 后在 860–862 调用 compute；在写图构造前发生 | gold 未改此分支，不能用写图共享推断采样结果也被缓存共享；不据静态代码声称精确四倍 |
| 列裁剪图层可见且只读 B | test_parquet.py:2256–2275，手动 optimize_read_parquet_getitem；前缀 read-parquet、BlockwiseParquet、columns==['B'] | 列裁剪局部正证据；对等价其他层名/图表示有具体静态误拒风险；未运行完整替代解 |
| 输出值正确 | 保留尾部 assert_eq 比较 ddf.compute(optimize_graph=False) 与 ddf.compute() | 计算的是读取 Series，不是 out 或 write 目录；不能补足写入与计数目标 |
| 既有 IO 行为 | 延迟写、schema/append/compression/kwargs/index/null 等 P2P 风险抽查 | 有局部回归证据；169 个 expected P2P 逐 ID 状态核对不能冒充全语义覆盖 |

完整 gold 只改 parquet/core.py：以原 df 分区键构造写任务，用 HighLevelGraph.from_collections(dependencies=[df]) 替代逐 to_delayed 的独立优化。结合 dataframe/core.py:1474–1497 的 optimize_graph=True 默认值，这确实避免提前分别优化共享上游。Arrow/FastParquet 写入、metadata 汇合、Delayed、HLG、优化 helper 已查，gold 不是题意来源。

交叉后补充确认：dask/delayed.py:464–467 的普通 Delayed optimizer 仅 ensure_dict/cull，不能从测试手动调用 dataframe 优化器推断 out.compute 自动做相同投影。io/io.py:580–615 显式 meta 会跳过 make_meta 的计算，公开例已有 meta，因此不能把问题笼统归因于 from_delayed 自动探测。core.py:536 创建本地 kwargs_pass 字典，旧记录“修改调用者 kwargs”不成立。tokenize 漏 compression/engine/write_metadata_file/backend kwargs 是条件性碰撞风险；涉及同路径写语义，仍未证 check26 新增破坏。

## 原对照证据与旧发现裁定

原 pair 仅使用 private/run_refs 精确授权的 compat_v3 本题 gold/noop ledger 第 1 行及日志，候选/base/测试投影摘要与原日志差异均已独立核对。base 为 5589bfddb5982777d29e424fa438f1667a74a60a。noop 的 git status/show/diff 支持其历史 base 状态，gold 的实际差异与 gold.patch 对应；这不是 actual actor 初态或实际交付证明。

原命令为 `pytest -n0 -rA --color=no dask/dataframe/io/tests/test_parquet.py`。两边先离线执行 `python -m pip install --no-index --find-links=/opt/rh2/compat-wheels --no-deps pandas==1.1.5 fastparquet==0.5.0 pytest==7.4.4`，再 `python -m pip install --no-deps -e .`，安装 RC=0。原 before/after 脚本只改变安装条件，未改变目标选择。日志直接记录 Python 3.8.15 / pytest 7.4.4。371 collected；noop 8 failed / 355 passed / 1 skipped / 7 xfailed、RC=1；gold 363 passed / 1 skipped / 7 xfailed、RC=0。skip/xfail 不在 expected 的四 F2P +169 P2P 中。

| expected F2P，test_getitem_optimization 参数 | noop 原日志 | gold 原日志 |
| --- | --- | --- |
| pyarrow-index1-True | FAILED:1708；1257–1260 无 read 层导致 IndexError | PASSED:1418 |
| pyarrow-None-True | FAILED:1706；1175–1178 同类 IndexError | PASSED:1416 |
| pyarrow-None-False | FAILED:1707；1200–1231 构图/cull 中 DataFrame truth ValueError | PASSED:1417 |
| pyarrow-index1-False | FAILED:1709；1283–1314 同类 ValueError | PASSED:1419 |

其余四个 fastparquet 参数也失败，但不属于 expected F2P，不能改写分母。169 P2P 均逐 ID 匹配两侧 PASSED；具体选择和风险抽查区段保留于封存初稿。额外完整核查 scheduler 测试 test_parquet.py:1857–1877：wrapper 只令 flag[0]=True，再 assert flag[0]，没有任务/上游执行计数。旧记录把它称为图形或计数保障不成立。test_graph_size_pyarrow:2241–2253 序列化的是读取 ddf2 图，不能证明写图缩小。主审已纠正后者与 kwargs，但对 scheduler 旧说法此前只保留未核，本 reviewer 现补充直接源码裁定。

旧 L1 的缺 fastparquet / pytest8 失败不能覆盖当前 compat_v3 原 pair；历史 hints 中被复述的 infer 维护意图只作为旧记录说法，本轮未读原 hints，不能用来静默删除公开目标。

## 分歧收口、结构与唯一下一步

初稿 check2=pass 只支持 base 有相关机制，容易被理解为公开计数例完整复现；最终采用主审 **2=unknown**。初稿 check16 的历史候选正证据不等于真实 actor 交付；最终 **16=unknown**。保留历史绑定事实。最终 **20/23/24/25/27/32=issue，26=unknown**；24 表示具体误拒风险，不是“所有其他解必拒”。check3 实际输入 unknown 不代替 check23 的公开规格争议。

主审 screening_record 有规定 13 个顶层字段，checks 采用原 1–40 编号且有 status/evidence_refs/by，issues 有 category/scope/evidence_refs/proposed_action/status；additional_exclusions=[]、revision_refs=[]、成本未观测为 null。check9/17/18/19/21 等 pass 仅限本次精确历史 pair；19 的身份匹配不证明需求覆盖。主审的 reviewer=not_read 为交叉前封存状态；本 review 是后续 reviewer 证据，root 收口时应引用，reviewer 不回改封存文件。

唯一优先下一步：在获准的私有 CPU 验证中按公开例做 base/gold 普通 schema 与 infer 的分阶段上游计数对照，显式 pyarrow、两独立临时目录，分别记录构建和联合 compute。独立目录是排除原同路径写冲突的诊断调整，必须记录；不能改原题来迎合 gold。结果可决定 infer 残留规模与验收应覆盖的阶段，本轮未执行。

## 审查边界、原件索引与封存

八方面按独立初稿及本审稿收口：公开目标与需求—断言双向关系；base/patch/身份；全部新增断言和决定性 helper/逐 F2P/风险 P2P；合理非gold与误拒；完整 gold 与相关调用者/回归；开发依赖和资产；源码交付与可信恢复；公开/私有材料暴露。全仓与第三方全实现、actual actor 消息/初态工作树/权限/资产/开发工具条件未取得，仍 unknown；不能以导出的 Git base、路径存在或历史 grader 条件替代。镜像 source digest、actual image ID 与脚本摘要分别记录于下表，不因本机目录缺失猜测镜像资产。

仅在 root 明确 cross_review release 后读取本题 public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json 与 history/refs.json 指定的历史内容。未读根汇总、其他包/角色结果或未授权历史原件，未执行/导入项目、测试、网络、安装或实验，未派生 agent。此阶段仅写本题 review.md；三份 reviewer_initial.md 均保持原 SHA。新成本、实际 actor 条件、跨环境可复验与训练适配未观察，不造资格；additional_exclusions=[]、revision_refs=[]。

原日志逐行位置、全部 expected 状态表、源码阅读区段及未读范围详见封存 reviewer_initial；本审稿明确更正处优先。以下摘要固定本次交叉读取的具体版本；它们是审计定位信息，不是用摘要替代内容审查。

| 原件 | SHA256 / 定位 |
| --- | --- |
| [reviewer_initial.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-6801/reviewer_initial.md) | `cb1a9e8de841e81d7510815041f3bfc7978abc32eb55756a9381a674fcd7edab`（封存，未改） |
| [public_read.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-6801/public_read.md) | `24ca52cd4e51548a82240f55b9ce0fd2d28d56b5dd35ed09eb9d0f422bbeea10` |
| [analysis_before_history.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-6801/analysis_before_history.md) | `63f149eb941bb9e99be20f405e8c3c3fad1ee6e1ed968e4909bef6dc7e6a8216` |
| [old_findings_delta.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-6801/old_findings_delta.md) | `29a9fe4f6ecee3c7ec29ffee2e489de2c71447964a5d91ea01b23613ea687c34` |
| [card.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-6801/card.md) | `823cbe410195b8805516e7702afafd12940b53bd04473ceae5bda91c382b7ba9` |
| [screening_record.json](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-6801/screening_record.json) | `e747dd49aba7fa7f8546644bb1b56355a5d6ea5c1df60ee0e640c82a77357ae5` |
| [PUBLIC/user_prompt.txt](/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/dask__dask-6801/user_prompt.txt) | `9eccdffbde611da92e5125d92807177e066a2663ec7d21d8896dc07e9fd5c832` |
| [PUBLIC/base_identity.json](/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/dask__dask-6801/base_identity.json) | `22d34a00ad2f1a320b1ad4c29b9aeba164654ec562698fa53a8a5d1e1c4d7d3f` |
| [PRIVATE/gold.patch](/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/dask__dask-6801/gold.patch) | `4c7a12dfd989740a37dab9a77f86b3dec7e59f894d01447684e06e1145b5d185` |
| [PRIVATE/test.patch](/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/dask__dask-6801/test.patch) | `ca7b93598aa3bb27738e0e51cd74d3974ea441be37a21de0c0497ab08b97aa5c` |
| [PRIVATE/grading.json](/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/dask__dask-6801/grading.json) | `49927076956ccd4fe76c9a82994f95c0a4acd2cb3b874f664f93b55c11169018` |
| [PRIVATE/run_refs.json](/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/dask__dask-6801/run_refs.json) | `4cf092f4f0078ac073f163549029eace96a767cf3c07ce8b1813fd7e0f8be6ed` |
| [获准历史 L1_dask/dask__dask-6801.json](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/records/dask__dask-6801.json) | `0bf09007a604f064fa216d43a69547c7c6779eeb4e72c139596a4dd1c13353f2` |
| [gold 原日志](/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/compat_v3/tasks/dask__dask-6801/gold/eval_logs/evallog_replay-er19-compat_v3-da_8671cb8c.eval.log) | `3ff08305fa585658eece7eee40321ab261ef008697c80432522d5f138c7e5dfe` |
| [gold 原 ledger 第 1 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/compat_v3/tasks/dask__dask-6801/gold/ledger.jsonl:1) | 行 SHA256 `76c617470ce07f3194b73a2ccc6aad7175b4bad5fe4b186ab2cdd19d4beecf22`；仅授权行 |
| gold 镜像/脚本身份 | source `sha256:b9dbc69abe704126d82a4b3b05b9da7237b430971e63b76e0688b5b52f1fbb9e`；actual `sha256:83edfe0e19540a793fb328e5276e5531381b2b8ce48a6f6e2d7be9d6a950cc98`；scripts `sha256:068923e3885087f41db7d1c2e9948f9c4ec752cf2be7da54d825840c81d228e2` |
| [noop 原日志](/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/compat_v3/tasks/dask__dask-6801/noop/eval_logs/evallog_replay-er19-compat_v3-da_c2afc4d4.eval.log) | `5fa8407dbdc91cec8871099e0a54b257ea10011de9caafa9723065e4ccba94f8` |
| [noop 原 ledger 第 1 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/compat_v3/tasks/dask__dask-6801/noop/ledger.jsonl:1) | 行 SHA256 `0e3d941dc464b23ce5e3993a3070810fd1e4d52778e0a55f3a9ea61ef039ac90`；仅授权行 |
| noop 镜像/脚本身份 | source `sha256:b9dbc69abe704126d82a4b3b05b9da7237b430971e63b76e0688b5b52f1fbb9e`；actual `sha256:83edfe0e19540a793fb328e5276e5531381b2b8ce48a6f6e2d7be9d6a950cc98`；scripts `sha256:068923e3885087f41db7d1c2e9948f9c4ec752cf2be7da54d825840c81d228e2` |

审查者：pack07_dask independent reviewer；阶段：root 已解封后的 cross-review。所有最终意见均为静态判断，未发出正式评测或训练批准。
