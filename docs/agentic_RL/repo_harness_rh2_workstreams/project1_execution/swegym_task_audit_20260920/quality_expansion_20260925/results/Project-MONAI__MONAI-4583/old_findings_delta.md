# Project-MONAI__MONAI-4583 历史差异核对

root 在核验并封存本包全部初稿后明确 history release。本次只读取 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/history/Project-MONAI__MONAI-4583/refs.json` 精确指向的 `/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_monai_2/records/Project-MONAI__MONAI-4583.json` 全文，SHA256=`5414f03cbe835279918e621548e1ccca9b0084e2c857f0d60d0fef75a0a80534`；未沿历史记录链接读旧日志、索引、别题、汇总或reviewer。以下旧日志数字/报错如无本次授权原运行独立支持，均是旧记录自述，不能提升为本次运行事实。H/路径表示该历史JSON指针；P/S/V缩写同初稿。

冻结初稿SHA256=`10bdd057c1373b8842b1679b70b02517d1a579a1f1fa42bb1f210f728e5f33aa`；未改写。证据级别是静态源码推导、旧记录主张、或V/run_refs授权历史真实RH2，三者分开；本轮未执行项目/测试/安装/网络/模型/任务二。实际actor仍unknown，成本未观察null，reviewer未读。

## 逐项对照历史原文

| 历史位置/主张 | 本次判定 | 决定性证据与处理 |
|---|---|---|
| materials_refs、checks1/2：同题材料，前景反例失败 | 确认 | base标签读取角点与题面反例相符；新授权baseline01 noop4 F2P标签失败、gold4通过，原9项逐项对应 |
| checks3：题面完整，无外链，所以实际输入pass | 收窄 | 公开静态题面可理解，但当前实际actor消息没有捕获，3unknown；原始hints_text空不代表当前public_hints是否交付 |
| checks4/17：测试恢复不会覆盖gold；file_rules建议排除utils | 确认指定候选恢复；不采纳额外排除 | 日志只恢复test_box_transform，projection只有box_ops，与测试无交集。是否任意候选修改utils被完整恢复/过滤仍需当前控制面证据；additional_exclusions=[] |
| checks5：26题中唯一 | 未核 | 不读共享索引/其他题，5unknown |
| checks23：单/双通道例来自公开要求 | 确认 | 新两个fixture分别对应原例与multi-class自然推广；函数文档每通道一框进一步支持，23pass限静态契约 |
| checks24：不锁唯一实现、任取前景/众数都过 | 收窄到静态空间 | 断言仅返回值且未查helper/源码成立；合法替代前景取值空间存在，但未跑候选，不证明普遍无误拒。单通道混合类未定义，众数不是必须支持的新增策略 |
| checks25/部分修复：仅改2D可获满分 | 确认静态漏测，不包装成已运行变异 | 4新增全2D；旧3D rectangle最小角为前景，无法区分；3D稀疏输入由函数3D契约可推。与初稿一致 |
| checks26：缺3D非矩形和包装单独覆盖即回归issue | 纠正 | 包装已在test_value_2d及test_value_3d_mask里真实调用；并非未覆盖，只缺稀疏场景。漏测归25，未证gold新增回归，26unknown |
| checks27：gold正确完整 | 收窄 | 真实前景索引在2D/3D对文档合法输入有正确性论证和9项原运行正证据；未验任意dtype/device/MetaTensor/边界，不宣称全域完整 |
| checks29：无泄漏；题面给期望不算泄漏 | 确认期望输出是合法规格，actual泄露unknown | 未捕获actor工作树/权限/工具消息；审查者私有暴露独立记usage |
| checks6/7/11/13：离线CPU小张量足够、资源pass | 确认最小开发需求和原run局部成功；当前未知 | 公开API只需内存数组，无权重/网络/GPU必需性；原policy2 CPU/4294967296 bytes下跑完，resource为原字段。不能由最大某张量估计整个评分峰值或actor期限必足 |
| checks14/参考ID漂移：CUDA分支重赋TEST_NDARRAYS、同ID改语义 | 确认静态机制；不称同条件重复不稳定 | utils:711–719显式覆盖使GPU可见时NumPy被CPU/GPU Tensor代替，长度仍2。编号检查宜记19 issue（跨profile身份）和14 unknown（未重复实验）。只collect ID列表可能看不见问题，因为ID相同，必须记录参数类型/device |
| checks19：9项状态对账、无skip | 确认当前CPU参考对账；跨profile收窄 | 新noop/gold9个状态完整，无skip/xfail/漏项；这不抵消上述同ID类型漂移。19总体issue，notes明确当前CPU对账成立 |
| checks31/评分控制面：改utils为空assert或新增conftest即可伪过 | 未核当前可达性，保留具体历史风险 | helper确实承载断言，测试恢复清单不含utils有局部日志支持；但是当前candidate投影、完整baseline重建、权限与测试依赖恢复政策未做攻击候选验证，也未读其冻结实现，不能由eval.sh局部清单推出候选可改写后必留到grader。31unknown，不自动添加排除、不运行攻击 |
| proposed_experiments：collect-only比较CUDA IDs；改空断言再empty评分 | 纠正方法与优先级 | 仅ID列表不能检测同名语义变化；携带恶意文件又称empty补丁会混淆候选身份。若后续授权核控制面，须明确candidate patch/projection及实际执行helper来源；本轮不派此任务 |
| proposed_regression_tests：扩到WSI/box_utils；其他函数可能溢出 | 不采纳机械扩大 | 本题gold只改标签选择与列表追加；优先公开3D稀疏API对照足以针对主要疑点，没有已知必要性跑WSI模块 |
| disposition ready_for_probe、costs.minutes=18 | 收窄 | 仍needs_review/static_review，actor未验，不能沿旧静态标签视为已可运行。旧分钟数不是本轮成本，costs=null |

## 对冻结初判的影响

目标/3D漏测/类型精确覆盖判断保持。旧记录提供一个此前未定性的控制面攻击主张；现只增加“历史控制面风险待核”，不当作已证漏洞。初稿已识别CUDA参数漂移；后稿将其明确归入check19跨profile参考身份issue，并保留check14同条件重复稳定性unknown。这只是编号/范围精化，没有新增runtime事实，也未改冻结初稿。

唯一优先下一步仍是任务二在实际actor条件执行公开2D+3D稀疏前景API最小对照并记录类型/device、导入来源、初态和RC；控制面主张独立保留，不以其未核代替本轮最优开发验证，也不删除该问题。
