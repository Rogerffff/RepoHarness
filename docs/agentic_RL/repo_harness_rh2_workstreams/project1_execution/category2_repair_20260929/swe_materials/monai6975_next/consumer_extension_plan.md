# 6975 两文件消费的最窄扩展边界

2026-09-30。这里只记录接缝和未来检查，不修改生产。当前冻结D6的 `SWETestPatchFile.path` 没有本题两个文件，P2P类型/registry `test_files` 为max_length=1，节点literal没有本题，bundle校验又要求完整有效patch路径恰等于登记文件集合。本题原patch已有两文件，不能只登记新增方法所在Dataset。后续以root指定的唯一consumer基线开隔离实现；当前优先Moto5406，材料任务不抢先热改基线。

建议保留 `replace_test_patch_append_p2p` 的奖励语义，给6975唯一instance/repo/revision/节点与恰好两个文件的受信配对。可以选专属revision子类型或等价的封闭题级schema；不可把全局max_length或任意路径放开后仅依赖普通字符串。revision候选 `monai6975-dataset-dict-pixels-cpu-v1`，独立受信registry/producer pins由后续root封板。本包manifest不是注册表或生产pin。

两文件immutable base身份必须逐件核，SHA为：

| 原文件 | base SHA256 |
| --- | --- |
| tests/test_compose.py | ef004f2fa3fb371cfcbadf31bfaa30efb43fa3321e3f77065e54734d1f0d1901 |
| tests/test_dataset.py | 7a54e57faf059bca0767e9ebefd9c5dddfac518c6a78d223c860f1fc9c981d29 |

未来材料/类型/consumer检查须覆盖以下并列条件：

- 原instance/repo/base/public/parent grading digest及原test_patch/SHA固定；还原原patch+原两类参考后必须得到原parent digest。两份base文件都须是普通文件，无symlink或错SHA；错题/错revision/错schema类型均拒绝。
- 完整effective patch的a/b安全路径一致，其完整路径集合必须恰为两登记文件，缺Compose、缺Dataset、多文件、源测试路径错配都拒绝。extra patch仅增Dataset方法；不能借完整替换删除原Compose hunk、已有参数、日志断言或旧测试。
- 本包已证明base+原patch+extra与base+effective两文件同字节；Compose原patch后字节保持，Dataset去唯一新增方法后原AST/原字节保持。未来生产测试仍钉这些事实，不能只比较参考计数或diff文件名。
- 原4F2P及原59P2P的具体键和顺序保持；只追加本普通node到P2P，禁止交集/重复/重新排序/错误放F2P或空新增。正式分区为original_f2p、original_p2p、added_p2p，并须从P2P桶读取新增结果。
- 共用builder必须在候选之前从两份immutable base恢复、应用完整effective patch，两个文件均进入hygiene并root所有不可写。候选篡改两任一文件/symlink须被恢复；wrong base/effective SHA在候选前拒绝。安装/测试仍正式vendor，actor/replay同spec/context/材料，不用私有shell或wrapper评分。
- 新grading/environment/material identity绑定两文件和新增参考，public原题面不变。旧prepared、旧qualification、旧host grading、任意替换路径或错registry pin必须拒绝。未注册的本包不能借旧0/1/1记录获得成功资格。
- 旧已验题的材料、script/context序列化/公开登记/安装字节保持；新producer精确只改6975相应行，其他行及旧pins不变。新路径不得覆盖旧producer/历史证据；完整代码inventory和producer/registry最终SHA由root核定。

至少需检查的消费者为 envpack/bundles_v2.py 的封闭配对与parent还原、swe_material_revisions.py 的注册/baseline/新producer，prepared_task_face.py 的共用builder及两文件恢复/保护，grading/material_revision.py 的现有P2Pcontext兼容和正确分区；prepared/TrustedTaskController selector须天然加载新producer。可以复用现有机制，但必须先确认两文件能力，不能将一个文件的基线校验当两文件证明。公共parser、reward规则、权限、完整baseline和原artifact导出语义不在扩展范围。

未来正式CPU需实际收集64节点及逐参考无缺席/skip，读完整安装/测试RC、policy+真实像素失败原因、实际transform.py和两测试SHA、保护/ledger、manager与独立标签两层清理。noop/gold/discard应0/1/0。之后真实CC仅公开开发、原工件fresh grader完整baseline直评由root另授权执行。本材料未实现这些consumer，也未运行新node。
