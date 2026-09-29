# L1_monai_1 · 逐题静态审查小结

范围：Project-MONAI/MONAI 13 题（ASSIGNMENT.json 顺序）。方法：先只看 `problem_statement` + base 代码写 `public_view`，再读 `test_patch` / `fail_to_pass` / `pass_to_pass` / `golden_patch` / `hints_text`。
base 代码用裸克隆的 `git show <base_commit>:<path>` / `git grep` 读取（COMMON.md 允许的只读操作），**未建 worktree、未起 Docker、未装依赖、未调用模型 API、未连任何远程机器**。
逐题记录：`records/<instance_id>.json`（13 个，均为合法 JSON）。脚本（8 个，均可重跑）：`scripts/{prescan,dupidx,newfile_scan,bogus_statusmap,skipscan,p2p_mechanism,conftest_scan,evalcmd_nontest_scan}.py`。
大文件产物在 `runs/env_overnight_20260916/L1_monai_1/`：`mat/`（13 题四面材料抽取）、`prescan.json`、`dupidx.txt`、`newfile_scan.txt`、`bogus_statusmap.txt`、`skipscan.txt`、`p2p_mechanism.txt`、`conftest_scan.txt`、`evalcmd_nontest_scan.txt`、`monai_extra_scans.txt`。

**MONAI 的评分形状与 mypy 完全不同**：`eval_cmd` 是 `pytest -rA ` 后面直接跟 **test_patch 触碰的整份测试文件**（不是 `-k` 选择器）。实跑命令见 `runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/<tid>/gold/offline/a1/eval.sh` 的 `pytest` 行。

| task | 主要发现 | 建议处置 | 下一实验 |
| --- | --- | --- | --- |
| MONAI-1121 | **离线硬阻断**：8 条 P2P（TestFCN/TestMCFCN/TestAHNETWithPretrain）要下载 torchvision ResNet50 ImageNet 权重，gold 在离线 stage1 判 **RESOLVED_NO**，与 no-op 零分差。题面 245 字符是一条「补 TorchScript 单测」的 feature request，而 public_hints 明令禁改测试；真正要改的 `ahnet.py` 两处（`dropout_prob = 0` 的 int 字面量、`tuple(x.size()[2:])`）题面零线索。另有 6 条 `::test_script_save` 误收集 ERROR，和 4 条 `np.int` 已删除导致的 test_discriminator 失败 | needs_repair | 把 `resnet50-0676ba61.pth` 预置进 `/root/.cache/torch/hub/checkpoints/` 重跑 gold/empty，确认 gold→FULL |
| MONAI-3205 | **离线硬阻断且更严重**：唯一的 F2P 在 **gold 侧也 FAILED**（要从 `msd-for-monai.s3-us-west-2.amazonaws.com` 下载 Task04_Hippocampus.tar）。**P2P=0**。题面是一条论坛式提问（「训练集验证集要用不同 transform，请问怎么处理」），不含任何 API 规格，而 F2P 要求 `get_dataset(folds, **dataset_params)` 这个精确形状 | needs_repair（数据体积不可接受则 reject_revision） | 先量 Task04_Hippocampus.tar 体积；预置后重跑确认 gold→FULL、empty→NO |
| MONAI-2454 | 题干净（gold=FULL / empty=NO、3s、无网络），但两件事要先定：(a) **test_patch 是新建文件** `tests/test_to_tensor.py`，恢复步骤对 base 不存在的路径直接跳过，候选若在同名路径写自己的复现测试就会让 `git apply` 失败 → 整题按 `official_test_patch_apply_failed` 判 0，**真实 DeepSeek 轨迹就是这么挂的**；(b) 题面只说 numpy 0 维，F2P 却要求 Python 标量 `5` 也保形，按题面字面修好会判 0。另：`return torch.as_tensor(img)` 一行假修复可满分（丢掉 contiguous 语义） | needs_review | 构造「候选同名新建测试」的 patch 跑现行 v2 setup，确认落到 apply_failed；加 `rm -f` 后重跑 |
| MONAI-6975 | **本包质量最高的一题**：gold 63/63、empty 的失败恰好等于 4 条 F2P、P2P 59 条、离线无外部资产。**有真实反例证明不强制唯一实现**（DeepSeek 改 `dataset.py:98` 调用点、gold 改 `transform.py:107` 默认值，都判 RESOLVED_FULL）。代价是**部分修复拿满分**：只修 `Dataset` 一处即可，另外 11 处 `apply_transform` 调用点（CacheDataset/IterableDataset/GridPatch/WSI/ImageDataset）仍忽略 lazy。题面整段重复两遍；题面复现引用的 `ref_avg152T1_LR.nii.gz` 不在仓库里（要从 GitHub Releases 下），离线跑不通 | ready_for_probe | 给 CacheDataset/IterableDataset 各补一条同形 lazy 日志断言，重放 DeepSeek 的单点修复确认它会失败 |
| MONAI-763 | F2P 是端到端整数像素和 `assert_allclose(np.sum(output_image), 33621)` 且**无 rtol**——等价于要求候选复刻 gold 的 slice 集合，题面（只说「不要有重复 slice」）完全预知不到。评分容器 **/dev/shm 不足**：`test_integration_segmentation_3d.py` 的 `DataLoader(num_workers=4)` 被 Bus error 杀掉（两侧一致，不计分但白烧时间）。该 shm 报错行 `ERROR: Unexpected bus error...` 被日志 parser 当成一条测试结果记进 status_map（伪条目 `{'Unexpected': 'ERROR:'}`）。题面承诺「给这个函数补单测」但 test_patch 里一条也没有 | needs_repair | 实现「事后 `dict.fromkeys` 去重」的替代解法跑 F2P，判定 33621 是否仍成立 |
| MONAI-2061 | 环境最廉价（离线 2.81s、分差精确到 2 条）。题面 252 字符纯 feature request。**P2P 只有两条 `assertRaises` 用例**：把条件直接写成 `if True:`（永远走逐样本 zip 路径）很可能满分——纯 tensor 输入被拆开再 `torch.cat` 回来，数值与 details 形状不变；形状不匹配用例在逐样本路径下照样抛异常。代价是丢掉批量路径。gold 用 `zip` 且未处理两侧长度不等 | needs_repair | 把条件改成 `if True:` 跑当前 F2P+P2P，预期 RESOLVED_FULL |
| MONAI-2446 | 题面质量好（复现 + 前后输出 + 一句话期望），gold 只加 `data = copy(data)`。**镜像 nibabel 已把 int64 数据从警告升级成 ValueError**，同文件 5 条 `test_shape_*` 两侧一致失败被挤出 P2P，有效回归只剩 2/8。F2P 只断言「原 list 不变」，不断言「内部确实被打乱」 | ready_for_probe | 降级 nibabel 后重跑，确认 5 条转 PASSED 并加回 P2P |
| MONAI-3403 | **P2P=0**。F2P 的新断言只查 `type(result1[0]) == type(result2[0])`（类型一致性，不查具体类型）→「统一返回 `torch.tensor`」也满分，而这会改变公开返回类型并传导到 `generate_pos_neg_label_crop_centers` / `generate_label_classes_crop_centers` 两个热路径。gold 还顺手把「就地改写调用方 centers」改成返回新列表，这一点零覆盖。另：测试形参名与实参顺序对调，**F2P 实际没有覆盖题面那组参数** | needs_repair | 写「统一返回 tensor 且保留就地改写」的假修复跑 F2P，预期满分 |
| MONAI-3547 | **P2P=0**。test_patch 往既有用例里插了一行 `torch.backends.disable_global_flags()`——**不可逆的进程级全局状态改写且不还原**；gold 的「永久解冻」副作用恰好抵消它，而题面 traceback 里 torch 自己推荐的 `flags()` 上下文管理器式修法不会抵消，**同一份测试对两种正确实现留下不同的进程状态**。本题还给出了 SKIPPED 记账问题的直接实证：`SKIPPED [1] tests/test_set_determinism.py:59` 被 parser 记成键 `[1]` | needs_repair | 把 `tests/test_set_determinism.py` 与任一会设 cudnn 标志的文件放同一条 pytest 命令跑，观察顺序依赖 |
| MONAI-3566 | **题面与 gold 方向相反**：题面要的是「默认就应带上 DICOM tag」（复现代码不传任何新参数），gold 做的是**默认关闭**的开关 `series_meta=False`，而 F2P 必须用 `series_meta=True` 这个题面里从未出现的名字调用——按题面字面实现的候选会因未知 kwarg 直接判 0。P2P 20 条里有 5 条来自 test_patch 顺手改的**无关文件** `tests/test_timedcall_dist.py`（multiprocessing spawn + 墙钟超时，上游自己在放宽 10s→20s）。另有 5 条 `RuntimeError: Unknown type: itkMatrixF44`（itk 版本漂移）。整题 46.29s，本包最慢 | needs_repair（不改题面则 reject_revision） | 让模型只看当前题面跑一次，统计是否会猜到 `series_meta` 这个名字（预期 0） |
| MONAI-3690 | 题本身干净（4/4、19s、分差精确、F2P/P2P 搭配合理，P2P 挡住了「run() 直接 return」）。两个流程性事项：(a) test_patch **新建** `tests/test_prepare_batch_default_dist.py`，同 2454 的恢复缺口；(b) **F2P 一半依赖 torch.distributed 2 进程**（`DistCall(nproc_per_node=2)`），`master_port` 是 `np.random.randint(10000,20000)` 且无冲突重试。与 MONAI-3715 紧邻，划分必须同侧。gold 的 warning 有拼写错 `is emply` | needs_review | 同机并发 6 个评分容器各跑 10 次，统计 dist 两条的失败率与端口冲突 |
| MONAI-3715 | 环境完全干净（4.75s、单进程、分差精确、题面带 traceback 指到行）。**但整份评分只有 2 条用例且都不覆盖 train 分支**：报告者要的是 `mode='train'`（为 SaliencyInferer），test_patch 加的却是 `mode='eval'`。把 `evaluator.py:117-123` 换成单行 `self.mode = eval_mode` 即可满分，而那恰好让 `mode='train'` 静默失效（比原来只报错更糟）。这是本包最干净的一个奖励漏洞反例 | needs_repair | 直接跑 `self.mode = eval_mode` 版假修复，预期 RESOLVED_FULL |
| MONAI-4109 | **本包质量最高的一题之二**：题面 3 行最小复现、gold 精确对应、离线 6s、P2P 54 条覆盖 `inch×dim×scale` 全组合，且 `test_script_save` 内部用 `convert_to_torchscript(verify=True, rtol=1e-4)` 做数值比对，难以被假修复骗过。唯一隐患：F2P 带 `@SkipIfBeforePyTorchVersion((1, 8, 1))`，一旦换到 torch<1.8.1 的环境就会被 skip → 在 status_map 里找不到 nodeid → 按缺席计失败 → **gold 假判 RESOLVED_NO** | ready_for_probe | 扫 216 题 F2P/P2P 的 skip 装饰器（已做，见下），在缺依赖环境跑一次 gold 验证假判 |

## 覆盖与统计

- 覆盖 **13/13** 题，全部落盘 `records/<instance_id>.json`（均为合法 JSON）。**未做清单：空**。
- 处置建议分布：`ready_for_probe` 3（2446、4109、6975）、`needs_review` 2（2454、3690）、`needs_repair` 8（763、1121、2061、3205、3403、3547、3566、3715）、`reject_revision` 0（3205 与 3566 各有一个「若某条件不满足则建议 reject」的条件分支）。
- `issues` 共 40 条：P1 20、P2 18、P3 2。逐项检查共填 229 格：`pass` 150、`issue` 78、`unknown` 1（MONAI-3205 的检查 16：未核实 Hippocampus 数据落地后的磁盘占用与 `skip_if_quick` 在评分环境是否生效）；带 `severity_hint` 的 issue 级检查 P1 29、P2 38、P3 11。
- 凡标 `pass` 的检查都附了具体 `commit:path:行号` 或日志路径；未做的检查写 `not_checked`，证据不足写 `unknown`。
- 成本：13 题合计 `costs.minutes` = 289 分钟（含跨题扫描）。

## 仓库级与跨仓库发现

以下七条不是单题问题。证据文件都在 `runs/env_overnight_20260916/L1_monai_1/`。

### 1. MONAI 的 F2P/P2P 是「整文件跑两遍取差集」，24/26 题可精确复算（`p2p_mechanism.txt`）

对全部 26 道 MONAI 题，用离线 stage1 的 gold/empty `status_map` 重算
`F2P = {gold 通过 且 base 不通过}`、`P2P = {两侧都通过}`，**24 题与官方名单逐条完全一致**。
这与 L1_mypy_1 报告的 mypy 机制（P2P 是 diff 邻接 + `-k` 子串过选的副产物、14/40 题为空）形成直接对照：**MONAI 的 P2P 是真的整文件回归基线，质量结构性地高于 mypy**。

两个例外恰好就是本包里两道离线阻断题：
- MONAI-1121：官方 P2P 比重算多 8 条（全是要下载 ResNet50 权重的用例）；
- MONAI-3205：官方 F2P 比重算多 1 条（唯一那条，要下载 Hippocampus）。

**由此得到一个现成的环境体检工具**：重算结果与官方名单的差集，**就是当前镜像/网络条件下已经跑不动的那些用例**。建议把这个对拍做成常规检查，在换镜像或换机器后跑一遍。

**附带核对的两项（`evalcmd_nontest_scan.txt`）**：
- 216 题的 `eval_cmd` 共 7 种，**按仓库完全一致**：MONAI 全 26 题是 `pytest -rA`（无 `-n0`、无 `-k`）；dvc 35 题同为 `pytest -rA`；moto/conan/modin 是 `pytest -n0 -rA`；dask 是 `pytest -n0 -rA  --color=no`；pydantic 是 `pytest -rA --tb=short -vv -o console_output_style=classic --no-header`；pandas 是 `pytest -rA --tb=long`；mypy 是 `pytest -n0 -rA -k`（34 题）与 `pytest -rA -k`（6 题）。MONAI 虽然没有 `-n0`，但**仓库里没有任何 pytest 配置也没有 conftest.py**（已核对 `5b91f9372`/`392c5c1b8` 的 `setup.cfg` 无 `[tool:pytest]`/`addopts`，`requirements-dev.txt` 不含 pytest-xdist），所以不会出现 mypy 那种被 `addopts = -nauto` 拉进 xdist 的情况——MONAI 是单进程原生 pytest。
- `test_patch` 里含**非 `test_*` 文件**的共 11 题：本包的 `MONAI-1121`（`tests/utils.py`）与 `MONAI-3690`（`tests/min_tests.py`），另有 moto 6 题、dvc 2 题、mypy 1 题（`mypy/test/teststubgen.py`）。这些路径都会被恢复覆盖；MONAI 的两个还会被当作 pytest 目标直接传入（`tests/utils.py` 因此产生了 `::test_script_save` 的误收集 ERROR）。

### 2. 日志 parser 会把**任意**以 FAILED/PASSED/SKIPPED/ERROR/XFAIL 开头的行记成测试结果（`bogus_statusmap.txt`）

`rh2/src/repoharness2/envpack/swegym_parsers.py:47-58` 的 `parse_log_pytest`：
```python
if any([line.startswith(x) for x in TEST_STATUS_VALUES]):
    test_case = line.split()
    test_status_map[test_case[1]] = test_case[0]
```
第二个 token 不做 nodeid 校验。扫描 181 个有 gold 日志的题：**54 题已经产生了伪条目**，例如
`iterative__dvc-*` 的 35 题有 `{'Could': 'ERROR:'}`（dvc 自己打印的 `ERROR: Could not ...`）、
`pandas-dev__pandas-*` 的 `{"pip's": 'ERROR:'}`、本包 MONAI-763 的 `{'Unexpected': 'ERROR:'}`（shm Bus error 提示行）。

当前这些伪键都不与真实 nodeid 相撞，所以**没有已知的判分错误**。但它证明**被测程序的输出会直接进入 status_map**。
由于同键后写覆盖先写，而 pytest 的 short summary 在运行末尾打印，一条注入要生效必须出现在 summary **之后**——`atexit` 钩子或 teardown 之后直接写 fd 1 都满足这个条件。
**建议在消费侧加约束**：只接受形如 `<path>::<...>` 且落在 `F2P ∪ P2P` 名单内的键，其余一律丢弃并记诊断。这是低成本、跨仓库生效的加固。

### 3. 被 skip 的 F2P/P2P 用例会被静默计为失败（`skipscan.txt`）

pytest `-rA` 的 SKIPPED 摘要行格式是 `SKIPPED [n] 文件:行号: 原因`，**不含 nodeid**；parser 只能记下键 `[n]`（本包 MONAI-3547 有直接实证，全库 16 题出现过 `[1]`）。
于是名单里的用例一旦被 skip，就在 status_map 里找不到自己的 nodeid，被 `get_eval_tests_report` 当作**缺席 → 失败**。
`scoring.py:199-201` 注释里写的「SKIPPED 不进桶」这条分支，在 pytest `-rA` 下**永远触发不了**。

静态扫描 216 题（只看装饰器文本，不判断条件是否成立）：**22 题的 F2P/P2P 用例带 skip 类装饰器，其中 5 题的 F2P 受影响**：
- `getmoto__moto-7105`：3 条 F2P 带 `@requires_docker`（Docker-in-Docker）；
- `Project-MONAI__MONAI-4925`：F2P 带 `@SkipIfNoModule("torchvision")` 与 `@SkipIfNoModule("ignite")`；
- `Project-MONAI__MONAI-4159`：F2P 带 `@skip_if_windows`（Linux 下良性）；
- `Project-MONAI__MONAI-3205`：F2P 带 `@skip_if_quick`（取决于 QUICKTEST 环境变量）；
- `conan-io__conan-12397`：F2P 带 Py2 skipif（良性）。
另有 2 题是 **test_patch 新增**的 skip 装饰器（base 扫不到）：`Project-MONAI__MONAI-4109` 的 `@SkipIfBeforePyTorchVersion((1, 8, 1))`、`getmoto__moto-7105` 的 `@requires_docker`。

风险形态很具体：**换一台缺 GPU / 缺某个可选依赖 / 未装 Docker 的机器，gold 会被判 RESOLVED_NO，而日志里看不出是 skip 还是 fail**。

### 4. `test_patch` 新建测试文件时，恢复机制有缺口（`newfile_scan.txt`）

`rh2/src/repoharness2/adapters/slime/prepared_task_face.py:199-210` 的恢复步骤是
`if git cat-file -e <base>:"$f"; then git checkout <base> -- "$f"; fi`——**base 里不存在的 official test 路径直接跳过**，随后 `git apply` official test_patch。
若候选在同一路径上写了自己的文件，`new file mode` hunk 就冲突失败，`sandbox_profile.py:1289` 随即 `exit 3`，整题按 `official_test_patch_apply_failed` 判 0，**候选的源码修复即使完全正确也拿不到分**。

216 题里 test_patch 含 `new file mode` 的共 **8 道**：`MONAI-2454`、`MONAI-3690`（本包）、`conan-11594`、`moto-5885`、`moto-7607`、`dvc-3665`、`dvc-6954`、`mypy-15184`；删除/改名 0 道。
这不是假设：**MONAI-2454 的真实 DeepSeek 轨迹就在 `tests/test_to_tensor.py` 上撞了名**（`runs/env_probe_20260909_final_sync/ledger/logs_cc/Project-MONAI__MONAI-2454/candidate.diff`；既有审查 `solvability_review_20260909/02_oracle_cases.md:15` 已记过这个现象）。而「先写一个复现测试」正是 agent 最自然的行为之一。
建议修法：对「base 不存在但 official test_patch 要新建」的路径显式 `rm -f` 再 apply（语义上就是「恢复到 base 的不存在状态」），apply 成功后 `RH2_SETUP_ABSENT_TEST_FILES` 仍为 0，不与 §10.2 的「缺失即拒」冲突。

### 5. 这批 MONAI 镜像没有把依赖钉到对应年代，已吃掉多题的回归覆盖

本包 13 题里有 3 题被依赖漂移削掉了 P2P（都是两侧一致失败、因而被排除出名单，**不影响判分，只影响回归强度**）：
- MONAI-1121（v0.3）：`np.int` 已从 numpy 移除 → `monai/networks/nets/regressor.py:81` 崩，4 条 test_discriminator 失效；
- MONAI-2446（v0.5）：nibabel 把 int64 数据从警告升级成 `ValueError` → 5 条 `test_shape_*` 失效，**有效 P2P 从 7 条降到 2 条**；
- MONAI-3566（v0.8）：`RuntimeError: Unknown type: itkMatrixF44` → 5 条 test_load_image 失效。
这三条与结论 1 的对拍工具互为印证：差集就是漂移代价。修镜像依赖能直接把这些回归加回来，是性价比最高的一项环境修复。

### 6. MONAI 里必须同侧划分的题对（`dupidx.txt`）

按「共用 gold 文件或共用 test 文件」取连通分量，26 题里有 5 组需要同侧：
- **`MONAI-3690` ↔ `MONAI-3715`（两题都在本包）**：共用 `tests/test_prepare_batch_default.py`；3715 的 base（2022-01-26）晚于 3690（2022-01-20），**3715 的唯一 P2P 就是 3690 新增的那条用例**，3715 的 base 里能直接读到 3690 的参考解；
- `MONAI-763` ↔ `MONAI-907`：共用 `tests/test_sliding_window_inference.py`，907 的 base 已含 763 的 gold；
- `MONAI-5932` ↔ `MONAI-6756`：共用 `monai/bundle/reference_resolver.py` + `tests/test_config_parser.py`；
- `MONAI-4676` ↔ `MONAI-6523`：共用 `monai/data/meta_tensor.py` + `tests/test_meta_tensor.py`；
- `MONAI-5686` ↔ `MONAI-5908`：共用 `monai/losses/ssim_loss.py` + `tests/test_ssim_loss.py`；
- 另：`MONAI-763` ↔ `MONAI-4688` 共用 `monai/data/utils.py`（不同函数）。

另外两项材料卫生（`monai_extra_scans.txt`）：
- **problem_statement 整段重复两遍**：MONAI 里 3 题（`4775`、`6523`、`6975`），其中 `6975` 在本包。与 L1_mypy_1 报告的 mypy-11352、dvc-4785、mypy-17071 是同一类加工缺陷。
- **`test_script_save` helper 被 pytest 误收集**：MONAI 用 `from tests.utils import test_script_save` 把一个 `test_` 开头的辅助函数引进模块命名空间，pytest 当用例收集并报 `fixture 'net' not found`。本包 MONAI-1121 产生 6 条、MONAI-4109 产生 1 条，另有 MONAI-6775（L1_monai_2 的题）1 条。不在名单里所以不影响判分，但会让「rc≠0 即失败」「有 ERROR 即失败」这类粗粒度判据误判整题。

### 7. 候选新建/改写的 conftest.py 既不被剔除也不被恢复；MONAI 的 26 个 base 里一个 conftest.py 都没有（`conftest_scan.txt`）

三条已核对的代码事实：
- `rh2/src/repoharness2/grading/manager.py:672` 构造 SWE spec 时 `test_globs=()`，注释写明「P-B：不再按测试名通配剔除候选改动」——候选改动里的 `tests/conftest.py` **不会被投影剔除**，会随 `cleaned.patch` 落进评分树（`manager.py:2592` 的 `git apply`）；
- `rh2/src/repoharness2/grading/manager.py:566-577` 对 conftest / fixture / pytest 配置类路径**只做观测**（写进 sidecar 的 `candidate_touched_conftest_or_fixture`），不改判定、不剔除；
- `rh2/src/repoharness2/grading/trusted_projection.py:18-20` 已把这件事登记为「已知不足（登记不修），等 taskset 定后由 environment adapter 声明通用控制面」。

本轮新增的是**暴露形状**。逐题（而非逐仓库）核对 base commit 下是否存在任何 `conftest.py`：
**`Project-MONAI/MONAI` 26/26 个 base 下一个都没有**；`iterative/dvc` 4/35；其余七个仓库每个 base 都至少有一个（moto 0/59、mypy 0/40、pydantic 0/20、dask 0/14、conan 0/12、modin 0/5、pandas 0/5，pandas 单个 base 下多达 26~27 个）。
所以 **MONAI 是暴露面最干净的仓库**：候选新建的 `tests/conftest.py` 是一个全新路径，
恢复步骤不会碰它（它不在 `hygiene.test_files` 里），`git apply` 也不会冲突，而 pytest 在
`pytest -rA tests/test_x.py` 下会自动加载同目录的 `tests/conftest.py`。
**需要强调**：在已有 conftest.py 的仓库里这个洞同样存在——候选**改写**既有 conftest.py 一样不会被剔除也不会被恢复（它通常不在 test_patch 里），只是要处理与既有内容的合并。MONAI 只是最省事的那一种。
最小利用形状是一个 `pytest_runtest_makereport` 的 hookwrapper，把每条用例的 `rep.outcome` 改写成 `"passed"`，
`-rA` 摘要随即对每条打出 `PASSED <nodeid>`，parser 照单全收 → RESOLVED_FULL。

**这一条我只做了静态核对，没有实跑验证**（本包不允许起 Docker）。但每一环都有代码出处，而且 MONAI 恰好是「无 conftest、无 pytest 配置、无 addopts」的最干净形状（已核对 `5b91f9372` 与 `392c5c1b8` 两个 base：`ls-tree -r | grep -c conftest` 均为 0，`setup.cfg` 无 `[tool:pytest]`/`addopts`，`requirements-dev.txt` 不含 pytest-xdist；所以 MONAI 的评分是单进程原生 pytest，没有 mypy 那种 `addopts = -nauto` 的并行问题）。
**建议的下一实验**：在 MONAI-2061（离线 2.81s，最廉价）上构造一个只含上述 hookwrapper 的 `tests/conftest.py` 作为候选 patch，走完整评分流程，看是否判 RESOLVED_FULL。这是本次审查里**最值得优先验证**的一条。

## 最值得用户裁定的 3 个问题

1. **要不要给评分镜像补下载资产与 shm？涉及本包 3 题，其中 2 题现在完全不可用。**
   MONAI-1121 需要预置 torchvision `resnet50-0676ba61.pth`（约 100MB），否则 gold 与 no-op 零分差；MONAI-3205 需要预置 Decathlon `Task04_Hippocampus.tar`（体积待量，可能数百 MB），否则唯一的 F2P 在 gold 侧也失败；MONAI-763 需要 `--shm-size=2g`（或去掉最慢的那个不计分文件）。
   三者的代价差别很大：shm 是一行容器参数；ResNet50 权重可接受；Hippocampus 数据集可能不可接受。
   **是按题预置资产、按题剔除下载型用例、还是把这两题整体 reject？**

2. **「题面与评分方向不一致」的题怎么处置？本包命中 4 道，形态各不相同。**
   - `MONAI-3566`：题面要「默认带上 DICOM tag」，gold 做的是默认关闭的开关，且开关名 `series_meta` 不可推断——按题面字面实现必判 0；
   - `MONAI-1121`：题面字面要求「补单测」，而规则明令禁改测试，真正要改的文件题面零线索；
   - `MONAI-3205`：题面是论坛提问，不含任何 API 规格；
   - `MONAI-2454`：题面只说 numpy 0 维，F2P 要求 Python 标量也保形（已有真实候选因此判 0）。
   我的建议是 3566/3205 改题面或剔除、1121 改写成缺陷式描述、2454 补一句话，但这属于数据集取舍，需要用户拍板：**是补题面、放宽 F2P、还是直接剔除？**

3. **三条评分机制问题要不要现在修？它们都超出 MONAI，影响全部 216 题。**
   (a) **候选新建/改写的 conftest.py 不被剔除也不被恢复**（`test_globs=()`，只观测不拦截；`trusted_projection.py:18-20` 已登记为「登记不修」）。MONAI 的 26 个 base 里连一个 conftest.py 都没有（dvc 另有 4/35），新建即生效；一个 `pytest_runtest_makereport` hookwrapper 就能把全部用例改写成 PASSED。这个洞在有 conftest 的仓库同样存在，只是要合并既有内容。**这是我看到的最大奖励漏洞，建议优先做一次实跑验证**（在 MONAI-2061 上，2.81s）。
   (b) **SKIPPED 记账**：pytest `-rA` 的 skip 摘要行不含 nodeid，名单里的 skip 会被当缺席计失败；22 题的名单里有 skip 装饰器，5 题的 **F2P** 直接受影响（含 `moto-7105` 的 `@requires_docker`）。换机器就可能让 gold 假判 RESOLVED_NO，且日志上看不出来。
   (c) **status_map 键无校验**：被测程序的任意输出会进 status_map，54/181 题已经在产生伪条目。当前无判分错误，但这是一个候选可控的注入面。
   (b)(c) 的修法都不大（前者换一条能拿逐 nodeid 结果的通道，后者在消费侧按「必须是 nodeid 且在名单内」过滤）；(a) 需要决定控制面规则怎么声明。**问题是要不要在本轮训练前改评分口径**——改了之后历史 evidence 的可比性会变。
