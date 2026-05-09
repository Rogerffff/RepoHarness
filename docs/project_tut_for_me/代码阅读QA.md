# 代码阅读 QA

本文档记录阅读 RepoHarness 源码过程中的问答，方便日后回顾。

---

## Q1: `ScaffoldRegistry.__init__` 在做什么？

**涉及文件**：[registry.py](file:///Users/roger/Desktop/claude-code/src/repo_harness/scaffolds/registry.py)（L14-L22）

**代码片段**：

```python
def __init__(self, definitions: list[ScaffoldDefinition] | None = None) -> None:
    self._definitions: dict[str, ScaffoldDefinition] = {}
    for definition in definitions or [
        build_simple_react_scaffold(),
        build_patch_focused_react_scaffold(),
        build_single_shot_patch_scaffold(),
        build_planner_coder_verifier_scaffold(),
    ]:
        self.register(definition)
```

**解答**：

这段代码是 `ScaffoldRegistry` 类的 `__init__` 构造方法，作用是**初始化 scaffold 注册表，并注册一组默认的 scaffold 定义**。逐行解释：

1. **`definitions: list[ScaffoldDefinition] | None = None`** — 构造参数，允许调用方传入一组自定义的 `ScaffoldDefinition`。如果不传（默认 `None`），则使用内置的默认列表。

2. **`self._definitions: dict[str, ScaffoldDefinition] = {}`** — 内部存储，是一个字典，key 是 `scaffold_id`（字符串），value 是对应的 `ScaffoldDefinition` 对象。

3. **`for definition in definitions or [...]`** — 这里用了 Python 的 `or` 短路逻辑：
   - 如果调用方传了 `definitions`（非 `None`、非空列表），就遍历调用方传入的那些定义。
   - 如果没传或传了 `None`，就 fallback 到方括号里的**四个内置 scaffold**：
     - `build_simple_react_scaffold()` — 简单 ReAct 循环 scaffold
     - `build_patch_focused_react_scaffold()` — 以 patch 生成为核心的 ReAct scaffold
     - `build_single_shot_patch_scaffold()` — 单次直接生成 patch 的 scaffold
     - `build_planner_coder_verifier_scaffold()` — 多角色（规划者-编码者-验证者）scaffold

4. **`self.register(definition)`** — 对每个 definition 调用 `register` 方法（L24），把它存进 `_definitions` 字典，同时做去重校验（如果 `scaffold_id` 重复会抛 `ConfigError`）。

**总结**：这是一个典型的"带默认值的注册表"模式 —— 正常使用时不需要传参，registry 会自动注册四种内置 scaffold；如果需要测试或自定义场景，可以传入自己的 definition 列表来覆盖默认行为。

---

## Q2: Feedback Policy 完整链路（Pydantic → StrictBaseModel → 策略解析 → runner 调用）

**涉及文件**：

- [schema_base.py](file:///Users/roger/Desktop/claude-code/src/repo_harness/schema_base.py) — `StrictBaseModel` 定义
- [schemas.py](file:///Users/roger/Desktop/claude-code/src/repo_harness/evaluation/schemas.py)（L24-L79） — 枚举和 `ResolvedFeedbackPolicyFacts`
- [policies.py](file:///Users/roger/Desktop/claude-code/src/repo_harness/scaffolds/policies.py)（L17-L69） — `resolve_feedback_policy()` 函数
- [runner.py](file:///Users/roger/Desktop/claude-code/src/repo_harness/evaluation/runner.py)（L88-L92） — 调用位置

### 2.1 Pydantic 是什么

[Pydantic](https://docs.pydantic.dev/) 是一个 Python 第三方库（通过 `pip install pydantic` 安装），核心功能是**数据验证和类型强制**。你用它定义一个类，给每个字段标注类型，Pydantic 就会在你创建对象时自动帮你：

- **校验类型**：比如字段写的是 `int`，你传了 `"abc"`，就会报错。
- **自动转换**：比如字段是 `int`，你传了 `"42"`，它会自动转成 `42`。
- **序列化/反序列化**：可以方便地 `.model_dump(mode="json")` 导出成字典/JSON，也能从 JSON 反向构建对象。

简单理解：**它是一个让你用 Python 类来定义"数据格式契约"的工具**，比手动写 `if isinstance(...)` 校验干净得多。

### 2.2 StrictBaseModel 是什么

在 `schema_base.py` 里：

```python
class StrictBaseModel(BaseModel):
    """默认禁止未知字段，避免运行事实被悄悄写错位置。"""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
```

这是项目自己定义的 Pydantic 基类，在 Pydantic 原生 `BaseModel` 的基础上加了两条规则：

| 配置项 | 含义 |
|---|---|
| `extra="forbid"` | 如果你传入了类里**没声明的字段**，直接报错。防止因为拼写错误（比如 `stauts` 而不是 `status`）导致数据悄悄丢失。 |
| `validate_assignment=True` | 创建对象后，如果你修改某个字段的值（如 `obj.status = "xxx"`），也会重新校验类型。 |

项目里几乎所有数据结构都继承 `StrictBaseModel` 而不是裸的 `BaseModel`，就是为了**拧紧螺丝，不让脏数据偷偷溜进来**。

### 2.3 Feedback Policy 核心问题

RepoHarness 让 agent 去修 bug / 写代码，修完后要跑测试来验证。但有个关键决策：

> **在 agent 还在循环修改代码的过程中，要不要把测试结果反馈给它？如果反馈，反馈多少？**

这就是 **Feedback Policy**（反馈策略）要解决的问题。

### 2.4 两个枚举：策略有哪些选项

在 `schemas.py`（L24-L38）：

**`TestFeedbackPolicy`** — 测试结果要不要给 agent 看：

| 值 | 含义 |
|---|---|
| `disabled` | 完全不给 agent 跑测试的机会 |
| `public_only` | 只把公开测试的结果反馈给 agent |
| `structured_public_feedback` | 把公开测试结果以结构化格式反馈 |
| `oracle_hidden_feedback` | 连隐藏测试（正常对 agent 不可见的）结果也告诉 agent（"作弊模式"，用于研究对比） |

**`FeedbackTestsPassedPolicy`** — 如果 feedback 测试全通过了，agent 要不要停下来：

| 值 | 含义 |
|---|---|
| `stop_immediately` | 测试全过就立刻停 |
| `require_model_final` | 测试全过后再让模型说一轮最终话再停 |
| `continue_` | 测试全过也继续跑（不以此为停止条件） |

### 2.5 `resolve_feedback_policy()` — 策略解析函数

在 `policies.py`（L17-L69），这个函数的职责是**从多个来源中，按优先级合并出最终生效的策略**。输入有三个来源：

```
优先级（高 → 低）：
1. 用户在 run_config 里显式指定的（runtime 配置）
2. scaffold 自带的默认策略
3. 根据任务类型 / provider 推导的兜底默认值
```

核心逻辑拆解：

1. **读取 runtime 覆盖**（L23-L31）：看用户有没有在配置里手动指定策略。
2. **scaffold 兼容性检查**（L33-L41）：`single_shot_patch` scaffold 只能用 `disabled`，因为它一次出 patch，根本没有循环跑测试的环节。
3. **SWE-Bench-like 特殊处理**（L42-L44）：如果任务被标记为 `swe_bench_like_final_only`（只在最后验证，中间不反馈），默认强制 `disabled`。
4. **三级 fallback 合并**（L46-L50）：`runtime 指定 → scaffold 默认 → 任务/provider 兜底`。
5. **passed policy 联动**（L51-L59）：如果测试反馈被禁了（`disabled`），那"测试通过后怎么办"这个策略自然就是 `not_applicable`（不适用）。

最终返回一个 `ResolvedFeedbackPolicyFacts` 对象，**完整记录了"最终选了什么、为什么选了这个"**。

### 2.6 `ResolvedFeedbackPolicyFacts` — 策略解析结果的"审计快照"

在 `schemas.py`（L52-L79），这个类不仅存最终结果，还存了每个来源的原始值：

| 字段 | 含义 |
|---|---|
| `scaffold_default_*` | scaffold 的默认策略（来源 2） |
| `runtime_*` | runtime 配置的覆盖值，可能为 None（来源 1） |
| `resolved_*` | **最终合并后生效的值** |
| `hidden_feedback_visible_to_model` | 推导出的布尔值：隐藏测试结果对 agent 是否可见 |
| `swe_bench_like_final_only` | 任务是否为"仅最终验证"模式 |

`@model_validator` 是 Pydantic 的功能，在对象创建后自动运行交叉校验，防止出现逻辑矛盾的组合（比如 `disabled` 却说隐藏反馈可见）。

### 2.7 在 runner.py 中的调用位置

在 `runner.py`（L88-L92）：

```python
feedback_policy = resolve_feedback_policy(
    run_config=config,
    scaffold=scaffold,
    task=loaded.runnable_task,
)
```

这是在 `run_task()` 函数的早期阶段调用的。解析出来的 `feedback_policy` 随后被用于：

- **L93**：决定 agent 可以使用哪些工具（如果 `disabled` 就移除 `run_tests` 工具）
- **L393-L394**：传给 `ToolExecutionContext`，控制工具执行时的测试反馈行为
- **L402-L404**：传给 `AgentLoop`，控制 agent 循环中的测试反馈和停止条件
- **L309**：写入 `run_config_facts`，作为审计记录保存

### 2.8 一句话总结

整条链路就是——运行一个任务前，先根据"用户配置 → scaffold 默认 → 任务类型兜底"三级优先级，解析出"agent 能不能看测试结果、看多少、看完测试通过后要不要停"这组策略，然后把这个策略贯穿到工具层、agent loop 和审计记录中。

---

## Q3: `with RunRecorder(...) as recorder:` 包裹了什么？`with` 是什么意思？退出时做了什么？

**涉及文件**：

- [runner.py](file:///Users/roger/Desktop/claude-code/src/repo_harness/evaluation/runner.py)（L98-L628） — 调用位置
- [recorder.py](file:///Users/roger/Desktop/claude-code/src/repo_harness/trajectory/recorder.py) — `RunRecorder` 实现

**代码片段**：

```python
with RunRecorder(
    actual_run_id,
    run_dir,
    task_id=loaded.runnable_task.task_id,
    max_artifact_bytes=config.workspace.max_artifact_bytes,
) as recorder:
    recorder.append_event(...)
    ...  # 整个 run_task 的核心逻辑全在这个 with 块里
```

### 3.1 `with` 是什么 — Python 的上下文管理器协议

`with` 是 Python 的语法糖，用于**自动管理"需要善后清理"的资源**。工作原理：

```python
with SomeObject() as obj:
    # 使用 obj 做事情
    ...
# ← 离开 with 块时，不管是正常结束还是抛了异常，都自动调用清理逻辑
```

底层依赖两个魔法方法（在 `recorder.py` L83-L87）：

```python
def __enter__(self) -> "RunRecorder":
    return self          # with 块开始时调用，返回值赋给 as 后面的变量

def __exit__(self, exc_type, exc, traceback) -> None:
    self.close()         # with 块结束时调用（无论正常/异常），执行清理
```

最常见的同类例子是文件操作：`with open("a.txt") as f:` — 不管读写过程中是否出错，文件句柄都会自动关闭。

### 3.2 RunRecorder 包裹了整个运行管线

`with RunRecorder(...)` 的 `with` 块从 `runner.py` L98 一直延伸到 L628，**包裹了单任务运行的完整生命周期**：

```
with RunRecorder(...) as recorder:
    ├─ run_started 事件
    ├─ workspace adapter 创建
    ├─ setup 命令执行
    ├─ baseline 验证
    ├─ agent loop（agent 循环修代码）
    ├─ final patch 冻结
    ├─ final verifier 验证
    ├─ reward / metrics 写入
    ├─ finalize_run(summary)
    └─ adapter.cleanup_workspaces()
```

整条管线里的每一步都通过 `recorder.append_event()`、`recorder.write_artifact()` 等方法，把事件和产物追加写入磁盘。

### 3.3 `__init__` 进入时做了什么

`__init__`（`recorder.py` L30-L65）里做了这些初始化：

| 步骤 | 代码位置 | 作用 |
|---|---|---|
| 创建目录 | L52-L53 | 确保 `run_dir/` 和 `run_dir/artifacts/` 存在 |
| 防止覆盖 | L54-L56 | 如果已 FINALIZED 就拒绝重新打开写入 |
| 进程锁 | L57 → `_acquire_lock()` | 用文件锁（`run.lock`）防止两个进程同时写同一个 run |
| 初始化 JSONL 文件 | L58 | touch `transcript.jsonl` 和 `events.jsonl` |
| 恢复计数器 | L59-L61 | 从已有文件恢复 artifact/event/transcript 计数器（支持断点续写） |
| 写入初始状态 | L62-L65 | 写 `run_status.json`（状态 = `RUNNING`）和空的 `artifacts.json` |

### 3.4 `close()` 退出时做了什么

`close()`（`recorder.py` L79-L81）只做一件事：

```python
def close(self) -> None:
    if self.lock_path.exists():
        self.lock_path.unlink()    # 删除 run.lock 文件，释放进程锁
```

注意 `close()` **不会**自动调用 `finalize_run()`。正常流程是在 `with` 块**内部**、`close()` 之前，由 runner 主动调用 `recorder.finalize_run(summary)`（`recorder.py` L232-L246），它会：

- 写入 `summary.md`
- 把 `run_status.json` 从 `RUNNING` 更新为 `FINALIZED`

如果中途异常导致 `finalize_run()` 没被调用，`close()` 只释放锁，`run_status.json` 会保持 `RUNNING` 状态 —— 这就是一个可审计的"非正常退出"信号，后续的 resume 机制可以据此判断这个 run 是否需要重跑。

### 3.5 一句话总结

`with RunRecorder(...)` 用 Python 上下文管理器模式包裹了整个任务运行管线，进入时创建目录、加锁、初始化记录文件；正常退出前由 runner 显式 `finalize_run` 写入最终状态；最后 `close()` 释放锁。如果异常退出，状态保持 `RUNNING`，为断点续跑提供信号。
