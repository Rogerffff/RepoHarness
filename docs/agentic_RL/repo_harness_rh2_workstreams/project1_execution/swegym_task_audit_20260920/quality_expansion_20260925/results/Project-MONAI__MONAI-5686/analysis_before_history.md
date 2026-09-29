# Project-MONAI__MONAI-5686 历史释放前独立静态分析

封存阶段：2026-09-25；仅第一阶段。未读取任何 history/旧质量结论；写入后不修改。

路径约定：ROOT=`/Users/roger/Desktop/claude-code-verl-stage0h`；P=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-5686`；V=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/Project-MONAI__MONAI-5686`；O=`/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/Project-MONAI__MONAI-5686`。正文源码路径相对 P/base；原运行路径相对 ROOT。仅用只读文本/JSON/hash与限定源码阅读，没有执行项目命令、安装/网络/容器/GPU/模型、修改原题/评分或派生agent。证据分为静态推断与已存在的历史真实RH2，当前CPU/actor运行证据为无。

## 1. 公开目标、版本与初态

题面给出 x/y=[1,1,10,10] 的相同0.5图像，y.requires_grad_(True)，要求 SSIMLoss 输出 requires_grad=True。作为损失函数，合理语义是对需要梯度的输入保持真实计算图，而非只给无连接输出强制 requires_grad。base=`25130db17751bb709e841b9727f34936a84f9093`、版本1.1，与 V/grading 和历史 gold stage 对应；实际 actor 消息/初态 unknown。

base/ssim_loss.py:83–90 走 SSIMMetric.__call__，CumulativeIterationMetric:330 进入 IterationMetric:69–71 对两输入 detach。公开复现缺陷有直接静态根因与 no-op 双 F2P 失败证据。损失 docstring:69–74 另有 B=1,C=5 的 pseudo-3D 公开用例，不能把所有多通道都当未承诺的任意扩展。

## 2. 全部新断言、fixture/helper 及双向表

test.patch 添加模块级 x/y=[1,1,10,10]/2、y.requires_grad_(True)、data_range=x.max().unsqueeze(0)，构造 TESTS2D_GRAD。device 依据 cuda availability：CPU 条件为 None/"cpu" 两个参数化用例；有 CUDA 会另生一个用例。新增 test_grad 计算 `1 - SSIMLoss(spatial_dims=2)(x,y,drange)`，唯一断言 `self.assertTrue(result.requires_grad)`；没有 backward、输入 .grad、grad_fn/数值梯度或多通道。反转一次损失不改变该标志的意义。None 和 cpu 用同一个合成问题，不能按2项数目声称两个语义分支；没有新增 helper。

| 需求/旧行为 | 公开依据 | 具体测试/断言 | 覆盖/缺失/冲突及证据 |
|---|---|---|---|
| 题面单通道输出 requires_grad | user_prompt 复现 | F2P `tests/test_ssim_loss.py::TestSSIMLoss::test_grad_0`(None)、`…::test_grad_1`(cpu)，仅 result.requires_grad | 原条件两项均 noop fail/gold pass |
| backward 能到达输入 y | Loss 用途与题面 requires_grad 动机 | 没有对应断言 | 明确漏测；返回脱离输入、单独 requires_grad 的叶子也可满足标志要求，未实验 mutant |
| 两端输入、3D、多通道可微 | forward 的 x/y Tensor API；spatial_dims 文档；C=5 示例 | F2P 仅2D/B1/C1/y侧 | 部分缺失；gold 的多通道漏修可由调用链推导 |
| 单通道2D前向数值保留 | 旧 test2d | P2P `…::test2d_0` None相同图像≈1；`_1` None零图像≈0；`_2` cpu相同≈1；`_3` cpu零≈0；均 Tensor 且误差<.001 | 全部 noop/gold pass；仅常量两组，没有一般非恒定数值比较 |
| 单通道3D前向数值保留 | 旧 test3d | P2P `…::test3d_0` None相同≈1；`_1` None零≈0；`_2` cpu相同≈1；`_3` cpu零≈0；同一类型/容差断言 | 全部 noop/gold pass；没有3D梯度 |
| SSIMMetric 的评估缓存/aggregate 旧语义 | RegressionMetric.aggregate、IterationMetric.detach | 非本题 expected；公开 test_ssim_metric 对2D/3D与 aggregate 有断言，多通道 contrast 用例只检查类型/contrast | gold 不改 metric 公共入口；若合法解抽共用纯计算，需保留评估入口语义；这组未在引用日志执行 |
| batch>1、不同通道/非法形状等 | forward 文档/shape检查 | expected 均 B1C1 | 有限覆盖；现存 batch拼接缺陷不可偷记成 gold 新回归 |

全部 F2P=2、P2P=8 已逐一映射；当前历史收集10项，无 CUDA 参数项，因此不能报告 GPU通过。所有新增断言均有公开依据，不是隐含实现规范；主要是检查强度不够（check25）。

## 3. gold、合理替代实现与回归

gold 将 loss 内两次 SSIMMetric(...) 的公开 __call__ 改成 `_compute_tensor(...)`。RegressionMetric:78–82 保留类型/形状检查并直接计算；这确实绕过最外层 detach，对题面 B1C1 路径的卷积/四则运算保留图。没有改变公式、window、loss.mean 或 metric 公共调用者，也不需要累计这个临时 metric 的 buffer。

但 gold **不完整覆盖公开多通道损失用法**：C>1 进入 regression.py:329–345，内部列表推导在:338 又使用 `SSIMMetric(...)(channel_x, channel_y)`，重新经 metric.py:69–71 detach。若 data_range 按题面来自不需要梯度的 x，而 y 为叶子 requires_grad，所有子 SSIM 输出都没有图，stack/mean/view 无法恢复；B1C5 的 loss 仍没有 y 的梯度。此为静态完整调用链证据，尚无本轮 CPU 实测。它是 base 既有 bug 的残留/参考修复不完整（check27），不是 gold 从好变坏的新增回归（check26）。

另有 base/ssim_loss.py:87–94 的已有拼接问题：B>=3 时前两结果 cat 后含2个元素，第三轮对累计值 view(1) 不成立；B>1,C>1 时 ssim_val 也未必可 view(1)。gold 不改该逻辑，不能算新增回归，也不把整批次重写设为题面额外必需。空 batch 既有 ValueError 保留；半精度、data_range 向量、NaN等边界未检。

合理非 gold 路线：抽取不 detach 的纯 SSIM 运算供 loss/metric 共用；或从 loss 显式按 channel 处理再调用无 detach 的底层计算，保持前向均值与接口。无需从所有 metrics 全局移除 detach，否则扩大评估内存/缓存语义变化。当前测试不强制 `_compute_tensor` 调用形式；未执行这些路线，不声称普遍无误拒。

public_read 命令 A 有公开 API 与文档依据：原例 backward，以及2D/3D、C1/C3、两端单独梯度，有助区分 fake requires_grad。对其不同常量图像，非零梯度是特定选例的预期，不能泛化为所有图像每个元素必须非零；相同图像零梯度应合法。该脚本是提案，不是现有评分规范。

## 4. 原始历史评分、交付与可信恢复

引用 baseline01 w06-1 ledger 第3行 noop、第4行 gold，行hash逐一匹配 run_refs。实际 `pytest -rA tests/test_ssim_loss.py`；noop log:689–725,790–807 收集10项，8个前向 P2P pass、test_grad_0/1 均因 requires_grad=False 失败；gold:718–809 十项 pass。install末命令 RC=0，test RC=1/0，missing/skip=[]、区段外解析0，cleanup removed=true。无真实多通道/反向执行证据，满分只能表达这些参考断言。

安装链从日志核得删指定 git+ requirement 行、types-pkg-resources0.1.3/pytest、requirements-dev、setup.py develop；conda testbed 路径 Python3.8，parameterized0.9.0、ignite0.4.10，import 观测为 /testbed/monai/__init__.py。安装链分号导致末 RC 不代表每步骤独立 RC；未见定向 ERROR/重试，不因此宣称重建任意网络条件都成功。baseline-only 未单独定位当时生成脚本，未拿当前 manager 代替历史版本。

gold candidate.patch 的字节 hash 与 V/gold.patch 一致，stage 为 git_apply、HEAD正确；projection 仅含 monai/losses/ssim_loss.py，log:185–209 的实际 diff 对应两处变更。noop status clean/diff空、gold status仅 loss.py；这都为历史 grader 恢复可信测试前状态。log 的 git show 中 confusion_matrix.py 是 base commit 内容，不是初始未提交改动。trusted setup 恢复 tests/test_ssim_loss.py 并 apply patch，attestation restored=expected=present=1、absent=0、apply_rc=0、setup_ok=1；控制文件保护报告通过，runner hash 前后不变。源码修复可合法交付，无证据表明恢复误删答案；控制面攻击、完整投影实现/排除规则未独立审计。

## 5. 开发需求、资源与唯一下一步

| 操作/资产 | 公开依据 | 现有证据适用条件 | actor 缺口 | 最小公开命令/预期（未执行） |
|---|---|---|---|---|
| 确认实际源码初态及编辑权限 | P 提示、base身份 | 历史 gold可交付 loss.py；P只是Git导出 | actor HEAD/status/准备后差异、UID/HOME/cwd/PATH/权限 unknown | `git rev-parse HEAD`、`git status --porcelain=v1`；记录RC和采集阶段，保留来源改动 |
| Python、torch、numpy、MONAI/parameterized | requirements torch>=1.8、numpy>=1.17，min有parameterized | 历史安装、导入与10项评分完成 | actor 激活/导入源码与依赖版本 unknown | `python -c 'import sys,torch,monai,parameterized; print(sys.executable,torch.__version__,monai.__file__)'` |
| 原公开例真实反向与多通道 | user_prompt；loss.py:69–74 | 仅合成小tensor；静态证据，不需权重/数据集 | actor CPU/内存实际未验 | 在 B1C1 与 B1C5 上令 y.requires_grad=True、data_range固定无梯度，调用 SSIMLoss 后检查 requires_grad 与 backward 后 y.grad；完整修复应连接输入，gold静态预期C5失败 |
| 前向数值与指标行为回归 | 两份已读公开SSIM测试 | 历史只运行loss模块 | actor旧测试可用性未知；metric模块历史未验 | `python -m unittest tests.test_ssim_loss tests.test_ssim_metric`；前向/aggregate保留，但不能替代梯度连通性 |
| 网络/资产/GPU | 全部测试合成tensor；条件CUDA | 历史deny_all、cpus2.0/memory_bytes4294967296完成CPU分支 | actor资源、依赖供应路径unknown | 最小问题不需要网络/GPU；不能将未测CUDA写为skip失败或环境阻断 |

唯一优先下一步：在隔离私有对照环境，以公开文档 B1C5 例加 y 梯度做一次有目的的 gold CPU 诊断，同时记录 B1C1 对照、loss.requires_grad/backward/y.grad 与前向数值，确认静态残留并为决定评分/参考修订提供运行证据。不是全仓测试，也不需要模型/GPU；本轮只提出、不执行或另派。actor开发资格仍须另行核验。

## 6. 用途、暴露、检查编号和真正读取范围

静态 needs_review：验收没有验证输入梯度连通性，gold又留下公开多通道用法缺陷；可作 development_diagnostic，不能把现有满分当完整修复或训练/评测资格。与另两题仅同仓，具体base、行为和补丁不同；跨包重复/评测重叠未查。审查者见过 gold/test/原评分，不能做独立solver；未读history/旧结论/reviewer；实际 actor 历史/网络答案暴露 unknown。

稀疏编号：1、2、18–20 在指定版本/历史单通道范围 pass；3、6–8、10–15、30、33–36 unknown；4、9、16–17 对历史benign gold路径支持；23 静态规格合理；24 没有实现形式强制证据；25 issue（flag不等于连通性，缺多通道/3D梯度）；26 unknown（没有已证新增回归）；27 issue（gold多通道残留，静态）；28 不把所有梯度非零/全部batch语义扩成新门槛；29 issue（审查答案只限私有）；31–32 未完整对抗验证；37–39 not_checked；40 已保留静态/历史/actor层次。未列not_checked。

真正阅读：五份中性方法、本题O/public_read，P/user_prompt/public_bundle/base_identity/environment_brief及三份requirements全文；base/ssim_loss.py全文、regression.py:27–90,241–396、metric.py:19–100,260–336、test_ssim_loss/test_ssim_metric全文；针对monai/tests下SSIMLoss/SSIMMetric的rg命中行（包括两个__init__导出），未将搜索结果冒称全仓阅读。V/grading/test/gold/validation及run_refs/environment_record的本题字段；精确原ledger两行、两个diagnostics全文、gold candidate hash/projection/stage；日志status/diff/setup、安装命令/版本/错误检索和逐项失败/总结，未逐字通读全部依赖输出。第一次长输出中间截断，核心loss/regression和测试已分次复读。未读convert_to_dst_type实现、所有其它metrics、baseline_manifest全文、host_grading_view、归档代码、source_refs/history、其它ledger行/题包/旧报告/reviewer。没有项目导入/执行、测试、安装、网络、模型；本轮runtime/token/费用无观测。

## 附录：本题精确运行定位与原条件

源镜像tag：`xingyaoww/sweb.eval.x86_64.project-monai_s_monai-5686:latest`；期望manifest digest：`sha256:d3524dd2cbd2dcf1fb0cdc492b11cb143ed7a9b0269a711ec19425b1d4756269`。

### noop

- 原账本：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w06-1/ledger.jsonl:3`；选中行SHA256（不含末换行）`3e371ac388b3f3715619607ec56c91274332eab76f6d3d370b613e9d4007009a`。
- 日志：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w06-1/eval_logs/evallog_replay-f216-baseline01-w_8270b8b1.eval.log`；SHA256 `1952528ad44611a0f18f886d2883b69b4d4a18c734a173272fea94681f8602e8`。
- 原条件：`{"run_id": "f216-baseline01-w06-1", "source": "swe_gym_lite", "schema_id": "rh2.replay_grade_ledger.v1", "started_at_utc": "2026-09-18T21:07:37.867626+00:00", "image_ref": "xingyaoww/sweb.eval.x86_64.project-monai_s_monai-5686:latest", "image_digest_expected": "sha256:d3524dd2cbd2dcf1fb0cdc492b11cb143ed7a9b0269a711ec19425b1d4756269", "image_id_actual": null, "image_identity": "sha256:d3524dd2cbd2dcf1fb0cdc492b11cb143ed7a9b0269a711ec19425b1d4756269", "image_local_build": false, "derived_image_recipe": null, "scripts_digest": "sha256:538e47decf626343d421e958d14f877ac651f42182f009dff533c16cf843f13c", "baseline_policy_version": "baseline_policy_v2", "policy": {"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}, "budgets": {"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}, "resource": {"mem_peak_mb": 1001.273, "mem_peak_unavailable_or_zero": false}, "resource_facts": null, "reference": null}`。
- 原安装/测试摘要：`{"install_rc_last_command": 0, "install_seconds": 9.036, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 1, "test_seconds": 13.018}`；报告：`{"execution_failure_evidence": [], "execution_failure_stage": null, "f2p_pass": 0, "f2p_total": 2, "failure_category": "tests_failed", "grader_version": "swebench-4.1.0+swegym_parsers@242429c1", "grading_semantics": "swe_f2p_p2p", "infra_failure_detail": null, "outcome": "unresolved", "p2p_fail": 0, "p2p_total": 8, "report_id": "rpt_grading_8270b8b1", "reward": 0.0}`。
- 投影：`{"frozen_patch_digest": "sha256:d0d118186715af50561d4b34158e724b5e95f63e1cca984a4d2657008b6908d0", "ignored_paths": [], "included_paths": [], "unsupported_shape_reasons": []}`；parser：`{"apply_ok": true, "num_parsed_outside_segment": 0, "num_parsed_tests": 10, "parser_source": "swegym_parsers@242429c1", "reference_missing": [], "reference_skipped": [], "resolution": "RESOLVED_NO"}`。

### gold

- 原账本：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w06-1/ledger.jsonl:4`；选中行SHA256（不含末换行）`10d76e2fbef83290281cda88f5c3fe7269e12516f2d0e789decfbf12a85c62f6`。
- 日志：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w06-1/eval_logs/evallog_replay-f216-baseline01-w_2d0e37bb.eval.log`；SHA256 `292e0e3e3f30d71bc72bbb22106b03797998669ae90ce2ab43692ef41f4c47bd`。
- 原条件：`{"run_id": "f216-baseline01-w06-1", "source": "swe_gym_lite", "schema_id": "rh2.replay_grade_ledger.v1", "started_at_utc": "2026-09-18T21:08:39.188488+00:00", "image_ref": "xingyaoww/sweb.eval.x86_64.project-monai_s_monai-5686:latest", "image_digest_expected": "sha256:d3524dd2cbd2dcf1fb0cdc492b11cb143ed7a9b0269a711ec19425b1d4756269", "image_id_actual": null, "image_identity": "sha256:d3524dd2cbd2dcf1fb0cdc492b11cb143ed7a9b0269a711ec19425b1d4756269", "image_local_build": false, "derived_image_recipe": null, "scripts_digest": "sha256:538e47decf626343d421e958d14f877ac651f42182f009dff533c16cf843f13c", "baseline_policy_version": "baseline_policy_v2", "policy": {"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}, "budgets": {"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}, "resource": {"mem_peak_mb": 542.176, "mem_peak_unavailable_or_zero": false}, "resource_facts": null, "reference": null}`。
- 原安装/测试摘要：`{"install_rc_last_command": 0, "install_seconds": 7.914, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 0, "test_seconds": 9.657}`；报告：`{"execution_failure_evidence": [], "execution_failure_stage": null, "f2p_pass": 2, "f2p_total": 2, "failure_category": null, "grader_version": "swebench-4.1.0+swegym_parsers@242429c1", "grading_semantics": "swe_f2p_p2p", "infra_failure_detail": null, "outcome": "resolved", "p2p_fail": 0, "p2p_total": 8, "report_id": "rpt_grading_2d0e37bb", "reward": 1.0}`。
- 投影：`{"frozen_patch_digest": "sha256:2974bc4088942f9fae4d3d0b894118260a8d014a1f601179d5aaa992f6ad2ef2", "ignored_paths": [], "included_paths": ["monai/losses/ssim_loss.py"], "unsupported_shape_reasons": []}`；parser：`{"apply_ok": true, "num_parsed_outside_segment": 0, "num_parsed_tests": 10, "parser_source": "swegym_parsers@242429c1", "reference_missing": [], "reference_skipped": [], "resolution": "RESOLVED_FULL"}`。

所有资源字段保持原名与数值，未自行换算单位。source镜像inventory ID、期望manifest digest和实际grader image ID不可互代；3715/5686的实际image_id_actual为null。历史env_qualification=absent；实际actor工作树/消息、准备后status输出与RC/采集阶段、忽略资产、UID/HOME/cwd/PATH、源码导入、资产位置权限、网络与资源均unknown。没有用静态base干净代替这些事实。
