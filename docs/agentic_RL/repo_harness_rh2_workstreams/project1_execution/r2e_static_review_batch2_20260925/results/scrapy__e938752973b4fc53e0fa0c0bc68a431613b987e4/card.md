# scrapy__e938752973b4fc53e0fa0c0bc68a431613b987e4 审查短卡

R2E 私有主审，2026-09-25，`static_review`。前稿是 `analysis_before_history.md`，历史核对见 `old_findings_delta.md`。

## 1. 题目与建议用途

- **问题**：在 Python 3 下，`PythonItemExporter(binary=True).export_item()` 的值已经是 bytes，但键仍是 `str`。题目要求把键也转成 bytes。
- **修复范围**：只需改 `scrapy/exporters.py`。
- **版本**：base `2514973242e3`，scrapy 1.1.0dev1，Python 3.9.21；没有材料修订。
- **隐藏测试**：公开的 `tests/test_exporters.py`，再加一个新增的 `test_export_binary`。62 个键全部期望 PASSED，其中目标键 1 个，回归键 61 个。
- **建议**：作为开发诊断用的静态候选，状态 `needs_review`，待 actor 验证。

## 2. 关键映射

| 需求或旧行为 | 公开依据 | 测试 ID / 断言 | 覆盖 | 证据 / 下一步 |
|---|---|---|---|---|
| binary 下顶层键为 bytes（题面原例） | 题面 Expected | `PythonItemExporterTest.test_export_binary`：整个 dict 相等 | 覆盖 | noop FAILED、gold PASSED，各有两次执行 |
| binary=False 下键和值保持 str | 公开测试 | `test_nested_item`、`test_export_list`、`test_export_item_dict_list` | 覆盖 | 执行；C3 |
| 其它 exporter 的键保持 str | 公开测试 | 其它 8 个类共 53 个键 | 覆盖 | 执行 |
| binary 下的 dict item、`fields_to_export`、嵌套结构 | 可推知 | 无 | 缺失 | C2 |
| binary 下 `export_empty_fields` 的缺失字段为 `None`；serializer 输出原样保留 | 文档与 base 源码 | 无 | 缺失；gold 破坏了这两条 | E1 |

## 3. 八方面

- **公开需求**：
  - 已查：题面、源码、文档、公开测试。
  - 嵌套 dict 的键、非 str 键、键的编码都没有约定，但测试也都没有测。
  - 未查：模型实际收到的渲染消息。
- **材料与初态**：已查。noop 的失败原因行与题面一致。
- **测试是否测到要求**：
  - 62 个测试体全部读过。
  - 目标断言就是题面原例。
  - binary 模式的其它路径没有测。
- **是否误拒合理解**：
  - 没有发现。
  - 期望里没有非 PASSED 键，也没有对内部结构的约束。
  - C1 待实跑确认。
- **回归与 gold**：
  - 回归键保护了 binary=False 和其它 exporter。
  - gold 有未测回归，E1 待实跑。
- **开发条件**：
  - devcheck 实测了导入、pytest 8.3.4、权限和断网。
  - 没有 pip。
  - 抓取类公开测试有与本题无关的失败。
  - 真实模型求解还没做。
- **交付与评分边界**：
  - gold 投影只含 `scrapy/exporters.py`。
  - 评分时隐藏测试整个目录被替换。
  - 共享机制沿用平台层的审查。
- **题目关系**：同仓 5 题都已核对，见第 4 节第 3 条。

## 4. 具体问题（按证据层次）

1. **漏测**（低，静态推断）：
   - binary 模式只测了顶层原例。
   - 只处理 Item、不处理 dict item 的实现也能得 1。
   - 不建议补测试，因为题面只给了顶层例；用 C2 实跑确认。
2. **gold 的未测回归**（低，静态推断）：
   - gold 在 binary 模式下把所有值再序列化一遍。当 `export_empty_fields=True` 且字段缺失，或者 serializer 返回非字符串时，会抛 `TypeError`；base 在这两种情况下都正常。
   - 这不影响任何键。
   - 不补测试：题面没提这些情况，补了就是把审查者自己的要求加进标准。用 E1 实跑确认。
3. **同仓包含关系**（中，影响数据划分，已人工核实）：
   - 本题的修复和 `test_export_binary` 出现在 `a95a338e`、`75450e75` 的公开初态里。
   - 本题初态含有 `9a15fcf8` 的一行修复（`scrapy/responsetypes.py:27`）。
   - 本题与 `cfed9b66` 互不包含。
   - 划分数据时把它们当同族处理。
4. **解题侧条件**（低，实测）：
   - 没有 pip。
   - `tests/test_closespider.py` 等抓取类测试因 Twisted 24.11 恒失败，与本题无关。
5. **未知项**：
   - 模型实际收到的题面和 `public_hints` 还没有捕获。
   - devcheck 用的镜像 `a2fe6dfe…` 与评分运行的镜像 `1517a0c4…` ID 不同，前者上还没有做过隐藏测试评分。

环境侧：本题没有配方，也没有材料修订。历史环境记录（`environment_qualified`）的证据经本审复核成立。

## 5. 待实跑的候选与对照（交协调者）

C1–C3 都只改 `scrapy/exporters.py` 里的 `PythonItemExporter.export_item`，`_serialize_dict` 不动。

- **C1 合理替代解**
  - 改法：函数体改为 `fields = self._get_serialized_fields(item)`；binary 时 `return dict((to_bytes(k, encoding=self.encoding), v) for k, v in fields)`，否则 `return dict(fields)`。
  - 预期：reward 1，62/62，没有不符键。
- **C2 不完整实现**
  - 改法：保留 `result = dict(self._get_serialized_fields(item))`，只在 `self.binary and isinstance(item, BaseItem)` 时执行 `result = dict((to_bytes(k), v) for k, v in result.items())`，然后 `return result`。
  - 预期：reward 1，没有不符键。dict item 在 binary 下仍是 str 键，但测试不查这一点。
  - 本地佐证：
    - 在 C2 状态下跑 public_read 的命令 B，第 3 行应与 base 相同，仍是 str 键：`3 {'name': b'John\xc2\xa3', 'age': b'22'}`。
    - gold 下这一行是 bytes 键，私有 gold 对照已经实测过。
- **C3 错误实现**
  - 改法：`return dict((to_bytes(k, encoding=self.encoding), v) for k, v in self._get_serialized_fields(item))`，不看 `self.binary`。
  - 预期：reward 0，59/62。不符的是下面 3 个键，期望 PASSED，实际 FAILED：
    - `PythonItemExporterTest.test_nested_item`
    - `PythonItemExporterTest.test_export_list`
    - `PythonItemExporterTest.test_export_item_dict_list`
- **E1 gold 回归对照**（不是评分）
  - 在私有容器的 `/testbed` 下，分别在 base、gold、C1 三种代码状态运行下面的脚本：

```bash
cd /testbed && python - <<'PY'
from scrapy.item import Item, Field
from scrapy.exporters import PythonItemExporter

class TestItem(Item):
    name = Field()
    age = Field()

class IntItem(Item):
    name = Field()
    age = Field(serializer=lambda v: int(v))

def show(label, make):
    try:
        print(label, repr(make()))
    except Exception as e:
        print(label, 'RAISES', type(e).__name__, str(e))

show('E1a', lambda: PythonItemExporter(binary=True, export_empty_fields=True).export_item(TestItem(name=u'x')))
show('E1b', lambda: PythonItemExporter(binary=True).export_item(IntItem(name=u'x', age=u'22')))
show('E1c', lambda: PythonItemExporter(binary=False, export_empty_fields=True).export_item(TestItem(name=u'x')))
PY
```

| 代码状态 | E1a | E1b | E1c（对照） |
|---|---|---|---|
| base | `{'age': None, 'name': b'x'}` | `{'name': b'x', 'age': 22}` | `{'age': None, 'name': 'x'}` |
| gold | `RAISES TypeError to_bytes must receive a unicode, str or bytes object, got NoneType` | `RAISES TypeError to_bytes must receive a unicode, str or bytes object, got int` | 同 base |
| C1 | `{b'age': None, b'name': b'x'}` | `{b'name': b'x', b'age': 22}` | 同 base |

说明：
- E1a 的字段顺序来自 `ItemMeta` 按 `dir()` 排序，所以 age 在 name 前；E1b 的顺序来自构造参数的顺序。
- `PendingDeprecationWarning` 在默认设置下不显示。

## 6. 静态建议与下一步

- **建议**：
  - 保留原版材料，不改测试和 expected。
  - 作为开发诊断用的静态候选。
  - 划分数据时，与 `a95a338e`、`75450e75` 按同族处理。
- **历史环节**：
  - 没有推翻任何旧主张，处置不变。
  - 补上了两条事实："`cwd=/tmp` 时可以导入"，以及抓取类公开测试的噪声。
  - 旧记录里"提示与环境矛盾"一条已经过时。
- **reviewer**：还没有。
- **唯一优先的下一步**：用正式评分代码一批实跑 C1、C2（C3 可以同批），同时在私有容器里跑 E1。
