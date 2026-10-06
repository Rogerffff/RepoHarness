# Pandas 50319 Qwen3.6 首轮非作者窄核（2026-10-04）

**结论：本臂原 1 分可信，完整候选通过当前公开“None 或正确格式”契约和 109 条来源 P2P；未发现误奖、误拒或需阻断的题级缺陷。** Qwen 的源修法保留点号分隔 token，actor 真实重建后原报错输入返回正确格式，既有模块自测闭合；正式 grader 又独立重编译，115 个物理节点全通过。正式两条新增断言没有直接打印返回分支；本臂没有 `pd.to_datetime` 数组路线的动态观察，不能替用旧 CPU None 对照。单次结果不代表稳定成功率或训练资格。

仅核 `gpu1003-pandas50319-qwen36-a1` 的新候选和新增执行证据。旧 CPU 矩阵、公开 actor 与 Coder 首轮核查按原版本复用，没有重复运行或审查；双模型总回执只承担执行回告，语义结论由本核原件支持。

## 范围、独立性与完整性

本非作者 subagent 没有编写或执行本次求解、评分或题主分析。先读 AGENTS、现行三方流程和覆盖优先边界，随后从封存原件独立解析；先完成新臂核查，再读新 Qwen 作者分析作最终比对。已读旧 Coder 报告及题主交接摘要，因而不称完全盲审。只进行本机只读 JSON/日志/轨迹解析、大小/SHA 重算、base64 解码、tar 成员只读及内存文本 diff；没有 SSH、Docker、CPU/GPU 运行、安装、候选导入或新采样。唯一写入是排他新建本报告，未动原件、旧报告、共享文件和总账。

记快照根 S=`runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pandas50319-qwen36-a1/`，作业根 J=`S/queue_qwen_next12_v1/results/gpu1003-pandas50319-qwen36-a1/`，身份读回 D=`S/diagnostics/QUEUE_QWEN_NEXT12_V1_gpu1003-pandas50319-qwen36-a1_before/`。本核逐件重算 closed manifest 所列 **227 件、280,036,452 字节，全部大小和 SHA 一致**。目录实际 229 件；另外两件是 closed manifest 自身和 `sync_receipt_v4.json`，不在 227 的统计范围内。

- GPU 配对总回执：`runs/ordinary_gpu_probe_20261002/migration_20261003/probe-swe-pandas-50319-20261003-v1_pair_execution_receipt_v1.json`，4,066 字节，SHA256 `3bffd0623ab64925274dc9b879692f3902d71d2b6fb7aa2d367b031cb0497f0e`。
- 新臂机械回执：同 migration 目录 `pandas50319_qwen36_execution_receipt_v1/execution_receipt.json`，122,922 字节，SHA256 `e1b22549ff2dcaae46a5a53bf82701001a17a5239701299c5fa54f4c234e3c6d`。未把它的语义/训练 null 填为通过。
- closed manifest：`S/qwen_next12_closed_v1/gpu1003-pandas50319-qwen36-a1/closed_manifest.json`，49,886 字节，SHA256 `bba3c256524179954fde99df157d2642e60f35881bb971eb48cdc3701e99f3d3`。
- 原 eval.log：465,001 字节，SHA256 `eb0e961f958bdaa2f1c2c265973550685ea186fbc335f31ce73964c4906ce100`；原 trajectory：264,044 字节，SHA256 `7a64a1a0c0ec92cf89567ddd1d86503bf29db162a6bc5706ffd0491f1324f52b`，与 harness 副本逐字相同。

## 原分、参考来源及七个绑定成员

`J/grading/report.json` 原 reward=1、outcome=resolved、F2P=2/2、P2P 失败=0/109；failure_category、execution_failure_stage、infra_failure_detail 均 null。完整候选干净重放，test_files_modified=false、forbidden_path_touched=false，patch hygiene=clean。

从本臂 `S/prepared_dask_pandas_four_code8_v1/pandas50319/private/host_grading_views.jsonl` 独立将每条参考映射到原日志：2 F 精确匹配；109 来源 P 为 94 精确引用、12 个按空白截断且唯一对应的旧引用、3 个显式绑定组。组内成员数为 1/2/4；共覆盖 **113 个互不重复物理 P 节点**，加 2 F 正好覆盖原日志全部 115 节点。全部 PASSED，无缺席、skip、未归类或重复；原 P 列表与 revision.original_pass_to_pass 逐字相等。以下成员共同前缀为 `pandas/tests/tslibs/test_parsing.py::`，行号指本臂原 eval.log。

| 完整成员后缀 | 状态 | 行 |
| --- | --- | --- |
| `test_is_iso_format[%Y\\%m\\%d %H:%M:%S-True]` | PASSED | 5048 |
| `test_guess_datetime_format_with_parseable_formats[2011-12-30 00:00:00-%Y-%m-%d %H:%M:%S]` | PASSED | 4988 |
| `test_guess_datetime_format_with_parseable_formats[2011-12-30 00:00:00.000000-%Y-%m-%d %H:%M:%S.%f]` | PASSED | 5012 |
| `test_guess_datetime_format_no_padding[2011-1-1 00:00:00-%Y-%d-%m %H:%M:%S-True-None]` | PASSED | 5043 |
| `test_guess_datetime_format_no_padding[2011-1-1 00:00:00-%Y-%m-%d %H:%M:%S-False-None]` | PASSED | 5042 |
| `test_guess_datetime_format_no_padding[2011-1-1 0:0:0-%Y-%d-%m %H:%M:%S-True-None]` | PASSED | 5039 |
| `test_guess_datetime_format_no_padding[2011-1-1 0:0:0-%Y-%m-%d %H:%M:%S-False-None]` | PASSED | 5038 |

绑定字典 canonical SHA 为 `d2d78ebe7df4115b4d2d8e748fd83ff54e68c3234b3d91c814bff65c468097cd`，与实际消费身份相等。有效 test patch SHA 为 `0cef8c604fb79cd8d677087b28a09736751617e5aacfb312cb8fede48d3cae8f`，host view 的 test_patch 与 effective_test_patch 逐字相等。日志1684–1695行从精确 base 恢复 `test_parsing.py`，核其 SHA `71a22bdd…ff4d` 后正常应用补丁；1716–1728行 attest=恢复1/应用0/存在1/缺失0/setupOK1。

日志5015/5016行两条新 `[reported]`、`[another-dot-date]` PASSED；5066行 `115 passed, 3 warnings in 0.22s`。新测试真实调用 `guess_datetime_format`；返回非 None 时才检查 str 和 `datetime.strptime` 的完整日期、时间、微秒。这证明已验收的有限契约；日志4938行有点号格式警告，作为辅助证据保留，不把它改写成两例逐项返回值采集。私有评分材料未交给 actor，模型自测113条与正式115条范围不同。

## 原完整候选与重新编译

FP canonical digest 独立重算为 `sha256:de94997d6eae27396fc9bae092804438964885af028a539ce3b9d22b3a728612`；baseline manifest canonical digest 为 `sha256:3da93f2518e48272209d08a9045857954b4b5110e68ffa8a17946e653b3c504d`。result、attempt、projection 均相等；actor baseline census 和 grader rebuild census 字节相同。只读 baseline.tar 有2561成员，base HEAD=`1613f26ff0ec75e30828996fd9ec3f9dd5119ca6`。

99 个 FP entry 全部解码并独立核 content_digest；成员元数据与 attempt 相等，projection 按路径/顺序包含全部99件，没有过滤：96 add（43个 build `.so`、52个 `.o`、`test-data.xml`）和3 modify（`parsing.pyx`、生成 C、checkout 的 parsing.so）。payload 总59,090,036字节，FP JSON 78,815,910字节、审阅 diff 22,642,066字节。不把真实候选概括成只有4行源代码，也不把自测 XML 当正式评分。

baseline pyx 为38,455字节、SHA `5c8e81b9…48aa`；候选为38,636字节、SHA `bc4b3fdd53889ca5bd271472939ece5acc0236da5f5f863fa734f39d81c8556d`。独立内存 diff 只新增 `_fill_token` 中 split 后的 `if not seconds: return token` 及两行解释；已有秒格式补齐、微秒截取与最终匹配逻辑保留。它处理点号日期分隔符，不将空 seconds 改为0。生成 C SHA `52630f8d…c96` 的15342–15356行真实判断并返回 token，不是仅同步注释。

actor parsing.so 从 baseline 492,144字节/SHA `127481b2…425c` 变为496,240字节/SHA `c11977c01ec3ef0b37356d5211360b338e44e7da85fa979226144a6b2fec6ccf`；build 与 checkout 两份候选 so 相同。编译时用了管道 `| tail -20`，因此后台 exit0 单独不能证明 Python build 的退出码，但扩展复制日志、不同原 `.so`、重启 Python 后原行为确实改变共同支持真实构建成功。

正式 grader 3156行运行 editable install；3165行 Cythonizing 修改 pyx，3873/3875/3880行依次构建、编译新 parsing.c、链接独立临时 build 的新 parsing.so，4014行复制回 checkout，4910行 installRC0。4920行新 pytest 进程执行唯一正式模块，5074行 testRC0。因此正式分不依赖搬入 actor 旧二进制。原 compile_probe=null 保留，最终 grader `.so` 没有单独SHA/mtime证据；日志证明编译流程，不冒充通用 compile_probe 已通过。

评分脚本digest=`38c1676d…39c4`、材料身份=`aec98b70…2979` 与实际加载资格账本 `ok:gold_ledger.jsonl:rpt_grading_a29b64e6` 相等；runner前后SHA均 `1cfac682…13a4`，runner_integrity_changed=false。保护4目录/1文件，EXPECTED_FILES1、missing0、protectOK1。

## 模型行为、自测质量和效率

405条轨迹记录中独立数得24个唯一工具调用，全部各有一次结果，协议层最多1个未返回。Bash17/Read6/Edit1；唯一 is_error 是修复前真实 ValueError（71→75行），不是候选失败或基础设施问题。

| 原轨迹行 | 实际行为和边界 |
| --- | --- |
| 39→43、71→75、85→89 | 先观察真实 lexer 的两个 `.` token、真实崩溃和 dateutil 解析，再用 Python 复制拆分逻辑定位空 seconds。没有声称直接追踪了私有 Cython cdef 的逐token执行。 |
| 167→171 | 仅编辑源 pyx；与最终 FP 小 diff 相等。 |
| 185→192、284–285、297→301 | 构建成为后台job，后来明确 completed通知、exit0及 parsing.so 复制。期间用10/60/60/90秒等待加进程/输出检查；最后 grep无匹配的辅助等待通知failed，不能误归为构建失败。 |
| 315→319 | 新 Python 中原报错输入明确返回 `%d.%m.%Y %H:%M:%S.%f`，伴随预期 dayfirst警告。此返回分支有本臂动态证据。 |
| 333→337 | 既有 guess_datetime 子集：62 passed、51 deselected、1 warning、0.15秒。 |
| 351→355 | 原输入有格式assert；另4个边界打印了格式，其中含无小数、纯日期、6位/9位小数。后4项没有逐项正确性assert，末尾“All tests passed”不能升级成4项独立oracle验收。 |
| 369→373、401/405 | 全既有模块113 passed、1 warning、0.17秒；候选XML也是113、errors/failures/skipped均0。该pytest也接tail，未独立保存pytest RC；完整footer支持模块结果，不凭管道退出码声称pytest独立RC0。最终原输入正确格式声明有依据，但不是全仓回归已验证。 |

后台构建与查看/等待确有重叠，不笼统称全程串行；220秒显式sleep及最初后台等待体现构建开销和被动轮询。独立读取测试、准备附带断言可在构建期间先做，是效率机会，不推断能并行执行依赖新扩展的自测。实际工具入口只有 Bash/Edit/NotebookEdit/Read/Write，没有 Task/agent，跨agent能力不可评估；SGLang max_running_requests1不等于执行层所有并行均不支持。

gateway25条请求均为生成，无count_tokens，序号1–25与25响应对应，全部HTTP200、stream_error null，24 tool_use+1 end_turn。累计input312,515/output5,518，cache0；单次input峰22,098、output峰639。adapter计数与CC相等，累计input不能当单个上下文。CC25回合、382.439秒/API34.707秒；gateway累计34.073秒，solve386.155秒。正常end_turn，harness0/completed，没有预算截断证据。原预算240回合/10,800秒/196,608上下文，25请求max_tokens都65536；CC modelUsage.maxOutputTokens32000原值保留。

作业15:10:38.067133–15:35:44.543467Z共1506.476秒，包括actor准备、求解、候选保存和评分。actor原sanitize73.419秒/trusted_init18.128秒；总评分994.782秒，受信准备591.119062秒、start_and_verify74.7048秒；test包装321.975505秒内含安装317.562秒/测试包装2.989秒，pytest本体0.22秒。cleanup/parser计时null，不填0；queue_wait0只覆盖本回执口径，不推全局排队零等待。

## 身份与双清理

本臂code_v8 source manifest SHA `09ddb8bf…9d`、entry SHA `bdf806bf…74c4`、固定inputs manifest SHA `2f20d271…231` 均已包含在逐件重算中。 对本快照所带旧Coder attempt身份副本仅做profile逐项对比，唯一差异是 `network.model_proxy_upstream` 的18082/18081；没有重复旧臂候选或语义验收。owner request两个封存副本相同，SHA=`10fa9a12…a2e2`；材料revision=`pandas50319-dot-date-full-bindings-v1`、公开bundle=`5c94214a…7d27`、grading bundle=`052e12f6…cc3`、environment package=`b2cc52ce…e6b5`，对应请求、input_check和实际评分身份。solver_prompt和attempt/prompt逐字一致，公开None契约已交付，未追加私有评分目标。

actor UID54321、testbed Python3.8.20。精确容器名/run_id筛出33个actor样本（15:10:47.412333–15:18:49.693321Z）与66个grader样本（15:19:19.833740–15:35:39.321228Z）；同角色container ID稳定，两角色actual image均=`sha256:a3f20f616f78963bee9c87426b8a93c28fb63a6ade97d0f444115279c28f859a`。镜像manifest `e645e434…ba21e` 是另一身份口径，不与actual ID混写。采样中grader峰4GiB、oom/oom_kill均0，采样空档未知，resource_facts/supply=null保留。

D的现场捕获时间15:10:37.790905–37.955768Z，engine/adapter前后ID/PID/启动时间相等、restart0、模型只读挂载；HTTP读回/model、bfloat16、context196608、TP1、max_running_requests1与实际服务配置相等。gateway实际model_sent=`Qwen3.6-35B-A3B`，download绑定repo=`Qwen/Qwen3.6-35B-A3B`、revision=`995ad96eacd98c81ed38be0c5b274b04031597b0`，manifest SHA `32bd30f6…52ab`。独立核列明37文件实际大小全相等，含26权重分片；files_count=40与列明37的元数据范围差异如实保留，不推断丢权重。未重新散列每个权重文件，也无GPU内存权重证明。

原gateway_audit.checkpoint_identity_verified=false、input_check.config_only=true/runtime_request_and_sglang_readback_verified=false、launch_facts.launched=null均保留；新增现场原件不能静默改原标记。typed actor训练租约和训练资格均未由本探针证明。

actor cleanup：container_rm0、container_left空、label容器/网络空、network/relay failures空、cleanup_ok=true；pre_drain residual0、gateway已撤销/active0/drained=true。grader status/result cleanup_ok=true，manager创建1/移除1，containers_open/supply_open/cleanup_failures空。终结同时有原job exit0、CC completed和精确PID1成功journal事件（15:35:44.571747Z）；不使用retired unit的not-found默认ExecMainStatus0作证明。不声称本核重新做现场最终残留查询或全机零残留。

快照当时paired_request_closed=false、机械回执paired_request_closed=null保留为当时状态；稍后GPU配对总回执each_model_first_once_complete=true，只表示两模型首轮执行完成。已有Coder独立结论与本臂分别成立后，才可在有限公开契约层面作双成功对照。

## 收口与剩余范围

本次stop condition已满足：新增原件身份与运输闭合、来源参考和七绑定成员覆盖完整、真实编译/测试/正常结束/双清理可追溯；没有需修实现或追加实验的blocking finding。新Qwen作者材料已完成最终比对，关键事实和边界一致，未发现需改作者结论的实质错误。保留正式两例具体返回值、数组端到端路线、逐项边界oracle、连续资源/权重身份的观察限制，不因此自动追加采样或要求重做已验CPU。当前用途是这一次首轮的可靠成功样本与验证行为分析，不授予稳定成功率、全仓正确性或训练资格。


## 作者材料最终比对

题主新分析 `tasks/pandas-dev__pandas-50319/probe_analysis_qwen36_and_pair_20261004_v1.md` 为11,804字节，SHA256 `e1e21658d7a3111429b66690ed5a1e90cd6d18b499905972b84d52ab038d3a3f`；结构化计数原件 `runs/category2_repair_20260929/pandas_cpu_20261003/gpu_analysis_20261004/pandas50319_qwen36_a1_v1/evidence.json` 为36,594字节，SHA256 `5e913c93f8a362115e069f413b472ad25e68e9b6f71f71bde21625bf69347cd0`。这两份SHA已独立重算。作者小source_delta与本核内存diff相同（只差说明性文件名）；99项、115物理节点、3组7成员、原返回格式、自测footer、token/回合/工具/计时、资源身份和双清理均相符。25个唯一assistant message ID另独立重数，不将60条流事件当生成次数。

作者明确保留build/full-module pytest管道退出码局限、其它4变体仅打印、正式第二输入具体返回未记录、无本候选数组观察，以及false/null和files_count40/列明37的范围限制；与本核相符。双模型比较的旧Coder结论只复用既有非作者核查，本轮没有重验旧臂或从单次效率差异推普遍优劣。无需补评、改材料或追加采样。
