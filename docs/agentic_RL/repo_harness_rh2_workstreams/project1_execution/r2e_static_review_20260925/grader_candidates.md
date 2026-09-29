# R2E 首批：主审与复核提出的候选，真实评分结果（2026-09-25）

Claude（B 线 R2E 协调者）执行。本页回答主审与复核留下的"最小后续实验"：用与正式评分同一套 RH2 回放代码，在当前派生镜像上给候选评分，每个候选跑 1 次。**本页只记运行事实**，处置以各题 `card.md` 与 `review.md` 为准。

补丁由协调者按题卡与复核里的描述写成，都只改库源码，不碰测试或 conftest（账本 `candidate_touched_conftest_or_fixture` 均为空）。每个补丁都是在公开工作树的基础上改写，用 `git diff` 导出。

- **机器**：A 线借给 B 线的 CPU 机（x86_64），代码与 [actor 核对](actor_devcheck.md) 是同一快照。
- **材料与镜像**：
  - pandas 与 orange3 `9b5494e2` 用 `prepared_a` 与 `derived7`（`+material_v2` / `+env_v2`）；
  - coveragepy、pillow、aiohttp、numpy 用 `prepared_b` 与今晚新建的 `derived8`；
  - 新建镜像上的四处 gold 对照都得 1，与环境阶段的评分一致。
- **证据**：本机 `runs/r2e_actor_20260925/grader/`。
  - `ledger_<标签>.jsonl`：账本；
  - `eval_logs/`：评分日志；
  - `cands/*.patch`：候选补丁；
  - `pillow_fresh/`：新进程打开检查；
  - `aiohttp_c2c3/`：aiohttp 候选的 C2 / C3 检查；
  - `numpy_probe/`：numpy 候选的行为探针；
  - `orange3_mcve/`：orange3 V1 / V3 下的题面原例。

| 题 | 候选（补丁） | 预期（来源） | 实测 reward（期望键匹配） | 不符的键 |
| --- | --- | --- | --- | --- |
| pandas `32dd55cb` | C1：`blk_func` 只对数值 EA 调 `values._reduce`，其余同 base（`pandas_32dd_C1_numeric_ea_only.patch`） | 0（主审、复核） | **0**（91/92） | `test_mean_datetimelike_numeric_only_false`（T2） |
| coveragepy `5dbbe143` | gold | 1 | 1（75/75） | — |
| 同上 | CE1：`once=True` 按消息去重 | 0（主审、复核） | **0**（74/75） | `ApiTest.test_warn_once` |
| 同上 | CE3：`once=True` 按 slug 去重（独立集合，正对照） | 1 | 1（75/75） | — |
| 同上 | CE4：第一次 `once` 之后，所有 `once` 警告都不显示（过粗） | 1（漏测） | **1**（75/75） | — |
| pillow `2b061b68` | gold | 1 | 1（55/55） | — |
| 同上 | P1：列出的格式都不匹配时，回退到全部格式 | 0（主审） | **0**（54/55） | `TestImage.test_open_formats`（DID NOT RAISE `UnidentifiedImageError`） |
| 同上 | P2：`formats is None` 时取 `list(ID)` 快照（取在 `preinit()` 之前） | 1（复核 N2） | **1**（55/55） | — |
| 同上 | P3：gold，再让无参 `show()` 发 DeprecationWarning | 1（主审、复核） | **1**（55/55） | — |
| aiohttp `61833518` | gold | 1 | 1（47/47） | — |
| 同上 | AP1：只在 `_write_length_payload` 跳过空块（部分修复） | 1（主审：漏测） | **1**（47/47） | — |
| 同上 | AP2：两个写出器（`_write_length_payload`、`_write_chunked_payload`）都跳过空块 | 1 | 1（47/47） | — |
| orange3 `9b5494e2`（`+env_v2`） | P1：默认 `solver="auto"`，在 `__init__` 里就按 l1→liblinear、其余→lbfgs 解析 | 1（主审） | 1（13/13） | — |
| 同上 | P2：gold，再加 elasticnet→saga | 1（主审） | 1（13/13） | — |
| 同上 | V1：保留默认 lbfgs，只在 l1 且 lbfgs 时改 liblinear（`orange3_9b54_OR1_…`） | 0（主审、复核） | **0**（12/13） | `test_auto_solver` |
| 同上 | V3：同 gold，但 l1 选 saga（`orange3_9b54_OR2_…`） | 0（主审、复核） | **0**（12/13） | `test_auto_solver` |
| 同上 | V4：默认 "auto"，在 `fit` 里解析 | 0（主审） | **0**（12/13） | `test_auto_solver` |
| 同上 | V5："auto" 用映射表（`penalty=None` 查不到） | 0（主审） | **0**（12/13） | `test_auto_solver` |
| 同上 | V7：只把默认 solver 改成 liblinear | 0（主审；另看 scorer 两键） | **0**（10/13） | `test_auto_solver`；**两个 scorer 键翻成 PASSED**（期望 FAILED） |
| 同上 | W1：gold，但 l1 静默改成 l2 | 0（主审） | **0**（12/13） | `test_auto_solver` |
| 同上 | G1：gold，再把默认 `multi_class` 改成 `"ovr"`（复核提出的条件实验） | 看 scorer 两键 | 1（13/13） | —（两个 scorer 键仍 FAILED，与期望一致） |
| numpy `18b7cd9d` | gold | 1 | 1（11/11） | — |
| 同上 | A：`__eq__` 对非 poly1d 返回 False | 1（主审） | 1（11/11） | — |
| 同上 | D：只让 `__eq__` 返回 NotImplemented，`__ne__` 不改 | 0（主审、复核） | **0**（10/11） | `test_poly_eq`（`p != None` 得 False） |
| 同上 | N：只特判 `other is None` | 1（主审：蒙混） | **1**（11/11） | — |
| 同上 | I：删掉 `__eq__` 与 `__ne__`，退回身份比较 | 1（主审：蒙混） | **1**（11/11） | — |

**P2 的新进程检查**：用 `private_control.py` 在同一派生镜像的一次性容器里应用 P2，root 身份，不联网。

| 条件 | 新进程里第一次 `Image.open('Tests/images/hopper.png')` | 同样打开 `hopper.tif` |
| --- | --- | --- |
| P2 | `UnidentifiedImageError` | `UnidentifiedImageError` |
| gold | `PNG` | `TIFF` |

P2 让不传 `formats` 的普通调用在新进程里全部失败，评分仍给 1。评分测不到这一点，是因为评分进程里其它测试先触发了插件加载。

**aiohttp 的标题场景检查**：用同一方式应用候选，再跑公开读者写的 C2（题面配置，查每次 `transport.write`）和 C3（无 Content-Length，走 chunked 写出器，查正文开头是否就是终止块 `0\r\n\r\n`）。

| 条件 | C2（空写入） | C3（提前终止块） | 公开 `test_http_protocol.py` |
| --- | --- | --- | --- |
| AP1 | 无空写入 | **仍以终止块开头** | 全过 |
| AP2 | 无空写入 | 正常 | 全过 |
| gold | 无空写入 | 正常 | 全过 |

AP1 修掉了题面示例，没修标题说的提前 EOF，评分仍给 1：隐藏测试没有覆盖"压缩在后 + chunked"这条路径。

**numpy 的行为探针**：主审给的 `print(p==None, p!=None, p==3, p==P([1,2,3]))`，同样在一次性私有容器里应用候选后运行。正确修复应输出 `False True False True`。

| 条件 | 输出 |
| --- | --- |
| gold | `False True False True` |
| A | `False True False True` |
| D | `False False False True`（`p != None` 错） |
| N | `p == 3` 抛 `AttributeError` |
| I | `False True False False`（系数相同的两个 poly1d 不再相等） |

N 与 I 都是错的实现，评分给 1：隐藏测试只比较了 `None`，只比较了同一对象与系数不同的对象。D 得 0 是应得的（`!=` 的结果错了），但题面没提 `!=`。

**orange3 `9b5494e2` 的 V7**：把默认 solver 改成 liblinear 后，期望为 FAILED 的 `test_learner_scorer`、`test_learner_scorer_multiclass` 翻成 PASSED。说明这两键失败是因为默认 solver 从 liblinear 换成了 lbfgs，与主审"上游测试期望过时"的解释一致；也说明它们会惩罚改回 liblinear 默认值的修复。G1（只改 `multi_class`）下两键仍 FAILED，所以翻转与 solver 有关，与 `multi_class` 无关；复核提出的"只改 scorer 所用模型"一类候选没有跑。

## 读法

- **合理修复被判 0（评分已测）**：pandas C1、coveragepy CE1、orange3 `9b5494e2` 的 V1 / V3 / V4 / V5，共 6 个。orange3 V1 / V3 实测修好了题面原例；V4 / V5 与 pandas C1 能否修好题面原例是代码推断。V7（默认改 liblinear）也得 0，是否算合理修复有争议，不计入。
- **遵循冲突示例的候选被拒（单列）**：pillow P1。题面一处要求 `formats` 限制格式，另一处要求 PNG 配 `['JPEG']` 能打开；P1 符合后一句、违反前一句，也没实现 `show()` 警告，不能算完整满足题面的修复（Codex 复核 R3）。它证明的是题面自相矛盾。
- **失败位置相同，不等于同样合理**：orange3 W1 与 V1 都只错 `test_auto_solver`（12/13），但 W1 把用户指定的 L1 静默换成 L2，是错误修复。所以诊断时失败键模式只用来筛出待复核的样本，要核实候选语义后才标"合理误拒"，原始 reward 保留（Codex 复核 R2）。
- **漏测已由执行证实**：
  - aiohttp AP1 只修了题面示例的路径，标题说的提前 EOF 仍在，仍得 1；
  - coveragepy CE4 过粗，仍得 1；
  - numpy N（只特判 None）与 I（退回身份比较）都是错的实现，仍得 1；
  - pillow P2 在新进程里打不开任何图片，仍得 1；
  - pillow P3 做了公开测试本想禁止的改动，仍得 1，原因是那两条期望 FAILED 的测试在 `pytest.warns(None)` 处就失败，后面的断言都不执行。
- **适用范围**：以上是评分侧事实，只说明这些实现在当前材料下的得分，不说明模型会写出哪种实现。各题的修订草案（改题面、放宽断言、补断言）是否采纳由用户决定；采纳后要在修订版材料上重跑同一批候选，确认误拒与漏测都已消除。
- **尚未跑**：
  - scrapy 的修订 B 验收（需先有修订版材料）；
  - pandas 的 C2 至 C4。
