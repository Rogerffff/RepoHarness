# Project-MONAI__MONAI-4583 history前独立私有初判

本稿由私有主审 e25_main_pack05_monai 在 history release 前完成。仅作静态审查；未执行或导入项目、测试、安装、网络、容器、模型或任务二，未读 history、旧质量结论、reviewer、其他包及根汇总。已授权读取本题 public_read（root 先前核 SHA 封存）、PUBLIC/PRIVATE 与 run_refs 指定本题原件。本文 P 指本题 PUBLIC，S=P/base，V 指本题 PRIVATE；源文件行号均为 base 或补丁文本，不能混作修后行号。

实际 actor 消息/初始工作树/UID、HOME、cwd、PATH、写权限、资产权限、网络与资源均 unknown。公开 bundle 是计划输入；历史 grader 的成功不替代 actor 验证。第一次读取派发卡用了绝对路径但未设置 workdir；其后全部 exec 明确使用卡内 ROOT；第一次没有读默认目录内容。本稿保存后冻结，不以历史补写。disposition=needs_review/static_review，usage.intended_use=development_diagnostic；additional_exclusions=[]、revision_refs=[]；本轮 token/费用未观察为 null。

## 初判与公开目标

题面给出二维反对角前景：背景-1，前景0，正确框是[0,0,2,2]、标签0。base分别取各轴最小值形成框，再从框角点取标签；(0,0)虽是包围框角却为背景。gold改从同一真实前景坐标取值；与公开契约匹配，历史4项F2P/5项P2P对照成立。静态保留候选，但不是actor资格或正式训练批准。主要风险是二维稀疏反例覆盖了新增目标，三维相同缺陷及类型精确约束未被充分验收。

## 需求—断言双向表

| 需求或旧行为 | 公开依据 | 全部新/受影响断言 | 覆盖、证据及限制 |
|---|---|---|---|
| 二维单通道反例框不变、类别0 | prompt；box_ops.py:273–320 | test_value_2d_mask_0/_1：np.array/torch.as_tensor，框[[0,0,2,2]]、标签[0] | 直接覆盖题面；noop返回[-1]，gold通过；type/device开关True，atol=1e-3 |
| 多通道分别保留类别 | 同函数每通道一框契约280–282；标题multi-class | _2/_3：两通道相同反对角，类别0、1；预期双框和[0,1] | 覆盖2D多类，noop[-1,-1]，gold通过；未测任意非默认背景/空通道/大坐标 |
| 三维输入也取真实前景类别 | 返回Nx6，shape支持3/4；dict包装旋转/裁剪例 | 无新3D稀疏前景断言；旧test_value_3d_mask仅长方体往返 | 部分。只修2D、保留旧3D角取值的补丁可通过现有选中用例但仍有3D同根因，是静态具体漏测（未运行变异） |
| 2D字典包装/类别平移 | BoxToMaskd:911–923；MaskToBoxd:992–1001 | test_value_2d_0/_1：两个矩形类1/0，float32/float16；mask数值及回框/标签allclose | 已完整读，历史P2P通过；rectangle角本来是前景，不能覆盖稀疏bug |
| 3D包装、类别与几何 | test_box_transform:91–113 | test_value_3d_mask：三个立方体类1/0/3、shape(3,32,33,34)、box/label往返 | 旧P2P通过；float32/float16是输入cast，box/label回值比较禁type/device检查，不证明所有输出dtype |
| 其他框变换保留 | test_box_transform:36–55,115–287 | test_value_3d_0/_1：mode转换、zoom/inverse、缺affine错误、world/image affine、flip、clip去空并同步labels/scores、crop数量/对齐、90度旋转及inverse | 全文读断言，历史通过；多数不经过mask提标签路径，不当目标覆盖 |
| NumPy/Tensor类型、device与输出dtype参数 | type_conversion.py:294–336；box_ops:318–319 | 新helper assert_allclose实际检查ndarray/Tensor类别与device，随后detach→cpu→numpy数值比较 | type/device有覆盖；没有dtype精确assert，默认float32/long及自定义dtype未被这两个assert严格检验 |
| 空通道与空输出 | box_ops:301–302,314–319 | 本题新增无覆盖 | gold未改该分支；未证明全库无覆盖，也未把缺测试归为已证gold回归 |

所有新增断言只有boxes与labels两次assert_allclose，分别参数化四项；无隐藏实现名/源码结构要求。测试用统一前景类别，符合每个通道一个box的文档。单通道多个不同非背景值属于未定义/不符合该前提的输入，不额外要求拆类或连通分量。

## Gold与调用者、替代解、回归

gold仅移动boxes_list.append并把2D/3D标签取值改成 `fg_indices[d][0]` 的同索引坐标。np.nonzero各轴数组同位置属于同一前景点；空通道已先跳过，所以索引0在此处有定义。包围框各轴min/max+1-TO_REMOVE（TO_REMOVE=0.0）不变，标签顺序仍与非空通道框顺序对齐，dtype/device转换不变。对旧矩形前景角本身有类别，新取值与旧一致；对稀疏/旋转/椭球前景新取值消除背景角问题。此为静态证明的受限语义论证，加历史选中用例证据，不是所有数值dtype/设备的运行证明。

已核MaskToBox→convert_mask_to_box；BoxToMaskd使用min_fg_label-1为背景并整体减背景，MaskToBoxd再加回背景；gold不破坏这条标签平移路径。convert_box_to_mask支持ellipse_mask，dictionary公开文档提旋转/裁剪，因此非矩形3D不是审查者任意发明的要求。合理非gold可使用任一确定前景点，或在背景小于前景、每通道同一类的输入契约内取最大值；验收不锁定gold写法。未执行其他实现，不声称普遍无误拒。

一个具体未测不完整修复是仅修改2D分支；例如3D前景位于(0,1,0)、(1,0,1)，类别2，背景-1，仍应返回框[0,0,0,2,2,2]与[2]，旧3D取(0,0,0)得-1。此例由已公开函数3D范围/包装用途推导，静态手算、未执行。gold本身处理该例的理由充分，不能把测试缺口说成gold已回归。精确dtype、任意合法背景、混合空通道、MetaTensor以及可选CUDA还缺有范围的执行证据。

TEST_NDARRAYS的base helper:711–719值得单列：无CUDA时是(np.array,torch.as_tensor)，CUDA可用时719又赋为(TEST_TORCH_TENSORS+gpu_tensor)，覆盖原先含NumPy元组。因而编号_0…_3的类型语义随环境可变化；不要假定GPU run会自动多出第5/6个用例。当前日志中_0输入/报错以NumPy、_1以Tensor表现，4项对应该CPU分支；本稿不修该旧helper，也不作全平台状态映射保证。

## 开发、交付和运行条件

| 必要操作/资产 | 公开依据 | 已有证据/缺口 | 最小公开命令与预期（未执行） |
|---|---|---|---|
| 实际工作树/导入与源码写权限 | prompt、public_hints、requirements | 历史仅box_ops候选投影和工作区导入；actor消息/初态unknown | `git status --porcelain=v1`、`git diff`，`python -c 'import sys,monai,numpy,torch; print(sys.executable,monai.__file__,numpy.__version__,torch.__version__)'` |
| 原公开复现 | prompt | noop历史同反例失败；gold同验收通过；当前actor未验 | `python -c 'import numpy as np; from monai.apps.detection.transforms.box_ops import convert_mask_to_box; print(convert_mask_to_box(np.asarray([[[-1,0],[0,-1]]])))'`；修后框float32和类0 |
| 窄旧回归 | tests/test_box_transform全文 | 历史9项跑完，无skip；actor参数化工具unknown | `python -m unittest tests.test_box_transform`；保持公开旧断言，单模块即可 |
| 3D同根因与类型/空通道 | 3D契约、函数分支 | 静态具体漏测；不需外部素材 | 合成上述两点3D前景，numpy/Tensor各调公开API，断言box和label；空通道与非默认bg作为同一小矩阵附加，不修改可信测试 |
| CPU和依赖 | requirements.txt torch>=1.7/numpy>=1.17；min parameterized | 历史Python3.8.20/torch1.13.1+cu117/numpy1.24.4，actorunknown | 内存数组即可；不需要模型、GPU、网络或数据下载；可选GPU保持device验证另记 |

noop/gold原日志132起分别显示干净/仅box_ops修改；随后git show仅是base提交。恢复test_box_transform（noop218/gold242）再apply，gold投影仅box_ops，没有候选测试路径；证明本次源码合法交付局部路径，不证明评分控制面普遍不可改。安装删除远端git依赖，已有依赖与setup.py develop最后RC0；无本次目标资产阻断。runtime actual image ID未采集为null，不能用manifest digest当实际ID。

唯一优先下一步：由任务二在实际actor条件运行一个公开API的最小3D稀疏前景对照，连同题面2D例记录导入位置、初态、RC、框/标签/dtype；私有隔离gold对照用同命令核3D根因消失。该步骤同时针对明确3D漏测疑点和actor开发资格缺证据，不要求全仓、GPU或模型；本稿未执行或派发。

## 检查编号与阅读范围

1 pass（静态base/patch/指定attempt）；2 pass（明确标签反例）；3 unknown；4 pass仅候选源码投影范围，actorunknown；6/7/8/9/17/18/19/20/21历史局部pass；10/11/13/14/15/16/22 unknown（历史网络/资源字段不算actor事实）；23 pass（目标与调用链可解释）；24 unknown（无唯一实现限制证据，但未跑替代解）；25 issue（3D稀疏/dtype覆盖缺口）；26 unknown（无已证gold回归）；27 pass仅所述契约和选中路径；28 pass（额外建议均来源公开契约，不把未定义混类输入强加）；29 unknown；30/31/32/33/34/35/36/37/38/39/40 unknown。未列项not_checked，by为本稿作者，证据见正文及附录；流程合规不证明筛查无偏差。

已直接读P元数据/prompt、公读稿；V gold/test/grading/validation/run_refs/source_refs与environment字段；box_ops.py:196–322；array.py:365–449；dictionary.py可见837–1005中重点894–1002（前段展示曾截断，未将其全部算已读）；test_box_transform.py全文1–291；utils.py:77–143,700–730；type_conversion.py:294–340；box_utils:40–45；requirements.txt/min全文。所有新增/选中旧断言全文已读；其他框变换生产实现未全文审查，不因P2P全过证明所有回归。日志定位范围见附录，没有读其他任务行、旧质量记录、外部链接或实际actor。

## 原件身份、运行证据与逐测试状态附录

P=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-4583`；V=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/Project-MONAI__MONAI-4583`。base_commit=`9c4710199b80178ad11f7dd74925eee3ae921863`，source版本=0.9，adapter=`rh2.private_grading_bundle.v2`，vendor=`swegym_constants_242429c1`。gold/test patch全文已读，test.patch与grading.test_patch标准库字节比较相同；gold与validation及原候选绑定由root先核，本稿又逐项读取run_refs允许的projection/baseline/stage JSON指针，HEAD/base同本题。原候选SHA与投影SHA是不同含义，不混用。

### noop

- 原账本：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w06-0/ledger.jsonl:1`，仅机械选定该行。原日志：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w06-0/eval_logs/evallog_replay-f216-baseline01-w_8246538a.eval.log`，授权范围1–928。
- run_id=`f216-baseline01-w06-0`；image_ref=`xingyaoww/sweb.eval.x86_64.project-monai_s_monai-4583:latest`；expected manifest digest=`sha256:79bf18ecd969a2e68a113b6d29b3d9e77ed977e37bd02666f17eef51930824d5`；actual image ID=`None`（None=null/unknown）。recipe=`None`；scripts_digest=`sha256:0b2546c62263339a4260468e89792f755570eef61ab613297c106f3d122292d0`。source-image tag另见P/public_bundle，不能以source镜像代替派生grader实际ID。
- candidate raw patch SHA=`None`；projection frozen digest=`sha256:f9e00af0238b6bf9e84728b3e1928d81da76aa138240f30965c4a9eea741f663`；纳入路径=[]；ignored=[]。
- install={"install_rc_last_command": 0, "install_seconds": 9.787, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 1, "test_seconds": 10.632}。report F2P=0/4、P2P fail=0/5；reference_missing/skipped=[]/[]；解析测试数=9，segment外=0。
- 历史policy={"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}；budgets={"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}；resource={"mem_peak_mb": 936.129, "mem_peak_unavailable_or_zero": false}，保持原字段不推单位。cleanup={"detail": "", "removed": true, "steps": ["rm:ok"]}；包源码导入=/testbed/monai/__init__.py；runner_integrity_changed=False。
- 原命令/关键输出（定向检索显示，未执行）：
  - L393: `+ python -m pip install types-pkg-resources==0.1.3 pytest`
  - L401: `+ pip install -r requirements-dev.txt`
  - L586: `+ python setup.py develop`
  - L699: `RH2_INSTALL_RC=0`
  - L709: `+ pytest -rA tests/test_box_transform.py`
  - L921: `=================== 4 failed, 5 passed, 22 warnings in 9.00s ===================`
  - L925: `RH2_TEST_RC=1`

### gold

- 原账本：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w06-0/ledger.jsonl:2`，仅机械选定该行。原日志：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w06-0/eval_logs/evallog_replay-f216-baseline01-w_609ff299.eval.log`，授权范围1–815。
- run_id=`f216-baseline01-w06-0`；image_ref=`xingyaoww/sweb.eval.x86_64.project-monai_s_monai-4583:latest`；expected manifest digest=`sha256:79bf18ecd969a2e68a113b6d29b3d9e77ed977e37bd02666f17eef51930824d5`；actual image ID=`None`（None=null/unknown）。recipe=`None`；scripts_digest=`sha256:0b2546c62263339a4260468e89792f755570eef61ab613297c106f3d122292d0`。source-image tag另见P/public_bundle，不能以source镜像代替派生grader实际ID。
- candidate raw patch SHA=`sha256:c1969e4884ce48981edd183d1458b54e8593628eb9fd9beb6602ba8f1f4f063b`；projection frozen digest=`sha256:cd7a6c58540fe4cb5a45e834bc425066d666cb398fbf8e29d826fb36a5b688bd`；纳入路径=["monai/apps/detection/transforms/box_ops.py"]；ignored=[]。
- install={"install_rc_last_command": 0, "install_seconds": 7.728, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 0, "test_seconds": 9.366}。report F2P=4/4、P2P fail=0/5；reference_missing/skipped=[]/[]；解析测试数=9，segment外=0。
- 历史policy={"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}；budgets={"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}；resource={"mem_peak_mb": 464.328, "mem_peak_unavailable_or_zero": false}，保持原字段不推单位。cleanup={"detail": "", "removed": true, "steps": ["rm:ok"]}；包源码导入=/testbed/monai/__init__.py；runner_integrity_changed=False。
- 原命令/关键输出（定向检索显示，未执行）：
  - L417: `+ python -m pip install types-pkg-resources==0.1.3 pytest`
  - L425: `+ pip install -r requirements-dev.txt`
  - L610: `+ python setup.py develop`
  - L723: `RH2_INSTALL_RC=0`
  - L733: `+ pytest -rA tests/test_box_transform.py`
  - L808: `======================== 9 passed, 22 warnings in 7.68s ========================`
  - L812: `RH2_TEST_RC=0`

### Expected逐项对账

每项行号指上文相应noop/gold原日志末尾状态行。语义覆盖范围在正文逐函数/参数表中，以下不是以状态数替代语义。

| 类别 | 测试ID | noop状态/行 | gold状态/行 |
|---|---|---|---|
| F2P | `tests/test_box_transform.py::TestBoxTransform::test_value_2d_mask_1` | FAILED/L918 | PASSED/L802 |
| F2P | `tests/test_box_transform.py::TestBoxTransform::test_value_2d_mask_3` | FAILED/L920 | PASSED/L804 |
| F2P | `tests/test_box_transform.py::TestBoxTransform::test_value_2d_mask_0` | FAILED/L917 | PASSED/L801 |
| F2P | `tests/test_box_transform.py::TestBoxTransform::test_value_2d_mask_2` | FAILED/L919 | PASSED/L803 |
| P2P | `tests/test_box_transform.py::TestBoxTransform::test_value_3d_1` | PASSED/L915 | PASSED/L806 |
| P2P | `tests/test_box_transform.py::TestBoxTransform::test_value_3d_mask` | PASSED/L916 | PASSED/L807 |
| P2P | `tests/test_box_transform.py::TestBoxTransform::test_value_2d_1` | PASSED/L913 | PASSED/L800 |
| P2P | `tests/test_box_transform.py::TestBoxTransform::test_value_3d_0` | PASSED/L914 | PASSED/L805 |
| P2P | `tests/test_box_transform.py::TestBoxTransform::test_value_2d_0` | PASSED/L912 | PASSED/L799 |

全部expected在上述状态行找到，没有缺席/skip/xfail；原运行不是本轮执行，未证明重复稳定性。source_refs仅阅读本题导出身份，不沿共享源扩读；environment_record只把元数据、所选条目及source digest作为范围证据，未把其自带描述视作旧质量判决，也未读其历史质量记录。审查者见过本题gold与隐藏测试及授权原运行日志，因此此产物及审查工作区不能给独立solver；check29实际actor泄露仍unknown，check40仍未证明无漏检/误拒或抽样偏差。
