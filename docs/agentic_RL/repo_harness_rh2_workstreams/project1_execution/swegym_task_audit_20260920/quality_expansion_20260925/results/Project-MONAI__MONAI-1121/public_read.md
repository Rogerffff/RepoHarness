# Project-MONAI__MONAI-1121 独立公开阅读

本报告仅依据本题公开包进行静态判断，没有执行、导入或修改项目，没有运行测试、安装依赖、联网或读取私有/历史/其他角色结果。派发卡的静态操作限制不是原题开发要求。以下路径以 `PUBLIC_DIR=/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-1121` 为根；`base/` 为静态源码导出。

## 先于源码阅读的题面判断

`user_prompt.txt:1–5` 指定 MONAI、提交 `5b91f937234a`，请求为所有网络增加测试，以保证能导出并加载为 TorchScript。直接交付目标是测试覆盖，不是泛化的网络重构。合理旧行为应保留：网络原有构造参数、普通前向计算、输出形状与训练/推理语义。仅从题面不能确定所有网络的枚举范围、是否包括 blocks/layers、要求 scripting 还是 tracing、训练模式是否必须可导出、数值比较容差、设备或 PyTorch 版本矩阵。导出且加载成功是明确最低目标；加载后执行并比较结果是合理验证增强，不能冒充题面逐字要求。

## 公开信息能够确认的范围及冲突

1. `base/monai/networks/nets/__init__.py:12–22` 与 `base/docs/source/networks.rst:195–281` 给出合理覆盖清单：AHNet、DenseNet 及四个工厂、DynUNet、Generator、HighResNet/HighResBlock、Regressor、SegResNet/SegResNetVAE、SENet 及六个工厂、UNet、VNet、Classifier、Discriminator、Critic。`classifier.py:21–140` 确认后三者是实际网络类；`unet.py:196` 确认 `Unet`、`unet` 是 UNet 别名，不能当成三种架构。文档把 Blocks、Layers 与 Nets 分开，但 FCN/MCFCN 位于 Blocks 且 `tests/test_ahnet.py:103–120` 将其作为网络测试。因此“所有”边界仍需明确，不能只覆盖现有同名测试文件就声称完整。
2. 对 `base/tests`、`base/monai/networks`、`base/docs` 搜索 `torchscript|TorchScript|jit\.|save_net|test_script` 没有匹配。这只说明所搜索文本未发现此类测试/接口，不证明其他表达形式绝不存在。实际读取的旧测试主要验证前向输出形状，未发现保存—加载回环。`tests/utils.py:12–118` 也没有 TorchScript 共用助手。
3. 关键公开契约冲突：`public_bundle.json` 的 `public_hints` 要求 “edit NON-TEST source files” 及 “Do NOT modify test files”，并声称评分前恢复测试文件；题面却直接要求增加单元测试。`CONTRIBUTING.md:95–105` 也要求新功能配测试。若这些 hints 实际交付，它们阻止了最直接的题面产物；只改源码兼容性不等同于补足测试。不能凭 hints 的评分声明反推隐藏测试、实际重置行为或所需补丁。`environment_brief.md:4–6` 明确实际消息/hints 交付尚未捕获，故此为条件性冲突，尚不能确认实际 actor 遇到的指令组合。
4. 公开 base 身份记录为 `5b91f937234a69fb299f220fc4bbdd8ef51ae37d`，452 个静态条目，无导出 `.git`，身份文件列出的 symlinks/gitlinks/LFS 未物化项均为空。这不等于核实实际 actor HEAD、工作树、依赖或镜像状态；`environment_brief.md:2–10` 明确这些仍 unknown。

## 旧行为与实现选择

- UNet 的 2D/3D、残差、批归一化和自定义激活组合在 `tests/test_unet.py:20–124` 保留形状断言。HighResNet 旧例覆盖 1D/2D/3D（`test_highresnet.py:19–51`）；DenseNet 的已读参数覆盖 1D/2D/3D及预训练选择（`test_densenet.py:20–100`）；Generator、Discriminator（各自 `:19–47`）及 VNet（`:51–67`）采用 `eval()`、`no_grad()`、形状断言。这些为选择合法小规模合成输入提供依据，不是 TorchScript 已通过的证据。
- `DynUNet.forward`（`dynunet.py:113–130`）在训练且 deep_supervision 时返回张量列表，其他情况下返回单张量；旧测试 `test_dynunet.py:103–122` 分别检查普通形状和训练时多个不同尺度输出。`SegResNetVAE.forward`（`segresnet.py:306–330`）训练时返回 `(x, vae_loss)`、推理返回 `x`；旧 `test_segresnet.py:92–98` 明确解包训练结果。任何兼容性调整都应保留这些已公开行为，不能未经需求支持统一改变返回结构。
- `SegResNet`/VAE 的索引式模块循环（`segresnet.py:152–168,298–300,312–325`）、DynUNet 的 `reversed(outputs)` 与按索引调用 supervision heads（`:121–129`）、训练分支返回类型差异是应重点验证的结构。仅凭静态文本不能断言具体 PyTorch 版本报错或给出唯一根因。文档默认值亦有局部差异，例如 DynUNet 的 res_block 文档写 True 而签名为 False（`:55–70`），应按显式参数构造验证例，不能顺便认定属于本题修复范围。
- 合理实现之一是建立公共测试助手，按架构参数表做 TorchScript 导出、序列化、加载及加载后前向；逐网络分散测试同样合理。可用临时文件或内存字节流完成回环，题面未要求持久文件。对返回列表/元组逐项比较；数值比较应先固定模式并考虑 VAE 随机损失（`segresnet.py:275–304`）。若采用 tracing，需要明确覆盖的输入/控制流；单个 eval trace 并不验证训练分支。采用 scripting 是另一选择，是否全量要求仍未由公开材料消解。
- 实际证明网络存在兼容性问题后，局部类型标注或等价循环改写属于合理候选；仅添加猜测性的源码改动、只测试编译而不测试加载、或为便于导出改变原输出 API，都不足以自然满足题面。这里没有实际修题，也未见 gold，因此不把任何文件名、助手名或实现策略定为标准答案。

## 开发需求表

下列命令是未来在已授权的实际 actor 工作树中验证的建议，本轮均未执行。原公开声明的 `/testbed`、conda `testbed`、bash/edit 是来源字段；不能当作已经验证的运行条件。

| 操作/资产 | 公开依据 | 已取得证据或 unknown | 最小公开验证命令与预期 |
|---|---|---|---|
| 获取实际消息及允许修改测试的范围 | 题面与 public_hints 冲突；environment_brief:4–6 | 实际消息、权限规则及 hints 交付 unknown | 查看实际 actor 收到的完整指令；应明确新增测试能否保留，shell 无法替代消息证据 |
| 确认实际源码初态与可读写权限 | user_prompt:1；base_identity；environment_brief:2–3 | 仅静态 base 身份已给出；实际 HEAD/status/初始改动、用户及路径 unknown | `pwd`、`id`、`git rev-parse HEAD`、`git status --short`、`git diff --stat`；确认工作目录、提交与来源规定初态，不能预设必须干净；`test -w tests`/`test -w monai/networks` 只验证文件系统权限 |
| Python、PyTorch、NumPy、parameterized及本地导入 | requirements.txt:1–2；requirements-min.txt:1–5；CONTRIBUTING:95–100 | 声明 torch>=1.4、numpy>=1.17，最小测试需 parameterized；实际版本/激活/导入 unknown | `python -c "import sys,torch,numpy,parameterized,monai; print(sys.executable,torch.__version__,numpy.__version__,monai.__file__)"`；应成功且导入实际工作树，版本须记录 |
| 合成输入上的旧前向行为 | test_unet:20–124及各网络旧测试 | 静态断言已读；实际通过与资源消耗 unknown | `python -m tests.test_unet`；期望现有 2D/3D 参数化形状断言通过；随后按受影响网络逐个窄测 |
| TorchScript 转换、保存、加载与推理 | user_prompt:3–5 | 没有本轮执行结果；具体 jit 策略、失败点 unknown | 在新增回环测试放入 `tests/test_unet.py` 的方案下，运行 `python -m tests.test_unet`；应实际覆盖 jit 转换、save/load、加载后前向及与原结果比较。此为拟议增量，现有命令本身不会验证回环 |
| 广度及训练返回语义回归 | nets 导出清单；test_dynunet:103–122；test_segresnet:78–98 | 静态可枚举；“所有”精确矩阵 unknown | 分别 `python -m tests.test_dynunet`、`python -m tests.test_segresnet`；保留普通张量、深监督列表、VAE训练元组的旧行为；其余架构按已确认清单逐项运行新增回环例 |
| 临时存储或内存流 | 保存/加载需求；标准库 tempfile 已在 tests/utils.py 使用 | actor 临时目录权限及空间 unknown；内存流不要求磁盘产物 | `python -c "import tempfile; f=tempfile.TemporaryFile(); f.write(b'x'); f.seek(0); assert f.read()==b'x'; f.close()"`；若选择文件方案，临时文件读写应成功；实际 TorchScript 内容仍由回环例验证 |
| 预训练权重、网络、CPU/GPU与内存 | test_senet:27–34；senet._load_state_dict:272；旧 DenseNet/AHNet预训练例 | 权重缓存、网络与资源全部 unknown；基本合成输入例不显示 GPU 必需性 | 最小回环使用 `pretrained=False` 的小规模 CPU 构造及拟议单例命令；期望无需权重下载。不能盲目运行 `python -m tests.test_senet` 作离线最小验证，因为其模块级 pretrained=True 构造可能在测试跳过前触发加载；GPU不是题面明确要求 |

## 实际阅读范围与局限

全文读取：派发卡、角色卡、user_prompt.txt、environment_brief.md、base_identity.json、public_bundle.json；base 的 nets/__init__.py、tests/utils.py、docs/source/networks.rst、requirements.txt、requirements-min.txt、requirements-dev.txt；tests/test_unet.py、tests/test_dynunet.py、tests/test_segresnet.py（含许可段）以及 classifier.py:12–140。

明确读取的其他区段：dynunet.py:20–155（分段，含构造与 forward）；segresnet.py:145–170、260–330；unet.py:185–196；regressor.py:130–142；generator.py:138–147；senet.py:261–278；tests/test_discriminator.py:12–51、test_generator.py:12–51、test_highresnet.py:12–55、test_densenet.py:12–100、test_ahnet.py:103–177、test_senet.py:12–65、test_vnet.py:45–67；CONTRIBUTING.md:78–105。另执行公开包文件名枚举，以及上述 TorchScript 词项、nets 类/forward/预训练符号、测试中的 Classifier/Regressor/Critic、CONTRIBUTING/runtests/setup 中测试命令关键词检索。宽检索的一次输出遭截断，后续对使用的关键证据定点复读；不将截断区段视为已读全文。test_classifier.py、test_regressor.py 这两个猜测路径未找到，只表明静态导出无这两个路径，不能据此推断实际镜像缺失。

未完整阅读其余网络实现、blocks/layers 实现、其余测试和文档；未读任何链接目的地、隐藏测试、gold、实际镜像或 actor 状态。当前能确认的是公开开发目标及测试交付约束之间的条件性冲突、现有网络/旧行为的合理覆盖范围和验证所需条件；无法判断实际 TorchScript 通过率、实际 actor 可执行资格或训练资格。
