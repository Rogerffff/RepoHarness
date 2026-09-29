# reserve6 MONAI4583/6975：actor 与私有行为独立复核

2026-09-29。**两题原镜像均完成正式 actor 开发诊断；私有 base/gold/退化三方完整，真实值证明两个退化候选有公开行为缺陷。正式评分尚在途，本稿不判定正式误奖或题目资格。** 这是跨包独立复核，复用当前上下文，不是 fresh 盲审；先读公开题面/base、命令、补丁和原始运行记录，再读题主计划。原件读完后，已窄核题主随后落盘的 result_partial.md/json。未远端执行、运行项目或改生产。

原件：[4583](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-4583/reserve6-v1)、[6975](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-6975/reserve6-v1)。读取范围包括两份 actor 完整 captures/trajectory/attempt、prelaunch/activation/CC、结束状态，以及两题各三个 private run 的完整行为输出、旧测输出、prepare 与 cleanup。6975 的 degenerate_run 此次已完整收口，不再列作缺项。

## MONAI4583：前景标签与2D/3D输出

[题面](../../../../../../runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-4583/user_prompt.txt)明确反对角前景 label0 应取0而非背景-1。[base API](../../../../../../runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-4583/base/monai/apps/detection/transforms/box_ops.py)明确同通道前景值是分类标签、支持Nx4/Nx6、ndarray/Tensor、box_dtype/label_dtype，且代码接受3维/4维输入并恢复目标类型。因此增加第二通道label7、稀疏3D和公开dtype参数有公开依据，不由 gold 实现反推。

actor 真实 NumPy/Torch CPU、默认float32/int64与指定float64/int32，在2D/3D各四组合全部到达结构化输出；boxes 均是两份 `[0…0,2…2]`，类型/dtype/device 正确，只有 labels 错为 `[-1,-1]`，随后准确触发目标断言，两个命令rc1。公开5项旧测完整5 passed、22 warnings，rc0。

私有 base 重现相同结果；gold 八组合均得 `[0,7]`，box/类型/dtype/device全部正确；2D-only 候选四个2D组合正确，四个3D组合仍取 `[-1,-1]`，其余输出契约保持。各变体旧测都完整5 passed，没有导入/collection故障或额外失败。对应子命令rc分别为 base `1/1/0`、gold `0/0/0`、退化 `0/1/0`，不是将 helper整体0解释成行为通过。

这证明退化遗漏了已有公开3D契约；尚未证明当前正式参考会误奖。内存小数组覆盖的CPU行为不扩写成CUDA或任意mask拓扑已验证。

## MONAI6975：lazy传参与实际返回像素

[题面](../../../../../../runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-6975/user_prompt.txt)关注 Dataset 不应忽略 Compose.lazy。[公开 Compose](../../../../../../runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-6975/base/monai/transforms/compose.py)规定 True/False/None：分别启用、强制逐步执行、继承子变换lazy属性；[Dataset](../../../../../../runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-6975/base/monai/data/dataset.py)取样应返回 transform 的结果。这里以CPU内存图像和确定性两次Flipd核相同入口机制，没有执行题面NIfTI读取与随机RandAffine完整原例。

每个变体均完整输出 direct/Dataset × True/False/None 六行，输入为float32 CPU `[0..11]` 的1×3×4图像；正确输出三行分别为 `[11,10,9,8]`、`[7,6,5,4]`、`[3,2,1,0]`。子类只记录lazy实参后调用原Flipd，mock的wrap仍执行真实resample函数。

| 变体 | lazy参数与真实像素 | 完整旧测 |
| --- | --- | --- |
| base/actor | Dataset True/None 两行被传入False，effective=False；六行像素均正确，最终政策断言rc1 | 56 passed，20 warnings |
| gold | 六行政策和值均正确，True/None各继承正确语义；rc0 | 56 passed，20 warnings |
| discard退化 | Dataset True实参/effective均True，却返回原始0..11图像，value_ok=False、rc1；其余五行正确 | 56 passed，20 warnings |

gold 与退化的 Dataset True 都实际调用一次resample，退化随后丢弃dict返回值。因此决定性反例来自错误像素，不能用调用次数、日志或applied_operations数替代值验收。旧Compose/Dataset的56项原测试没有拒绝这个退化，正式原参考是否拒绝仍待完整评分。

## 身份、候选整字节与收尾

两题都用原 immutable manifest，无新依赖镜像或修复后actor。4583实际image ID为 `8305e1f5f6f13226ef30941433ed794fc294acc62fef85a28bc82131c6f6e0c4`，6975为 `789cb5d10d9b343a2e8b656581697a7127b56a0d467b1cc5b8779a79a0ff0727`，与各题prelaunch和三方私有summary一致。两题CPU2/4GiB，actor UID54321、CC2.1.205、Python3.8.20，实际解释器在testbed env、目标源码从 `/testbed/monai/` 导入。4583为NumPy1.24.4/Torch1.13.1+cu117/pytest8.3.3；6975为NumPy1.24.4/Torch2.4.1+cu121/pytest8.3.3/NiBabel5.2.1。CUDA均false；这不是Pydantic任务，不套core版本要求。

HEAD分别核到 `9c4710199b80178ad11f7dd74925eee3ae921863`、`392c5c1b860c0f0cfd0aa14e9d4b342c8b5ef5e7`。4583起止git状态空；6975原镜像已删 requirements-dev.txt 中MetricsReloaded Git依赖，起止均保留该dirty项，不能称为干净checkout或本次候选修改。两题结束agent进程0。

私有容器实际在apply前核base完整源文件 SHA，check/apply后再核完整文件 SHA；本审查另在临时静态副本应用输入补丁，逐字hash对齐捕获，而非只信候选名称：

| 题目/文件 | base SHA | gold SHA（字节） | 退化 SHA（字节） |
| --- | --- | --- | --- |
| 4583 box_ops.py | a439e2cf0de7ac19d715e0fefb5224e96e933d7001b4e554f4fbc5f6090c4f5c | ad4fd4db54ee21ce6d2da4e5e707a91f2e3b8e16ca269eaa03b72d3b1460539a（17755） | ff73733407f3f1d096331da2c90b289a98fe68b7bd28293f1c4cb9754db700ac（17737） |
| 6975 transform.py | 1e39afa8d4464c4ef18ac3f1a05c654a213af65e4364fa194923faa92b156ee9 | 5d8ba724a4e09bdf533c1030e0891a9acfb00a98069ca6586533cddb4e369bb5（21532） | a8382325df5169732767963fa29553845514fe29b318ce60184bdcc12ddf369a（21696） |

私有三方身份都是root，不能外推actor权限。actor分别4/3个Bash调用，与tool_result完整配对；prelaunch/activation为true，完整轨迹与captures未截断。两个旧通用探针 `interpreter_in_tool_result`/`bashenv_denied_for_agent` 为false，故不写“所有checks都通过”或OS隔离已证；实际解释器由身份命令与activation单独确认。两题actor container_rm/stub_rc=0，label容器/网络与强制复查残留空，network/relay失败空。六个私有变体的prepare均rc0、全部命令结束、rm/query均0且remaining空。

题主[4583部分卡](../tasks/Project-MONAI__MONAI-4583/result_partial.md)与[6975部分卡](../tasks/Project-MONAI__MONAI-6975/result_partial.md)及各自 JSON 已在原件审查后窄对齐，行为、身份/源码SHA、旧测和清理事实及未验正式的边界一致；无新增阻断。正式安装、三方完整投影/逐参考、manager清理、root parser/传输SHA及题主最终卡仍待后续单独验收，本稿不引用在途正式部分推结论。资源全生命周期、完整原例、自主模型、D6和训练资格均不由这组actor/private控制解除。
