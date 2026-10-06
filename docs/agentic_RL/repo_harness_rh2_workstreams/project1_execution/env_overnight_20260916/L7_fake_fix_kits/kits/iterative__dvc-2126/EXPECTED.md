# iterative__dvc-2126 · 反例期望

- 仓库/版本：`iterative/dvc` @ `1c6f46c0419232cc45f7ae770e633d3884bac169`（version 0.41，python 3.8）
- 镜像：`xingyaoww/sweb.eval.x86_64.iterative_s_dvc-2126:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -rA`
- 判分面：F2P 2 条、P2P 0 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=0）

## 1. 断言来源

- 来源包：`L1_dvc_1 / records/iterative__dvc-2126.json issues[1]`
- 断言编号：零回归保护 P1（25/26）
- 原文摘要：写硬编码 `"Binary: False\n"` 的假修复跑当前 F2P，预期满分，形成反例。（证据：`mat/iterative__dvc-2126/grading.json#pass_to_pass` 0 条；`git show 1c6f46c041:tests/func/test_version.py` 全文件仅 2 条用例，均入 F2P）

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/iterative__dvc-2126.fake.diff` | `CmdVersion.run` 里把 Binary 行写死成 `"Binary: False\n"`，不调用 `dvc.utils.is_binary()`。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：2 条 F2P 的新增断言是正则 `Binary: (True|False)`，硬编码字面量必然命中；P2P 为 0，没有任何回归能拦下。题面要的是『报告当前是否为打包二进制』，硬编码之后 pyinstaller 打包场景永远报 False。

## 4. 正确评分器应该抓到什么

把 `dvc.command.version.is_binary` 打桩成返回 True，输出必须变成 `Binary: True`；base/fake 里这个名字根本不存在（monkeypatch 会 AttributeError）。

判别用例脚本：`kits/iterative__dvc-2126/diagnostic_test.py`（run_matrix.sh 会把它复制成 `/testbed/tests/func/l7_diag_dvc_2126.py` 再运行，跑完删除；它断言的是 base 的既有公开行为与题面目标，**不是** 官方判分面的一部分，也不参与 `full_score` 判定）。

## 5. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）
