# 8316 R20十九行接续输入：非作者静态增量审查

日期：2026-10-03。结论：**固定接续输入静态审查通过**。当前范围内未发现阻断封包或受控接续的字节、参考、版本及消费冲突。实际上传核收、新十九行CPU结果和公开actor诊断仍缺；本报告不证明900秒足够，不证明CPU已恢复、整矩阵通过、GPU就绪或训练资格。

我已读过私有题卡、controls、正式评分材料及R14部分CPU原件，**不是fresh公开读者**。本次只用本地标准库读取、SHA/字节、JSON、AST、源码差异和tar检查；没有执行作者helper、SSH、Docker、任务pytest、安装或模型。复用旧材料意见与R14部分CPU审查，不重审题义、不重跑旧五行，也不重核旧759份原件。

## 固定入口及旧结果归属

正式输入只有8316，十九个candidate完整对象严格等于旧24行的 `candidates[5:]`。candidate名称、patch路径与SHA、source SHA映射、预期reward及required_statuses均原值；其余题字段也完整相同。144个参考保持1F+143P的原序列、唯一性和分区，所要求的状态均指向这144个参考。28件材料包括原24个controls，逐件SHA仍匹配旧输入；本次未重新执行候选应用，候选生成后源码依据复用已核旧输入和原件。

前五行 `noop/gold/keep_digit/scan/w_example_only` 的实际reward `0/1/1/1/0` 继续属于R14作业 `pyd8316-formal-20261003020938-r14-d2baf`。旧部分审查JSON的SHA为 `317e724014183c09effd0046a8ba6189e3b16dd72e46134d4db61e7fc33d882a`，已重新绑定。其720个参考状态（5×144）、清理无残留与旧759份证据的完整核查在该报告中，本次复用。

旧第六行 `w_acr_max8` 在 `control_surface_protect` 的300秒超时中自然停止；install/test没有开始，reward为null，不能记成模型0。新十九行是这一个失败行加18个未执行行，全部预期0尚未观察。前五行不进入R20重跑，也不能改称“24行在R20均通过”。后续组合核收须明确“五行R14+十九行R20”的来源和预算版本。

## R20实际支持与消费边界

R20发布清单SHA为 `2a4ceb0315ea959232151d70f29ccc48bd34bdb0cb7dcfbb4aa177fec07bd393`，1479成员。题主已全量核1479大小/SHA及精确集合、全部264消费快照；本次复用该核收，重新核对其17个绑定原件及本地prepare核收的13个绑定原件。另独立比较R19/R20清单集合和当前相关源码、8316的完整32字段快照；没有声称本次重新全量核1479文件或264题。

R19的1476条文件路径全部保留，实际变化为两份consumer源码和 `rh2/SNAPSHOT_ID`；新增固定policy代码、policy JSON及其维护测试三件。consumer两处都只有新增块：`prepared_task_face.py` 根据固定policy生成reset900的spec；`replay_grade.py` 把实际spec预算和policy/request身份写入账本。原manager逐字节未改；其保护步骤仍使用 `spec.env_reset_timeout_seconds`，所以R20运行时应消费900。这里的“保护未改”指保护脚本和检查机制不改，**该保护步骤的超时由同一reset字段从300变900**。

policy文件由固定SHA绑定，只允许8316与dvc9395两条按序记录。8316必须同时匹配v3 revision、有效grading digest、补丁SHA、f939精确grader镜像，并要求manifest digest为None；错配拒绝，无自由预算覆盖。原环境档位必须为300。6283不在policy中，仍为reset300。8316实际完整快照只有 `env_reset_timeout_seconds 300→900`；安装、补丁应用120、test1800、whole预算、资源及其余31字段保持。

发布者保存的8例replay是替代Docker外部调用的入口消费检查，不是项目CPU实测。8316四例的账本预算/policy确有900及固定request身份；正确身份两例保存完整spec，错inspect/override两例按预期拒绝。既有镜像inspect原件证明cpu-a的目标ID匹配，但没有新容器安装、测试或任务恢复。900是否足够仍待真实新作业。

R14的SWE34与R20的SWE40全bundle本来不同。本次独立确认**8316的public/grading/environment三条记录完整相同**，不能把其他题已发布变化当成8316材料失配。一次错误比较整bundle的生成失败记录保留；失败发生在固定输入写入之前，当前生成器改为逐8316三记录比较，输出用exclusive create，未运行新CPU或覆写旧输入。

## 保存prepare、runner和actor

本机实际已保存prepare的完整 `spec_record` 对R14仅reset300→900，七段脚本逐字节相同；所有脚本SHA与spec一致。prepared manifest的一条public、host/private身份及文件摘要匹配；public与grading的canonical digest、materials identity按原公式独立复算匹配。private有效补丁字节与当前材料相同、144参考相同，状态仍为 `not_evaluated`，apply/result均null。

当前关键身份为v3 revision `pyd8316-acronym-v3`、base commit `20c0c6d9219e29a95f5e1cadeb05ec39d8c15c24`、core2.14.5，E10安装资产与原输入一致。base镜像为 `sha256:add19c2969be6265a7e21a070900f97f159006af42e7879861f270f39539cac4`，实际保存grader spec为 `sha256:f939c2664826e600f77549aee98d305dc02f705ee4f68939f5eea1db808e651d`。public digest为 `sha256:0880b03743ac3a54b6c379ce2f712931ac209ef044dc77c9742aa2f9340ac4f2`；材料身份为 `sha256:05c815276fd0e953aa6a6fb90cbd1a4e1d6e936d7bb1fb7f4499b0557007aaa9`。

正式runner相对已核R14仅增加五条prepare/账本身份及预算检查、两处8316任务/run-id限制；撤销这些增量后整份AST与旧runner相同。`execute` AST完整不变，因此七脚本消费、安装/test/whole预算、2CPU/4GiB资源和首次失败停止/清理逻辑不变。新runner核真实保存账本的预算与policy，不把发布者的替代调用记录当真实新CPU结果。

actor输入的整题对象、public记录、base/derived镜像及三命令字节完全保持R14。actor runner只有task限制和新 `actor_outputs` 命名空间两处变更，撤销后整份AST相同。三命令仍查正确UID/公开源码与依赖、公开HTTPResponse目标、既有公开测试；私有only名称列表为空本身不能证明无泄漏，实际CC UID/调用/公开条件仍须新namespace诊断核收。本机actor/host spec相等只证明prepare身份相等，不是actor已执行。

## 封包、派发和归档

tar SHA为 `22bb9355d5c6c398c3bf7790c661c6d3419aa7dc7e7292cc0c27c8db3d56379e`。六payload加manifest共七个普通成员，无重复、symlink或hardlink，成员精确集合、大小、SHA及完整字节均匹配本机固定文件。28件旧材料不重复装入tar；上传verifier须逐件核远端 `formal_v2/materials`，也核新目录六payload+manifest精确集合，再exclusive写核收。当前实际上传题主回读仍不存在，静态封包通过不等于上传通过。

六份helper只做静态核查及AST解析，未执行。生成/prepare/package入口限定新路径及固定身份，不改旧输入、旧分数或失败工件。派发要求实际R20支持回读、这份JSON的通过字段与四个裸SHA、实际上传回读和28材料SHA核收；任务仅8316、命名空间固定、无自动循环或下一档预算升级。原 `cpu_infra_hold.json` 的SHA `ce3b1b2581109b955261c5da6d689df0dd219ffd6f5f34e03714710e19160f5b` 保持，helper不删除它；这是已授权支持下8316 R20的有限接续入口，不是广域hold解除。6283旧派发入口仍因原hold返回75。sequence hold若出现仍阻止本入口；actor还需新十九行实际通过及清理核收。

新归档入口SHA为 `ac3a771129746f0a3aa65ce3395970d590561d68ff3df339eb892b8eaf3b40ba`。相对已核6283归档入口仅更换8316 formal/actor命名空间、相应outputs/actor_outputs和新results路径。它只接收自然finished、非deferred的本包job，取回作业输出及slot原件，使用data过滤解tar，拒绝同job重复登记，append新R20 results的attempts，不覆盖旧partial。归档可收失败结果，`non_author_review` 仍pending；归档finished不代表CPU通过，也不替代完整原件/清理的独立核收。

## 后续验收要求

- 先真实上传并核收七成员和28件复用材料，保存实际上传题主回读；本报告没有代做该动作。
- 新作业只执行固定十九行；首个infra、状态缺失或清理未知即停止并保原件，不循环重试，不升级预算。逐行核actual spec、实际账本900与policy/request身份、安装/源/依赖身份、144参考、resource/清理；不得仅凭预期0判通过。
- 新十九行全部核收后才执行本namespace的公开actor诊断。组合报告保留旧五行R14归属和旧null失败；实际actor核收后再判断普通GPU探针入口。
- 实际CPU恢复、整矩阵通过、GPUready、训练资格当前全部为false。无当前范围内新的决定性静态阻断。

完整逐件绑定、比较结果、十九行名称与源码SHA映射见同名JSON。只写本审查MD/JSON；作者输入、封包、旧原件、hold和共享代码均未修改。
