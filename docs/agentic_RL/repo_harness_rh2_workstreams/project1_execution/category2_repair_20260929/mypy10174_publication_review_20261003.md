# mypy10174 正式材料消费者窄核

2026-10-03。可把该候选合入下一版 CPU 发布。题级正式评分和实际 actor 验收仍由题主完成，不因本地维护检查取得探针资格。

候选为 `runs/category2_repair_20260929/release_work_20261003/mypy10174_combined_swe8_v1/`，父为第五版 manifest `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`。根逐项核实父 837 件、候选 848 件，8 改／11 增／0 删与 delta_manifest 相符，未改的 Git、R2E、builder 及其余资产逐字保留。

根已读两份生产文件完整增量、受影响测试及维护结果。本次只为 10174 新增受限有效测试补丁类型，保留真实 base 文件、原补丁与既有节点。新增 case 不是 base 中已有测试；代码明确拒绝伪装为既有 case，核唯一新增、固定文件／摘要、来源题目与父材料关系。受信恢复／应用与候选测试剥离复用现有路径，不增加安装脚本或改变原奖励语义。公开材料不变。

实际评分选择原 1 F2P／2 P2P，再加入固定新 P2P `testStrictEqualityWithFixedLengthTupleInCheckWithoutStrictOptional`。原 `testUnimportedHintAnyLower` 仍由原子串选择覆盖。有效补丁 SHA `91ea4e972129deaf770ef9e72aa26d11d9bafca85229eae6931f2b22568322cf`；真实 base 文件 SHA `faf0a2a1512eba689901ec6a4df57bc1be9183d2616f6846c8dc9ada181884ec`。原始补丁与增加 case 后的差异有维护验证，不能把合成评分日志测试当作题级运行。

已核作者 321 项维护原日志及 SHA，包含错误资产／来源／旧资格拒绝、actor/host 同 spec、真实本地 Git fixture 恢复、候选测试修改剥离；未重复运行这些无变化的检查。双侧实际 264 consumer 快照仅 10174 材料身份改变，原 7 条 SWE 和全部 R2E 保留。后续合包须再次核最终组合的变更范围。

统一 SWE8 producer 为 `s2/ingest_mypy10174_swe8_v1/`，manifest SHA `2ac0e972d6ec699125f58ff6d1ec895bff35f0d0004999d5d1cc1e6d915bde2c`。代码补丁之外的 4 件登记／补丁／base 资产和 6 件 producer 输出必须一起发布。15184 新发现的泛型 F2P 不在本片，不因同仓误称完成。无 SSH、Docker 或题目执行。
