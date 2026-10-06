# Project-MONAI__MONAI-1121 history前独立私有初判

本稿由私有主审 e25_main_pack05_monai 在 history release 前完成。仅作静态审查；未执行或导入项目、测试、安装、网络、容器、模型或任务二，未读 history、旧质量结论、reviewer、其他包及根汇总。已授权读取本题 public_read（root 先前核 SHA 封存）、PUBLIC/PRIVATE 与 run_refs 指定本题原件。本文 P 指本题 PUBLIC，S=P/base，V 指本题 PRIVATE；源文件行号均为 base 或补丁文本，不能混作修后行号。

实际 actor 消息/初始工作树/UID、HOME、cwd、PATH、写权限、资产权限、网络与资源均 unknown。公开 bundle 是计划输入；历史 grader 的成功不替代 actor 验证。第一次读取派发卡用了绝对路径但未设置 workdir；其后全部 exec 明确使用卡内 ROOT；第一次没有读默认目录内容。本稿保存后冻结，不以历史补写。disposition=needs_review/static_review，usage.intended_use=development_diagnostic；additional_exclusions=[]、revision_refs=[]；本轮 token/费用未观察为 null。

## 初判与公开目标

题面要求为“所有网络”增加能导出并加载 TorchScript 的单元测试。局部 AHNet 编译修复有真实 RH2 正证据，但现有任务产物/验收不足以代表完整公开目标。P/public_bundle.json 的 hints 要求只改非测试文件，测试改动会恢复；若实际交付，则直接冲突于题面测试交付目标。check3 仍 unknown，check23 为静态规格 issue，不能说实际 actor 已被误导。

S/monai/networks/nets/__init__.py:12–22 至少还导出 DenseNet、DynUNet、HighResNet、Regressor、SegResNet/VAE、SENet 等；本题 test.patch 只新增 AHNet、Discriminator、Generator、UNet、VNet 五项回环。“所有”的 blocks/工厂枚举可澄清，但这些明显 nets 类的缺席不靠该疑义消失。gold.patch 只改 ahnet.py 两处，不添加测试，也不证明其他网络兼容。

## 需求—断言双向表

| 公开要求/合理旧行为 | 公开依据 | 全部新增断言/决定性 helper | 覆盖/缺失及证据 |
|---|---|---|---|
| 导出、序列化、重新加载网络 | prompt:3–5 | test.patch 的 tests/utils.py::test_script_save：torch.jit.script→save_to_buffer→jit.load(BytesIO)，原网与重载网 eval/no_grad 后前向 | 五个固定配置有回环；实际历史五项均执行；仅 AHNet 是 F2P |
| AHNet 正常脚本兼容 | nets/ahnet.py:172–235,238–329,434–455,502–533 | TestAHNET::test_script；3D/out_channels=2，输入(1,1,128,128,64)，torch.allclose | noop 在属性 float←int 编译处失败；gold 通过；数值对照是候选自身 eager 对自身 script，非独立功能 oracle |
| Discriminator 回环 | test_discriminator.py:19–47 | TestDiscriminator::test_script；in_shape(1,64,64),channels(2,4),strides(2,2),num_res_units=0；输入(16,1,64,64)，allclose | 历史执行并通过，但该新增项及其3个形状项均不在 expected F2P/P2P 中；不能把实际执行等同于评分约束 |
| Generator 回环 | test_generator.py:19–47 | TestGenerator::test_script；latent(64),start(8,8,8),channels(8,1),strides(2,2),res=2；输入(16,64)，allclose | P2P，新旧均通过；仅一配置 |
| UNet 回环 | test_unet.py:20–124 | TestUNET::test_script；2D/1→3/channels(16,32,64)/strides(2,2)/res=0；输入(16,1,32,32)，allclose | P2P，新旧均通过；3D/残差/自定义激活脚本路径未测 |
| VNet 回环 | test_vnet.py:19–67 | TestVNet::test_script；3D/1→3/dropout_dim=3；输入(1,1,32,32,32)，allclose | P2P，新旧均通过；2D/其他 dropout 配置脚本未测 |
| 所有网络均得到新增测试 | nets/__init__.py 与 prompt | 无对应 DenseNet、DynUNet、HighResNet、Regressor、SegResNet/VAE、SENet 回环 | 缺失，check25；不能用35项P2P数量代替覆盖 |
| 保持 eager 形状/预训练兼容 | test_ahnet.py:21–177及四个其余测试文件全文 | FCN/MCFCN 各3、AHNet 2D/3D×模式6、预训练迁移3及初始化1；UNet7、Generator3、VNet6旧形状断言 | 已逐参数阅读并核原日志通过；多数只检查shape，不验证与修前固定数值一致 |
| 交付新增测试；不限定实现策略 | prompt；CONTRIBUTING:95–105 | 隐藏 helper 强制 scripting，并恢复6个测试文件 | 恢复使纯测试实现不计入候选；仅 tracing 能否满足公开 wording 有疑义，不自动断言 tracing 是完整正确解；scripting要求和合法测试交付须明确 |

全部新增 assert 都是五个 torch.allclose，无明确 atol/rtol、seed；helper 没有独立期望输出，也没有训练模式、不同输入形状或输出结构矩阵。序列化在 eval 前进行，实际比较在 eval 中进行，不代表训练前向已验证。未出现硬编码 gold 文件内容或源码结构断言。

## Gold、合理替代解和回归

gold 第一处把 Pseudo3DLayer.forward 的 dropout_prob=0/比较0 改成0.0；构造签名是 float，AHNet 的 dense0…dense4 传0.0。dropout 仍被每次关闭，数值路径不因该字面量改变；这是兼容性修复，不是修正原先关闭 dropout 的设计。第二处将 PSP 非 transpose 分支的 tuple(x.size()[2:]) 改成 x.shape[2:]，用于四个 F.interpolate 的 size。对正常 Tensor 的 eager 空间大小相同；旧 AHNet bilinear/trilinear 参数形状断言给局部回归证据。新脚本单例默认 transpose，不能据其证明非 transpose 的所有脚本分支。

已读调用链 DenseBlock→Pseudo3DLayer，AHNet dense0…4→PSP→Final，以及 copy_from 开头；未全读所有网络和框架 JIT 实现。局部等价循环/类型修复、其他序列化 helper 组织方式都可合理；测试不要求与 gold 文本一致。只修 AHNet 也可获得该参考分数而没有交付“所有网络新增测试”，是具体漏测/任务收窄，不是已证明 gold 新增功能回归。未执行替代候选，不宣称普遍无误拒。check27 局部正证据与全题完整性分开；check26 未发现已证回归，保持 unknown。

## 开发、合法交付、原运行限制

| 必要操作/资产 | 公开依据 | 现有证据及缺口 | 最小公开验证（建议，未执行） |
|---|---|---|---|
| 确认可交付测试范围与所有网络清单 | prompt/hints/CONTRIBUTING/nets exports | 存在静态冲突；实际消息 unknown | 核实际消息与恢复政策；这不是CPU可决定的题意 |
| 本地 Python、torch、numpy、parameterized、工作树导入 | requirements.txt:1–2、CONTRIBUTING:95–100 | 历史 Python3.8.20、torch1.13.1+cu117、numpy1.23.5；actor unknown | `python -c "import sys,torch,numpy,monai; print(sys.executable,torch.__version__,numpy.__version__,monai.__file__)"`，应导入工作树 |
| AHNet/其余公开网络前向和回环 | 旧测试、公开请求 | 历史窄模块40项完成，峰值原字段见附录；不证明全网络 | 先小规模合成CPU网络新增回环，再按确认清单运行单模块；`python -m tests.test_unet` 现有版仅旧测试，不能冒称已测回环 |
| 预训练权重与离线缓存 | test_ahnet.py:26–29,161–173 | 历史 deny_all 下 pretrained 例通过；actor缓存位置权限 unknown | 最小新回环使用 pretrained=False；预训练旧例另核缓存可读，不能从静态包缺权重推断镜像缺失 |
| 写入与保存 | 测试源码与BytesIO可选方案 | actor测试/源码写权限未知；磁盘文件不是题面唯一要求 | `git status --porcelain=v1`、`git diff`记录实际初态，内存流可完成save/load |

历史 noop/gold 日志132起分别报告干净/仅ahnet.py改动，随后 git show 是基线提交内容，不是未提交diff。noop:584的实际diff为空；gold投影只纳入ahnet.py。日志588–622（gold618起）恢复六个测试文件再应用补丁。这个恢复有历史原件支持，但不能概括任意新增候选测试的处置。材料版本为 materials-v1，与原 test.patch 的完整收集行为尚未按冻结源码逐字复核：原 helper 名 test_script_save 可能受到 pytest 收集策略影响，而引用日志实际只收集40项且无helper fixture error；不得把这次结果外推至未核的原始默认 pytest 条件。

唯一优先下一步：先由任务拥有者对齐公开目标、合法测试交付和评分范围，明确本题是否仍要求“所有网络新增测试”。在该决定前继续CPU/模型探针不能解决目标错位，因此不派任务二、不机械建议重跑。

## 初步检查编号与实际阅读范围

1 pass（包内base/patch与指定attempt局部绑定）；2 pass（历史目标编译失败）；3 unknown；4 issue（条件性测试交付冲突）；6/7/8/9/17/18/19/20/21 仅历史局部pass，当前actor部分unknown；10/11/13/14/15/16/22 unknown（网络/资源仅历史字段）；23 issue；24 unknown（脚本策略边界/未执行替代解）；25 issue；26 unknown；27 issue（局部修复成立，全部目标完整性不足）；28 pass（未另造硬性需求）；29 unknown（actor泄露），审查者私有暴露另记；30/31/32/33/34/35/36/37/38/39/40 unknown，未列项not_checked。by均为本稿作者，具体证据见表、原运行附录与阅读范围；封存流程本身不证明无筛查偏差。

完整读五个新增测试文件及 tests/utils.py 的base全文、gold/test patch、nets/__init__.py、pyproject.toml、requirements.txt/dev、CONTRIBUTING:90–106；ahnet.py:110–546（未读1–109及547以后）。公开网络广度/其他返回语义参考已封存public_read，未把其作者阅读等同于本稿直接读源码。所有F2P/P2P语义已按上述全文/参数表审阅；未读所有其他网络实现、其他测试、ITK/JIT第三方库。日志按附录关键区段与定向检索阅读，不称全文。部分批量输出截断，引用处均复读或收窄到实际显示段。

## 原件身份、运行证据与逐测试状态附录

P=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-1121`；V=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/Project-MONAI__MONAI-1121`。base_commit=`5b91f937234a69fb299f220fc4bbdd8ef51ae37d`，source版本=0.3，adapter=`rh2.private_grading_bundle.v2`，vendor=`swegym_constants_242429c1`。gold/test patch全文已读，test.patch与grading.test_patch标准库字节比较相同；gold与validation及原候选绑定由root先核，本稿又逐项读取run_refs允许的projection/baseline/stage JSON指针，HEAD/base同本题。原候选SHA与投影SHA是不同含义，不混用。

### gold

- 原账本：`runs/env_recipe_repair_20260919/materials_v1/runs/Project-MONAI__MONAI-1121-gold/ledger.jsonl:1`，仅机械选定该行。原日志：`runs/env_recipe_repair_20260919/materials_v1/runs/Project-MONAI__MONAI-1121-gold/eval_logs/evallog_replay-er19-mat1-Project_c30adeed.eval.log`，授权范围1–1131。
- run_id=`er19-mat1-Project-MONAI__MONAI-1121-gold`；image_ref=`sha256:b3bccbbee1887d67b83232c451588cb0f7226dd41f12d4af10b520b96d3e05bd`；expected manifest digest=`sha256:0f5853531e10b960378077b7837b972ac46656281d87c41f15f073a06d73a481`；actual image ID=`sha256:b3bccbbee1887d67b83232c451588cb0f7226dd41f12d4af10b520b96d3e05bd`（None=null/unknown）。recipe=`verified-assets-dependencies+materials-v1`；scripts_digest=`sha256:56667b0a30d20c1c968ac6756e0ec5e2ab65cd085ce2022cc7a7080ddfa5032e`。source-image tag另见P/public_bundle，不能以source镜像代替派生grader实际ID。
- candidate raw patch SHA=`sha256:4fb1556f5c38746e9a8562e2fe852aaea08a0d5ed9cb81cc4cab1ee1a5009e48`；projection frozen digest=`sha256:e50e7727248792327e8b46e041da48f50cf5d3768d073e42013e8cc078504b9e`；纳入路径=["monai/networks/nets/ahnet.py"]；ignored=[]。
- install={"install_rc_last_command": 0, "install_seconds": 5.288, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 0, "test_seconds": 698.484}。report F2P=1/1、P2P fail=0/35；reference_missing/skipped=[]/[]；解析测试数=40，segment外=0。
- 历史policy={"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}；budgets={"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}；resource={"mem_peak_mb": 2638.379, "mem_peak_unavailable_or_zero": false}，保持原字段不推单位。cleanup={"detail": "", "removed": true, "steps": ["rm:ok"]}；包源码导入=/testbed/monai/__init__.py；runner_integrity_changed=False。
- 原命令/关键输出（定向检索显示，未执行）：
  - L843: `+ python -m pip install types-pkg-resources==0.1.3 pytest`
  - L851: `+ pip install -r requirements-dev.txt`
  - L945: `+ python setup.py develop`
  - L1021: `RH2_INSTALL_RC=0`
  - L1031: `+ pytest -rA tests/test_ahnet.py tests/test_discriminator.py tests/test_generator.py tests/test_unet.py tests/test_vnet.py tests/utils.py`
  - L1124: `================= 40 passed, 27 warnings in 696.97s (0:11:36) ==================`
  - L1128: `RH2_TEST_RC=0`

### noop

- 原账本：`runs/env_recipe_repair_20260919/materials_v1/runs/Project-MONAI__MONAI-1121-noop/ledger.jsonl:1`，仅机械选定该行。原日志：`runs/env_recipe_repair_20260919/materials_v1/runs/Project-MONAI__MONAI-1121-noop/eval_logs/evallog_replay-er19-mat1-Project_e59e287f.eval.log`，授权范围1–1162。
- run_id=`er19-mat1-Project-MONAI__MONAI-1121-noop`；image_ref=`sha256:b3bccbbee1887d67b83232c451588cb0f7226dd41f12d4af10b520b96d3e05bd`；expected manifest digest=`sha256:0f5853531e10b960378077b7837b972ac46656281d87c41f15f073a06d73a481`；actual image ID=`sha256:b3bccbbee1887d67b83232c451588cb0f7226dd41f12d4af10b520b96d3e05bd`（None=null/unknown）。recipe=`verified-assets-dependencies+materials-v1`；scripts_digest=`sha256:56667b0a30d20c1c968ac6756e0ec5e2ab65cd085ce2022cc7a7080ddfa5032e`。source-image tag另见P/public_bundle，不能以source镜像代替派生grader实际ID。
- candidate raw patch SHA=`None`；projection frozen digest=`sha256:771ce7c8c0170c5c6c0109ba03d433917cd2641bd9fa53f8b63b83e328bbf528`；纳入路径=[]；ignored=[]。
- install={"install_rc_last_command": 0, "install_seconds": 5.233, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 1, "test_seconds": 542.216}。report F2P=0/1、P2P fail=0/35；reference_missing/skipped=[]/[]；解析测试数=40，segment外=0。
- 历史policy={"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}；budgets={"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}；resource={"mem_peak_mb": 2633.566, "mem_peak_unavailable_or_zero": false}，保持原字段不推单位。cleanup={"detail": "", "removed": true, "steps": ["rm:ok"]}；包源码导入=/testbed/monai/__init__.py；runner_integrity_changed=False。
- 原命令/关键输出（定向检索显示，未执行）：
  - L813: `+ python -m pip install types-pkg-resources==0.1.3 pytest`
  - L821: `+ pip install -r requirements-dev.txt`
  - L915: `+ python setup.py develop`
  - L991: `RH2_INSTALL_RC=0`
  - L1001: `+ pytest -rA tests/test_ahnet.py tests/test_discriminator.py tests/test_generator.py tests/test_unet.py tests/test_vnet.py tests/utils.py`
  - L1155: `============ 1 failed, 39 passed, 27 warnings in 540.68s (0:09:00) =============`
  - L1159: `RH2_TEST_RC=1`

### Expected逐项对账

每项行号指上文相应noop/gold原日志末尾状态行。语义覆盖范围在正文逐函数/参数表中，以下不是以状态数替代语义。

| 类别 | 测试ID | noop状态/行 | gold状态/行 |
|---|---|---|---|
| F2P | `tests/test_ahnet.py::TestAHNET::test_script` | FAILED/L1154 | PASSED/L1096 |
| P2P | `tests/test_unet.py::TestUNET::test_shape_0` | PASSED/L1140 | PASSED/L1110 |
| P2P | `tests/test_vnet.py::TestVNet::test_vnet_shape_5` | PASSED/L1153 | PASSED/L1123 |
| P2P | `tests/test_ahnet.py::TestAHNETWithPretrain::test_ahnet_shape_2` | PASSED/L1129 | PASSED/L1099 |
| P2P | `tests/test_ahnet.py::TestAHNET::test_ahnet_shape_5` | PASSED/L1126 | PASSED/L1095 |
| P2P | `tests/test_generator.py::TestGenerator::test_shape_2` | PASSED/L1138 | PASSED/L1108 |
| P2P | `tests/test_ahnet.py::TestAHNETWithPretrain::test_initialize_pretrained` | PASSED/L1130 | PASSED/L1100 |
| P2P | `tests/test_ahnet.py::TestAHNETWithPretrain::test_ahnet_shape_0` | PASSED/L1127 | PASSED/L1097 |
| P2P | `tests/test_ahnet.py::TestMCFCN::test_mcfcn_shape_1` | PASSED/L1119 | PASSED/L1088 |
| P2P | `tests/test_ahnet.py::TestAHNET::test_ahnet_shape_4` | PASSED/L1125 | PASSED/L1094 |
| P2P | `tests/test_unet.py::TestUNET::test_shape_3` | PASSED/L1143 | PASSED/L1113 |
| P2P | `tests/test_vnet.py::TestVNet::test_script` | PASSED/L1147 | PASSED/L1117 |
| P2P | `tests/test_unet.py::TestUNET::test_shape_4` | PASSED/L1144 | PASSED/L1114 |
| P2P | `tests/test_vnet.py::TestVNet::test_vnet_shape_3` | PASSED/L1151 | PASSED/L1121 |
| P2P | `tests/test_ahnet.py::TestFCN::test_fcn_shape_1` | PASSED/L1116 | PASSED/L1085 |
| P2P | `tests/test_generator.py::TestGenerator::test_script` | PASSED/L1135 | PASSED/L1105 |
| P2P | `tests/test_ahnet.py::TestFCN::test_fcn_shape_0` | PASSED/L1115 | PASSED/L1084 |
| P2P | `tests/test_ahnet.py::TestMCFCN::test_mcfcn_shape_0` | PASSED/L1118 | PASSED/L1087 |
| P2P | `tests/test_ahnet.py::TestAHNETWithPretrain::test_ahnet_shape_1` | PASSED/L1128 | PASSED/L1098 |
| P2P | `tests/test_vnet.py::TestVNet::test_vnet_shape_1` | PASSED/L1149 | PASSED/L1119 |
| P2P | `tests/test_vnet.py::TestVNet::test_vnet_shape_2` | PASSED/L1150 | PASSED/L1120 |
| P2P | `tests/test_unet.py::TestUNET::test_shape_5` | PASSED/L1145 | PASSED/L1115 |
| P2P | `tests/test_ahnet.py::TestAHNET::test_ahnet_shape_2` | PASSED/L1123 | PASSED/L1092 |
| P2P | `tests/test_ahnet.py::TestAHNET::test_ahnet_shape_3` | PASSED/L1124 | PASSED/L1093 |
| P2P | `tests/test_ahnet.py::TestAHNET::test_ahnet_shape_0` | PASSED/L1121 | PASSED/L1090 |
| P2P | `tests/test_unet.py::TestUNET::test_shape_6` | PASSED/L1146 | PASSED/L1116 |
| P2P | `tests/test_vnet.py::TestVNet::test_vnet_shape_0` | PASSED/L1148 | PASSED/L1118 |
| P2P | `tests/test_ahnet.py::TestMCFCN::test_mcfcn_shape_2` | PASSED/L1120 | PASSED/L1089 |
| P2P | `tests/test_unet.py::TestUNET::test_script` | PASSED/L1139 | PASSED/L1109 |
| P2P | `tests/test_unet.py::TestUNET::test_shape_2` | PASSED/L1142 | PASSED/L1112 |
| P2P | `tests/test_generator.py::TestGenerator::test_shape_0` | PASSED/L1136 | PASSED/L1106 |
| P2P | `tests/test_vnet.py::TestVNet::test_vnet_shape_4` | PASSED/L1152 | PASSED/L1122 |
| P2P | `tests/test_unet.py::TestUNET::test_shape_1` | PASSED/L1141 | PASSED/L1111 |
| P2P | `tests/test_ahnet.py::TestFCN::test_fcn_shape_2` | PASSED/L1117 | PASSED/L1086 |
| P2P | `tests/test_ahnet.py::TestAHNET::test_ahnet_shape_1` | PASSED/L1122 | PASSED/L1091 |
| P2P | `tests/test_generator.py::TestGenerator::test_shape_1` | PASSED/L1137 | PASSED/L1107 |

全部expected在上述状态行找到，没有缺席/skip/xfail；原运行不是本轮执行，未证明重复稳定性。source_refs仅阅读本题导出身份，不沿共享源扩读；environment_record只把元数据、所选条目及source digest作为范围证据，未把其自带描述视作旧质量判决，也未读其历史质量记录。审查者见过本题gold与隐藏测试及授权原运行日志，因此此产物及审查工作区不能给独立solver；check29实际actor泄露仍unknown，check40仍未证明无漏检/误拒或抽样偏差。
