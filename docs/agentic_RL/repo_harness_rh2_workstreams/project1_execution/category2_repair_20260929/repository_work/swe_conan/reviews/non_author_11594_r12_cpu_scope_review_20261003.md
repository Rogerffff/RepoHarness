# Conan11594：R12 正式 CPU 语义与范围窄核

2026-10-03。非作者 Falsifier / Simplifier；本批指定 GPT-6.1 Sol / high。这是授权后的私有 CPU 证据复核，不是干净公开盲审。

## 结论

未发现阻断本题 **R12 正式 CPU 矩阵验收**的问题。完整 noop / gold / drop_config 的正式 reward 为 **0 / 1 / 0**。原六个 generator case 保留，新增真实 CTest Release 执行检查已消费。正式分母是 **6 个来源参考（2F + 4P），对应 7 个完整 pytest node**；原 Ninja 来源参考按两个完整成员 ALL 聚合，没有用其中一个通过覆盖另一个失败。

drop_config 的拒绝有实际配置错误依据：它通过原六个命令测试，但执行了 `ctest -C Debug`，请求 Release 的真实 CTest 检查失败；安装及工具前置检查均成功，不是缺环境导致的误拒。

结论只覆盖此次正式 CPU 评分及其材料身份，不自动批准 solver 探针或训练。主审查者后来通知已回收并根核新 actor 工具原件；本次不重复读取该新增范围，也不把 actor 工具检查、另一人的公开读者报告或本次固定候选 replay 当作完整 solver 题面交付/功能验收。

## 范围与方法

只读本次授权的：

- `runs/category2_repair_20260929/conan_cpu_20261003/formal_matrix_11594_r12_v1_evidence/formal_matrix_11594_r12_v1/` 中计划、驱动、prepared 身份/host view、候选、账本、FrozenPatch/投影、原始 eval log、diagnostics 和退出记录。
- 同级 `formal_matrix_11594_r12_v1_remote_audit.json` 与 `formal_matrix_11594_r12_v1_audit.json`。后者作为根核摘要参考，关键结果另对原件计算。
- 固定 R12 `runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe21_conan_v1/` 的 manifest、11594 consumer 值、11594 registry/绑定/环境材料，以及 `prepared_task_face.py`、`bundles_v2.py`、`conan11594_reference_bindings.py` 的相关消费段落。没有核其他题的 consumer 值或运行结果。
- 11594 工作包 `revision_plan.json`、`publication_request_20261003_v1.json`、`effective_test.py`、`reference_bindings.json`；必要公开 issue/base。此前已读 `non_author_material_review_20261003.md` 的 11594 静态范围继续复用，不重审旧题义。

本地校验仅使用 stdlib JSON/SHA/AST 与内存中的完整 patch 应用比较。没有访问远端、Docker、模型，未执行项目代码/Conan/pytest，不重跑历史或新增反例/guard。唯一新增文件为本报告；13230 及已有报告未修改。

## 固定身份与完整候选

release ID 为 `cat2-cpu-r2e089092-swe21-conan-20261003-v1`。独立计算 manifest SHA 为 `3fe07ef04c88f9883b2bc3040cac425374cbd7bcd23041fc4280e17ef62e7987`。本次核对的 11 个相关消费/修订文件 SHA 与 manifest 一致；不是独立重审全部 1020 成员。保留的运行驱动在执行前核过整包，release verify 和 prepare 的退出为 0。

本次 55 个导出文件的 SHA/大小全部与 remote audit 一致。11594 consumer 与 formal plan 完全相等，formal 阶段的 publication input 与固定工作包请求逐字相等。prepared host grading view 消费完整有效测试补丁及正式 2F/4P 数组；原 P2P 数组逐项保持，新增 F2P 只有 Release 真实执行检查。

| 材料 | SHA-256（省略 `sha256:` 前缀） |
| --- | --- |
| 原测试补丁 | `ec6de8505d349e44baa83a6a7505f4900a282d6b5bee28eaa4f8be85f9a2ceef` |
| 有效测试补丁 | `4a781bc87b05f63cac3af0686bbd6b29817dacd39f0ef7ba053fd0f2f9a47eb2` |
| 有效测试文件 | `d046573dbe09adc44bf98e4e84ad8739c9be27e32ab9aa80c52928c710cabe81` |
| 固定 reference bindings | `ca0987bd0bdde5926b33eabf31bf51b1e704165036e1441e66ff97e6f9630bcc` |
| 修订 registry | `105cf9f779eac8c933ff38984b829da23608659abe926ec7269088a524ce4fde` |
| 正式 grading bundle | `9a06e834021494ea7b52c05db8837d0df833835b402d581d7bb3703e32ace976` |
| 正式 grading materials identity | `fe68e56946f2eeab35c4c335f317ef2a17fb27da4af54024b3d837f2548788a4` |

gold SHA 为 `e49265e4fd430f627dd2293f1f79b3b6c30b30d36c8a6a066c992f4d4b48abfa`，drop_config 为 `f4445e51d087748cf00cd647bcf2ddf13a592c1be343561ad6956a367ef408e1`，与固定请求和 plan 一致。独立将整份候选应用到公开 `conan/tools/cmake/cmake.py`，所得文件分别与对应 FrozenPatch 唯一 modify 条目逐字相等、content digest 相符；保存的 candidate.patch 也与阶段候选逐字相等。noop 为零条目。三方投影无 ignored paths、无 unsupported shape，`excluded_pathset_changed=false`，没有截取补丁片段评分的证据。

`run_matrix.py` 的 expected reward 是正式 report 产出后的检查，不替代实际评分。固定 HostGradingView 构造 grading spec 后，完整候选沿正式 replay 的冻结导出/投影进入 grader；新测试、绑定版本与 parser 身份均出现在实际 diagnostics 中。

## 原文件缺席的实际处理

公开 base 中 `conans/test/unittests/tools/cmake/test_cmake_test.py` 确实不存在。registry 明确记录 `base_state=absent`，`baseline_files` 不伪造该文件的 SHA；schema 固定本题、路径、base commit 和材料身份。

`prepared_task_face.py` 的 11594 分支在受信 apply 前检查 base commit 不含该路径，且工作树该路径既不存在也不是 symlink。gold 原始 log 显示这两项检查执行后，完整官方 patch 创建该文件并 cleanly apply；三方 setup apply rc 都为 0、expected/present 文件各为 1、保护成功。

`RH2_SETUP_RESTORED=0` 在本题是正确结果：没有旧文件可 checkout。`RH2_SETUP_ABSENT_TEST_FILES=0` 是 **应用后** 自证检查没有缺失测试文件，不表示 base 本来有该文件。不能将这两个计数误读为漏恢复或伪造基线。

原补丁的参数化 `test_run_tests` 函数 AST 与有效文件逐字结构一致，六个 generator/target 参数不变；新测试仅追加。因此原参考保留和缺席文件创建各有独立证据。

## 来源参考、ALL 与原始节点对账

从有效测试原参数化 AST 独立导出六个完整 nodeid，加上新增执行节点，得到七节点集合；三方原始 `PASSED/FAILED` 摘要集合精确与其相等，无缺席、跳过或额外参考。

原 Ninja alias 绑定以下两个完整成员：

- `test_run_tests[Ninja Makefiles-test]`
- `test_run_tests[Ninja Multi-Config-test]`

固定 parser `bound_states()` 要求每个成员都有完整状态，否则不产生 alias；`parse_conan11594_bound()` 先删除旧 parser 的碰撞值，再添加完整成员聚合结果。状态优先级使任一失败/非通过不能被通过覆盖。实际 noop 提供了一通过、一失败的非对称证据：最终 alias 失败，证明本轮不是沿用碰撞末值放行。

| 完整候选 | Ninja Makefiles | Ninja Multi-Config | Ninja 来源 ALL | 新真实 Release 执行 | 4 个原 P2P | 原始 pytest | 正式 reward |
| --- | --- | --- | --- | --- | --- | --- | --- |
| noop | 通过 | 失败 | 失败 | 失败 | 全通过 | 2 failed, 5 passed；rc 1 | 0 |
| gold | 通过 | 通过 | 通过 | 通过 | 全通过 | 7 passed；rc 0 | 1 |
| drop_config | 通过 | 通过 | 通过 | 失败 | 全通过 | 1 failed, 6 passed；rc 1 | 0 |

逐项用原始成员结果重建 ALL，与 diagnostics 的原 F2P success/failure 一致。正式 parser 的 `num_parsed_tests=6` 是来源聚合后的数量；raw pytest collected 7 是完整节点数量，二者不是丢节点矛盾。三方原/新增分区的 missing/skipped/unaccounted 都为空，标记段外计数为 0；没有将两个 Ninja 成员改算两个来源参考。

## 错解归因与接受范围

公开 issue 明确要求 `cmake.test()` 在 Ninja Multi-Config 下可执行，原日志同时请求 Release。新增测试使用 `project(... NONE)`，无需真实编译器编译；它通过 Conan CMake configure/test 执行 CTest，并仅在 `$<CONFIG>` 为 Release 时写 marker，最后从 TestClient 隔离目录读取 marker。这是原 `cmake.test()` 主题的执行验收，没有扩大到额外产品能力或平台。

drop_config 原始 log 第 668–710 行显示 configure/generate 成功、构建 `test` 目标、运行 `requested_config`，随后走 `CMakeFiles/Debug/test.util` 与 `ctest --force-new-ctest-process -C Debug`，CTest 失败并导致 `client.run('build .')` 抛异常。它的问题是删掉请求配置之后实际执行 Debug。gold 在同一受信材料/工具环境中通过 marker 检查；故此次拒绝有功能语义依据，不能归因于 CMake/Ninja 缺失。

三方 candidate prerequisite 均以 UID54322 执行成功，固定 Ninja Python 分发包检查为 `1.10.2.4`、CMake 为 `3.22.1`；保留的 Ninja binary stdout 为 `1.10.2.git.kitware.jobserver-1`。分发包版本与 binary 版本串是不同标识，不据版本串不等于 `1.10.2.4` 判环境失配。该证据只针对正式 grader 候选用户，不代替 actor UID54321 的工具证明。

新增检查要求实际执行正确配置，不锁内部修法、flag 次序或命令日志的固定字符串；原六例按已有材料规则保持。本次三候选未观察到漏判/误拒，不声称所有合理实现都已实测，也不为理论反例扩展候选数量。

## 清理、仍未知与停止条件

三方安装成功、测试段完整、driver rc 均为 0、`stage_error=null`；noop/drop_config 为 `tests_failed`，没有 infra 判定。候选容器移除成功；每次 manager 创建/移除 grader 各 1，open containers/supply 与 cleanup_failures 为空，精确 run label 容器/网络读回为空。三方 runner 完整性未变。保留的内存峰值和声明策略不能替代完整的逐容器资源事实，本报告不扩大资源/吞吐结论。

当前 CPU 范围没有阻断。较小方案是采纳这份固定材料、完整三候选及 ALL/Release 实际证据，结束本轮 CPU 复核；actor 工具及完整 solver 交付沿各自授权证据处理，不重跑已经对账的矩阵，不新增 guard、SDK 或平台测试。后续具体的材料身份变化、原始结果矛盾或合理实现被拒证据，才重开相应窄核。

本轮停止条件已满足：完整候选冻结对应、base 缺席处理、原参考保留、七节点/六来源逐项对账、ALL 非对称实例、drop_config 错配置归因和两层清理均已核。仍未知的是本报告范围之外的完整 solver 题面交付与未实测实现；不以这些未知内容倒推本轮 CPU 验收失败。

定位摘要：`matrix_results.json` SHA `8d93c3afc9e01ccd0d61d30bef5253345d2ea9e6340a2e17e8772cffef791e26`；`plan.json` SHA `7137422fc40083747ea048ff2b0a1c72d95fc5b69c869b84571c61958fcd3e13`；`prepared_identity.json` SHA `ad484ef281b71b0a17e17e17999269df725999a15da138a13d1d20c1662fdc71`。
