# pydantic__pydantic-5662 独立公开静态审查

## 题面先验：目标、旧行为与疑义

在阅读实现前，依据 `user_prompt.txt:10–49,58–70` 确定目标：保持模型处于比较左侧，使 `MyModel(foo="bar") == unittest.mock.ANY` 成立，并让有意支持模型的非 BaseModel 自定义比较对象有机会接手；不要求用户调换左右顺序。题面给出返回 `NotImplemented` 的候选方案，但没有将具体代码形状规定为唯一方案。

合理保留的旧行为是模型之间原有的相等性判定，以及不能处理模型的普通异类对象仍不相等。题面没有要求恢复 V1 的先转字典比较（其副作用恰是 side note 所述问题），也没有要求让所有异类对象都相等。初始疑义包括：模型间具体保留哪些规则、普通字典的地位、是否必须配置开关、是否需要性能阈值、直接调用 `__eq__` 与使用 `==` 是否应区别对待、Python/core 版本应以何者为准。

`public_bundle.json.public_hints` 声明只编辑 NON-TEST 源文件、测试文件会被重置、可运行窄范围测试；这些是公开来源中的提示内容。本轮静态阅读边界不是题目的额外开发要求。提示是否实际交付给 actor、以及 `/testbed`、预激活 conda 环境、bash/edit 工具是否实际可用均未捕获。

## 公开证据与可消解问题

本节相对路径均以 `runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-5662/` 为前缀。

- 根因明确：`base/pydantic/main.py:540–542` 的 `BaseModel.__eq__` 对非 BaseModel 直接返回 `False`，阻止此左操作数表达式使用对方的相等比较结果。此结论来自源码，不是运行复现。
- `main.py:544–561` 明确模型比较规则：泛型使用 origin 或实际类判断类型；类型不同即不等；`__dict__` 不同即不等；最后比较每个私有属性，未设置时使用 `Undefined`。这一区段的规则均应保留，不能用简单地比较 dump 或精确泛型参数替代。
- `base/tests/test_main.py:1965–2057` 的公开旧测试支持上述边界：相同模型相等；不同模型类型即使 dump 相同也不等；模型与普通 dump/dict 不等；显式字段集合差异不影响相等；私有属性差异影响相等；同一泛型 origin 的不同参数化以及嵌套泛型可相等。`base/docs/migration.md:38` 也明确模型不再与字典相等。因而支持异类对象反向比较不等于恢复 V1 的字典值相等规则。
- 题面 `user_prompt.txt:31–36` 已解释候选协议：返回 `NotImplemented` 让 Python 尝试对方比较。直接调用 `model.__eq__(other)` 可以得到这个哨兵，而 `model == other` 是完整的运算符处理；不能将两者预期结果混为一谈。将 `NotImplemented` 当作异常抛出、只特殊判断 ANY、直接无条件调用对方 `__eq__`，都不是题面所展示的一般协议语义。
- 在已查的 `main.py` 中未找到 `def __ne__`；本题核心是 `__eq__`，旧测试又大量使用 `!=`，因此回归核验应包含不等比较。没有公开依据要求另外添加 `__ne__`。
- 配置开关只在 `user_prompt.txt:49` 被条件性提出：若方案出现性能或其他坏影响才考虑。已读公开材料没有必须增加开关的要求。题面明确未做基准（47 行），也没有可量化的性能验收门槛；不能宣称性能已验证。
- `user_prompt.txt:76–81` 是报告者的历史软件环境（core 0.25.0、Python 3.10.1、macOS arm64）。该精确 base 的 `pyproject.toml:57–62` 则声明 Python >=3.7、core ==0.27.0、typing-extensions >=4.5.0、annotated-types >=0.4.0。开发环境应遵循所给 base 的兼容依赖声明，而不能将报告者机器规格强加给 actor。实际装了什么仍是 unknown。

## 合理实现范围与仍存不确定性

合理的最小修复位置是 `BaseModel.__eq__` 的非模型分支，使其参与 Python 的正常比较回退，并保留模型分支行为。可保留早返回结构，或重排为模型/非模型两个分支；具体控制流和解释注释是实现选择，不是公开题目唯一要求。本角色不可见 gold，也未修题。

明确验收目标是示例 ANY 通过；一般自定义对象应收到原始模型，并可决定 True 或 False；不支持比较的普通对象及普通字典不应因为修复而被无条件视为相等。自定义 BaseModel 子类主动覆盖比较、返回非布尔值的特殊对象、异常传播以及极端递归比较没有完整公开验收规格，不能推断隐藏要求。可按语言正常比较协议实现，不应为这些未给出的场景引入额外策略。

公开信息足够定位一个小范围行为修复，但不能由此推断实际 actor 已收到相同题面、源码无初始改动、依赖可导入或测试已能收集；更不能给出成功率、训练资格或实际 actor 资格结论。

## 开发需求与最小公开验证

以下命令仅是交给获准开发者在实际 actor 环境中的核验建议，本审查没有执行。命令以实际项目根 `/testbed` 为预期 cwd，是否存在和获准使用尚为 unknown。

| 操作或资产 | 公开依据 | 实际证据或 unknown | 最小公开验证命令与预期 |
| --- | --- | --- | --- |
| 确认题面、工作目录与源码初态 | prompt:1；bundle 的 workdir/base_commit；environment_brief.md | 精确 Git 静态导出可读；实际用户/system 消息、HEAD、status、初始改动 unknown | `pwd`、`git rev-parse HEAD`、`git status --short`；应确认真实根路径、对照 base，并解释已有差异；这些命令不能证明消息交付，消息另需实际记录 |
| 能读写非测试源文件 | public_hints 的 bash/edit 与 NON-TEST 约束；main.py:540–561 | 静态源码已读；actor 工具呈现、UID、文件权限 unknown | `test -r pydantic/main.py && test -w pydantic/main.py`；应返回成功；修复后 `git diff -- pydantic/main.py` 可审阅行为改动，`git diff --name-only` 确认改动范围 |
| 可用 Python 与匹配依赖 | pyproject.toml:57–62；测试导入段 | 仅有版本声明，激活环境、解释器、导入来源、core 二进制可用性 unknown | `python -c "import sys, pydantic, pydantic_core; print(sys.executable, pydantic.__file__, pydantic_core.__version__)"`；预期导入当前项目且 core 为 0.27.0，不应误用其他 site-packages |
| 执行题面最小行为复现 | prompt:58–70 | 代码公开；未执行，实际结果 unknown | 下方内联命令；旧源码预期在 ANY 断言失败，修复后全部通过 |
| 保留旧模型相等规则 | test_main.py:1941–2057；migration.md:38 | 旧测试文本已读；pytest 及插件安装、收集与执行结果 unknown | `python -m pytest -q tests/test_main.py -k model_equality`；预期相等、类型、dump、fields_set、私有属性、泛型相关旧例通过；这组旧例单独通过不证明 ANY 已修复 |
| 有 pytest 及所需测试依赖 | pyproject.toml:97–104、139–145；test_main.py:1–41；conftest.py:1–86 | 依赖声明和导入可读，真实安装/缓存/联网权限 unknown | 上述窄测试命令能完成收集并执行即提供相关运行证据；导入或插件缺失应记录具体失败，不能由导出目录未包含依赖断言镜像缺失 |

最小行为验证示例（只列出，未执行；不需要修改测试文件）：

```sh
python - <<'PYCODE'
from unittest.mock import ANY
from pydantic import BaseModel

class MyModel(BaseModel):
    foo: str

m = MyModel(foo='bar')
assert m == ANY
assert not (m != ANY)
assert m != {'foo': 'bar'}
assert m != object()

class Matcher:
    def __init__(self, answer):
        self.answer = answer
        self.seen = None
    def __eq__(self, other):
        self.seen = other
        return self.answer

for answer in (True, False):
    matcher = Matcher(answer)
    assert (m == matcher) is answer
    assert matcher.seen is m
PYCODE
```

ANY 是 Python 标准库资产；示例没有外部数据、网络服务、GPU 或模型实验需求。并非断言实际环境具备这些资产。安装或下载是否必要只能在实际依赖核验后决定，本轮不安装、不联网。

## 阅读范围及封存说明

实际读过：派发卡全文、`roles/public_reader.md` 全文；本题 `user_prompt.txt` 全文（1–83）、`environment_brief.md` 全文、`base_identity.json` 全文、`public_bundle.json` 全文；`base/pydantic/main.py:505–580`（聚焦 540–561）；`base/tests/test_main.py:1–85,1930–2085`（聚焦 1941–2057）；`base/tests/conftest.py:1–86` 全文；`base/docs/migration.md:20–60`；`base/pyproject.toml:1–160`。另对本题公开目录做了文件名清单，对 main.py 查询 `def __eq__|def __ne__|NotImplemented`，对 test_main.py/test_generics.py/migration.md 查询 `equal|equality|__eq__|mock|ANY`，仅阅读命中输出；未通读 test_generics.py。

未读：其余源码、文档、旧测试与锁文件的正文；HISTORY.md 和 changes 正文；任何私有材料、历史质量结论、manifest/assignments、准备报告、内部账本、其他题或角色结果；未跟随链接。文件名出现在清单中不代表已阅读其内容。

`base_identity.json` 声明 base_commit 为 `0346ddb6a35770007f32815d8e4a179b778e0ef4`，288 个跟踪条目均静态落地、无软链/gitlink/未落地 LFS 指针，并声明 blob 核验通过。本审查只引用该公开身份声明，没有再次全量核验，也没有将其当作 actor 工作树或镜像资产证明。本轮只执行静态文件读取/搜索以及报告写入与 SHA256 计算，未运行、导入或测试项目。此报告一次写入后封存，哈希在交付消息中报告。
