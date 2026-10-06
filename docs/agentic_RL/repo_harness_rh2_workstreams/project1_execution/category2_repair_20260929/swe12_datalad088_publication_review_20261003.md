# SWE12与DataLad088共用发布核查

2026-10-03。第七版已封包为 `cat2-cpu-r2e088-swe12-git-20261003-v1`，905个成员，外部manifest SHA `f9dfcd16c9c88e4f514512e61781856b7d6f1a71a20b64cd1843d20546c5009b`。发布目录：`runs/category2_repair_20260929/releases_20261003/r2e_088_swe12_git_candidate_v1/`。这是共用材料CPU候选，不是五题已经完成正式验收。

## 改动及复核范围

| 题目 | 本次进入正式消费者的修订 | 题主后续验收 |
| --- | --- | --- |
| Moto6114 | 在已有测试内加强公开行为断言，保留原1F／34P与vendor命令；单独context记录原参考，不伪造新增键 | 原正确／错误候选、安装与完整参考状态、正式收口 |
| Pydantic5662 | 新目标F2P及固定E10离线安装，2F／127P；core0.27和本题资产独立绑定 | 实际安装/import/core、公开actor、正负对照与全部参考 |
| Pydantic6283 | 非42目标F2P及本题E10离线安装，2F／38P；core0.42和本题资产独立绑定 | 保留不验证构造护栏，实际正负对照、安装与收口 |
| DVC5839 | 真实数值精度F2P，2F／21P；精确E13＋pathspec离线配方和4 wheel身份，setup验证候选UID可读 | 新镜像内UID54322实际读取与安装、正确修法及有效数字退化候选 |
| DataLad6b6f | 088来源到最终修订替代active065，两个已有测试内增加K7/K8；题面、runner和17期望键不变 | 新noop／C-A／gold三方；预期0／1／0，核gold失败位置与C-A完整匹配，旧GPU请求维持暂停 |

主维护者读完三个SWE候选的实际生产差异、材料绑定与关键维护检查，负责三方合并。Pyd候选作者另做跨候选合并窄核；明确它不是Pyd作者之外的fresh盲审。其报告位于 `release_work_20261003/swe12_combined_v1/MERGE_REVIEW.md`，SHA `745fc91cf4b30e33b2052bf51be987a838780d26c828a6ffb7f76dc929f40bd3`。

五个受影响SWE生产文件中，各候选新增类／函数的AST与原候选一致；类型分派、固定registry和asset、原parent／source／public／base检查、控制文件恢复及hygiene保留。原R6类型、manager、Git四文件、builder与R2E消费实现均保留。Pyd两题即使安装文本相同，core、来源、镜像、资产仍独立；DVC wheel检查走既有setup失败infra路径，没有变成模型0分。

DataLad登记由另一子agent在精确R6副本完成，主维护者核代码差异、source→065→088、两个AST新增断言及公开兼容性依据。生产loader只换registry／pins／manifest常量；无算法改动。088保留原source before，将原4处与新增2处合并，避免同target叠加065和088。新hidden tree为 `2a62382c32a9def6a9ccf42c27fb938b7e4c0c0747805bafeaa605afce6b4724`。17期望中仍含原FAILED，不能写成17项均通过。

## 验证与证据

- SWE维护共有462个不同用例最终分批通过。组合v2为449通过／13个fixture错误；只修fixture重复copy后，该模块34通过，覆盖上述13错误。原失败日志保留，没有将它写成一次全绿完整运行。
- R2E精确登记候选73项维护通过。两部分生产delta不相交，受检代码逐字复用；未重跑不变的Git／builder共同验收。
- 四个SWE与DataLad单题共5份prepared成功。最后合包重新实际消费264题：只有上表五题改变，其余259项不变；五题消费身份各自与独立候选逐字相同。
- SWE12 producer manifest SHA `9bf50d0a4e14ace49eac459c50ad630d9e228365d606e0dcfc9d9f529b88615e`；R2E registry v19、pins v20。最终905个文件的大小／SHA和成员集合、trusted 48 R2E／216 SWE通过。
- 原R6及三个冻结候选保持。第一次封包工具写错SWE manifest文件名，尚未生成release manifest即失败；保留为 `r2e_088_swe12_git_unsealed_attempt1/`，不是部署版本。修正发布脚本路径后另建上述有效release，生产代码不变。

详细命令、原stdout/stderr、三方合并delta、实际264消费、逐候选身份核对在有效发布目录的 `checks/`。本轮没有SSH、项目容器或新增正式CPU结果。

## 交接边界

总协调统一部署：cpu-a供Moto6114、Pyd两题、DVC5839；cpu-c供DataLad6b6f。cpu-b无受影响新题可保留R6。在途作业不热换代码，不因本次发布重跑已收口且身份未变的题。Moto5406工具仍固定R5。新旧FrozenPatch不能重绑。

各题负责人保留端到端责任，安排受影响正式对照和非作者结果核查，再向统一GPU执行者提交；共用发布维护者不重复包揽题级终审。此次不含Moto5134和其它排队中的修订，候选准备完成不等于已发布。
