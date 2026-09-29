# dask__dask-7894：旧结论对照

root已明确释放history，本稿在封存初判之后形成。初判SHA256为 `2f2243f0536a7171eb204e71123a5e8a838555b93f8e9be74c69a2bb91ba73e2`，不改写。只读本题history/refs.json指定的两份旧记录，不追其其他链接，不读reviewer，不执行或派发任务二。

## 旧记录身份

以下路径相对 `/Users/roger/Desktop/claude-code-verl-stage0h`：

- L1：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/records/dask__dask-7894.json`，SHA256 `de6c82fd4fbd0b0f8e760330de5f17de22acf2e8805ac364f363613e3db5f053`。
- Pilot：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/dask_pilot/records/dask__dask-7894.json`，SHA256 `63ac5e27701b0d425882afc4db73180e77bdafcfdf06c10649aa5d1fb52ec756`。

均完整读取并核对refs所列SHA。P/Q及原日志简称沿用analysis_before_history.md；本表证据来自封存前已经独立读过的本题原件，而非以旧标签代替判断。

## L1逐项对照

| 旧字段/主张 | 处理 | 决定性证据、适用范围 |
| --- | --- | --- |
| public_view.goal/constraints：drop后depth、boundary重排 | 确认 | P/user_prompt与overlap.py:691–699，公开目标一致 |
| public_view.unknown：标量drop依据不明 | 纠正 | core.py:477–481,659–660明确number/iterable；依据不是coerce_depth |
| public_view.unknown：chunks=(0,)是噪声 | 收窄 | 题面确有此参数，隐藏测试没传；不足以直接删除其复现价值，也不是一般零chunks契约 |
| checks.1：同题同base与patch职责一致 | 确认，限静态身份 | base_identity、Q/test/gold、原candidate与baseline/stage指针；actual actor初态unknown |
| checks.2：base存在目标缺陷 | 确认 | 控制流与原noop日志5个形状失败；不引用未重读的09-10结果 |
| checks.3：实际输入完整pass | 收窄 | 计划题面内容充分属23；实际消息/public_hints交付未捕获，3=unknown |
| checks.4：源码/测试分离支持交付 | 确认，限计划规则与普通候选 | public_hints、test/gold路径；actor写权限未验 |
| checks.17：无需附加排除 | 确认结论、补强依据 | 原恢复checkout/apply/attestation及投影，additional_exclusions=[]；空规则本身不是恢复证据 |
| checks.5：14题唯一修改overlap、无重复 | 未核 | 此次无跨题授权；不沿prescan扩读，不把同文件唯一等同语义无重复 |
| checks.23：数值断言合理，标量可推断 | 确认并纠正依据 | 新七参数；scalar来自map_blocks文档/实现，不是depth的标量支持 |
| checks.24：DeepSeek非gold实现已全过 | 收窄/未核其运行 | 新测试不锁实现；未读候选或其原运行，不继承RESOLVED_FULL主张，不宣称所有替代解都过 |
| checks.25：只排depth一定会失败、判别力最佳 | 纠正 | 新boundary=(0,reflect,nearest)均非none；trim_internal/_trim只区分none。缺口见前稿I1；不作跨题排名 |
| checks.26：建议回归即可pass | 纠正 | 建议不是运行；gold新增回归未证，26=unknown。已核P2P只是局部正证据 |
| checks.27(a)：没处理new_axis即gold不完整 | 收窄 | 这是邻近组合；题面要求drop。未证明具体base通过/gold失败，不能强制扩大任务 |
| checks.27(b)/issues[2]：kwargs.pop修改外部字典 | 纠正 | overlap.py签名接收**kwargs，收集为本次调用的局部字典；pop只删局部键，不删调用者用于展开的原字典 |
| checks.29：无实际答案泄露pass | 收窄 | 计划公开文本不含修复正文，但实际actor可见材料未知；check29=unknown，审查私有暴露另记usage |
| checks.6：旧离线安装成功 | 确认已有09-19条件，未核09-10路径 | 本次授权原pair安装RC均0；不外推当前actor |
| checks.7：无网络/资产问题 | 收窄 | 核心本地小数组，无外部数据需求；没有全文件/actor资产穷举证明 |
| checks.11/issues[0]：无seed导致判分抖动；应连跑20次 | 确认无显式seed，未核抖动、纠正优先级 | 同图随机输入与一次pair不证明重复分数抖动；应先做具体boundary差分，不机械重跑20次。随机稳定性归14而非网络11 |
| checks.9：empty5失败/gold5通过、P2P全过 | 确认09-19原pair | ledger:7–8、精确5+75 ID与原log匹配；代码生效另有candidate/projection/import证据 |
| checks.8：新增两点P2P保护过度修复 | 确认局部作用，未核“包内唯一” | drop_axis2=(2,),drop_axis4=(1,2)的保留轴号不动，不能补boundary none交互；expected语义归18–20 |
| issues[1]：new_axis已知错且不影响判分 | 收窄 | 新测试未覆盖属事实，具体错误未实测；不能笼统断言任意候选new_axis变化不影响旧测试 |
| proposed_regression_tests | 确认相关性，未核新测试结果 | 已读现有multiarray/trim测试；未运行新增回归，不能计为通过 |
| disposition_hint ready_for_probe / 判别力最好 | 纠正 | needs_review/static_review；I1是有公开依据的缺口，actor也未验，不能从旧pair批准资格 |
| costs.minutes=24 | 未核本次成本 | 不迁移为本轮耗时/费用，当前未观察成本为null |

## Pilot逐项对照及对本次初判的影响

| Pilot字段/主张 | 处理 | 本次结论 |
| --- | --- | --- |
| public_contract及scalar依据 | 确认 | 与独立初判一致；raw_hints_visible=false只视作该旧记录声明，实际当前消息仍未知 |
| grading_contract.assertion_assessment / old checks25 refuted | 确认 | 独立初判已定位同一depth-only盲点；无新增运行事实，仍为静态推断 |
| gold_review与kwargs局部字典纠正 | 确认 | 追加明确排除L1错误副作用主张；初判没有把pop列为问题，因此不撤销初判issue |
| old checks26/new_axis范围收窄 | 确认 | 未执行相应组合；保留unknown，不据之拒绝gold |
| old checks24替代实现未重放 | 确认边界 | 无运行证据证明其完整性；数值型oracle仍有非唯一实现空间 |
| environment_evidence noop/gold、RC及摘要 | 确认，限记录条件 | 本次已独立核相同精确账本/日志；“无维修需求”只能说这对pair未受安装阻断，不能代替当前actor资格 |
| old checks3/29 confirmed | 再收窄 | 内容审查归23/usage；实际输入与实际actor泄露分别3/29 unknown |
| cross_task_materials / old checks5 confirmed | 未核 | 未沿跨题链接，保留关系未知，不复制14题唯一性结论 |
| old no-seed issue unresolved | 确认 | 无具体抖动证据，不能直接把随机输入判不合格 |
| recommendation needs_counterexample / next_action | 确认方向，使用本次更具体例 | 前稿I1用确定性arange、boundary=(reflect,none)、drop_axis=0，预测10对6个元素；未执行 |
| quality_certified=false / validation_limits | 确认边界 | 静态证据与原历史运行分离；本轮未读其其他日志来源 |

历史读取不改变独立初判的主要结论和唯一优先下一步；明确补充L1 kwargs副作用主张为错误，并拒绝把L1的ready、跨题排名或Pilot的静态确认迁移为实际actor资格。前稿一句“测试要求不同成员数值相等”应理解为不同参数场景各自与其均值参考比较，不是额外跨成员相等约束；新断言原文与逐参数表为准，前稿保持原SHA不改写。

唯一优先下一步仍是由任务二在独立私有CPU副本对base/gold/depth-only候选运行原overlap选择与I1公开none边界例，核实际数组与chunks，确定是否false acceptance；此处仅建议，未执行、未派发。reviewer未读，分歧状态unknown。当前无训练/评测资格结论。
