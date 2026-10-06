# Moto6114 新37：两模型首轮收口

2026-10-03。R21当前材料的Coder与Qwen各首次一次均原分1、安装／测试0、37参考完整；题主完整候选及轨迹分析完成。两者都返回当前要求的正确ARN身份，并保持新增Neptune名字start／delete行为。当前无须题目、评分或环境修订；额外候选操作及单样本稳定性限制仍保留，不授训练资格。

| 当前模型 | 具体修法和验收边界 | 本次轨迹 |
| --- | --- | --- |
| [Coder](coder_a1_neptune37_analysis_20261003.md) | 仅修改describe，沿用既有模式按ARN地区选择当前账号backend再查名字；原start／delete／stop等委托源码未改。当前37参考全过；跨地区额外自测不扩大正式范围。 | 18回合、17工具、0标错；输入965999／输出3756；solver61.527秒。首个明确ARN自测在源码修改后，没有修前失败复现。 |
| [Qwen](qwen_a1_neptune37_analysis_20261003.md) | 本地backend截取ARN末段，额外扩改5方法；保留名字start／delete的Neptune委托，当前37全过。额外ARN modify未同步kwargs，六方法一般正确性未获验收；跨账号／地区／服务沿既定范围排除。 | 42回合、41工具、2标错＋1未标错空测试；输入611249／输出8237；solver93.869秒。先修导入再复现目标失败，源码修后同复现成功；另扩范围及重复公共测试。 |

配对输入固定 `swe-moto6114-identity-neptune37-r21-20261003-v1`，SHA `6dfa36e642bee0e9fb5e8d35efe85149bb8c9258a4a980591c9706cc57d31723`；材料 `moto6114-cluster-identity-neptune-preservation-v2`。两臂1972baseline entries、完整prompt原字节、材料身份、实际镜像和模型／评分预算相等；都实际code8、setup900，与CPU政策单独区分。模型引擎／adapter不同部署与记录时间，各自捕获身份关联，未重复全部权重或GPU内存hash。

两臂机械回执 `runs/ordinary_gpu_probe_20261002/migration_20261003/swe-moto6114-identity-neptune37-r21-20261003-v1_pair_execution_receipt_v1.json`，SHA `ea6eba363c8e9565ac02de8b9f9b5558c132ff4671e4c184ee64a8623536f7b8`，原件不改。总账已returned可供题主核验后确认。单个执行原件paired_request_closed=false、机械semantic字段未填，不改成题主结论；当前收口记录单列。

Qwen更多回合但累计输入较少，Coder较少回合但有长源码读取；该样本描述两种定位和验证选择，不推出一般模型排名、成本优势或稳定成功率。评分保护耗时与solver、正式项目安装／测试分别保留，不能混算。每模型只有一次，普通未启动追加继续暂缓。

旧 `swe-moto6114-identity-r7-20261003-v1`／35的Qwen原满分为历史：其两条Neptune名字回退已在新37的R21源码复评验证为0。此次两份新工件均保持新两项，旧结果不能作为本次一臂、不能被重标为37通过。严格300超时、支持900后有效0及旧安装2不回写。

当前本题首轮收口；继续Moto其余四题的Qwen首次回传与题主分析。本题无活CPU作业、无普通重复或新材料发布安排。
