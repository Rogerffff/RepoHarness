# Moto5960／6408 R18 公开 CC 薄工具：非作者静态窄核

日期：2026-10-03。结论：**固定新工具未发现启动前静态阻断，可按既定 CPU 槽位分别执行。** 这是工具可启动结论，两题新的真实 CC 命令证据尚未验收；不等于 CPU 评分通过、自主模型修复通过或 typed actor／训练资格。

## 范围与固定字节

仅本地标准库文本、JSON、SHA-256、AST 与字节对照，未执行／导入项目、SDK、测试、Docker、CPU、CC、模型或 SSH；没有读取在途6408作业。只新增本报告，不改旧工具、报告、冻结发布或证据。审查者已接触私有对照／金标，不是公开盲读 solver。本次依照题主授权作独立窄核，不新增审批条件。

读取新 `tools/moto_two_r18_public_actor_v1/` 五件、公开命令 binding、两题原 B3 `public_read.md` 的完整命令块、原公开 base 的模块和 Makefile、新 public brief；对照已审并实跑7584的 `tools/moto_cloud_public_actor_r13_v1/actor.py`、固定 R18 内实际 DevRunner／startup／profile API，以及新安全 launcher。R18 全1419成员、原供应材料与 matrix／UID 工具的既有核验引用 [R18工具报告](moto_two_r18_offline_tools_non_author_20261003.md)，本次没有重做全发布或题级测试语义审查。7584 运行经验以 [7584独立验收](moto7584_final_cpu_non_author_20261003.md) 为依据，不跨题冒称新结果。

| 文件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| `manifest.json` | 610 | `8df46bb3a71d05288c8b50642c6661f6c606f2f22fdaaf7677903238a3a62f9c` |
| `actor.py` | 11790 | `372a398cd2a399a1a914165a8832339c5232f7059363598acdc98746881f2f7f` |
| `tasks.json` | 10255 | `c00693e62f126ce5e693488d167e0baab1576693cc72e14e55118a10b975f405` |
| `commands_5960.json` | 4239 | `0101854eef9577ef38080a99ff08ef566e6a201d7d853141af00e2e3e80f93a6` |
| `commands_6408.json` | 3029 | `670922f251bd1dbd90d408bdf86129dd4e71fadee2303b10535c72945c2742e8` |
| OWN `public_reader_command_binding_r18_v1.json` | 2032 | `d36b1d0e808e0278c8243e4ce59cce5453899d08ad3656abfee76fa7786372fe` |
| ignored `launch_moto_two_r18_public_actor_v1.py` | 7750 | `adaf4cce8304c5a7586f7afa201785866ae1817a8bc8264384ed9835f059e552` |

目录集合精确，四个 manifest 成员 SHA／bytes 均匹配且无 symlink；actor／launcher AST 可解析。binding 两题 reader路径／SHA、commands路径／SHA均与实际文件及 tasks 相同。

## 命令来源与边界

独立从原公开报告的 ` ```bash ` fenced 块按原始字节提取；没有直接接受 binding 的 true 字段。5960 原报告22770B、SHA `c2ac93029588118e7ba49745674a38096cbd9702d5b5c9f6b431e887662023dc`，共有6个 bash 块，前5块精确对应 C1/C2/C3a/C3b/C3c；6408 原报告16608B、SHA `3212cb98b0a286da9a7759f476af6bbcd0f1c0ae3f28e95602dcd74e2111739d`，共有4个 bash 块，前2块对应 C1/C2，第3块的两行分别对应 C3a/C3b。所有选入 reader 命令包括结尾换行均逐字节相同；两题可选 C4 syntax/build 均未选入。

每题仅额外加入 `INSTALL`：`cd /testbed\nmake init\n`，timeout300秒、expect zero。两题 public_dev_brief 都公开注明原安装入口；两份原 base Makefile 的 init 第17–19行均为 `pip install -e .` 后 `pip install -r requirements-dev.txt`。公开 reader 曾建议最小复现无需先全量安装；本次明确授权另补原公开开发安装证明，命令本身有公开依据，不是私有测试或修法。未新增预装／评分脚本或改公开功能要求。

| 题目 | 原 reader 命令 | 总命令数 | timeout／预期 |
| --- | --- | ---: | --- |
| 5960 | C1、C2、C3a、C3b、C3c | 6（含INSTALL） | INSTALL300秒；reader240秒；C2 nonzero，其余zero |
| 6408 | C1、C2、C3a、C3b | 5（含INSTALL） | 同上 |

新 actor 的命令条数／ID guard 接受5或6条，固定 commands 文件分别精确5／6条且 ID 唯一；完整输出 wrapper 按每条 `timeout_s` 派生。未把 reader300秒泛化，实际全部 reader240秒。每条在 `/testbed` 下运行，保留原 `TEST_SERVER_MODE=false`／`PYTHONPATH=/testbed` 和测试选择文本。

C2 的 nonzero 必须在闭合后核具体业务路径，不能用 rc1 代替复现证明。5960 C2 先完成 INCLUDE、KEYS_ONLY 两次 scan，打印两组实际字段集合，最后才 `assert all(results), "GSI scan returned attributes outside the configured projection"`；应核两组输出和最终断言，而非缺包、collection、mock启动错误。6408 C2 先核两份 manifest不同，完成创建／上传／迁移／两次读取，最终 `assert initial_image != new_image`；应核最后这个公开断言，不能将前置 manifest偶然相同、helper导入失败或其它异常算作题面 bug。C3 的旧公开测试通过也不能证明题面 bug已修复。

## R18 身份、供应与原 consumer

新 tasks 和 launcher 固定 release `cat2-cpu-r2e093-swe40-moto-offline-20261003-v1`，manifest SHA `a84bdc339618e010440df3728c982b2d1d141b1f8295f69761984386ee3a512e`；本地实际 manifest相符。两题 task_id、base、public、ENV 与已审 R18 matrix expected逐字段相同；tasks 的完整 environment 对象与 R18 matrix tasks逐字段相同，runtime ID等于其 grader_actual_image_id。

| 题目 | base／public／ENV | 原来源／实际COPY-only ID |
| --- | --- | --- |
| 5960 | base `d1e3f50756fdaaea498e8e47d5dcd56686e6ecdf`；public `sha256:a09554119b86752f15f8b2fa12eb31a559e92dc28b3334565e8b94ae50862336`；ENV `sha256:508c321ed4834474fcdf780e3411bf26aff718a2bde916f64fbf4e61e54f8c19` | source ConfigID `c67dbd…fe079d`／manifest `4b7176…ef8944`；runtime `sha256:4bafbb6965ff41c0f6eb50a73f831e7b62c41b5beda6ffad957fbc926c2359ac` |
| 6408 | base `1dfbeed5a72a4bd57361e44441d0d06af6a2e58a`；public `sha256:614eff48270224a61e540333a4588303eae4f76e5d3e259e894e78db7e16ba71`；ENV `sha256:fc3f039787ba630fe6b8a80f5a4022fea3eb418b70219f9f57b3fe76933c8f08` | source ConfigID `a00718…e2e689`／manifest `db52bf…12f8a4`；runtime `sha256:f00e022c3edf2dd23121abab802e401a64ee9e98598f07fb37a83d5c4c2012a1` |

原 public actor face 仍为各自 `xingyaoww/sweb.eval.x86_64.getmoto_s_moto-<id>:latest`，没有改 public source。工具先从单题 prepared view 构造原 `rollout_spec_from_view`，核原 source image、base/public/ENV、`grading_spec is None`；随后通过既有 DevRunner 的显式 image override 用各题已登记 COPY-only actual ID。这里没有复用 R13 的 source ID运行条件，也没有修改共享评分路径、consumer或公共契约。

`CompleteDevRunner.image_facts` 运行时将 inspect 固定source manifest和runtime ID，要求source ConfigID／RepoDigest、derived实际ID、原层前缀精确保留且只多1层、离线 PIP ENV。独立初态容器限制2CPU/4GiB/PID512/shm64MiB、network none、`--rm`且带本 attempt标签，只读可信原初态 Git HEAD／porcelain，完整输出保存。它不在该容器跑安装或读取私有评分。

两份原 workspace 模块 pin 实物匹配：5960 `moto/dynamodb/models/__init__.py` 29677B，SHA `fba195aa3985edf3616237b965aefae6ea6845c9d2591f3d814d094dd70882fc`；6408 `moto/ecr/models.py` 40991B，SHA `4df8182f9651cc5ef40ecac5defd993da7e9277e241de403b189c9b41658dc70`。**这些在 tasks 中是原公开 base 元数据，actor.py 没有自动比对实际运行模块 SHA；不能把静态 pin说成 CC 内实际 hash检查。** C1完整输出能证明顶层 Moto来源／解释器／SDK，单独 UID工具提供工作区目标模块读回；两种证据必须各按范围验收，不因UID parent0而声称 CC命令已跑。

固定 R18 内 `devcheck.py` SHA `75399297da458697ebcd17e6ca79aad90b56e4dbdda3214a4c70f82a4b389160`、`acceptance_startup_2.py` SHA `c67194f09e202c1cd1e83a3a1fbf5df7706952d2e542f97a4b2f3882604dc5d1` 均与 tasks code_pins一致，并与已实跑 R13 对应文件逐字节相同。新增actor相对已审R13源码仅改两题选择、R18 prepared／输出目录、清单条数、允许INSTALL300秒及wrapper使用每条timeout；其余受限初态、trusted root exec、完整捕获、首请求核验及清理子类代码未变。旧 CAP目录名／模块装载别名含r13只是容器内局部名称，实际repo、release、prepared路径／hash均绑定R18，不代表复用了R13 prepared。

## 实际启动、公开 prompt 与身份边界

原 DevRunner 复用 production sanitize→trusted init→写入原 activation文件→prelaunch→agent activation→`ClaudeCodeDriver.run` 顺序。rollout profile固定 `agent`／UID54321，没有agent UID／user环境旋钮；资源2CPU/4GiB/PID512 guard保持。实际受限actor profile、64MiB默认shm、caps／no-new-privileges、激活解释器、HOME/BASH_ENV、SDK仍须读取这次 prelaunch／activation／trajectory原件；静态不能跨题沿7584实际值宣称已验。

CC平台包固定 SHA `d3dadfa9cde294ac82c755eb6d889291228849180bac5d677ad1a4027aca1bc4`（原CC2.1.205），stub18193、gateway18192保持。stub启动前尝试独占bind，启动后核子进程存活；经原relay/internal attempt network提供受限模型proxy通信，不把actor网络误写成network none（只有初态探针是none）。无自主模型：确定性stub按原公开command list依次给真实CC Bash tool_use，最后end_turn；每条CC工具timeout为命令预算加30秒，原whole wall1800秒及outer1800+300 guard保持，max-turns按命令条数n+3派生。

host读取prepared/private仅为原load_context；agent实际收到 `spec.prompt` 来自safe rollout view，传给原 `module.main --prompt`、原 `ClaudeCodeDriver.run(prompt=ns.prompt)`。没有将private grading、test patch、gold、对照或修法写入prompt或stub command。执行后工具将读取 `stub/requests/messages_000.json`，要求原prepared prompt在user文本中准确出现一次，并记录prompt／实际首请求SHA。此代码路径核实不等于现在已有实际首请求；必须等新作业完整trajectory及messages原件才能证明实际送达。

所有root exec使用production `TRUSTED_ROOT_EXEC_PREFIX`；非root取回设置原HOME并以agent执行。原post-run facts整段含`git status`，子类将**整段**转agent，记 `post_run_fact_actual_role='agent_uid_54321'`，防止root读取候选可控制的Git。旧 `post_run_facts_root.txt` 文件名保留，不是root权限证明；后续清理若root受控终止agent进程也是另一个事实，不据旧文件名混淆角色。

## 完整捕获、失败和清理

wrapper完整保存stdout/stderr合并输出、真实rc、字节数；wrapper自身exit0用于让CC继续清单，不替代原命令退出。collect以agent cat `.rc/.bytes/.full`，核取回rc与实际字节数，写各条完整捕获及SHA，不使用旧200000B截尾。完整输出本身保留真实业务异常；最终要求条数等于清单、rc只允许0/1且符合每条zero/nonzero预期，故124/137 timeout、make init2等不会算正常完成。INSTALL expect0并且完整stdout/stderr保留，不能把wrapper0冒称make init0。

原 `pytest_counts` regex要求带等号的summary，公开`-q`输出可能给null；null不是零测试或失败证明，必须读完整实际pytest输出。两项旧checks按专用marker扫描：`interpreter_in_tool_result`要求tool_result含 `RH2_SYS_EXECUTABLE=...`，`bashenv_denied_for_agent`要求 `RH2_BASHENV_WRITE=DENIED`；新公开清单没有这些marker形状，wrapper只回rc marker，预期可能false。工具没有把它们重写为true，只选择与本清单相容的host_log/message_start/result/log_complete/all_commands_ran，并另核真实prelaunch／activation及C1原件。闭合报告要注明false的具体适用边界，不能静默写“所有checks通过”。

原 DevRunner main 对取消走 finally cleanup；初始化／初态失败也进入同一收口。只清理本次container、relay、attempt network、stub及本attempt `rh2.run_id`标签对象。继承的首次查询字段不是全部清理依据：DevRunner后续对自有容器／网络重新查询，失败写 `<container_query_failed>`／`<network_query_failed>`，不会当零残留；最终工具要求 residual_after_force=[]、relay/network failures空。实际container_rm、stub_rc、force删除结果和双查询必须原件读回，不凭summary布尔值替代。没有全局清理／删除历史证据。

## 安全 launcher 与结论

launcher只接受5960／6408及对应CPUjob；从本地已运输闭合CPUjob invocation核instance／execute=true／**external_release_manifest_sha256等于R18固定SHA**，从其transport receipt核全SHA/bytes匹配且parent0。prepared summary SHA由已回收本题原件计算，远端路径从其固定remote_output派生；actor还要求summary位于`moto_r18_offline_v1`下、SHA匹配、单题TID及R18public/ENV一致。不能用旧R13的prepared或错release invocation通过这些条件。

运输前核本地五件精确集合／manifest；远端预检不覆盖已有错字节，运输后逐SHA/bytes／非symlink，chmod文件0444目录0555，已有transport receipt须完全相同。经原 `cpu_slot.py --mode run --package swe_moto` 使用独占新actor job，固定R18PYTHONPATH／解释器／CC包／relay port并清除overlay。连接调用capture，运行stdout/stderr仅写本地自有文件；用户输出仅中性job/receipt/rc，异常仅type与中性说明，不打印host/key/SSHargv/raw连接错误。本审查没有启动此launcher。

**无需现在修复的具体工具阻断。** 闭合后应独立核运输成员、父job/CC/harness正常终局、首实际request与原prompt、完整trajectory中全部Bash及tool_result、11条命令各自完整输出/SHA/bytes/真实rc、两题C2具体公开断言、安装0及C1/C3实际来源/收集/运行、生产prelaunch/activation资源/身份、真实post-run角色与完整finally清理。新的UID安装原件、CPU评分矩阵、真实CC公开开发证明各有用途，不互相替代。

本工具不export FrozenPatch、不grade、不修改参考、不替换旧raw，也不运行自主模型。普通确定性开发探针即使全部完成，仍不能据此授予typed训练actor资格。上述后续要求只是本次原件验收范围，不机械重跑旧证据、不扩大公开功能契约。
