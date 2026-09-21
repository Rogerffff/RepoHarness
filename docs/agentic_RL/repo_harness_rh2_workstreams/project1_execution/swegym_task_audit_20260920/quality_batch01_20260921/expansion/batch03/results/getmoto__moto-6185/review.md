# getmoto__moto-6185 对照复审

结论：同意主审维持 `needs_review / static_review`、用途 `development_diagnostic`。公开合法深层S的gold漏修和非法非键S字典的旧错误路径回归，均有具体源码链支持，但仍是未执行反例。历史gold=1只说明现有参考通过。主CPU方案选“正常资源API、HASH名M、嵌套S=None”的base/gold Put/Get对照，不把新候选或正式actor验收强制放在该语义诊断之前。

独立性：本人initial SHA256=`68f3fd5b8cbc9e992cace54efab0fc2e89608dc68075e5b88d6f3c9e0b4601d3`，root于2026-09-20T22:03:11.721133+00:00确认整包封存并明确放行后，才读本题public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json，以及本题history/refs.json指定唯一旧记录 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_moto_2/records/getmoto__moto-6185.json`。没有追旧记录内master、repo_level_findings、mat、被提及其它题或聚合。initial保持原字节。本轮仍纯静态，没有项目import/执行、测试、安装、网络、Docker/SSH、模型或配额操作。

路径约定：ROOT=.；P=ROOT/runs/swegym_quality_batch03_20260921_v1/public/getmoto__moto-6185；V为对应private；E=ROOT/runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-6185。原阅读范围及原件SHA详见封存initial；environment_record自带gold/noop结果摘要的暴露继续适用，不称结果盲审。

## 决定性主张逐项核对

| 主张 | 复审判断 | 决定性证据与限制 |
| --- | --- | --- |
| 题面要求任意合法属性名S，None和深层map属于公开范围 | 同意 | user_prompt的两原例和deeply nested措辞；public_read在未读私有材料时也独立识别。公开旧S/N错误测试可读，不是私有新增契约。 |
| 新正例覆盖顶层S字符串、未覆盖题面NULL/深层 | 同意 | V/test.patch全部正例仅client put/get完整字典相等，输入pk:S val和属性S:S asdf。主审与本人均逐体展开唯一F2P；P2P清单不等于全部函数体已读。 |
| gold在主键名M时仍拒绝合法嵌套S | 同意，强静态推断 | table.py:257–259允许HASH/RANGE名M；gold递归两分支均传key，A→类型M→字段S使attr=M命中表键名单。本人initial的M:N与主审M:S是同一条件的不同合法标量版本，不构成分歧。未实跑。 |
| 非主键S字典值被gold“允许成功” | 拒绝这个旧概括；同意主审修正 | gold跳过SerializationException后，Item→LimitedSizeDict→DynamoType.size→utilities.bytesize(dict)预计报AttributeError。base原有校验可观测；不能把未报原错误说成成功落库。 |
| 任何update_item都必经该校验 | 同意delta撤回旧主张 | 追加逐行核P/base/moto/dynamodb/models/__init__.py:428–474：仅item不存在时用键data调用table.put_item；已有item走UpdateExpressionValidator/Executor或update_with_attribute_updates。Put、batch Put、transaction Put共享路径成立。 |
| 历史环境修复、现有分差可解释 | 同意，限原grader条件 | 原make init两轮editable构建/安装有完成记录；gold36 passed/rc0、noop1 failed35 passed/rc1，noop在新增合法put上失败，F2P1/1 vs0/1、P2P34/34。COPY/ENV、末命令rc或历史环境摘要本身都不代替这些原日志。 |
| 脚本/评分/交付身份对应 | 同意 | historical baseline.tar.gz成员、原getmoto/moto4.1 spec、prepared本题项/host第87行与V/grading相等；gold业务源码被projection包含、官方只恢复精确exceptions测试文件。无recipe/materials/binding覆盖。 |
| 与master相同就不算缺陷；同文件即可聚类 | 不沿用 | 旧记录这些结论没有改变公开行为要求；未读取master或跨题commit关系，也无需为了本题判定去追。 |

新增复核阅读为本题models/__init__.py:428–474、tests/test_dynamodb/conftest.py全文、tests/__init__.py全文、tests/helpers.py:1–12，以及原noop日志718–755。确认conftest只声明Table fixture，F2P不使用该fixture；测试包会导入sure相关helper。补足测试导入入口的阅读不代表真实actor依赖已验。

## 本人initial的修正与证据分级

**撤回对真实评分中失败遮蔽的过强推断。** initial说“将来前一个失败后一个通过可能被覆盖”；这只描述任意摘要顺序下字典写入的一般可能性，不能当本题实际pytest管线的结论。复查E/noop/...416532ff.eval.log:718–755可见PASSED汇总在前、FAILED在后；冻结parser按摘要遍历，因此不能以节点声明/执行顺序推出同键失败被后一个通过覆盖。当前可确认的只有36实际节点、35解析键、F2P1+P2P34参考键，以及两条含空格参数名同映`[set`；当前两条均PASS，未观察错分。赞同delta/card/record已经采用此限定；不将parser改版列为主CPU目的。initial封存原文保留，以本段为后续解释。

主审封存分析的mem峰值“MiB”表述已经在delta撤回。最终只引用resource.mem_peak_mb=224.422/252.023，resource_facts=null；单位定义未查，不换算。本人initial已保留原字段名，复审无新的资源结论。

证据没有因多个审查者一致而升级成实跑：M键反例和非键非法S路径继续是静态推断；历史RH2的安装、真实36节点和gold/noop分差是已跑观察；两者分别成立。未证明所有合理替代实现都接受、完整SDK错误顺序或全部相关回归。

## 选定的主CPU方案及运行边界

只选一个主语义场景：在正常SDK校验、显式region/虚假凭证、mock_dynamodb模式下，创建HASH名M、类型S的表，Put资源item `{"M":"id","A":{"S":None}}`，再Get并比较完整值；分别记录精确base和gold的API结果/异常及来源。预期二者均在合法嵌套S失败，这是待证预测。已有gold原评分可作为单独历史证据，不为证明此缺口强制开发第三份“正确候选”或机械构造错误补丁。若实际结果不符，应先检查SDK编码/代码生效再修订静态链；非键非法S回归作为次要后续，暂不扩展此主实验。

若使用固定grader重放，必须另建重定位summary/manifest（原副本仍指/work）、核目标镜像实际身份和historical baseline code-root/Python依赖、使用新run_id/输出；不回写历史ledger。所需本题派生image为sha256:03d0313ef99258a707b5218ca0fc91985dca2bcde321650e709365b8f2597720，scripts_digest为sha256:80f2f995f16033f90aa2624be1991aec547956228b0b9364614be1c72b32f64c，原install仍是make init，pins=72.1.0/0.43.0/24.1，原context/wheel payload本地缺失，当前镜像可用性未验。重放命令的唯一来源是原launcher/status/冻结driver，不能悄换当前生产harness。

正式模型actor仍需共同验收实际镜像消费、UID/HOME/cwd/PATH/解释器/权限和CLI消息。grader rh2grader/54322、candidate apply agent/54321、历史正确导入与deny_all执行都不能代替该门槛；但它不自动成为上述固定环境语义CPU诊断的前置。原资源字段保持cpus=2.0、memory_bytes=4294967296、pids_limit=512、shm_bytes=67108864、tmpfs_bytes=1073741824。没有因静态未知宣布题不可解，没有新增排除路径或批准训练/正式评测。

八方面的范围/未查项沿initial成立；复审补充了公开视角一致性、旧结论撤回依据和解析顺序限定。只写本review，没有修改initial、主审稿或任何源/tests/gold/reference/reward/expected。

## 对照阶段补充：解析缺席边界与同包关系

当前原运行无skip或缺席；失败摘要顺序的修正不使身份合并变成完整节点核验。冻结parser按空白取键，scoring的reference_missing/reference_skipped也仅检查该合并键；如果某个真实参数节点未产生可分别识别的状态，不能由同键另一节点PASSED证明两者均执行或通过。skip摘要的实际形状、顺序与缺席混合情形本轮没有运行观测，因此只保留核验边界，不宣称已证奖励遮蔽。

root在对照阶段提示后，本人在已分配三题精确原件核读：5960 gold新增scan deepcopy+index.project核心逐行存在于6185公开base的moto/dynamodb/models/table.py:846–850；6185 gold的attr参数、递归和主键名单条件完整存在于6408公开base同文件487–504。6408:839–842仍有deepcopy+projection，但改成返回值列表推导，不能称与5960字节相同。由此将“未核关系”补为公开源码包含/演变的有限事实，不推断Git祖先、重复题或真实solver泄漏，也不回写任何initial。没有读取本包三题之外的材料。
