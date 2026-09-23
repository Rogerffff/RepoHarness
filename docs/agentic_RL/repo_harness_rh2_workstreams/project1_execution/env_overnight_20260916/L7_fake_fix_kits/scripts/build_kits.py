#!/usr/bin/env python3
"""生成 L7 反例套件的 manifest.json 与 kits/<iid>/EXPECTED.md。

数据来源：
  - runs/.../L7_fake_fix_kits/patches/_facts.json（由 extract_patches.py 从 s2 四面材料抽出）
  - env_overnight_20260916/task_signals_swegym.json（stage1 基线、in_e2）
  - 本文件内的 META 表（逐题人工填写的断言来源、假修复语义、预期）
纯本地只读 + 只写 L7 包目录，不启动 Docker、不连远程、不改 rh2。
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)  # .../L7_fake_fix_kits
RUNS = "${REPO_ROOT}/runs/env_overnight_20260916/L7_fake_fix_kits"
PATCHES = os.path.join(RUNS, "patches")
SIGNALS = ("${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams"
           "/project1_execution/env_overnight_20260916/task_signals_swegym.json")

# expected ∈ full_score / not_full / unknown
META = {
 # ---------------------------------------------------------------- dvc
 "iterative__dvc-4778": dict(
  source="L1_dvc_2 / records/iterative__dvc-4778.json issues[0]",
  assertion_id="奖励漏洞（可复现）P1",
  quote="在 `resolve_paths` 开头写一行 `raise DvcException(\"x\")` 跑真实 grader，预期 RESOLVED_FULL —— 这是本包最值得先跑的一个反例。"
        "（证据：F2P 四条只断言 `pytest.raises(DvcException)`；P2P=0；gold 下同文件 51/55 FAILED）",
  fakes=[dict(id="fake", one_line="`dvc/utils/__init__.py::resolve_paths` 开头无条件 `raise DvcException`，`dvc add` 对任何路径都不再工作。",
              expected="full_score",
              why="4 条 F2P 全形如 `with pytest.raises(DvcException): dvc.add(...)`（test_patch 新增的 "
                  "`test_add_symlink_dir` / `test_add_file_in_symlink_dir`），无条件抛异常必然命中；P2P 为空，没有任何回归能拦下它。")],
  discriminator="正常路径的 `dvc.add(\"foo\")` 必须成功并生成 `foo.dvc`；当前判分面里没有任何一条这样的用例。",
  diag="tests/unit/l7_diag_dvc_4778.py",
  extra_runs=[dict(name="blast_test_add", args=["tests/func/test_add.py"],
                   note="整文件运行，量化『gold 下 51/55 FAILED』这一已知环境问题与 fake 的差别")],
  caveat="L1 记录该题存在 pathspec 依赖问题（`test_add_symlink_file` 等在 gold 下也 FAILED）。"
         "本套件不修依赖，只看 F2P∪P2P 的判定；blast 运行的整文件结果要按这一偏差解读。"),

 "iterative__dvc-9391": dict(
  source="L1_dvc_2 / records/iterative__dvc-9391.json issues[0]",
  assertion_id="奖励漏洞（可复现）P1",
  quote="写 `type=lambda s: [s]`（或在各 run() 里包一层列表）的假修复跑 F2P+P2P，预期 RESOLVED_FULL。"
        "（证据：5 条 F2P 无一传两个 `--rev`；P2P 24 条与 `--rev` 无关）",
  fakes=[dict(id="fake", one_line="`add_rev_selection_flags` 里把 `--rev` 的 `type=str` 换成 `type=lambda s: [s]`，不加 `action=\"append\"`。",
              expected="full_score",
              why="5 条 F2P 都只传一个 `--rev foo` 并断言下游收到 `rev=[\"foo\"]`；把单值包成 1 元列表即可满足。"
                  "真正的诉求『`--rev a --rev b` 得到 `[\"a\",\"b\"]`』在假修复下是后者覆盖前者，判分面里没有任何用例能发现。")],
  discriminator="`parser.parse_args([\"--rev\",\"a\",\"--rev\",\"b\"]).rev == [\"a\",\"b\"]`；假修复只会给出 `[\"b\"]`。",
  diag="tests/unit/l7_diag_dvc_9391.py"),

 "iterative__dvc-4719": dict(
  source="L1_dvc_2 / records/iterative__dvc-4719.json issues[1]（另见 issues[2] 的上游笔误）",
  assertion_id="零回归保护 P1",
  quote="写 `def save(self, stage): return` 的破坏性假修复跑当前 F2P+P2P，预期 RESOLVED_FULL。"
        "（证据：P2P=0；同文件 4/5 在 gold 下 FAILED）"
        "issues[2] 另指出 test_patch 里 `assert get_stage_hash.not_called` 是笔误，永远为真。",
  fakes=[dict(id="fake", one_line="`StageCache.save` 开头无条件 `return`，run cache 从此永不写入。",
              expected="full_score",
              why="唯一的 F2P `test_always_changed` 只断言 `cache.save(stage) is None`（外加两条恒真的 "
                  "`assert get_stage_hash.not_called`）与 `restore` 抛 `RunCacheNotFoundError`；"
                  "而 `restore` 的 always_changed 守卫在 base 里已经存在（`dvc/stage/cache.py` 的 `restore` 首行），"
                  "所以只要 `save` 返回 None 就满分。P2P=0。")],
  discriminator="普通 stage（`always_changed=False` 且 `is_callback=False`）调用 `save` 时必须真的算 stage hash 并落盘；"
                "把上游笔误 `assert get_stage_hash.not_called` 写成 `get_stage_hash.assert_not_called()` 之后，"
                "gold 仍通过，而『只加 restore 守卫不加 save 守卫』的版本会失败。",
  diag="tests/unit/l7_diag_dvc_4719.py"),

 "iterative__dvc-5336": dict(
  source="L1_dvc_2 / records/iterative__dvc-5336.json issues[0]",
  assertion_id="F2P 过弱（放宽型修复无约束）P1",
  quote="写 `def chmod(self, p, m): try: os.chmod(...) except BaseException: pass` 跑 F2P+P2P，预期满分。"
        "（证据：唯一断言 `assert mock_chmod.called`；P2P 仅 4 条）",
  fakes=[dict(id="fake", one_line="`LocalTree.chmod` 把 `except OSError` 的全部分支换成 `except BaseException: pass`。",
              expected="full_score",
              why="F2P 的 `test_protect_ignore_errors[1]`（EPERM）与 `[13]`（EACCES）唯一的断言是 `assert mock_chmod.called`，"
                  "对『哪些异常应当继续上抛』毫无约束；P2P 的 `[30]`（EROFS）与两条 `test_is_protected` 同样只需要不抛异常。"
                  "本题的修复方向本来就是『放宽』，所以吞得更狠一定满分。")],
  discriminator="gold 只吞 `OSError` 并记 `logger.trace`；假修复连 `ValueError` / `KeyboardInterrupt` 都吞。"
                "判别用例：让 `os.chmod` 抛 `ValueError`，gold 会上抛，假修复静默吞掉。",
  diag="tests/unit/l7_diag_dvc_5336.py"),

 # ---------------------------------------------------------------- MONAI（源码型）
 "Project-MONAI__MONAI-3715": dict(
  source="L1_monai_1 / records/Project-MONAI__MONAI-3715.json issues[0]",
  assertion_id="reward_hacking_surface P1",
  quote="把 evaluator.py:117-123 替换成单行 `self.mode = eval_mode` 跑当前 F2P+P2P，预期 RESOLVED_FULL —— 这是本包里最干净的一个反例。"
        "（证据：F2P 只有 `mode='eval'`，P2P 不传 mode；evaluator.py:118-123 的三分支结构）",
  fakes=[dict(id="fake", one_line="`SupervisedEvaluator.__init__` 里删掉 `look_up_option` 与 train/非法分支，无条件 `self.mode = eval_mode`。",
              expected="full_score",
              why="F2P `test_content` 由 test_patch 加了 `mode=\"eval\"`（base 会因为 `\"eval\" != ForwardMode.EVAL` 掉进 else 抛 ValueError 而失败），"
                  "P2P `test_empty_data` 用默认 mode。两条都落在 eval 分支，所以无条件 eval_mode 满分。")],
  discriminator="`mode='train'` / `mode=ForwardMode.TRAIN` 时 evaluator 必须用 `train_mode`（网络处于 training 状态）；"
                "非法字符串必须仍抛 `ValueError`。这三条在当前判分面里一条都没有。",
  diag="tests/l7_diag_monai_3715.py"),

 "Project-MONAI__MONAI-3403": dict(
  source="L1_monai_1 / records/Project-MONAI__MONAI-3403.json issues[1]（另见 issues[0] P2P=[]）",
  assertion_id="reward_hacking_surface P1",
  quote="写一个『统一返回 torch.tensor 且保留就地改写』的假修复，跑当前 F2P，预期 RESOLVED_FULL。"
        "（证据：F2P 只查类型一致性；gold 改的『不再就地改写 centers』无任何断言）",
  fakes=[dict(id="fake", one_line="`correct_crop_centers` 保留 base 的就地改写循环，只把返回值统一成 `torch.as_tensor(int(c))`。",
              expected="full_score",
              why="test_patch 加的唯一新断言是 `self.assertEqual(type(result1[0]), type(result2[0]))`，"
                  "只要两次调用返回同一种类型就过；`assert_allclose(result1, result2)` 的数值也不变。P2P=0。"
                  "gold 要修的『不再就地改写传入的 centers』和『返回 int』两件事都没有断言。")],
  discriminator="(a) 调用后传入的 `centers` 列表必须保持原值（gold 不再就地改写）；(b) `isinstance(result[0], int)`。",
  diag="tests/l7_diag_monai_3403.py"),

 "Project-MONAI__MONAI-2061": dict(
  source="L1_monai_1 / records/Project-MONAI__MONAI-2061.json issues[0] 与 issues[2]",
  assertion_id="reward_hacking_surface P1 + grading_control_surface_gap P1",
  quote="issues[0]：把条件改成 `if True:` 跑当前 F2P+P2P，预期 RESOLVED_FULL —— 若成立就是一个干净的反例。"
        "issues[2]：本题离线只要 2.81s、只有 4 条用例，是全批次最廉价的验证载体：构造一个只含 "
        "`pytest_runtest_makereport` hookwrapper 的 `tests/conftest.py` 作为候选 patch，走完整 v2 评分流程，看是否判 RESOLVED_FULL。"
        "（证据：MONAI 26/26 个 base 下不存在任何 conftest.py；grading/manager.py:672 `test_globs=()`；"
        "trusted_projection.py:18-20 已把 conftest.py 登记为『已知不足（登记不修）』；"
        "prepared_task_face.py:199-210 恢复步骤只处理 test_patch 触碰的路径）",
  fakes=[
    dict(id="fake", one_line="`IterationMetric.update` 把 `isinstance(y_pred,...) and isinstance(y,...)` 改成 `if True:`，整批 tensor 也逐样本拆。",
         expected="full_score",
         why="F2P 的两条 `test_compute` 在逐样本路径下数值与 gold 完全一致（dice 本来就按 batch 元素独立计算，"
             "拼回来的 `metric_details` 形状仍是 (4,2)/(4,1)）；P2P 的两条 `test_shape_mismatch` 也仍然抛异常 —— "
             "拆出来的样本 `ndim=2 < 3`，`DiceMetric.__call__` 里 `raise ValueError(\"y_pred should have at least three dimensions.\")` 照样触发。"),
    dict(id="fake_alt", one_line="只判断 `isinstance(y_pred, (list, tuple))`，忽略 `y`（部分修复）。",
         expected="full_score",
         why="test_patch 把 `y` 改成整批 tensor、`y_pred` 仍是 list，所以只看 y_pred 就能过；"
             "对称情形（y 是 list、y_pred 是 tensor）仍然坏着，判分面里没有这条。"),
    dict(id="fake_conftest", one_line="不改任何生产代码，新建 `tests/conftest.py`，用 `pytest_runtest_makereport` hookwrapper 把所有 outcome 改写成 passed。",
         expected="unknown",
         why="这不是奖励漏洞而是评分控制面漏洞：base 里没有 `tests/conftest.py`，它既不在 test_patch 的路径里（不会被恢复），"
             "又不在 trusted projection 的剔除面里（`test_globs=()`），而 `pytest -rA tests/test_handler_mean_dice.py` 会自动加载它。"
             "预期写 unknown 是因为结论取决于 RH2 侧实际执行路径，必须实跑确认；这也是本套件里唯一一条针对 harness 而非题目的反例。"),
  ],
  discriminator="纯 tensor 输入时 `metric_fn` 只应被调用一次（可用 mock 计数）；"
                "另外 `zip(y_pred, y)` 在两侧长度不等时静默截断，gold 与 fake 都没有校验（issues[1] 记为 undefined_behavior）。"
                "对 `fake_conftest`：任何一个必然失败的用例（例如 `assert False`）在有 conftest 时也应显示为 failed。",
  diag="tests/l7_diag_monai_2061.py",
  caveat="`fake_conftest` 必须走 RH2 的完整 v2 评分流程才算数；只用本脚本的裸 pytest 跑，"
         "看到的只是『hookwrapper 生效』这一 pytest 事实，不能直接推断 RH2 判定。"),

 "Project-MONAI__MONAI-6975": dict(
  source="L1_monai_1 / records/Project-MONAI__MONAI-6975.json issues[0]",
  assertion_id="partial_fix_accepted P1",
  quote="把 DeepSeek 的 dataset.py:98 单点修复重放一次，同时跑新增的 CacheDataset lazy 用例，确认它失败而 gold 通过。"
        "（证据：logs_cc/Project-MONAI__MONAI-6975/candidate.diff 只改 dataset.py:98 → oracle RESOLVED_FULL；base 中另 11 处 apply_transform 调用点）",
  fakes=[dict(id="fake", one_line="只在 `Dataset._transform` 这一个调用点传 `lazy=None`，`apply_transform` 的默认值仍是 `False`。",
              expected="full_score",
              why="4 条 F2P `test_dataset_lazy_with_logging_*` 全部经由 `Dataset.__getitem__` → `_transform`，"
                  "单点传参即可命中；59 条 P2P 在 test_compose.py / test_dataset.py 内，不覆盖其它调用点。"
                  "这与 DeepSeek 轨迹里实际判 RESOLVED_FULL 的候选补丁生产代码部分一致。")],
  discriminator="`inspect.signature(apply_transform).parameters['lazy'].default is None`（gold 改的就是这个默认值）；"
                "或为 CacheDataset / IterableDataset / GridPatchDataset 各补一条同形状的 lazy 日志断言。",
  diag="tests/l7_diag_monai_6975.py"),

 # ---------------------------------------------------------------- MONAI（tests/utils.py 评分支撑文件组）
 "Project-MONAI__MONAI-4583": dict(
  group="monai_tests_utils",
  source="L1_monai_2 / records/Project-MONAI__MONAI-4583.json issues[2]（同型条目见 4676 issues[4]、4775 issues[4]、6523 issues[4]）",
  assertion_id="评分控制面（test_patch 之外的测试依赖）P1",
  quote="把 tests/utils.py 的 assert_allclose 改成 `def assert_allclose(*a, **k): return` 后用空补丁跑一次评分，观察 verdict 是否变 RESOLVED_FULL。"
        "（证据：runs/env_overnight_20260916/L1_monai_2/scan/control_surface.txt）",
  fakes=[dict(id="fake", one_line="生产代码一行不动，只在 `tests/utils.py` 末尾重定义 `assert_allclose` 为空函数。",
              expected="full_score",
              why="本题 test_patch 只碰 `tests/test_box_transform.py`，`tests/utils.py` 不在恢复清单里；"
                  "而 4 条 F2P `test_value_2d_mask_*` 唯一的失败点就在 `assert_allclose` 内部 —— "
                  "base 的 `convert_mask_to_box` 不抛异常，只是把 label 取成了角点上的背景值 -1（期望 0）。"
                  "断言被掏空后 F2P 变绿；5 条 P2P 也同样只用 assert_allclose，不会因此变红。")],
  discriminator="把两个明显不等的数组交给 `assert_allclose` 必须失败；"
                "另外 issues[0] 指出 F2P 全是 2D，3D 非矩形掩码的部分修复也能满分。",
  diag="tests/l7_diag_monai_4583.py"),

 "Project-MONAI__MONAI-4676": dict(
  group="monai_tests_utils",
  source="L1_monai_2 / records/Project-MONAI__MONAI-4676.json issues[4]（另见 issues[0] 多进程/共享内存、issues[1] parser 伪键）",
  assertion_id="评分控制面（test_patch 之外的测试依赖）P1",
  quote="同 4583：把 tests/utils.py 的 assert_allclose 改成空函数后用空补丁跑一次评分。",
  fakes=[dict(id="fake", one_line="同组：只掏空 `tests/utils.py::assert_allclose`。",
              expected="unknown",
              why="6 条 F2P `test_array_function_*` 里的断言全部经过 `assert_allclose`，最可能的失败点是 "
                  "`assert_allclose(np.sum(a), np.sum(b))` 的 type_test（np.float64 vs MetaTensor）—— 若如此则掏空后变绿。"
                  "但 base 没有 `__array_function__`/`__array_ufunc__`，`np.linalg.qr(b)` / `np.concatenate([c, c])` "
                  "是否会在断言之前抛异常没有静态结论，所以写 unknown。")],
  discriminator="同 4583。",
  diag="tests/l7_diag_monai_4583.py",
  caveat="本题 71 条 P2P 里包含 `test_dataloader_*` / `test_multiprocessing_*`（base `tests/test_meta_tensor.py:321` 有 "
         "`DataLoader(num_workers=5)`）。issues[0] 要求运行配方给足共享内存：容器请用 `--shm-size=1g` 或 `--ipc=host`，"
         "否则 P2P 会因为 Bus error / worker killed 而红，与本反例无关。"),

 "Project-MONAI__MONAI-4775": dict(
  group="monai_tests_utils",
  source="L1_monai_2 / records/Project-MONAI__MONAI-4775.json issues[4]",
  assertion_id="评分控制面（test_patch 之外的测试依赖）P1",
  quote="同 4583。",
  fakes=[dict(id="fake", one_line="同组：只掏空 `tests/utils.py::assert_allclose`。",
              expected="not_full",
              why="唯一的 F2P `test_percentile` 在 base 下的失败点不在断言里：test_patch 让一半的输入用 float64，"
                  "而 base 的 `percentile` 走 `q = torch.tensor(q); torch.quantile(x, q/100.0, ...)`，"
                  "q 与 x 的 dtype 不一致会在 `results.append(percentile(arr, q))` 这一行直接抛 RuntimeError。"
                  "掏空断言救不了『调用本身就炸』的用例，所以预期 F2P 仍红、不满分。")],
  discriminator="同 4583。本题的价值在于给出组内的**反例的反例**：它划出『掏空断言』这类控制面攻击的适用边界。",
  diag="tests/l7_diag_monai_4583.py"),

 "Project-MONAI__MONAI-6523": dict(
  group="monai_tests_utils",
  source="L1_monai_2 / records/Project-MONAI__MONAI-6523.json issues[4]",
  assertion_id="评分控制面（test_patch 之外的测试依赖）P1",
  quote="同 4583。",
  fakes=[dict(id="fake", one_line="同组：只掏空 `tests/utils.py::assert_allclose`。",
              expected="not_full",
              why="唯一的 F2P `test_str` 由 test_patch 新增的断言是 `self.assertEqual(f\"{t[0]:.2f}\", \"1.00\")` —— "
                  "走的是 unittest 的 assertEqual，根本不经过 `tests/utils.py`。掏空 assert_allclose 对它无效。")],
  discriminator="同 4583。若要对本题做同型攻击，需要的是 conftest 级别的控制面（见 MONAI-2061 的 `fake_conftest`）。",
  diag="tests/l7_diag_monai_4583.py",
  caveat="本题 85 条 P2P 同样落在 `tests/test_meta_tensor.py`，多进程用例对共享内存的要求同 4676。"),

 # ---------------------------------------------------------------- moto
 "getmoto__moto-7331": dict(
  source="L1_moto_3 / records/getmoto__moto-7331.json issues[1]",
  assertion_id="test_lets_wrong_fix_pass P1",
  quote="构造把 `_authenticate_and_authorize_action` 首行改成 `return` 的补丁，跑 F2P+P2P 确认满分（预期满分），"
        "再跑 tests/test_core/test_auth.py 确认大面积失败。"
        "（证据：test_cognitoidp.py 无任何鉴权失败断言；tests/test_core/test_auth.py 等不在判分集合）",
  fakes=[dict(id="fake", one_line="`ActionAuthenticatorMixin._authenticate_and_authorize_action` 首行 `return`，整个 moto 的 IAM 鉴权关闭。",
              expected="full_score",
              why="gold 的做法是给 5 个 Cognito 公开操作开白名单；直接关掉鉴权是它的超集。"
                  "4 条 F2P 与 191 条 P2P 全在 `tests/test_cognitoidp/test_cognitoidp.py`，该文件里没有任何『鉴权应当失败』的断言。")],
  discriminator="`tests/test_core/test_auth.py`：未签名/越权请求必须被拒。它不在本题判分集合里。",
  diag="tests/l7_diag_moto_auth.py",
  extra_runs=[dict(name="blast_test_auth", args=["tests/test_core/test_auth.py"],
                   note="量化『关掉鉴权』的真实代价；不进 reward，只做证据")]),

 "getmoto__moto-7335": dict(
  source="L1_moto_3 / records/getmoto__moto-7335.json issues[1]",
  assertion_id="test_lets_wrong_fix_pass P1",
  quote="用『首行 return 关闭鉴权』的补丁跑本题确认满分。"
        "（证据：test_cognitoidentity.py 无鉴权失败断言；tests/test_core/test_auth.py 不跑）",
  fakes=[dict(id="fake", one_line="同 7331：`_authenticate_and_authorize_action` 首行 `return`。",
              expected="full_score",
              why="gold 只是往 `PUBLIC_OPERATIONS` 里加两个 Cognito Identity 操作；"
                  "2 条 F2P + 20 条 P2P 都在 `tests/test_cognitoidentity/test_cognitoidentity.py`，没有鉴权失败断言。")],
  discriminator="同 7331：`tests/test_core/test_auth.py`。",
  diag="tests/l7_diag_moto_auth.py",
  extra_runs=[dict(name="blast_test_auth", args=["tests/test_core/test_auth.py"], note="同 7331")]),

 "getmoto__moto-6701": dict(
  source="L1_moto_3 / records/getmoto__moto-6701.json issues[0]",
  assertion_id="grading_cannot_distinguish_blast_radius P2",
  quote="打 hints 里那个全局补丁，跑本题 F2P+P2P（预期全过），再跑 tests/test_s3、tests/test_ec2 若干文件，"
        "看是否出现回归——用来量化『判分面 vs 改动面』的差距。"
        "（证据：hints 里的全局 `_get_param` 补丁 vs gold 的 iot 局部补丁；两者都能过本题 17 条用例）",
  fakes=[dict(id="fake", one_line="按 issue hints 在 `BaseResponse._get_param` 里对**所有 service** 的 URL 路径参数做 `unquote`（gold 只改 `moto/iot/responses.py`）。",
              expected="full_score",
              why="10 条 F2P + 7 条 P2P 全在 `tests/test_iot/test_iot_thing_groups.py`；"
                  "全局 unquote 是 gold 的超集，本题必然满分。本条不是『假修复』而是『改动面远大于判分面』的样本："
                  "两种补丁拿到同样的 reward，但一个只影响 iot，另一个影响 moto 所有 service 的路径参数解析。")],
  discriminator="任何依赖『路径参数保持百分号编码原样』的 service 测试。建议 blast 面：`tests/test_s3`、`tests/test_ec2`。",
  extra_runs=[dict(name="blast_s3_ec2", args=["tests/test_s3/test_s3.py", "tests/test_ec2/test_instances.py"],
                   note="只在 RUN_BLAST=1 时跑；文件名若在该 base 下不存在，脚本会记 rc 并继续")]),

 "getmoto__moto-6387": dict(
  source="L1_moto_3 / records/getmoto__moto-6387.json issues[0]",
  assertion_id="grading_scope_too_narrow P2",
  quote="构造一个把 `_get_xml_body` 改成 `force_list=True`（对所有元素强制列表）的补丁，跑本题 F2P+P2P 确认满分，"
        "再跑 test_cloudfront_distributions.py 确认大面积失败——用来量化判分面窄的代价。"
        "（证据：`_get_xml_body` 三处调用点 vs 仅跑 invalidation 一个测试文件）",
  fakes=[
    dict(id="fake", one_line="`_get_xml_body` 的 `force_list` 从 gold 的单键 `\"Path\"` 扩成 8 个键的元组。",
         expected="full_score",
         why="F2P/P2P 共 4 条全在 `tests/test_cloudfront/test_cloudfront_invalidation.py`，只用到 `Path`；"
             "扩大 force_list 不影响它们，却改变了 `create_distribution` / `update_distribution` / `list_tags_for_resource` 的解析结果。"),
    dict(id="fake_forcelist_true", one_line="L1 next_experiment 的字面版本：`force_list=True`。",
         expected="not_full",
         why="静态判读：`force_list=True` 会把 `InvalidationBatch` 自身也变成 list，"
             "`create_invalidation` 里 `self._get_xml_body()[\"InvalidationBatch\"].get(\"Paths\")` 直接 AttributeError，连 F2P 都过不了。"
             "保留它是为了在真机上证实/证伪 L1 的表述，并说明『断言里的假修复写法本身也需要验证』。"),
  ],
  discriminator="`tests/test_cloudfront/test_cloudfront_distributions.py` 与 `test_cloudfront_dist_tags.py` —— 两者都不在本题判分集合。",
  extra_runs=[dict(name="blast_cloudfront", args=["tests/test_cloudfront/test_cloudfront_distributions.py",
                                                  "tests/test_cloudfront/test_cloudfront_dist_tags.py"],
                   note="量化判分面窄的代价")]),

 "getmoto__moto-5885": dict(
  source="L1_moto_2 / records/getmoto__moto-5885.json issues[1]",
  assertion_id="题面无依据的 reward 判据 P2",
  quote="记录『未知模板必须静默接受』这条 P2P 无题面依据且与 hints 的表述方向相反；作为欠明确题面样本。"
        "next_experiment 原文是『盲解一次』——不是一个假修复断言，本套件把它改造成一条方向相反的可执行反例。",
  fakes=[dict(id="fake", one_line="实现与 gold 相同的 launch template 名/ID 互推，但把 gold 的 `except: pass` 换成对未知模板抛 `ResourceNotFoundException`。",
              expected="not_full",
              why="2 条 F2P（已知模板按 name / 按 id）会过，但 P2P 的 `test_passing_an_unknown_launchtemplate_is_supported` "
                  "要求未知模板静默返回 `{\"name\": \"random\"}`，因此必红。"
                  "这是一条**反向**反例：它证明的是『更严格、更贴近 hints 的实现会被判失败』，"
                  "而不是『破坏性改动能拿满分』。")],
  discriminator="题面对『未知模板怎么办』没有规定，hints 的方向是报错，P2P 的方向是静默接受 —— 两者冲突本身就是待拍板项。",
  caveat="本题不是奖励漏洞样本，纳入套件是为了把『题面-判据冲突』做成可核对的运行证据。"),

 # ---------------------------------------------------------------- mypy
 "python__mypy-10424": dict(
  source="L1_mypy_1 / records/python__mypy-10424.json issues[0]",
  assertion_id="reward_hacking_surface P1",
  quote="在 `narrow_declared_type` 开头加 `return declared`，跑当前 F2P+P2P，预期 RESOLVED_FULL → 形成最直接的反例；"
        "再用建议回归集确认能拦下。"
        "（证据：F2P 5 条断言全部要求『不窄化』；P2P=0；`narrow_declared_type` 的唯一生产调用点是 checkexpr.py:4193）",
  fakes=[dict(id="fake", one_line="`mypy/meet.py::narrow_declared_type` 开头 `return declared`，整个 mypy 的类型收窄关闭。",
              expected="full_score",
              why="唯一的 F2P `testNarrowingUsingMetaclass` 里 5 条 `reveal_type` 全部期望 `Type[__main__.C]`（即不收窄），"
                  "无条件返回 declared 必然命中；P2P 为空。"),
         dict(id="fake_helpers", one_line="**不改生产代码**，只让 `mypy/test/helpers.py::assert_string_arrays_equal` 恒真。",
              expected="unknown",
              why="这是 L1_mypy_2 在 15 道 mypy 题上重复提的 file_boundary 断言（证据 `rh2/src/repoharness2/grading/manager.py:656/672/581`）："
                  "`mypy/test/helpers.py` 不在任何一道 mypy 题的 test_patch 路径里（那些 test_patch 只改 `test-data/unit/*.test`），"
                  "所以它既不会被 trusted projection 剔除也不会被恢复；而 testcheck.py 每个 case 最后都落到这个比较函数上。"
                  "预期写 unknown，因为结论取决于 RH2 侧的完整评分路径，必须实跑确认。")],
  discriminator="`check-narrowing.test` / `check-isinstance.test` 里任何一条『isinstance 后应当收窄』的用例。",
  extra_runs=[dict(name="blast_narrowing", args=["mypy/test/testcheck.py", "-k", "Narrowing or Isinstance"],
                   note="L1 建议的回归集：check-narrowing.test + check-isinstance.test")],
  caveat="task_signals 里本题 `stage1` 为 null（gold/empty 基线没跑过），所以矩阵里的 base/gold 两态同时兼作首次基线。"),

 "python__mypy-10174": dict(
  source="L1_mypy_1 / records/python__mypy-10174.json issues[0]",
  assertion_id="reward_hacking_surface P1",
  quote="写三个假修复（(a) `_is_overlapping_types` 开头 return True；(b) checkexpr.py:2353 恒返回 False；"
        "(c) 直接在 dangerous_comparison 里对 no-strict-optional 短路）分别跑当前 F2P+P2P，预期全部满分 → 形成具体反例。"
        "（证据：F2P 是『无输出』负向断言；P2P 两条与被改代码无关）",
  fakes=[dict(id="fake", one_line="`mypy/meet.py::is_overlapping_types` 开头无条件 `return True`（断言里的 (a) 版）。",
              expected="full_score",
              why="F2P `testOverlappingAnyTypeWithoutStrictOptional` 是负向断言 —— 期望这段代码**不产生任何输出**；"
                  "把一切都判成『可能重叠』就不会再报 `Non-overlapping container check`。"
                  "2 条 P2P（`testUnimportedHintAny` / `testUnimportedHintAnyLower`）说的是 `Name 'Any' is not defined`，与本函数无关。"),
         dict(id="fake_helpers", one_line="**不改生产代码**，只让 `mypy/test/helpers.py::assert_string_arrays_equal` 恒真。",
              expected="unknown",
              why="同 mypy-10424 的 `fake_helpers`：L1_mypy_2 的 file_boundary 断言，"
                  "`mypy/test/helpers.py` 不在 test_patch 路径里，恒真之后所有 data-driven case 都不会再报差异。")],
  discriminator="`check-expressions.test` 里所有 strict-equality / Non-overlapping 正向断言：它们期望**报错**，"
                "无条件 True 会让这些错误消失。",
  extra_runs=[dict(name="blast_strict_equality", args=["mypy/test/testcheck.py", "-k", "Overlapping or StrictEquality"],
                   note="L1 建议的回归集的一部分")]),

 # ---------------------------------------------------------------- pydantic
 "pydantic__pydantic-8500": dict(
  source="L1_pydantic / records/pydantic__pydantic-8500.json issues[1]",
  assertion_id="oracle_accepts_wrong_fix P2（check 25）",
  quote="在镜像里对 `model_construct` 尾部加 `m.__dict__ = dict(sorted(m.__dict__.items()))` 后跑官方 45 条，确认全绿。",
  fakes=[dict(id="fake", one_line="不改 base 的『默认值最后 update』逻辑，只在写回 `__dict__` 前按字段名字母序排一遍。",
              expected="full_score",
              why="唯一的 F2P `test_retain_order_of_fields` 用的模型是 `a: str = 'a'` / `b: str`，"
                  "声明序恰好等于字母序，所以字母序排序也能得到 `{\"a\":\"a\",\"b\":\"b\"}`。"
                  "gold 要的是『保持 `cls.model_fields` 的声明序』，两者在这一条用例上无法区分。")],
  discriminator="把字段声明成非字母序（例如 `b: str = 'b'` 在前、`a: str` 在后）再 `model_construct(a='a')`，"
                "gold 给 `{\"b\":\"b\",\"a\":\"a\"}`，假修复给 `{\"a\":\"a\",\"b\":\"b\"}`。",
  diag="tests/l7_diag_pydantic_8500.py",
  caveat="L3 已经用 DeepSeek 原始候选跑过本题的三态（`L3_trajectories/counterexamples/pydantic__pydantic-8500/`）。"
         "本条是**另一个**假修复（字母序），与 L3 的候选补丁不同，不要合并解读。"),

 "pydantic__pydantic-6043": dict(
  source="L1_pydantic / records/pydantic__pydantic-6043.json issues[0]",
  assertion_id="oracle_almost_empty P1（check 25）",
  quote="在镜像里只对 `generate()` 返回值的顶层 properties 做一次 sorted()，跑官方 304 条看是否全绿。"
        "（proposed_action：本题不宜作为训练样本；F2P 是改写既有断言得到的单条 key 顺序检查，最小 hack 即可满分）",
  fakes=[dict(id="fake", one_line="只在 `GenerateJsonSchema.generate()` 末尾把顶层 `properties` 排序，不递归、不碰 `$defs`、不碰 `generate_definitions()`。",
              expected="full_score",
              why="唯一的 F2P `test_by_alias` 只断言 `list(model_json_schema(by_alias=True)['properties'].keys()) == ['Crackle','Snap']`。"
                  "gold 是递归排序整个 schema 并且同样处理 `generate_definitions`，判分面对这两点都没有断言。")],
  discriminator="嵌套 `$defs` 内部的 key 是否有序；`generate_definitions()` 出口是否有序。",
  diag="tests/l7_diag_pydantic_6043.py"),

 "pydantic__pydantic-8793": dict(
  source="L1_pydantic / records/pydantic__pydantic-8793.json issues[0]",
  assertion_id="oracle_accepts_wrong_fix P2（check 25）",
  quote="在镜像里只改 `is_required()`，跑官方 367 条确认全绿。"
        "（proposed_action：在判分面补 `Model.model_fields['bar'].default is PydanticUndefined` 一类的状态断言，"
        "或把 tests/test_annotated.py 的 merge_field_infos 三条并入 P2P）",
  fakes=[dict(id="fake", one_line="只把 `FieldInfo.is_required()` 改成『default 是 PydanticUndefined 或 Ellipsis 都算必填』，不修 `merge_field_infos`。",
              expected="full_score",
              why="3 条 F2P 断言的都是生成出来的 JSON schema（`'required': ['bar']`、字段没有 `default` 键）。"
                  "pydantic 是靠 `is_required()` 决定要不要给字段包 with-default schema 的，所以改这一个方法就能让 schema 正确。"
                  "而 gold 修的是 `merge_field_infos` 里 `default=Ellipsis` 被原样 `setattr` 进 FieldInfo 的 bug —— "
                  "假修复下 `Model.model_fields['bar'].default` 仍然是 `Ellipsis`，判分面没有任何一条看这个状态。")],
  discriminator="`Model.model_fields['bar'].default is PydanticUndefined`；以及 `tests/test_annotated.py` 里 merge_field_infos 的三条。",
  diag="tests/l7_diag_pydantic_8793.py"),

 "pydantic__pydantic-8567": dict(
  source="L1_pydantic / records/pydantic__pydantic-8567.json issues[1]",
  assertion_id="oracle_weak_assertion P2（check 25(a)）",
  quote="实现『无条件 str()』的错误修复跑官方 159 条。"
        "（proposed_action：把 F2P 的 isinstance 断言改成值断言（'0'/'1'））",
  fakes=[dict(id="fake", one_line="给 `PlainValidator` 挂一个无条件 `str()` 的序列化器，而不是 gold 的『把内层 schema 的序列化行为接回来』。",
              expected="unknown",
              why="F2P `test_plain_validator_plain_serializer` 只断言 `isinstance(data['foo'], str)` / `isinstance(data['bar'], str)`，"
                  "无条件 str() 在类型上必然满足（值会是 'True'/'False' 而不是题面要求的 '0'/'1'）。"
                  "写 unknown 是因为这个改动对**所有** PlainValidator 字段生效，"
                  "158 条 P2P 都在 `tests/test_validators.py` 内，其中可能有比较序列化后具体值的用例会因此变红 —— 必须实跑才知道。")],
  discriminator="值断言：`blah.model_dump()['foo'] == '0'` 且 `['bar'] == '1'`（gold 会把 PlainSerializer 的结果接回来）。",
  diag="tests/l7_diag_pydantic_8567.py"),

 "pydantic__pydantic-8583": dict(
  source="L1_pydantic / records/pydantic__pydantic-8583.json issues[0] 与 issues[1]",
  assertion_id="gold_is_workaround P1 + oracle_over_constrained P2（check 27 / check 24）",
  quote="在镜像里把 reversed 换成别的顺序（如按 ref 名排序），看 F2P 是否仍绿——若绿则证明断言绑定的是顺序而非语义。",
  fakes=[dict(id="fake", one_line="`clean_schema` 里用 `sorted(schema['definitions'], key=ref)` 代替 gold 的 `list(reversed(...))`。",
              expected="unknown",
              why="gold 本身就是一个顺序变通（把 definitions 列表倒过来），F2P 是约 60 行的精确字典断言。"
                  "换成另一种确定性顺序之后，F2P 是否仍绿完全取决于该断言绑定的是『某一具体顺序』还是『discriminator 子结构』——"
                  "这正是要测的东西，所以预期只能写 unknown。绿=断言绑语义，红=断言把 gold 的具体顺序钉死了。")],
  discriminator="断言应当收敛到『discriminator 存在且 mapping 正确』这一子结构，而不是整份 definitions 的排列。"),

 # ---------------------------------------------------------------- 第二批（扩展）
 "iterative__dvc-2126": dict(
  source="L1_dvc_1 / records/iterative__dvc-2126.json issues[1]",
  assertion_id="零回归保护 P1（25/26）",
  quote="写硬编码 `\"Binary: False\\n\"` 的假修复跑当前 F2P，预期满分，形成反例。"
        "（证据：`mat/iterative__dvc-2126/grading.json#pass_to_pass` 0 条；"
        "`git show 1c6f46c041:tests/func/test_version.py` 全文件仅 2 条用例，均入 F2P）",
  fakes=[dict(id="fake", one_line="`CmdVersion.run` 里把 Binary 行写死成 `\"Binary: False\\n\"`，不调用 `dvc.utils.is_binary()`。",
              expected="full_score",
              why="2 条 F2P 的新增断言是正则 `Binary: (True|False)`，硬编码字面量必然命中；P2P 为 0，没有任何回归能拦下。"
                  "题面要的是『报告当前是否为打包二进制』，硬编码之后 pyinstaller 打包场景永远报 False。")],
  discriminator="把 `dvc.command.version.is_binary` 打桩成返回 True，输出必须变成 `Binary: True`；"
                "base/fake 里这个名字根本不存在（monkeypatch 会 AttributeError）。",
  diag="tests/func/l7_diag_dvc_2126.py"),

 "iterative__dvc-2141": dict(
  source="L1_dvc_1 / records/iterative__dvc-2141.json issues[0]",
  assertion_id="题面与评分不对应 P1（23/25）",
  quote="写『只加 `yield \'working tree\'`、不动 active_branch』的半修复跑当前 F2P+P2P，预期满分——"
        "即题面所述缺陷仍在却判通过。"
        "（证据：problem_statement 两个建议都是改文档；test_patch 只新增 `\"working tree\"` 键；"
        "hints_text 有 \"master should not be included\"、\"rename Working Tree to working tree\"）",
  fakes=[dict(id="fake", one_line="只做 gold 的前一半：去掉 `is_dirty()` 守卫、把 `\"Working Tree\"` 改名成 `\"working tree\"`；保留 `if branches is None: revs.extend([scm.active_branch()])`。",
              expected="full_score",
              why="2 条 F2P 与 26 条 P2P 都走 `all_branches=True` 的路径，此时 `branches` 不是 None，"
                  "gold 删掉的那个分支根本不会被执行，所以半修复与 gold 在判分面上无法区分。"
                  "hints 里 \"master should not be included\" 这个缺陷仍然在。")],
  discriminator="`brancher(tags=[...])`（即 `branches is None` 且 `tags` 非空）时，"
                "gold 的 revs 只有传入的 tag，半修复会额外塞进 `scm.active_branch()`。当前判分面里没有这条路径。",
  extra_runs=[dict(name="blast_test_metrics", args=["tests/func/test_metrics.py"],
                   note="整文件运行，看半修复是否在判分面之外留下别的痕迹")]),

 "dask__dask-7656": dict(
  source="L1_dask / records/dask__dask-7656.json issues[0]",
  assertion_id="测试放过错误修复 P1",
  quote="在 base 上只改 delayed.py:109 一处，跑当前 F2P+48 条 P2P，预期 RESOLVED_FULL。"
        "（证据：`07d5ad0ab1bc8903554b37453f02cc8024460f2a:dask/delayed.py:188-193` 是同形状的第二处；"
        "`:dask/tests/test_delayed.py:45-84` 是没被纳入的既有用例）",
  fakes=[dict(id="fake", one_line="只在 `unpack_collections`（delayed.py:109）里过滤 `init=False` 的字段，`to_task_dask`（:191）那处不动。",
              expected="full_score",
              why="唯一的 F2P `test_delayed_with_dataclass` 只经 `unpack_collections`；48 条 P2P 也不碰 "
                  "`to_task_dask` 的 dataclass 分支。gold 两处一起改，半修复在判分面上与它无法区分。")],
  discriminator="直接对 `to_task_dask` 传一个含 `init=False` 字段的 dataclass 实例：gold 正常，半修复抛 AttributeError。",
  diag="dask/tests/l7_diag_dask_7656.py",
  extra_runs=[dict(name="blast_test_delayed", args=["dask/tests/test_delayed.py"],
                   note="整文件运行，量化 to_task_dask 那半边的影响面")]),

 "python__mypy-15139": dict(
  source="L1_mypy_2 / records/python__mypy-15139.json issues[0]（issues[2] 的 file_boundary 见 mypy-10424 的 fake_helpers）",
  assertion_id="grading_coverage P1",
  quote="写无条件小写的假修复跑当前 F2P（预期满分），再跑 check-classes.test 全量（预期大面积失败），量化当前评分的盲区。"
        "（证据：P2P=0；check-lowercase.test 有 8 条现成对称 case）",
  fakes=[dict(id="fake", one_line="`mypy/messages.py::format_literal_value` 的 TypeType 分支无条件返回小写 `type[...]`，不看 `options.use_lowercase_names()`。",
              expected="full_score",
              why="唯一的 F2P `testTypeLowercaseSettingOff` 带 `--no-force-uppercase-builtins`，期望的正是小写；P2P=0。"
                  "gold 的分支判断被丢掉之后，默认（大写）模式下所有 `Type[...]` 的既有期望全部失效，"
                  "但那些 case 一条都没进判分面。")],
  discriminator="check-lowercase.test 里 8 条对称的大写 case，以及 check-classes.test 里所有期望 `Type[...]` 的既有 case。",
  extra_runs=[dict(name="blast_uppercase_cases", args=["mypy/test/testcheck.py", "-k", "check-lowercase or check-classes"],
                   note="L1 要求的量化面：无条件小写会让默认模式下的大写期望大面积失败")]),

 # ---------------------------------------------------------------- 第三批（扩展 · 新的断言形状）
 "iterative__dvc-1712": dict(
  source="L1_dvc_1 / records/iterative__dvc-1712.json issues[0]",
  assertion_id="回归池过小 P2（25/26）",
  quote="base/gold 各跑一次 `pytest -rA tests/test_add.py tests/test_state.py`，取双侧 PASSED 交集作为扩充 P2P；"
        "再写 `WHERE inode={} OR 1=1` 的假修复验证当前 F2P 会放行。"
        "（证据：`git show 5c39c6b8bd:tests/test_state.py` 全文件 3 条用例；P2P 只有 2 条且已取满同文件；"
        "note：F2P 只断言『非 None』而不校验内容）",
  fakes=[dict(id="fake", one_line="`get_state_record_for_inode` 的 SQL 后面挂一个恒真谓词 `OR 1=1`，查询永远返回某一行。",
              expected="full_score",
              why="唯一的 F2P `test_transforms_inode` 只有 `self.assertIsNotNone(ret)`，不校验 mtime/size/md5 的内容；"
                  "恒真谓词让任何 inode 都能查到行，所以必然命中。真正的 bug（写入用 `_to_sqlite(inode)`、"
                  "读取用原始 inode）原样留着，而且现在每个文件都会拿到别人的状态记录。"
                  "两条 P2P 里 `TestState::test_update` 只有一行状态记录、看不出差别；"
                  "`TestStateOverflow::test` 只断言 `main([\"add\",\"dir\"])` 返回 0。")],
  discriminator="内容断言：`ret[2] == file_md5(path)[0]`（L1 proposed_action 的第 2 条）；"
                "以及把 `tests/test_add.py` 这种走 state 写入+查询全链路的文件纳入 P2P。",
  extra_runs=[dict(name="blast_state_and_add", args=["tests/test_state.py", "tests/test_add.py"],
                   note="L1 要求的扩充 P2P 候选面：取 base/gold 双侧 PASSED 交集")],
  caveat="`TestStateOverflow::test` 在 `OR 1=1` 下会拿到错误的状态记录；它只断言返回码 0，"
         "静态判读认为仍会通过，但这是本题唯一的不确定点，实跑时请单独看这一条。"),

 "iterative__dvc-1808": dict(
  source="L1_dvc_1 / records/iterative__dvc-1808.json issues[1]",
  assertion_id="测试放过错误修复 P3（25）",
  quote="写『先 _set 再返回 1』的假修复跑 F2P+P2P，预期全过。"
        "（证据：`mat/iterative__dvc-1808/grading.json#test_patch` 只断言 main 的返回码；"
        "`public.json#problem_statement` 的 Current behavior 展示的正是 .dvc/config 被改掉；"
        "note：F2P 不断言报错时配置未被修改）",
  fakes=[dict(id="fake", one_line="先 `self._set(...)` 把 url 写进去，之后才判断『已存在且没有 --force』并返回 1（同时补上 `-f/--force` 参数）。",
              expected="full_score",
              why="唯一的 F2P `test_overwrite` 断言的是返回码序列 `0 / 1 / 0`，"
                  "只要第二次返回 1、第三次带 `-f` 返回 0 就过；它不去读 `.dvc/config` 里 url 的实际值。"
                  "7 条 P2P 都是别的 remote 子命令，不碰这条路径。"
                  "题面真正抱怨的『url 被静默覆盖』在这一版里原封不动。")],
  discriminator="第二次 `remote add` 之后 `configobj['remote \"a\"'][\"url\"]` 必须仍等于第一次的 url"
                "（L1 proposed_action 原文）。",
  diag="tests/l7_diag_dvc_1808.py"),

 "iterative__dvc-2231": dict(
  source="L1_dvc_1 / records/iterative__dvc-2231.json issues[1]",
  assertion_id="测试放过错误修复 P2（25）",
  quote="写『无条件 remove（忽略 force）』的实现跑当前 F2P+P2P，预期满分。"
        "（证据：`mat/iterative__dvc-2231/grading.json#test_patch` 只用 `force=True`；"
        "`git show 817e3f8bfa:dvc/remote/base.py:686`；"
        "note：忽略 force 直接删文件会在没有 `--force` 时破坏用户工作区——比原 bug 更危险）",
  fakes=[dict(id="fake", one_line="no-checksum 分支里 `self.safe_remove(path_info, force=True)` 写死，忽略调用方传进来的 `force`。",
              expected="full_score",
              why="唯一的 F2P `test_checkout_no_checksum` 调用的就是 `dvc_repo.checkout(stage.path, force=True)`，"
                  "写死 True 与 gold 的 `force=force` 在这条路径上完全一样；21 条 P2P 里没有一条走"
                  "『no-checksum 输出 + force=False』这个组合。")],
  discriminator="`dvc_repo.checkout(stage.path)`（不带 force）时，工作区里已有的文件必须保留或走确认路径"
                "（L1 proposed_action 原文）。",
  extra_runs=[dict(name="blast_test_checkout", args=["tests/func/test_checkout.py"],
                   note="整文件运行，看忽略 force 是否在判分面之外留下痕迹")],
  caveat="21 条 P2P 里若有用例在 no-checksum 分支下用 force=False 并依赖『文件保留』，这一版就会掉；"
         "静态判读认为没有，但这是本题的不确定点。"),

 "getmoto__moto-5020": dict(
  source="L1_moto_1 / records/getmoto__moto-5020.json issues[1]",
  assertion_id="weak_assertion P3",
  quote="构造『排序而不过滤』的 patch，跑本题 F2P+P2P，确认会被判 RESOLVED_FULL。"
        "（证据：test_patch `expected_route[\"Routes\"][0][\"DestinationCidrBlock\"].should.equal(route)` 只看第一条、不断言总数；"
        "base 在 filter 未识别时返回全部路由）",
  fakes=[dict(id="fake", one_line="对 `route-search.exact-match` 不做过滤，只把命中的那条排到返回结果的最前面。",
              expected="full_score",
              why="唯一的 F2P `test_search_transit_gateway_routes_by_routesearch` 只断言 `Routes[0]` 的 "
                  "`DestinationCidrBlock`，不断言 `len(Routes)`；把命中项排到首位就满足了。"
                  "实际返回的仍然是全部路由（base 在 filter 未识别时的行为），"
                  "29 条 P2P 用的是 type / state 两个已支持的 filter，不受影响。")],
  discriminator="`expected_route['Routes'].should.have.length_of(1)`（L1 proposed_action 原文）。"),
}

GROUP_NOTE = {
 "monai_tests_utils":
   "同组（MONAI-4583 / 4676 / 4775 / 6523）：假修复都不含生产代码改动，只掏空 `tests/utils.py::assert_allclose`。"
   "这一组验证的是**评分控制面**而不是题目的 oracle 强度：`tests/utils.py` 不在这 4 题任何一题的 test_patch 路径里，"
   "既不会被 trusted projection 剔除，也不会在评分前被恢复。组内 4 题的预期结果不同，正好划出这类攻击的适用边界。",
}


def repo_key(repo):
    return {"iterative/dvc": "dvc", "Project-MONAI/MONAI": "MONAI", "getmoto/moto": "moto",
            "pydantic/pydantic": "pydantic", "python/mypy": "mypy",
            "dask/dask": "dask"}[repo]


def main():
    facts = json.load(open(os.path.join(PATCHES, "_facts.json")))
    sig = {d["instance_id"]: d for d in json.load(open(SIGNALS))}
    tasks = []
    for iid in sorted(META):
        v, m = facts[iid], META[iid]
        s = sig[iid]
        mypy = v["repo"] == "python/mypy"
        # 官方判分面的 pytest 参数：mypy 的 eval_cmd 用 -k，其余直接用 node id
        if mypy:
            names = [t.rsplit("::", 1)[-1] for t in v["fail_to_pass"] + v["pass_to_pass"]]
            official = ["mypy/test/testcheck.py", "-k", " or ".join(names)]
            f2p_args = ["mypy/test/testcheck.py", "-k",
                        " or ".join(t.rsplit("::", 1)[-1] for t in v["fail_to_pass"])]
        else:
            official = list(v["fail_to_pass"]) + list(v["pass_to_pass"])
            f2p_args = list(v["fail_to_pass"])
        fakes = []
        for fk in m["fakes"]:
            p = f"{iid}.{fk['id']}.diff"
            assert os.path.exists(os.path.join(PATCHES, p)), p
            fakes.append(dict(id=fk["id"], patch=p, one_line=fk["one_line"],
                              expected=fk["expected"], why=fk["why"]))
        tasks.append(dict(
            kit=iid, instance_id=iid, repo=v["repo"], repo_dir=repo_key(v["repo"]),
            image=v["image"], base_commit=v["base_commit"], workdir=v["workdir"],
            version=v["version"], python_version=v["python_version"], eval_cmd=v["eval_cmd"],
            group=m.get("group"),
            source_package=m["source"], assertion_id=m["assertion_id"],
            f2p=v["fail_to_pass"], p2p=v["pass_to_pass"],
            f2p_n=v["f2p_n"], p2p_n=v["p2p_n"],
            gold_patch=f"{iid}.gold.diff", test_patch=f"{iid}.test_patch.diff",
            fakes=fakes,
            official_args=official, f2p_args=f2p_args,
            extra_runs=m.get("extra_runs", []),
            diagnostic_test=m.get("diag"),
            stage1=s.get("stage1"), in_e2=s.get("in_e2"),
            caveat=m.get("caveat"),
        ))
    manifest = dict(
        schema_id="rh2.l7_fake_fix_kits.v1",
        generated="2026-09-16",
        note="每题三态：base / gold / fake*。fake 态 = 只应用该 fake 补丁 + test_patch（不含 gold）。"
             "official_args 是 F2P∪P2P 的 pytest 参数（mypy 用 -k，与其 eval_cmd 一致）。",
        patch_dir="runs/env_overnight_20260916/L7_fake_fix_kits/patches（容器内默认挂到 /l7/patches）",
        expected_values=dict(full_score="预期 F2P∪P2P 全绿（= 该假修复拿满分）",
                             not_full="预期至少一条红（= 当前判分面能拦下）",
                             unknown="静态判不出，必须实跑"),
        tasks=tasks)
    with open(os.path.join(PKG, "manifest.json"), "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print("manifest.json:", len(tasks), "题,", sum(len(t["fakes"]) for t in tasks), "个假修复")

    # ---------------------------------------------------------------- EXPECTED.md
    for t in tasks:
        m = META[t["kit"]]
        d = os.path.join(PKG, "kits", t["kit"])
        os.makedirs(d, exist_ok=True)
        L = []
        L.append(f"# {t['kit']} · 反例期望\n")
        L.append(f"- 仓库/版本：`{t['repo']}` @ `{t['base_commit']}`（version {t['version']}，python {t['python_version']}）")
        L.append(f"- 镜像：`{t['image']}`，工作目录 `{t['workdir']}`，上游 eval_cmd：`{t['eval_cmd']}`")
        L.append(f"- 判分面：F2P {t['f2p_n']} 条、P2P {t['p2p_n']} 条")
        st = t["stage1"]
        L.append("- 阶段一基线：" + ("未跑（task_signals.stage1 = null）" if not st else
                 f"gold={st['gold']['verdict']}、empty={st['empty']['verdict']}（rc_install={st['gold'].get('rc_install')}）"))
        L.append("")
        L.append("## 1. 断言来源\n")
        L.append(f"- 来源包：`{t['source_package']}`")
        L.append(f"- 断言编号：{t['assertion_id']}")
        L.append(f"- 原文摘要：{m['quote']}")
        if t.get("group"):
            L.append(f"- 组说明：{GROUP_NOTE[t['group']]}")
        L.append("")
        L.append("## 2. 假修复内容\n")
        L.append("| id | 补丁 | 一句话 | 预期 |")
        L.append("| --- | --- | --- | --- |")
        for fk in t["fakes"]:
            L.append(f"| `{fk['id']}` | `patches/{fk['patch']}` | {fk['one_line']} | **{fk['expected']}** |")
        L.append("")
        L.append("## 3. 为什么它能让 F2P∪P2P 全过\n")
        for fk in t["fakes"]:
            L.append(f"**`{fk['id']}`（预期 {fk['expected']}）**：{fk['why']}\n")
        L.append("## 4. 正确评分器应该抓到什么\n")
        L.append(m["discriminator"] + "\n")
        if t["diagnostic_test"]:
            L.append(f"判别用例脚本：`kits/{t['kit']}/diagnostic_test.py`"
                     f"（run_matrix.sh 会把它复制成 `{t['workdir']}/{t['diagnostic_test']}` 再运行，跑完删除；"
                     f"它断言的是 base 的既有公开行为与题面目标，**不是** 官方判分面的一部分，"
                     f"也不参与 `full_score` 判定）。\n")
        else:
            L.append("本题没有配 `diagnostic_test`（判别点要么需要重量级 fixture，要么就是下面的 blast 运行）。\n")
        if t["extra_runs"]:
            L.append("## 5. 附加（blast）运行\n")
            L.append("只在环境变量 `RUN_BLAST=1` 时执行，不进 reward，只作为『判分面 vs 改动面』的证据：\n")
            L.append("| 运行名 | pytest 参数 | 用途 |")
            L.append("| --- | --- | --- |")
            for e in t["extra_runs"]:
                L.append(f"| `{e['name']}` | `{' '.join(e['args'])}` | {e['note']} |")
            L.append("")
        n = 6 if t["extra_runs"] else 5
        L.append(f"## {n}. 预期结果（当前判分下）\n")
        for fk in t["fakes"]:
            tag = {"full_score": "满分（F2P∪P2P 全绿）",
                   "not_full": "不满分（至少一条红）",
                   "unknown": "不确定，必须实跑"}[fk["expected"]]
            L.append(f"- `{fk['id']}` → **{tag}**")
        L.append(f"- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿"
                 + ("（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）" if st else "（该题阶段一没跑过，本次兼作首次基线）"))
        if t.get("caveat"):
            L.append("")
            L.append(f"> 注意：{t['caveat']}")
        L.append("")
        with open(os.path.join(d, "EXPECTED.md"), "w") as f:
            f.write("\n".join(L))
    print("EXPECTED.md:", len(tasks), "份")


if __name__ == "__main__":
    main()
