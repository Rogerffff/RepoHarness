# scrapy__9a15fcf8 独立复核·第一步初判（读主审产物前）

2026-09-25 · 独立复核者（静态、干净上下文，未参与本题主审）· 只做静态阅读与既有运行原件核对，未运行代码或容器，未改任何原件。

路径约定（均相对仓库根）：`PUB=runs/r2e_static_prep_20260924/v2/public/scrapy__9a15fcf89a151811de8ac783419df0512c863d5e`，`PRIV=runs/r2e_static_prep_20260924/v2/private/scrapy__9a15fcf89a151811de8ac783419df0512c863d5e`，`WT=$PUB/worktree`。

## 0. 初判摘要

| # | 判断 | 证据级别 |
| --- | --- | --- |
| 1 | **核心需求成立且测到了。** 唯一目标键是 `ResponseTypesTest.test_from_content_type`，新增断言就是题面原例（`'application/x-json; encoding=UTF8;charset=UTF-8'` → `TextResponse`）。noop 在该键的失败信息与题面 "Actual" 逐字对应。gold 只加一行，四次 gold 运行都与期望完全一致 | 执行证据：current 两组 noop/gold，外加 M3 两次参考运行 |
| 2 | **主要问题：错误回归，并因此误拒更完整的修复。** 期望映射里 `test_from_args`、`test_from_headers` 为 FAILED。原因是这个 base 在 Py3 下 `Headers` 的值是 bytes，而 `from_content_type` / `from_content_disposition` 用 str 去切分，于是抛 `TypeError`；这与本题无关。一个把 bytes 处理补全、使这两个键变成 PASSED 的候选会被判 0 | 执行证据：P4 诊断候选 7/7 PASSED、reward 0 |
| 3 | **根因是测试搬迁带来的伪影。** 上游在 `tests/py3-ignores.txt:40` 里列了 `tests/test_responsetypes.py`，Py3 下整个文件本来不会被收集。搬到 `r2e_tests/test_1.py` 后绕过了这条忽略，于是 Py3 不兼容被固化成两条期望 FAILED | 源码 + 日志 |
| 4 | **次要漏测。** `application/json`、`application/javascript`、`application/x-javascript` 以及 atom/rdf/rss 映射没有任何断言，隐藏测试和公开测试里都没有。一个把 `'application/json'` 键改名成 `'application/x-json'` 的错误补丁，预计能拿到 1 分 | 静态推断，未执行 |
| 5 | **暂定处置：`needs_review`。** 题意清楚、材料一致、评分稳定，可作为开发诊断的静态候选；但它带着已证实的"修得更全反而 0 分"陷阱。建议把"删除两条 Py3 失败键"作为测试标准修订候选交用户决定。修订前如用于探针，任何 0 分都要先查这两个键是否翻转 | 建议 |

## 1. 实际读取范围

**读了：**

- **角色卡与方法文档**
  - `roles/reviewer_r2e.md` 全文。
  - `roles/investigator_r2e.md`：终端一次输出了全部 33 行，但评分口径只采用"材料"与"R2E 的评分口径"两节；其余各节只是主审的流程说明，没有当作依据。
  - `quality_review_protocol_20260920.md`、`r2e_environment_card.md`、`record_template.md` 全文。
  - 40 项清单不在本步可读范围内，没有读。清单编号只引用协议 §2 表格里给出的号。
- **公开包**
  - `user_prompt.txt`、`environment_brief.md`、`public_bundle.json` 全文。
  - `worktree_manifest.json`：读了汇总字段和 6 个关键文件的哈希，并与 `WT` 里的实物逐一核对，结果一致。
  - `WT` 下的源码与配置：`scrapy/responsetypes.py`、`scrapy/http/headers.py`、`scrapy/http/__init__.py`、`scrapy/utils/datatypes.py`（`CaselessDict`）、`scrapy/utils/python.py`（`isbinarytext`、`_BINARYCHARS`）、`scrapy/utils/misc.py`（`load_object`）、`conftest.py`、`pytest.ini`、`run_tests.sh`、`tox.ini`、`setup.cfg`、`tests/py3-ignores.txt`。
  - `tests/test_responsetypes.py`：与隐藏测试做了 diff。
  - `scrapy/mime.types`：只读了前 30 行。
  - 全树 grep：`responsetypes`、`from_content_type|from_mimetype|from_headers`、`x-json|application/json` 的调用者和出现位置。
- **私有包**
  - `hidden_tests/__init__.py`（空文件）与 `hidden_tests/test_1.py` 全文。
  - `expected_output.json`、`gold.patch`、`run_tests.sh`、`grading_bundle.json`、`validation_bundle.json`、`revisions.json`（内容为 `[]`）、`run_refs.json`。
  - 已核对：`run_tests.sh`、期望映射、gold 三者的 sha256 都与 bundle 记录一致；两份隐藏文件的 sha256 与 `grading_bundle.json` 一致。
- **运行原件（`run_refs.json` 所列）**
  - current 四行账本：R-f 的 noop 和 gold（各 `:45`），环境轮中央复跑的 noop 和 gold（各 `:45`），以及对应的四份 `.eval.log`。
  - diagnostic 一行：P4 overfix 账本 `:1` 及其日志。
  - M3 独立参考：账本 `:31`、`:78`，以及两份 `test_output.txt`。
  - 上述七份日志的 sha256 全部与 `run_refs.json` 一致。
- **评分代码**（只读，用来确认评分时只替换哪些文件）：`rh2/src/repoharness2/adapters/slime/r2e_grading_scripts.py` 第 87–130 行，即 `_restore_lines` 与 `_candidate_test_lines`。

**没读：**

- P4 overfix 候选 diff 本体。只看到账本里的 `patch_sha256`、投影路径和测试结果。
- 各次运行的 `diagnostics.json`。
- M3 的 `facts/initial.diff`（manifest 记为 0 字节）。
- 公开读者与主审的产物；`OUTPUT_DIR` 下的其它文件。写入本文件前核对过，该目录为空；写完后发现公开读者同时写入了 `public_read.md`（修改时间 01:57），没有打开。
- 任何 `history/` 目录、`r2e_env_repair_20260924` 文档目录、`*review*` 目录、本批 README，以及 `runs/` 下的分析与汇总文件。

## 2. 公开目标（只用公开包）

- **题面**（`PUB/user_prompt.txt:3-23`）：`responsetypes.from_content_type('application/x-json; encoding=UTF8;charset=UTF-8')` 应返回 `scrapy.http.TextResponse`，现在返回的是 `scrapy.http.response.Response`；并概括要求"MIME 为 `application/x-json` 的响应应解释为 `TextResponse`"。题面还有一句动机提到 "downstream processing"，但没有说是哪个下游接口。
- **读代码能知道的**：`ResponseTypes.CLASSES`（`WT/scrapy/responsetypes.py:18-31`）里有 `application/json` 等映射到 TextResponse 的项，但没有 `application/x-json`。`from_mimetype`（`:41-49`）查不到时回落到 `application/*`，这一项也不存在，于是返回 `Response`。
- **题面没提的**：Py3 下的 bytes 问题。另外，公开的 `tests/test_responsetypes.py` 里没有 x-json 用例，解题者需要自己写复现。

## 3. 隐藏测试展开（`PRIV/hidden_tests/test_1.py`，唯一测试文件，共 7 个键）

隐藏文件等于公开的 `WT/tests/test_responsetypes.py` 加 1 行（`test_1.py:38`，diff 已核）。它只导入 `scrapy.responsetypes` 和 `scrapy.http`，不依赖仓库里的测试辅助代码。

| 键 | 期望 | noop | gold | 性质 | 调用与决定性断言 |
| --- | --- | --- | --- | --- | --- |
| `test_from_content_type` | PASSED | FAILED | PASSED | **目标键** | 7 个 str 输入逐一调用 `from_content_type`，断言 `retcls is cls`（`:30-42`）；新增的 `:38` 就是题面原例 |
| `test_from_filename` | PASSED | PASSED | PASSED | 回归 | `from_filename`，含 `data.bin`→`Response`、`file.xml.gz`→`Response`（`:8-19`） |
| `test_from_content_disposition` | PASSED | PASSED | PASSED | 回归 | str 输入 → `XmlResponse`（`:21-28`） |
| `test_from_body` | PASSED | PASSED | PASSED | 回归 | `isbinarytext` 加标签嗅探（`:44-53`） |
| `test_custom_mime_types_loaded` | PASSED | PASSED | PASSED | 回归 | 检查包内 `mime.types` 已加载（`:80-82`） |
| `test_from_headers` | **FAILED** | FAILED | FAILED | 期望失败的死键 | `Headers` 的值是 bytes，`from_content_type` 在 `responsetypes.py:56` 抛 `TypeError`（`:55-64`） |
| `test_from_args` | **FAILED** | FAILED | FAILED | 期望失败的死键 | 第 2 组输入经 `from_headers` 触发同一个 `TypeError`（`:66-78`） |

**回归保护的实际范围：**

- 受保护：`text/html`、`text/xml`、`application/xhtml+xml`、`application/vnd.wap.xhtml+xml`、`application/xml`、`application/octet-stream` 这六个 content-type 映射；按文件名、正文、disposition 的推断。
- 不受保护：
  - `application/json`、`application/javascript`、`application/x-javascript`、`application/{atom,rdf,rss}+xml` 这些映射；
  - header 与 args 两条入口。这两条在 Py3 下对任何类型本来都会崩，所以这两个键不提供任何回归保护，唯一的作用是"不许修 Py3"。

## 4. 需求—测试双向映射

| 公开要求 / 合理旧行为 | 公开依据 | 测试 ID / 断言 | 覆盖 | 执行证据 / 待做 |
| --- | --- | --- | --- | --- |
| 题面原例 → `TextResponse` | `user_prompt.txt:11-14` | `test_from_content_type` 的 `:38`，由 `:42` 的 `is` 断言检查 | 覆盖 | noop 日志 `:78` 失败；gold 日志 `:106` 通过 |
| 各入口对 `application/x-json` 的结果一致（`from_mimetype`、header 路径） | 题面 "Expected Behavior" 的泛述 | 无；header 路径在 Py3 下对任何类型都崩 | 部分 | 静态判断；gold 在 Py3 下同样没有让 header 路径可用 |
| 既有 content-type 映射不变 | `CLASSES`（`:18-31`） | `test_from_content_type` 前 6 组 | 部分 | `application/json` 等 5 项没有断言（反例见 §7） |
| 宽泛改法不得误伤 `application/octet-stream` | 旧行为 | `test_1.py:37`，以及 `test_from_filename` 的 `data.bin` 一组 | 覆盖 | 把 `application/*` 整体映射成 TextResponse 的改法会被拒，这是正确的拒绝 |
| Py3 下 header 路径**继续崩溃** | **没有公开依据**；相反，`Headers` 的设计就是把值规范成 bytes（`WT/scrapy/http/headers.py:13-36`） | 期望 `test_from_headers`、`test_from_args` 为 FAILED | **冲突** | P4 诊断：修好即判 0 |

反向检查：唯一有公开依据的新断言是 `:38`。两条 FAILED 期望都没有公开依据，只是 base 缺陷的快照。

## 5. R2E 专项

**(a) 非 PASSED 期望键会不会惩罚正确修复：会，且已有执行证据。**

- 失败原因：
  - noop 日志 `:50`、`:58`：`content_type = b'text/html; charset=utf-8'`，`TypeError: a bytes-like object is required, not 'str'`。
  - gold 日志 `:59`、`:91`：同样的错误；因为插入了一行，行号从 56 移到 57。
- P4 诊断候选的执行结果（`runs/r2e_env_repair_20260924/p4/ledger_overfix.jsonl:1`）：
  - 只改了 `scrapy/responsetypes.py`，见 `projection.included_paths`。
  - 与 current 用的是同一张派生镜像 `fe908bed…`，同一个隐藏测试树 `a3f0f6e4…`（日志 `:4-5`）。
  - 结果：7 个键全部 PASSED（日志 `:33-39`），reward 0，两条不一致的键正是 `test_from_args` 和 `test_from_headers`。
- 翻转边界（静态推断，未执行）：
  - 必须同时处理 `responsetypes.py:56` 的 `content_type.split(';')` 和 `:61` 的 `content_disposition.split(';')` 两处 bytes；`:64` 只捕获 `IndexError`，挡不住 `TypeError`。
  - 原因：`test_from_headers` 的第 2 组（`test_1.py:58`）和 `test_from_args` 的第 3 组（`test_1.py:72`）都会走到 `from_content_disposition(bytes)`。
  - 因此只在 `from_content_type` 里解码的半截修法会让两个键仍为 FAILED，照样得 1；在 `from_headers` 里把两个头都解码，或者两处都兼容 bytes，就会让两键一起翻转，得 0。
- 状态只会在 FAILED 与 PASSED 之间变化：unittest 方法内抛出的异常记为 FAILED；ERROR 只可能来自夹具或收集问题（见 (d)）。
- 这种 bytes 修复与 `Headers` 的设计一致，是合理的 Py3 修复；真实下游调用者全都经过 `from_args(headers=…)`，例如 `http11.py:264`、`webclient.py:129`、`httpcache.py:187/246/318`、`httpcompression.py:28`。
  - 我记得上游后续版本也做了同类处理，但这点没有在本次材料里核对。
- 真实模型会不会往这个方向修：未知，需要真实模型探针。
  - 一个风险放大因素：公开测试在 base 上本来就有这两条 `TypeError` 失败；题面的 "downstream processing" 也会把解题者引向 header 路径。

**(b) 题面描述的报错是否出现在 noop 目标键：是。**

- noop 日志 `:78`：`AssertionError: application/x-json; encoding=UTF8;charset=UTF-8 ==> <class 'scrapy.http.response.Response'> != <class 'scrapy.http.response.text.TextResponse'>`，与题面 "Actual: scrapy.http.response.Response" 对应。
- 中央复跑的 noop 日志与之逐行相同，差别只有时间戳、对象地址和耗时。

**(c) 题面是否泄漏修法：** 题面给出了与隐藏断言逐字相同的输入和期望类，但没有给出实现位置或代码。修法（在 `CLASSES` 里加一项）读代码一眼就能找到，难度很低。这属于原始需求本身，不算泄漏隐藏细节。反过来，两条期望 FAILED 的"陷阱"题面完全没有提示。

**(d) 测试支撑、搬迁伪影与撞键：**

- 撞键：只有一个测试文件，没有撞键。
- 仓库测试辅助：不依赖。
- 搬迁伪影：
  - 原文件在 `WT/tests/py3-ignores.txt:40` 中，由 `WT/conftest.py:25-29` 在 Py3 下加入 `collect_ignore`。
  - 搬迁后路径变成 `r2e_tests/test_1.py`，不在忽略列表里，于是被收集，这正是 (a) 的根因。
- 隐式支撑：
  - `pytest.ini:2` 的 `usefixtures = chdir` 依赖根目录 `conftest.py:32-35` 定义的 `chdir` 夹具。
  - 根目录的 `conftest.py` 和 `pytest.ini` 评分时不会被重置：grader 只执行 `rm -rf` `r2e_tests` 与 `run_tests.sh`，并注释说明不做 reset（`r2e_grading_scripts.py:97`、`:99`、`:103`）。
  - 所以，候选如果删掉或弄坏 `chdir`，7 个键都会变成 ERROR 并判 0，这是候选自己造成的。正常修复不会碰这两个文件。
- 收集情况：`python_files` 包含 `__init__.py`，`r2e_tests/__init__.py` 也会被收集，但它是空文件；日志 `:19` 显示共收集 7 项。

**(e) 时间、随机、资源敏感：** 没有发现。测试是纯函数映射，不依赖时间、随机、并发或网络。同类运行的重复结果逐键状态完全相同：两次 noop 一致；两次 RH2 gold 与两次 M3 gold 一致。每次约 1 秒，内存峰值约 205 MB（见账本 `resource`）。

**(f) 材料修订：** 无（`revisions.json` 为 `[]`，`material_revisions` 为 `[]`），不适用。R-f 那组虽标为"来源版材料"，但本题没有修订，所以它就是 current 材料。

## 6. 八方面覆盖（已查 / 未查）

1. **公开需求（3、23）。**
   - 已查：渲染后的 `user_prompt.txt`、`public_hints`、`CLASSES` 和调用者。需求只有一个，没有新 API，也没有错误格式要求。
   - 缺项：`public_hints` 里"conda 已激活、pip 可用、测试文件会被重置"对 R2E 不成立（环境卡 §3，E09）。正式 actor 实际收到的系统提示没有核验，属于 actor 待验。
2. **材料与初始问题（1、2、27）。**
   - 已查：题面里的 commit `3fc4e0b319fc`、bundle 的 `base_commit`、M3 的 `facts.head` 三者一致，且 M3 记录 `head_is_parent_of_fix=yes`。
   - manifest 的 `initial_diff` 为 0 字节，说明初态就是 base。
   - M3 账本记录 `gold_matches_git_diff_changed_lines: true`，并排除了 `tests/test_responsetypes.py`，说明 gold 就是修复提交中的非测试部分。
   - 初始问题在 noop 目标键上有执行证据。**没有发现材料错配。**
3. **测试是否测到要求（18–20、25、32）。**
   - 已查：7 个键的全部断言；目标断言用的是 `is` 身份比较，硬编码或无操作都过不了。
   - 缺口：既有映射有 5 项没有保护；header 路径不可测。见 §3、§4。
4. **误拒合理解（24、28）。** 更完整的 Py3 修复会被判 0，已有执行证据，见 §5(a)。其它不同于 gold 的合理实现都能通过（静态推断）：
   - 在 `from_mimetype` 里用 `'json' in mimetype` 判断；
   - 顺带处理 `+json` 后缀；
   - 在 `from_content_type` 里把 `/x-` 前缀规范化掉。
5. **回归与 gold 完整性（26、27）。** 见 §7。gold 没有无关改动；它也没有修 Py3 下的 header 路径，但这是既有缺陷，不是 gold 引入的。
6. **agent 开发条件（6–15）。** 见 §8。评分侧有实测；解题侧只能引用环境卡的镜像层面结论，本题的探针输出没有读到。
7. **交付与评分边界（4、16–17、21–22、29–31）。**
   - gold 唯一改动的路径在投影 `included_paths` 里，`ignored_paths` 为空（gold 账本 `projection`）。
   - 根目录的 `conftest.py` 和 `pytest.ini` 候选可写，评分时生效，见 §5(d)。这是 R2E 的通用通道：理论上候选可以用 hook 改写结果。账本有 `candidate_touched_conftest_or_fixture` 字段，但它是否影响得分，本步没有查。
   - 公开测试基本暴露了隐藏测试的结构（7 个名字；在 base 上跑一遍就能观察到两条 FAILED），但除了题面原例，不构成答案泄漏。
   - 来源镜像：M3 facts 显示修复提交可达（`fix_reachable=commit`，`commits_after_head=6821`），`/r2e_tests` 也在；环境卡 §2 指出正式 actor 目前取的是来源镜像。这是池级问题，**本题进入正式 actor 前必须改用派生镜像**。
8. **题目关系与用途（5、29–30、37–40）。**
   - 已查：难度很低（改一行字典）；题面给出了目标映射。
   - 这是 py2 时代的修复（`tox.ini:7` 为 `envlist = py27`），却在 Py3.9 下评分，产生了 (a)。
   - 没查：与同仓其它 scrapy 题的关系。

## 7. gold 与替代实现

- **gold 本身**：只加一行 `'application/x-json': 'scrapy.http.TextResponse'`（`PRIV/gold.patch:9`）。题面原例能修到（gold 日志 `:106`），没有无关改动，其它映射不受影响。
- **可区分的漏测反例**（静态推断，未执行）：把 `CLASSES` 里 `'application/json'` 这个键**改名**为 `'application/x-json'`，而不是新增一项。
  - 隐藏测试没有 `application/json` 用例，7 个键预计与期望完全一致，得 1。
  - 但此时 `from_content_type('application/json')` 会回落到 `Response`，这是一个真实回归。
  - 公开的 `tests/` 目录里也没有任何 `application/json` 用例（grep 结果为空）。
  - 可能性不高，但成本很低，可以做 CPU 验证。
- **会被正确拒绝的错误改法**：把 `application/*` 映射到 TextResponse，会被 `:37` 和 `test_from_filename` 拒掉。

## 8. 开发需求（逐题）

- **解释器、依赖、网络**：
  - 解释器是 `/testbed/.venv/bin/python`，Python 3.9.21（`environment_brief.md:10`，日志 `:16`）。
  - 没有 pip，也不能出网（brief `:11`）；本题是纯 Python 改动，不需要新依赖，也不需要构建。
  - 评分时 `scrapy` 从 `/testbed/scrapy/__init__.py` 导入（账本 `observations.RH2_OBS_IMPORT_PATH`）。
- **权限与交付边界**：
  - uid 54321 可以写 `/testbed`（brief `:12`）。
  - 提交边界是 `scrapy/responsetypes.py`。改公开测试不影响评分，也不计分。
- **最小验证命令**（静态建议，actor 待验）：
  - `cd /testbed && python -c "from scrapy.responsetypes import responsetypes as r; print(r.from_content_type('application/x-json; encoding=UTF8;charset=UTF-8'))"`
  - `cd /testbed && python -m pytest tests/test_responsetypes.py`：base 上预计 `test_from_headers`、`test_from_args` 两条 `TypeError` 是既有失败；公开文件里没有 x-json 用例。
- **静态推断的坑**：
  - 显式给出文件路径时，不受 `collect_ignore` 影响（pytest 8 的 init path 分支）；但用 `python -m pytest tests/` 按目录跑时，这个文件会被跳过。
  - 根目录 `conftest.py:26` 用相对路径 `open('tests/py3-ignores.txt')`，所以必须在 `/testbed` 下运行。
- **actor 条件**：正式启动链还没接。conda/pip 提示有误；来源镜像会泄漏答案（环境卡 §2）。都记为 actor 待验，不写"环境正常"。

## 9. 疑点、未知与建议（建议队列，由协调者安排）

1. **【决策，优先】** 把"从隐藏测试和期望映射里删除 `test_from_headers`、`test_from_args`"作为测试标准修订候选，交用户决定。
   - 这项修订不扩大原需求。两个键目前不提供任何回归保护，只惩罚 Py3 修复。
   - 修订后需要复验三项：noop 得 0，gold 得 1，P4 overfix 得 1。
   - 如果决定不修订，就把陷阱记进用途说明，探针阶段按 §0 第 5 条解读 0 分。
2. **【CPU】** 用 §7 的改名反例确认漏测（预计得 1）。如果确认，可以考虑补一条 `application/json` 断言（这是合理旧行为），但补断言时要同时用合理替代解和已知错误解校准。
3. **【CPU】** 用"只在 `from_content_type` 里解码 bytes 的 x-json 修复"确认翻转边界（预计仍得 1）。这决定了探针里哪些修法是安全的。
4. **【真实模型】** 解题者多频繁地去做 Py3 bytes 修复，未知。需要先把 actor 切到派生镜像。
5. **【池级，未核实】** 同仓其它 scrapy 题，如果隐藏测试来自 `tests/py3-ignores.txt` 所列的文件，可能有同类的 Py3 FAILED 期望键。建议协调者按这条规则扫一遍。
6. **未知**：
   - P4 候选的具体改法（没读 diff，只能从结果反推它两处 bytes 都处理了）；
   - 解题侧本题的具体探针输出；
   - `candidate_touched_conftest_or_fixture` 是否参与判定。

**唯一优先下一步：** 第 1 条的用户决策。翻转机制已由 P4 执行证实，不需要新实验来证明。

## 附录：证据定位

**评分侧运行（current）**：四次运行都用派生镜像 `rh2-r2e-derived/scrapy:9a15fcf89a15-r2e_derive_v1`（`fe908bed…`），配方 `r2e_derive_v1`（`0da821a1…`）。

| 运行 | 账本行 | reward / 匹配 | 日志 | 关键行 |
| --- | --- | --- | --- | --- |
| R-f noop | `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:45` | 0，6/7，不一致键为 `test_from_content_type` | `…/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-s_49e74388.eval.log` | `:50`、`:58` TypeError；`:78` 题面原例失败；`:122-128` 摘要 |
| R-f gold | `runs/r2e_rf_20260923/remote/ledger_r2e_all_gold.jsonl:45` | 1，7/7；`projection.included_paths=["scrapy/responsetypes.py"]` | `…/evallog_replay-r2e-rf-all-gold-s_798f95c6.eval.log` | `:1` 改动文件；`:59`、`:91` TypeError；`:103-109` 摘要 |
| 中央复跑 noop | `runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl:45` | 0，6/7 | `…/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_92f27267.eval.log` | 与 R-f noop 逐行相同，差别只在时间戳、地址、耗时 |
| 中央复跑 gold | `runs/r2e_env_repair_20260924/_rerun2/ledger_gold.jsonl:45` | 1，7/7 | `…/evallog_replay-r2e-envrepair-rer_14d83f49.eval.log` | 同上 |

- 两组运行的时间：账本 `started_at_utc` 分别为 2026-09-23T15:50Z 和 19:38Z。`run_refs` 把后一组的组名写成 09-24，推测是本地时区，不影响结论。

**诊断与参考运行：**

- **P4 overfix（diagnostic）**：`runs/r2e_env_repair_20260924/p4/ledger_overfix.jsonl:1`
  - `patch_sha256 81cedada…`，只改 `scrapy/responsetypes.py`；
  - 5/7，不一致键为 `test_from_args`、`test_from_headers`，reward 0；
  - 日志 `…/p4/eval_logs/evallog_replay-r2e-envrepair-p4-_1acaf88b.eval.log`：`:22` 七个点，`:33-39` 全部 PASSED，`:42` 显示 `RH2_TEST_RC=0`。
- **M3 独立参考（来源镜像）**：`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:31`、`:78`
  - gold 两次都得 reward 1，期望状态为 PASSED 5 / FAILED 2；
  - facts：`head=3fc4e0b3…`，`fix_reachable=commit`，`r2e_tests_root=2`，`egress_pypi=fail`；
  - 两份 `test_output.txt` 的 `:87-94` 与 RH2 gold 的状态相同。

**源码与评分代码：**

- **源码**（`WT/`）：
  - `scrapy/responsetypes.py`：`:18-31` `CLASSES`；`:41-49` `from_mimetype`；`:56` 与 `:61` 两处 str 切分；`:64` 只捕获 `IndexError`；`:72` 取 `headers['Content-type']`。
  - `scrapy/http/headers.py:13-36`：值统一规范为 bytes。
  - `conftest.py`：`:25-29` 在 Py3 下读 `py3-ignores`；`:32-35` 定义 `chdir`。
  - `pytest.ini`：`:2` `usefixtures`；`:5` `--doctest-modules`。
  - `tests/py3-ignores.txt:40`。
- **评分代码**：`rh2/src/repoharness2/adapters/slime/r2e_grading_scripts.py`：`:97` 注释说明不做 reset；`:99`、`:103` 只替换 `r2e_tests` 和入口脚本；`:123` 注释说明有 FAILED 期望键的题，gold 的 RC 也非 0。
