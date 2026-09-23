# pydantic__pydantic-8511 — history 前私有分析（封存稿）

2026-09-21。本稿形成于获准读取本题旧调查之前；保存后不回写。结论为静态审查与既有原始 RH2 证据核对，不是当前 CPU 或 actor 验收。

## 路径、材料身份与暴露

- `R=${REPO_ROOT}`。
- `P=R/runs/swegym_quality_batch01_20260921_v2/public/pydantic__pydantic-8511`；`Q=R/runs/swegym_quality_batch01_20260921_v2/private/pydantic__pydantic-8511`。
- `O=R/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/pydantic__pydantic-8511`。
- `E=R/runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-8511`。下文这些缩写均展开为上述绝对路径后定位；源码行号指 `P/base/`。
- 已读本批 investigator 角色卡、八方面协议、actor_environment_card、record_template、`O/public_read.md`；本题 public bundle/base identity/prompt/environment brief，指定源码及测试；`Q/test.patch`、`gold.patch`、`grading.json`、`validation.json`、`run_refs.json`、`environment_record.json`；只沿 run/recipe 引用读取本题原件。environment_record 的状态、checks、运行元数据及 analysis/history **路径名**已暴露；没有打开它们指向的汇总。未读 source_refs、manifest、主计划、method_adjustments、其它角色结论或旧质量报告。
- base 为 `e4fa099d5adde70acc80238ff810c87a5cec7ebf`，tree `f6b994800d90c9fd0671ac000b4aa5cfaa9a52f7`，静态导出记录 452 tracked entries、blob 校验为真，无 .git、symlink/LFS/gitlink。public image manifest digest 为 `sha256:bfb85a33f105b41c42c88805c45bd7d823c3884dadc000dbfc040401d8be4a73`。
- 元数据 Python 只读 JSON、文本并计算 SHA256，没有 import 项目。核得独立 test/gold patch 分别与 grading/validation 内嵌值逐字相等；两个原始日志 SHA256 均与 run_refs 匹配。尚未重新核每个 base blob，也未运行项目、安装、Docker、SSH、网络或模型。

## 1. 公开需求与初态

题面希望赋值形式 `c: int = pydantic.dataclasses.Field(repr=False)` 与标准库 `dataclasses.field(repr=False)` 一样，从实例表示中隐藏该字段，保留其它字段。原例顶层输出应由 `x(y=3) a(b=1, c=2)` 变为 `x(y=3) a(b=1)`；题面末尾原输出不是验收目标。`fields.py:664,670` 将 repr 与序列化 exclude 分开，不能删除字段或停止验证来满足隐藏要求。

公开接口依据充分：`dataclasses.py:15` 绑定同一 Field 函数；`fields.py:201,576-593` 默认 repr=True；`docs/concepts/dataclasses.md:27-30,47-99,103-104` 说明标准 dataclass 兼容和两种字段工厂。issue 报告 Pydantic 2.1.1/core 2.4.0/Python 3.11.4，指定 base 为 2.6.0a1/core 2.14.5（pyproject:64-68）；报告者版本是背景，不应降级覆盖指定 base。

base 的同步入口只在 Python >=3.10 为 `FieldInfo.kw_only` 包装标准库字段（dataclasses.py:144-167）；标准库 dataclass 先生成 repr，之后 Pydantic 才收集字段并建立 validator/serializer（208-229；_internal/_dataclasses.py:94,118,135-182）。因此 FieldInfo.repr 已存储但未转交标准库的静态路径，与原始 noop 隐藏字段断言失败一致。不是凭 gold 差异认定 bug。

public_hints 的“只改非测试源码”是操作指令；无需修改测试即可合理修复。其“所有测试都会恢复”不能当当前机制概括。真实消息、system prompt、CLI 附加信息未捕获；静态 user_prompt 只证明当前渲染文件的内容。

## 2. 所有新增/修改断言、fixture/helper 与双向映射

test.patch 只改 `tests/test_dataclasses.py`，没有混入生产代码。新增测试的 `field_constructor` 是 pytest 参数注入，并非 Mock；两个测试都无专用 fixture/helper。模块使用标准库 dataclasses、真实 Pydantic 装饰器、Field 与 core。全局 autouse `tests/conftest.py:46-50` 仅设置 `PYDANTIC_ERRORS_OMIT_URL`。已读其余 fixture：create_module 写 tmp_path、用 AssertionRewritingHook/importlib 装载本地代码；subprocess_run_code 在 tmp_path 用 sys.executable 执行，二者不参与新增用例。`dataclass_decorators` 的 pydantic/stdlib/combined/identity 路径（test_dataclasses.py:1650-1675）影响相关旧 P2P，不参与 repr F2P。

唯一 F2P `test_repr_false[Field]`：定义局部 A，visible_field 是普通必填 str，hidden_field 是 `Field(repr=False)`；以两个关键字字符串构造真实实例；断言 repr 包含完整可见字段片段，且不含完整隐藏字段片段。两个断言有直接公开依据，未绑定内部 helper、mock 次序或 gold 文件布局；没有检查隐藏属性仍存在、仍验证、仍序列化，也没有验证 Field() 默认显示。

P2P `test_repr_false[field]` 为同一测试的标准库工厂分支，保护原例对照。修改的 `test_default_factory_field[field/Field]` 两分支均在 P2P：使用 `lambda: {'John': 'Joey'}`；构造 User(id=123)，断言 id=123、**新增** other 字典等于预期、id.is_required=True、repr(id.default) 为 PydanticUndefined、other.is_required=False、other.default_factory() 返回预期字典。最后几条从 base:530-534 继承。字典值是测试输入/可观察输出，PydanticUndefined 是已有表示约定；都不是无依据的新 API 约束。该测试保护工厂和元数据，但不检查 repr，也不检查父类工厂继承。

| 公开要求/合理旧行为 | 公开依据 | 对应测试与决定性断言 | 覆盖 | 原始执行或缺口 |
|---|---|---|---|---|
| Field(repr=False) 隐藏、普通字段保留 | issue；fields:670 | F2P `test_repr_false[Field]` 的正/负子串断言 | 核心覆盖；换为 str/关键字输入，未原样执行 int/位置参数原例 | noop 明确在负断言失败；gold 通过 |
| stdlib repr=False 行为保留 | issue x 类 | P2P `test_repr_false[field]` | 覆盖单一局部类 | 两角色通过 |
| 两种工厂及字段 required/default 元数据 | docs dataclasses:47；tests:519-534 | 两个 `test_default_factory_field` P2P | 覆盖；测试补丁合理补强 | 两角色通过 |
| Field()/Field(repr=True) 默认显示 | fields:201,591；docs dataclasses:13-24 | 新 F2P 可见字段未使用 Field；相关默认/schema/签名 P2P 均无实例 repr 断言 | 缺失直接保护 | 可隐藏所有 FieldInfo 的错误实现仍可能过；尚未制作/计分 |
| 隐藏字段仍可访问、验证、序列化 | fields:664,670；_dataclasses:135-182 | `test_simple`、`test_value_error`、`test_schema`、init=False 两用例、TypeAdapter/RootModel 旧行为 | 分开场景有 P2P；未与 repr=False 组合 | 读到相关测试，两角色相应参考均过；不是组合验证 |
| 默认值、schema、alias、签名、继承保留 | tests:500-589,1938-1969,2141-2169,2481-2507 | required/default/schema equality、alias 错误、signature 精确输出等 P2P | 相关单行为覆盖 | 两角色对应参考通过 |
| 无本地注解子类继承 required/default_factory FieldInfo | dataclass 兼容及 fields:281-292；已有默认继承 tests:1938-1969 | 继承 P2P 参数为普通1/stdlib default=1/Field(default=1)，没有 required/工厂 FieldInfo 的空子类 | **具体组合缺口** | gold 的新 getattr+setattr 路径存在旧 Python 静态回归嫌疑，见下 |
| kw_only、slots 与较新 Python 分支 | dataclasses:144-167；tests:1622-1647,1678-1693,2293-2339 | kw_only 6项、slots 4项 | 有公开测试，但不在冻结 F2P/P2P 且本次执行跳过 | Python 3.8；`test_dataclasses_with_slots_and_default` 虽通过，此版本装饰器忽略 slots，不能证明真 slots |
| class repr=False、自定义 repr、Annotated repr | dataclasses:100,214；字段说明；tests:2395-2441 | 未找到本模块对应实例 repr 断言 | 未覆盖；混用测试公开说明有历史边界 | Annotated/混合冲突不强行扩为本题硬验收；类级行为为合理回归 |

168 个 P2P ID 已全部与原始日志核对；没有把读到的名字当作读完所有测试体。实际深读范围为基础转换/错误、stdlib 再装饰及继承、post_init、fields/default factory/schema、InitVar/ClassVar、kw_only/helper、默认继承与 default validation、元信息/alias、slots、Annotated 混用、init=False/序列化、签名和模块末尾默认值继承；其余 validator/generic/recursive 大段未逐条展开。全模块相关 repr/Field/测试函数定义搜索已完成。

## 3. 合理替代实现与部分实现

合理非 gold 路线：只处理**本地注解**中需要桥接 repr=False 或 kw_only 的 FieldInfo，在调用标准库装饰器前补齐对应元数据，沿用现有字段收集保留校验、默认值和工厂。公开要求不要求把每个 FieldInfo 都包装，也不要求某个 helper 名。当前测试属于输出行为测试，静态未发现它会因实现路线不同而误拒；没有实际运行替代补丁，不能升级为所有合理解可接受。

具体漏测候选：把全部 FieldInfo 设置为标准库 repr=False，可满足唯一 Field F2P，而错误隐藏默认应显示的 Field()/Field(repr=True)。本模块没有其它实例 repr 断言；已有默认/schema/签名断言不直接捕获它。仍需真实 RH2 对照才可称已证实假阳性。另一类只改 repr 字符串引号的办法可能绕过隐藏片段负断言，但这只是断言强度限制，优先级低于真实路径上的继承嫌疑。

## 4. gold 完整性与独立发现

gold 只改 `pydantic/dataclasses.py`，把 helper 提到版本分支外、包装 FieldInfo 默认对象并转交 repr，保留 >=3.10 的 kw_only 条件。该路径静态能修复题面赋值形式；普通字段/stdlib Field 跳过，默认值和工厂仍由 collect_dataclass_fields:281-292 接回原 FieldInfo；无新依赖或外部文件。历史 gold F2P/P2P 成功支持其在已执行场景有效，不等于完整性证明。

**G1：无本地注解子类的潜在 gold 回归，静态假设，尚未执行。** gold.patch:39 使用 `getattr(cls, '__annotations__', [])`，随后 40/56 读取并向当前类写入 dataclasses.Field。Python 3.8/3.9 的继承注解访问可能取到父类 annotations；父类 required `Field()`、`Field(repr=False)` 或 `Field(default_factory=...)` 的 default 仍是 PydanticUndefined，因此 `_fields.py:290-292` 不会把类属性替换成普通默认值。没有本地注解的 `@dataclass class Child(Parent): pass` 可能于是新增没有自身注解的标准库 Field，装饰器拒绝创建 Child。base 在该 Python 分支 helper 是 no-op。已追 DecoratorInfos.build:414-499，不见为此空子类建立本地 annotations 的保护；_dataclasses.is_builtin_dataclass:264-268 对带继承 validator 的子类不会走重建 stdlib 子类分支。已有继承 P2P 的 Field(default=1) 恰好会被替换为普通1，无法区分此风险。Python 标准库具体运行源码未包含在本题导出且未另行读取，因此这里保留“可能”，不写已确认异常或已拒绝 gold。

**T1：默认 Field repr 直接覆盖缺失。** 有公开默认 True 依据，已给可区分错误实现；是静态测试充分性问题，不能说当前 gold 实际有该 bug。

**V1：版本回归保护局限。** 冻结集明确不含 10 个 >=3.10 kw_only/slots 用例；历史执行也跳过它们。不能用“全模块命令”或“168 P2P”声称该版本分支已有评分保护。此限制本身不使核心题目无效。

## 5. 原始运行证据与条件边界

两条 `E/{noop,gold}/ledger.jsonl:1` 是 2026-09-19 原始 RH2 replay；派生配方 `pydantic-install-v1`，实际 image ID `sha256:4c4a01e8ed281b10ab94e9f37f7a02f33e2b0b9b1cefba4d72a253a394ce94d5`，非 public manifest 原像本身。policy 为 rh2grader/54322、2 CPU、4 GiB、network deny_all、64 MiB shm；解释器前缀允许写。candidate 由 agent/54321 应用不等于真实 actor 会话验收。

- noop 原日志 `E/noop/eval_logs/evallog_replay-er19-pyd1-pydanti_8ae8a3eb.eval.log`：132-146 核 base HEAD，137-138 有镜像遗留 pdm.lock/pyproject 差异；395-405 的 pyproject 差异额外加入 pre-commit。410-447 官方测试恢复/应用成功；585-667 安装从 `/opt/rh2/build-wheels` 完成，core 2.14.5、Python 3.8 site-packages；677-679 确实运行整个 tests/test_dataclasses.py、收集180项；867-874 是实际 repr 负断言失败；884-894 为1 failed/168 passed/11 skipped、test rc=1。
- gold 原日志 `E/gold/eval_logs/evallog_replay-er19-pyd1-pydanti_cb903f4a.eval.log`：496-508 setup 成功；647-728 安装完成；738-740 同一模块收集180项；778-779 工厂两项、831-832 repr两项通过；827-836及896-901记录跳过项；928-937 为169 passed/11 skipped、rc=0。
- 两角色冻结参考均 F2P=1/P2P=168、missing=0；gold F2P1/1、P2P168/168、reward1，noop F2P0/1、P2P168/168、reward0。原始逐行状态共180项，parser 标记176 parsed tests；11 skip 全在参考集外，差异没有漏掉冻结参考。没有把 parser 数当实际测试总数。
- ledger 的包导入路径观测为 `/testbed/pydantic/__init__.py`、版本2.6.0a1；projection gold included_paths 仅 pydantic/dataclasses.py、ignored_paths=[]，noop无改动；cleanup.removed=true、runner_integrity_changed=false。原始安装耗时 gold4.385s/noop5.025s，测试4.15s/4.69s；不是本次 agent 容器耗时。
- 配方 `E/gold/recipe/recipe.json` 与 after scripts 已读：候选安装 editable 当前项目并按 testing/testing-extra metadata 安装；相较原 pdm add pre-commit/make install 不再在候选阶段跑完整 docs/lint/hook 设置。实际运行仍消费遗留 pre-commit 依赖的镜像工作树。不能将此对照称“干净公开源码导出的当前 actor 环境”。

## 6. 开发条件、交付与评分边界

| 操作/资产 | 公开依据 | 现有证据适用范围 | 当前缺口与最小验证 |
|---|---|---|---|
| 定位与提交 | issue；dataclasses.py:144-229；source-only修复 | gold 的单源码路径已投影；eval 恢复 tests/test_dataclasses.py | actor git/workdir/可写性未验；核 HEAD、cwd、UID、diff。合法修复不需要改会恢复的测试或系统包 |
| 必要导入 | pyproject:64-68；_dataclasses:12-18 | grader 从本地工作区导入2.6.0a1、core2.14.5依赖已满足 | 用正式 actor shell 打印 sys.executable/version、pydantic.__file__/version、core version；核实际 PATH/BASH_ENV，而非搬 grader结论 |
| 公开复现/测试 | prompt；tests imports:13-16；conftest；pyproject addopts | grader pytest/dirty-equals/plugins已安装，模块完成 | actor 执行公开原例和窄范围默认/继承测试；插件缺失是环境失败，不能算原 bug |
| 安装/构建 | hatchling/readme backend；testing组 | grader 离线 build-wheels/cache 安装完成、前缀可写 | actor 非同UID/权限；准备阶段须有匹配 core wheel与测试插件；源码修复无新增编译需求，无需无条件 make install |
| 外部资产/服务/网络 | 题面只标准库和本地包；contributing:40-42 | 本题回放在deny_all完成 | 无本题特定外部数据、数据库、GPU、运行期服务；actor是否消费相同离线资产仍未知 |
| 资源与文件控制面 | actor card；本题小型单模块 | grader历史峰值约192/225MiB，不能代填actor | 正式 profile、实际shm/tmp/home、工具消息待验；未做完整镜像泄漏或评分控制面安全审计 |

test.patch 只有官方测试文件；正常业务改动可交付且不被该文件恢复覆盖。修改 pyproject/conftest 会影响装载/测试是共享控制面，本轮只记录本题安装消费 metadata 的适用点，没有执行攻击或新增排除规则。additional_exclusions 保持空。公开源码包无 .git 不证明真实镜像无未来答案；issue含 assignee 与版本线索，不足以推断答案可达性。未跨题读取或聚类。

## 7. 暂定处置及唯一优先 CPU 实验

`state=needs_review, scope=static_review, intended_use=development_diagnostic`。核心题意与 F2P 一致，历史修复配方下可区分 noop/gold；但 G1 有具体机制与缺失回归，先验证再决定是否列优先模型探针。actor 条件、实际消息与较新 Python 保护仍未验；没有“训练/最终评测准入”结论。

唯一优先 CPU 实验：在隔离的同一 Python3.8、同一派生配方下，对 base/gold/只枚举 `cls.__dict__.get('__annotations__', {})` 的窄修正版，运行下面的**单一继承矩阵**，同时保留官方 F2P/P2P得分。它能区分 G1 是否真实、修正是否只修该回归，以及历史 reward1是否漏掉该问题。以下仅实验设计，未运行、未写补丁：

```python
from pydantic import Field
from pydantic.dataclasses import dataclass

for make_field, kwargs, expected in [
    (lambda: Field(), {'x': '3'}, 3),
    (lambda: Field(repr=False), {'x': '3'}, 3),
    (lambda: Field(default_factory=lambda: 3), {}, 3),
    (lambda: Field(default=3), {}, 3),  # 已有P2P形状的控制
]:
    @dataclass
    class Parent:
        x: int = make_field()

    @dataclass
    class Child(Parent):
        pass

    assert Child(**kwargs).x == expected
```

如实验不支持 G1，撤销“gold 回归嫌疑”并保留未覆盖组合说明；如支持，记录异常及发生阶段，增补窄回归依据后再讨论测试/参考修订，不能为了 gold 保留而放宽合法继承行为。默认 repr 的 T1、>=3.10 的 V1、正式 actor待验分别保留，未因唯一实验而删项。

## 八方面收口

公开需求、材料/初態、全部新增修改断言/F2P及相关P2P、合理替代解、gold/回归、逐题开发条件、投影恢复边界、用途/暴露均已按上述范围审查。未查完整项目/标准库源码、每条P2P体、真实镜像祖先/资产、正式actor/完整消息、攻击验证、模型成功率与成本。所有运行陈述限定为原始历史RH2；G1/T1推测限定为静态。旧调查尚未开放，本稿至此封存。
