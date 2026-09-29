# Conan13230：最终CPU结果

2026-09-29。**正式noop/gold/退化为0/1/1。** 原镜像可开发，gold修复已执行的公开Linux host生成路径；只排除Android的退化仍错误，却获正式1。确认 **S1/T2b覆盖遗漏**。 本稿复用既有静态审查，题主逐份读回[本轮原件](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/conan-io__conan-13230/reserve6-v1)，未重新盲审、执行项目或操作远端；运行状态executed_pending_review不替代验收。

## 公开目标与实际行为

[公开题面](../../../../../../../runs/swegym_quality_expansion_20260925/public/conan-io__conan-13230/user_prompt.txt)明确Macos armv8 build、Linux x86_64 gcc host，并故意 `raise Exception(tc.cflags)` 展示flags；没有要求实际跨编译器。已执行[公开配方](../../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs_reserve6_v1/conan-io__conan-13230/public_repro.py)的真实 `python -m conans.conan install --profile:build default --profile:host ./linux-cross --build=missing .`。先按原条件，第二遍仅加公开conf `tools.apple:sdk_path=/public-diagnostic-sdk` 作为观察哨兵，不安装SDK、不伪造xcrun。

| 实际变体 | 原条件case | SDK哨兵case | 公开旧测 |
| --- | --- | --- | --- |
| actor/base | 构造工具链时误查xcrun，rc1 | 到故意raise，两条Apple flags，rc1 | 34通过 |
| gold | 到故意raise，flags=[]，rc1 | 到故意raise，flags=[]，rc1 | 34通过 |
| android_only | 与base同样误查xcrun，rc1 | 与base同样两条Apple flags，rc1 | 34通过 |

两条错误flags准确为 `-isysroot /public-diagnostic-sdk`、`-arch x86_64`。gold两次均在 `raise Exception(tc.cflags)` 结束；base/退化原条件在 `tc = AutotoolsToolchain(self)` 先失败。诊断wrapper退出0表示完整采集，不能把所有CLI rc1等同环境失败；xcrun缺失在本题是不应到达的Apple分支证据。私有三方均UID0，只证明行为，不能替代actor权限。

## 开发条件与候选身份

原镜像无新增依赖修复或派生层；actor UID54321、Python3.10.14、Conan2.0.0、pytest6.2.5、Jinja23.1.4，实际conan/conans均从testbed导入。初态与结束git status均空，HEAD `c2001bad8aa873eaf2c392ab6e3ff8b8bdfec971`；原manifest `3f7ba164d697c75bf27b917cd2ea794c8ebefbbb3c6954113e1dc1f2d5e62376`绑定config ID `sha256:470bafe8634b5ef92f942aef63a818d7dd681ba591548d467a6f25be420806df`。原tag缺席时只是给已核immutable镜像加本地别名，未借用11594的Ninja修复。

Claude Code 2.1.205实际执行3个Bash命令，identity、公开行为及完整旧测均收齐。activation检查ok；通用 `interpreter_in_tool_result`、`bashenv_denied_for_agent` 两字段为false，实际解释器由identity/activation核实，不宣称所有检查通过或证明OS隔离。两题均未单独执行完整pip check或自主模型求解。

noop frozen entries为空，未产生candidate.patch文件。gold/退化只投影 `conan/tools/gnu/autotoolstoolchain.py`，mode100644、excluded_pathset_changed=false；candidate.patch逐字等于输入。解码整份frozen源码，逐字等于公开base纯文本应用对应patch，也与私有apply后捕获SHA一致：

- gold：13040字节，SHA `bc27d227c5ace77320acc92c99b225c03d0d27493cfae2a76fc97b7b3705b567`。
- degenerate：13025字节，SHA `27ff8904f912db9f468d35033fda856c0399121190556639bf58e04b599fd3dc`。

## 正式安装、参考与收尾

三方均实际执行原安装前缀 `cython<3` constraint及三段 `python -m pip install -r conans/requirements{,_server,_dev}.txt`（这是三条实际命令的简写），未跳过安装、未新增pin。项目按原配方通过PYTHONPATH=/testbed直接导入候选源码，不把三段依赖安装冒称额外pip editable安装。安装失败命令为空、RC0，完整安装/测试起止标记齐。实际测试为 `pytest -n0 -rA conans/test/unittests/client/toolchain/autotools/autotools_toolchain_test.py`。

| 候选 | reward/testRC | F2P | P2P | 安装秒 | test段秒 | trusted setup秒 |
| --- | --- | --- | --- | --- | --- | --- |
| noop | 0/1 | 0/1 | 34/34 | 2.311 | 1.024 | 108.195 |
| gold | 1/0 | 1/1 | 34/34 | 2.172 | 0.948 | 110.301 |
| degenerate | 1/0 | 1/1 | 34/34 | 2.346 | 0.853 | 107.394 |

noop唯一F2P在构造AutotoolsToolchain时误查xcrun并报127；这是Android host进入错误Apple分支，不是缺工具需补SDK。新增 `test_crossbuild_from_macos_to_non_apple_os` 虽在注释列Linux/Android/QNX，实际只构造Android，故 `os_host != "Android"` 退化可以全过且直接违背公开Linux题例。

全部35个原参考在每份完整日志恰出现一次，无缺失/skip、收集失败或参考外失败；三方共105个逐参考状态写入[evidence_audit.json](evidence_audit.json)。显式reference bindings为本题空映射，原/绑定后状态完全相同；未套用11594映射。三份完整日志SHA与ledger一致，且与[root冻结parser](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/conan13230_final_v1.json)逐ID一致。runner摘要安装前后不变，正式image_id_actual仍null，镜像身份依据原manifest、拉取/别名记录与frozen runtime绑定，不能补写成实测字段。

actor容器删除和stub退出均0、label容器/网络/relay残留为空；私有三方准备及内部两命令各0，完成标记和旧测数量齐，容器rm/query0且无残留。正式三方candidate removed=true；driver原终行与checked receipt一致，manager每次created=removed=1，open/supply/failures均空，final exit0、grader_open空、cleanup_failures_total0。

## 资源、当前用途与剩余事项

2CPU/4GiB、setup900、候选900、whole3600，原test预算保持。[root资源记录](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/resource_final3_v1.json)对应noop/gold/退化7/8/8个约15秒样本，采样未观察OOM/PID拒绝；ledger峰为336.137/334.383/334.754MiB，不能以较低的采样峰替换。采样可能主要覆盖准备，resource_facts仍null，不推断全生命周期零事件或最低内存。[传输对账](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_final3_v1.json)联合两Conan与MONAI6975恢复共239件、3,529,295字节远端/本地SHA一致，非本题单独数量。

当前用于开发环境、行为和奖励覆盖诊断；本批未授予任何模型比较、训练或留出资格。后续如决定受限比较，仍需统一、事先固定的语义验收与材料/预算/分母条件，原分不能单独判胜负。

已有公开repro两case可复用为D6最小验收：Macos build/Linux host必须到达故意raise且flags=[]，保留Android原参考及34项公开回归；按payload和失败位置判，不要求CLI rc0。 **D6尚未实施**，本次未改正式测试或评分。只验证Linux容器中的公开profile生成；未运行真实Mac主机、SDK、编译器或openssl构建。 完整公开题面/public_hints交付、完整pip check、自主模型及训练资格未验证；[跨包独立复核与最终卡对齐](../../reviews/reserve6_conan_pair_final_review.md)已完成，root已接收本次CPU结论。结构化结果见[result.json](result.json)，保留[运行前计划](plan.md)作为历史。
