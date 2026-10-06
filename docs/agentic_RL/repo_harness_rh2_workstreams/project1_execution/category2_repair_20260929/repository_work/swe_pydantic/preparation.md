# Pydantic 六题：当前准备入口

2026-10-04接续；既有材料和原件日期保持2026-10-03。题主为`SWE | Pydantic 题目修订`（`01a0fd62-62c8-7cc3-b49f-e959fca60a14`），负责5662／6283／8316／8511／8567／9066六题；8793继续归原探针线程。R27命令目标窄修已发布部署并核收ACK，旧R26阻断保留，接续见[10月4日检查点](continuation_checkpoint_20261004.md)。用户已批准三方流程并恢复实验，历史[暂停记录](pause_checkpoint_20261003.md)保留。

**最新：六题原固定探针及题主分析、独立复核均已ACK；8511的v2修订补验也已闭环。** R27四候选177参考CPU实际奖励0/0/1/0及非作者验收通过；原Qwen完整FP在cpu-a另作实际177参考补评分，旧173通过、新4失败，正式0/tests_failed、非infra，109原件/435,098字节及独立25项检查核收，固定请求ACK、active清空。见[原完整FP新版核收](model_audits_20261003/8511_original_fp_v2_regrade_acceptance.md)。本轮新模型采样0；各题单次结果不授训练、留出或稳定能力结论。

**8511原Coder0、原Qwen旧173/raw1保持；新材料准确拒绝Qwen的合法字段回归。** [真实四项诊断](cpu_acceptance_20261003/8511_fieldinfo_retention_diagnostic_v1/actual_v3_readback.md)和[私有v2](tasks/pydantic__pydantic-8511/revisions/pyd8511-behavior-v2/README.md)已核收，原173保留并新增4P2P。R26测试文件目标遗漏的false报告/hold保持；R27仅修精确选择并重新发布部署，21材料不变，固定输入/上传及独立delta通过。[正式CPU矩阵](cpu_acceptance_20261003/8511_fieldinfo_v2_targetfix/actual_matrix_semantics_20261004.md)为noop0/gold0/narrow1/Qwen源码0，非作者与题主核收；随后[原完整FP实际补评分](model_audits_20261003/8511_original_fp_v2_regrade_acceptance.md)同版得到0，原完整FP、452项baseline和实际stdin字节身份均已核。原请求ACK/revision5，题目progress26、phase=probe、active=null。前置独立核查通知发送时序已核，书面报告事后落盘的界限保留；不追加模型或CPU重跑。

**六题均已完成对应固定版本范围的CPU验收和本次GPU交接；8511新覆盖缺口的材料、177CPU与原完整FP补评分现已核收。** 8316最终CPU组合核收通过，后续两模型144参考各全过；Coder失败临时文件保持，Qwen仅源码，无失败文件。6283 R19四行奖励0／1／0／0，每行41个正式参考齐全，Python3.8.19/core0.42.0下旧Qwen源码负对照确实破坏PrivateAttr可信构造默认值；[498原件及清理题主读回](coordination_20261003/6283_v2_formal_owner_readback_v1.json)通过，[非作者实际核查](reviews/non_author_6283_v2_cpu_review_20261003.md)通过并核收，旧source/base公开actor有限复用边界已核；生成器静态核查及525绑定读回通过。原Qwen完整FP现已在code_v8/v2材料下实际补评分并获执行独立复核和题主核收：安装RC0、F2P2/2、P2P38/39，新增PrivateAttr节点因TypeError失败、奖励0，新模型采样0；见[原FP补评分与语义结论](model_audits_20261003/6283_original_fp_v2_regrade_acceptance.md)。新Coder首臂实际install0/test0、41参考全过，完整轨迹与159绑定已核收：专门可信构造保留合法私有状态，附带失败调试脚本另记交付缺陷。见[版本续作核收](model_audits_20261003/6283_coder_v2_continuation_acceptance.md)。returned回执已ACK，活动指针已清；后续重复按覆盖门槛另排，不作同求解条件双模型比较。旧R7、旧GPU安装RC1/raw1及安全partial原件保留。

8316 R14前五行0／1／1／1／0获[部分核查](reviews/non_author_8316_partial_cpu_review_20261003.md)通过；第六行在测试前保护300秒超时，infra/reward=null保持。R20仅对本题和DVC9395固定材料／精确grader将准备预算300→900，[实际支持核收](coordination_20261003/8316_r20_support_owner_readback_v1.json)、输入／派发guard增量独立核查及七上传成员／28复用材料SHA回读通过。原广域hold已原字节归档，[具体范围处置](coordination_20261003/cpu_hold_scope_disposition_v1.json)允许6283 R19和8316 R20各一次固定版本实验，不要求另一题先成功。6283自然结束且清理读回后，8316唯一作业`pyd8316-formal-20261003035447-r20-f5f0f`已派发公共槽；十九行实际全0、各144参考、2464原件及清理读回通过；公开actor实际三命令0／1／0、9项原公开测试通过、32原件与首请求字节及清理核收完成，见[实际矩阵和语义](cpu_acceptance_20261003/8316_r20_resume/actual_matrix_semantics.md)。[最终组合非作者核查](reviews/non_author_8316_r20_combined_cpu_review_20261003.md)及题主核收通过，[固定探针](tasks/pydantic__pydantic-8316/probe_request.json)已提交并实际通知。首个新infra或清理未知立即建新hold停止新派发，不自动重试、自由增预算或热换已封材料。

**5662本次首轮交接及两候选语义已核收：新Coder安装／测试RC0、129正式参考全通过，一般NotImplemented委托修复有效；旧Qwen原完整FP在权限修复后同129参考全通过，没有新Qwen采样。** [当前双候选报告](model_audits_20261003/5662_coder_versioned_two_model_acceptance.md)记录完整15工具、137证据绑定及强提示题面的诊断限制。本次returned回执已ACK、清活动指针；重复按覆盖门槛另排，不作跨求解环境的模型能力／效率比较。[阻断范围处置](coordination_20261003/5662_grader_block_scope_disposition_v1.json)仍仅阻断旧425a grader，当前总账裸旧镜像SHA保持。旧安装RC1/raw1、有限来源补证及旧复评缺grader采样／关闭后网络原件不回写。8511／8567／9066的两模型首次执行、实际镜像/安装及题主分析已核收并ACK；8511新字段保留缺口另走窄诊断，原Qwen1不授完整正确。没有题目因发布、提交探针或单个raw1获得训练资格或标为整体处理完成。

| 题目 | 已准备的修订 | 当前验收范围与下一步 |
| --- | --- | --- |
| [5662](tasks/pydantic__pydantic-5662/card.md) | 普通 matcher 委托，新增独立 F2P；原 ANY 与旧参考保留 | R7四候选0／1／0／0及CPU／actor已核；[本次两候选核收](model_audits_20261003/5662_coder_versioned_two_model_acceptance.md)确认旧Qwen原FP修复后安装0、129参考全过，新Coder实际安装／测试0、129参考全过且通用修复有效。returned已ACK清指针，旧失败保留；跨求解环境不比较模型，公开强提示限制独立定位诊断，重复及用途待。 |
| [6283](tasks/pydantic__pydantic-6283/card.md) | v2保留非42相等F2P，新增PrivateAttr可信构造默认值P2P | CPU四行0／1／0／0及41参考、原件、清理和有限公开actor复用核收通过。原Qwen完整FP同v2实际评分0，合法私有状态回归；[新Coder与续作核收](model_audits_20261003/6283_coder_v2_continuation_acceptance.md)确认install0/test0、41参考全过，源码修复有效、附带失败调试文件交付缺陷另记。固定续作已returned并ACK、清活动指针；旧v1失败／raw1保持，跨求解环境不比较模型，重复样本按覆盖门槛另排。 |
| [8316](tasks/pydantic__pydantic-8316/card.md) | 逐字采用云端已复核v3，原参考不变 | R14/R20及公开actor核收通过，旧保护超时null保留。[两模型首次核收](model_audits_20261003/8316_qwen_first_arm_and_pair_acceptance.md)：各install0/test0、144参考全过/raw1；源码均有效，Coder失败临时文件交付缺陷保持。交接ACK/active清，重复与用途待。 |
| [8511](model_audits_20261003/8511_original_fp_v2_regrade_acceptance.md) | 原173保留；v2新增4项字段保留P2P，共177，R27恢复精确测试文件目标 | 四候选正式CPU0/0/1/0及非作者核收；原Qwen完整FP实际旧173通过、新4失败，正式0且非infra，原173/raw1保持。补评分请求ACK、active清空，109原件与独立25检查通过；后续重复和用途由总协调按覆盖门槛另排。 |
| [8567](tasks/pydantic__pydantic-8567/card.md) | v4保留，新增B03 F2P、B06/N3 P2P形成v5 | 原CPU/actor核收通过，旧infra/null及75保持。[两模型首次核收](model_audits_20261003/8567_qwen_first_arm_and_pair_acceptance.md)：各强制inner schema使2F/2P失败、raw0正确；Coder失败脚本保持，Qwen仅源码。交接ACK/active清，当前不需新材料/CPU，重复与用途待。 |
| [9066](tasks/pydantic__pydantic-9066/card.md) | 云端v1的stdlib dataclass默认实例保护独立为P2P | R14/公开actor核收通过。[两模型首次核收](model_audits_20261003/9066_qwen_first_arm_and_pair_acceptance.md)：各370参考全过/raw1，标量IP修复有效，dataclass保持；Qwen过宽fallback已纠正，依赖切换线索撤回。容器IP旧T3保持。交接ACK/active清，重复与用途待。 |

每题目录包含完整原／有效 `test_patch`、公开基线测试文件、固定候选、安装配方、机器可读 [revision.json](tasks/pydantic__pydantic-6283/revision.json) 和 `result_manifest.json`。早期离线检查只验证材料提案；后续实际激活和部署以各题发布回执、固定版本及CPU记录为准，不以早期 `result_manifest.json` 推断。全部公开题面与 public_hints 保持原输入。私有测试、gold 和语义分析不得交给 solver。

## 首轮离线轻量检查

- 六题缓存 public/grading 内容与原 ingest 逐字段一致；base_commit 与已有身份记录一致。新记录固定单行字节哈希、镜像摘要和父材料 digest，未重新证明真实 actor 工作树。
- 原／有效测试补丁均在独立临时文件夹通过 `git apply --check` 与应用；74份非空候选补丁可在对应缓存 base 文件上应用，所得文件通过 Python AST 解析。
- 原测试函数／类的 AST 保留；8316 的 `test_camel2snake` 和8567 的 `test_plain_validator_plain_serializer` 是明确允许改变的原节点。参考不删除、ID无重复。
- [8316纯函数结果](tasks/pydantic__pydantic-8316/pure_function_result.json)仅使用当前本机 Python 与标准库，不导入 Pydantic／core。34个工件的字符串断言结果符合旧矩阵；未运行其它 P2P、pytest 收集、actor或RH2评分。
- 汇总原件：[offline_checks.json](offline_checks.json)。该离线轮未连接 SSH、拉镜像、安装项目依赖或执行远端实验；该首轮未包含后续独立材料核查和 CPU 验收；当前状态见页首与下文。

## cpu-a 准备（2026-10-03）

总协调已授权在新 cpu-a 上继续准备；旧机限制继续有效。执行约束以 [CPU 资源页](../../cpu_resources_20261003.md) 为准，所有 Docker 拉取、构建与运行走全机作业槽，每次使用唯一作业ID。本包只写远端 `packages/swe_pydantic/` 和自己的作业输出。

六题材料与镜像准备输入已上传到本包 `preparation_v1`，138个输入文件的字节数／SHA在远端逐项吻合。**六题镜像均完成拉取、八个公开wheel校验与断网派生构建**，base config ID吻合、base层保留；此前繁忙75记录保留。该镜像准备轮尚未运行候选安装及新材料正式矩阵；后续两题正式CPU、两题私有诊断见下文。来源与实际身份见 [新机准备记录](cpu_preparation_20261003/README.md)，不冒作历史canary镜像的逐字节重建。另已准备六份中性公开开发说明草稿，不改变原题面。

既有公开actor诊断绑定首份不可变基线 `cat2-cpu-r2e064065-swe5-20261003-v1`；当时本包核了外部manifest摘要、794个文件及48 R2E／216 SWE受信回读。该历史身份保留。

8511／8567私有诊断绑定第五版 `cat2-cpu-r2e078079-swe7-git-20261003-v1` ＋ `runtime_cpu_v2`，外部manifest SHA为 `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`；该历史身份保持。

**5662／6283正式新尝试使用第七版** `cat2-cpu-r2e088-swe12-git-20261003-v1`，外部manifest为 `f9dfcd16c9c88e4f514512e61781856b7d6f1a71a20b64cd1843d20546c5009b`。总协调已核cpu-a只读905成员及可信48／216读回，两题新增F2P与各自E10安装已登记。新prepared在本包新输出目录生成，不搬旧绝对路径、不改绑旧FrozenPatch；该R7版本不包含其它四题新断言；四题已在后续R14登记，旧两题运行身份保留。六题镜像与既有公开开发证据不因共享部署机械重做。[正式CPU入口](cpu_acceptance_20261003/README.md)说明输入、矩阵和实际范围。

**6283、5662 已在CPU runtime v2完成原材料公开actor诊断。** 两题UID54321、Python3.8、精确core、源码SHA与可写性断言通过；首个桩请求包含原题面及public_hints。原公开示例均按已知基线问题精确复现，已有公开测试分别为6283的41passed／3xfailed、5662的7passed；三命令全部执行，CC正常结束且收尾零残留。没有应用新私有测试或导出候选基线，不是新40／129参考评分。6283旧runtime缺torch的零请求失败及此前75原件保留，不记题目0分。[公开actor诊断记录](cpu_diagnostics_20261003/README.md)给出具体事实与路径。

**5662／6283 的非作者静态窄核已完成，无新增阻断：** [审查原件](reviews/non_author_5662_6283_review_20261003.md)核对了有效断言、公开依据、冻结正负对照与SHA。审查对象的 `revision.json` 未改；报告没有运行新节点、安装或actor。两题consumer已发布，两题本轮CPU均已获非作者核查通过。

**恢复后的独立核查：** [6283 CPU窄核](reviews/non_author_6283_cpu_review_20261003.md)核375份归档原件、40正式参考与391文件完整baseline运输，确认0／1／0及本run零残留；公开actor是固定桩，其适用范围与未测项保留。两个含空格参数的非参考节点被parser截断，不影响当前40参考；已按独立`cpu_support`请求交发布者，不把42个parser键写成42个有效终态。baseline环境字段null也不外推为训练lineage验收。[其余四题材料窄核](reviews/non_author_remaining_material_review_20261003.md)已完成，允许正式发布，仍缺各题完整CPU及actor验收。

[5662 CPU窄核](reviews/non_author_5662_cpu_review_20261003.md)独立核496原件、129正式参考及完整288文件baseline，确认0／1／0／0和本run零残留。any_only的原ANY与127项P2P均通过，仅新增普通matcher失败，旧漏奖被准确拒绝。本题另有14个非参考参数节点出现同根因parser截断／合并；当前正式参考评分不受影响，新增证据已整理为既有共享支持请求的补充草稿；CLI仅允许待输入请求接受补充，当前已领取状态仍不接受CLI补充；新增真实语料已一次定向发给发布方，原请求不可变范围和输入保持。

当前探针交接ID：5662为`swe-pydantic5662-behavior-v1-20261003`；6283为`swe-pydantic6283-behavior-v2-20261003`，旧v1已安全returned并ACK；8511／8567／9066各为`swe-pydantic<题号>-behavior-v1-20261003`。8316为`swe-pydantic8316-behavior-v1-20261003`；四题旧publish请求保留；共享parser缺口为`swe-pydantic-parser-space-support-v1-20261003`。固定输入和真实发送回执位于[coordination_20261003/](coordination_20261003/)，通知已登记；不重复提交或抄送管理线程。模型执行、发布和题目处理完成分别记录。

按[今晚接续约定](../../overnight_watch_20261003.md)，六题本次GPU固定交接均已ACK/清活动指针，首轮结果分析已核收；重复与用途资格仍待全局覆盖门槛。5662/6283旧Qwen原FP补评分与新Coder的求解环境不同，四个新Qwen首臂身份与配对范围见页首。当前8511有新CPU接续依赖：原Qwen四项字段行为回归已实际确认，私有177参考v2尚待发布、完整四行CPU及非作者验收；v1/v2零行为hold与v3具体执行位修复证据保持。不能沿旧无CPU待办快照宣布资源退租就绪。原R7/R14组合的六题1018参考没有命中已知parser空白截断，不外推全pool；原分、旧infra/null与所有封存报告保持。

两题Qwen原轨迹已完整初审：[5662](model_audits_20261003/5662_qwen36_a1_preliminary.md)实现公开的一般比较委托，当前范围未发现具体语义回归；[6283](model_audits_20261003/6283_qwen36_a1_preliminary.md)普通相等修复有效，但无条件删除合法PrivateAttr状态，后续新CPU真实依赖确认见页首。报告记录首次正确定位与纠错、验证质量、工具／请求／累计token、分段时间及实际并行证据；5662根因修法本已在公开prompt给出，不能包装为无提示独立发现。原初审保留安装RC1及当时checkpoint仅配置标签的限制；随后已核收wheel读取权限层和有限运营来源补证，不回写旧flags或冒作逐job快照，5662随后原完整FP实际安装／重评核收，6283原完整FP随后在v2新材料补评分0、安装RC0、旧40参考通过而新增PrivateAttr失败，旧R7原件与分数保持。首轮每模型一次不作稳定能力或成功率结论，后续臂与分批重复仍待；不以原raw1替代环境验收，不提前写退租就绪。

四题固定R14执行入口与输入的[非作者静态核查](reviews/non_author_remaining_runner_review_20261003.md)已通过，独立核66成员、四题本地prepare身份和41候选预期。静态报告保留当时范围；8511／9066随后完成实际验收和探针提交，8567保留旧infra失败，新的七行与公开actor已获组合核查并提交探针，8316五行完成后第六保护超时null，旧R14留下19行与公开actor缺项；R20新十九行及actor现已完成，组合非作者核查及题主核收通过，固定普通GPU探针已提交并实际通知；原hold已按具体版本范围原字节归档，R20十九行和actor读回已完成；新infra立即建新hold。原共享CPU支持ID为`swe-pydantic8567-control-protect-timeout-support-v1-20261003`，最新重复故障支持为`swe-pydantic8316-control-protect-timeout-support-v1-20261003`（R20支持已回执并ACK）；不改固定入口、预算、保护步骤或历史结果。

共享parser支持已按离线窄修范围核收并在总账ack。发布方回执为`runs/category2_repair_20260929/publication_cpu_takeover_20261003/support/pydantic_parser_space_candidate_receipt_v1.json`：v2修复非作者发现的opaque参数内状态词误认，35相关定界检查、七份原日志回放与非作者增量通过；当前40／129正式参考及原reward保持。它会保守跳过含方括号的后置原因，报告版本接线未实现，候选未发布或热替换固定release；含空格／opaque节点加入正式参考前仍须单独版本化验收。现有两题探针继续，不机械重跑旧CPU。

等待发布期间已完成8511的E10离线安装及新增四项继承／repr节点，以及8567的v5三个新增节点和保留的v4 F2P。首轮只取8511的noop／gold／narrow、8567的noop／gold／c3_reorder／upstream261／ok_post_attach；这是**私有root安装与行为诊断**，不是正式consumer矩阵、actor权限证明或reward。八份安装／收集均为0、实际版本及资源正确、容器零残留，节点区分符合预期；输入与原件见 [诊断记录](cpu_diagnostics_20261003/README.md)。新正式材料、全参考、FrozenPatch运输与非作者CPU核查仍待。共享维护者随后完成5662／6283的consumer并随第七版发布；这不改变本段R5私有诊断的历史绑定。

## 机器到位后的执行

优先用6283／5662的小矩阵验证新的材料消费，然后逐题推进8511／9066、8316和8567；就绪一题提交一题，不等待全仓结束。顺序可按镜像缓存与共享入口就绪情况调整。

固定正式入口和材料版本后，核安装各步退出码、精确Python/core与源码导入、全部参考逐ID结果、新断言实际执行、候选导出与清理。换宿主先核关键身份；复用已完成开发证据，只补受影响命令与尚缺的实际公开材料交付。独立核查由非本轮材料作者承担。

## 给共享维护者的具体输入

SWE D6 登记／发布由“负责处理分类二的明确问题”集中维护，本线程没有修改共享代码或 pins。

**维护者接收与复核状态（2026-10-03）：** 六题具体输入已接收，六题非作者材料窄核均已完成。R7保留5662／6283运行身份；四题publish回执及R14在cpu-a/c部署已核收。8511／9066正式CPU和公开actor获非作者核查并提交探针；8567原两行与新七行及公开actor组合核查通过、探针已提交，旧第三行infra/null保留；8316五行完成后第六保护超时null，旧R14留下19行与公开actor缺项；R20新十九行及actor现已完成，组合非作者核查及题主核收通过，固定普通GPU探针已提交并实际通知；当前R20接续已完成实际十九行及actor读回，旧hold原字节归档；新infra立即建立新hold。不为等待共享实现重跑已有74份候选补丁检查或旧矩阵；后续按实际版本及影响补验。[四题CPU记录](cpu_acceptance_20261003/remaining/README.md)区分已执行与待执行。

| 题目 | 原 F2P／P2P | 提案 F2P／P2P | 所需正式消费 |
| --- | --- | --- | --- |
| 5662 | 1／127 | 2／127 | 受信有效 test_patch 替换，追加1 F2P |
| 6283 | 1／38 | 2／38 | 同上 |
| 8316 | 1／143 | 1／143 | 受信有效 test_patch 替换，参考不变 |
| 8511 | 1／168 | 1／172 | 受信有效 test_patch 替换，追加4 P2P |
| 8567 | 1／158 | 2／160 | 受信有效 test_patch 替换，同时追加1 F2P＋2 P2P |
| 9066 | 2／367 | 2／368 | 受信有效 test_patch 替换，追加1 P2P |

原测试文件均存在于对应 base；完整节点、基线文件SHA、原／新补丁SHA、父材料身份与候选字节见各题 `revision.json`。测试命令不变，不新增摘要别名绑定。安装资产按题引用既有 `pydantic_v1`，不复用8793的core版本；新机恢复离线 wheel 时核版本、文件SHA和来源，云端等效镜像不冒作历史镜像的逐字节重建。

恢复后为8316／8511／8567／9066分别新增`publication_manifest_20261003.json`，固定当前题卡、修订单、完整补丁、安装配方、公开基线测试和全部候选的字节数／SHA；四份分别40／10／38／12成员。8511／8567旧`result_manifest.json`的题卡SHA属于追加私有诊断前的历史输入，不代表当前题卡；旧清单保留，新发布使用当前清单。新的非作者材料核查与逐题发布输入位于`reviews/`及`coordination_20261003/`，草稿不算已提交。

所有原件保留。按现行[三方流程](../../coordination_workflow_20261003.md)，题主仅通过`category2_task_board.py`维护本包逐题进度与请求；发布、GPU交接直接落账后通知登记接收方，不经过管理线程。四题修订单ID及SHA仍保留在不可变发布请求中；逐题总账已核收并改记R14正式consumer版本。此处不新增训练或留出准入。

8567两份正对照的非作者源码／语义窄核已完成：重排与事后补挂均保留PlainValidator跳过内层schema，未发现新的公开可证回归。复用旧v4独立证据，不要求多PlainValidator或题外自定义包装成为新公共保证；该静态意见当时未验实际矩阵；随后完整162参考及公开actor组合核查已通过。原CPU计划为前五主要候选、后四个B1/B2/B3/Python-only代表，其它旧v4适用意见保留。可选B03＋WrapSerializer交叉检查不是新增评分闸门。固定发布成员保持原字节，本报告通过不代表GPU/训练准入。

发布方06:44（新加坡时间）已领取共享parser-space支持，确认6283当前40参考／0-1-0不受影响，现有探针无需等待或重跑；将先用真实语料做离线复现和窄候选，不热改已封D1来源parser，带空格节点入正式参考前完成修复验收。题主补发5662同根因14节点／9非法条目语料，实际发送回执位于coordination_20261003；固定探针输入与旧报告保持历史字节。四题consumer冻结是发布方当前通知，不冒作cpu-a部署或正式CPU已验证。

R14历史绑定：`cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1`，manifest `51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8`。已核本地1220精确成员、四题已审发布清单及实际有效patch／F-P／各题E10登记；cpu-a部署回执与对应镜像ID回读通过。本地固定入口prepare四题分别144／173／162／370参考及actor/host spec一致，formal_v2输入66文件已逐字校验。8511首派75保留，后续实际验收与探针提交见页首；9066及8567矩阵后来完成；8316剩余十九行与公开actor已按新R20完成，当前组合核查范围见页首。新部署本身不等于验收。

6283的[私有属性保护v2原条件草稿](tasks/pydantic__pydantic-6283/revisions/pyd6283-behavior-v2/README.md)追加1 P2P并保留原40参考，[非作者材料窄核](reviews/non_author_6283_privateattr_v2_material_review_20261003.md)可接续。随后旧探针安全partial returned已实际核收并ACK，活动指针清除；原FP重评分与最小PrivateAttr观察未执行。15成员正式清单已在R19发布、回执核收并总账ACK及清活动指针。固定[新四候选输入](cpu_acceptance_20261003/6283_privateattr_v2/formal_inputs.json)来自实际冻结发布；本地prepare／独立输入核查和上传读回另记，发布不是四行CPU验收。实际四行及真实依赖观察已完成，最终非作者验收已通过，source/base公开actor仅有限复用；旧R7、原probe请求／FP和原raw1不回写。
