# Conan12397 R12 正式 CPU 结果：非作者范围窄核

日期：2026-10-03。角色：Falsifier／Simplifier，核实际新结果与正式消费差异；不重做公开初判或完整题义审查。

## 结论

**本题 R12 当前四完整候选的正式 CPU 结果在本轮范围内通过独立核查：noop／gold／objcpp_only／apple_only = 0／1／0／0。** 2 F2P + 2 P2P 在四轮原日志中共 16 个实际状态逐项一致；不是 16 个不同测试。未发现实际新增 P0、P1 或 P2，最小修正：无需修改。

已有材料审查待核的两份部分修法均被正式新测试拒绝，且原因来自实际断言，不是前置失败或缺测试。正式私有补丁、完整 Frozen 候选、当前 release 与 vendor 安装入口能够对应。没有本轮范围内阻断，停止，不追加候选、实验、假想 guard 或全语义审查。

这不是 clang／Meson／libc++ 完整编译链接验收，也不证明真实首请求已交付新 brief、普通求解就绪或训练资格。原件 root audit 的 `ordinary_probe_ready=false`、`training_eligibility=not_established` 不由本报告改写。

## 16 个实际状态与拒绝依据

所有参考均位于 `conans/test/integration/toolchains/meson/test_mesontoolchain.py`。下表使用函数名，完整 nodeid 为该模块路径加 `::` 和函数名。

| 完整候选 | Apple F2P `test_apple_meson_keep_user_custom_flags` | Linux F2P `test_linux_native_clang_libcxx_link_args` | P2P `test_correct_quotes` | P2P `test_extra_flags_via_conf` | reward／pytest rc |
| --- | --- | --- | --- | --- | --- |
| noop | FAILED | FAILED | PASSED | PASSED | 0／1 |
| gold | PASSED | PASSED | PASSED | PASSED | 1／0 |
| objcpp_only | FAILED | FAILED | PASSED | PASSED | 0／1 |
| apple_only | PASSED | FAILED | PASSED | PASSED | 0／1 |

每轮日志均实际 `collected 4 items`，并有完整 Start／End 测试段与 `RH2_TEST_RC`；无参考缺席或平台 skip。四轮驱动 rc 均为 0，测试段 exec rc 均为 0，测试 rc 按表分别为 1／0／1／1；不能将驱动 rc0 当成所有测试通过。原始状态、ledger、matrix_results 和 root audit 的 16 状态相符，F2P/P2P 分区的成功／失败／缺席／skip 项与结果一致。

- **objcpp_only：**完整候选仅给 `objcpp_link_args` 加入 stdlib 参数。Apple F2P 在有效测试第63行失败，实际读取到的 cpp 参数列表没有 `-stdlib=libc++`；Linux F2P 在第174行失败，完整 `cpp_link_args` 键读取为空列表。日志分别位于 `objcpp_only` eval log 第520–545行，summary 第562–565行。两参考都拒绝它，证明后缀相似的 objcpp 键不能冒充 cpp 链接键。
- **apple_only：**完整候选仅在 Apple 系统加入 cpp 链接参数。Apple F2P 实际通过，新增 Linux F2P 第174行失败，读取的 `cpp_link_args` 是空列表（eval log 第484–487行）；summary 第504–507行。**真正排除 Apple 限域遗漏的是 Linux F2P**，不能写成它被 Apple 参考拒绝。
- **noop：**同样由 Apple 第63行、Linux 第174行的缺 stdlib 断言拒绝；旧两个 P2P 通过。失败不是安装、导入或 profile 阶段错误。
- **gold：**两个 F2P 和两个 P2P 全通过。只支持当前配置生成 oracle 范围，不替代真实编译链接。

原日志入口（相对于下文证据根）：

| 候选 | eval log 路径 | summary 行 |
| --- | --- | --- |
| noop | `output/noop/eval_logs/evallog_replay-conan12397-formal_6fbfac0f.eval.log` | 545–548 |
| gold | `output/gold/eval_logs/evallog_replay-conan12397-formal_3248c0eb.eval.log` | 480–483 |
| objcpp_only | `output/objcpp_only/eval_logs/evallog_replay-conan12397-formal_05e72429.eval.log` | 562–565 |
| apple_only | `output/apple_only/eval_logs/evallog_replay-conan12397-formal_7bbc5d1d.eval.log` | 504–507 |

## 完整候选与 Frozen 核对

plan 固定四候选，非空原始 patch 分别为 gold `a2601a41…`、objcpp_only `5dae45b8…`、apple_only `b53ab66a…`。本轮核保留的 `candidates/*.patch` 与各轮 artifact `candidate.patch` 逐字相等，并与 plan SHA 相符；没有抽取片段替代完整候选。

noop 的 Frozen entries 为空。其余三份 Frozen 均有且只有一个 regular、100644 的 modify entry：`conan/tools/meson/toolchain.py`；投影包含该完整文件，没有 ignored path 或 unsupported shape。各 Frozen `content_b64` 安全解码后，逐字内容的 SHA 与 entry 的 `content_digest` 相符。静态撤回原始 patch 的唯一新增行／两行后，三个完整文件均恢复为共同 baseline 内容摘要 `sha256:0ef440c35a0aced3c9846a5ef35eeaa380599c891e467a3ee274d4e88c8e999e`，因此不是只保留了候选差异摘要或部分实现。

| 候选 | Frozen 完整文件字节数 | Frozen 内容 SHA256 |
| --- | --- | --- |
| gold | 17327 | `9158959e91179f270568345c614a589d71fc064bc675b3f256ab88cde7f8bae6` |
| objcpp_only | 17330 | `5a58fd930e21472c762c006513f082f1b9d2513d2a41786b7fbd168e25c269c6` |
| apple_only | 17369 | `b2aab3c4a46749c5e7e7c28059ec23e3af82f50f83e069fe157ad7e877dfaae6` |

按固定 release 的 `compute_frozen_patch_digest` canonical JSON 规则独立重算，四份 Frozen digest 均与各自 projection 和 ledger 相符；四份 baseline canonical digest 也与 Frozen 相符。materialized HEAD 为 `883eff8961d6e0d96652f78e3d7d3884479e769e`，public/image 身份一致，`excluded_pathset_changed=false`。候选 touched test-like／fixture 清单为空，`runner_integrity_changed=false`，未见本轮候选通过测试文件绕过评分的迹象。

## 正式私有测试、原镜像与 vendor 安装消费

固定发布版：`cat2-cpu-r2e089092-swe21-conan-20261003-v1`；manifest SHA256 为 `3fe07ef04c88f9883b2bc3040cac425374cbd7bcd23041fc4280e17ef62e7987`。本轮独立核 manifest 字节以及七个相关 registry／test／consumer／vendor 成员的 SHA、字节数。原 runner 的发行前检查另有 `checksummed_files=1020`、rc0 留存；本轮没有全仓重审或重跑 release 验证器。

当前 prepared private grading row 与发布版 SWE21 combined 中本题 row 完全相等；其 canonical grading digest 为 `sha256:ac629d6d493f6bbbd82a429694397a66e83517da617d1487b9a0fca008d89c43`。plan、prepared identity、私有 row、registry 与每轮 ledger 一致指向：

- revision：`conan12397-private-test-v1`。
- 有效测试 patch SHA256：`7352a2fd18bcaccaa5e35ae5746b2b8a87725fa40c48972adb3b8647c8335e0b`。
- 有效测试文件 SHA256：`9d0c482b3b2c3ced8ee08798161289d71257dc728dcd1e7e20e7549b3e5f18b0`。
- registry SHA256：`dac2ff528a751e94b73e942d4a8f8f504b7cf931191a163a4bd8bce8ed409013`。
- grading materials identity：`sha256:7b653025a36ffb5e389cc0b1d98c5683d2f5974a4985468fc3a56d26475ffbe4`。
- 2F/2P 清单不变；原 Apple F2P 与新增 Linux F2P、原两个 P2P 按实际分区消费。

固定 consumer 从同一 host view 构造正式 spec。日志实际先恢复本题旧测试，核 base SHA `b457ad1b…`，受信应用有效补丁，attest 的 apply rc0／expected=present=1／absent=0／irregular为空／setup_ok=1。接着实际运行该有效模块，四个 nodeid 与当前私有测试方法对应，未只消费旧三测。

本题没有派生评分镜像覆盖：plan／prepared identity／ledger 为原来源 `xingyaoww/sweb.eval.x86_64.conan-io_s_conan-12397:latest`，manifest digest `sha256:b3192aee6c3565730fece66f36212dc2fd77f13271bb632cbb1be2ba0bb6bd55`，`image_local_build=false`，candidate prerequisite 为 null。保留的 prepared identity 记录 runner preflight image inspect 的 config ID 为 `sha256:d0b6f915791c8c4597dffc2642093dfdc864a90f122544b23561e09ad6ba90a1`，与 plan 一致；逐轮 ledger 的 `image_id_actual` 本身是 null，故不将其写成四次独立容器 image inspect 证明。

固定 `spec_vendor` 的 Conan1.54 安装串仍为 cython<3 constraint，然后安装 `conans/requirements.txt`、`requirements_server.txt`、`requirements_dev.txt`；12397 不进入其它三题的派生镜像或固定工具 prerequisite 分支。四轮日志均实际执行这三个 pip 命令，环境 activation／PYTHONPATH 为 testbed，安装段完整，`RH2_INSTALL_RC=0`，没有失败命令记录。测试平台为 Linux／Python3.10.14／pytest6.2.5／xdist3.5.0，四轮均到真实断言与 summary。四个 final driver record 均正常收尾、容器 removed、无 cleanup failure；本轮没有进行新的容器操作。

## 旧 actor 证据的适用范围

只复用 `baseline_actor_12397_r5_v1_audit.json` 已有结论：原注册 actor 的 UID54321、testbed Python／当前工作树导入、Linux clang14/libc++ profile 实际生成 native 配置，以及 base 原公开模块三项通过。它是原 release 下的受控 devcheck prompt，不能因本次正式新评分通过就变成真实首请求 issue／brief 交付记录。

旧 actor 的 Apple 公共测试通过与当前 noop 的 Apple 私有参考失败并不矛盾：当前有效补丁强化了 Apple cpp 两完整键的 stdlib 检查，并新增 Linux F2P，测试字节已改变。旧三测支持开发入口可执行；当前私有四测支持 R12 新 oracle 的实际 0/1/0/0，两者分母、用途和输入身份不同。

完整 clang／Meson／libc++ 编译链接依旧未验；brief 本身也明确此界限。旧 actor audit 的两项 generic marker check 为 false，不据此作全局权限结论。新 runner 声明 CPU2／内存4GiB，保留各轮内存峰值，但 `resource_facts=null`；本轮不声称每容器所有资源参数已实测。这些是既有证据边界，没有发现把它们升级成新的运行失败或额外审批要求的依据。

## 原件范围、独立检查与停止

原件根为 `runs/category2_repair_20260929/conan_cpu_20261003/formal_matrix_12397_r12_v1_evidence/formal_matrix_12397_r12_v1/`。读取本轮 plan、runner、input/publication/prepared 身份文件、当前私有 grading view、三份候选、四轮 ledger／eval log／diagnostics／Frozen／baseline／projection／stage 与 rc/stdout 等留存原件。remote audit 清单共68文件；独立检查本地同样68文件，所有原件 SHA 与字节数逐项匹配，无缺件或多件。

相关固定 release 只读本题 revision registry、有效测试／补丁、SWE21 combined 的本题 row，以及 prepared_task_face／spec_vendor／Frozen 合约的必要消费代码。原有 `non_author_material_review_20261003.md`、本题 revision_plan 和公开 brief 用于复用范围，不据其旧 draft／pending 文本否认新正式运行；未修改这些原件或任务状态。

关键留存文件 SHA256：

| 文件 | SHA256 |
| --- | --- |
| `matrix_results.json` | `4100a1c5db827f02cff8efb705476d6ca0367faaa780c795b3df97571b4e2077` |
| `formal_matrix_12397_r12_v1_audit.json` | `28aafb6c3dbc356207a326421263be95d0222b285c6d42fe8b877a468bcba941` |
| `formal_matrix_12397_r12_v1_remote_audit.json` | `a8d095268d0e49d829c618e07482bf04b12207e76445bf1ffc36ecbd3924a0b9` |
| `baseline_actor_12397_r5_v1_audit.json` | `f079b4a23dced9f2ceb740d7a0e9d17d00c466f88ae4af37e459e889b3283ae4` |
| 既有材料审查 | `a3ce78e2711f07a9f9b16014046209b61fb11056015b08b920b2e407bdd3e06e` |

本轮仅 stdlib JSON/hash/AST/base64/文本静态核对，未导入项目模块，未远端、Docker、pytest、Conan、实验或模型，也未重跑历史。没有向其他线程发消息。唯一新增本报告，task／board／shared 文件与前两份公开审查报告均不写入。

停止条件已满足：实际新状态与原日志无矛盾，部分修法的拒绝参考明确，完整冻结及当前正式私有消费身份对应，无实际新缺口。仅在这些原件身份变化、正式消费出现具体差异或新运行反证时再按影响范围核查。
