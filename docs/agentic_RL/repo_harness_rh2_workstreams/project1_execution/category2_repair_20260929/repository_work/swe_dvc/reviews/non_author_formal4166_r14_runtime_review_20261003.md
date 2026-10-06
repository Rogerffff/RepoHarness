# DVC4166 R14 正式 CPU 三方原件窄核（非作者，2026-10-03）

结论：当前 R14 有效材料的真实正式控制矩阵为 **noop 0／gold 1／strip_positive_trailing_slash 0**。各执行 66 个节点，计分参考 63 个（3 F2P／60 P2P），另 3 个非参考节点全过；没有 missing、skip、未计账或额外失败。错解因否定目录恢复和普通文件保持行为失败而被拒绝，未将基础设施或安装／导入／收集错误算成 reward0。没有发现阻断这批正式矩阵结论的差异。

审查者已见私有材料与历史结论，不是 fresh 公开读者。复用已有材料语义、wrapper、R5 实际公开 actor 与 R14 静态适用范围审查，只补本题新实际运行原件和新 prepared。仅 stdlib 离线读取、SHA、完整日志重建、内存候选核对；未运行 CPU／SSH／Docker／pytest／项目测试，未改输入或旧报告。

## 固定输入、prepare 与正式入口

固定请求实读 SHA256 `a51f7e342b14d159f994f0e3d49380da6e1c1c7d5d331aa86f06edc3580c3953`；124 个输入 SHA 全匹配。三个 tar 各含 32／33／33 普通文件，逐成员与本机归档字节相同；原件 manifest 各列 31／32／32 文件，SHA 与 size 全匹配（tar 额外含自身 manifest）。R14 manifest 下 1220 个 repo 成员逐个实读 SHA/size，全匹配；没有运行验证器。

- release：`cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1`；manifest `51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8`。
- publication receipt：`b6f7589425f8875955764d049bed14913d37264ac4934ae38b3fcc120fd0f7e1`。
- prepare 输入：`445755210c96fc7070ffa93f6e1aae32d19054480827ba28ac059f9c1fe0bf19`；run 输入：`79219964127bac23b3fff1d091c9787982c431b641fb40a777cf487708dc2458`。
- wrapper v2：`16a78e7019827e126d0788dcbb4bf13bd0ce913a9df842b79b9c110e75dc24c0`，实际副本相同。官方入口 `rh2/scripts/replay_grade.py` SHA `d36fa3367415e573305a7a03619f51e7cbd358627569f3844d5c203b70d66db3`；正式 consumer `adapters/slime/replay_grade.py` = `b391d2c923f9bafaccad3c28bf8455bcce5c157470d590063e50adf5fb1bc96e`；prepared face = `22bf13dd0fc6c7b7d8ab7155c0afcef547b71acf5ff0d919c7a6c57160f7d012`。

prepare 作业 `dvc4166-r14-prepare-20261003-235453-a2` 的 slot 实际调用 wrapper `--mode prepare`；官方命令为固定 release 的 `replay_grade.py prepare --repo-root <该 release>/repo --out-dir <新 series>/prepared --private-dir <新 series>/private --task-ids swe_gym_lite::iterative__dvc-4166`。invocation 与 completion 的 task/release/runner/runtime/环境/命令相同，process rc0、slot returncode0，release_files_checked=1220。使用 `runtime_cpu_v2/rh2/.venv/bin/python` 与 R14 PYTHONPATH；这里核调用记录，未独立保存 Python 二进制／完整 runtime 快照。

run 固定 prepare completion `175c4e4cbb6f87e45a7fa3cda33224e776e933770ad89478226b62b9a8bde480` 和 summary `2c5bad8c15d61a887545a4cbfb73fd0f4cbc4f6764550329782f61712bd74c3f`。summary、prepare process.log JSON、manifest `1f09baaf0719c9d077694ddbcc5304f849e02bb6095bad2248ca8991ac5cb0c5`、host `c5a2c1338e5e9e760f30fc98f7fd374d2b030e78af379a10ecdae36f99da4c8b`、两公开文件/count1 和 host/count1 的引用链均匹配，三档共享同一新 prepared 的字节副本，未重绑 R5 prepared。三档 run invocation/completion 也同题、同 release/runner/runtime/输入，process/ledger SHA 匹配。

当前 revision `dvc4166-behavior-v2-draft`，registry `815811717d21fa259b354eaf85a1598241d66d85b5af547d9208b2835c4edace`，effective patch `786588558c0e5c909475073912a54749ea254492406c24c5302aba13df360ade`。grading digest `246ac88c4512483b2a3fb3e30807b239d2e7c263753037bd3a06adb21c8a033d`、environment digest `c0c30f8d0d678d956541f8552d97487199943e932a35972c12a1639932862478`、materials identity `f8b06581558ea281d57125a23fe9820da7200ce4e96ac0eb5533cc5e1aa7735c`，host／diagnostics／ledger 绑定一致。

## 节点、计分与实际失败

实际测试命令 `pytest -rA tests/func/test_ignore.py tests/unit/test_ignore.py`，完整日志均 `collected 66 items`。逐行从 `PASSED/FAILED <完整ID>` 重建；仅删除 pytest 失败行在完整 ID 后附带的 ` - As...` 简述，不按空白拆 ID。独立状态先生成，再核作者 matrix；没有从作者节点摘要生成状态。

| 候选 | 实际过／败 | 原 F2P | 新 F2P | 原绑定 P2P | 新 P2P | install／test rc | driver／slot rc | outcome／reward |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| noop | 63／3 | 0/1 | 0/2 | 59/59 | 1/1 | 0／1 | 0／0 | unresolved／0 |
| gold | 66／0 | 1/1 | 2/2 | 59/59 | 1/1 | 0／0 | 0／0 | resolved／1 |
| strip_positive_trailing_slash | 64／2 | 1/1 | 1/2 | 59/59 | 0/1 | 0／1 | 0／0 | unresolved／0 |


三档 install_skipped=false、candidate_exec rc0、segment_completed=true、log_partial=false、install_failed_commands 空，实际 RH2_INSTALL_RC=0，RH2_TEST_RC=1／0／1；测试 summary 与计分 report 一致。driver rc0 只表示正式评分运输正常。no execution_failure/infra_failure。三档 3 个非参考节点均 PASSED，所有参考分区 missing/skipped/unaccounted 空。

原材料有 1 F2P + 58 P2P 参考。唯一显式绑定是 `tests/unit/test_ignore.py::test_match_ignore_from_file[` 一对二映射到完整的 `[leading_space_literal]` 和 `[leading_space_escaped]`；二者三档均实际 PASSED。该原参考是截断含空白 ID 的导航片段，不能用前缀匹配所有参数，也不能以其中一个通过代替两者。展开后原 P2P 是 59 个完整节点；再加 `test_directory_rule_keeps_regular_file` 得 60。原 F2P 不改，加 2 个新 F2P 得 3；总计 63 参考／66 执行。host bindings、revision 与实际分区三方相符，其余原参考逐字保持。

noop 原 F2P 在 parent ignore 规则下仍枚举出 `dir/subdir/should_ignore`，断言集合本应为空；新增目录 prune 仍 `isdir("blocked")==True`，否定恢复仍 `isdir("kept")==False`。错解把正向目录规则末尾 `/` 去掉后，原 F2P 与 prune 通过，但把同名普通文件 `blocked` 错误忽略（`isfile==False`，新增 P2P 失败），且 negated directory `kept` 仍未恢复（新增 F2P 失败）。这些失败进入 AssertionError，均非导入、收集、安装或 API 使用错误。gold 全部通过。

完整 66 个节点如下；P/F = PASSED/FAILED。“原 P2P（一对二）”两行对应上面的同一原参考，其余原参考无需改名。

| 完整节点 | 分区 | noop | gold | strip-slash |
| --- | --- | --- | --- | --- |
| `tests/func/test_ignore.py::test_directory_rule_keeps_regular_file` | 新增 P2P | P | P | F |
| `tests/func/test_ignore.py::test_directory_rule_prunes_directory` | 新增 F2P | F | P | P |
| `tests/func/test_ignore.py::test_dvcignore_in_out_dir` | 额外非参考 | P | P | P |
| `tests/func/test_ignore.py::test_ignore` | 原 P2P | P | P | P |
| `tests/func/test_ignore.py::test_ignore_blank_line` | 原 P2P | P | P | P |
| `tests/func/test_ignore.py::test_ignore_collecting_dvcignores[dir/subdir]` | 原 P2P | P | P | P |
| `tests/func/test_ignore.py::test_ignore_collecting_dvcignores[dir]` | 原 P2P | P | P | P |
| `tests/func/test_ignore.py::test_ignore_directory` | 原 P2P | P | P | P |
| `tests/func/test_ignore.py::test_ignore_external` | 额外非参考 | P | P | P |
| `tests/func/test_ignore.py::test_ignore_file_in_parent_path[data_struct0-pattern_list0-result_set0]` | 原 P2P | P | P | P |
| `tests/func/test_ignore.py::test_ignore_file_in_parent_path[data_struct1-pattern_list1-result_set1]` | 原 P2P | P | P | P |
| `tests/func/test_ignore.py::test_ignore_file_in_parent_path[data_struct2-pattern_list2-result_set2]` | 原 F2P | F | P | P |
| `tests/func/test_ignore.py::test_ignore_on_branch` | 原 P2P | P | P | P |
| `tests/func/test_ignore.py::test_ignore_sub_directory` | 原 P2P | P | P | P |
| `tests/func/test_ignore.py::test_ignore_subrepo` | 原 P2P | P | P | P |
| `tests/func/test_ignore.py::test_ignore_unicode` | 原 P2P | P | P | P |
| `tests/func/test_ignore.py::test_match_nested` | 额外非参考 | P | P | P |
| `tests/func/test_ignore.py::test_negated_directory_rule_recovers_non_example` | 新增 F2P | F | P | F |
| `tests/func/test_ignore.py::test_remove_file` | 原 P2P | P | P | P |
| `tests/func/test_ignore.py::test_remove_ignored_file` | 原 P2P | P | P | P |
| `tests/func/test_ignore.py::test_rename_file` | 原 P2P | P | P | P |
| `tests/func/test_ignore.py::test_rename_ignored_file` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[!to_ignore.txt-patterns10-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[#to_ignore-patterns3-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[#to_ignore-patterns4-False]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[/full/path/to/ignore/file/to_ignore-patterns15-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[2ile.txt-patterns24-False]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[data/file-patterns12-False]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[data/file-patterns13-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[data/file.txt-patterns18-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[data/file.txt-patterns38-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[data/p/file.txt-patterns39-False]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[dont_ignore.txt-patterns1-False]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[fi/e.txt-patterns22-False]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[file-patterns11-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[file.txt-patterns20-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[file.txt-patterns21-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[file.txt-patterns23-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[leading_space_escaped]` | 原 P2P（一对二） | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[leading_space_literal]` | 原 P2P（一对二） | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[other/data/file-patterns14-False]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[path/to_ignore.txt-patterns17-False]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[path/to_ignore.txt-patterns36-False]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[path/to_ignore.txt-patterns37-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[rel/p/p2/to_ignore-patterns25-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[rel/p/p2/to_ignore-patterns26-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[rel/p/p2/to_ignore-patterns28-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[rel/p/p2/to_ignore-patterns29-False]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[rel/p/p2/to_ignore-patterns32-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[rel/p/to_ignore-patterns31-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[rel/path/path2/dont_ignore-patterns27-False]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[rel/path/path2/dont_ignore-patterns30-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[rel/path/path2/dont_ignore-patterns33-False]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[rel/path/path2/dont_ignore-patterns34-False]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[rel/path/path2/to_ignore-patterns19-False]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[rel/path/path2/to_ignore-patterns40-False]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[to_ignore-patterns0-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[to_ignore-patterns2-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[to_ignore.txt-patterns16-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[to_ignore.txt-patterns35-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[to_ignore.txt-patterns7-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[to_ignore.txt-patterns8-False]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_match_ignore_from_file[to_ignore.txt-patterns9-True]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_should_ignore_dir[.dvc]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_should_ignore_dir[.git]` | 原 P2P | P | P | P |
| `tests/unit/test_ignore.py::test_should_ignore_dir[.hg]` | 原 P2P | P | P | P |


## 基线、候选与 FrozenPatch

三档 baseline manifest 文件 SHA `793c35ecb2b2dd28dbbded4976fc3f302343a5d7339c9facca5e467f6ce09929` 相同，独立 canonical digest `16f108c365097d36390d40ff2b06c47fcf186b13c0e4cae2381ebfe6048ab6db` 与 FrozenPatch 锚相符；stage/head、materialized_head、task_base_commit 均为 `520e01f11305aba1994df354adef86e6d90180de`。git sanitize rc0、HEAD before/after 相同、violations 空。

noop entries/projection 空，candidate.patch 不存在；空候选约定 SHA `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`。gold 原文件与实际 candidate.patch SHA `092d48c27ce32921855206a1d1608d653edaed3e3878be1dac5984747d3a3e03`；错解 SHA `5786a6c734109186b52c5ae2932b3e31e6f8a5aadf720b83b7b8e9e26ea2f90e`。两者只修改 `dvc/ignore.py`，实际 git_apply 正常、分类 projectable，projection 无 ignored/unsupported，私有 pathset 不变，候选测试路径／conftest／fixture 清单空。ledger 将离线 patch 控制标为 kind=cc 是入口内部类型，不能据此声称产生新模型或 CC 求解。

严格解码 FrozenPatch content 并重算 SHA：gold `f06500d1bfa7114b453fc3205b4a933274014186996b24d1c00d302492a81f07`，错解 `a220117326109ef80ff0797561a6f20188dc8376e814fb353870bb3a68dc683e`。对实际候选 patch 做纯内存反向 hunk 核对（上下文逐行匹配），均还原到同一基线内容 SHA `998e87ebd8b3f87ac23f3b7e768cdb87b4f067be6f9478152a44ba0bfbc92460`，等于 baseline 对应 entry。FrozenPatch canonical SHA 重算等于 projection/ledger：noop `a356f9a30f7d67bd66261e74db59854b0d5f097fcca342b347be95f477672e99`、gold `7c5fe94116853051210be19ac8e9bf88b5051a31e45c4058463287c31b9893cc`、错解 `77737371b8d1ebb9e7dafa948ba08753e0e0aa98e2590f5811dff60425d6c9bb`。

原固定镜像的 setup.py moto `1.3.14.dev464→1.3.14` 差异仍可见于三次 trusted diff；它在既有 baseline 中，不是这些候选新增的修改。三次该 diff 显示片段为相同 355B／SHA `f49f71982f6d9a9b38559080b90c74b247bb7d9d8202996da2db6d62fe71dc04`。这个日志展示片段不等于原 R5 v2 guard 所核完整 binary diff 字节；后者的固定 SHA `8bd072b6e35dd358d920432c24b35048d4e51a9d0bc78972ceeb18e302b8dfbf` 及精确 porcelain 例外仍按旧审查保留，不泛化许可其它 dirty 初态。

## 固定镜像、UID54322 预检与测试恢复

三档 grader 镜像 actual/ref、baseline/FrozenPatch runtime identity 及注册 installation 一致，均为 `sha256:28ed5ef69d46c326ec183f8719e426611ca848046156fa98f9f6c7f35b46ebeb`。正式消费者配对这个固定 ID 与 manifest=None，ledger `image_digest_expected=null`、identity=`local_build:<ID>`；原来源 manifest `f32dbb8cd78ee8146529185f79532b3e3dca61c06a10c4ede6ca48ba26b15041` 只留在 public／installation 来源 pin，没有误配到派生镜像。

三档 diagnostics.candidate_prerequisite 的原始 exec 结果为 user54322、home=/home/rh2grader、rc0、stderr 空、stdout `RH2_DVC_BEHAVIOR_UID54322_WHEEL_BYTES_OK=1`、state=verified。根据 host installation 的五个 wheel pins 与冻结 source 字符串独立重建脚本，SHA 全等于 `8076e4575f91568e04df5bb3439d69333b5a738d5c22336ff6e62d26ab93d42f`。包括固定兼容 wheel `networkx-2.3+rh2.1-py2.py3-none-any.whl` SHA `1aae272f148313261e4c8b5fb15717d430cd1828371cd94ccd2f79de9f27c412`，以及 pathspec0.8.1；不是换为别的 NetworkX 版本。预检使用 -I、geteuid、offline ENV、O_NOFOLLOW、regular file／完整 wheel SHA，不依赖包导入判断安装身份。manager 以 candidate UID 执行并要求 rc0；这是独立 exec 的原始诊断字段，未另存 standalone 脚本／日志。eval.log 另有 UID0 trusted 检查，不能拿它替代 UID54322 结果。

两份测试文件均存在于 immutable base，三次实际恢复 `tests/func/test_ignore.py`／`tests/unit/test_ignore.py` 后，核 SHA 分别为 `0b11d0098c2e97b3cc1f454cba2fbccdbb3e144545b45854aff75cf0be8f9602`／`67cff53e0626e13934a1b74461d5d2648c8e56859fc1aadd9fc067282b6c48ed`，再应用固定 effective patch。RH2_SETUP_RESTORED=2、APPLY_RC=0、EXPECTED/TEST_FILES=2、ABSENT=0、IRREGULAR 空、OK=1，保护检查正常。没有新增测试文件，因此没有套用 6954 新文件 base64 capture。两测试文件 apply 后完整源码未另归档；本报告依据恢复 SHA、固定补丁和实际完整节点，不宣称做了另一次完整 after-apply 字节读回。

## 新 prepared 公开输入、清理及限制

R14 实际 rollout.public 与固定 R5 成功作业完整相等，public digest `5d5da25d1dcc9203b201085f837abf65b4cc32adb0e61dff65fba48f20db1a4a` 相同。solver prompt 字符串 UTF-8 字节相同；metadata 仅 environment digest 从 `3d2335c616a8ad71f9f3672d7fec4617a4ea4e8a7c13d427ea6fa1d672cb62c2` 改为 `c0c30f8d0d678d956541f8552d97487199943e932a35972c12a1639932862478`，**整 prompts.jsonl 字节不相同**。新 rollout SHA `a01adc0fcb7f1003aecbacc6ce4b9e6b201511194d2e1bbb802f573ca7a98c39`、prompts SHA `187161c961d719fc75d8c9240070a6ee8948863e313e7ee70e3b2e97a63b3fb6`。

固定旧成功输入确为 `input_v2.json`，实读 SHA `894bb5e2af530d979552d0244386cff5357df69d742515338cd9c81e15309be9`，helper SHA `f513232d19dae5c28e3a0ae8600cc9ad7cbab71aa0a7582f5abd9ceccaf7bd8d`。旧 R5 29 passed、首请求逐字 original issue+neutral brief、UID54321／CC2.1.205／profile及清理事实按旧非作者审查复用；旧 v1 guard 在 CC/命令前失败的事实保留。当前请求正确固定 v2 输入，没有延用上一复用请求的遗留 v1 导航。不是新 R14 actor 运行。

三档内层 cleanup removed=true／rm:ok，process manager_close created_total=removed_total=1、containers/supply/open/failures 空、halted/aborted null、final rc0；外层 cleanup_readback 按各 run_id 标签查询 container/network 均 rc0、stdout/stderr 空、ids=[]。支持归档时间点该标签无残留，未做新在线清理。

ledger policy 为 UID54322、2 CPU、4GiB、PID512、deny_all、64MiB shm／1GiB tmpfs、指定 candidate writable prefix；candidate UID 预检实际通过。resource_facts=null，没有另存实际正式 grader HostConfig inspect，policy 不能替代实际配置验收。env_qualification=absent，正式过程 qualifications0、overlay0，不授予环境资格。

作者 matrix 实读 SHA `d4d2875cd77cdacb0011fe399e9f8e1872a41033a9104b7158887c1b3eb915c6`，其当前节点／分区／reward 与独立重建一致。保留其限制：没有封存原版仅旧安装历史 consumer，所以旧原版正式 reward 仍未知，不能从私有诊断补造。旧 revision 的 draft/not_run 字段属于历史冻结输入，不覆盖或静默更新。本报告不验证其它题、新模型 probe、训练 actor 接入或环境／训练资格，也不要求为当前结论重跑旧历史矩阵。

## 最少原件指针与实读 SHA

全部原件根与路径见固定请求；各 job 的 eval_logs 完整日志、ledger 为节点／计分依据，completion/process/slots/status 为调用／退出依据，cleanup_readback 为外层残留查询。

| job | eval.log SHA256／节点行区间 | ledger SHA256 | completion SHA256 | cleanup_readback SHA256 |
| --- | --- | --- | --- | --- |
| `dvc4166-r14-noop-20261003-235453-a2` | `be422410eee249d0255f31a9c2f39fff6d03472852c8f076064aea6a8e548009`／1031–1096 | `850809932ce83025c14497fa1ed06b51a761ebe92406b9e1733acc664855bd26` | `218768af7a6954d6133a531a27749defe6319598c809f3dbea5502b81b5b1d03` | `c3086e473f3f7eadf556f47b353a72778b1b554398e4e09dea90f664243d3078` |
| `dvc4166-r14-gold-20261003-235453` | `cce3201643e73128258acd9c9e82e9abdcdd4aaef7c94017c634a8eabdf7bf41`／1008–1073 | `7a05fa5a1b1b7b80e7bad3da4eb4979a57524da72a4dd0c1db4fd062fc5d78f1` | `915d79d76dba8c34fff5e00336b3d399e85d0151f5f60236d7e10d94323e4fa4` | `e3194a73d9e5f168c6cdfbf6e27c428ee0757d1a6bcb149b78f7e2b60847dc2d` |
| `dvc4166-r14-strip_positive_trailing_slash-20261003-235453` | `7f90723aae9fb48db934eb52f2fbb6836b73be2f1c0e85acbf18e81d47f7a5dc`／1010–1075 | `f871628b07cb6185c87b3be9da883b27384231c617d85483fb84564d2761c78a` | `4e319830b0b4855289baa60aaaf0716f1bf462b5ae7ee407656d6be953e1a032` | `7c05a7ba11a9e50365f348e9d569cf51a26df5afd700220a256430bf1c9ba7bb` |


归档与 prepare 关键 SHA：

| 文件 | 实读 SHA256 |
| --- | --- |
| `formal4166_r14_noop_235453_v1.tar.gz` | `2e86062c280807147236e52c36f468e8356cc9ca395469fd52b3a7e106988a86` |
| `formal4166_r14_gold_235453_v1.tar.gz` | `bf6f9aed2a294873f5241d163e02cd981b54843f67d19eb1d7452a708919b3d5` |
| `formal4166_r14_strip_positive_trailing_slash_235453_v1.tar.gz` | `6de54b91d77db90662153434261eee3c4111d1a72637145afb7fae6e7c24e237` |
| `dvc4166-r14-prepare-20261003-235453-a2/invocation.json` | `64ea3db0d1c05c2a568ad3e629343d789f633e5f7292d87281368c0890886491` |
| `dvc4166-r14-prepare-20261003-235453-a2/process.log` | `443276a2af5a16473346a11455698c69acf6088cff30cedcedcd8fabee681fd8` |
| `dvc4166-r14-prepare-20261003-235453-a2/completion.json` | `175c4e4cbb6f87e45a7fa3cda33224e776e933770ad89478226b62b9a8bde480` |
