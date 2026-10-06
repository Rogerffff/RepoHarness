# Q24 Pydantic 8511／8567 Coder 首臂非作者执行窄核

2026-10-03。本轮执行证据核查通过；两份原 reward 0 可以作为当前固定版本下的普通探针结果保留。8511 和 8567 的拒绝都与实际生产源码改动有直接关系，属于普通候选行为失败。未见安装、测试运输、预算超时或清理失败导致的误记 0；本报告不接受两份候选的完整语义，也不核销另一模型或训练资格。

核查者不是本轮候选、执行入口或材料作者，但已接触 R14 私有材料、CPU 对照、先前独立报告及题主本轮分析，不是 fresh 公开读者。本轮只读本地原件，使用标准库核 SHA、tar、canonical identity、逐键测试结果和文本差异；未运行 SSH、Docker、安装、项目测试、模型、作者检查器或 board，也未修改旧证据、评分或共享文件。

**权威与固定输入。** 执行权威仅为以下 closed snapshots。题主的 canonical transcript／production delta 用作导航，并另与这里的完整 JSONL、真实 baseline.tar 和 FrozenPatch 字节核对。未从旧 remote 差异取代当前候选。

| 项目 | 8511 | 8567 |
| --- | --- | --- |
| 实际 job | gpu1003-pyd8511-coder-a1 | gpu1003-pyd8567-coder-a1 |
| closed snapshot 清单成员 | 356／23,240,483 bytes | 377／25,272,259 bytes |
| authority 清单 SHA256 | 4069a5bacddea61b95c9e1b8b7c1bebdc50b3b9439f834994734b3b950b49c21 | c9399d48fe41d7b7591376b1358ffed198ba147c6e9960d29a64679dba038d8f |
| owner request SHA256 | 52dab640a4ab8a19a19cfa0449f4b92b3d52df82da844cc1f515432a0f6abb84 | 72fdd7614fbc09241eaa2d461241f4a7784ca0ad43bfae01a2c0608f4fb6e1e2 |
| 实际 actor／grader image ID | df6c3affb7ea6fd826f44863ec92926f7b52558dd0f1b42e05f97aec9fe8ca68 | bc5d796fe30c9c0150a1c15c25347a98f0a1f25bf5f8d9cb098756b38b3c2b74 |
| 基线 commit | e4fa099d5adde70acc80238ff810c87a5cec7ebf | 8060fa1cff965850e5e08a67ca73d5272dcdcf9f |
| 修订单／实际 core | pyd8511-behavior-v1／2.14.5 | pyd8567-order-old-behavior-v5／2.15.0 |

根目录分别为 runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pyd8511-coder-a1/、gpu1003-pyd8567-coder-a1/。清单中的每个成员大小和 SHA 独立复算全部相符；根目录额外的本 job authority manifest 与 sync_receipt 不混入成员分母。包中附带的其他历史作业只核运输哈希，未纳入本轮语义结论。

两题均绑定 R14 cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1，发布 manifest 51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8。当前题级入口为 queue_v24／code_v8，entry SHA bdf806bf8da1d5ebb4970887bfc3c7738eb3e57a75e1d07215d6d68b17e574c4；当前 source manifest SHA 09ddb8bfdeecd3ffaa38c1048a574161ef6fa6053b2855da50166e8e8677899d，固定输入 manifest SHA 23abe51243d90e12bf344c01e9c61ba90f6c859d4d03d02073ae291b9d226367。两份 original_request 的全部 65 个输入路径均在各自 snapshot 内找到且 SHA 相符；tasks 配置、prepared／private 文件、安装、正式分区及实际 image 与 input_check／attempt／report 一致。共享 solve_attempt SHA 00ca849909150de02769f297374a9bbfacf2746347c425474775d9c3e22a04f9 与当前 source manifest 对应条目一致；本 snapshot 未另存其完整源文件，不把 manifest 绑定称为对全部共享源码重审。

**真实模型与公开交付。** 首 HTTP user 题面分别与 solver_prompt.txt／attempt/prompt.txt 逐字相同，包含原公开示例和公开上下文；没有新增 hints 或私有修法。8511／8567 各有 23／44 次生成请求及真实 adapter 输出，HTTP 均 200、流无错误，最后 stop_reason=end_turn；8511 另有 1 次 count_tokens HTTP 200，不计作生成回合。第一轮即产生 Read 工具调用，属于实际 Coder 求解，不是 CPU 控制桩。

审 entry 数据流：公开 rollout spec／prompt 传入 solve；private host grading view 用于宿主 grading spec，结束后由 grade_original 消费原冻结对象。actor 实际 inspect 的 binds／mounts 为空，私有 host 文件没有挂入；两个 actual baseline 不含私有新增测试。全部请求正文中均无私有新增 node 名称及完整 effective test patch。以上结合了数据流、实际挂载、公开文件边界和消息正文，不只依靠搜索私有函数名。未宣称任意环境下的全部角色隔离或防信息泄漏测试。

两题执行前分别在 09:04:30.978–09:04:31.154、09:09:34.739–09:09:34.911 UTC 捕获当前 engine／adapter inspect 和 HTTP model/server readback；前后 CID、StartedAt、PID、restart=0、只读 /model mount 一致。实际服务为 Qwen/Qwen3-Coder-30B-A3B-Instruct，下载 revision b2cff646eb4bb1d68355c01b18ae02e7cf42d120、清单 SHA 5783533eae085661e3b3cde2e46ee46c9dbce0c05154d6028f6e46aa7260de39，engine CID 0752efbc6887af4d7cf59e583213447dd7f6488887c060d67df49baff3933af2，adapter CID d761d7ad2a8b744f2fc14dcd02b2e3742934f378ca4a30c855bc4e651d459bb1。实际 Cmd／HTTP 读回为 bf16、TP1、context 196608；adapter sampling 为 temperature .7、top_p .8、top_k 20、repetition_penalty 1.05，输出限额 65536。请求的 model_sent 与服务、首真实返回吻合。

identity_binding_actual.json 的 source_code=code_v4 是 03:48 形成的服务元数据；实际 adapter Cmd 也使用 code_v4 的 adapter server。它不能替代本题 queue_v24／code_v8 的执行 source 绑定。gateway_audit 的 checkpoint_identity_verified=false 仍保留；独立当前服务绑定足以支持本轮所声明的服务来源，但未逐文件重算权重，也没有 GPU 内存权重哈希证明。

**预算与环境。** probe-wide-v1 固定为 wall 10800 秒、240 回合、context 196608、每请求输出 65536、session 1024 请求、首字节 1800 秒、adapter idle 14400 秒。实际请求均带 max_tokens=65536；CC 内部 modelUsage 的 maxOutputTokens=32000 是另一处元数据，不能覆盖 HTTP 实际请求。最大实际 prompt／output 分别为 38587／819、39227／628，模型正常收尾，没有撞到预算。实际 solve 57.322／79.529 秒；CC 累计 input 629984／1090100、output 5063／7246，累计 input 含重复上下文，不是单请求 context 占用。CC 标价 cost 字段也不是本地 GPU 的实际费用。

actor 实际 Python3.8.19、UID54321，repo／home／tmp 可写，conda prefix 不可写；activation 与 prelaunch inspect／cgroup 核对成功，实际 actor 配额为 2 CPU／4 GiB／pids512。两份 pip freeze 前后字节不变；core 2.14.5／2.15.0 与固定配方一致。镜像导入和八 wheel 的 UID54321 可读摘要证据相符，但可读性本身不等于安装验收。正式 grader 的 UID54322 固定离线 prerequisite 实际退出0；完整 eval 日志中 editable install、生成 testing requirements、requirements install 全完成，install_rc=0、无失败命令，源码导入 /testbed/pydantic/__init__.py、版本2.6.0a1，随后正式测试退出1。受保护有效测试恢复／应用成功，control_surface RH2_PROTECT_OK=1、runner 前后 digest 相同。grade whole/setup/apply/test 限额 3600／300／120／1800 秒；实际 total grading 208.006／248.402 秒，未出现保护超时。snapshot 没有逐 Docker 调用 streams 或独立 grader prelaunch raw report；本次依据冻结入口、实际 grader CID/image、prerequisite／setup／保护诊断及完整测试日志核上述范围，不宣称另做了全套现场隔离验收。

**FrozenPatch 与完整 baseline。** 独立核 full tar 的 452／458 个文件内容、路径集合和规范 mode，完整 baseline census 和 grader 重建 census 一致，excluded path 列表及 digest 一致。tar 中三个 executable 原权限为0777，census／manifest 使用100755规范模式；核的是规范执行位及内容，并非原 POSIX 权限每一位相同。pdm.lock／pyproject.toml 在求解前已脏，实际字节进入 baseline；没有把这些准备变化算作模型改动，也没有以 clean HEAD 代替真实基线。baseline 的 environment_package_digest=null；assignment 环境 digest 非空，不能因此补填 typed 环境资格。

| 对象 | 8511 | 8567 |
| --- | --- | --- |
| canonical baseline digest | 40135f281c216e76a04de6772eaaadcdfd0b46d949e98c5164f29cba2f454e45 | eb494e7682db99522d57c38a96dc78b9469c0c6cbc36e33cdb811b1f25fc2d64 |
| baseline.tar SHA256 | 81eea77963c4a236dbe2151d000a12a55fd4c51da622f0b0804e2e17caa9a863 | c6728639451eec9b168632b1ba09af69b60848815ee1b156cd18332706cb8d19 |
| canonical FP digest | b8f75c2cd844fc318746adeda5ecbcce2fe8a04ee9c444fd9a08f39319972ea0 | a54c75aa6a946b6cb05dede88b0b5d02ac75269a40339c073c91d8bc3eccfa90 |
| FP 条目 | 1 个生产文件 | 1 个生产文件＋7 个自写诊断文件 |

每个 content_b64 字节摘要独立复算；review diff 的全部1／8个条目严格从实际 baseline 重放后等于 FP。projection 包含全部条目，rollout／physical attempt／public／runtime image／base／baseline identity 对齐，result／status／report 引用同一 FP，未 regrade。生产 delta 与题主导航副本逐字一致。8511 模型最终删除自写复现文件，仅剩 dataclasses.py；8567 七个诊断文件仍在 FP 并运输，但不改正式 tests／conftest，正式命令只测试 tests/test_validators.py。

**正式逐参考结果和失败机制。** 使用原 eval 测试区段保留完整 node ID 的独立读取，与冻结 private 分区及 diagnostics result 逐键核对；所有正式参考均为实际 PASSED／FAILED，无 missing、skipped 或 unaccounted，原 report 数值相符。

| 题目 | 原 F2P | 新增 F2P | 原 P2P | 新增 P2P | 原 reward |
| --- | --- | --- | --- | --- | --- |
| 8511 | 1／1通过 | 无 | 168／168通过 | 3／4通过 | 0 |
| 8567 | 0／1通过 | 0／1通过 | 158／158通过 | 0／2通过 | 0 |

8511 原 test_repr_false[Field] 已通过，三个新增行为也通过；唯一失败为 test_inherited_hidden_field_without_local_annotations。当前 Python3.8 分支新增 getattr(cls, '__annotations__', {})，在无本地注解的 Child 上读到 Parent 的 x；随后把继承 FieldInfo(repr=False) 包装为 Child 本地 dataclasses.field。标准库按 Child 本地注解检查这个本地 field，于 tests:2671 → candidate dataclasses.py:235 → Python3.8 dataclasses.py:885 抛 TypeError: 'x' is a field but has no type annotation。真实 baseline 的旧3.8 helper为 no-op，当前 FP 字节确实新增该包装；这是候选回归，未见环境或评分运输误拒。模型此前六个公开 AttributeError 经改用 getattr 消失，公开3个基本测试、4个 metadata 测试及162 passed／11 skipped／4 deselected范围通过；这些结果没有包含新增私有继承断言。公开示例实际改善为 x(y=3) a(b=1)，不能扩成完整语义正确。

8567 当前 PlainValidator 新增无条件 handler(source_type)，为保留 serialization 先强制生成内部 schema。原函数直接创建 plain validator schema，可绕过不需要的内部 schema；当前改动使 Unsupported、未解析 forward reference、stdlib TypedDict进入内部生成路径。原 F2P 在 tests:2860 的 WithUnsupported、新增 F2P 在 tests:2900 的 Before 创建时均经 functional_validators.py:157 → _unknown_type_schema 抛 PydanticSchemaGenerationError；新增 P2P 分别在 tests:2916 抛 Model 未完整定义／NotDefinedAnywhere8567，tests:2925 经同一新增 handler 路径抛 Python<3.12 的 typing.TypedDict错误。这些是在固定受支持运行条件下由候选强制内部生成造成的普通行为失败，不能只因错误文字提 Python而改记基础设施失败。

公开 bool 示例确实改善为 {"x":"0","y":"1"}。原 F 是多子场景节点，实际到 Unsupported才失败，此前断言已走过；其后 Replaced／Between／Both子场景尚未执行，不能从0／1推断公开 bool未修复或后续子场景均失败。模型首复现曾因3.8的typing.Annotated导入失败，改为typing_extensions后成功；另三次工具错误分别来自两份自写诊断脚本和一个不存在的测试节点。其中 debug_issue.py 因缺少 GenerateSchema.types_namespace 运行失败，fix_plain_validator.py 因一参 lambda 被 with_info 按两参调用而失败；两份脚本随后都未修正或删除，最终 FP 仍包含它们，属于完整交付缺陷。本次正式四节点失败不来自这两个文件；不存在测试节点的调用也不能算一次测试通过。最终只跑选中的公开1／1／8／11／1测试及2个自写测试，“all existing tests／backward compatibility”超出其证据范围。完整正式拒绝则来自上述四个实际行为节点。

8511 原日志184节点＝172P＋1F＋11Skip，来源 parser报告180键；8567 原日志168节点＝164P＋4F，其中6个非参考参数 ID含空格。报告中的180／168不等于对所有 pytest node语法的完整 parser states证明；已有非参考 parser限制保留。本轮正式173／162参考逐键完整，不把这个非阻断限制扩大成当前原分失效，也不宣称 parser已修复。

**终止、资源与清理。** 两题 terminal exit0、harness exit0、termination=completed，完整 raw JSONL分别276／517行；canonical副本中全部实际文本、工具调用和结果可对应，22／43工具调用及1／4工具错误与记录一致。CC 正常 end_turn与正式 tests_failed分开，outer exit0并不代表题目成功。

资源只按实际 CID／run_id 和时间窗核：8511窗口09:04:16–09:09:42 UTC共22样本，actor CID 244bd8e020d1721a5b05ee7c1ac8d0bb81e34ca5ff680603948597346be3813f、grader CID 2a202d3f619f7e013d00c6efd965948b5f0b4adc7aa2479c1044566638110d99；8567窗口09:09:20–09:15:53共26样本，actor CID 97a51c76fc5cfc10bfe435a6be9a667a898e917c9fc78c1aabe2af3304a9c0a3、grader CID d8f617a01e05aeb75be03bf8cc9923af222c8c3a5174d33a1a286d35848c78bc。可观察的 actor／grader／relay样本均无 OOM、oom_kill、pids max事件。actor观测 memory.peak约853.1／868.0MiB，pids.peak18／21；grader采样peak约555.6／561.1MiB，report峰值另为643.926／653.457MB，来源／时间不同，未混为连续测量。

两窗口 gaps_unknown=true；8567 09:15:36.268样本PID=0、cgroup与资源字段null，未当作0。最后样本出现后续9066容器，属于别的job；共享GPU的90113等数值也未算入本题actor峰值。这些采样只能证明对应观察窗口，不证明连续完整资源最大值或全机空闲。

pre_drain_stop与quiescence均 residual0、无timeout，workspace双读稳定，gateway revoke/drain active0。actor rm退出0，自己标签容器／网络为空，relay／network cleanup无失败。两份 grader manager各1建1删、containers_open／supply_open／cleanup_failures均空，cleanup_ok=true，regrade_events／total=0。实际运行收尾无本job残留；不外推 snapshot整理时或当前所有其他作业的全局清理状态。

当前没有需要否定这两份执行结果或要求材料／CPU改版的具体新阻断。候选回归可进入题主后续模型能力／题目信号分析；原分仍为0。仅 Coder首臂已完成，另一模型未覆盖部分不在本报告中置完成，也不据此授予训练、留出、typed actor租约或全题语义资格。同名JSON提供逐参考states、资源CID窗口、实际绑定和限制；汇总回执入口为 runs/ordinary_gpu_probe_20261002/migration_20261003/q24_first_coder_execution_receipt_v1.json。
