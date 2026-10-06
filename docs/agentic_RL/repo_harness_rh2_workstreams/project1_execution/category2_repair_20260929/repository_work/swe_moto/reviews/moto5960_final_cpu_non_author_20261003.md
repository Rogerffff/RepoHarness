# Moto5960：固定 R18 实际 CPU 非作者验收

2026-10-03。审查者为本题工具、材料和运行的非作者；已读私有断言、对照补丁和金标，不是公开盲读 solver。本次仅使用本地标准库读取、解析和 hash 已闭合原件，补丁比对只在内存进行。没有执行项目、SDK、测试、Docker、CPU、SSH、CC 或模型，没有改写冻结输入、工具、共享实现、原件和既有报告。

**结论：固定 R18 的三臂正式评分、真实 UID54321 开发安装和真实 CC 六条公开命令在约定范围内验收通过，无当前结果阻断；可用于本条件下的普通 CPU 诊断／基座探针。** 实际三臂 raw 为 0／1／0，三次 `make init` 均为 0，158 个 parser 参考完整，155P 全部通过；漏 KEYS_ONLY 控制准确触发新增 scan 断言。独立 UID 及 CC 下的原公开安装也成功，CC 的目标复现失败来自原公开 bug。确定性桩驱动真实 CC，不是自主模型解题；不授予 typed actor／训练资格，不证明 actor→FrozenPatch→grader 的 a2g 链路。矩阵中的 `kind='cc'` 只是补丁输入枚举。

本报告合并此前已完成的 111 件矩阵／UID 原件核查和本次新增 27 件公开 CC 核查。临时核验记录 `runs/category2_repair_20260929/moto_cpu_20261003/moto5960_r18_matrix_uid_non_author_partial_20261003.json` 的 SHA 为 `28b53bdacb07495e8ad8d3be446327f37930de028b3204763d2bf54c040e00f2`、75927B；其“CC 待补”是当时状态，原件保持不变。作者报告及作者 readback JSON 仅用于导航，结论来自实际日志、ledger、参考状态、FP 和首请求／轨迹／完整输出的交叉核对。

## 1. 原件身份与闭合状态

四个证据根均为 `runs/category2_repair_20260929/moto_cpu_20261003/<job>_evidence/`，同级保存运输 tar、receipt 和作者导航。四个 `job/status.json` 均为 finished、父 returncode 0。本次逐件重新计算 **138 件原运行文件、2400011B** 的 SHA256／字节数；全部与各自 transport manifest 相符，没有以 symlink 替代原件。归档成员（含运输 manifest）逐字节等于本地回收实物；数量不把运输 manifest 本身计为运行文件。

| job | 运行件数／字节 | archive SHA256 | transport manifest SHA256 |
| --- | --- | --- | --- |
| `moto5960-cpu-eeaa3dd27a5d`，noop | 45／687610 | `0765a8fe269f1aa61b81b577fabba8183290018a189144972ef70048dd27ceb0` | `3877ebd1f0f953f3635bf6583db8b5a44e75707dc6d3054675fd01415fb31efa` |
| `moto5960-cpu-66515b832d45`，gold／omit | 60／1364159 | `680fc0692dcb4daab251c223eee6e6d3f38b5badf480db73146e7b72ad390cd8` | `34d5839117a5a00ceb957c7a93836b60baadec80c8448ecc73596133c6d8aa8c` |
| `moto5960-uid-a680fa8321a6` | 6／94883 | `826155c27f9989fe4844d7e76ade9fc7217527a52ad9c7ac46d1e1512e49bf28` | `d39163b13c21f5186dbf8141fd01add2afb27220ad6cb35d58500526596b3763` |
| `moto5960-actor-668cd16294ae` | 27／253359 | `d773fb2366d3ccd255924611606778e9e5af5d39ca148642041a8ebc4396f28c` | `31d46a7f98ceef94149b0b34462f696b781033afc7703b791d79ee2edca04913` |

公开 CC 归档 30168B、运输 manifest 4354B。其 job 最终退出与 CC／harness 最终退出均为 0，没有把 SSH 包装状态当成项目成功。本文未读取其它在途作业。

## 2. 三臂和开发补查使用同一固定供应条件

固定 release 为 `cat2-cpu-r2e093-swe40-moto-offline-20261003-v1`，manifest `a84bdc339618e010440df3728c982b2d1d141b1f8295f69761984386ee3a512e`；本地源 `runs/category2_repair_20260929/releases_20261003/r2e_093_swe40_moto_offline_v1/repo`。本次沿用已完成的 R18 来源／工具静态核查，不重做整份发布或题级测试语义审查。

两个矩阵 job 的 `output/runtime_inputs.json` **逐字节相同**：18013B、SHA `67ebfc34422aeb9b2e3fb64e4841adf8dc238f183ddfc5b20a4907e4c00e7309`；实际 `consumer_before` 字段与固定工具 expected 对应，包括 public、ENV、grading、registry、材料、参考、完整命令、脚本和预算。可合成同条件三臂，无须重跑 noop。

| 身份 | 原件核得的固定值 |
| --- | --- |
| base | `d1e3f50756fdaaea498e8e47d5dcd56686e6ecdf` |
| public bundle | `sha256:a09554119b86752f15f8b2fa12eb31a559e92dc28b3334565e8b94ae50862336` |
| ENV | `sha256:508c321ed4834474fcdf780e3411bf26aff718a2bde916f64fbf4e61e54f8c19` |
| grading bundle | `sha256:7368a4e18b0d4b6f3605e3e1ff913e4e74b650f01c75cf7ca5530e1624e02292` |
| revision／registry | `moto5960-gsi-scan-keys-only-v1`／`sha256:149b3cd74abc6c3293f9ef01527a15c621fa0f6ae7bf0ac4f36188e976c4fc7d` |
| materials identity | `sha256:0fb164e025a6f9ef9298b7edcb0a013ac2260dad1fcbab71c80e5d66f592f8cc` |
| effective test patch | `sha256:b9a656bde376f6fefa3dd33b16dad74704b50213795b3c52dfcecfa3c57c296e` |
| scripts digest | `sha256:3beee38304a678da9ac936da1975bdd3405997bc83fa3e8b6140e3755085b79e` |
| 5960 source ConfigID | `sha256:c67dbd356fcaa937ebff4b3fe0d78e4ea78211888233a4e5f07da95eddfe079d` |
| source manifest | `sha256:4b71766331736b51bd74bb86cdb5e4e21040a7816e01fbb5d914526d33ef8944` |
| 实际 registered COPY＋ENV ConfigID | `sha256:4bafbb6965ff41c0f6eb50a73f831e7b62c41b5beda6ffad957fbc926c2359ac` |

实际 image inspect 的 source 13 层与 derived 14 层满足前 13 层逐项相同，derived 具备 `PIP_NO_INDEX=1`、`PIP_FIND_LINKS=/opt/rh2/build-wheels`。这次使用 5960 自己的 source 身份，没有借用 6408。三件 wheel 的 COPY／离线 ENV 供应沿已核固定 R18；本次安装输出实际使用该目录。public source face 仍保留原 tag，执行通过既定 exact image override 使用上述本地 ConfigID，不扩公共契约。

矩阵仍走原 `prepare`、`export-gold`、`run`，实际 CLI 使用上述 derived ID／recipe。预算保持 candidate 900、grading 1800、cleanup 120、pull 1800 秒；原 setup／apply／test 分别 300／120／1800 秒。UID 和公开 CC 绑定到闭合 gold／omit job 的 prepared summary，SHA `190b824649b60a5494b2710ecb20324566dc8af1b5c05b372b020d3630c1d825`，没有使用旧 R13 prepared 条件。矩阵工具 manifest `58e4b113ef1b98c3f5ce3df56cb7a654b9c2f4d425bd5f6b65e8c21eb49457d0`；UID 工具 manifest `7761a5da501bdc76aaf804cc6a05ac9f3b0c1e0e4193f9248670d98c0cd41560`；公开 CC 工具 manifest `8df46bb3a71d05288c8b50642c6661f6c606f2f22fdaaf7677903238a3a62f9c`。

## 3. 实际评分、完整 pytest 和逐参考结果

三臂实际日志均完整包含 `+ make init` 和原 `+ pytest -n0 -rA tests/test_dynamodb/test_dynamodb.py`；安装／测试起止、RC 标记唯一、段落完整，没有截尾、跳过安装或以失败安装继续构造成功。每臂 `stage_error=null`，report 为正常 resolved／unresolved、failure_category 为 null／tests_failed、reward 为 0／1；没有把 failed_to_grade 或 null reward 当普通负样本。

| 控制 | raw／outcome | make init RC／秒 | pytest RC／秒 | F2P／P2P 实际结果 |
| --- | --- | --- | --- | --- |
| noop | 0／unresolved，tests_failed | 0／10.346 | 1／28.048 | 3F 全失败；155P 全通过 |
| gold | 1／resolved，null | 0／10.793 | 0／26.479 | 3F 全通过；155P 全通过 |
| omit_keys_only | 0／unresolved，tests_failed | 0／9.892 | 1／26.292 | 旧 2F 通过，新增 1F 失败；155P 全通过 |

三次候选 wrapper exec RC 和三次 CLI RC 都为 0。noop／omit 的 **pytest 1** 表示真实断言失败，wrapper 0 表示日志和评分流程完整闭合，两者没有混同。实际 grading log SHA／字节分别为 noop `7c2e01e52222944efcde8375ededc967e6f71529074272ce82c7b9009b7499ad`／67532B，gold `2a41f64b9fa1d37282b669d2cb3ebdbc5d2856585bbb8748a8589edc0fd19b06`／55688B，omit `0b5f5bb96bb3e122d0f510e580ab07115f7c293ed10e341af38aa8f9ba4ee236`／57619B。

每臂 pytest 实际收集并报告 **159 个完整参数 nodeid**。原 SWE parser 用空格拆分 summary 行，以下两个既有参数实例合并成一个 parser key，故正式参考为 158 唯一 key（3F＋155P）：

- `test_set_attribute_is_dropped_if_empty_after_update_expression[use attribute name]`：三臂均 PASSED。
- `test_set_attribute_is_dropped_if_empty_after_update_expression[use expression attribute name]`：三臂均 PASSED。

我逐参考将实际 summary／parser 结果与固定分区对应，不以“159 versus 158”直接判为缺项，也没有修改 parser。158 个参考集合完全对应；缺失、skip、XFAIL、测试段外解析、未知及无归属项均无。raw passed 数为 noop 156、gold 159、omit 158；合键后的 passed 数分别为 155、158、157。两参数都通过，因此合键没有遮蔽本次失败；这不证明 parser 对任意未来相冲突参数状态都有区分能力。

原两个 F 为 `test_gsi_projection_type_include`、`test_lsi_projection_type_keys_only`；新增 F 为 `test_gsi_scan_projection_keys_only_all_items`，均在 `tests/test_dynamodb/test_dynamodb.py`。omit 的真实 trace 指向该文件 **4754 行**：Count／Items 数量为 2 的前置断言已通过，随后逐项集合比较失败。实际第一项仍为 `{'id': 'row-a', 'gsi_id': 'index-a', 'payload': 'alpha'}`，第二项仍含 `payload: 'beta'`，预期只有 `id`／`gsi_id`。它漏掉 KEYS_ONLY scan 的完整投影，失败准确来自新断言；其它两个 F 和全部 P 保持通过。没有把环境缺件、测试未收集或 reward 文件名当作此结论。

## 4. 候选投影、trusted setup、保护和两层清理

三臂候选 sanitize 都核得 base HEAD 不变、历史 7347 条前后相同、删 54 refs／剩 184、remotes／reflog／unreachable 为 0；apply 为 agent／54321。noop 没有 entry；gold 和 omit 均为单一 `moto/dynamodb/models/table.py` 常规 100644 modify，没有 tests／conftest／评分脚本 entry、ignored path 或 unsupported shape。对公开 base 严格逐 hunk 的标准库内存 apply 结果分别等于实际 FP entry 内容，并独立核 canonical FP digest。

| 控制 | 原输入 patch SHA256／字节 | 实际 FrozenPatch digest |
| --- | --- | --- |
| noop | 无 patch | `sha256:72ba65bc3f39e4eb2244bf47cfbb917895f735f03fbf9bde72246dabfba9742e` |
| gold | `df2af6b800578dc24b6ef33c396677683d766702734f44d506248354147b7af9`／593 | `sha256:a7438a6041ab1c4050faf43a54f25adca90770888bb220e7899c25921b04c1c7` |
| omit_keys_only | `5ddf1b01fdf43ecf0bc1a18e6d20908ff20ae70737d01ea00324f3a52fb1c734`／712 | `sha256:9c3690a66b40ce87c343b263890bb7d85cf64db75d6613a2883d57325a6d02d3` |

三臂 baseline canonical digest 同为 `sha256:aa86897423c3db376fa681fec311742d54e61f3e9674c20024dfb613abcb2f6c`，public／实际 runtime 相同；baseline 中 ENV 为 None 是既有形状，不替它补值。gold 内容 39690B／SHA `68bca68efb75b08b768b4856326771cb2ee970c1d3ccf2533266fef4c3459007`；omit 内容 39818B／SHA `97ddb27e24c94a965d223b0b744de1399a2b66039d520128d237a74f57472816`。

每臂 trusted setup 实际 restored=1、apply RC=0、expected/test files=1、absent=0、irregular 空、setup OK=1；控制面保护 expected/protected files=1、protected dirs=3、无缺失／不规则项、protect OK=1。实际 grading prerequisite 用户 54322、HOME `/home/rh2grader`，固定离线 wheel 可读 hash 检查返回 `RH2_MOTO_FIXED_OFFLINE_PREREQUISITE_OK=1`／RC0；脚本 SHA `sha256:02dbe5bd09606ecf644bed6cd187f8f601a5debf7b1b91dd6905f81cd0c163e4`。三臂 `runner_integrity_changed=false`。

每个候选的清理记录 `removed=true`、`rm:ok`。逐次 CLI footer rows=1、halted／aborted 为空，manager created_total=removed_total=1、`containers_open=[]`、`supply_open=[]`、cleanup_failures=[]、regrade=0，最后 exit_code=0／reason=ok。每臂自有标签容器／网络查询分别 RC0、stdout 和 stderr 都空。没有只检查候选而漏 manager，也没有把查询失败当零残留。

矩阵依据固定 profile／消费配置的 2CPU、4GiB、PID512、shm64MiB 等条件执行；ledger 的诊断 `resource_facts=null`、`env_qualification` 缺省，没有 typed 环境资格回执，故本文不捏造每臂独立 HostConfig 或训练准入。矩阵实际 `mem_peak_mb` 值为 851.582／852.086／853.652；新 UID 与真实 CC 的实际 inspect／cgroup 证据见下文，不能把它们复制成三个 grader 容器各自的实测。

## 5. 新宿主真实 UID54321 原公开安装

`moto5960-uid-a680fa8321a6` 的 6 件原件中保存完整 13 次 Docker 调用、argv、stdout／stderr／RC。13 次全部 RC0，生产 sanitize／trusted init 及原 BASH_ENV 激活实际通过，HEAD／历史和工作区身份与上文一致。第 7 次以 **用户 54321**、HOME `/home/agent`、BASH_ENV `/rh2/bash_env` 执行原 `cd /testbed && PYTHONDONTWRITEBYTECODE=1 make init`，没有注入私有测试或预装替代原命令。

安装实际 stdout 20740B／SHA `61d51a6696a5609cb787f7ab208f8284517a4f49258221a6d7e1a84adf81ad7f`，stderr 426B／SHA `ed35e0e19a25feaf7ed5c8ae560c1768d041c025c8d733fb28ad3ece924d8f7f`；我读了完整输出，不只采纳 owner 的 install=true。pip 因 normal site-packages 不可写而使用用户安装，离线 find-links 指向固定 wheel 目录，editable build／两次 Moto 安装成功；stderr 只有两次 `moto_server` 用户 bin 不在 PATH 的 warning，命令真实 RC0。

随后的实际 identity JSON 核得 UID／GID54321、cwd `/testbed`、HOME `/home/agent`、Python／sys.prefix 为 testbed，Moto 为 `/testbed/moto/__init__.py`，目标模块为 `/testbed/moto/dynamodb/models/__init__.py`。模块 SHA `fba195aa3985edf3616237b965aefae6ea6845c9d2591f3d814d094dd70882fc` 对应原公开 base 的 29677B；boto3／botocore 均 1.35.9。独立实际 HostConfig 核得 CPU ConfigID `4baf…2359ac`、NanoCpus=2000000000、Memory=4294967296、PidsLimit=512、ShmSize=67108864、NetworkMode=none。

第 10 次核自有 label；第 11 次删除 RC0；最后容器／网络两次自有查询都 RC0、stdout／stderr 空。UID job 父0且已闭合。它实际解决“开发 UID 能否读取离线 wheel 并完成原安装”的补查，不能只从 grader 的安装0推定，也不是 CC 或模型。

## 6. 真实 CC 首请求、六条公开命令及完整输出

公开 CC job 的 `output/stub/requests/messages_000.json` 为 **17898B／SHA `39ed07590708749e7ad075e92b68e3ec8481730a163551a0a03e5c51773819d7`**。实际首 user message 含一次完整 prepared public prompt，UTF-8 SHA 为 `d68c2e86f170a85d8d1207f198de2fd8f198b59ad813005b815706bc33b1c669`；逐字与上述 R18 prepared `prompts.jsonl` 对应。原 prompt 仍为公开功能题面；附加内容是 CC 日期／环境上下文，没有私有新增断言、对照 patch、金标或答案。不能从 reviewer 已接触私有材料推导 solver request 也包含私有材料。

命令清单 `commands_5960.json` SHA `0101854eef9577ef38080a99ff08ef566e6a201d7d853141af00e2e3e80f93a6`／4239B。独立从 B3 原 `public_read.md` 的 bash fenced block 逐字提取前五条，原文件 22770B／SHA `c2ac93029588118e7ba49745674a38096cbd9702d5b5c9f6b431e887662023dc`：C1／C2／C3a／b／c 长度为 277／2050／266／150／181B，全部与实际六个 Bash 中的原 command 字节相同。INSTALL 为原公开开发说明的 `cd /testbed\nmake init\n`，22B；可选 C4 syntax／build 未执行，不作为缺失必需操作。来源 binding `public_reader_command_binding_r18_v1.json` 为既有静态记录，其 not_executed 保留为当时事实。

实际 `trajectory.jsonl` 32581B／SHA `fe3f642cdef2ae8aff43b39fdff097f26d2ef88b1d90b4f9adfbe1c6c9818660`，完整 **68 行**：12 system、42 stream_event、7 assistant、6 user、1 result。独立解析六次 Bash tool_use／六次 tool_result，逐个核 ID、原 command 的完整包装、timeout 和 RC marker：INSTALL 原调用300秒／工具330000ms，其它原调用240秒／工具270000ms；均将完整 stdout＋stderr 留到 `.full`，内层 RC 单独保存并返 `RH2DC_END`。包装 `exit 0` 不覆盖内层 C2 的 RC1。七次实际 API request 的 message 数为 1／3／5／7／9／11／13；除 cache_control 缓存位置改变外，初始文本保持相同，先前 tool_use 和 tool_result 内容／ID 全部与真实轨迹对应，没有仅按桩计划认定执行。

| 实际命令 | 内层 RC | 完整 capture 字节／SHA256 | 独立读得的实际行为 |
| --- | --- | --- | --- |
| INSTALL | 0 | 21166／`d8bd3a91e66589560bb90b2f31e7850c8acc15ecd7c8c619adf02461f9d3d10b` | 实际原 make init、offline find-links、editable build 和 Moto 安装成功；只有用户 bin PATH warning |
| C1 | 0 | 161／`cf969958f2ac09abbcc959400a386540fad6cb47ea31e86476dd9ec7a6384588` | `/opt/miniconda3/envs/testbed/bin/python`、Python3.12.4、Moto `/testbed/moto/__init__.py`、SDK1.35.9／1.35.9 |
| C2 | 1 | 395／`78304e49dcdf4958a5e993e7a20d7909a3941fd597daa310f317219112215d44` | 两种投影完整输出后，最后第46行目标 AssertionError |
| C3a | 0 | 1382／`70b25d9a24211afe9ffa50fc86270423191a3229ea2914f6e235e6f4b610330b` | 15 passed、143 deselected |
| C3b | 0 | 2073／`580bbbf8f8e5fb14bfb830b73b2a5ca9bc31a243a8864f77857f8c5530b83274` | 1 passed |
| C3c | 0 | 1632／`b262150c2fcbfd28f598110268e98cb077a905b5248f65e5991ba11ed415f8e0` | 2 passed、25 deselected |

六件完整 capture 都与实际 attempt 的 SHA／output_bytes 相同，output_truncated_to=null；我读了所有内容。`commands_result.pytest=null` 是旧摘要对本组 `-q` 形状的未填字段，实际 capture 有上表完整 pytest 汇总，不当测试缺失；公开 `-q` 输出没有逐 node verbose census，正式 158 参考的逐项证据来自矩阵，不借公开子集 totals 代替。

C2 先打印 INCLUDE **3 项**，每项键 `['attr1','attr2','id']`，随后打印 KEYS_ONLY **6 项**，每项键 `['attr1','id','seq']`。公开脚本期望分别为 id／attr2 和 id／seq，两个 `check_projection` 都实际执行，最后 `assert all(results)` 在 `<stdin>` 第46行抛 `AssertionError: GSI scan returned attributes outside the configured projection`。这是原公开 bug 的完整两模式观察；不是 import／SDK／安装失败，也没有因第一模式抛异常而遮蔽第二模式。非零 RC 在此是预期的公开复现结果。

CC 版本原件为 2.1.205；launch harness log stdout 32581B、stderr0B、log_complete=true，stream_error=null；实际 exec inspect Running=false、ExitCode0。末行 result subtype=success、is_error=false、num_turns7、stop_reason=end_turn，实际完成六条操作；stub 七次 message request 与 message_start 数对应。这里的 `slime-actor` 和 usage/cost 是确定性 API 桩的返回形状，不是自主模型推理证明；model_attempts=0 保留。

## 7. 真实 CC 身份、隔离、旧 false 和 finally

actual `prelaunch.json` SHA `17f5397d9334ff2e82886849ba3b5b588b70cf6e9f7c11b5ddc18fa8d735b113`／2300B，`activation_check.json` SHA `af1e0f016efac8a8da0d1b89eeb4928aad99df507c1546a839ad02886ae9d1e8`／506B。生产 sanitize/init／原 activation 都实际成功：UID／GID54321、WORKDIR owner54321／可写、effective/permitted caps0、NNP1；激活 python／sys.prefix 为 testbed、CONDA_DEFAULT_ENV=testbed、VIRTUAL_ENV 空；BASH_ENV file root-owned0644／目录0755、agent 可读而写拒绝。

实际 inspect 为同一 CPU4baf ConfigID、2CPU／4GiB／PID512／shm64MiB，cgroup CPU200000/100000、memory4294967296、PIDs512／swap0；tmp1GiB、home256MiB、无 bind／mount，非 privileged、no-new-privileges。CC 使用单次自有网络／relay，relay 可达，外部 DNS、四个禁止目标、直接 upstream 和 `/root` 读取均 denied；UID-only job 是 network none，两种检查不能混称同一网络拓扑。CC prelaunch ok=true、violations=[]。

两个既有 `checks` **false 原值保持**，不能称“所有检查 true”：

- `interpreter_in_tool_result=false`：原 acceptance evaluator 搜索 tool_result 中 `RH2_SYS_EXECUTABLE=<prefix>/` marker。本清单返回的是六个 RC marker，C1 的完整原输出另取回，未运行该 marker 形状；false 不证明解释器错误。实际 C1 capture＋activation＋独立 UID 已证明本次解释器／模块来源。
- `bashenv_denied_for_agent=false`：原 evaluator 搜索 tool_result 中 `RH2_BASHENV_WRITE=DENIED`。原公开清单没有写 BASH_ENV 的 marker 命令；此条件在 tool_result 中未被直接证明。实际生产 prelaunch 同 UID 核得 `ACTIVATION_WRITE=DENIED`、`ACTIVATION_STAT=0:644` 和 activation 成功，支持本次权限／激活范围，但不把 false 改成 true 或声称该旧 marker 测试已跑。

`post_run_facts_root.txt` 是保留的旧文件名。新薄工具将带 Git 的整段事实命令改为 agent 执行，实际 attempt 记录 `post_run_fact_actual_role=agent_uid_54321`，所以这里不是 root Git／读权限证明。完整文件核得 `.harness`、`/tmp/.run.sh`、`/tmp/.run.done` absent、git status lines0；newer files107含普通 import／pytest cache，开发操作合法写工作区，不能要求零写入。该时点 agent processes4，随后可信清理记录 `RH2_AGENT_PROCS_AFTER=0`，不静默忽略这一过程。

实际 attempt 的 finally 收口为 container_rm=0、stub_rc=0、network_failures=[]、relay_failures=[]、labeled_containers_left=[]、labeled_networks_left=[]、residual_after_force=[]。原 DevRunner finally 调用完整 container／network／relay／stub 清理；R18原消费者二次容器与网络查询 RC 非0会写 `<container_query_failed>`／`<network_query_failed>`，本次最终列表为空，不能由查询失败伪装而来。此公开 CC 工具没有另存每次 Docker 调用的完整 argv/stdout/stderr census；结论依据原固定清理实现、实际 attempt 过程／收口、父与 harness0及空残留，不能声称已得到不存在的逐调用清单。

## 8. 验收边界与历史保全

本次针对已核 R18 身份形成三臂评分、开发 UID 安装、实际公开 CC 消费／命令／失败语义／清理的证据闭环，无须因两个不适用旧 marker 或已完整取得的原件再机械重跑。此前 author matrix report 的 UID“尚未闭合”和 public summary 的 pending independent review／formal_cpu_accepted=false，都是在报告形成前的原始状态，已保留；本报告提供新的独立验收结论，不回写原件。

旧 R13 source 缺 setuptools／make init2 与旧 raw 观察保持原记录；本次 offline 供应下的新安装0不抹去旧阻断。旧 R5 原材料 omit 得分仍未知，不能用本次修订 R18 的 raw0 回填。材料中的 `constructed_negative_unrun` 是固定角色描述；本次该控制已实际运行，两者要按各自时间／对象理解。

本次没有自主模型求解，没有把真实 CC 开发命令导出为 FrozenPatch，没有 actor-to-grader regrade，没有 typed trajectory／环境资格或训练消费验收；矩阵 FP 是独立对照补丁投影。没有更改 public/base、参考、test patch、评分器、预算、旧 actor／FP／raw identity；没有新增审批门槛。以上普通 CPU 诊断验收仅适用本文固定 R18 和 CPU4baf 供应条件，不推广到旧 source、其它题目或其它宿主镜像。
