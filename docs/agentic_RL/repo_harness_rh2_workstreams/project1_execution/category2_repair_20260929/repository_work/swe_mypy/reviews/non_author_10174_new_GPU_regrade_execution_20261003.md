# mypy10174 原 FP 在新 GPU 镜像重评分：非作者执行链窄核

日期：2026-10-03。按 `review-standards.md` §10.4 担任 Production Tracer。范围限于 `mypy10174_original_fp_newimage_regrade_v1` 的新增闭包、code_v8消费原件、真实安装、正式参考、基线/投影、可信控制面与清理。只读本地原件并重算SHA、解析JSON/tar、静态阅读源码；未执行SSH、CPU、模型、容器、测试或项目代码。本轮唯一写入为本报告；旧报告、原raw和在用请求保持原样。既有CPU r16与GPU权限核只复用其适用事实，不重审Qwen完整轨迹或模型身份。

## 结论

**本次新GPU重评分的执行证据成立，没有发现当前具体阻断。** 79件闭包SHA/size全符；code_v8从原FP和完整1472项基线构造原50路径投影，实际80418df…镜像上的完整重建成立；正式三条pip命令均正常完成，editable确实成功构建并安装；4个正式参考执行、解析并通过，reward1.0，manager与外层资源核均清理为空。

这是原Qwen候选在新GPU依赖权限镜像上的一次重评分，不是新增模型首臂、旧GPU原raw被修正、完整mypy回归或语义/训练验收。原FP与baseline的runtime lineage仍是旧32f313…，本次实际grader镜像另记80418df…；没有回填旧身份。CPU r16的独立安装预热与Python probes范围仍保留，不能移植为本次GPU证据。

## 原件与封存核对

下列路径从仓库根目录起算。

| 别名 | 入口 |
| --- | --- |
| `B` / `R` | `runs/ordinary_gpu_probe_20261002/` / `B/remote/` |
| `G` | `R/mypy10174_original_fp_newimage_regrade_v1/` |
| `O` | `R/queue_v12/results/gpu1003-mypy10174-qwen36-a1/`，原GPU候选/基线/投影。 |
| `C8` | `B/frozen_code_v8/`，本地冻结消费源码。 |
| `P` | `R/prepared_swe_four_v1/mypy10174/`，原prepared与可信private。 |
| `I` | `B/tools/regrade_mypy10174_original_fp_newimage_v1_inputs.json`，固定输入绑定。 |
| `W` | `B/tools/regrade_mypy10174_original_fp_newimage_v1.py`，本次窄执行worker。 |

入口 `B/migration_20261003/mypy10174_original_fp_newimage_regrade_v1_closed_manifest.json` 重算SHA为 `89d51f9ee836c2d594ab2ffe6909f4dbdfa09ec113db3667d4ebe2dadf9f26b2`，与委托一致。其79个文件全部存在，SHA和大小全部匹配，总281,562字节。该数字包括61个exec交付日志、6个preflight及状态/评分材料，不是79次独立执行。闭包内plan的 `grade_executed=false` 属执行前计划，不能替代后续status/done事实。

`I`重算SHA `fcb6d2abdce3fd4e9fbebfa0c8faeda3abe7422916c48b0013a4ecab920840a7`，其22个固定来源成员SHA/size全部相符，涵盖原FP/baseline/tar/projection、prepared/private、原配置与结果、权限层读回和C8入口/source manifest。`W`本地SHA `a357d87fd8697438d149b70c5bfd944efa42a8f5805172d08ca1ba6ae7bc3c80`，与执行前作者check的固定tool引用相符；静态核其调用与后续原件对应，不以作者的预期PASS作为观察事实。

| 新增关键原件 | 字节SHA |
| --- | --- |
| `G/done.json` | `99a4c910bd03b0ba75ead98c2a6571be0c56aa482dc49a7ebd650e9fde748c41` |
| `G/eval_logs/evallog_gpu1003-mypy10174-qwen36_62794c38.diagnostics.json` | `215c37df72d94a7d20b3bc253cae7d567dfa75abe655646c0c26eb3d88486346` |
| 同ref正式eval log | `e63a6bb3b5d32a6c714e8df02fa8eb02253aed4e7d94c31d4d2c3288d2a7ecc4`，28,740字节。 |

## 真实消费链与运行身份

封存journal记录08:52:21Z启动 `/work/ordinary_gpu_probe_20261002/code_v8/rh2/.venv/bin/python` 执行worker `--execute`。worker先核固定材料与已验权限镜像、空闲队列/资源场景，再仅把原tasks-config中本题 `grader.derived_image` 从32f313…改为80418df…；独立把 `G/tasks.json` 此字段恢复旧值后，与原config_v12对象完全相同。所有固定期望输入字段与本次input_check精确一致，未改变安装配方、参考、预算或材料。

实际链为worker `controls/construct` → code_v8 `entry.load_inputs` → `entry.source_from_original` → `SWEGradingManager._verify_frozen_delta_binding` → `grade(workspace=None,frozen_delta=source)` → parser/report → `manager.close`。worker未调用actor/CC或模型；模型配置仅被加载作原输入绑定。source_from_original直接消费O的原FP/baseline，并按可信hygiene规则派生投影，不读审阅diff，不另造候选。worker要求新投影与原projection对象相等、scripts digest相同；最终新projection与旧文件连字节都相同。

C8 source manifest SHA为 `09ddb8bfdeecd3ffaa38c1048a574161ef6fa6053b2855da50166e8e8677899d`，入口SHA为 `bdf806bf8da1d5ebb4970887bfc3c7738eb3e57a75e1d07215d6d68b17e574c4`，与固定输入、runtime_binding及input_check相符。manager SHA仍为 `1783533e1e3b66a57fcaa5a599a1da4f8e4e886318e24f040c6df91f294c1c1e`，与旧已核消费链相同；组合code_v8整树并非code_v4/R6整树等价。实际scripts digest仍为 `f111e77dbc1a70b7d469cdb656034aa59c701e9ead3b2ef31e7fa0bd3a45d4ed`，材料identity为 `dca86b80c83f2e2e9c4eee8c4375952adef834008ad4cb7006ac60abeca58065`，registry为 `a49edd0750cd45c880344bdda762bd757d8bdfddd09689c69cf2e46e316e3cf6`；与旧输入及CPU r16对应项相同。

实际镜像 `sha256:80418df01e0544855bbba9d858a53e45089320ed650bc4b1eb05e91bbf33880f` 由preflight_03实际inspect和本次diagnostics同时记录。preflight的Id/Os/Architecture/Config/RootFS与已冻结权限修复镜像inspect逐项相同；此前已验wheel权限、源码未变及双UID可读只复用对应事实，本轮不再复跑权限核。实际镜像有离线PIP设置，正式pip输出使用 `/opt/rh2/build-wheels`。

## 原1472基线与原50路径投影

原FP字节SHA `d72699b958fc0f688d5e6c4d4fd5e93006bd18c4a4ea86a2f76c998a4bbeae07`；canonical digest独立重算为 `5772af211384a9828c83dd61c60c96a6447475e34c4b2bfb891f584ac4304664`。其51项内容base64的SHA全部匹配，rollout/physical identity仍为原job/#p1。原baseline字节SHA `5fab6a0f7932073ac2f47d0c69e950c8e0e64949c4d043da4227918395b2a958`，canonical为 `337be5fc6ed9a5013249a17bcfb9e48cf7dce2aa3ca27cb4b8b9fd9f0efb7172`。二者runtime_image_digest均保持旧 `sha256:32f313c82fd4f065517b8fd1faff22b79a8c1c8e108200c85c8de8188191baad`，未改写成新实际grader镜像。

原baseline.tar字节SHA `714753b01aff10c04468da922f8e9e6bccb3e02223de96209cd9f532d7688437`；本地逐项读取1472个成员，路径/类型/契约模式/内容SHA全符，无多或少项。本次 `exec_logs/003.json` 的baseline_rebuild退出0；其census stdout与原actor census逐字相同，SHA `67c508e55dd3aa024a3e1f1c9c2f5e5e09b370ea02757740724344978a19bcf7`。1498行由1472 regular条目、24 EXCL路径及2个cache省略计数构成；1472条正式manifest行精确匹配，不把排除区计数当额外baseline文件。初始env_reset显示镜像已有 `test-requirements.txt` tracked差异，完整baseline重建正是核同源内容的证据，不能把git空diff当必要前提。

manager重建时实际核HEAD与原materialized_head `c8bae06919674b9846e3ff864b0a44592db888eb`，从fresh grader census核完整条目、policy和排除路径集；不可在容器内重推导的lineage按原baseline复制参与canonical对账。因此基线通过证明同源工作树，不宣称新旧镜像ID相同。status的baseline_rebuild_passed在原verify返回后才置true。

原FP51项包含49个 `.mypy_cache/` 文件、`mypy/meet.py`及候选改动的 `test-data/unit/check-expressions.test`。可信评分投影继续是原50路径，排除那1项测试控制面，完整保留49cache和meet源码，没有新增净化。新projection字节SHA仍为 `8d61762ccbf5de9a0a3667d7e1cac48cd81d686b0246298843118d4133f8c77d`；投影后的条目集digest重算为 `4c7309d372d1d76232f5bff070cd5f9f52435bae9df5056d329e04f6eab80d7d`，与report精确匹配。`meet.py`内容SHA为 `fda3ae751b225a484400198ff560bbaab9ec56d0dc5f54e3b2846a85c103a0a7`。50次delta_write全部退出0；这是实际重放条目数，不是50次评分。report的 `test_files_modified=false` 指评分投影未含测试控制面，不能解释成原FP从未改过测试。

## 三条安装的真实结果与正式参考

三条pip都在正式候选安装段，由冻结manager按候选UID54322执行；prefix属主观测为54322。完整候选exec交付原件为 `G/exec_logs/061.json`，退出0、完整stdout，与正式eval候选段一致。脚本在三条命令前启用 `set -E` 和ERR trap，失败简单命令会写实际 `RH2_INSTALL_CMD_FAILED=<rc> <command>`；本次完整stdout无实际失败标记、diagnostics失败命令数组为空。**成功判据不是最后的 `RH2_INSTALL_RC=0` 单项。**

| 原正式命令 | 本次完整输出中的实际结果 |
| --- | --- |
| `python -m pip install -r test-requirements.txt` | requirement逐项在testbed Python3.9 site-packages满足，正常进入下一命令，ERR trap无失败。 |
| `python -m pip install -e .` | `Obtaining file:///testbed`；build dependencies/build_editable/metadata步骤全部done；Successfully built mypy，成功卸载并安装 `mypy-0.820+dev.c8bae…dirty`，随后进入第三命令。 |
| `pip install pytest pytest-xdist` | pytest6.1.2、xdist1.34.0及依赖已满足，正常结束安装段，最后RC0。 |

这是三条实际正常完成的输出证据；包未另打每条成功的独立数值RC，不伪造 `[0,0,0]` 成逐命令原始记录。完整ERR trap、命令边界和editable明确成功输出共同排除了本轮旧式“editable失败、末尾pip成功掩盖”的情形。candidate install_skipped=false、install_seconds2.735、segment_completed=true、log_partial=false、exec0；没有owner前置三install预热，本次直接跑原正式vendor安装串。镜像本来已含依赖，前/后要求“Requirement already satisfied”不能改称本次新下载依赖。

原test command保持 `pytest -n0 -rA -k "testOverlappingAnyTypeWithoutStrictOptional or testStrictEqualityWithFixedLengthTupleInCheckWithoutStrictOptional or testUnimportedHintAny"`。日志实际collection9423、deselected9419、selected4；4个节点均PASSED，pytest内部1.29s、test marker RC0。不是9423项完整回归通过。

| 正式分区 | `mypy/test/testcheck.py::TypeCheckSuite` 下逐参考结果 |
| --- | --- |
| original F2P 1项 | `testOverlappingAnyTypeWithoutStrictOptional`：success。 |
| original P2P 2项 | `testUnimportedHintAnyLower`、`testUnimportedHintAny`：success。 |
| added P2P 1项 | `testStrictEqualityWithFixedLengthTupleInCheckWithoutStrictOptional`：success。 |

diagnostics/full_reference_readback各分区与原4参考一致；parser为 `swegym_parsers@242429c1`，parsed4，missing/skipped/unaccounted/outside均0，RESOLVED_FULL，与report F1/1、P失败0/3、reward1一致。worker只要求逐参考结果完整，不强制PASS/reward1，因此原件不是按预设得分生成的成功回执。

## 可信恢复、runner、退出与清理

61个exec交付日志全部退出0。可信root setup恢复1份正式测试文件、apply RC0，root attest为expected1/actual1/absent0/irregular空/OK1；控制面protected1、目录3、missing0、protectOK1，均另有057/058原始交付。runner观察摘要前后同为 `2f4655b6933a219bb88c823bdc724ed84e84c89a2a23b39c1f399cb1da2b61c4`，diagnostics标记未变；mypy观察导入路径为 `/testbed/mypy/__init__.py`。本轮没有新增逐模块SHA/pytest同进程loader probe，不把旧CPU独立Python probe冒称新GPU同进程证据。

closed manifest的systemd读回为MainPID0、ExecMainStatus0、LoadState=not-found、ActiveState=inactive；**被collect后的not-found默认RC0不是成功证据。** 采用其封存journal_unit：08:52:21Z实际启动上述code_v8命令，08:53:57Z `Deactivated successfully`，并与08:53:56.741719Z正式report、无exception的status及 `done.complete_original_FP_newimage_regrade=true` 对应。journal_invocation是`-- No entries --`，不解释为额外退出证明。journal的6.904sCPU/92.8M峰值是systemd进程口径，不与grader的94.025s/393.602MiB嵌套相加。

manager在finally close，created/removed1/1、lease1、containers_open/supply_open/cleanup_failures均空；外层preflight_04按本job标签查所有容器为空。preflight_05/06与开始前01/02一致：只剩原2个Coder共用model服务、bridge/host/none默认网络，无本次grader遗留。这里的两层清理是manager与外层资源查询，本轮根本没有actor/session生命周期，不能套用“新actor也完成”的说法。

status还记录所有固定来源执行后SHA不变；本次独立读取22项与固定输入相符，旧GPUresult/FP仍原身份。done保留new_models0、原raw1/安装失败不回写、not_semantic_or_training_acceptance=true。`resource_facts=null`、`env_qualification=absent` 原样保留，不扩HostConfig、权重或元数据复验。

## 最小接续与停止点

没有具体问题要求新增重复GPU/CPU/model运行。这份证据可交题主作为原Qwen候选在80418df…新GPU镜像上的窄安装/重评分结果收口；原GPU“安装失败但raw1”、CPU r16预热范围与候选控制面排除事实继续各自保留。剩余模型首臂或语义/训练用途依原请求另行处理，本报告不扩查。真实消费链、身份、安装、四参考与清理已有对应原件，Production Tracer在此停止。
