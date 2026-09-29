# Conan 11594 静态短卡

Ninja Multi-Config 的`CMake.test()`应默认使用`test`并保留`--config Release`。基线4ed1bee0fb81，gold只改新helper目标选择，静态修复方向合理。

| 需求 | 测试/证据 | 结论 |
|---|---|---|
| Ninja Multi-Config默认test | 新增参数case，noop失败/gold通过 | 直接覆盖命令 |
| NMake/Unix/Visual/Xcode旧目标 | 四P2P均过 | 旧行为有限覆盖 |
| 保留配置、target/skip、真实测试 | 无相关新增断言 | 不能由满分推断 |

八方面已查：公开需求与新旧helper范围、精确base/工件身份、全部六case/helper及四P2P、替代条件和全局错误多配置修法、gold/调用者、依赖/临时preset/开发工具、投影与测试恢复、用途/暴露。实际actor初态/消息/权限与跨池关系仍unknown；未审计全部评分安全实现。

reference_v1原账本各行1：安装rc0，noop1失败5通过、gold6通过；F2P短`[Ninja`绑定两完整node均过，parser五键不表示少跑。旧碰撞/新文件恢复风险不能再当本配方未修；不外推到当前actor。Mock不运行CMake，测试还固定POSIX引号格式。旧helper同问题及人工None状态保留范围疑义，不升格成已证gold回归。

处置needs_review/static_review，仅development_diagnostic。check29实际actor泄漏unknown；私有审查已见gold/隐藏测试/两旧记录。唯一优先下一步：获准进入任务二后，以实际actor跑临时Ninja Multi-Config公开用户流程，观察配置保留和测试真正执行。reviewer待完成，未读其输出。完整证据见analysis_before_history.md和old_findings_delta.md。
