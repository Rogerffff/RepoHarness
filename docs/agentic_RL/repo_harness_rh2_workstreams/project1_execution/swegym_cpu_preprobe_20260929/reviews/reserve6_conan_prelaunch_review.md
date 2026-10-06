# Conan reserve6 预发窄审

2026-09-29，Pydantic 题负责人交叉复核。仅本地读原题、base、输入、冻结入口与指定历史原件，未运行目标项目或远端，未改作者材料；这是已有上下文下的窄审，不是 fresh 盲审。

**预发接受：目标路径、候选语义和正式空 binding 未见阻断；两处清理判据已补齐。** 最终脚本 SHA `1be9fe84c0a02d7277b3e0950394214ca76734b7dc72f0733805b0e2b66c4693` 已本地重算并通过 AST 检查。首轮审阅脚本 SHA `faf6b4b9b34ffad2dc358174a670ffffdb137658f2d5484b561577f40baf2e96`。两输入 manifest 为13230 `562d37f9c740038e53c86bccc4208f2749144203ac7c67ebab2182e3f984e421`、13721 `298d6adebd8f58602c96a16ab4236ede9db3aae1d4525eddd2da72f125bc9e37`，全部文件哈希已重算一致；本次仅回读下述清理差异，未重复材料审查；运行后不热改该冻结版。

## 清理差异复核（已完成）

1. `Campaign.actor` 当前仅核最终 Docker 残留及 network/relay failures。冻结 devcheck 的 `residual_after_force` 只复查 Docker 容器与网络；父 Runner 的 stub 超时 kill 后可能留下 `stub_rc=null`，此时它不由 residual 表达，devcheck 自身也不据此改退出码。请显式核 `container_rm==0`、`stub_rc==0`、两个 labeled leftovers 空及最终 residual 空；network/relay 字段宜用明确空列表，未知不当作成功。这样清理未知不能进入 private/formal。
2. `Campaign.grade` 目前核 footer open/顶层 failures/final exit，但缺 `manager_close.containers_created_total == containers_removed_total == 1`、`supply_open==[]`、内部 `cleanup_failures==[]`；建议同时核 final 的 `grader_containers_open==[]` 和 `cleanup_failures_total==0`。这些是已由冻结 driver 返回的实际字段，不需修改生产或新造证据。

修订版 actor 已显式要求 container_rm/stub_rc 为0、两组 labeled leftovers 与最终 residual 为空；formal 已显式要求 created/removed 各1、open/supply/internal cleanup failures 为空及 final 退出0、无剩余容器/清理失败。两处均在进入下一阶段或候选之前检查，缺字段不能通过这些新增检查。network/relay 沿原失败列表检查；本次正常 formal actor 流程由冻结 Runner 写出对应字段。上述两项整改已核销，无剩余预发阻断。

取消路径已有 TERM 等180秒、KILL等30秒，异常上抛并在 finally 保存step和整题状态，不继续后续候选；不要求扩大框架。上列首轮发现属于清理信息遗漏，现已补齐，不是目标行为存在规范争议。

## 13230：真正经过 generate 的两条路径

公开原题明确 Macos/armv8 build、Linux/x86_64 host，实际编译器不必存在，并故意 `raise Exception(tc.cflags)`。输入按此配置独立 CONAN_HOME，经 `python -m conans.conan install`、真实 recipe `generate()` 和 `AutotoolsToolchain`，没有用 mock 参数替代该路径。

base 的源码在 `os_build == 'Macos'` 时无条件进入 SDK 查找；`apple_sdk_path` 先读公开 conf，否则调用 xcrun。Linux 宿主的原例预期先在 toolchain 构造处遇 xcrun 不存在；第二条仅通过公开 `tools.apple:sdk_path` 提供哨兵路径，使同一错误分支可走到故意异常并显示 `-isysroot /public-diagnostic-sdk`、`-arch x86_64`。命令要求 CLI rc1、Calling generate、对应出错行；xcrun 只接受原例构造阶段，哨兵例必须到故意 raise。外层再比对两行结构与 flags，不能把任意非零视为复现。SDK路径不是文件存在/编译通过声明。

gold 以 host 是否 Apple 为条件，两个 Linux 例应均在故意 raise 得到空 flags；Android-only 退化对 Linux 保持原错，却满足原新增 Android 用例。该退化有明确公开原例反证，正式能否误奖仍待实际运行；不能从静态补丁先写 reward1。旧整模块34项的执行与完成也单独检查。

## 13721：请求的软链名与模板目标名

公开需求明确多个 profile 名应可作为软链共享一个生成器，并由全局 `profile_name` 分解。两条无后缀 alpha/beta 软链同指 `_generator`，实际 CLI install 经 profile_loader、Jinja `from ... import ... with context`，在 configure 读并打印生成的 conf，确实观察模板结果。base 未定义该变量时 Jinja 输出空串；conf 的空值解析仍为空字符串，预期不是 `None`。gold 使用请求路径 basename，分别得到 alpha/beta；realpath 退化错误得到同一 `_generator`。这个差异直接对应公开软链需求，不是从 gold 代码形式定义“正确”。

公开例中的 `.jinja` 后缀如何纳入变量仍属既有范围问题；本控制刻意选择无后缀，不回答后缀争议，也不把本次窄行为通过推广为整题用途解除。旧整模块6项保持独立；输入没有把私有补丁或隐藏断言传入 actor。

## 冻结入口、来源与正式评分

4个 FROZEN 入口 SHA 与本地 code_v1 快照一致。已读预算 wrapper、recipe wrapper、reference_bindings：`--bindings` 的顶层字典非空，因此满足 wrapper 的输入要求；任务内 `bindings={}` 使原 parser 的 states 和原 F2P/P2P 原样保留，没有替换任何参考键。recipe=None，不替换安装行或候选测试脚本；只增加版本化 parser 审计及该 run 的独立 grader label。setup900是本批已授权准备预算，原测试/全评分预算沿冻结入口。

本人核两题 prepared host-view 行 SHA、原 grading 的 base/test_patch/全部参考，gold 输入与 remote/gold/reserve6_v1 逐字一致。指定历史 noop/gold 原日志 SHA 匹配，13230的1+34及13721的1+6参考均可按完整 nodeid 在原日志找回（noop F2P失败、gold通过、P2P全过），无须复制11594的参数别名映射。历史安装可定位但不代替本次原镜像实际安装验收；若依赖失败，现脚本停止，不把11594缺 Ninja 根因套过来。

两份base目标文件及每题两补丁均用纯文本逐hunk重建并核 applied SHA/AST；与 patch_validation 一致。私有容器 apply前后有完整目标文件 SHA，正式完整 frozen export 再核同一 applied SHA，因此源码对照可达。新run实际镜像由 immutable digest 拉取，再核 prepared公开tag为同ID，actor、private和formal均沿此原镜像；没有派生安装层或空推断的SDK恢复。

安装失败、参考缺失/skip、测试段不完整、源码投影不符、控制组结果异常均停止。退化得1只留待误奖审查，不提前认证。脚本 AST 与所有内联 Python 命令均只作语法检查，没有执行项目。

证据入口：[脚本](../../../../../../rh2/experiments/swegym_cpu_preprobe_20260929/conan_reserve_followups_v1.py)；[13230输入](../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs_reserve6_v1/conan-io__conan-13230/input_manifest.json)；[13721输入](../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs_reserve6_v1/conan-io__conan-13721/input_manifest.json)。本稿不证明新run已执行、全部清理已成功或训练资格。
