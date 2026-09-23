# conan-io__conan-14177

目标：base `b43eb839` 为 `apply_conandata_patches` 新增默认关闭的 verbose，开启时记录每个补丁文件。建议 **needs_review / static_review，先修订题面—验收契约**；原版不作为通用求解探针。

| 公开要求/旧行为 | 测试或gold | 判断 |
| --- | --- | --- |
| verbose=False；True时逐文件输出 | 13个参考均不传verbose；gold不改签名 | 接口未测、gold未交付 |
| 默认不新增日志 | 两个multiple F2P默认调用却要求新文件日志 | 冲突 |
| 保留直接patch()日志 | single_patch_description强制新增(file) | 无公开依据的范围扩大 |
| 路径/参数/显式元数据/错误 | 10 P2P保护底层patch() | 部分回归有保护 |

原始RH2：noop的3个失败均是新增文案断言，gold 13/13通过、命令退出0；安装成功，无参考缺席/跳过。这证明当前验收可执行，不能证明题面完成。新增检查使用Mock，不应用真实补丁；第二个带description的文件名也没被断言，gold不会补出该名称。

八方面已查：当前公开规格；base/S2/补丁一致；3 F2P及10 P2P全部展开；符合题面但被拒的替代路线；gold/调用者回归；导入、资产、权限、网络、编译与交付需求；官方恢复/源码投影；具体跨题关系。未查：真实actor/消息/镜像资产、patch-ng内部、其它全仓回归及当前控制面利用性。

15422的公开base已含本题gold关键日志行为，属具体参考行为暴露线索，非同需求重复。历史对照维持契约冲突，纠正“把==放宽成in即可修好”；旧记录也未实跑替代解。

唯一下一步：CPU对照题面实现与gold，检验默认/False/True下真实文件改动和日志，再比较官方评分；据结果形成独立修订版本。独立reviewer同意契约校准处置，跨题关系仅第二阶段核验；见[review.md](review.md)。详见[历史前分析](analysis_before_history.md)及[对照增量](old_findings_delta.md)。主审已见隐藏测试/gold/旧调查，不得充当本题独立solver。
