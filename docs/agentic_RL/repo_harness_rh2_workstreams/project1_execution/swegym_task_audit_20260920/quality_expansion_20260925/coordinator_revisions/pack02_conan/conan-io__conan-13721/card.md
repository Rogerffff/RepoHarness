# Conan 13721 静态短卡

基线0efbe7e49fdf的Jinja profile缺profile_name。目标是让不同命名入口/软链接共用生成器。gold每次从未解引用路径取basename放入局部context，方向合理。

| 需求 | 测试/证据 | 结论 |
|---|---|---|
| 名称可用于模板 | 唯一F2P含五次install | 普通路径/cache/覆盖行为可测 |
| 扩展名是否保留 | 隐藏要求foo.profile；题面旧宏传stem | 两种解释有依据，规格仍不唯一 |
| symlink入口名及with-context宏 | 五例未覆盖 | realpath误实现可能漏过 |

八方面已查需求/歧义、base/工件、五新增assert/helper和六P2P、stem/realpath等路线、loader递归及API调用者、Jinja/临时cache/软链接开发需求、恢复投影、用途暴露。实际actor初态/消息/权限、跨池关系与完整安全控制面未核。

baseline01/w01-1第15/16行：安装rc0，noop1失败6通过、gold7通过。noop只到首个foobar断言，不能称五条都失败。六P2P中test_profile_template两assert是非空常量；其他五项有效。新增substring也未严格限制名称结尾。均属覆盖边界，不是已证gold回归。

与旧pilot保留分歧：basename含后缀合理，不能据旧文件查找参数唯一规定新模板变量格式。处置needs_review/static_review，仅development_diagnostic。唯一优先下一步先明确公开后缀/入口名称约定；不为该歧义先安排CPU。check29实际actor泄漏unknown，私有暴露放usage。reviewer待完成，未读输出；完整映射/旧结论对照见两份分析。
