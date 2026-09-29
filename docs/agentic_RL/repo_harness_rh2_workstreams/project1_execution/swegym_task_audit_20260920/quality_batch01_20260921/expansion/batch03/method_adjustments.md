# Batch03 方法与例外记录

固定11题，沿用根已验收的B3材料和环境清单，不重复16541个blob核验。所有公开/主审/reviewer均新上下文；同仓reviewer先封存整包初稿再开放任一结论。每题主审先封存本题无历史稿再开放本题history。历史聚合只按精确题ID取对象，不用head/tail猜结构。

四类既有入口分别为DVC安装wrapper、6题install_wave1镜像增层、50319原镜像加tasks映射bindings、51605原baseline campaign/default driver。运行审计不等于原输入；固定grader语义诊断与正式actor开发资格分开。33份预期封存稿与77份逐题产物只是最终目标，不提前记为已成。

历史代码版本：B3清单有baseline/dvc两个既存tar快照；协调者只读取其中prepared_task_face.py相关文本，确认各自test_globs为空、rollout取public.image。CLI相同不代表内部driver相同；后续私有角色按本题family读取归档或明确标注当前源码，不能混同历史执行字节。

原件范围澄清：inventory 列出的归档成员是父任务已校验的定位索引，不是源码调查的穷举白名单。私有角色可沿已经读到的调用链只读同一冻结归档的相关成员，并记录路径/hash/范围；不解包覆盖工作区、不导入执行。这不开放质量历史。DVC3665已据此区分执行节点、业务日志伪解析键、冻结引用，具体结论等待独立复核。

文档修正：6954未封存old_findings_delta首段曾误写历史放行的UTC日期；作者已在核对登记后纠正为2026-09-20T21:10:32.205491+00:00，并保留SGT对照。封存analysis哈希未变；不是提前阅读或重新封存。

输出校验采用“13个既有必需字段齐全”，不是封闭生产schema；mypy记录增加reviewed_at_utc不算缺陷。协调者首次临时校验使用exact-key比较产生2个误报，读模板后改为必需字段子集并重验0错误；没有为校验器删产物。

参数节点合并与错分分开：Moto6185真实noop摘要先PASSED后FAILED，且两个合并节点在既有双角色中都过。封存初稿之后，协调者据本题日志要求最终材料限制为身份粒度问题；不能仅凭last-write或人为排序宣称mixed状态被遮为通过。初稿不改，后续限定留在delta/最终记录。

## DVC整包独立复核后的收束

6954选择公开actor参数/lock链优先，保留int-only漏测线索而不强制双候选。3665私有helper与Windows行为分离，合理内联路线的实际误拒尚未运行。4785采用reviewer的405/404 base/gold窄对照优先，主审原生Requests/CLI差分保留降序；CPU只能验证响应选择和行为，不能裁决未明规格，404/403冲突不设武断oracle。更新仅最终card/record，初稿/历史差异/独立复核原文保留分歧。

晚题base包含早题具体实现，记录文本/核心逻辑关系；没有完整Git谱系或实际solver资产证据时，不升级为重复题、污染或泄漏结论。正式actor资格是模型开发门槛，不自动阻塞固定grader语义诊断；6954优先项本身才是actor公开通路检查。

## 安装证据与解析修订的精确作用域

Pandas50319封存主审核到原安装串用分号串联多个命令，RH2_INSTALL_RC只报告最后一步卸载的状态。安装成功不能只凭该RC；本题另有editable构建/安装输出、工作区导入及行为翻转共同支持。后续复核保留这一证据层次，不据脚本总体RC自动判所有安装步骤成功。

reference_v1的绑定修复按明确列出的完整节点生效。50319反斜杠引用已补齐，并不自动把另两组多成员短alias变成完整成员检查；114实际节点、110冻结参考、111绑定后解析键可以同时正确。本次合并成员均通过，不能据身份粒度丢失直接声称错分；未来缺席/skip诊断也须保留真实摘要顺序。以上均只读历史文本、未执行parser或项目。

## 封存后数字表述修正

Moto主审主动报告5960初稿把原mem_peak_mb写为MiB；root定点检索发现6185/6408初稿有同类表述。三份封存稿不改，作者在各delta明确限定为原字段与原数值、未核单位换算，最终记录不沿用未经证实的单位。固定profile的已知bytes→GiB/MiB标示与这项观测字段问题分开。Pandas50319初稿中None分支计数的局部描述由作者在delta修正为12；62/58及114/110/111总账不变。

Pandas两题delta与record的history_release_utc误用了SGT日期配UTC钟点；作者只将四处09-21T21…Z改为真实09-20T21…Z。root反向替换后重现四个原SHA，证明更正范围；两封存初稿未变。真实时序以assignments明确放行时间为准，未把撰写日期当UTC事件时间。

## Mypy复核后的实质纠正

15184公开初读C3及reviewer初判曾预期原SupportsIndex程序必然报错。复核沿is_same_type→双向proper-subtype→结构协议成员/绑定self追踪后撤回该预测；不同fullname不等于协议类型不等价。最终card/record/CPU以实际CLI开放判据收束，封存公开稿/独立初判保留原字节与被纠正轨迹。原例可能不触发不抹去已由原F2P证明的普通名义类消歧缺陷。

15139与15184公开base还包含10174关键Any检查排序，15184含15139的TypeType小写选择；root逐行复核，仍只称代码包含，不补造Git谱系或已发生泄漏。10174 record将“所有CPU前先验formal actor”改为诊断自身条件与模型开发资格分别登记。

最后Pandas reviewer首次spawn返回agent thread limit reached，未伪造角色/开放结论；Mypy reviewer完成后以fresh context重试成功，独立性要求未放宽。


## Pandas 待收束记录的字段校验

2026-09-20T22:05:08.104574+00:00：全批记录检查发现Pandas两份未最终收束记录共7个issue使用kind/detail/next_step，但缺少既有记录约定的category/scope/evidence_refs/proposed_action/status。保留原内容，协调者在独立复审后补齐最终record，封存稿不改。Mypy/DVC完整包通过本次校验；不把已知缺项隐藏为全批通过。


## Moto 三题协调裁决

2026-09-20T22:11:49.417478+00:00：6185因公开深层S漏修先诊断；6408和5960保留受限静态候选，不把邻接旧错误或有限覆盖自动视为任务无效。6408新manifest两版错误形态不同，不称已证gold新增回归；6185非法S是异常类别变化，未证明成功落库。6185/6408主实验只需base/gold，第三份合理实现降为可选后续；5960仅一份有目的的缺KEYS_ONLY候选，存储复读不再机械增加去copy候选。6185/5960 reviewer在最终review撤回真实-rA失败覆盖的过强推断：PASSED摘要先于FAILED，保留真实身份合并、skip/缺席未知，未观测错分。新增三条Moto源码包含/演变关系只用于上下文隔离，不证明Git祖先、重复任务或实际污染。


## Pandas 复审与记录收束

2026-09-20T22:14:39.224798+00:00：两题均先作语义诊断。50319公开None-or-format与唯一exact-format断言冲突，采纳reviewer将#24改issue；无gold正则绑定不能支持整体pass。两题#3查真实输入交付，应unknown，公开语义归#23。7个原issue及checks/disposition/usage补齐约定字段，保留原notes和暴露来源；这是记录修正，非新增运行证据。51605首项只需base/gold iterator对照，第三份合理修复及固定两False错误候选退为次级跟进；空str/bytes校验回归由主审先提出、reviewer复核。晚题公开源码含早题修复仅作为具体上下文隔离线索；旧hints_text与当前public_hints不是同字段/版本，不能相互替代。所有封存稿和最终review原字节保留。


## 最终元数据校验口径

2026-09-20T22:17:01.588721+00:00：最终11链/77件/33封存/11review/22放行门通过，字段校验同时检查checks的evidence_refs/by、disposition的evidence_refs/reviewer和usage.exposure_notes，稀疏编号及额外元数据合法。Pandas既有缺项已完成；三份Mypy最终record的#5按已核源码关系改unknown，历史完成摘要继续保留为快照，当前77件摘要另存。DVC已验收21件未变。210份原环境文件重算通过；dispatch_manifest_sha256对应dispatch.json内指向的batch_manifest.json，并非dispatch元数据文件本身。最终仅给4个非assignments聚合做摘要，避免自引用。全程无新runtime/模型执行，B4未启动。
