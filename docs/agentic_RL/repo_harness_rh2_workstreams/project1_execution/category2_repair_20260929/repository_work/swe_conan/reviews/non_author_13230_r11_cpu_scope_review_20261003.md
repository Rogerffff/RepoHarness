# Conan13230：R11 正式 CPU 语义与范围复核

2026-10-03。角色：非作者 Falsifier / Simplifier。沿用本批指定 GPT-6.1 Sol / high。

## 结论

在本次限定证据中，未发现阻断 Conan13230 **正式 CPU 矩阵验收**的问题。固定 R11 发布材料已被正式评分消费，新增两个 Linux 节点实际执行，完整 noop / gold / Android-only 的 reward 为 **0 / 1 / 0**；原 Android F2P 和 34 个 P2P 保留。没有把静态预期、私有诊断或公开 recipe 的观察异常替代为此次正式结果。

此结论支持题级正式 CPU 证据验收，不自动批准普通 solver 探针或训练。公开 brief v2 的显式 SDK 配置路径可复用旧 actor 的已验依据；**v2 完整题面已交付给正式 solver 尚未验证**。本次 formal replay 的 prepared prompt 不包含 v2 的新增占位路径，旧 scripted actor audit 也明确没有建立完整公开题面交付。

## 阶段与读取边界

这是主审查者明确授权私有 CPU 阅读后的第二阶段。首次公开读者报告及 v2 增量报告保留，没有回写，不能将本阶段看到的 gold、私有测试或运行结果冒称首次公开盲审已知。14177 的运行结果不在本次范围，没有核查。

新增读取范围：

- `runs/category2_repair_20260929/conan_cpu_20261003/formal_matrix_13230_r11_v2_evidence/formal_matrix_13230_r11_v2/`：计划、发布输入/回执、驱动、prepared 视图、候选、三方账本/冻结产物、正式原始 eval log、diagnostics、阶段退出记录。
- 同级 `formal_matrix_13230_r11_v2_remote_audit.json`：作业终态、55 个导出文件的 SHA/大小以及本批精确 run label 的清理读回。
- 固定 R11 `runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe17_dask_conan_v1/`：manifest；`checks/consumer_combined_264.json` 的 13230 consumer 值；`repo/` 内 13230 修订材料、`prepared_task_face.py`、正式 replay 模块/脚本和 `grading/material_revision.py` 的相关消费路径。文件名检索用于定位，没有核其他题的 consumer 内容或测试结果。
- 固定回执 `runs/category2_repair_20260929/publication_cpu_takeover_20261003/r11/conan13230_publication_receipt.json`。
- 当前 13230 `card.md`、固定 `publication_request_20261003_v1.json`，以及此前 `reviews/non_author_material_review_20261003.md`。后者的原参考保留与接受范围静态结论作为已有依据，并对正式修订字节/旧函数 AST 再核；没有重做其他题材料审查。
- `baseline_actor_13230_v2_audit.json` 及授权 evidence 中 `output/captures/identity.out`、`public_profiles.out`、`public_regression.out`、`output/prelaunch.json`。主审查者补充的 `baseline_actor_13230_v2_evidence/baseline_actor_13230_v2/` 子目录在本地不存在；实际原件位于已授权 evidence 根的 `output/`，已向主审查者说明。
- 必要复用首次已读 13230 公开 base 与 brief v2，用于整份候选的内存应用比较及公开命令语义判断。

本次不访问远端、不运行 Conan/pytest、容器或历史实验，不读取题级 `result_manifest.json` 或扩大 SDK 范围。仅使用本地 stdlib JSON/SHA/AST/内存 patch 校验；唯一新增文件为本报告。此前三方私有诊断无需再读，因为正式原始结果已足以裁定本次问题。

## 正式消费与材料身份

固定 release ID：`cat2-cpu-r2e089092-swe17-dask-conan-20261003-v1`。独立计算本机 manifest SHA 为 `bf1d0e8a279f996a7737de775c9a30abf3401dc34840ef54bf7e56b754991bb9`。本次相关 9 个消费/修订文件的摘要均与 manifest 一致；不将这项窄核冒称独立重审全部 980 成员。阶段驱动原件则在运行前核了全部成员，`release_verify.rc.json` 为 0。

固定回执与 formal 阶段保存的回执逐字相等，SHA 为 `8e4a2d59eb6b06d35b681e5a89570e7f7a5c6a87fdd251937bf1e5ee18c3adb3`。13230 consumer 行与 `plan.json.consumer_identity` 完全相等。准备后的 host grading view 与固定修订中的有效补丁逐字相等；F2P/P2P 数组与 publication input、plan 逐项一致，F2P = 3、P2P = 34，无重新分组。

关键身份：

| 对象 | SHA-256（省略 `sha256:` 前缀） |
| --- | --- |
| 原测试补丁 | `7bae4492595c23d2c4bf274664ebc3a2d65d8b5d87526299f3fc408b65186a90` |
| 有效测试补丁 | `15834b7e16c8fac6c5386c5ebf1f6ad1df9ad56c67af1c87df6a178f6e374db1` |
| 有效测试文件 | `0657560b1a7ad50485b62b825e241182fcd6ceee2005c6b5137998d6e19422ff` |
| 修订 registry | `a77762545641e664bedd6eed0d9c041257da1aee08fbc5b8da63d191e5835b70` |
| 正式 grading bundle | `0ef6056f3b8e7ae42d5e06dd169afd46a46e5f41594e50188a3845eaaf49822f` |
| 正式 grading materials identity | `c19c5f0f18836b70f99718f1a7afb4ceb11b3cca974b5e4413489045b21b80e2` |
| 公开 bundle | `bc74aee04e62ec6ff8f4913d183afe140d7a0a932287d9836ad4909d7f2c04f4` |

正式路径为：固定发布包的 replay CLI → prepared HostGradingView → `build_grading_spec_from_host_view()` → 完整候选 `git apply --check` / `git apply` → FrozenPatch 导出及受信投影 → `SWEGradingManager.grade(workspace=None, frozen_delta=...)` → 受信恢复/应用有效官方测试 → vendor 测试命令 → SWE-Gym parser → 原/新增参考分区与 report。

`run_matrix.py` 中的 expected reward 只是 report 产出后的断言，不是评分输入。正式 replay 模块第 406–450、683–708 行消费候选并提交冻结内容，未见按候选 ID 造 reward。评分 spec 中 parser 捕获 grading view；测试命令为 `pytest -n0 -rA conans/test/unittests/client/toolchain/autotools/autotools_toolchain_test.py`。三方 trusted setup 的恢复/应用/保护均成功，runner 摘要前后相同。

## 原始结果与评分对账

本地逐一计算 55 个 formal 导出文件的 SHA/大小，全部与 remote audit 相符。三方原始日志的 `PASSED/FAILED` 完整 nodeid 集合均精确等于正式 3F + 34P，不缺席、不跳过、不混入标记段外节点。

| 完整候选 | 原 Android F2P | 新 Linux 无 SDK | 新 Linux SDK 哨兵 | 原 P2P | 原始 pytest 结果 | 正式 reward |
| --- | --- | --- | --- | --- | --- | --- |
| noop | 失败 | 失败 | 失败 | 34/34 通过 | 3 failed, 34 passed；rc 1 | 0 |
| gold | 通过 | 通过 | 通过 | 34/34 通过 | 37 passed；rc 0 | 1 |
| Android-only | 通过 | 失败 | 失败 | 34/34 通过 | 2 failed, 35 passed；rc 1 | 0 |

三方 driver process rc 均为 0；候选安装 rc 为 0，正式测试段完整，`stage_error=null`，`reference_missing_count=0`，分区的 missing/skipped/unaccounted 均为空。noop 与 Android-only 为 `tests_failed`，gold 无失败类别；没有 infra 判定。三方容器移除成功，阶段精确 run label 的容器/网络清理读回为空。这里没有将 driver rc 0 误作测试通过。

gold 原件 SHA 为 `c77c7fa0aca6eecc6acaff2f21a23eeef23443c13467057b1367527ddfece7f7`；Android-only 为 `8d99fdcef2c400cf07c11e26de93af78f62030a2594c2ae6d86aac45dd4583fe`。分别将整份补丁在内存中应用到公开 base，所得生产文件与对应 FrozenPatch 的唯一 modify 条目逐字相等，也与其 content digest 相符；阶段候选与保存的 `candidate.patch` 逐字相等。noop 为零条目。三方 `excluded_pathset_changed=false`，没有候选裁剪或候选被替换的证据。

## 是否漏判、误拒或扩大题义

原测试补丁应用后的 21 个公开/原回归函数，其 AST 在有效测试中逐项保留，包括 Android F2P；正式 34P 数组与固定请求的原数组相等。新增两节点使用题面最小 recipe 的 os/arch settings：host Linux/x86_64、build Macos/armv8。原材料审查已解释该最小设置下其他 flags 来源为空；本次没有把所有 Linux 工具链都约束为空。

新增断言检查公开 `cflags` 与导出的 `CFLAGS`，没有规定修复必须修改哪个内部判断或采用 gold 写法。SDK 哨兵只用于检验相同非 Apple host 语义；无 SDK 分支失败于旧树错误进入 SDK 查找，SDK 哨兵分支则直接失败于生成的 Apple flags。Android-only 原始 log 第 419–497 行分别展示 `xcrun: not found` 与非空 cflags 断言失败，第 527、535–537 行展示 Android 通过、新两例失败，因此拒绝它具有公开 Linux 场景依据，不是缺依赖造成的误拒。

没有观察到本次矩阵范围内的漏判或误拒。该结论限于三份固定完整候选及既核接受范围，不能推出所有可能合理实现都已实测。未新增拒绝路径或缩小正式参考集合，也不需要增加状态机、候选数量或真实 SDK 安装来成立本轮结论。

## 公开 CLI 与 brief v2 的复用限度

旧 baseline actor 原件确认 `/opt/miniconda3/envs/testbed/bin/python`、从 `/testbed` 导入 Conan 2.0.0、base HEAD `c2001bad8aa873eaf2c392ab6e3ff8b8bdfec971`、源镜像 config ID `470bafe8634b5ef92f942aef63a818d7dd681ba591548d467a6f25be420806df`。formal plan/准备身份核对同一源镜像 config ID；正式原始 log 也观察到同一工作树导入及 Conan/Jinja2 版本。旧公开回归为 34/34，通过数量与此次 formal 的原 P2P 一致，但它本身没有验证新增私有节点。

旧 `public_profiles.out` 清楚保留两种 rc 1：

- `issue_exact` 在 `AutotoolsToolchain(self)` 提前调用 `xcrun --show-sdk-path`，得到 127，尚未到题面观察异常；这是基线错误分支的诊断，不能将其当作主动输出 flags。
- `explicit_sdk_diagnostic` 通过公开 `-c tools.apple:sdk_path=/public-diagnostic-sdk` 到达 `raise Exception(tc.cflags)`，观察到 `['-isysroot /public-diagnostic-sdk', '-arch x86_64']`。该 rc 1 是故意观察异常，不是依赖安装失败，也不是修复通过。

brief v2 使用相同公开 CLI/config 接口，仅将占位字符串换成 `/tmp/sdk-path-for-config`，并明确限定配置生成观察、不验证编译或链接；此前公开 SDK 路径实现和测试也证明无需真实 SDK 内容。故已有显式配置路径证据可以复用，不必仅为占位路径改名重跑历史。

尚未实测 v2 中该字面命令，亦未证明新的完整 brief 已替换正式 solver 的通用说明。formal prepared prompt 不含 `/tmp/sdk-path-for-config`；本次 formal 是固定候选 replay，没有模型解题。本报告不把旧 scripted devcheck 或 CPU replay 记作完整 solver 交付验收。

## 当前阻断、较小方案与停止条件

**当前阻断：无（限定为此次题级 formal CPU 矩阵及语义范围）。** 题卡仍写正式原件待验/公开 v1 正在阅读，是其记录时点；以本报告原件事实供主审查者整合，未修改题卡，也不把旧状态静默改写为当前事实。

较小方案是保留现有 3F + 34P、0/1/0 正式证据和已验显式 SDK 路径；后续若启动普通 solver，只核完整公开 brief v2 的实际交付与身份，不重跑本轮已成立的候选矩阵、扩大 SDK/平台测试或重审全仓。完整交付未证实属于下一授权阶段的明确待办，不应倒推为本轮 CPU 评分错误。

停止条件已满足：正式固定身份、整份候选冻结对应、37 节点逐项对账、旧参考保留、公开 CLI 失败分类均已核。仅当材料身份变化、原始结果矛盾，或出现具体公开有效实现被拒的证据时重开相关窄核。仍未知的是完整 solver 题面交付和未实测的其他实现接受范围；14177 待另行授权和原件，未以本报告放行。

定位摘要：`matrix_results.json` SHA `af6e3ce7837e3fb5a32d711192fac45cc565385df9d72207d09c8aa9b84b8901`；`plan.json` SHA `1f40f4ab9e9f4f6be6181f44b1a4979c100100ac4bf1611c66d2f9cd5b3d5116`；`prepared_identity.json` SHA `3340a78ad36d03b8ceb4fc37fc075745864689c8819a6c2c6762fb6e31dacc12`；旧 actor audit SHA `a6af60a804a9285796fac9aca40274313cf96ba2bfd9af5778598b3e0b1477db`。
