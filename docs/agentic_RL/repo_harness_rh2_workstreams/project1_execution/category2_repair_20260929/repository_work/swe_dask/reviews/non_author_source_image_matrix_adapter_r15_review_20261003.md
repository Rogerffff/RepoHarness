# R15 来源镜像矩阵 adapter 非作者窄核

2026-10-03。**新独立 helper 的来源镜像分支与冻结 R15 的身份校验相符，有限核查未发现具体放过缺证或错镜像的阻断。** 9378首个noop实际正式reward为0，137个参考完整，3F失败、134P全PASSED，安装与清理完成。该原件由旧helper产生，随后wrapper断言中止；**只接受这一个评分结果的证据，不授全矩阵、探针或训练资格，新helper的source CPU结果尚未纳入本核查。**

核查者未参与作者修改或本轮CPU运行；此前已接触私有gold/报告，不是公开盲审。仅写本报告和同名JSON；未进行CPU任务、SSH、Docker、网络调用，也未读取或修改其他仓库题材料。本机仅做内存格式反例与固定release纯函数重算，不执行安装/测试shell。

## 固定路径与字节

本轮起初在原路径读取的修正版已移至[独立v2 helper](../tools/cpu_formal_matrix_source_identity_v2.py)，SHA256 **`05080362f74eeba0cfacee4a51c2002a1806d2a387ee571bfb69ca695140e962`**（11781字节），与起初审到的字节精确相同。[旧helper](../tools/cpu_formal_matrix.py)现恢复原字节，SHA256 **`208430d5b5a87121c8473cb209858f95089e2716613325919028dcfa9d55c85d`**（10775字节）；不能把旧路径称为已修复。两版差异只有来源镜像inspect/留证、按local_build/source分别核账本、增加来源身份记录字段；原评分/预期分/负对照逻辑未因这次修正改变。

冻结R15为 `cat2-cpu-r2e089092-swe39-dask-monai-20261003-v1`，[release manifest](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe39_dask_monai_v1/manifest.json) SHA256 `2b788d1ce84228a27894e04886ade347e91993f48ddc9bdeeb8f92de4aa92917`。相关5份consumer/manager/materialize/profile代码已逐SHA及大小核manifest；manager SHA `1783533e1e3b66a57fcaa5a599a1da4f8e4e886318e24f040c6df91f294c1c1e`，replay SHA `715076023e58d12cfcbc974a48ec2e979aa889bf9877862bb2aaf75620414595`。不扩为重核R15全部1305资产或其他仓库材料。

## 来源分支是否保持证据要求

旧wrapper把派生镜像专用的 `image_id_actual=configID` 断言用于全部题。R15 replay在source分支将该字段保留null；其有效身份是冻结manifest digest，故旧断言与该表示方式不相容。新helper保持local_build的精确configID检查；source只在 `image_id_actual is None`、`image_identity=image_digest_expected=spec.image_manifest_digest`、`image_local_build is False` 时继续，缺字段、错digest、非null实际ID或错误分支均不会静默接受。

新source prepare先在固定槽内对tag做一次image inspect，要求一项输出、Id精确等于config且RepoDigests命中 `@` 后的冻结digest，将原始JSON保存为 `source_image_inspect.json`。命令失败、空/重复输出、缺ID或RepoDigests、错值、损坏格式均中止，不生成通过矩阵。`formal_binding.image_id`和新 `source_config_id_inspected` 描述的是prepare时tag inspect的config身份，**不是运行中容器configID**，也不补填ledger的null字段。

决定实际评分容器身份的是[R15 manager](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe39_dask_monai_v1/repo/rh2/src/repoharness2/grading/manager.py)：启动容器后先读取该容器的 `.Image`，再用这个实际ID读RepoDigests，命中冻结manifest后才checkout/安装/测试。查询失败、空清单、损坏JSON或错digest抛 `GradingInfraError`；helper还要求stage正常、完整测试/参考及无infra详情。初始tag inspect没有替代这个逐容器校验，因此tag后来漂移到错manifest不能靠旧inspect回执放过。正常Docker RepoDigests格式下，新helper的 `endswith("@"+digest)` 与manager的 `rpartition("@")[2]==digest` 判据相符。

有限本机检查直接取050字节的两个AST分支，用内存mock替代所有subprocess：18项正/负格式检查符合预期，包括source错ID/错digest/缺字段/空或多项inspect、row缺字段/错identity/非nullID、local_build错/空ID。另调用R15原 `_verify_image_digest` 方法，以mock Docker结果核7项：匹配通过，容器inspect失败、错/空/null/损坏RepoDigests及查询失败均拒绝，第二次查询确实使用第一次返回的容器Image。**25项有限检查不是实际Docker/CPU验证，也不扩大为共用grader安全审计。**

## 9378首个noop原件

[terminal readback清单](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask9378-formal-cpu-c-20261003-v1/remote/readback_manifest.json) SHA256 `c73858cd16fe9fb6174c57c073cbc1893b46d165f5de6987950d886a7308bdbf`。逐SHA及大小复核 **25/25原件、297126字节**，零不符、无排除；完整清单见JSON。原件路径是 `dask9378-formal-cpu-c-20261003-v1/remote`，不是新helper的v2运行。

[正式ledger](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask9378-formal-cpu-c-20261003-v1/remote/run/noop/ledger.jsonl) SHA256 `f9a59b8dcfe6973a6587755716177734a6935936a520ab4f2d251130cb0c4a44`；[eval](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask9378-formal-cpu-c-20261003-v1/remote/run/noop/eval_logs/evallog_replay-dask9378-formal-c_0725faa2.eval.log) SHA256 `96c971374f2ae14e4a4370aafa9b47d334b4b227cd2af907d3470cb8476884ab`。唯一Start/End顺序正确，区间内直接逐项读取137参考，全部在场、无跳过：empty_like/zeros_like/ones_like三个F2P均在实际mask比较断言失败，134P全PASSED，summary为3 failed/134 passed；reward0是正常测试失败，不是wrapper断言或基础设施故障制造的0。

安装确实执行原 `python -m pip install --no-deps -e .`，成功安装dask，安装rc0、无失败命令、未跳过；实际Linux Python3.10.14/pytest8.3.2。测试rc1，外层exec rc0，段完整且无partial。账本补丁应用身份为agent54321、评分安装/测试为54322，与冻结agent_ws和manager候选exec的 `-u` 路径相符；本source题无额外geteuid前置probe，也没有单独id -u原件，不能声称存在。root受信setup负责materialize/基线/测试恢复和权限布置，不是候选安装/测试身份。实际导入观察指向/testbed/dask，运行器前后摘要一致；观察只是辅助证据。

noop导出为空；ledger记录候选容器 `removed=true/rm:ok`。grade最终回执记录grader created1/removed1、无open container/supply或cleanup failure、final_status退出0。峰值观察4096MB接近4GiB限额，不能据此声称其他候选有资源余量；本行测试与清理完整且无infra失败。

实际source身份仍为 `sha256:d59dc8d2aa23abc26c301754af4623f7bbad5d798713a6c5caa2d2113b6691b1`，`image_id_actual=null` 原样保留。旧formal binding里的 `sha256:1e5a0ee850161b35d33d26445f73e872488a45e0e436195af239190b68574096` 是config预期，**25原件没有source image inspect输出，不称其为独立取得的实际容器configID**。运行中manifest校验通过的判断来自冻结R15强制调用顺序、无infra失败及完整评分；原件未单独保存两次Docker inspect的raw stdout。

通过R15模型和渲染函数本机只读重算：source spec为False/无local_build_id、digest和300秒setup符合原binding；host JSON SHA `d4293f4ea9838a313bd9e09eb6b21d53211784d83a8a0e214ff73504876381d4`、材料identity `sha256:2823a332c83a6a37ce56e3cb1816fa7d267788b4616b28f76be8c4896fc915c4`、scripts digest `sha256:973844ec7101c4754a1a0d3ca73815717f75430a80a494d0dcb1d184f68bac69`、有效补丁SHA `9fc1a9d5ae885d9cc30388a875ab7ed629081de7ba7bdcc8571f3aca604a248a` 全吻合本轮原件；不重审mask题目标。

[run/status](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask9378-formal-cpu-c-20261003-v1/remote/run/status.json)显示verify/prepare/grade_noop三步退出0，随后 `AssertionError()`、`stopped_needs_diagnosis`，formal_rows为空。terminal退出1保留，不回写成矩阵成功。旧208代码的无条件configID断言与实际null不符，解释该中止；不存在gold或其余行的实际证据。

## 尚缺验证

新helper的source CPU结果未纳入本报告；当前25原件没有它新增的inspect文件，内存检查不能替代新路径实际运行。父线程告知不可变快照 `c58d4ad6fd35eab8` 已启动、仍含050修正字节并使用snapshot内原相对名，没有热改在途；本审查未读取新运行，不能把“已启动”写成“已通过”。未来新launch应指独立v2路径。

完整矩阵回收后，须另核新source inspect原件、每行正式consumer/材料绑定、正负对照、137参考、安装/评分和清理。现有首noop实际0可保留，不能授全矩阵资格。旧路径208保持原件，不称已修复。逐件SHA、有限反例和137项实际状态见[同名JSON](non_author_source_image_matrix_adapter_r15_review_20261003.json)。
