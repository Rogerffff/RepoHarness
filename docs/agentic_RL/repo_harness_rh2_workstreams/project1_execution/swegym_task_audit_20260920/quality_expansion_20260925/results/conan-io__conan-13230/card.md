# Conan 13230 静态短卡

Macos build→非Apple host生成Autotools参数时，不应注入Apple arch/sysroot或查询无关SDK。基线c2001bad8aa8，普通flags原本就读host；标题“compiler选错”不是另一未修需求。

| 需求 | 测试/证据 | 结论 |
|---|---|---|
| 非Apple host不进入Apple分支 | Android唯一F2P，三属性断言 | 代理根因，min_version原本为空 |
| Apple SDK/arch等旧行为 | 全34P2P及helper已读、均过 | 有效但非全平台覆盖 |
| 题面Linux/最终flags/脚本 | 官方无直接断言 | Android-only错误修复可能漏过 |

八方面已查公开最小复现、base/工件、全部新增断言及34P2P、替代实现/None表示、gold/共享flag出口、开发依赖与profile资产、恢复/投影、用途和暴露。当前actor初态/消息/权限、跨池关系及恶意候选控制面仍unknown。

baseline01/w01-1第13/14行：安装rc0；noop1失败34通过，gold35通过。noop在构造时xcrun127，尚未到属性断言；gold避开错误分支。不能据xcrun缺失要求先装Apple SDK，也不能把它说成原Macos污染路径已实测。strict None存在表示约束，但有旧属性测试依据；无已证gold回归。

处置needs_review/static_review，仅development_diagnostic，actual actor泄漏check29未知；审查暴露独立记usage。唯一优先下一步：实际actor按题面显式Macos/Linux profiles执行生成流程，核cflags异常内容不再污染，并保留故意raise的非零退出解释；不需真实交叉编译器/openssl。独立reviewer已完成，协调者已读并收口。详情见两份分析。

协调收口：Android内部属性不能代替题面Linux最终flags；xcrun127由错误分支触发，不默认要求安装SDK。题面故意raise须按payload与位置解释。 check40 unknown，阶段合规不能证明无筛查偏差；actual actor仍未验，未执行/派发任务二。复核与前后版本记录见review.md及../../coordinator_revisions/pack02_conan/revision_log.json。
