# getmoto__moto-7584：无质量历史初稿

本稿先于本题历史门禁保存；仅静态阅读，没有运行项目、测试、容器、安装或联网。暂定 `needs_review / static_review`，用途限 `development_diagnostic`。有两项具体题意—验收冲突，不能因已有 gold=1/noop=0 将本题列为可直接探针候选。

路径约定（均相对 `.`）：`PUB=runs/swegym_quality_batch02_20260921_v2/public/getmoto__moto-7584`，`PRI=同包/private/getmoto__moto-7584`；`RUN=runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-7584`；`S2=docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest`；`RH2=rh2/src/repoharness2`。`GLOG=RUN/gold/eval_logs/evallog_replay-er19-iw1-getmoto__7e7ff56f.eval.log`；`NLOG=RUN/noop/eval_logs/evallog_replay-er19-iw1-getmoto__befbc4a3.eval.log`。下文公开源码路径从 `PUB/base/` 起算。

## 1. 版本、公开输入与初态

- 固定 base=`cc1193076090f9daf90970db286b6b41581dd8bc`，tree=`63d237e03a2a4e7fbc31e324013809e31565e6bd`；`PUB/base_identity.json:3-12` 记录 2531 个跟踪条目均物化，无 gitlink/LFS/symlink 缺项、没有 `.git`。采用协调层全包字节核验，本人不重做逐 blob 核验。
- `PRI/source_refs.json` 的三个精确 S2 原行均为 110；逐题元数据比较确认 public/grading/validation JSON 与包内对象一致。test patch SHA256=`5b1c7b7a6b655d9d226d72f899f76c761e41c4430c81b4c09e809e670500f99f`；gold=`4259577987a8f90d16046a73060c2d3f5b3c8a7d19ace77c2a7b1c6104e7bbea`。不是相邻任务材料错配。
- issue 明示：application 协议订阅不存在 endpoint 应报 `InvalidParameterException`；服务 Code 为 `InvalidParameter`，正文以请求 ARN 结束（`PUB/user_prompt.txt:3-4`）。具体复现先成功订阅，再删除 endpoint，再向原 topic 重订阅，末次应报错（`:23-39`）。首次合法订阅属于明示应保留行为。
- `SNSResponse.subscribe → SNSBackend.subscribe`（`moto/sns/responses.py:221-255`）先查重并直接返回旧订阅（`models.py:514-517`）；`delete_endpoint` 只删 endpoint 字典、不删订阅（`:714-718`）。初态可解释题面失败。历史 no-op 的实际失败只证明另一条“无旧订阅”的路径没有抛异常（`NLOG:609-622`），不是已执行题面原例。
- issue 自报 5.0.3，源码 `moto/__init__.py:4` 是 5.0.6.dev，`setup.cfg:3` 的包元数据是 4.1.0.dev。原日志 editable 安装显示后者，导入观测显示 `/testbed/moto/__init__.py` 和前者；不能据版本字符串宣布错包。
- 当前 `render_user_prompt` 仅渲染 issue（`RH2/envpack/bundles.py:282-289`）。`public_hints` 保留禁止改测试、conda 已激活等原字段，是否进入 CLI 实际消息未验；公开 bundle 本身会被投放（`prepared_task_face.py:342-357`）。本题合理修复可只改非测试源码，原禁止改测试指令不阻断该路线。

## 2. 公开要求与验收的双向映射

冻结奖励引用：F2P=1、P2P=19，均在 `tests/test_sns/test_application_boto3.py`；唯一 F2P 是 `test_publish_to_deleted_platform_endpoint`。执行选集由 test patch 路径产生，实际命令 `pytest -n0 -rA tests/test_sns/test_application_boto3.py`（`GLOG:607`、`NLOG:579`；`RH2/envpack/spec_vendor.py:164-191`）。这三个概念分别是奖励引用、执行选集、实际阅读范围，不能互换。

| 公开要求/合理旧行为 | 公开依据 | 具体断言/调用及反向依据 | 覆盖判断与证据 |
| --- | --- | --- | --- |
| application + 不存在 endpoint 应拒绝 | prompt:3-4 | F2P 先建 GCM application/Disabled endpoint/topic，再删 endpoint；`pytest.raises(ClientError)`（`PRI/test.patch:15-38`） | 部分覆盖。真实 no-op 因 DID NOT RAISE 失败；gold 该 case 通过。测试名虽叫 publish，实际调用 Subscribe。 |
| 已有订阅后删除再订阅也应拒绝 | prompt:23-39 | F2P 删除前完全没有 Subscribe；19 个 P2P 也没有 application Subscribe | **核心原例缺失，gold 明确漏修**。gold 在旧订阅提前返回之后才加校验（`gold.patch:5-18`），其私有注释主张旧订阅可暂时复用，与公开预期相反。该注释不是公开规格，也不是 AWS 实测证据。 |
| 有效 endpoint 的第一次订阅成功；有效重复订阅幂等 | prompt:23-27；`models.py:514-548`；公开 `test_double_subscription:29-43` 为 SQS 协议 | F2P 没有成功 Subscribe；本模块 P2P 的 publish/create endpoint 不是 Subscribe 正例 | 未直接保护，但不单凭此普通覆盖缺口判坏。静态 gold 对有效 application 路径继续查 topic/建订阅；自然部分实现“一律拒绝 application”有可能通过本冻结选集，本轮不另造攻击补丁。 |
| 服务错误 Code=`InvalidParameter` | prompt:4；`moto/sns/exceptions.py:45-49` | F2P `err["Code"] == "InvalidParameter"`（patch:39-40） | 有公开依据，检查外部响应而非内部类名。`ClientError` 不单独验证动态 SDK 异常类，但 Code 与现有错误封装一致。 |
| 错误正文使用请求 endpoint ARN | prompt:4；贡献测试约定 `docs/docs/contributing/development_tips/tests.rst:13-24` | F2P 精确要求 `... endpoint arn{endpoint_arn}`（patch:41-44）；gold 同样硬加 `arn`（gold:15-17） | **与公开文本冲突**。`PlatformEndpoint.arn` 本来以 `arn:aws:...` 开头（models:347），因此验收要求 `arnarn:aws:...`。遵从题面且不多加 `arn` 的实现会在此断言失败；这是静态反例预测，尚未实跑替代解。 |
| 缺失 endpoint 的 GetEndpointAttributes 仍为 NotFound；删除幂等 | `models.py:699-718,1088-1090` | P2P `test_get_non_existent_endpoint_attributes:311-326`、`test_get_missing_endpoint_attributes:329-333`、`test_delete_endpoints_of_delete_app:473-492`；`test_get_list_endpoints_by_platform_application:270-275` | 有关回归受引用保护，19 个 P2P 两角色均通过。阻止把共享 `get_endpoint` 全局改为 InvalidParameter；gold 仅在 Subscribe 捕获，不破坏原异常路径。 |
| Endpoint 创建、属性、重复 token；enabled/disabled publish；application CRUD；SMS 属性 | 同模块旧测试 13-492 | 其余 P2P 检查 application/endpoint ARN、属性回读/修改、重复 token 幂等或冲突、删除后列表/NotFound、publish 正例和 EndpointDisabled、SMS 属性筛选 | 全部 19 个 P2P 测试体已读，可按这些同类行为合并解释。它们支持相邻生命周期回归，不支持“整个 SNS 订阅已回归”。 |
| SMS/HTTP/email/SQS 订阅、订阅属性、分页等旧行为 | `test_subscriptions_boto3.py:15-104,174-310`；response:229-255 | 本人已读相关公开测试；**不在上述冻结 P2P，也没被这次命令执行** | gold 的 application 分支静态不影响这些协议；仍须按改动选择窄回归，不把阅读当运行通过。 |
| CloudFormation topic 内联订阅 | `models.py:128-145` 直接调 backend | 冻结选集无相应 case | backend 校验可覆盖该调用者。response 层替代解不能仅因位置不同否定，但须解释其直接调用者行为。本轮未读完整 CFN 测试链。 |

新增测试只有这一函数，没有修改其它断言。其 fixture `tests/test_sns/__init__.py:11-50` 默认在 `mock_aws()` 中以 `mock_api_key` 调用；开启 `MOTO_TEST_ALLOW_AWS_REQUEST=true` 才读 SSM/Firebase 并可能 SkipTest。`NLOG:592` 明示本次走 mock；gold 日志 20 项全 PASSED、无 skip。Enabled=false 只是已被删除资源的前置属性，不能据此新增“禁用 endpoint 不许订阅”的要求。随机 UUID 只构造独立名称；断言动态拼接真实 ARN，不要求固定 UUID。finally 清理 topic/application 无独立业务断言；若前置创建异常，局部变量清理可能遮蔽错误，但本次两角色均已达到目标调用，没有这种执行异常。

## 3. 合理解、自然部分实现与 gold

一条不依赖 gold 的合理实现：在 Subscribe 的 application 分支、查重返回之前判断 `endpoint in self.platform_endpoints`，不存在时用现有 `SNSInvalidParameter` 构造题面正文；也可复用 `get_endpoint` 并在此边界转换 NotFound。应保留其它 API 的 NotFound、正常重复订阅，以及其它协议；不需要新增私有 helper 名或改数据库结构。测试没有 Mock 调用形状/内部 helper 的约束，误拒疑点集中在多出的 `arn` 文本。

gold 只改 `moto/sns/models.py`，复用已有 imports/异常，无新增依赖或无关文件。但它本身就是自然的部分实现：只在“新订阅”分支校验存在性，因此通过本 F2P 却保留题面原例。另有对照可能是一律拒绝 application；因选集中没有成功 Subscribe，不排除被放过，暂不把尚未执行的推断写成已证评分漏洞。

跨账号/区域的存在性、多参数同时无效的报错顺序和清理旧订阅不是题面明示要求；本轮不据这些边界增设验收。gold 私有注释声称 AWS 行为不能消解公开题意冲突；本轮没有联网求证真实 AWS。若维护者确要改成该语义，应形成题面/验收修订，不能悄悄当作原题已修。

## 4. 既有真实运行与环境适用范围

| 原件 | 可确认事实 | 不能外推的结论 |
| --- | --- | --- |
| `RUN/image.json:2-11`、`RUN/build.log:19-28` | 正式公开 digest=`sha256:3b263c0c4745d890400b7beaf08c10b5413f86ae7983dd4bf14d93e43cd2fbf9`；派生 ID=`sha256:5d879f39ae06cd7e1245af6a278fb8a680227331ca9810d2e9a3a450d6ee8f40`，只 COPY setuptools72.1.0/wheel0.43.0/packaging24.1 wheels 并设 `PIP_NO_INDEX/PIP_FIND_LINKS`，保留 base 层 | COPY 不是安装，不能据镜像构建宣布候选安装已完成。 |
| `runs/env_recipe_repair_20260919/install_wave1/run_install_wave1.py:24-62` | 通用构建消费本题 pins，逐角色以 `--derived-image`/`--derived-image-recipe install-wave1:getmoto__moto-7584` 调真实 replay_grade。没有本题另一个安装覆盖分支 | 正式 actor 仍取 public image；该脚本不是正式 actor 配方消费的证据。 |
| GLOG:434-602；NLOG:408-574；`Makefile:16-18`、requirements-dev:1-2 | 两角色实际 `make init`，分别完成两次 editable 构建/安装（直接 `-e .` 与 requirements-dev 的 `-e .[all,server]`），均在离线 wheels 搜索路径下完成，install RC=0 | 完成证据来自实际安装日志，而非 COPY 或最后 RC 单独推断。未人工逐行复核全部已满足传递依赖版本。 |
| `RUN/{gold,noop}/ledger.jsonl:1`、gold diagnostics:39-41 | grader 身份 `rh2grader/54322`；deny_all；testbed prefix 可写；2 CPU/4 GiB/shm64 MiB；导入观测 `/testbed/moto/__init__.py`、5.0.6.dev。gold/noop apply_user 均是 `agent/54321` | apply_user 只说明补丁应用阶段身份，不是 solver/actor 验收。导入观测仍是运行输出，不能当不可伪造证明。 |
| GLOG:607-652；NLOG:579-658；相应 ledger:1 | 都收集执行20项；gold 20 passed、test RC0、F2P1/1/P2P19/19、reward1；noop唯独目标 F2P DID NOT RAISE、19 passed、RC1、reward0；missing/skipped=[]；无全局执行失败 | 只证无旧订阅的目标行为分差；普通 pytest RC 与冻结引用判分分开，本题恰无额外非引用失败。不等于题面原例执行过。 |
| 两角色 artifact `stage.json`/`baseline_manifest.json` 的元数据、gold `candidate.patch`、`projection.json` | HEAD=固定 base；runtime image=上述派生 ID；gold 仅 models.py 纳入投影、noop 无变更；gold candidate.patch 与本题 gold 内容对应 | 不重复协调层整包哈希核验；未把所有 manifest 条目重新人工检查。清理无失败由 ledger/driver 提供，未另实测重置/并发/重复稳定性。 |

此前 `PRI/environment_record.json` 的 `status=verified_environment_pair`、checks 和 observations 摘要已见，亦见其中 analysis/history 路径字符串；**没有打开这些链接或任何质量历史**。本节结论已以指定原始镜像记录、构建脚本、账本、安装日志和测试正文复核，不能把“fresh”解释成从未接触环境摘要。

## 5. 开发条件与交付边界

| 需要的操作/资产 | 公开依据与现有证据 | 当前缺口及最小验证（仅建议，未执行） |
| --- | --- | --- |
| 找到入口并导入待改源码 | response/models 路径明确；setup.cfg:27-37；历史 grader 已从 /testbed 导入 | 正式 actor/54321 实际 shell、PATH、解释器和工具待验。先 `python -c 'import sys,moto,boto3,botocore,pytest; print(sys.executable,moto.__file__)'`，应命中当前源码。 |
| 必要包、editable 安装、写权限 | pyproject.toml:1-3、Makefile:16-18、requirements-dev/tests；派生 grader make init 成功 | actor 是否消费离线 wheel 资产、conda 激活和包前缀权限未知。若现有源码直接可导入，则本纯 Python 条件修复不必强行重装；确需安装时由实际身份验证离线路线，不能假定 agent 可写 grader 获准前缀。 |
| mock 资源与网络 | `sns_aws_verified` 默认 mock；题面所有资源可在进程内创建；无 gitlink/大资产缺项 | 最小复现无需真实 AWS/Firebase/SSM 服务、密钥或公网。建议显式 `MOTO_TEST_ALLOW_AWS_REQUEST=false TEST_SERVER_MODE=false TEST_PROXY_MODE=false`。准备可预置包；解题/候选安装/测试各阶段不据 grader 推断公网权限。 |
| 验证与资源 | 已有原件在2 CPU/4 GiB运行目标模块；测试耗时 gold2.899s/noop2.544s、历史峰值188.156/207.281MiB见账本 | 仅是该 grader 单次观测；正式 actor 的 tmp/home、资源、稳定性未验。可按公开读者命令 B 复现，分别窄跑 application/subscriptions 两模块；没有本题必需编译器或外部构建产物证据。 |
| 可提交路径与恢复 | `PRI/test.patch:1-3` 只触碰 `tests/test_sns/test_application_boto3.py`；`prepared_task_face.py:312-336` 固定 `test_globs=()` | 官方只精确恢复该文件，本题业务修复 models.py 不受覆盖；GLOG:264-304 实际 checkout 固定 base 后注入官方 patch。默认测试名通配为空，不能照旧提示称所有测试改动永不计分。`additional_exclusions=[]`，没有本题特有额外排除依据。 |

tests/__init__.py、tests/test_sns/__init__.py 和 setup.cfg 是会影响测试的候选控制面，已读相关配置/fixture，但未做篡改探针；不因理论可改就新增路径排除。本题 test patch 没混入生产源码。实际 actor `.git`、可见缓存/包/祖先历史和工具网络尚未验，静态无 `.git` 的包不能证明运行环境无答案；派生镜像只补构建工具 wheels，未见目标修复被预装的具体证据。

## 6. 八方面覆盖、唯一优先实验与门禁

八方面已覆盖：公开需求及消息局限；版本/初态与原始 no-op；新增全部断言/fixture和全部19个P2P；合理非gold路线及具体精确字符串误拒疑点；调用者/相邻回归与gold漏修；开发依赖/资产/四阶段网络/权限/资源；精确官方恢复及投影；任务关系与用途。本轮未读其它题，未确认同族/重复关系；题面未直接给修复代码。没有真实 solver 轨迹、token/费用、目标基座难度、actor CPU、重复稳定性、全量SNS/CFN回归或答案泄漏实测。未知费用留 null，不能外推训练适用性。

**唯一优先实验：在隔离、固定配方中做一次“公开复现—冻结评分”对照，使用已有 base/gold 与一个按公开要求实现的候选。** 候选只在旧订阅返回前校验 application endpoint，使用题面正文，不改测试/奖励/控制面。先在 mock 里验证有效首次/重复订阅，然后删除 endpoint、重订阅原 topic；再对另一 topic 用已删除 ARN 首次订阅，核异常类型、Code、题面正文及400。最后用原冻结F2P/P2P评分。静态预期：gold原例仍成功，候选修复原例却因 `arnarn` 消息要求在 F2P 被拒；实际结果和导入来源必须另存。它同时区分核心漏测/gold不完整与误拒疑点，无须机械再造第二个坏补丁。

若实验证实，应分别记录两项任务修订建议：补上题面明确的先订阅再删除再订阅行为；解决题面与精确错误文本冲突。不得为保住 gold 自动把原题改成“只查新订阅”，也不在本轮修改原件。本题先保持 `needs_review/static_review`；actor 条件缺项另外保留，不把语义争议归结为环境失败。

实际阅读：指定四个方法文件及它们明确链接的记录定义/40项编号；本题 public 根材料、已封存 public_read；private grading/test/gold/validation/source_refs/run_refs/environment_record；上表精确S2行、镜像/build脚本通用入口、两角色账本和日志相关原文、artifact元数据与gold candidate.patch；公开 application 模块全部19个旧测试、SNS fixture与tests初始化，subscriptions选段；models/responses/exceptions/core异常/装饰器及开发依赖选段；必要当前RH2控制面。未通读全仓、全部订阅/CFN测试、botocore异常映射源码和日志中所有依赖明细。少量长输出发生截断，关键测试/安装/断言段已定点重读；不把未呈现内容当已核验。一次控制面检索包含不存在的 `RH2/boundary` 路径并返回错误，随后改用实际 manager/face/vendor 文件；不是项目执行失败。

本稿保存后暂停。未经协调者SHA封存与明确开放 `I2/history/getmoto__moto-7584/refs.json`，不读历史、不生成delta/card/record，不进入5752原件阶段。
