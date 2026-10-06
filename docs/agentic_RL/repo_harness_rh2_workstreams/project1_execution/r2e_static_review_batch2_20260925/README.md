# R2E 静态审查：第二批 12 道无已知线索的题（2026-09-25）

Claude（B 线，R2E 协调）。承接[首批 8 题](../r2e_static_review_20260925/README.md)与 [Codex 复核](../r2e_static_actor_review_20260925/README.md)。**用户 09-25 上午决定**：有问题的题先不做内容修订，继续审剩下的题；第二批审 12 道无已知线索的题；先做口径修正、两道探针候选的后检脚本、新提示材料，再派发；R1 与审题并行修。本线程只做协调、材料、执行核对与修复，不担任审查角色；公开读者、主审、复核者都是不继承本对话的新会话（Opus），并发上限 6。

## 1. 选题

从 21 道"无已知线索"的题中按仓库均衡取 12 道。"无已知线索"是指：期望全 PASSED，没有材料修订，也没有环境或资源配方。首批 8 题里有 6 道是专门挑的已知问题题，不是随机样本。这一批用来补充可用题的供应，也用来看普通题上的真实问题率。两类题分开统计，不合起来估计全池缺陷率。

| 题 | 本题修复或目标测试出现在同仓哪些题的公开工作树里 | 本题工作树包含同仓哪些题的修复或目标测试 |
| --- | --- | --- |
| aiohttp `1c1c0ea3` | `22a12cc2`（码测） | `240da100`（测）、`4075c653`（测） |
| aiohttp `22a12cc2` | — | `1c1c0ea3`（码测）、`240da100`（测）、`4075c653`（测） |
| coveragepy `97997d2c` | `ea6906b0`（码测） | `016af5f6`（码测）、`5dbbe143`（码测） |
| coveragepy `ea6906b0` | — | `016af5f6`（测）、`5dbbe143`（码测）、`97997d2c`（码测）、`f5eb5f21`（码） |
| datalad `19f5b450` | — | `58ba5165`（码） |
| numpy `5e8301c2` | `43e333e2`（码）、`d89bc4bb`（码） | `18b7cd9d`（码）、`2f4a9650`（码测）、`a5ea773e`（测）、`d805e9b6`（码） |
| numpy `a5ea773e` | `18b7cd9d`、`2f4a9650`、`43e333e2`、`5e8301c2`、`d805e9b6`、`d89bc4bb`（都是测；修复以重构后的形式存在，见下） | — |
| orange3 `4014f248` | `22e98f8f`、`50f6a758`、`c3fb72ba`、`f5026689`（都是码测） | `9b5494e2`（码测）、`f237f968`（码测） |
| pillow `3a61c9e9` | `f9d3ee0f`（码）；主审另核出 `a682ceaf`（逐字 77%，低于阈值） | `2b061b68`（码测）、`2d01f7d0`（码测）、`3ac9396e`（测）、`4bc64835`（码） |
| pillow `3ac9396e` | `2b061b68`、`2d01f7d0`、`3a61c9e9`、`4bc64835`、`a682ceaf`、`f9d3ee0f`（都是测） | — |
| scrapy `75450e75` | — | `9a15fcf8`（码）、`a95a338e`（码测）、`e9387529`（码测） |
| scrapy `e9387529` | `75450e75`（码测）、`a95a338e`（码测） | `9a15fcf8`（码） |

两份协调者机械比对合并，只是线索，也只是下限：
- "码"：[`cross_task_gold_scan.json`](../../../../../runs/r2e_static_prep_20260924/cross_task_gold_scan.json)。gold 新增的非平凡代码行（去注释、12 字符以上）在另一题公开工作树的同名文件里逐字出现 80% 以上。上游后来重构了修复时会漏报。
- "测"：[`cross_task_test_scan.json`](../../../../../runs/r2e_static_prep_20260924/cross_task_test_scan.json)（09-25 下午补）。本题隐藏测试里新增的测试函数名（本题工作树里没有的 `def test_*`）在另一题公开工作树里出现 80% 以上。修改已有测试时会漏报，同名巧合会误报。
- **协调者更正（09-25 下午）**：上午版本只用了"码"，numpy `a5ea773e` 两列都写成"—"。主审发现后，协调者核对了另 6 道 numpy 题的公开工作树：`numpy/lib/shape_base.py` 的 `tile` 里有本题修复的重构版本（注释逐字相同，代码改成 `all(x == 1 for x in tup)` 和 `return _nx.array(A, copy=True, ...)`），`test_tile_one_repetition_on_array_gh4679` 也都在。于是补了"测"这份比对。

合并后，全池 48 题里有 36 题的修复或目标测试出现在同仓至少一题的初态里（只看"码"是 32 题，只看"测"是 26 题），留出评测必须按仓库或时间划分。题面代码块与 gold 的逐行比对见 [`statement_gold_overlap_scan.json`](../../../../../runs/r2e_static_prep_20260924/statement_gold_overlap_scan.json)，本批 12 题都没有命中。

## 2. 流程与材料

流程与首批相同：公开读者 → 私有主审（先封存读历史前的初判，再开历史）→ 独立复核（先独立初判，再核主审）→ 真实环境开发核对 → 候选真实评分。改动如下：

| 项目 | 本批用法 |
| --- | --- |
| 材料 | v3：`runs/r2e_static_prep_20260924/v3/{public,private,history}/<iid>/`。与 v2 只差 48 题的 `public_bundle.json`（新提示）与 `environment_brief.md`（去掉"提示与镜像不符"一句）；verify 48/48 工作树、15/15 镜像一致 |
| 角色卡 | [公开读者](roles/public_reader_r2e.md)、[私有主审](roles/investigator_r2e.md)、[独立复核](roles/reviewer_r2e.md)。新增"第二批补充规则"：合理误拒逐个候选核语义；遵循冲突示例的候选单列；失败键相同不代表同样合理；候选写成可改补丁的描述；同仓跨题包含必查 |
| 环境 | [第二批环境卡](r2e_environment_card.md)：正式 actor 接线已实施（待 A 审），首批 8 题的真实启动事实 |
| 真实环境核对 | 公开读者落盘后，协调者按其建议命令跑 devcheck 与私有 gold 对照，再派主审；证据与首批同目录，在 `runs/r2e_actor_20260925/devcheck/<iid 前 40 字符>/`（`orig/` 为正式启动路径 + 真实 CC + 桩端点，`private_gold/` 为私有 gold 对照） |
| 派发记录 | [assignments.json](assignments.json) |

## 3. 结果（09-25 下午）

12 题的角色链都已走完：公开读者 → 主审（封存初判、历史对照、题卡、记录）→ 独立复核（初判、第二步）。另有真实启动链开发核对（devcheck）与候选真实评分。派发与完成逐会话记在 [assignments.json](assignments.json)，逐题产物在 `results/<instance_id>/`，评分与私有核对的运行事实在 [grader_candidates.md](grader_candidates.md)（81 次正式评分，都在 derived9 镜像上；其中 11 次是重复实验：aiohttp `1c1c0ea3` gold 同机并行 6 次、scrapy `75450e75` K2 重复 5 次）。以下"处置"都是 `static_review` 范围，不是训练或评测批准。

**题卡时点**：各题 `card.md` 与 `screening_record.json` 写于候选实跑之前，其中"待实跑""预期"是当时的推断。实跑结果以 grader_candidates.md 为准，主审与复核的对照在各题 `review.md`。

### 3.1 逐题

处置一栏全部是 `needs_review`（静态候选，待 actor 验证），用途都是开发诊断。复核对处置都同意，下表只写复核改动的要点。

| 题 | 主要问题（执行证据见 grader_candidates.md） | 复核改动的要点 | 待定 |
| --- | --- | --- | --- |
| numpy `5e8301c2` | 15 个目标键只测题面一例；只修一个方向的 C-C 得 1；**gold 本身不完整**：求和维度走 BLAS 仍报错，连 `np.einsum('i,i', [2., 3.], [4.])` 默认也报错（本 base 默认 `optimize=True`） | 精度修正：后续题的公开测试含本题断言（下标改名）；I1 只把 R3、R4 算覆盖缺口 | 是否补交换顺序断言（若补，gold / noop / C-C / C-A 预期 1 / 0 / 0 / 1） |
| coveragepy `97997d2c` | 目标测试只经 `Coverage` 包装、从空 `paths` 起步；W1（`CoverageConfig` 仍不认 `paths`）、W2（设的值不进 `combine()`）、M（合并而非替换）都得 1 | 主审的补测 REV1 堵不住 W2，审计口径应改用后检脚本；`coverage/backunittest.py` 是可被候选改动的测试依赖面 | 替换还是合并（用户）；是否补测 |
| orange3 `4014f248` | **合理修复被误拒**：只改 `.pyx` 的根因修复评分 0，root 构建后 27/27；评分不重建，**agent 在解题环境里也重建不了**（见 §3.2 第 3 条） | I2 更正：C3 在小量级数据下把 100 个值并成一个区间；若评分将来重建，须以 uid 54322 在候选测试阶段做 | 派生配方修 `sysconfig`；评分是否重建改动过的扩展（都需用户定） |
| aiohttp `1c1c0ea3` | Ctrl+C 后 cleanup 错误被静默吞掉的 C3 得 1（诊断脚本：错误丢失）；gold 由"报告"改为"抛出" | 时序键 `test_shutdown_handler_cancellation_suppressed` 维持 watch：源数据集裸机上失败过两次，本批同机并行 6 次 gold 都通过 | 是否补"抛出或报告二选一"的断言 |
| numpy `a5ea773e` | 唯一目标键只测 `reps=1` 的 1-D 输入；B、C 与复核者的 C2、C3 都得 1（元组 reps 仍共享内存、维度提升丢失） | 题卡里的检查项在实跑后已过时；N3 的引用行号应指向 `prepared_task_face.py:415-449` | 训练用途前由用户选：接受、修订或排除 |
| datalad `19f5b450` | 只断言退出码 3；K2（改回抛 `CommandError`，公开测试会失败）、K3（输入缺失时退出 0）、H（硬编码 3）都得 1 | stderr 约束两侧都有公开依据：K4 单列为"遵循一侧信号"的候选；失败在 L87 的 rollout 标疑似规格争议；补测可精简为三条 CLI 检查 | 是否补测 |
| pillow `3a61c9e9` | 只比较恒等映射后的 Python 层字节，且调用后才读原图；W1（GIF 保存坏）、W2（C 层丢 alpha）、W3（恒等短路）、W5（就地改坏原图）都得 1 | 检查项 32 改为 issue；补测须用字面量或调用前快照；7 道 pillow 题同侧划分 | 训练用途前是否补测 |
| scrapy `e9387529` | dict item 不生效的 C2 得 1；**gold 有未测回归**：`export_empty_fields` 缺字段、serializer 返回 int 时抛 `TypeError` | G3 归因修正（含非 str 键时 C1 也会抛）；C1 改认为合理替代解 | — |
| coveragepy `ea6906b0` | 只断言 `htmlcov/.gitignore` 存在：空文件（C-B）得 1；提前建目录的候选得 1，但破坏"无数据不建目录"（公开旧测试会 FAILED） | `encoding="utf-8"` 被测试替身拒绝（C-C 得 0），是仓库惯用写法，但公开测试同样暴露，原始 0 保留 | — |
| aiohttp `22a12cc2` | 题面误导（示例在构造时就报错，真实缺陷只在代理 CONNECT 路径）；**合理修复被误拒**：K2（不经 `_get_fingerprint`）与复核者 C（改用 `abort()`）真实握手与 gold 一致却得 0；K3（什么也没修）、K4（连正确指纹也拒）得 1 | "唯一硬约束"写法不准，测试替身本身也是约束；K1 附录 diff 不能直接 apply | 修订前本题 reward 不计入探针成功率，得 1 的补丁另跑代理场景核对 |
| scrapy `75450e75` | 目标测试只查退出码与一句报错；掩盖型 K3 得 1；**gold 有缺陷**：协程排在不运行的循环上，槽位不空闲，`SCRAPER_SLOT_MAX_ACTIVE_SIZE=1000` 时第二次 fetch 超时挂起 | "测试过宽"最有力的证据是 gold 挂起仍得 1；题面提示会把解题者引向 gold 的做法 | 可选 E3（async 中间件下对比 base / gold / K1 / K3） |
| pillow `3ac9396e` | 题面把原因说成"零分母"，非零分母同样失败；只修零分母的 K2、只登记 41988 的 K4b、把 int 也当有理数的 C6 都得 1；gold 顺带把未注册整数的类型码从 LONG 改成 SHORT | C6 是错误实现而非部分实现，检查项 25、26 升为实跑证据；K2 只是特例，不能说与题面一致；libtiff 相关的 ERROR 成因未核实；撤回自己"补非零分母测试"的建议（会让 K2 得 0，需先改题面） | 若补测防 C6，要断言 `type(v[0]) is int`（`IFDRational(5, 1) == 5` 为真，等值比较分不开） |

### 3.2 本批的共性结论

1. **测试偏宽是普遍问题**：12 题每题都有至少一个错误或不完整的候选实跑得 1。原始 reward 只能说明题面那一例修好了。这些题用于诊断或探针时，得 1 的补丁要配本题的语义核对（grader_candidates.md §2 的脚本与命令都可复用）；用于训练 reward 前要先决定是否补测。
2. **实测的合理误拒只有两题**：orange3 `4014f248`（交付层，见下条）与 aiohttp `22a12cc2`（测试与实现细节耦合，两个候选）。另有两处按公开约束单列、不算误拒：coveragepy `ea6906b0` 的 `encoding=`、datalad 的 stderr 约束。首批 6 道已知线索题里有 5 题出现误拒，两批分开统计，不合起来估全池。
3. **环境缺陷（B 线，已实测）**：派生镜像把解释器搬到 `/opt/py/...`，但 `sysconfig` 的 `LIBDIR` 仍指向 `/root/.local/share/uv/python/.../lib`，`/root` 对 agent 不可读，agent 身份下重建任何 C 扩展都在链接时报 `cannot find -lpython3.7m`。凡是自然修复落在编译代码里的题（orange3、pandas 的 `.pyx`，numpy、pillow 的 C 源码），agent 都无法在本地验证，交付后评分也不重建。修法属于环境配方与评分语义，本批按用户"先不修"只登记。
4. **gold 自身有缺陷或回归**：numpy `5e8301c2`（修不全）、scrapy `e9387529`（`TypeError` 回归）、scrapy `75450e75`（挂起）、pillow `3ac9396e`（整数类型码被改）。这些不影响正确候选得分，但探针里 gold 式的补丁得 1 不代表行为正确。
5. **同仓跨题包含**：两份机械比对合并后，全池 36/48 题的修复或目标测试出现在同仓别题的初态里（§1）。主审与复核又各补出机械比对漏掉的关系（numpy `a5ea773e` 被 6 题包含、pillow `3a61c9e9` 被 `a682ceaf` 包含、coveragepy `f5eb5f21` 与 `97997d2c` 初态相同）。留出评测按仓库或时间划分。

### 3.3 协调者自己的差错与更正（本批）

- **命令改写引入伪影**：生成 devcheck 命令时给 pytest 插了 `-p no:cacheprovider`，与 coveragepy 两题 `setup.cfg` 的 `--failed-first` 冲突，4 条命令以 rc=4 失败。两位主审都识别为伪影；已去掉该参数以 agent 身份重跑（`devcheck/*/plainpytest/`，全部 rc=0），生成脚本已改。
- **错误断言**：grader_candidates.md 上一版写"agent 可以自己构建并在本地看到测试通过"，依据是 base 上的 `build_ext`（源码没改，只复制已有 `.so`）。以 agent 身份实测改 `.pyx` 后重建，链接失败（§3.2 第 3 条），已在页内更正。
- **并发超限**：一次唤醒两位复核者给第二步材料，实际并发到 8（上限 6）；随即暂停这两位，有空位后再唤醒。之后每次派发或唤醒前按 assignments.json 计数。
- **跨题比对漏报**：上午的逐字代码比对漏掉了 numpy `a5ea773e` 被 6 题包含（上游重构了修复），已补测试名比对并更正 §1 的表。
- **其它**：numpy 行为核对第一次用了本 base 没有的 `np.shares_memory`，改用 `np.may_share_memory` 重跑；aiohttp `22a12cc2` 题卡附录里 K1 的 diff 行数不对、不能直接 apply，按同样改法重新生成；datalad H 的账本在复核读取时尚未回传本机，之后已补齐。
