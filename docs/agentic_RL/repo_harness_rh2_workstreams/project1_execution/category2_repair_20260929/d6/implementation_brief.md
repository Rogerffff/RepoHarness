# D6 实施 Brief：先让两道 mypy 的公开回归测试进入正式评分

2026-09-29。状态：**用户已批准，实施中；尚未完成新正式运行验收**。当前事实与授权依据见 [current_entry_review.md](current_entry_review.md)。本方案替代旧成本稿“默认先 MONAI＋Conan”的首片建议，不改写旧证据。

## 已批准范围与原方案依据

**推荐实施一个有界的 SWE 材料版本通道，首批只启用 mypy10424、mypy17071：保留原题面与原测试补丁，登记现成公开测试为 P2P，扩展 mypy 的受信 case 选择和对应文件保护，使 ingest、正式 actor 与 replay 使用同一有效材料，并绑定资格及版本诊断。** 首片仍使用原 `swe_f2p_p2p` 和 `binary_v1`；不开放任意 shell、不新增奖励算法，不自动迁移28题。

首片约涉及 **8–10个生产消费点、六组定向测试、至少6次正式 CPU 评分**；新216题材料集中，**其余214题的原包字节与摘要保持不变**。2026-09-29用户已批准共用机制，先验证这两题，通过后逐步用于其他需修订的题。后续按既有修题规则分片实施和复验，不因每次沿用本机制重新申请；新的任务目标、奖励或安全边界变化仍另行处理。

需要的决定只有这个共用实施范围。它包含下文明确的数据形状、消费点和兼容义务；不是要求用户再判两题已确认的收窄／unbound 语义。依据是统一标准 §5 对“SWE-Gym 修订机制的实现”的显式保留和 D6“实现前把成本与设计交用户”的要求。本轮已授权的题级准备、安装收口与复核照常推进。

| 选项 | 可得到什么 | 实际代价与限制 |
| --- | --- | --- |
| A：两道 mypy 起步（推荐） | 复用已有公开 case，验证仅参考变化也有正确身份／资格；不用写重复测试或改题面 | 必须补 mypy 选择式及文件保护；题级安装问题还需收口。 |
| B：MONAI5932 起步 | 在现有受测文件追加单独命名的数值断言，现有命令派生可直接覆盖 | 要把私有 shell 对照转成项目测试 fixture；只做它不能证明“只改参考、脚本不变”的资格失效。 |
| C：先 MONAI5932＋Conan11594 | 验证新增测试与真实工具链两类 | 比 A／B 多 CMake/CTest fixture、环境配方及精确参考绑定接缝；不适合作为共用入口最小首片。 |
| D：维持诊断 wrapper，暂不接正式入口 | 能继续准备题级证据 | 28题当前正式修复目标仍无法闭合；不能将私有后检当普通探针豁免。 |

A 的测试材料最小，不代表已经证明总工时最少。两题环境优先复用已验的09-19 `install_wave1`，不是新增配方；若恢复该配方时发现资产或候选生效问题，先补窄证据。B 可作为后续调整实施范围的候选，但不因 A 暂未通过就自动启用 B；保留 A 的选择／保护／资格反例测试，不把安装失败转成通过。不存在“换题更便宜所以永不修”的决定。

## 数据流与唯一材料来源

```text
冻结来源 archive + 原 T1/vendor/image pins
              + 钉住 SHA 的 SWE 修订单与题级文件
                         ↓ trusted ingest（从原件重放，不改原件）
public bundle + 有版本的 private grading + 原 validation bundle
                         ↓ EnvironmentPackage 有效摘要
同一 TrustedTaskController → prepare_tasks → 公开 prepared / 私有 host grading
                         ↓ 同一 build_grading_spec_from_host_view
            正式 actor 的冻结评分 / replay grading
                         ↓ 原 SWE parser + F2P/P2P 二值判定
           公共 report：联合结果；私有 sidecar：版本／分区／执行事实
```

沿用 R2E 已有“修订单前后摘要 → 从原件重放 → manifest 与代码 pin → 消费期重验”的做法。**复用纪律和运输层，不把 R2E expected-map 语义移植到 SWE，也不修改 R2E 在制品。**

推荐在 `s2/revisions/` 新建 SWE 私有修订单，由一个 loader 管理；一次只接受每题一条确定父版本的修订。多步编辑先在材料侧形成最终版，再登记一条父子关系，首版不做任意修订组合／插件注册／数据库服务。

首片输入已有 [题级材料清单](../swe_materials/first_mypy_bundle/materials_manifest.json)：10424 的两个 TypeEquals case 位于 `test-data/unit/check-isinstance.test`，17071 的 `testUnboundTypeVar` 位于 `test-data/unit/check-typevar-unbound.test`；两文件均不在各自原 patch 中，须显式恢复／保护。清单的 `suggested_eval_argv` 是材料作者建议，不是已批准命令；本方案保持原 vendor 前缀，只扩展受信 `-k` 并集，核实际完整 nodeid 集合，不顺便引入 `python -m`、`no:cacheprovider` 等无必要命令改动。

| 材料 | 首片登记的最少内容 | 消费约束 |
| --- | --- | --- |
| 来源原件 | instance_id、repo、base、来源 public/grading digest、原 test_patch SHA、原 F2P/P2P | 从已验 archive 构造原包后比对，不能把本次候选结果当原件。gold 仍仅在 validation 面。 |
| 修订身份 | revision_id、parent digest、修订类型、公开依据／独立证据链接、登记文件 SHA | ID 为材料身份，不占用仓库 `version` 或 `spec_vendor_id`；同题仍用原 source-qualified task_id。 |
| 有效测试 | 首片 `test_patch` 与来源逐字节相同；将来修订补丁须给完整有效 patch、前后 SHA | 将来追加／替换测试也是在 immutable base 上构造有效 patch；原补丁留存。首片不接受测试替换操作。 |
| 有效参考 | 原 F2P/P2P + 精确新增 P2P nodeid；原／新增集合分开保存 | 去重、F2P/P2P 不重叠，必须能从真实收集／执行映射到节点；首片不删原参考、不改原分组。 |
| mypy 执行选择 | 新增 case 名与准确文件路径、base 文件 SHA | 只能追加已登记的公开 case；用代码生成原 case 与新增 case 的并集选择式，禁止登记原始 shell。对 case 名字符集验证，不能靠 shell quoting 后就信任任意字符串。 |
| 恢复／保护 | 原 patch paths ∪ 新增参考依赖的 `.test` 文件 | 将公开基线文件恢复后再 apply 有效 patch，均进入既有受保护路径。若引用支撑文件影响判定，一并登记所需范围；不可让 candidate 改写验收 oracle。 |
| 题面 | 首片原题面 SHA 和有效题面 SHA 相同 | 后续 R-f 使用同一修订单增加经过批准模板审查的 `statement_replace`，新内容只进入 public bundle；私有依据／测试／gold 不进 prompt。当前不启用该类型。 |
| 参考绑定 | 首片为空，沿用原 parser 可识别的精确节点 | 后续 Conan／DVC／Pandas 如需绑定，登记准确 alias→节点组、parser/绑定版本及 SHA，接同一 builder；不在 replay 另设特例，不做猜测式 unescape。 |

**模型选择建议：**新增一个仅修订任务使用的 SWE 私有 schema（可继承现有 v2 字段与校验器，示意名 `PrivateGradingBundleSWERevision`），包含有效 v2 字段及上表修订身份、原参考、新增选择／保护资料。未修订任务仍序列化为原 v2，摘要不变。新增判别类型进入现有 `HostGradingView` 联合及 schema registry。`EnvironmentPackageV1`、公开 `RolloutTaskView`、prepared manifest、`GradingReport` 不需要为首片换 schema；已有摘要字段足够绑定新私有包。

新私有模型只能接受首片支持的修订操作。后续测试替换、题面替换与绑定按各自切片实现，不先加入无人消费的自由字段。设计已给出它们如何复用本通道，不声称本首片完成这些能力。

## 入库、激活与两侧消费

1. **原 `s2/ingest` 和原 manifest 保留。** 新产物写入独立修订目录；复用现有生成器核心与 R2E 的封板／回读操作顺序。新增修订单 SHA pin 和修订输出 manifest pin，原 archive、vendor、image pins 不改。不能重写历史目录以便“沿用路径”。
2. 新集包含原216题，首片仅2题有效私有包／环境包改变，其余214题保持字节和摘要；来源重复簇仍按原件记录，另列有效材料变化，不借修订重新拆分仓库或任务身份。生成这一小文本集不意味着重跑216题。
3. 采用现有“代码 pin 指向唯一受信产物”的激活方式。先生成、核审新集；实施验收版本把可信 loader 的产物路径／manifest pin 指向新目录。首片只 `prepare` 两道题。无需新增任意 `--materials path` 运行时旁路，也不为当前需求建材料选择平台；旧代码＋旧 prepared／原件保留历史复现能力。
4. `trusted_prep` 与 replay `prepare` 继续走同一 controller。新 host grading 联合在 `prepare_tasks`、私有 loader、`PreparedTaskFace` 和 replay 均重验；公开 prompt 不出现修订测试、参考 ID 或私有原因。只改参考仍改变环境包／host artifact／prepared manifest 的身份，不能混用旧 prompt metadata 或旧 candidate 账本。
5. 同一 builder 用有效材料生成完整 eval、root setup、candidate test、安装／测试两段脚本；同一解析闭包捕获有效参考。供应默认仍关闭，两段字段需静态／单元核一致，无须为首片启用网络供应。
6. 正式 actor 的冻结候选导出、hygiene 和 grading join 使用同一有效包。冻结工件仍携带原 task_id＋本次环境包摘要；复用旧候选重评分必须明确新材料版本，不更改旧结果。题面或公开开发条件变了，要观察模型行为时另开干净尝试。

## 身份、分区报告与环境资格

**不改 reward。** 有效 F2P/P2P 的联合结果仍由现有 `parse_eval_log_v2`／SWE helper 计算，公共 `GradingReport` 保持一份联合结果，`grading_semantics=swe_f2p_p2p`、`reward_scale_version=binary_v1` 不变。不引入要求全部项目测试通过的新判分规则；完整测试 RC 和非参考失败仍要解释。

共用 spec 增加有类型的私有修订上下文（有效材料摘要、修订号、原／新增参考分区）；manager 的现有 diagnostics sidecar 输出这些元数据，并按现有 verdict 的 success／failure／missing／skipped 列表分区。它是该次修订运行的“原参考投影”和“新增参考投影”，不是复刻历史原始评分。精确原始状态仍可由完整日志和冻结 parser 核对，不把成功桶擅自改写成全是 PASSED（SWE 原规则也接受相应 XFAIL）。首片可以不增加 `EvalVerdict` 字段，不在 parser 闭包内写诊断文件。

在 spec 构造时确定 `grader_version`，附 parser＋修订版本；侧车与 replay 行记录有效 public/grading/environment digest、修订单 SHA、原／新增分区和实际选择式。准备失败、超时、安装失败等早退也有版本标识；判定尚未发生时分区结果为未执行，不能用空列表表现为全部成功。

**资格推荐显式加一个可选身份字段，而不改变 `scripts_digest` 的旧含义。** 给内部 `GradingEnvSpec`／`EnvQualification` 加 `grading_materials_identity`，由有效 grading digest、parser 版本、绑定版本（首片无）规范化计算；在 replay 资格账本载入与 manager 对照中贯穿。旧 v2 双方为 `None` 时保持原行为；新修订 spec 必须与新资格精确匹配，旧账本缺此字段不能赋予新材料资格。仅参考／parser／绑定变化时也因此失效；脚本和镜像仍照旧分别比较。公开题面变化已进入环境包身份，不能继承旧模型尝试的能力结论；题面本身不决定评分环境是否具备执行参考的能力。

这沿用现有全局失败归因规则：资格不足时不将未知环境故障归为候选错误，不新设训练丢样策略。恢复正确身份后可重验资格；不得静默吞掉不匹配。首片不需要更改公共 grading 契约、在线奖励或训练消费规则。

## 文件归属与验证面

实施时由一个明确的共用机制负责人修改下列生产边界，题级负责人只交输入材料。本轮文档作者没有修改这些文件；实际实现分工由主线程协调，不自动沿用共享文件写权限。

| 文件／边界 | 首片改动或核对 | 主要维护测试／验收 |
| --- | --- | --- |
| `envpack/bundles_v2.py`、`registry.py` | 新私有修订 schema、来源映射、原 v2 兼容 | `tests/envpack/test_bundles_v2.py`；旧包字节不变，非法分组／身份拒绝。 |
| `envpack/ingest_swegym_lite.py`，小型 SWE 修订单 loader／生成脚本 | 原件重放、登记 pin、修订 manifest、只改2题 | `tests/envpack/test_ingest_swegym_lite.py`；错 parent/base/hash、孤儿修订、半写、篡改和重复 ID 反例。 |
| `envpack/training_view.py`、`prepared_tasks.py` 消费边界 | 新联合、来源重验、上下游摘要和私有边界；prepared 格式尽量原样复用 | `tests/test_w2a_trusted_views.py`、`tests/test_w1b_prepared_tasks.py`；新私有文件、旧 manifest／旧 metadata 混配拒绝。 |
| `envpack/spec_vendor.py`、`adapters/slime/prepared_task_face.py` | mypy case 并集、额外基线文件恢复保护、共用 spec 与全部脚本一致 | `tests/adapters/test_w1b_prepared_task_face_v2.py`；实际 case 选择、跨文件参考、候选企图改测试、旧任务命令不变。 |
| `grading/manager.py`、`adapters/slime/replay_grade.py` | 材料资格身份、统一诊断、早退版本；replay 行与资格 loader | `tests/grading/test_manager_unit.py`、`tests/adapters/test_replay_grade.py`；仅参考变化、旧资格、失败／缺席／skip／早退和正常对照。 |
| `envpack/trusted_prep.py`、`scripts/replay_grade.py` CLI；正式冻结消费 | 通常只需接线验证，不预设新增 CLI 参数；真实 prepare／load 调共同入口 | 两种 prepare 得到相同内容身份；`tests/adapters/test_w3a_formal_grading_freeze.py`、`test_w3a_trusted_projection.py` 核冻结材料 join。 |
| `envpack/scoring.py`、`contracts/grading.py` | 首片预期不改，定向证明评分语义保持 | 旧／新共同解析的正负日志对照，reward/semantics 不变；不是机械重跑无关测试。 |

新增测试应针对真正风险，不写只复述字段赋值的测试。最小代码验收覆盖六组：原件与篡改、旧材料兼容、CLI／正式消费者一致、选择与保护、资格身份、报告分区与早退。改公共类型后搜全消费点；没有变更的 R2E 保留一组兼容哨兵，不能用 R2E 正在变化的材料当固定 oracle。

## 真实端到端验收与成本

首片至少 **2题 ×（noop、gold／可信正确修法、已证错误候选）= 6次修订版完整 CPU 评分**，预期联合 `0/1/0`；新增 P2P 在未修 base 上应通过，在目标退化上失败。若可信替代正对照替代 gold，保留 gold 的实际结果，不能省略事实。两题的安装前提和旧候选 bytes 由题级材料包提供；[安装复用记录](../swe_materials/first_mypy_bundle/installation_reuse.json) 已指向 `install_wave1` 的 image／wheel 摘要与历史正式验收，不重跑无变化的环境诊断矩阵。新 D6 材料版的6次正式评分仍必需。

每次核以下事实：候选实际交付字节、真实测试收集／逐参考结果、新增 case 确实执行、恢复／保护文件与实际材料一致、安装各相关子命令与最终作用对象、完整测试退出码、缺席／skip、资源／终止分类、两层容器清理。仅外层命令0或 reward1不算闭环。新增公开测试在 base／gold／错误候选的行为控制可复用现有适用证据，但新有效版本必须经正式评分重验。

另做两题真实 actor 开发入口核对，使用既有桩端点／固定命令方式，不需要自主模型或 GPU：同身份、激活环境、相关安装／公开测试、冻结导出与 grader 接线。正式 actor 与 replay 的 spec 字节一致可以复用，不要求把6次评分机械翻倍。若 actor 开发配方未变且已有同版本完整证据，可定向补修订运输与冻结 join；两题已知安装失败必须解决或有足以说明正确候选实际生效的完整窄证据。

| 工作块 | 工作量级 | 主要不确定性／可复用部分 |
| --- | --- | --- |
| 两题材料准备 | 小：既有3个公开 case，不写新测试逻辑；逐节点来源、SHA、原／新参考清单及正反候选 | 节点实际名称／参数展开、候选安装问题。题级负责人可现在完成。 |
| 共用版本通道 | 中：约8–10个生产文件／核心消费点，另一个小型修订单 loader 与生成入口；不改公共 report schema | 类型联合、manifest兼容、旧214题字节保持；大部分 prepared／冻结运输已有。该范围估计不等于确切最终文件数。 |
| 选择、保护、资格与诊断 | 中：mypy 专用选择扩展及既有 manager/replay 接缝；六组定向测试 | 公共测试不在原 patch 路径、仅参考变化资格误复用、早退丢身份。无需新服务或新状态机。 |
| 真实验收／独立复核 | 至少6次完整评分＋两题开发入口窄核；一轮独立验收 | 准备／安装通常比测试本身贵；不能把 MONAI／Conan 的数百秒准备成本当 mypy 实测，也不能只按测试秒数报价。 |

以上给的是可复核工作块、文件面和运行次数，不承诺尚无实测依据的工时。先完成材料与一次安装诊断，即可用该题真实阶段耗时更新 CPU 估计；沿用用户“不设会话／正式评分／CPU预算”的规定，不据此取消每次运行的技术 timeout、清理或预算记录。新材料产生的全量216行文本兼容核对很便宜；没有理由为本首片重跑全部216题或自主模型。

主要风险集中在三处：新增参考未真正执行／被候选篡改；actor与replay材料分叉；旧环境资格套到新参考。上述验收都直接针对这些风险。安装配方、解析绑定或真实工具链若超出首片，按具体题另立窄项；不要为了修共用入口一次实现全部修订种类。

## 下一切片与停止条件

- 首片达到正式 `0/1/0`、新增参考完整执行、actor/replay身份一致、安装问题收口及独立复核后，两题可交第2类负责人逐题确认转类；这仍不是自动训练授权。
- 后续先接 MONAI5932：在同一注册器增加受信测试补丁替换类型，只消费有公开依据、在基线上可重建的有效 patch，复用首片身份／诊断／资格。原／新增测试分列，至少再做 noop／正／误三次完整评分。
- mypy15184 需要 R-f 题面类型：新读者核完具体改文后，使用同一来源／父版本登记进入 public bundle；验证 prompt 实际交付。首片不假称已经支持。
- Conan11594 与部分 DVC/Pandas 需要精确参考绑定：待同一共用 parser 接缝有版本化绑定后再正式验收。首片不迁移诊断 wrapper，不扩大 vendored parser 总体规则。
- 当前继续实施并完成首片验收；通过后按用户授权逐步处理其他需修订题。目标仍不明确或修订不能收敛时，记录具体证据与解除条件；不因共用依赖停下无关题。
