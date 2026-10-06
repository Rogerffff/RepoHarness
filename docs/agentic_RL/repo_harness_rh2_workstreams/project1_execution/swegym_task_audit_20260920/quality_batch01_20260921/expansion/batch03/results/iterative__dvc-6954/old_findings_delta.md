# iterative__dvc-6954 — 旧结论差异

封存稿 SHA256 `d5ebf321afc22eba7f33a588fcd04d0fe9605ada0bb9b973b0b68f3b6438e4ce`。协调者 2026-09-20T21:10:32.205491+00:00（UTC；SGT 2026-09-21 05:10:32） 明确放行后，才读本题 history/refs.json 及其唯一精确旧记录；未回写封存稿。旧记录路径：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_2/records/iterative__dvc-6954.json`。决定性新证据路径简写沿 analysis_before_history.md。

| 旧主张/行号 | 处置 | 决定性证据与本次解释 |
| --- | --- | --- |
| base 有负数缺参 bug，gold 无业务外改动；1 F2P/12 P2P (:52,63-70,152-158,200-205) | 确认其本题语义与最新 grader 分差 | base _py.py:116-119,172-181；V/test.patch/gold.patch 全文；R/noop 日志:667-673 与 gold:698-711；两 ledger:1。不是重跑 09-16。 |
| 13/13 ID 按空白截断，目前无碰撞 (:106-115) | 确认本次身份限度；不据此重写参考 | V/grading.json 与原日志完整 13 项一一对应独特首 token；两 ledger missing/skipped=[]、parsed=13。以后增用例须重新审身份；旧碰撞脚本未重跑。 |
| CONSTRUCTOR/SUM “无题面依据”，应补题面、用 eval 对照 (:117-123,221-228) | 推翻“必须补题面”判断 | 公开 base _py.py:89-120,172-181 已给出静态提取与忽略非法节点的旧行为；test_params.py:164-176 也限定赋值范围。正常 bug 修复可要求保留此边界；执行用户文件的 eval 不是已证明合法替代解。无需为测试倒补规格。 |
| P2P 因为新建文件所以不是既有回归 (:143-149) | 推翻该二分；确认调用面缺口 | 新用例能够检查 base 已有类型和作用域行为（公开 test_params.py:114-176）；noop 12 passed 是直接证据。仍没有 ParamsDependency/CLI/lock/update 的冻结保护。 |
| 负 float/容器/类/CLI 未测；+1 也应补；硬编码很难通过 (:134-140,230-237) | 部分确认，收窄范围 | test.patch:14-50 确无前述负值变体和端到端。+1 非公开必要条件；12 P2P 不能阻止只加整数负号支持的部分修复，不能称强抗硬编码。没有实际反例，保留静态线索。 |
| install 段仍需网络、环境通过 (:168-174) | 对当前引用条件已过时 | recipes/<id>.json:3-11 与 wrapper:61-86；最新双角色日志有离线链接目录、editable 安装成功，RC0，deny_all。COPY wheels 本身不是成功证据。actor 安装/权限/镜像存在仍未核。 |
| 题面 hints 为空且可判泄漏 pass (:73-79,160-165) | 分开来源；不能推广 | raw hints_text 的旧字段未再查；当前 public_bundle 存非空 harness public_hints。静态题面没有答案代码，但未核真实 actor 可见 Git/镜像/缓存，不给泄漏验收 pass。 |
| 新文件 checkout 不影响恢复 (:90-96) | 最新实际机制更新 | 历史归档 prepared_task_face.py:185-234：profile 对 base 不存在的官方路径跳过 checkout 并 attested apply；R 两 diagnostics trusted_setup OK。不能拿完整 eval 审计文本代替实际 profile 脚本。 |
| 无同包同路径题即无重复、上游 commit 精确相符 (:55-60,98-104) | 未核实其谱系外推 | 本次只核本题原件/运行；未读 prescan 或访问旧 clone 的上游提交，不按同文件/本包唯一推断无重复。 |
| ready_for_probe，成本 16 分钟 (:262-268) | 不沿用 | 两次新 ledger env_qualification=absent；正式 actor/工具/输入未验。当前固定为 needs_review/static_review；未知成本 null，旧估时不冒充观测。 |

历史没有改变主审的核心静态候选建议。它增加了“当前无碰撞但参考截断”的显式记录，纠正旧语义理由，并更新环境/恢复适用条件。唯一优先下一步仍是明确 actor 条件下的窄公开 repro/lock 流程及同形负浮点检查；未自动申请改题、改 reward、全仓门槛或 parser 改写。
