# Project-MONAI__MONAI-5932 — old findings delta

root 明确 release 后读取唯一授权旧记录 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_monai_2/records/Project-MONAI__MONAI-5932.json`，文件 SHA256 与 history/本题/refs.json 相符：`574f987d1cb269131ee8c08edeaf2286e8b7ee8485cdab8da870b7914f20fed1`。没有沿其链接读取 scan、stage1、其他题、候选或 reviewer。前稿 SHA=`d7f8a40c8d393862caf53db241014096593f83102ed373a0bb82a0061975c40f`，未改写。

| 旧主张（原编号） | 结论 | 决定性证据和本次范围 |
|---|---|---|
| 1/2：base、题面、gold 相符，初态含子串替换 bug | 确认，限定版本 | 前稿独立源码分析；授权09-19 ledger第3/4行与日志直接显示目标SyntaxError→pass；不借旧stage1作当前执行证据 |
| 3：输入完整、hints为空，因此 pass | 收窄并纠正编号 | 公开计划 prompt 有完整复现，属23正证据。当前public_bundle带public_hints；旧raw hints字段不等于当前交付。actual actor消息/工具呈现未捕获，3=unknown |
| 4/17：测试/源码分离，恢复单文件 | 确认局部 | 当前gold仅resolver，test.patch仅test_config_parser；授权RH2恢复/应用RC0。不是任意候选或当前actor权限保证 |
| 5：与 MONAI-6756 跨题顺序依赖，必须同侧 | 未核实 | 仅在授权旧记录中见主张；本轮未被授权读取那题原件/跨题scan，不把旧标签转成已证重复或强制划分结论。保留待协调者独立核验 |
| 23：唯一F2P是公开示例同构数值式 | 确认 | A/A_B=1/2、断言4；无新API或gold形状约束 |
| 24：多种算法都能通过 | 收窄 | 无直接唯一实现断言；一次完整匹配callback是合理非gold。未运行替代，不能由静态推导声称所有所列方案实际通过；正则“词边界”本身需处理#合法路径 |
| 25：反转出现顺序可过单例，多前缀未覆 | 确认具体漏测，收窄建议 | 反转会在长ID先出现的合法式失败，测试只含短在前。整串@引用本身只有一完整token，且旧相对/对象引用P2P已覆盖，不能说非表达式分支完全无覆盖，也不能机械加无关验收 |
| 26：14 P2P充分保护，pass | 收窄 | 已读全部14项，确有旧行为覆盖且历史均pass；不能证明无gold新回归。26=unknown；覆盖组合不足归25 |
| 27：gold最小正确完整 | 局部确认、完整性未证 | 长度降序对已定义ID前缀有效，H验证核心；允许缺失+前缀的旧风险仍在，不是已证新回归 |
| 29：题面无修复代码，故无泄露 | 收窄 | 计划题面合法堆栈不等于actor本地全部可见材料安全；29=unknown。审查者私有暴露单列usage |
| 6/7/11：离线安装可用、无外部资产/网络 | 限定确认 | 09-19原日志最后安装RC0、deny_all下所选测试完成。核心是内存字典，宏用临时文件；当前actor依赖和准备供应路径unknown。不能把“无DOWNLOAD命中”作所有阶段不需网络证明 |
| 13：无多进程、无shm需求；慢因TEST_CASE_1的torch.rand | 纠正 | tests/test_config_parser.py:32–43的TimedCall，tests/utils.py:535–624明确torch.multiprocessing spawn、Queue/Process；需子进程能力，具体shm需求未核。torch.rand在test_non_str_target，不在TEST_CASE_1。旧跨题速度排名不复用 |
| 19：torchvision skip会造成P2P缺席/误判 | 守卫确认，parser链未核 | skipUnless(has_tv)原件已读；09-19日志该项实际PASSED且reference_missing/skipped为空。旧parser/scoring链接不在release范围，条件性误归因机制未独立确认，不把它说成当前失败 |
| 31：TimedCall未恢复但仅影响skip/超时、无正收益；可新建conftest | 只确认局部，安全结论未核 | 恢复清单确实只有目标测试；TimedCall执行被包装函数并传播异常，功能不限skip/超时。候选投影规则/可信控制面完整性未审计，不能断言攻击可达或无正收益；不擅加路径规则 |
| ready_for_probe、16分钟 | 不继承资格或成本 | 本轮仅static_review/needs_review；当前actor未知，费用/token未观测null。旧耗时仅旧记录自述 |

初判没有因旧标签改变核心题意/测试判断；新增收口事项为：外题关系与skip/parser主张单列未核，纠正旧资源与helper功能说明。旧建议的全端到端bundle测试、屏蔽torchvision实验不自动执行，也不列为本题最高优先项。

唯一优先下一步保持前稿：由任务二在真实actor入口保存初态、解释器/源码导入及公开ConfigParser复现和窄旧测试结果，区分目标失败、skip及环境问题。前稿和后稿都没有本轮运行新项目命令；不读reviewer，不把history给solver。
