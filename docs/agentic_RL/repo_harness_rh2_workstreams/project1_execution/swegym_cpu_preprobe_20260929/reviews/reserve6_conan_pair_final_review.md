# Reserve6 两道 Conan：独立最终结果复核

2026-09-29。**13230与13721正式均为noop0／gold1／退化1，确认S1／T2b误奖；两题最终卡与原件一致，无新增阻断。** 13721后缀P5仍未消解，保持diagnostic-only、不进比较分母。先核公开题面、实际actor/private、正式日志与完整导出，再读题主result.md/json及evidence_audit；独立原件判定已先写入[本复核JSON](reserve6_conan_pair_final_review.json)。这是已知本批背景的跨包独立复核，非fresh盲审；未运行项目或远端、未修改作者材料/生产/参考。

原件：[13230 reserve6-v1](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/conan-io__conan-13230/reserve6-v1)、[13721 reserve6-v1](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/conan-io__conan-13721/reserve6-v1)。最终卡：[13230](../tasks/conan-io__conan-13230/result.md)、[13721](../tasks/conan-io__conan-13721/result.md)。

## Actor 与私有行为

两个原镜像均无需修复，无新wheel或派生层。actor实际UID54321，Python3.10.14／pytest6.2.5／Jinja2 3.1.4，Conan分别2.0.0／2.0.4，conan/conans均来自testbed；初态及结束git status为空。Claude Code 2.1.205执行identity、公开CLI和旧模块共3条Bash命令。capture字节数与commands_result逐条一致，activation为ok。通用interpreter_in_tool_result、bashenv_denied_for_agent为false，不能写全部通用检查通过；实际解释器由identity/activation核实。

两题公开wrapper均退出0，含义是完成指定观察，不能代替语义验收。私有三方均UID0，base准备3步、gold/退化6步全0，含apply前后完整源码SHA；不能以私有root证明actor权限。各私有matrix的stdout字节数、完成标记及两个内部命令收口一致，stderr为空。

**13230。** [公开题面](../../../../../../runs/swegym_quality_expansion_20260925/public/conan-io__conan-13230/user_prompt.txt)就是Macos/armv8 build、Linux/x86_64 gcc host；真实CLI使用两份profile及 `python -m conans.conan install`。原例有意raise tc.cflags，因此CLI rc1本身不代表失败。base/actor原条件在构造AutotoolsToolchain时走错Apple分支，因xcrun不存在127结束；公开conf哨兵 `/public-diagnostic-sdk` 允许继续观察，得到 `['-isysroot /public-diagnostic-sdk', '-arch x86_64']`。gold两种条件均到有意raise，flags=[]。Android-only退化两种条件均与base相同。三变体公开旧34项都通过。

这不是将Linux缺少SDK当成应修环境：Linux host本不应查询Apple SDK，显式conf控制又直接观测了错误flags。没有安装/伪造xcrun，没有运行实际跨编译器、Mac主机或openssl；结论限于公开profile生成路径。

**13721。** [公开题面](../../../../../../runs/swegym_quality_expansion_20260925/public/conan-io__conan-13721/user_prompt.txt)明确希望多个入口软链共享生成模板，通过入口profile_name区分。实测alpha/beta软链都指向 `_generator`，后者从 `_macro` 导入generate with context；真实CLI分别install两入口，由recipe.configure打印user conf。base/actor两次均空字符串，gold分别alpha/beta，realpath退化两次都是 `_generator`；CLI均0。三方旧6项都通过。实际输入profile conf、configure marker与readlink目标一致，既有空值和退化合并入口不是推测。

无后缀控制隔离了入口名要求，不能解决 `.jinja` 是否属于profile_name：公开示例文件有后缀，但旧宏显式传不带后缀的名称；正式新测试反而明确要求保留 `foo.profile` 扩展名。P5不因这次gold无后缀成功而解除。

## 正式原件、完整源码与绑定

| 题目 | 原参考／三方状态总数 | noop完整结果 | gold | 退化 |
| --- | --- | --- | --- | --- |
| 13230 | 1 F2P+34 P2P／105状态 | 1失败34通过，testRC1，reward0 | 35通过，RC0，reward1 | 35通过，RC0，reward1 |
| 13721 | 1 F2P+6 P2P／21状态 | 1失败6通过，testRC1，reward0 | 7通过，RC0，reward1 | 7通过，RC0，reward1 |

完整日志逐键核对全部126状态，恰各出现一次，无缺席、skip、额外/段外结果或参考外失败。13230唯一失败是 `test_crossbuild_from_macos_to_non_apple_os` 中Android host错误查xcrun；13721唯一失败是 `test_profile_template_profile_name` 首个foobar安装后的空名称断言。均到达目标测试，不是安装、导入或收集故障。

六次均执行原 `cython<3` constraint及requirements、requirements_server、requirements_dev三段pip安装，安装RC0、failed_commands为空且未跳过；所有安装/测试起止标记齐。项目通过原PYTHONPATH=/testbed导入候选，不声称额外editable安装。实际命令分别为 `pytest -n0 -rA conans/test/unittests/client/toolchain/autotools/autotools_toolchain_test.py` 与 `pytest -n0 -rA conans/test/integration/configuration/test_profile_jinja.py`。六次runner digest前后相同，均实际导入 `/testbed/conans/__init__.py`。

输入bindings是wrapper要求的顶层tasks映射，两题实际任务项bindings均 `{}`。每次recipe记录原/绑定后状态逐字段相同，仅parser_source标签添加 `+reference-bindings-v1`，没有重命名nodeid或重解释结果，未借用11594映射。与[root13230冻结parser](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/conan13230_final_v1.json)、[13721冻结parser](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/conan13721_final_v1.json)逐参考一致。

noop两题frozen entries均空，无candidate.patch文件。四个gold/退化candidate.patch逐字等于输入；每个frozen仅含目标源码一个mode100644条目。解码完整文件逐字等于公开base纯文本应用补丁，再与私有apply后实际SHA一致：

| 题目／变体 | 整文件字节 | SHA256 |
| --- | --- | --- |
| 13230 gold | 13040 | bc27d227c5ace77320acc92c99b225c03d0d27493cfae2a76fc97b7b3705b567 |
| 13230 Android-only | 13025 | 27ff8904f912db9f468d35033fda856c0399121190556639bf58e04b599fd3dc |
| 13721 gold | 16848 | 8a9adf4ba9b122fdda24ef4afa874eb610eb4dd5d7f3c8561c2a1e1a7c3f55f6 |
| 13721 realpath | 16866 | ef928b72a7cf6981d36f95f6bec30c5dc03a754735a8dfe6cfbc3ed78358c11d |

目标分别为 `conan/tools/gnu/autotoolstoolchain.py`、`conans/client/profile_loader.py`；未投影测试或环境文件。六份eval.log完整SHA与ledger一致。正式image_id_actual均null，不能冒称该字段采到了config ID；镜像manifest、actor/private实际ID、拉取别名及frozen runtime提供绑定，原件留有完整摘要。

## 漏判依据与准入边界

13230来源新测虽在注释列Linux/Android/QNX，只实际构造Android。退化只排除Android，公开Linux核心例子仍错却35项全过，S1/T2b明确。已有两条公开CLI可作为D6修订种子：检查精确payload与失败位置，gold应到有意raise且flags=[]；不能把CLI rc0写成验收条件，保留原Android参考与34项旧回归。

13721来源新测一个节点含五次install，覆盖普通foobar、foo.profile、default、baz、include_default，未覆盖真实软链+with-context；realpath在普通文件上等于入口basename，因而7项全过。公开软链目标明确，入口丢失是独立S1/T2b。已有alpha/beta控制可作D6种子，但含后缀验收必须先确定公开范围及可接受正对照，不能由gold或隐藏断言替代决策。

认可题主当前用途：13230为CPU环境/行为/覆盖诊断，本批未授予比较资格；若后续受限比较，应预先固定统一语义验收与材料/预算/分母，原分不能单独判胜负。13721仅诊断，**必须先消解P5才可考虑受限比较**，不能靠事后语义审计绕过。两题D6都未实施，不能直接作为可靠训练奖励或授予留出资格。完整pip check、真实公开题面/public_hints交付、自主模型和训练准入仍未验证。

## 清理、传输与资源

actor container_rm/stub均0、网络/relay失败及残留为空；六个私有容器rm/query均0、remaining为空。六次正式candidate removed=true；原driver终行与receipt相同，manager各created=removed=1，containers_open/supply_open/cleanup_failures为空，final exit0。两层清理确认。

[root联合传输manifest](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_final3_v1.json)共239件3,529,295字节，含MONAI6975新恢复，不能冒称全是Conan。独立再核本两题子集各98件：13230为1,138,146字节、13721为1,094,200字节，逐大小/SHA均匹配。

六次均2CPU/4GiB，setup900、test1800、whole3600。[资源采样](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/resource_final3_v1.json)13230 noop/gold/退化7/8/8样本，13721为8/8/7；约15秒采样，均未观察OOM或PID拒绝。ledger峰分别336.137/334.383/334.754与345.312/346.750/347.473MiB，保留与采样峰的差别。采样包含准备，resource_facts仍null，不外推全生命周期零事件、最低内存或性能因果。

两题result.md/json及evidence_audit与上述独立原件判定一致，最终卡窄对齐已完成。可核销独立复核待办；不新增实验，不改变D6/P5及模型准入剩余项。
