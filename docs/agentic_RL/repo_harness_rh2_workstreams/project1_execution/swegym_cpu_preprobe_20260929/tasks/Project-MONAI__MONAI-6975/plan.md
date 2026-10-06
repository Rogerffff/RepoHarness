# MONAI6975 reserve6 CPU计划

2026-09-29，仅本地静态就绪，未执行。接既有静态结论，不改正式题面、测试或评分。

输入为 `runs/swegym_cpu_preprobe_20260929/task_inputs_reserve6_v1/Project-MONAI__MONAI-6975/`。公开actor仅消费 `public_commands.json`，私有补丁、预期及参考独立放在 `private/`。原镜像 manifest `0a529471d25c944c76e598474d7a665b20edc2ee95b1a2f30bf9c36fd8db6055`，base `392c5c1b860c0f0cfd0aa14e9d4b342c8b5ef5e7`；历史baseline01无派生配方、noop0/gold1。本轮先原镜像，不预建依赖层；缺包或镜像不可恢复时停题归因，不推定与其它MONAI相同。

公开检查以CPU内存图像替换原例随机仿射与读图，专门检验同一Dataset/Compose入口的lazy政策和返回值。不能据此声称原NIfTI/RandAffine完整原例已运行。输入`arange(12).reshape(1,3,4)`，两次确定性Flipd分别沿空间轴0、1翻转，预期像素为`torch.flip(source,[1,2])`。direct/Dataset × Compose True/False/None 共6行，Flipd实例均lazy=True；子类只记录实参及有效lazy后调用原方法。True应覆盖实例为lazy，False强制eager，None继承实例True，依据公开Compose/Flipd文档。

同时用标准mock wrap实际 `monai.transforms.lazy.functional.resample` 函数，保留真实函数执行并记录调用次数；不数 `applied_operations`，也不把某个精确内部调用次数设成唯一规范。决定性断言联合真实返回像素与有效lazy参数。dtype/device与调用次数保留供结果解释；测试旧公开Compose/Dataset两文件另执行，旧Dataset测试自行生成临时NIfTI，不依赖题面外部图像。

| 变体 | 六行矩阵预期（尚未运行） | 公开旧测预期 |
| --- | --- | --- |
| base | 所有像素正确；Dataset True/None实际effective=False，故最终目标断言失败 | 通过 |
| gold | 六行像素及lazy政策全通过 | 通过 |
| 丢弃dict返回候选 | 先执行正确lazy路径，但Dataset True返回原始字典，像素不符；其它行通过 | 预计通过，未知失败即停解释 |

私有候选在gold的默认None基础上，使`apply_transform`对lazy=True的Compose字典调用返回原始data，仍实际执行原转换。没有硬编码图像值、测试名或日志字符串；它用于检验“日志正确但返回值错”的既有覆盖疑点。其正式分数尚未知；若已有P2P拒绝，应记录正确拒绝，不能预设误奖。base/gold/候选在独立root容器运行，准备前后源文件整份SHA核验；私有权限不算actor权限。

正式保持原4 F2P+59 P2P、来源test_patch和选择器，三方新attempt对照，noop/gold预期0/1。冻源码完整字节、逐参考、实际安装/测试RC、日志SHA和两层清理齐后才作质量结论。新函数不会修改已有69xx题或通用helper生产实现。

入口：`rh2/experiments/swegym_cpu_preprobe_20260929/monai_reserve_followups_v1.py --task Project-MONAI__MONAI-6975`，新attempt `reserve6-v1`，actor端口18110，root远端统一并发。继续code_v1及prepared/private/gold/reserve6_v1；2CPU/4GiB，actor wall1800，公开identity120/matrix240/旧测360秒，私有整体3600，正式setup900/test原1800/whole3600。immutable源image拉取后只建同ID本地公开tag别名供冻结grader，无新层；不依赖可变latest可下载。

任何prepare、导入、collection、超时、非预期像素/lazy状态或清理未知都停本题；完整输出须有结构化6行和指定目标断言/成功标记，不能只认非零。远端当前资产/初态仍待观察。已完成本地JSON/命令AST/纯文本patch及SHA核对；未执行项目、下载或远端命令。D6仅设计；完整原例、其它Dataset/helper调用者、自主模型与GPU/训练资格未由本材料解除。
