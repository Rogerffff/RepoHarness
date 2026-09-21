# iterative__dvc-4785 独立最终复核

**结论：保留 `needs_review` / `static_review`，用途 `development_diagnostic`；同意存在异常类型解释争议与明确401覆盖缺口，暂不作为无争议探针。** 与主审仍有下一实验优先级分歧：本 reviewer 优先受控 **HEAD405 → GET404 的 base/gold 对照**，并用少量明确状态作控制；主审优先原生 raise_for_status 的异常类型/CLI差分。两者均未执行，本稿不以一致为目标撤掉分歧。

初判 SHA256=`704225d50ee63dc2927be81752a21ade16f9c9398a6067e00ad03e95ef85aa4b`，保持不变。

复核保存时间：UTC 2026-09-20T21:40:54.057106+00:00；SGT 2026-09-21T05:40:54.057106+08:00。

权威 ROOT=`.`。下文 P=`runs/swegym_quality_batch03_20260921_v1/public/本题`，V=同批 `private/本题`，R=`runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/本题`，E=`runs/env_recipe_repair_20260919/dvc_install_v1c`；均相对 ROOT，日志短后缀唯一对应本题 run_refs。

本 reviewer 先独立完成整包三份初判。协调者于 UTC 2026-09-20T21:34:52.575948+00:00（SGT 2026-09-21 05:34:52.575948+08:00）核哈希封存并明确开放后，才读取三题 public_read、analysis_before_history、old_findings_delta、card、screening_record 和各题 history/refs 唯一指向的旧记录。未回写初判，未读旧聚合/相邻题。environment_record 在独立阶段已带历史结果摘要，故独立性是未接触主审和历史质量结论，不是无结果暴露盲审。

本轮只做静态文件与 stdlib 文本/哈希核对；没有项目导入、执行、测试、安装、联网、Docker、模型或新 CPU 实验。重读历史日志不称重跑。所有后续实验和修订均为建议、未执行。未修改题面、源码、测试、gold、参考、reward 或配方；只新增本文件。


## 主审决定性主张的逐项核对

| 方面 | 最终处置与原件依据 |
| --- | --- |
| 公开目标与合理实现 | 同意基础目标。prompt:3–10 明示HTTP(S)的401/403不应静默不存在，成功与404例外，并建议 raise_for_status；重复文本没有第二套规格。`tree/http.py:130–144`、HTTPS继承和 BaseTree/Remote/BaseOutput调用者给出合理调查路径。没有唯一内部结构或异常文案要求。 |
| 全部隐藏断言、helper、F2P/P2P | 初判已完整读追加28行、唯一F2P及8项P2P/必要fixture。F2P同一个Response依次200/404/403，request全部返回同对象；断言True/False/DVC.HTTPError。没有401/5xx、独立HEAD/GET状态、真实HTTPS派发或CLI。8 P2P是本地下载错误、认证/TLS配置与请求方法，不能借作exists状态组合覆盖。 |
| 异常类型是否误拒 | 同意“争议”，不升级确定误拒。题面明确建议原生 Requests 路线是实质支持；测试精确DVC类与其不相容。但同文件 `_download:161–164`、`_upload:198–200` 已用DVC.HTTPError；exceptions.py:287–289及CLI catches提供公开约定。`command/data_sync.py:39,62,83`、`command/status.py:80` 区分DvcException，main.py:88–109把其它异常记为unexpected。因此异常类型可改变产品出口，不是纯隐藏名字。主审分析§2给下载raise的170–171行锚点不准确，实际为163–164；证据内容仍成立。 |
| 401及相关旧行为 | 同意主审纠正旧“同gold分支所以已覆盖”。候选只对403抛错即可遗漏明示401；这仍是静态漏检路线，未获实际reward。HEAD405/GET200既有成功回退应保留；同对象Mock不能证明差异状态回退。冲突错误状态与405方法不支持须区别，详见下节。 |
| gold完整性与调用者 | gold仅改变exists，源文件可投影、无未交付依赖。同状态200/404/403的历史9项通过；401/5xx静态也抛DVC异常。保留_head源码不等于所有回退可观察行为不变，因为exists由False改为抛错会重新解释_head选出的响应。已读get_hash/list_hashes_exists、Remote.hashes_exist、BaseOutput.exists/workspace_status、HTTP依赖与CLI。 |
| 原件版本、日志、开发条件 | base=`7da3de451f1580d0c48d7f0a82b1f96ea0e91157`。gold `...bd348b66:605–628` 为9 passed/RC0；noop `...ad440329:586–643` 为8 passed、403未抛DVC异常失败/RC1。补充初判漏记：主审指出setup.py共同moto pin，已回noop:132–174/gold:181–193确认 `1.3.14.dev464 → 1.3.14`；不能称clean base或只凭.mod判gold。 |
| 投影、恢复、计分与安装 | 同意。gold投影仅http.py，官方只恢复既有`tests/unit/remote/test_http.py`，restored/expected1、apply_rc0；test_globs=()、无新增排除。实际9节点/解析9键/冻结1+8分别核对，本题无Could伪键、missing/skipped=[]，reward1/0。E/recipes输入经wrapper消费；原gold:570–590/noop:551–571证实离线editable成功，不能用COPY wheels替代。固定grader54322、apply54321与正式actor分开；env_qualification=absent。 |
| 暴露、用途与关系 | 当前已见整包私有材料/主审/精确旧记录，不可作solver；实际消息、Git对象/镜像答案可见性、正式actor导入/loopback权限与迁移均未知。F2P全mock、P2P下载使用localhost随机端口，原日志GET404并非公网偶然失败。跨题代码关系见下文，不根据同仓认定重复或干净holdout。 |

## 对初判和主审均需加上的语义界限

| 状态组合 | base/gold静态输出 | 支持什么、不能支持什么 |
| --- | --- | --- |
| HEAD405 → GET200 | 均True | 公开 `_head:135–139` 为HEAD受限服务器回退GET的明确兼容依据；不得提前在HEAD失败时抛错。 |
| HEAD405 → GET404 | base False；gold 抛DVC.HTTPError(405) | 方法不支持后，实际GET给出公开允许的404，较强地关联“回退仍能判断缺失”的旧行为。gold改变可观察结果是源码事实；是否构成需修的回归有公开注释/404豁免支持，但未做CPU确认，不称已证实gold错误。 |
| HEAD404 → GET403 | 均False | HEAD声称缺失、GET声称拒绝，响应结论冲突。公开资料未规定两者优先级；不能仅因看见GET403就判gold漏修，也不能把遵从HEAD当作唯一正确解。 |
| HEAD401/GET401、HEAD403/GET403 | base False；gold抛对应DVC异常 | 明示核心需求，401未输入现有F2P；异常类型约束另记。 |

**修正初判的措辞和优先范围，不回写初稿：** 初判开头及末段把HEAD404/GET403称“漏修候选”，并写“优先确认……漏修”，容易把策略假设写成待确认既定缺陷。最终仅保留“冲突响应策略未定”，不把此组列为pass/fail oracle或优先实验的决定性结果。对HEAD405/GET404也采用“有较强公开依据的回归疑点”；CPU只能确认当前响应选择和输出变化，规格判断仍要依赖公开契约/兼容意图。不能用运行结果本身裁决未明规格。

主审分析§4把HEAD404/GET403和HEAD403/GET404都留为未定，处理正确；但“gold保留_head”须限定到源码和HEAD失败/GET成功的情形。HEAD405/GET404的不同输出值得单列，而不是被泛化成任意互相矛盾的服务器状态后全部降权。

## 历史对照、跨题关系与唯一优先实验

精确旧记录为 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_2/records/iterative__dvc-4785.json`。同意主审纠正“异常类是唯一判分细节”“必须按gold手写raise”“401跟403同分支所以覆盖充分”“改题面/放宽类型即可使用”。200/404也计入F2P，其他包装实现能抛DVC类；异常语义仍需公开证据。当前9个真实解析键与离线成功安装不支持沿用旧Could/公网标签。旧难度、raw hints不可见、上游提交一致及无同路径即无关系未在本轮验明；不批量去重或自动修改oracle。

整包原件补证：4785公开`config.py:385–399`已有3665 gold的核心helper/partial/PathInfo.as_posix保存链；6954 `config.py:230–250`保留演化版本但绝对路径分支不同。三题缺陷不同，然而晚题公开base含早题实现的代码关系应登记，不将其当作完全独立材料。未核完整Git谱系、未据此自动划分；6954 HTTP已换FS架构，不据同仓直接宣称含本题完整gold。

**本 reviewer 唯一优先实验（建议，未执行）：** 在可确认候选身份与导入源的固定诊断环境，对base和gold的真实HTTPTree提供分开的HEAD、GET Response，窄测HEAD405/GET404；以HEAD405/GET200、同状态200、404、401/403作控制，记录实际调用方法、选中状态、返回或异常类。主判据是方法受限时，gold是否将原可观察的missing变成405查询错误；不引入HEAD404/GET403的任意期望。不要求先造第二个候选、改test/ref/reward或全仓回归；原RH2的9项得分作为既有对照，任何新运行必须另记而不冒称历史重跑。

**为何暂不改采主审首选：** 原生raise_for_status与DVC类的断言不相容已可直接从源码定位；再跑预计拒绝不能单独证明该候选在CLI约定下属于完全合理解。类型差分若做，需要同时评估公开CLI错误出口，而非“抛了异常”即裁定测试坏。窄405/404实验不依赖新增候选，可先确认gold自身在有既有回退目的支持的场景是否发生行为退化。主审异常类型差分仍有价值，但本 reviewer 排在该项之后；两类规范判断都不能由CPU结果独自解决。此优先级分歧保留交由协调者按证据收敛。

最终没有确定的替代解误拒实跑、gold回归实跑或获准修订；相关风险、actor资格和规格边界仍开放。`screening_record`中局部gold pass只能按原注释限制到同状态核心路径与历史九项，不能据此对差异HEAD/GET全面背书。
