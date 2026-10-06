# Project-MONAI__MONAI-3715 历史释放前独立静态分析

封存阶段：2026-09-25；仅第一阶段。未读取任何 history/旧质量结论；写入后不修改。

路径约定：ROOT=`/Users/roger/Desktop/claude-code-verl-stage0h`；P=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-3715`；V=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/Project-MONAI__MONAI-3715`；O=`/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/Project-MONAI__MONAI-3715`。正文源码路径相对 P/base；原运行路径相对 ROOT。仅用只读文本/JSON/hash与限定源码阅读，没有执行项目命令、安装/网络/容器/GPU/模型、修改原题/评分或派生agent。证据分为静态推断与已存在的历史真实RH2，当前CPU/actor运行证据为无。

## 1. 公开目标、版本与初态

公开题面要求 Evaluator 的字符串 mode 工作，具体报错来自 `SupervisedEvaluator(mode="train")`；字符串 `"eval"` 同样由公开注解/文档承诺。saliency 是动机，题面没有给另一个错误的详情，不能追加“修好全部显著图推理”要求。base=`d36b835b226ab95ffae5780629a5304d8df5883e`、版本0.8，P/base_identity、V/grading、历史 stage 对应一致。实际 actor 消息、初始改动与工作树 unknown。

`evaluator.py:117–123` 将 `look_up_option(mode, ForwardMode)` 存到 self.mode，却用原 mode 与普通 Enum 比较，两个合法字符串都落入 ValueError；`enums.py:207–213` 及 `module.py:47–121` 支持这条静态推导。历史 no-op 失败实际是 eval 字符串，不是 train。该区别不能被总分掩盖。历史 grader no-op status clean、gold 仅 evaluator.py 修改；git show 长输出为 base 提交，不是当前 diff，也不是 actor 初态。

## 2. 全部新增/修改断言与双向需求映射

test.patch 仅在现有 `TestPrepareBatchDefault.test_content` 的构造中新增 `mode="eval"`，没有新增断言或 helper。必须连同已有断言审：合成字典 image=[1,2]、label=[3,4] 和 extra 字段；TestNet.forward 返回 x；构造后 run，再用 `tests.utils.assert_allclose` 验 image/label。helper 默认检查 NumPy/Tensor 类型然后转 CPU NumPy 比较数值，默认不检查 device，也不检查 network.training、梯度、预测值或 state 恢复。

| 公开要求/合理旧行为 | 依据 | 参考测试/断言 | 覆盖或缺口 |
|---|---|---|---|
| `"train"` 应可构造并进入训练上下文 | user_prompt 的实际错误；evaluator.py:67–68,120–121,260–265 | 无对应 F2P/P2P | **核心遗漏**：只接受 eval 仍可能拿满分；静态可构造反例，未运行 |
| `"eval"` 可构造/执行 | 公开 Union[ForwardMode,str]，文档 eval/train | F2P `tests/test_prepare_batch_default.py::TestPrepareBatchDefault::test_content`：新增 eval、run，image/label allclose | 覆盖接受字符串及可运行；不证明 eval 关闭梯度/模型状态正确 |
| 默认枚举 eval 保留 | 原默认 ForwardMode.EVAL | P2P `…::test_empty_data`：空列表、epoch_length=0、默认 mode，run 无异常 | 只覆盖构造与空流程；Workflow:275–281 直接 return，不运行模型 |
| train/eval 模式与梯度状态、退出恢复 | networks/utils.py:293–357；旧 eval_mode/train_mode 测试 | expected 未包含；旧测试分别检查 training 和反向可否执行，但没有字符串分派 | 漏测；模式 helper 独立正确不证明 Evaluator 选择正确 |
| EnsembleEvaluator 同样支持字符串 | evaluator.py:336,341–358,396–407 | 本题 expected 无；公开 test_ensemble_evaluator 只用默认值 | 共享基类合理修复自然覆盖，但只修 Supervised 子类可漏过 |
| 非法值拒绝/枚举保留 | look_up_option 文档与已有路径 | 参考集无 | 保留边界有公开依据；大小写别名和精确错误文案没有新要求 |

反向检查：eval 新增用例虽不是题面具体 train 复现，仍有公开接口依据，故不是隐藏规格冲突（check23）；真正问题是题意覆盖不足（check25）。没有强制 gold 的局部变量赋值形式，test_patch 没检查内部实现。全部 F2P=1、P2P=1 均逐个审阅。

## 3. gold、合理替代路线与回归

gold 只把 `self.mode = look_up_option(...)` 改成局部 `mode = ...`；归一化后两分支分别设置 callable `eval_mode/train_mode`，与 Supervised 的 `with self.mode(self.network)` 及 Ensemble 的 `with self.mode(network)` 相容。枚举输入保持同值；字符串按 helper strip 后接受，非法值依旧由 helper 拒绝。没有证据表明此一行变更引入新回归（check26 保留未穷举）；它静态上解决 train 与 eval 两类问题，历史评分仅验证后者。

合理替代包括使用规范化的临时变量、比较 self.mode 再改成上下文管理器、枚举→函数映射。这些都可保持公共语义，不必调整 Enum 类型、显著图算法或网络工具。没有执行非 gold 实现，不能声称普遍无误拒。

一个明确的静态漏检机制：只在 mode=="eval" 时转换为 ForwardMode.EVAL，保留原 train 分支缺陷，能满足 F2P 与默认空流程 P2P 的所有已读条件，却仍重现公开 train 错误。另一种始终进入 eval 上下文的错修也不受当前 image/label 断言约束。这里没有实际运行 mutant，故证据等级为静态充分路径推导而非实验分数。

public_read 的建议 smoke 能检查 mode 选择、上下文与真实 run，作为诊断有价值；但其 `engine.mode is expected` 直接要求某个函数身份，合理自定义等效上下文管理器可能被误拒。不能把该身份断言直接升级为评分规范，应通过 network.training、torch.is_grad_enabled、退出恢复及用户 API 行为检查。空白字符串是原 helper 一致性边界，不等于题面新增必验项。

## 4. 历史真实条件、交付与恢复

只取原 baseline01 w05-1 ledger 第15行 noop、第16行 gold；选中行 hash 与 run_refs 一致。实际命令 `pytest -rA tests/test_prepare_batch_default.py`。no-op log:897–996、1040–1049：2项收集，test_content 因 `unsupported mode: eval` 失败，test_empty_data pass；gold:915–975 两项 pass。没有 train 的执行证据。test RC=1/0，install 最后命令 RC 均0；reference_missing/reference_skipped=[]，num_parsed_outside_segment=0。日志 conda testbed、editable 安装和 import 观测支持执行本地 MONAI；不是安装失败伪装成目标失败。

原安装链包括删 requirements-dev 中指定 git+ 行、`python -m pip install types-pkg-resources==0.1.3 pytest`、`pip install -r requirements-dev.txt`、`python setup.py develop`，分号串行，末命令 RC 不等于各步独立 RC。原日志有 parameterized0.9.0、pytorch-ignite0.4.8 满足；没有单独定位的 baseline generated recipe 文件，不能把当前工具版本冒充当时 runner。没有独立审读归档 manager/parser 实现。

gold 原 candidate.patch 与 V/gold.patch hash 一致；stage HEAD 正确、git_apply，无 stage_error；projection 只交付 monai/engines/evaluator.py，日志 diff:423–436 与 gold 相同。trusted setup 从 base 恢复 tests/test_prepare_batch_default.py 并 apply 私有补丁，attestation restored=expected=present=1、absent=0、apply_rc=0、setup_ok=1；控制文件保护通过、runner digest 前后一致，清理 removed=true。修改非测试源码的合法路线没有被恢复操作删掉。评分控制面抗攻击及所有路径排除规则未完整审计，不能由这次 benign gold 成功推导安全性。

## 5. 开发需求与条件

| 操作/资产 | 公开依据 | 已有证据及适用条件 | actor 缺口 | 最小公开命令/预期，均未运行 |
|---|---|---|---|---|
| 正确仓库、非测试编辑权限 | public_hints；evaluator.py | 历史 gold 源码投影成功 | actor HEAD/status/准备后差异、UID/HOME/PATH/cwd、写权 unknown | `git rev-parse HEAD`、`git status --porcelain=v1`，保留 RC/阶段和来源改动 |
| Python、torch、numpy、Ignite 与本地 MONAI | requirements torch>=1.6/numpy>=1.17；dev ignite==0.4.8 | grader testbed Python3.8 路径，ignite0.4.8；导入 /testbed/monai | actor 激活、版本/源码来源 unknown | `python -c 'import sys,torch,numpy,ignite,monai; print(sys.executable,monai.__file__,torch.__version__,ignite.__version__)'` |
| 用户 API 字符串模式及真实 forward | 题面 train；两个 evaluator 子类 | 静态路径明确，历史只测 eval；只需合成数据/小 nn.Module | actor 可执行性 unknown | public_read smoke 应删除函数身份必等约束，以 SupervisedEvaluator(mode="train"/"eval").run() 时模型记录 training/grad 状态与退出恢复判断 |
| 旧模式/默认评估流程 | 已读旧 mode/ensemble 测试 | tests 为合成 CPU 数据，无权重下载 | actor 测试依赖 unknown | `python -m unittest tests.test_eval_mode tests.test_train_mode tests.test_ensemble_evaluator`；只作相关公开回归，非全仓门槛 |
| 网络、资源、资产 | 合成数据 tests；原 policy | 历史 deny_all、cpus2.0、memory_bytes4294967296；实际完成 | actor 网络/资源/资产权限 unknown | 核心无需网络/GPU/数据集；准备依赖走批准供应路径，不能据安装日志假定 actor 联网 |

唯一优先下一步：先形成独立、行为导向的 train 验收用例提案（公开 API、启用梯度、退出恢复、保留 eval/枚举），由协调者决定评分修订；现有文本已足以证明选择器遗漏，不为确认这个选择器事实再凑 CPU。实际 actor 验证仍必需，但不是本题当前最具区分力的下一步。本轮不执行、不派任务二。

## 6. 用途、暴露与范围

静态 disposition：needs_review，原因首先是验收漏掉题面 train 场景，其次 actor 条件未验证；可作 development_diagnostic，不批准正式训练/评测。与另外两题仅同仓库，base、行为、补丁文件不同；未跨包查重/留出重叠。审查者已见本题私有答案/评分，材料不可给 solver；未读 history/旧结论/reviewer，实际 actor 答案暴露渠道 unknown。

编号稀疏结论：1、2、18–20 对所列版本/历史 eval 路径 pass；3、6–8、10–15、30、33–36 unknown（无 actor/模型证据）；4、9、16–17 对历史 benign gold 的限定路径有支持；23 静态无隐藏要求冲突；24 未见实现强制，但 public_read 建议的身份检查不能作验收；25 issue（train 及模式效果缺失）；26 unknown（未证新回归）；27 单行修复静态支持；28 已剔除身份式新增要求；29 issue（私有答案暴露限定用途）；31–32 非全面审计；37–39 not_checked；40 历史释放边界保持。未列 not_checked。

真正阅读：五份中性方法、本题 O/public_read；P/user_prompt/public_bundle/base_identity/environment_brief 与三份 requirements 全文。base/evaluator.py:60–125,195–225,250–268,330–358,390–412；module.py:47–122；enums.py:207–215；networks/utils.py:293–358；workflow.py:90–160,270–288；test_prepare_batch_default/test_ensemble_evaluator/test_eval_mode/test_train_mode 全文；tests/utils.py:62–120（相关 helper）。V/grading/test.patch/gold.patch/validation 与 run_refs/environment_record 的本题字段；精确 ledger 两行、diagnostics 全文、gold candidate hash/projection/stage、日志 status/diff/setup/安装命令与版本/错误检索/失败与逐项总结；完整依赖输出未逐字审阅。部分首次大输出截断内容均未据此宣称通读；核心源码和测试已单独复读。未读 SaliencyInferer 内部、全部调用者、私有 source_refs/history、host_grading_view、baseline_manifest 全文、归档代码、其它 ledger 行/题包/旧报告/reviewer。没有执行项目、测试、安装或模型；新 CPU/token/费用无观测。

## 附录：本题精确运行定位与原条件

源镜像tag：`xingyaoww/sweb.eval.x86_64.project-monai_s_monai-3715:latest`；期望manifest digest：`sha256:503ca39274e12c0aa0d06d0e77ad4f41628516a7b175feb4a5c10f940e2d1ab8`。

### noop

- 原账本：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w05-1/ledger.jsonl:15`；选中行SHA256（不含末换行）`39e45b0f908ea3f12f912c1034e468c944c85612f60fdd5dfd40a8f795b231d7`。
- 日志：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w05-1/eval_logs/evallog_replay-f216-baseline01-w_5146f8c9.eval.log`；SHA256 `9b4a7187ca78c56a3fc414b22bc5800b19e2e2b77c24c916a3a28682f1151fad`。
- 原条件：`{"run_id": "f216-baseline01-w05-1", "source": "swe_gym_lite", "schema_id": "rh2.replay_grade_ledger.v1", "started_at_utc": "2026-09-18T20:17:17.554496+00:00", "image_ref": "xingyaoww/sweb.eval.x86_64.project-monai_s_monai-3715:latest", "image_digest_expected": "sha256:503ca39274e12c0aa0d06d0e77ad4f41628516a7b175feb4a5c10f940e2d1ab8", "image_id_actual": null, "image_identity": "sha256:503ca39274e12c0aa0d06d0e77ad4f41628516a7b175feb4a5c10f940e2d1ab8", "image_local_build": false, "derived_image_recipe": null, "scripts_digest": "sha256:56d3a76fcd8e956e3960c6d170247fe2b24142f99012d9625b6e684eb276590d", "baseline_policy_version": "baseline_policy_v2", "policy": {"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}, "budgets": {"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}, "resource": {"mem_peak_mb": 840.281, "mem_peak_unavailable_or_zero": false}, "resource_facts": null, "reference": null}`。
- 原安装/测试摘要：`{"install_rc_last_command": 0, "install_seconds": 11.922, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 1, "test_seconds": 12.166}`；报告：`{"execution_failure_evidence": [], "execution_failure_stage": null, "f2p_pass": 0, "f2p_total": 1, "failure_category": "tests_failed", "grader_version": "swebench-4.1.0+swegym_parsers@242429c1", "grading_semantics": "swe_f2p_p2p", "infra_failure_detail": null, "outcome": "unresolved", "p2p_fail": 0, "p2p_total": 1, "report_id": "rpt_grading_5146f8c9", "reward": 0.0}`。
- 投影：`{"frozen_patch_digest": "sha256:5987ff4719e160520536a0e6a95bc5912a062e93bc9108e024cb91b452ad2d29", "ignored_paths": [], "included_paths": [], "unsupported_shape_reasons": []}`；parser：`{"apply_ok": true, "num_parsed_outside_segment": 0, "num_parsed_tests": 2, "parser_source": "swegym_parsers@242429c1", "reference_missing": [], "reference_skipped": [], "resolution": "RESOLVED_NO"}`。

### gold

- 原账本：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w05-1/ledger.jsonl:16`；选中行SHA256（不含末换行）`25921f2f2e92678bad9d88a5f142988abf4518fe715127515059699d2e773e65`。
- 日志：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w05-1/eval_logs/evallog_replay-f216-baseline01-w_1bbe329c.eval.log`；SHA256 `c8db008cd16894ca8bac4466fa80847b97ef802e22f02910fab8c033a15e62c3`。
- 原条件：`{"run_id": "f216-baseline01-w05-1", "source": "swe_gym_lite", "schema_id": "rh2.replay_grade_ledger.v1", "started_at_utc": "2026-09-18T20:18:13.395719+00:00", "image_ref": "xingyaoww/sweb.eval.x86_64.project-monai_s_monai-3715:latest", "image_digest_expected": "sha256:503ca39274e12c0aa0d06d0e77ad4f41628516a7b175feb4a5c10f940e2d1ab8", "image_id_actual": null, "image_identity": "sha256:503ca39274e12c0aa0d06d0e77ad4f41628516a7b175feb4a5c10f940e2d1ab8", "image_local_build": false, "derived_image_recipe": null, "scripts_digest": "sha256:56d3a76fcd8e956e3960c6d170247fe2b24142f99012d9625b6e684eb276590d", "baseline_policy_version": "baseline_policy_v2", "policy": {"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}, "budgets": {"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}, "resource": {"mem_peak_mb": 444.496, "mem_peak_unavailable_or_zero": false}, "resource_facts": null, "reference": null}`。
- 原安装/测试摘要：`{"install_rc_last_command": 0, "install_seconds": 7.477, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 0, "test_seconds": 7.325}`；报告：`{"execution_failure_evidence": [], "execution_failure_stage": null, "f2p_pass": 1, "f2p_total": 1, "failure_category": null, "grader_version": "swebench-4.1.0+swegym_parsers@242429c1", "grading_semantics": "swe_f2p_p2p", "infra_failure_detail": null, "outcome": "resolved", "p2p_fail": 0, "p2p_total": 1, "report_id": "rpt_grading_1bbe329c", "reward": 1.0}`。
- 投影：`{"frozen_patch_digest": "sha256:2f8dc84eda8a511939e7b26ac0abdcb625505a5fc87657e2d2d063a98d3137c1", "ignored_paths": [], "included_paths": ["monai/engines/evaluator.py"], "unsupported_shape_reasons": []}`；parser：`{"apply_ok": true, "num_parsed_outside_segment": 0, "num_parsed_tests": 2, "parser_source": "swegym_parsers@242429c1", "reference_missing": [], "reference_skipped": [], "resolution": "RESOLVED_FULL"}`。

所有资源字段保持原名与数值，未自行换算单位。source镜像inventory ID、期望manifest digest和实际grader image ID不可互代；3715/5686的实际image_id_actual为null。历史env_qualification=absent；实际actor工作树/消息、准备后status输出与RC/采集阶段、忽略资产、UID/HOME/cwd/PATH、源码导入、资产位置权限、网络与资源均unknown。没有用静态base干净代替这些事实。
