# Pydantic 8316：R14 部分 CPU 结果的非作者窄核

2026-10-03。**已完成的 noop/gold/keep_digit/scan/w_example_only 五行核查通过，可按原 job 复用实际 0/1/1/1/0。第六行 w_acr_max8 在控制面保护阶段超时，未安装或测试，保持 infra_failure／reward=null，不是模型 0。** 本 run 实际零残留；24 候选矩阵未完成，公开 actor 未跑，CPU 全题及普通 GPU readiness 均为 false，未授训练资格。

## 范围、方法与实际绑定

审查者不是材料、runner 或本轮结果作者，但已接触私有修订、候选和正式参考／日志，不是 fresh 公开读者。复用另一非作者的[四题材料意见](non_author_remaining_material_review_20261003.md)中8316部分及已核[R14入口](non_author_remaining_runner_review_20261003.md)／共用runner，不重新审原材料、旧34格或完整release。公开题面未改。

只读取本地原件，以标准库复算 SHA、tar payload、canonical baseline／FrozenPatch、逐对象census、base64／stdin运输与逐ID日志。AST提取冻结parser纯文本函数后独立对拍144参考及原report／分区；作者checks或wrapper passed不能替代实际验收。没有SSH、Docker、安装、pytest／模型、作者helper执行、自动重试或调整保护300秒。仅写本报告及[同名JSON](non_author_8316_partial_cpu_review_20261003.json)。

| 身份 | 本轮原件绑定 |
| --- | --- |
| job／namespace／slot | `pyd8316-formal-20261003020938-r14-d2baf`／`formal_v2`／cpu-a slot1；02:09:41–02:34:26 UTC，外层rc1 |
| release／manifest | `cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1`／`51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8` |
| 输入／runner SHA | `bea70edd55d2a316b5d92fde1a3a894e9c79363a168e2cd92c7de2d40b83ac1b`／`b127f7309ffae3eae2bbe834c595f846104406e2f858b8073ff2182d0a2ce3c5` |
| revision／SHA | `pyd8316-acronym-v3`／`8b7b214598fa34943a3276f9fbe159210869745eee38976c7b3191ddd5addc3b` |
| 材料／公开bundle | `sha256:05c815276fd0e953aa6a6fb90cbd1a4e1d6e936d7bb1fb7f4499b0557007aaa9`／`sha256:0880b03743ac3a54b6c379ce2f712931ac209ef044dc77c9742aa2f9340ac4f2` |
| prepare环境锚／HEAD | `sha256:8d3e5b4e37604a1fa12aaf1dae531c4de4a1e1f09bbff9cfe832047358882dac`／`20c0c6d9219e29a95f5e1cadeb05ec39d8c15c24` |
| base／实际派生image | `sha256:add19c2969be6265a7e21a070900f97f159006af42e7879861f270f39539cac4`／`sha256:f939c2664826e600f77549aee98d305dc02f705ee4f68939f5eea1db808e651d` |
| 有效test patch／file SHA | `b248daa2eaf1ee37523ba03b078d768a9790a5db234813ee2b8b239b774a81e0`／`7dc1c199ead539bfea6725ff81fcb274b99c5add3301e059e9b9f2ad3414156a` |
| 安装资产SHA／core | `a6fe422e5e999d5aaceb86a0296761817234acf95e87724e11fb9cc2143f620c`／`2.14.5` |
| 归档 | 759件；tar SHA `38b4e27b7a3bd583283c3e1b3fcf5b0facafc8a480a328c77c748b17fd972126` |

按 [remaining/results.json](../cpu_acceptance_20261003/remaining/results.json) 独立核759文件路径／大小／SHA。tar精确含相同759普通文件，每个payload大小／SHA相等，无缺项／多项。原件根为 `runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v2/outputs/<job>/`，slot原件同remote_evidence的 `jobs/swe_pydantic/<job>/`。

实际prepared manifest、两份public文件和host grading原件的SHA／单行数相符；actual public／private和已核local_prepare_r14_v1/8316逐字段相同，spec严格相同，prepared runtime／image／材料身份接续R14。已核共同release意见按原范围复用，未机械重核1220成员。

## 五行完整参考及实际行为

每行 **1原F2P＋143原P2P＝144参考**，本题没有新增节点分区；11条追加断言在原F2P测试体内。原始完整日志、冻结parser、report和 original_f2p／original_p2p分区逐ID一致，无参考缺失或跳过。JSON保存五份逐参考完整状态、原raw节点、非参考解析限制、日志SHA和FP来源。

| 候选 | 原reward | 原F2P | 143 P2P | 原raw汇总 | test rc | 可复用 |
| --- | ---: | --- | --- | --- | ---: | --- |
| noop | 0 | FAIL | 全PASS | 158 PASS／1 FAIL／14 SKIP | 1 | 是 |
| gold | 1 | PASS | 全PASS | 159 PASS／14 SKIP | 0 | 是 |
| keep_digit | 1 | PASS | 全PASS | 159 PASS／14 SKIP | 0 | 是 |
| scan | 1 | PASS | 全PASS | 159 PASS／14 SKIP | 0 | 是 |
| w_example_only | 0 | FAIL | 全PASS | 158 PASS／1 FAIL／14 SKIP | 1 | 是 |
| w_acr_max8 | null | 未执行 | 未执行 | 无正式测试段 | 无 | 不可记行为结果 |

noop和w_example_only均在 `tests/test_utils.py:543` 原CAMELToSnake断言得到 `camelto_snake`，预期 `camel_to_snake`。这是普通缩写分词行为失败；w_example_only的例子特判没有覆盖这条原要求。两者在原断言即退出，不声称其后11条追加断言都执行或首个失败由新断言发现。

gold、keep_digit、scan完整通过原F2P节点；当前固定测试体在该参数下继续顺序执行11条追加断言，无提前return/skip，故完整节点PASS覆盖它们。三份不同合理实现没有被误拒，keep_digit保留允许的另一数字读法，scope沿已有语义意见，不外推任意数字歧义或其它转换函数。143旧P2P均通过。每行另有29非参考raw节点（15PASS／14SKIP）；Python3.8下这些SKIP不在144参考中，不是参考缺失或infra。

五份原日志均有唯一完整Start／End Test Output段，大小／SHA与ledger/report相符；正对照resolved/1，负对照unresolved/tests_failed/0，无collection error、半截segment或infra detail。pytest rc1与candidate exec rc0分别保留，不能以shell最终0代替测试判定。

## 实际安装、导入、完整baseline与运输

五行prerequisite实际rc0，原stdin SHA `847310cc9c6b22229f3c19a41492e75d44653bf168e778d0fb288eeb7b63dc68`，stdout均 `RH2_PYD_FIXED_OFFLINE_PREREQUISITE_OK=1`；editable／测试依赖安装完成，install rc0、未跳过、失败命令列表空、candidate exec0。七份保存脚本SHA与spec相符；实际六次trusted setup、五次candidate test的stdin与保存字节相同，runner前后摘要未变。

五行原Docker审计stdout与supplemental observation一致：UID54322、Python3.8.19、`/opt/miniconda3/envs/testbed/bin/python`、Pydantic2.6.0a1／core2.14.5；alias_generators实际从 `/testbed/pydantic/alias_generators.py` 导入，逐候选源码SHA和登记／运输后字节相同。有效tests/test_utils.py SHA固定、root所有且执行UID不可写。五次保护均RH2_PROTECT_OK=1，image inspect原输出及run参数绑定固定派生SHA。

六份FULL baseline各 **451项政策内对象**，canonical digest均 `sha256:159f38430075ed49590b96724934cee9689f1f09219547ce213300c367dac4ba`。独立复算全部baseline／FP／projection canonical摘要及task/public/image/HEAD/physical attempt/rollout execution身份；六候选初态、应用后、fresh grader应用delta前共 **18份完整census**逐路径、类型、mode、内容SHA一致，各25政策排除对象摘要也相符。失败行census完整不代表后续保护／安装／测试完成。

noop为空delta；其余五份只改alias_generators.py，其它450项保持baseline。实际patch stdin、候选base64导出bytes、FP content digest和fresh grader注入stdin逐件相符。w_acr_max8 patch SHA `c41061bd25bf4373d2dae91a485c632540fe0271313e9457bfed27eedfdf7e53`，FP canonical `sha256:1d7546f4e6a419906f5c25673956005322925c918c426847f3fc0cb69992fbb7`，身份和运输可核；没有其测试阶段core／UID／import审计，不能外推该项通过。

baseline environment_package_digest仍null。验证范围是政策内逐对象census／摘要、实际image、安装和运输；没有额外全baseline payload tar、测试后全census或typed训练租约验收。prepare非空环境锚不替换FP baseline null。

## w_acr_max8实际失败阶段与自有清理

trusted setup实际0208退出0，恢复原测试文件、固定patch cleanly apply，RH2_SETUP_APPLY_RC=0／RESTORED=1／OK=1。随后0210控制面保护开始1790994563.9797726、结束1790994864.0899909，**300.110218秒**超时。目录只有call.json，无exit_code或stdout/stderr；不能造退出码或定位在具体chown/chmod。它与前五次保护正文逐字相同。

原report明确failed_to_grade／infra_failure／reward=null，detail为grading_control_surface_protect_timeout_after_300s、test_seconds0；ledger install/test/observations为null，日志无安装／测试开始标记或真实test segment。失败日志22809字节、SHA `20fe2628419bd5656697aa520d8d30d609e7cefa93be55658848e0d1c1a7b956`。execution_failure_stage原字段仍null，本报告据原调用另记observed stage，不回写历史字段。

0212实际memory events均0（oom_kill0），pids max0；0213 inspect OOMKilled=false。能排除这些已记录事件，不能据此断定宿主CPU／I/O根因或保护内部卡点。第六行144参考完全未执行，不计模型0，不计材料或候选行为失败。后18候选没有运行。

216调用中215实际rc0，0210无返回码／streams。12次删除 `0011/0035/0048/0072/0085/0109/0122/0146/0159/0183/0196/0214` 均rc0／stderr空，对应六候选与六grader；manager6create/6delete，containers_open／supply_open／cleanup_failures空。0215/0216按本job标签查询容器和网络，rc0、stdout/stderr空：归档时**本run零残留**。

原stderr保留首validate异常“真实测试标记缺失”，原因是评分前保护已infra失败；finally用end.exit_code==0及residual条件判断，aborted/4导致再次抛“收尾异常或存在本run残留”。外层异常措辞掩盖保护超时，但不证明残留；不能把exit4解释为删除失败或四个残留。

12个run参数均network none、精确image、2CPU／4GiB／512pids；五行实际cgroup `200000 100000/4294967296/512`。reset/apply/test预算300/120/1800秒，replay候选／评分／清理／镜像900/3600/120/1800秒、manager close300秒、保护300秒。前五次保护140.622、191.075、170.060、141.388、228.785秒完成，第六触及300秒上限；不称整轮预算通过或共享问题已永久解决。

## 复用条件与未完成范围

可保留本job五行原分及原件，用于同R14／同字节runner／revision／测试／材料／安装／精确image／spec的接续；不重跑五行，不移记为新job。失败工件、null、原error和清理来源保留。后续单独输入若补验，范围应为失败w_acr_max8与原未跑18行；新input／job／namespace和共享恢复事实需分别核，不从本报告自动生成、上传或派发，也不改保护300秒。题主已告自有新CPU派发hold；本审查没有重试。

共享parser非参考限制：**169个parser键不是169个完整合法states**。144参考正确；另9个非参考SKIP准确；16个带空格参数的截断键含非法状态，代表原raw的15PASS／5SKIP共20个非参考ID，其中部分发生键合并。raw full ID另保存，未用于改reward。若这些ID成为参考或要声明全节点完整states，须共享parser修复另验；本现有非参考缺口不扩大为全pool阻断。

JSON `partial_review_passed=true`、completed_rows_reusable列五行、failed_row_reward_is_null=true、failed_row_is_model_zero=false、cleanup_no_residue_verified=true。**全24候选仍缺第六及后18行，实际公开actor尚缺**，full_cpu_matrix_passed／cpu_review_passed／ordinary_gpu_probe_ready_within_review_scope均false，training_eligibility_asserted=false。五行可复用、失败归因和零残留确认不代替全题CPU、GPU或训练资格。
