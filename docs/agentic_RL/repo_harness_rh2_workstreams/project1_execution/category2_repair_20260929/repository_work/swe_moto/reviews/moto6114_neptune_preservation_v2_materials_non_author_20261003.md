# Moto6114 Neptune 名称委托 P2P v2 草案：非作者静态窄核

2026-10-03。结论：**固定三件草案未发现需在发布前修复的静态阻断。** 新有效 test patch 可以严格应用原公开 base，完整保留 R7 的 35 条测试函数及 ARN/name identity 断言，只增加两条既有名称委托行为测试。该两条 P2P 范围现已获题级裁定批准，实施与运行验证仍待完成。新参考为 1F／36P，共 37 条；这不是 37 条测试已经运行的结论。

本次范围是材料静态审查。我已接触私有评分参考、实际 Qwen patch 和先前语义审查上下文，不能作为公开盲读 solver。仅使用标准库读取、SHA256、JSON、tar 成员读取、内存中逐 hunk 文本应用和 AST 核对；没有导入或执行项目／SDK、Docker、CPU、模型、远端或测试。只新增本报告，没有修改三件草案、原件、固定 R7、已有报告或 probe request。没有重复 Qwen 完整语义审查。

## 固定输入和实际读取

草案目录：`tasks/getmoto__moto-6114/neptune_name_preservation_v2/`，相对于本题工作包根。

| 输入 | 实读字节 | 实读 SHA256 |
| --- | ---: | --- |
| `proposal.json` | 5556 | `8eeba063ece96a69992f73fb12d1ee386c6ff41f8f275432ec02a93c336edf31` |
| `proposed_effective_test.patch` | 2748 | `2a9661d78743cf5e36f8363e308d63260ab2076bf4bc1d68de8a9e5fd226dda4` |
| `decision_brief.md` | 2815 | `00c07d1bf57535fb9470091684b655e90bf2cbaa49258e93fd2a577fc467ec3f` |
| 原公开 `tests/test_rds/test_rds_clusters.py` | 27917 | `5d8d00b39173ff60d8a7f0273787d4d8fcd2231a3fdc231113a70f9531f99e34` |
| 旧 `revised_test_draft_v1.patch` | 1336 | `fe211059864c661a557758f5c5ed4106016c767cbe98eaef4718733008a87d5f` |

三件草案与题主给定 pin 一致，proposal 中 base test、旧 patch、新 patch 的路径、摘要、字节数也逐项吻合。原公开 base 读取自 `runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114/base/`。同时读取 R7 冻结包 `runs/category2_repair_20260929/releases_20261003/r2e_088_swe12_git_candidate_v1/` 的 manifest、相关材料 registry、旧有效 patch、公开和私有 bundle 的本题行，以及已有 v4 `expected_runtime.json` 的本题参考分区。

R7 manifest SHA 为 `f9dfcd16c9c88e4f514512e61781856b7d6f1a71a20b64cd1843d20546c5009b`。其冻结 `effective_test.patch` 与旧草案逐字一致；`material_revisions.json` SHA 为 `27e1b01dfec9aa2284e79fec753f70b62f6bd45462346483484f98785a59ae22`，其中 `moto6114-cluster-identity-v1` 绑定相同 base、base test 和旧有效 patch。公开 bundle 的 base 为 `f01709f9ba656e7cf4399bcd1a0a07fd134b0aec`、workdir 为 `/testbed`，与 proposal 相同；功能 statement SHA 为 `sha256:1bf351c6cac9794d802f518053cefdfb62a47e07b5ca8f1254f05a29855339c3`。本次草案只包含测试 diff，没有题面或项目源码 diff。

R7 冻结 `public_bundles_v0.jsonl` 为 684749B／`278a52be906f4f5fe98418f5bfd6536e97b333b0fdc9bbd15cd1328ae8c5f7f3`，`grading_bundles_v2_v0.jsonl` 为 2295611B／`6b863e2fdcca425a2e71dac78503ffdf1182450f57bb7f051d481d24f9533d09`，都与发布 manifest 相符。只核本题行，不重新审查其它题材料。

## 应用、旧断言和 37 条引用

旧 patch 的 1 个 hunk、新 patch 的 3 个 hunk 均在内存中按原行号、上下文、旧／新行数严格匹配，只有一个目标文件 `tests/test_rds/test_rds_clusters.py`，没有 fuzz 或 offset 回退。新 patch 是应用到原公开 base 的完整有效 patch，不能再叠加到已经应用旧 patch 的文件上。

旧 patch 应用后文本为 28566B／`bfe882b96a69e067dd18f5ae15b57e8ab64f33807670c2875a77a8d817abdf05`；新 patch 应用后文本为 29581B／`82c17bd8eaecec33bc2c65dd2ee81556bf3a357b98ab857b0042b38776ceeb13`。这些是内存核对结果，没有写回工作区。

原文件和旧 R7 有效文件各有 35 个唯一的顶层 `test_` 函数，新有效文件有 37 个。逐个比较旧 35 函数的源码和不含行号的 AST，新文件中全部一致，包含原 `@mock_rds` 装饰器。新文件删去新增的 `mock_neptune` import、`rds_backends` import 和两个新增函数后，整个模块 AST 与旧有效文件一致。

因此旧 F2P `test_describe_db_cluster_after_creation` 的两次创建、第二个集群 ARN 捕获、无过滤长度 2、名称查找长度 1、ARN 查找长度 1、返回 `cluster-id2`、返回 ARN 相等，以及追加的名称／ARN对象身份一致断言全部保留。没有缩小原 34 个 P2P 或改写它们的测试体。

proposal 的 `original_f2p_preserved` 和 `original_34_p2p_preserved` 与 R7 冻结私有 bundle、v4 固定预期分区逐项且顺序一致。三组引用的并集没有重复，恰好对应新有效文件全部 37 个测试名。新增仅为：

- `tests/test_rds/test_rds_clusters.py::test_rds_facade_preserves_neptune_name_start`
- `tests/test_rds/test_rds_clusters.py::test_rds_facade_preserves_neptune_name_delete`

`proposed_counts` 的 F2P 1、P2P 36、总计 37 与这些引用一致。草案没有改变原执行命令或预算；尚未发布的 registry、prepared bundle、消费者实际参考集及预算绑定仍须随正式材料核对，本次不能替未来生成产物作运行证明。

## 新测试 API、隔离和要求边界

我读取了原公开 `moto/__init__.py`、`moto/core/models.py`、`moto/core/base_backend.py`、`moto/core/__init__.py`、`moto/rds/__init__.py`、`moto/rds/models.py`、`moto/neptune/models.py` 的相关定义，以及原 `tests/test_neptune/test_clusters.py` 的 start／delete 用例。还从实际 GPU `attempt/frozen/baseline.tar` 只读相应成员，确认本次关键六文件与公开 base 字节一致：测试文件、RDS models、Neptune models、Moto 顶层 exports、core models、base backend。不存在拿其它版本 API 解释本草案的情况。

原 RDS models 为 160973B／`a614a137f21dce20445cad98611e578b435d4f09a592ced584d887d9edb9250c`；Neptune models 为 16523B／`c5bf4a50b5676592daf8df02dbaef2978019b6d04cbbfdceb0387c6acbcfe906`。构造和调用相容性有以下源码依据：

- 原 `DEFAULT_ACCOUNT_ID` 为 `123456789012`，`rds_backends[ACCOUNT_ID]["us-east-1"]` 符合原 account／region 索引；RDS `neptune` property（1349–1350）返回同 account／region 的 `neptune_backends`。
- Neptune `create_db_cluster(**kwargs)`（260–282）接受 `db_cluster_identifier`，其它构造参数由原默认值补齐；草案明确传 `storage_encrypted="false"`，符合 `DBCluster.__init__` 对字符串 `.lower()` 的要求（76），不会触发遗漏该参数时原默认布尔值的类型问题。创建后状态为 `available`（82），按该名称写入 `self.clusters`（281）。两个测试使用不同名称，各自创建自己的对象。
- 原 RDS `start_db_cluster(name)`（1989–1991）在名称不属于 RDS clusters 时直接交给 Neptune。Neptune `start_db_cluster`（346–353）接受存在的名称，返回 deepcopy 的 `started` 状态对象，并保留原 cluster。因此草案检查返回 identifier、`started` 和对象仍存留均有原行为依据。它没有要求 RDS Aurora 的 start 前提也适用于 Neptune。
- 原 RDS `delete_db_cluster(name)`（1976–1987）对存在的 Neptune 名称调用 Neptune delete；后者（319–326）返回按名称 pop 的对象。因此返回 identifier 和名称已移除均为原行为，而非新增删除保护、快照或 AWS 行为要求。

双 mock 可静态追溯到真实原实现：Moto 顶层 `mock_neptune`（116）实际 `lazy_load(".rds", "mock_rds", boto3_name="neptune")`，`mock_rds`（124）也加载 RDS 的 `base_decorator(rds_backends)`。它们并非两个互不相关的 backend patcher；这里的状态隔离来自原 RDS reset 的 Neptune 连带重置。`BaseMockAWS.start(reset=True)`（81–92）在函数执行前重置所持 account backends；`AccountSpecificBackend.reset`（214–216）重置已实例化区域；`RDSBackend.reset`（1344–1346）先调用同区 Neptune reset，再重置自身。两个装饰器的 `start` 都发生在测试函数创建对象之前，嵌套计数受原实现管理。`decorate_callable`（118–127）在 `finally` 调用 `stop`，最外层 stop（100–116）在默认 `remove_data=True` 时再清理状态。`functools.update_wrapper` 保留函数身份。未发现 double mock 会在对象创建后额外重置、遗留共享数据或隐藏测试名称的静态问题；实际 pytest 环境兼容性仍由 CPU 对照确认。

新增两条直接调用已存在的 RDS backend façade，Neptune setup 也使用原 backend。没有引入 ARN 写操作、跨账户／跨区校验、真实 AWS 规范、原 rename 缺陷全面修复或新的独立评分器。原 Neptune 测试已分别覆盖创建后 start 返回 `started`（108–116）、delete 后列表为空（73–80）；本草案补的是 RDS façade 对已有 Neptune 名称的回退路径。

## 已批准范围和后续读回边界

固定 proposal 明确 `proposed_not_published_not_cpu_validated`、`runtime_execution=false`、原评分及冻结身份不可变；固定 brief 保留提交裁定时的请求措辞，并把四类 CPU 奖励列为计划。未发现三件草案把运行预期写成已发布、CPU 已通过或模型已改判。

报告定稿期间，题主通知两条范围已获裁定批准。我独立读取新机器记录 `runs/category2_repair_20260929/overnight_watch_20261003/moto6114_p2p_decision_20261003.json`（2330B／`db149b0657615ae9562d5723387607387ef6d42eaabbce04f4121722df3ab716`）。其 `state=scope_approved_implementation_and_runtime_validation_pending`、`runtime_verified=false`，只批准现有 Neptune 名称 start／delete 两项，保留原题面／base／1F34P／ARN identity／预算，引用的三件材料及既有语义报告 SHA 与本次实读一致。该决定排除 ARN 写操作新要求、跨账户／跨区 AWS 契约、原 rename 缺陷修复、历史 raw／FrozenPatch 改写及全局评分／训练规则。固定草案旧措辞与最新批准状态分别保留来源，不回写原输入。

原实际模型 diff 仍为 6463B／`bb5eab97577260270def73fc06f8a0aa4917727cb9348afbe871f5905b2eb747`，与 proposal 相符。brief 引用的[既有非作者语义报告](moto6114_qwen_a1_semantics_non_author_20261003.md) SHA `eb30f25349feac4b04d76087e270e76faf318d071647fcdd5a9fd23f7d40c13f` 也吻合；其中的静态异常推导没有升级为本次运行结果。原 GPU 的 raw1、35 参考、FrozenPatch 和安装环境问题须保留各自原身份，不能仅凭新草案或安装问题回写原分。

最小两容器诊断工具 manifest SHA `2772408eec3de9501ee20f355bdc154e864a99d1edcb4c9aec955aa0f7e3a2f0` 与 proposal 指向一致；其工具静态结论另见[诊断工具非作者报告](moto6114_neptune_name_diagnostic_tools_non_author_20261003.md)。题主通知 job `moto6114-neptune-2a7e2a72a7c6` 已返回 parent0，但尚未回收／校对原件。本次没有读取其运行产物；该通知不作为本报告的运行验收结论，不能据此宣称 baseline pass／候选 fail 已独立确认。

**本报告不提出新的审批条件，也不要求重复申请已批准的两条范围。** 按已有决定，随后仍须独立读回原 base 的两条行为通过、实际候选的对应失败，再核新身份下的材料发布和必要 37 参考对照原件。拟议 noop／gold／wrong_first／Qwen 奖励目前都不是本次观测值。没有静态阻断，仍不等于 CPU 准入、typed actor 资格或训练资格。
