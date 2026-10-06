# DVC5839 R10：真实正式 CPU 三方矩阵非作者读回（2026-10-03）

结论：本轮没有新增阻断。R10 新 prepare 下 noop／gold／固定 precision=8 三条官方正式评分原件支持正常 reward **0／1／0**，不是 infra／None；完整 23 节点恰好覆盖 2 F2P＋21 P2P，无额外、skip、missing。固定 8 只在 added_f2p 的真实数值行为断言失败。prepare 来源、候选 patch→baseline→FrozenPatch→projection 字节关联、UID54322 固定 wheel 预检、真实安装／测试退出及两层清理均一致。

审查者已读私有材料及此前结论，不是 fresh 公开读者。只读固定请求原件与 release 声明成员，用 stdlib SHA／JSON／日志解析、离线内存补丁和纯脚本文本重建；没有运行正式入口、项目／维护测试、SSH、Docker、安装或新 CPU，没有改共享代码、题卡、结果或旧 evidence。公开 actor 本报告未纳入，另存独立报告。

## 范围、版本与新 prepare

固定请求 `reviews/formal5839_r10_runtime_review_request_20261003.json` 实际 SHA256 `0919c5d26f2dc1a74b221dfc2daccb1162f652fa6264781b960bbb05a2d27190`；109／109 份所列原件 SHA 匹配。R10 外部 manifest `runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe14_preflight_v1/manifest.json` 实际 SHA256 `00ac5c375629f59543f548fbc7b0cb3cbe7d1418f7a956d9deebcefab2e8a87c`；950／950 声明成员实际尺寸与 SHA 均匹配且路径在 release repo 内。该清单明确包含官方 replay_grade.py 与被核消费代码，不把声明集合校验说成额外文件全目录清点。

release 为 `cat2-cpu-r2e089092-swe14-preflight-20261003-v1`；封装 v2 SHA256 `16a78e7019827e126d0788dcbb4bf13bd0ce913a9df842b79b9c110e75dc24c0`；官方 replay_grade.py SHA256 `d36fa3367415e573305a7a03619f51e7cbd358627569f3844d5c203b70d66db3`。support receipt SHA256 `212593584592dd57cb3c7eecf87863a4a9394cc2bfe58562f9a871586d8eac48` 只是部署／支持导航，实际结论从本轮运行原件重建。

三份归档根均在 `runs/category2_repair_20260929/repository_work/swe_dvc/formal_evidence/`，分别为 `formal5839_r10_noop001_v1/`、`formal5839_r10_gold001_v1/`、`formal5839_r10_hardcoded001_v1/`。各根 `formal/jobs/<job>/` 下保存官方过程、ledger 与 cleanup；同根 `slots/<job>/` 保存进程原件。三份归档的 prepare 输入、prepared／private、成功 prepare completion 完全相同，不是三次不同 prepare。

实际 prepare job `dvc5839-r10-prepare-20261003-001`：UTC 2026-10-02 21:20:12–21:20:22，官方 prepare／封装／slot 均 rc0，使用 R10 repo、独立 `formal_jobs/dvc5839_r10_v1/{prepared,private}` 和单题 `swe_gym_lite::iterative__dvc-5839`。invocation 与 completion 命令相同；completion 绑定 prepare input、release manifest、自身 runner 与 runtime Python，process.log 的 SHA 相符，prepared manifest 时间位于该 prepare 区间。run 固定相同 completion SHA，并与同题目／release／runner／runtime 及实际 summary SHA 一致；没有换绑旧 prepared。

| 来源链原件 | 实际 SHA256 |
|---|---|
| prepare input | `5f4157f0efda911a8ea49fada69e2e511de6409a9650ba580bf1e7097371b42e` |
| run input | `5835b85f79392536bd995b29abd3a222651ebac18829163c3e48ea3d7e120db6` |
| prepare completion.json | `f08c1bd26195c31a369b1d184df9ef9f766621165ad9c1d277e20ea01a2a4f16` |
| prepared/replay_summary.json | `8f11b6f53548c262901ac7f40698a94191ffa8d3f1857a7f81aa627556bd8d04` |
| prepared/prepared_manifest.json | `717d252c3b9b1ea84d21ea09f40c9380deecd7e421740bc7c8ec0469df88917f` |
| prepared/prompts.jsonl | `0888a8ae6f9570cfc737444cbd3a3e31b428dc10390a16a7899ecd5092d32694` |
| prepared/rollout_task_views.jsonl | `bd9cf7c5da26fbd694d289603372400ac885c717b37ca90557abae28b757a5cf` |
| private/host_grading_views.jsonl | `dc326026c895190e0745e4e05f84cf806a860452dfcb7958eee8fd734032364d` |

summary→manifest→prompts／rollout／host grading SHA 链全部相符；task_count 与 jsonl count 均 1；public bundle `a4d44e026d6dc40e7542bc122bd8e0365c68583519f157bc48e2eb66427adba0`、environment `7a3fc2a3619cb666dd4293d54cd83168c15642f6b0b4d14381bbfd1fafb33950`、grading bundle `9b10972c8de81eb7fedfab53973e59a18a61afa11296edadf8503781cca1db89` 与 ledger revision 对齐。

有效 revision `dvc5839-precision-values-v1`；实际 host-grading test_patch 文本 SHA 为 `1acc81a67bca0511b78f515d0d777a00ceeca3725b7907ee741764d1e623540f`，与输入、revision 和此前材料审查一致。原 1 F2P＋21 P2P 保留，仅 added_f2p `test_metrics_show_precision_real_values`；公开语义、原断言保留及新数值目标复用 `reviews/non_author_5839_material_review_20261003.md`，本次实读 SHA256 `9c30a93bed6b152dbb7c1a6c874fdaaa04b8ca9620377486faec893a0b55eb23`，不重复扩审材料。

## 基线与候选投影

三条 baseline_manifest 原件相同，共 547 entries；materialized_head 与 task_base_commit 均 `daf07451f8e8f3e76a791c696b0ea175e8ed3ac1`，镜像 ID 均 `35e6260d03d9e4792df404b498ca7800a3a633eb678e27fbed9246c0fe580147`。baseline_policy_v2 只按声明排除 `.git/`、`.harness/` 及可重建缓存。canonical baseline digest 重算为 `548c0eefe25c58c53a7595addc6bc9a251290e87cbdb84f8db03ed0bbd8a4f40`，与每条 FrozenPatch 关联一致；该 canonical digest 不同于 JSON 文件字节 SHA，未混用。

baseline 记录 metrics.py 字节 SHA `a15322b578260579b778aacab78dbef930ff616a1fa7099361afdaa1a371a589`，官方测试父基线 SHA `64f7af4cebece4c559b2edf1e86e38a45c2c340ff8c395510fbca09b8e19e2ca`。从 gold FrozenPatch 解码完整 metrics.py，离线逆补丁恢复的基线字节确切匹配前者；在内存对这份基线分别应用归档 gold／固定8 patch，输出逐字等于对应 FrozenPatch content_b64，content_digest 重算也相符。未调用 git apply 或项目代码。

| 候选 | 输入／stage patch SHA256 | FrozenPatch canonical digest | 投影结果 |
|---|---|---|
| noop | 显式 empty SHA `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`；ledger patch null | `4931683830ad279578398bc67a34b62f9f9d32c65ca2b59995639b80e445a9d4` | entries／included_paths 空 |
| gold | `15078fc2c73469c535ed73bfdce45674205d0b77922f4dd082580e8be569ddde` | `8485f83bd063161e2318e67ccd8482a2255da649f47358dd894caef5bf4860d7` | 仅 metrics.py modify，传 self.args.precision |
| hardcoded_precision8 | `97b5ac9aa9645cc715f5a301f191c0534758bdcf67b6a9624d1829c07da1171b` | `8331f550adce416e650eb9c787640d60edd4fe112853b8572193590687e13605` | 仅 metrics.py modify，固定传 8 |

两份非空候选配置／候选文件／stage candidate.patch／ledger patch SHA 一致；FrozenPatch runtime image／public bundle／baseline／materialized head 对齐，各自 rollout_execution_id／physical_attempt_id 属于本 job，并与 projection 精确相同，未重绑历史 FrozenPatch。classification 全部 projectable、reason_codes 空、private pathset 与 excluded pathset 未变；projection 无 ignored／unsupported，未投影测试或共享消费器。

## 真实正式矩阵与逐参考

| job（UTC，2026-10-02） | 完整 pytest | original_f2p | added_f2p | original_p2p | install RC／test RC | slot／官方 driver RC | 正常正式 reward |
|---|---|---|---|---|---|---|
| dvc5839-r10-noop-20261003-001（21:21:12–21:25:37） | 21P／2F | 0／1 | 0／1 | 21／21P | 0／1 | 0／0 | 0，tests_failed／unresolved |
| dvc5839-r10-gold-20261003-001（21:27:13–21:31:49） | 23P | 1／1P | 1／1P | 21／21P | 0／0 | 0／0 | 1，resolved |
| dvc5839-r10-hardcoded8-20261003-001（21:34:07–21:38:16） | 22P／1F | 1／1P | 0／1 | 21／21P | 0／1 | 0／0 | 0，tests_failed／unresolved |

P=PASSED、F=FAILED。三份完整 eval.log 的 `collected 23 items`、`-rA` 逐节点及终摘要一致；23 个唯一节点键集恰等于 host grading 的参考集合。下面每个节点均带公共前缀 `tests/unit/command/test_metrics.py::`，没有缩短参数 ID 或遗漏节点。

| 完整前缀之后的 node ID | 分区 | noop | gold | 固定8 |
|---|---|---|---|---|
| `test_metrics_show` | original_f2p | FAILED | PASSED | PASSED |
| `test_metrics_show_precision_real_values` | added_f2p | FAILED | PASSED | FAILED |
| `test_metrics_show_raw_diff` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_diff_markdown_empty` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_diff_no_changes` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_show_with_no_revision` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_diff_markdown` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_show_with_valid_falsey_values` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_diff_deleted_metric` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_diff_sorted` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_show_with_one_revision_multiple_paths` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_show_md` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_diff_precision` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_show_default` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_show_with_non_dict_values` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_diff_new_metric` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_diff_no_path` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_diff_no_diff` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_show_with_different_metrics_header` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_diff` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_show_precision` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_show_with_multiple_revision` | original_p2p | PASSED | PASSED | PASSED |
| `test_metrics_show_json_diff` | original_p2p | PASSED | PASSED | PASSED |

每分区结果与 ledger／diagnostics parser partition 的 success／failure 集逐参考对齐；三条 reference_missing_count=0，skipped／missing／unaccounted 空，无 extra；apply_ok=true，stage_error、execution_failure_decision、execution_failure_stage 与 infra detail 均 null。实际不是安装／导入／收集错误。noop 原 F2P 堆栈在 test_metrics.py:138，期望传 precision=8 而实际 `_show_metrics({}, False, True, True, True)` 未传该参数；noop 新 F2P 在 :415，precision3 实际 `[0.12346, 1e-05]` 对期望 `[0.123, 0.0]`。固定8仅新 F2P :415 失败：默认 options=[] 实际 `[0.12345679, 1.483e-05]` 对默认5的 `[0.12346, 1e-05]`。gold 两者均实际 PASSED。这是本版本新增数值断言拒绝固定8的直接行为证据。

## UID 预检、安装退出和清理边界

三份 diagnostics.candidate_prerequisite 均 state=verified、exit_code=0、user=54322、home=/home/rh2grader，stdout 精确 `RH2_DVC_UID54322_WHEEL_BYTES_OK=1\n`、stderr 空。从已核 release 的纯脚本文本生成函数离线重建 SHA 为 `fe04e8a1f2a9837105539b51fa72afe82dcbde0a7ed541b776cc5d292ae9e2d1`，与原件一致；脚本先 assert 实际 euid54322，再以 O_NOFOLLOW 开四个固定 wheel、验证 regular 与完整 SHA，最后才打印标记。manager.py:3476–3480 以 profile candidate_exec_uid／home 执行该前检，因此本轮证据不是仅凭 ledger.policy 的 UID 字段推定实际身份。

四个 wheel 包括 packaging24.1、pathspec0.8.1、setuptools75.1.0、wheel0.36.2；预检 success 后，完整 eval.log 可见可信测试恢复与 `RH2_SETUP_APPLY_RC=0／RESTORED=1／TEST_FILES=1／ABSENT=0／SETUP_OK=1`，安装含固定 pathspec 与实际 editable DVC，观测版本为 `2.0.18+daf074.mod`、import 来自 `/testbed/dvc/__init__.py`。安装／测试开始结束时间标记齐全、安装失败命令集空、install_skipped=false、log_partial=false、segment_completed=true。三个候选 exec 传输 rc 都 0；真实 `RH2_INSTALL_RC=0` 与 `RH2_TEST_RC=1／0／1` 从原日志自行读回，未用成功 shell／driver 退出抹掉 pytest 失败。

ledger.policy 声明 grader 2 CPU／4 GiB／PID512、UID54322、deny_all，输入环境同样设置这些值；但当前原件没有实际 grader HostConfig／cgroup inspect 快照，resource_facts=null。因此本报告验证实际 UID 前检和执行，不将 ledger.policy 或内存峰值冒称事后实际 CPU／内存／PID／网络 inspect 验收。三条 env_qualification=absent，也未据此授予环境资格。

两层清理一致：每条正式 ledger.cleanup 为 removed=true、steps=[rm:ok]、detail 空；随后独立 cleanup_readback 的 docker ps／network ls 按本 job 的 rh2.run_id label 查询，exit_code 都 0，stdout／stderr 空、ids=[]。这支持正式 cleanup 返回及该 job 标签下容器／网络确实无残留；不是仅信清理愿望，也不声称全主机所有资源为空。

## 最少正式结果证据 SHA256

下列均为本次实际字节 SHA；每列对应上文归档的独立 run job，eval 文件在各自 eval_logs 下由固定请求精确定位。

| 原件 | noop | gold | hardcoded_precision8 |
|---|---|---|---|
| ledger.jsonl | `b4747e7656ef7cf49e80e1ab24553b62d8330736ac9ecff3b21c3de3d3aec53a` | `26f86eadc832b5b5104dda29829cbd0de330dd1d837e60da7e9281a730e3e395` | `e1988701b3edf2d2e04ab49c300922f563e1b7e8ea817d192e41b2b12f4c3ec9` |
| 完整 eval.log | `e2b6c42afa4920fcf5174a753bd523481c7707db48b7da67e7b4e9014a60c960` | `799e3e324c0787aa815a41dd691ae56825a954024a44785e357a260a6103a236` | `6edce180b5381cd170572b29f88862e00fcc9c3c51573c881eab00cba1262dcf` |
| diagnostics.json | `dd188e74cd0de01d5ee65bbc52f7864e6e2a261b73ce130a58acf721c5355053` | `1d82cc5b38f8daef3a7327cc2ee2ddf6b29dedd75a246b67a67a7bb5354df022` | `acdd9aa009465b436290202b87532b34e6a24f94b42b3fdd7dc3ac97870fb65a` |
| completion.json | `d49f93b28daf17c601564d2c16c07863be3a8329a31104a9a45fe6220d6d6944` | `7b5ec8396ac430880aefa9dc536a899242f85e50e9a22a231faf8ba5dca5c165` | `c79bd65a41720aa13890d470ad2151ea85c9c312c4719ba38b0baf5f80ee83a4` |
| cleanup_readback.json | `0b29e6d6112bc32f246021f29613c0dbbaa3a16f543437f38d043ffcce9a2cc3` | `ef709917d46ea032d2244dcadc83e43c9c8469f0d40af3920b64d90410922a8e` | `216bd4cc9d409922c069f185dff881c806059e6601149132ceea3d218588d16f` |
| baseline_manifest.json | `e3d0cb077b65a411de1c9dd87195f3e540b3652a96abf0569dc048eb61d97c46` | `e3d0cb077b65a411de1c9dd87195f3e540b3652a96abf0569dc048eb61d97c46` | `e3d0cb077b65a411de1c9dd87195f3e540b3652a96abf0569dc048eb61d97c46` |
| frozen_patch.json | `c0ff702294d5fabd201f4da25ceb4d2df99e76ded909e18ca8434b7aaf993dd7` | `814cedb277b427a7d7b23f1562e2d2c511c317aa349d512f5afeade1f1545769` | `fe1e1bd41e51931c256c1aaa34bfcd507b67daa516952a5d089ffa1ee481683a` |
| projection.json | `1d2c179f53f1212792260cda1928cfc8cc2162e545c65a2144bae6cfdc49e3c6` | `0ad8c9d7046ac0566a503db1cdd589a7bf8844e06d85ba0b6ff23148871c8454` | `f7fc72580abbcea255c88b4366962ac37929fd64dc0c04778d500a4c96ee3bf1` |

作者导航 formal_matrix_r10_v1.json 实际 SHA256 `fad934b76a1d4e2ba23a54930e9493323d12bce58b50216098bd3d4cb4d05be2`；本报告没有修改它。所有三个 tar.gz 的实际 SHA 与请求也匹配，结论以各归档内部完整原件重建。

## 用途及未验证范围

本次确认的是 R10 当前有效 revision 的这三条真实官方正式评分事实，可支持本材料的下一步，不能推广成其它 release／候选或训练资格。旧“原版固定8”的正式 reward 仍未知；此前原版私测22节点全过不能改写成正式 reward1，本轮只运行当前有效23节点，未补造旧成绩或要求旧矩阵重跑。

没有新 CPU 复跑，也没有核准本轮公开 actor（另报告）、模型解题、探针、训练／留出资格、全 host profile inspect、未声明额外 release 文件或其它四题矩阵。正常正式 reward0／1／0 已得到原件支持，与正式训练／环境／模型探针资格是不同结论。
