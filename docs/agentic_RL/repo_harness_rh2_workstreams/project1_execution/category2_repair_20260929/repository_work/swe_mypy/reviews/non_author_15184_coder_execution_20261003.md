# mypy15184 Coder 首臂与两模型配对：非作者执行链窄核

日期：2026-10-03。角色：按 `review-standards.md` §10.4 担任 Production Tracer。范围为新增 `gpu1003-mypy15184-coder-a1` 的请求、公开交付、原 FrozenPatch（FP）、评分、身份与清理，以及与已收口 Qwen 首臂的有限输入对账。只读本地原件，使用本地 JSON/tar 解析、SHA 重算和源码静态阅读；没有执行 SSH、容器、CPU/项目测试或模型。本轮只新建本报告，不修改任何旧报告或原 evidence。审查者已见 gold/private，**不是 fresh 盲审**；不重审 Qwen 旧语义。

## 结论与适用范围

**Coder 首臂的执行证据可以收口。** 题主请求与实际公开题目 block 一致；原 FP 的 102 项全部进入评分投影，包含 97 个 cache、4 个候选脚本和 `mypy/messages.py`；完整 1422 项基线重建成立，正式 3 个 F2P 和 2 个 P2P 全部执行、解析并通过，安装 RC0、测试 RC0、raw reward1.0，actor/session 与 grader 两层清理正常。未发现本题请求、候选、材料或正式评分之间的具体身份矛盾。

两臂已有各一次执行结果，配对回执的 `execution_pair_complete=true` 和 `remaining_unexecuted=[]` 有原件支持。结论是两次普通探针的执行结果，不是候选语义、完整 mypy 回归、模型能力差异或训练准入的验收。所核冻结回执原样保留 `task_semantic_final_review=owner_pending`、`training_qualification=false`、`not_sent=true`、`request_returned=false`；题主后续语义收口与返回另有记录，本报告不回写此回执的历史状态。

## 原件封存与关键身份

下列路径从仓库根目录起算。

| 别名 | 入口 |
| --- | --- |
| `B` | `runs/ordinary_gpu_probe_20261002/` |
| `R` | `B/remote/` |
| `G` | `R/queue_v21/results/gpu1003-mypy15184-coder-a1/` |
| `Q` | `R/queue_v13/results/gpu1003-mypy15184-qwen36-a1/`，仅核配对引用与输入，不重开旧语义审查。 |
| `P` | `R/prepared_swe_three_code5_v1/mypy15184/`，两臂复用的准备材料与镜像读回。 |
| `C5` / `C7` | `B/frozen_code_v5/` / `B/frozen_code_v7/`，本地冻结源码。 |
| `GW` | `R/services_v19/coder/gateway/gpu1003-mypy15184-coder-a1/` |
| `AD` | `R/services_v14/coder/adapter/gpu1003-mypy15184-coder-a1.turns.jsonl` |
| `D` | `R/diagnostics/QUEUE_V21_gpu1003-mypy15184-coder-a1_before/` |
| `CPU` | `runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/`，只作已验材料、脚本与基线条目对照。 |

配对回执 `B/receipts/swe-mypy15184-nested-nominal-v2-20261003_two_model_v1.json` 的字节 SHA 为 `f3acea51e02fcf91931d43a10673a0945d543b165d8c87b3242354adb041e6fa`，与委托一致。独立核其 16 个证据文件引用的 SHA/size，以及另外 4 个关键运输源码在 C5/C7 两边的 SHA，均相符。

Coder closed manifest `B/migration_20261003/gpu1003-mypy15184-coder-a1_closed_manifest_v1.json` 的 SHA 为 `4041691fbaf1d14c4a8dc69a97eadc061ac18d15a3212b7fbb6adb5cef09ffe0`；其 142 个文件全部存在、SHA/size 全符，总 36,570,464 字节。142 是封存文件数，包含共用输入和其它题材料，不能计为本题 142 个结果；既有 Qwen 95 件封存亦不新增为本题执行数量。执行方 `B/reviews/mypy15184_coder_a1_execution_review_v1.json`（SHA `f24339e626224a5e460ad8667fb7b29e461d252c605e570f455b18d4f25ad8f6`）只作导航；关键结论来自本轮原件重算。

| Coder 原件 | 字节 SHA（不与 canonical digest 混用） |
| --- | --- |
| `G/result.json` | `081febbd9031b08a1d6349b24e663e2a5fe082f3215116128f89e5ad6a954d4d` |
| `G/attempt/attempt.json` | `1494edb0fc386420e0e02414b83bff7f5f74debb0a3a29dbf217b68123b87796` |
| `G/input_check.json` | `02ec08f60c3879bd8b6cc61cdedbd50f8ee6b66f6df8293c1c3d72bdad0728d4` |
| `G/attempt/frozen/frozen_patch.json` | `b78832a71c622967f0ff0171bf5defe85ba98374fc411e73a019c39f2c97c1eb` |
| `G/attempt/frozen/baseline_manifest.json` | `1019f5a9d08c1cda7676a9385f6a472613d391d7bc6c841c363466819a9ec689` |
| 正式 eval log | `e9f7d7d07016d00f3f7e189470de2cce228e2f74cc1555d41501d2df700f3a24`，26,130 字节。 |

## 实际调用链、公开交付与 code_v5→7

终态 `R/gpu1003-mypy15184-coder-a1_terminal_snapshot_v1.json` 的原题主请求 SHA 为 `623bc39612a9812e92b3c5ec218480e916e3c4dae219c4e4f17d7e85056e993e`；固定 request copy 重算相同。外层队列包装 SHA `58ec5f05665733294480b19d8672c947b27298036dd96d2b14967c97cee76f65` 是另一个对象，不能误判为题主请求换绑。终态 command 明确执行 code_v7 entry，进程退出0后记录 `evidence_ready`；attempt 未单列 `code_snapshot_id`，运行树身份依靠终态 command、固定输入和 source manifest 外部绑定，不补造字段。

真实链为 serial dispatcher → ordinary entry → shared solve attempt → actor 基线捕获/CC → quiescence/FP 导出 → `source_from_original` → `SWEGradingManager.grade` → parser/report → `manager.close`。`C7/rh2/experiments/ordinary_gpu_probe_20261002/entry.py:223–289` 直接加载原 baseline/FP、核 attempt/public binding、构建可信投影并评分；`candidate/*.diff` 是审阅运输件，不是评分输入。基线 census 只增加读回观测，重建通过才设 `baseline_rebuild_passed=true`；manager 在 `finally` 关闭。

首条实际生成请求 `GW/requests.jsonl` 的首个 user 有两个 text block：306 字节 CC 日期 reminder，以及 **1830 字节的题目 block**。后者逐字等于 `G/solver_prompt.txt`、`G/attempt/prompt.txt`，SHA 为 `2efeb37e86cb65e228a92d9623c73c31286bf5eaccacbff2935def2bd75ec8de`，与 Qwen 相同；不是整个 user message 都等于 prompt。题目 block 包含新版两模块复现及完整公开 brief；brief SHA `0fe106b96bd74d6f28ba226bdc2c8be1b67326048509a5636b8d600e35f3d1e7`，public bundle digest `77b85678b3f20ef5689e4a9b646518ae1247407ff44b250803563c11dce3ea7e`。prelaunch 实际 binds/mounts 为空，private host view留在宿主可信面。该检查限于首条交付和核过的材料，不声称完成全轨迹泄漏审计。

配对 `input_check.json` 的 task、预算、assignment、baseline policy、prepared manifest、host grading artifact、材料 identity、revision、grading budgets、public delivery 10 个字段全部相同。材料 identity 为 `bf000616fc92f2d7869bdb2039ab1fe0d9167e507a5bb15e6c5987ab033d8053`，revision 为 `mypy15184-nested-nominal-types-v2`，registry 为 `7abfdf350875e5d28c679ac196f20c8a44efdce184fa7be00ddf97cb2009740c`。`P/private/host_grading_views.jsonl` 与 CPU 已验件逐字相同（SHA `1ce37a96ae9140654e5604cc6f2570345a92928315b99131cb99b0ce6e2946ff`），实际 diagnostics 的 scripts digest 与 Q/CPU 都为 `eb6990fb1a94e807ee047e7e36029d27f37411fb590c4a36a33e42a6d8a68364`，五分区引用相同。

C5/C7 source manifest SHA 分别为 `37688573eeb6cd9ce11cc89eb55601fa8127feac7ed753f131bdf86ababed814` / `be705a777484c70af2afe9a34b6dd288bd85c2b1f536c6d57bd59aecb4eb0352`。两树的 ordinary entry、R2E solve、shared solve、frozen transport 4 个运输成员逐字相同；manager 也相同，SHA `1783533e1e3b66a57fcaa5a599a1da4f8e4e886318e24f040c6df91f294c1c1e`。本题 `SWEMypy15184TestFile`、`SWEMypy15184TestPatchRevision`、公开 revision 应用函数和 `SWEGradingMypy15184RevisionContext` 静态提取后逐字相同。

7 个共用成员确有增量：新增其它题的 revision/environment/context 分支，replay 的 Conan 固定镜像分支，ingest 从 swe17 换到 swe40，以及通用诊断 F2P bucket 名扩展。静态分支阅读未见本题参考或安装替换，本题实际材料、脚本、五分区和镜像读回又相同；这支持本题有限可比性，**不证明整树或全部行为等价**。两臂 sandbox profile 的差异是模型代理 upstream 端口18082/18081，不能把 profile digest 写成相同；Coder 服务 adapter 仍运行 code_v4 的只读挂载，这是服务层身份，不能与 code_v7 评分入口混为一谈。

## 镜像、完整基线和未净化候选

actor 实际 image ID 与 grader diagnostics 均为 `sha256:cda77e2d613176919d3c6fb8a0f1aae952a1f77a5d0170602db93c432867c025`，与 Qwen 相同。`P/actual_image.json`、Dockerfile 和 wheel census 证明该准备镜像仅 COPY 离线 wheels 并设置 `PIP_NO_INDEX=1`、`PIP_FIND_LINKS=/opt/rh2/build-wheels`；9 个 wheel 为 root:root、0644，目录0755，source/actual census逐项相同。准备时的 `actor_baseline_verified=false` 是准备范围，随后本次 actor 捕获及 grader 重建另有原件，不静默改写旧准备记录。

actor prelaunch/probe 已证 UID/GID54321、能力有效集0、NNP1，2 CPU/4GiB/512 PID限制及激活后的 Python prefix正确。grader 的冻结 profile 为候选 UID54322，manager 的 candidate exec/observation 均传该 UID；本次 prefix 属主观测为54322。包中未另留 grader 候选进程的独立 UID probe，故不把 prefix 属主或静态调用参数说成单独进程 UID 原件。诊断 `env_qualification=absent`、`resource_facts=null` 原样保留。

基线 canonical digest 重算为 `fdd59f846a872a5fb2680de446faf5d8a286db2237559c43c8b43874e82df1a5`；manifest 与 Q 字节相同，1422 条内容/模式与 CPU 已验基线相同。独立读取 Coder baseline.tar 的全部1422个成员，名称、类型、内容 SHA和契约模式全符，无多/少项；模式按契约归一为可执行100755或非可执行100644，tar原权限不冒充manifest的Git模式。tar字节 SHA `58e6844980ff148edb1ebbb207505162b222dd8eca1b9438c68503d82fe86f36`，16,711,680字节；不同于Q的tar封装字节不影响逐项内容对齐。actor与grader census逐字相同（SHA `5d6f0d161a576c62b4161ad3114dfa586e579f4a5ca5485b053fa021984f3fd5`），`baseline_rebuild_passed=true`。

原 FP canonical digest 重算为 `20de4d05bea9c2f046e56bf3212c98c85a8f82ba7e74bc32e6ed09991ca45f1a`，102项的 base64 内容 SHA全部匹配、身份绑定原 cda77…镜像与上述基线；classification 为 projectable。`grading/projection.json` 的路径序列与102项原FP完全一致，没有净化cache或脚本。全102项 applied-entry digest重算为 `96f2208183c6820cbd9c2f976aa1cb2eaa8a52770c640d4a99c284834637c6cb`，与报告 hygiene精确匹配；该digest是条目集，不是原FP或“清洗diff”的digest。

102项构成为97个 `.mypy_cache/` 文件、`a.py`/`b.py`/`correct.py`/`t.py` 4个新增脚本及1个修改 `mypy/messages.py`，均100644。没有候选测试文件改动。`messages.py` SHA为 `2ca8bce8da916a44cf9ef4e598085f1dcd9575a0bf1c4cba71869f6f0ebe330f`，与Qwen源码字节相同；完整FP不同，不能说两臂提交了同一候选。基线政策只省略 `.pytest_cache`/`__pycache__`，并未省略 `.mypy_cache`。报告 `hygiene=clean` 只表明本题路径规则下无剥离测试/禁区、重放完成；不等于cache或脚本经过独立语义验收。审阅diff的5,011,421字节和102 headers也如实保留，未另造源码净化评分件。

## 正式安装、参考、保护和终止

manager先验证/重建完整基线及应用投影，再以root恢复并应用可信测试补丁、读取root自证、保护控制面，随后候选身份执行安装与测试。正式diagnostics记录 restored1、apply0、expected/actual2、absent0、setupOK1；protected2、目录6、missing0、protectOK1。两份官方测试控制面与CPU相同。runner摘要安装前后均为 `bffa1d1e04c07d52b4d5db5941f0d97a8c71a68e29cca90c4bf5671ea66e1548`，未变化；观察到mypy从 `/testbed/mypy/__init__.py` 导入。该Python观测不是pytest同进程模块SHA证明，不扩大其证据范围。

正式 eval log 的安装段实际执行 `python -m pip install -r test-requirements.txt` 和 `python -m pip install -e .`，从离线wheel目录取包，成功构建并安装带dirty版本的 editable mypy。`RH2_INSTALL_RC=0`、`install_failed_commands=[]`、install_skipped=false；候选段完整、exec0、partial=false，随后pytest精确选择5项，5 passed in0.58s、`RH2_TEST_RC=0`。

| 正式参考分区 | 原件执行、解析结果 |
| --- | --- |
| original F2P 2项 | `testAssertTypeFail1`、`testAssertTypeFail2`，均成功。 |
| added F2P 1项 | `testAssertTypeFailNestedNominalTypes`，成功。 |
| original P2P 1项 | `testAssertTypeFail3`，成功。 |
| added P2P 1项 | `check-expressions.test::testAssertType`，成功。 |

均来自 `mypy/test/testcheck.py::TypeCheckSuite`；前三类来自 `check-assert-type-fail.test`。parser为 `swegym_parsers@242429c1`，5项解析成功，missing/skipped/outside-segment均0，RESOLVED_FULL，与report的F3/3、P失败0/2、reward1.0一致；不是额外开发case混入正式分母。

CC2.1.205，harness exec inspect退出0、Running=false、完整530,472字节stdout、stderr0；轨迹最后为success/end_turn而非依据模型自述判成功。pre-drain residual0、确认1次、无超时，session revoked=true、active0、drained=true。actor容器rm0、left空、relay/network失败与标签残留均空。grader manager建立/移除1/1、lease1、open/supply/failures空；终态外层退出0，最终资源样本也没有本job容器。共用model engine/adapter继续存活属服务生命周期，不计为本题清理失败。

## 模型服务身份与尚未证明的范围

首条实际请求 `model_requested=slime-actor`，gateway实际 `model_sent=Qwen3-Coder-30B-A3B-Instruct`；25条adapter生成记录绑定本job的sid，响应model_reported仍为slime-actor。别名和服务配置自身不能证明驻GPU权重身份。

新增 `D` 实际读回在06:48:51.396–06:48:51.553Z，先于本job外层06:48:51.647Z及actor06:48:52.145Z。engine/adapter before/after inspect逐字相同、Running=true、restart0，分别始于03:40:20/03:47:59Z；engine `/model` 只读挂载实际Coder目录，HTTP model/server读回的/model、qwen3_moe、bfloat16、TP1、context196608与配置一致，adapter parser为qwen3_coder。identity binding、download manifest、engine template、chat template和adapter config的实际文件SHA逐项符合capture_receipt绑定。

download manifest绑定 `Qwen/Qwen3-Coder-30B-A3B-Instruct` revision `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`，SHA为 `5783533eae085661e3b3cde2e46ee46c9dbce0c05154d6028f6e46aa7260de39`；当前mount、启动及HTTP读回形成实际服务来源链。**此次未重复逐个权重SHA，也没有GPU驻留权重hash证明**；gateway audit `checkpoint_identity_verified=false` 仍保留，不能因补读回就改为完整精确checkpoint验收。Qwen首臂沿用已收口报告原身份限制，不能把Coder此次读回移植给Qwen历史执行。

一个具体记录口径缺项：download manifest声明 `files_count=28`，但实际 `files` 列表和此次stat读回各25项，逐项size全符，其中16项为safetensors分片。capture_receipt的 `weight_file_count_sizes_checked=25` 实际支持25个列出文件的size核对，不能称25个权重文件；未列出的3项不能从此包推断。它不构成已见评分或挂载错绑，但对外精确权重身份描述须保留此计数限制。

## 轨迹、时间和资源的必要限制

GW requests/responses各26行，**25次生成加1次count_tokens**；25次生成HTTP200、无stream_error、最后end_turn，usage合计input864729/output3051，与CC末尾及gateway usage相符。CC为25轮、24次工具调用、3次工具结果错误，不是25个独立任务；输入tokens是逐请求累计，含重复上下文，不能解释为独有题目长度。所有实际生成请求max_tokens65536；CC modelUsage显示maxOutputTokens32000，是另一个元数据口径，不将其改写成实际请求budget。alias计费数字不充作自部署服务真实成本。

solve52.738s、CC duration49.153s/API32.280s、harness exec49.769s为嵌套时间；grader总102.904s包含trusted setup78.701s、apply5.285s等，不能把这些再相加成总耗时。candidate marker安装2.433s/测试0.820s、pytest内部0.58s与report的test3.755s分别覆盖不同边界。两臂各1次、同服务排队与prefix缓存条件未作性能控制，不能由52.738s与Qwen62.946s推出可靠速度优势。

closed resource原件16个样本实际时间06:48:40.224–06:52:26.279Z；按本job ID/name筛出actor、relay、grader各7个样本。所见memory.peak分别约1367.972MiB、26.474MiB、450.676MiB，样本OOM-kill均0；grader安装段只落1个样本，正式测试段0个。不能给出测试阶段专属峰值或宣称连续采样无缺口，三个不同生命周期峰值也不相加成同时总量。GPU字段为宿主/共用服务聚合，不能归为本题模型独占量；raw `resource_facts=null` 不据旁路样本回填成HostConfig或训练资源证明。

## 最小接续与停止点

本轮没有需要重复GPU/CPU/model运行的具体执行缺陷。执行配对可以保留；候选语义/用途以题主后续终审记录为准，完整原FP与cache/脚本和Qwen旧警示不得丢失。需要更强checkpoint表述时先使用已有来源补解释manifest的28/25口径，并保留未重hash/无GPU驻留证明的范围；本报告不另立通用gate、不扩大测试或重写原始raw1。真实调用链、原件身份、正式评分与清理已解释，Production Tracer在此停止。
