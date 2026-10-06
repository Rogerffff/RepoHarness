# python__mypy-11236

**保留为受限静态候选；needs_review · static_review · development_diagnostic**。mypy 0.920，base `209a7193feb4bbfa38d09232b0a5a916e9d2e605`。公开目标是接受显式 `Union[Tuple[str],Tuple[Literal[1]]]` 返回类型下的 `("a",)` 和 `(1,)`。Gold 两行让带已知字面值的 Instance 复用原 Literal 子类型比较，静态符合目标。

| 需求/行为 | 断言与实际范围 |
|---|---|
| 合法 Literal 元组返回 | 唯一 F2P 用布尔标签双元素 Union 的两个正确分支、Final(1,) 和显式 Literal 元组覆盖；原题单元素 Union/CLI flags 未原样执行。 |
| 值、类型和 Union 分支保持 | F2P 六条反例拒绝 Final(2,)、Final(True,)、交叉标签及未知 bool；另有1条声明类型 note。并非“1个ID只测1件事”。 |
| 旧 Final 调用行为 | 官方 patch 改 `testLiteralFinalGoesOnlyOneLevelDown` 的两次调用及输出；其 header 不在 patch hunk，未被选择，也不在冻结参考。 |
| 长度及共享调用者回归 | 已读 tuple 长度、Final/普通变量、直接 Literal/tuple 上下文和实参路径；均未执行，P2P=[]。 |

原 install_wave1 派生 grader 的 noop/gold 均完成安装和1项测试，结果0/1，失败确为正确返回被多报错误。初态共同的 `types-typing-extensions==3.7.3` pin 已保留。此证据属于 UID54322 派生 grader；正式 UID54321/public image 的开发条件未验。

八方面均已展开：需求与源码因果、材料/初态、逐条断言、替代及部分实现、gold/回归、开发条件、投影/恢复/评分、泄漏/用途。恢复仅 `check-literal.test`，`test_globs=()`，额外排除=[]；冻结奖励与执行选集分开记录。真实 actor 消息、缓存/网络泄漏、控制面反例、重复稳定性和模型能力未知。

旧“任意放宽 Literal 仍满分”被现有六条反例推翻；“唯一实现”与“gold 已知不安全”也无充分证据。保留两个未运行假设：漏长度检查的 tuple 局部实现可能通过 F2P 却接受 `(1,999)`；正确上下文替代解可能因 got 显示 Literal 而误拒。覆盖缺口不自动升级为坏题。

**唯一优先下一步（未执行）：**在固定派生grader做原题base/gold及 `(2,)`、`(1,999)` 负例对照，保留Python3.7目标与原flags并记录算法模块来源。独立[复核](review.md)已完成：认可既有正负约束，未证明唯一gold或实际误拒；zip-only候选不是准入必测。正式actor另作模型开发启用条件；按具体结果再选旧case或完整替代诊断，不改原oracle，成本未知/null。

证据入口：[封存分析](analysis_before_history.md)（SHA256 `2569d428660d3d94807b468a66f62d52733cabed9cc7b8ac71b6690efd8cc310`）、[历史逐项对照](old_findings_delta.md)、[完整40项记录](screening_record.json)。原件：`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-11236/{gold,noop}/ledger.jsonl:1`；Glog:560–579、Nlog:546–595（精确文件名见分析）；Raw SWE-Gym:201 的14157字符 hints 仅在封存后暴露，不提供给 solver。
