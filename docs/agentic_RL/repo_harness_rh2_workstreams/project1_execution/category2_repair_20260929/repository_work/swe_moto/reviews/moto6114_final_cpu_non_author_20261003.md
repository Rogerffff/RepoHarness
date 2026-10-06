# Moto6114 最终 CPU 原件非作者窄核

2026-10-03。审查者：Codex 非作者 subagent。范围为 v4 作业 `moto6114-cpu-0661259fc3d1`、新宿主 UID 作业 `moto6114-uid-83565d38db45` 的本地运输原件及公开开发说明；复用已经独立核过的 v3 noop，不重读其整套 43 件，不重审断言语义。本审查者已读私有有效测试、gold 和 wrong_first 对照，**不是公开盲 solver**。本轮只运行标准库的文件／JSON／哈希读回，不执行远端、项目、SDK、测试或 Docker；只新增本报告，不修改题主材料、旧报告或运行原件。

**最终结论：本题既定 CPU 准入条件已满足，未发现必须先修改的材料、消费者或执行问题。** 合并既有 noop 与本次 gold／wrong_first 的 reward 为 0／1／0：gold 全部 35 项通过；wrong_first 由新增对象身份断言实际拒绝，原 34 P2P 保持通过。新宿主实际 UID／激活／源码导入／SDK 一致性和清理补查也已通过，关闭历史公开开发路径复用的环境缺项。可完成本题 CPU 准入记录并固定下一步真实 probe 请求；**本报告不宣称本次 fresh CC、基座模型 actor、probe 或 a2g 已通过，也不授予训练资格。**

CLI 中 wrong_first 的 `candidate.kind='cc'` 是 `patch:` 输入的既有枚举值，实际命令只输入既定补丁；本矩阵没有启动真实 CC、模型或 solver。两臂的冻结补丁也仅是 CLI staging 的产物，不能记作真实 actor→grader（a2g）通过。构造的 `actor_spec` 同样只提供派生镜像绑定读回。

## 原件完整性与版本

原件根目录为 `runs/category2_repair_20260929/moto_cpu_20261003/moto6114-cpu-0661259fc3d1_evidence/`，以下本次路径均相对此目录。题主 [读回导航](moto6114_gold_wrong_first_owner_readback_20261003.json) SHA `e2cb407c4fa9e1fa066cab37239be159689651118dcc5b16bb4daf0faea3c463` 仅用于定位；结论来自命令／退出、账本、完整 eval log、sidecar、冻结／投影和清理原件，未直接接受其布尔结论。

- `transport_manifest.json` SHA `cd1ea021c6d2c38600191bb503f4b38669d507ae2ad0d22d9e7762ec15095f2a`；所列 **59 件**原件的 SHA 与字节数已逐件独立重算，全部匹配。
- `job/status.json` 为 finished、returncode=0；实际入口是固定 R7 PYTHONPATH 下的 v4 `matrix.py --execute --controls gold wrong_first`，显式清除共享 image overlay 两个环境变量。job stderr 为空，stdout 中 verify_release、image_inspect、prepare、export_gold、run_gold、run_wrong_first 均 rc0。本 job 只有两臂，不能改称同一 job 完成三臂。
- R7 外部 manifest SHA `f9dfcd16c9c88e4f514512e61781856b7d6f1a71a20b64cd1843d20546c5009b`；原件 `output/verify_release.stdout` 记录检查 905 文件。v4 manifest SHA `0a3968d13043a3baab1f40ae150da54cae3577e7501844964635f2a7134e479c`、matrix SHA `51e94a18a5d653dce1c081d091027a9762713b211a49e667713676b554c75691`，本地重算未变。expected_runtime／image_recipe_binding SHA 分别为 `826c008810cbdb753b476a22cda58dc2b5133762369ff30e264eeeb530310a2f`／`553e1aeaa984ea899518d12688462be0a35d815b4d94abae13a7af0e301d990f`，与已审 v4 相同。
- `output/consumer_readback_before_checks.json` 的全部 13 个消费字段与 expected 对应字段精确相同；含 public／grading／environment、base、完整命令、1／34 参考、revision context 及五份生成脚本 SHA。expected 内描述性的 `status` 和 `original_test_patch_sha256` 不属于该 13 字段输出，未误称整个 JSON 逐字相同；原始补丁 SHA 另由实际 private host view 内原始补丁文本独立重算确认。

| 绑定 | 实际消费原件 |
| --- | --- |
| 任务与基线 | `swe_gym_lite::getmoto__moto-6114`；HEAD `f01709f9ba656e7cf4399bcd1a0a07fd134b0aec`。 |
| 公开／私有／环境 digest | `sha256:6c8f45da003f8e8d1e065d1801afa4659c43cbb212e319a5d07a84922af5f0f2`／`sha256:e33ad739c3f8f9ebe4ba1210e7527b100fa6ff257131cad9f1f0a23653b01f3d`／`sha256:a791b087e4475a2a4f7d70183e7031a711e077091206e7826a3203cd32189f41`。 |
| 私有修订 | `moto6114-cluster-identity-v1`；registry SHA `27e1b01dfec9aa2284e79fec753f70b62f6bd45462346483484f98785a59ae22`；材料身份 `sha256:44bef90dc4148f74ad2b2e26e2c9d09e09b20993ae8c734c67d8df83e92c6309`。原始／有效测试补丁 SHA 重算为 `32beadd88d5189dcab69b796980a93c464cb7b6f9d16bc8329d5da3e80571b61`／`fe211059864c661a557758f5c5ed4106016c767cbe98eaef4718733008a87d5f`。 |
| 原安装／完整命令 | `make init`；`pytest -n0 -rA tests/test_rds/test_rds_clusters.py`，保留原 1 F2P／34 P2P，非仅 eval_cmd 前缀。 |
| 实际派生镜像 | CLI `--derived-image`、账本及 baseline／frozen runtime digest 都为 `sha256:1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5`；recipe `moto6114_install_wave1_copy_only_20261003`。实际 inspect 来源 manifest 为 `sha256:cb35f7e131f8e46c8a6865e8fb618c09032ce5ee27f1122f79010a7cfae8ef9a`，base ID 为 `sha256:fefec492f58ed0f8385a7e72234d296bd84d295031ce7e019f63fc33973ec249`；linux／amd64，派生保留 13 个来源层并只多 1 层，离线 wheel 环境不变。 |
| 预算与限额 | setup／apply／test=300／120／1800 秒；candidate／whole grading／cleanup／image=900／1800／120／1800 秒。实际 grader policy 为 2 CPU、4 GiB、512 PIDs、64 MiB shm、网络 deny_all、UID 54322；candidate patch apply_user 为 agent／54321。没有提高预算或替换评分器。 |

五份消费脚本 SHA 与已核 expected 精确相同：eval `b3034e25d32d24fd0e409b78b3fe3a3d90ef06f24e25f106996b60b0a786769c`；trusted_setup `b268429ec5e9a4b144f039a49d697c75f4fd23aabde8d7915971dc74419d3ef3`；candidate_test `5600b6eada3c6bedb6a0c628040c458f86289a21720a1c52236560808fbfee1e`；candidate_install `866c2e11adc8e8d47da77fbd59cca78568636bdf3ace4a15ab65d19ac77f20cc`；candidate_test_after_install `87c0c3a522d33c8e559d2956e975aa6650251a350da1684536ffd8146b392c8e`。

## 两臂实际行为与完整执行

| 原件事实 | gold | wrong_first |
| --- | --- | --- |
| 实际候选 SHA | `bfae681e1044acffe64d7d65c1615b5545f4b62b2625961b7a6fe7d0ad591bbc`，实际 export-gold 和 staging 文件相同。 | `5c042121e4bf56693c71f418c139b628d108b0c1fcd67bc0af48201e471c6451`，实际 staging 文件相同。 |
| staging／投影 | stage_error=null，git_apply；冻结恰 1 个路径 `moto/rds/models.py`，projection 仅此路径，projectable、reason_codes 空、私有路径集未改。 | 相同执行性质；无测试／conftest／fixture 改动。 |
| 原安装段 | eval log `:375` 执行 make init；`:375`–`:534` 两轮 editable 构建、metadata、wheel、卸载和安装完整结束。 | eval log `:374` 执行 make init；`:374`–`:533` 同样完整结束。 |
| 安装成功依据 | 两轮各有 build dependencies／metadata／editable build done、Successfully built、uninstalled 和 installed moto；段内无实际安装 error 或失败标记。install_rc=0、install_skipped=false、log_partial=false。 | 同左；不能只凭末条 rc 宣称安装通过，本轮已核完整段中的完成／失败事件。 |
| 原测试段 | `:548` 完整命令；collection 35；`:578` 起的 35 条 short summary 全 PASSED，与原参考集合逐项相等，无额外项。`:613` 为 `35 passed, 166 warnings`；test_rc=0。 | `:547` 完整命令；collection 35；short summary 34 PASSED／1 FAILED 与原 34 P2P／1 F2P 精确对应，无额外项。`:650` 为 `1 failed, 34 passed, 165 warnings`；test_rc=1。 |
| parser／参考 | parsed=35、outside_segment=0、apply_ok=true；各分区 missing／skipped／unaccounted 均空。1 F2P 与 34 P2P 全成功。 | 相同完整解析；仅 F2P failure，34 P2P success；missing／skipped／unaccounted 均空。 |
| 评分 | reward=1，resolved，failure_category=null，infra_failure_detail=null。 | reward=0，unresolved，failure_category=tests_failed，infra_failure_detail=null。 |

两个测试段都有 Start／End Test Output、RH2_TEST_RC 和测试时间起止，安装也有 RC／时间起止；`candidate_segment_completed=true`、candidate_exec_exit_code=0 和 CLI rc0 代表包装及收口完成，**不把 wrong_first 的 test_rc1 改成测试通过**。实际安装依赖行中 boto3／botocore 均为 1.35.9；观测 Moto 导入路径为 `/testbed/moto/__init__.py`，runner 摘要前后相同、runner_integrity_changed=false。这些是 grader 侧原件；下节另核实际 agent UID smoke，未混作同一进程的证据。

wrong_first 的决定性证据为原 eval log `:584`–`:594`：B 集群实际 ARN 查询已返回 `clusters`，长度断言通过，随后 `test_rds_clusters.py:268` 的 `assert clusters[0]["DBClusterIdentifier"] == "cluster-id2"` 实际比较为 `'cluster-id1' == 'cluster-id2'` 并抛 AssertionError。故拒绝发生在新增身份断言，非旧数量检查、DBClusterNotFoundFault、导入或安装失败；后续 ARN 等断言因首个身份断言失败未执行，不能称它们各自已经失败。这正好补上既有 noop 只在 ARN 查找处失败、尚未到新增断言的证据边界。

两份 sidecar 的 trusted setup 原始 footer 均为 apply_rc=0、restored=1、expected／present_test_files=1、absent=0、irregular 空、setup_ok=1；control_surface expected_files=1、missing=0、protect_ok=1。candidate 与 grader 的 git sanitize 都为 verified、无 violations，HEAD 保持固定 base，remotes／reflog／unreachable 为 0。原恢复与保护集合仍是同一测试文件。

## 两层清理与 noop 复用

两臂 `output/run_*.exit.json` 都 rc0，stderr 空；stdout 最终摘要都为 rows=1、halted=null、aborted=null。各账本 candidate cleanup 为 removed=true、steps=[rm:ok]；manager_close 中 containers_open／supply_open／cleanup_failures 全空、created_total=removed_total=1，最终 exit_code=0／reason=ok。`output/residual_gold.json` 和 `output/residual_wrong_first.json` 的自有 run_id 容器／网络查询均 returncode=0 且 stdout／stderr 空；不是查询失败被当零残留。两层分别证明 candidate 删除与 manager／grader 收口，并额外核对既定归属资源为空。

noop 直接引用 [已完成 noop 与 v4 入口独立窄核](moto6114_v4_entry_and_noop_reuse_non_author_20261003.md)，报告 SHA `62bffba46ad08d282c0cd48306f24562a2eabe1decfc6f25d0912cf41a658b96`，本轮重算未变，不机械重核原 43 件。该报告已独立核固定 R7、同消费者／材料／镜像／限额及预算下的 `moto6114-cpu-ffe3a2e97334-noop`：完整安装、35 解析、1 F2P 失败、34 P2P 通过、reward0、两层清理及自有资源零残留。其 v3 外层 job 因 gold 目录冲突 rc1，后两臂零执行；本次不改变该历史事实。实际已完成 noop 可与本次独立完成的两臂组合，得到 0／1／0，而无需再次跑 noop。

## 公开开发说明的边界

[public_dev_brief.md](../tasks/getmoto__moto-6114/public_dev_brief.md) SHA `8ee4f528e81f02a45984d758804461a4d8ae6c0aa3535cfa420c04342d1f3052`，1,558 字节。新增文字仅描述 `/testbed`、固定基线、镜像已有 conda 解释器、本地 Moto 导入、通用环境核对命令、原 make init、模拟 AWS 测试凭据及以原公开 issue 为功能要求。原 `public_hints` 在文中出现一次且逐字相同，没有私有新增测试行／断言、A／B 反例、wrong_first 行为、gold 修法或评分答案。可作为中性环境说明使用。

实际本次 prepared public 对象同时与固定 R7 producer 的本题 public 及历史 prepared 本题 public **逐对象精确相同**。problem_statement SHA 重算为 `1bf351c6cac9794d802f518053cefdfb62a47e07b5ca8f1254f05a29855339c3`，public digest 为上述固定值。因此功能 statement 未改；开发说明是独立文字补充，不能说它已进入本次 CPU 作业公开 bundle，也不能由此宣称模型已理解原题面。

## 新宿主 UID 补查与历史公开路径复用

UID 原件根目录为 `runs/category2_repair_20260929/moto_cpu_20261003/moto6114-uid-83565d38db45_evidence/`。运输 manifest SHA `7b1b20ec5d4ca30d4bea02a915a70d63d27ed7250d9b776fe0b5895db7e5ccf5`，所列 **5 件**原件的 SHA／字节数独立重算全部匹配。同级 transport receipt SHA `fd430466034661dedbc71cc0a18d51c6e0e97334afb02df3be2c64480ec1c102`，记录 archive SHA `45cc4030e6d89de653513b7c692fced3161910077ee103fa881d1d40753f94c1`；本审查者核的是解包后原件及 manifest，未独立取得压缩归档字节，故 archive SHA 仅作运输来源索引。

`job/status.json` 为 finished、rc0、stderr 空；实际命令使用固定 R7 PYTHONPATH、修后 UID 工具及本次 v4 prepared summary，summary SHA 独立重算为 `44ad39c1802736c0080c93849cfefedb4ba6b01dd118f2a938b797ff803f6e3d`，与 job 参数和 UID result 一致。修后本地脚本 SHA 仍为 `da3798980fc199315b0977a49792769cd042869eab7e57d7ebc5b846af8dc2b0`；原导入错误已静态修复，本次执行实际通过该导入。依据 `output/docker_calls.json` 的 **12 次实际调用及输出**核对，未只接受 `result.status`。

| 补查项 | 实际原件及边界 |
| --- | --- |
| 生产 sanitize／init | root 运行实际固定 helper 生成脚本；sanitize 脚本文本 SHA `46c627f7924277715f0cc4bc8477d6ae91d769f887035a42a99562e81dece125`，rc0，HEAD 前后固定 base、历史数量 7454 不变、remotes／reflog／unreachable 为 0。trusted init rc0，WORKDIR_PRESENT=1、RH2_INIT_OK=1、AGENT_UID=54321。 |
| 激活与 shell 环境 | root 容器 exec 将 `/rh2/bash_env` 写入并 chmod 0644，rc0。生产 activation probe 以 UID 54321、HOME=/home/agent、BASH_ENV=/rh2/bash_env 启动子 shell；实际 command-v python、sys.executable 均为 `/opt/miniconda3/envs/testbed/bin/python`，sys.prefix 为 `/opt/miniconda3/envs/testbed`、CONDA_DEFAULT_ENV=testbed、probe_ok=1，无 violations。身份命令也实际注入相同 HOME／BASH_ENV；该 JSON 未另打印 HOME 值，未虚称该字段被直接观测。此 smoke 未执行 BASH_ENV 写拒绝攻击测试，不扩展其安全结论。 |
| 实际身份／SDK | 独立 exec `--user 54321` 的 Python 输出为 uid=gid=54321、cwd=/testbed、正确解释器和 prefix，boto3=botocore=1.35.9，rc0。result.identity 与该原始 stdout 的 JSON 精确一致。 |
| 本地源码 | Moto 导入为 `/testbed/moto/__init__.py`，RDS 导入为 `/testbed/moto/rds/models.py`；实际读取源码 SHA `a614a137f21dce20445cad98611e578b435d4f09a592ced584d887d9edb9250c`，也与本次 gold／wrong_first 两个 baseline manifest 的同一路径 content_digest 相等，未误用 gold 或负对照修改后的源码。 |
| 实际镜像／限额 | image inspect、container inspect 实际 ID 为固定 `sha256:1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5`；NanoCpus=2,000,000,000、Memory=MemorySwap=4,294,967,296、PidsLimit=512、ShmSize=67,108,864。container inspect 实际 NetworkMode=none、Privileged=false、Init=true、no-new-privileges；属于本题补查的 network-none UID 容器，不证明真实 actor 模型代理／网络通道。 |
| 自有清理 | 删除前独立 inspect 的容器 ID 与 launch 返回一致，name 为本 job 独占名称，`rh2.run_id` label 精确匹配；只执行此 name 的 rm -f，rc0。其后自有 label 容器／网络两项查询都 rc0、stdout／stderr 空，无残留或查询失败。全部 12 调用 rc0、stderr 空。 |

UID result 的 scope 明示 no CC、model、baseline export or grader；这项成功关闭的是当前宿主运行条件，不能把 result 的 `new_host_actor_identity...` 名称解释成新 CC actor 已执行。

历史三条真实 CC 公开路径的复用边界沿用 [独立复用窄核](moto6114_public_actor_reuse_non_author_20261003.md)，报告 SHA `5d81a1c39477825eef278b2cf237f5b472a6b1c0ea787c8b0c62367980eba642`，本轮重算未变：历史 identity rc0、B ARN 预期 DBClusterNotFoundFault rc1、原公开 `-k describe_db_cluster` 4 pass／31 deselected 有实际 CC 轨迹与完整 capture。此次 public／base／来源镜像／COPY-only 配方相同，物理 derived ID 不同；本次实际 UID／激活／导入／SDK 一致性和清理补查已通过，**可按既审范围复用三条公开开发路径**，无需机械重跑。不将不同 physical image 的历史记录重新绑定为本次 frozen export。

两个历史 legacy flags 仍为 false：interpreter 标志因模板只匹配 RH2_SYS_EXECUTABLE、实际命令打印 PY_CHECK 而未命中；bashenv 写拒绝标志在那三条 CC 命令中未执行／未打印，其可读不可写的证据来自历史独立 prelaunch 阶段。不能静默改 true，也不能由新 smoke 推成历史 CC tool_result 已测写拒绝。历史 devcheck 无冻结导出，未覆盖 fresh actor／公开题面自主理解／a2g。

## CPU 准入结论与保留边界

已有 [新测试材料独立审查](non_author_new_tests_review_20261003.md) 的 Moto6114 部分继续有效，本轮仅确认所审报告身份（SHA `2e15f7643ed3a309718b5b0b3a4e8549a091ebdbb84fe06d2ccff5d69edc2709`），未重新审查全题断言语义。结合固定 R7 消费者、原 prepare／export-gold／run、同材料及镜像绑定下的三臂原件、完整安装和逐参考测试、trusted footer／保护／清理、新宿主补查，以及适用范围内的历史真实 CC 公开开发证据，**本题修订的 CPU 准入证据完整，可以接续固定真实基座 probe 请求；没有需要现在先修的具体阻断项。**

本次原件 `output/result.json` 的 formal_cpu_accepted=false、actor_executed=false，以及 scope 中 model_attempts=0 都保留原字节。formal_cpu_accepted=false 是原工具在独立读回前刻意保留的状态；本报告提供其后独立 CPU 准入结论，未把历史 result 回写成 true。actor_executed=false 则仍是本次矩阵事实。历史公开开发证据与新 UID 补查的组合不等于 fresh CC、模型自主求解、完整公开题面理解、probe 成绩、真实 actor 冻结导出或 a2g 成功。下一步真实 probe 是尚未发生的工作，本报告不授予训练资格，也不扩大公共契约、评分器或审批流程。

## 关键原件定位与 SHA

| 原件（相对本次原件根） | SHA-256／字节数 |
| --- | --- |
| `output/gold/ledger.jsonl` | `ef6aaf096ece7c1e6708929188d77ae0d663c0628a48358b644e90c6e7a66148`／12,484。 |
| `output/gold/eval_logs/evallog_replay-moto6114-cpu-0661_b9d6e404.eval.log` | `54ff2659f8b70a012b4ecaa9f4582a0c75d857bac8adaf45ea1dcf230df8efb2`／41,407，620 行。 |
| `output/gold/eval_logs/evallog_replay-moto6114-cpu-0661_b9d6e404.diagnostics.json` | `1d0852e3c543b9c94f0519b97c8f2d28eb694267fd09a44f046d62c99838c97c`／11,053。 |
| `output/wrong_first/ledger.jsonl` | `3ecc6507a0e955f652e1c980efd3cbe2be0b2945d5061191bf357f6179770d5f`／12,552。 |
| `output/wrong_first/eval_logs/evallog_replay-moto6114-cpu-0661_3368ab7e.eval.log` | `1c1d0eccc0a59c42499d50ac64074fff2d20f5a84f9e59d6f1c5afc708e3065f`／42,764，657 行。 |
| `output/wrong_first/eval_logs/evallog_replay-moto6114-cpu-0661_3368ab7e.diagnostics.json` | `7dd7ffd32277cf642ce6a773a3860f8b520a5c3acc1e69d80c8f40c6edbc7097`／11,058。 |
| `output/residual_gold.json` 与 `output/residual_wrong_first.json` | 均为 `63d5bbc4aad1d186d01425a682037021f16d06701db9e33db4017047f5f8226f`／159。 |

冻结文件物理 SHA 分别为 `b14188e004cd9d4d1efbd913d0a85d0643676be80a2968e88e8e5efdab70119d`／`c3c3b4d1862f8a3289417516ceb45c93aeca86301037431d800969f2e19c31b3`；账本绑定的规范化 frozen digest 分别为 `sha256:357ac2239b4044fe4c4eefe9e19b3a8a50cfed22edea134afc310522c4d72a67`／`sha256:9686c4a608c70076acb98c3b68fb245a32bd676318ff63aa8d721c77de9ce2e3`，两者不是同一种文件摘要，未混用。

UID 关键原件（相对 UID 原件根）：`output/docker_calls.json` SHA `0e9023e0c5d4990b3652ebb8c729d6ff1579777afe5507f82760880a0b2ae022`／34,215 字节；`output/result.json` SHA `9db172c5925b78edeafa4f68b45e3ca4ec0a9a703b14fa41ba7fc04c6001266d`／2,798 字节；`job/status.json` SHA `a2b9b3079707f56ed7f637dad55077a9894190bf2e4e13e4139511f33c3a719f`／1,038 字节。
