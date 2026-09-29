# dask__dask-7138 cross-review

最终裁决：**needs_review / static_review；仅 development_diagnostic**。array_like 转换主体有直接局部正证据，但 gold 把旧形参 array 更名为 array_like，破坏原来可绑定的 `da.ravel(array=...)`。这项静态可证明的兼容性变化应单独处理，不能被 561 passed 抹去。

## 独立发现与交叉后的补充

封存初稿已独立识别：八个新断言、全零样本局限、首条失败后后续 noop 断言未到达、asanyarray/reshape 现有 Array 快路径，以及旧 array= 的签名回归。主审独立得到相同核心结论；交叉用于检验依据和收窄归纳，不作为投票。

| 公开需求或旧行为 | 全部新断言/相关 P2P | 最终判断 |
| --- | --- | --- |
| scalar/list/tuple/nested 接受并返回 Dask Array | 新 test_ravel_with_array_like：0、[0,0]、(0,0)、[(0,),(0,)] 各一条 assert_eq 和 isinstance | 八断言直接验证类型、值与形状；全零不能区分 flatten 顺序，未覆盖空输入/子类等完整域 |
| 现有 Dask 0D–3D、chunks 与图行为 | test_ravel:954–978 有非零数据、图长度约束、不同 chunks | 有实质局部回归证据 |
| 未知长度 1D 快路径 | test_ravel_1D_no_op:980–986 仅 assert_eq | 有结果等价证据，没有对象身份或共享内存断言，不是零拷贝证明 |
| 旧 array= 关键字 | base 签名 ravel(array)，gold 改 ravel(array_like)；新旧测试均位置参数 | 未测且已由签名/装饰器证实破坏；合理修复可保留旧形参并在内部转换 |

完整 gold 只有签名与 asanyarray 转换的局部改动。array/core.py:4058–4095 的 asanyarray 对现有 Array 直接返回；Array.ravel/flatten:1855–1861、reshape:1870–1881 与 reshape.py:146–238 的 1D -1 快路径支持惰性局部行为。dask/utils.py:663–710 的 derived_from 正常分支处理 docstring 后返回原 method，没有关键字别名包装；因此 array= 绑定变化不需要执行项目才能判断。公开提议 array_like/asanyarray 的方向不等于授权删除旧关键字。题面的 asasanyarray 拼写错误可由现有源码辨认，不应强加同名函数或全部 numpy.append 支持。

交叉后细化 helper 证据：array/utils.py:223–328 会同步 compute、检查图、shape/meta、计算结果与自身 dtype 的一致性，再用 allclose/相等比较；263–269 的跨结果 dtype 检查有条件，不应把初稿“dtype 一致性”读成所有 NumPy 参考 dtype 必须完全相同，或 bit-exact 比较。test_array_core.py:2495–2556 有 asarray 的 identity / matrix chunk 测试，但它们不在本次 routines 选择器/expected P2P 中，也不能转移为 ravel_no_op 的零拷贝断言。调用 ravel 的 roll、compress、argwhere 相关测试已追加静态阅读；其余 468 P2P 只有逐 ID 状态核对，未全语义穷举，名字相似的 ravel_multi_index 也不自动算该调用链覆盖。

## 原对照证据与旧发现裁定

原件仅为 run_refs 授权的 round2b/dask7138-pytest-v1 gold/noop 各 ledger 第 1 行、日志及候选原件；base 9bb586a6b8fac1983b7cea3ab399719f93dbbb29、摘要、可信测试投影和历史候选差异均核对。原命令为 `pytest -n0 -rA --color=no dask/array/tests/test_routines.py`，两侧 `python -m pip install --no-deps -e .` 安装 RC=0。

唯一 F2P `test_ravel_with_array_like`：noop 日志 582–598 在首个 scalar 的 reshape 调用抛 AttributeError，最终 FAILED:1179；gold PASSED:1067。noop 未到后续 list/tuple/nested 断言，不能把四类都称为本次实际独立失败。561 collected；noop 560 passed / 1 failed、RC=1；gold 561 passed、RC=0；各 92 warnings，无 skip/xfail。468 expected P2P 逐 ID 两侧 PASSED；test_ravel 为 noop:1063/gold:1065，no_op 为 noop:1064/gold:1066。

更正初稿证据范围：初稿没有确认精确 pytest 版本，交叉后直接补读原日志 gold:585 / noop:565，明确 Python 3.8.15、pytest 7.4.4、pluggy 1.5.0；不是从 recipe 名推断。旧 L1 的 pytest8 故障、pytest<7 才可用的说法不适用于这个成功原 pair；但仍没有完整镜像构建可复验链。旧记录“no_op 保证零拷贝”被实际断言否定；旧全面 pass 结论不能覆盖签名兼容性差异。

公开题面直接给修法方向，降低独立定位的诊断难度；这是公开提示，不是 actual actor 收到私有 gold 的证据。历史 grader 的成功与用户实际开发环境不同，不能据此赋予任务或模型资格。

## 分歧收口、结构与唯一下一步

初稿 check27=pass 仅认可转换主体，汇总表达过强；最终采用主审 **26=issue、27=issue**，保留局部正确证据，明确旧关键字回归。初稿 check24=pass 只说明断言没有点名 helper/层名；最终 **24=unknown**，没有运行完整非gold候选，不外推所有合法实现的可接受性。合理保留 array 形参并转换是静态可行方向，不是已测试成功的候选。初稿 check16 的历史交付正证据收窄为 **16=unknown** 的真实 actor 总判断。最终 **2/20/23=pass** 只针对公开 array_like 目标及已定位的初态机制，**25=issue** 指输入覆盖/兼容性漏测；它与26的已证新增行为破坏分开。

主审 screening_record 的 13 顶层字段、原 1–40 稀疏编号、每 check 的 status/evidence_refs/by、每 issue 的五个必需字段均符合格式。additional_exclusions=[]、revision_refs=[]，本轮成本未观测为 null；check3/29/33 等 actual actor 状态维持 unknown；9/17/18/19/21 的 pass 是历史 pair 的局部证据，不是生产开发资格。主审 reviewer=not_read 是封存时状态，root 后续收口应引用此 review，reviewer 不回写封存文件。

唯一优先下一步：维护者明确保留既有 array= 兼容，并据此处理 gold 参考与兼容性验收。签名及装饰器证据已经静态明确，不机械增加 CPU 来证明 Python 绑定规则；真实 actor 环境验证属于另一个尚未完成的工作边界。此选择取代初稿将公开 MRE/关键字 CPU 复跑排在优先位的建议，本轮不改原题、gold 或测试。

## 审查边界、原件索引与封存

八方面按独立初稿及本审稿收口：公开目标与需求—断言双向关系；base/patch/身份；全部新增断言和决定性 helper/逐 F2P/风险 P2P；合理非gold与误拒；完整 gold 与相关调用者/回归；开发依赖和资产；源码交付与可信恢复；公开/私有材料暴露。全仓与第三方全实现、actual actor 消息/初态工作树/权限/资产/开发工具条件未取得，仍 unknown；不能以导出的 Git base、路径存在或历史 grader 条件替代。镜像 source digest、actual image ID 与脚本摘要分别记录于下表，不因本机目录缺失猜测镜像资产。

仅在 root 明确 cross_review release 后读取本题 public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json 与 history/refs.json 指定的历史内容。未读根汇总、其他包/角色结果或未授权历史原件，未执行/导入项目、测试、网络、安装或实验，未派生 agent。此阶段仅写本题 review.md；三份 reviewer_initial.md 均保持原 SHA。新成本、实际 actor 条件、跨环境可复验与训练适配未观察，不造资格；additional_exclusions=[]、revision_refs=[]。

原日志逐行位置、全部 expected 状态表、源码阅读区段及未读范围详见封存 reviewer_initial；本审稿明确更正处优先。以下摘要固定本次交叉读取的具体版本；它们是审计定位信息，不是用摘要替代内容审查。

| 原件 | SHA256 / 定位 |
| --- | --- |
| [reviewer_initial.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-7138/reviewer_initial.md) | `502e3261285977f252f65eff4404d7ba5b66e1406561efd005615feee4ac38ef`（封存，未改） |
| [public_read.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-7138/public_read.md) | `193423aeea342015ce4202b7c918345bf035ce0462687970ed0e73b0e2c3d13a` |
| [analysis_before_history.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-7138/analysis_before_history.md) | `171bac649f1b83fbfe7eeab666ac4b5f6b608d273a9f516d37f9166b1a21a097` |
| [old_findings_delta.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-7138/old_findings_delta.md) | `7075756fe1b96a623eadea0d699d912e272009d3bd54624d7b7edb46b5c524ef` |
| [card.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-7138/card.md) | `487ff9120578f868535191271aaefe88bdfde7ed308a5d85109a068408e74215` |
| [screening_record.json](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-7138/screening_record.json) | `caee45e5fc2c9d085a752fc19431573b0efca1d938b7e1c2be72e50aff136588` |
| [PUBLIC/user_prompt.txt](/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/dask__dask-7138/user_prompt.txt) | `b02c916a8faba2fe3718f1e67a58d230df7863c8abd4864ec7e78781200f46c8` |
| [PUBLIC/base_identity.json](/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/dask__dask-7138/base_identity.json) | `c9c2ed6bfd239147e9fb6d2d3516bfd23b398f2163b114f906a5b738576046ef` |
| [PRIVATE/gold.patch](/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/dask__dask-7138/gold.patch) | `d68ca41cd89d5607d0db853a76b4161314033cc70aeefaa59385e828bcf6644b` |
| [PRIVATE/test.patch](/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/dask__dask-7138/test.patch) | `0b2bb2830ddee05ce5c37b304bf3122662f057871f8bc2c49aa4288bb455792e` |
| [PRIVATE/grading.json](/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/dask__dask-7138/grading.json) | `3bdf170b94807d9a2a19fbf9711e3cf83b9d836feac9ed4e1582bbee00cefaf0` |
| [PRIVATE/run_refs.json](/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/dask__dask-7138/run_refs.json) | `4765e656f6831c70ff5e2b65dc2cbd9587147264dc6473390dff0bf0fe540161` |
| [获准历史 L1_dask/dask__dask-7138.json](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/records/dask__dask-7138.json) | `ea6f61ecb906af265925354e43bc1ba97b06e416cdb90fceef0e166945345cc5` |
| [gold 原日志](/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/round2b/runs/dask7138-pytest-v1-gold/eval_logs/evallog_replay-er19-r2-dask7138-_979d801a.eval.log) | `1cbe85b89c848aa3872a7e50f88db516e72cd601774f434ed85ac8ee3270997a` |
| [gold 原 ledger 第 1 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/round2b/runs/dask7138-pytest-v1-gold/ledger.jsonl:1) | 行 SHA256 `e5ba76ee026910cc16e852827ac7333bcb253d2714fc41b0c66381b5c735ec36`；仅授权行 |
| gold 镜像/脚本身份 | source `sha256:91df52cb66bb64003ecf4721832eae373c701536aa3dcb85ddc7d9e0ea757736`；actual `sha256:281a1a511f29617325b7663eba79fe6a51d9710c9fbb2ee40f13df09f8332389`；scripts `sha256:b3c18dbeea69cce27bd9e1e85a1e7caad3529b53b35a4b14ce46268e34535f1b` |
| [noop 原日志](/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/round2b/runs/dask7138-pytest-v1-noop/eval_logs/evallog_replay-er19-r2-dask7138-_cc53c2de.eval.log) | `8cc3ad60155fcb25c890175031179edb08429ef10f348a2680af75b5f8e7fe7f` |
| [noop 原 ledger 第 1 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/round2b/runs/dask7138-pytest-v1-noop/ledger.jsonl:1) | 行 SHA256 `b5a07c50f2bd4003a6f2f810f64dec849d35fbb4c1b84f01bad133abafd77bba`；仅授权行 |
| noop 镜像/脚本身份 | source `sha256:91df52cb66bb64003ecf4721832eae373c701536aa3dcb85ddc7d9e0ea757736`；actual `sha256:281a1a511f29617325b7663eba79fe6a51d9710c9fbb2ee40f13df09f8332389`；scripts `sha256:b3c18dbeea69cce27bd9e1e85a1e7caad3529b53b35a4b14ce46268e34535f1b` |

审查者：pack07_dask independent reviewer；阶段：root 已解封后的 cross-review。所有最终意见均为静态判断，未发出正式评测或训练批准。
