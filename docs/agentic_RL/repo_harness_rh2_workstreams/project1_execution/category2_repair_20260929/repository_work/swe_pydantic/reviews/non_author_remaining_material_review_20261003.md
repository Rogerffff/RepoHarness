# Pydantic 剩余四题：非作者材料窄核

2026-10-03 / Codex 非作者子代理。对象为 8316／8511／8567／9066 的当前材料；结论不覆盖其它题或后续改动。

**四题材料均可继续正式发布，没有发现新增题级语义阻断。四题目前均不能据本报告直接进入普通探针：正式 consumer、新版本完整参考矩阵、实际 actor 开发与公开交付及对应非作者 CPU 核查仍缺。** 8511 的 narrow、8567 的 c3_reorder／ok_post_attach 仍是完整正对照待验对象，不能将其私有五／四节点全过写成 173／162 参考全过。

| 题目与修订 | 本次判断 | 正式运行仍缺什么 |
| --- | --- | --- |
| 8316 `pyd8316-acronym-v3` | 逐字接续云端 v3；数字歧义未被断言选边；可发布 | Python3.8／core2.14.5 的正式安装、144 参考、新 consumer／FrozenPatch 运输、actor 交付 |
| 8511 `pyd8511-behavior-v1` | 四个新增 P2P 有旧行为依据；gold 三类继承回归应被拒；可发布 | noop／gold／narrow 的 173 参考正式矩阵、正式 E10 安装 consumer、actor 交付 |
| 8567 `pyd8567-order-old-behavior-v5` | B03 F2P、B06／N3 P2P 必须保留；已撤下 upstream261 正对照地位；可发布 | 两份不同机制提名的完整 162 参考与语义核查，正式矩阵、actor 交付 |
| 9066 `pyd9066-behavior-v1` | dataclass 默认实例拆成独立 P2P 合理；未再声称文档有默认实例示例；可发布 | 新独立节点、五候选 370 参考正式矩阵、Python3.8／core2.16.3 安装与 actor 交付 |

## 范围和已接触上下文

我没有参与本轮修订材料编写。已读仓库规则、10-03 三方协作流程、剩余流程第 3 节和本仓准备页，接触了题主提供的私有上下文、gold／错误候选、既有云端审查与诊断结果。因此这是**接续已有证据的非作者窄核，不是干净上下文公开读者或全题盲审**。公开题面及 public_hints 未改，本次不新增公开读者闸门。

本次只读本地材料并使用 Python 标准库检查；未 SSH、联网、使用 Docker、安装或导入项目依赖、调用模型、改共享代码／总账或发送外部线程消息。唯一写入为本报告和同名 JSON。A／E／F／H／N 适用于断言语义、参考保留、身份与证据范围；不审核共享实现、CPU／GPU现场、训练消费或全量安全边界。

## 共通核对结果

- 四份 `revision.json` 的 original F2P／P2P 与各自缓存 `grading.json` 逐项、顺序一致；effective 集合以原集合为完整前缀，无删除、重复或交叉混入。原／有效数量为 8316：1／143 → 1／143；8511：1／168 → 1／172；8567：1／158 → 2／160；9066：2／367 → 2／368。原 `test_patch` 与缓存私有原件逐字相同，测试命令和 Python3.8 声明不变。
- 34／3／31／5 份 controls 均仍存在，SHA 与修订单一致，非空补丁与登记的历史 source 逐字相同。没有删除旧工件，也没有把 `expected_reward_not_observed` 当实测 reward。
- 用标准库在内存还原原／有效测试并比较 AST：8316 只改 `test_camel2snake`；8511 无原节点改动、追加四节点；8567 只改原 serializer 节点、追加三节点；9066 无原节点改动、追加一节点。8567 的 v4 原测试体逐 AST 保留。后三题 `extra_tests.py` 与有效补丁中的新增函数完全一致。8316 无独立 extra 文件是 v3 在原 F2P 测试体内追加断言的设计，不是漏件。未据内存还原宣称真实 pytest 收集或 git／consumer 应用已验。
- 当前 `publication_manifest_20261003.json` 的 40／10／38／12 个成员共 **100 个**，路径、SHA、字节数均正确；material_version 绑定当前 revision SHA，参考计数吻合。旧 `result_manifest.json` 中 8511／8567 的 card SHA 分别为早期 `a0a315de…`／`687733b3…`，当前题卡为 `113783dd…`／`a4167ff7…`。这是题卡更新后的历史清单口径，测试／revision／controls 未失配；新发布清单已明确区别。正式封包应消费新清单，保留旧清单原件。
- base_commit 同公开 bundle／grading 相符；各题源码 pyproject 的精确 core pin 为 8316／8511：2.14.5，8567：2.15.0，9066：2.16.3，与镜像准备方案一致。四份 E10 配方均先消费候选 editable 项目，再从候选 pyproject 的 testing／testing-extra 导出并安装依赖；步骤失败会返回非零。镜像准备是带固定八 wheel 的新等效派生构建，不能称为历史镜像逐字节重建。

## 8316：缩写的一般要求及正式矩阵去重

当前有效补丁 SHA `b248daa2…` 与云端独立复核采用的 v3 相同。新增 11 条字符串断言来自题面的一般缩写分词要求或 base 已有行为：串中／两字母／多个／长缩写、下划线及数字相邻、末尾缩写。`ÜberHTTPClient` 的断开位置仍在 ASCII 字符 `r/H` 和 `P/C` 之间；它没有规定非 ASCII 字母本身如何划分词边界。`base64URLEncode` 也没有大写字母紧邻数字的歧义。没有新增 `A1`／`snakeV2`、单字母缩写、kebab-case 或 `to_camel` 修复要求。

除读取现有 [纯函数结果](../tasks/pydantic__pydantic-8316/pure_function_result.json)，我独立用当前 Python3.12.13／标准库在内存重放 34 个固定工件的 18 个参数及该参数门下的 11 条追加断言，结果与记录逐行一致：gold 与九份合理实现通过，noop 与 23 份错误候选失败。没有导入 Pydantic／core、运行其余 P2P、收集 pytest 或作正式评分；不能外推为新机完整 CPU 验收。原件中的 `failed_parameters` 记录触发追加断言的参数门，部分行的 CAMELToSnake actual／expected 相同；这不表示没有失败，真实失败位于其后追加断言。逐机制分析应读历史首条失败信息，不能只看该字段的值。

**可以按机制精简正式复验，但不能仅按 0／1 或同一首条失败合并。** 明确可合并的建议为：

| 正式保留代表 | 可引用旧证据覆盖的工件 | 合并依据与限制 |
| --- | --- | --- |
| `w_acr_max8` | `acr_max4`、`acr_max5` | 都给缩写长度设上限；v3 长缩写辨别该机制，三者旧 P2P 均全过。`acr3` 是下限误拒，仍单独保留。 |
| `w_count2` | `first_only` | 都给处理次数设上限；v3 三个缩写辨别该机制。`w_last_only` 只取最后一次，方向不同，仍保留。 |
| `gold` | `upstream_main` | 在本题规定及评分范围内同结果；后者额外支持 kebab-case，属范围外。必须同时保留 `keep_digit`，保护允许的另一数字读法。 |

其它已知机制仍须各有对照：位置限制／窗口、吞字符的匹配、前后下划线与内部下划线、数字条件回退、编码条件回退、输入长度条件回退、删旧小写→大写／末尾缩写／两条数字规则、词表特判、只修示例、只在症状出现时修。不能因它们都为 0 而合并成一行。九份合理实现无需全部机械复制正式评分，可复用其既有语义意见；正式小矩阵至少同时保留 gold、keep_digit 和一份不同算法（如 scan），随后按尚未被正式消费证明的机制补行。上述是预算建议，不改当前34份登记，也不要求发布前先跑完整34格。

## 8511：继承保护的分类准确

新增三类无本地注解的子类仅检查正常构造、取值与工厂默认值；并未要求 base 尚未修好的 inherited repr=False 生效。第四项只保护默认 Field 继续显示。这些是 P2P（旧行为不退化），原隐藏字段 F2P 仍独立保留；不绑定 `cls.__dict__` 或特定遍历实现。题面直接要求 `repr=False`；base 的 dataclass 文档保护 Field／default_factory 与继承验证，既有 R4 及本轮 noop 结果提供更直接行为依据。

[私有结果](../cpu_diagnostics_20261003/private_results.json)的 36 个引用原件 SHA 全部一致，重解析三个 `selected_nodes.out` 与摘要一致：noop 1 fail／4 pass；gold 3 fail／2 pass；narrow 5 pass。gold 三项失败都发生于创建 Child，错误为 `'x' is a field but has no type annotation`，符合继承回归；不是安装／收集失败。narrow 字节直接复用旧真实导出，与 gold 的差异是只遍历本地注解，仍须完整173参考验它没有其它回归。

本轮三候选 reset／初始文件／应用／editable／测试依赖／解释器／core／测试应用／收集各步骤均为 0；root UID0、Python3.8.19、core2.14.5、源码导入与补丁后文件 SHA 正确，2 CPU／4 GiB／PID512，清理列表为空。当前 revision／test／controls 字节与私有输入绑定一致，运行 image ID 与准备结果一致。旧 R4 的 pdm rc127、make rc2 保留；本轮只关闭私有安装执行疑问，不核销正式安装 consumer、actor 权限、完整参考或 FrozenPatch 运输。

## 8567：保留 B03、B06／N3，继续核完整正对照

B03 组合题面“一般顺序要求”与 PV 对未知内层类型的既有支持，检查 validator 输出和精确 Python／JSON 序列化；B06 只要求未定义内层前向引用被 PV 取代后可构造；N3 只保护 Python3.8 stdlib `typing.TypedDict` 被 PV 取代时的已有行为，不改变普通 TypedDict 政策。base `functional_validators.py:132` 和 validators 文档 66／70／134 行直接规定替代内层验证与顺序；noop 对 B06／N3 的实测通过是 P2P 分类的直接依据。三项没有内部 complete 标志、schema 结构或排序 helper 断言。

这三项必须保留。原 v4 测试体、原1 F2P＋158 P2P 全保留，新增1 F2P＋2 P2P正确。拒绝 upstream261 是公开行为不满足的结果，不能为了保存正对照而排除断言。A16／A17 源类型／类型参数 serializer 等既有范围说明不因本轮扩大。

私有结果的56个引用原件 SHA 全部一致，五份日志重解析一致：noop 两个 F2P 失败、两个 P2P通过；gold 四项失败；upstream261 只有原v4通过，新增三项均失败；c3_reorder／ok_post_attach 各四项全过。五候选安装／收集全为0、Python3.8.19／core2.15.0／源码及补丁后 SHA、镜像、资源、零残留均吻合当前绑定。这里有 **20 个节点执行**，不是162参考矩阵。

c3_reorder 通过移动 serializer 保留验证顺序，ok_post_attach 在最终 schema 上补挂 serializer，机制不同，均可继续作为完整正对照提名；历史v4意见可复用。本次未运行或最终认证162参考，也未完成它们在新范围下的完整语义核查。ok_pv_first_keep_sers 未执行新增B06／N3，仍是另一提名；ok_wrapshim 的 validation JSON schema 问题已有登记，不能重新纳入正对照。首轮正式5候选（noop／gold／c3_reorder／upstream261／ok_post_attach）可以验证新消费，随后按 B1／B2／B3 与 Python-only 等独立错误机制追加，而不是重跑旧31格。

## 9066：既有默认实例行为不冒作文档示例

新节点只取 `Model.model_json_schema()['properties']['point']['default'] == {'x': 1}`，不绑定 TypeAdapter、异常捕获或实现路径。原 IP IPv4／IPv6 两个 F2P 的测试体 AST 未改，原367 P2P包括不可编码默认值护栏全部保留。将云端 v1 混在 IP F2P 内的回归检查独立为一个 P2P，分区更准确。

直接依据是 base 已支持 stdlib dataclass 默认实例，且 `json_schema.py:1985` 的 encode_default 职责是编码字段默认值。dataclass 文档展示字段类型，**没有默认实例的公开示例**；当前题卡已正确收窄。云端非作者已核 noop／gold／fallback／upstream271／gold_catch_user_error 的 v1结果0／0／1／1／0；fallback 与 upstream271 两种机制可复用为对照，不能把本轮新独立节点当已跑。fallback 的前向引用异常穿出及回退分支 ser_json 配置缺口仍属已记录边界，不能拿它推导更广默认值规范。当前 E10 配方和 core2.16.3 身份材料可发布，真实运行待补。

## 发布与停止条件

本轮材料窄核已足够继续由发布方登记／冻结／部署这四题，不增加新审批或全套盲审。发布方仍应核实际共用 consumer 与正式输入身份；本报告不替代该职责。四题新清单均已通过字节检查，审查报告的最终 SHA 应在发起请求的固定输入中引用，不能把报告路径本身当字节绑定。

普通探针前须逐题完成当前版本的正式安装、全部参考逐ID结果、新断言执行、FrozenPatch／基线运输与清理，完成实际公开 actor 条件与交付，并由非作者核相应 CPU 原件。8511 gold 的失败必须仍定位为三类继承回归；8567至少一份有效完整正对照，且不同合理机制不被误拒；8316 两种数字读法均可通过；9066五候选保持0／0／1／1／0，不能以安装／收集错误充当候选0。若有版本差异，仅补受影响范围，不重做已完成旧矩阵。上述满足后由题主申请GPU；CPU环境通过、发布成功和本报告均不赋予训练／留出资格。

机器可读核对及材料摘要见 [同名 JSON](non_author_remaining_material_review_20261003.json)。历史运行与原件均保持不变。
