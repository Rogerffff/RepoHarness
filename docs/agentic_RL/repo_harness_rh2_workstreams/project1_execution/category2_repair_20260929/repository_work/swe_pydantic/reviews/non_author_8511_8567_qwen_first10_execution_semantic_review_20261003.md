# Pydantic 8511／8567：Qwen 首臂与 Coder 配对的非作者执行、语义窄核

2026-10-03。**两份 Qwen 首臂的执行与配对绑定通过；候选语义均不能验收。** 8511 原始 reward **1**、安装／测试退出 **0／0**，全部173正式参考通过，但最终补丁静态可见丢弃 `FieldInfo` 的工厂、约束和别名，构成当前参考集的具体覆盖缺口。最小运行对照尚未执行，不能把该原分解释为完整正确。8567 原始 reward **0**、安装／测试退出 **0／1**，四项失败由候选无条件生成内层 schema 引起，是普通行为回归。原分、原 FP 和历史证据全部保留。本报告不改评分、不授训练资格、不核销行政 pair 状态。

审查者不是本轮材料、runner 或回执作者；此前已读私有新增测试、CPU对照、Coder轨迹和题主分析，不是 fresh 公开读者。复用[已验 Coder 执行审查](non_author_8511_8567_coder_q24_execution_review_20261003.md)及既有 R14材料／CPU审查，仅核本轮两个 Qwen 原件和同题配对。使用本地标准库读取、哈希、tar和文本复算；没有 SSH、Docker、安装、项目测试、模型调用、执行题主 helper、修改board或跨线程发信。只写本文及[同名JSON](non_author_8511_8567_qwen_first10_execution_semantic_review_20261003.json)。

## 执行权威与固定输入

权威根仅为 [gpu1003-pyd8511-qwen36-a1](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pyd8511-qwen36-a1) 与 [gpu1003-pyd8567-qwen36-a1](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pyd8567-qwen36-a1)；没有以旧 remote 差异或导航摘要覆盖当前原件。独立复算全部209／204成员，分别24,921,954／21,130,321字节，路径、大小和SHA均相符。目录各另有未计入这批成员的 `closed_manifest.json` 自身和 `sync_receipt_v4.json`，已另核其SHA，不误计作缺失或额外执行。两执行回执及两pair回执的原SHA也独立一致：

| 绑定 | 8511 | 8567 |
| --- | --- | --- |
| closed manifest | `159a973edd655ed465c8135bf71332d9ccdcfe8b031d205fd9b2dc1c58d7cd8b` | `e7350ec766b224ed081934d73e7177e9853d20c29730a3a128cdcb1f43abe6b2` |
| [execution receipt 8511](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-pyd8511-qwen36-a1_execution_receipt_v4/execution_receipt.json)／[8567](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-pyd8567-qwen36-a1_execution_receipt_v4/execution_receipt.json) | `c9ea2620dd7f5687b6714acda8ccd9aafa9bd1a106bcefc68174a6bc51632984` | `402934dcbb016bbe095daa3d855c52bb3f07a4c918f705689d65de36a7e153ae` |
| [pair receipt 8511](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/swe-pydantic8511-behavior-v1-20261003_pair_execution_receipt_v1.json)／[8567](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/swe-pydantic8567-behavior-v1-20261003_pair_execution_receipt_v1.json) | `1f656c12f840c631f0b9faf0479f9abdba751a9e152fc27fa443fe13d3ecfe41` | `b49ff19170e62a276880c8eb180950d1a3547420209167eebd27a16438a58dea` |
| 实际题级request | `3b775ef774a730a29af5fd0bc3e1ea3c0f5828e4303de6625f3019dd42391467` | `3afb34c2e5f0a71c7531c642932e39b3dbb171b0cee0d803c6f739dff165d318` |

两个 request 各60份固定输入逐文件复算，无缺失或不匹配。输入manifest SHA为 `97bd3ed8b8b8943c1a2272a9cb5b965df2d8fa2b7812a0c28f795fa4e842ee3f`；当前题级运行是 `queue_qwen_first10_v1/code_v8`，entry SHA `bdf806bf8da1d5ebb4970887bfc3c7738eb3e57a75e1d07215d6d68b17e574c4`，source manifest SHA `09ddb8bfdeecd3ffaa38c1048a574161ef6fa6053b2855da50166e8e8677899d`，共用 solve入口锚 `00ca849909150de02769f297374a9bbfacf2746347c425474775d9c3e22a04f9`。R14 release为 `cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1`，manifest `51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8`；没有重审整个release。

同题 Qwen／Coder 的 owner request、prepared manifest、公开prompt／rollout view、私有host artifact、entry／source manifest逐字相同。分别实际使用同一base和actor／grader镜像：

| 题 | base commit | actual image ID | Python／core |
| --- | --- | --- | --- |
| 8511 | `e4fa099d5adde70acc80238ff810c87a5cec7ebf` | `df6c3affb7ea6fd826f44863ec92926f7b52558dd0f1b42e05f97aec9fe8ca68` | 3.8.19／2.14.5 |
| 8567 | `8060fa1cff965850e5e08a67ca73d5272dcdcf9f` | `bc5d796fe30c9c0150a1c15c25347a98f0a1f25bf5f8d9cb098756b38b3c2b74` | 3.8.19／2.15.0 |

实际prelaunch inspect和cgroup probe为2CPU、4GiB、PID512、swap0；solver UID54321，正式prerequisite UID54322；从 `/testbed` editable源码导入。两次真实安装输出固定core已满足、editable安装完成，安装RC0、失败命令为空；前后pip freeze相同。trusted setup恢复并应用1份有效测试文件，apply0、缺失／irregular0，control protection通过，runner前后digest相同。题级环境资格仍 `absent`，baseline环境digest仍null；assignment环境digest非空，不补填typed资格。

两臂预算同 `probe-wide-v1`：求解10800秒、CC240回合、上下文196608、输出65536、session1024请求、首字节1800秒、adapter idle14400秒；正式whole／setup／apply／test为3600／300／120／1800秒。实际所有生成HTTP都传 `max_tokens=65536`，没有以CC结果里缓存的 `modelUsage.maxOutputTokens=32000` 替代真实请求。sandbox profile唯一差别为模型网关端口：Coder18081、Qwen18082；模型本身及规定采样不同，不能称同一model adapter或同采样实验。

## 真实模型、公开交付与终态

实际Qwen是 `Qwen/Qwen3.6-35B-A3B`，下载revision `995ad96eacd98c81ed38be0c5b274b04031597b0`；engine CID `5a023c27c62bb2f37cf060429a59f96b726d1b404cf756bc8052564037bf3349`，adapter CID `aff52a71c621b2520b42350259a2992a18c0ed40ea209906357d3c2a552fc36d`。[8511当前capture](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pyd8511-qwen36-a1/diagnostics/QUEUE_QWEN_FIRST10_V1_gpu1003-pyd8511-qwen36-a1_before/capture_receipt.json)在14:08:16.394028–.545044 UTC，[8567当前capture](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pyd8567-qwen36-a1/diagnostics/QUEUE_QWEN_FIRST10_V1_gpu1003-pyd8567-qwen36-a1_before/capture_receipt.json)在14:14:02.597103–.784016 UTC，各在派发前完成真实inspect和server／model HTTP读回。实际engine PID999327、adapter PID1000924，启动分别13:24:03和13:26:58，capture时running／restart0；两次capture前后inspect一致。实际 `/model` 为同下载目录的只读mount，adapter Cmd与其只读代码mount指向code_v8。Qwen的 `identity_binding_actual.source_code=code_v8` 与实际一致；Coder审查中历史code_v4服务元数据及其实际adapter与当前queue_v24/code_v8题级consumer的区别仍保留。

model/server指向 `/model`、context196608；真实adapter默认temperature1.0／top_p0.95／top_k20／max_new_tokens65536。下载清单SHA `32bd30f61860366b3783eabc9d75bee0cd28c474d9c07de8be8d9ae60a4552ab`，template／chat template／adapter config SHA与capture逐字绑定。清单头 `files_count=40`，实际 `files` 列37项；当前37项大小均匹配，含26份safetensors。这个计数差异是非阻断元数据缺口，不称40文件全核；没有重算全部权重SHA或证明GPU内存权重hash。

[8511首HTTP及完整请求](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pyd8511-qwen36-a1/services_qwen_code8_v1/qwen36/gateway/first10-v1/gpu1003-pyd8511-qwen36-a1/requests.jsonl)／[8567](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pyd8567-qwen36-a1/services_qwen_code8_v1/qwen36/gateway/first10-v1/gpu1003-pyd8567-qwen36-a1/requests.jsonl)的首题面与实际prompt原始字节完全一致，包括原CRLF、公开示例和已有公开提示；`slime-actor`别名实际发送为 `Qwen3.6-35B-A3B`。分别44／34次生成请求，全HTTP200，每份SSE有完整message_start／message_stop、无error；43／33次tool_use后各1次end_turn。8511另外1次count_tokens单独记账。逐条adapter sid和原CC结果对应，实际最大prompt60480／41980 tokens，最大单次输出1176／3228；aggregate input／output分别1847294／14972和897628／10466，与gateway和CC相同。

私有隔离依据包括实际actor无bind／mount、UID和hidden-root不可读probe、当前entry的rollout／grading数据流及完整HTTP正文。entry仅把rollout spec与公开prompt交给solver，私有host grading view用于独立grader，并在actor清理后调用；有效test patch及新增私有节点未出现在所有模型请求中，baseline公开测试也不含新增节点。不能只凭私有函数名未出现作隔离证明，也不外推为全机任意通道审计。

完整原CC轨迹分别727／551事件，45／33工具调用且全部有对应返回；8511为31Bash／10Read／4Edit，8567为26Bash／6Read／1Edit，没有Write。按assistant message.id合并，8511有两组各2工具调用，其余41组各1；8567的33组均各1。不能按JSONL单行认定8511全串行，也不能将44生成请求、45工具和46CC回合混为同一分母。正常CC结果为46／34回合、end_turn、is_error=false。8511六条tool_result error包括误把dataclasses当目录，以及五次字段顺序TypeError；后者有真实git stash／checkout基线对照，不能算成最终候选的新回归。中途公开pytest的“无annotations”AttributeError通过最后一次Edit改为getattr处理，最终公开dataclasses166 passed／11 skipped，dataclasses+fields172 passed／11 skipped。这些head／tail管道和工具exit0不能替代正式矩阵。8567唯一tool error是Python3.8无法从typing导入Annotated，随后改用typing_extensions；后续公开bool序列化示例和多组旧公开测试通过，未在求解时测试Unsupported／未知forward／stdlib TypedDict的plain绕过路径。两份最终FP都仅一个生产文件，原临时验证均为inline命令，没有临时验证文件留在FP。

真实题级终态分别14:08:16.650321–14:13:48.408744和14:14:02.902461–14:19:11.046989 UTC，exit0，执行含 `--execute`。精确本unit的[8511原PID1 journal](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pyd8511-qwen36-a1/diagnostics/QUEUE_QWEN_FIRST10_V1_gpu1003-pyd8511-qwen36-a1_before/current_terminal_evidence_v3/journal.jsonl)／[8567](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pyd8567-qwen36-a1/diagnostics/QUEUE_QWEN_FIRST10_V1_gpu1003-pyd8567-qwen36-a1_before/current_terminal_evidence_v3/journal.jsonl)各有 `_PID=1` 的 `Deactivated successfully.`，时间分别14:13:48.437364／14:19:11.095131；回链request／attempt／result SHA相符。退出后临时unit的not-found／inactive／默认ExecMainStatus0不作为独立退出证据，归档的其他job journal也不拿来补本job终态。派发前backend日志不覆盖本job完整服务生命周期；当前capture加真实HTTP／turn数据证明本轮绑定，不称全程持续inspect。

## 完整baseline、原FP与正式逐参考

两份baseline全部452／458 tar成员的相对path、类型、执行位和内容SHA逐项重算；无绝对路径、父级逃逸、重复或未知成员。完整census与manifest逐条相同，fresh grader重建census逐字相同，canonical baseline、policy和excluded census摘要相符。与同题Coder基线内容及mode相同，canonical digest相同；原tar字节不同仅为每项PAX atime／ctime，不能称tar SHA相同。

| 实际Qwen绑定 | 8511 | 8567 |
| --- | --- | --- |
| baseline canonical | `40135f281c216e76a04de6772eaaadcdfd0b46d949e98c5164f29cba2f454e45` | `eb494e7682db99522d57c38a96dc78b9469c0c6cbc36e33cdb811b1f25fc2d64` |
| baseline.tar SHA／bytes | `6207027aa65a3caad3ce78cbb4d08081b2f74a56432bbd6b25e91a1062c472d2`／7,075,840 | `d1f5dda5d7536e7e51a3c4511bf9e12d0d65fc86c25546a8b067e8f28830884b`／7,096,320 |
| 原FP canonical | `4c305765cca042e14a8b79ebafa304394739f982b0eb68a471a47efbf92b3da1` | `0f494797f772de09c0c9a40cc332b808e5587d2e319163e48eead6611ab7af4f` |
| 唯一生产内容SHA | `161678b86e6cdde428771594d2c5e2d4f1016108a2c9fa9b7d900bc0fb28401d` | `cf4e454eb6828c3bf2c9dde1400ff74b0e89233e4d34cbb93460cba75cd4f33c` |

canonical mode的100755／100644是执行位规范；tar的 `build-docs.sh`、`tests/test_pydantic_settings.sh`、`tests/test_validators_dataclass.py`实际0777，执行位相符，不声称所有POSIX权限位相同。baseline已含镜像准备造成的pdm.lock／pyproject差异，捕获早于solver，不当作模型delta。null environment digest保留，不能把同源运输通过写成typed lineage通过。

原FP每项base64、内容digest、task／attempt／physical_attempt／public／image／base身份相符；所有diff条目从该次actual baseline严格纯文本重放后与FP字节相同。正式projection、status、report回链同一原FP，仅纳入该生产路径，不从宿主review diff替换候选。8511的 `excluded_pathset_changed=true` 与原轨迹git stash／pop一致，classification仍projectable；FP不含.git／.harness。未归档post排除区全文census，不能宣称排除区逐内容已审；这不影响当前scoreable条目验证。8567该flag为false。

我读取两份完整原日志唯一测试区段，保留完整参数ID独立逐键核173／162正式参考，并按SHA匹配的冻结parser算法独立复算。原report、partition success／failure及原日志全部一致，参考missing／skipped／unaccounted为空：

| 实际臂 | raw | 原F2P | 新F2P | 原P2P | 新P2P | install／test |
| --- | --- | --- | --- | --- | --- | --- |
| 8511 Qwen | 1 | 1／1 | 无 | 168／168 | 4／4通过 | 0／0 |
| 8511 Coder（已验） | 0 | 1／1 | 无 | 168／168 | 3／4通过 | 0／1 |
| 8567 Qwen | 0 | 0／1 | 0／1 | 158／158 | 0／2通过 | 0／1 |
| 8567 Coder（已验） | 0 | 0／1 | 0／1 | 158／158 | 0／2通过 | 0／1 |

[8511原log](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pyd8511-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-pyd8511-qwen36-a1/grading/eval_logs/evallog_gpu1003-pyd8511-qwen36-a_f1759736.eval.log) SHA `3db69481c3121088d640f821dde0d65ad0964f7b2652e20a5a1e8e056ed2f527`，51,336B，真实184节点＝173P＋11SKIP。[8567原log](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pyd8567-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-pyd8567-qwen36-a1/grading/eval_logs/evallog_gpu1003-pyd8567-qwen36-a_42ab78a7.eval.log) SHA `fa7da23d94be0be9064269f31972ab44e4b4fd7b160eb797face0fb461fdd65b`，91,561B，真实168节点＝164P＋4F。均安装完整、candidate shell exec0；不能把shell0或外层entry0称作test0。原report分别resolved／unresolved，infra detail和execution failure stage为空，无收集错误或未跑测试。

8511 parser180键只含7个非参考SKIP，未含另外4个带reason的非参考SKIP；8567 parser168键中六个含空格参数ID被截断，其状态误成 `input_value='123',`，原完整六项实际PASSED。全部正式参考合法且完整，但两个reported键数均不是完整states证明；保留此非参考缺口，不扩为全pool阻断。8567根summary误写reward1不被采用，正式report／status／日志实际仍0。

## 候选语义与8511材料缺口

**8511需要阻断“原分1即语义正确”的验收。** 原FP `pydantic/dataclasses.py:179–180` 将 `FieldInfo.default` 或 `dataclasses.MISSING`传给stdlib `dataclasses.field`，仅传repr／kw_only，不保留原FieldInfo对象、default_factory或metadata。actual baseline的 `_internal/_fields.py:281–288`只有在stdlib field.default仍为FieldInfo时，才走保留原对象的分支；现在走 `FieldInfo.from_annotated_attribute(annotation, dataclass_field)`。随后 `fields.py:338–357,421–432`只从真正stdlib field的default_factory／metadata复制属性，这两项已空，因此原工厂、gt等约束和alias不能恢复。相关actual baseline文件SHA及行号见JSON。

这是本题应保留的既有语义：baseline `docs/concepts/dataclasses.md:47`明确Field与stdlib field均可指定工厂，示例已有Field的ge／le元数据；`tests/test_dataclasses.py`现有schema、alias、signature测试以及本轮有效patch的Field工厂节点也承认这些行为。题卡要求修复赋值式Field(repr=False)，不授权为隐藏repr丢弃字段的验证／默认行为。无需改变公开题面来说明这个保留要求。

现有173参考漏掉的是**repr=False与这些已有属性的组合**：新增hidden继承节点仅Field(repr=False)必填构造；新增factory继承节点的repr保持True；默认repr节点只要求可见。因此Qwen恰好绕过三类继承TypeError而全部通过，但不能证明字段信息完整。Qwen依然用继承getattr读取annotations；Parent的required／hidden字段经MISSING包装后类属性被stdlib移除，Child读取不到对应FieldInfo而不再setattr，故本轮hidden／required继承通过。factory继承节点不触发repr转换，也通过。这与Coder直接把继承FieldInfo包到无本地注解Child而抛TypeError的失败机制不同。

本轮静态推导的最小保留行为对照如下，**尚未执行**；应先在原base、已验narrow和原Qwen FP分别核对，不能给它们虚构新分或覆盖原raw1：

```python
from typing import List
from pydantic import Field, ValidationError
from pydantic.dataclasses import dataclass

@dataclass
class HiddenFactory:
    x: List[int] = Field(default_factory=list, repr=False)

assert HiddenFactory().x == []  # 仅核工厂保留，不要求base修好repr

@dataclass
class Child(HiddenFactory):
    pass

assert Child().x == []

@dataclass
class Positive:
    x: int = Field(default=1, gt=0, repr=False)

try:
    Positive(x=0)  # 显式输入，避免混淆validate_default
except ValidationError:
    pass
else:
    raise AssertionError("gt约束必须保留")

@dataclass
class Aliased:
    x: int = Field(default=1, alias='y', repr=False)

assert Aliased(y='2').x == 2
```

源码流预测Qwen工厂字段变必填、显式0不再受gt限制、别名输入不再写入x；未在本轮观察这些具体运行结果。既有[narrow工件](../tasks/pydantic__pydantic-8511/controls/narrow.patch)保留FieldInfo并只遍历本地annotations，提供最小正对照方向，但它在上述新增组合中的实际结果同样未验证。应在后续单独任务文件化／执行最小对照，再决定私有P2P补充；不需要重跑全部材料或将old奖改写。这里是具体公开保留语义及评分覆盖缺口，不是模型轨迹已复现的旧字段顺序TypeError。

**8567当前失败可直接判为候选语义回归。** 原FP `functional_validators.py:157`无条件执行 `handler(source_type)`。原F `test_plain_validator_plain_serializer`虽先改善公开bool示例，随后在其Unsupported部分抛 `PydanticSchemaGenerationError`；新增Unsupported两顺序F同样失败；新增未知forward P使Model保持未定义，`PydanticUserError`；新增stdlib `typing.TypedDict` P在Python3.8被强制走内层schema，触发要求typing_extensions的错误。原公开PlainValidator doc明示“替代内层验证”，plain分支无需生成这些内层schema，不能用支持typing_extensions.TypedDict证明stdlib绕过仍可用。

原F以及三个新增节点的栈、错误和生产行一致；158旧P仍通过，安装、收集和服务没有对应失败。这与已验Coder的无条件handler机制相同，虽代码组织和原FP身份不同，不能混称补丁字节一致。没有看到要求8567材料或CPU改版的新证据；新增节点按原冻结范围有效拒绝候选。

## 资源、清理与通过边界

资源只按本job实际CID、run_id和任务时间窗口核。8511 actor／relay／grader分别9／9／13样本，CID前缀78859d0c／9bcad460／36311983；8567分别8／8／12样本，前缀7d7ec39c／b61f12ac／f2cdcb76；完整CID和时间在JSON。grader run_id严格是对应job加 `-grade`，镜像与该题actual ID一致。可观察样本均有事件数据，OOM／oom_kill／pids.max为0；actor观察memory.peak约920／908MB、pids.peak24，grader观察约680／645MB、pids.peak9。正式report峰值648.445／647.934MiB与采样窗口是不同统计，不强行等同。

两窗口23／22离散样本，`gaps_unknown=true`；短保护、安装和pytest段未保证逐段采到，不能据采样宣布所有时刻无OOM或预算绝对充足。实际solve114.923／99.884秒，正式grading186.226／177.341秒，test5.664／6.585秒，均在固定上限内；没有超时或OOM证据解释8567普通失败。

两job求解进程停止residual0，quiescence双读稳定；gateway session均revoked／drained、active_requests0。actual container_rm0、labeled容器和网络查询空、relay／network failures空；每份manager1建1删、open／supply／cleanup failures为空、regrade0。收尾证明本run自有资源清理，不宣称整个宿主机器无其他作业。

因此，这两题四个已交付first arms可作为**原始执行结果和同材料配对比较**留存。8511 Coder0／Qwen1的分差不能据此当作Qwen完整修复成功；8511候选语义与材料充分覆盖的肯定结论需先处理上述静态缺口。8567 Coder0／Qwen0均由候选真实回归支持。训练消费、typed actor／租约、材料改版和补充实验均不由本报告完成或授权。

