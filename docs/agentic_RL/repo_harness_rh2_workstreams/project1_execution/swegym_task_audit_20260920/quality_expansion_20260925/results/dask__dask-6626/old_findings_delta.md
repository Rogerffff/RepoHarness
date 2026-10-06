# dask__dask-6626 指定history解封后的差异记录

2026-09-25，by=e25_main_dask。协调者已明确release且核验三题全部初判；本题前稿SHA256=`521b13b61b153d74919eb17113f90bab473398d10fbfc782f9c0413ad338ca99`保持不变。先独立核SHA再全文读取以下sources，未沿链接扩读原旧运行、其它任务、汇总或未来版本，未读reviewer。文件完整性校验不是旧主张正确性保证。

- `/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/records/dask__dask-6626.json`；SHA256 `469df00e11632d09f6d7adec272283a80cbf99eecc64b86901936f11f21687b0`，匹配。

路径约定与原始证据：PUBLIC=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/dask__dask-6626`；PRIVATE=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/dask__dask-6626`；本题[封存初判](analysis_before_history.md)§6已列精确原ledger行、log路径/hash、配方与逐测试状态。下文“旧记录记述”只代表上述历史文档的主张；“确认”需有本题公开原件或本次已核原运行支持。全部为静态阅读，无新项目运行、模型或环境实验。

## 旧主张逐项处理

| 旧记录位置/主张 | 处理 | 本次决定性证据及限定 |
|---|---|---|
| public_view、checks.1/2：类别元数据错误、base/test/gold同题 | 确认 | PUBLIC题面、base utils.py:543–559，PRIVATE三种补丁一致性和原noop目标失败；版本身份见初判§1/6。不是actor初态证明 |
| checks.3：raw hints有定位线索，据此判输入issue | 未核实并纠正适用面 | 本次不获准扩读raw hints原件；已读public_bundle.public_hints为通用操作提示，planned user_prompt有完整题面。旧记录对raw字段的记述不能证明actual actor看到了它；check3=unknown |
| checks.4/17：纯源码与测试分离，additional_exclusions为空 | 确认有限范围 | gold仅utils.py；测试只test_utils_dataframe.py；引用RH2恢复目标单文件且投影保留源码。空exclusions不是一般可信恢复证明 |
| checks.5：旧包唯一相关文件 | 未核实 | 涉及旧包prescan，未获准扩读。文件共用与任务派生/评测重叠也不是同一判断；不移植全池去重pass |
| checks.23/25、issues[0]：缺set_index用户路径断言 | 确认并重归类 | test.patch只meta_nonempty；题面from_pandas/set_index/compute均未被新增断言执行。这是check25集成覆盖缺口；不能直接说规格矛盾或gold错误 |
| checks.24、issues[2]：强制修复位置、任何调用侧等效修复都不得分 | 收窄 | helper行为确被检查，但非物理文件或代码结构强制；公共旧dtype断言和categoricals/design文档支持此不变量。未执行具体替代解，不能以“任何”外推所有合法实现被误拒 |
| checks.24：空categories的O/f8/M8[ns] P2P能防写死object类型 | 确认有限判别力 | test_meta_nonempty_empty_categories:172–190直接检查类别索引类型/ordered/name；但不查类别长度/值，CategoricalIndex分支原缺口仍存在 |
| checks.25：新增判据只有len一行 | 修正 | 新fixture K也扩展原有 `(df3.dtypes==df2.dtypes).all()`；本次noop日志487–490在K dtype处先失败。新增显式assert一行不等于新增约束只有一行 |
| checks.26：列出proposed_regression_tests即可pass | 不接受证明强度 | 建议用例不等于已执行回归；本次check26 unknown，无已证gold新增回归。Index残余路径是旧问题/覆盖缺口 |
| checks.27：gold精准且保存类别dtype | 确认默认目标，保留边界 | cats显式为原空categories切片，gold历史目标通过；不能据一行小补丁证明所有类别索引/用户集成行为完备 |
| checks.29：无题面补丁则无泄漏 | 修正到unknown | 公开题面本身未含gold补丁可确认；actual actor目录/消息未捕获，所以check29不能pass。审查授权私有暴露放usage |
| checks.6/8、issues[1]：pytest8使sparse用例恒失败 | 对所引旧条件仅为旧记录记述；当前引用条件已过时 | 本次原compat_v1 recipe离线pin pytest7.4.4；noop与gold日志均PASSED test_nonempty_series_sparse（532/521行），整文件分别1失败15通过、16通过。因此不能继续把当前引用条件写成恒失败 |
| issues[1]建议pytest<7 | 已被更精确现有配方取代 | 所引原recipe与实际日志证明pytest7.4.4可使该用例通过，不需要据旧建议再次降低版本。本次不执行安装，也不推广到别题 |
| checks.7/11：本地fixture、无skip即环境/网络通过 | 部分确认并重归类 | 新fixture本地生成、expected无缺席/skip有本次原日志支持；只能证明该grader执行，不能证明actor资产权限或解题期网络 |
| checks.9：empty/gold可区分 | 确认到本次精确原运行 | compat_v1 noop F2P0/1、gold1/1，两侧P2P14全通过；不是旧stage1原日志独立复核 |
| proposed_regression_tests：sparse纳入P2P、set_index相关用例 | 保留建议性质 | sparse现在执行成功但仍不在expected14，实际选择文件比reference广；改变reference需独立决定，本文不改。set_index建议须先验证精确公开测试ID，旧拼接ID不是已核存在的测试 |
| disposition_hint：“补一条即可进探针” | 收窄 | 仍需actual actor公开开发路径/初态与消息证据；静态结论仅needs_review/development_diagnostic，不自动ready_for_probe |
| costs.minutes=22 | 不沿用 | 是旧审查者记录，不是本轮成本；当前token/费用/运行耗时无工具观测填null |

## 对已封存初判的影响

核心初判不变：用户集成覆盖不足，gold修复Series元数据有支持，actual actor未验。历史材料新增了旧pytest8故障的时间背景；本次初判已经引用兼容修复后的原运行，因此这是旧主张过时，不是本轮重新修复。独立初判关于runner digest变化的unknown继续保留：compat安装改pytest与变化相符，但没有runner字节差异证据，不能写成全部合法变化已证明。

不采用旧结论中“强制位置”与“缺新增断言就是规格问题”的绝对表述。不删除原件，不更改测试、gold、配方或前稿。唯一优先下一步仍为任务二的实际actor题面双路径验证，保存导入/初态/身份/RC；本文不执行或派发。
