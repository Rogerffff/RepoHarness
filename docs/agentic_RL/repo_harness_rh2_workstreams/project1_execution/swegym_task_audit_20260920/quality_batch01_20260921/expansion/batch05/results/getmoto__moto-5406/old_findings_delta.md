# getmoto__moto-5406：自身历史解封比对

顺序已遵守：先独立完成并封存 `analysis_before_history.md`（SHA256 `35beb534748cc6d850550deecc699230c5399f5549dcc780701fd4d313bb4fcb`），协调者核验后显式解封本题 `history/getmoto__moto-5406/refs.json` 及其唯一旧记录。本稿没有改动初稿；没有沿旧引用阅读其它题、repo-level/聚合报告或未来历史。

唯一旧记录：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_moto_2/records/getmoto__moto-5406.json`，SHA256 `45a4a1f22dda7e16297942724f00774776f2a5e16b3a2074cdbe01611648dd78`。下表以其JSON字段定位；新证据位置及完整路径约定见封存初稿。所有新结论仍为静态审查或已存在原baseline执行证据，未做新项目执行。

| 旧主张/位置 | 处置 | 新的决定性证据与边界 |
| --- | --- | --- |
| `public_view.目标行为`、check2：地区被硬编码，初态含问题 | 确认 | 公开Table接收region却由helper写死East1；原noop日志683–693、753–775真正在East1/East2 ARN比较失败。证据升级为本题原baseline，而未核旧stage1引用。 |
| check1：材料对应且无本题必需的缺失子模块 | 确认，限定范围 | 精确base、gold/test原件哈希、host_grading_views第63行与当前grading对象完全一致；Terraform子模块与普通mock建表路径无关。actual image ID仍为null，不将材料对应扩写成实际镜像身份已完整验证。 |
| check3、issue“题面实际输入”：创建名和断言名不一致 | 确认 | 当前 `P/user_prompt.txt:39,54,56` 仍为两个名字。公开模型/旧测试要求保留实际表名，核心地区要求可消解；建议保留原件另做最小勘误，非拒绝题目。 |
| `public_view.约束`：只能改moto/目录 | 推翻过窄表述 | 当前public_hints只要求NON-TEST源码，未规定所有允许路径只能在moto/。本题合法修复确实在moto/，但不能将该实现位置当通用交付规则。原禁止改测试指令实际是否进入CLI仍待验。 |
| `public_view.公开材料无法确定的点`：“所有us-east-1位置是否要改，范围只能猜” | 推翻过强结论 | 题面与实际请求链指向TableArn；`responses.py:140`、model:1200–1207支持通用地区，stream record的awsRegion与服务兼容变量不是本原例验收目标。公开信息足以提出合理范围；其它相邻常量不自动变成必修项。 |
| check4、17：恢复不覆盖合法源码 | 确认并补执行证据 | 原gold投影included_paths仅model文件；N:161–201/G:187–227只恢复并注入T文件，setup成功。未扩展到所有候选形状或当前actor权限。 |
| check5：无重复、与其它19题不重叠 | 未核实 | 本轮禁止访问其它题与去重聚合，旧记录仅有路径而无可在自身材料核验的跨题证据。不继承pass，不因同仓或同文件推断关系。 |
| check6、9：安装可用、测到候选 | 确认原baseline范围；旧来源未核实 | 新读原日志make init成功、moto导入/testbed、gold源码差异与目标断言0→1；原stage1/repo-level运行未读。它们不能替代实际actor的UID/PATH/安装验证。 |
| check7、11：纯mock、无额外数据集与运行期网络 | 确认最小任务范围 | 全评分文件、mock包装及开发入口已读；原grader deny_all下完成。botocore服务模型/Python依赖仍须存在；不泛化为整个仓库不需资产或安装阶段永远无联网需求。 |
| check23及issue“P2P语义”：26个P2P ID在base全不存在，故不度量旧行为保持 | **推翻** | 静态AST精确对照：22个P2P改名；`test_get_key_schema`、`test_update_item_double_nested_remove`、`test_scan_pagination`、`test_scan_by_index` 4个ID在base已存在。补丁只有首项改变region/ARN，其余改名保持测试体；旧行为仍被这些测试保护。补丁后27个ID恰等于1F2P+26P2P，原日志全部执行且reference_missing/skipped为空。真正缺口是它们不测ARN地区，不是名字变化使回归无效。 |
| check24：没有强制gold内部实现 | 确认静态范围 | F2P及P2P调用外部boto3接口；完整断言已读，构造期直接按region生成table_arn是可解释替代路线。未运行所有替代实现，不声称普遍无误拒。 |
| check25：“常量改East2即可全绿” | 确认漏测机制；下调断言强度 | 评分文件只有一处TableArn断言，已改成East2；26项P2P不查ARN。新旧均未提供该错误候选实际运行结果，故只写“预期可能满分、待CPU对照”，不写已观测reward=1。此发现已在读历史前独立形成。 |
| check26及proposed_regression_tests：评分外有合理ARN/恢复回归 | 部分确认；部分未核实 | 已完整读create_table文件，East1 ARN断言43–45足以区分硬编码；已读backup/restore模型和相应测试，主要校验同一ARN一致性。旧提及STS集成和单独range-key文件未在本轮阅读，不把它们计入已审范围；已有create_table公开用例覆盖range key。 |
| check27：gold两行修复目标、无夹带；stream record仍写死不必否决 | 确认 | gold完整两处改动及所有Table创建调用路径已核；原baseline gold27项通过。完整题面组合、跨区/账户/流/CFN仍非执行认证。 |
| check29：hints含上游L569链接且默认对agent不可见 | **对当前版本过时；历史文件本身未核实** | 当前public_bundle的public_hints不含L569/GitHub链接；内容是通用操作指令。environment_brief说明bundle可见且CLI system投递未验，不能沿用“hints一定不可见”。未读旧hints原文件，也未检查真实actor可见镜像。 |
| disposition_hint=`ready_for_probe` | 不继承；改为有限静态候选/needs_review | 当前协议要求实际公开输入与开发侧条件；本题已有原评分baseline，缺actor事实、actual image ID及独立复审，并有具体单区域漏收疑点。不是环境失败或原题不可解，不从旧标签直接批准。 |
| costs.minutes=35 | 未核实、不迁移 | 本轮没有工具观测的token、费用或容器用时；全部保持null。旧估计不是本轮成本。 |

## 封存初稿的后稿更正与处置细化

协调者指出初稿把原资源字段 `mem_peak_mb` 的250.824/230.828写成了MiB。**后稿更正：仅保留原字段 `resource.mem_peak_mb=250.824`（noop）、`230.828`（gold），单位实现未核，不再换算或标MiB。** 证据为原 `R/workers/w04-3/ledger.jsonl:1–2`，不改封存初稿。这是元数据表述更正，不改变原两次未观察资源阻断的事实，也不变成actor资源保证。

历史比对没有改变独立初判的核心：缺陷真实，gold核心合理，单地区验收存在具体漏收风险，题面有可消解笔误，actual image ID未知，当前actor未验。新增的是对旧P2P解释的反证、旧hints时效的澄清及资源单位更正。

**唯一优先未来CPU实验**仍为：在另行授权且明确原baseline来源条件的单题环境，把ARN地区常量改为East2，记录原RH2的27项结果，同时运行公开East1 ARN断言；与base/gold对照，以判定“业务错误却获通过”是否实际发生。无需把流、CFN、所有账户/地区回归全部做完才允许模型诊断。若协调者选择先做有限模型观察，应先满足实际actor的基本可用性，并人工核查通过补丁，不能把此题的原标量reward直接当完整正确性证明。本题暂不列模型优先候选，是因为有这一项具体、低成本且可能影响reward解释的诊断，非统一的“全覆盖先于模型”门槛。

reviewer状态：待独立复审；本轮未读取reviewer产物，不代填一致。当前只完成静态审查产物，未批准/执行CPU、模型、题面或测试修订。
