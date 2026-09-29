## 总结

**三题均通过本轮草案复核，可落正式修订单；尚不能据此标为正式评分通过或探针就绪。**

本轮全程只读：在内存中应用草案、核对前后摘要与期望键集，并用正式解析器重解析了 **37 份试跑日志**，结果与记录一致；未新跑容器。草案内容与对应试跑输入一致。本包仅涉及 **R-a／R-c**。

## 1. `scrapy__e9387529`：通过

1. **模板和公开依据成立。** 三个新增测试分别针对普通 dict、空字段默认值、serializer 返回值，均属窄范围 R-c。普通 dict 有 [exporters.rst:170](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/scrapy__e938752973b4fc53e0fa0c0bc68a431613b987e4/worktree/docs/topics/exporters.rst:170) 支持；serializer 返回值规则见同文件 **164–168 行**，空字段和非文本值规则见 **204–217 行**。缺字段为 `None` 另有 [exporters.py:54](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/scrapy__e938752973b4fc53e0fa0c0bc68a431613b987e4/worktree/scrapy/exporters.py:54) 的默认参数及 **71–78 行**支持。

2. **试跑支持验收方向。** C1 两次 **65/65**，RC2 同样通过；noop、gold、C2、C3 均不匹配期望。C2 的 dict 漏修被新测试抓住；C3 的 `binary=False` 回归仍被拒。C1 只转换顶层键、不二次处理值，结合源码、历史行为对照及独立复核，足以作为本次替代正对照，不是仅凭满分认定合理。gold 在新增的 `None`／整数返回值测试中抛 `TypeError`，因此期望显然不是照抄 gold 输出。见[试跑证据](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/scrapy__e938752973b4fc53e0fa0c0bc68a431613b987e4/trials)。

3. **未扩大需求或为保 gold 放宽要求。** 原 62 键及状态不变；没有替嵌套普通 dict 键、非字符串键或 serializer 返回字符串的争议选边。题面“keys and values … bytes”需结合既有 serializer／非文本值契约理解，不能推成任意值都必须字节化。无公开题面改动或答案泄漏。

4. **结论：通过，可落正式修订单。**

## 2. `scrapy__75450e75`：通过

1. **两处 R-c 均有公开依据。** [题面第 19 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/scrapy__75450e75d269b2a2b00b6303af1033df1f69cc67/user_prompt.txt:19)要求异步操作实际推进；[asyncio.rst:9](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/scrapy__75450e75d269b2a2b00b6303af1033df1f69cc67/worktree/docs/topics/asyncio.rst:9)及 `coroutines.rst:17–18、32–38` 支持使用 asyncio 的下载中间件协程。第二次 fetch 有公开测试 `test_command_shell.py:84–88`，槽位释放依据是 [settings.rst:1383](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/scrapy__75450e75d269b2a2b00b6303af1033df1f69cc67/worktree/docs/topics/settings.rst:1383)：只有正在处理的响应占用额度。

2. **试跑支持验收方向。** K1 两次 **19/19**，K1b 同样通过；noop、gold、K2、K3 均为不匹配。K1 在线程启动时设置 reactor 已有循环，源码与历史“两次 fetch 完成、槽位空闲”对照支持其合理性。新增日志把 K3 的既往静态风险落实为 `await wasn't used with future`；gold 两个新键缺少完成标记，整轮约 155 秒。不是补丁应用失败或收集失败。见[试跑证据](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/scrapy__75450e75d269b2a2b00b6303af1033df1f69cc67/trials)。

3. **辅助模块和闹钟可接受，但不能宣称零抖动风险。** `sleep(0.1)` 用于产生真正需要等待的 Future，标记写在 await 完成之后，不靠“睡够时间”猜完成。60 秒闹钟只限制子进程挂起，没有耗时比较或事件顺序断言；**它仍是实际墙钟上限**，不能表述成完全没有时间约束。当前 K1 两轮整套测试约 37／39 秒，未见误拒；正式资源配置下仍须确认裕量。辅助模块保持私有，不规定候选修改位置；没有为保 gold 放宽要求，也未新增题面矛盾。

4. **结论：通过，可落正式修订单。**

## 3. `scrapy__9a15fcf8`：通过

1. **R-a 与追加两处 R-c 均成立。**
   - **R-a：** 两键确因 bytes／str 不兼容而固定失败，不是时序抖动；上游在 [py3-ignores.txt:40](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/scrapy__9a15fcf89a151811de8ac783419df0512c863d5e/worktree/tests/py3-ignores.txt:40)忽略该公开测试文件，由 `conftest.py:25–29` 生效。草案确已同时删除两个方法及两个 expected 键。
   - **R-c-1：** `test_2.py` 与公开 `tests/test_http_headers.py` **逐字节一致**。bytes 契约见 [headers.py:18](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/scrapy__9a15fcf89a151811de8ac783419df0512c863d5e/worktree/scrapy/http/headers.py:18)及公开测试 **25–30 行**。17 个方法围绕同一 Headers API 的既有契约，属于相关回归范围，不因多于一条断言而越出 R-c。
   - **R-c-2：** [题面第 18 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/scrapy__9a15fcf89a151811de8ac783419df0512c863d5e/user_prompt.txt:18)要求一般的 `application/x-json`，不是仅示例完整字符串；无参数和另一 charset 是直接实例，符合 §4 第 2 步。

2. **试跑支持完整的纠错链。** gold 两次 **23/23**；noop 为 0；P4 从误拒变为通过；`bad_headers_str`、逐字特判候选均为 0。只做 R-a 时 `bad_headers_str` 确会通过，追加 Headers 测试因此有具体必要性。最终 **删除 2 键、增加 18 键，共 23 键**，所有相关试跑均无 missing／unexpected。见[试跑证据](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/scrapy__9a15fcf89a151811de8ac783419df0512c863d5e/trials)。

3. **未扩大需求或保护错误 gold。** 新期望分别来自公开旧测试和题面一般要求。P4 只在输入边界解码 bytes，保留 Headers 契约；删除死键不意味着要求 header 路径继续出错。该路径仍未覆盖，应保留现有登记。无题面改动或答案泄漏。

4. **结论：通过，可将 R-a＋两处 R-c 合并落正式修订单，无需新增用户决策。**

## 正式验收剩余项

三题的 **§5 试跑对照条件已满足，正式评分验收尚未完成**。落修订单、更新 pins 并重建材料后，应在正式权限、摘要核验及资源配置下复验：

- e938：C1／noop／gold／C2／C3。
- 75450：K1／noop／gold／K2／K3，并确认辅助模块可导入、挂起候选能在评分期限内完整产出结果。
- 9a15：gold／noop／P4／`bad_headers_str`／逐字特判。

正式结果一致后，才可核销本次修订验收；探针资格还需满足批次 README 的其余条件。