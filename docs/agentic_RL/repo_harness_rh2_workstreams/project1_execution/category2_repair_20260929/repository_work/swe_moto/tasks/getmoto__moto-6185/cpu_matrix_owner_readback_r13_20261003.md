# Moto6185 R13 全22对照作者验收读回

2026-10-03。固定22臂全部完成，作者原件读回完成；最终非作者报告尚未写入。此处记录普通题目质量／基座诊断证据，不授训练、留出集或typed actor资格。运行原件、发布输入和历史独立报告保留原字节。

实际材料固定R13 `cat2-cpu-r2e089092-swe27-pandas-moto-20261003-v1`，manifest `3fad18daff8db219294e10cbf08d4424d68cf7000d008bb983cba4bdc427b641`；修订 `moto6185-nested-s-v3`，有效补丁 `fc65a52722f47a6d458465d2e4a529caa057c2f238453d1659efdfef42bc332d`。原公开题面及1F／34P参考不改；source config `47443b04543c5fa25c85bb4e86c871f1f98ea0df9e254b2ca8fac9f9bdb19325`，CPU COPY-only实际image `79d39d611186289b10956c2f845af1272218a1f4cf8fc00382c7c6ab4eced35d`。六组runtime_inputs逐字节相同，脚本／预算／参考绑定由原件及读回逐组核对。

原安装 `make init`，测试 `pytest -n0 -rA tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py`；安装300／apply120／测试1800／candidate900／whole1800／cleanup120秒。实际资源2CPU／4GiB／PID512／shm64MiB，评分network none；runtime_cpu_v2、矩阵v2正常评分白名单。工具静态审查不能替代下面的实际结果。

| 控制（原矩阵顺序） | 既定角色 | 原分 | 安装rc／秒 | 测试rc／秒 | 实际job |
| --- | --- | ---: | --- | --- | --- |
| noop | noop | 0 | 0／12.131 | 1／7.156 | `moto6185-cpu-34561d16159e` |
| gold | gold_known_incomplete | 0 | 0／10.263 | 1／6.544 | `moto6185-cpu-d3ebfdc58aa8` |
| ctx | positive | 1 | 0／11.336 | 0／6.450 | `moto6185-cpu-d3ebfdc58aa8` |
| ctx_list | alternative_compatibility | 1 | 0／10.541 | 0／6.286 | `moto6185-cpu-d3ebfdc58aa8` |
| depth2 | known_wrong | 0 | 0／10.862 | 1／6.341 | `moto6185-cpu-171d1b6897be` |
| list_as_names | known_wrong | 0 | 0／11.404 | 1／5.571 | `moto6185-cpu-171d1b6897be` |
| null_only | known_wrong | 0 | 0／11.739 | 1／6.716 | `moto6185-cpu-171d1b6897be` |
| parity | positive | 1 | 0／11.046 | 0／5.980 | `moto6185-cpu-d3ebfdc58aa8` |
| rootkey | known_wrong | 0 | 0／13.837 | 1／7.587 | `moto6185-cpu-171d1b6897be` |
| shape | known_wrong | 0 | 0／11.077 | 1／6.381 | `moto6185-cpu-171d1b6897be` |
| siblings | known_wrong | 0 | 0／11.334 | 1／6.901 | `moto6185-cpu-2a9a5338febf` |
| skip_s_subtree | known_wrong | 0 | 0／11.748 | 1／6.652 | `moto6185-cpu-2a9a5338febf` |
| swallow | known_wrong | 0 | 0／11.391 | 1／6.566 | `moto6185-cpu-2a9a5338febf` |
| top_only | known_wrong | 0 | 0／10.510 | 1／6.099 | `moto6185-cpu-2a9a5338febf` |
| rv_break_after_s | known_wrong | 0 | 0／11.742 | 1／7.229 | `moto6185-cpu-811928f6a0d2` |
| rv_depth4 | known_wrong | 0 | 0／11.074 | 1／6.730 | `moto6185-cpu-811928f6a0d2` |
| rv_dynamotype | observation_not_positive | 1 | 0／11.519 | 0／6.228 | `moto6185-cpu-811928f6a0d2` |
| rv_scalar_s | known_wrong | 0 | 0／10.923 | 1／6.726 | `moto6185-cpu-811928f6a0d2` |
| rv_shape_key | known_wrong | 0 | 0／11.424 | 1／6.802 | `moto6185-cpu-28e751fc3785` |
| rv_swallow_attr | known_wrong | 0 | 0／11.847 | 1／7.394 | `moto6185-cpu-28e751fc3785` |
| rv_tagparent | known_wrong | 0 | 0／10.547 | 1／6.071 | `moto6185-cpu-28e751fc3785` |
| rv_top_or_null | known_wrong | 0 | 0／11.979 | 1／6.452 | `moto6185-cpu-28e751fc3785` |

raw分数为4个1、18个0；只有ctx／parity两个正对照，ctx_list另属兼容修法，rv_dynamotype是范围外漏判观察。16个既定错误修法均0；noop0，原gold D4不完整仍0。不能将四个1写成四种语义正确修法，也不能改写原gold或rv分数。

每臂实际收集36项、原短摘要36行、解析35键。1F与原34P全部逐项对应；所有原34P通过，两条历史参数合键的实际行均PASSED，无missing／skipped／unaccounted。分数0臂只有目标F失败，目标函数首个失败之后没有达到的断言不作通过结论。作者已读每个失败臂的完整FAILURES段与实际参数，以及所有CLI footer、候选清理及查询；具体失败位置见[noop](cpu_noop_preflight_r13_20261003.md)、[首组](cpu_group1_owner_readback_r13_20261003.md)、[第二组](cpu_group2_owner_readback_r13_20261003.md)、[第三组](cpu_group3_owner_readback_r13_20261003.md)、[第四组](cpu_group4_owner_readback_r13_20261003.md)、[末组](cpu_group5_owner_readback_r13_20261003.md)。DID NOT RAISE日志没有完整循环locals时，静态机制与实际失败分开。

noop原完整安装全文已读。其余21臂完整安装段比较仅归一化两处固定editable wheel生成SHA、pip临时目录及结束时间戳，其余字节与noop一致；所有安装完整rc0、两轮build/install成功。每臂实际创建／移除1，无open、halted、aborted、cleanup failure；自有容器与网络查询actual rc0且完整stdout／stderr为空。有限四组串行wrapper已自然退出0，没有自动重跑。

下面8个不同archive共528原件：六组矩阵499件，实际UID6件，真实CC23件；这不是528次实验，也不加算作者生成的读回记录。所有archive、manifest、成员SHA和长度经运输核对，parent均0。

| 实际job | 原件数 | archive SHA256 | manifest SHA256 |
| --- | ---: | --- | --- |
| `moto6185-cpu-34561d16159e` | 45 | `0e5b23b58c608b6b1be73089c776a9ec566c6c1a8c970580da1283f81118d4c7` | `10e0a7e39e03f721d8c6d1cfb87dacc203696066c0c20b1f1606aa4ce72ef53e` |
| `moto6185-cpu-d3ebfdc58aa8` | 88 | `e4e24a8d76fde4ccef67c3d9c6f2e4d221f2a9ecbd9fddf82cbdebe069cd9fbd` | `b3bd95d3fe240e4d46f22f0e50ef82b4263b6815657ff875fbae948afced3f97` |
| `moto6185-cpu-171d1b6897be` | 102 | `248433b0c5fa8144523e6a2c999c5e867bc5455ab9e2163e8911cb4368dfd17a` | `ca15ac962795e649a5a4d939607f848f1ea9a4e8d944887918bb6f65e29a469f` |
| `moto6185-cpu-2a9a5338febf` | 88 | `b84d3980b1cf09e09242b2c3e1b5d43c933b6d1bed32cc00fd10bbc31aafb492` | `80cc25181611f58c94ffff37cb735198b216a59fa62cdbbbb83e43a905c4fe4f` |
| `moto6185-cpu-811928f6a0d2` | 88 | `5c118782cb45cd2e97304d0b35b5296d1e2c270a3e152404c2f29ca5276ddd3f` | `0447a7eeade865d395b0e158e365dee9ef03956f37470a55739ace34df42b099` |
| `moto6185-cpu-28e751fc3785` | 88 | `3213a42a5dc48e601943d904f9ee7a0de011bbb1fbfa9cf84320fdc5c5b348b5` | `d20fddb26721399bc4bbd82f537ed9feffd33514d573251838fad3e4cab33bf4` |
| `moto6185-uid-9859d882f206` | 6 | `f822eb7e72f4d9fd85585d6ec11a5b2ce677a12f6928311dcc2b11d1641e7c38` | `24c325c2aa46850e0d1b03e431cd1a78dba38c9f03adfd177d6624aff2690c62` |
| `moto6185-actor-262aa667567f` | 23 | `7697cfc2f06887929cb4e501bf4fe12858244dc95b090a11922bb0a2bc76407a` | `ac24e06b9ba326504c2a84561b6d2e259021c9f44595029fbc7eab4776643a1b` |

原件根均为 `runs/category2_repair_20260929/moto_cpu_20261003/<job>_evidence/`，六组作者逐项读回为同目录 `<job>_author_raw_readback_v2.json`。第2–5组安装比较为 `<job>_install_segment_comparison_owner_v1.json`；首组另保留已核安装差异记录。该路径是运行工件入口，报告不复制FP内容或私有断言给solver。

实际UID54321原make init rc0，激活后的testbed解释器／本地Moto模块／botocore+boto3 1.35.9、限制和清理已核，见[UID读回](../../reviews/moto6185_r13_uid_install_owner_readback_20261003.json)。真实CC2.1.205＋确定桩已执行原C1–C4四公开操作，首request完整statement spec.prompt实际交付，六行generic public_hints没有进入messages/system。原CC不含INSTALL，UID原安装另验。完整stdout/stderr只在进程侧捕获，CC tool_result只有RC标记；不能声称CC或自主模型看到完整输出。93个newer entries仅部分目录／pycache列举，不证明93个全为pycache或全工作区无产物。既有legacy false、清理前进程和实际最终清理的不同范围保留，详见[原作者记录](../../reviews/moto6185_r13_uid_public_actor_owner_readback_20261003.json)及[交付范围补充](../../reviews/moto6185_r13_public_actor_scope_clarification_20261003.md)。没有自主模型、actor FP或actor-to-grader实际链路结果。

复用[部分非作者报告](../../reviews/moto6185_r13_partial_cpu_non_author_20261003.md)的已闭合5臂＋UID＋CC162件；后续13臂已有增量预读，仅最后4臂及全矩阵一致性待最终非作者确认。遵守[既定停止范围](../../reviews/moto6185_existing_stop_scope_readback_20261003.md)：多标签、未保护畸形值、超五层及其它范围外输入登记限制，不据此开启新的穷举或追加授权。模型实际源码若在保护范围内回退，仍须分析并修复。

安装约10–14秒、项目测试约6–8秒只来自各自原阶段；可信保护／环境准备、复制与运输另有耗时，不归因solver或模型。单次固定对照不证明时延稳定性、GPU可运行性或训练准入；resource_facts null和typed资格缺口保留。最终独立普通诊断通过后才能另固定探针输入、落总账并通知GPU；GPU必须另核实际code／image／UID／预算／完整prompt／FP与轨迹。未启动普通追加采样暂缓，后续资源处置需用户授权。
