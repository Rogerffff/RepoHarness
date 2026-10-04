# 发布者交接说明

日期：2026-10-04。此处交付实施补丁和实验材料，不表示已更新共享源码、重冻 GPU 版本或启用生产开关。

[最终独立复核](codex_delivery_review_20261004.md)已完成：隔离重建及 44 项定向测试通过，两项原反例关闭，历史 CPU 证据与最终索引对账通过。审查结论限本地实现与历史 CPU 记录，尚未实施集成或部署。

## 应用对象

父版是实际 `runs/ordinary_gpu_probe_20261002/frozen_code_v8` 的 1046 文件快照，记录 Git HEAD 为 `a31cdcd0adb0fab3e681201edfb928653fdf5b3c`。补丁前置摘要以 [manifest](../../../../../runs/grading_performance_20261003/deliveries/rollout_v13/manifest.json) 为准；不要仅按 Git HEAD 或同名目录认定相同父版。

[代码补丁](../../../../../runs/grading_performance_20261003/deliveries/rollout_v13/grading_performance.patch) SHA-256：`66cc2dc69533482fe9e03c4dea5be12211acf4d4126f2af6dd2234ef40e503ea`。包含 11 个实现文件、7 个 CPU／Prime 实验入口与辅助文件、5 个新测试。应用前核对 manifest 的每个 `before_sha256`；新增路径应不存在。若集成树已有后续改动，应按语义移植并保留他人更改，再重新冻结，不能整文件覆盖。

最终 `rollout_v13` 包含两项发布者复核修正：Prime 取得并发槽后重查未知创建；可选计时读取异常只记诊断，不改变评分或覆盖原保护步骤失败，取消等 BaseException 仍传播。相对 CPU 接缝所用 v11 共改两个实现及其测试文件；原有 27 次评分均无计时读取错误，新失败分支由定向反控及最终回归验证。具体见同目录 `revision_from_cpu_v11.json`。历史 v11/v12 包保留，不是最新候选。

本片已在全新父版副本执行 `git apply --check`、实际应用、全部改动文件 after SHA 核对和未改父版文件核对；这些是补丁可重现性证据，不代替目标集成树验证。

## 开关与入口

- `RH2_GRADING_DIAGNOSTICS=1`：启用旁路分段诊断；默认关闭。原始 eval log 和 ArtifactRef 不改写。
- `RH2_GRADING_ORIGINAL_CONTAINER=1`：仅在 `fa_formal` 中显式启用原容器交接；默认关闭。实际镜像／profile 不兼容和满槽仍走原 fresh。当前 Pandas 实际 actor 与 grader 镜像不同，不能把 CPU 同镜像原型当作该真实任务已可采用。
- 权限和依赖模板：见 `rh2/experiments/grading_performance_20261003/run_case.py` 的 `--prepare-template`、`--prepare-repository`、`--prepare-dependencies`、`--template` 与 `--qualification`。生产 bringup 没有暗中切换镜像或跳过资格检查；本片证据使用明确的模板 manifest。
- 队列测试：`run_queue_benchmark.py` 的每个真实评分子进程分别申请现有公共 CPU 槽；不能把协调器包装成一个槽后隐藏并发。
- 原容器测试：`--in-place` 是 grader-profile 原型，`--rollout-handoff` 是真实 rollout profile／撤网／队列接缝。两者 solve 都是原固定成果夹具，没有模型调用。
- Prime：`run_prime.py` 默认只生成本地计划，`--execute` 才可能收费。需显式私有 key 文件、费用范围、核定的 SDK 环境、实际镜像发布绑定；当前均不得用假回执补齐。SDK 接口核对 commit 为 `3c7f8bf88df0b0da6c79d0992206cf5fabcf6888`，尚无线上运行结果。

## 验证复现

[验证测试补充包](../../../../../runs/grading_performance_20261003/deliveries/rollout_v13/verification_test_supplement.tar.gz)和 [其 manifest](../../../../../runs/grading_performance_20261003/deliveries/rollout_v13/test_supplement_manifest.json)保存了本次使用的 275 个当前维护测试文件。它们不属于冻结代码父版，也不包含本任务新测试。只在隔离验证树补充缺失文件，重叠路径保留真实父版，再应用代码补丁；不要将补充包覆盖到共享工作区。其中 4 个内容不同的重叠文件位于 `tests/envpack/`，均不在下列回归清单中；独立复核保留了父版，并在其重建回执中逐项列出。

从该树的 `rh2/` 执行，使用已有兼容依赖环境：

```sh
PYTHONPATH=src python -m pytest -q \
  tests/grading/test_in_place.py tests/grading/test_rollout_in_place.py \
  tests/grading/test_queue.py tests/grading/test_prime_backend.py \
  tests/grading/test_prime_manager.py tests/grading/test_performance_timing.py \
  tests/grading/test_manager_unit.py tests/grading/test_w3b_grader_profile_unit.py \
  tests/grading/test_e2b_grader_trusted_root_exec.py tests/grading/test_supply_cleanup_ownership.py \
  tests/adapters/test_slime_generate.py tests/adapters/test_budget_deadline.py \
  tests/adapters/test_w3b_sandbox_profile.py tests/adapters/test_w3b_bringup_sandbox_runtime.py \
  -k 'not disaggregated_template_pins_train_async_form'
```

本批结果：343 passed、1 skipped、1 deselected。deselect 的唯一原因是该冻结快照未携带历史 `experiments/s1_7a_bringup/container_train_disaggregated.sh`；未把该项记为通过。如果目标树有该文件，应按自身集成要求恢复检查。

CPU 固定输入、原日志、分段诊断、模板与完整 snapshot manifests 保存在 `runs/grading_performance_20261003/`，入口见 [当前结果](README.md)。输入沿用原 FrozenPatch；新增空补丁只用于派生 Pandas 镜像资格，不混入候选对照。

## 明确未完成的部分

真实 Claude Code／GPU 原容器 rollout、编译型任务推广资格、Prime 实际镜像发布与线上完整生命周期都未完成。当前未提高评分超时，未改变 reward 或错误分类，未把性能等价当作题目语义金标或训练准入。Prime 线上仍等待此前询问的账户文件与费用授权，不应创建资源替用户补答。
