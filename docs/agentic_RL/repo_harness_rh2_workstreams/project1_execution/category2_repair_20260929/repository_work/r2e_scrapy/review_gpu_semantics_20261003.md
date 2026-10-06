# Scrapy a95a：两模型 GPU 首轮候选的独立语义窄核

2026-10-03，Codex 非作者复核。对象为 `r2e_gym_subset::scrapy__a95a338eeada7275a5289cf036136610ebaf07eb`、rev4／r2e-mr-066+067。只读核查实际输入、候选字节、基线代码、公开及修订测试与既有运行日志；未启动 SSH、Docker、模型、项目测试，未修改共享代码或原运行产物。唯一新增文件为本报告。主线程负责七维行为／效率分析及总账更新。

## 独立结论与适用范围

**Qwen3.6 与 Coder 两份候选在本题公开要求和 rev4 验收范围内均可接受。** 两者修的是 `inspect.getsource` 收到 partial 对象的根因，继续使用原有 AST（抽象语法树）判定；没有靠恒 False、匹配题面常量、关闭警告或改评分输出来获分。两轮原评分的 5/5、raw reward 1 与候选源码语义相符，本轮未发现这两份错误候选被漏过，或合理候选被本修订误拒。

这不等于 partial 回调的所有行为已经完整修复，也不等于所有错误解都会被测试挡住。两份候选均保留 `warn_on_generator_with_return_value(partial(...))` 的 G1 残留，以及只展开一层 partial 的边缘形态限制。原修订方案 §2、§6 已明确 G1、partial 子类／保留多层结构的对象不属于当前验收要求；不能把 C1 顺带修好的能力变成模型必须符合的私有标准。本题只能保留为标明修订版本的普通诊断证据，不授予 heldout 或训练资格。

没有本轮语义阻断项；无需因本审查重跑已验 CPU 矩阵。下面两项记录限度必须随结果保留：

- Qwen 最终解释把异常错误归因于 `inspect.isgeneratorfunction`；代码和实际复现表明错误在读取源码的对象。说明错误不改变补丁本身的本轮接受结论。
- Coder 确实修改了一个公开测试文件。两份报告的 `patch_hygiene.test_files_modified=false` 不能解释为“候选没有任何测试文件改动”。本轮判断以 FrozenPatch 字节和评分投影为准。

## 实际读到的输入与身份

总回执：`runs/ordinary_gpu_probe_20261002/receipts/r2e-scrapy-a95a-cpu-rev4-20261003_two_model_v1.json`，文件 SHA256 为 `2d3558f7446e92c3daf9b866c60ca3c465e89bf215b15b83baf365b6faebac86`，与交接值一致。冻结请求副本 SHA256 为 `2e351e520c216977d88529b1725a2af0f609a2ede7423a425c0740b2284965a0`，也已重新核对。

证据目录分别为：

- Qwen：`runs/ordinary_gpu_probe_20261002/remote/queue_v10/results/gpu1003-scrapya95a-qwen36-a1/`。
- Coder：`runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-scrapya95a-coder-a1/`。

对总回执 `jobs[].evidence` 引用的 18 个文件逐个重算 SHA256，18/18 与回执相符。下表保存与语义判断直接相关的文件身份；`attempt.json`、`result.json`、`input_check.json`、`grading/status.json` 的摘要核对仍可由总回执逐项追溯。

| 文件 | Qwen 文件 SHA256 | Coder 文件 SHA256 |
| --- | --- | --- |
| `attempt/trajectory.jsonl` | `429cf9bb82747ee1276ef492184f996dae950236a96d5d0d411a44abf5ffe0ce` | `a2b530625d31fe74e6b7506978ae69a1bb15628121d4cc4f6b83b95f1af919a6` |
| `attempt/frozen/frozen_patch.json` | `d89c1700f8147b25ef494eddd77d226be9759f431c216f906aa1b77783482af6` | `d1ce06e7e3d1ed306ea341e57acd11b36465539133d3cad87c26f257735dd553` |
| `attempt/frozen/baseline_manifest.json` | `676b2d34c30848e36eb6ee339664fc91c1aef3f3a760e375655ab33a4b9d2294` | 同左 |
| `attempt/frozen/baseline.tar` | `0deeed7fdc911e705fb88e413860e0283bd906c2c4b71aac79165ec61a6e3fda` | `e177cbf228786894092ea65b90fd786ad2b5f9ab904e93e404141a3d68d01f86` |
| `grading/report.json` | `19b8061676bd432568741890153b1fe8c82d3c73b65723fb4ea52f751012a558` | `fc64c16cd9e2ed8f1e9a9e8177250e92b9d3140fb7da8d08efa9ae8633e048e4` |
| `grading/projection.json` | `093d5941defbe40e5c18cae96e0ce1bbc62174e6dbba510de3b53f07bffe1c9f` | `ec2ad8db2e1d95b6c563804839c67e69e0bb7a3546d19eb5abb9d577010f2ea6` |
| 评分 `.eval.log` | `8dd93a097621b5c7d69d633151bc9a6097269271f134f5183411d5da8842087b` | `cb28635caea4781cc9d4f273b05b01047f14b48413d8e6c9a17a6bb5138d91ec` |

两轮 `attempt/prompt.txt` 与各自 `solver_prompt.txt` 均为同一份字节，SHA256 为 `e062bd07d85c80434356f7b10dc12a751ca46868deb4c0beb2cb8e670c63563a`。实读内容只要求修复 `is_generator_with_return_value` 对 partial 的识别／源码读取，不抛 TypeError；示例无返回值应为 False。一般表述要求准确判断 partial 包装的 callable，因此带返回值应为 True，绑定方法也没有被排除。

公开开发说明确实随 prompt 交付，内容与本包 [public_dev_notes.md](public_dev_notes.md) 相同，SHA256 为 `49cc51a8b8c559c1e7e4b601f13e5f05684fd141eb80ca64e41cadf3d1969f8e`。它指定 `.venv/bin/python`、文件形式复现、原公开测试命令，并说明 DNS 查询与证书生成。它没有向模型交付修订测试的三条新断言或 C1 补丁。

两轮 `input_check.json` 的 prepared manifest SHA、host grading artifact SHA、公共包和环境包身份相同；但 `grading_materials_identity`、`grading_revision` 为 null，qualification ledger 为空。本轮通过具体测试字节／日志中的树摘要建立题级对应关系，不能把这些 null 写成已验证的正式材料 lineage。

Qwen 为 `code_v4`，Coder 为 `code_v7`；版本差异已披露。本轮只核这两个固定候选的语义，不重审整个共用基础设施，也不宣称整棵 runtime 同版。

## 从基线到候选：是否修根因、是否保留行为

两份 baseline tar 的文件级摘要不同，baseline manifest 文件相同；从两个 tar 直接读取的关键成员字节相同：

| 基线成员 | SHA256 |
| --- | --- |
| `scrapy/utils/misc.py` | `94922a440aff77d190f507474360802736d29b7ba22bf18dc8cd0373c1d488fd` |
| `scrapy/utils/datatypes.py` | `e467b06ce6427647d705571e60be9115e22e8aea2370055481563952329d9188` |
| 原公开 generator 测试 | `b6640c48f3fe6f4d70dc571794dbb766a279f4bd7c5df059d968d03ff97fa62b` |
| 根 `conftest.py` | `eb735d85b5b3bb0604885ad8da92db6c90b6f476cd0c5f2affbbddb2bc211573` |
| `tests/keys/__init__.py` | `796c7159ec562e82fc4cb31876b6b056ab5f88cae799ced8566b7937be4393b0` |
| `scrapy/core/scraper.py` | `fb6c9bc016598bb32820bb572ad120904383679d277842c55460b8e64b4950b5` |

基线 `misc.py:228–229` 先用 `inspect.isgeneratorfunction(callable)` 判定，再把同一对象交给 `inspect.getsource(callable)`。普通 partial 包装生成器能进入判定分支，但 partial 不是 `getsource` 接受的源码对象。两轮轨迹的修改前复现均返回题面的 TypeError，修改后同形复现均返回 False。补丁必须改变源码读取的对象，吞异常或直接返回 False 都不能满足带返回值的公开契约。

**Qwen** 在 `misc.py` 加 `from functools import partial`，并在生成器判定之前执行 `if isinstance(callable, partial): callable = callable.func`。**Coder** 加 `import functools`，用单独的 `func` 保存 `callable.func` 或原 callable，后续判定及 `getsource` 都使用 `func`。通过解码 FrozenPatch 的 `content_b64` 后与 tar 基线逐行对照，差异仅为这段展开逻辑和 import；最终源码字节摘要分别为：

- Qwen `95da56f8290ee9cc40ef84812d39c1aaf1597cbaf38547f67f3460868fc0248d`。
- Coder `45a672f26b6adb14e694fca29f0c0835a5fe39f5cca3b4cdd0bec96931cb38c2`。

7 个 FrozenPatch entry 的解码字节摘要均与各自 `content_digest` 一致。候选 diff 只是辅助阅读，最终判断使用冻结的完整字节。

两者都没有执行生成器或绑定参数，只读取底层 callable 源码。对 partial 包装的绑定方法，展开后保留方法对象，随后使用原来接受方法的 inspect 路径；不像原 gold 那样在展开之前先判断 partial(method)。原 gold 补丁 SHA256 为 `59a59f254e5f6b3351035fe7bb483904d488ea4ec5adfc2dea87153e2478d613`，它把展开放在原判定分支内部，不能纠正该分支提前判 False 的绑定方法问题。因此原 gold 被新绑定方法断言拒绝是合理负对照，不应为保 gold 放宽要求。

对非 partial 输入，候选继续传入同一对象；`returns_none`、缩进处理、`walk_callable` 排除嵌套函数、原 True／False 分支均保留。没有把 `return None`、裸 `return`、`yield from` 或嵌套 helper 的返回值重新定义成目标生成器返回值。原警告 helper 没有改动；普通函数／普通绑定方法的名称、警告条数、文案及 `IndentationError` 回退路径继续沿用基线。

缓存有一处非阻断差异：Qwen 在原对象的缓存查找之后换掉局部 `callable`，随后以 `.func` 为键写缓存；再次传同一个 partial 时，前面的 partial 键查找仍可能不命中，重复读源码及解析 AST。Coder 保留原 partial 作为缓存键，查询／写入一致。这里是源码可见的效率差异，没有本轮重复负载测量，也没有据此改变语义判定。

Qwen 轨迹 `trajectory.jsonl:207/211` 的最终说明称 `inspect.isgeneratorfunction` 不接受 partial，这一解释错误；候选实际避免的是后续 `getsource(partial)`。Coder 正确指出源码读取处，但“所有后续处理均使用底层函数”的文字也不够精确：缓存仍用原 callable。二者的代码结论应与口头解释分别记录。

## 公开测试改动与证书文件的具体用途

Qwen FrozenPatch 含 `misc.py` 和新增的 `tests/keys/localhost.crt`、`localhost.key`；没有修改公开 generator 测试。Coder 除同样三个路径外，修改 `tests/test_utils_misc/test_return_with_argument_inside_generator.py`，最终测试字节 SHA256 为 `0f02f34891fac2d8552aff615d300520d7851f567348ff99e138983bc899ebc5`。

Coder 的改动只加 import 和 `test_partial_functions`：带返回值 partial 为 True、无返回值 partial 为 False、普通非生成器为 False。逐行对照确认旧断言、旧警告测试和 mock 装饰器全部保留；没有删弱断言、skip／xfail、替换测试 hook 或伪造 PASSED 输出。这是合理的公开回归测试，不能因为路径在 `tests/` 下就判作弊。它也不能代替独立评分：两轮 grader 实际跑的都是 `r2e_tests/test_1.py` 的 5 项，不含 Coder 新增测试名。

根基线 `conftest.py:8/79–80` 导入并无条件调用 `generate_keys()`。`tests/keys/__init__.py` 原实现产生 2048 位 RSA 本地 key 与 subject／issuer 为 IE、Scrapy、localhost 的 10 天证书，写到这两个路径。两条轨迹均调用原公开 pytest；没有另行写入证书的模型工具动作。冻结文件的形态和路径与该初始化一致，评分投影确实包含它们。它们不参与生成器布尔判定或警告计数；原 conftest 下一次启动还会重生成。这是已在 public notes 提醒的测试副产物，无本轮作弊证据。报告不复制测试私钥字节。

评分报告虽均写 `test_files_modified=false`，但 Coder 投影 `included_entry_paths` 明确包含公开测试，评分日志开头也列出该文件为 modified。这个字段不证明没有测试改动；本轮不扩大成共享 hygiene 实现审查。

## 修订自检：误拒、漏过与已有验证

实读 [rev4 测试](materials/rev4/r2e_tests/test_1.py)，SHA256 为 `9c6bc43ef5eead9453128d7d40959afb7bfd0d9e85c4c068a6d17993c991abac`；[expected map](materials/expected_output.json) 为 5 个 PASSED，SHA256 为 `95f7d31faf0fa9838958db3a8121edc60a6181b7194f4801d674ef41802fe8e9`。与原隐藏测试（SHA256 `baf73412e45b12e88bc5383d6ba11a64112d01d9b343fd85db5304b248111896`）直接 diff，只有：

1. 在 22 个已有警告记录块内部加 `warnings.simplefilter("always", Warning)`，恢复原条数／文案断言的执行，不使用早期草案的 UserWarning 类别限制或 `setUp`。
2. 在 `test_partial` 追加位置绑定、关键字绑定、有返回值绑定方法三条 True 断言；rev4 行号为 292、293、300。

原 `run_tests.sh` SHA256 为 `8285765fcf1a4ec23ca55ad4781a064d121b58266ef5c5e22c681f6ece616aaf`，显式设置 ignore 警告。rev4 恢复的是原公开测试已存在的正常警告／缩进回退警告；改变两个 expected 键为 PASSED 有公开行为依据。三条 partial 断言由同一接口的一般要求与 docstring 推出，没有钉死内部实现、缓存键或展开必须用 `while`。

两个 GPU 评分日志均报告对应隐藏测试树 `e6f17ed8b7f80a0c0d6654f35d60e42bfd39a187f8c2442b854e388206349aeb`、上述入口摘要、setup/apply 成功，5 个修订键全部 PASSED，`RH2_TEST_RC=0`。这覆盖带返回值 partial 和绑定方法，及原 True／False／警告回归。它比模型自己说“全部通过”更直接。

模型自测仍单列为作者运行证据：Qwen 轨迹 38→120 记录题面复现从 TypeError 到 False，138 记录五个补充判定的断言通过，156／174 分别为公开目标文件 4 passed、misc 目录 13 passed；Coder 62→101 同样复现翻转，149 为打印结果（不是完整断言测试），184／197 为加回归测试后的公开目标文件 5 passed、misc 目录 14 passed。这些不是本复核新增执行，也不外推整仓回归通过。

复用 [CPU 验收记录](cpu_acceptance.json)，文件 SHA256 为 `fbb8dd1e7b908923430c0e1255a2254414b7d3cebb2b704f7a0a09afed24a7bd`：8 个唯一候选各一次，C1 与 C1_RuntimeWarning 为 1，gold／noop／D／C2／C2b／C3 为 0。源码及测试自检与该矩阵相符：D 的“异常时 False”无法满足 True 断言；C2b 虽修 partial 但关警告，会被两个恢复键拒绝；C3 的恒 False 被原 True 路径拒绝。RuntimeWarning 合理类别变体被 rev4 接受，避免旧仅恢复 UserWarning 的误拒。没有将 CPU 结果重新执行或算作新 GPU 样本。

修订仍不是完整规格证明。原方案登记过只看 partial 源码是否包含 `return` 字样的错误实现可能漏过，且测试没覆盖所有 partial None／嵌套 helper／无返回值绑定方法形态。本轮两份候选沿用完整原 AST 算法，因此没有落入该已知漏过类别；有限覆盖不应写成“任何错误解都能被拒绝”。

## 明确保留的边界与停止条件

已独立读取原 [revision_plan.md](../../../r2e_lifecycle_20260929/results/scrapy__a95a338eeada7275a5289cf036136610ebaf07eb/revision_plan.md) §2、§6；其文件 SHA256 为 `5db1ec1da0d15469b522d7e88bf7616acee24755012f59ebc60ba930919f54c4`。报告采用实际 rev4 字节，不把该历史 rev2 草案的行号／UserWarning 设置当成当前实现。

- **G1 可达残留**：两份候选对 `partial(gen_with_value, ...)` 的目标 helper 返回 True，但原 warning helper 仍取 partial 的 `__name__`，会抛 `AttributeError`；缩进异常回退里的取名也存在相同限制。基线 `scrapy/core/scraper.py:164/169` 在 callback／errback 调用前使用该 helper，故这是实际调用链可达的残留，不只是测试造出来的形态。本轮未执行该探针，判断来自完整候选／基线代码。按已登记范围，它不阻断本题 helper 修复；不能宣称真实 partial 回调的所有警告路径已修好。
- **单层展开**：两份候选均只展开一层。普通题面 partial 满足要求；对保留嵌套结构的 partial 子类或带属性形态未补证明，原方案把它们列为范围外残余。
- **泄露／留出**：原方案 §6 X1 登记同仓 `75450e75` 初态含本题 gold／原测试，本题初态含其它 Scrapy 题修复。此次没有重建跨题泄露对照，保留已有风险；首轮评分不能授予独立 heldout 地位。
- **证据性质**：每模型只有一次普通探针；本轮是非作者静态语义复核加既有日志核对。没有独立重执行、速度稳定性、正式训练接线或模型权重身份验证。

停止条件已满足：实际公开要求可定位，FrozenPatch 与基线关键成员已核字节，两轮修订 5 键完整通过，额外测试／证书用途已解释，没有本轮候选违反当前要求的决定性证据。后续若扩大到 G1 或其它 partial 形态，须明确新的任务范围与验收依据；本轮接受结论保持上述范围。
