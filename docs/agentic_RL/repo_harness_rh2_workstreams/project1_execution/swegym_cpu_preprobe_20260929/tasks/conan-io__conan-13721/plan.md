# Conan 13721：reserve6 CPU 准备（2026-09-29）

状态：材料/语法与精确 base 核对完成，尚未运行。复用既有静态卡与审查，不是重新盲审。root 统一远端执行；本题不改正式题面/测试/评分或生产。

按题面共享生成模板，经 `{% from ... import generate with context %}` 向宏传递 profile_name；alpha/beta 两个无后缀软链都指向同一 `_generator`。真实 `python -m conans.conan install . -pr:b default -pr:h ./alpha`（再 beta），由 configure 打印收到的 user conf。base 应两次空值，gold 应 alpha/beta；后缀是否包括扩展名仍是 P5 范围限制，本控制不代替该决定。

退化 `realpath_name.patch` 在取 basename 前解析真实路径：两个软链都得到 `_generator`，直接违背公开按入口名称生成用途。旧模块 6 项三方应完整通过（其中一个旧 test 仅常量非空断言，不能扩大其证明力）；正式 1 F2P/6 P2P 不含软链/with-context 组合，实际得分待运行。

原镜像固定 `xingyaoww/sweb.eval.x86_64.conan-io_s_conan-13721@sha256:05df007b940aa6495e4ee237a820125c046c683c3b782f0ea8b39290bf6837e5`。历史 baseline01 requirements 安装和目标模块已完成，没有本题依赖修复证据；保留原三段 pip requirements 安装，不复制 Conan11594 Ninja 修复，也不安装 SDK。实际 Python/Conan/pytest/Jinja2、导入路径、HEAD、dirty 和 freeze 由 actor identity 采集，历史版本不冒充本轮事实。未知缺包/工具/CLI 异常即停，取得真实证据后另版修复并原命令复验。

[输入与 SHA 清单](../../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs_reserve6_v1/conan-io__conan-13721/input_manifest.json)、[公开命令](../../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs_reserve6_v1/conan-io__conan-13721/public_commands.json)、[原始身份/安装/参考绑定](../../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs_reserve6_v1/conan-io__conan-13721/private/evidence_binding.json)、[实际补丁字节核验](../../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs_reserve6_v1/conan-io__conan-13721/private/patch_validation.json)。公开命令只来自题面/base，私有补丁/原参考不发给 actor。

执行入口：[conan_reserve_followups_v1.py](../../../../../../../rh2/experiments/swegym_cpu_preprobe_20260929/conan_reserve_followups_v1.py) `--task conan-io__conan-13721 --attempt reserve6-v1`。本地输入复制到远端 `/work/swegym_cpu_preprobe_20260929/inputs_reserve6_v1/conan-io__conan-13721`；消费已冻结 `code_v1` 与 `prepared/private/gold/reserve6_v1`。端口 18107。原 actor → 私有 base/gold/退化 → 正式 noop/gold/退化；无依赖修复则不伪造 revised actor。

停止条件：未知异常、导入/collection/超时、命令缺失/截断、base/gold行为控制不符、旧测数量不符、投影源码 SHA 不符、安装未完成、参考缺席/skip、noop/gold 正式预期变动、完整测试/双层清理不齐。退化正式 1 是待解释数据而非资格。私有 root 不是 actor 权限；helper 0 必须读内层命令和完成标记。正式仍用原参考和原命令，空 reference bindings 明确表示没有本题截断映射，不套11594映射。

本批统一 CPU 准备上限 setup900、候选900、whole3600，原 test timeout 由冻结 spec 保持；2CPU/4GiB。需读回全日志、逐参考、实际候选、资源与清理并独立复核，不能由脚本完成态授权训练/比较。完整公开材料交付、自主模型及 GPU/预算仍另属资格；D6 未实施。
