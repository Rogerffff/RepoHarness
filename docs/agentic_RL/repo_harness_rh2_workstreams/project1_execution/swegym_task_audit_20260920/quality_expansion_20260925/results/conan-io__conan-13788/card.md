# conan-io__conan-13788

静态建议：**needs_review / static_review；仅 development_diagnostic**。base `c1b3978914dd09e4c07fc8d1e688d5636fda6e79`（Conan1.60开发版）。公开问题未给复现；旧代码允许不同context/消费者的同名版本，不能因用户疑问改成全局禁止。

| 需求/旧行为 | 断言与结论 |
| --- | --- |
| host构建依赖与profile build工具重放正确 | F2P True要求两次install都含tool4.0；原noop只在重放后失败，gold通过 |
| 普通host依赖、双context/不同ID、build-order、依赖保留/缺失错误 | 9个P2P逐项已读且原运行均通过 |
| 完整锁边、build tool3.0保留 | 新测试只查tool4.0输出，缺直接context/边断言 |
| build工具的普通依赖继承build | gold对Requirement.build_require_context=None统一查host；与graph_builder继承node.context的路径冲突，是未运行的具体回归疑点 |

完整八方面与证据见[初判](analysis_before_history.md)：目标/版本已核；全部1F2P+9P2P及决定性fixture/helper已读；联合键/按context筛选等非gold结构不受显式限制但未执行；gold所有改动和普通依赖调用者已追踪；本地Python/cache即可构造公开验证，当前actor条件unknown；历史候选投影、可信恢复、逐ID状态已核；未证明无跨集重复、实际泄漏、控制面攻击或偏差。

原RH2 `baseline01/workers/w01-2/ledger.jsonl:15,16`同命令收集10：noop 1失败9通过、RC1；gold 10通过、RC0；两次安装末命令RC0，无skip/xfail。actual image ID=null；历史grader成功不能替代当前actor开发资格或证明gold完整。

历史“题面方向必然反向”“9P2P足以保回归”“gold正确”均收窄；未核旧hints原件。历史后确认本题可选conftest_user/tools_locations入口，纠正复制的2.x default_profiles说法；当前交付利用未证，不新增排除。主审出稿时未读reviewer；独立交叉复核现已完成。

**唯一优先下一步：任务二私下使用公开CLI，以root→build工具T→普通依赖D的两profile锁重放做同条件base/gold对照，检查边context/错误位置。** 这能改变check26/27；本轮没有执行或派发。前稿SHA `508a697338f38cdde6e9b6cc111654d60d4f72a64be8e6e0312707a0aee81c95`未改，逐项历史处置见[差异](old_findings_delta.md)。


协调裁定：quality_first，ready_for_probe=false。26/27维持unknown：普通Requirement.build_require_context与继承的Node.context不同，现有静态路径尚无实际CLI复现。唯一私有CPU提案采用lock create生成待构建锁，再install --build；若改用install生成已有prev的完整锁，不应无条件强制重建而混入另一限制。主审不可变delta中的Requirement.context简称由review明确纠正，原稿保留。
