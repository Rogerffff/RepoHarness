# 固定候选的 CPU 行为裁决（Codex 09-22 §9.3 高优先工作包 B）——离线准备，待机器恢复后执行

用 `../behavior_check.sh` 在题目公开镜像里对 noop / gold / 指定候选运行同一段公开检查脚本，产出"输入 → 预期依据 → 各变体结果"表。不评分、不改题、不回写历史。

| 题目 | 检查脚本 | 要对照的候选 | 镜像与前提 | 状态 |
| --- | --- | --- | --- | --- |
| Conan15422 | （已执行）`runs/base_probe_20260922/remote/runs/conan15422_fp_check/` | gold、DeepSeek a1、Coder a1 | 原镜像 | 已实测：两条官方通过的候选各漏一条路径 |
| Moto5752 | `moto5752.py` | gold、DeepSeek a1/a2、Qwen3.6 a1/a2、Coder a1/a2 | 原镜像 | 待执行 |
| Moto5134 | `moto5134.py` | gold、Coder a1–a4、Qwen3.6 a1（哨兵）、a2（布尔标志）、DeepSeek a1 | 原镜像；含评分选集外的 `test_events.py` 全文件 | 待执行 |
| DVC5839 | `dvc5839.py` | gold、DeepSeek a2（过度修复）、Qwen3.6 a1、另造"命令层硬编码 8"校准候选 | **actor_dvc5839_v1** 派生镜像（pathspec 0.8.1，`/work/probe/derived/actor_dvc5839_v1/image_id.txt`） | 待执行；校准候选待写 |
| DVC6954 | `dvc6954.py`（按处置卡 E1 修订：去掉无区分力的 params diff、helper 逐输入、加 -0.5→-0.25 与 nested 改值重跑、坏行文件、`dvc run`） | gold、DS a2（封住 -'a'）、DS a3、Coder a2、Q36 a2 | 原镜像（pathspec 0.9.0） | 待执行 |
| mypy17071 | 待写 | gold、Qwen3.6 a1、DeepSeek a1/a2、校准候选 C1（在 BASE `mypy/checker.py:1423` 文档串后插 `return`，静态预计官方得 1）、可选 C2（见 guard 回调即 return） | install_wave1 派生镜像（本轮重建 `sha256:92e9a049…`；题卡 / 队列仍引 09-19 的 `65be1535…`） | 待写：原例 TypeGuard/TypeIs、`f()->T` / 带界 U / 值约束 V、回调只含 U 返回 T、两层嵌套回调、延迟探针（未定义名 / 后定义模块级名）、stderr 非诊断行；随后用 `replay_grade.py` 对 C1/C2 做 RH2 评分，据此再定选项 B |
| mypy11236 | 待写 | gold、DeepSeek a1、**a2**、Qwen3.6 a2（**候选必须用 `candidate_v2/`**，v1 含镜像自带脏文件 `test-requirements.txt` 会 apply 失败） | install_wave1 派生镜像（本轮重建 `sha256:5e4a1727…`；队列项 `replay_entry` 仍指 09-19 历史镜像，需改指） | 待写：公开 MWE（题面原 flags）/ `(2,)`、`(1,999)` / Final / 六负例（"是否报错"与 got 文本分两列）/ 处置卡新增的区分输入 A（`Union[Tuple[int,str], Tuple[Literal[1],int]]` 返回 `(1,5)`）与 B（`Union[Tuple[Literal[1],int], Tuple[str,Literal[2]]]` 返回 `("a",2)`）；另在固定 grader 上对 gold / noop / 三条候选跑 base 版与上游改写版 `testLiteralFinalGoesOnlyOneLevelDown` |

执行示例（远端，实例恢复后）：
```bash
cd /work/code/rh2/experiments/base_probe_20260922
A=/work/probe/runs/matrix/attempts
bash behavior_check.sh getmoto__moto-5752 xingyaoww/sweb.eval.x86_64.getmoto_s_moto-5752:latest checks/moto5752.py /work/probe/runs/behavior/moto5752 \
  gold=/work/probe/replay/gold/getmoto__moto-5752.gold.patch \
  ds_a1=$A/getmoto__moto-5752/deepseek-v4-pro/a1/candidate/getmoto__moto-5752.diff \
  q36_a1=$A/getmoto__moto-5752/qwen3.6-35b-a3b/a1/candidate/getmoto__moto-5752.diff \
  coder_a1=$A/getmoto__moto-5752/qwen3-coder-30b-a3b-instruct/a1/candidate/getmoto__moto-5752.diff
```
候选 diff 里的测试段会被自动剔除（只应用源码段）；候选夹带的仓库根草稿文件会随源码段一起应用，不影响检查结果。
