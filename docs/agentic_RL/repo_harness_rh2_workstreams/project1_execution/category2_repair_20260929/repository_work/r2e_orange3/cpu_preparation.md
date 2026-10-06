# orange3：CPU执行记录

更新：2026-10-03。本包固定cpu-c；网关18196／桩18197。连接只读总协调的私有入口，不写入本包或solver材料。远端写入仅限`packages/r2e_orange3/`和自己的jobs。

## 22e98首轮

- 首版发布 `cat2-cpu-r2e064065-swe5-20261003-v1`，manifest `282021…`，794文件SHA／可信48＋216读回已核。只新增本题题面064及DataLad065，不含Orange另三题草案。
- cpu-a39份私有输入完整传输，外层包SHA `869fc505…`；两个来源镜像请求均75未入槽。迁至cpu-c的外层包 `9a1f0096…`，39份私有材料与4份公开检查文件逐份核SHA。私有材料不整体交actor。
- 首版本机trusted prepare返回0，prepared manifest `5329a886…`，host grading artifact `b428e59d…`。
- `orange22-derived-c-20261003-v1`返回75，v2获槽且返回0。新daemon镜像`29d37138…`，recipe `r2e_derive_v1`／`0da821a1…`；20项完整性检查通过，agent/grader身份均可执行解释器且不可读隐藏材料。此作业在旧builder上运行，不声称新增运输限制已使用。
- `orange22-actor-c-20261003-v1`在runtime_cpu_v2返回0。CC2.1.205／UID54321／Python3.7.9／NumPy1.17.5正确；实际HostConfig和cgroup为2 CPU／4 GiB／512进程，禁止对外网络及私有挂载。
- 首HTTP含完整新题面 `f8701d3a…`，保存prompt为`cbb5bef0…`，网关与桩messages相同、无旧直接答案。来源public_hints未交付，当前GPU公开说明另行提供。
- preflight与导入检查返回0，公开helper 1passed，数字复现返回1且实际M=`[1,2,0,1,2]`，不满足还原关系。它是原缺陷，字符串例因先前断言失败未执行。没有源码修改，原生FrozenPatch为空、导出正确；excluded缓存路径变化据实保留。
- actor、relay、network与gateway/stub均清理成功，残留为0。合成桩端点不代表实际模型推理，也未运行正式grader。原件32文件逐份SHA收取，capture压缩包`f17f0660…`。

原件与摘要在忽略目录 `runs/category2_repair_20260929/repository_work/r2e_orange3/cpu-c_20261003/`；[首轮收据](tasks/22e98f8f/cpu_actor_v1_receipt.json)只证明上述范围。

## 配方一致性接续

历史已验noop0／gold1／DG0使用`r2e_derive_v1+sysconfig_v1`／`e2e17bf…`。本次首构建漏带该步骤，已主动报告，不能将缺步骤的镜像直接等同历史环境。首轮证据保留，补建仅恢复原批准步骤，不修改题面或评分。

第四版的补建v1请求返回75，未运行。后续直接改用已开放的第五版 `cat2-cpu-r2e078079-swe7-git-20261003-v1`，manifest `80ee228…`，builder `5af7dc…`与第四版相同；总协调已验其837成员／可信读回／Git窄修。22e98四个任务面及两份recipe脚本与首版相同。

第五版trusted prepare返回0：prepared manifest `3bfbbaad…`，host grading artifact仍为`b428e59d…`，重新生成本机路径。补建使用原profile、`--sysconfig-fix`、唯一job-prefix及2 CPU／4g／512／cleanup60参数，经全机prepare槽运行。补建v2返回0，实际镜像`ad9d2a37…`／配方`e2e17bf…`与历史一致，21项复核全过。最终actor v1请求75未入槽，v2返回0；新题面、身份、资源限制、冻结导出和所有清理已核，见[最终收据](tasks/22e98f8f/cpu_acceptance.json)及[说明](tasks/22e98f8f/cpu_acceptance.md)。非作者窄核40/40项通过（检查项，不是实验数），[固定单题请求](probe_request.json)已提交GPU线程，执行者已确认收到，正在复核与排队，见[回执](tasks/22e98f8f/probe_submission_receipt.json)。

## 其它三题

[4014八方](tasks/4014f248/acceptance_plan.json)、[50f6八方](tasks/50f6a758/acceptance_plan.json)、[9b54十方](tasks/9b5494e2/acceptance_plan.json)仍为固定待运行目标，observed均为空。50f6公开命令与剧本已准备但未执行；9b54三组概率关系校准已完成，正式十方仍未执行。共用版本更新不代表本包草案已发布，取得题级发布回执后才进行新版评分。

所有Docker作业领取全机槽，75低频重试用新job ID；只清理本包label，不全机prune，不终止其它端口服务。历史grader准备预算1200需在最终入口登记，不能与GPU求解预算混淆。[资源规则](../../cpu_resources_20261003.md)为当前公共入口。

9b54前检使用原020与原隐藏面，本机新prepared/私有场景已核SHA；不使用未发布的新隐藏测试。第一次完整组合尝试的构建与拒绝保留，下述单独env_v2校准接续，不改其原件。

9b54前置CPU检查：原020＋env_v2＋sysconfig镜像构建22项通过，但consumer拒绝完整`caa2db…`摘要，CC／拟合／模型请求均未开始；[首轮诊断收据](tasks/9b5494e2/probability_precheck_v1.json)保留原异常和清理。公共维护者已通知，不能绕过批准检查。随后以原已批准完整`env_v2`／`512277…`另建实际镜像481eb85，21项复核通过；prepare v4与actor v1均返回0，实际三组拟合完成。base/gold最大差0，G1差0.38716698009532013；当前iris数据容差可保留。七步RC0，45份actor/实际prepared原件SHA核对，模块来源、最后G1原生FrozenPatch与资源/全部清理已核，见[作者校准收据](tasks/9b5494e2/probability_precheck_v2.json)。未运行新隐藏评分，省略sysconfig不代替最终开发配方。

[等待回执](tasks/9b5494e2/probability_precheck_wait_receipt.json)保留纯env_v2 prepare v1/v2/v3均75未入槽的历史；总协调轮转后资源等待解除。最终完整组合审批、新材料发布与十方正式评分仍待完成。
