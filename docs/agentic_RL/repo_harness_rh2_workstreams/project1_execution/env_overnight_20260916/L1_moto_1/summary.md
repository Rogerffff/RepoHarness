# L1_moto_1 · 逐题静态审查小结（moto，19 题）

负责人：Claude sub-agent（Opus 5）。起始 2026-09-16 02:10（本机）。逐题记录见 `records/<instance_id>.json`。
证据引用约定：`<commit>:<path>:<line>` 指裸克隆 `runs/env_overnight_20260916/repos/moto`；
`stage1:<id>/<gold|empty>` 指 `runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/<id>/<...>/offline/a1/`；
`mat:<id>/<kind>` 指从 s2 bundles 抽出的本地副本 `runs/env_overnight_20260916/L1_moto_1/mat/`。

| task | 主要发现 | 建议处置 | 下一实验 |
| --- | --- | --- | --- |
| getmoto__moto-5701 | P1 评分材料双 bug：①F2P/P2P 参数化 ID 被按空白截断（真实 `[baz bar]`/`[file another]`），当前靠 RH2 status_map 解析器同款截断才侥幸匹配；②P2P 的 `[/the-key-unîcode/test]` 与 pytest 的 ascii_escaped `\xee` 形式永不相等，p2p_missing=1 直接导致 gold=RESOLVED_NO。P2：题面只讲 Spark 现象，"key 含空格被编码成 +" 只在 hints 里；F2P 仅覆盖 ServerMode，decorator 模式缺陷可被放过 | needs_repair | 容器内 `pytest --collect-only -q` 取运行时真实 ID，在匹配层加 ascii_escaped 归一化后重跑 gold |
| getmoto__moto-4799 | P1：P2P 含两条 `@pytest.mark.network` 用例（test_context_manager / test_decorator_start_and_stop），按设计要连 `https://ec2.us-west-1.amazonaws.com/`，离线沙箱必然 FAILED → gold=RESOLVED_NO，这是本题唯一阻塞。题面自足、gold 最小、边界干净 | needs_repair（剔除 network P2P 后可用） | 重跑 gold，对比加 `-m 'not network'` 前后的 verdict |
| getmoto__moto-4833 | 同因 P1（同两条 network P2P）。P2：4833 的 base 已包含 4799 的 gold（commit 010d525de #4799），两题同文件同函数、P2P 交集 17/23、4833 的 P2P 就含 4799 的 F2P → 顺序泄漏 + 重复。P3：gold 新增的 `unittest.TestCase in klass.__mro__` 限制无任何测试覆盖 | needs_repair + 与 4799 二选一 | 对全 216 题按 (repo, gold 文件, gold 函数) 聚类，统计同类“续作对” |
| getmoto__moto-5899 | 题目本身健康（gold=FULL，DeepSeek 也 FULL）。P2：F2P 判别力弱——get_groups_for_user 本身已去重，F2P 只有"remove 一次后为空"一条有判别力，改 remove 侧（while 循环删干净）可满分通过却不修 add 侧。P2：rc_install=2 —— 离线下 `make init` 必然 DNS 失败被静默容忍。P3：hints 含精确到 `moto/iam/models.py#L2473` 的永久链接 | ready_for_probe（建议补一条 get_group 成员数断言） | 手工构造 remove 侧 patch 跑一次，确认会被判 RESOLVED_FULL |
| getmoto__moto-6470 | P1 题面二义：题面只说"调用返回 500"，自然读法是"应当创建成功"，gold 却要求"按真实 AWS 拒绝"。DeepSeek 真实轨迹正是把参数改成有默认值让它成功（candidate.diff），被判 RESOLVED_NO。P1 exact string：还要逐字命中 `Error executing request, Exception : Instance role is required.` / `... Resource minvCpus is required.` 且异常类型必须是 ClientException（同函数其它校验用的是 InvalidParameterValueException，是反向误导）。P3 gold 不完整：maxvCpus/subnets/securityGroupIds 缺失时仍 500 | needs_repair（补题面后可用） | 补一句"真实 AWS 会返回 ClientException"后重跑 3 次 rollout，看方向是否翻转 |
| getmoto__moto-6913 | P1 静态泄漏：题面直接写出 `moto/sesv2/responses.py line 45-50` 并贴出完整修正代码 `body=content["Simple"]["Body"]["Text"]["Data"],`，与 gold 唯一新增行一字不差 → 解题退化为复制粘贴（gold 与 DeepSeek 都 FULL）。P3：F2P 新断言包在 `if not settings.TEST_SERVER_MODE:` 内，若环境设了 ServerMode 会在 base 上静默通过 | needs_review（宜作冒烟/最低档，或改写题面） | 对全 216 题做"gold 新增行在题面中出现"的子串匹配，产出泄漏清单 |
| getmoto__moto-5417 | P1：P2P 的 `test_multipart_upload_with_copy_key[the-unicode-💩-key]` 因 pytest ascii_escaped 转义而永不匹配 → p2p_missing=1 → gold=RESOLVED_NO（与 5701/5545/5562/6308 同因，本包 5/19 题）。P2：两条含空格的参数化 ID 被截断，靠解析器同款 bug 侥幸匹配。P2：题面说"默认 ACL 没设置"，gold 却改读路径把 None ACL 当无限制 —— 两种修法对未签名访问结果相反（200 vs 403），F2P 完全不覆盖该分支 | needs_repair | 匹配层加 ascii_escaped 归一化后批量重跑这 5 题的 gold |
| getmoto__moto-5545 | P1 同上的 💩 ID 不匹配 → gold=RESOLVED_NO。P1 静态泄漏：题面 `Adding this to S3Backend fixes the warning:` 后整段给出 reset() 实现，gold 仅多一个 isinstance 守卫。P2 测试脆弱：F2P 在 `catch_warnings` 内调 `gc.collect()`，会回收整个进程的垃圾 —— 同文件先前用例的遗留句柄就能让它失败，与本题修没修无关。P3 gold 不完整：不遍历 `bucket.multiparts`，且 `key.multipart` 分支从未被触达（F2P 用的是普通 put_object） | needs_repair | 整文件跑 vs 单条跑 × base/gold 各 3 次，验证该 F2P 是否顺序敏感 |
| getmoto__moto-5562 | P1 同上的 `î` ID 不匹配 → gold=RESOLVED_NO。P2 跨题答案可见：5562 的 base 是 5701 base 的祖先，5701 的 base 里已含 commit `5f7f3e6e4 ...(#5562)` 即本题 gold 原文；且 5562 的 F2P 就是 5701 的 P2P 之一（本包第二对，第一对是 4799→4833）。P3：F2P 第二块断言（CommonPrefixes 长度 8 / Versions 长度 24）题面无任何线索 | needs_repair | 对全 216 题按仓库建 base_commit 偏序，统计"答案可见对"总数 |
| getmoto__moto-6308 | P1 同上的 💩 ID 不匹配 → gold=RESOLVED_NO（本包因此单一原因不可用的第 5 题）。P3：F2P 只做"原地 copy"，源与目标内容相同，无法区分 gold 改动的语义（checksum 取源还是取目标），只检验了"不再抛 ValueError"。题面 traceback 精确到 `responses.py:1634` 的 `key_to_copy.value`，属中等泄漏 | needs_repair | 补一条跨 key 带 ChecksumAlgorithm 的 copy 断言，区分 checksum 取哪一侧 |
| getmoto__moto-7105 | P1 需要真实 Docker：无 /var/run/docker.sock → `Error while fetching server API version: FileNotFoundError`，`test_cancel_pending_job` 走 failed-dependency 分支报 `KeyError: 'statusReason'` → gold 只能 RESOLVED_PARTIAL；moto 自带开关 `TESTS_SKIP_REQUIRES_DOCKER`（tests/markers.py + settings.py:41），但 4 条 F2P 本身就带 @requires_docker。P1 解析器污染：status_map 24 个键里有 2 个是 captured-log 行（`moto.batch.models:models.py:899`），证明解析作用于整份输出而非短摘要区。P2 F2P 是顺序连锁副产物：11 条 F2P 对 2 行 gold，P2P 仅 1 条 | needs_repair（或剔除） | 设 TESTS_SKIP_REQUIRES_DOCKER=1 重跑 base/gold；再单跑新增那一条 F2P 看能否独立区分 |
| getmoto__moto-4847 | P2 判分与题面脱节：题面核心诉求是 DNS 验证的 `ResourceRecord`(CNAME) 与 `ValidationMethod`，F2P 一条都没查 —— 只补 DomainName/ValidationDomain/RenewalEligibility/Options 的部分修复即可满分；反过来 F2P 又要求题面从未提及的 `RenewalEligibility='INELIGIBLE'` 与 `Options`。P3 test_patch 含非测试数据清单 `tests/terraform-tests.success.txt`（只被 .github/workflows/build.yml:261 使用，不被 pytest 读取）。P3 gold 夹带无关改动 `Serial` → `str(Serial)` 与 ExtendedKeyUsages，均无断言覆盖 | needs_review（补断言+补题面后可用） | 构造只补 DomainName/ValidationDomain 的 patch，确认会被判 RESOLVED_FULL |
| getmoto__moto-4975 | 运行面健康（gold=FULL, rc_install=0）。P3 gold 自身引入别名缺陷：`group_ids = nic.get("SecurityGroupId") or []` 直接引用 nic 里的 list，随后 `extend` 就地修改；而 `add_instances` 在 count>1 时复用同一份 nics，第二个实例会拿到被追加过的列表（base 每次新建列表，反而没这问题）。P3：gold 改动的 extend 分支在 F2P 下从未执行（MinCount=1 且不传顶层 SecurityGroups） | ready_for_probe（建议补回归） | MinCount=2 + NetworkInterfaces + SecurityGroups 同时给，比较两实例 ENI 的 Groups |
| getmoto__moto-4990 | 本包质量最好的题之一：题面可定位、gold 是模板变量名单点修复、边界干净、gold=FULL 且 rc_install=0。P3 唯一缺口：F2P 只查单个 loadbalancer 的 ResourceArn，describe_tags 的多资源列表语义与 targetgroup/listener 类型无断言，"只对第一个入参正确"的实现可满分 | ready_for_probe | 补一条同时查 loadbalancer + targetgroup 两个 ARN 的用例 |
| getmoto__moto-5020 | 运行面健康（gold=FULL, rc_install=0）。P2 题面根因误诊：标题与正文都说是"缓存"，真实原因是 `route-search.exact-match` 这个 filter 根本没实现、未知 filter 被静默忽略于是每次返回全量（正确根因只在 hints 里）。P3 弱断言：只查 `Routes[0]`，不查 `len(Routes)`，"排序而不过滤"的实现可满分。P3 同函数邻近缺陷：`routes[:int(max_results)]` 对 dict 切片，gold 未碰也无覆盖 | ready_for_probe（标记为"题面根因错误"分层） | 跑 3 次 rollout，统计模型先查缓存还是先查 filters |
| getmoto__moto-5134 | 本包综合质量最好的题：题面自带真实 AWS 对照用例并讲清"字段缺失 vs 值为 null"的区别，gold 用 UNDEFINED 哨兵最小修复，F2P 正反四象限全查（把 `leaf_exists = is_leaf_node` 这种偷懒修法拦住）。P2 唯一问题是 P2P 的 `test_event_pattern_dump[{"source":` 被按空白截断（真实 ID 含带空格的 JSON），当前靠解析器同款截断侥幸匹配 —— 是碰撞风险最直观的例子 | ready_for_probe | 用本题 test_output.txt 作夹具验证新解析器能还原完整 ID |
| getmoto__moto-5286 | 运行面健康（gold=FULL, rc_install=0，P2P 171 条为本包最多）。P3 单向断言：只验"有 domain 时返回正确值"，不验"无 domain 时不返回该键"，无条件写入 Domain=None 的实现可满分。P3 gold 语义外溢：`if self.domain:` 插在 `if extended/else` 之后，导致 list_user_pools（responses.py:71 用 extended=False）也返回 Domain，而 AWS 的 UserPoolDescriptionType 不含该字段，无用例覆盖 | ready_for_probe | 补"无 domain 的池不应有 Domain 键"与 list_user_pools 键集合两条断言 |
| getmoto__moto-5321 | 运行面全绿（gold=FULL, rc_install=0，F2P 正反都查）。P1 静态泄漏：题面 `It seems that describe_db_clusters is missing a simple check...` 后逐字给出 gold 的全部两行新增代码，并给出完整异常类型与消息 —— 与 6913、5545 构成本包"答案泄漏三题"（19 题中 3 题）。P3：缺一条"传已存在 id 正常返回"的显式断言 | needs_review（冒烟档或改写题面） | 并入全 216 题的"gold 新增行出现在题面"子串匹配 |
| getmoto__moto-5347 | 运行面健康（gold=FULL, rc_install=0）。初查担心 F2P 只有反向断言（无 keypair 时不返回 KeyName），"删掉 `<keyName>` 整行"会满分；**静态核实后排除**：P2P 的 `test_run_instance_with_keypair`（test_instances.py:1562-1565）提供正向锚点。P3 gold 不完整：spot_fleets.py:109、spot_instances.py:115/173 三处同类缺陷未修；上游用例自带 `# TODO: Add additional asserts` | ready_for_probe | 无（已核实）；如加固则按 TODO 补默认实例字段断言 |

---

## 跨题发现（不属于单题，但决定 moto 整体可用性）

复现脚本在 `scripts/`（相对本目录），都只读本机既有材料，不联网、不起容器。跑法：`python3 scripts/<name>.py`。

### A. RH2 的 pytest 状态解析器有三个可实证的缺陷（P1）

直接源码证据：`rh2/src/repoharness2/envpack/swegym_parsers.py:44-57` 的 `parse_log_pytest`：

```python
for line in log.split("\n"):
    if any([line.startswith(x) for x in TEST_STATUS_VALUES]):
        if line.startswith("FAILED"):
            line = line.replace(" - ", " ")
        test_case = line.split()
        if len(test_case) <= 1:
            continue
        test_status_map[test_case[1]] = test_case[0]
```

即「行首是状态词 → `line.split()` 取 `[1]` 当 nodeid」。由此产生：

1. **含空格的参数化 ID 被截断**。实证：`stage1:5701/gold/test_output.txt:1620` 的
   `PASSED tests/test_s3/test_server.py::test_s3_server_bucket_create[baz bar]` 被记成
   `...[baz`。本包命中 4 题（5701 F2P + P2P、5417 P2P×2、5545 P2P×2、5134 P2P）。
2. **captured-log 行被当成测试结果**。实证：`stage1:7105/gold` 的 status_map 24 个键里有 2 个是
   `moto.batch.models:models.py:899` / `:954`，来自 `test_output.txt:509` 的
   `ERROR    moto.batch.models:models.py:899 Failed to run AWS Batch container ...`；该行在
   `short test summary info`（第 1145 行）之前，说明解析作用于整段输出而非短摘要区。
3. **同一 nodeid 多条 verdict 按"后者覆盖"**。实证：`stage1:4799/empty/test_output.txt:1336` 是
   `ERROR ...::TestSetUpInBaseClass::test_a_thing`、:1339 是 `FAILED` 同一 ID，status_map 记为 FAILED。
   `-rA` 的区段顺序是 PASSED → ERROR → FAILED，所以当前巧合地偏保守；但这是顺序的副产品，不是设计。

**关键约束（决定修法）**：该 parser 是从 SWE-Gym fork 逐字移植的（文件头 `SWEGYM_PARSERS_SOURCE_COMMIT
= 242429c1...`），而 F2P/P2P 常量多半也由同一个上游 parser 生成。所以缺陷 1 目前**不破坏匹配**——
常量和解析器犯的是同一个错，互相抵消。**单独修解析器而不同步重算常量，会把现在能跑的题打坏。**
建议：要么两边一起改（解析锚定到短摘要区 + 保留整行 nodeid + 重算常量），要么都不动、只把受影响的题
登记为"依赖截断巧合"。缺陷 2、3 可以独立修，风险低。

### B. 非 ASCII 参数化 ID 不匹配——本包 5/19 题不可用的单一原因（P1，已给出精确修法）

受影响：5701、5417、5545、5562、6308，全部 `gold=RESOLVED_NO` 且 `p2p_missing=1`，题目本身没问题。

机制：常量里是原始字符（`î`、`💩`），pytest 输出的是 `ascii_escaped` 形式（`\xee`、`\U0001f4a9`）。
`scripts/idfix.py` 用 `param.encode('unicode_escape').decode('ascii')` 重算，**5 题 5 条全部精确命中运行时 ID**：

| 题 | 常量 | 运行时（已核对 test_output.txt） |
| --- | --- | --- |
| 5701 / 5562 | `test_key_with_special_characters[/the-key-unîcode/test]` | `...[/the-key-un\xeecode/test]` |
| 5417 / 5545 | `test_multipart_upload_with_copy_key[the-unicode-💩-key]` | `...[the-unicode-\U0001f4a9-key]` |
| 6308 | `test_copy_key_boto3[the-unicode-💩-key]` | `...[the-unicode-\U0001f4a9-key]` |

所以这是匹配层一个归一化函数就能解决的问题，不需要逐题改常量，也不该用"找不到就跳过"兜底（会同时
掩盖真正缺失的用例）。注意它与 A.1 不同：A.1 两边同错所以抵消，这里两边不同错所以暴露——说明常量的
生成环境与当前镜像的 pytest 行为已经不一致（见 D）。

### C. 离线沙箱与外部依赖（P1）

- **`@pytest.mark.network`**：4799、4833 的 P2P 各含 2 条（`test_context_manager`、
  `test_decorator_start_and_stop`），按设计要连 `https://ec2.us-west-1.amazonaws.com/` 断言 AuthFailure，
  离线下必然 FAILED → 两题 `gold=RESOLVED_NO`。moto 在 `setup.cfg` 里正式声明了 `network` marker。
  `scripts/netscan.py` 已扫全包，只有这两题命中。
- **`@requires_docker`**：7105 的 F2P 有 4 条带该标记，无 docker.sock → `gold=RESOLVED_PARTIAL`。
  moto 提供开关 `TESTS_SKIP_REQUIRES_DOCKER`（`tests/markers.py` + `moto/settings.py:41`），但把它们转成
  SKIPPED 后 F2P 也就不成立了。
- **install 阶段离线静默失败**：5899/6470/6913/6308/7105 的 `rc_install=2`，原因是 `make init` 的 pip
  连不上 PyPI（`stage1:5899/gold/test_output.txt:384-388` 的 `Temporary failure in name resolution`），
  但流程继续、靠镜像预装跑测试。对纯 Python 的 moto 无害（gold 能 FULL 即证明 `/testbed` 源码被 import），
  但 `rc_install != 0` 不应被当作 pass，否则真正的安装失败会被这层噪声淹没。

### D. 环境保真度：18/19 题在上游从未声明支持的 Python 上运行（P2）

| 题（举例） | moto 版本 | 上游 setup.py/cfg 声明的最高 Python | 实际运行 |
| --- | --- | --- | --- |
| 4799 / 4833 | 3.0 | 3.10 | 3.12.4 |
| 4975/4990/5020/5134/5286/5321/5347 | 3.1 | 3.10 | 3.12.4 |
| 5417 / 5545 / 5562 | 4.0 | 3.10 | 3.12.4–3.12.7 |
| 5701 | 4.0 | 3.11 | 3.12.7 |
| 5899 / 6470 / 6308 | 4.1 | 3.11 | 3.12.4–3.12.7 |
| 6913 | 4.2 | 3.11 | 3.12.4 |
| **7105** | 4.2 | **3.12** | 3.12.4（唯一合规） |

pytest 统一是 8.3.2/8.3.3。这既是 B 里"常量与运行时 ID 形式不一致"的合理解释（常量生成时的 pytest
与镜像里的不是同一套行为），也是一类独立风险：2022 年的 moto 跑在 2023 年底才发布的 Python 上，
任何 stdlib 行为漂移（`datetime.utcnow` 弃用、`distutils` 移除等）都会以"与题目无关的失败"形式出现。
目前 19 题里没观察到由此直接引发的失败，但这是"看起来没事"而不是"已验证无事"。

### E. 题面把答案直接给出（P1，3/19）

`scripts/leak.py` 对 gold 的新增行做去空白规范化后在题面里做子串匹配：

| 题 | gold 新增行 | 题面命中 |
| --- | --- | --- |
| 6913 | 1 | **1/1**（`body=content["Simple"]["Body"]["Text"]["Data"],`，还点名 `responses.py line 45-50`） |
| 5321 | 2 | **2/2**（`if cluster_identifier not in self.clusters:` + `raise DBClusterNotFoundError(...)`） |
| 5545 | 9 | **8/9**（题面整段给出 `S3Backend.reset()` 实现，gold 只多一个 isinstance 守卫） |
| 7105 | 2 | 1/2 —— **假阳性**：命中的 `job.join(0.2)` 是 traceback 里的上下文行，gold 只是给它加了缩进 |
| 其余 15 题 | — | 0 |

脚本可直接用于全 216 题；用时要带上"gold 的 diff 上下文行重排会造成假阳性"这个已知偏差。

### F. 跨题答案可见 / 重复（P2，本包 2 对）

- **4799 → 4833**：`git log fc1ef55a..bb6fb120 -- moto/core/models.py` 含 `010d525de ...(#4799)`，
  即 4833 的 base 已包含 4799 的 gold；4833 的 P2P 里就有 4799 的 F2P（`TestSetUpInBaseClass::test_a_thing`），
  两题 P2P 交集 17/23。
- **5562 → 5701**：`merge-base --is-ancestor 121e3ead d6c43840` 为真，`git log 121e3ead..d6c43840 --
  moto/s3/models.py` 含 `5f7f3e6e4 ...(#5562)`，5701 的 `moto/s3/models.py:1626-1632` 就是 5562 的 gold 原文；
  5562 的 F2P `test_list_object_versions_with_delimiter` 是 5701 的 P2P。

一个 19 题的小包里出现 2 对，说明按仓库建 base_commit 偏序做一次全量"答案可见对"检查是值得的。

### G. 判分口径的共性缺口（P2/P3，用于后续统一处置）

- **测试放过错误修复**：5899（`get_groups_for_user` 自带去重，改 remove 侧也满分）、4847（题面核心的
  `ResourceRecord`/`ValidationMethod` 一条都没查）、5417（未签名访问分支无覆盖）、7105（删掉 join 也满分）、
  5020（只查 `Routes[0]` 不查 `len`）。
- **题面推不出 F2P**：6470（方向二义 + 两条必须逐字命中的 AWS 文案，DeepSeek 真实轨迹选了相反方向被判 0）、
  4847（`RenewalEligibility`/`Options` 题面从未提）、5701（空格/ServerMode 只在 hints 里）、
  7105（array job 触发条件只在 hints 里）。
- **题面根因误诊**：5020（说是"缓存"，实为 filter 未实现）。这是真实 issue 的常态，建议单独分层统计。
- **gold 不完整或有夹带**：6470（同函数其它必填键仍 500）、5545（不遍历 `bucket.multiparts`）、
  5347（spot_fleets/spot_instances 三处同类缺陷未修）、4847（`Serial` 转 str 与 ExtendedKeyUsages 属夹带）、
  4975（gold **引入**列表别名副作用，base 反而没有）、5286（让 `list_user_pools` 也返回 Domain，与 AWS 不符）。
  含义：用"与 gold 的文本差异"给候选打分会系统性低估正确解答，应改用"被 F2P 检验的行为"。

---

## 覆盖与统计

- **覆盖：19/19 题全部完成**（ASSIGNMENT.json 的全部题目），每题一份 `records/<instance_id>.json`。
  起止：2026-09-16 02:10 → 02:5x（本机时间）。**未做清单：空**。
- 处置建议分布：`ready_for_probe` 7（4975、4990、5020、5134、5286、5347、5899）、
  `needs_repair` 9（5701、4799、4833、5417、5545、5562、6308、6470、7105）、
  `needs_review` 3（6913、5321、4847）。
- issue 严重度：P1 15 条、P2 14 条、P3 21 条。出现最多的类别是
  `grading_materials/id_encoding_mismatch`（5 题，单一原因就让本包 26% 不可用）。
- **只要修好 B（非 ASCII ID 归一化）与 C（剔除 network 标记的 P2P），`needs_repair` 9 题里有 7 题
  可直接转 `ready_for_probe`**；剩下 6470（题面二义）与 7105（需 Docker）要单独裁定。
  换算：本包当前可用 7/19（37%），修完这两处后是 14/19（74%）。

### 每题检查项完成度说明

按 L1 brief 的要求填了 1、2、3、4/17、5、23、24、25、26、27、29 与 6/7/11 静态线索，共 14 个编号。
其余 40 项检查里本轮**未触及**的（一律按 `not_checked` 理解，记录里未列出以免造成"已查"的错觉）：
需要实跑容器、需要跨仓库统计、或属于运行期观测的条目。凡证据不足的地方记录里写的是 `issue` 并
在 `next_experiment` 写清了怎么验证，没有因为"没发现问题"就写 pass。

### 最值得用户裁定的 3 个问题

1. **状态解析器的两个 bug 目前互相抵消，要不要动？** `swegym_parsers.parse_log_pytest` 按空白切 nodeid，
   而 F2P/P2P 常量多半由同一个上游 parser 生成，所以含空格的参数化 ID 现在"错得一致"因而能匹配。
   单独修 parser 会打坏现在能跑的题；两边一起改要重算全部常量。第三条路是都不动、只登记受影响题目。
   三条路的代价和风险差别很大，需要先定方向再动手。（非 ASCII 那条不在此列——它两边不一致、必须修。）
2. **7105 这类需要 Docker 的题，是给环境装 DinD 还是直接剔除？** 装 DinD 与"离线沙箱"的现有约束冲突
   （还要预拉 batch 基础镜像）；设 `TESTS_SKIP_REQUIRES_DOCKER=1` 会把 4 条 F2P 变成 SKIPPED，本题也就
   没有判别力了。这个决定会外溢到 moto 之外所有依赖容器的题，应该一次定清楚。
3. **"题面即答案"的题（6913/5321/5545，本包 16%）怎么处置？** 三选一：作为流水线冒烟/最低难度档保留
   但不计入训练难度分布；改写题面删去定位与修复代码后入训练集；直接剔除。当前它们的 gold 与 DeepSeek
   都是 RESOLVED_FULL，作为冒烟很好用，但作为训练样本奖励的是"照抄题面"而不是"定位与推理"。

### 遗留的开放项（本轮能做的静态核对都已做完，剩下都需要实跑）

- B 的归一化修好后，5 题的 gold 是否真能从 RESOLVED_NO 转 FULL（需要容器重跑）。
- 4799/4833 剔除 network P2P 后是否转 FULL（需要容器重跑）。
- 5899 的 remove 侧修法、7105 的删 join 修法、5020 的"排序不过滤"修法是否真会被判满分
  （需要构造 patch 实跑；静态推断都指向"会"）。
- 5545 的 F2P 是否顺序敏感（整文件跑 vs 单条跑，base/gold 各 3 次）。
- 全 216 题范围的三项统计：`scripts/leak.py`（题面泄漏）、按仓库的 base_commit 偏序（答案可见对）、
  `@pytest.mark.network` 与 `@requires_docker` 在 F2P/P2P 中的命中率。三个脚本都已就绪，只是本包只跑了 moto。
