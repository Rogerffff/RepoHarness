# EA69 R17 启动前非作者静态窄核

2026-10-03。**静态窄核通过，无必须修正项；尚未验证实际 CPU。** 本报告只覆盖本题 R6→R17 身份差异、既有 wrapper 的冻结父入口及两份启动脚本。未执行 SSH、Docker、安装、模型或项目测试，不是 fresh 公开读者，也不授训练资格。此前报告和原件未覆盖。

## 发布及本题身份

发布 receipt 摘要为 `0a4ff5bc6992eed0e27f1d007af718b2086b3928fc71732375093e3da0b3de0d`，R17 manifest 为 `76aee53151d3b58758d00a9feb5a901b720b4b430f37d2057ed07c1ef0ce2fa6`，均与指定值相符。发布成功不代表题级 CPU 已通过；已有本地 dispatch 为 rc75，status 原件为 `not_admitted`。此处不推断后续实时状态。

独立逐字段比较旧 R6 与本地 R17 的本题 public、private 和 prompt 原件：

- public payload 只改 `problem_statement` 及其 SHA。Expected Behavior 增加保留既有用户内容、确保所有生成报告被 Git 忽略并在重复生成时成立的说明。新题面与发布 statement 文件逐字相同，SHA 为 `39b6b28abc08b21a76a71d8908a7e37a00040cbfc3f9d92ee12bc37b3b6a194f`。
- private grading payload 只在 `material_revisions` 增加 `r2e-mr-093`；073/074/075、全部 hidden 文件内容、runner、expected map、parser/normalization/source/base 字段完全相同，仍为49键。没有改变授权验收目标或降低评分要求。
- environment payload 只有关联 public/grading digest 变化；源镜像、manifest digest、base及其余字段一致。R17 public、grading、environment digest分别为 `sha256:53deb1de7539fb7dfb1150fbe52957a29ee0f69d35f68f9796a53aa787ebdcc0`、`sha256:46de14f5ca6fc9adcfff2fcac483c05d98fc8a9e29d1286e66867a3a463566c8`、`sha256:8fb9b7e14b7e0e28030bc1d8e49d9a51b5620231a445c44d6be104c0016f85a9`，已按固定 canonical JSON 算法重算。
- prepared prompt 的完整差异恰为新旧 statement 替换，其余模板相同；prepared manifest、public/prompt 文件和host artifact摘要与summary逐一相符。该本地静态prepare证明消费身份，不证明CPU-C实际消费。

## 冻结入口及启动脚本

R17 的 E2E、R2E solve、base solve 与此前审查字节相同。replay、builder、stub、gateway、result_validity、frozen_transport、budget及env_pins与R6字节相同。两份 wrapper 和 scenario 也保持此前通过静态核查的版本；`EmptyPublicDelivery`仍在评分前核原候选摘要与FrozenPatch空entries，未改评分或候选。

`launch_prepare_r17.py` 和 `launch_narrow_r17.py` 的外层及嵌入 BODY 均通过AST语法检查。它们只用原 `control/cpu_slot.py` 的prepare/run模式、本包固定job；共享2槽、prepare最多1仍由原入口管理。没有另造调度或绕过slot。prepare使用固定R17、全量release验证及最小packet逐SHA核对，在新目录只prepare EA69；源镜像按固定RepoDigest拉取，核linux/amd64。原builder直接使用digest基线，因此`--skip-pull`无需依赖来源tag另行存在；仍用sysconfig及固定env_pins、2CPU/4g/512pids。facts必须ok且recipe为原 `r2e_derive_v1+material_v2+sysconfig_v1`、`sha256:85b488e5c8a0078f952842c9f5a12f7f949b51029c3f3c80f3f0fec4b14cbb0b`。

narrow要求对应prepare完成且返回0，核derived镜像实际ID、固定CC包、题面/public/grading/hidden/runner/49键及recipe，再检查本题已分配18210/18211可bind，调用原已审wrapper。原求解、导出、正式noop、往返和清理不变；没有加入gold或私有候选方案。两段BODY都拒绝`python -O`/`PYTHONOPTIMIZE`，wrapper的assert身份门保持有效。

最小包只有7项已声明输入及packet manifest，归档每项SHA、大小、当前源码、packet内容全部一致；传输回执绑定同一tar摘要。实际远端读取字节须在运行原件回收后对拍。R17没有打包`ordinary_gpu entry.py`，它仅用于此前prompt公式比对，wrapper并不import它，因此不构成缺失依赖。

| 工件 | SHA-256 |
| --- | --- |
| prepare launcher | `f4880b892f524596ac8cbd560f1af9a524149a894acea0c56ada749b0804c652` |
| prepare远端BODY | `cc6a40639bd86a2fdf70a45a3b4789f3379f3ed0dab71f50d98c6423520861d3` |
| narrow launcher | `e66764549008a8dc396735cfb76e09710785d703986cdc30e6f53e36dc1a6607` |
| narrow远端BODY | `7d2ab2dac70f068676478410adc1acc9d5f3738abaeb4058b37778e4e842e010` |
| 输入packet manifest | `b83480ffc46c832fb48045b974e74b4701839dd4a809913d91aee5f954781bbb` |
| 输入packet tar | `88070ff558952f1544632d1a942080d886faa4d8360396b0bce22fddddcafd5a` |

## 复用及未关闭范围

R6七候选矩阵与实际空noop仅在私有payload、源/配方不变范围复用；公开交付变化仍须R17实际CPU窄验。发布者共享32字段/264题核查按版本复用，本报告不重新审其他题。

尚未核R17实际镜像、真实首`messages_000`中的完整新题面和brief、公开compat命令46测试、空FrozenPatch、49键noop、运输往返及清理。实际运行完成后应独立核一次原件，保留原分数与所有失败证据，再决定普通探针用途。静态通过不替代该回执。

完整证据SHA及差异字段见[同名JSON](non_author_ea69_r17_pre_run_check_20261003.json)。
