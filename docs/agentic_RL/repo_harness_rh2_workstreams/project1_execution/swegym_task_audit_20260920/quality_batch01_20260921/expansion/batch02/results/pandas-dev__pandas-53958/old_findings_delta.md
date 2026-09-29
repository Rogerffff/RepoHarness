# pandas-dev__pandas-53958：历史差异

独立初稿SHA256=`f2da3107461dcacece34bdbdddeb0e22d38a4a25cdcc42d1f2856dd7bacbcc8e`，协调者校验封存后才读本题history/refs及其唯一 `env_overnight_20260916/L1_modin_pandas/records/pandas-dev__pandas-53958.json`。封存稿不回写；未读reviewer或批次聚合。原始后续仅按instance_id提取 `s2/raw/swe_gym_lite_full_f70b1a29.jsonl:169` 的本题hints。

| 旧主张 | 处置 | 新的决定性证据及影响 |
| --- | --- | --- |
| 材料对应、base缺新增入口、gold自洽，11参考唯一命中 | 确认（限定范围） | 本轮完整读测试与类型定义，并核w06-2 ledger11/12及两原日志：noop名称16对18，gold11通过，missing/skipped为空。性质是导出API扩展，不是缺失值运算修复；命中干净不等于oracle语义完整。 |
| 题面提了typing，所以要求充分 | 推翻其充分性结论 | 同一题面也明确问是否向 `_libs` 加NAType，并以“Another option”提出typing，没有选择定论。公共typing文档支持偏好而不排除另一选项；隐含唯一目标不能从gold反推。保留初稿的合法替代误拒疑点。 |
| raw hints仅一句，没有题面外关键信息 | 文字确认，影响判断修正 | 精确原raw行169为 `Adding to typing makes sense to me.`，这是支持其中一个方案的意见，比单纯重复题面多了一层方向，但未署明最终排他决定。当前S2/public bundle的public_hints是harness说明，不含该句；不能把未提供的评论当actor已知，也不把它自动解释成唯一公开规格。 |
| F2P只检查名称，placeholder可以蒙混 | 结构确认，运行结论仍未证 | `Base.check`只比较dir字符串，未读取新属性对象；全10 P2P也没有新类型身份断言。初稿独立提出更自然的误导出singleton值/漏__all__情形。尚未写或执行假补丁，因此只记静态漏测，不能填写真实RH2假阳性已证。 |
| 精确命名空间约束完全隐藏，agent无法预知 | 精确性确认；不可见主张推翻 | 当前公开base里完整包含同一test_api.py的Base.check、allowed_typing和旧约束；私有patch只加两名字。约束是已有API规则，不是新强制helper或导入写法；无需因精确比较本身就改成包含关系或额外向题面抄验收。目标命名空间争议另列。 |
| 题面逐字包含gold两行，属于最严重solution leak，应删题或删imports | 不采纳该定性/处置 | 两行是题面说明**已经有效的旧入口**的必要示例；标准重导出复用它们很自然。题面主动提出方案应如实记为“给实现方向、补丁小”，不能据文本重合证明未来答案污染，也不能静态推断目标基座难度或训练价值。删掉目标/旧入口会损害题意，当前不改写或剔除。 |
| Meson缓存令本题极便宜，完整评分不到15秒 | 历史局部事实确认，泛化撤回 | 新原件有Meson reconfigure、ninja仅生成version；安装8–9秒/test4.5秒，但账本还有准备/重建/清理阶段。不能把两段相加当完整评分总时长、actor冷构建时间或模型成本。历史CPU信息可引用，本轮未知成本仍null。 |
| 段外pip ERROR键污染判分 | 当前接线已隔离；告警本身保留 | 新账本段外parsed=1、段内11、reference missing0，当前v2只解析Start/End内。原日志xarray对pandas dev版本的依赖元数据告警确实存在；它没有阻断源码安装和本题测试，不代表全环境pip check健康。 |
| 标量/dtypes旧测试可补新导出身份，回归pass | 不把建议当运行事实；建议需精确化 | 所读scalar singleton/NaT identity保护旧对象，若新api.typing名字绑错而旧对象不变，这些旧测试仍可能通过。要测本题导出身份，应在**选择后的入口**直接对照现有真实类/单例类型，不用邻近目录测试数量代替；本轮没有执行更广回归。 |
| 与其它pandas题无关系、无运行环境问题 | 本轮未核实相应广义结论 | 不读他题来认证关系；已有grader成功仅覆盖其UID54322/deny_all/旧环境。当前actor实际消息/激活/权限/资源和完整镜像可见资产仍未知。 |

本轮初判保持：`needs_review/static_review`，有具体公开选项—官方唯一入口争议及对象身份漏测。Gold实现一个合理候选且历史oracle成功，不足以消除这两点。历史没有提供能纳入当前公开输入的排他设计定论，也没有新的真实替代/错误解执行原件。

唯一优先下一步仍是固定grader条件中的 `_libs` 单独真实类型重导出对照：确认旧/新共同入口对象身份与兼容性，再取原官方验收与RH2分数。只有实证后才决定补公开设计意见或修订标准；并行存在的身份漏测保留，不在本次静态工作中改测试。后续正式actor启用前另做导入、Meson路径权限和公开窄验证，不能以语义对照或历史grader成功代替。未产生新CPU/模型/费用证据。
