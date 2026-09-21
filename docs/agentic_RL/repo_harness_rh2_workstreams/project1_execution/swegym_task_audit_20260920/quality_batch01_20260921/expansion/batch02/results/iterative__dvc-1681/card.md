# iterative__dvc-1681

**优先保留为受限静态候选**，状态 `needs_review / static_review`，用途 `development_diagnostic`。base `9175c45b1472070e02521380e4db8315d7c910c4`（DVC 0.30）：旧 `.dvc` 无 wdir，升级后未改数据却报 changed checksum。源码显示绝对 wdir 进入 stage 校验；gold 将序列化字典统一为相对路径，因果方向合理。

| 要求/边界 | 验收与证据 | 判断 |
|---|---|---|
| 旧格式 checksum 兼容 | 唯一 F2P 新建 stage、去 YAML wdir、再检查 unchanged；noop 先在新增 `dumpd()[wdir] == "."` 失败 | 没有固定旧 md5；可能拒绝只在校验输入规范化的合理路线，尚未实测 |
| 非默认 wdir 仍影响校验 | 3 个 checksum P2P 全部 Mock dumpd，含 `.`/`..` 固定哈希 | 保护哈希规则，未保护真实目录转换；抹平真实 wdir 的部分实现疑点未执行 |
| 保存/加载及基础结构 | 12 P2P 中 8 schema、1 real add/load/dump、3 checksum | 不能称所有调用者零覆盖；非默认目录、缓存等回归仅选读未执行 |

修复配方的真实 grader 原件：gold 13 pass，noop 12 pass/1 fail；实际/解析/冻结参考均13个完整身份，reward 1/0。配方固定 awscli/PyYAML/colorama/rsa 并完成 editable 安装，仅证明 rh2grader/54322 条件；actor/54321 的实际消息、权限与开发验证仍未知。旧 Stage1 同样分差已找到原件，但安装曾失败后被末尾 RC 掩盖，status_map 多出 `Could`/`No`；当前配方下未见这些症状，不能沿用旧“环境干净”说法。

八方面已查：公开初态；全部新增断言及13参考、fixture/Mock；合理替代与部分实现；gold、消费者及选读回归；具体依赖/本地资产/updater；源码投影与两文件恢复；本题 #1658→#1681 历史；私有暴露。未验完整替代候选、实际 actor、重复稳定性及跨题关系。gold 去掉 dump(fname) 的外部兼容未知，未见内部传参破坏。默认额外排除为空。

唯一优先后续：固定配方的 base/gold/仅在校验输入规范化三路对照，原13项不变，外置固定旧样本及真实非默认目录/数据变化探针。单删内部断言不足以建立旧格式判别。全程静态，无新运行或材料修订；独立[复核](review.md)已完成，支持内部表示与Mock边界疑点；协调者已收口。固定旧样本先查元数据checksum，缺原XML/缓存时不要求完整status为空；一般覆盖空白不全部设为准入门。主审见过 gold、隐藏测试、旧 hints/修复提交，产物不可交 solver。

证据：[封存分析](analysis_before_history.md)、[历史差异及 SHA 原件索引](old_findings_delta.md)、[40项结构化引用](screening_record.json)。
