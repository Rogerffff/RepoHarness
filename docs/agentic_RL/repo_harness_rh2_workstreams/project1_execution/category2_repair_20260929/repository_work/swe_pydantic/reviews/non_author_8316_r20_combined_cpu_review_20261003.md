# Pydantic 8316：R14 五行与 R20 十九行组合 CPU 的非作者核查

2026-10-03。**组合对照矩阵符合预期，实际新公开 actor 诊断通过；可继续本版本范围内的普通 GPU 题目探针。** 24 行由 R14 已验五行与 R20 新十九行组成，不是 24 行均在 R20 执行。旧 `w_acr_max8` 的保护超时、infra／null 及失败工件保留；新 job 对同候选取得独立行为结果 0。本意见不授予训练／留出资格，不证明 GPU 实际镜像兼容或新模型能力。

## 范围和证据绑定

审查者不是材料、runner 或结果作者，但已接触本题私有修订、对照候选、参考和日志，不是 fresh 公开读者。复用[已验材料意见](non_author_remaining_material_review_20261003.md)、[R20 固定输入意见](non_author_8316_r20_input_review_20261003.md)和[R14 部分 CPU 意见](non_author_8316_partial_cpu_review_20261003.md)／题主核收中的准确范围，不重做旧 759 件或旧矩阵。原公开题面和 v3 语义材料未变。

本次只读本地原件，用标准库重算文件、tar 普通成员、canonical baseline／FP、census、base64／stdin、原日志及逐参考状态。AST 提取冻结 parser 的纯文本函数对拍，未导入或执行作者 helpers，未执行 SSH、Docker、安装、项目 pytest 或模型。作者 `passed`／`checks` 不作为验收依据。只写本报告及[同名 JSON](non_author_8316_r20_combined_cpu_review_20261003.json)。

| 身份 | 实际绑定 |
| --- | --- |
| 新正式 job／slot 时间 | `pyd8316-formal-20261003035447-r20-f5f0f`；cpu-a slot1，03:54:50–05:04:36 UTC；自然 rc0 |
| 新公开 actor job／slot 时间 | `pyd8316-actor-20261003050519-r20-f3934`；05:05:23–05:06:20 UTC；自然 rc0 |
| 复用正式 job | `pyd8316-formal-20261003020938-r14-d2baf`；只复用五行 0/1/1/1/0 |
| 新 release／manifest SHA | `cat2-cpu-r2e093-swe40-prepare900-20261003-v1`／`2a4ceb0315ea959232151d70f29ccc48bd34bdb0cb7dcfbb4aa177fec07bd393` |
| formal input／runner SHA | `58765caa86ef8909129a6b6d66643748bc2de6e8055b7fad0cc50da96a8026a9`／`16fd525666314ae0102d400fab83211e7593d208107bff141f1f53cff5a7b201` |
| actor input／runner SHA | `0984f53d1a36776f86df0973812175366a94f227df43257693ac2864a9ec20af`／`4866a706b9b54bda753416af280adb71a41b6aa8f6c7c73d534b920b48ac785e` |
| 最终两 attempt 索引 SHA | [results.json](../cpu_acceptance_20261003/8316_r20_resume/results.json)，948301 B，`d3da394101e6d263a1c2be77d01f092ba6676e1e6d2e59132a3d26551f442ae1` |
| revision／base commit | `pyd8316-acronym-v3`／`20c0c6d9219e29a95f5e1cadeb05ec39d8c15c24` |
| 有效 patch／test file SHA | `b248daa2eaf1ee37523ba03b078d768a9790a5db234813ee2b8b239b774a81e0`／`7dc1c199ead539bfea6725ff81fcb274b99c5add3301e059e9b9f2ad3414156a` |
| 精确派生镜像 | `sha256:f939c2664826e600f77549aee98d305dc02f705ee4f68939f5eea1db808e651d` |
| formal／actor tar SHA | `1b5b859857fcef7818c45367c6710a466e9d539dcf7e31010ad01deae55b8b17`／`0c7ed3a140ef182a8a072d74ca7aee9889cf19210d969f4a487ec40783e22706` |

独立逐件重算新 formal 2464 件、actor 32 件共 **2496 件**的大小和 SHA；两个 tar 分别精确包含同一普通文件集合，payload 字节相同，无重复成员、缺项、多项或其它对象类型。JSON 保存全 2496 条绑定、45 条本地／冻结源码绑定及完整逐参考状态。raw 根均在 `runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/` 下的 `packages/swe_pydantic/formal_8316_r20_resume_v1/{outputs,actor_outputs}/<job>/`；slot 原件在同根 `jobs/swe_pydantic/<job>/`。

## 24 行组合与逐参考失败

每行仍为 **1 原 F2P＋143 原 P2P＝144 参考**。11 条追加断言留在原 F2P 测试体内，没有新增节点分区。十九行原完整日志、raw 完整 ID、冻结 parser、report、ledger 及两原分区逐 ID 相符，共独立核 2736 条参考状态；复用旧五行 720 条，共 24×144 份状态记录，不能当作 3456 个不同测试。

R14 的 `noop/gold/keep_digit/scan/w_example_only` 保留原 job、manifest、输入和分数 **0/1/1/1/0**。题主旧核收绑定的报告大小／SHA仍相符，旧五份实际 report 与独立报告所记全文相同。正对照三种修法完整通过原 F2P 体内追加断言及 143 P2P；两旧负对照在原 CAMELToSnake 断言即失败，不声称其后所有追加断言均执行。

新十九行全部是 `unresolved/tests_failed/reward=0`，install rc0、candidate exec rc0、pytest rc1；无参考 missing／skipped、collection error、半截 segment 或 infra detail。下表是本节点**首次**实际断言失败；没有把该节点中未走到的后续断言冒称全部执行。

| R20 候选 | F2P 首个实际失败（实际 → 预期） | 旧 P2P 失败数 |
| --- | --- | ---: |
| w_acr_max8 | `load_configurationfile` → `load_configuration_file`，line556 | 0 |
| skip_if_digit | `base_64_urlencode` → `base_64_url_encode`，line552 | 0 |
| no_lower_upper | `gethttp_response_code` → `get_http_response_code`，line547 | 0 |
| acr3 | `user_idtoken` → `user_id_token`，line548 | 0 |
| w_last_only | `xmlto_json_converter` → `xml_to_json_converter`，line549 | 0 |
| w_window8 | `convert_xml_to_jsonvia_httprequest` → `convert_xml_to_json_via_http_request`，line557 | 0 |
| w_skip_nonascii | `über_httpclient` → `über_http_client`，line560 | 0 |
| no_trailing_upper | `parseurl` → `parse_url`，line554 | 0 |
| skip_if_underscore | `__httpresponse__` → `__http_response__`，line551 | 0 |
| w_count2 | `convert_xml_to_json_via_httprequest` → `convert_xml_to_json_via_http_request`，line557 | 0 |
| only_if_no_us | `camelto_snake` → `camel_to_snake`，原 line543 | 0 |
| lower_or_start | `xml_to_jsonconverter` → `xml_to_json_converter`，line549 | 0 |
| w_len_cap | `load_configurationfile` → `load_configuration_file`，line556 | 0 |
| lower_or_start_la | `__httpresponse__` → `__http_response__`，line551 | 0 |
| no_digit_split | `base64_url_encode` → `base_64_url_encode`，line552 | 8 |
| w_mid_underscore | `get_httpresponse` → `get_http_response`，line558 | 0 |
| literal | `camelto_snake` → `camel_to_snake`，原 line543 | 0 |
| lead_only | `get_httpresponse_code` → `get_http_response_code`，line547 | 0 |
| no_digit_upper | `base_64url_encode` → `base_64_url_encode`，line552 | 2 |

`no_digit_split` 的额外八个旧 P2P 失败是 `camel2/Camel2` 及首尾下划线／Snake 变体漏掉字母与数字之间的下划线；`no_digit_upper` 的两个旧 P2P 失败是 `camel2Snake/Camel2Snake` 漏掉数字与后续词之间的下划线。都是原测试 line543 的行为断言，不能误记为新增材料误拒或环境失败。其它十七行的 143 原 P2P 全通过。

十九份 raw 各 173 节点：通常158 PASS／1 FAIL／14 SKIP；`no_digit_split` 为150/9/14，`no_digit_upper` 为156/3/14。14 SKIP 均不在144参考内。冻结 parser 仍有已知含空格参数 ID 截断：169 键不是169个完整合法状态，16个非参考截断键对应20个 raw ID。当前参考均正确；本报告不外推全 pytest 语法或非参考 parser 修复通过。

## 实际安装、baseline、运输和 R20 边界

实际 prepared public／private 与已审本机 R20 prepare 字节相同，manifest 单行数和各 SHA 相符；公开 actor prepare 同样使用该公开输入和 host grading 身份。七份保存脚本逐字与 R20 本机 prepare、R14 原件相同，SHA 与真实 spec 相符。十九次 trusted setup 和 candidate test 注入 stdin 分别等于保存脚本；独立 prerequisite stdin 均为既有 SHA `847310cc9c6b22229f3c19a41492e75d44653bf168e778d0fb288eeb7b63dc68`，真实 UID54322 运行、stdout 固定成功标记。它不是七段中的 candidate_install 脚本；两项分别核对，未混淆。

十九行实际安装段完成、install rc0、没有失败命令标记或跳过。完整 eval log 恰为 trusted setup 原 stdout 与 candidate test 原 stdout 串接。runner 前后 digest 不变。实际 Docker 审计 stdout 与补充观察相同：Python3.8.19、Pydantic2.6.0a1、core2.14.5、UID54322，解释器 `/opt/miniconda3/envs/testbed/bin/python`；包及 alias_generators 从 `/testbed` 候选源码导入，每行源码 SHA 等于登记、FP 和实际导出／注入字节。有效测试文件固定 SHA、root 所有且 UID54322 不可写。

十九份完整 baseline 均451项政策内 regular对象，canonical digest与旧已验基线相同：`sha256:159f38430075ed49590b96724934cee9689f1f09219547ce213300c367dac4ba`。逐路径／类型／mode／内容SHA核对19候选初态、19应用后、19 fresh grader应用前，共57份全census；每份25政策排除路径摘要相符、cache omitted均0。每份 delta 只改 alias_generators，其它450项保持基线；原patch stdin、candidate base64导出、FP content digest、fresh grader注入 stdin逐件一致。FP／projection／baseline的task/public/image/HEAD及各physical attempt／rollout execution身份和canonical摘要匹配。

baseline 的 `environment_package_digest` 仍为 null；prepare 环境锚不替换它。该运输验收覆盖451政策内对象摘要，没有额外全baseline payload tar、测试后全census或typed训练租约验收。

R20真实spec与R14严格只差 `env_reset_timeout_seconds:300→900`，其余revision、材料、脚本、hygiene与120/1800预算一致。十九条真实ledger均reset900，并绑定实际固定policy SHA `d417dbb8d3140e6a0082f2f12cda02fd492feb14db9375ace3d69222e48acdab`及原支持请求输入。重核冻结manifest和12个相关产品源码／policy成员与manifest字节；完整1479发布集合沿题主已核支持意见复用，不冒称本轮重审全部发布源码。

十九次保护正文逐字相同，也与旧失败call0210相同；均 `RH2_PROTECT_OK=1`。实际耗时129.630–315.576秒，`w_count2` 的315.576秒超过旧300秒，在新900秒范围内完成。保护机制和资源未改；这证明本次受控接续完成，不能推断共享宿主根因或所有未来保护均成功。candidate stage900／grading deadline3600／cleanup120／pull1800等既有边界保留。

旧 `w_acr_max8` 原report仍 `failed_to_grade/infra_failure/reward=null`，旧wrapper仅保存五个完成rows，不能伪造第六个完成行。旧保护300秒超时，未安装或测试；新R20同候选实际通过安装并因line556行为失败得0。两事实各归原job，不回写旧分、旧报告、旧失败原件或旧partial索引。

## 实际公开 actor 和清理

完整读四份请求、固定桩script/log和唯一trajectory：4个assistant、24个stream事件、3个Bash tool调用、3个tool结果、1个成功result；stream事件不重复计为工具调用。三条实际命令的包装正文解码后与冻结public_commands逐条相同，captures／trajectory／后续请求回传逐字相符，返回码0/1/0。

首请求为一条user消息，实际原题面＋公开hints与冻结公开bundle／prepared prompt精确组成相同。`public_prompt.txt`使用 `read_bytes().decode('utf-8')`比较，保留64个CRLF；不以`read_text()`的换行归一化误报题面改变。四请求420个解码字符串中，完整私有effective patch和`loadCONFIGURATIONFile/convertXMLToJSONViaHTTPRequest/base64URLEncode/userIDToken`四个非公开例子均未出现。该检查是具体本轮投送范围的证据，不声称不存在所有可能私有信息通道。

实际公开actor使用f939派生镜像、UID54321、Python3.8.19／core2.14.5，公开源码可写、导入路径与冻结identity命令要求相符，CC2.1.205。`HTTPResponse`真实得到`httpresponse`，`TARGET_EQUALS False`并触发预期公开断言；原公开snake2camel_start_lower的9条测试真实通过。公开actor没有投送本题私有patch／新增断言，且未用于正式评分。

actual prelaunch inspect无Mounts／Binds，2CPU／4GiB／512pids，非privileged、有效cap为0、no-new-privileges；本轮记录中relay可达，外部DNS／直连及列出的禁止目标被拒，激活文件agent不可写。专门BASH_ENV拒绝试验未跑，`bashenv_denied_for_agent=false`如实保留。固定桩诊断证明本轮公开开发路径，不是新模型采样或全部角色隔离验收。

formal原审计708调用均返回0，19 candidate＋19 grader的38个run和38个删除逐名对应；run实际network none、精确f939、2CPU／4GiB／512pids，无volume／mount。19 grader实际prelaunch和补充cgroup一致。manager记录19建19删、open／supply／cleanup failures为空，最终exit0。末尾0707/0708按本job标签查询容器／网络，均rc0、stdout/stderr空。

actor原记录container删除rc0、network／relay失败空、stub rc0、标签容器／网络及residual_after_force空；post facts无actor进程、容器内harness目录／launcher／done marker。actor.log收尾与attempt／diagnostic一致。确认归档时两新job各零残留，不外推全CPU池状态。

## 结论的适用范围

JSON中 `cpu_review_passed=true`、`full_cpu_matrix_passed=true`、`ordinary_gpu_probe_ready_within_review_scope=true` 指当前24对照预期及公开actor范围，绑定最终两attempt索引和不同job／release归属。`combined_candidate_order`保存旧24完整顺序；`old_w_acr_max8_infra_null_preserved=true`。已静态核生成器要求的job、actor_job、reused_formal_job、formal_jobs、顺序、旧null、source_release和manifest字段均准确提供；本审查未执行生成器、写snapshot或probe_request。

后续普通GPU执行仍须核实际候选／baseline／安装／评分／清理、完整轨迹和模型checkpoint。**本R20 policy只允许该CPU精确f939镜像和对应revision／grading／patch的900预算；实际GPU镜像ID不同，须共享发布者提供对应版本兼容支持，不能任意覆盖900。** 不从本CPU通过推断GPU环境已验、新模型求解能力、所有合理／错误实现的一般完备性或训练／留出资格。当前范围内未发现新的决定性阻断。
