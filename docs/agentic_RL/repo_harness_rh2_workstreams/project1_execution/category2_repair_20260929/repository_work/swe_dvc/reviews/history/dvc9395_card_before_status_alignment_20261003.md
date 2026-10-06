# DVC9395 当前题卡

2026-10-03。状态：**v2草案六候选私有CPU诊断及非作者材料／原日志窄核已完成；正式评分、actor交付和模型探针未完成。** 输入为云端v4及09-30更正；v4不是已验收版本。完整身份和工件见 [revision.json](revision.json)。

公开目标是拉取此次repro必需的缺失数据；base的 `is_data_source`明确含add/import。原测试的checkout/restore次数约束误拒合理实现；吞错误候选在原云端私测得1但不恢复文件；gold会覆盖用户修改，且有已证dry、无remote和run-cache回归。最新范围见 [09-30交接](../../../../../category3_diagnosis_20260929/handover_to_category2_20260930.md)及 [原结果](../../../../../category3_diagnosis_20260929/tasks/iterative__dvc-9395/result.md)，以页首更正为准，不能沿用下面历史T3/S2豁免。

保留v4：去掉精确计数、核拉回内容和下游产物、确认修改不被旧数据覆盖、import缺失恢复、不可拉回时传播错误。另补11个精确参考：

| 缺口 | 新断言 | 草案分组 |
| --- | --- | --- |
| 冻结stage输出 | 工作区和缓存都删掉；下游恢复并用到remote数据；命令痕迹不变 | F2P |
| dry两种状态 | 缺源或缺输出时，workspace/对象cache/runs内容快照不变；允许base在缺源dry时报既有错误 | P2P 2项 |
| 无需下载无remote | normal/dry均能处理齐全数据，不因预拉取报错 | P2P 2项 |
| 无remote且用户修改源 | 修改保留，下游使用新内容 | P2P |
| 无remote且源确实缺失 | 抛出失败，不能吞掉错误并声称成功 | P2P |
| no-run-cache | 本地runs删除后，不下载runs、不执行不必要命令 | P2P |
| 无hash已有输出 | 普通新stage可以按原公开路径产生正确输出 | P2P |
| 依赖变化 | 旧输出cache不可得、remote空，仍按新依赖重算 | P2P |
| HTTP恢复 | 保留本地run-cache，从只读loopback HTTP恢复缺失对象和lock，不重新执行命令 | P2P |

HTTP没有要求新增外网服务或让HTTP列举runs。目录部分删除歧义继续登记，不补断言；原run-cache恢复要求的P3风险仍保留。新增行为不依赖gold的具体函数分解、调用次数或传参形式。

主正确对照复用独立核实的 `c3_frozenfix`（SHA以修订单为准）；gold与`up351_port`作为负/辨别对照，后者有dry回归，不能为保它删断言。正式矩阵预期noop0/gold0/c3_frozenfix1/c3_missing_only0/up351_port0/w_swallow3 0，**正式reward全部为null**。

私有诊断 [cpu_diagnostics_v2.json](cpu_diagnostics_v2.json) 分开记录原版与当前v2：原版30执行／29参考，gold与吞错候选全过，`c3_frozenfix`仅被旧restore次数断言拒绝。当前v2为41执行／40参考，无参考缺席，六方观察如下；这些是pytest结果，不是正式评分。

| 候选 | 当前v2观察 |
| --- | --- |
| noop | 三个F2P及未计分的原import用例失败；37个P2P通过 |
| c3_frozenfix | 全部41节点通过 |
| gold | 修改源保护及全部10个新增P2P失败 |
| c3_missing_only | 仅新增冻结输出F2P失败 |
| up351_port | 两个dry及四个无remote边界失败 |
| w_swallow3 | 修改源保护及全部10个新增P2P失败 |

本轮v1诊断曾有6个新增节点因 `Repo.odb` 不存在而失败。v2仅把三处 `dvc.odb.local.cache_dir` 改为本base真实的 `dvc.cache.local.path`，不删断言、不改候选。v1材料保留在 [history](history/dvc9395-behavior-v1-draft/revision.json)；旧API错误的effective行不复用，original六行的补丁、依赖与候选身份未变，报告明确复用范围。当前六个容器全部清理成功，无残留。

[非作者v2差异窄核](../../reviews/non_author_4166_9395_v2_review_20261003.md) 确认API修正有基线源码依据且没有扩题；该报告写于新版运行结束前，不能代表六方原日志已验收。原restore仍含内部调用约束，后续合理实现接受性风险继续保留。

[非作者CPU原件读回](../../reviews/non_author_6954_9395_cpu_review_20261003.md) 随后独立核了未变original六行及当前v2六行：全部参考精确命中、退出与清理相符，失败落在实际行为路径而非旧API、导入或收集错误，无新增阻断。noop的非参考import失败明确保留；旧effective六行只核原件完整性，不混入当前结果。报告不验正式评分、完整安装或actor。

下一步在原版对`w_swallow3`做正式评分确认，再做新六方矩阵和actor交付。其它云端候选证据按接受性需要定向复用，不重跑历史全部组合；不能核销缺席、skipped或正对照失败。

环境：cpu-a已准备公开依赖镜像，源码未变、base层保留、`pip check=0`，实际pygit2为1.14.1。首轮旧assets的CPython3.10 wheel与本题CPython3.9不符，已改用历史核实的CPython3.9 wheel，未放宽SHA检查；身份见 [CPU准备记录](../../cpu_preparation_20261003.json)。

[v2发布请求](publication_request_v2.json) 已固定完整测试补丁、有效安装配方、公开开发说明及诊断报告身份，等待共用冻结版本。未改题面，不把私有反例交给solver。正式CPU、actor、非作者验收通过后才能提交普通探针。

[本轮公开actor检查](public_actor_r5_v1.json) 已完成真实CC/relay的四条公开命令，17个既有公开测试实际通过且无skip／缺失；首请求逐字交付题面和开发说明，身份/profile一致，自有容器与网络清理。完整原件已SHA校验回收到本机，[非作者运行原件读回](../../reviews/non_author_actor4166_9395_runtime_review_20261003.md)已完成，无新增阻断；正式CPU评分和模型探针尚未完成。
