# iterative__dvc-1681 — 独立复核收口

2026-09-21。**优先保留为受限 `development_diagnostic` 静态候选**，状态 `needs_review / static_review`。用途是检验旧格式行为与内部表示断言是否错位；不得把原13项总分直接解释为旧格式兼容的完整证明。主审与独立初稿在根因、具体合理替代、Mock边界及运行范围上基本一致。没有已执行替代解/部分解，误拒与错误接受仍是静态疑点；一般非默认/调用者覆盖空白不全部设成准入前置门。

协调者已先封存三题全部独立初稿，之后统一开放本题五份角色产物和history精确指针。本题初稿 SHA-256 `2b4e16f0703aa95d0a16eb495d6228e218ebd35243afd6a5d1013e2ed491d561` 不变；只新增本review.md。没有将已见主审结论回写为独立初判。

## 原件与阶段定位

`ROOT=.`；`I=ROOT/runs/swegym_quality_batch02_20260921_v2`，`P=I/public/iterative__dvc-1681`，`V=I/private/iterative__dvc-1681`，`B=P/base`，`O`为本报告目录。`R=ROOT/runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-1681`。

- `G=R/gold/eval_logs/evallog_replay-er19-dv1-iterativ_ed4fa666.eval.log`，SHA `343e328a61dc9df9083d8c835b3cc861561964c6bf5cdd77bd31923c8477d21f`。
- `N=R/noop/eval_logs/evallog_replay-er19-dv1-iterativ_ffddd94c.eval.log`，SHA `da0ebba65221c3983393ac9b2d94a9e2a383b41615632ea7fa17b1b3115dc43f`。
- `H=ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_1/records/iterative__dvc-1681.json`，SHA `22a3ebd4054342cbc36c439204b9c8a6a0beeb3c9352d4540812033d0f6fdd1f`。
- `S=ROOT/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/iterative__dvc-1681`；旧 `LG=S/gold/offline/a1/test_output.txt` SHA `5ff25882cd0aecc86e3df682b7faa497df791d0e08b8ce73db60063214e7235f`；`LE=S/empty/offline/a1/test_output.txt` SHA `47bd28176388d7b4d02ab7bcb6fdd3f1a3fd47c57dce44bdccf11a0486e88a83`。

第一阶段已核S2三份第113行与本地材料、base `9175c45b1472070e02521380e4db8315d7c910c4`、gold/test/候选、recipe安装与恢复原件。旧LG/LE、本次引用的修复G/N、源码静态推断、未来CPU以及actor均分别记账；本复核没有新运行。

## 主审决定性论据逐项对照

| 主张及引用 | 复核判断 |
| --- | --- |
| 旧无wdir stage校验被运行时绝对目录污染（public_read:11–19,48；analysis:43–49） | 同意。`B/dvc/stage.py:494–536`加载缺省 `.` 后绝对化并原样dumpd；538–554只在写YAML时相对化；558–577仅忽略字面 `.`。问题来自stage定义，不是输出文件内容MD5。公开兼容注释已经足够定位，不缺大XML就无法调查。 |
| 唯一F2P在新增dumpd断言先失败，未到后面的旧格式changed检查（analysis:65–78） | 同意。`V/test.patch:8–9`要求内部wdir为 `.`；N:542–548、旧LE:451–457均实际得到绝对路径并AssertionError。不能用该失败代称“真实旧样本状态失败”。 |
| 新增删除后读取的assertIsNone是fixture检查（analysis:70） | 同意。它确认测试已删掉wdir，不是另一个独立旧格式兼容断言。真正末尾load/changed本来就在base测试中。 |
| 末尾测试是当前版本生成再删除wdir，缺固定旧哈希（analysis:55,113；delta:26） | 同意，且是关键限制。base创建/加载可共享同一错误绝对表示而自洽。没有固定旧哈希，就不能把“删除新增内部断言”视为足够的行为验收修订。旧H的直接删断言建议不采纳。 |
| 校验输入局部规范化是合理替代方向（analysis:107–109） | 同意为未执行路线。保留dumpd原表示、仅对用于_compute_md5的局部字典副本规范化绝对wdir，已有相对值/无值继续按原规则；dump仍可写正确相对YAML，is_cached在同一stage路径比较也有可行性。题面未规定dumpd的表示。完整候选未执行，不能宣称已证合法解被判0。 |
| 三个checksum单测全Mock dumpd，两个新增也是P2P（analysis:73–103） | 同意。真实hash/筛除逻辑被测，规范化入口却被替代；无wdir和 `.` 摘要相同、`..` 不同是有效契约。不能由此推断真实绝对非默认目录一定参与校验。 |
| 一律把真实dumpd wdir写为 `.` 可能通过（analysis:111） | 同意为具体自然部分实现假说。默认F2P会接受，原dump仍按真实self.wdir改写保存值，三个Mock单测绕过真实serializer。未实现/运行该候选，不称已骗过reward或已证false positive。 |
| P2P有8schema、1真实TestReload、3checksum，不能说所有调用者零覆盖（analysis §2.2；delta:28） | 同意。TestReload真实add/load/dump并保留人工MD5；F2P真实Repo.run。这些不是全回归保证，也不是零调用者覆盖。非默认目录/cache/move等已读源码不冒称执行通过。 |
| gold直接解决表示分歧，同时删掉dump(fname)（analysis:117–129） | 同意。相对化移到dumpd，真实对象仍用绝对wdir；内部已查调用无fname。外部兼容未知，没有受影响调用者便不升成已证gold回归，也不把保留fname的解判错。 |
| 修复gold13过/noop12过1败，实际/解析/冻结13个身份全对上（analysis:152–163） | 同意，初稿独立逐项核过原件。G:566,1469–1486；N:525,1392–1409，ledger为reward1/0。非标准文件名tests/unit/stage.py被显式点名，不是当前漏收集问题。 |

## 历史纠正与新增原件

H对源码根因与内部断言约束的观察有价值，但没有任何替代候选/分数原件。现在核到的旧LG/LE同样只有gold/empty：LG:1374–1391为13过，LE:1297–1314为12过1败。不能因旧记录也提出相同疑点，把静态假说升级为历史实验事实；其“KeyError”也不适用于这里保留wdir键的路线，实际noop是AssertionError。

主审delta:31–33对环境的纠正成立。LG:357–372是Git依赖下载失败并被true掩盖，406–411有botocore==1.35.9和requirements缺失，412–437的editable构建依赖失败；eval.sh:14–15记录串联末尾命令，LG:449–452仍写RC0。LE:365–390、410–411给出同类证据。两份旧status_map有13个真实测试身份，再多Could/No两个安装文本ERROR键（并非caplog造成）。旧“安装与测试正常、环境干净”的概括应撤回。

当前R两份安装明确固定awscli1.15.85/PyYAML3.13/colorama0.3.9/rsa3.4.2并安装requirements/editable，G:387–438,531–551有成功原件；本题metadata `0.30.0` 与模块Git版本 `0.30.0+9175c4.mod` 是不同字段，不是错base证据。当前13个解析身份outside=0也不等于任意候选日志的parser安全证明，更不能替旧安装洗白。

**本地功能资产足够，不等于运行完全没有网络相关副作用。** 此点补充独立初稿的环境边界：旧LG:585–586、LE:467–468和当前G:1234–1235,1252–1253均记录updater daemon尝试/启动；没有成功远程访问证据。`B/dvc/updater.py:42–44`与analytics.py:205–212允许通过DVC_TEST抑制，既有grader本身deny_all。后续诊断可固定该环境设置；不据此要求云服务或原Wikipedia文件。

本题raw第126行（SHA `d4f617bee89d9146a30ca40e1098a0d7428ed93c4c77e7d9a56f4f8dc4b32fc0`）hints只给bisect回归commit `38536903e101b7449e65fc668c4b19519e61869c`。沿H的精确本地clone只读该stage.py diff，可见#1658同时引入wdir绝对运行值、dumpd原值、dump相对化、checksum字面dot筛除；只读merge-base核为给定base祖先。该线索是历史定位帮助，当前公开源码已足以推导，不自动构成缺少必要题面信息。

还只读本题merge `a36d77272367bf2872799040686b9807caf08c90`的metadata及相对base的stage.py diff，第一父为给定base，业务diff与gold相符。一个不影响结论的引用精度补充：主审delta:13所说的“Stage checksum with default wdir fix”出现在merge正文，commit首行subject实际为“Merge pull request #1681 from shcheklein/fix-1680”。没有据此读取1877/2254或prescan；本题引入→修复链不证明其他题同义、重复或必须同侧。

## 八方面结论与运行身份

| 方面 | 已核/未核与对静态候选的影响 |
| --- | --- |
| 公开目标/初态 | 题面旧YAML、stage-vs-data校验、兼容注释、create/load/dump链清晰。报告版本拼写差异不改变指定base。完整XML缺失限制原CLI复现，不阻塞元数据探针。 |
| 需求—断言映射 | 全部新增4处关键断言/Mock方法和13参考已在初稿展开；内部表示断言、fixture删除确认、自生成checksum尾部、固定hash各保护不同事实。主审映射准确。 |
| 合法路线/部分实现 | 输入层规范化与真实serializer一律dot的两个具体疑点独立保留，均未运行。只优先实验其中最直接的合理替代，不为凑反例扩大范围。 |
| gold/调用者/回归 | 直接根因得到局部修复；save/status/changed/is_cached、run/add/move与输出相对路径已查。保留fname或其他等价内部结构不受官方签名断言限制。外部fname兼容、真实非默认checksum未全面证明，不全部升级为静态候选硬门。 |
| 开发环境/资产 | Python/shell/Git、SQLite、临时文件/缓存和旧依赖即可；无需下载用户大数据。版本生成文件和home/tmp权限、测试导入rlimit及后台updater需实际actor另验。 |
| 投影/恢复/控制 | gold只投影stage.py，noop空；test.patch明确两文件恢复，非标准unit文件名不妨碍该机制。当前test_globs=()，不沿用旧“所有测试改动还原”解释。额外排除维持空。 |
| 关系/版本 | S2身份、base、精确本题历史对象、旧Stage1与修复run分别定位。跨题历史序列/同侧主张没有本包精确证据，不采纳。 |
| 暴露/用途 | 初稿前允许的environment摘要已披露；门禁后读本题所有角色稿、H/raw hints/回归及修复对象。私有暴露材料不可给公开solver，实际actor/预训练泄漏未检查。 |

修复成功仅在引用派生镜像和rh2grader/54322、可写prefix、离线wheelhouse/deny_all条件下成立；public image与actor/54321的实际开发流程未验证。apply_user同为agent只说明补丁应用身份。没有实际Claude Code消息、工具shell、资源稳定性或模型求解证据。env_qualification=absent、resource_facts=null保持未知。普通完成pytest的非引用失败和全局评分故障概念上分开；本题恰好执行与冻结身份一致，不虚构额外未计分测试。

## 唯一优先后续实验

**固定本题修复grader配方，比较 base/gold/仅在checksum输入规范化wdir的三条路线。** 原官方13项和reward保持不变；外置探针使用题面固定旧YAML检查顶层changed_md5，小型本地旧无wdir/显式dot文件验证干净状态，再用真实非默认目录、保存重载/缓存比较及真实数据变化核对行为。没有XML时只检查元数据，不能把缺数据/缓存的完整status也要求为空。

若替代路线的外部行为成立而仅因dumpd表示断言失败，才可形成实际误拒证据；若旧样本、非默认路径或缓存比较不成立，就撤回其完整合法性推断。固定旧哈希用于避免自生成fixture的自洽问题，真实非默认构造用于避免Mock盲区。无需先修改测试、删除内部断言、跑全仓、修所有一般回归空白或取得真实模型会话。自然“一律dot”候选与外部fname兼容仍保留为独立未决，不增设另一前置实验。

此实验可以先在限定grader条件下回答oracle问题；启用actor开发前再核actor环境/输入，二者不能互相代替。当前没有实现/执行候选、没有新CPU分数或耗时、没有改题面/test/gold/reward，也没有把唯一下一步写成运行授权。

## 本次阅读范围与初稿完整性

已读O五份开放产物及本题history refs/H全文；两份旧eval.sh（90行）和status_map；LG/LE安装、收集、失败、结果/updater精确段；raw第126行hints；上述两个精确Git对象和祖先关系；复核updater/analytics与当前G相关日志。首次长输出中LG部分被截断，已补读353–374、400–438；全文件hash不计作逐行阅读。未读H的跨题prescan、其他任务、B1/B2汇总/manifest/method_adjustments/CPU队列或未经开放材料。

全程静态：文件/JSON/元数据哈希及Git对象只读，没有项目导入、pytest、依赖安装、容器、SSH、联网或模型调用；没有改变base、共享clone、初稿、他人文件或生产材料。优先静态候选判断不等于正式可用；未执行假说、实际actor与完整正确性继续保持未决。
