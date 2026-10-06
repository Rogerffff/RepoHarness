# Pydantic 8567：旧两行与补验七行的非作者 CPU 合并核查

2026-10-03。**组合九行 CPU 核查通过，实际分数为 0/0/1/0/1/0/0/0/0；实际公开 actor 诊断通过。当前 R14、材料、固定安装和精确派生镜像范围内，足以继续普通 GPU 探针；未授予训练资格。** 旧失败轮只复用 noop/gold，原 c3_reorder 的 300 秒 infra 超时和 `reward=null` 单独保留，不改成模型 0 分或新作业结果。

## 范围、方法与作业归属

审查者不是材料、runner 或本轮结果作者，但已接触私有测试、候选、参考和正式日志，不是 fresh 公开读者。复用[四题材料意见](non_author_remaining_material_review_20261003.md)、[R14 入口意见](non_author_remaining_runner_review_20261003.md)、[8567 正对照语义](non_author_8567_positive_semantics_20261003.md)、[旧失败轮核查](non_author_8567_partial_cpu_review_20261003.md)及[补验输入意见](non_author_8567_resume_input_review_20261003.md)。公开题面未变，不更换读者，不重做 release 全成员、材料或旧完整矩阵。

本轮只读本地原件，用标准库复算 SHA、tar、canonical identity、census、候选字节运输和逐节点日志；AST 提取冻结 parser 的纯文本解析函数后对拍 162 参考。未运行 SSH、Docker、模型、安装、项目 pytest 或作者检查／请求生成器。只写本报告和[同名 JSON](non_author_8567_combined_cpu_review_20261003.json)。作者 checks 和 wrapper passed 仅作对照。

| 作业与用途 | 固定输入与 namespace | 实际原件与结束 |
| --- | --- | --- |
| 旧 `pyd8567-formal-20261003001737-r14-b631d`，仅复用 noop/gold | `formal_v2`；输入 SHA `bea70edd55d2a316b5d92fde1a3a894e9c79363a168e2cd92c7de2d40b83ac1b` | slot 0，外层 rc1；375 件及 tar 的既有核查复用；旧 c3 infra/null 保留 |
| 新 `pyd8567-formal-20261003013213-r14s1-a8dbf`，仅补验七行 | `formal_8567_resume_v1`；输入 SHA `cce81e77a4122786ed78f8134d79fab11e7c46e4b851c80308c393076b3c3845` | slot1，01:32:16–02:00:39 UTC，rc0；928 件，本轮核每文件路径／大小／SHA及 tar payload |
| 实际 `pyd8567-actor-20261003020814-r14-e919a` | `diagnostics_v2`；输入 SHA `226ef4ab9be63c08f0ddfdd5755dc48353d87b3c24fbc3732745737cf36e3882` | slot1，02:08:17–02:09:18 UTC，rc0；32 件，本轮逐文件及 tar 核对 |

tar SHA：旧 `5f1fa451cbbb80f809bfcf92e9f581d9c9ca5915d5aa50151afa1f7ddb79e09c`；新 `dfea0f3ceccebe7031b2c49b1b68405ba8f9c395674a9d63489c08e5788bedb8`；actor `2ae9b6ff914abeaf7ec863ebf28baa4ac38b4006f0dfd5c2dc78b71e7c580e2a`。新两份 tar 精确含清单的 928／32 个普通文件，逐成员 payload SHA／大小相同，无缺项或多项。旧 375 件没有改写为新作业证据。

原件按 [remaining/results.json](../cpu_acceptance_20261003/remaining/results.json) 的 job 清单追溯，正式根为 `runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/<namespace>/outputs/<job>/`，slot 控制原件在同 remote_evidence 的 `jobs/swe_pydantic/<job>/`。旧新正式 spec **逐字段严格相同**；新固定输入只删除旧 noop/gold，仍使用 `formal_v2/materials`。新 namespace／唯一 job 未覆盖旧原件。

| 共用身份 | 实际绑定 |
| --- | --- |
| release／manifest | `cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1`／`51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8` |
| 正式／actor runner SHA | `b127f7309ffae3eae2bbe834c595f846104406e2f858b8073ff2182d0a2ce3c5`／`21caef4f953334a2b3759657ac3d5de00bd03373ffa8e40794674ddf5797f4f9` |
| revision | `pyd8567-order-old-behavior-v5`；revision.json SHA `22636f9481cc93a112a768043a21cc8d9d5ae8abaf6be1fffdc96a3aa870b81a` |
| materials／public bundle | `sha256:79fdb8c6fb5328a023a3f1b5ff2ade9e6fa405aec636d42755783bbb36546d0d`／`sha256:f01b3794148642ee4d987fdb2e57ec142f19080378c9ced0221290542149379f` |
| prepare 环境锚／HEAD | `sha256:8d64c28668f711aa8ab86fbe1bfe10ff3a24b4afc5c2a3001e8b43b8e3bcfb8d`／`8060fa1cff965850e5e08a67ca73d5272dcdcf9f` |
| 实际派生 image | `sha256:bc5d796fe30c9c0150a1c15c25347a98f0a1f25bf5f8d9cb098756b38b3c2b74` |
| 有效 test patch／file SHA | `a1ed762e8f64ddaa9654c2281e66e7be993de5b6b13a27ee04e8cf3387e5bfc6`／`dbe96a1fc7ce78c9fb1453e5eb2481f381d665f99042d282d1c525edf6ed6e0c` |
| 安装资产 SHA／core | `f013894eacd2b6a869f2c258212f51a298cf67632f9bfeab14793f581a449123`／`2.15.0` |

## 九行真实结果与普通失败

每行 **1 旧 F2P + 1 新 F2P + 158 旧 P2P + 2 新 P2P = 162**。逐参考的原始日志、冻结 parser、report 和四分区成功／失败集合相符，无参考缺失、跳过或未归账。实际各有 168 个节点，其余六个非参考都 PASS。JSON 保存每个 ID 的完整原状态、分区、log SHA、candidate／FrozenPatch 和原 job 归属。

| 固定顺序候选 | 来源 | reward | 旧 F2P | 新 F2P | 旧 P2P | 新 P2P | test rc |
| --- | --- | ---: | --- | --- | --- | --- | ---: |
| noop | 旧 | 0 | FAIL | FAIL | 158 PASS | 2 PASS | 1 |
| gold | 旧 | 0 | FAIL | FAIL | 158 PASS | 2 FAIL | 1 |
| c3_reorder | 新 | 1 | PASS | PASS | 158 PASS | 2 PASS | 0 |
| upstream261 | 新 | 0 | PASS | FAIL | 158 PASS | 2 FAIL | 1 |
| ok_post_attach | 新 | 1 | PASS | PASS | 158 PASS | 2 PASS | 0 |
| bad_nonvalidators_after_pv | 新 | 0 | FAIL | PASS | 158 PASS | 2 PASS | 1 |
| c3_serpass | 新 | 0 | FAIL | FAIL | 158 PASS | 2 FAIL | 1 |
| rv_ser_to_end | 新 | 0 | FAIL | PASS | 158 PASS | 2 PASS | 1 |
| n_python_only | 新 | 0 | FAIL | FAIL | 158 PASS | 2 FAIL | 1 |

旧 noop 丢失 PlainValidator 内侧的 serializer；gold 调用了本应被取代的 inner handler，触发未知类型 schema、未解析前向引用和 stdlib TypedDict 错误，细节复用旧报告。gold 的原 0 分保留，不称其正对照。新 c3／ok 正对照实际完整 162 参考全 PASS，意义限于已核旧 annotation 顺序／PlainValidator 取代 inner 行为及当前参考，不外推任意 WrapValidator、组合或版本。

新五个负对照均启动并完成正式测试，属于普通行为拒绝：

- **upstream261**：旧 F2P PASS，新增 F2P `test_validators.py:2908` dump 得到 Unsupported 实例，预期 `'custom!'` 失败；新增 P2P 在 `:2916` 为未解析 inner forward reference，在 `:2925` 为 Python<3.12 的 stdlib TypedDict inner schema 错误。
- **bad_nonvalidators_after_pv**：仅旧 F2P FAIL；`:2869` 的 Replaced 经 `_known_annotated_metadata.py:280` 抛出 `Unable to apply constraint strict to schema function-plain`。被取代的 strict 约束仍被应用；其它参考 PASS。
- **c3_serpass**：旧 F2P `:2884` 中间 AfterValidator 应得 70，实际 7；新增 F2P 仍得到 Unsupported，新增 P2P 两项 FAIL。`functional_validators.py:162` 的 `handler(source_type).get('serialization')` 构造了本应被取代的 inner schema。
- **rv_ser_to_end**：仅旧 F2P FAIL；`:2890` 应用外层 serializer 应为 `'outer'`，实际 `'inner'`，改变优先级。其它参考 PASS。
- **n_python_only**：旧 F2P `:2833` JSON bar 为 true，预期字符串 1；新增 F2P `:2900` 经 inner handler 触发 PydanticSchemaGenerationError，新增 P2P 两项 FAIL。仅 Python 路径没有恢复 JSON 语义。

新七行均有唯一完整真实测试段，大小／digest 与 ledger／report 相符；无 collection error、安装失败、半截 segment 或 infra detail。正对照为 resolved/1，其余 unresolved/tests_failed/0。pytest rc1 是行为失败，candidate exec rc0 不应误读为测试通过。

## 安装、源码与完整 baseline 运输

七行 prerequisite 实际 rc0，stdin SHA 同为 `69f723c29108c52e3cea16130b8957922b825a066c71e54f017841c164040eb4`，stdout 均 `RH2_PYD_FIXED_OFFLINE_PREREQUISITE_OK=1`。editable／测试依赖安装完成，install rc0、未跳过、失败命令列表空、candidate exec0、测试完整。七份保存脚本 SHA 与 spec 一致；七次 trusted setup／candidate test 实际 stdin 与保存字节相同，runner 前后摘要未变。

原 Docker 审计 stdout 与七份 supplemental observation 相等：实际 UID54322、Python3.8.19、`/opt/miniconda3/envs/testbed/bin/python`、Pydantic2.6.0a1／core2.15.0，三个源码模块从 `/testbed` 导入，SHA 与各候选运输后源码相同。有效测试 SHA 固定、root 所有且执行 UID 不可写；保护返回 `RH2_PROTECT_OK=1`，新 P2P 实际执行状态已核。

新七份 FULL baseline 各 **458 项政策内对象**，canonical digest 均 `sha256:eb494e7682db99522d57c38a96dc78b9469c0c6cbc36e33cdb811b1f25fc2d64`。逐一核 baseline／FrozenPatch／projection canonical 摘要、task/public/image/HEAD/physical attempt/rollout execution；候选初态、应用后、fresh grader 应用 delta 前共 **21 份完整 census**，逐路径／类型／模式／内容 SHA 相同，25 项政策排除对象摘要也相符。加旧有效两行六份，共27份属于组合九行；旧失败 c3 三份 census 留在旧失败工件。

新候选均只改一份源码：c3／ok／bad／rv 改 `_internal/_generate_schema.py`，upstream／c3_serpass／n_python_only 改 `functional_validators.py`，其它457项不变。实际 patch stdin、原候选 base64 导出 bytes、FrozenPatch content digest、fresh grader 注入 stdin 相同，import 探针再次核实际字节。新旧 c3 patch SHA 同为 `221bbe05b331ff83740ba64eff3a91666c5eb0b2062e80b1fa3c4e75721f86a1`，但 physical attempt／FrozenPatch 归属分开。

baseline `environment_package_digest` 仍为 **null**。证明范围是逐对象 census／摘要、实际 image／安装和运输；未声称额外全 baseline payload tar、测试后全 census 或正式训练 typed baseline／环境租约。prepare 的非空环境锚不填补该 null。

## 预算、清理及旧 infra 保留

新264次 Docker 调用均实际退出0。14个 run 绑定精确 image、network none、2CPU／4GiB／512pids，实际 cgroup `200000 100000/4294967296/512`。固定 reset/apply/test 为300/120/1800秒，replay候选／评分／清理／镜像为900/3600/120/1800秒，manager close及保护均300秒，没有放宽。

七次保护在155.055、193.472、167.152、161.770、200.164、164.225、**282.782秒**成功，小于300秒。末次接近上限，不能宣称共享资源问题永久解决。维护方保护-only恢复／ack按专用root/base/禁hooks、省略activation/display原范围复用，不扩作本题正式安装／模型证据。

14次实际删除 rc0／stderr空，对应七候选与七grader；manager7create/7delete，无open/supply/cleanup failure；0263/0264按本run标签查询容器／网络，rc0、stdout/stderr空，final ok/0。actor容器／网络／relay／stub收尾成功，residual列表空。

旧 c3 原 `failed_to_grade/infra_failure/reward=null` 与0099保留：trusted setup后、安装／测试前 protect **300.071秒**超时，只有call.json，无退出码或streams，不定位内部具体卡点。已记录OOM/pids事件0，三候选／三grader已删除，0104/0105空。首wrapper异常为“真实测试标记缺失”，finally 的 aborted/4触发“收尾异常或存在本run残留”；该措辞不能推翻零残留。新c3的1分属于新job，不替换旧null。JSON保留旧returncode/error/cleanup及完整失败行，`old_c3_infra_null_preserved=true`。

首派actor `pyd8567-actor-20261003020327-r14-f200e` journal为deferred/rc75，dispatch只有 `All CPU slots busy; retry later`。未入槽或执行题目，不记actor结果／0分，未用作实际actor_job。

## 实际公开 actor

实际完成actor为 **pyd8567-actor-20261003020814-r14-e919a**。原命令、stub script、实际三次Bash input、后续request的tool result和完整capture逐项一致；timeout90/90/180秒，rc **0/1/0**，均未达200000字节截尾上限。完整trajectory22658字节，四request、三Bash、result success；harness0／stderr0字节／CC2.1.205，wall1800／outer2400秒。

1. **identity rc0**：实际UID54321、Python3.8.19／core2.15.0、解释器和 `/testbed/pydantic/__init__.py` 相符。三baseline源码SHA、三模块import路径和 `os.access(..., W_OK)` 断言实际执行通过；未实际编辑源码。
2. **public_goal rc1**：原示例实际 `{'x': '0', 'y': True}`，`TARGET_EQUALS False`，复现已知基线问题，符合nonzero预期，不是actor新失败或评分0。
3. **public_existing rc0**：原已存 `test_use_bare_field_validator` 实际 **1 passed**。这是小范围开发路径；作者summary的pytest字段仍null，结论来自原capture。

首request SHA `ddeab9bfba2be2537eae15e77231cf87562905a58fb4c5aac7c87c1f7f42b9de`，prompt SHA `59a04f7f19d50b3d162a4b1df9bac45e6b2d820cefd8ae1cdb93689efb5e600d`。bytes decode保留CRLF核首user与公开prompt精确相等，包含原题面+hints；actual prepared public与已核R14 local prepare逐字段及canonical digest相同。

私有隔离核了数据流及实际请求：冻结源码host load_context可读private grading，但Runner只将 `ctx.rollout_views` public送入 `rollout_spec_from_view`，`grading_spec=None`；devcheck只替换image，driver接受公开prompt，actor路径不apply private test patch。prelaunch实际mounts/binds空。四真实JSON request的420个解码字符串检查，两份完整私有test patch blob、新增私有节点、revision/control/host-evidence标识均未出现；后续内容是公开命令及真实回显。host注册／校验私有材料不等于solver交付，不只凭函数名缺席判断隔离。

prelaunch实际UID54321、effective/permitted capabilities零、NNP1、精确image及2CPU／4GiB／512pids，direct upstream／外DNS禁止、relay可达、workdir可写。初态HEAD正确，pdm.lock／pyproject.toml两修改为派生安装初态，未称clean worktree。启动activation写探针DENIED；专门agent BASH_ENV写拒绝命令未测，作者 `bashenv_denied_for_agent=false` 保留，不由启动探针替换。

## 通过范围和限制

`cpu_review_passed=true` 与 `ordinary_gpu_probe_ready_within_review_scope=true` 只适用**旧两行+新七行组合**、实际公开控制桩、R14/revision/固定安装/精确image。新job范围仍为 **new seven rows only**。各输入、清理、旧rc1/error与新rc0分别保存；后续合并请求须绑定两个formal job、实际actor、九行顺序及旧c3 null，不能把旧失败轮伪称完整通过。

共享parser限制保留：**168个parser键不等于168个合法完整states**。162参考准确；六个带空格非参考PASS参数ID被截断，值为 `input_value='123',`。本轮另从raw full IDs核六PASS，不扩大为全pool阻断；这些ID成为参考或声明全节点完整states之前须共享parser修复另验。

当前无本窄核阻断。未验证真实模型推理／修复、实际源码编辑、全公开suite、专门BASH_ENV写拒绝、typed正式训练actor／租约、baseline envnull对应训练契约。公开actor是固定控制桩和诊断精确image override。普通GPU探针仍需实际模型服务、checkpoint／任务请求绑定、现场image／资源及实测；wheel可读层回执不代替本题GPU镜像安装验收。未改reward、历史工件或训练资格。
