# Conan 15422 v2 非作者运行核查

日期：2026-10-03。角色：Production Tracer。结论依据仅为暂停要求到达前已经读取的原件；收到暂停后未新增检查、实验、外部搜索或通知下游，仅保存本报告。

**当前 v2 私有 CPU 运行与报告一致，没有新增当前运行 finding，也没有当前 P0／P1。** 八方各收集 48 个节点，5F／40P 完整出现；独立从原始输出重建的 360 条精确参考状态与题主 audit 一致。有效正对照保留，Qwen3.6 a2 被实际 CMake configure 拒读。此结论只覆盖 UID0 私有源码投影诊断，不是正式评分、完整 FrozenPatch 重放、actor 或训练资格证明。

## 上下文及读取范围

本审查者未参与材料编写；接受主线程给出的角色、指定路径与停止条件，继承仓库规范。已经接触题主报告、预期矩阵及作者 audit，因此不是全盲公开读者；作者主张均回查原件。模型／努力配置继承主线程，未自行另设，未再派子 agent。

已读根 AGENTS、review-standards §10.1／10.4／10.5、remaining_workflow_20261002，以及以下原件（均为工作区相对路径）：

- 题主 `.../repository_work/swe_conan/tasks/conan-io__conan-15422/` 当前 revision plan、effective patch／py、CPU 报告；materials/v2 的材料、change_from_v1、from_v1.diff。
- `runs/category2_repair_20260929/conan_cpu_20261003/diagnostic_15422_v2/` 的 spec、manifest、runner、7 份 original/source patch 及投影表；`diagnostic_evidence_15422_v2/output/` 的 summary、八方准备／identity／收集／完整模块／真实消费输出；两个 v2 audit。
- 同一运行目录的 image_prepare_15422_cmake_v1、对应 complete evidence／receipt 与环境 remote audit：配方、历史镜像记录、prepare 脚本、归档、pull/build、inspect/id。
- 由明确指针读取历史 original patch；base 中 TestClient、runner、conftest、CMakeToolchain 与 presets 调用点。没有广扫其它题或全部 runs。

## 真实路径与退出语义

回传父作业运行 private_behavior.py，2026-10-02 18:34:00–18:36:40 UTC 完成，RC0。runner 第35–98行顺序运行八个候选，每次一个容器，network none、2CPU／4GiB、pids-limit512、init，入口 sleep infinity，UID0；pytest -n0，无 xdist worker 并行。

每方先核 HEAD 与 base 文件 SHA，应用受信 v2 测试，再应用候选 presets.py 投影并核应用后 SHA。noop 6步，其余各9步准备，全部RC0；identity／collect也全RC0，无准备失败后继续、收集ERROR或缺失参考。

```text
private_behavior → docker exec → timeout → bash → pytest -n0
→ tool(cmake,3.23) fixture → jobs2/jobs7 测试
→ TestClient.run(install) → ConanAPI／Cli.run
→ CMakeToolchain.generate → write_cmake_presets → _CMakePresets.generate
→ 断言生成 jobs → TestClient.run_command(cmake --preset <生成名称>)
→ conan_run → subprocess.Popen／communicate
→ configure 成功才执行 cmake --build --preset <生成名称>
```

TestClient.run 使用隔离 cache 与测试 I/O／服务器替身；run_command 调真实 CMake 进程，非零退出经 _handle_cli_result 抛异常（base tools.py:575–604；runners.py:35–59），不是独立 actor 求解。Linux fixture 指向 /usr/share/cmake-3.23.5/bin 并前置PATH，teardown恢复（base conftest.py:90–93、351–393）。fixture 只查目录／路径，本次版本另由归档SHA、构建及identity补证。

runner 对 shell 有 timeout 和外层 subprocess 超时；准备失败停止。普通命令RC被保存并继续后续诊断，故父RC0不表示测试全过；额外消费脚本本身RC0也不表示内部CMake全过，它只打印内部RC。

## 精确参考结果

F2P的公共nodeid前缀为 `conans/test/integration/toolchains/cmake/test_cmaketoolchain.py::`；五列分别是 test_presets_njobs、test_presets_jobs_default_matches_public_helper、test_presets_jobs_explicit_values[jobs2]、同[jobs7]、test_presets_jobs_multiconfig_append_replace。P/F为原始PASSED/FAILED，不是reward。

| 候选 | jobs42 | 默认 | jobs2 | jobs7 | 追加／替换 | P2P | 模块RC | 额外消费configure／build RC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| noop | F | F | F | F | F | 40／40 P | 1 | 0／0 |
| gold | P | P | P | P | P | 40／40 P | 0 | 0／0 |
| coder_a1 | P | F | P | P | P | 40／40 P | 1 | 0／0 |
| coder_a3 | P | F | P | P | P | 40／40 P | 1 | 0／0 |
| deepseek_a1 | P | P | P | P | F | 40／40 P | 1 | 0／0 |
| deepseek_a4_generator_boundary | P | P | P | P | P | 40／40 P | 0 | 0／0 |
| coder_a2_alternative | P | P | P | P | P | 40／40 P | 0 | 0／0 |
| qwen36_a2_schema_diagnostic | P | P | F | F | P | 40／40 P | 1 | 1／1 |

从 effective_module.out 的完整nodeid逐项重建，8×45状态与audit相同、参考集合与当前plan相同，参考无ERROR／skip／xfail；旧40P列表不变。每方额外三个收集节点为 test_apple_vars_overwrite_user_conf、test_cmaketoolchain_cmake_system_processor_cross_apple、test_presets_paths_normalization；两项Only OSX、一项Only Windows跳过均不属于参考。

Qwen两节点先通过jobs断言，继而在configure抛出 `"cmakeMinimumRequired" version too new`（原日志行62／118）；原patch将最低版本3.15改为3.25，真实消费输出也记录该值。**两个失败测试节点没有执行到build**；其build RC1来自额外诊断，该脚本即使configure失败仍继续执行build。gold及两种替代正对照的通过节点，结合顺序代码证明两命令成功；额外日志也直接记录0／0。noop额外消费成功仅说明无jobs的旧JSON可消费。

NONE工程与Unix Makefiles验证实际预设消费及字段值，不测实际编译并行度。默认helper与Ninja Multi-Config仍是JSON行为检查，没有真实Ninja编译证据。

## 投影、材料与环境完整性

7份original均与历史指针逐字节一致，source均恰好等于原patch中presets.py的原字节diff块，original/projected SHA符合投影表。遗漏范围：Coder a3的README_JOBS_FEATURE.md、额外单测、debug_test.py、verify_implementation.py；DeepSeek a1的test_cmake_presets_definitions.py；DeepSeek a4的本评分测试文件。其余四份非空候选没有遗漏，source即original。这保护受信测试，但不证明完整原patch在正式冻结／恢复中的表现。

根与materials/v2三个材料完全相同；测试py／patch与运行包相同：

- patch SHA256：9ad7529457054bb004534951feb4d08b40973a06fd30b4a1564054de074a0bb6。
- py SHA256：5de644e248dc131c250f343885d95ec5b9d9f2f35798852d79e263fe4252c16a。
- 当前plan SHA256：e90392691d2f942d1ed0ff8c620a9107a3a974d3fb034a41fd3c8a6e9a72b1d1；运行快照：1328c62b797703fd9598d21fd703774909ea0947f5105cc11d12d2b88a199a18。

plan差异仅status/pending运行后更新，参考／候选／测试身份不变，不能宣称当前plan全字节经过远端执行。部分候选历史pending字符串不覆盖此次私有结果，也没有正式新reward。from_v1.diff只修改同两个显式参数节点的工具fixture、NONE／Unix Makefiles和真实消费，5F／40P不变。

镜像receipt的pull/build均RC0，原base config为 `sha256:bb264f88ffc338f8b33c58e15a5f0373761abfe75145e7ae201e360031a8b9c8`；CMake归档SHA256为 `bbd7ad93d2a14ed3608021a9466ae63db76a24efd1fae7a5f7798c1de7ab9344`。Dockerfile恢复历史CMake／conan入口配方，构建禁网、2CPU／4GiB，日志列四个中间容器删除。派生config `sha256:a27936515e625ace25f5d76dcef25566079c7ac355b51bdfc5c3408c26a07ead` 在receipt／inspect／id／spec／summary一致。八方identity显示testbed导入、Conan2.1.0-dev、PATH CMake3.23.5、系统CMake3.22.1。

独立重新计算诊断audit的131件与环境audit的10件SHA，全部吻合无缺件。证明本地与回传哈希一致，不是远端签名或未列文件的完整性认证。八方清理均rm_rc0、query_rc0、remaining为空；支持这些容器删除与查询时零残留。入口sleep最终被rm -f，未记录正常容器退出码、OOM标记或全宿主容器清单，不能称八个容器自然正常退出。

## Findings与仍未知范围

没有新增当前运行finding。已核Qwen候选缺陷标 `test_only`／P2，v2已捕获；调用真实Conan／CMake代码不等于本轮进入RH2正式生产入口，不能标production_observed。

已知验收缺口维持 `conditional_future`，不核销、不新增本轮修复闸门：正式consumer登记当前v2、有效测试替换和完整FrozenPatch正式评分，归共用发布／评分负责人；actor历史证据按base／归档／配方复用与普通solver实际交付，归题主／统一执行者。本轮没有权限资格或GPU证据。取消／超时／OOM故障未实测，未列远端文件未核，不据此扩展平台或恢复机制。

停止条件已满足：v2真实执行与报告一致，参考、身份、投影、RC／清理和SHA已核。按最新暂停要求，到此结束，不开启下一轮或发送下游通知。
