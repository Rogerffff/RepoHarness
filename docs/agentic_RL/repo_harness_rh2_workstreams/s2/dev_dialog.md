# S2 开发沟通文档（dev_dialog）

> **用途**（用户 2026-07-13 要求建立）：每一轮实现/修改中，我（Claude，S2-1 线程）在此记录：作出的设计决策、有意的偏离或新增、以及需要你知晓或拍板的事项。与 `implementation-notes.md` 的分工——**本文面向沟通**（可以有未定事项、备选方案、我的建议），**notes 面向阶段归档**（只记定案）。条目标记：❓ 待你拍板 / ✅ 已定案（含定案人）/ ℹ️ 周知即可。
>
> 阅读顺序建议：只看未勾选的 ❓ 与最近一节即可跟上；历史细节在 `s2_1_t2_report.md` 与 `codex_reviews.md`。

---

## 2026-07-13：codex 轮次 15 修复（T2-c 可信链收口）

**背景**：codex 复核确认 T2-c 数据内容正确，但可信链还有两个洞：输出提交记录没有外部锚（一致性篡改整套产物可通过）、loader 没绑定封板全集（裁成 1 条也通过）。本轮全部修复，T2-c 达到其"可关闭"条件。

### 决策记录

- ✅（我定，理由如下，可否决）**输出外部锚选了"代码 pin 常量"而不是独立的 `t2c_output_pins_v1.json` 文件**。codex 给了两个方案；我选把 `ingest_manifest_v0.json` 的 sha256 钉进 `ingest_swegym_lite.py` 的 `INGEST_MANIFEST_SHA256_PIN` 常量。理由：① 与 t1_pins 同一信任根（代码文件被 S1 账本 rglob 追踪，篡改 = 账本红灯）；② 少一个"pins 文件的 pins"层级——提交记录已内嵌五文件 digest，钉住它即传递锚定全部输出；③ **重新生成产物 = 必须改代码常量 = 账本可见的审计事件**，这正是我们要的语义。代价：重生成产物的流程多一步（runner 注释已写明顺序）。
- ✅（我定）**`load_trusted_ingest_outputs(repo_root)` 是 T2-d/e 的唯一正式消费入口**（codex 建议采纳）：内部完成 T1 pins 三级验证 → survivors/image store 严格加载 + 完成断言 → 提交记录对代码 pin → 严格解析 + 全集绑定 + 逐包验证 + 簇重算。下游不再自行拼装 pins/store。裸的 `load_ingest_outputs` 保留但 docstring 明示非正式入口（单测用）。
- ✅（我定）**无 pins 写出只存在于 `write_ingest_outputs_for_tests`**（显式命名，t1_input_pins 全零占位，产物永远过不了 strict loader）；正式 writer 的 `pins` 必传。
- ✅（我定）**F2P/P2P 唯一性与互斥进了 schema validator**（`PrivateGradingBundleV2`）：矛盾评分事实在模型层不可表示，不再只靠 ingestion 构造时检查；`python_version` 也纳入消费期互检（`verify_grading_eval_cmd` 现在同时互检 eval_cmd 与 python_version——凡声称来自 vendor 的字段一律重派生互检）。
- ℹ️ **测试夹具修正**：合成 grading 夹具的 `python_version` 从 "3.11" 改为 "3.12"——因为消费期互检生效后，夹具值必须等于真实 vendor 派生值（getmoto/moto 4.1 → python 3.12）。

### 现状与下一步

- T2-c 按 codex 的关闭条件已收口（等其复核确认）；真实 216 题产物五文件 digest 全程未变（本轮改的全是链条不是数据）。
- **T2-d（`grade_controlled_patch` 受控评分入口）已具备开工条件**：接 `load_trusted_ingest_outputs`，合成 fixture 开发可先行（codex 同意的并行面）。
- ❓ **无待拍板事项**。若你对"外部锚用代码 pin"的选择有异议（例如更希望独立 pins 文件形成纯数据链），说一声我可以低成本切换——两种方案的验证逻辑同构。

---

## 追溯摘要（本文档建立前的关键已定案，避免翻历史）

- ✅（用户 2026-07-13）T1 关闭；T2 开工。
- ✅（codex 轮次 12~14，用户经我采纳）：vendor 链 = 封闭枚举 id + 固定注册表 + 构建期提取 JSON/运行期只读；eval_cmd 注册表派生 + 构造/消费双互检；身份交叉核对（repo/base_commit 逐字相等）；T1 输入封板 pins（代码→pins→文件三级链）；输出事务化（原子写 + 提交记录）。
- ✅ 去重语义：任务身份 ≠ 环境身份；moto-6469/6470 与 mypy-11824/11857 两对同环境不同任务必须保留；suspected_duplicate 只标记进人工复核。
- ✅ strip_spec 三保险（常量 + yaml digest pin + 语义等价测试）；D5 survivor 级断言收编。
