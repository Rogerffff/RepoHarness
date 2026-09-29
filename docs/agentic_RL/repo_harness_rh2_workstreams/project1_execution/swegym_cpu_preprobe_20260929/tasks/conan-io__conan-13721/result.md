# Conan13721：最终CPU结果

2026-09-29。**正式noop/gold/退化为0/1/1。** 原镜像可开发；gold在无后缀软链alpha/beta场景正确，realpath退化丢失入口名却获正式1。确认 **S1/T2b覆盖遗漏**；后缀P5未消解，当前仅诊断。 本稿复用既有静态审查，题主逐份读回[本轮原件](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/conan-io__conan-13721/reserve6-v1)，未重新盲审、执行项目或操作远端；运行状态executed_pending_review不替代验收。

## 公开目标与实际行为

[公开题面](../../../../../../../runs/swegym_quality_expansion_20260925/public/conan-io__conan-13721/user_prompt.txt)要求多个profile软链共享生成模板，并通过 `with context` 让宏使用入口的 `profile_name`。[本轮公开配方](../../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs_reserve6_v1/conan-io__conan-13721/public_repro.py)建立无后缀alpha/beta软链，二者指向同一 `_generator`，模板从 `_macro` 导入generate with context。真实CLI为 `python -m conans.conan install . -pr:b default -pr:h ./alpha`，再运行beta；由recipe.configure输出实际user conf。

| 实际变体 | alpha渲染 | beta渲染 | CLI退出 | 公开旧测 |
| --- | --- | --- | --- | --- |
| actor/base | 空字符串 | 空字符串 | 均0 | 6通过 |
| gold | alpha | beta | 均0 | 6通过 |
| realpath_name | _generator | _generator | 均0 | 6通过 |

三方原始输出的输入profile conf与configure marker一致，软链真实目标均为 `_generator`；不以wrapper0代替值判定。gold使用入口basename，退化先realpath再basename，两个不同入口因此被合并。旧6测其中一条旧test仅作常量非空断言，不能扩大其证明范围；其它旧测实际完整运行。私有三方均UID0，不等同actor权限。

## 开发条件与候选身份

原镜像无新增依赖修复或派生层；actor UID54321、Python3.10.14、Conan2.0.4、pytest6.2.5、Jinja23.1.4，实际conan/conans均从testbed导入。初态与结束git status均空，HEAD `0efbe7e49fdf554da4d897735b357d85b2a75aca`；原manifest `05df007b940aa6495e4ee237a820125c046c683c3b782f0ea8b39290bf6837e5`绑定config ID `sha256:e5e14326d6e58a37cc8c39bcaf67a4130d49a2cd8116f0decd60f6cd9a4c48f4`。原tag缺席时只是给已核immutable镜像加本地别名，未借用11594的Ninja修复。

Claude Code 2.1.205实际执行3个Bash命令，identity、公开行为及完整旧测均收齐。activation检查ok；通用 `interpreter_in_tool_result`、`bashenv_denied_for_agent` 两字段为false，实际解释器由identity/activation核实，不宣称所有检查通过或证明OS隔离。两题均未单独执行完整pip check或自主模型求解。

noop frozen entries为空，未产生candidate.patch文件。gold/退化只投影 `conans/client/profile_loader.py`，mode100644、excluded_pathset_changed=false；candidate.patch逐字等于输入。解码整份frozen源码，逐字等于公开base纯文本应用对应patch，也与私有apply后捕获SHA一致：

- gold：16848字节，SHA `8a9adf4ba9b122fdda24ef4afa874eb610eb4dd5d7f3c8561c2a1e1a7c3f55f6`。
- degenerate：16866字节，SHA `ef928b72a7cf6981d36f95f6bec30c5dc03a754735a8dfe6cfbc3ed78358c11d`。

## 正式安装、参考与收尾

三方均实际执行原安装前缀 `cython<3` constraint及三段 `python -m pip install -r conans/requirements{,_server,_dev}.txt`（这是三条实际命令的简写），未跳过安装、未新增pin。项目按原配方通过PYTHONPATH=/testbed直接导入候选源码，不把三段依赖安装冒称额外pip editable安装。安装失败命令为空、RC0，完整安装/测试起止标记齐。实际测试为 `pytest -n0 -rA conans/test/integration/configuration/test_profile_jinja.py`。

| 候选 | reward/testRC | F2P | P2P | 安装秒 | test段秒 | trusted setup秒 |
| --- | --- | --- | --- | --- | --- | --- |
| noop | 0/1 | 0/1 | 6/6 | 2.240 | 1.760 | 108.100 |
| gold | 1/0 | 1/1 | 6/6 | 1.952 | 2.113 | 109.625 |
| degenerate | 1/0 | 1/1 | 6/6 | 2.321 | 2.143 | 107.296 |

noop唯一F2P在第一遍普通文件foobar的输出断言失败，actual profile_name为空，不是安装/collection故障。新增 `test_profile_template_profile_name` 一个节点包含五次install，覆盖foobar、foo.profile（明确保留扩展名）、default、baz和include_default；均是普通文件，未覆盖软链+with-context流程。realpath退化因此全过，却违背公开按软链入口名共享模板用途。

全部7个原参考在每份完整日志恰出现一次，无缺失/skip、收集失败或参考外失败；三方共21个逐参考状态写入[evidence_audit.json](evidence_audit.json)。显式reference bindings为本题空映射，原/绑定后状态完全相同；未套用11594映射。三份完整日志SHA与ledger一致，且与[root冻结parser](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/conan13721_final_v1.json)逐ID一致。runner摘要安装前后不变，正式image_id_actual仍null，镜像身份依据原manifest、拉取/别名记录与frozen runtime绑定，不能补写成实测字段。

actor容器删除和stub退出均0、label容器/网络/relay残留为空；私有三方准备及内部两命令各0，完成标记和旧测数量齐，容器rm/query0且无残留。正式三方candidate removed=true；driver原终行与checked receipt一致，manager每次created=removed=1，open/supply/failures均空，final exit0、grader_open空、cleanup_failures_total0。

## 资源、当前用途与剩余事项

2CPU/4GiB、setup900、候选900、whole3600，原test预算保持。[root资源记录](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/resource_final3_v1.json)对应noop/gold/退化8/8/7个约15秒样本，采样未观察OOM/PID拒绝；ledger峰为345.312/346.75/347.473MiB，不能以较低的采样峰替换。采样可能主要覆盖准备，resource_facts仍null，不推断全生命周期零事件或最低内存。[传输对账](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_final3_v1.json)联合两Conan与MONAI6975恢复共239件、3,529,295字节远端/本地SHA一致，非本题单独数量。

当前 **diagnostic-only，不进模型比较分母**。题面示例用带 `.jinja` 的入口，但宏拆分示例传入不带后缀的名字；正式参考要求保留扩展名。本轮只用无后缀入口隔离并证实软链遗漏，没有消解公开目标的后缀P5。需先明确范围并确认可接受正对照，才可另行决定受限比较，不能靠事后语义审计绕过P5；训练与留出资格同样未授予。

已有无后缀alpha/beta软链+with-context真实CLI可作为D6最小控制，必须分别渲染alpha/beta；保留原6测和已有非软链参考。后缀验收仍需依据明确公开范围形成版本化材料，不能由gold或原隐藏断言自动新增题义。 **D6尚未实施**，本次未改正式测试或评分。后缀是否应保留仍为P5公开范围歧义；本轮无后缀软链正反对照不解除该限制。 完整公开题面/public_hints交付、完整pip check、自主模型及训练资格未验证；[跨包独立复核与最终卡对齐](../../reviews/reserve6_conan_pair_final_review.md)已完成，root已接收本次CPU结论。结构化结果见[result.json](result.json)，保留[运行前计划](plan.md)作为历史。
