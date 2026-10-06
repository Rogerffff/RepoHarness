# Moto 六题：当前准备与下一步

依据：2026-10-04 整理的当前题级总账、固定发布回执、运行原件与独立报告。题主 `SWE | Moto 题目修订`，线程 ID `01a0fd61-fbf9-7d83-860e-c6627bcd3d7f`；负责 5406、5960、6114、6185、6408、7584。

六题当前普通探针CPU与最终非作者验收、两模型各首次和题主完整源码／轨迹分析全部完成；六份当前请求均已终局回传、确认并closeout。当前12个材料有效模型臂中11个有效1、1个有效0（6185 Coder公开嵌套S None漏修）；旧35的6114 Qwen单臂仅历史，不与新37配对。Qwen6114额外ARN操作和6185不可达类型校验分支等限制单列。当前首轮无剩余必做CPU或GPU任务；普通未启动追加暂缓，每模型单次不证明稳定、一般API兼容或训练资格。

| 题目 | 当前有效事实 | 下一步 |
| --- | --- | --- |
| [5406](tasks/getmoto__moto-5406/results.json) | 固定R5，1F／27P；两模型首次均安装／测试0、28参考通过。题主完成源码与轨迹核对，实际region修法正确。 | [双模型首轮分析](tasks/getmoto__moto-5406/two_model_first_round_analysis_20261003.md)已收口，总回执已核并总账确认。每模型1次，追加暂缓，不能证明稳定。 |
| [5960](tasks/getmoto__moto-5960/results.json) | 新R18三组0／1／0、安装均0；159实际项合键158完整。实际UID安装、真实CC原6条公开操作通过[最终独立验收](reviews/moto5960_final_cpu_non_author_20261003.md)。 | [双模型分析](tasks/getmoto__moto-5960/two_model_first_round_analysis_20261004.md)已收口、总回执已确认；两模型原1／1、安装／测试0、159实际／158解析全过；投影与表内存储保护一致，复制分支不同。旧R13安装2保持。 每模型1次，普通追加暂缓。 |
| [6114](tasks/getmoto__moto-6114/results.json) | 新R19的noop／gold／wrong_first有效0／1／0、37参考完整、实际UID安装0。R21原Qwen源码臂安装0、原35全过、仅新增两条Neptune保持项失败，正式0；[最终独立验收](reviews/moto6114_r21_neptune37_final_cpu_non_author_20261003.md)通过。 | [新37固定请求](tasks/getmoto__moto-6114/probe_request_r21.json)已returned并终局确认；两模型原1／1、安装／测试0、37全过，[双模型分析](tasks/getmoto__moto-6114/two_model_neptune37_first_round_analysis_20261003.md)确认身份及Neptune名字保持。Qwen额外ARN操作限制单列。旧35不配对，实际900另核、原300超时保留；每模型1次，普通追加暂缓。 |
| [6185](tasks/getmoto__moto-6185/results.json) | R13全22对照安装0，36实际／35解析、原34P与两合键参数保持、自有清理空。raw4个1／18个0，ctx／parity正、ctx_list兼容、rv_dynamotype仅范围外观察。 | [双模型分析](tasks/getmoto__moto-6185/two_model_first_round_analysis_20261004.md)已收口、总回执已确认；Coder原0／Qwen原1，安装均0、测试1／0；公开嵌套漏修属于Coder有效0，Qwen完整36实际／35解析通过。原34P保持，Qwen不可达校验分支和停止范围单列。 每模型1次，普通追加暂缓。 |
| [6408](tasks/getmoto__moto-6408/results.json) | 新R18三组0／1／0、安装均0、96参考完整，reorder在新增唯一归属断言失败、95P全过。实际UID原安装和真实CC原5条操作通过[最终独立验收](reviews/moto6408_final_cpu_non_author_20261003.md)。 | [双模型分析](tasks/getmoto__moto-6408/two_model_first_round_analysis_20261004.md)已收口、总回执已确认；两模型原1／1、安装／测试0、96齐，迁移标签唯一归属与两側原标签保持。Qwen中间回归和工具／自测失败已单列，旧R13安装2／raw保持。 每模型1次，普通追加暂缓。 |
| [7584](tasks/getmoto__moto-7584/results.json) | R13全11对照安装0／20参考完整，两有效正对照1、其余0。实际UID和真实CC原4操作通过[最终独立验收](reviews/moto7584_final_cpu_non_author_20261003.md)。 | [固定请求](tasks/getmoto__moto-7584/probe_request.json)已returned并终局确认；两模型原1／1、安装／测试0、20齐，[双模型分析](tasks/getmoto__moto-7584/two_model_first_round_analysis_20261003.md)确认源码功能相同、校验先于重复订阅返回。工具错误／隐藏空测试及弱复现单列；每模型1次，普通追加暂缓。 |

## 固定发布与实际运行

5406固定R5 `cat2-cpu-r2e078079-swe7-git-20261003-v1`。6114旧35材料及原Qwen满分保持历史身份，旧请求已安全部分结束，未执行Coder、追加采样或旧35复评。旧Qwen两处Neptune行为回退已实际复现，新37材料追加两条原本通过的参考，固定R19 manifest `2cfdd9b4f1134c0915346b727b729665482c4c1121b550764833f16f2982402e`；R19 exact源码臂保护300超时保留infra/null。R21支持manifest `630f71fc1a4ae6f587f3161fae56d92927a91801ae4b08954a556ee059cada9c`，1482成员核验并确认，严格同题／patch／image保护900恢复单exact有效0，不改原材料和旧超时。

6185／7584与5960／6408历史失败对照固定R13 `cat2-cpu-r2e089092-swe27-pandas-moto-20261003-v1`，manifest `3fad18daff8db219294e10cbf08d4424d68cf7000d008bb983cba4bdc427b641`。发布回执、1094成员和48 R2E／216 SWE消费者读回已核，发布请求均确认；发布完成不能代替项目安装／测试成功。

5960／6408新离线供应固定R18 `cat2-cpu-r2e093-swe40-moto-offline-20261003-v1`，manifest `a84bdc339618e010440df3728c982b2d1d141b1f8295f69761984386ee3a512e`，1419成员和固定source＋单COPY层已核。两题实际candidate与开发UID安装、公开操作和最终验收完成，见[发布读回](reviews/moto_r18_offline_publication_owner_readback_20261003.json)。历史R13安装失败和未执行的旧R5反例对照保留，不预报其分数。

CPU使用本题固定发布、`runtime_cpu_v2`，原prepare／export-gold／run接口、原安装及测试。后续[矩阵v2](tools/moto_four_r13_matrix_v2/manifest.json)只增加正常评分白名单，failed_to_grade／未知／infra停止，不能把所有非零都归为环境失败。当前Moto固定cpu-a，题主串行、全child经共用cpu_slot，遵守[资源规则](../../cpu_resources_20261003.md)；退出75为未开始，不能计题目失败。cpu-b已经退租，不派发。凭据仅在忽略连接文件，CPU身份不能跨题替代验证。

6185六组评分共499原件，UID6、真实CC23，8个archive合计528件；不是528次实验。22臂均安装0、原参考完整、候选与自有容器／网络查询实际清理空。原gold D4不完整仍0；rv_dynamotype原满分仅保留为范围外观察。遵守[既定停止范围](reviews/moto6185_existing_stop_scope_readback_20261003.md)，不新增未保护畸形值、五层以上输入的穷举。作者原件读回和最终非作者核查均已完成，普通双模型请求已实际提交；GPU运行与训练资格仍需各自证据。

## 证据与公开交付边界

每题 `results.json` 是当前入口，[cpu_preparation.json](cpu_preparation.json)汇总实际准备。固定发布引用的题卡、revision_request、acceptance_matrix、发布输入、旧验收／独立报告和运行原件保留原字节。工具静态审查、镜像准备、正式CPU验收、GPU实际运行和训练资格分别记录。

6185的[部分独立报告](reviews/moto6185_r13_partial_cpu_non_author_20261003.md)覆盖最先5臂、UID和原C1–C4；后17臂和全矩阵一致性已由[最终报告](reviews/moto6185_final_cpu_non_author_20261003.md)独立验收。真实CC2.1.205＋确定桩证明原公开操作实际执行；完整statement spec.prompt已经交付，六行generic public_hints没有进入messages/system。完整命令stdout/stderr只在进程侧捕获，CC tool_result只有RC标记，不能声称模型读过完整输出。原CC不含INSTALL，实际UID原make init另验。93个newer entries只部分列举目录／pycache，不证明全93为pycache或全工作区无产物，见[范围补充](reviews/moto6185_r13_public_actor_scope_clarification_20261003.md)。不授自主模型、actor FrozenPatch、actor-to-grader或typed训练资格。

5960、6185历史参数合键必须核实际收集、两条原行和逐参考状态；parser保持。目标测试首次失败后未达到的后半段不能声称通过。候选安装、完整测试、实际退出、逐参考、具体失败和两层清理均保留；保护／复制／运输与项目测试耗时分开，不归因solver。

## 探针与协作

题主负责修订、验收、每次模型结果分析及必要修复；发布线程负责共享consumer、供应与CPU发布；GPU线程负责固定请求兼容、排队、实际模型运行和回传；巡检线程负责观察及已授权裁定。按[三方总账工作流](../../coordination_workflow_20261003.md)先固定输入、CLI落账、直接通知接收者，再核真实终局回执。普通进度写当前记录，不通过协调者中转；写文件不等于已经通知。

每题两模型首轮各一次，实际GPU代码／镜像／开发及评分UID／完整预算／首prompt及hints交付／新FP与轨迹由执行者另核。题主逐attempt分析修法、定位与纠错、工具错误及重试、验证质量、token／回合／调用数、solver／工具／环境／队列耗时和终止原因。截断、缺模型、未评分或infra保留原分母；rawscore1仍需核源码语义。没有并行机会或执行层串行记不可判断，单样本不证明稳定。

当前GPU优先首轮覆盖，普通未启动追加采样暂缓；旧固定请求中的重复安排作为历史输入保留。后续重复、停机、销毁或新租机服从用户当前明确授权，题主不自行处置。当前首轮及必要分析均已完成，未发现需新CPU修复的材料／环境缺陷；此阶段完成不等于稳定性或训练资格。Moto依赖消除不代表共享机器已停止或退租。
