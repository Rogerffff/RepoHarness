# L1_monai_2 · 逐题静态审查小结

范围：Project-MONAI/MONAI 13 题（ASSIGNMENT.json 顺序）。方法：先只看 `problem_statement` + base 代码写 `public_view`，再读 `test_patch` / `fail_to_pass` / `pass_to_pass` / `golden_patch` / `hints_text`。
base 代码用裸克隆 `git show <base>:<path>` / `git grep <base>` 读取（COMMON.md 允许的只读操作），未建 worktree、未起 Docker、未实跑测试、未调用模型 API。
逐题记录：`records/<instance_id>.json`。辅助产物在 `runs/env_overnight_20260916/L1_monai_2/`：`mat/<id>/{public,grading,validation,raw,envpkg}.json`（四面材料抽取）、`scan/prescan.json`、`scan/monai_cross_index.txt`（26 道 MONAI 题的 base/test/gold 交叉索引与同族分组）。
脚本：`scripts/{extract.py,prescan.py,show.py}`。

| task | 主要发现 | 建议处置 | 下一实验 |
| --- | --- | --- | --- |
| MONAI-4159 | **题面与评分完全不对应**：题面要求 `ckpt_export` 新增 `--bundle_path/--out_path` 自动发现 bundle 目录，gold 实现的却是「把 TorchScript 的 `more_extra_files` 从单键 `config` 改成按配置文件名分键」，题面一个字都没提 extra_files；**P2P=0**（零回归保护），而 gold 是导出产物布局的不兼容改动；F2P 只查「某键存在」，把合并后的整份配置写进每个键也能满分 | needs_repair | 用 `{basename(i): json.dumps(parser.get())}`（每键写合并配置）的假修复跑 F2P，预期 2/2 通过 |
| MONAI-4583 | 题面自带最小复现且 F2P 第一条逐字等于它，gold 6 行干净、不强制唯一实现——本包质量最好的题之一。缺口：gold 同时改了 3D 分支但 **F2P 全是 2D**，唯一的 3D 回归 `test_value_3d_mask` 用矩形掩码（左上角必是前景），对 3D 修法零判别力 → 只修 2D 的部分修复可满分。另：F2P 的 `_0.._3` 位置 ID 建立在 `TEST_NDARRAYS` 上，而 tests/utils.py:716-719 在有 CUDA 时把它整个重赋值（np.array 被挤掉） | ready_for_probe | 写只改 2D 分支的部分修复跑当前 F2P+P2P，预期 RESOLVED_FULL |
| MONAI-4676 | 题面只给 `np.sum(MetaTensor(1.0))` 一个例子，F2P 却要求 `np.linalg.qr`/`np.concatenate`/`np.argwhere` 与 ufunc 比较全部工作（NEP-18 通用实现可一并覆盖，属线索不足非不可解）。**P2P=71 条 = 整文件通过集**，回归保护是本包最强的一档；代价是 **12 条 P2P 依赖多进程 DataLoader(num_workers=5) 与 ForkingPickler**，Docker 默认 64m shm 会把资源不足伪装成 P2P 失败（MONAI-763 同型）。另发现 parser 把 `SKIPPED [6] file:line` 解析成伪键 `[6]`，8 条真正跳过的 nodeid 从 status_map 消失 | ready_for_probe | 同镜像 `--shm-size=64m` vs `1g` 各跑一次整文件，对比 test_dataloader_*/test_multiprocessing_* 状态 |
| MONAI-4688 | **整个评分面只有 2 个用例**（F2P=1、P2P=1，测试文件总共就 2 个 test）。题面 traceback 真正崩的是 `decollate_batch`，而测试完全不调用 decollate；gold 只在 `collate_meta_tensor` 里加 `(tuple,list)` 分支，这个分支插在 `default_collate` 之前，会**抢走 torch 对 namedtuple 的特判**（保留字段名 → 退化成普通 list），零覆盖。另：`assertTrue(label.is_batch, True)` 是 assertTrue 误用（第二实参是 msg） | needs_repair | 在 base/gold 各跑 tests/test_decollate.py + test_dataloader.py + test_image_dataset.py，取双侧通过集补 P2P |
| MONAI-4775 | **题面整段重复两遍**（2152 字符 = 1076×2），且题面 Additional context **直接给出修复代码**（`q = torch.tensor(q, device=x.device, dtype=x.dtype)`，与 gold 的 `convert_to_dst_type(q/100.0, x)[0]` 等价）→ 区分度极低。F2P 的判别力依赖 `TEST_NDARRAYS` 的元素顺序（CPU 机上 idx0=numpy、idx1=torch；有 CUDA 时 numpy 分支被挤掉，退化成两个 torch 结果互比）。P2P=11 条 = 整文件其余用例，回归方向正确 | ready_for_probe | 删掉题面 'A possible solution' 段后再盲解一次，与完整题面对比通过率 |
| MONAI-4925 | **要求不可推断 + 精确字符串锁死实现**：题面只有一句「打印时不要显示空字典」、零样例输出，F2P 却逐字断言 `repr(eo) == "{'weights': 122, 'optim': 2, 'metrics': 1, 'weight_type': fl_weight_diff, 'statistics': 1}"`——其中 122 是 torchvision 0.14.1 下 `resnet18().state_dict()` 的条目数、2 是该 torch 版本 `Adam.state_dict()` 的键数，连键顺序都锁死。反向也成立：只凑这一个字符串即可满分，`summary()` 继续返回 `dir(self)` 也不影响。另：整类被 `@SkipIfNoModule("torchvision")+("ignite")` 守卫，依赖缺失时 5 条参考全部 SKIPPED → 因 parser 丢 nodeid 而变成「缺席计失败」，失败原因不可见。gold 自带死代码 `self._summary.update(self)` 且 `_summary` 跨调用累积。**确认不下载权重**（resnet18 无 pretrained，stage1 日志无 Downloading 行） | reject_revision | 让 3 个独立求解上下文各实现一次，统计逐字命中该字符串的次数（预期 0） |
| MONAI-5686 | 题面自带 8 行可运行复现、F2P 逐字搬运、P2P=8 条有数值判别力（挡得住「返回带梯度的常量」），质量较好。缺口三条：gold 同时改了 `x.shape[0]>1` 分支但**全部用例 batch=1 → 该分支零覆盖**；参数表 `[None,"cpu","cuda"] if cuda else [None,"cpu"]` 让条目数随机器画像变化；CPU 上 `y.to(None)` 与 `y.to("cpu")` 是同一对象，**test_grad_0 与 test_grad_1 完全等价**。gold 用私有方法 `._compute_tensor` 绕过 `Metric.__call__` 的 detach，是过渡修法（7 周后被 5908 重写） | ready_for_probe（须与 5908 同侧划分） | 写只改 `x.shape[0]==1` 分支的部分修复跑 F2P+P2P，预期 RESOLVED_FULL |
| MONAI-5908 | **本包评分设计最健康的一题**：F2P 10 条覆盖 2D/3D/梯度三类 × batch=16，P2P 20 条覆盖 batch=1/2 全部组合并含 5686 引入的梯度用例，数值断言有 1.0 与 0.0 两个方向，挡得住返回常量的假修复。静态推理确认 base 只在 **batch≥3** 才炸（i=2 时 `ssim_value.view(1)` 对 2 元素张量抛 RuntimeError），与 F2P 全是 batch=16 一致。本题 base 已含 5686 的 gold、P2P 含 5686 的新用例 → 两题顺序依赖必须同侧。`test2d_04` 的两位零填充是 `parameterized` 按 `len(str(n-1))` 定位宽的直接证据 | ready_for_probe（须与 5686 同侧划分） | 补一条 batch=3 的最小失败点用例，确认它在 base 失败、gold 通过 |
| MONAI-5932 | 题面质量本包前列：完整 traceback 直接暴露错误中间产物 `__local_refs['training#num_epochs']_per_validation`，根因（引用按子串替换）一目了然；gold 只加一行 `result.sort(key=len, reverse=True)`；P2P=14 条 = 整文件其余用例，对替换逻辑有实质判别力。缺口：F2P 只有一个两级前缀用例（三级以上、非表达式分支未覆盖）；P2P 成员 `test_parse_0` 被 `@skipUnless(has_tv)` 守卫，torchvision 缺失时会 SKIPPED→缺席→计失败且原因不可见。与 6756 同文件同测试、6756 的 base 已含本题 gold → 必须同侧 | ready_for_probe（须与 6756 同侧划分） | 构造三级同前缀引用 `$@a#b + @a#b_c + @a#b_c_d` 在 base/gold 各跑一次 |
| MONAI-6523 | **题面 17804 字符、前后两半逐字重复**，去重后仍有 8902 字符且约 6000 字符是不可运行的 PyTorch Lightning 管线草稿（`from ... import MyDataModule`）；真正有用的信息只占前 2000 字符。gold 六行（新增 `__format__`）、P2P=85 条 = 整文件通过集，质量好。**本包最重的机器画像风险**：`TESTS = TEST_DEVICES × DTYPES` 在 CPU 上是 6 项（一位序号），有 CUDA 时变 12 项 → `parameterized` 序号位宽从 1 位变 2 位 → 72 条一位数参考 ID 全部 MISSING → 按缺席计失败，gold 也拿 0。另 12 条 P2P 依赖多进程 DataLoader/shm | ready_for_probe（须固定无 CUDA + 记 shm） | 同镜像 CUDA 可见/不可见各 `pytest --collect-only -q`，对比 `test_add_*` 是 `_0..5` 还是 `_00..11` |
| MONAI-6756 | **唯一的 F2P `test_parse_0` 被 `@skipUnless(has_tv, "Requires torchvision >= 0.8.0.")` 守卫**：torchvision 缺失即 SKIPPED → 因 parser 丢 nodeid 而缺席 → 按「缺席计失败」无条件判 0，且日志里只有 `SKIPPED [n] file:line` 无法归因。**本包最慢的一题（72.5s，第二名 22.5s）**：test_patch 把 cldice 的 TEST_CASES 从 `(100,3,256,256)` 缩到 `(7,3,11,10)`，却**漏掉了同文件的 `test_with_cuda`**（仍是两个 78.6 MB 张量、无 skip 守卫、CUDA 不可用时照样在 CPU 上跑多轮软骨架化），而它是 P2P 成员 → OOM/超时会被记成候选弄坏了东西。test_patch 还打包了与 gold 无关的 cldice 性能改动；gold 含一处纯风格重构 | needs_review | 单独跑 `test_with_cuda` 记墙钟与峰值 RSS；再屏蔽 torchvision 跑一次确认 verdict 变 0 且原因不可见 |
| MONAI-6775 | **决定性要求只在不可见 hints 里**：题面（654 字符）只说类别权重 w 被约掉、引 NiftyNet「先求和再相除」，而 hints 逐字给出目标代码 `(intersection * w).sum(final_reduce_dim, keepdim=True)` 并给出关键裁定「GDL cannot generate [C] output」——后者是 gold 把 `reduction="none"` 输出从 (2,2,1) 改成 (2,1,1) 的唯一依据。**题面真正抱怨的 `batch=True` 情形零数值覆盖**：12 个 TEST_CASES 一个都没开 batch=True，唯一的 `test_batch` 只查 `grad_fn is not None`。F2P 要求 6 个新期望值在 rtol=1e-5 下逐个命中。另：`from tests.utils import test_script_save` 被 pytest 当测试收集并 ERROR，**gold 侧 test 段 rc 也是 1**（本包唯一） | needs_repair | 只按题面字面实现（仅 batch=True 时求和）跑 F2P，预期大面积失败；并补 batch=True 数值用例 |
| MONAI-907 | 题面短（531 字符）但信息密度高：直接给出 `scan_interval=(72,72,0)` 这个中间量与 `len(slices)=30` 的症状，F2P 的 `roi_shape=(4,1,7)` 是题面 (M,N,1) 的同型最小化；P2P=9 条 = 整文件通过集，覆盖 2D/3D、constant/gaussian、overlap 0.25/0.5。缺口：gold 除了给 interval 加下界，还把两个 `assert` 改成 `raise ValueError`（对外异常类型变更），**零覆盖**；F2P 只验 `roi=1, overlap=0.25` 一个组合。另：`test_sliding_window_default_8` 用 `cuda:0` 但体内有降级分支，在 CPU 机上与 _7 完全等价 | ready_for_probe | 用 `_get_scan_interval` 维度不匹配的输入在 base/gold 各调一次，比较异常类型（AssertionError vs ValueError） |

## 覆盖与统计

- 覆盖 **13/13** 题，全部落盘 `records/<instance_id>.json`（均为合法 JSON）。**未做清单：空**。
- 处置建议分布：`ready_for_probe` 8（4583、4676、4775、5686、5908、5932、6523、907）、`needs_repair` 3（4159、4688、6775）、`needs_review` 1（6756）、`reject_revision` 1（4925）。
- 检查状态：`pass` 168、`issue` 68、`unknown` 2（4676 的 check 25、4159 的 check 13），未做的检查按 COMMON.md 留空而非记 pass。
- 记录 issue 数：P1 16 条、P2 27 条、P3 12 条。
- 方法与限制：**全部为静态审查**——未启动 Docker、未实跑任何测试、未调用模型 API、未连接任何远程机器。base 代码用裸克隆的 `git show <base>:<path>` / `git grep` / `git ls-tree` 读取（COMMON.md 允许的只读操作），未建 worktree。凡标 `pass` 的检查都附了文件行号或 stage1 日志路径。
- 辅助产物（`runs/env_overnight_20260916/L1_monai_2/`）：
  `scan/prescan.json`（四面材料 + stage1 对账）、`scan/envscan.txt`（13 题测试文件的下载/网络/GPU/多进程/大张量静态扫描）、
  `scan/p2p_mechanism.txt`（P2P 生成机制核查）、`scan/param_id_width.txt`（parameterized 序号位宽 × CUDA 画像）、
  `scan/parser_skipped.txt`（SKIPPED 行 parser 键错位证据）、`scan/control_surface.txt`（test_patch 之外的测试依赖）、
  `scan/leak_and_ps_quality.txt`（gold 行泄漏与题面重复扫描）、`scan/monai_cross_index.txt`（26 道 MONAI 题交叉索引）、
  `mat/<id>/{public,grading,validation,raw,envpkg}.json`。

## 仓库级（跨题）发现

以下六条不是单题问题，证据文件都在 `runs/env_overnight_20260916/L1_monai_2/scan/`。

1. **MONAI 的评分口径是「整文件跑」，参考清单是它的直接产物。**（`p2p_mechanism.txt`）
   13/13 题的 `eval_cmd` 都是 `pytest -rA <test_patch 触碰的全部测试文件>`（**没有 `-k`、没有选择器**），
   且 13/13 题满足 `P2P == (gold 侧整文件 PASSED 集) − F2P`。
   与 mypy 包发现的「`-k` 子串过选副产物、14/40 题 P2P 为空」正好相反：MONAI 的 P2P 通常很大（最大 6523 的 85 条）、
   回归保护强。代价有两个：(a) 每次评分都要跑完整个文件，包括与本题无关的慢用例（6756 的 `test_with_cuda` 单条就占了 72.5s 里的大部分）；
   (b) 文件里任何一条用例的环境脆弱性都会变成本题的判分脆弱性。
   例外：**4159 的 P2P 为 0**，因为它的测试文件总共只有 2 个用例且都是 F2P。

2. **参考 ID 是 `parameterized` 的位置序号，位宽随参数表长度跳变，而参数表长度依赖 `torch.cuda.is_available()`。**（`param_id_width.txt`）
   `parameterized.expand` 的序号位宽 `digits = len(str(n-1))`，本包内有直接实证：907 的 10 项参数 → `..._9`（一位），
   5908/6775 的 12 项参数 → `test2d_04`/`test_shape_04`（两位）。
   而 `tests/utils.py:730-732` 的 `TEST_DEVICES` 在有 CUDA 时从 1 项变 2 项。
   于是 **4676 与 6523** 的 `TESTS = TEST_DEVICES × DTYPES(6)` 会从 6 项变 12 项，序号从 `test_add_0` 变成 `test_add_00`：
   在有 GPU 的机器上评分时，这两题的 77/86 条参考 ID 里各有 72 条会 MISSING，按 `scoring.py` 的「缺席计失败」口径 **gold 也拿 0**。
   另有 4583/4775/5686/5908 的参数表长度或元素含义随 CUDA 变化但不跨位宽，表现为「同一个 ID 在两类机器上验的不是同一件事」。
   特别地，`tests/utils.py:716-719` 在有 CUDA 时把 `TEST_NDARRAYS` **整体重赋值**为 `TEST_TORCH_TENSORS + (gpu_tensor,)`，
   `np.array` 被挤掉——这是 MONAI 自己的测试基建 bug，后果是 4583/4775 的 numpy 分支在 GPU 机上完全不被跑。

3. **pytest `-rA` 的 SKIPPED 摘要行不含 nodeid，parser 产出伪键并吞掉被跳过用例的身份。**（`parser_skipped.txt`）
   `swegym_parsers.py:47-58` 的 `parse_log_pytest` 取 `line.split()[1]`；而跳过摘要形如
   `SKIPPED [6] .../unittest/case.py:118: Skipping CUDA-based tests`，第二个 token 是 `[6]`。
   实证：4676 与 6523 的 gold 日志摘要写 `8 skipped`，status_map 里却只多出两个伪键 `[1]` 与 `[6]`，8 条 nodeid 全部消失。
   当前不影响判分（这 8 条不在参考清单内），但 `EvalVerdict.reference_skipped` 对 pytest 仓库**恒为空**，是失效字段；
   而且一旦某条参考在评分机上被 SKIP，它会落进 `reference_missing` 按失败计，日志里唯一线索是一行不含 nodeid 的摘要。
   本包最直接的暴露面：**6756 的唯一 F2P `test_parse_0` 被 `@skipUnless(has_tv, "Requires torchvision >= 0.8.0.")` 守卫**；
   4925 整个测试类被 `@SkipIfNoModule("torchvision")` + `("ignite")` 守卫（5 条参考全覆盖）；5932 的 P2P 同样含 has_tv / has_yaml 守卫的用例。

4. **test_patch 只恢复它自己触碰的文件，`tests/utils.py` 留在候选手里。**（`control_surface.txt`）
   stage1 的 eval.sh 只做 `git checkout <base> <test_patch 路径>` 再 apply。本包 13 题没有一题的 test_patch 含 `tests/utils.py`，
   但其中 9 题的测试从它 import helper。**最强暴露是 `assert_allclose`**（4583 的 4 条 F2P、4676、4775、6523 的断言全部经过它）：
   候选把它改成空函数即可让相关 F2P 通过。其次是 6775 的 `test_script_save`。
   base 里也没有 `tests/conftest.py`，候选可新建一个注入 hook（`pytest -rA tests/xxx.py` 从 /testbed 运行会自动加载）。
   注意反面证据：同仓库的 **MONAI-1121 的上游 test_patch 本身就修改了 tests/utils.py**，所以不能对 MONAI 全仓一刀切永久排除该文件，只能按题判断。
   我在 4583/4676/4775/6523/6775 的 `file_rules.additional_exclusions` 里写了 `["tests/utils.py"]` 作为**建议**并给了理由；其余 8 题保持 `[]`。

5. **多进程与大张量是被低估的资源面。**（`envscan.txt`）
   4676 与 6523 各有 **12 条 P2P**（`test_dataloader_0..5` + `test_multiprocessing_0..5`）依赖 `DataLoader(num_workers=5)` 与
   `ForkingPickler`/`torch.multiprocessing`，即 /dev/shm；5932 与 6756 的 `test_pdb` 走 `TimedCall` spawn 子进程。
   6756 的 P2P `test_with_cuda` 在 CUDA 不可用时**不跳过**，照样在 CPU 上对两个 `torch.ones((100,3,256,256))`（各约 78.6 MB）
   跑多轮软骨架化——上游 PR 把同文件的 TEST_CASES 缩小了却漏了它，它单条主导了本包最慢的 72.5s。
   这些失败一旦发生都会被记成「P2P 失败 = 候选弄坏了东西」，正是已批反例 MONAI-763 要区分的情形。

6. **题面质量：两题整段重复，一题题面与 gold 完全不对应，两题的决定性信息在题面之外。**（`leak_and_ps_quality.txt`）
   - 整段重复：**4775**（2152 = 1076×2）与 **6523**（17804 = 8902×2），与 mypy 包在 216 题里扫出的 6 题同型。
   - **4159 的题面与 gold 完全不是一回事**：题面要 `--bundle_path/--out_path`，gold 改的是 TorchScript extra_files 的键名约定。
   - **6775 的决定性信息只在不可见的 hints 里**（逐字给出目标代码，且给出「GDL cannot generate [C] output」这条裁定）；
     **4775 的题面反过来直接给出修复方案**（`q = torch.tensor(q, device=x.device, dtype=x.dtype)`，与 gold 语义等价但不逐字相同，
     所以逐行匹配的泄漏扫描没命中，需要人工确认）。
   - **4925 的题面只有一句「打印时不要显示空字典」，F2P 却逐字断言一个含 torchvision/torch 内部条目数的字符串**，是本包唯一的 `reject_revision`。

## 最值得用户裁定的 3 个问题

1. **评分机的 CUDA 画像要不要写成硬约束？** 现在参考清单是在无 CUDA 的机器上生成的，4676/6523 在有 GPU 的机器上会整体失配并把 gold 判 0。
   选项：(a) 规定评分容器一律 `CUDA_VISIBLE_DEVICES=""`；(b) 评分前用 `pytest --collect-only` 做一次 ID 一致性校验，失配判 environment；(c) 两者都做。
2. **`tests/utils.py` 这类「被参考测试 import 但不在 test_patch 里」的文件，按题排除还是全仓排除？**
   本包 9 题有暴露、其中 5 题是强暴露（`assert_allclose` 直接承载 F2P 断言）；但 MONAI-1121 的上游 test_patch 又确实修改了该文件，
   一刀切会破坏那一题。需要一个「按题计算恢复闭包」的口径，还是只做「报告候选改动了哪些非恢复测试文件」的观测？
3. **题面与 gold 不对应 / 要求不可推断的题，处置边界在哪？** 4159（题面讲 A，gold 做 B）、4925（零样例却要逐字字符串）、
   6775（裁定只在 hints）三题的共同点是：材料本身自洽、stage1 gold 也是 RESOLVED_FULL，但盲解者拿不到判分所需的信息。
   是按「修订题面」保留，还是直接剔除？这直接决定本包 13 题里有多少能进训练/评测池。
