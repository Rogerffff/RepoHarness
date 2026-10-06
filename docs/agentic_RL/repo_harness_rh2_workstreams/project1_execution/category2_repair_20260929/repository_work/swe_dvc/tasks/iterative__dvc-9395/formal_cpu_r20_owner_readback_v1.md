# DVC9395 R20 正式 CPU 读回

2026-10-03 12:10 SGT。六项正式结果已回收；最终非作者运行复查已完整核收，无新增阻断。只供当前普通基座诊断，不授予训练或留出资格。

| 对照 | 正式reward | 实际通过／失败 | F2P通过／总数 | P2P失败／总数 | 行为解释 |
| --- | --- | --- | --- | --- | --- |
| noop | 0 | 37／4 | 0／3 | 0／37 | 缺失源、run-cache恢复、冻结输出目标失败；另有未计分import失败 |
| gold | 0 | 30／11 | 2／3 | 10／37 | 覆盖用户修改，原缺失源F及10个新增边界P失败；源gold不是正确解 |
| c3_frozenfix | 1 | 41／0 | 3／3 | 0／37 | 41节点全部通过，唯一固定正对照 |
| c3_missing_only | 0 | 40／1 | 2／3 | 0／37 | 仅新增冻结输出目标失败 |
| up351_port | 0 | 35／6 | 3／3 | 6／37 | 恢复目标通过，但两个dry及四个无remote边界回归 |
| w_swallow3 | 0 | 30／11 | 2／3 | 10／37 | 必要缺失源恢复F及10个新增边界P失败，吞异常未实现目标 |

每项实际41个节点、40个计分参考（3F／37P）。参考无缺席、跳过或未归类，实际没有pytest收集／导入／ERROR节点。未计分原import节点保留在41分母中。所有候选UID54322 wheel字节预检通过、安装rc0，测试rc与reward一致；评分清理成功且外部精确job标签的容器／网络均为空。

R20固定release为 `cat2-cpu-r2e093-swe40-prepare900-20261003-v1`，manifest为 `sha256:2a4ceb0315ea959232151d70f29ccc48bd34bdb0cb7dcfbb4aa177fec07bd393`。新prepare／run input／FrozenPatch／完整日志／逐参考结果各自保留在归档；复用同一冻结材料、镜像和脚本digest。实际spec及六账本reset均900，封闭policy只绑定已授权精确题级身份；900用于九处既有reset步骤。候选／安装／测试／whole／清理预算、保护规则与资源profile没有扩大。

六项trusted setup聚合约149–249秒，均低于旧300秒；不能由本次完成推断新增预算被用到、具体chown根因或效率提升。旧R14两次protect300 infra/null不并入本矩阵。

六项成功账本 `resource_facts` 均为null。c3_frozenfix单个运行时点的实际HostConfig为2CPU／4GiB／PID512／none、非privileged，并核cap列表；该时点OOMKilled=false不是全程资源证据。镜像默认root执行可信setup／protect，候选预检／安装／测试以UID54322 exec；不能声称整个容器非root或全程没有OOM/PID事件。

R5真实公开actor17测试通过证据只按相同公开payload、prompt正文、镜像和执行源码复用。R20新prepared已核公共数据与prompt字符串字节相同；整份prompts.jsonl metadata不声称字节相同。没有新R20 actor执行，也没有模型成绩。

旧离线collector v1把captured logging中的 `ERROR dvc.commands.freeze` 误算成第42节点，导致监督进程末尾exit1。保留旧helper及实际错误观察；v2限定两个选定pytest文件后离线成功汇总。没有重跑候选、改官方report、日志或材料。 官方诊断num_parsed_tests也有同类额外非参考logging键：42或43不能当实际测试分母；完整日志重建41节点、40参考的逐项分区结果不受影响。

GPU实际镜像若与CPU c093不同，须先经共享发布固定精确新policy／image／consumer并窄验，实际spec与账本保留900；CPU image ID不能冒填GPU ID，不能静默回退300。solver只取得原题面、中性开发说明及公开依赖，私有正负补丁和评分材料留在host。

原测试仍含内部mock约束；模型合理替代方案若得0，需要按公开目标和实际行为复核。公开issue明确必要缺失恢复，dry／no-remote／修改保护来自既有公开源码与API依据，不能说issue逐项规定了所有新增边界。

证据入口：

- [正式矩阵](formal_matrix_r20_v1.json)
- [实际CPU spec](../../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/9395_r20_actual_spec_readback_v1.json)
- [六项题主检查点](../../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/9395_r20_6controls_owner_checkpoint_v1.json)
- [汇总修正观察](../../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/9395_r20_offline_collector_correction_v1.json)
- [正确对照HostConfig范围](../../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/9395_r20_c3_live_resource_owner_check_v1.json)

- [官方解析计数边界](../../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/9395_r20_official_parsed_count_boundary_v1.json)
