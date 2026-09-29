# pydantic__pydantic-5386 公开静态阅读报告

本报告仅依据指定角色卡与本题公开目录。下文 `P/` 指 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-5386/`，`B/` 指其 `base/`。静态 base_commit 为 `6cbd8d69609bcc5b4b383830736790f9b8087e36`（`P/base_identity.json:3`），不是实际 actor 初始工作树。未执行项目、导入、测试或联网；未读取 gold、隐藏测试、历史或其他报告，未实际修题。

## 题面目标、约束和先验疑义

- 目标：在模型类定义阶段、不实例化模型，取得该类所有字段及其元数据，以便父类检查子类字段是否提供示例（`P/user_prompt.txt:3,10–12,23–34`）。“检查每个字段都有示例”是使用场景，不要求库默认强制所有字段提供示例。
- 初始疑义：这是 `__fields__` 更名问题，还是 `__init_subclass__` 调用时序问题？必须保留普通 Python 钩子的同名接口，还是可提供字段就绪后调用的新接口？字段就绪是否等于所有前向引用已解析、模型可以实例化？题面未规定新接口名称、签名或多继承调用策略。
- 示例是意图草图：第 21、32 行缺 `class`，第 25 行 `_checker` 未通过类引用，第 33 行使用单数 `example=`。不能把原样执行该片段作为修复成立的条件，也不能把根验证器的输入值与类字段定义混为一谈。
- `P/public_bundle.json:1` 的 `public_hints` 要求修改 NON-TEST 源文件、不修改测试、验证保持单文件/模块范围；声明 `/testbed`、预激活 conda `testbed`、bash/edit 工具。这些是公开来源声明；实际交付与运行事实仍为 unknown（`P/environment_brief.md:3–10`）。

## 公开资料能消解什么

1. **类字段接口已经存在。** `B/docs/usage/models.md:121–122` 说明 `model_fields` 是字段字典；同文件 `1194–1204` 在实例化前读取 `Model.model_fields.keys()`。`B/pydantic/main.py:177` 给出 `ClassVar[dict[str, FieldInfo]]` 类型提示，但该声明位于 `TYPE_CHECKING` 分支，不能据此认定运行时 BaseModel 已有空字典。`B/pydantic/_internal/_model_construction.py:136–144` 才实际赋值 `cls.model_fields`。
2. **根因是创建时序。** `ModelMetaclass.__new__` 在 `B/pydantic/main.py:109` 先调用 `super().__new__`，之后才在 `148` 收集当前类字段、`149–154` 完成模型。依据 Python 类创建语义，普通 `__init_subclass__` 会在前者内部执行，尚未到后面的字段赋值；因此它可能取得继承的旧字段映射，首层模型也可能根本没有该属性。此为静态推断，未运行复现。仅把 `__fields__` 改成 `model_fields` 不能保证定义阶段看到新增字段。
3. **不能拿原始注解字典替代最终字段字典。** `collect_fields` 在 `B/pydantic/_internal/_fields.py:139–156` 遍历类型提示、排除 ClassVar 与下划线名称；`198–214` 处理继承字段并复制 FieldInfo；`223–233` 从类命名空间移除字段默认属性。因此字段集合与 `cls.__dict__` 或本类 `__annotations__` 不等价。别名生成在最终赋值前发生（`_model_construction.py:142–143`）。
4. **示例元数据的精确接口是复数。** `B/pydantic/fields.py:301,335,382` 使用 `examples`，`FieldInfo.examples` 在 `87` 保存它。所读 `Field` 签名 `291–323` 没有 `example` 或任意 `**kwargs`。合理最小验证应使用 `Field(examples=['pretty_test'])`，不应将单数参数兼容性扩展为本题必须完成的工作。
5. **已有类关键字参数行为需保留。** `B/tests/test_main.py:1338–1351` 要求自定义 `__init_subclass__(cls, something)` 接收 `something=2`。`B/pydantic/config.py:227` 会先从 kwargs 移除配置项；`tests/test_main.py:1667–1701` 覆盖配置项优先级以及未知参数报错。修复不应吞掉普通钩子的参数、不应重复触发它，也不应让配置项误传给用户钩子。
6. **字段就绪不保证模型完全可用。** `B/pydantic/_internal/_model_construction.py:159–160` 指出完成模型需要现成类对象；`165–183` 表明未解析注解可能使完成阶段返回 False 并放置 MockValidator。题面只要求字段检查，没有支持“此时所有类型都可解析/可以实例化”的承诺。

## 合理实现范围与未定选择

可在模型字段收集后提供可覆盖的类级生命周期钩子，并从元类按继承方法解析顺序调用，使父类逻辑检查新子类的 `model_fields`；保留原生 `__init_subclass__` 的既有行为。另一种可能方向是重排类构造时序，但 `collect_fields` 与模型完成依赖类对象，改动面和兼容风险更大。仅补充字段改名说明不能解决题面标题中的时序需求。

新增钩子叫什么、在字段收集后还是模型完成尝试后调用、是否要求显式 `@classmethod`、如何支持多层 `super()` 合作调用，均属于需定义并记录的设计选择，公开题面没有给出唯一答案。本角色不可见 gold，不将某一命名或代码结构当作评分规范。合理实现应保证调用对象是正在创建的子类、可读取继承及新增字段；支持用户检查抛错以阻止不合要求的类定义。前向引用、泛型、多继承和重建时是否再次调用，应明确边界，不能无依据承诺全覆盖或把它们全部升级为题面硬要求。

## 开发需求与最小公开验证建议

所有命令都仅供后续 actor 在其实际源码工作目录使用，本轮未运行；不是强制评分规范。不得在此静态导出上宣称测试已通过。

| 需要操作/资产 | 公开依据 | 已取得证据或未知 | 建议最小命令与预期 |
| --- | --- | --- | --- |
| 确认真实源码位置和修改基线 | `P/user_prompt.txt:1`、`P/environment_brief.md:2–7` | 精确静态导出已读；实际 HEAD、初始 diff、cwd 均 unknown | `pwd`、`git rev-parse HEAD`、`git status --short`；核对 `/testbed`、给定提交及初始改动，不能默认干净 |
| 可编辑非测试源文件 | `P/public_bundle.json:1` 的公开提示；`B/pydantic/main.py:60–158` | 所需元类源码可读；actor 写权限 unknown | `git diff -- pydantic/main.py pydantic/_internal/_model_construction.py`；确认实际修复涉及类生命周期且没有误改测试 |
| 可导入本地 Pydantic 的 Python 与依赖 | `B/pyproject.toml:57–62`：Python >=3.7、typing-extensions >=4.2.0、pydantic-core >=0.22.0、annotated-types >=0.4.0 | 安装版本、二进制兼容性、解释器、导入路径均 unknown；下界不保证任意未来版本兼容旧代码 | `python -c 'import sys, pydantic, pydantic_core; print(sys.executable); print(pydantic.__file__); print(pydantic_core.__version__)'`；应成功并指向被修复源码 |
| pytest 与窄范围旧回归 | `B/requirements/testing.in:1–6`；`B/tests/test_main.py:26–41`、`B/tests/conftest.py:11–12` | 文件与依赖声明已读，是否安装/能收集 unknown | `python -m pytest -q tests/test_main.py -k 'custom_init_subclass_params or class_kwargs or field_order or recursive_model'`；已有参数传递、字段顺序、配置和递归行为保持原状 |
| 定义阶段字段检查的新行为 | 题面 `10–12,23–34` 与上述静态根因 | 已有旧测试不直接验证新增生命周期接口；运行结果 unknown | 使用 `python -` 输入一次性验证片段：父类覆盖实现公开的字段就绪钩子；子类含继承字段、`Field(examples=['pretty_test'])` 和无 examples 字段；记录钩子中的类与字段字典，不实例化。预期能读到子类全部字段并区分示例，执行检查时可因缺示例抛错；片段须匹配最终所选接口，不能预先强制某个未公布名称 |

无需从题面推出网络、GPU、外部数据或服务需求；是否具备这些资产未验证，也不构成本题静态结论。若运行需要补依赖，须先根据 actor 实际环境确认；本报告不提出已安装或应联网安装的事实判断。

## 实际阅读范围与边界

完整读取：角色卡 `roles/public_reader.md`；`P/user_prompt.txt`、`environment_brief.md`、`base_identity.json`、`public_bundle.json`；`B/pyproject.toml:1–146`；`B/requirements/testing.in:1–6`；`B/tests/conftest.py:1–86`。

定向读取：`B/pydantic/main.py:1–225`；`B/pydantic/_internal/_model_construction.py:130–205`；`B/pydantic/_internal/_fields.py:25–251`；`B/pydantic/fields.py:15–95,291–390`；`B/pydantic/config.py:214–265`；`B/docs/usage/models.md:100–129,1177–1214`；`B/tests/test_main.py:1–48,349–367,1320–1370,1650–1710,1725–1764`。

另执行本题文件名枚举，以及针对所读源码/测试/文档的 `model_fields`、`__fields__`、`init_subclass`、`examples` 等文本检索；全域钩子检索仅覆盖 `B/pydantic`、`B/tests`、`B/docs`，命中摘录不等于通读。检索还看到 `B/docs/usage/schema.md:284,392,522,536` 与 `B/pydantic/config.py:193,198` 等命中行，未追读上下文。未完整阅读其余源码、文档、测试、依赖锁定文件；未读取 `HISTORY.md` 或任何历史材料。未查看实际镜像、actor 消息/权限/工具呈现、运行账本、私有材料和他人报告。静态导出缺少某项内容不能证明实际镜像缺失该资产。本报告不评估成功率或训练资格。
