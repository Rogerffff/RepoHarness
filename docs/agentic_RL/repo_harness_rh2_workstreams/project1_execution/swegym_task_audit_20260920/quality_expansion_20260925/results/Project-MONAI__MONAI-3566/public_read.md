# Project-MONAI__MONAI-3566：独立公开静态阅读

## 题面先行判断

仅依据 `user_prompt.txt:1–24`，目标是使 `LoadImage(reader="ITKReader", pixel_type=itk.UC)("tests/testing_data/CT_DICOM")` 返回的 metadata 包含输入中可用的 DICOM 标签，并保留现有 `spacing`、`original_affine`、`affine`、`spatial_shape`、`original_channel_dim`、`filename_or_obj`。题面展示标签键，不展示其值；合理实现必须从输入读取实际值，不能硬编码示例键。

合理旧行为包括目录读取仍形成三维体积、保留像素内容和几何信息、单文件及多输入读取继续可用。题面未要求重做图像轴顺序或改变默认输出类型。初始疑义是：多切片标签冲突采用哪一片、是否合并全系列标签、私有标签是否包括在“available”内、标签类型与顺序是否有要求，以及多系列目录如何选择。这些疑义在读源码前保留，不能从示例键序推定唯一实现。

公开 `public_bundle.json.public_hints` 声明修复非测试源码、不得修改测试、运行应限于窄测试，并声称 `/testbed` 与已激活 conda 环境可用。这是计划公开提示；其实际交付及实际环境均 unknown。本次静态审查的禁止执行边界不是原题额外开发要求。

## 公开实现及旧测试能确定的内容

以下源码路径均相对于本题 `PUBLIC_DIR/base/`，其中 `PUBLIC_DIR=/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-3566`。

- `monai/data/image_reader.py:187–225`：`ITKReader.read` 对目录使用 `GDCMSeriesFileNames`，启用 series details，按 `0008|0021` 限制分组；空目录无系列时报错，多系列警告，默认首个 series UID 或指定 `series_name`。目录被改写为所选系列的文件列表后传给 `itk.imread(name, **kwargs_)`；调用参数覆盖构造参数。没有显式从系列文件获取并附回 DICOM 字典的步骤。
- 同文件 `227–269`：`get_data` 调用 `_get_meta_dict`；后者只读取返回 ITK 图像自身的 `GetMetaDataDictionary()`，过滤 `ITK_` 前缀，再补 spacing。几何信息和通道信息随后加入。这与题面所述“体积可读而 DICOM 标签缺失”相符，定位到系列读取结果与元数据传递之间；第三方 `itk.imread` 内部的实际运行原因仍未执行核实。
- 同文件 `107–136, 227–255`：外层多个输入作为通道堆叠，只使用第一个输入图像的元数据并检查后续 affine/shape 兼容。这能消解“多个输入目录”的代表元数据约定，但不等于已经规定一个 DICOM 系列内部取哪一片。
- 同文件 `271–332` 及 `158–161`：仿射由图像方向、spacing、origin 构造，转为 nibabel 坐标约定；`reverse_indexing` 只影响像素数组布局，不影响元数据。修复不能将二维切片的几何字段覆盖到三维体积的派生字段上。
- `monai/transforms/io/array.py:93–155, 170–225`：字符串 reader 会接收额外参数，实例 reader 保留自身配置；默认返回数组与字典，默认数组转 float32，`image_only=True` 仅返回数组。`filename_or_obj` 仍应是用户输入目录。`switch_endianness:48–72` 递归处理字典/列表等，对未知类型报错，因此新增标签值须能经过现有返回路径。
- `monai/transforms/io/dictionary.py:101–136`：`LoadImaged` 委托 `LoadImage`，直接将其字典存入对应 meta key。没有另一套 DICOM 标签过滤逻辑。
- `tests/test_load_image.py:89–108, 150–167`：公开旧 DICOM 用例覆盖 reader 实例、字符串及 reverse indexing。期望 spatial_shape 为 `(16,16,4)`，默认数组形状相同，反向索引为 `(4,16,16)`；明确验证 affine 与原目录文件名，却不验证 DICOM 标签。`131–148, 169–199` 补充 ITK 单文件、多输入、彩色与多通道兼容要求。
- `tests/test_load_imaged.py:80–123`：单目录及重复目录组成双通道的读取、保存 NIfTI、重读比较像素/几何信息，同样没有标签断言。
- `docs/source/data.rst:120–131` 仅通过 autoclass 引用 reader 的文档，没有另行定义系列内标签归并策略。

因此，公开信息足以定位主要修改范围为 ITK 系列读取/元数据保留路径，并明确几何及数据兼容性；旧测试通过本身不足以验证标签修复。题面期望扁平标签字典，不能合理推导必须增加每切片列表、标签键严格顺序或特定新参数。

## 合理实现范围与剩余不确定性

可考虑在系列读取阶段保留元数据，或读取选中系列的代表切片标签并传递给最终体积；均须真实提取标签、保留现有 ITK 图像返回接口、参数及体积几何，不能改变系列选择或全局删除过滤规则以冒充修复。代表切片方案与现有首图像代表元数据的风格相容，但系列内部取首片、末片、共有标签还是合并标签，公开文字与旧测试没有唯一规定。这里是非 gold 的候选实现空间，未看到也未推测 gold。

ITK 支持的具体系列元数据接口、版本兼容性、私有标签开关、不同切片值/缺失键、非字符串值、异常系列以及自定义 image IO 参数的相互作用，仍需在实际开发环境用公开输入验证。示例标签表支持要求该样本的可用标签出现；它不能证明所有 DICOM 输入拥有相同键，也不构成真实患者值的预期清单。

## 开发需求表

以下命令仅是未来在已核实的 actor 仓库根目录运行的最小公开验证建议，本轮一条也未执行；不要求安装、网络、GPU 或模型实验。

| 操作/资产 | 公开依据 | 实际证据或 unknown | 最小公开验证命令及预期 |
|---|---|---|---|
| 确认初态、源码导入位置及非测试文件写权限 | prompt 的 base、公开 hints 的 `/testbed` 与非测试修复要求 | 静态 base identity 是 `9417ff217843db1cee7aef53b367cf1a7b21b7da`；actor HEAD、status、消息、UID、权限、预置改动均 unknown | `pwd`、`git rev-parse HEAD`、`git status --short`、`test -w monai/data/image_reader.py`；应记录实际位置、初始变更、是否可写，再按已交付要求比对，不用静态 base 代替实际初态 |
| Python / NumPy / PyTorch / ITK 与 GDCM 能力 | `requirements.txt:1–2` 为 torch>=1.6、numpy>=1.17；`requirements-dev.txt:6` 为 itk>=5.2；安装文档 `17` 为 Python>=3.7；reader 的实际 imports | 仅静态依赖声明；已安装版本、解释器激活、导入路径及可用 API 均 unknown | `python -c 'import sys, monai, itk, numpy, torch; print(sys.executable, monai.__file__, itk.Version.GetITKVersion(), numpy.__version__, torch.__version__); print(itk.GDCMSeriesFileNames.New())'`；应导入目标源码及 ITK 的系列命名器，无缺包异常 |
| 本地 DICOM 样本可读 | prompt 示例、旧测试 89–108 | 静态目录列出 `17106`、`17136`、`17166`、`17196` 四个文件；未解析二进制内容，actor 文件存在性及可读性 unknown | `python -c 'from pathlib import Path; p=Path("tests/testing_data/CT_DICOM"); print([(x.name, x.stat().st_size) for x in sorted(p.iterdir()) if x.is_file()])'`；应有预期四个非空切片文件，最终有效性通过 ITK 复现确认 |
| 验证本题新增行为 | prompt 7–23；`read` / `_get_meta_dict` 路径 | 问题复现、修复后结果均未取得 | `python -c 'import itk; from monai.transforms import LoadImage; a,m=LoadImage(reader="ITKReader",pixel_type=itk.UC)("tests/testing_data/CT_DICOM"); print(a.shape, sorted(m)); assert all(k in m for k in ("0008|0005","0020|000e","0028|0010","affine","spacing","filename_or_obj"))'`；修复后应保持 `(16,16,4)` 并包含所列样本标签。该命令只是最小冒烟检查，完整验证还须将所选系列切片的真实可用标签与返回值对比，不能只检查键存在 |
| 窄范围旧行为回归及测试依赖 | `test_load_image.py:17–24, 131–199`；`requirements-min.txt:5`；dev 6–8 | unittest 用例公开可见；parameterized、nibabel、Pillow 等实际可用性 unknown | `python -m unittest tests.test_load_image.TestLoadImage -k itk`；应通过 DICOM 形状/affine、单文件和多通道相关用例，结果不能代替新增标签断言 |
| 字典包装和本地临时目录读写 | `test_load_imaged.py:80–123` 使用 TemporaryDirectory 与 NIfTI 保存 | actor 临时空间、权限及相关依赖 unknown | `python -m unittest tests.test_load_imaged.TestConsistency.test_dicom tests.test_load_imaged.TestConsistency.test_multi_dicom`；应保留单/双通道像素、shape 和 affine；无远端数据、权重或 GPU 的公开必要性 |

## 阅读范围与边界

实际读取：派发卡、`roles/public_reader.md`；本题 `user_prompt.txt` 全文、`public_bundle.json` 全字段、`environment_brief.md` 全文、`base_identity.json` 全文。源码完整阅读区段为 `image_reader.py:12–332`、`io/array.py:48–72,75–225`、`io/dictionary.py:101–136`；测试为 `test_load_image.py:12–199`、`test_load_imaged.py:12–123`；文档为 `data.rst:111–138`、`installation.md:15–25`；依赖为 `requirements-min.txt` 全文、`requirements-dev.txt:1–12`。另外对本题 monai 源码、相关测试、docs/source 做 DICOM/元数据符号搜索，对 requirements/setup.py/installation.md 做依赖关键词搜索，只读其返回匹配行；文件名清单读取不算全文源码阅读。首次猜测 `tests/test_itk_reader.py` 时文件不存在，随后使用真实 `test_load_image.py`，不将该不存在路径视为缺失运行资产。

未读其余源码/测试正文、DICOM 二进制内容、外部链接、ITK 第三方实现、私有材料、历史、其他题目与任何角色结果；未读取实际 actor 工作树或环境。未执行/导入项目、未测试、未安装联网、未修题、未改测试/评分、未派生 agent。本产物只给静态开发可理解性及验证需求，不宣称成功率、训练资格或实际 actor 资格。
