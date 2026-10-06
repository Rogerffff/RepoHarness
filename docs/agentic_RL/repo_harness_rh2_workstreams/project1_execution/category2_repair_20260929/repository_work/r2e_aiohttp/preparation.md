# aiohttp 四题：当前执行入口

2026-10-03，Asia/Singapore。持续题主为 `R2E | aiohttp 题目修订`，线程ID `01a0fd63-99aa-7af0-94bb-591d3c151b17`，工作包 `r2e_aiohttp`。原cpu-b已销毁；本次1c1归因与新增P2P的五行消费验收均已在现存cpu-a完成。行政暂停已由统一恢复通知接替，[暂停检查点](pause_checkpoint_20261003.md)保留历史。现在按[三方流程](../../coordination_workflow_20261003.md)和[总账工具](../../task_board_usage_20261003.md)接续；本包题主维护逐题进度，直接向发布/GPU请求，不再经管理线程转话。

| 题目 | 当前事实 | 下一步 |
| --- | --- | --- |
| [4075](4075_current_card.md) | R069、CPU、首轮两模型原工件评分及独立执行/题主语义完成；均reward1，133 PASSED+3固定C-only FAILED匹配；[行为分析](4075_trajectory_analysis_20261003.md)已补 | 首轮总回执已ack，活动交接清空；统一第二阶段同条件重复待安排，不重复已有首轮 |
| [1c1](1c1_current_card.md) | 首轮原58/58和raw1保留；[实际归因](followup_1c1_cancelled_main_20261003/results_public_cancelled_main_20261003.json)与非作者核查确认完整Coder新增取消清理回归及58键漏检 | [单P2P修订](revision_1c1_cancelled_main_p2p_20261003/README.md)已发布094/095并完成59键五行及非作者核收；Coder只在新P2P失败、Qwen59/59，原raw1/58保留；未来重复须新binding |
| [240d](240d_current_card.md) | 首轮两模型及[完整行为](240d_trajectory_analysis_20261003.md)核收；Qwen33/33，Coder最终撤回兼容层导致收集失败，原null保留 | 原safe_partial回执已ack，活动交接清空；同条件重复待安排，不为通过重解/重判 |
| [6183](6183_current_card.md) | 首轮两模型及[行为核收](6183_trajectory_analysis_20261003.md)完成：Qwen49/49，Coder自身撤回兼容预置导致收集失败，原null保留 | 原safe_partial回执已ack并清活动交接；同条件重复待安排，不为通过重解/重判 |

其余三题当前CPU固定第六版 `cat2-cpu-r2e080087-swe8-git-20261003-v1`，855成员，manifest SHA256 `ab0a3a13fd65e0ea4cd60541ea3b37b01196170477e25832df246f33ea208828`，material_v18/pins_v19。见[正式绑定](publication_binding_r6_20261003.json)、[prepare作者读回](results_preparation_r6_20261003.json)与[两题材料版本](material_bindings_1c1_240d_r6_20261003.json)。4075的已结束请求保持069版绑定，不改绑历史尝试。

13行CPU作业已自然结束、rc0；148份矩阵原件的大小/SHA、固定parser完整58/33键、原补丁/FrozenPatch/projection、profile、runner及清理均由作者核对。见[1c1六方](results1c1_r6_matrix_20261003.json)、[240d七方](results240d_r6_matrix_20261003.json)、[非作者复核包](review_handoff_1c1_240d_r6_cpu_20261003.json)。按自有aio-r6标签只读查容器/网络残留0；当前一次非作者双角色已完成，题主另核决定性原件，见[CPU核收](cpu_result_acceptance_r6_20261003.json)；不是按报告投票。公开R085/R082真实首请求另见[6183交付](results6183_r085_delivery_20261003.json)、[240d交付](results240d_r082_delivery_20261003.json)。CPU桩只交题面；GPU首轮四题两模型的已审题面/brief真实交付另已核收。

[CPU资源入口](../../cpu_resources_20261003.md)的恢复时点记录保留；随后1c1实际归因经发布者支持与现存cpu-a公平槽完成。本包不自行改control/setup或重复已完成CPU矩阵。队列与运行事实以总账/执行者回执为准；普通进度不广播。下面保留具体材料/机制说明，筹备时点字段不覆盖上面的最新事实。

原[CPU退租依赖回执](cpu_retirement_dependency_20261003.json)当时列明空依赖，652文件及7份下载回执已本地核SHA/大小，历史不回写。**1c1公开取消边界归因已完成并核收**：现存cpu-a使用原00ad镜像和同一公开输入，对原baseline／完整Coder7／完整Qwen2串行执行，退出0，96份实际原件SHA／大小核齐。仅Coder在observer前留下worker pending1及开放gen／loop，基线和Qwen正确收尾；原分不改，实际语义失败与58键遗漏单列。[单P2P修订](revision_1c1_cancelled_main_p2p_20261003/README.md)已完成094/095五行及非作者核收，不追加模型。归因和材料消费均无待跑／待归档部分；见[最新资源依赖](resource_dependencies_20261003.json)。

四题首轮两模型各一次均正常结束，8次尝试中6次有有效正式评分、2次为候选自行撤回兼容层后无法收集（6183／240d Coder），原null保留。[首轮状态快照](first_round_status_20261003.json)记录补证前时点；当前1c1取消回归／评分遗漏已实测证实，窄材料修订已发布并通过实际五行及非作者核收；新版诊断单列，原raw不改，旧binding禁用，未来GPU须新binding，其余三题照常。GPU暂缓尚未开始的普通重复，优先新题／缺另一模型首轮；统一第二阶段同条件重复仍待安排，整个aiohttp探针工作未全部完成，不给稳定成功率或GPU退租结论。按[收口规则](../../overnight_watch_20261003.md)接续。

## 具体材料与验证边界

- [机器可读修订草案](revision_draft.json)保留七条原草案操作。`r2e-mr-990`起的编号仅用于本地解析，不是正式编号；草案中的未来路径不替代[正式发布绑定](publication_binding_r6_20261003.json)。公开/私有材料已按实际登记进入固定发布，不回写已审草案快照。
- [材料清单](material_manifest.json)：固定父材料摘要、当前评分材料身份、各题修订文件摘要及期望键增删。四题题号不变。
- [本地检查结果](local_validation.json)：调用现有生产摄入纯函数，检查文本重放、摘要、键变化和公开／私有分离；不是正式摄入发布、评分、actor 验收或训练资格。
- [cleanup 控制流隔离检查](cleanup_control_flow_check.json)：执行原 web.py 与 gold/C1/C3 补丁中的 `run_app`／`_cancel_tasks`，以 async generator 替代 Application/AppRunner 和网络。新增断言接受 base／gold／C1、拒绝 C3；base 仅通过此新增断言，原目标仍失败。此检查使用本地 Python3.12，不顶替正式 Linux/Python3.9 环境的58键验收。
- 修订前后差异分别在 `materials/<题目前8位>/statement.patch` 和 `hidden_test.patch`。公开读者只接收对应的 `public_reader_bundle.json` 与原公开工作树；不得接收本页、私有测试、gold、候选或验收矩阵。
- [准备脚本](prepare_materials.py)与[检查脚本](validate_materials.py)只在本包输出。草案冻结后，不用重新生成覆盖已审版本；后续修正需保留旧版本及其结果。
- [首版草案快照](snapshots/material_draft_v1_20261003/snapshot_manifest.json)完整保留首次非作者复核对应材料；[复核报告](reviews/non_author_material_review_20261003.md)不回写。[AIO-MAT-01 关闭复核](reviews/non_author_6183_correction_review_20261003.md)已接受当前摘要下的 Expected Behavior 句子修正，两段公开代码和评分材料不变。
- [CPU 验收计划](cpu_acceptance_plan.json)固定两题共13行评分矩阵与历史候选补丁摘要；F1／WR2 等原件均已找到并核对旧槽清单，无需重写候选。[公开命令清单](cpu_inputs/public_commands_manifest_v1.json)包含四题14条环境、复现及目标相关开发命令。4075已实际执行，原件见[结果清单](results4075_r069_20261003.json)；6183草案公开base／gold对照也已实际完成，见[开发结果](results6183_public_development_20261003.json)；两段分别区分空写入/提前EOF，公开protocol47通过。1c1／240d的公开开发检查已使用第五版入口完成，分别公开55／13通过，见[1c1结果](results1c1_public_development_20261003.json)和[240d结果](results240d_public_development_20261003.json)。这些仅证明开发路径，不是新隐藏材料评分。
- [正对照 actor 适配器](run_public_actor_control.py)沿共用固定版 devcheck，补丁由宿主 stdin 在 actor 启动前应用，不交付补丁文件给 CC。该适配器已完成非作者窄核与4075真机验证；devcheck 控制提示不证明题面实际送达，4075已另走原 probe_e2e 桩场景核实完整题面。
- [4075 fresh 公开静态阅读](materials/4075c653/public_reader_review_20261003.md)与[读者建议命令](materials/4075c653/public_reader_commands_20261003.json)只接触公开材料，核对9文件及最终题面 `c3253b92…` 摘要。两个示例可理解且与公开回归不冲突；header 名／值、请求／响应和 Python／C 的既有边界仍须保留。读者建议命令未执行，不计为 actor 或 CPU 通过；题主已用本包固定公开命令另做4075实际对照。另两份报告见[240d公开阅读](materials/240da100/public_reader_review_20261003.md)、[6183公开阅读](materials/61833518/public_reader_review_20261003.md)。

## 逐题验收矩阵与已知限制

### 4075c653

评分与 expected 不变，复用 [独立验收](../../r2e/aiohttp4075_acceptance.md)及原件 `runs/r2e_lifecycle_20260929/codex_status_check_20260929_1020/formal_v11/`。不重复七方矩阵。ALT2 为主正对照，ALT1 为备选；原 gold 按已修订要求应为0，不把它作为正对照。

新增工作限于题面：base 接受修正后的非法字段名，ALT2 拒绝；以 actor 身份执行并保存完整输出。正式公开题面与实际送达文本须绑定新摘要。三个 C 扩展预期 FAILED 键保留既有纯 Python 范围解释；若启用新的 C 扩展构建路径，须另核其 expected，不能把环境变化当候选错误。4075新结果已非作者核可接受，探针申请已接收，见当前题卡。

### 1c1c0ea3

当前094/095的取消清理P2P已完成实际59键与五行核收，见[当前入口](revision_1c1_cancelled_main_p2p_20261003/README.md)。以下保留080/081的58键历史材料依据，不覆盖新版。

新增测试复用公开 `patched_loop` 和 `stopper`，无需真实网络服务器。cleanup context 在 yield 后抛出新消息的 RuntimeError；必须实际走到 cleanup，且异常向调用者或 loop 异常处理器可见。不会强制与 gold 使用同一种路线。代码位于 `materials/1c1c0ea3/test_1.py`，差异只新增此函数。

新版本预期：gold／C1=1；noop／F1／C5／C3=0。C3 原 v5 得1，正是此次需要关闭的漏判；其余独立机制的候选继续保留。保存完整测试段、精确键集和异常／清理证据，不凭退出码或失败键名称推定原因。旧关闭顺序与后台异常报告断言不删。

### 240da100

选择 R-a 窄移除路线：私有测试中仅删除 `HttpClientConnectorTests.test_tcp_connector`、`test_unix_connector`，同步移除 expected 两个 FAILED 键。两项旧真实 client/server 路径受兼容改写影响而失效；本题代理端口、非示例端口、CONNECT 明确端口及其它31个旧有效键保留，总数为33。没有新增 skip，也没有改目标源码或把 FAILED 直接标成 PASSED。

此处不是宣称旧客户端／服务端兼容已修复。采用经已有行为证据支持的无网络 transport Future 复现作为目标相关开发路径，Future公开复现已由实际CC核base丢端口／gold保端口，相关公开代理13项通过；新材料的正式33键矩阵现已另完成。原件 `runs/r2e_lifecycle_20260929/inv/aiohttp_240d/pcheck_*.json` 多为 root 私有对照，不能冒充 actor 验收。

新版本实际结果：gold／AL1／SC1=1；noop／DG1／WR1／WR2=0。gold／AL1为两种端口路线，SC1为gold加decorator的兼容变体。正式复核已确认仅移除上述两键，正常请求保留端口，负对照能识别遗漏与重复。

### 61833518

评分材料不变，原 v5 gold／AP2／A1=1，noop／AP1／AP1m=0 的正式证据可复用。公开代码不再检查 `mock.call` 对象的恒真值；先检查实际 write 字节，再解析 chunked 线上数据，确认终止块在末尾且解压载荷完整。

此公开复现替换旧未定义 transport／compressed_data 的片段，不提供候选修法。目标相关开发路径选 protocol 层；其余真实 client/server 的 TypeError 不宣称已恢复，也不以无关 cookie 测试全绿作为本题条件。当前草案两段已由真实CC独立执行，base均失败、gold均通过，相关公开protocol47通过；最终085题面已经正式发布且真实首请求送达，CPU独立核查已接受，见[统一结果](reviews/6183_r085_cpu_coordinator_review_20261003.md)。旧v5六方完整日志也已按当前不变材料逐键读回，见[当前题卡](6183_current_card.md)。HTTP/1.0、gzip 等原登记范围不在本次扩大。

## 共用入口的具体交接

现有 `statement_text_replace`、`hidden_test_text_replace`、`expected_file_replace` 能表达上述操作，当前未发现必须先改通用工具才能准备材料的缺口。

共用发布者已完成正式登记：1c1的080/081替换040/041，240d用隐藏083/expected084替换051/052并登记082题面，6183登记085题面。没有同一目标重复叠加。第六版material_v18/pins_v19、855成员与CPU-b可信读回已确认；本包的新prepare从该版生成材料，受影响1c1/240d镜像已重建通过，见[准备原件读回](results_preparation_r6_20261003.json)。4075/6183只改题面，不重跑不变评分矩阵；其实际交付及评分复用身份仍分别核对。

“负责处理分类二的明确问题”统一维护SWE/R2E修订登记与发布；本包未使用990–996作为正式编号。4075已正式登记069进入 `cat2-cpu-r2e069-swe6-20261003-v1`，manifest `40ca2914da2be665754175954defe4bbecfdb31efc1ad394153c09acfb5f9f15`，material_v15／pins_v16。协调者已核CPU-b的812成员与可信48／216读回，本包再次逐成员核本地固定快照，4075 actual PreparedTaskFace、题面与不变评分身份均读回一致。CPU结果见[当前题卡](4075_current_card.md)。

240d/6183的fresh公开静态阅读与新登记采用相同材料SHA，复用已有意见。原版本四题派生镜像均准备通过、残留零；它们与新58/33键镜像分开记录，见[cpu_preparation.json](cpu_preparation.json)。[新增brief复核指针](review_handoff_briefs_20261003.json)按题固定新增内容、已执行公开命令与原件SHA；正式CPU矩阵与一次非作者结果核查已核收，两项新probe已登记并直接通知GPU，固定请求和交接回执由各题当前卡定位。

总协调已在CPU-b部署并统一真机核 `cat2-cpu-r2e070077-swe6-20261003-v1` 的builder修补：检查容器具有独占标签、2 CPU／4 GiB／512 pids限制，正常／非零／超时清理及异主保留通过。新prepare从该固定builder调用，显式传 `--job-prefix <本次唯一名> --container-cpus 2 --container-memory 4g --container-pids-limit 512 --cleanup-timeout 60`，仍经统一prepare名额；保留题目材料、env pins与sysconfig参数。各包不重复共享冒烟。该版本尚未含本包剩余草案，不为4075重建不变材料镜像，也不热切在途。构建daemon资源限制和Git修复的适用范围按[CPU资源入口](../../cpu_resources_20261003.md)与发布清单记录。

上述历史准备使用原CPU-b；当前它已销毁，新增工作只使用发布者分配的现存主机统一槽位与固定版本验收；就绪一题提交一题给统一 GPU 执行者，探针后分析和修复仍归本线程。

四题均保留 aiohttp 同仓答案关联登记；训练／留出不得跨同仓拆分。这一轮没有授予训练或留出资格。

剩余三题新prepare、baseline与评分使用已部署第六版 `cat2-cpu-r2e080087-swe8-git-20261003-v1`（manifest `ab0a3a13fd65e0ea4cd60541ea3b37b01196170477e25832df246f33ea208828`）及runtime_cpu_v2。该版继承已审Git/builder修复，并纳入本包080–085材料；已结束控制保留原版本，不机械重跑。
