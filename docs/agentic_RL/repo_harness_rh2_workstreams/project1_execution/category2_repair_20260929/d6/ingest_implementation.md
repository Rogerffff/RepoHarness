# D6 首片：类型与可信入库实施记录

2026-09-29。**本切片已实施并通过本地定向验证，尚不代表正式 actor／评分端到端验收完成。** 用户已明确批准 SWE 正式材料修订机制先用 mypy10424／17071 验证；本记录只覆盖本作者负责的类型、可信摄入、独立文本产物和对应测试。没有运行远端／容器／模型，没有提交或推送；未修改 R2E 在制品。

## 交付 API 与范围

- `bundles_v2.py` 新增 `SWEMypyCase(path, base_sha256, case_name, node_id)`、`SWEMaterialRevision` 和继承原 v2 的 `PrivateGradingBundleSWERevision`。专属 schema 为 `rh2.private_grading_bundle.swe_revision.v1`；仅接受 `append_mypy_p2p`。
- `revision` 包含 `revision_id`、`registry_sha256`、`parent_grading_digest`、`public_bundle_digest`、`original_fail_to_pass`、`original_pass_to_pass`、`added_mypy_cases`。后三项为不可变 tuple，JSON 仍为数组。子类重建来源 v2 并核 parent digest，因此不能夹带 test_patch、vendor 命令或原 F2P/P2P 的改变。
- 新模块 `envpack/swe_material_revisions.py` 提供 `load_trusted_swe_revision_outputs(repo_root)`，返回 `.result/.pins/.image_store/.survivors`，另保留 `.source/.registry`；`verify_swe_revision_package_relations(package, public, grading, validation, *, trusted)` 用于 controller 消费期重验。
- `registry.py` 登记新私有 schema；原 v2 schema 与序列化不改。旧 `load_trusted_ingest_outputs` 仍读原目录和原 pin。`ingest_swegym_lite.py` 仅增加子类 import 及共同关系检查中的 `revision.public_bundle_digest == public.digest()`，因此非权威测试入口也不能混配题面身份。
- 修订单校验固定 SHA、身份/base、来源 grading/public/test_patch 摘要、case 所在公开文件 SHA及唯一 case；路径、case 名和 nodeid 不接受 shell／选择表达式。有效 P2P 必须恰好是原清单追加登记节点，重复、交集、未知操作／字段均拒绝。评分面／公开面不含 gold。

正式 controller、prepared、脚本派生、manager 与 replay 由其他负责人接线，本作者未修改这些文件。

## 产物与固定摘要

| 对象 | 路径／SHA-256 |
| --- | --- |
| 首片私有登记与两份公开基线测试文件 | [s2/revisions/mypy_p2p_v1/](../../../s2/revisions/mypy_p2p_v1/)；登记 `69e0373734865687f11bd65f7e1a2d2e097ab478a0603bb446aadb2391457a75` |
| 新独立216题产物 | [s2/ingest_mypy_p2p_v1/](../../../s2/ingest_mypy_p2p_v1/)；manifest `c46fc3c072b437d0af8503f3c83ad846e2762942f6550fc8a05a412f22760ca6` |
| 原来源 manifest（保留） | [s2/ingest/ingest_manifest_v0.json](../../../s2/ingest/ingest_manifest_v0.json)；`3408bab759b0a22ea2f038b908f298c8a1c241d2f710500c52224f14125003a7` |

新正式 loader 同时核原来源、修订单和新输出三层 pin，再从来源重放有效材料，要求五个输出文件与重放字节完全一致。来源重复簇原样保留，不以新增参考改写来源血缘。公开基线测试来自首包已核 SHA 的 base 文件，固定复制到登记资产目录，运行期不依赖被忽略的 `runs/` 材料。

生成入口为 [build_swe_revisions.py](../../../../../../rh2/scripts/build_swe_revisions.py)：`build` 只向新目录首次写入，文件原子落盘、manifest 最后写；存在目录即拒绝，不能覆盖原产物或失败现场。`verify` 只读。已有产物不应重复运行 `build`。

## 实际验证

从仓库根执行：

```bash
rh2/.venv/bin/python rh2/scripts/build_swe_revisions.py build
rh2/.venv/bin/python rh2/scripts/build_swe_revisions.py verify
```

生成216题、回读成功，两题修订 ID 为 `swe-mr-mypy-10424-p2p-v1`、`swe-mr-mypy-17071-p2p-v1`。另逐题调用正式 `verify_swe_revision_package_relations`，216/216通过。

对原／新 JSONL 按 instance_id 比较每行**含换行的原始字节**：

- public 和 validation 两文件216行全部一致；来源 duplicate clusters 文件完全一致。
- grading 和 environment packages 仅10424／17071两行改变，其余214行完全一致。
- 两题 test_patch、eval_cmd、原 F2P 及原 P2P 不变；有效参考分别为10424的1 F2P＋2 P2P、17071的2 F2P＋3 P2P。公开追加文件分别是 `check-isinstance.test`、`check-typevar-unbound.test`；正式恢复／保护与命令选择由消费者切片处理。

从 `rh2/` 执行以下精确命令：

```bash
.venv/bin/python -m pytest -q tests/envpack/test_swe_material_revisions.py tests/envpack/test_bundles_v2.py tests/envpack/test_ingest_swegym_lite.py tests/contracts/test_full_registry.py
.venv/bin/ruff check src/repoharness2/envpack/bundles_v2.py src/repoharness2/envpack/ingest_swegym_lite.py src/repoharness2/envpack/swe_material_revisions.py src/repoharness2/registry.py scripts/build_swe_revisions.py tests/envpack/test_swe_material_revisions.py tests/contracts/test_full_registry.py
```

结果：**107 passed in 6.23s，ruff 全通过**。覆盖真实216题兼容及消费期重验、registry与输出篡改／半写、错误来源/base/patch/public摘要、未知操作、shell／路径／节点错配、重复／交集、嵌套列表变更、确定性写出与拒绝覆盖、私有 schema CLI 和精确注册表枚举。注册表原测试中的完整枚举已同步新增一项，未放宽预期集合。

此轮停止在本切片交付；不重复无关全库测试。共同生产消费、两题真实评分 `0/1/0`、安装配方交付和独立集成审查仍由主线程收口，未由本地107项测试替代。
