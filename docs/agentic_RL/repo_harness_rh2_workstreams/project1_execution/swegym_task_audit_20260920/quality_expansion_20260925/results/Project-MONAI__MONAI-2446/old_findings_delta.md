# 历史主张对照：Project-MONAI__MONAI-2446

协调者核验本包三份初稿后明确 release，才读取本题 history/refs.json 唯一 sources 记录。没有读取其链接、旧原日志、跨题报告或 reviewer；本题封存稿不修改。下表“旧记录”指 L1_monai_1/records/Project-MONAI__MONAI-2446.json，hash 已与 refs 匹配。

| 旧主张/字段 | 判定 | 决定性证据与处理 |
|---|---|---|
| base、patch文件、F2P/P2P身份、实际整模块选择器 | 确认 | 本题P/V与原compat-v1 ledger/log一致；source创建日期未另查 |
| 输入外层列表被原地打乱，浅/深复制未规定，非shuffle不必改 | 确认 | dataset.py:681–685,712–716；题面；copy只在gold shuffle分支。生成器并非这里明确承诺的Sequence，不将旧“可迭代都可copy”疑义升级为要求 |
| copy import已在base测试第12行，补丁不缺helper | 确认 | test_smartcachedataset.py全文与test.patch；新增仅一个allclose |
| check3 pass来自题面完整、hints空 | 不足以证明/纠正编号 | 计划user_prompt足够理解，属于check23；本批public_hints并非空，实际actor消息仍unknown，check3=unknown。旧raw hints空不代表本批无提示 |
| 纯测试恢复、不覆盖合法源码；additional_exclusions空 | 确认，限历史路径 | gold projection仅dataset.py；trusted restored/apply成功且实际diff对应；没有完整对抗审计 |
| check5无重复、与6975同文件不同函数、26题唯一修改 | 未核实 | 这是旧报告的跨题检索结论，本轮未读其索引/其它题；不沿链接、不确认留出安全 |
| F2P由题面可推；不强制copy实现 | 确认，限制普遍性 | 功能断言无API/源码身份约束；替代实现仅静态分析，不能把“都能过”当实测 |
| check25称P2P比较dataset[0]与期望不同 | 推翻 | 公开base test_shuffle:120–125实际逐次精确断言dataset[15]为18/13/5号文件，旧描述错误 |
| “删除randomize可能漏过，保护是偶然，因此issue” | 不采纳作为已证漏检 | 删除shuffle后默认顺序首次补入16、17，dataset[15]应为17，与旧P2P要求18不同（静态窗口推导）；不是因为测试未专为此缺陷新增就失去约束效力。本轮未运行mutant，不冒称实验分数。保留有限输入覆盖边界，不机械补CPU |
| 旧stage1 gold3pass+5fail、empty2pass+5fail；nibabel int64错误 | 旧条件未核实，当前引用条件已过时 | 只读取旧记录，没读它的stage1原日志。09-19 compat-v1原日志明确先把5.2.1换4.0.2，noop七pass+目标一fail、gold八pass；5个shape均执行通过。不能把旧噪声延续成当前grader阻断 |
| 建议必须pin nibabel3.x或永久接受五失败 | 已被后续条件覆盖 | 已定位配方用4.0.2且实际成功，无证据要求3.x；这不证明当前actor已有该底座 |
| check26因P2P条数少/环境失败就标回归 | 纠正编号与证据 | 不能从覆盖少证明gold引入新回归。check26 unknown；shape现已实际通过但仍非expected参考成员，是否增补是评分设计选择，非本轮自动改定义 |
| check9环境漂移 | 问题类型重归类 | 依赖兼容性归check6/10等；check9重点是是否执行候选。本次projection/import/log支持执行gold，不能沿用旧编号含义 |
| check10称test_update_cache会shutdown | 部分推翻 | 公开测试74–101未shutdown；test_shuffle与shape才shutdown。旧单次稳定不证明反复运行/线程时序稳定，也不自动证明actor开发可用 |
| check6/7/11安装离线、无外部资产 | 有限确认 | 合成输入无下载；本次历史grader deny_all且实际模块完成，有临时NIfTI与线程。install最后命令RC=0不等于每安装步骤独立RC，更不证明actor安装/网络权限 |
| check20分差来自目标 | 确认，更新条件 | 新引用的no-op目标allclose失败、gold目标pass，其余七项pass；不沿用旧3.66s |
| check27 gold正确最小 | 确认列表目标，保留未知 | copy在建缓存前，保留种子/替换；未穷举自定义Sequence与复制协议 |
| check29无泄漏 | 限定/未知 | 公开题面未给修复代码是可确认的内容事实；本审查已见gold/隐藏测试/旧记录，必须私有隔离；实际actor Git历史和工具答案暴露unknown |
| 父类测试、正向shuffle新增检查与ready_for_probe | 建议不直接采纳 | 父类相关性真实但非全仓门槛；已有P2P对shuffle有判别力；当前只静态needs_review，不批准probe/训练。唯一下一步仍核对实际actor初态与解释器/底座，不另造重复实验 |
| 旧costs.minutes=20 | 不迁移为本轮成本 | 本轮耗时/token/费用没有相应工具观测，填null |

相对封存初稿：核心结论不变。历史带来可核实的旧叙述错误（shuffle断言、shutdown）和需保留但不可跨题确认的关联线索；没有理由改动封存稿。独立review待完成。

历史唯一来源：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_monai_1/records/Project-MONAI__MONAI-2446.json`；SHA256 `604d8709101b5d43bac3026d1d0d8a782ae585f0f43799b2551be32e0321234c`。封存初稿SHA256 `d14a76295e09a753f1a53bed7f54b9e8127289586ceefc73efd4e17bb7df3905`。

## 封存后的编号修正（协调者提醒）

协调者在阅读封存初稿后提醒：按授权流程，私有审查者见到gold/test并不等于actor本地发生答案泄漏。采纳此区分：初稿不改；后稿check29改为unknown（实际actor可见材料未取得），审查者见过的gold/隐藏测试/旧记录只记在usage与读取范围，不计成题目质量缺陷。此修正来自协调者封存后提醒，不冒称独立review结论。独立review仍待完成。
