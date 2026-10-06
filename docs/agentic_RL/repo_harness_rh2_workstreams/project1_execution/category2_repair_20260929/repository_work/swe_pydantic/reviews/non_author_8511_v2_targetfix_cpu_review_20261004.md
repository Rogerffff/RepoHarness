# 8511 v2 R27 targetfix：非作者实际 CPU 窄验收

日期：2026-10-04（Asia/Singapore）。正式唯一作业：`pyd8511-formal-20261003175031-v27-dc821`。

**本次四行177参考正式 CPU 验收通过，实际奖励 noop/gold/narrow/qwen_original 为0/0/1/0。** narrow全177参考通过；原Qwen生产源码对照的原173参考全过，新增四项全失败，真实失败与此前直接v3诊断相同。本次核到安装、完整参考终态、源码运输、保护和本run清理，未发现CPU范围阻断。可接续既有授权的原FP-only新版本请求草稿与精确输入join；原GPU完整FP的新版本评分仍未执行，新模型采样仍为0。

同名 [JSON](../../../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_pydantic/reviews/non_author_8511_v2_targetfix_cpu_review_20261004.json)明确 `actual177CPU_executed=true`、`cpu_review_passed=true`、`actual_GPU_FP_v2_regrade=false`，并保存526件实际原件逐文件path/SHA/大小、四行177逐参考状态、分区、精确CID和formal_status绑定。原173/raw1/FP、R26 false报告及旧失败原件不回写；不宣称fresh actor或typed训练资格。

## 1. 审查范围与固定版本

审查者不是本轮材料、runner或候选作者，已接触私有测试、直接诊断、旧CPU/actor和模型候选，**不是fresh公开读者**。复用已核[直接v3实际诊断](../../../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_pydantic/reviews/non_author_8511_fieldinfo_retention_v3_cpu_review_20261003.md)、[材料静态窄核](../../../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_pydantic/reviews/non_author_8511_fieldinfo_v2_material_review_20261003.md)和[R27静态输入核查](../../../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_pydantic/reviews/non_author_8511_v2_targetfix_input_review_20261004.md)，未重新全量审题、release或旧矩阵。

仅本地标准库读/hash/tar/JSON、解析完整原日志和固定stdin，并把实际trusted-setup中的patch作为数据严格应用；没有helper执行、SSH、Docker、安装、pytest、模型或看板操作。只写本报告和同名JSON。题主readback用于导航，结论来自实际原件，不以作者checks的passed布尔值代替验收。

| 固定对象 | 绑定 |
| --- | --- |
| source release | `cat2-cpu-r2e094095-swe40-pyd8511-fieldinfo-v2-test-target-20261004-v1` |
| release manifest SHA | `897cac778bce053740d7ac6dce9b2e90ac96a553a119c0bbdfe7e62b298cfe0d`，1529成员 |
| [formal_inputs.json](../../../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_pydantic/cpu_acceptance_20261003/8511_fieldinfo_v2_targetfix/formal_inputs.json) | 75,422B，SHA `88939f7d852133b2b6130f8d2e2c5a3237e9c7bdd13ed994dfa25c6782f368cd` |
| [run_formal.py](../../../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_pydantic/cpu_acceptance_20261003/8511_fieldinfo_v2_targetfix/run_formal.py) | 22,791B，SHA `b127f7309ffae3eae2bbe834c595f846104406e2f858b8073ff2182d0a2ce3c5`，复用R14原字节 |
| [原归档](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/pyd8511-formal-20261003175031-v27-dc821.tar.gz) | 658,639B，SHA `5f7891378fcb969f4b406bac82365a38f23ed0c87e0bcadf38c3c4c9c8b5c1d0` |

独立重算索引526件大小/SHA，实际raw/slot目录精确文件集合相同；归档全部普通成员逐文件字节与本地相同，共2,567,861B。实际[formal status](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_8511_fieldinfo_v2_targetfix/outputs/pyd8511-formal-20261003175031-v27-dc821/status.json)与slot的job、task、execute、source/manifest/input/runner均一致。release全成员和部署delta复用既有独立静态审查，没有把status自报1529重新包装成这次全量发布核查。

## 2. 177逐参考终态与实际奖励

逐行从完整verbose原日志独立取得终态，再与report、冻结parser states和三个参考分区比对。每行恰177个正式参考，均为PASSED或FAILED；missing、skipped、unaccounted均空。参考为1F2P＋176P2P，其中原F1、原P168、既有新增P4、本轮新增P4；没有把新增保留行为改为F2P。

| CPU行 | reward | F2P通过 | P2P失败 | install/test RC | 正式参考结果 |
| --- | --- | --- | --- | --- | --- |
| noop | 0 | 0/1 | 0/176 | 0/1 | 仅原隐藏repr F失败，176P全过 |
| gold | 0 | 1/1 | 4/176 | 0/1 | 原168P全过；旧三类继承和新增继承factory失败 |
| narrow | 1 | 1/1 | 0/176 | 0/0 | 全177通过 |
| qwen_original | 0 | 1/1 | 4/176 | 0/1 | 原173全过；新增四项全失败 |

原件：[noop report](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_8511_fieldinfo_v2_targetfix/outputs/pyd8511-formal-20261003175031-v27-dc821/noop/report.json)、[gold report](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_8511_fieldinfo_v2_targetfix/outputs/pyd8511-formal-20261003175031-v27-dc821/gold/report.json)、[narrow report](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_8511_fieldinfo_v2_targetfix/outputs/pyd8511-formal-20261003175031-v27-dc821/narrow/report.json)、[Qwen生产源码对照 report](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_8511_fieldinfo_v2_targetfix/outputs/pyd8511-formal-20261003175031-v27-dc821/qwen_original/report.json)。report的log ref SHA/bytes与实际完整log、ledger路径/SHA逐项相符。JSON保存全部708个逐参考终态与各row分区SHA，未只核失败列表或汇总计数。

每行项目pytest实际输出188个nodeid：177正式参考＋11个非参考SKIPPED。冻结parser每行184个唯一键，其中7个非参考SKIPPED键；原始skip节点身份在parser中未完整保留。**184不是参考数，也不是完整188节点状态。** 独立原verbose逐行解析确认177正式参考均完整，这个已有非参考口径限制不阻断当前评分，不外推全pool parser完整性或整个项目全测试通过。

实际命令已精确恢复为：

```text
pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_dataclasses.py
```

不是R26错误目录目标。本次四行都是上述有效测试模块的真实执行，不是prepare、直接四行为脚本或维护检查。

## 3. 普通失败的具体机制

**noop：** `test_repr_false[Field]` 的repr仍包含hidden_field，原断言真实失败；176P全过，四个新增保留P2P也全过。不是安装或基础设施失败。

**gold：** 实际生产源码用 `getattr(cls, '__annotations__', [])`，会读到父类注解；随后对无本地注解的Child设置stdlib Field。stdlib dataclass转换因此报 `TypeError: 'x' is a field but has no type annotation`。失败节点为旧required/hidden/factory三类继承，加新 `test_inherited_repr_false_field_preserves_default_factory`；不能误写成直接索引缺注解导致KeyError，或把四个新增保留节点全称失败。

**原Qwen：** [完整原日志](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_8511_fieldinfo_v2_targetfix/outputs/pyd8511-formal-20261003175031-v27-dc821/eval_logs/evallog_replay-pyd8511-formal-20_d86704af.eval.log)恰有四个新增普通失败：

- `test_repr_false_field_preserves_default_factory`：HiddenFactory()报ValidationError，x变必填。
- `test_inherited_repr_false_field_preserves_default_factory`：Child()报ValidationError，x变必填。
- `test_repr_false_field_preserves_gt_constraint`：显式x=0未抛ValidationError，pytest报告DID NOT RAISE。
- `test_repr_false_field_preserves_alias`：Aliased(y='2').x仍为默认1，断言1==2失败。

其原173参考全部PASSED，新增四项失败正好重现已核直接v3行为：生产转换只取FieldInfo.default或MISSING，未保留default_factory、gt metadata、alias。narrow保留完整FieldInfo并限制本地注解，在当前177矩阵全过。report均没有execution_failure_stage、infra_failure_detail或失败证据，普通失败行category为tests_failed；narrow resolved/category null。

148个Docker外层调用均RC0，并不表示pytest全过；安装/测试真正退出分别由完整RH2 marker确定。负行test1是评分依据，不被外层exec0或作者wrapper passed抹掉，也不另记基础设施失败。

## 4. 实际安装、解释器、受保护私有测试

四行完整安装段均实际执行E10：先 `python -m pip install -e .`，再从pyproject testing/testing-extra生成要求文件并安装；install RC0，没有failed-command或partial marker。完整日志显示core2.14.5已满足、Pydantic2.6.0a1安装成功。未跳过安装、修改依赖、改预算或新增模型求解。

四次后置实际audit均为UID54322、Python3.8.19、core2.14.5；导入 `/testbed/pydantic/__init__.py`，模块 `/testbed/pydantic/dataclasses.py` 与对应候选源SHA相同。pytest/pluggy等runner的前后digest均 `cdcb38ab1e198b9cd561dd143e40400f292c84e3211d65ee5e13cc16744cea34`，runner_integrity_changed=false。

四次实际trusted-setup stdin逐字等于固定 [trusted_setup_script.sh](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_8511_fieldinfo_v2_targetfix/outputs/pyd8511-formal-20261003175031-v27-dc821/trusted_setup_script.sh)。脚本先按base恢复 `tests/test_dataclasses.py` 并核原SHA `ca0aeebd83f995c08159e247c6505d54eee75af00b94cb634d5a65b0c043e2a3`，再完整应用固定v2 patch。独立核heredoc是4,083B原patch加分隔换行，patch SHA `6f7360d58088c01d59ac51133758ee2404ad21725d859144a14c58765b670125`；严格数据应用结果75,547B/SHA：

`3caba437582031957a9a6c4df706e1532e137c0312816afa4563ef7fcdeb6647`

四次真实attest均APPLY_RC0、RESTORED1、EXPECTED1、ABSENT0、IRREGULAR空、SETUP_OK1；保护stdout均PROTECTED_FILES1、PROTECTED_DIRS2、MISSING0、PROTECT_OK1。每行测试后的audit确认该有效文件SHA准确、owner UID0、对54322不可写。实际eval stdin是固定candidate_test_script，trusted-setup和测试按原受信分离执行；不会因总eval_script包含setup而误判实际eval stdin与整段脚本不相等。

实际prepared prompts、rollout views与已核R27本地prepare逐字相同，private host artifact同样逐字相同；公开文件只携带原公开题面/hints，新增四项留在private effective patch/host grading。公开bundle摘要 `edc64cdddc65f7fe20b6d9f7fdfd3c8fcfb77dacbd6457010e1a8b06c9d46165` 不变。当前材料identity为 `42e41bce9e6da8f1434687d7fe2231db78c63efad7b1457abf5f26a708baf8b5`；grading/registry/parser分区实际绑定R27的pyd8511-behavior-v2。没有新增公开solver或模型调用，因此不把这些private文件存在与本次CPU评分说成新actor隔离实测。

## 5. FrozenPatch、完整baseline与源码等价范围

每行实际baseline manifest均452个政策成员，canonical digest为 `40135f281c216e76a04de6772eaaadcdfd0b46d949e98c5164f29cba2f454e45`。独立读取三次完整census：候选应用前、候选应用后、grader delta应用前。每份452成员的path/type/mode/content SHA与manifest完整比对；候选应用后仅预定dataclasses.py变化，grader原baseline与manifest逐项相同。

本run走**同镜像workspace baseline一致分支**，不是原GPU tar重建：在完整census相等后，运输FrozenPatch生产delta，随后受信setup替换私有测试。不能把baseline摘要核齐写成原GPU完整baseline tar已做v2补评分。排除.git/.harness和可再生cache仍按baseline_policy_v2处理，不外推全容器文件系统；baseline environment_package_digest仍null、env_qualification absent。

| CPU变体 | 实际生产源码SHA | 本run新FP canonical SHA |
| --- | --- | --- |
| noop | `3fd9cc00c536227d63b4232c60e67ce45521b1b7d8473cf7c8bd9866d9a1539f` | `12c14593d10f01a7131c99deee94bfc871458d58c71310cab8075bcde0ba6645` |
| gold | `3635a04fcb3b3b5a450216a71f3f1477f9e5855ec41e88a275894d4869bcdc6d` | `6ea33f64ef8a7980f8b940cdc7edb5cb1899a3b02cd22ecf2c22e543f5db1a35` |
| narrow | `337e4d552b22aef94960740b385c7ca93cd1b09619997e74e4e93da6427190df` | `44c320c3d0bf66387498e72a231d4e7ac47f37a150730409885fd624b17fc79b` |
| qwen_original | `161678b86e6cdde428771594d2c5e2d4f1016108a2c9fa9b7d900bc0fb28401d` | `538ca970f568d69b6c69e813a874aa2cf43bd4627b4403be6736f53a8a892a84` |

noop为空FP；其余各一条modify/regular/100644 dataclasses.py。逐条核patch输入stdin、实际git apply检查/应用、候选Base64输出、FP内容/digest、grader写入stdin及后置源码导入SHA，字节一致。所有delta只涉及生产文件，无test/conftest/fixture或forbidden路径变更，projection没有unsupported shape。

原Qwen CPU行是旧GPU FP唯一生产条目的**等字节源码对照**。本run重新构造CPU FP，执行id/metadata和canonical digest均不同；旧GPU `gpu1003-pyd8511-qwen36-a1` 的原完整FP digest仍 `4c305765cca042e14a8b79ebafa304394739f982b0eb68a471a47efbf92b3da1`。这项CPU结果足以确认新177评分拒绝该源码，却不能写成旧GPU完整FP已安装并获新分。后者须接续其原FP与原baseline的真实FP-only新版本作业，新模型采样无需增加。

## 6. 精确镜像、UID、资源、原预算

实际候选和grader均使用linux/amd64派生镜像：

`sha256:df6c3affb7ea6fd826f44863ec92926f7b52558dd0f1b42e05f97aec9fe8ca68`

base image `b331c8fa2b55168dbce5d57753265c02d9aa2a3525761d202f3802684681b9a0`，源码head `e4fa099d5adde70acc80238ff810c87a5cec7ebf`。候选git_apply为UID54321；正式install/test和audit为54322。grader prelaunch实际有效/许可cap均0、NoNewPrivs1、网络外连DENIED、可写home/tmp检查通过；root受信setup沿用原profile的CHOWN/DAC_OVERRIDE/DAC_READ_SEARCH/FOWNER/KILL，不套用直接retention诊断只有两cap的配置。

四个grader精确CID/PID为：

| 行 | grader CID | 宿主PID | 保护call / 实际秒 |
| --- | --- | --- | --- |
| noop | `603177aabef3e23b212fb159da5fe1fb352dfb348ede4a22f3bc661070046c7d` | 1178858 | 0025 / 137.095 |
| gold | `7e83edf94ac62f8248effd66ec7db9fd59608f5a14b5148114c9fee89bf75797` | 1181569 | 0062 / 129.301 |
| narrow | `beab060b99861acbcba8bedce5aef01e616d084f59042c53cbfcc00d697c690b` | 1184127 | 0099 / 133.811 |
| qwen_original | `8df6d4d761f93fbe71bc5990ce93053d607f3ee9080584183c7660381f060cc4` | 1186920 | 0136 / 135.449 |

实际run返回的CID、inspect CID、image、name、run_id标签和本row trajectory相互绑定；四个candidate容器也逐run返回CID与rm名字闭合。四次inspect确认2CPU、Memory=MemorySwap=4GiB、pids512、network none、无Mounts/Binds、非privileged；prelaunch的cgroup确认cpu.max=200000 100000、memory.max=4294967296、swap.max0、pids.max512。

保护四次均在**原reset/protect300秒**内完成，未升级900、未自动重试。apply120、test1800、candidate stage900、cleanup120、grading deadline3600和image-pull1800预算保持；runner字节与已核R14相同。整个四行作业内部耗时744.596秒，不使用retention诊断的600秒整作业上限。

资源证据限于实际prelaunch/inspect、后置audit和末尾cgroup memory.peak。峰值MB为677.418/663.980/664.125/664.605；其原字节值在JSON绑定。resource_facts=null，没有连续cgroup采样或最终memory.events/pids.events。初始inspect的OOMKilled=false、普通日志和正常退出不等于全过程零OOM/pids事件，本报告不作该外推；此缺口不改变实际普通测试失败归因。

## 7. 普通前台slot终态与本run清理

[实际slot status](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/jobs/swe_pydantic/pyd8511-formal-20261003175031-v27-dc821/status.json)为共享cpu_slot前台作业，slot0，supervisor PID1177875、child PID1177876；17:50:34至18:02:59 UTC，finished/RC0。[slot stdout](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/jobs/swe_pydantic/pyd8511-formal-20261003175031-v27-dc821/stdout.log)仅报告任务完成状态，stderr为空；formal status execute=true、run_id及task/source/input均匹配。**本job没有retention诊断的systemd unit，不虚构PID1 service事件。**

148条原始Docker调用的stdout/stderr/stdin均已读，148条RC0、全部stderr空、18份stdin完整。四candidate及四grader的实际rm均RC0/回显对应名字；manager close为grader4建4删、containers_open/supply_open/cleanup_failures为空、regrade_total0，final_status exit0且open为空。

最终 [0147容器label查询](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_8511_fieldinfo_v2_targetfix/outputs/pyd8511-formal-20261003175031-v27-dc821/docker_calls/0147/call.json)和[0148 network label查询](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_8511_fieldinfo_v2_targetfix/outputs/pyd8511-formal-20261003175031-v27-dc821/docker_calls/0148/call.json)均精确绑定本run_id，RC0、stdout/stderr空；没有本run残留。范围仅此作业，不能外推共享机其它容器或服务清理。

## 8. 通过范围与后续边界

当前R27真实修复目标下，四候选177参考的普通安装/评分运输与精确身份、完整正式参考、负对照机制和清理均核收。**CPU这一前置已完成，可以接续已授权FP-only请求；请求需精确join本job、formal input、source/manifest、formal status和原完整FP/baseline身份。** 本报告不称该GPU请求已创建、提交、执行或通过。

旧实际公开actor `pyd8511-actor-20261002234027-r14-3deca` 仅按未变公开材料、base、实际image/E10/core的既有source开发/交付控制桩证据有限复用。实际prepared公开/private字节仍与已核R27 prepare一致，未扩大到fresh公开读者、新模型能力、fullroles或typed训练actor。formal status中历史“四题actor仍待”模板文字不覆盖这项已核有限复用，也不能替代尚未发生的验收。

R26旧输入false、错误目标工件与hold历史保留；本次新R27 CPU通过不热改旧结论。原Qwen旧173/raw1/ACK和原FP保留，直接v3与本轮177各自范围清晰。完整GPU FP补评分、GPU运行身份/资源服务核收、typed训练资格仍无本报告实际证据；无需新增solve，亦未放宽私有材料或评分规则。
