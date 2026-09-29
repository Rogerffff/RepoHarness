# Conan 13230：reserve6 CPU 准备（2026-09-29）

状态：材料/语法与精确 base 核对完成，尚未运行。复用既有静态卡与审查，不是重新盲审。root 统一远端执行；本题不改正式题面/测试/评分或生产。

题面 Macos armv8 build / Linux x86_64 gcc host profiles，真实 `python -m conans.conan install --profile:build default --profile:host ./linux-cross --build=missing .`。第一遍原条件；第二遍只通过公开 conf 给 SDK 哨兵路径观察 flags，不安装或伪造 xcrun。题面故意 raise：内层 CLI rc1 不是失败验收；必须到 generate，区分构造工具链时错误调用 xcrun 与最终 `raise Exception(tc.cflags)`。base/退化预计第一遍误查 SDK、第二遍 Apple 两 flags；gold 两遍到最后 raise，flags=[]。这里没有真实 Mac 主机/SDK/编译器执行资格。

退化 `android_only.patch` 只排除 Android，保留 Linux 错误分支；公开 Linux 题例直接拒绝它。原 34 项公开旧测三方都应完整通过；正式 1 F2P/34 P2P 只增 Android 分支，退化得分待实跑，不预称误奖。

原镜像固定 `xingyaoww/sweb.eval.x86_64.conan-io_s_conan-13230@sha256:3f7ba164d697c75bf27b917cd2ea794c8ebefbbb3c6954113e1dc1f2d5e62376`。历史 baseline01 requirements 安装和目标模块已完成，没有本题依赖修复证据；保留原三段 pip requirements 安装，不复制 Conan11594 Ninja 修复，也不安装 SDK。实际 Python/Conan/pytest/Jinja2、导入路径、HEAD、dirty 和 freeze 由 actor identity 采集，历史版本不冒充本轮事实。未知缺包/工具/CLI 异常即停，取得真实证据后另版修复并原命令复验。

[输入与 SHA 清单](../../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs_reserve6_v1/conan-io__conan-13230/input_manifest.json)、[公开命令](../../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs_reserve6_v1/conan-io__conan-13230/public_commands.json)、[原始身份/安装/参考绑定](../../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs_reserve6_v1/conan-io__conan-13230/private/evidence_binding.json)、[实际补丁字节核验](../../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs_reserve6_v1/conan-io__conan-13230/private/patch_validation.json)。公开命令只来自题面/base，私有补丁/原参考不发给 actor。

执行入口：[conan_reserve_followups_v1.py](../../../../../../../rh2/experiments/swegym_cpu_preprobe_20260929/conan_reserve_followups_v1.py) `--task conan-io__conan-13230 --attempt reserve6-v1`。本地输入复制到远端 `/work/swegym_cpu_preprobe_20260929/inputs_reserve6_v1/conan-io__conan-13230`；消费已冻结 `code_v1` 与 `prepared/private/gold/reserve6_v1`。端口 18106。原 actor → 私有 base/gold/退化 → 正式 noop/gold/退化；无依赖修复则不伪造 revised actor。

停止条件：未知异常、导入/collection/超时、命令缺失/截断、base/gold行为控制不符、旧测数量不符、投影源码 SHA 不符、安装未完成、参考缺席/skip、noop/gold 正式预期变动、完整测试/双层清理不齐。退化正式 1 是待解释数据而非资格。私有 root 不是 actor 权限；helper 0 必须读内层命令和完成标记。正式仍用原参考和原命令，空 reference bindings 明确表示没有本题截断映射，不套11594映射。

本批统一 CPU 准备上限 setup900、候选900、whole3600，原 test timeout 由冻结 spec 保持；2CPU/4GiB。需读回全日志、逐参考、实际候选、资源与清理并独立复核，不能由脚本完成态授权训练/比较。完整公开材料交付、自主模型及 GPU/预算仍另属资格；D6 未实施。
