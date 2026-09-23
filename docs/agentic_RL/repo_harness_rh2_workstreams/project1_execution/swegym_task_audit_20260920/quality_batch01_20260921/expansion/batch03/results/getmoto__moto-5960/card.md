# getmoto__moto-5960

**needs_review / static_review；development_diagnostic。** 基线 `d1e3f50756fdaaea498e8e47d5dcd56686e6ecdf`。目标是让 GSI scan 遵守 INCLUDE/KEYS_ONLY。gold 先复制再调用公开投影 helper，已查核心路径合理；当前评分遗漏一项明确公开要求。

| 需求/旧行为 | 判据与结果 | 结论 |
|---|---|---|
| GSI INCLUDE scan | F2P `test_gsi_projection_type_include` 新增首项4字段相等 | 单项覆盖；未核scan总数/全部项 |
| GSI KEYS_ONLY scan | 同名P2P只执行query；第二F2P实际是LSI scan | **缺失**，公开第二复现未进入评分 |
| LSI KEYS_ONLY scan | F2P `test_lsi_projection_type_keys_only` 首项3字段相等 | 共享模型支持，但issue只写GSI，范围待澄清 |
| 扫描后原表数据完整 | 已有复读P2P只走无索引ProjectionExpression | 索引投影后的复读缺失；gold复制正确避免损坏 |

部分修复可能仅漏 GSI KEYS_ONLY 分支，或直接对原 Item 投影而损坏原表；源码与断言支持这些风险，**未执行候选，不声称已观测满分反例**。旧记录的“漏复制全绿”也仅为静态预测。

八方面范围：公开需求/完整patch/两个F2P已逐项映射；155 P2P名单全部读、只展开相关函数；response→backend→scan/project/filter与分页调用已读；gold与非gold路线已评；开发材料/hygiene已查，正式actor输入、权限与工具闭环未知；环境与原日志已查，当前镜像可用性未验；历史对照已完成，独立reviewer已完成；未做模型、CPU探针或训练准入。

install_wave1 实际执行原spec的make init与单文件pytest，gold158pass、F2P2/2+P2P155/155、reward1；noop2fail156pass、F2P0/2+P2P155/155、reward0。两个带空格参数节点均pass，158节点合并成157解析键只证明身份丢失，当前无错分证据。旧离线安装失败不适用于这两行新条件；apply/grader用户不等于正式actor。

唯一优先下一步：base/gold加一份仅遗漏GSI KEYS_ONLY投影的候选，对照原评分与题面两GSI例的全项/数量；附存储复读观察，不再强制去copy第二候选。全部未执行；LSI范围疑义单独保留。

证据：完整双向表、展开范围、日志身份见 [封存初稿](analysis_before_history.md)；精确历史核对与单位限定见 [历史差异](old_findings_delta.md)；可定位ledger/引用见 [结构化记录](screening_record.json)。封存于2026-09-20T21:48:04.328918Z / 2026-09-21 05:48:04.328918 SGT。独立复核已完成，见[复审](review.md)。

协调裁决（2026-09-20T22:11:49.417478+00:00）：受限静态开发诊断候选：gold沿已查共享投影路径合理，历史2F2P/155P2P分差成立；明确GSI KEYS_ONLY scan和索引后存储保持仍漏测，LSI额外范围保留疑义。一个有目的的部分实现可校准分数外推，尚未执行。 同包源码关系已核：5960的scan复制/投影核心原样存在于6185 base；6185类型校验核心原样存在于6408 base，6408 scan另有返回值式演变。仅为公开源码包含/演变，不证明Git祖先、重复题或实际solver泄漏。
