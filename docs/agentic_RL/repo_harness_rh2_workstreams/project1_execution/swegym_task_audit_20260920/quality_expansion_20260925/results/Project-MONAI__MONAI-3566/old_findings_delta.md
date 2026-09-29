# Project-MONAI__MONAI-3566 历史差异核对

root 在核验并封存本包全部初稿后明确 history release。本次只读取 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/history/Project-MONAI__MONAI-3566/refs.json` 精确指向的 `/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_monai_1/records/Project-MONAI__MONAI-3566.json` 全文，SHA256=`7dbdf7fba67eee3deb9a781ea18ff480700a57dfbbe2dcc97b3daea2694b4e47`；未沿历史记录链接读旧日志、索引、别题、汇总或reviewer。以下旧日志数字/报错如无本次授权原运行独立支持，均是旧记录自述，不能提升为本次运行事实。H/路径表示该历史JSON指针；P/S/V缩写同初稿。

冻结初稿SHA256=`60772209144b70492316aef2ba6ca03fbf891d2a9baee9be3ea9d17733320ec5`；未改写。证据级别是静态源码推导、旧记录主张、或V/run_refs授权历史真实RH2，三者分开；本轮未执行项目/测试/安装/网络/模型/任务二。实际actor仍unknown，成本未观察null，reviewer未读。

## 逐项对照历史原文

| 历史位置/主张 | 本次判定 | 决定性证据与处理 |
|---|---|---|
| materials_refs、checks1：base匹配，但无关TimedCall变动等于材料对应性issue | 身份确认；问题分类收窄 | 本题test.patch确有10→20秒变更，grading来源与base/attempt仍匹配。无关覆盖不是证据串题；check1局部pass，另列unrelated_timing_coverage |
| checks2：base含缺陷；3题面完整可复现 | 确认静态可理解性；实际输入unknown | 原目录read只imread并读图像字典，题面可理解；新noop在series_meta=True读阶段通用异常，未达标签assert。不能用它当题面无新参数调用的实测；3专记actual输入unknown |
| checks4/17/file_rules：源码与测试无交集且恢复可行 | 确认历史指定候选 | 原日志恢复2个测试文件后apply，projection仅image_reader.py；实际actor文件权限未知，additional_exclusions=[] |
| checks5：26题无重复 | 未核 | 未读跨题索引与别题，不沿用pass |
| checks23、requirement_unreachable：隐藏series_meta名/default False与公开默认例冲突 | 确认实质，收窄绝对措辞 | P原例无参数；V test加True、gold default False。未公开精确关键字有误拒风险；不是“整个F2P行为完全不可推断”，标签保留与该样本期望仍公开可推断。未跑替代解，不宣称实际误拒率接近100% |
| checks24：强制唯一实现两层，精确字符串含空格 | 确认接口偏置；不称内部唯一实现 | 必须接受未公开series_meta是真问题；原样保留标签值与合理保真目标一致。未证明所有规范化都不合法或取首片是唯一算法 |
| checks25：仅一个标签允许只补一个键 | 确认覆盖缺口 | 新测试只idx0008|103e，out未断言；可从结构说明漏测，不声称已跑硬编码作弊候选 |
| checks26：20 P2P中5无关/5因ITK失败排除，所以gold回归issue | 纠正编号与时效 | 有效范围不足归25；新itk_v2共26项全执行，gold全PASS，原5个ITK噪声项也PASS；没有因此证明gold破坏旧行为，26=unknown |
| checks27：“首片TODO说明gold自认不完整” | 收窄 | 首片代表策略未由公开规格排除，TODO不是缺陷证明。gold默认未实现原例标签保留是明确完整性缺口；开启新分支单样本正确且几何构造仍来自体积有局部证据 |
| checks29无泄露 | 收窄 | 题面无修复代码不等于actual actor可见范围安全；29unknown，审查私有暴露单列 |
| checks6/7/11：离线依赖/仓库4片资产均可用 | 确认本地输入与历史grader局部成功；actor未知 | 新itk_v2使用离线wheel目录固定全组件5.2.1.post1、numpy1.23.5；新标签用例成功，actor资产路径权限/解释器未取，不能凭Git blob断言实际读权限 |
| checks9/image_dependency_drift：itkMatrixF44令5项永久失败 | 新授权条件已过时；“永久”错误 | noop/gold日志test_itk_reader_1/3、test_kwargs、test_load_nifti_multichannel、test_register全部PASS；这5项仍不在expected表，执行成功不等于纳入评分。没读旧stage1日志，不复证其原报错；兼容性分类为6而非代码生效9 |
| checks10/unrelated_test_in_p2p：spawn+墙钟在负载下一定随机翻车，建议移除并4容器×10轮 | 保留风险、拒绝当实测失败/自动删除 | helper确实spawn并计时，原patch放宽超时；当前两次原运行5项均PASS，没有重复/并发失败率证据。无关项可供任务拥有者评估，未获授权更改P2P，亦不机械开40次实验 |
| checks20：分差干净 | 收窄 | 原授权run中新旧只1目标不同，但noop是未公开参数导致读取路径失败，尚非公开默认调用标签差异；不能据总分判规格一致 |
| proposed_regression_tests：默认False必须无标签、多键/旧读取路径补覆盖 | 部分接受 | 多标签真值与旧路径验证合理；默认False无标签只有在公开契约先明确该选项后才能成为要求。当前不能以gold默认值反向定义规格 |
| disposition不改题reject、costs.minutes=24 | 不沿用硬裁定/当前成本 | needs_review/static_review，先对齐公共API契约与验收；不直接reject，也不做训练批准。本轮费用/时间未观察null |

## 对冻结初判的影响

主要判断保持：未公开series_meta接口和默认行为错位；原单标签验收不足。旧记录进一步提示TimedCall负载风险，但未提供本次允许范围内可复核的重复证据，故仅列风险与unknown。新授权itk_v2已经覆盖旧5项失败，不能继续称环境永久阻断。初稿未改；既有公共命令和actor unknown继续有效。

唯一优先下一步保持：先统一公开默认示例与series_meta接口/验收；不执行题目变更、CPU或模型实验。
