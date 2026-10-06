# Project-MONAI__MONAI-3566 history前独立私有初判

本稿由私有主审 e25_main_pack05_monai 在 history release 前完成。仅作静态审查；未执行或导入项目、测试、安装、网络、容器、模型或任务二，未读 history、旧质量结论、reviewer、其他包及根汇总。已授权读取本题 public_read（root 先前核 SHA 封存）、PUBLIC/PRIVATE 与 run_refs 指定本题原件。本文 P 指本题 PUBLIC，S=P/base，V 指本题 PRIVATE；源文件行号均为 base 或补丁文本，不能混作修后行号。

实际 actor 消息/初始工作树/UID、HOME、cwd、PATH、写权限、资产权限、网络与资源均 unknown。公开 bundle 是计划输入；历史 grader 的成功不替代 actor 验证。第一次读取派发卡用了绝对路径但未设置 workdir；其后全部 exec 明确使用卡内 ROOT；第一次没有读默认目录内容。本稿保存后冻结，不以历史补写。disposition=needs_review/static_review，usage.intended_use=development_diagnostic；additional_exclusions=[]、revision_refs=[]；本轮 token/费用未观察为 null。

## 初判与公开目标

公开请求是在已有 `LoadImage(reader="ITKReader", pixel_type=itk.UC)` 目录调用返回元数据中保留可用 DICOM 标签。私有测试却新增 `series_meta=True` 参数并仅检查一个标签。gold 将该参数默认设 False，故不带新参数的公开调用依然走旧读取路径。存在静态可确定的题意/验收错位；历史1/1 F2P通过只支持选项开启的单样本，不能认定公开默认示例已修复。

## 需求—断言双向表

| 要求/合理旧行为 | 公开依据 | 新增/受影响断言 | 覆盖及证据 |
|---|---|---|---|
| 题面原调用保留可用 DICOM 标签 | prompt:7–23；image_reader.py:187–269 | 新 TestLoadImage::test_itk_meta 改用 series_meta=True | 冲突/缺失：无默认调用标签断言；gold默认False。公开无这个参数或选项名的约定 |
| 标签真实来自所选系列 | prompt标签列表；series_name选择路径 | 同一CT_DICOM，idx=0008|103e；GDCMImageIO.GetLabelFromTag返回label；断言 f"{label}={meta[idx]}" == "Series Description=Routine Brain " | 覆盖单键单值（保留末尾空格）；不验证全部列出标签、不区分代表切片策略、不验证多系列/缺键输入。示例数据值合理可从fixture读取，但具体新参数无公开依据 |
| 保留体积shape、affine及原目录名 | image_reader.py:227–332；test_load_image.py:89–108 | test_itk_dicom_series_reader_0/1/2：affine矩阵、(16,16,4)及reverse索引(4,16,16)、filename_or_obj | P2P完整读；均未启用新选项。对新元数据分支的几何无直接断言 |
| ITK单文件、多输入、彩色通道 | read/get_data及test_load_image:73–87,131–199 | expected的test_itk_reader_0/2及multichannel；实际还执行_1/3 | 局部覆盖旧shape/affine/RGB数值；新series_meta对自定义IO kwargs及额外读取没有覆盖 |
| 其他reader与自定义reader继续工作 | LoadImage构造与fallback:93–225 | nibabel_reader_0…6、load_png、my_reader；实际额外kwargs/register/NIfTI多通道 | 全读相关断言；历史通过，不能替代DICOM新标签完整性 |
| 定时辅助保持行为 | tests/test_timedcall_dist.py全文；utils.TimedCall:438–557 | test.patch只把成功调用Linux超时10秒放宽20秒；good_call输出good，skip_timing输出testing，3个超时例抛TimeoutError（其中一项还要求Warning） | 无DICOM公开依据，是测试辅助范围变更；不新增生产修复要求。全部5项P2P实际通过 |

全部 test.patch 已读，仅一个新增 self.assertEqual 加一个非断言的定时器参数修改。`meta[idx]`先索引，因此缺标签也会失败，但只能证明这一个键；`out`未被新测试断言。未调用内部gold私有函数，不查源码布局；核心偏置是未公开参数而非代码文本。

## Gold与调用链、合理替代实现

base 的 ITKReader.__init__把未知kwargs保存，read合并后把目录转成GDCM所选series的文件名列表，直接 `itk.imread(name, **kwargs_)`；get_data只取返回图像已有dictionary并补几何字段。gold完整改动：新增series_meta属性/文档，目录先正常imread，然后在选项开启时额外 `itk.ImageSeriesReader.New(FileNames=name)`、Update，若dictionary array非空便将第0片字典赋给原体积；非目录维持imread。原体积的spacing/origin/direction仍供后续几何构造，不是用首片2D图像替换整个体积。

S/monai/transforms/io/array.py:93–225说明参数会送给reader，read异常在手动指定reader路径被吞后尝试其他reader，最终抛通用“cannot find suitable reader”；noop日志734在新参数调用处失败、788–793是这个通用错误，尚未走到标签assert。静态路径支持未知series_meta被透传imread是原因候选；没有底层原始TypeError日志，不能把根因当已直接观测，也不能据通用建议安装依赖误判为缺ITK，旧ITK用例同run已通过。

合理非gold实现可以默认保留标签，或使用现有ITK流程保存dictionary、从代表切片读取真实标签，保留原接口。若它没有消费未公开series_meta参数，隐藏测试可能因透传未知kwargs失败，即便公开调用已修复；此为静态误拒风险，未运行替代解，不声称已实验误拒。另一方面，仅硬编码0008|103e一个值可满足新断言但不满足真实提取要求，是具体漏测路径。

gold取首片的策略可解释为代表元数据，但公开没有唯一要求；不能强制每片标签合并或新增患者字段验证。第二次读取未转交pixel_type、自定义imageio/其他kwargs，可能使选项开启时出现额外类型/IO兼容性和资源成本；这尚非已证回归。默认False延续旧行为，主要是需求未覆盖而非破坏原有合理行为。LoadImaged（dictionary.py:101–136）直接保存LoadImage元数据；新标签须经过switch_endianness(array.py:48–72)，字符串可行，其他ITK值型未穷举。check26 unknown；check27局部单样本正确、完整性有缺口。

## 开发条件和历史事实边界

| 操作/资产 | 公开依据 | 现有证据/缺口 | 最小公开命令与预期（未执行） |
|---|---|---|---|
| 明确默认行为或公开选项 | 原例、gold/test对照 | 当前包公开无series_meta；actor消息unknown | 先确认需求和验收统一到哪一种；不能靠运行替代决定 |
| Python/ITK/GDCM及源码导入 | requirements-dev:6，ITKReader | 历史itk_v2固定全组件5.2.1.post1/NumPy1.23.5，torch1.13.1+cu117/Python3.8.20；actor未验 | `python -c "import sys,itk,monai; print(sys.executable,itk.Version.GetITKVersion(),monai.__file__)"`应指工作树 |
| 四片CT_DICOM本地数据 | prompt及旧DICOM测试 | 公开reader列出四个切片；本稿未解析二进制。历史标签单例成功仅支持该grader可读 | 实际actor中核 `tests/testing_data/CT_DICOM`文件和读取权限，再执行题面原例；修复后包含真实DICOM标签且shape/affine不变 |
| 默认公开功能复现 | prompt | 历史没有原调用新增标签的assert | `python -c 'import itk; from monai.transforms import LoadImage; a,m=LoadImage(reader="ITKReader",pixel_type=itk.UC)("tests/testing_data/CT_DICOM"); print(a.shape,sorted(m))'`；应与样本可用标签比对，不能只看单标签 |
| 窄旧行为与字典包装 | test_load_image、LoadImaged | 当前actor未知；历史对应模块已完成 | `python -m unittest tests.test_load_image.TestLoadImage -k itk`；期望旧体积/通道通过，再用公共标签复现确认新行为 |
| 临时目录与子进程 | test_load_image写图像；TimedCall spawn/queue | grader2 CPU/4GiB策略可完成；actor写权限/PIDs未知 | 本地临时NIfTI读写可用；定时测试需spawn权限，无题目GPU必要性 |

历史日志先恢复test_load_image与test_timedcall_dist，再apply测试补丁。安装流程删除requirements-dev里Project-MONAI远端git依赖，pip已有依赖后setup.py develop；itk_v2先用 `/opt/rh2/compat-wheels` 的 `--no-index --no-deps` 全组件pin与numpy1.23.5覆盖原ITK5.4.0/numpy1.24.4，日志最后再核组件版本（noop:700–706）。不能把修复配方或缓存成功外推当前actor，也未借目录缺失猜资产不足。无证据要求GPU、训练、网络服务或真实患者数据。

唯一优先下一步：由任务拥有者对齐公开默认示例与隐藏series_meta选项，选择明确公开新选项或让验收覆盖原调用；这个静态错位已有充分证据，优先于CPU或模型探针。本稿不执行、不转派该修改。

## 检查编号、阅读范围

1 pass（静态与指定attempt）；2 pass仅“新验收在base失败”，公开原例缺标签由源码/题面支持、未在本次执行；3 unknown；4 pass仅源码候选能投影，actor权限unknown；6/7/8/9/17/18/19/21历史局部pass；10/11/13/14/15/16/22 unknown，20 issue（分差包含新增参数接受性，不是原调用标签断言）；23/24/25 issue；26 unknown；27 issue（开启选项单例正证据、公开目标完整性不足）；28 pass（不把多片归并/额外IO策略升格硬要求）；29 unknown；30–40 unknown（37仅看到依赖维修，未作完整等价证明）。by为本稿作者；证据见本表和附录；未列项not_checked。

已直接读：P三种元数据文件及prompt、公读稿；V gold/test/grading/validation/run_refs/source_refs和environment_record中引用字段；image_reader.py:107–335；io/array.py:48–72,93–225；io/dictionary.py:101–138；tests/test_load_image.py全文、test_timedcall_dist.py全文、utils.py:438–557；requirements.txt和dev:1–20。全部新增断言与所有expected P2P实现/参数已读。未读ITK第三方实现、未解析DICOM二进制、未全读其余MONAI源码/测试；LoadImaged外部一致性测试只参考已封存public_read，没有冒称本稿直接阅读。日志按附录/命令定位范围阅读，不称全量。原件中setup.py deprecation提示不是安装失败。

## 原件身份、运行证据与逐测试状态附录

P=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-3566`；V=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/Project-MONAI__MONAI-3566`。base_commit=`9417ff217843db1cee7aef53b367cf1a7b21b7da`，source版本=0.8，adapter=`rh2.private_grading_bundle.v2`，vendor=`swegym_constants_242429c1`。gold/test patch全文已读，test.patch与grading.test_patch标准库字节比较相同；gold与validation及原候选绑定由root先核，本稿又逐项读取run_refs允许的projection/baseline/stage JSON指针，HEAD/base同本题。原候选SHA与投影SHA是不同含义，不混用。

### gold

- 原账本：`runs/env_recipe_repair_20260919/itk_v2/tasks/Project-MONAI__MONAI-3566/gold/ledger.jsonl:1`，仅机械选定该行。原日志：`runs/env_recipe_repair_20260919/itk_v2/tasks/Project-MONAI__MONAI-3566/gold/eval_logs/evallog_replay-er19-itk_v2-Proje_30a04be3.eval.log`，授权范围1–882。
- run_id=`er19-itk_v2-Project-MONAI__MONAI-3566-gold`；image_ref=`sha256:eae21d6d574c7cd6107c0b2ee1c67d613e3c7af89f58ee91253e616515d866c3`；expected manifest digest=`sha256:4e9c1b27c58f657611dc46164bf710ced21b6b2987cc4759dd084d1b4c72f3d6`；actual image ID=`sha256:eae21d6d574c7cd6107c0b2ee1c67d613e3c7af89f58ee91253e616515d866c3`（None=null/unknown）。recipe=`itk_v2:Project-MONAI__MONAI-3566`；scripts_digest=`sha256:d808c4f1fb4a20294e2c787722b1e551724a1062c9ec83bb0747d652f89a06a8`。source-image tag另见P/public_bundle，不能以source镜像代替派生grader实际ID。
- candidate raw patch SHA=`sha256:72d3c83a84418378f8b230a73308721484bc942ce8a770040e4743be76100f3d`；projection frozen digest=`sha256:87d0e509f7ef616e1d8a947b09d5572421c96cec861c7536dc29864c395e72aa`；纳入路径=["monai/data/image_reader.py"]；ignored=[]。
- install={"install_rc_last_command": 0, "install_seconds": 34.107, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 0, "test_seconds": 52.733}。report F2P=1/1、P2P fail=0/20；reference_missing/skipped=[]/[]；解析测试数=26，segment外=0。
- 历史policy={"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}；budgets={"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}；resource={"mem_peak_mb": 2209.719, "mem_peak_unavailable_or_zero": false}，保持原字段不推单位。cleanup={"detail": "", "removed": true, "steps": ["rm:ok"]}；包源码导入=/testbed/monai/__init__.py；runner_integrity_changed=False。
- 原命令/关键输出（定向检索显示，未执行）：
  - L426: `+ python -m pip install --no-index --find-links=/opt/rh2/compat-wheels --no-deps itk==5.2.1.post1 itk-core==5.2.1.post1 itk-io==5.2.1.post1 itk-filtering==5.2.1.post1 itk-numerics==5.2.1.post1 itk-registration==5.2.1.post1 itk-segmentation==5.2.1.post1 numpy==1.23.5`
  - L473: `+ python -m pip install types-pkg-resources==0.1.3 pytest`
  - L481: `+ pip install -r requirements-dev.txt`
  - L646: `+ python setup.py develop`
  - L763: `RH2_INSTALL_RC=0`
  - L773: `+ pytest -rA tests/test_load_image.py tests/test_timedcall_dist.py`
  - L875: `======================= 26 passed, 17 warnings in 50.91s =======================`
  - L879: `RH2_TEST_RC=0`

### noop

- 原账本：`runs/env_recipe_repair_20260919/itk_v2/tasks/Project-MONAI__MONAI-3566/noop/ledger.jsonl:1`，仅机械选定该行。原日志：`runs/env_recipe_repair_20260919/itk_v2/tasks/Project-MONAI__MONAI-3566/noop/eval_logs/evallog_replay-er19-itk_v2-Proje_147443e1.eval.log`，授权范围1–884。
- run_id=`er19-itk_v2-Project-MONAI__MONAI-3566-noop`；image_ref=`sha256:eae21d6d574c7cd6107c0b2ee1c67d613e3c7af89f58ee91253e616515d866c3`；expected manifest digest=`sha256:4e9c1b27c58f657611dc46164bf710ced21b6b2987cc4759dd084d1b4c72f3d6`；actual image ID=`sha256:eae21d6d574c7cd6107c0b2ee1c67d613e3c7af89f58ee91253e616515d866c3`（None=null/unknown）。recipe=`itk_v2:Project-MONAI__MONAI-3566`；scripts_digest=`sha256:d808c4f1fb4a20294e2c787722b1e551724a1062c9ec83bb0747d652f89a06a8`。source-image tag另见P/public_bundle，不能以source镜像代替派生grader实际ID。
- candidate raw patch SHA=`None`；projection frozen digest=`sha256:3c10fbc8f58cf6f3a20ec9acd22c65a81782d66c8fa20a721c0b2151b36042f3`；纳入路径=[]；ignored=[]。
- install={"install_rc_last_command": 0, "install_seconds": 39.29, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 1, "test_seconds": 54.057}。report F2P=0/1、P2P fail=0/20；reference_missing/skipped=[]/[]；解析测试数=26，segment外=0。
- 历史policy={"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}；budgets={"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}；resource={"mem_peak_mb": 3352.09, "mem_peak_unavailable_or_zero": false}，保持原字段不推单位。cleanup={"detail": "", "removed": true, "steps": ["rm:ok"]}；包源码导入=/testbed/monai/__init__.py；runner_integrity_changed=False。
- 原命令/关键输出（定向检索显示，未执行）：
  - L369: `+ python -m pip install --no-index --find-links=/opt/rh2/compat-wheels --no-deps itk==5.2.1.post1 itk-core==5.2.1.post1 itk-io==5.2.1.post1 itk-filtering==5.2.1.post1 itk-numerics==5.2.1.post1 itk-registration==5.2.1.post1 itk-segmentation==5.2.1.post1 numpy==1.23.5`
  - L416: `+ python -m pip install types-pkg-resources==0.1.3 pytest`
  - L424: `+ pip install -r requirements-dev.txt`
  - L589: `+ python setup.py develop`
  - L706: `RH2_INSTALL_RC=0`
  - L716: `+ pytest -rA tests/test_load_image.py tests/test_timedcall_dist.py`
  - L877: `================== 1 failed, 25 passed, 17 warnings in 52.19s ==================`
  - L881: `RH2_TEST_RC=1`

### Expected逐项对账

每项行号指上文相应noop/gold原日志末尾状态行。语义覆盖范围在正文逐函数/参数表中，以下不是以状态数替代语义。

| 类别 | 测试ID | noop状态/行 | gold状态/行 |
|---|---|---|---|
| F2P | `tests/test_load_image.py::TestLoadImage::test_itk_meta` | FAILED/L876 | PASSED/L852 |
| P2P | `tests/test_timedcall_dist.py::TestTimedCall::test_skip_timing` | PASSED/L872 | PASSED/L871 |
| P2P | `tests/test_load_image.py::TestLoadImage::test_my_reader` | PASSED/L862 | PASSED/L861 |
| P2P | `tests/test_load_image.py::TestLoadImage::test_nibabel_reader_6` | PASSED/L869 | PASSED/L868 |
| P2P | `tests/test_load_image.py::TestLoadImage::test_itk_dicom_series_reader_1` | PASSED/L852 | PASSED/L850 |
| P2P | `tests/test_load_image.py::TestLoadImage::test_nibabel_reader_0` | PASSED/L863 | PASSED/L862 |
| P2P | `tests/test_load_image.py::TestLoadImage::test_itk_dicom_series_reader_0` | PASSED/L851 | PASSED/L849 |
| P2P | `tests/test_load_image.py::TestLoadImage::test_itk_reader_0` | PASSED/L854 | PASSED/L853 |
| P2P | `tests/test_load_image.py::TestLoadImage::test_load_png` | PASSED/L861 | PASSED/L860 |
| P2P | `tests/test_timedcall_dist.py::TestTimedCall::test_timeout` | PASSED/L873 | PASSED/L872 |
| P2P | `tests/test_load_image.py::TestLoadImage::test_nibabel_reader_2` | PASSED/L865 | PASSED/L864 |
| P2P | `tests/test_timedcall_dist.py::TestTimedCall::test_timeout_not_force_quit` | PASSED/L875 | PASSED/L874 |
| P2P | `tests/test_load_image.py::TestLoadImage::test_nibabel_reader_4` | PASSED/L867 | PASSED/L866 |
| P2P | `tests/test_load_image.py::TestLoadImage::test_itk_dicom_series_reader_2` | PASSED/L853 | PASSED/L851 |
| P2P | `tests/test_load_image.py::TestLoadImage::test_nibabel_reader_5` | PASSED/L868 | PASSED/L867 |
| P2P | `tests/test_timedcall_dist.py::TestTimedCall::test_good_call` | PASSED/L871 | PASSED/L870 |
| P2P | `tests/test_load_image.py::TestLoadImage::test_nibabel_reader_1` | PASSED/L864 | PASSED/L863 |
| P2P | `tests/test_load_image.py::TestLoadImage::test_nibabel_reader_3` | PASSED/L866 | PASSED/L865 |
| P2P | `tests/test_timedcall_dist.py::TestTimedCall::test_timeout_bad` | PASSED/L874 | PASSED/L873 |
| P2P | `tests/test_load_image.py::TestLoadImage::test_itk_reader_multichannel` | PASSED/L858 | PASSED/L857 |
| P2P | `tests/test_load_image.py::TestLoadImage::test_itk_reader_2` | PASSED/L856 | PASSED/L855 |

全部expected在上述状态行找到，没有缺席/skip/xfail；原运行不是本轮执行，未证明重复稳定性。source_refs仅阅读本题导出身份，不沿共享源扩读；environment_record只把元数据、所选条目及source digest作为范围证据，未把其自带描述视作旧质量判决，也未读其历史质量记录。审查者见过本题gold与隐藏测试及授权原运行日志，因此此产物及审查工作区不能给独立solver；check29实际actor泄露仍unknown，check40仍未证明无漏检/误拒或抽样偏差。
