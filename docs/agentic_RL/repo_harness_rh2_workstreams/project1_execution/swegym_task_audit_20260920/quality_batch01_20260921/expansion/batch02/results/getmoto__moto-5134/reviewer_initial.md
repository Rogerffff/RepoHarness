# getmoto__moto-5134 — reviewer_initial

日期：2026-09-21。独立 reviewer 第一阶段；未读公开读者、主审、本题旧质量结论或 history 目录。已见授权私有原件 environment_record.json 中的批次 history 引用字段，未跟读其汇总。仅原件静态审查与元数据读取，未执行项目/测试/安装/Docker/SSH/网络/真实模型。三题全部保存后等待整包封存。

## 初判

建议 `needs_review / static_review`，用途 `development_diagnostic`。公开要求、两条 F2P 与 gold 的 missing/null 区分一致；目前没有足够具体的语义误判或回归争议要求先造质量反例。保留测试范围限度和正式 actor 开发条件未知。历史 sqs_v1 的 noop/gold 成功对照只证明修订评分安装配方的诊断条件；COPY wheel 不是正式 actor 中已安装依赖的证据。

缩写：`P=ROOT/runs/swegym_quality_batch02_20260921_v2/public/getmoto__moto-5134`，`Q=…/private/getmoto__moto-5134`，`E=ROOT/runs/env_recipe_repair_20260919/sqs_v1`，`T=E/tasks/getmoto__moto-5134`；`ROOT=${REPO_ROOT}`。base 路径均在 P/base。

## 公开目标、初态与断言映射

base `0e3ac260682f3354912fe552c61d9b3e590903b8`，tree `ab7f05b7fa775f24a93863be3cbfacf22b2811b7`。S2 public/grading/validation 为 source_refs 精确第59行，身份对应。题面要求 EventBridge rule 的 exists:true 将存在且值为 JSON null 的字段视为存在。AWS test_event_pattern 例是原作者的服务对照；本地重现是 mock_events/mock_logs 的发送/接收链，不能要求本轮跑 live AWS，也不能把 base 未实现 test_event_pattern API 自动扩为本题必须实现。

| 要求 / 合理回归 | 公开依据和实现 | 新改断言 / 冻结测试 | 结论 |
| --- | --- | --- | --- |
| 存在且为 null 时 exists:true 为真 | user_prompt；models.py:829 的 event.get(k) 将缺字段与None混同；859 的 item is not None | test_event_pattern_with_exists_event_filter 新 assert foo_exists.matches_event(detail.foo=None) | 直接覆盖目标；历史 noop 此断言 False |
| 存在且为 null 时 exists:false 为假 | 同一 existence 语义的补面，旧正反测试结构 | 同 F2P 新 assert not foo_not_exists.matches_event(detail.foo=None) | 合理对称约束，非另一隐藏功能 |
| 保留缺字段、普通字符串、非叶字典的存在性语义 | 公开 test_event_pattern.py:23–45 | 同 F2P 原断言全保留；bar 存在/缺失也检查 | 区分 missing/null；不是仅加入 None 总为True 的测试 |
| 事件应真实投递至 CloudWatch logs，保留原字符串事件 | 公开完整 MWE | 第二 F2P test_moto_matches_none_value_with_exists_filter：source/detail-type、foo/bar各exists:true，投递字符串与null两条，读取日志后 detail 列表完整相等 | 覆盖公开集成路径和顺序；无只验计数的替代。日志 eventId 在本 base 为递增计数（logs/models.py:30–43），不是随机 UUID |
| 原有 allowed values、nested list/string、prefix、numeric、dump | test_event_pattern.py:8–20、48–105 | 全部对应 P2P 正文含5组数值参数和2组dump都已读 | gold 未见具体回归；不是枚举所有 JSON 类型 |
| 原有发送日志结构、时间、字段 | integration.py:12–68 | P2P test_send_to_cw_log_group | 已读正文；历史通过 |
| SQS/FIFO/custom event bus | integration.py:71–251 | 三条执行但不在冻结12个P2P中 | 已读正文且历史17项全过；不能把它们称为评分必过参考项 |

test.patch 全文及两个目标文件全部旧正文已读：test_event_pattern.py 1–105、test_events_integration.py 1–251，并逐条读了新增集成测试。F2P共2、P2P共12、派生命令实际17项。新增集成用同文件 import 的 mock_events/mock_logs/sure、ACCOUNT_ID，无额外下载 fixture；输入都在测试中构造。两条新存在性断言与一个完整 detail 列表断言的来源已逐项追溯。

## gold、调用者和替代路线

gold 增加唯一 UNDEFINED 对象，event.get(k, UNDEFINED) 将真正缺失和显式None区分，exists 判断改为非dict且非UNDEFINED。它保留原来的“只匹配叶节点”规则，未改公共 API 签名或强制 solver 使用该 sentinel 名。合理替代是递归匹配时传递字段是否存在的布尔标识，在 exists 分支使用该标识并保留非叶逻辑；外部行为测试可接受。只把 item is not None 删除会同时把缺字段判存在，现有同一F2P的旧断言会挡住这种自然部分实现；只修 logs 投递、不修 EventPattern 的旁路也会被直接单元F2P挡住。

已读模型链：EventPattern.matches_event/_does_event_match/_does_item_match_filters/_does_item_match_named_filter（818–886），Rule.send_to_targets（119起）、_send_to_cw_log_group（173起）、put_events（1164起）及 test_event_pattern（1244的NotImplementedError）；responses.put_events 委派和 test_event_pattern 入口已定位。集成链对 Detail 做 json.loads，None 会保持为None，不要求改日志序列化。未发现 gold 对已读类型与调用者的具体新破坏。

prefix/numeric 遇缺失或不合适类型、缺失中间嵌套对象等一般边界没有全面测试；base 本来也有直接 startswith/比较和递归访问，没有据此证明本次新增回归。单凭没穷举不判坏题。题面所述 AWS 行为和版本是原来源报告，本轮不远程核验。

## 安装配方消费链与历史证据

已读 T/image.json、build.log，T/{gold,noop}/recipe/recipe.json、candidate_test_script/eval_script 的 before/after 差异，E/recipes/getmoto__moto-5134.json、E/replay_with_install_recipe.py 与 E/run_compat_cases.py 的通用消费链，以及本题原始 ledger/log。

1. public digest `79117a6d6ffeaa6b146eb86c7959b7421ad4387c80b18fb4c835e4074ec10847`；T/build.log 明确 FROM 此digest。派生 image 为 `6aefb17daa7c99b95c250c36f9440e662cbc86f2f222aa17135264e35811d820`，Dockerfile 只有 COPY wheels 至 /opt/rh2/compat-wheels。没有安装 RUN，不能称镜像已启用 pins。
2. 配方将原 make init 包在 rh2_compat_install 内：先离线安装 boto3=1.28.57、botocore=1.31.57、s3transfer=0.7.0、urllib3=1.26.20，打印版本并断言 SQS service model protocol=query，再 make init、再次打印版本并返回原安装rc。
3. wrapper:22–31 的 code-root 是含 src/ 与 scripts/ 的 RH2根，映射本机应为 ROOT/rh2。61–74 把 revised_install 替换进 eval_script 和 candidate_test_script，105 dataclasses.replace，107–111 接回原真实 replay driver。run_compat_cases:64–80 同时传派生 image 与 recipe，未改 test.patch 或业务代码。before/after 除安装段外不变；这不等于正式 actor 自动消费。
4. T/gold/ledger.jsonl:1 对应 log `evallog_replay-er19-sqs_v1-getmo_949cd6be.eval.log`：547–551 离线安装成功、版本与query协议；839–846 原make后版本仍为pins、install rc0；856执行两文件，862共17项，933/947两F2P passed，948共17 passed/rc0。
5. T/noop/ledger.jsonl:1 对应 `…_ee16eb53.eval.log`：510–514/802–809同样安装链；819两文件；837–841 null exists返回False，890–896/980–986集成只收到字符串事件；1062–1068两F2P failed、15 passed/rc1。不是安装错误替代目标失败。

冻结评分 gold F2P2/2、P2P12/12、reward1；noop F2P0/2、P2P12/12、reward0，参考均到场。两者 observation import=/testbed/moto/__init__.py、3.1.9.dev；UID54322、deny_all、2CPU/4GiB、可写 conda 前缀，峰值约281–288MiB仅属历史 grader。candidate.apply_user=agent/54321 是应用补丁；没有开发会话证据。原件已重读，不称独立重跑或本轮CPU成功。

## 公开 actor 开发需要

| 操作/资产 | 可见依据 | 现有证据范围与缺口 | 最小验证方向 |
| --- | --- | --- | --- |
| 导入 moto.events/models 并跑存在性公开旧测试 | base Makefile:17–19、requirements-tests 中 pytest/xdist/sure；纯单元 test_event_pattern | grader 已安装，actor 的 Python/PATH/包来源未实测 | agent 实际工具 shell 打印 sys.executable、moto.__file__、boto3/botocore版本，窄跑公开 test_event_pattern.py |
| 执行公开 mock_events/mock_logs 原例 | 题面第二测试，公开 integration 日志测试 | 本地内存事件/日志，无必需 live AWS 或外部数据；actor能否导入对应依赖待验 | 用明确 region、mock 装饰运行原例，区分初态目标失败与导入/环境错误 |
| SQS 相关公开回归 | integration另外3条；历史修订为query协议 | pins只由 grader安装脚本启用，正式actor仍public image；是否需要actor派生/启动安装必须明确 | 如选择运行该文件，核实际 SQS模型协议及回归；不把COPY当安装，也不要求全仓测试 |
| 子模块/其它资产 | gitlink仅 tests/terraformtests/terraform-provider-aws@f34a786…，.gitmodules可见 | 不在EventPattern/Logs/SQS调用链；静态内容未导出不是运行缺资产 | 本题无需为Terraform子模块申请下载 |
| 可写/可提交文件 | 非测试源 moto/events/models.py 足够 | 工作区默认可写；系统安装权限不由grader前缀可写推出 | 验证候选源码在actor命令中生效；无需提交测试或环境产物 |

## 投影、评分与公开面

当前 prepared_task_face.py:312–335、trusted_projection.py 和 manager.HygieneRules 已读：test_globs=()，恢复/保护两个官方文件 `tests/test_events/test_event_pattern.py`、`tests/test_events/test_events_integration.py`，不是一律排除所有测试。gold 的 moto/events/models.py 在 included_paths，合法布尔标识替代路线也不必碰恢复文件。未见本题 test.patch 混入普通源码。其它配置或 helper 可影响测试是一般候选面，不凭一般可篡改性新增题特有坏题结论。

scoring.parse_eval_log_v2、swegym_parsers.parse_log_pytest 与 manager.execution_failure_trigger/classify_execution_failure_shape 已读。三条SQS普通测试虽执行但不在冻结参考中；若会话正常完成、参考都通过，仅它们失败/rc1不自动使reward0，全局收集/执行失败另判。历史选择修复它们使完整命令通过，应如实记环境证据，不能擅自扩为新的评分门。

正式 rollout_spec_from_view 取public image与bundle；render_user_prompt只拼issue，public_hints仍可从bundle看到。profile固定agent54321、默认资源和受限网络为源码事实；/root/.rh2_bash_env与隐藏/root的激活效果、工具进程环境、消息是否含hints均待actor核验。环境缺证不是题目不成立。没有实际模型、token/费用或稳定性采样，本轮不填这类结论。

## 关系、暴露与唯一下一步

同上下文私有审7584/5752；两题后续base的events/models.py都已有UNDEFINED及存在性修法（5752:35/839/868；7584:40/888/917），是跨版本答案包含关系。不能仅因同仓认定相同任务；跨题solver任务划分与暴露应记录。本人已见gold/隐藏测试/原始运行，不是独立公开求解者；未读主审/旧结论/history。

唯一优先下一步：做正式公开 actor 开发路径的 CPU 验证，明确是否仍用public image或已版本化的actor配方，在agent54321实际工具shell中记录UID/HOME/cwd、解释器/导入来源、依赖版本与必要权限，窄跑公开EventPattern旧测试和mock_events/mock_logs原例，并验证源码编辑可生效。base原例应呈现目标失败，而非要求未修代码通过；若选用sqs_v1资产，必须实际启用并观测消费链。此建议不授权本轮执行，亦不等于正式模型准入。
