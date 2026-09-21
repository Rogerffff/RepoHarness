# getmoto__moto-5134：公开视角审查

仅依据指定角色卡与本题公开包静态阅读。下文文件路径相对于 `runs/swegym_quality_batch02_20260921_v2/public/getmoto__moto-5134/`；源码、文档和旧测试均在 `base/` 下。没有运行项目代码或测试、安装依赖、联网、读取 Git 历史或修改 base；没有读取私有评分材料、gold、其他题或其他角色产物。

公开需求足以定位一个明确的行为修复：事件字段已经存在且值为 JSON `null` 时，`{"exists": true}` 应匹配它。现有实现把字段缺失和 `null` 都变成 `None`，与题面现象相符。这是静态代码推断，尚无 actor 运行结果。

## 1. 需求表

| 行为或约束 | 确定程度 | 公开依据与可观察结果 |
| --- | --- | --- |
| 已存在、值为 JSON `null` 的叶子字段，应匹配 `{"exists": true}` | 明示 | `user_prompt.txt:3–10,37–43,95–124`。示例的 `detail.foo = null`、`detail.bar = "123"` 应使规则匹配，CloudWatch Logs 中应同时收到字符串事件与 null 事件。 |
| 原本能够匹配的非空字符串字段继续匹配 | 明示及旧测试 | 示例同时发送 `foo = "123"`，仍期待它出现在日志中；`user_prompt.txt:101,118–124`；`base/tests/test_events/test_event_pattern.py:23–26`。不能为修复 null 而丢弃原事件。 |
| 真正缺失的字段不能被 `exists: true` 匹配；`exists: false` 则应匹配缺失字段 | 由公开测试明确约束 | `base/tests/test_events/test_event_pattern.py:23–45` 覆盖空 detail、错误字段名及正反向存在性判断。必须区分“键不存在”和“键存在而值为空”。 |
| `exists` 的对象字段行为应保留：对象本身不是叶子，`exists: true` 不匹配，`exists: false` 匹配 | 由公开测试明确约束 | `base/tests/test_events/test_event_pattern.py:27–35` 直接注释“only match leaf nodes”，并测试 `foo = {"bar": "baz"}`。此处是本包既有契约，不是本次独立验证的 AWS 全面语义。 |
| 显式 null 应不匹配 `exists: false` | 合理推知，非题面直接断言 | 用户把 null 视为“存在”；现有实现将 `exists: false` 定义为同一 `leaf_exists` 条件的否定，见 `base/moto/events/models.py:857–861`。修正存在性后应保持这组逻辑互补。旧测试未覆盖 null 的反向情况。 |
| 多字段条件、普通允许值、嵌套模式、前缀、数值比较与序列化行为继续工作 | 由公开接口、调用者和旧测试推知 | 示例同时要求 source、detail-type、foo、bar；当前递归模式以 `all` 合并字段，见 `base/moto/events/models.py:829–852`。旧测试覆盖字符串候选、嵌套字段及完整列表匹配（`:8–20`）、prefix（`:48–52`）、numeric（`:55–96`）、原始模式 dump（`:99–105`），均位于 `base/tests/test_events/test_event_pattern.py`。 |
| 匹配结果应作用于规则投递路径，日志中的 null 仍为 null | 明示与调用链 | `user_prompt.txt:65–124`；`base/moto/events/models.py:119–143,173–192,1216–1229`。只改变显示文本或 `test_event_pattern` 返回值，不能满足该投递复现。 |
| `exists` 修复不应仅对 `foo`、特定总线或 Logs 目标生效 | 合理推知 | 题目描述的是过滤操作符行为；`EventPattern` 是通用匹配器，`Rule.send_to_targets` 在选择 Logs、Archive 或 SQS 目标前统一调用它，见 `base/moto/events/models.py:124–143`。Archive 规则也使用 `exists: false`，见 `:1441–1448`。 |
| 是否同时实现 Moto 的 `test_event_pattern` API | 有边界疑义，但并非必要修复范围 | `user_prompt.txt:46–63` 的第一个测试没有 mock，用户称其在 AWS 上成功；第二个才是 Moto 失败复现。公开服务文档 `base/docs/docs/services/events.rst:144` 标为已实现，但 response 在 `base/moto/events/responses.py:208–209` 是 `pass`，backend 在 `base/moto/events/models.py:1244–1245` 抛 `NotImplementedError`。不能把第一个测试视为现有 Moto API 的可运行回归要求。 |
| 空列表、列表中 null、缺失中间对象、null 字面量过滤、多个过滤器组合等更广泛语义 | 仍未完整规定 | 题面只给出已存在的 `detail` 对象内的 null 叶子。已读旧测试没有这些组合的完整期望。现有代码可提供兼容性线索，但不能据此宣称完整 AWS 兼容，也不应把所有相邻缺陷扩大为本题必修项。 |

## 2. 合理实现范围

可接受的实现不必采用唯一内部表示。至少有两种合理设计：在递归匹配中显式传递“键是否存在”，或使用与任何有效 JSON 值都不同的缺失标记，再让 `exists` 判断字段存在性与叶子类型。也可适度重构匹配流程，只要行为一致、保持旧测试约束。公开材料没有约定缺失标记的名字、类名、辅助函数名称或私有方法参数形式。

实际已有约定是 JSON 操作符名 `exists`、布尔值含义、Boto3 请求键名、`EventPattern.load(...).matches_event(...)` 返回的匹配结果，以及 `dump()` 保留原始模式字符串。依据是 `user_prompt.txt:37–43,77–107` 与 `base/tests/test_events/test_event_pattern.py:8–45,99–105`。实现不能用可能与合法用户值冲突的普通字符串来代表缺失，也不能把所有 falsy 值都当成缺失；后者会误伤 `False`、`0`、空字符串等当前不为 `None` 的叶子值（`base/moto/events/models.py:857–861`，推知兼容要求）。

若只删除 `item is not None` 而不保留缺失信息，当前 `event.get(k)` 会让不存在的键也匹配 `exists: true`，违反旧测试（`base/moto/events/models.py:830,859`；`base/tests/test_events/test_event_pattern.py:26,38–39`）。修复范围因此应覆盖“区分缺失与 null”，而不只是特判示例内容。

题面日志排序是复现时收集结果的方式，不要求重新设计日志 ID 或全局排序。当前 Logs 将递增整数 ID 转为字符串（`base/moto/logs/models.py:30–43`）；若扩展复现与大量既有事件共用进程，字符串排序跨位数可能干扰顺序，应区分这种断言问题与漏投递问题。最小验证可以比较两条 detail 的内容与数量，保持本题关注点。

## 3. 初态线索与疑义

**定位入口充分。** 题面提供具体 Python/SDK 版本、完整 mock 流程、过滤模式与失败输出（`user_prompt.txt:14–24,26–127`）。从 `put_events` 可以追到 `Rule.send_to_targets`、`EventPattern.matches_event`、`_does_event_match` 和 `exists` 分支。`put_events` 会把 Detail JSON 解析成 Python 对象（`base/moto/events/models.py:1228`），`event.get(k)` 将缺失键和显式 null 合并为 `None`（`:830`），而 `leaf_exists` 排除 `None`（`:859`）。不需要私有测试、未来修复或祖先历史才能形成调查假设。

**既有公开测试缺少关键 null 用例。** `base/tests/test_events/test_event_pattern.py:23–45` 已覆盖字符串、缺失和非叶子对象，却未覆盖 null。它们可用于防回归，但即使通过也不能单独证明本题已修复。题面本身足以导出独立的最小 null 复现，不属于缺失开发材料。

**示例中区域配置是可正常查明的运行前提。** 题面创建 Boto3 clients 时未传 `region_name`，但目标 ARN 写 `eu-west-1`（`user_prompt.txt:47,68,72,90`）；文档要求设置默认区域与 dummy credentials，并在创建 clients 前启用 mock（`base/docs/docs/getting_started.rst:210–224`）。可在复现进程设 `AWS_DEFAULT_REGION=eu-west-1` 或显式给两个客户端同一区域。若发生 `NoRegionError`，是复现配置未补齐，不是题意不清。

**真实 AWS 对照不是必要服务。** 第一个测试是未 mock 的 AWS 调用；在本环境不能假定公网、账号和凭据可用（`environment_brief.md:10–12`）。第二个 mock 测试及内部匹配器足以检验所要求的行为。AWS 上的成功仅作为 issue 作者陈述，本次未复核；若要重新核实广泛 AWS 边界语义，需要额外公开规格或获准的真实服务条件，但这并不阻碍本题明确的 null 修复。

**公开 API 文档与源码不一致。** `test_event_pattern` 的文档勾选与占位实现存在冲突，位置见需求表。实际开发应使用 mock 规则投递或内部 `EventPattern` 调查，不应因该占位方法失败而误判 null 修复仍未生效。若验收意图包括补全该 API，则公开需求需额外澄清；当前题面不支持将其列为强制实现。

**版本与环境尚待验证。** Python 3.9.7、boto3 1.22.4、botocore 1.25.4、moto 3.1.8 是作者复现版本（`user_prompt.txt:14`），不是已证实的运行镜像状态。`base/setup.py:29–42,138–150` 使用较宽依赖范围并支持多个 Python 版本。开发应确认导入的是 `/testbed` 中待修改的源码，不能用安装发布版 moto 的方式替代该 checkout。若现有包不兼容或缺少依赖，离线包来源/预装情况才是真正需要 actor 补证的运行缺口。

### Issue、harness 指令和环境声明分开处理

| 类别 | 公开内容 | 本次判读 |
| --- | --- | --- |
| Issue 需求 | null 与 `exists: true` 的匹配及投递 | 行为目标，不与部署方式或工具混为一谈。 |
| Harness 操作指令 | `public_bundle.json:1` 的 `public_hints` 要求探索原因、修改非测试源码、禁止改测试、窄范围测试、完成后简述 | 原指令是否进入本次实际 system message 未验证；bundle 会作为公开文件可见，不在 `user_prompt.txt` 内不等于不可见（`environment_brief.md:3–4,20–26`）。此审查不授权忽略原指令。 |
| 旧评分解释 | “所有测试修改都会恢复、永不计分” | 不是已核实的当前机制；环境说明明确目前没有按测试文件名统一排除，仍有官方文件恢复等具体限制（`environment_brief.md:22–23`）。具体文件限制留给协调者核实，本角色未查私有资料。 |
| 环境事实声明 | `/testbed`、预激活 `testbed` conda、工具 bash/edit、镜像标识、资源与 actor 配置 | 这些是公开声明/计划；不是实际导入、运行或权限证据（`public_bundle.json:1`；`environment_brief.md:8–13`）。 |

“禁止改测试”适用时，源代码中的匹配逻辑仍足以容纳合理修复；可运行已有测试和不写仓库文件的临时命令复现。不适用时，可另外添加 null 正反向回归测试，但并非修复行为的必要交付。两种情况下需求不变，目前看不到必须修改测试文件才能实现的冲突。指令适用性与恢复机制仍登记为共享输入/运行条件未知。

## 4. 开发需求表

本表列出的命令均为**建议，未执行**；预期现象由公开代码推断，不是运行记录。后面的命令块在实际 actor 的 `/testbed` checkout 中使用，不在本静态导出中执行。

| 操作 / 资产 / 服务 | 公开依据 | 环境说明支持到哪层 | 缺口 | 最小命令及预期 |
| --- | --- | --- | --- | --- |
| Python 与本地源码导入 | `user_prompt.txt:14`；`base/setup.py:29–42,138`；`base/moto/events/models.py:1–34` | 仅声明 conda 环境、actor 与工作目录；要求另做 actor 验证 | Python 路径、版本、源码导入位置和实际兼容性未知 | C1（建议，未执行）：打印解释器及模块路径，导入 Events、Logs、pytest、sure。预期无导入错误且源码来自 `/testbed`。 |
| 测试依赖 | `base/requirements-tests.txt:1–6`；`base/tests/__init__.py:3` 导入 helpers，`base/tests/helpers.py:4` 导入 sure | 没有已安装包清单或离线 wheel 证据；公网下载不可假定 | 即使只跑 pattern 测试，也要考虑 tests 包初始化的 sure；依赖版本兼容未知 | C1、C3（建议，未执行）。若失败在 collection/import，应先补运行条件，不应归因于 null 逻辑。 |
| 核心 bug 复现 | `base/moto/events/models.py:818–861`；题面 `user_prompt.txt:37–43,107` | base 源码已导出；未证实可执行 | 无专有数据、下载资产或外部服务需求；只缺实际 Python 导入/执行证明 | C2（建议，未执行）：比较 null、缺失、字符串、对象四种输入。原代码预计 null 的正向结果为 false、反向为 true；修复应相反，其他结果保持。 |
| Events → Logs 本地投递 | `user_prompt.txt:65–124`；`base/tests/test_events/test_events_integration.py:12–68`；`base/moto/events/models.py:119–192` | 说明不保证实际服务或资产；默认 mock 可在进程内运行 | 需 mock 初始化成功、同一区域、dummy credentials；Logs 还会导入 S3 backend（`base/moto/logs/models.py:16`），依赖不能仅按表面模块名推断 | C4（建议，未执行）：本地 mock 下创建总线、规则、日志组并投递两条事件。原 bug 预计仅一条 detail，修复应包含字符串和 null 两条。 |
| 公开防回归测试 | `base/tests/test_events/test_event_pattern.py:1–105`；`base/tests/test_events/test_events_integration.py:12–68` | 不要求全仓测试全部运行（`environment_brief.md:16`） | 实际测试工具、插件和运行耗时未验 | C3（建议，未执行）：pattern 整文件及 Logs 单个集成测试。原状态预期这些旧用例可通过，但不覆盖 null；修复后仍应通过。 |
| 安装 / 构建 | `base/CONTRIBUTING.md:19–22`；`base/Makefile:17–19,34–40`；`base/requirements-dev.txt:1–5` | 解释器/系统包写权限待实际核对，公网不可假定 | 未提供缓存、离线包与依赖安装验证；不能保证 `make init` 在此环境完成 | `make init` 是上游安装入口（建议，未执行），会执行 `setup.py develop` 和安装开发依赖，不建议未确认依赖来源就依赖它。C5 为局部语法检查（建议，未执行）；本改动无须独立原生构建。 |
| 外部 AWS / Docker / 子模块 | 第一个未 mock 测试 `user_prompt.txt:46–63`；全仓指南 `base/docs/docs/contributing/installation.rst:9–12`；`base/.gitmodules:1–3` | 网络、资源与资产均未验证 | 未提供真实 AWS 访问；Terraform 子模块内容未确认，但不在本题必要路径 | 本题最小验证不需真实 AWS、Docker、Terraform 子模块或下载镜像。全仓 `make test` 的额外条件不能当作本题必要条件；不建议运行未 mock 的 AWS 对照。 |

**C1：最小环境与导入检查（建议，未执行）。** `id` 与 `pwd` 仅核对 actor 和工作目录，不代表其他运行条件已满足。

```bash
id
pwd
python - <<'PY'
import sys
import boto3, botocore, moto, pytest, sure
import moto.events.models as events_models
import moto.logs.models as logs_models
print(sys.executable, sys.version)
print(moto.__file__, events_models.__file__, logs_models.__file__)
print(boto3.__version__, botocore.__version__, moto.__version__)
PY
```

**C2：最小逻辑复现与边界检查（建议，未执行）。** null 的反向期望是从存在性互补关系推知，来源区别见需求表。

```bash
python - <<'PY'
import json
from moto.events.models import EventPattern
cases = [
    {"detail": {"foo": None}},
    {"detail": {}},
    {"detail": {"foo": "123"}},
    {"detail": {"foo": {"bar": "baz"}}},
]
for exists, expected in [
    (True, [True, False, True, False]),
    (False, [False, True, False, True]),
]:
    pattern = EventPattern.load(json.dumps({"detail": {"foo": [{"exists": exists}]}}))
    actual = [pattern.matches_event(event) for event in cases]
    print(exists, actual)
    assert actual == expected, (exists, actual, expected)
PY
```

原代码预计第一次打印 `True [False, False, True, False]` 后断言失败；修复后两轮均符合期望。此命令不创建/修改仓库测试文件。

**C3：已有公开窄范围测试（建议，未执行）。** 显式关闭 server mode，避免环境遗留开关把 mock 改为服务器调用；该开关依据为 `base/moto/settings.py:8` 与 `base/moto/core/models.py:398–402`。

```bash
env TEST_SERVER_MODE=false AWS_DEFAULT_REGION=eu-west-1 AWS_ACCESS_KEY_ID=testing AWS_SECRET_ACCESS_KEY=testing AWS_SESSION_TOKEN=testing python -m pytest -q tests/test_events/test_event_pattern.py
env TEST_SERVER_MODE=false AWS_DEFAULT_REGION=eu-west-1 AWS_ACCESS_KEY_ID=testing AWS_SECRET_ACCESS_KEY=testing AWS_SESSION_TOKEN=testing python -m pytest -q tests/test_events/test_events_integration.py::test_send_to_cw_log_group
```

**C4：题面等价的本地投递复现（建议，未执行）。** 用两个 mock、同一区域和 detail 内容比较；不调用 AWS 对照 API、不写测试文件。

```bash
env TEST_SERVER_MODE=false AWS_DEFAULT_REGION=eu-west-1 AWS_ACCESS_KEY_ID=testing AWS_SECRET_ACCESS_KEY=testing AWS_SESSION_TOKEN=testing python - <<'PY'
import json
import boto3
from moto import mock_events, mock_logs
from moto.core import ACCOUNT_ID

expected = [{"foo": "123", "bar": "123"}, {"foo": None, "bar": "123"}]
pattern = {
    "source": ["test-source"],
    "detail-type": ["test-detail-type"],
    "detail": {"foo": [{"exists": True}], "bar": [{"exists": True}]},
}
with mock_events(), mock_logs():
    events = boto3.client("events", region_name="eu-west-1")
    logs = boto3.client("logs", region_name="eu-west-1")
    logs.create_log_group(logGroupName="test-log-group")
    events.create_event_bus(Name="test-event-bus")
    events.put_rule(Name="test-event-rule", State="ENABLED",
                    EventBusName="test-event-bus", EventPattern=json.dumps(pattern))
    events.put_targets(
        Rule="test-event-rule", EventBusName="test-event-bus",
        Targets=[{"Id": "123", "Arn":
                  f"arn:aws:logs:eu-west-1:{ACCOUNT_ID}:log-group:test-log-group"}],
    )
    events.put_events(Entries=[
        {"EventBusName": "test-event-bus", "Source": "test-source",
         "DetailType": "test-detail-type", "Detail": json.dumps(detail)}
        for detail in expected
    ])
    received = logs.filter_log_events(logGroupName="test-log-group")["events"]
    details = [json.loads(event["message"])["detail"] for event in received]
    print(details)
    assert len(details) == 2 and all(detail in details for detail in expected), details
PY
```

**C5：局部语法检查（建议，未执行）。** 仅证明语法可编译，不能替代行为验证。

```bash
python -m py_compile moto/events/models.py
```

## 5. 实际阅读范围与限制

- 首先完整读取指定 `roles/public_reader.md`，再读本题 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`。对 PUBLIC_DIR 做了文件名枚举；枚举输出被截断，未据此声称已阅读整仓。
- 完整/实质完整打开：`base/README.md`、`base/CONTRIBUTING.md`、`base/setup.py`、`base/setup.cfg`、`base/Makefile`、`base/requirements-tests.txt`、`base/requirements-dev.txt`、`base/docs/docs/contributing/installation.rst`、`base/.gitmodules`、`base/tests/test_events/test_event_pattern.py`、`base/tests/test_events/test_events_integration.py`、`base/tests/__init__.py`、`base/tests/helpers.py`、`base/tests/test_events/__init__.py`、`base/moto/events/__init__.py`、`base/moto/logs/__init__.py`、`base/moto/s3/__init__.py`。
- 按段阅读：`base/moto/events/models.py` 的 Rule/投递部分（请求读取 1–255；合并输出局部截断，结论只引用已显示的 1–192）、EventPattern/Parser（818–933）、put_events/占位 API（1158–1260）、Archive 规则（1438–1466）；`base/moto/events/responses.py:1–80,165–220`；`base/moto/logs/models.py:1–50,92–135,355–389,394–427`；`base/moto/core/models.py:43–72,82–99,195–203,389–407`；`base/moto/__init__.py:1–39`；`base/moto/settings.py:1–66`；`base/docs/docs/services/events.rst:85–156`；`base/docs/docs/getting_started.rst:204–225`。
- 另外做了相关字符串检索：`base/moto/events`、`base/tests/test_events`、安装文档/配置、`base/moto/logs/models.py`、`base/moto/core/models.py`、`base/moto/settings.py`、`base/moto/__init__.py` 与 getting_started；在 `base/moto`、`base/tests` 检索 EventPattern 及其私有匹配方法调用者。检索命中但未整文件展开的内容包括 `base/tests/test_events/test_events.py`、`base/tests/test_events/test_events_cloudformation.py`、`base/moto/events/exceptions.py`、`base/moto/iam/aws_managed_policies.py` 等；不把这些关键词片段称为全面审查。
- 未读取 `base_identity.json`、Git 历史、完整无关服务实现、外部文档/链接、真实容器、依赖缓存或镜像文件系统。`.gitmodules` 的 Terraform 路径仅用于判断本题最小路径不依赖该子模块，没有访问其远程仓库。
- `user_prompt.txt` 只是当前函数静态渲染，不是捕获的实际模型消息。`base/` 是跟踪文件导出，不能证明完整运行镜像、预装依赖、激活状态、消息注入、权限、CPU/内存或 actor 的开发条件已经验证（`environment_brief.md:3–13,20–26`）。没有 essential 的外链附件缺失阻碍这里的核心行为分析；运行可用性、旧提示适用性及更广泛 EventBridge 边界语义仍是上述未知。
- 本次没有已知私有材料误读。只读边界是协作约定；不将其描述为操作系统权限隔离或预训练无污染证明。没有给本题通过/淘汰标签。
