# conan-io__conan-14177：第3类诊断结果

2026-09-29 / Claude（云端，第3类负责人）。原分类：第3类“公开目标与验收关系需核定”。

**结论：问题和修法已明确，建议转第2类。**

- 按统一标准 v1 的 R-b＋R-c 修订验收，用经独立核实的替代实现 `pubcand` 作正对照（v1 §9 D4）。
- 当前修订草案为 **v2**：按独立复核的 B1/B2 和 N1–N7 修改，15 个候选的诊断评分全部符合预期。
- 实施依赖 D6 **首片之后**的两项能力，见 §5。落地前，原版只作问题定位。

## 1．公开要求

题面标题是“Verbose option for apply_conandata_patches()”，给出签名 diff：`apply_conandata_patches(conanfile, verbose=False)`。`verbose=True` 时在构建日志中逐个记录应用的补丁文件，示例为 `zlib/1.2.13: Applying: patches/0001-Fix-cmake.patch`。

- 默认值是 False，所以省略参数时不新增这类日志。
- 题面没有要求改直接调用 `patch()` 的输出。
- 目标只有一种读法，不属于 P5。

## 2．实测结果

镜像 `xingyaoww/sweb.eval.x86_64.conan-io_s_conan-14177`，摘要 `sha256:e83f64f4…41db8`，与 ingest 冻结值一致；使用原材料，无派生配方。

- 私有对照：root、断网、一次性容器（`semantic_control.py`）。
- 正式评分：`replay_grade.py`，grader UID 54322、deny_all、2 CPU／4 GiB。

### （1）私有行为矩阵

两份真实文本补丁，第二份带不含文件名的描述；分别用四种方式调用。

| 版本 | 省略参数 | `verbose=False` | `verbose=True` | 位置参数 `True` |
| --- | --- | --- | --- | --- |
| base | 两份都应用；只有旧 backport 行 | `TypeError` | `TypeError` | `TypeError` |
| gold | 两份都应用；**默认新增** `Apply patch (file): patches/0001…`，第二份仍无文件名 | `TypeError` | `TypeError` | `TypeError` |
| 按题面实现的候选 `pubcand` | 与 base 相同 | 与 base 相同 | 两份文件名都记录，旧 backport 行保留 | 同 `verbose=True` |

补充说明：

- 三个版本都不修改输入 `conan_data`，文件内容也确实被改写。
- **gold 没有实现题面接口**，却改变了默认输出。
- 在 base 版公开旧测试 `test_patches.py` 上，gold 失败 3 项，`pubcand` 13/13 通过。
- 公开功能测试的窄选中，三版均为 7/7。

### （2）原材料正式评分

| 候选 | reward | F2P | P2P | 说明 |
| --- | --- | --- | --- | --- |
| noop | 0 | 0/3 | 10/10 | 与 09-19 历史一致 |
| gold | 1 | 3/3 | 10/10 | 与历史一致 |
| `pubcand`（按题面实现） | **0** | 0/3 | 10/10 | 失败见下 |
| `gold_log_only`（只打印、不应用补丁） | **1** | 3/3 | 10/10 | 退化候选：文件补丁根本没应用，仍得满分 |

`pubcand` 的三个 F2P 失败原因：

- `test_single_patch_description` 要求直接 `patch()` 输出 `(file)` 类型标签；
- 两个 multiple 测试要求省略参数的默认调用新增 `Apply patch (file): …` 行。

三处都与 `verbose` 无关。所有正式评分参考缺席 0，安装失败 0，测试段完整，两层清理成功。

## 3．判定（v1 §3–§4）

- **T2a（S1，§4 第 1 步）**：原测试没有任何 `verbose` 调用，题面核心要求没有断言。
- **P2／T1（已由正式评分确认）**：按题面实现的候选被判 0，gold 不支持 `verbose` 却得 1。测试锁定的是题面之外、与“默认关闭”相反的实现，即默认日志和 `patch()` 的 `(file)` 类型。
- **T2b（S1，§4 第 3 步）**：退化候选“只打印日志、不应用补丁”在原材料下得 1。原因是两个上层 F2P 只检查输出子串，mock 也不记录每份补丁是否应用。
- **G1**：gold 未交付题面接口，不能再作正对照。
- 题面本身正确，**不需要 R-f**。

## 4．修法（交第2类）：修订版测试草案 v2

### 草案文件

- 测试补丁：[`revised_test_v2.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/conan14177/revised_test_v2.patch)，sha256 `ee614041…2d8c`；
- 生成源：[`revised_tests_v2.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/conan14177/revised_tests_v2.py)＋`make_revised_test_patch_v2.py`；
- 父版本：v1（`51c9bd79…6a10`）。

测试编号与原 F2P 相同：

- `test_single_patch_description` 保持 base 原断言不动，等于撤销原 test_patch 对它的修改（R-b）；
- 两个 multiple 测试原位替换。

### 需求—断言依据表

| 断言 | 公开依据 | 拦下的错误候选 |
| --- | --- | --- |
| 直接 `patch()` 输出不变（base 原断言） | 题面只为 `apply_conandata_patches` 加开关；base 公开测试 `test_patches.py:118-124` | gold、`gold_log_only` |
| 省略参数与 `verbose=False` 的输出与 base 全等 | 题面签名 `verbose=False`，以及“when `verbose=True`”；base 公开测试 `:161-177、:208-214` 本来就是全等 | `always_log`、gold |
| `verbose=True` 时两份文件都能在带 `mocked/ref: ` 前缀的行中辨认，并按处理顺序出现；不锁定措辞 | 题面示例：带引用前缀、conandata 相对路径、逐补丁一行 | `never_log`、`output_verbose`、`probe_basename` |
| `verbose=True` 时原描述内容仍可见（只查内容，不要求整行一致） | 题面没有要求删除既有描述；base 输出惯例 | `print_only` |
| 第二个位置参数 `True` 也可用 | 题面签名原文 `def apply_conandata_patches(conanfile, verbose=False)`（非核心，见 §5） | `probe_kwonly` |
| 每次调用都真实应用所选补丁，路径与 `base_path` 不变（记录型 mock） | 函数文档“Applies patches…”；base 路径语义 `patches.py:54-68、95-102` | `probe_logonly_v` |
| 版本缺失时的断言不变；无补丁版本在 `verbose=True` 下不输出任何补丁名、不应用；匹配版本只记录并应用该版本的补丁；输入不被修改 | base 版本选择 `patches.py:83-94`；base 公开测试 `:206-217` | 版本范围错误类候选 |

### v2 正式诊断评分

使用 `replay_with_install_recipe.py --materials`，grader 后缀 `+c3-conan14177-public-verbose-v2`，F2P／P2P 名单不变。

| 候选 | reward | 说明 |
| --- | --- | --- |
| `pubcand`（正对照） | **1** | |
| `probe_post`（应用成功后才记录） | **1** | 合理变体 |
| `probe_abspath`（记录绝对路径） | **1** | 合理变体 |
| `probe_merged`（有描述时文件名并入描述行） | **1** | 合理变体，v1 曾误拒 |
| `probe_header`（verbose 时多打一行“选中 N 个补丁”） | **1** | 合理变体，v1 曾误拒 |
| noop | 0 | |
| gold | 0 | 原 gold 失败依 D4 记录 |
| `gold_log_only` | 0 | |
| `always_log` | 0 | 默认输出全等处失败 |
| `never_log` | 0 | |
| `print_only`（verbose 时只打印不应用） | 0 | |
| `output_verbose` | 0 | 边界，理由见下 |
| `probe_basename`（只记文件名，不含 `patches/` 路径） | 0 | |
| `probe_kwonly`（仅关键字参数） | 0 | 位置参数调用处失败，边界 |
| `probe_logonly_v`（接受参数、各模式日志都对、复现描述行，但从不应用） | 0 | **两处失败都只在 `_applied(...)` 断言**，证明修正 T2b 的断言独立起作用 |

所有评分参考缺席 0，清理成功。

### 两处边界判断（写明，供 Codex 复核）

- **`output_verbose` 判为不满足**，理由有两条：
  - `ConanOutput` 默认等级为 status，`verbose()` 输出在默认构建日志中不可见，这与“recorded in the build log”的目的冲突；
  - 题面示例的上下文行都是默认等级可见的输出。示例未写命令行，是否带 `-v` 属于推断。
- **位置参数**：依据是题面签名原文，不是核心要求。如 Codex 认为不应因此判 0，删除这一处调用即可，其余断言不受影响。

### 交接给第2类

1. D6 落地所需的首片之外能力，见 §5；
2. 独立 reviewer 已核实 `pubcand` 可作替代正对照（见复核）；
3. 正式版本复验上表：正对照及合理变体为 1，其余为 0；
4. Codex 复核修订。

## 5．依赖与当前用途

D6 实施说明（`category2_repair_20260929/d6/implementation_brief.md`）写明，首片“不接受测试替换操作”“不删原参考、不改原分组”；测试补丁替换排在 MONAI5932 之后的下一切片。本题需要其中两项：

- **整段替换 test_patch**；
- **参考分组调整**：`test_single_patch_description` 在 base 上已经通过，正式版本宜从 F2P 改记 P2P。如果后续切片也不支持改分组，需要明确登记“保留在 F2P、base 上已通过”的例外，不能静默处理。

这两项落地并验收前：本题原版**只作问题定位**，不进入能力比较分母和训练；照题面做会得 0，不能用事后审计豁免。

## 6．独立复核（已完成）

独立复核结论为“部分同意”，文件见 [review_initial.md](review_initial.md)（先于读作者材料封存）和 [review.md](review.md)。

- **同意**：分类与方向、全部实测数字；`pubcand` 可作替代正对照。
- **阻断项与处理**：

  | 阻断项 | 内容 | 处理 |
  | --- | --- | --- |
  | B1 | 无补丁版本在 verbose 下必须空输出，这一约束无公开依据 | 已删除，`probe_header` 现为 1 |
  | B2 | 缺少单独证明 `_applied` 断言有效的候选 | 已补 `probe_logonly_v`，正式评分只在 `_applied` 处失败 |
  | B3 | 交接未写 D6 首片之外的依赖 | 已写入 §5 |

- **非阻断项**：
  - N1：verbose 下只查描述内容，已采纳；
  - N2：位置参数边界，已写明；
  - N3：依据表，已补；
  - N4：T2a，已补；
  - N5：措辞，已改；
  - N6：`output_verbose` 理由，已写全；
  - N7：原位替换，已采纳。

v2 由复核者再做一次聚焦复核的安排，见本目录 README 记录。

## 7．未做与剩余事项

- 真实 actor 开发条件（UID 54321、激活环境、写权限）本次未验。
- 跨题关系：Conan15422 的 base 含本题 gold 的默认日志写法。修订后的答案是 `verbose` 参数，不在该 base 中，原线索影响减弱；未另行核对。
- `patch_string` 在 verbose 下是否要记录，题面未规定；修订版不作断言。
- 本题没有模型求解证据。

## 8．版本与证据

- 代码与运行环境见 [环境说明](../../environment.md)。评分路径与已提交 `a31cdcd` 逐字相同。
- 候选补丁在 `rh2/experiments/category3_cloud_20260929/conan14177/`，其中 `pubcand` 的 sha256 为 `22906325…a2f8`。
- 原始证据在 [evidence/](evidence/)，包括：
  - 原材料评分：`ledger_*.jsonl`、`eval_logs/`；
  - 修订版评分：`formal_revised_v1/`、`formal_revised_v2/`；
  - 私有矩阵：`semantic_v2/`、`revised_matrix_v1/`；
  - 云端首次复现：`calibration/`；
  - 全部文件的 SHA256：`evidence_manifest.json`。
