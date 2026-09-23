# pydantic__pydantic-5706 公开材料静态审查

本审查仅使用公开阅读角色卡及本题 PUBLIC_DIR。未运行项目代码、安装依赖、修改 base、访问网络、读取私有材料或未来历史。下文路径相对于本题 PUBLIC_DIR；行号对应静态导出。结论不是运行验证，也不提供通过/淘汰标签。

**1. 需求表**

核心问题可以定位，但最终行为存在实质歧义。issue 不只报告失败，还提出“schema 生成失败时 JSON 验证也应拒绝”的方向；仓库的序列支持和 JSON/Python 分流能力，又使“支持合法 JSON 数组并生成对应 schema”成为可解释的修复方向。公开材料未给出维护者对此方向的澄清。

| 行为 | 公开依据 | 要求强度与解释 |
| --- | --- | --- |
| 调查并修正 `Sequence[int]` 在 JSON Schema 与 JSON 验证间的不一致 | `user_prompt.txt:3,10–15,21–33` | 明示。最小例子同时包含 `Sequence[int]` 与 `list[int]`。 |
| schema 生成失败时，不应继续把输入当作可验证模型处理 | `user_prompt.txt:11–15` | issue 明示的期待方向，但以未勾选项及 “seems as a correct behavior” 表达；没有规定应抛何种异常、在哪个阶段抛出、是否适用于所有类型。示例 JSON 验证本来已抛 `ValidationError`，所以“应抛异常”本身不足以定义修复。 |
| 是否改成两条路径均成功：为 `Sequence[int]` 生成整数数组 schema，并接受 JSON 数组 | `base/pydantic/_internal/_generate_schema.py:826–845`；`base/pydantic/json_schema.py:332–336,567–571`；`base/tests/test_json_schema.py:692–705` | 仓库支持能力可以合理推导此方向，但不是题面明示的成功标准。不能把“schema 不可导出”自动等同于“core validation schema 无效”，也不能静默把报告者的拒绝方向改成接收方向。 |
| 保留 Python 输入的序列语义 | `base/tests/test_types.py:1876–1891,2029–2144`；`base/pydantic/_internal/_validators.py:46–74` | 已有公开契约：list 保持 list；tuple/deque 按原容器重建；range 变为 list；元素类型仍校验，错误位置仍指向元素。不能为解决 JSON 路径而把所有 Python 序列直接压成 list。 |
| 保留非序列与字符串的拒绝行为 | `base/tests/test_types.py:2010–2026,2080–2097`；`base/tests/test_edge_cases.py:2480–2522` | 已有公开契约：Python generator、set 不因可迭代就成为合法 `Sequence[T]`；纯 str/bytes 拒绝，已有 `sequence_str` 错误约定。 |
| 保留现有 API、模型结构与普通列表行为 | `base/pydantic/main.py:415–440,630–655`；`base/tests/test_json_schema.py:676–685,692–748` | 合理推知。真正 API 是 `model_validate_json`；题面文字中的 `BaseModel.validate_json` 可由示例和源码消除命名歧义，不构成开发障碍。schema 默认 mode 为 `validation`、`by_alias=True`。 |
| TypeAdapter、`Sequence[Any]`、无参数 Sequence、strict、嵌套类型和 serialization mode 的范围 | `base/pydantic/type_adapter.py:72–76,104–128,149–163,256–276`；`base/pydantic/_internal/_generate_schema.py:830–845`；`base/pydantic/_internal/_std_types_schema.py:557–600` | 共享实现意味着需要兼容性调查，但题面没有逐项规定验收。尤其 Any 分支不同，不能仅据 `Sequence[int]` 例子臆定其全部行为。 |

issue、harness 与环境声明须分开：

- **issue 目标**：上述 JSON/Sequence 行为，来自 `user_prompt.txt:3–45`。
- **harness 操作指令**：探索代码、修改非测试源码、禁止改测试、窄范围运行测试、完成后简短总结，来自 `public_bundle.json:1` 的 `public_hints`，并非业务语义。
- **待验环境声明**：`/testbed`、conda `testbed` 已激活、python/pip/测试工具已就绪，来自同一字段；它们不是实际运行证据。bundle 未出现在静态用户消息正文不意味着 actor 不可读（`environment_brief.md:18–24`）。

**2. 合理实现范围**

在目标明确为支持 JSON 数组的前提下，可以采用统一构建序列 schema、组合现有 JSON/Python 分流能力、或对 JSON 验证与 schema 导出分别做局部适配等不同组织方式；不应限定某个内部 helper 名称、修改文件清单或 core-schema 字典形状。可观察结果应保持一致，并保留前述 Python 契约。现有代码已经提供独立的 JSON/Python 分支机制和 JSON Schema 对该机制的处理，见 `base/pydantic/_internal/_std_types_schema.py:532–549`、`base/pydantic/json_schema.py:567–571`。

在目标明确为拒绝该 JSON 用法的前提下，调用入口检查或相应类型的 JSON 分支拒绝都可能是实现组织方式；但需要公开补充异常类别、作用范围，以及“早于什么阶段”的标准。不能仅改变错误字符串就宣称解决了题面所说的“仍尝试验证”。

两种方向都能从当前材料解释出来，但结果相反，不能据公开材料断言其中一种就是唯一合法答案。这是需求方向的不确定性，不是要求披露隐藏测试或参考补丁。

有实际约定的输出包括普通整数列表的 `type: array` / `items: {type: integer}`、模型字段标题与 required 字段，以及既有 Python 错误的类型和位置（`base/tests/test_json_schema.py:676–748`、`base/tests/test_types.py:2010–2144`）。若选择支持 Sequence 的方向，复用这些结构是合理推知；无依据要求新的私有辅助函数名或 JSON 键插入顺序。

JSON Schema 不能生成，并不普遍意味着模型不能用于其他操作：现有 Enum 测试可成功构建、dump 和 dump_json，同时明确期待 model_json_schema 失败（`base/tests/test_types.py:1422–1450,1453–1484`）。因此若采用拒绝方向，不宜未经公开目标确认就扩展为模型构造、Python 验证或序列化的全局禁止。上述测试没有直接决定此类模型的 JSON 输入规则。

“禁止改测试”若适用，以上行为方向均未显现必须修改测试文件才能实现的障碍；可使用临时命令复现并运行已有测试。它会限制把新回归用例写入测试文件。若原指令不适用，添加测试可以是正常开发操作，但仍不能据此推断所有文件都会被保留或计分。旧提示所说“所有测试改动都会恢复、永不计分”不是当前机制的已核实描述；`environment_brief.md:18–24` 明确说明目前无按测试文件名统一排除，仍有官方文件恢复等具体限制。本审查未核验哪些文件受影响，不取消原指令，登记为共享输入/运行条件问题。

**3. 初态线索与疑义**

调查入口充分：

1. 最小复现、字段定义、两次 API 调用、异常和报告者版本已给出（`user_prompt.txt:21–44`）。
2. `model_validate_json` 直接交给 `__pydantic_validator__.validate_json`（`base/pydantic/main.py:415–440`），模型构建由 GenerateSchema 创建 core schema，再实例化 SchemaValidator（`base/pydantic/_internal/_model_construction.py:172–209`）。
3. 参数化 Sequence 的通用分派可到 `_sequence_schema`，非 Any 分支先做 Sequence 实例检查，再包装 list 元素验证（`base/pydantic/_internal/_generate_schema.py:471–474,826–845`）。
4. JSON Schema 的 chain 默认取第一步，is-instance 默认不能导出 JSON Schema（`base/pydantic/json_schema.py:323–336,546–551,1209–1215`）。这能静态解释题面中的导出错误；core 扩展在 JSON 模式下的实际异常仍需运行核验。
5. 已有 Python 行为和相邻 list schema 测试可作为回归入口。阅读调用者、分派与包装器是正常开发调查，不是题面缺失。

实质未知与普通调查项：

- **会影响正确验收方向**：接收 JSON 数组还是更早拒绝；若拒绝，精确的异常/阶段/泛化范围。最小补充是来自问题发生时的公开目标说明，不需要未来修复或私有预期。
- **会影响复现，不足以认定不可开发**：报告者是 Pydantic 2.0a3 / core 0.25.0（`user_prompt.txt:40–43`），base 声明 2.0a4 / core 0.31.0（`base/pydantic/version.py:3`、`base/pyproject.toml:60–65`）。不应安装报告者旧版覆盖基线；先验证 actor 的版本、导入路径及两次调用的现象。
- **可由仓库继续调查**：无参数 Sequence/Any 的边界、strict、泛型、schema mode；类型别名与注解预处理并非只有一个入口（`base/pydantic/_internal/_generate_schema.py:1050–1099`、`base/pydantic/_internal/_std_types_schema.py:557–600`）。无需外部服务或完整历史才能先开展调查。
- **公开文档有陈旧内容**：`base/docs/usage/types/sequence_iterable.md:116–118` 说 Sequence 会消费 generator，但 `base/tests/test_types.py:2010–2026` 和实例检查拒绝 generator；`base/docs/install.md:7–9` 只列 typing-extensions，而 pyproject 还要求 annotated-types 和 pydantic-core。应记录冲突，并用当前代码/测试/依赖声明确认基线，不能把旧文档一句话当作扩大本题范围的指令。
- **缺失运行事实**：原生 core 扩展及其依赖是否预装、actor 是否导入本工作区、缓存/临时目录是否可写、所列测试能否收集均未验（`environment_brief.md:3–13`）。静态包没有 core 扩展源码或其实际安装目录的证据；本题通常只需可导入的兼容扩展，不必先要求编译 Rust。
- 未发现复现必须依赖但未收录的外链附件、数据集、凭证或数据库。通用外部文档链接不是本题最小复现的必要材料。未请求祖先历史，未访问共享镜像克隆。

**4. 开发需求表**

以下命令均为 **建议，未执行**，应由实际 actor 在目标容器 `/testbed`、CPU 条件下运行。它们不是本静态审查已经完成的验证。资源说明仅提供默认计划值，不能据此保证成功。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 缺口及最小验证 | 预计现象 |
| --- | --- | --- | --- | --- |
| actor、工作目录与可写工作区 | `public_bundle.json:1`；`environment_brief.md:8–12` | 声明 bash/edit、/testbed、agent/54321 和可写 workspace/home | 建议，未执行：`id`、`pwd`、`test -w /testbed`、`python -c "import tempfile; f=tempfile.TemporaryFile(); f.close()"` | actor/workdir 与声明一致，临时文件可用；失败为环境缺口，不是 Sequence 修复失败。 |
| Python 与原生 pydantic-core；typing-extensions、annotated-types | `base/pyproject.toml:60–65`；`base/pydantic/__init__.py:1–2`；`base/pydantic/version.py:3` | conda 激活仅是旧提示；真实镜像依赖未验，公网下载不保证 | 建议，未执行：`python -B -c "import sys, pydantic, pydantic_core, annotated_types, typing_extensions; from pydantic import BaseModel, TypeAdapter; print(sys.executable); print(pydantic.__file__); print(pydantic.__version__, pydantic_core.__version__)"` | 从工作区导入 Pydantic，基线预期 2.0a4 / core 0.31.0；缺包、ABI 或版本不符须先解决。 |
| 最小复现，不需数据资产/网络/服务 | `user_prompt.txt:21–33`；相关源码入口如上 | 仅 CPU 计划，实际导入/执行尚未核验 | 建议，未执行：运行下方复现命令 R1。按原例使用 `list[int]` 需 Python 3.9+；报告者为 3.10.11。旧 Python 可等价用 `typing.List[int]`。 | 初态预计 schema 导出触发 is-instance 不支持错误，JSON 验证不能正常得到示例模型；异常类别/文本以 core 0.31.0 实测为准。 |
| Python Sequence 兼容性测试 | `base/tests/test_types.py:1876–2144,4726–4745`；测试导入 `base/tests/test_types.py:36–41` | 未证明 pytest、dirty-equals 等测试依赖可导入 | 建议，未执行：`python -m pytest -q tests/test_types.py -k sequence` | 旧的成功/失败类型契约应保持通过；这些测试不直接证明本题 JSON 缺陷已修复。 |
| 纯字符串拒绝回归 | `base/tests/test_edge_cases.py:2480–2522`；导入见该文件 `24–27` | 同上，版本过低会 skip | 建议，未执行：`python -m pytest -q tests/test_edge_cases.py -k test_sequences_str` | Python 3.9+ 应覆盖 list、Sequence[str]/Sequence[bytes] 的既定错误；skip 不能视为已验行为。 |
| 相邻 JSON Schema 回归 | `base/tests/test_json_schema.py:676–748,1185–1202,1281–1286` | 仅提供旧公开测试；不要求全仓测试均可运行 | 建议，未执行：`python -m pytest -q tests/test_json_schema.py -k 'test_list or test_callable_type or test_error_non_supported_types'` | 原有数组结构和不支持类型行为应保持。测试通过不解决 Sequence 成功/拒绝方向的需求歧义。 |
| 开发依赖/打包，仅在缺失时需要 | `base/pyproject.toml:1–3,100–107`；`base/Makefile:12–15,51–53`；`base/docs/contributing.md:32–52` | 公网受限，未证明 PDM、hatchling、readme 构建插件或离线轮子已具备 | 不默认运行联网 `make install`。若确需本地可编辑安装且构建依赖已有：建议，未执行：`python -m pip install --no-deps --no-build-isolation -e .`。若需构建 smoke 且 backend 已有：建议，未执行：`python -m pip wheel --no-deps --no-build-isolation --no-index . --wheel-dir /tmp/pydantic-audit-wheel`。 | 应在无依赖下载条件下安装/产出本基线 wheel；若缺构建 backend/依赖，需提供离线资产或修正镜像。这不是本题必须先完成的全仓构建步骤。 |
| 外部服务/GPU/大型资产 | 最小复现仅标准库类型、BaseModel 和 core；`base/docs/contributing.md:32–34` 声明测试无需数据库 | 2 CPU/4 GiB 等仅默认资源声明，`environment_brief.md:10–12` | 最小路径无额外服务需求；资源与平台以 actor 实测为准 | 不需要网络 API、数据库或 GPU 才能复现。 |

R1，**建议，未执行**。两个调用分别捕获异常，避免 schema 失败后无法观察 JSON 验证；这里只记录现象，不提前选定修复方向：

```bash
python -B - <<'PY'
from typing import Sequence
from pydantic import BaseModel

class Model(BaseModel):
    int_sequence: Sequence[int]
    int_list: list[int]

payload = '{"int_sequence": [1, 2, 3], "int_list": [1, 2, 3]}'
operations = (
    ("python", lambda: Model(int_sequence=[1, 2, 3], int_list=[1, 2, 3])),
    ("json_schema", Model.model_json_schema),
    ("json_validation", lambda: Model.model_validate_json(payload)),
)
for label, operation in operations:
    try:
        print(label, "OK", operation())
    except Exception as exc:
        print(label, type(exc).__name__, str(exc))
PY
```

初态的 Python 调用应成功。若公开目标补充确认为支持数组，则修复后另外两项也应成功且数组元素为整数；若确认为提前拒绝，则需要先补充拒绝类别/时机后制定判据。捕获异常的 R1 退出码为零不表示 bug 已修复，应检查各标签输出。最小导入/复现/所列 pytest 足以启动本题调查；make 全仓检查、文档构建和额外联网集成不是必要前置条件。

**5. 阅读范围与限制**

实际打开或返回正文的文件/片段：

- 公开阅读角色卡；`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json` 全文。
- `base/README.md:1–68`、`base/Makefile:1–105`、`base/pyproject.toml:1–205`、`base/docs/install.md:1–40`、`base/docs/contributing.md:28–78`。
- `base/pydantic/_internal/_generate_schema.py:350–490,795–855,1045–1102`；`base/pydantic/_internal/_validators.py:1–110`；`base/pydantic/_internal/_std_types_schema.py:468–601,620–649`；`base/pydantic/_internal/_model_construction.py:165–212`。
- `base/pydantic/main.py:380–444,628–658`；`base/pydantic/type_adapter.py:60–128,125–166,250–278`；`base/pydantic/json_schema.py:305–340,395–420,540–575,1204–1218`；`base/pydantic/errors.py:132–152`；`base/pydantic/version.py:1–30`。
- `base/tests/conftest.py:1–94`；`base/tests/test_types.py:1–135,1410–1490,1815–2160,4630–4745` 中返回的片段；`base/tests/test_json_schema.py:1–100,667–750,1176–1206,1265–1290,2392–2448`；`base/tests/test_edge_cases.py:1–65,2466–2530`；`base/tests/test_generics.py:1405–1441,2144–2208`。
- `base/docs/usage/types/sequence_iterable.md:1–125`；`base/docs/usage/schema.md:1–145`。
- 补充检索命中包含 `base/pydantic/__init__.py`、`base/tests/test_main.py`、`base/tests/test_json.py`、`base/tests/test_prepare_annotations.py`、`base/docs/usage/types/standard_types.md`、`base/docs/plugins/schema_mappings.toml`；这些仅查看搜索返回行，未整文件阅读。
- 对 PUBLIC_DIR 做文件名清单查询，以及对相关源码/公开 tests 做 Sequence、schema、调用接口关键词检索。首次全清单和一批较大输出被工具截断；关键 Sequence 测试、文档和 API 片段随后单独读取。尝试读取 `docs/usage/json_schema.md` 发现不存在，随后按实际文件名读取 `docs/usage/schema.md`，未把路径错误视为材料缺失。

未查项：未读整个仓库、完整锁文件内容、未读 Git/祖先历史、外链正文、真实容器、实际 CLI 消息、工具权限、网络规则实测或私有验收。没有访问角色卡父目录、其他题或旧结论。没有看到本题私有材料。

`base_identity.json:3–11` 记录指定提交、无 Git 元数据等导出信息；这不是实际容器完整性验证。`environment_brief.md:3–6,18–24` 明确 user_prompt 只是静态渲染，public_hints 的消息位置、真实镜像附加文件与运行条件尚未核验。本次只遵守公开读取范围的协作约定，不宣称文件权限隔离、预训练无污染或开发条件已通过。

