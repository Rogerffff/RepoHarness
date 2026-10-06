<!-- 协调者注（2026-09-25）：宿主不允许子会话写报告文件（"Subagents should return findings as text"），本文由协调者从该会话被拒的写入调用中原样取出保存，未改一字。 -->
# 私有主审初判（读历史前）：scrapy__e938752973b4fc53e0fa0c0bc68a431613b987e4

角色：R2E 私有主审（第二批，静态审查）。日期：2026-09-25。本文写于读取任何历史调查之前。

证据级别：
- 【执行】：运行原件，包括账本、eval log、devcheck 捕获、私有 gold 对照。
- 【解析】：账本或日志里的解析状态。
- 【源码】：静态读源码得出的推断，没有运行。

## 0. 暂定处置

- **题目**：在 Py3 下，`PythonItemExporter(binary=True).export_item(...)` 返回的键仍是 `str`，题目要求把键也转成 bytes。修复只涉及 `scrapy/exporters.py` 里的 `PythonItemExporter`。
- **评分结构**：
  - 隐藏测试 = 公开的 `tests/test_exporters.py` 原文 + 新增的 `PythonItemExporterTest.test_export_binary`，外加一行没有用到的 `import warnings`。
  - 期望映射有 62 个键，全部是 PASSED。
  - 目标键只有 1 个（noop FAILED，gold PASSED）。其余 61 个是回归键，noop 和 gold 下都是 PASSED。
- **暂定处置**：静态候选（用于开发诊断）。状态 `needs_review`，理由是"静态候选，待 actor 验证"。没有发现题意或测试上的争议。
  - **误拒风险低**：唯一的目标断言就是题面 Expected Behavior 里的原例。期望里没有非 PASSED 键，所以更完整的修复也不会让某个键翻转而被判 0。
  - **漏测**：binary 模式下只测了顶层原例。dict 形式的 item、`fields_to_export`、嵌套 Item 或 dict、键的编码、`export_empty_fields` 都没有测。一个只处理 Item、不处理 dict item 的部分修复也能得 1（静态推断，待 C2 实跑）。
  - **gold 的问题**：gold 修到了原例。但它在 binary 模式下多做了一遍 `_serialize_dict`，带来未测回归：
    - `export_empty_fields=True` 且字段缺失时，gold 抛 `TypeError`，base 返回 `None`；
    - 字段的自定义 serializer 返回非字符串时，gold 也抛 `TypeError`。

    以上是静态推断，待 E1 实跑。这些回归不影响任何键。不建议为此改测试。
  - **题目关系**：
    - 本题的修复和 `test_export_binary` 出现在 `scrapy__75450e75…`、`scrapy__a95a338e…` 的公开初始工作树里。gold 的 5 行中有 4 行逐字出现，另 1 行只是方法改了名。
    - 本题的工作树里已经含有 `scrapy__9a15fcf8…` 的一行修复。

    这些同族关系需要登记。
- **唯一最值得先做的下一步**：用正式评分代码实跑 C1（合理替代解）和 C2（只处理 Item 的部分解），把"不会误拒"和"漏测 dict item"两条从静态推断变成执行证据。E1 可以同一批做。

## 1. 读取范围

已读：
- **方法与公开包**：四份方法文档和角色卡；`public_read.md`；公开包的 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`，以及 `worktree_manifest.json` 的汇总字段。
- **工作树**：
  - `scrapy/exporters.py` 全文；
  - `scrapy/utils/python.py` 里的 `is_listlike`、`to_unicode`、`to_bytes`、`stringify_dict`；
  - `pytest.ini`、`conftest.py`、`.gitignore`；
  - `docs/topics/exporters.rst` 里讲 `export_empty_fields` 和 serializer 的段落。
- **私有包**：全部读过，包括 `gold.patch`、`hidden_tests/{__init__.py,test_1.py}`（全文 407 行，62 个测试体都读了）、`expected_output.json`、`run_tests.sh`、`grading_bundle.json`、`validation_bundle.json`、`revisions.json`（内容为空）、`run_refs.json`。
- **运行原件**：`run_refs.json` 里 4 个 current 行对应的账本行和 eval log，sha256 都与 `run_refs.json` 一致；M3 独立 runner 的两份 `test_output.txt`。
- **devcheck**：
  - `orig/` 下的命令清单、全部 captures、`attempt.json`、`prelaunch.json`、`activation_check.json`、`devcheck_stdout.json`、`post_run_facts_root.txt`，以及第一条桩请求；
  - `private_gold/private_control.json`。
- **跨题**：
  - 两份机械比对文件里与 scrapy 有关的行；
  - 同仓另外 4 题的公开包，只看了 `scrapy/VERSION`、`exporters.py` 里的 `PythonItemExporter`、`tests/test_exporters.py` 里的 binary 测试、`responsetypes.py`、`utils/misc.py:load_object`、`middleware.py`、`utils/conf.py:build_component_list`。

未读：任何历史或审查目录、本批 README、`assignments.json`、其它题的私有包、上游仓库和网络资料。

## 2. 核对公开读者的产物（步骤 1）

public_read 的推导都被执行证据证实了：
- **命令 A**：修复前依次输出 `{'name': b'John\xc2\xa3', 'age': b'22'}`、`['str', 'str']`、`False`。【执行：devcheck `captures/pr1_1_cmd.out`，agent 身份 54321】
- **命令 B**：修复前的 4 行输出与 public_read 的预测逐字一致。【执行：`pr2_2_cmd.out`】
- **公开测试**：整个文件 61 passed；`-k PythonItemExporterTest` 选中 8 个，8 passed，53 个 deselected。【执行：`pr3_3_pytest.out`、`pr3_4_pytest.out`】
- **环境**：`python` 指向 `/testbed/.venv/bin/python`；scrapy 版本 `1.1.0dev1`，从 `/testbed/scrapy/__init__.py` 导入；没有 pip；pytest 是 8.3.4。【执行：`env.out`】

public_read 没有捕获的内容，本审补上了哪些、还剩哪些未知：
- **真实消息，仍未知**：
  - `user_prompt.txt` 只是静态渲染。devcheck 桩请求里的用户消息是 devcheck 专用指令（"Devcheck run: execute exactly the tool calls…"），不是本题题面。
  - 所以模型实际收到的题面，以及 `public_hints` 会不会进入对话，都不知道。环境卡 §2 说 hints 写进容器里的 `/rh2/public_task_bundle.json`，不注入系统提示。
  - 对本题影响小：prelaunch 的 `config_env` 里 PATH 第一项就是 `/testbed/.venv/bin`，本题也不需要网络。
- **容器条件，已由 devcheck 补上**：
  - agent 的 uid 是 54321；`/testbed` 属主是 54321，可写；HOME 和 `/tmp` 可写；激活文件不可写。
  - 外网和外部 DNS 都被拒绝。
  - git 历史已清理：HEAD 是 `2514973242e3`，没有 refs、remote、reflog 和不可达对象；预检确认 HEAD 没有子提交。
  - 隐藏测试不可读。
- **pytest-twisted 没装**：每次运行都有 `PytestConfigWarning: Unknown config option: twisted`，来自 `pytest.ini:6`。本题的测试是纯 unittest，不受影响。
- **public_read R13 漏了一条路径**：R13 说非字符串的值在两种模式下都会抛错。它没注意到，`export_empty_fields` 的缺省值 `None` 在 base 里不经过 `_serialize_value`，所以 base 不会抛错。gold 的二次序列化让这条路径开始抛错，见 §6 G1。

## 3. 展开隐藏测试（步骤 2）

### 3.1 唯一的目标键

`PythonItemExporterTest.test_export_binary`（`hidden_tests/test_1.py:119-123`）：
- **调用**：`PythonItemExporter(binary=True).export_item(TestItem(name=u'John\xa3', age=u'22'))`。`TestItem` 定义在测试文件自己里（`:19-21`），有 `name`、`age` 两个 `Field`。
- **断言**：`assertEqual({b'name': b'John\xc2\xa3', b'age': b'22'}, 结果)`。这是普通的 dict 相等比较，不检查返回类型、键的顺序和嵌套结构。
- **公开依据**：与题面的 Example Code 和 Expected Behavior 原例逐字对应。
- **noop 下的失败原因**：`AssertionError: {b'name': b'John\xc2\xa3', b'age': b'22'} != {'name': b'John\xc2\xa3', 'age': b'22'}`。【执行：R-f noop log 第 34 行；09-24 复跑相同】这与题面的 Actual Behavior 相同。
- **gold 下**：PASSED。【执行：R-f 和 09-24 两次 gold log】

### 3.2 回归键（61 个，测试体逐条读过）

| 组 | 键数 | 与本题改动的关系 |
|---|---|---|
| `PythonItemExporterTest` 的其余 8 个 | 8 | 全部用 `binary=False`（`_get_exporter` 写死了 `binary=False`，见 `:85-86`）。它们保护 binary=False 下的行为不被改坏，具体如下。<br>• `test_nested_item`、`test_export_list`、`test_export_item_dict_list`：断言整个嵌套结构相等（键是 str），并且每层都是 `type(...)==dict`。<br>• `test_fields_to_export`：直接调用私有方法 `_get_serialized_fields`，期望得到 `[('name', u'John\xa3')]`。<br>• `test_serialize_field`、`test_field_custom_serializer`：直接调用 `serialize_field`。<br>• `test_export_item`、`test_export_dict_item`：`_check_output` 是 `pass`，只检查不抛异常。 |
| Base、Pprint、Pickle、Csv、Xml、JsonLines、Json、Custom 各类 | 53 | 不经过 `PythonItemExporter`。它们能拦住"在 `BaseItemExporter._get_serialized_fields` 里不分情况地转键"这类改法：JSON 编码遇到 bytes 键会抛错；Pickle 和 Pprint 的 `_assert_expected_item` 会比较 `self.i == dict`；XML 的元素名必须是 str。 |

弱键：`BaseItemExporterTest` 和 `PythonItemExporterTest` 各自的 `test_export_item`、`test_export_dict_item`，共 4 个键，只在抛异常时才会失败。

### 3.3 binary=True 下没有测到的

62 个测试里只有目标键用了 `binary=True`。以下情况都没测：
- dict 形式的 item；
- `fields_to_export`、`export_empty_fields`；
- 嵌套的 Item、dict、list；
- 自定义 serializer；
- 非默认的 `encoding`；
- 非 str 的键；
- 不传参数时默认 `binary=True` 的行为。

## 4. 双向映射（步骤 3）

需求编号沿用 public_read 的 R1–R13。

| 需求或旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖 | 执行证据 / 下一步验证 |
|---|---|---|---|---|
| R1 binary 下顶层键为 bytes（原例） | 题面 Expected Behavior | `test_export_binary`，整体相等 | 覆盖 | noop FAILED / gold PASSED【执行】 |
| R2 值仍按 `encoding` 转成 bytes | 题面；`exporters.py:268-269` | 同上，只测了默认的 utf-8 | 部分 | — |
| R3 binary=False 下键和值保持 str | 公开测试 `tests/test_exporters.py:83-116` | `test_nested_item` 等 3 个键，以及 `test_fields_to_export` | 覆盖 | noop 和 gold 都 PASSED【执行】；C3 可以实证 |
| R4 每层都是 dict；serializer 优先 | 公开测试（只有 binary=False） | 上面的类型断言；`test_field_custom_serializer` 只调 `serialize_field` | 部分（binary=True 缺失） | — |
| R5 binary 下嵌套 Item 的键为 bytes | 可推知 | 无 | 缺失 | gold 确实会转【执行：私有 gold 对照 pr2 第 1 行】 |
| R6 binary 下嵌套普通 dict 的键 | 公开材料有多种合理解释 | 无 | 缺失（因此两种解释都不会被拒） | gold 转成 bytes【执行：同上】 |
| R7 dict item 的顶层键为 bytes | 可推知（文档说 dict 可以作 item） | 无 | 缺失 | gold 会转【执行：pr2 第 3 行】；C2 |
| R8 用 `fields_to_export` 时同样转 | 可推知 | 无（`test_fields_to_export` 用的是 binary=False） | 缺失 | gold 会转【执行：pr2 第 4 行】 |
| R9 非 str 的键 | 多种合理解释 | 无 | 缺失 | gold 抛 `TypeError`【源码】 |
| R10 键用什么编码 | 多种合理解释 | 无（键全是 ASCII） | 缺失（两种做法都能通过） | gold 用默认 utf-8，不用 `self.encoding`【源码】 |
| R11 其它 exporter 的键保持 str | 公开测试 | 其它类的 53 个键 | 覆盖 | noop 和 gold 都 PASSED【执行】 |
| R12 默认 `binary=True`；未知参数抛 `TypeError` | `exporters.py:249-255` | 无（所有测试都显式传 binary） | 缺失 | — |
| 旧行为：binary + `export_empty_fields=True` 时，缺失字段返回 `None` | 文档 `docs/topics/exporters.rst:204-210`；`exporters.py:75-76` | 无 | 缺失，且 **gold 破坏了它** | E1 |
| 旧行为：binary 下字段 serializer 的输出原样保留 | 文档 serializer 段 `:88-106,158-166`；`exporters.py:257-259` | 无 | 缺失；gold 改成了二次序列化 | E1 |

反向核对：隐藏测试文件和公开的 `tests/test_exporters.py` 做 diff，差别只有新增的 `test_export_binary` 和一行 `import warnings`【执行 diff】。所以：
- 61 个回归断言都在求解者能看到的公开测试里；
- 唯一的新断言逐字来自题面原例。

没有哪条断言缺少公开依据。

## 5. R2E 专项（步骤 4）

- **(a) 非 PASSED 键**：没有，62 个键全是 PASSED（`expected_output.json`）。更完整的修复不会改变任何键的状态，例如把嵌套 dict 的键也转掉、键用 `self.encoding` 编码、或者让非字符串的值原样通过。按现有测试体，只有改坏了 binary=False 或者改坏了其它 exporter，回归键才会翻转。
- **(b) 题面描述的报错是否出现在 noop 目标键的失败原因里**：是，见 §3.1。【执行】
- **(c) 题面是否泄漏修法**：
  - 题面没有点名 `_serialize_dict` 或 `to_bytes`，也没说改哪一行。
  - 但 Expected Behavior 给出的精确 dict 就是隐藏断言本身。这属于需求，不算泄漏修法；不过目标断言因此完全公开，题目偏容易。
- **(d) 对 base 辅助代码的依赖、搬迁伪影、撞键**：
  - 隐藏测试文件自己定义了 `TestItem`，不从 `tests` 包导入辅助代码，只依赖 lxml、six、scrapy。
  - 它依赖仓库根目录的两个文件，二者都是 base 版本、候选可以改、评分时不会重置：
    - `pytest.ini`：`usefixtures = chdir`、`--doctest-modules`，`python_files` 里包含 `__init__.py`；
    - `conftest.py`：提供 `chdir` fixture；导入时用相对路径读取 `tests/py3-ignores.txt`，并导入 twisted。
  - 合法修复不会碰这些文件。反过来，如果删改了 `tests/py3-ignores.txt`，测试收集会失败，得 0 分；这属于候选自伤，不是误判。
  - 只有一个隐藏文件，62 个键没有撞键：收集到 62 个，解析出 62 个。
- **(e) 时间、随机、资源敏感的键**：
  - 没有。每次测试不到 1 秒，评分时内存峰值约 209 MB。【解析：账本的 `resource.mem_peak_mb`】
  - noop 和 gold 各跑了两次（R-f 09-23 和 09-24 复跑），两次日志除时间戳和耗时外逐字相同。【执行 diff】
  - M3 独立 runner 在来源镜像上跑了两次 gold，都是 62 passed。【执行】
- **(f) 材料修订**：没有。`revisions.json` 是 `[]`，`material_revisions` 为空，`env_recipe` 和 `resource_recipe` 都是 null。

## 6. gold 检查（步骤 5）

gold 只改了 `scrapy/exporters.py`。评分投影的 `included_paths` 是 `["scrapy/exporters.py"]`，`ignored_paths` 为空。【解析：gold 账本】

它有两处改动：
1. `_serialize_dict`：binary 时执行 `key = to_bytes(key)`，嵌套普通 dict 的键因此变成 bytes。
2. `export_item`：先照旧得到 `result`；binary 时再执行 `dict(self._serialize_dict(result))`。这一步把顶层键转成 bytes，同时也把**所有的值再过一遍 `_serialize_value`**。

gold 修到了原例。【执行：私有 gold 对照 pr1 输出 `True`；隐藏测试 62/62】gold 下公开的 exporter 测试仍然是 61 passed。【执行：私有 gold 对照 pr3】没有无关改动。

未测的回归和行为变化。下面都是**源码推断，没有运行**，并且只在 binary=True 时出现：
- **G1**：`PythonItemExporter(binary=True, export_empty_fields=True).export_item(TestItem(name=u'x'))`。
  - base：缺失的字段取 `default_value=None`，不经过序列化（`exporters.py:75-76`），结果是 `{'name': b'x', 'age': None}`。
  - gold：第二遍对 `None` 调用 `_serialize_value`。`is_listlike(None)` 为 False（`utils/python.py:68`），于是走到 `to_bytes(None)`，抛 `TypeError`（`utils/python.py:110-120`）。
  - `export_empty_fields` 是 `BaseItemExporter` 的文档化选项（`docs/topics/exporters.rst:204-210`）。
- **G2**：字段的 serializer 返回非字符串，例如 `int`。
  - base 原样保留，因为 `serialize_field` 用自定义 serializer 代替了 `_serialize_value`（`:257-259`）。
  - gold 第二遍执行 `to_bytes(int)`，抛 `TypeError`。
  - 如果 serializer 返回 str，gold 会把它再转成 bytes。这与题面"值都是 bytes"一致，但改变了"serializer 优先"的旧行为。
- **G3**：dict item 含非 str 的键，例如 `{1: u'a'}`。base 保留键 `1`；gold 执行 `to_bytes(1)`，抛 `TypeError`。
- **G4**：gold 的键用 `to_bytes(key)` 的默认 utf-8 编码，而值用 `self.encoding`。当键不是 ASCII、`encoding` 又不是 utf-8 时，两者不一致。

旁证：同仓的更新版本（`scrapy__75450e75…`、`a95a338e…` 公开工作树里 `exporters.py` 的 `_serialize_value`）已经改成只对 `str` 和 `bytes` 编码，其它值直接 `return value`。这说明上游后来消除了 G1 和 G2。这是公开代码，不是本题的材料。

判断：
- gold 可以作为本题的参考实现，但它不是没有回归的标准答案。
- 这些回归都不在隐藏测试里；合理的候选不论有没有同样的回归，得分都不受影响。
- 题面没提 `export_empty_fields`。如果为此补测试，就是把审查者自己的要求加进评分标准（清单第 28 项），所以**不建议改测试**，只做登记。

## 7. 可以区分结论的候选（交协调者用正式评分代码实跑）

- **C1 合理替代解（预期得 1）**
  - 做法：只改 `scrapy/exporters.py` 里的 `PythonItemExporter.export_item`：
    ```python
    def export_item(self, item):
        result = self._get_serialized_fields(item)
        if self.binary:
            return dict((to_bytes(k, encoding=self.encoding), v) for k, v in result)
        return dict(result)
    ```
  - 与 gold 的差别：`_serialize_dict` 不动，嵌套普通 dict 的键仍是 str；不做二次序列化，所以不会出现 G1、G2。嵌套的 Item 会经递归调用 `export_item`，键同样被转掉。
  - 预期：62 个键全部符合，reward 1。
  - 用途：证明测试不强制 gold 的嵌套 dict 行为，也不强制二次序列化。
- **C2 可能蒙混过关的部分解（预期得 1，但它本身有缺陷）**
  - 做法：改同一个位置，但只在 `self.binary and isinstance(item, BaseItem)` 时转键。这样 dict 形式的 item 在 binary 模式下仍返回 str 键，违反 R7。
  - 预期：reward 1。
  - 用途：实证"dict item 没测到"。
- **C3 错误解（预期得 0，可选）**
  - 做法：在 C1 的基础上去掉 `if self.binary` 判断，两种模式都转键。
  - 预期：reward 0。失配的键是 `PythonItemExporterTest.test_nested_item`、`test_export_list`、`test_export_item_dict_list`。`test_fields_to_export` 直接调用 `_get_serialized_fields`，不受影响。
  - 用途：实证回归键保护了 binary=False。
- **E1 本地函数对照（不是评分）**
  - 做法：在 base 和 gold 上各跑两例：
    - `PythonItemExporter(binary=True, export_empty_fields=True).export_item(TestItem(name=u'x'))`；
    - 一个带 `age = Field(serializer=lambda v: int(v))` 的 Item，取值 `age=u'22'`。
  - 预期：base 分别返回 `{'name': b'x', 'age': None}` 和 `{'name': b'x', 'age': 22}`；gold 两例都抛 `TypeError`。
  - 用途：把 G1、G2 从源码推断变成执行证据。

## 8. 开发需求（步骤 6）

devcheck 走的是正式启动路径，用真实 Claude Code 2.1.205 加桩端点，以 agent 身份运行，镜像是 `sha256:a2fe6dfe…`（`image_is_overlay_derived_id: true`）。私有 gold 对照用的是同一个镜像，以 root 身份运行，不联网。

| 项目 | 本题需求 | 证据 |
|---|---|---|
| 导入 | `from scrapy.exporters import PythonItemExporter`，scrapy 取自 `/testbed/scrapy` | 镜像层面实测（`env.out`） |
| 依赖 | six、lxml、twisted（`conftest.py` 会导入）、pytest，都已安装 | 实测：以 agent 身份跑公开测试 61 passed；评分时 62 个键都执行了 |
| pip 和新包 | 没有 pip；本题也不需要装新包 | 实测 |
| 资产 | 不需要 | 源码推断 |
| 权限 | 需要写 `scrapy/exporters.py`；测试时 `chdir` 会切到 tmpdir（`/tmp` 容量 1 GiB） | 实测：`WORKDIR_WRITABLE=1`、属主 54321、`TMP_WRITABLE=1` |
| 网络 | 准备、解题、安装、测试各阶段都不需要 | 源码推断；actor 外网被拒绝已实测 |
| 构建 | 不需要（纯 Python） | 源码推断 |
| 提交边界 | 只需改 `scrapy/exporters.py`。`*.pyc` 被 `.gitignore` 忽略；初态只有未跟踪的 `install.sh` 和 `run_tests.sh` | gold 投影实测；actor 候选的交付待 actor 验证 |
| 本地验证 | public_read 的命令 A、B 能区分修复前后，命令 C 用来防回归 | 实测：修复前以 agent 身份运行，修复后看私有 gold 对照 |
| 真实求解、实际消息、adapter 链路 | — | 待 actor 验证 |

注意镜像不一致：devcheck 用的镜像 ID 是 `a2fe6dfe…`，两次 current 评分运行用的是 `1517a0c4…`（`rh2-r2e-derived/scrapy:e938752973b4-r2e_derive_v1`）。两者都是派生镜像，但本目录里没有证据说明内容等价，可能是在不同机器上按同一配方重建的。在 `a2fe6dfe…` 上还没有跑过隐藏测试的 noop 和 gold 评分。

## 9. 八方面小结与 checks 初稿

| 方面 | 已查 | 未查或未知 |
|---|---|---|
| 公开需求 | 题面、base 源码、文档、公开测试。需求清楚；有歧义的 R6、R9、R10 都没有被测 | 实际渲染的消息，以及 hints 是否送达 |
| 材料与初态 | base、gold、隐藏测试、expected 相互对应；noop 的失败位置与题面一致 | — |
| 测试是否测到要求 | 62 个测试体全部读过；目标键就是题面原例 | binary 模式的其它路径漏测（C2 待实跑） |
| 是否误拒合理解 | 除了原例的精确输出，没有其它形式约束；没有非 PASSED 键 | C1 待实跑 |
| 回归与 gold 完整性 | 回归键保护了 binary=False 和其它 exporter；gold 有 G1–G4 | E1 待实跑 |
| 开发条件 | devcheck 实测了导入、pytest、权限、外网被拒 | 真实模型求解 |
| 交付与评分边界 | gold 投影只含源码；隐藏测试整个目录被替换 | 根目录的 `conftest.py`、`pytest.ini` 候选可写，并且评分时会加载（属共享机制，本题适用） |
| 题目关系与用途 | 同仓 5 题都逐一核对过（§10） | 预训练是否见过无法知道 |

checks 初稿（按 40 项清单编号，只记有结论的项）：

| 状态 | 编号 |
|---|---|
| pass | 1、2、4、6、8、9、10、11、13、14（次数有限）、16（gold 重放路径）、17、18、19、20、21、22、23、24（静态判断，C1 待实跑）、29、30、32 |
| issue | 5（同族包含关系）；25（低）；26（gold 的未测回归，低）；27（低） |
| unknown | 3；31（共享机制） |
| not_applicable | 7、12、28、37、38 |
| not_checked | 15、33–36、39、40 |

## 10. 题目关系（第 8 方面）

按公开工作树的代码判断，各题初始状态的先后是：
1. `9a15fcf8`：1.1.0dev1，exporter 没有 binary 选项，也没有 x-json 映射；
2. `cfed9b66`：1.1.0dev1，没有 binary，但有 x-json 映射；
3. **本题**：1.1.0dev1，有 binary；
4. `a95a338e`：2.7.0；
5. `75450e75`：2.7.1。

具体关系：
- **本题的修复被别的题包含**：
  - `a95a338e` 和 `75450e75` 的公开 `scrapy/exporters.py` 里有 `key = to_bytes(key) if self.binary else key`，也有 binary 下的二次序列化，只是方法改名为 `_serialize_item`；
  - 它们的公开 `tests/test_exporters.py:182` 有 `test_export_binary`。
  - 机械比对：gold 5 行中 4 行逐字命中，测试名比对也命中。已人工核实。
- **本题工作树包含别题的修复**：
  - `scrapy/responsetypes.py:27` 已经有 `'application/x-json': 'scrapy.http.TextResponse'`。这正是 `9a15fcf8` 的修复（其题面：x-json 被当成 `Response`）。机械比对也标出了这一对。
  - 这影响的是 `9a15fcf8` 的数据划分，不影响本题质量。
- **与 `cfed9b66` 互不包含**：
  - 按 `cfed9b66` 题面指向的两处代码，本题的 `middleware.py` 与 `cfed9b66` 初态逐字相同，`scrapy/utils/misc.py:load_object` 也一样，仍然直接调用 `path.rindex('.')`。据此推断本题初态**不含** `cfed9b66` 的修复（没有读它的私有 gold）。
  - 反过来也不含：`cfed9b66` 的 exporter 没有 `binary` 选项。
  - 机械比对也没有标出这一对，结论一致。
- **用途**：
  - 只要本题和 `a95a338e`、`75450e75` 不分别落在"训练"和"留出评测"两侧，就不构成答案泄漏。
  - 同族关系：本题的修复出现在 `a95a338e`、`75450e75` 里；`9a15fcf8` 的修复出现在 `cfed9b66`、本题、`a95a338e`、`75450e75` 里。
- **任务类型**：单个函数的 Py3 bytes/str 修复，目标断言完全公开，适合作为开发诊断用的冒烟题。难度和学习价值不做静态判断。

## 11. 缺口与未知

1. C1、C2、E1 还没实跑，目前是静态推断。这是唯一优先的下一步。
2. 实际题面消息和 `public_hints` 的送达方式没有验证（清单第 3 项）；真实模型求解（第 33–36 项）没有做。
3. 在 `a2fe6dfe…` 上还没有隐藏测试的评分。actor 和 grader 用同一张镜像，目前只是代码配置（环境卡 §2，待 A 线审查）。
4. 根目录的 `conftest.py` 和 `pytest.ini` 候选可写，评分时会加载。这是 R2E 共享的控制面问题，逐题只记"适用"。
5. 从 `/testbed` 以外的目录运行脚本时能否导入 scrapy（即是否做了 editable 安装）没有测。按公开建议在 `/testbed` 下运行没有问题。
