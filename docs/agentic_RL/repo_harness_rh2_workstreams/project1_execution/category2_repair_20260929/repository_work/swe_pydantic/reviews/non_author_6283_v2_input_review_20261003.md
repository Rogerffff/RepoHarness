# 6283 v2：R19 实际固定输入的非作者增量核查

2026-10-03。**实际固定输入的静态身份核查通过，没有新增输入阻断。** 本报告只核收 R19 发布／固定输入／本机 prepare／待上传载荷的连接；四行41参考 CPU、真实 PrivateAttr 观察及旧 GPU FP 安装修复后重评分仍未执行。**本包 CPU hold 仍在，上传也未核收；本报告不解除 hold，不授予派发、CPU／GPU就绪、模型完成或训练资格。**

我不是材料、runner、生成器或 helper 作者；此前已接触私有测试、gold／负对照、原 Qwen FP与旧评分，不是 fresh 公开读者。复用[v2 材料窄核](non_author_6283_privateattr_v2_material_review_20261003.md)及[runner／生成器静态窄核](non_author_6283_v2_runner_static_review_20261003.md)，不重审题义或重跑旧矩阵。本轮只读、hash、JSON、AST和tar内存读取；未执行作者 helper、SSH、Docker、pytest或模型。仅写本文与[JSON](non_author_6283_v2_input_review_20261003.json)。

## 发布与固定入口

R19 release 为 `cat2-cpu-r2e093-swe40-pyd6283-moto6114-20261003-v1`，manifest SHA `2cfdd9b4f1134c0915346b727b729665482c4c1121b550764833f16f2982402e`。[实际发布回执](../../../../../../../../runs/category2_repair_20260929/publication_cpu_takeover_20261003/r19/pyd6283_publication_receipt.json) SHA 为 `3419c89f38455ead83b329d9255d8c04cab4c39422133623a40a187c850863a9`，记录 cpu-a 部署、safe_closed和题级 CPU未由发布者运行。

复用题主[owner readback](../coordination_20261003/6283_v2_r19_publication_owner_readback_v1.json)对1476成员大小／SHA／精确集合的完整核查；本轮没有机械重hash全部1476。独立重核其七份绑定原件的大小与SHA、manifest的1476项计数，及本题三份published bundle、独立v2 registry和四份必要consumer源码，共八个release成员。部署回执的48 R2E＋216 SWE是注册消费任务数，不能当作264题实际通过数。

| 固定入口 | 字节数 | SHA-256 |
| --- | ---: | --- |
| [formal_inputs.json](../cpu_acceptance_20261003/6283_privateattr_v2/formal_inputs.json) | 23289 | `4d50c69969e883e48f919ac1221594d88665e409a720f67b9a16952c393b4640` |
| [run_formal.py](../cpu_acceptance_20261003/6283_privateattr_v2/run_formal.py) | 23684 | `40b0460b70c2890a1eb3fbbf2474e10bee906125e3068868079370044d875805` |
| [upload_manifest.json](../cpu_acceptance_20261003/6283_privateattr_v2/upload_manifest.json) | 2278 | `42331860972b15eb9e3f7ee5947fb5a8be3d9fc9f3ee6be01401ac16a5a11314` |
| `6283_privateattr_v2_inputs_v1.tar.gz` | 18292 | `e4cfa59f7e3a74219ecc42eedf57c65ad2247ed8bce708123add218bd4825f86` |

输入只含6283，release ID／manifest／1476计数与实际回执一致，public／grading／environment文件SHA各自吻合。当前正式publication材料清单的15项全部大小／SHA吻合，已包含README及两份原材料审查；上一轮draft清单不含README的同步条件已落实。runner及生成器SHA仍与已审版本一致，未扩展它们的静态结论。

## 原参考、候选及公开 actor 复用

固定输入、当前revision、published grading和本机host grading逐项一致，均为 **2 F2P＋39 P2P＝41**。与旧 R7固定输入相比，两个F2P原序完全保留，P2P前38项原序完全保留，只在末尾增加 `test_root_model_construct_preserves_private_default`。无重复或分区交叉。有效补丁SHA为 `30037d927f57145f7c0a80281e60861000183d10ae20e4bf10c03bcd8f5c7cde`；应用后的测试文件SHA `6bb8bce7277436102efc2bb43a61dcddd2ccf9830730b7e3026b7add680129e8` 与上轮独立内存应用一致，本轮不再重做该应用。

四份patch与已核副本SHA相同；重新hash公开base三个生产文件，并复用上轮精确应用产物，核四个候选的完整 `source_sha256` map一致。三个imported module固定为main、root_model、_model_construction。Qwen root源码仍为 `2e8b2748bea649c5bde853049ba9255d62dd6eb033ad9c979dac90765f644b44`；这绑定原diff的源等价CPU负对照，**不是原GPU FP重评分**。

| 候选 | 正式参考预期范围 | 整题预期，未运行 | supplemental预期，未运行 |
| --- | --- | ---: | --- |
| noop | 两F失败，39P通过 | 0 | normal／construct均abc |
| gold | 全41通过 | 1 | normal／construct均abc |
| validate_construct | 两F与新增P通过；原test_construct／test_construct_nested失败，五项required_statuses | 0 | normal／construct均abc |
| qwen36_a1_pop_private | 原40通过，新增P失败 | 0 | normal abc；construct TypeError |

validate_construct其余参考仍由runner要求全部有PASSED／FAILED终态，不能把五项required_statuses当作全部41无附带回归的证明。所有预期合法、指向本题参考，补充观察不改formal reward。

公开actor复用的七项条件——base、public digest、base／derived镜像ID、core、安装资产SHA及完整配方——与已绑定的旧 R7输入逐项相同。公开cache与新published public对应字段完全相同，canonical public digest仍为 `sha256:d2d8b998296f14d164a024519603119def49bbc9ba84fad05b7a5c0eebceddc5`。

复用[旧CPU非作者审查的公开actor边界](non_author_6283_cpu_review_20261003.md)：旧actor由固定桩驱动预定公开命令，支持公开开发／CC交付／收尾证据，不是模型求解、私有新节点、FrozenPatch导出或全启动隔离验收。本机prompt行仍只含issue；public_hints完整保留在public view，未写入新增私有节点名。这里核身份等价并保留旧证明范围，不冒称看到新CC首请求或完成新actor实际运行。

## 本机 prepare 与新 spec join

独立核保存产物的完整SHA链：

- prepared manifest：`2b6b38174236aab489d5a6e227f0bef840245e4b3ef653887dc2c46a4cd25bfa`；两份公开prepared文件各一行，字节SHA和manifest计数一致。
- private host grading：`ec519cb476c029291fb54ca1c0843dc8f757d0870476865dada2d4daded5a83b`；唯一grading对象与published grading逐字段相同，公开view也与published public相同。
- 重算grading digest `sha256:1a01c6c5461210695e2441d7a20528a2323551b447d11684bc416cde3cdba2e4`、environment digest `sha256:ea8586e7aea5d42013865e38b2a442fad8cf75de61723535022af01f06ce6263` 与prepared／host／environment package／spec一致。
- 按已发布公式重算materials identity `sha256:6cbe982fee845a107fc907790183c7b825e65508cdd017f86e59f41261498131`，与spec一致。独立v2 registry SHA `c5d14877f146f41c68fb56b1eab57382d4afde4bfeba8250449527fec2858b0f` 与诊断pin一致。
- 七份保存脚本SHA全部与status一致；eval／trusted_setup内嵌完整有效补丁逐字吻合，三个安装脚本内的E10配方逐字吻合。安装资产仍为 `6e50864b8f8976413f6fb32df2fd11060e1b190fb4161c8567810ac748e6a570`，安装文本SHA也独立重算一致。

spec参考分区为1原F／1既有新增F／38原P／1新P。revision仍是 `not_evaluated`，apply_ok与各分区result均为None。状态 `local_prepare_identity_join_passed_not_cpu` 证明本机消费身份连接，不证明目标Python3.8／core0.42安装或PrivateAttr实际值。actor／host相等记录覆盖runner的spec_record子集；发布者32个完整GradingEnvSpec字段比较证据保留其来源范围，本轮没有再执行全字段比较。

当前预算实际记录 **reset300／apply120／test1800秒**。R20的8316／9395 reset900设计不适用于本题；未把300秒保护延长。系统Python首试缺harness依赖pydantic的失败JSON及空目录均保留；它不是候选安装失败、任务pytest失败或题级0分。后用既有rh2/.venv -B成功由题主交接，本次只核产物；status本身未记录解释器身份，未包装为新依赖实测。

## 显式 derived 镜像与运输／派发边界

实际R19 published consumer保留source默认ref／manifest。6283不在四题自动固定grader installation枚举中；新runner通过 `DerivedImage(ref=c['derived_id'])` 显式选择 `sha256:58d0c004cec144834a01dfc160c0f4caf427a9b31fd5ad95a60d03f6f3623226`。已发布replay源码在6283明确derived时令spec manifest为None、local_build为True，并令ledger `image_digest_expected=None`；未选择derived时仍保留原source manifest。后续实际inspect／container／FP身份仍须核原件，本轮没有新ledger或容器。发布者现有镜像readback是只读供给身份，不是任务CPU或actor资格。

上传manifest列 **10项载荷**：runner／formal_inputs及八项私有资产。逐项与本机文件大小／SHA一致；tar包含这10项加manifest自身，共 **11个普通文件成员**，精确集合、每项完整字节与本机文件均一致，没有额外路径、符号链接或路径穿越。仅在内存读取tar，未解包或执行。该包仍待上传，当前没有upload owner readback，不能把本地tar核对写成远端运输验收。

五份helper当前SHA及AST保留在JSON：local_prepare只调已核prepare；packager使用排他创建；上传verifier为一次性精确集合／大小／SHA核查；archive只接收本namespace已结束的job，并追加独立v2 pending-review索引，非零／异常记录不转为任务分数。它们没有改原GPU FP／原分的路径。本轮未执行任何helper。

dispatch guard要求本报告JSON的 `actual_frozen_input_review_passed=true`，以及**裸SHA** `formal_inputs_sha256` 与当前输入字节一致，另需actual upload owner readback。通过这些条件后仍检查本机 `cpu_sequence_hold.json`／`cpu_infra_hold.json`；任一存在即rc75 deferred，远端调用之前停止，不自动重试。当前cpu_infra_hold实际存在，本次没有删除或修改它。archive“finished”状态也不能代替成功清理／全参考通过的非作者原件验收。

## 当前用途

本JSON可作为**实际固定输入静态审查**的guard证据，绑定SHA `4d50c69969e883e48f919ac1221594d88665e409a720f67b9a16952c393b4640`。其他ready字段保持false，CPU hold仍在。

既有下一步仍是：核收真实上传，按共享CPU支持恢复回执处理hold，然后四行41参考正式安装／日志／补充PrivateAttr观察、FP和完整baseline运输及两层清理，最后非作者运行验收。旧GPU install RC1、raw1及原FP历史继续保留；源码等价CPU负对照、发布、prepare和本次静态通过均不能替代旧GPU重评分、模型完成或新GPU准入。
