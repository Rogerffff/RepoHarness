# dask__dask-8597：历史主张对照

2026-09-21。协调者确认 `analysis_before_history.md` 已落盘并记录其 SHA/mtime 后，才提供并读取 `runs/swegym_quality_batch01_20260921_v2/history/dask__dask-8597/refs.json` 中的两份旧记录。前稿保持原字节。下表中的 G/N、B、PUB/PRIV 均沿用前稿第 1、5 节定义；决定性证据是本次重新读取的原件，不以旧记录互相引用作为验证。

旧记录简称：L1 = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/records/dask__dask-8597.json`；P = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/dask_pilot/records/dask__dask-8597.json`。未读取它们引用的其它题、prescan 或 raw hints。

| 旧主张及位置 | 处置 | 本次决定性证据／差异 |
| --- | --- | --- |
| L1 checks.1/2/4/23/27；P 对应段：base、F2P、单行 gold 对应原例 | 确认 | 三份 S2 第47行与本题 bundle 对象一致；patch文本一致；N:775–863 实际在 `take:647` 因除零失败；G:350–363,790,937–944 核补丁生效且通过。日志异常为 RuntimeWarning 而非题面 OverflowError，原因是公开 warnings-as-errors 配置，不是另一故障。 |
| L1 checks.3 / public_view / issues[0]：出错行只在不可见 hints；省略 traceback 是题面问题，应补隐藏调用栈 | 推翻其规格缺失及必要修题判断 | 完整本地复现、NumPy期望与公开调用链已经给出目标和可定位入口（PUB/user_prompt；B/core.py:1832–1847、slicing.py:638–648）；新公开读者在未见私有材料时也独立定位此处。没有证据要求把隐藏栈并入公开题面。P 已正确收窄此点；其“公开难度未证明”的判断确认。 |
| L1/P 对 raw hints 长度、内容和可见性的细节 | 未核实 | 本次未打开 raw hints；只确认实际 public bundle 的 hints 是 harness 操作指令、静态 user_prompt 不包含完整栈。真实消息、bundle读取与CLI附加消息仍待actor捕获，不能沿用 raw hints 长度作为当前输入证明。 |
| L1 checks.24 / P 对应段：“断言只看结果数组”，所有列举替代实现都能过 | 部分确认，收窄未经运行部分 | 未要求指定补丁位置/表达式，合理替代路线存在；但 `assert_eq` 对 Array 还核图、chunks、元信息（B/utils.py:192–340），并非只比数组值。列举路线均未实测，不能写“已能过”。它又未直接断言 Array 类型，空分支返回 NumPy 的潜在漏测是本次补充。 |
| L1 checks.25、P grading_contract/old_claim_reviews：P2P 能拦无条件 `warnsize=maxsize=inf` | 确认这一有限主张 | P2P `test_take_avoids_large_chunks:929–953` 明确检查 True 配置下拆块/图条数，`test_take_uses_config:956–964` 检查阈值配置。不能由此推出条件式禁用默认警告的部分修复也会被拦。 |
| L1 checks.11 / issues[1]：两个相邻测试在 pytest8 恒失败，建议 pytest<7 | 对当前 compat-v1 运行条件已过时 | G:620–645、N:602–627 的实际兼容版本为 **7.4.4**，无需 `<7`；G:898,908 与 N:736,747 两测试确实 PASS。P 对兼容修复与清单未扩充的描述确认。原始 actor 镜像的安装状态未因此获得验证。 |
| P 将上述工具链恢复用于“优先模型 probe”的依据；L1称F2P/P2P正反判别力完整 | 不接受充分性推断；先CPU对照 | 两个恢复的测试仍未入116条P2P，其中 `test_getitem_avoids_large_chunks` 独立保护默认大块警告。B/docs/source/array-slicing.rst:73–95 明示该行为；当前 scoring.py:250–268 仅用参考清单判定。前稿I1给出“仅True计算阈值”的条件式部分修复，可同时检验未计分旧警告与True空轴漏测；其真实奖励尚未知。区别于旧“无条件inf”对照，本次对照并不破坏True分块保护。 |
| L1 checks.6/9；P environment_evidence：安装正常、noop0/gold1、P2P全过 | 确认所引grader范围，actor保持未知 | 两账本第1行与G/N原件哈希一致，1 F2P /116 P2P均有状态；gold全模块rc0。角色为rh2grader/54322、compat-v1本地派生镜像、前缀可写；没有正式agent/54321工具shell消费配方的证据。 |
| L1 checks.7 / P 对应段：不依赖运行期外部资产/服务 | 确认本题最小修复与模块范围 | 已读完整test_slicing.py；NumPy本地构造，pandas只在sanitizer用例可选导入，无本题网络/外部数据；setup.py给出基础依赖。准备阶段仍需匹配依赖及兼容wheel，不能推为actor依赖已齐。 |
| L1 checks.5 / P 对应段：旧十四题内只有本题改slicing.py | 未核实，不据此建立题簇 | 本次没读其它题或prescan。即使文件唯一也不足以证明没有同问题/派生关系；当前记录保留关系未知。 |
| L1 checks.17/29；P 对应段：不追加排除、公开题面无修复代码 | 确认限定范围 | gold投影只含slicing.py；test_patch仅恢复并添加test_slicing.py，源码修复可交付。issue正文无修复代码；实际包带base commit和repo标识，外部答案可达性与镜像资产未审，不能泛化为无泄漏。 |
| L1 checks.26 / proposed_regression_tests；P next_action：另一个零轴组合可作有限诊断 | 确認建议相关性，未当作完成证据 | 旧建议P2P拆块/配置测试确有价值；新分析增加明确配置分支、返回类型和默认警告的双向映射。未写测试/候选，未执行新增实验。 |
| L1 disposition=ready_for_probe；P recommendation=probe_candidate | 旧状态不继承 | 本次 `needs_review/static_review`；先验证I1的具体误收疑点，然后再加actor条件验证。不是由历史标签pass/reject，也不代表题目必须拒绝。 |

本次历史阅读**没有改变独立前稿的事实结论或优先下一步**：原题与gold成立，先做一个有区分力的CPU/RH2部分修复对照。新增的历史信息主要说明“两个测试仍未入P2P”并非此前完全没人注意；本次新增价值在于补全helper/调用者和清单映射，并给出不受旧“无条件inf”保护覆盖的条件式反例。旧日志已由同一compat-v1原件覆盖，无需再次做无关安装维修。

独立 reviewer 结论尚未读取；后续由协调者合并，不回写本稿或独立前稿。审查上下文已额外暴露两份旧答案/调查，不能用于该题独立solver。
