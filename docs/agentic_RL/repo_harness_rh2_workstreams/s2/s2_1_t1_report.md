# S2-1 T1 报告：raw 重抓归档 + 键控镜像清单

日期：2026-07-12。执行：S2-1 线程（本机）。依据：执行计划 §4 T1。判定（2026-07-13 终态）：**T1a PASS；T1b 完成（216/216 fully-verified，完成断言全过，schema v4）——待复核后 T1 关闭**。产物 digest 账：`s2_1_manifest_v0.json`（回链 freeze_manifest v0.1，冻结账本未动）。

## T1a raw 重抓归档（`rh2/experiments/s2_1_ingestion/fetch_raw_lite.py`，可重跑）

```text
1. revision 核对：HF 当前 sha == 冻结 pin（f70b1a29…）——数据集自冻结未动；
   下载走 hf_hub_download 按 pin 取 parquet（不走 datasets-server，
   它只服务最新 revision 无法按 pin 取数）。
2. 230 行 × 11 列，与 strip_spec swe_bench_family 键集合双向相等
   （多列拒绝/少列拒绝的 fail-closed 两个方向都在脚本里）。
3. survivor 级 D5 断言（codex 轮次 5 指出旧互斥脚本的 train_pool∩heldout
   是同义反复后新增的真实检查）：216/216 按 instance_id join 成功、
   唯一、repo ∩ {tornado,pyramid,hydra,bokeh} = ∅。此断言就此成为
   正式机器检查，T2 起并入 ingestion 库。
4. 一致性回验：230 行的 8 个裁剪字段逐字节等于冻结 meta/swe_gym_lite.jsonl
   ——raw archive 与冻结元数据同源同版的直接证明。
5. 落盘：s2/raw/swe_gym_lite_full_f70b1a29.jsonl（3.5MB 明文，按
   instance_id 排序 + 键排序，可 diff 可复算）+ .sha256 旁证。
```

## T1b 键控镜像清单（`rh2/experiments/s2_1_ingestion/resolve_image_digests.py`，可重跑/断点续跑）

```text
216/216 解析成功 → s2/image_manifest_keyed.json
方法：逐镜像匿名 token + registry HEAD 读 Docker-Content-Digest
  （HEAD 不计 Docker Hub pull 限额；0.4s 间隔 + 指数退避，实跑零 429）。
映射校验：`_s_` 规则推导 ref 均存在于冻结清单——但首跑抓到一个真实坑：
  Docker 仓库名强制小写，规则必须是 replace('__','_s_') + lower()
  （Project-MONAI__MONAI-* → project-monai_s_monai-*）。data_freeze 的
  image_manifest.md 只写了 `_s_` 替换未写小写化；fail-closed 校验按设计
  拦截，规则已修正并记 implementation-notes（勘误回写清单 +1）。
内容类型：216 个全部是单架构 v2 manifest（非 manifest list）——
  platform 字段按命名约定记 x86_64，抽样 GET 证实"单 manifest"形态
  （架构在 config blob，未展开；诚实留痕，不冒充逐镜像实证）。
```

## 发现：214 唯一 digest / 216 条——两对同镜像任务

```text
getmoto__moto-6469 / getmoto__moto-6470    同 repo+base_commit（3e11578a…）
python__mypy-11824 / python__mypy-11857    同 repo+base_commit（f96446ce…）
```

两对都是**同一仓库快照上的不同 issue**（题面、F2P 各不相同）——是真正不同的任务，共享环境镜像合理。**语义结论（T2 落实）**：`(repo, base_commit)` 是**环境身份**（镜像缓存/物化可去重），不是**任务身份**（任务身份 = instance_id / 题面 + F2P）；data_freeze 的跨源去重规则意图是"同一真实 commit 的**同一任务**从两源重复进池"，T2 实现应比对 `(repo, base_commit, F2P 集合)` 或标记人工复核，**不得按 (repo, base_commit) 盲目去重**（否则这两对里各有一题被错杀）。

## T0 补注（codex 轮次 5）

旧互斥脚本的 `train_pool ∩ heldout` 检查在数学上必空（`train_pool` 定义时已减去 heldout），T0 报告的该行不构成 survivor 级证明；真实证明由本报告 T1a 第 3 项 + codex 独立复跑（216/216 join、命中 0）补齐。T0 的其余结论（digest 零漂移、与 Verified 互斥）不受影响。

## T1 follow-up（2026-07-13，codex 轮次 6 审查后修复；T1 验收状态 = 待富化收满）

codex 用反例证明了 v1 resolver 三个真实缺陷，全部修复（`resolve_image_digests.py` v2）：

```text
1. 续跑 fail-open（改 digest 为 "bad"/塞多余条目仍报 ALL PASS）
   → v2 加载旧文件逐条严格校验（id∈survivors / ref 与规则+冻结清单双合 /
     digest 正则 / 必填字段 / 无多余 id / header refs digest 匹配），
     损坏即拒绝；完成时强制 set(entries)==set(survivors) 且逐条 enriched。
2. 重跑清空 platform_sample header → v2 header 由事实重建（含
     schema_id=rh2.s2_1.image_manifest_keyed.v2），幂等。
3. 非原子写 → 临时文件 + fsync + os.replace（主文件与 evidence 同律）。
```

计划要求的完整口径补齐中：**平台实证** = 逐镜像 GET manifest（顺带 digest
漂移检测：GET 返回的 Docker-Content-Digest 与已存值不符即 fail）→ GET
config blob（不计 pull 限额）→ 断言 os/architecture == linux/amd64；
**registry_evidence_ref** 回链 `raw/image_registry_evidence.jsonl` 逐镜像
事实行。进度：**183/216 enriched**（匿名 pull 限额 ratelimit-remaining
降至 7 触发优雅停车，checkpoint 原子落盘；限额窗口重置后重跑续做剩余 33）。
已 enriched 的 183 条全部平台断言通过、零 digest 漂移。

其余修复：fetch_raw_lite 加 immutable 守卫（同名不同内容拒绝覆盖）+ 原子写
+ 脚本内 current-sha 对照（复跑实证 verify-only 路径）；pyproject 新增
`data` dependency group（huggingface_hub/pyarrow/pyyaml，此前靠环境碰巧
装有）；去重语义按 codex 建议再收严——`(repo, base_commit, F2P)` 也不作
自动去重主键，改为 source-qualified task_id + 多 digest（题面/test_patch/
F2P/P2P/gold patch）构成 duplicate cluster 交规则或人工判定（T2 落实）。

## T1 follow-up 2（2026-07-13，codex 轮次 7 → resolver v3）

新发现的引用完整性缺口成立（他的反例：evidence 文件整个删掉或 digest 全改错，
v2 仍 ALL PASS）。v3 修复（状态机抽到
`rh2/src/repoharness2/taskset/image_manifest_store.py`，13 项无网络单测覆盖
他要求的全部七类场景）：

```text
1. enriched 判定 = entry 字段形状 ∧ evidence 行存在 ∧ 逐字段交叉核对
   （manifest/config digest、repository、content type、平台、evidence_id、
   blob 哈希已验）∧ evidence 无多余/重复 id。
2. 双文件事务：evidence 先原子写 → sha256+行数入 manifest header →
   manifest 最后原子写（提交记录）。崩溃唯一可能 = evidence 超前，
   load 按提交记录恢复（丢未提交行并计数告警）；反方向一律拒绝。
3. evidence_ref 修正为 raw/image_registry_evidence.jsonl#imgev-<id>；
   evidence 行带 schema_id（rh2.s2_1.image_registry_evidence.v1）+
   稳定 evidence_id + config_blob_sha256_verified（下载原始字节重算
   sha256 必须等于 config_digest——不再只信解析后的 JSON）。
```

执行：183 条 v2 legacy 走**零限额升级通道**（仅重取 config blob 补验哈希，
不重复消耗 manifest GET 限额），blob 哈希 183/183 实证一致；限额窗口未复位
（余 7），完整富化续做 1 条后再次优雅停车——**当前 184/216**，重跑续做剩余 32。

## T1 follow-up 3（2026-07-13，codex 轮次 8 → store v3.1）

事务恢复的 SHA 回验缺口成立（反例：改已提交行的 fetched_at、保留旧 header
SHA → v3.0 照单全收且 recovered_drop=0，因为 fetched_at 不在 cross_check
字段内）。v3.1 修复三项 + 一项补强：

```text
1. 恢复规则收严：evidence 文件 SHA ≠ 提交记录时，取已提交 id 集合按 flush
   同规则规范化重序列化回验 SHA——已提交行任何字段变更（含非交叉核对字段）
   都被拒绝；只有"逐字节原样 + 纯追加"才算 evidence 超前。
2. manifest 重复 instance_id 显式拒绝（原先字典写入静默覆盖）。
3. header 机器账目对账：count / evidence_line_count 必须与实际相等；
   enriched_count 严格对账对 v3.1+ 文件（reverify_count 标记在场）执行，
   v3.0 旧口径文件一次性迁移跳过。
4. 补强：manifest 原始字节 sha256 == Docker-Content-Digest 实证
   （manifest_blob_sha256_verified 入 evidence；旧条目归 reverify 通道
   由完整富化补验）。
回归测试 +6（含"已提交行被修改必须拒绝"），店面单测 19 项全绿。
执行：限额窗口恰好重置，本轮 ~190 个 manifest GET 把 184 条 reverify 全部
补齐字节实证（零 digest 漂移——相当于对既有数据做了一次全量复验）+ 1 条新
富化：当前 185/216 fully-verified，剩 31 条待下一窗口。
```

## T1 follow-up 4（2026-07-13，codex 轮次 9 → schema v4）

降级绕过缺口成立（四个反例：删 evidence_file_sha256 / 删 reverify_count 改
enriched_count=999 / 删 source_refs_file_sha256 / 改 evidence_file 路径均被
v3.1 接受；组合反例 = 删提交 SHA 后改已提交 evidence 也被接受）。根因：
v3.1 的严格性挂在**可选字段**上——删字段即关闭 fail-closed。

v4 修复：显式新 schema（rh2.s2_1.image_manifest_keyed.v4），header 十个字段
**必填必验**（schema_version/source_refs_file 及其 sha256/evidence_file 及其
sha256/evidence_line_count/count/enriched_count/reverify_count；路径字段与
固定值比对、digest 字段正则校验）；v2/v3 直接加载一律拒绝（报错指向显式
迁移），`migrate_v3_manifest` 只接受调用方提供 sha256 pin 命中的**已知旧
产物**，迁移后立即重写为 v4。回归测试 +14（含 9 字段删除参数化、路径不符、
删版本标记伪造计数、删提交 SHA 改 evidence 组合反例、迁移 pin 错误拒绝、
迁移后 v4 round-trip），store 单测 33 项全绿。

执行：真实产物以 pin=20ad8f33… 一次性迁移为 v4 并通过严格加载（185 条
fully-verified 无损保留）；限额余量仍低，续富化 1 条后停车——当前
**186/216**，剩 30 条待下一限额窗口。

## T1 follow-up 5（2026-07-13，codex 轮次 10 → store v4.1 + T1b 收满）

三个问题全部成立并修复：

```text
严重 1 无归属 evidence（digest-only entry 名下的 evidence 行）：v4 加载接受
  但不消费，下次 flush 静默删除——writer 可写出无法无损往返的状态。
  修复双防守：flush 写盘前逐条校验 evidence 归属（enriched-shape entry 存在
  且 cross_check 通过，否则拒绝写盘）；严格加载要求
  set(st.evidence) == set(raw_lines)，未消费行一律拒绝。旧格式 evidence 的
  丢弃只允许发生在显式迁移路径且计数（migrated_dropped_evidence）。
一般 2 迁移只 pin manifest：无内嵌提交 SHA 的旧产物可在 pin 后换 evidence。
  修复：迁移要求 manifest+evidence 双 pin；旧 header 内嵌 SHA 与调用方 pin
  互检；resolver CLI 的迁移入口其后按轮次 11 移除（见 follow-up 6）。
一般 3 计数字段类型：216.0/True/False 都能通过 ==。修复：type(v) is int
  且 >= 0（显式排除 bool/float）+ 计数链一致性
  enriched + reverify <= evidence_line_count <= count。
回归测试 +10（无归属 evidence 加载/写盘双向、双 pin、header 互检、丢弃计数、
类型参数化），store 单测 43 项全绿。
```

**T1b 收满**：本轮限额窗口重置，剩余 30 条完整富化全部完成——
**216/216 fully-verified**（digest + manifest 字节哈希 + config blob 哈希 +
平台 linux/amd64 + evidence 逐字段交叉核对），`finish_assertions` 全过，
resolver 以 ALL PASS 退出。T1 全部交付物就位，待复核后关闭。

## T1 follow-up 6（2026-07-13，codex 轮次 11 → 代码面收尾，T1 交付终态）

两条均成立并修复：

```text
严重 1 迁移 CLI 与双 pin API 脱节：v4.1 改了 migrate_v3_manifest 签名
  （双 pin）但 CLI 仍传单 pin——调用即 TypeError；报告"CLI 带双重防护"
  与代码不符。处置（按 codex 推荐的最干净方案）：从 resolver CLI 移除
  迁移入口（真实迁移已完成）；migrate_v3_manifest 留在 store 供未来
  一次性审计化使用（双 pin + 互检 + 丢弃计数，单测覆盖）；报告措辞修正。
一般 2 writer/loader 不对称：flush 拒绝"evidence 无归属"但不拒绝
  "enriched entry 缺 evidence"——能写出 loader 必拒（计数链）的状态。
  修复：写盘前对称守卫 set(st.evidence) == owned_ids（多与少双向拒绝）
  + 逐条 cross_check；新增写盘拒绝测试。
store 单测 44 项全绿；真实产物复跑 ALL PASS（216/216 保持）。
上轮提交信息里的"822"是文字口径过时（提交时全套已 831，账本记录一致）。
```
