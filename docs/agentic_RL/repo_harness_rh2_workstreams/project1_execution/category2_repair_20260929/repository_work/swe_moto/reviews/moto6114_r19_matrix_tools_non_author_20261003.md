# Moto6114 R19 四臂薄工具：非作者启动前窄核

日期：2026-10-03。结论：**所核固定字节未发现启动前静态阻断，可进入既定 CPU 槽位执行；新37参考的四臂结果仍全部待实际原件验收。** `noop/gold/wrong_first/exact_qwen = 0/1/0/0` 是计划预期，不是观测得分。本报告不改旧 R7 准入、GPU raw1、FrozenPatch 或既有请求，也不授予真实 actor／训练资格。

## 范围与实际读取

本次只读本地文件，使用标准库文本、JSON、SHA-256、AST 和字段比较；未导入或执行项目、SDK、测试、模型、Docker、SSH 或 CPU 作业。只新增本报告。审查者已接触私有评分、反例与 gold，不是公开盲读 solver。

实际读取：`tools/moto6114_cli_matrix_r19_v1/` 四文件；已审 `tools/moto6114_cli_matrix_v4/` 对应文件作增量对照；固定 R19 发布 manifest、verify 脚本和全部1476个列举成员的字节；R19 的 CLI、prepared-task consumer、replay driver、revision model/context、sandbox profile 和 producer／registry；`runs/category2_repair_20260929/moto_cpu_20261003/local_r19_prepare_v1/` 六份原件；CPU 来源／派生收据；gold、wrong_first、exact_qwen 的固定源；新安全 launcher。没有读取其它在途作业。

已有效的 [R7 v4／noop审查](moto6114_v4_entry_and_noop_reuse_non_author_20261003.md)、[两条P2P材料审查](moto6114_neptune_preservation_v2_materials_non_author_20261003.md)、[两容器实际行为对照](moto6114_neptune_name_diagnostic_result_non_author_20261003.md) 和 [发布输入审查](moto6114_neptune_p2p_publication_input_non_author_20261003.md) 作为范围依据，本次不重复整题断言或 Qwen 完整语义审查。

## 固定身份

| 文件／对象 | 字节数 | SHA-256 |
| --- | ---: | --- |
| 工具 `manifest.json` | 493 | `5ae8d8f6e5c65477a5ccc61212e2043057f25900a6f3de443a6eff11eefbf013` |
| `matrix.py` | 14976 | `293f08a9acff84fb5fc5cc2d745e940ab5bb4729a0530997c370e8a264c185aa` |
| `expected_runtime.json` | 6024 | `556a41c525a8b9931832b0f0c2ca875dc61d5cbab2b0f80543fe2c60daf67166` |
| `image_recipe_binding.json` | 1724 | `553e1aeaa984ea899518d12688462be0a35d815b4d94abae13a7af0e301d990f` |
| 安全 `launch_moto6114_r19_v1.py` | 6790 | `eb3b1072b578a959b722ee8824e616664ed831752064a15dacfdc572459ef305` |
| 实际旧 Qwen 源码 diff | 6463 | `bb5eab97577260270def73fc06f8a0aa4917727cb9348afbe871f5905b2eb747` |

工具目录文件集合精确，manifest 的三个成员 SHA／bytes 均匹配且不是 symlink；matrix 和 launcher AST 可解析。R19 manifest SHA 为 `2cfdd9b4f1134c0915346b727b729665482c4c1121b550764833f16f2982402e`，release 为 `cat2-cpu-r2e093-swe40-pyd6283-moto6114-20261003-v1`，本地根为 `runs/category2_repair_20260929/releases_20261003/r2e_093_swe40_pyd6283_moto6114_v1/`。独立逐成员核1476件、合计160697519B，均与 manifest 的 SHA／size 相符且不是 symlink；外置 `verify_release.py` 的 hash 也与 manifest pin 相符，未执行该脚本。发布状态仍是 `cpu_verification_candidate_not_probe_qualified`。

工具 producer pin 为 `f0154ff831d9a08fe9f2a819b08cf45068dee63657c6b8e632479a3068c9a0a7`，指向 `s2/ingest_swe40_pyd6283_moto6114_p2p_20261003_v1/ingest_manifest_swe_revision_v1.json`；registry pin 为 `6aecd8d4f9eb40b0a82af7faae73121dc2a0292122876166765f9ecd4a5d8bd1`，指向 `s2/revisions/moto6114_neptune_p2p_v2/material_revisions.json`。两者均为固定发布成员且匹配工具常量。

## 增量及默认 prepare 读回

与 R7 v4 的执行源码 diff 相符：切换 R19 release／producer／registry、expected 和独占输出目录；增加固定 exact_qwen patch 输入与第四臂；增加正常评分三项 guard。原命令、三个既有候选、预算、安装／测试 consumer 和清理编排保持。原 `gold_input` 与 `gold` 行目录分离，未恢复早期 v3 的目录冲突。控制 choices 仅四个，默认四臂，拒绝重复；显式选择可只执行既定子集，实际循环次序仍是固定四臂顺序。输出目录 `moto6114_r19_v1/<job>` 以 `exist_ok=False` 创建，不覆盖旧证据。

本地默认 prepare 原件的单题 summary、manifest、public rollout view 和 private grading view 均对应 `swe_gym_lite::getmoto__moto-6114`。manifest 绑定的两份 public 文件 SHA、count=1 与 private host grading SHA／count=1 全部吻合；summary 的 manifest／private 摘要也吻合。其 `expected_runtime.json` 与工具 expected **逐字节相同**。

| prepare 原件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| `prepared/prepared_manifest.json` | 918 | `b8dff5ef980e9ed8f657e49b2d135882853df8e13b319f4879d52d16807bc545` |
| `prepared/prompts.jsonl` | 1994 | `ca0d46c99ff17d834a9dfadd2dd137981950450c0709ce3bc4d66b9446d8a8e6` |
| `prepared/rollout_task_views.jsonl` | 3122 | `e81c49c6bd79692b0ccab949092dc0baef75926eb5f382e868956467cd7d0525` |
| `prepared/replay_summary.json` | 544 | `f4e5c6226b010cfb31282fa29508e39941b2fe7aa4b1638ad17169e37e9d2bcb` |
| `private/host_grading_views.jsonl` | 11607 | `0c85186b769b80e51612f9b8939099a94a073dbfedf2f4709af2e8820126191a` |

直接比较固定 R7／R19 producer 的本题对象：public bundle 所有字段相同，base 仍 `f01709f9ba656e7cf4399bcd1a0a07fd134b0aec`；ENV 对象仅 `grading_bundle_digest` 不同，来源镜像、base、public、vendor、archive、validation 等其余字段相同。标准库规范化 JSON 重新计算得到：public `sha256:6c8f45da003f8e8d1e065d1801afa4659c43cbb212e319a5d07a84922af5f0f2`；新 grading `sha256:0d7a09c24df12b581adc180c577da3c947d6446ab64ec9f01789b4cc08f5afd6`；新 ENV `sha256:941bebb539b3974ff894822f9920fdd07227f6a8cf08eaa5c31173f90ea206b2`。因此 ENV 摘要变化是评分链接变化，不是换了项目环境。

新 private view 的原1F、34P逐键及顺序与旧 expected 相同；36P正好等于旧34P后追加 name_start、name_delete，37个键无重复。effective test patch SHA `2a9661…dda4` 与已审固定草案相同。context 的 `state=not_evaluated`、`apply_ok=null`、所有分区 `result=null`，没有静态伪造结果。materials identity `sha256:ea5d966eb5dfe35b9b4a8a4f5732d7fdf4c8383bc2558302a5d60c4f795ab29e` 按原 consumer 的 grading/parser/binding 三字段规范化摘要独立重算吻合。

五组 script SHA 中只有 `eval_script`、`trusted_setup_script` 相比旧 R7 改变，对应新 effective patch；三个 candidate 安装／测试 script SHA 不变。原安装命令仍 `make init`，完整测试命令仍 `pytest -n0 -rA tests/test_rds/test_rds_clusters.py`，保护集合仍唯一原 RDS 测试文件。新增两条位于同一文件，因此没有遗漏第二个测试文件的派生问题。

## 实际 R19 API 与镜像路径

已对照发布内实际源码，而非工作区最新共享实现。`rh2/scripts/replay_grade.py` 仍提供原 `prepare/export-gold/run` 参数；prepare 经 `TrustedTaskController.from_repo_root` 的原默认 SWE 来源与 R19 revised ingest 准备，并未指定旧 R7 ingest。export-gold 读取该 R19 producer 的 validation bundle；其中 gold 文本635B，SHA `bfae681e1044acffe64d7d65c1615b5545f4b62b2625961b7a6fe7d0ad591bbc`，与工具 pin 一致。wrong_first 原492B反例 SHA `5c042121e4bf56693c71f418c139b628d108b0c1fcd67bc0af48201e471c6451` 与 R19 source_members 和本地原件一致。

实际 `SWEMoto6114P2PRevision`／record 固定新 v2、原 base/public/1F34P 和两条追加 P2P 顺序；registry loader 固定新 registry 及 effective/source assets。`prepared_task_face.py` 明确将新子类排除于旧 `SWEGradingMoto6114RevisionContext` 的35项专用分支，使用原一般 `SWEGradingRevisionContext`，带 `added_pass_to_pass`；因此新37不会触发旧 revision_id／34P 限定。`diagnostics(None)` 字段与工具 expected 相容。replay 的报告形状确实含 outcome、failure_category、reward 三项，新增 guard 不依赖虚构字段。

本题不是四题 `moto_fixed_revision_environment` 注册环境分支；6114 保持既有显式 `--derived-image` 诊断路径。工具传入实际 CPU ID `sha256:1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5` 与原配方 `moto6114_install_wave1_copy_only_20261003`；原 replay 将 grader spec 置为 local_build，inspect 得到 actual ID 后记入 ledger，candidate 容器也从显式 ID 启动。原公共 source face 仍保留 tag／manifest。没有传 R2E-only overlay，且清除两个 overlay 环境变量。

`image_recipe_binding.json` 与已审 v4 **逐字节相同**。source receipt765B SHA `07d55cf5cbe3061449ad69794ddd9735ce743a7479b5294e48001892f539fff0`，derived receipt1439B SHA `497c0736359dd7964b6db8abaaa26fd4716f366868001ab298459b6da4c8cf47`；原 source manifest `cb35f7…e8ef9a`／ConfigID `fefec4…ec249`、CPU derived `1d8dd…a9f27d5`、COPY-only recipe `352caa…44993` 和三件 wheel pins 一致。运行前工具将重新 inspect 来源及派生，核 amd64/linux、source RepoDigest、原13层前缀保留且仅新增1层、离线 PIP ENV。静态没有把 GPU43f／613 镜像混作本次 CPU 条件。

exact_qwen 取 R19 registry 的固定 `source_members/.../exact_qwen_a1_source.patch`，核 SHA／6463B／非 symlink；与 OWN 固定副本及旧 GPU 实际 candidate diff 完全相同。本工具仅把这份源码内容当新条件 patch 输入，不读写旧 attempt、FP、trajectory、raw 或评分参考。CLI 中 patch 候选的 `kind='cc'` 枚举仍不构成真实 CC／模型运行证据。

工具构造的 `actor_spec` 只用于身份静态读回，通过 `rollout_spec_from_view` 后替换 CPU镜像，且检查 `grading_spec is None`。这不是实际 actor 执行，也没有将 gold／private grading 送进 agent。scope/result 保留 `model_attempts=0`、`actor_executed=false`、`formal_cpu_accepted=false`。

## Guard、预算、清理及安全启动器

资源要求保持 rollout/grader 2CPU、4GiB、PID512，grader shm64MiB；没有错误访问 rollout 上不存在的 shm 字段。setup/apply/test 为300/120/1800秒，CLI candidate900、whole grading1800、cleanup120、image inspect/pull1800秒，repeat=1；与已审 v4 相同。默认不带 `--execute` 只 prepare、镜像／消费读回与 gold 导出；正式执行仍须显式 execute。四个期望仅影响最后比较，未传给评分器，也未覆盖 report reward。

每臂要求 CLI rc0、ledger 唯一一行、stage_error=null、report存在，再要求 outcome 属于 resolved/unresolved、failure_category 属于 null/tests_failed、reward 属于0/1。failed_to_grade、解析／基础设施失败、null reward 会停止后续臂并保留此前原件。正常评分但 reward 不符合 planned 时，按既定矩阵完成所选后 rc1，待分析实际失败；这不能误写为 CPU 得分已确认。

原 replay 的 candidate 阶段保持有界 finally 持久化与自有容器删除；工具要求 `cleanup.removed=true`。原 CLI 在 finally `await manager.close()`，保存 manager_close／halted／aborted／final_status；工具要求正常单行 footer、无 halted/aborted、final exit0、无 candidate cleanup_failures。随后仅按本臂 `rh2.run_id` 查容器／网络，**查询 rc非零不会当作零残留**，两次完整 stdout/stderr/rc 均保存到独占目录。没有无标签全局删除或改写旧证据。matrix 自身没有另造评分/清理器；实际运行后还须独立读 manager 的 containers_open／supply_open 和完整原件，不能只读薄工具的 result 布尔值。

launcher 的固定工具路径、release ID／SHA、解释器、四臂选择、输出目录与 matrix 一致；先核本地四文件集合与 manifest，运输预检拒绝已有错字节，落地逐SHA／bytes核验后 chmod文件0444、目录0555，固定 receipt 存在则要求相同。经既有 `cpu_slot.py --mode run --package swe_moto` 起独占 job，使用 R19 `PYTHONPATH` 且清除 overlay；没有额外评分、模型或连接参数写入 CPU 命令记录。

连接侧 subprocess 输出捕获而非透传；运行 stdout/stderr 写本地自有文件，用户输出仅 job、控制列表、运输匹配回执与返回码；异常输出仅异常类型和中性说明，不打印 host/key/SSHargv/raw连接错误。launcher 没有另加 cpu_inv release gate；实际 matrix 在任何测试前核外部 release manifest、逐成员 verify、producer／registry以及正式 prepared expected，因此不会静默使用旧 R7 consumer。launcher 顶部旧“两题R18”说明文字有残留，执行常量、记录 schema、路径均是 R19；此为文字不准确，不构成启动阻断。

## 结论及后续原件验收边界

**无需现在修复的具体工具阻断。** 可启动所核固定 R19 四臂诊断，遵守既定 CPU 槽位调度；本报告本身没有派发作业。发布回执 ACK 不等于新37已评分，旧35 CPU及旧两容器行为对照不能替代本次正式评分。

闭合后至少读回每个实际执行臂的固定 consumer／ENV／脚本／CPU actual ID、精确候选来源和 FrozenPatch 投影、完整原 `make init` 输出与退出、完整 pytest／parser37键及原1F/34P＋新增2P逐状态、正常 report 和真实失败位置、candidate／manager 两层清理与自有双资源查询、最终父作业与 CLI footer。正常 report guard 不独立保证安装0、所有参考无缺失或某条具体断言符合预期；尤其 exact_qwen 的两个已知名称回归须在本次新37参考下看实际断言/异常，不能仅凭 planned0或旧诊断推定。这里是已有验收要求的读回边界，不新增评分契约或审批闸门。
