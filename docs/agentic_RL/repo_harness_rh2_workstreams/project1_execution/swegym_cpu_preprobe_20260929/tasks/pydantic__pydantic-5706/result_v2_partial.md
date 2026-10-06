# Pydantic5706 v2：actor/private/noop/gold 已核（partial）

2026-09-29，`symptom_v2_20260928T201808Z-232b80`。**修正的症状诊断已通过；私有退化真实破坏Python Sequence既有行为；正式noop是有效目标0。** gold后续完整落盘亦已核；本稿尚不对正式退化作判断，S1和P5均保留，不能仅加后检就进入能力比较。

旧轮异常预期错误及全部失败原件保留在result_partial。新轮只补跑一条public_original_symptoms，精确捕捉core0.31的schema错误及NotImplementedError文本并到达尾marker，rc0。新trajectory仅1个Bash及对应tool_result；prelaunch/activation正常、trusted_init UID54321、实际原image与base均匹配，清理container/network/relay/stub无残留、agent进程0。新命令不重复打印身份探针：公开identity和两组回归引用旧轮，10份receipt原件SHA本地逐项匹配，不扩大为新轮又执行了三条。旧core0.25题面示例与base/core0.31区别仍在，症状0不等于支持/拒绝目标已澄清。

独立root私有三方均为原image `3e3b78ae…`、Python3.8.19/core0.31/checkout导入，准备及预采集成功。base的精确症状诊断及4类型值控制通过，旧六项6passed/645deselected；gold保留list/tuple/range/deque行为，旧六项也全通过。sequence_list补丁将collections.abc.Sequence映到list：tuple/deque实际变list，range抛ValidationError/list_type，新探针三项明确失败；旧六项中tuple、range、deque与tuple-of-tuples四参数失败，2passed/645deselected。每个命令仍执行至PRIVATE_COMMAND_END，matrix按既定预期解释rc后到达完成marker；matrix rc0不表示退化语义正确。三私有容器rm/query0、remaining空。

私有spec绑定固定v2补丁文件，git apply均0且之后git diff显示目标文件变化；本版没有独立导出private完整源码SHA，因此不把receipt称为完整私有源码字节验收。后续将与正式完整frozen导出、输入补丁及base逐字核对。gold/退化没有运行base症状诊断，不据私有记录声称其JSON目标已实测支持。

8个公开wheel下载日志文件名/尺寸/SHA与冻结manifest一致，derived image `d8e8a4475e62b5c38ec3629a6ed33bad147ef915084d311f1571325285dbb943`，保留原13层加COPY层，离线PIP环境设置可见。同步不含wheel内容，未本地重算wheel字节；历史1021byte canary仍排除。

noop沿既定candidate-aware recipe执行editable安装并消费testing/testing-extra，install rc0/4.443秒，core0.31、pydantic2.0a4从/testbed导入；runner摘要前后一致。两个F2P `test_sequences_int_json_schema[sequence_type1]` 与 `test_sequence_schema[sequence_type1]` 均因IsInstanceSchema的PydanticInvalidForJsonSchema失败，273个P2P逐ID在原日志全PASSED。完整pytest是2failed/275passed/1xfailed；多出的两个PASS为带空格参数名的callable非可序列化默认值测试，1XFAIL为公开已有的test_get_pydantic_core_schema_calls，均不属于来源参考，没有参考缺席、重复或额外失败。完整测试段rc1/3.392秒，reward0是正常负对照。日志SHA `259fb48b685622ce5094a9a9d9f7ac69dc03f146f7d5bc0eaf35378cf14d978e` 本地重算与ledger匹配；noop投影included_paths为空。

candidate removed=true；原grade_noop.log最后manager_close记录创建/移除各1、open/supply/cleanup为空、final_status exit0。此runner没有单独driver_close_checked.json，本稿直接核原driver日志，不因receipt文件名不同推定清理缺失。setup170.798秒，2CPU/4GiB、准备900/test1800/whole3600；内存峰值678.469MiB，resource_facts=null，不外推全程无OOM。

gold正式补核：2F2P+273P2P全通过，完整277passed/1xfailed，reward1、install0/4.205秒、test0/2.576秒，setup162.298秒，mem672.586MiB。完整导出_generate_schema.py为60545字节、SHA`82a04ddea65392cf028fecf3acb54c36ef6975540d24b483a74403d5c5fc4522`，逐字等于公开base+输入gold补丁，实际candidate.patch也与输入一致。原日志SHA、完整标记、runner前后相同及candidate/manager两层清理均正常；逐参考详情入evidence_audit_v2_partial。通过JSON schema参考只说明正式参考结果，P5目标方向未因此解决。

剩余：正式sequence_list完整原件/实际导出/逐参考与双层清理，root parser/SHA，跨包最终审查。D6未实施；真实题面/public_hints、自主模型、GPU/训练资格不由此次CPU诊断授予。

证据：[新actor](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-5706/symptom_v2_20260928T201808Z-232b80/actor_symptom_v2/attempt.json)；[私有退化原输出](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-5706/symptom_v2_20260928T201808Z-232b80/private_sequence_list/sequence_list/private_matrix.out)；[noop完整日志](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-5706/symptom_v2_20260928T201808Z-232b80/grade_noop/eval_logs/evallog_replay-cpu29-symptom-v2-_cb00d579.eval.log)；[逐参考审计](evidence_audit_v2_partial.json)；[partial机器记录](result_v2_partial.json)。
