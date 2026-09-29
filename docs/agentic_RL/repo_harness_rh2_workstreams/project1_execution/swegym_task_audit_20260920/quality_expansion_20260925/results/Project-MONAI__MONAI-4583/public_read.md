# Project-MONAI__MONAI-4583 公开静态审查

## 题面先验记录

本节先验来自先读取的 `user_prompt.txt` 与 `public_bundle.json`，形成时尚未阅读源码。目标是修复 `convert_mask_to_box` 的类别标签：输入 `numpy.asarray([[[-1, 0], [0, -1]]])`，应返回框 `[[0., 0., 2., 2.]]`（float32）和标签 `[0]`，而不是 `[-1]`。题面明确的合理旧行为是这一示例的框坐标保持不变；不应把这次修复扩展成改变坐标定义。仅据题面，背景默认值、每通道含义、多个类别的表示方式、2D/3D及空掩码行为尚有疑义。

公开 hints 要求修复非测试源码、不修改测试文件、验证保持窄范围；其是否实际交付 actor 为 unknown。题面的环境调试命令是收集环境信息的模板，未提供执行结果，不构成实际环境证据。本审查派发的静态禁令是审查运行边界，不是原题新增开发要求。

## 公开证据与问题消解

下文源码路径均相对于本题 `PUBLIC_DIR/base/`，其中 `PUBLIC_DIR=/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-4583`。

1. **根因可静态确定。** `monai/apps/detection/transforms/box_ops.py:273–320` 中，`convert_mask_to_box` 用 `np.nonzero(boxes_mask_np[b, ...] - bg_label)` 找前景（300），各轴分别求最小值、最大值并生成框（303–307），然后从框的最小角读取标签（308–311）。题面前景坐标为 `(0,1)` 和 `(1,0)`，分别取最小值会得到 `(0,0)`；该点实际为背景 `-1`。这说明空间包围框正确不等于其角点一定是前景。此为手工静态推导，未执行复现。
2. **“多类”不是在单通道中拆出多个对象。** 同文件280–289与 `convert_box_to_mask` 的207–221规定每个通道代表一个框，通道前景值是该框的类别。不同通道可以有不同类别；本题应恢复该通道真实前景标签。将每种像素值或连通分量输出成独立框，缺乏公开契约依据。
3. **背景与几何约定明确。** 默认 `bg_label=-1`；配对生成器232–237要求背景小于所有前景标签；`array.py:424`重复此约束。转换器当前按“不等于背景”寻找前景。`monai/data/box_utils.py:40–45`说明 `TO_REMOVE=0.0`，右下端点不含最后一个像素，因此最大前景索引加一得到示例中的2。修复没有理由改动这个约定。
4. **需兼容2D和3D及空输入结果。** `box_ops.py:291–293`接受三维或四维输入，即通道加2D/3D空间；301–302跳过无前景通道，314–319为无框输出构造 `(0, 2*spatial_dims)` 的框和 `(0,)` 的标签，并按指定 dtype 转换。默认框 float32、标签 torch.long 对应整数类型。`type_conversion.py:294–336`显示返回类型与设备跟随输入，支持 Tensor、NumPy 和 MetaTensor分支；不应因标签修复丢失既有转换行为。
5. **数组、字典包装共享同一实现。** `array.py:417–447`的 `MaskToBox`直接调用本函数。`dictionary.py:911–923, 992–1001`将类别整体平移，使中间掩码背景为0，恢复背景后调用 `MaskToBox`。应保留平移语义；不能只把背景硬编码为0。`dictionary.py:837–889`公开描述旋转、裁剪后还原框的用途，并举 ellipse_mask=True、nearest插值例子，这支持非矩形前景属于合理输入。
6. **旧测试不能排除这一缺陷。** `tests/test_box_transform.py:57–113`包含2D矩形往返和3D矩形往返，标签分别包括 `[1,0]` 与 `[1,0,3]`，并使用float32/float16及类型测试辅助设施。这些矩形的最小角本身为前景，故静态上不能检出题面根因。未在本次定位到的相关测试区段见到角点为空的稀疏形状或 ellipse_mask=True 往返测试。不能据此宣称全库没有相关覆盖，也未声称旧测试运行通过。

## 合理实现范围与保留疑义

最小合理修复是：每个非空通道仍产生同一个包围框，但从确实属于前景的像素取得类别，覆盖2D与3D，并保持通道顺序、空通道跳过、dtype及设备转换。选择一个已经得到的前景坐标进行取值，是符合公开契约的一种实现；在背景严格小于所有前景且单一前景类别的约定下，按通道最大值提取类别也是另一种可解释选择。两者并非同等适合无效或额外扩展输入：最大值额外依赖背景排序；取任一前景仍依赖通道内前景类别一致。这里不指定唯一代码写法，也未读取或推测 gold。

单通道出现多个非背景类别、非整数插值结果、非法背景顺序、溢出边界和新增校验/报错策略未由题面定义，不应借修复擅自建立新的分割或冲突解决规范。`MaskToBox`类文档421提到 `min_fg_label`，但其实际参数是 `bg_label`；字典包装才接受 `min_fg_label`。公开调用链能澄清使用方式，这个文档瑕疵不妨碍定位标签缺陷，也不意味着必须扩大修改范围。

## 开发需求表

以下命令仅是将来在获准的实际 actor 工作树中执行的最小公开验证建议，本轮未执行。命令中的 `/testbed` 来自计划提示，真实路径仍需核验。

| 操作/资产 | 公开依据 | 实际证据或 unknown | 最小公开验证命令与预期 |
|---|---|---|---|
| 获得真实任务、可编辑源码和初始状态 | user_prompt 指定 `/testbed`、commit `9c4710199b80`；hints 限非测试源码 | base_identity记录完整base commit `9c4710199b80178ad11f7dd74925eee3ae921863`的静态导出；actor消息、HEAD、diff、权限均unknown | 实际会话中核对收到的提示；`pwd`、`git -C /testbed rev-parse HEAD`、`git -C /testbed status --short`、`git -C /testbed diff -- monai/apps/detection/transforms/box_ops.py`；确认来源要求及记录差异，不能仅凭base推定初态 |
| 可用Python、NumPy、PyTorch及本地MONAI导入 | requirements.txt列torch>=1.7、numpy>=1.17；box_ops.py导入二者 | actor解释器、依赖版本和激活均unknown；公开字段仅声称conda testbed已激活 | `python -c 'import sys, numpy, torch, monai; print(sys.executable); print(monai.__file__); print(numpy.__version__, torch.__version__)'`；应导入待修工作树与兼容依赖。题面另有 `python -c 'import monai; monai.config.print_debug_info()'` 可供诊断 |
| 原始缺陷的窄复现与修复验证 | user_prompt的明确输入/输出；box_ops.py:300–311 | 仅静态推导，无运行证据 | `python -c 'import numpy as np; from monai.apps.detection.transforms.box_ops import convert_mask_to_box; print(convert_mask_to_box(np.asarray([[[-1,0],[0,-1]]])))'`；修复后框float32为 `[[0,0,2,2]]`、标签为 `[0]` |
| 2D/3D包装回归及测试工具 | test_box_transform.py:12–113；requirements-min.txt列parameterized | 旧测试文件存在；actor测试工具及执行结果unknown | `python -m unittest tests.test_box_transform`；既有断言应保持成立，属于单模块验证；CPU即可进行必要回归 |
| 非矩形多类、空通道和dtype的针对性验证 | 每通道一个框的文档；box_ops.py:291–319 | 可用内存构造，无题目数据集或权重要求；实际执行条件unknown | 在 `python -` 中临时构造两个通道，每通道前景为不同整数类别且框角是背景；再构造3D同类形状、全背景通道、Tensor与NumPy输入，并调用本函数断言。预期各非空通道保持自身类别和几何、空通道不输出、类型/dtype跟随既有参数；不修改测试文件 |
| CPU内存数据与可选GPU | 复现只创建2×2数组；tests/utils.py:711–719仅在CUDA可用时加入GPU类型 | 实际CPU/GPU、网络、工具权限unknown | 最小复现无需下载、模型、数据集、训练或GPU；必要时 `python -c 'import torch; print(torch.cuda.is_available())'`只用于决定是否附加设备保留验证，不能把GPU当作必备资产 |

本次无需研究网络、容器或安装步骤；公开包缺少实际运行状态并不意味着镜像缺失依赖。完整开发依赖文件含许多可选库，不能据此将全部依赖列为此缺陷最小需求。未进行任何项目执行、导入、测试、安装、网络或模型实验；无成功率、训练资格或实际actor资格结论。

## 阅读范围与审查边界

已读：派发卡和 public_reader角色卡；本题 user_prompt.txt、environment_brief.md、base_identity.json、public_bundle.json全文；box_ops.py显示区段1–360（重点196–320）；array.py:365–450（重点380–447）；dictionary.py:837–1005；test_box_transform.py:1–180（重点57–113）；type_conversion.py:229–351；tests/utils.py:700–726；docs/source/apps.rst:127–152；requirements.txt、requirements-min.txt、requirements-dev.txt全文。另使用rg定位 convert_mask_to_box/convert_box_to_mask/BoxToMask/MaskToBox及相关常量、包装类、类型辅助定义；box_utils.py仅看相应rg命中，未完整阅读。对PUBLIC_DIR做过文件名清单列举，输出被截断，不把未显示清单或文件名视为内容已读。

未读：无关源码和其余旧测试内容、项目全量文档、实际镜像或actor工作树、私有材料、历史记录、其他题、其他角色结果、隐藏测试及gold；未跟随引用链接。环境身份JSON中的校验值是公开材料声明，不是本次重新验核。流程记录：首次读取派发卡时命令使用绝对卡路径但未显式设置workdir；其后所有exec均显式设置卡内ROOT。首次命令只读取允许的派发卡，没有读取默认工作目录内容。

唯一写入产物为本文件；保存计算SHA256后封存停止。
