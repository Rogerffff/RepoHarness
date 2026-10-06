# SWE 材料修订首片：复用 mypy 公开 P2P

2026-09-29。用户已批准正式机制先用 mypy10424／17071 验证。此目录保存带代码 SHA pin 的 `material_revisions.json` 和登记引用的公开基线 `.test` 文件；没有新增测试正文、替换题面或修改来源 test_patch。

原材料仍在 `s2/ingest/`；有效216题产物写在 `s2/ingest_mypy_p2p_v1/`。两题仅追加已存在的3个公开 case 为 P2P。公开文件的来源、正反对照和安装复用清单见 [首包材料](../../../project1_execution/category2_repair_20260929/swe_materials/first_mypy_bundle/materials_manifest.json)；实现与107项定向验证见 [类型／入库实施记录](../../../project1_execution/category2_repair_20260929/d6/ingest_implementation.md)。这份登记不等于正式评分已验收。

可信入口为 `repoharness2.envpack.swe_material_revisions.load_trusted_swe_revision_outputs`。它从旧受信来源重建有效包，再核本登记、公开文件摘要和新输出 manifest；禁止通过手改 prepared／grading JSON 使用材料。后续变更应新建版本并更新代码 pin，不覆盖原文件或历史评分。
