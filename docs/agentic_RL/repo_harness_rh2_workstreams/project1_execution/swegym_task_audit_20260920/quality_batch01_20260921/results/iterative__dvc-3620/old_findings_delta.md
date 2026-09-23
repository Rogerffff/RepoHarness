# iterative__dvc-3620：历史核对差异

协调者核实前稿后才开放 `R/runs/swegym_quality_batch01_20260921_v2/history/iterative__dvc-3620/refs.json`。本题前稿 SHA256 `d4aa8c171a4a39d05ae8a7a9028b3777b1b71d7a12a2ddcb71b634405882dfb7` 保持不变；R/P/Q/O/T/GL/NL 的绝对路径定义见前稿。

实际读过的旧材料：

- H = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_1/records/iterative__dvc-3620.json`，history refs 唯一指定的旧结论。
- S = `runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/iterative__dvc-3620`；gold/empty 的 `offline/a1/status_map.json` 全文，`test_output.txt` 的安装错误、测试命令/收集、CLI 失败与终态片段，gold 的 `eval.sh` 安装与恢复/测试命令。
- 旧报告以省略路径引用的 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_probe_20260909/ledger/cc_candidate_grading.jsonl`，仅按本题 ID 提取，未找到本题行，未读其它题内容。
- 历史提出的同族 3527 等其它题材料没有打开；未读 prescan、旧仓 clone、其它旧质量报告。额外在本题 base 的 test_fs/test_remove/test_gc 静态查找权限/删除测试位置，不把搜索命中当全文审阅。

| 旧主张 | 核对结论 | 当前决定性依据与处理 |
| --- | --- | --- |
| base 的先 chmod 再 unlink 对应 issue；测试不要求新增 `_unlink`；gold 修复合理 | 确认，范围限定 | 前稿已独立追 fs.py:118–143、local.py:412–450 与每个断言；当前 GL 两个 F2P 确实通过，NL 最终 cache 权限失败。gold/helper 不是唯一实现。 |
| “islink 时跳过 chmod”或 `follow_symlinks=False` 同样能通过全部要求 | 推翻其“全部通过”静态判断；是否满足公开需求仍待范围裁定 | 这两种修改若保留 hardlink 原路径，hardlink 的共享 inode 仍被 chmod；新 hardlink F2P 明确要求 POSIX 源保持 0444。NL:654–693 给出对应失败位置。没有实际执行这两个替代方案，不报告实测分数；symlink-only 的逻辑后果与其是否为充分合法解是两件事。CPU 只能核行为/得分，不能替人决定 issue 是否要求硬链接推广。 |
| “F2P 全部可直接从题面推出”，题面无信息落差 | 部分确认、部分降为待审 | symlink 主例直接对应；hardlink 仅有相同根因的推广依据，而公开旧单元/功能测试明确允许源暂时可写。此前初判已保留此歧义，历史没有消除它。当前 public_hints 也不是空字段；旧报告的 hints 描述不可代替当前生成的 public bundle 或实际模型消息。 |
| 旧 gold/empty 的 CLI 测试都在 `os.access(self.FOO,W_OK)` 失败，root 是原因 | 旧失败位置确认；root 解释获日志线索支持，最新环境阻塞已过时 | S/gold test_output:495–498、empty:462–465 均在 unprotect 前失败；empty:494、551 的临时路径为 pytest-of-root。旧报告所引候选账本没有查到本题 UID 行，不额外伪造身份事实。当前账本为 rh2grader/54322，GL:707–718 全7通过；NL CLI 改在 unprotect 后缓存可写断言失败，说明这个历史前置假失败已被当前环境对照消除。 |
| CLI 因旧 root 失败“被剔除参考集”，修身份后必须纳入 F2P | 缺席事实确认；生成因果未证；修改参考是新版本决策 | Q/grading.json 无 CLI ID，最新命令实际执行7、来源只保护6。旧双侧失败不证明来源参考生成时排除此项的具体动机。现在它是额外 F→P；若纳入，应保存来源参考变体，不能悄悄重写原 benchmark。前稿已区分执行过与参考保护。 |
| 旧安装正常，无依赖漂移；status_map 无污染键 | 推翻 | S/gold test_output:383–426 包含 PyYAML 无包、GitHub 解析失败、两份 requirements 不存在、editable build 缺 setuptools；旧 eval.sh:14 把多命令连在一起，末项 RC 不代表全安装成功。两份 status_map 开头均含 `Could:ERROR:`、`No:ERROR:` 假键，9 个映射项不能当9个测试。当前修复配方与日志独立证明安装 RC0、7个真实测试、parser7，旧异常不外推到新运行。 |
| 无 chmod 回退的实现 Linux 可过却破坏 NTFS 只读文件删除 | 静态风险合理，未执行反例 | gold 保留失败回退；本题当前 7项只跑 Linux，无 unlink 首次失败的受控测试。4 P2P 的 chmod mock 作用于 protect，不是 remove。不能把“仍可满分”写成已观测错误候选，也不能据此宣称正常 gold 在 Windows 已验证。 |
| 加跑 Linux remove/gc 公共模块就能挡住缺 NTFS 回退的实现 | 证据不足，建议不能保证目标 | 本题公开 test_fs.py:163–172 只检查删除普通 str/PathInfo；已读 test_remove 核文件/断链/目录，当前关键词搜索未发现该三文件注入首次 unlink 权限失败。普通 Linux 删除只读文件不能模拟 NTFS 的拒绝条件。若今后需验证回退，应选真实 Windows 或受控首次 unlink EACCES、chmod 后成功的独立测试；不把扩大 Linux 文件数当跨平台证明。此项不取代前稿唯一优先 CPU 对照。 |
| 与 3527 同测试ID，所以必须同侧划分 | 本轮未核实，不能据此强制同族 | 未打开其它题。当前题自身的 base→patch 已显示同 ID 语义变化，因此索引需含任务与版本；这不单独证明跨题同修复或训练/留出污染。 |
| 题面给出根因，属于合法详尽 bug 报告但定位难度接近零 | 前半确认，难度估计保留未知 | 当前题面确实含故障源码和原因，不是 gold/未来补丁泄漏。能力/难度、成功率与token成本需独立 solver；不能从 issue 详细度推断实际基座表现。 |

历史阶段没有推翻前稿的核心处置；它增加了两个可直接核实的旧报告错误（安装正常、parser无污染）及“仅修 symlink 即全部通过”的静态误判。当前仍为 `needs_review / static_review`，可在声明硬链接范围与 actor 条件的有限开发诊断中使用，不沿旧 `needs_repair` 标签认定当前权限环境仍坏。新增实验仍未执行，原题/参考/环境配方均未改。

唯一优先后续仍是前稿的 base/gold/symlink-only 对照：同一非 root actor 条件、固定非空内容与两类链接，分开记录公开主例行为、硬链接推广行为、来源分数及额外 CLI。若得到“修好 symlink 但硬链接 F2P 失败”，事实能界定评分范围，不能自动宣告测试误拒或替代解已满足全部公开义务。独立 reviewer 尚未回填，不预写其结论。
