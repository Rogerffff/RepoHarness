# Conan 13721 静态短卡

基线0efbe7e49fdf的Jinja profile缺profile_name。目标是让不同命名入口/软链接共用生成器。gold每次从未解引用路径取basename放入局部context，方向合理。

| 需求 | 测试/证据 | 结论 |
|---|---|---|
| 名称可用于模板 | 唯一F2P含五次install | 普通路径/cache/覆盖行为可测 |
| 扩展名是否保留 | 隐藏要求foo.profile；题面旧宏传stem | 两种解释有依据，规格仍不唯一 |
| symlink入口名及with-context宏 | 五例未覆盖 | realpath误实现可能漏过 |

八方面已查需求/歧义、base/工件、五新增assert/helper和六P2P、stem/realpath等路线、loader递归及API调用者、Jinja/临时cache/软链接开发需求、恢复投影、用途暴露。实际actor初态/消息/权限、跨池关系与完整安全控制面未核。

baseline01/w01-1第15/16行：安装rc0，noop1失败6通过、gold7通过。noop只到首个foobar断言，不能称五条都失败。六P2P中test_profile_template两assert是非空常量；其他五项有效。新增substring也未严格限制名称结尾。均属覆盖边界，不是已证gold回归。

协调者纠正主审历史归纳：旧pilot也保留后缀留白，并未完全否定争议；basename合理，但新增变量格式未唯一规定。处置needs_review/static_review，仅development_diagnostic。唯一优先下一步是由任务二在真实actor使用无后缀双软链接验证公开CLI/with-context入口区分；后缀表示另记未定，不阻断此流程。check29实际actor泄漏unknown，私有暴露放usage。独立reviewer已完成，协调者已读并收口；完整映射/旧结论对照见两份分析。

协调收口：确认核心软链接漏测；协调者采纳reviewer两项纠正：旧pilot保留后缀留白，无后缀双软链接可先验证公开开发路径，无需先裁决带后缀规范。 check40 unknown，阶段合规不能证明无筛查偏差；actual actor仍未验，未执行/派发任务二。复核与前后版本记录见review.md及../../coordinator_revisions/pack02_conan/revision_log.json。
