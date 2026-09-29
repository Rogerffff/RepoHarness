## 结论：需小改

**R-c #1、#2 可接受；R-c #3 应本轮补入请求目标里的 CR、TAB，期望键数从 134 增至 136。** 补齐并复核前维持 `needs_repair`，不落正式修订单。本次全程只读，未修改文件。

### 1. 模板与公开依据

三处均属于 R-c，各针对一个窄问题；没有删测试、放宽旧断言或修改题面，不涉及 R-a／R-b／R-e／R-f。

- **#1 成立。** [题面第 4、22 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/user_prompt.txt:22)不是只要求拒绝 `ÿ`。核对后，`http_parser.py:59–65` 定义的是 method/token；`client_advanced.rst:108–112` 本文只讲字段名大小写，但其链接的 [RFC 7230 §3.2](https://www.rfc-editor.org/rfc/rfc7230.html#section-3.2)明确规定字段名为 token。中部西里尔字母确属无效字符，依据成立。
- **#2 成立。** FF 单独分隔、VT 分隔是题面第 23 行“不当空白与控制字符”的非示例实例。M1 更正正确：[RFC 9112 §3](https://www.rfc-editor.org/rfc/rfc9112.html#section-3)的宽松许可同时列出 HTAB、VT、FF、裸 CR，不能用它单独排除 HTAB。
- **I4 确属第 4 步 S1，#3 在模板内。** 题面使用的是“contains”；源码 `http_parser.py:550、564–566` 与私有矩阵一致：base 拒绝目标内 LF／FF／CR／TAB，gold 接受全部四种。[RFC 9112 §3.2](https://www.rfc-editor.org/rfc/rfc9112.html#section-3.2)也明确禁止请求目标包含空白。断言父类 `BadHttpMessage` 合理：`_http_parser.pyx:829–834`、`http_exceptions.py:96–106` 支持 `BadStatusLine`／`InvalidURLError` 两种拒绝方式。

### 2. 验收与替代正对照

我在内存中应用三处 edit：每处旧文本唯一，结果摘要与草案一致；旧 129 键逐键不变，仅新增五个 `PASSED`。重算全部试跑结果，无 missing／unexpected：

| 候选 | 当前草案试跑 | 与期望不符的键 |
|---|---:|---|
| ALT1、ALT2、ALT3、ALT4 | 1 | 无，134/134 状态一致 |
| gold | 0 | 仅目标内 LF、FF |
| noop | 0 | 恰好 5 键 |
| DG1 | 0 | 西里尔字母、VT 两键 |

**ALT2 主正对照、ALT1 第二正对照的依据充分。** 不只是隐藏测试满分：补丁语义、22 行私有矩阵、原材料正式评分 129/129，以及四个公开文件的 259 项通过均相互支持。额外拒绝 `\x01`、版本号 FF，以及 ALT1 拒绝字段名 `/`，没有违反已核实的公开行为。ALT2 存档与 `env_reverify_positive_control` 的 SHA-256 也一致。

ALT3 的更正成立：整行检查必然拒绝版本号 FF；ALT4 才能支持“这三项额外严格性不是评分要求”。但 ALT3／ALT4 的相关行为仍是源码推导／模拟，**不是容器矩阵实测**。

新期望不是抄 gold：gold 正好违反 #3。试跑支持修订方向，尚不等于正式验收；仍需新材料／镜像下确认摘要、严格键集及完整失败回溯，不能把截断日志推定的 `DID NOT RAISE` 写成已核实全文。

### 3. 需求边界与泄漏

未发现扩大需求、为保 gold 放宽要求或新增答案泄漏。公开包不变；原有示例 1 的 P4 问题仍在，但不是本轮新增。修订后应继续明确：**这是标明版本的自建题，原 gold／上游同款修复按设计得 0。**

### 4. 本轮必须补齐什么

[修订方案第 380–384 行](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/revision_plan.md:380)以“没有新的已有候选”为由只登记 CR／TAB，这个理由不足：**已有 gold 就是原材料得 1、同时放行这两例的具体候选，I4 已据此成立。** 这不是要求继续搜索反例，而是补完已确认的同一窄问题。

具体修改：

- #3 增加 `b"GET /pa\rth HTTP/1.1"`、`b"GET /pa\tth HTTP/1.1"`，仍断言 `BadHttpMessage`；同步新增两个 expected 键及摘要、说明。
- 补试跑：ALT1–ALT4 应仍为 1；gold 应仅在 #3 四键失败；noop 仍差五键，DG1 仍差两键。
- “gold 切分＋只拒 LF／FF”的变体目前只能记**静态推断**，不得写成已有满分实跑。

补齐后复核，再落正式材料并正式评分。其余已登记缺口不要求本轮继续扩测，也不需要重新请求用户授权。