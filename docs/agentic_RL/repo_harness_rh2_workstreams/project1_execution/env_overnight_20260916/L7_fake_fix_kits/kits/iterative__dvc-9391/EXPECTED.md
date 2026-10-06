# iterative__dvc-9391 · 反例期望

- 仓库/版本：`iterative/dvc` @ `6b6084a84829ba90b740a1cb18ed897d96fcc3af`（version 2.56，python 3.9）
- 镜像：`xingyaoww/sweb.eval.x86_64.iterative_s_dvc-9391:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -rA`
- 判分面：F2P 5 条、P2P 24 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=0）

## 1. 断言来源

- 来源包：`L1_dvc_2 / records/iterative__dvc-9391.json issues[0]`
- 断言编号：奖励漏洞（可复现）P1
- 原文摘要：写 `type=lambda s: [s]`（或在各 run() 里包一层列表）的假修复跑 F2P+P2P，预期 RESOLVED_FULL。（证据：5 条 F2P 无一传两个 `--rev`；P2P 24 条与 `--rev` 无关）

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/iterative__dvc-9391.fake.diff` | `add_rev_selection_flags` 里把 `--rev` 的 `type=str` 换成 `type=lambda s: [s]`，不加 `action="append"`。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：5 条 F2P 都只传一个 `--rev foo` 并断言下游收到 `rev=["foo"]`；把单值包成 1 元列表即可满足。真正的诉求『`--rev a --rev b` 得到 `["a","b"]`』在假修复下是后者覆盖前者，判分面里没有任何用例能发现。

## 4. 正确评分器应该抓到什么

`parser.parse_args(["--rev","a","--rev","b"]).rev == ["a","b"]`；假修复只会给出 `["b"]`。

判别用例脚本：`kits/iterative__dvc-9391/diagnostic_test.py`（run_matrix.sh 会把它复制成 `/testbed/tests/unit/l7_diag_dvc_9391.py` 再运行，跑完删除；它断言的是 base 的既有公开行为与题面目标，**不是** 官方判分面的一部分，也不参与 `full_score` 判定）。

## 5. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）
