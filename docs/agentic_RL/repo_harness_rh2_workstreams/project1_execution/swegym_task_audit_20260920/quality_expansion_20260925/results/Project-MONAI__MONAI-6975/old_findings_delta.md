# Project-MONAI__MONAI-6975 — old findings delta

root 明确 release 后，只读取 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_monai_1/records/Project-MONAI__MONAI-6975.json`；SHA256=`d6d1b51eaa8aeb8374dec26cb387d0ab5ced14da8ece5e02e2207fff899dd473`，与本题history refs一致。没有跟随旧链接查看DeepSeek轨迹/candidate、stage1、dupidx、其他题或reviewer。前稿SHA=`1d6e7118309e10b3dd37cdfceba652080a4a3313619241b2af1398a42a5fd7a8`，保持不变。

| 旧主张（原编号） | 结论 | 决定性证据/限制 |
|---|---|---|
| 1/2/27：base默认False覆盖Dataset实例True，gold改None | 确认核心，完整性收窄 | 前稿独立读Dataset→helper→Compose全链，gold两个hunk全读；授权09-19真实RH2四个目标fail→pass。全局helper回归仍未证完备 |
| 3：题面重复 | 确认材料事实，归23说明 | 当前计划prompt也重复相同复现；内容未互相矛盾。不据此断言actual actor输入缺失或不可解，3=unknown |
| 3：git不跟踪nii.gz，所以离线容器跑不起来 | 推翻该推断，资产状态未核 | Git导出不包含文件不能证明镜像忽略/预置资产不存在；实际actor资产位置/可读性unknown。原题文件可能需要获取的旧数据配置链接未另读，不能声称已验证FileNotFoundError |
| 4/17：两测试文件成对恢复无缺口 | 确认历史局部 | 本轮授权RH2两文件checkout/apply RC0，gold不碰tests；未审计任意候选/其他helper恢复完整性 |
| 5：26题路径唯一，因此无重复派生 | 未核；逻辑亦不足以证全局无重叠 | 未读dupidx或别题；路径唯一不是无语义重复/留出重叠的充分证据。5=unknown |
| 23：题面只字未提日志，F2P精确日志要求无公开依据 | 部分纠正 | 原题明确log_stats=True；公开base已有精确日志测试。完整文案非题面规格，仍有潜在过约束；但不是完全无公开观测依据。旧引的lazy=False字符串属于新增P2P反向对照，四个F2P期望True累积 |
| 24：DeepSeek改Dataset调用点也获满分 | 历史主张未独立复验；与静态合理非gold一致 | 仅旧record自述，release未授权其candidate.diff/运行。保持“存在合理局部修法”的静态判断，不能报本轮核实真实模型满分 |
| 25：Dataset局部修复满分属于P1 partial_fix，应强制修全Dataset类型 | 收窄并纠正规格扩张 | 原题只说明普通Dataset；局部显式lazy=None满足该范围，不能仅因与gold全局默认变更不同就判不完整。其他caller是回归/可扩展性风险，不应据gold反推强制要求。前稿已有更直接漏测：目标测试丢弃返回数据，坏实现可产生日志却返回原输入 |
| 25/回归建议：dataset.py:1279/1432是CacheDataset/PersistentDataset | 纠正明确源码定位错误 | release后新增静态AST定位及源码1250–1285、1405–1445阅读：1279属于ZipDataset._transform，1432属于NPZDictItemDataset._transform。没有执行项目。不能用这些行证明Cache/Persistent相同行为 |
| 26：缺其他Dataset测试就是gold回归issue | 纠正编号和证据等级 | 缺覆盖归25；未有gold引入错误的反例，26=unknown。公共helper对直接Flip(lazy=True)的返回pending变化只是待辨契约风险 |
| 26：59 P2P对Compose保护非常充分 | 收窄 | 前稿全语义读发现flags分支assertTrue(expected,actual)并非相等；部分空管线loop无断言；其他direct日志不等于Dataset返回数据正确。状态数量不能代替强度 |
| 29：无泄露 | 收窄 | 计划题面不含修复不等于actual actor本地材料无答案；29=unknown，审查者gold/test/history暴露单列usage |
| 6/7/11/20：评分离线可运行、分差仅目标 | 确认09-19授权条件 | 63状态与expected逐项匹配，noop四目标fail、gold全pass，install RC0、deny_all。核心F2P内存合成数据；旧shape测试仍读写临时NIfTI，所以“不读磁盘”只限F2P。不升级actor资格 |
| 10：无多进程/shm需求 | 限定并纠正 | 最小F2P没有显式worker需求；完整所选test_compose.py:201–244含DataLoader workers=1/2，不能称整套无多进程。shm必要量未核；旧logger干扰风险无本次失败证据 |
| 18：空测试恒pass，不影响判分 | 确认弱测试，归25 | test_dataset_lazy_on_call无Dataset/断言；历史确实收集执行完成，因此不是18“没跑完”的证据。它不贡献目标判别力，不能当安全覆盖 |
| ready_for_probe、真实模型RESOLVED_FULL、25分钟 | 不继承资格/成本 | 未读模型原轨迹；actor条件unknown。保持needs_review/static_review、成本未观测null |

唯一新增源码阅读是本题dataset.py两个范围及stdlib AST类定位，其他旧链接均未追随。旧结论促成的变化仅是新增明确定位纠正与历史主张分级；前稿“日志覆盖有限、公共helper变更需关注、Dataset局部修法合理”不变。

唯一优先下一步保持：任务二用真实actor上的内存字典Flipd direct/Dataset True/False/None小矩阵，同时看实际返回图像与lazy执行证据，保存初态和源码导入。它针对真实用户API漏测及actor未知，不要求扩成所有Dataset类别的新私有标准。题面去重可作为后续材料编辑建议，本轮未修订题目，revision_refs=[]。
