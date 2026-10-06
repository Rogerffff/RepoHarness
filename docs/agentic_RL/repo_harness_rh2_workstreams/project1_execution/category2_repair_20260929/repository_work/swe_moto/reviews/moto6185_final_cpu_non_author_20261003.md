# Moto6185 R13 全 22 对照：最终普通诊断 CPU 非作者验收

2026-10-03。审查性质：固定材料与实际闭合原件的增量独立验收。审查者已接触私有测试、金标与反例，不是公开盲读者。

## 1. 准入结论

**固定 22 臂的运行与评分验收通过；在既定题级范围内，当前 R13 材料可进入普通双模型诊断探针。** 22 个控制的角色、原分及失败行均与既有 v3 停止矩阵一致：18 个 raw0、4 个 raw1。16 个既定错误修法全为 0，noop 为 0，已知不完整的原 gold 为 0；ctx、parity 是两个有效正对照，ctx_list 是兼容对照。rv_dynamotype 的 raw1 仅保留为 observation_not_positive，不能写成第四种正确修法。

全部 22 臂实际 make init 成功，完整测试执行，实际 36 项逐一对应原 1F/34P 的 35 个解析参考键；原 34P 在每臂全过，历史合键的两个完整参数实例在每臂都 PASSED。每臂都有正常 report、完整 CLI footer、候选删除、manager 关闭和自有容器/网络查询成功且为空。没有将安装/基础设施失败计为模型 0，也没有以包装 exec0 代替内层 pytest1。

开发 UID 54321 的真实原安装、生产 sanitize/init/activation、工作区模块来源、SDK、物理资源及清理已核；真实 CC 2.1.205 与确定桩的原 C1–C4 四公开操作已核。实际 statement prompt 交付成立，六行 generic public_hints 未进入首请求；完整命令输出在进程侧保存，CC tool_result 只含 RC 标记。这些已知交付限制保留，不能写成完整 public bundle/hints 已送、CC 看见全部输出或自主模型已求解。

当前没有剩余的本题普通诊断 CPU 阻断项。准入依据是既有明确保护范围、有效正负对照及实际环境/开发路径证据；不是通过降级 rv_dynamotype 的角色豁免一个已在有效评分范围内的缺陷。已知多类型标签差异由此前明确的范围限定处理，理由与限制见 §7。训练、留出集、typed actor、fresh autonomous fullprompt、actor FrozenPatch/a2g 均未授予；GPU 实际部署与模型执行也未由本报告预验。

本报告只新增最终验收文件，复用已固定有效部分，不修改旧报告、材料、输入、注册表或运行原件；未运行 SSH、CPU、Docker、项目、SDK、测试或模型，未发起新实验。不存在为了完成本报告而追加的输入穷举或重跑。

## 2. 增量审查链与原件范围

固定部分报告 reviews/moto6185_r13_partial_cpu_non_author_20261003.md，27770 bytes、SHA256 b45a7bfba13e59a3412497236824da69704fd72535598f8ca1bbd44737a62f32，已经独立核 noop、group1 四臂、实际 UID 安装及真实 CC，共 162 件原件。本轮确认该报告固定字节未变，复用其适用结论，没有重做这五臂/UID/CC 的整套验收。

随后独立读 group2+3 九臂 190 件、group4 四臂 88 件，最后增量读 group5 四臂 88 件。新 17 臂逐组核 transport SHA/bytes、归档与本地精确成员、consumer/runtime、单行 ledger、完整安装与测试段、全部 FAILURES 段、逐参考状态、FP 投影、原 CLI footer 及自有查询。作者 reader true、owner 报告或文件名没有代替原件。

本报告中的 CPUROOT 为 runs/category2_repair_20260929/moto_cpu_20261003；OWN 为本 swe_moto 根。原件入口为 CPUROOT/<job>_evidence/，归档为 CPUROOT/<job>.transport.tar.gz。八个不同归档共有 528 件运行原件，14,090,704 bytes；其中六组矩阵 499 件、13,839,022 bytes，UID 6 件，CC 23 件。数量不是实验次数，也未加算作者/非作者自行生成的读回记录或 transport_manifest 本身。

| 已闭合 job | 原件数 | transport_manifest SHA256 | archive SHA256 |
| --- | ---: | --- | --- |
| moto6185-cpu-34561d16159e | 45 | 10e0a7e39e03f721d8c6d1cfb87dacc203696066c0c20b1f1606aa4ce72ef53e | 0e5b23b58c608b6b1be73089c776a9ec566c6c1a8c970580da1283f81118d4c7 |
| moto6185-cpu-d3ebfdc58aa8 | 88 | b3bd95d3fe240e4d46f22f0e50ef82b4263b6815657ff875fbae948afced3f97 | e4e24a8d76fde4ccef67c3d9c6f2e4d221f2a9ecbd9fddf82cbdebe069cd9fbd |
| moto6185-cpu-171d1b6897be | 102 | ca15ac962795e649a5a4d939607f848f1ea9a4e8d944887918bb6f65e29a469f | 248433b0c5fa8144523e6a2c999c5e867bc5455ab9e2163e8911cb4368dfd17a |
| moto6185-cpu-2a9a5338febf | 88 | 80cc25181611f58c94ffff37cb735198b216a59fa62cdbbbb83e43a905c4fe4f | b84d3980b1cf09e09242b2c3e1b5d43c933b6d1bed32cc00fd10bbc31aafb492 |
| moto6185-cpu-811928f6a0d2 | 88 | 0447a7eeade865d395b0e158e365dee9ef03956f37470a55739ace34df42b099 | 5c118782cb45cd2e97304d0b35b5296d1e2c270a3e152404c2f29ca5276ddd3f |
| moto6185-cpu-28e751fc3785 | 88 | d20fddb26721399bc4bbd82f537ed9feffd33514d573251838fad3e4cab33bf4 | 3213a42a5dc48e601943d904f9ee7a0de011bbb1fbfa9cf84320fdc5c5b348b5 |
| moto6185-uid-9859d882f206 | 6 | 24c325c2aa46850e0d1b03e431cd1a78dba38c9f03adfd177d6624aff2690c62 | f822eb7e72f4d9fd85585d6ec11a5b2ce677a12f6928311dcc2b11d1641e7c38 |
| moto6185-actor-262aa667567f | 23 | ac24e06b9ba326504c2a84561b6d2e259021c9f44595029fbc7eab4776643a1b | 7697cfc2f06887929cb4e501bf4fe12858244dc95b090a11922bb0a2bc76407a |

各组核验均确认精确文件集合、非符号链接、每件 SHA/bytes 与 manifest 一致；只读 tar 内普通成员与本地字节一致，没有提取/覆盖原件。全部 job/status.json 实际 finished、parent returncode=0；没有把入槽 75、在途或未知作业当闭合样本。最后 job 的 manifest 为 15517 bytes，archive 为 507272 bytes；原件合计 2530662 bytes，闭合时间为 2026-10-03T07:01:42Z。

已固定增量笔记在 CPUROOT/moto6185_non_author_incremental_notes_20261003/，记录的是本审查者的原件核查，不是新评分实现：

| 笔记 | bytes | SHA256 |
| --- | ---: | --- |
| group2_group3_closed_raw_notes_v1.json | 169514 | 843bb9458607e45e8f6bf416a4386cae49102183c0a7a65562dc2d1e1d548b06 |
| group4_closed_raw_notes_v1.json | 62097 | ff92fb14335b0ce777f651d87455d8ef8f16a4e6b45172b5aa5d4ebd6deb4674 |
| group5_closed_raw_notes_v1.json | 74523 | 75af527c05e8e8063ed722f2ad0992fe65cafa26be25246083267bf6ec86f0c1 |
| all22_consistency_notes_v1.json | 5221 | 1c227089aae92a7fe5826ee75e34456256c24c06ba16b0b83b05bc340d550649 |

最终还将 22 个独立读回的 role/reward/install/test/job 与固定 acceptance_matrix 控制列表和全矩阵 owner 表逐项比较。名称集合、顺序、角色、奖励、阶段退出与秒数全部相符。全矩阵作者报告 tasks/getmoto__moto-6185/cpu_matrix_owner_readback_r13_20261003.md（9070 bytes、0e65a6ff2440201826a25bc91b40126f177ad043410a51d9935c0da31079970d）只作这一对照与导航。末组 owner 报告为 2545 bytes、ee92c9e8f52d927a286325ce57aac666229227efcc8152972c398a3d8b4874df；末组 reader 为 69138 bytes、b95d45bb7697ecd3a14c29e4394a3966746123e5af411c3d7cf01ab9bbbbdd73；均不据其布尔结论授准入。

## 3. 六组共同消费身份和原执行条件

原消费者来自固定 R13 cat2-cpu-r2e089092-swe27-pandas-moto-20261003-v1，仓库快照位于 runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe27_pandas_moto_v1/repo；release manifest SHA256 3fad18daff8db219294e10cbf08d4424d68cf7000d008bb983cba4bdc427b641。工具复用此前已审 moto_four_r13_matrix_v2（manifest 6cd02683d46370adf553531064f29d99a1e9da47ebf9f3c909f1bc6fdb9d1fd3）的原 prepare/export-gold/run 与正常评分 guard，未另写 grader。

六组 runtime_inputs.json 完全相同：7142 bytes、SHA256 d14b50614a95b88df45d74b60a94e00f4d8b0772390ad8937ed26e93ffdc5df1。新 17 臂的 consumer_readback_before_checks 与已审工具的本题 expected_runtime 实物解码内容一致；各实际 ledger 的材料、revision、scripts、镜像、预算及原参考分区也一致。固定部分报告 §3 的脚本单件身份仍适用。

| 绑定（digest 省略 sha256: 前缀） | 固定值 |
| --- | --- |
| task / base | swe_gym_lite::getmoto__moto-6185 / dc460a325839bc6797084a54afc297a2c9d87e63 |
| public bundle | 2a2ae08fcef35f245257572088bc8f79d3eb0827f8025f358e93764c085e5a15 |
| ENV | 161da515114764dd74ff279cbe8a7aff39dc647b1de2748c6ec85f9f473772b4 |
| grading bundle / revision | 60e14bedb18e640e7b577ae10dc610efcec6f89fb7b3b44b7e9298aa3aa7e5c1 / moto6185-nested-s-v3 |
| registry | deb67b2a3b521c29bb1b8c5ca6b7e485c4cae3e6c76336f804da3d533390cf66 |
| grading materials | edbb9f5f978049bfb82c5bcfaa6b70c15a493bbad42e4e80f4d5318952359fa2 |
| effective test patch | fc65a52722f47a6d458465d2e4a529caa057c2f238453d1659efdfef42bc332d |
| scripts aggregate | 507abe2e5732da65c47016e03e2d10a100d771e205a7944beaa55baf4be87851 |
| 原 source ConfigID / manifest | 47443b04543c5fa25c85bb4e86c871f1f98ea0df9e254b2ca8fac9f9bdb19325 / ade7d85a8ef82a6d87940dd9c8d486e50b27dcc33e968e55f50421adf6864eda |
| 实际 COPY-only ConfigID | 79d39d611186289b10956c2f845af1272218a1f4cf8fc00382c7c6ab4eced35d |
| recipe / recipe SHA256 | moto6185-fixed-environment-v1 / db39d769d399b98bb1728948ea906223145467bb5878659cb6aed8abf7243f36 |

公开 source face 仍是 xingyaoww/sweb.eval.x86_64.getmoto_s_moto-6185:latest；实际 CLI 显式 --derived-image 为注册 79d39d… ID、--derived-image-recipe 为原配方，overlay=null。派生是原 COPY-only 供应诊断 override，未把 source manifest 冒充 ConfigID、未更换公开 base 或材料。实际离线 find-links 是 /opt/rh2/build-wheels。

原命令仍为 make init 和 pytest -n0 -rA tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py。setup/reset 300、apply 120、test/grading 1800、candidate 900、whole-child 1800、cleanup 120、pull 1800 秒全部保持。评分 UID54322 的原 policy 是 2CPU、4GiB、PID512、shm64MiB、deny-all 网络；开发 UID54321 与评分角色分开。ledger resource_facts=null、env_qualification 未授，不把评分成功扩成训练环境资格；开发物理资源由独立 UID/CC 原件证明。

## 4. 全 22 臂真实评分与具体目标失败

所有臂 stage_error=null，outcome 只为 resolved 或 unresolved，failure_category 为 null 或 tests_failed，reward 为 1 或 0。4 个 raw1 的完整 pytest 为 36 passed；18 个 raw0 只有目标 F2P 失败，实际为 35 passed/1 failed。报告不将 gold 0 改写为 1，也不将 rv_dynamotype 1 改写为 0。

下表按固定 acceptance_matrix 顺序。test rc 后的秒数来自实际原分段，不包含环境准备、保护、复制、清理或运输耗时。测试行号指 tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py。

| 控制 / 角色 | raw | install rc / 秒 | pytest rc / 秒 | 完整日志中的目标结果 |
| --- | ---: | --- | --- | --- |
| noop / noop | 0 | 0 / 12.131 | 1 / 7.156 | 944：合法普通属性名 S、字符串 asdf 被拒，SerializationException |
| gold / gold_known_incomplete | 0 | 0 / 10.263 | 1 / 6.544 | 994：合法 key_named_m 的嵌套 S 被拒，SerializationException |
| ctx / positive | 1 | 0 / 11.336 | 0 / 6.450 | 全 36 实际项通过 |
| ctx_list / alternative_compatibility | 1 | 0 / 10.541 | 0 / 6.286 | 全 36 实际项通过 |
| depth2 / known_wrong | 0 | 0 / 10.862 | 1 / 6.341 | 967：实际 pk=deeply_nested，合法 A.M.B.M.S 被拒 |
| list_as_names / known_wrong | 0 | 0 / 11.404 | 1 / 5.571 | 967：实际 pk=nested_in_list，合法 A.L[0].M.S 被拒 |
| null_only / known_wrong | 0 | 0 / 11.739 | 1 / 6.716 | 944：合法顶层 S 字符串被拒 |
| parity / positive | 1 | 0 / 11.046 | 0 / 5.980 | 全 36 实际项通过 |
| rootkey / known_wrong | 0 | 0 / 13.837 | 1 / 7.587 | 1006：非键 S 字典值进入 Item/DynamoType/bytesize，内部 AttributeError |
| shape / known_wrong | 0 | 0 / 11.077 | 1 / 6.381 | 938：畸形主键 S 字典值进入 _validate_key_sizes，内部 AttributeError |
| siblings / known_wrong | 0 | 0 / 11.334 | 1 / 6.901 | 967：实际 issue_nested 的合法 A.M.S.NULL 被拒 |
| skip_s_subtree / known_wrong | 0 | 0 / 11.748 | 1 / 6.652 | 978：畸形 N 校验循环 DID NOT RAISE ClientError |
| swallow / known_wrong | 0 | 0 / 11.391 | 1 / 6.566 | 978：畸形 N 校验循环 DID NOT RAISE ClientError |
| top_only / known_wrong | 0 | 0 / 10.510 | 1 / 6.099 | 967：实际 issue_nested 的合法 A.M.S.NULL 被拒 |
| rv_break_after_s / known_wrong | 0 | 0 / 11.742 | 1 / 7.229 | 978：校验循环 DID NOT RAISE；patch 在属性名 S 后 break |
| rv_depth4 / known_wrong | 0 | 0 / 11.074 | 1 / 6.730 | 967：实际 pk=five_levels_deep，合法五层 map 中 S 被拒 |
| rv_dynamotype / observation_not_positive | 1 | 0 / 11.519 | 0 / 6.228 | 全 36 实际项通过；多标签差异没有被本材料断言 |
| rv_scalar_s / known_wrong | 0 | 0 / 10.923 | 1 / 6.726 | 967：实际 pk=S_holding_a_map，合法 S.M.S 被拒 |
| rv_shape_key / known_wrong | 0 | 0 / 11.424 | 1 / 6.802 | 1006：非键畸形 S 值进入 Item/DynamoType/bytesize，内部 AttributeError |
| rv_swallow_attr / known_wrong | 0 | 0 / 11.847 | 1 / 7.394 | 978：校验循环 DID NOT RAISE，日志无 loop locals |
| rv_tagparent / known_wrong | 0 | 0 / 10.547 | 1 / 6.071 | 1006：非键畸形 S 值进入 Item/DynamoType/bytesize，内部 AttributeError |
| rv_top_or_null / known_wrong | 0 | 0 / 11.979 | 1 / 6.452 | 967：实际 pk=deeply_nested，合法 A.M.B.M.S 被拒 |

上述合法值误拒的完整 traceback 实际为 PutItem 的 SerializationException，消息 Start of structure or map found where not expected；没有以文件名“已知错误”代替失败语义。内部错误的 traceback 实际到 moto/dynamodb/models/utilities.py:16，val={'S':'asdf'}，AttributeError: 'dict' object has no attribute 'encode'，不是预期 ClientError。最后两份 1006 日志有这个内部 val，但没有该循环的 attributes locals；保留具体异常，不凭相同 val 独立断言当前运行一定是第一或第二个循环项。

DID NOT RAISE 的完整失败段没有当前循环 locals/API 参数时，只验收实际拒绝检查未触发，机制来自精确 patch 的静态对照另行说明；不能据静态机制推称每个循环项都实际跑过。rv_break_after_s 的 patch 先校验 S 子树再 break，后续成员被跳过；该机制与 978 DNR 一致，但 runtime traceback 仍没有逐轮 locals。任何目标函数均在首个失败处停止，失败后未到达的循环项或后半段不写成已通过。

五层阈值、list 内 map、S 自身持有 map、主键名 M 和非键 S→dict 的既定保护路径已经有真实正负对照。本报告不延伸为无限深度、全部畸形组合或真实 AWS 报错规则的验证。

独立从各完整 short-test-summary 回收原状态，按固定 parser 到首个空白的历史规则得到 35 键；逐一与原 1F/34P 对齐，没有 missing/skipped/unaccounted/outside-segment。唯一 F2P 是 test_put_item__string_as_integer_value；原 34P 全部实际通过。历史合键不是少跑一项，以下两个完整实例在每臂都 PASSED：

- test_update_item_with_duplicate_expressions[set example_column = :example_column, example_column = :example_column]
- test_update_item_with_duplicate_expressions[set example_column = :example_column ADD x :y set example_column = :example_column]

两实例的历史解析键同为 test_update_item_with_duplicate_expressions[set。parser 保持原样，实际 36 项/35 键的区别与双方状态一同保留。

全部原安装段标记、原 make init、两轮 editable build/install 成功与退出 0 完整保留。新 17 臂安装全文与此前已读段比较，仅两处固定 editable wheel 生成 SHA、两个 pip 临时缓存名和最后结束时间戳不同；规范化只针对这些精确行，wheel 文件名/size、所有依赖、build/install 与其它字节一致。没有宽泛过滤错误输出。末组 owner 比较记录 SHA256 c5f73508049958b769ededd9784ea462378213b32a17d6bc58b6bf9b9afbcaea（2420 bytes）可导航，实际规范化独立重建并与前述已核中间笔记摘要一致。

## 5. 精确候选身份、投影与资源闭合

公开 base moto/dynamodb/models/table.py 为 39690 bytes、SHA256 68bca68efb75b08b768b4856326771cb2ee970c1d3ccf2533266fef4c3459007，来自 runs/swegym_quality_batch03_20260921_v1/public/getmoto__moto-6185/base/。新 17 臂的 candidate.patch 均与固定 tasks/acceptance_matrix 所指原补丁的 bytes/SHA 及本地实物完全一致；用标准库内存逐 hunk 对 base 应用后，与新 CPU FrozenPatch 解码 payload 完全一致。没有执行 git apply 或项目。

所有 21 个非空控制都只有 moto/dynamodb/models/table.py 的 regular modify、mode100644；noop entries 为空。新 FP 的 baseline canonical digest、public/runtime/head、canonical FP digest与 ledger/projection 相符；没有测试路径、conftest/fixture、私有 pathset 改动或不支持形态。kind=cc 是原 CLI patch 输入枚举，不是自主 CC/模型产出的候选。

最后四个新实际 FP 的关键 pin 如下；此前 13 个增量和最初四个非空臂分别见固定增量笔记与部分报告，均已独立投影，未在本次改绑为模型历史 FP。

| 末组控制 | 原 patch SHA256 / bytes | 新 payload SHA256 / bytes |
| --- | --- | --- |
| rv_shape_key | d0c1275343e37364c2cf498da6873a468574d8c048062a38cdd82c12ccee04c3 / 1815 | cd6945c930c67721f5ce8a1dc9323e7ecdec34ec5f6faf3a450157cb72eafe61 / 40281 |
| rv_swallow_attr | 9d37f01bbaf924417cc7889e2864c4ed1acee834157b39a44dc37e40eb1a4435 / 792 | ebad23adb0f2efd5c6f18b767b730a862c6260c75f4edbe0750b83eacb8e4aa2 / 40071 |
| rv_tagparent | 9d4c841f0232b34c61ed053d7f79a48bbfe03bdbd3ffed2a7527e8d90af91b40 / 1429 | cf2b764a293b6c340215ddb2486ca4f77eecb5380926959a2eb419507aba7cf5 / 40122 |
| rv_top_or_null | 5d441c3e35d6de99bab5a259b4d229e4eb2b5ba6edf161ee017ad3cbbc26b8e7 / 1192 | 8e47b92baf7e522e743438cda2d135399767adc451a5185d755c05f5844aacf7 / 39915 |

候选和评分 sanitize 均 verified，回到固定 base，history7501，remote/reflog/unreachable0，violations为空。trusted setup 实际 restore1/apply0/expected test file1/actual1/setupOK；控制面保护文件1、目录4、保护成功且无缺失。candidate.apply_user=agent/54321，不混评分身份。

每臂原 run stdout 的最后完整 footer 是 rows=1、halted/aborted=null、final exit0，manager created1/removed1、containers_open/supply_open/cleanup_failures为空、regrade_total0。候选 cleanup removed=true、rm:ok、detail空；完整 run stderr 为空。每臂 output/residual_<control>.json 的容器/网络查询都实际 returncode0，完整 stdout/stderr为空，查询失败未当成零残留。正常 reward0 的原 CLI exit0、包装 exec0、内层 pytest1 是三个不同事实，不合并成“测试通过”。

末组四份完整 eval.log 的独立 pin 为 rv_shape_key 54748 bytes / 3afde48bed7944d504fb6d702d161c8db9027dc5d22c820922ddab5b9313d3b5；rv_swallow_attr 48017 / 1daec18e167245a83d9b0df2881b26529a54ed4582e9316e86e6551d898d2d73；rv_tagparent 54328 / 7ad52d265fda8e0e76df7801be094f840ab30c515d10e5a55c51a2afab0f2b94；rv_top_or_null 51685 / 8e9ec5484146012a47cf45a3fac733470139d82b6af59cc49b24f1cae2f49b14。路径均在该 job 的 output/<control>/eval_logs/，可直接追到完整失败段与参考状态。

## 6. 复用的实际开发 UID、公开 CC 与交付限制

UID job moto6185-uid-9859d882f206 的 13 次 Docker 调用全部实际 0。真实 UID54321、HOME=/home/agent、原 BASH_ENV=/rh2/bash_env 执行 cd /testbed && PYTHONDONTWRITEBYTECODE=1 make init，完整 stdout21045/stderr426 bytes，两轮安装成功。随后实际 UID/GID54321、cwd/testbed、testbed 解释器/prefix、/testbed/moto 与 /testbed/moto/dynamodb/models/__init__.py 来源成立；模块 SHA256 740a35208924fc2a99ab809f2734ef0b258664bbf571a5fdacd0277b379bf74e，与原公开 base 相同，boto3/botocore1.35.9。实际 79d39d… 容器 inspect 为 2CPU/4GiB/PID512/shm64MiB/network none，finally删除及两个自有查询 rc0空。该证据不是评分 UID 安装，也不是 CC 调用 INSTALL；它与 CC 是不同容器。

CC job moto6185-actor-262aa667567f：真实 CC2.1.205/确定桩，46 行 trajectory，四个 Bash 内层命令与原公开 C1–C4 逐字相同；五次消息起点对应五个真实 stub 请求，最后 harness/result/parent0。C1 解释器、本地 Moto 与 SDK 正确；C2 首先完整观察到 control_lower_s/control_A/list_map_S 正常，top_S/nested_S/deep_S 仍为原 SerializationException，最后第31行 AssertionError:['top_S','nested_S','deep_S']，原 bug 实际存在。C3 原两公开节点2passed，C4 原五公开节点5passed；不是私有35参考或自主求解。

首真实 request output/stub/requests/messages_000.json 为15195 bytes，SHA256 74a8ddcce7afed801235f44bf9cbb7a633d4709c7fb37fffa61ca29878a8b069；实际 statement spec.prompt2550 bytes，SHA256 416f16088cd1d3725ba9d657713dbc9580026c5add8446ea142fff3d6811c37b，在首 user 文本精确一次。六行 public_hints719 bytes（4c44aa0b42dc948bc10e52b927058ab3b567b9b436cd1c4beb299878be72ceb4）均未进入首 messages/system。其含义是工作区起点、预激活 testbed、只改非测试源码、评分复原测试、窄测试和总结停止。

原 R13 bundles.py:282–289 的 render_user_prompt 只渲染 repo/workdir/base/problem_statement；prepared_task_face.py:769 使用它，完整含 hints 的 public_bundle_payload 为独立字段；薄工具 actor.py:165–168 原样传 --prompt spec.prompt。该既有 renderer/请求边界与具体 rawref 在固定部分报告 §8 已独立查明，不是新工具丢掉已有 statement 字节。本报告不把完整 prepared statement 偷换成完整 public bundle/hints。

四份 captures 完整取回，但 CC Bash tool_result 实际仅 RH2DC_END…RC 标记；模型是否看到完整结果没有被证明。原 interpreter_in_tool_result=false、bashenv_denied_for_agent=false 按标记判据保留：C1 完整捕获证明子进程解释器正确，prelaunch 另证明 activation 写拒绝，二者不冒充相应 CC tool_result 中的证明。actor prelaunch 实际 54321、受限资源、relay 网络及直接 upstream/DNS 拒绝已核；它不是 UID smoke 的 network none。

旧 post_run_facts_root.txt 文件名不证明 root，实际 post_run_fact_actual_role=agent_uid_54321。清理前进程4、新增 newer entries93 及部分目录/pycache列表保留，不能概括93个全是pycache或全目录没有产物。barrier 后实际 RH2_AGENT_PROCS_AFTER=0；attempt finally 的 container_rm0/stub_rc0、relay/network failures空、最后自有容器/网络空。原 helper 对查询失败会记录失败 sentinel，最后空 residual 未把失败查询当清空。

reviews/moto6185_r13_public_actor_scope_clarification_20261003.md（1943 bytes、6c7cffb868928d1d78c3697abc67e5407905e8b447747345d2a6a69322c793f7）与上述独立限定一致；其中作者关于 GPU code 路径的后续描述不代替本报告对未来 GPU 首请求的独立核验。

这些限制不使当前已执行功能、实际开发安装或固定参考评分无效，也未发现它们造成当前普通诊断的决定性运行失败。完整 hints 交付、自主完整反馈求解、训练轨迹、安全标记全部通过等更强声明均不成立，仍须在对应用途实际验证。

## 7. 既有停止范围、raw1 观察与当前普通诊断资格

这里将“22 臂运行验收通过”和“当前材料可进入普通诊断”分别判断。前者来自原件；后者还依赖此前明确题级范围、有效正对照与实际开发环境。没有只用所有 matches_expected_reward=true 或几个满分作准入理由。

实际读取的原独立复核位于 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/getmoto__moto-6185/review.md，28545 bytes、SHA256 7a73a3020f80bdfa3c194980b70c2ba6f2bce6f19ecc0d3010c5dc3e6fe94b44。§6要求原22臂与v3私有模拟逐格奖励/失败行一致；一致即结束，不一致只查对应材料、镜像、UID或解析格，不重开整题判断。当前正式22格及失败行已一致。

§5非阻断建议4明确“范围外、不断言、只登记”，§6停止条件4明确“以下不再构成阻断理由，只登记”：深于五层的阈值、其它未保护属性名/类型标签组合、list内畸形值、S布尔/列表值、多类型标签、服务器HTTP状态、真实AWS精确文案。它们是已存在的具体范围限定，本次没有新增例外或扩大需求。

同文§3.4及§5建议5明确记录 rv_dynamotype 可存入特定多标签值 {'S':'a','N':5}，而 base 会拒绝，故 rv 不作正对照。这个事实未被抹去；§6笼统背景句“base本来就不校验…多类型标签”也未被本报告用来概括所有多标签行为。当前普通用途沿明确的范围排除处理这个差异，不声称差异不存在，也不声称 rv 广泛正确。

现行 coordination_workflow_20261003.md 第7行要求已知会妨碍合理求解或造成错误评分的缺陷先修复复验，同时明确不替代统一标准/用户准入边界、适用既有证据按范围复用。因此 observation_not_positive 本身不能免除有效评分范围内的假阳性；但上述多标签反例已由具体既有停止范围排除，本轮没有新的范围内漏判证据，也不能仅因存在一个已登记范围外差异，就自行加新阻断或新断言。此解释依据的是条文适用范围，不是把 raw1 改成另一种分数。新的模型若在当前保护范围内引入回归或漏判，仍须据实际源码与轨迹处理，不能套用范围外登记免责。

范围读回 reviews/moto6185_existing_stop_scope_readback_20261003.md（2107 bytes、8515456bc1d293032484304c9881f9d575b6428b3da1596abfbc55a53a0c60c0）与原文一致；它是解释旧范围的作者导航，不是新的用户决定。非作者的独立条文笔记 SHA256 31a45b8b9d30351069756aa596b6e12c1c08ffb1a7fd6b45012a8aa6e8b17533 保留在 ignored 目录。

据此，当前固定 R13 修订满足普通题目/双基座诊断的 CPU 与独立验收条件，可以另固定普通 probe 请求。probe 应明确实际 actor/grader 镜像及已验证范围，保留 statement/hints、输出可见性和评分语义限制；本报告没有提交请求或发送 GPU 通知。未来 GPU 需另核实际 code、物理镜像、UID/安装、预算、实际首请求、轨迹及候选/评分身份，不能由本 CPU 原件自动宣称 GPU 已可运行。

本轮没有未完成矩阵臂，也没有仍需本报告补做的 CPU 实验。单次对照和约10–14秒安装、6–8秒项目测试不证明性能稳定性；准备/保护等其它阶段耗时未归因模型。训练、留出、typed actor、完整 hints 交付、自主模型能力与 actor FP/a2g 仍是未授用途，不随普通诊断准入自动获得。
