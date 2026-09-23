# iterative__dvc-4185

**静态建议：needs_review / static_review；用途 development_diagnostic。** Base `0899b277c020`。题面要求同时消除未变参数的 commit 误报，以及 false 参数反复被 status 标为 new。gold 只改 fill_values；公开两目标不应被静默裁成一项。

| 需求/旧行为 | 公开依据 | 关键验收 | 覆盖/证据 |
| --- | --- | --- | --- |
| 已记录假值不报 new | 题面 false；param.py 键存在语义 | 七 F2P：fill_values 后 status=={} | 局部覆盖；历史 noop 0/7、gold 7/7。空文本项为 null，并非真正空字符串。 |
| 未变参数 commit 无提示 | 题面第 1 点 | 无参数 commit 参考断言 | 缺失；强静态链表明仍比较参数映射中的缺失 md5 与文件哈希，gold 未改。 |
| 真变值/删键/新增仍可检测 | param.py:L63-L75、公开 repro 旧测试 | 七项都仅测“不变→空” | 缺失；恒空 status 是待验错误候选。当前文件缺键应 deleted；当前有键但 lock 未记录才是 new。 |

八方面已查：公开要求；base/补丁身份；全部 test.patch、7 F2P、22 P2P及必要 helper；合理哨兵/映射替代路线；loader/cache/serialize/commit 回归路径；既有环境原件；官方恢复两测试文件及 gold 投影；暴露/用途。未查：真实 solver 消息、actor 开发条件/可见资产、替代解实跑、跨题关系、模型表现。独立复审支持先诊断双目标缺口，暂缓普通能力 probe；不是仅待 actor 验收的候选。

09-19 真 RH2 在 dvc_install_v1c＋reference-bindings-v1 下，gold 为 49 passed/2 skipped、参考 7/7＋22/22；noop 为 7 failed/42 passed/2 skipped。ID 转义和 networkx 旧阻塞已被这套条件覆盖；满分不证明 commit 目标完成。日志/ledger 详见初稿；这些是 rh2grader/54322 条件，未验 actor。

封存后补充：两侧 setup.py 均预改 moto `.dev464`→`1.3.14`，未来对照须固定此共享差异，不能称 pristine base。资源只引用原字段 `mem_peak_mb`（gold 386.82/noop 482.152）；初稿换写 MiB 的表述已在差分稿纠正，未回写原稿。历史 raw hints 说法未核原件，实际 actor 资产泄漏仍未知。

**唯一优先下一步：**在记录了镜像、配方、moto 预改、身份及源码来源的固定环境，对 base/gold 重放公开本地两阶段例：普通 start 参数＋嵌套 false，重新加载后记录 status 与不带 force 的 commit。预期 gold 清除 false 的 new，却仍提示普通参数已变；首轮仅附 start 改值正向控制，并记录参数 info 与文件哈希；其他边界留后续。尚未执行任何新实验。详见 [初稿](analysis_before_history.md) 和 [差分](old_findings_delta.md)。审查已见隐藏测试、gold、运行结果和旧记录，产物不得进入 solver 上下文。

[独立复审](review.md) 已纳入。复审将替代解 KeyError 提醒限定为基类 status 返回空映射等条件下的风险，不否定所有参数专用比较方案。两份初稿均保持封存。
