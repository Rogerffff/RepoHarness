# Project-MONAI__MONAI-2446 历史释放前独立静态分析

封存阶段：2026-09-25；仅第一阶段。未读取任何 history/旧质量结论；写入后不修改。

路径约定：ROOT=`/Users/roger/Desktop/claude-code-verl-stage0h`；P=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-2446`；V=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/Project-MONAI__MONAI-2446`；O=`/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/Project-MONAI__MONAI-2446`。正文源码路径相对 P/base；原运行路径相对 ROOT。仅用只读文本/JSON/hash与限定源码阅读，没有执行项目命令、安装/网络/容器/GPU/模型、修改原题/评分或派生agent。证据分为静态推断与已存在的历史真实RH2，当前CPU/actor运行证据为无。

## 1. 公开目标、版本与初态

题面要求 `SmartCacheDataset(shuffle=True)` 只打乱内部数据，调用方的外层 `data_list` 顺序不变；不是禁止内部 shuffle，也不要求元素深复制。P/user_prompt.txt 给出五个单元素 NumPy 数组、cache_rate=0.5、replace_rate=0.4 的具体复现。P/base_identity.json 的 base 为 `05b2da61d70324c2f02b5d72429ddb7cc171b9b9`，公开版本 0.5；V/grading.json、gold/test patch 及历史 gold stage 的 HEAD 对应同一 base。

`monai/data/dataset.py:681–685` 先用原 data 调 `randomize` 再传父类，`:712–716` 原地 `self.R.shuffle(data)`；父类 `Dataset:70` 直接保存引用，`CacheDataset:548–556,574–586` 按这一数据建立缓存。初态缺陷有静态根因及历史 no-op 目标失败双重证据。历史 grader no-op 的 `git status` 显示 clean，gold 显示仅 dataset.py 修改；它们均为可信测试恢复前的 grader 视图，不能替代来源镜像/实际 actor 准备完成后 status。日志中 `git show` 是 base 提交内容，不是未提交 diff。

## 2. 全部新增断言、fixture/helper 与双向映射

test.patch 只增加 `TestSmartCacheDataset.test_datalist`，没有新增 helper/import。构造五个数组列表，`copy.copy` 备份外层列表，按题面构造 dataset，唯一新增断言为 `np.testing.assert_allclose(data_list, data_list_backup)`。共享元素身份不妨碍检测换序，但它不检测对元素内容的原地改动；本题直接要求的是 shuffle 副作用，不据此扩展成任意变换深复制门槛。

| 公开要求/合理旧行为 | 公开依据 | 测试 ID/决定性断言 | 覆盖与证据 |
|---|---|---|---|
| 输入列表顺序不变 | user_prompt 复现及结尾 | F2P `tests/test_smartcachedataset.py::TestSmartCacheDataset::test_datalist`，allclose 五个有区别的元素 | 直接覆盖这组输入；no-op 3/5 元素错位，gold pass；不强制 copy API |
| 内部仍 shuffle，保持种子结果 | dataset.py:664–665；Randomizable 的局部 RandomState；已有公开 test_shuffle | P2P `…::test_shuffle`，seed=123，三次更新后 dataset[15] 分别为 18、13、5 号文件 | 历史双方 pass；可拒绝简单取消 shuffle。只覆盖固定规模/种子和这些取样位置 |
| shuffle=False 的运行窗口保留/替换 | dataset.py:618–640,718–831；旧测试 | P2P `…::test_update_cache`，旧缓存尾部与新缓存前 8 项相等；替换队列与后 2 项相等 | 历史双方 pass；不约束 shuffle=False 的容器身份 |
| 初始缓存规模、变换、重复启停 | CacheDataset 与旧 test_shape | 实际额外执行 `…::test_shape_0` 至 `_4`：缓存长度、非 None、图像/标签相等或字符串类型 | 这 5 项不在 expected P2P，但双方实际 pass；不是所有线程时序的证明 |
| 一般 Sequence、自定义可复制对象、其他种子/规模 | 注解 Sequence；randomize 捕获 TypeError | 本题参考集没有对应断言 | 有限覆盖；未证明具体合理实现被误拒，不将所有 Sequence 均应支持 shuffle 加为新要求 |

反向看，唯一新增断言全部由题面直接支持。P2P 的精确随机序列来自公开旧行为，合理保留；新增测试不规定 shallow/deep copy、变量名、函数结构或内部容器类型。全体 F2P=1、P2P=2 已逐个阅读，无抽样。

## 3. gold、合理替代实现与回归

gold 在 shuffle 分支、randomize 前加 `data = copy(data)`，保留随机数消耗、父类建缓存时机和 shuffle=False 的引用语义，符合列表目标；文档新增“不原地修改原输入序列”说明与题面一致。对 ndarray 的 copy 通常隔离数据，对不可变 tuple 原有 TypeError 警告分支仍在；对自定义 `__copy__` 的行为没有测试/实证，不把这一泛化写成普遍正确性保证。

合理非 gold 路线包括在该分支将普通输入列表浅拷贝到内部容器、或者创建相同随机排列的独立列表；只要首次缓存和后续替换都使用内部顺序，应满足断言。深复制普通数组列表也能通过，但额外成本与元素身份变化没有题面要求。上述替代路线未执行，不声称“所有正确解均不会误拒”。反例“关闭 shuffle”会被公开 test_shuffle 阻止；针对特定长度/seed 的不完整补丁可能漏过有限样本，这是有限覆盖，不是本轮已执行攻击。

相关调用者 `SmartCacheHandler`（全文 1–78）仅按 STARTED/EPOCH_COMPLETED/COMPLETED 调 start/update_cache/shutdown，不依赖原列表被改动。gold 不改这些方法。旧 `test_update_cache` 不 shutdown 背景 daemon、快照 replacements 有时序相关性，本轮未作重复运行/线程调度验证；历史两次通过不能证明确定性。未发现有具体证据的 gold 新增回归（check26 不作 pass 保证）。

## 4. 历史真实评分条件及交付/恢复

本题仅引用 2026-09-19 compat-v1 的 no-op/gold 两次，各自 ledger 第 1 行；没有引用未提供的修前原始失败结论。配方确实从 nibabel 5.2.1 改装预置 wheel 4.0.2，logs 的安装前后版本输出一致。派生镜像仅 COPY wheels，image.json 声明 base_layers_preserved；build.log 对应派生 image ID。两次 recipe 的五个文件逐字节相同。此修复已覆盖这里引用的 grader，不能推导 actor 已装同一版本，亦不能仅据 pin 推断旧失败原因。

实际命令为 `pytest -rA tests/test_smartcachedataset.py`，不是只运行 expected 三项。no-op log:611–670、755–770 记录目标 allclose 失败，另外七项 pass；gold:645–755 八项 pass。install 最后命令 RC=0，test RC 分别 1/0，无 missing/skip、无区段外解析。日志明确导入 `/testbed/monai/__init__.py`。安装链使用分号，`install_rc_last_command=0` 只严格代表末命令；定向核读未见 ERROR/重试，但不据它证明每个安装步骤有独立 RC。

候选 gold 输入 hash 与 V/gold.patch 相同，stage 为 git_apply、目标 HEAD 正确，projection 仅包含 `monai/data/dataset.py`，日志 diff 也仅为 gold 三块改动。可信恢复先从 base checkout `tests/test_smartcachedataset.py` 再 apply test patch，setup attestation 的 restored=1、expected=1、present=1、absent=0、apply_rc=0、setup_ok=1；控制文件保护报告通过，runner digest 前后相同。公开 non-test 修复能交付，未见排除合法源码之证据；未独立审计完整 manager/投影算法或对抗性评分控制面，不扩大为安全证明。cleanup 原账本 removed=true。

## 5. 开发需求、资产、网络与资源

| 需要操作/资产 | 公开依据 | 现有证据适用条件 | actor 缺口 | 最小公开命令/预期（未执行） |
|---|---|---|---|---|
| 在正确初态编辑非测试源码 | public_hints、dataset.py | 历史 gold git_apply 可交付上述源码；P 为静态 base | 实际 HEAD/status/初始差异、UID/HOME/cwd/PATH、写权限全 unknown | `git rev-parse HEAD` 与 `git status --porcelain=v1`，记录 RC/采集阶段，识别来源改动 |
| Python、NumPy、torch、本地 MONAI | requirements: torch>=1.5、numpy>=1.17 | 历史 grader conda testbed Python3.8 路径、editable 安装及导入路径已见 | actor 激活/版本/源码生效 unknown | `python -c 'import sys,monai,numpy,torch; print(sys.executable,monai.__file__,numpy.__version__,torch.__version__)'` |
| 公开复现：外部列表保持、内部仍乱序及缓存一致 | 题面；公开 test_shuffle | 所需仅合成小数组、CPU 线程，不要求下载权重/影像 | actor 线程/权限 unknown | public_read 的短脚本可作提案；seed=0、shuffle True/False 和缓存首两项的预期有源码依据，不规定唯一复制策略 |
| 窄旧测试、临时 NIfTI 文件 | test_smartcachedataset.py:17–72 | 历史 grader 预置 nibabel4.0.2/parameterized0.9.0；shape 用 tempfile 合成影像 | actor nibabel、临时目录写权、wheel 可见性 unknown | `python -m unittest tests.test_smartcachedataset`；base 旧公开测试应可运行，新增目标断言另按公开复现检查 |
| 依赖获取与资源 | requirements-dev；原安装日志 | grader deny_all；compat wheel 本地；cpus=2.0、memory_bytes=4294967296、pids_limit=512 | actor 网络政策、供应路径/资源 unknown | 最小复现无需网络/GPU；必要安装只能走既定供应路径，不能据 pip 声称任意联网可用 |

public_read 建议的命令是开发诊断提案，不是评分规范；其 test_shape 会用文件/更多依赖，而单纯列表复现没有该需求。无需为了本轮静态判定安排重复 CPU。唯一优先下一步：由协调者在实际 actor 材料交付时核对 HEAD、准备后 status/初始差异及解释器/本地 MONAI 来源，确认本题历史 grader 的兼容底座是否到达 actor；本轮不派任务二。

## 6. 用途、暴露、稀疏检查与未读范围

静态建议为可保留的 development_diagnostic 候选，`scope=static_review,state=needs_review`（待 actor 验证），不等于训练/正式评测批准。此任务是缓存容器所有权问题；与本包另外两题同属 MONAI 但修改文件、目标行为、base 均不同，未见同修复派生；跨包重复/留出重叠未查。审查者已见本题 gold、隐藏测试、no-op/gold 原评分，不可再作为独立 solver；截至封存未读任何 history/旧质量结论/reviewer。P 不带 Git 历史，实际 actor 历史/工具/网络是否能取得答案 unknown，不能声称无污染。

稀疏编号：1、2、18–20 在上述材料/历史运行限定内 pass；3、8、10、13–15、30、33–36 unknown；4、9、16–17 仅上述投影/历史路径有支持；23、24、27、28 对列表目标静态支持且未证普遍性；25 有有限样本边界，无本轮证实错修通过；26 unknown（未证新增回归）；29 issue（本审查材料有答案，只限私有审查用途）；31–32 未全面对抗审计；37 的 nibabel 配方只改环境；38 当前 actor 可复验性 unknown；39 未跨题检查；40 已明确公开/私有与历史释放边界。未列编号 not_checked。

真正阅读：指定五份中性方法、本题 O/public_read.md；P 的 user_prompt/public_bundle/base_identity/environment_brief 全文；base/dataset.py:52–115,483–590,609–866（长输出中段曾截断，核心构造/替换路径及目标测试已单独复读）、test_smartcachedataset.py 全文、compose.py:104–115、transform.py:140–170、smartcache_handler.py 全文，三份 requirements 全文。V/grading/test.patch/gold.patch/validation/run_refs/environment_record 的本题字段；run_refs 所定两个原 ledger 行、两个 diagnostics 全文、gold candidate hash/projection/stage 全文、五份 gold recipe 全文及 noop 对应字节相等核对、image.json/build.log 全文；inventory 只读取身份、python/head、facts 键名，未通读其 files 内容。日志仅定向阅读 status/diff/setup、安装命令与依赖版本/错误检索、目标失败与逐项总结；未宣称逐字阅读全部依赖输出。没有读取 source_refs/history、host_grading_view、共享其它 ledger 行、baseline_manifest 全文、归档内容、其它题包/旧报告/reviewer。未执行项目或候选，所有新 CPU/模型/token/费用观测为空。

## 附录：本题精确运行定位与原条件

源镜像tag：`xingyaoww/sweb.eval.x86_64.project-monai_s_monai-2446:latest`；期望manifest digest：`sha256:cca2571758f276aa5d82fcb372b523e2201cd10be150776badceaaa04defad6a`。

### gold

- 原账本：`runs/env_recipe_repair_20260919/compat_v1/tasks/Project-MONAI__MONAI-2446/gold/ledger.jsonl:1`；选中行SHA256（不含末换行）`cfc04c7e5599324b9e590ba38d9c3229e923d09d4f7d104a37f496e2eb79f3fe`。
- 日志：`runs/env_recipe_repair_20260919/compat_v1/tasks/Project-MONAI__MONAI-2446/gold/eval_logs/evallog_replay-er19-cv1-Project-_0e7de613.eval.log`；SHA256 `8d934bf53841c59e1cc51531dfbe7b7f0595b70a099136a520be04716fdbeab1`。
- 原条件：`{"run_id": "er19-cv1-Project-MONAI__MONAI-2446-gold", "source": "swe_gym_lite", "schema_id": "rh2.replay_grade_ledger.v1", "started_at_utc": "2026-09-19T07:06:41.836517+00:00", "image_ref": "sha256:c203df7326b9ed001876855ac1e24a6fa5e7d213d07fd395ee4261433f931a55", "image_digest_expected": "sha256:cca2571758f276aa5d82fcb372b523e2201cd10be150776badceaaa04defad6a", "image_id_actual": "sha256:c203df7326b9ed001876855ac1e24a6fa5e7d213d07fd395ee4261433f931a55", "image_identity": "local_build:sha256:c203df7326b9ed001876855ac1e24a6fa5e7d213d07fd395ee4261433f931a55", "image_local_build": true, "derived_image_recipe": "compat-v1:Project-MONAI__MONAI-2446", "scripts_digest": "sha256:1301d6363a7c104b8ad1e153fd4d1dbff2d070b30f8620ec6404a3bb99eda207", "baseline_policy_version": "baseline_policy_v2", "policy": {"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}, "budgets": {"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}, "resource": {"mem_peak_mb": 428.621, "mem_peak_unavailable_or_zero": false}, "resource_facts": null, "reference": null}`。
- 原安装/测试摘要：`{"install_rc_last_command": 0, "install_seconds": 8.302, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 0, "test_seconds": 7.002}`；报告：`{"execution_failure_evidence": [], "execution_failure_stage": null, "f2p_pass": 1, "f2p_total": 1, "failure_category": null, "grader_version": "swebench-4.1.0+swegym_parsers@242429c1", "grading_semantics": "swe_f2p_p2p", "infra_failure_detail": null, "outcome": "resolved", "p2p_fail": 0, "p2p_total": 2, "report_id": "rpt_grading_0e7de613", "reward": 1.0}`。
- 投影：`{"frozen_patch_digest": "sha256:22623f3ff7b2f887f5097ce3fa92acc91055a3381a1dbc39b39ad1431267ce3d", "ignored_paths": [], "included_paths": ["monai/data/dataset.py"], "unsupported_shape_reasons": []}`；parser：`{"apply_ok": true, "num_parsed_outside_segment": 0, "num_parsed_tests": 8, "parser_source": "swegym_parsers@242429c1", "reference_missing": [], "reference_skipped": [], "resolution": "RESOLVED_FULL"}`。

### noop

- 原账本：`runs/env_recipe_repair_20260919/compat_v1/tasks/Project-MONAI__MONAI-2446/noop/ledger.jsonl:1`；选中行SHA256（不含末换行）`f645490f585def67b09bc0cb31f7f3158bd680927d43648273e1692be3978ca9`。
- 日志：`runs/env_recipe_repair_20260919/compat_v1/tasks/Project-MONAI__MONAI-2446/noop/eval_logs/evallog_replay-er19-cv1-Project-_d1a9c1c5.eval.log`；SHA256 `b5e7014496170f3e8ff4cb914b608f45b32e607136df3ca561d261bb64bb8335`。
- 原条件：`{"run_id": "er19-cv1-Project-MONAI__MONAI-2446-noop", "source": "swe_gym_lite", "schema_id": "rh2.replay_grade_ledger.v1", "started_at_utc": "2026-09-19T07:05:54.605294+00:00", "image_ref": "sha256:c203df7326b9ed001876855ac1e24a6fa5e7d213d07fd395ee4261433f931a55", "image_digest_expected": "sha256:cca2571758f276aa5d82fcb372b523e2201cd10be150776badceaaa04defad6a", "image_id_actual": "sha256:c203df7326b9ed001876855ac1e24a6fa5e7d213d07fd395ee4261433f931a55", "image_identity": "local_build:sha256:c203df7326b9ed001876855ac1e24a6fa5e7d213d07fd395ee4261433f931a55", "image_local_build": true, "derived_image_recipe": "compat-v1:Project-MONAI__MONAI-2446", "scripts_digest": "sha256:1301d6363a7c104b8ad1e153fd4d1dbff2d070b30f8620ec6404a3bb99eda207", "baseline_policy_version": "baseline_policy_v2", "policy": {"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}, "budgets": {"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}, "resource": {"mem_peak_mb": 485.766, "mem_peak_unavailable_or_zero": false}, "resource_facts": null, "reference": null}`。
- 原安装/测试摘要：`{"install_rc_last_command": 0, "install_seconds": 8.832, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 1, "test_seconds": 7.452}`；报告：`{"execution_failure_evidence": [], "execution_failure_stage": null, "f2p_pass": 0, "f2p_total": 1, "failure_category": "tests_failed", "grader_version": "swebench-4.1.0+swegym_parsers@242429c1", "grading_semantics": "swe_f2p_p2p", "infra_failure_detail": null, "outcome": "unresolved", "p2p_fail": 0, "p2p_total": 2, "report_id": "rpt_grading_d1a9c1c5", "reward": 0.0}`。
- 投影：`{"frozen_patch_digest": "sha256:5f17a8c508b226da92c328c029045dac17cede4ecba040083b2655fae90d3116", "ignored_paths": [], "included_paths": [], "unsupported_shape_reasons": []}`；parser：`{"apply_ok": true, "num_parsed_outside_segment": 0, "num_parsed_tests": 8, "parser_source": "swegym_parsers@242429c1", "reference_missing": [], "reference_skipped": [], "resolution": "RESOLVED_NO"}`。

所有资源字段保持原名与数值，未自行换算单位。source镜像inventory ID、期望manifest digest和实际grader image ID不可互代；3715/5686的实际image_id_actual为null。历史env_qualification=absent；实际actor工作树/消息、准备后status输出与RC/采集阶段、忽略资产、UID/HOME/cwd/PATH、源码导入、资产位置权限、网络与资源均unknown。没有用静态base干净代替这些事实。
