# DVC6954 R14 正式 CPU 三方原件窄核（非作者，2026-10-03）

结论：本批 R14 当前有效材料的真实正式控制矩阵为 **noop 0／gold 1／negative_int_only 0**。每次实际执行 26 个节点，计分参考为 3 F2P + 12 P2P，另有 11 个公开功能非参考节点；无缺席、skip、未计账节点或额外失败。正常错误解被行为检查拒绝，未把基础设施、安装、导入或收集错误充作 reward0。没有发现阻断本批矩阵结论的差异。

审查者已见私有材料、历史诊断和 R5 actor 原件，不是 fresh 公开读者。复用已有材料语义／wrapper 静态／R5 actor 核查，新增范围是本批实际正式运行原件。仅用 stdlib 离线读文件、SHA、日志重建与内存补丁核对；没有运行 CPU、SSH、Docker、pytest／项目测试或修改输入。此报告不宣称新 actor／模型 probe／环境或训练资格通过。

## 输入固定性与来源链

请求实读 SHA256 `df1b8c290d41827913e0cdb118b1533fa442f4e4fcbada3830a72e4febd031a7`；123 个固定输入文件 SHA 全匹配。三个 tar 分别含 32／33／33 个普通文件，逐成员与本机归档字节相同；其中 manifest 各声明 31／32／32 文件，其 SHA 和 size 全匹配（tar 额外含自身 manifest）。R14 manifest `51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8` 所声明 1220 个 repo 成员已逐个读回 SHA，全匹配。未运行 release 验证器。

- release：`cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1`。
- publication receipt：`2ac314f6751bc0e9150d1ef101d5361cc88906fb5fcb577517f112ed227b4668`；prepare 输入 `b20b4aec837e2b4b83f708d312f8ded2c302deaf86558e0ef645d009f42ca0ee`，run 输入 `0f35137fa5a0306c2b08aee877a7a84dfa370df9b142638606b8a8d35a8c6772`。
- wrapper v2：`16a78e7019827e126d0788dcbb4bf13bd0ce913a9df842b79b9c110e75dc24c0`；实际归档副本与当前文件相同，仅调用固定 release 官方入口。
- 官方入口 `rh2/scripts/replay_grade.py`：`d36fa3367415e573305a7a03619f51e7cbd358627569f3844d5c203b70d66db3`；消费者 `adapters/slime/replay_grade.py`：`b391d2c923f9bafaccad3c28bf8455bcce5c157470d590063e50adf5fb1bc96e`；prepared face：`22bf13dd0fc6c7b7d8ab7155c0afcef547b71acf5ff0d919c7a6c57160f7d012`。

prepare 作业为 `dvc6954-r14-prepare-20261003-002`。slot 命令调用该 series 的 wrapper `--mode prepare`；invocation 与 completion 同 task/release/manifest/runner/runtime/命令/环境，completion process rc0，slot returncode0。官方命令为固定 release `replay_grade.py prepare --repo-root <该 release>/repo --out-dir <新 series>/prepared --private-dir <新 series>/private --task-ids swe_gym_lite::iterative__dvc-6954`，不是重绑 R5 prepared。其 process.log JSON 与实际 summary 相等、SHA 匹配。

prepare completion `cdfb21b13d038b7083b15f74cb06b92c0d9da4f29e5ad1931af64e523c9831d1` → summary `a4862ec050024536e718c107fe69ad8613fa9e573427b8c182aa445b2fcfde11` → manifest `a1aa0200be589df82faafc91d008429521724d56a9f5ff8ab51926980dc51cde`／host `3d5459fee235d462960d7e1042ff87e6e6f40de9cf2962e2fd315f7433bc2118` 引用链逐项匹配；manifest 两个公开文件 count1、host count1 和三档归档副本相同。run 输入固定这份 completion 与 summary，三档 invocation 均使用同 prepared、runtime_cpu_v2 Python 路径和 R14 PYTHONPATH。这里确认归档调用与 SHA 链，没有独立保存运行时 Python 二进制或其完整环境快照。

当前材料身份：revision `dvc6954-behavior-v1-draft`，registry `815811717d21fa259b354eaf85a1598241d66d85b5af547d9208b2835c4edace`，effective patch `52c6a71bba1b1ca9f067d9846006dc5f2af9ecb0dde107f8a4ee75519c0b33fc`；grading digest `b52115d1d2cfc212db95f2a2bafe71c7e8c2c7d1f9a6a3a6d020130d20e7025e`，environment digest `c8cde31e2160b7caa94884d54e45a48f2527a744e2bb1ecb3789f502ebc6e311`，materials identity `77a22ff0a47782cb689525fc0ac48a7b2828bf931b17c887ea0d42683e067bfa`。host、ledger、diagnostics 的同题绑定相符。

## 三方实际执行与逐节点重建

正式命令均为 `pytest -rA tests/func/params/test_show.py tests/unit/utils/serialize/test_python.py`；完整日志各写 `collected 26 items`。从实际 `PASSED/FAILED <完整ID>` 汇总行逐行提取，独立重建状态，然后与原参考绑定、diagnostics 分区、ledger report 核对；没有使用作者矩阵的 actual_states 来生成结果。

| 候选 | 实际通过／失败 | 原绑定 F2P | 新增 F2P | P2P | install rc／test rc | driver／slot rc | outcome／reward |
| --- | --- | --- | --- | --- | --- | --- | --- |
| noop | 23／3 | 0/1 | 0/2 | 12/12 | 0／1 | 0／0 | unresolved／0 |
| gold | 26／0 | 1/1 | 2/2 | 12/12 | 0／0 | 0／0 | resolved／1 |
| negative_int_only | 24／2 | 1/1 | 0/2 | 12/12 | 0／1 | 0／0 | unresolved／0 |


三档 candidate exec 均 rc0、install_skipped=false、segment_completed=true、log_partial=false、失败安装命令为空；RH2_INSTALL_RC=0 与 RH2_TEST_RC=1／0／1 标记和真实 summary 一致。driver rc0 表示评分运输正常，不等于测试都通过。执行／基础设施 failure stage 与 detail 均空；原绑定与新增分区的 missing/skipped/unaccounted 均空，额外 11 个节点三档全部 PASSED。

下表列完整 26 个实际 ID；P/F 分别为 PASSED/FAILED。原参考列保留原截断参数片段，前缀均为同一 `tests/unit/utils/serialize/test_python.py::` 的对应函数；原 13 条没有被替换为新增参考。

| 完整节点 | 分区／原参考片段 | noop | gold | int-only |
| --- | --- | --- | --- | --- |
| `tests/func/params/test_show.py::test_log_errors[dvc.yaml-error_path0]` | 额外非参考 | P | P | P |
| `tests/func/params/test_show.py::test_log_errors[params_other.yaml-error_path1]` | 额外非参考 | P | P | P |
| `tests/func/params/test_show.py::test_negative_python_params_lock_and_repro` | 新增 F2P | F | P | F |
| `tests/func/params/test_show.py::test_pipeline_params` | 额外非参考 | P | P | P |
| `tests/func/params/test_show.py::test_show` | 额外非参考 | P | P | P |
| `tests/func/params/test_show.py::test_show_branch` | 额外非参考 | P | P | P |
| `tests/func/params/test_show.py::test_show_empty` | 额外非参考 | P | P | P |
| `tests/func/params/test_show.py::test_show_list` | 额外非参考 | P | P | P |
| `tests/func/params/test_show.py::test_show_multiple` | 额外非参考 | P | P | P |
| `tests/func/params/test_show.py::test_show_no_repo` | 额外非参考 | P | P | P |
| `tests/func/params/test_show.py::test_show_py` | 额外非参考 | P | P | P |
| `tests/func/params/test_show.py::test_show_toml` | 额外非参考 | P | P | P |
| `tests/unit/utils/serialize/test_python.py::test_parse_invalid_types[constructor]` | 原 P2P：`test_parse_invalid_types[CONSTRUCTOR` | P | P | P |
| `tests/unit/utils/serialize/test_python.py::test_parse_invalid_types[sum]` | 原 P2P：`test_parse_invalid_types[SUM` | P | P | P |
| `tests/unit/utils/serialize/test_python.py::test_parse_negative_float_and_containers` | 新增 F2P | F | P | F |
| `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[bool]` | 原 P2P：`test_parse_valid_types[BOOL` | P | P | P |
| `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[class]` | 原 P2P：`test_parse_valid_types[class` | P | P | P |
| `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[dict]` | 原 P2P：`test_parse_valid_types[DICT` | P | P | P |
| `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[float]` | 原 P2P：`test_parse_valid_types[FLOAT` | P | P | P |
| `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[int]` | 原 P2P：`test_parse_valid_types[INT` | P | P | P |
| `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[list]` | 原 P2P：`test_parse_valid_types[LIST` | P | P | P |
| `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[negative_int]` | 原 F2P：`test_parse_valid_types[UNARY_OP` | F | P | P |
| `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[none]` | 原 P2P：`test_parse_valid_types[NONE` | P | P | P |
| `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[set]` | 原 P2P：`test_parse_valid_types[SET` | P | P | P |
| `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[str]` | 原 P2P：`test_parse_valid_types[STR` | P | P | P |
| `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[tuple]` | 原 P2P：`test_parse_valid_types[TUPLE` | P | P | P |


noop 的 `negative_int` 在 test_python.py:35 返回 `{}`，违反 `UNARY_OP=-1` 的值断言；新增负浮点／容器在 :51 返回 `{}`，缺少 rate、values、config。端到端 lock/repro 测试实际执行到 `dvc.repro()`，因负值未提取而抛 `MissingParamsError`，缺 my_int、my_float、nested.v。int-only 修法使原 negative_int 通过，但仍缺 my_float、nested.v 且负浮点／容器断言失败；这两项是行为拒绝，未伪装成收集／导入错误。gold 全部通过。公开测试中的预期错误 fixture 输出没有被当作额外失败。

## 基线、候选和 FrozenPatch

三档基线 manifest 文件 SHA `72a642433f73e15983fd0cd9089a1b7a42a4b5a94953f5a196c67312e2c73f94` 相同，独立 canonical digest `be0c03047652bd7c8ac13b696722f056a7b498ca5dd3c12fceba519a642c8625` 与 FrozenPatch 锚相符；materialized_head、task_base_commit、stage.head 全为 `28dd39a1a0d710585ff21bf66199208b1b83cbde`。git sanitize rc0、HEAD before/after 相同、violations 空。

noop 无 candidate.patch、FrozenPatch.entries 与 projection.included_entry_paths 均空；空候选约定 SHA `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`。gold 原候选及实际 candidate.patch 同为 `50ed349f0cad3875991e03a9a4c9a01c0ff286cc18a00f1c221f121bcddb8116`，int-only 同为 `4787d6e313bb413600e1f455a123c359339d101e46d4ef4e079516e6a0c2a2f8`。两者只包含 `dvc/utils/serialize/_py.py`，git_apply 正常、分类 projectable、reason_codes 空、私有 pathset 未改变，没有测试或 conftest/fixture 候选路径。

严格解码两份 FrozenPatch 内容并重算 content SHA，分别为 `d1baddca3228a29e251a990b77bb6f852d75b69d9f3c4a9ee2cf0b4bca6b0848`／`469c0cd2f454c1ad7c93a8928143cea2485ee1af47ce48eefe19e454acf21755`。对各自实际 candidate.patch 做纯内存反向 hunk 核对（每行上下文必须匹配），均还原到同一基线字节 SHA `bcf2be648cfea2aae1a1be6066f2d30a8e4cbab22e975ad692ceda5bfb3eb233`，与 baseline 对应 entry 一致。FrozenPatch canonical digest 与 projection/ledger 锚逐项重算匹配：noop `dcbac5f544e25f37d8d75d560de023fdb2b3f35277a0a883897e1dc259b24cac`、gold `7f8899b7e77b9b123503e835be7d54e03bbeee45d975d50668e158c77db94d5a`、int-only `fab86367225c9d4bb8e49c250a5776056731f6b9ad5fde14760444d8283b0743`。

## 真实评分镜像、预检与测试文件恢复

实际评分镜像固定为 `sha256:083832998996245f4f49eaab3f5f9314fe9fe23bafda7fc9641ae8cec6803c30`，三档 ledger actual/ref、baseline/FrozenPatch runtime image 与注册 installation 一致。正式消费者明确将该固定 grader ID 配对 manifest=None；ledger `image_digest_expected=null`、identity=`local_build:<ID>`，没有把原来源 manifest `1cf3894f...` 错配给派生镜像。原来源身份仍保留在 public 与 installation 的来源 pin 中。

UID54322 candidate prerequisite 的原始 exec 结果存于 diagnostics.candidate_prerequisite：三档 user=54322、home=/home/rh2grader、rc0、stderr 空、stdout 为 `RH2_DVC_BEHAVIOR_UID54322_WHEEL_BYTES_OK=1`、state=verified。独立依据注册 wheel pins 与 source 字符串重建脚本 SHA，均为 `8eeb79a16593e4c73237adacb98f2dd9494eb831136b0cf4ac21752b34fa5092`。代码使用 Python -I、geteuid 断言、PIP_NO_INDEX=1、固定 PIP_FIND_LINKS、O_NOFOLLOW、regular file 与逐 wheel SHA；manager 在 user=54322 下执行后留存 exec 返回并要求 rc0。完整 eval.log 另含 UID0 的 trusted 检查与同 wheel 字节 marker，不能将它冒充 UID54322；本轮 UID54322 证据是独立 exec 的原始诊断字段，未另存单独日志／脚本文件。

三次 trusted 日志均证明：先核 immutable base commit 可读，`git ls-tree <base> -- tests/unit/utils/serialize/test_python.py` 成功且输出空；删除这一登记新增路径；恢复 existing test_show.py；重新核其 base SHA `b4f326a46584b7a6e4eae8462ff5018341dee1bbaf2eaef4c5dca37bbf4436eb`；再 git apply effective test patch。不是将 cat-file 错误直接猜作缺席。baseline 也没有新增 test_python.py entry，registered base_exists=false。

三档 apply rc0、RH2_SETUP_RESTORED=1、EXPECTED_TEST_FILES=2、TEST_FILES=2、ABSENT_TEST_FILES=0、IRREGULAR 空、SETUP_OK=1，control protection 正常。从完整 BEGIN/END 间只允许预期的 base64 命令 trace 和完整 base64 数据，使用 validate=True 严格解码，三次均得到 **1624 字节／56 行／SHA `291c52123b8d576780732193f2c651f3c95f695bb1976e0621736ea57f0283ae`**，逐字节等于从 effective patch 新文件 hunk 推导的文件。不是仅核日志中打印的 SHA，也不是依赖作者 actual_new_file_capture 摘要。完整 existing test_show.py 有基线 SHA／补丁／节点证据，但没有归档其 apply 后完整源码字节，故不新增宣称该整个文件实际 SHA 已另行读回。

## 公开复用、清理及限制

新 R14 rollout public payload 与 R5 成功原件完整相等，public digest `9186b41928accff7f5b576f240163c6c87c013cc9cfb219fa8a42571b3d526fb` 相同。solver prompt 字符串 UTF-8 字节相同；**prompts.jsonl 整文件不相同**，其 metadata 的 environment digest 随新私有 consumer 更新。R14 prompts 文件 SHA `120d534963bf25937dbefdd85c682450823463ab31691ad5e322bb847a2ed5b2`、rollout 文件 SHA `d9f8d6e34e7d234a2127cb98868958d879c97f7a94e723fa685c7b9e82fcee92`。R5 公开 actor 11 passed 的历史事实按既有复用报告保留，没有运行新 R14 actor。

两层清理均核：ledger.cleanup 为 removed=true、rm:ok、detail 空；process.log 的 manager_close/final_status 显示 created_total=removed_total=1、open/supply/failures 空、halted/aborted null、final rc0。另存 cleanup_readback 的两个按本次 run_id 标签查询均 rc0、stdout/stderr 空、ids=[]。这支持本次归档时间点没有该标签容器／网络残留，未声称做了新在线查询。

资源 policy 记录 UID54322、2 CPU、4 GiB、PID512、network=deny_all、64MiB shm／1GiB tmpfs、仅指定候选安装 prefix；三档 candidate 实际 UID 预检通过。但 `resource_facts=null`，没有另存正式 grader 的实际 HostConfig inspect；policy 不等于事后实际配置证明。env_qualification=absent，qualifications=0、overlay=0；不能授予环境资格。

作者 matrix SHA `3c7fb8eb75db7c19b20c564be09f152d28fe26af520791c6af3512969b2980a0` 的当前三方结果／限制与独立重建一致。旧 revision.json 的 draft/not_run 字段属于原冻结材料，不回写；旧原版安装与历史测试的正式 reward 仍未知，不能用先前私有 CPU 诊断推断。请求模板含 4166／9395 的检查条目，本请求实际固定 instance 是 6954，未附这两题新运行原件，本报告不将它们写成已核。本批 CPU 矩阵结论不等于训练 typed actor 接入、真实模型 probe 或训练资格。

## 最少原件指针与实读 SHA

全部原件位于请求列明的三个 `formal_evidence/formal6954_r14_*` 根；每行 job 下的完整 eval_log 与 ledger 是状态／计分依据，completion 与 process 是调用／退出依据，cleanup_readback 是外层清理依据。

| 候选／job | eval.log SHA256（节点行区间／新文件 capture） | ledger SHA256 | completion SHA256 | cleanup_readback SHA256 |
| --- | --- | --- | --- | --- |
| `dvc6954-r14-noop-20261003-001` | `b0c8d4074d655b88f6f68d1273e8bb55b63de00a11e96efe30662770afbfb66f`（1484–1509／258–290） | `e5263043b4c1faf5fdb4bd33f43e0764119d5028725c71b579973f5c7d21134c` | `5e5164866846d7b43168b71ba77888f1c4c46a175bf96c8807b2f28386bdd273` | `2174ecd916831603f950e245da952ab01d146fbd6bc934a5a9b8196a1464a06d` |
| `dvc6954-r14-gold-20261003-001` | `de175500ee858fa0523868b2e879252012422717dd72ce8071be751150d492ff`（1544–1569／313–345） | `3cc9cf83280ac53b61bf41562d1cbf0505aacb25360dddbe7ce42c217d2efff6` | `f6de9fdfa1e27709cc6c3d5c0f63aac17be5ef19ff6c7844fc5744ac4c6ace27` | `3577920bb44f88980ef332f11726b62024e5984d9dfcfd702a9cb3bdf0e37660` |
| `dvc6954-r14-negative_int_only-20261003-233645-a4` | `84fe2da330d4be96e079d83af486bb278be980dd021a5cfcd68b3440aba53807`（1466–1491／280–312） | `b084f10dc020526e867cc2ad50f092e9c9be2b3aef3f7dca7fcbd14e8ecfb706` | `2eb979611336f2372148c0883145ccd3540deab5d7e21d650ec2588817726008` | `52674b61e78568515accdeb7d52844bda079602d95e20ac0fcc5d6e5896b71ae` |


三档 tar 实读 SHA：noop `28c5978dcd0b12344537a3dfb91e084887432be6f59d3fde87f4c1f9fb7e8531`；gold `b89f1c7bf00b61f9547c77b78e2e5da4968c60122b85652ba7ea7ab0eeacc105`；int-only `8f2c78ef785dfad51717eb758b61fa83ae517ddfc0b55ddb70f150ab0474fe4f`。prepare process.log 实读 SHA `d05a0a19d6d71bd25e1ae40cf594f843b1ce5fea2e4eba8b5cc720a556a4dd61`，invocation `598422e9bd01982338ca40497256520f579617751cd22f0b0abd069218deb6ac`。
